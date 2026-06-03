# Story — Streaming HUD CSS + JS (vanilla dark tokens; SSE subscriber on 4 event types)

**ID:** story-hud-css
**Epic:** Epic 13 — Streaming HUD (OPTIONAL — stretch)
**Optional:** **true** — orchestrator may skip this story if Wave 4 runs hot (epics.md §1 marks E13 cuttable; ux-spec §4 confirms the rich terminal layout alone carries the live-render value)
**Depends on:** story-hud-sse-server, story-hud-routes, story-investigator-hooks
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** ship `src/silentwitness_hud/assets/hud.css` (≤200 LOC vanilla CSS using the dark token palette from ux-spec §3.5) plus `src/silentwitness_hud/assets/hud.js` (≤150 LOC vanilla JS subscribing to the `/events` SSE stream and updating the DOM on 4 event types: hypothesis, tool_call, finding, critic) AND a vendored JetBrains Mono WOFF2 with the matching `@font-face` declaration — no Tailwind, no React, no CDN
**So that** the HUD browser surface (ux-spec §3.4) is visually consistent with the rich terminal layout and the SilentWitness brand (`#0a0a0a` background, `#7fb069/#f4a259/#d96c5c/#5ba3d0` status palette, JetBrains Mono throughout), survives offline / firewalled SIFT 2026 environments (no external CDN per ux-spec §3.6 banned-patterns list), and the SSE subscriber renders the same data the rich live layout shows in the terminal — proving the HUD is a renderer over the same hypothesis-pivot data, not a separate control plane.

---

## File modification map

- `src/silentwitness_hud/assets/hud.css` — NEW — ≤200 LOC vanilla CSS, no preprocessors, no imports. Sections:
  1. `:root` design-token block lifting ux-spec §3.5 verbatim:
     ```css
     :root {
       --bg:        #0a0a0a;
       --surface:   #1a1a1a;
       --text:      #e8e8e8;
       --text-dim:  #a0a0a0;
       --success:   #7fb069;
       --warning:   #f4a259;
       --error:     #d96c5c;
       --info:      #5ba3d0;
       --font-mono: "JetBrains Mono", Menlo, Consolas, monospace;
       --radius:    2px;
       --line-h:    1.5;
     }
     ```
  2. `@font-face` declaration loading `JetBrains Mono Regular` + `JetBrains Mono Bold` from `./jetbrains-mono-regular.woff2` + `./jetbrains-mono-bold.woff2` (vendored — no CDN). `font-display: swap` so the page text renders immediately in the fallback monospace then swaps when the WOFF2 loads.
  3. Layout: `body { background: var(--bg); color: var(--text); font-family: var(--font-mono); line-height: var(--line-h); margin: 0; padding: 16px; }` — single-column with `max-width: 1200px; margin: 0 auto`. Header bar `<header>` carries the case ID + elapsed time. Main `<main>` is a 3-section vertical stack (hypothesis stack, current tool call, findings + budget).
  4. Sections: `section { background: var(--surface); border-radius: var(--radius); padding: 16px; margin-bottom: 12px; }`. Section headings (`h2`) use `font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-dim); margin: 0 0 12px 0`.
  5. Tables: monospaced, no chrome, hover row highlight `tr:hover { background: rgba(255,255,255,0.03); }`. Column header row uses `color: var(--text-dim)`.
  6. Status pills: small inline rounded chips for finding status (STAGED, APPROVED, REJECTED, ARCHIVED), hypothesis transition (form, dispatch, confirm, pivot, abandon), critic verdict (APPROVED, CHALLENGE, REJECT). Color mapping: STAGED + form/dispatch → `--info`; APPROVED + confirm → `--success`; CHALLENGE + pivot → `--warning`; REJECTED + abandon + REJECT → `--error`.
  7. Event flash: when a new event arrives via SSE, the corresponding row gets a `.flash` class added; CSS animates background from `--warning` (subtle, 5% opacity) to transparent over 200ms (ux-spec §3.6: "No animation beyond 200ms fade-in on new events"). Keyframe `@keyframes flash-bg { from { background: rgba(244, 162, 89, 0.12); } to { background: transparent; } }`.
  8. Accessibility: `:focus-visible { outline: 2px solid var(--info); outline-offset: 2px; }`; respects `prefers-reduced-motion: reduce` by zeroing the flash keyframe.
  9. NO Tailwind classes, NO CDN imports, NO frameworks. Confirmed by the `tests/unit/test_hud_assets.py` `grep` against the rendered file.
