# Story — Accuracy report writeup (`docs/ACCURACY_REPORT.md` — deliverable #6)

**ID:** story-accuracy-report-writeup
**Epic:** Epic 16 — Documentation polish + submission
**Depends on:** story-dataset-manifests (Epic 14), story-baseline-runner (Epic 14), story-silentwitness-runner (Epic 14), story-scorer (Epic 14), story-delta-report (Epic 14), story-gates-property-tests (Epic 3 — sanitizer test corpus)
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** judge scoring the "IR Accuracy" criterion (PRD §8 row 2 — equally weighted with five others, with Autonomous Execution Quality as tiebreaker)
**I want to** read `docs/ACCURACY_REPORT.md` and find the methodology, the baseline establishment, per-dataset measured Δ vs vanilla Protocol SIFT, an honestly-flagged list of false positives + misses + residual hallucinations the system caught AND a separate list of residual hallucinations the system did NOT catch, the sanitizer test-corpus results, and the threat-model summary — all in calibrated, measured tone matching the sponsor's own admission that "Protocol SIFT works. It also hallucinates more than we'd like."
**So that** the second killer artifact of the submission (after the report itself) gives the judges a reproducible accuracy story they can audit, the IR Accuracy + Audit Trail Quality + Autonomous Execution Quality criteria score against a paper that says what we measured rather than what we claim, and the document matches Rob T. Lee's honesty-over-polish rubric without quoting his exact wording (PRD §14 vocabulary discipline — match the tone, not the verbatim phrase).

---

## File modification map

