# Story — Critic trigger logic (interval-based; idempotent)

**ID:** story-critic-trigger
**Epic:** Epic 10 — Closed-loop critic agent
**Depends on:** story-critic-agent, story-investigator-agent
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** build the critic trigger in `src/silentwitness_agent/critic_trigger.py` — a class that watches `cases/<case_id>/findings.json` and fires the critic whenever (N findings have been staged since the last critic run) OR (M minutes have elapsed since the last critic run), defaulting N=5 and M=10, all configurable via env, and idempotent across server restarts
**So that** the critic runs on a steady cadence during a case without firing on every single observation (expensive) and without missing a stretch where the investigator goes quiet (under-supervised), with the trigger state persisted to `cases/<case_id>/critic_state.json` so a server restart picks up the cadence cleanly (architecture.md §5.5 — Triggers: "Every N findings staged. Default N=5; configurable via SILENTWITNESS_CRITIC_INTERVAL_FINDINGS. Every M minutes since last critic run. Default M=10; configurable via SILENTWITNESS_CRITIC_INTERVAL_MINUTES.").

---

## File modification map

- `src/silentwitness_agent/critic_trigger.py` — NEW — `CriticTrigger` class. Constructor takes `case_dir: Path`, `examiner: str`, `interval_findings: int | None = None`, `interval_minutes: float | None = None`, `clock: Callable[[], datetime] = lambda: datetime.now(UTC)`. Reads env defaults (`SILENTWITNESS_CRITIC_INTERVAL_FINDINGS=5`, `SILENTWITNESS_CRITIC_INTERVAL_MINUTES=10`). Methods:
  - `should_fire(current_finding_count: int) -> bool` — returns True if (current_finding_count - last_critic_finding_count >= interval_findings) OR (now - last_critic_at >= interval_minutes). Idempotent — calling twice without state advance returns the same answer.
  - `mark_fired(current_finding_count: int) -> None` — records the firing in `cases/<case_id>/critic_state.json` (atomic write via story-atomic-io). Updates `last_critic_at` and `last_critic_finding_count`.
  - `staged_findings_for_review(findings_json_path: Path) -> list[StagedFinding]` — reads `findings.json`, filters to findings staged AFTER `last_critic_finding_count`, loads each finding's cited audit_blobs from disk, returns `list[StagedFinding]` ready to pass to `critique()` (story-critic-agent).
  - `_load_state() -> _TriggerState` — reads `critic_state.json` on construction. Returns `_TriggerState(last_critic_at: datetime, last_critic_finding_count: int)`. Defaults to (epoch_start, 0) if file missing.
  - Target ≤220 LOC.
- `src/silentwitness_agent/_critic_state.py` — NEW — small Pydantic BaseModel `_TriggerState(last_critic_at: datetime, last_critic_finding_count: int)` with `model_config = ConfigDict(extra="forbid", frozen=True)`. ~30 LOC. (Separate file so the trigger module can stay focused.)
- `tests/unit/test_critic_trigger.py` — NEW — ≥10 behavioural tests:
  - Fresh trigger (no state file) with 0 findings → `should_fire(0)` returns False;
  - Fresh trigger with 5 findings → `should_fire(5)` returns True (interval threshold hit);
  - `should_fire` is idempotent (calling twice without `mark_fired` returns True twice);
  - After `mark_fired(5)`, `should_fire(5)` returns False;
  - After `mark_fired(5)` and 5 more findings (count=10), `should_fire(10)` returns True;
  - With M=10 minutes and only 1 minute elapsed, `should_fire(1)` returns False;
  - With M=10 minutes and 11 minutes elapsed (mock clock), `should_fire(1)` returns True (time-based trigger);
  - Env override `SILENTWITNESS_CRITIC_INTERVAL_FINDINGS=3` is honoured at construction;
  - Env override `SILENTWITNESS_CRITIC_INTERVAL_MINUTES=2` is honoured;
  - `staged_findings_for_review` returns only findings staged after `last_critic_finding_count`;
  - State persists across construction (pre-write `critic_state.json` with `last_critic_finding_count=3`, instantiate fresh trigger, assert `should_fire(5)` returns False because 5-3=2 < interval=5).
