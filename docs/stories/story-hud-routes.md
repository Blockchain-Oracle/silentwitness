# Story — Streaming HUD route handlers (`/`, `/case/<id>`, `/findings`, `/audit`)

**ID:** story-hud-routes
**Epic:** Epic 13 — Streaming HUD (OPTIONAL — stretch)
**Optional:** **true** — orchestrator may skip if Wave 4 runs hot (epics.md §1 marks E13 cuttable)
**Depends on:** story-hud-sse-server, story-hypothesis-stack, story-audit-logger, story-record-observation-tool
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** build the four read-only HTML route handlers in `src/silentwitness_hud/routes.py` — landing (`/`), case detail (`/case/<case-id>`), findings list (`/findings`), and audit viewer (`/audit`) — using inline HTML templates (no Jinja, no framework) that the stdlib `BaseHTTPRequestHandler` from story-hud-sse-server dispatches to
**So that** the HUD's four browser surfaces (ux-spec §3.4) render server-side with a graceful JS-free fallback (per ux-spec §3.6 the SSE subscriber is the only JS), each surface auto-updates from the same `EventBus` stream the agent already publishes to, and the entire HUD remains a read-only renderer with zero write surfaces (ux-spec §3.4 explicit — "no `/approve`, no `/reject`, no write surfaces. Approval lives in CLI per §2.4")

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `src/silentwitness_hud/routes.py` — NEW — pure-function handlers dispatched by `_HUDRequestHandler.do_GET` from story-hud-sse-server. Public surface:
  - `def handle_landing(case_dir: Path) -> tuple[int, bytes, dict[str, str]]` — renders `/`. Returns `(200, body, headers)` where body is HTML showing: current case ID + status (read from `case_dir/.silentwitness/case.toml`), elapsed time, the last 10 events from `HUD_EVENT_BUS.recent`, and a `<script type="module" src="/assets/hud.js"></script>` tag (story-hud-css). Server-rendered; the 10 events show even with JS disabled (ux-spec §3.4 "JS-free fallback").
  - `def handle_case_detail(case_dir: Path, case_id: str) -> tuple[int, bytes, dict[str, str]]` — renders `/case/<id>`. Sections: hypothesis stack (parsed from `cases/<case_id>/audit/hypothesis.jsonl` — tail last 50 lines, group by `hypothesis_id`, show current state per architecture.md §5.3 form/dispatch/confirm/pivot/abandon); findings (staged + approved counts from `cases/<case_id>/findings.json`); budget (tokens spent / max from latest `agent.jsonl` `step` line). Auto-updates from `/events` via the `hud.js` subscriber (story-hud-css). Returns 404 if `case_id` directory does not exist.
  - `def handle_findings(case_dir: Path) -> tuple[int, bytes, dict[str, str]]` — renders `/findings`. Lists every finding from `cases/<active_case>/findings.json` (one row per finding: ID, status (STAGED|APPROVED|REJECTED|ARCHIVED), title, confidence, citations). Each row's `audit_id` citation links to `/audit?audit_id=<id>` (deep-link per ux-spec §3.4). Read-only — no approve button (ux-spec §3.6).
  - `def handle_audit(case_dir: Path, query: dict[str, str]) -> tuple[int, bytes, dict[str, str]]` — renders `/audit`. Tail-style JSONL viewer paginated 100 lines per page. Reads `cases/<case>/audit/<backend>.jsonl` files (architecture.md §3 — `harness/`, `audit/<backend>.jsonl` per MCP backend). Columns: ts, type, tool_name, audit_id, result_sha256 (truncated to first 8 chars + last 4), elapsed_ms. Anchor `<a id="audit_id-<id>">` per row so the deep-link from `/findings?audit_id=<id>` jumps to the right row.
  - `def render_404(path: str) -> tuple[int, bytes, dict[str, str]]` — minimal 404 page.
  - `def _html_escape(text: str) -> str` — wrap `html.escape(text, quote=True)` so the inline templates can't be XSS'd by malicious tool output. CRITICAL — tool output is untrusted (a `windows.cmdline` result could contain `<script>` from a malware sample). Every interpolation in every template MUST go through this.
  - `def _read_case_state(case_dir: Path) -> CaseState` — small helper returning a `CaseState` dataclass (case_id, examiner, status, elapsed, last_event_ts) from `.silentwitness/case.toml` + tail of `audit/hypothesis.jsonl`.
  - HTML templates are inline f-strings (no Jinja per ux-spec §3.6 framework ban). Each template ≤60 LOC. Semantic HTML5: `<main>`, `<section>`, `<table>` (ux-spec §6 — screen-reader friendly).
  - Target ≤300 LOC.
