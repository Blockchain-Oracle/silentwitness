# MCP / FastMCP — Deep Verification

**Auditor:** deep-audit research agent
**Date:** 2026-06-03
**Subject specs:** `docs/architecture.md` §4–§8, `docs/BRAINSTORM.md` §3.5, all stories in `docs/stories/story-*.md` that touch `@mcp.tool()`, `docs/CICD_SPEC.md`, `context/technical/07-mcp-and-agent-platforms.md` Part A/B.
**Sources used:**
1. Pinned source-read of `modelcontextprotocol/python-sdk` at tag **v1.27.2** (commit `6213787`, dated 2026-05-29 — the current stable release on PyPI as of audit date) at `/tmp/mcp-python-v1/`.
2. Source-read of `python-sdk` `main` branch (commit `ed39e73`, dated 2026-06-02 — pre-alpha v2) at `/tmp/mcp-python-audit/`.
3. Live runtime smoke tests inside an ephemeral `uv run --with 'mcp==1.27.2'` venv (host-binding default, transport security, generic Pydantic output schema).
4. Live spec read: `modelcontextprotocol.io/specification/2025-11-25/basic/transports`, `.../lifecycle`, `.../security_best_practices`, `.../utilities/tasks`.
5. CVE corpus: GHSA-3qhf-m339-9g5v (CVE-2025-53366), GHSA-9h52-p55h-vw2f (CVE-2025-66416), CVE-2026-33032 / MCPwn (nginx-ui), CVE-2026-27124 (jlowin/FastMCP — DIFFERENT project, see §Pin recommendation), the April 2026 OX Security "MCP design flaw" disclosure.
6. PyPI release metadata for `mcp` (latest: 1.27.2).

---

## Per-claim verdict (1–6)

### Claim 1 — FastMCP decorator API for typed tools — **VALIDATED**

**Spec claims (verbatim quotes):**
- `architecture.md:289` — "Each tool has typed Pydantic input + output"
- `story-fastmcp-server-bootstrap.md:120` — "The FastMCP construction pattern: `mcp = FastMCP("silentwitness", version=__version__)`. Tool registration happens via `@mcp.tool()` decorators"
- `story-record-observation-tool.md:119` — `@mcp.tool(name="record_observation", description="...")`
- `architecture.md:323` — `ToolResponse[TPayload]` generic Pydantic model used as tool return type

**Evidence:**
- `/tmp/mcp-python-v1/src/mcp/server/fastmcp/server.py:446-506` — `def tool()` decorator. Signature: `(name, title, description, annotations, icons, meta, structured_output)`. Calls `add_tool` → `Tool.from_function` (`base.py:46-91`) which calls `func_metadata` (`utilities/func_metadata.py:182-329`).
- `func_metadata` auto-derives **inputSchema** from the function signature and a Pydantic input model (`arg_model`), and auto-derives **outputSchema** from the return type annotation if it is a BaseModel subclass / TypedDict / dataclass / primitive / dict / generic alias (`func_metadata.py:332-433`).
- `server.py:315-330` shows the registered `Tool` is published in `list_tools` with both `inputSchema=info.parameters` and `outputSchema=info.output_schema`. Confirms the architecture's "typed Pydantic input + output" claim.

**Runtime confirmation (smoke test executed in ephemeral venv on 2026-06-03):**
```
@mcp.tool(name="record_observation")
async def record_observation(text: str, ctx: Context) -> ToolResponse[ObservationResult]: ...

# Output:
name: record_observation
has inputSchema: True
has outputSchema: True
outputSchema keys: ['$defs', 'properties', 'required', 'title', 'type']
input props: ['text']
```
Pydantic generic `ToolResponse[ObservationResult]` is resolved to a real BaseModel subclass (`type(EnvWithPayload).__name__ == 'ModelMetaclass'`, `isinstance(EnvWithPayload, type) == True`, `issubclass(EnvWithPayload, BaseModel) == True`). FastMCP's `_try_create_model_and_schema` Case 1 (`func_metadata.py:382-384`) handles this cleanly. `ctx` is auto-injected via `find_context_parameter` (`base.py:69-70`).

**Caveat:** structured output is enabled by `structured_output=None` default which auto-detects from the return annotation. If a story omits the return annotation, no outputSchema is generated. Stories MUST annotate return types or set `structured_output=True` (which raises if no annotation).

