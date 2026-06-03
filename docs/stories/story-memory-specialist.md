# Story — Memory specialist subagent (Pydantic AI agent-delegation)

**ID:** story-memory-specialist
**Epic:** Epic 9 — Specialist subagents (memory / disk / network / log)
**Depends on:** story-investigator-agent, story-investigator-hooks, story-vol-pslist, story-vol-pstree-psscan, story-vol-malfind, story-vol-netscan, story-vol-cmdline, story-vol-dlllist-handles, story-vol-lsadump, story-record-observation-tool, story-record-interpretation-tool
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** build the memory specialist as its own Pydantic AI `Agent[SpecialistDeps, SpecialistReport]` in `src/silentwitness_agent/specialists/memory.py`, invoked by the investigator via Pydantic AI's agent-delegation pattern (one specialist call = one `@investigator.tool` that runs the specialist agent and returns its structured findings)
**So that** memory-forensics work runs in its own context window with a cost-optimized model (default `anthropic:claude-haiku-4-5`) and a tight MCP allowlist (only `vol_*` + `record_*` tools), keeping the investigator's main context lean and surfacing specialist dispatch in the audit trail as senior-analyst behaviour rather than a chatty single agent (architecture.md §5.2 — Memory specialist).

---

## File modification map

- `src/silentwitness_agent/specialists/__init__.py` — NEW — empty package marker.
- `src/silentwitness_agent/specialists/_base.py` — NEW — shared specialist primitives (extracted skeleton since 4 specialists share 80% of the shape):
  - `SpecialistDeps` (Pydantic frozen BaseModel): `case_dir: Path`, `examiner: str`, `hypothesis_id: str` (the hypothesis the specialist is testing), `evidence_paths: list[Path]` (registered evidence the specialist may touch), `pending_critiques: list[CriticVerdict]`.
  - `SpecialistReport` (Pydantic BaseModel): `findings: list[SpecialistFinding]` (each carries `observation_id`, `interpretation_id`, `confidence`, `summary`), `tokens_spent: int`, `tool_calls: list[ToolCallRecord]` (each `tool_name`, `audit_id`, `elapsed_ms`, `success`), `time_elapsed_ms: float`, `confidence_assessment: Literal["LOW", "MEDIUM", "HIGH"]`, `next_specialist_suggested: SpecialistName | None`, `notes_for_investigator: str`.
  - `ToolCallRecord` + `SpecialistFinding` Pydantic models.
  - `_load_specialist_prompt(slug: str) -> str` helper to read `prompts/specialist_<slug>.md` via `importlib.resources`.
  - Target ≤200 LOC.
- `src/silentwitness_agent/specialists/memory.py` — NEW — memory specialist. Exports:
  - `MEMORY_TOOL_ALLOWLIST` (frozenset[str]): `{"vol_pslist", "vol_pstree", "vol_psscan", "vol_malfind", "vol_netscan", "vol_cmdline", "vol_dlllist", "vol_handles", "vol_lsadump", "record_observation", "record_interpretation", "register_evidence", "verify_evidence_hash"}`.
  - `build_memory_specialist(model: str | None = None) -> Agent[SpecialistDeps, SpecialistReport]` — factory. Model resolved from `SILENTWITNESS_SPECIALIST_MODEL_MEMORY` env (default `anthropic:claude-haiku-4-5`; `anthropic:claude-opus-4-7` if `SILENTWITNESS_MODEL_QUALITY=high`). Toolset is an `MCPServerStdio` filtered to `MEMORY_TOOL_ALLOWLIST` via the `.filtered()` method (see "Pydantic AI tool_filter correction" note below).

> **Pydantic AI tool_filter correction:** `MCPServerStdio(..., tool_filter=...)` does NOT exist. Use `MCPServerStdio(...).filtered(lambda ctx, td: td.name in ALLOWLIST)`. The real primitive is `pydantic_ai.FilteredToolset` (source: `pydantic_ai_slim/pydantic_ai/toolsets/filtered.py`). Pattern:
> ```python
> from pydantic_ai.mcp import MCPServerStdio
> mcp_server = MCPServerStdio("silentwitness-mcp")
> filtered = mcp_server.filtered(lambda ctx, td: td.name in MEMORY_TOOL_ALLOWLIST)
> # Pass filtered as a toolset in `toolsets=[filtered]` (NOT `mcp_servers=[...]`, which is deprecated).
> # If a streamable-HTTP transport is needed, use `MCPServerStreamableHTTP` (NOT `MCPServerHTTP`, which is deprecated).
> ```
  - `register_as_investigator_tool(investigator: Agent, memory_specialist: Agent) -> None` — registers the specialist as an `@investigator.tool` named `dispatch_memory_specialist(question: str, hypothesis_id: str) -> SpecialistReport`. The tool body runs `await memory_specialist.run(question, deps=specialist_deps_from(...))` and returns `result.output`. This is the Pydantic-AI agent-delegation pattern.
  - Target ≤220 LOC.
