# Story — `silentwitness status <case-id>` (case state snapshot via rich.table)

**ID:** story-cli-status
**Epic:** Epic 12 — CLI (Typer) + Claude Code drop-in config
**Depends on:** story-cli-init, story-hypothesis-stack, story-audit-logger
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As an** IR consultant or peripheral observer who wants to check on an in-flight or completed case without disrupting it
**I want to** run `silentwitness status <case-id>` and see a pretty-printed table of active/confirmed/pivoted/abandoned hypotheses, finding counts (DRAFT/APPROVED/REJECTED), and remaining token budget — safe to run during an active investigation
**So that** I can sanity-check progress at a glance, hand off to a colleague mid-case, or confirm a completed run before invoking `review` and `approve` (ux-spec §2.2 `status` sample output verbatim; architecture §5.3 hypothesis state machine; FR — report-as-state visibility).

---

## File modification map

- `src/silentwitness_agent/cli.py` — UPDATE — add `@app.command("status")` function. Signature: `def status(case_id: str = typer.Argument(...), json_out: bool = typer.Option(False, "--json"), watch: bool = typer.Option(False, "--watch"), full: bool = typer.Option(False, "--full"))`. Body delegates to `cli_commands.status.render(...)`. (~20 LOC delta to cli.py.)
- `src/silentwitness_agent/cli_commands/status.py` — NEW — owns: read-only parse of `cases/<case_id>/audit/hypothesis.jsonl` + `cases/<case_id>/findings.json` + the latest entry in `cases/<case_id>/audit/agent.jsonl` for budget info; builds the `rich.table.Table` per ux-spec §2.2 sample; `--json` flag emits structured JSON to stdout instead of the table (for `jq` piping); `--watch` re-renders every 2 seconds until SIGINT; `--full` adds confirmed/pivoted/abandoned sections (default elides them to active + summary). All reads are non-locking — safe during an active `investigate` run. (~150 LOC.)
- `tests/integration/test_cli_status.py` — NEW — ≥9 BDD scenarios: case with no hypotheses shows zero counts; case with 3 active + 2 confirmed + 1 pivoted + 0 abandoned matches the ux-spec sample shape; `--json` emits `{"case_id": ..., "hypotheses": {"active": 3, ...}, ...}` parseable by `jq`; `--watch` redraws on hypothesis.jsonl append (test uses tempfile + sleep); status during an active investigate (concurrent test) returns successfully without locking; case not found exits 1; case with corrupted `hypothesis.jsonl` exits 2 with parse error wording; tokens-remaining computed correctly from the latest `agent.jsonl` entry; `--full` shows confirmed/pivoted/abandoned sections.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given case mr-evil-001 has audit/hypothesis.jsonl with 3 ACTIVE + 2 CONFIRMED + 1 PIVOTED + 0 ABANDONED entries
And   findings.json has 9 DRAFT + 0 APPROVED + 1 REJECTED entries
And   the latest agent.jsonl entry reports tokens_consumed=312000 against budget=800000
When  `uv run silentwitness status mr-evil-001` runs
Then  exit code is 0
And   stdout contains a rich.table with rows for H-IDs and status labels
And   stdout contains "hypothesis stack (3 active, 2 confirmed, 1 pivoted, 0 abandoned)" (or rich table equivalent)
And   stdout contains "findings: staged 9  approved 0  rejected 1"
And   stdout contains "tokens:   312k / 800k budget"
And   the output shape matches ux-spec §2.2 sample

Given mr-evil-001 has zero hypotheses (just-initialized case)
When  `silentwitness status mr-evil-001` runs
Then  exit code is 0
And   stdout shows "no hypotheses yet" with all counts at 0

Given `--json` flag is passed
When  `silentwitness status mr-evil-001 --json` runs
Then  exit code is 0
And   stdout is valid JSON parseable by `jq -e '.case_id'`
And   the JSON has keys: case_id, hypotheses, findings, budget, last_event
And   stdout contains zero ANSI escape sequences

Given an active investigate is running on mr-evil-001 (concurrent fixture)
When  `silentwitness status mr-evil-001` runs in a separate process
Then  exit code is 0
And   no file lock blocks the read
And   the returned snapshot is consistent (no partial-line JSON parse errors)

Given `--watch` flag is passed
And   hypothesis.jsonl is appended to (simulated) during the watch
When  `silentwitness status mr-evil-001 --watch` runs for 5 seconds with SIGINT at t=5
Then  exit code is 130
And   stdout shows at least 2 redraws (verifiable by counting cleared-screen sequences)

Given case mr-evil-999 does not exist
When  `silentwitness status mr-evil-999` runs
Then  exit code is 1
And   stderr contains "case 'mr-evil-999' not found"

Given audit/hypothesis.jsonl contains a non-JSON line (corruption)
When  `silentwitness status mr-evil-001` runs
Then  exit code is 2
And   stderr contains "hypothesis.jsonl parse error at line N"

Given `--full` flag is passed
When  `silentwitness status mr-evil-001 --full` runs
Then  stdout includes a CONFIRMED section table
And   stdout includes a PIVOTED section table
And   stdout includes an ABANDONED section (empty if none)

Given tests/integration/test_cli_status.py exists
When  `uv run pytest tests/integration/test_cli_status.py -v` runs
Then  exit code is 0
And   ≥9 tests pass
```

---

## Shell verification

```bash
uv run pytest tests/integration/test_cli_status.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥9

uv run mypy --strict src/silentwitness_agent/cli_commands/status.py
uv run ruff check src/silentwitness_agent/cli_commands/status.py

[ "$(wc -l < src/silentwitness_agent/cli_commands/status.py)" -le 200 ]

