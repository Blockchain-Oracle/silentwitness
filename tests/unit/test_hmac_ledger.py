"""Behavioural tests for src/silentwitness_mcp/audit/ledger.py.

Real filesystem, real PBKDF2 / HMAC — no crypto mocks per architecture §14.
The single permitted mock is on ``hmac.compare_digest`` to prove the
constant-time API IS on the verify path (the test pattern the story spec
prescribes — a timing-side-channel test is flaky in CI).
"""

from __future__ import annotations

import hashlib
import hmac as _hmac_mod
import json
import os
import stat
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from silentwitness_common.types import Confidence, LedgerEntry, LedgerItemType
from silentwitness_mcp.audit import ledger as ledger_mod
from silentwitness_mcp.audit.ledger import (
    HMACLedger,
    InterpretationParts,
    LedgerComposer,
    LedgerCorruptionError,
    LedgerKeyError,
    LedgerSecurityError,
    ObservationParts,
)

_PBKDF_INPUT = "x" * 24  # test fixture — derived bytes are deterministic
_SALT = b"\x00" * 16
_CASE_ID = "c1"
_CONTENT = b"approval content bytes (composed via LedgerComposer at the call site)"
_CONTENT_HASH = hashlib.sha256(_CONTENT).hexdigest()
_FIXED_NOW = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)


def _key() -> bytes:
    return HMACLedger.derive_key(_PBKDF_INPUT, _SALT)


# ---------------------------------------------------------------------------
# derive_key
# ---------------------------------------------------------------------------


def test_derive_key_is_deterministic_and_32_bytes() -> None:
    k1 = HMACLedger.derive_key(_PBKDF_INPUT, _SALT, 600_000)
    k2 = HMACLedger.derive_key(_PBKDF_INPUT, _SALT, 600_000)
    assert k1 == k2
    assert len(k1) == 32


def test_derive_key_matches_stdlib_pbkdf2() -> None:
    """The wrapper must NOT silently transform inputs; bit-for-bit equality
    with hashlib.pbkdf2_hmac is the contract."""
    expected = hashlib.pbkdf2_hmac("sha256", _PBKDF_INPUT.encode("utf-8"), _SALT, 600_000, dklen=32)
    assert HMACLedger.derive_key(_PBKDF_INPUT, _SALT, 600_000) == expected


def test_derive_key_below_owasp_floor_raises() -> None:
    with pytest.raises(LedgerKeyError, match="OWASP minimum 600000"):
        HMACLedger.derive_key(_PBKDF_INPUT, _SALT, iterations=599_999)


def test_derive_key_rejects_non_str_password() -> None:
    with pytest.raises(TypeError, match="password must be str"):
        HMACLedger.derive_key(b"bytes-password", _SALT)  # type: ignore[arg-type]


def test_derive_key_rejects_non_bytes_salt() -> None:
    with pytest.raises(TypeError, match="salt must be bytes"):
        HMACLedger.derive_key(_PBKDF_INPUT, "not-bytes")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# compute_hmac + verify_hmac (constant-time)
# ---------------------------------------------------------------------------


def test_compute_hmac_is_deterministic_hex64() -> None:
    key = _key()
    msg = b"some bytes"
    h1 = HMACLedger.compute_hmac(key, msg)
    h2 = HMACLedger.compute_hmac(key, msg)
    assert h1 == h2
    assert len(h1) == 64
    assert all(c in "0123456789abcdef" for c in h1)


def test_verify_hmac_matches_on_correct_key_and_message() -> None:
    key = _key()
    msg = b"approval bytes"
    assert HMACLedger.verify_hmac(key, msg, HMACLedger.compute_hmac(key, msg)) is True


def test_verify_hmac_rejects_single_bit_flip_in_expected() -> None:
    key = _key()
    msg = b"approval bytes"
    correct = HMACLedger.compute_hmac(key, msg)
    # Flip the last nibble.
    last = correct[-1]
    flipped = correct[:-1] + format((int(last, 16) ^ 0xF), "x")
    assert HMACLedger.verify_hmac(key, msg, flipped) is False


def test_verify_hmac_uses_constant_time_compare() -> None:
    """Patches hmac.compare_digest on the ledger module path and asserts it
    was the function that decided the outcome — short-circuit `==` would
    bypass the patched call and leak through timing."""
    key = _key()
    msg = b"x"
    expected = HMACLedger.compute_hmac(key, msg)
    with patch.object(ledger_mod.hmac, "compare_digest", wraps=_hmac_mod.compare_digest) as spy:
        result = HMACLedger.verify_hmac(key, msg, expected)
    spy.assert_called_once()
    assert result is True


