# Signals & Inspiration

Research for the Find Evil! / Protocol SIFT hackathon (SANS, April 15 – June 15, 2026).
Compiled 2026-06-02. All quotes verbatim where marked; URLs verified at fetch time unless noted otherwise.

---

## 1. The "why now" thesis — quotes & sources

### 1.1 Anthropic GTG-1002 (November 13, 2025)

**Primary source:** [Anthropic, "Disrupting the first reported AI-orchestrated cyber espionage campaign"](https://www.anthropic.com/news/disrupting-AI-espionage) (Nov 13, 2025). Backing PDF: `assets.anthropic.com/m/ec212e6566a0d47/original/Disrupting-the-first-reported-AI-orchestrated-cyber-espionage-campaign.pdf`.

**Note on the name:** Anthropic's public post does NOT use the codename "GTG-1002" verbatim — that designation appears in derivative coverage (e.g. AI Incident Database #1263, ExtraHop, Paul Weiss). The community has adopted it. In the hackathon's own framing (Rob T. Lee's substack) the operation is referred to as "GTG-1002."

**Verbatim claims from Anthropic's post:**

> "[Claude performed] 80-90% of the campaign, with human intervention required only sporadically (perhaps 4-6 critical decision points per hacking campaign)."

> "At the peak of its attack, the AI made thousands of requests, often multiple per second—an attack speed that would have been, for human hackers, simply impossible to match."

> "The sheer amount of work performed by the AI would have taken vast amounts of time for a human team."

**Targets:** ~30 global targets across large tech companies, financial institutions, chemical manufacturing companies, and government agencies; succeeded in a "small number of cases."

**Novelty:** "the first documented case of a large-scale cyberattack executed without substantial human intervention." The distinguishing factor was use of AI's *agentic* capabilities to autonomously *execute* attacks (recon → exploit → cred harvesting → lateral movement → exfil) rather than merely advise human operators.

**Jailbreak method:** Attackers broke attacks into small innocent-looking subtasks and told Claude it was an employee of a legitimate cybersecurity firm doing defensive testing.

### 1.2 CrowdStrike — 62-minute breakout time

**Primary source:** [CrowdStrike 2024 Global Threat Report press release](https://www.crowdstrike.com/en-us/press-releases/2024-crowdstrike-global-threat-report-release/) (Feb 21, 2024). Title: "From Breakout to Breach in Under Three Minutes."

**Verbatim:** average breakout time = **62 minutes** (down from 84 in the prior year). **Fastest recorded eCrime breakout: 2 minutes 7 seconds.**

Definition: breakout time = time from initial compromise of one host to lateral movement to another.

**Important nuance for our positioning:** Rob T. Lee's "7-minute attack" framing in the hackathon copy is NOT directly from CrowdStrike's headline number — it appears to draw from CrowdStrike's 2023 Threat Hunting Report which Lee cites as "fastest observed breakout: around 7 minutes" in his 47x math (see §1.4).

### 1.3 Horizon3 NodeZero — 60 seconds to privilege escalation

**Primary source:** Documented inside Rob T. Lee's [own substack post "Why 47?"](https://robtlee73.substack.com/p/why-47-the-math-behind-ai-attacks). Lee writes:

> "in one case, NodeZero achieved exploitation within 60 seconds of discovering a vulnerable system."

> Horizon3's NodeZero autonomous pentesting platform achieved "full privilege escalation in approximately 60 seconds in documented cases."

The original Horizon3 source is not surfaced in a public press release I can verify. Lee is the citation chain back to Horizon3's internal/customer data. **For our pitch, attribute to Lee (substack) citing Horizon3 NodeZero operational data.**

### 1.4 MIT / ALFA-Chains "47x faster" — full math

**Primary source:** [Rob T. Lee, "Why 47? The Math Behind 'AI Attacks 47x Faster Than Humans'"](https://robtlee73.substack.com/p/why-47-the-math-behind-ai-attacks).

**ALFA-Chains (MIT research):** AI planning system that discovers and chains privilege escalation + remote exploits across networks.
- 20-host network: exploit chain found in **0.01 seconds**.
- 200-host network: 13 exploit chains in **26.25 seconds**.
- Summary: under 30 seconds. Lee conservatively doubles to **60 seconds** for the calculation.

**CrowdStrike 2023 Threat Hunting Report (human baseline used by Lee):**
- Average time to lateral movement: 79 minutes.
- Fastest observed breakout: ~7 minutes.
- Industry range: 48–120 minutes.

**Lee's math:** 79 min ÷ 30 sec ≈ 158x; 79 min ÷ 60 sec ≈ 79x; 48 min ÷ 30 sec = 96x, halved = 48x, "reduced to 47 for credibility."

**The killer quote:**
> "Yes, that's the actual reason it's 47 and not 48. I wish I had a more rigorous justification. I don't."

Also worth knowing: a separate 2025 MIT study (cited by Malwarebytes / Cybersecurity Dive) showed an AI model using MCP "achieved domain dominance on a corporate network in under an hour with no human intervention, evading EDR through on-the-fly tactic adaptation." Source: [Cybersecurity Dive, "Autonomous attacks ushered cybercrime into AI era in 2025"](https://www.cybersecuritydive.com/news/cybercrime-ai-ransomware-mcp-malwarebytes/811360/).

The CAI (Cybersecurity AI) 2025 paper reported automated expert-level performance "3,600× faster than humans while reducing costs 156-fold" — a more aggressive number than Lee uses.

### 1.5 Composite framing for our pitch (3-sentence narrative)

> In November 2025, Anthropic disclosed GTG-1002 — a Chinese state operation where Claude Code autonomously executed 80–90% of an espionage campaign across ~30 targets, making "multiple requests per second." Defender OODA loops still run in hours; the adversary's runs in seconds. Find Evil! exists to close that gap — to give defenders the same MCP-orchestrated agent architecture that just got operationalized for offense.

---

## 2. Rob T. Lee — the judge's worldview

### 2.1 SANS blog post: "Protocol SIFT: An Experimental Research Initiative for AI-Assisted DFIR"

**URL:** https://www.sans.org/blog/protocol-sift-experimental-research-initiative-ai-assisted-dfir

**Verbatim positioning:**

> "AI acts strictly as a constrained workflow assistant used to coordinate DFIR tooling, sequence analytical steps, and reduce friction in repetitive tasks."

> "Protocol SIFT is in its initial research stage and has not been validated for forensic soundness or evidentiary reliability."

> Deterministic DFIR utilities remain the sole source of analytical output; investigators (not the AI) handle validation, interpretation, and reporting.

**5-bullet summary of what this post telegraphs:**
- Protocol SIFT is positioned defensively/legally — NOT court-admissible, NOT a replacement for analysts.
- "Constrained workflow assistant" is the preferred framing — not "autonomous agent."
- Deterministic tools = source of truth. The LLM is the orchestrator, not the analyst.
- Human oversight is mandatory throughout.
- Research-stage, community-driven, open-source.

### 2.2 Substack: "Introducing Protocol SIFT: Meeting AI Threat Speed with Defensive AI Orchestration"

**URL:** https://robtlee73.substack.com/p/introducing-protocol-sift-meeting

**The defining quotes** (these are the ones to internalize):

> "The velocity gap between AI offense and human defense is already operational, and closing it requires defenders to build with the same architecture."

> "Defensive OODA loops are measured in hours while offensive loops are now measured in seconds. Defenders are out here bringing knives to a drone strike."

> "The architecture they used, an agentic AI connected to offensive tools via MCP, is the exact same architecture I'd been building for defense."

> "the AI sometimes 'fabricated credentials' or overstated access levels" — and: "Claude doesn't get defensive when you call it out."

> "I've been doing this for 27 years... watched the industry spend billions on detection capabilities while the actual investigation workflow hasn't fundamentally changed."

> "Two-thirds [of tested students] showed meaningful improvement in time-to-findings" (with Protocol SIFT in SANS classes).

> "Chinese state hackers operationalized this first... should tell you something about our collective sense of urgency."

> "the adversary's loop still runs in seconds, so we haven't won anything. We've just stopped losing quite as badly."

**5-bullet summary of Rob's worldview from this post:**
- Speed asymmetry is the whole problem. Not detection coverage, not better signatures — *speed*.
- Same architecture for defense as offense (agentic LLM + MCP + many specialized tools).
- Hallucination is acknowledged, owned, not hand-waved away.
- 27-year veteran framing: "the workflow hasn't fundamentally changed" — he's tired of incremental detection investments.
- China framing: nation-state did this first. Urgency = national security.

### 2.3 Substack: "AI Isn't a Tool Anymore. It's an Operator." (SANS AI Cybersecurity Summit notes)

**URL:** https://robtlee73.substack.com/p/ai-isnt-a-tool-anymore-its-an-operator

> "Stop threat modeling AI like a tool and start threat modeling it like an operator." (quoting Yotam Perkal)

> "When you give an autonomous agent business context, access to tools, and permission to act, it stops being software. It becomes an actor, a privileged actor."

> "Stop modeling the AI. Start modeling the workflow."

> Quoting Julie Davila: "Failures rarely occur where you're watching. They occur in the seams between the components." Lee adds vulnerabilities live "in the orchestration layers, the APIs and the points where untrusted AI output gets serialized into privileged execution boundaries."

> Defenders built "security controls assuming we were defending against humans or relatively simple malware. Not autonomous agents or systems that can test thousands of variations."

### 2.4 Substack: "My talk at [un]prompted: SIFT - Find Evil! The Era of Autonomous Forensics"

**URL:** https://robtlee73.substack.com/p/dangerous-new-attack-techniques-rsac-2026-preview-protocol-sift

> "I typed two words, 'find evil,' and fourteen minutes twenty-seven seconds later had a complete C drive analysis."

> "The tool handles the syntax so the investigator can focus on what actually requires a human: reading the findings and driving the case. Only someone who knows DFIR can interpret that output."

YouTube version of the talk: [un]prompted 2026 (uploaded Mar 25, 2026): https://www.youtube.com/watch?v=OsUg3TlAqjQ — title: "SIFT-FIND EVIL! I Gave Claude Code R00t on DFIR SIFT Workstation."

### 2.5 SANS press release: "Two Words That Changed Cybersecurity..."

**URL:** https://www.sans.org/press/announcements/two-words-changed-cybersecurity-find-evil-builders-answer-call-defend-infrastructure

Three more quotes that should be on the wall while we build:

> "The answer is not faster humans. The answer is AI-augmented defenders, matching AI speed with AI speed."

> "I built Protocol SIFT thinking I was ahead of the curve. Then Anthropic's security team disclosed a Chinese state-sponsored operation using the exact same architecture for offense."

> "Offensive teams operate with three or four people working in secret. We're putting the entire practitioner community on this problem at the same time."

### 2.6 What Rob will reward / penalize (prediction)

Based on the corpus above, Rob's vote criteria — in priority order:

1. **Will reward:** Architectural constraints over prompt-based ones. The MCP server *physically cannot* run destructive commands → wins. "I prompted Claude to be careful with rm" → loses.
2. **Will reward:** Explicit hallucination handling. A submission that catches and flags its OWN hallucinations beats a submission that pretends not to hallucinate. Honesty > perfection (rules section literally says this).
3. **Will reward:** Court-admissibility-aware chain-of-custody. Read-only evidence mounts, output hashing, structured audit logs. Rob built SIFT in 2007 for court-admissible work — he cares about this lineage.
4. **Will reward:** Speed measured as time-to-findings, not lines of code or tool count. He cited "two-thirds improvement in time-to-findings" as the SANS-classroom success metric.
5. **Will penalize:** Anything that makes Claude *replace* the analyst. He says explicitly: "Only someone who knows DFIR can interpret that output." Submissions framed as "fire your analysts" lose. Framing must be "augment the senior analyst."
6. **Will penalize:** Hallucinated tool output. Models inventing files/paths/CVEs that don't exist in the image. This is the #1 known failure mode he's flagged.
7. **Will penalize:** Marketing-style "autonomous SOC" branding without architectural rigor. He's hostile to vendor copilot language. Sound like an investigator, not a vendor pitch deck.

---

## 3. Prior art landscape

### 3.1 OSS DFIR + LLM tools that already exist

| Tool | What it does | License | Notable | Differentiation for us |
|------|--------------|---------|---------|------------------------|
| **Velociraptor** (Rapid7 OSS) | Endpoint DFIR + VQL hunting at scale | AGPL | Acquired by Rapid7 in 2024 | We're not on live endpoints — we're on dead-disk images + memory dumps. Different lane. |
| **SOCFortress velociraptor-mcp-server** | MCP wrapper exposing Velociraptor VQL to LLMs (11 tools) | AGPL-3.0, 39 stars | Production-shaped (JWT, retry logic). [github.com/socfortress/velociraptor-mcp-server](https://github.com/socfortress/velociraptor-mcp-server) | Same MCP-server pattern Protocol SIFT uses, but on live agents not forensic images. Read their tool-typing approach. |
| **snoe-findley/mcp-velociraptor** | Alt MCP for Velociraptor | Open source | Multi-LLM (Claude/Gemini/Open WebUI/n8n) | Multi-LLM compatibility is a thing judges may care about. |
| **Timesketch + Sec-Gemini** (Google) | Autonomous timeline analysis & threat hunting | Apache 2.0 | DEF CON 33 + Black Hat USA 2025 reveal. "Log Reasoning Agent" populates DFIQ questions auto-magically. | Closest spiritual prior art. We should LITERALLY reference this in our pitch — "Google built this for timelines; we built it for the whole investigation." |
| **TheHive + Cortex + MISP** | Case mgmt / observable analysis / threat intel sharing | OSS | Established SOC stack; LLM integrations now appearing via SocTalk and others. | Not forensic-image-focused — these are alert/IOC-focused. Different stage of the pipeline. |
| **SocTalk** (gbrigandi) | LLM SOC agent (LangGraph) integrating Wazuh, Cortex, TheHive, MISP via MCP | OSS | [github.com/gbrigandi/soctalk](https://github.com/gbrigandi/soctalk). Encodes triage→enrichment→verdict→human review→response. | LangGraph pattern is worth borrowing. Our domain is more invasive (kernel-level forensics) but the orchestration philosophy maps. |
| **Tsurugi Linux** | Pre-built DFIR distro (similar ethos to SIFT) | OSS | At DEF CON 33 2025 | Direct SIFT competitor at distro layer — not relevant to our hackathon scope. |
| **Virga** | LLM-powered C2 framework with embedded LLM doing autonomous post-exploitation | OSS / arsenal | DEF CON 33 2025 | OFFENSIVE counterpart. Worth name-dropping as "the offensive tool we're defending against." |

### 3.2 Vendor "AI SOC" comparison (commercial)

| Vendor | Product | Autonomy claim | Notes |
|--------|---------|----------------|-------|
| CrowdStrike | **Charlotte AI** + Charlotte Agentic SOAR | "Eliminates 40+ hours of grunt work per week, 98% accuracy" on triage; "bounded autonomy" | Multi-droid architecture. Source: [crowdstrike.com/.../charlotte-ai](https://www.crowdstrike.com/en-us/platform/charlotte-ai/) |
| Microsoft | **Security Copilot** in Defender + Sentinel MCP Server | "Security Analyst Agent" autonomously orchestrates investigations | The Sentinel MCP Server is a direct architectural analog. [Source](https://techcommunity.microsoft.com/blog/microsoftsentinelblog/the-agentic-soc-era-how-sentinel-mcp-enables-autonomous-security-reasoning/4491003) |
| Palo Alto | **Cortex XSIAM** + Cortex AgentiX (launched Oct 28, 2025) | "98% reduction in MTTR, 75% less manual work" | GigaOm Leader 3 years running. |
| Splunk (Cisco) | **Splunk Enterprise Security 8.2 + AI Assistant + SOAR** | AI Playbook Authoring, Response Importer (natural language → playbook) | September 2025 launch. |

**Key strategic differentiation:** Every one of these is *SIEM/alert/SOAR*-shaped. They operate on *streaming telemetry* and *open alerts*. Protocol SIFT lives at a different stage — *forensic dead-disk analysis*, where the breach already happened and you need to reconstruct what occurred from frozen artifacts (disk images, memory dumps, packet captures). The vendor "agentic SOC" gold rush has left the dead-disk DFIR lane wide open. That's our wedge.

### 3.3 Academic papers (2024-2026) — top 5 with gap analysis

| # | Paper | Claim | Gap we exploit |
|---|-------|-------|----------------|
| 1 | **DFIR-Metric: A Benchmark Dataset for Evaluating LLMs in DFIR** ([arXiv:2505.19973](https://arxiv.org/html/2505.19973v1)) | 14 models, 3 modules (700 MCQ, 150 CTF, 500 NIST disk/memory tasks). GPT-4.1 best — 92.75% on theory MCQ, but **0% complete solutions** on Module III (practical disk/memory cases). | Confirms practical forensics is unsolved. "Models hallucinate files, bash commands, paths or libraries that are absent from the image." Our accuracy report should benchmark against this. |
| 2 | **Digital Forensics in the Age of LLMs** ([arXiv:2504.02963](https://arxiv.org/html/2504.02963v1)) | Survey + framework. Lists hallucination, non-determinism, prompt sensitivity, chain-of-custody, no standards as core gaps. | "Non-determinism undermines reproducibility — LLMs are inherently probabilistic and may produce variable outputs" — our submission needs deterministic-tool-as-source-of-truth framing. |
| 3 | **CyberSleuth: Autonomous Blue-Team LLM Agent for Web Attack Forensics** ([arXiv:2508.20643](https://arxiv.org/abs/2508.20643)) | 3 agent architectures × 6 LLM backends on 30 controlled web-attack cases. Best: 80% accuracy with GPT-5/DeepSeek R1. Multi-agent specialization wins; flat orchestration beats nested. | Validates the modular-subagent architecture. We should cite "Multi-agent specialisation is key to sustained reasoning" + "Simple orchestration outperforms nested hierarchical architectures." |
| 4 | **Multi-Agent Collaboration in Incident Response with LLMs** ([arXiv:2412.00652](https://arxiv.org/pdf/2412.00652)) | Multi-agent LLM workflow for IR coordination. | (PDF didn't extract cleanly; rely on abstract — multi-agent IR pattern is established.) |
| 5 | **Is the DFIR Pipeline Ready for Text-Based Threats in the LLM Era?** ([arXiv:2407.17870](https://arxiv.org/abs/2407.17870)) | DFIR pipeline NOT ready for NTG-authored text threats. CS-ACT attack exploits "model sophistication and lack of distinctive style." | Different threat model (NTG-authored content) but confirms broader DFIR-readiness gap that motivates the hackathon. |

### 3.4 Adjacent OSS LLM-DFIR repos

- **teamdfir/protocol-sift** — Rob T. Lee's reference impl. 15 stars, 8 forks, 4 commits, Python (77.6%) + Shell. Skill files for memory, timeline, filesystem, Windows artifacts, YARA. Read-only enforcement via `settings.json`. **Stars are LOW** — the canonical repo is barely starred. Implication: room to define the standard.
- **AppliedIR/Valhuntir** (Steve Anson, SANS) — listed as the *example submission* in the official Devpost resources. AI-augmented IR platform with MCP tools. Human-in-the-loop with cryptographic signing, password-gated approvals. **This is the published quality bar.**
- **AppliedIR/sift-mcp** — Valhuntir SIFT platform: MCP servers + gateway + "Examiner Portal."
- **AppliedIR/wintools-mcp** — Windows forensic tool execution via MCP.
- **marez8505/find-evil** — A real hackathon submission already on GitHub. Five-phase architecture (triage → disk timeline → memory → persistence → correlation), each with self-correction. JSON tool outputs, audit hashes, Flask web UI bound to 127.0.0.1 with bcrypt. MIT license, 1 star.

### 3.5 What's NOT yet built — the wedge

Cross-referencing prior art:
- Vendor SOC tools (Charlotte/Sentinel/AgentiX) all live on **live alerts and telemetry**. None solve **dead-disk forensic triage** at agent speed.
- Sec-Gemini solves **timeline analysis** but not full investigation (memory, persistence, correlation).
- CyberSleuth handles **web-attack forensics** with 80% accuracy but only on a 30-case controlled set, not real-world disk images.
- Valhuntir is the closest analog — but it's human-in-the-loop by design with cryptographic gating. There's room for a *more* autonomous variant within rigorous architectural guardrails.
- DFIR-Metric proves nobody scores well on practical disk/memory forensic cases — Module III had 0% complete solutions.

**The wedge:** an MCP-orchestrated agent that operates on dead-disk + memory + network captures, runs the full multi-phase investigation autonomously, catches and flags its own hallucinations against deterministic tool ground truth, and produces a court-admissibility-aware structured report — and can prove its findings against the published case answer keys (Nitroba, NIST Hacking, NIST Data Leakage).

---

## 4. Validation datasets — full reference

### 4.1 Tier 1 datasets (score against these)

#### 4.1.1 Nitroba University Harassment

| Field | Value |
|-------|-------|
| URL | https://digitalcorpora.org/corpora/scenarios/nitroba-university-harassment-scenario/ |
| Download | https://downloads.digitalcorpora.org/corpora/scenarios/2008-nitroba/nitroba.pcap |
| File | `nitroba.pcap` |
| Size | ~60 MB |
| MD5 | `9981827f11968773ff815e39f5458ec8` |
| SHA1 | `65656392412add15f93f8585197a8998aaeb50a1` |
| SHA256 | `2b77a9eaefc1d6af163d1ba793c96dbccacb04e6befdf1a0b01f8c67553ec2fb` |
| Scenario | Chemistry teacher at fictional Nitroba State U. receives harassing emails. Sender used dorm-room IP, then "willselfdestruct.com" auto-delete email service. |
| Investigation question | Identify which Chemistry 109 student sent the emails. Provide conclusive evidence. |
| Materials | pcap + screenshots of headers + class roster + dorm wifi info. |
| Answer key | Password-protected solution for accredited faculty only. Not public — must reconstruct from pcap. |
| Expected pivot | HTTP traffic → identify the willselfdestruct.com POST → correlate IP + MAC + timestamp to roster. |
| Agent target | LOW–MEDIUM difficulty. Network forensics. Smallest dataset on the list. **Start here.** |

#### 4.1.2 NIST CFReDS — Data Leakage Case (Iaman Informant)

| Field | Value |
|-------|-------|
| URL | https://cfreds.nist.gov/all/NIST/DataLeakageCase (dynamic) — static archive: https://cfreds-archive.nist.gov/data_leakage_case/data-leakage-case.html |
| Answer key | https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf (publicly available — important for our accuracy report) |
| PC image | `cfreds_2015_data_leakage_pc` — E01 format, 20 GB uncompressed (~7 GB compressed). MD5 `A49D1254C873808C58E6F1BCD60B5BDE`, SHA1 `AFE5C9AB487BD47A8A9856B1371C2384D44FD` |
| Removable media image | `cfreds_2015_data_leakage_rm#3_type` — RAW ISO/CUE, 102 MB. MD5 `858C7250183A44DD83EB706F3F`, SHA1 `471D3EEDCA9ADD872FC0708297284E1960FF44F` |
| Scenario | "Iaman Informant" — tech-division manager planned to leak data to "Spy Conspirator." Caught at security checkpoint. USB stick + CD checked with portable write-blocker (no apparent evidence), transferred to forensics lab. |
| Question | Find evidence of data leakage. |
| Expected pivot | Disk forensics, USB artifact analysis, anti-forensics (suspect tried to wipe). |
| Agent target | HIGH difficulty. Full Windows disk image + removable media. Answer key is PUBLIC so we can score automatically. **Best Tier-1 target for accuracy reporting.** |

#### 4.1.3 NIST CFReDS — Hacking Case (Greg Schardt / "Mr. Evil")

| Field | Value |
|-------|-------|
| URL | https://cfreds.nist.gov/all/NIST/HackingCase (dynamic) — static: https://cfreds-archive.nist.gov/Hacking_Case.html |
| Format | DD image in 7 parts + EnCase image |
| Scenario | 09/20/04 — abandoned Dell CPi notebook (serial #VLQLW) found with wireless PCMCIA card + homemade 802.11b antenna. Suspect Greg Schardt aka "Mr. Evil" — wardriving Starbucks / T-Mobile hotspots to intercept CC numbers, creds. Ethereal installed in promiscuous mode. |
| Question | Tie the notebook to Schardt. Identify hacking activity. |
| Expected pivot | Wireless artifacts, browser history, sniffer software config, registry → username, hostname, MAC. |
| Answer key | Publicly walked through in many blog posts (e.g., `intrinsicode.net/2021/05/19/cfreds-hacking-case-report/`, `zarat.hatenablog.com/entry/2021/12/19/223735`). Multiple GitHub writeups. |
| Agent target | MEDIUM-HIGH. **Most famous CFReDS case.** Naming is rich: "find evil" → "find Mr. Evil" is on-brand. Strong demo material. |

### 4.2 Tier 2 datasets

#### 4.2.1 Ali Hadi #9 — "Encrypt Them All" (Anti-Forensics Case 2 / AHMK)

| Field | Value |
|-------|-------|
| URL | https://archive.org/details/anti-forensics-case-2 |
| Size | 7.4 GB |
| Format | Archive (torrent available, 38.7K torrent file) |
| Date added | March 24, 2023, by AHMK |
| Three challenges | (1) "Lost in Space" — recover AES-encrypted README. (2) "Do Not Be Deceived!" — decrypt BitLocker volume named R2D2. (3) "Reality Focus" — extract GPG keys, decrypt asymmetric-encrypted message in Downloads. |
| Scenario | User Jane suspected of encrypted communications with unknowns. |
| Agent target | HIGH — crypto-heavy, anti-forensics. Tests whether agent can identify crypto containers vs. just dumping strings. |

#### 4.2.2 Ali Hadi #1 — Web Server Compromise

| Field | Value |
|-------|-------|
| URL | https://archive.org/details/dfir-case1 |
| Size | 4.4 GB total |
| Components | Memory dump (110.1 MB) + disk image (1.4 GB), E01 format. Includes password info + hashes. |
| Scenario | Company web server breached via the website. Windows. |
| Agent target | MEDIUM. Classic web-compromise case. Good for memory + disk correlation. |

#### 4.2.3 DFRWS 2008 Linux Memory Challenge

| Field | Value |
|-------|-------|
| URL | https://github.com/dfrws/dfrws2008-challenge |
| Materials | Memory dump + hard disk + pcap (multi-source). |
| Scenario | "Fusion of evidence from memory, hard disk, and network." |
| Winning submission | Cohen, Collett, and Walters — password breaking, file carving, browser history parsing, evidence tampering detection. |
| Answer key | Available in `/results` folder of repo (winning writeups). |
| Agent target | HIGH — multi-modal evidence correlation. Anna Tchijova reportedly built VIGIA ground truth for this one (unverified — see §4.5). |

### 4.3 Tier 3 datasets (practice — not for scoring)

#### 4.3.1 M57-Jean

| Field | Value |
|-------|-------|
| URL | https://digitalcorpora.org/corpora/scenarios/m57-jean/ |
| Files | `nps-2008-jean.E01`, `nps-2008-jean.E02` (multi-volume EnCase) |
| Scenario | Startup data theft — confidential salary spreadsheet posted online; suspect is Jean (senior exec, sole laptop holding the doc). Jean claims she was hacked. |
| Question | Determine how data was stolen — or whether Jean is lying. |
| Answer key | Encrypted PDF (password-protected). |
| **WARNING** | Solutions widely distributed online → "should only be used for self-study, and not for academic credit." LLMs may have memorized the answers. **DO NOT USE FOR SCORING.** |

#### 4.3.2 Ali Hadi #7 — SysInternals Malware

| Field | Value |
|-------|-------|
| Directory listing | https://archive.org/download/sysinternals-case |
| Scenario | User downloaded fake SysInternals tool suite; tools wouldn't open; system slowed. |
| Expected findings | MFT shows 2× `sysinternals.exe` — first clean (likely corrupted, no MZ header), second malicious (32 VT hits). `sysinternals[1].exe` uses `URLDownloadToFileA`, `InternetOpenUrlA`, `ShellExecuteA` → second-stage downloader pattern. |
| Answer key | Extensive public writeups (windowsir.blogspot.com, hackdefendlabs.com, walshcat on Medium). |
| Agent target | MEDIUM. Practice — answer-key contamination risk. |

### 4.4 Tier 4 datasets (not ready)

#### 4.4.1 DFRWS 2011 Android Challenge

| Field | Value |
|-------|-------|
| URL | https://github.com/dfrws/dfrws2011-challenge |
| Case 1 | Suspicious Death — Donald Norby's Android. Suicide or murder? KRYPTIX crime group? `Case1.tgz` 157 MB compressed / 16.5 GB uncompressed. MD5 `9a756c41cbd3b628fb55d35e695efdee31efa58e`. |
| Case 2 | IP Theft — Yob Taog stole "Palomino" product designs from SwiftLogic. `Case2.tgz` 338 MB compressed / 16.5 GB uncompressed. MD5 `17bd6109410a0c57439aa8e701354a5f1dfd4ab3`. |
| Distribution | Dropbox links. Winning entry: Fox-IT. |
| Status | "Not ready" per hackathon rules — likely because Android-specific tooling isn't well-integrated into the SIFT MCP server set yet. Skip. |

#### 4.4.2 Volatility Cridex

URL listed as dead in the brief. Verify: original was on `files.volatilityfoundation.org`. Sample mirrors exist (`westoahu.hawaii.edu` Cridex walkthrough; sempersecurus 2012 writeup). **Skip — not maintained as canonical.**

### 4.5 VIGIA format (Anna Tchijova)

**Status: UNVERIFIED — only known from the hackathon brief.**

Searches across X, LinkedIn, Google Scholar, and academia.edu did not surface any public artifact called VIGIA tied to Anna Tchijova in a DFIR / Protocol SIFT context. A LinkedIn profile for "Anna Tchijova" (Solidaridad) exists; an X handle `@annatchijova` exists; but neither shows DFIR-tool work.

Separate note: "VIGIA" is a Brazilian government phone-call interception system referenced in forensic literature (academia.edu paper "Perícia Computacional em Artefatos Digitais de Interceptações Telefônicas") — *not* the same VIGIA.

**Conclusion:** Either (a) VIGIA is internal SANS work not yet published, (b) the name has been internally normalized to something else (e.g. embedded in the Protocol SIFT install or NotebookLM docs), or (c) it's referenced verbally only. **Action:** check the Protocol SIFT NotebookLM (https://notebooklm.google.com/notebook/f0957a60-6fb2-452b-93d4-ecd73ba47779) and the Slack community.

### 4.6 Dataset choice recommendation for our build

**Score against (in priority order):**
1. **NIST Data Leakage (Tier 1)** — public answer key, anti-forensics angle, big Windows image. *Primary accuracy benchmark.*
2. **NIST Hacking Case / "Mr. Evil" (Tier 1)** — on-brand naming, multiple public answer keys, wireless + browser + registry — exercises broad tool coverage. *Demo dataset.*
3. **Nitroba (Tier 1)** — smallest (60 MB), network-only, fast iteration. *Smoke test + CI dataset.*

**Use for development practice (don't score in accuracy report):**
- Ali Hadi #1 (Web Server) — quick to iterate on memory+disk integration.
- M57-Jean — likely memorized by LLMs; useful only for sanity checking the harness.

**Skip:**
- DFRWS 2011 Android, Volatility Cridex — explicitly Tier 4 in brief.

---

## 5. Discourse & community signal

### 5.1 X / Twitter

**Confirmed accounts/posts:**
- [@robtlee](https://x.com/robtlee) — Rob T. Lee personal. Active. Posted hackathon launch (status 2039476641903046820, 2044816200069230635).
- [@SANSInstitute](https://x.com/SANSInstitute) — Official account. Posted on Mar 12 framing (status 2044524689360318777): "first hackathon for autonomous AI incident response. Two months, $22K+ in prizes, no IR background required."

Rob's Mar 2026 tweet: "More than 1,400 solo builders and teams registered as of this morning. IR professionals, AI engineers, developers, students."

**No high-engagement participant tweets surfaced** via public search. Build-in-public discourse on X appears thin — most discussion is likely in the Protocol SIFT Slack (private).

### 5.2 Reddit / forums

Direct fetch of `reddit.com/r/computerforensics/search` blocked by tool. Google `site:reddit.com` search returned no relevant hits. **r/computerforensics and r/cybersecurity have not picked up this hackathon in any meaningful thread we could find.** Possible reasons: hackathon audience is more SANS-Slack-internal than reddit-OSS; or the discussion exists but isn't well-indexed.

### 5.3 GitHub activity on protocol-sift

- `teamdfir/protocol-sift`: **15 stars, 8 forks, 4 commits, 0 open issues, 0 PRs, 0 watchers** as of fetch. Languages: Python 77.6%, Shell 22.4%. Tiny canonical repo — definitely room to influence the standard.
- `AppliedIR/Valhuntir` (Steve Anson reference impl) — listed in official resources.
- `AppliedIR/sift-mcp`, `AppliedIR/wintools-mcp` — Valhuntir MCP companion repos.
- `marez8505/find-evil` — confirmed hackathon submission, MIT, Python 63.4%. 5-phase pipeline with self-correction and JSON output guarding. **1 star, 0 forks** — this is the public-build-in-progress benchmark.

Stars across the entire Protocol SIFT GitHub footprint are tiny. The community is small but high-signal (SANS instructors, DFIR practitioners). **Implication:** novelty bar is low; quality bar is high.

### 5.4 Notable participants / institutional signal

- **3,861 registered participants** as of one Devpost fetch (rising from the initial 1,100 cited in the April press release). Internshala mirror lists the competition too — implying significant international student interest.
- **48-judge panel** including representatives from Palo Alto Networks, Google Mandiant, AWS, Lockheed Martin per the Devpost overview.
- **Valhuntir / Steve Anson** is the published quality bar.

### 5.5 Strategic implication

1. **Community is small and SANS-internal.** Discourse on public reddit/X is weak. This is NOT a hackathon won by social/marketing — it's won by submission quality the judges read in a closed review.
2. **Canonical Protocol SIFT repo is barely touched.** Whoever produces the architecturally-cleanest reference implementation can become the de facto post-hackathon standard. Rob himself said winning submissions "will be reviewed for integration back into Protocol SIFT."
3. **Vendor SOC tools have flooded the live-alert-triage space.** Dead-disk forensic agent territory is wide open and aligns with Rob's worldview (he started SIFT, he cares about court-admissibility, he wants 200+ tool orchestration).
4. **The dataset answer keys are public for the Tier-1 cases.** We can actually score ourselves automatically — and that automated accuracy report is likely the single highest-leverage submission artifact.
5. **The judge panel is large (48) and weighted toward enterprise SOC.** Sound like a tool a Fortune-500 IR lead would deploy, not a research demo.
6. **VIGIA is a wildcard.** It's mentioned in the brief but invisible on the public internet. If it's the official ground-truth framework, we should track it down through the Slack. If we can't, we build our own ground-truth scoring against the public answer keys (Data Leakage PDF, Hacking Case writeups) — and that itself becomes a defensible artifact.

---

## Appendix — primary URLs to keep open

- Hackathon: https://findevil.devpost.com/ + /rules + /resources
- SANS announcement: https://www.sans.org/blog/sans-launches-first-hackathon-autonomous-incident-response
- Press: https://www.sans.org/press/announcements/two-words-changed-cybersecurity-find-evil-builders-answer-call-defend-infrastructure
- Anthropic GTG-1002: https://www.anthropic.com/news/disrupting-AI-espionage
- Rob T. Lee substack root: https://robtlee73.substack.com/
- Protocol SIFT SANS blog: https://www.sans.org/blog/protocol-sift-experimental-research-initiative-ai-assisted-dfir
- Protocol SIFT GitHub: https://github.com/teamdfir/protocol-sift
- Protocol SIFT NotebookLM: https://notebooklm.google.com/notebook/f0957a60-6fb2-452b-93d4-ecd73ba47779
- Valhuntir reference: https://github.com/AppliedIR/Valhuntir
- DFIR-Metric benchmark: https://arxiv.org/html/2505.19973v1
- CyberSleuth: https://arxiv.org/abs/2508.20643
- Sec-Gemini / Timesketch talk: https://elie.net/talk/autonomous-timeline-analysis-and-threat-hunting-an-ai-agent-for-timesketch
