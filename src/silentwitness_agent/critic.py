"""Closed-loop critic agent for evaluating staged findings against cited evidence.

The critic is a separate Pydantic AI Agent with a fresh context window.
It receives ONLY the staged finding text + its cited evidence quotes — never
the investigator's reasoning chain or hypothesis history.  This fresh-context
property is the architectural mechanism that breaks the sycophancy loop
(architecture.md §5.5).

Entry point: ``critique()``.  Factory: ``build_critic()``.
"""

from __future__ import annotations

import importlib.resources
import logging
import os
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent
from pydantic_ai.models import Model, infer_model
from pydantic_ai.usage import UsageLimits

from silentwitness_agent._caching import cache_settings
from silentwitness_agent.model_policy import (
    DEFAULT_CRITIC_MODEL,
    cost_optimized_model_for_provider,
)
from silentwitness_common.types import Confidence

_LOG = logging.getLogger(__name__)

_DEFAULT_MODEL = DEFAULT_CRITIC_MODEL
_CRITIC_FAST_MODEL = "anthropic:claude-haiku-4-5"

try:
    _SYSTEM_PROMPT: str = (
        importlib.resources.files("silentwitness_agent.prompts")
        .joinpath("critic.md")
        .read_text(encoding="utf-8")
    )
except FileNotFoundError as _exc:
    raise FileNotFoundError(
        "critic: 'critic.md' is missing from the 'silentwitness_agent.prompts' "
        "package. Re-install the package or ensure the file exists at "
        "src/silentwitness_agent/prompts/critic.md."
    ) from _exc


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class StagedFinding(BaseModel):
    """A single investigator finding submitted for peer review.

    The critic receives ONLY these fields — no investigator context.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    finding_id: str = Field(min_length=1)
    observation_text: str = Field(min_length=1)
    interpretation_text: str = Field(min_length=1)
    confidence: Confidence
    cited_audit_ids: list[str] = Field(default_factory=list)
    # The verbatim evidence the finding cites — the span_texts from the
    # observation's cited_spans, already verified by the citation gate as real
    # substrings of index records. The critic evaluates the finding against
    # exactly these bytes (no blob re-reading post index-citation rewire).
    cited_evidence: tuple[str, ...] = Field(default_factory=tuple)


class CriticVerdictRecord(BaseModel):
    """Per-finding verdict from the critic agent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    finding_id: str = Field(min_length=1)
    verdict: Literal["AGREE", "CHALLENGE", "REJECT"]
    reason: str = Field(min_length=1)
    suggested_revision: str | None = None
    missing_corroboration: list[str] = Field(default_factory=list)


class CriticReport(BaseModel):
    """Structured output returned by the critic agent after reviewing all findings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    verdicts: list[CriticVerdictRecord]
    tokens_spent: int = Field(ge=0)
    time_elapsed_ms: float = Field(ge=0.0)


class CriticDeps(BaseModel):
    """Dependencies injected into the critic agent.

    Contains ONLY the staged findings — no investigator reasoning chain.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    case_dir: Path
    examiner: str = Field(min_length=1)
    findings_to_review: list[StagedFinding]


# ---------------------------------------------------------------------------
# Model resolution
# ---------------------------------------------------------------------------


def _resolve_critic_model(model_str: str) -> Model:
    """Resolve model string to a Pydantic AI Model instance."""
    return infer_model(model_str)


