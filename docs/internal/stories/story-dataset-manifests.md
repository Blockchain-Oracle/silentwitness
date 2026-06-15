# Story — Dataset manifests (Nitroba + NIST Data Leakage + NIST Hacking Case + optional case-trapdoor)

**ID:** story-dataset-manifests
**Epic:** Epic 14 — Accuracy harness + baseline comparison
**Depends on:** story-common-types, story-evidence-registry
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent preparing the accuracy harness
**I want to** ship per-dataset manifest files at `harness/datasets/<dataset>.manifest.json` that pin the canonical SHA256 of every evidence binary, the expected investigation path, the ground-truth status (public PDF / public writeups / password-gated / synthetic), and the LLM-memorization risk band — plus a stub 60 MB Nitroba fixture for CI `dataset-hash-verify` (`CICD_SPEC` §3)
**So that** every downstream harness component (ground-truth parsers, baseline runner, silentwitness runner, scorer, delta report) has a single typed pin for what "this evidence" means — and so the PRD §4 headline metric (time-to-handoff-ready-report) and PRD §6 secondary metrics (pivot count, claim provenance rate, hallucinated-claim count, epistemic-honesty count) are computed against verifiable, hash-pinned datasets per Rob T. Lee's honesty rubric (PRD §9 memorisation-risk disclosure; FR11 accuracy harness; judging criterion IR Accuracy).

---

## File modification map

