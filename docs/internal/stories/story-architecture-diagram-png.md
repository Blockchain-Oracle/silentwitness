# Story — Architecture diagram (Mermaid source + PNG export via mmdc)

**ID:** story-architecture-diagram-png
**Epic:** Epic 16 — Documentation polish + submission
**Depends on:** None (sources from architecture.md §2 which is already in-repo)
**Estimate:** ~45 min
**Status:** PENDING

---

## User story

**As a** judge scanning the Devpost submission for the architecture diagram (Rules §4 deliverable 3 — must distinguish prompt-based vs architectural guardrails)
**I want to** see a single-page system diagram at `docs/diagrams/architecture.png` (rendered from the canonical Mermaid source at `docs/diagrams/architecture.mmd`) that visibly maps `silentwitness-agent → silentwitness-mcp → SIFT 2026 native tooling`, marks the six architectural boundaries with the trailing label `(architectural)`, marks the two prompt-based boundaries with `(prompt-based — supplementary, not load-bearing)`, and is regeneratable on any CI runner via `mmdc`
**So that** Rules §4 deliverable 3 is satisfied with a versioned PNG (not a hand-drawn screenshot), the README's inline Mermaid block stays byte-for-byte in sync with the diagram source, and the install path picks up the Node.js + `@mermaid-js/mermaid-cli` dependency it needs on SIFT 2026 (which ships dotnet 9 + Python but NOT Node.js per `context/.raw-design-research/03` line 207).

---

## File modification map

- `docs/diagrams/architecture.mmd` — NEW — the single source of truth for the architecture diagram. Mermaid `flowchart LR`. Lifted from `docs/architecture.md` §2 (the existing canonical block) AND extended with the explicit `(architectural)` / `(prompt-based — supplementary, not load-bearing)` trailing-tag labels on the six + two boundaries. ≤120 LOC. Encoding: UTF-8 with `LF` line endings (NOT `CRLF` — `mmdc` is sensitive on macOS). The file's last byte is a single `\n`.
- `docs/diagrams/architecture.png` — NEW — rendered output. Produced by `mmdc -i docs/diagrams/architecture.mmd -o docs/diagrams/architecture.png -t dark -b transparent -w 1600 -H 1000`. Committed binary. ≤500 KB. Regenerated on every change to `architecture.mmd` via the `just diagrams` target.
- `scripts/render_diagrams.sh` — NEW — ≤30 LOC wrapper that (a) checks `mmdc --version` exists, (b) runs the render for every `.mmd` file under `docs/diagrams/`, (c) checks the resulting PNG sizes are ≤500 KB each, (d) exits 1 with a clear advisory pointing at `install.sh --diagrams` if `mmdc` is missing.
- `install.sh` — UPDATE — add `install_mermaid_cli()` step (new function block). Provisions Node.js 20 LTS via `nvm` (per `context/.raw-design-research/03` line 207 — Node.js is NOT pre-installed on SIFT 2026), then `npm install -g @mermaid-js/mermaid-cli@^10` to install `mmdc` globally. Pinned version range documented inline. Gated behind a `--diagrams` flag (default off) so the base install path remains fast for judges who only want to run `silentwitness investigate`. Coding agent: the diagram regen is a docs-time concern, not a run-time dep — keep it optional. (~25 LOC delta to install.sh.)
- `justfile` — UPDATE — add the `diagrams` target: `diagrams:\n    ./scripts/render_diagrams.sh` (per CICD_SPEC §13.1 justfile shape). (~3 LOC delta.)
- `tests/unit/test_architecture_diagram.py` — NEW — ≥6 BDD scenarios: (a) the `.mmd` file exists and is valid UTF-8; (b) the `.mmd` parses as Mermaid (`mmdc -i docs/diagrams/architecture.mmd -o /tmp/x.png` exits 0); (c) the `.mmd` contains ≥6 occurrences of the literal string `(architectural)`; (d) the `.mmd` contains ≥2 occurrences of `(prompt-based`; (e) the `.png` file exists and is a valid PNG (first 8 bytes match `\x89PNG\r\n\x1a\n`); (f) the `.png` is ≤500 KB; (g) the canonical Mermaid block in `docs/architecture.md` §2 matches the `.mmd` source byte-for-byte (sync check — same byte-for-byte sync the README gate enforces, applied here against architecture.md).

The coding agent must NOT touch `src/` from this story.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given docs/diagrams/architecture.mmd exists
When  `file docs/diagrams/architecture.mmd` is read
Then  the output contains "UTF-8" or "ASCII"
And   the file does not contain CRLF line endings (`file ... | grep -v CRLF`)

Given `mmdc` is installed on the runner
When  `mmdc -i docs/diagrams/architecture.mmd -o /tmp/render.png -t dark -b transparent -w 1600 -H 1000` runs
Then  exit code is 0
And   /tmp/render.png exists
And   `file /tmp/render.png` reports "PNG image data"

