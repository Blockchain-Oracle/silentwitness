# Sponsor Repos Deep Dive — Protocol SIFT / Find Evil! 2026

> All clones at `/tmp/protocol-sift-research/`. Both target repos were `git clone --depth 1`.
> Read date: 2026-06-02.

---

## TL;DR — The Single Most Important Finding

**Protocol SIFT (teamdfir) is a thin, prompt-library configuration of Claude Code** —
~10 files of CLAUDE.md system prompts, a permissions JSON, and 5 skill files. It is
**not** an agent framework, not an MCP server, not a runtime. It's "what to install in
`~/.claude/` to make Claude Code stop hallucinating on a SIFT VM."

**Valhuntir (AppliedIR) is the actual platform** the rules are pointing at as the
quality bar — **~14,000 LOC of Python**, **9 MCP backends**, **100 forensic tools**,
**HMAC-signed human-approval workflow**, a **bwrap kernel sandbox**, an **Examiner
Portal** (8-tab browser UI), and a **22,000-record forensic RAG**. It's already
deployed by a real DFIR practitioner (Steve Anson, AppliedIR) and is production-shape.

If you submit anything less than (Protocol-SIFT v2 with MCP) you are below the floor.
The wedge has to be something Valhuntir **doesn't** do — and Valhuntir is wide. The
best gaps we identified: (a) **adversarial-evidence robustness** (Valhuntir admits
HITL is "the primary defense" — implies a structural defense would be novel),
(b) **structural self-correction loop** (Valhuntir does response-level enrichment
but no closed-loop critique-revise), (c) **non-Claude-Code client parity** (the
sandbox/audit hooks are Claude-Code-only), (d) **memory-first** investigations
(Volatility 3 is exposed through sift-mcp but only as raw command execution — no
plugin-aware reasoning chain).

---

## 1. teamdfir/protocol-sift

**Repo:** https://github.com/teamdfir/protocol-sift
**Last commit (HEAD of main on read date):** `40bed7a Update README.md` (Mar 25, 2026)
**Stars/license:** Not surfaced via clone; description blank in teamdfir org listing.
**Languages on file:** Python, Shell, Markdown.
**Clone:** `/tmp/protocol-sift-research/protocol-sift`

### Architecture overview

This is a **configuration bundle for vanilla Claude Code running on a SIFT VM**. There
is no daemon, no MCP server, no agent framework. The install dumps 10 files into
`~/.claude/` and that's the whole product.

```
Claude Code (CLI binary)
    │
    ├── ~/.claude/CLAUDE.md         ← global system prompt ("Principal DFIR Orchestrator")
    ├── ~/.claude/settings.json     ← pre-approved tool list + Stop hook (audit log append)
    ├── ~/.claude/settings.local.json ← machine-local overrides (sudo apt)
    └── ~/.claude/skills/{memory-analysis,plaso-timeline,sleuthkit,windows-artifacts,yara-hunting}/SKILL.md
            ← loaded on-demand as domain prompt libraries
   per case:
    └── /cases/<CASE>/CLAUDE.md     ← per-case project prompt (FOR508 SRL template)
    └── /cases/<CASE>/analysis/generate_pdf_report.py  ← WeasyPrint PDF report engine
```

There is **no MCP server**. There is **no agent loop**. Claude Code is just running
`bash` commands directly, with an aggressively pre-approved allowlist, a `Stop`-hook
audit log, and skill files that teach it how to invoke each forensic tool correctly.

### Key files & purposes