- `harness/__init__.py` — NEW — empty package marker.
- `harness/datasets/__init__.py` — NEW — empty package marker.
- `harness/datasets/schema.py` — NEW — Pydantic v2 model `DatasetManifest` with fields: `dataset_id: Literal["nitroba", "nist-data-leakage", "nist-hacking-case", "case-trapdoor"]`, `scenario_summary: str` (min_length=80, max_length=800), `download_url: HttpUrl | None`, `sha256: str` (`^[a-f0-9]{64}$`), `size_bytes: int >= 0`, `evidence_files: list[EvidenceFileRecord]` (each: `relative_path: str`, `sha256: str`, `size_bytes: int >= 0`), `expected_investigation_path: list[str]` (ordered hypothesis-step labels), `ground_truth_status: Literal["public_pdf", "public_writeups", "password_gated", "synthetic"]`, `LLM_memorization_risk: Literal["low", "medium", "high", "very_high"]`, `memorization_risk_note: str` (verbatim disclosure per PRD §9), `notes: str | None`. `model_config = ConfigDict(frozen=True, extra="forbid")`. Module ≤120 LOC.
- `harness/datasets/nitroba.manifest.json` — NEW — Nitroba pcap; `sha256: "2b77a9eaefc1d6af163d1ba793c96dbccacb04e6befdf1a0b01f8c67553ec2fb"`, `size_bytes: 56180821` (exact; ~56 MB — the prior `~60 MB` rounding has been replaced with the byte-exact value, since `size_bytes` is verified against `os.path.getsize` by `verify_manifest.py`), `ground_truth_status: "password_gated"` (official solution PDF gated; community writeups are partial), `LLM_memorization_risk: "medium"`. Single `evidence_files` entry: `nitroba.pcap`. `expected_investigation_path` lists the wardrive/wireless-harassment pivot chain at hypothesis-step granularity.
- `harness/datasets/nist-data-leakage.manifest.json` — NEW — NIST CFReDS Data Leakage; PC E01 `md5_legacy: "A49D1254C873808C58E6F1BCD60B5BDE"` retained as a legacy field for cross-reference but the canonical pin is the recomputed `sha256` (placeholder `<computed-on-fetch>` until fetched once and committed); `size_bytes: ~2_000_000_000` (~2.0 GB — the correct size; an earlier draft of this story stated ~20 GB, which is wrong by 10x). `evidence_files`: `pc.E01` + removable-media raw ISO. `ground_truth_status: "public_pdf"` (the parseable `leakage-answers.pdf`). `LLM_memorization_risk: "high"` for scenario summary, `"medium"` for per-artifact paths (PRD §9; evaluation context A.2).
- `harness/datasets/nist-hacking-case.manifest.json` — NEW — NIST CFReDS Hacking Case (Greg Schardt / "Mr. Evil"); the canonical evidence is the **single reassembled EnCase E01 image** at `images/4Dell%20Latitude%20CPi.E01` on the CFReDS archive (NIST publishes a pre-reassembled E01 alongside the legacy multi-part DD split — the E01 is the authoritative single-file form). Use the E01 as the single `evidence_files` entry; the legacy multi-part DD is documented in `notes` only. `download_url` points at `https://cfreds-archive.nist.gov/.../images/4Dell%20Latitude%20CPi.E01` (URL-encoded space). `md5_legacy: "aee4fcd9301c03b3b054623ca261959a"` (reassembled DD legacy hash retained for cross-reference); E01 has a different MD5 — compute on first fetch. `sha256: "<computed-on-fetch>"`; `size_bytes: ~6_000_000_000`. `ground_truth_status: "public_writeups"` (no canonical NIST answer PDF; community writeups at intrinsicode.net + zarat.hatenablog.com). `LLM_memorization_risk: "very_high"` with the PRD §9 honesty paragraph as `memorization_risk_note`.
- `harness/datasets/case-trapdoor.manifest.json` — NEW — synthetic; `dataset_id: "case-trapdoor"`, `sha256: "<filled-by-epic-15>"`, `ground_truth_status: "synthetic"`, `LLM_memorization_risk: "low"`, `download_url: null`, `notes: "Filled by Epic 15 if optional adversary-pair epic ships; harness skips gracefully when sha256 is the placeholder."`.
- `harness/datasets/stubs/nitroba-stub.pcap` — NEW — first 60 MB truncated stub of the real Nitroba pcap for CI dataset-hash-verify; sha256 pinned in `nitroba-stub.manifest.json`.
- `harness/datasets/nitroba-stub.manifest.json` — NEW — manifest for the CI stub; same schema as the full Nitroba manifest but with `notes: "Truncated stub used only for CI dataset-hash-verify per CICD_SPEC §3.dataset-hash-verify"`.
- `harness/datasets/verify_manifest.py` — NEW — CLI: `python harness/datasets/verify_manifest.py [--stub-only] [--manifest <path>]`. Loads every `*.manifest.json` under `harness/datasets/` (or the one passed via `--manifest`), recomputes SHA256 of each file referenced in `evidence_files` that exists on disk (skips missing files unless `--strict`), prints a `rich.table` of `dataset_id | file | expected | actual | match`. Exits 0 on all-match, exits 1 on any mismatch, exits 2 if `--strict` and required files are missing. `--stub-only` restricts to manifests with the substring `-stub` in the filename (used by CI per `CICD_SPEC` §3 `dataset-hash-verify` job which only verifies the 60 MB stub, not the full 20 GB image). ≤180 LOC.
- `harness/datasets/recompute_manifest.py` — NEW — sibling helper that recomputes and rewrites the `sha256` + `size_bytes` of a manifest in-place after a fixture intentionally changes (used by the CICD_SPEC §run-book item for `dataset-hash-verify failed`). ≤120 LOC.
- `harness/datasets/README.md` — NEW — operator doc: how to fetch each dataset (canonical URLs), where to drop the binaries (gitignored evidence root), how the manifest schema works, and the PRD §10 deliverable-5 framing ("Dataset documentation"). ≤200 LOC.
- `tests/integration/test_harness_dataset_manifests.py` — NEW — ≥6 BDD scenarios: every committed manifest parses against `DatasetManifest`; `verify_manifest.py --stub-only` exits 0 against the committed Nitroba stub; `verify_manifest.py` against the full manifests skips missing files when not `--strict`; `verify_manifest.py --strict` against missing full files exits 2; deliberately corrupting the Nitroba stub byte 0 → `verify_manifest.py --stub-only` exits 1 with diff lines; `LLM_memorization_risk` of `nist-hacking-case` is exactly `"very_high"` (PRD §9 disclosure floor); `ground_truth_status` of `nist-data-leakage` is exactly `"public_pdf"`; `dataset_id` round-trips through `model_dump_json` / `model_validate_json` without drift; `case-trapdoor` manifest passes with the `<filled-by-epic-15>` placeholder (does NOT fail the schema — schema accepts the placeholder so optional Epic 15 can fill it later). ≥6 tests pass.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given harness/datasets/nitroba.manifest.json is committed
When  `uv run python -c "import json; from harness.datasets.schema import DatasetManifest; DatasetManifest.model_validate(json.load(open('harness/datasets/nitroba.manifest.json'))); print('ok')"` runs
Then  exit code is 0
And   stdout contains "ok"
And   the parsed model's sha256 equals "2b77a9eaefc1d6af163d1ba793c96dbccacb04e6befdf1a0b01f8c67553ec2fb"

Given harness/datasets/stubs/nitroba-stub.pcap is committed (≤60 MB)
And   harness/datasets/nitroba-stub.manifest.json is committed
When  `uv run python harness/datasets/verify_manifest.py --stub-only` runs
Then  exit code is 0
And   stdout contains "nitroba-stub" and "match=True"

Given harness/datasets/nist-hacking-case.manifest.json is committed
When  the manifest is loaded
Then  LLM_memorization_risk == "very_high"
And   memorization_risk_note contains the substring "writeups"
And   ground_truth_status == "public_writeups"

