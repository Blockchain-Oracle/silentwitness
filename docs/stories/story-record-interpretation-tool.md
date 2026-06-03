# Story — `record_interpretation` MCP tool (confidence + justification + falsification-clause)

**ID:** story-record-interpretation-tool
**Epic:** Epic 4 — MCP server skeleton + finding-state tools
**Depends on:** story-fastmcp-server-bootstrap, story-response-envelope, story-record-observation-tool, story-audit-logger
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** SilentWitness investigator agent forming an interpretation over a staged observation
**I want to** call `record_interpretation(observation_id, text, confidence, justification, what_would_change_this_confidence)` and have the server enforce that every interpretation carries an explicit confidence band, a justification, and a falsification clause
**So that** the critic's CHALLENGE pass (Epic 10) has structured fields to evaluate, and the report's confidence-banded findings survive cross-examination

---

## File modification map

Exact files the coding agent creates or modifies:

- `src/silentwitness_mcp/findings/interpretation.py` — NEW — `@mcp.tool() async def record_interpretation(...)` with strict required-field enforcement (≤250 LOC; architecture.md §4.2 row `record_interpretation`)
- `src/silentwitness_common/types.py` — UPDATE — `InterpretationInput`, `InterpretationResult`, `Confidence` types if not already exported from envelope (≤30 LOC delta)
- `tests/integration/test_record_interpretation.py` — NEW — ≥10 BDD scenarios: valid path; each rejection (missing observation, missing required field, invalid confidence); audit emission

The coding agent must NOT modify files outside this map.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a staged observation O-001 exists in findings.json
And   InterpretationInput(observation_id="O-001", text="anomalous parent chain suggests masquerading", confidence=Confidence.HIGH, justification="svchost.exe rarely spawns from cmd.exe; legitimate svchost has services.exe as parent", what_would_change_this_confidence="if pstree shows a legitimate services.exe ancestor, downgrade to LOW")
When  record_interpretation is called
Then  the result is InterpretationResult(success=True, interpretation_id="I-001")
And   the interpretation is appended to findings.json under O-001
And   an audit entry is written to cases/<case_id>/audit/findings.jsonl

Given InterpretationInput referencing observation_id "O-999" which does not exist
When  record_interpretation is called
Then  the result is InterpretationResult(success=False, reason="OBSERVATION_NOT_FOUND")
And   the audit entry for the rejection is still written

Given InterpretationInput with empty justification string
When  record_interpretation is called
Then  the result is InterpretationResult(success=False, reason="MISSING_REQUIRED_FIELD", context={"field": "justification"})

Given InterpretationInput with empty what_would_change_this_confidence string
When  record_interpretation is called
Then  the result is InterpretationResult(success=False, reason="MISSING_REQUIRED_FIELD", context={"field": "what_would_change_this_confidence"})

Given InterpretationInput with confidence=Confidence.HIGH and a justification shorter than 20 chars
When  record_interpretation is called
Then  the result is InterpretationResult(success=False, reason="JUSTIFICATION_TOO_SHORT_FOR_CONFIDENCE")

Given InterpretationInput with text containing an XML role token
When  record_interpretation is called
Then  the sanitizer strips it before the interpretation is persisted
And   a sanitizer JSONL entry is emitted

Given a successful interpretation
When  the same observation_id is interpreted a second time with different text
Then  a NEW interpretation_id is allocated (I-002) and both are retained
And   the audit log shows two distinct entries

Given the test suite runs
When  uv run pytest tests/integration/test_record_interpretation.py
Then  ≥10 tests pass
And   coverage on src/silentwitness_mcp/findings/interpretation.py is ≥90%
```

---

## Shell verification

```bash
# Tests pass with ≥10 cases
uv run pytest tests/integration/test_record_interpretation.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥10

# Coverage ≥90%
uv run coverage run -m pytest tests/integration/test_record_interpretation.py
uv run coverage report --include="src/silentwitness_mcp/findings/interpretation.py" --fail-under=90

