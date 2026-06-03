# Story — Property-based tests for the verification gates

**ID:** story-gates-property-tests
**Epic:** Epic 3 — Verification gates
**Depends on:** story-output-normalizer, story-citation-gate, story-entity-gate, story-sanitizer
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As the** SilentWitness CI pipeline
**I want to** run Hypothesis property-based tests against citation_gate, entity_gate, and sanitizer that randomize inputs and assert architectural invariants hold for every input
**So that** edge cases the example-based tests miss (random Unicode, malformed audit IDs, adversarial entity overlap, normalization collisions) are caught before they reach a judge's demo run

---

## File modification map

Exact files the coding agent creates or modifies:

- `tests/property/__init__.py` — NEW — package marker
- `tests/property/test_gates.py` — NEW — Hypothesis property tests across all three gates + the normalizer (≤400 LOC; ≥12 distinct property tests)
- `tests/property/strategies.py` — NEW — reusable Hypothesis strategies: `audit_entry_strategy`, `cited_span_strategy`, `dfir_entity_strategy`, `injection_payload_strategy`, `normalizable_output_strategy` (≤250 LOC)
- `tests/conftest.py` — UPDATE — register Hypothesis profiles: `dev` (50 examples), `ci` (500 examples), `slow` (5000 examples); per CICD_SPEC §4.1 `property-tests` job

The coding agent must NOT modify files outside this map.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a randomly generated valid observation (cited spans constructed from real fixture audit entries)
When  citation_gate + entity_gate are applied
Then  the result is ACCEPTED for every example Hypothesis generates
And   no shrinkage produces a failing accept→reject inversion

Given a randomly generated invalid observation (text containing entities NOT in any cited span)
When  entity_gate is applied
Then  the result is REJECTED with reason HALLUCINATED_ENTITIES for every example
And   the hallucinated list is non-empty

Given a randomly generated CitedSpan whose sha256 is randomized
When  citation_gate verifies it against the deterministic blob index
Then  the result is REJECTED with reason OUTPUT_HASH_MISMATCH (probability 1 - 2^-256)

Given a Hypothesis-generated raw output bytes string
When  normalize_output(raw) is called twice
Then  the second call returns identical bytes (idempotency property)

Given any pair of byte-distinct raw outputs that differ ONLY in stripped whitespace / banners / timestamps
When  normalize_output is applied to both
Then  the SHA256 of the normalized outputs is identical (collision absence within the equivalence class)

Given a Hypothesis-generated string containing exactly one of: <system>, <|im_start|>, U+202E, U+200B, [INST]
When  sanitize is applied
Then  the strip_count is ≥1
And   the wrapped_text does NOT contain the literal injection token

Given a Hypothesis-generated DFIR entity (IPv4, SHA256, registry key, Windows path, etc.)
When  it is placed verbatim into both observation_text and a cited_span's span_text
Then  entity_gate accepts it (hallucinated list is empty)

Given a Hypothesis-generated DFIR entity placed in observation_text but NOT in any cited span
When  entity_gate is applied
Then  the entity appears in the hallucinated list (no false negatives)

Given a Hypothesis-generated audit_id string conforming to the sift-<examiner>-<YYYYMMDD>-<NNN> format
When  the audit index is queried
Then  no false-positive AUDIT_ID_NOT_FOUND rejections occur for IDs that ARE in the index

Given any sanitized output
When  the regex catalog of injection patterns is applied to the wrapped_text
Then  zero matches remain (sanitizer is a fixpoint under reapplication)

Given the property-test module is run under the `ci` profile (500 examples per test)
When  uv run pytest tests/property/test_gates.py --hypothesis-profile=ci
Then  all property tests pass in <5 minutes
And   exit code is 0
```

---

## Shell verification

```bash
# Dev profile runs fast
HYPOTHESIS_PROFILE=dev uv run pytest tests/property/test_gates.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥12

