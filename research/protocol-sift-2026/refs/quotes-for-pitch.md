# refs/quotes-for-pitch — Quote bank for video, write-up, and architecture diagram

Every quote here is **verbatim** with source URL. Use in the demo video script, Devpost write-up, README, and architecture diagram callouts.

---

## A. The "why now" thesis (use to open the demo + write-up)

### A.1 Anthropic GTG-1002 disclosure (Nov 13, 2025)

> "[Claude performed] 80-90% of the campaign, with human intervention required only sporadically (perhaps 4-6 critical decision points per hacking campaign)."

> "At the peak of its attack, the AI made thousands of requests, often multiple per second — an attack speed that would have been, for human hackers, simply impossible to match."

> "The first documented case of a large-scale cyberattack executed without substantial human intervention."

**Source:** https://www.anthropic.com/news/disrupting-AI-espionage (PDF: https://assets.anthropic.com/m/ec212e6566a0d47/original/Disrupting-the-first-reported-AI-orchestrated-cyber-espionage-campaign.pdf)

### A.2 CrowdStrike — 62-minute breakout (Feb 2024)

> "From Breakout to Breach in Under Three Minutes."

> Average breakout time = **62 minutes** (down from 84 the prior year). Fastest recorded eCrime breakout: **2 minutes 7 seconds**.

**Source:** https://www.crowdstrike.com/en-us/press-releases/2024-crowdstrike-global-threat-report-release/

### A.3 Horizon3 NodeZero — 60-second escalation

> "Horizon3's NodeZero autonomous pentesting platform achieved full privilege escalation in approximately 60 seconds in documented cases."

> "In one case, NodeZero achieved exploitation within 60 seconds of discovering a vulnerable system."

**Source:** Rob T. Lee citing Horizon3 — https://robtlee73.substack.com/p/why-47-the-math-behind-ai-attacks

### A.4 MIT ALFA-Chains — 0.01 sec exploit chain

> 20-host network: exploit chain found in 0.01 seconds.
> 200-host network: 13 exploit chains in 26.25 seconds.

**Source:** Rob T. Lee citing ALFA-Chains research — https://robtlee73.substack.com/p/why-47-the-math-behind-ai-attacks

### A.5 The 47x number (cite with care — Rob admits it's vibes)

> "Yes, that's the actual reason it's 47 and not 48. I wish I had a more rigorous justification. I don't."

This is a **safe-to-quote** moment — Rob rewards honesty. Quoting this back in the accuracy report ("we follow your example — here's our actual hallucination rate") will resonate.

**Source:** https://robtlee73.substack.com/p/why-47-the-math-behind-ai-attacks

---

## B. Rob T. Lee's defining quotes (use throughout — these ARE the rubric)

### B.1 The rubric in one sentence

> **"Teach an AI agent to think like a senior analyst — how to sequence its approach, recognize when something doesn't add up, and self-correct when it gets it wrong."**

**Use this as the cover quote of the README.** This is the rubric.

**Source:** https://robtlee73.substack.com/p/registration-is-open-find-evil-hackathon

### B.2 The Ralph Wiggum Loop (use as the self-correction demo title)

> "When a Volatility command returns an error, Claude reads the error message, adjusts its hypothesis... and retries."

> "A tool that's fast but fails silently is worse than useless. In forensics you need to know what you couldn't find as much as what you did find."

**Use as caption when the demo shows Volatility erroring → agent adjusting → retrying.**

**Source:** https://robtlee73.substack.com/p/introducing-protocol-sift-meeting

### B.3 Permission to flag your own hallucinations

> "Protocol SIFT works. It also hallucinates more than we'd like. (That's exactly why this hackathon exists.)"

**Quote in the accuracy report intro paragraph.** Establishes that you measured your own failures *because the sponsor asked for honesty*.

**Source:** https://robtlee73.substack.com/p/introducing-protocol-sift-meeting

### B.4 The time-to-finding anchor

> "I typed two words, 'find evil,' and fourteen minutes twenty-seven seconds later had a complete C drive analysis."

**Quote in the architecture diagram or the demo video intro.** Your submission's time-to-finding number is anchored against this.

**Source:** https://robtlee73.substack.com/p/dangerous-new-attack-techniques-rsac-2026-preview-protocol-sift

### B.5 Speed asymmetry framing

> "Adversaries are operating at machine speed. The answer is not faster humans."

> "Defenders are out here bringing knives to a drone strike."

