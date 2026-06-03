# Story — Common Pydantic v2 types

**ID:** story-common-types
**Epic:** Epic 2 — Common types + audit infrastructure
**Depends on:** story-scaffold-uv-pyproject
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** define the shared Pydantic v2 models — `Finding`, `Observation`, `Interpretation`, `Pivot`, `ResponseEnvelope` (a.k.a. `ToolResponse`), `AuditEntry`, `CitedSpan`, `DataProvenance`, plus supporting enums — in `src/silentwitness_common/types.py` and the ID generators in `src/silentwitness_common/ids.py`
**So that** every component (MCP server tools, agent, hypothesis stack, report renderer, audit logger, ledger) consumes one type set and ID format (architecture §5.2 — shared types; §6.3 — record_observation surface; PRD FR5 `audit_id` format).

---

## File modification map

- `src/silentwitness_common/types.py` — NEW — Pydantic v2 models: `Confidence` (enum: LOW/MEDIUM/HIGH), `EvidenceType` (disk_image/memory_dump/evtx/pcap/hive/other), `HypothesisStatus` (ACTIVE/CONFIRMED/PIVOTED/ABANDONED), `SpecialistName` (MEMORY/DISK/NETWORK/LOG), `ReportSection` (executive_summary/engagement_overview/methodology/findings/timeline/iocs/recommendations/gaps/appendix_audit), `FindingStatus` (DRAFT/REVIEWED/FINAL/ARCHIVED), `CriticVerdict` (AGREE/CHALLENGE/REJECT), `CitedSpan`, `DataProvenance`, `Observation`, `Interpretation`, `Pivot`, `Finding`, `AuditEntry`, `ToolResponse[TPayload]` (alias `ResponseEnvelope`). All `model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)` except `Finding` (mutable status field). (~350 LOC, splits if over.)
- `src/silentwitness_common/ids.py` — NEW — ID generators: `make_finding_id(seq: int) -> str` returns `F-<NNN>`, `make_timeline_id(seq: int) -> str` returns `T-<NNN>`, `make_audit_id(examiner: str, date: date, seq: int) -> str` returns `sift-<slug>-<YYYYMMDD>-<NNN>`, `parse_audit_id(s: str) -> AuditIdParts` returns NamedTuple of (examiner, date, seq), `slug_examiner(name: str) -> str` lowercase + strip non-alnum (~120 LOC).
- `tests/unit/test_common_types.py` — NEW — 14 behavioral tests: each Pydantic model round-trips via `model_dump_json` / `model_validate_json`; `CitedSpan` rejects negative line_start; `CitedSpan` rejects line_end <= line_start; `Observation` rejects empty cited_spans list; `Observation` rejects empty audit_ids list; `Finding` defaults to status=DRAFT; `ToolResponse[ProcessListOutput]` parametric typing works; enum string values are stable across releases (string-valued not int); `Confidence.HIGH > Confidence.MEDIUM > Confidence.LOW` is comparable.
- `tests/unit/test_common_ids.py` — NEW — 8 behavioral tests: `make_audit_id("ajweb3", date(2026,6,13), 7)` returns `"sift-ajweb3-20260613-007"`; `parse_audit_id` round-trips; `make_finding_id(1)` returns `"F-001"`; `make_timeline_id(42)` returns `"T-042"`; `slug_examiner("AJ Web3!")` returns `"ajweb3"`; `slug_examiner("")` raises ValueError; sequence numbers ≥1000 produce 4-digit `NNNN` not `NNN`.
- `tests/property/test_audit_id_properties.py` — NEW — 4 Hypothesis property tests: `parse_audit_id(make_audit_id(e, d, n)) == (slug_examiner(e), d, n)` for valid e/d/n; `make_audit_id` is injective for distinct (e, d, n) triples; slug_examiner is idempotent; round-trip preserves date.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given src/silentwitness_common/types.py exists with the Pydantic v2 model set
When  `uv run python -c "from silentwitness_common.types import Observation, Interpretation, Pivot, Finding, ToolResponse, AuditEntry, CitedSpan, DataProvenance; print('ok')"` runs
Then  exit code is 0
And   stdout contains "ok"

Given the type models declare model_config = ConfigDict(extra='forbid')
When  an unknown field is passed to Observation
Then  pydantic.ValidationError is raised

Given make_audit_id is defined
When  `make_audit_id("ajweb3", date(2026,6,13), 7)` is called
Then  return value is exactly "sift-ajweb3-20260613-007"

Given parse_audit_id is defined
When  `parse_audit_id("sift-ajweb3-20260613-007")` is called
Then  return value is ("ajweb3", date(2026,6,13), 7)

Given slug_examiner is defined
When  `slug_examiner("AJ Web3!")` is called
Then  return value is "ajweb3"

Given Finding defaults to status=DRAFT
When  Finding(id="F-001", observation_id="O-007", interpretation_id="I-007") is constructed
Then  Finding.status == FindingStatus.DRAFT

Given tests/unit/test_common_types.py exists
When  `uv run pytest tests/unit/test_common_types.py -v` runs
Then  exit code is 0
And   14 tests pass