# ---------------------------------------------------------------------------
# zero_key
# ---------------------------------------------------------------------------


def test_zero_key_overwrites_bytearray_in_place() -> None:
    buf = bytearray(b"\xff" * 32)
    HMACLedger.zero_key(buf)
    assert buf == bytearray(32)


# ---------------------------------------------------------------------------
# Directory + file modes
# ---------------------------------------------------------------------------


def test_construction_creates_ledger_dir_mode_0700(tmp_path: Path) -> None:
    ledger_dir = tmp_path / "verification"
    HMACLedger(ledger_dir=ledger_dir, case_id=_CASE_ID)
    assert ledger_dir.exists()
    actual = stat.S_IMODE(os.stat(ledger_dir).st_mode)
    assert actual == 0o700, f"expected 0o700, got 0o{actual:o}"


def test_construction_refuses_weaker_existing_dir_mode(tmp_path: Path) -> None:
    ledger_dir = tmp_path / "verification"
    ledger_dir.mkdir(mode=0o755)
    os.chmod(ledger_dir, 0o755)  # noqa: S103 — deliberately weak; test asserts refusal
    with pytest.raises(LedgerSecurityError, match="group/other access"):
        HMACLedger(ledger_dir=ledger_dir, case_id=_CASE_ID)


def test_construction_accepts_existing_dir_with_exact_0700(tmp_path: Path) -> None:
    ledger_dir = tmp_path / "verification"
    ledger_dir.mkdir(mode=0o700)
    os.chmod(ledger_dir, 0o700)
    HMACLedger(ledger_dir=ledger_dir, case_id=_CASE_ID)
    assert stat.S_IMODE(os.stat(ledger_dir).st_mode) == 0o700


def test_first_append_writes_file_mode_0600(tmp_path: Path) -> None:
    led = HMACLedger(ledger_dir=tmp_path / "verification", case_id=_CASE_ID)
    led.append(_key(), "F-001", LedgerItemType.FINDING, _CONTENT, "aj", now=_FIXED_NOW)
    mode = stat.S_IMODE(os.stat(led.ledger_path).st_mode)
    assert mode == 0o600, f"expected 0o600, got 0o{mode:o}"


# ---------------------------------------------------------------------------
# append → read_all → verify_entry round-trip
# ---------------------------------------------------------------------------


def test_append_writes_well_formed_jsonl(tmp_path: Path) -> None:
    led = HMACLedger(ledger_dir=tmp_path / "verification", case_id=_CASE_ID)
    entry = led.append(_key(), "F-001", LedgerItemType.FINDING, _CONTENT, "aj", now=_FIXED_NOW)
    content = led.ledger_path.read_text(encoding="utf-8")
    assert content.count("\n") == 1
    re_parsed = LedgerEntry.model_validate_json(content.rstrip("\n"))
    assert re_parsed == entry


def test_read_all_round_trips_multiple_entries(tmp_path: Path) -> None:
    led = HMACLedger(ledger_dir=tmp_path / "verification", case_id=_CASE_ID)
    key = _key()
    emitted: list[LedgerEntry] = []
    for i in range(5):
        emitted.append(
            led.append(
                key,
                f"F-{i:03d}",
                LedgerItemType.FINDING,
                f"content-{i}".encode(),
                "aj",
                now=datetime(2026, 6, 13, 14, 27, i, tzinfo=UTC),
            )
        )
    listed = led.read_all()
    assert listed == emitted


def test_verify_entry_succeeds_on_unmodified_entry(tmp_path: Path) -> None:
    led = HMACLedger(ledger_dir=tmp_path / "verification", case_id=_CASE_ID)
    key = _key()
    entry = led.append(key, "F-001", LedgerItemType.FINDING, _CONTENT, "aj")
    assert led.verify_entry(key, entry, _CONTENT) is True


def test_verify_entry_fails_on_tampered_content_bytes(tmp_path: Path) -> None:
    """THE bit-rot detector: HMAC is over content_bytes; a single-byte change
    must invalidate verification. This is the BDD test the original
    implementation lacked (code-reviewer PR-104 finding #1)."""
    led = HMACLedger(ledger_dir=tmp_path / "verification", case_id=_CASE_ID)
    key = _key()
    entry = led.append(key, "F-001", LedgerItemType.FINDING, _CONTENT, "aj")
    tampered_content = _CONTENT[:-1] + bytes([_CONTENT[-1] ^ 0x01])
    assert led.verify_entry(key, entry, tampered_content) is False