- `docs/ACCURACY_REPORT.md` — NEW — the deliverable. Sections in order (each is a top-level `##` heading):
  1. **Status + scope** — DRAFT / FINAL marker, datasets covered, harness version, generation timestamp from `harness/scorer.py`.
  2. **TL;DR** — table: per-dataset, baseline hallucination count vs SilentWitness hallucination count vs absolute Δ vs percentage reduction; primary metric (time-to-handoff-ready-report) per-dataset. ≤30 lines of table + 5 lines of plain-English summary.
  3. **Methodology** — how the harness was constructed: vanilla Protocol SIFT runner (cite story-baseline-runner), SilentWitness runner (cite story-silentwitness-runner), the precision / recall / hallucination-rate definitions per PRD §4 Secondary metrics, the deterministic-output normalization rules (architecture.md §4.6 — timestamp strip, whitespace, path separator before SHA256), what counts as a "hallucinated claim" per CyberSleuth Module III + DFIR-Metric HALL definition (cite both verbatim), the abstention-as-feature rule (PRD §4 Epistemic-honesty count).
  4. **Baseline establishment** — vanilla Protocol SIFT setup: stock SIFT 2026 VM, Claude Code v2.0.61 at `/usr/local/bin/claude`, no MCP server, system prompt is the vanilla Protocol SIFT prompt (sourced from `harness/baseline/vanilla_prompt.md`), same evidence mount, same time budget. Cite the exact run command from story-baseline-runner. Reproducibility instructions: how to re-run on a fresh SIFT VM. Disclose Mr. Evil / Greg Schardt memorization risk (PRD §9 verbatim) — the model has likely seen writeups; the harness measures gates not capability.
  5. **Datasets** — three subsections (Nitroba, NIST Data Leakage, NIST Hacking Case), each citing `docs/DATASETS.md` for source URL + canonical SHA256 + answer-key path + license. ≤15 lines per dataset.
  6. **Per-dataset results** — three subsections matching §5:
     - **Nitroba** — baseline precision/recall/hallucination/time, SilentWitness precision/recall/hallucination/time, Δ. ≥1 specific example of a baseline hallucination (file/path/hash not in image) and how the SilentWitness citation+entity gate rejected the same shape. ≤40 lines including a quoted JSONL audit entry.
     - **NIST Data Leakage** — same shape, quantitative numbers from `harness/scorer.py` output, ≥1 specific finding the harness's ground-truth parser scored as TP for SilentWitness and FN (false negative) for baseline (or vice versa where honest). ≤50 lines.
     - **NIST Hacking Case** — same shape, plus the on-brand Mr. Evil demo finding (Ethereal install path) with the audit trail. ≤50 lines.
  7. **Known false positives** — itemized list of TPs that the harness flagged as FPs because the ground-truth parser disagreed with the agent's interpretation, with our judgment on whether the parser or the agent was correct. Honest tone — if the agent was wrong, say so. ≥3 entries. ≤40 lines.
  8. **Known misses** — itemized list of ground-truth findings the agent did NOT surface. ≥3 entries. ≤40 lines.
  9. **Residual hallucinations we caught** — itemized list of REJECTED claims (server returned REJECTED before the claim landed in the report) — cite `audit/citation_gate.jsonl` + `audit/entity_gate.jsonl` entries by audit_id. Each entry: what the agent tried to claim, why the gate rejected, what the revised claim was. ≥3 entries. ≤50 lines.
  10. **Residual hallucinations we did NOT catch** — itemized list of claims that landed in the report but were later flagged by an offline `grep`-the-mounted-image verifier (the residual layer per PRD §4 Secondary metrics). Honest tone — explain why each escaped. ≥2 entries. ≤40 lines.
  11. **Sanitizer test corpus results** — per `tests/property/test_sanitizer.py` + `harness/datasets/case-trapdoor.yaml` (if Epic 15 ran), the count of prompt-injection patterns / unicode-trick characters detected and quarantined out of the planted total. Per-pattern table. ≤30 lines.
  12. **Threat model summary** — single page restating architecture.md §9: what we defend against (prompt injection in evidence, citation forgery, entity hallucination, ledger tampering), what we explicitly do NOT defend against (compromised SIFT host, malicious tool subprocess, model API key leak, side-channel timing). ≤30 lines.
  13. **Limitations + future work** — honest about Mr. Evil memorization risk; honest about critic-of-critic shared-inference failures (per `research/protocol-sift-2026/refs/quotes-for-pitch.md` §E.4 framing — tone-match, NO verbatim quote); honest about the gates' scope (line-level entity match, not byte-level — see architecture.md ADR-004). ≤30 lines.
  14. **Reproducibility** — single bash block: how to regenerate this entire report from scratch on a clean SIFT 2026 VM in one `just accuracy-harness` invocation; expected wall-clock ≤4 hours; expected $X token spend at default model. Cite story-cli-baseline-comparison.
  15. **Appendix A — Audit-trail samples** — 3 representative `audit/*.jsonl` entries (one citation-gate-PASS, one citation-gate-REJECT, one entity-gate-REJECT), each fully-formed JSON with `audit_id`, `tool`, `result_sha256`, `cited_spans` redacted to the entity-gate match list. ≤30 lines.
  16. **Appendix B — Glossary** — terms used in this report: TP, FP, FN, hallucinated-claim, abstention, citation-gate-PASS, entity-gate-REJECT. ≤20 lines.

  **LOC budget for the whole file: ≤500 lines.** If the file grows past 500, split Appendix A into `docs/ACCURACY_REPORT_APPENDIX_A.md` and link.

