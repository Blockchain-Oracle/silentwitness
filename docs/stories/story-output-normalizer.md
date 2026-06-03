# Story — Output normalizer (deterministic SHA256 hashing surface)

**ID:** story-output-normalizer
**Epic:** Epic 3 — Verification gates
**Depends on:** story-common-types, story-atomic-io
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** SilentWitness MCP server
**I want to** normalize raw forensic tool stdout to a byte-stable canonical form before hashing
**So that** the citation gate's SHA256 comparison is reproducible across re-runs of the same tool against the same evidence, and cited spans survive timestamp/whitespace/path-separator drift

---

## File modification map

Exact files the coding agent creates or modifies:

- `src/silentwitness_mcp/verification/__init__.py` — NEW — package marker, exports `normalize_output`
- `src/silentwitness_mcp/verification/normalizer.py` — NEW — pure functions implementing the 6-rule normalization pipeline (≤200 LOC; architecture.md §4.6)
- `src/silentwitness_mcp/verification/_patterns.py` — NEW — per-tool regex catalog (banner patterns, metadata-line patterns) loaded once at import (≤120 LOC)
- `tests/unit/verification/__init__.py` — NEW — package marker
- `tests/unit/verification/test_normalizer.py` — NEW — exhaustive rule-by-rule coverage (≥18 test cases minimum; one per normalization rule × valid/invalid + edge cases)

The coding agent must NOT modify files outside this map.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a raw Volatility 3 stdout sample containing the "Volatility 3 Framework 2.x" banner
When  normalize_output(raw, tool="vol_pslist") is called
Then  the returned bytes contain no banner line matching ^Volatility 3 Framework
And   re-invoking normalize_output(normalize_output(raw, ...), ...) returns identical bytes (idempotent)

Given a raw EvtxECmd CSV stdout containing two ISO-8601 metadata wall-clock timestamps
When  normalize_output(raw, tool="parse_evtx") is called
Then  metadata timestamps are replaced with the literal token <TS>
And   evidence-content timestamps (inside CSV rows) are preserved verbatim

Given a raw output containing Windows-style line endings (\r\n) and trailing whitespace
When  normalize_output(raw, tool="any") is called
Then  every line ends with a single \n
And   no line has trailing whitespace

Given a raw output containing ANSI escape sequences (\x1B[31m...)
When  normalize_output(raw, tool="any") is called
Then  zero ANSI escape sequences remain (regex \x1B\[[0-9;]*[mK] matches nothing)

Given two byte-identical raw outputs from successive runs of the same Vol3 plugin
When  hashlib.sha256(normalize_output(run_a)).hexdigest() and the same for run_b are compared
Then  the two hashes are identical (byte-stability test)

Given a raw output containing backslash paths inside a Vol3 diagnostic line
When  normalize_output(raw, tool="vol_pslist") is called
Then  diagnostic-line backslashes are converted to forward slashes
And   evidence-content backslashes (e.g. C:\Program Files\Ethereal\) are preserved verbatim

Given the normalizer test module is run with coverage
When  uv run coverage run -m pytest tests/unit/verification/test_normalizer.py
Then  line coverage on src/silentwitness_mcp/verification/normalizer.py is ≥95%
```

---

## Shell verification

```bash
# Tests pass with ≥18 behavioral test cases
uv run pytest tests/unit/verification/test_normalizer.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥18

# Coverage floor on the file under test
uv run coverage run -m pytest tests/unit/verification/test_normalizer.py
uv run coverage report --include="src/silentwitness_mcp/verification/normalizer.py" --fail-under=95

# Lint + types
uv run ruff check src/silentwitness_mcp/verification/normalizer.py
uv run ruff format --check src/silentwitness_mcp/verification/normalizer.py
uv run mypy --strict src/silentwitness_mcp/verification/normalizer.py

# File-size guard
[ "$(wc -l < src/silentwitness_mcp/verification/normalizer.py)" -le 400 ]

# No banned patterns
! grep -E "(print\(|os\.system|eval\(|exec\()" src/silentwitness_mcp/verification/normalizer.py
```

---

## Notes for coding agent

- Source of truth: architecture.md §4.6 (rules applied in order); also referenced in §5.4 "last paragraph" framing of normalization preceding hash.
- The 6 rules in strict order: (1) strip tool version banners; (2) strip wall-clock timestamps in metadata-only lines; (3) collapse whitespace; (4) normalize path separators in diagnostic lines only; (5) strip ANSI escape sequences; (6) normalize line endings (\r\n → \n).
- The "metadata-only line" allowlist is per-tool — keep the regex catalog in `_patterns.py` as a typed dict `TOOL_PATTERNS: dict[str, ToolPatternSet]` with explicit keys: `banner`, `metadata_timestamp_lines`, `diagnostic_lines`.
- Idempotency property: `normalize(normalize(x)) == normalize(x)`. Add an explicit test; it catches accidental ordering bugs.
- Determinism: function is pure, no time / random / locale dependencies.
- Do NOT strip timestamps from evidence content (CSV rows from EvtxECmd contain real event timestamps that ARE the evidence). The per-tool metadata allowlist is the discriminator.
- The original (pre-normalized) output is NOT retained (architecture.md §4.6 commitment: "what the model saw is what the gate verifies").
- The function signature: `def normalize_output(raw: bytes, tool: str) -> bytes`. Returns bytes, not str, so callers can SHA256 directly.
- Reuse `re.compile` at module level — patterns compile once.
- Context7 hints: this story has no external library beyond stdlib `re`. No Context7 query needed.
- Vocabulary: never "court-admissible" — say "defensible audit trail" or omit. Never "Ralph Wiggum Loop."
