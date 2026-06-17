"""Regression coverage for approving normal prose containing commas."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from silentwitness_agent.cli import app
from tests.integration._helpers_status import init_case

runner = CliRunner()


def _write_case_yaml(case_dir: Path) -> None:
    (case_dir / "CASE.yaml").write_text(
        yaml.safe_dump({"salt_hex": "deadbeef" * 8}),
        encoding="utf-8",
    )


def _write_draft_finding(case_dir: Path) -> None:
    records = [
        {
            "observation_id": "O-001",
            "text": "Prefetch record shows Dropbox, GoogleDriveFS, and OneDrive activity",
            "audit_ids": ["sift-001-20260602-014"],
            "interpretations": [
                {
                    "interpretation_id": "I-001",
                    "text": "The record indicates cloud-sync activity, with caveats",
                    "confidence": "HIGH",
                }
            ],
        },
        {
            "finding_id": "F-001",
            "observation_id": "O-001",
            "interpretation_id": "I-001",
            "status": "DRAFT",
            "staged_at": "2026-01-01T12:00:00+00:00",
        },
    ]
    (case_dir / "findings.json").write_text(json.dumps(records), encoding="utf-8")


def test_approve_allows_commas_in_finding_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_dir = init_case(tmp_path, "mr-ap-comma-001", monkeypatch)
    _write_case_yaml(case_dir)
    _write_draft_finding(case_dir)
    ledger_dir = tmp_path / "verification"
    ledger_dir.mkdir(mode=0o700)
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", "demo-password")

    result = runner.invoke(
        app,
        ["approve", "mr-ap-comma-001", "F-001", "--ledger", str(ledger_dir)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert "F-001 APPROVED" in result.output
    assert "PIPELINE_INTERNAL_ERROR" not in result.output
    assert (case_dir / "report.md").exists()
