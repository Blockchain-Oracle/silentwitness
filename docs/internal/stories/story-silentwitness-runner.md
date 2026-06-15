# Story — SilentWitness runner (invoke the investigator against pinned evidence with the same model + temp as baseline)

**ID:** story-silentwitness-runner
**Epic:** Epic 14 — Accuracy harness + baseline comparison
**Depends on:** story-investigator-agent, story-dataset-manifests
**Indirect deps (covered transitively):** story-investigator-hooks, story-hypothesis-stack, story-evidence-registry, story-common-types
**Note:** audit harmonized this header with `sprint-status.yaml` canonical `depends_on: [investigator-agent, dataset-manifests]`. Earlier draft listed `baseline-runner` and `cli-investigate` — those are siblings (no real dependency). YAML is canonical.
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent preparing the head-to-head accuracy harness
**I want to** ship `harness/silentwitness/runner.py` that invokes the SilentWitness reference investigator agent against the same evidence path the baseline runner sees, with `SILENTWITNESS_MODEL` + temperature pinned identically, and captures the full structured trace (findings, hypothesis events, pivots, MCP tool calls, generated `report.md`) into a single JSON artifact at `harness/results/<dataset>/silentwitness-<timestamp>.json`
**So that** the scorer (`story-scorer`) has a symmetric input shape on both sides of the bar chart at demo 4:30–4:50 — same evidence, same model, same temperature, different workflow — and the PRD §4 headline metric (time-to-handoff-ready-report) plus PRD §6 secondary metrics (pivot count, claim provenance rate, hallucinated-claim count, epistemic-honesty count) are measured against the SilentWitness side fairly per Rob T. Lee's honesty rubric (PRD §14 vocabulary; FR11 accuracy harness; judging criterion IR Accuracy).

---

## File modification map

