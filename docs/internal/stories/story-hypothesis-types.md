# Story — Hypothesis dataclasses + event types

**ID:** story-hypothesis-types
**Epic:** Epic 8 — Hypothesis state machine + investigator agent (Pydantic AI)
**Depends on:** story-common-types, story-audit-logger
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** define the `Hypothesis` dataclass, `HypothesisEvent` dataclass, and supporting enums (`HypothesisStatus`, `HypothesisEventType`, `SpecialistName`) in `src/silentwitness_agent/hypothesis/types.py`
**So that** the hypothesis stack (story-hypothesis-stack), the budget enforcer (story-hypothesis-budget), the investigator agent (story-investigator-agent), and the report renderer all consume one frozen type set for hypothesis transitions and the `audit/hypothesis.jsonl` schema is single-sourced (architecture.md §5.3 — Hypothesis dataclass + HypothesisEvent JSONL shape).

---

## File modification map

- `src/silentwitness_agent/__init__.py` — NEW — empty package marker (`__version__ = "0.0.0"` placeholder; real version populated by python-semantic-release).
- `src/silentwitness_agent/hypothesis/__init__.py` — NEW — empty package marker.
- `src/silentwitness_agent/hypothesis/types.py` — NEW — Pydantic v2 models (NOT plain dataclasses; we use Pydantic for free JSON serialization + `model_validate_json` round-trip in the audit JSONL writer):
  - `HypothesisStatus` (StrEnum): `ACTIVE`, `CONFIRMED`, `PIVOTED`, `ABANDONED`.
  - `HypothesisEventType` (StrEnum): `FORM`, `DISPATCH`, `CONFIRM`, `PIVOT`, `ABANDON`.
  - `SpecialistName` (StrEnum): `MEMORY`, `DISK`, `NETWORK`, `LOG`. (Imported from `silentwitness_common.types` if already defined there per story-common-types; re-exported here for ergonomic agent-side imports.)
  - `Hypothesis` (BaseModel, mutable — status + counters mutate): `id: str` (H-NNN), `statement: str` (min_length=1), `status: HypothesisStatus` (default ACTIVE), `formed_at: datetime`, `formed_from: str | None` (parent hypothesis ID if pivot child), `evidence_expected: list[str]` (one-line phrases the agent expected to find), `evidence_observed: list[str]` (audit_ids of confirming evidence), `assigned_specialist: SpecialistName | None`, `tokens_budgeted: int` (default 5000), `tokens_consumed: int` (default 0), `steps_budgeted: int` (default 10), `steps_consumed: int` (default 0). `model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)`.
  - `HypothesisEvent` (BaseModel, frozen): `ts: datetime`, `type: HypothesisEventType`, `hypothesis_id: str`, `reason: str` (default ""), `related_audit_ids: list[str]` (default []), `tokens_spent: int` (default 0), `steps_spent: int` (default 0). `model_config = ConfigDict(extra="forbid", frozen=True)`.
  - `BudgetExceeded` (exception): subclass of `WorkflowError` (defined in `silentwitness_common.types`); raised by the budget enforcer (story-hypothesis-budget) — declared here so types module owns the exception class alongside the budget fields.
  - Helper: `make_hypothesis_id(seq: int) -> str` returns `"H-NNN"` with zero-pad-3 width.
  - Target ≤220 LOC. (Imports + 4 enums + 2 BaseModels + 1 exception + 1 helper.)
- `tests/unit/test_hypothesis_types.py` — NEW — ≥10 behavioural tests: `Hypothesis` constructs with required fields; defaults populate (status=ACTIVE, tokens_budgeted=5000, steps_budgeted=10); `extra="forbid"` rejects unknown fields; `Hypothesis.status` is mutable but `HypothesisEvent` is frozen (assignment raises `ValidationError`); `model_dump_json` round-trips both models via `model_validate_json`; `HypothesisEventType` string values are stable (`"form"`, `"dispatch"`, etc., lowercase per JSONL convention in architecture.md §5.3); `make_hypothesis_id(1)` returns `"H-001"`; `make_hypothesis_id(42)` returns `"H-042"`; `make_hypothesis_id(1042)` returns `"H-1042"` (no leading zeros beyond 3); `BudgetExceeded` is importable from this module and subclasses `WorkflowError`.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given src/silentwitness_agent/hypothesis/types.py exists
When  `uv run python -c "from silentwitness_agent.hypothesis.types import Hypothesis, HypothesisEvent, HypothesisStatus, HypothesisEventType, SpecialistName, BudgetExceeded, make_hypothesis_id; print('ok')"` runs
Then  exit code is 0
And   stdout contains "ok"