- `tests/integration/test_trigger_idempotent.py` — NEW — 1 e2e scenario: trigger.should_fire is called from multiple threads concurrently, only one firing window is recorded.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a fresh CriticTrigger(case_dir, examiner) on an empty case
When  trigger.should_fire(current_finding_count=0) is called
Then  return value is False

Given a fresh CriticTrigger with default interval_findings=5
When  trigger.should_fire(current_finding_count=5) is called
Then  return value is True

Given a CriticTrigger that has just returned True from should_fire(5)
When  trigger.should_fire(5) is called again WITHOUT mark_fired
Then  return value is still True (idempotent — no side effects in should_fire)

Given a CriticTrigger after trigger.mark_fired(5) has been called
When  trigger.should_fire(5) is called
Then  return value is False (no new findings since last firing)

Given a CriticTrigger after mark_fired(5), and 5 more findings have been staged
When  trigger.should_fire(10) is called
Then  return value is True (delta = 10 - 5 == interval threshold)

Given a CriticTrigger with default interval_minutes=10 and an injected clock at t=now+1min since last fire
When  trigger.should_fire(current_finding_count=1) is called
Then  return value is False (not enough time elapsed AND not enough new findings)

Given a CriticTrigger with default interval_minutes=10 and an injected clock at t=now+11min since last fire
When  trigger.should_fire(current_finding_count=1) is called
Then  return value is True (time-based trigger fired even though finding count below threshold)

Given SILENTWITNESS_CRITIC_INTERVAL_FINDINGS="3" is in the env
When  CriticTrigger(case_dir, examiner) is constructed
Then  trigger.interval_findings == 3

Given SILENTWITNESS_CRITIC_INTERVAL_MINUTES="2" is in the env
When  CriticTrigger(case_dir, examiner) is constructed
Then  trigger.interval_minutes == 2.0

Given cases/<case>/critic_state.json pre-exists with last_critic_finding_count=3
When  a fresh CriticTrigger is constructed and should_fire(5) is called
Then  return value is False (5 - 3 == 2 < interval=5)

Given trigger.mark_fired(5) has been called
When  the file cases/<case>/critic_state.json is inspected
Then  it contains last_critic_finding_count=5 and a valid ISO-8601 last_critic_at

Given a findings.json with 7 findings, of which the first 3 were already reviewed (last_critic_finding_count=3)
When  trigger.staged_findings_for_review(findings_json_path) is called
Then  return value is a list of 4 StagedFinding objects (indices 3..6)
And   each StagedFinding has populated cited_blob_paths read from cases/<case>/audit/blobs/

Given 10 threads concurrently call trigger.should_fire then mark_fired
When  all threads complete
Then  critic_state.json reflects exactly one firing per actual threshold crossing (no duplicate mark_fired side effects)

Given tests/unit/test_critic_trigger.py exists
When  `uv run pytest tests/unit/test_critic_trigger.py -v` runs
Then  exit code is 0
And   ≥10 tests pass

Given tests/integration/test_trigger_idempotent.py exists
When  `uv run pytest tests/integration/test_trigger_idempotent.py -v` runs
Then  exit code is 0
```

---

## Shell verification

```bash
# Import smoke
uv run python -c "from silentwitness_agent.critic_trigger import CriticTrigger; print('ok')"

# Unit tests
uv run pytest tests/unit/test_critic_trigger.py -v
# Must show ≥10 passing

# Integration (idempotency)
uv run pytest tests/integration/test_trigger_idempotent.py -v
# Must show 1 passing

# Env override smoke
SILENTWITNESS_CRITIC_INTERVAL_FINDINGS=3 SILENTWITNESS_CRITIC_INTERVAL_MINUTES=2 uv run python -c "
from pathlib import Path
import tempfile
from silentwitness_agent.critic_trigger import CriticTrigger
with tempfile.TemporaryDirectory() as d:
    t = CriticTrigger(case_dir=Path(d), examiner='aj')
    assert t.interval_findings == 3, t.interval_findings
    assert t.interval_minutes == 2.0, t.interval_minutes
    print('env overrides OK')
"

# Coverage ≥85%
uv run coverage run -m pytest tests/unit/test_critic_trigger.py tests/integration/test_trigger_idempotent.py
uv run coverage report --include="src/silentwitness_agent/critic_trigger.py,src/silentwitness_agent/_critic_state.py" --fail-under=85