def _select_model_str(model: str | None) -> str:
    """Resolve the critic model string from args → env → default."""
    if model is not None:
        return model
    if os.environ.get("SILENTWITNESS_CRITIC_FAST") == "1":
        return _CRITIC_FAST_MODEL
    critic_env = os.environ.get("SILENTWITNESS_CRITIC_MODEL")
    if critic_env:
        return critic_env
    global_model = os.environ.get("SILENTWITNESS_MODEL")
    if global_model:
        return cost_optimized_model_for_provider(global_model)
    return _DEFAULT_MODEL


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_critic(model: str | None = None) -> Agent[CriticDeps, CriticReport]:
    """Build and return the critic Agent.

    Model resolution order (first defined wins):
    1. ``model`` argument
    2. ``SILENTWITNESS_CRITIC_FAST=1`` → haiku
    3. ``SILENTWITNESS_CRITIC_MODEL`` env var
    4. provider-aware cheap sibling of ``SILENTWITNESS_MODEL``
    5. Hard default: ``anthropic:claude-haiku-4-5``

    The critic has NO MCP toolset — it reasons purely over inline evidence.
    This is architecturally required: tool access would pollute the fresh context.
    """
    model_str = _select_model_str(model)
    resolved_model = _resolve_critic_model(model_str)

    return Agent(
        model=resolved_model,
        deps_type=CriticDeps,
        output_type=CriticReport,
        system_prompt=_SYSTEM_PROMPT,
        model_settings=cache_settings(resolved_model),
    )


def critic_usage_limits(
    model: Any,
    *,
    request_limit: int | None,
    token_limit: int | None,
) -> UsageLimits:
    """Build critic limits, avoiding token pre-counting for TestModel."""
    return UsageLimits(
        request_limit=request_limit,
        total_tokens_limit=token_limit,
        count_tokens_before_request=model.__class__.__name__ != "TestModel",
    )


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------


def _build_critique_prompt(findings: list[StagedFinding]) -> str:
    """Render the per-run user prompt with findings and their cited evidence.

    The cited evidence is the verbatim span_texts the investigator quoted from
    the index (citation-gate-verified). The critic judges whether the
    observation + interpretation are actually supported by those bytes."""
    parts: list[str] = ["Review the following staged findings against the cited evidence.\n"]
    for f in findings:
        parts.append(f"--- Finding {f.finding_id} ---")
        parts.append(f"Observation: {f.observation_text}")
        parts.append(f"Interpretation: {f.interpretation_text}")
        parts.append(f"Confidence: {f.confidence}")
        if f.cited_audit_ids:
            parts.append("Cited source tools (audit_ids): " + ", ".join(f.cited_audit_ids))
        if f.cited_evidence:
            parts.append("Cited evidence (verbatim quotes from the index):")
            parts.extend(f"  • {ev}" for ev in f.cited_evidence)
        else:
            parts.append("Cited evidence: (none — the finding cites no evidence)")
        parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def critique(
    case_dir: Path,
    examiner: str,
    findings: list[StagedFinding],
    *,
    model: str | None = None,
    usage: Any | None = None,
    request_limit: int | None = None,
    total_token_limit: int | None = None,
) -> CriticReport:
    """Run the critic against a list of staged findings; return a CriticReport.

    Each finding carries its cited evidence inline (the verbatim span_texts the
    investigator quoted from the index), so the critic needs no filesystem
    access — it judges the finding against exactly the citation-gate-verified
    bytes."""
    if not findings:
        return CriticReport(verdicts=[], tokens_spent=0, time_elapsed_ms=0.0)

    t0 = time.monotonic()

    prompt = _build_critique_prompt(findings)
    deps = CriticDeps(case_dir=case_dir, examiner=examiner, findings_to_review=findings)

    agent = build_critic(model=model)
    run_kwargs: dict[str, Any] = {"deps": deps}
    if usage is not None:
        run_kwargs["usage"] = usage
    if request_limit is not None or total_token_limit is not None:
        run_kwargs["usage_limits"] = critic_usage_limits(
            agent.model,
            request_limit=request_limit,
            token_limit=total_token_limit,
        )
    run_result = await agent.run(prompt, **run_kwargs)

    elapsed_ms = (time.monotonic() - t0) * 1000.0
    # SDK-authoritative token count; wall-clock elapsed replaces any model-reported value.
    return CriticReport(
        verdicts=run_result.output.verdicts,
        tokens_spent=run_result.usage.total_tokens or 0,
        time_elapsed_ms=elapsed_ms,
    )


__all__ = [
    "CriticDeps",
    "CriticReport",
    "CriticVerdictRecord",
    "StagedFinding",
    "build_critic",
    "critic_usage_limits",
    "critique",
]