> "Defensive OODA loops are measured in hours while offensive loops are now measured in seconds."

**Use in the opening 30 seconds of the demo video.**

**Source:** https://robtlee73.substack.com/p/introducing-protocol-sift-meeting

### B.6 Same architecture, different polarity

> "The architecture they used, an agentic AI connected to offensive tools via MCP, is the exact same architecture I'd been building for defense."

**Use as the bridge between "offensive AI exists (GTG-1002)" and "we're building the defensive counterpart."**

**Source:** https://robtlee73.substack.com/p/introducing-protocol-sift-meeting

### B.7 AI augments, doesn't replace

> "The tool handles the syntax so the investigator can focus on what actually requires a human: reading the findings and driving the case. Only someone who knows DFIR can interpret that output."

**Use in the write-up section on "what we built." Establishes you respect the analyst.**

**Source:** https://robtlee73.substack.com/p/dangerous-new-attack-techniques-rsac-2026-preview-protocol-sift

### B.8 The "operator" framing

> "Stop threat modeling AI like a tool and start threat modeling it like an operator." (quoting Yotam Perkal — who is also a judge)

> "When you give an autonomous agent business context, access to tools, and permission to act, it stops being software. It becomes an actor, a privileged actor."

**Cite this in the architecture diagram security section.** Demonstrates you read the panel.

**Source:** https://robtlee73.substack.com/p/ai-isnt-a-tool-anymore-its-an-operator

### B.9 The mission framing

> "The answer is not faster humans. The answer is AI-augmented defenders, matching AI speed with AI speed."

**Use as the demo video closing line.**

**Source:** https://www.sans.org/press/announcements/two-words-changed-cybersecurity-find-evil-builders-answer-call-defend-infrastructure

### B.10 The community framing

> "Offensive teams operate with three or four people working in secret. We're putting the entire practitioner community on this problem at the same time."

**Use in the "what's next" section of the write-up.** Establishes your work is meant to be reintegrated.

**Source:** Same SANS press release.

---

## C. SANS official framing

### C.1 The challenge (from the Devpost overview)

> "Find Evil! challenges you to close [the speed gap]."

### C.2 The deferred admission (from the SANS blog)

> "AI acts strictly as a constrained workflow assistant used to coordinate DFIR tooling, sequence analytical steps, and reduce friction in repetitive tasks."

> "Protocol SIFT is in its initial research stage and has not been validated for forensic soundness or evidentiary reliability."

> "Deterministic DFIR utilities remain the sole source of analytical output; investigators (not the AI) handle validation, interpretation, and reporting."

**Translation for our positioning:** Frame your submission as **constrained workflow assistance**, NOT "autonomous SOC." Match this language verbatim in the README.

**Source:** https://www.sans.org/blog/protocol-sift-experimental-research-initiative-ai-assisted-dfir

---

## D. Judge quotes worth weaving in

### D.1 Ovie Carroll on evidence as narrative

> "Digital devices are silent witnesses. The Digital Investigative Analyst acts as their voice, meticulously translating the data into an objective narrative."

> "Through meticulous examination, they extract the unvarnished story from electrons, a chronicle free from bias or embellishment."

**Cite when describing your finding generation philosophy.**

### D.2 Jens Ernstberger on contextual authorization

> "Failures rarely occur where you're watching. They occur in the seams between the components." — Julie Davila quoted by Rob T. Lee, framed by Lee as: vulnerabilities live "in the orchestration layers, the APIs and the points where untrusted AI output gets serialized into privileged execution boundaries."

**Cite when describing your sanitizer layer — you understand where the seams are.**

---

## E. Composite frames for the pitch (paste-ready)

### E.1 The 3-sentence "why" — for the demo video open

> "In November 2025, Anthropic disclosed GTG-1002 — a Chinese state operation where Claude Code autonomously executed 80–90% of an espionage campaign across ~30 targets, making 'multiple requests per second.' Defender OODA loops still run in hours; the adversary's runs in seconds. Find Evil! exists to close that gap — to give defenders the same MCP-orchestrated agent architecture that just got operationalized for offense."

### E.2 The architecture story — for the write-up

> "Rob T. Lee's framing of Protocol SIFT is 'AI as constrained workflow assistant — deterministic tools remain the sole source of analytical output.' Our submission honors that frame. The agent doesn't *make* findings; it *runs* deterministic forensic tools, parses their output server-side, and stages findings as DRAFTs that humans cryptographically approve. The novel layer is what we add: a closed-loop critic agent that fires every N findings, re-reads the cited evidence, and CHALLENGES findings the investigator cannot defend. This is the operational implementation of Rob's 'recognize when something doesn't add up, and self-correct when it gets it wrong.'"