Given tests/unit/test_common_ids.py exists
When  `uv run pytest tests/unit/test_common_ids.py -v` runs
Then  exit code is 0
And   8 tests pass

Given tests/property/test_audit_id_properties.py exists with Hypothesis strategies
When  `HYPOTHESIS_PROFILE=ci uv run pytest tests/property/test_audit_id_properties.py -v` runs
Then  exit code is 0
And   4 property tests pass with no shrunk failures

Given mypy --strict is configured
When  `uv run mypy --strict src/silentwitness_common/` runs
Then  exit code is 0 (Generic[TPayload] resolves; no Any leaks)
```

---

## Shell verification

```bash
# Import smoke
uv run python -c "from silentwitness_common.types import (
    Observation, Interpretation, Pivot, Finding, ToolResponse, AuditEntry,
    CitedSpan, DataProvenance, Confidence, EvidenceType, HypothesisStatus,
    SpecialistName, ReportSection, FindingStatus, CriticVerdict,
); print('ok')"

# Unit tests
uv run pytest tests/unit/test_common_types.py tests/unit/test_common_ids.py -v
# Must show 22 passing (14 + 8)

# Property tests
HYPOTHESIS_PROFILE=ci uv run pytest tests/property/test_audit_id_properties.py -v --hypothesis-show-statistics
# Must show 4 passing

# Strict typing
uv run mypy --strict src/silentwitness_common/
# Must exit 0

# Lint clean
uv run ruff check src/silentwitness_common/
# Must exit 0

# Format clean
uv run ruff format --check src/silentwitness_common/
# Must exit 0

# File size guard
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_common/types.py src/silentwitness_common/ids.py
# Must exit 0 (both ≤400 LOC)

# §14 no-mocks check
git diff main...HEAD -- 'src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded)" | grep -v "test\|spec"
# Must output nothing
```

---

## Notes for coding agent

- Reference: architecture.md §4.3 (`ToolResponse` envelope shape — fields `success`, `data`, `audit_id`, `examiner`, `caveats`, `advisories`, `corroboration`, `discipline_reminder`, `data_provenance`), §4.4 (`AuditEntry` schema), §5.2 (`Hypothesis` dataclass shape — note: this lives in `silentwitness_agent/hypothesis/` and is owned by Epic 8, NOT this story), §5.4 (Finding shape — observation_id, interpretation_id, status), §5.5 (`CriticVerdict` model).
- Reference: PRD.md FR5 (`audit_id` format `sift-<examiner>-<YYYYMMDD>-<NNN>` with restart-resume — sequence resume logic is story-audit-logger, NOT here; this story owns the format only).
- Reference: BRAINSTORM.md §4 (verbatim entry schema).
- `ToolResponse[TPayload]` is `Generic[TPayload]` — payload models live in tool wrapper modules (`tools/memory.py`, etc., owned by E5/E6/E7). Define the generic here; do NOT define `ProcessListOutput`, `NetscanOutput`, etc. in this story.
- `CitedSpan` fields: `audit_id: str`, `sha256_of_normalized_output: str` (validated `^[a-f0-9]{64}$`), `line_start: int >= 0`, `line_end: int > line_start`, `span_text: str` (`min_length=1`).
- `DataProvenance` fields: `tool: str`, `stdout_path: Path`, `result_sha256: str`, `elapsed_ms: float`, `cmd_argv: list[str]`. All required.
- `Finding` MUST allow status mutation — it transitions DRAFT → REVIEWED → FINAL → ARCHIVED. Use `model_config = ConfigDict(extra="forbid")` but do NOT freeze it. All other models freeze.
- `Confidence` is a string-valued enum (`"LOW"`, `"MEDIUM"`, `"HIGH"`). Add a `__lt__` / `__gt__` via an `_order` class attribute so comparisons work for the critic verdict logic later.
- Examiner slug rules: lowercase, strip all non-alphanumeric, raise `ValueError` if result is empty. Max length 32 chars (truncate). Used in `audit_id` format.
- Sequence number: zero-pad to 3 digits (`001`-`999`); for `seq >= 1000` use the natural width (no leading zeros beyond 3). The format becomes `sift-aj-20260613-1042` and `parse_audit_id` must still round-trip.
- For Pydantic v2: use `model_dump_json` / `model_validate_json` NOT `.json()` / `.parse_raw()`. Use `Field(default_factory=list)` for mutable defaults. NEVER use mutable default arguments per architecture §13 banned patterns.
- mypy strict will complain about `Generic[TPayload]` if `TPayload = TypeVar("TPayload", bound=BaseModel)` is omitted — bound it.
- Library docs to consult via Context7 BEFORE coding:
  - `pydantic` topic `model_config ConfigDict v2 frozen extra forbid` (v2 model_config replaces v1 Config class).
  - `pydantic` topic `generic models TypeVar` (Generic[TPayload] in v2 has stricter typing than v1).
- The file may approach 400 LOC. If it crosses, split into `types.py` (models) + `enums.py` (the 8 enums). Document the split in the commit body per CICD_SPEC §14.
