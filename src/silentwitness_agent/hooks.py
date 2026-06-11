"""Pydantic AI Hooks capability for agent-side audit emission.

Emits one JSONL audit line per lifecycle event to ``cases/<case_id>/audit/agent.jsonl``,
accumulates per-hypothesis token + step consumption against BudgetEnforcer, and writes
a final hypothesis snapshot on run completion.

Parallel layer to ``silentwitness_mcp.audit.logger`` (MCP-side audit); the two layers
cross-link via ``audit_id`` — every ``after_tool`` line references the MCP-side
``audit_id`` so ``silentwitness verify-claim`` resolves agent.jsonl → MCP-side entry.

JSONL event shapes (one JSON object per line):
  before_tool : {ts, type, tool_name, tool_args_summary, agent_step, active_hypothesis_id}
  after_tool  : {ts, type, tool_name, audit_id, result_sha256, elapsed_ms, agent_step,
                 active_hypothesis_id, success[, error_type, error_message]}
  step        : {ts, type, step_index, input_tokens, output_tokens, active_hypothesis_id}
  finish      : {ts, type, final_state, stack_snapshot, model_used, total_tokens_consumed}
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.capabilities import Hooks, ValidatedToolArgs
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models import ModelRequestContext
from pydantic_ai.tools import ToolDefinition

from silentwitness_agent.hypothesis.budget import BudgetEnforcer
from silentwitness_agent.hypothesis.stack import HypothesisStack
from silentwitness_agent.investigator import InvestigatorDeps
from silentwitness_common.atomic_io import append_jsonl_line

_LOG = logging.getLogger(__name__)

# Mirrors architecture §4.4 result_summary truncation: full args are in MCP-side JSONL.
_ARGS_SUMMARY_LIMIT = 1024


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ts_now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _args_summary(args: ValidatedToolArgs) -> str:
    raw = json.dumps(args, default=str)
    return raw[:_ARGS_SUMMARY_LIMIT]


def _hyp_id(stack: HypothesisStack) -> str | None:
    snap = stack.snapshot()
    return snap.active.id if snap.active else None


def _append_agent_jsonl(case_dir: Path, payload: dict[str, Any]) -> None:
    """Append one audit event to ``audit/agent.jsonl`` using atomic fsync-append."""
    path = case_dir / "audit" / "agent.jsonl"
    append_jsonl_line(path, json.dumps(payload, default=str))


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_investigator_hooks(
    case_dir: Path,
    examiner: str,
    stack: HypothesisStack,
    budget: BudgetEnforcer,
) -> Hooks[InvestigatorDeps]:
    """Return a Hooks instance with four audit-emission callbacks registered.

    Pass the result as ``capabilities=[hooks]`` to ``build_investigator()``
    (NOT ``hooks=[...]`` — that kwarg does not exist in Pydantic AI v1.105).
    """
    hooks: Hooks[InvestigatorDeps] = Hooks()

    # Per-call timing keyed by tool_call_id; populated in before_tool, consumed in after_tool.
    _inflight: dict[str, int] = {}
    # Step counter incremented once per after_model_request firing.
    _step: list[int] = [0]

    # ------------------------------------------------------------------
    # before_tool_execute — record start time, emit pre-tool audit line
    # ------------------------------------------------------------------

    @hooks.on.before_tool_execute
    async def _on_before_tool(
        ctx: RunContext[InvestigatorDeps],
        /,
        *,
        call: ToolCallPart,
        tool_def: ToolDefinition,
        args: ValidatedToolArgs,
    ) -> ValidatedToolArgs:
        _inflight[call.tool_call_id] = time.monotonic_ns()
        payload: dict[str, Any] = {
            "ts": _ts_now(),
            "type": "before_tool",
            "tool_name": call.tool_name,
            "tool_args_summary": _args_summary(args),
            "agent_step": _step[0],
            "active_hypothesis_id": _hyp_id(ctx.deps.stack),
        }
        try:
            _append_agent_jsonl(case_dir, payload)
        except Exception:
            _LOG.exception("hooks: before_tool append failed tool=%s", call.tool_name)
        return args

    # ------------------------------------------------------------------
    # after_tool_execute — compute elapsed + SHA256, emit post-tool line
    # ------------------------------------------------------------------

    @hooks.on.after_tool_execute
    async def _on_after_tool(
        ctx: RunContext[InvestigatorDeps],
        /,
        *,
        call: ToolCallPart,
        tool_def: ToolDefinition,
        args: ValidatedToolArgs,
        result: Any,
    ) -> Any:
        start_ns = _inflight.pop(call.tool_call_id, None)
        elapsed_ms = (time.monotonic_ns() - start_ns) / 1e6 if start_ns is not None else 0.0
        # Extract MCP-side audit_id from the ToolResponse envelope if present.
        audit_id: str | None = result.get("audit_id") if isinstance(result, dict) else None
        payload: dict[str, Any] = {
            "ts": _ts_now(),
            "type": "after_tool",
            "tool_name": call.tool_name,
            "audit_id": audit_id,
            "result_sha256": _sha256(result),
            "elapsed_ms": elapsed_ms,
            "agent_step": _step[0],
            "active_hypothesis_id": _hyp_id(ctx.deps.stack),
            "success": True,
        }
        try:
            _append_agent_jsonl(case_dir, payload)
        except Exception:
            _LOG.exception("hooks: after_tool append failed tool=%s", call.tool_name)
        return result

    # ------------------------------------------------------------------
    # tool_execute_error — log failure line then re-raise so agent sees error
    # ------------------------------------------------------------------

    @hooks.on.tool_execute_error
    async def _on_tool_error(
        ctx: RunContext[InvestigatorDeps],
        /,
        *,
        call: ToolCallPart,
        tool_def: ToolDefinition,
        args: ValidatedToolArgs,
        error: Exception,
    ) -> Any:
        start_ns = _inflight.pop(call.tool_call_id, None)
        elapsed_ms = (time.monotonic_ns() - start_ns) / 1e6 if start_ns is not None else 0.0
        payload: dict[str, Any] = {
            "ts": _ts_now(),
            "type": "after_tool",
            "tool_name": call.tool_name,
            "audit_id": None,
            "result_sha256": None,
            "elapsed_ms": elapsed_ms,
            "agent_step": _step[0],
            "active_hypothesis_id": _hyp_id(ctx.deps.stack),
            "success": False,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
        try:
            _append_agent_jsonl(case_dir, payload)
        except Exception:
            _LOG.exception("hooks: tool_error append failed tool=%s", call.tool_name)
        raise error

    # ------------------------------------------------------------------
    # after_model_request — record token delta, increment step counter
    # ------------------------------------------------------------------

    @hooks.on.after_model_request
    async def _on_after_model_request(
        ctx: RunContext[InvestigatorDeps],
        /,
        *,
        request_context: ModelRequestContext,
        response: ModelResponse,
    ) -> ModelResponse:
        _step[0] += 1
        usage = response.usage
        hyp_id = _hyp_id(ctx.deps.stack)
        if hyp_id:
            try:
                budget.record_tokens(hyp_id, usage.input_tokens, usage.output_tokens)
                budget.record_step(hyp_id)
            except Exception:
                _LOG.exception("hooks: budget record failed hypothesis=%s", hyp_id)
        payload: dict[str, Any] = {
            "ts": _ts_now(),
            "type": "step",
            "step_index": _step[0],
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "active_hypothesis_id": hyp_id,
        }
        try:
            _append_agent_jsonl(case_dir, payload)
        except Exception:
            _LOG.exception("hooks: step append failed step=%d", _step[0])
        return response

    # ------------------------------------------------------------------
    # after_run — write final hypothesis snapshot and finish line
    # ------------------------------------------------------------------

    @hooks.on.after_run
    async def _on_after_run(
        ctx: RunContext[InvestigatorDeps],
        /,
        *,
        result: Any,
    ) -> Any:
        snap = stack.snapshot()
        model_used: str | None = getattr(result.output, "model_used", None)
        total_tokens: int = getattr(result.usage, "total_tokens", 0) or 0
        payload: dict[str, Any] = {
            "ts": _ts_now(),
            "type": "finish",
            "final_state": "COMPLETED",
            "stack_snapshot": snap.model_dump(mode="json"),
            "model_used": model_used,
            "total_tokens_consumed": total_tokens,
        }
        try:
            _append_agent_jsonl(case_dir, payload)
        except Exception:
            _LOG.exception("hooks: finish append failed")
        # Epic 11 report renderer not yet merged; save_atomic deferred.
        _LOG.debug("hooks: finish emitted for case=%s examiner=%s", case_dir.name, examiner)
        return result

    return hooks


__all__ = ["build_investigator_hooks"]
