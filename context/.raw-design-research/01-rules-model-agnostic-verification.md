# Verification: is model-agnostic MCP server permitted?

**Date pulled:** 2026-06-02
**Question on the table:** Is shipping a Custom MCP Server that supports multiple LLM providers (Claude Code, Claude Desktop, LibreChat, Cherry Studio, custom GPT-5 / Gemini / Ollama clients) permitted, neutral, or penalized under the FIND EVIL! hackathon rules?

---

## Source-by-source verbatim findings

### Source 1: findevil.devpost.com/rules — Official Rules

Pulled in full as raw HTML and text-extracted. Verbatim passages relevant to the question:

**Section 4, "What to Create":**

> "Entrants must submit a working software application ("Project") that extends Protocol SIFT's autonomous incident response capability using an agentic framework as the primary execution engine. **Claude Code and OpenClaw are the preferred frameworks, though comparable agentic architectures are permitted.** Projects may operate on any supported case data type, including disk images, memory captures, log files, network captures, and remote endpoints via MCP."

**Section 4, "Platforms":**

> "Projects must be built on Linux terminal / SIFT Workstation environment. **Projects must run on or integrate with the SANS SIFT Workstation using Claude Code or OpenClaw as the agentic framework.**"

Note: this sentence appears to narrow the "comparable agentic architectures permitted" language. However the public-facing Devpost overview page (Source 2) explicitly opens the aperture again — see below.

**Section 4, mandatory deliverables (relevant subset):**

> "Self-correction — the agent detects and resolves errors or inconsistencies in its own output without human intervention.
> Accuracy validation — all findings are traceable to specific artifacts, files, offsets, or log entries.
> Analytical reasoning — output is presented as a structured investigative narrative, not a raw execution log."

> "Include an Architecture Diagram -- A clear visual showing how components connect -- the agent, SIFT tools, MCP servers, evidence sources, output pipeline."

**Section 6, Judges & Criteria — verbatim, equally weighted:**

> 1. **Autonomous Execution Quality** — Does the agent reason about next steps, handle failures, and self-correct in real time?
> 2. **IR Accuracy** — Are findings correct? Hallucinations caught and flagged? Confirmed findings distinguished from inferences?
> 3. **Breadth and Depth of Analysis** — How much case data can the agent handle? Depth on fewer types beats shallow coverage of many.
> 4. **Constraint Implementation** — Are guardrails architectural or prompt-based? Judges evaluate where security boundaries are enforced and whether they were tested for bypass.
> 5. **Audit Trail Quality** — Can judges trace any finding back to the specific tool execution that produced it?
> 6. **Usability and Documentation** — Can another practitioner deploy and build on this?

**No statement found** in the official Rules section that names a specific LLM provider as required.
**No statement found** that restricts which MCP client the user's submission must work with.
**No statement found** prohibiting LLM-agnostic / multi-provider implementations.

---

### Source 2: findevil.devpost.com (overview / "What to Build") — public hackathon page

This is the page judges and entrants are directed to. Contains the critical permission language. Verbatim:

> "**Four supported architectural approaches: Direct Agent Extension (Claude Code or OpenClaw), Custom MCP Server, Multi-Agent Frameworks (AutoGen, CrewAI, LangGraph), or Alternative Agentic IDEs (Cursor, Cline, Aider).**"

**Approach #2 — Custom MCP Server (verbatim, in full):**

> "**2. Custom MCP Server** --- Build a purpose-built MCP server that exposes structured functions instead of generic shell commands. Instead of giving the AI execute_shell_cmd, expose typed functions like get_amcache(), extract_mft_timeline(), analyze_prefetch(). The agent physically cannot run destructive commands because the server doesn't have those tools. The MCP server handles raw tool output natively and can parse it before returning to the LLM, preventing context window overload from massive text dumps. **(This is the most sound architecture in the evaluation. It's also the most work.)**"

**The decisive caveat (verbatim, exactly as published):**