Given harness/datasets/nist-data-leakage.manifest.json is committed
When  the manifest is loaded
Then  ground_truth_status == "public_pdf"
And   evidence_files contains an entry whose relative_path ends with "pc.E01"

Given harness/datasets/case-trapdoor.manifest.json is committed with sha256="<filled-by-epic-15>"
When  the schema parses the manifest
Then  the manifest validates (placeholder allowed)
And   ground_truth_status == "synthetic"

Given harness/datasets/stubs/nitroba-stub.pcap is mutated (byte 0 flipped)
When  `uv run python harness/datasets/verify_manifest.py --stub-only` runs
Then  exit code is 1
And   stderr contains "sha256 mismatch"

Given tests/integration/test_harness_dataset_manifests.py exists
When  `uv run pytest tests/integration/test_harness_dataset_manifests.py -v` runs
Then  exit code is 0
And   ≥6 tests pass
```

---

## Shell verification

```bash
# Schema parses every committed manifest
uv run python -c "
import json, pathlib
from harness.datasets.schema import DatasetManifest
for p in pathlib.Path('harness/datasets').glob('*.manifest.json'):
    DatasetManifest.model_validate(json.load(open(p)))
    print(p.name, 'ok')
"

# CI dataset-hash-verify gate (CICD_SPEC §3)
uv run python harness/datasets/verify_manifest.py --stub-only
# Must exit 0

# Unit + integration tests
uv run pytest tests/integration/test_harness_dataset_manifests.py -v
# Must show ≥6 passing

# Strict typing
uv run mypy --strict harness/datasets/

# Lint
uv run ruff check harness/datasets/

# File-size guard (≤400 LOC each)
uv run python .pre-commit-hooks/file-size-guard.py \
    harness/datasets/schema.py \
    harness/datasets/verify_manifest.py \
    harness/datasets/recompute_manifest.py

# Coverage floor on harness/
uv run coverage run -m pytest tests/integration/test_harness_dataset_manifests.py
uv run coverage report --include="harness/datasets/*" --fail-under=85
```

---

## Notes for coding agent

- Reference: `docs/architecture.md` §3 (folder layout — `harness/datasets/` houses manifests, binaries gitignored). `docs/PRD.md` §4 (headline metric anchored against datasets), §6 secondary-metrics row on hallucinated-claim count (per CyberSleuth Module III + DFIR-Metric HALL definition), §9 demo-dataset-choice table (Nitroba / Data Leakage / Hacking Case / `case-trapdoor`), §10 deliverable 5 ("Dataset documentation"). `docs/epics.md` Epic 14 DoD. `docs/CICD_SPEC.md` §3 `dataset-hash-verify` job (calls `harness/datasets/verify_manifest.py --stub-only`).
- Reference for hashes + scenarios: `context/evaluation/10-datasets-and-evaluation-methodology.md` §A.1 (Nitroba), §A.2 (NIST Data Leakage), §A.3 (NIST Hacking Case). Quote the SHA256 and MD5 verbatim from §A.1/§A.2/§A.3 — do NOT recompute or paraphrase.
- **Hash pins (from evaluation context):**
  - Nitroba pcap SHA256 = `2b77a9eaefc1d6af163d1ba793c96dbccacb04e6befdf1a0b01f8c67553ec2fb`. Exact size = `56,180,821 bytes` (~56 MB).
  - Nitroba pcap MD5 (legacy) = `9981827f11968773ff815e39f5458ec8`.
  - NIST Data Leakage PC E01 MD5 (legacy) = `A49D1254C873808C58E6F1BCD60B5BDE` (≈**2.0 GB** — not 20 GB; earlier draft was off by 10x); SHA256 = `<computed-on-fetch>` placeholder until the binary is fetched once locally and the manifest is updated via `recompute_manifest.py`.
  - NIST Hacking Case canonical evidence = single reassembled EnCase E01 at `images/4Dell%20Latitude%20CPi.E01` on the CFReDS archive (download_url: `https://cfreds-archive.nist.gov/.../images/4Dell%20Latitude%20CPi.E01`, URL-encoded space). Reassembled DD MD5 (legacy, for cross-reference only) = `aee4fcd9301c03b3b054623ca261959a` (≈6 GB); the E01 SHA256 = `<computed-on-fetch>` placeholder; the E01's own MD5 differs from the DD hash — record both in the manifest's `notes` field after first fetch.
  - `case-trapdoor` SHA256 = `<filled-by-epic-15>` literal placeholder string; schema must accept it. The scorer + runners check for the placeholder and skip the dataset with a clear "Epic 15 not yet shipped" log line.
