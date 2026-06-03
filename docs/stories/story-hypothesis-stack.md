# Story — `HypothesisStack` state machine + JSONL event emission

**ID:** story-hypothesis-stack
**Epic:** Epic 8 — Hypothesis state machine + investigator agent (Pydantic AI)
**Depends on:** story-hypothesis-types, story-audit-logger, story-atomic-io
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** build the `HypothesisStack` class in `src/silentwitness_agent/hypothesis/stack.py` that manages the active hypothesis, the FIFO queue of pending hypotheses, and the history of resolved ones — and emits a `HypothesisEvent` JSONL line via the audit logger on every transition
**So that** the investigator agent (story-investigator-agent) has a single, testable, audit-emitting state machine for the form → dispatch → confirm/pivot/abandon lifecycle (architecture.md §5.3 — `HypothesisStack` methods + transition diagram; PRD FR7 — pivot count metric is `grep -c '"type":"pivot"' audit/hypothesis.jsonl`).

---

## File modification map

- `src/silentwitness_agent/hypothesis/stack.py` — NEW — `HypothesisStack` class. State: `active: Hypothesis | None`, `queued: deque[Hypothesis]`, `history: list[Hypothesis]`, `_seq: int` (monotonic ID counter), `_audit: AuditLogger` (injected). Methods:
  - `form(statement: str, specialist: SpecialistName, evidence_expected: list[str] | None = None, from_hypothesis_id: str | None = None) -> Hypothesis` — allocates next H-NNN, status=ACTIVE, formed_at=now(UTC). If `active is None` and queue is empty → becomes active. Otherwise → appended to `queued`. Emits FORM event.
  - `dispatch(hypothesis_id: str, specialist: SpecialistName) -> None` — asserts the hypothesis is `active` and status is ACTIVE; consults the budget enforcer (injected from story-hypothesis-budget) BEFORE marking dispatched. Emits DISPATCH event with `related_audit_ids=[]` (the actual tool-call audit_ids accumulate during specialist execution and are written into `Hypothesis.evidence_observed` at confirm/pivot time).
  - `confirm(hypothesis_id: str, evidence_audit_ids: list[str]) -> None` — sets status=CONFIRMED, appends `evidence_audit_ids` to `Hypothesis.evidence_observed`, moves from active to history, promotes next queued hypothesis to active (if any). Emits CONFIRM event with `related_audit_ids=evidence_audit_ids`.
  - `pivot(from_id: str, to_statement: str, reason: str, evidence_expected: list[str] | None = None) -> Hypothesis` — sets `from_id` status=PIVOTED, creates a new child via `form(to_statement, ..., from_hypothesis_id=from_id)`. Emits PIVOT event on the parent (carries `reason` + `related_audit_ids` from `parent.evidence_observed`). The child's FORM event is emitted by the `form` call. Returns the new child.
  - `abandon(hypothesis_id: str, reason: str) -> None` — sets status=ABANDONED, moves to history, promotes next queued. Emits ABANDON event with `reason`.
  - `snapshot() -> StackSnapshot` — returns a frozen Pydantic view of (active, queued, history, total_pivot_count). Used by the rich live layout (Epic 12) and the report renderer (Epic 11).
  - Target ≤380 LOC. (~7 public methods + invariant checks + JSONL emission helper.)
- `src/silentwitness_agent/hypothesis/_jsonl.py` — NEW — `emit_hypothesis_event(case_dir: Path, event: HypothesisEvent) -> None` helper. Appends one line to `case_dir/audit/hypothesis.jsonl` using `silentwitness_mcp.audit.logger.AuditLogger`'s atomic append path (NOT the AuditLogger class directly — `audit/hypothesis.jsonl` lives at the agent layer, not the MCP backend layer; the helper reuses `atomic_io.append_jsonl_line` from story-atomic-io for the same fsync-after-append discipline). ~60 LOC.
- `tests/unit/test_hypothesis_stack.py` — NEW — ≥14 behavioural tests:
  - empty stack `form("...", MEMORY)` returns H-001 and stack.active is H-001;
  - second `form()` while H-001 active goes to `queued`;
  - `dispatch(H-001, MEMORY)` succeeds; emits DISPATCH event;
  - `confirm(H-001, [audit_id1, audit_id2])` sets status=CONFIRMED, evidence_observed=[ids], moves to history, promotes next queued;
  - `pivot(H-001, "new statement", "vol3 symbol-table mismatch; rebuilt")` creates H-002 with formed_from="H-001"; parent status=PIVOTED;
  - `abandon(H-001, "BUDGET_EXHAUSTED")` sets ABANDONED, moves to history;
  - `confirm` on an inactive hypothesis raises `InvalidTransition`;
  - `dispatch` when budget enforcer denies raises `BudgetExceeded` (mock the injected enforcer to return False);
  - each transition appends exactly one line to `<case_dir>/audit/hypothesis.jsonl`;
  - the appended JSONL line parses back to `HypothesisEvent` via `model_validate_json`;
  - PIVOT event JSONL line contains `"type":"pivot"` literally (so `PRD §4` pivot-count grep works);
  - `snapshot()` returns immutable copies (mutating returned list does NOT mutate stack state);
  - thread-safety smoke: 50 concurrent `form` calls produce 50 unique IDs H-001..H-050 with no gaps or duplicates;
  - sequence-resume: pre-write 3 events with `_seq` 1..3 to `hypothesis.jsonl`, instantiate fresh stack, assert next H-id is H-004.