# Required-field enforcement is tested
for r in OBSERVATION_NOT_FOUND MISSING_REQUIRED_FIELD JUSTIFICATION_TOO_SHORT_FOR_CONFIDENCE; do
  grep -q "$r" tests/integration/test_record_interpretation.py || { echo "missing test for $r"; exit 1; }
done

# Lint + types
uv run ruff check src/silentwitness_mcp/findings/interpretation.py
uv run mypy --strict src/silentwitness_mcp/findings/interpretation.py

# File-size guard
[ "$(wc -l < src/silentwitness_mcp/findings/interpretation.py)" -le 400 ]
```

---

## Notes for coding agent

- Source of truth: architecture.md §4.2 (`record_interpretation` row: `InterpretationInput(observation_id: str, text: str, confidence: Confidence)`); §5.5 (critic verdict consumes confidence + cited evidence — design implies justification must be present for the critic to evaluate); §8.1 step 23 (interpretation render in the report); `PRD` §2 row "3:00–3:30" (the demo's revised-confidence moment requires this tool).
- The architecture's minimal input is `(observation_id, text, confidence)`. This story EXTENDS that to require `justification` and `what_would_change_this_confidence` — both are structurally required by the critic pipeline (Epic 10) and the report's confidence-banded shape (Epic 11). Document this extension in the module docstring with cross-reference to architecture.md §5.5.
- `InterpretationInput`:
  ```python
  class InterpretationInput(BaseModel):
      observation_id: str
      text: str
      confidence: Confidence                                # LOW | MEDIUM | HIGH
      justification: str                                    # min_length=20
      what_would_change_this_confidence: str                # min_length=10 — the falsification clause
  ```
- `InterpretationResult`:
  ```python
  class InterpretationResult(BaseModel):
      success: bool
      interpretation_id: str | None = None
      reason: InterpretationRejectReason | None = None
      context: dict[str, Any] = Field(default_factory=dict)
  ```
- `InterpretationRejectReason` StrEnum: `OBSERVATION_NOT_FOUND | MISSING_REQUIRED_FIELD | JUSTIFICATION_TOO_SHORT_FOR_CONFIDENCE | INVALID_CONFIDENCE`.
- Pipeline:
  1. Sanitize `text` AND `justification` AND `what_would_change_this_confidence` (story-sanitizer; all three are LLM-bound fields).
  2. Validate `observation_id` exists in `findings.json`. Reject `OBSERVATION_NOT_FOUND` if missing.
  3. Validate required fields are non-empty. Reject `MISSING_REQUIRED_FIELD`.
  4. If `confidence=HIGH`, require `len(justification) >= 50`. If `confidence=MEDIUM`, require `len(justification) >= 30`. Reject `JUSTIFICATION_TOO_SHORT_FOR_CONFIDENCE` otherwise. Rationale: high-confidence claims must carry proportionate justification — this is the architectural floor on overclaim drift.
  5. Allocate `I-NNN` interpretation_id.
  6. Append interpretation to `findings.json` under the observation's record.
  7. Audit JSONL append.
  8. Return wrapped in `ToolResponse[InterpretationResult]`.
- The interpretation does NOT re-verify cited spans — the observation already passed citation + entity gates. Re-verifying would be redundant and wasteful. The architectural defense for interpretations is the critic (Epic 10), which re-reads the cited evidence with fresh context.
- Multiple interpretations per observation are allowed. The report renderer (Epic 11) shows the latest one but retains the history in `findings.json`.
- Context7 hints: `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic"` then query "field_validator min_length conditional validation" — the length-vs-confidence rule needs a `model_validator(mode="after")`.
- Vocabulary: never "court-admissible." Never "Ralph Wiggum Loop." Describe the behavior: "confidence-banded with falsification clause."
- Known pitfalls: (1) the sanitizer must run BEFORE the length checks (sanitization may shrink the strings); (2) `Confidence` enum serialization: use `StrEnum` so JSON gets `"HIGH"` not `<Confidence.HIGH: 'HIGH'>`; (3) appending to findings.json must be atomic (story-atomic-io); (4) the critic (Epic 10) reads the latest interpretation per observation — make sure the append order is stable.