- `tests/unit/test_hud_routes.py` — NEW — ≥15 behavioural tests:
  - `handle_landing` returns status 200 + valid HTML;
  - `handle_landing` includes the last 10 events from a seeded `HUD_EVENT_BUS.recent`;
  - `handle_landing` includes the `<script src="/assets/hud.js">` tag;
  - `handle_case_detail` returns 200 for an existing case;
  - `handle_case_detail` returns 404 for a missing case;
  - `handle_case_detail` parses `hypothesis.jsonl` and groups by hypothesis_id;
  - `handle_case_detail` shows current state per hypothesis (form|dispatch|confirm|pivot|abandon);
  - `handle_case_detail` shows staged + approved finding counts;
  - `handle_case_detail` shows token budget consumed / max;
  - `handle_findings` lists every finding from a seeded `findings.json`;
  - `handle_findings` links each `audit_id` to `/audit?audit_id=<id>`;
  - `handle_findings` contains NO `<button>`, `<form>`, or `<input type="submit">` (read-only — ux-spec §3.4);
  - `handle_audit` paginates at 100 lines/page;
  - `handle_audit` anchors each row with `id="audit_id-<id>"`;
  - `render_404` returns status 404 + minimal HTML;
  - `_html_escape` neutralises `<script>` inside an interpolated tool output string (XSS guard).
- `tests/integration/test_hud_routes_e2e.py` — NEW — 1 scenario: spin up `run_hud_server` on an ephemeral port, seed a fake case directory with `hypothesis.jsonl` (3 hypotheses, one pivot), `findings.json` (5 findings), and `audit/mcp.jsonl` (50 entries). Hit each of the 4 routes via `urllib.request.urlopen`, assert status 200 + the expected substrings appear in each body.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a seeded case directory at cases/test-case-001/ with case.toml present
When  handle_landing(case_dir) is called
Then  the response status is 200
And   the body contains "test-case-001"
And   the body contains the last 10 entries from HUD_EVENT_BUS.recent (server-rendered)
And   the body contains '<script type="module" src="/assets/hud.js">'

Given a seeded case directory with audit/hypothesis.jsonl containing 3 hypotheses and 1 pivot transition
When  handle_case_detail(case_dir, "test-case-001") is called
Then  the response status is 200
And   the body contains "H-001", "H-002", "H-003" (each hypothesis ID)
And   exactly one hypothesis shows state "PIVOTED"

Given cases/missing-case-999/ does not exist
When  handle_case_detail(case_dir, "missing-case-999") is called
Then  the response status is 404
And   the body contains "case 'missing-case-999' not found"

Given a seeded findings.json with 5 staged findings
When  handle_findings(case_dir) is called
Then  the response status is 200
And   the body contains exactly 5 table rows for findings
And   each row's audit_id is wrapped in <a href="/audit?audit_id=<id>">
And   the body contains zero <button>, <form>, or <input type="submit"> tags (read-only)

Given a seeded audit/mcp.jsonl with 250 entries
When  handle_audit(case_dir, query={"page": "2"}) is called
Then  the response status is 200
And   exactly 100 audit rows appear in the body (page 2 of 3)
And   each row has an HTML anchor id="audit_id-<the-audit-id>"

