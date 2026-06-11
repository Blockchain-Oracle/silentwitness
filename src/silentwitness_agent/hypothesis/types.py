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


class BudgetExhaustedReason(StrEnum):
    """Exhaustion reason codes carried by ``BudgetExceeded``.

    Using a StrEnum makes ``if exc.reason == BudgetExhaustedReason.TOKEN_BUDGET_EXHAUSTED``
    exhaustively checkable by mypy — a misspelled string literal would be a type error.
    """

    TOKEN_BUDGET_EXHAUSTED = "TOKEN_BUDGET_EXHAUSTED"  # noqa: S105
    STEP_BUDGET_EXHAUSTED = "STEP_BUDGET_EXHAUSTED"


class BudgetExceeded(WorkflowError):  # noqa: N818 — name mandated by BDD spec
    """Raised when a hypothesis exhausts its token or step budget.

    Carries structured context so callers can log a useful ABANDON reason
    without re-querying enforcer state.

    Attributes: ``reason`` (``BudgetExhaustedReason``), ``tokens_consumed``,
    ``steps_consumed``, ``tokens_budgeted``, ``steps_budgeted``.
    """

    def __init__(
        self,
        hypothesis_id: str,
        reason: BudgetExhaustedReason,
        tokens_consumed: int,
        steps_consumed: int,
        tokens_budgeted: int,
        steps_budgeted: int,
    ) -> None:
        super().__init__(
            f"{reason}: hypothesis={hypothesis_id} "
            f"tokens={tokens_consumed}/{tokens_budgeted} "
            f"steps={steps_consumed}/{steps_budgeted}"
        )
        self.hypothesis_id = hypothesis_id
        self.reason = reason
        self.tokens_consumed = tokens_consumed
        self.steps_consumed = steps_consumed
        self.tokens_budgeted = tokens_budgeted
        self.steps_budgeted = steps_budgeted


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
        min_length=1,
        description="Parent hypothesis ID if this is a pivot child.",
    )
    evidence_expected: list[str] = Field(
        default_factory=list,
        description="Predicted confirmations for this hypothesis.",
    )
    evidence_observed: list[str] = Field(
        default_factory=list,
        description="Audit IDs of confirming evidence.",
    )
    assigned_specialist: SpecialistName | None = Field(default=None)
    tokens_budgeted: int | None = Field(default=None, ge=1)
    tokens_consumed: int = Field(default=0, ge=0)
    steps_budgeted: int | None = Field(default=None, ge=1)
    steps_consumed: int = Field(default=0, ge=0)


class HypothesisEvent(BaseModel):
    """Immutable audit record emitted to ``audit/hypothesis.jsonl`` per transition.

    Schema matches architecture §5.3 verbatim — ``model_dump_json()`` output
    is the JSONL line; ``model_validate_json`` reads it back losslessly.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    ts: datetime
    type: HypothesisEventType
    hypothesis_id: str = Field(min_length=1)
    reason: str = Field(default="")
    related_audit_ids: tuple[str, ...] = Field(default_factory=tuple)
    tokens_spent: int = Field(default=0, ge=0)
    steps_spent: int = Field(default=0, ge=0)


def make_hypothesis_id(seq: int) -> str:
    """Return ``H-NNN`` zero-padded to 3 digits; natural width beyond 999."""
    return f"H-{seq:03d}"


__all__ = [
    "BudgetExceeded",
    "BudgetExhaustedReason",
    "Hypothesis",
    "HypothesisEvent",
    "HypothesisEventType",
    "HypothesisStatus",
    "SpecialistName",
    "make_hypothesis_id",
]
