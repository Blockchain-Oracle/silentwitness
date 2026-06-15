# Story — Dataset documentation (`docs/DATASETS.md`; Rules deliverable #5; per-dataset reproducibility writeup)

**ID:** story-dataset-doc
**Epic:** Epic 16 — Documentation polish + submission
**Depends on:** story-dataset-manifests, story-ground-truth-parsers, story-scorer, story-delta-report, story-accuracy-report-writeup
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent assembling the Devpost Rules §4 deliverable set
**I want to** ship `docs/DATASETS.md` — the human-readable catalog of every evidence dataset SilentWitness is tested against, with per-dataset: source URL, canonical SHA256 (lifted verbatim from the manifest at `harness/datasets/<name>.manifest.json`), what was tested, what was found (live link to the matching scoring + delta artifacts), what was missed (false-negatives table from the latest scoring run), and a reproducibility recipe (clone → fetch → verify hash → run harness)
**So that** PRD §10 deliverable 5 ("Dataset documentation") is satisfied with a single Markdown file judges can read end-to-end in <5 minutes, the memorization-risk disclosure for NIST Hacking Case is surfaced verbatim per Rob T. Lee's honesty rubric (PRD §9), and any reviewer can reproduce the bar-chart numbers by following the recipe step by step (epics.md Epic 16 DoD; PRD §14 vocabulary discipline; FR11 reproducibility).

---

## File modification map