# --json output is jq-clean
uv run silentwitness status test-case --json | jq -e '.case_id' >/dev/null

# Concurrent-read safety: kick off an investigate in the background and confirm status returns 0
( uv run silentwitness investigate test-case --max-iterations 1000 & ) ; sleep 1 ; uv run silentwitness status test-case ; [ "$?" = "0" ]
```

---

## Notes for coding agent

- Source of truth: ux-spec.md §2.2 (`status` sample output — copy verbatim; the elapsed-time format `12m 04s`, the hypothesis-stack line shape `H-007 [ACTIVE]    wardriving — Ethereal + intercepted SMTP creds`, the findings + tokens + last-pivot lines), §2.5 (three-prefix rule for any warning); architecture.md §5.3 (`HypothesisStatus` enum: ACTIVE | CONFIRMED | PIVOTED | ABANDONED — the order matters for the header line).
- This command is **read-only** and **safe during active runs**. Open files in `"r"` mode only. Use line-by-line `for line in f:` reads to handle partial-write edge cases (skip non-JSON lines with a warning if `--debug` is set, error if not).
- The `hypothesis.jsonl` and `findings.json` parses are the heaviest reads. Cache them via `functools.lru_cache` keyed on file mtime — `--watch` re-reads by re-stat'ing each tick.
- `--watch` uses `rich.live.Live` with `refresh_per_second=0.5` (one redraw every 2s). SIGINT cleanly exits 130 (same handler pattern as story-cli-investigate). The non-watch path is a one-shot render — no `Live`.
- `--json` emits structured output to stdout (no rich, no ANSI). Schema:
  ```json
  {
    "case_id": "mr-evil-001",
    "examiner": "sansforensics",
    "elapsed_seconds": 724,
    "hypotheses": {
      "active": [{"id": "H-007", "statement": "...", "specialist": "MEMORY"}, ...],
      "confirmed": [...], "pivoted": [...], "abandoned": [...],
      "counts": {"active": 3, "confirmed": 2, "pivoted": 1, "abandoned": 0}
    },
    "findings": {"draft": 9, "approved": 0, "rejected": 1},
    "budget": {"tokens_consumed": 312000, "tokens_budget": 800000, "steps_consumed": 47, "steps_budget": 200},
    "last_event": {"ts": "2026-06-02T12:34:01Z", "type": "PIVOT", "summary": "H-004 → H-005 symbol-table rebuilt"}
  }
  ```
- Budget remaining = `budget - consumed`. Display as `312k / 800k` (k = ×1000, not KiB) per ux-spec §2.2 sample. Implement with a `_humanize_count(n)` helper that uses `k` for thousands and `M` for millions.
- Default render shape (the non-`--full` path) per ux-spec §2.2:
  ```
  case:        mr-evil-001       model:   anthropic:claude-opus-4-7-1m
  examiner:    sansforensics     status:  INVESTIGATING (12m 04s elapsed)

  hypothesis stack (3 active, 2 confirmed, 1 pivoted, 0 abandoned):
    H-007 [ACTIVE]    wardriving — Ethereal + intercepted SMTP creds
    H-006 [ACTIVE]    Schardt is the user; Documents and Settings\Mr. Evil\
    H-005 [CONFIRMED] memory image OS = WinXP SP2 (vol windows.info)
    H-004 [PIVOTED]   ⤳ vol3 symbol-table mismatch; rebuilt

  findings: staged 9  approved 0  rejected 1 (entity gate)
  tokens:   312k / 800k budget
  last pivot: 12:34:07Z  H-004 → H-005  symbol-table rebuilt
  ```
  Build via `rich.table.Table` for the hypothesis-stack rows; the header/footer lines via `Console.print`. Match the exact spacing and the `⤳` glyph for PIVOTED (Unicode U+2937).
- Status field options: `INVESTIGATING` (most recent agent.jsonl entry has no `on_finish`), `COMPLETED` (on_finish present, exit 0), `ABORTED` (sigint_checkpoint present), `IDLE` (no agent.jsonl yet — just-initialized case).
- Elapsed-time computation: from the first `agent.jsonl` entry's `ts` to the latest entry's `ts` (or `datetime.utcnow()` if the run is still active). Format `Xm YYs` for <1h; `Xh YYm` for ≥1h.
- Last event: read the last line of `hypothesis.jsonl`; if it's a `PIVOT` event, show the `from → to` shape; if `HYPOTHESIS_FORMED`, show "H-XXX formed"; etc.
- Context7 hints BEFORE coding:
  - `rich` topic "Table column add_row Console print" — confirm column-alignment behaviour.
  - `pydantic` (optional) for parsing each hypothesis.jsonl line via `HypothesisEvent.model_validate_json` — reuse the model from story-hypothesis-stack.
- Known pitfalls:
  1. JSONL files are routinely partial during active writes. Catch `json.JSONDecodeError` per-line and either skip (default) or error (with `--debug` flag set). Do NOT use `json.load(f)` on the whole file.
  2. `Path.stat().st_mtime` for the cache key: filesystem precision is 1s on some platforms. The `--watch` redraw at 0.5 Hz won't miss appends because the JSONL grows in size — also key on `Path.stat().st_size`.
  3. The `⤳` glyph (U+2937) renders correctly in modern terminals; in `TERM=dumb` it falls back to `->`. Test this path.
  4. `--watch` MUST honor SIGINT cleanly (exit 130). Reuse the signal handler pattern from story-cli-investigate's notes.
- Vocabulary: "staged" for DRAFT findings, "approved" for APPROVED, "rejected" for REJECTED. Never "queued" or "pending." The PRD §14 reject-vocab list does not block any of these.