Given docs/diagrams/architecture.mmd is read
When  `grep -c "(architectural)" docs/diagrams/architecture.mmd` runs
Then  the count is ≥6

Given docs/diagrams/architecture.mmd is read
When  `grep -c "(prompt-based" docs/diagrams/architecture.mmd` runs
Then  the count is ≥2

Given docs/diagrams/architecture.png exists in the repo
When  `wc -c docs/diagrams/architecture.png` runs
Then  the byte count is ≤512000 (≤500 KB)
And   the first 8 bytes match the PNG magic `\x89PNG\r\n\x1a\n`

Given install.sh is read
When  `grep -E "mermaid-cli|mmdc|nvm install" install.sh` runs
Then  ≥3 matches are found
And   the matches are guarded by a `--diagrams` flag block

Given the canonical Mermaid block at docs/architecture.md §2
When  it is extracted via `awk '/^```mermaid$/,/^```$/' docs/architecture.md | sed '1d;$d'`
And   compared against docs/diagrams/architecture.mmd
Then  `diff` exits 0 (byte-for-byte match)

Given mmdc is NOT installed on the runner
When  `scripts/render_diagrams.sh` runs
Then  exit code is 1
And   stderr contains "mmdc not found"
And   stderr contains "install.sh --diagrams"

Given tests/unit/test_architecture_diagram.py exists
When  `uv run pytest tests/unit/test_architecture_diagram.py -v` runs
Then  exit code is 0
And   ≥6 tests pass
```

---

## Shell verification

The coding agent runs this to confirm the story is done before opening a PR:

```bash
# Source file exists, UTF-8, LF-only
file docs/diagrams/architecture.mmd | grep -E "UTF-8|ASCII"
! file docs/diagrams/architecture.mmd | grep -q CRLF

# Boundary labels present
[ "$(grep -c '(architectural)' docs/diagrams/architecture.mmd)" -ge 6 ]
[ "$(grep -c '(prompt-based' docs/diagrams/architecture.mmd)" -ge 2 ]

# Renders cleanly
mmdc -i docs/diagrams/architecture.mmd -o /tmp/render.png -t dark -b transparent -w 1600 -H 1000

# PNG committed + valid + under size cap
file docs/diagrams/architecture.png | grep -q "PNG image data"
[ "$(wc -c < docs/diagrams/architecture.png)" -le 512000 ]

# Tests pass
uv run pytest tests/unit/test_architecture_diagram.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥6

# Architecture.md §2 canonical block matches the .mmd source
diff <(awk '/^```mermaid$/,/^```$/' docs/architecture.md | sed '1d;$d') docs/diagrams/architecture.mmd

# Install script registers mermaid-cli behind --diagrams gate
grep -E "mermaid-cli|mmdc" install.sh

