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
                 active_hypothesis_id, success}
                 on error: result_sha256=null, audit_id=null, plus error_type, error_message
  step        : {ts, type, step_index, input_tokens, output_tokens, active_hypothesis_id}
  finish      : {ts, type, final_state, stack_snapshot, model_used, total_tokens_consumed,
                 audit_append_failures, finalized_open_hypotheses_abandoned}
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Never

from pydantic_ai import RunContext
from pydantic_ai.capabilities import Hooks, ValidatedToolArgs
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models import ModelRequestContext
from pydantic_ai.tools import ToolDefinition

from silentwitness_agent.hypothesis.budget import BudgetEnforcer
from silentwitness_agent.hypothesis.stack import HypothesisStack
from silentwitness_agent.investigator import InvestigatorDeps
from silentwitness_mcp.audit.chained_jsonl import append_chained_jsonl

_LOG = logging.getLogger(__name__)

# Mirrors architecture §4.4 result_summary truncation: full args are in MCP-side JSONL.
_ARGS_SUMMARY_LIMIT = 1024
_FINALIZE_ABANDON_REASON = "RUN_FINALIZED_WITH_OPEN_QUESTIONS"


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


def _close_open_hypotheses(stack: HypothesisStack) -> int:
    """Abandon active and queued hypotheses before writing a completed finish line."""
    closed = 0
    while True:
        active = stack.snapshot().active
        if active is None:
            return closed
        try:
            stack.abandon(active.id, _FINALIZE_ABANDON_REASON)
        except Exception:
            _LOG.exception("hooks: failed to finalize open hypothesis %s", active.id)
            return closed
        closed += 1


def _append_agent_jsonl(case_dir: Path, payload: dict[str, Any]) -> None:
    """Append one hash-chained audit event to ``audit/agent.jsonl``.

    The MCP ``AuditLogger`` cannot be reused here because it owns per-case
    audit-id sequencing and a singleton lock. Agent lifecycle events are a
    separate stream, but still need the same tamper-evident chain.
    """
    path = case_dir / "audit" / "agent.jsonl"
    append_chained_jsonl(path, json.loads(json.dumps(payload, default=str)))


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_investigator_hooks(
    case_dir: Path,
    examiner: str,
    stack: HypothesisStack,
    budget: BudgetEnforcer,
) -> Hooks[InvestigatorDeps]:
    """Return a Hooks instance with five audit-emission callbacks registered.

    The five registered hooks: before_tool_execute, after_tool_execute,
    tool_execute_error, after_model_request, after_run.

    Pass the result as ``capabilities=[hooks]`` to ``build_investigator()``
    (NOT ``hooks=[...]`` — that kwarg does not exist in Pydantic AI v1.105).

    The returned instance is NOT safe for concurrent ``agent.run()`` calls.
    Each investigation must obtain a fresh instance from this factory.
    """
    hooks: Hooks[InvestigatorDeps] = Hooks()

    # Per-call timing keyed by tool_call_id; populated in before_tool_execute,
    # consumed in after_tool_execute (success) or tool_execute_error (failure).
    _inflight: dict[str, int] = {}
    # Step counter incremented once per after_model_request firing.
    _step: list[int] = [0]
    # Count of failed _append_agent_jsonl calls; surfaced in finish payload so
    # verify-claim can detect runs where the audit trail is incomplete.
    _append_failures: list[int] = [0]

    def _pop_elapsed_ms(tool_call_id: str) -> float:
        """Return elapsed ms since the matching before_tool, or 0.0 if untracked."""
        start_ns = _inflight.pop(tool_call_id, None)
        if start_ns is None:
            _LOG.warning(
                "hooks: no before_tool timing for tool_call_id=%s — elapsed_ms=0.0 (fabricated)",
                tool_call_id,
            )
            return 0.0
        return (time.monotonic_ns() - start_ns) / 1e6

    def _safe_append(payload: dict[str, Any], event_label: str) -> None:
        """Append payload to agent.jsonl; log (but never raise) on failure.

        Hooks must not abort the agent run on audit-emission failure.
        Failures are counted and surfaced in the finish line.
        """
        try:
            _append_agent_jsonl(case_dir, payload)
        except Exception:
            _append_failures[0] += 1
            _LOG.exception(
                "hooks: %s append failed (total_failures=%d case=%s)",
                event_label,
                _append_failures[0],
                case_dir.name,
            )

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
        _safe_append(payload, f"before_tool tool={call.tool_name}")
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
        elapsed_ms = _pop_elapsed_ms(call.tool_call_id)
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
        _safe_append(payload, f"after_tool tool={call.tool_name}")
        return result

    # ------------------------------------------------------------------
    # tool_execute_error — emit after_tool (success=False), then re-raise
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
    ) -> Never:
        elapsed_ms = _pop_elapsed_ms(call.tool_call_id)
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
        _safe_append(payload, f"tool_error tool={call.tool_name}")
        # Re-raise so Pydantic AI propagates the original tool error to the agent.
        # Returning here would be interpreted as recovery (tool appears to succeed
        # with None as result). See pydantic_ai/capabilities/hooks.py dispatcher.
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
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0
        hyp_id = _hyp_id(ctx.deps.stack)
        if hyp_id:
            # Split into separate try blocks so a token-record failure does not
            # skip the step increment — both must execute independently.
            try:
                budget.record_tokens(hyp_id, input_tokens, output_tokens)
            except Exception:
                _LOG.exception("hooks: budget token record failed hypothesis=%s", hyp_id)
            try:
                budget.record_step(hyp_id)
            except Exception:
                _LOG.exception("hooks: budget step record failed hypothesis=%s", hyp_id)
        payload: dict[str, Any] = {
            "ts": _ts_now(),
            "type": "step",
            "step_index": _step[0],
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "active_hypothesis_id": hyp_id,
        }
        _safe_append(payload, f"step step={_step[0]}")
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
        finalized_count = _close_open_hypotheses(stack)
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
            "audit_append_failures": _append_failures[0],
            "finalized_open_hypotheses_abandoned": finalized_count,
        }
        _safe_append(payload, "finish")
        if _append_failures[0] > 0:
            _LOG.error(
                "hooks: agent.jsonl is INCOMPLETE — %d append failure(s) during run; "
                "case=%s — verify-claim will report gaps in the audit trail",
                _append_failures[0],
                case_dir.name,
            )
        # TODO(epic-11): wire report.renderer.save_atomic here once merged.
        _LOG.info(
            "hooks: finish emitted (epic-11 save_atomic deferred) case=%s examiner=%s",
            case_dir.name,
            examiner,
        )
        return result

    return hooks


__all__ = ["build_investigator_hooks"]
