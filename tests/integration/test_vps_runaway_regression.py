"""Regression coverage for the June 17 VPS runaway investigation snapshot."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from silentwitness_agent.cli import app
from silentwitness_agent.cli_commands._investigate_runner import _agent_step_token_total
from tests.integration._helpers_status import init_case, runner

_VPS_TOTAL_TOKENS = 44_096_043
_VPS_STEP_RECORD_COUNT = 320
_VPS_SIGINT_STEP = 297
_VPS_LAST_STEP_INPUT = 250_966
_VPS_LAST_STEP_OUTPUT = 19
_VPS_TAIL_AGENT_STEPS = tuple(range(290, 298))


def _write_vps_agent_log(case_dir: Path) -> None:
    audit_dir = case_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    base = datetime(2026, 6, 17, 7, 45, tzinfo=UTC)
    tail_before_tools = [
        {
            "ts": (base + timedelta(minutes=59, seconds=i * 10)).isoformat(),
            "type": "before_tool",
            "tool_name": "list_detections",
            "tool_args_summary": '{"limit": 1}' if i % 3 else '{"limit": 5}',
            "agent_step": step,
            "active_hypothesis_id": None,
        }
        for i, step in enumerate(_VPS_TAIL_AGENT_STEPS)
    ]
    prior_total = _VPS_TOTAL_TOKENS - _VPS_LAST_STEP_INPUT - _VPS_LAST_STEP_OUTPUT
    prior_count = _VPS_STEP_RECORD_COUNT - 1
    per_step = prior_total // prior_count
    remainder = prior_total - (per_step * prior_count)
    events: list[dict[str, object]] = []
    for i in range(prior_count):
        extra = remainder if i == prior_count - 1 else 0
        events.append(
            {
                "ts": (base + timedelta(seconds=i * 12)).isoformat(),
                "type": "step",
                "step_index": i + 1,
                "input_tokens": per_step + extra - 19,
                "output_tokens": 19,
                "active_hypothesis_id": None if i > 250 else "H-009",
            }
        )
    events.append(
        {
            "ts": "2026-06-17T08:46:32.783583+00:00",
            "type": "step",
            "step_index": _VPS_SIGINT_STEP,
            "input_tokens": _VPS_LAST_STEP_INPUT,
            "output_tokens": _VPS_LAST_STEP_OUTPUT,
            "active_hypothesis_id": None,
        }
    )
    events.extend(tail_before_tools)
    events.append(
        {
            "ts": "2026-06-17T08:46:35+00:00",
            "event": "sigint_checkpoint",
            "step": _VPS_SIGINT_STEP,
            "reason": "sigint_checkpoint",
        }
    )
    (audit_dir / "agent.jsonl").write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )
    (audit_dir / "hypothesis.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "ts": "2026-06-17T07:50:00+00:00",
                        "type": "form",
                        "hypothesis_id": "H-009",
                        "statement": "VPS mount posture hypothesis confirmed",
                    }
                ),
                json.dumps(
                    {
                        "ts": "2026-06-17T08:00:00+00:00",
                        "type": "confirm",
                        "hypothesis_id": "H-009",
                        "reason": "record_observation was rejected by mount guard",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_status_reports_vps_runaway_snapshot_truthfully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_dir = init_case(tmp_path, "mr-evil-001", monkeypatch)
    _write_vps_agent_log(case_dir)

    result = runner.invoke(app, ["status", "mr-evil-001", "--full"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "status:  ABORTED" in result.output
    assert "tokens:   44M / 6M budget" in result.output
    assert "(0 active, 1 confirmed, 0 pivoted, 0 abandoned)" in result.output


def test_agent_step_token_total_matches_vps_snapshot(tmp_path: Path) -> None:
    case_dir = tmp_path / "cases" / "mr-evil-001"
    _write_vps_agent_log(case_dir)

    assert _agent_step_token_total(case_dir) == _VPS_TOTAL_TOKENS


def test_vps_snapshot_preserves_null_hypothesis_detection_tail(tmp_path: Path) -> None:
    case_dir = tmp_path / "cases" / "mr-evil-001"
    _write_vps_agent_log(case_dir)

    events = [
        json.loads(raw)
        for raw in (case_dir / "audit" / "agent.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    before_tail = [event for event in events if event.get("type") == "before_tool"][-8:]
    last_step = [event for event in events if event.get("type") == "step"][-1]

    assert len(before_tail) == 8
    assert [event["agent_step"] for event in before_tail] == list(_VPS_TAIL_AGENT_STEPS)
    assert {event["tool_name"] for event in before_tail} == {"list_detections"}
    assert {event["active_hypothesis_id"] for event in before_tail} == {None}
    assert last_step["step_index"] == _VPS_SIGINT_STEP
    assert last_step["input_tokens"] == _VPS_LAST_STEP_INPUT
    assert last_step["output_tokens"] == _VPS_LAST_STEP_OUTPUT