| File | Lines | Purpose |
|---|---|---|
| `README.md` | 393 | Install instructions (curl one-liner / clone / ZIP), file-by-file rationale, chain-of-custody notes |
| `install.sh` | 191 | Bash installer — detects existing Claude Code, clones repo if not run locally, backs up existing `~/.claude/{CLAUDE.md,settings.json,settings.local.json}` with `.bak-<timestamp>`, copies all skill files, optionally installs WeasyPrint |
| `global/CLAUDE.md` | 75 | Global system prompt. Defines role ("Principal DFIR Orchestrator"), evidence-mode (read-only), forensic constraints (no hallucinations, UTC timestamps, write only to `./analysis/`, `./exports/`, `./reports/`), installed tool paths table, routing table from artifact-type → skill file |
| `global/settings.json` | 145 | Massive permission allowlist (~100 forensic CLI commands pre-approved: Volatility, Sleuth Kit, Plaso, EZ Tools, YARA, bulk_extractor, network tools, hashing tools). Deny list: `rm -rf`, `dd`, `wget`, `curl`, `ssh`, `WebFetch`. `Stop` hook appends conversation summary to `./analysis/forensic_audit.log` |
| `global/settings.local.json` | 11 | Local-only allows: `sudo apt`, `apt-cache search`, `psort.py`. Trivial. |
| `skills/memory-analysis/SKILL.md` | 379 | Volatility 3 + Memory Baseliner cookbook. 6-step methodology, every plugin documented, output redirect patterns to `./analysis/memory/`, error handling, anomaly indicators table |
| `skills/plaso-timeline/SKILL.md` | 294 | log2timeline / psort / pinfo / image_export reference. Filter syntax, parser presets, VSS handling, multi-plaso merge |
| `skills/sleuthkit/SKILL.md` | 409 | TSK + EWF tools — verify, mount, fls/icat workflow, timeline generation, bulk_extractor + PhotoRec carving |
| `skills/windows-artifacts/SKILL.md` | 721 | **The longest skill file.** EZ Tools (PECmd, AmcacheParser, MFTECmd, EvtxECmd, RECmd, SBECmd, JLECmd, LECmd, WxTCmd, SBECmd, RBCmd, SrumECmd, SQLECmd, bstrings), Autoruns/ASEP triage, Windows event-ID reference tables for Security/PowerShell/RDP/Defender/System/Tasks/WMI, USB device-chain registry queries |
| `skills/yara-hunting/SKILL.md` | 339 | YARA rule structure, PE/math/hash modules, performance ordering, IOC sweep workflow, community-rule sources (Neo23x0, Elastic, Mandiant). Also documents Velociraptor VQL as enterprise add-on but notes it's NOT a local binary |
| `case-templates/CLAUDE.md` | 199 | Per-case project CLAUDE.md template. Pre-populated with SRL FOR508 case (Stark Research Labs, CRIMSON OSPREY APT, dc01/rd01 hosts, attack timeline 2023-01-24/25). Examiner must strip + replace per new case |
| `analysis-scripts/generate_pdf_report.py` | (not read in detail; bullets in README) | WeasyPrint-based PDF report generator. Generated reports per-case import this and pass `DATA` dict + `output_path`. Critical gotcha noted: `body_html` must be `r"""..."""` raw string if it contains Windows paths |

### `install.sh` flow (step by step)

1. Preflight: require `curl` + `git`.
2. Check for Claude Code (`command -v claude`); if absent, fetch & run `https://claude.ai/install.sh` and re-source `~/.bashrc` / `~/.bash_profile` / `~/.profile` / `~/.zshrc`.
3. Locate repo files: if the script is being run from inside a checked-out copy, use that; else `git clone --depth=1 --quiet` to a tempdir and trap-rm on exit.
4. `mkdir -p ~/.claude/`.
5. For each of `CLAUDE.md`, `settings.json`, `settings.local.json` in `global/`: backup existing target as `.bak-<timestamp>`, then `cp` the new version.
6. For each skill in `{memory-analysis, plaso-timeline, sleuthkit, windows-artifacts, yara-hunting}`: `mkdir -p ~/.claude/skills/<skill>/`, `cp` the SKILL.md.
7. `mkdir -p ~/.claude/analysis-scripts/` + copy `generate_pdf_report.py`.
8. `mkdir -p ~/.claude/case-templates/` + copy `CLAUDE.md`.
9. If stdin is a TTY: prompt to install WeasyPrint (`pip3 install weasyprint`); if piped, skip with manual instructions. Falls back to suggesting `sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 libpango-1.0-0` if pip fails.
10. Print next-steps banner for starting a new case (`export CASE=...`, `mkdir /cases/...`, `cp` template, `cd && claude`).

### Current capability ("the baseline POC")

The repo as-shipped lets a SIFT user run `claude` from a case directory and have Claude
Code drive forensic tools end-to-end without permission prompts. Capabilities:

- Read-only evidence handling enforced **by prompt + write-path allowlist**, not by sandbox.
- Volatility 3 / Memory Baseliner against memory images.
- Plaso super-timelines + filtering.
- EZ Tools-driven Windows artifact parsing.
- YARA sweeps against mounted images and memory.
- Final WeasyPrint PDF report generation.

### Self-correction handling

**None at the code level.** The only `self-correct`-shaped construct is in
`global/CLAUDE.md`:

> Verification — Verify tool success after every run. On failure: read stderr →
> hypothesize → correct → retry.

This is **a single sentence in the system prompt**. There is no structured retry
loop, no critique step, no validator agent, no checkpoint that fires before
conclusions. The LLM is asked to be careful; that's it.

### Known limitations (from code + commit history)

- No MCP — every tool call is a raw `Bash(...)` invocation, which means:
  - No structured outputs back to the LLM (parses CSV/text via shell pipes).
  - No audit-log entry per tool call (only one summary at conversation end via `Stop` hook).
  - No way to enrich tool output with caveats / corroboration suggestions / forensic discipline reminders at the point of use.
- **No human approval gate.** The LLM writes findings as plain text into `./analysis/` and `./reports/`. There is no DRAFT/APPROVED state, no signing, no examiner password.
- **No agent constraint enforcement.** Skill files are guidance — Claude Code can ignore them.
- **No multi-examiner support.** Single-user, single-case.
- **Generated PDF reports are case-specific scripts** Claude writes per-investigation; reuse is manual.
- **Network exfil is blocked only by prompt + `deny: [wget, curl, ssh, WebFetch]`.** A clever shell trick (e.g., `python3 -c 'urllib.request...'`) is not on the denylist.
- **The case template ships with SRL FOR508 lab data hardcoded.** First step on a new engagement is strip-and-replace.
- **No VSCMount / MemProcFS** on Linux SIFT — Windows-only artifacts must move to a separate Windows analysis VM.

