"""Behavioural tests for silentwitness_agent.hypothesis.types."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from silentwitness_agent.hypothesis.types import (
    BudgetExceeded,
    BudgetExhaustedReason,
    Hypothesis,
    HypothesisEvent,
    HypothesisEventType,
    HypothesisStatus,
    SpecialistName,
    make_hypothesis_id,
)
from silentwitness_common.types import WorkflowError

_NOW = datetime(2026, 6, 11, 12, 0, 0, tzinfo=UTC)


def _h(**kwargs: object) -> Hypothesis:
    defaults: dict[str, object] = {
        "id": "H-001",
        "statement": "Expect promiscuous-mode capture tool on the suspect host",
        "formed_at": _NOW,
    }
    defaults.update(kwargs)
    return Hypothesis(**defaults)


def _e(**kwargs: object) -> HypothesisEvent:
    defaults: dict[str, object] = {
        "ts": _NOW,
        "type": HypothesisEventType.FORM,
        "hypothesis_id": "H-001",
    }
    defaults.update(kwargs)
    return HypothesisEvent(**defaults)


# ---------------------------------------------------------------------------
# Construction + defaults
# ---------------------------------------------------------------------------


def test_hypothesis_constructs_with_defaults() -> None:
    h = _h()
    assert h.status == HypothesisStatus.ACTIVE
    assert h.tokens_budgeted is None
    assert h.steps_budgeted is None
    assert h.tokens_consumed == 0
    assert h.steps_consumed == 0
    assert h.formed_from is None
    assert h.assigned_specialist is None
    assert h.evidence_expected == []
    assert h.evidence_observed == []


def test_hypothesis_assigned_specialist_stored() -> None:
    h = _h(assigned_specialist=SpecialistName.MEMORY)
    assert h.assigned_specialist == SpecialistName.MEMORY


def test_hypothesis_event_constructs_with_defaults() -> None:
    e = _e()
    assert e.reason == ""
    assert e.related_audit_ids == ()
    assert e.tokens_spent == 0
    assert e.steps_spent == 0


# ---------------------------------------------------------------------------
# Mutability / immutability
# ---------------------------------------------------------------------------


def test_hypothesis_status_is_mutable() -> None:
    h = _h()
    h.status = HypothesisStatus.CONFIRMED
    assert h.status == HypothesisStatus.CONFIRMED


def test_hypothesis_event_is_frozen() -> None:
    e = _e()
    with pytest.raises(ValidationError):
        e.reason = "mutation attempt"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Extra="forbid"
# ---------------------------------------------------------------------------


def test_hypothesis_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        _h(rogue="value")


def test_hypothesis_event_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        _e(rogue="value")


# ---------------------------------------------------------------------------
# make_hypothesis_id
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "seq, expected",
    [(1, "H-001"), (42, "H-042"), (1042, "H-1042")],
)
def test_make_hypothesis_id(seq: int, expected: str) -> None:
    assert make_hypothesis_id(seq) == expected


# ---------------------------------------------------------------------------
# HypothesisEventType lowercase JSONL values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "member, expected",
    [
        (HypothesisEventType.FORM, "form"),
        (HypothesisEventType.DISPATCH, "dispatch"),
        (HypothesisEventType.CONFIRM, "confirm"),
        (HypothesisEventType.PIVOT, "pivot"),
        (HypothesisEventType.ABANDON, "abandon"),
    ],
)
def test_hypothesis_event_type_values_lowercase(member: HypothesisEventType, expected: str) -> None:
    assert member.value == expected


# ---------------------------------------------------------------------------
# HypothesisStatus values (uppercase, re-exported from common types)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "member, expected",
    [
        (HypothesisStatus.ACTIVE, "ACTIVE"),
        (HypothesisStatus.CONFIRMED, "CONFIRMED"),
        (HypothesisStatus.PIVOTED, "PIVOTED"),
        (HypothesisStatus.ABANDONED, "ABANDONED"),
    ],
)
def test_hypothesis_status_values_uppercase(member: HypothesisStatus, expected: str) -> None:
    assert member.value == expected


# ---------------------------------------------------------------------------
# JSON round-trips
# ---------------------------------------------------------------------------


def test_hypothesis_event_round_trip() -> None:
    e = _e(
        type=HypothesisEventType.PIVOT,
        reason="evidence contradicts initial assumption",
        related_audit_ids=["sift-aj-20260611-042"],
        tokens_spent=1200,
        steps_spent=3,
    )
    raw = e.model_dump_json()
    restored = HypothesisEvent.model_validate_json(raw)
    assert restored == e


def test_hypothesis_round_trip() -> None:
    h = _h(
        status=HypothesisStatus.CONFIRMED,
        evidence_observed=["sift-aj-20260611-007"],
        tokens_consumed=3400,
        steps_consumed=8,
    )
    raw = h.model_dump_json()
    restored = Hypothesis.model_validate_json(raw)
    assert restored == h


# ---------------------------------------------------------------------------
# BudgetExceeded inheritance
# ---------------------------------------------------------------------------


def test_budget_exceeded_subclasses_workflow_error() -> None:
    assert issubclass(BudgetExceeded, WorkflowError)


def test_budget_exceeded_is_exception() -> None:
    exc = BudgetExceeded("H-001", BudgetExhaustedReason.TOKEN_BUDGET_EXHAUSTED, 5000, 3, 5000, 10)
    with pytest.raises(BudgetExceeded):
        raise exc


# ---------------------------------------------------------------------------
# SpecialistName re-export
# ---------------------------------------------------------------------------


def test_specialist_name_values() -> None:
    assert SpecialistName.MEMORY.value == "MEMORY"
    assert SpecialistName.DISK.value == "DISK"
    assert SpecialistName.NETWORK.value == "NETWORK"
    assert SpecialistName.LOG.value == "LOG"


# ---------------------------------------------------------------------------
# Constraint rejection tests (min_length, ge=0, validate_assignment)
# ---------------------------------------------------------------------------


def test_hypothesis_rejects_empty_id() -> None:
    with pytest.raises(ValidationError):
        _h(id="")


def test_hypothesis_rejects_empty_statement() -> None:
    with pytest.raises(ValidationError):
        _h(statement="")


def test_hypothesis_event_rejects_empty_hypothesis_id() -> None:
    with pytest.raises(ValidationError):
        _e(hypothesis_id="")


def test_hypothesis_rejects_negative_tokens_budgeted() -> None:
    with pytest.raises(ValidationError):
        _h(tokens_budgeted=-1)


def test_hypothesis_rejects_negative_tokens_on_assignment() -> None:
    h = _h()
    with pytest.raises(ValidationError):
        h.tokens_consumed = -1


def test_hypothesis_validate_assignment_rejects_invalid_status() -> None:
    h = _h()
    with pytest.raises(ValidationError):
        h.status = "NOT_A_STATUS"  # type: ignore[assignment]


def test_hypothesis_formed_from_rejects_empty_string() -> None:
    with pytest.raises(ValidationError):
        _h(formed_from="")


# ---------------------------------------------------------------------------
# Liskov: BudgetExceeded caught as WorkflowError
# ---------------------------------------------------------------------------


def test_budget_exceeded_caught_as_workflow_error() -> None:
    with pytest.raises(WorkflowError):
        raise BudgetExceeded(
            "H-001", BudgetExhaustedReason.TOKEN_BUDGET_EXHAUSTED, 5000, 3, 5000, 10
        )
