# Story — Per-hypothesis token + step budget enforcer

**ID:** story-hypothesis-budget
**Epic:** Epic 8 — Hypothesis state machine + investigator agent (Pydantic AI)
**Depends on:** story-hypothesis-types, story-hypothesis-stack
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** build the `BudgetEnforcer` class in `src/silentwitness_agent/hypothesis/budget.py` that tracks per-hypothesis token + tool-call (step) consumption, denies dispatch when either budget is exhausted, and raises `BudgetExceeded` cleanly so the stack can transition the hypothesis to ABANDONED with reason `"BUDGET_EXHAUSTED"`
**So that** an investigator agent that gets stuck on a hypothesis cannot burn the entire model budget on it — the agent halts cleanly, marks the hypothesis ABANDONED, and the architecture §5.3 budget-exhaustion semantics (per-hypothesis token cap 5000; per-hypothesis step cap 10) are enforced mechanically, not by prompt reminder.

---

## File modification map

- `src/silentwitness_agent/hypothesis/budget.py` — NEW — `BudgetEnforcer` class. Constructor takes `default_token_budget: int = 5000`, `default_step_budget: int = 10`, both overridable per-hypothesis via `Hypothesis.tokens_budgeted` / `Hypothesis.steps_budgeted`. Defaults are env-overridable: `SILENTWITNESS_HYPOTHESIS_TOKEN_BUDGET`, `SILENTWITNESS_HYPOTHESIS_STEP_BUDGET` (architecture §5.3). Methods:
  - `record_tokens(hypothesis_id: str, prompt_tokens: int, completion_tokens: int) -> None` — accumulates against the active hypothesis. Tracks per-hypothesis state in an internal dict.
  - `record_step(hypothesis_id: str) -> None` — increments step count by 1 (one tool call).
  - `check_dispatch(hypothesis: Hypothesis) -> None` — called by the stack BEFORE the DISPATCH transition. Raises `BudgetExceeded(hypothesis_id, reason, tokens_consumed, steps_consumed, tokens_budgeted, steps_budgeted)` if either budget would be exceeded. Reason codes: `TOKEN_BUDGET_EXHAUSTED`, `STEP_BUDGET_EXHAUSTED`.
  - `remaining(hypothesis_id: str) -> BudgetRemaining` — returns `BudgetRemaining(tokens_remaining: int, steps_remaining: int)` for the rich live layout (Epic 12).
  - `reset(hypothesis_id: str) -> None` — clears state for a hypothesis (called by stack on confirm/pivot/abandon for housekeeping; not strictly required for correctness because hypothesis IDs are unique, but keeps the dict bounded for long sessions).
  - Target ≤200 LOC.
- `tests/unit/test_hypothesis_budget.py` — NEW — ≥11 behavioural tests:
  - `BudgetEnforcer()` defaults to 5000 tokens + 10 steps;
  - env override `SILENTWITNESS_HYPOTHESIS_TOKEN_BUDGET=12000` is honoured at construction time;
  - `record_tokens` accumulates correctly across multiple calls;
  - `record_step` increments correctly;
  - `check_dispatch` passes when no budget breached;
  - `check_dispatch` raises `BudgetExceeded` with reason=`TOKEN_BUDGET_EXHAUSTED` when tokens_consumed ≥ tokens_budgeted;
  - `check_dispatch` raises `BudgetExceeded` with reason=`STEP_BUDGET_EXHAUSTED` when steps_consumed ≥ steps_budgeted;
  - `check_dispatch` raises TOKEN reason FIRST when both are exhausted (deterministic ordering for the test suite);
  - per-hypothesis `tokens_budgeted` field override beats the enforcer default (e.g., a hypothesis with `tokens_budgeted=200` triggers earlier);
  - `remaining` returns correct deltas;
  - `reset(hypothesis_id)` clears state and subsequent `record_tokens` starts at 0.