def test_verify_entry_fails_on_tampered_content_hash_field(tmp_path: Path) -> None:
    """If the stored content_hash is mutated without changing the live bytes,
    the sha256(content_bytes) != entry.content_hash short-circuit catches it
    BEFORE the HMAC compare."""
    led = HMACLedger(ledger_dir=tmp_path / "verification", case_id=_CASE_ID)
    key = _key()
    entry = led.append(key, "F-001", LedgerItemType.FINDING, _CONTENT, "aj")
    tampered = entry.model_copy(update={"content_hash": "b" * 64})
    assert led.verify_entry(key, tampered, _CONTENT) is False


def test_verify_entry_fails_on_tampered_hmac_field(tmp_path: Path) -> None:
    led = HMACLedger(ledger_dir=tmp_path / "verification", case_id=_CASE_ID)
    key = _key()
    entry = led.append(key, "F-001", LedgerItemType.FINDING, _CONTENT, "aj")
    flipped_hmac = entry.hmac[:-1] + ("0" if entry.hmac[-1] != "0" else "1")
    tampered = entry.model_copy(update={"hmac": flipped_hmac})
    assert led.verify_entry(key, tampered, _CONTENT) is False


def test_verify_entry_fails_on_wrong_key(tmp_path: Path) -> None:
    led = HMACLedger(ledger_dir=tmp_path / "verification", case_id=_CASE_ID)
    key1 = _key()
    entry = led.append(key1, "F-001", LedgerItemType.FINDING, _CONTENT, "aj")
    key2 = HMACLedger.derive_key("wrong password", _SALT)
    assert led.verify_entry(key2, entry, _CONTENT) is False


def test_read_all_on_missing_ledger_returns_empty(tmp_path: Path) -> None:
    led = HMACLedger(ledger_dir=tmp_path / "verification", case_id=_CASE_ID)
    assert led.read_all() == []


def test_read_all_malformed_line_raises_corruption_with_index(tmp_path: Path) -> None:
    led = HMACLedger(ledger_dir=tmp_path / "verification", case_id=_CASE_ID)
    led.append(_key(), "F-001", LedgerItemType.FINDING, _CONTENT, "aj")
    # Append a malformed line behind the back of the API (simulates corruption).
    with led.ledger_path.open("a", encoding="utf-8") as fh:
        fh.write("not valid jsonl\n")
    with pytest.raises(LedgerCorruptionError, match="line #1"):
        led.read_all()


def test_read_all_blank_line_raises_corruption(tmp_path: Path) -> None:
    """Silent-failure H5: an attacker who can write to the file but doesn't
    have the key could selectively erase approval entries by blank-overwriting
    them. The ledger now fails closed on blank lines."""
    led = HMACLedger(ledger_dir=tmp_path / "verification", case_id=_CASE_ID)
    led.append(_key(), "F-001", LedgerItemType.FINDING, _CONTENT, "aj")
    with led.ledger_path.open("a", encoding="utf-8") as fh:
        fh.write("\n")
    with pytest.raises(LedgerCorruptionError, match="blank"):
        led.read_all()


# ---------------------------------------------------------------------------
# LedgerComposer — composition rules verbatim
# ---------------------------------------------------------------------------


