"""Hypothesis dataclasses + event types — architecture §5.3.

Types for the hypothesis state machine: one concrete claim at a time,
dispatch a specialist, confirm or pivot based on evidence.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from silentwitness_common.types import (
    HypothesisStatus,
    SpecialistName,
    WorkflowError,
)


class HypothesisEventType(StrEnum):
    """Hypothesis lifecycle transitions emitted to ``audit/hypothesis.jsonl``.

    Lowercase values match the architecture §5.3 JSONL schema verbatim.
    """

    FORM = "form"
    DISPATCH = "dispatch"
    CONFIRM = "confirm"
    PIVOT = "pivot"
    ABANDON = "abandon"


class BudgetExceeded(WorkflowError):  # noqa: N818 — name mandated by BDD spec
    """Raised when a hypothesis exhausts its token or step budget."""


class Hypothesis(BaseModel):
    """A single testable claim: form it, dispatch a specialist, confirm or pivot.

    Mutable — ``status`` and budget counters change over the hypothesis lifecycle.
    ``validate_assignment=True`` keeps runtime mutations type-safe.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: str = Field(min_length=1, description="H-NNN identifier.")
    statement: str = Field(
        min_length=1,
        description="One-sentence concrete claim being tested.",
    )
    status: HypothesisStatus = Field(default=HypothesisStatus.ACTIVE)
    formed_at: datetime
    formed_from: str | None = Field(
        default=None,
        description="Parent hypothesis ID if this is a pivot child.",
    )
    evidence_expected: list[str] = Field(
        default_factory=list,
        description="Predicted confirmations; populated at FORM time.",
    )
    evidence_observed: list[str] = Field(
        default_factory=list,
        description="audit_ids of confirming evidence; populated at CONFIRM time.",
    )
    assigned_specialist: SpecialistName | None = Field(default=None)
    tokens_budgeted: int = Field(default=5000, ge=0)
    tokens_consumed: int = Field(default=0, ge=0)
    steps_budgeted: int = Field(default=10, ge=0)
    steps_consumed: int = Field(default=0, ge=0)


class HypothesisEvent(BaseModel):
    """Immutable audit record emitted to ``audit/hypothesis.jsonl`` per transition.

    Schema matches architecture §5.3 verbatim — ``model_dump_json()`` output
    is the JSONL line; ``model_validate_json`` reads it back losslessly.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    ts: datetime
    type: HypothesisEventType
    hypothesis_id: str = Field(min_length=1)
    reason: str = Field(default="")
    related_audit_ids: list[str] = Field(default_factory=list)
    tokens_spent: int = Field(default=0, ge=0)
    steps_spent: int = Field(default=0, ge=0)


def make_hypothesis_id(seq: int) -> str:
    """Return ``H-NNN`` zero-padded to 3 digits; natural width beyond 999."""
    return f"H-{seq:03d}"


__all__ = [
    "BudgetExceeded",
    "Hypothesis",
    "HypothesisEvent",
    "HypothesisEventType",
    "HypothesisStatus",
    "SpecialistName",
    "make_hypothesis_id",
]
