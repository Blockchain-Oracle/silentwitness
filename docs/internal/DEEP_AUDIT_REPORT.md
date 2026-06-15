# Deep Audit Report — SilentWitness Spec Set

**Audit date:** 2026-06-03
**Auditor:** Wave A + Wave B (6 source-code verification agents) + Wave C synthesis
**Scope:** External validation against actual library source code, GitHub issues, current docs, dataset URLs
**Verdict:** **PASS WITH PATCH SERIES** — wedge + architecture survive scrutiny; 21 tactical patches needed before orchestrator fires

---

## §0 — Executive summary

Six source-code-level verification agents audited the SilentWitness spec set against the actual current state of every dependency: Pydantic AI, MCP/FastMCP, Volatility 3 (per plugin), Eric Zimmerman tools, Python lib stack, SIFT 2026 install, and dataset URLs. They cloned source, read implementations, checked open GitHub issues, verified release SHA256s, and HEAD-confirmed every dataset URL.

**Findings:**
- **21 BLOCKERs** — tactical issues (wrong kwarg names, wrong DLL paths, missing CVE-closing version pins) that would have killed the build at coding-agent merge time. None invalidate the wedge or the architectural pattern.
- **18 FIX-ITs** — corrections that should land before submission but wouldn't break the build.
- **0 strategic failures** — the wedge (hypothesis-first investigator + report-as-state + verifiability gates + harness vs vanilla Protocol SIFT) is sound. The pattern (Custom MCP Server + Pydantic AI agent loop + Markdown report) survived external validation.

**Estimated patch time:** 6-10 hours focused editing, or 2-3 hours wall-clock with 3-4 parallel patch agents. After patches → small re-audit (Wave 5 internal) → orchestrator fires safely.

**Most urgent finding:** `windows.malfind.Malfind` is a deprecation stub that expires **2026-06-07 (Friday — 4 days)**. If SIFT pulls Vol3 ≥2.29.0 after that date, every `vol_malfind` call dies. Plugin path must be updated to `windows.malware.malfind.Malfind` in story-vol-malfind + architecture.md §5.

---

## §1 — Severity classification

### BLOCKER (must fix before any coding agent runs)

21 items, ordered by source.

#### Pydantic AI (4 BLOCKERs)
- **B-PYAI-1:** `Agent(hooks=[...])` is not a real kwarg. Actual: `Agent(capabilities=[hooks])`. Constructor will reject our spec.
- **B-PYAI-2:** Hook names `on_step` / `on_finish` don't exist. Map to `@hooks.on.after_model_request` (per-LLM-call delta — token accounting) and `@hooks.on.after_run` (final snapshot — report-as-state save). story-investigator-hooks BDD won't pass as written.
- **B-PYAI-3:** `MCPServerStdio(..., tool_filter=...)` doesn't exist. All 4 specialist stories rely on this. Replace with `MCPServerStdio(...).filtered(lambda ctx, td: td.name in ALLOWLIST)`. Real primitive: `pydantic_ai.FilteredToolset`.
- **B-PYAI-4:** `Agent(max_iterations=N)` constructor kwarg doesn't exist. Map `SILENTWITNESS_MAX_ITERS=50` to `UsageLimits(request_limit=50)` passed at `agent.run(..., usage_limits=...)` time. Catch `UsageLimitExceeded`.

#### MCP / FastMCP (2 BLOCKERs)
- **B-MCP-1:** `mcp>=1.0` pin admits two unpatched CVEs: CVE-2025-66416 (DNS-rebinding default-off until 1.23.0) + CVE-2025-53366 (DoS, fixed 1.9.4). Our "127.0.0.1-only is enough" defense collapses on pre-1.23 install. **Fix:** pin `mcp>=1.23.0,<2.0` everywhere.
- **B-MCP-2:** story-fastmcp-server-bootstrap.md:130 claims FastMCP returns `code=-32000` with structured reason in `error.data`. **Source-read disproves this:** `lowlevel/server.py:467-474` shows exceptions become `CallToolResult(isError=True, content=[TextContent(text=msg)])`. JSON-RPC layer returns SUCCESS. The `isError=true` + `ToolResponse(success=False)` envelope inside `structuredContent` is correct — just stop claiming `-32000`.

