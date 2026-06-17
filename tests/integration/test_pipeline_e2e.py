"""End-to-end regression guard for the back-half pipeline.

This is the test whose ABSENCE let the disconnected pipeline ship: nothing
exercised observation → materialize → review → approve → report through the live
CLI. It runs the real commands (no model, no forensic binaries) and asserts a
populated report.md comes out the other end.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from silentwitness_agent.cli import app
from silentwitness_agent.critic import CriticReport
from silentwitness_agent.report.template import ReportStatus, parse_frontmatter
from tests.integration._helpers_status import init_case

runner = CliRunner()


def _seed_observation(case_dir: Path) -> None:
    """Simulate a completed investigate: one observation + interpretation, but
    NO Finding record (record_observation never materializes findings)."""
    records = [
        {
            "observation_id": "O-001",
            "text": "weird.log shows a bad_HTTP_request to an external host",
            "audit_ids": ["sift-e2e-20260613-001"],
            "interpretations": [
                {
                    "interpretation_id": "I-001",
                    "text": "non-standard HTTP consistent with C2 beaconing",
                    "confidence": "MEDIUM",
                }
            ],
        }
    ]
    (case_dir / "findings.json").write_text(json.dumps(records), encoding="utf-8")


async def _no_op_critique(*_args: object, **_kwargs: object) -> CriticReport:
    """Deterministic critic stub — keeps the materialized DRAFT (no model call)."""
    return CriticReport(verdicts=[], tokens_spent=0, time_elapsed_ms=0.0)


def test_observation_materializes_through_review_to_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_dir = init_case(tmp_path, "pipe-e2e-001", monkeypatch)
    # init now writes CASE.yaml with a salt (required by approve).
    assert (case_dir / "CASE.yaml").exists(), "init must create CASE.yaml salt"
    _seed_observation(case_dir)
    monkeypatch.setattr("silentwitness_agent.critic.critique", _no_op_critique)

    # --- review: materializes a DRAFT Finding from the observation ---
    review_res = runner.invoke(app, ["review", "pipe-e2e-001"], catch_exceptions=False)
    assert review_res.exit_code == 0, review_res.output
    findings = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    finding = next((f for f in findings if isinstance(f, dict) and f.get("finding_id")), None)
    assert finding is not None, "review did not materialize a Finding record"
    assert finding["status"] == "DRAFT"
    assert finding["observation_id"] == "O-001"
    assert finding["interpretation_id"] == "I-001"
    fid = finding["finding_id"]
    assert fid in review_res.output  # appears in the review table

    # --- approve: promotes to APPROVED + renders report.md ---
    ledger_dir = tmp_path / "verification"
    ledger_dir.mkdir(mode=0o700)
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", "examiner-pw")
    approve_res = runner.invoke(
        app,
        ["approve", "pipe-e2e-001", fid, "--ledger", str(ledger_dir)],
        catch_exceptions=False,
    )
    assert approve_res.exit_code == 0, approve_res.output
    assert f"{fid} APPROVED" in approve_res.output
    assert "report.md updated" in approve_res.output

    # --- report.md is populated with the approved finding ---
    report = (case_dir / "report.md").read_text(encoding="utf-8")
    frontmatter, _ = parse_frontmatter(report)
    assert "## Findings" in report
    assert "bad_HTTP_request" in report, "approved observation text missing from report"
    assert frontmatter.status == ReportStatus.REVIEWED
    findings_after = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    approved = next(f for f in findings_after if f.get("finding_id") == fid)
    assert approved["status"] == "APPROVED"


def test_review_is_idempotent_no_duplicate_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_dir = init_case(tmp_path, "pipe-e2e-002", monkeypatch)
    _seed_observation(case_dir)
    monkeypatch.setattr("silentwitness_agent.critic.critique", _no_op_critique)
    runner.invoke(app, ["review", "pipe-e2e-002"], catch_exceptions=False)
    runner.invoke(app, ["review", "pipe-e2e-002"], catch_exceptions=False)
    findings = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    finding_count = sum(1 for f in findings if isinstance(f, dict) and f.get("finding_id"))
    assert finding_count == 1, "review materialized duplicate findings"
