# Pydantic AI — Deep Verification

**Audit date:** 2026-06-03
**Auditor:** deep-audit research agent (fresh context)
**Pydantic AI HEAD inspected:** `2a6a1a6658afde4c154f1651a66763b248ff2b27` (2026-06-02), repo @ `/tmp/pydantic-ai-audit/`
**Latest stable tag:** `v1.105.0` (2026-06-02). v2 in beta: `v2.0.0b5`.
**Specs audited:**
- `docs/architecture.md` §1 stack row, §5.1, §5.2, §5.5
- `docs/BRAINSTORM.md` §3 Decision 5
- `docs/stories/story-investigator-agent.md`
- `docs/stories/story-investigator-hooks.md`
- `docs/stories/story-memory-specialist.md`
- `docs/stories/story-critic-agent.md`
- `docs/stories/story-critic-trigger.md`
- `docs/stories/story-critic-verdict-handling.md`
- `context/.raw-design-research/02-model-agnostic-agent-libraries-survey.md`

## TL;DR

- Pydantic AI v1.105.0 is the correct pick. The library exists, is MIT, is active (daily commits), and has every primitive the SilentWitness spec set assumes. The strategic choice is sound.
- BUT the specs encode several wrong **API surface names** that will cause stories to fail when the coding agent types them verbatim:
  - `Agent(hooks=[...])` — **WRONG**. The actual kwarg is `Agent(capabilities=[hooks])`. There is no `hooks=` parameter.
  - Hook names `on_step` / `on_finish` — **DO NOT EXIST**. Closest equivalents are `after_run` (for "finish") and `before_node_run` / `after_node_run` (for "step").
  - `MCPServerStdio(..., tool_filter=callable)` — **DOES NOT EXIST**. The pattern is `MCPServerStdio(...).filtered(lambda ctx, td: td.name in ALLOWLIST)`.
  - `MCPServerHTTP` — **WRONG NAME**. Actual classes are `MCPServerStreamableHTTP` and `MCPServerSSE`.
  - `Agent(mcp_servers=...)` — **DEPRECATED in v1**, removed in v2. Use `toolsets=[server]`.
  - `max_iterations=N` constructor kwarg — **DOES NOT EXIST**. The cap is enforced via `UsageLimits(request_limit=N)` and `UsageLimitExceeded`.
- Model strings are mostly correct: `anthropic:claude-opus-4-7`, `openai:gpt-5`, `google-gla:gemini-2.5-pro`, `ollama:llama-3.3-70b` (the last as runtime-only str, not in the KnownModelName Literal), `anthropic:claude-haiku-4-5` are all parseable today. One landmine: in v1.105 `openai:` issues a DEPRECATION WARNING and currently resolves to Chat Completions; in v2 it will resolve to the Responses API by default — use `openai-chat:gpt-5` if you want stable Chat-Completions behaviour across the v1→v2 boundary.
- The architectural intent of the specs (hooks for audit; agent-delegation for specialists; provider-agnostic model strings; native MCP) all map cleanly to real Pydantic AI primitives. The fix is **terminology + a small substitution table**, not a redesign.

---

## Per-claim verdict

### Claim 1: Pydantic AI has Hooks (PreToolUse / PostToolUse / OnStep / OnFinish)

**Status:** PARTIAL — the primitive exists; the specific names + the Agent constructor kwarg are wrong.

**Evidence (from cloned source):**

- The `Hooks` capability is real and lives at `/tmp/pydantic-ai-audit/pydantic_ai_slim/pydantic_ai/capabilities/hooks.py` (1307 lines). Exported as `from pydantic_ai.capabilities import Hooks` and `from pydantic_ai import Hooks` (re-exported in `pydantic_ai_slim/pydantic_ai/__init__.py`).
- Construction pattern (verbatim from `docs/hooks.md` quick-start, lines 12–30):

  ```python
  from pydantic_ai import Agent, ModelRequestContext, RunContext
  from pydantic_ai.capabilities import Hooks

  hooks = Hooks()

  @hooks.on.before_model_request
  async def log_request(ctx, request_context):
      return request_context

  agent = Agent('test', capabilities=[hooks])   # NOTE: capabilities=, NOT hooks=
  ```

- Available hook decorators on `hooks.on` (verified at `hooks.py:314-707`):
  - Run lifecycle: `before_run`, `after_run`, `run` (wrap), `run_error`
  - Node lifecycle: `before_node_run`, `after_node_run`, `node_run` (wrap), `node_run_error`
  - Model request: `before_model_request`, `after_model_request`, `model_request` (wrap), `model_request_error`
  - Tool execution: `before_tool_execute`, `after_tool_execute`, `tool_execute` (wrap), `tool_execute_error` — all support `tools=[name, ...]` filter
  - Tool validation: `before_tool_validate`, `after_tool_validate`, `tool_validate`, `tool_validate_error`
  - Output validate / process families (`before_output_validate` etc.)
  - Event stream: `run_event_stream`, `event` (per-event)
  - `prepare_tools`, `prepare_output_tools`, `deferred_tool_calls`