Given HypothesisStatus is a StrEnum with values ACTIVE, CONFIRMED, PIVOTED, ABANDONED
When  `Hypothesis(id="H-001", statement="If wardriving, expect promiscuous-mode tool", formed_at=datetime.now(UTC), assigned_specialist=SpecialistName.MEMORY)` is constructed
Then  hypothesis.status == HypothesisStatus.ACTIVE
And   hypothesis.tokens_budgeted == 5000
And   hypothesis.steps_budgeted == 10
And   hypothesis.tokens_consumed == 0

Given Hypothesis has model_config extra="forbid"
When  Hypothesis is constructed with an unknown field rogue="value"
Then  pydantic.ValidationError is raised

Given a Hypothesis has been constructed with status=ACTIVE
When  hypothesis.status = HypothesisStatus.CONFIRMED is assigned
Then  no exception is raised (Hypothesis is intentionally mutable)
And   hypothesis.status == HypothesisStatus.CONFIRMED

Given a HypothesisEvent has been constructed (frozen)
When  event.reason = "new value" is assigned
Then  pydantic.ValidationError is raised (frozen models reject mutation)

Given make_hypothesis_id is defined
When  make_hypothesis_id(1), make_hypothesis_id(42), make_hypothesis_id(1042) are called
Then  return values are exactly "H-001", "H-042", "H-1042"

Given a HypothesisEvent is serialized via model_dump_json
When  the resulting JSON line is parsed via HypothesisEvent.model_validate_json
Then  the round-trip is identity (all fields preserved including timezone-aware ts)

Given HypothesisEventType values are JSONL-stable
When  HypothesisEventType.FORM.value, HypothesisEventType.DISPATCH.value, HypothesisEventType.PIVOT.value are read
Then  return values are exactly "form", "dispatch", "pivot" (lowercase, matching architecture.md §5.3 schema)

Given BudgetExceeded is declared here
When  `from silentwitness_agent.hypothesis.types import BudgetExceeded; from silentwitness_common.types import WorkflowError; assert issubclass(BudgetExceeded, WorkflowError)` runs
Then  exit code is 0

Given tests/unit/test_hypothesis_types.py exists
When  `uv run pytest tests/unit/test_hypothesis_types.py -v` runs
Then  exit code is 0
And   ≥10 tests pass

Given mypy --strict is configured
When  `uv run mypy --strict src/silentwitness_agent/hypothesis/types.py` runs
Then  exit code is 0
```

---

## Shell verification

```bash
# Import smoke
uv run python -c "from silentwitness_agent.hypothesis.types import (
    Hypothesis, HypothesisEvent, HypothesisStatus, HypothesisEventType,
    SpecialistName, BudgetExceeded, make_hypothesis_id,
); print('ok')"

# Unit tests
uv run pytest tests/unit/test_hypothesis_types.py -v
# Must show ≥10 passing

# Strict typing
uv run mypy --strict src/silentwitness_agent/hypothesis/

# Lint + format
uv run ruff check src/silentwitness_agent/hypothesis/
uv run ruff format --check src/silentwitness_agent/hypothesis/

# File-size guard
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_agent/hypothesis/types.py
# Must exit 0 (≤400 LOC; target ~220)

# Coverage ≥85% on the file (CICD_SPEC §8.1 project floor)
uv run coverage run -m pytest tests/unit/test_hypothesis_types.py
uv run coverage report --include="src/silentwitness_agent/hypothesis/types.py" --fail-under=85