def _lp(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return len(encoded).to_bytes(8, "big") + encoded


def test_compose_observation_is_order_independent_and_length_prefixed() -> None:
    a = LedgerComposer.observation(
        ObservationParts(text="evil.exe ran", audit_ids=("zzz", "aaa", "mmm"))
    )
    b = LedgerComposer.observation(
        ObservationParts(text="evil.exe ran", audit_ids=("mmm", "aaa", "zzz"))
    )
    assert a == b  # audit_ids sorted → order-independent
    assert a == _lp("evil.exe ran") + (3).to_bytes(8, "big") + _lp("aaa") + _lp("mmm") + _lp("zzz")


def test_compose_interpretation_length_prefixed() -> None:
    parts = InterpretationParts(
        observation_id="O-042", text="malware detonated", confidence=Confidence.HIGH
    )
    assert LedgerComposer.interpretation(parts) == _lp("O-042") + _lp("malware detonated") + _lp(
        "HIGH"
    )


def test_compose_finding_concatenates_self_delimiting_parts() -> None:
    obs = ObservationParts(text="ran", audit_ids=("a",))
    interp = InterpretationParts(observation_id="O-1", text="bad", confidence=Confidence.MEDIUM)
    assert LedgerComposer.finding(obs, interp) == LedgerComposer.observation(
        obs
    ) + LedgerComposer.interpretation(interp)


@pytest.mark.parametrize("ch", ["|", ",", "\x00", "\t", "\n"])
def test_compose_accepts_arbitrary_chars_in_free_text(ch: str) -> None:
    """Length-prefixing lets observation/interpretation text contain ANY char —
    commas/pipes/tabs from forensic tool output no longer break approval (the
    old separator scheme rejected them, making approval impossible for real
    findings)."""
    LedgerComposer.observation(ObservationParts(text=f"a{ch}b", audit_ids=(f"x{ch}y",)))
    LedgerComposer.interpretation(
        InterpretationParts(observation_id="O-1", text=f"a{ch}b", confidence=Confidence.HIGH)
    )


def test_compose_is_unambiguous_across_field_boundaries() -> None:
    """Distinct field splits must NOT collapse to identical bytes — the property
    length-prefixing guarantees (and the old separator scheme attempted)."""
    a = LedgerComposer.observation(ObservationParts(text="ab", audit_ids=("c",)))
    b = LedgerComposer.observation(ObservationParts(text="a", audit_ids=("bc",)))
    assert a != b


def test_construction_accepts_setgid_plus_0700_directory(tmp_path: Path) -> None:
    """Silent-failure H3: setgid + 0o700 is a legitimate analyst-group setup;
    exact-equality on S_IMODE would falsely reject it. The check is
    ``mode & 0o077 == 0`` (no group/other access)."""
    ledger_dir = tmp_path / "verification"
    ledger_dir.mkdir(mode=0o700)
    os.chmod(ledger_dir, 0o2700)  # setgid + 0o700
    HMACLedger(ledger_dir=ledger_dir, case_id=_CASE_ID)


def test_zero_key_rejects_non_bytearray() -> None:
    """Silent-failure H6: calling zero_key on bytes silently no-ops; raise."""
    with pytest.raises(TypeError, match="bytearray"):
        HMACLedger.zero_key(b"\xff" * 32)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Construction edge cases
# ---------------------------------------------------------------------------


def test_construction_rejects_empty_case_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="case_id"):
        HMACLedger(ledger_dir=tmp_path / "verification", case_id="")


def test_append_with_trailing_space_in_item_id_round_trips(tmp_path: Path) -> None:
    """Regression: previously LedgerEntry stripped whitespace via Pydantic
    ``str_strip_whitespace=True``, so a signer composing HMAC bytes from
    ``"F-001 "`` and a verifier composing from the post-strip ``"F-001"``
    silently disagreed. Hypothesis caught it; this pins the fix."""
    led = HMACLedger(ledger_dir=tmp_path / "verification", case_id=_CASE_ID)
    key = _key()
    entry = led.append(key, "F-001 ", LedgerItemType.FINDING, _CONTENT, "aj")
    assert entry.item_id == "F-001 "  # NOT stripped to "F-001"
    assert led.verify_entry(key, entry, _CONTENT) is True


def test_ledger_entry_rejects_nul_in_item_id() -> None:
    """item_id with embedded NUL must fail validation — otherwise an attacker
    could craft an item_id that collides with the canonical-message
    separator and forge a verifier-passing entry."""
    from pydantic import ValidationError as _ValidationError

    valid_hex = "a" * 64
    with pytest.raises(_ValidationError):
        LedgerEntry(
            ts=_FIXED_NOW,
            item_id="F-001\x00wrong",
            item_type=LedgerItemType.FINDING,
            content_hash=valid_hex,
            hmac=valid_hex,
            examiner="aj",
        )


def test_append_preserves_jsonl_with_unicode_examiner(tmp_path: Path) -> None:
    """Pydantic model_dump_json uses ensure_ascii=False — unicode round-trips."""
    led = HMACLedger(ledger_dir=tmp_path / "verification", case_id=_CASE_ID)
    entry = led.append(_key(), "F-001", LedgerItemType.FINDING, _CONTENT, "島田")
    parsed = json.loads(led.ledger_path.read_text(encoding="utf-8").rstrip("\n"))
    assert parsed["examiner"] == "島田"
    assert led.verify_entry(_key(), entry, _CONTENT) is True
