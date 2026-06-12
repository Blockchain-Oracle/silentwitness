"""Integration tests for `silentwitness verify` — ≥11 BDD scenarios."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from silentwitness_agent.cli import app
from silentwitness_common.types import Confidence, LedgerItemType
from silentwitness_mcp.audit.ledger import (
    HMACLedger,
    InterpretationParts,
    LedgerComposer,
    ObservationParts,
)
from tests.integration._helpers_status import init_case

runner = CliRunner()

_SALT_HEX = "deadbeef" * 8
_PASSWORD = "examiner-secret-pw"  # noqa: S105  # pragma: allowlist secret
_WRONG_PW = "wrong-password"

_OBS_ID = "O-001"
_OBS_TEXT = "Ethereal was present on the filesystem"
_AUDIT_IDS: tuple[str, ...] = ("sift-001-20260602-014",)
_INTERP_ID = "I-001"
_INTERP_TEXT = "wardriving activity consistent with network sniffing"
_INTERP_CONF = "HIGH"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_case(tmp_path: Path, case_id: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    case_dir = init_case(tmp_path, case_id, monkeypatch)
    (case_dir / "CASE.yaml").write_text(f"salt_hex: {_SALT_HEX}\n", encoding="utf-8")
    return case_dir


def _make_ledger_dir(tmp_path: Path) -> Path:
    d = tmp_path / "verification"
    d.mkdir(mode=0o700)
    return d


def _findings_data(
    finding_id: str = "F-001",
    obs_text: str = _OBS_TEXT,
    status: str = "APPROVED",
) -> list[object]:
    return [
        {
            "observation_id": _OBS_ID,
            "text": obs_text,
            "audit_ids": list(_AUDIT_IDS),
            "interpretations": [
                {
                    "observation_id": _OBS_ID,
                    "interpretation_id": _INTERP_ID,
                    "text": _INTERP_TEXT,
                    "confidence": _INTERP_CONF,
                }
            ],
        },
        {
            "finding_id": finding_id,
            "observation_id": _OBS_ID,
            "interpretation_id": _INTERP_ID,
            "status": status,
            "staged_at": "2026-01-01T12:00:00+00:00",
        },
    ]


def _content_bytes() -> bytes:
    obs_parts = ObservationParts(text=_OBS_TEXT, audit_ids=_AUDIT_IDS)
    interp_parts = InterpretationParts(
        observation_id=_OBS_ID,
        text=_INTERP_TEXT,
        confidence=Confidence(_INTERP_CONF),
    )
    return LedgerComposer.finding(obs_parts, interp_parts)


def _sign_entry(ledger_dir: Path, case_id: str, finding_id: str = "F-001") -> None:
    """Append a correctly-signed ledger entry using the test password and salt."""
    salt = bytes.fromhex(_SALT_HEX)
    ledger = HMACLedger(ledger_dir=ledger_dir, case_id=case_id)
    key = ledger.derive_key(_PASSWORD, salt)
    ledger.append(key, finding_id, LedgerItemType.FINDING, _content_bytes(), "examiner")


# ---------------------------------------------------------------------------
# 1. All entries VERIFIED → exit 0, "ledger intact" summary
# ---------------------------------------------------------------------------


def test_verify_all_verified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Correct password with intact findings.json exits 0 with VERIFIED table."""
    case_dir = _make_case(tmp_path, "mr-v-001", monkeypatch)
    (case_dir / "findings.json").write_text(json.dumps(_findings_data()), encoding="utf-8")
    ledger_dir = _make_ledger_dir(tmp_path)
    _sign_entry(ledger_dir, "mr-v-001")
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _PASSWORD)
    result = runner.invoke(
        app, ["verify", "mr-v-001", "--ledger", str(ledger_dir)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "VERIFIED" in result.output
    assert "ledger intact" in result.output
    assert "PBKDF2-SHA256" in result.output
    assert "window:" in result.output


# ---------------------------------------------------------------------------
# 2. Tampered finding text → DESCRIPTION_MISMATCH, exit 1
# ---------------------------------------------------------------------------


def test_verify_tampered_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutating obs text in findings.json after signing produces DESCRIPTION_MISMATCH."""
    case_dir = _make_case(tmp_path, "mr-v-002", monkeypatch)
    ledger_dir = _make_ledger_dir(tmp_path)
    (case_dir / "findings.json").write_text(json.dumps(_findings_data()), encoding="utf-8")
    _sign_entry(ledger_dir, "mr-v-002")
    # Mutate the observation text after signing.
    (case_dir / "findings.json").write_text(
        json.dumps(_findings_data(obs_text="TAMPERED text")), encoding="utf-8"
    )
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _PASSWORD)
    result = runner.invoke(
        app, ["verify", "mr-v-002", "--ledger", str(ledger_dir)], catch_exceptions=False
    )
    assert result.exit_code == 1
    assert "DESCRIPTION_MISMATCH" in result.output
    assert "verification FAILED" in result.output


# ---------------------------------------------------------------------------
# 3. Tampered ledger HMAC field → DESCRIPTION_MISMATCH
# ---------------------------------------------------------------------------


def test_verify_tampered_ledger_hmac(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Flipping a digit in the HMAC field of the ledger produces DESCRIPTION_MISMATCH."""
    case_dir = _make_case(tmp_path, "mr-v-003", monkeypatch)
    ledger_dir = _make_ledger_dir(tmp_path)
    (case_dir / "findings.json").write_text(json.dumps(_findings_data()), encoding="utf-8")
    _sign_entry(ledger_dir, "mr-v-003")
    # Flip one hex digit in the stored HMAC.
    ledger_file = ledger_dir / "mr-v-003.jsonl"
    entry = json.loads(ledger_file.read_text(encoding="utf-8").strip())
    entry["hmac"] = entry["hmac"][:-1] + ("0" if entry["hmac"][-1] != "0" else "1")
    ledger_file.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _PASSWORD)
    result = runner.invoke(
        app, ["verify", "mr-v-003", "--ledger", str(ledger_dir)], catch_exceptions=False
    )
    assert result.exit_code == 1
    assert "DESCRIPTION_MISMATCH" in result.output


# ---------------------------------------------------------------------------
# 4. APPROVED finding with no ledger entry → APPROVED_NO_VERIFICATION
# ---------------------------------------------------------------------------


def test_verify_approved_no_verification(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """APPROVED finding absent from ledger produces APPROVED_NO_VERIFICATION, exit 1."""
    case_dir = _make_case(tmp_path, "mr-v-004", monkeypatch)
    ledger_dir = _make_ledger_dir(tmp_path)
    # Sign only F-001, but also have APPROVED F-002 with no ledger entry.
    both = [
        *_findings_data("F-001"),
        {
            "finding_id": "F-002",
            "observation_id": _OBS_ID,
            "interpretation_id": _INTERP_ID,
            "status": "APPROVED",
            "staged_at": "2026-01-01T13:00:00+00:00",
        },
    ]
    (case_dir / "findings.json").write_text(json.dumps(both), encoding="utf-8")
    _sign_entry(ledger_dir, "mr-v-004", "F-001")
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _PASSWORD)
    result = runner.invoke(
        app, ["verify", "mr-v-004", "--ledger", str(ledger_dir)], catch_exceptions=False
    )
    assert result.exit_code == 1
    assert "APPROVED_NO_VERIFICATION" in result.output
    assert "F-002" in result.output


# ---------------------------------------------------------------------------
# 5. Ledger entry references nonexistent finding → VERIFICATION_NO_FINDING
# ---------------------------------------------------------------------------


def test_verify_no_finding_for_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ledger entry whose item_id is absent from findings.json → VERIFICATION_NO_FINDING."""
    case_dir = _make_case(tmp_path, "mr-v-005", monkeypatch)
    ledger_dir = _make_ledger_dir(tmp_path)
    (case_dir / "findings.json").write_text(json.dumps(_findings_data("F-001")), encoding="utf-8")
    # Sign F-999 which doesn't exist in findings.json.
    _sign_entry(ledger_dir, "mr-v-005", "F-999")
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _PASSWORD)
    result = runner.invoke(
        app, ["verify", "mr-v-005", "--ledger", str(ledger_dir)], catch_exceptions=False
    )
    assert result.exit_code == 1
    assert "VERIFICATION_NO_FINDING" in result.output
    assert "F-999" in result.output


# ---------------------------------------------------------------------------
# 6. Wrong password → all DESCRIPTION_MISMATCH + wrong-password hint
# ---------------------------------------------------------------------------


def test_verify_wrong_password(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Wrong password causes all entries to fail with possible-wrong-password hint."""
    case_dir = _make_case(tmp_path, "mr-v-006", monkeypatch)
    ledger_dir = _make_ledger_dir(tmp_path)
    (case_dir / "findings.json").write_text(json.dumps(_findings_data()), encoding="utf-8")
    _sign_entry(ledger_dir, "mr-v-006")
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _WRONG_PW)
    result = runner.invoke(
        app, ["verify", "mr-v-006", "--ledger", str(ledger_dir)], catch_exceptions=False
    )
    assert result.exit_code == 1
    assert "DESCRIPTION_MISMATCH" in result.output
    assert "wrong password" in result.output.lower()


