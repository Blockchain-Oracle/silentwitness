"""Unit tests for hypothesis attribution in build_investigator_hooks audit lines.

These tests focus on the active_hypothesis_id field written to each audit event
and the budget enforcement calls attributed to the correct hypothesis.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai import RunContext, RunUsage
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.test import TestModel
from pydantic_ai.tools import ToolDefinition

from silentwitness_agent.hooks import build_investigator_hooks
from silentwitness_agent.hypothesis.budget import BudgetEnforcer
from silentwitness_agent.hypothesis.stack import HypothesisStack
from silentwitness_agent.hypothesis.types import SpecialistName
from silentwitness_agent.investigator import InvestigatorDeps

# ---------------------------------------------------------------------------
# Helpers (mirrors test_investigator_hooks.py)
# ---------------------------------------------------------------------------


def _make_deps(case_dir: Path, stack: HypothesisStack, budget: BudgetEnforcer) -> InvestigatorDeps:
    return InvestigatorDeps(case_dir=case_dir, examiner="aj", stack=stack, budget=budget)


def _make_ctx(deps: InvestigatorDeps) -> RunContext[InvestigatorDeps]:
    return RunContext(deps=deps, model=TestModel(), usage=RunUsage())


def _make_call(name: str = "test_tool", call_id: str = "call-001") -> ToolCallPart:
    return ToolCallPart(tool_name=name, args={"key": "val"}, tool_call_id=call_id)


def _make_tool_def(name: str = "test_tool") -> ToolDefinition:
    return ToolDefinition(name=name, parameters_json_schema={})


def _read_jsonl(case_dir: Path) -> list[dict]:  # type: ignore[type-arg]
    path = case_dir / "audit" / "agent.jsonl"
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]


# ---------------------------------------------------------------------------
# 1. before_tool line carries the correct active_hypothesis_id
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_before_tool_active_hypothesis_id_value(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    stack.form("If C2 beacon, expect DNS record", SpecialistName.NETWORK)
    hyp_id = stack.snapshot().active.id  # type: ignore[union-attr]
    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))
    call = _make_call("net_scan", "c-hyp-001")

    fn = hooks._registry["before_tool_execute"][0].func
    await fn(ctx, call=call, tool_def=_make_tool_def(), args={})

    line = _read_jsonl(tmp_path)[0]
    assert line["active_hypothesis_id"] == hyp_id


# ---------------------------------------------------------------------------
# 2. step line carries the correct active_hypothesis_id
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_step_active_hypothesis_id_value(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    stack.form("If persistence, expect schtasks entry", SpecialistName.DISK)
    hyp_id = stack.snapshot().active.id  # type: ignore[union-attr]
    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))

    response = ModelResponse(parts=[], usage=MagicMock(input_tokens=10, output_tokens=5))
    fn = hooks._registry["after_model_request"][0].func
    await fn(ctx, request_context=MagicMock(), response=response)

    step_line = _read_jsonl(tmp_path)[0]
    assert step_line["active_hypothesis_id"] == hyp_id


# ---------------------------------------------------------------------------
# 3. record_step called with the correct hypothesis_id
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_record_step_called_with_correct_hypothesis_id(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    stack.form("If lateral movement, expect new logon event", SpecialistName.LOG)
    hyp_id = stack.snapshot().active.id  # type: ignore[union-attr]
    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))

    response = ModelResponse(parts=[], usage=MagicMock(input_tokens=30, output_tokens=20))
    with patch.object(budget, "record_step") as mock_rs:
        fn = hooks._registry["after_model_request"][0].func
        await fn(ctx, request_context=MagicMock(), response=response)
        mock_rs.assert_called_once_with(hyp_id)


# ---------------------------------------------------------------------------
# 4. 10 concurrent before_tool calls each produce one valid JSONL line
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_concurrent_before_tool_calls_produce_exactly_n_lines(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))
    before_fn = hooks._registry["before_tool_execute"][0].func

    async def _fire(i: int) -> None:
        call = _make_call(f"tool_{i}", f"call-{i:03d}")
        await before_fn(ctx, call=call, tool_def=_make_tool_def(f"tool_{i}"), args={"i": i})

    await asyncio.gather(*[_fire(i) for i in range(10)])

    lines = _read_jsonl(tmp_path)
    assert len(lines) == 10
    for ln in lines:
        assert ln["type"] == "before_tool"
        assert "tool_name" in ln
        assert "ts" in ln
