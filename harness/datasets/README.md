# Harness datasets

This directory pins the forensic evaluation datasets used by the SilentWitness accuracy harness (Epic 14). Manifests are committed; the large binary images are gitignored.

## Dataset overview

| dataset_id | Ground truth | LLM risk | Primary evidence |
|---|---|---|---|
| nitroba | password_gated | medium | 56 MB pcap |
| nist-data-leakage | public_pdf | high | ~2 GB E01 |
| nist-hacking-case | public_writeups | very_high | ~6 GB E01 |
| case-trapdoor | synthetic | low | _Epic 15_ |

## Fetch instructions

### Nitroba pcap (~56 MB)

Available from the DFRWS 2010 challenge archive. Drop the binary at `harness/datasets/nitroba.pcap` (gitignored). The CI uses a 24-byte minimal stub committed at `harness/datasets/stubs/nitroba-stub.pcap`.

### NIST Data Leakage (~2 GB)

NIST CFReDS archive — PC E01 + removable-media ISO. Drop at `harness/datasets/pc.E01` and `harness/datasets/removable-media.iso`. Run `recompute_manifest.py nist-data-leakage.manifest.json` after fetch to pin the SHA256.

### NIST Hacking Case (~6 GB)

NIST CFReDS archive — single reassembled EnCase E01. Drop at `harness/datasets/4Dell Latitude CPi.E01`. Run `recompute_manifest.py nist-hacking-case.manifest.json` after fetch.

## Manifest schema

See `schema.py` — Pydantic v2 `DatasetManifest`. Key fields:

- `sha256` — hex digest of the primary evidence file, or the placeholder `<computed-on-fetch>` / `<filled-by-epic-15>` until the binary is locally available.
- `LLM_memorization_risk` — honesty-rubric disclosure. Surfaced in `memorization_risk_note`.
- `expected_investigation_path` — ordered hypothesis-step labels that ground-truth parsers and scorer use.

## Verifying hashes

```bash
# CI gate — only the committed nitroba stub
uv run python harness/datasets/verify_manifest.py --stub-only

# Verify a specific manifest (e.g., after fetching the NIST binaries)
uv run python harness/datasets/verify_manifest.py --manifest harness/datasets/nist-hacking-case.manifest.json

# Strict mode — exit 2 if evidence files missing from disk
uv run python harness/datasets/verify_manifest.py --strict

# Recompute SHA256 after first fetch
uv run python harness/datasets/recompute_manifest.py harness/datasets/nist-hacking-case.manifest.json
```

## Dataset documentation framing

Each manifest encodes the `memorization_risk_note` verbatim for the "Dataset documentation" submission deliverable. The nist-hacking-case manifest in particular carries the full Greg Schardt / Mr. Evil disclosure paragraph, which satisfies Rob T. Lee's honesty rubric requirement for that dataset.
