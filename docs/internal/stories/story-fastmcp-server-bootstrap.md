# Story — FastMCP server bootstrap (stdio + Streamable HTTP transports)

**ID:** story-fastmcp-server-bootstrap
**Epic:** Epic 4 — MCP server skeleton + finding-state tools
**Depends on:** story-citation-gate, story-entity-gate, story-sanitizer, story-audit-logger, story-evidence-registry, story-hmac-ledger, story-common-types
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As an** MCP client (Claude Code, Claude Desktop, the Pydantic AI reference agent, Cherry Studio, LibreChat, Continue)
**I want to** connect to a single `silentwitness` server over either stdio (subprocess) or Streamable HTTP on `localhost:4508`
**So that** any compliant MCP host on the SIFT 2026 VM can drive the SilentWitness tool surface with zero glue code — matching the model-agnostic floor set by Valhuntir

---

## File modification map

Exact files the coding agent creates or modifies:

- `src/silentwitness_mcp/__init__.py` — UPDATE — exports `__version__`, top-level `mcp` instance handle for entrypoint discovery
- `src/silentwitness_mcp/__main__.py` — NEW — module entrypoint so `python -m silentwitness_mcp` launches the server (≤40 LOC)
- `src/silentwitness_mcp/server.py` — NEW — FastMCP instance construction; tool registration; lifecycle hooks; transport selection (stdio | http); capability declaration (≤350 LOC)
- `src/silentwitness_mcp/_lifecycle.py` — NEW — startup checks (mount validator from story-evidence-registry; audit-id sequence resume from story-audit-logger; injection-pattern YAML load from story-sanitizer); shutdown flushers (≤150 LOC)
- `tests/integration/__init__.py` — NEW — package marker
- `tests/integration/test_server_bootstrap.py` — NEW — ≥10 integration tests: stdio handshake; HTTP handshake on 4508; capability declaration; tool registration; shutdown cleanup; bearer-token rejection on HTTP

The coding agent must NOT modify files outside this map.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the project is installed and `silentwitness_mcp` is on PYTHONPATH
When  `python -m silentwitness_mcp` is launched with no arguments
Then  the process opens stdio for MCP framing
And   responds to the MCP `initialize` request with serverInfo.name == "silentwitness"
And   the response capabilities object declares `tools.listChanged=true`

Given the server is launched as `python -m silentwitness_mcp --transport http --port 4508`
When  a client sends an MCP initialize over Streamable HTTP to http://127.0.0.1:4508/mcp
Then  the handshake completes with protocolVersion matching the MCP 2025-11-25 revision
And   the bind address is 127.0.0.1 (NOT 0.0.0.0) — DNS-rebinding defense

Given the HTTP server requires SILENTWITNESS_GATEWAY_TOKEN env var
When  a client connects without an Authorization: Bearer header
Then  the server returns HTTP 401

Given the server is initialized
When  the client calls tools/list
Then  the response includes every registered tool from the §4.2 catalog (record_observation, record_interpretation, record_pivot, record_narrative, approve_finding, register_evidence, verify_evidence_hash, and the tool-wrapper stubs)

Given the lifecycle startup hook runs
When  /evidence is mounted without ro,noexec,nosuid
Then  the server logs a startup error to stderr
And   the server refuses to register any evidence-bound tool (every call returns MOUNT_NOT_RO_NOEXEC_NOSUID)

Given the server is running and the audit/ directory contains prior JSONL entries from a previous session
When  the server starts
Then  the audit_id sequence resumes from max(extant) + 1 for the current date

Given the server is shut down via SIGTERM
When  the shutdown hook runs
Then  all open JSONL writers fsync their buffers
And   the HMAC ledger holds no in-memory derived key (zeroed)

Given the bootstrap test suite is run
When  uv run pytest tests/integration/test_server_bootstrap.py
Then  ≥10 test cases pass
And   exit code is 0
```

---

## Shell verification

```bash
# Integration tests pass
uv run pytest tests/integration/test_server_bootstrap.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥10

# Server launches via python -m and responds to initialize
timeout 5 uv run python -c "
import asyncio, json
from mcp.client.stdio import stdio_client, StdioServerParameters
async def main():
    params = StdioServerParameters(command='python', args=['-m', 'silentwitness_mcp'])
    async with stdio_client(params) as (r, w):
        # initialize handshake assertion handled inside fixture; here we just verify launch
        pass
asyncio.run(main())
"

# Streamable HTTP binds 127.0.0.1:4508 only (NOT 0.0.0.0)
uv run python -m silentwitness_mcp --transport http --port 4508 &
SERVER_PID=$!
sleep 2
ss -tlnp 2>/dev/null | grep ":4508" | grep "127.0.0.1" || { echo "HTTP server not on loopback"; kill $SERVER_PID; exit 1; }
ss -tlnp 2>/dev/null | grep ":4508" | grep "0.0.0.0" && { echo "HTTP server bound to 0.0.0.0 — DNS rebinding risk"; kill $SERVER_PID; exit 1; }
kill $SERVER_PID

