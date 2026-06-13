"""Hypothesis-driven IR investigator agent.

Entry point: ``investigate()``.  Factory: ``build_investigator()``.
"""

from __future__ import annotations

import importlib.resources
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models import Model, infer_model
from pydantic_ai.usage import UsageLimits

from silentwitness_agent.hypothesis.budget import BudgetEnforcer
from silentwitness_agent.hypothesis.stack import HypothesisStack
from silentwitness_common.types import CriticVerdict
from silentwitness_mcp._case_env import build_server_env

_LOG = logging.getLogger(__name__)

_DEFAULT_MODEL = "anthropic:claude-opus-4-7"
_DEFAULT_MAX_ITERS = 50

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
    # Populated by story-critic-verdict-handling; read by agent at turn start.
    pending_critiques: list[CriticVerdict] = Field(default_factory=list)


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
    max_iters: int


def _parse_max_iters_env(default: int) -> int:
    """Read SILENTWITNESS_MAX_ITERS; raises ValueError with a diagnostic message on bad input."""
    raw = os.environ.get("SILENTWITNESS_MAX_ITERS")
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(
            f"investigator: SILENTWITNESS_MAX_ITERS={raw!r} is not a valid integer; "
            f"set it to a positive integer (e.g. {default}) or unset it."
        ) from None
    if value < 1:
        raise ValueError(f"investigator: SILENTWITNESS_MAX_ITERS={value} must be >= 1.")
    return value


def _resolve_model(model_str: str) -> Model:
    """Route ``vllm:<base_url>`` through OpenAIChatModel; all others via Pydantic AI registry."""
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

    Reads ``SILENTWITNESS_MODEL`` (default ``anthropic:claude-opus-4-7``) and
    ``SILENTWITNESS_MAX_ITERS`` (default 50) at call time.  Constructor args
    override env values.

    ``case_dir`` / ``examiner`` are passed to the spawned MCP server via
    ``build_server_env`` so the server binds to this case (see
    :mod:`silentwitness_mcp._case_env`) — without it the server runs case-less
    and every evidence-bound tool refuses.

    ``hooks`` is optional so the agent can run without emitting per-step audit events.
    """
    model_str = (
        model if model is not None else os.environ.get("SILENTWITNESS_MODEL", _DEFAULT_MODEL)
    )
    max_iters = (
        max_iterations if max_iterations is not None else _parse_max_iters_env(_DEFAULT_MAX_ITERS)
    )
    if max_iters < 1:
        raise ValueError(f"max_iterations must be >= 1, got {max_iters}")

    resolved_model = _resolve_model(model_str)

    mcp_server = MCPServerStdio(
        "python",
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

    Catches ``UsageLimitExceeded`` and marks the active hypothesis ABANDONED
    with reason ``"MAX_ITERATIONS"`` before returning a partial result.
    Queued hypotheses are left in ACTIVE state in the audit log on this path.
    """
    from pydantic_ai.exceptions import UsageLimitExceeded

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
            total_tokens_consumed=usage.total_tokens,
        )

    except UsageLimitExceeded as exc:
        _LOG.warning(
            "investigate: UsageLimitExceeded after %d iterations for examiner=%s: %s",
            cfg.max_iters,
            examiner,
            exc,
            exc_info=True,
        )
        snap = stack.snapshot()
        if snap.active:
            try:
                stack.abandon(snap.active.id, "MAX_ITERATIONS")
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
            final_state="MAX_ITERATIONS",
            findings_staged=0,
            total_tool_calls=0,
            total_tokens_consumed=0,
        )


__all__ = [
    "CriticVerdict",
    "InvestigatorDeps",
    "InvestigatorResult",
    "build_investigator",
    "investigate",
]