- All hooks support `timeout=N` (raises `HookTimeoutError` — `hooks.py:64`). Tool-family hooks additionally support `tools=Sequence[str]` filter (`hooks.py:546-606`).
- Constructor-kwarg form also works: `Hooks(before_tool_execute=fn, after_tool_execute=fn2, ...)` (`hooks.py:746-797`).
- `Agent` constructor signature (`pydantic_ai_slim/pydantic_ai/agent/__init__.py:321-342`) takes `capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None`. There is NO `hooks=` parameter at any version since v1.71.

**Mapping of SilentWitness's claimed hook list to real hook names:**

| Spec claim (`story-investigator-hooks.md`) | Real Pydantic AI hook | File:line |
|---|---|---|
| `before_tool_execute` | `hooks.on.before_tool_execute` ✓ EXACT | `hooks.py:548-561` |
| `after_tool_execute` | `hooks.on.after_tool_execute` ✓ EXACT | `hooks.py:563-576` |
| `on_step` | NOT A REAL HOOK. Closest: `hooks.on.before_node_run` / `hooks.on.after_node_run` (fires per graph step — `UserPromptNode`, `ModelRequestNode`, `CallToolsNode`). For per-LLM-call cadence specifically, use `hooks.on.after_model_request` (fires once per model request inside each node). | `hooks.py:370-402`, `426-460` |
| `on_finish` | NOT A REAL HOOK. Use `hooks.on.after_run` — receives `result: AgentRunResult[Any]`, fires exactly once at end of an `agent.run()`. | `hooks.py:347-352`, `877-880` |

**Spec implication:**

- BLOCKER: every story that does `Agent(..., hooks=[hooks])` will fail at construction (unknown kwarg). The constructor signature explicitly only accepts `capabilities=`.
- BLOCKER for `story-investigator-hooks` story-line: the BDD acceptance criteria require `_on_step` and `_on_finish` callbacks. These names map to nothing. The story needs to be rewritten as `_on_after_model_request` (per-LLM-call delta) + `_on_after_run` (final snapshot). The semantics are preserved; the names change.
- FIX-IT: `story-investigator-hooks` system-prompt-style code snippet showing `@hooks.on.step()` / `@hooks.on.finish()` is wrong — those decorators do not exist on `_HookRegistration`.

**Required rewrite (story-investigator-hooks.md):**

```python
from pydantic_ai.capabilities import Hooks
from pydantic_ai import RunContext, ModelRequestContext
from pydantic_ai.messages import ModelResponse

hooks = Hooks()

@hooks.on.before_tool_execute   # bare or @hooks.on.before_tool_execute() for params
async def _on_before_tool(ctx, *, call, tool_def, args):
    ...
    return args  # MUST return args (it is the validated args passed through)

@hooks.on.after_tool_execute
async def _on_after_tool(ctx, *, call, tool_def, args, result):
    ...
    return result

@hooks.on.after_model_request   # replaces "on_step"
async def _on_step(ctx, *, request_context, response):
    # access usage delta via response.usage (RunUsage carries input_tokens/output_tokens)
    return response

@hooks.on.after_run             # replaces "on_finish"
async def _on_finish(ctx, *, result):
    # result is AgentRunResult — exposes .output, .usage(), .all_messages()
    return result
```

Then bind:

```python
agent = Agent(
    model=os.environ.get("SILENTWITNESS_MODEL", "anthropic:claude-opus-4-7"),
    deps_type=InvestigatorDeps,
    output_type=InvestigatorResult,
    system_prompt=SYSTEM_PROMPT,
    toolsets=[MCPServerStdio("python", ["-m", "silentwitness_mcp"])],
    capabilities=[hooks],          # NOT hooks=[hooks]
)
```

---

### Claim 2: agent-delegation is a real primitive for subagents

**Status:** VALIDATED. The pattern is exactly what the survey + specs describe.

**Evidence:**

- Documented under `docs/multi-agent-applications.md` §"Agent delegation" (lines 13-77).
- Canonical pattern (verbatim, `multi-agent-applications.md:25-57`):

  ```python
  joke_selection_agent = Agent('openai:gpt-5.2', instructions='...')
  joke_generation_agent = Agent('google:gemini-3-flash-preview', output_type=list[str])

  @joke_selection_agent.tool
  async def joke_factory(ctx: RunContext[None], count: int) -> list[str]:
      r = await joke_generation_agent.run(
          f'Please generate {count} jokes.',
          usage=ctx.usage,                # this is the load-bearing line
      )
      return r.output
  ```

