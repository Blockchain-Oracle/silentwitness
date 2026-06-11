"""Behavioural tests for BudgetEnforcer — ≥11 tests per story spec."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from silentwitness_agent.hypothesis.budget import BudgetEnforcer, BudgetRemaining
from silentwitness_agent.hypothesis.types import (
    BudgetExceeded,
    Hypothesis,
    HypothesisStatus,
)

_TS = datetime(2026, 6, 11, tzinfo=UTC)


def _h(
    hid: str = "H-001",
    tokens_budgeted: int = 5000,
    steps_budgeted: int = 10,
) -> Hypothesis:
    return Hypothesis(
        id=hid,
        statement="test hypothesis",
        status=HypothesisStatus.ACTIVE,
        formed_at=_TS,
        tokens_budgeted=tokens_budgeted,
        steps_budgeted=steps_budgeted,
    )


# ---------------------------------------------------------------------------
# Construction — defaults and env override
# ---------------------------------------------------------------------------


def test_default_token_budget_is_5000() -> None:
    e = BudgetEnforcer()
    assert e.remaining("H-001").tokens_remaining == 5000


def test_default_step_budget_is_10() -> None:
    e = BudgetEnforcer()
    assert e.remaining("H-001").steps_remaining == 10


def test_env_override_token_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_HYPOTHESIS_TOKEN_BUDGET", "12000")
    e = BudgetEnforcer()
    assert e.remaining("H-001").tokens_remaining == 12000


def test_env_override_step_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_HYPOTHESIS_STEP_BUDGET", "20")
    e = BudgetEnforcer()
    assert e.remaining("H-001").steps_remaining == 20


# ---------------------------------------------------------------------------
# record_tokens and record_step accumulation
# ---------------------------------------------------------------------------


def test_record_tokens_accumulates_across_calls() -> None:
    e = BudgetEnforcer()
    e.record_tokens("H-001", prompt_tokens=1000, completion_tokens=500)
    e.record_tokens("H-001", prompt_tokens=1000, completion_tokens=500)
    assert e.remaining("H-001").tokens_remaining == 5000 - 3000


def test_record_tokens_accepts_zero_delta() -> None:
    e = BudgetEnforcer()
    e.record_tokens("H-001", prompt_tokens=0, completion_tokens=0)
    assert e.remaining("H-001").tokens_remaining == 5000


def test_record_step_increments() -> None:
    e = BudgetEnforcer()
    e.record_step("H-001")
    e.record_step("H-001")
    assert e.remaining("H-001").steps_remaining == 10 - 2


# ---------------------------------------------------------------------------
# check_dispatch — pass path
# ---------------------------------------------------------------------------


def test_check_dispatch_passes_when_budget_intact() -> None:
    e = BudgetEnforcer()
    assert e.check_dispatch(_h()) is True


# ---------------------------------------------------------------------------
# check_dispatch — token exhaustion
# ---------------------------------------------------------------------------


def test_check_dispatch_raises_token_exhausted() -> None:
    e = BudgetEnforcer()
    h = _h(tokens_budgeted=200)
    e.record_tokens("H-001", prompt_tokens=200, completion_tokens=50)
    with pytest.raises(BudgetExceeded) as exc_info:
        e.check_dispatch(h)
    assert exc_info.value.reason == "TOKEN_BUDGET_EXHAUSTED"
    assert exc_info.value.tokens_consumed == 250
    assert exc_info.value.tokens_budgeted == 200


# ---------------------------------------------------------------------------
# check_dispatch — step exhaustion
# ---------------------------------------------------------------------------


def test_check_dispatch_raises_step_exhausted() -> None:
    e = BudgetEnforcer()
    h = _h(steps_budgeted=3)
    for _ in range(4):
        e.record_step("H-001")
    with pytest.raises(BudgetExceeded) as exc_info:
        e.check_dispatch(h)
    assert exc_info.value.reason == "STEP_BUDGET_EXHAUSTED"


# ---------------------------------------------------------------------------
# check_dispatch — token-first when both exhausted
# ---------------------------------------------------------------------------


def test_check_dispatch_token_reason_wins_when_both_exhausted() -> None:
    e = BudgetEnforcer()
    h = _h(tokens_budgeted=100, steps_budgeted=2)
    e.record_tokens("H-001", prompt_tokens=100, completion_tokens=0)
    for _ in range(2):
        e.record_step("H-001")
    with pytest.raises(BudgetExceeded) as exc_info:
        e.check_dispatch(h)
    assert exc_info.value.reason == "TOKEN_BUDGET_EXHAUSTED"


# ---------------------------------------------------------------------------
# Per-hypothesis budget override beats enforcer default
# ---------------------------------------------------------------------------


def test_per_hypothesis_token_budget_override_triggers_earlier() -> None:
    e = BudgetEnforcer()  # default 5000
    h = _h(tokens_budgeted=200)
    e.record_tokens("H-001", prompt_tokens=200, completion_tokens=1)
    with pytest.raises(BudgetExceeded) as exc_info:
        e.check_dispatch(h)
    assert exc_info.value.tokens_budgeted == 200


# ---------------------------------------------------------------------------
# remaining
# ---------------------------------------------------------------------------


def test_remaining_returns_budget_remaining_type() -> None:
    e = BudgetEnforcer()
    r = e.remaining("H-001")
    assert isinstance(r, BudgetRemaining)
    assert r.tokens_remaining == 5000
    assert r.steps_remaining == 10


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------


def test_reset_clears_consumption_state() -> None:
    e = BudgetEnforcer()
    e.record_tokens("H-001", prompt_tokens=2000, completion_tokens=0)
    e.record_step("H-001")
    e.reset("H-001")
    r = e.remaining("H-001")
    assert r.tokens_remaining == 5000
    assert r.steps_remaining == 10


def test_reset_idempotent_on_unknown_id() -> None:
    e = BudgetEnforcer()
    e.reset("H-999")  # must not raise
    assert e.remaining("H-999").tokens_remaining == 5000


# ---------------------------------------------------------------------------
# Exception fields
# ---------------------------------------------------------------------------


def test_budget_exceeded_carries_structured_fields() -> None:
    exc = BudgetExceeded(
        hypothesis_id="H-001",
        reason="TOKEN_BUDGET_EXHAUSTED",
        tokens_consumed=5100,
        steps_consumed=3,
        tokens_budgeted=5000,
        steps_budgeted=10,
    )
    assert exc.hypothesis_id == "H-001"
    assert exc.tokens_consumed == 5100
    assert exc.steps_consumed == 3
    assert exc.tokens_budgeted == 5000
    assert exc.steps_budgeted == 10
    assert "TOKEN_BUDGET_EXHAUSTED" in str(exc)


# ---------------------------------------------------------------------------
# Isolation between hypotheses
# ---------------------------------------------------------------------------


def test_record_tokens_isolated_per_hypothesis() -> None:
    e = BudgetEnforcer()
    e.record_tokens("H-001", prompt_tokens=1000, completion_tokens=0)
    assert e.remaining("H-002").tokens_remaining == 5000