Given a tool result containing the literal substring "<script>alert(1)</script>"
When  it is interpolated into any of the four routes' templates
Then  the rendered HTML contains "&lt;script&gt;alert(1)&lt;/script&gt;" (escaped)
And   the raw <script> tag does NOT appear in the response body

Given the HUD is running and an HTTP GET hits /unknown-path
When  the dispatch happens
Then  render_404 is called
And   the response status is 404

Given tests/unit/test_hud_routes.py exists
When  `uv run pytest tests/unit/test_hud_routes.py -v` runs
Then  exit code is 0
And   ≥15 tests pass

Given tests/integration/test_hud_routes_e2e.py exists
When  `uv run pytest tests/integration/test_hud_routes_e2e.py -v` runs
Then  exit code is 0

Given `uv run coverage run -m pytest tests/unit/test_hud_routes.py tests/integration/test_hud_routes_e2e.py`
When  `uv run coverage report --include="src/silentwitness_hud/routes.py" --fail-under=85` runs
Then  exit code is 0

Given `grep -rE "(jinja|mako|tornado\.template)" src/silentwitness_hud/routes.py`
When  the output is inspected
Then  zero matches appear (ux-spec §3.6 template-engine ban)

Given `grep -rE "(POST|PUT|DELETE|PATCH)" src/silentwitness_hud/routes.py`
When  the output is inspected
Then  zero matches appear (read-only HUD per ux-spec §3.4)
```

Every criterion is checkable by running a command. Prose-only criteria = blocked.

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
# Unit tests
uv run pytest tests/unit/test_hud_routes.py -v
# Must show ≥15 passing

# Integration e2e
uv run pytest tests/integration/test_hud_routes_e2e.py -v
# Must show 1 passing

# Coverage ≥85% on routes.py
uv run coverage run -m pytest tests/unit/test_hud_routes.py tests/integration/test_hud_routes_e2e.py
uv run coverage report --include="src/silentwitness_hud/routes.py" --fail-under=85

# Template-engine + write-method bans
grep -rE "(jinja|mako|tornado\.template)" src/silentwitness_hud/routes.py && exit 1 || true
grep -rE "(POST|PUT|DELETE|PATCH)" src/silentwitness_hud/routes.py && exit 1 || true

# XSS guard: every interpolation must route through _html_escape
grep -cE "_html_escape\(" src/silentwitness_hud/routes.py
# Must output ≥10 — every dynamic interpolation in the templates

# Strict typing + lint + file-size guard
uv run mypy --strict src/silentwitness_hud/routes.py
uv run ruff check src/silentwitness_hud/routes.py
uv run ruff format --check src/silentwitness_hud/routes.py
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_hud/routes.py
# routes.py must be ≤300 LOC
```

---

## Notes for coding agent

