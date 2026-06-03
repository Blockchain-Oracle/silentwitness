# Story — Delta report (Markdown table + matplotlib bar chart PNG per dataset; "baseline hallucinated X concrete things; ours refused" callouts)

**ID:** story-delta-report
**Epic:** Epic 14 — Accuracy harness + baseline comparison
**Depends on:** story-scorer
**Indirect deps (covered transitively):** story-baseline-runner, story-silentwitness-runner, story-dataset-manifests, story-atomic-io, story-common-types
**Note:** audit harmonized this header with `sprint-status.yaml` canonical `depends_on: [scorer]`. YAML is canonical.
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent preparing the demo bar chart at 4:30–4:50 and the PRD §10 deliverable-6 accuracy report
**I want to** ship `harness/delta_report.py` that reads the latest `baseline-*.json` + `silentwitness-*.json` + `scoring-*.json` triple in `harness/results/<dataset>/`, computes pairwise Δ per metric per dataset (precision Δ, recall Δ, hallucination_rate Δ, time-to-first-finding Δ, time-to-handoff-ready-report Δ), renders a Markdown comparison table at `harness/results/<dataset>/delta.md`, generates a matplotlib bar chart PNG at `harness/results/<dataset>/delta.png` (the asset shown on screen at demo 4:30–4:50), and surfaces the top hallucination-example callouts ("baseline hallucinated X concrete things; ours refused") as a verbatim list extracted from the scorer's `hallucination_examples` field
**So that** the demo bar chart is **measured, not estimated** per PRD §4 + Rob T. Lee's honesty rubric, the per-case Δ feeds the accuracy report (PRD §10 deliverable 6) and the README callout (story-readme-polish), and the killer "baseline hallucinated X; ours refused" narrative writes itself from real scoring data (epics.md Epic 14 DoD; PRD §14 vocabulary discipline; FR11 accuracy harness; judging criterion IR Accuracy as primary).

---

## File modification map

