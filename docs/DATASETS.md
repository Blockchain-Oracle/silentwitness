# Datasets — SilentWitness evidence corpus

This catalog documents every evidence dataset SilentWitness is tested against (accuracy harness + memorization-risk disclosure). For each dataset: source URL, canonical SHA256 (lifted verbatim from `harness/datasets/<id>.manifest.json`), what we tested, what we found, what we missed, the memorization-risk band, and a reproducibility recipe judges can follow step by step.

## At a glance

| Dataset | Size | Role | Memorization-risk band | Status |
|---|---|---|---|---|
| Nitroba University Harassment | ~56 MB pcap | Active — primary IR benchmark | Medium (community writeups exist; no official solution PDF) | active |
| NIST CFReDS Data Leakage Case | ~20 GB E01 + media | Active — broad-coverage Windows IR | Medium per-artifact / High scenario-summary | active |
| NIST CFReDS Hacking Case (Mr. Evil) | ~6 GB E01 | Active — verify entity-gate behavior under high-memorization pressure | **High** (canonical answers in hundreds of writeups) | active |
| case-trapdoor (synthetic adversary pair) | n/a | Optional / Epic 15 | None (synthetic, no public answers) | optional (skipped until Epic 15 ships) |

## Official SANS Find Evil! 2026 datasets (Egnyte share)

The hackathon's official cases live behind a public Egnyte share — no account, no API key, just `python scripts/download_starter_cases.py`. The script speaks the Egnyte share-link API directly (the same one their web UI uses), paginates folder listings, and streams files in 1 MiB chunks with on-the-fly SHA256.

```bash
# Enumerate every case at the share root (counts + sizes)
python scripts/download_starter_cases.py list

# Output (as of 2026-06-15):
#   Compromised APT Attack Scenarios: 33 files, 177.44 GiB
#   Standard Forensic Case:            3 files,  27.38 GiB
#   Standard Forensics Case 2:         2 files,  40.73 GiB

# Drill into one case
python scripts/download_starter_cases.py list "Standard Forensic Case"
#       38.3 MiB  /HACKATHON-2026/Standard Forensic Case/ROCBA-BACKGROUND.pptx
#      22.05 GiB  /HACKATHON-2026/Standard Forensic Case/rocba-cdrive.e01
#       5.29 GiB  /HACKATHON-2026/Standard Forensic Case/Rocba-Memory.zip

# Dry-run a download (no GETs, just prints what it would do)
python scripts/download_starter_cases.py download "Standard Forensic Case" /evidence/rocba --dry-run

# Real download — idempotent, resumable (skips files already at expected size)
python scripts/download_starter_cases.py download "Standard Forensic Case" /evidence/rocba
```

Verified locally on 2026-06-15: `ROCBA-BACKGROUND.pptx` (38.3 MiB) downloads cleanly with SHA256 `44a12c54d1324339…`. The large E01 + memory archives weren't downloaded during scaffolding; their size matches the Egnyte UI to the byte.

**Multi-host scope.** SilentWitness's submission demonstrates the single-host spine end-to-end on the ROCBA case (Standard Forensic Case). The downloader works for ALL three cases — including the 177 GiB multi-host APT bundle — but full cross-host investigation correlation is tracked as Phase 10 follow-up (out of scope for the v1.0.0-hackathon-2026 tag). The 33-file APT case is downloadable + per-host indexable today; the cross-host hypothesis linker lands later.

## Reproducibility recipe

Prerequisites: `uv==0.11.18` (or any 0.11.x; CLAUDE.md pins this), Python 3.12, and a working `bash`. The `evidence/` directory is `.gitignore`'d so binaries never enter the git index.

The same recipe works for every active dataset. Substitute `<dataset>` with one of `nitroba`, `nist-data-leakage`, `nist-hacking-case`.

