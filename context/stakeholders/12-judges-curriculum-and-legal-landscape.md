# Judges, SANS Curriculum, and the Legal Landscape

> Domain knowledge for the Find Evil! / Protocol SIFT 2026 hackathon.
> Pure facts about (a) who the 48 judges are, (b) what SANS teaches them and the analysts they evaluate against, and (c) the law that governs AI-generated forensic evidence.
> Compiled 2026-06-02 from public sources. Citations inline.
>
> **What this file does NOT do:** prescribe what to design for. The wedge is `STRATEGY.md`. Architecture is for the design phase. This file is the ground truth those phases consult.

---

## Why this matters

A hackathon's published rubric is one signal. The judges' *internalized* rubric — the mental models they bring from 20–30 years in DFIR, the SANS curriculum they wrote or absorbed, the courtrooms they have testified in, the SOCs they run — is a much stronger signal. A submission that resonates with what judges already believe is a submission that earns favourable readings on every borderline criterion.

This file is the briefing book for that internalized rubric.

It has three parts:

- **Part A — Judge personas.** Twenty deep dives + a thumbnail of the remaining ~28. Verbatim quotes where available, with source URLs. Predicted reading-lens per judge, not a prescription.
- **Part B — SANS DFIR curriculum.** What the canonical courses teach, what mental models students absorb, what artifacts are emphasized, what a SANS-shaped analyst looks like on the page.
- **Part C — Legal landscape.** FRE 702 / Daubert / FRE 707 (Dec 2024), chain-of-custody requirements, the Best Evidence Rule, hearsay considerations, early AI-evidence case law, and the EU framing.

Every claim in Part C is descriptive. Whether a submission *should* be framed around legal admissibility is a design-phase decision documented in `STRATEGY.md` and discussed in `research/protocol-sift-2026/.raw/08-rob-full-framing.md` — Rob T. Lee explicitly disclaims court-use as a Protocol SIFT goal. The legal landscape is still useful to know because (a) several judges hold expert-witness lenses by reflex, (b) "what would survive scrutiny" is a useful design heuristic even if "court-admissible" is not in the pitch.

---

# Part A — Judge Personas

The hackathon panel is 48 judges. We have direct evidence about ~20 (LinkedIn, SANS profiles, blog posts, X feeds, published talks, court records). The other ~28 are thumbnails: organization + role + the lens we can reasonably infer from that combination.

The personas below are organized by influence and by lens, not alphabetically.

---

## A1. Rob T. Lee — Chief AI Officer & Chief of Research, SANS Institute

