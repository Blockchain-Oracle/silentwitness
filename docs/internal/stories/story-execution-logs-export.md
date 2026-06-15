# Story — Example execution logs export (`docs/EXAMPLE_EXECUTION_LOGS/`; Rules deliverable #8; synthetic tiny case readable without running the system)

**ID:** story-execution-logs-export
**Epic:** Epic 16 — Documentation polish + submission
**Depends on:** story-audit-logger, story-evidence-registry, story-hypothesis-types, story-record-observation-tool, story-critic-agent, story-hmac-ledger, story-report-template, story-common-types
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent assembling the Devpost Rules §4 deliverable set
**I want to** ship `docs/EXAMPLE_EXECUTION_LOGS/` — a tiny synthetic case (3–5 tool calls; all filenames suffixed `EXAMPLE`) containing the full per-MCP-backend `audit/*.jsonl` files, `report.md`, `evidence.json` registry, hypothesis-event log, critic verdict log, and an index `README.md` — so a judge browsing the Devpost gallery preview can READ the audit trail end-to-end without cloning the repo, without installing SIFT, without invoking the LLM
**So that** PRD §10 deliverable 8 ("Agent execution logs") is satisfied as a static, hash-anchored artifact judges can click through in 90 seconds; every audit-trail claim in PRD §2 (the 4:50–5:00 verify-link demo arc) has a concrete reference judges can point to; and the rules §4 deliverables checklist passes a teammate audit (epics.md Epic 16 DoD; PRD §14 vocabulary discipline; FR5 JSONL audit per tool call; FR6 Markdown report with FOR508 sections + Gaps + Appendix-Audit; judging criterion Audit Trail Quality + Usability).

---

## File modification map

- `docs/EXAMPLE_EXECUTION_LOGS/README.md` — NEW — index document, ≤200 lines. Section order:
  1. `# Example execution logs — SilentWitness case-example-001 (synthetic)` — H1 + 2-sentence framing: this is a static synthetic case, all filenames are suffixed `EXAMPLE` to make the simulation status obvious to the reader. It exists to make PRD §10 deliverable 8 readable without running the system. Cite the PRD §14 §14 carve-out (the `EXAMPLE` suffix is the discriminator that lets this story exist alongside the no-mock/no-fake gate per CICD_SPEC §14).
  2. `## What this directory contains` — bullet list, one line per file with what it demonstrates:
     - `case-example-001_EXAMPLE/.silentwitness/case.toml` — case metadata
     - `case-example-001_EXAMPLE/evidence.json` — evidence registry; 1 evidence-registration event for a synthetic 4-byte sample binary
     - `case-example-001_EXAMPLE/audit/memory.jsonl` — 1 vol3 plugin call
     - `case-example-001_EXAMPLE/audit/disk.jsonl` — 1 MFT parse call
     - `case-example-001_EXAMPLE/audit/log.jsonl` — 1 EVTX parse call
     - `case-example-001_EXAMPLE/audit/findings.jsonl` — 1 `record_observation` event (APPROVED) + the envelope showing citation + entity gates passed
     - `case-example-001_EXAMPLE/audit/hypothesis.jsonl` — 5 events: form → dispatch → confirm → PIVOT → confirm
     - `case-example-001_EXAMPLE/audit/critic.jsonl` — 1 critic CHALLENGE event + 1 verdict
     - `case-example-001_EXAMPLE/findings.json` — final findings registry (1 finding APPROVED)
     - `case-example-001_EXAMPLE/report.md` — rendered Markdown report with `[verify:audit_id]` links
     - `case-example-001_EXAMPLE/ledger.jsonl` — HMAC-signed approval ledger; 1 APPROVED entry
  3. `## How to read this` — short narrative: open `report.md` first, click any `[verify:sift-example-...]` link mentally (the link IDs anchor into `audit/*.jsonl`), then read the corresponding JSONL row. This mirrors the live demo arc at 4:50–5:00.
  4. `## What the synthetic case demonstrates` — bullets, each tied to a PRD requirement:
     - FR5 (JSONL audit per tool call): 3 tool calls visible across `audit/memory.jsonl`, `audit/disk.jsonl`, `audit/log.jsonl`.
     - FR6 (Markdown report with Gaps + Appendix-Audit): `report.md` includes both sections explicitly.
     - FR7 (≥1 self-correction in demo): the hypothesis log shows 1 PIVOT transition with `reason="vol3 symbol-table mismatch; rebuilt"` (mirrors the PRD §2 3:00–3:30 demo moment).
     - Critic CHALLENGE: `audit/critic.jsonl` shows 1 verdict of `CHALLENGE` followed by 1 verdict of `APPROVED` after corroboration (mirrors PRD §2 4:00–4:30).
     - Entity gate pass: `audit/findings.jsonl` shows a `record_observation` envelope where the citation + entity gates passed (status=APPROVED). A second entry would normally show REJECTED — for brevity, this example case only includes the passing case; the rejected-case is demonstrated in the demo video and in the integration tests.
     - HMAC ledger: `ledger.jsonl` shows the SHA256 + PBKDF2-iter count + HMAC over the finding's substantive text.
  5. `## Synthetic disclosure` — verbatim 3-sentence paragraph:
     > This case is synthetic and is intended solely to make the audit trail readable without running the system. The evidence file is a 4-byte placeholder; the tool outputs are hand-crafted to demonstrate the JSONL row shape, not real Volatility / EZ Tools / EVTX output. Every filename is suffixed `_EXAMPLE` so the simulation status is obvious to the reader; nothing in this directory should be interpreted as a real investigation result.
  6. `## Source` — pointer to `scripts/build_example_execution_logs.py` (below) + the deterministic regeneration recipe (`uv run python scripts/build_example_execution_logs.py --out docs/EXAMPLE_EXECUTION_LOGS/`).
