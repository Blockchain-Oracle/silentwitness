# Story — Baseline runner (vanilla Protocol SIFT 2026 in plan mode against pinned evidence)

**ID:** story-baseline-runner
**Epic:** Epic 14 — Accuracy harness + baseline comparison
**Depends on:** story-dataset-manifests
**Indirect deps (covered transitively):** story-evidence-registry, story-common-types
**Note:** audit harmonized this header with `sprint-status.yaml` canonical `depends_on: [dataset-manifests]`. Earlier draft listed `cli-baseline-comparison` which created a cycle (cli-baseline-comparison → scorer + delta-report → this story). YAML is canonical.
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent preparing the head-to-head accuracy harness
**I want to** ship `harness/baseline/runner.py` that clones + installs the vanilla teamdfir Protocol SIFT distribution (`curl -fsSL https://raw.githubusercontent.com/teamdfir/protocol-sift/main/install.sh | bash` — the official one-liner cited in research/protocol-sift-2026/refs) into a throwaway working directory, then drives it in **plan mode** against the same evidence path SilentWitness sees, with `SILENTWITNESS_MODEL` and temperature pinned identically so the comparison is a fair test of the workflow/architecture and not of model parameters
**So that** PRD §4's primary metric (time-to-handoff-ready-report) and PRD §6 secondary metrics (pivot count, claim provenance rate, hallucinated-claim count, epistemic-honesty count) have a verifiable baseline number for the bar chart at demo 4:30–4:50 — measured, not estimated — feeding the scorer (`story-scorer`) and delta report (`story-delta-report`) per epics.md Epic 14 DoD, judging criterion IR Accuracy, and Rob T. Lee's honesty-over-polish rubric (PRD §14 vocabulary discipline).

---

## File modification map

- `harness/baseline/__init__.py` — NEW — empty package marker.
- `harness/baseline/runner.py` — NEW — Python CLI module. Public surface:
  - `class BaselineRunConfig(BaseModel)` — `dataset_id: Literal["nitroba","nist-data-leakage","nist-hacking-case","case-trapdoor"]`, `evidence_path: Path`, `examiner: str` (default `"sansforensics"`), `model: str` (default from env `SILENTWITNESS_MODEL`; falls back to `"anthropic:claude-opus-4-7"`), `temperature: float` (default `0.0` — pinned for determinism), `timeout_seconds: int` (default `1800` = 30 min), `work_dir: Path | None` (None → `tempfile.mkdtemp(prefix="protocol-sift-baseline-")`), `model_config = ConfigDict(frozen=True, extra="forbid")`.
  - `class BaselineRunResult(BaseModel)` — `dataset_id: str`, `started_at: datetime`, `finished_at: datetime`, `elapsed_seconds: float`, `exit_code: int`, `model: str`, `temperature: float`, `commit_sha: str` (head SHA of cloned baseline), `findings: list[BaselineFinding]`, `tool_calls: list[BaselineToolCall]`, `stdout_path: Path`, `stderr_path: Path`, `report_md_path: Path | None`, `notes: list[str]`.
  - `class BaselineFinding(BaseModel)` — `id: str` (e.g., `BF-001`), `text: str`, `cited_artifact_paths: list[str]` (substrings the baseline cites), `cited_at_offset_seconds: float` (offset from start; supplies time-to-first-finding).
  - `class BaselineToolCall(BaseModel)` — `seq: int`, `tool_name: str`, `argv: list[str]`, `elapsed_ms: int`, `exit_code: int`.
  - `def install_baseline(work_dir: Path, *, install_url: str = "https://raw.githubusercontent.com/teamdfir/protocol-sift/main/install.sh") -> Path` — uses `httpx` to fetch the install script to `work_dir/install.sh`, verifies SHA256 against a pinned hash in `harness/baseline/install-script-sha256.txt` (re-pinned on intentional upstream version bump only; CI fails closed on mismatch), runs `bash work_dir/install.sh` with `cwd=work_dir` and `env={**os.environ, "PROTOCOL_SIFT_HOME": str(work_dir / 'protocol-sift')}`. Returns the absolute path of the installed `protocol-sift` directory. Raises `BaselineInstallError` on non-zero exit. Streams install stdout/stderr to `work_dir/install.log`.
  - `def run_baseline(config: BaselineRunConfig) -> BaselineRunResult` — invokes `<work_dir>/protocol-sift/bin/protocol-sift investigate <evidence_path> --plan-mode --model <model> --temperature <temp> --examiner <examiner> --json-events` via `subprocess.Popen(..., stdout=PIPE, stderr=PIPE, text=False)`. Reads stdout line-by-line, parses `BaselineFinding` + `BaselineToolCall` records from the `--json-events` stream (one JSON object per line, type field discriminates), enforces `timeout_seconds`, captures the generated `report.md` under `work_dir/cases/<dataset_id>/report.md`, returns the populated `BaselineRunResult`. The `--plan-mode` flag tells the upstream tool to operate in read-only plan mode (no tool execution against evidence beyond plan-mode reads) per Protocol SIFT 2026 README; if upstream rejects the flag the runner logs a `notes` entry and falls back to the documented `--dry-run` flag.
  - `def main()` — Typer/argparse CLI: `python -m harness.baseline.runner --dataset <id> --evidence <path> [--examiner ...] [--model ...] [--temperature ...] [--out <dir>]`. On success writes the `BaselineRunResult` as `harness/results/<dataset_id>/baseline-<UTC-ISO-timestamp>.json` (atomic rename via story-atomic-io). Exit 0 on success; 2 on config/validation error; 3 on baseline install failure; 4 on timeout; 5 on baseline non-zero exit.
  - Module ≤400 LOC.
