"""Unit tests for build_investigator_hooks — ≥10 behavioural tests.

No network calls — hooks are exercised by directly invoking the registered closures
via ``hooks._registry[name][0].func``.  A real ``HypothesisStack`` and ``BudgetEnforcer``
are used so state transitions and token accounting are tested end-to-end.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai import RunContext, RunUsage
from pydantic_ai.capabilities import Hooks
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.test import TestModel
from pydantic_ai.tools import ToolDefinition

from silentwitness_agent.hooks import build_investigator_hooks
from silentwitness_agent.hypothesis.budget import BudgetEnforcer
from silentwitness_agent.hypothesis.stack import HypothesisStack
from silentwitness_agent.hypothesis.types import SpecialistName
from silentwitness_agent.investigator import InvestigatorDeps

# ---------------------------------------------------------------------------
# Helpers
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
# 1. Factory contract
# ---------------------------------------------------------------------------


def test_build_returns_hooks_instance(tmp_path: Path) -> None:
    hooks = build_investigator_hooks(
        tmp_path, "aj", HypothesisStack(case_dir=tmp_path, examiner="aj"), BudgetEnforcer()
    )
    assert isinstance(hooks, Hooks)


def test_all_five_lifecycle_callbacks_registered(tmp_path: Path) -> None:
    hooks = build_investigator_hooks(
        tmp_path, "aj", HypothesisStack(case_dir=tmp_path, examiner="aj"), BudgetEnforcer()
    )
    reg = hooks._registry
    assert "before_tool_execute" in reg
    assert "after_tool_execute" in reg
    assert "on_tool_execute_error" in reg
    assert "after_model_request" in reg
    assert "after_run" in reg


# ---------------------------------------------------------------------------
# 2. before_tool — appends well-formed JSONL line
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_before_tool_appends_jsonl_line(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))
    call = _make_call("mem_scan", "c-001")

    fn = hooks._registry["before_tool_execute"][0].func
    ret = await fn(ctx, call=call, tool_def=_make_tool_def("mem_scan"), args={"pid": 1234})

    assert ret == {"pid": 1234}  # passthrough — args must be returned unchanged

    lines = _read_jsonl(tmp_path)
    assert len(lines) == 1
    line = lines[0]
    assert line["type"] == "before_tool"
    assert line["tool_name"] == "mem_scan"
    assert "ts" in line
    assert "tool_args_summary" in line
    assert line["agent_step"] == 0
    assert "active_hypothesis_id" in line


# ---------------------------------------------------------------------------
# 3. after_tool — SHA256 + elapsed_ms + audit_id cross-link
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_after_tool_sha256_is_64_hex_chars(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))
    call = _make_call("disk_scan", "c-002")

    before_fn = hooks._registry["before_tool_execute"][0].func
    await before_fn(ctx, call=call, tool_def=_make_tool_def(), args={})

    after_fn = hooks._registry["after_tool_execute"][0].func
    result = {"findings": ["proc-X"], "audit_id": "sift-aj-20260613-007"}
    ret = await after_fn(ctx, call=call, tool_def=_make_tool_def(), args={}, result=result)
    assert ret is result  # passthrough

    lines = _read_jsonl(tmp_path)
    after_line = next(ln for ln in lines if ln["type"] == "after_tool")
    sha = after_line["result_sha256"]
    assert isinstance(sha, str) and len(sha) == 64
    assert all(c in "0123456789abcdef" for c in sha)


@pytest.mark.anyio
async def test_after_tool_elapsed_ms_non_negative(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))
    call = _make_call("perf_tool", "c-003")

    await hooks._registry["before_tool_execute"][0].func(
        ctx, call=call, tool_def=_make_tool_def(), args={}
    )
    await hooks._registry["after_tool_execute"][0].func(
        ctx, call=call, tool_def=_make_tool_def(), args={}, result={}
    )

    lines = _read_jsonl(tmp_path)
    after_line = next(ln for ln in lines if ln["type"] == "after_tool")
    assert after_line["elapsed_ms"] >= 0


@pytest.mark.anyio
async def test_after_tool_cross_links_mcp_audit_id(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))
    call = _make_call("net_tool", "c-004")

    await hooks._registry["before_tool_execute"][0].func(
        ctx, call=call, tool_def=_make_tool_def(), args={}
    )
    await hooks._registry["after_tool_execute"][0].func(
        ctx,
        call=call,
        tool_def=_make_tool_def(),
        args={},
        result={"data": "x", "audit_id": "sift-aj-20260613-007"},
    )

    after_line = next(ln for ln in _read_jsonl(tmp_path) if ln["type"] == "after_tool")
    assert after_line["audit_id"] == "sift-aj-20260613-007"


@pytest.mark.anyio
async def test_after_tool_audit_id_none_when_absent(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))
    call = _make_call("plain_tool", "c-005")

    await hooks._registry["before_tool_execute"][0].func(
        ctx, call=call, tool_def=_make_tool_def(), args={}
    )
    await hooks._registry["after_tool_execute"][0].func(
        ctx, call=call, tool_def=_make_tool_def(), args={}, result={"plain": True}
    )

    after_line = next(ln for ln in _read_jsonl(tmp_path) if ln["type"] == "after_tool")
    assert after_line["audit_id"] is None


# ---------------------------------------------------------------------------
# 4. tool_execute_error — emits after_tool with success=False, then re-raises
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_tool_error_emits_failure_line_and_reraises(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))
    call = _make_call("failing_tool", "c-006")

    await hooks._registry["before_tool_execute"][0].func(
        ctx, call=call, tool_def=_make_tool_def(), args={}
    )
    err_fn = hooks._registry["on_tool_execute_error"][0].func
    exc = RuntimeError("MCP subprocess died")

    with pytest.raises(RuntimeError, match="MCP subprocess died"):
        await err_fn(ctx, call=call, tool_def=_make_tool_def(), args={}, error=exc)

    after_line = next(ln for ln in _read_jsonl(tmp_path) if ln["type"] == "after_tool")
    assert after_line["success"] is False
    assert after_line["error_type"] == "RuntimeError"
    assert "MCP subprocess died" in after_line["error_message"]


# ---------------------------------------------------------------------------
# 5. after_model_request — token accounting + step JSONL
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_after_model_request_records_tokens_and_step(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    stack.form("If persistence, expect Run-key entry", SpecialistName.DISK)
    hyp_id = stack.snapshot().active.id  # type: ignore[union-attr]

    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))
    response = ModelResponse(parts=[], usage=MagicMock(input_tokens=120, output_tokens=80))

    fn = hooks._registry["after_model_request"][0].func
    ret = await fn(ctx, request_context=MagicMock(), response=response)

    assert ret is response
    state = budget._states.get(hyp_id)
    assert state is not None
    assert state.tokens_consumed == 200  # 120 + 80
    assert state.steps_consumed == 1


@pytest.mark.anyio
async def test_after_model_request_appends_step_jsonl(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))

    response = ModelResponse(parts=[], usage=MagicMock(input_tokens=50, output_tokens=30))
    fn = hooks._registry["after_model_request"][0].func
    await fn(ctx, request_context=MagicMock(), response=response)

    lines = _read_jsonl(tmp_path)
    assert len(lines) == 1
    step = lines[0]
    assert step["type"] == "step"
    assert step["step_index"] == 1
    assert step["input_tokens"] == 50
    assert step["output_tokens"] == 30


@pytest.mark.anyio
async def test_after_model_request_no_hypothesis_skips_budget(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))

    response = ModelResponse(parts=[], usage=MagicMock(input_tokens=10, output_tokens=5))
    with patch.object(budget, "record_tokens") as mock_rt:
        fn = hooks._registry["after_model_request"][0].func
        await fn(ctx, request_context=MagicMock(), response=response)
        mock_rt.assert_not_called()


# ---------------------------------------------------------------------------
# 6. after_run — finish line with stack snapshot embedded
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_after_run_emits_finish_line(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))

    mock_result = MagicMock()
    mock_result.output.model_used = "test-model"
    mock_result.usage.total_tokens = 500

    fn = hooks._registry["after_run"][0].func
    ret = await fn(ctx, result=mock_result)
    assert ret is mock_result

    lines = _read_jsonl(tmp_path)
    assert len(lines) == 1
    finish = lines[0]
    assert finish["type"] == "finish"
    assert finish["final_state"] == "COMPLETED"
    assert finish["model_used"] == "test-model"
    assert finish["total_tokens_consumed"] == 500
    assert finish["audit_append_failures"] == 0
    assert "stack_snapshot" in finish
    snap = finish["stack_snapshot"]
    assert "active" in snap
    assert "history" in snap


# ---------------------------------------------------------------------------
# 7. Full sequence — all JSONL lines parse cleanly
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_all_lines_parse_and_contain_required_fields(tmp_path: Path) -> None:
    stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    budget = BudgetEnforcer()
    hooks = build_investigator_hooks(tmp_path, "aj", stack, budget)
    ctx = _make_ctx(_make_deps(tmp_path, stack, budget))
    call = _make_call("full_tool", "c-099")

    await hooks._registry["before_tool_execute"][0].func(
        ctx, call=call, tool_def=_make_tool_def(), args={"x": 1}
    )
    await hooks._registry["after_tool_execute"][0].func(
        ctx, call=call, tool_def=_make_tool_def(), args={"x": 1}, result={"y": 2}
    )
    await hooks._registry["after_model_request"][0].func(
        ctx,
        request_context=MagicMock(),
        response=ModelResponse(parts=[], usage=MagicMock(input_tokens=10, output_tokens=5)),
    )
    mock_result = MagicMock()
    mock_result.output.model_used = "test"
    mock_result.usage.total_tokens = 15
    await hooks._registry["after_run"][0].func(ctx, result=mock_result)

    path = tmp_path / "audit" / "agent.jsonl"
    for raw in path.read_text().splitlines():
        parsed = json.loads(raw)
        assert "type" in parsed
        assert "ts" in parsed