# §14 no-mocks clean
git diff main...HEAD -- 'src/silentwitness_agent/hypothesis/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded)" | grep -v "test\|spec"
# Must output nothing
```

---

## Notes for coding agent

- Reference: architecture.md §5.3 (Hypothesis dataclass + HypothesisEvent JSONL schema verbatim — the schema in `cases/<case_id>/audit/hypothesis.jsonl` MUST exactly match `HypothesisEvent.model_dump_json` output of this module); §5.2 (SpecialistName values consumed by specialists in Epic 9).
- Reference: PRD.md FR7 (≥1 self-correction; the PIVOT event type is the load-bearing audit record for this requirement) and §4 (pivot count metric is `grep -c '"type":"pivot"' cases/<case_id>/audit/hypothesis.jsonl`).
- Reference: context/domain/01-dfir-foundations.md §4.1 — explicit-named-hypothesis-with-pivot is the senior-analyst discipline these types encode. Each `Hypothesis.statement` should be ONE concrete sentence ("expect promiscuous-mode capture tool + intercepted credentials"), not a checklist or a paragraph — enforced by `min_length=1` on the field, with a docstring noting that the investigator system prompt instructs the agent to compress to one sentence (story-investigator-agent).
- Pydantic v2 specifics: use `StrEnum` from stdlib `enum` (Python 3.12 ships it natively) for the three enums so they serialize cleanly to JSONL as quoted strings. Use `ConfigDict(extra="forbid", frozen=True)` for `HypothesisEvent` (frozen because events are immutable audit records). Use `ConfigDict(extra="forbid", str_strip_whitespace=True)` for `Hypothesis` (NOT frozen — status + counters mutate during a run).
- `SpecialistName` enum values MUST match `silentwitness_common.types.SpecialistName` exactly (story-common-types Already defines this). Re-export here via `from silentwitness_common.types import SpecialistName` rather than redefining, so the two layers cannot drift.
- `BudgetExceeded` exception declaration: `class BudgetExceeded(WorkflowError): pass` — keep it minimal. The actual budget enforcement logic lives in story-hypothesis-budget; this module just owns the class so `BudgetEnforcer` can `raise BudgetExceeded(reason=..., hypothesis_id=...)` without circular imports. If `WorkflowError` is not yet defined in `silentwitness_common.types`, define a local fallback `class BudgetExceeded(Exception): pass` and add a TODO note — story-common-types may need a tiny follow-up patch.
- `make_hypothesis_id(seq: int)` mirrors `make_finding_id` / `make_timeline_id` from story-common-types: zero-pad 3 digits up to 999, then natural width. Sequence number is monotonic per case; the stack (story-hypothesis-stack) owns the counter.
- `formed_from` is `str | None`: when the agent pivots H-003 → H-004, `H-004.formed_from = "H-003"`. This is what builds the demo's hypothesis-tree visualization. Architecture §5.3 transition diagram (`PIVOTED --> [*]: child hypothesis formed`) requires this field.
- `evidence_expected: list[str]` is for the investigator system prompt's "predict before you run" discipline (context/domain/01 §4.1) — the agent populates it at FORM time, and at CONFIRM time the stack compares it against `evidence_observed` to log a structured "matched 3 of 4 predicted" diff. Stories §5.3 (architecture) and the investigator prompt (story-investigator-agent) consume this — do NOT over-engineer it here; it is a `list[str]` of free-form phrases at this layer.
- Library docs to consult via Context7 BEFORE coding:
  - `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic"` then `query-docs` topic `"StrEnum model_config frozen v2"` — Pydantic v2 changed enum handling for JSON serialization; the StrEnum + `model_dump_json` interaction has at least one footgun (enum subclass + `use_enum_values` interaction). Verify before coding.
- Vocabulary discipline: never "court-admissible," never "Ralph Wiggum Loop." Docstrings describe the behaviour (e.g., "form one concrete hypothesis at a time, dispatch a specialist to test it, pivot when evidence contradicts").
- LOC budget tracking: types.py is small (~220 LOC). If approaching 400 (it shouldn't), split enums into a separate `enums.py` and re-export.