# ---------------------------------------------------------------------------
# 7. No ledger entries (no approvals yet) → exit 0, informational message
# ---------------------------------------------------------------------------


def test_verify_no_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty ledger exits 0 with an informational 'no entries to verify' message."""
    _make_case(tmp_path, "mr-v-007", monkeypatch)
    ledger_dir = _make_ledger_dir(tmp_path)
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _PASSWORD)
    result = runner.invoke(
        app, ["verify", "mr-v-007", "--ledger", str(ledger_dir)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "no entries to verify" in result.output


# ---------------------------------------------------------------------------
# 8. --strict exits 3 on any mismatch
# ---------------------------------------------------------------------------


def test_verify_strict_exits_3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--strict flag changes exit code from 1 to 3 when any entry fails."""
    case_dir = _make_case(tmp_path, "mr-v-008", monkeypatch)
    ledger_dir = _make_ledger_dir(tmp_path)
    (case_dir / "findings.json").write_text(json.dumps(_findings_data()), encoding="utf-8")
    _sign_entry(ledger_dir, "mr-v-008")
    (case_dir / "findings.json").write_text(
        json.dumps(_findings_data(obs_text="TAMPERED")), encoding="utf-8"
    )
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _PASSWORD)
    result = runner.invoke(
        app,
        ["verify", "mr-v-008", "--ledger", str(ledger_dir), "--strict"],
        catch_exceptions=False,
    )
    assert result.exit_code == 3
    assert "verification FAILED" in result.output


