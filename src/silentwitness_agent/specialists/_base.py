"""Shared primitives for all four specialist subagents (memory/disk/network/log).

Architecture §5.2 — each specialist returns a SpecialistReport to the
investigator, which owns all pivot decisions.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from silentwitness_common.types import CriticVerdict, SpecialistName

# ---------------------------------------------------------------------------
# Tool-call + finding records
# ---------------------------------------------------------------------------


class ToolCallRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tool_name: str = Field(min_length=1)
    audit_id: str = Field(min_length=1)
    elapsed_ms: float = Field(ge=0.0)
    success: bool


class SpecialistFinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    observation_id: str = Field(min_length=1)
    interpretation_id: str = Field(min_length=1)
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
    summary: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# Specialist deps + report
# ---------------------------------------------------------------------------


class SpecialistDeps(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    case_dir: Path
    examiner: str = Field(min_length=1)
    hypothesis_id: str = Field(min_length=1)
    evidence_paths: list[Path] = Field(default_factory=list)
    pending_critiques: list[CriticVerdict] = Field(default_factory=list)


class SpecialistReport(BaseModel):
    model_config = ConfigDict(frozen=False, extra="forbid")

    findings: list[SpecialistFinding] = Field(default_factory=list)
    tokens_spent: int = Field(ge=0)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    time_elapsed_ms: float = Field(ge=0.0)
    confidence_assessment: Literal["LOW", "MEDIUM", "HIGH"]
    next_specialist_suggested: SpecialistName | None = None
    notes_for_investigator: str = ""


# ---------------------------------------------------------------------------
# Prompt loader
# ---------------------------------------------------------------------------


def _load_specialist_prompt(slug: str) -> str:
    """Read ``prompts/specialist_<slug>.md`` from the installed package."""
    filename = f"specialist_{slug}.md"
    try:
        return (
            importlib.resources.files("silentwitness_agent.prompts")
            .joinpath(filename)
            .read_text(encoding="utf-8")
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"specialist prompt '{filename}' is missing from silentwitness_agent.prompts; "
            f"ensure src/silentwitness_agent/prompts/{filename} exists."
        ) from exc


__all__ = [
    "SpecialistDeps",
    "SpecialistFinding",
    "SpecialistReport",
    "ToolCallRecord",
    "_load_specialist_prompt",
]