- `tests/property/test_hypothesis_budget_properties.py` — NEW — 2 Hypothesis property tests: for any sequence of positive `record_tokens` calls, total consumed equals sum of inputs (no off-by-one); for any per-hypothesis budget value `B` and any input sequence that sums to ≥ `B`, `check_dispatch` raises before the next dispatch.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a fresh BudgetEnforcer with defaults
When  enforcer.record_tokens("H-001", prompt_tokens=1000, completion_tokens=500) is called twice
Then  enforcer.remaining("H-001").tokens_remaining == 5000 - 3000 == 2000

Given a BudgetEnforcer is constructed with SILENTWITNESS_HYPOTHESIS_TOKEN_BUDGET=12000 in the env
When  enforcer.remaining("H-001").tokens_remaining is read on a fresh hypothesis
Then  return value is 12000

Given a Hypothesis with tokens_budgeted=200 (per-hypothesis override) and 250 tokens recorded
When  enforcer.check_dispatch(hypothesis) is called
Then  BudgetExceeded is raised with reason="TOKEN_BUDGET_EXHAUSTED"
And   exception.tokens_consumed == 250
And   exception.tokens_budgeted == 200

Given a Hypothesis with steps_budgeted=3 and 4 steps recorded
When  enforcer.check_dispatch(hypothesis) is called
Then  BudgetExceeded is raised with reason="STEP_BUDGET_EXHAUSTED"

Given both budgets are simultaneously exhausted
When  enforcer.check_dispatch(hypothesis) is called
Then  BudgetExceeded is raised with reason="TOKEN_BUDGET_EXHAUSTED" (token reason wins by convention)

Given enforcer.reset("H-001") has been called
When  enforcer.remaining("H-001") is read
Then  return value is BudgetRemaining(tokens_remaining=5000, steps_remaining=10)

Given the stack wraps `dispatch` and consults the enforcer
When  the stack calls dispatch on an over-budget hypothesis
Then  BudgetExceeded propagates up to the caller
And   the caller (investigator) can catch it and call stack.abandon(hypothesis_id, reason="BUDGET_EXHAUSTED")

Given tests/unit/test_hypothesis_budget.py exists
When  `uv run pytest tests/unit/test_hypothesis_budget.py -v` runs
Then  exit code is 0
And   ≥11 tests pass

Given tests/property/test_hypothesis_budget_properties.py exists
When  `HYPOTHESIS_PROFILE=ci uv run pytest tests/property/test_hypothesis_budget_properties.py -v` runs
Then  exit code is 0
And   2 property tests pass

Given mypy --strict is configured
When  `uv run mypy --strict src/silentwitness_agent/hypothesis/budget.py` runs
Then  exit code is 0
```

---

## Shell verification

```bash
# Unit tests
uv run pytest tests/unit/test_hypothesis_budget.py -v
# Must show ≥11 passing

# Property tests
HYPOTHESIS_PROFILE=ci uv run pytest tests/property/test_hypothesis_budget_properties.py -v --hypothesis-show-statistics
# Must show 2 passing

# Coverage ≥85% on budget.py
uv run coverage run -m pytest tests/unit/test_hypothesis_budget.py tests/property/test_hypothesis_budget_properties.py
uv run coverage report --include="src/silentwitness_agent/hypothesis/budget.py" --fail-under=85

# Env override smoke
SILENTWITNESS_HYPOTHESIS_TOKEN_BUDGET=12000 uv run python -c "
from silentwitness_agent.hypothesis.budget import BudgetEnforcer
b = BudgetEnforcer()
assert b.remaining('H-001').tokens_remaining == 12000, b.remaining('H-001').tokens_remaining
print('env override OK')
"

# Strict typing + lint + file-size guard
uv run mypy --strict src/silentwitness_agent/hypothesis/budget.py
uv run ruff check src/silentwitness_agent/hypothesis/budget.py
uv run ruff format --check src/silentwitness_agent/hypothesis/budget.py
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_agent/hypothesis/budget.py