- `usage=ctx.usage` is documented as "you'll generally want to pass" so parent-agent token usage rolls up. This is exactly what `story-memory-specialist.md` documents in its Notes section. ✓
- `RunContext.usage` is real and exposes the running `RunUsage` (`pydantic_ai_slim/pydantic_ai/usage.py:182`, `RunUsage` extends `UsageBase` and has `input_tokens`, `output_tokens`, `requests`, etc.).
- Context isolation: each `agent.run(..., deps=specialist_deps, ...)` has its own `RunContext` and its own message history. The delegate agent does NOT see the parent agent's messages. The `usage=ctx.usage` propagation is the ONLY thing that crosses the boundary (plus whatever the parent puts into the delegate's prompt). This matches the "fresh context" property the specs assume for the critic too.

**Spec implication:**

- KEEP `story-memory-specialist`, `story-disk-specialist`, `story-network-specialist`, `story-log-specialist` as currently written for the delegation pattern. The shape is correct.
- KEEP the `usage=ctx.usage` propagation guidance in `story-memory-specialist.md` Notes (line 232 in the file).
- The `architecture.md` §5.2 wording ("subagents via Pydantic AI agent-delegation") is accurate. No change needed.

---

### Claim 3: Model-string switching across providers works

**Status:** PARTIAL — the prefixes work, but two important caveats.

**Evidence (from `pydantic_ai_slim/pydantic_ai/models/__init__.py`):**

- `KnownModelName` Literal enumerates every supported string at lines 72-580. Confirmed entries relevant to SilentWitness:
  - `'anthropic:claude-opus-4-7'` — line 86 ✓
  - `'anthropic:claude-opus-4-5'`, `'anthropic:claude-opus-4-6'`, `'anthropic:claude-opus-4-8'` — also present
  - `'anthropic:claude-haiku-4-5'` — line 78 ✓ (`SILENTWITNESS_SPECIALIST_MODEL_MEMORY` default)
  - `'anthropic:claude-sonnet-4-7'` — NOT in the Literal. The available sonnets are `claude-sonnet-4-0`, `claude-sonnet-4-5`, `claude-sonnet-4-6`. **SilentWitness's claimed `anthropic:claude-sonnet-4-7` does not exist.** Use `claude-sonnet-4-6` (or wait for it to land — `KnownModelName` has only `4-0`/`4-5`/`4-6`).
  - `'openai:gpt-5'` — present (line ~580) ✓
  - `'openai:gpt-5-mini'` — present ✓
  - `'google:gemini-2.5-pro'` — present (line 283) ✓
  - `'google-cloud:gemini-2.5-pro'` — present (line 266) ✓
- `infer_model` (lines 1544-1644) handles prefixes by `provider_name` extracted from the colon-separated model id:
  - `'anthropic'` → `AnthropicModel` (line 1627)
  - `'openai'` / `'openai-chat'` → `OpenAIChatModel` — **emits `PydanticAIDeprecationWarning`** saying v2 will switch `openai:` to `OpenAIResponsesModel` (lines 1597-1603)
  - `'openai-responses'` → `OpenAIResponsesModel` (line 1607)
  - `'google'` / `'google-gla'` / `'google-vertex'` / `'google-cloud'` all route to `GoogleModel` (line 1611) ✓
  - `'ollama'` → `OllamaModel` (line 1591) ✓
  - `'vllm'` is NOT a prefix — there is no vllm branch. The spec is right that the route is `OpenAIChatModel(base_url=...)` via the `OpenAIChatCompatibleProvider` mechanism. There is also a `'fireworks'`, `'together'`, `'openrouter'`, etc., but no `vllm:` shortcut. **`SILENTWITNESS_MODEL="vllm:..."` will raise `UserError("Unknown model")`.**
- `ollama:llama-3.3-70b` — `ollama` IS a real prefix that routes to `OllamaModel` (a subclass of `OpenAIChatModel`). The Literal does not enumerate ollama model IDs (none are in `KnownModelName`), so static type checkers will warn, but at runtime `Agent('ollama:llama-3.3-70b')` will pass `'llama-3.3-70b'` to OllamaModel. Note: Ollama needs a `base_url` — set via `OLLAMA_BASE_URL` env or by constructing `OllamaProvider(base_url=...)` and passing the model object directly to `Agent`.
- Provider extras (`pydantic-ai-slim[openai,vertexai,google,xai,groq,anthropic,mistral,cohere,bedrock,huggingface,cli,mcp,fastmcp,...]` per `pyproject.toml:metadata.hooks.uv-dynamic-versioning`):
  - `[anthropic]`, `[openai]`, `[google]`, `[google-gla]` — present
  - `[ollama]` — present (pulls openai package since ollama uses openai-compat API)
  - No `[vllm]` extra — vLLM routes through `[openai]` with custom base_url
  - The spec's `pydantic-ai[anthropic,openai,google-gla,ollama]` is a valid extras combo.

**Spec implication:**

