# Story — Investigator Pydantic AI Agent (model-agnostic; senior-analyst frame)

**ID:** story-investigator-agent
**Epic:** Epic 8 — Hypothesis state machine + investigator agent (Pydantic AI)
**Depends on:** story-hypothesis-types, story-hypothesis-stack, story-hypothesis-budget, story-fastmcp-server-bootstrap, story-record-observation-tool, story-record-interpretation-tool, story-record-pivot-tool
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** build the main investigator agent in `src/silentwitness_agent/investigator.py` as a Pydantic AI `Agent[InvestigatorDeps, InvestigatorResult]` whose model is selected from the `SILENTWITNESS_MODEL` env var (default `anthropic:claude-opus-4-7`), whose toolset is the SilentWitness MCP server (`MCPServerStdio("python", ["-m", "silentwitness_mcp"])`), and whose system prompt encodes the senior-analyst hypothesis-driven frame
**So that** the investigator can be swapped between Anthropic, OpenAI, Google, and Ollama via a single env var change (PRD FR3) and the agent's behaviour ("form one concrete hypothesis at a time, dispatch one specialist to test it, pivot when evidence contradicts") is built into the system prompt rather than inferred from training (context/domain/01 §4 — senior analyst mental model).

---

## File modification map

- `src/silentwitness_agent/investigator.py` — NEW — main module. Exports:
  - `InvestigatorDeps` (Pydantic frozen BaseModel): `case_dir: Path`, `examiner: str`, `stack: HypothesisStack`, `budget: BudgetEnforcer`, `pending_critiques: list[CriticVerdict]` (mutable list; the critic handler from story-critic-verdict-handling pushes CHALLENGE verdicts here, the agent reads them at start of each turn).
  - `InvestigatorResult` (Pydantic BaseModel): `hypotheses_formed: int`, `hypotheses_confirmed: int`, `hypotheses_pivoted: int`, `hypotheses_abandoned: int`, `findings_staged: int`, `total_tool_calls: int`, `total_tokens_consumed: int`, `time_elapsed_ms: float`, `final_state: Literal["COMPLETED", "MAX_ITERATIONS", "BUDGET_EXHAUSTED", "ERROR"]`.
  - `build_investigator(model: str | None = None, max_iterations: int | None = None) -> Agent[InvestigatorDeps, InvestigatorResult]` — factory. Reads `SILENTWITNESS_MODEL` (default `"anthropic:claude-opus-4-7"`) and `SILENTWITNESS_MAX_ITERS` (default 50). Constructs the Pydantic AI Agent with **`toolsets=[mcp_server]`** (NOT `mcp_servers=` — that kwarg is DEPRECATED), `capabilities=[hooks]` (NOT `hooks=[...]` — that kwarg does not exist; `capabilities=` is the real surface per Pydantic AI v1.105), `output_type=InvestigatorResult`. `max_iterations` is NOT a constructor kwarg — it is passed as `usage_limits=UsageLimits(request_limit=N)` at `agent.run()` call time (see `investigate()` below). Returns the configured Agent.
  - `async def investigate(case_dir: Path, examiner: str, prompt: str) -> InvestigatorResult` — top-level entry. Builds deps. Calls `agent.run(prompt, deps=deps, usage_limits=UsageLimits(request_limit=max_iters))`. Catches `pydantic_ai.exceptions.UsageLimitExceeded` — on catch: mark every still-ACTIVE hypothesis as ABANDONED with reason="MAX_ITERATIONS", populate the report's `Gaps` section, and return `InvestigatorResult(final_state="MAX_ITERATIONS", ...)`. Otherwise returns the parsed InvestigatorResult.
  - Target ≤350 LOC.