- `docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/.silentwitness/case.toml` — NEW — minimal case metadata (`case_id`, `examiner="example-sansforensics"`, `created_at` fixed deterministic ISO-Z timestamp).
- `docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/evidence.json` — NEW — 1 entry: `evidence_id="ev-example-001"`, `path="/evidence/sample_EXAMPLE.bin"`, `sha256=<4-byte-stable-sha256>`, `size_bytes=4`, `registered_at=<fixed ISO-Z>` per `story-evidence-registry` schema.
- `docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/audit/memory.jsonl` — NEW — 1 line: a synthetic `vol_pslist` envelope per `story-response-envelope` shape (audit_id `"sift-example-20260613-001"`, tool_name `"vol_pslist"`, result_sha256 of a stable 32-line stdout, elapsed_ms 4200, status `"OK"`).
- `docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/audit/disk.jsonl` — NEW — 1 line: synthetic `parse_mft` envelope (audit_id `"sift-example-20260613-002"`).
- `docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/audit/log.jsonl` — NEW — 1 line: synthetic `parse_evtx` envelope (audit_id `"sift-example-20260613-003"`).
- `docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/audit/findings.jsonl` — NEW — 1 line: `record_observation` envelope showing citation gate match + entity gate match (status APPROVED; cites `sift-example-20260613-001`).
- `docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/audit/hypothesis.jsonl` — NEW — 5 lines: form (`H-001`), dispatch memory specialist, confirm via `vol_pslist`, PIVOT with `reason="vol3 symbol-table mismatch; rebuilt"`, confirm again. Schema per `story-hypothesis-types`.
- `docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/audit/critic.jsonl` — NEW — 2 lines: 1 verdict `CHALLENGE` with `reason="interpretation requires intercepted-traffic evidence"`; 1 verdict `APPROVED` after corroboration. Schema per `story-critic-agent`.
- `docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/findings.json` — NEW — 1 finding `F-example-001` with status `APPROVED`, cited_audit_ids `["sift-example-20260613-001"]`, observation + interpretation + caveats + MITRE tag.
- `docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/report.md` — NEW — rendered Markdown report per `story-report-template`: YAML frontmatter, Executive Summary, Findings (with `[verify:sift-example-20260613-001]` link), Gaps (≥1 bullet), Appendix-Audit (table showing the 3 tool-call rows with SHA256 + elapsed_ms). ≤200 lines.
- `docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/ledger.jsonl` — NEW — 1 HMAC ledger entry: `ledger_id`, `finding_id=F-example-001`, `pbkdf2_iter=600000`, `hmac_sha256=<deterministic from example key>`, `signed_at=<fixed ISO-Z>`. The HMAC key for the example case is the literal string `"EXAMPLE-not-a-real-secret-EXAMPLE"` — documented in the index README + the ledger entry's `notes` field so no reader confuses it for a real ledger.
- `scripts/build_example_execution_logs.py` — NEW — ≤300 LOC Python script that deterministically regenerates the entire directory tree. Inputs: `--out <dir>`, `--seed <int>` (default 0). Outputs: every file above. Uses fixed timestamps + fixed SHA256s from a small fixture so re-running produces byte-identical output (verifiable via `git diff --exit-code` after regeneration). Imports `silentwitness_common.types` to build the envelopes properly (no hand-crafted JSON — uses real models with `model_dump_json`); this keeps the example logs schema-locked to the production schema, so a schema change forces an update to the example logs (intentional drift-detection).
- `tests/integration/test_example_execution_logs.py` — NEW — ≥7 BDD scenarios:
  - every JSONL file under `case-example-001_EXAMPLE/audit/` parses as well-formed JSON line by line (no syntax errors);
  - `audit/hypothesis.jsonl` contains exactly 5 events;
  - `audit/hypothesis.jsonl` contains exactly 1 event with `transition=="pivot"` (FR7 self-correction visible);
  - `audit/critic.jsonl` contains exactly 1 verdict `"CHALLENGE"` and ≥1 verdict `"APPROVED"`;
  - `audit/findings.jsonl` contains exactly 1 envelope with `status=="APPROVED"` and the entity_gate match list is non-empty;
  - `report.md` contains exactly 1 `## Gaps` section and exactly 1 `## Appendix-Audit` section (FR6);
  - `report.md` contains at least 1 `[verify:sift-example-` link;
  - re-running `scripts/build_example_execution_logs.py --out <tmpdir>` produces byte-identical output to the committed `docs/EXAMPLE_EXECUTION_LOGS/` tree (deterministic regeneration check).

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/audit/hypothesis.jsonl is committed
When  `wc -l docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/audit/hypothesis.jsonl` runs
Then  the integer is 5

