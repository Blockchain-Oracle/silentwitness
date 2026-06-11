"""Investigator Pydantic AI agent — hypothesis-driven IR analyst.

Model-agnostic: SILENTWITNESS_MODEL env var selects the provider (default
``anthropic:claude-opus-4-7``).  Supports Anthropic, OpenAI, Google, Ollama,
and vLLM via the Pydantic AI model string protocol.

Entry point: ``investigate()`` coroutine.  Factory: ``build_investigator()``.
"""

from __future__ import annotations

import importlib.resources
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.usage import UsageLimits

from silentwitness_agent.hypothesis.budget import BudgetEnforcer
from silentwitness_agent.hypothesis.stack import HypothesisStack

_LOG = logging.getLogger(__name__)

# Placeholder until story-critic-verdict-handling ships the real type.
CriticVerdict = Any

_DEFAULT_MODEL = "anthropic:claude-opus-4-7"
_DEFAULT_MAX_ITERS = 50

_SYSTEM_PROMPT: str = (
    importlib.resources.files("silentwitness_agent.prompts")
    .joinpath("investigator.md")
    .read_text(encoding="utf-8")
)


class InvestigatorDeps(BaseModel):
    """Runtime dependencies injected into every agent turn."""

    model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True)

    case_dir: Path
    examiner: str
    stack: HypothesisStack
    budget: BudgetEnforcer
    # Bridge for story-critic-verdict-handling: critic handler appends CHALLENGE
    # verdicts here; agent reads them at the start of each turn.
    pending_critiques: list[CriticVerdict] = []


class InvestigatorResult(BaseModel):
    """Summary written at end of every investigation run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    hypotheses_formed: int
    hypotheses_confirmed: int
    hypotheses_pivoted: int
    hypotheses_abandoned: int
    findings_staged: int
    total_tool_calls: int
    total_tokens_consumed: int
    time_elapsed_ms: float
    final_state: Literal["COMPLETED", "MAX_ITERATIONS", "BUDGET_EXHAUSTED", "ERROR"]
    model_used: str


@dataclass
class _AgentConfig:
    """Bundled config produced by ``build_investigator`` and consumed by ``investigate``."""

    agent: Agent[InvestigatorDeps, InvestigatorResult]
    model_str: str
    max_iters: int


def _resolve_model(model_str: str) -> Any:
    """Return a Pydantic AI model instance for the given model string.

    vLLM exposes an OpenAI-compatible API; ``vllm:<base_url>`` is routed
    through ``OpenAIChatModel`` with a custom provider pointed at that URL.
    All other strings are passed verbatim (resolved by Pydantic AI's registry).
    """
    if model_str.startswith("vllm:"):
        # vLLM uses an OpenAI-compatible endpoint; route through OpenAIChatModel.
        from openai import AsyncOpenAI
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        base_url = model_str[len("vllm:") :]
        provider = OpenAIProvider(openai_client=AsyncOpenAI(base_url=base_url, api_key="vllm"))
        return OpenAIChatModel("gpt-4o", provider=provider)
    return model_str


def build_investigator(
    model: str | None = None,
    max_iterations: int | None = None,
    hooks: list[Any] | None = None,
) -> _AgentConfig:
    """Build and return an ``_AgentConfig`` wrapping the configured Investigator Agent.

    Reads ``SILENTWITNESS_MODEL`` (default ``anthropic:claude-opus-4-7``) and
    ``SILENTWITNESS_MAX_ITERS`` (default 50) at call time.  Constructor args
    override env values.

    ``hooks`` is intentionally optional — story-investigator-hooks will pass
    a populated list when it wraps this factory.  Without hooks the agent
    still runs but emits no per-step audit events.
    """
    model_str = model or os.environ.get("SILENTWITNESS_MODEL", _DEFAULT_MODEL)
    max_iters = max_iterations or int(
        os.environ.get("SILENTWITNESS_MAX_ITERS", str(_DEFAULT_MAX_ITERS))
    )
    resolved_model = _resolve_model(model_str)

    mcp_server = MCPServerStdio(
        "python",
        ["-m", "silentwitness_mcp"],
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
    )
    return _AgentConfig(agent=agent, model_str=model_str, max_iters=max_iters)


async def investigate(
    case_dir: Path,
    examiner: str,
    prompt: str,
    *,
    model: str | None = None,
    max_iterations: int | None = None,
    hooks: list[Any] | None = None,
) -> InvestigatorResult:
    """Run a full investigation; returns an ``InvestigatorResult``.

    Builds the agent, constructs deps, and drives ``agent.run()``.  Catches
    ``UsageLimitExceeded`` and marks all still-ACTIVE hypotheses ABANDONED
    with reason ``"MAX_ITERATIONS"`` before returning a partial result.
    """
    from pydantic_ai.exceptions import UsageLimitExceeded

    cfg = build_investigator(model=model, max_iterations=max_iterations, hooks=hooks)
    stack = HypothesisStack(case_dir=case_dir, examiner=examiner)
    budget = BudgetEnforcer()
    deps = InvestigatorDeps(
        case_dir=case_dir,
        examiner=examiner,
        stack=stack,
        budget=budget,
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
            usage_limits=UsageLimits(request_limit=cfg.max_iters),
        )
        usage = run.usage
        return _build_result(
            final_state="COMPLETED",
            findings_staged=run.output.findings_staged,
            total_tool_calls=run.output.total_tool_calls,
            total_tokens_consumed=usage.total_tokens or 0,
        )

    except UsageLimitExceeded:
        _LOG.warning(
            "investigate: UsageLimitExceeded after %d iterations for examiner=%s",
            cfg.max_iters,
            examiner,
        )
        snap = stack.snapshot()
        if snap.active:
            stack.abandon(snap.active.id, "MAX_ITERATIONS")
        return _build_result(
            final_state="MAX_ITERATIONS",
            findings_staged=0,
            total_tool_calls=0,
            total_tokens_consumed=0,
        )


__all__ = [
    "CriticVerdict",
    "InvestigatorDeps",
    "InvestigatorResult",
    "_AgentConfig",
    "build_investigator",
    "investigate",
]