> "**(If another agentic framework can do the job, we won't disqualify it. But Claude Code, OpenClaw, and the four approaches above are the primary targets. Build for those.)**"

**Section header "Supported Architectural Approaches" preamble (verbatim):**

> "You can build on any of these patterns. **The platform matters less than how your architecture enforces evidence integrity and enables genuine self-correction.**"

**Starter idea #6 — "The Purpose-Built MCP Server" (verbatim):**

> "**6. The Purpose-Built MCP Server** --- Wrap SIFT's 200+ tools as structured, type-safe functions exposed through a custom MCP server. The agent physically cannot run destructive commands because the server doesn't expose them. Success metric: zero evidence spoliation risk, with the same or better analytical output as the baseline Protocol SIFT agent. **(This is the architecture that would make a practitioner comfortable standing behind the results.)**"

**Architecture Diagram requirement (verbatim):**

> "Architecture Diagram --- How components connect: the agent, SIFT tools, MCP servers, data sources, output pipeline. **Your diagram must identify which architectural pattern you're using and document where security boundaries are enforced. Prompt-based guardrails and architectural guardrails must be clearly distinguished.**"

**Accuracy Report requirement on alternative IDEs (verbatim):**

> "If your submission uses an alternative IDE, your accuracy report must document what happens when the model ignores read-only rules."

**No statement found** in the overview restricting MCP client choice for Custom MCP Server submissions.
**No statement found** requiring a specific LLM provider for Custom MCP Server submissions.

---

### Source 3: findevil.devpost.com/resources — Resources page

Pulled in full. Verbatim content (entire body):

> "Protocol SIFT integrates AI agents with the SANS SIFT Workstation -- 200+ incident response tools on a single platform -- through Model Context Protocol (MCP). An analyst types what they need in natural language. The AI selects tools, executes them, reasons about the output, and produces structured reports. The community's mission: sharpen this proof of concept into a production-grade capability."

**Tools and Technologies (verbatim):**
- SANS SIFT Workstation: https://sans.org/tools/sift-workstation — Download ova file and can run in VMs
- Protocol SIFT Package: `$ curl -fsSL https://raw.githubusercontent.com/teamdfir/protocol-sift/main/install.sh | bash`
- Starter case data: https://sansorg.egnyte.com/fl/HhH7crTYT4JK — "Sample disk images and memory captures provided at launch."
- Protocol SIFT NotebookLM notebook: https://notebooklm.google.com/notebook/f0957a60-6fb2-452b-93d4-ecd73ba47779?authuser=1 — "this is the chief location to go to for asking questions on how to build it, what to build, and how. A great resource for getting ideas of if you are just beginning."

**Example Type of Project Submission (verbatim):**

> "Example Submission and level of quality to meet/exceed written by Steve Anson (SANS Author)
> GitHub - AppliedIR/Valhuntir: Valhuntir CLI — AI-augmented incident response platform"

**Inspiration (verbatim):**
- SANS blog: "Protocol SIFT: An Experimental Research Initiative for AI-Assisted DFIR"
- Rob T. Lee's Substack: "Introducing Protocol SIFT: Meeting AI Threat Speed with Defensive AI Orchestration"
- Anthropic GTG-1002 threat intelligence report

**No statement found** about LLM provider choice on the resources page. The NotebookLM is gated; cannot verify its contents directly.

---

### Source 4: SANS blog — "Protocol SIFT: An Experimental Research Initiative for AI-Assisted DFIR"

Pulled. Per WebFetch extraction: the article emphasizes "AI acts strictly as a constrained workflow assistant" and that Protocol SIFT is in "initial research stage." **No statement found** about: specific LLM model selection, provider choice between Claude/OpenAI/Google/etc., the four architectural approaches, MCP server pattern as a specific submission path, Valhuntir, or judging philosophy.

The blog stays at the conceptual framing layer. It does not constrain model choice.

---

### Source 5: SANS press release — "Two Words That Changed Cybersecurity: Find Evil!"