- `tests/property/test_hypothesis_stack_properties.py` — NEW — 3 Hypothesis property tests: random sequences of (form/dispatch/confirm/pivot/abandon) calls maintain invariants (at most one active hypothesis; total events == sum of transitions; pivot events always reference a parent that exists in history).

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given an empty case directory at /tmp/case-stack/
And   a fresh HypothesisStack(case_dir=/tmp/case-stack/, examiner="aj")
When  stack.form("If wardriving, expect promiscuous-mode tool", SpecialistName.MEMORY) is called
Then  the returned Hypothesis has id "H-001", status ACTIVE, formed_at non-None
And   stack.active is that hypothesis
And   /tmp/case-stack/audit/hypothesis.jsonl exists with exactly 1 line
And   the line parses as HypothesisEvent with type=FORM, hypothesis_id="H-001"

Given H-001 is active
When  stack.form("If persistence, expect Run-key entry", SpecialistName.DISK) is called
Then  the returned Hypothesis has id "H-002"
And   stack.active is still H-001
And   stack.queued contains H-002 at the front

Given H-001 is active and dispatched
When  stack.confirm("H-001", evidence_audit_ids=["sift-aj-20260613-007", "sift-aj-20260613-008"]) is called
Then  H-001 status is CONFIRMED
And   H-001 is in stack.history
And   stack.active is the previously-queued H-002
And   hypothesis.jsonl has 1 additional line with type=CONFIRM and related_audit_ids of length 2

Given H-001 is active
When  stack.pivot("H-001", "Vol3 symbol-table mismatch — rebuild then retry pstree", "vol3 symbol-table mismatch; rebuilt") is called
Then  H-001 status is PIVOTED
And   the returned new Hypothesis has id "H-002" with formed_from="H-001"
And   stack.active is H-002
And   hypothesis.jsonl has 2 additional lines (PIVOT on H-001, FORM on H-002)
And   `grep -c '"type":"pivot"' hypothesis.jsonl` returns 1 (PRD §4 metric)

Given an injected BudgetEnforcer that returns False for dispatch
When  stack.dispatch("H-001", SpecialistName.MEMORY) is called
Then  BudgetExceeded is raised
And   no DISPATCH event is appended to hypothesis.jsonl (rejection happens before transition)

Given the case directory contains a pre-existing hypothesis.jsonl with 3 prior FORM events (H-001..H-003)
When  a fresh HypothesisStack(case_dir=..., examiner="aj") is constructed
Then  stack._seq is 3 (resumed from prior state)
And   the next stack.form() returns H-004

Given 50 threads each call stack.form(...) concurrently
When  all threads complete
Then  exactly 50 unique hypothesis IDs are allocated (H-001..H-050)
And   no gaps or duplicates exist in the IDs
And   hypothesis.jsonl contains exactly 50 well-formed FORM lines

Given stack.snapshot() returns a StackSnapshot
When  the caller mutates snapshot.queued
Then  stack.queued is unchanged (snapshot is a defensive copy)

Given tests/unit/test_hypothesis_stack.py exists
When  `uv run pytest tests/unit/test_hypothesis_stack.py -v` runs
Then  exit code is 0
And   ≥14 tests pass

Given tests/property/test_hypothesis_stack_properties.py exists
When  `HYPOTHESIS_PROFILE=ci uv run pytest tests/property/test_hypothesis_stack_properties.py -v` runs
Then  exit code is 0
And   3 property tests pass
```

---

## Shell verification

```bash
# Unit tests
uv run pytest tests/unit/test_hypothesis_stack.py -v
# Must show ≥14 passing

# Property tests
HYPOTHESIS_PROFILE=ci uv run pytest tests/property/test_hypothesis_stack_properties.py -v --hypothesis-show-statistics
# Must show 3 passing

# Coverage ≥85% on stack.py (CICD_SPEC §8.1)
uv run coverage run -m pytest tests/unit/test_hypothesis_stack.py tests/property/test_hypothesis_stack_properties.py
uv run coverage report --include="src/silentwitness_agent/hypothesis/stack.py,src/silentwitness_agent/hypothesis/_jsonl.py" --fail-under=85

# PRD §4 pivot-count grep works end-to-end
uv run python -c "
from pathlib import Path
from silentwitness_agent.hypothesis.stack import HypothesisStack
from silentwitness_agent.hypothesis.types import SpecialistName
import tempfile
with tempfile.TemporaryDirectory() as d:
    s = HypothesisStack(case_dir=Path(d), examiner='aj')
    h1 = s.form('a', SpecialistName.MEMORY)
    s.pivot(h1.id, 'b', 'evidence contradicted')
    import subprocess
    out = subprocess.check_output(['grep', '-c', '\"type\":\"pivot\"', str(Path(d)/'audit'/'hypothesis.jsonl')])
    assert out.strip() == b'1', out