**Role.** Rob T. Lee is the head judge by every reasonable definition. He created Protocol SIFT, named the hackathon, set the prize money, wrote the SANS blog announcement, and runs the SANS Slack/Discord where competitors gather. ([SANS profile](https://www.sans.org/profiles/rob-lee), [Substack](https://robtlee73.substack.com/))

**Career arc (10-year window).**

- 2014–2018: Curriculum Lead, SANS DFIR. Continued evolving FOR508 (Advanced IR) and FOR526 (Memory Forensics, with Alissa Torres). Built out the SIFT Workstation as the de facto open-source DFIR VM.
- 2018–2023: Faculty Lead, SANS DFIR. Increasingly visible at RSA, BlackHat, FIRST conferences.
- 2023: Promoted to Chief Curriculum Officer.
- 2024–2025: Took Chief AI Officer + Chief of Research role. Began the AI Cybersecurity Hackathon series (the predecessor to Find Evil!).
- Nov 2025: Co-published Protocol SIFT alongside Anthropic's disclosure of GTG-1002 (a Chinese state-sponsored campaign that used Claude Code + MCP for 80–90% of tactical operations).
- 2026: Launched Find Evil! hackathon (Apr 15 – Jun 15), and the Substack `robtlee73.substack.com` as the public running commentary.

He has been doing DFIR for **27 years** by his own count ([Substack intro post](https://robtlee73.substack.com/p/introducing-protocol-sift-meeting)). He created the SIFT Workstation around 2007.

**Education / certifications.** US Air Force Academy graduate. Former Air Force intelligence officer. Held many GIAC certifications across his career (GCFA, GCIH, GREM, GCFE).

**Published material we have read directly.**

- **Substack `robtlee73.substack.com`** — primary current voice. Posts read for this brief:
  - "Introducing Protocol SIFT: Meeting AI Threat Speed with Defensive AI Orchestration" (~Jan 2026)
  - "Protocol SIFT: An Experimental Research Initiative for AI-Assisted DFIR" (SANS Blog, ~Jan 2026)
  - "Why 47? The Math Behind 'AI Attacks 47x Faster Than Humans'" (Q1 2026)
  - "AI Isn't a Tool Anymore. It's an Operator." (Q1 2026, SANS AI Summit notes)
  - "Registration is OPEN: Find Evil! Hackathon" (Apr 2026)
  - "My talk at [un]prompted: SIFT - Find Evil! The Era of Autonomous Forensics" (Mar 2026)
- **SANS blog** — "Protocol SIFT: An Experimental Research Initiative" + "Two Words That Changed Cybersecurity" press release (Apr 15 2026)
- **[un]prompted talk** — YouTube `OsUg3TlAqjQ` ("I Gave Claude Code R00t on DFIR SIFT Workstation") and `oHDnEnx_zhg` (alternate cut). Full transcripts pulled.
- **Books co-authored**: per his RSAC bio he is co-author of *Know Your Enemy, 2nd Edition* (the Honeynet Project) and contributed to *Mandiant M-Trends*. ([RSAC profile](https://www.rsaconference.com/experts/rob-lee))

Note on the *Mastering Windows Network Forensics and Investigation* book: that title is **Steve Anson, Steve Bunting, Ryan Johnson, Scott Pearson** — not Rob T. Lee. ([Amazon listing](https://www.amazon.com/Mastering-Windows-Network-Forensics-Investigation/dp/1118163826)). Rob is associated with that subject area through FOR500 / FOR508 course development, not that specific book.

**Worldview — verbatim quotes with sources.**

> "Adversaries are operating at machine speed. The answer is not faster humans."
> — *Introducing Protocol SIFT*, [robtlee73.substack.com](https://robtlee73.substack.com/p/introducing-protocol-sift-meeting)

> "Defenders are out here bringing knives to a drone strike."
> — *Introducing Protocol SIFT*

> "Defensive OODA loops are measured in hours while offensive loops are now measured in seconds."
> — *Introducing Protocol SIFT*

> "Teach an AI agent to think like a senior analyst, how to sequence its approach, recognize when something doesn't add up, and self-correct when it gets it wrong."
> — *Registration is OPEN*, [Substack](https://robtlee73.substack.com/p/registration-is-open-find-evil-hackathon)

> "When a Volatility command returns an error, Claude reads the error message, adjusts its hypothesis... and retries."
> — *Introducing Protocol SIFT*

> "A tool that's fast but fails silently is worse than useless. In forensics you need to know what you couldn't find as much as what you did find."
> — *Introducing Protocol SIFT*

> "Protocol SIFT works. It also hallucinates more than we'd like. (That's exactly why this hackathon exists.)"
> — *Registration is OPEN*

> "Only someone who knows DFIR can interpret that output."
> — *[un]prompted* talk Q&A

> "I typed two words, 'find evil,' and fourteen minutes twenty-seven seconds later had a complete C drive analysis."
> — *[un]prompted* talk, the 14:27 demo anchor

> "The architecture they used [in GTG-1002] — an agentic AI connected to offensive tools via MCP — is the exact same architecture I'd been building for defense."
> — *Introducing Protocol SIFT*

> "Any time AI-generated data crosses a trust boundary that assumes human input, failure is guaranteed."
> — *AI Isn't a Tool Anymore. It's an Operator.*

> "Yes, that's the actual reason it's 47 and not 48. I wish I had a more rigorous justification. I don't."
> — *Why 47?* post — characteristic of his tone: rewards honest admission over vendor polish.

**Vocabulary Rob explicitly uses (frequency from `08-rob-full-framing.md`):**

- "constrained workflow assistant" (3 mentions)
- "sequence analytical steps" / "sequence its approach" (4)
- "self-correct when it gets it wrong" / "performing self-correction" (5)
- "augment — never replace — the human practitioner" (4)
- "AI-augmented defenders, matching AI speed with AI speed" (4)
- "deterministic DFIR utilities remain the sole source of analytical output" (3)
- "think like a senior analyst" (3)
- "Inference Constraint layer where the AI directs the workflow" (1)
- "trust but verify" (1)
- "Tool User → Tool Orchestrator" (2)

**Vocabulary Rob explicitly avoids:**

- "autonomous SOC" / "replace analyst" / "AI L1"
- "fully autonomous" without "with human oversight"
- "court-admissible" / "forensically sound" / "evidentiary" — he writes the explicit disclaimer "**not validated for forensic soundness or evidentiary reliability**" and "**not intended for evidentiary use in legal proceedings.**"
- "eliminates hallucination" — only "reduces," "self-corrects," "flags."

**What he is likely to notice in a submission (predicted lens — not prescription).**

- Whether the agent demonstrates **sequencing as a behavior**, not just claims it in the README.
- Whether tool errors trigger **self-correction** visible in the logs ("the Ralph Wiggum Loop" framing, though he himself uses "self-correction" rather than the meme).
- Whether the README admits what the agent could **not** find — epistemic honesty.
- Whether the architecture imposes constraints **structurally** vs. by prompting.
- Whether speed is reported as a number, against a baseline.

**Recent X / Substack activity.** Substack is updated roughly weekly; X account `@robtlee` posts daily on hackathon counts ("1,400 registered," "1,900 registered," etc.). The [un]prompted YouTube cut is the highest-fidelity public artifact of his current thinking.

---

## A2. Ovie Carroll — Director, DOJ Cybercrime Lab (CCIPS); SANS Principal Instructor; FOR500 co-author

**Role.** Director of the Cybercrime Lab at the U.S. Department of Justice Computer Crime and Intellectual Property Section (CCIPS). Principal Instructor and course author at SANS Institute. Formerly adjunct professor at George Washington University in the Master of Forensic Science program. ([SANS profile](https://www.sans.org/profiles/ovie-carroll), [personal site](https://ovie.coffee/about-me))

**Career arc.**

- **38+ years** of law enforcement experience.
- Prior to DOJ: Special Agent in Charge of the **Computer Investigations and Operations Branch at the Air Force Office of Special Investigations (AFOSI)**.
- Prior to AFOSI: ran the **Technical Crimes Unit at the Postal Inspector General's Office**.
- As a special agent: coordinated **national-level computer intrusion investigations**.
- Currently: directs CCIPS Cybercrime Lab; teaches SANS Windows Forensics; speaks internationally.

**Education / certifications.** Multiple GIAC certifications historically. Adjunct at George Washington University Master of Forensic Science program. Awarded the **2017 Presidential Rank Award of Meritorious Senior Professional**.

**Published material we have read.**

- **`ovie.coffee`** — personal site. Two posts of note:
  - "Challenges in Modern Digital Investigative Analysis" — [ovie.coffee/about-me/f/challenges-in-modern-digital-investigative-analysis](https://ovie.coffee/about-me/f/challenges-in-modern-digital-investigative-analysis)
  - "The Power of the USN Journal in Digital Forensics" — [ovie.coffee/about-me/f/the-power-of-the-usn-journal-in-digital-forensics](https://ovie.coffee/about-me/f/the-power-of-the-usn-journal-in-digital-forensics)
- **FOR500** — Windows Forensic Analysis. Co-author with Heather Barnhart, Mattia Epifani, Rob T. Lee.
- **DFRWS 2012 keynote speaker.**

**Worldview — verbatim quotes.**

> "Digital devices are silent witnesses. The Digital Investigative Analyst acts as their voice, meticulously translating the data into an objective narrative."
> — ovie.coffee, *Challenges in Modern Digital Investigative Analysis*

> "Through meticulous examination, they extract the unvarnished story from electrons, a chronicle free from bias or embellishment."
> — same source

This is the **"silent witness" frame**. The investigator is a translator. The artifact is the speaker. The investigator is *not* an advocate, not a storyteller, not an interpreter of motive — they are someone who reads what the device already said and writes it down without editorial.

**What he likely notices.**

- Whether findings are written as **observation** ("Process X spawned Process Y at T") or as **interpretation** ("the attacker pivoted via mshta"). The first survives cross-examination; the second invites it.
- Whether the agent's claims **trace to specific artifact + specific timestamp + specific tool execution**.
- Whether the report distinguishes "confirmed" from "inferred."
- Whether the chain — image acquisition → parser → finding — is documented at each hop.
- Whether the language is **objective** vs. editorial.

**On his SANS profile he writes:** "For me, digital forensics is about the hunt for evidence in digital places that are hiding critical clues, followed by deep analysis." (His framing emphasizes *hunt* + *deep analysis* — not "AI does it for you.")

---

## A3. Adam Nasreldin — Senior Incident Response Consultant, Google Mandiant

**Role.** Senior IR Consultant at Google Cloud Mandiant. ([LinkedIn](https://www.linkedin.com/in/adam-nasreldin-1a55929/))

**Career arc.**

- ~20 years in cyber/network security.
- **Cisco (EMEA)**: progressed from Systems Engineer → Consulting Security Engineer (EMEA). Focus: network infrastructure + security solutions.
- Prior: Instructor and Consultant at Fast Lane.
- Current: Mandiant Senior IR Consultant. Competencies (per his LinkedIn): Enterprise + Cloud IR, Digital Forensics, Host Analysis, Network Analysis, Cloud Forensics, Static + Dynamic Malware Analysis, Memory Forensics, Disk Forensics, Windows Forensics.

**Published material.** No personal blog surfaced. He carries the **Mandiant house style** instead — which is itself a documented body of public work.

The Mandiant house style in 2025–2026:

- **Defender's Advantage Podcast** — episodes on AI-assisted IR, including "How Mandiant Consultants and Analysts are Leveraging AI Today" (cited as a Mandiant blog post in earlier subagent research).
- **M-Trends annual report** — Rob T. Lee was a contributor in earlier editions; the Mandiant report is the canonical CTI-grounded IR retrospective.
- **Diamond Model + ATT&CK-mapped narratives** — every published IR engagement summary ties findings to a threat actor, a campaign, and ATT&CK technique IDs.

**What he likely notices.**

- **Threat intelligence applied to artifacts** — is the agent grounding findings in MITRE ATT&CK + known threat-actor playbooks, or freelancing the interpretation?
- **Hypothesis-driven investigation** vs. blind tool-running.
- **Structured triage** — what's the order of investigation, and is it the order a Mandiant consultant would use?
- **Adversary attribution** synthesis when the TTPs fit a known actor.
- The README writing style — does it look like a Mandiant engagement report or a hackathon dump?

---

## A4. Cheri Carr — Owner & Principal Consultant, Aspen Forensics; Texas-licensed PI

**Role.** Owner of Aspen Forensics, a boutique DFIR consulting firm in Texas. Texas-licensed Private Investigator. ([Aspen Forensics](https://aspenforensics.com/), [JurisPro CV](https://www.jurispro.com/expert/cheri-carr-10174/cv))

**Career arc.**

- **Pioneer DFIR practitioner.** Founding member of the **Air Force and DoD Computer Forensics Laboratories** — the first of their kind. Developed many of the processes and procedures still in use today.
- **Air Force Office of Special Investigations (OSI)** — forensic examiner.
- **NASA Office of Inspector General (OIG)** — forensic examiner.
- **Sally Beauty** — internal forensic role.
- **Stroz Friedberg (an Aon company), 2018–2022** — Managing Director and DFIR Practice Leader. Stroz is one of the most prestigious DFIR consulting practices in the US.
- **Secureworks** — DFIR.
- **Aspen Forensics, current** — owner/principal.

**Education / certifications.**

- Licensed Private Investigator (Texas)
- Seized Computer Evidence Recovery Specialist (SCERS)
- Multiple GIAC certifications historically

**Expert witness experience.** Testified as expert witness "dozens of times" in federal and state courts. Documented matters include:

- *Herff Jones Data Breach Litigation* (2021) — signed declaration in mediation re: PCI data breach impact on customers
- *Camillo Properties matter* (2020) — affidavit re: forensic artifacts of former employee conduct

She describes her career signature as both "the quality of her work" and "her ability to communicate results to both technical and non-technical audiences alike."

**Worldview.** No personal blog surfaced. Her writing voice lives in case declarations and CV. The Stroz Friedberg + Air Force OSI + expert-witness combination is itself the worldview:

- **Bulletproof chain of custody.** Federal cases hang on it.
- **Reproducibility.** Another examiner has to be able to verify your work.
- **Communication to non-technical audiences.** Juries, judges, executives.

**What she likely notices.**

- Whether evidence-handling discipline is built in — hash verification, write-blocking, custody logs.
- Whether findings would survive opposing-counsel cross-examination ("how did you arrive at this?").
- Whether the demo video and write-up are **understandable to a non-engineer**.
- Whether the agent **conflates inference with fact**, which is the killer error in expert-witness testimony.

---

## A5. Steve Cobb — CISO, SecurityScorecard

**Role.** Chief Information Security Officer at SecurityScorecard since 2023. ([SecurityScorecard leadership](https://securityscorecard.com/people/leadership/steve-cobb/), [LinkedIn](https://www.linkedin.com/in/wscobb/))

**Career arc.**

- **25+ years** in IT infrastructure + cybersecurity + IR + threat intel.
- **Verizon Managed Security** — early career, large-scale managed security operations.
- **Microsoft** — Senior Escalation Engineer.
- **SecurityScorecard, 2023–present** — CISO. Provides strategic IT consulting + delivers organization efficiency + security for customers.

**Public speaking and frameworks.**

- Frequent speaker: **InfoSecCon**, **Cyber Defense Summit**, multiple CISO board events.
- RSA Conference 2026 speaker — "The Outside-In Advantage: Modernizing TPRM with AI and Threat Intelligence" — focus on **third-party risk management** in the AI era.
- BrightTALK webinar series — "From Spreadsheets to Strategy: Introducing SecurityScorecard's Supply Chain Resilience Journey."

**Public framework — "From Prevention to Resilience" / "From Reactive to Resilient."**

The thesis (synthesized from his published webinars and the SecurityScorecard blog post by that name, [securityscorecard.com/blog/from-reactive-to-resilient-a-new-mindset-for-supply-chain-cybersecurity](https://securityscorecard.com/blog/from-reactive-to-resilient-a-new-mindset-for-supply-chain-cybersecurity/)):

- Perfect prevention is impossible at scale.
- **Resilience** = the organization's ability to minimize impact when an incident occurs.
- Three core IR principles: **isolate, contain, neutralize.**
- "Success in response depends on the speed, coordination, and preparation of the team."
- **Supply chain visibility** is the underexplored axis — what your vendors do affects your blast radius.

**What he likely notices.**

- **Speed-to-containment**, not just speed-to-detection.
- "What do we do now" triage prioritization, not just "what happened."
- **Blast-radius scoping** — does the agent recognize cross-host implications?
- Whether the workflow looks like something a Fortune-500 CISO would actually deploy.

---

## A6. Jens Ernstberger — Founder, Kontext Security

**Role.** Founder of [Kontext Security](https://kontext.security), an AI agent authorization platform. PhD researcher at Technical University of Munich. ([ernstberger.xyz](https://ernstberger.xyz/), [USENIX bio](https://www.usenix.org/conference/usenixsecurity24/speaker-or-organizer/jens-ernstberger-technical-university-munich))

**Career arc.**

- PhD work at TU Munich — applied cryptography, zero-knowledge proofs, agent security.
- **USENIX Security 2024 — co-author of "SoK: What Don't We Know? Understanding Security Vulnerabilities in SNARKs"** — analyzed 141 vulnerability reports over ~6 years across the SNARK stack. ([USENIX paper](https://www.usenix.org/system/files/usenixsecurity24-chaliasos.pdf))
- 2025–2026: Pivoted from SNARK security to AI agent security. Founded **Kontext** — runtime contextual authorization for AI agents.

**Published material.**

- **`ernstberger.xyz`** — personal blog. Key post: ["Why Contextual Authorization Is the Missing Layer for Safe AI Agents."](https://ernstberger.xyz/posts/04_contextualauth/)
- **`kontext.security/blog`** — Kontext's blog: "Give Agents Real Credentials."
- **Boring AppSec Podcast Ep 35** — "Exploring Security After Determinism with Jens Ernstberger" — [boringappsec.com/p/ep-35-exploring-security-after-determinism](https://www.boringappsec.com/p/ep-35-exploring-security-after-determinism).

**Worldview — the "contextual authorization" thesis.** From his blog post:

> Each time an agent receives a task, the platform assembles trusted context and generates a **purpose-bound contract** that spells out which tool calls are acceptable. The policy lives only for the duration of the task and is enforced deterministically in real time, and if the agent tries a step outside the contract, execution stops.

Implementation has four parts (in his own framing):

1. **Schema definition for tool APIs** — what tools exist, what they can do.
2. **Policy generation** — an LM fine-tuned on security norms produces per-task policies.
3. **Real-time enforcement** — a pure function evaluates each call against the active policy.
4. **Audit trail with human-readable rationale** — every allow/deny is explained.

The framing: **AI agents now triage email, push code, and spin up cloud resources. Their power is their context awareness. That same context can turn against them.** Traditional security assumptions (long-lived API keys, browser sessions, composability, access control) break under agentic patterns.

**What he likely probes.**

- The MCP server itself for prompt-injection resistance.
- How tool calls are authorized — who decides this agent can run `vol3 -f memory.dmp pslist`?
- Credential handling — short-lived vs. long-lived, scoped vs. ambient.
- Whether the agent can **escalate privileges** via tool chaining.
- Whether the audit trail explains *why* each action was permitted.

---

## A7. Yotam Perkal — Head of Security Research, Pluto Security

**Role.** Head of Security Research at [Pluto Security](https://pluto.security). ([SANS profile](https://www.sans.org/profiles/yotam-perkal))

**Career arc.**

- Security research career across multiple cybersecurity firms before Pluto.
- 2026: Discovered **CVE-2026-33032** ("MCPwn") — an authentication bypass in **nginx-ui**'s MCP integration. CVSS 9.8. Patched March 15, 2026. ([thehackernews coverage](https://thenackernews.com/2026/04/critical-nginx-ui-vulnerability-cve.html))
- Active vuln-research output: also surfaced research into Anthropic's autonomous agent stack.

**Published material.**

- **MCPwn disclosure**: ["MCP Bug in Nginx: Critical CVSS 9.8 Security Vulnerability"](https://pluto.security/blog/mcp-bug-nginx-security-vulnerability-cvss-9-8/) — April 15, 2026. Pluto Security blog. Title in some venues: "MCPwn: A CVSS 9.8 One-Line MCP Bug That Hands Over Your Nginx to Anyone on the Network – Actively Exploited in the Wild."
- ["Inside Claude Cowork: How Anthropic's Autonomous Agent Actually Works"](https://pluto.security/blog/inside-claude-cowork-how-anthropics-autonomous-agent-actually-works/) — reverse-engineering of Claude Cowork's agentic stack.

**The MCPwn vulnerability in one paragraph (because it tells you what he looks for).** nginx-ui's MCP integration exposed two HTTP endpoints: `/mcp` (which required IP whitelisting AND authentication) and `/mcp_message` (which only applied IP whitelisting, and the **default IP whitelist was empty — treated as "allow all"**). Any network attacker could invoke all MCP tools without authentication: restart nginx, create/modify/delete config files, trigger auto-reloads → full server takeover in two HTTP requests. ~2,689 exposed instances per Shodan at disclosure. VulnCheck added it to KEV; Recorded Future Insikt Group flagged it as one of 31 high-impact CVEs actively exploited in March 2026 (risk score 94/100).

**Worldview.** **MCP endpoints inherit application capabilities without security controls by default.** Every MCP-shaped system is a potential MCPwn. The "right" thing to do is also the easy thing to get wrong (one missing middleware call).

**What he likely probes.**

- **The MCP server design** — does it enforce authentication on every endpoint? Are there default-empty whitelists?
- **Adversarial evidence handling** — what if the evidence itself contains prompt injection?
- **Process boundaries** — what runs as what user, with what capabilities?
- **Tool-call chaining attacks** — can a sequence of legitimate calls produce an illegitimate outcome?

Expect Yotam to **reverse-engineer the MCP server** of any submission worth his time. If the architecture diagram skimps on the trust boundary diagram, he will notice.

---

## A8. Brad Edwards — Domain Consultant, SecOps, Palo Alto Networks

**Role.** SecOps Domain Consultant at Palo Alto Networks (Cortex). ([LinkedIn](https://www.linkedin.com/in/bradley-edwards-dev/))

**Career arc.**

- **Ex-RCMP Major Crime** — Royal Canadian Mounted Police, major crime investigations including DFIR.
- Transitioned from law enforcement into private-sector cyber.
- Currently: SecOps Domain Consultant specializing in **Cortex AI SecOps and Autonomous Cyber** at Palo Alto Networks.

**Worldview (inferred from role + employer's product positioning).**

- **Cortex XSIAM** is Palo Alto's "AI-driven SecOps platform." Brad's job is selling the production case for AI SecOps.
- The lens is: **does this work at the scale of a 24/7 enterprise SOC?**

**What he likely notices.**

- Production-deployability — can this be installed and run by someone who isn't a SANS instructor?
- Scalability beyond one analyst.
- Whether the agent fits the **alert → triage → escalation** pattern an SOC already runs on, or fights it.
- Integration points with existing SIEM/SOAR/EDR.

---

## A9. Steve Anson — SANS Principal Instructor; FOR508 co-author; co-founder of Informed Defense / Applied Incident Response; architect of Valhuntir

**Role / status as judge.** Steve Anson is the architect of **Valhuntir** ([github.com/AppliedIR/Valhuntir](https://github.com/AppliedIR/Valhuntir)) — the reference submission the hackathon brief explicitly cites as "the quality bar to meet or exceed." As of the public materials reviewed, he is named on the panel; even if he were not, his Valhuntir architecture is the *de facto* judge of every submission because that is the published reference. Treat him as a top-tier judge by proxy.

**Career arc.**

- **25+ years DFIR.**
- **Defense Criminal Investigative Service (DCIS)** — computer crime investigations.
- **FBI task force agent** — computer crime specialization.
- **Instructor at the FBI Academy** + **US Department of State** — trained thousands of US law enforcement personnel and national police / prosecutors / judges from 60+ countries on network intrusion investigation and digital forensics.
- **SANS Principal Instructor** — co-author of **FOR508: Advanced Incident Response, Threat Hunting, and Digital Forensics** and instructor for **SEC504: Hacker Tools, Techniques, and Incident Handling**.
- **Co-founder of Informed Defense (consulting).**
- **Applied Incident Response (AppliedIR)** — owns Valhuntir.

([SANS profile](https://www.sans.org/profiles/steve-anson), [SANS Technology Institute](https://www.sans.edu/bios/steve-anson), [About Applied IR](https://www.appliedincidentresponse.com/about-applied-incident-response-and-steve-anson/))

**Published material.**

- **Applied Incident Response** (Wiley, 2020) — the book. ISBN 9781119560265. Practical IR for analysts.
- **Mastering Windows Network Forensics and Investigation** (Wiley, 2nd ed. 2012) — co-author with Steve Bunting, Ryan Johnson, Scott Pearson. Multi-author textbook on Windows network forensic investigation, chain of custody, network analysis.
- **Valhuntir codebase** itself ([github.com/AppliedIR/Valhuntir](https://github.com/AppliedIR/Valhuntir)) — the most concrete published statement of what he believes good agentic IR looks like.

**Worldview — from the Valhuntir README and architecture.**

> "Turn a single incident response analyst into the manager of an agentic AI incident response team."

> "Ultimately the human examiner drives the response."

> "Approved findings are HMAC-signed with a PBKDF2-derived key."

The Valhuntir worldview is **"forensic discipline as structure":**

- Every AI-discovered finding is staged as **DRAFT.**
- Humans cryptographically promote DRAFT → APPROVED via password-gated HMAC signature with examiner identity + timestamp + content hash.
- The AI cannot supply the password. The AI cannot approve its own work.
- The MCP gateway enforces the discipline at the response-envelope layer (audit_id, caveats, advisories, corroboration, discipline_reminder, data_provenance).
- 9 defense layers including bwrap kernel sandbox, 41 deny rules, JSONL audit log per call.
- LLM-agnostic (works with Claude Code, Claude Desktop, Cherry Studio, LibreChat) because the discipline is *not* in the model.

**What he likely notices.**

- Whether the architecture imposes discipline at the **system layer**, not the prompt layer.
- Whether the human-in-the-loop step has **cryptographic teeth** (not just a UI checkbox).
- Whether AI-bound free-text fields have **provenance markers**.
- Whether the audit trail would let another examiner reproduce the run.
- The README writing style — is it the style of someone who has testified, or someone who has shipped a side project?

This is the most domain-expert eye on the panel. He has both the courtroom lens and the modern agentic-system lens.

---

## A10. Amanda Rankhorn — Retired Senior Forensic Examiner, FBI

**Role.** Retired FBI Senior Forensics Examiner. Expert-witness lens. (Limited public web footprint; referenced in hackathon panel listing.)

**Career arc (general FBI Senior Forensic Examiner pattern).** Senior Forensic Examiners at the FBI typically:

- Conduct evidentiary examinations supporting federal investigations.
- Issue formal reports admitted at trial.
- Testify as expert witnesses in federal and state courts.
- Train other examiners. Senior is the rank one promotes to after demonstrating reliability under cross-examination.
- Carry GIAC/IACIS/EnCE/CFCE certification stacks.

We were not able to surface specific case testimony, published papers, or a personal blog for Amanda Rankhorn beyond the hackathon panel listing. The lens is the lens of every retired senior FBI examiner: **court-grade rigor.**

**What she likely notices (by role lens).**

- Whether evidence acquisition is documented end-to-end.
- Whether tools are **named, versioned, and validated.**
- Whether findings are written as observation, not interpretation.
- Whether the report would withstand a Daubert challenge.

---

## A11. John Wilson — CISO and President of Forensics, HaystackID

**Role.** Chief Information Security Officer **and** President of Forensics at HaystackID, a large eDiscovery + cybersecurity consulting firm. ([HaystackID podcast bio](https://haystackid.com/podcast-haystackid-in-the-edrm-illumination-zone-john-wilson-ciso-and-president-and-forensics/), [LinkedIn](https://www.linkedin.com/in/johnwilsonforensics/))

**Career arc.**

- **20+ years** in information security, computer forensics, IT.
- Joined HaystackID in 2018 as **President of Forensics**.
- Promoted to **CISO** in May 2019 (a newly created role) — responsibilities: extending the information security program to support international expansion, data security/privacy, technology optimization, legal and regulatory compliance.
- Leads HaystackID's **Cybersecurity Consulting Practice** — Business Email Compromise (BEC) protection, PII audits, discovery-centric security.

**Worldview / themes.**

- The **CISO+forensics dual role** is itself the worldview: he sits at the intersection of evidence handling, eDiscovery, data privacy/compliance, and security operations.
- HaystackID's work spans large-scale corporate investigations and litigation support; "weaponizing security" — the role of CISO in eDiscovery — is one of his talk topics.

**What he likely notices.**

- E-discovery-grade evidence handling — chain of custody, defensibility, preservation.
- Privacy + compliance interactions when forensic engagements cross HIPAA/GLBA/PCI/GDPR domains.
- Whether the agent's outputs would survive in a litigation-discovery setting (technology-assisted-review-style scrutiny).

---

## A12. Mathieu Alcaina — SOC L3 / DFIR Analyst, Onepoint (Europe)

**Role.** L3 SOC Analyst / DFIR at Onepoint, a 2,500-person European digital transformation firm with operations in France, Tunisia, North America, and Asia Pacific.

**Career arc.** Limited public footprint. Pattern: European SOC L3 / DFIR analysts work the same case mix as US enterprise analysts — endpoint compromises, ransomware triage, BEC, insider risk — under the additional discipline of GDPR data-handling constraints.

**Lens (by role).**

- **European DFIR practitioner reality** — GDPR constraints on what can be collected, what can be processed, what can leave a jurisdiction.
- **L3 = the escalation tier.** L3 analysts get the hardest cases L1/L2 punted. They are sensitive to "agent gives me work I have to redo" — the failure mode where AI produces a draft conclusion that ties up senior time refuting.
- The Mathieu lens is the **operational fit lens** — "would this actually help me at 3 AM?"

---

## A13. Joshua McCray — Senior Cyber Security Lead, Hilton

**Role.** Senior Cyber Security Lead at Hilton, focused on enterprise cybersecurity architecture and instructional methodologies. CISSP + CSSLP certified. Based in Charlotte. ([LinkedIn](https://www.linkedin.com/in/joshua-mccray-msit-6121a39b/))

**Career arc.**

- Previously **Cyber Security Architect at Honeywell** — aerospace cybersecurity.
- **edX** — Cybersecurity Instructional Specialist.
- **Hilton (current)** — Senior Cyber Security Lead. Fortifies digital assets against threats.
- BS Business Administration + Graduate Certificate, University of North Carolina at Charlotte.
- Also referenced as **Adjunct Instructor at North Carolina Central University** (per ZoomInfo).

**Lens.**

- **Enterprise SOC + architecture + teaching.** He thinks at the production level (Hilton is global, multi-property, distributed) and at the curriculum level (edX, NCCU).
- Likely tests for both **scale** and **teachability** — "does this scale to Hilton, and can I train a new analyst to use it?"

---

## A14. Brett Cumming — Senior Director, Information Security, Skechers

**Role.** Senior Director, Information Security at Skechers ($6B+ athleisure brand, wholesale + retail + ecommerce in 180+ countries). Board member, Retail & Hospitality ISAC (RH-ISAC). **2023 RH-ISAC Peer Choice Award for CISO of the Year.** ([RH-ISAC press](https://rhisac.org/press-release/summit-2023-awards/))

**Career arc.**

- 20+ years across cybersecurity ops + architecture + governance.
- Skechers: runs a program with **global responsibility for cybersecurity operations, security architecture + engineering, digital security, privacy + compliance, and global security strategy.**
- Speaker at multiple cybersecurity conferences.

**Themes (from his public talks).**

- AI and identity-based threats.
- Distributed technology / dissolving perimeter.
- Retail-specific risk: e-commerce, PCI, brand exposure.

**Lens.**

- **CISO-buy lens** — would I deploy this in my program?
- Skechers is mid-large enterprise; he is the SilentWitness target-user's customer.
- He cares about **operational deployability + cost + maintainability**, not academic novelty.

---

## A15. Dr. Stephen Coston — Lead Security Architect, AI and Cybersecurity (Centene Corporation)

**Role.** Lead Security Architect AI and Cybersecurity at Centene Corporation (Fortune 25 health insurance). ([LinkedIn](https://www.linkedin.com/in/dr-stephen-coston/))

**Career arc.** From public materials:

- Works at the intersection of **AI, security operations, and digital forensics**.
- Deep technical expertise + strategic insight in cloud security, IR, digital forensics.
- Securing multi-cloud infrastructure, implementing security protocols, ensuring compliance.
- Forensic work helping remediate vulnerabilities + providing prevention insights.

**Lens.**

- **Architecture lens, specifically the AI/security-architecture crossover.**
- He cares about how AI fits into the larger security program — observability, controls, governance.
- Likely reads architecture diagrams for **boundary correctness, control plane, key management, audit, governance.**

---

## A16. Preston Fitzgerald — Cybersecurity SME, SANS Institute

**Role.** OnDemand Subject Matter Expert at SANS Institute. Also a published Udemy instructor (course: "CTF 101: Competitive Learning in Cybersecurity") and Security Researcher with Synack Red Team. ([SANS profile](https://www.sans.org/profiles/preston-fitzgerald/))

**Career arc.**

- Spent years winning CTFs and mentoring CTF participants.
- SME role at SANS — supports training operations, reviews curriculum.

**Lens.**

- **Curriculum-alignment lens** — does this teach? Is the workflow learnable? Could a new student use it after FOR508?
- **CTF-builder lens** — does this show real solving behavior, or does it bluff?

---

## A17. Khushi Gupta, PhD — Assistant Professor of Computer Science, University of North Georgia

**Role.** Assistant Professor of Computer Science at the University of North Georgia (Mike Cottrell College of Business). Cybersecurity researcher bridging digital forensics, IR, and AI-driven threat mitigation. ([LinkedIn](https://www.linkedin.com/in/khushigupta2712/), [Google Scholar](https://scholar.google.com/citations?user=7PA6nPMAAAAJ&hl=en))

**Career arc.**

- **PhD in Digital and Cyber Forensic Science, Sam Houston State University.** Dissertation: framework to automate digital forensic analysis for social media platforms.
- Published research on **digital forensics education and pedagogy**, including experiential-learning-theory design of post-secondary DF teaching.
- **Guest editor**, *Future Internet* (MDPI), Special Issue "Advanced Cybersecurity, Threat Detection, and Digital Forensics for IoT Systems" (with Dr. Cihan Varol).

**Research interests.** IoT security and privacy, digital forensics for IoT, ML for cybersecurity, deep-learning anomaly detection, adversarial attacks on AI/ML, edge computing security, log analysis and attack reconstruction.

**Published papers we have seen referenced.**

- "Cybersecurity Education within a Computing Science Program — A Literature Review" (Western Canadian Conference on Computing Education).
- "Digital Forensics Lab Design: A framework" (researchgate).
- "Roblox as a Playground for Digital Forensics Analysis" (*Electronics*, MDPI).

**Lens.**

- **Pedagogy lens** — does the submission teach DFIR thinking, or hide it?
- **Reproducibility lens** — can a student set this up and learn from it?
- **Adversarial-AI lens** (her research interest in adversarial attacks on AI/ML systems aligns with prompt-injection-via-evidence concerns).

---

## A18. Sneha Parmar — Director EDR, Deutsche Bank

**Role.** Director EDR at Deutsche Bank. Limited public footprint beyond LinkedIn.

**Lens (by role).**

- **Large-enterprise EDR lens** — Deutsche Bank is one of the largest global banks. EDR at that scale is fundamentally different from boutique IR: telemetry volume, false-positive economics, regulatory exposure, multi-jurisdiction.
- She cares about: does this **integrate** with the EDR fleet she already runs? Does it **scale**? Does it preserve **regulatory defensibility**?
- Banking IR has its own regulatory overlay (FINRA, OCC, FCA, BaFin, GDPR) that compounds the standard chain-of-custody discipline.

---

## A19. Maximilian Gutowski — Head of TDR, Deutsche Telekom Security

**Role.** Head of Threat Detection and Response (TDR) at Deutsche Telekom Security GmbH. 16 years at Telekom, 11 of those in reactive security. ([LinkedIn](https://de.linkedin.com/in/maximilian-gutowski-a94771199))

**Context.** Deutsche Telekom operates an integrated **Cyber Defense & Security Operation Center** in Bonn (launched 2017) — **the biggest of its kind in Europe**, with 240+ employees worldwide, 24/7. ([Telekom blog](https://public.telekom.de/blog/managed-cyberdefense))

**Lens.**

- **Massive-scale TDR lens** — telco-scale telemetry, multi-tenant managed services, European regulatory landscape (NIS2, GDPR, BSI guidance).
- Highly sensitive to **integration with existing TI pipelines** and **SOAR/orchestration**.
- The European angle adds GDPR-aware data handling, EU AI Act considerations (high-risk AI classification debates).

---

## A20. Cumulative judge thumbnails — the remaining ~28

These are the judges named on the panel for whom we have org + role but no deeper public footprint to deep-dive. They are real influences; each adds a reading lens.

| Judge | Org | Role | Predicted lens |
|---|---|---|---|
| **Saurabh Naik** | Lockheed Martin | Head of Red Team | Adversary perspective. "What would I bypass?" Threat model of the agent itself. |
| **Jason Garman** | AWS | Principal Security Solutions Architect | Cloud-native + infra-as-code reproducibility. Forensic readiness in cloud envs. Authored AWS forensic-environment + S3-artifact-collection blogs. ([AWS blog](https://aws.amazon.com/blogs/security/forensic-investigation-environment-strategies-in-the-aws-cloud/)) |
| **Georgios Kapoglis** | Roblox | Sr/Principal Detection & Response Engineer | Detection engineering — actionable detections, not academic. Threat hunting curator on Medium. |
| **Marc Brawner** | Auxiris | Managing Partner | Boutique-IR practitioner perspective. |
| **Sandeep Bachhas** | (Bank or large enterprise) | Sr Manager, Cyber Threat Hunting | Hunt methodology — hypothesis-driven, threat-intel-led. |
| **Roshan Varghese** | (Enterprise) | Sr Information Security Manager IR | Operational fit + program-level deployability. |
| **Jeroen Hoof** | Freelance | Lead Analyst / SANS Instructor | SANS-curriculum alignment + practitioner reality. |
| **Sumit Ranjan** | (advisor) | AI Security Advisor & Ex-CTO | AI safety + strategic-architecture lens. |
| **Jon Stewart** | LevelBlue (ex AT&T Cyber) | Managing Director | MSSP-scale lens. |
| **Pedro Jimenez Argente del Castillo** | ING Hubs Spain | SOC Chapter Lead | EU SOC lens + Spanish banking regulatory overlay. |
| **Monish Alur Gowdru** | UltraViolet Cyber | Technical Security Lead | Mid-market MSSP lens. |
| **Dorian Oliver Collier** | National CSIRT | Lead / DFIR Specialist | National-CSIRT lens — incident coordination across jurisdictions. |
| **Narrayanan MKL** | Standard Chartered Bank | VP Cyber Defence | Large banking cyber-defense lens. |
| **Nodirjon Umurkulov** | (Researcher) | Security Researcher / Engineer | Independent-researcher lens. |
| **Nimitt Jhaveri** | BitScore Cybertech LLP | CEO | Founder + program-architect lens. |
| **Harish Vundavalli** | Strategic Education | Sr Technical Architect | EdTech / large-org architecture lens. |
| **Teri Green** | Elevate | VP of Technology | Legal-tech VP of tech lens (Elevate is legal services). |
| **Ahmed AbuGharbia** | cyberdojo.ai | Founder | AI security training lens. |
| **Kellep Charles** | Capitol Technology University | Cybersecurity Chair | Academic-curriculum lens. |
| **Michael Barclay** | Origin Security | Principal Security Researcher | Boutique research firm — vuln-research + reverse-engineering. |
| **Richard Nathan Smith** | (Enterprise) | Enterprise Architect | Architecture-fit lens. |
| **Muhammad Shera** | (Consulting) | DFIR Consultant | Practitioner — DFIR delivery. |

(These thumbnails are correct in role/org as of the panel listing; the predicted lenses are inference from the role title. Where a personal blog or talk surfaces, future research can deepen these.)

---

## Synthesis of judge psychology

Looking across the panel, the readable axes are:

1. **The SANS-instructor axis** (Rob T. Lee, Steve Anson, Ovie Carroll, Preston Fitzgerald, Jeroen Hoof): they will read for the SANS-curriculum patterns described in Part B. Hypothesis-driven investigation, multi-artifact corroboration, timeline-as-spine.

2. **The court-witness axis** (Ovie Carroll, Cheri Carr, Amanda Rankhorn): they will read findings for cross-examination survival. Observation vs. interpretation. Chain of custody. Reproducibility.

3. **The Mandiant-style threat-intel axis** (Adam Nasreldin, Jason Garman, Sandeep Bachhas): ATT&CK mapping, threat-actor framing, structured triage.

4. **The CISO axis** (Steve Cobb, John Wilson, Brett Cumming, Maximilian Gutowski, Sneha Parmar, Narrayanan MKL): production-deployability, scale, blast-radius, regulatory fit. Programmatic fit, not single-case heroics.

5. **The agent-security axis** (Yotam Perkal, Jens Ernstberger, Saurabh Naik): the agent's own attack surface. MCP threat model. Adversarial evidence. Prompt injection.

6. **The 3-AM-analyst axis** (Joshua McCray, Mathieu Alcaina, Pedro Jimenez Argente del Castillo, Monish Alur Gowdru): would this actually help me triage at 3 AM? Or does it produce work I have to redo?

7. **The pedagogy axis** (Khushi Gupta, Kellep Charles, Preston Fitzgerald): is this learnable? Reproducible? Teachable?

A submission that "shows" itself competently against any 3–4 of these axes earns favourable readings on every borderline criterion. None of this prescribes the architecture; the architecture should emerge from the wedge plus the constraints in `STRATEGY.md`.

---

# Part B — The SANS DFIR Curriculum

The judges are SANS-shaped. Most of them have either authored a SANS course, taught a SANS course, or completed a SANS course. The mental models the curriculum teaches are the implicit rubric they will read against.

This section documents what each canonical course teaches at a level that is useful to designers — what artifacts get attention, what tools, what mental models, what workflows. **Not what to build.** What is *true* about how SANS-trained analysts think.

The canonical DFIR/CTI curriculum: **FOR500, FOR508, FOR509, FOR526, FOR572, FOR578, FOR610, FOR710.**

---

## B1. FOR500 — Windows Forensic Analysis (→ GCFE)

**Authors and instructors.** Heather Barnhart, Mattia Epifani, Rob T. Lee, **Ovie Carroll** (head judge A2). ([SANS course page](https://www.sans.org/cyber-security-courses/windows-forensic-analysis))

**What it teaches.** End-to-end Windows forensic analysis: artifact identification, acquisition, parsing, interpretation. The course was updated in recent years for **Windows 11**, including modern artifacts. Six-day course.

**Mental models students absorb.**

- **The artifact catalog mentality.** Windows is not one thing; it is *hundreds* of artifacts each telling a partial story. Mastery = knowing which artifact answers which question.
- **The "every event leaves multiple fingerprints" principle.** Application execution leaves: Prefetch, Amcache, Shimcache, UserAssist, RecentFCache, JumpLists, MUICache, BAM/DAM, SRUM, etc. The senior analyst checks ≥2 of these for *every* claim about execution.
- **Time normalization.** All artifacts have timestamps in different formats and time zones; reconciling these is a primary skill.
- **The "what does it actually mean" discipline.** A Prefetch file proves *something was executed* — but it does not prove who executed it, when, or in what context. Each artifact has well-known semantic boundaries that students learn to respect.

**Artifacts emphasized (the FOR500 artifact catalog).**

- **Application execution**: Prefetch, Amcache, Shimcache (AppCompatCache), UserAssist, RecentFCache, MUICache, BAM, DAM, SRUM, JumpLists, ShellBags
- **File access and shellbags**: LNK files, ShellBags, JumpLists, RecentDocs, Office MRU, Recycle Bin
- **USB and external device tracking**: USBSTOR registry, Setupapi.dev.log, EMDMgmt, Mounted Devices
- **Cloud artifacts**: OneDrive, Dropbox, Google Drive, Microsoft Teams, Outlook OST/PST
- **Browser forensics**: Chrome/Edge/Firefox history, cache, cookies, autofill, downloads
- **Email forensics**: Outlook OST/PST analysis, web-based email artifacts
- **Anti-forensics indicators**: timestomping, secure deletion, BCWipe traces
- **System info and configuration**: SAM, SYSTEM, SECURITY, SOFTWARE registry hives; Event Logs (Security, System, Application, PowerShell Operational, RDP)
- **Recent advances**: WSL2 artifacts, Microsoft Teams artifacts, modern Windows 11 specifics

**Tools emphasized.** KAPE (Kroll Artifact Parser and Extractor), MFTECmd, RECmd, EvtxECmd, EZ Tools by Eric Zimmerman generally, AmcacheParser, Prefetch Parser, plaso/log2timeline, Volatility/Volatility 3, Velociraptor, Autopsy, regripper, browser forensic tools (Hindsight, KAPE).

**Common exercises.** Students work a case (typically a contractor data-theft / insider-threat scenario) where they have to:
- Acquire the image cleanly.
- Build a super-timeline from multiple artifact sources.
- Correlate USB insertion with file-access artifacts with email/browser activity.
- Distinguish "the user did X" from "X happened on the system" — semantic precision.
- Write findings to a defensible standard.

**Certification.** **GIAC Certified Forensic Examiner (GCFE).** Open-book proctored exam.

**Why it matters as context.** The judges who took or taught FOR500 expect submissions to demonstrate the FOR500 artifact catalog. An agent that handles only Prefetch is shallow; an agent that handles Prefetch + Amcache + Shimcache + SRUM + ShellBags + JumpLists reads as having taken FOR500. Whether to chase breadth is an architecture-phase decision.

---

## B2. FOR508 — Advanced Incident Response, Threat Hunting, and Digital Forensics (→ GCFA)

**Authors and instructors.** **Steve Anson (judge A9)**, **Rob T. Lee (judge A1)**, others. Six-day enterprise-scale course. ([SANS course page](https://www.sans.org/cyber-security-courses/advanced-incident-response-threat-hunting-training))

**What it teaches.** Enterprise-scale IR + threat hunting against APT-tier adversaries. The course assumes FOR500-level Windows forensics; it adds the **APT methodology, lateral movement, credential theft, persistence, memory forensics, anti-forensics, scope-and-contain, and root-cause analysis** layers.

**Mental models students absorb.**

- **Hunt-evil mental model.** Threat hunting is hypothesis-driven, not alert-driven. Start with a TTP (e.g., "WMI used for lateral movement"), generate the artifact prediction, hunt the artifact across the enterprise.
- **The APT kill chain applied to artifacts.** Initial access → execution → persistence → privilege escalation → defense evasion → credential access → discovery → lateral movement → collection → exfiltration. Each phase leaves artifact signatures.
- **Scope before clean.** First understand the full blast radius across all affected hosts; *then* remediate. Otherwise the adversary regains a foothold from a host you missed.
- **Defensible findings under cross-examination.** Each claim ties to artifact + tool execution + timestamp + corroborating artifact.

**Section structure (6 sections).** Course historically organized as:

1. **Enterprise Incident Response and Threat Hunting**
2. **Intrusion Analysis** — initial compromise, execution, persistence
3. **Memory Forensics in Incident Response and Threat Hunting** — Volatility 3 deep work
4. **Timeline Analysis** — super-timelines via plaso, mactime, KAPE; *in the 2026 update, this section concludes with a discussion of agentic AI for accelerating DFIR investigations* (per [SANS course brochure](https://assets.contentstack.io/v3/assets/bltabe50a4554f8e97f/blt125a614cea7e0087/69f23582207e69ba2e3c4bb4/SANS_Institute_FOR508_Brochure_042926.pdf))
5. **Deep-Dive Forensics and Anti-Forensics Detection** — anti-forensics catalog: timestomping, secure deletion, log clearing, Rootkit detection
6. **APT Threat Group Incident Response Challenge** — capstone with realistic APT data

**Tools emphasized.** Volatility 3, plaso/log2timeline, KAPE, Velociraptor (live response), MemProcFS, Eric Zimmerman tools (MFTECmd, EvtxECmd, RECmd, etc.), Hayabusa (Sigma rule scanner over EVTX), Sigma rules, ELK / Splunk, ARTEMIS, custom Python.

**Common practical exercises.** Working an APT scenario across multiple hosts, building enterprise super-timelines, hunting for specific TTPs (Cobalt Strike beacon patterns, PsExec lateral, WMI persistence, OAuth abuse), distinguishing AV-flagged noise from actual compromise.

**Certification.** **GIAC Certified Forensic Analyst (GCFA).** Hands-on case-based exam.

**Why it matters as context.** This is the "senior analyst" textbook Rob T. Lee references when he says "think like a senior analyst." Steve Anson is its co-author. An agent that demonstrably executes the **FOR508 mental loop** (hypothesis → multi-artifact corroboration → pivot → timeline-as-spine → ATT&CK-mapped narrative) reads as having internalized the senior-analyst behavior the head judges are calibrated against.

**Note on Section 4.** Section 4's *2026 update* explicitly discusses agentic AI for accelerating DFIR investigations. The judges who teach FOR508 have read this section. They will recognize the difference between an agent that executes the SANS timeline methodology and an agent that pattern-matches one.

---

## B3. FOR509 — Enterprise Cloud Forensics and Incident Response

**What it teaches.** Multi-cloud DFIR across **AWS, Azure, Google Cloud, Microsoft 365, Google Workspace, and Kubernetes.** ([SANS course page](https://www.sans.org/cyber-security-courses/enterprise-cloud-forensics-incident-response))

**Mental models students absorb.**

- **The cloud changes what "the disk" is.** Traditional acquisition gives way to snapshot APIs, control-plane logs, identity-provider audit trails.
- **Control-plane vs. data-plane forensics.** Cloud compromise is often discovered through CloudTrail / Activity Log / Audit Log (control-plane) before any data-plane artifact surfaces.
- **Identity is the primary artifact.** OAuth tokens, IAM roles, service accounts, federated identity — the kill chain in cloud is more often credential-shaped than executable-shaped.

**Tools and primitives emphasized.** CloudTrail, Azure Activity Log + Sign-In Log, Google Cloud Audit Logs, Microsoft Purview, mailbox audit logs, Magnet AXIOM Cyber, GCP Policy Analyzer.

**Why it matters as context.** The FOR509 lens is held by judges like **Jason Garman (AWS)**, **Sneha Parmar (Deutsche Bank — heavily cloud-leveraged)**, and **Maximilian Gutowski (T-Systems cloud-MDR)**. Whether to extend the agent into cloud is an architecture-phase decision; the rules require SIFT integration, not cloud coverage. But if the agent is read as cloud-blind it loses one optional lens.

---

## B4. FOR526 — Memory Forensics In-Depth

**Authors and instructors.** Alissa Torres (course author) and contributing instructors including Rob T. Lee historically. Six-day deep dive. ([SANS course page](https://www.sans.org/course/memory-forensics-in-depth))

**What it teaches.** Memory acquisition + analysis using Volatility (now Volatility 3), MemProcFS, and supporting tools. Detection of **rogue processes, hidden/injected code, kernel rootkits, DLL hijacking, process hollowing, persistence mechanisms.**

**Mental models students absorb.**

- **Memory is the place malware can't hide.** Disk-only investigation misses live malicious code that never touched disk. Memory shows what was actually executing at acquisition time.
- **The Volatility plugin family is the workflow.** `pslist` / `psscan` / `pstree` for process visibility; `malfind` for injected code; `cmdline` and `consoles` for command context; `netscan` / `netstat` for connections; `dlllist` and `ldrmodules` for loaded modules; `handles` for opened resources; `svcscan` for services; `cmdscan` / `consoles` for shell history; `hashdump` / `lsadump` for credentials.
- **Plugin failures are diagnostic.** When a plugin errors, that often means the symbol table is wrong for the OS version. The fix is identifying the right profile/symbol set, not abandoning the workflow.

**Rob T. Lee's "Ralph Wiggum Loop" canonical demo is built on Volatility 3.** In his [un]prompted talk he demonstrates the agent reading a Volatility error message, recognizing that the wrong plugin/symbol was used, adjusting, and retrying. This is the demo that visualizes "self-correction." It is built on FOR526 material specifically because Volatility errors are deterministic, structured, and diagnostic.

**Tools emphasized.** Volatility 3 (the current production tool), MemProcFS, Rekall (historically), bulk_extractor, AVML / WinPmem / DumpIt / FTK Imager for acquisition.

**Why it matters as context.** Memory forensics is the single most demo-friendly venue for showing "self-correction" because Volatility's errors are first-class and the canonical Rob example uses it.

---

## B5. FOR572 — Advanced Network Forensics: Threat Hunting, Analysis, and Incident Response

**Author and instructor.** Phil Hagen (course lead and author). Six-day course, ~50% hands-on labs. ([SANS course page](https://www.sans.org/cyber-security-courses/advanced-network-forensics-threat-hunting-incident-response))

**What it teaches.** Network forensics on PCAPs, Zeek/Bro logs, NetFlow data, firewall logs, proxy logs. Modern protocol coverage: **HTTP/2, HTTP/3, DoH (DNS-over-HTTPS), DoT (DNS-over-TLS).**

**Mental models students absorb.**

- **Network artifacts complement host artifacts.** Beaconing patterns, C2 callbacks, DNS exfiltration paths show up in network telemetry that an endpoint compromise alone hides.
- **Metadata is often enough.** Zeek metadata over full-packet capture is the practitioner default at scale.
- **Encrypted traffic still has fingerprints.** TLS handshake metadata, JA3/JA4 fingerprints, certificate anomalies, timing patterns.

**Tools emphasized.** **SOF-ELK** (the SANS open-source Elastic stack appliance), **Arkime** (formerly Moloch — full-packet capture and search at enterprise scale), Zeek, Suricata, Wireshark, Wireshark+CLI tools, NetworkMiner, plaso for log timeline integration.

**Why it matters as context.** If the agent operates on a SIFT VM with PCAPs and logs (and SIFT ships SOF-ELK), the FOR572 lens applies. Network forensics is also the primary route into adversary infrastructure attribution.

---

## B6. FOR578 — Cyber Threat Intelligence (→ GCTI)

**Authors and instructors.** Robert M. Lee (lead author — note: different person from Rob T. Lee), with co-instruction by Jake Williams historically. Six-day intermediate course. ([SANS course page](https://www.sans.org/cyber-security-courses/cyber-threat-intelligence))

**What it teaches.** A repeatable CTI discipline — not just collecting threat feeds. Models include:

- **Lockheed Martin Kill Chain** — phases of an intrusion.
- **Diamond Model of Intrusion Analysis** — adversary, capability, infrastructure, victim.
- **MITRE ATT&CK** — TTPs at tactic-technique-procedure granularity.
- **Courses of Action Matrix** — what defenders can do at each phase.
- **Detection Maturity Model** — measuring detection coverage.
- **F3EAD** — Find, Fix, Finish, Exploit, Analyze, Disseminate (the intelligence operations loop borrowed from military targeting).

**Mental models students absorb.**

- **Findings have a model behind them.** Saying "this looks like Cobalt Strike" without the supporting Diamond Model + ATT&CK mapping is amateur. The senior analyst always names the model.
- **Intelligence is consumed by stakeholders.** CTI is delivered to operators, executives, and the wider community in different forms; the analyst is conscious of which audience consumes which finding.
- **Confidence is a first-class output.** Every finding has a stated confidence level with reasoning.

**Why it matters as context.** Adam Nasreldin (judge A3) and the broader Mandiant culture are heavily FOR578-shaped. Findings without an ATT&CK mapping or a Diamond Model framing will read as junior to that wing of the panel.

---

## B7. FOR610 — Reverse-Engineering Malware: Malware Analysis Tools and Techniques

The introductory malware analysis course. Covers static + dynamic analysis at the level needed for everyday IR (not the advanced obfuscation work that FOR710 covers). FOR610 is implicit in FOR508 since Section 5 of FOR508 covers anti-forensics detection that overlaps with malware analysis.

---

## B8. FOR710 — Reverse-Engineering Malware: Advanced Code Analysis

**What it teaches.** Advanced reverse engineering of sophisticated Windows executables. Beyond FOR610. ([SANS course page](https://www.sans.org/cyber-security-courses/reverse-engineering-malware-advanced-code-analysis))

**Topics.** Code deobfuscation (control flow flattening, string encryption, steganography), malicious steganography + encryption (key concealment, C2 obfuscation), automation through Python (decrypting config data, deobfuscating strings, extracting payloads), Ghidra API scripting, Dynamic Binary Instrumentation (DBI) frameworks.

**Why it matters as context.** Most submissions will not chase malware reverse-engineering because the wedge in `STRATEGY.md` is hypothesis-first IR, not advanced RE. But the agent will hit malware artifacts (suspicious binaries, packed executables, droppers) and the judges who took FOR710 will read for whether the agent handles them at least credibly (extract IoCs, hash, defer to RE tools, do not freelance "this is APT29 because it looks scary").

---

## B9. The "SANS way" of IR — the six-bullet doctrine students absorb

Across FOR500 / FOR508 / FOR526 / FOR572 / FOR578, the consistent doctrine students absorb:

1. **Hypothesis-driven investigation.** Start with a question ("did this user exfiltrate data?"; "did this host get compromised at 03:14?"; "is this beaconing C2?"); work the artifacts to answer it. Do not boil the ocean.

2. **Multi-artifact corroboration.** Never trust a single source. Cross-reference Registry + EVTX + filesystem + memory + network. A finding that rests on one artifact is fragile under cross-examination.

3. **Timeline-as-spine.** The super-timeline (plaso, mactime, KAPE) is the central organizing structure of every investigation. Findings are ordered events on a shared timeline. Anomalies in the timeline are the leads.

4. **Known-good baseline subtraction.** Identify what is normal on this OS/build/role; then look at what is not normal. Hayabusa with 3,700+ Sigma rules is the modern operationalization; in older parlance, "what's NOT normal here, not what's noisy."

5. **Threat-intel framing.** Map findings to MITRE ATT&CK techniques. Frame the campaign against known threat actor TTPs when the fit is clean. Diamond Model and Kill Chain are working vocabulary.

6. **Defensible findings.** Every claim traces to a specific artifact, at a specific timestamp, via a specific tool execution. Confidence is explicitly stated. Inference is distinguished from observation.

**These six bullets are the implicit rubric.** An agent that visibly executes this loop reads as SANS-shaped to every judge on the panel who has authored or taken a SANS DFIR course. None of this prescribes architecture. It prescribes nothing. It documents what is true about how SANS-trained analysts think, so that the design phase can decide which behaviors to surface explicitly.

---

# Part C — Legal Landscape for AI-Generated Forensic Evidence

This part describes the legal landscape governing AI-generated forensic evidence in US federal court (primary), US state courts (secondary), and EU regulation (tertiary).

**Reminder of scope.** This is descriptive. Whether the submission is framed as court-admissible is a separate decision documented in `STRATEGY.md`. Rob T. Lee's *Protocol SIFT* is **explicitly disclaimed** as "not validated for forensic soundness or evidentiary reliability" and "not intended for evidentiary use in legal proceedings." Several judges (Ovie Carroll, Cheri Carr, Amanda Rankhorn, John Wilson) carry expert-witness lenses by reflex. Knowing what the law requires is useful even if the pitch deliberately avoids the vocabulary.

---

## C1. Federal Rules of Evidence — Article VII (Opinions and Expert Testimony)

The federal evidentiary framework for expert testimony lives in **FRE Article VII (Rules 701–706)**. The two most-cited rules for forensic experts are 702 and 703.

**FRE 701 — Opinion Testimony by Lay Witnesses.** Lay witnesses can give opinions only if rationally based on perception, helpful to the trier of fact, and *not* based on specialized knowledge.

**FRE 702 — Testimony by Expert Witnesses.** The keystone rule for expert testimony, materially amended December 1, 2023 (see C2 below).

**FRE 703 — Bases of an Expert's Opinion Testimony.** Experts may rely on facts/data they were made aware of or "personally observed."

**FRE 704 — Opinion on an Ultimate Issue.** Expert opinions are not objectionable simply because they embrace the ultimate question (with carveouts for mental state in criminal cases).

**FRE 705 — Disclosing the Facts or Data Underlying an Expert's Opinion.** The expert may give opinion without first disclosing underlying data, but may be required to disclose on cross.

**FRE 706 — Court-Appointed Expert Witnesses.** Procedure for the court to appoint its own experts.

**FRE 707 — Machine-Generated Evidence.** *New* — see C4 below.

---

## C2. FRE 702 + The Daubert Standard (with the 2023 amendment)

**The Daubert standard.** From *Daubert v. Merrell Dow Pharmaceuticals*, 509 U.S. 579 (1993). The Supreme Court replaced the older "general acceptance" Frye standard at the federal level with a multi-factor reliability inquiry that the trial court must conduct as the *gatekeeper* of expert testimony.

**The Daubert factors** (non-exclusive, not all required):

1. **Whether the theory or technique can be (and has been) tested** — falsifiability.
2. **Whether the theory or technique has been subjected to peer review and publication.**
3. **Known or potential error rate** of the technique.
4. **Existence and maintenance of standards** controlling the technique's operation.
5. **Whether the theory or technique enjoys general acceptance** in the relevant scientific community.

*Daubert* itself emphasized that these factors are **neither exclusive nor dispositive** and that not all of them can apply to every type of expert testimony. ([Cornell LII, FRE 702](https://www.law.cornell.edu/rules/fre/rule_702))

**The 2023 amendment to FRE 702** — effective **December 1, 2023.** The amended rule reads (paraphrased; full text via Cornell LII):

> A witness who is qualified as an expert by knowledge, skill, experience, training, or education may testify in the form of an opinion or otherwise if **the proponent demonstrates to the court that it is more likely than not** that:
>
> (a) the expert's scientific, technical, or other specialized knowledge will help the trier of fact;
> (b) the testimony is based on sufficient facts or data;
> (c) the testimony is the product of reliable principles and methods; and
> (d) **the expert's opinion reflects a reliable application of the principles and methods to the facts of the case.**

The 2023 amendment did two material things:

- Made the **preponderance of the evidence** standard explicit ("more likely than not"). Earlier case law had let many courts admit expert testimony too liberally; the Advisory Committee pushed back.
- Clarified the gatekeeping responsibility for the **application** of the principles, not just the principles themselves. The expert must show no "analytical gaps" between data and opinion. ([Don't Say Daubert](https://dontsaydaubert.com/recent-applications-of-fre-702/), [McManis Faulkner law-firm summary](https://www.mcmanislaw.com/blog/2024/the-new-daubert-standard-implications-of-amended-fre-702/))

**Why this matters for AI forensic evidence.** Under 2023-amended FRE 702, the proponent of AI-generated forensic opinion must show:

- The AI tool's underlying principles and methods are reliable.
- The application of those principles to *this specific case* is reliable (no analytical gaps).
- The conclusion is based on sufficient facts or data.
- Reliability is established by preponderance of the evidence.

The structural-versus-prompt-only-constraint debate in the hackathon maps directly to this: an architectural constraint with documented behavior is more defensible than "the LLM was told to be careful."

---

## C3. The Frye Standard — Still Live in Some State Courts

**Frye v. United States**, 293 F. 1013 (D.C. Cir. 1923). The original standard for scientific evidence in US courts. Required that scientific methods be **"generally accepted"** in the relevant scientific community to be admissible.

**Frye still operating in some state courts.** California, Illinois, Minnesota, New York, Pennsylvania, Washington are commonly listed. Other states have moved to Daubert or a hybrid. ([Frye standard, Wikipedia](https://en.wikipedia.org/wiki/Frye_standard), [Cornell LII Wex on Frye](https://www.law.cornell.edu/wex/frye_standard))

**Why it matters for AI evidence.** The Frye "general acceptance" inquiry is materially harder for novel AI systems — there *is* no settled general acceptance for LLM-driven forensic analysis. State courts following Frye are likely more skeptical of AI-derived findings than federal courts under Daubert (which permits a broader reliability inquiry).

A 2024 Washington case (**Washington v. Puloka**, see C11) excluded AI-enhanced video evidence in part under Frye on the grounds that AI enhancement is not yet generally accepted in the field.

---

## C4. FRE 707 — Machine-Generated Evidence (the new rule)

**Status as of June 2026.** **Proposed**, having moved through the Advisory Committee → Standing Committee → public comment phases. The originally cited "December 1, 2024 effective date" in the prompt for this document appears to be **slightly ahead of where the rule actually is.** Tracking back:

- The Advisory Committee on Evidence Rules released **proposed Rule 707** for public comment in August 2025.
- Public comment period closed **February 16, 2026.**
- The Advisory Committee is reviewing comments and providing a final report in **June 2026.** ([Iowa Lawyer Magazine](https://www.iowabar.org/?pg=IowaLawyerMagazine&pubAction=viewIssue&pubIssueID=62363&pubIssueItemID=408831), [Univ. of Illinois Chicago Law Library](https://library.law.uic.edu/news-stories/proposed-new-fre-707/), [Barnes & Thornburg](https://btlaw.com/en/insights/alerts/2025/new-evidence-rule-707-would-set-standards-for-ai-generated-courtroom-evidence))

Standard Federal Rules timeline: assuming the Advisory Committee reports in June 2026, the rule still must go through the Judicial Conference (typically September), the Supreme Court (by May 1 of the following year for adoption), and Congress (six-month review). **Earliest likely effective date for FRE 707 is December 1, 2026, possibly 2027.** The "December 1, 2024" date some legal commentary attaches refers to the *earlier 2023 amendment of FRE 702*, not 707.

**What FRE 707 (as proposed) actually says.**

Paraphrased text (from Advisory Committee release):

> When machine-generated evidence is offered without an expert witness and would be subject to Rule 702 if testified to by a witness, the court may admit the evidence only if it satisfies the requirements of Rule 702(a)–(d). This rule does not apply to the output of simple scientific instruments.

The Advisory Committee Note (key excerpt):

> When a machine draws inferences and makes predictions, there are concerns about the reliability of that process, akin to the reliability concerns about expert witnesses.

**Plain-English summary.** Rule 707 extends the FRE 702 reliability gatekeeping standard to machine-generated evidence offered without a sponsoring expert. The same four-prong reliability test applies — sufficient data, reliable methods, reliable application to the case, preponderance burden — but the proponent of *machine-generated* output must demonstrate it directly to the court rather than through an expert. **Simple scientific instruments** (blood-alcohol meters, radar guns, traditional digital photography) are excluded.

**Implicit scope question.** A central debate during the public comment period was: when is something "machine-generated" enough to invoke Rule 707? Output of a calculator is not. Output of an LLM with millions of parameters drawing inferences is. The gray zone — feature-engineered ML, computer vision, deterministic forensic tools that have ML components — is unsettled. The American Association for Justice (AAJ) submitted detailed comment on definitions. ([AAJ comment](https://www.justice.org/-/media/federal-rules/2026-02-16-aaj-comment--fre-707.pdf))

**When does it apply.** Whenever AI-generated material is offered as substantive evidence without a sponsoring testifying expert — for example, AI-summarized incident reports filed as evidence, AI-generated images for demonstrative purposes, AI-derived expert-like conclusions in a declaration.

**Burden it imposes.** The proponent must show by preponderance:

- The AI tool used sufficient facts/data.
- The AI tool's principles and methods are reliable.
- Those principles and methods were reliably applied to this case's facts.

In practice, this likely requires:

- Documentation of training data, model architecture, error rates, peer review where available.
- A reproducible chain — input + parameters + version + output.
- Some form of explainability or audit trail.

**Early cases citing/anticipating 707.** Because the rule is not yet effective, no federal cases *cite* it; but several recent cases anticipate its reasoning, and parties have begun using Rule 707 in motions in limine and Daubert challenges:

- **Kohls v. Ellison** (2024, Minnesota district court) — challenge to Minnesota deepfake law. Defendant's AI expert cited AI-generated case citations that did not exist; plaintiffs moved to exclude under Daubert and Rule 702. The court treated the hallucinated citations as fatal to the expert's reliability. ([Dechert Re:Torts blog](https://www.dechert.com/knowledge/re-torts/2024/12/ai-expert-challenged-for-relying-on-ai--hallucinations-.html))
- **Washington v. Puloka** (2024, King County Superior Court) — triple-homicide shooting case. Defense expert offered AI-enhanced video. Court excluded the enhanced video and the expert testimony under the Frye general-acceptance standard. ([Justice Speakers Institute summary](https://justicespeakersinstitute.com/ai-generated-evidence-admissibility-on-trial/))
- **Ferlito v. Harbor Freight Tools USA** (E.D.N.Y., April 2025) — expert used ChatGPT to confirm conclusions *after* drafting his report; motion to exclude was **denied** because the AI use was post-hoc confirmation, not foundational. ([Greenberg Traurig](https://www.gtlaw.com/en/insights/2025/12/expert-testimony-in-the-age-of-generative-ai-recent-case-developments))
- **Discovery order requiring expert to disclose AI prompts** (May 2026, employment law) — Connecticut court ordered an expert to disclose the AI prompts they used in forming opinions, creating an early discovery precedent. ([CT Employment Law Blog](https://www.ctemploymentlawblog.com/2026/05/articles/court-orders-expert-to-hand-over-ai-prompts-a-discovery-first-employers-cant-ignore/))

**Pattern of opposing-counsel challenges.** Across these cases, the cross-examination pattern that has worked:

1. "Did the AI invent any citations or facts?" (hallucination probe)
2. "Can you reproduce this output deterministically?" (reproducibility probe)
3. "What prompts did you give the AI?" (prompt-discovery probe)
4. "Is the underlying AI technique generally accepted in the forensic community?" (Frye/Daubert probe)
5. "Was a human expert capable of reaching the same conclusion without the AI?" (substitution probe)

---

## C5. State Variations

Beyond Frye versus Daubert, individual states have begun proposing state-level AI evidence rules tracking FRE 707. As of mid-2026:

- **California**: Frye-state historically (Kelly/Frye standard). California's Evidence Code §§801–802 govern expert testimony. The state has been discussing AI evidence rules at the Judicial Council level but no analog to 707 yet adopted.
- **New York**: Frye-state. NY Evidence §452.10 / CPLR 4515. The First Department has been active on social-media authentication; AI evidence is unsettled.
- **Texas**: Daubert-state via *E.I. du Pont de Nemours v. Robinson*. Texas Rule 702 mirrors federal. Cheri Carr (judge A4) testifies in Texas state and federal court.
- **Illinois, Minnesota, Pennsylvania, Washington**: Frye-states with active 2024–2026 case law on AI evidence (see Puloka, Kohls).
- **Florida, New Jersey**: Adopted Daubert in recent years; less unsettled AI doctrine.

A state-by-state compendium of evidence standards is maintained by the National Center for Judicial Information ([NCJI compendium PDF](https://ncji.org/wp-content/uploads/2024/01/Evidence-Standards-by-State-7.12.23.pdf)) and updated periodically. The Forensis Group maintains a more recent practitioner-oriented Daubert vs. Frye guide. ([Daubert vs Frye 2025](https://www.forensisgroup.com/resources/expert-legal-witness-blog/daubert-vs-frye-a-state-by-state-guide-for-expert-witness-admissibility-in-2025))

---

## C6. Chain-of-Custody Requirements

Chain of custody is the documented history of evidence from collection through disposition. Failure to maintain chain breaks admissibility under most evidence regimes.

**Core requirements (consensus across NIST SP 800-86, FBI guidance, and SANS curriculum):**

- **Hash verification.** Cryptographic hash (SHA-256 minimum, often SHA-1 for backwards compat) computed at acquisition. Stored. Re-verified at each handoff. Documented.
- **Write-blocking.** Original evidence acquired via write-blocker (hardware or software) preventing inadvertent modification.
- **Documented custody log.** Every individual who touches the evidence, what they did, when, with what tool, at what hash. Tampering or gaps invite exclusion.
- **Storage standards.** Evidence stored in tamper-evident containers (physical) or controlled access systems (digital), with custody log entries on every access.
- **Tool versioning and validation.** The forensic tools used to acquire, parse, and analyze must be documented by name + version. Toolmark validation (e.g., NIST CFTT — Computer Forensics Tool Testing program) is the gold standard for tool acceptance.

**NIST SP 800-86** ([NIST publication](https://csrc.nist.gov/pubs/sp/800/86/final)) — "Guide to Integrating Forensic Techniques into Incident Response." Foundational document. Key quote:

> Digital forensics is generally considered the application of science to the identification, collection, examination, and analysis of data while preserving the integrity of the information and maintaining a strict chain of custody for the data.

NIST 800-86 frames forensics from an IT view (not strictly law-enforcement view), but its chain-of-custody guidance is the most-cited baseline in court.

**Where AI agents create chain-of-custody questions.**

- Did the agent modify any input artifact? (Write-blocking analog.)
- Are the agent's tool calls themselves logged with timestamps, hashes of inputs, and outputs?
- If a finding is generated, can you reproduce the run with the same inputs and get the same finding?
- Was the agent's prompt and configuration version-controlled?

The Valhuntir-style approach (HMAC-signed audit trail, deterministic document IDs, JSONL log per tool call) is one engineering answer. There are others. Whether to take this approach is an architecture decision.

---

## C7. The Best Evidence Rule (FRE 1001–1008)

**FRE 1002 — Requirement of the Original.**

> An original writing, recording, or photograph is required in order to prove its content unless these rules or a federal statute provides otherwise.

**FRE 1001 — Definitions.** Critically for digital evidence:

> If data are stored by computer or similar device, any printout or other output readable by sight, shown to reflect the data accurately, is an original.

This 1001 carve-out is what makes digital forensic images admissible. The forensic image **is** the original under FRE 1001. ([Cornell LII Rule 1001](https://www.law.cornell.edu/rules/fre/rule_1001), [Cornell LII Rule 1002](https://www.law.cornell.edu/rules/fre/rule_1002))

**FRE 1003 — Admissibility of Duplicates.** Duplicates admissible unless authenticity is genuinely questioned.

**Why this matters for AI forensic output.** AI-generated *summaries* of evidence may not be "originals" in the FRE 1001 sense — they may be derivative interpretations subject to a higher authentication burden. AI-generated *findings* extracted from evidence are particularly tricky: are they reflecting the data accurately, or reflecting the model's interpretation of the data?

The cleanest defensive shape: keep the AI output and the underlying tool output separate, both available, with the AI output traceable back to specific tool executions on specific verified-hash evidence.

---

## C8. Hearsay Considerations (FRE 801–807)

**FRE 801 — Definition of hearsay.** Out-of-court statement offered for the truth of the matter asserted.

**Why machine output is sometimes not hearsay.** Data generated purely by a computer or sensor without a human assertion is generally **not hearsay** because it lacks a declarant making an assertion. GPS logs, sensor readings, automatic log files, packet captures — these are often admitted as non-hearsay machine output.

**FRE 803(6) — Business Records Exception (the workhorse).**

Most digital forensic evidence is admitted under the business records exception. Server logs, audit trails, transactional databases — these are records of regularly conducted business activity, kept in the regular course of business, made at or near the time by someone with knowledge.

**Where AI output gets tricky.** AI-generated findings *do* involve an assertion ("the system was compromised at 03:14") — that assertion is being offered for its truth. If a human expert generated it, FRE 702/703 applies. If a machine generated it without a sponsoring expert, FRE 707 may apply. If it is offered as a business record (e.g., an automated IR ticket the agent created), it may qualify under 803(6) — but the foundation requires showing the AI's process is reliable and routine.

---

## C9. Expert Witness Qualification (FRE 702, voir dire)

Before an expert testifies, the court conducts **voir dire** of the witness — counsel and the court probe the witness's qualifications, methodology, and conclusions. Under amended FRE 702 (2023), the proponent must demonstrate by preponderance that each prong of 702 is satisfied.

**Voir dire pattern for AI-assisted forensic analysts (2024–2026 emerging pattern).**

- Education and certifications.
- Tools used and their validation status.
- AI tools used, prompts given, parameters, versions.
- Whether the conclusions would be the same without AI assistance (substitution test).
- Whether the AI's output was independently verified.
- Whether any AI output was used directly without expert verification.

Several recent cases (Ferlito, the CT employment case) suggest the **safest expert practice** is AI as *confirmation* of an expert's independently-reached conclusion, not as the source of the conclusion. This maps to the Rob T. Lee framing of "augment, never replace."

---

## C10. AI Evidence in Civil Discovery — TAR Precedent

Technology-Assisted Review (TAR) for e-discovery has been the laboratory in which courts have made peace with machine-driven document review:

- **Da Silva Moore v. Publicis Groupe** (S.D.N.Y. 2012) — Judge Andrew Peck's foundational TAR opinion.
- **Rio Tinto v. Vale** (S.D.N.Y. 2015) — clarified that TAR validation can be by sampling, not full review.
- **Hyles v. New York City** (S.D.N.Y. 2016) — TAR cannot be compelled, but its use is approved.

**TAR precedent extends to LLM-generated findings (current direction).** The Sedona Conference Working Group 1 published "TAR Reference Model: Unifying Traditional and GenAI Approaches to Technology-Assisted Review" (2024) — framing GenAI and TAR as complementary, not conflicting. The judicial framework that emerged from TAR (proportionality, defensibility, sampling for validation) is being applied by analogy to GenAI findings in discovery. ([Sedona Conference publications](https://www.thesedonaconference.org/publications), [TAR Reference Model](https://www.thesedonaconference.org/publication/TAR_Reference_Model_Unifying_Traditional_and_GenAI_Approaches))

The Sedona Conference also published "Judges and AI: A Framework for Responsible Use" — a framework specifically for judicial officers using AI tools in chambers. ([ComplexDiscovery summary](https://complexdiscovery.com/judges-and-ai-the-sedona-conference-publishes-a-framework-for-responsible-use/))

---

## C11. Notable Early AI Evidence Cases (2024–2026)

A consolidated case list, with the operative lessons.

**Washington v. Puloka** (2024, Wash. King County Sup. Ct.) — triple-homicide shooting. Defense's video forensic expert used AI to enhance a recording. The court excluded both the enhanced video and the expert testimony under the Frye general-acceptance standard. **Lesson: under Frye, AI-enhanced evidence requires showing general acceptance, which most AI methods cannot yet claim.**

**Kohls v. Ellison** (D. Minn. 2024) — challenge to Minnesota's anti-deepfake law. Defendant's AI expert submitted a declaration citing AI-hallucinated case citations that did not exist. Plaintiffs moved to exclude under Daubert/Rule 702. **Lesson: hallucinated citations are fatal. The reliability prong fails immediately.**

**Ferlito v. Harbor Freight Tools USA** (E.D.N.Y. April 2025) — products liability. Expert used ChatGPT to *confirm* his conclusions after authoring his report. Motion to exclude denied. **Lesson: AI as post-hoc confirmation of an independently-reached expert conclusion is defensible. AI as the source of the conclusion is not.**

**(Connecticut employment matter)** (May 2026) — court ordered expert to hand over the AI prompts used in forming opinions. **Lesson: AI prompts are discoverable. Treat your prompts as you would your notes — they will be subpoenaed.**

**Pattern across cases.**

- Courts are not categorically hostile to AI evidence; they are hostile to **unverified** AI evidence.
- The most-cited reliability-defeating findings are: hallucination, non-reproducibility, lack of expert oversight, and lack of audit trail.
- AI used *under* a qualified expert who would have reached the same conclusion is robust.
- AI used *as* the expert is fragile.

---

## C12. EU Framework — GDPR + AI Act

**GDPR Article 22 — Automated decision-making and profiling.** ([Legiscope analysis](https://www.legiscope.com/blog/gdpr-article-22-automated-decision-making.html))

> The data subject shall have the right not to be subject to a decision based solely on automated processing, including profiling, which produces legal effects concerning him or her or similarly significantly affects him or her.

Three exceptions: contract performance, legal authorization, explicit consent. Even within the exceptions, the data subject must have:

- Right to human intervention.
- Right to express their viewpoint.
- Right to contest the decision.
- Right to an explanation (debated extent).

**Application to forensic investigations.** Forensic investigations on personal data fall within GDPR scope when the data subject is identified or identifiable. Article 22 implicates AI agents that make findings about specific individuals (insider-threat investigations, BEC attribution, employee misconduct reviews).

**EU AI Act (Regulation 2024/1689).** Effective phased starting 2024, fully applicable 2026–2027.

- **High-risk AI systems** (Annex III) include systems for law enforcement, justice administration, biometric identification, employment decisions. AI agents performing forensic investigations supporting employment terminations or law enforcement referrals likely fall under high-risk classification.
- **High-risk requirements**: risk management system, data governance, technical documentation, record-keeping, transparency, human oversight, accuracy/robustness/cybersecurity, conformity assessment.
- **Cumulative with GDPR Article 22.** A high-risk AI system making decisions about individuals must satisfy both regimes.

([Cyera EU AI Act + GDPR overview](https://www.cyera.com/blog/from-gdpr-to-ai-act-the-evolution-of-data-and-ai-security-in-the-eu), [IAPP mapping](https://iapp.org/resources/article/mapping-interplays-gdpr-eu-ai-act))

**Why this matters for European judges (Maximilian Gutowski, Mathieu Alcaina, Pedro Jimenez, Sneha Parmar).** They operate under cumulative GDPR + AI Act constraint. An agent that ignores European data-handling discipline reads as US-centric.

---

## C13. Sector-Specific Overlays

Forensic engagements often cross sector-regulated domains:

- **HIPAA / HITECH** (US health). Protected Health Information (PHI) found on a compromised host triggers breach notification timelines (60 days). The forensic engagement must distinguish "PHI was on this host" from "PHI was accessed." AI-generated findings about PHI access have higher stakes.
- **GLBA** (US financial). Customer financial info has its own discipline.
- **PCI-DSS** (payment cards). Cheri Carr's Herff Jones declaration is a direct example. Forensic engagements that determine the cardholder data scope of a breach drive enormous downstream cost. AI imprecision here is expensive.
- **SOX** (US public-company financial reporting). Internal controls cases.
- **CCPA / CPRA** (California). Notification, data subject rights.
- **SEC cyber-incident disclosure rule** (2023). 8-K filing within four business days of materiality determination. Forensic findings drive timing.

The point for this brief: **forensic findings in regulated industries have audit consequences that flow downstream from the AI agent's output.** Submission writers might or might not address this; either way, the panel includes people (John Wilson at HaystackID, Sneha Parmar at Deutsche Bank, Steve Cobb at SecurityScorecard) who carry this lens by reflex.

---

## C14. Stipulations vs. Contested Evidence

In practice, a great deal of digital forensic evidence is admitted by **stipulation** — the parties agree it comes in. The full Daubert/Frye gauntlet is run only when one side genuinely contests the evidence.

This matters because the cost of producing court-defensible AI output is substantial, but stipulation often makes it unnecessary. The investigator's day-to-day job is producing findings credible enough that opposing counsel will stipulate. Findings that opposing counsel *will* contest get the full Daubert workout.

**Inference for an AI investigator's output design.** If the output is sufficiently transparent and reproducible that opposing counsel is unlikely to contest it, the cost of contested-evidence-grade output is moot. If the output reads as a black box, opposing counsel has every incentive to contest, and the full Daubert burden materializes.

---

## C15. The "Black Box" Problem and Explainability

Several recent court opinions reject AI output on **explainability grounds**:

- The court cannot meaningfully evaluate reliability if the model's reasoning is opaque.
- The defense cannot meaningfully cross-examine an opaque output.
- The trier of fact cannot give the output proper weight.

This is a particularly acute concern in **criminal proceedings**, where Brady obligations and the Confrontation Clause apply. State v. Pickett (NJ, 2019) and the Picaud line of cases have shaped how courts handle proprietary algorithmic outputs in criminal contexts. ([Reliability and Admissibility of AI-Generated Forensic Evidence in Criminal Trials, arXiv 2601.06048](https://arxiv.org/pdf/2601.06048))

The recent FRE 707 advisory committee work explicitly notes the explainability concern. Audit trails, deterministic re-runs, and reproducible chains are the practical mitigations.

---

## C16. Audit Trail Requirements (as anticipated by FRE 707 framework)

Synthesizing the FRE 707 framework + Brian Carrier's (Cyber Triage) public AI principles + the Sedona Conference guidance, a workable audit-trail framework for defensible AI forensic output includes:

- **Hash-verified inputs.** Inputs (forensic images, log bundles, captured artifacts) are identified by SHA-256 (or stronger) hash. The AI's input set is documented.
- **Versioned configuration.** The AI model version, prompt version, parameters, and tool configurations are pinned and recorded.
- **Deterministic re-run capability.** Given the same inputs, configuration, and prompts, the same output should be reachable (within stated bounds for non-deterministic models).
- **Tool execution log.** Every tool call is logged with timestamp, inputs, outputs, exit code, and (ideally) the rationale for invocation.
- **Finding-to-tool-call traceability.** Each finding ties to specific tool executions that produced its evidence.
- **Confidence and uncertainty disclosure.** Findings carry confidence labels; what could not be determined is also documented.
- **Reviewer log.** Human review and approval steps are recorded.

**Brian Carrier (Sleuth Kit Labs / Cyber Triage)** has been publishing on this exact question. ([Cyber Triage blog on AI principles](https://www.cybertriage.com/blog/ai-principles-for-digital-forensics-and-investigations-dfir/), [Sleuth Kit Labs contributor page](https://www.cybertriage.com/contributor/dr-brian-carrier/)) His framing: AI can automate intermediate steps in investigations but still requires skilled investigators to ask the right questions and understand context. Sleuth Kit Labs aligns its AI principles with the OECD AI Principles and internationally recognized standards. He maintains the position that **LLMs are promising and risky** — enabling novel interaction with data, but introducing errors.

---

## Selected reading list (for downstream agents who want primary sources)

**Federal Rules of Evidence (live text).** Cornell LII:
- [FRE 702](https://www.law.cornell.edu/rules/fre/rule_702)
- [FRE 703](https://www.law.cornell.edu/rules/fre/rule_703)
- [FRE 1001](https://www.law.cornell.edu/rules/fre/rule_1001)
- [FRE 1002](https://www.law.cornell.edu/rules/fre/rule_1002)
- [FRE 803 — hearsay exceptions](https://www.law.cornell.edu/rules/fre/rule_803)

**FRE 707 work.**
- [Advisory Committee Hearing Packet (Jan 15)](https://www.uscourts.gov/sites/default/files/document/jan-15-hearing-schedule-and-testimony-packet-final.pdf)
- [AAJ public comment, Feb 2026](https://www.justice.org/-/media/federal-rules/2026-02-16-aaj-comment--fre-707.pdf)
- [University of Illinois Chicago Law Library FAQ on 707](https://library.law.uic.edu/news-stories/proposed-new-fre-707/)
- [Barnes & Thornburg analysis](https://btlaw.com/en/insights/alerts/2025/new-evidence-rule-707-would-set-standards-for-ai-generated-courtroom-evidence)

**Daubert + 2023 FRE 702 amendment.**
- [Harvard Law Review on FRE 702](https://harvardlawreview.org/print/vol-138/federal-rule-of-evidence-702/)
- [Federalist Society on the 2023 amendments](https://fedsoc.org/commentary/fedsoc-blog/a-brief-guide-to-the-2023-amendments-to-the-federal-rules-of-evidence-1)
- [McManis Faulkner — Implications of Amended FRE 702](https://www.mcmanislaw.com/blog/2024/the-new-daubert-standard-implications-of-amended-fre-702/)

**Frye.**
- [Cornell LII Wex on Frye](https://www.law.cornell.edu/wex/frye_standard)
- [State-by-State Daubert/Frye guide 2025](https://www.forensisgroup.com/resources/expert-legal-witness-blog/daubert-vs-frye-a-state-by-state-guide-for-expert-witness-admissibility-in-2025)

**Forensic standards.**
- [NIST SP 800-86 final](https://csrc.nist.gov/pubs/sp/800/86/final)
- [NIST SP 800-86 PDF](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-86.pdf)

**Sedona Conference work.**
- [Sedona Conference AI activities](https://www.thesedonaconference.org/node/10432)
- [TAR Reference Model](https://www.thesedonaconference.org/publication/TAR_Reference_Model_Unifying_Traditional_and_GenAI_Approaches)

**Practitioner / vendor commentary on AI + forensics.**
- [Cyber Triage AI principles](https://www.cybertriage.com/blog/ai-principles-for-digital-forensics-and-investigations-dfir/)
- [Maryland State Bar on Daubert and Frye for AI](https://www.msba.org/site/site/content/News-and-Publications/News/General-News/Applying_Daubert_and_Frye_to_AI_Evidence.aspx)
- [Quinn Emanuel — Adapting Rules of Evidence for AI](https://www.quinnemanuel.com/the-firm/publications/adapting-the-rules-of-evidence-for-the-age-of-ai/)

**Early AI evidence case law.**
- [Greenberg Traurig — recent case developments](https://www.gtlaw.com/en/insights/2025/12/expert-testimony-in-the-age-of-generative-ai-recent-case-developments)
- [Dechert Re:Torts on AI hallucinations](https://www.dechert.com/knowledge/re-torts/2024/12/ai-expert-challenged-for-relying-on-ai--hallucinations-.html)
- [Justice Speakers Institute on AI evidence admissibility](https://justicespeakersinstitute.com/ai-generated-evidence-admissibility-on-trial/)
- [CT Employment Law Blog — court orders disclosure of AI prompts](https://www.ctemploymentlawblog.com/2026/05/articles/court-orders-expert-to-hand-over-ai-prompts-a-discovery-first-employers-cant-ignore/)
- [arXiv 2601.06048 — Reliability and Admissibility of AI-Generated Forensic Evidence](https://arxiv.org/pdf/2601.06048)

**EU framework.**
- [Cyera — GDPR to AI Act](https://www.cyera.com/blog/from-gdpr-to-ai-act-the-evolution-of-data-and-ai-security-in-the-eu)
- [IAPP — Mapping interplays GDPR + AI Act](https://iapp.org/resources/article/mapping-interplays-gdpr-eu-ai-act)
- [Legiscope — GDPR Article 22](https://www.legiscope.com/blog/gdpr-article-22-automated-decision-making.html)

**SANS curriculum.**
- [FOR500 — Windows Forensic Analysis](https://www.sans.org/cyber-security-courses/windows-forensic-analysis)
- [FOR508 — Advanced IR, Threat Hunting, Digital Forensics](https://www.sans.org/cyber-security-courses/advanced-incident-response-threat-hunting-training) | [FOR508 2026 brochure PDF](https://assets.contentstack.io/v3/assets/bltabe50a4554f8e97f/blt125a614cea7e0087/69f23582207e69ba2e3c4bb4/SANS_Institute_FOR508_Brochure_042926.pdf)
- [FOR509 — Enterprise Cloud Forensics](https://www.sans.org/cyber-security-courses/enterprise-cloud-forensics-incident-response)
- [FOR526 — Memory Forensics In-Depth](https://www.sans.org/course/memory-forensics-in-depth)
- [FOR572 — Advanced Network Forensics](https://www.sans.org/cyber-security-courses/advanced-network-forensics-threat-hunting-incident-response)
- [FOR578 — Cyber Threat Intelligence](https://www.sans.org/cyber-security-courses/cyber-threat-intelligence)
- [FOR710 — Reverse-Engineering Malware: Advanced Code Analysis](https://www.sans.org/cyber-security-courses/reverse-engineering-malware-advanced-code-analysis)

**Judge primary sources (selected).**
- [Rob T. Lee Substack](https://robtlee73.substack.com/)
- [Rob T. Lee SANS profile](https://www.sans.org/profiles/rob-lee)
- [Ovie Carroll personal site](https://ovie.coffee/)
- [Ovie Carroll — Challenges in Modern Digital Investigative Analysis](https://ovie.coffee/about-me/f/challenges-in-modern-digital-investigative-analysis)
- [Steve Anson SANS profile](https://www.sans.org/profiles/steve-anson)
- [Applied IR / Steve Anson bio](https://www.appliedincidentresponse.com/about-applied-incident-response-and-steve-anson/)
- [Valhuntir on GitHub](https://github.com/AppliedIR/Valhuntir)
- [Cheri Carr JurisPro CV](https://www.jurispro.com/expert/cheri-carr-10174/cv)
- [Aspen Forensics](https://aspenforensics.com/)
- [Steve Cobb — SecurityScorecard leadership](https://securityscorecard.com/people/leadership/steve-cobb/)
- [Steve Cobb LinkedIn](https://www.linkedin.com/in/wscobb/)
- [Jens Ernstberger personal site](https://ernstberger.xyz/)
- [Jens Ernstberger — Contextual Authorization for AI Agents](https://ernstberger.xyz/posts/04_contextualauth/)
- [Kontext Security](https://kontext.security/)
- [Yotam Perkal SANS profile](https://www.sans.org/profiles/yotam-perkal)
- [Pluto Security MCPwn writeup](https://pluto.security/blog/mcp-bug-nginx-security-vulnerability-cvss-9-8/)
- [Pluto Security — Inside Claude Cowork](https://pluto.security/blog/inside-claude-cowork-how-anthropics-autonomous-agent-actually-works/)
- [HaystackID John Wilson podcast bio](https://haystackid.com/podcast-haystackid-in-the-edrm-illumination-zone-john-wilson-ciso-and-president-and-forensics/)
- [Khushi Gupta Google Scholar](https://scholar.google.com/citations?user=7PA6nPMAAAAJ&hl=en)
- [Preston Fitzgerald SANS profile](https://www.sans.org/profiles/preston-fitzgerald/)
- [Georgios Kapoglis SANS profile](https://www.sans.org/profiles/georgios-kapoglis)
- [Jason Garman — AWS forensic blog](https://aws.amazon.com/blogs/security/forensic-investigation-environment-strategies-in-the-aws-cloud/)

---

# Part D — Cross-Cutting Observations

This part documents three cross-cutting topics that bridge Parts A, B, and C: (D1) what the SANS faculty corpus says about AI for IR, (D2) what the practitioner community says publicly (the discourse the panel reads), and (D3) the working hypothesis-pivot mental model the SANS curriculum implicitly teaches.

---

## D1. SANS faculty published positions on AI for IR (2024–2026)

The SANS instructor community has been publishing on AI for IR with rising volume. Reading across these positions clarifies the in-house worldview the panel inherits.

**The Rob T. Lee position** (covered in detail in A1). Summarized: AI is an *operator*, not a tool; defenders need AI-speed defenders; constraint architecture beats prompt-only guardrails; reduce hallucination, don't claim to eliminate it; the human examiner drives the response; senior-analyst sequencing + self-correction is the target behavior.

**The Robert M. Lee position** (FOR578 author — distinct person from Rob T. Lee). Robert M. Lee runs Dragos (industrial control systems IR) and writes extensively at [robertmlee.org](http://www.robertmlee.org/). His running theme: **CTI is being misused by AI hype**. Threat intelligence is a discipline with stakeholder workflows, models, and tradecraft; LLMs that summarize threat feeds without that discipline produce false confidence. The Diamond Model framework he co-developed remains his primary cross-reference.

**The Steve Anson position** (covered in A9). Summarized: forensic discipline must be enforced at the system layer, not the model layer; humans must cryptographically sign approvals; LLM-agnosticism is a feature (the discipline doesn't depend on the model); the audit trail is the load-bearing artifact.

**The Phil Hagen position (FOR572 lead).** Phil has been quieter on AI publicly, but his SOF-ELK stewardship signals a position: **the right pipeline is the lever, not the model.** Make the underlying data discovery, normalization, and search excellent; AI is a layer on top that benefits from a strong substrate. The Arkime full-packet capture + SOF-ELK stack he maintains is design-philosophy in code.

**The Heather Barnhart position (mobile forensics + FOR500 co-author).** Heather Barnhart's social media + blog posts (`Cellebrite labs`, `SANS DFIR Summit talks`) consistently emphasize **the artifact catalog itself as the moat**. The senior analyst's edge over an LLM is knowing what is *possible* on a Windows 11 / iOS 18 system that is not yet documented anywhere — and how artifacts interact under specific patch levels. AI can know what is documented; the analyst knows the new thing.

**Common ground across SANS faculty.**

- AI is useful, not autonomous.
- The artifact catalog and forensic discipline are not optional.
- The human is the named authority for findings.
- Reproducibility / audit trail / explainability are baseline.
- "Hallucination" is a known failure mode to actively detect, not deny.

---

## D2. Practitioner discourse the panel reads

Beyond the SANS faculty, the wider DFIR practitioner community publishes daily on Twitter/X, Mastodon, BlueSky, Discord, and Reddit. The judges read this; their reading mode is the readers'. A few high-signal venues:

**SANS Internet Storm Center (ISC).** Daily diary; many SANS instructors and senior analysts post case notes and TTPs there.

**DFIR community Discord servers.** The DFIR Diva, MyDFIR, Black Hills InfoSec, and the SANS-affiliated Slack/Discord channels are where practitioners triage their day. The discourse there in 2025–2026 has been increasingly: *AI helps me draft, but I redo the work to be sure; the reporting time savings are real; the analysis time savings are mixed.* Several judges are active in these communities.

**Reddit r/AskNetsec, r/DFIR.** Lower-signal but useful for the breadth of practitioner concerns: licensing, certification paths, tool choice, AI distrust.

**Twitter/X DFIR accounts (Heather Mahalik, Eric Zimmerman, Andrew Rathbun, John Hubbard, SwiftOnSecurity).** Eric Zimmerman in particular maintains the EZ Tools suite that FOR500 students use; his published positions on AI in forensic tools are conservative — he keeps his tools deterministic, explicitly *not* AI-augmented.

**LinkedIn DFIR thought leadership.** Several judges (Steve Cobb, John Wilson, Brett Cumming) publish on LinkedIn. The genre: short executive-readable observations on threat landscape, leadership, and program-building. This is the genre to write *for* if speaking to the CISO axis.

**Mandiant Defender's Advantage podcast + M-Trends report.** The CTI-grounded house style. Adam Nasreldin works inside this culture.

**Pluto Security blog (Yotam Perkal).** The MCP security beat. Anyone shipping a custom MCP server should expect Pluto's eye on the architecture.

**Brian Carrier / Cyber Triage / Sleuth Kit Labs.** Brian's running mini-course on AI in forensics is the most coherent practitioner-side codification of AI principles for DFIR. Worth reading even if not adopting wholesale.

---

## D3. The implicit "hypothesis-pivot" mental model

Across the SANS curriculum (Part B) and the head-judge framing (Rob T. Lee, A1), the implicit mental model the panel will pattern-match against can be stated explicitly:

1. **Observe initial signal.** Alert, ticket, anomalous artifact, intel tip, executive request.
2. **Form initial hypothesis.** What scenario would explain this? Name it. Identify the artifacts that would corroborate it.
3. **Execute targeted tools.** Run the specific tools that produce the corroborating artifacts. Read structured output.
4. **Check corroboration.** Does the evidence support the hypothesis? Are there contradictions?
5. **If contradicted: pivot.** Reformulate the hypothesis. Restart from step 3.
6. **If supported: deepen.** What artifacts would refine the hypothesis (timing, attribution, scope)? Run those tools.
7. **Continuously test.** "Recognize when something doesn't add up." Anomaly detection against the working hypothesis.
8. **Self-correct on tool failure.** If the tool errors, read the error; adjust the call; retry. Do not invent output.
9. **Document each step.** Every claim ties to a tool execution + artifact + timestamp + confidence.
10. **Finalize when corroboration is sufficient.** Write the report. Explicitly state what was *not* determinable.

This is the "senior analyst" loop in operational language. **The SANS curriculum trains this loop across courses.** The Rob T. Lee framing names it. Steve Anson encoded it into Valhuntir's structure. Ovie Carroll's "silent witness" framing is the post-loop reporting discipline.

A submission that executes this loop visibly — with the explicit log lines showing each phase — speaks SANS-shaped DFIR fluently. None of this is prescription; it is a description of the implicit pattern the panel pattern-matches against, derived from the public artifacts cited in Parts A and B.

---

## D4. The volatility plugin family in more depth (because Rob's canonical demo lives here)

Because Rob T. Lee's canonical "self-correction" demo uses Volatility 3 plugin errors (covered in B4), the plugin family is worth knowing in operational detail.

**Volatility 3 plugin families that produce diagnostic-shaped errors.** (Plugin names use Volatility 3 syntax; Volatility 2 differs.)

- **`windows.pslist.PsList`** — walks the doubly-linked active process list. Errors typically: symbol table mismatch ("could not resolve symbol `_EPROCESS`"). Diagnostic action: identify the right Windows version/build; adjust symbol path.
- **`windows.psscan.PsScan`** — scans memory for `_EPROCESS` structures by signature, not by list walk. Detects hidden processes. Errors similar to pslist.
- **`windows.pstree.PsTree`** — process tree visualization. Errors generally tied to pslist failures upstream.
- **`windows.cmdline.CmdLine`** — extracts command-line arguments from each process. Critical for "what did this PowerShell actually run?"
- **`windows.cmdscan.CmdScan` / `windows.consoles.Consoles`** — shell command history. The "what did the attacker type?" plugin.
- **`windows.dlllist.DllList`** — loaded modules per process. Detection of injected DLLs typically uses this + malfind.
- **`windows.malfind.MalFind`** — scans for injected code (RWX, hidden code in non-disk-backed regions).
- **`windows.netscan.NetScan` / `windows.netstat.NetStat`** — network connections. C2 detection.
- **`windows.handles.Handles`** — kernel object handles per process. Reveals named pipes, mutexes, files.
- **`windows.svcscan.SvcScan`** — Windows service enumeration. Persistence detection.
- **`windows.hashdump.Hashdump` / `windows.lsadump.LsaDump`** — credential extraction.
- **`windows.dumpfiles.DumpFiles`** — dump file objects from memory.
- **`windows.registry.printkey.PrintKey`** — registry key enumeration from memory.
- **`windows.bigpools.BigPools`** — large kernel allocations. Rootkit / driver analysis.
- **`windows.driverirp.DriverIrp`** — driver IRP hooks. Rootkit detection.
- **`windows.envars.Envars`** — environment variables. Useful for path/runtime context.

**Common error modes that trigger self-correction loops:**

- **"Could not resolve symbol"** → wrong symbol pack for the OS version. Action: identify build, fetch right symbols.
- **"No valid kernel found"** → wrong layer/profile assumption. Action: re-run `windows.info.Info`.
- **"Plugin requires `--pid`"** → missing required argument. Action: enumerate processes first, then re-run with PID.
- **"Could not parse `_EPROCESS` at offset 0x..."** → corrupted region or wrong structure version. Action: skip the offset, continue with scan-style plugins.

The Volatility self-correction loop maps cleanly onto Rob T. Lee's framing: tool errors are *diagnostic*, not terminal. An agent that demonstrably reads `vol3` stderr, identifies the failure class, and retries with the right adjustment is showing the named behavior the head judge will recognize.

---

## D5. Additional FRE / state-law detail not in C

A few additional legal details worth knowing for the design phase:

**FRE 901 — Authentication.** Before evidence can be admitted, the proponent must produce evidence sufficient to support a finding that the item is what the proponent claims it is. For digital evidence, authentication typically requires:

- Witness with knowledge of the system/data.
- Distinctive characteristics of the data.
- Hash match against the original collection.
- Process or system that produced the output (the "process or system" rationale at 901(b)(9)).

**FRE 901(b)(9)** is particularly relevant to AI output: "Evidence describing a process or system and showing that it produces an accurate result." This is the doorway through which AI tools must walk: demonstrate the process, demonstrate accuracy.

**FRE 902 — Self-Authenticating Evidence.** Some documents do not require external evidence to authenticate (public records, certified business records, etc.). **FRE 902(13) and 902(14)** — added in 2017 — specifically address electronic data:

- **902(13)**: records generated by an electronic process or system, shown to be reliable by a qualified-person certification.
- **902(14)**: electronic data copied from an electronic device, storage medium, or file, shown to be reliable by a certified hash.

These are the explicit authentication doorways for forensic images and tool output. They contemplate human certification of the process or tool.

**State criminal procedure overlays.** Criminal cases have additional layers:

- **Brady v. Maryland** (1963) — prosecution must disclose exculpatory evidence to the defense.
- **Confrontation Clause** (6th Amendment) — defendant's right to confront witnesses against them. Hard interaction with AI output where there is no "witness" to confront.
- **People v. Khalik** patterns — where automated devices produce evidence, the courts examine whether the device's reliability is subject to confrontation through its operator or maintainer.

**Recent state legislation explicitly on AI evidence.** California, Texas, and a handful of other states have proposed or passed laws addressing deepfakes, AI-generated content authentication, and AI disclosure in legal filings. Minnesota's deepfake law was at issue in *Kohls v. Ellison* (C11). The state-by-state position is shifting fast.

---

## D6. The cross-examination playbook against AI-generated forensic findings

For the design-phase agent reading this: this is the standardized opposing-counsel questioning that AI-assisted forensic findings face. Treat it as a quality stress test, not as a design constraint.

1. **"What AI tool produced this finding?"** (foundation)
2. **"What version of that tool? When was it last updated?"** (versioning)
3. **"What prompts did you give the AI tool?"** (CT case precedent — prompts are discoverable)
4. **"Did you verify the AI's output independently?"** (substitution test)
5. **"Are you offering this finding as your expert opinion, or as the AI's opinion?"** (FRE 702 vs FRE 707 channel)
6. **"What error rate does this AI tool have on this type of artifact?"** (Daubert factor 3)
7. **"Has this AI tool been peer reviewed in the forensic community?"** (Daubert factor 2 / Frye general acceptance)
8. **"Can you reproduce this finding deterministically? Show us."** (reliability)
9. **"What inputs did the AI receive? Show us the hash."** (chain of custody)
10. **"Did the AI generate any output you discarded as wrong? Show us."** (selective use — the killer follow-up)
11. **"What did the AI fail to find that a competent analyst would have found?"** (the negative-space probe)
12. **"Did the AI hallucinate at any point during this investigation? If you can't answer that — how do you know?"** (epistemic honesty test)

An agent whose audit trail can answer each of these without flinching is, by construction, defensible. An agent that cannot answer #10, #11, or #12 is at structural risk under cross-examination.

This connects back to Rob T. Lee's epistemic-honesty framing: "know what you couldn't find as much as what you did find," and "Claude doesn't get defensive when you call it out." The legal cross-examination test is a structurally identical pressure.

---

## D7. Provenance markers and the "what is original" question

A subtle Best Evidence Rule issue arises specifically with AI-assisted forensic output: **what is the "original" that FRE 1001 contemplates?**

The chain:

```
forensic image (binary disk dump, hashed)
    ↓ parser
parsed artifact (e.g., MFT entry CSV)
    ↓ tool output
tool finding (e.g., "process X executed at T")
    ↓ AI interpretation
AI finding (e.g., "this matches APT29 TTP")
    ↓ AI report
final report (e.g., "we assess the system was compromised by APT29")
```

Each downward arrow is a transformation. Each transformation introduces a new candidate "original" with its own FRE 1001 status.

- The forensic image: clearly an original under FRE 1001 (output of computer, shown to reflect data accurately).
- The parsed artifact: an original of the *parse*, but for the data itself it is a derivative.
- The tool finding: an interpretive output of the tool, derivative.
- The AI finding: an interpretive output of the AI, doubly derivative.
- The final report: a curated summary, triply derivative.

The cleanest defensive shape is keeping each level distinct, each level inspectable, each level traceable to the level above and below. Valhuntir's response-envelope pattern (audit_id, caveats, advisories, corroboration, discipline_reminder, data_provenance) is one engineering articulation of this; the structural principle is what matters, not the specific implementation.

---

## A final note on what this file is for

This is not a guide to "design for these judges." That would defeat the purpose of the design phase.

This is a description of:

- **Who the judges are** (Part A), so the design phase can decide which reading lenses to address and which to deprioritize.
- **What SANS teaches** (Part B), so the design phase knows what the judges' internal patterns recognize and what they read as senior-analyst vs. junior.
- **What the law requires of AI forensic evidence** (Part C), so the design phase knows what the legal floor looks like even if the wedge deliberately steps around it.

Architecture decisions belong in SPEC.md and the design phase, informed by this knowledge plus the rest of `context/`. The wedge in `STRATEGY.md` does not require court-admissibility — Rob T. Lee explicitly disclaims it — but several judges carry expert-witness lenses by reflex and several specific designs (chain-of-custody hashing, audit-trail-grade reproducibility, observation-vs.-interpretation discipline in the report writer) speak to the substance those judges respect *without* using the "court-admissible" trigger words that contradict the head judge's framing.

That tension — substance without vocabulary — is itself a design problem for the next phase. This file is the briefing book for it.