- `src/silentwitness_agent/prompts/specialist_memory.md` — NEW — system prompt for the memory specialist. ~50 lines of Markdown (see §"System prompt" below).
- `tests/unit/test_memory_specialist_build.py` — NEW — ≥6 unit tests using `TestModel`:
  - factory honours `SILENTWITNESS_SPECIALIST_MODEL_MEMORY` env;
  - default is `anthropic:claude-haiku-4-5`;
  - `SILENTWITNESS_MODEL_QUALITY=high` upgrades to `anthropic:claude-opus-4-7`;
  - the tool allowlist contains exactly the 13 expected tool names (9 vol_* + 4 record/registry);
  - `dispatch_memory_specialist` is registered on the investigator after `register_as_investigator_tool`;
  - the system prompt is loaded from `prompts/specialist_memory.md` and contains "memory forensics" and "cite the exact tool output line".
- `tests/integration/test_memory_specialist_allowlist.py` — NEW — 1 integration test: construct a memory specialist, attempt to call a disk tool (`parse_mft`) via the specialist's toolset, assert the call is refused (the tool is not in the specialist's allowlist). Uses `TestModel` to simulate the specialist trying the disallowed tool.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## System prompt (verbatim — write into `prompts/specialist_memory.md`)

```
You are a memory forensics specialist working under a senior incident
response analyst. The analyst hands you exactly one hypothesis at a time and
asks you to test it against the memory evidence registered for this case.

Your toolset is limited to Volatility 3 memory plugins (pslist, pstree,
psscan, malfind, netscan, cmdline, dlllist, handles, lsadump) plus the
record_observation, record_interpretation, register_evidence, and
verify_evidence_hash tools. You cannot call disk, log, network, or registry
tools. If your hypothesis needs corroboration from another artifact family,
set next_specialist_suggested in your report so the analyst can dispatch
the right specialist.

For every finding you record, you cite the specific tool-execution audit_id
that produced it. You quote the exact line from the tool output rather than
paraphrasing.

When a Volatility plugin returns an error, read stderr carefully. The most
common failures are symbol-table mismatch (wrong OS profile), corrupted
evidence header, or a plugin that does not apply to this memory image. You
adjust your call (rebuild symbols via vol_info, retry with the correct
profile, or move to a different plugin) rather than rerunning the same call.

When evidence contradicts the hypothesis you were assigned, you do not
override the analyst's pivot decision. You record the contradicting evidence
as a finding with HIGH confidence and a note in notes_for_investigator
naming the contradiction. The analyst pivots; you do not.

Vocabulary: report findings in plain forensic language. Do not use the
phrases "court-admissible" or "eliminates hallucinations." Do not name
attacker groups unless their TTPs are directly evidenced in the tool output
you cite.

Return a SpecialistReport with findings, tokens_spent, tool_calls,
time_elapsed_ms, confidence_assessment, next_specialist_suggested,
notes_for_investigator. The analyst reads this and decides next steps.
```

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the memory specialist module is importable
When  `uv run python -c "from silentwitness_agent.specialists.memory import build_memory_specialist, MEMORY_TOOL_ALLOWLIST; print(len(MEMORY_TOOL_ALLOWLIST))"` runs
Then  exit code is 0
And   stdout is "13"

Given SILENTWITNESS_SPECIALIST_MODEL_MEMORY is unset and SILENTWITNESS_MODEL_QUALITY is unset
When  build_memory_specialist() is called
Then  agent.model resolves to "anthropic:claude-haiku-4-5"

Given SILENTWITNESS_MODEL_QUALITY="high" is set in the env
When  build_memory_specialist() is called
Then  agent.model resolves to "anthropic:claude-opus-4-7"

Given SILENTWITNESS_SPECIALIST_MODEL_MEMORY="openai:gpt-5-mini" is set in the env
When  build_memory_specialist() is called
Then  agent.model resolves to "openai:gpt-5-mini"

Given the MEMORY_TOOL_ALLOWLIST is inspected
When  the set is read
Then  it contains all 9 vol_* tool names plus record_observation, record_interpretation, register_evidence, verify_evidence_hash
And   it does NOT contain parse_mft, zeek_run, parse_evtx, regripper_run, or any other non-memory tool

