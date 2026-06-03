# Story — `record_pivot` MCP tool (hypothesis pivot event emission)

**ID:** story-record-pivot-tool
**Epic:** Epic 4 — MCP server skeleton + finding-state tools
**Depends on:** story-fastmcp-server-bootstrap, story-response-envelope, story-audit-logger
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** SilentWitness investigator agent abandoning one hypothesis in favor of another
**I want to** call `record_pivot(from_hypothesis_id, to_hypothesis_id, reason, abandoning_evidence)` and have the server emit a structured pivot event to `audit/hypothesis.jsonl`
**So that** the demo's pivot count (PRD §4 secondary metric) is auditable, and the self-correction moment at 3:00–3:30 (Vol3 symbol-table mismatch → rebuild → retry) renders as a logged PIVOT transition

---

## File modification map

Exact files the coding agent creates or modifies:

- `src/silentwitness_mcp/findings/pivot.py` — NEW — `@mcp.tool() async def record_pivot(...)` emitting a `HypothesisEvent(type="pivot", ...)` to `cases/<case_id>/audit/hypothesis.jsonl` (≤150 LOC; architecture.md §4.2 row `record_pivot`, §5.3 HypothesisEvent schema)
- `tests/integration/test_record_pivot.py` — NEW — ≥8 BDD scenarios: valid pivot; missing from_hypothesis_id; missing to_hypothesis_id; missing reason; audit emission; sequence preservation

The coding agent must NOT modify files outside this map.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given an active hypothesis H-001 and a newly-formed hypothesis H-002
And   PivotInput(from_hypothesis_id="H-001", to_hypothesis_id="H-002", reason="vol3 symbol-table mismatch on netscan; pivot to windows.info to determine OS build", abandoning_evidence=["sift-aj-20260613-007"])
When  record_pivot is called
Then  the result is PivotResult(success=True, pivot_id="P-001")
And   cases/<case_id>/audit/hypothesis.jsonl gains exactly one JSONL line with type="pivot"
And   that line includes from_hypothesis_id, to_hypothesis_id, reason, and related_audit_ids matching the input

Given PivotInput with from_hypothesis_id referencing a hypothesis that does not exist
When  record_pivot is called
Then  the result is PivotResult(success=False, reason="HYPOTHESIS_NOT_FOUND")
And   context.field == "from_hypothesis_id"

Given PivotInput with empty reason string
When  record_pivot is called
Then  the result is PivotResult(success=False, reason="MISSING_REQUIRED_FIELD")
And   context.field == "reason"

Given PivotInput with empty abandoning_evidence list
When  record_pivot is called
Then  the result is PivotResult(success=False, reason="MISSING_ABANDONING_EVIDENCE")

Given five sequential record_pivot calls in the same case
When  the audit/hypothesis.jsonl is inspected
Then  there are five lines with type="pivot"
And   the pivot_ids are P-001 through P-005 in order

Given a reason string containing an XML role token
When  record_pivot is called
Then  the sanitizer strips it before the event is persisted

Given the test suite runs
When  uv run pytest tests/integration/test_record_pivot.py
Then  ≥8 tests pass
And   coverage on src/silentwitness_mcp/findings/pivot.py is ≥90%
```

---

## Shell verification

```bash
# Tests pass with ≥8 cases
uv run pytest tests/integration/test_record_pivot.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥8

# Coverage ≥90%
uv run coverage run -m pytest tests/integration/test_record_pivot.py
uv run coverage report --include="src/silentwitness_mcp/findings/pivot.py" --fail-under=90

# Reject reasons tested
for r in HYPOTHESIS_NOT_FOUND MISSING_REQUIRED_FIELD MISSING_ABANDONING_EVIDENCE; do
  grep -q "$r" tests/integration/test_record_pivot.py || { echo "missing test for $r"; exit 1; }
done

# Lint + types
uv run ruff check src/silentwitness_mcp/findings/pivot.py
uv run mypy --strict src/silentwitness_mcp/findings/pivot.py

# File-size guard
[ "$(wc -l < src/silentwitness_mcp/findings/pivot.py)" -le 400 ]

