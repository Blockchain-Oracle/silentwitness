"""Hypothesis property tests for HMACLedger invariants."""

from __future__ import annotations

import tempfile
from pathlib import Path

from hypothesis import given, settings, strategies as st

from silentwitness_common.types import LedgerItemType
from silentwitness_mcp.audit.ledger import HMACLedger

_SALT = b"\x00" * 16
# Restrict examiner / item_id alphabet to AuditEntry-safe chars (no line
# terminators — append_jsonl_line rejects them; Pydantic str_strip_whitespace
# rejects pure-whitespace).
_FIELD_TEXT = st.text(
    alphabet=st.characters(blacklist_categories=("Cc", "Cs", "Zl", "Zp")),
    min_size=1,
    max_size=20,
).filter(lambda s: s.strip())


@given(password=st.text(min_size=1, max_size=40), salt=st.binary(min_size=8, max_size=32))
@settings(max_examples=8, deadline=None)
def test_derive_key_is_deterministic(password: str, salt: bytes) -> None:
    """For any (password, salt), derive_key returns the same 32 bytes twice."""
    k1 = HMACLedger.derive_key(password, salt)
    k2 = HMACLedger.derive_key(password, salt)
    assert k1 == k2
    assert len(k1) == 32


@given(message=st.binary(min_size=0, max_size=4096))
@settings(max_examples=15, deadline=None)
def test_round_trip_verify_succeeds_for_any_message(message: bytes) -> None:
    """For any byte payload, sign-then-verify with the same key always passes."""
    key = HMACLedger.derive_key("p", _SALT)
    hex_ = HMACLedger.compute_hmac(key, message)
    assert HMACLedger.verify_hmac(key, message, hex_) is True


@given(
    password_a=st.text(min_size=1, max_size=20),
    password_b=st.text(min_size=1, max_size=20),
    message=st.binary(min_size=1, max_size=512),
)
@settings(max_examples=10, deadline=None)
def test_wrong_key_never_verifies(password_a: str, password_b: str, message: bytes) -> None:
    """For any two distinct passwords, a signature with A never verifies under B."""
    if password_a == password_b:
        return  # vacuous case
    key_a = HMACLedger.derive_key(password_a, _SALT)
    key_b = HMACLedger.derive_key(password_b, _SALT)
    hex_ = HMACLedger.compute_hmac(key_a, message)
    assert HMACLedger.verify_hmac(key_b, message, hex_) is False


@given(item_ids=st.lists(_FIELD_TEXT, min_size=1, max_size=8, unique=True))
@settings(max_examples=8, deadline=None)
def test_append_read_all_round_trip_preserves_order(item_ids: list[str]) -> None:
    """For any sequence of distinct item_ids, append-then-read_all preserves
    insertion order AND every entry verifies under the key it was signed with."""
    with tempfile.TemporaryDirectory() as raw:
        ledger_dir = Path(raw) / "verification"
        led = HMACLedger(ledger_dir=ledger_dir, case_id="cprop")
        key = HMACLedger.derive_key("p", _SALT)
        contents = {item_id: f"content for {item_id}".encode() for item_id in item_ids}
        emitted = [
            led.append(key, item_id, LedgerItemType.FINDING, contents[item_id], "aj")
            for item_id in item_ids
        ]
        listed = led.read_all()
        assert listed == emitted
        for entry, item_id in zip(listed, item_ids, strict=True):
            assert led.verify_entry(key, entry, contents[item_id]) is True


@given(
    content=st.binary(min_size=1, max_size=512),
    tamper_offset=st.integers(min_value=0, max_value=511),
)
@settings(max_examples=10, deadline=None)
def test_single_byte_tamper_in_content_bytes_always_fails_verify(
    content: bytes, tamper_offset: int
) -> None:
    """Silent-failure detection: flipping any single bit in content_bytes
    must invalidate verification. The bit-rot detector contract."""
    if tamper_offset >= len(content):
        return  # vacuous case
    with tempfile.TemporaryDirectory() as raw:
        ledger_dir = Path(raw) / "verification"
        led = HMACLedger(ledger_dir=ledger_dir, case_id="ctamp")
        key = HMACLedger.derive_key("p", _SALT)
        entry = led.append(key, "F-001", LedgerItemType.FINDING, content, "aj")
        flipped = bytes([content[tamper_offset] ^ 0x01])
        tampered = content[:tamper_offset] + flipped + content[tamper_offset + 1 :]
        assert led.verify_entry(key, entry, tampered) is False