- `src/silentwitness_agent/prompts/investigator.md` — NEW — system prompt content (loaded by `build_investigator` at construction). Senior-analyst hypothesis-driven frame written verbatim (see §"System prompt" below). ~80 lines of Markdown. Read into a Python string via `importlib.resources` so the prompt ships in the wheel.
- `src/silentwitness_agent/prompts/__init__.py` — NEW — empty package marker.
- `tests/unit/test_investigator_build.py` — NEW — ≥7 unit tests that do NOT actually call a model (Pydantic AI's `TestModel` is used). Tests: factory reads `SILENTWITNESS_MODEL` env var; factory default is `"anthropic:claude-opus-4-7"`; factory honours `SILENTWITNESS_MAX_ITERS`; system prompt loaded from `prompts/investigator.md`; system prompt contains the hypothesis-driven sentence (string fragment "form one concrete hypothesis at a time"); MCP toolset is `MCPServerStdio` with the expected argv; `InvestigatorResult` schema fields match the documented surface.
- `tests/integration/test_investigator_provider_switch.py` — NEW — 2 integration scenarios using Pydantic AI's `TestModel` + `FunctionModel` to simulate provider switching: (a) `SILENTWITNESS_MODEL="anthropic:claude-opus-4-7"` → `agent.model` repr contains `"anthropic"` and the final audit log records `model_used="anthropic:claude-opus-4-7"`; (b) `SILENTWITNESS_MODEL="openai:gpt-5"` → `agent.model` repr contains `"openai"` and the final audit log records `model_used="openai:gpt-5"`. Network calls are stubbed via `TestModel`.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## System prompt (verbatim — write into `prompts/investigator.md`)

```
You are a senior incident response analyst working a digital forensics case.
Your method is hypothesis-driven. You form one concrete hypothesis at a time
(one sentence naming what you expect to see if your guess is right). You
dispatch a single specialist — memory, disk, network, or log — to test that
hypothesis. Based on the specialist's findings you either confirm the
hypothesis, pivot to a new one, or abandon it.

You cite a specific tool-execution audit_id for every claim you record.
You never assert a fact that is not present in cited tool output. When the
record_observation tool returns REJECTED, you read the rejection reason, you
re-read the cited tool output, and you revise your wording with the verbatim
text from the output. You do not argue with the gate.

When a tool returns an error, you read stderr carefully. You adjust your
hypothesis based on the actual failure mode (wrong OS profile, missing
symbol table, malformed evidence, evidence-registry refusal). You retry with
corrected parameters. You do not retry the same call without thinking.

When evidence contradicts your current hypothesis, you log a pivot event via
record_pivot, you name the contradicting evidence in the reason field, and
you form a new hypothesis. A refuted hypothesis is information, not failure.

When the evidence is incomplete, you record what you could not verify in
the report's Gaps section via record_narrative(section="gaps", ...). You
do not guess. Epistemic honesty — naming what you did not check — is
explicitly part of the deliverable.

You work one hypothesis at a time. You stop when the hypothesis is
confirmed or refuted. You do not run kitchen-sink collection. You are
working a case, not running a checklist.

When the critic returns a CHALLENGE on a finding you staged, you read the
challenge reason. If the reason names a missing corroboration, you dispatch
the appropriate specialist to corroborate. If the reason names an over-stated
confidence, you re-stage the interpretation with the corrected confidence.
You do not dismiss the challenge.

Vocabulary: report findings in plain forensic language. Do not use the
phrases "court-admissible," "autonomous SOC," or "eliminates
hallucinations." Use "defensible audit trail" or "survives cross-examination"
when describing the audit chain. Do not use marketing claims you cannot
substantiate from the cited tool output.
```

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the SilentWitness investigator module is importable
When  `uv run python -c "from silentwitness_agent.investigator import build_investigator, investigate, InvestigatorDeps, InvestigatorResult; print('ok')"` runs
Then  exit code is 0
And   stdout contains "ok"

Given SILENTWITNESS_MODEL env var is not set
When  build_investigator() is called
Then  agent.model resolves to the Pydantic AI string "anthropic:claude-opus-4-7"

Given SILENTWITNESS_MODEL="openai:gpt-5" is set in the env
When  build_investigator() is called
Then  agent.model resolves to "openai:gpt-5"
And   the InvestigatorResult written at end of run records model_used="openai:gpt-5"

Given SILENTWITNESS_MAX_ITERS="25" is set in the env
When  build_investigator() is called
Then  the agent is configured with max_iterations=25

Given the system prompt is loaded from prompts/investigator.md
When  the file is read at agent construction
Then  the string "form one concrete hypothesis at a time" is present
And   the string "you log a pivot event" is present
And   the string "court-admissible" does NOT appear in the prompt
And   the string "Ralph Wiggum" does NOT appear in the prompt
And   the string "autonomous SOC" does NOT appear in the prompt

Given the MCP toolset is configured
When  the agent.toolset is inspected
Then  it is an MCPServerStdio instance with command="python" and args=["-m", "silentwitness_mcp"]

Given a TestModel stub for Anthropic and one for OpenAI
When  SILENTWITNESS_MODEL="anthropic:claude-opus-4-7" and investigate() runs end-to-end
Then  the final audit JSONL line at cases/<case>/audit/agent.jsonl carries model_used="anthropic:claude-opus-4-7"

Given a TestModel stub for OpenAI
When  SILENTWITNESS_MODEL="openai:gpt-5" and investigate() runs end-to-end
Then  the final audit JSONL line carries model_used="openai:gpt-5"
And   the OpenAI provider is the one constructed (verified by mocking the provider factory)

Given tests/unit/test_investigator_build.py exists
When  `uv run pytest tests/unit/test_investigator_build.py -v` runs
Then  exit code is 0
And   ≥7 tests pass

Given tests/integration/test_investigator_provider_switch.py exists
When  `uv run pytest tests/integration/test_investigator_provider_switch.py -v` runs
Then  exit code is 0
And   both provider-switch scenarios pass
```

---

## Shell verification

```bash
# Import smoke
uv run python -c "from silentwitness_agent.investigator import build_investigator, investigate, InvestigatorDeps, InvestigatorResult; print('ok')"

# Default model resolution
uv run python -c "
import os; os.environ.pop('SILENTWITNESS_MODEL', None)
from silentwitness_agent.investigator import build_investigator
a = build_investigator()
assert 'anthropic:claude-opus-4-7' in repr(a.model), repr(a.model)
print('default OK')
"

# Provider switch
SILENTWITNESS_MODEL="openai:gpt-5" uv run python -c "
from silentwitness_agent.investigator import build_investigator
a = build_investigator()
assert 'openai' in repr(a.model).lower(), repr(a.model)
print('openai switch OK')
"

# Vocabulary discipline (system prompt audit)
! grep -i 'court-admissible\|ralph wiggum\|autonomous soc\|eliminates hallucinations' src/silentwitness_agent/prompts/investigator.md
# Must exit 0 (grep finds none → ! inverts → 0)

# Senior-analyst frame present
grep -q "form one concrete hypothesis at a time" src/silentwitness_agent/prompts/investigator.md
grep -q "you log a pivot event" src/silentwitness_agent/prompts/investigator.md

# Unit tests
uv run pytest tests/unit/test_investigator_build.py -v
# Must show ≥7 passing

# Integration (provider switch)
uv run pytest tests/integration/test_investigator_provider_switch.py -v
# Must show 2 passing

# Coverage ≥85% on investigator.py
uv run coverage run -m pytest tests/unit/test_investigator_build.py tests/integration/test_investigator_provider_switch.py
uv run coverage report --include="src/silentwitness_agent/investigator.py" --fail-under=85

# Strict typing + lint + file-size guard
uv run mypy --strict src/silentwitness_agent/investigator.py
uv run ruff check src/silentwitness_agent/investigator.py
uv run ruff format --check src/silentwitness_agent/investigator.py
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_agent/investigator.py
```

---

## Notes for coding agent

- Reference: architecture.md §5.1 verbatim — `SILENTWITNESS_MODEL` env var with default `anthropic:claude-opus-4-7`; supported model strings include `anthropic:claude-haiku-4-5`, `openai:gpt-5`, `openai:gpt-5-mini`, `google-gla:gemini-2.5-pro`, `ollama:llama-3.3-70b`, `vllm:<base_url>` via `OpenAIChatModel(base_url=...)`. **NOTE:** `anthropic:claude-sonnet-4-7` is NOT in Pydantic AI's `KnownModelName` enum (max sonnet variant is 4-6 currently — if needed, instantiate `AnthropicModel("claude-sonnet-4-7")` directly). **NOTE:** `openai:` prefix emits a `PydanticAIDeprecationWarning` in v1.105 — `openai-chat:gpt-5` is the forward-safe variant across the v2 transition. Toolset = `MCPServerStdio("python", ["-m", "silentwitness_mcp"], sampling_model=model)` (the `sampling_model=` arg goes on the `MCPServerStdio` constructor — there is NO `agent.set_mcp_sampling_model(model)` method). Use `Agent(toolsets=[mcp_server], capabilities=[hooks], output_type=...)`. Max iterations 50 default — passed at `agent.run(..., usage_limits=UsageLimits(request_limit=50))` time, NOT at Agent construction. Halts cleanly on limit (catch `UsageLimitExceeded`) and marks remaining hypotheses ABANDONED.
- Reference: architecture.md §5.1 — exact system prompt vocabulary discipline. The prompt above is the verbatim text — NO substitution of "Ralph Wiggum," "court-admissible," "autonomous SOC," "eliminates hallucinations." Describe the behaviour (read stderr; adjust hypothesis; retry with corrected params; log a pivot when contradicted) rather than naming the behaviour with community jargon.
- Reference: PRD §5 FR3 — model-agnostic via `SILENTWITNESS_MODEL`; CI-tested against ≥2 providers. The two integration tests (anthropic + openai) discharge this requirement.
- Reference: PRD §14 vocabulary discipline.
- Reference: context/.raw-design-research/02-model-agnostic-agent-libraries-survey.md §2 — Pydantic AI is MCP-native via `MCPServerStdio` / `MCPServerStreamableHTTP` (NOTE: `MCPServerHTTP` does NOT exist as a class — the streamable HTTP class is `MCPServerStreamableHTTP`); provider-agnostic via model strings; first-class `Hooks` capability via `Agent(capabilities=[hooks])`. Agent-delegation primitive for specialists (Epic 9; not this story).
- Reference: context/domain/01-dfir-foundations.md §4 — senior analyst mental model. The system prompt encodes §4.1 (named explicit hypotheses), §4.6 (pivot decision discipline), and §3.3 (hypothesis-driven over kitchen-sink triage). Do not paraphrase — the wording above is calibrated against published SANS doctrine + context/domain/01.
- Pydantic AI Agent construction shape (target API per Context7 lookup):
  ```python
  from pydantic_ai import Agent
  from pydantic_ai.mcp import MCPServerStdio

  agent = Agent(
      model=os.environ.get("SILENTWITNESS_MODEL", "anthropic:claude-opus-4-7"),
      deps_type=InvestigatorDeps,
      output_type=InvestigatorResult,
      system_prompt=SYSTEM_PROMPT,
      toolsets=[MCPServerStdio("python", ["-m", "silentwitness_mcp"])],
      hooks=[investigator_hooks(...)],  # from story-investigator-hooks
  )
  ```
- The hooks parameter wires in audit emission (story-investigator-hooks) — DO NOT inline the hook bodies here. This story owns the factory; story-investigator-hooks owns the hook callables. Import them and pass them to the Agent constructor.
- `InvestigatorDeps.pending_critiques` is the bridge to the critic handler (story-critic-verdict-handling). The list is shared mutable state: the critic handler `.append()`s CHALLENGE verdicts; the investigator agent reads them at the start of each turn via a tool or via the system-prompt template. The Pydantic AI pattern: register an `instructions` callback that consults `ctx.deps.pending_critiques` and prepends them to the next user-turn instructions. See architecture.md §5.5 ("CHALLENGE → return the verdict to the investigator with the reason and suggested_revision").
- MCP sampling model: pass `sampling_model=model` to the `MCPServerStdio(...)` constructor itself. There is NO `agent.set_mcp_sampling_model(model)` method on `Agent` in Pydantic AI v1.105 (verified against source). If the server emits prompts via Sampling, they will route to the same provider as the investigator.
- `max_iterations` enforcement: architecture §5.1 — "halts cleanly when the limit is reached, marks remaining hypotheses as ABANDONED, and writes the report's Gaps section." Implement this in `investigate()` (the wrapping coroutine), NOT in the Agent itself. There is no `max_iterations` constructor kwarg on `Agent`. Pass `usage_limits=UsageLimits(request_limit=N)` to `agent.run(...)` and catch `pydantic_ai.exceptions.UsageLimitExceeded`. On catch: call `stack.abandon` on every still-ACTIVE hypothesis with reason="MAX_ITERATIONS".
- TestModel + FunctionModel are Pydantic AI's built-in test helpers (no network, deterministic output). Use them in the integration tests to avoid actual provider calls. The provider-switch tests can mock the provider construction via `pytest monkeypatch` on the env, then assert the Agent's internal `model` attribute carries the right provider tag.
- Library docs to consult via Context7 BEFORE coding (architecture §12 mandate):
  - `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic-ai"` then:
    - `query-docs` topic `"Agent constructor model string MCPServerStdio toolsets"` — exact constructor signature and toolsets handling shifts across 0.x.
    - `query-docs` topic `"Hooks before_tool_execute after_tool_execute"` — hook registration patterns (consumed by story-investigator-hooks but factory passes them here).
    - `query-docs` topic `"TestModel FunctionModel provider switching"` — testing patterns without network.
- Vocabulary discipline: NEVER "court-admissible," NEVER "Ralph Wiggum Loop," NEVER "autonomous SOC," NEVER "eliminates hallucinations." Describe the behaviour. The grep test above is the gate.
- Pitfall: env-var reads at construction. Tests must `monkeypatch.setenv` BEFORE `build_investigator()`. The factory does NOT re-read mid-run.
- Pitfall: Pydantic AI's `Agent` requires the model string to be a known provider OR a `Model` instance. For `vllm:<base_url>` we route through `OpenAIModel(base_url=...)`; check via `model_str.startswith("vllm:")` and construct accordingly. Document this branch in a code comment.
- Pitfall: the system prompt is loaded via `importlib.resources.files("silentwitness_agent.prompts").joinpath("investigator.md").read_text(encoding="utf-8")` so it ships inside the wheel. Do NOT use `open(__file__)`-relative paths; those break under `pip install`.
- LOC budget: ~350. If approaching 400, extract `_resolve_model(model_str)` helper to a `_model.py` sibling.
