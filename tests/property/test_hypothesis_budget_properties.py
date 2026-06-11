"""Property tests for BudgetEnforcer — accumulation and exhaustion invariants."""

from __future__ import annotations

from datetime import UTC, datetime

from hypothesis import given, settings, strategies as st

from silentwitness_agent.hypothesis.budget import BudgetEnforcer
from silentwitness_agent.hypothesis.types import (
    BudgetExceeded,
    Hypothesis,
    HypothesisStatus,
)

_TS = datetime(2026, 6, 11, tzinfo=UTC)


def _h(tokens_budgeted: int = 5000, steps_budgeted: int = 10) -> Hypothesis:
    return Hypothesis(
        id="H-001",
        statement="property test hypothesis",
        status=HypothesisStatus.ACTIVE,
        formed_at=_TS,
        tokens_budgeted=tokens_budgeted,
        steps_budgeted=steps_budgeted,
    )


@settings(max_examples=50, deadline=None)
@given(
    calls=st.lists(
        st.tuples(st.integers(min_value=0, max_value=500), st.integers(min_value=0, max_value=500)),
        min_size=1,
        max_size=20,
    )
)
def test_total_consumed_equals_sum_of_inputs(
    calls: list[tuple[int, int]],
) -> None:
    """For any sequence of record_tokens calls, consumed = sum(prompt + completion)."""
    e = BudgetEnforcer()
    expected = sum(p + c for p, c in calls)
    for prompt, completion in calls:
        e.record_tokens("H-001", prompt_tokens=prompt, completion_tokens=completion)
    remaining = e.remaining("H-001")
    assert remaining.tokens_remaining == 5000 - expected


@settings(max_examples=50, deadline=None)
@given(
    budget=st.integers(min_value=1, max_value=100),
    inputs=st.lists(
        st.integers(min_value=1, max_value=50),
        min_size=1,
        max_size=50,
    ),
)
def test_check_dispatch_raises_once_budget_met(budget: int, inputs: list[int]) -> None:
    """Once cumulative tokens >= budget, check_dispatch raises BudgetExceeded."""
    e = BudgetEnforcer()
    h = _h(tokens_budgeted=budget)
    total = 0
    raised = False
    for tokens in inputs:
        e.record_tokens("H-001", prompt_tokens=tokens, completion_tokens=0)
        total += tokens
        if total >= budget:
            try:
                e.check_dispatch(h)
            except BudgetExceeded:
                raised = True
                break
    if total >= budget:
        assert raised, f"Expected BudgetExceeded after {total} tokens (budget={budget})"