# justfile target works (smoke test)
just diagrams
```

---

## Notes for coding agent

- Source of truth: architecture.md §2 (the canonical Mermaid block + the six architectural / two prompt-based boundary annotations from §2 "Trust boundaries"); PRD §2 0:30–1:00 (the architectural-vs-prompt-based split is the load-bearing distinction the Devpost rules require), PRD §10 deliverable 3 (`docs/diagrams/architecture.svg` is the original target; we use `.png` instead because Devpost's gallery preview renders PNGs natively without SVG sandboxing — see PRD §10 footnote-style choice); `context/.raw-design-research/03` line 207 (Node.js is NOT pre-installed on SIFT 2026 — flagged for `install.sh`); CICD_SPEC §13.1 (`justfile` shape — add the `diagrams` target alongside `ci`, `lint`, `test`).
- The Mermaid source already exists in `architecture.md` §2 (lines 66–173 at time of writing). This story's job is to (a) lift it into a standalone `.mmd` file so `mmdc` can render it; (b) **augment** it with the explicit `(architectural)` and `(prompt-based — supplementary, not load-bearing)` trailing-tag labels on the relevant node descriptions; (c) keep the architecture.md §2 block byte-for-byte in sync (the existing block in architecture.md must be edited in the SAME commit to add the trailing tags — coding agent does both edits, both go in one commit).
- Label injection. Look up each boundary in architecture.md §2's component block and append the tag inline. Examples (don't paste these — derive from the actual block):
  - `mcp_artifact["silentwitness-mcp (FastMCP server — THE PRODUCT) (architectural)"]`
  - `cit_gate["verification/citation_gate.py (architectural)"]`
  - `ent_gate["verification/entity_gate.py (architectural)"]`
  - `sanit["verification/sanitizer.py (architectural)"]`
  - `hmac_led["audit/ledger.py (architectural)"]`
  - `mount_v["evidence/mount.py — ro,noexec,nosuid (architectural)"]`
  - `cc_md["CLAUDE.md — senior-analyst frame (prompt-based — supplementary, not load-bearing)"]`
  - `(advisory tool-call hints in system prompt) (prompt-based — supplementary, not load-bearing)` — added as a separate node if not already present.
- The six architectural boundaries to label (per PRD §2 0:30–1:00):
  1. Typed MCP tool surface (`mcp_artifact` subgraph wrapper).
  2. bwrap kernel sandbox (add explicit node `bwrap_sandbox["bwrap kernel namespaces (architectural)"]`).
  3. ro,noexec,nosuid evidence mount (`mount_v` + `evidence_volume` subgraph wrapper).
  4. Citation gate (`cit_gate`).
  5. Entity gate (`ent_gate`).
  6. HMAC-signed approval ledger (`hmac_led` + `ledger_volume` subgraph wrapper).
- The two prompt-based boundaries to label:
  1. System-prompt senior-analyst frame (`cc_md` — Claude Code CLAUDE.md / agent system prompt).
  2. Tool-call advisories (add explicit node `advisories["tool-call advisories injected by MCP (prompt-based — supplementary, not load-bearing)"]`).
- mmdc invocation specifics. The canonical render command is:
  ```
  mmdc -i docs/diagrams/architecture.mmd -o docs/diagrams/architecture.png -t dark -b transparent -w 1600 -H 1000
  ```
  - `-t dark` matches GitHub's dark-mode rendering (most judges read on GitHub dark).
  - `-b transparent` so the PNG composites cleanly into the README and PDF.
  - `-w 1600 -H 1000` keeps the PNG ≤500 KB for typical diagram complexity. If the rendered PNG exceeds 500 KB, reduce to `-w 1280 -H 800` and document in the commit body.
- `install.sh --diagrams` flag. Per architecture.md repo structure, `install.sh` is the single-binary installer. This story adds an OPTIONAL `--diagrams` flag that bootstraps Node.js 20 via `nvm` and installs `@mermaid-js/mermaid-cli` globally. Default install (no flag) does NOT install Node.js — judges who only want to run the agent get a fast install. Contributors who want to regenerate diagrams run `install.sh --diagrams` once. The `nvm` install URL is pinned to the v0.40.x release tag (current as of 2026-06); audit-trail the version in a comment.
- Architecture.md sync. The block at architecture.md §2 (currently lines ~66–173) and `docs/diagrams/architecture.mmd` are two copies of the same content. The CI gate in story-readme-polish enforces sync between README.md's inline block and `architecture.mmd`. THIS story's test enforces sync between architecture.md §2 and `architecture.mmd`. Result: three locations, one source-of-truth content, two CI sync checks. When the diagram changes: edit `architecture.mmd`, regen the PNG, copy into architecture.md §2 + README.md, commit all four files together.
- Context7 hints BEFORE coding:
  - `mermaid` topic "flowchart LR subgraph classDef" — Mermaid syntax for subgraph-grouped flowcharts with custom class styling (matches the dotted-stroke boundary classes in the existing block).
  - `mermaid-cli` topic "mmdc theme background width height" — flag reference for the CLI; confirm `-t dark` and `-b transparent` flag spellings.
- Known pitfalls:
  1. macOS line-endings drift. The `.mmd` file MUST be LF-only. If a contributor edits on Windows or with a misconfigured editor, the byte-for-byte sync check fails silently. The test asserts `file ... | grep -v CRLF`.
  2. Mermaid version drift. `@mermaid-js/mermaid-cli@^10` aligns with Mermaid 10.x syntax (used by the existing `architecture.md` block). Newer Mermaid 11.x changed some classDef semantics — if you must upgrade, regenerate the PNG and re-verify the layout.
  3. The PNG is committed as binary. Pre-commit `check-added-large-files` is set to 1MB (CICD_SPEC §15.1). 500 KB is well under that. If a render exceeds, see the `-w`/`-H` reduction above.
  4. `mmdc` requires Chromium for the headless render. The `@mermaid-js/mermaid-cli` package bundles Puppeteer which auto-installs Chromium on `npm install`. CI runners (Ubuntu 24.04 GitHub-hosted) need `libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2` available — already present in the GitHub-hosted runners as of 2026-06. Document the requirement in `install.sh --diagrams` for SIFT VM users.
  5. The Mermaid label syntax: parens inside node descriptions need to be inside the quoted node-label string. `node["foo (architectural)"]` works; `node[foo (architectural)]` does NOT parse. Test enforces.
- Vocabulary discipline (PRD §14): the architectural-vs-prompt-based phrasing IS the vocabulary discipline applied to the diagram. No "court-admissible" anywhere in the labels; no "autonomous SOC"; no "Ralph Wiggum" — describe the behavior (`closed-loop critic`, `hypothesis pivot`).