# The pivot-count metric (PRD §4) can be computed from the audit log
grep -c '"type":"pivot"' /tmp/test-case/audit/hypothesis.jsonl
```

---

## Notes for coding agent

- Source of truth: architecture.md §4.2 (`record_pivot` row: `PivotInput(from_hypothesis_id: str, to_statement: str, reason: str)`); §5.3 (HypothesisEvent schema — `{ts, type, hypothesis_id, reason, related_audit_ids, tokens_spent, steps_spent}`); `PRD` §4 (secondary metric: pivot count); `BRAINSTORM` §3.2 (Decision 2 — hypothesis-pivot engine is the demo gold).
- The architecture.md §4.2 input is `(from_hypothesis_id, to_statement, reason)`. This story REFINES to `(from_hypothesis_id, to_hypothesis_id, reason, abandoning_evidence)` because:
  - `to_hypothesis_id` (instead of `to_statement`): the new hypothesis is formed via the agent-side `HypothesisStack.form()` (Epic 8) which allocates the ID; the MCP tool just records the transition. The hypothesis stack and its event log are split across the server-side audit (this tool) and the agent-side state machine (Epic 8). Document this refinement in the module docstring.
  - `abandoning_evidence: list[str]`: the audit_ids of evidence that led to abandoning the from-hypothesis. This is what the report's Findings section cites when explaining the pivot.
- Pipeline:
  1. Sanitize `reason` (story-sanitizer).
  2. Validate `from_hypothesis_id` exists in `cases/<case_id>/audit/hypothesis.jsonl`. Reject `HYPOTHESIS_NOT_FOUND` otherwise.
  3. Validate `to_hypothesis_id` is well-formed (matches `H-\d{3}`). Note we do NOT require `to_hypothesis_id` to exist yet — the agent may record the pivot before forming the child hypothesis.
  4. Validate `reason` is non-empty post-sanitize. Reject `MISSING_REQUIRED_FIELD` otherwise.
  5. Validate `abandoning_evidence` is non-empty. Reject `MISSING_ABANDONING_EVIDENCE`.
  6. Allocate `P-NNN` pivot_id.
  7. Append a `HypothesisEvent(type="pivot", hypothesis_id=from_hypothesis_id, reason=..., related_audit_ids=abandoning_evidence, ...)` to `cases/<case_id>/audit/hypothesis.jsonl`.
  8. Emit an audit JSONL entry to `cases/<case_id>/audit/findings.jsonl` (tool="record_pivot").
  9. Return `ToolResponse[PivotResult]`.
- `PivotInput`:
  ```python
  class PivotInput(BaseModel):
      from_hypothesis_id: str       # H-\d{3} pattern
      to_hypothesis_id: str         # H-\d{3} pattern; need not exist yet
      reason: str                   # min_length=10 post-sanitize
      abandoning_evidence: list[str]  # audit_ids of evidence that led to abandon
  ```
- `PivotResult`:
  ```python
  class PivotResult(BaseModel):
      success: bool
      pivot_id: str | None = None
      reason: PivotRejectReason | None = None
      context: dict[str, Any] = Field(default_factory=dict)
  ```
- `PivotRejectReason` StrEnum: `HYPOTHESIS_NOT_FOUND | MISSING_REQUIRED_FIELD | MISSING_ABANDONING_EVIDENCE | MALFORMED_HYPOTHESIS_ID`.
- `HypothesisEvent` schema (architecture.md §5.3 verbatim): `{ts, type, hypothesis_id, reason, related_audit_ids, tokens_spent, steps_spent}`. `tokens_spent` and `steps_spent` MAY be 0 if the MCP-tool side doesn't have agent budget context (the agent-side recorder in Epic 8 will populate them when it owns the call).
- The pivot count (PRD §4) is `grep -c '"type":"pivot"' cases/<case_id>/audit/hypothesis.jsonl` — make sure that grep works against the emitted JSONL.
- Pivot ID generator: `P-NNN`, zero-padded, resumes across restarts by reading max(P-id) from prior audit entries.
- Context7 hints: minimal external library surface here; reuse the audit_logger and sanitizer dependencies.
- Vocabulary: never "Ralph Wiggum Loop" — describe the behavior as "hypothesis pivot transition." Never "court-admissible."
- Known pitfalls: (1) `to_hypothesis_id` may reference a not-yet-formed hypothesis (the agent records the pivot transition before forming the child); do NOT validate its existence; (2) `abandoning_evidence` carries audit_ids — these must reference real entries in `audit/<backend>.jsonl` files, but verifying that is the agent's responsibility, not this tool's (this tool trusts well-formed input from the agent and only checks the format).
