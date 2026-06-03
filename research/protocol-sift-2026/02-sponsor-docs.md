# 02 — Sponsor Docs & Available Primitives

This file is the "what already exists that we can build on or extend" reference.

---

## 1. Protocol SIFT (the baseline — `teamdfir/protocol-sift`)

### What it actually IS

**Not** an agent framework. **Not** an MCP server. **Not** a runtime.

Protocol SIFT is a **~10-file Claude Code configuration bundle** that drops into `~/.claude/`. It teaches vanilla Claude Code (CLI) how to drive SIFT forensic tools through `Bash` invocations against a pre-approved allowlist.

| Stat | Value |
|---|---|
| Last commit | 2026-03-25 (`40bed7a Update README.md`) |
| Stars / forks | 15 / 8 |
| Open issues / PRs | 0 / 0 |
| Total files | ~10 |
| Languages | Python 77.6% + Shell 22.4% + Markdown |
| MCP server? | **No** |
| Agent loop? | **No** (just Claude Code's loop) |
| Self-correction? | One sentence in CLAUDE.md: "On failure: read stderr → hypothesize → correct → retry." |
| Sandbox? | Prompt-based read-only + write-path allowlist. **Not architectural.** |
| Audit trail? | One Stop-hook summary appended to `forensic_audit.log` at end of session. **Not per-tool.** |
| Approval gate? | **None.** LLM writes findings as plain text to `./reports/`. |

### The 10 files

```
~/.claude/CLAUDE.md         ← system prompt: "Principal DFIR Orchestrator", 75 lines
~/.claude/settings.json     ← ~100 forensic CLIs pre-approved; deny list = [rm -rf, dd, wget, curl, ssh, WebFetch]; Stop hook appends audit
~/.claude/settings.local.json ← sudo apt, psort.py
~/.claude/skills/memory-analysis/SKILL.md      (379 lines — Volatility 3 cookbook)
~/.claude/skills/plaso-timeline/SKILL.md       (294 lines — log2timeline / psort)
~/.claude/skills/sleuthkit/SKILL.md            (409 lines — TSK + EWF)
~/.claude/skills/windows-artifacts/SKILL.md    (721 lines — EZ Tools + Win event ID tables)
~/.claude/skills/yara-hunting/SKILL.md         (339 lines — YARA rule structure + hunts)
~/.claude/case-templates/CLAUDE.md             (199 lines — per-case template, ships with FOR508 SRL case hardcoded)
~/.claude/analysis-scripts/generate_pdf_report.py  (WeasyPrint PDF generator)
```

### install.sh in one paragraph

Detect Claude Code (install if absent). Locate the repo files (in-place or `git clone --depth=1` to tempdir). Make `~/.claude/`. For each of `CLAUDE.md`, `settings.json`, `settings.local.json`: backup existing as `.bak-<ts>`, then copy. For each skill in 5 categories: copy SKILL.md. Copy PDF script + case template. Prompt to `pip3 install weasyprint` if TTY else skip. Print case-start banner.

### What Protocol SIFT asks us to do

Per the README and directory layout: **extend `~/.claude/skills/`**, add new skill files, or build a project CLAUDE.md that orchestrates the existing skills better. Adding capability (new skills, new artifact types, an MCP server, better self-correction) on top of this baseline is encouraged.

### What Protocol SIFT cannot do (these are open-field opportunities)

- ❌ No MCP — every tool call is raw `Bash(...)`. No structured outputs back to the LLM.
- ❌ No human approval gate / DRAFT→APPROVED state.
- ❌ No agent constraint enforcement (skill files are guidance, not enforcement — Claude Code can ignore them).
- ❌ No multi-examiner support.
- ❌ Generated PDF reports are case-specific scripts the LLM writes per-investigation — reuse is manual.
- ❌ Network exfil only blocked by prompt + denylist `[wget, curl, ssh, WebFetch]`. **`python3 -c 'urllib.request...'` is NOT on the denylist.** (Trivial bypass.)
- ❌ Case template ships with SRL FOR508 lab data hardcoded — first step on a new engagement is strip-and-replace.
- ❌ No VSCMount / MemProcFS on Linux SIFT — Windows-only artifacts require separate Windows analysis VM.
- ❌ No per-tool-call audit trail. Only end-of-session summary.

### Strategic implication

**The baseline is trivially exceeded.** Anything that adds a real MCP server, a structured audit log per call, an approval gate, or measured constraint exceeds Protocol SIFT. The actual bar to beat is Valhuntir, not Protocol SIFT.

---

## 2. Valhuntir (the bar — `AppliedIR/Valhuntir` + `AppliedIR/sift-mcp` + companions)

### What it IS

A real platform built by **Steve Anson** (SANS Principal Instructor, FOR508 co-author, AppliedIR founder) using Claude Code. The `Valhuntir` repo is the **vhir CLI + architecture docs**. The actual MCP servers live in sibling repos under `AppliedIR/`:

| Repo | Purpose |
|---|---|
| `AppliedIR/Valhuntir` | vhir CLI (~10K LOC Python) + architecture docs |
| `AppliedIR/sift-mcp` | 11-package monorepo: gateway + 7 MCP backends |
| `AppliedIR/wintools-mcp` | Windows tool execution (10 tools, 31 catalog entries) |
| `AppliedIR/opensearch-mcp` | Evidence indexing/querying (17 tools, 15 parsers) |

Author disclosure: *"I do DFIR. I am not a developer. This project would not exist without Claude Code handling the implementation."*

### Top-level scale

| Metric | Value |
|---|---|
| MCP backends | 9 (8 SIFT-local stdio + wintools HTTP) |
| Total MCP tools | 100 (73 base, 90 with opensearch, 100 with wintools) |
| Forensic-knowledge tool catalog | 59 tools × 17 categories |
| Windows triage baseline records | **2.6 million** |
| Forensic RAG records | **22,000+** across 23 authoritative sources |
| OpenSearch parsers | 15 (evtx, 10 EZ Tools, Volatility 3, JSON/JSONL, delimited, access logs, W3C, MPLog, schtasks, WER, SSH, PowerShell transcripts, Prefetch/SRUM) |
| Hayabusa Sigma rules auto-applied | 3,700+ |
| Defense layers | 9 |
| Resource req | 16 GB RAM basic / 32 GB w/ OpenSearch; 50–100 GB disk + evidence |
| vhir CLI commands | 24 |

### Architecture (3 layers)

```
LLM Client (Claude Code / Desktop / LibreChat / Cherry Studio)
    │ MCP Streamable HTTP
    ▼
sift-gateway :4508  ─── auth bearer ───►  Examiner Portal (browser, 8 tabs)
    │ stdio subprocess
    ├──► forensic-mcp        (23 tools: investigation state machine + 14 discipline tools/resources)
    ├──► case-mcp            (15 tools: case lifecycle, evidence ops, audit/reasoning logs)
    ├──► report-mcp          (6 tools: 6 report profiles, bidirectional reconciliation)
    ├──► sift-mcp            (5 tools: Linux forensic tool execution, denylist-protected)
    ├──► forensic-rag-mcp    (3 tools: semantic search across 22K records)
    ├──► windows-triage-mcp  (13 tools: offline baseline validation, 2.6M records)
    ├──► opencti-mcp         (8 tools: threat intel, rate-limited + circuit breaker)
    └──► opensearch-mcp      (17 tools: evidence indexing, Hayabusa auto-run)

(separate hosts)
LLM Client ─── HTTPS ───► wintools-mcp :4624 (Windows VM, 10 tools, hardcoded denylist of 20+ binaries)
LLM Client ─── HTTP ────► remnux-mcp :3000 (REMnux VM, optional)
```

### The 9 defense layers (verbatim from `docs/security.md`)

| Layer | Control | Type | Scope |
|---|---|---|---|
| L1 | Structural approval gate (DRAFT → APPROVED requires password) | Structural | All clients |
| L2 | HMAC verification ledger (PBKDF2 + HMAC-SHA256, 600K iterations) | Cryptographic | All clients |
| L3 | Case data deny rules (41 rules blocking Edit/Write/Bash on case files) | Permission | Claude Code only |
| L4 | Sandbox filesystem `denyWrite` via bwrap | Kernel | Claude Code only |
| L5 | File permission chmod 444 after write | Filesystem | All clients (advisory) |
| L6 | Bidirectional report reconciliation | Integrity | All clients |
| L7 | Password authentication (CLI + portal challenge-response) | Authentication | All clients |
| L8 | Provenance enforcement (MCP > HOOK > SHELL > NONE) | Structural | All clients |
| L9 | Kernel sandbox (bubblewrap namespaces, `--unshare-net`, `--unshare-pid`) | Kernel | Claude Code only |

### Self-correction implementation in Valhuntir

**Defense-in-depth at the response envelope level, NOT a closed critique-revise loop.** This is critical — it's where we can beat Valhuntir.

1. **`validate_finding(finding_json)`** — forensic-mcp tool LLM is supposed to call **before** `record_finding()`. Structured assessment.
2. **Hard gate in `record_finding()`** — server-side rejects: NONE-provenance, unknown source files, unknown audit_ids.
3. **Grounding score** — STRONG/PARTIAL/WEAK based on whether 2+/1/0 reference backends were consulted. Advisory, not blocking.
4. **Rotating discipline reminders** — every tool response carries one of 15+ reminders ("Absence of evidence ≠ evidence of absence", "Shimcache and Amcache prove file PRESENCE, never execution"). Deterministic modulo rotation.
5. **Stale-content detection** — content hash mismatches between staging and approval surfaced as `field 'X' changed since review`.

**The gap:** an explicit critic agent that periodically re-reads evidence + findings, challenges weak findings, and gates further work on resolving low-confidence items is **not in Valhuntir**.

### Accuracy validation in Valhuntir (5 stacked)

1. `validate_finding()` pre-check (schema + methodology).
2. SHA-256 evidence registry (`vhir evidence verify`).
3. Content hash on findings (compute at staging + approval; mismatch → `stale_at_approval=True`).
4. **HMAC verification ledger (L2)**: PBKDF2-SHA256 600K-iter key from examiner password, HMAC-SHA256 over substantive text. Stored at `/var/lib/vhir/verification/{case_id}.jsonl`, chmod 0600. **LLM cannot forge entries.**
5. Bidirectional report reconciliation: `APPROVED_NO_VERIFICATION` / `VERIFICATION_NO_FINDING` / `DESCRIPTION_MISMATCH` flagged.

Code paths:
- `src/vhir_cli/verification.py:33` — `derive_hmac_key(password, salt)` (PBKDF2-SHA256, 600K)
- `src/vhir_cli/verification.py:38` — `compute_hmac(derived_key, description)`
- `src/vhir_cli/verification.py:45-54` — `write_ledger_entry()` (fsync, chmod 0600)
- `src/vhir_cli/verification.py:82-98` — `verify_items()` (`hmac.compare_digest`)
- `src/vhir_cli/approval_auth.py:249-271` — `verify_password()` (PBKDF2 + `secrets.compare_digest`)
- `src/vhir_cli/commands/approve.py:552-621` — `_write_verification_entries()`

### Audit trail in Valhuntir

Every MCP tool call → JSONL entry in per-backend log under case `audit/`:

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

`audit_id` is cross-referenced — findings cite `audit_ids`; PostToolUse hook captures every Bash command from Claude Code to `claude-code.jsonl` with SHA-256 hashes (this is what gives a finding its HOOK-tier provenance).

### Finding schema in Valhuntir (the output contract to match)

```json
{
  "id": "F-alice-001",
  "title": "STUN.exe lateral movement via Net Use",
  "observation": "<what was seen>",
  "interpretation": "<what it means>",
  "confidence": "HIGH|MEDIUM|LOW|SPECULATIVE",
  "confidence_justification": "<why>",
  "context": "<scope, host, time window>",
  "type": "<finding type — used for FK corroboration lookup>",
  "audit_ids": ["sift-alice-20260520-007", "sift-alice-20260520-012"],
  "iocs": ["172.16.6.12", "STUN.exe", "hash:..."],
  "mitre_ids": ["T1021.002", "T1543.003"],
  "examiner": "alice",
  "created_by": "alice",
  "status": "DRAFT|APPROVED|REJECTED",
  "content_hash": "<SHA-256 of substantive text>",
  "approved_at": "<iso8601>",
  "approved_by": "alice",
  "modified_at": "<iso8601>",
  "examiner_modifications": {<field>: {original, modified, by, at}},
  "examiner_notes": [{note, by, at}, ...]
}
```

Timeline events are auto-spawnable from findings (`auto_created_from: F-alice-001`).

### Reports

6 profiles: full / executive / timeline / ioc / findings / status.

LLM renders narrative; `report-mcp.generate_report()` returns structured JSON + Zeltser IR Writing guidance. `save_report()` persists. Only APPROVED items appear.

### Patterns we should steal

1. **MCP-based architecture > raw Bash.** Structured envelope per call: `audit_id, caveats, advisories, corroboration_suggestions, field_meanings, discipline_reminder, data_provenance`.
2. **Forensic Knowledge (FK) enrichment system.** YAML-defined per-tool contexts injected at the MCP response layer, with token-budget decay (caveats always; advisories first-3-calls then every-10th). Delivers methodology AT the point of need, not in the drift-prone system prompt.
3. **Provenance tier classification** (MCP > HOOK > SHELL > NONE). Server rejects NONE-provenance findings.
4. **HMAC-signed ledger outside the sandbox** at `/var/lib/vhir/...`. Even if LLM owns case dir, can't forge approval entries. Cryptographic > prompt-based.
5. **`data_provenance: tool_output_may_contain_untrusted_evidence`** marker — explicit prompt-injection-resistance signal.
6. **MCP `Resources` vs `Tools`** — 14 discipline items exposed as Resources by default, fallback `reference_mode="tools"` for clients without resource support.
7. **Per-examiner ID prefix** (`F-alice-001`) for global uniqueness across multi-examiner merges.
8. **Examiner Portal** is the primary review surface; CLI is secondary. Challenge-response auth — password never leaves browser.
9. **Two voluntary reasoning logs** the LLM writes: `case-mcp.log_reasoning(text)` and `case-mcp.record_action(...)`. Captures hypothesis-formation auditably.
10. **Grounding score** advisory on `record_finding()` — STRONG/PARTIAL/WEAK from whether reference backends were consulted. Cheap; surfaces "you didn't check your work."

### What Valhuntir LEAVES OPEN (our wedge surface)

1. **No closed-loop critique-revise self-correction.** Prompt-level rotation + structural gates only. No critic agent firing periodically to challenge weak findings + gate further work on resolving them.
2. **HITL is admitted as primary defense against adversarial evidence.** A *structural* defense (quarantining/escaping layer for free-text evidence fields, or a sanitizer agent stage) is open.
3. **Claude-Code-only sandbox / deny rules / audit hooks** (L3, L4, L9). Other MCP clients (Desktop, LibreChat) get MCP-level guidance only. Bringing structural controls to those clients via gateway-side enforcement is open.
4. **Synchronous, examiner-blocking findings state machine.** No asynchronous AI self-review pass before HITL — examiner gets a raw DRAFT pile. An LLM-driven pre-review that flags weak findings + suggests merges + surfaces duplicates would reduce examiner cognitive load.
5. **Memory analysis is exposed as raw Volatility commands via `sift-mcp.run_command`.** No Volatility-plugin-aware reasoning agent that knows the `psscan→pslist→diff` pattern, or `malfind→dumpfiles→YARA→VirusTotal` pattern, as structured workflows.
6. **No live-system support.** Valhuntir is post-mortem only. Live-host triage via Velociraptor MCP + agentic guidance is open.
7. **Examiner Portal is static HTML/JS.** A live investigation HUD with real-time agent traces / tool-call streaming would be a much better demo.
8. **Heavyweight platform.** 16–32 GB RAM, ~14 GB disk install. A sub-200MB / sub-2GB-RAM lightweight wedge that hits rubric items could win on Usability + breadth-of-deployability.

---

## 3. SIFT Workstation (the platform — `sans-dfir/sift` + `teamdfir/sift-saltstack`)

| Field | Value |
|---|---|
| Repo | https://github.com/sans-dfir/sift (mostly issue tracker now) |
| Actual install | https://github.com/teamdfir/sift-saltstack |
| Install cmd | `sudo cast install teamdfir/sift-saltstack` |
| Base | Ubuntu 22.04 Jammy (Feb 2024 build) |
| Config mgmt | SaltStack |
| VM build | Packer (`teamdfir/sift-packer`) |
| Cloud | Pre-built AMIs on AWS multi-region |
| Container | Dockerfiles in `teamdfir/sift-dockerfiles` |
| Default user | `sansforensics` |
| Marketed | "200+ forensic tools pre-installed" |

teamdfir org repos (ordered by relevance):

| Repo | Lang | Last commit | Relevance |
|---|---|---|---|
| `sift-saltstack` | Python | 2026-05-17 | **High** — actual install logic |
| `sift-packer` | Shell | 2026-04-19 | Medium — VM builds |
| `protocol-sift` | Python | 2026-03-25 | **THIS REPO** |
| `volatility-plugins-community` | Python | 2024-09-18 | Medium — plugin reference |
| Others | — | older | Lower priority |

**No other repos tagged `mcp`, `agentic`, `ai`, or `find-evil`.** Protocol SIFT is the only agentic surface in either org.

### Tool inventory (synthesized from `protocol-sift/skills/*` + Valhuntir FK catalog)

| Category | Tools |
|---|---|
| **Memory** | Volatility 3 (`/opt/volatility3-2.20.0/vol.py`), Memory Baseliner, winpmem |
| **Disk** | Sleuth Kit (mmls, fls, icat, istat, ils, tsk_recover), ewfacquire/ewfmount/ewfverify/ewfinfo, dc3dd/dcfldd |
| **Timeline** | log2timeline.py, psort.py, pinfo.py, mactime |
| **Windows artifacts (EZ Tools)** | MFTECmd, EvtxECmd, AmcacheParser, AppCompatCacheParser, PECmd, RECmd, RBCmd, SBECmd, LECmd, JLECmd, SrumECmd, SQLECmd, bstrings, WxTCmd, srum-dump |
| **Registry** | RegRipper (`rip.pl`) |
| **Threat hunting** | Hayabusa, Chainsaw (both Rust, Sigma-rule driven) |
| **Carving** | bulk_extractor, foremost, scalpel, photorec |
| **Network** | tshark, tcpdump, Zeek, Suricata, NetworkMiner |
| **Malware triage** | YARA, ClamAV, strings, binwalk, ssdeep, capa, FLOSS, densityscout, moneta, hollows_hunter, sigcheck, capa, 1768_cobalt |
| **VSS / encryption** | libvshadow (vshadowinfo, vshadowmount), libbde (BitLocker), libfvde (FileVault) |
| **Parsing libs** | libesedb (esedbexport), libevt, libevtx (evtxexport), lightgrep |
| **Triage / live** | KAPE (Windows-binary, can Mono on SIFT), Velociraptor (enterprise add-on) |
| **Docs / mounting** | dfvfs, dftimewolf, imagemounter, xmount |
| **Browser** | hindsight, BrowsingHistoryView |
| **Recycle bin** | rifiuti2 |
| **Doc malware** | pdf-parser, pdfid, peepdf, oledump, oletools, steghide |

Full per-tool invocation reference + standard chains are in `02-sponsor-docs.md` (this file) and the raw `03-domain-knowledge.md` under `.raw/`.

### Standard tool chains (memorize these — judges expect to see them)

**Disk super-timeline:**
```
ewfmount → imagemounter → log2timeline.py → psort.py -o l2tcsv → filter date/source → grep
```

**EZ Tools triage (faster, structured CSV per artifact):**
```
KAPE collect → MFTECmd / EvtxECmd / AmcacheParser / PECmd / AppCompatCacheParser / SBECmd
           → Hayabusa csv-timeline → Timeline Explorer
```

**Memory:**
```
WinPMEM/DumpIt → mem.dmp
vol windows.info → pstree → malfind → netscan → cmdline → dumpfiles --pid <p>
YARA on dumped → capa describe behavior
```

**Network:**
```
capture.pcap → zeek -r → conn.log/dns.log/http.log/ssl.log
            → suricata -r → eve.json alerts
            → bulk_extractor email/url/ip
            → RITA beacon detection
            → tshark targeted extraction
```

**Hunt-Evil log rapid triage:**
```
EvtxECmd --csv → Hayabusa csv-timeline → Chainsaw hunt --sigma → pivot top-confidence
```

---

## 4. Model Context Protocol (MCP)

### Architecture (TL;DR)

JSON-RPC 2.0 over **stdio** (subprocess pipes) or **Streamable HTTP**. Three primitives:

- **Tools** — callable functions with typed input/output schemas.
- **Resources** — readable data, URI-addressed.
- **Prompts** — server-supplied prompt templates.

Tagline Rob T. Lee uses: **"USB-C for AI."** Same plug, any tool.

Client (Claude Code / Claude Desktop / etc.) → spawns server subprocess (stdio) or connects HTTP → `initialize` handshake → enumerates tools/resources/prompts → invokes.

### Python SDK

`mcp` on PyPI. Two API levels: **FastMCP** (decorators, easy) and **low-level Server** (more control).

Minimal SIFT-shaped example, paste-ready:

```python
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession
from pydantic import BaseModel, Field
import subprocess

mcp = FastMCP("sift-forensics")

class AmcacheEntry(BaseModel):
    file_name: str = Field(description="Executable name")
    full_path: str
    sha1: str
    file_size: int | None = None
    publisher: str | None = None
    first_run: str | None = Field(default=None, description="ISO 8601 UTC")

class AmcacheResult(BaseModel):
    entries: list[AmcacheEntry]
    total: int
    case_id: str
    audit_id: str

@mcp.tool()
async def parse_amcache(
    hive_path: str,
    case_id: str,
    ctx: Context[ServerSession, None],
) -> AmcacheResult:
    """Parse the Amcache.hve hive and return structured execution records."""
    if not hive_path.startswith("/evidence/"):
        raise ValueError("hive_path must be under /evidence/ (read-only mount)")
    await ctx.info(f"Parsing {hive_path}")
    proc = subprocess.run(
        ["AmcacheParser", "-f", hive_path, "--csv", "/tmp/", "-c", case_id],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"AmcacheParser failed: {proc.stderr[:500]}")
    entries = _read_csv("/tmp/amcache.csv")  # server-side parse
    audit_id = _record_audit(case_id, "parse_amcache", hive_path, len(entries))
    return AmcacheResult(entries=entries, total=len(entries), case_id=case_id, audit_id=audit_id)

if __name__ == "__main__":
    mcp.run()  # stdio transport
```

Full reference + long-running ops examples in `refs/sdk-snippets.md`.

### The security argument (THE Constraint criterion argument)

| Risk | Generic `execute_shell` | Typed MCP tools |
|---|---|---|
| `dd if=/dev/zero of=/evidence/disk.E01` | Allowed | Tool doesn't exist |
| `rm -rf /evidence/case01` | Allowed | Tool doesn't exist |
| Mount evidence rw | Allowed | Function only does `ro,noexec,noload` |
| Run wrong tool on wrong artifact | Allowed (hallucinated cmdline) | Schema rejects mismatched input |
| Spoliate by writing to evidence | Allowed | Server enforces read-only paths via input validation |
| Audit trail | Shell history (junky) | Structured per-call audit IDs |
| Reproducibility | Cmdline string | Typed args = reproducible by replay |

**Architectural guardrail (function doesn't exist) > prompt guardrail ("don't write to /evidence").** Judges score this directly under Constraint Implementation.

### Best practices for SIFT MCP design (synthesized from Anthropic + Valhuntir)

1. **One tool = one forensic action.** `parse_mft`, `parse_amcache`, `run_volatility(plugin=...)`. Not `do_forensics`.
2. **Pydantic-typed I/O.** Schema is the contract.
3. **Path allowlist** (`/evidence/`, `/cases/<case_id>/`). Never accept arbitrary writes.
4. **Response envelope** with `audit_id`, `caveats`, `corroboration`, `discipline_reminder`. (Valhuntir's pattern.)
5. **Server-side parse** of tool output. Don't return raw stdout. Parse to typed objects.
6. **JSONL audit log per invocation** with `(ts, tool, args, result_hash, audit_id)`.
7. **Denylist of destructive commands** as defense-in-depth even though the architectural guardrail is the primary control.

---

## 5. Agentic framework reference

### Claude Code SDK (Agent SDK as of late 2025)

- Renamed Agent SDK to reflect broader use.
- Python + TypeScript. Same agent loop + tool use + context management as Claude Code.
- Four primitives: **tools, hooks, MCP servers, subagents**.
- MCP-native — pass `mcp_servers` dict; just works.
- Subagents = specialized agents with own context window, prompt, tool permissions.
- Hooks (PreToolUse, PostToolUse, Stop) — perfect for forensic audit.
- **Starting June 15, 2026: Agent SDK + `claude -p` usage on subscription plans draws from a new monthly Agent SDK credit, separate from interactive limits.** Coincides with submission deadline — relevant for cost planning if you do automated runs at the end.

### OpenClaw

- Real project. https://openclaw.ai/, https://github.com/mergisi/awesome-openclaw-agents (200+ templates).
- **Config-first, no-code**. Agents defined as `SOUL.md` markdown declaring persona, capabilities, MCP tools, channels (Telegram/Slack/Discord/email), rules.
- Node.js runtime, ~150MB binary, ~512MB RAM. Local gateway port `18789`.
- Multi-agent built in — many specialized agents with isolated memory.
- Model-agnostic: Claude, GPT-4o, Gemini, Ollama.
- Lifecycle: write SOUL.md → `openclaw agents add` → `openclaw gateway start`.
- **Why SANS named it alongside Claude Code:** quickest path for a non-engineer DFIR pro to ship a credible multi-agent setup. Weaker for hard architectural guardrails (still depends on MCP-typed tools underneath).

### Multi-agent frameworks for 2026

| Framework | Strength | Weakness | Verdict for Protocol SIFT |
|---|---|---|---|
| **LangGraph (LangChain)** v0.4 | Stateful graph orchestration. First-class persistence (checkpointers), HITL, time travel, streaming. Production-grade. | Verbose; you write the graph yourself. | **Best for credible multi-agent submission** — checkpoints become audit trail |
| **CrewAI** | Role-based ("you are the memory specialist"), quick to set up. Now has enterprise observability + scheduling. | Coordination is inferred — black-box for audit. Less message-flow control. | Fast to prototype but harder to defend on Constraint/Audit |
| **AutoGen / AG2** v1.0 GA (2026) | Event-driven, async-first, GroupChat coordination. Microsoft-backed. | More machinery; bigger surface area. | Solid if you want true async + pluggable orchestration |

### Pattern × judging criteria matrix

Scores: ✓✓✓ strong / ✓✓ ok / ✓ weak / ✗ penalty.

| Pattern | Autonomous Exec | IR Accuracy | Breadth | Constraint | Audit Trail | Usability |
|---|---|---|---|---|---|---|
| Direct Extension (Claude Code/OpenClaw + prompts) | ✓✓ | ✓✓ | ✓✓ | ✗ (prompt-based) | ✓✓ (hooks) | ✓✓✓ |
| **Custom MCP Server** (Valhuntir-shape) | ✓✓✓ | ✓✓✓ | ✓✓ | ✓✓✓ (architectural) | ✓✓✓ (typed) | ✓✓ (more setup) |
| **Multi-Agent over MCP** (Custom MCP + LangGraph) | ✓✓✓ | ✓✓✓ | ✓✓✓ | ✓✓✓ | ✓✓✓ (msg logs) | ✓ (complexity) |
| Multi-Agent over shell | ✓✓ | ✓ (no validation layer) | ✓✓ | ✗ | ✓✓ | ✓ |
| Alternative IDE (Cursor/Cline) | ✓✓ | ✓✓ | ✓✓ | ✗ (rules call this out) | ✓ | ✓✓✓ |

**The dominant pattern is Custom MCP Server, optionally layered with multi-agent (LangGraph or Agent SDK subagents) for breadth.** That's the path that scores ✓✓✓ on the heavy criteria — Autonomous Execution, IR Accuracy, Constraint, Audit Trail — which together drive placing.

---

## 6. Existing forensics MCP servers (prior art — do NOT duplicate)

| Project | Purpose | Tools | Verdict |
|---|---|---|---|
| **AppliedIR/sift-mcp** (Valhuntir) | Multi-backend MCP for SIFT-side forensics | 73 (90 + opensearch, 100 + wintools) | **The 800-lb gorilla.** Do not duplicate. |
| **AppliedIR/wintools-mcp** | Catalog-gated Windows tool execution | 10 | Same family |
| **AppliedIR/opensearch-mcp** | Evidence indexing into OpenSearch | 17 tools / 15 parsers | Same family |
| **AppliedIR/forensic-rag** | 22K-record semantic search across Sigma/MITRE/Atomic/Elastic/Splunk/LOLBAS/etc. | 3 tools | Bench-set the knowledge layer |
| **bornpresident/Volatility-MCP-Server** | Volatility 3 plugin exposure to Claude | 14 plugins (pstree, pslist, psscan, netscan, malfind, dlllist, filescan, cmdline, handles, memmap, custom plugin exec, dump discovery) | Single-purpose. Subset of Valhuntir's sift-mcp.run_command. |
| **socfortress/velociraptor-mcp-server** | Velociraptor live endpoint engine via MCP | 11 (Auth, GetAgentInfo, ListArtifacts × 4, CollectArtifact + Details, FindArtifactDetails, GetCollectionResults, RunVQLQuery) | Live-host triage. **Valhuntir does not cover live hosts. Real gap.** |
| **mgreen27/mcp-velociraptor** | Alt Velociraptor MCP | unknown | Earlier-stage. Confirms multiple Velociraptor MCPs exist. |
| **DFIR-IRIS MCP server** | DFIR-IRIS case management via MCP | 35 + KPI | Case-mgmt focused. Overlaps with Valhuntir's case-mcp / forensic-mcp / report-mcp. |

### Gap territory we can claim

Public MCP servers we did **NOT** find — these are credible novelty zones:

- **Plaso super-timeline MCP** as plugin-aware reasoning chain (not just `run_command`)
- **EZ Tools / Zimmerman MCP** as structured per-artifact functions
- **Hayabusa Sigma detection** as a standalone MCP server
- **YARA-rule-generation MCP** that emits rules from observed IOCs and tests them in-process
- **Adversarial-evidence sanitizer MCP** — strips/quarantines free-text fields before LLM consumption
- **Live-IR triage MCP** that targets Velociraptor + adds investigative agent layer above raw RunVQLQuery
- **Critic-agent MCP** that takes a finding bundle and challenges it against evidence
- **Volatility-plugin-aware reasoning MCP** that knows the `psscan→pslist→diff` pattern as a structured workflow

---

## Strategic implications (compressed)

1. **Do NOT rebuild Valhuntir.** Architecturally complete, well-maintained, MIT-licensed, ~14K LOC. You will lose any feature comparison.
2. **Lean into MCP from day 1.** Protocol SIFT (no MCP) is below the floor. Even a minimal MCP server with 5-10 well-chosen tools that demonstrate the self-correction wedge exceeds Protocol SIFT and differentiates from Valhuntir.
3. **Wedge candidates (orthogonal to Valhuntir, ranked by win-leverage):**
   1. **Closed-loop critic→revise self-correction agent** (top tiebreaker criterion + Rob's #1 quoted complaint about Protocol SIFT)
   2. **Structural adversarial-evidence defense** (Yotam Perkal + Jens Ernstberger will probe this)
   3. **Memory-first investigator** with Volatility plugin-aware reasoning chain (huge daily-use leverage, not in Valhuntir)
   4. **Live-host triage** via Velociraptor MCP + agentic guidance (Valhuntir is post-mortem only)
   5. **Measured hallucination reduction harness** with public answer keys (NIST cases have public PDFs)
4. **Bare-minimum architectural floor:** typed MCP server, audit log per call, finding schema matching Valhuntir's, MITRE ATT&CK tags, confidence levels, evidence registry with SHA-256.
5. **Velociraptor MCP servers exist — do not duplicate the wrapper layer.** If you go live-host, build the agentic layer on top of socfortress's or mgreen27's.
6. **The audit-trail + HMAC-ledger pattern is gold.** Even if you don't build the whole platform, your submission should produce an audit log that any examiner could verify post-hoc. This is what makes a forensic AI submission credible vs. a chatbot demo.
