# Model-Agnostic Agent Libraries — 2026 Survey

> Scope: agent-loop layer for a Python (3.12+) Custom MCP Server for the SANS Find Evil! hackathon (DFIR). Must be MCP-native, multi-provider (Anthropic / OpenAI / Gemini / Ollama / vLLM), support subagent specialization, streaming tool calls, pre/post-tool hooks for audit logging, production-shape, and friendly to a ≤400 LOC-per-file discipline.

GitHub stats and last-push dates pulled live from the GitHub REST API on 2026-06-02. Doc-level claims cross-checked via Context7 (pydantic-ai, mcp-agent) and the libraries' own READMEs.

---

## TL;DR

1. **Pydantic AI** — the cleanest fit. MCP-native (`MCPServerStdio`/`MCPServerHTTP` toolsets + `MCPServerTool` native bridge), all four providers as first-class model strings, formal `Hooks` + `AbstractCapability` middleware (pre/post tool, model-request wrappers, event-stream auditors), agent-as-tool delegation with usage propagation, MIT, 17.5k stars, daily commits. Type-safe, small surface, fits the 400-LOC rule.
2. **OpenAI Agents SDK (`openai-agents-python`)** — solid runner-up if you accept the OpenAI accent. Native MCP tools, multi-provider via the bundled LiteLLM extra (Anthropic/Gemini/Ollama), built-in handoffs/agents-as-tools, lifecycle hooks (`RunHooks` / `AgentHooks`), MIT, 26.9k stars, current. Less Pydantic-flavored, slightly more boilerplate for non-OpenAI providers.
3. **`mcp-agent` (LastMile)** — most MCP-pure on paper (the only framework whose vision is "MCP is all you need"), `AugmentedLLM` swaps providers mid-conversation with history preserved, ships orchestrator/router/evaluator patterns, Apache-2.0. **Caveat: last commit was 2026-01-25 (4+ months stale at survey time)**. Use only if you accept the maintenance risk; otherwise mine its patterns and implement on top of Pydantic AI.