# Strict typing + lint + file-size guard
uv run mypy --strict src/silentwitness_agent/critic_trigger.py src/silentwitness_agent/_critic_state.py
uv run ruff check src/silentwitness_agent/critic_trigger.py src/silentwitness_agent/_critic_state.py
uv run ruff format --check src/silentwitness_agent/critic_trigger.py src/silentwitness_agent/_critic_state.py
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_agent/critic_trigger.py src/silentwitness_agent/_critic_state.py
```

---

## Notes for coding agent

- Reference: architecture.md §5.5 verbatim:
  - "Every N findings staged. Default N=5; configurable via `SILENTWITNESS_CRITIC_INTERVAL_FINDINGS`."
  - "Every M minutes since last critic run. Default M=10; configurable via `SILENTWITNESS_CRITIC_INTERVAL_MINUTES`."
  - "whichever fires first" — the trigger uses `OR` semantics, not `AND`.
- Reference: PRD §2 row "4:00–4:30 Critic moment" — "Critic subagent fires after the 8th observation." The N=5 default puts the first firing around finding #5; the second around #10. The 4:00–4:30 demo arc is the "second firing" (post #8 findings) and the trigger logic above is what produces that cadence.
- Reference: PRD FR7 — ≥1 self-correction sequence in the demo. The critic CHALLENGE → corroboration loop IS the second self-correction (the first is the Vol3 symbol-table pivot from Epic 8); both are mandatory per Rules §4.
- `should_fire` is **idempotent and side-effect-free**. Callers may invoke it multiple times in a polling loop without advancing state. Only `mark_fired` mutates the persisted state. This separation is what enables the concurrent test scenario: the firing-window detection is read-only; only the explicit mark advances it.
- Persistence shape: `cases/<case_id>/critic_state.json` (NOT JSONL — single-state-document, atomic-rename writes). Pydantic `_TriggerState.model_dump_json()` serializes; `_load_state` reads via `model_validate_json`. Use the atomic-io helper (story-atomic-io) for `mark_fired` writes.
- Clock injection: `clock: Callable[[], datetime]` defaults to `lambda: datetime.now(UTC)`. Tests pass a fake clock that increments deterministically. NEVER call `datetime.now()` directly inside production paths — always through the injected callable. This is the same discipline as the audit logger (story-audit-logger).
- Threading: a single `threading.Lock` guards reads + writes on `critic_state.json` to prevent two concurrent `mark_fired` calls from racing. The investigator agent is single-threaded inside Pydantic AI's event loop, but the trigger may be called from multiple coroutines if the architecture evolves; protect at this layer.
- `staged_findings_for_review` is the bridge between this trigger and `critique()` (story-critic-agent). It reads `findings.json` (architecture §4 — finding state file), filters by index ≥ `last_critic_finding_count`, loads each finding's `cited_audit_ids` from the corresponding `audit/<backend>.jsonl` to find `stdout_path` for each, then reads the blob from `audit/blobs/<audit_id>.txt`. The result is the `list[StagedFinding]` ready for `critique()`. Blob truncation per story-critic-agent's 50KB cap is implemented here.
- Pitfall: a brand-new case has no `findings.json`. Handle the missing-file case by treating it as zero findings (return False from `should_fire(0)`).
- Pitfall: time comparison uses `datetime` with TZ awareness. Storing `last_critic_at` as ISO-8601 with `Z` suffix and parsing back via `datetime.fromisoformat` is the simplest pattern. Pydantic v2 handles this natively.
- Pitfall: `interval_minutes` is a float (allows fractional minutes for tests). The env var is parsed as float, not int.
- Library docs to consult via Context7 BEFORE coding:
  - `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic"` topic `"datetime ISO-8601 round-trip UTC frozen BaseModel"` — Pydantic v2's datetime parsing has UTC-handling edge cases; verify before coding.
- Vocabulary discipline: never "court-admissible," never "Ralph Wiggum Loop." Docstrings: "interval-based critic trigger; idempotent; persists state for restart-resume."
- LOC budget: ~220. Comfortable.
- After this story merges, the cadence is enforced. The critic verdict handler (story-critic-verdict-handling) is the third Epic-10 story — together they form the closed loop.
