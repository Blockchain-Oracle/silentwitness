# Story — JSONL audit logger with restart-resume

**ID:** story-audit-logger
**Epic:** Epic 2 — Common types + audit infrastructure
**Depends on:** story-common-types, story-atomic-io
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** build the JSONL audit writer in `src/silentwitness_mcp/audit/logger.py` that emits one append-only line per MCP tool call with the stable `audit_id` format `sift-<examiner>-<YYYYMMDD>-<NNN>` and resumes the sequence number across server restarts
**So that** every claim in the report can resolve to a real audit entry (PRD FR5; architecture §4.4 / §5.3 — JSONL discipline, fsync after each line, sequence resume reads highest extant `audit_id` for the current date at startup).

---

## File modification map

- `src/silentwitness_mcp/audit/__init__.py` — NEW — empty package marker.
- `src/silentwitness_mcp/audit/logger.py` — NEW — `AuditLogger` class. Methods: `__init__(self, case_dir: Path, examiner: str, clock: Callable[[], datetime] = ...)`; `_load_sequence_state(self) -> dict[date, int]` scans `case_dir/audit/*.jsonl` at startup, parses `audit_id`s for today's date, returns highest seq per date; `next_audit_id(self) -> str`; `emit(self, backend: str, tool: str, params: dict, result_summary: dict, result_sha256: str, stdout_path: Path, elapsed_ms: float, model_used: str, model_token_count: dict[str, int]) -> AuditEntry` — composes the AuditEntry, appends to `case_dir/audit/<backend>.jsonl` via atomic-io helper (open append, fsync, close), returns the entry; `audit_id_of(self, entry: AuditEntry) -> str` convenience accessor. (~280 LOC, splits if over.)
- `tests/unit/test_audit_logger.py` — NEW — 12 behavioral tests: `next_audit_id` produces `sift-aj-<today>-001` on empty case; second call returns `-002`; date rollover resets to `-001`; restart scenario — pre-write 3 lines with `-001`, `-002`, `-003` to memory.jsonl, instantiate new logger, assert next is `-004`; restart scenario across multiple backend files (memory.jsonl with `-005`, disk.jsonl with `-007`) returns `-008`; emit writes exactly one line to the correct backend file; emit calls fsync (mocked at the syscall level — `patch.object(os, 'fsync')` then assert called); emit refuses backend names containing `/`; emit refuses examiner mismatch (if examiner field set later); JSONL line parses back to AuditEntry via `model_validate_json`; concurrent emit calls from threads do not interleave (10 threads × 10 emits → 100 well-formed JSON lines); `next_audit_id` is thread-safe (no duplicate sequence numbers under 100-thread fan-out).
- `tests/property/test_audit_logger_properties.py` — NEW — 3 Hypothesis property tests: for any list of (backend, tool, params) tuples, replaying them produces strictly monotonic `audit_id` sequence numbers; for any pre-populated state, `_load_sequence_state` recovers the max correctly; emit-line-parse round-trip is identity (no data loss in JSONL serialization).

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given an empty case directory at /tmp/case-xyz/
When  AuditLogger(case_dir=/tmp/case-xyz/, examiner='aj').next_audit_id() is called
Then  return value is "sift-aj-<YYYYMMDD>-001" where YYYYMMDD is today (UTC)

Given an AuditLogger has just returned sift-aj-<today>-001
When  next_audit_id is called again
Then  return value is sift-aj-<today>-002

Given case-xyz/audit/memory.jsonl already contains 3 entries with audit_ids sift-aj-<today>-001..003
When  a fresh AuditLogger(case_dir=/tmp/case-xyz/, examiner='aj') is constructed and next_audit_id is called
Then  return value is sift-aj-<today>-004 (restart-resume per architecture §4.4)

Given case-xyz/audit/memory.jsonl contains sift-aj-<today>-005 and case-xyz/audit/disk.jsonl contains sift-aj-<today>-007
When  a fresh AuditLogger is constructed
Then  next_audit_id returns sift-aj-<today>-008 (max-across-backends)

Given an AuditLogger emits an entry for backend="memory"
When  the call returns
Then  case-xyz/audit/memory.jsonl exists
And   the file contains exactly one line
And   the line parses as AuditEntry via model_validate_json
And   AuditEntry.audit_id matches sift-aj-<today>-001

Given an AuditLogger is asked to emit with backend="../etc/passwd"
When  emit is called
Then  ValueError is raised with reason "invalid backend name"

Given 10 threads each call emit() 10 times concurrently
When  all threads complete
Then  case-xyz/audit/<backend>.jsonl contains exactly 100 well-formed JSON lines
And   all 100 audit_ids are unique
And   the sequence numbers form a contiguous range 001..100 (no gaps, no duplicates)