Skip for this project: LangGraph (too much state-graph ceremony for a hackathon), CrewAI (multi-agent role-play overshoots the need), AG2/AutoGen (heavy), LlamaIndex agents (RAG-shaped, not DFIR-shaped), Haystack (pipeline shape), Open Interpreter (AGPL — license tax), bare Anthropic SDK (no MCP client primitives, you'd rebuild Pydantic AI poorly), Marvin (no MCP), Mirascope (no MCP, low velocity), Instructor (structured outputs only — not a loop), smolagents (CodeAgent paradigm + AGPL-adjacent Apache, no formal hooks).

---

## Detailed library cards

### 1. LiteLLM (BerriAI/litellm)

- **What it is.** Provider-translation layer + proxy/gateway. Single Python entrypoint (`litellm.completion`) that proxies to 100+ providers in OpenAI-shape; plus a standalone "AI Gateway" with an "MCP Gateway" feature that maps MCP tools into chat-completion `tools=`.
- **License + maturity.** "NOASSERTION" SPDX (LiteLLM is MIT-licensed in the LICENSE file, but the repo also contains commercial enterprise code under a separate license — read the LICENSE before vendoring). 49.1k stars. Pushed 2026-06-02. **3,537 open issues** — extremely high signal of churn/bugs.
- **MCP support.** Yes via the proxy/gateway "MCP Gateway" feature; SDK side exposes MCP tool loading. Useful but the MCP integration sits at the gateway layer, not as a first-class agent abstraction.
- **Provider switching.** Best-in-class — change a model string. Anthropic/OpenAI/Gemini/Ollama/vLLM all supported.
- **Subagent primitives.** None — LiteLLM is a transport, not an agent framework.
- **Tool-call / streaming.** OpenAI-shape `tools=` and streaming. Quality varies by provider adapter; edge cases (Anthropic tool_use blocks, Gemini function-call parts) historically lag upstream.
- **Hooks.** Callbacks for pre/post API call exist at the SDK level, plus the proxy has audit logging. Not a tool-level pre/post hook surface like Pydantic AI's.
- **Structured output.** Pydantic via `response_format` translated per-provider; reliability varies.
- **File-size friendliness.** Tiny client footprint. The proxy is a separate process.
- **Verdict.** Use LiteLLM **underneath** another agent framework (Pydantic AI's `OpenAIModel` pointed at LiteLLM proxy, or `openai-agents` via `litellm` extra) to get cheap provider switching for less-common providers. Don't make it your loop.

### 2. Pydantic AI (pydantic/pydantic-ai)

- **What it is.** "FastAPI for GenAI" — small, type-safe agent framework. `Agent(model, toolsets=[...], capabilities=[...])` is the core. Tools are decorated functions with auto-generated JSON schemas from Pydantic.
- **License + maturity.** MIT. 17.5k stars. Pushed 2026-06-02 (daily). 584 open issues (healthy ratio). Backed by the Pydantic team — they ship.
- **MCP support.** Native, two ways:
  - `MCPServerStdio` / `MCPServerHTTP` as a `toolset` (full programmatic MCP client; tools become agent tools transparently; sampling supported via `agent.set_mcp_sampling_model()`).
  - `MCPServerTool` wrapped in `NativeTool(...)` — hands the MCP server URL directly to providers that natively speak MCP (Anthropic, OpenAI Responses).
- **Provider switching.** Model strings: `'anthropic:claude-sonnet-4-6'`, `'openai:gpt-5.2'`, `'google:gemini-3-flash-preview'`, `'ollama:...'`, plus a generic `OpenAIModel(base_url=...)` for vLLM/LM Studio/LiteLLM proxy.
- **Subagent primitives.** "Agent delegation" pattern — one agent calls another agent inside a `@agent.tool`, dependencies + usage propagate automatically. Plus `composable Capabilities` that bundle tools/hooks/instructions/model settings into reusable specialist units.
- **Tool-call / streaming.** `@agent.tool` / `@agent.tool_plain`. Full streaming including streamed structured-output validation. Event stream surfaces `ToolCallEvent` / `ToolResultEvent` / `PartStartEvent`.
- **Hooks.** First-class. The `Hooks()` capability exposes `@hooks.on.before_tool_execute(tools=[...])` and post-execute equivalents. Beyond that, the `AbstractCapability` API gives `wrap_model_request`, `wrap_tool_execute`, `wrap_run_event_stream`, `get_wrapper_toolset` — exactly the surface you want for tamper-evident DFIR audit logging.
- **Structured output.** Pydantic-native, validated per provider, streaming-aware.
- **File-size friendliness.** Excellent. An agent + 5 tools + a hook fits in ~150 LOC. No graph DSL.
- **Verdict.** **Top pick.** Has every property the constraint list demands, MIT, fast-moving, and the audit-hook surface is unusually well thought-out for DFIR forensics work.

### 3. Mirascope (Mirascope/mirascope)

- **What it is.** "LLM anti-framework" — decorator-based unified interface (`@llm.call("anthropic/claude-sonnet-4-5")`, `@llm.tool`).
- **License + maturity.** MIT. **1.5k stars** — small community. Pushed 2026-05-29. 16 open issues (healthy but tiny).
- **MCP support.** Not mentioned in current docs. No MCP toolset primitive.
- **Provider switching.** Good — string-based, all major providers.
- **Subagent primitives.** None formal.
- **Tool-call / streaming.** Decorator-based tools, streaming and async.
- **Hooks.** Not documented as a first-class surface.
- **Structured output.** Strong (Pydantic).
- **File-size friendliness.** Excellent.
- **Verdict.** Niche, low velocity, no MCP. **Skip.**

### 4. Marvin (PrefectHQ/marvin)

- **What it is.** Pythonic "Tasks / Agents / Threads" framework from the Prefect team. Sits on top of Pydantic AI models.
- **License + maturity.** Apache-2.0. 6.2k stars. Pushed 2026-05-12. 105 open issues.
- **MCP support.** Not native. Could be bolted on via Pydantic AI underneath, but Marvin doesn't expose MCP primitives.
- **Provider switching.** Inherits Pydantic AI providers.
- **Subagent.** Tasks + Agents + Threads abstractions; portable agent configs.
- **Tool-call / streaming.** Yes, inherited.
- **Hooks.** Less formal than Pydantic AI.
- **Structured output.** Pydantic.
- **File-size friendliness.** Good.
- **Verdict.** Pydantic AI with extra abstractions you don't need. Use Pydantic AI directly. **Skip.**

### 5. Instructor (instructor-ai/instructor)

- **What it is.** Structured-output extraction across providers — not an agent loop.
- **License + maturity.** MIT, 13.1k stars, current (v1.15.1, April 2026).
- **MCP support.** None.
- **Provider switching.** Excellent (`instructor.from_provider("anthropic/...")`).
- **Subagent.** N/A.
- **Tool-call.** Tool-calling treated as a structured-output mechanism, not a loop.
- **Hooks.** Retry hooks only.
- **Structured output.** Best in class for cross-provider Pydantic extraction with streaming `Partial`.
- **Verdict.** Wrong shape — it's a structured-output library, not an agent. **Use as a complement** inside Pydantic AI tools if you need bullet-proof per-provider Pydantic extraction; not as the loop.

### 6. LangChain + LangGraph (langchain-ai/langgraph)

- **What it is.** Low-level stateful-agent graph orchestrator. State, checkpoints, durable execution, HITL, memory.
- **License + maturity.** MIT, 33.7k stars, pushed 2026-06-02, 567 open issues. "Deep Agents" sub-package adds planning + subagents.
- **MCP support.** Via `langchain-mcp-adapters` (community adapter), not a first-class primitive on the graph. Workable but extra layer.
- **Provider switching.** Via LangChain's `ChatModel` provider zoo — yes.
- **Subagent.** Yes (Deep Agents; subgraphs).
- **Tool-call / streaming.** Yes; streaming is first-class.
- **Hooks.** Via LangSmith / OpenTelemetry callbacks. Decent but indirect.
- **Structured output.** OK; not as ergonomic as Pydantic AI.
- **File-size friendliness.** Poor. Graph DSL + LangChain imports balloon files.
- **Verdict.** Overkill for a hackathon DFIR MCP server. The graph runtime is gold for long-running production workflows but you don't need durable execution here. **Skip for this build.**

### 7. CrewAI (crewAIInc/crewAI)

- **What it is.** Role-playing multi-agent crews and event-driven Flows.
- **License + maturity.** MIT, **52.7k stars**, pushed 2026-06-02. Very active.
- **MCP support.** Yes — `crewai-tools[mcp]` integrates MCP servers as tools.
- **Provider switching.** Yes (LiteLLM under the hood).
- **Subagent.** Crews are the whole point — agents with roles/goals/backstories.
- **Tool-call.** Yes.
- **Hooks.** Decorator-driven (`@agent`, `@task`, `@crew`, `@listen`, `@router`) but not the same as fine-grained pre/post-tool audit hooks.
- **Structured output.** OK.
- **File-size friendliness.** Medium — role/goal/backstory prose tends to bloat configs.
- **Verdict.** Excellent for "team of personas" tasks; the role-play prose is a poor fit for forensic-tool dispatch where you want deterministic specialist routing. **Skip.**

### 8. AG2 / AutoGen (ag2ai/ag2)

- **What it is.** Microsoft AutoGen's community fork. ConversableAgent, swarms, group chats, nested chats, AutoPattern.
- **License + maturity.** Apache-2.0 (with original Microsoft MIT pieces). 4.6k stars. Pushed 2026-06-02 (active). 137 open issues.
- **MCP support.** Yes (MCP Registry integration).
- **Provider switching.** `LLMConfig`, multi-provider.
- **Subagent.** Strongest in this list — full conversational agent patterns.
- **Tool-call / streaming.** Yes.
- **Hooks.** Limited pre/post-tool surface; observability via OpenTelemetry.
- **Structured output.** OK.
- **File-size friendliness.** Heavier than Pydantic AI.
- **Verdict.** Strong if you want chatty multi-agent conversation; overshoots a focused DFIR MCP loop. **Skip.**

### 9. LlamaIndex agents (run-llama/llama_index)

- **What it is.** Document-agent + RAG framework with an agent module.
- **License + maturity.** MIT, 49.9k stars, current.
- **MCP support.** Not native; community integrations.
- **Provider switching.** Yes.
- **Subagent.** Workflows.
- **Verdict.** Wrong shape (document-centric). **Skip.**

### 10. Haystack agents (deepset-ai/haystack)

- **What it is.** Pipeline + agent framework, model/vendor agnostic.
- **License + maturity.** Apache-2.0, 25.4k stars, current.
- **MCP support.** Yes via Hayhooks (wraps pipelines/agents as MCP servers — i.e., the inverse of what we need: it makes Haystack a server, not an MCP client agent).
- **Provider switching.** Yes.
- **Verdict.** Pipeline mental model is wrong shape for hackathon agent-loop. **Skip.**

### 11. Open Interpreter (OpenInterpreter/open-interpreter)

- **What it is.** Code-execution agent — give the LLM `exec()`.
- **License + maturity.** **AGPL-3.0** — license-incompatible with most MIT/Apache projects (copyleft contamination risk). 63.8k stars.
- **Verdict.** **Skip on license alone.**

### 12. smolagents (huggingface/smolagents)

- **What it is.** Tiny code-execution agent framework (`CodeAgent` writes Python instead of JSON tool calls; `ToolCallingAgent` traditional).
- **License + maturity.** Apache-2.0, 27.7k stars, pushed 2026-06-02 (active).
- **MCP support.** Yes — "tools from any MCP server".
- **Provider switching.** Excellent (via LiteLLM, HF inference, OpenAI-compat, Bedrock, transformers).
- **Subagent.** "Multi-agent hierarchies" mentioned, limited primitives.
- **Tool-call / streaming.** Yes; `stream_outputs=True`.
- **Hooks.** Not first-class.
- **File-size friendliness.** Excellent — core is ~1k LOC total.
- **Verdict.** Charming and small. The CodeAgent paradigm (LLM writes Python) is a **risk vector for DFIR** — you'd be executing model-authored Python over forensic artifacts. ToolCallingAgent works but offers less surface than Pydantic AI. **Skip for this build.**

### 13. Anthropic Python SDK + custom loop (anthropics/anthropic-sdk-python)

- **What it is.** Provider SDK. Build your own loop.
- **License + maturity.** MIT, 3.6k stars, pushed 2026-06-01.
- **MCP support.** SDK exposes MCP-server tool blocks (Claude has native MCP server support in API messages), but you write the client glue.
- **Provider switching.** None — Anthropic-locked.
- **Verdict.** Violates the multi-provider constraint. You'd end up reimplementing Pydantic AI poorly. **Skip.**

### 14. OpenAI Agents SDK (openai/openai-agents-python)

- **What it is.** OpenAI's official "lightweight, powerful framework for multi-agent workflows." Agents, Tools, Handoffs, Sessions, Guardrails, Tracing.
- **License + maturity.** MIT, 26.9k stars, pushed 2026-05-31.
- **MCP support.** Yes — native MCP tool type.
- **Provider switching.** Native OpenAI; **other providers via `openai-agents[litellm]` or `any-llm` extras** — works for Anthropic, Gemini, Ollama but is not OpenAI's primary path. Responses-API-only features (hosted tools, realtime voice) won't work cross-provider.
- **Subagent.** First-class **Handoffs** + agents-as-tools.
- **Tool-call / streaming.** Yes (streaming is fully supported).
- **Hooks.** Yes — `RunHooks` (global) and `AgentHooks` (per-agent) with `on_start`/`on_end`/`on_handoff`/`on_tool_start`/`on_tool_end`/`on_llm_start`/`on_llm_end`. Tracing built-in.
- **Structured output.** Pydantic via `output_type=`.
- **File-size friendliness.** Good.
- **Verdict.** **Strong runner-up.** Use this if you want the handoff pattern out of the box and don't mind the OpenAI-flavored API. Slightly heavier non-OpenAI provider story than Pydantic AI.

### 15. `mcp-agent` (lastmile-ai/mcp-agent)

- **What it is.** Apache-2.0 framework whose thesis is "MCP is all you need." `AugmentedLLM` wraps the loop; `attach_llm(OpenAIAugmentedLLM)` / `attach_llm(AnthropicAugmentedLLM)` swaps providers mid-conversation with history preserved. Workflow patterns: parallel/map-reduce, routing, intent-classification, orchestrator-workers, deep-research, evaluator-optimizer, swarms.
- **License + maturity.** Apache-2.0, 8.4k stars. **Last commit: 2026-01-25 (>4 months stale at survey).** Updated_at shows repo activity (issues/PRs) but no merged commits since January. This is a yellow flag for a project relying on it during a hackathon weekend where you can't fix upstream bugs.
- **MCP support.** Best in class — built around it. Full tool/resource/prompt/notification surface, OAuth, sampling, elicitation, roots.
- **Provider switching.** OpenAI, Anthropic (direct + Bedrock + Vertex), Azure, Bedrock, Google AI/Vertex, Ollama. Switch via `attach_llm()`.
- **Subagent.** Built-in orchestrator-worker, router, evaluator-optimizer, swarm patterns.
- **Tool-call / streaming.** `generate_str`, `generate_structured`, `generate_str_stream`.
- **Hooks.** Structured logging + OpenTelemetry tracing + TokenCounter with threshold watchers. Less granular pre/post-tool hook decorator surface than Pydantic AI, but the observability primitives are real.
- **Structured output.** `generate_structured(response_model=PydanticClass)`.
- **File-size friendliness.** Reasonable.
- **Verdict.** Conceptually the best fit — but **the velocity is the problem**. Strategy: **mine the patterns (orchestrator-worker, router, evaluator) and re-implement on Pydantic AI** which gives you the same shape with active maintenance + tighter audit-hook surface.

---

## Comparison matrix

| Library | MCP support | Multi-provider | Subagent | Hooks (pre/post tool) | Streaming tools | Stars | Last push | License | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Pydantic AI** | Native (`MCPServer*` + `MCPServerTool`) | First-class (string) | Agent delegation + Capabilities | First-class (`Hooks`, `AbstractCapability`) | Yes | 17.5k | 2026-06-02 | MIT | **PICK** |
| **OpenAI Agents SDK** | Native | Via `[litellm]` / `[any-llm]` extras | Handoffs + agents-as-tools | `RunHooks` / `AgentHooks` | Yes | 26.9k | 2026-05-31 | MIT | Strong runner-up |
| **mcp-agent (LastMile)** | Best (purpose-built) | Yes (`attach_llm`) | Built-in patterns | Logging + OTel + TokenCounter | Yes | 8.4k | **2026-01-25 (stale)** | Apache-2.0 | Mine patterns, don't depend |
| LiteLLM | Via gateway | Best (100+) | None | Callbacks | Provider-dependent | 49.1k | 2026-06-02 | NOASSERTION (MIT + commercial) | Use under the hood |
| LangGraph | Adapter | Yes | Subgraphs / Deep Agents | LangSmith callbacks | Yes | 33.7k | 2026-06-02 | MIT | Too heavy for hackathon |
| CrewAI | `crewai-tools[mcp]` | Yes (LiteLLM) | Crews + Flows | Decorators (coarse) | Yes | 52.7k | 2026-06-02 | MIT | Role-play overshoots |
| AG2 / AutoGen | Yes | Yes | ConversableAgent / Swarm | OTel | Yes | 4.6k | 2026-06-02 | Apache-2.0 | Heavy |
| LlamaIndex | Community | Yes | Workflows | Module hooks | Partial | 49.9k | 2026-05-29 | MIT | Wrong shape (RAG) |
| Haystack | Hayhooks (server-side) | Yes | Pipelines | Pipeline | Yes | 25.4k | 2026-06-02 | Apache-2.0 | Wrong shape |
| smolagents | Yes | Excellent | Limited | No | Yes | 27.7k | 2026-06-02 | Apache-2.0 | CodeAgent risk for DFIR |
| Marvin | No | Inherits Pydantic AI | Tasks/Agents/Threads | Limited | Yes | 6.2k | 2026-05-12 | Apache-2.0 | Use Pydantic AI directly |
| Mirascope | No | Yes | None | No | Yes | 1.5k | 2026-05-29 | MIT | Low velocity, no MCP |
| Instructor | No | Yes | N/A | Retry only | Partial streaming | 13.1k | 2026-04-03 | MIT | Wrong shape (structured-output lib) |
| Open Interpreter | No | LiteLLM | N/A | N/A | Yes | 63.8k | 2026-05-17 | **AGPL-3.0** | License blocker |
| Anthropic SDK | MCP block native | None (locked) | N/A | None | Yes | 3.6k | 2026-06-01 | MIT | Multi-provider blocker |

---

## Concrete recommendation patterns

For a Custom MCP Server + model-agnostic agent loop in 2026, three patterns dominate:

### Pattern A — Pydantic AI as the loop, MCP server as the toolset (recommended)
- Build the Find Evil DFIR MCP server with the official Python `mcp` SDK (`FastMCP` style).
- The agent loop is Pydantic AI:
  - `Agent('anthropic:claude-sonnet-4-6', toolsets=[MCPServerStdio('python', ['-m', 'find_evil_mcp'])])`
  - Swap providers via the model string. Optionally route exotic ones (vLLM, local) through a `LiteLLM` proxy exposed as `OpenAIModel(base_url=...)`.
- Specialization: each specialist subagent is its own `Agent(model=..., toolsets=[subset])` invoked from a `@router_agent.tool` — usage and dependencies propagate automatically.
- Audit log: a single `AbstractCapability` with `wrap_tool_execute` writes per-tool entries to an append-only audit file before and after each MCP tool invocation. Add `wrap_run_event_stream` to record streamed reasoning. This is exactly the surface a DFIR judge wants to see.
- Files: each subagent in its own module (~150–250 LOC); shared audit capability lives in `agents/_audit.py`; MCP server tools in `mcp/tools/*.py`. Fits the 400-LOC rule cleanly.

### Pattern B — OpenAI Agents SDK with `litellm` extra
- Same MCP server, but use OpenAI Agents SDK with the LiteLLM extra for non-OpenAI providers.
- Handoffs and agents-as-tools are batteries-included.
- Audit logging via `RunHooks` (`on_tool_start` / `on_tool_end`).
- Pick this if you prefer OpenAI's handoff vocabulary over Pydantic AI's delegation pattern, or if any teammate is already fluent in this SDK.

### Pattern C — Bare provider SDKs unified by LiteLLM, hand-rolled tiny loop
- ~200-line tool-loop in `loop.py` calling `litellm.completion(tools=...)`. Streaming hooks via LiteLLM callbacks.
- MCP client written against the `mcp` SDK directly; convert MCP tool list → OpenAI-shape `tools=[...]`.
- Highest control, lowest framework dependency, hardest to debug under hackathon time pressure. Recommend only if you've shipped this exact pattern before.

---

## What 2026-canonical Python MCP-server projects use

Signals from current MCP/DFIR projects and 2026 framework round-ups:

- **DFIR-domain MCP servers** (Velociraptor MCP, DFIR-IRIS MCP, MCP-Forensic-Toolkit, winforensics-mcp): all use **FastMCP** for the server side. Client-side agent loop varies; the most common pairings on the agent side in 2026 round-ups are **Pydantic AI**, **OpenAI Agents SDK**, **Claude Agent SDK**, and **mcp-agent**, with **LangGraph** in the production-graph camp.
- **Trend.** Frameworks **built for MCP from day one** (Pydantic AI, OpenAI Agents SDK, Google ADK, Claude Agent SDK, mcp-agent) are the cleanest choice; pre-MCP frameworks (LangChain, LlamaIndex, Haystack) bolt MCP on via adapters.
- **Hackathon judging context.** SANS Find Evil! judges DFIR rigor — the **audit-trail story matters**. The `Hooks` + `AbstractCapability` surface in Pydantic AI lets you demo tamper-evident per-tool logs in 30 lines; this is a differentiator.

---

## Honest notes

- **LiteLLM has 3,537 open issues.** It works, it ships, but its sprawl is real. Use it as a translator layer, not as the heart of your loop.
- **mcp-agent has been quiet since January 2026.** The patterns it codifies are excellent — orchestrator-workers, evaluator-optimizer, router — but you shouldn't bet a weekend on a framework whose maintainer hasn't merged in months.
- **Pydantic AI moves fast and sometimes breaks APIs between minor versions.** Pin `pydantic-ai==1.105.*` in your `pyproject.toml`.
- **OpenAI Agents SDK's "100+ providers via Chat Completions" claim is real but uneven** — Responses-API features (hosted tools, realtime voice) silently degrade when you point it at Anthropic/Gemini. If you stay on Chat Completions tool-use shape across all four providers, you're fine.
- **Pydantic AI vs mcp-agent for "specialist subagents".** Pydantic AI's agent-delegation pattern is more verbose than mcp-agent's named workflows (`Router`, `Orchestrator`, `EvaluatorOptimizer`), but you can copy those names as thin wrapper functions in ~50 LOC and get both worlds. That is my recommended path.

---

## Final recommendation

**Use Pydantic AI 1.105+ as the agent loop, FastMCP for the Find Evil DFIR MCP server, and an `AbstractCapability`-based audit hook for tamper-evident per-tool logging.** Provider switching via model strings (Anthropic / OpenAI / Gemini), local models via `OpenAIModel(base_url=...)` pointed at Ollama or vLLM, optionally proxied through LiteLLM only if a specific exotic provider is needed.

Sources (key references gathered during this survey):
- GitHub REST API stats pulled 2026-06-02 for all 15 repos
- Context7 docs: `/pydantic/pydantic-ai`, `/lastmile-ai/mcp-agent`
- "AI Agent Frameworks in 2026" (morphllm), "How to build AI agents with MCP: 12 framework comparison" (ClickHouse), "Best Python AI Agent Frameworks 2026" (Uvik, Fastio)
- DFIR MCP ecosystem: Velociraptor MCP (SOCFortress), DFIR-IRIS MCP (LobeHub), MCP-Forensic-Toolkit (axdithyaxo), winforensics-mcp, Cyber Triage "Intro to MCP Servers for DFIR"
- Pydantic AI hooks/capabilities docs: `docs/hooks.md`, `docs/capabilities.md`, `docs/mcp/client.md`, `docs/native-tools.md`, `docs/multi-agent-applications.md`
- mcp-agent docs: `docs/concepts/augmented-llms.mdx`, `docs/mcp-agent-sdk/core-components/augmented-llm.mdx`
