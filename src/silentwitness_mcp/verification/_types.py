"""Pydantic v2 contracts for the citation gate (architecture §4.5).

The citation gate's wedge promise (constrained by ADR-004 — closure
comes from §4.5 + §4.7 together, NOT from this gate alone): an agent
cannot record a finding whose cited bytes do not exist OR whose cited
slice does not contain the claimed substring. The full no-hallucination
guarantee depends on the entity gate (§4.7) layered on top to close
the same-range wrong-row-match attack.

:class:`CitedSpan` lives in :mod:`silentwitness_common.types` as the
single source-of-truth (harmonised in PR-110 round-2 — code-reviewer
finding #1). This module re-exports it and adds the gate-specific
:class:`CitationRejectReason` and :class:`CitationResult` types.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from silentwitness_common.types import CitedSpan

__all__ = ["CitationRejectReason", "CitationResult", "CitedSpan"]


class CitationRejectReason(StrEnum):
    """Architectural rejection codes (architecture §4.5).

    Every non-exception path through :func:`verify_citation` ends in
    ``success=True`` or in one of these codes. The set is closed for
    well-formed audit entries; programmatic invariants (e.g. an audit
    entry whose ``tool`` was removed from the normalizer's registry)
    map to :attr:`TOOL_NOT_REGISTERED` rather than propagating exceptions.
    """

    AUDIT_ID_NOT_FOUND = "AUDIT_ID_NOT_FOUND"
    STDOUT_PATH_MISSING = "STDOUT_PATH_MISSING"
    STDOUT_PATH_UNREADABLE = "STDOUT_PATH_UNREADABLE"
    TOOL_NOT_REGISTERED = "TOOL_NOT_REGISTERED"
    OUTPUT_HASH_MISMATCH = "OUTPUT_HASH_MISMATCH"
    LINE_RANGE_OUT_OF_BOUNDS = "LINE_RANGE_OUT_OF_BOUNDS"
    SPAN_NOT_IN_LINES = "SPAN_NOT_IN_LINES"


_BASE_CONFIG = ConfigDict(frozen=True, extra="forbid")


class CitationResult(BaseModel):
    """Tagged-union result of :func:`verify_citation`.

    ``success=True`` ⇒ ``span`` is the original ``CitedSpan`` echoed
    back, ``reason`` is ``None``, ``context`` is empty. ``success=False``
    ⇒ ``reason`` names the failure and ``context`` carries structured
    self-correction data the agent needs (expected/actual hash, line
    range checked, errno of the underlying OSError, etc.). The
    ``@model_validator`` enforces the discriminator invariant; the
    ``.accept`` / ``.reject`` classmethods are the only construction
    paths code should use.

    Note: a Pydantic-v2 native discriminated union via
    ``Annotated[Union[CitationAccept, CitationReject], Field(discriminator="kind")]``
    would give mypy automatic narrowing on the success bool. Deferred
    to a follow-up so downstream Epic 4+ stories aren't blocked.
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
