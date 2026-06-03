"""Pydantic v2 contracts for the citation gate (architecture §4.5).

The citation gate's wedge promise: an agent cannot record a finding whose
cited bytes do not exist OR do not say what the agent claims they say.
:class:`CitedSpan` is the agent-emitted claim ("this audit entry's
normalised stdout hashes to X, and lines line_start..line_end contain the
substring span_text"). :func:`silentwitness_mcp.verification.citation_gate.verify_citation`
returns :class:`CitationResult` — success with the span echo-ed back, or
a structured rejection naming which of the five failure modes fired and
what context the agent needs to self-correct.

These types live in ``verification/_types.py`` (NOT
``silentwitness_common/types.py``) because they are the citation-gate's
input/output schema. ``silentwitness_common.types.CitedSpan`` is a
related but distinct legacy type used elsewhere; harmonisation is a
follow-up concern, not this story's surface.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CitationRejectReason(StrEnum):
    """The five architectural rejection codes (architecture §4.5).

    The set is closed: every silent path through the verifier ends in one
    of these codes or in ``success=True``. New codes append; existing
    codes are stable wire identifiers.
    """

    AUDIT_ID_NOT_FOUND = "AUDIT_ID_NOT_FOUND"
    STDOUT_PATH_MISSING = "STDOUT_PATH_MISSING"
    OUTPUT_HASH_MISMATCH = "OUTPUT_HASH_MISMATCH"
    LINE_RANGE_OUT_OF_BOUNDS = "LINE_RANGE_OUT_OF_BOUNDS"
    SPAN_NOT_IN_LINES = "SPAN_NOT_IN_LINES"


_BASE_CONFIG = ConfigDict(frozen=True, extra="forbid")


class CitedSpan(BaseModel):
    """An agent-emitted citation pointing into a normalised tool output.

    The line range uses Python-slice semantics (0-based, half-open):
    ``line_start`` is inclusive, ``line_end`` is exclusive, matching
    ``lines[line_start:line_end]``. Agents must emit 0-based indices.
    """

    model_config = _BASE_CONFIG

    audit_id: str = Field(
        min_length=1,
        description="audit_id of the MCP tool call that produced the cited output.",
    )
    sha256_of_normalized_output: str = Field(
        pattern=r"^[a-f0-9]{64}$",
        description="SHA-256 hex of the FULL normalised tool output the agent claims to have read.",
    )
    line_start: int = Field(ge=0, description="0-based inclusive start of the cited slice.")
    line_end: int = Field(ge=0, description="0-based exclusive end (Python slice semantics).")
    span_text: str = Field(
        min_length=1,
        description="Verbatim substring the agent claims appears within "
        "``lines[line_start:line_end]``.",
    )

    @model_validator(mode="after")
    def _check_range(self) -> CitedSpan:
        if self.line_end <= self.line_start:
            raise ValueError(f"line_end ({self.line_end}) must be > line_start ({self.line_start})")
        return self


class CitationResult(BaseModel):
    """Tagged-union result of :func:`verify_citation`.

    ``success=True`` ⇒ ``span`` is the original ``CitedSpan`` echoed back,
    ``reason`` and ``context`` are ``None``. ``success=False`` ⇒ ``reason``
    names the failure mode and ``context`` carries structured self-correction
    data (expected vs actual hash, line range checked, etc.). The
    ``@model_validator`` enforces the invariant so callers can rely on the
    discriminator without re-checking field combinations.
    """

    model_config = _BASE_CONFIG

    success: bool
    span: CitedSpan | None = None
    reason: CitationRejectReason | None = None
    context: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_tag(self) -> CitationResult:
        if self.success:
            if self.span is None:
                raise ValueError("CitationResult.success=True requires span")
            if self.reason is not None:
                raise ValueError("CitationResult.success=True must not carry reason")
        else:
            if self.reason is None:
                raise ValueError("CitationResult.success=False requires reason")
            if self.span is not None:
                raise ValueError("CitationResult.success=False must not carry span")
        return self

    @classmethod
    def accept(cls, span: CitedSpan) -> CitationResult:
        return cls(success=True, span=span)

    @classmethod
    def reject(cls, reason: CitationRejectReason, **context: Any) -> CitationResult:
        return cls(success=False, reason=reason, context=dict(context))


__all__ = ["CitationRejectReason", "CitationResult", "CitedSpan"]
