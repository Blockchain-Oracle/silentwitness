"""Hypothesis-driven IR investigator agent.

Entry point: ``investigate()``.  Factory: ``build_investigator()``.
"""

from __future__ import annotations

import importlib.resources
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models import Model, infer_model
from pydantic_ai.usage import UsageLimits

from silentwitness_agent._caching import cache_settings
from silentwitness_agent.config import DEFAULT_MAX_STEPS, DEFAULT_MAX_TOKENS
from silentwitness_agent.critic import CriticVerdictRecord
from silentwitness_agent.hypothesis.budget import BudgetEnforcer
from silentwitness_agent.hypothesis.stack import HypothesisStack
from silentwitness_agent.model_policy import DEFAULT_INVESTIGATOR_MODEL, normalize_model_string
from silentwitness_mcp._case_env import build_server_env

_LOG = logging.getLogger(__name__)

_DEFAULT_MODEL = DEFAULT_INVESTIGATOR_MODEL
_DEFAULT_MAX_ITERS: int | None = DEFAULT_MAX_STEPS
_DEFAULT_MAX_TOKENS = DEFAULT_MAX_TOKENS
# How many times the coverage gate may bounce the agent back before it is allowed to
# finalize regardless — so a genuinely-unanswerable question can't deadlock the run. Each
# bounce consumes one of the Agent ``retries`` below, which is SHARED with tool-call and
# output-schema retries — so the budget is set with headroom above the cap to leave room
# for those without tripping pydantic-ai's "exceeded retries" error.
_MAX_COVERAGE_GATE_ATTEMPTS = 3
_OUTPUT_RETRIES = 12

try:
    _SYSTEM_PROMPT: str = (
        importlib.resources.files("silentwitness_agent.prompts")
        .joinpath("investigator.md")
        .read_text(encoding="utf-8")
    )
except FileNotFoundError as _exc:
    raise FileNotFoundError(
        "investigator: 'investigator.md' is missing from the 'silentwitness_agent.prompts' "
        "package. Re-install the package or ensure the file exists at "
        "src/silentwitness_agent/prompts/investigator.md."
    ) from _exc


class InvestigatorDeps(BaseModel):
    model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True, validate_assignment=True)

    case_dir: Path
    examiner: str = Field(min_length=1)
    stack: HypothesisStack
    budget: BudgetEnforcer
    # Populated by the live critic handler when a CHALLENGE fires; surfaced back
    # into the agent's context each turn by the pending-critique instruction so
    # the investigator can revise or corroborate the challenged finding.
    pending_critiques: list[CriticVerdictRecord] = Field(default_factory=list)
    # How many times the coverage gate has bounced this run back (see the output
    # validator); capped at _MAX_COVERAGE_GATE_ATTEMPTS so an unanswerable question
    # can't deadlock the agent.
    coverage_gate_attempts: int = 0
    # Shared Pydantic-AI request cap for nested specialist calls. None disables
    # Pydantic's own default cap, which is otherwise 50 and can terminate long IR
    # runs inside a specialist even when the outer investigator was configured higher.
    request_limit: int | None = None
    total_token_limit: int | None = None