- FIX-IT: `architecture.md §5.1` supported-models list has `anthropic:claude-sonnet-4-7` which does not exist in `KnownModelName` as of v1.105. Replace with `anthropic:claude-sonnet-4-6` or `anthropic:claude-sonnet-4-5` (whichever Anthropic ships as the long-context default at hackathon time). Same fix in `story-investigator-agent.md` notes.
- FIX-IT: `architecture.md §5.1` says `vllm:<base_url>` via `OpenAIModel(base_url=...)` — this is correct in spirit, but it requires the agent factory to special-case `model_str.startswith("vllm:")`, build an `OpenAIChatModel(base_url=...)` instance directly, and pass it as a `Model` object to `Agent(model=...)` (not as a string). The story `story-investigator-agent.md` already notes this in the Pitfall section (good). Verbiage check: change references to `OpenAIModel(base_url=...)` to `OpenAIChatModel(base_url=...)` — that is the actual class name (`OpenAIModel` no longer exists in v1.105; the splits are `OpenAIChatModel` and `OpenAIResponsesModel`).
- NOTE: `openai:gpt-5` emits a `PydanticAIDeprecationWarning` in v1.105 and will silently change behaviour at v2.0. For SilentWitness, pin to `openai-chat:gpt-5` if Chat Completions semantics are required, or accept the warning and live with v2's Responses-API default. Document this in the README and in the test that asserts `'openai' in repr(a.model).lower()` (story BDD line 99-100 / shell verification line 156-161).
- The default `anthropic:claude-opus-4-7` works. Pin this.

---

### Claim 4: Native MCP integration (`mcp_servers` kwarg)

**Status:** PARTIAL — MCP integration IS native and excellent. `mcp_servers=` is DEPRECATED in v1 and removed in v2. The class names the spec uses are partly wrong.

**Evidence:**

- MCP module: `/tmp/pydantic-ai-audit/pydantic_ai_slim/pydantic_ai/mcp.py` (2300+ lines).
- Classes exposed (from `mcp.py` grep):
  - `MCPServer` (abstract base)
  - `MCPServerStdio` (line 1406) — `__init__(command: str, args: Sequence[str], *, env, cwd, tool_prefix, log_level, log_handler, timeout=5, read_timeout=300, process_tool_call, allow_sampling=True, sampling_model=None, max_retries=1, elicitation_callback, cache_prompts=True, cache_tools=True, cache_resources=True, include_instructions=False, ...)`
  - `MCPServerSSE` (HTTP SSE transport)
  - `MCPServerStreamableHTTP` (line 2098) — the modern Streamable HTTP transport
  - `MCPToolset` (FastMCP-based, the *recommended* path for new code per docstrings at `mcp.py:692`)
  - There is NO class called `MCPServerHTTP`. The architecture.md §1 row writes `MCPServerStdio` / `MCPServerHTTP` toolsets — the second name is wrong.
- `Agent` constructor (`agent/__init__.py:321-342`):
  - `toolsets: Sequence[AgentToolset[AgentDepsT]] | None = None` — the canonical kwarg (line 287/335)
  - `mcp_servers: Sequence[MCPServer] = ()` — **explicitly deprecated** via `@deprecated('`mcp_servers` is deprecated, use `toolsets` instead.')` overload at line 297. At line 461-465 the runtime emits a `DeprecationWarning` and remaps `mcp_servers` into `toolsets`. Will be removed in v2.
- Canonical example (verbatim, `mcp.py:1416-1424` docstring):

  ```python
  from pydantic_ai import Agent
  from pydantic_ai.mcp import MCPServerStdio
  server = MCPServerStdio('uv', args=['run', 'mcp-run-python', 'stdio'], timeout=10)
  agent = Agent('openai:gpt-5.2', toolsets=[server])
  ```

- Streamable HTTP (verbatim from `docs/mcp/client.md` lines 1-50 area): `MCPServerStreamableHTTP(url='http://localhost:4508/mcp', ...)` registered via `toolsets=[...]`. Bearer auth via `headers={'Authorization': f'Bearer {TOKEN}'}` parameter.
- Tool filtering / allowlist: there is NO `tool_filter=` constructor kwarg on `MCPServerStdio`. The mechanism is the `.filtered(filter_func)` method inherited from `AbstractToolset` (`pydantic_ai_slim/pydantic_ai/toolsets/abstract.py:192-201`). Pattern:

  ```python
  toolset = MCPServerStdio("python", ["-m", "silentwitness_mcp"]).filtered(
      lambda ctx, td: td.name in MEMORY_TOOL_ALLOWLIST
  )
  agent = Agent(..., toolsets=[toolset])
  ```

  `FilteredToolset` is at `pydantic_ai_slim/pydantic_ai/toolsets/filtered.py` and exported at `pydantic_ai.FilteredToolset`. The filter function receives `(ctx, tool_def)` where `tool_def` carries `.name`. Sync OR async filter functions accepted.

- Sampling: every MCP server class accepts `sampling_model: Model | None = None` as a kwarg at construction (`MCPServerStdio.__init__:1476`). The architecture.md §5.1 calls `agent.set_mcp_sampling_model(model)` — that method DOES NOT exist on the v1.105 `Agent`. The correct pattern is to pass `sampling_model=...` at MCPServer construction, OR mutate `server.sampling_model = ...` post-hoc (the field is mutable per the dataclass declaration at line 1454).

