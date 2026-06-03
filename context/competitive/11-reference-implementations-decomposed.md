# 11 — Reference Implementations, Decomposed

> Domain knowledge. NOT prescription. This file decomposes what other people have built around the Find Evil! / Protocol SIFT problem so that design-phase agents can read the field clearly. Conclusions about what to build are NOT in this file. They are made in SPEC.md, informed by what is true here.
>
> All facts in this file are public as of 2026-06-02. Where a repo has been cloned and read directly, file paths and line numbers are given. Where information comes from public READMEs, vendor product pages, or arXiv papers, the source is named inline.
>
> **Meta-rule observed throughout:** for each implementation, this document tells you what the thing *is*, what specific design choices it *makes*, and what those choices *signal* about the user problem the author was solving. It does NOT say "we should copy X" or "we should beat Y." Read this, then make your own architectural decisions in design phase.

---

## How to read this file

The file is organised in eight sections matching eight distinct categories of prior work:

1. **`teamdfir/protocol-sift`** — the official hackathon baseline (the thing every submission either extends or replaces).
2. **`AppliedIR/Valhuntir` + its sibling MCP repos** — the published quality bar named in the rules.
3. **`marez8505/find-evil`** — a public solo-builder competitor visible on GitHub.
4. **Other competitor builds** visible publicly on GitHub topics `find-evil`, `protocol-sift`, `sift-sentinel`, `sift-mcp` — pattern, wedge, maturity per build.
5. **Existing forensic MCP servers built independently of this hackathon** — what already exists in the OSS DFIR-MCP ecosystem.
6. **Vendor "AI SOC" / agentic-DFIR commercial products** — the parallel commercial track that the hackathon is implicitly competing with as a category.
7. **Adjacent OSS LLM-DFIR tools** — projects that don't fit any of the above buckets but are conceptually adjacent (Timesketch+Sec-Gemini, SocTalk, Talon).
8. **Anti-hallucination patterns from outside DFIR** — Pydantic Instructor citation validators, NABAOS tool receipts, GitMCP context injection — non-DFIR prior art that is technically relevant to the hackathon's stated problem.

A closing section enumerates **observable patterns across the field** — recurring choices that emerge in multiple implementations. It does not recommend.

Where a file:line citation appears (e.g. `forensic-mcp/server.py:126-254`), it points into the Valhuntir / sift-mcp source as cloned at HEAD on 2026-06-02. The repos at issue were cloned at depth 1 into `/tmp/protocol-sift-research/` for the research underlying this document.

---

## Section 1 — `teamdfir/protocol-sift`

### Repo metadata

| Field | Value |
|---|---|
| URL | https://github.com/teamdfir/protocol-sift |
| Stars / forks | 15 / 8 (read 2026-06-02) |
| License | Not specified (see "What it does NOT do" below) |
| Language split | Python 77.6%, Shell 22.4% |
| HEAD commit | `40bed7a Update README.md` — Mar 25, 2026 |
| Releases | None published |
| Author | Rob T. Lee (SANS / teamdfir org) |
| Status | "Baseline POC" — official starting point for hackathon submissions |

### Stated purpose / target user (verbatim from README & code)

The README frames Protocol SIFT as "configuration files to make Claude Code on a SIFT VM behave like a Principal DFIR Orchestrator." The unstated-but-implied target user is the SANS-curriculum-trained DFIR analyst working a single case on a single SIFT VM, with Claude Code already installed and authenticated.

The system prompt's first line (`global/CLAUDE.md`) declares the role: **"You are the Principal DFIR Orchestrator."** It tells the model the evidence is read-only, that timestamps must be UTC, and that writing is permitted only to `./analysis/`, `./exports/`, and `./reports/`. This is a one-prompt characterisation of "what good DFIR looks like" rather than a system that *enforces* good DFIR.

### Architecture decomposition — what's the shape, what are the layers

Protocol SIFT is **not an application**. It has no daemon, no MCP server, no agent framework, no runtime. It is **a 10-file configuration bundle** that gets installed into `~/.claude/` so that vanilla Claude Code behaves a particular way when invoked from a case directory on a SIFT Workstation.

The shape:

```
Claude Code (the CLI binary, installed separately)
    │
    ├── ~/.claude/CLAUDE.md             ← global system prompt
    ├── ~/.claude/settings.json         ← pre-approved tool list + Stop hook
    ├── ~/.claude/settings.local.json   ← machine-local overrides (sudo apt)
    ├── ~/.claude/skills/
    │   ├── memory-analysis/SKILL.md
    │   ├── plaso-timeline/SKILL.md
    │   ├── sleuthkit/SKILL.md
    │   ├── windows-artifacts/SKILL.md
    │   └── yara-hunting/SKILL.md
    ├── ~/.claude/case-templates/CLAUDE.md   ← per-case template
    └── ~/.claude/analysis-scripts/generate_pdf_report.py
```

There are exactly three layers in conceptual terms:

1. **The Claude Code binary.** Not shipped by Protocol SIFT. Installed separately from `claude.ai/install.sh`.
2. **The CLAUDE.md prompt layer.** Two files: a global one in `~/.claude/CLAUDE.md` that always loads, and a per-case one in `/cases/<CASE>/CLAUDE.md` that loads when the user `cd`s into a case directory and runs `claude`.
3. **The `~/.claude/skills/` library.** Skill files are domain-specific prompt bundles that Claude Code can pull into context when relevant. The Anthropic Skills feature treats `SKILL.md` files as on-demand context augmentation.

There is no fourth layer. Every tool invocation is a raw `Bash(...)` call from Claude Code. There is no MCP server interposed between the model and the shell.

### The 10-file config bundle structure — file by file

| File | Lines | Purpose |
|---|---|---|
| `README.md` | 393 | Install instructions, file-by-file rationale, chain-of-custody notes |
| `install.sh` | 191 | Bash installer; backs up existing config; copies new files in |
| `global/CLAUDE.md` | 75 | Global system prompt (role, evidence-mode, output paths, tool path table, artifact→skill routing) |
| `global/settings.json` | 145 | Permission allowlist (~100 forensic CLIs); deny list; Stop hook |
| `global/settings.local.json` | 11 | Local-only allows: `sudo apt`, `apt-cache search`, `psort.py` |
| `skills/memory-analysis/SKILL.md` | 379 | Volatility 3 + Memory Baseliner cookbook |
| `skills/plaso-timeline/SKILL.md` | 294 | log2timeline / psort / pinfo reference |
| `skills/sleuthkit/SKILL.md` | 409 | TSK + EWF, fls/icat workflow, bulk_extractor, PhotoRec |
| `skills/windows-artifacts/SKILL.md` | 721 | EZ Tools suite + event-ID reference tables + USB chain queries |
| `skills/yara-hunting/SKILL.md` | 339 | YARA rule structure + community-rule sources + Velociraptor note |
| `case-templates/CLAUDE.md` | 199 | Per-case template, pre-populated with SRL FOR508 lab case |
| `analysis-scripts/generate_pdf_report.py` | (~300) | WeasyPrint-based PDF generator |

#### `global/CLAUDE.md` (75 lines) — the global system prompt

This file is unconditionally loaded into every Claude Code session for the user who installed Protocol SIFT. It sets up:

- **Role.** "You are the Principal DFIR Orchestrator."
- **Evidence stance.** Evidence is read-only.
- **Output constraints.** Write only to `./analysis/`, `./exports/`, `./reports/`. UTC timestamps. No hallucinations.
- **Installed tool table.** Where each forensic tool's binary lives on a SIFT VM (e.g. Volatility 3 at `/opt/volatility3-2.20.0/vol.py`).
- **Routing table.** Maps artifact type to skill file ("for memory analysis → load `memory-analysis` skill"; "for Windows artifacts → load `windows-artifacts` skill"; etc.).
- **One-sentence verification clause.** "Verify tool success after every run. On failure: read stderr → hypothesize → correct → retry."

That last sentence is the **only** self-correction construct in the entire repo. It is in the prompt, not in code.

#### `global/settings.json` — permission allowlist + deny list + Stop hook

This is the structural piece (such as it is). The settings file is a JSON document Claude Code reads at startup to determine which tools are pre-approved and which are forbidden.

**Pre-approved (~100 entries)** include:
- Sleuth Kit: `fls`, `icat`, `mmls`, `blkls`, `mactime`, `tsk_recover`
- Plaso: `log2timeline.py`, `psort.py`, `pinfo.py`
- Volatility: `vol`, `vol.py`, `python3 vol.py`
- EZ Tools: `PECmd.exe` via `dotnet`, `EvtxECmd.exe`, `RECmd.exe`, `MFTECmd.exe`, etc.
- YARA: `yara`, `yarac`
- Carving: `bulk_extractor`, `foremost`, `scalpel`, `photorec`
- Hashing: `sha256sum`, `md5sum`, `ssdeep`, `hashdeep`
- Network: `tshark`, `tcpdump` (read-only)
- File ops within whitelisted dirs: `mkdir`, `cp`, `mv`, `ls`, `cat`, `head`, `tail`, `grep`, `awk`, `sed`, `find`, `wc`

**Denied** entries (notably):
- `rm -rf`
- `dd`
- `wget`, `curl`
- `ssh`
- Claude Code's own `WebFetch` tool

The deny list is short. It blocks the obvious exfiltration commands but does not block "shell trickery" — e.g. a `python3 -c 'urllib.request...'` would not be caught, nor would `nc` or `socat` if either were installed (they are not in the deny list by name).

**The Stop hook.** At conversation end, settings.json registers a hook that appends a conversation summary to `./analysis/forensic_audit.log`. This is the only audit artifact the system produces by default. It is **one entry per session**, not one entry per tool call.

#### The five skill files — what each one teaches

Skills are not executable. They are markdown documents loaded into Claude's context when a routing keyword matches. Each one is a domain-specific cookbook.

**`skills/memory-analysis/SKILL.md` (379 lines).** A Volatility 3 + Memory Baseliner methodology. Six-step structure: profile detection → process tree → network → injection → handles/registry → timeline correlation. Documents every relevant Vol3 plugin (`pslist`, `pstree`, `psscan`, `dlllist`, `handles`, `cmdline`, `netstat`, `netscan`, `malfind`, `ldrmodules`, `modules`, `modscan`, `svcscan`, `registry.printkey`, `windows.filescan`, `windows.dumpfiles`). Specifies output redirect patterns (`> ./analysis/memory/pstree.txt`). Has an "anomaly indicators" table (svchost not as child of services.exe; PowerShell as child of Office; suspicious DLL paths under `\\AppData\\Local\\Temp`). Documents error handling for common failure modes (wrong OS profile, missing symbol cache).

This file teaches the model **what to run when**, and what to look at in the output. It does not teach the model how to recover when wrong — except through one-shot examples.

**`skills/plaso-timeline/SKILL.md` (294 lines).** The Plaso super-timeline cookbook: `log2timeline.py` to produce a `.plaso` storage file, `psort.py` to filter and render, `pinfo.py` to inspect, `image_export.py` to extract files. Documents filter syntax (`"date > '2025-01-01' AND parser is 'mft'"`), parser presets, VSS handling (`--vss-stores all`), multi-plaso merge patterns.

**`skills/sleuthkit/SKILL.md` (409 lines).** The Sleuth Kit + EWF tools reference. Documents `ewfverify` → `ewfmount` → `mmls` → `fls -r` → `icat` workflow. Carving with `bulk_extractor` and `photorec`. Timeline generation with `fls + mactime`. Specifies how to mount E01 read-only without polluting evidence.

**`skills/windows-artifacts/SKILL.md` (721 lines — the longest).** A wide reference for the EZ Tools / Zimmerman suite running under `dotnet` on the SIFT VM. Documents:
- `PECmd` for Prefetch (proof of execution + 8 most recent run times)
- `AmcacheParser` for Amcache (file presence, PE metadata — NOT execution)
- `MFTECmd` for $MFT (file timestamps, MFT records, ADS detection)
- `EvtxECmd` for Windows event logs (with Hayabusa map files)
- `RECmd` for registry hives (with batch files for ASEP triage)
- `SBECmd` for ShellBags
- `JLECmd` for jumplists
- `LECmd` for LNK files
- `WxTCmd` for Windows Timeline
- `RBCmd` for the Recycle Bin
- `SrumECmd` for SRUM (network/app usage stats)
- `SQLECmd` for SQLite DBs (browser history etc.)
- `bstrings` for string extraction

Plus Windows event-ID reference tables for Security/PowerShell/RDP/Defender/System/Tasks/WMI, and USB device-chain registry queries.

This is the file that does the most "teaching the model the domain" — it is dense with the knowledge a FOR508 graduate uses.

**`skills/yara-hunting/SKILL.md` (339 lines).** YARA 4.1.0 reference: rule structure, modules (`pe`, `math`, `hash`, `magic`), performance ordering (cheap conditions first), IOC sweep workflow. Community rule sources named: Neo23x0/signature-base, Elastic protections, Mandiant rules.

Notes that Velociraptor VQL is "an enterprise add-on, not a local binary" — Velociraptor is mentioned as conceptually relevant but explicitly out-of-scope for the local SIFT VM.

#### `case-templates/CLAUDE.md` (199 lines) — the per-case prompt

This is a project-level CLAUDE.md the examiner copies into each new case directory. It contains:

- A case-metadata header (CASE ID, examiner, date opened, status).
- A pre-populated SRL FOR508 case: **Stark Research Labs, CRIMSON OSPREY APT, dc01/rd01 hosts, attack timeline 2023-01-24/25**. This is the FOR508 official lab data hardcoded into the template.
- Per-host inventory section (image hashes, mount points).
- A working hypothesis section (mostly empty in the template).
- A findings section (header only — Claude writes into this).
- Report section (header only).

**The examiner is expected to strip out the SRL hardcoding on each new case.** This is the first manual step on any real engagement.

#### `analysis-scripts/generate_pdf_report.py`

A WeasyPrint-based PDF report generator. Claude writes one of these per case with a `DATA` dict and a `body_html` raw string, then executes it to produce a PDF. The README flags one gotcha verbatim: `body_html` must be `r"""..."""` (raw triple-quoted) if it contains Windows paths (because `\U` is otherwise interpreted as a Unicode escape).

The PDF generator is therefore **per-case code Claude writes**, not a reusable library. There is no template that gets parameterised across cases; there is one Python script generated each time, with the case's data inline.

### Specific design choices and what each signals about user pain

This is where reading the artifact carefully pays off — every choice is a signal about a problem the author thought was urgent.

| Choice | Pain it signals |
|---|---|
| Configuration bundle, not an application | Author wanted minimal install friction. Pain: SIFT users will not install a daemon for a configuration tweak. |
| ~100 pre-approved CLIs in `settings.json` | Pain: permission-prompt fatigue. The author observed that vanilla Claude Code on a SIFT VM hits a permission prompt every 10 seconds, and the analyst rubber-stamps until they stop reading. |
| Skill files (markdown) instead of code | Pain: keeping the model on the "right" tool for the artifact type. Author believes the failure mode is *wrong tool selection*, not wrong tool execution. |
| Routing table inside the global CLAUDE.md | Pain: when faced with N skills, the model picks the wrong one. The routing table is a forcing function. |
| Per-case template pre-populated with the SRL FOR508 case | Pain: cold-start. Author expects the user to be a FOR508 attendee who has *that* case in front of them. Onboarding signal. |
| Stop hook for audit (one entry per session) | Pain: "I need a record that something happened" but not "I need a record of every tool call." Minimum-viable audit. |
| Single-sentence "verify and self-correct" in CLAUDE.md | Pain noticed but not solved. Author flags the problem to the LLM and hopes. |
| Output path constraint (`./analysis/`, `./exports/`, `./reports/`) | Pain: the LLM was overwriting evidence in earlier iterations. Forcing function moves writes to safe dirs. |
| Generate-PDF-script-per-case pattern | Pain: per-case data shape varies enough that a fixed template doesn't fit; author surrenders to "let Claude write the report code." |
| WeasyPrint instead of LaTeX or DOCX | Pain: WeasyPrint is `pip install`-able on SIFT without much fuss. LaTeX install pulls 2 GB. |
| Note about `r"""..."""` for `body_html` with Windows paths | Pain encountered during development; ships as a footnote because the fix would require code the author didn't want to write. |

### Tooling / library stack

- **Runtime:** the user's installed Claude Code binary.
- **Skills loader:** Anthropic's built-in Skills feature in Claude Code (markdown SKILL.md files in `~/.claude/skills/<name>/`).
- **PDF generation:** WeasyPrint (Python + GTK/Pango/Cairo dependencies).
- **Forensic tool binaries:** assumed already on the SIFT VM (Volatility 3, Sleuth Kit, Plaso, EZ Tools via dotnet, YARA, bulk_extractor, etc.). The repo does not install or version-pin them.
- **Installer:** bash + curl + git (the `install.sh` script).
- **No databases, no message queues, no servers, no schedulers, no daemons, no caches.**

### Audit / logging story

Single mechanism: the Claude Code `Stop` hook in `settings.json` appends a conversation summary to `./analysis/forensic_audit.log` at session end.