### Claim 2 — Both stdio AND Streamable HTTP transports — **VALIDATED with caveats**

**Spec claims:**
- `architecture.md:285` — "Transports are stdio (default for Claude Code) and Streamable HTTP on `localhost:4508`"
- `architecture.md:792` — "Streamable HTTP on `localhost:4508`. Binds 127.0.0.1 only (DNS-rebinding defense)"
- `story-fastmcp-server-bootstrap.md:46` — "the bind address is 127.0.0.1 (NOT 0.0.0.0) — DNS-rebinding defense"

**Evidence:**
- `server.py:279-300` — `def run(transport: Literal["stdio", "sse", "streamable-http"])`. Three transports. stdio and streamable-http are the two we use.
- `server.py:777-790` — `run_streamable_http_async` builds a Starlette app via `self.streamable_http_app()` and binds it with `uvicorn.Config(host=self.settings.host, port=self.settings.port)`.
- `server.py:147-176` — Constructor accepts `host: str = "127.0.0.1"` (NOTE the SDK default is already 127.0.0.1) and `port: int = 8000`.
- `server.py:177-183` — When `host in ("127.0.0.1", "localhost", "::1")`, FastMCP **auto-enables DNS-rebinding protection** with `allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*"]` and `allowed_origins=["http://127.0.0.1:*", ...]`.
- Runtime confirmation: instantiating `FastMCP("audit", host="127.0.0.1", port=4508)` produces `transport_security.enable_dns_rebinding_protection=True` automatically; instantiating with `host="0.0.0.0"` produces `transport_security=None`. This is the **fix for CVE-2025-66416**, landed in mcp 1.23.0 (April 2026). Pre-1.23.0 servers were silently vulnerable.
- `transport_security.py:11-127` — `TransportSecurityMiddleware` validates `Host` header (returns 421) and `Origin` header (returns 403) when enabled.

**Maturity caveats (open issues filed against streamable HTTP, all unresolved as of audit date):**
- Issue #1367 — Mounting `streamable_http_app()` inside an existing FastAPI app does not work cleanly (we are not affected — we run uvicorn directly).
- Issue #1269 — HTTP HEAD requests can kill a streamable HTTP FastMCP server. Mitigation: don't expose to anything that probes with HEAD; loopback-only deploy already mitigates.
- Issue #1053 — Streamable HTTP fails when deployed behind Cloud Run (we are not affected; we deploy on the SIFT VM, loopback-only).
- Issue #2208 — `get_access_token()` returns stale token in stateful streamable-HTTP sessions. Affects OAuth; not our path (we use a static bearer — see Claim 3).

**Caveat about the spec story:**
- `story-fastmcp-server-bootstrap.md:122` claims the spec uses "Bearer token auth from `$SILENTWITNESS_GATEWAY_TOKEN` env var." The MCP Python SDK's `AuthSettings` (`auth/settings.py:15-30`) is built around **OAuth-style metadata** (`issuer_url`, `resource_server_url`, scopes). You **CAN** wire a static-token verifier by implementing the `TokenVerifier` Protocol (`auth/provider.py:96-100`) — its only required method is `async def verify_token(self, token: str) -> AccessToken | None`. But the story's mental model that you just pass `token=$SILENTWITNESS_GATEWAY_TOKEN` is wrong — you need ~20 lines of `class GatewayTokenVerifier` boilerplate.

### Claim 3 — MCPwn / CVE-2026-33032 mitigation surface — **VALIDATED but the spec OVER-CLAIMS the threat-model coverage**

**Spec claims:**
- `architecture.md:950-951` — Lists "MCPwn-class (CVE-2026-33032)" in the threat model and claims defense via "no shell-execute, no arbitrary file write, no network egress tools" + 127.0.0.1-only HTTP binding + bearer auth.
- `context/technical/07-mcp-and-agent-platforms.md:1158-1187` — Survey description of the CVE is **factually accurate** (Pluto Security disclosure, nginx-ui /mcp + /mcp_message middleware split, CVSS 9.8, ~2,689 exposed instances).

**Evidence from primary sources (Pluto blog, official MCP spec):**

The current MCP spec `2025-11-25/basic/transports#streamable-http` explicitly says:
> 1. Servers **MUST** validate the `Origin` header on all incoming connections to prevent DNS rebinding attacks
> 2. When running locally, servers **SHOULD** bind only to localhost (127.0.0.1) rather than all network interfaces (0.0.0.0)
> 3. Servers **SHOULD** implement proper authentication for all connections