### What protocol-sift is asking us to do

Per the README and the directory layout: **extend `~/.claude/skills/`**, add new
skill files, or build a project CLAUDE.md that orchestrates the existing skills
better. The rules-of-engagement encourage adding capability (more skills, more
artifact types, an MCP server, better self-correction) on top of this baseline.

---

## 2. AppliedIR/Valhuntir — the bar to beat

**Repo:** https://github.com/AppliedIR/Valhuntir
**Last commit:** `ce1ae36 Update mkdocs-material requirement from >=9.5 to >=9.7.6 (#8)` (June 2026 — actively maintained, dependabot churn)
**License:** MIT
**Author:** Steve Anson (AppliedIR). Built with Claude Code (Anthropic).
**Disclosure:** Author states "I do DFIR. I am not a developer. This project would not exist without Claude Code handling the implementation."
**Clone:** `/tmp/protocol-sift-research/valhuntir`

This repo is just the **vhir CLI** + architecture docs. The actual MCP server code
lives in three sibling repos (also AppliedIR):
- **sift-mcp** — monorepo: 11 packages, the gateway + 7 backends
- **opensearch-mcp** — evidence indexing/querying (17 tools, 15 parsers)
- **wintools-mcp** — Windows tool execution (10 tools, 31 catalog entries)

We only cloned Valhuntir, but the architecture docs are thorough enough to reconstruct
the platform shape.

### Top-level scale

| Metric | Value |
|---|---|
| MCP backends | 9 (8 SIFT-local stdio + wintools-mcp HTTP) |
| Total MCP tools | 100 (73 without opensearch, 90 with, 100 with wintools) |
| Forensic-knowledge tool catalog | 59 tools × 17 categories |
| Windows triage baseline records | 2.6 million |
| Forensic RAG records | 22,000+ across 23 authoritative sources |
| OpenSearch parsers | 15 (evtx, 10 EZ Tools, Volatility 3, JSON/JSONL, delimited, access logs, W3C, MPLog, schtasks, WER, SSH, PowerShell transcripts, Prefetch/SRUM) |
| Hayabusa Sigma rules auto-applied after evtx ingest | 3,700+ |
| Defense layers (HITL controls) | 9 |
| Total resource req | 16 GB RAM (basic SIFT) → 32 GB (with OpenSearch); 50–100 GB disk + evidence |
| vhir CLI Python LOC (commands only) | ~10,400 |
| Total commands | 24 vhir CLI commands |

### Architecture (verbatim from `docs/architecture.md`)

Three layers:
1. **Gateway layer** — HTTP entry point, auth, request routing, Examiner Portal (sift-gateway :4508)
2. **MCP backends** — Specialized stdio subprocesses (forensic-mcp, case-mcp, report-mcp, sift-mcp, forensic-rag-mcp, windows-triage-mcp, opencti-mcp, opensearch-mcp)
3. **Tool layer** — Forensic tool execution, knowledge DBs, OpenSearch evidence index

```
LLM Client → MCP Streamable HTTP → sift-gateway :4508 → stdio → 8 backends
                                                       → /portal/ → Examiner Portal (browser)
LLM Client → HTTPS → wintools-mcp :4624 (separate Windows VM)
LLM Client → streamable-http → remnux-mcp :3000 (separate REMnux VM, optional)
```

Authentication: Bearer token `Authorization: Bearer vhir_gw_<24 hex>` (96 bits of
entropy). Per-examiner API key in `gateway.yaml`. Health check exempt.

### MCP backend breakdown

