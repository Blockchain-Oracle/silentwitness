# Story — Citation gate (SHA256 + line-range + span verification)

**ID:** story-citation-gate
**Epic:** Epic 3 — Verification gates
**Depends on:** story-output-normalizer, story-audit-logger, story-common-types
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness MCP server processing a `record_observation` call
**I want to** verify, before persisting, that every cited span in the observation matches the stored normalized tool output by SHA256 and verbatim line-range substring
**So that** an agent cannot record a finding whose cited bytes do not exist or do not say what the agent claims they say — making closed-domain hallucination architecturally impossible

---

## File modification map

Exact files the coding agent creates or modifies:

- `src/silentwitness_mcp/verification/citation_gate.py` — NEW — `verify_citation(cited_span, audit_index) -> CitationResult` pure function; 4-step algorithm per architecture.md §4.5 (≤180 LOC)
- `src/silentwitness_mcp/verification/_types.py` — NEW — `CitedSpan`, `CitationResult`, `CitationRejectReason` Pydantic v2 models (≤80 LOC)
- `tests/unit/verification/test_citation_gate.py` — NEW — ≥15 BDD test cases covering all 5 reject reasons + valid path

The coding agent must NOT modify files outside this map.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given an audit entry sift-aj-20260613-007 exists with a stored blob at audit/blobs/sift-aj-20260613-007.txt
And   the blob contains the verbatim text "svchost.exe at PID 1208" on line 42
And   a CitedSpan(audit_id="sift-aj-20260613-007", sha256_of_normalized_output=<correct hash>, line_start=42, line_end=43, span_text="svchost.exe at PID 1208") is passed
When  verify_citation(span, audit_index) is called
Then  the result is CitationResult(success=True)

Given a CitedSpan whose sha256_of_normalized_output does NOT match the stored blob's recomputed SHA256
When  verify_citation(span, audit_index) is called
Then  the result is CitationResult(success=False, reason="OUTPUT_HASH_MISMATCH")
And   the result includes expected_sha256 and actual_sha256 in structured context

Given a CitedSpan whose span_text is NOT a verbatim substring of the lines[line_start:line_end] slice
When  verify_citation(span, audit_index) is called
Then  the result is CitationResult(success=False, reason="SPAN_NOT_IN_LINES")
And   the result includes the line range that was checked

Given a CitedSpan whose audit_id does not exist in the audit index
When  verify_citation(span, audit_index) is called
Then  the result is CitationResult(success=False, reason="AUDIT_ID_NOT_FOUND")

Given a CitedSpan whose referenced audit entry has a stdout_path that no longer exists on disk
When  verify_citation(span, audit_index) is called
Then  the result is CitationResult(success=False, reason="STDOUT_PATH_MISSING")

Given a CitedSpan whose line_start or line_end exceeds the line count of the stored blob
When  verify_citation(span, audit_index) is called
Then  the result is CitationResult(success=False, reason="LINE_RANGE_OUT_OF_BOUNDS")

Given the citation gate test module is run with coverage
When  uv run coverage run -m pytest tests/unit/verification/test_citation_gate.py
Then  line coverage on src/silentwitness_mcp/verification/citation_gate.py is ≥95%
```

---

## Shell verification

```bash
# Tests pass with ≥15 behavioral test cases
uv run pytest tests/unit/verification/test_citation_gate.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥15

# Coverage floor 95% on this file (per CICD_SPEC §8)
uv run coverage run -m pytest tests/unit/verification/test_citation_gate.py
uv run coverage report --include="src/silentwitness_mcp/verification/citation_gate.py" --fail-under=95

# Lint + types
uv run ruff check src/silentwitness_mcp/verification/citation_gate.py
uv run mypy --strict src/silentwitness_mcp/verification/citation_gate.py

# File-size guard
[ "$(wc -l < src/silentwitness_mcp/verification/citation_gate.py)" -le 400 ]

# Reject-reason enum is exhaustive (all 5 codes referenced)
grep -E "(OUTPUT_HASH_MISMATCH|SPAN_NOT_IN_LINES|AUDIT_ID_NOT_FOUND|STDOUT_PATH_MISSING|LINE_RANGE_OUT_OF_BOUNDS)" src/silentwitness_mcp/verification/_types.py | wc -l
# Must output ≥5

# Each reject reason has at least one test case
for r in OUTPUT_HASH_MISMATCH SPAN_NOT_IN_LINES AUDIT_ID_NOT_FOUND STDOUT_PATH_MISSING LINE_RANGE_OUT_OF_BOUNDS; do
  grep -q "$r" tests/unit/verification/test_citation_gate.py || { echo "missing test for $r"; exit 1; }
done
```

---

## Notes for coding agent

- Source of truth: architecture.md §4.5 (citation gate algorithm — 4 steps + 5 reject reason codes). The "4-step" framing in the brief: (1) load stored output via stdout_path; (2) re-normalize and verify SHA256; (3) slice lines[line_start:line_end] and verify span_text substring; (4) reject with structured reason or pass.
- `CitedSpan` Pydantic model fields verbatim from architecture.md §4.5: `audit_id: str`, `sha256_of_normalized_output: str`, `line_start: int`, `line_end: int`, `span_text: str`.
- `CitationResult` is a tagged union: `CitationResult(success=True, span=CitedSpan)` OR `CitationResult(success=False, reason=CitationRejectReason, context=dict[str, Any])`.
- `CitationRejectReason` is `StrEnum` with exactly the 5 codes above. Future codes get appended; existing codes are stable.
- Use `verification.normalizer.normalize_output` to re-normalize the loaded blob before hashing (story-output-normalizer dependency).
- The audit index is an in-memory dict[str, AuditEntry] built by reading `cases/<case_id>/audit/*.jsonl` at server startup (story-audit-logger provides the loader). Do NOT re-read jsonl files on every citation check — that's an integration concern not this gate's job. This story takes an `audit_index: Mapping[str, AuditEntry]` as injected dependency.
- Performance: the SHA256 recomputation is the hot path. Cache the normalized bytes + hash by audit_id at first verification within a single observation call (multiple cited_spans may reference the same audit_id).
- Function is pure; no I/O state held across calls. File reads are eager and inline so test fixtures can use `tmp_path` and pytest's `monkeypatch`.
- Failure must be observable: every reject path returns the structured context the agent needs to self-correct (the expected vs actual hash, the line range that was checked, etc.). This is what enables the demo's 3:30–4:00 moment.
- Context7 hints: no external library here. Pydantic v2 only. If unsure on Pydantic discriminated unions, run `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic"` then query topic "discriminated unions tagged union".
- Vocabulary: never "court-admissible." The defensibility comes from the structural mechanism, not marketing language.
- Known pitfall: line indexing is 0-based in Python slicing but human "line 42" is 1-based. Architecture.md §4.5 uses `lines[line_start:line_end]` Python-style. Document this in the CitedSpan field docstring so agents emit 0-based ranges.
