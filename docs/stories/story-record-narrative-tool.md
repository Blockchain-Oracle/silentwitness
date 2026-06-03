# Story — `record_narrative` MCP tool (structured narrative draft with required pivot field)

**ID:** story-record-narrative-tool
**Epic:** Epic 4 — MCP server skeleton + finding-state tools
**Depends on:** story-fastmcp-server-bootstrap, story-response-envelope, story-record-observation-tool, story-record-pivot-tool, story-audit-logger
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness investigator agent composing the case narrative as findings accumulate
**I want to** call `record_narrative(section, text, initial_hypothesis, attack_chain, pivots, gaps)` and have the server enforce that every narrative draft carries an initial hypothesis, the attack chain, the pivots that were taken, AND a gaps section
**So that** the report's structured narrative reads as senior-analyst reasoning (form → test → pivot → gaps) rather than a flat findings dump, and the report's Gaps section (architecture.md §5.4) cannot be omitted

---

## File modification map

Exact files the coding agent creates or modifies:

- `src/silentwitness_mcp/findings/narrative.py` — NEW — `@mcp.tool() async def record_narrative(...)` with required structured fields including pivots and gaps (≤300 LOC; architecture.md §4.2 row `record_narrative`)
- `src/silentwitness_common/types.py` — UPDATE — `ReportSection` StrEnum, `NarrativeInput`, `NarrativeResult`, `AttackChainStep` Pydantic models (≤60 LOC delta)
- `tests/integration/test_record_narrative.py` — NEW — ≥10 BDD scenarios: valid narrative; missing pivot field rejected; missing gaps field rejected; invalid section rejected; audit emission; sanitizer integration

The coding agent must NOT modify files outside this map.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given NarrativeInput(section=ReportSection.FINDINGS, text="On 2004-08-19 the wardriving setup was active...", initial_hypothesis="if wardriving, expect promiscuous-mode capture tool + intercepted credentials", attack_chain=[AttackChainStep(observation_id="O-001", interpretation_id="I-001"), ...], pivots=["P-001"], gaps=["could not verify whether ethernet adapter was in promiscuous mode at boot — no driver-level evidence"])
When  record_narrative is called
Then  the result is NarrativeResult(success=True, narrative_id="N-001")
And   findings.json gains the narrative entry under the Findings section
And   an audit entry is written to cases/<case_id>/audit/findings.jsonl

Given NarrativeInput with pivots=[] (empty list)
When  record_narrative is called
Then  the result is NarrativeResult(success=False, reason="MISSING_REQUIRED_FIELD")
And   context.field == "pivots"
And   context.message includes "narrative must enumerate the pivots taken — an empty pivots list with multiple findings is rejected"

Given NarrativeInput with gaps=[] (empty list) AND >3 attack_chain steps
When  record_narrative is called
Then  the result is NarrativeResult(success=False, reason="MISSING_GAPS")
And   context.field == "gaps"

Given NarrativeInput with empty initial_hypothesis
When  record_narrative is called
Then  the result is NarrativeResult(success=False, reason="MISSING_REQUIRED_FIELD")
And   context.field == "initial_hypothesis"

Given NarrativeInput with section=ReportSection.RECOMMENDATIONS (which architecture.md §5.4 reserves for the examiner)
When  record_narrative is called
Then  the result is NarrativeResult(success=False, reason="SECTION_NOT_AGENT_WRITABLE")

Given NarrativeInput referencing observation_id "O-999" in attack_chain that does not exist
When  record_narrative is called
Then  the result is NarrativeResult(success=False, reason="OBSERVATION_NOT_FOUND")

Given NarrativeInput referencing pivot_id "P-999" in pivots that does not exist
When  record_narrative is called
Then  the result is NarrativeResult(success=False, reason="PIVOT_NOT_FOUND")

Given a NarrativeInput.text containing an injection pattern
When  record_narrative is called
Then  sanitizer strips it and emits a sanitizer JSONL entry

Given the test suite runs
When  uv run pytest tests/integration/test_record_narrative.py
Then  ≥10 tests pass
And   coverage on src/silentwitness_mcp/findings/narrative.py is ≥90%
```

---

## Shell verification

```bash
# Tests pass with ≥10 cases
uv run pytest tests/integration/test_record_narrative.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥10

# Coverage ≥90%
uv run coverage run -m pytest tests/integration/test_record_narrative.py
uv run coverage report --include="src/silentwitness_mcp/findings/narrative.py" --fail-under=90

# Reject reasons tested
for r in MISSING_REQUIRED_FIELD MISSING_GAPS SECTION_NOT_AGENT_WRITABLE OBSERVATION_NOT_FOUND PIVOT_NOT_FOUND; do
  grep -q "$r" tests/integration/test_record_narrative.py || { echo "missing test for $r"; exit 1; }
done

# Lint + types
uv run ruff check src/silentwitness_mcp/findings/narrative.py
uv run mypy --strict src/silentwitness_mcp/findings/narrative.py

# File-size guard
[ "$(wc -l < src/silentwitness_mcp/findings/narrative.py)" -le 400 ]