# ---------------------------------------------------------------------------
# 9. Case not found → exit 1, stderr contains case id
# ---------------------------------------------------------------------------


def test_verify_case_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-existent case exits 1 with the case id in stderr."""
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    result = runner.invoke(app, ["verify", "mr-v-no-case"], catch_exceptions=False)
    assert result.exit_code == 1
    assert "mr-v-no-case" in result.stderr


# ---------------------------------------------------------------------------
# 10. Derived key is zeroed after the verify run (HMACLedger.zero_key called)
# ---------------------------------------------------------------------------


def test_verify_key_zeroed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """HMACLedger.zero_key is called exactly once after the verify loop."""
    zero_key_calls: list[int] = []
    original = HMACLedger.zero_key

    def patched(buf: bytearray) -> None:
        zero_key_calls.append(len(buf))
        original(buf)

    monkeypatch.setattr(HMACLedger, "zero_key", staticmethod(patched))
    case_dir = _make_case(tmp_path, "mr-v-010", monkeypatch)
    ledger_dir = _make_ledger_dir(tmp_path)
    (case_dir / "findings.json").write_text(json.dumps(_findings_data()), encoding="utf-8")
    _sign_entry(ledger_dir, "mr-v-010")
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _PASSWORD)
    runner.invoke(app, ["verify", "mr-v-010", "--ledger", str(ledger_dir)], catch_exceptions=False)
    assert len(zero_key_calls) == 1
    assert zero_key_calls[0] == 32  # 32-byte derived key


# ---------------------------------------------------------------------------
# 11. Rich table renders per-entry rows with outcome column
# ---------------------------------------------------------------------------


def test_verify_table_renders_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Output contains the finding_id in a table row alongside its outcome."""
    case_dir = _make_case(tmp_path, "mr-v-011", monkeypatch)
    ledger_dir = _make_ledger_dir(tmp_path)
    (case_dir / "findings.json").write_text(json.dumps(_findings_data("F-001")), encoding="utf-8")
    _sign_entry(ledger_dir, "mr-v-011")
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _PASSWORD)
    result = runner.invoke(
        app, ["verify", "mr-v-011", "--ledger", str(ledger_dir)], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "F-001" in result.output
    assert "finding" in result.output
    assert "VERIFIED" in result.output
