"""Shared test helpers for test_cli_status.py and test_cli_status_coverage.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from silentwitness_agent.cli import app

runner = CliRunner()


def init_case(tmp_path: Path, case_id: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    result = runner.invoke(app, ["init", case_id], catch_exceptions=False)
    assert result.exit_code == 0
    return tmp_path / "cases" / case_id


def write_agent_jsonl(case_dir: Path, events: list[dict[str, Any]]) -> None:
    lines = "\n".join(json.dumps(e) for e in events) + "\n"
    (case_dir / "audit" / "agent.jsonl").write_text(lines, encoding="utf-8")


def write_hyp_jsonl(case_dir: Path, events: list[dict[str, Any]]) -> None:
    lines = "\n".join(json.dumps(e) for e in events) + "\n"
    (case_dir / "audit" / "hypothesis.jsonl").write_text(lines, encoding="utf-8")


def write_findings_json(case_dir: Path, items: list[dict[str, Any]]) -> None:
    (case_dir / "findings.json").write_text(json.dumps(items), encoding="utf-8")


def step_event(input_tokens: int = 1000, output_tokens: int = 500) -> dict[str, Any]:
    return {
        "ts": "2026-01-01T00:00:00+00:00",
        "type": "step",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def finish_event(
    total_tokens: int = 312_000,
    stack_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ev: dict[str, Any] = {
        "ts": "2026-01-01T00:05:00+00:00",
        "type": "finish",
        "event": "on_finish",
        "total_tokens_consumed": total_tokens,
        "model_used": "claude-sonnet-4-6",
    }
    if stack_snapshot is not None:
        ev["stack_snapshot"] = stack_snapshot
    return ev


def hyp_event(hid: str, hyp_type: str, reason: str = "") -> dict[str, Any]:
    ev: dict[str, Any] = {
        "ts": "2026-01-01T00:01:00+00:00",
        "type": hyp_type,
        "hypothesis_id": hid,
    }
    if reason:
        ev["reason"] = reason
    return ev


def make_stack_snapshot(
    active: dict[str, Any] | None = None,
    queued: list[dict[str, Any]] | None = None,
    history: list[dict[str, Any]] | None = None,
    total_pivot_count: int = 0,
) -> dict[str, Any]:
    return {
        "active": active,
        "queued": queued or [],
        "history": history or [],
        "total_pivot_count": total_pivot_count,
    }