| Backend | Tools | Role |
|---|---|---|
| **forensic-mcp** | 23 (9 core + 14 discipline) | Investigation state machine. `record_finding`, `record_timeline_event`, `validate_finding`, plus 14 discipline tools/resources (`get_investigation_framework`, `get_rules`, `get_checkpoint_requirements`, `get_evidence_standards`, `get_confidence_definitions`, `get_anti_patterns`, `get_tool_guidance(tool_name)`, `get_false_positive_context`, `get_corroboration_suggestions`, `list_playbooks`, `get_playbook(name)`, `get_collection_checklist(artifact_type)`) |
| **case-mcp** | 15 | Case lifecycle: `case_init`, `case_activate`, `case_list`, `case_status` (dynamically detects available platform via `importlib.util.find_spec()`), evidence ops, audit/reasoning logging, export/import, backup, dashboard launcher |
| **report-mcp** | 6 | Data-driven report profiles (full / executive / timeline / ioc / findings / status). Bidirectional reconciliation against HMAC verification ledger. Zeltser IR Writing MCP integration for narrative templates |
| **sift-mcp** | 5 | Linux forensic tool execution. `run_command`, `list_available_tools`, `get_tool_help`, `check_tools`, `suggest_tools`. Denylist-protected (mkfs/shutdown/kill/nc blocked). Cataloged tools get FK-enriched responses |
| **forensic-rag-mcp** | 3 | Semantic search across 22K records. `search_knowledge(query, top_k, source, source_ids, technique, platform)`, `list_knowledge_sources`, `get_knowledge_stats` |
| **windows-triage-mcp** | 13 | Offline baseline validation. `check_file`, `check_process_tree`, `check_service`, `check_scheduled_task`, `check_autorun`, `check_registry`, `check_hash` (LOLDrivers), `analyze_filename` (unicode/typosquat detection), `check_lolbin`, `check_hijackable_dll`, `check_pipe`, `get_db_stats`, `get_health`. UNKNOWN verdict explicitly defined as "neutral, not suspicious" |
| **opencti-mcp** | 8 | Threat intel. Rate-limited (60/min default) + circuit breaker (opens after 5 failures, recovers after 60s). Read-only |
| **opensearch-mcp** (optional) | 17 (8 query + 6 ingest + 2 enrichment + 1 detection) | Evidence indexing. Deterministic content-based document IDs (re-ingest = 0 dupes). Full provenance fields (`host.name`, `vhir.source_file`, `vhir.ingest_audit_id`). 15 parsers. Hayabusa Sigma auto-runs post-evtx-ingest |
| **wintools-mcp** (separate) | 10 | Windows-side forensic tool execution. 31 catalog entries (zimmerman.yaml=14, sysinternals=5, memory=4, timeline=3, analysis=3, collection=1, scripts=1). Hardcoded denylist of 20+ binaries (cmd, powershell, pwsh, wscript, cscript, mshta, rundll32, regsvr32, certutil, bitsadmin, msiexec, bash, wsl, sh, msbuild, installutil, regasm, regsvcs, cmstp, control). Argument sanitization blocks shell metacharacters, `@filename` response-file syntax, `-e/-enc` flags |

### Self-correction implementation

**Multiple layers, NO single closed-loop critique step.** Valhuntir's self-correction
story is *defense-in-depth at the response envelope level*, not a critique-revise
agent loop. Specifically:

1. **`validate_finding(finding_json)`** — forensic-mcp tool the LLM is supposed to
   call **before** `record_finding()`. Returns structured assessment of issues
   (missing fields, insufficient evidence, anti-pattern matches).
2. **Hard gate in `record_finding()`** — server-side enforcement that rejects:
   - NONE-provenance findings (no audit trail at all)
   - Findings whose source files are not in the evidence registry
   - Findings whose claimed audit_ids don't exist
   - Classifies provenance as MCP > HOOK > SHELL > NONE
3. **Grounding score** — computed at finding-stage time. Returns advisory
   STRONG / PARTIAL / WEAK based on whether 2+/1/0 reference backends were
   consulted (forensic-rag, windows-triage, opencti). Does **not** block, just
   informs the examiner.