- `docs/DATASETS.md` — NEW — Markdown document, ≤400 lines. Section order locked:
  1. `# Datasets — SilentWitness evidence corpus` — H1 + 2-sentence framing tying back to PRD §4 + §9.
  2. `## At a glance` — single Markdown table summarising all four datasets: columns `Dataset | Size | Role | Memorization-risk band | Status (active/optional/skipped)`. Lifted from PRD §9 verbatim with the `Status` column added.
  3. `## Reproducibility recipe` — copy-paste shell block applicable to ANY dataset:
     ```bash
     # 1. Clone and install
     git clone https://github.com/<org>/silentwitness.git && cd silentwitness
     uv sync
     # 2. Fetch the binary to the gitignored evidence root
     mkdir -p evidence/
     # See per-dataset section below for the fetch command + canonical SHA256
     # 3. Verify hash
     uv run python harness/datasets/verify_manifest.py --manifest harness/datasets/<dataset>.manifest.json --strict
     # 4. Run baseline + silentwitness + scorer + delta report
     just harness DATASET=<dataset>
     # 5. Read the delta report
     cat harness/results/<dataset>/delta.md
     ```
  4. `## Nitroba University Harassment` — per PRD §9 row + harness manifest:
     - Source URL: `<from manifest>`
     - Size: ~60 MB pcap
     - SHA256: `2b77a9eaefc1d6af163d1ba793c96dbccacb04e6befdf1a0b01f8c67553ec2fb` (verbatim from `harness/datasets/nitroba.manifest.json`)
     - Ground-truth source: hand-crafted from community-converged consensus (the password-gated NIST solution PDF is NOT used; PRD §9 + story-ground-truth-parsers `notes`)
     - What we tested: wireless harassment investigation; suspect identification (Johnny Lee Henry); willselfdestruct.com one-shot URL; SMTP timing
     - What we found: link to `harness/results/nitroba/delta.md` showing precision/recall/hallucination-rate (lifted at write time from the latest scoring JSON; if absent, document the `just harness DATASET=nitroba` command that produces it)
     - What we missed: list of FALSE_NEGATIVE classifications from the scoring run (top 5; full list in the scoring JSON)
     - Memorization-risk band: medium (per manifest)
     - Reproducibility: dataset is publicly available from `<official URL>`; redistribution permitted under the dataset's documented license.
  5. `## NIST CFReDS Data Leakage Case` — same shape:
     - Source URL: `https://cfreds-archive.nist.gov/data_leakage_case/`
     - Size: ~20 GB E01 + removable-media raw
     - SHA256: `<computed-on-fetch>` (note: placeholder until fetched once; the manifest holds the legacy MD5 `A49D1254C873808C58E6F1BCD60B5BDE` cross-reference)
     - Ground-truth source: parseable public PDF answer key (`leakage-answers.pdf`); parsed by `harness/ground_truth/nist_data_leakage_parser.py`; 20+ structured findings
     - What we tested: Iaman Informant pivot chain, exfiltration via removable media + email + cloud
     - What we found: link to `harness/results/nist-data-leakage/delta.md`
     - What we missed: top 5 FALSE_NEGATIVE classifications
     - Memorization-risk band: high for scenario summary, medium for per-artifact paths
     - Reproducibility note: 20 GB download; expect 20–40 minutes wall-clock the first time.
  6. `## NIST CFReDS Hacking Case (Greg Schardt / Mr. Evil)` — same shape PLUS the verbatim PRD §9 memorization-risk paragraph as a callout block at the top of the section:
     > **Memorization-risk disclosure (PRD §9, verbatim):** Greg Schardt / Mr. Evil canonical answers (MAC, IP, hostname, email) appear in hundreds of indexed writeups. A passing finding here is not evidence of working forensic capability — it is evidence the model has seen the writeups. The citation + entity gate forces every claim to ground in evidence-present spans rather than regurgitated memory; this dataset demonstrates the gates work, not latent capability.
     - Source URL: `https://cfreds-archive.nist.gov/all/Computer/Misc/HackingCase`
     - Size: ~6 GB reassembled DD
     - SHA256: `<computed-on-fetch>` (legacy MD5 `aee4fcd9301c03b3b054623ca261959a` cross-referenced from manifest)
     - Ground-truth source: community writeups at intrinsicode.net + zarat.hatenablog.com; snapshots committed under `harness/ground_truth/snapshots/`; 15+ findings
     - What we tested: primary user profile = Mr. Evil; installed tools (Ethereal, Anonymizer, Cain & Abel); MAC `00:02:B3:DD:00:A2`; intercepted credentials
     - What we found: link to `harness/results/nist-hacking-case/delta.md`
     - What we missed: top 5 FALSE_NEGATIVE classifications
     - Memorization-risk band: very high (manifest + PRD §9 + this disclosure)
     - Reproducibility note: same as NIST Data Leakage; expect 15–30 minute first fetch.
  7. `## case-trapdoor (synthetic, OPTIONAL)` — per Epic 15 status:
     - If Epic 15 has shipped: link to `harness/case-trapdoor/SYNTHESIS_LOG.md` for the per-element ground-truth derivation; full reproducibility recipe (`python harness/case-trapdoor/synthesis.py --output harness/case-trapdoor/output/`).
     - If Epic 15 has NOT shipped (default state): single paragraph documenting the optional epic and pointing the reader to the empty-state placeholder.
     - Memorization-risk band: low (synthetic by definition)
     - License of synthesized outputs: MIT (per Epic 15 directive).
  8. `## Gitignored evidence binaries` — short note on why binaries are NOT committed (`.gitignore` entries for `*.E01 *.dd *.pcap *.img` per story-dataset-manifests); only manifests + the 60 MB Nitroba stub are committed; CI only verifies the stub.
  9. `## Verification` — short walkthrough showing how to re-verify any manifest:
     ```bash
     uv run python harness/datasets/verify_manifest.py --manifest harness/datasets/<dataset>.manifest.json
     ```
     and how to interpret the rich-table output.
  10. `## Sources + licenses` — table mapping each dataset to its license + citation. NIST CFReDS datasets are in the public domain (US federal work); Nitroba is research-use under the dataset's documented terms; case-trapdoor outputs are MIT. Two-column table, ≤1 row per dataset.