- **OPTIONAL EPIC** — see epics.md §5 risk-weighted: drop if Wave 4 runs hot. The rich terminal layout from story-cli-investigate is canonical; this HUD is the demo split-screen (ux-spec §4) for non-DFIR judges.
- **Why inline f-strings not Jinja** — ux-spec §3.6 framework ban. 4 routes × ≤60 LOC = ≤240 LOC of template HTML, easy to fit. The `_html_escape` discipline replaces Jinja's auto-escape.
- **Why XSS escaping matters in a forensic tool** — tool output is untrusted by design. A malware sample's PE name, a registry key value, an EVTX event message — any of these can contain `<script>`, JavaScript URIs, or HTML-encoded payloads designed to defeat naive viewers. The HUD renders raw tool output. Every interpolation MUST `_html_escape`. The XSS test is non-negotiable.
- **Why read-only** — ux-spec §3.4 explicit: "No `/approve`, no `/reject`, no write surfaces. Approval lives in CLI per §2.4." The HMAC ledger (architecture.md §4.9 — HMAC-signed approval ledger) requires the examiner password every approval; that flow is terminal-only by threat-model design (BRAINSTORM Decision 5 — the password IS the HMAC key, caching it defeats the threat model). The HUD never accepts a POST. The grep gate enforces this in code.
- **Hypothesis state machine source** — architecture.md §5.3 verbatim shape:
  ```jsonc
  {
    "ts": "<iso8601 UTC>",
    "type": "form|dispatch|confirm|pivot|abandon",
    "hypothesis_id": "H-007",
    "reason": "<free text>",
    "related_audit_ids": ["sift-aj-20260613-042", "..."],
    "tokens_spent": 3214,
    "steps_spent": 6
  }
  ```
  `handle_case_detail` tails the last 50 lines of `audit/hypothesis.jsonl`, groups by `hypothesis_id`, and shows the latest `type` per group as the current state. PIVOTED hypotheses get the warning color token (#f4a259 per ux-spec §3.5).
- **Findings shape** — `cases/<case_id>/findings.json` is the source (story-record-observation-tool + story-approve-finding-tool are the writers). Each finding has: `finding_id` (`F-<case>-NNN`), `status` (STAGED|APPROVED|REJECTED|ARCHIVED), `observation_text`, `interpretation_text`, `confidence` (per architecture.md §4.3 `Confidence` literal), `cited_audit_ids` (list), `mitre_techniques` (list).
- **Audit JSONL source** — `cases/<case_id>/audit/<backend>.jsonl` per architecture.md §3. The HUD tails one file at a time (default: the MCP backend's JSONL). Use `pathlib.Path.iterdir()` to list backends in the audit directory; let the query string `?backend=<name>` pick one.
- **Pagination** — query string `?page=N` defaults to 1. Read the file once, slice `[(page-1)*100 : page*100]`. For ≤10k entries this is fine; if a case explodes past that, add a TODO comment for streaming pagination (out of scope for this story).
- **Deep-link convention** — `/findings` rows link to `/audit?audit_id=<id>`. `handle_audit` recognises `query["audit_id"]` and jumps to that anchor in the rendered page (adds an HTML `<script>document.getElementById("audit_id-<id>").scrollIntoView();</script>` at end of body — single-line, no framework needed). Per ux-spec §3.4 the audit page is the deep-link target for every verify link.
- **Design tokens** — defer all styling to `src/silentwitness_hud/assets/hud.css` (story-hud-css). This story produces semantic HTML5 only — no inline `style=`. The CSS file handles all visual concerns including the dark palette (ux-spec §3.5 #0a0a0a / #1a1a1a / #e8e8e8 / #7fb069 / #f4a259 / #d96c5c / #5ba3d0 / JetBrains Mono).
- **Library docs to consult via Context7 BEFORE coding** (architecture §12 mandate):
  - `mcp__plugin_context7_context7__resolve-library-id libraryName="python-stdlib-html"` — verify `html.escape` quote-handling default (we want `quote=True`)
  - `query-docs` topic `"urllib.parse parse_qs query string"` — for the `?page=N&audit_id=<id>` parsing
- **Pitfall:** `tomllib` (stdlib, Python 3.11+) parses `.silentwitness/case.toml` — do NOT pull `toml` or `tomli` as a dependency.
- **Pitfall:** the f-string template must wrap multi-line interpolations carefully. For tables, build the rows as a list and `"\n".join(rows)` then interpolate the joined string — single-pass escape, no half-rendered DOM.
- **Pitfall:** `BaseHTTPRequestHandler.send_response` writes the status line but does NOT send headers — must call `send_header` then `end_headers` separately. story-hud-sse-server's `_HUDRequestHandler.do_GET` is the caller; this story's handlers return the tuple and let the dispatcher write the wire format. Keep the boundary clean — these handlers are pure functions.
- **Vocabulary discipline:** never "court-admissible." Never "Ralph Wiggum" in docstrings. The HUD is a "read-only renderer over the agent's event stream."
- LOC budget: ≤300 — comfortable for 4 handlers + the XSS helper + the case-state helper. If approaching 300, split per-route into separate files (`landing.py`, `case_detail.py`, etc.) under a `routes/` subpackage.
