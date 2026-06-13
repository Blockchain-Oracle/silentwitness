"""`approve --non-interactive` — password from env, not a TTY (headless demo)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from silentwitness_agent.cli import app
from tests.integration._helpers_status import init_case
from tests.integration.test_cli_approve import (
    _make_ledger_dir,
    _write_case_yaml,
    _write_draft_finding,
)

runner = CliRunner()


def test_approve_non_interactive_with_env_password(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--non-interactive takes the password from SILENTWITNESS_APPROVE_PASSWORD (no TTY)."""
    case_dir = init_case(tmp_path, "mr-ni-001", monkeypatch)
    _write_case_yaml(case_dir, with_verifier=False)  # salt only — password is the HMAC key
    _write_draft_finding(case_dir)
    ledger_dir = _make_ledger_dir(tmp_path)
    monkeypatch.delenv("_SILENTWITNESS_TEST_PASSWORD", raising=False)
    monkeypatch.setenv("SILENTWITNESS_APPROVE_PASSWORD", "hmac-key-pw")
    result = runner.invoke(
        app,
        ["approve", "mr-ni-001", "F-001", "--ledger", str(ledger_dir), "--non-interactive"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert "F-001 APPROVED" in result.output
    findings = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    f = next(x for x in findings if isinstance(x, dict) and x.get("finding_id") == "F-001")
    assert f["status"] == "APPROVED"


def test_approve_non_interactive_without_password_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_dir = init_case(tmp_path, "mr-ni-002", monkeypatch)
    _write_case_yaml(case_dir, with_verifier=False)
    _write_draft_finding(case_dir)
    ledger_dir = _make_ledger_dir(tmp_path)
    monkeypatch.delenv("_SILENTWITNESS_TEST_PASSWORD", raising=False)
    monkeypatch.delenv("SILENTWITNESS_APPROVE_PASSWORD", raising=False)
    result = runner.invoke(
        app,
        ["approve", "mr-ni-002", "F-001", "--ledger", str(ledger_dir), "--non-interactive"],
        catch_exceptions=False,
    )
    assert result.exit_code == 2
