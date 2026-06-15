# Story — Streaming HUD SSE server (stdlib HTTP, port 8088)

**ID:** story-hud-sse-server
**Epic:** Epic 13 — Streaming HUD (OPTIONAL — stretch)
**Optional:** **true** — orchestrator may skip this story if Wave 4 runs hot (epics.md §1 marks E13 cuttable; ux-spec §4 confirms the rich terminal layout alone carries the live-render value)
**Depends on:** story-investigator-hooks, story-hypothesis-stack, story-atomic-io
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** build a minimal stdlib HTTP server in `src/silentwitness_hud/server.py` that binds `127.0.0.1:8088`, exposes a small in-memory `EventBus` that `silentwitness_agent.hooks` callbacks push to, and serves a Server-Sent-Events stream at `/events` plus four read-only HTML routes (`/`, `/case/<case-id>`, `/findings`, `/audit`)
**So that** the demo split-screen (ux-spec §4) renders the live investigation in a browser without a JavaScript framework, without an external CDN, and without binding the SIFT-occupied port 80 — the HUD is a stretch renderer over the same `HypothesisEvent` + `agent.jsonl` data the CLI already produces, so dropping this epic does not lose any audit-trail content

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `src/silentwitness_hud/__init__.py` — NEW — package marker; exports `EventBus`, `run_hud_server`. ~10 LOC.
- `src/silentwitness_hud/server.py` — NEW — stdlib `http.server.ThreadingHTTPServer` subclass + `BaseHTTPRequestHandler` subclass plus an `asyncio`-backed `EventBus` (in-memory `asyncio.Queue` per subscriber). Public surface:
  - `class EventBus` — small in-memory pub/sub. Methods: `subscribe() -> asyncio.Queue[dict]` (called per SSE client), `unsubscribe(q)`, `publish(event: dict) -> None` (called by hooks; non-blocking — drops the oldest event if a subscriber's queue exceeds `max_queue=256`). Maintains a `recent: collections.deque[dict]` (maxlen=200) so a new SSE client can be backfilled the last 200 events on connect. The bus is process-global at `silentwitness_hud.server.HUD_EVENT_BUS` so `silentwitness_agent.hooks` can `from silentwitness_hud.server import HUD_EVENT_BUS; HUD_EVENT_BUS.publish(...)` from `_on_before_tool` / `_on_after_tool` / `_on_step` / `_on_finish` (cite story-investigator-hooks line 167–171 JSONL shapes — the HUD bus receives the same dict the agent.jsonl line records, plus an injected `case_id`).
  - `def run_hud_server(host: str = "127.0.0.1", port: int = 8088, case_dir: Path) -> threading.Thread` — starts the server on a daemon thread (so `silentwitness investigate --hud` can launch it without blocking the rich live loop). Returns the thread handle so the CLI can `.join(timeout=1)` on shutdown. Refuses any host other than `127.0.0.1` or `localhost` — raises `ValueError("HUD must bind loopback only — auth-by-scope per ux-spec §3.6")`.
  - `class _HUDRequestHandler(BaseHTTPRequestHandler)` — dispatches to handlers in `silentwitness_hud.routes` (story-hud-routes). Implements `do_GET` only; everything else returns 405. Logs to `cases/<case_id>/audit/hud.jsonl` (one line per request: ts, path, status, elapsed_ms) via `atomic_io.append_jsonl_line` (cite story-atomic-io). NO request logging to stderr (would interleave with rich live layout in the same terminal).
  - SSE generator at `/events` runs the connection in a per-request asyncio loop: subscribe to `HUD_EVENT_BUS`, flush the `recent` backlog as a single batch first, then `await queue.get()` in a loop, formatting each event as `event: <type>\ndata: <json>\n\n` and writing to `self.wfile`. Connection terminates cleanly on `BrokenPipeError` (browser tab closed). Heartbeat: emit `: ping\n\n` every 15s so proxies don't time out.
  - Refuse to start if port 8088 is in use — print to stderr `[red]✗[/red] HUD port 8088 busy (Apache or another HUD instance?). HUD disabled; CLI unaffected.` and return `None`. The CLI must tolerate this — HUD failure must NOT crash `silentwitness investigate`.
  - Target ≤300 LOC.
- `tests/unit/test_hud_server.py` — NEW — ≥12 behavioural tests using `unittest.mock` + `socket` + a synthetic `EventBus`:
  - `EventBus.subscribe()` returns an `asyncio.Queue`;
  - `EventBus.publish(...)` delivers to one subscriber;
  - `EventBus.publish(...)` delivers to N subscribers (fan-out);
  - `EventBus.publish(...)` drops the oldest event when a subscriber's queue hits `max_queue`;
  - `EventBus.recent` retains the last 200 events;
  - `run_hud_server(host="0.0.0.0", ...)` raises `ValueError` (loopback-only bind enforced);
  - `run_hud_server(...)` with port 8088 already bound returns `None` and prints a graceful warning (no crash);
  - `_HUDRequestHandler.do_POST` returns 405;
  - request logging appends one line to `cases/<case>/audit/hud.jsonl` per request;
  - the SSE generator emits a `: ping\n\n` heartbeat at ≤15s intervals (use a fast-clock mock);
  - SSE generator backfills `recent` events on connection;
  - SSE generator terminates cleanly on `BrokenPipeError`.
- `tests/integration/test_hud_smoke.py` — NEW — 1 e2e scenario: spin up `run_hud_server` on an ephemeral port (override 8088 → port `0` for test isolation), publish 3 events to `HUD_EVENT_BUS`, open a raw socket to `/events`, read until `data:` line, assert all 3 events appear in order. Use `urllib.request.urlopen` for the HTML routes (smoke check status 200 + `Content-Type: text/html; charset=utf-8`).

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given run_hud_server(host="127.0.0.1", port=8088, case_dir=cases/<case>) is called
When  the returned thread is started
Then  curl -sI http://127.0.0.1:8088/ returns HTTP/1.1 200 OK
And   the response Content-Type is "text/html; charset=utf-8"

Given the HUD is running and HUD_EVENT_BUS.publish({"type":"before_tool", "tool_name":"vol_pslist", ...}) is called
When  a client connects to /events
Then  the SSE stream emits an "event: before_tool\ndata: {...}\n\n" frame within 100ms
And   the frame's data field parses as JSON
And   the JSON contains the published tool_name verbatim

Given the HUD is running with no subscribers
When  HUD_EVENT_BUS.publish(...) is called 250 times
Then  HUD_EVENT_BUS.recent contains exactly 200 events (deque maxlen)
And   a new /events subscriber receives those 200 events as a backfill batch on connect

Given run_hud_server(host="0.0.0.0", port=8088, case_dir=...) is called
When  the function executes
Then  it raises ValueError
And   the error message contains "loopback only"

Given port 8088 is already bound by another process
When  run_hud_server(...) is called
Then  the function returns None (does NOT raise)
And   stderr contains "HUD port 8088 busy"
And   the calling CLI process continues running normally

Given a POST request to /events
When  _HUDRequestHandler.do_POST executes
Then  the response status is 405 Method Not Allowed

Given the SSE generator is mid-stream
When  the client closes the connection (simulated BrokenPipeError)
Then  the generator exits cleanly
And   HUD_EVENT_BUS.unsubscribe was called for that subscriber's queue

Given 30 seconds elapse on an idle SSE connection (mocked clock)
When  the generator's main loop ticks
Then  at least two ": ping\n\n" heartbeat frames have been written

Given tests/unit/test_hud_server.py exists
When  `uv run pytest tests/unit/test_hud_server.py -v` runs
Then  exit code is 0
And   ≥12 tests pass

Given tests/integration/test_hud_smoke.py exists
When  `uv run pytest tests/integration/test_hud_smoke.py -v` runs
Then  exit code is 0
And   the e2e SSE scenario passes

Given `uv run coverage run -m pytest tests/unit/test_hud_server.py tests/integration/test_hud_smoke.py`
When  `uv run coverage report --include="src/silentwitness_hud/server.py" --fail-under=85` runs
Then  exit code is 0

Given `grep -rE "(flask|fastapi|starlette|aiohttp|tornado|jinja|tailwind)" src/silentwitness_hud/`
When  the output is inspected
Then  zero matches appear (ux-spec §3.6 framework ban)

Given `grep -rE "(cdn\.|googleapis|jsdelivr|unpkg|cdnjs)" src/silentwitness_hud/`
When  the output is inspected
Then  zero matches appear (ux-spec §3.6 no external CDN)
```

Every criterion is checkable by running a command. Prose-only criteria = blocked.

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
# Unit tests
uv run pytest tests/unit/test_hud_server.py -v
# Must show ≥12 passing

# Integration smoke
uv run pytest tests/integration/test_hud_smoke.py -v
# Must show 1 passing

# Coverage ≥85% on server.py
uv run coverage run -m pytest tests/unit/test_hud_server.py tests/integration/test_hud_smoke.py
uv run coverage report --include="src/silentwitness_hud/server.py" --fail-under=85

# Framework + CDN bans (ux-spec §3.6)
grep -rE "(flask|fastapi|starlette|aiohttp|tornado|jinja|tailwind)" src/silentwitness_hud/ && exit 1 || true
grep -rE "(cdn\.|googleapis|jsdelivr|unpkg|cdnjs)" src/silentwitness_hud/ && exit 1 || true

# Port 8088 hardcoded, no port 80
grep -E "port.*=.*80\b" src/silentwitness_hud/server.py && exit 1 || true
grep -E "8088" src/silentwitness_hud/server.py || (echo "8088 must be the default port"; exit 1)

# Loopback-only bind enforced
grep -E '"0\.0\.0\.0"' src/silentwitness_hud/server.py && exit 1 || true

# Strict typing + lint + file-size guard
uv run mypy --strict src/silentwitness_hud/server.py
uv run ruff check src/silentwitness_hud/server.py
uv run ruff format --check src/silentwitness_hud/server.py
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_hud/server.py
# server.py must be ≤300 LOC
```

---

## Notes for coding agent

- **OPTIONAL EPIC** — if Wave 4 runs hot the orchestrator may skip this story entirely. The rich terminal live layout from story-cli-investigate is the canonical render; the HUD is the demo split-screen (ux-spec §4 + PRD §2 1:00–4:30). Per epics.md §1 row E13 and §5 Risk-Weighted, this is cuttable without losing the wedge.
- **Why stdlib `http.server` not Flask/FastAPI:** ux-spec §3.6 bans frameworks explicitly. Per `context/.raw-design-research/03` §"Implications" #6, Apache binds port 80 for CyberChef — we use 8088. Per same doc, Node.js is NOT pre-installed on SIFT 2026, so any Node-based HUD would require an install step that breaks the "judge runs `silentwitness investigate --hud` and it just works" promise. stdlib `http.server` + `asyncio` ships in CPython 3.12 (the SIFT default per `03 §"Base platform"`).
- **Why 127.0.0.1 only:** ux-spec §3.6 explicit ("No login UI — 127.0.0.1 bind only; security by scope, not auth"). Refuse 0.0.0.0 at the function level so a future config typo can't accidentally expose the HUD to the network.
- **Why port 8088:** ux-spec §3.2 verbatim — "8088 chosen: IANA-unassigned, distinct from common 8080, mnemonic ('two eights' = double witness), above 1024 so no root. Binds 127.0.0.1:8088; configurable via [hud].port and [hud].bind." Per `context/.raw-design-research/03` `scripts/cyberchef.sls:5–24` Apache already owns port 80; binding there would crash the HUD on every SIFT VM.
- **EventBus wiring** — `silentwitness_agent.hooks` (story-investigator-hooks) is the publisher. The hooks already emit dicts shaped `{"ts","type":"before_tool|after_tool|step|finish", ...}` to `agent.jsonl`. This story does NOT modify hooks.py; it adds a one-line import-and-publish call in each hook callback. Coding-agent convention: wrap the publish in `try: HUD_EVENT_BUS.publish(payload) except Exception: pass` so a HUD failure NEVER crashes the agent. The hook callback already has the payload — same dict goes to JSONL and to the bus.
- **`HypothesisEvent` source** — architecture.md §5.3 defines the `HypothesisEvent` shape written to `cases/<case_id>/audit/hypothesis.jsonl`. The HUD's `EventBus` carries the *same* dict per transition (form, dispatch, confirm, pivot, abandon). story-hypothesis-stack is the writer. When this story's HUD is enabled, hypothesis-stack should also publish to `HUD_EVENT_BUS` (same try/except wrap pattern).
- **SSE framing** — per ux-spec §3.4 the `/events` stream emits `event: <type>\ndata: <json>\n\n`. The `event:` line lets the browser side filter on `EventSource.addEventListener("before_tool", ...)` instead of parsing every payload. Heartbeat `: ping\n\n` (comment per SSE spec) every 15s keeps proxies happy.
- **Daemon thread** — the HUD MUST run on a daemon thread so Ctrl-C in the CLI terminates everything cleanly. Use `threading.Thread(target=..., daemon=True)`. Do NOT use `multiprocessing` (forks Pydantic AI state — disaster).
- **Request log** — `cases/<case_id>/audit/hud.jsonl` is parallel to `audit/agent.jsonl` (story-investigator-hooks) and `audit/<backend>.jsonl` (story-audit-logger). It records HTTP-level events only (path, status, elapsed_ms). NOT a security audit; just operational visibility. Per architecture.md §3 the audit/ subtree is the single source of truth for all JSONL streams.
- **Library docs to consult via Context7 BEFORE coding** (architecture §12 mandate):
  - `mcp__plugin_context7_context7__resolve-library-id libraryName="python-stdlib-http.server"` (or fall back to CPython docs for `http.server.ThreadingHTTPServer` + `BaseHTTPRequestHandler`) — verify `do_GET` signature + how to flush chunked responses for SSE
  - `query-docs` topic `"asyncio Queue subscribe fanout heartbeat"` — for the SSE generator's queue management
- **Pitfall:** `BaseHTTPRequestHandler` is synchronous; SSE wants async. Workaround: run the SSE per-connection generator on a dedicated `asyncio.new_event_loop()` per request thread. Heavy but ≤300 LOC and avoids pulling `aiohttp` (banned). Alternatively, a synchronous SSE loop with `self.wfile.write` + `self.wfile.flush` and a `time.sleep(0.05)` polling cadence is acceptable — under the §300 LOC ceiling, simpler is better.
- **Pitfall:** if the agent dispatches 10 specialists in rapid succession and a HUD client is slow to drain, the bus must not block the agent. The `publish` method must be non-blocking (drop-oldest semantics on full queue). Test this explicitly.
- **Pitfall:** the SIFT VM may have `firewalld` or `ufw` blocking even loopback by default. Per `context/.raw-design-research/03` §"Implications" #9 there is no firewall by default, but be defensive — print the URL the user should hit on startup (`[green]✓[/green] HUD live at http://127.0.0.1:8088`) so even if curl fails the user sees the bind attempt succeeded.
- **Vocabulary discipline:** never "court-admissible." Docstrings say "read-only renderer over the same event data the CLI produces." Never "Ralph Wiggum" — describe the behaviour.
- LOC budget: ≤300 — comfortable for stdlib HTTP + a small EventBus class. If approaching 300, split EventBus into its own `bus.py` module.