# The required pivot field is enforced (not optional)
grep -q "pivots: list\[str\]" src/silentwitness_common/types.py
```

---

## Notes for coding agent

- Source of truth: architecture.md §4.2 (`record_narrative` row: `NarrativeInput(section: ReportSection, text: str)`); §5.4 (report sections — Findings, Timeline, IOCs, Gaps mandatory; Recommendations examiner-only; Executive Summary written last); §5.3 (pivot transitions logged to hypothesis.jsonl). The brief's "§6.4" reference is a slip — the relevant sections are §5.3 (hypothesis machine) and §5.4 (report structure).
- The architecture's minimal input is `(section, text)`. This story REFINES to `(section, text, initial_hypothesis, attack_chain, pivots, gaps)` because the narrative must encode the senior-analyst reasoning shape (form → dispatch → confirm-or-pivot → gaps). Document this extension in the module docstring with cross-reference to architecture.md §5.3 + §5.4.
- `ReportSection` StrEnum maps to architecture.md §5.4 sections:
  ```python
  class ReportSection(StrEnum):
      EXECUTIVE_SUMMARY = "executive_summary"      # agent draft; written last
      ENGAGEMENT_OVERVIEW = "engagement_overview"
      METHODOLOGY = "methodology"
      FINDINGS = "findings"                        # primary target
      TIMELINE = "timeline"
      IOCS = "iocs"
      RECOMMENDATIONS = "recommendations"          # EXAMINER ONLY — not agent-writable
      GAPS = "gaps"                                # mandatory section
      APPENDIX_AUDIT = "appendix_audit"            # rendered, not agent-writable
  ```
  The tool rejects `RECOMMENDATIONS` and `APPENDIX_AUDIT` with reason `SECTION_NOT_AGENT_WRITABLE`.
- `NarrativeInput`:
  ```python
  class NarrativeInput(BaseModel):
      section: ReportSection
      text: str                                # the prose body
      initial_hypothesis: str                  # min_length=20
      attack_chain: list[AttackChainStep]      # min_length=1
      pivots: list[str]                        # pivot_ids referenced; required
      gaps: list[str]                          # min_length=1 if attack_chain has >3 steps
  ```
- `AttackChainStep`:
  ```python
  class AttackChainStep(BaseModel):
      observation_id: str
      interpretation_id: str | None = None     # may be None if observation has no interpretation yet
      note: str | None = None
  ```
- `NarrativeResult`:
  ```python
  class NarrativeResult(BaseModel):
      success: bool
      narrative_id: str | None = None
      reason: NarrativeRejectReason | None = None
      context: dict[str, Any] = Field(default_factory=dict)
  ```
- `NarrativeRejectReason` StrEnum: `MISSING_REQUIRED_FIELD | MISSING_GAPS | SECTION_NOT_AGENT_WRITABLE | OBSERVATION_NOT_FOUND | PIVOT_NOT_FOUND | INVALID_SECTION`.
- The "required pivot field" framing from the brief: `pivots` is a structurally-required field. If the case had no pivots (a single-hypothesis run), the agent should pass `pivots=[]` AND `attack_chain` with ≤3 steps; the validator only requires pivots when the attack chain is long enough to imply hypothesis exploration. This avoids forcing fake pivots for trivial cases.
- Pipeline:
  1. Sanitize `text`, `initial_hypothesis`, every `gaps[]` entry, every `attack_chain[].note` (story-sanitizer).
  2. Validate `section` is agent-writable. Reject `SECTION_NOT_AGENT_WRITABLE` for RECOMMENDATIONS and APPENDIX_AUDIT.
  3. Validate `initial_hypothesis` non-empty post-sanitize. Reject `MISSING_REQUIRED_FIELD`.
  4. Validate `attack_chain` non-empty.
  5. Validate every `observation_id` in `attack_chain` exists in `findings.json`. Reject `OBSERVATION_NOT_FOUND` with the offending id.
  6. Validate every `pivot_id` in `pivots` exists in `audit/hypothesis.jsonl`. Reject `PIVOT_NOT_FOUND`.
  7. If `len(attack_chain) > 3`, require `len(gaps) >= 1`. Reject `MISSING_GAPS` otherwise — the architectural floor on epistemic honesty (architecture.md §5.4 final paragraph on Gaps).
  8. Allocate `N-NNN` narrative_id.
  9. Append to `findings.json` under the section.
  10. Audit JSONL append.
  11. Return `ToolResponse[NarrativeResult]`.
- Multiple narratives per section are allowed; the report renderer (Epic 11) shows them in append order.
- Context7 hints: `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic"` then query "model_validator conditional length check" — the `if len(attack_chain) > 3: require gaps` rule needs `model_validator(mode="after")`.
- Vocabulary: never "Ralph Wiggum Loop." Never "court-admissible." Describe the structure: "form → dispatch → confirm-or-pivot → gaps."
- Known pitfalls: (1) `RECOMMENDATIONS` rejection is critical — architecture.md §5.4 explicitly reserves this section for the examiner; the agent must not be able to draft recommendations; (2) the gaps requirement is conditional on attack chain length — DO NOT enforce gaps on every narrative or trivial cases break; (3) the narrative's `text` is the prose body of the section, not a substitute for the structured fields — both are persisted.
