# Story — Scorer (per-finding classification + metrics: precision / recall / hallucination_rate / time-to-first-finding / time-to-handoff-ready-report)

**ID:** story-scorer
**Epic:** Epic 14 — Accuracy harness + baseline comparison
**Depends on:** story-ground-truth-parsers, story-baseline-runner, story-silentwitness-runner
**Indirect deps (covered transitively):** story-dataset-manifests, story-evidence-registry, story-common-types
**Note:** audit harmonized this header with `sprint-status.yaml` canonical `depends_on: [ground-truth-parsers, baseline-runner, silentwitness-runner]`. YAML is canonical.
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent producing the head-to-head accuracy numbers
**I want to** ship `harness/scorer.py` that takes a baseline result JSON, a SilentWitness result JSON, and the dataset's ground-truth list, classifies every finding on each side as `TRUE_POSITIVE | FALSE_POSITIVE | HALLUCINATION | FALSE_NEGATIVE`, then computes the metrics PRD §4 and §6 require (precision, recall, hallucination_rate, time-to-first-finding, time-to-handoff-ready-report), with the HALLUCINATION classification grounded in a real `find`/`grep` shell-out against the mounted evidence so the verdict is **verifiable**, not estimated
**So that** the demo bar chart at 4:30–4:50 and the accuracy report (PRD §10 deliverable 6) carry numbers Rob T. Lee's honesty rubric accepts — every HALLUCINATION verdict is reproducible by re-running the same `find -iname` against the same mount, and every FALSE_NEGATIVE is reproducible by looking up the ground-truth ID in the parser output (per epics.md Epic 14 DoD; PRD §14 vocabulary discipline; FR11 accuracy harness; judging criterion IR Accuracy as primary).

---

## File modification map

