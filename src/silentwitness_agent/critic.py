"""Closed-loop critic agent for evaluating staged findings against cited evidence.

The critic is a separate Pydantic AI Agent with a fresh context window.
It receives ONLY the staged finding text + cited blob contents — never the
investigator's reasoning chain or hypothesis history.  This fresh-context
property is the architectural mechanism that breaks the sycophancy loop
(architecture.md §5.5).

Entry point: ``critique()``.  Factory: ``build_critic()``.
"""

from __future__ import annotations

import hashlib
import importlib.resources
import logging
import os
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent
from pydantic_ai.models import Model, infer_model

from silentwitness_agent._caching import cache_settings
from silentwitness_common.types import Confidence

_LOG = logging.getLogger(__name__)

_DEFAULT_MODEL = "anthropic:claude-opus-4-7"
_CRITIC_FAST_MODEL = "anthropic:claude-haiku-4-5"
# Max bytes of blob content passed inline to avoid flooding the critic's context.
_BLOB_TRUNCATION_BYTES = 50_000

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
    cited_blob_paths: list[Path] = Field(default_factory=list)


class CriticVerdictRecord(BaseModel):
    """Per-finding verdict from the critic agent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    finding_id: str = Field(min_length=1)
    verdict: Literal["AGREE", "CHALLENGE", "REJECT"]
    reason: str = Field(min_length=1)
    suggested_revision: str | None = None
    missing_corroboration: list[str] = Field(default_factory=list)


# Backwards-compatible alias: avoids shadowing silentwitness_common.types.CriticVerdict (StrEnum).
CriticVerdict = CriticVerdictRecord


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
    # Fall back to investigator model, then hard default.
    return os.environ.get("SILENTWITNESS_MODEL", _DEFAULT_MODEL)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_critic(model: str | None = None) -> Agent[CriticDeps, CriticReport]:
    """Build and return the critic Agent.

    Model resolution order (first defined wins):
    1. ``model`` argument
    2. ``SILENTWITNESS_CRITIC_FAST=1`` → haiku
    3. ``SILENTWITNESS_CRITIC_MODEL`` env var
    4. ``SILENTWITNESS_MODEL`` env var
    5. Hard default: ``anthropic:claude-opus-4-7``

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


# ---------------------------------------------------------------------------
# Blob loading helpers
# ---------------------------------------------------------------------------


def _load_blob(path: Path) -> str:
    """Read a blob file; return empty string if missing.

    Files over _BLOB_TRUNCATION_BYTES are cut with a ``[TRUNCATED]`` marker.
    Non-UTF-8 files (binary) get a one-line descriptor with a SHA-256 prefix
    rather than silently replacing bytes, which would corrupt evidence text.
    """
    if not path.exists():
        _LOG.warning("critic: blob not found path=%s", path)
        return ""
    content = path.read_bytes()
    truncated = len(content) > _BLOB_TRUNCATION_BYTES
    if truncated:
        _LOG.info(
            "critic: blob truncated path=%s original_bytes=%d limit=%d",
            path,
            len(content),
            _BLOB_TRUNCATION_BYTES,
        )
        content = content[:_BLOB_TRUNCATION_BYTES]
    try:
        return content.decode("utf-8") + ("\n[TRUNCATED]" if truncated else "")
    except UnicodeDecodeError:
        digest = hashlib.sha256(content).hexdigest()[:16]
        return f"[BINARY BLOB — {len(content)} bytes, sha256={digest}...]"


def _build_critique_prompt(findings: list[StagedFinding], blob_contents: dict[str, str]) -> str:
    """Render the per-run user prompt with findings and inline blob evidence."""
    parts: list[str] = ["Review the following staged findings against the cited evidence.\n"]
    for f in findings:
        parts.append(f"--- Finding {f.finding_id} ---")
        parts.append(f"Observation: {f.observation_text}")
        parts.append(f"Interpretation: {f.interpretation_text}")
        parts.append(f"Confidence: {f.confidence}")
        if f.cited_audit_ids:
            parts.append("Cited audit IDs: " + ", ".join(f.cited_audit_ids))
        for aid in f.cited_audit_ids:
            blob_text = blob_contents.get(aid, "")
            if blob_text:
                parts.append(f"\nBlob [{aid}]:\n{blob_text}")
            else:
                parts.append(f"\nBlob [{aid}]: (not found)")
        for bp in f.cited_blob_paths:
            blob_text = blob_contents.get(str(bp), "")
            if blob_text:
                parts.append(f"\nBlob [{bp.name}]:\n{blob_text}")
            else:
                parts.append(f"\nBlob [{bp.name}]: (not found)")
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
) -> CriticReport:
    """Run the critic against a list of staged findings; return a CriticReport.

    Loads cited blob contents from ``case_dir/audit/blobs/<audit_id>.txt``
    and from each ``cited_blob_paths`` entry.  Blobs over 50 KB are truncated
    with a ``[TRUNCATED]`` marker so the critic's context remains manageable.
    """
    if not findings:
        return CriticReport(verdicts=[], tokens_spent=0, time_elapsed_ms=0.0)

    t0 = time.monotonic()

    blob_contents: dict[str, str] = {}
    blobs_dir = case_dir / "audit" / "blobs"
    for finding in findings:
        for aid in finding.cited_audit_ids:
            if aid not in blob_contents:
                blob_contents[aid] = _load_blob(blobs_dir / f"{aid}.txt")
        for bp in finding.cited_blob_paths:
            key = str(bp)
            if key not in blob_contents:
                blob_contents[key] = _load_blob(bp)

    prompt = _build_critique_prompt(findings, blob_contents)
    deps = CriticDeps(case_dir=case_dir, examiner=examiner, findings_to_review=findings)

    agent = build_critic(model=model)
    run_result = await agent.run(prompt, deps=deps)

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
    "CriticVerdict",
    "CriticVerdictRecord",
    "StagedFinding",
    "build_critic",
    "critique",
]
