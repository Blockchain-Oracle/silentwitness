# Story — `silentwitness investigate <case-id>` (investigator agent + 4-pane rich.live render + SIGINT)

**ID:** story-cli-investigate
**Epic:** Epic 12 — CLI (Typer) + Claude Code drop-in config
**Depends on:** story-cli-init, story-investigator-agent, story-hypothesis-stack, story-audit-logger
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As an** IR consultant on a Tier-2 boutique who has just registered evidence for case `mr-evil-001`
**I want to** run `silentwitness investigate mr-evil-001` and watch a four-pane rich.live layout render the hypothesis stack, current tool call, findings/budget, and last event in real time at ≤4 Hz — while the investigator agent works the case end-to-end (5–30 min) — with `Ctrl-C` cleanly checkpointing state and exiting 130
**So that** I can keep peripheral eyes on the case during a customer call (per ux-spec §3.1 multi-tasking reality), trust the run will not corrupt audit state if I cancel, and have a live view that degrades to plain `EVT ` JSONL when stdout is not a TTY for `jq`-pipe use (ux-spec §2.3 live investigation rendering; architecture §5.1 investigator agent; FR3 model-agnostic via `SILENTWITNESS_MODEL`; FR7 ≥1 self-correction visible in demo).

---

## File modification map

- `src/silentwitness_agent/cli.py` — UPDATE — add `@app.command("investigate")` function. Signature: `def investigate(case_id: str = typer.Argument(...), model: str | None = typer.Option(None, "--model"), max_iterations: int = typer.Option(50, "--max-iterations"), max_tokens: int = typer.Option(800_000, "--max-tokens"), specialist: list[str] | None = typer.Option(None, "--specialist"), resume: bool = typer.Option(False, "--resume"), no_hud: bool = typer.Option(False, "--no-hud"), hud: bool = typer.Option(False, "--hud"))`. Body delegates to `silentwitness_agent.cli_commands.investigate.run(...)`. (~30 LOC delta to cli.py.)
- `src/silentwitness_agent/cli_commands/investigate.py` — NEW — the heavy implementation. Owns: SIGINT/SIGTERM handler registration (must save state via `hypothesis_stack.checkpoint()` + emit final `audit/agent.jsonl` entry + exit 130); the `rich.live.Live` + `rich.layout.Layout` setup with four panes per ux-spec §2.3 layout sketch; the asyncio event loop that subscribes to `HypothesisEvent` + MCP audit stream queues; the TTY/non-TTY render switch (TTY → rich live; non-TTY → `EVT <json>` JSONL line-buffered); the HUD autostart hook (calls into Epic 13 `hud_sse_server.start()` if installed and `--hud` set OR `[hud].enabled = true` in config, but `--no-hud` always wins). The investigator agent itself lives in story-investigator-agent; this module orchestrates render + lifecycle. (~180 LOC.)
- `src/silentwitness_agent/cli_commands/_live_layout.py` — NEW — pure builder for the four-pane `rich.layout.Layout` per the ux-spec §2.3 sketch. Functions: `build_layout() -> Layout`; `render_hypothesis_stack(stack: HypothesisStack) -> RenderableType`; `render_current_tool_call(active_tool: ToolCallSnapshot | None) -> RenderableType`; `render_findings_budget(findings: FindingsSnapshot, budget: BudgetSnapshot) -> RenderableType`; `render_last_event(event: HypothesisEvent | None) -> RenderableType`. No I/O, no side effects — pure functions over snapshot dataclasses. Pivots get a one-tick yellow flash via a `_flash_frame` counter in the render call. (~140 LOC.)
- `tests/integration/test_cli_investigate.py` — NEW — ≥10 BDD scenarios: happy-path investigate against a stubbed Pydantic AI agent fixture exits 0; `--model openai:gpt-5` is passed through to `SILENTWITNESS_MODEL`; SIGINT mid-run results in exit 130 + final audit entry with `reason="sigint_checkpoint"`; SIGTERM behaves identically to SIGINT; non-TTY stdout produces `EVT ` JSONL lines (parseable by `jq`); TTY stdout produces ANSI-rendered rich frames; `NO_COLOR=1` strips ANSI; `--no-hud` skips HUD even if config enables it; missing case directory exits 1 with "case not found"; `--resume` continues from the last `audit/agent.jsonl` checkpoint; budget exhaustion (max_tokens hit) results in clean shutdown with exit 0 and final report flush.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given case mr-evil-001 is initialized with registered evidence
And   the investigator agent is stubbed (test fixture) to form 1 hypothesis + dispatch 1 specialist + complete
When  `uv run silentwitness investigate mr-evil-001` runs in a TTY
Then  exit code is 0
And   the four-pane rich.live layout renders at least one frame (verifiable via captured ANSI in test)
And   cases/mr-evil-001/audit/hypothesis.jsonl contains ≥1 line
And   cases/mr-evil-001/audit/agent.jsonl ends with a {"event": "on_finish"} entry

