"""Per-hypothesis token + step budget enforcer.

Enforces per-hypothesis token and tool-call budgets so a stuck hypothesis
cannot consume the entire model budget.  Inject into ``HypothesisStack``
via ``BudgetEnforcer`` protocol; the stack calls ``check_dispatch`` before
every DISPATCH transition.
"""

from __future__ import annotations

import dataclasses
import os
import threading

from pydantic import BaseModel, ConfigDict

from silentwitness_agent.hypothesis.types import BudgetExceeded, Hypothesis


class BudgetRemaining(BaseModel):
    """Point-in-time budget headroom for the rich live layout (Epic 12)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tokens_remaining: int
    steps_remaining: int


@dataclasses.dataclass
class _State:
    tokens_consumed: int = 0
    steps_consumed: int = 0


class BudgetEnforcer:
    """Tracks per-hypothesis token and step consumption; denies dispatch on exhaustion.

    Token-first precedence: when both budgets are simultaneously exhausted,
    ``TOKEN_BUDGET_EXHAUSTED`` is raised. Tokens are the dominant cost driver.

    Env override is read at construction time, not per-call. If a test mutates
    the environment, it must re-instantiate the enforcer.
    """

    def __init__(
        self,
        default_token_budget: int = 0,
        default_step_budget: int = 0,
    ) -> None:
        # Env overrides take precedence; constructor args are fallbacks for explicit override.
        env_tokens = int(os.environ.get("SILENTWITNESS_HYPOTHESIS_TOKEN_BUDGET", "5000"))
        env_steps = int(os.environ.get("SILENTWITNESS_HYPOTHESIS_STEP_BUDGET", "10"))
        self._default_token_budget = default_token_budget or env_tokens
        self._default_step_budget = default_step_budget or env_steps
        self._states: dict[str, _State] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Recording — called from Pydantic AI hooks (story-investigator-hooks)
    # ------------------------------------------------------------------

    def record_tokens(self, hypothesis_id: str, prompt_tokens: int, completion_tokens: int) -> None:
        """Accumulate token usage for a hypothesis. Accepts zero deltas (cached prompts)."""
        with self._lock:
            self._get_or_create(hypothesis_id).tokens_consumed += prompt_tokens + completion_tokens

    def record_step(self, hypothesis_id: str) -> None:
        """Increment step count by 1 (one tool call)."""
        with self._lock:
            self._get_or_create(hypothesis_id).steps_consumed += 1

    # ------------------------------------------------------------------
    # Dispatch gate — called by HypothesisStack.dispatch (under stack lock)
    # ------------------------------------------------------------------

    def check_dispatch(self, hypothesis: Hypothesis) -> bool:
        """Return True if dispatch is permitted; raise BudgetExceeded otherwise.

        Token-first: TOKEN_BUDGET_EXHAUSTED is raised when both limits are hit.
        Uses per-hypothesis ``tokens_budgeted`` / ``steps_budgeted`` fields if
        they differ from defaults (per-hypothesis override beats enforcer default).
        """
        token_budget = hypothesis.tokens_budgeted or self._default_token_budget
        step_budget = hypothesis.steps_budgeted or self._default_step_budget

        with self._lock:
            state = self._get_or_create(hypothesis.id)
            tokens_consumed = state.tokens_consumed
            steps_consumed = state.steps_consumed

        if tokens_consumed >= token_budget:
            raise BudgetExceeded(
                hypothesis.id,
                "TOKEN_BUDGET_EXHAUSTED",
                tokens_consumed,
                steps_consumed,
                token_budget,
                step_budget,
            )
        if steps_consumed >= step_budget:
            raise BudgetExceeded(
                hypothesis.id,
                "STEP_BUDGET_EXHAUSTED",
                tokens_consumed,
                steps_consumed,
                token_budget,
                step_budget,
            )
        return True

    # ------------------------------------------------------------------
    # Introspection + housekeeping
    # ------------------------------------------------------------------

    def remaining(self, hypothesis_id: str) -> BudgetRemaining:
        """Return remaining token and step headroom for the live layout."""
        with self._lock:
            state = self._get_or_create(hypothesis_id)
            tokens_consumed = state.tokens_consumed
            steps_consumed = state.steps_consumed
        return BudgetRemaining(
            tokens_remaining=self._default_token_budget - tokens_consumed,
            steps_remaining=self._default_step_budget - steps_consumed,
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