- `scripts/build_datasets_doc.py` — NEW — ≤200 LOC helper invoked by CI (added to `just check-docs`). Reads `harness/datasets/*.manifest.json` + the latest `harness/results/<dataset>/scoring-*.json` + `delta.md` and emits a freshness check: every active dataset section in `docs/DATASETS.md` must reference a SHA256 that matches the manifest verbatim; every "What we found" subsection that links to a scoring artifact must reference a file that exists. Exits 0 on pass; exits 1 with the failing dataset_id on drift. Does NOT auto-mutate `DATASETS.md` (author-controlled markdown — the script catches drift, the human resolves).
- `tests/unit/test_datasets_doc.py` — NEW — ≥6 BDD scenarios via subprocess against `scripts/build_datasets_doc.py` and a fixture `docs/DATASETS-fixture.md` that intentionally drifts (wrong SHA, missing section, banned vocab, etc.):
  - script exits 0 against a clean DATASETS.md fixture;
  - script exits 1 when the Nitroba SHA256 in DATASETS.md does NOT match the manifest;
  - script exits 1 when a referenced `harness/results/<dataset>/delta.md` path does not exist;
  - script exits 1 when the NIST Hacking Case section is missing the verbatim memorization-risk paragraph;
  - script exits 1 when the banned vocab list (PRD §14) appears anywhere in the file (court-admissible, Ralph Wiggum, autonomous SOC);
  - script exits 1 when total line count exceeds 400.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given docs/DATASETS.md is committed
When  `wc -l docs/DATASETS.md` runs
Then  the line count is ≤ 400

Given docs/DATASETS.md is committed
When  `grep -c '^## ' docs/DATASETS.md` runs
Then  the integer is ≥ 9 (At a glance, Reproducibility recipe, Nitroba, NIST Data Leakage, NIST Hacking Case, case-trapdoor, Gitignored, Verification, Sources)

Given docs/DATASETS.md is committed
When  `grep -F '2b77a9eaefc1d6af163d1ba793c96dbccacb04e6befdf1a0b01f8c67553ec2fb' docs/DATASETS.md` runs
Then  exit code is 0 (Nitroba SHA256 present verbatim)

Given docs/DATASETS.md is committed
When  `grep -F 'A passing finding here is not evidence of working forensic capability' docs/DATASETS.md` runs
Then  exit code is 0 (NIST Hacking Case memorization-risk paragraph present verbatim)

Given docs/DATASETS.md is committed
When  `grep -iE '(court-admissible|Ralph Wiggum|autonomous SOC|replaces L1|eliminates hallucinations)' docs/DATASETS.md` runs
Then  exit code is 1 (banned vocab list zero hits)

Given `uv run python scripts/build_datasets_doc.py` runs against committed docs/DATASETS.md + manifests
When  the script completes
Then  exit code is 0

Given a fixture DATASETS-fixture-bad-sha.md with a wrong Nitroba SHA
When  `uv run python scripts/build_datasets_doc.py --file tests/fixtures/datasets/DATASETS-fixture-bad-sha.md` runs
Then  exit code is 1
And   stderr contains "nitroba" and "sha256 mismatch"

Given tests/unit/test_datasets_doc.py exists
When  `uv run pytest tests/unit/test_datasets_doc.py -v` runs
Then  exit code is 0
And   ≥6 tests pass
```

---

## Shell verification

```bash
# Tests
uv run pytest tests/unit/test_datasets_doc.py -v

# Lint
uv run ruff check scripts/build_datasets_doc.py

# §14 vocab gate clean on the doc
grep -iE '(court-admissible|Ralph Wiggum|autonomous SOC|replaces L1|eliminates hallucinations)' docs/DATASETS.md && exit 1 || true

# Line-count cap
test "$(wc -l < docs/DATASETS.md)" -le 400