Given the system prompt is loaded
When  prompts/specialist_memory.md is read
Then  the string "memory forensics specialist" is present
And   the string "cite the specific tool-execution audit_id" is present
And   the string "court-admissible" does NOT appear
And   the string "Ralph Wiggum" does NOT appear

Given a memory specialist is constructed and registered on an investigator
When  the investigator.toolset is inspected
Then  a tool named "dispatch_memory_specialist" is registered
And   its signature includes (question: str, hypothesis_id: str) -> SpecialistReport

Given an attempted call to a disk tool (parse_mft) through the memory specialist's toolset
When  the specialist tries to invoke parse_mft via the MCP allowlist filter
Then  the call is refused (toolset filter blocks it) with a structured error

Given a memory specialist run completes
When  the returned SpecialistReport is inspected
Then  it carries findings (list), tokens_spent (int), tool_calls (list), time_elapsed_ms (float), confidence_assessment (LOW|MEDIUM|HIGH), next_specialist_suggested (Optional[SpecialistName]), notes_for_investigator (str)

Given tests/unit/test_memory_specialist_build.py exists
When  `uv run pytest tests/unit/test_memory_specialist_build.py -v` runs
Then  exit code is 0
And   ≥6 tests pass

Given tests/integration/test_memory_specialist_allowlist.py exists
When  `uv run pytest tests/integration/test_memory_specialist_allowlist.py -v` runs
Then  exit code is 0
And   the allowlist-enforcement scenario passes
```

---

## Shell verification

```bash
# Import smoke
uv run python -c "from silentwitness_agent.specialists.memory import build_memory_specialist, MEMORY_TOOL_ALLOWLIST, register_as_investigator_tool; assert len(MEMORY_TOOL_ALLOWLIST) == 13; print('ok')"

# Default model
uv run python -c "
import os
for k in ('SILENTWITNESS_SPECIALIST_MODEL_MEMORY', 'SILENTWITNESS_MODEL_QUALITY'): os.environ.pop(k, None)
from silentwitness_agent.specialists.memory import build_memory_specialist
a = build_memory_specialist()
assert 'haiku' in repr(a.model).lower(), repr(a.model)
print('default OK')
"

# High-quality override
SILENTWITNESS_MODEL_QUALITY=high uv run python -c "
from silentwitness_agent.specialists.memory import build_memory_specialist
a = build_memory_specialist()
assert 'opus' in repr(a.model).lower(), repr(a.model)
print('quality=high OK')
"

# Vocabulary discipline
! grep -i 'court-admissible\|ralph wiggum\|autonomous soc' src/silentwitness_agent/prompts/specialist_memory.md

# Allowlist does not include disk/log/network tools
uv run python -c "
from silentwitness_agent.specialists.memory import MEMORY_TOOL_ALLOWLIST
banned = {'parse_mft','parse_amcache','parse_shimcache','parse_prefetch','parse_shellbags','regripper_run','zeek_run','suricata_run','parse_evtx','hayabusa_csv_timeline','chainsaw_hunt'}
assert not (MEMORY_TOOL_ALLOWLIST & banned), MEMORY_TOOL_ALLOWLIST & banned
print('allowlist clean')
"

# Unit + integration tests
uv run pytest tests/unit/test_memory_specialist_build.py tests/integration/test_memory_specialist_allowlist.py -v
# Must show ≥7 passing total

# Coverage ≥85%
uv run coverage run -m pytest tests/unit/test_memory_specialist_build.py tests/integration/test_memory_specialist_allowlist.py
uv run coverage report --include="src/silentwitness_agent/specialists/memory.py,src/silentwitness_agent/specialists/_base.py" --fail-under=85