Pulled. Relevant verbatim mentions:

> "Anthropic's security team disclosed a Chinese state-sponsored operation using the exact same architecture for offense: AI agents, MCP, security tools, 80–90% autonomy across 30+ targets."

> "Claude Mythos Preview, an unreleased frontier model, has already found thousands of critical zero-day vulnerabilities across every major operating system and web browser"

> "connecting AI agents to the SIFT Workstation's 200+ forensic tools through MCP"

**No statement found** that prescribes Claude as the required model for entrants. **No statement found** mentioning OpenAI, Google, Meta, or Ollama. **No statement found** about framework requirements for hackathon submissions. The press release is a marketing announcement, not a technical spec.

---

### Source 6: SANS blog — "SANS Launches the First Hackathon for Autonomous Incident Response"

Pulled. **No statement found** about: the four architectural approaches, Custom MCP Server, LLM provider choice, model agnosticism, the "if another agentic framework can do the job" caveat, or Valhuntir. This is a launch announcement that defers technical specifics to the Devpost rules.

---

### Source 7: Rob T. Lee Substack — "Registration is OPEN: Find Evil!"

Pulled. Per WebFetch extraction:

> "Claude Code reasoning through 200+ tools via Model Context Protocol"
> "Claude Code, MCP, and security tools" are mentioned as the architecture Protocol SIFT uses.

**No statement found** mentioning GPT, Gemini, Ollama, or guidance about choosing between LLM providers. **No statement found** describing the four architectural approaches. **No statement found** prohibiting alternative LLMs.

Rob T. Lee discusses Claude because Protocol SIFT (the reference POC) runs on Claude Code. The Substack does not extend a constraint to submissions.

---

### Source 8: GitHub — AppliedIR/Valhuntir (the SANS-cited reference submission)

Pulled. README verbatim passages:

> "Supported clients include **Claude Code, Claude Desktop, Cherry Studio, self-hosted LibreChat, and any client that supports Streamable HTTP transport with Bearer token authentication.**"

> "**Valhuntir is LLM client agnostic** — connect any locally installed MCP-compatible client through the gateway."

> "**Forensic discipline is provided structurally at the gateway and MCP layer, not through client-specific prompt engineering, so the same rigor applies regardless of which AI model or client drives the investigation.**"

> "**Valhuntir reinforces forensic discipline through multiple layers built into the MCP servers, client configuration, and gateway — not through a single system prompt that the LLM can drift from during long sessions.**"

Supported clients table (verbatim from README):

| Client | Platforms | Notes |
|--------|-----------|-------|
| Claude Code | Linux, macOS, Windows | Primary; includes sandbox & audit hooks |
| Claude Desktop | macOS, Windows | Requires mcp-remote bridge (stdio-only) |
| Cherry Studio | Linux, macOS, Windows | Manual JSON import |
| LibreChat | Any (browser) | Manual YAML merge |
| Other | Any | Requires Streamable HTTP + Bearer token |

**This is decisive:** the SANS-cited reference submission ("Example Submission and level of quality to meet/exceed") is itself architected as LLM-client-agnostic. Steve Anson, the SANS Author who wrote it, ships a model-agnostic MCP gateway as the published bar.

---

### Source 9: findevil.devpost.com/discussions and /faq

Both pages return HTTP 404. **No discussion threads or FAQ entries are publicly indexed** at these paths. No organizer answers about model choice were obtainable from public web sources.

---

### Source 10: Protocol SIFT NotebookLM

URL: https://notebooklm.google.com/notebook/f0957a60-6fb2-452b-93d4-ecd73ba47779
**Gated.** Page metadata not publicly accessible without Google auth. No public statement obtainable. The resources page describes it as "the chief location to go to for asking questions on how to build it" — meaning any model-choice clarification from organizers would land there or in the Protocol SIFT Slack (also gated).

---

### Source 11: X / Twitter scan

