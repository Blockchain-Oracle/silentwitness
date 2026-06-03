# 00 — Overview

## Hackathon at a glance

| Field | Value |
|---|---|
| Name | **FIND EVIL!** — Protocol SIFT hackathon |
| Sponsor | SANS Institute (495 Lowell St, Lexington MA 02420) |
| Sponsor handle | [@SANSInstitute](https://x.com/SANSInstitute) |
| Platform | Devpost |
| Listing | https://findevil.devpost.com/ |
| Tagline | "AI threats strike in minutes. Build the defender that responds in seconds." |
| Total prize pool | $22,000+ cash + SANS Summit passes + SANS OnDemand courses + webcast slot |
| Team size | 1–5 (solo permitted) |
| Eligibility | 18+, no Brazil/Quebec/Russia/Iran/NK/Cuba/Crimea, no SANS/Devpost employees |
| **Submission opens** | Apr 15 2026 12:00 PM EDT |
| **Submission closes** | **Jun 15 2026 11:45 PM EDT** |
| Judging period | Jun 19 – Jul 3 2026 |
| Winners announced | On or around Jul 8 2026 |
| Today's date | 2026-06-02 |
| **Days remaining to submit** | **~13 days** |
| Registered participants | 3,861 (verified 2026-06-02) |
| Judge count | 48 |

## Mission (one paragraph, verbatim from sponsor framing)

> "An AI-powered adversary can go from initial access to full domain control in under 8 minutes. CrowdStrike's fastest observed breakout time: 7 minutes. Horizon3's autonomous agent: 60 seconds to full privilege escalation. MIT's 2024 research: AI-driven attack workflows running 47 times faster than human operators. Meanwhile, a human incident responder is still pulling up their toolkit. That gap is the most dangerous problem in cybersecurity. Find Evil! challenges you to close it."

The hackathon emerged in response to **Anthropic's Nov 2025 disclosure of GTG-1002** — a Chinese state operation where Claude Code autonomously executed 80–90% of an espionage campaign across ~30 targets, "thousands of requests, often multiple per second." Rob T. Lee (SANS CAIO, judge): "The architecture they used, an agentic AI connected to offensive tools via MCP, is the exact same architecture I'd been building for defense."

## What we are building

A working AI agent (single or multi) on or extending the **SANS SIFT Workstation** that demonstrates:

1. **Self-correction** — detects and resolves its own errors without humans.
2. **Accuracy validation** — every finding traces to a specific artifact, offset, or log entry.
3. **Analytical reasoning** — output is a structured investigative narrative, not a raw execution log.

Allowed architectural patterns (verbatim from rules):
- **Direct Agent Extension** (Claude Code / OpenClaw + prompts + skills)
- **Custom MCP Server** ← rules call this "the most sound architecture"
- **Multi-Agent Frameworks** (AutoGen, CrewAI, LangGraph)
- **Alternative Agentic IDEs** (Cursor, Cline, Aider) ← explicitly noted as weaker for evidence integrity

Linux/SIFT environment is mandatory. Open-source license is mandatory (MIT or Apache 2.0).

## Key links — pin these to the wall

### Sponsor
- Devpost listing: https://findevil.devpost.com/
- Devpost rules: https://findevil.devpost.com/rules
- Devpost resources: https://findevil.devpost.com/resources
- SANS launch blog: https://www.sans.org/blog/sans-launches-first-hackathon-autonomous-incident-response
- SANS press release: https://www.sans.org/press/announcements/two-words-changed-cybersecurity-find-evil-builders-answer-call-defend-infrastructure
- Protocol SIFT SANS blog: https://www.sans.org/blog/protocol-sift-experimental-research-initiative-ai-assisted-dfir
- Protocol SIFT NotebookLM (judges' shared mental model): https://notebooklm.google.com/notebook/f0957a60-6fb2-452b-93d4-ecd73ba47779
- Slack: https://join.slack.com/t/sansaihackathon/shared_invite/zt-3zhbphvt0-3mMkKpBeUvll1DYwnr1yOA
- Discord: https://discord.com/invite/HP4BhW3hnp
- Help: aihackathon@sans.org

### Rob T. Lee (THE primary judge)
- Substack root: https://robtlee73.substack.com/
- "Introducing Protocol SIFT": https://robtlee73.substack.com/p/introducing-protocol-sift-meeting
- "Registration is OPEN": https://robtlee73.substack.com/p/registration-is-open-find-evil-hackathon
- "[un]prompted talk" (Find Evil 14:27 demo): https://robtlee73.substack.com/p/dangerous-new-attack-techniques-rsac-2026-preview-protocol-sift
- "Why 47?" math post: https://robtlee73.substack.com/p/why-47-the-math-behind-ai-attacks
- "AI Isn't a Tool Anymore. It's an Operator.": https://robtlee73.substack.com/p/ai-isnt-a-tool-anymore-its-an-operator
- X: https://x.com/robtlee
- [un]prompted YouTube talk: https://www.youtube.com/watch?v=OsUg3TlAqjQ

### Anthropic context
- GTG-1002 disclosure: https://www.anthropic.com/news/disrupting-AI-espionage
- Full PDF: https://assets.anthropic.com/m/ec212e6566a0d47/original/Disrupting-the-first-reported-AI-orchestrated-cyber-espionage-campaign.pdf
- Agent SDK docs: https://code.claude.com/docs/en/agent-sdk/overview

### Code repos
- Protocol SIFT (the baseline): https://github.com/teamdfir/protocol-sift
- SIFT Workstation: https://github.com/sans-dfir/sift (actual install: https://github.com/teamdfir/sift-saltstack)
- **Valhuntir (the bar to beat)**: https://github.com/AppliedIR/Valhuntir
- Valhuntir's MCP monorepo: https://github.com/AppliedIR/sift-mcp
- Valhuntir's Windows MCP: https://github.com/AppliedIR/wintools-mcp
- Valhuntir's OpenSearch MCP: https://github.com/AppliedIR/opensearch-mcp
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- MCP spec: https://modelcontextprotocol.io/
- One public competitor build: https://github.com/marez8505/find-evil

### Validation datasets (full deep-dive in `refs/datasets.md`)
- Nitroba (network, Tier-1): https://downloads.digitalcorpora.org/corpora/scenarios/2008-nitroba/nitroba.pcap
- NIST Data Leakage (Tier-1, public answer key): https://cfreds-archive.nist.gov/data_leakage_case/data-leakage-case.html
- NIST Hacking Case "Mr. Evil" (Tier-1): https://cfreds-archive.nist.gov/Hacking_Case.html
- Starter cases (private Egnyte from sponsor): https://sansorg.egnyte.com/fl/HhH7crTYT4JK

### Required deliverables (8 mandatory — missing ANY = elimination)

1. Public GitHub repository (MIT or Apache 2.0)
2. **Demo video ≤ 5 min** — live terminal execution with audio narration, must include at least one self-correction sequence
3. Architecture diagram (security boundaries marked architectural vs prompt-based)
4. Devpost-format written description
5. Dataset documentation
6. Accuracy report (false positives, missed artifacts, hallucinated claims — honesty > perfection)
7. Live deployment URL or step-by-step local setup instructions
8. Structured agent execution logs with timestamps + token usage (multi-agent: per-message logs; single-agent: per-tool logs; persistent loops: per-iteration traces). Judges must be able to trace any finding to the tool execution that produced it.

## File index for this research folder

| File | What it gives you |
|---|---|
| `CONTEXT.md` | Master entrypoint. Load this first. |
| `00-overview.md` | This file. Facts + links. |
| `01-prizes-tracks.md` | Prize / judging criteria deep dive |
| `02-sponsor-docs.md` | Architecture references (Protocol SIFT, Valhuntir, SIFT tools, MCP, frameworks) |
| `03-project-gallery.md` | Devpost gallery state + one known public competitor |
| `04-competitor-analysis.md` | Valhuntir + marez8505/find-evil — what to copy, what to beat |
| `05-prior-winners.md` | First-edition hackathon — reframed as "Valhuntir is the bar" |
| `06-hidden-field.md` | Lane saturation analysis — which wedges are open |
| `07-pre-commit-checklist.md` | Pre-commit checklist answers |
| `refs/sdk-snippets.md` | MCP Python SDK code snippets (paste-ready) |
| `refs/sponsor-repos.md` | All repos with clone commands |
| `refs/participant-repos.md` | Known competitor repos |
| `refs/judges.md` | Per-judge profile + predicted preferences |
| `refs/datasets.md` | Full validation dataset reference with hashes + answer keys |
| `refs/quotes-for-pitch.md` | Quote bank for video + write-up |
| `.raw/` | The 4 original subagent research dumps (verbose source-of-truth) |
