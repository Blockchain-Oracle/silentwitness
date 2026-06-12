"""Security and audit coverage tests for `silentwitness approve` (scenarios 10-13)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from silentwitness_agent.cli import app
from tests.integration._helpers_status import init_case
from tests.integration.test_cli_approve import (
    _CORRECT_PW,
    _WRONG_PW,
    _make_ledger_dir,
    _write_case_yaml,
    _write_draft_finding,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# 10. Password not echoed in stdout/stderr
# ---------------------------------------------------------------------------


def test_approve_password_not_echoed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Password must not appear in stdout or stderr output."""
    case_dir = init_case(tmp_path, "mr-ap-echo-001", monkeypatch)
    _write_draft_finding(case_dir)
    secret = "super-secret-pw-xyz"  # noqa: S105  # pragma: allowlist secret
    _write_case_yaml(case_dir, password=secret)
    ledger_dir = _make_ledger_dir(tmp_path)
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", secret)
    result = runner.invoke(
        app,
        ["approve", "mr-ap-echo-001", "F-001", "--ledger", str(ledger_dir)],
        catch_exceptions=False,
    )
    assert secret not in result.output
    assert secret not in (result.stderr or "")


# ---------------------------------------------------------------------------
# 11. Password not written to cli.jsonl
# ---------------------------------------------------------------------------


def test_approve_password_not_in_audit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """cli.jsonl approve entry must contain no password field."""
    case_dir = init_case(tmp_path, "mr-ap-audit-001", monkeypatch)
    _write_case_yaml(case_dir)
    _write_draft_finding(case_dir)
    ledger_dir = _make_ledger_dir(tmp_path)
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _CORRECT_PW)
    runner.invoke(
        app,
        ["approve", "mr-ap-audit-001", "F-001", "--ledger", str(ledger_dir)],
        catch_exceptions=False,
    )
    cli_log = case_dir / "audit" / "cli.jsonl"
    assert cli_log.is_file()
    lines = [ln for ln in cli_log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    approve_entry = next(
        (json.loads(ln) for ln in lines if json.loads(ln).get("tool") == "cli.approve"),
        None,
    )
    assert approve_entry is not None
    assert "password" not in approve_entry
    assert _CORRECT_PW not in json.dumps(approve_entry)


# ---------------------------------------------------------------------------
# 12. Three wrong password attempts each emit a cli.jsonl entry
# ---------------------------------------------------------------------------


def test_approve_wrong_attempts_audit_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Three wrong passwords each produce a cli.jsonl entry with outcome=error_INVALID_PASSWORD."""
    case_dir = init_case(tmp_path, "mr-ap-audit3-001", monkeypatch)
    _write_case_yaml(case_dir)
    _write_draft_finding(case_dir)
    ledger_dir = _make_ledger_dir(tmp_path)
    monkeypatch.setattr(
        "silentwitness_agent.cli_commands.approve._read_password",
        lambda prompt="examiner password: ": _WRONG_PW,
    )
    runner.invoke(
        app,
        ["approve", "mr-ap-audit3-001", "F-001", "--ledger", str(ledger_dir)],
        catch_exceptions=False,
    )
    cli_log = case_dir / "audit" / "cli.jsonl"
    lines = [ln for ln in cli_log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    invalid_pw_entries = [
        json.loads(ln) for ln in lines if json.loads(ln).get("outcome") == "error_INVALID_PASSWORD"
    ]
    assert len(invalid_pw_entries) == 3


# ---------------------------------------------------------------------------
# 13. --note flag stored in findings.json
# ---------------------------------------------------------------------------


def test_approve_note_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--note text is stored as approval_note in findings.json after approval."""
    case_dir = init_case(tmp_path, "mr-ap-note-001", monkeypatch)
    _write_case_yaml(case_dir)
    _write_draft_finding(case_dir)
    ledger_dir = _make_ledger_dir(tmp_path)
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _CORRECT_PW)
    result = runner.invoke(
        app,
        [
            "approve",
            "mr-ap-note-001",
            "F-001",
            "--ledger",
            str(ledger_dir),
            "--note",
            "matches HKLM reg key",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    findings = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    f = next(x for x in findings if isinstance(x, dict) and x.get("finding_id") == "F-001")
    assert f.get("approval_note") == "matches HKLM reg key"