# CI profile runs the 500-example floor
HYPOTHESIS_PROFILE=ci uv run pytest tests/property/test_gates.py
# Must exit 0

# Lint + types on test modules (looser than src but still typed)
uv run ruff check tests/property/
uv run mypy --strict tests/property/strategies.py

# File-size guard on test files (still bounded)
[ "$(wc -l < tests/property/test_gates.py)" -le 400 ]
[ "$(wc -l < tests/property/strategies.py)" -le 400 ]

# Combined coverage across verification/ remains ≥95% with property tests included
uv run coverage run -m pytest tests/unit/verification/ tests/property/test_gates.py
uv run coverage report --include="src/silentwitness_mcp/verification/*" --fail-under=95
```

---

## Notes for coding agent

- Source of truth: architecture.md §14 (CI requirements — "Property tests on the verification gates via hypothesis. Coverage of the gates includes adversarial-input property tests (random Unicode, random injection patterns, malformed audit IDs)"); CICD_SPEC §4.1 (`property-tests` job); CICD_SPEC §8 (verification floor 95%).
- This is the closing story of Epic 3 — its purpose is to ratify that the four upstream stories meet the architectural floor.
- Hypothesis strategies catalog:
  - `dfir_entity_strategy()` returns one of: IPv4 (`hypothesis.strategies.ip_addresses(v=4)`), IPv6, MD5/SHA1/SHA256 hex, Windows path (composite), POSIX path (composite), registry key (composite), domain account, email.
  - `audit_entry_strategy()` builds a fake `AuditEntry` Pydantic model with a tmp-path-backed blob and a recomputed SHA256.
  - `cited_span_strategy(audit_entry)` derives a valid CitedSpan from an audit entry by picking a random line range and slicing span_text from it.
  - `injection_payload_strategy()` emits random combinations of XML role tokens, chat-format tokens, RLO/ZWSP/tag chars, and pattern-catalog phrases.
  - `normalizable_output_strategy()` emits raw bytes with a random subset of: ANSI escapes, CRLF endings, banner lines, mixed-case path separators, trailing whitespace.
- The "valid input always passes" / "invalid input always rejects" pair is the strongest assertion this story makes. Both must be machine-verifiable across 500+ examples (CI profile).
- Idempotency: `normalize(normalize(x)) == normalize(x)` AND `sanitize(sanitize(x)) == sanitize(x)` (sanitizer fixpoint). Add both as explicit Hypothesis properties.
- No-collision: distinct semantic outputs must produce distinct normalized SHA256. Frame this as: pick a random Vol3 row and a CSV row that DIFFER only in a content field; assert their normalized hashes differ.
- The `tests/conftest.py` profile registration: `settings.register_profile("dev", max_examples=50, deadline=None)`, `settings.register_profile("ci", max_examples=500, deadline=None)`, `settings.register_profile("slow", max_examples=5000, deadline=None)`. Pull profile from `HYPOTHESIS_PROFILE` env var with `settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))`.
- Performance: the entity gate has spaCy in the hot path. Use a module-level cached `_nlp` so 500 examples don't pay 500× the model-load cost.
- Use `hypothesis.strategies.composite` for the `cited_span_strategy` — the line range and span_text need correlated generation.
- Context7 hint: `mcp__plugin_context7_context7__resolve-library-id libraryName="hypothesis"`, then query topic "composite strategies stateful" for the audit-index ↔ cited-span correlation pattern.
- Vocabulary: never "court-admissible." Property tests are about architectural invariants; that's the language.
- Known pitfalls: (1) Hypothesis shrinking on Unicode strings can spend minutes — use `max_size` bounds on the text strategies; (2) the SHA256 randomization test relies on collision-resistance probability not equality — phrase the assertion as "P(collision) is negligible" via `assume()`; (3) spaCy can be non-deterministic across versions — pin the model in pyproject.toml so property tests stay reproducible.