# Strict typing + lint + file-size guard
uv run mypy --strict src/silentwitness_agent/specialists/memory.py src/silentwitness_agent/specialists/_base.py
uv run ruff check src/silentwitness_agent/specialists/
uv run ruff format --check src/silentwitness_agent/specialists/
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_agent/specialists/memory.py src/silentwitness_agent/specialists/_base.py
```

---

## Notes for coding agent

- Reference: architecture.md §5.2 verbatim:
  - Memory specialist model: `SILENTWITNESS_SPECIALIST_MODEL_MEMORY`, default `anthropic:claude-haiku-4-5` (cost), `anthropic:claude-opus-4-7` if `SILENTWITNESS_MODEL_QUALITY=high`.
  - MCP allowlist: the 9 vol_* tools + record_observation + record_interpretation + register_evidence + verify_evidence_hash (13 total).
  - System prompt: memory forensics frame — "You answer one targeted question per invocation. You cite the exact tool output line that supports your answer."
  - Returns: structured `SpecialistReport`.
- Reference: context/.raw-design-research/02-model-agnostic-agent-libraries-survey.md §2 — "Pydantic AI's agent-delegation primitive: one agent calls another agent inside a `@agent.tool`, dependencies + usage propagate automatically." This is the canonical pattern; do NOT reinvent.
- Reference: context/domain/01-dfir-foundations.md §4 — senior analyst mental model. The specialist tests ONE hypothesis at a time and reports structured findings. The investigator owns the pivot decision, not the specialist (the prompt above states this explicitly).
- Pydantic AI agent-delegation shape (verify via Context7):
  ```python
  memory_specialist = build_memory_specialist()

  @investigator.tool
  async def dispatch_memory_specialist(
      ctx: RunContext[InvestigatorDeps],
      question: str,
      hypothesis_id: str,
  ) -> SpecialistReport:
      specialist_deps = SpecialistDeps(
          case_dir=ctx.deps.case_dir,
          examiner=ctx.deps.examiner,
          hypothesis_id=hypothesis_id,
          evidence_paths=ctx.deps.evidence_paths,  # passed through
          pending_critiques=[],
      )
      result = await memory_specialist.run(
          question,
          deps=specialist_deps,
          usage=ctx.usage,  # propagate usage budget
      )
      return result.output
  ```
  The `usage=ctx.usage` propagation is the load-bearing part: it credits specialist tokens against the investigator's overall budget, AND the investigator-hooks story (story-investigator-hooks) records specialist tokens via the same on_step path.
- Reference: architecture.md §5.2 — "Each specialist returns structured findings to the investigator. The investigator does not re-invoke specialists for the same hypothesis once a verdict is returned." The `SpecialistReport.confidence_assessment` field is the verdict signal: HIGH → confirm; MEDIUM → consider pivot; LOW → abandon. The investigator's prompt (story-investigator-agent) instructs the agent on how to act on this signal.
- `MCPServerStdio` tool filtering: the correct surface is `MCPServerStdio(...).filtered(lambda ctx, td: td.name in MEMORY_TOOL_ALLOWLIST)`. There is NO `tool_filter=` kwarg on `MCPServerStdio` — the real primitive is `pydantic_ai.FilteredToolset` (`pydantic_ai_slim/pydantic_ai/toolsets/filtered.py`). The agent receives the filtered toolset via `toolsets=[filtered]` on `Agent(...)`; the deprecated `mcp_servers=[...]` kwarg must NOT be used. If a streamable-HTTP transport is needed, use `MCPServerStreamableHTTP` (the deprecated `MCPServerHTTP` is gone).
- The allowlist enforcement test: the assertion is "an attempt to call `parse_mft` via the memory specialist's toolset is refused." In practice, with `tool_filter`, `parse_mft` is simply not listed in the specialist's toolset → the model never sees it → the model cannot call it. The integration test simulates the case where the LLM hallucinates a `parse_mft` call (via `FunctionModel` returning a hand-crafted tool call) and asserts the toolset rejects it with a `ToolNotFound`-class error.
- `_base.py` is the shared foundation for all four specialists (memory / disk / network / log). It owns `SpecialistDeps`, `SpecialistReport`, `SpecialistFinding`, `ToolCallRecord`, and the `_load_specialist_prompt` helper. The other three stories (disk/network/log specialists) re-use these without redeclaration.
- Library docs to consult via Context7 BEFORE coding (architecture §12 mandate):
  - `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic-ai"` then:
    - `query-docs` topic `"agent delegation @agent.tool usage propagation"` — the verbatim agent-delegation pattern.
    - `query-docs` topic `"MCPServerStdio tool_filter allowlist"` — the exact tool-allowlist surface.
- Vocabulary discipline: never "court-admissible." Specialist prompts use "memory forensics specialist," "cite the audit_id," "report structured findings."
- LOC budget: `memory.py` ~220, `_base.py` ~200. Comfortable margin.
- Pitfall: the specialist is constructed at import time of the investigator module — but the model resolution reads env vars. Tests must `monkeypatch.setenv` BEFORE importing the factory.
- Pitfall: `usage=ctx.usage` in the delegation — if the version of Pydantic AI installed doesn't propagate usage, tokens will not be credited against the investigator budget. The integration test should assert that after a specialist run, `ctx.usage.input_tokens` has grown by the specialist's token consumption.