4. **Rotating discipline reminders** — every tool response carries one of 15+
   reminders ("Absence of evidence ≠ evidence of absence", "Shimcache and
   Amcache prove file PRESENCE, never execution"). Deterministic modulo
   rotation across the session.
5. **Stale-content detection** — when applying portal-pending edits, fields
   that changed since review are skipped with `field 'X' changed since review`
   error. Content hash mismatches between staging and approval are surfaced.

**Verdict on self-correction:** Valhuntir does **prompt-level rotation and
structural validation gates**, not an explicit critic→revise loop. This is a
real wedge for us: a structural self-correction agent loop ("after every N
findings, fire a critique pass against the latest findings + their evidence,
emit a self-assessment, gate further work on resolving low-confidence items")
is **not** in Valhuntir.

### Accuracy validation implementation

Not just one mechanism — Valhuntir stacks five:

1. **`validate_finding()` pre-check** — described above. Schema + methodology
   conformance.
2. **Evidence registry + SHA-256 hashes** — every evidence file SHA-256-hashed
   at registration. `vhir evidence verify` re-hashes on demand. Findings cite
   `audit_ids` that must trace back to entries in the registry.
3. **Content hash on findings** — `compute_content_hash(item)` runs at staging
   and at approval. If they differ, the approval log includes a
   `stale_at_approval=True` marker.
4. **HMAC verification ledger (L2 — cryptographic guarantee)** — at approval
   time, an HMAC-SHA256 over the substantive text (observation +
   interpretation for findings; description for timeline events) is computed
   with a key derived via PBKDF2-SHA256 (600,000 iterations) from the
   examiner's password. Stored at `/var/lib/vhir/verification/{case_id}.jsonl`
   (mode 0700 dir, 0600 file). The LLM **cannot forge entries** because the
   key derives from a password it doesn't have. `vhir review --verify`
   re-derives and checks.
5. **Bidirectional report reconciliation** — `report-mcp.generate_report()`
   cross-checks approved items against the ledger and surfaces:
   - `APPROVED_NO_VERIFICATION` (approved but no ledger entry)
   - `VERIFICATION_NO_FINDING` (ledger entry with no current finding)
   - `DESCRIPTION_MISMATCH` (substantive text changed post-signing)
   - Count mismatches

**Code paths:**
- `src/vhir_cli/verification.py:33` — `derive_hmac_key(password, salt)` (PBKDF2-SHA256, 600K iters)
- `src/vhir_cli/verification.py:38` — `compute_hmac(derived_key, description)` (HMAC-SHA256)
- `src/vhir_cli/verification.py:45-54` — `write_ledger_entry()` writes to `/var/lib/vhir/verification/{case_id}.jsonl`, fsyncs, chmod 0600
- `src/vhir_cli/verification.py:82-98` — `verify_items()` uses `hmac.compare_digest` (constant-time)
- `src/vhir_cli/verification.py:101-165` — `rehmac_entries()` re-signs ledger on password rotation
- `src/vhir_cli/approval_auth.py:249-271` — `verify_password()` PBKDF2 + `secrets.compare_digest`
- `src/vhir_cli/commands/approve.py:552-621` — `_write_verification_entries()` integrated into the approve flow

### Audit trail implementation

**Every** MCP tool call writes a JSONL entry to a per-backend log under `audit/`
in the case directory:

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

`audit_id` is a stable cross-reference: findings cite audit_ids, audit_ids
resume sequence numbering across process restarts. PostToolUse hook captures
every Bash command from Claude Code to `claude-code.jsonl` with SHA-256
hashes — that's what gives a finding its HOOK-tier provenance.

`vhir audit log [--mcp <backend>] [--tool <name>] [--limit N]` and
`vhir audit summary` query this trail.

### Constraint model

**Both architectural and prompt-based, in nine layers** (verbatim from `docs/security.md`):

| Layer | Control | Type | Scope |
|---|---|---|---|
| L1 | Structural approval gate (DRAFT → APPROVED requires password) | Structural | All clients |
| L2 | HMAC verification ledger (PBKDF2 + HMAC-SHA256) | Cryptographic | All clients |
| L3 | Case data deny rules (41 rules blocking Edit/Write/Bash) | Permission | Claude Code only |
| L4 | Sandbox filesystem `denyWrite` via bwrap | Kernel | Claude Code only |
| L5 | File permission chmod 444 after write | Filesystem | All clients (advisory) |
| L6 | Bidirectional report reconciliation | Integrity | All clients |
| L7 | Password authentication (CLI + portal challenge-response) | Authentication | All clients |
| L8 | Provenance enforcement (MCP > HOOK > SHELL > NONE) | Structural | All clients |
| L9 | Kernel sandbox (bubblewrap namespaces, `--unshare-net`, `--unshare-pid`) | Kernel | Claude Code only |

**Critical Claude-Code-specific structural pieces** (from
`setup-client-linux.sh:543-655`):

- **Deny rules in `.claude/settings.json`** — 41 entries blocking `Edit`/`Write`
  to `findings.json`, `timeline.json`, `approvals.jsonl`, `todos.json`,
  `CASE.yaml`, `actions.jsonl`, `audit/*.jsonl`, `evidence.json`,
  `pending-reviews.json`, `/var/lib/vhir/**`, plus the `.claude/` and `.vhir/`
  control files themselves. Plus `Bash(vhir approve*)`, `Bash(*vhir approve*)`,
  `Bash(vhir reject*)`, `Bash(*vhir reject*)`.
- **Sandbox config**:
  ```json
  "sandbox": {
    "enabled": true,
    "allowUnsandboxedCommands": false,
    "filesystem": {
      "denyWrite": [
        "~/.vhir/gateway.yaml", "~/.vhir/config.yaml",
        "~/.vhir/active_case", "~/.vhir/hooks",
        "~/.vhir/.password_lockout", "~/.vhir/.pin_lockout",
        "~/.claude/settings.json", "~/.claude/CLAUDE.md", "~/.claude/rules"
      ]
    }
  }
  ```
- **`UserPromptSubmit` hook** — injects `<forensic-rules>PLAN before 3+ steps |
  EVIDENCE for claims | APPROVAL before conclusions | RECORD actions via
  forensic-mcp | NO DELETE without approval</forensic-rules>` before every
  user prompt.
- **`PostToolUse` hook on `Bash` matcher** — runs `forensic-audit.sh` that
  captures every Bash command + SHA-256 hash + output to
  `audit/claude-code.jsonl`.

**Provenance enforcement code path** (from `architecture.md` + `approve.py`): findings
must trace to either an MCP audit_id (auto-discovered from per-backend JSONL) or
a HOOK audit_id (claude-code.jsonl) or examiner-supplied `supporting_commands`.
NONE = hard reject in `record_finding()`.

### Output structure — report template + example finding

**Finding schema (from `approve.py` field handling + `_display_item`):**

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

**Timeline event schema:**

```json
{
  "id": "T-alice-001",
  "timestamp": "<iso8601 UTC>",
  "description": "...",
  "source": "...",
  "auto_created_from": "F-alice-001",  // findings can auto-spawn timeline events
  "examiner_modifications": {...},
  "status": "DRAFT|APPROVED|REJECTED",
  ...
}
```

**Reports** are generated through 6 profiles (full / executive / timeline / ioc /
findings / status). The LLM renders narrative; `report-mcp.generate_report()`
returns structured JSON + Zeltser IR Writing guidance, then `save_report()`
persists to `case/reports/`. Only APPROVED items appear.

### Lessons we should steal

1. **MCP-based architecture beats raw Bash.** Every tool call gets a structured
   envelope (audit_id, caveats, advisories, corroboration suggestions,
   field_meanings, discipline_reminder, data_provenance marker).
2. **The Forensic Knowledge (FK) enrichment system.** YAML-defined per-tool
   contexts that the MCP response layer injects, with token-budget decay
   (caveats always; advisories first-3-calls then every-10th). Brilliant —
   delivers methodology AT the point of need, not in the system prompt where
   the LLM drifts away from it.
3. **Provenance tier classification** (MCP > HOOK > SHELL > NONE) — the
   server-side rejects findings with no audit trail. We should adopt this.
4. **HMAC-signed ledger outside the sandbox** at `/var/lib/vhir/...`. Even if
   the LLM owns the case directory entirely it can't forge approval entries.
   Cryptographic > prompt-based for any defense layer.
5. **`data_provenance: tool_output_may_contain_untrusted_evidence`** marker on
   every response — explicit prompt-injection-resistance signal.
6. **Resource exposure (MCP `Resources` API) vs Tool exposure** — Valhuntir
   exposes 14 discipline items as `Resources` by default, with a
   `reference_mode="tools"` fallback for clients without resource support.
   Clean abstraction.
7. **Per-examiner ID prefix** (`F-alice-001`, `T-bob-003`, `TODO-alice-001`)
   for global uniqueness across multi-examiner merges. Conflict-free.
8. **Examiner Portal (browser UI)** is the primary review surface; CLI is
   secondary. Challenge-response auth — password never leaves the browser.
9. **Two reasoning logs the LLM voluntarily writes:**
   `case-mcp.log_reasoning(text)` and `case-mcp.record_action(...)` — append-only
   to audit trail. Captures hypothesis-formation in a way that's auditable.
10. **The grounding score returned from `record_finding()`** — STRONG/PARTIAL/WEAK
    based on whether reference backends were consulted. Advisory, not blocking.
    Cheap to compute, surfaces "you didn't check your work" to the examiner.

### Lessons we should beat

1. **No closed-loop critique-revise self-correction.** Valhuntir leans on
   prompt-rotation and structural gates. A separate critic agent that fires
   periodically (or after every finding-stage) to re-read evidence and
   challenge the finding — and gates further work on resolving low-confidence
   items — is unbuilt.
2. **HITL is admitted as "primary defense" against adversarial evidence.** That's
   *human* primary defense. A *structural* defense against prompt injection in
   evidence (e.g., a quarantining/escaping layer for any LLM-bound free-text
   field, or a separate "untrusted-evidence-reader" agent that translates raw
   evidence into structured/sanitized form before the investigator agent sees
   it) is a real gap.
3. **Claude-Code-only sandbox / deny rules / audit hooks** (L3, L4, L9). Other
   MCP clients (Claude Desktop, LibreChat) get MCP-level guidance only.
   Bringing structural controls to those clients via an MCP-resident proxy /
   gateway-side enforcement is open.
4. **The forensic-mcp findings state machine is rich, but synchronous and
   examiner-blocking.** No asynchronous AI-self-review pass before HITL
   review — the human gets a raw DRAFT pile. An LLM-driven pre-review pass
   that flags weak findings, suggests merges, surfaces duplicates, etc. would
   reduce examiner cognitive load.
5. **Memory analysis is exposed as raw Volatility commands via sift-mcp.run_command.**
   There's no Volatility-plugin-aware reasoning agent that knows the
   `psscan→pslist→diff` pattern, the `malfind→dumpfiles→YARA→VirusTotal`
   pattern, etc., and runs them as structured workflows. We could build a
   memory-first investigator that beats this.
6. **No live-system support.** Valhuntir is post-mortem only (disk images,
   memory dumps, KAPE triage output). A live-host triage workflow via
   Velociraptor MCP + agentic guidance is open.
7. **The Examiner Portal is a "8-tab browser UI" but the architecture
   suggests it's a static HTML/JS app served by the gateway.** A live
   investigation HUD with real-time agent traces / tool-call streaming would
   be a much better demo.
8. **The platform is heavyweight.** 16–32 GB RAM, ~14 GB disk for the
   recommended install. A genuinely lightweight wedge (sub-200MB install,
   sub-2GB RAM, works on a laptop) that hits the rubric items could win.

---

## 3. sans-dfir/sift — platform inventory

> Did not clone (OVA is GB). Surfaced via web fetch.

**Status:** `sans-dfir/sift` is a metadata/issue-tracking repo. The actual SIFT
deploy logic lives in **`teamdfir/sift-saltstack`** under `teamdfir` org, which
is consumed by **Cast** (the successor to sift-cli) via:

```
sudo cast install teamdfir/sift-saltstack
```

**Packaging strategy:**
- **Base:** Ubuntu (20.04 Focal / 22.04 Jammy supported)
- **Config management:** SaltStack (`teamdfir/sift-saltstack`)
- **VM build:** Packer (`teamdfir/sift-packer`)
- **Installer:** Cast (single binary, distro-agnostic)
- **Cloud:** Pre-built AMIs on AWS across multiple regions
- **Container:** Dockerfiles in `teamdfir/sift-dockerfiles`

**Tool inventory:** No explicit list surfaced in the GitHub READMEs. Tool
inventory is implied by `protocol-sift/skills/` (which targets a SIFT-installed
machine) and Valhuntir's `forensic-knowledge` package (which catalogs 59 tools
across 17 categories):

| Category | Tools (per Valhuntir FK catalog) |
|---|---|
| **Disk forensics** | fls, icat, mmls, blkls (Sleuth Kit), ewfmount, ewfacquire, dc3dd |
| **Memory forensics** | Volatility 3 (vol3), winpmem, Memory Baseliner |
| **Network forensics** | tshark, zeek |
| **Log analysis** | hayabusa (Sigma), chainsaw, log2timeline, psort |
| **Triage / collection** | KAPE, densityscout, Velociraptor (enterprise) |
| **Anti-forensics detection** | (covered via baseline DB comparisons in Valhuntir's windows-triage-mcp) |
| **Windows artifacts (EZ Tools)** | AmcacheParser, PECmd, AppCompatCacheParser, RECmd, MFTECmd, EvtxECmd, JLECmd, LECmd, SBECmd, RBCmd, SrumECmd, SQLECmd, bstrings, WxTCmd |
| **Carving** | bulk_extractor, foremost, scalpel, photorec |
| **Malware** | yara, strings, ssdeep, binwalk, capa, densityscout, moneta, hollows_hunter, sigcheck, maldump, 1768_cobalt |
| **Registry** | regripper |
| **Hashing** | hashdeep, ssdeep |
| **Persistence** | autorunsc |
| **Browser** | hindsight |
| **Logs** | logparser |

**Most-relevant tools for an agent's first 90% of work** (per Protocol SIFT skill files):
- **Memory:** Volatility 3 (`/opt/volatility3-2.20.0/vol.py`), Memory Baseliner
- **Timeline:** Plaso (log2timeline.py, psort.py, pinfo.py)
- **Filesystem:** fls / icat / mmls / mactime / tsk_recover, ewfmount
- **Windows artifacts:** EZ Tools suite (dotnet runtime)
- **Threat hunting:** YARA (4.1.0), hayabusa

---

## 4. sans-dfir org survey

(Verified by WebFetch on https://github.com/sans-dfir — returned 404, so org listing
is unsurfaced. The `sans-dfir/sift` and `sans-dfir/sift-cli` repos exist but the
org-index page failed.)

What we know exists under `sans-dfir/`:
- `sans-dfir/sift` — metadata/issue tracker (no actual tool code)
- `sans-dfir/sift-cli` — **archived 2023-03-25**, deprecated in favor of `cast`

**Verdict:** sans-dfir is publishing branding + tracking only. The actual code
lives under `teamdfir/`.

---

## 5. teamdfir org survey

(Via WebFetch on https://github.com/orgs/teamdfir/repositories)

| Repo | Description | Lang | Last commit | Relevance |
|---|---|---|---|---|
| **sift-saltstack** | Salt States for Configuring the SIFT Workstation | Python | 2026-05-17 | **High** — actual install logic |
| **sift-packer** | Packer for building SIFT Workstation | Shell | 2026-04-19 | Medium — VM builds |
| **protocol-sift** | (no description) | Python | **2026-03-25** | **THIS REPO** |
| sift-scripts | Bunch of random 3rd party scripts | — | 2025-01-22 | Low |
| sift-dockerfiles | Docker images for SIFT | Dockerfile | 2025-01-10 | Low |
| volatility-plugins-community | Community Volatility plugins | Python | 2024-09-18 | Medium — plugin reference |
| sift | "SIFT" (minimal description) | — | 2024-02-14 | Low |
| sift-cli | CLI tool to manage a SIFT Install | JavaScript | 2023-03-25 | Archived |
| package-scripts | Files for SIFT PPA | Dockerfile | 2023-01-27 | Low |
| friends | Sigstore user stories | — | 2021-08-16 | Irrelevant |
| sift-packer-legacy | Old packer.io scripts | Shell | 2020-08-29 | Irrelevant |
| concordance | SANS DFIR course term concordances | — | 2020-08-07 | Low |
| sift-jenkins-dsl | (Jenkins) | Groovy | 2019-07-18 | Irrelevant |
| sift-bootstrap | SIFT Bootstrap Script | Shell | 2017-06-20 | Irrelevant |
| chocolateypackages | (Chocolatey packages) | — | 2017-01-05 | Irrelevant |

**No** other repos tagged `mcp`, `agentic`, `ai`, or `find-evil`. Protocol SIFT
is the only agentic / AI work surface in either org.

---

## 6. Existing forensics MCP servers (prior art)

| Project | Purpose | Tools | Verdict |
|---|---|---|---|
| **AppliedIR/sift-mcp** (Valhuntir) | Multi-backend MCP for SIFT-side forensics | 73 (90 + opensearch, 100 + wintools) | **The 800-lb gorilla.** Do not duplicate. |
| **AppliedIR/wintools-mcp** | Catalog-gated Windows tool execution | 10 | Same project family |
| **AppliedIR/opensearch-mcp** | Evidence indexing into OpenSearch | 17 tools / 15 parsers | Same project family |
| **bornpresident/Volatility-MCP-Server** | Volatility 3 plugin exposure to Claude | 14 plugins (pstree, pslist, psscan, netscan, malfind, dlllist, filescan, cmdline, handles, memmap, custom plugin exec, dump discovery) | Single-purpose, narrow. Subset of what Valhuntir's sift-mcp.run_command does. |
| **socfortress/velociraptor-mcp-server** | Velociraptor endpoint engine via MCP | 11 (Auth, GetAgentInfo, ListArtifacts × 4, CollectArtifact, CollectArtifactDetails, FindArtifactDetails, GetCollectionResults, RunVQLQuery) | Live-host triage. Valhuntir does not cover live hosts. **Real gap.** |
| **mgreen27/mcp-velociraptor** | Alternative Velociraptor MCP bridge | unknown | Earlier-stage. Confirms multiple Velociraptor MCPs exist. |
| **DFIR-IRIS MCP server** (`dfirmesi-iris-mcp-server`) | DFIR-IRIS case management via MCP | 35 functions + KPI metrics | Case-mgmt focused. Overlaps with Valhuntir's case-mcp / forensic-mcp / report-mcp. |
| **AppliedIR/forensic-rag** (in sift-mcp monorepo) | 22K-record semantic search across Sigma/MITRE/Atomic/Elastic/Splunk/LOLBAS/etc. | 3 tools | Bench-set the knowledge layer. |

**Public MCP servers we did NOT find** (gap territory we can claim):

- **Plaso super-timeline MCP** — log2timeline / psort exposed structurally as tools (Valhuntir wraps it via run_command, but no plugin-aware reasoning chain).
- **EZ Tools / Zimmerman tools MCP** specifically (covered by wintools-mcp as raw catalog entries).
- **Hayabusa Sigma detection MCP** (Valhuntir does post-evtx-ingest Hayabusa auto-application, but not a standalone server).
- **YARA-rule-generation MCP** that emits rules from observed IOCs and tests them in-process.
- **Adversarial-evidence sanitizer MCP** — strips/quarantines free-text fields before LLM consumption.
- **Live-IR triage MCP** that targets Velociraptor + adds an investigative agent layer above the raw RunVQLQuery.

---

## Strategic implications

1. **Do NOT rebuild Valhuntir.** It is feature-complete for the Protocol SIFT
   problem statement, well-architected, MIT-licensed, and actively maintained
   by a real DFIR practitioner with Anthropic-credited build-out. We will lose
   any head-to-head feature comparison. The wedge must be **orthogonal**, not
   competing.
2. **Self-correction is the cleanest wedge.** Valhuntir does prompt-level
   rotation + structural gates, **no closed critique-revise loop**. Building
   an explicit critic-agent loop that runs over staged findings before
   examiner review, scoring each finding against its evidence and gating
   weak ones for revision, fits the rubric ("Self-correction handling")
   directly and is **not** in the incumbent.
3. **Adversarial-evidence robustness is the second-cleanest wedge.** Valhuntir
   admits HITL is the primary defense — a structural defense (e.g., a
   quarantine layer for any free-text evidence field, or a separate
   sanitizer-agent stage) is a credible novelty.
4. **Don't try to win on tool coverage.** Valhuntir has 100 tools. Anything
   smaller is below par. We must wrap or extend, not replace.
5. **Lean into MCP from day 1.** Protocol SIFT (no MCP) is below the floor.
   Even a minimal MCP server with 5 well-chosen tools that demonstrate the
   self-correction wedge will exceed Protocol SIFT and differentiate from
   Valhuntir.
6. **Velociraptor MCP servers exist — do not duplicate the wrapper layer.**
   If we go live-host, build on socfortress/velociraptor-mcp-server (or
   mgreen27/mcp-velociraptor) and add the agentic layer above it.
7. **The audit-trail and HMAC-ledger pattern is gold.** Even if we don't
   build the whole platform, our submission should produce an audit log that
   any examiner could verify post-hoc. This is what makes a forensic AI
   submission credible vs. a chatbot demo.
8. **Match Valhuntir's bar on output structure.** Findings should have
   `observation` / `interpretation` / `confidence` / `confidence_justification`
   / `audit_ids` / `iocs` / `mitre_ids`. Reports should support the same 6
   profiles (full / executive / timeline / ioc / findings / status). This is
   table-stakes formatting, not differentiation.