```bash
# 1. Clone and install
git clone https://github.com/Blockchain-Oracle/silentwitness.git && cd silentwitness
uv sync

# 2. Fetch the binary to the gitignored evidence root (see per-dataset section
#    below for the exact URL — datasets ship from official archives only).
mkdir -p evidence/

# 3. Verify hash against the committed manifest (strict mode aborts on drift).
#    Note: NIST manifests pin SHA256 on first fetch; strict mode passes once
#    the manifest's `<computed-on-fetch>` placeholder is populated.
uv run python harness/datasets/verify_manifest.py \
    --manifest harness/datasets/<dataset>.manifest.json --strict

# 4. Run baseline + silentwitness + scorer + delta report
#    (one-shot via `just harness DATASET=<dataset>`).
just harness DATASET=<dataset>
# OR step-by-step:
uv run python -m harness.baseline.runner --dataset <dataset> --evidence ./evidence
uv run python -m harness.silentwitness.runner --dataset <dataset> --evidence ./evidence
uv run python -m harness.scorer --dataset <dataset> \
    --baseline harness/results/<dataset>/baseline-*.json \
    --silentwitness harness/results/<dataset>/silentwitness-*.json \
    --evidence ./evidence
uv run python -m harness.delta_report --dataset <dataset>

# 5. Read the delta report and bar chart.
cat harness/results/<dataset>/delta.md
open harness/results/<dataset>/delta.png   # or xdg-open on Linux / start on Windows
```

## Nitroba University Harassment

- **Source URL:** `https://digitalcorpora.s3.amazonaws.com/corpora/scenarios/2008-nitroba/nitroba.pcap` (per `harness/datasets/nitroba.manifest.json`)
- **Size:** ~56 MB pcap (56,180,821 bytes exact)
- **SHA256:** `2b77a9eaefc1d6af163d1ba793c96dbccacb04e6befdf1a0b01f8c67553ec2fb` (verbatim from `harness/datasets/nitroba.manifest.json`)
- **Ground-truth source:** hand-crafted from community-converged consensus. The 2010 DFRWS official solution PDF is password-gated and is NOT used; the SilentWitness parser reads `harness/ground_truth/nitroba.handcrafted.json` per `story-ground-truth-parsers.notes`.
- **What we tested:** wireless harassment investigation; suspect identification (Johnny Lee Henry); willselfdestruct.com one-shot URL; SMTP timing; DHCP lease windows; MAC-to-room mapping.
- **What we found:** `harness/results/nitroba/delta.md` carries the latest scoring run with precision / recall / hallucination_rate / time-to-handoff-ready-report. Re-run `just harness DATASET=nitroba` or follow the reproducibility recipe above to regenerate.
- **What we missed:** the top FALSE_NEGATIVE classifications from the latest scoring run are surfaced as `harness.scorer.compute_false_negatives` rows in `harness/results/nitroba/scoring-*.json`; the delta report (`harness/results/nitroba/delta.md`) summarizes the top 5.
- **Memorization-risk band:** Medium. Community writeups exist on academic course pages and DFIR blogs but no official answer key is published; the gates are exercised under realistic information-leakage pressure.
- **Reproducibility:** the dataset is publicly available from the Digital Corpora archive; redistribution permitted under their documented terms.

## NIST CFReDS Data Leakage Case