- `harness/baseline/install-script-sha256.txt` — NEW — single hex line pinning the upstream `install.sh` SHA256. Re-pinned when the upstream version bump is intentional; CI dataset-hash-verify analog refuses silent drift.
- `harness/results/.gitkeep` — NEW — directory marker so `harness/results/<dataset>/` paths exist before first run.
- `harness/results/.gitignore` — NEW — ignores `*.json` outputs (results are per-run artifacts; only the directory is committed).
- `tests/integration/test_harness_baseline_runner.py` — NEW — ≥6 BDD scenarios using `pytest-mock` + `subprocess` fakes (do NOT actually clone/install over the network in CI):
  - `install_baseline` writes the script + verifies SHA256;
  - `install_baseline` with mismatched SHA256 raises `BaselineInstallError` referencing the pinned file;
  - `run_baseline` parses `--json-events` lines into `BaselineFinding` and `BaselineToolCall` objects;
  - `run_baseline` respects `timeout_seconds` (mock 10s subprocess, config 1s → exit 4);
  - `BaselineRunResult` round-trips through `model_dump_json` / `model_validate_json` without drift;
  - CLI `python -m harness.baseline.runner --dataset nitroba --evidence /tmp/nope` with a missing evidence path exits 2 and stderr names the failing field.
- `pyproject.toml` — UPDATE — add `httpx>=0.27` if not already present (story-fastmcp-server-bootstrap may have added it; check first).

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given harness/baseline/install-script-sha256.txt is committed
And   a fake install.sh with matching SHA256 is staged in a tmp dir
When  `uv run python -c "from pathlib import Path; from harness.baseline.runner import install_baseline; install_baseline(Path('/tmp/sw-bl-test'))"` runs (network mocked)
Then  exit code is 0
And   /tmp/sw-bl-test/install.log exists

Given the pinned install-script SHA256 does NOT match the staged install.sh
When  install_baseline is called
Then  BaselineInstallError is raised
And   the error message references "install-script-sha256.txt"

Given a fake protocol-sift binary emits 3 JSON-event lines of type "finding" and 5 of type "tool_call"
When  run_baseline is invoked against it
Then  result.findings has length 3
And   result.tool_calls has length 5
And   every finding has cited_at_offset_seconds >= 0

Given run_baseline is configured with timeout_seconds=1 against a 10-second subprocess
When  the runner executes
Then  the subprocess is terminated
And   the runner exit code is 4 (timeout sentinel)
And   stderr contains "baseline timeout"

Given `uv run python -m harness.baseline.runner --dataset nitroba --evidence /does/not/exist` runs
Then  exit code is 2
And   stderr contains "evidence_path"

Given a successful run completes
When  the result is serialized
Then  harness/results/nitroba/baseline-<timestamp>.json exists
And   json.load(...) round-trips through BaselineRunResult.model_validate without drift

Given tests/integration/test_harness_baseline_runner.py exists
When  `uv run pytest tests/integration/test_harness_baseline_runner.py -v` runs
Then  exit code is 0
And   ≥6 tests pass
```

---

## Shell verification

```bash
# Tests
uv run pytest tests/integration/test_harness_baseline_runner.py -v
# Must show ≥6 passing