- `src/silentwitness_hud/assets/hud.js` — NEW — ≤150 LOC vanilla JS, no bundler, no framework. Loaded by the `<script type="module" src="/assets/hud.js">` tag from story-hud-routes. Public surface:
  1. `class HUDClient` — encapsulates the SSE subscriber + DOM updaters.
  2. `constructor()` — opens `new EventSource("/events")`; binds handlers for the 4 event types via `eventSource.addEventListener("hypothesis", this.onHypothesis.bind(this))` + same for `tool_call`, `finding`, `critic`. Auto-reconnect via the browser's built-in EventSource retry (no custom logic — ux-spec §3.7 prefers simplicity).
  3. `onHypothesis(event)` — parses `JSON.parse(event.data)`; switches on `data.transition` (form|dispatch|confirm|pivot|abandon); updates the `#hypothesis-stack` table row matching `data.hypothesis_id` (creates a new row if missing); applies the appropriate status-pill class + adds `.flash` for 200ms (then removes via `setTimeout`).
  4. `onToolCall(event)` — parses event; switches on `data.phase` (`start|complete`); when `start`, updates the `#current-tool-call` block (tool name, target, audit_id, elapsed); when `complete`, clears the block.
  5. `onFinding(event)` — parses; switches on `data.status` (`STAGED|APPROVED|REJECTED|ARCHIVED`); inserts/updates the row in the `#findings-table`; applies the flash.
  6. `onCritic(event)` — parses; switches on `data.verdict` (`APPROVED|CHALLENGE|REJECT`); inserts a new row in the `#critic-log` section with the verdict pill colored appropriately; applies the flash.
  7. `safeText(s)` — `String(s).replace(/[&<>"']/g, ...)` HTML-escape helper. Every interpolation into the DOM MUST go through this — tool output is untrusted (story-hud-routes documents the same XSS guard for server-rendered HTML; this is the client-side mirror for SSE-pushed updates).
  8. Page boot: `document.addEventListener("DOMContentLoaded", () => new HUDClient())` — single instance.
- `src/silentwitness_hud/assets/jetbrains-mono-regular.woff2` — NEW (binary, vendored) — ≤50 KB; downloaded once from the official JetBrains Mono OFL-1.1-licensed release; committed verbatim. License attribution lives in `src/silentwitness_hud/assets/LICENSE-FONTS.txt`.
- `src/silentwitness_hud/assets/jetbrains-mono-bold.woff2` — NEW (binary, vendored) — ≤50 KB; same source + license as above.
- `src/silentwitness_hud/assets/LICENSE-FONTS.txt` — NEW — verbatim OFL-1.1 license text + the URL the WOFF2 files were downloaded from + the SHA256 of each file (pinned). Total ≤120 lines.
- `src/silentwitness_hud/assets/__init__.py` — NEW — empty marker; presence lets `importlib.resources` reference the assets package.
- `tests/unit/test_hud_assets.py` — NEW — ≥10 BDD scenarios via file-content grep + small JSDOM-free smoke parsing:
  - `hud.css` total LOC ≤ 200;
  - `hud.css` contains the literal `#0a0a0a` token + 4 status color tokens (`#7fb069`, `#f4a259`, `#d96c5c`, `#5ba3d0`);
  - `hud.css` does NOT contain `tailwind`, `bootstrap`, `cdnjs`, `unpkg`, `googleapis` (CDN ban per ux-spec §3.6);
  - `hud.css` contains `@font-face` with a relative URL `./jetbrains-mono` (vendored, not CDN);
  - `hud.css` respects `prefers-reduced-motion` (literal substring check);
  - `hud.js` total LOC ≤ 150;
  - `hud.js` contains `new EventSource("/events")`;
  - `hud.js` registers handlers for all 4 event types (`hypothesis`, `tool_call`, `finding`, `critic`) — verified by grep for `addEventListener("hypothesis"` + 3 siblings;
  - `hud.js` contains a `safeText` (or equivalent) HTML-escape helper used at every DOM-interpolation site (verified by counting `innerHTML =` occurrences = 0 — only `textContent =` or `safeText(...)` is allowed);
  - both vendored WOFF2 files exist + each is ≤ 100 KB + the committed SHA256 in `LICENSE-FONTS.txt` matches the file's actual SHA256.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given src/silentwitness_hud/assets/hud.css is committed