print('pivot-grep OK')
"

# Strict typing + lint
uv run mypy --strict src/silentwitness_agent/hypothesis/stack.py src/silentwitness_agent/hypothesis/_jsonl.py
uv run ruff check src/silentwitness_agent/hypothesis/
uv run ruff format --check src/silentwitness_agent/hypothesis/

# File-size guard
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_agent/hypothesis/stack.py src/silentwitness_agent/hypothesis/_jsonl.py
```

---

## Notes for coding agent

- Reference: architecture.md §5.3 verbatim — the state diagram is the contract:
  `[*] --> ACTIVE: form()` → `ACTIVE --> ACTIVE: dispatch()` → `ACTIVE --> CONFIRMED|PIVOTED|ABANDONED`. Concurrency is NOT supported in v1 (one hypothesis tested at a time per ADR-003); enforce in `dispatch` by asserting `active is the dispatched hypothesis`.
- Reference: PRD §4 — secondary metric "pivot count" is computed by `grep -c '"type":"pivot"' cases/<case_id>/audit/hypothesis.jsonl`. The literal string `"type":"pivot"` (lowercase, no spaces) MUST appear in the JSONL line. Pydantic's `model_dump_json` with the `HypothesisEventType.PIVOT` enum value `"pivot"` produces this naturally — verify in test.
- Reference: context/domain/01 §4.1 + §4.6 — pivot decision rule: "When evidence contradicts the current hypothesis, log a pivot event, name the contradicting evidence, form a new hypothesis." The `reason` field on PIVOT events is what the report and the demo show; populate it with the agent's stated reason verbatim (truncated to 240 chars in the helper).
- Reference: BRAINSTORM.md §4 verbatim audit schema. JSONL line shape (architecture §5.3):
  ```json
  {"ts":"<iso8601 UTC>","type":"form|dispatch|confirm|pivot|abandon","hypothesis_id":"H-007","reason":"<text>","related_audit_ids":["sift-aj-..."],"tokens_spent":3214,"steps_spent":6}
  ```
- Use `silentwitness_mcp.audit.logger.AuditLogger`-style atomic append (open append, fsync, close) per story-audit-logger pattern. Do NOT instantiate `AuditLogger` directly — the MCP-side logger owns `audit/<backend>.jsonl` for tool calls; this story owns `audit/hypothesis.jsonl` which is structurally simpler (no `audit_id` allocation needed, just append-with-fsync). Use `silentwitness_common.atomic_io.append_jsonl_line` from story-atomic-io directly.
- Thread safety: single `threading.Lock` on the stack guards `_seq`, `active`, `queued`, and the JSONL append. The 50-thread test confirms no interleaving. Architecture §4.4 says "no long-lived file handles" — we open append-mode for every write.
- `InvalidTransition` exception: declare locally in `stack.py` (not types.py — it's stack-internal), subclasses `WorkflowError`. Raised when caller attempts confirm/pivot/abandon on a hypothesis that is not currently active or has already terminated.
- `BudgetEnforcer` is **injected** via constructor (`HypothesisStack(case_dir, examiner, budget: BudgetEnforcer | None = None)`). Default `None` → no budget enforcement (used in tests where we want pure state-machine behaviour). The investigator agent (story-investigator-agent) wires a real `BudgetEnforcer` (story-hypothesis-budget) at runtime. The stack calls `budget.check_dispatch(hypothesis)` BEFORE marking dispatched.
- Sequence resume: at construction, the stack scans `case_dir/audit/hypothesis.jsonl` for the highest `hypothesis_id` (`H-NNN`), sets `_seq = max + 1` (or 1 if missing). Matches the audit-logger restart-resume discipline from story-audit-logger.
- `snapshot() -> StackSnapshot`: define `StackSnapshot` as a Pydantic frozen BaseModel here (not in types.py — internal to the stack). Fields: `active: Hypothesis | None`, `queued: tuple[Hypothesis, ...]` (tuple is immutable), `history: tuple[Hypothesis, ...]`, `total_pivot_count: int`. Used by the Epic 12 rich live layout for the "Current Hypothesis" panel.
- LOC budget: stack.py at ~380 is fine. If approaching 400, extract `_emit_event` helper to `_jsonl.py` (already there).
- Library docs to consult via Context7 BEFORE coding:
  - `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic"` then `query-docs` topic `"BaseModel deque tuple immutable model_config v2"` — Pydantic v2 has specific serialization edge cases for `deque` (it serializes to a list, which is fine for our case but worth a sanity check).
- Vocabulary discipline: never "Ralph Wiggum Loop," never "court-admissible." Docstrings describe the behavior plainly. Example for `pivot`: `"""Pivot from a hypothesis whose evidence contradicts it to a new child hypothesis with the contradicting evidence cited in the audit log."""`.
- Pitfall: when an active hypothesis transitions to history and there's a queued one, the promoted hypothesis becomes `active` BUT it does NOT auto-emit a new FORM event — it was already FORMED when first queued. Only `dispatch` is needed to start work on it. Test this explicitly.