Given a long-running investigate is in progress
When  the process receives SIGINT (Ctrl-C)
Then  exit code is 130
And   cases/mr-evil-001/audit/agent.jsonl ends with {"event": "sigint_checkpoint", ...}
And   no partial write artifacts remain (.tmp.* files)
And   the hypothesis stack state is recoverable via `--resume`

Given a long-running investigate is in progress
When  the process receives SIGTERM
Then  exit code is 130 (same checkpoint path as SIGINT)
And   the same checkpoint entry shape is written

Given investigate runs with --model openai:gpt-5
When  the agent initializes
Then  the env var SILENTWITNESS_MODEL is set to "openai:gpt-5" for the agent process
And   the audit entries' model_used field reflects "openai:gpt-5"

Given investigate runs with stdout redirected (non-TTY: `... | cat`)
When  the agent emits a hypothesis event
Then  stdout contains a line of shape `EVT {"event":"HYPOTHESIS_FORMED",...}` (JSONL)
And   stdout contains zero ANSI escape sequences
And   stdout is line-buffered (each EVT line flushed immediately)

Given NO_COLOR=1 is set in a TTY environment
When  investigate runs
Then  the live layout renders without ANSI color (ASCII box-drawing still aligns per ux-spec §2.3)
And   pivots show as `PIVOT` text not yellow flash

Given config sets [hud].enabled = true
And   --no-hud is passed on the CLI
When  investigate runs
Then  the HUD SSE server is NOT started
And   no socket is bound on 127.0.0.1:8088

Given config sets [hud].enabled = false
And   --hud is passed on the CLI
When  investigate runs
Then  the HUD SSE server IS started on 127.0.0.1:<config_port> (default 8088)
And   GET http://127.0.0.1:8088/ returns 200 within 2 seconds

Given case mr-evil-999 does not exist
When  `uv run silentwitness investigate mr-evil-999` runs
Then  exit code is 1
And   stderr contains "case 'mr-evil-999' not found"

Given the budget cap is reached (max_tokens exhausted) during an in-progress run
When  the budget enforcer fires
Then  the investigator marks remaining hypotheses as ABANDONED
And   the report's Gaps section is written
And   exit code is 0 (clean shutdown, NOT an error)

Given tests/integration/test_cli_investigate.py exists
When  `uv run pytest tests/integration/test_cli_investigate.py -v` runs
Then  exit code is 0
And   ≥10 tests pass
```

---

## Shell verification

```bash
uv run pytest tests/integration/test_cli_investigate.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥10

uv run mypy --strict src/silentwitness_agent/cli_commands/investigate.py src/silentwitness_agent/cli_commands/_live_layout.py
uv run ruff check src/silentwitness_agent/cli_commands/

# File-size guards
[ "$(wc -l < src/silentwitness_agent/cli_commands/investigate.py)" -le 400 ]
[ "$(wc -l < src/silentwitness_agent/cli_commands/_live_layout.py)" -le 400 ]

# SIGINT exit code spot check (uses a short-running stub fixture)
( uv run silentwitness investigate test-case --max-iterations 1000 & PID=$!; sleep 0.5; kill -INT $PID; wait $PID; ) ; [ "$?" = "130" ]

# Non-TTY mode emits parseable JSONL
uv run silentwitness investigate test-case --max-iterations 2 | head -1 | jq -e '.event' >/dev/null