When  `wc -l src/silentwitness_hud/assets/hud.css` runs
Then  the integer is ≤ 200

Given src/silentwitness_hud/assets/hud.css is committed
When  `grep -F '#0a0a0a' src/silentwitness_hud/assets/hud.css` runs
Then  exit code is 0
And   `grep -E '#(7fb069|f4a259|d96c5c|5ba3d0)' src/silentwitness_hud/assets/hud.css | wc -l` returns ≥ 4

Given src/silentwitness_hud/assets/hud.css is committed
When  `grep -iE '(tailwind|bootstrap|cdnjs|unpkg|googleapis)' src/silentwitness_hud/assets/hud.css` runs
Then  exit code is 1 (zero hits — CDN ban per ux-spec §3.6)

Given src/silentwitness_hud/assets/hud.js is committed
When  `wc -l src/silentwitness_hud/assets/hud.js` runs
Then  the integer is ≤ 150

Given src/silentwitness_hud/assets/hud.js is committed
When  `grep -F 'new EventSource("/events")' src/silentwitness_hud/assets/hud.js` runs
Then  exit code is 0

Given src/silentwitness_hud/assets/hud.js is committed
When  `grep -cE 'addEventListener\("(hypothesis|tool_call|finding|critic)"' src/silentwitness_hud/assets/hud.js` runs
Then  the integer is ≥ 4 (one per event type)

Given src/silentwitness_hud/assets/hud.js is committed
When  `grep -cF 'innerHTML =' src/silentwitness_hud/assets/hud.js` runs
Then  the integer is 0 (XSS guard — only textContent or safeText)

Given the vendored WOFF2 files are committed
When  `sha256sum src/silentwitness_hud/assets/jetbrains-mono-regular.woff2 | awk '{print $1}'` runs
Then  the output matches the pinned hash in src/silentwitness_hud/assets/LICENSE-FONTS.txt

Given tests/unit/test_hud_assets.py exists
When  `uv run pytest tests/unit/test_hud_assets.py -v` runs
Then  exit code is 0
And   ≥10 tests pass
```

---

## Shell verification

```bash
# Tests
uv run pytest tests/unit/test_hud_assets.py -v

# Line-count caps
test "$(wc -l < src/silentwitness_hud/assets/hud.css)" -le 200
test "$(wc -l < src/silentwitness_hud/assets/hud.js)"  -le 150

# CDN ban (ux-spec §3.6)
grep -iE '(tailwind|bootstrap|cdnjs|unpkg|googleapis)' src/silentwitness_hud/assets/hud.css src/silentwitness_hud/assets/hud.js && exit 1 || true

# XSS guard
test "$(grep -cF 'innerHTML =' src/silentwitness_hud/assets/hud.js)" -eq 0

