# refs/judges — Per-judge profile + predicted preferences

48 judges total. Below is the top tier (those whose worldview matters most) plus structural notes on the rest.

---

## Tier 1: Must-internalize (top 5)

### 1. Rob T. Lee — CAIO & Chief of Research, SANS (THE primary judge)

**Background:**
- Created the SIFT Workstation ~2007. 27 years DFIR.
- Currently Chief AI Officer at SANS.
- Author/co-author of FOR508 (Advanced IR), FOR526 (Memory Forensics).
- Active substack publisher: https://robtlee73.substack.com/
- X: https://x.com/robtlee

**Worldview (verbatim quotes from his recent posts):**

> "Adversaries are operating at machine speed. The answer is not faster humans."

> "Defenders are out here bringing knives to a drone strike."

> "Defensive OODA loops are measured in hours while offensive loops are now measured in seconds."

> **"Teach an AI agent to think like a senior analyst, how to sequence its approach, recognize when something doesn't add up, and self-correct when it gets it wrong."** ← THIS IS THE RUBRIC IN ONE SENTENCE

> "When a Volatility command returns an error, Claude reads the error message, adjusts its hypothesis... and retries." ← The "Ralph Wiggum Loop"

> "Protocol SIFT works. It also hallucinates more than we'd like. (That's exactly why this hackathon exists.)" ← Permission to flag your own hallucinations

> "Only someone who knows DFIR can interpret that output." ← AI augments, doesn't replace

> "I typed two words, 'find evil,' and fourteen minutes twenty-seven seconds later had a complete C drive analysis." ← The time-to-finding anchor

> "The architecture they used [in GTG-1002] — an agentic AI connected to offensive tools via MCP — is the exact same architecture I'd been building for defense." ← Same shape, different polarity

> "Yes, that's the actual reason it's 47 and not 48. I wish I had a more rigorous justification. I don't." ← Rewards honesty over vendor polish

**Will reward:**
1. Architectural constraints > prompt-based ones
2. Explicit hallucination handling — flag your own
3. Court-admissibility chain-of-custody
4. Speed measured as time-to-findings (< 15 min on full C-drive)
5. "Senior analyst sequencing" + Ralph Wiggum Loop demo

**Will penalize:**
1. AI replacing analyst (must augment)
2. Hallucinated tool output / invented files / fake paths
3. Marketing-style "autonomous SOC" branding without architectural rigor
4. Prompt-only guardrails

---

### 2. Ovie Carroll — Director, DOJ Cybercrime Lab; FOR500 co-author

**Background:**
- 31 years law enforcement + cyber investigation.
- Currently directs the DOJ's CCIPS Cybercrime Lab.
- Co-author of SANS FOR500: Windows Forensic Analysis.
- Adjunct at George Washington University.
- Personal site: https://ovie.coffee/

**Worldview (verbatim quotes):**

> "Digital devices are silent witnesses. The Digital Investigative Analyst acts as their voice, meticulously translating the data into an objective narrative."

> "Through meticulous examination, they extract the unvarnished story from electrons, a chronicle free from bias or embellishment."

**Will reward:**
- Clean audit trails
- Defensible chain-of-custody (read-only mounts, hash-verified evidence)
- Evidence integrity that could survive courtroom scrutiny
- Findings framed as objective narrative, not vendor speak

**Will penalize:**
- AI making interpretive claims without traceable artifact provenance
- "AI hallucinated this finding" without flagging
- Editorial tone in findings

---

### 3. Adam Nasreldin — Senior IR Consultant, Google Mandiant

**Background:**
- 20 years Cyber/Network Security. Long Cisco background before Mandiant.
- Mandiant's house style: Defender's Advantage podcast, threat-intel-driven IR.
- No specific public blog posts surfaced for him.

