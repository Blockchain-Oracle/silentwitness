"""Integration tests for `silentwitness verify` — error paths and edge cases."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from silentwitness_agent.cli import app
from silentwitness_agent.cli_commands.verify import _NoTTYError
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

_OBS_ID = "O-001"
_OBS_TEXT = "Ethereal was present on the filesystem"
_AUDIT_IDS: tuple[str, ...] = ("sift-001-20260602-014",)
_INTERP_ID = "I-001"
_INTERP_TEXT = "wardriving activity consistent with network sniffing"
_INTERP_CONF = "HIGH"


def _make_case(tmp_path: Path, case_id: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    case_dir = init_case(tmp_path, case_id, monkeypatch)
    (case_dir / "CASE.yaml").write_text(f"salt_hex: {_SALT_HEX}\n", encoding="utf-8")
    return case_dir


def _make_ledger_dir(tmp_path: Path, *, mode: int = 0o700) -> Path:
    d = tmp_path / "verification"
    d.mkdir(mode=mode)
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


def _sign_entry(ledger_dir: Path, case_id: str, finding_id: str = "F-001") -> None:
    salt = bytes.fromhex(_SALT_HEX)
    ledger = HMACLedger(ledger_dir=ledger_dir, case_id=case_id)
    key = ledger.derive_key(_PASSWORD, salt)
    obs_parts = ObservationParts(text=_OBS_TEXT, audit_ids=_AUDIT_IDS)
    interp_parts = InterpretationParts(
        observation_id=_OBS_ID,
        text=_INTERP_TEXT,
        confidence=Confidence(_INTERP_CONF),
    )
    content = LedgerComposer.finding(obs_parts, interp_parts)
    ledger.append(key, finding_id, LedgerItemType.FINDING, content, "examiner")


# ---------------------------------------------------------------------------
# 12. CASE_SALT_MISSING — CASE.yaml present but no salt_hex key
# ---------------------------------------------------------------------------


def test_verify_case_salt_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CASE.yaml without salt_hex exits 2 with CASE_SALT_MISSING in stderr."""
    case_dir = init_case(tmp_path, "mr-ve-012", monkeypatch)
    (case_dir / "CASE.yaml").write_text("other_field: value\n", encoding="utf-8")
    ledger_dir = _make_ledger_dir(tmp_path)
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _PASSWORD)
    result = runner.invoke(
        app, ["verify", "mr-ve-012", "--ledger", str(ledger_dir)], catch_exceptions=False
    )
    assert result.exit_code == 2
    assert "CASE_SALT_MISSING" in result.stderr


# ---------------------------------------------------------------------------
# 13. CASE_SALT_MALFORMED — invalid hex in salt_hex
# ---------------------------------------------------------------------------


def test_verify_case_salt_malformed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CASE.yaml with non-hex salt_hex exits 2 with CASE_SALT_MALFORMED in stderr."""
    case_dir = init_case(tmp_path, "mr-ve-013", monkeypatch)
    (case_dir / "CASE.yaml").write_text("salt_hex: not-valid-hex!\n", encoding="utf-8")
    ledger_dir = _make_ledger_dir(tmp_path)
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _PASSWORD)
    result = runner.invoke(
        app, ["verify", "mr-ve-013", "--ledger", str(ledger_dir)], catch_exceptions=False
    )
    assert result.exit_code == 2
    assert "CASE_SALT_MALFORMED" in result.stderr


# ---------------------------------------------------------------------------
# 14. LEDGER_DIR_PERMISSIONS_WEAK — ledger dir is group/world readable
# ---------------------------------------------------------------------------


def test_verify_ledger_dir_permissions_weak(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ledger dir with mode 0o755 exits 2 with LEDGER_DIR_PERMISSIONS_WEAK in stderr."""
    _make_case(tmp_path, "mr-ve-014", monkeypatch)
    ledger_dir = _make_ledger_dir(tmp_path, mode=0o755)
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _PASSWORD)
    result = runner.invoke(
        app, ["verify", "mr-ve-014", "--ledger", str(ledger_dir)], catch_exceptions=False
    )
    assert result.exit_code == 2
    assert "LEDGER_DIR_PERMISSIONS_WEAK" in result.stderr


# ---------------------------------------------------------------------------
# 15. LEDGER_CORRUPT — blank line appended to the ledger JSONL
# ---------------------------------------------------------------------------