Only one relevant tweet surfaced (Rob T. Lee announcement). No tweets clarifying or constraining model choice were found. No SANS Institute or organizer thread on this topic is publicly indexed.

---

### Source 12: Cross-check of the four "supported architectural approaches"

Confirmed verbatim from the Devpost overview that Custom MCP Server is explicitly listed as **#2 of 4**:

> "Four supported architectural approaches: Direct Agent Extension (Claude Code or OpenClaw), **Custom MCP Server**, Multi-Agent Frameworks (AutoGen, CrewAI, LangGraph), or Alternative Agentic IDEs (Cursor, Cline, Aider)."

Confirmed verbatim that approach #2 is described as "the most sound architecture in the evaluation."

Confirmed verbatim that the architecture diagram requirement only asks entrants to "identify which architectural pattern you're using and document where security boundaries are enforced" — no client-or-LLM-provider lock-in is required.

---

## Cross-cutting answer

**Yes — shipping a Custom MCP Server that is usable by multiple LLM providers (Claude Code, Claude Desktop, LibreChat, Cherry Studio, custom GPT-5 / Gemini / Ollama Python clients) is explicitly permitted and arguably rewarded by the published rubric.** The Rules section names Claude Code and OpenClaw as "preferred frameworks" but immediately adds "though comparable agentic architectures are permitted." The public-facing overview goes further, listing Custom MCP Server as architectural approach #2 of 4 and labeling it "the most sound architecture in the evaluation." The decisive caveat is verbatim: *"If another agentic framework can do the job, we won't disqualify it."* The architectural pattern matters, the **client** does not — judges are required to evaluate "where security boundaries are enforced," which is a structural question about the MCP server, not about which client connects to it.

**The SANS-cited reference submission validates this directly.** The resources page names AppliedIR/Valhuntir as "the level of quality to meet/exceed," written by SANS Author Steve Anson. Valhuntir's README declares itself "LLM client agnostic" verbatim and ships a supported-clients matrix covering Claude Code, Claude Desktop, Cherry Studio, LibreChat, and "any client that supports Streamable HTTP transport with Bearer token authentication." Crucially, Valhuntir's design philosophy — *"Forensic discipline is provided structurally at the gateway and MCP layer, not through client-specific prompt engineering, so the same rigor applies regardless of which AI model or client drives the investigation"* — maps directly to the rubric criterion "Constraint Implementation: Are guardrails architectural or prompt-based?" Architectural enforcement at the MCP layer is the model-agnostic strategy that the published bar already uses.

**The only constraint on model/framework choice is one indirect platform requirement: "Projects must run on or integrate with the SANS SIFT Workstation using Claude Code or OpenClaw as the agentic framework"** (Section 4 Platforms). This is in tension with the "comparable agentic architectures are permitted" line earlier in the same section and with the overview's "If another agentic framework can do the job, we won't disqualify it." The safe read: judges will demo your submission using either Claude Code or OpenClaw against your MCP server. If your MCP server is genuinely model-agnostic, you can satisfy the platform requirement (judges run Claude Code → your MCP server) **and** demonstrate broader value (works with Cherry Studio, LibreChat, custom Python agent against GPT-5/Gemini/Ollama) for free. The Usability and Documentation criterion ("Can another practitioner deploy and build on this?") explicitly rewards portability.

---

## Constraints we DO have to respect

- Project must run on or integrate with the SANS SIFT Workstation (Linux terminal). [Rules §4 Platforms]
- Project must be demonstrable with **Claude Code or OpenClaw** as a working integration path — judges will use one of these. [Rules §4 Platforms]
- Project must demonstrate **self-correction, accuracy validation, and analytical reasoning**. [Rules §4]
- Project must include: GitHub repo (MIT or Apache 2.0), README, demo video ≤5min with audio narration of live terminal execution showing at least one self-correction sequence, architecture diagram, dataset documentation, accuracy report, try-it-out instructions, agent execution logs. [Rules §4 Submission Requirements + overview "What to Submit"]
- Architecture diagram must **identify the architectural pattern** and **distinguish prompt-based vs architectural guardrails**. [Overview]
- All findings must be **traceable to specific artifacts, files, offsets, or log entries** with full audit trail. [Rules §4 + Judging Criterion 5]
- If you use an Alternative Agentic IDE, accuracy report must document what happens when the model ignores read-only rules. [Overview] — not applicable to Custom MCP Server submissions.
- Open source license (MIT or Apache 2.0) visible at top of repo. [Rules §4]
- Substantially new work created April 15 – June 15, 2026. [Rules §4]