# Drift check
uv run python scripts/build_datasets_doc.py
```

---

## Notes for coding agent

- Reference: `docs/PRD.md` §9 (dataset choice table — copy the table verbatim into "At a glance"; copy the NIST Hacking Case memorization-risk paragraph verbatim into the section callout) + §10 deliverable 5 (Dataset documentation); `docs/architecture.md` §3 folder layout; `harness/datasets/*.manifest.json` (SHA256 + memorization-risk fields are the source of truth — DATASETS.md references them, never reinvents them); `docs/epics.md` Epic 16 DoD ("rules §4 deliverable checklist passes"); `docs/CICD_SPEC.md` §14 vocab gate.
- **Single source of truth discipline:** SHA256 + memorization-risk band live in `harness/datasets/<name>.manifest.json`. `docs/DATASETS.md` quotes them. `scripts/build_datasets_doc.py` enforces that the quote matches verbatim. If a manifest changes, this doc must be updated in the same commit — that's the freshness gate.
- **Memorization-risk disclosure is the killer honesty beat (PRD §9):** the verbatim paragraph for NIST Hacking Case MUST appear in the section, not paraphrased. The drift check enforces this with `grep -F 'A passing finding here is not evidence of working forensic capability'`. This is the difference between a credible accuracy report and a vanity one — Rob T. Lee's published rubric explicitly rewards self-disclosure of memorization risk.
- **Reproducibility recipe is paste-ready:** every shell line must work when copied. No placeholders the reader has to guess at (`<org>` is the only intentional placeholder; document it in the section preamble). Test the recipe against a clean clone before merging.
- **"What we found / What we missed" links are dynamic:** they point to `harness/results/<dataset>/delta.md` + the latest `scoring-*.json`. If those files do not yet exist on first commit (the harness hasn't been run), document the `just harness DATASET=<dataset>` command that produces them — do NOT inline placeholder numbers. PRD §14: never claim what you cannot show.
- **DATASETS.md is judge-facing.** Optimise for the 5-minute scan: H2 navigation, tight tables, no walls of prose. The verbatim memorization-risk paragraph is the one exception — it earns the lines.
- **case-trapdoor section gates on Epic 15:** if Epic 15 (`story-case-trapdoor-synthesis` + `story-case-trapdoor-ground-truth`) hasn't shipped, the section documents the optional status and links to the epic. Do NOT delete the section — its presence is the audit trail showing the optional epic was scoped + visible.
- **Public-domain status (NIST CFReDS):** US federal government works are in the public domain (17 USC §105). Document this verbatim; do not paraphrase as "open source" or "MIT" — they are NOT MIT, they are public domain. The case-trapdoor outputs ARE MIT (we own the synthesis).
- **`scripts/build_datasets_doc.py` is a CI gate, not a generator.** It does NOT mutate `DATASETS.md`. The doc is human-edited; the script fails CI if the human forgets to update it. This matches the pattern in story-readme-polish (which uses `scripts/check_readme_gate.py` the same way).
- Vocabulary discipline (PRD §14): never "court-admissible"; never "autonomous SOC"; never "Ralph Wiggum Loop"; never "replaces L1"; never "eliminates hallucinations". Use "memorization-risk disclosure", "ground-truth fidelity", "reproducibility recipe". The literal phrase "Find Evil!" is allowed when referring to the hackathon name (PRD §14 carve-out — same as story-readme-polish).
- Library docs to consult via Context7 BEFORE coding:
  - `pydantic` topic `model_validate_json + selective field extraction` (the drift-check script loads each manifest as `DatasetManifest` and asserts the SHA256 + memorization-risk fields).
- Known pitfalls:
  1. Per-dataset SHA256 strings are 64 hex chars — easy to typo. Use `grep -F` (literal mode) in the drift check, not `grep -E`.
  2. NIST CFReDS archive has moved (cfreds.nist.gov → cfreds-archive.nist.gov) — pin the archived URL; document the move in the section.
  3. The "What we found" link to `harness/results/<dataset>/delta.md` will 404 on the GitHub web UI until the harness has been run at least once. Document this clearly so a judge browsing the gallery preview understands the artifact is generated, not static.
  4. Total line cap 400 — if you exceed, cut the "Sources + licenses" appendix to a single sentence per dataset; the manifest is the canonical source.
