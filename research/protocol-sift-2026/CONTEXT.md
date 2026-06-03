# CONTEXT — Find Evil! / Protocol SIFT 2026

> **LOAD THIS FILE FIRST.** This is the agent entrypoint for all research on this hackathon.
> Compiled by 4 parallel research subagents + synthesis pass.
> Last updated: **2026-06-02**

---

## What this hackathon is

**FIND EVIL!** is a hackathon sponsored by **SANS Institute** to build autonomous AI incident-response agents on the SANS SIFT Workstation. The agents extend **Protocol SIFT** — an existing proof-of-concept that connects Claude Code to SIFT forensic tools via the Model Context Protocol (MCP). The hackathon exists because SANS published Protocol SIFT in Nov 2025 alongside their disclosure of GTG-1002 — a Chinese state-sponsored operation where Claude Code autonomously executed 80–90% of an espionage campaign using the same architecture for offense. The mission: close the speed gap between offensive AI and human-driven defense.

**Platform:** Devpost
**URL:** https://findevil.devpost.com/
**Sponsor:** SANS Institute ([@SANSInstitute](https://x.com/SANSInstitute))
**Submission window:** Apr 15 2026 → **Jun 15 2026 11:45 PM EDT**
**Days remaining as of 2026-06-02:** **~13 days**
**Registered participants:** 3,861

---

## Target track

**There is only one track.** Single classification by judging criteria across all submissions.

**Why we're entering:** $22K cash + Summit pass + OnDemand course + SANS Webcast slot is meaningful. More importantly, the winning submission "will be reviewed for integration back into Protocol SIFT" (Rob T. Lee). The post-hackathon Protocol SIFT standard is the meta-prize.

**Prize structure:**

| Place | Cash | Other |
|---|---|---|
| 1st (SLAYED EVIL) | $10,000 | Summit pass + OnDemand course (per member) + Webcast slot |
| 2nd (HUNTED EVIL) | $7,500 | Same as 1st |
| 3rd (FOUND EVIL) | $4,500 | OnDemand course (per member) |

**Judging criteria (6 equally weighted; tiebreaker order is the listed order):**
1. **Autonomous Execution Quality** (tiebreaker) — self-correction, failure handling
2. **IR Accuracy** — findings correct, hallucinations flagged, confirmed vs inferred distinguished
3. **Breadth and Depth** — depth on few evidence types > shallow coverage of many
4. **Constraint Implementation** — architectural > prompt-based, tested for bypass
5. **Audit Trail Quality** — every finding traces to specific tool execution
6. **Usability and Documentation** — reproducible by other practitioners

Full deep-dive: `01-prizes-tracks.md`.

---

## Key verified facts

| Field | Value | Source |
|---|---|---|
| Total prize pool | $22,000+ cash + ~$60K in courses/passes | Devpost listing |
| Submission deadline | 2026-06-15 11:45 PM EDT | Devpost rules |
| Eligible tech stack | SIFT Workstation + Claude Code / OpenClaw / Custom MCP / LangGraph / AutoGen / CrewAI / Cursor / Cline / Aider | Devpost rules |
| Mandatory architecture pattern | Agentic framework as primary execution engine; Custom MCP Server explicitly noted as "most sound architecture" | Devpost rules |
| Team size | 1–5 (solo permitted) | Devpost rules |
| Prior work allowed | Open-source libraries + SIFT codebase as foundation; novel contribution must be documented | Devpost rules |
| License | MIT or Apache 2.0 only | Devpost rules |
| Deliverables | 8 mandatory (repo, video ≤5min w/ live terminal, architecture diagram, write-up, dataset doc, accuracy report, setup instructions, structured execution logs) | Devpost rules |
| Judges | 48 panel (Rob T. Lee primary; Yotam Perkal + Jens Ernstberger will audit MCP security; Ovie Carroll + Cheri Carr + Amanda Rankhorn care about chain-of-custody; enterprise SOC weighting from Palo Alto/Mandiant/AWS/Lockheed) | Devpost listing |

---

## What exists in the field

**Devpost gallery scraped:** **NO** — unpublished until after Jun 15 close
**GitHub-discoverable competitor builds:** 1 known (`marez8505/find-evil`, 1 star, MIT, Direct Extension w/ Flask UI)
**Sponsor-explicit reference:** **Valhuntir** by Steve Anson / AppliedIR — cited in the rules as "the level of quality to meet/exceed"

### The two artifacts that define the field

| Repo | What it is | Verdict |
|---|---|---|
| [teamdfir/protocol-sift](https://github.com/teamdfir/protocol-sift) | **The baseline.** A ~10-file Claude Code config bundle (CLAUDE.md system prompts + permissions JSON + 5 skill files + PDF report script). **NO MCP, NO agent loop, NO real self-correction, NO approval gate.** 15 stars, 4 commits. | **Trivially exceeded** — any submission with a real MCP server clears it. |
| [AppliedIR/Valhuntir](https://github.com/AppliedIR/Valhuntir) (+ `sift-mcp`, `wintools-mcp`, `opensearch-mcp`) | **The bar to meet/exceed.** ~14K LOC Python. 11-package monorepo. **9 MCP backends, 100 tools, 22K-record forensic RAG, 2.6M-record Windows triage baseline, 3,700 Sigma rules auto-applied.** 9 defense layers including HMAC-SHA256 PBKDF2 600K-iter approval ledger, bwrap kernel sandbox, 41 deny rules. By a SANS Principal Instructor + FOR508 co-author. | **Production-shape. Cannot win on coverage.** Must go orthogonal. |

Full read: `02-sponsor-docs.md` + `04-competitor-analysis.md`.

---

## Available primitives (what we build on)

| Primitive | Status | Source |
|---|---|---|
| SANS SIFT Workstation OVA | Live (free download) | sans.org/tools/sift-workstation |
| Protocol SIFT install | Live (one-liner curl) | github.com/teamdfir/protocol-sift |
| MCP Python SDK | Live | github.com/modelcontextprotocol/python-sdk |
| Claude Code / Agent SDK | Live (Python + TS); new Agent SDK credits effective Jun 15 | code.claude.com/docs/en/agent-sdk |
| OpenClaw | Live (config-first multi-agent framework) | openclaw.ai |
| LangGraph (recommended for multi-agent) | Live, v0.4 | github.com/langchain-ai/langgraph |
| Validation datasets (public answer keys) | Live | digitalcorpora.org, cfreds.nist.gov, archive.org |
| Existing forensics MCP servers | `bornpresident/Volatility-MCP-Server` (memory), `socfortress/velociraptor-mcp-server` (live host), `AppliedIR/sift-mcp` (full SIFT) | GitHub |

Code snippets paste-ready: `refs/sdk-snippets.md`.
Full repo clone commands: `refs/sponsor-repos.md`.

---

## Hidden-field verdict

| Sub-lane | Verdict | Why |
|---|---|---|
| Custom MCP tool coverage breadth | 🔴 RED | Valhuntir owns 100 tools |
| Response-envelope rotating reminders + structural gates | 🔴 RED | Valhuntir's pattern |
| HMAC-signed approval ledger | 🔴 RED (copy, don't compete) | Valhuntir's L2 layer |
| **Closed-loop critic→revise self-correction agent** | 🟢 GREEN | Not in Valhuntir. Maps to tiebreaker criterion + Rob T. Lee's #1 quoted complaint. **TOP WEDGE.** |
| **Structural adversarial-evidence defense** | 🟢 GREEN | Not in Valhuntir. Maps to judges Perkal (MCPwn CVE) + Ernstberger (Kontext). |
| **Measured hallucination-reduction harness vs public answer keys** | 🟢 GREEN | NIST Data Leakage has a PUBLIC PDF answer key. Auto-scoring achievable. |
| Memory-first Vol3-plugin-aware investigator | 🟢 GREEN | Demo-friendly because of Rob's Ralph Wiggum Volatility example |
| Live-host triage via Velociraptor MCP + agentic layer | 🟢 GREEN | Valhuntir is post-mortem only |
| Court-admissibility annotation per finding | 🟢-🟡 | Cheap addition, maps to 3+ judges' worldviews |
| Real-time investigation HUD (streaming traces) | 🟢-🟡 | Demo polish |
| Lightweight Docker compose install | 🟢-🟡 | Usability wedge only |

Full analysis: `06-hidden-field.md`.

---

## The composite wedge (synthesized strategy)

**A Custom MCP Server submission ("Protocol-SIFT v2 with closed-loop critic"), built such that:**

1. **Architecture floor matches Valhuntir** on:
   - Typed MCP server with Pydantic I/O
   - Response envelope (`audit_id / caveats / advisories / corroboration / discipline_reminder / data_provenance`)
   - JSONL audit log per call, stable `audit_id`
   - Finding schema (`F-<examiner>-<NNN>`, `observation / interpretation / confidence / confidence_justification / audit_ids / iocs / mitre_ids`)
   - HMAC-signed approval ledger (PBKDF2-SHA256, 600K iters)
   - Provenance tier rejection (NONE → server rejects)

2. **Differentiator on top: closed-loop critic→revise subagent.**
   - Fires every N findings or every M minutes
   - Re-reads evidence + findings + audit_ids
   - Emits `{verdict: AGREE|CHALLENGE|REJECT, reason, suggested_revision, missing_corroboration}` per finding
   - CHALLENGE findings return to investigator with critique
   - REJECT findings auto-archive
   - Logs to `audit/critic.jsonl`

3. **Adversarial-evidence sanitizer layer** in front of all LLM-bound free-text fields (XML strip, role-token strip, unicode normalize, BIDI/homoglyph strip, render with `[UNTRUSTED]` markers).

4. **Measured hallucination harness** scoring against Nitroba + NIST Data Leakage + NIST Hacking Case. Reports `precision / recall / hallucination_rate` per case, vs baseline Protocol SIFT.

5. **Tool coverage:** 15-25 well-chosen tools focused on memory + disk + Windows-artifact triage. **Don't try to match Valhuntir's 100.**

6. **Demo arc** (5 minutes):
   - 0:00-0:30 GTG-1002 framing
   - 0:30-1:00 architecture diagram with security boundaries marked
   - 1:00-3:00 "find evil" live against NIST Hacking Case
   - 3:00-3:30 **Self-correction moment** (Volatility errors → adjust → retry — the Ralph Wiggum Loop)
   - 3:30-4:00 **Critic moment** (critic CHALLENGES a wrong finding; investigator revises)
   - 4:00-4:30 Hallucination metric: "baseline X% → ours Y%"
   - 4:30-5:00 Final report with court-admissibility annotations

Three failure modes to avoid:
- ❌ Rebuilding Valhuntir worse on tool coverage
- ❌ Direct Extension with prompt-only guardrails (auto-loses Constraint)
- ❌ No measured accuracy report

---

## Effort estimate (~13 days remaining)

| Component | Days |
|---|---|
| Custom MCP server (15-25 typed tools) | 4 |
| Closed-loop critic subagent | 3 |
| Adversarial-evidence sanitizer | 1.5 |
| Hallucination harness (3 datasets) | 2.5 |
| Court-admissibility annotation | 0.5 |
| Real-time HUD (optional) | 2 |
| Docker compose install | 0.5 |
| Demo video + write-up + diagram + accuracy report | 2 |
| **Total** | **~13-15 days** |

**Solo is tight.** Team of 2-3 is comfortable. If solo, drop the HUD and the memory-first wedge; keep critic + sanitizer + harness as the core differentiators.

---

## Prior winner pattern (N/A — first edition)

This is the first SANS hackathon for autonomous IR. **No prior winners to reverse-engineer.** The winning-shape proxy is Valhuntir (the published quality bar to meet/exceed). Full analysis: `05-prior-winners.md`.

Pattern: a submission that **(a) matches Valhuntir's architectural floor** and **(b) adds 1-2 orthogonal wedges with measurable evidence** is positioned to score ✓✓✓ on the heavy-weight criteria.

---

## Open questions / unverified

- [ ] **VIGIA ground-truth files** (attributed to Anna Tchijova for Cridex + DFRWS 2008) have NO public footprint. Likely internal SANS or Slack-only. Check the [Protocol SIFT NotebookLM](https://notebooklm.google.com/notebook/f0957a60-6fb2-452b-93d4-ecd73ba47779) and Slack. If unavailable, build our own ground-truth scoring against public answer keys (which is what the harness does anyway — this is a graceful fallback).
- [ ] **Devpost project gallery** is unpublished until after Jun 15 close. We are operating without competitor intel. Re-check after Jun 15.
- [ ] **`teamdfir/protocol-sift` star + activity** is low (15 stars, 4 commits). Confirms novelty bar is low; quality bar is high. **Implication:** whoever produces the architecturally-cleanest reference can become the de facto post-hackathon Protocol SIFT.
- [ ] **Agent SDK pricing** changes effective Jun 15 — new monthly Agent SDK credit pool separate from interactive limits. Relevant for cost planning if running automated harness runs.
- [ ] **Slack discourse signal** — public X/Reddit discussion is thin (most activity inside private SANS Slack). Joining and lurking is the only way to catch competitive signal.

---

## File index

| File | Contents | Load when |
|---|---|---|
| **`CONTEXT.md`** | **This file. Master entrypoint.** | **Always first.** |
| `00-overview.md` | One-page hackathon facts + links | Anytime you need a deliverable checklist or a URL |
| `01-prizes-tracks.md` | Prize / judging criteria deep dive (incl. unwritten rubric) | When making scope tradeoffs |
| `02-sponsor-docs.md` | Architecture references — Protocol SIFT, Valhuntir, SIFT tools, MCP, frameworks, prior MCP servers | When designing the architecture or picking tools |
| `03-project-gallery.md` | Devpost gallery state (unpublished) + known public competitor | When evaluating competition |
| `04-competitor-analysis.md` | Valhuntir deep-read + marez8505 — what to copy, what to beat, ranked wedges | **When deciding the wedge stack** |
| `05-prior-winners.md` | First-edition hackathon — Valhuntir as winning-shape proxy | When questioning the winning shape |
| `06-hidden-field.md` | Lane saturation matrix + composite wedge recommendation | **When picking which lanes to enter** |
| `07-pre-commit-checklist.md` | Go / no-go gates + pre-commit architectural choices + day-1 actions | **Before committing 13 days to this** |
| `refs/sdk-snippets.md` | Paste-ready MCP server / critic / sanitizer / HMAC ledger code | When implementing |
| `refs/sponsor-repos.md` | Clone commands + "what to borrow" per repo | When setting up |
| `refs/participant-repos.md` | Known competitor builds + ongoing-discovery queries | When checking the field |
| `refs/judges.md` | Per-judge profile + predicted preferences + demo-tactical implication | When recording the demo + writing the README |
| `refs/datasets.md` | All 10 validation datasets with hashes / URLs / answer keys / fetch commands + hallucination scoring methodology | **When building the accuracy harness** |
| `refs/quotes-for-pitch.md` | Quote bank for video / write-up / architecture diagram callouts | When writing the deliverables |
| `.raw/01-devpost-judges.md` | Subagent 1 raw research (verbose, source-of-truth) | Backup |
| `.raw/02-sponsor-repos.md` | Subagent 2 raw research | Backup |
| `.raw/03-domain-knowledge.md` | Subagent 3 raw research | Backup |
| `.raw/04-signals-and-data.md` | Subagent 4 raw research | Backup |

---

## The one-paragraph summary for a cold agent

> You are being asked to help build a winning submission to the SANS "Find Evil!" hackathon (deadline 2026-06-15 11:45 PM EDT, ~13 days from today 2026-06-02). The hackathon scores on 6 equally-weighted criteria with **Autonomous Execution Quality as the tiebreaker**. The baseline (`teamdfir/protocol-sift`) is a trivial Claude Code config bundle with no MCP. The bar to meet/exceed is **Valhuntir** by Steve Anson / AppliedIR — a production-shape 100-tool MCP platform with HMAC-signed approvals, bwrap sandbox, and 22K-record forensic RAG. **You cannot win on tool coverage.** The wedge is to **match Valhuntir's architectural floor** AND add a **closed-loop critic→revise subagent** (Wedge 1: tiebreaker criterion), a **measured hallucination-reduction harness** (Wedge 2: IR Accuracy) against public-answer-key datasets (NIST Data Leakage PDF, NIST Hacking Case writeups, Nitroba pcap), and an **adversarial-evidence sanitizer layer** (Wedge 3: maps to judges Perkal + Ernstberger). Use Custom MCP Server architecture in Python with FastMCP; Pydantic-typed I/O; Valhuntir-style response envelope; JSONL audit log per call. Write findings as DRAFTs that require HMAC-SHA256 cryptographic approval (Valhuntir's PBKDF2 600K-iter pattern, code paste-ready in `refs/sdk-snippets.md` §5). Frame all written deliverables in Rob T. Lee's preferred language ("constrained workflow assistant," "augments the senior analyst," "measured hallucination rate") — NEVER vendor-marketing ("autonomous SOC," "replaces L1," "eliminates hallucinations"). Demo video must be ≤5 min with live terminal execution and at least one self-correction sequence — the rules require this and the tiebreaker depends on it.