- The stub fixture (`harness/datasets/stubs/nitroba-stub.pcap`) is a truncated copy of the real Nitroba pcap, **first 60 MB byte-for-byte** (which happens to be the full pcap; if the full pcap is ≤60 MB, the stub == full file). Its SHA256 is fresh — recompute when committing; pin in `nitroba-stub.manifest.json`. CI only verifies the stub per CICD_SPEC §3.
- The full Nitroba pcap, the NIST Data Leakage 20 GB E01, the NIST Hacking Case 6 GB DD, and any `case-trapdoor` binary are **gitignored** (add `harness/datasets/*.pcap`, `harness/datasets/*.E01`, `harness/datasets/*.dd`, `harness/datasets/*.img` to `.gitignore` if not already). Only manifests + the stub are committed.
- `expected_investigation_path` is an ordered list of short hypothesis-step labels (one phrase each, ≤80 chars). For Nitroba: `["identify dorm DHCP lease window", "filter SMTP/HTTP to lilytuckrige@yahoo.com", "extract willselfdestruct.com one-shot URL", "pivot to roster + MAC + dorm room"]`. For NIST Data Leakage: derived from `leakage-answers.pdf` section headings (Iaman Informant pivot chain). For NIST Hacking Case: `["identify primary user profile (Mr. Evil)", "enumerate installed tools (Ethereal/Anonymizer/Cain)", "extract MAC + IP + hostname", "correlate intercepted credentials in pcap"]`.
- `memorization_risk_note` for `nist-hacking-case` MUST contain the PRD §9 verbatim disclosure: "Greg Schardt / Mr. Evil canonical answers (MAC, IP, hostname, email) appear in hundreds of indexed writeups. A passing finding here is not evidence of working forensic capability — it is evidence the model has seen the writeups. The citation + entity gate forces every claim to ground in evidence-present spans rather than regurgitated memory; this dataset demonstrates the gates work, not latent capability." (PRD §9 phrasing.)
- Manifest JSON is human-edited (not auto-generated). Keep keys in stable order: `dataset_id, scenario_summary, download_url, sha256, size_bytes, evidence_files, expected_investigation_path, ground_truth_status, LLM_memorization_risk, memorization_risk_note, notes`. Pydantic v2 round-trip preserves this if fields are declared in this order.
- Use streaming SHA256 (`hashlib.sha256().update(chunk)` in 8 KB blocks per story-evidence-registry) for `verify_manifest.py` — do NOT load multi-GB files into memory.
- `rich.table` for the verify output. Coloring: `[green]match=True[/green]`, `[red]match=False[/red]`, `[yellow]missing (skipped)[/yellow]`.
- DO NOT use the `EvidenceRegistry` from `silentwitness_mcp/evidence/registry.py` here — that registry is per-case (`cases/<case_id>/evidence.json`). The harness manifests are per-dataset, global, committed to the repo. Different concerns.
- DO NOT include the answer key PDF / writeup HTML in this story — that lives in `story-ground-truth-parsers`. This story is binary-evidence pins only.
- Vocabulary discipline (PRD §14): never "court-admissible", never "Ralph Wiggum", never "autonomous SOC". Use "measured hallucination rate", "verifiable against the mounted image", "ground-truth fidelity". The `case-trapdoor` literal name is intentional — keep verbatim.
- Library docs to consult via Context7 BEFORE coding:
  - `pydantic` topic `Literal types and discriminated unions` (the `dataset_id` and status enums are Literal-based for stricter mypy).
  - `pydantic` topic `HttpUrl validator v2` (download_url accepts plain str on input but exports as str via `.unicode_string()`).
- Known pitfalls:
  1. `model_config = ConfigDict(frozen=True, extra="forbid")` interacts with `Literal` — make sure mypy strict passes; if it complains, add `from __future__ import annotations` to the schema module.
  2. The "first 60 MB" Nitroba stub assumption: verify that `nitroba.pcap` is ≈60 MB — if it's smaller, the stub == full file; if larger, truncate to 60 MB on a packet boundary (Wireshark `editcap -c <pkts> in out` or hard truncate is acceptable for hash-pinning, though the truncated file will not parse as a complete pcap — that is fine; CI only checks SHA256, not pcap validity).
  3. The `<computed-on-fetch>` placeholder must be a stable string the schema accepts (regex is `^[a-f0-9]{64}$` for `sha256` — use a Union of the placeholder literal and the hex pattern: declare `sha256: Annotated[str, Field(pattern=r"^([a-f0-9]{64}|<computed-on-fetch>|<filled-by-epic-15>)$")]`). Verify with the BDD test for `case-trapdoor`.
  4. Coverage 85% floor on `harness/*` per PRD §6 NFR + CICD_SPEC §6. The verify CLI is the largest LOC contributor; cover its happy path + the corrupted-stub path + the missing-file path.