class InvestigatorResult(BaseModel):
    """findings_staged and total_tool_calls are agent-reported; total_tokens from run.usage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    hypotheses_formed: int = Field(ge=0)
    hypotheses_confirmed: int = Field(ge=0)
    hypotheses_pivoted: int = Field(ge=0)
    hypotheses_abandoned: int = Field(ge=0)
    findings_staged: int = Field(ge=0)
    total_tool_calls: int = Field(ge=0)
    total_tokens_consumed: int = Field(ge=0)
    time_elapsed_ms: float = Field(ge=0.0)
    final_state: Literal["COMPLETED", "MAX_ITERATIONS", "BUDGET_EXHAUSTED", "ERROR"]
    model_used: str = Field(min_length=1)


@dataclass(frozen=True)
class _AgentConfig:
    agent: Agent[InvestigatorDeps, InvestigatorResult]
    model_str: str
    max_iters: int | None
    # The investigator's MCP server, exposed so specialists can SHARE it (one
    # subprocess, one AuditLogger). pydantic-ai's MCPServer is ref-counted, so
    # nested specialist runs reuse the same session instead of spawning a second
    # case-bound server (which would collide on the AuditLogger flock).
    # INVARIANT: this is the same object passed to Agent(toolsets=[...]) above —
    # sharing only yields one subprocess because it is that identical server.
    mcp_server: MCPServerStdio


def _parse_max_iters_env(default: int | None) -> int | None:
    """Read SILENTWITNESS_MAX_ITERS/MAX_STEPS with diagnostics on bad input."""
    env_key = "SILENTWITNESS_MAX_ITERS"
    raw = os.environ.get(env_key)
    if raw is None:
        env_key = "SILENTWITNESS_MAX_STEPS"
        raw = os.environ.get(env_key)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(
            f"investigator: {env_key}={raw!r} is not a valid integer; "
            "set it to a positive integer (e.g. 80)."
        ) from None
    if value < 1:
        raise ValueError(f"investigator: {env_key}={value} must be >= 1.")
    return value


def _usage_limits(
    request_limit: int | None,
    token_limit: int,
    *,
    model: Any = None,
) -> UsageLimits:
    _ = model
    return UsageLimits(
        request_limit=request_limit,
        total_tokens_limit=token_limit,
        count_tokens_before_request=False,
    )


def _usage_limit_final_state(
    exc: BaseException,
) -> Literal["MAX_ITERATIONS", "BUDGET_EXHAUSTED"]:
    if "token" in str(exc).lower():
        return "BUDGET_EXHAUSTED"
    return "MAX_ITERATIONS"


def _resolve_model(model_str: str) -> Model:
    """Route ``vllm:<base_url>`` through OpenAIChatModel; all others via Pydantic AI registry."""
    model_str = normalize_model_string(model_str)
    if model_str.startswith("vllm:"):
        base_url = model_str[len("vllm:") :]
        if not base_url or not base_url.startswith(("http://", "https://")):
            raise ValueError(
                f"investigator: SILENTWITNESS_MODEL={model_str!r} — vllm: prefix requires "
                f"a full HTTP(S) base URL, e.g. 'vllm:http://localhost:8000/v1'. "
                f"Got base_url={base_url!r}."
            )
        try:
            from openai import AsyncOpenAI
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.openai import OpenAIProvider
        except ImportError as exc:
            raise ImportError(
                "investigator: vllm: routing requires the 'openai' package. "
                "Install it with: pip install openai"
            ) from exc
        provider = OpenAIProvider(openai_client=AsyncOpenAI(base_url=base_url, api_key="vllm"))
        return OpenAIChatModel("gpt-4o", provider=provider)
    return infer_model(model_str)


def build_investigator(
    case_dir: Path,
    examiner: str,
    model: str | None = None,
    max_iterations: int | None = None,
    hooks: list[Any] | None = None,
) -> _AgentConfig:
    """Build and return an ``_AgentConfig`` wrapping the configured Investigator Agent.

    Reads ``SILENTWITNESS_MODEL`` (default ``anthropic:claude-sonnet-4-6``) and
    ``SILENTWITNESS_MAX_ITERS`` / ``SILENTWITNESS_MAX_STEPS`` at call time.
    Constructor args override env values.

    ``case_dir`` / ``examiner`` are passed to the spawned MCP server via
    ``build_server_env`` so the server binds to this case (see
    :mod:`silentwitness_mcp._case_env`) — without it the server runs case-less
    and every evidence-bound tool refuses.

    ``hooks`` is optional so the agent can run without emitting per-step audit events.
    """
    model_str = normalize_model_string(
        model if model is not None else os.environ.get("SILENTWITNESS_MODEL", _DEFAULT_MODEL)
    )
    max_iters = (
        max_iterations if max_iterations is not None else _parse_max_iters_env(_DEFAULT_MAX_ITERS)
    )
    if max_iters is not None and max_iters < 1:
        raise ValueError(f"max_iterations must be >= 1, got {max_iters}")

    resolved_model = _resolve_model(model_str)

    mcp_server = MCPServerStdio(
        # sys.executable, not bare "python" — the latter is often absent (the SIFT
        # OVA / VPS ship only python3 + the venv interpreter), which crashed the
        # real ROCBA run with "No such file or directory: 'python'".
        sys.executable,
        ["-m", "silentwitness_mcp"],
        env=build_server_env(case_dir, examiner, model_str),
        sampling_model=resolved_model,
    )

    capabilities: list[Any] = hooks or []

    agent: Agent[InvestigatorDeps, InvestigatorResult] = Agent(
        model=resolved_model,
        deps_type=InvestigatorDeps,
        output_type=InvestigatorResult,
        system_prompt=_SYSTEM_PROMPT,
        toolsets=[mcp_server],
        capabilities=capabilities,
        model_settings=cache_settings(resolved_model),
        retries=_OUTPUT_RETRIES,
    )

    @agent.output_validator
    def _enforce_question_coverage(
        ctx: RunContext[InvestigatorDeps], output: InvestigatorResult
    ) -> InvestigatorResult:
        """Refuse to finalize while a Key Question has no supporting observation.

        Structural breadth: instead of trusting the model to explore, the gate reads the
        recorded observations and bounces the agent back (``ModelRetry``) naming each
        unanswered question + the artifact types that bear on it — until all five are
        addressed or the bounce budget is spent (so an unanswerable question can't
        deadlock the run)."""
        from silentwitness_agent.coverage import analyze_coverage, coverage_gap_message

        report = analyze_coverage(ctx.deps.case_dir)
        if ctx.deps.coverage_gate_attempts >= _MAX_COVERAGE_GATE_ATTEMPTS:
            # Bounce budget spent — finalize, but do NOT let an incomplete investigation
            # masquerade as complete: surface the still-open questions loudly.
            if not report.is_complete:
                _LOG.warning(
                    "coverage gate gave up after %d attempts; UNANSWERED Key Questions: %s",
                    ctx.deps.coverage_gate_attempts,
                    ", ".join(q.qid for q in report.uncovered),
                )
            return output
        message = coverage_gap_message(report)
        if message is None:
            return output
        ctx.deps.coverage_gate_attempts += 1
        raise ModelRetry(message)

    return _AgentConfig(
        agent=agent, model_str=model_str, max_iters=max_iters, mcp_server=mcp_server
    )


async def investigate(
    case_dir: Path,
    examiner: str,
    prompt: str,
    *,
    model: str | None = None,
    max_iterations: int | None = None,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
    hooks: list[Any] | None = None,
) -> InvestigatorResult:
    """Run a full investigation; returns an ``InvestigatorResult``.

    Catches ``UsageLimitExceeded`` and marks the active hypothesis ABANDONED
    with reason ``"MAX_ITERATIONS"`` before returning a partial result.
    Queued hypotheses are left in ACTIVE state in the audit log on this path.
    """
    from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded

    cfg = build_investigator(
        case_dir, examiner, model=model, max_iterations=max_iterations, hooks=hooks
    )
    stack = HypothesisStack(case_dir=case_dir, examiner=examiner)
    budget = BudgetEnforcer()
    deps = InvestigatorDeps(
        case_dir=case_dir,
        examiner=examiner,
        stack=stack,
        budget=budget,
        request_limit=cfg.max_iters,
        total_token_limit=max_tokens,
    )

    t_start = time.monotonic()

    def _build_result(
        final_state: Literal["COMPLETED", "MAX_ITERATIONS", "BUDGET_EXHAUSTED", "ERROR"],
        findings_staged: int,
        total_tool_calls: int,
        total_tokens_consumed: int,
    ) -> InvestigatorResult:
        snap = stack.snapshot()
        return InvestigatorResult(
            hypotheses_formed=len(snap.history) + (1 if snap.active else 0),
            hypotheses_confirmed=sum(1 for h in snap.history if h.status.value == "CONFIRMED"),
            hypotheses_pivoted=snap.total_pivot_count,
            hypotheses_abandoned=sum(1 for h in snap.history if h.status.value == "ABANDONED"),
            findings_staged=findings_staged,
            total_tool_calls=total_tool_calls,
            total_tokens_consumed=total_tokens_consumed,
            time_elapsed_ms=(time.monotonic() - t_start) * 1000,
            final_state=final_state,
            model_used=cfg.model_str,
        )

    try:
        run = await cfg.agent.run(
            prompt,
            deps=deps,
            usage_limits=_usage_limits(cfg.max_iters, max_tokens, model=cfg.agent.model),
        )
        usage = run.usage
        return _build_result(
            final_state="COMPLETED",
            findings_staged=run.output.findings_staged,
            total_tool_calls=run.output.total_tool_calls,
            total_tokens_consumed=usage.total_tokens,
        )

    except UsageLimitExceeded as exc:
        _LOG.warning(
            "investigate: UsageLimitExceeded after %s iterations for examiner=%s: %s",
            cfg.max_iters,
            examiner,
            exc,
            exc_info=True,
        )
        final_state = _usage_limit_final_state(exc)
        snap = stack.snapshot()
        if snap.active:
            try:
                stack.abandon(snap.active.id, final_state)
            except Exception as abandon_exc:
                _LOG.error(
                    "investigate: failed to emit ABANDON for %s after MAX_ITERATIONS"
                    " (examiner=%s): %s",
                    snap.active.id,
                    examiner,
                    abandon_exc,
                    exc_info=True,
                )
        # findings_staged and total_tool_calls are unavailable from UsageLimitExceeded.
        return _build_result(
            final_state=final_state,
            findings_staged=0,
            total_tool_calls=0,
            total_tokens_consumed=0,
        )

    except UnexpectedModelBehavior as exc:
        # e.g. the shared retry budget (tool + output + coverage-gate bounces) is exhausted.
        # Return a partial ERROR result rather than crashing the whole run — and abandon the
        # active hypothesis so it isn't left ACTIVE in the audit log.
        _LOG.warning(
            "investigate: model behaviour error for examiner=%s (likely retry budget "
            "exhausted): %s",
            examiner,
            exc,
            exc_info=True,
        )
        snap = stack.snapshot()
        if snap.active:
            try:
                stack.abandon(snap.active.id, "ERROR")
            except Exception as abandon_exc:
                _LOG.error(
                    "investigate: failed to emit ABANDON for %s after ERROR (examiner=%s): %s",
                    snap.active.id,
                    examiner,
                    abandon_exc,
                    exc_info=True,
                )
        return _build_result(
            final_state="ERROR", findings_staged=0, total_tool_calls=0, total_tokens_consumed=0
        )


__all__ = [
    "CriticVerdictRecord",
    "InvestigatorDeps",
    "InvestigatorResult",
    "build_investigator",
    "investigate",
]