**Will reward (inferred from Mandiant's published approach):**
- Agents that look like a Mandiant playbook
- Threat intel applied to artifacts
- Structured triage, hypothesis-driven investigation
- Adversary attribution synthesis (named threat actor likely based on TTPs)

**Will penalize:**
- Blind tool-running without hypothesis
- Findings without ATT&CK mapping

---

### 4. Cheri Carr — Owner/Principal, Aspen Forensics; Texas-licensed PI

**Background:**
- Pioneer DFIR practitioner.
- **Founding member of the Air Force and DoD Computer Forensics Laboratories** — the first of their kind.
- Air Force OSI + NASA OIG before private sector.
- Managing Director and DFIR Practice Leader at Stroz Friedberg (2018-2022).
- Testified as expert witness "dozens of times" in federal/state courts.
- https://aspenforensics.com/

**Will reward:**
- Bulletproof chain of custody
- Reproducible findings
- Clear communication of results to non-technical audiences (read: demo video + write-up MATTER)

**Will penalize:**
- Sloppy evidence handling
- Ambiguous findings
- Agents that conflate inference with fact

---

### 5. Steve Cobb — CISO, SecurityScorecard

**Background:**
- 25+ years across Verizon Managed Security, Microsoft (Senior Escalation Engineer), now SecurityScorecard CISO since 2023.
- Frequent speaker: InfoSecCon, Cyber Defense Summit, multiple CISO boards.
- https://securityscorecard.com/people/leadership/steve-cobb/

**Worldview (synthesized from public talks):**
- "From Prevention to Resilience": assume breach, prioritize response.
- Core IR principles: **isolate, contain, neutralize.**
- "Success in response depends on the speed, coordination, and preparation of the team."
- Supply chain security is a major theme.

**Will reward:**
- Speed-to-containment thinking, not just speed-to-detection
- Agents that triage and prioritize "what do we do now"
- Multi-host blast-radius scoping

---

## Tier 2: Will security-audit your work

### 6. Jens Ernstberger — Founder, Kontext Security

**Specialty:** Runtime authorization for AI agents — scoped creds, short-lived tokens, audit trails. USENIX Security 2024 SNARK research.

**Will probe:**
- MCP server prompt-injection resistance
- Credential handling
- Tool-use authorization
- Whether agents can escalate privileges

**Action:** Document scoped credentials, short-lived tokens, deny-lists, and a clean audit trail explicitly in the architecture diagram.

---

### 7. Yotam Perkal — Head of Security Research, Pluto Security

**Specialty:** Discovered CVE-2026-33032 ("MCPwn") — MCP endpoints inheriting application capabilities without security controls (CVSS 9.8). Published "Inside Claude Cowork: How Anthropic's Autonomous Agent Actually Works."

**Will probe:**
- The MCP server itself for reverse-engineerable security flaws
- Adversarial evidence handling
- Process boundaries

**Action:** If we ship a custom MCP, expect it to be reverse-engineered. Build the adversarial-evidence sanitizer layer. Document the threat model.

---

## Tier 3: Will read for production-shape

### 8-14. Enterprise SOC judges

| Judge | Org | What they care about |
|---|---|---|
| Brad Edwards | Palo Alto Networks (Domain Consultant SecOps) | Production-deployable, scales beyond one analyst |
| Sneha Parmar | Deutsche Bank (Director EDR) | Enterprise EDR integration; runs at scale |
| Saurabh Naik | Lockheed Martin (Head of Red Team) | Adversary perspective; what would I bypass? |
| Maximilian Gutowski | Deutsche Telekom Security (Head of TDR) | SOC workflow fit |
| Jason Garman | AWS (Principal Security Specialist) | Cloud-native, infra-as-code; reproducibility |
| Steve Cobb | SecurityScorecard (CISO) | Supply chain + speed (also Tier 1) |
| Georgios Kapoglis | Roblox (Staff Detection & Response Engineer) | Detection engineering — actionable, not academic |

**Composite preference:** Production-shape, not research demo. README that another Fortune-500 IR lead would actually deploy. Reproducible. Documented threat model.

---

## Tier 4: Will read for DFIR practitioner credibility

| Judge | Org | Lens |
|---|---|---|
| Amanda Rankhorn | Ex-FBI Senior Forensics Examiner (Retired) | Court-admissibility |
| Khushi Gupta | Asst. Professor of Cybersecurity, UNG | Pedagogy — is this teachable? |
| Marc Brawner | Auxiris (Managing Partner) | Boutique IR practitioner perspective |
| Adam Nasreldin | Mandiant (also Tier 1) | Threat-intel-grounded |
| John Wilson | HaystackID (CISO + President of Forensics) | E-discovery-grade evidence handling |
| Preston Fitzgerald | SANS (Cybersecurity SME) | SANS-curriculum alignment |
| Cheri Carr | Aspen Forensics (also Tier 1) | Expert-witness rigor |
| Sandeep Bachhas | Sr. Manager, Cyber Threat Hunting | Hunt methodology |
| Roshan Varghese | Sr. Information Security Manager IR | Operational fit |

**Composite preference:** SANS-style narrative. Hypothesis-driven investigation. Multi-artifact corroboration. Defensible findings.

---

## Tier 5: Will read for "would this actually help a SOC analyst at 3 AM"

| Judge | Org |
|---|---|
| Joshua McCray | Hilton (Sr. Lead Cyber Security Analyst) |
| Pedro Jimenez Argente del Castillo | ING Hubs Spain (SOC Chapter Lead) |
| Mathieu Alcaina | Onepoint (SOC L3 / DFIR Analyst) |
| Monish Alur Gowdru | UltraViolet Cyber (Technical Security Lead) |
| Dorian Oliver Collier | National CSIRT Lead & DFIR Specialist |
| Narrayanan MKL | Standard Chartered Bank (VP Cyber Defence) |
| Nodirjon Umurkulov | Security Researcher/Engineer |
| Brett Cumming | Skechers (CISO) |
| Nimitt Jhaveri | BitScore Cybertech LLP (CEO) |
| Harish Vundavalli | Sr. Technical Architect, Strategic Education |
| Teri Green | Elevate (VP of Technology) |
| Ahmed AbuGharbia | cyberdojo.ai (Founder) |
| Jeroen Hoof | Freelance Lead Analyst / SANS Instructor |
| Sumit Ranjan | AI Security Advisor & Ex CTO |
| Jon Stewart | LevelBlue (Managing Director) |
| Kellep Charles | Capitol Technology University (Cybersecurity Chair) |
| Michael Barclay | Origin Security (Principal Security Researcher) |
| Richard Nathan Smith | Enterprise Architect |
| Dr. Stephen Coston | Lead Security Architect AI and Cybersecurity |
| Muhammad Shera | DFIR Consultant |

**Composite preference:** Practical, not academic. "I would actually run this during an incident." Demo video must show a real triage moment, not a slide deck.

---

## Synthesized judge psychology — the unwritten checklist

A submission that nods to ALL of these will resonate broadly:

1. **Rob T. Lee will see:** senior-analyst sequencing + Ralph Wiggum Loop + measured hallucination reduction
2. **Ovie Carroll / Cheri Carr / Amanda Rankhorn will see:** chain-of-custody + hash-verified evidence + audit-id-traceable findings
3. **Adam Nasreldin will see:** ATT&CK-mapped narrative + adversary attribution synthesis
4. **Steve Cobb will see:** speed-to-containment + blast-radius scoping
5. **Yotam Perkal / Jens Ernstberger will see:** MCP threat model documented + sanitizer layer + scoped creds
6. **Enterprise SOC tier will see:** production-shape, reproducible install, README that's actually useful
7. **3-AM-analyst tier will see:** the demo video shows real triage, not slides

## Tactical implication for the demo video

The 5-minute video should hit:
- **0:00-0:30** — context: "AI threats strike in minutes; here's the defender." Cite GTG-1002.
- **0:30-1:00** — architecture diagram with security boundaries marked. (Resonates Perkal/Ernstberger.)
- **1:00-3:00** — live terminal: "find evil" against NIST Hacking Case. Show real findings appearing with audit_ids. (Resonates Rob/Ovie/Cheri/3-AM analysts.)
- **3:00-3:30** — **Self-correction moment**: Volatility errors / wrong plugin → agent reads stderr → adjusts → retries. (Resonates Rob — Ralph Wiggum Loop is on the wall.)
- **3:30-4:00** — Critic moment: critic subagent CHALLENGES a wrong finding; investigator revises. (Resonates Rob — tiebreaker criterion live.)
- **4:00-4:30** — Hallucination metric: "baseline 18% → ours 4%". (Resonates Rob honesty + IR Accuracy.)
- **4:30-5:00** — Final report rendered; findings with court-admissibility annotations. (Resonates Ovie/Cheri/Amanda.)

This sequence hits every judge tier's primary value in 5 minutes.
