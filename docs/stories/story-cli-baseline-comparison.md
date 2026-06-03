# Story — `silentwitness baseline-comparison <case-id>` (vanilla Protocol SIFT Δ vs SilentWitness)

**ID:** story-cli-baseline-comparison
**Epic:** Epic 12 — CLI (Typer) + Claude Code drop-in config
**Depends on:** story-cli-init, story-cli-investigate, story-investigator-agent
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As an** IR consultant or judge who wants to measure (not estimate) the Δ between vanilla Protocol SIFT and SilentWitness on the same registered evidence
**I want to** run `silentwitness baseline-comparison <case-id>` and have the command (1) run the vanilla Protocol SIFT baseline against the case's evidence, (2) run the SilentWitness investigator, (3) compute the Δ on hallucination rate, precision, recall, and time-to-finding, (4) emit `cases/<case_id>/baseline-delta.json` + a summary `rich.table` to stdout
**So that** the PRD §4 headline metric ("time-to-handoff-ready-report and hallucination-rate-Δ vs vanilla Protocol SIFT must be **measured, not estimated**") is satisfied at the CLI surface — and the demo video bar chart at 4:30–4:50 (PRD §2) has reproducible source data (ux-spec §2.2 `baseline-comparison` flags; PRD §4 headline metric; FR11 accuracy harness).

---

## File modification map

- `src/silentwitness_agent/cli.py` — UPDATE — add `@app.command("baseline-comparison")` function. Signature: `def baseline_comparison(case_id: str = typer.Argument(...), baseline: str = typer.Option("protocol-sift", "--baseline"), out: Path | None = typer.Option(None, "--out"), metrics: str = typer.Option("time,pivots,provenance,hallucinations,epistemic", "--metrics"))`. Body delegates to `cli_commands.baseline_comparison.run(...)`. (~25 LOC delta to cli.py.)
- `src/silentwitness_agent/cli_commands/baseline_comparison.py` — NEW — orchestrates: (a) call into `harness.baseline.runner.run_protocol_sift(case_dir, model, evidence_paths) -> BaselineResult` from Epic 14 (story-baseline-runner); if Epic 14 not yet merged, subprocess-invoke `claude --plan-mode-prompt "find evil"` against the registered evidence and capture stdout/findings count — but the preferred path is the Epic 14 module call; (b) call into `harness.runner.run_silentwitness(case_dir, model, evidence_paths) -> SilentWitnessResult` from Epic 14 (story-silentwitness-runner); (c) compute Δ via `harness.scorer.score_delta(baseline_result, silentwitness_result, ground_truth)`; (d) write `cases/<case_id>/baseline-delta.json` (or `--out`); (e) print summary `rich.table` with one row per metric. The `--metrics` flag is a comma-separated allowlist for which metrics to include. (~200 LOC.)
- `tests/integration/test_cli_baseline_comparison.py` — NEW — ≥9 BDD scenarios: happy-path on a stubbed baseline+silentwitness fixture exits 0 + writes `baseline-delta.json`; the delta JSON has keys `time_to_handoff_seconds_delta`, `pivots_count_delta`, `hallucination_rate_delta`, `precision_delta`, `recall_delta`, `epistemic_honesty_count_delta`; `--metrics time,hallucinations` restricts the output rows; missing ground truth exits 2 with `GROUND_TRUTH_MISSING`; case not found exits 1; `--baseline vanilla` runs the vanilla-claude-code baseline; `--out /tmp/delta.json` honored; rich.table renders the delta with green/red coloring for improvement/regression per metric; Epic 14 module missing exits 2 with a setup hint.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given case mr-evil-001 has registered evidence
And   harness/ground_truth/mr-evil-001.json exists (or a known-case mapping)
And   the Epic 14 baseline-runner and silentwitness-runner modules are importable
When  `uv run silentwitness baseline-comparison mr-evil-001` runs
Then  exit code is 0
And   cases/mr-evil-001/baseline-delta.json is written
And   the JSON has keys time_to_handoff_seconds_delta, pivots_count_delta, hallucination_rate_delta, precision_delta, recall_delta, epistemic_honesty_count_delta
And   stdout contains a rich.table with one row per metric
And   stdout contains a summary line with "Δ measured against Protocol SIFT baseline"