Given the JSONL line shape matches architecture §4.4
When  `head -1 case-xyz/audit/memory.jsonl | jq '.audit_id, .tool, .result_sha256, .stdout_path, .elapsed_ms, .model_used'` runs
Then  all fields are non-null

Given tests/unit/test_audit_logger.py exists
When  `uv run pytest tests/unit/test_audit_logger.py -v` runs
Then  exit code is 0
And   12 tests pass

Given tests/property/test_audit_logger_properties.py exists
When  `HYPOTHESIS_PROFILE=ci uv run pytest tests/property/test_audit_logger_properties.py -v` runs
Then  exit code is 0
And   3 property tests pass
```

---

## Shell verification

```bash
# Unit tests
uv run pytest tests/unit/test_audit_logger.py -v
# Must show 12 passing

# Property tests
HYPOTHESIS_PROFILE=ci uv run pytest tests/property/test_audit_logger_properties.py -v --hypothesis-show-statistics
# Must show 3 passing

# Coverage on the audit subtree must be ≥90% (architecture §14 + CICD_SPEC §8.1)
uv run coverage run -m pytest tests/unit/test_audit_logger.py tests/property/test_audit_logger_properties.py
uv run coverage report --include="src/silentwitness_mcp/audit/logger.py" --fail-under=90

# Strict typing
uv run mypy --strict src/silentwitness_mcp/audit/

# Lint clean
uv run ruff check src/silentwitness_mcp/audit/

# File size guard
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_mcp/audit/logger.py

# §14 no-mocks check (test mocks are fine; production mocks are not)
git diff main...HEAD -- 'src/silentwitness_mcp/audit/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded)" | grep -v "test\|spec"
# Must output nothing
```

---

## Notes for coding agent

- Reference: architecture.md §4.4 (audit_id format + sequence resume semantics — verbatim: "The sequence number resumes across server restarts by reading the highest extant audit_id for the current date from the case's audit/*.jsonl files at startup"), §5.3 (HypothesisEvent JSONL — DO NOT implement here; Epic 8 owns hypothesis.jsonl).
- Reference: BRAINSTORM.md §4 (entry schema verbatim).
- Reference: PRD.md FR5 (audit JSONL per tool call).
- Use the `atomic-io` helpers from story-atomic-io for the fsync-after-append discipline. The actual API: `atomic_io.append_jsonl_line(path, line)` opens the file in append mode (`"a"`), writes the line + `\n`, calls `fsync(fd)`, closes. NO long-lived file handles per architecture §4.4 "no long-lived file handles, so concurrent writes from multiple tool calls cannot interleave bytes."
- Thread safety: the logger holds an internal `threading.Lock` that serializes `next_audit_id` + emit (so the sequence counter and the append are atomic together). Test thread safety explicitly per the 100-thread acceptance criterion.
- The clock is injected (`clock: Callable[[], datetime]` defaulting to `lambda: datetime.now(UTC)`) so the date-rollover test is deterministic. NEVER call `datetime.now()` directly inside production code paths — always go through the injected callable.
- Use `silentwitness_common.ids.make_audit_id` + `parse_audit_id` from story-common-types. Do NOT re-implement format logic here.
- Sequence resume: scan `case_dir/audit/*.jsonl`. For each line, `parse_audit_id` the `audit_id` field. Group by date. Track max seq per date. The next seq is `max(today_seqs) + 1` (or 1 if today has no entries). Tolerate the empty file case + the missing directory case (return 1).
- Backend name validation: must match `^[a-z][a-z0-9_]{0,31}$`. Reject anything with path separators, dot-dot, leading digits, or empty.
- Do NOT implement the OS append-only flag (`chattr +a`) per architecture §4.4 — it requires root and is environment-dependent. The deny rule in Claude Code settings.json prevents the LLM from editing the file; the MCP server is the only writer.
- Do NOT log the password, the HMAC key, or any cred material via this logger. Those flow through `audit/ledger.py` (story-hmac-ledger) which writes to a different path (`/var/lib/silentwitness/verification/`).
- Library docs to consult via Context7 BEFORE coding:
  - `structlog` topic `JSONL bound logger` (the recommended pattern for our scope is direct `model_dump_json()` write, NOT structlog — but check current 24+ docs in case we benefit from structlog's contextvars binding for examiner threading).
  - `pydantic` topic `model_dump_json by_alias exclude_none` (we want compact, deterministic JSON serialization).
- Pitfall: on macOS, fsync semantics differ from Linux — `os.fsync(fd)` on macOS does not guarantee disk persistence (need `fcntl(F_FULLFSYNC)`). For the hackathon we accept the Linux semantics; document this in a code comment and do not over-engineer for macOS.