def test_verify_ledger_corrupt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A blank line in the ledger JSONL exits 2 with LEDGER_CORRUPT in stderr."""
    case_dir = _make_case(tmp_path, "mr-ve-015", monkeypatch)
    ledger_dir = _make_ledger_dir(tmp_path)
    (case_dir / "findings.json").write_text(json.dumps(_findings_data()), encoding="utf-8")
    _sign_entry(ledger_dir, "mr-ve-015")
    # Corrupt the ledger by appending a blank line.
    ledger_file = ledger_dir / "mr-ve-015.jsonl"
    ledger_file.write_text(ledger_file.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _PASSWORD)
    result = runner.invoke(
        app, ["verify", "mr-ve-015", "--ledger", str(ledger_dir)], catch_exceptions=False
    )
    assert result.exit_code == 2
    assert "LEDGER_CORRUPT" in result.stderr


# ---------------------------------------------------------------------------
# 16. No-TTY path — verify requires interactive terminal
# ---------------------------------------------------------------------------


def test_verify_no_tty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Monkeypatching _read_password to raise _NoTTYError exits 2 with TTY hint in stderr."""
    case_dir = _make_case(tmp_path, "mr-ve-016", monkeypatch)
    ledger_dir = _make_ledger_dir(tmp_path)
    (case_dir / "findings.json").write_text(json.dumps(_findings_data()), encoding="utf-8")
    _sign_entry(ledger_dir, "mr-ve-016")

    def _raise_no_tty(prompt: str = "") -> str:
        raise _NoTTYError()

    monkeypatch.setattr("silentwitness_agent.cli_commands.verify._read_password", _raise_no_tty)
    result = runner.invoke(
        app, ["verify", "mr-ve-016", "--ledger", str(ledger_dir)], catch_exceptions=False
    )
    assert result.exit_code == 2
    assert "TTY" in result.stderr


# ---------------------------------------------------------------------------
# 17. KeyboardInterrupt during password prompt → exit 130
# ---------------------------------------------------------------------------


def test_verify_keyboard_interrupt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """KeyboardInterrupt from _read_password exits 130."""
    case_dir = _make_case(tmp_path, "mr-ve-017", monkeypatch)
    ledger_dir = _make_ledger_dir(tmp_path)
    (case_dir / "findings.json").write_text(json.dumps(_findings_data()), encoding="utf-8")
    _sign_entry(ledger_dir, "mr-ve-017")

    def _raise_interrupt(prompt: str = "") -> str:
        raise KeyboardInterrupt()

    monkeypatch.setattr("silentwitness_agent.cli_commands.verify._read_password", _raise_interrupt)
    result = runner.invoke(
        app, ["verify", "mr-ve-017", "--ledger", str(ledger_dir)], catch_exceptions=False
    )
    assert result.exit_code == 130


# ---------------------------------------------------------------------------
# 18. Mixed outcomes — some VERIFIED, some DESCRIPTION_MISMATCH
# ---------------------------------------------------------------------------


def test_verify_mixed_outcomes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Partial tamper: one VERIFIED entry and one DESCRIPTION_MISMATCH in the same run."""
    case_dir = _make_case(tmp_path, "mr-ve-018", monkeypatch)
    ledger_dir = _make_ledger_dir(tmp_path)

    # Two findings that share obs+interp — sign both, then tamper F-001's HMAC in the ledger.
    findings: list[object] = [
        *_findings_data("F-001"),
        {
            "finding_id": "F-002",
            "observation_id": _OBS_ID,
            "interpretation_id": _INTERP_ID,
            "status": "APPROVED",
            "staged_at": "2026-01-01T13:00:00+00:00",
        },
    ]
    (case_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
    _sign_entry(ledger_dir, "mr-ve-018", "F-001")
    _sign_entry(ledger_dir, "mr-ve-018", "F-002")

    # Flip one hex digit in F-001's HMAC (first line) so only that entry fails.
    ledger_file = ledger_dir / "mr-ve-018.jsonl"
    lines = ledger_file.read_text(encoding="utf-8").strip().splitlines()
    entry_0 = json.loads(lines[0])
    hmac_val = entry_0["hmac"]
    entry_0["hmac"] = hmac_val[:-1] + ("0" if hmac_val[-1] != "0" else "1")
    lines[0] = json.dumps(entry_0)
    ledger_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _PASSWORD)
    result = runner.invoke(
        app, ["verify", "mr-ve-018", "--ledger", str(ledger_dir)], catch_exceptions=False
    )
    assert result.exit_code == 1
    assert "VERIFIED" in result.output
    assert "DESCRIPTION_MISMATCH" in result.output
    # Wrong-password hint must NOT fire (only one of two entries failed).
    assert "wrong password" not in result.output.lower()
    assert "1/2" in result.output
