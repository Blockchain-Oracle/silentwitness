# Devpost & Judges Research -- Find Evil! Hackathon (Protocol SIFT 2026)

_Research date: 2026-06-02. Sponsor: SANS Institute. Devpost: findevil.devpost.com._

---

## 1. Devpost listing verification

The Devpost listing matches the rules we already ingested. New/confirmed details:

- **Tagline:** "AI threats strike in minutes. Build the defender that responds in seconds."
- **Registered participants:** 3,861 (as of 2026-06-02).
- **Total prize pool stated as $22,000+** (matches $10K/$7.5K/$4.5K cash + Summit pass + OnDemand + broadcast slot).
- **Submission requirements (8 mandatory items), confirmed verbatim from Devpost:**
  1. Public GitHub repository (open-source MIT or Apache 2.0)
  2. Demo video (max 5 minutes) with **live terminal execution**
  3. Architecture diagram showing **security boundaries and enforcement mechanisms**
  4. Devpost-format written description
  5. **Dataset documentation** with test sources
  6. **Accuracy report addressing false positives and evidence integrity**
  7. Deployment/setup instructions for judges
  8. **Structured agent execution logs with timestamps**
- **Supported architectural approaches** (explicitly listed):
  - Direct Agent Extension (Claude Code or OpenClaw enhancements)
  - Custom MCP Server
  - Multi-Agent Frameworks (AutoGen, CrewAI, LangGraph)
  - Alternative Agentic IDEs (Cursor, Cline, Aider)
- **Onboarding flow:**
  - Slack: `https://join.slack.com/t/sansaihackathon/shared_invite/zt-3zhbphvt0-3mMkKpBeUvll1DYwnr1yOA`
  - Discord: `https://discord.com/invite/HP4BhW3hnp`
  - SIFT Workstation: `sans.org/tools/sift-workstation`
  - Install: `curl -fsSL https://raw.githubusercontent.com/teamdfir/protocol-sift/main/install.sh | bash`
  - Help: `aihackathon@sans.org`
