"""Regression tests for null-active-hypothesis tool loops."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic_ai import RunContext, RunUsage
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.models.test import TestModel
from pydantic_ai.tools import ToolDefinition

from silentwitness_agent.hooks import NoActiveHypothesisToolError, build_investigator_hooks
from silentwitness_agent.hypothesis.budget import BudgetEnforcer
from silentwitness_agent.hypothesis.stack import HypothesisStack
from silentwitness_agent.hypothesis.types import SpecialistName
from silentwitness_agent.investigator import InvestigatorDeps


def _make_deps(case_dir: Path, stack: HypothesisStack, budget: BudgetEnforcer) -> InvestigatorDeps:
    return InvestigatorDeps(case_dir=case_dir, examiner="aj", stack=stack, budget=budget)


def _make_ctx(deps: InvestigatorDeps) -> RunContext[InvestigatorDeps]:
    return RunContext(deps=deps, model=TestModel(), usage=RunUsage())


def _make_call(name: str, call_id: str) -> ToolCallPart:
    return ToolCallPart(tool_name=name, args={"key": "val"}, tool_call_id=call_id)


def _make_tool_def(name: str) -> ToolDefinition:
    return ToolDefinition(name=name, parameters_json_schema={})


def _read_jsonl(case_dir: Path) -> list[dict[str, object]]:
    path = case_dir / "audit" / "agent.jsonl"
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]


@pytest.mark.anyio
async def test_before_tool_blocks_vps_null_hypothesis_detection_loop(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    h = stack.form("If detections exist, expect Sigma hits", SpecialistName.LOG)
    stack.confirm(h.id, ["sift-root-20260617-205"])
    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))

    fn = hooks._registry["before_tool_execute"][0].func
    with pytest.raises(NoActiveHypothesisToolError, match="NO_ACTIVE_HYPOTHESIS"):
        await fn(
            ctx,
            call=_make_call("list_detections", "vps-loop"),
            tool_def=_make_tool_def("list_detections"),
            args={"limit": 5},
        )

    assert _read_jsonl(tmp_path) == []


@pytest.mark.anyio
async def test_before_tool_allows_new_hypothesis_after_resolved_stack(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    h = stack.form("If detections exist, expect Sigma hits", SpecialistName.LOG)
    stack.confirm(h.id, ["sift-root-20260617-205"])
    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))

    fn = hooks._registry["before_tool_execute"][0].func
    ret = await fn(
        ctx,
        call=_make_call("form_hypothesis", "new-hyp"),
        tool_def=_make_tool_def("form_hypothesis"),
        args={"statement": "new", "specialist": "LOG"},
    )

    assert ret == {"statement": "new", "specialist": "LOG"}
