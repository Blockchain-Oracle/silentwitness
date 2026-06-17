"""Agent construction and execution seam for ``silentwitness investigate``."""

from __future__ import annotations

import contextlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from silentwitness_agent.cli_commands._live_render import DisplayState, build_display_hooks
from silentwitness_mcp.audit.chained_jsonl import append_chained_jsonl
from silentwitness_mcp.evidence.registry import EvidenceRegistry

type _FinalState = Literal["COMPLETED", "MAX_ITERATIONS", "BUDGET_EXHAUSTED", "ERROR"]


def _agent_usage_limits(request_limit: int | None, token_limit: int) -> Any:
    from pydantic_ai.usage import UsageLimits

    return UsageLimits(
        request_limit=request_limit,
        total_tokens_limit=token_limit,
        count_tokens_before_request=False,
    )


def _usage_limit_final_state(exc: BaseException) -> _FinalState:
    message = str(exc).lower()
    if "token" in message:
        return "BUDGET_EXHAUSTED"
    return "MAX_ITERATIONS"


def _agent_step_token_total(case_dir: Path) -> int:
    total = 0
    path = case_dir / "audit" / "agent.jsonl"
    if not path.is_file():
        return total
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return total
    for raw in lines:
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "step":
            continue
        total += int(event.get("input_tokens") or 0) + int(event.get("output_tokens") or 0)
    return total


async def _do_agent_run(
    case_dir: Path,
    examiner: str,
    *,
    model: str | None,
    max_iterations: int | None,
    max_tokens: int,
    state: DisplayState,
    is_tty: bool,
    t_start: float,
) -> Any:  # pragma: no cover - integration-only seam (monkeypatched in tests)
    """Build the investigator, run it, and return ``InvestigatorResult``."""
    from pydantic_ai.exceptions import UsageLimitExceeded

    from silentwitness_agent.hooks import NoActiveHypothesisToolError, build_investigator_hooks
    from silentwitness_agent.hypothesis.budget import BudgetEnforcer
    from silentwitness_agent.hypothesis.stack import HypothesisStack
    from silentwitness_agent.hypothesis_tools import register_hypothesis_tools
    from silentwitness_agent.investigator import (
        InvestigatorDeps,
        InvestigatorResult,
        build_investigator,
    )
    from silentwitness_agent.live_critic import (
        build_live_critic_hooks,
        register_pending_critique_instruction,
    )
    from silentwitness_agent.specialists._wiring import register_all_specialists

    stack = HypothesisStack(case_dir=case_dir, examiner=examiner)
    budget = BudgetEnforcer(default_token_budget=max_tokens)
    audit_hooks = build_investigator_hooks(case_dir, examiner, stack, budget)
    display_hooks = build_display_hooks(state, is_tty)
    critic_hooks = build_live_critic_hooks(case_dir, examiner, model=None)
    cfg = build_investigator(
        case_dir,
        examiner,
        model=model,
        max_iterations=max_iterations,
        hooks=[audit_hooks, display_hooks, critic_hooks],
    )
    register_hypothesis_tools(cfg.agent)
    register_pending_critique_instruction(cfg.agent)
    register_all_specialists(cfg.agent, model=model, shared_server=cfg.mcp_server)
    deps = InvestigatorDeps(
        case_dir=case_dir,
        examiner=examiner,
        stack=stack,
        budget=budget,
        request_limit=cfg.max_iters,
        total_token_limit=max_tokens,
    )

    def _build_result(
        final_state: _FinalState,
        findings_staged: int,
        total_tool_calls: int,
        total_tokens_consumed: int,
    ) -> InvestigatorResult:
        snap = deps.stack.snapshot()
        return InvestigatorResult(
            hypotheses_formed=len(snap.history) + len(snap.queued) + (1 if snap.active else 0),
            hypotheses_confirmed=sum(
                1 for h in snap.history if str(h.status).upper() == "CONFIRMED"
            ),
            hypotheses_pivoted=snap.total_pivot_count,
            hypotheses_abandoned=sum(
                1 for h in snap.history if str(h.status).upper() == "ABANDONED"
            ),
            findings_staged=findings_staged,
            total_tool_calls=total_tool_calls,
            total_tokens_consumed=total_tokens_consumed,
            time_elapsed_ms=(time.monotonic() - t_start) * 1000,
            final_state=final_state,
            model_used=cfg.model_str,
        )

    def _emit_finish(final_state: _FinalState, total_tokens_consumed: int) -> None:
        snap = deps.stack.snapshot()
        append_chained_jsonl(
            case_dir / "audit" / "agent.jsonl",
            {
                "ts": datetime.now(UTC).isoformat(),
                "type": "finish",
                "final_state": final_state,
                "stack_snapshot": snap.model_dump(mode="json"),
                "model_used": cfg.model_str,
                "total_tokens_consumed": total_tokens_consumed,
                "audit_append_failures": 0,
            },
        )

    evidence_records = EvidenceRegistry(case_dir=case_dir).list_all()
    evidence_block = (
        "\n".join(f"- {rec.path} ({rec.type.value})" for rec in evidence_records)
        or "- (no evidence registered)"
    )
    try:
        run_result = await cfg.agent.run(
            f"Investigate case {case_dir.name}.\n\n"
            "This evidence is parsed into the searchable case index - discover with "
            "search_evidence/timeline/get_record (do NOT read raw artifacts):\n"
            f"{evidence_block}\n\n"
            "Form your first hypothesis and analyse the evidence by querying the index.",
            deps=deps,
            usage_limits=_agent_usage_limits(cfg.max_iters, max_tokens),
        )
    except UsageLimitExceeded as exc:
        final_state = _usage_limit_final_state(exc)
        snap = deps.stack.snapshot()
        if snap.active:
            with contextlib.suppress(Exception):
                deps.stack.abandon(snap.active.id, final_state)
        total_tokens = _agent_step_token_total(case_dir)
        _emit_finish(final_state, total_tokens)
        return _build_result(final_state, 0, 0, total_tokens)
    except NoActiveHypothesisToolError:
        total_tokens = _agent_step_token_total(case_dir)
        _emit_finish("ERROR", total_tokens)
        return _build_result("ERROR", 0, 0, total_tokens)

    snap = deps.stack.snapshot()
    usage = run_result.usage
    return InvestigatorResult(
        hypotheses_formed=len(snap.history) + len(snap.queued) + (1 if snap.active else 0),
        hypotheses_confirmed=sum(1 for h in snap.history if str(h.status).upper() == "CONFIRMED"),
        hypotheses_pivoted=snap.total_pivot_count,
        hypotheses_abandoned=sum(1 for h in snap.history if str(h.status).upper() == "ABANDONED"),
        findings_staged=run_result.output.findings_staged,
        total_tool_calls=run_result.output.total_tool_calls,
        total_tokens_consumed=getattr(usage, "total_tokens", 0) or 0,
        time_elapsed_ms=(time.monotonic() - t_start) * 1000,
        final_state="COMPLETED",
        model_used=cfg.model_str,
    )


__all__ = [
    "_agent_usage_limits",
    "_do_agent_run",
    "_usage_limit_final_state",
]