# WOFF2 size sanity (each ≤ 100 KB)
test "$(stat -c%s src/silentwitness_hud/assets/jetbrains-mono-regular.woff2 2>/dev/null || stat -f%z src/silentwitness_hud/assets/jetbrains-mono-regular.woff2)" -le 102400
test "$(stat -c%s src/silentwitness_hud/assets/jetbrains-mono-bold.woff2 2>/dev/null || stat -f%z src/silentwitness_hud/assets/jetbrains-mono-bold.woff2)" -le 102400
```

---

## Notes for coding agent

- Reference: `docs/ux-spec.md` §3.3 (visual reference + Tailwind ban) + §3.4 (4 routes the JS subscribes against) + §3.5 (design tokens — copy verbatim) + §3.6 (banned patterns — Tailwind/React/CDN); `docs/architecture.md` §3 (`src/silentwitness_hud/assets/` location); `docs/PRD.md` §6 NFR (network port 8088, no external CDN dependence in CI/firewalled env); story-hud-sse-server (the SSE stream this JS subscribes to); story-hud-routes (the HTML the CSS styles).
- **Banned patterns (ux-spec §3.6) are load-bearing:** zero Tailwind, zero React/Vue/Svelte, zero CDNs (`unpkg`, `cdnjs`, `googleapis`, `jsdelivr`). The CI gate `grep -iE '(tailwind|bootstrap|cdnjs|unpkg|googleapis)'` enforces this. A judge cloning to a firewalled SIFT VM must see the HUD render without internet — every asset is vendored.
- **JetBrains Mono is OFL-1.1 licensed** — compatible with MIT for distribution; preserve the license text + attribution in `LICENSE-FONTS.txt`. SHA256 the WOFF2 binaries at commit time and pin in the license file; the integration test verifies the pin (catches accidental swap or truncation).
- **XSS guard via `safeText` + `textContent`:** tool output (vol3 stdout, registry value strings) can contain `<script>` from malware samples. The HUD MUST never `innerHTML` user-supplied content. The grep `innerHTML = ` returning 0 enforces this. Templated structural HTML CAN use `innerHTML` if it interpolates ONLY trusted strings — but the convention here is to skip the risk entirely and use `textContent` everywhere.
- **4 event types, no more:** `hypothesis`, `tool_call`, `finding`, `critic`. If a future story adds a 5th event type, this story's CI gate will need to be updated (the `addEventListener` grep counts 4 — bump to 5 then). Document the event-type schema in the JS module's top-level docstring.
- **Auto-reconnect via browser default:** EventSource has built-in retry-with-backoff (default 3s). DO NOT implement custom reconnect logic — ux-spec §3.7 explicitly prefers stdlib over hand-rolled. The browser handles the retry; the SSE server's `: ping\n\n` heartbeat (story-hud-sse-server) keeps the connection alive through proxies.
- **`prefers-reduced-motion` (accessibility):** users with vestibular disorders MUST be able to disable the 200ms flash. The CSS media query zeroes the keyframe animation. Same line.
- **Status-pill color mapping** lifts the ux-spec §3.5 + §2.5 three-prefix rule (`✓` success, `⚠` warning, `✗` error) directly. The terminal-aesthetic continuity matters — a judge watching the demo recording with both terminal + browser open will see the same palette in both places.
- **Vendored WOFF2 sourcing:** download from the official JetBrains Mono GitHub release (`https://github.com/JetBrains/JetBrainsMono/releases`) — pick the latest stable tag. Document URL + tag + download date in `LICENSE-FONTS.txt`. Do NOT use the npm version (npm pulls in extra metadata).
- **Asset serving:** the SSE server (story-hud-sse-server) routes `/assets/*` to this directory via `importlib.resources` — that wiring lives in story-hud-routes; this story just ships the files.
- DO NOT add the HUD CSS to the rich terminal layout's surface (the rich layout has its own styling via the rich library). The CSS lives ONLY in the HUD package.
- Vocabulary discipline (PRD §14): never "court-admissible"; never "autonomous SOC"; never "Ralph Wiggum Loop". CSS comments + JS module docstrings should reference "live hypothesis stack", "tool-call envelope", "critic verdict" — same vocab as the rich live layout (ux-spec §2.3).
- Library docs to consult via Context7 BEFORE coding:
  - None — vanilla CSS + vanilla JS only; no library API surface. The MDN docs for `EventSource` are sufficient; the MDN docs for `prefers-reduced-motion` are sufficient.
- Known pitfalls:
  1. WOFF2 commit size: 2 fonts × ~30 KB = ~60 KB total binary in git. Acceptable. If either file exceeds 100 KB, subset the font to Latin-1 + ASCII via `fonttools pyftsubset` before committing.
  2. EventSource closes on tab-hidden in some browsers; the SSE server's heartbeat masks this. Do not implement custom visibility-change handling — it interacts badly with the browser's default retry.
  3. CSS specificity: avoid `!important`. The token-based palette is low-specificity; element-scoped rules suffice.
  4. JS module loading: `<script type="module">` enforces strict mode + CORS for same-origin only. The HUD binds 127.0.0.1 (story-hud-sse-server), so this is a no-op constraint; document it anyway.
  5. The 4 event types' JSON shape comes from story-investigator-hooks (the hook callbacks publish to `HUD_EVENT_BUS`). The shapes are defined in `silentwitness_common.types` — cite the discriminator field per event type in the JS module docstring so a reader knows the contract.
