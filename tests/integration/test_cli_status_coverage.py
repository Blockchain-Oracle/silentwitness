"""Additional coverage tests for `silentwitness status` (edge cases and extra paths)."""

from __future__ import annotations

from pathlib import Path

import pytest

from silentwitness_agent.cli import app
from tests.integration._helpers_status import (
    finish_event,
    hyp_event,
    init_case,
    runner,
    step_event,
    write_agent_jsonl,
    write_findings_json,
    write_hyp_jsonl,
)

# 13. last_pivot line from hypothesis.jsonl pivot event


def test_status_last_pivot_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given a pivot event in hypothesis.jsonl, 'last pivot:' line appears in output."""
    case_dir = init_case(tmp_path, "mr-pivot-001", monkeypatch)
    write_agent_jsonl(case_dir, [step_event()])
    write_hyp_jsonl(
        case_dir,
        [
            hyp_event("H-001", "form"),
            {
                "ts": "2026-01-01T00:02:00+00:00",
                "type": "pivot",
                "hypothesis_id": "H-001",
                "reason": "Evidence contradicts initial assumption",
            },
        ],
    )
    result = runner.invoke(app, ["status", "mr-pivot-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "last pivot:" in result.output
    assert "H-001" in result.output


# 14. _hyp_counts fallback: counts come from events when no stack_snapshot


def test_status_hyp_counts_from_events(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given hyp events in hypothesis.jsonl but no stack_snapshot, counts from events."""
    case_dir = init_case(tmp_path, "mr-live-001", monkeypatch)
    write_agent_jsonl(case_dir, [step_event()])  # no finish event → no stack_snapshot
    write_hyp_jsonl(
        case_dir,
        [
            hyp_event("H-001", "form"),
            hyp_event("H-001", "dispatch"),
            hyp_event("H-002", "form"),
            hyp_event("H-002", "confirm"),
        ],
    )
    result = runner.invoke(app, ["status", "mr-live-001"], catch_exceptions=False)
    assert result.exit_code == 0
    # H-001 dispatched → ACTIVE, H-002 confirmed → CONFIRMED
    assert "(1 active, 1 confirmed, 0 pivoted, 0 abandoned)" in result.output


# 15. Approved findings counted correctly


def test_status_approved_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given APPROVED findings in findings.json, approved count is correct."""
    case_dir = init_case(tmp_path, "mr-approved-001", monkeypatch)
    write_agent_jsonl(case_dir, [finish_event()])
    write_findings_json(
        case_dir,
        [
            {"status": "APPROVED", "id": "F-001"},
            {"status": "APPROVED", "id": "F-002"},
            {"status": "DRAFT", "id": "F-003"},
        ],
    )
    result = runner.invoke(app, ["status", "mr-approved-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "findings: staged 1  approved 2  rejected 0" in result.output


# 16. findings.json corruption emits warning and exits 0


def test_status_findings_json_corrupted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given corrupted findings.json, status exits 0 with a degraded warning."""
    case_dir = init_case(tmp_path, "mr-findings-corrupt-001", monkeypatch)
    write_agent_jsonl(case_dir, [finish_event()])
    (case_dir / "findings.json").write_text("NOT VALID JSON", encoding="utf-8")
    result = runner.invoke(app, ["status", "mr-findings-corrupt-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "findings.json unreadable" in result.output


# 17. Snapshot unavailable shown for in-progress run with hypotheses


def test_status_snapshot_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given hypothesis events but no stack_snapshot, 'snapshot unavailable' is shown."""
    case_dir = init_case(tmp_path, "mr-inprog-snap-001", monkeypatch)
    write_agent_jsonl(case_dir, [step_event()])  # no finish event → no stack_snapshot
    write_hyp_jsonl(case_dir, [hyp_event("H-001", "form")])
    result = runner.invoke(app, ["status", "mr-inprog-snap-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "snapshot unavailable" in result.output


# 18. Elapsed time uses hours/minutes format for long runs


def test_status_elapsed_hours_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given timestamps 2h apart, elapsed shows Xh YYm format."""
    case_dir = init_case(tmp_path, "mr-longrun-001", monkeypatch)
    events: list[dict] = [
        {
            "ts": "2026-01-01T00:00:00+00:00",
            "type": "step",
            "input_tokens": 100,
            "output_tokens": 50,
        },
        {
            "ts": "2026-01-01T02:15:00+00:00",
            "type": "finish",
            "event": "on_finish",
            "total_tokens_consumed": 5_000,
            "model_used": "claude-sonnet-4-6",
        },
    ]
    write_agent_jsonl(case_dir, events)
    result = runner.invoke(app, ["status", "mr-longrun-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "2h" in result.output