# §14 no-mocks check (excluding test fixtures)
git diff main...HEAD -- 'src/silentwitness_agent/cli_commands/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded)" | grep -v "test\|spec\|stub"
```

---

## Notes for coding agent

- Source of truth: ux-spec.md §2.2 (`investigate` flags `--model`, `--max-steps`, `--max-tokens`, `--specialist`, `--resume`, `--hud`), §2.3 (the four-pane layout sketch — copy verbatim into `_live_layout.py` as the canonical reference; ≤4 Hz refresh; `NO_COLOR=1`/`TERM=dumb` degradation rules; pivots flash yellow for one tick then settle; non-TTY → `EVT ` JSONL); architecture.md §5.1 (investigator agent — Pydantic AI Agent instance, `SILENTWITNESS_MODEL` env, max_iterations default 50, on_finish flushes state and writes Gaps section), §5.3 (hypothesis state machine — `HypothesisEvent`s feed the rich layout queues), §8.1 (sequence diagram — investigator → form → dispatch → tool call → citation gate → observation → report update); FR3 (model-agnostic), FR7 (≥1 self-correction visible).
- This is the heaviest CLI command. Implementation lives in `cli_commands/investigate.py`, not directly in `cli.py`, to keep the cumulative cli.py budget under 400. The Typer command wrapper in cli.py is ~30 LOC; the real work is delegated.
- SIGINT/SIGTERM handling is **mandatory** and **load-bearing**. The flow:
  1. Install signal handlers via `signal.signal(SIGINT, _handler)` and `signal.signal(SIGTERM, _handler)` at the start of `run()`.
  2. The handler sets an `asyncio.Event` (`_shutdown_event`) — does NOT call `sys.exit()` directly (that raises `SystemExit` inside the asyncio loop and corrupts state).
  3. The main loop checks `_shutdown_event.is_set()` after every agent step; on set, calls `hypothesis_stack.checkpoint()` (atomic write via story-atomic-io), emits one final `agent.jsonl` entry with `event="sigint_checkpoint"` and the current step count + token consumed, then `sys.exit(130)`.
  4. The `rich.live.Live` context manager must be properly `__exit__`ed before the exit call (otherwise the terminal stays in raw mode). Use `try/finally`.
- Rich layout (per ux-spec §2.3 verbatim sketch):
  ```python
  layout = Layout()
  layout.split_column(
      Layout(name="hypothesis_stack", size=8),
      Layout(name="current_tool_call", size=6),
      Layout(name="footer", size=5),
  )
  layout["footer"].split_row(
      Layout(name="findings"),
      Layout(name="budget"),
      Layout(name="last_event"),
  )
  ```
  Refresh rate: `Live(layout, refresh_per_second=4)`. The 4 Hz cap is per ux-spec §2.3 ("legible over SSH") — do NOT bump it.
- TTY detection: `sys.stdout.isatty()`. If False → use the `_emit_jsonl_event` writer instead of the live layout; line-buffered `print(json.dumps({"event": ..., ...}), flush=True)` with `EVT ` prefix.
- `NO_COLOR=1`, `TERM=dumb`: `Console(no_color=True)` or `Console(force_terminal=False)`. Rich auto-detects `NO_COLOR`; double-check via integration test that `\x1b[` count == 0 in captured output.
- Model selection (FR3): `--model` flag overrides `SILENTWITNESS_MODEL` env which overrides the config file's `[model].default`. Pass the resolved model string into the investigator agent's construction (the agent itself reads from env per architecture §5.1; CLI's job is to `os.environ["SILENTWITNESS_MODEL"] = resolved` before invoking).
- HUD autostart logic (Epic 13 — `--hud`/`--no-hud`/config interaction):
  - Precedence: `--no-hud` > `--hud` > `config.hud.enabled` (default False).
  - `--no-hud` always wins (even if `--hud` is somehow also passed — error: Typer can be told these are mutually exclusive).
  - If HUD requested but Epic 13 not installed (`hud_sse_server` module missing), warn with `[yellow]⚠[/yellow] HUD requested but hud-sse-server not installed; continuing without HUD`. Do NOT exit; the investigation must still run.
- Resume logic (`--resume`): load the last `agent.jsonl` checkpoint entry; restore hypothesis stack state via `HypothesisStack.from_checkpoint(...)`; continue from the next step. If no checkpoint exists, error: exit 1 with `[red]✗[/red] no checkpoint to resume from`.
- Budget exhaustion is **clean shutdown, exit 0** (architecture §5.1 — "the agent halts cleanly when the limit is reached, marks remaining hypotheses as ABANDONED, and writes the report's `Gaps` section"). It's NOT an error condition. The bar chart in the demo (PRD §2 4:30–4:50) depends on this being a measured graceful path, not a crash.
- Context7 hints BEFORE coding:
  - `rich` topics: "Live Layout refresh_per_second", "Layout split_column split_row size", "Console NO_COLOR isatty".
  - `pydantic-ai` topic: "Agent run streaming events Hooks" — confirm the `HypothesisEvent` subscription pattern.
  - Python stdlib `signal` + `asyncio.add_signal_handler` (only on Unix; SIFT 2026 is Ubuntu Noble per FR1 — Unix-only is fine).
- Known pitfalls:
  1. `signal.signal()` inside an asyncio app: use `loop.add_signal_handler(SIGINT, callback)` instead. The plain `signal.signal` won't fire in the asyncio loop on all event-loop policies. Architecture rule: prefer `loop.add_signal_handler` on Unix.
  2. `rich.live.Live` will trash the terminal on uncaught exception. Always wrap in `try/finally` and call `live.stop()` in the `finally` block — even on `sys.exit(130)`.
  3. The non-TTY JSONL path MUST NOT use rich at all. A captured rich-rendered string still contains ANSI when piped. Branch the entire render code path on `isatty`, don't try to flatten rich output.
  4. `refresh_per_second=4` means the layout-builder functions are called 4×/s. They MUST be cheap (no I/O, no JSONL reads). The data they render comes from in-memory snapshots updated by the event subscriber.
  5. The HUD port (8088, per ux-spec §3.2) is the **renderer** — read-only. Do NOT open a write endpoint from this command; approval lives in `silentwitness approve` (story-cli-approve).
- Vocabulary discipline: never "find evil," "autonomous SOC," "court-admissible" in stdout/stderr of this command. Status panel labels are forensic-neutral: "HYPOTHESIS STACK," "CURRENT TOOL CALL," "FINDINGS," "BUDGET," "LAST EVENT" — verbatim from ux-spec §2.3 sketch.
