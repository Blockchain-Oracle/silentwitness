# Story — `record_observation` MCP tool (citation gate + entity gate + sanitizer wired)

**ID:** story-record-observation-tool
**Epic:** Epic 4 — MCP server skeleton + finding-state tools
**Depends on:** story-fastmcp-server-bootstrap, story-response-envelope, story-citation-gate, story-entity-gate, story-sanitizer, story-audit-logger
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness MCP client (the reference agent or any compliant host)
**I want to** call `record_observation(text, cited_spans, audit_ids)` and receive either an accepted `ObservationResult(observation_id=...)` or a structured `REJECTED` with reason and self-correctable context
**So that** the killer demo moment at 3:30–4:00 — hallucinated path rejected by the server, agent re-reads tool output, revises with verbatim path, observation accepted — works exactly as architected

---

## File modification map

Exact files the coding agent creates or modifies:

- `src/silentwitness_mcp/findings/__init__.py` — NEW — package marker
- `src/silentwitness_mcp/findings/observation.py` — NEW — `@mcp.tool() async def record_observation(...)` implementing the citation + entity + sanitizer pipeline; emits audit entry on both accept and reject (≤300 LOC; architecture.md §4.2 row `record_observation`)
- `src/silentwitness_mcp/findings/_id_gen.py` — NEW — observation ID generator (O-NNN sequencer) backed by case directory state (≤80 LOC)
- `tests/integration/test_record_observation.py` — NEW — ≥15 BDD scenarios: valid observation accepted; each reject reason tested end-to-end; structured context returned for self-correction; audit entry emitted on both paths
- `tests/fixtures/observations/` — NEW directory — hand-crafted observation fixtures (valid + each rejection case) with companion blob fixtures

The coding agent must NOT modify files outside this map.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a registered audit entry sift-aj-20260613-007 whose stored blob contains the verbatim text "svchost.exe at PID 1208 has parent cmd.exe at PID 4172"
And   an ObservationInput citing that audit_id with correct sha256, lines, and span_text
When  record_observation is called
Then  the result is ObservationResult(success=True, observation_id="O-001")
And   a JSONL entry is appended to cases/<case_id>/audit/findings.jsonl with audit_id sift-aj-20260613-NNN
And   findings.json gains an entry with observation_id="O-001"

Given an ObservationInput citing an audit_id that does NOT exist
When  record_observation is called
Then  the result is ObservationResult(success=False, reason="AUDIT_ID_NOT_FOUND")
And   the audit entry for this rejection IS still written (rejected calls are also audited)

Given an ObservationInput whose sha256_of_normalized_output does not match the stored blob
When  record_observation is called
Then  the result is ObservationResult(success=False, reason="OUTPUT_HASH_MISMATCH")
And   the result.context contains expected_sha256 and actual_sha256

Given an ObservationInput whose span_text is NOT in the cited line range
When  record_observation is called
Then  the result is ObservationResult(success=False, reason="SPAN_NOT_IN_LINES")
And   the result.context contains the line range that was checked

Given an ObservationInput whose text contains a path NOT in any cited span (the Ethereal demo case)
When  record_observation is called
Then  the result is ObservationResult(success=False, reason="HALLUCINATED_ENTITIES")
And   the result.hallucinated list contains the missing path
And   the result.suggested string includes the verbatim path FROM the cited span

Given an ObservationInput whose text contains an XML role token like <system>
When  record_observation is called
Then  the sanitizer strips the token before the entity gate runs
And   a JSONL entry is appended to cases/<case_id>/audit/sanitizer.jsonl

Given an ObservationInput that passes all three gates
When  record_observation is called
Then  the observation is appended to findings.json
And   the data_provenance.tool field of the audit entry equals "record_observation"
And   the result.audit_id matches the format sift-<examiner>-<YYYYMMDD>-<NNN>

Given the reference agent self-corrects after a HALLUCINATED_ENTITIES rejection
When  it resubmits with the verbatim path from the suggested context
Then  the second call succeeds with success=True

Given the test suite is run
When  uv run pytest tests/integration/test_record_observation.py
Then  ≥15 test cases pass
And   coverage on src/silentwitness_mcp/findings/observation.py is ≥90%
```

---

## Shell verification

```bash
# Integration tests pass with ≥15 cases
uv run pytest tests/integration/test_record_observation.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥15

# Coverage ≥90% on the file (findings/ floor per architecture.md §14)
uv run coverage run -m pytest tests/integration/test_record_observation.py
uv run coverage report --include="src/silentwitness_mcp/findings/observation.py" --fail-under=90

# All reject reasons exercised end-to-end
for r in AUDIT_ID_NOT_FOUND OUTPUT_HASH_MISMATCH SPAN_NOT_IN_LINES LINE_RANGE_OUT_OF_BOUNDS HALLUCINATED_ENTITIES; do
  grep -q "$r" tests/integration/test_record_observation.py || { echo "missing test for $r"; exit 1; }