- `harness/scorer.py` — NEW — Python module. Public surface:
  - `class FindingClassification(BaseModel)` — `finding_id: str`, `side: Literal["baseline","silentwitness"]`, `classification: Literal["TRUE_POSITIVE","FALSE_POSITIVE","HALLUCINATION","FALSE_NEGATIVE"]`, `matched_ground_truth_id: str | None`, `reason: Literal["CITED_ARTIFACT_PRESENT_AND_MATCHED","CITED_ARTIFACT_PRESENT_BUT_GT_MISS","CITED_ARTIFACT_NOT_PRESENT","NO_FINDING_FOR_GT"]`, `evidence_shellout_argv: list[str] | None` (the exact `find` or `grep` argv used to verify; reproducible), `evidence_shellout_hits: int | None`, `model_config = ConfigDict(frozen=True, extra="forbid")`.
  - `class ScoringMetrics(BaseModel)` — `dataset_id: str`, `side: Literal["baseline","silentwitness"]`, `true_positives: int`, `false_positives: int`, `hallucinations: int`, `false_negatives: int`, `precision: float` (TP / (TP + FP + HALL); HALL counts as FP for precision penalty per CyberSleuth Module III + DFIR-Metric HALL definition cited in PRD §6), `recall: float` (TP / (TP + FN)), `hallucination_rate: float` (HALL / (TP + FP + HALL)), `time_to_first_finding_seconds: float | None`, `time_to_handoff_ready_report_seconds: float | None`, `total_findings_emitted: int`.
  - `class ScoringReport(BaseModel)` — `dataset_id: str`, `commit_sha: str` (HEAD SHA at scoring time), `scored_at: datetime`, `baseline: ScoringMetrics`, `silentwitness: ScoringMetrics`, `classifications: list[FindingClassification]`, `notes: list[str]`, `hallucination_examples: list[HallucinationExample]` (≤10 ranked by string length of the cited artifact — for the delta report's "baseline hallucinated X concrete things; ours refused" callout).
  - `class HallucinationExample(BaseModel)` — `side`, `finding_id`, `cited_artifact_path: str`, `evidence_shellout_argv: list[str]`, `evidence_shellout_hits: int`, `excerpt: str` (≤200 chars).
  - `def verify_artifact_present_in_evidence(cited_substring: str, evidence_root: Path) -> tuple[bool, list[str], int]` — runs `find <evidence_root> -iname '<basename(cited_substring)>'` via `subprocess.run(..., capture_output=True, text=True, timeout=60)`, returns `(found, argv, hit_count)`. If the basename is empty or contains glob metacharacters that `find` rejects, falls back to `grep -r -l --binary-files=text -F '<cited_substring>' <evidence_root>` for substring search across mounted files. Read-only operations against the `ro,noexec,nosuid` mount — confirms PRD §6 NFR mount constraints.
  - `def classify_finding(finding: dict, ground_truth: list[GroundTruthFinding], evidence_root: Path, side: str) -> FindingClassification` — runs the decision tree:
    1. For each `cited_artifact_path` in the finding, call `verify_artifact_present_in_evidence`. If ALL cited paths return `hit_count == 0` → `HALLUCINATION` with `reason=CITED_ARTIFACT_NOT_PRESENT`.
    2. Else for each ground-truth finding, check if ANY of its `expected_artifact_substrings` appears either in `finding["text"]` OR in `finding["cited_artifact_paths"]` joined. First match → `TRUE_POSITIVE` with `matched_ground_truth_id` set.
    3. Else (artifact present but no GT match) → `FALSE_POSITIVE` with `reason=CITED_ARTIFACT_PRESENT_BUT_GT_MISS`.
  - `def compute_false_negatives(ground_truth: list[GroundTruthFinding], side_findings: list[dict]) -> list[FindingClassification]` — for every GT finding whose `expected_artifact_substrings` does NOT appear in any of the side's findings, emit a `FindingClassification(finding_id=f"FN-{gt.id}", side=side, classification="FALSE_NEGATIVE", matched_ground_truth_id=gt.id, reason="NO_FINDING_FOR_GT")`.
  - `def score_run(baseline_result_path: Path, silentwitness_result_path: Path, dataset_id: str, evidence_root: Path) -> ScoringReport` — top-level orchestrator. Loads both result JSONs, looks up the ground-truth parser by dataset_id (calls `parse()` from the matching module under `harness.ground_truth.*`), runs classification on each side, computes metrics, returns the populated `ScoringReport`.
  - `def main()` — argparse CLI: `python -m harness.scorer --dataset <id> --baseline <path> --silentwitness <path> --evidence <path> [--out <dir>]`. Writes `harness/results/<dataset_id>/scoring-<UTC-ISO-timestamp>.json` via atomic rename. Exit 0 on success; 2 on config/validation error; 3 if either input result file is missing; 4 if ground truth returns empty for the dataset (refuses to score against nothing).
  - Module ≤400 LOC.
- `tests/integration/test_harness_scorer.py` — NEW — ≥10 BDD scenarios using synthetic baseline + silentwitness + ground-truth fixtures + a mock `/evidence/case-001/` directory:
  - **HALLUCINATION verdict (the critical scoring path):** given a finding citing `C:\Tools\NotReal.exe`, when scorer shells `find /evidence/case-001 -iname 'NotReal.exe'`, then 0 hits → marked HALLUCINATION with `reason="CITED_ARTIFACT_NOT_PRESENT"` and `evidence_shellout_hits == 0`.
  - given a finding citing `C:\Program Files\Ethereal\ethereal.exe` and the mock evidence dir contains a file named `ethereal.exe`, then the classification is TRUE_POSITIVE (if matched) or FALSE_POSITIVE (if no GT match) — NEVER HALLUCINATION.
  - given a GT finding with `expected_artifact_substrings=["00:02:B3:DD:00:A2"]` and the side has a finding whose text contains that substring, then classification is TRUE_POSITIVE with `matched_ground_truth_id` set.
  - given a GT finding NOT covered by any side finding, then `compute_false_negatives` yields one `FALSE_NEGATIVE` row.
  - `precision = TP / (TP + FP + HALL)` with HALL=2, FP=1, TP=7 → 7/10 = 0.7;
  - `recall = TP / (TP + FN)` with TP=7, FN=3 → 0.7;
  - `hallucination_rate = HALL / (TP + FP + HALL)` with HALL=2, FP=1, TP=7 → 0.2;
  - `time_to_first_finding_seconds` is passed through verbatim from each side's result JSON;
  - `time_to_handoff_ready_report_seconds` is passed through verbatim from each side's result JSON (None when the side did not reach handoff-ready state);
  - CLI `python -m harness.scorer --dataset nitroba --baseline missing.json --silentwitness x.json --evidence /tmp/x` exits 3 with stderr mentioning the missing baseline file;
  - CLI `python -m harness.scorer --dataset case-trapdoor --baseline b.json --silentwitness s.json --evidence /tmp/x` exits 4 when ground truth is empty (case-trapdoor not synthesised).
  - Coverage target: 90% on `harness/scorer.py` per story directive (critical scoring dependency).

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a side finding cites C:\Tools\NotReal.exe
And   the mock evidence directory /evidence/case-001 contains no file matching "NotReal.exe"
When  classify_finding runs and verify_artifact_present_in_evidence shells `find /evidence/case-001 -iname 'NotReal.exe'`
Then  shellout_hits == 0
And   the classification is HALLUCINATION
And   the reason is "CITED_ARTIFACT_NOT_PRESENT"
And   evidence_shellout_argv begins with ["find", "/evidence/case-001", "-iname"]

Given a side finding cites C:\Program Files\Ethereal\ethereal.exe
And   the mock evidence dir contains /evidence/case-001/Program Files/Ethereal/ethereal.exe
And   a GT finding has expected_artifact_substrings=["ethereal.exe"]
When  classify_finding runs
Then  the classification is TRUE_POSITIVE
And   matched_ground_truth_id matches the GT's id

Given a GT finding with id="GT-NHC-005" and expected_artifact_substrings=["00:02:B3:DD:00:A2"]
And   no side finding contains that substring
When  compute_false_negatives is called
Then  one FALSE_NEGATIVE row is emitted with matched_ground_truth_id="GT-NHC-005"

Given baseline classifications TP=7, FP=1, HALL=2 and FN=3
When  ScoringMetrics is computed
Then  precision == 0.7
And   recall == 0.7
And   hallucination_rate == 0.2

Given `uv run python -m harness.scorer --dataset case-trapdoor --baseline b.json --silentwitness s.json --evidence /tmp/x` runs (case-trapdoor GT empty)
Then  exit code is 4
And   stderr contains "ground truth returned empty"

Given tests/integration/test_harness_scorer.py exists
When  `uv run pytest tests/integration/test_harness_scorer.py -v` runs
Then  exit code is 0
And   ≥10 tests pass

Given coverage is measured on harness/scorer.py
When  `uv run coverage report --include="harness/scorer*" --fail-under=90` runs
Then  exit code is 0
```

---

## Shell verification

```bash
# Tests
uv run pytest tests/integration/test_harness_scorer.py -v
# Must show ≥10 passing

# Strict typing
uv run mypy --strict harness/scorer.py

# Lint
uv run ruff check harness/scorer.py

# §14 vocab gate clean
grep -rE "(court-admissible|Ralph Wiggum|autonomous SOC)" harness/scorer.py && exit 1 || true

# File-size guard (≤400 LOC)
uv run python .pre-commit-hooks/file-size-guard.py harness/scorer.py

# Coverage floor 90% on harness/scorer.py (story-specific critical floor)
uv run coverage run -m pytest tests/integration/test_harness_scorer.py
uv run coverage report --include="harness/scorer*" --fail-under=90
```

---

## Notes for coding agent

- Reference: `docs/architecture.md` §3 folder layout (`harness/scorer.py` slot); `docs/PRD.md` §4 (headline metric tied to time-to-handoff-ready-report) + §6 (hallucinated-claim count definition cites CyberSleuth Module III + DFIR-Metric HALL — this story implements that definition machine-readably) + §10 deliverable 6 (accuracy report); `docs/epics.md` Epic 14 DoD; `docs/CICD_SPEC.md` §6 coverage floor (this story raises to 90% locally — the scorer is the load-bearing scoring dependency).
- **HALLUCINATION verdict is the keystone:** the whole architectural pitch (PRD §2 3:30–4:00 demo moment) is that hallucinated findings are rejected at the gate. The scorer here measures the **residual** — claims that escaped the gate. The verification mechanism MUST be a real shell-out to `find` or `grep` against the mounted evidence so the verdict is reproducible by hand. This is the PRD §6 definition verbatim: "count of claims that escaped and would have been flagged by an offline `grep`-the-mounted-image verifier."
- **Mount safety:** the evidence root is `ro,noexec,nosuid` (PRD §6 NFR + architecture.md §4.11 — mount validation). `find` and `grep` are explicitly safe (no write, no exec). DO NOT shell out to anything that mutates the mount. Confirm via `os.statvfs(evidence_root).f_flag & os.ST_RDONLY` before running — if the mount is writable, log a notes entry but proceed (developer machine vs CI; the safety is per-PRD on the deployed system).
- **Precision formula** treats HALLUCINATION as worse-than-FP (HALL counts AGAINST precision in the denominator): `precision = TP / (TP + FP + HALL)`. The PRD §6 row on "hallucinated-claim count" is the architectural-floor metric — high HALL rate on the baseline + ~0 HALL on SilentWitness is the demo's killer number. Rationale: a FP is "right shape, wrong answer"; a HALLUCINATION is "cites something that doesn't exist." The penalty asymmetry encodes Rob T. Lee's honesty rubric.
- **`time_to_first_finding_seconds` + `time_to_handoff_ready_report_seconds`** are passed through verbatim from the runner result JSONs. The scorer does NOT recompute them — the runners own those definitions. Document this in the module docstring so the delta report knows.
- **`hallucination_examples` ranking:** sort by `len(cited_artifact_path)` descending, take top 10. This surfaces the most-specific hallucinations (e.g., `"C:\Tools\HotPlugSpy\BinHex\dropper-v3.exe"`) for the delta report's narrative callout.
- The scorer is **deterministic given the same inputs + same evidence mount**. Pin via committing the `harness/results/<dataset_id>/scoring-<timestamp>.json` artifact along with the result inputs — re-running on a different evidence mount may produce different shellout_hits, but the classification verdict for HALLUCINATION is stable (0 hits remains 0 hits regardless of which mount).
- DO NOT mock `subprocess.run` at the **scorer** boundary in tests — use real `find` + `grep` against a tests/fixtures/mock-evidence/ directory tree. The whole point of the HALLUCINATION verdict is that it shells out to real `find`. Mocking defeats the test. The mock-evidence directory contains 5–10 fake artifact files (`ethereal.exe`, `cmd.exe`, `notepad.exe`, etc.) — small, committed.
- DO mock the **ground-truth parser** boundary in tests — pass a synthetic `list[GroundTruthFinding]` directly into `classify_finding` / `score_run`. The ground-truth-parsers story owns its own integration.
- Output path discipline: `harness/results/<dataset_id>/scoring-<timestamp>.json` joins with `baseline-<timestamp>.json` + `silentwitness-<timestamp>.json` in the same directory — the delta report (story-delta-report) pairs by directory listing + closest-pair-by-timestamp heuristic.
- Vocabulary discipline (PRD §14): never "court-admissible"; never "autonomous SOC"; never "Ralph Wiggum Loop". Use "HALLUCINATION verdict reproducible by re-running the cited shellout against the mount". Use "claim provenance rate" (PRD §6 row) when the scorer ever surfaces the related metric.
- Library docs to consult via Context7 BEFORE coding:
  - `pydantic` topic `Literal types + discriminator + computed_field` (the metrics class can use `computed_field` for precision/recall/hallucination_rate so they auto-derive from TP/FP/HALL/FN counts — optional).
  - `subprocess` topic `run with capture_output + timeout + text=True` (Python stdlib).
- Known pitfalls:
  1. `find -iname` on a path containing spaces or non-ASCII — pass the basename as a single argv element, not a shell-interpolated string. `subprocess.run(["find", str(root), "-iname", basename], ...)` not `subprocess.run(f"find {root} -iname {basename}", shell=True)`.
  2. Basenames with `[` or `?` or `*` confuse `find -iname` glob handling — detect via `re.search(r'[*?\[\]]', basename)` and route through `grep -r -F` (literal-string mode) instead.
  3. Very large evidence trees (NIST Hacking Case is 6 GB; Data Leakage is 20 GB) — `find` on a hot cache is fast; on cold cache it can hang. Cap each shellout at `timeout=60s` and treat timeout as `(False, argv, -1)` with a `notes` entry — do NOT call timeout HALLUCINATION (insufficient evidence to classify either way).
  4. Coverage floor 90%: cover the timeout path, the glob-metacharacter fallback path, the empty-cited-paths edge case (finding with no `cited_artifact_paths` → HALLUCINATION by definition, the agent claimed something with zero provenance), the multi-cited-path AND-vs-OR logic (HALLUCINATION only if ALL cited paths return 0 hits).