- `scripts/check_accuracy_report_vocab.py` — NEW — ≤60 LOC pure-Python gate that scans `docs/ACCURACY_REPORT.md` for the PRD §14 banned vocab list AND verifies that the literal quote *"Claude doesn't get defensive when you call it out"* and *"Protocol SIFT works. It also hallucinates more than we'd like."* are NOT present (tone-match required, verbatim quotation forbidden — both are Rob T. Lee's published phrases). Exit 0 on pass; exit 1 with the failing rule name on fail.
- `tests/unit/test_accuracy_report_vocab.py` — NEW — ≥6 BDD scenarios: clean fixture passes; fixture with banned vocab fails per rule; fixture with the Rob T. Lee verbatim quote fails; fixture without verbatim quote but with tone-match passes; fixture over 500 LOC fails.
- `tests/fixtures/accuracy_report/*.md` — NEW — ≥4 synthetic fixtures.

The coding agent must NOT touch `src/` or `harness/` from this story. If `harness/scorer.py` output numbers are needed, the coding agent reads them from `harness/output/scorecard.json` (produced by story-scorer) at write time — does NOT rewrite the scorer.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given docs/ACCURACY_REPORT.md exists
When  `wc -l docs/ACCURACY_REPORT.md` runs
Then  the line count is ≤500

Given docs/ACCURACY_REPORT.md is read
When  the top-level `## ` headings are enumerated
Then  16 distinct headings appear in the order specified in the file modification map
And   the first heading is "Status + scope"
And   the last heading is "Appendix B — Glossary"

Given docs/ACCURACY_REPORT.md is scanned for banned vocab
When  `grep -iE "court-admissible|autonomous soc|ralph wiggum|replaces l1|eliminates hallucinations" docs/ACCURACY_REPORT.md` runs
Then  exit code is 1 (no matches)

Given docs/ACCURACY_REPORT.md is scanned for Rob T. Lee verbatim quotes
When  `grep -F "Claude doesn't get defensive when you call it out" docs/ACCURACY_REPORT.md` runs
Then  exit code is 1 (no matches — tone-match only, verbatim forbidden)

When  `grep -F "Protocol SIFT works. It also hallucinates more than we'd like" docs/ACCURACY_REPORT.md` runs
Then  exit code is 1 (no matches)

Given docs/ACCURACY_REPORT.md contains the TL;DR section
When  the table of per-dataset Δ is read
Then  3 rows are present (Nitroba, NIST Data Leakage, NIST Hacking Case)
And   each row has numeric values in baseline + SilentWitness + Δ columns (NOT "TBD")

Given docs/ACCURACY_REPORT.md contains "Residual hallucinations we caught"
When  the section is parsed for itemized entries
Then  ≥3 entries appear
And   each entry cites at least one `audit_id` matching the regex `sift-[a-z0-9]+-\d{8}-\d{3}`

Given docs/ACCURACY_REPORT.md contains "Residual hallucinations we did NOT catch"
When  the section is parsed for itemized entries
Then  ≥2 entries appear

Given docs/ACCURACY_REPORT.md contains "Reproducibility"
When  the bash block under that heading is extracted
Then  it contains `just accuracy-harness`

Given `scripts/check_accuracy_report_vocab.py` exists
When  `uv run python scripts/check_accuracy_report_vocab.py docs/ACCURACY_REPORT.md` runs
Then  exit code is 0

Given `tests/unit/test_accuracy_report_vocab.py` exists
When  `uv run pytest tests/unit/test_accuracy_report_vocab.py -v` runs
Then  exit code is 0
And   ≥6 tests pass

Given docs/ACCURACY_REPORT.md is read by markdownlint with the project config
When  `markdownlint docs/ACCURACY_REPORT.md` runs (or pure-Python equivalent)
Then  no errors of class MD001 (heading-increment) or MD025 (single H1) are raised
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
# LOC cap
[ "$(wc -l < docs/ACCURACY_REPORT.md)" -le 500 ] || { echo "ACCURACY_REPORT over 500 LOC"; exit 1; }

# Banned vocab clean
! grep -iE "court-admissible|autonomous soc|ralph wiggum|replaces l1|eliminates hallucinations" docs/ACCURACY_REPORT.md

# Rob T. Lee verbatim quotes NOT present (tone-match only)
! grep -F "Claude doesn't get defensive when you call it out" docs/ACCURACY_REPORT.md
! grep -F "Protocol SIFT works. It also hallucinates more than we'd like" docs/ACCURACY_REPORT.md

# 16 top-level sections present
[ "$(grep -cE '^## ' docs/ACCURACY_REPORT.md)" -eq 16 ]

# TL;DR table has all three datasets
grep -E "Nitroba|NIST Data Leakage|NIST Hacking Case" docs/ACCURACY_REPORT.md | head -20

# audit_id citations present in "Residual hallucinations we caught"
awk '/^## Residual hallucinations we caught/,/^## Residual hallucinations we did NOT catch/' docs/ACCURACY_REPORT.md | \
  grep -cE "sift-[a-z0-9]+-[0-9]{8}-[0-9]{3}"
# Must output ≥3

# Vocab gate passes
uv run python scripts/check_accuracy_report_vocab.py docs/ACCURACY_REPORT.md

# Tests pass
uv run pytest tests/unit/test_accuracy_report_vocab.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥6

# §14 banned-vocab check on the diff
git diff main...HEAD -- docs/ACCURACY_REPORT.md | grep -E "^\+" | grep -iE "(court-admissible|autonomous soc|ralph wiggum|replaces l1|eliminates hallucinations)"
# Must output nothing
```

---

## Notes for coding agent

- Source of truth: PRD §4 (the headline + secondary metrics — precision, recall, hallucination-rate, pivot count, claim-provenance rate, epistemic-honesty count; the Mr. Evil memorization-risk note PRD §9), PRD §8 row 2 (IR Accuracy criterion definition), PRD §10 deliverable 6 (this is `docs/accuracy-report.md` per PRD — we use `docs/ACCURACY_REPORT.md` (upper) for filesystem prominence; the PRD path is a directive on placement, not exact casing), PRD §14 (vocabulary discipline + the explicit reject list), architecture.md §4.6 (output normalization rules — cite verbatim methodology), architecture.md §9 (threat model — verbatim source for §12 of this report), architecture.md ADR-004 (line-level + entity gate over byte-level — limitation to disclose in §13), `research/protocol-sift-2026/refs/quotes-for-pitch.md` §B.3 (the honesty framing — tone-match WITHOUT verbatim quote) and §E.3 (the architecture story — same), `context/evaluation/10-datasets-and-evaluation-methodology.md` (the CyberSleuth Module III + DFIR-Metric HALL definitions — cite both by section number).
- **The honesty tone is load-bearing.** Rob T. Lee's published rubric explicitly rewards saying what you got wrong. Match the tone via the §8 / §9 / §10 / §13 sections that itemize false positives, misses, residual hallucinations the gates caught, residual hallucinations the gates missed, and disclosed limitations. The verbatim quote *"Claude doesn't get defensive when you call it out"* is what Rob said about Claude in his blog post; we don't quote it back at him (he wrote it about a different system) — we DEMONSTRATE it by saying what we got wrong. Tone-match, never copy-paste.
- **Numbers come from the harness, not from estimates.** The TL;DR table and the per-dataset results sections read from `harness/output/scorecard.json` produced by story-scorer (Epic 14). The coding agent for THIS story does NOT compute or estimate numbers — they regenerate the report from the scorer output at write time. If `scorecard.json` is missing (harness hasn't run yet), the coding agent SHOULD block the merge and surface "run `just accuracy-harness` first" — do NOT write "TBD" or "TODO" or any placeholder; an in-progress report with placeholder numbers is worse than no report.
- **Story sequencing.** This story DEPENDS ON story-baseline-runner + story-silentwitness-runner + story-scorer + story-delta-report all having merged with real outputs in `harness/output/`. If those have not merged, this story cannot complete; block the orchestrator with a clear message.
- **Memorization-risk disclosure.** PRD §9 verbatim: NIST Hacking Case is "very high" memorization risk because canonical answers (MAC, IP, hostname, "Mr. Evil" email) appear in hundreds of indexed writeups. The §4 "Baseline establishment" section MUST state this in the first paragraph and explain that the harness is testing the gates (does the agent ground claims in evidence-present spans?) NOT the model's latent capability. This is the honest framing. Failure to disclose = scoring own goal.
- **Citation discipline inside the report.** Every quantitative claim cites either a `harness/output/scorecard.json` field, an `audit/*.jsonl` `audit_id`, or a dataset manifest at `harness/datasets/<name>.yaml`. Sentences like "the citation gate rejected 14 claims" without a citation are NOT acceptable. The tone is "Here is what we measured + here is where you can verify it" — same discipline the architecturally-enforced citation gate applies to the agent.
- **Sanitizer test-corpus section (§11).** This depends on story-gates-property-tests (Epic 3) shipping the property-test fixture corpus AND story-sanitizer landing the sanitizer. The numbers come from `tests/property/output/sanitizer-corpus-results.json` (a CI artifact). If story-case-trapdoor (Epic 15) ran, augment with those numbers; if not, note that case-trapdoor was deferred and the §11 numbers come from the property-test corpus alone.
- **What counts as a hallucinated claim** (PRD §4 verbatim methodology):
  1. **Caught (gate-floor):** Citation gate or entity gate returned REJECTED before the claim landed in the report. Counted via `grep -c '"verdict":"REJECTED"' cases/*/audit/citation_gate.jsonl cases/*/audit/entity_gate.jsonl`.
  2. **Escaped (residual):** Claim that landed in the report but does not survive an offline `grep` of the mounted image for the cited entity / path / hash. Counted via `harness/verify_residual.py` (a stretch script — if missing, the coding agent runs `grep` by hand against the three case directories and records the count + a per-instance audit_id list).
- **Reproducibility section (§14).** The exact bash:
  ```
  curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/<org>/silentwitness/main/install.sh | bash
  cd ~/silentwitness && just accuracy-harness
  cat harness/output/scorecard.json
  cat docs/ACCURACY_REPORT.md   # regenerated from scorecard.json
  ```
  Wall-clock: ≤4h on the three datasets with default model. Token spend: order-of-magnitude estimate from a single dry run, with the actual run's `model_token_count` summed from `audit/*.jsonl` cited.
- **Sample audit-trail JSONL in Appendix A.** Real entries copied from a real case run; redact only the examiner name + the model API key (which should never appear anyway). Format: one JSON object per line; `jq -c` the entries before pasting so the line lengths are consistent.
- **No emojis.** Per ux-spec §6 + the project-wide tone. The three-prefix CLI rule (`✓` `⚠` `✗`) does not apply to documents.
- **Markdown linting.** Use the project's `.markdownlint.yaml` config (if present from CICD_SPEC §3); otherwise: H1 single-instance, heading hierarchy increments by one, no trailing whitespace, fenced code blocks have language tags.
- Known pitfalls:
  1. The Rob T. Lee verbatim-quote ban is enforced by the gate. If a coding agent quotes him verbatim "to credit him properly," the gate fails. Credit via citation in a footnote (`[1]: research/protocol-sift-2026/refs/quotes-for-pitch.md §B.3`) — do not paste his sentence.
  2. The 500-line cap is tight given 16 sections + 3 datasets. Keep each per-dataset entry to ≤50 lines; lean on `docs/DATASETS.md` for source-URL + license + license-trail repetition.
  3. The "Residual hallucinations we did NOT catch" section is the most important. ≥2 entries; honest about why each escaped (e.g., "the agent and critic shared the same incorrect inference about the tool's output"). If you cannot list ≥2 residuals — either the harness is too lenient or the gates are perfect (unlikely). Re-run the residual verifier and find them.
  4. The verbatim CyberSleuth Module III + DFIR-Metric HALL definitions belong in §3 Methodology as quoted text with the citation. If they're not in `context/evaluation/10-datasets-and-evaluation-methodology.md`, raise it as a blocker — they're load-bearing.
- Vocabulary discipline (PRD §14): never "court-admissible" (use "defensible audit trail" or "survives cross-examination"); never "autonomous SOC" / "replaces L1" / "eliminates hallucinations"; never "Ralph Wiggum Loop" (describe behavior: "closed-loop critic that re-reads evidence and CHALLENGES findings"); never quote Rob T. Lee verbatim (tone-match only). The gate enforces these.