FastMCP v1.23+ implements (1) and (2) automatically when `host="127.0.0.1"` (confirmed above). (3) is on us to wire.

**MCPwn-specific framing — clarification:**

CVE-2026-33032 is NOT a flaw in MCP-the-protocol or in the Python SDK. It is a deployment-class bug specific to `nginx-ui`: they wired two HTTP endpoints to the same handler and forgot the auth middleware on `/mcp_message`. The generalizable lesson is "audit ALL routes that touch your MCP tools, not just `/mcp`."

Our deployment is structurally immune to the exact MCPwn shape because:
- FastMCP only exposes one route (`/mcp`, configurable via `streamable_http_path`). There is no `/mcp_message` companion route in the streamable_http stack.
- Auth (if configured) wraps that one route uniformly via `RequireAuthMiddleware` (`server.py:1011-1016`).

**However**, two newer items the architecture's threat model §9 does NOT cover (BLOCKER-level, see Recommended adjustments below):

- **CVE-2025-66416** — "DNS rebinding protection disabled by default" in mcp Python SDK ≤ 1.22.x. The pin in `architecture.md:26` (`mcp >= 1.0`) and `BRAINSTORM.md:117` (`>=1.0`) would **silently accept** a 1.0–1.22 install that ships without protection. The fix was 1.23.0+ (April 2026). Our minimum pin MUST be `mcp>=1.23.0`.
- **CVE-2025-53366** — DoS via unhandled exception on malformed requests. Fixed in mcp 1.9.4. Our pin would silently accept vulnerable 1.0–1.9.3.
- **OX Security April 2026 "MCP design flaw"** — affects MCP CLIENTS (hosts) that auto-execute server commands from untrusted MCP configs. Does NOT affect us as a server author. Out of scope; spec doesn't claim otherwise.

### Claim 4 — Context object API (`ctx.info`, `ctx.report_progress`) — **VALIDATED**

**Spec claims:**
- Multiple stories call `await ctx.info(...)`, `await ctx.report_progress(...)`, etc.

**Evidence (`/tmp/mcp-python-v1/src/mcp/server/fastmcp/server.py:1098-1354`):**
- `class Context(BaseModel, Generic[ServerSessionT, LifespanContextT, RequestT])` — the actual class.
- `async def report_progress(self, progress: float, total: float | None = None, message: str | None = None)` (line 1162). Matches spec usage.
- `async def info(self, message: str, **extra)` → `await self.log("info", message, **extra)` (line 1344). Same for `debug`, `warning`, `error`.
- `async def log(self, level, message, *, logger_name=None)` (line 1263). Sends via `send_log_message`.
- `async def read_resource(self, uri)` (line 1182) — for cross-tool resource access.
- `async def elicit(...)` (line 1194) — newer; takes a Pydantic schema, returns `ElicitationResult`. Used by story-elicitation flows if any (none currently in scope).
- `self.request_context.lifespan_context` — the value yielded by the `@asynccontextmanager` lifespan, accessible from any tool (matches `story-fastmcp-server-bootstrap.md:125-127` lifecycle pattern).
- Context is auto-injected by `find_context_parameter` (`utilities/context_injection.py`) whenever a parameter is type-annotated as `Context`.

All spec usages of `ctx` are valid.

### Claim 5 — Resources vs Tools primitive split — **VALIDATED**

**Spec claims:**
- `BRAINSTORM.md` and `architecture.md` mention "Valhuntir pattern" of exposing discipline texts via MCP Resources, though no story currently builds a resource in v1.

**Evidence (`server.py:534-647`):**
- `@mcp.resource(uri, *, name, title, description, mime_type, icons, annotations, meta)` decorator. Path templates supported (`@server.resource("resource://{city}/weather")`).
- Resource read returns str/bytes/JSON-serializable. ResourceTemplate registration is automatic when the URI has `{params}`.
- Underlying `ResourceManager` lives in `fastmcp/resources/`.

The architecture's plan to expose discipline texts as Resources is straightforward should we choose to add it. Not currently a story.

### Claim 6 — Maturity, version pin, breaking changes — **PARTIAL (the pin is wrong)**

**Spec claims:**
- `architecture.md:26` and `BRAINSTORM.md:117` — `mcp >= 1.0` (open lower bound)
- `architecture.md:285` — "MCP per the 2025-11-25 revision"