Given the delta JSON shows hallucination_rate_delta = -0.42 (SilentWitness improvement)
When  the summary table renders
Then  the hallucination_rate row has [green]↓ -0.42[/green] (improvement = green)

Given the delta JSON shows time_to_handoff_seconds_delta = +120 (SilentWitness slower)
When  the summary table renders
Then  the time_to_handoff row has [yellow]↑ +120s[/yellow] (regression = yellow, not red)

Given `--metrics time,hallucinations` is passed
When  the command runs
Then  the rich.table shows exactly 2 rows (time_to_handoff, hallucination_rate)
And   the baseline-delta.json still contains all metrics (filter is display-only)

Given `--baseline vanilla` is passed
When  the command runs
Then  the baseline-runner is invoked with mode="vanilla" (vanilla-claude-code, no Protocol SIFT scaffolding)

Given `--out /tmp/custom-delta.json` is passed
When  the command runs
Then  /tmp/custom-delta.json is written
And   cases/mr-evil-001/baseline-delta.json is NOT written

Given harness/ground_truth/mr-evil-001.json does not exist
When  the command runs
Then  exit code is 2
And   stderr contains "GROUND_TRUTH_MISSING — add ground truth at harness/ground_truth/<case_id>.json"

Given the Epic 14 modules are not importable (not yet merged)
When  the command runs
Then  exit code is 2
And   stderr contains "baseline-runner not installed; Epic 14 required"

Given case mr-evil-999 does not exist
When  `silentwitness baseline-comparison mr-evil-999` runs
Then  exit code is 1
And   stderr contains "case 'mr-evil-999' not found"

Given tests/integration/test_cli_baseline_comparison.py exists
When  `uv run pytest tests/integration/test_cli_baseline_comparison.py -v` runs
Then  exit code is 0
And   ≥9 tests pass
```

---

## Shell verification

```bash
uv run pytest tests/integration/test_cli_baseline_comparison.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥9

uv run mypy --strict src/silentwitness_agent/cli_commands/baseline_comparison.py
uv run ruff check src/silentwitness_agent/cli_commands/baseline_comparison.py

[ "$(wc -l < src/silentwitness_agent/cli_commands/baseline_comparison.py)" -le 240 ]

