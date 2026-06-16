# SilentWitness — Agent Guide

A hypothesis-first IR investigator (Custom MCP Server + Pydantic AI reference agent) for SANS Find Evil! See `docs/architecture.md` for the architecture spec.

## Non-negotiables

1. **Quality > deadline.** AI coding gives us speed to ship the *right thing*, not to cut corners. **No mocks on the hot path. No half-built features.** If the right way takes longer, do it the right way. Per Abu 2026-06-03: *"by using AI coding…a deadline is not a barrier. I don't want this to go; I've been doing mock integration and something like that."*
2. **Test before commit.** Coverage gate (enforced per-package in CI): 95% on `verification/`, 90% on `audit/` + `findings/`, 85% elsewhere. Property tests with `hypothesis` where applicable.
3. **Research when stuck.** Library APIs drift. If behavior differs from spec: Context7 the library → web-search the symptom → read source → amend. Don't ship a workaround that hides the underlying issue.
4. **Research existing libraries BEFORE hand-rolling.** It's 2026 — a mature permissive library probably already solves it. Don't reinvent (e.g. evidence access/parsing/indexing = `dfvfs`/`plaso`/`regipy`/`python-evtx`/SQLite-FTS5, NOT bespoke TSK glue). **Licensing gate: submission is MIT/Apache, so every dep must be permissive — `dissect` (Fox-IT) is AGPL-3.0, DO NOT USE.** Check license before adopting.
5. **Use sub-agents liberally for research/audits.** Parallel, fast, keeps main context clean — delegate surveys/audits/deep-dives to `general-purpose`/`Explore` agents. (Implementation stays one-task-at-a-time: sub-agents are for research, not parallel coding.)
6. **≤400 LOC per Python file** (CI gate). Split at natural module boundaries.

## Vocab discipline (CI grep gate)
Never: "Ralph Wiggum Loop", "court-admissible", "autonomous SOC", "eliminates hallucinations", "find evil" as marketing.
Use: "defensible audit trail", "senior-analyst sequencing", "hypothesis pivot", "self-correct".

## Plan-vs-shipped audit (MANDATORY before claiming "done")
Never report work complete by shipping a subset and calling it finished. Before saying done, write an explicit checklist: enumerate *every* feature/item the plan or your own stated scope promised, and mark each **SHIPPED** (cite the file/commit that proves it), **CUT** (state why + who decided), or **CHANGED** (we took a different approach than planned — state the deviation and why). Any item that is not SHIPPED must be named out loud, not silently dropped.

## Critical pin reminders
- `mcp>=1.23.0,<2.0` (CVE-2025-66416 + CVE-2025-53366 closed)
- `pydantic-ai[anthropic,openai,google,ollama,mcp,fastmcp]>=1.105.0,<2.0.0`
- `mistune>=3.2.1` (6 CVEs in 3.0-3.2.0 closed)
- `weasyprint>=68.1,<70.0` (CVE-2025-68616 closed)
- `uv==0.11.18` (0.5.x has breaking semantics)
- `rich>=14.1,<16` (nested-Live fix)
- `volatility3==2.27.0` in own venv at `/opt/silentwitness/vol3-venv/bin/vol`
- **structlog DROPPED** — use Pydantic `model_dump_json()` directly

## Critical SDK gotchas (audit-verified vs Pydantic AI 1.105 source)
- `Agent(capabilities=[hooks])` — NOT `hooks=[...]`
- `@hooks.on.after_model_request` / `@hooks.on.after_run` — NOT `on_step` / `on_finish`
- `agent.run(..., usage_limits=UsageLimits(request_limit=N))` — NOT `Agent(max_iterations=N)`. `request_limit=None` disables the cap (this repo's default since PR #236 — Pydantic-AI's own default is 50, which silently killed real runs at iteration 50).
- `MCPServerStdio(...).filtered(lambda ctx, td: td.name in ALLOWLIST)` — NOT `tool_filter=`
- `Agent(toolsets=[server])` — `mcp_servers=` is DEPRECATED
- `MCPServerStreamableHTTP` — NOT `MCPServerHTTP` (doesn't exist)
- `sampling_model=` on `MCPServerStdio(...)` constructor — no `agent.set_mcp_sampling_model()` method

## SIFT 2026 paths (verified vs current sift-saltstack)
- Vol3 (ours): `/opt/silentwitness/vol3-venv/bin/vol` — never `/opt/volatility3/bin/vol` (SIFT pins no version)
- Vol3 plugins: `windows.malware.malfind.Malfind` (NOT `windows.malfind.Malfind` — removed 2026-06-07); `windows.registry.lsadump.Lsadump` (NOT `windows.lsadump.Lsadump`)
- EZ Tools FLAT path: `/opt/zimmermantools/<Tool>.dll` for MFTECmd, AmcacheParser, AppCompatCacheParser, SBECmd, PECmd, SrumECmd, JLECmd, LECmd, RBCmd. NESTED only for RECmd, SQLECmd, iisGeolocate, **EvtxECmd**
- EvtxECmd quirk: `/opt/zimmermantools/EvtxeCmd/EvtxECmd.dll` (lowercase `e` in dir, uppercase `EC` in DLL)
- EZ Tools exit codes are UNRELIABLE for EvtxECmd, PECmd, SBECmd, AmcacheParser, AppCompatCacheParser → parse stderr for Serilog `^\[\d{2}:\d{2}:\d{2} (ERR|FTL)\]` markers. MFTECmd is the only EZ tool whose exit code IS reliable.
- Claude Code v2.0.61 pre-installed at `/usr/local/bin/claude`

## When in doubt
1. Read the relevant section of `docs/architecture.md`
2. Read the source code (this repo is the source of truth — no external spec to consult)
3. Context7 / web for fresh library API