# §14 no-mocks clean
git diff main...HEAD -- 'src/silentwitness_agent/hypothesis/budget.py' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded)" | grep -v "test\|spec"
# Must output nothing
```

---

## Notes for coding agent

- Reference: architecture.md §5.3 verbatim:
  - "Default per-hypothesis token budget: 5,000 tokens (configurable via `SILENTWITNESS_HYPOTHESIS_TOKEN_BUDGET`)."
  - "Default per-hypothesis step budget: 10 tool calls (configurable via `SILENTWITNESS_HYPOTHESIS_STEP_BUDGET`)."
  - "Budget exhaustion → automatic ABANDONED transition with `reason: 'BUDGET_EXHAUSTED'`. Logged."
- Reference: architecture.md §5.1 Investigator hooks — `on_step` emits per-step token accounting; the investigator's hooks (story-investigator-hooks) call `BudgetEnforcer.record_tokens` and `BudgetEnforcer.record_step` from those hooks. This story owns the enforcer; the hook wiring is story-investigator-hooks's responsibility.
- `BudgetExceeded` is declared in `silentwitness_agent.hypothesis.types` per story-hypothesis-types. Import it here; do NOT redeclare. Add the structured fields via constructor: `BudgetExceeded(hypothesis_id: str, reason: str, tokens_consumed: int, steps_consumed: int, tokens_budgeted: int, steps_budgeted: int)`. The exception carries the structured context so the caller (HypothesisStack / investigator) can log a useful ABANDON reason.
- `BudgetRemaining` is a Pydantic frozen BaseModel local to this file. Fields: `tokens_remaining: int`, `steps_remaining: int`. Used by the rich live layout (Epic 12) to show a "budget meter" per active hypothesis.
- Env override read at construction (NOT at every call), so tests can monkeypatch the env before instantiation:
  ```python
  default_token_budget = int(os.environ.get("SILENTWITNESS_HYPOTHESIS_TOKEN_BUDGET", "5000"))
  default_step_budget = int(os.environ.get("SILENTWITNESS_HYPOTHESIS_STEP_BUDGET", "10"))
  ```
- Per-hypothesis state: `dict[str, _HypothesisBudgetState]` where `_HypothesisBudgetState` is a private mutable dataclass with `tokens_consumed`, `steps_consumed`. Reset zeroes the entry.
- `check_dispatch` precedence: token-first. Document the convention in the docstring so the test is deterministic. Rationale: tokens are the dominant cost driver; if both are exhausted at the same dispatch, the agent's takeaway should be "your model burn is too high" not "you ran too many tools."
- Thread safety: a single `threading.Lock` guards the state dict for the `record_*` increments. The `check_dispatch` read is also under the lock. The investigator agent runs single-hypothesis-at-a-time (architecture §5.3 "Concurrency is not supported in v1") so contention is low, but the hooks fire from Pydantic AI's async event loop — the lock prevents an `on_step` hook from racing with `check_dispatch` from the stack.
- Library docs to consult via Context7 BEFORE coding:
  - `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic-ai"` then `query-docs` topic `"hooks on_step token usage accounting"` — Pydantic AI exposes `RunUsage` per step; the hooks story (story-investigator-hooks) reads `RunUsage.input_tokens` + `RunUsage.output_tokens` and calls `record_tokens` on this enforcer. Verify the field names; the API surface has shifted across 0.x releases.
- Pitfall: `record_tokens` should accept `0` cleanly — some hooks fire with zero deltas (cached prompts on Anthropic). Do not raise on zero.
- Pitfall: the env override is read at construction. If a test changes the env mid-run, it must re-instantiate. Document this explicitly so the test author doesn't waste an hour.
- Vocabulary discipline: never "court-admissible." Docstrings: "Enforces per-hypothesis token and tool-call budgets so a stuck hypothesis cannot consume the entire model budget."
- LOC budget: ~200, comfortable margin.