# JSON output is jq-clean
uv run silentwitness baseline-comparison test-case
jq -e '.hallucination_rate_delta' cases/test-case/baseline-delta.json >/dev/null
```

---

## Notes for coding agent

- Source of truth: PRD.md §2 (5-minute demo timing — 4:30–4:50 "Measured Δ vs baseline" with bar chart showing time-to-handoff + hallucination-count + epistemic-honesty); PRD.md §4 (headline metric "time-to-handoff-ready-report and hallucination-rate-Δ vs vanilla Protocol SIFT must be **measured, not estimated** per Rob T. Lee's honesty rubric"); ux-spec.md §2.2 `baseline-comparison` flags (`--baseline <protocol-sift|vanilla>`, `--out`, `--metrics time,pivots,provenance,hallucinations,epistemic`); FR11 (accuracy harness); architecture.md §3 (harness/ structure — `harness/baseline/`, `harness/scorer.py`, `harness/ground_truth/`); Epic 14 stories `story-baseline-runner`, `story-silentwitness-runner`, `story-scorer`, `story-delta-report`.
- This command is the **CLI surface** for the harness. The hard work is in Epic 14 — `harness/baseline/runner.py`, `harness/runner.py` (silentwitness side), `harness/scorer.py`. This story orchestrates the calls and renders the output. If Epic 14 is not yet merged, this story can stub-call the runners and fail with a clear exit-2 setup hint; the integration tests use fixture runners.
- **The baseline runner is a real subprocess call to Claude Code with a Protocol SIFT prompt**, or a vanilla "find evil" prompt without scaffolding. Architecture choice (story-baseline-runner owns the detail):
  - `--baseline protocol-sift`: invokes the published Protocol SIFT prompt template against the registered evidence using `claude` CLI (the SIFT 2026 pre-installed Claude Code v2.0.61 at `/usr/local/bin/claude`).
  - `--baseline vanilla`: vanilla "find evil" prompt with no agent scaffolding, no MCP server.
  - Both are real measurements — no mocked baselines per PRD §4 honesty commitment.
- The SilentWitness side reuses the investigator agent from story-investigator-agent. Same code path as `silentwitness investigate`, but invoked from within the harness with structured result capture.
- Metrics computed (architecture §3 harness/scorer.py + Epic 14 story-scorer):
  - `time_to_handoff_seconds` — seconds from start to report.md reaching DRAFT-with-executive-summary state.
  - `pivots_count` — number of `PIVOT` events in `audit/hypothesis.jsonl`.
  - `precision` — true positives / (true positives + false positives) against ground truth.
  - `recall` — true positives / (true positives + false negatives) against ground truth.
  - `hallucination_rate` — count of claims entity-gate would reject / total claims. Per PRD §4 ("entity NOT in evidence, verifiable by `grep` against the mounted image").
  - `epistemic_honesty_count` — count of explicit "gap" / "did not check" / abstention statements.
- Δ formula: `delta_metric = silentwitness_value - baseline_value` for additive metrics (time, counts); `delta_rate = silentwitness_rate - baseline_rate` for rates. Negative delta on hallucination_rate = improvement (SilentWitness lower); positive delta on precision/recall = improvement (SilentWitness higher).
- Coloring rule for the rich.table:
  - Improvement (lower hallucination, higher precision/recall, higher epistemic) → `[green]`.
  - Regression → `[red]`.
  - Neutral (time within ±10%) → `[yellow]`.
- The `baseline-delta.json` schema:
  ```json
  {
    "case_id": "mr-evil-001",
    "baseline_mode": "protocol-sift",
    "baseline_model": "anthropic:claude-opus-4-7",
    "silentwitness_model": "anthropic:claude-opus-4-7-1m",
    "ground_truth_source": "NIST Hacking Case",
    "metrics": {
      "time_to_handoff_seconds": {"baseline": 3600, "silentwitness": 1200, "delta": -2400},
      "pivots_count": {"baseline": 0, "silentwitness": 4, "delta": +4},
      "precision": {"baseline": 0.72, "silentwitness": 0.91, "delta": +0.19},
      "recall": {"baseline": 0.65, "silentwitness": 0.78, "delta": +0.13},
      "hallucination_rate": {"baseline": 0.18, "silentwitness": 0.0, "delta": -0.18},
      "epistemic_honesty_count": {"baseline": 2, "silentwitness": 11, "delta": +9}
    },
    "generated_at": "2026-06-02T13:48:30Z",
    "silentwitness_version": "0.3.1"
  }
  ```
- Long-running command (5–30 min per side × 2 sides = 10–60 min total). Reuse the rich.progress + SIGINT-safe lifecycle from story-cli-investigate. Document the runtime in the help text: `--help` shows "expect 10–60 min wall time".
- Context7 hints BEFORE coding:
  - `subprocess.run` (stdlib) — for the `claude` CLI subprocess; do NOT use `os.system`. Set `check=False` so non-zero exit from Claude Code is handled gracefully (baseline runs may legitimately exit with errors).
  - `rich.table` — confirm row-coloring API.
- Known pitfalls:
  1. Baseline runs can wedge or run away. Set a hard wall-clock timeout (default 60 min) via `subprocess.run(timeout=3600)`. On timeout, record `baseline_timeout: true` in the JSON and exit 0 (timeout is data, not error).
  2. The baseline-runner module from Epic 14 may not exist when this story is built. Implement defensive `try: from harness.baseline.runner import run_protocol_sift; except ImportError: exit 2 with setup hint`. Document this in the story notes.
  3. Ground truth is per-case. The mapping is `harness/ground_truth/<case_id>.json` OR a manually-specified `--ground-truth <path>` flag (deferred — out of scope for v1 of this story unless trivial).
  4. NIST Hacking Case may be in the training data (PRD §9 honest disclosure). The harness must disclose this in the output JSON's `notes` field.
  5. The `claude` binary at `/usr/local/bin/claude` (per `.raw-design-research/03`) is the SIFT 2026 pre-installed Claude Code v2.0.61. Check `shutil.which("claude")` at runtime; if missing, error with `[red]✗[/red] claude CLI not found at /usr/local/bin/claude`.
- Vocabulary discipline: "measured Δ" not "estimated Δ"; "baseline" not "control"; "Protocol SIFT" verbatim (the team's name). Per PRD §14 + §4 honesty rubric.