# Strict typing
uv run mypy --strict harness/baseline/

# Lint
uv run ruff check harness/baseline/

# §14 vocab gate clean on changed files
grep -rE "(court-admissible|Ralph Wiggum|autonomous SOC)" harness/baseline/ && exit 1 || true

# File-size guard (≤400 LOC)
uv run python .pre-commit-hooks/file-size-guard.py harness/baseline/runner.py

# Coverage floor 85% on harness/baseline/
uv run coverage run -m pytest tests/integration/test_harness_baseline_runner.py
uv run coverage report --include="harness/baseline/*" --fail-under=85
```

---

## Notes for coding agent

- Reference: `docs/architecture.md` §3 (`harness/baseline/` slot); `docs/PRD.md` §4 (headline metric anchored against vanilla Protocol SIFT baseline on the same case) + §6 (secondary metrics) + §10 deliverable 6 (accuracy report consumes this output); `docs/epics.md` Epic 14 DoD; `docs/CICD_SPEC.md` §6 coverage floor 85% on `harness/*`.
- **Fair-compare discipline (PRD §14):** the whole point of pinning model + temperature is that the demo bar chart compares **workflows**, not provider tuning. The runner MUST pass `SILENTWITNESS_MODEL` verbatim through to the baseline subprocess (export it in the env it inherits) AND pass `--temperature` explicitly. If the baseline does not honour either, log a `notes` entry — do NOT silently swap. The harness scorer (story-scorer) reads `notes` and surfaces this in the delta report.
- **Plan mode rationale:** the baseline runs against the same `/evidence/` mount SilentWitness sees. Plan mode means "no destructive ops, no writes outside `work_dir`." If the upstream baseline does NOT support `--plan-mode`, the runner uses `--dry-run`; if neither exists, the runner raises and logs the situation rather than silently running uncontained — supply-chain hygiene per CICD_SPEC §1.3 (Yotam lens).
- The install script SHA256 pin is the same shape as the dataset-hash-verify pattern from `story-dataset-manifests` — pinned once on intentional upstream version bump, recomputed via a sibling helper (`harness/baseline/repin_install_script.py` — story-out-of-scope, document the pattern in module docstring instead).
- The `--json-events` flag is the standard interop surface for Protocol SIFT 2026 (per research/protocol-sift-2026/CONTEXT.md). One JSON object per line; type field is `"finding" | "tool_call" | "pivot" | "abandon"`. Discriminated union in Pydantic v2 uses `Field(discriminator="type")`.
- DO NOT use real network in tests. Mock `httpx.Client.get` for the install-script fetch. Mock `subprocess.Popen` for the baseline run. The integration test fixtures live in `tests/fixtures/baseline/` (committed sample `--json-events` streams replayed via `pipe-stdin`).
- Output path discipline: `harness/results/<dataset_id>/baseline-<timestamp>.json` is consumed by `story-scorer` and `story-delta-report`. Use ISO-8601 UTC with `Z` suffix (`datetime.now(UTC).isoformat().replace("+00:00", "Z")`); the timestamp format is the join key.
- Vocabulary discipline (PRD §14): never "court-admissible"; never "autonomous SOC"; never "Ralph Wiggum Loop". Use "vanilla Protocol SIFT baseline" verbatim (PRD §4 + §10).
- Library docs to consult via Context7 BEFORE coding:
  - `pydantic` topic `Discriminated unions with Field(discriminator=...)` (the `--json-events` parser uses one).
  - `httpx` topic `Streaming downloads + SHA256 verification` (for the install-script fetch).
  - `subprocess` topic `Popen with timeout + terminate vs kill on SIGTERM` (Python stdlib — `process.terminate()` then `process.kill()` after 5s grace).
- Known pitfalls:
  1. The upstream baseline binary may write to `$HOME/.cache/protocol-sift/` on first invocation — confine via `XDG_CACHE_HOME=<work_dir>/cache` in the subprocess env so concurrent harness runs do not collide.
  2. `bash install.sh | bash` patterns sometimes inherit `set -e` from the calling shell — invoke explicitly as `bash -c 'bash <(curl ...)'` is fragile; do the two-step fetch-then-execute pattern above.
  3. `--plan-mode` may not exist in older baseline versions — probe with `--help | grep plan-mode` before invoking; fall back to `--dry-run`; record the choice in `notes`.
  4. Coverage 85% floor: cover the timeout path + the install-SHA-mismatch path + the missing-evidence-path validation. These are the largest LOC contributors.