Given docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/audit/hypothesis.jsonl is committed
When  `jq -c 'select(.transition == "pivot")' docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/audit/hypothesis.jsonl | wc -l` runs
Then  the integer is 1

Given docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/audit/critic.jsonl is committed
When  `jq -c 'select(.verdict == "CHALLENGE")' docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/audit/critic.jsonl | wc -l` runs
Then  the integer is 1

Given docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/audit/findings.jsonl is committed
When  `jq -c 'select(.status == "APPROVED")' docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/audit/findings.jsonl | wc -l` runs
Then  the integer is ≥ 1

Given docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/report.md is committed
When  `grep -c '^## Gaps' docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/report.md` runs
Then  the integer is 1
And   `grep -c '^## Appendix-Audit' docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/report.md` returns 1

Given docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/report.md is committed
When  `grep -cE '\[verify:sift-example-' docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/report.md` runs
Then  the integer is ≥ 1

Given all _EXAMPLE filenames are committed
When  `find docs/EXAMPLE_EXECUTION_LOGS/ -type f ! -name 'README.md' | grep -vE '(_EXAMPLE|EXAMPLE)' | wc -l` runs
Then  the integer is 0 (every committed file path contains the EXAMPLE token; the index README is the documented carve-out)

Given `uv run python scripts/build_example_execution_logs.py --out /tmp/sw-ex-test` runs
When  the output is compared with `git diff --no-index --exit-code docs/EXAMPLE_EXECUTION_LOGS/ /tmp/sw-ex-test/`
Then  exit code is 0 (deterministic regeneration)

Given tests/integration/test_example_execution_logs.py exists
When  `uv run pytest tests/integration/test_example_execution_logs.py -v` runs
Then  exit code is 0
And   ≥7 tests pass
```

---

## Shell verification

```bash
# Tests
uv run pytest tests/integration/test_example_execution_logs.py -v

# Strict typing
uv run mypy --strict scripts/build_example_execution_logs.py

# Lint
uv run ruff check scripts/build_example_execution_logs.py

# §14 vocab gate clean on the index README + the report.md
grep -iE '(court-admissible|Ralph Wiggum|autonomous SOC|replaces L1|eliminates hallucinations)' \
   docs/EXAMPLE_EXECUTION_LOGS/README.md \
   docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/report.md \
   && exit 1 || true

# §14 no-mock/no-fake gate carve-out check
# (the _EXAMPLE suffix is the documented carve-out; CICD_SPEC §14 allows this directory)
git ls-files docs/EXAMPLE_EXECUTION_LOGS/ | grep -vE '(README\.md$|_EXAMPLE)' && exit 1 || true