- `harness/delta_report.py` — NEW — Python module. Public surface:
  - `class DeltaRow(BaseModel)` — one row per metric: `metric: Literal["precision","recall","hallucination_rate","time_to_first_finding_seconds","time_to_handoff_ready_report_seconds","pivot_count","epistemic_honesty_count"]`, `baseline_value: float | None`, `silentwitness_value: float | None`, `delta: float | None` (silentwitness - baseline; None when either side is None), `direction: Literal["higher_is_better","lower_is_better","neutral"]`, `interpretation: str` (short human sentence: e.g., `"SilentWitness recall +0.20 above baseline (higher is better)"`), `model_config = ConfigDict(frozen=True, extra="forbid")`.
  - `class HallucinationCallout(BaseModel)` — `cited_artifact_path: str`, `side: Literal["baseline","silentwitness"]`, `excerpt: str` (≤200 chars), `evidence_shellout_argv: list[str]`, `evidence_shellout_hits: int` (always 0 for the side that hallucinated; non-zero is impossible by HALLUCINATION definition).
  - `class DeltaReport(BaseModel)` — `dataset_id: str`, `baseline_result_path: Path`, `silentwitness_result_path: Path`, `scoring_result_path: Path`, `generated_at: datetime`, `rows: list[DeltaRow]`, `baseline_hallucinated_callouts: list[HallucinationCallout]` (≤10; from scorer's hallucination_examples filtered to side=baseline), `silentwitness_refused_callouts: list[HallucinationCallout]` (≤10; from the silentwitness side's entity-gate REJECTED envelopes — sourced indirectly via the silentwitness runner's `entity_gate_rejections` and the audit JSONL).
  - `def compute_delta_rows(baseline_metrics, silentwitness_metrics) -> list[DeltaRow]` — emits one `DeltaRow` per metric. Direction lookup: precision/recall higher_is_better; hallucination_rate lower_is_better; time-to-* lower_is_better; pivot_count neutral; epistemic_honesty_count higher_is_better.
  - `def render_markdown(report: DeltaReport) -> str` — renders the canonical Markdown shape:
    ```
    # Δ vs vanilla Protocol SIFT baseline — <dataset_id>

    ## Headline (PRD §4)
    | Metric | Baseline | SilentWitness | Δ | Direction |
    |---|---|---|---|---|
    | time-to-handoff-ready-report (sec) | ... | ... | ... | lower is better |
    | precision | ... | ... | ... | higher is better |
    | recall | ... | ... | ... | higher is better |
    | hallucination_rate | ... | ... | ... | lower is better |
    | pivot count | ... | ... | ... | neutral |
    | epistemic-honesty count | ... | ... | ... | higher is better |

    ## Baseline hallucinated; SilentWitness refused
    The architectural floor in action — these are claims the baseline emitted
    against artifacts that do not exist on the mounted evidence, verifiable
    by re-running the cited shell command:
    - `C:\Tools\HotPlugSpy\dropper.exe` — find /evidence/case-001 -iname 'dropper.exe' → 0 hits
    - ... (≤10 examples)

    SilentWitness rejected the equivalent class of claims at the entity gate
    (count = N from cases/.../audit/findings.jsonl, status=REJECTED).

    ## Footnotes
    - Run anchor: baseline-<ts>, silentwitness-<ts>, scoring-<ts>
    - Methodology: harness/scorer.py classification tree; see PRD §6 for definitions.
    - Memorization-risk disclosure: <copied verbatim from dataset manifest>.
    ```
  - `def render_bar_chart_png(report: DeltaReport, out_path: Path) -> None` — uses matplotlib (pinned `matplotlib==3.10.x`) with `Agg` backend (no display required, CI-friendly) to render a 4-panel grouped bar chart:
    - Panel 1: time-to-handoff-ready-report (seconds) — baseline vs silentwitness
    - Panel 2: hallucination_rate — baseline vs silentwitness
    - Panel 3: precision + recall — baseline vs silentwitness (grouped)
    - Panel 4: epistemic-honesty count — baseline vs silentwitness
    Style: dark-on-light, no gridlines, terminal-ish; explicit axis labels with metric direction (`(lower is better)` / `(higher is better)`); title `"SilentWitness vs vanilla Protocol SIFT — <dataset_id>"`. `figsize=(10, 7)`, `dpi=120`. Writes to `out_path` via `plt.savefig(out_path, bbox_inches='tight')` then `plt.close()`.
  - `def build_delta_report(dataset_id: str, results_dir: Path) -> DeltaReport` — scans `results_dir/<dataset_id>/` for the most recent `baseline-*.json`, `silentwitness-*.json`, `scoring-*.json` (sorted by filename ISO timestamp), loads them, calls `compute_delta_rows`, assembles the `DeltaReport`.
  - `def write_delta_artifacts(report: DeltaReport, results_dir: Path) -> tuple[Path, Path]` — writes `<results_dir>/<dataset_id>/delta.md` (via atomic rename per story-atomic-io) and `<results_dir>/<dataset_id>/delta.png`. Returns `(md_path, png_path)`.
  - `def main()` — argparse CLI: `python -m harness.delta_report --dataset <id> [--results-dir <dir>] [--out-md <path>] [--out-png <path>]`. Exit 0 on success; 2 on config/validation error; 3 if any input result file is missing.
  - Module ≤400 LOC.
- `pyproject.toml` — UPDATE — add `matplotlib>=3.10,<3.11` to `[project.dependencies]` (or `harness` optional-group). Pin the minor per story directive to avoid CI flake on chart-rendering drift across matplotlib minor versions.
- `tests/integration/test_harness_delta_report.py` — NEW — ≥7 BDD scenarios using fixture baseline + silentwitness + scoring JSONs:
  - `compute_delta_rows` emits exactly 7 `DeltaRow` objects (one per metric);
  - `compute_delta_rows` with baseline_value=None produces a row with `delta=None`;
  - `render_markdown` output contains the literal `"## Baseline hallucinated; SilentWitness refused"` heading;
  - `render_markdown` output contains the dataset_id in the H1;
  - `render_bar_chart_png` writes a non-empty PNG with reasonable byte count (≥4 KB, ≤1 MB);
  - `build_delta_report` picks the most recent timestamped file when multiple `baseline-*.json` exist;
  - CLI `python -m harness.delta_report --dataset nitroba --results-dir <fixture>` writes both `delta.md` and `delta.png` under the dataset subdir and exits 0;
  - CLI `python -m harness.delta_report --dataset case-trapdoor --results-dir <empty-fixture>` exits 3 with stderr referencing missing inputs.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given fixture baseline-202606021200Z.json with precision=0.5 and silentwitness-202606021205Z.json with precision=0.85
When  compute_delta_rows is called
Then  the precision row has baseline_value=0.5, silentwitness_value=0.85, delta=+0.35
And   the direction is "higher_is_better"

Given a DeltaReport with 3 baseline_hallucinated_callouts
When  render_markdown is called
Then  the output contains the literal substring "## Baseline hallucinated; SilentWitness refused"
And   each callout's cited_artifact_path appears in the output
And   each callout's evidence_shellout_argv joined with spaces appears in the output

Given a DeltaReport for dataset_id="nitroba"
When  render_bar_chart_png writes to /tmp/test_delta.png
Then  /tmp/test_delta.png exists
And   os.path.getsize("/tmp/test_delta.png") between 4000 and 1_000_000
And   the file's first 8 bytes are b"\x89PNG\r\n\x1a\n"

Given harness/results/nitroba/ contains baseline-202606021200Z.json and baseline-202606021800Z.json
When  build_delta_report runs
Then  the report's baseline_result_path ends with "baseline-202606021800Z.json" (most recent wins)

Given `uv run python -m harness.delta_report --dataset case-trapdoor --results-dir tests/fixtures/empty-results/` runs
Then  exit code is 3
And   stderr contains "no baseline result found"

Given a successful CLI invocation against the fixture
When  the command completes
Then  delta.md exists in the dataset subdir
And   delta.png exists in the dataset subdir
And   delta.md contains the literal "Δ vs vanilla Protocol SIFT baseline"

Given tests/integration/test_harness_delta_report.py exists
When  `uv run pytest tests/integration/test_harness_delta_report.py -v` runs
Then  exit code is 0
And   ≥7 tests pass
```

---

## Shell verification

```bash
# Tests
uv run pytest tests/integration/test_harness_delta_report.py -v

# Strict typing
uv run mypy --strict harness/delta_report.py

# Lint
uv run ruff check harness/delta_report.py

# §14 vocab gate clean
grep -rE "(court-admissible|Ralph Wiggum|autonomous SOC)" harness/delta_report.py && exit 1 || true

# File-size guard (≤400 LOC)
uv run python .pre-commit-hooks/file-size-guard.py harness/delta_report.py

# Coverage floor 85% on harness/delta_report.py
uv run coverage run -m pytest tests/integration/test_harness_delta_report.py
uv run coverage report --include="harness/delta_report*" --fail-under=85

# Smoke: matplotlib import path uses Agg backend (no display required in CI)
uv run python -c "import matplotlib; matplotlib.use('Agg'); from harness.delta_report import render_bar_chart_png; print('ok')"
```

---

## Notes for coding agent

- Reference: `docs/architecture.md` §3 folder layout (`harness/` slot); `docs/PRD.md` §2 demo arc 4:30–4:50 (bar chart on screen) + §4 headline metric + §6 secondary metrics (every metric in the table maps to a `DeltaRow`) + §10 deliverable 6 (accuracy report consumes this Markdown); `docs/epics.md` Epic 14 DoD ("emits Δ JSON + Markdown report"); `docs/CICD_SPEC.md` §6 coverage 85% on `harness/*`.
- **Matplotlib pin discipline (story directive):** `matplotlib>=3.10,<3.11`. Minor-version pin because chart rendering output varies across minor matplotlib versions (anti-alias subtly differs; CI snapshot fragility); pinning the minor keeps the bar chart byte-stable enough for the README screenshot embed and the demo recording.
- **`Agg` backend mandatory:** `matplotlib.use('Agg')` BEFORE any pyplot import. CI has no display server. SIFT 2026 has X11 but the harness runs headless in containers. Same constraint applies to local dev.
- **Markdown shape locked above:** the `## Baseline hallucinated; SilentWitness refused` section IS the killer narrative beat. The render MUST surface verbatim `cited_artifact_path` + the exact `find` argv that returned 0 hits — this is the "reproducible by hand" property the IR Accuracy criterion rewards. Cite the scorer's `evidence_shellout_argv` field verbatim — do NOT paraphrase.
- **Pairing heuristic:** `build_delta_report` picks the MOST RECENT timestamped triple per dataset. Files are named `baseline-<ISO-Z>.json` / `silentwitness-<ISO-Z>.json` / `scoring-<ISO-Z>.json`; sort by filename string (lexicographic ISO-8601 sort is correct), take the tail. If counts mismatch (e.g., 3 baselines but only 1 silentwitness), use the most recent silentwitness + the closest-earlier baseline + the most recent scoring whose `commit_sha` matches both — log a `notes` entry on the report when the SHAs disagree.
- **`baseline_hallucinated_callouts` source:** the scorer's `hallucination_examples` filtered to `side="baseline"`, capped at 10. These are the demo-video bullet points; they need to be specific (`"C:\Tools\HotPlugSpy\BinHex\dropper-v3.exe"`) not generic (`"some file"`). The scorer's ranking (length descending) already surfaces specificity.
- **`silentwitness_refused_callouts` source:** the silentwitness side does NOT log HALLUCINATIONS (that's the whole point — the entity gate catches them). Instead, surface the entity gate REJECTED envelopes from `cases/<id>/audit/findings.jsonl` filtered to `status=="REJECTED"` AND `reason` containing `"entity"`. Build a `HallucinationCallout` for each — `evidence_shellout_hits=0` by construction (the entity gate rejected because the cited entity was NOT in any cited span, which by transitivity means it would have failed the same `find` check). These rows are what the demo voices over at 4:50–5:00: "the architectural floor at work — these claims never reached the report because the server refused them."
- **Bar chart styling:** dark-on-light, axis labels with direction annotation, no gridlines, no legend chrome. Pattern reference: the rich live terminal aesthetic (ux-spec §2.3) ported to a static PNG. NOT a Material/Bootstrap chart. Two colors only: a desaturated red for baseline, a desaturated green for silentwitness (`#d96c5c` + `#7fb069` from ux-spec §3.5 HUD tokens — keeps the SilentWitness visual brand consistent across CLI/HUD/charts).
- DO NOT shell out to `find` from the delta report — the scorer already did. The delta report just consumes the scorer's `FindingClassification` rows.
- The `delta.md` file is consumed by `story-accuracy-report-writeup` and by `story-readme-polish` (the README's "Accuracy report" pointer). Locking the H1 shape (`# Δ vs vanilla Protocol SIFT baseline — <dataset_id>`) lets the accuracy-report writeup grep across `harness/results/*/delta.md` to assemble the per-dataset summary.
- Vocabulary discipline (PRD §14): never "court-admissible"; never "autonomous SOC"; never "Ralph Wiggum Loop". Use "vanilla Protocol SIFT baseline" verbatim. Use "measured Δ" not "estimated Δ".
- Library docs to consult via Context7 BEFORE coding:
  - `matplotlib` topic `Agg backend headless rendering + savefig + close figure` (the lifecycle is `fig, axes = plt.subplots(...)` → plot → `fig.savefig(...)` → `plt.close(fig)`; forgetting `close` leaks memory in long-running CI).
  - `matplotlib` topic `subplots grouped bar chart with categorical x-axis v3.10` (the API has settled by 3.10 but the offset-bar pattern still requires hand-computing x positions).
  - `pydantic` topic `model_validate + json.load + datetime UTC parsing` (the ISO-Z timestamps parse via `datetime.fromisoformat` after `Z` → `+00:00` substitution; Python 3.11+ accepts `Z` natively but pin via shim for 3.12 strict).
- Known pitfalls:
  1. Matplotlib import time is ~600 ms cold — the CLI startup is non-trivial. Acceptable for a per-run harness invocation; do NOT call `import matplotlib.pyplot` at module top level — defer inside `render_bar_chart_png` so the module imports cheap.
  2. PNG file determinism: matplotlib PNG metadata embeds a timestamp by default — pass `metadata={"Software": "silentwitness-delta-report"}` and `pil_kwargs={"optimize": True}` to keep byte-stability minus the timestamp drift; do NOT assert exact byte equality in tests (size range only).
  3. Empty results dir: `build_delta_report` against an empty dir must exit 3 cleanly with a clear stderr message — do NOT raise an uncaught `IndexError` from `sorted(...)[-1]` on empty list.
  4. None-handling in Δ math: `time_to_handoff_ready_report_seconds` can be None on either side (the runner did not reach handoff-ready). `DeltaRow.delta` is None in that case; the Markdown renderer shows `"n/a"` for None values.
  5. Coverage 85% floor: cover the None-delta path, the empty-results path, the multi-baseline-pick-most-recent path, the SHA-mismatch notes path, the PNG-write path.