- **Starter case data (private Egnyte share):** `https://sansorg.egnyte.com/fl/HhH7crTYT4JK`
- **Protocol SIFT NotebookLM (judges' likely shared mental model):** `https://notebooklm.google.com/notebook/f0957a60-6fb2-452b-93d4-ecd73ba47779?authuser=1`
- **Anthropic GTG-1002 report** is cited as inspirational context -- the Nov 2025 state-sponsored AI-assisted campaign showing "80-90% of tactical operations executed autonomously without human intervention."

Judging timeline confirmed: submissions close **Jun 15 2026 11:45 PM EDT**, scoring **Jun 19 -- Jul 3**, winners on/around **Jul 8 2026**.

---

## 2. Submission gallery state (as of 2026-06-02)

**Gallery is unpublished.** Both `/project-gallery` and `/submissions` return:
> "The hackathon managers haven't published this gallery yet, but hang tight!"

This is normal -- Devpost galleries typically open after submissions close. **Implication:** no public incumbent check is possible right now. We are operating blind on competitor field until at minimum after Jun 15 close, more likely after winner announcement Jul 8. The only public exemplar we have is **Valhuntir** (the example submission). All competitive intel must come from Slack/Discord chatter.

---

## 3. Key judges -- what they value

### Rob T. Lee (THE primary judge -- CAIO + Chief of Research, SANS)

Source: his Substack `robtlee73.substack.com`, the SANS Protocol SIFT blog, [un]prompted talk preview, and the registration-open post. These are the closest thing to a published rubric we will get.

**Core thesis (verbatim):**

> "Adversaries are operating at machine speed. The answer is not faster humans."

> "Defenders are out here bringing knives to a drone strike."

> "Defensive OODA loops are measured in hours while offensive loops are now measured in seconds."

**What a winning agent does (verbatim from the registration-open post):**

> "Teach an AI agent to think like a senior analyst, how to sequence its approach, recognize when something doesn't add up, and self-correct when it gets it wrong."

This sentence is the rubric in compressed form. Decompose it:
1. **Sequence its approach** = explicit, principled workflow (not one giant prompt).
2. **Recognize when something doesn't add up** = anomaly self-detection, hallucination guards.
3. **Self-correct when it gets it wrong** = the "Ralph Wiggum Loop" (below).

**The Ralph Wiggum Loop (verbatim from Substack intro):**

> "When a Volatility command returns an error, Claude reads the error message, adjusts its hypothesis... and retries."

> "A tool that's fast but fails silently is worse than useless. In forensics you need to know what you couldn't find as much as what you did find."

**Architectural constraint Rob explicitly endorses (verbatim from intro):**

> "Inference Constraint layer where the AI directs the workflow."

The framing is: AI is **high-constraint when verifying** (runs `strings`, `binwalk`, Volatility, parses verified output), and is **explicitly prohibited from low-constraint analysis** like "summarizing hex directly" -- because that path produces hallucinated evidence.

**Honest admission Rob made about Protocol SIFT itself (verbatim):**

> "Protocol SIFT works. It also hallucinates more than we'd like. (That's exactly why this hackathon exists.)"

**Translation:** Submissions that demonstrably reduce hallucination rate (with measured before/after) will score disproportionately well on **IR Accuracy** and **Constraint Implementation** criteria.

**The [un]prompted demo benchmark (verbatim):**

> "Fourteen minutes twenty-seven seconds" -- typing the words "find evil" produced complete C-drive analysis. Rob verified accuracy via "self-inflicted intrusion testing."

This is the **time-to-finding bar**. Submissions noticeably slower than ~15min on a full disk will look weak. Submissions noticeably faster with comparable depth will look elite.

**On who can win (verbatim):**

> "You don't need to be an incident response expert."

Important signal: technical quality and engineering rigor matter more than 20 years of DFIR background. The agent must *embody* the senior analyst -- the builder doesn't have to *be* one. Levels the playing field for non-DFIR engineers who can ship constraint architecture.

**Other recent posts of interest (May 5 2026):** "AI Isn't a Tool Anymore. It's an Operator." Rob is publicly framing AI as an actor with agency -- which is why the rubric weights **Autonomous Execution Quality** as the tiebreaker.

### Ovie Carroll (DOJ Cybercrime Lab Director, FOR500 co-author)

- 31 years law enforcement + cyber investigation. Currently directs the DOJ's Computer Crime and Intellectual Property Section (CCIPS) Cybercrime Lab.
- Co-author of **SANS FOR500: Windows Forensic Analysis**. Adjunct at GWU.
- Public statements emphasize **evidence-as-narrative**:

  > "Digital devices are silent witnesses. The Digital Investigative Analyst acts as their voice, meticulously translating the data into an objective narrative."

  > "Through meticulous examination, they extract the unvarnished story from electrons, a chronicle free from bias or embellishment."

- **What he will reward:** clean audit trails, defensible chain-of-custody, evidence integrity that could survive courtroom scrutiny (even though Protocol SIFT itself isn't legally admissible -- he'll evaluate as if it had to be).
- **What he will penalize:** AI making interpretive claims without traceable artifact provenance; any sign of "AI hallucinated this finding" without flagging.

### Adam Nasreldin (Senior IR Consultant, Google Mandiant)

- 20 years Cyber/Network Security. Long Cisco background (Systems Engineer → Consulting Security CX Engineer EMEA) before Mandiant.
- Mandiant's house style: **Defender's Advantage podcast**, threat-intel-driven IR, "from compromise assessment to red-team-informed defense."
- No specific public blog posts surfaced for him directly, but Mandiant in 2026 has been publishing extensively on **AI-assisted IR consulting** -- their public blog post "How Mandiant Consultants and Analysts are Leveraging AI Today" is the lens through which he'll evaluate.
- **What he will reward:** agents that look like a Mandiant playbook -- threat intel applied to artifacts, structured triage, hypothesis-driven investigation rather than blind tool-running.

### Cheri Carr (Owner/Principal, Aspen Forensics; Texas-licensed PI)

- Pioneer DFIR practitioner. **Founding member of the Air Force and DoD Computer Forensics Laboratories** -- the first of their kind. Built processes still in use today.
- Air Force OSI + NASA OIG background before private sector.
- **Managing Director and DFIR Practice Leader at Stroz Friedberg (2018-2022)** -- so she's seen both elite enterprise IR and now runs her own boutique.
- Testified as expert witness "dozens of times" in federal/state courts.
- **What she will reward:** "bulletproof chain of custody," reproducible findings, clear communication of results to non-technical audiences (read: the demo video and write-up matter).
- **What she will penalize:** sloppy evidence handling, ambiguous findings, agents that conflate inference with fact.

### Steve Cobb (CISO, SecurityScorecard)

- 25+ years across Verizon Managed Security, Microsoft (Senior Escalation Engineer), now SecurityScorecard CISO since 2023.
- Frequent speaker: InfoSecCon, Cyber Defense Summit, multiple CISO boards.
- Public detection/response philosophy:
  - **"From Prevention to Resilience":** assume breach, prioritize response and minimize impact.
  - **Core IR principles: isolate, contain, neutralize.** "Success in response depends on the speed, coordination, and preparation of the team."
  - **Supply chain security** is a major theme (vendor risk, third-party visibility).
- **What he will reward:** agents that show speed-to-containment thinking, not just speed-to-detection. Agents that triage and prioritize "what do we do now" instead of just "what happened."

### Additional judges worth flagging

- **Jens Ernstberger (Kontext Security):** Founder of Kontext, runtime authorization for AI agents (scoped creds, short-lived tokens, audit trails). USENIX Security 2024 SNARK research. He **will scrutinize the security architecture of the agent itself** -- prompt injection resistance, credential handling, tool-use authorization. Constraint Implementation criterion is his domain.
- **Yotam Perkal (Pluto Security):** Head of security research at Pluto. Discovered CVE-2026-33032 ("MCPwn") -- MCP endpoints inheriting application capabilities without security controls. Published "Inside Claude Cowork: How Anthropic's Autonomous Agent Actually Works." **He will read the MCP server design for security flaws.** If you ship a custom MCP, expect it to be reverse-engineered.

---

## 4. Steve Anson + Valhuntir signal (THE example submission)

Steve Anson is a **SANS Principal Instructor**, **co-author of FOR508**, and former Defense Criminal Investigative Service + FBI task force agent (computer crime). 25+ years DFIR. Co-founder of Informed Defense (consulting). Trained national cyber units in 60+ countries. Co-author of *Mastering Windows Network Forensics and Investigation*.

He architected **Valhuntir** -- the example submission the hackathon brief explicitly cites as the quality bar to "meet or exceed." This is the most concrete signal we have about what judges will recognize as "right."

### Valhuntir's architecture (`github.com/AppliedIR/Valhuntir`)

**Tagline:** "Turn a single incident response analyst into the manager of an agentic AI incident response team."

**Stack:**
- Python (91%), Shell, PowerShell. MIT licensed.
- `sift-gateway` HTTP endpoint on port 4508 aggregating **8 MCP backends**.
- **23 forensic MCP tools** (findings, timeline, evidence, audit).
- **15 case-management MCP tools.**
- **6 report-generation MCP tools** with MITRE ATT&CK mappings.
- **17 OpenSearch MCP tools** for evidence indexing/querying (optional).
- `forensic-rag` with **semantic search across 22K authoritative records**.
- `windows-triage-mcp` with **2.6M known-good baseline records** for offline validation.
- Examiner Portal: browser-based review UI.
- **15 parsers**: Windows Event Logs, MFT, Registry, Shimcache, Amcache, Volatility memory dumps, JSON/JSONL, etc.
- **Hayabusa auto-runs 3,700+ Sigma rules** after EVTX ingestion.

### Design philosophy (verbatim from Valhuntir README, via Steve Anson)

> "Ultimately the human examiner drives the response."

> "Approved findings are HMAC-signed with a PBKDF2-derived key."

Every AI-discovered finding is staged as **DRAFT**. Only humans can promote DRAFT → APPROVED via:
- Password-gated commitment
- HMAC signature with examiner identity + timestamp + content hash
- The AI cannot supply the password

**This is the operational implementation of "Inference Constraint" that Rob T. Lee describes architecturally.** The AI runs deterministic forensic tools, returns structured findings; the human cryptographically approves. The AI **cannot approve its own work**.

### Other Valhuntir signals worth copying

- **LLM-agnostic via MCP gateway** -- works with Claude Code, Claude Desktop, Cherry Studio, LibreChat. The forensic discipline is enforced at the architecture layer, not at the model layer.
- **"Forensic Discipline as Structure"** -- not via prompting. Enforced at MCP response enrichment, sandbox rules, deny-lists, audit hooks.
- **Deterministic document IDs** prevent duplicate ingestion (important for evidence integrity).
- **Isolated network assumption:** no inbound internet, designed for forensic networks.
- **System size:** SIFT alone = 16GB RAM / 50GB disk. With OpenSearch = 32GB / 100GB. Lite mode = 8GB.

### Implication for our submission

The example bar is **systems-engineering heavy, forensic-discipline heavy, MCP-architecture heavy**. Judges expect:
- Multi-tool MCP orchestration, not a single LLM doing everything
- Cryptographic approval flows (or equivalent provenance guarantees)
- Knowledge bases / RAG over authoritative forensic references
- Known-good baselines for false-positive suppression
- A browser-based or structured review UI for the human-in-the-loop step

To "exceed" Valhuntir we'd need to either (a) ship a meaningfully different architecture wedge (autonomy bias toward speed-to-finding, with provable hallucination reduction), or (b) push some axis Valhuntir is weak on (e.g., adversarial robustness, prompt injection defense, novel evidence types, real-time streaming triage).

---

## 5. SANS DFIR course landscape -- the "senior analyst" the agent must mimic

The judges will subconsciously evaluate against the SANS DFIR curriculum because most of them taught it or learned from it.

| Course | Focus | Why it matters for the agent |
| --- | --- | --- |
| **FOR508** -- Advanced IR, Threat Hunting, Digital Forensics | APT tradecraft, lateral movement, credential theft, memory forensics, timeline analysis, anti-forensics, enterprise APT capstone | **This is the "senior analyst" textbook.** Co-authored by Steve Anson. The agent must execute the FOR508 mental model: hypothesis-driven, threat-intel-grounded, multi-artifact correlation, root-cause analysis. **Section 4 explicitly teaches "agentic AI for accelerating investigations"** -- judges have read this section. |
| **FOR500** -- Windows Forensic Analysis | Application execution, file access, USB/external device usage, cloud artifacts, anti-forensics, file download forensics | Co-authored by Ovie Carroll. **The agent's parsers must cover the FOR500 artifact catalog** -- ShellBags, Jump Lists, Prefetch, LNK, SRUM, Amcache, Shimcache, USB history, browser artifacts. Missing these will read as "this builder didn't take FOR500." |
| FOR572 | Network forensics | Less central but bonus points if the agent handles PCAP/Zeek/Suricata output cleanly. |
| FOR526 | Memory forensics in depth | Volatility 3 workflow knowledge. Rob T. Lee's Ralph Wiggum Loop example uses Volatility errors specifically -- this is the canonical demo. |
| FOR578 | Cyber Threat Intelligence | Maps to Mandiant judge perspective. Agent should ground findings in MITRE ATT&CK + known threat actor TTPs, not freelance the interpretation. |

**"SANS way" of IR (the implicit rubric):**
1. **Hypothesis-driven investigation** -- start with a question, work the artifacts to answer it.
2. **Multi-artifact corroboration** -- never trust a single source; cross-reference Registry + EVTX + filesystem + memory.
3. **Timeline-as-spine** -- super-timeline is the unit of investigation.
4. **Known-good baseline subtraction** -- what's NOT normal here, not what's noisy.
5. **Threat-intel framing** -- if the findings fit a known threat actor playbook, name it.
6. **Defensible findings** -- every claim traces to a specific artifact at a specific timestamp.

An agent that visibly executes this loop will resonate with every SANS-trained judge in the panel.

---

## 6. Strategic takeaways

1. **The rubric is one sentence:** "Think like a senior analyst, sequence the approach, recognize anomalies, self-correct." Optimize the entire build around demonstrating this loop. The Ralph Wiggum Loop (tool returns error → AI reads error → adjusts hypothesis → retries) is the single most quotable feature; design a demo moment that shows it explicitly.

2. **Time-to-finding bar is ~15 min on a full C-drive.** Rob T. Lee's [un]prompted demo set this anchor. Submissions noticeably slower will look weak; meaningfully faster with comparable depth will look elite. Build a benchmark harness early and report numbers.

3. **Hallucination reduction is the unspoken #1 differentiator.** Rob explicitly admitted Protocol SIFT "hallucinates more than we'd like -- that's exactly why this hackathon exists." Any submission that ships a **measured before/after hallucination rate** with a defensible methodology will win the IR Accuracy and Constraint Implementation criteria simultaneously. Don't just constrain -- *measure and report* the constraint.

4. **Valhuntir is the architectural floor, not the ceiling.** The judges expect: multi-tool MCP orchestration, cryptographic or equivalent human-approval flow, RAG over forensic knowledge, known-good baselines, structured logs. Anything materially below this looks like a toy. To exceed, pick one axis (speed, prompt-injection robustness, novel artifact coverage, streaming triage, or measurable hallucination reduction) and dominate it.

5. **Demo video and write-up matter more than usual.** Cheri Carr, Ovie Carroll, Steve Cobb -- multiple judges come from a "communicate findings to non-technical audiences" school. Live terminal execution is mandatory. Write the accuracy report like a real Mandiant IR engagement report, not a hackathon README.

6. **Security of the agent itself will be audited.** Jens Ernstberger (Kontext) and Yotam Perkal (Pluto, the MCPwn researcher) are on the panel. They will look at the MCP server design for prompt injection, credential leakage, tool-call chaining attacks. Bake in scoped credentials, short-lived tokens, deny-lists, and a clean audit trail -- and *say so explicitly in the architecture diagram.*

---

## Sources

- [FIND EVIL! Devpost](https://findevil.devpost.com/)
- [FIND EVIL! Resources](https://findevil.devpost.com/resources)
- [SANS blog: Protocol SIFT -- An Experimental Research Initiative for AI-Assisted DFIR](https://www.sans.org/blog/protocol-sift-experimental-research-initiative-ai-assisted-dfir)
- [Rob T. Lee Substack: Introducing Protocol SIFT](https://robtlee73.substack.com/p/introducing-protocol-sift-meeting)
- [Rob T. Lee Substack: Registration is OPEN -- Find Evil! Hackathon](https://robtlee73.substack.com/p/registration-is-open-find-evil-hackathon)
- [Rob T. Lee Substack: [un]prompted talk -- SIFT - Find Evil! The Era of Autonomous Forensics](https://robtlee73.substack.com/p/dangerous-new-attack-techniques-rsac-2026-preview-protocol-sift)
- [Rob T. Lee on X (post on Protocol SIFT)](https://x.com/robtlee/status/2014117375960920074)
- [Valhuntir GitHub (AppliedIR/Valhuntir)](https://github.com/AppliedIR/Valhuntir)
- [Steve Anson SANS profile](https://www.sans.org/profiles/steve-anson)
- [SANS FOR508 course](https://www.sans.org/cyber-security-courses/advanced-incident-response-threat-hunting-training)
- [SANS FOR500 course](https://www.sans.org/cyber-security-courses/windows-forensic-analysis)
- [Ovie Carroll SANS profile](https://www.sans.org/profiles/ovie-carroll)
- [Ovie Carroll personal site](https://ovie.coffee/about-me/f/challenges-in-modern-digital-investigative-analysis)
- [Cheri Carr -- Aspen Forensics](https://aspenforensics.com/)
- [Steve Cobb -- SecurityScorecard leadership](https://securityscorecard.com/people/leadership/steve-cobb/)
- [Jens Ernstberger -- Kontext Security](https://kontext.security/)
- [Jens Ernstberger -- Contextual Authorization for AI Agents](https://ernstberger.xyz/posts/04_contextualauth/)
- [Yotam Perkal SANS profile](https://www.sans.org/profiles/yotam-perkal)
- [Pluto Security blog -- MCPwn (CVE-2026-33032)](https://pluto.security/blog/mcp-bug-nginx-security-vulnerability-cvss-9-8/)
- [Pluto Security blog -- Inside Claude Cowork](https://pluto.security/blog/inside-claude-cowork-how-anthropics-autonomous-agent-actually-works/)
- [Mandiant Cybersecurity Consulting](https://www.mandiant.com/)