- **Source URL:** `https://cfreds-archive.nist.gov/data_leakage_case/`
- **Size:** ~20 GB total — Windows XP workstation E01 + removable-media raw images
- **SHA256:** `<computed-on-fetch>` (the manifest at `harness/datasets/nist-data-leakage.manifest.json` carries a `<computed-on-fetch>` placeholder; the legacy MD5 cross-reference `A49D1254C873808C58E6F1BCD60B5BDE` is preserved in the manifest's `legacy_cross_references` section)
- **Ground-truth source:** parseable public PDF answer key (`leakage-answers.pdf`); parsed by `harness/ground_truth/nist_data_leakage_parser.py`; yields 20+ structured ground-truth findings.
- **What we tested:** Iaman Informant insider-threat pivot chain; exfiltration via removable media + email + cloud; LNK-and-shellbag tracking; browser history.
- **What we found:** `harness/results/nist-data-leakage/delta.md` carries the latest scoring run. Re-run via the reproducibility recipe above.
- **What we missed:** top FALSE_NEGATIVE rows from `harness/results/nist-data-leakage/scoring-*.json`; summarized in `harness/results/nist-data-leakage/delta.md`.
- **Memorization-risk band:** High for scenario summary (CFReDS scenario name is widely indexed), Medium for per-artifact paths (less commonly cited).
- **Reproducibility note:** the 20 GB download takes 20–40 minutes wall-clock the first time. Verify the manifest before running the harness; mismatch aborts in strict mode.

## NIST CFReDS Hacking Case (Greg Schardt / Mr. Evil)

> **Memorization-risk disclosure (verbatim):** Greg Schardt / Mr. Evil canonical answers (MAC, IP, hostname, email) appear in hundreds of indexed writeups. A passing finding here is not evidence of working forensic capability — it is evidence the model has seen the writeups. The citation + entity gate forces every claim to ground in evidence-present spans rather than regurgitated memory; this dataset demonstrates the gates work, not latent capability.

- **Source URL:** `https://cfreds-archive.nist.gov/Hacking_Case.html` (canonical single reassembled EnCase E01 at `images/4Dell Latitude CPi.E01`)
- **Size:** ~6 GB E01 (reassembled from the 7 segmented files NIST originally distributed)
- **SHA256:** `<computed-on-fetch>` per `harness/datasets/nist-hacking-case.manifest.json`
- **Ground-truth source:** parsed by `harness/ground_truth/nist_hacking_case_parser.py` from the NIST scenario document + community-converged supplemental answers at `harness/ground_truth/nist-hacking-case.supplemental.json`.
- **What we tested:** Ethereal / Anonymizer / Cain tool-installation provenance; intercepted-credential trail; LNK / Prefetch / Registry recovery.
- **What we found:** `harness/results/nist-hacking-case/delta.md` carries the latest scoring run.
- **What we missed:** top FALSE_NEGATIVE rows from `harness/results/nist-hacking-case/scoring-*.json`.
- **Memorization-risk band:** **High.** This is the dataset where the entity-gate proof-of-correctness lives — every claim must cite an audit row whose stored stdout contains the entity, otherwise the observation is rejected.
- **Reproducibility note:** 6 GB download. After verify, expect ~30 minutes baseline + silentwitness runs (the model walks the same evidence the baseline does; the Δ vs the baseline is the headline metric).

## case-trapdoor

- **Status:** Optional. Synthetic adversary-pair challenge case created specifically for SilentWitness evaluation to avoid LLM memorization bias. Evidence artifacts and ground-truth answers will be provided when Epic 15 ships.
- **Source:** `harness/datasets/case-trapdoor.manifest.json` (placeholder SHA256; the scorer and runners skip this dataset gracefully when the placeholder is detected).
- **Why it matters:** when shipped, this is the dataset where a *clean* delta is achievable — no internet writeups can leak answers because the case did not exist before Epic 15.
- **Memorization-risk band:** None (synthetic, no public answers).

## Gitignored evidence binaries

The repo never commits dataset binaries. `evidence/` is in `.gitignore`; fetched files land there and stay local. The committed manifests at `harness/datasets/<id>.manifest.json` carry the canonical SHA256, expected size, and source URL — that triple is what the CI hash-verify gate (`dataset-hash-verify` workflow) anchors against. If you receive a corpus from a colleague, drop it under `evidence/<dataset>/` and run step 3 of the recipe to confirm the hash matches before scoring.

## Verification

Two CI gates protect against silent dataset drift:

1. **`harness/datasets/verify_manifest.py --strict`** (run by humans + by `just harness`): reads the committed manifest, computes the SHA256 of the on-disk binary, asserts equality, and aborts with a non-zero exit if either is missing or drifts. Strict mode also refuses to run against a `<computed-on-fetch>` placeholder so an un-pinned manifest never produces fake-clean scoring numbers.
2. **`.github/workflows/dataset-hash-verify.yml`** (CI on every PR touching `harness/datasets/`): re-computes the SHA256 of the committed `nitroba-stub.manifest.json` fixture and asserts the manifest's hash field is correct. This catches a maintainer mutating the manifest without re-fetching.

Anyone can independently verify a manifest by running `sha256sum <binary> | grep -i $(jq -r .sha256 harness/datasets/<id>.manifest.json)`.

## Sources + licenses

| Dataset | Distributor | License / terms |
|---|---|---|
| Nitroba | Digital Corpora (NPS) | Free for research + education; redistribution permitted under Digital Corpora's documented terms |
| NIST Data Leakage Case | NIST CFReDS Archive | Public domain (US Government work, 17 USC §105); redistribution permitted |
| NIST Hacking Case | NIST CFReDS Archive | Public domain (US Government work, 17 USC §105); redistribution permitted |
| case-trapdoor (synthetic) | SilentWitness (this repo, when Epic 15 ships) | MIT (matches SilentWitness license) |

## Cross-references

- Per-dataset binary hashes + ground-truth parser pointers: `harness/datasets/<id>.manifest.json`.
- Scoring + delta artifacts (regenerated by the recipe above): `harness/results/<id>/`.
- Accuracy report (cross-dataset summary): `ACCURACY_REPORT.md`.
- Memorization-risk discipline: verbatim Mr. Evil paragraph quoted above.
