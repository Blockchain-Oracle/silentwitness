"""Per-hypothesis token + step budget enforcer.

Enforces per-hypothesis token and tool-call budgets so a stuck hypothesis
cannot consume the entire model budget.  Inject into ``HypothesisStack``
via the ``BudgetEnforcer`` protocol defined in ``stack.py``; the stack
calls ``check_dispatch`` before every DISPATCH transition.

Lock ordering invariant: stack._lock is ALWAYS acquired BEFORE budget._lock.
``record_tokens`` and ``record_step`` MUST NOT acquire any stack-level lock.
This is relevant to story-investigator-hooks, which calls these methods from
Pydantic AI hooks that run while the stack processes transitions.
"""

from __future__ import annotations

import dataclasses
import os
import threading

from pydantic import BaseModel, ConfigDict, Field

from silentwitness_agent.hypothesis.types import (
    BudgetExceeded,
    BudgetExhaustedReason,
    Hypothesis,
)


class BudgetRemaining(BaseModel):
    """Point-in-time budget headroom for the rich live layout (Epic 12).

    Values are clamped to zero — never negative — even when consumption
    has exceeded the budget.  ``check_dispatch`` is the authoritative gate;
    ``BudgetRemaining`` is display-only.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    tokens_remaining: int = Field(ge=0)
    steps_remaining: int = Field(ge=0)


@dataclasses.dataclass
class _State:
    tokens_consumed: int = 0
    steps_consumed: int = 0


def _parse_budget_env(var: str, default: int) -> int:
    """Parse a positive-integer env var; raise ValueError with a diagnostic on bad input."""
    raw = os.environ.get(var)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(
            f"BudgetEnforcer: {var}={raw!r} is not a valid integer. "
            f"Set it to a positive integer (e.g. {default}) or unset it."
        ) from None
    if value <= 0:
        raise ValueError(f"BudgetEnforcer: {var}={value} must be a positive integer.")
    return value


class BudgetEnforcer:
    """Tracks per-hypothesis token and step consumption; denies dispatch on exhaustion.

    Token-first precedence: when both budgets are simultaneously exhausted,
    ``TOKEN_BUDGET_EXHAUSTED`` is raised. Tokens are the dominant cost driver.

    Env override is read at construction time, not per-call. If a test mutates
    the environment, it must re-instantiate the enforcer.

    Per-hypothesis override: if ``Hypothesis.tokens_budgeted`` (or
    ``steps_budgeted``) is not ``None``, it overrides the enforcer default for
    that hypothesis.  ``None`` means "inherit the enforcer default".
    """

    def __init__(
        self,
        default_token_budget: int = 0,
        default_step_budget: int = 0,
    ) -> None:
        # Constructor args override env (explicit > env > hardcoded fallback).
        env_tokens = _parse_budget_env("SILENTWITNESS_HYPOTHESIS_TOKEN_BUDGET", 5000)
        env_steps = _parse_budget_env("SILENTWITNESS_HYPOTHESIS_STEP_BUDGET", 10)
        self._default_token_budget = default_token_budget or env_tokens
        self._default_step_budget = default_step_budget or env_steps
        self._states: dict[str, _State] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Recording — called from Pydantic AI hooks (story-investigator-hooks)
    # ------------------------------------------------------------------

    def record_tokens(self, hypothesis_id: str, prompt_tokens: int, completion_tokens: int) -> None:
        """Accumulate token usage for a hypothesis. Accepts zero deltas (cached prompts)."""
        if prompt_tokens < 0 or completion_tokens < 0:
            raise ValueError(
                f"record_tokens: negative token counts are invalid "
                f"(hypothesis={hypothesis_id}, prompt={prompt_tokens}, "
                f"completion={completion_tokens})"
            )
        with self._lock:
            self._get_or_create(hypothesis_id).tokens_consumed += prompt_tokens + completion_tokens

    def record_step(self, hypothesis_id: str) -> None:
        """Increment step count by 1 (one tool call)."""
        with self._lock:
            self._get_or_create(hypothesis_id).steps_consumed += 1

    # ------------------------------------------------------------------
    # Dispatch gate — called by HypothesisStack.dispatch (under stack lock)
    # ------------------------------------------------------------------

    def check_dispatch(self, hypothesis: Hypothesis) -> None:
        """Raise BudgetExceeded if dispatch would exceed the hypothesis budget.

        Token-first: TOKEN_BUDGET_EXHAUSTED is raised when both limits are hit.
        Respects per-hypothesis ``tokens_budgeted`` / ``steps_budgeted`` fields;
        ``None`` on either field falls back to the enforcer default.

        Counters are snapshotted and checked under a single lock acquisition to
        avoid TOCTOU skew in the exception payload fields.
        """
        token_budget = (
            hypothesis.tokens_budgeted
            if hypothesis.tokens_budgeted is not None
            else self._default_token_budget
        )
        step_budget = (
            hypothesis.steps_budgeted
            if hypothesis.steps_budgeted is not None
            else self._default_step_budget
        )

        with self._lock:
            state = self._get_or_create(hypothesis.id)
            tokens_consumed = state.tokens_consumed
            steps_consumed = state.steps_consumed
            if tokens_consumed >= token_budget:
                raise BudgetExceeded(
                    hypothesis.id,
                    BudgetExhaustedReason.TOKEN_BUDGET_EXHAUSTED,
                    tokens_consumed,
                    steps_consumed,
                    token_budget,
                    step_budget,
                )
            if steps_consumed >= step_budget:
                raise BudgetExceeded(
                    hypothesis.id,
                    BudgetExhaustedReason.STEP_BUDGET_EXHAUSTED,
                    tokens_consumed,
                    steps_consumed,
                    token_budget,
                    step_budget,
                )

    # ------------------------------------------------------------------
    # Introspection + housekeeping
    # ------------------------------------------------------------------

    def remaining(self, hypothesis: Hypothesis) -> BudgetRemaining:
        """Return remaining token and step headroom for the live layout.

        Uses the same budget resolution as ``check_dispatch`` (per-hypothesis
        override if set, otherwise enforcer default).  Values are clamped to
        zero — ``check_dispatch`` is the authoritative gate.
        """
        token_budget = (
            hypothesis.tokens_budgeted
            if hypothesis.tokens_budgeted is not None
            else self._default_token_budget
        )
        step_budget = (
            hypothesis.steps_budgeted
            if hypothesis.steps_budgeted is not None
            else self._default_step_budget
        )
        with self._lock:
            state = self._get_or_create(hypothesis.id)
            tokens_consumed = state.tokens_consumed
            steps_consumed = state.steps_consumed
        return BudgetRemaining(
            tokens_remaining=max(0, token_budget - tokens_consumed),
            steps_remaining=max(0, step_budget - steps_consumed),
        )

    def reset(self, hypothesis_id: str) -> None:
        """Clear state for a hypothesis; subsequent record_* calls start at 0."""
        with self._lock:
            self._states.pop(hypothesis_id, None)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_or_create(self, hypothesis_id: str) -> _State:
        """Return existing state or create a fresh entry. Caller must hold lock."""
        if hypothesis_id not in self._states:
            self._states[hypothesis_id] = _State()
        return self._states[hypothesis_id]


__all__ = ["BudgetEnforcer", "BudgetRemaining"]