# Lint + types
uv run ruff check src/silentwitness_mcp/server.py src/silentwitness_mcp/__main__.py src/silentwitness_mcp/_lifecycle.py
uv run mypy --strict src/silentwitness_mcp/server.py src/silentwitness_mcp/__main__.py src/silentwitness_mcp/_lifecycle.py

# File-size guard
[ "$(wc -l < src/silentwitness_mcp/server.py)" -le 400 ]
[ "$(wc -l < src/silentwitness_mcp/_lifecycle.py)" -le 400 ]
```

---

## Notes for coding agent

- Source of truth: architecture.md §4.1 (what the server is); §4.2 (tool catalog with snake_case names); §7.3 (transports: stdio default, Streamable HTTP on `localhost:4508`); §8 (sequence diagrams of agent ↔ server interaction); architecture.md cites `context/technical/07` §A2–A8 for protocol primitives.
- Context7 is MANDATORY before writing the first line of this story: `mcp__plugin_context7_context7__resolve-library-id libraryName="mcp"`, then `mcp__plugin_context7_context7__query-docs context7CompatibleLibraryID=<resolved> topic="FastMCP server stdio Streamable HTTP transport lifecycle"`. The MCP Python SDK ships in lockstep with protocol revisions (`02` §2 / `07` §A3.2), and training data may be out of date.
- The FastMCP construction pattern: `mcp = FastMCP("silentwitness", version=__version__)`. Tool registration happens via `@mcp.tool()` decorators imported from the `findings/`, `evidence/`, and `tools/` modules. This story registers the SHELLS / placeholders for the findings tools — actual logic lives in stories 8–12 of this epic.
- Transport CLI: `python -m silentwitness_mcp` defaults to stdio. Pass `--transport http --port 4508` for HTTP; pass `--transport stdio` to be explicit. Architecture.md §7.3 commits port 4508.
- HTTP bind to `127.0.0.1` ONLY. Per `context/technical/07` §A3.2: DNS-rebinding defense requires loopback-only binding. NEVER `0.0.0.0`.
- HTTP auth: bearer token from `$SILENTWITNESS_GATEWAY_TOKEN` env var (architecture.md §7.3). If the env var is unset, HTTP server refuses to start. stdio transport has no auth (subprocess identity is the boundary).
- Capability declaration (per `context/technical/07` §A6 server capabilities): declare `tools.listChanged=true`, `logging=true`. We do NOT declare `prompts`, `resources`, or `sampling` server-side capabilities in v1 (out of scope).
- Lifecycle hooks (architecture.md §4.11 mount check + §4.4 audit_id resume + §4.8 sanitizer YAML load):
  - `on_startup`: call `mount.validate()`; rebuild audit-id sequencer; load injection-patterns YAML; install SIGHUP handler for YAML reload.
  - `on_shutdown`: fsync every open JSONL handle; zero any in-memory HMAC keys; release spaCy model handle.
- Tool registration is split across files; this story imports each module to trigger decorator registration but does NOT implement the tool bodies. Tools 8–12 of this epic implement them.
- Logging: emit JSONL audit events via direct Pydantic `model_dump_json()` (per audit Decision A — `structlog` was dropped). For non-audit informational logging, `logging.getLogger(__name__)` from stdlib. NO `print()`. Forward log entries through MCP's `notifications/message` so the host sees them.
- Error envelope: every tool returns the `ToolResponse` envelope from story-response-envelope; the FastMCP layer surfaces `success=False` cases as MCP error responses with `code=-32000` and the structured reason in `error.data`.
- Context7 hint redux: also query `pydantic-ai` topic "MCPServerStdio MCPServerHTTP toolset binding" to ensure the server-side shape matches client expectations (the reference agent's binding lives in Epic 8).
- Vocabulary: never "court-admissible." Stay clinical. The MCP server is "the typed tool surface" — that's the framing.
- Known pitfalls: (1) FastMCP requires a `lifespan` async context manager for proper shutdown; do NOT use `@app.on_event` (deprecated upstream pattern); (2) Streamable HTTP's session handshake is stateful — the server must persist session state across requests; if running behind a reverse proxy, the proxy must forward the `Mcp-Session-Id` header; (3) stdio mode is the Claude Code default — the SIFT 2026 pre-installed Claude Code v2.0.61 launches `python -m silentwitness_mcp` as a subprocess and expects no banner output on stdout (any banner breaks the JSON-RPC framing). Banner output goes to stderr only.