### E.3 The accuracy story — for the accuracy report

> "Rob said it best: 'Protocol SIFT works. It also hallucinates more than we'd like.' That admission is the entire reason we built the hallucination harness. On the Nitroba pcap, the NIST Data Leakage Case, and the NIST Hacking Case, we measured baseline Protocol SIFT against our submission. Baseline produced [X] hallucinated findings (citing files / paths / hashes that do not exist in the image); our submission produced [Y] — a [Z]% reduction. We attribute most of the improvement to two architectural choices: server-side parsing of all tool output (no raw stdout reaches the LLM) and the closed-loop critic re-reading evidence before findings can be approved."

### E.4 The honesty disclosure — for the accuracy report

> "We adopt Rob's discipline of admitting what we don't know. The harness flagged [X] findings we still got wrong, including [examples]. The critic agent caught most of our hallucinations but missed [N] — typically those where the agent and critic shared the same (incorrect) inference about the tool's output. This is the next frontier — adversarial critic-of-critic loops — and it's where Protocol SIFT v3 should go."

---

## F. The architecture diagram callouts

When marking the diagram, use these phrases on the labels:

| Boundary | Phrasing |
|---|---|
| MCP server tools | "Architectural guardrail — destructive functions don't exist" |
| Evidence mount | "Read-only at the kernel (ro,noexec,nosuid) — not at the prompt" |
| Sandbox | "bwrap kernel namespaces (--unshare-net --unshare-pid)" |
| Approval ledger | "HMAC-SHA256, PBKDF2-derived key, stored outside the LLM sandbox" |
| Sanitizer layer | "Adversarial-evidence quarantine (Perkal/Ernstberger threat model)" |
| Critic subagent | "Closed-loop critic→revise (Rob T. Lee's Ralph Wiggum Loop, generalized)" |
| Audit log | "Per-tool JSONL with stable audit_id — every finding traces here" |
| Finding state machine | "DRAFT → APPROVED requires cryptographic signature (LLM cannot forge)" |

These phrases are deliberately load-bearing. Each one IS a security argument when a judge reads the diagram.

---

## G. README open-paragraph templates

### G.1 The 1-paragraph "what is this"

> **[YourProjectName]** is an autonomous forensic investigator built on the SANS SIFT Workstation. It teaches an AI agent to think like a senior analyst — sequencing its approach, recognizing when artifacts don't corroborate, and self-correcting when it gets a finding wrong. Built for the SANS Protocol SIFT "Find Evil!" hackathon (Apr–Jun 2026). MIT-licensed. Built on Custom MCP Server architecture with a closed-loop critic→revise subagent.

### G.2 The 1-paragraph "what's novel"

> Existing Protocol SIFT extensions (including the reference Valhuntir platform by Steve Anson / AppliedIR) rely on prompt-level rotation and structural validation gates to suppress hallucination. We add two architectural layers on top: (1) a **closed-loop critic→revise subagent** that fires periodically, re-reads cited evidence, and CHALLENGES findings the investigator cannot defend; (2) an **adversarial-evidence sanitizer layer** that strips prompt-injection patterns and unicode-trick characters from any LLM-bound free-text field. We measure both against a public-answer-key harness on Nitroba + NIST Data Leakage + NIST Hacking Case.

---

## H. Negative quotes — anti-patterns to avoid

Rob T. Lee is hostile to vendor-marketing language. Do NOT use:

- ❌ "Autonomous SOC"
- ❌ "AI-powered triage" (without architecture detail)
- ❌ "Replaces L1 analysts" — Rob explicitly says AI augments, doesn't replace
- ❌ "Eliminates hallucinations" — over-claim; he wants you to measure and admit
- ❌ "Production-grade" without evidence
- ❌ "Industry-first" without checking Valhuntir
- ❌ "Patent-pending" / "proprietary algorithms" — this is open-source-only

Use INSTEAD:

- ✅ "Constrained workflow assistant" (Rob's preferred framing)
- ✅ "Architectural constraint" (specific, measurable)
- ✅ "Closed-loop critic" (descriptive of the wedge)
- ✅ "Measured hallucination rate of X% on Y dataset"
- ✅ "Augments the senior analyst" (not replaces)
- ✅ "Reproducible by other practitioners" (a Usability anchor)