**Reality:**
- **Latest stable PyPI release: 1.27.2** (May 29, 2026). Tag `v1.27.2`. Repo last commit on `v1.x` branch: `6213787`.
- **v2 is in pre-alpha on `main`** (commit `ed39e73`, June 2, 2026). The `README.v2.md:19-22` explicitly states: "**v1.x remains the recommended version** for production use. v1.x will continue to receive bug fixes and security updates for at least 6 months after v2 ships." Target Q1 2026 for stable v2 — already slipped. v2 renames `FastMCP` → `MCPServer` (verified at `/tmp/mcp-python-audit/src/mcp/server/mcpserver/__init__.py:1-9`). API shape is otherwise nearly identical (same `@server.tool()` decorator, same Context, same Pydantic output-schema derivation — verified at `mcpserver/server.py:512-580`).
- **Breaking changes in v1.x family (since 1.0):**
  - 1.9.4 — CVE-2025-53366 patch (malformed request DoS).
  - 1.23.0 — CVE-2025-66416 patch (DNS rebinding protection auto-enable). **This is the critical floor.**
  - 1.24.x–1.27.x — incremental fixes, tasks-primitive scoping (PR #2720 in v1.27.2 — "Scope experimental tasks to the session that created them").

**The `mcp >= 1.0` pin admits versions vulnerable to two known CVEs.** This is the single most consequential finding in this audit.

---

## Sub-verifications

### JSON-RPC 2.0 protocol-level details — VALIDATED
All wire messages are JSON-RPC 2.0 per MCP spec `2025-11-25/basic/transports` and SDK `src/mcp/server/lowlevel/server.py`. No issue.

### Lifecycle (initialize handshake) — VALIDATED
The spec mandates: client sends `initialize` with `protocolVersion: "2025-11-25"` and capabilities → server responds with its own capabilities → client sends `notifications/initialized`. FastMCP wires this via `_setup_handlers` (`server.py:302-313`) + `MCPServer.create_initialization_options()` (called in `run_stdio_async`, `run_streamable_http_async`).

`story-fastmcp-server-bootstrap.md:45` says "protocolVersion matching the MCP 2025-11-25 revision" — correct.

The spec story also requires `capabilities.tools.listChanged=true` and `capabilities.logging=true`. FastMCP sets these via the lowlevel `MCPServer.get_capabilities(notification_options=NotificationOptions(...))`. Verified default capabilities include `tools` (from `_setup_handlers`'s `list_tools` registration) and the log notification surface is available via `Context.log`. **Story-level note:** to *advertise* `tools.listChanged=true` rather than just `tools={}`, the spec story needs to ensure `NotificationOptions(tools_changed=True)` is passed. FastMCP defaults to `NotificationOptions()` which has tools_changed=False by default — verify this in the bootstrap implementation. (FIX-IT, see Recommended adjustments.)

### Error semantics — PARTIAL / **the spec story is WRONG about -32000**

`story-fastmcp-server-bootstrap.md:130` states: "the FastMCP layer surfaces `success=False` cases as MCP error responses with `code=-32000` and the structured reason in `error.data`."

**Reality** (verified at `lowlevel/server.py:467-474, 580-584`): when a FastMCP tool function raises any exception, the lowlevel server **catches it and returns a successful JSON-RPC response containing a `CallToolResult` with `isError=True`** and the exception message inside `content=[TextContent(text=error_message)]`. It does NOT return a JSON-RPC error envelope with code -32000.

The `isError=true` pattern IS still the current canonical way (MCP spec `2025-11-25/server/tools` and our `tasks` spec page both reference `isError` as the failure indicator for tool calls). The only exception that propagates as a real JSON-RPC error (code -32042) is `UrlElicitationRequiredError` (`server.py:580-582`).

This means the SilentWitness audit-trail design (every rejection emits a `ToolResponse(success=False, ...)` envelope) is BETTER than relying on -32000: our envelope sits inside `CallToolResult.structuredContent` and carries full structured rejection context. But the spec story should be re-worded to remove the false -32000 claim.

### Long-running ops / `ctx.report_progress` — VALIDATED
`Context.report_progress` (line 1162-1180) sends `notifications/progress` via `request_context.session.send_progress_notification`. Requires the client to have included a `progressToken` in the request `_meta`; if absent, the call is a no-op. Matches spec.

### Tasks primitive — EXPERIMENTAL (spec mentions correctly)

The 2025-11-25 spec page for tasks (`modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks`) opens with:

> "Tasks were introduced in version 2025-11-25 of the MCP specification and are currently considered **experimental**. The design and behavior of tasks may evolve in future protocol versions."

The Python SDK at v1.27.2 implements tasks under `src/mcp/server/experimental/` (modules: `task_context.py`, `task_support.py`, `task_result_handler.py`, `task_scope.py`) — confirming the spec's experimental status. The latest commit on the v1.x branch (`6213787`, the audit's anchor commit) tightens task isolation per session (PR #2720: "Scope experimental tasks to the session that created them"), an active-bug-fix signal. Type definitions for `tasks/get`, `tasks/result`, `tasks/cancel`, `tasks/list`, `notifications/tasks/status` are present in `src/mcp/types.py:593-668`.

**Recommendation for SilentWitness:** do NOT adopt the tasks primitive in v1. Our tool calls are all short-lived (single CLI exec, bounded by per-tool elapsed budget per architecture.md §4.x). No story currently relies on tasks. Keep the option open for v2 (chainsaw_hunt and hayabusa_csv_timeline are the most likely candidates if needed later — both can exceed 10s on large evidence sets).

---

## Recommended spec adjustments

### BLOCKER — must fix before any tool story enters DOING

1. **[BLOCKER] Tighten the dependency pin** in `architecture.md:26` and `BRAINSTORM.md:117`. Change `mcp >= 1.0` → **`mcp>=1.23.0,<2.0`**. Rationale: (a) closes CVE-2025-53366 (DoS, fixed 1.9.4) and CVE-2025-66416 (DNS rebinding default, fixed 1.23.0); (b) keeps us on v1.x (v2 is pre-alpha, ETA slipped past Q1 2026 per `README.v2.md`); (c) `<2.0` upper bound forces a deliberate migration when v2 ships rather than a silent break (the `FastMCP → MCPServer` rename is a breaking import change). Also update `uv add` invocation at `architecture.md:1046`.

2. **[BLOCKER] Correct the false -32000 claim** in `story-fastmcp-server-bootstrap.md:130`. Replace with: "the FastMCP layer surfaces tool exceptions as `CallToolResult(isError=true)`; our convention is that EVERY tool returns a `ToolResponse[T]` envelope as `structuredContent` (with `success` either True or False), and we let FastMCP map raw exceptions to `isError=true` only for unexpected crashes — at which point the audit log still captures the attempt because the tool's `try` block must emit the audit JSONL line before re-raising."

3. **[BLOCKER] Add CVE-2025-53366 and CVE-2025-66416 to architecture.md §9 threat model.** Both are MCP-SDK-class issues we MUST cite by CVE so a re-auditor sees we considered them. Current §9 (architecture.md:950-951) cites CVE-2026-33032 / MCPwn but does NOT mention these two. Add a row:

   | Threat | Description | Mitigation | Residual |
   |---|---|---|---|
   | DNS rebinding via stale localhost binding (CVE-2025-66416) | `mcp` <1.23 disables DNS-rebinding defense even on 127.0.0.1 bind | Hard pin `mcp>=1.23.0`; assert `transport_security.enable_dns_rebinding_protection==True` at server startup | None |
   | Tool-input DoS (CVE-2025-53366) | Malformed JSON-RPC requests crash the FastMCP server via unhandled exception | Hard pin `mcp>=1.9.4`; covered by the `>=1.23.0` pin above | None |

### FIX-IT — should fix before merging the bootstrap story

4. **[FIX-IT] Make capability advertisement explicit** in story-fastmcp-server-bootstrap.md. The story asserts `capabilities.tools.listChanged=true` in BDD (`story-fastmcp-server-bootstrap.md:42`). FastMCP does not advertise `listChanged=true` by default. The lifecycle initialization uses `MCPServer.create_initialization_options()` which builds a `Capabilities` object from `NotificationOptions(tools_changed=False, ...)` by default. To make the BDD pass we need to either: (a) override the lowlevel init options when calling `await self._mcp_server.run(...)` (requires monkey-patching FastMCP, brittle), or (b) since we never actually mutate the tool list at runtime, relax the BDD to `tools` capability declared (any sub-shape) and drop the `listChanged=true` assertion. **Recommendation: option (b).** SilentWitness tools are registered once at startup and never change; `listChanged=true` would be a false promise.

5. **[FIX-IT] Replace the "bearer token" hand-wave with a `TokenVerifier` implementation note.** `story-fastmcp-server-bootstrap.md:122` says "Bearer token auth from `$SILENTWITNESS_GATEWAY_TOKEN` env var" as if it's a config flag. Reality: the SDK's `AuthSettings` is built around OAuth metadata. To use a static bearer token, the story MUST add the following file to its file-modification map:

   - `src/silentwitness_mcp/_auth.py` — NEW — implements `class GatewayTokenVerifier` satisfying the `TokenVerifier` Protocol (`async def verify_token(token: str) -> AccessToken | None`); compares against `$SILENTWITNESS_GATEWAY_TOKEN`; returns an `AccessToken(token=token, client_id="silentwitness-gateway", scopes=[])` on match, else None. (~30 LOC.)

   Plus the FastMCP construction needs `FastMCP(name="silentwitness", ..., token_verifier=GatewayTokenVerifier(), auth=AuthSettings(issuer_url="http://127.0.0.1:4508", resource_server_url="http://127.0.0.1:4508"))`. AuthSettings requires the two URL fields even for a static-bearer setup — they're cosmetic for us but Pydantic-required.

6. **[FIX-IT] The bootstrap story tests `python -m silentwitness_mcp --transport http --port 4508` but does not exercise the auth-disabled path.** Add explicit BDD: "Given `SILENTWITNESS_GATEWAY_TOKEN` is unset, when launching with `--transport http`, the server SHALL exit with a clear error before binding the port." (Code is trivial in `__main__.py` lifecycle hook; story-fastmcp-server-bootstrap.md:123 calls out this requirement but the BDD scenarios don't cover it.)

7. **[FIX-IT] Add a startup invariant test:** assert at server-start time that `mcp.settings.transport_security is not None and mcp.settings.transport_security.enable_dns_rebinding_protection is True` whenever `--transport http`. This is a defense in depth against someone accidentally bumping the dependency pin downward in a future PR.

### NOTE — informational only, no spec change required

8. **[NOTE] v2 migration path** — When mcp v2 stabilizes (post-Q1 2026 slip; realistic target H2 2026), the only code change needed is `from mcp.server.fastmcp import FastMCP, Context` → `from mcp.server.mcpserver import MCPServer, Context` and replacing `FastMCP("name")` with `MCPServer("name")`. The `@mcp.tool()`, `@mcp.resource()`, lifespan, and Context surface are byte-identical between FastMCP v1 and MCPServer v2 (verified at `/tmp/mcp-python-audit/src/mcp/server/mcpserver/server.py:512`). Low-risk migration; can wait.

9. **[NOTE] Tasks primitive opt-in** — for `chainsaw_hunt` and `hayabusa_csv_timeline` which can exceed 30s on multi-GB evidence sets, tasks would be the natural fit if added later. The runtime is present in `mcp.server.experimental.*`. Marked experimental in the 2025-11-25 spec. Not for v1.

10. **[NOTE] The architecture's "we control the MCP server" framing (architecture.md:950) is correct** as the answer to tool-poisoning. Our deployment is single-server; the agent does not connect to third-party MCP servers. The MCPwn class is fully closed. The OX Security April 2026 "design flaw" RCE is a host-side issue (hosts auto-spawning untrusted MCP server commands); we are a server author, not affected.

---

## Pin recommendation

**`mcp>=1.23.0,<2.0`**

Concretely in `pyproject.toml` / `uv add`:
```
mcp>=1.23.0,<2.0
```

Rationale:
- `>=1.23.0` is the floor that closes CVE-2025-66416 (DNS-rebinding default — directly relevant to our story's BDD assertion that 127.0.0.1 binding is sufficient defense) and transitively CVE-2025-53366 (DoS — fixed 1.9.4).
- `<2.0` upper bound prevents an unattended pre-alpha v2 install (the v2 SDK renames `FastMCP` to `MCPServer`, a breaking import). Forces a deliberate migration PR when v2 lands.
- If we want to be more conservative on stability, pin exactly `mcp==1.27.2`. The patch releases since 1.23.0 (1.24.0, 1.25.0, 1.26.0, 1.27.0, 1.27.1, 1.27.2) brought tasks-scope fixes and stream lifecycle hardening. None affect our hot paths. I recommend the range pin over the exact pin so dependabot can keep us current.
- Already-locked transitive deps from this pin: `pydantic>=2.11.0,<3.0.0`, `starlette>=0.27`, `uvicorn>=0.31.1`, `anyio>=4.5`, `pydantic-settings>=2.5.2`, `pyjwt[crypto]>=2.10.1`. All compatible with our `pydantic>=2.9` / `pydantic-ai>=0.1` constraints in `architecture.md:1046`.

---

## Sources

**Primary source-reads (commit-pinned):**
- `modelcontextprotocol/python-sdk` @ v1.27.2 (`6213787`, 2026-05-29): `src/mcp/server/fastmcp/server.py`, `src/mcp/server/fastmcp/tools/base.py`, `src/mcp/server/fastmcp/tools/tool_manager.py`, `src/mcp/server/fastmcp/utilities/func_metadata.py`, `src/mcp/server/lowlevel/server.py`, `src/mcp/server/transport_security.py`, `src/mcp/server/auth/settings.py`, `src/mcp/server/auth/provider.py`, `src/mcp/types.py`, `src/mcp/server/experimental/__init__.py`, `pyproject.toml`, `README.v2.md`.
- `modelcontextprotocol/python-sdk` @ main (`ed39e73`, 2026-06-02): `src/mcp/server/mcpserver/__init__.py`, `src/mcp/server/mcpserver/server.py`.

**Spec source (`modelcontextprotocol.io`):**
- `/specification/2025-11-25` — overview
- `/specification/2025-11-25/basic/transports` — Streamable HTTP MUST/SHOULD security clauses (Origin validation, localhost binding, auth)
- `/specification/2025-11-25/basic/lifecycle` — initialize handshake, capability negotiation
- `/specification/2025-11-25/basic/security_best_practices` — confused deputy, token passthrough, SSRF, session hijacking, local server compromise, scope minimization
- `/specification/2025-11-25/basic/utilities/tasks` — tasks primitive (experimental)

**CVE / advisory sources:**
- CVE-2025-53366 / GHSA-3qhf-m339-9g5v — FastMCP malformed-request DoS (fix: mcp 1.9.4). GitLab Advisory: https://advisories.gitlab.com/pkg/pypi/mcp/CVE-2025-53366/. Miggo: https://www.miggo.io/vulnerability-database/cve/CVE-2025-53366.
- CVE-2025-66416 / GHSA-9h52-p55h-vw2f — DNS rebinding default-off (fix: mcp 1.23.0). GitHub advisory: https://github.com/advisories/GHSA-9h52-p55h-vw2f. Vulnerable MCP Project: https://vulnerablemcp.info/vuln/cve-2025-66414-66416-dns-rebinding-mcp-sdks.html.
- CVE-2026-33032 / MCPwn — nginx-ui auth bypass. Pluto Security disclosure: https://pluto.security/blog/mcp-bug-nginx-security-vulnerability-cvss-9-8/. The Hacker News: https://thehackernews.com/2026/04/critical-nginx-ui-vulnerability-cve.html. Picus teardown: https://www.picussecurity.com/resource/blog/cve-2026-33032-mcpwn-how-a-missing-middleware-call-in-nginx-ui-hands-attackers-full-web-server-takeover.
- OX Security April 2026 disclosure — "MCP by design" RCE (host-side, not relevant to us as a server author). https://www.ox.security/blog/the-mother-of-all-ai-supply-chains-critical-systemic-vulnerability-at-the-core-of-the-mcp/. The Register: https://www.theregister.com/2026/04/16/anthropic_mcp_design_flaw/.

**PyPI / GitHub metadata:**
- `mcp` PyPI: https://pypi.org/project/mcp/ — latest stable 1.27.2 (audit date 2026-06-03)
- python-sdk repo: https://github.com/modelcontextprotocol/python-sdk — `v1.x` is the maintenance branch; `main` is pre-alpha v2.

**Runtime validation:**
- Live smoke test executed in ephemeral `uv run --with 'mcp==1.27.2' --with 'pydantic>=2.11'` venv on macOS Darwin 25.2.0 / Python 3.12, audit date 2026-06-03. Confirmed: (a) `@mcp.tool()` derives outputSchema from `ToolResponse[ObservationResult]` generic return annotation; (b) `FastMCP(host="127.0.0.1")` constructs `transport_security.enable_dns_rebinding_protection=True` automatically; `FastMCP(host="0.0.0.0")` constructs `transport_security=None`.
