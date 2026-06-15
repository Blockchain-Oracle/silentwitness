# Story — Pydantic AI Hooks for investigator audit emission

**ID:** story-investigator-hooks
**Epic:** Epic 8 — Hypothesis state machine + investigator agent (Pydantic AI)
**Depends on:** story-investigator-agent, story-hypothesis-stack, story-hypothesis-budget, story-audit-logger
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** build the Pydantic AI `Hooks` capability in `src/silentwitness_agent/hooks.py` — pre-tool, post-tool, on-step, on-finish — that emits one JSONL audit line per lifecycle event to `cases/<case_id>/audit/agent.jsonl`, accumulates per-hypothesis token + step consumption against the `BudgetEnforcer`, and writes a final report-as-state snapshot
**So that** every agent step, every tool call, and every model usage delta is captured in the audit trail without the agent reasoning about logging — the audit emission is wired into the Pydantic AI lifecycle, not into the model prompt (architecture.md §5.1 — `before_tool_execute`, `after_tool_execute`, `after_model_request`, `after_run` hooks).

---

## File modification map

- `src/silentwitness_agent/hooks.py` — NEW — Pydantic AI `Hooks()` capability factory + callables. Exports:
  - `build_investigator_hooks(case_dir: Path, examiner: str, stack: HypothesisStack, budget: BudgetEnforcer) -> Hooks` — returns a configured Hooks instance with the four callbacks below registered. The returned object is passed into `build_investigator()` (story-investigator-agent) via `Agent(..., capabilities=[hooks])` (NOT `hooks=[...]` — `hooks` is not a real Agent kwarg per Pydantic AI v1.105 source; `capabilities=` is the correct surface).
  - `_on_before_tool(ctx: RunContext[InvestigatorDeps], tool_call: ToolCallEvent) -> None` — async callback. Emits a JSONL line of shape `{ts, type: "before_tool", tool_name, tool_args_summary, agent_step}` to `cases/<case_id>/audit/agent.jsonl`. Records the start timestamp on the in-flight context dict so `_on_after_tool` can compute `elapsed_ms`.
  - `_on_after_tool(ctx, tool_call, tool_result) -> None` — async callback. Computes `stdout_sha256 = sha256(json.dumps(tool_result, sort_keys=True).encode())` (the result is already structured JSON — Pydantic-validated by the MCP envelope from story-response-envelope). Emits `{ts, type: "after_tool", tool_name, audit_id (extracted from tool_result.audit_id if present), result_sha256, elapsed_ms, agent_step}`. If `tool_result` carries an `audit_id` field (i.e. the MCP server emitted one), reference it so the agent.jsonl line cross-links to the MCP-side audit JSONL.
  - `_after_model_request(ctx, step_event) -> None` — async callback. Reads `step_event.usage.input_tokens` + `step_event.usage.output_tokens` (Pydantic AI's `RunUsage` per-step delta) and calls `ctx.deps.budget.record_tokens(active_hypothesis_id, prompt, completion)` + `ctx.deps.budget.record_step(active_hypothesis_id)`. Emits a step-summary JSONL line.
  - `_after_run(ctx, run_result) -> None` — async callback. Writes the final hypothesis snapshot via `ctx.deps.stack.snapshot()`, dumps it to `cases/<case_id>/audit/agent.jsonl` as a single line with `type: "finish"`, and triggers a final report-as-state save (call `report.renderer.save_atomic` from Epic 11 if available; otherwise log a TODO line and continue — Epic 11 may not be merged yet).
  - Internal helper `_append_agent_jsonl(case_dir: Path, payload: dict) -> None` — uses `atomic_io.append_jsonl_line` (story-atomic-io) for fsync-after-append discipline. Same pattern as story-audit-logger.
  - Target ≤320 LOC.
- `tests/unit/test_investigator_hooks.py` — NEW — ≥10 behavioural tests using `TestModel` + a fake `InvestigatorDeps`:
  - `build_investigator_hooks(...)` returns a `Hooks` instance with all four callbacks registered;
  - `_on_before_tool` appends one well-formed JSONL line to `agent.jsonl` with `type: "before_tool"`;
  - `_on_after_tool` appends one line with `type: "after_tool"` and a real SHA256 in `result_sha256`;
  - `_on_after_tool` cross-links to the MCP-side `audit_id` when the tool result carries one;
  - `_after_model_request` calls `budget.record_tokens` with prompt + completion deltas;
  - `_after_model_request` calls `budget.record_step` once;
  - `_after_run` writes a `type: "finish"` line with the stack snapshot embedded;
  - elapsed_ms is non-negative and matches the time between before/after callbacks (use `time.monotonic` mock);
  - hooks survive an MCP tool that raises (the `_on_after_tool` still fires with `success: False` semantics);
  - JSONL lines parse back via `json.loads` and contain the required fields.
- `tests/integration/test_hooks_end_to_end.py` — NEW — 1 e2e scenario: run a `TestModel`-backed `build_investigator()` against a stubbed MCP toolset that returns 3 fake tool calls; assert `cases/<case>/audit/agent.jsonl` ends up with `1 + 3 + 3 + N_steps + 1` lines (1 startup-context line if any, 3 before_tool, 3 after_tool, N step lines, 1 finish line) and that `BudgetEnforcer.record_tokens` was called for each step.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given build_investigator_hooks(case_dir, examiner, stack, budget) is called
When  the returned object is inspected
Then  it is a pydantic_ai.Hooks instance
And   all four lifecycle callbacks are registered (before_tool, after_tool, after_model_request, after_run)

Given an investigator agent runs against a TestModel that issues 3 tool calls
When  the run completes
Then  cases/<case>/audit/agent.jsonl contains exactly 3 "before_tool" lines, 3 "after_tool" lines, ≥1 step line, and exactly 1 "finish" line
And   every after_tool line carries a non-empty result_sha256 (64 hex chars)
And   every after_tool line carries elapsed_ms > 0
And   the after_tool lines for tool calls that returned an MCP envelope reference the envelope's audit_id

Given an MCP tool call returns a ToolResponse carrying audit_id="sift-aj-20260613-007"
When  _on_after_tool fires for that call
Then  the appended JSONL line contains "audit_id":"sift-aj-20260613-007"

Given _after_model_request fires with step_event.usage.input_tokens=120, output_tokens=80
When  the callback returns
Then  budget.record_tokens has been called with prompt_tokens=120, completion_tokens=80
And   budget.record_step has been called exactly once for the same hypothesis_id

Given a hypothesis is currently active when an agent step fires
When  _after_model_request reads ctx.deps.stack.snapshot().active.id
Then  the recorded tokens are attributed to that hypothesis_id in the BudgetEnforcer

Given the run completes via run_result
When  _after_run fires
Then  cases/<case>/audit/agent.jsonl gains exactly 1 line with type="finish"
And   that line embeds the JSON-serialised stack.snapshot() output
And   the line is the last line in the file

Given an MCP tool raises an exception during execution
When  _on_after_tool would normally fire
Then  the hook still appends an after_tool line with the error captured (no silent drop)

Given the JSONL writer uses atomic_io.append_jsonl_line under the hood
When  10 concurrent agent steps fire (simulated)
Then  agent.jsonl contains exactly 10 well-formed lines (no interleaving)

Given tests/unit/test_investigator_hooks.py exists
When  `uv run pytest tests/unit/test_investigator_hooks.py -v` runs
Then  exit code is 0
And   ≥10 tests pass

Given tests/integration/test_hooks_end_to_end.py exists
When  `uv run pytest tests/integration/test_hooks_end_to_end.py -v` runs
Then  exit code is 0
And   the e2e scenario passes
```

---

## Shell verification

```bash
# Unit tests
uv run pytest tests/unit/test_investigator_hooks.py -v
# Must show ≥10 passing

# Integration (e2e)
uv run pytest tests/integration/test_hooks_end_to_end.py -v
# Must show 1 passing

# Coverage ≥85% on hooks.py
uv run coverage run -m pytest tests/unit/test_investigator_hooks.py tests/integration/test_hooks_end_to_end.py
uv run coverage report --include="src/silentwitness_agent/hooks.py" --fail-under=85

# JSONL shape audit on a synthetic run
uv run pytest tests/integration/test_hooks_end_to_end.py -v
# After it runs, the produced agent.jsonl must be valid JSONL
find /tmp -name 'agent.jsonl' -newer /tmp -path '*/audit/agent.jsonl' 2>/dev/null | head -1 | xargs -I {} sh -c '
  while read -r line; do echo "$line" | python -c "import sys,json; json.loads(sys.stdin.read())" || exit 1; done < {}
'

# Strict typing + lint + file-size guard
uv run mypy --strict src/silentwitness_agent/hooks.py
uv run ruff check src/silentwitness_agent/hooks.py
uv run ruff format --check src/silentwitness_agent/hooks.py
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_agent/hooks.py
```

---

## Notes for coding agent

- Reference: architecture.md §5.1 verbatim hook list:
  - `before_tool_execute` — emit a pre-tool JSONL entry; capture the model's tool selection rationale (if streamed).
  - `after_tool_execute` — emit a post-tool entry referencing the `audit_id` returned by the MCP server.
  - `after_model_request` — emit an event to `audit/agent.jsonl` per agent step.
  - `after_run` — flush state, write the final hypothesis snapshot.
- Reference: architecture.md §4.4 — every audit JSONL line carries SHA256 + elapsed_ms + audit_id. The agent.jsonl produced by this story is the **agent-side** audit log; the MCP-side `audit/<backend>.jsonl` is owned by story-audit-logger. The two layers cross-link via `audit_id` references. Each MCP tool response envelope (story-response-envelope) carries an `audit_id` that this story extracts and references in the after_tool JSONL line. This is the load-bearing cross-link that makes `silentwitness verify-claim` work end-to-end.
- Reference: context/.raw-design-research/02-model-agnostic-agent-libraries-survey.md §2 — Pydantic AI's `Hooks()` capability exposes `@hooks.on.before_tool_execute(tools=[...])` and post-execute equivalents; `AbstractCapability` gives `wrap_model_request`, `wrap_tool_execute`, `wrap_run_event_stream`. For SilentWitness audit emission the `Hooks` decorator surface is sufficient.
- Reference: context/technical/07-mcp-and-agent-platforms.md §C3.4 (Hooks) — the broader Claude-Agent-SDK hook shape is similar but NOT identical to Pydantic AI's. This story uses **Pydantic AI's Hooks**, not the Claude Agent SDK's. Do not import from `claude_agent_sdk`.
- Pydantic AI Hooks construction (target API; verify via Context7):
  ```python
  from pydantic_ai import Hooks
  hooks = Hooks()

  @hooks.on.before_tool_execute()
  async def _on_before_tool(ctx: RunContext[InvestigatorDeps], event):
      ...

  @hooks.on.after_tool_execute()
  async def _on_after_tool(ctx, event):
      ...

  @hooks.on.step()
  async def _after_model_request(ctx, event):
      ...

  @hooks.on.finish()
  async def _after_run(ctx, event):
      ...

  return hooks
  ```
  The exact decorator names have shifted across Pydantic AI 0.x → 1.x. Confirm via Context7 (architecture §12 mandate) BEFORE coding.
- The audit logger from story-audit-logger (`silentwitness_mcp.audit.logger.AuditLogger`) is the canonical JSONL writer for MCP-side events. This story does NOT instantiate that AuditLogger — `agent.jsonl` is agent-side and uses the simpler `atomic_io.append_jsonl_line` directly (no `audit_id` allocation needed at this layer; the relevant `audit_id` is the MCP-side one already allocated when the tool ran). Cite `silentwitness_mcp.audit.logger` in the docstring so future readers see the parallel.
- JSONL line shape (per-event-type — write into docstring):
  - `before_tool`: `{"ts","type":"before_tool","tool_name","tool_args_summary","agent_step","active_hypothesis_id"}`
  - `after_tool`: `{"ts","type":"after_tool","tool_name","audit_id" (if mcp), "result_sha256","elapsed_ms","agent_step","active_hypothesis_id","success"}`
  - `step`: `{"ts","type":"step","step_index","input_tokens","output_tokens","active_hypothesis_id"}`
  - `finish`: `{"ts","type":"finish","final_state","stack_snapshot": {...}, "model_used", "total_tokens_consumed"}`
- `tool_args_summary` is the JSON-serialised tool args truncated to first 1KB (matches the MCP-side `result_summary` truncation convention from architecture §4.4). Full args are already in the MCP-side audit JSONL via the MCP envelope; agent-side just needs the cross-link.
- `result_sha256`: compute `sha256(json.dumps(tool_result, sort_keys=True, default=str).encode("utf-8"))`. The `sort_keys=True` is critical for reproducibility — Pydantic dict ordering is field-declaration order, but the hook may receive a generic dict.
- `elapsed_ms`: store `time.monotonic_ns()` in a per-tool-call context dict at `before_tool`, subtract at `after_tool`, divide by 1e6. Use `time.monotonic`, not `time.time` (monotonic is immune to clock skew).
- `active_hypothesis_id`: `ctx.deps.stack.snapshot().active.id if stack.active else None`. Each hook attributes its event to the currently active hypothesis.
- Cross-linking convention: when the MCP envelope returned by a tool call carries `audit_id` (most tools do via the ToolResponse envelope from story-response-envelope), the agent-side after_tool line MUST reference that audit_id verbatim. This is how `silentwitness verify-claim F-001/sift-aj-20260613-042` (architecture §5.4) resolves through the agent.jsonl back to the MCP-side audit entry.
- Critic interaction: this story does NOT directly call the critic. The critic trigger (story-critic-trigger) reads finding counts and timer state; it does NOT register itself as a Pydantic AI hook. The hooks here purely emit agent-side audit events.
- Library docs to consult via Context7 BEFORE coding (architecture §12 mandate):
  - `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic-ai"` then:
    - `query-docs` topic `"Hooks decorator before_tool_execute after_tool_execute after_model_request after_run RunContext"` — exact decorator surface; this has shifted at least twice across 0.x.
    - `query-docs` topic `"RunUsage input_tokens output_tokens per step"` — the field path for `_after_model_request`'s token accounting.
- Pitfall: Pydantic AI's hook callbacks receive `RunContext[YourDeps]` — the generic type parameter MUST match `InvestigatorDeps` (story-investigator-agent). `mypy --strict` will catch a mismatch.
- Pitfall: `RunContext` is read-only inside hooks; do NOT try to mutate `ctx.deps.pending_critiques` here (that is the critic-handler's job — story-critic-verdict-handling). The hooks only read.
- Pitfall: if `_on_after_tool` fires for a tool that raised (an exception escaped through Pydantic AI's wrapping), the `tool_result` argument may be an exception object or `None`. Handle both: log `success: False` with the exception type and message, but never let the hook itself raise (a raising hook crashes the entire run).
- Vocabulary discipline: never "court-admissible." Hook docstrings: "emits one JSONL audit line per Pydantic AI lifecycle event."
- LOC budget: ~320. Comfortable margin.