#### Volatility 3 (3 BLOCKERs)
- **B-VOL-1:** `windows.malfind.Malfind` is a deprecation stub at `framework/plugins/windows/malfind.py:11-20` with `removal_date="2026-06-07"` (4 DAYS). Real path: `windows.malware.malfind.Malfind`. Same pattern: `windows.lsadump.Lsadump` (removal 2026-09-25) → `windows.registry.lsadump.Lsadump`. story-vol-malfind + story-vol-lsadump + architecture.md §5 must update plugin strings.
- **B-VOL-2:** story-vol-pstree-psscan schema has 3 errors:
  - `tree_depth: int` column doesn't exist in Vol3 output. Tree shape is via `JsonRenderer.__children` nesting; depth must be computed server-side.
  - MISSING 3 actual columns: `Audit`, `Cmd` (full pre-process command line — HIGH SIGNAL we'd drop), `Path`.
  - `offset_p: int` wrong — Vol3 emits single `Offset(V)` by default; only `Offset(P)` if `--physical` flag.
- **B-VOL-3:** story-vol-lsadump schema wrong + SIFT 2026 pins NO Vol3 version + 2.28.0 regression live:
  - Spec claims `name, hex_value, printable_value`. Actual columns: `Key, Secret, Hex`.
  - SIFT saltstack: `pip.installed: name: volatility3; upgrade: True` — NO version pin, pulls latest.
  - Open issue #1985: 2.28.0 layer-detection regression on large memory dumps. SIFT inherits until 2.28.2.
  - **Fix:** pin to `volatility3==2.27.0` in SilentWitness's own venv at `/opt/silentwitness/vol3-venv/bin/vol`. Do NOT modify SIFT-managed `/opt/volatility3/`. Pre-fetch Windows ISF bundle from `downloads.volatilityfoundation.org/volatility3/symbols/windows.zip` into `~/.cache/volatility3/` at init.

#### EZ Tools (9 BLOCKERs)
- **B-EZ-1:** **DLL paths are FLAT for 11 of 15 tools, not nested.** Spec's `/opt/zimmermantools/<Tool>/<Tool>.dll` is wrong for MFTECmd, AmcacheParser, AppCompatCacheParser, SBECmd, PECmd, SrumECmd, JLECmd, LECmd, RBCmd. Real: `/opt/zimmermantools/<Tool>.dll` (flat). Nested confirmed only for RECmd, SQLECmd, iisGeolocate, **EvtxECmd** (our flagged inner-directory quirk IS correct).
- **B-EZ-2:** MFTECmd schema errors:
  - `SiFnDelta` is INVENTED. Real columns: `Timestomped: bool` + `uSecZeros: bool`. Wrapper either renames or documents as derived alias.
  - `RecordNumber` doesn't exist — actual: `EntryNumber` + `SequenceNumber`.
  - `IsDeleted` doesn't exist — derived from `InUse=False`.
- **B-EZ-3:** EvtxECmd schema errors (story-parse-evtx):
  - `UserSid` → `UserId`
  - `RenderedDescription` → `MapDescription`
  - `EventRecordID: int` → `EventRecordId: str`
  - `EventData: dict` doesn't exist as a dict — only `Payload: str` (XML) or `PayloadData1..6` map-populated columns.
- **B-EZ-4:** EvtxECmd has NO channel-name filter. story-parse-evtx BDD line 75 is wrong (`--inc` filters by EID list, not channel). Wrapper must translate `channel="Security"` to canonical Security-channel EID list (4624, 4625, 4648, 4672, 4688, 4697, 4698, 4720, 4732, 4768, 4769, 4776, 5140, 5145, 5156, 1102, etc.).
- **B-EZ-5:** PECmd schema errors:
  - `LastRunTime` → `LastRun`
  - `DirectoriesLoaded` → `Directories`
  - Volumes HARDCODED max-2 (`Volume0/1Name/Serial/Created`) with `Note` field flagging `>2 volumes` — not an arbitrary list.
- **B-EZ-6:** AmcacheParser emits MULTIPLE CSVs, not one. Wrapper must glob `_UnassociatedFileEntries.csv` specifically:
  - `FileSize` → `Size`
  - `KeyLastWriteTimestamp` → `FileKeyLastWriteTimestamp` (in FileEntry table — different from ProgramEntries)
- **B-EZ-7:** AppCompatCacheParser schema renames:
  - `Position` → `CacheEntryPosition`
  - `FullPath` → `Path`
  - `LastModifiedUTC` → `LastModifiedTimeUTC`
  - `Executed: bool` → `Executed: Literal["Yes","No","NA"]`
  - DROP `FileSize` (doesn't exist in shimcache)
- **B-EZ-8:** **Exit code is UNRELIABLE** for 5 tools. EvtxECmd, PECmd, SBECmd, AmcacheParser, AppCompatCacheParser all call `Environment.Exit(0)` even on errors (7+ paths each verified in source). Wrapper MUST parse stderr for Serilog `[ERR]`/`[FTL]` markers — exit code alone misses failures. MFTECmd is the only exception (uses `Environment.Exit(-1)`).
- **B-EZ-9:** PECmd + SrumECmd are NOT pre-installed on SIFT 2026 (confirmed missing from saltstack tool array). `install.sh` adds via dotnet wrapper with FLAT install path.

#### Python libs (3 BLOCKERs)
- **B-PY-1:** mistune `>=3` floor admits SIX 2026 CVEs in 3.0.x-3.2.0: CVE-2026-44708 (XSS math plugin), 44896 (figure directive), 44897 (heading-ID injection), 44899 (CSS injection), 33441 (DoS), 33079 (ReDoS). All patched in 3.2.1. **Fix:** pin `mistune>=3.2.1`.
- **B-PY-2:** uv 0.5.11 is 17 minor versions stale vs current 0.11.18, with breaking semantics changes: `uv venv --clear` now required, multiple `default=true` indexes now error, lockfile `exclude-newer` semantics changed. **Fix:** pin `uv==0.11.18`.
- **B-PY-3:** regipy + python-evtx are READ-ONLY → story-case-trapdoor-synthesis can't write registry hives or EVTX files. 3 of 5 `synth_*` helpers can't ship as written. Since Epic 15 is OPTIONAL (PRD §9 "time-permitting"), recommended **CUT from v1** or rewrite to template-fixture pattern (check in clean NTUSER.DAT, patch by byte offset).

### FIX-IT (must fix before submission)

18 items.

#### MCP / FastMCP (1)
- **F-MCP-1:** story-fastmcp-server-bootstrap.md:122 treats `$SILENTWITNESS_GATEWAY_TOKEN` like a config flag. Reality: `AuthSettings` is OAuth-shaped. For static-bearer: custom `TokenVerifier` Protocol impl (~30 LOC at `src/silentwitness_mcp/_auth.py`). Story needs file modification map addition + BDD scenario for missing-token rejection.

#### Pydantic AI partial fixes (4)
- **F-PYAI-1:** `mcp_servers=` kwarg DEPRECATED → use `toolsets=[server]`.
- **F-PYAI-2:** `MCPServerHTTP` wrong → use `MCPServerStreamableHTTP`.
- **F-PYAI-3:** `agent.set_mcp_sampling_model()` doesn't exist → pass `sampling_model=` at `MCPServerStdio` construction.
- **F-PYAI-4:** `vllm:` is NOT a model-string prefix → route through `OpenAIChatModel(base_url=...)`. Also: `claude-sonnet-4-7` NOT in `KnownModelName` (max 4-6 currently). `openai:` emits PydanticAIDeprecationWarning in v1.105 → use `openai-chat:gpt-5`.

#### Python libs (5)
- **F-PY-1:** WeasyPrint `>=60,<62` ships known CVE-2025-68616. Bump to `>=68.1,<70.0`.
- **F-PY-2:** rich v15.0 explicitly fixed nested Live (our HUD pattern). Pin `>=14.1,<16`.
- **F-PY-3:** Dockerfile apt list missing `libharfbuzz-subset0`, `libpangoft2-1.0-0`, font packages.
- **F-PY-4:** Base image `python:3.12-slim` floating tag will flip to trixie/forky mid-hackathon. Pin `python:3.12-slim-bookworm`.
- **F-PY-5:** structlog can be DROPPED entirely — spec itself notes direct `model_dump_json` is right for our scope.

#### SIFT install + datasets (8)
- **F-DS-1:** NIST Hacking Case manifest says multi-part DD. Reality: single reassembled E01 at `images/4Dell%20Latitude%20CPi.E01`.
- **F-DS-2:** NIST PC E01 size: 2.0 GB not 20 GB (10× correction in spec).
- **F-DS-3:** Nitroba size: 56,180,821 bytes exact, not "~60 MB".
- **F-DS-4:** intrinsicode.net unreachable live → use Wayback Machine snapshot URL.
- **F-DS-5:** Pre-commit the answer-key SHA256: `218165427fcb2f490b44eccf7fbc9bf3700b938ea976004051a067e79e0da62b`.
- **F-DS-6:** install.sh must add WeasyPrint native deps (Pango/HarfBuzz/GdkPixbuf — only Cairo + libffi-dev ship in SIFT 2026).
- **F-DS-7:** Velociraptor pin v0.76.2 (not abstract "latest").
- **F-DS-8:** Add `story-third-party-notices` for license attribution NOTICES file.

### NOTE (informational)
- **N-1:** spaCy + `en_core_web_lg` confirmed KEEP — pure regex can't catch hallucinated PERSON/ORG/GPE entities ("Lazarus Group") which are the highest-value class for the architectural floor. ADR-006 stands. Pin `spacy>=3.8.10,<3.9` + `en_core_web_lg==3.8.0`.
- **N-2:** EvtxECmd `--csv` + `--json` flags coexist (both outputs written simultaneously).
- **N-3:** dotnet 9 SDK is the right runtime (net6 EOL'd for 2026 EZ builds).
- **N-4:** SilentWitness can stay MIT — all subprocess-invoked GPL/AGPL tools (Hayabusa/Chainsaw GPL-3.0, Velociraptor AGPL-3.0, Suricata GPL-2.0) don't trigger conveyance.
- **N-5:** EvtxECmd inner-directory quirk (`/opt/zimmermantools/EvtxeCmd/EvtxECmd.dll`) verified real — only nested EZ tool we got right.
- **N-6:** agent-delegation pattern in Pydantic AI is validated — specialist + critic stories use it correctly (`await delegate_agent.run(prompt, usage=ctx.usage, deps=delegate_deps)`).

---

## §2 — Time-critical BLOCKERs (external deadlines / CVE exposure)

In order of urgency:

1. **B-VOL-1 (windows.malfind deprecation expires 2026-06-07 — Friday, 4 days).** Must fix story-vol-malfind plugin string OR pin Vol3 ≤2.28.x.
2. **B-MCP-1 (mcp >=1.0 admits CVE-2025-66416 + CVE-2025-53366).** Must pin `mcp>=1.23.0,<2.0` before any MCP server boots.
3. **B-PY-1 (mistune >=3 admits 6 CVEs).** Must pin `mistune>=3.2.1` before any report renders.
4. **F-PY-1 (WeasyPrint >=60,<62 ships CVE-2025-68616).** Bump to `>=68.1,<70.0` before any PDF renders.

All four close on dep-pin patches in `architecture.md §2`, `BRAINSTORM.md §3.5`, `CICD_SPEC.md §11`, and the `pyproject.toml` block (when written in story-scaffold-uv-pyproject).

---

## §3 — Patch series (concrete, file-grouped, paste-ready)

### 3.1 BRAINSTORM.md
Update §3.5 dep stack:
- `mcp>=1.0` → `mcp>=1.23.0,<2.0`
- `mistune>=3` → `mistune>=3.2.1`
- `weasyprint>=60,<62` → `weasyprint>=68.1,<70.0`
- `uv>=0.5` → `uv==0.11.18`
- `pydantic-ai>=0.1` → `pydantic-ai[anthropic,openai,google,ollama,mcp,fastmcp]>=1.105.0,<2.0.0`
- Add `rich>=14.1,<16`
- Add `spacy>=3.8.10,<3.9` (was implicit)
- **DROP** `structlog` (use Pydantic `model_dump_json` directly)
- Add `volatility3==2.27.0` (own venv strategy)

### 3.2 architecture.md
Update §2 stack to mirror BRAINSTORM. Update §5 tool catalog plugin strings:
- `windows.pslist.PsList` (unchanged — verify)
- `windows.malfind.Malfind` → **`windows.malware.malfind.Malfind`**
- `windows.lsadump.Lsadump` → **`windows.registry.lsadump.Lsadump`**

Update §5.2 response envelope — keep as-is (validated).

Update §5.4 citation-gate — note that `Vol3 --renderer json` confirmed reliable on 2.27.0 for all 9 plugins.

Update §6 agent layer:
- `Agent(hooks=[...])` → `Agent(capabilities=[hooks])`
- Hook names: `on_step` → `after_model_request`; `on_finish` → `after_run`
- `mcp_servers=` → `toolsets=[server]`
- `MCPServerHTTP` → `MCPServerStreamableHTTP`
- `tool_filter=` → `.filtered(lambda ctx, td: td.name in ALLOWLIST)`
- `max_iterations=N` → `usage_limits=UsageLimits(request_limit=N)` at `.run()` time

Update §10 threat model — adjust the MCPwn mitigation paragraph to note CVE-2025-66416 closes at mcp 1.23.0 (was implicit in our defense).

### 3.3 CICD_SPEC.md
Update §11 (Docker) + §13 (justfile) dep-block:
- Same pins as §3.1
- Add Dockerfile apt: `libharfbuzz-subset0 libpangoft2-1.0-0 fonts-dejavu fonts-liberation`
- Base image: `python:3.12-slim` → `python:3.12-slim-bookworm`
- Update SBOM gate to include the new pin floors

### 3.4 PRD.md
No changes (audit found no PRD-level issues).

### 3.5 ux-spec.md
No changes (audit found no ux-spec issues).

### 3.6 epics.md
- **Decision required:** Epic 15 (case-trapdoor) — CUT or rewrite to template-fixture? See §4.
- Add Epic 16 story: `story-third-party-notices` (license NOTICES file).

### 3.7 sprint-status.yaml
- If Epic 15 cut: remove `story-case-trapdoor-synthesis` + `story-case-trapdoor-ground-truth`. If rewritten: leave but flag scope change.
- Add `story-third-party-notices` to Epic 16.

### 3.8 Story patches (24 stories impacted)

#### Epic 1 — scaffolding
- **story-scaffold-uv-pyproject.md:** update pyproject template — apply all dep pins from §3.1. Pin uv to 0.11.18.
- **story-docker-baseline.md:** base image → `python:3.12-slim-bookworm`. Add apt-installed `libharfbuzz-subset0 libpangoft2-1.0-0 fonts-dejavu fonts-liberation`.

#### Epic 4 — MCP server skeleton
- **story-fastmcp-server-bootstrap.md:**
  - Line 130: remove `-32000` claim, replace with "exceptions become `CallToolResult(isError=True, content=[TextContent(text=msg)])`; the `success=False` envelope inside `structuredContent` is correct."
  - Line 122: add detail on bearer auth — note `AuthSettings` is OAuth-shaped; implement custom `TokenVerifier` Protocol at `src/silentwitness_mcp/_auth.py`. Add file to modification map + BDD scenario for missing-token rejection.
  - Update mcp pin reference to `>=1.23.0,<2.0`.

#### Epic 5 — Memory tools
- **All 7 vol-* stories:** Add note pointing at SilentWitness's own venv at `/opt/silentwitness/vol3-venv/bin/vol`. Pin `volatility3==2.27.0`. Pre-fetch ISF bundle.
- **story-vol-malfind.md:** plugin string `windows.malfind.Malfind` → `windows.malware.malfind.Malfind`.
- **story-vol-pstree-psscan.md:** schema corrections — remove `tree_depth: int` (compute server-side from `__children` nesting); add `Audit`, `Cmd`, `Path` columns; change `offset_p: int` → `offset_v: int` (default mode) + note `--physical` flag swap.
- **story-vol-lsadump.md:** plugin string → `windows.registry.lsadump.Lsadump`. Schema: `name` → `Key`, `hex_value` → `Hex`, `printable_value` → `Secret`.

#### Epic 6 — Disk + Registry tools
- **story-parse-mft.md:** DLL path FLAT (`/opt/zimmermantools/MFTECmd.dll`). Schema corrections: `SiFnDelta` → rename to derived alias of `Timestomped: bool` + `uSecZeros: bool` (compute via wrapper); `RecordNumber` → `EntryNumber` + `SequenceNumber`; `IsDeleted` → derive from `InUse=False`.
- **story-parse-amcache-shimcache.md:** DLL paths FLAT. AmcacheParser: glob `*_UnassociatedFileEntries.csv` (multi-CSV emission); `FileSize` → `Size`; `KeyLastWriteTimestamp` → `FileKeyLastWriteTimestamp`. AppCompatCacheParser: `Position` → `CacheEntryPosition`; `FullPath` → `Path`; `LastModifiedUTC` → `LastModifiedTimeUTC`; `Executed: bool` → `Executed: Literal["Yes","No","NA"]`; drop `FileSize`.
- **story-parse-prefetch.md:** DLL path FLAT (PECmd is NOT pre-installed — install.sh adds). Schema: `LastRunTime` → `LastRun`; `DirectoriesLoaded` → `Directories`; volumes are hardcoded max-2 with `Note` flag for >2.
- **story-parse-shellbags.md:** DLL path FLAT.
- **story-regripper.md:** No changes (regripper not affected by EZ Tools audit).

#### Epic 7 — Log + Network tools
- **story-parse-evtx.md:** Schema corrections: `UserSid` → `UserId`; `RenderedDescription` → `MapDescription`; `EventRecordID: int` → `EventRecordId: str`; `EventData: dict` → surface `Payload: str` (XML) + `PayloadData1..6` map columns directly. Channel filter: translate `channel="Security"` → canonical EID list (not `--inc` by name).
- **story-hayabusa-timeline.md:** Pin Hayabusa v3.9.0 with verified SHA256.
- **story-chainsaw-hunt.md:** Pin Chainsaw v2.16.0 with verified SHA256.
- **story-zeek-run.md:** Document Ubuntu 24.04 install pattern (OpenSUSE repo or apt).
- **story-suricata-run.md:** apt install pattern.

#### Epic 8 — Hypothesis + investigator
- **story-investigator-agent.md:**
  - `Agent(hooks=[...])` → `Agent(capabilities=[hooks])`
  - `max_iterations=50` → `agent.run(..., usage_limits=UsageLimits(request_limit=50))`; catch `UsageLimitExceeded`
  - Default model `anthropic:claude-opus-4-7` confirmed validated
  - `vllm:` provider: route through `OpenAIChatModel(base_url=...)` (note as advisory; not BDD critical)
  - Optional: switch to `openai-chat:gpt-5` if openai deprecation warning matters
- **story-investigator-hooks.md:** Hook names: `on_step` → `@hooks.on.after_model_request` (token accounting); `on_finish` → `@hooks.on.after_run` (report save). Rewrite BDD scenarios using these.

#### Epic 9 — Specialists
- **story-memory-specialist.md, story-disk-specialist.md, story-network-specialist.md, story-log-specialist.md:** `MCPServerStdio(..., tool_filter=...)` → `MCPServerStdio(...).filtered(lambda ctx, td: td.name in ALLOWLIST)`. Import `pydantic_ai.FilteredToolset` if explicit.

#### Epic 10 — Critic
- **story-critic-agent.md:** Same agent-delegation pattern is validated. Confirm `usage=ctx.usage` propagation for token-rollup. `mcp_servers=` deprecated → `toolsets=[...]` if used.

#### Epic 11 — Report
- **story-report-template.md:** Pin mistune `>=3.2.1` reference.
- **story-report-pdf-export.md:** Pin WeasyPrint `>=68.1,<70.0`. Update Dockerfile native dep list reference (libharfbuzz-subset0, libpangoft2-1.0-0, font packages). Test against bookworm-pinned base image.

#### Epic 14 — Accuracy harness
- **story-dataset-manifests.md:** Hacking Case = single reassembled E01 at `images/4Dell%20Latitude%20CPi.E01` (not multi-part DD). NIST PC E01 size 2.0 GB (not 20). Nitroba exact 56,180,821 bytes.
- **story-ground-truth-parsers.md:** intrinsicode.net URLs swap to Wayback Machine. Pre-commit answer-key SHA256.

#### Epic 15 — case-trapdoor (OPTIONAL — decision required)
- **story-case-trapdoor-synthesis.md:** Either CUT or rewrite to template-fixture pattern. See §4.
- **story-case-trapdoor-ground-truth.md:** Depends on above outcome.

#### Epic 16 — Documentation + submission
- **Add story-third-party-notices.md:** new story for license NOTICES file aggregating Hayabusa/Chainsaw/Velociraptor/Suricata/Vol3/etc. licenses.
- Update story-devpost-submission pre-commit checklist to include NOTICES file presence.

---

## §4 — Architecture-level decisions to reconfirm

### Decision A: Drop structlog?
Audit Doc 05 §15 found the spec itself notes direct `pydantic.model_dump_json()` is right for our scope. structlog adds dependency weight + minimal value at our write rate. **Recommendation: DROP.** Update affected stories (story-audit-logger, story-investigator-hooks, story-critic-verdict-handling, story-report-writer) to use `model_dump_json()` directly.

### Decision B: Cut Epic 15 (case-trapdoor)?
B-PY-3: synthesis libs (regipy, python-evtx) are read-only. Three of five `synth_*` helpers can't ship as written.

**Option B1 — CUT (recommended):**
- Pros: -0.5 day scope removed; harness still works on Nitroba + NIST cases (the 3 mandatory Tier-1 datasets with public answer keys)
- Cons: lose the "adversary-pair" demo asset for the hackathon video
- Impact on demo: minor — the headline metric is time-to-handoff-ready report on NIST Hacking Case, not the trapdoor case

**Option B2 — Rewrite to template-fixture pattern:**
- Check in clean NTUSER.DAT / Security.evtx / dropper.exe fixtures
- Patch by byte offset (timestomp = patch 8 bytes at MFT record offset; log clear = patch first 4 bytes of EVTX header; etc.)
- Pros: keep the adversary-pair demo
- Cons: +1 day scope; fragile to fixture re-baselining

**Recommendation:** CUT for v1 submission. Add Epic 15 to "future work" in PRD §10. If time permits post-submission, ship as a follow-on demo asset.

### Decision C: SilentWitness's own Vol3 venv?
B-VOL-3 recommends `/opt/silentwitness/vol3-venv/bin/vol` to avoid SIFT-managed Vol3 drift.

**Recommendation:** YES. Pin `volatility3==2.27.0`. Document the venv strategy in architecture.md §8 deployment topology + story-scaffold-uv-pyproject Notes. install.sh creates the venv early in setup, pre-fetches Windows ISF.

### Decision D: Bearer token implementation
F-MCP-1: `AuthSettings` is OAuth-shaped — we need a custom `TokenVerifier` Protocol.

**Recommendation:** Add `src/silentwitness_mcp/_auth.py` (~30 LOC) to story-fastmcp-server-bootstrap. BDD scenario: "Given missing/wrong bearer token, When Streamable HTTP request hits :4508, Then 401 returned + audit log entry for AUTH_REJECTED."

---

## §5 — Execution plan

### Phase 1: High-velocity CVE pin patches (~1 hour)
Apply BRAINSTORM.md §3.5 + architecture.md §2 + CICD_SPEC.md §11 dep pins. Single file pass.

### Phase 2: Architecture.md surgical patches (~1 hour)
- §5 plugin name corrections (3 lines)
- §6 agent layer kwarg names + hook event names + tool_filter pattern + max_iterations pattern (8-10 lines)
- §8 deployment — add SilentWitness Vol3 venv strategy
- §10 threat model — CVE-2025-66416 mitigation note

### Phase 3: Story patches (~3-4 hours OR 1-2h parallel)
24 stories impacted. Group by epic for batch editing or per-cluster parallel dispatch.

Options:
- **(a) Sequential manual:** I edit each story one at a time. ~3-4 hours focused.
- **(b) Parallel patch agents:** dispatch 4 agents per cluster (Epic 5 vol-*, Epic 6 disk/reg, Epic 7 log/net, Epic 8-10 agent layer). ~1-2 hours wall-clock. Risk: rate-limit if too many concurrent.
- **(c) Hybrid:** I do the high-touch surgical patches (story-investigator-agent + story-investigator-hooks + story-fastmcp-server-bootstrap), dispatch 3 patch agents for the bulk tool-wrapper stories.

**Recommendation:** Option (c). Surgical for the agent-layer + MCP-bootstrap (precision matters), bulk-parallel for the tool wrappers (template-driven edits).

### Phase 4: Sprint-status.yaml + epics.md scope adjustments (~30 min)
- Add story-third-party-notices to Epic 16
- Decision on Epic 15 (cut vs rewrite)

### Phase 5: Re-audit (~30 min)
Quick internal-consistency re-run (the original Wave 5 / `AUDIT_REPORT.md` style) to confirm patches landed without contradictions.

### Phase 6: Then orchestrator fires
Build phase begins safely.

**Total estimated patch time:** ~6-7 hours focused / ~2-3 hours wall-clock with parallel dispatch.

---

## §6 — Confidence in architecture (the wedge)

After external validation:

| Layer | Pre-audit confidence | Post-audit confidence |
|---|---|---|
| Wedge (hypothesis-first IR investigator + report-as-state + verifiability gates) | HIGH | UNCHANGED HIGH |
| Pattern (Custom MCP Server + Pydantic AI agent loop + Markdown report + harness) | HIGH | UNCHANGED HIGH |
| Critical primitives (model-agnostic, MCP-native, structural-not-prompt) | HIGH | VALIDATED with caveats |
| Tactical implementation details (kwarg names, DLL paths, schema columns, version pins) | MEDIUM | LOW until patches applied — then HIGH |
| External dep stability (Vol3 plugin paths, EZ Tools schemas, mcp CVE state) | MEDIUM | LOW until patches applied — then HIGH |

**The audit did not invalidate any architectural choice.** It surfaced 21 tactical issues that would have killed the build at coding-agent merge time. The validated primitives (agent-delegation, MCP transports, verification gate algorithm) all hold up under source-code scrutiny.

---

## §7 — What the audit caught vs what the previous audit missed

The earlier `AUDIT_REPORT.md` (Wave 5 — internal consistency) passed because it had no source-read of the SDKs. It checked that BRAINSTORM ↔ architecture ↔ stories agreed with each other. It could not catch:
- `Agent(hooks=[...])` not matching the actual constructor surface
- Vol3 plugin names being deprecated at the framework level
- EZ Tools CSV column names differing from what we Pydantic-typed
- mcp pin not closing live CVEs
- mistune `>=3` admitting unpatched issues

This deep audit added the source-code layer those checks needed. **No future audit should rely on internal consistency alone for an SDK-heavy spec set.**

---

## §8 — Carved-out optional epics post-audit

- **Epic 13 (HUD)** — still optional, no audit blockers. Pin rich `>=14.1,<16` for nested-Live fix.
- **Epic 15 (case-trapdoor)** — RECOMMENDED CUT per B-PY-3 (regipy + python-evtx read-only). Alternative: template-fixture pattern (+1 day).

---

## §9 — Final verdict

**PASS WITH PATCH SERIES.**

The wedge is sound. The architecture pattern survives external validation. The 21 BLOCKERs are tactical and patchable in 6-10 hours of focused work (2-3h wall-clock with parallel dispatch). The patch series is concretely specified above. After patches → small re-audit → orchestrator fires safely.

**Most urgent: B-VOL-1 (`windows.malfind.Malfind` deprecation expires 2026-06-07, Friday).** If we don't patch in 4 days, every memory analysis in production breaks the moment SIFT pulls Vol3 2.29.0.

**Recommended next step:** Abu approves the patch series. Then either (a) I apply patches manually, (b) 3-4 parallel patch agents fire, or (c) Abu wants to review patches before any land.

---

## §10 — Sources

- `docs/.audit/01-pydantic-ai-verification.md` (4 BLOCKERs)
- `docs/.audit/02-mcp-fastmcp-verification.md` (2 BLOCKERs + 1 FIX-IT)
- `docs/.audit/03-volatility3-verification.md` (3 BLOCKERs)
- `docs/.audit/04-ez-tools-verification.md` (9 BLOCKERs)
- `docs/.audit/05-misc-libs-verification.md` (3 BLOCKERs + 5 FIX-ITs)
- `docs/.audit/06-sift-and-datasets-verification.md` (0 BLOCKERs + 8 FIX-ITs)
- Total: 21 BLOCKERs + 18 FIX-ITs across 6 audit reports

Plus external references cited in each audit doc (GitHub commit SHAs, CVE IDs, source file:line refs, vendor docs URLs).