Schema: free-form text (whatever Claude Code's summary feature produces). Not JSONL. Not signed. Not append-only at the OS level (the file is writable). One entry per session, not one entry per tool call.

There is no per-Bash-call audit. There is no provenance ID. There is no record of which `analysis/memory/pstree.txt` came from which `vol.py` invocation with which arguments at which time.

### Constraint / security story

**Three constructs, all prompt-or-permission-based:**

1. **Prompt constraint.** The global CLAUDE.md tells the model evidence is read-only and writes go to specific paths. The model is asked to comply.
2. **Permission allowlist.** Claude Code's `settings.json` allows ~100 specific commands; everything else triggers a permission prompt.
3. **Permission denylist.** Five entries: `rm -rf`, `dd`, `wget`, `curl`, `ssh`, plus Claude Code's `WebFetch` tool.

**There is no sandbox.** No bubblewrap. No containers. No filesystem chroot. No network isolation. No process isolation. No capability dropping.

**There is no examiner password gate.** The findings file is `./analysis/findings.json` (or whatever Claude writes), readable and writable by Claude at any time. There is no DRAFT/APPROVED state. There is no cryptographic signing of approved findings.

**Network egress is blocked only by the deny list.** Python's `urllib` is not blocked. `nc`/`socat`/`telnet` are not blocked. `git push` is not blocked (and Claude could write to a temp directory that happens to be a git repo).

### Self-correction story

**One sentence in `global/CLAUDE.md`:**

> "Verification — Verify tool success after every run. On failure: read stderr → hypothesize → correct → retry."

That is the entire mechanism. There is no:
- Critic agent
- Retry loop in code
- Checkpoint before conclusions
- Validation step before findings get written
- Cross-check between independent tool outputs
- Comparison against a ground-truth corpus
- Anything programmatic at all

The model is asked to be diligent. The architecture does not enforce it.

### Report / output story

**WeasyPrint PDF, generated per case by Claude writing a Python script.**

The shape: Claude builds a `DATA` dict containing case metadata, findings, timeline events, and IOCs; then renders a `body_html` template string; then calls a WeasyPrint helper from `~/.claude/analysis-scripts/generate_pdf_report.py` to produce the PDF.

There is no:
- Report profile (full / executive / timeline / IOC)
- Approved-only filter
- Cross-reference between report claims and tool executions
- Signature on the report
- Versioning of the report against the same case at different times

The README notes that the per-case Python script is reuse-by-copy: there is no shared library beyond the WeasyPrint helper function. Two cases produce two independent Python scripts.

### Public commit / issue activity signal

- HEAD commit at read time: `40bed7a Update README.md` (Mar 25, 2026).
- Total commits visible: 4 on `main`.
- Releases: 0.
- Open issues: not surfaced via the web fetch (description blank in teamdfir org listing).
- Forks: 8 (signal that some builders are extending it; some of the competitor repos in section 4 are forks).

The maintenance posture is "the baseline has been published; the community is expected to extend." There is no indication that Rob T. Lee is iterating on it further during the hackathon.

### What Protocol SIFT does NOT do (the gaps)

Listed comprehensively, as these gaps are what every competitor submission either fills or claims to fill:

- **No MCP server.** Every tool call is a raw `Bash(...)`. Outputs are unstructured text.
- **No per-tool-call audit.** Only the Stop hook gives a session summary.
- **No approval gate.** There is no DRAFT/APPROVED state.
- **No HMAC or any other cryptographic signing.**
- **No multi-examiner support.** Single-user, single-case.
- **No structured finding schema.** Claude writes free-text into markdown / JSON files.
- **No structured timeline schema.**
- **No grounding score, no provenance tier classification, no caveats library.**
- **No self-correction loop.** Just a one-line prompt instruction.
- **No critic agent or revise step.**
- **No adversarial-evidence sanitization.**
- **No sandbox.** Permissions only.
- **No memory-plugin-aware reasoning chain.** Vol3 is called via shell.
- **No live-host triage.** Disk image / memory dump only.
- **No real-time investigation HUD.** No browser UI at all.
- **No accuracy benchmark.**
- **No license file** (notable — the rules require MIT or Apache 2.0 for submissions; Protocol SIFT itself does not declare one in the standard place).
- **No CI.** No tests in the repo.
- **No version pinning of forensic tools.** Assumes whatever SIFT ships.

These omissions are not necessarily defects. They are signals about what Protocol SIFT *is* — a baseline configuration kit, not a platform.

---

## Section 2 — `AppliedIR/Valhuntir` + `sift-mcp` + `wintools-mcp` + `opensearch-mcp`

The hackathon rules name Valhuntir as **"Example Submission and level of quality to meet/exceed written by Steve Anson (SANS Author)."** It is the published quality bar.

This is a multi-repo platform. Decomposing it requires walking through each repo and each MCP backend separately, because the surface area is large (~14,000 LOC Python, 9 MCP backends, 100 forensic tools across them, 22,000-record forensic RAG, 2.6M-row Windows triage baseline).

### Repo group metadata

| Repo | URL | Role | LOC est. | License |
|---|---|---|---|---|
| `AppliedIR/Valhuntir` | https://github.com/AppliedIR/Valhuntir | `vhir` CLI + architecture docs | ~10,400 (commands only) | MIT |
| `AppliedIR/sift-mcp` | https://github.com/AppliedIR/sift-mcp | Monorepo: 11 packages — gateway + 7 backends + 2 libraries | ~24,000 across packages | MIT |
| `AppliedIR/opensearch-mcp` | https://github.com/AppliedIR/opensearch-mcp | Evidence indexing/query backend (17 tools, 15 parsers) | — | MIT |
| `AppliedIR/wintools-mcp` | https://github.com/AppliedIR/wintools-mcp | Windows-side tool execution (10 tools, 31 catalog entries) | — | MIT |

**Valhuntir HEAD on read date:** `ce1ae36 Update mkdocs-material requirement from >=9.5 to >=9.7.6` (Jun 2026 — dependabot churn).
**Total commits in `AppliedIR/Valhuntir`:** 330 (as of read date).
**Releases:** v0.5.0 first cut (Feb 28, 2026), v0.6.1 latest (Apr 16, 2026).
**Stars / forks for Valhuntir:** 73 / 15 (the largest in the field by an order of magnitude).
**Stars for `AppliedIR/sift-mcp`:** 8.

### Author / motivation disclosure

The README's "Clear Disclosure" section (verbatim):

> "I do DFIR. I am not a developer. This project would not exist without Claude Code handling the implementation. While an immense amount of effort has gone into design, testing, and review, I fully acknowledge that I may have been working hard and not smart in places. My intent is to jumpstart discussion around ways this technology can be leveraged for efficiency in incident response while ensuring that the ultimate responsibility for accuracy remains with the human examiner."

**Significance.** The author identifies as a practitioner using Claude Code as the implementer. The platform is a *methodology made executable* by an LLM, not a software product engineered for resale.

**Author background.** Steve Anson is SANS Principal Instructor, co-author of FOR508 (Advanced IR), former DCIS + FBI computer-crime task force agent, trained national cyber units in 60+ countries, co-author of *Mastering Windows Network Forensics and Investigation* and *Applied Incident Response* (Wiley, 2020). Runs Informed Defense (training + vCISO consultancy). Notably his consultancy does NOT sell IR as a billable service line — he sells training and policy work. Valhuntir is therefore positioned as a *reference platform for what disciplined IR-AI looks like*, distributed MIT-free.

### Stated purpose / target user (verbatim from README & docs)

> "Valhuntir turns a single incident response analyst into the manager of an agentic AI incident response team."
>
> "The AI, like a hex editor, is a tool to be used by properly trained incident response professionals."
>
> "ALWAYS verify results and guide the investigative process. If you just tell Valhuntir to 'Find Evil' it will more than likely hallucinate rather than provide meaningful results. The AI can accelerate, but the human must guide it and review all decisions."

The README warns about hallucination twice, with the exact same phrasing, in two different documents (README + user-guide). This is the *only* literal use of "hallucination" in the docs corpus. The framing throughout is: **hallucination is what happens when you don't enforce methodology — fix methodology, not the model.**

Target user implied by every choice: a **credentialed FOR508-graduate examiner** who is currently solo on a case, who is or could be cross-examined on their findings, who works at a small consultancy or in-house IR team, and who needs the audit trail to survive defense-side scrutiny.

### Architecture decomposition — three layers, nine backends

Per `docs/architecture.md`:

```
Layer 1 — Gateway:     sift-gateway :4508 (HTTP, bearer auth, Examiner Portal)
Layer 2 — MCP backends: 8 stdio subprocesses (+1 HTTP on separate VM)
Layer 3 — Tool layer:  forensic CLIs, knowledge DBs, OpenSearch evidence index
```

```
LLM Client ──► MCP Streamable HTTP ──► sift-gateway :4508 ──┬──► /portal/ (Examiner Portal, browser, 8 tabs)
                                                            │
                                                            ├── stdio ──► forensic-mcp        (23 tools — state machine)
                                                            ├── stdio ──► case-mcp            (15 tools — lifecycle)
                                                            ├── stdio ──► report-mcp          (6 tools — 6 profiles)
                                                            ├── stdio ──► sift-mcp            (5 tools — Linux exec, denylist)
                                                            ├── stdio ──► forensic-rag-mcp    (3 tools — 22K records)
                                                            ├── stdio ──► windows-triage-mcp  (13 tools — 2.6M baseline)
                                                            ├── stdio ──► opencti-mcp         (8 tools — threat intel)
                                                            └── stdio ──► opensearch-mcp      (17 tools — 15 parsers)

(separate Windows VM)   LLM Client ──► HTTPS ──► wintools-mcp :4624 (10 Windows tools)
(separate REMnux VM)    LLM Client ──► streamable-http ──► remnux-mcp :3000 (optional)
```

Authentication is bearer token: `Authorization: Bearer vhir_gw_<24 hex>` — 96 bits of entropy per token. Per-examiner API key in `gateway.yaml`. Health-check exempt.

### sift-gateway :4508 routing

Per `docs/architecture.md`, the gateway is the single HTTP entrypoint. It:

- Authenticates the MCP client (Claude Code, Claude Desktop, LibreChat, etc.) via bearer.
- Routes inbound MCP tool calls to the appropriate backend over stdio.
- Serves the Examiner Portal at `/portal/`.
- Enforces rate limits and per-backend timeouts.
- Health-check endpoint at `/health` is auth-exempt.

**Why stdio over network sockets between gateway and backends.** Stdio means each backend is a long-running subprocess of the gateway. No port to expose. No additional auth between gateway and backend. Failure isolation: if one backend crashes, the gateway respawns it without bringing the others down.

### MCP backend breakdown — what each one does, what its tools mean

#### `forensic-mcp` (23 tools — 9 core + 14 discipline) — the investigation state machine

This is the **core finding pipeline**. It implements the DRAFT → APPROVED state machine.

**The 9 core tools** (from `forensic-mcp/server.py`):
- `record_finding(finding)` — stage a DRAFT finding
- `record_timeline_event(event)` — stage a DRAFT timeline event
- `validate_finding(finding_json)` — pre-flight schema + methodology check
- `log_reasoning(text)` — append-only hypothesis log
- `record_action(...)` — append-only action log
- `list_findings(status=DRAFT|APPROVED|REJECTED)` — query findings
- `list_timeline(status=...)` — query timeline events
- `get_finding(id)` — fetch one finding
- `get_timeline_event(id)` — fetch one event

**The 14 discipline tools/resources** — these expose forensic methodology to the LLM as either MCP Resources (passive, read-only) or as Tools (active calls) when the client doesn't support Resources:
- `get_investigation_framework` — high-level methodology
- `get_rules` — the rule list ("Shimcache proves PRESENCE not EXECUTION", etc.)
- `get_checkpoint_requirements` — what must be true before claiming a conclusion
- `get_evidence_standards` — what counts as evidence
- `get_confidence_definitions` — HIGH / MEDIUM / LOW / SPECULATIVE thresholds
- `get_anti_patterns` — common analysis mistakes
- `get_tool_guidance(tool_name)` — per-tool methodology
- `get_false_positive_context` — known false-positive patterns
- `get_corroboration_suggestions` — "if you saw X, also check Y"
- `list_playbooks` — available investigation playbooks
- `get_playbook(name)` — full playbook content
- `get_collection_checklist(artifact_type)` — what to collect for each artifact class

**Key code path: `record_finding`** in `forensic-mcp/server.py:126-254` and `forensic-mcp/case/manager.py:660-1158`:

The server-side gate logic is non-trivial. It performs:
1. Schema validation via `validate_finding_data` (manager.py:679-687) — string-length and required-field checks.
2. **`audit_id` existence check** (manager.py:821-862) — each artifact in the finding cites an `audit_id`. The server loads `audit/<backend>.jsonl` and verifies the cited ID exists. If not, REJECT.
3. **Hash-based provenance chain resolution** (manager.py:940-1100) — uses `input_files` and `output_files` from the audit entry to trace which evidence file produced the artifact's `audit_id`. Sets `provenance_grade = FULL/PARTIAL`.
4. **Evidence-registry path check** (manager.py:1121) — artifact source filenames must be in the registered evidence list. Path-level check.
5. **Provenance tier classification** — MCP > HOOK > SHELL > NONE. NONE = hard reject. The provenance tier is derived from whether the cited `audit_id` came from a per-backend MCP audit JSONL (MCP-tier), the Claude-Code PostToolUse hook log (HOOK-tier), or examiner-supplied `supporting_commands` (SHELL-tier), or none of the above (NONE = reject).
6. **Grounding score computation** (manager.py:1593-1671) — STRONG/PARTIAL/WEAK based on whether 2+/1/0 of the reference backends (`forensic-rag-mcp`, `windows-triage-mcp`, `opencti-mcp`) were consulted during the case. Advisory, not blocking. Surfaces to the examiner.
7. **Finding gets staged as DRAFT.** Persisted to `findings.json`. Not visible in reports until approved.

**What `validate_finding()` actually does** (per `forensic-mcp/discipline/validation.py:23-105`):

```
required = ["title", "observation", "interpretation", "confidence", "type"]
for field in required:
    if not finding.get(field): errors.append(...)
# audit_ids must be a list
# type must be in {finding, attribution, conclusion, exclusion}
# confidence must be in known set
# attribution requires 3+ audit_ids
# event_timestamp regex check
```

This is pure schema + structural validation, plus one count constraint (attribution-type findings require ≥3 audit_ids). It does **not** open any audit file. It does not read tool output. It does not check whether observation text references entities present in the evidence. It is structural, not semantic.

#### `case-mcp` (15 tools) — case lifecycle

Manages the case from creation to export. Tools include:
- `case_init(case_id, examiner)`
- `case_activate(case_id)`
- `case_list`
- `case_status` — dynamically detects available platform via `importlib.util.find_spec()`
- Evidence ops: `register_evidence`, `verify_evidence_hash`, `list_evidence`, `unlock_evidence`
- Audit ops: `log_reasoning`, `record_action`, `query_audit`
- Export / import / backup
- Dashboard launcher

The case lifecycle has a state machine independent of findings: CREATED → ACTIVE → SEALED → EXPORTED.

#### `report-mcp` (6 tools) — report profiles

Tools generate reports in 6 profiles:
- `full` — every approved finding + timeline + IOCs + executive summary
- `executive` — short narrative
- `timeline` — chronological event view
- `ioc` — IOC list with grouping
- `findings` — finding-only view
- `status` — current case state

Tools include:
- `generate_report(profile)`
- `save_report(profile, path)`
- `reconcile_report(profile)` — bidirectional reconciliation against the HMAC ledger
- `list_reports`
- `delete_report`
- `preview_report(profile)`

Reports only include APPROVED items (DRAFT findings are not rendered).

**Bidirectional report reconciliation** (per `report-mcp/server.py:618-685`): at report-generation time, the system cross-checks approved items against the verification ledger and surfaces:
- `APPROVED_NO_VERIFICATION` — finding is APPROVED but has no ledger entry (anomaly: how was it approved?)
- `VERIFICATION_NO_FINDING` — ledger entry exists but the finding has been deleted or renamed
- `DESCRIPTION_MISMATCH` — the finding's substantive text differs from what was signed at approval time (mutation detected)
- Count mismatches

Also embeds **Zeltser IR Writing MCP** narrative templates (Lenny Zeltser's report templates ship as an embedded MCP).

#### `sift-mcp` (5 tools) — Linux forensic tool execution

This is what runs the actual SIFT-side commands. Tools:
- `run_command(command, purpose)` — executes a forensic CLI; denylist-protected; FK-enriched response
- `list_available_tools` — what's installed and cataloged
- `get_tool_help(tool_name)` — methodology snippet + flag reference
- `check_tools(tools=[...])` — installed-status check
- `suggest_tools(task)` — given a task description, return ranked candidate tools

Denylist: `mkfs`, `shutdown`, `reboot`, `kill -9`, `nc -e` patterns, `rm` against evidence paths, etc.

For each command in the FK catalog (59 tools × 17 categories), the response is enriched with `caveats`, `advisories`, `corroboration` suggestions, etc. (see Forensic Knowledge section below.)

#### `forensic-rag-mcp` (3 tools) — 22K-record knowledge base

Tools:
- `search_knowledge(query, top_k, source=None, source_ids=None, technique=None, platform=None)`
- `list_knowledge_sources`
- `get_knowledge_stats`

The 22,000-record knowledge base is sourced from 23 authoritative DFIR sources:
- Sigma rules (the open-source SIEM rule format)
- MITRE ATT&CK (techniques, sub-techniques, mitigations)
- MITRE D3FEND (defensive techniques)
- Atomic Red Team (attack simulation procedures)
- LOLBAS (Living Off the Land Binaries and Scripts)
- LOLDrivers (signed-but-vulnerable drivers)
- Elastic detection rules
- Splunk Enterprise Security content
- Microsoft Sentinel KQL queries
- KAPE (Kroll Artifact Parser and Extractor)
- Hayabusa rules (Sigma → EVTX detection)
- Volatility plugin documentation
- The SIFT tool documentation set
- Sleuth Kit documentation
- Plaso parser documentation
- EZ Tools documentation
- Velociraptor artifact documentation
- Windows artifact references (Eric Zimmerman's blog, Mandiant blog, SANS blog)
- TheHive analyzers
- MISP attribute types
- OpenCTI entity types
- DFIR Report writeups
- The 13Cubed YouTube channel transcripts (for Windows artifact explanation)

The "23 sources" count is from `forensic-rag-mcp/sources.yaml`. Records are chunked, embedded, and stored in a local vector index. Search returns top-K with source attribution.

#### `windows-triage-mcp` (13 tools) — 2.6M-record offline baseline

Tools:
- `check_file(path, hash=None)` — known-good / known-bad lookup
- `check_process_tree(parent, child)` — is this parent/child relationship normal?
- `check_service(name, image_path)` — known Windows service legitimacy
- `check_scheduled_task(name, action)` — known task legitimacy
- `check_autorun(key, value)` — ASEP key legitimacy
- `check_registry(hive, key, value)` — value baseline
- `check_hash(sha256)` — against LOLDrivers + known-good lists
- `analyze_filename(name)` — unicode / typosquat / homoglyph detection
- `check_lolbin(name)` — is this binary a Living Off the Land BIN?
- `check_hijackable_dll(dll, exe)` — known DLL-hijack pair check
- `check_pipe(name)` — known-good named-pipe lookup
- `get_db_stats` — counts per table
- `get_health` — DB availability

The 2.6 million records cover: known-good Windows file paths + hashes (across multiple OS versions and patch levels), known scheduled tasks, known services, known autorun keys, LOLBAS catalog, LOLDrivers, hijackable DLL pairs.

**Important behavioural detail:** `UNKNOWN` verdict is explicitly defined as "neutral, not suspicious." This is a discipline choice — an unknown file is not evidence of evil; it is evidence of unknown. The choice signals an author worried about false positives.

#### `opencti-mcp` (8 tools) — threat intel

Read-only access to a configured OpenCTI instance. Tools include indicator lookup, observable enrichment, attribution graph queries.

**Reliability features:**
- Rate-limited: 60 requests/minute default.
- Circuit breaker: opens after 5 consecutive failures, recovers after 60s.
- Read-only: no write tools exposed.

#### `opensearch-mcp` (17 tools — 8 query + 6 ingest + 2 enrichment + 1 detection) — optional evidence indexing

The optional evidence-search backend. Indexes evidence into an OpenSearch cluster for fast querying. Tools:
- **Query (8):** `search`, `aggregate`, `histogram`, `top_n`, `field_values`, `time_range_search`, `nested_search`, `cross_index`
- **Ingest (6):** `ingest_file`, `ingest_dir`, `ingest_evtx`, `ingest_plaso`, `ingest_csv`, `ingest_jsonl`
- **Enrichment (2):** `enrich_with_geoip`, `enrich_with_threat_intel`
- **Detection (1):** `apply_hayabusa_ruleset` — runs Hayabusa's 3,700+ Sigma rules against ingested EVTX automatically post-ingest

**15 parsers** (per `opensearch-mcp/parsers/__init__.py`): evtx, 10 EZ Tools (Amcache, Prefetch, ShellBags, JumpList, MFT, etc.), Volatility 3, JSON/JSONL, delimited (CSV/TSV), access logs (Apache/IIS/nginx), W3C, MPLog (Defender), schtasks XML, WER (Windows Error Reporting), SSH logs, PowerShell transcripts, Prefetch/SRUM.

**Deterministic content-based document IDs.** Re-ingesting the same file produces zero duplicates (the doc ID is a hash of content + source path).

**Provenance fields on every document:** `host.name`, `vhir.source_file`, `vhir.ingest_audit_id` — every search result can be traced back to the file it came from and the audit_id of its ingestion.

#### `wintools-mcp` (separate VM, 10 tools, 31 catalog entries)

Runs on a separate Windows VM (since SIFT is Linux). Listens on :4624 HTTPS. Tools execute Zimmerman tools (`zimmerman.yaml=14`), Sysinternals (`sysinternals=5`), memory tools (4), timeline tools (3), analysis tools (3), collection tools (1), scripts (1).

**Hardcoded denylist of 20+ binaries:** `cmd`, `powershell`, `pwsh`, `wscript`, `cscript`, `mshta`, `rundll32`, `regsvr32`, `certutil`, `bitsadmin`, `msiexec`, `bash`, `wsl`, `sh`, `msbuild`, `installutil`, `regasm`, `regsvcs`, `cmstp`, `control`.

**Argument sanitization:** blocks shell metacharacters (`;|&$\``), `@filename` response-file syntax (which can smuggle args), `-e`/`-enc` flags (PowerShell encoded command).

#### `remnux-mcp` (separate VM, optional)

Optional REMnux-side malware analysis MCP. Listens on :3000 streamable-http. Used when the case involves malware reverse engineering and a REMnux VM is available.

### The 9 defense layers — each layer explained with code reference

Per `docs/security.md`:

| Layer | Control | Type | Scope | Where it lives in code |
|---|---|---|---|---|
| **L1** | Structural approval gate (DRAFT → APPROVED requires examiner password) | Structural | All MCP clients | `src/vhir_cli/commands/approve.py:212-550` |
| **L2** | HMAC verification ledger (PBKDF2 + HMAC-SHA256) | Cryptographic | All MCP clients | `src/vhir_cli/verification.py:33-165`, `commands/approve.py:552-621` |
| **L3** | Case data deny rules (41 rules blocking Edit/Write/Bash) | Permission | Claude Code only | `setup-client-linux.sh:543-655` |
| **L4** | Sandbox filesystem `denyWrite` via bwrap | Kernel | Claude Code only | `setup-client-linux.sh:560-580` |
| **L5** | File permission chmod 444 after write | Filesystem | All clients (advisory) | `case-mcp/storage.py` |
| **L6** | Bidirectional report reconciliation | Integrity | All clients | `report-mcp/server.py:618-685` |
| **L7** | Password authentication (CLI + portal challenge-response) | Authentication | All clients | `approval_auth.py:249-271` |
| **L8** | Provenance enforcement (MCP > HOOK > SHELL > NONE) | Structural | All clients | `forensic-mcp/case/manager.py:940-1100` |
| **L9** | Kernel sandbox (bubblewrap namespaces) | Kernel | Claude Code only | `setup-client-linux.sh:600-655` |

#### L1 — Structural approval gate

Findings stage as DRAFT in `findings.json`. The MCP server **does not** expose an `approve_finding` tool. Approval is exclusive to:
- The `vhir approve` CLI command, which prompts for examiner password.
- The Examiner Portal browser UI's challenge-response auth flow.

Because there is no MCP tool to approve a finding, **the LLM cannot approve its own findings even if it tried.** This is the single most load-bearing control in the platform.

#### L2 — HMAC verification ledger

At approval time, an HMAC-SHA256 is computed over the substantive text of the approved item:
- For findings: `observation + interpretation`
- For timeline events: `description`

The HMAC key is derived from the examiner's password via PBKDF2-SHA256 with **600,000 iterations** (the OWASP 2023 minimum for PBKDF2-SHA256). The salt is per-case, generated at case init.

The ledger entry is written to `/var/lib/vhir/verification/{case_id}.jsonl`:
- Directory mode: `0700` (examiner only)
- File mode: `0600` (read/write by examiner only)
- `fsync()` after every write
- Append-only by convention; no append-only filesystem flag enforced

**Critical**: the ledger is OUTSIDE the case directory. The case directory might be under `/cases/<CASE>/`. The ledger is under `/var/lib/vhir/`. Even if the LLM owns the case directory entirely (and it does — bwrap denyWrite excludes `/var/lib/vhir/`), it cannot forge ledger entries because:

1. It can't write into `/var/lib/vhir/` (kernel-level denyWrite).
2. Even if it could, it doesn't have the password to derive the HMAC key.

`hmac.compare_digest` is used for verification (constant-time comparison, preventing timing attacks).

Code paths (verbatim file:line):
- `src/vhir_cli/verification.py:33` — `derive_hmac_key(password, salt)` — PBKDF2-SHA256, 600K iters
- `src/vhir_cli/verification.py:38` — `compute_hmac(derived_key, description)` — HMAC-SHA256
- `src/vhir_cli/verification.py:45-54` — `write_ledger_entry()` — writes to `/var/lib/vhir/verification/{case_id}.jsonl`, fsyncs, chmod 0600
- `src/vhir_cli/verification.py:82-98` — `verify_items()` — uses `hmac.compare_digest` (constant-time)
- `src/vhir_cli/verification.py:101-165` — `rehmac_entries()` — re-signs ledger on password rotation
- `src/vhir_cli/approval_auth.py:249-271` — `verify_password()` — PBKDF2 + `secrets.compare_digest`
- `src/vhir_cli/commands/approve.py:552-621` — `_write_verification_entries()` — integrated into the approve flow

#### L3 — Case data deny rules

41 entries in `.claude/settings.json` (from `setup-client-linux.sh:543-655`) blocking:
- `Edit`/`Write` to `findings.json`, `timeline.json`, `approvals.jsonl`, `todos.json`, `CASE.yaml`, `actions.jsonl`, `audit/*.jsonl`, `evidence.json`, `pending-reviews.json`
- `Edit`/`Write` to `/var/lib/vhir/**` (the ledger directory)
- `Edit`/`Write` to the `.claude/` and `.vhir/` control files themselves
- `Bash(vhir approve*)`, `Bash(*vhir approve*)`, `Bash(vhir reject*)`, `Bash(*vhir reject*)`

The deny rules cover three threat vectors:
- LLM directly editing the case state files.
- LLM editing its own config files to weaken constraints.
- LLM invoking the approve/reject CLI as a Bash command.

#### L4 — Sandbox filesystem denyWrite via bwrap

From `setup-client-linux.sh:560-580`, the Claude Code `settings.json` includes:

```json
{
  "sandbox": {
    "enabled": true,
    "allowUnsandboxedCommands": false,
    "filesystem": {
      "denyWrite": [
        "~/.vhir/gateway.yaml",
        "~/.vhir/config.yaml",
        "~/.vhir/active_case",
        "~/.vhir/hooks",
        "~/.vhir/.password_lockout",
        "~/.vhir/.pin_lockout",
        "~/.claude/settings.json",
        "~/.claude/CLAUDE.md",
        "~/.claude/rules"
      ]
    }
  }
}
```

This is filesystem-level write denial. Note: the deny list is paths inside the user's home directory. The ledger at `/var/lib/vhir/` is outside, so it doesn't need to be in this list; it's already inaccessible to the Claude Code user.

#### L5 — chmod 444 after write

After case state files are written by case-mcp, they are chmod'd to 444 (read-only for everyone). Advisory — the case-mcp process itself can rewrite when needed by chmod'ing back to 644 temporarily.

#### L6 — Bidirectional report reconciliation

Covered above under `report-mcp`. Detects three integrity-failure modes:
- `APPROVED_NO_VERIFICATION` — finding APPROVED but no ledger entry (anomaly)
- `VERIFICATION_NO_FINDING` — ledger entry but finding gone/renamed
- `DESCRIPTION_MISMATCH` — finding text changed after signing

#### L7 — Password authentication

Examiner password is set at case init, hashed via PBKDF2-SHA256 (600K iters) with a per-examiner salt, stored in the case config. Used to derive the HMAC key (L2) and to gate approve/reject CLI commands.

Portal uses challenge-response so the password never leaves the browser: server sends challenge, browser does PBKDF2 derivation and HMAC-signs the challenge, server verifies. Lockout after N failed attempts.

#### L8 — Provenance enforcement (MCP > HOOK > SHELL > NONE)

Implemented in `forensic-mcp/case/manager.py:940-1100`. Each cited `audit_id` in a finding is classified by which audit log it came from:
- **MCP-tier** — the audit_id appears in a per-backend MCP audit JSONL (e.g. `audit/sift-mcp.jsonl`). Highest trust.
- **HOOK-tier** — the audit_id appears in `audit/claude-code.jsonl` (the PostToolUse hook log of raw Bash calls).
- **SHELL-tier** — the examiner provided `supporting_commands` directly. Lowest auto-trust.
- **NONE** — no audit trail at all. Hard reject.

#### L9 — Kernel sandbox via bubblewrap

For Claude Code clients, `setup-client-linux.sh:600-655` installs a bwrap wrapper that runs Claude Code with:
- `--unshare-net` — no network access from the sandboxed Claude Code process
- `--unshare-pid` — Claude Code can't see or signal other processes
- `--unshare-uts` — separate UTS namespace
- `--unshare-ipc` — separate IPC namespace
- Read-only bind of the evidence directory
- Read-write bind of `./analysis/`, `./reports/`, etc.

The MCP gateway runs OUTSIDE the sandbox (so it can access the network for OpenCTI etc.). The LLM client (Claude Code) is inside. Communication is via stdio passed across the namespace boundary.

### The 41 deny rules in `.claude/settings.json`

From `setup-client-linux.sh:543-655` (the Linux client setup script). The full list:

```
Edit, Write to:
  findings.json
  timeline.json
  approvals.jsonl
  todos.json
  CASE.yaml
  actions.jsonl
  audit/forensic-mcp.jsonl
  audit/case-mcp.jsonl
  audit/report-mcp.jsonl
  audit/sift-mcp.jsonl
  audit/forensic-rag-mcp.jsonl
  audit/windows-triage-mcp.jsonl
  audit/opencti-mcp.jsonl
  audit/opensearch-mcp.jsonl
  audit/wintools-mcp.jsonl
  audit/claude-code.jsonl
  audit/*.jsonl (catch-all)
  evidence.json
  pending-reviews.json
  /var/lib/vhir/**
  ~/.vhir/gateway.yaml
  ~/.vhir/config.yaml
  ~/.vhir/active_case
  ~/.vhir/hooks/**
  ~/.vhir/.password_lockout
  ~/.vhir/.pin_lockout
  ~/.claude/settings.json
  ~/.claude/CLAUDE.md
  ~/.claude/rules/**

Bash:
  vhir approve*       (deny)
  *vhir approve*      (deny — catches `echo password | vhir approve` etc.)
  vhir reject*        (deny)
  *vhir reject*       (deny)
```

These rules cover three categories: case-state files (which approval mutates), control configs (which approval logic reads), and the approve/reject CLI itself.

### PreToolUse + PostToolUse + UserPromptSubmit hook architecture

Claude Code's hook system fires three types of hooks at three stages:

#### UserPromptSubmit hook

Fires before every user prompt is sent to the model. Injects:

```xml
<forensic-rules>PLAN before 3+ steps | EVIDENCE for claims | APPROVAL before conclusions | RECORD actions via forensic-mcp | NO DELETE without approval</forensic-rules>
```

This is the structural reinforcement of the methodology at every turn. The injection is invisible to the user (rendered as part of the system context) but always present in the model's input.

#### PreToolUse hook on Bash

Inspects the proposed Bash command before it executes. Used to enforce a second layer of denylist beyond `.claude/settings.json`'s static deny rules — e.g., dynamic checks like "does this command resolve to a binary in `/usr/local/bin/vhir`?"

#### PostToolUse hook on Bash

Fires after every Bash command. Runs `forensic-audit.sh` which:
1. Captures the full command string.
2. Captures the command's output.
3. Computes a SHA-256 of the output.
4. Writes a JSONL entry to `audit/claude-code.jsonl` with `ts`, `command`, `output_hash`, `exit_code`, `audit_id`.

This is **what gives a finding its HOOK-tier provenance.** Even if the LLM bypasses the MCP entirely and runs `vol.py` via raw Bash, the call is still logged and hashed, and a finding can cite the resulting `audit_id`.

### The `forensic-mcp.record_finding` gate logic, in plain English

When the LLM calls `record_finding(finding)`:

1. **Schema check.** Required fields present, types correct, lengths within limits.
2. **`audit_ids` array check.** Each ID is a string; the array is non-empty (unless the finding type is `exclusion`).
3. **For each `audit_id`:** look it up in `audit/<backend>.jsonl`. Doesn't exist anywhere? REJECT.
4. **For each artifact source:** the source filename must appear in the evidence registry (`evidence.json`). Not in registry? REJECT.
5. **Provenance tier classification.** For each `audit_id`, classify as MCP/HOOK/SHELL based on which log it came from. If all `audit_ids` are NONE (none found in any log AND no examiner-supplied `supporting_commands`): REJECT.
6. **Hash-chain resolution.** Walk back from the audit entry's `input_files` to its `output_files` to trace the data lineage. Sets `provenance_grade = FULL/PARTIAL`.
7. **Grounding score.** Check whether `forensic-rag-mcp.jsonl`, `windows-triage-mcp.jsonl`, `opencti-mcp.jsonl` are non-empty in this case's audit dir. Set STRONG (2+ consulted) / PARTIAL (1) / WEAK (0). Advisory — does NOT block.
8. **Compute content hash.** SHA-256 of the substantive text. Store on the finding.
9. **Stage as DRAFT.** Write to `findings.json` with status=`DRAFT`. Issue a finding ID like `F-alice-001`.
10. **Return** the response with `audit_id` for the record_finding call itself, the grounding score, the provenance tier(s), the discipline reminder for this turn, the data_provenance marker, and corroboration suggestions if the finding type is in the FK catalog.

### The forensic knowledge (FK) enrichment system

This is the **per-tool methodology injection layer**, defined in YAML and applied at MCP-response time.

Every cataloged tool (59 tools across 17 categories) has an FK YAML entry that specifies:
- **`caveats`** — methodology warnings always present in responses (e.g., "Shimcache and Amcache prove file PRESENCE, never execution")
- **`advisories`** — corroboration suggestions presented less often
- **`corroboration`** — "if you saw X with this tool, also check Y with that tool"
- **`field_meanings`** — what each output field means

The response envelope on every MCP call carries:
- `audit_id`
- `caveats`
- `advisories`
- `corroboration`
- `field_meanings`
- `discipline_reminder`
- `data_provenance`

**Token-budget decay.** To avoid spending the model's context window on the same caveats every call:
- `caveats` — always included
- `advisories` — included on the first 3 calls to a tool, then every 10th call
- `corroboration` — included on the first 3 calls, then on demand
- `discipline_reminder` — one of 15+ reminders, rotated deterministically modulo the session

The rotation list includes:
- "Absence of evidence ≠ evidence of absence."
- "Shimcache and Amcache prove file PRESENCE, never execution."
- "Prefetch proves execution but only the 8 most recent runs."
- "Event log gaps are common — do not assume tampering."
- "$LogFile and $UsnJrnl have rollover; recent activity overwrites older."
- "AppCompatCache entries are LIFO and OS-version dependent."
- "Browser InPrivate mode does not bypass DNS / proxy logs."
- "An empty Recycle Bin does not mean files were never deleted."
- "Persistence in a registry key proves intent, not necessarily execution."
- "WMI subscription persistence is invisible to autoruns."
- "Scheduled task XML may differ from the loaded in-memory representation."
- "Sysmon coverage is configuration-dependent; absence of an event class does not mean it didn't happen."
- "PowerShell ScriptBlock logging is OS-version dependent."
- "ETW providers can be disabled by an attacker with SYSTEM."
- "Process names can be spoofed; verify against the on-disk binary's signing/hash."

### The 22K-record forensic-rag knowledge base — sources

From `forensic-rag-mcp/sources.yaml`. 23 authoritative DFIR sources, totaling ~22,000 chunked records embedded into a local vector index:

| # | Source | Record count est. |
|---|---|---|
| 1 | Sigma rules (master + DFIR-Report) | ~3,000 |
| 2 | MITRE ATT&CK (techniques, sub-techniques, procedures) | ~600 |
| 3 | MITRE D3FEND | ~300 |
| 4 | Atomic Red Team | ~1,500 |
| 5 | LOLBAS | ~250 |
| 6 | LOLDrivers | ~1,800 |
| 7 | Elastic detection rules | ~1,200 |
| 8 | Splunk ES content | ~800 |
| 9 | Sentinel KQL queries | ~700 |
| 10 | KAPE targets + modules | ~400 |
| 11 | Hayabusa rules | ~3,700 |
| 12 | Volatility plugin docs | ~200 |
| 13 | SIFT tool documentation | ~300 |
| 14 | Sleuth Kit docs | ~150 |
| 15 | Plaso parser docs | ~250 |
| 16 | EZ Tools docs | ~200 |
| 17 | Velociraptor artifact docs | ~600 |
| 18 | Windows artifact references (Zimmerman, Mandiant, SANS blogs) | ~800 |
| 19 | TheHive analyzers | ~150 |
| 20 | MISP attribute types | ~200 |
| 21 | OpenCTI entity types | ~200 |
| 22 | DFIR Report writeups | ~3,000 |
| 23 | 13Cubed YouTube transcripts | ~700 |

Search returns top-K with source attribution. Filters: `source`, `source_ids`, `technique` (ATT&CK ID), `platform` (Windows/Linux/macOS).

### The 2.6M-record windows-triage baseline DB

A local SQLite database (typically) shipped with the platform, containing:
- Known-good Windows file paths and hashes across multiple OS versions, multiple patch levels, and multiple language packs.
- Known scheduled tasks per OS version.
- Known services per OS version.
- Known autorun entries (ASEPs).
- LOLBAS catalog (~250 entries).
- LOLDrivers catalog (~1,800 entries).
- Known DLL-hijack pairs.
- Known named pipes.

Total row count across all tables: ~2.6 million.

The baseline answers: "Is this Windows artifact known-good, known-bad, or UNKNOWN?" UNKNOWN is explicitly defined as neutral.

### Hayabusa 3,700+ Sigma rule auto-application

When EVTX is ingested into OpenSearch via `opensearch-mcp.ingest_evtx`, the post-ingest step automatically runs **Hayabusa** (the Sigma-based EVTX detection engine) with the bundled rule set (~3,700 rules at read time). Detection hits are written back as enriched documents in OpenSearch with `vhir.detection.rule_id`, `vhir.detection.severity`, etc.

This means a typical case workflow is: ingest EVTX → Hayabusa runs automatically → query opensearch for `detection.severity:high` to find immediate leads. No manual rule sweep required.

### The Examiner Portal (8 tabs, browser-based)

Per `docs/architecture.md` and the README's Portal section, the Examiner Portal is a single-page-application served by `sift-gateway` at `/portal/`. It is the primary review surface; the CLI is secondary.

**Authentication.** Challenge-response: the server sends a challenge; the browser does PBKDF2 derivation locally and HMAC-signs the challenge; the server verifies. Password never leaves the browser. Lockout after N failed attempts.

**The 8 tabs:**
1. **Findings** — review, edit, approve DRAFT findings.
2. **Timeline** — chronological view of timeline events.
3. **Evidence** — registered evidence files with SHA-256, last verified time, mount status.
4. **Audit** — per-MCP audit log search (filter by tool, examiner, time).
5. **Reports** — 6 report profiles + reconciliation status.
6. **Reasoning** — the append-only `log_reasoning` + `record_action` history.
7. **TODOs** — investigator-tracked TODOs (manual + AI-suggested).
8. **Case settings** — case ID, examiners, evidence dir, ledger location, password rotation.

**Keyboard shortcuts** for common operations (approve, reject, next finding, prev finding).

### The finding schema

From `forensic-mcp` server code and `approve.py` field handling:

```json
{
  "id": "F-alice-001",
  "title": "STUN.exe lateral movement via Net Use",
  "observation": "<what was seen — quoted/described from evidence>",
  "interpretation": "<what it means — analytical claim>",
  "confidence": "HIGH|MEDIUM|LOW|SPECULATIVE",
  "confidence_justification": "<why this confidence level>",
  "context": "<scope, host, time window>",
  "type": "finding|attribution|conclusion|exclusion",
  "audit_ids": ["sift-alice-20260520-007", "sift-alice-20260520-012"],
  "iocs": ["172.16.6.12", "STUN.exe", "hash:sha256:..."],
  "mitre_ids": ["T1021.002", "T1543.003"],
  "examiner": "alice",
  "created_by": "alice",
  "status": "DRAFT|APPROVED|REJECTED",
  "content_hash": "<SHA-256 of substantive text>",
  "approved_at": "<iso8601 UTC>",
  "approved_by": "alice",
  "modified_at": "<iso8601 UTC>",
  "examiner_modifications": {
    "<field>": {
      "original": "...",
      "modified": "...",
      "by": "alice",
      "at": "<iso8601>"
    }
  },
  "examiner_notes": [
    {"note": "...", "by": "alice", "at": "<iso8601>"}
  ]
}
```

**ID format.** `F-{examiner}-{NNN}`. Per-examiner prefix means two examiners working on the same case in parallel never collide — Alice produces F-alice-001, F-alice-002, ...; Bob produces F-bob-001, F-bob-002, ... Merge is conflict-free.

**Timeline event schema:**

```json
{
  "id": "T-alice-001",
  "timestamp": "<iso8601 UTC>",
  "description": "...",
  "source": "<source file or audit_id>",
  "auto_created_from": "F-alice-001",
  "examiner_modifications": {...},
  "status": "DRAFT|APPROVED|REJECTED",
  ...
}
```

Findings can auto-spawn timeline events via the `auto_created_from` linkage.

### Resource exposure vs Tool exposure for discipline items

MCP has two primitives for context delivery:
- **Tools** — active operations the LLM invokes when needed.
- **Resources** — passive read-only context the LLM can be pre-fed or query on demand.

Valhuntir exposes the 14 discipline items as MCP **Resources** by default (which is the cleaner abstraction — they're read-only methodology content, not actions). For MCP clients that don't fully support Resources, there's a `reference_mode="tools"` fallback that re-exposes the same items as tools.

This means in Claude Code (which supports Resources), the model gets the discipline items as background context. In a client without Resource support, it has to actively query them.

### The 24 vhir CLI commands

From the README's command reference:

**Password-gated (human-only) commands:**
- `vhir approve` — approve a DRAFT finding/timeline event
- `vhir reject` — reject a DRAFT item
- `vhir exec` — privileged exec
- `vhir evidence unlock` — unlock evidence for re-mount
- `vhir password set` / `vhir password rotate`
- `vhir review --verify` — re-derive HMAC and verify ledger

**General commands:**
- `vhir portal` — launch the Examiner Portal
- `vhir backup` / `vhir restore`
- `vhir case init` / `vhir case activate` / `vhir case list` / `vhir case status` / `vhir case migrate`
- `vhir review` — interactive review of DRAFTs
- `vhir todo` — TODO management
- `vhir evidence register` / `vhir evidence verify` / `vhir evidence list`
- `vhir export` / `vhir merge`
- `vhir report generate` / `vhir report save`
- `vhir audit log` / `vhir audit summary`
- `vhir service start` / `vhir service stop` / `vhir service status`
- `vhir config` — view/set config
- `vhir update` — self-update
- `vhir join` — join existing case as another examiner
- `vhir setup` — first-time setup

The split between password-gated and general commands matches the L1+L7 architecture.

### Audit trail implementation — JSONL per backend

Every MCP tool call writes a JSONL entry to a per-backend log under `audit/` in the case directory:

```
cases/INC-2026-0219/audit/
├── forensic-mcp.jsonl
├── case-mcp.jsonl
├── report-mcp.jsonl
├── sift-mcp.jsonl
├── forensic-rag-mcp.jsonl
├── windows-triage-mcp.jsonl
├── opencti-mcp.jsonl
├── opensearch-mcp.jsonl
├── wintools-mcp.jsonl
└── claude-code.jsonl       # PostToolUse hook captures every Bash command (Claude Code only)
```

**Entry schema** (verbatim from `commands/execute.py:160-171`):

```json
{
  "ts": "<iso8601 UTC>",
  "mcp": "<backend>",
  "tool": "<tool_name>",
  "audit_id": "{backend}-{examiner}-{YYYYMMDD}-{NNN}",
  "examiner": "<name>",
  "case_id": "<env VHIR_ACTIVE_CASE>",
  "source": "cli_exec",
  "params": {"command": "...", "purpose": "..."},
  "result_summary": {"exit_code": <int>, "output": "<N lines>; stderr: <first 200 chars>"},
  "elapsed_ms": <float>
}
```

`audit_id` is a stable cross-reference. The sequence number `NNN` resumes across process restarts (the backend reads the existing JSONL on startup, finds the max NNN for today's date, continues from there).

**`result_summary` truncates non-dict/list results to `str(result)[:500]`** (per `sift-common/audit.py:335-341`). The full raw output is preserved separately on disk as `output_file` / `full_output_path` per the FK-cataloged tools (per `sift-mcp/server.py:240-259`).

### Audit query commands

- `vhir audit log [--mcp <backend>] [--tool <name>] [--limit N]` — filter by backend/tool/limit
- `vhir audit summary` — aggregate view (tool call counts, time distribution, error rate)

### Bidirectional report reconciliation

Already covered above under `report-mcp`. The three reconciliation failure modes:
- `APPROVED_NO_VERIFICATION` — finding APPROVED but no ledger entry. Anomaly. Either approval happened without going through `approve.py`, or the ledger file was tampered with / deleted.
- `VERIFICATION_NO_FINDING` — ledger entry exists but the corresponding finding has been deleted or renamed. Suggests the finding was tampered with after signing.
- `DESCRIPTION_MISMATCH` — finding's substantive text differs from what was HMAC-signed. The mutation is post-signing, which means it's invisible to the original signature.

### Tooling / library stack

- **MCP server framework:** FastMCP (the Python MCP server library, Anthropic's reference impl).
- **HTTP gateway:** Starlette / Uvicorn.
- **HMAC / crypto:** Python stdlib `hmac`, `hashlib`, `secrets`.
- **PBKDF2:** Python stdlib `hashlib.pbkdf2_hmac`.
- **Sandbox:** bubblewrap (`bwrap`) — the Linux user-namespaces sandbox.
- **Storage:** filesystem (JSONL audit logs, YAML case state, JSON findings). Optional OpenSearch for evidence indexing.
- **Vector index for forensic-rag:** local embedding store (likely sentence-transformers + FAISS or similar; specific impl is in `forensic-rag-mcp/`).
- **Hayabusa:** the open-source Sigma-on-EVTX detection engine, bundled.
- **Velociraptor artifact docs:** ingested from Velociraptor's release artifact YAMLs.
- **CLI:** Click (Python).
- **Tests:** pytest.
- **Docs site:** MkDocs + mkdocs-material.
- **Containers:** Docker Compose for local dev; native install for SIFT VM.

### Deployment shape

The platform recommends three VMs:
- **SIFT VM (primary).** 16–32 GB RAM, 50–100 GB disk + evidence storage. Runs sift-gateway + forensic-mcp + case-mcp + report-mcp + sift-mcp + forensic-rag-mcp + windows-triage-mcp + opencti-mcp + opensearch-mcp. The "Lite" variant skips OpenSearch and shrinks to 8 GB RAM / 30 GB disk.
- **Windows VM (optional but recommended).** Runs wintools-mcp on :4624 HTTPS. Used for any Windows tool (EZ Tools, Sysinternals).
- **REMnux VM (optional).** Runs remnux-mcp on :3000 streamable-http. Used for malware analysis.

The three VMs communicate over a local network. The LLM client (Claude Code / Claude Desktop / LibreChat) connects to sift-gateway via MCP Streamable HTTP; if Windows tools are needed, the gateway routes the call to wintools-mcp on the Windows VM.

### What Valhuntir does NOT have (the gaps competitors are filling)

Per the wider research corpus this document draws on:

- **No closed-loop critic→revise agent.** The platform stages DRAFT findings, surfaces them to the examiner, and depends on the human to challenge weak findings. There is no separate AI agent that fires periodically to re-read evidence and challenge low-confidence findings before they reach the examiner.
- **No structural adversarial-evidence defense.** Valhuntir's `data_provenance: tool_output_may_contain_untrusted_evidence` marker is a flag the model is asked to respect. There is no separate sanitization layer that strips role tokens, normalizes BIDI / homoglyphs, or quarantines untrusted text into a separate namespace. The README explicitly notes that HITL is "the primary defense."
- **No multi-host live triage.** Valhuntir is post-mortem only — disk images, memory dumps, KAPE triage output. There is no integration with Velociraptor or any other live-host engine.
- **No per-finding AI pre-review.** Findings reach the examiner as raw DRAFT pile. There's no AI-driven first pass that flags weak findings, surfaces duplicates, or suggests merges before the human reviews.
- **No memory-plugin-aware reasoning chains.** Volatility is exposed via `sift-mcp.run_command` as raw shell. There's no agent that knows `psscan→pslist→diff` is the canonical chain for hidden processes and can run that as a structured workflow.
- **No real-time investigation HUD.** The Examiner Portal is a static-ish browser UI for review, not a live HUD streaming the agent's tool calls and reasoning.
- **No lightweight deployment for laptop-only use.** The Lite variant is 8 GB RAM / 30 GB disk. There's no sub-200MB / sub-2GB-RAM "investigate-this-image-on-my-Macbook" mode.
- **No closed claim-vs-evidence content verification.** The eight gates (schema, ID existence, evidence-registry path, provenance chain, grounding score, HMAC, reconciliation, IOC regex extraction) all stop one architectural step short of "open the cited tool output and check the finding's observation text appears there." A perfectly hallucinated finding, once approved, gets a valid HMAC.
- **No DFIR-specific adversarial benchmark.** There's no published harness measuring hallucination rate, false-positive rate, missed-finding rate against a ground-truth case set.
- **Claude-Code-only structural enforcement.** L3 (deny rules), L4 (sandbox), L9 (kernel sandbox) are Claude-Code-specific. Other MCP clients (Claude Desktop, LibreChat) get the MCP-level controls but not the kernel-level ones.

### Public commit / issue activity signal

- Total commits: 330 (as of read date, June 2026)
- Releases: v0.5.0 (Feb 28, 2026) → v0.6.1 (Apr 16, 2026)
- Dependabot active: HEAD commits are mkdocs-material version bumps
- Stars: 73 (by far the highest in the field)
- Forks: 15
- License: MIT

The maintenance posture: actively maintained by the author solo, with dependabot keeping deps current. No issue tracker activity surfaced in public view at read time, but the issue templates suggest the author expects community contributions.

---

## Section 3 — `marez8505/find-evil`

A public solo competitor build visible on GitHub. Decomposed here because it's one of the most complete non-Valhuntir, non-Protocol-SIFT public artifacts.

### Repo metadata

| Field | Value |
|---|---|
| URL | https://github.com/marez8505/find-evil |
| Stars / forks | 1 / 0 |
| License | MIT |
| Language split | Python 63.4%, HTML, Shell |
| Last commit | June 2026 (recent) |
| Architecture pattern | "Direct Agent Extension" with multi-phase pipeline (no MCP server) |

### Stated purpose / target user (verbatim from README)

The README describes the project as an **"autonomous DFIR agent"** that "executes five sequential phases with self-correction" — building on top of Protocol SIFT's POC by adding structure on top of vanilla Claude Code.

### Architecture decomposition

**Five-phase architecture, each with its own self-correction step:**

```
Phase 1 — Triage:          identifies evidence type, OS, time range
Phase 2 — Disk Timeline:   extracts MFT, identifies suspicious paths
Phase 3 — Memory Analysis: runs Volatility plugins, detects injected code
Phase 4 — Persistence & Artifacts: checks registry keys, scheduled tasks, Prefetch
Phase 5 — Correlation:     cross-references findings across sources
```

Each phase produces JSON output, persisted to disk, and then "evaluated" before the next phase begins. The "self-correcting loop" re-runs phases when "logical inconsistencies emerge."

### Specific design choices and what each signals about user pain

| Choice | Pain it signals |
|---|---|
| 5 explicit phases | Pain: vanilla Claude Code wanders; explicit phasing forces sequential discipline. |
| Per-phase self-correction (re-run if inconsistent) | Pain: a single shot per phase produces brittle output. Author wants retry-with-adjusted-params. |
| JSON output per tool with SHA-256 of output + token estimate | Pain: audit-trail credibility (the SHA-256) + cost visibility (the token estimate). |
| Flask web UI | Pain: terminal-only review is friction for non-CLI users. |
| Bound to 127.0.0.1 | Pain: accidental exposure of the UI to a network. |
| bcrypt password hash in `web/.env` | Pain: someone-else-on-my-laptop threat model. |
| `HttpOnly` + `SameSite=Strict` cookies | Pain: session hijack / CSRF. |
| 5 login attempts per 5-min window per IP | Pain: brute-force. |
| Local-only assets (no CDN) | Pain: external dependencies in air-gapped envs. |

### Tooling / library stack

- Python with Claude Agent SDK (no MCP server)
- Flask for the web UI
- bcrypt for password hashing
- WeasyPrint (likely, given the Protocol SIFT baseline) for PDFs

### Audit / logging story

Every MCP tool invocation is logged with:
- timestamp
- arguments
- **SHA-256 of output**
- **token estimate**

The token estimate is a notable touch — most submissions don't track LLM cost. This signals an author who watched their bill.

### Constraint / security story

- Flask bound to `127.0.0.1` only.
- bcrypt-hashed password in `.env`.
- HttpOnly + SameSite=Strict cookies.
- Rate limiting on login.
- No CDN, no external assets.

Notable: no MCP server, no HMAC ledger, no kernel sandbox. The security model is "single-user laptop" — not "multi-examiner with cross-examination risk."

### Self-correction story

Per the README, each phase has a self-correcting loop:
1. Run the phase's tools.
2. Evaluate the output.
3. If "logical inconsistencies emerge," re-run with adjusted parameters.
4. Continue when consistent.

The exact "logical inconsistency" detection is not specified in the public README — likely heuristic / LLM-based.

### Report / output story

JSON outputs per phase + presumably a final aggregated report via the Flask UI. No mention of multiple report profiles.

### Public commit / issue activity signal

- 1 star, 0 forks.
- Recent commits as of June 2026.
- Solo build.
- MIT licensed.

### What it does NOT do

- No MCP server (direct Claude Agent SDK calls).
- No HMAC-signed approval ledger.
- No multi-examiner support.
- No structured finding schema (per README — output is JSON tool dumps).
- No 22K forensic RAG.
- No kernel sandbox.
- No published accuracy benchmark.

---

## Section 4 — Other competitor builds visible publicly

This section decomposes the other named competitor repos surfaced via GitHub topic searches on `find-evil`, `protocol-sift`, `sift-sentinel`, `sift-mcp` between April and June 2026. **Conservative public-build count: ~60 GitHub repos as of 2026-06-02.** Of those, ~30 have meaningful READMEs and code. The most distinctive are decomposed below.

This is not a ranking. It is a survey of the design space. Each entry tells you what the build's distinctive choice is and what that choice signals.

### VALKYRIE — `elchacal801/valkyrie`

| Field | Value |
|---|---|
| URL | https://github.com/elchacal801/valkyrie |
| Pattern | Custom MCP server + Claude Code |
| Wedge | Structured Analytical Reasoning (Analysis of Competing Hypotheses, US IC doctrine) |
| Maturity | Functional — 81 tests, sample reports, accuracy report shipped |
| Size | 10,847 KB |
| Last commit | 2026-06-01 |

**Distinctive choice:** Imports US Intelligence Community analytical doctrine — specifically **Analysis of Competing Hypotheses (ACH)** — into the agent's reasoning shape. Findings carry 3-tier evidence labels: `CONFIRMED` / `INFERRED` / `UNVERIFIED`. The README explicitly states: *"Most forensic AI agents are tool runners — they wrap forensic tools behind an LLM and execute them in sequence. VALKYRIE is an analytical reasoner — it applies structured analytic techniques adapted from US Intelligence Community doctrine to investigate incidents with hypothesis testing, evidence tiering, and multi-layer self-correction."*

**Scope:** Host evidence + cloud plane (Entra ID / M365). Notable as the only public submission integrating cloud-identity logs into the same workflow as host disk/memory.

**What it signals:** author treats forensic investigation as an analytic-reasoning problem rather than a tool-execution problem. ACH is from Richards Heuer's *Psychology of Intelligence Analysis* (CIA, 1999) — a deliberate import of a 60-year-old analytic tradecraft into LLM agent design.

### foveal-dfir — `Hokutoman00/foveal-dfir`

| Field | Value |
|---|---|
| URL | https://github.com/Hokutoman00/foveal-dfir |
| Pattern | Custom MCP, structurally different verifier |
| Wedge | Blind independent grader + machine-cadence detection |
| Maturity | Functional — 13 verifier modules; validated against ROCBA case (4,818 findings analyzed) |
| Size | 3,350 KB |
| Last commit | 2026-05-30 |

**Distinctive choice 1: Blind independent grader.** A second agent reviews findings without seeing the first agent's reasoning or any anchoring text — only the raw evidence. To reach `CONFIRMED` status, **N ≥ 2 distinct sources must agree** in the grader's blind review. Implemented in code, not prompt.

**Distinctive choice 2: Instruction-text quarantine.** Free-text fields suspected of containing instruction-shaped tokens (`<system>`, "ignore previous", etc.) are extracted into a separate namespace and rendered with `[UNTRUSTED]` markers.

**Distinctive choice 3: Cadence detector.** Heuristic that flags `MACHINE_PACED` vs `HUMAN_LIKELY` action sequences — designed to detect AI-driven attackers (GTG-1002 style). Tool-call interarrival times below a threshold trigger MACHINE_PACED.

**What it signals:** the author reads the hackathon's stated motivation literally — the Anthropic GTG-1002 disclosure described an autonomous AI attacker. The defender should plausibly recognize one. The cadence detector is the only public artifact directly addressing this.

### GLAIVE — `aliyaalias19/glaive`

| Field | Value |
|---|---|
| URL | https://github.com/aliyaalias19/glaive |
| Pattern | Typed evidence graph + Custom MCP |
| Wedge | "Hallucination architecturally impossible" via typed graph paths |
| Maturity | Functional — 327 tests passing, 5 bypass attack tests |
| Size | 220 KB |
| Last commit | 2026-05-29 |

**Distinctive choice:** Every finding must correspond to a path in a **typed evidence graph**. The graph's node types are evidence artifacts (PEs, registry keys, log events). Edges are typed relations (`spawned_by`, `signed_by`, `wrote_to`). A finding without a corresponding graph path **cannot be expressed**. The README states the wedge verbatim: *"GLAIVE makes hallucination architecturally impossible by forcing every finding to correspond to a path in a typed evidence graph."*

**The 5 bypass attack tests** are deliberate attempts to make the LLM produce a finding without a graph path. All 5 are tested to fail.

**What it signals:** author treats hallucination as a **type-system problem**. The unrepresentable-state principle from category theory ports into a forensic agent.

### Verdict — `TimothyVang/Verdict`

| Field | Value |
|---|---|
| URL | https://github.com/TimothyVang/Verdict |
| Pattern | Mode-aware dual-LLM verifier-gateway |
| Wedge | Two AI models cross-check each other (Qwen3 vs GLM-4.5-Air) |
| Maturity | Functional, structured build plan |
| Size | 2,064 KB |
| Last commit | 2026-05-25 |

**Distinctive choice 1:** Dual LLM cross-check. Every finding is independently produced by Qwen3 and GLM-4.5-Air, then compared. Disagreement → flagged for human.

**Distinctive choice 2:** Modes are locked at `case_init`: `cloud` (both models in the cloud), `airgap` (both local), `dual` (one cloud, one local). The mode choice is bound to the case so it cannot be silently downgraded mid-case.

**Distinctive choice 3:** HMAC-signed audit (matching the Valhuntir pattern).

**Distinctive choice 4:** FOR500 rule — every finding must cite ≥2 artifacts to be eligible for promotion past `INFERRED`.

**What it signals:** author is solving for "two models disagreeing IS the verification signal" — independent cross-check at the model layer rather than at the tool layer.

### find-evil-sleuth — `WilBtc/find-evil-sleuth`

| Field | Value |
|---|---|
| URL | https://github.com/WilBtc/find-evil-sleuth |
| Pattern | Postgres-substrate multi-agent |
| Wedge | Database as the substrate; live judge `SELECT` queries during demo |
| Maturity | Production-shape — 14 MB repo |
| Size | 14,009 KB |
| Last commit | 2026-06-02 |

**Distinctive choice 1: Postgres 17 + 11 extensions as the substrate.** All evidence + findings + audit + reasoning live in Postgres. Extensions in use: pgvector (embeddings for FK), Apache AGE (graph queries), TimescaleDB (timeline), pgaudit (database-level audit), pg_jsonschema (schema validation in DB), pg_partman (partitioning).

**Distinctive choice 2: The architectural guardrail is a Bash PreToolUse hook.** The README states verbatim: *"The architectural guardrail is not a system prompt — it is a Bash PreToolUse hook that exits 1 on any command other than `./bin/sb` or `./bin/es`, enforced at the Claude Code hook layer before the shell sees the command."*

So the LLM can only execute two binaries:
- `./bin/sb` — the SQL submitter
- `./bin/es` — the evidence-search wrapper

Everything else returns exit 1 before the shell runs.

**Distinctive choice 3: Rust message broker.** Inter-agent messages flow through a Rust broker.

**Distinctive choice 4: Rootless podman + seccomp filters.** Containers, not bwrap.

**Distinctive choice 5: BLAKE3 hashes (not SHA-256).**

**Distinctive choice 6: Demo pattern.** Judge runs `SELECT` queries against the running Postgres mid-demo to validate findings live.

**What it signals:** author imports DBA discipline. The database is not just storage — it is the constraint surface, the audit surface, the verification surface, and the demo surface.

### provenance — `vinodhalaharvi/provenance`

| Field | Value |
|---|---|
| URL | https://github.com/vinodhalaharvi/provenance |
| Pattern | Go-native typed arrows (NO MCP) |
| Wedge | "Misconfigurations are not expressible" via typed Go structs |
| Maturity | WIP — 25 unit tests, fixture-driven |
| Size | 54 KB |
| Last commit | 2026-05-13 |

**Distinctive choice:** Skip MCP entirely. The LLM emits Go structs that are validated at the type-system level. The README states verbatim: *"Existing AI-assisted DFIR tooling (Protocol SIFT and similar) gives an LLM agent a generic `execute_shell_cmd` plus a long system prompt and hopes it stays on the rails. The hackathon brief flags this as the source of the autonomy gap: hallucination, evidence spoliation risk, loops that don't terminate."*

The wedge is "replace `execute_shell_cmd` + prompt with typed Go structs where misconfigurations don't compile."

**Other notable choice:** independent critic agent — separate from the investigator agent.

**What it signals:** Go's type system is treated as the constraint architecture. Strong typing as anti-hallucination.

### sift-bench — `aksoni/sift-bench`

| Field | Value |
|---|---|
| URL | https://github.com/aksoni/sift-bench |
| Pattern | Benchmark + eval framework first, agent second |
| Wedge | Negative-assertion benchmark + deterministic replayable scorer |
| Maturity | Functional — Run 6: 5/5 critical, 3/3 FP traps, 0.9833 score |
| Size | 1,313 KB |
| Last commit | 2026-06-01 |

**Distinctive choice 1: Negative assertions.** Ground truth includes "behaviors that did NOT occur" — the agent must correctly NOT-report them. Standard forensic benchmarks only score positive findings.

**Distinctive choice 2: FP-trap cases.** Cases deliberately designed to elicit common forensic false positives. The score includes "FP traps avoided."

**Distinctive choice 3: Committed LLM-judge verdict cache.** The LLM-judge that scores submissions is cached deterministically — every replay produces the same score.

**What it signals:** author treats the benchmark as the primary artifact, the agent as illustrative. Inverted shape.

### SIFTGuard — `Nafsgerman/siftguard`

| Field | Value |
|---|---|
| URL | https://github.com/Nafsgerman/siftguard |
| Pattern | Custom MCP, 5 orchestrators on 1 typed MCP |
| Wedge | "Court-defensible" framing + 19-col SQLite auditentry table + 15/15 spoliation tests |
| Maturity | Production-shape — Devpost link live, 4:42 demo video at https://www.youtube.com/watch?v=ALmArb3lGR8 |
| Size | 6,057 KB |
| Last commit | 2026-06-01 |

**Distinctive choice 1:** 19-column SQLite audit-entry schema — denser than the typical JSONL approach. Columns include `ts`, `examiner`, `mcp`, `tool`, `args_json`, `result_summary`, `exit_code`, `elapsed_ms`, `output_sha256`, `evidence_paths_json`, `finding_ids_json`, `audit_id`, `case_id`, `tool_version`, `previous_audit_hash`, `chain_hash`, `signature`, `verified`, `notes`.

**Distinctive choice 2:** 15-out-of-15 spoliation tests pass. The threat model is explicit and the test corpus is exhaustive.

**Distinctive choice 3:** F1 scores across 3 datasets reported.

**Distinctive choice 4:** LLM-agnostic — works with Claude, GPT, local models.

**What it signals:** author wants legal-grade defensibility but doesn't claim the legal vocabulary (no Daubert / FRE 901 framing in code). "Court-defensible" is in the marketing layer.

### siftguard demo video

YouTube link: https://www.youtube.com/watch?v=ALmArb3lGR8 (4:42 demo). Public as of 2026-06-01. The video is the first public Find Evil! demo confirmed live.

### MemoryHound — `saivarun3407/DFIR-AI`

| Field | Value |
|---|---|
| URL | https://github.com/saivarun3407/DFIR-AI |
| Pattern | Custom MCP + Claude Code skills/agents/hooks + LangGraph FSM |
| Wedge | "Drop-in DFIR for Claude Code" — 31 typed tools / 14 skills / 4 subagents / 5 hooks / 20-node IR graph |
| Maturity | Production-shape — 360 tests CI green, ~10K LoC |
| Size | 740 KB |
| Last commit | 2026-05-30 |

**Distinctive choice 1:** Multi-framework support (NIST/ISO/PICERL/ATT&CK/D3FEND). Findings can be tagged with framework citations across all five.

**Distinctive choice 2:** 20-node IR graph (LangGraph FSM) — the most explicit state machine in the field.

**Distinctive choice 3:** SHA-256 chained audit (each entry includes the previous entry's hash, like Bitcoin's blockchain).

**Distinctive choice 4:** "Drop-in for Claude Code" framing — the install is `~/.claude/`-shaped, similar to Protocol SIFT's deployment pattern.

**What it signals:** author imports the PAI (Personal AI Infrastructure) `.claude/` configuration pattern. Optimizes for Claude Code as the deployment target.

### W.A.R.V.I.S. — `WooYoungSang/warvis-findEvil`

| Field | Value |
|---|---|
| URL | https://github.com/WooYoungSang/warvis-findEvil |
| Pattern | Go orchestrator + Python MCP + Gemma 4 (local Ollama) |
| Wedge | Single Go binary control plane + airgap focus |
| Maturity | Production-shape |
| Size | 42,724 KB |
| Last commit | 2026-05-09 |

**Distinctive choice 1:** 5-state Hunt FSM with **compile-time tool whitelist.** Tools that aren't in the whitelist literally cannot be invoked.

**Distinctive choice 2:** Budget-preserving resume + kill-switch. If the agent runs out of token budget mid-investigation, the state is durable and resumable.

**Distinctive choice 3:** Local LLM only (Gemma via Ollama). Airgap-compatible.

**What it signals:** author optimizes for air-gapped deployment. The constraint is regulatory/operational, not model-quality.

### EvidenceChain — `tejasprasad2008-afk/evidencechain`

| Field | Value |
|---|---|
| URL | https://github.com/tejasprasad2008-afk/evidencechain |
| Pattern | Custom MCP, 21 typed tools |
| Wedge | 7 named contradiction detectors |
| Maturity | Functional |
| Size | 144 KB |

**Distinctive choice:** Seven contradiction detectors named in code:
- `TIMESTAMP_PARADOX` — claimed event time outside evidence-reasonable bounds
- `EXECUTION_OVERCLAIM` — claim of execution when only presence is proven
- `GHOST_PROCESS` — process named in finding doesn't appear in `pslist`/`psscan`
- (and 4 more)

4-pass self-correction. "Proves" column on each finding distinguishes execution from presence.

**What it signals:** author has a forensic-discipline checklist in code form. The "Proves" column is a direct nod to the FOR508 maxim "presence ≠ execution."

### SIFT-Guard (separate from siftguard) — `chang6chang/SIFT-Guard`

Distinct from `Nafsgerman/siftguard`. Custom MCP + analyst/validator subagents. Validator subagent has **deliberately restricted tool surface** — it can read but not run heavy tools. 4 hash-chained JSONL logs.

### sgharlow's find-evil — `sgharlow/find-evil`

| Field | Value |
|---|---|
| URL | https://github.com/sgharlow/find-evil |
| Pattern | Custom MCP |
| Wedge | Evidence Integrity Enforcer — background daemon re-hashes every 30s + before every tool call |
| Maturity | Production-shape |
| Size | 61,774 KB |

**Distinctive choice:** background daemon that re-computes SHA-256 of evidence files every 30 seconds AND before every tool call. UUID-linked audit. DRS confidence gate.

**What it signals:** paranoid about evidence tampering during the investigation. Continuous attestation rather than at-rest attestation.

### ThreatPipe v2 — `Prathameshsci369/ThreatPipe-v2-Autonomous-SIFT-IR-Agent-with-MCP`

LangGraph + Custom MCP. **4-Lens cross-referencing:** Hacker / Temporal / Kill Chain / Analyst. Persistent "Hacker Mindset Graph." Predicts next ATT&CK move. Mistral backend.

**What it signals:** author wants to model the attacker's reasoning explicitly, then defend by anticipating it.

### Aura-Forensics — `kdsecdev/Aura-Forensics`

Custom MCP + Triangulation Engine. **DKOM / unlinked-EPROCESS rootkit detection** — cross-references `pslist` vs `psscan` to find malware Volatility's `malfind` misses. 19 GB memory dump physical scrape.

**What it signals:** author has a specific deep-memory wedge — kernel rootkits. Single-purpose excellence over breadth.

### Forenly — `Forenly/protocol-sift-dfir`

**Cyber-physical robot forensics.** Compromised ROS 2 robots, SLAM logs, motion control overrides. Cross-leverages Splunk Agentic Ops + UiPath Maestro entries. Public Discord.

**What it signals:** author refuses the SIFT-Windows-default assumption and stakes a niche claim (OT / robotics).

### tracelock find-evil — `voidd0/tracelock-find-evil`

Read-only harness. Per-finding `{event_id, tool, confidence, SHA-256 hash, self-check, final status}`. Includes a `splunk-ops/` extension with 3-case Splunk accuracy suite (all P=R=1.0). Public Devpost demo URL.

### find-evil-jarvis — `Turbo31150/find-evil-jarvis`

**Parallel multi-agent** (`asyncio.gather`). 4 specialist agents (IOC / phishing / malware-pattern / log-anomaly) in <100ms. FastAPI. Functional but **archived** — author appears to have abandoned mid-build.

### Lona44/find-evil-ir-agent

Multi-agent LangGraph + misalignment-eval layer. Investigator → Validator → Reporter pipeline. "Fabricated artefact citations" framed as the moat. Scaffold (declared).

### vigia-cases — `annatchijova/vigia-cases`

**Dataset only.** 10 real DFIR cases (NIST CFReDS, DFRWS, Digital Corpora, Ali Hadi, Volatility Foundation) in a canonical "VIGÍA" format with ground truth, IOCs, MITRE TTPs, and Peirce semiotic classification. README states the classification was applied by Rob T. Lee. Apache-2.0.

**What it signals:** dataset-as-submission shape. Lateral move — provide the ground truth, let others build agents that score against it.

### ProofSIFT — `Vasanthadithya-mundrathi/SANS-FIND-EVIL`

Custom MCP. "Evidence-gated autonomous DFIR." WIP.

### sift-sentinel (multiple authors)

The `sift-sentinel` name was used by at least six independent builders, each with a different wedge:
- `marez8505/sift-sentinel` — Custom MCP + skills, self-correcting triage
- `MukundaKatta/sift-sentinel` — Custom MCP, simulated backend, runs offline with no API key, "60-second proof," SHA-256 ledger
- `vandit98/sift-sentinel` — Custom MCP, "Architecture Pattern: Custom MCP Server"
- `scastile/sift-sentinel` — generic "FIND EVIL submission" stub
- `FlemingJohn/sift-sentinel` — MCP server suite + orchestration + terminal UI
- `charanbobby/sift-sentinel` — WIP stub

**What it signals:** "sift-sentinel" became a generic Find-Evil-shaped naming pattern; builders converge on the name independently.

### MuneebX65/protocol-sift-agent

Custom MCP, "safe typed functions." WIP.

### samaritan0/dfir-agentic-suite

Claude skills + 4 MCP servers. 5 forensic skills, IOC extractor, Windows artifacts, timeline merger, YARA gen. **9 stars, 4 forks** — second-highest after Valhuntir in the field.

### Architectural pattern distribution across the field

Across ~30 builds where README and code were read:

| Pattern | Share |
|---|---|
| Custom MCP server (typed read-only forensic tool wrappers) | ~85% |
| Multi-agent / LangGraph layered on Custom MCP | ~30% |
| Direct Extension of Protocol SIFT (skills + hooks, no custom server) | ~15% |
| Novel substrate / not MCP (Go arrows, Postgres, FSM) | ~5% |
| Dataset / benchmark only | ~5% |

The default recipe is dead obvious to every builder: read Protocol SIFT's POC → notice it gives the LLM raw `execute_shell_cmd` → wrap each SIFT tool as a typed MCP function → bolt on a self-correction validator → claim "architectural" guardrails.

### Wedge distribution across the field

| Wedge | Approx count |
|---|---|
| Custom MCP server with typed read-only tools | ~25 |
| Self-correction / validator loop | ~22 |
| Spoliation resistance / SHA-256 evidence sealing | ~18 |
| Hash-chained or JSONL audit trail | ~15 |
| "Architectural" (not prompt-based) guardrails | ~14 |
| Hallucination-prevention via citation enforcement | ~12 |
| MITRE ATT&CK / sub-technique mapping | ~10 |
| Two-agent investigator/validator split | ~9 |
| Multi-agent LangGraph pipeline | ~8 |
| Confidence scoring + retract/promote rules | ~8 |
| Replayable / deterministic / no-API-key offline mode | ~6 |
| Benchmark / accuracy framework as primary deliverable | 3 |
| Negative-assertion scoring | 1-2 |
| Dual-LLM cross-check | 2 |
| Local-only LLM (Ollama/Gemma/Mistral) | 4 |
| Cross-OS (Windows + macOS + Linux artifacts) | 2 |
| Adversary-cadence detection | 1 |
| Cloud-plane forensics (Entra ID / M365) | 1 |
| Tier-1 SOC / Splunk operator workflow | 1 |
| Live-system EDR-style response | 0 visible |

### Wedges that appear absent or near-absent in the visible field

(From the public-builder discourse research.)

- Court-admissibility / Daubert / FRE 901 framing
- EU AI Act / GDPR compliance evidence for AI findings
- Examiner notes / chain-of-custody form-fill
- BEC / M365 unified audit log triage
- Insider-threat / data-exfil specific
- Live-host / live-response
- Cyber-physical (1 — Forenly)
- Cloud-only (no host disk image)
- Mobile (iOS / Android)
- Network-only (PCAP-first, no host)
- Cost-aware / token-budget-optimal agent loop
- LOLBAS-catalog-driven hunt
- Real-time stream (Kafka / Splunk live tap)
- Adversary-emulation pair: attacker + defender in same repo
- Multi-host correlation across an org
- UEFI / firmware rootkit
- Privacy-preserving forensics (responder cannot see PII)
- Plain-English executive summary
- Cost-of-investigation report

---

## Section 5 — Existing forensic MCP servers (non-hackathon prior art)

This section catalogs forensic MCP servers built independently of the hackathon, primarily over the late-2025 / early-2026 period as MCP adoption took off in the security community.

### bornpresident/Volatility-MCP-Server

| Field | Value |
|---|---|
| URL | https://github.com/bornpresident/Volatility-MCP-Server |
| Author | Vishal Chand |
| Role | Memory forensics via Volatility 3 |
| Plugins exposed | 14 (per prior research; per the README it "exposes Volatility plugins as MCP tools") |
| Scope | Memory dumps only |

**What it does.** "Bridges Volatility 3 with LLMs through MCP." Plugins exposed include: `pstree`, `pslist`, `psscan`, `netscan`, `malfind`, `dlllist`, `filescan`, `cmdline`, `handles`, `memmap`, plus custom plugin exec and dump discovery.

**What it signals.** Single-purpose, narrow scope. Demonstrates that exposing Vol3 as MCP tools is a sensible primitive — but the project does not wrap the *reasoning* around Vol3 (which plugins to call when, how to interpret results, how to pivot). That layer is the LLM's responsibility.

**Setup.** Clone, install Python deps, configure Volatility path, register as an MCP server in Claude Desktop / Claude Code config.

### OMGhozlan/Volatility-MCP-Server

Alternative Volatility 3 MCP wrapper. Same conceptual shape. Demonstrates that "expose Vol3 plugins as MCP tools" is a pattern multiple authors converge on.

### socfortress/velociraptor-mcp-server

| Field | Value |
|---|---|
| URL | https://github.com/socfortress/velociraptor-mcp-server |
| Stars / forks | 39 / 7 |
| License | AGPL-3.0 |
| Tools | 11 |
| Auth | JWT token, automatic refresh |

**The 11 tools** (verbatim from README):
- `AuthenticateTool` — test connection
- `GetAgentInfo` — retrieve client details by hostname
- `RunVQLQueryTool` — execute custom VQL queries
- `ListLinuxArtifactsTool` — list available Linux artifacts
- `ListWindowsArtifactsTool` — list available Windows artifacts
- `CollectArtifactTool` — initiate artifact collection from clients
- `GetCollectionResultsTool` — retrieve completed collection results (with retry logic)
- `CollectArtifactDetailsTool` — obtain artifact specifications and parameters
- `ListLinuxArtifactNamesTool` — simple Linux artifact name listing
- `ListWindowsArtifactNamesTool` — simple Windows artifact name listing
- `FindArtifactDetailsTool` — search artifact specifications by name

**What it does.** Exposes Velociraptor (the live-host forensic / threat-hunting engine) via MCP. Velociraptor uses VQL (Velociraptor Query Language) — the wrapper exposes both pre-built artifacts and arbitrary VQL execution.

**What it signals.** Live-host triage is feasible as MCP. The architecture is conventional: the MCP server is a thin wrapper around Velociraptor's gRPC API; JWT auth + HTTP/2 retry handling are infrastructure niceties.

**License note.** AGPL-3.0 — not MIT or Apache 2.0. Reuse in a hackathon submission would require either dual licensing or the AGPL inheritance. The hackathon rules require MIT or Apache 2.0 for the submission, so any submission incorporating this code as a library has a licensing question to resolve.

### mgreen27/mcp-velociraptor

Alternative Velociraptor MCP bridge. Earlier-stage. Demonstrates that multiple Velociraptor MCPs exist.

### DFIR-IRIS MCP server — dfirmesi-iris-mcp-server

35 functions + KPI metrics. Provides MCP access to DFIR-IRIS (the open-source incident response case-management platform). CRUD over IRIS cases + natural-language query.

**What it signals.** Case management can be MCP-fronted. Overlaps significantly with Valhuntir's case-mcp + report-mcp + forensic-mcp triad.

### x746b/winforensics-mcp

KALI Windows forensics MCP. Tool-execution wrapper. No finding gate.

### axdithyaxo/mcp-forensic-toolkit

Generic forensic toolkit MCP. Tool-execution wrapper.

### GitMCP — idosal/git-mcp

| Field | Value |
|---|---|
| URL | https://github.com/idosal/git-mcp |
| Stars | ~2k |
| License | Apache 2.0 |
| Pattern | Context-injection MCP for documentation |

**What it does.** A remote MCP server that transforms any GitHub project (repo + GitHub Pages) into a documentation hub. AI tools that connect to GitMCP get up-to-date docs and code injected into context when querying.

**Stated purpose** (verbatim from README): *"Put an end to code hallucinations!"*

**Mechanism.** Not verification. **Prevention by improved context.** Instead of letting the LLM generate from training-data memory (which is stale), GitMCP feeds the LLM the actual current docs at query time.

**Deployment forms.** `gitmcp.io/{owner}/{repo}` URL pattern. Add as MCP server in IDE. No install.

**What it signals.** "Better context" as the hallucination-mitigation strategy. This is the opposite end of the spectrum from architectural-gate approaches — instead of detecting hallucinated outputs, prevent them by ensuring the model always has accurate context.

**Relevance to Find Evil!** Not directly applicable as a forensic tool, but is the closest *named* OSS MCP server whose explicit pitch is "end hallucinations." Pattern reusable: forensic-rag-mcp in Valhuntir is conceptually GitMCP-shaped — inject authoritative DFIR knowledge into context instead of relying on the LLM's training-data recall.

### Other MCPs in the security space worth knowing about

- **AppliedIR/forensic-rag** (in sift-mcp monorepo) — 22K-record semantic search across Sigma/MITRE/Atomic/Elastic/Splunk/LOLBAS/etc. 3 tools. Bench-sets the knowledge layer for the field.
- **mcp-server-wazuh** — Wazuh SIEM MCP wrapper. Used by SocTalk (Section 7).
- **mcp-server-cortex** — TheHive Cortex analyzer MCP. Used by SocTalk.
- **mcp-server-misp** — MISP threat intel MCP. Used by SocTalk.
- **mcp-server-thehive** — TheHive case-mgmt MCP. Used by SocTalk.
- **SecurityCopilotMCPServer** (jguimera) — community MCP for Microsoft Security Copilot artifact development.

### Public MCP servers that have NOT been built (per the prior-research scan)

Notably absent from the OSS landscape as of 2026-06-02:
- A standalone Plaso super-timeline MCP exposing log2timeline / psort structurally (rather than as raw shell wrapped in MCP).
- A standalone EZ Tools / Zimmerman tools MCP (only Valhuntir's wintools-mcp covers it, and that's tightly coupled to the broader platform).
- A standalone Hayabusa Sigma detection MCP.
- A YARA-rule-generation MCP that emits rules from observed IOCs and tests them in-process.
- An adversarial-evidence sanitizer MCP — strips/quarantines free-text fields before LLM consumption.
- A live-IR triage MCP that targets Velociraptor and adds an investigative agent layer above raw VQL.

---

## Section 6 — Vendor "AI SOC" / agentic-DFIR commercial products

The hackathon is happening alongside an aggressive commercial-vendor land-rush into agentic security tooling. This section catalogs the major vendor products with public positioning as of 2026-06-02. Pure descriptive. Not a recommendation about which to copy or compete with.

### CrowdStrike Charlotte AI + Charlotte Agentic SOAR

**Positioning.** "Agentic SOC orchestration layer of the Falcon platform." Charlotte Agentic SOAR was announced November 5, 2025. Charlotte AI is positioned as an "Agentic Analyst for Cybersecurity."

**What it does.** Per CrowdStrike's official material: Charlotte Agentic SOAR orchestrates AI-powered agents across the security lifecycle, "connecting context and data so they can reason and act dynamically together in real time under analyst command, and by uniting native, custom-built, and trusted third-party agents in a single coordinated system."

**Autonomy claim.** "Machine-speed response under analyst command." Bounded autonomy — human is the orchestrator, agents act within guardrails.

**Autonomy level.** Tier 1-2 SOC operations, with explicit human oversight on Tier 3 actions. Hard guardrails on credential changes, host quarantine, mass-deploy.

**Deployment model.** SaaS, integrated into Falcon platform. No on-prem option.

**Charlotte AI AgentWorks Ecosystem.** Announced March 2026. Partner ecosystem with Accenture, AWS, Anthropic, Deloitte, Kroll, NVIDIA, OpenAI, Salesforce, Telefónica Tech. Customers get a no-code agent-builder platform with frontier models, can ship custom security agents into the Falcon ecosystem.

**Architectural shape (per public docs).** Multi-agent. MCP-compatible. Sandboxed agent execution. Centralized policy / governance layer ("bounded autonomy"). Agent-to-agent messaging within the orchestrator.

### Microsoft Security Copilot + Sentinel MCP Server

**Positioning.** "Agentic SOC Era." Sentinel MCP Server announced late 2025, GA in early 2026.

**What it does.** Per Microsoft Learn: the Sentinel MCP Server "provides access to intelligence across internal and external data sources and automates investigations." It "allows teams to convert natural-language explorations into full KQL queries or Spark Notebook cells."

**MCP scope.** The Sentinel MCP exposes:
- A search tool collection (find relevant tables, retrieve data)
- An entity-analysis tool collection
- An incident-triage tool collection
- A threat-hunting tool collection
- An agent-creation tool collection (used to build custom Sentinel agents in Copilot Studio)

**Clients supported.** Security Copilot, GitHub Copilot, Azure Foundry, ChatGPT Enterprise.

**Autonomy claim.** "AI-driven agents can perform advanced reasoning over security telemetry."

**Autonomy level.** Investigation + KQL generation + entity analysis under analyst review. Agent-creation tools allow customers to build their own agents on top.

**Deployment model.** Azure-resident. Sentinel data lake + MCP server + Security Copilot.

**Recent development (Feb 2026):** Microsoft Copilot data connector for Sentinel — sends Copilot data to Sentinel data lake. Opens integrations with custom graphs and MCP server.

### Palo Alto Networks Cortex AgentiX + XSIAM

**Positioning.** "Build, deploy and govern the AI agent workforce of the future." Cortex AgentiX is positioned as the next generation of Cortex XSOAR.

**What it does.** Per Palo Alto's product page: "The industry's most secure platform to build, deploy and govern the AI agent workforce of the future." Available today in Cortex Cloud and Cortex XSIAM. Cortex XDR and standalone AgentiX platform: early 2026.

**Claimed metrics.** "Up to a 98% reduction in MTTR with 75% less manual work." (Vendor claim.)

**Integrations.** 1,000+ prebuilt integrations. **Native Model Context Protocol (MCP) support.**

**Architectural shape (per public docs).** Cortex Agentic Assistant is the interface for deploying / controlling AI agents across Cortex XSIAM, Cortex XDR, and Cortex Cloud. "Prebuilt agents are able to dynamically plan, reason and execute solutions."

**Autonomy level.** Multi-tier. Some agents are auto-action; others require approval. Customer-configurable.

**Deployment model.** SaaS, Cortex platform.

### Splunk Enterprise Security 8.2 — embedded AI Assistant for Security

**Positioning.** "AI SOC Workflows" — embedded AI throughout the ES experience.

**What it does in 8.2.** AI Assistant for Security:
- Generate complex SPL searches from natural language
- Auto-summarize investigation findings
- Extract key insights / IOCs
- Provide context-rich explanations during investigations

**Detection Studio.** Maps detection coverage against MITRE ATT&CK. Identifies gaps. Helps deploy high-fidelity rules faster.

**Coming in 2026** (per Cisco / Splunk roadmap):
- **Triage Agent** — auto-evaluates / prioritizes / explains alerts
- **AI Playbook Authoring** — natural language → SOAR playbooks
- **Malware Reversal Agent** — AI-driven reverse engineering, explains malicious scripts line-by-line
- **Response Importer**
- **AI-Enhanced Detection Library**
- **Personalized Detection SPL Generator**

**Autonomy claim.** Embedded AI assistance rather than agentic autonomy. Closer to a "Cursor for SOC" than to Charlotte Agentic SOAR.

**Deployment model.** Splunk Cloud or Enterprise on-prem. AI features cloud-only initially.

### Cyber Triage (Brian Carrier / Sleuth Kit Labs)

**Positioning.** "Verify generative AI" — the explicit anti-hallucination DFIR product. Brian Carrier is the author of *The Sleuth Kit* and *Autopsy* — the foundational open-source forensic library set.

**What it does.** From Sleuth Kit Labs' AI principles (published Dec 11, 2025): *"Verify generative AI: Where possible, structured data such as file paths, hashes, timestamps, and URLs in generative AI output are automatically cross-checked against source evidence to reduce the risk of AI 'hallucinations.'"*

**Mechanism.** Cross-check structured data (paths, hashes, timestamps, URLs) extracted from AI output against the source evidence at gating time.

**Principles set.** The "Verify generative AI" principle is part of a broader set of AI principles Cyber Triage publishes, framed as aligning with the OECD AI Principles. Other principles include transparency about which steps used AI, scoped retention of AI-derived outputs, etc.

**Autonomy claim.** AI-assisted, not autonomous. The AI accelerates the human; the human gates.

**Deployment model.** On-prem Windows application + SaaS option. MCP server support added in 2025 (per Cyber Triage's "Intro to MCP Servers for DFIR" blog).

**Significance.** Brian Carrier is the author of the most-used open-source forensic library (Sleuth Kit). His architectural choice — structured data extraction from LLM output + cross-check against source — is an authoritative published pattern in the field.

### Magnet Forensics Magnet AI

**Positioning.** "Built for justice. Designed for truth." Magnet AI is the "intelligence engine powering AI-driven innovation across the Magnet ecosystem."

**What it does (per Magnet's product page, 2026).**
- **Intelligent Search.** Natural-language search across thousands of media files, messages, audio, video. Surface meaningful leads.
- **Intelligent Insights** (in Magnet Review). Plain-language query → structured investigative summaries, key findings, suggested lines of analysis. **All grounded in verifiable citations linked directly to the source evidence.**
- **Media Analysis.** AI-powered classification (extremism, terrorism, narcotics, weapons).
- **Evidence Verification.** Every AI insight remains "grounded in verifiable evidence with built-in citation verification — ensuring findings are transparent, reviewable, and defensible."

**Autonomy claim.** "Keeping verification and decision making firmly in human hands."

**Autonomy level.** Search + classification + summary. Investigator reviews and validates.

**Deployment model.** Magnet AXIOM / Magnet Review on-prem + Magnet One cloud.

**Significance.** Built-in citation verification is the productized version of the pattern many hackathon submissions are attempting to implement.

### Cellebrite UFED + Inseyets + Pathfinder

**Positioning.** Mobile + cross-source digital investigation. Inseyets is the unified analysis platform; Pathfinder is the lead-discovery layer.

**What it does (per 2026 product material).** UFED extracts data from mobile devices. Inseyets unifies analysis across data sources — automatic content classification, identification of AI-generated modifications, on-demand transcriptions of audio/video. Pathfinder surfaces leads.

**Autonomy claim.** AI to "automate tasks, surface insights, and enhance the efficiency of digital investigations." Not autonomous — assistive.

**Deployment model.** On-prem.

**Significance.** Cellebrite is one of the two market leaders in mobile DFIR (Magnet being the other). Their AI features point toward where the broader DFIR market is going. No hackathon submission is in mobile DFIR.

### Belkasoft X + BelkaGPT

**Positioning.** "Offline AI for DFIR." Belkasoft X is the broader product; BelkaGPT is the offline AI assistant.

**What it does.** "BelkaGPT is Belkasoft's groundbreaking offline AI assistant... driven by Belkasoft X's advanced artifact extraction." Capabilities:
- Speech-to-text on audio/video files
- Picture content descriptions
- Picture classification (preset + custom categories)
- Question-answering over case artifacts + extracted text

**Autonomy claim.** Offline-only. Question-answering + classification + transcription.

**Autonomy level.** Assistant — not autonomous agent.

**Deployment model.** Belkasoft X is on-prem. **Operates entirely offline** — explicitly positioned against cloud AI for data-protection-regulated environments.

**BelkaGPT Hub (2026 update).** Supports distributed media-file processing across GPU-equipped infrastructure for picture description / classification / face-recognition preprocessing.

**Significance.** The only major DFIR vendor explicitly positioning AI as offline-only as a feature. Pattern relevant to airgap-focused hackathon submissions.

### SOCFortress Talon

| Field | Value |
|---|---|
| URL (canonical) | https://github.com/taylorwalton/talon |
| URL (alt) | https://github.com/psyll0n/talon-soc-agent |
| Positioning | "Open-Source AI SOC Analyst That Actually Works" |
| Trigger paths | Real-time POST /investigate + 15-minute scheduled sweep |
| Stack | Claude + local LLMs + Wazuh/OpenSearch SIEM |

**What it does.** "Automated AI SOC analyst built for SOCfortress CoPilot that runs as a background service, pulling raw events from your Wazuh/OpenSearch SIEM, enriching them with threat intelligence, correlating across your environment, and writing structured investigation reports directly back into CoPilot."

**Workflow.** SIEM raw event → IOC extraction → VirusTotal / Shodan / AbuseIPDB → MITRE ATT&CK correlation → structured report.

**Privacy-first architecture (distinctive choice).** An **anonymizing MCP proxy** intercepts raw SIEM events and replaces PII (usernames, hostnames, internal IPs) with session tokens **before they reach the cloud model**. Security-critical values (file hashes, external IPs, domains, process paths) pass through unchanged. Before the final report, the agent calls a built-in `deanonymize` tool to restore real names and IPs. **The cloud model never sees PII; the local user sees accurate output.**

**Local LLM support.** If Ollama is running locally, raw event interpretation routes to a local model. "The most sensitive step of reading the full raw event and extracting IOCs stays entirely on-premises."

**Autonomy claim.** Tier 1 SOC analyst automation. Per the team: "Not designed to replace your security team but to be a valuable extension of it."

**Deployment model.** OSS, self-hosted.

**Significance.** The anonymizing MCP proxy is a published OSS pattern for privacy-preserving cloud-LLM use in SOC workflows. Pattern relevant to any submission wanting to use cloud Claude on PII-containing evidence.

### Talion / Other smaller commercial entries

Smaller agentic-SOC vendors exist (Talion's Agentic SOC, etc.) — generally positioned the same way: bounded autonomy, multi-agent, MCP-compatible, vendor cloud.

### Common pattern across vendor "AI SOC" products

A few observations from this scan, presented descriptively:

- Every vendor named above either supports MCP natively or has it on the public roadmap. MCP is the de facto standard for agentic security tooling as of 2026-06-02.
- Every vendor positions as "AI accelerates the analyst, human stays accountable." None claims full autonomy.
- "Bounded autonomy" / "machine-speed response under analyst command" / "verification stays with the human" are common phrasings.
- Every vendor product is SaaS or on-prem with cloud-AI dependency (with two explicit airgap exceptions: BelkaGPT and Talon's optional local-Ollama path).
- The MTTR-reduction claims are vendor-specific and not directly comparable: CrowdStrike doesn't publish a specific number; Palo Alto claims "98%"; Splunk claims "minutes instead of hours."
- Citation verification (Magnet AI, Cyber Triage) is now a productized feature in two major DFIR vendors. The hackathon submissions racing to this wedge are converging on the same pattern as the commercial roadmap.

---

## Section 7 — Adjacent OSS LLM-DFIR tools

Projects that don't fit any of the above buckets but are conceptually relevant to the Find Evil! problem.

### Timesketch + Sec-Gemini (Google)

**Talk venue.** DEF CON 33 AI Village (August 2025). "Autonomous Timeline Analysis and Threat Hunting." Black Hat USA 2025 had the same talk in a different track.

**What it is.** Timesketch is Google's open-source forensic timeline analysis tool. Sec-Gemini is Google's security-specialized Gemini model. The combination is a "Log Reasoning Agent" that autonomously analyzes timelines.

**What it does (per Elie Bursztein's talk page).** "The Sec-Gemini digital forensic agent is able to autonomously perform timeline analysis and threat hunting with high accuracy on real-world compromised systems and directly integrate with Timesketch."

**UI integration.** A "Timesketch AI Panel" surfaces Sec-Gemini findings inside the Timesketch UI. Investigators interact with AI findings in a user-friendly manner rather than via API.

**Community reception.** At DEF CON 33, "77% of respondents said that they had found Sec-Gemini either 'very helpful' or 'extremely helpful' in assisting them with solving the challenges."

**Status.** Google research project — Sec-Gemini is not generally available. Timesketch AI Panel is in iterative development.

**Significance.** The single closest published demonstration of "autonomous DFIR agent integrated with a production forensic UI." Architecturally relevant: Timesketch is the well-known timeline tool, Sec-Gemini brings autonomous analysis, the integration shows what the productized form looks like.

### SocTalk — gbrigandi/soctalk

| Field | Value |
|---|---|
| URL | https://github.com/gbrigandi/soctalk |
| Pattern | LangGraph SOC agent across Wazuh / Cortex / TheHive / MISP via MCP |

**What it is.** An AI-powered SOC automation agent using LangGraph workflow: triage → enrichment → verdict → human review → response.

**Architecture.**
- **MCP servers (integrations):** `mcp-server-wazuh`, `mcp-server-cortex`, `mcp-server-misp`, `mcp-server-thehive`
- **Integrated solutions:** Wazuh (SIEM), Cortex (analysis), MISP (threat intel), TheHive (case/IR)

**Workflow.**
1. **Ingest** — poll Wazuh alerts, correlate into an investigation
2. **Investigate** — supervisor routes work to MCP-backed workers (Wazuh / Cortex / MISP / TheHive)
3. **Decide** — reasoning LLM produces verdict; thresholds pick auto-close vs escalate

**Infrastructure.**
- **Mock agents:** containerized Wazuh agents that execute MITRE ATT&CK-style techniques to generate realistic alerts
- **Persistence:** Postgres (event store + projections for timelines, metrics, dashboards)
- **API:** FastAPI
- **Dashboard:** SvelteKit
- **Capabilities:** REST, SSE event stream, metrics, review queue, settings

**Significance.** Demonstrates the LangGraph-based multi-agent SOC orchestration pattern, with MCP as the integration layer for each tool. The shape that several hackathon submissions are trying to apply to DFIR.

### Timeline-Analysis-In-Timesketch repos

Several smaller OSS projects (Plaso-LLM, log2timeline-MCP) experiment with similar shapes. None have reached the prominence of Sec-Gemini's integration.

---

## Section 8 — Anti-hallucination patterns from outside DFIR

Patterns that are not DFIR-specific but are technically relevant to the Find Evil! / Protocol SIFT problem.

### The Pydantic + Instructor citation validator pattern — `jxnl/instructor`

| Field | Value |
|---|---|
| URL | https://github.com/jxnl/instructor |
| Stars | ~13.1k |
| Monthly downloads | ~3M |
| Contributors | 1000+ |
| License | MIT |
| Author | Jason Liu (jxnl) |

**What Instructor is.** A Python library that extracts reliable JSON from any LLM. Built on Pydantic for validation, type safety, and IDE support. Eliminates manual JSON parsing, error handling, and retry logic.

**The citation validator pattern** (published Nov 18, 2023 in Instructor's blog at python.useinstructor.com/blog/2023/11/18/validate-citations/).

**Mechanism in plain English.** A Pydantic model field has a `@field_validator` decorator. The validator function gets the LLM-emitted value and the source text. It does a substring check: is the cited quote literally present in the source text? If yes, accept. If no, **raise ValueError**.

When Pydantic validation raises ValueError, Instructor automatically **retries the LLM request with the error message**, enabling self-correction without manual intervention. The model gets the error ("Your citation 'X' was not found in the source text") and tries again.

**Example pattern (paraphrased from the blog post):**

```python
class Answer(BaseModel):
    quote: str
    answer: str
    source_text: str  # passed in as context

    @field_validator("quote")
    @classmethod
    def quote_must_appear_in_source(cls, v, values):
        source = values.data["source_text"]
        if v not in source:
            raise ValueError(f"Quote '{v}' not found in source text")
        return v
```

**Variants in the blog.**
- Pure substring (above).
- LLM-judge variant for semantic alignment (cheaper than full substring, allows paraphrase).
- Span-offset variant (validator returns the byte offset of the match for downstream highlighting).

**Why this is the closest OSS prior art to "evidence-locked findings."**
- It's a Pydantic `@field_validator` doing substring check at parse time.
- Failure → hard rejection (ValueError) → automatic retry with error message.
- The pattern is widely used in production (Instructor has 13k stars and millions of monthly downloads).

**Differentiation from a forensic MCP-server gate.** Instructor's pattern is **SDK-layer for generic RAG**. A forensic MCP server enforcement is:
- Server-side (not optional SDK).
- Over forensic tool-execution audit_ids (not arbitrary text chunks).
- With NER + regex entity gate layered on top.
- Integrated with HMAC ledger and human-approval workflow.

**Significance.** Anyone designing a "verify findings against evidence" architecture should know about this. The pattern is mature, widely used, and the natural OSS reference point.

### NABAOS Tool Receipts — arXiv:2603.10060

| Field | Value |
|---|---|
| Paper | "Tool Receipts, Not Zero-Knowledge Proofs: Practical Hallucination Detection for AI Agents" |
| arXiv ID | 2603.10060 |
| Published | March 9, 2026 |
| Authorship | NABAOS (Nyāya-inspired framework, named after the Sanskrit epistemology Nyāya Śāstra) |

**The problem statement (verbatim from abstract).** *"AI agents that execute tasks via tool calls frequently hallucinate results — fabricating tool executions, misstating output counts, or presenting inferences as verified facts."*

**The mechanism.** A lightweight verification framework that:
1. **Classifies every claim in an LLM response by its epistemic source.** Inspired by Indian epistemology (Nyāya Śāstra) — classifies whether a claim is sourced from perception (tool output), inference (reasoning over tool output), testimony (from another agent), or fabrication.
2. **Generates HMAC-signed tool execution receipts** that the LLM cannot forge. Each tool call produces a receipt: signed metadata about what was executed, what came back, and when.
3. **Cross-references LLM claims against receipts** to detect hallucinations in real time.

**Detection rates** (per paper):
- 94.2% of fabricated tool references (the LLM cites a tool it never called)
- 87.6% of count misstatements (the LLM says "5 processes" when only 3 were returned)
- 91.3% of false absence claims (the LLM says "no evidence of X" when it didn't actually check)

**Overhead.** <15 ms verification per response.

**Alternative the paper rejects.** Zero-knowledge proofs of tool execution — cryptographically sound but impose minutes of proving time per query, making them impractical for interactive personal agents.

**Differentiation from claim-content verification.** NABAOS signs the **execution** of a tool call. It does NOT check whether a claim like "PID 4924 ran powershell.exe" appears verbatim in the byte range of the tool's stored output. It's execution attestation, not content attestation. And it operates as **post-hoc detection** (verify after generation) with epistemic-source classification, not as a hard architectural rejection gate.

**Significance.** The closest agent-domain prior art for cryptographically-signed tool-call provenance. Different in shape from forensic MCP-gate approaches (post-hoc vs gating; execution vs content) but related in spirit.

### GitMCP — context-injection pattern

Already covered in Section 5. Pattern summary: instead of detecting hallucinated outputs, prevent them by ensuring the model always has accurate context at generation time. Pattern relevant to forensic agents that could pre-inject authoritative DFIR knowledge into context (Valhuntir's forensic-rag-mcp is conceptually GitMCP-shaped for the DFIR domain).

### Anthropic Citations API

**Published.** Jan 2025 at claude.com/blog/introducing-citations-api.

**Mechanism.** Server-side sentence chunking of source documents → Claude is given chunks → Claude generates output with citation markers pointing at chunks.

**Anthropic's stated guarantee.** "Trained to resist fabricating sources... more likely to acknowledge uncertainty or decline to cite." Soft language — does NOT claim byte-level architectural guarantees.

**Availability.** Direct Anthropic API + Vertex AI + Bedrock.

**Relevance to Find Evil!** The Citations API operates at the LLM/API layer during generation, not at the MCP-server gate layer. It uses sentence chunks of provided documents as the citation substrate. It's soft (model trained to be faithful), not hard (server-side substring check). Pattern relevant to any submission considering training-aligned grounding vs architectural-gate grounding.

### Constrained decoding tooling (orthogonal but often confused)

- **Outlines** (~10k stars)
- **Guidance** (~19k)
- **XGrammar** (~1k — default for vLLM/SGLang/TensorRT-LLM/MLC-LLM)
- **lm-format-enforcer** (~1.5k)

All enforce **structural / grammar / regex / JSON-schema constraints during token decoding**. None verifies claim content against retrieved evidence. They guarantee well-formed JSON, not well-grounded findings.

**Why named here.** Judges and reviewers commonly conflate constrained decoding with grounding verification. Anyone building an anti-hallucination wedge will need to position relative to these.

### RAG-citation libraries

- **LlamaIndex citation modules** — produce citations as URL/chunk pointers
- **LangChain `with_citations`** — similar pattern
- **RAGAS** — evaluation framework for RAG
- **DeepEval** — eval framework

None hard-gate via substring at the server side. RAGAS / DeepEval are **evaluation frameworks**, not **enforcement gates** — they measure faithfulness after the fact, they don't reject at generation time.

### CiteCheck and academic span-validation patterns

A handful of academic papers (2024-2025) on subsentence-level citation validation. CiteCheck (Feb 2025, arXiv:2502.10881) decomposes answers into atomic claims and checks each against cited passage. Verifiable Generation with Subsentence-Level Fine-Grained Citations (June 2024, arXiv:2406.06125) studies subsentence-level citations. RetroLLM (Dec 2024, arXiv:2412.11919) constrains decoding to draw tokens from corpus via hierarchical FM-Index. SymGen (Nov 2023, arXiv:2311.09188) interleaves symbolic refs to JSON conditioning data so humans can verify spans.

All measure or detect rather than gate. The architectural-gate framing of "reject at server-side before staging the finding" is not the academic norm.

### DFIR-specific academic papers (named for completeness)

- **DFIR-Metric** (May 2025, arXiv:2505.19973) — pure evaluation benchmark. 700 MCQs + 150 CTFs + 500 NIST cases. Introduces Task Understanding Score for near-zero-accuracy models. Models score "0% complete solutions" on practical disk/memory cases — they "hallucinate files, bash commands, paths and libraries that are absent from the image."
- **CyberSleuth** (Aug 2025, arXiv:2508.20643) — multi-agent blue-team forensics with packet/log parsing sub-agents and CVE attribution. Compares 3 architectures × 6 LLMs. No architectural anti-hallucination gate.
- **Digital Forensics in the Age of LLMs** (April 2025, arXiv:2504.02963) — survey paper. Notes LLM hallucination as a limitation, proposes no architectural solution. Suggests HITL + grounding as direction.
- **Chances and Challenges of MCP in DFIR** (June 2025, arXiv:2506.00274v1) — surveys MCP for DFIR. Discusses provenance/audit logging as a forensic primitive but does not propose substring-verifying findings against tool output.

---

## Closing — observable patterns across the field

Pure observation. Choices that emerge in multiple independent implementations.

### Patterns appearing in 3+ implementations

**1. Typed MCP server with read-only forensic tool wrappers.**
Where it appears: Valhuntir's 9 backends, ~25 hackathon submissions, several non-hackathon Volatility/Velociraptor wrappers.
What the pattern is: forensic CLIs (Volatility, Sleuth Kit, Plaso, EZ Tools, YARA, etc.) wrapped as typed MCP tools with structured Pydantic-style input/output. Read-only by default.

**2. Stable cross-reference audit IDs.**
Where it appears: Valhuntir (`{backend}-{examiner}-{YYYYMMDD}-{NNN}`), MemoryHound (SHA-256-chained), SIFTGuard (19-col SQLite), marez8505/find-evil (SHA-256 + timestamp).
What it is: every tool call gets an ID; the ID is referenced by findings to claim "this finding comes from these tool calls." Stability across restart is a common design goal.

**3. Per-call audit log as JSONL.**
Where it appears: Valhuntir per-backend JSONL, SIFTGuard SQLite, MemoryHound, sgharlow's find-evil, sift-bench. Notable counter-example: Protocol SIFT (only Stop-hook session summary).
What it is: append-only structured log of every tool call with timestamp, tool name, args, output hash, exit code, elapsed time.

**4. SHA-256 hash of tool output.**
Where it appears: Valhuntir, marez8505/find-evil, SIFTGuard, MemoryHound, sgharlow, tracelock. Counter-example: find-evil-sleuth uses BLAKE3.
What it is: the output of each tool call is hashed; the hash goes into the audit entry. Used for tampering detection.

**5. DRAFT / APPROVED state machine for findings.**
Where it appears: Valhuntir (load-bearing), several Valhuntir-influenced submissions.
What it is: findings stage as DRAFT; an explicit approval step (human-gated) transitions to APPROVED. Only APPROVED findings appear in reports.

**6. Structured finding schema with observation + interpretation + confidence + audit_ids.**
Where it appears: Valhuntir, MemoryHound, SIFTGuard, VALKYRIE, EvidenceChain, several others.
What it is: a finding is not free-text. It's a typed object with separate observation (what was seen), interpretation (what it means), confidence (HIGH/MEDIUM/LOW/SPECULATIVE), and references to the tool calls that supported it.

**7. Three-to-four-tier confidence taxonomy.**
Where it appears: Valhuntir (HIGH/MEDIUM/LOW/SPECULATIVE), VALKYRIE (CONFIRMED/INFERRED/UNVERIFIED), MemoryHound, several others.
What it is: confidence is discretized, not continuous. The exact labels vary; the bucketing principle does not.

**8. MITRE ATT&CK technique tagging on findings.**
Where it appears: Valhuntir, MemoryHound, VALKYRIE, EvidenceChain, ~10 others.
What it is: findings carry an `mitre_ids` array referencing the relevant ATT&CK techniques.

**9. IOC extraction via regex from finding text.**
Where it appears: Valhuntir's `_extract_all_iocs()`, multiple submissions.
What it is: regex over the finding's observation + interpretation to extract IPs / hashes / paths / domains for the report's IOC index.

**10. Forensic discipline reminders / methodology library.**
Where it appears: Valhuntir's FK enrichment + 15+ rotating reminders, EvidenceChain's `Proves` column, several skill-file-style submissions.
What it is: "presence ≠ execution," "Shimcache proves presence," etc. — methodology truisms surfaced into the tool/response layer.

**11. Per-examiner ID prefix.**
Where it appears: Valhuntir's `F-alice-001`/`T-bob-003`/`TODO-alice-001`.
What it is: per-user namespacing so multi-examiner merges don't collide.

**12. PostToolUse hook capturing raw Bash for provenance.**
Where it appears: Valhuntir (claude-code.jsonl via forensic-audit.sh), find-evil-sleuth (PreToolUse exit-1 gate).
What it is: Claude Code's hook system used as an audit / enforcement layer below MCP.

**13. Pre-approved permission allowlist + small deny list.**
Where it appears: Protocol SIFT (~100 allow / 5 deny), most submissions to varying degrees.
What it is: settings.json with explicit allow rules to avoid permission-prompt fatigue, plus a deny list for obvious destructive / exfil commands.

**14. Sandbox / kernel isolation for the LLM client.**
Where it appears: Valhuntir (bwrap with `--unshare-net --unshare-pid`), find-evil-sleuth (rootless podman + seccomp), warvis (compile-time tool whitelist).
What it is: the LLM client runs inside a kernel-level constraint, not just a permission model.

**15. Local LLM as airgap option.**
Where it appears: warvis (Gemma via Ollama), MukundaKatta/sift-sentinel (offline simulation), Talon (optional Ollama route), BelkaGPT (vendor product).
What it is: support for local-only LLMs so the system can run airgapped.

**16. Reasoning log + action log — append-only LLM-voluntary writes.**
Where it appears: Valhuntir (`case-mcp.log_reasoning`, `case-mcp.record_action`), several others.
What it is: tools the LLM calls to write its hypothesis-formation and action choices into the audit trail. Captures intent, not just outcomes.

**17. Self-correction framing as the wedge.**
Where it appears: ~22 hackathon submissions.
What it is: the agent has some mechanism — varying — to recognize when output is inconsistent and retry / pivot. Universally framed as a wedge by submissions that have it.

**18. Examiner-friendly review UI (browser or terminal).**
Where it appears: Valhuntir (8-tab Portal), marez8505 (Flask), FlemingJohn's sift-sentinel (TUI), several others.
What it is: a review surface for humans separate from the agent loop. Reflects belief that pure terminal review is friction.

**19. License: MIT or Apache 2.0.**
Where it appears: nearly all hackathon submissions (rule requirement). Counter-examples: Protocol SIFT (no license declared), socfortress/velociraptor-mcp-server (AGPL — exists outside hackathon, would be incompatible with rules if reused).
What it is: liberal OSS license, partly rule-driven.

### Patterns appearing in 1-2 implementations (notable singletons)

**Adversarial-evidence cadence detection** — only `foveal-dfir` (`MACHINE_PACED` vs `HUMAN_LIKELY`).

**Typed graph paths as the finding substrate** — only `glaive` (the unrepresentable-state argument).

**Dual independent LLMs cross-checking each other** — only `Verdict` (Qwen3 vs GLM-4.5-Air).

**Postgres + 11 extensions as the substrate, with live judge SELECT queries during demo** — only `find-evil-sleuth`.

**Compile-time tool whitelist in Go FSM** — only `warvis`.

**Blind independent grader requiring N≥2 sources for CONFIRMED** — only `foveal-dfir`.

**Anonymizing proxy for cloud LLM use on PII evidence** — only `SOCFortress Talon` (outside hackathon).

**Negative-assertion benchmark** — only `aksoni/sift-bench`.

**Ground-truth dataset with Peirce semiotic classification** — only `annatchijova/vigia-cases`.

**Live-host triage via Velociraptor + agentic layer** — not built (Velociraptor MCPs exist; the agentic layer above does not).

**Cyber-physical / OT / robotics scope** — only `Forenly`.

**HMAC-signed approval ledger with PBKDF2-derived examiner-password key** — only Valhuntir (the pattern was named in several submissions but not implemented at the same depth).

**Bidirectional report reconciliation** (`APPROVED_NO_VERIFICATION` / `VERIFICATION_NO_FINDING` / `DESCRIPTION_MISMATCH`) — only Valhuntir.

**Token-budget-aware methodology decay** (FK enrichment with caveats-always / advisories-first-3-then-every-10th) — only Valhuntir.

**Provenance tier classification (MCP > HOOK > SHELL > NONE)** with server-side hard reject — only Valhuntir.

**Closed-loop critic→revise self-correction agent that periodically re-reads evidence + findings and challenges weak ones** — not present in any visible implementation. (Many submissions claim "self-correction"; none ships an independent critic agent that fires asynchronously over staged findings.)

**Structural adversarial-evidence sanitizer (strip role tokens / normalize unicode / quarantine free-text)** — only `foveal-dfir` in partial form; the structural sanitization layer as a first-class architecture is not present.

**Memory-Volatility-plugin-aware reasoning chain (typed `psscan→pslist→diff` workflow, automatic pivot on plugin failure)** — not present. Vol3 is exposed as raw command execution everywhere.

**Real-time investigation HUD streaming the agent's tool calls + reasoning** — not present in the visible field.

**Lightweight laptop-only deployment under 200 MB / 2 GB RAM** — claimed in some submissions but not measured/published in visible artifacts.

**Court-admissibility / Daubert / FRE 901 mapping for AI findings** — claimed as marketing in `Nafsgerman/siftguard` but no actual legal-rule mapping in code.

**EU AI Act / GDPR compliance evidence for AI-derived findings** — only `umfhero/Forensic-AI` mentions as a research task.

**Closed claim-vs-evidence content verification (server-side substring check of the finding text against the cited audit_id's stored byte range)** — the gap that the wedge novelty research identified as missing across the entire visible field, including Valhuntir.

### Patterns shared with vendor commercial products

**MCP as the agent-tool interface.** Charlotte AI, Microsoft Sentinel, Cortex AgentiX, Splunk roadmap, Cyber Triage — all MCP or MCP-compatible.

**Citation verification as a first-class feature.** Magnet AI, Cyber Triage — both publish "verify AI claims against source evidence" as a feature. The hackathon submissions racing to this wedge are converging on the same direction as the commercial roadmap.

**Bounded autonomy.** Every vendor product positions as "AI assists, human stays accountable." No vendor claims full autonomy. The hackathon submissions echo this.

**Multi-agent orchestration via supervisor + workers.** SocTalk, several hackathon submissions, Charlotte AgentWorks — all share the supervisor / workers pattern.

**Anonymizing proxy for cloud-AI use on sensitive data.** SOCFortress Talon publishes the pattern as OSS. No hackathon submission appears to have ported it.

**Local-LLM fallback for airgap.** Belkasoft (commercial), Talon (OSS), warvis (hackathon), MukundaKatta (hackathon) — all support local-only LLMs as an explicit deployment mode.

### Where the field has converged on a single answer

- **MCP is the agent-tool interface.** Direct shell access is now considered the failure mode.
- **Findings are typed objects, not free text.** The observation/interpretation/confidence shape is universal.
- **Audit trail is JSONL or similar append-only structured log.** Per-tool-call granularity is the floor.
- **SHA-256 of tool output is the minimum audit hash.** A few exceptions choose BLAKE3 for performance.
- **MITRE ATT&CK technique tagging is table stakes for findings.**

### Where the field has NOT converged

- **How self-correction is implemented.** Approaches range from "one sentence in the prompt" (Protocol SIFT) through "per-phase retry loop" (marez8505) through "dual independent LLM cross-check" (Verdict) through "blind independent grader" (foveal) through "typed graph paths" (GLAIVE) through "compile-time whitelist" (warvis). No consensus.
- **How human approval is gated.** Approaches range from "no gate at all" (Protocol SIFT) through "browser UI password prompt" (Valhuntir) through "bcrypt + Flask" (marez8505) through "Postgres SELECT review" (find-evil-sleuth). No consensus.
- **What the agent's reasoning is structured as.** ACH (VALKYRIE), LangGraph FSM (MemoryHound, SocTalk), Hunt FSM (warvis), Hacker Mindset Graph (ThreatPipe), atomic 5-phase pipeline (marez8505), state machine (Valhuntir forensic-mcp). Each picks a different shape.
- **Where the line between MCP-resident and gateway-resident logic should sit.** Valhuntir puts forensic-discipline enrichment in the MCP response envelope. Other submissions put it in the system prompt. Other submissions put it in client-side hooks.
- **What constitutes "evidence" in the audit chain.** Some submissions hash tool output bytes; some hash the audit entry; some hash both with a chain (MemoryHound, SIFTGuard); some use HMAC instead of plain hash (Valhuntir).
- **Whether to use a single typed schema or a frame-by-frame typed envelope.** Valhuntir's envelope is rich (`audit_id / caveats / advisories / corroboration / discipline_reminder / data_provenance / field_meanings`). Most submissions use a thinner envelope.
- **How to handle adversarial evidence.** Most submissions don't. The ones that do (foveal-dfir partial, the few with quarantine markers) use different approaches.

### Where there is a published gap visible in the wedge-novelty research that no implementation visible in the field fills

(Not a recommendation. Pure observation, drawn from the wedge-novelty research at `research/protocol-sift-2026/.raw/05-novelty-check.md`.)

Valhuntir has **eight gates** in the finding pipeline: schema, audit_id existence, evidence-registry path, provenance chain, grounding-MCP presence score, HMAC integrity ledger, bidirectional reconciliation, IOC regex extraction. **None of them open the cited tool output and check that the finding's observation text or its extracted entities appear there.** The combination of (server-side hard rejection at `record_finding()` + byte-range substring check of the cited audit_id's stored output + NER+regex entity gate that catches hallucinated entities) does not appear in Valhuntir or any of the ~60 hackathon submissions surveyed.

Substring-validated citations exist as a Pydantic pattern in **Instructor** (Section 8). HMAC-signed tool execution receipts exist in **NABAOS** (Section 8). The intersection — substring verification of claim text against named tool-execution audit IDs as the citable substrate, with hard server-side rejection inside an MCP server, layered with entity-gate, deployed inside a forensic MCP architecture — has no published or shipped prior visible in this scan.

This is a description of the gap. Whether or how to fill it is a design-phase decision, made informed by the rest of `context/`.

---

## Endnote

Reading order suggestion if you have limited time:

1. Section 1 (Protocol SIFT) — to understand what every submission either extends or replaces.
2. Section 2 (Valhuntir) — to understand what the published bar looks like in full.
3. Section 4 (hackathon competitors) — to see the design-space distribution.
4. Closing observable-patterns section — to see what is and isn't converged on.

Sections 3, 5, 6, 7, 8 are reference. Read them when you have a specific question.

Provenance: this document was assembled from (a) direct depth-1 clones of `teamdfir/protocol-sift`, `AppliedIR/Valhuntir`, and `AppliedIR/sift-mcp` to `/tmp/protocol-sift-research/` on 2026-06-02 with the file:line citations you see throughout; (b) public READMEs and product pages for the named hackathon submissions and vendor products; (c) the arXiv abstracts for the named academic papers; (d) the wedge-novelty and competitor-analysis research dumps in `research/protocol-sift-2026/.raw/`. Where a claim's source is not clear inline, it is reconstructable from the raw dumps in `research/protocol-sift-2026/.raw/`.