done

# Lint + types
uv run ruff check src/silentwitness_mcp/findings/observation.py
uv run mypy --strict src/silentwitness_mcp/findings/observation.py

# File-size guard
[ "$(wc -l < src/silentwitness_mcp/findings/observation.py)" -le 400 ]

# The demo scenario from architecture.md §8.4 is implemented as a test
grep -q "Ethereal" tests/integration/test_record_observation.py && grep -q "Program Files" tests/integration/test_record_observation.py
```

---

## Notes for coding agent

- Source of truth: architecture.md §4.2 (`record_observation` row — input model `ObservationInput(text: str, cited_spans: list[CitedSpan], audit_ids: list[str])`, output `ObservationResult`); §4.5 (citation gate algorithm); §4.7 (entity gate algorithm); §4.8 (sanitizer); §4.4 (audit JSONL schema); §8.1 (success sequence); §8.4 (rejection sequence — the killer demo moment); `PRD` §2 row "3:30–4:00 Citation-gate moment".
- Tool decorator: `@mcp.tool(name="record_observation", description="Record an observation grounded in cited tool output spans.")` from the FastMCP instance in story-fastmcp-server-bootstrap.
- Pipeline order is LOAD-BEARING (architecture.md §8.4):
  1. Sanitize `text` (story-sanitizer; logs any strip events to `audit/sanitizer.jsonl`).
  2. Citation gate over every cited_span (story-citation-gate). On reject → AUDIT the rejection → return.
  3. Entity gate over the sanitized text vs all cited_span span_texts (story-entity-gate). On reject → AUDIT → return.
  4. Allocate observation_id via `_id_gen.next_observation_id()`.
  5. Append observation to `cases/<case_id>/findings.json` (atomic — use story-atomic-io).
  6. Emit audit JSONL entry to `cases/<case_id>/audit/findings.jsonl` (story-audit-logger).
  7. Return `ObservationResult(success=True, observation_id=...)` wrapped in `ToolResponse[ObservationResult]` (story-response-envelope).
- REJECTED paths MUST still emit an audit entry. The audit log is the truth of "what the agent attempted" — rejected attempts are evidence too (and the demo arc relies on the rejection being audited so the verify-link click resolves).
- Self-correction hint: the rejection envelope's `result.suggested` field (when reason=HALLUCINATED_ENTITIES) carries the verbatim text from the cited span that the model should use. This is what enables the agent's revise → resubmit → accept loop (architecture.md §8.4 last steps).
- `ObservationInput` Pydantic model:
  ```python
  class ObservationInput(BaseModel):
      text: str                       # the observation prose
      cited_spans: list[CitedSpan]    # per architecture.md §4.5
      audit_ids: list[str]            # superset of cited_spans' audit_ids
  ```
- `ObservationResult` (carried as `TPayload` of `ToolResponse`):
  ```python
  class ObservationResult(BaseModel):
      success: bool
      observation_id: str | None = None
      reason: ObservationRejectReason | None = None
      context: dict[str, Any] = Field(default_factory=dict)
      hallucinated: list[str] = Field(default_factory=list)
      suggested: str | None = None
  ```
- `ObservationRejectReason` StrEnum union of citation + entity reasons: `AUDIT_ID_NOT_FOUND | OUTPUT_HASH_MISMATCH | SPAN_NOT_IN_LINES | LINE_RANGE_OUT_OF_BOUNDS | STDOUT_PATH_MISSING | HALLUCINATED_ENTITIES`.
- Observation ID generator: `O-NNN` zero-padded, resumes across server restarts by reading max(O-id) from `findings.json`.
- Audit entry shape (architecture.md §4.4 verbatim): `{ts, audit_id, tool: "record_observation", params: <ObservationInput JSON>, result_summary: <ObservationResult JSON, truncated to 1KB>, result_sha256, stdout_path, elapsed_ms, examiner, model_used, model_token_count}`. For rejections, `result_summary` still carries the reason and context.
- Context7 hints: `mcp__plugin_context7_context7__resolve-library-id libraryName="mcp"` then query topic "FastMCP tool decorator typed input output Pydantic". The decorator's signature handling differs between MCP SDK versions.
- Vocabulary: never "court-admissible." The envelope says "data_provenance" — that's the framing.
- Known pitfalls: (1) the entity gate's spaCy load is slow on first call; warm it in the lifecycle startup hook (story-fastmcp-server-bootstrap) so the first observation doesn't pay the cost; (2) the citation gate needs the audit index built from prior JSONL entries — pass it via the lifecycle-injected dependency rather than re-reading on every call; (3) `findings.json` writes MUST be atomic-rename (story-atomic-io) to survive crashes mid-write; (4) when both citation gate AND entity gate would reject, return the citation reason FIRST (it's the more upstream failure).