# Deterministic regeneration check
uv run python scripts/build_example_execution_logs.py --out /tmp/sw-ex-test
diff -r docs/EXAMPLE_EXECUTION_LOGS/ /tmp/sw-ex-test/
```

---

## Notes for coding agent

- Reference: `docs/PRD.md` §10 deliverable 8 ("Agent execution logs") — "sample case shipped at `examples/case-hacking-case-001/` so judges can read logs without running the system" — note: this story moves the path to `docs/EXAMPLE_EXECUTION_LOGS/` per the slug name in this directive; the rationale is identical; `docs/PRD.md` §2 (the demo arc this static case mirrors) + §5 FR5/FR6/FR7; `docs/architecture.md` §3 + §5 (audit-id format + envelope shape); `docs/CICD_SPEC.md` §14 (no-mock/no-fake gate; the `_EXAMPLE` filename suffix is the documented carve-out — every file in this directory MUST be suffixed `_EXAMPLE` or be the index `README.md`); `docs/epics.md` Epic 16 DoD.
- **`_EXAMPLE` suffix is non-negotiable.** Every file path in `docs/EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/` carries the suffix in the directory name OR in the filename. This is the §14 carve-out — the CICD gate's grep `(_EXAMPLE|EXAMPLE)` exempts these files from the no-mock/no-fake rule. If you add a file without the suffix, the gate fails. The index `README.md` is the documented exception (it explains the carve-out).
- **Determinism is the keystone.** The file tree is generated by `scripts/build_example_execution_logs.py` using fixed timestamps + fixed SHAs + fixed audit_ids. Re-running the script must produce byte-identical output — the integration test asserts this via `diff -r`. Random anything (timestamps, UUIDs, hashes) defeats this.
- **Schema-lock via real models.** The script uses `silentwitness_common.types` to build the envelopes via `model_dump_json` — NOT hand-written JSON strings. If the production schema changes (e.g., a new field added to the audit envelope), the example logs are regenerated, and any schema-incompatible drift surfaces in the deterministic-regeneration test. This is the same drift-detection pattern used in story-readme-polish + story-dataset-doc.
- **3-5 tool calls discipline:** the user story says 3-5 tool calls; this spec ships 3 (memory + disk + log). Adding more makes the audit-trail story harder to scan in 90 seconds. If a judge wants more, they can run the actual harness (`docs/TRY_IT_OUT.md`).
- **Sequence:** form → dispatch → confirm → PIVOT → confirm mirrors the PRD §2 3:00–3:30 demo arc (vol3 symbol-table mismatch → rebuild → retry). The PIVOT row's `reason` field carries verbatim text `"vol3 symbol-table mismatch; rebuilt"` to make the connection explicit to a reader cross-referencing the demo video.
- **HMAC key disclosure:** the example ledger uses a literal "EXAMPLE-not-a-real-secret-EXAMPLE" key, documented in the ledger entry's `notes` field AND in the index README. This is the only way to ship a deterministic HMAC value (a real ledger derives the key from the examiner password via PBKDF2; the example case stubs the key for reproducibility).
- **Report shape ties to story-report-template:** YAML frontmatter (case_id, examiner, model, generated_at fixed timestamp), `## Executive Summary` (2-sentence narrative), `## Findings` (1 finding with verify link), `## Gaps` (1 bullet — epistemic honesty), `## Appendix-Audit` (3-row table). Render via the actual `report.template` module, not a hand-written Markdown file, to lock the shape against drift.
- **Index README's job is navigation, not content.** ≤200 lines. Bullet-list of files + 5-sentence narrative + the verbatim synthetic disclosure paragraph. Anything longer belongs in `docs/architecture.md` §5.
- Vocabulary discipline (PRD §14): never "court-admissible"; never "autonomous SOC"; never "Ralph Wiggum Loop". The `report.md` example MUST follow the same vocab as the production report renderer (story-report-template + story-report-writer). The CI gate `grep -iE '(court-admissible|...)' docs/EXAMPLE_EXECUTION_LOGS/...` catches drift.
- Library docs to consult via Context7 BEFORE coding:
  - `pydantic` topic `model_dump_json + by_alias + exclude_none + indent` (for deterministic JSON output the script must use `indent=None` and sorted keys via `sort_keys=True` is NOT the Pydantic API — use `model_dump_json()` which is already deterministic by Pydantic v2 contract).
- Known pitfalls:
  1. Atomic-rename semantics (story-atomic-io) are NOT used in the build script — the script writes directly because the regeneration is one-shot, not concurrent. Document this in the script docstring.
  2. JSONL trailing newline discipline: every JSONL file MUST end with a newline; the deterministic-regeneration test catches trailing-newline drift if `model_dump_json` does not append one (Pydantic v2 does not; the script appends explicitly).
  3. The 4-byte sample binary is `b"\x00\x00\x00\x00"`; its SHA256 is fixed (`df3f619804a92fdb4057192dc43dd748ea778adc52bc498ce80524c014b81119`). The `evidence.json` references this exact value; the `vol_pslist` example envelope cites this SHA in `result_sha256` as the audit-trail hash example (different shape: it's actually the hash of the tool's stdout, not the evidence — be careful not to confuse the two; the script uses different fixed hashes for each role).
  4. Hardcoded timestamps must be in UTC ISO-8601 with `Z` suffix — match the format used by `story-audit-logger`.