## What we are free to choose

- **Architectural approach: Custom MCP Server is explicitly listed and described as "the most sound architecture in the evaluation."** [Overview §"Supported Architectural Approaches" #2]
- **MCP client(s) the server supports.** No rule constrains this. Valhuntir (the cited bar) supports 5+ clients.
- **LLM provider(s) the MCP server is usable with.** No rule names a required provider. The reference submission is explicitly "LLM client agnostic."
- Programming language for the MCP server (Python, TypeScript, Rust, Go — all valid).
- Transport (stdio, Streamable HTTP with Bearer token — Valhuntir uses both).
- Whether to include multi-agent orchestration on top (would combine approaches #2 and #3).
- Evidence sources you target (disk images, memory captures, log files, network captures, remote endpoints via MCP — all named in rules).
- Auxiliary tooling (Examiner Portal, CLI, OpenSearch indexing, etc. — Valhuntir bundles all three).

## Strategic recommendation (observation, not prescription)

**Model-agnosticism is a strength under this rubric, not neutral and not a weakness.** Three of the six equally weighted criteria reward it directly: (1) *"Constraint Implementation: Are guardrails architectural or prompt-based? Judges evaluate where security boundaries are enforced"* — model-agnostic MCP enforcement is by definition architectural, not prompt-based; the bar literally cannot be met better than by structural gateway controls. (2) *"Audit Trail Quality: Can judges trace any finding back to the specific tool execution that produced it?"* — an MCP server's typed tool calls produce machine-readable execution logs regardless of which LLM called them. (3) *"Usability and Documentation: Can another practitioner deploy and build on this?"* — multi-client support directly answers yes; a Claude-only submission directly limits this. The fourth criterion, *"Autonomous Execution Quality,"* is the tiebreaker and is orthogonal to model choice. The only risk is over-investing in client breadth at the expense of depth — but since Valhuntir (the cited bar) already ships 5+ clients, supporting at least 2-3 is the floor, not the ceiling. Building Custom MCP Server with multi-client support follows the published bar exactly and aligns with the rubric's strongest signals.

---

## Cited sources

- https://findevil.devpost.com/rules (pulled in full, verbatim quoted)
- https://findevil.devpost.com/ (pulled in full, verbatim quoted — contains the "If another agentic framework can do the job" caveat)
- https://findevil.devpost.com/resources (pulled in full, verbatim quoted)
- https://www.sans.org/blog/protocol-sift-experimental-research-initiative-ai-assisted-dfir/ (no statement found on model choice)
- https://www.sans.org/press/announcements/two-words-changed-cybersecurity-find-evil-builders-answer-call-defend-infrastructure (no statement found constraining models)
- https://www.sans.org/blog/sans-launches-first-hackathon-autonomous-incident-response/ (no statement found constraining models)
- https://robtlee73.substack.com/p/registration-is-open-find-evil-hackathon (Claude mentioned descriptively re Protocol SIFT POC, no constraint on submissions)
- https://github.com/AppliedIR/Valhuntir (README verbatim: "LLM client agnostic")
- https://findevil.devpost.com/discussions (404)
- https://findevil.devpost.com/faq (404)
- https://notebooklm.google.com/notebook/f0957a60-6fb2-452b-93d4-ecd73ba47779 (gated, not retrievable)
- X / Twitter scan: no relevant constraints found
