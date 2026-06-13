"""Shared primitives for all four specialist subagents (memory/disk/network/log).

Architecture §5.2 — each specialist returns a SpecialistReport to the
investigator, which owns all pivot decisions.
"""

from __future__ import annotations

import importlib.resources
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_ai.exceptions import UserError
from pydantic_ai.models import Model, infer_model

from silentwitness_common.types import AuditId, Confidence, CriticVerdict, SpecialistName

_GLOBAL_MODEL_ENV = "SILENTWITNESS_MODEL"
_QUALITY_ENV = "SILENTWITNESS_MODEL_QUALITY"

# ---------------------------------------------------------------------------
# Tool-call + finding records
# ---------------------------------------------------------------------------


class ToolCallRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tool_name: str = Field(min_length=1)
    audit_id: AuditId
    elapsed_ms: float = Field(ge=0.0)
    success: bool


class SpecialistFinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    observation_id: str = Field(min_length=1)
    interpretation_id: str = Field(min_length=1)
    confidence: Confidence
    summary: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# Specialist deps + report
# ---------------------------------------------------------------------------


class SpecialistDeps(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    case_dir: Path
    examiner: str = Field(min_length=1)
    hypothesis_id: str = Field(min_length=1)
    evidence_paths: tuple[Path, ...] = Field(default_factory=tuple)
    pending_critiques: tuple[CriticVerdict, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _case_dir_absolute(self) -> SpecialistDeps:
        if not self.case_dir.is_absolute():
            raise ValueError(f"case_dir must be an absolute path, got {self.case_dir!r}")
        return self


class SpecialistReport(BaseModel):
    model_config = ConfigDict(frozen=False, extra="forbid", validate_assignment=True)

    findings: list[SpecialistFinding] = Field(default_factory=list)
    tokens_spent: int = Field(ge=0)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    time_elapsed_ms: float = Field(ge=0.0)
    confidence_assessment: Confidence
    next_specialist_suggested: SpecialistName | None = None
    notes_for_investigator: str = ""


# ---------------------------------------------------------------------------
# Prompt loader
# ---------------------------------------------------------------------------


def _infer_model_checked(value: str, source: str) -> Model:
    """Resolve a model string, relabelling ONLY a genuine bad/unknown string.

    A valid string can still fail because the provider package or API key is
    missing (``ImportError`` / provider auth ``UserError``). Those are NOT
    string-syntax problems, so we let them propagate with their native type and
    message rather than mislabelling them as "invalid model string" (which would
    send an operator to fix the wrong thing). pydantic-ai signals a genuinely bad
    string as ``UserError: Unknown model`` or ``ValueError: Unknown provider`` —
    only those two are relabelled with the env-var context.
    """
    try:
        return infer_model(value)
    except (UserError, ValueError) as exc:
        if "Unknown model" in str(exc) or "Unknown provider" in str(exc):
            raise ValueError(
                f"{source}={value!r} is not a valid Pydantic AI model string "
                f"(e.g. 'anthropic:claude-haiku-4-5' or 'openai:gpt-4o'). Error: {exc}"
            ) from exc
        raise


def resolve_specialist_model(
    model: str | None,
    *,
    label: str,
    env_model_key: str,
    default_model: str,
    high_quality_model: str,
) -> Model:
    """Resolve a specialist's model with a single, model-agnostic precedence.

    Order (first match wins): explicit ``model`` arg → per-specialist
    ``env_model_key`` → global ``SILENTWITNESS_MODEL`` → ``MODEL_QUALITY=high``
    → ``default_model``. The global model deliberately outranks the quality
    knob: ``high_quality_model`` is a hardcoded Anthropic id, so honouring it
    over an explicit non-Anthropic ``SILENTWITNESS_MODEL`` (e.g. ``openai:*``)
    would reintroduce the very Anthropic-pinning this resolution order exists to
    prevent under an OpenAI/Gemini-only key.
    """
    if model is not None:
        return _infer_model_checked(model, f"{label} specialist: explicit model")
    env_model = os.environ.get(env_model_key)
    if env_model:
        return _infer_model_checked(env_model, f"{label} specialist: {env_model_key}")
    global_model = os.environ.get(_GLOBAL_MODEL_ENV)
    if global_model:
        return _infer_model_checked(global_model, f"{label} specialist: {_GLOBAL_MODEL_ENV}")
    if os.environ.get(_QUALITY_ENV, "").lower() == "high":
        return infer_model(high_quality_model)
    return infer_model(default_model)


def _load_specialist_prompt(slug: str) -> str:
    """Read ``prompts/specialist_<slug>.md`` from the installed package."""
    filename = f"specialist_{slug}.md"
    try:
        return (
            importlib.resources.files("silentwitness_agent.prompts")
            .joinpath(filename)
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, OSError, UnicodeDecodeError) as exc:
        raise FileNotFoundError(
            f"specialist prompt '{filename}' is missing or unreadable from "
            f"silentwitness_agent.prompts; ensure "
            f"src/silentwitness_agent/prompts/{filename} exists and is valid UTF-8."
        ) from exc


__all__ = [
    "SpecialistDeps",
    "SpecialistFinding",
    "SpecialistReport",
    "ToolCallRecord",
    "_load_specialist_prompt",
    "resolve_specialist_model",
]