- `harness/silentwitness/__init__.py` — NEW — empty package marker.
- `harness/silentwitness/runner.py` — NEW — Python module. Public surface MIRRORS `story-baseline-runner` so the scorer can treat both result files via the same join logic:
  - `class SilentWitnessRunConfig(BaseModel)` — `dataset_id: Literal["nitroba","nist-data-leakage","nist-hacking-case","case-trapdoor"]`, `evidence_path: Path`, `examiner: str` (default `"sansforensics"`), `model: str` (default from env `SILENTWITNESS_MODEL`; fallback `"anthropic:claude-opus-4-7"`), `temperature: float` (default `0.0`), `timeout_seconds: int` (default `1800`), `case_dir: Path | None` (None → `tempfile.mkdtemp(prefix="silentwitness-harness-")`), `model_config = ConfigDict(frozen=True, extra="forbid")`.
  - `class SilentWitnessRunResult(BaseModel)` — `dataset_id: str`, `started_at: datetime`, `finished_at: datetime`, `elapsed_seconds: float`, `exit_code: int`, `model: str`, `temperature: float`, `commit_sha: str` (HEAD SHA of THIS repo at run time), `findings: list[SwFinding]` (sourced from `cases/<id>/findings.json`), `hypothesis_events: list[SwHypothesisEvent]` (sourced from `cases/<id>/audit/hypothesis.jsonl`), `pivots: list[SwHypothesisEvent]` (subset of hypothesis_events with `transition == "pivot"`), `tool_calls: list[SwToolCall]` (sourced from `cases/<id>/audit/<backend>.jsonl` across all backend files), `critic_verdicts: list[SwCriticVerdict]` (sourced from `cases/<id>/audit/critic.jsonl`), `report_md_path: Path | None`, `report_md_sha256: str | None`, `entity_gate_rejections: int` (count of rejected `record_observation` calls from envelope `status == "REJECTED"`), `epistemic_honesty_count: int` (count of items under report's `## Gaps` section — counted by tail-parsing the rendered `report.md`), `time_to_first_finding_seconds: float | None`, `time_to_handoff_ready_report_seconds: float | None` (defined as: the moment `report.md` first contains a non-empty `## Executive Summary` section), `notes: list[str]`.
  - `class SwFinding(BaseModel)` — `id: str` (the `F-...` from findings.json), `text: str` (observation + interpretation merged), `cited_audit_ids: list[str]`, `cited_artifact_paths: list[str]` (lifted from the observation's entity gate match list), `status: Literal["STAGED","APPROVED","REJECTED","ARCHIVED"]`, `staged_at_offset_seconds: float`.
  - `class SwHypothesisEvent(BaseModel)` — passthrough of the `HypothesisEvent` JSONL row shape from `story-hypothesis-types`: `event_id`, `hypothesis_id`, `transition` (form|dispatch|confirm|pivot|abandon), `reason`, `timestamp`.
  - `class SwToolCall(BaseModel)` — passthrough of the envelope from `story-response-envelope`: `audit_id`, `tool_name`, `result_sha256`, `elapsed_ms`, `status`.
  - `class SwCriticVerdict(BaseModel)` — `verdict: Literal["APPROVED","CHALLENGE","REJECT"]`, `target_finding_id: str`, `reason: str`, `timestamp`.
  - `def run_silentwitness(config: SilentWitnessRunConfig) -> SilentWitnessRunResult` — invokes `silentwitness investigate <case_id> --evidence <evidence_path> --examiner <examiner> --auto-approve` as a subprocess with env `SILENTWITNESS_MODEL=<model>`, `SILENTWITNESS_TEMPERATURE=<temp>`, `SILENTWITNESS_CASE_DIR=<case_dir>`. Streams stdout to `case_dir/.harness-stdout.log`, enforces `timeout_seconds`, on completion reads `case_dir/findings.json`, every `case_dir/audit/*.jsonl`, the rendered `case_dir/report.md`, computes derived metrics (`time_to_first_finding_seconds`, `time_to_handoff_ready_report_seconds`, `entity_gate_rejections` count, `epistemic_honesty_count` count of `## Gaps` bullets, `report_md_sha256` via streaming `hashlib.sha256`), returns the populated `SilentWitnessRunResult`. The `--auto-approve` flag (ux-spec §2.4 — explicitly available for benchmarks per "auto-approve mode for benchmarks") is what makes the harness end-to-end without a live examiner.
  - `def main()` — argparse CLI: `python -m harness.silentwitness.runner --dataset <id> --evidence <path> [--examiner ...] [--model ...] [--temperature ...] [--case-dir <dir>] [--out <dir>]`. Writes `harness/results/<dataset_id>/silentwitness-<UTC-ISO-timestamp>.json` via atomic rename. Exit 0 on success; 2 on config/validation error; 4 on timeout; 5 on investigator non-zero exit.
  - Module ≤400 LOC.
- `harness/silentwitness/case_dir_reader.py` — NEW — small helper functions: `read_findings_json(case_dir) -> list[SwFinding]`, `read_hypothesis_jsonl(case_dir) -> list[SwHypothesisEvent]`, `read_audit_jsonl(case_dir) -> list[SwToolCall]`, `read_critic_jsonl(case_dir) -> list[SwCriticVerdict]`, `count_gaps_in_report(report_md_path: Path) -> int` (regex `^- ` lines under `## Gaps` heading until next `^## `). ≤150 LOC. Tests in same integration file.
- `tests/integration/test_harness_silentwitness_runner.py` — NEW — ≥7 BDD scenarios using a fixture case directory at `tests/fixtures/case-harness/` (pre-seeded with 5 findings, 8 hypothesis events including 2 pivots, 12 tool calls across `memory.jsonl`+`disk.jsonl`, 2 critic verdicts, a `report.md` with `## Executive Summary` and 3 `## Gaps` bullets):
  - `case_dir_reader.read_findings_json` returns ≥5 `SwFinding` objects;
  - `case_dir_reader.read_hypothesis_jsonl` returns ≥8 events, 2 with `transition == "pivot"`;
  - `case_dir_reader.read_audit_jsonl` merges across all `*.jsonl` files under `audit/` (≥12 entries);
  - `case_dir_reader.count_gaps_in_report` returns exactly 3;
  - `run_silentwitness` (with `subprocess` mocked to instantly return success + the fixture case dir populated) returns a `SilentWitnessRunResult` whose `entity_gate_rejections` matches the count of envelopes with `status == "REJECTED"` in the seeded `audit/findings.jsonl`;
  - `run_silentwitness` with `timeout_seconds=1` against a 10s mocked subprocess returns `exit_code=4`;
  - `SilentWitnessRunResult` round-trips through `model_dump_json` / `model_validate_json` without drift;
  - CLI `python -m harness.silentwitness.runner --dataset nitroba --evidence /does/not/exist` exits 2 and stderr contains `"evidence_path"`.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a seeded case directory at tests/fixtures/case-harness/ with 5 findings + 8 hypothesis events + 12 tool calls
When  `uv run python -c "from pathlib import Path; from harness.silentwitness.case_dir_reader import read_findings_json; print(len(read_findings_json(Path('tests/fixtures/case-harness'))))"` runs
Then  exit code is 0
And   stdout integer is ≥5

Given the seeded case directory has 2 hypothesis events with transition="pivot"
When  read_hypothesis_jsonl is invoked and filtered to pivots
Then  the filtered list length is exactly 2

Given the seeded report.md contains "## Gaps" with 3 bullet points
When  count_gaps_in_report is called
Then  the integer returned is exactly 3

Given run_silentwitness is invoked with timeout_seconds=1 against a mocked 10s subprocess
When  the runner executes
Then  result.exit_code == 4
And   stderr contains "silentwitness timeout"

Given run_silentwitness completes successfully against the seeded fixture
When  the result is serialized
Then  harness/results/nitroba/silentwitness-<timestamp>.json exists
And   the file json-loads to a dict that validates as SilentWitnessRunResult
And   the validated model's time_to_handoff_ready_report_seconds is not None

Given `uv run python -m harness.silentwitness.runner --dataset nitroba --evidence /does/not/exist` runs
Then  exit code is 2
And   stderr contains "evidence_path"

Given tests/integration/test_harness_silentwitness_runner.py exists
When  `uv run pytest tests/integration/test_harness_silentwitness_runner.py -v` runs
Then  exit code is 0
And   ≥7 tests pass
```

---

## Shell verification

```bash
# Tests
uv run pytest tests/integration/test_harness_silentwitness_runner.py -v
# Must show ≥7 passing

# Strict typing
uv run mypy --strict harness/silentwitness/

# Lint
uv run ruff check harness/silentwitness/

# §14 vocab gate clean
grep -rE "(court-admissible|Ralph Wiggum|autonomous SOC)" harness/silentwitness/ && exit 1 || true

# File-size guard (≤400 LOC)
uv run python .pre-commit-hooks/file-size-guard.py harness/silentwitness/runner.py harness/silentwitness/case_dir_reader.py

# Coverage floor 85% on harness/silentwitness/
uv run coverage run -m pytest tests/integration/test_harness_silentwitness_runner.py
uv run coverage report --include="harness/silentwitness/*" --fail-under=85
```

---

## Notes for coding agent

- Reference: `docs/architecture.md` §3 folder layout; `docs/PRD.md` §4 headline metric + §6 secondary metrics (every metric in §6 maps to a field on `SilentWitnessRunResult`); `docs/ux-spec.md` §2.4 (`--auto-approve` mode for benchmarks); `docs/epics.md` Epic 14 DoD; `docs/CICD_SPEC.md` §6 coverage floor 85% on `harness/*`.
- **Symmetric shape with baseline:** the scorer (`story-scorer`) joins on `dataset_id` and reads both `baseline-*.json` and `silentwitness-*.json` files from the same `harness/results/<dataset_id>/` directory. Field names that mean the same thing MUST match across both runners (`dataset_id`, `started_at`, `finished_at`, `elapsed_seconds`, `model`, `temperature`, `commit_sha`). Asymmetric fields (`hypothesis_events`, `critic_verdicts`, `entity_gate_rejections`) are SilentWitness-only — that asymmetry IS the wedge.
- **Fair-compare discipline:** same model, same temperature as `story-baseline-runner`. Run via env vars `SILENTWITNESS_MODEL` + `SILENTWITNESS_TEMPERATURE`, not as CLI args — the investigator already reads them per ux-spec §2.6 precedence. Confirm by snapshotting `subprocess.Popen.args` in the integration test (cite story-investigator-agent for env-var precedence).
- `--auto-approve` is the benchmark-mode flag (ux-spec §2.4 last paragraph; documented as in scope for the harness). It bypasses the password prompt by accepting findings to APPROVED state with an HMAC over a deterministic harness-mode password derived from `examiner + dataset_id + commit_sha` — story-cli-approve owns the implementation; this runner just passes the flag and asserts the case `report.md` reaches the handoff-ready state.
- **`time_to_handoff_ready_report_seconds` definition** (locked here for downstream scorer): the offset from `started_at` to the first observation that the rendered `report.md` contains a non-empty `## Executive Summary` section. Implemented as a tail-poll on `report.md` (`watchdog` is overkill — a 250 ms poll is fine for a 5–30 minute investigation). If the report never reaches that state by `finished_at`, the field is `None` and `notes` contains `"handoff-ready threshold not reached within timeout"`.
- **`epistemic_honesty_count` definition:** count of bullet lines (`^- `) under the `## Gaps` heading in the final rendered `report.md`. Implemented in `case_dir_reader.count_gaps_in_report` — regex anchored to `^## Gaps\b` until next `^## ` or EOF. This is the PRD §6 "epistemic-honesty count" row.
- **`entity_gate_rejections` definition:** count of `record_observation` MCP envelopes with `status == "REJECTED"` and `reason` containing `"entity"` in the merged `audit/*.jsonl` stream. Source rows are produced by `story-entity-gate` + `story-record-observation-tool`.
- DO NOT spin up a real `silentwitness investigate` against a real evidence image in tests — mock `subprocess.Popen` and use a pre-seeded fixture case directory. The actual end-to-end run happens via `just harness` orchestration (`story-justfile-targets`) on developer machines + manually in the demo recording session, not in CI.
- Output path discipline: `harness/results/<dataset_id>/silentwitness-<timestamp>.json`. The timestamp is the join key paired against `baseline-<timestamp>.json` in the scorer — they need not match each other (different runs), but each must be ISO-8601 UTC with `Z` suffix (matching the baseline runner exactly).
- Vocabulary discipline (PRD §14): never "court-admissible"; never "autonomous SOC"; never "Ralph Wiggum Loop". Use "SilentWitness investigator agent" verbatim; use "measured time-to-handoff-ready-report".
- Library docs to consult via Context7 BEFORE coding:
  - `pydantic` topic `Discriminated unions + JSONL deserialisation` (the hypothesis event types are a discriminated union by `transition`).
  - `subprocess` topic `Popen.communicate(timeout=) + cleanup on SIGTERM` (Python stdlib).
- Known pitfalls:
  1. JSONL files may have a trailing partial line if the agent was killed by timeout — `case_dir_reader.read_audit_jsonl` MUST skip lines that fail `json.loads` rather than raise. Log a `notes` entry counting skipped lines.
  2. `report.md` is written via atomic rename (story-atomic-io) — the poll loop MUST tolerate the brief window where the file does not exist. Use `try: report.read_text() except FileNotFoundError: continue`.
  3. `case_dir` cleanup: if `case_dir` was None (auto-tempdir), DO NOT delete it after the run — the scorer needs to re-read findings.json + report.md for deeper verification. Log the temp path in `notes`.
  4. Coverage 85% floor: cover the timeout path + the partial-JSONL skip + the `report.md`-never-reaches-handoff-ready path. These are the highest LOC contributors.