**Spec implication:**

- FIX-IT (BLOCKING): `architecture.md §1` "MCPServerStdio / MCPServerHTTP toolsets" → change "MCPServerHTTP" to "MCPServerStreamableHTTP" everywhere. Search for "MCPServerHTTP" in all specs and replace.
- FIX-IT: all stories that say `Agent(..., mcp_servers=[server])` need to say `Agent(..., toolsets=[server])`. The spec's investigator story already uses `toolsets=`, good. But check `story-investigator-agent.md` Notes section line 211 — it correctly uses `toolsets=[MCPServerStdio(...)]`. ✓
- FIX-IT: `story-memory-specialist.md` line 234 references `MCPServerStdio(..., tool_filter=callable)` as the spec's intended allowlist API. This kwarg does not exist. Rewrite to:

  ```python
  ALLOWLIST = MEMORY_TOOL_ALLOWLIST
  toolset = MCPServerStdio("python", ["-m", "silentwitness_mcp"]).filtered(
      lambda ctx, td: td.name in ALLOWLIST
  )
  ```

  Same fix applies to disk/network/log specialist stories.
- FIX-IT: `architecture.md §5.1` says "Sampling enabled via `agent.set_mcp_sampling_model(model)`." This method doesn't exist. Replace with: "Sampling enabled by passing `sampling_model=` at MCPServerStdio construction (or by setting `server.sampling_model` post-hoc)." `story-investigator-agent.md` Notes line 216 already has a `try/except AttributeError` wrapper for `set_mcp_sampling_model` — that defensive wrapping is the right instinct since the method doesn't exist; the wrapper just silently no-ops. Cleaner: drop the call and use the construction-time arg.
- NOTE: There is also a newer `MCPToolset` (FastMCP-based) that the upstream docs call "recommended" for new code. For the hackathon we keep `MCPServerStdio` for parity with the `mcp` SDK + FastMCP server we ship. Both work. Document the choice in an ADR.

---

### Claim 5: Maturity + breaking changes risk

**Status:** VALIDATED with caveats. Pin to v1.105.

**Live numbers (2026-06-03):**

- Stars: **17,476** (was 17.5K when survey was written; growth confirmed)
- Open issues: **586** (healthy ratio for a 17.5K-star project; survey said 584)
- Bug-labeled issues: **71** open
- Last push: **2026-06-02** (yesterday)
- License: **MIT** ✓

**Tag landscape (verified via `git tag --sort=-creatordate`):**

- Stable line: ... v1.93 → v1.94 → ... → v1.103 → v1.104 → **v1.105.0** (2026-06-02)
- v2 betas: v2.0.0b1 → b2 → b3 → b4 → **v2.0.0b5** (2026-06-02)
- Frequency: ~1 minor every 2-3 weeks since v1.0 (Sept 2025). Twelve minor releases between Jan 2026 and June 2026.

**Breaking change risk Jan-Jun 2026:**

- Official policy from `docs/changelog.md` line 3: "In September 2025, Pydantic AI reached V1, which means we're committed to API stability: we will not introduce changes that break your code until V2."
- v1.x changelog from v1.0 → v1.105 lists ZERO breaking changes per the upgrade guide. The Hooks/Capabilities API landed in **v1.71** as a NON-breaking additive change (per the Medium migration article).
- v2.0 IS coming (currently in beta b5). Key v2 breakage:
  - `mcp_servers=` is REMOVED (already deprecated in v1)
  - `openai:` model strings switch from Chat Completions → Responses API by default
  - Bare `pydantic-ai` install ships fewer extras (must explicitly add `bedrock`, `groq`, `mistral`)
  - Some toolsets default to `end_strategy='graceful'` instead of skipping
  - Instrumentation defaults bump to v5
- The upgrade-to-v2 path recommended by Pydantic team: upgrade to v1.100+ first, fix all DeprecationWarnings, THEN install v2 beta. SilentWitness should stay on v1.x for the hackathon and not chase v2.

**Hooks-related open issues** (from GitHub search `repo:pydantic/pydantic-ai is:open is:issue hooks in:title`): **2 total**:
- #4971 "Ability to register Hooks and Capabilities globally for a process" — enhancement, non-blocking
- #3359 "History and Message (De)Serialization hooks to prevent hitting Temporal payload size limit" — Temporal-specific, non-blocking

