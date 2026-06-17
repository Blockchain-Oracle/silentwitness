"""Unit coverage for the Rich live investigation HUD state updates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic_ai import RunContext, RunUsage
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.models.test import TestModel
from pydantic_ai.tools import ToolDefinition
from rich.console import Console

from silentwitness_agent.cli_commands._live_layout import render_findings_budget
from silentwitness_agent.cli_commands._live_render import DisplayState, build_display_hooks
from silentwitness_agent.hypothesis.budget import BudgetEnforcer
from silentwitness_agent.hypothesis.stack import HypothesisStack
from silentwitness_agent.hypothesis.types import SpecialistName
from silentwitness_agent.investigator import InvestigatorDeps


def _ctx(
    case_dir: Path,
    stack: HypothesisStack,
    budget: BudgetEnforcer,
    *,
    request_limit: int | None = None,
    total_token_limit: int | None = None,
) -> RunContext:
    deps = InvestigatorDeps(
        case_dir=case_dir,
        examiner="aj",
        stack=stack,
        budget=budget,
        request_limit=request_limit,
        total_token_limit=total_token_limit,
    )
    return RunContext(deps=deps, model=TestModel(), usage=RunUsage())


@pytest.mark.anyio
async def test_display_hooks_refresh_findings_budget_and_last_event(tmp_path: Path) -> None:
    state = DisplayState()
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer(default_token_budget=1000, default_step_budget=10)
    hooks = build_display_hooks(state, is_tty=True)
    call = ToolCallPart(
        tool_name="form_hypothesis",
        args={"statement": "x", "specialist": "LOG"},
        tool_call_id="call-1",
    )

    await hooks._registry["before_tool_execute"][0].func(
        _ctx(tmp_path, stack, budget),
        call=call,
        tool_def=ToolDefinition(name="form_hypothesis", parameters_json_schema={}),
        args={"statement": "x", "specialist": "LOG"},
    )
    h = stack.form("If detections exist, expect Sigma hits", SpecialistName.LOG)
    (tmp_path / "findings.json").write_text(
        json.dumps([{"finding_id": "F-001", "status": "DRAFT"}]),
        encoding="utf-8",
    )

    await hooks._registry["after_tool_execute"][0].func(
        _ctx(tmp_path, stack, budget),
        call=call,
        tool_def=ToolDefinition(name="form_hypothesis", parameters_json_schema={}),
        args={"statement": "x", "specialist": "LOG"},
        result={"hypothesis_id": h.id},
    )

    assert state.active_tool is None
    assert state.tool_call_count == 1
    assert state.stack_snap is not None
    assert state.stack_snap.active is not None
    assert state.findings is not None
    assert state.findings.findings_staged == 1
    assert state.findings.total_tool_calls == 1
    assert state.budget is not None
    assert state.budget.tokens_budgeted == 1000
    assert state.budget.tokens_remaining == 1000
    assert state.last_event is not None
    assert str(state.last_event.type) == "form"


@pytest.mark.anyio
async def test_display_hooks_show_run_budget_when_no_hypothesis_active(tmp_path: Path) -> None:
    state = DisplayState()
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer(default_token_budget=1000, default_step_budget=10)
    hooks = build_display_hooks(state, is_tty=True)
    h = stack.form("If detections exist, expect Sigma hits", SpecialistName.LOG)
    stack.confirm(h.id, ["audit-1"])
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir(exist_ok=True)
    (audit_dir / "agent.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"type": "step", "input_tokens": 1000, "output_tokens": 500}),
                json.dumps({"type": "step", "input_tokens": 1200, "output_tokens": 300}),
            ]
        ),
        encoding="utf-8",
    )
    call = ToolCallPart(tool_name="record_narrative", args={}, tool_call_id="call-1")

    await hooks._registry["after_tool_execute"][0].func(
        _ctx(
            tmp_path,
            stack,
            budget,
            request_limit=80,
            total_token_limit=6_000_000,
        ),
        call=call,
        tool_def=ToolDefinition(name="record_narrative", parameters_json_schema={}),
        args={},
        result={"ok": True},
    )

    assert state.stack_snap is not None
    assert state.stack_snap.active is None
    assert state.budget is not None
    assert state.budget.tokens_budgeted == 6_000_000
    assert state.budget.tokens_remaining == 5_997_000
    assert state.budget.steps_budgeted == 80
    assert state.budget.steps_remaining == 78

    _, budget_panel = render_findings_budget(state.findings, state.budget)
    console = Console(record=True, width=100, color_system=None)
    console.print(budget_panel)
    rendered = console.export_text()
    assert "3,000/6,000,000" in rendered
