"""Regression coverage for review-list next-step guidance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from silentwitness_agent.cli import app
from tests.integration._helpers_status import init_case

runner = CliRunner()


def _write_findings(case_dir: Path) -> None:
    data: list[dict[str, Any]] = [
        {
            "observation_id": "O-001",
            "text": "Observation text: suspicious cloud-sync shortcut",
            "audit_ids": ["sift-001"],
            "interpretations": [
                {
                    "interpretation_id": "I-001",
                    "text": "Interpretation text: candidate exfiltration staging",
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
    (case_dir / "findings.json").write_text(json.dumps(data), encoding="utf-8")


def test_review_list_prints_inspect_and_approve_next_steps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_dir = init_case(tmp_path, "mr-review-next-001", monkeypatch)
    _write_findings(case_dir)

    result = runner.invoke(app, ["review", "mr-review-next-001"], catch_exceptions=False)

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "silentwitness review mr-review-next-001 --finding-id F-001" in output
    assert "silentwitness approve mr-review-next-001 F-001" in output