**MCP-related open issues** (from `mcp in:title`): **19 total**, dominant themes are:
- Multi-server tool annotation edge cases (#5419, #1526)
- OAuth flow polish (#1957)
- Stateless connection support (#1844)
- None are blocking for the SilentWitness shape (single MCPServerStdio per agent + Streamable HTTP secondary).

**Pin recommendation:**

```toml
# pyproject.toml
[project]
dependencies = [
    "pydantic-ai[anthropic,openai,google,ollama,mcp,fastmcp]>=1.105.0,<2.0.0",
    ...
]
```

Why:
- `>=1.105.0` — the version with the verified Hooks API + the model strings the spec uses (Opus 4.7, Haiku 4.5, GPT-5, Gemini 2.5 Pro)
- `<2.0.0` — v2 will break `mcp_servers` (already deprecated; we don't use it) and silently shift `openai:` to Responses API (we DO use `openai:gpt-5`). Locking out v2 forces a deliberate upgrade decision.
- Extras: `[anthropic,openai,google,ollama,mcp,fastmcp]`. Note `google` not `google-gla` for the extra — `google-gla` is a model-string prefix routed by `GoogleModel`; the extra is just `[google]`. Adding `[fastmcp]` future-proofs us if we switch from `MCPServerStdio` to `MCPToolset`.

---

### Additional check — system prompt strategy

**Status:** VALIDATED.

- `Agent.__init__` accepts `system_prompt: str | Sequence[str] = ()` (`agent/__init__.py:279, 304, 327`).
- Loading via `system_prompt=Path("prompts/investigator.md").read_text(encoding='utf-8')` works — it's just a string.
- The story's preferred pattern `importlib.resources.files("silentwitness_agent.prompts").joinpath("investigator.md").read_text(encoding="utf-8")` works identically (returns a string).
- There is ALSO an `@agent.system_prompt` decorator for dynamic system prompts (e.g., per-run context injection). Useful for the `pending_critiques` injection bridge in `story-investigator-agent.md` Notes line 215 — instead of an `instructions` callback, use:

  ```python
  @agent.instructions
  async def inject_pending_critiques(ctx: RunContext[InvestigatorDeps]) -> str:
      if not ctx.deps.pending_critiques:
          return ""
      lines = ["Critic challenges pending:"]
      for v in ctx.deps.pending_critiques:
          lines.append(f"- {v.finding_id}: {v.reason}")
      return "\n".join(lines)
  ```

  `instructions` (note: not `system_prompt` — `system_prompt` decorator is the legacy path) — confirmed via `Agent.__init__` kwarg `instructions: AgentInstructions[AgentDepsT] = None` (line 278) and `@agent.instructions` decorator pattern documented at `docs/agents.md`.

---

## Additional findings

1. **`Hooks` is a `Capability`, not a separate primitive.** The spec set sometimes treats Hooks as a top-level concept; in v1.105 it IS a top-level concept but its mechanical implementation is `class Hooks(AbstractCapability)`. Knowing this matters because: (a) you can combine Hooks with other Capabilities (`capabilities=[hooks, instrumentation, other_cap]`); (b) anything Hooks can do, an `AbstractCapability` subclass can do more cleanly if you're building reusable audit infrastructure. For a hackathon, stick with `Hooks` — it's the documented short path.

2. **`event_stream_handler` deprecated; use `hooks.on.event` or a `ProcessEventStream` capability.** If we want to capture every streamed `AgentStreamEvent` (e.g., the model's reasoning rationale before a tool call — useful for the demo's "explain what you're about to do" moment), `@hooks.on.event` is the right path.

3. **`max_iterations` is not a real concept in Pydantic AI.** The agent runs until the model produces a final output OR a `UsageLimits` ceiling is hit. The spec's `SILENTWITNESS_MAX_ITERS=50` needs to map to `UsageLimits(request_limit=50)` and the wrapping coroutine catches `UsageLimitExceeded` (which IS defined at `pydantic_ai_slim/pydantic_ai/exceptions.py:195`). `story-investigator-agent.md` Notes line 217 already names `UsageLimitExceeded` — good — but the BDD criterion at line 102-104 says "the agent is configured with max_iterations=25" which doesn't map to any real Agent kwarg. Replace BDD criterion with "agent runs with usage_limits=UsageLimits(request_limit=25)" or assert that wrapping the run with `usage_limits=` kwarg on `agent.run(...)` enforces the cap.

4. **`agent.toolsets` is not the public attribute name.** The story-critic-agent BDD at line 122-124 asserts `agent.toolsets is empty`. The Agent does not expose a public `toolsets` attribute in v1.105 — internally it's `self._user_toolsets`, `self._dynamic_toolsets`, `self._cap_toolsets`, `self._function_toolset` (see `agent/__init__.py:519-537`). The safe way to assert "no MCP toolset" is to inspect the internal `_user_toolsets` list or use the new `agent.toolset` aggregated property if it exists. SAFER: don't assert via internals; instead assert via behaviour: construct the critic agent, call `await agent.run(...)` with a `TestModel`, and verify the test model's `available_tools` list is empty (or contains only output tools). This is a less brittle BDD.

5. **The DeprecationWarning on `openai:` is real and gets emitted on EVERY call.** If we ship a demo that says "watch the model fly," and judges see `PydanticAIDeprecationWarning` on stderr every time, that looks worse than it is. Filter the warning explicitly:

   ```python
   import warnings
   from pydantic_ai.exceptions import PydanticAIDeprecationWarning
   warnings.filterwarnings("ignore", category=PydanticAIDeprecationWarning, message=".*openai:.*")
   ```

   Or pin to `openai-chat:gpt-5` and bypass it entirely. Recommended: `openai-chat:gpt-5` (it is explicit about Chat Completions, and survives the v2 transition unchanged).

6. **`TestModel` and `FunctionModel`** the BDD/integration tests reference — both EXIST. `from pydantic_ai.models.test import TestModel`. `from pydantic_ai.models.function import FunctionModel`. They are in v1.105. The story tests using them are sound.

7. **No `RunHooks`/`AgentHooks` confusion.** Those are OpenAI Agents SDK names (the runner-up framework in the survey). The Pydantic AI surface is `Hooks` (singular). Make sure copy-pasted code from the survey or from prior team experience with OpenAI Agents doesn't leak.

---

## Recommendations for spec adjustments

Listed by impact.

### BLOCKER (fix before coding agent starts on these stories)

1. **`Agent(hooks=[...])` → `Agent(capabilities=[hooks])`** — search/replace across:
   - `architecture.md` §5.1, §5.2, §5.5
   - `story-investigator-agent.md` Notes (line 212)
   - `story-investigator-hooks.md` Notes (line 142-164 has the code snippet)
   - `story-critic-agent.md` (if it uses the pattern)
   The constructor will reject `hooks=` as an unknown kwarg and crash at `Agent(...)`.

2. **`on_step` / `on_finish` hook names** in `story-investigator-hooks.md` — replace per the table in Claim 1 above. Use `hooks.on.after_model_request` for the "step" role (per-LLM-request delta — fits the token-accounting use case) and `hooks.on.after_run` for the "finish" role (final snapshot — fits the report-as-state save).

3. **`MCPServerHTTP` → `MCPServerStreamableHTTP`** in `architecture.md` §1, §7.3, and any other reference.

4. **`MCPServerStdio(tool_filter=...)` → `MCPServerStdio(...).filtered(...)`** in the four specialist stories (memory/disk/network/log). Pattern verified at `pydantic_ai_slim/pydantic_ai/toolsets/abstract.py:192-201` and `toolsets/filtered.py`.

5. **`max_iterations=` constructor arg** doesn't exist. Reshape `story-investigator-agent.md` BDD line 102-104 + `architecture.md §5.1` to use `UsageLimits(request_limit=...)` passed at `agent.run(...)` time, with `UsageLimitExceeded` caught in the wrapping coroutine.

### FIX-IT (real but lower-blast-radius)

6. **`anthropic:claude-sonnet-4-7`** in supported-models list (architecture.md §5.1) doesn't exist as of v1.105 `KnownModelName`. Substitute `anthropic:claude-sonnet-4-6` or `anthropic:claude-sonnet-4-5`. If a 4-7 sonnet lands by hackathon time, easy swap.

7. **`agent.set_mcp_sampling_model(model)`** in `architecture.md §5.1` and `story-investigator-agent.md` Notes line 216 — this method doesn't exist. Replace with passing `sampling_model=Model` at `MCPServerStdio(...)` construction time. Drop the `try/except AttributeError` defensive wrap (it papers over a no-op).

8. **`OpenAIModel`** referenced in `architecture.md §5.1` ("OpenAIModel(base_url=...)") is no longer a class name in v1.105. Use `OpenAIChatModel(base_url=...)` (from `pydantic_ai.models.openai import OpenAIChatModel`) or `OpenAIResponsesModel` depending on which API surface the custom endpoint speaks. vLLM speaks Chat Completions, so `OpenAIChatModel`.

9. **`agent.toolsets`** attribute access in BDD assertions (story-critic-agent line 122-124) — not a public surface. Replace BDD with behavioural assertion (the critic agent's run should expose no callable tools to its `TestModel`/`FunctionModel`).

10. **`openai:gpt-5` DeprecationWarning** — either pin to `openai-chat:gpt-5` everywhere, or filter the warning explicitly. Pick one and apply consistently across architecture.md, story-investigator-agent.md, story-critic-agent.md, and the supported-models matrix.

### NOTE (informational; no code change required)

11. **Pin v1.x, not v2 beta.** Lock the project to `pydantic-ai>=1.105.0,<2.0.0`. The v2 beta is moving but it's not production-stable yet and the v1 → v2 migration is a separate-PR task. Migration is straightforward (the changelog is small) and best done post-hackathon.

12. **Instructions vs system_prompt for pending_critiques bridge.** Use `@agent.instructions` (dynamic per-run) rather than mutating `system_prompt` (static). `story-investigator-agent.md` Notes line 215 already suggests "an `instructions` callback" — correct. Make sure the story implementation uses `@agent.instructions` not `@agent.system_prompt`.

13. **The library survey at `context/.raw-design-research/02-...md` says "Pydantic AI 1.105+".** That was prescient — it's now the latest stable. Keep the survey's recommendation.

---

## Pin recommendation

```toml
[project]
dependencies = [
    "pydantic-ai[anthropic,openai,google,ollama,mcp,fastmcp]>=1.105.0,<2.0.0",
    # ... other deps
]
```

- **Lower bound `>=1.105.0`** — the version with all the API surface the verified spec uses (Hooks with `tools=` filter, FilteredToolset, MCPServerStdio with sampling_model kwarg, model strings for Opus 4.7, GPT-5, Gemini 2.5 Pro, Ollama Llama 3.3).
- **Upper bound `<2.0.0`** — v2 breaks `mcp_servers` kwarg (we don't use it), changes `openai:` semantics (we do use it; if we pin `openai-chat:` this stops mattering), and reshuffles extras. We should do the v2 migration as a deliberate post-hackathon PR.
- **Extras** — `[anthropic,openai,google,ollama,mcp,fastmcp]`. Each is pulled separately because v2 will stop including them in the bare install. Including `[fastmcp]` keeps `MCPToolset` available if we want to migrate from `MCPServerStdio`.

---

## Sources

### Repository inspected (cloned 2026-06-03)

- **Repo:** https://github.com/pydantic/pydantic-ai
- **HEAD:** `2a6a1a6658afde4c154f1651a66763b248ff2b27` (2026-06-02, "Add Grok 4.3 reasoning_effort support")
- **Local path:** `/tmp/pydantic-ai-audit/`

### Key file:line references

- `pydantic_ai_slim/pydantic_ai/capabilities/hooks.py:1-1307` — Hooks class, decorator registry, all hook function protocols
- `pydantic_ai_slim/pydantic_ai/capabilities/hooks.py:336-707` — `_HookRegistration` namespace (the `hooks.on` decorators)
- `pydantic_ai_slim/pydantic_ai/capabilities/hooks.py:178-192` — `BeforeToolExecuteHookFunc`, `AfterToolExecuteHookFunc` protocols (verbatim signatures)
- `pydantic_ai_slim/pydantic_ai/agent/__init__.py:272-342` — `Agent.__init__` signature with `capabilities=` and deprecated `mcp_servers=` overloads
- `pydantic_ai_slim/pydantic_ai/agent/__init__.py:461-465` — `mcp_servers` deprecation runtime warning
- `pydantic_ai_slim/pydantic_ai/mcp.py:1406-1539` — `MCPServerStdio.__init__` full signature
- `pydantic_ai_slim/pydantic_ai/mcp.py:2098-2280` — `MCPServerStreamableHTTP` class
- `pydantic_ai_slim/pydantic_ai/toolsets/abstract.py:192-201` — `.filtered()` method
- `pydantic_ai_slim/pydantic_ai/toolsets/filtered.py:1-32` — `FilteredToolset` implementation
- `pydantic_ai_slim/pydantic_ai/models/__init__.py:72-580` — `KnownModelName` Literal (all supported model strings)
- `pydantic_ai_slim/pydantic_ai/models/__init__.py:1544-1644` — `infer_model` provider dispatch
- `pydantic_ai_slim/pydantic_ai/usage.py:182-260` — `RunUsage`
- `pydantic_ai_slim/pydantic_ai/usage.py:260-420` — `UsageLimits` + `UsageLimitExceeded` enforcement
- `pydantic_ai_slim/pydantic_ai/exceptions.py:195` — `UsageLimitExceeded`

### Documentation (in-tree)

- `docs/hooks.md:1-345` — Hooks quick-start, hook tables, tool filtering, timeouts
- `docs/capabilities.md` — full capabilities concept doc
- `docs/multi-agent-applications.md:13-77` — agent delegation pattern (verbatim)
- `docs/mcp/client.md` — MCPServerStdio / MCPServerStreamableHTTP examples
- `docs/changelog.md` — upgrade guide

### Web sources

- GitHub repo stats API (live, 2026-06-03): https://api.github.com/repos/pydantic/pydantic-ai — 17,476 stars, 586 open issues, MIT, last push 2026-06-02
- Bug-labeled open issues: https://api.github.com/search/issues?q=repo:pydantic/pydantic-ai+is:open+is:issue+label:bug — **71 open**
- Hooks-titled issues: https://api.github.com/search/issues?q=repo:pydantic/pydantic-ai+is:open+is:issue+hooks+in:title — **2 open** (#4971, #3359; both non-blocking)
- MCP-titled issues: https://api.github.com/search/issues?q=repo:pydantic/pydantic-ai+is:open+is:issue+mcp+in:title — **19 open** (mostly enhancement)
- v1.105.0 release notes: https://github.com/pydantic/pydantic-ai/releases/tag/v1.105.0 — June 2 2026, on-demand capabilities + Grok 4.3
- v2.0.0b1-b5 release notes: https://github.com/pydantic/pydantic-ai/releases (v2 betas track)
- Migration write-up: https://medium.com/@kacperwlodarczyk/pydantic-ai-capabilities-hooks-agent-specs-migration-guide-with-real-code-d0d986eb2b91 — Hooks/Capabilities landed v1.71, March 2026
