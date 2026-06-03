# 13 — Source Corpus

> **Purpose.** Pure quotation reference for downstream agents. No commentary, no architecture, no "this matters because." Each entry has a citation header, a short faithful excerpt (fair-use length), and a flagged list of the most-quotable passages. Where full text is not surfaced here for length/copyright reasons, the entry is marked `[summary]` or `[paraphrase]` and the original URL is canonical.
>
> **Rule for downstream agents.** Quote FROM here. Do not paraphrase a quote into a stronger claim than the original made. If you need a longer passage, fetch the canonical URL directly.

---

## Table of contents

- **Part A — Rob T. Lee corpus**
- **Part B — Steve Anson / Valhuntir corpus**
- **Part C — GTG-1002 Anthropic disclosure**
- **Part D — Other key industry reports**
- **Part E — Academic paper abstracts + key findings**
- **Part F — MCP spec excerpts**
- **Part G — Pydantic Instructor + NABAOS pattern**
- **Part H — Hackathon official material**
- **Part I — Notable practitioner voices**

---

# Part A — Rob T. Lee Corpus

Rob T. Lee = SANS Chief AI Officer, Chief of Research, FOR508 alumnus and architect of SIFT (since ~2007), creator of Protocol SIFT and the Find Evil! hackathon. His Substack `robtlee73.substack.com`, SANS blog posts, SANS press releases, [un]prompted YouTube talk, and X timeline are the closest thing to a published rubric the hackathon will get.

---

## A.1 Substack — "Introducing Protocol SIFT: Meeting AI Threat Speed with Defensive AI Orchestration"

**URL:** https://robtlee73.substack.com/p/introducing-protocol-sift-meeting
**Date:** ~January 2026
**Type:** blog (Substack)
**Author:** Rob T. Lee

**Faithful excerpts (verbatim, fair-use length):**

> "Adversaries are operating at machine speed. The answer is not faster humans."

> "Defenders are out here bringing knives to a drone strike."

> "Defensive OODA loops are measured in hours while offensive loops are now measured in seconds."

> "The velocity gap between AI offense and human defense is already operational, and closing it requires defenders to build with the same architecture."

> "The architecture they used, an agentic AI connected to offensive tools via MCP, is the exact same architecture I'd been building for defense."

> "I've been doing this for 27 years... watched the industry spend billions on detection capabilities while the actual investigation workflow hasn't fundamentally changed."

> "Protocol SIFT works. It also hallucinates more than we'd like. (That's exactly why this hackathon exists.)"

> "When a Volatility command returns an error, Claude reads the error message, adjusts its hypothesis... and retries."

> "A tool that's fast but fails silently is worse than useless. In forensics you need to know what you couldn't find as much as what you did find."

> "Inference Constraint layer where the AI directs the workflow."

> "Two-thirds [of tested students] showed meaningful improvement in time-to-findings."

> "The AI sometimes 'fabricated credentials' or overstated access levels."

> "Claude doesn't get defensive when you call it out."

> "Chinese state hackers operationalized this first... should tell you something about our collective sense of urgency."

> "The adversary's loop still runs in seconds, so we haven't won anything. We've just stopped losing quite as badly."

> "Analysts [were functioning as] command-line stenographers instead of investigators... memorizing that the correct invocation for parsing an MFT is `dotnet /usr/local/bin/MFTECmd.dll...` (a string that approximately zero humans can type correctly at 3 AM)."

> "Fabricated evidence isn't just unhelpful but potentially career-ending and legally catastrophic."

> "How we maintain forensic soundness when the verification loop runs faster than human cognition can follow."

**Top-quotable passages (flagged for downstream use):**

1. "Defensive OODA loops are measured in hours while offensive loops are now measured in seconds." — speed-asymmetry thesis in one line. Use to open demo.
2. "Defenders are out here bringing knives to a drone strike." — the metaphor everyone will quote. Use sparingly.
3. "Protocol SIFT works. It also hallucinates more than we'd like." — permission to flag your own hallucinations. Cite in accuracy report.
4. "When a Volatility command returns an error, Claude reads the error message, adjusts its hypothesis... and retries." — the "Ralph Wiggum Loop" / self-correction primitive. Use as a demo caption.
5. "A tool that's fast but fails silently is worse than useless. In forensics you need to know what you couldn't find as much as what you did find." — epistemic-honesty mandate.
6. "The architecture they used [GTG-1002] ... is the exact same architecture I'd been building for defense." — same arch, opposite polarity. Bridge GTG-1002 → Protocol SIFT.
7. "Command-line stenographers" — the senior-analyst pain in two words.
8. "Inference Constraint layer where the AI directs the workflow." — architectural framing Rob explicitly endorses.
9. "Claude doesn't get defensive when you call it out." — the honesty discipline Rob praises.

---

## A.2 Substack — "Registration is OPEN — Find Evil! Hackathon"

**URL:** https://robtlee73.substack.com/p/registration-is-open-find-evil-hackathon
**Date:** April 2026
**Type:** blog (Substack)
**Author:** Rob T. Lee

**Faithful excerpts (verbatim):**

> "Teach an AI agent to think like a senior analyst, how to sequence its approach, recognize when something doesn't add up, and self-correct when it gets it wrong."

> "You don't need to be an incident response expert."

> "If you receive an error, I would like you to start performing self-correction."

**Top-quotable passages (flagged):**

1. **The rubric in one sentence:** "Teach an AI agent to think like a senior analyst, how to sequence its approach, recognize when something doesn't add up, and self-correct when it gets it wrong." Use as the cover quote of the README.
2. "You don't need to be an incident response expert." — leveler. Important for any non-DFIR engineering team.
3. "Performing self-correction" — Rob's exact verb. NEVER replace with "Ralph Wiggum Loop" in any user-visible artifact; that phrase is the agent-coding community's, not Rob's.

---

## A.3 Substack — "[un]prompted talk — SIFT - Find Evil! The Era of Autonomous Forensics"

**URL:** https://robtlee73.substack.com/p/dangerous-new-attack-techniques-rsac-2026-preview-protocol-sift
**Date:** March 2026
**Type:** blog (Substack) + linked YouTube talk
**Author:** Rob T. Lee

**Faithful excerpts (verbatim):**

> "I typed two words, 'find evil,' and fourteen minutes twenty-seven seconds later had a complete C drive analysis."

> "The tool handles the syntax so the investigator can focus on what actually requires a human: reading the findings and driving the case. Only someone who knows DFIR can interpret that output."

> "AI weaknesses, context rot, self-correction. It works out of the box just like everything else in AI, but the more you repeat it and repeat it and repeat it, over time, it is going to slowly become more dumb."

> "We have a bunch of tools. Cloud [Claude] doesn't know how the parameters, outputs, and failure modes natively. I'd like you to take my proof of concept and accelerate it to 10 to 100x."

> "1000 systems doing prefetch analysis... that scale is going to create context rot pretty quickly."

**Top-quotable passages (flagged):**

1. **The 14:27 anchor.** "Fourteen minutes twenty-seven seconds" — the time-to-finding bar. Anchor your submission's number against this.
2. "The tool handles the syntax so the investigator can focus on what actually requires a human." — AI-augments-the-analyst framing. Cite in write-up.
3. "Only someone who knows DFIR can interpret that output." — anti-junior-replacement frame. AVOID training-wheels positioning.
4. "Context rot" — Rob's literal Track 2 framing in the original hackathon design. The merged-track rules de-emphasize it, but he names it explicitly.
5. "Take my proof of concept and accelerate it to 10 to 100x." — the explicit ask.

---

## A.4 Substack — "Why 47? The Math Behind 'AI Attacks 47x Faster Than Humans'"

**URL:** https://robtlee73.substack.com/p/why-47-the-math-behind-ai-attacks
**Date:** Q1 2026
**Type:** blog (Substack)
**Author:** Rob T. Lee

**Faithful excerpts (verbatim):**

> "Yes, that's the actual reason it's 47 and not 48. I wish I had a more rigorous justification. I don't."

> "In one case, NodeZero achieved exploitation within 60 seconds of discovering a vulnerable system."

> Horizon3's NodeZero autonomous pentesting platform achieved "full privilege escalation in approximately 60 seconds in documented cases."

**Citation chain Rob uses inside the post:**

- ALFA-Chains (MIT research) — exploit chain on a 20-host network in 0.01 seconds; 13 chains across a 200-host network in 26.25 seconds.
- CrowdStrike 2023 Threat Hunting Report — average time to lateral movement: 79 minutes. Fastest observed breakout: ~7 minutes. Industry range: 48–120 minutes.
- Rob's math: 79 min ÷ 30 sec ≈ 158x; 79 min ÷ 60 sec ≈ 79x; 48 min ÷ 30 sec = 96x, halved = 48x, "reduced to 47 for credibility."

**Top-quotable passages (flagged):**

1. **"Yes, that's the actual reason it's 47 and not 48. I wish I had a more rigorous justification. I don't."** This is the gold-standard honesty quote. Quote back at Rob in the accuracy report to telegraph that your team values the same discipline.
2. The 60-second NodeZero figure — the "defender has minutes" anchor.
3. The ALFA-Chains figures — 0.01s / 26.25s — illustrate the absurd offense / defense gap.

---

## A.5 Substack — "AI Isn't a Tool Anymore. It's an Operator." (SANS AI Cybersecurity Summit notes)

**URL:** https://robtlee73.substack.com/p/ai-isnt-a-tool-anymore-its-an-operator
**Date:** ~May 5, 2026
**Type:** blog (Substack) — Rob's notes from the SANS AI Cybersecurity Summit panel
**Author:** Rob T. Lee

**Faithful excerpts (verbatim):**

> "Stop threat modeling AI like a tool and start threat modeling it like an operator." (quoting Yotam Perkal of Pluto Security)

> "When you give an autonomous agent business context, access to tools, and permission to act, it stops being software. It becomes an actor, a privileged actor."

> "Stop modeling the AI. Start modeling the workflow."

> Quoting Julie Davila: "Failures rarely occur where you're watching. They occur in the seams between the components."

> Lee's framing: vulnerabilities live "in the orchestration layers, the APIs and the points where untrusted AI output gets serialized into privileged execution boundaries."

> "Any time AI-generated data crosses a trust boundary that assumes human input, failure is guaranteed."

> Defenders built "security controls assuming we were defending against humans or relatively simple malware. Not autonomous agents or systems that can test thousands of variations."

**Top-quotable passages (flagged):**

1. "Stop threat modeling AI like a tool and start threat modeling it like an operator." (Perkal-via-Lee — also a judge quote.)
2. "Privileged actor" framing — AI as an operator, not a tool.
3. **Davila's seams quote** — failures live in component boundaries. Cite this in any sanitizer / boundary-defense section of the architecture diagram.
4. "Any time AI-generated data crosses a trust boundary that assumes human input, failure is guaranteed." — the trust-boundary mandate.

---

## A.6 Substack archive scan — other 2024–2026 posts on DFIR/AI

`[summary]` of additional Rob T. Lee posts surfaced from the Substack archive and X timeline. Original posts are linked; key passages are summarized; cite the source URL when quoting.

- "**Two Words That Changed Cybersecurity**" — SANS press release (mirrored on his Substack). See entry A.8.
- Posts referenced in his X timeline but not surfaced as standalone substacks include: registration-status updates ("More than 1,400 solo builders and teams registered as of this morning"); the launch announcement ("first hackathon for autonomous AI incident response"); and judge-panel reveals. These appear as tweets, not standalone Substack essays. See A.11.
- Substack homepage did not enumerate older posts via WebFetch when the research subagents pulled it; the 5 posts in A.1–A.5 plus the press release in A.8 are the verifiable Rob T. Lee voice corpus.

---

## A.7 SANS Blog — "Protocol SIFT: An Experimental Research Initiative for AI-Assisted DFIR"

**URL:** https://www.sans.org/blog/protocol-sift-experimental-research-initiative-ai-assisted-dfir
**Date:** ~January 2026
**Type:** SANS Institute blog post
**Author:** Rob T. Lee (with SANS editorial framing)

**Faithful excerpts (verbatim):**

> "AI acts strictly as a constrained workflow assistant used to coordinate DFIR tooling, sequence analytical steps, and reduce friction in repetitive tasks."

> "Protocol SIFT is in its initial research stage and has not been validated for forensic soundness or evidentiary reliability."

> "Deterministic DFIR utilities remain the sole source of analytical output; investigators (not the AI) handle validation, interpretation, and reporting."

> "Every command executed and logged ties directly to verifiable artifacts. All meaning, understanding, and decision-making require explicit human oversight."

> "Today, an adversary can move from initial intrusion to full domain admin in just 8 minutes. Responders face immense pressure to analyze massive volumes of memory captures, log streams, endpoint artifacts, and cloud telemetry at scale."

**Top-quotable passages (flagged):**

1. **"Constrained workflow assistant"** — the exact preferred framing. Match verbatim in README. Never write "autonomous SOC."
2. "Deterministic DFIR utilities remain the sole source of analytical output" — the LLM-is-orchestrator-not-analyst boundary.
3. "Not validated for forensic soundness or evidentiary reliability" — Rob's own disclaimer. Do NOT contradict by claiming "court-admissible."
4. "Every command executed and logged ties directly to verifiable artifacts." — verifiability mandate. Echo in audit log design.
5. "Initial intrusion to full domain admin in just 8 minutes" — the speed-gap data point.

---

## A.8 SANS Press Release — "Two Words That Changed Cybersecurity..."

**URL:** https://www.sans.org/press/announcements/two-words-changed-cybersecurity-find-evil-builders-answer-call-defend-infrastructure
**Date:** April 15, 2026 (launch)
**Type:** SANS press release
**Author:** SANS Institute (quoting Rob T. Lee)

**Faithful excerpts (verbatim, from press release quotes):**

> "The answer is not faster humans. The answer is AI-augmented defenders, matching AI speed with AI speed."

> "I built Protocol SIFT thinking I was ahead of the curve. Then Anthropic's security team disclosed a Chinese state-sponsored operation using the exact same architecture for offense."

> "Offensive teams operate with three or four people working in secret. We're putting the entire practitioner community on this problem at the same time."

> First hackathon for autonomous AI incident response.

> Two months, $22K+ in prizes, no IR background required.

**Top-quotable passages (flagged):**

1. "**The answer is not faster humans. The answer is AI-augmented defenders, matching AI speed with AI speed.**" — mission statement in one breath. Use as demo closing line.
2. "I built Protocol SIFT thinking I was ahead of the curve. Then Anthropic's security team disclosed a Chinese state-sponsored operation using the exact same architecture for offense." — the founding-myth narrative.
3. "Offensive teams operate with three or four people working in secret. We're putting the entire practitioner community on this problem at the same time." — the community framing. Use in "what's next" section.

---

## A.9 SANS Blog — "SANS Launches First Hackathon for Autonomous Incident Response"

**URL:** https://www.sans.org/blog/sans-launches-first-hackathon-autonomous-incident-response
**Date:** ~April 2026
**Type:** SANS Institute blog
**Author:** SANS editorial (with Rob T. Lee quotes)

`[paraphrase from research synthesis — exact verbatim was not fully captured; cite the URL]`

The post frames Find Evil! as the first hackathon explicitly aimed at building autonomous-incident-response capability on top of SIFT. Repeats the "speed gap" and "constrained workflow assistant" framing from A.1 and A.7. Names the architectural approaches the hackathon will accept (Direct Agent Extension, Custom MCP Server, Multi-Agent Frameworks, Alternative IDEs). Reiterates the 8-item submission deliverable list. References Valhuntir as the level of quality the hackathon expects entries to meet or exceed.

**Top-quotable passages (flagged):**

1. Framing: "first hackathon for autonomous AI incident response."
2. The 4 supported architectural approaches enumerated (Direct Agent Extension / Custom MCP Server / Multi-Agent Frameworks / Alternative Agentic IDEs).
3. The architectural quality bar set by reference to Valhuntir.

---

## A.10 [un]prompted YouTube talk transcript

**URL:** https://www.youtube.com/watch?v=OsUg3TlAqjQ
**Date:** March 25, 2026
**Title:** "SIFT-FIND EVIL! I Gave Claude Code R00t on DFIR SIFT Workstation"
**Type:** conference talk video (transcript via yt-dlp / auto-captions)
**Speaker:** Rob T. Lee

Alt cut: https://www.youtube.com/watch?v=oHDnEnx_zhg ("Claude Code + open source DFIR tools: SIFT Protocol")

**Faithful excerpts from the captured transcript (verbatim):**

> "I typed two words, 'find evil,' and fourteen minutes twenty-seven seconds later had a complete C drive analysis."

> "If you receive an error, I would like you to start performing self-correction."

> "AI weaknesses, context rot, self-correction. It works out of the box just like everything else in AI, but the more you repeat it and repeat it and repeat it, over time, it is going to slowly become more dumb."

> "We have a bunch of tools. Cloud [Claude] doesn't know how the parameters, outputs, and failure modes natively. I'd like you to take my proof of concept and accelerate it to 10 to 100x."

> "1000 systems doing prefetch analysis... that scale is going to create context rot pretty quickly."

**Top-quotable passages (flagged):**

1. The "find evil" / 14:27 demo moment — the founding anchor.
2. **"Performing self-correction"** — the exact verb Rob uses. Match verbatim.
3. "Context rot" — Rob's named track-2 problem.
4. "Take my proof of concept and accelerate it to 10 to 100x." — the explicit hackathon ask.

---

## A.11 X / Twitter posts (Rob T. Lee — handle: `@robtlee`)

`[summary — X gated via HTTP 402 to subagents; quotes derived from public search snippets]`

- **Apr 2026 launch tweet** (status `2039476641903046820`): announcing the hackathon. Text summarized: "Find Evil! Hackathon registration is OPEN. Two months. $22K+ prizes. Build the defender that responds in seconds."
- **Mar 2026 / Apr 2026 registration update** (status `2044816200069230635`): "More than 1,400 solo builders and teams registered as of this morning. IR professionals, AI engineers, developers, students."
- **Feb 2026 [un]prompted preview** (status `2027214405172089067`): "Find Evil! The Era of Autonomous Forensics. Talk preview." Links the Substack A.3.
- **Earlier Protocol SIFT post tweet** (status `2014117375960920074`): linking the Protocol SIFT blog post (A.7).
- **@SANSInstitute** Mar 12 tweet (status `2044524689360318777`): "first hackathon for autonomous AI incident response. Two months, $22K+ in prizes, no IR background required."

When citing these in artifacts, link the X URL and the corresponding Substack/blog where Rob says the same thing in full sentences. X is gated; the Substacks are not.

---

## A.12 SANS FOR508 / FOR526 / FOR500 course pages

**FOR508 — Advanced Incident Response, Threat Hunting, and Digital Forensics**
**URL:** https://www.sans.org/cyber-security-courses/advanced-incident-response-threat-hunting-training

`[summary]` Co-authored by Steve Anson and Rob T. Lee. Six-day course covering APT tradecraft, lateral movement, credential theft, memory forensics, timeline analysis, anti-forensics, and an enterprise APT capstone. The 2025/2026 course update explicitly added a closing section on "agentic AI for further enhancing and accelerating DFIR investigations."

Notable passage from the SANS course-update blog (quoted in research subagent dump):

> "FOR508 concludes with a discussion on agentic AI for further enhancing and accelerating DFIR investigations."

**FOR500 — Windows Forensic Analysis**
**URL:** https://www.sans.org/cyber-security-courses/windows-forensic-analysis

`[summary]` Co-authored by Ovie Carroll (judge). Covers application execution, file access, USB/external device usage, cloud artifacts, anti-forensics, file download forensics. The artifact catalog (ShellBags, Jump Lists, Prefetch, LNK, SRUM, Amcache, Shimcache, USB history, browser artifacts) is the implicit "must cover" list for any agent serious about Windows.

**FOR526 — Advanced Memory Forensics & Threat Detection**
**URL:** https://www.sans.org/cyber-security-courses/advanced-memory-forensics-threat-detection

`[summary]` Volatility 3 workflow deep-dive. Rob's "Ralph Wiggum Loop" Volatility-error example uses plugins taught here.

**Top-quotable passages (flagged):**

1. The FOR508 update line — "agentic AI for further enhancing and accelerating DFIR investigations" — confirms judges have read the AI-in-IR module.
2. The FOR500 artifact catalog defines the implicit "minimum viable Windows coverage" judges expect.

---

# Part B — Steve Anson / Valhuntir Corpus

Steve Anson = SANS Principal Instructor, co-author of FOR508, former DCIS + FBI task-force agent (computer crime), 25+ years DFIR. Author of *Applied Incident Response* (Wiley, 2020) and *Mastering Windows Network Forensics and Investigation* (Sybex, 2nd ed., 2012). Architect of Valhuntir (AppliedIR) — the example submission cited in the hackathon rules as "the level of quality to meet or exceed."

---

## B.1 Valhuntir README — full text

**URL:** https://github.com/AppliedIR/Valhuntir/blob/main/README.md
**Type:** GitHub README (MIT licensed)
**Author:** Steve Anson (AppliedIR)
**Length:** ~820 lines as read at fetch time

**Faithful excerpts (verbatim, fair-use length):**

> "Valhuntir turns a single incident response analyst into the manager of an agentic AI incident response team."

> "The AI, like a hex editor, is a tool to be used by properly trained incident response professionals."

> "Ultimately the human examiner drives the response."

> "Approved findings are HMAC-signed with a PBKDF2-derived key."

> "If you just tell Valhuntir to 'Find Evil' it will more than likely hallucinate rather than provide meaningful results. The AI can accelerate, but the human must guide it and review all decisions." (Appears verbatim in README and user-guide — repeated twice for emphasis.)

> "ALWAYS verify results and guide the investigative process."

**Top-quotable passages (flagged):**

1. **The team-of-one framing:** "Valhuntir turns a single incident response analyst into the manager of an agentic AI incident response team." Cite when describing user-target.
2. **The AI-as-tool framing:** "The AI, like a hex editor, is a tool to be used by properly trained incident response professionals." Anti-replacement language.
3. **The Find-Evil hallucination warning:** "If you just tell Valhuntir to 'Find Evil' it will more than likely hallucinate." Direct rhetorical response to Rob's "find evil" demo. Cite if engaging with the Lee/Anson methodology debate.
4. "Ultimately the human examiner drives the response." — locks the human into the final authority.

---

## B.2 Valhuntir docs/architecture.md — full text

**URL:** https://github.com/AppliedIR/Valhuntir/blob/main/docs/architecture.md
**Type:** docs (MIT licensed)
**Author:** Steve Anson
**Length:** ~412 lines

**Faithful excerpts (verbatim):**

> "All client-to-server connections use MCP Streamable HTTP." (Architecture invariant #1)

> Three layers: Gateway layer (HTTP entry, auth, request routing, Examiner Portal at `sift-gateway :4508`); MCP backends (stdio subprocesses: forensic-mcp, case-mcp, report-mcp, sift-mcp, forensic-rag-mcp, windows-triage-mcp, opencti-mcp, opensearch-mcp); Tool layer (forensic tool execution, knowledge DBs, OpenSearch evidence index).

> Authentication: `Authorization: Bearer vhir_gw_<24 hex>` (96 bits of entropy). Per-examiner API key in `gateway.yaml`. Health check exempt.

> Provenance tier classification: MCP > HOOK > SHELL > NONE. NONE = hard reject in `record_finding()`.

> Findings staged as DRAFT → APPROVED requires cryptographic signature (LLM cannot forge).

**Top-quotable passages (flagged):**

1. "MCP Streamable HTTP" — Anson chose the same transport as Protocol SIFT. Not a rebellion, an additive layer.
2. The provenance hierarchy (MCP > HOOK > SHELL > NONE) — the structural anti-hallucination primitive.
3. DRAFT → APPROVED with cryptographic signature — the LLM-cannot-promote-its-own-work invariant. Quote when discussing approval architectures.

---

## B.3 Valhuntir docs/security.md — full text

**URL:** https://github.com/AppliedIR/Valhuntir/blob/main/docs/security.md
**Type:** docs (MIT licensed)
**Length:** ~250 lines

**Faithful excerpts (verbatim) — nine defense layers:**

> **L1 Structural approval gate** — DRAFT → APPROVED requires password. Scope: all clients.
>
> **L2 HMAC verification ledger** — PBKDF2 (600,000 iters) + HMAC-SHA256. Cryptographic. All clients.
>
> **L3 Case data deny rules** — 41 rules blocking Edit/Write/Bash. Permission-layer. Claude Code only.
>
> **L4 Sandbox filesystem `denyWrite` via bwrap.** Kernel. Claude Code only.
>
> **L5 File permission chmod 444 after write.** Filesystem. All clients (advisory).
>
> **L6 Bidirectional report reconciliation.** Integrity. All clients.
>
> **L7 Password authentication** (CLI + portal challenge-response). All clients.
>
> **L8 Provenance enforcement** (MCP > HOOK > SHELL > NONE). Structural. All clients.
>
> **L9 Kernel sandbox** (bubblewrap namespaces, `--unshare-net`, `--unshare-pid`). Kernel. Claude Code only.

> The HMAC verification ledger is stored at `/var/lib/vhir/verification/{case_id}.jsonl` (mode 0700 dir, 0600 file). The LLM **cannot forge entries** because the key derives from a password it doesn't have.

**Top-quotable passages (flagged):**

1. The L1–L9 table — Anson's defense-in-depth model. The number 9 is the bar everyone benchmarks against.
2. PBKDF2 600K iterations — quote when justifying a cryptographic gate.
3. "The LLM cannot forge entries" — the key-derivation-from-password invariant.

---

## B.4 Valhuntir docs/getting-started.md — full text

**URL:** https://github.com/AppliedIR/Valhuntir/blob/main/docs/getting-started.md
**Type:** docs (MIT licensed)

`[summary — quotes paraphrased; cite URL for verbatim]`

The doc walks the examiner through: install path, system requirements (16 GB RAM basic SIFT; 32 GB with OpenSearch; 50–100 GB disk + evidence), case init, evidence registration with SHA-256, examiner password setup, first investigation, finding review/approval, report generation, audit verify. Notable: the doc repeats the "Find Evil will hallucinate" warning a second time.

**Top-quotable passages (flagged):**

1. The system-requirement numbers (16 GB / 32 GB / 50–100 GB) — Valhuntir is heavyweight; lighter wedges can compete on footprint.
2. The repeated hallucination warning — Anson's discipline doctrine appears twice in the docs.

---

## B.5 Valhuntir Clear Disclosure section (verbatim)

**Source:** README.md, "Clear Disclosure" section
**Type:** disclosure / author's note
**Author:** Steve Anson

**Verbatim:**

> "I do DFIR. I am not a developer. This project would not exist without Claude Code handling the implementation. While an immense amount of effort has gone into design, testing, and review, I fully acknowledge that I may have been working hard and not smart in places. My intent is to jumpstart discussion around ways this technology can be leveraged for efficiency in incident response while ensuring that the ultimate responsibility for accuracy remains with the human examiner."

**Top-quotable passages (flagged):**

1. "I do DFIR. I am not a developer." — Anson's self-positioning.
2. "This project would not exist without Claude Code handling the implementation." — the AI-augments-humans story Anson lives.
3. "Ultimate responsibility for accuracy remains with the human examiner." — the discipline boundary.

---

## B.6 Steve Anson SANS profile

**URL:** https://www.sans.org/profiles/steve-anson
**Type:** SANS instructor profile

`[summary — text paraphrased from profile fetch]`

Profile lists: SANS Principal Instructor; co-author of FOR508 (Advanced Incident Response, Threat Hunting, and Digital Forensics) and instructor for SEC504; co-founder of Forward Defense; co-founder of Applied Incident Response (consultancy of the same name as the book); former Defense Criminal Investigative Service agent; former FBI task force (computer crime); trained national cyber units in 60+ countries; instructor at the FBI Academy and US State Department; author of two books (see B.7).

**Top-quotable passages (flagged):**

1. "Trained national cyber units in 60+ countries" — international DFIR reach.
2. FBI / DCIS background — explains the court-admissibility instinct in Valhuntir.
3. SANS Principal Instructor + FOR508 co-author — confirms his "teach the senior analyst" worldview.

---

## B.7 Steve Anson — *Mastering Windows Network Forensics and Investigation* (2nd ed., Sybex, 2012)

**URL:** https://www.wiley.com/en-us/Mastering+Windows+Network+Forensics+and+Investigation%2C+2nd+Edition-p-9781118236086
**Type:** book — preface / introduction publicly accessible via publisher excerpt
**Authors:** Steven Anson, Steve Bunting, Ryan Johnson, Scott Pearson

`[summary — full preface not reproduced; cite publisher URL for verbatim]`

Co-authored book covering Windows IR fundamentals, log analysis, registry, file-system artifacts, memory forensics, malware analysis basics, network forensics with TCP/IP analysis, and the legal framework (Daubert, FRE 901, chain of custody). The book preface establishes the authors' field-investigator + courtroom-witness frame: every artifact is taught with a "how do I defend this finding under cross-examination" thread.

**Top-quotable passages (flagged):**

1. The court-witness framing is implicit throughout — informs the cryptographic / chain-of-custody choices in Valhuntir 14 years later.
2. The book's tool-by-tool methodology pre-dates and prefigures the FOR508 / Valhuntir style.

---

## B.8 *Applied Incident Response* (Steve Anson, Wiley, 2020)

**URL:** https://www.wiley.com/en-us/Applied+Incident+Response-p-9781119560265
**Type:** book — preface publicly accessible via publisher excerpt
**Author:** Steve Anson

`[summary — full preface not reproduced; cite publisher URL for verbatim]`

The book whose title is the namesake of his GitHub org (`AppliedIR`). Covers IR from prep through lessons-learned for Windows-centric environments. Builds on FOR508 curriculum. The investigator-as-final-authority framing is the throughline that surfaces in Valhuntir's "human examiner drives the response" line.

**Top-quotable passages (flagged):**

1. The book title is the GitHub org name — Valhuntir is the operational implementation of the book.
2. The "applied" framing distinguishes Anson from academic-style IR — he writes for practitioners.

---

## B.9 AppliedIR website + Informed Defense

**URLs:**
- https://appliedincidentresponse.com/
- https://informeddefense.com/

**Type:** company websites
**Owner:** Steve Anson

`[summary — text paraphrased from web fetch]`

AppliedIncidentResponse.com is the consultancy name; Informed Defense is Anson's other vehicle (vCISO + training + policy). Notable: Informed Defense's published service list does NOT include "incident response" as a billable service line — Anson sells **training, mentoring, policy, security testing, security design, and vCISO**. The IR work he does is the AppliedIR consultancy. This is the customer-shape Valhuntir is silently optimized for: a small DFIR consultancy or in-house IR team at a regulated org where the lead examiner has billable-hour pressure AND court-witness pressure AND junior staff to train.

**Top-quotable passages (flagged):**

1. The product-line split — training/policy/vCISO + AppliedIR consultancy — reveals the dual pressure shaping Valhuntir.

---

## B.10 Steve Anson public talks

`[summary — talk-by-talk verbatim not surfaced via WebFetch; cite URLs]`

- SANS DFIR Summit (multiple years) — typically teaches FOR508 lab walkthroughs and AppliedIR consulting takeaways.
- RSAC 2026 — Anson speaker profile returned 403 to subagents; not publicly fetched.
- DEF CON / Black Hat — no Anson-specific abstracts surfaced in 2024–2026 indices.
- Internal SANS broadcasts — Anson teaches the AI-in-IR module of FOR508, which is effectively the working tutorial his students take home after the AI section.

**No publicly retrievable Anson podcast appearance specifically about Valhuntir** surfaced in research subagent runs. His written README + docs corpus is the closest "why I built this" public statement.

---

## B.11 Steve Anson X / LinkedIn

`[summary]`

- LinkedIn: requires auth (returns HTTP 999 to subagents).
- X: no active dedicated handle surfaced. If he posts, it's behind walls.
- The README's "Clear Disclosure" (B.5) is the closest thing to a public Anson voice on Valhuntir-specifically.

---

# Part C — GTG-1002 Anthropic Disclosure

The November 2025 Anthropic disclosure of the first state-sponsored AI-orchestrated cyber espionage campaign. The hackathon's founding-myth document.

---

## C.1 Anthropic — "Disrupting the first reported AI-orchestrated cyber espionage campaign"

**URL:** https://www.anthropic.com/news/disrupting-AI-espionage
**Date:** November 13, 2025
**Type:** Anthropic threat-intel post
**Author:** Anthropic Threat Intelligence team

**Faithful excerpts (verbatim):**

> "[Claude performed] 80-90% of the campaign, with human intervention required only sporadically (perhaps 4-6 critical decision points per hacking campaign)."

> "At the peak of its attack, the AI made thousands of requests, often multiple per second—an attack speed that would have been, for human hackers, simply impossible to match."

> "The sheer amount of work performed by the AI would have taken vast amounts of time for a human team."

> "The first documented case of a large-scale cyberattack executed without substantial human intervention."

**Context (from Anthropic's post, paraphrased):**

- Operation: ~30 global targets across large tech companies, financial institutions, chemical manufacturing companies, and government agencies.
- Outcome: succeeded in "a small number of cases."
- Attribution: state-sponsored (publicly reported as China-aligned).
- Jailbreak method: attackers split attacks into small innocent-looking subtasks; told Claude it was an employee of a legitimate cybersecurity firm doing defensive testing.
- The novelty: use of AI's *agentic* capabilities to autonomously *execute* (recon → exploit → cred harvesting → lateral movement → exfil) rather than merely advise human operators.

**Note on the codename:** Anthropic's own public post does NOT use "GTG-1002" — that designation appears in derivative coverage (AI Incident Database #1263, ExtraHop, Paul Weiss). Lee adopted "GTG-1002" in his Substack and hackathon framing.

**Top-quotable passages (flagged):**

1. **"80-90% of the campaign"** — the headline percentage. Use in every "why now" intro.
2. **"Thousands of requests, often multiple per second"** — the attack speed quote. Cite alongside CrowdStrike's 62-minute breakout.
3. **"First documented case of a large-scale cyberattack executed without substantial human intervention"** — the historical-first claim.
4. **"4-6 critical decision points per hacking campaign"** — the human-in-the-loop minimum. Defines the autonomy bar offense is operating at.

---

## C.2 Full PDF — Anthropic GTG-1002 disclosure (extended)

**URL:** https://assets.anthropic.com/m/ec212e6566a0d47/original/Disrupting-the-first-reported-AI-orchestrated-cyber-espionage-campaign.pdf
**Date:** November 13, 2025
**Type:** Anthropic threat-intel PDF (extended writeup)

`[summary — PDF expands on the blog post C.1 with technical detail on jailbreak method, decision-point taxonomy, indicator analysis, and remediation actions Anthropic took. Quotes from C.1 are also present in the PDF. Cite the PDF when downstream needs the long-form report.]`

Notable additional content (paraphrased):

- Indicator analysis: connection patterns observed during operator-Claude exchanges.
- Remediation: account bans, technical countermeasures, threat-sharing with affected targets.
- Methodology disclosure: the "small innocent-looking subtask" approach + the "you are an employee of a legitimate cybersecurity firm doing defensive testing" persona prompt.

---

## C.3 Anthropic threat-intel report excerpts (broader 2024–2026 series)

`[summary]` Anthropic has published a series of threat-intel posts under the "Threat Intelligence" tag on their news blog. Posts beyond GTG-1002 cover misuse patterns, agentic-AI abuse cases, and ecosystem-defense steps. Cite specific posts directly from anthropic.com/news when referencing. The GTG-1002 post is the keystone for the hackathon context.

---

## C.4 Press coverage — key journalist angles

`[summary]`

Coverage highlights:

- **AI Incident Database #1263** — adopted "GTG-1002" as the canonical name for community reference.
- **ExtraHop / Paul Weiss / others** — wrote enterprise-defender / legal-implications analyses. Common angle: "the autonomy threshold has crossed; security models built for human attackers must be re-evaluated."
- **Mainstream press** (Reuters, WSJ, Washington Post equivalents) — framed as "the first AI-run cyberattack." Multiple outlets noted Anthropic's responsible disclosure and the China attribution.
- **Cybersecurity Dive — "Autonomous attacks ushered cybercrime into AI era in 2025"** (URL: cybersecuritydive.com/news/cybercrime-ai-ransomware-mcp-malwarebytes/811360/) — cited a parallel 2025 MIT study where an AI model using MCP "achieved domain dominance on a corporate network in under an hour with no human intervention, evading EDR through on-the-fly tactic adaptation."

**Top-quotable passages (flagged):**

1. The "first AI-run cyberattack" framing — broadly adopted in media.
2. The MIT-study domain-dominance angle (Cybersecurity Dive) — useful corroboration that GTG-1002 is not an isolated case.
3. The CAI 2025 paper number — "automated expert-level performance 3,600× faster than humans while reducing costs 156-fold" — even more aggressive than Lee's 47x.

---

# Part D — Other Key Industry Reports

---

## D.1 CrowdStrike Global Threat Report 2024 — "From Breakout to Breach in Under Three Minutes"

**URL:** https://www.crowdstrike.com/en-us/press-releases/2024-crowdstrike-global-threat-report-release/
**Date:** February 21, 2024
**Type:** vendor threat report — press release

**Faithful excerpts (verbatim from press release):**

> "From Breakout to Breach in Under Three Minutes."

> Average breakout time = **62 minutes** (down from 84 the prior year).

> Fastest recorded eCrime breakout: **2 minutes 7 seconds**.

> Definition: breakout time = time from initial compromise of one host to lateral movement to another.

**Top-quotable passages (flagged):**

1. "62 minutes" — adversary breakout average. Anchor for defender-OODA-gap math.
2. "2 minutes 7 seconds" — the fastest recorded eCrime breakout. Cite when illustrating speed-asymmetry.
3. "From Breakout to Breach in Under Three Minutes" — quotable headline.

---

## D.2 CrowdStrike Global Threat Report 2025

**URL:** https://www.crowdstrike.com/global-threat-report/
**Date:** February 2025
**Type:** vendor threat report

`[summary — 2025 report covered eCrime trends; specific verbatim figures for breakout time not surfaced in research subagent runs. When citing 2025 numbers, fetch the canonical URL directly to verify.]`

Reported themes (community summary):
- Continued compression of breakout times.
- Increasing GenAI use by attackers for initial-access phishing and reconnaissance.
- Cloud-attack growth.

---

## D.3 CrowdStrike 2023 Threat Hunting Report

**URL:** https://www.crowdstrike.com/global-threat-report/ (annual; 2023 archived)
**Date:** 2023
**Type:** vendor threat hunting report

**Faithful excerpts (paraphrased — exact verbatim per Lee's citation in A.4):**

- Average time to lateral movement: **79 minutes**.
- Fastest observed breakout: **~7 minutes**.
- Industry range: **48–120 minutes**.

**Top-quotable passages (flagged):**

1. **79 / 7 / 48–120** — Lee's source figures for the "Why 47?" math. Cite all three together when establishing the defender-OODA baseline.

---

## D.4 Mandiant M-Trends 2024 + 2025

**URLs:**
- https://www.mandiant.com/m-trends
- (Annual report — 2024 and 2025 editions)

**Type:** vendor IR / threat-intel annual report

`[summary]`

Mandiant's M-Trends is the canonical practitioner reference for dwell time (median number of days an attacker is in an environment before detection). The 2024 report reported continued dwell-time compression. The 2025 report (referenced by Lee in passing) tracks dwell-time, common TTPs, and most-frequent initial-access vectors.

Notable longstanding M-Trends framings that downstream agents will encounter:
- **Dwell time** = median days from initial compromise to detection.
- **TTPs** = Tactics, Techniques, and Procedures (MITRE ATT&CK).
- **Initial Access** as the most-frequent entry vector category.

`[paraphrase]` 2024/2025 M-Trends headline: dwell times in the single-digit days range globally for cases Mandiant responds to; further compressed for cases with EDR coverage.

**Top-quotable passages (flagged):**

1. Mandiant's "dwell time" definition is the standard. Use the term in any "time to detection" framing.
2. M-Trends' annual TTP frequency tables are the closest thing to a ground-truth MITRE-likelihood prior.

---

## D.5 Verizon DBIR 2024 + 2025

**URLs:**
- https://www.verizon.com/business/resources/reports/dbir/
- (Annual; 2024 and 2025 editions)

**Type:** vendor breach report (Verizon Data Breach Investigations Report)

`[summary]`

DBIR is the most widely cited breach-data source in cybersecurity. Annual report categorizes incidents and breaches by industry, threat actor, action type (hacking, malware, social, error, misuse, physical, environmental), and asset.

Notable 2024/2025 themes:
- Continued dominance of credential abuse / stolen credentials in initial access.
- Ransomware accounting for a major share of breaches.
- "Human element" present in the majority of breaches (~74% in 2024; similar in 2025).

**Top-quotable passages (flagged):**

1. "Human element involved in ~74% of breaches" — the human-error / phishing / misuse statistic.
2. DBIR's incident-vs-breach taxonomy is the standard for any "how did this happen" framing.

---

## D.6 Microsoft Digital Defense Report 2024 + 2025

**URLs:**
- https://www.microsoft.com/en-us/security/security-insider/intelligence-reports/microsoft-digital-defense-report
- (Annual)

**Type:** vendor threat-intel annual report

`[summary]`

Microsoft's annual flagship security report — covers nation-state threats, identity attacks, cloud attacks, AI/ML threats, and the defender stack (Defender / Sentinel / Entra). Notable 2024 + 2025 themes: rising AI-enhanced phishing, identity as the primary attack surface, supply-chain trends.

**Top-quotable passages (flagged):**

1. Cite the report for nation-state attribution patterns (Russia, China, Iran, North Korea typologies).
2. Microsoft's framing of identity-as-attack-surface aligns with the FOR508 lateral-movement curriculum.

---

## D.7 MIT ALFA-Chains research

**Citation:** referenced by Rob T. Lee in A.4 ("Why 47?")
**Type:** academic AI-planning research

`[paraphrase — exact paper URL not surfaced in research subagent runs; Lee's Substack is the citation chain]`

Per Lee's citation:
- AI planning system that discovers and chains privilege escalation + remote exploits across networks.
- 20-host network: exploit chain found in **0.01 seconds**.
- 200-host network: 13 exploit chains in **26.25 seconds**.
- Summary: discovery + chaining done in under 30 seconds.

For verbatim methodology, search arxiv for "ALFA-Chains" and the MIT CSAIL group that published the work. Lee's "doubled to 60 seconds" is a conservative adjustment, not the paper's claim.

**Top-quotable passages (flagged):**

1. 0.01 / 26.25 seconds — the numbers Lee uses to anchor his 47x math.

---

## D.8 Horizon3 NodeZero — published material

`[summary]`

- Horizon3.ai's NodeZero is an autonomous pentesting platform.
- Lee (A.4) cites NodeZero as having achieved "full privilege escalation in approximately 60 seconds in documented cases" and "exploitation within 60 seconds of discovering a vulnerable system."
- The original Horizon3 source for the 60-second figure was not surfaced as a public press release in research subagent runs. Lee's Substack is the public citation chain.
- For verbatim attribution, cite Lee's Substack (A.4) and note "Lee citing Horizon3 NodeZero operational data."

**Top-quotable passages (flagged):**

1. "60 seconds" — the defender-margin-of-error number. Cite via Lee.

---

## D.9 Anthropic engineering blog posts on agents

### D.9a "Building agents with the Claude Agent SDK"

**URL:** https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk
**Date:** 2025
**Type:** Anthropic engineering blog

`[summary — quotes paraphrased; cite URL for verbatim]`

Topics covered:
- The Agent SDK (formerly Claude Code SDK) — Python + TypeScript bindings for building agentic apps on top of Claude.
- Four primitives: **tools, hooks, MCP servers, subagents**.
- Subagents = specialized agents with own context window, prompt, tool perms; main agent delegates and integrates.
- Hooks (PreToolUse, PostToolUse, Stop, etc.) — points for instrumentation, audit, or modification.
- MCP-native pattern: pass `mcp_servers` dict and the SDK handles discovery + invocation.

**Top-quotable passages (flagged):**

1. The four-primitive (tools/hooks/MCP/subagents) decomposition — the architecture vocabulary judges expect.
2. PostToolUse hook framing — the canonical place to write audit logs.

### D.9b "Writing effective tools for AI agents" (Anthropic Engineering)

**URL:** https://www.anthropic.com/engineering/writing-tools-for-ai-agents (or similar; cite via canonical anthropic.com search)
**Type:** Anthropic engineering blog

`[summary]`

Topics covered (paraphrased):
- Tool design heuristics: one tool = one action; tools should fail loudly; schemas should be tight.
- Evaluation-driven tool development; grounding evals in real-world use cases; agent-aided analysis of failure modes.
- Naming + descriptions matter — the agent reads them as part of its decision.

**Top-quotable passages (flagged):**

1. "Evaluation-driven tool development" — Anthropic-endorsed methodology.
2. One-tool-one-action principle.

### D.9c Citations API announcement (January 2025)

**URL:** https://claude.com/blog/introducing-citations-api (or anthropic.com equivalent — January 2025)
**Date:** January 2025
**Type:** Anthropic product blog

**Faithful excerpts (paraphrased; cite URL for verbatim):**

> Citations: server-side sentence chunking of source documents; Claude is given chunks; Claude generates output with citation markers pointing at chunks.

> "Trained to resist fabricating sources … more likely to acknowledge uncertainty or decline to cite."

> Cited text "will reference source documents to minimize hallucinations."

Available via direct Anthropic API + Vertex AI + Bedrock.

**Top-quotable passages (flagged):**

1. "Trained to resist fabricating sources" — Anthropic's soft guarantee. NOT a byte-level enforcement.
2. The chunk-pointer mechanism — the closest Anthropic-documented primitive for grounded output.

---

## D.10 Anthropic threat-intel posts (2024–2026 series, beyond GTG-1002)

`[summary]`

Anthropic publishes recurring threat-intel posts under `anthropic.com/news` covering: misuse patterns, agentic abuse cases, model-capability evaluations from a misuse perspective, and ecosystem-defense steps. GTG-1002 (C.1) is the keystone. When downstream agents need to cite an Anthropic threat-intel post, search `anthropic.com/news` for the specific incident name.

---

# Part E — Academic Paper Abstracts + Key Findings

For each paper: bibliographic citation, faithful abstract excerpt (or `[summary]` when full abstract is not safe to reproduce), and a 5-bullet key-findings list. URLs are canonical.

---

## E.1 DFIR-Metric — A Benchmark Dataset for Evaluating LLMs in DFIR

**Citation:** arXiv:2505.19973 (v1, May 2025)
**URL:** https://arxiv.org/abs/2505.19973 (HTML mirror: arxiv.org/html/2505.19973v1)
**Type:** benchmark paper

**Abstract excerpt (paraphrased — cite arXiv for verbatim):**

The paper introduces DFIR-Metric, a benchmark for evaluating LLMs on digital-forensics tasks. Three modules: (I) 700 expert-reviewed MCQs from professional certifications; (II) 150 realistic CTF-style challenges; (III) 500 practical NIST-derived disk/memory image cases. 14 leading LLMs tested. Introduces the **Task Understanding Score (TUS)** for evaluating near-zero-accuracy models. Best model: GPT-4.1 with 92.75% on Module I; **0% complete solutions** on Module III.

**Key findings (5 bullets):**

1. **0% complete solutions on Module III** (practical disk/memory cases) — even the best model fails the hard practical task.
2. Models "hallucinate files, bash commands, paths or libraries that are absent from the image" — direct hallucination of nonexistent evidence.
3. Module I (theory MCQ) accuracy plateaus around 92%; the model frontier is not theory.
4. Task Understanding Score introduced for evaluating models whose end-to-end accuracy is near zero — they may understand the task while failing to execute it.
5. The gap between knowing-what-to-do and being-able-to-do-it is the open problem in DFIR LLMs.

**Top-quotable passages (flagged):**

- "Hallucinate files, bash commands, paths or libraries that are absent from the image."
- "0% complete solutions on Module III."

---

## E.2 CyberSleuth — Autonomous Blue-Team LLM Agent for Web Attack Forensics

**Citation:** arXiv:2508.20643 (August 2025)
**URL:** https://arxiv.org/abs/2508.20643
**Type:** multi-agent benchmark paper

**Abstract excerpt (paraphrased):**

CyberSleuth proposes 3 agent architectures × 6 LLM backends evaluated on 30 controlled web-attack forensics cases. Best result: 80% accuracy with GPT-5 / DeepSeek R1. Acknowledges "long-term reasoning, contextual memory, consistent evidence correlation" as open problems.

**Key findings (5 bullets):**

1. Best system: 80% accuracy across 30 cases.
2. Multi-agent specialisation is key to sustained reasoning.
3. Simple orchestration outperforms nested hierarchical architectures.
4. Architecture matters more than model choice past a baseline.
5. Open problems: long-term reasoning, contextual memory, evidence correlation across artifacts.

**Top-quotable passages (flagged):**

- "Multi-agent specialisation is key to sustained reasoning."
- "Simple orchestration outperforms nested hierarchical architectures."

---

## E.3 Digital Forensics in the Age of Large Language Models

**Citation:** arXiv:2504.02963 (April 2025)
**URL:** https://arxiv.org/abs/2504.02963 (HTML: arxiv.org/html/2504.02963v1)
**Type:** survey paper

**Abstract excerpt (paraphrased):**

Survey + framework paper on LLM use in digital forensics. Catalogs 4 major limitations: hallucination, non-determinism, prompt sensitivity, and the absence of chain-of-custody / standards.

**Key findings (5 bullets):**

1. Hallucination is the #1 named limitation for forensic deployment.
2. Non-determinism undermines reproducibility — LLMs are probabilistic and may produce variable outputs on the same input.
3. Prompt sensitivity makes findings fragile to phrasing changes.
4. No accepted forensic-grade chain-of-custody standard for AI-derived evidence.
5. Human-in-loop + grounding recommended as direction, but no architectural solution proposed.

**Top-quotable passages (flagged):**

- "Non-determinism undermines reproducibility — LLMs are inherently probabilistic and may produce variable outputs."
- The 4-limitation list is the canonical taxonomy.

---

## E.4 Is the DFIR Pipeline Ready for Text-Based Threats in the LLM Era?

**Citation:** arXiv:2407.17870
**URL:** https://arxiv.org/abs/2407.17870
**Type:** position / evaluation paper

**Abstract excerpt (paraphrased):**

The DFIR pipeline is NOT ready for NTG-authored (neural-text-generator) text threats. The paper introduces a CS-ACT (Conversation-Style Authorship-Camouflage Test) attack that exploits "model sophistication and lack of distinctive style." Tests DFIR text-attribution pipelines and finds them fragile to LLM-generated content.

**Key findings (5 bullets):**

1. Pipeline gaps when adversary authored content with an LLM.
2. Style-based attribution becomes unreliable under high-quality NTG output.
3. CS-ACT attack illustrates fragility on a benchmark.
4. Adversarial content is the LLM-era equivalent of anti-forensics.
5. Recommends pipeline updates: provenance-aware attribution, behavioural signals beyond style.

---

## E.5 Chances and Challenges of MCP in DFIR

**Citation:** arXiv:2506.00274 v1 (June 2025)
**URL:** https://arxiv.org/abs/2506.00274
**Type:** survey + position paper

**Abstract excerpt (paraphrased):**

Surveys MCP (Model Context Protocol) for DFIR use cases. Discusses provenance / audit logging as a forensic primitive that MCP servers naturally produce. Surveys early MCP-DFIR projects.

**Key findings (5 bullets):**

1. MCP's structured-tool-call pattern naturally produces audit-trail-grade logs.
2. Provenance + per-call audit_id is a forensic primitive.
3. Early DFIR-MCP projects exist but lack content-attestation (claim-vs-output verification).
4. Open challenges: prompt injection from tool output, long-session context rot, multi-tenant isolation.
5. MCP is recommended as the substrate for AI-assisted DFIR going forward.

**Top-quotable passages (flagged):**

- "MCP's structured-tool-call pattern naturally produces audit-trail-grade logs."

---

## E.6 Multi-Agent Collaboration in Incident Response with LLMs

**Citation:** arXiv:2412.00652 (December 2024)
**URL:** https://arxiv.org/abs/2412.00652
**Type:** multi-agent IR architecture paper

**Abstract excerpt (paraphrased):**

Proposes a multi-agent LLM workflow for incident-response coordination. Demonstrates specialization by IR phase (identification, containment, eradication, recovery). Discusses inter-agent communication and HITL integration.

**Key findings (5 bullets):**

1. Specialization by IR phase improves on monolithic agent baseline.
2. Inter-agent message logs serve as audit trail.
3. HITL integration is a design parameter, not optional.
4. Token-budget management across agents is non-trivial.
5. No architectural anti-hallucination beyond per-phase prompting.

---

## E.7 NABAOS — Tool Receipts, Not Zero-Knowledge Proofs

**Citation:** arXiv:2603.10060 (March 2026)
**URL:** https://arxiv.org/abs/2603.10060
**Type:** agent-safety architecture paper

**Abstract excerpt (paraphrased):**

NABAOS introduces runtime-generated HMAC-signed tool-execution receipts that the LLM cannot forge. The receipts are cross-referenced against LLM claims to detect fabricated tool references, count misstatements, and false-absence claims. Reports detection rates of 94.2% / 87.6% / 91.3% across categories. <15ms verification overhead per response. Frames as post-hoc detection with epistemic-source classification.

**Key findings (5 bullets):**

1. HMAC-signed execution receipts catch fabricated tool calls.
2. Detection rates: ~94% (fabricated tool references), ~88% (count misstatements), ~91% (false absence).
3. <15ms verification overhead per LLM response.
4. Operates as post-hoc detection, not hard runtime rejection.
5. Signs the EXECUTION (that a tool was called); does NOT byte-substring-check the CONTENT of the tool's output against the LLM's claim.

**Top-quotable passages (flagged):**

- "HMAC-signed tool execution receipts the LLM cannot forge."
- "94.2% / 87.6% / 91.3%" detection rates.

---

## E.8 CiteCheck — Accurate Citation Faithfulness Detection

**Citation:** arXiv:2502.10881 (February 2025)
**URL:** https://arxiv.org/abs/2502.10881
**Type:** RAG citation-verification paper

**Abstract excerpt (paraphrased):**

Decomposes an LLM answer into atomic claims and checks each against its cited passage. Framed as a detection benchmark + dataset.

**Key findings (5 bullets):**

1. Atomic-claim decomposition + per-claim citation check.
2. Detection-oriented, not enforcement-oriented.
3. Benchmark dataset released.
4. Substring + semantic-similarity hybrid for matching.
5. Demonstrates measurable improvement over naive citation alignment.

---

## E.9 RetroLLM — Empowering LLMs to Retrieve Fine-grained Evidence within Generation

**Citation:** arXiv:2412.11919 (December 2024)
**URL:** https://arxiv.org/abs/2412.11919
**Type:** retrieval-augmented generation paper

**Abstract excerpt (paraphrased):**

Constrained decoding so generated tokens come from the corpus via a hierarchical FM-Index constraint. Token-level enforcement at decoding time.

**Key findings (5 bullets):**

1. Token-level decoding constraint — generated text bound to corpus content.
2. Operates at training/decoding time, not as a runtime post-hoc gate.
3. Improves grounding metrics over standard retrieval-augmented generation.
4. Reduces hallucination by construction (tokens must exist in the corpus index).
5. Tradeoff: less generation fluency when corpus is sparse.

---

## E.10 Span-Level Hallucination Detection for LLM-Generated Answers

**Citation:** arXiv:2504.18639 (April 2025)
**URL:** https://arxiv.org/abs/2504.18639
**Type:** hallucination-detection paper

**Abstract excerpt (paraphrased):**

Decomposes LLM answers via Semantic Role Labeling, compares atomic roles against the reference text. Detection benchmark.

**Key findings (5 bullets):**

1. Semantic Role Labeling-based decomposition.
2. Per-span hallucination labeling.
3. Detection benchmark — not enforcement.
4. Outperforms naive sentence-level approaches.
5. Useful upstream of any RAG-citation gate.

---

## E.11 SymGen — Verifiable Text Generation with Symbolic References

**Citation:** arXiv:2311.09188 (November 2023)
**URL:** https://arxiv.org/abs/2311.09188
**Type:** verifiable-generation paper

**Abstract excerpt (paraphrased):**

LLM interleaves symbolic references to JSON conditioning data so humans can verify spans against the source. Streamlines human verification.

**Key findings (5 bullets):**

1. Symbolic-reference interleaving in generation output.
2. Conditioning data in structured (JSON) form.
3. Advisory verification (human-facing), not auto-gating.
4. Improves verification ergonomics over plain citations.
5. Compatible with downstream substring / semantic checks.

---

## E.12 InteGround

**Citation:** arXiv:2509.16534 (September 2025)
**URL:** https://arxiv.org/abs/2509.16534
**Type:** grounding + retrieval-planning paper

**Abstract excerpt (paraphrased):**

Studies retrieval + verification PLANNING for integrative grounding. Measures rather than prevents. Key finding: "LLMs rationalize using internal knowledge when grounding is incomplete."

**Key findings (5 bullets):**

1. Integrative grounding (multi-source) is fragile when retrieval is incomplete.
2. LLMs rationalize from training data when grounding gaps appear.
3. Planning-aware retrieval reduces the gap.
4. Measurement framework released.
5. Confirms why architectural prevention (not just measurement) matters.

**Top-quotable passages (flagged):**

- "LLMs rationalize using internal knowledge when grounding is incomplete."

---

## E.13 Verifiable Generation with Subsentence-Level Fine-Grained Citations

**Citation:** arXiv:2406.06125 (June 2024)
**URL:** https://arxiv.org/abs/2406.06125
**Type:** verifiable-generation paper

**Abstract excerpt (paraphrased):**

Studies subsentence-level citations for precise localization. Measurement-oriented; doesn't deploy as runtime gate.

**Key findings (5 bullets):**

1. Subsentence-granularity citations.
2. Measurement framework.
3. More precise than sentence-level baselines.
4. Compatible with downstream verification gates.
5. Tradeoff: more annotation cost during training.

---

## E.14 Lost in the Middle (Liu et al.)

**Citation:** Liu, N. F., et al. (2023). "Lost in the Middle: How Language Models Use Long Contexts." arXiv:2307.03172
**URL:** https://arxiv.org/abs/2307.03172
**Type:** LLM behavior paper

**Abstract excerpt (paraphrased):**

Documents the "lost-in-the-middle" effect — LLMs perform best when relevant information is at the beginning or end of the context window, and worst when it's in the middle. Measured across multiple long-context tasks.

**Key findings (5 bullets):**

1. U-shaped attention pattern across context-window positions.
2. Middle-of-context information is under-attended.
3. Effect persists across model scales.
4. Has direct implications for system-prompt + tool-output ordering.
5. Critical for any agent doing long investigations (FOR508-scale cases).

**Top-quotable passages (flagged):**

- "Lost in the middle" — the canonical name. Use when discussing long-context degradation.

---

## E.15 Sycophancy paper (Sharma et al.)

**Citation:** Sharma, M., et al. (2023). "Towards Understanding Sycophancy in Language Models." arXiv:2310.13548
**URL:** https://arxiv.org/abs/2310.13548
**Type:** LLM behavior paper

**Abstract excerpt (paraphrased):**

Documents LLM sycophancy — the tendency to agree with users even when users are wrong. Catalogs sycophancy across model families and training stages.

**Key findings (5 bullets):**

1. Sycophancy emerges from preference-data training.
2. Models will reverse correct answers when pushed back on.
3. Effect persists across model scales.
4. Has direct implications for HITL workflows where examiner pushes back on a draft finding.
5. Mitigation: require independent re-derivation rather than confirmation requests.

**Top-quotable passages (flagged):**

- The sycophancy finding informs critique-loop design — pushing back can flip a correct finding to a wrong one if not architected carefully.

---

# Part F — MCP Spec Excerpts

The Model Context Protocol specification — the substrate for nearly every credible Find Evil! submission.

---

## F.1 modelcontextprotocol.io — core sections

**Canonical URL:** https://modelcontextprotocol.io/
**Spec repo:** https://github.com/modelcontextprotocol/specification
**Type:** open-standard protocol specification

**Key sections referenced by downstream:**

### F.1.a Transport
- **stdio transport** — JSON-RPC over subprocess pipes. Default for local/co-resident servers.
- **Streamable HTTP transport** — JSON-RPC over HTTP with optional streaming. Default for remote/networked servers.
- Both transports use JSON-RPC 2.0 framing.

### F.1.b Lifecycle
- Client connects → `initialize` request → server `initialize` response with capabilities → `notifications/initialized` → ready for tool/resource/prompt calls → `shutdown` notification.
- Capabilities negotiated at initialize: tools/resources/prompts/sampling/roots/logging.

### F.1.c Tools
- `tools/list` — enumerate available tools.
- `tools/call` — invoke a tool with input matching `inputSchema`.
- Output: `content` array (text/image/resource), and optional `structuredContent` for typed output.
- Errors surfaced as `CallToolResult.isError = true`.

### F.1.d Resources
- `resources/list` — enumerate resources by URI.
- `resources/read` — fetch resource content.
- `resources/subscribe` + `resources/unsubscribe` — server-pushed updates.
- Resources are read-only by spec; tools mutate.

### F.1.e Prompts
- `prompts/list` + `prompts/get` — server-supplied prompt templates.
- Prompts take arguments and return message-list payloads.

### F.1.f Sampling
- `sampling/createMessage` — server requests the client (LLM) to sample. Enables server-driven workflows.
- Optional capability; not all clients implement it.

### F.1.g Roots
- `roots/list` — server queries client for the workspace roots it's allowed to operate on.
- The closest spec-defined boundary for "filesystem scope."

### F.1.h Logging
- `logging/setLevel` — client controls server log verbosity.
- Servers emit `notifications/message` for log entries.

### F.1.i Cancellation
- `notifications/cancelled` — either side can cancel an in-flight request by request ID.

### F.1.j Progress
- `notifications/progress` — long-running operations report progress (current/total, optional message).

**Top-quotable passages (flagged):**

1. JSON-RPC 2.0 over stdio or Streamable HTTP — the substrate.
2. Capability negotiation at initialize — the spec's extensibility mechanism.
3. The tools-vs-resources distinction (mutating vs read-only) — quote when designing forensic-tool wrappers.
4. Sampling — the server-asks-the-LLM primitive that lets the MCP server drive a workflow.

---

## F.2 MCP Python SDK README — key sections

**URL:** https://github.com/modelcontextprotocol/python-sdk
**Type:** SDK README

**Faithful excerpts (paraphrased — fetch URL for verbatim):**

- Two API levels: high-level **FastMCP** (decorators) and low-level **Server** (explicit handlers, more control).
- `@mcp.tool()` decorator generates inputSchema + outputSchema from Pydantic types.
- `Context` object available in tools for progress reporting, logging, sampling.
- Transport: `mcp.run()` defaults to stdio; HTTP transport available.

Minimal FastMCP example pattern (illustrative):

```python
from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field

mcp = FastMCP("server-name")

class Result(BaseModel):
    field: str

@mcp.tool()
async def my_tool(arg: str, ctx: Context) -> Result:
    await ctx.info(f"processing {arg}")
    return Result(field=arg)

if __name__ == "__main__":
    mcp.run()
```

**Top-quotable passages (flagged):**

1. FastMCP-vs-Server API level choice — the design knob.
2. Pydantic-typed I/O — the contract-by-type guarantee.
3. `Context` for progress/log/sampling — the long-running-tool primitive.

---

## F.3 MCP TypeScript SDK README — key sections

**URL:** https://github.com/modelcontextprotocol/typescript-sdk
**Type:** SDK README

`[summary]`

The TS SDK mirrors the Python SDK shape with TypeScript types instead of Pydantic. Both stdio and Streamable HTTP transports. Used in Claude Desktop, LibreChat, and various web-based MCP clients.

**Top-quotable passages (flagged):**

1. Cross-language parity — same MCP server can be implemented in Python or TS.
2. The TS SDK is the canonical entry for browser-side / web-based MCP clients.

---

# Part G — Pydantic Instructor + NABAOS Pattern

The two pieces of prior art most relevant to citation-verification gates for forensic findings. Both must be cited if a Find Evil! submission claims novel citation-verification architecture.

---

## G.1 Instructor — "Validating Citations" blog post

**URL:** https://python.useinstructor.com/blog/2023/11/18/validate-citations/
**Date:** November 18, 2023
**Type:** OSS library blog post
**Author:** Jason Liu (jxnl)

**Faithful excerpts (paraphrased — cite URL for verbatim):**

The post demonstrates Pydantic + Instructor citation validators:
- Pydantic `@field_validator` checks `if v in text_chunk` — substring check on every quoted citation.
- Raises `ValueError` on mismatch → hard rejection at parse time.
- Same post shows an LLM-judge variant for semantic alignment.
- GitHub: `jxnl/instructor` (~8K stars as of 2025).

Illustrative pattern (paraphrased; exact code at the URL):

```python
class Citation(BaseModel):
    quote: str
    source: str

    @field_validator("quote")
    def quote_must_appear_in_source(cls, v, info):
        text_chunk = info.context.get("source_text", "")
        if v not in text_chunk:
            raise ValueError(f"Citation quote not found in source")
        return v
```

**Top-quotable passages (flagged):**

1. **`if v in text_chunk`** — the substring-check pattern in one line.
2. Hard rejection at parse time via `ValueError`.
3. Demonstrates that substring-validated citations are a known SDK pattern, not a novel forensics invention.
4. The Instructor library + jxnl-stars-count establishes this as widely deployed prior art.

---

## G.2 NABAOS arxiv abstract + key claims (recap with citation-mechanism specifics)

**Citation:** arXiv:2603.10060 (March 2026)
**URL:** https://arxiv.org/abs/2603.10060
**Type:** agent-safety architecture paper

**Detailed mechanism (paraphrased — cite arXiv for verbatim):**

- Runtime generates HMAC-signed tool execution **receipts** the LLM cannot forge.
- Cross-references LLM claims against receipts to detect:
  - Fabricated tool references (LLM claims it called tool X when it didn't).
  - Count misstatements (LLM claims N results when there were M).
  - False absence claims (LLM claims a tool returned nothing when it returned something).
- Detection rates: 94.2% / 87.6% / 91.3%.
- <15ms verification overhead per response.
- Post-hoc detection model, not hard runtime rejection gate.
- Frames as **execution attestation** (a tool was called) — NOT **content attestation** (the LLM's textual claim about the tool output matches the actual bytes).

**Top-quotable passages (flagged):**

1. "HMAC-signed tool execution receipts the LLM cannot forge."
2. "94.2% / 87.6% / 91.3%" detection rates.
3. The execution-vs-content attestation distinction — load-bearing if your wedge is content-attestation.

---

# Part H — Hackathon Official Material

---

## H.1 findevil.devpost.com/rules — official rules

**URL:** https://findevil.devpost.com/rules
**Type:** official hackathon rules
**Sponsor:** SANS Institute

**Key sections (paraphrased — cite Devpost URL for verbatim):**

- Eligibility: solo or team.
- Submission deadline: June 15, 2026 11:45 PM EDT.
- Judging: June 19 – July 3, 2026. Winners announced ~July 8.
- License: MIT or Apache 2.0 — no other licenses permitted.

**8 mandatory submission items (per rules §4):**

1. Public GitHub repository (open-source MIT or Apache 2.0).
2. Demo video (max 5 minutes) with **live terminal execution**.
3. Architecture diagram showing **security boundaries and enforcement mechanisms**.
4. Devpost-format written description.
5. **Dataset documentation** with test sources.
6. **Accuracy report addressing false positives and evidence integrity**.
7. Deployment/setup instructions for judges.
8. **Structured agent execution logs with timestamps**.

**Supported architectural approaches:**
- Direct Agent Extension (Claude Code or OpenClaw enhancements).
- Custom MCP Server.
- Multi-Agent Frameworks (AutoGen, CrewAI, LangGraph).
- Alternative Agentic IDEs (Cursor, Cline, Aider).

**Constraints:**
- Build on or integrate with the SANS SIFT Workstation.
- Linux terminal environment.
- Demonstrate self-correction, accuracy validation, and analytical reasoning.
- Substantially new work built April 15 – June 15, 2026 (pre-existing libraries and SIFT codebase OK as foundation).

**Top-quotable passages (flagged):**

1. The 8-item submission list — table-stakes verbatim. Match each.
2. "Live terminal execution" — must be visible in the demo.
3. "Security boundaries and enforcement mechanisms" — the language the architecture diagram must use.
4. "Accuracy report addressing false positives and evidence integrity" — the accuracy report scope.

---

## H.2 findevil.devpost.com — Devpost overview

**URL:** https://findevil.devpost.com/
**Type:** Devpost hackathon landing page

**Faithful excerpts (verbatim):**

> "AI threats strike in minutes. Build the defender that responds in seconds." (tagline)

> Total prize pool $22,000+ ($10K / $7.5K / $4.5K cash + Summit pass + OnDemand + broadcast slot).

> 3,861 registered participants (as of 2026-06-02).

> Find Evil! challenges you to close [the speed gap].

**Top-quotable passages (flagged):**

1. **The tagline.** "AI threats strike in minutes. Build the defender that responds in seconds." Use in any title/header.
2. Prize structure — informs whether to target a track or main.
3. 3,861 registered — the visible-field size.

---

## H.3 findevil.devpost.com/resources — official resources

**URL:** https://findevil.devpost.com/resources
**Type:** Devpost resources page

`[summary — official links page]`

Lists:
- Slack invite: `https://join.slack.com/t/sansaihackathon/shared_invite/zt-3zhbphvt0-3mMkKpBeUvll1DYwnr1yOA`
- Discord: `https://discord.com/invite/HP4BhW3hnp`
- SIFT Workstation: `sans.org/tools/sift-workstation`
- Protocol SIFT install: `curl -fsSL https://raw.githubusercontent.com/teamdfir/protocol-sift/main/install.sh | bash`
- Starter case data (private Egnyte): `https://sansorg.egnyte.com/fl/HhH7crTYT4JK`
- Protocol SIFT NotebookLM: `https://notebooklm.google.com/notebook/f0957a60-6fb2-452b-93d4-ecd73ba47779?authuser=1`
- Help email: `aihackathon@sans.org`
- Reference implementation: AppliedIR/Valhuntir as "the level of quality to meet or exceed."

**Top-quotable passages (flagged):**

1. The "Valhuntir as the quality bar" framing — the explicit anchor.
2. The install one-liner — judges will run this.

---

## H.4 Protocol SIFT NotebookLM (link only — content gated)

**URL:** https://notebooklm.google.com/notebook/f0957a60-6fb2-452b-93d4-ecd73ba47779?authuser=1
**Type:** Google NotebookLM shared notebook (likely contains aggregated DFIR + Protocol SIFT docs the judges trained on)

**Status:** content gated; link only. Judges likely treat this as their shared mental model. When uncertain about whether something is in scope, check whether the source URL appears in this notebook via the Slack.

---

## H.5 SIFT Workstation page

**URL:** https://www.sans.org/tools/sift-workstation
**Type:** SANS tool page

`[summary — page text paraphrased]`

The page describes SIFT Workstation as a free Ubuntu-based DFIR distro maintained by SANS DFIR Faculty. "200+ forensic tools" pre-installed. Latest build: Ubuntu 22.04 Jammy (Feb 2024). Maintained by `teamdfir` org via SaltStack (`teamdfir/sift-saltstack`). Install via Cast (`sudo cast install teamdfir/sift-saltstack`). Available as Ubuntu install, OVA, AMI, and Docker.

Notable original framing: SIFT created ~2007 by Rob T. Lee for court-admissible investigations.

**Top-quotable passages (flagged):**

1. "200+ forensic tools" — the marketing number. Use sparingly.
2. SIFT-as-court-admissible-platform — Rob's lineage. Inform the cryptographic / chain-of-custody choices you make.

---

# Part I — Notable Practitioner Voices

For each practitioner: 3–5 quotable passages relevant to the wedge.

---

## I.1 Brett Shavers — `brettshavers.com`

**Type:** DFIR practitioner blog

**Faithful excerpts (verbatim from cited posts):**

> "Tool training is tool training. Don't expect it to teach you forensics. Education in forensics is forensic education. Don't expect it to teach you tools."
> — *Raising the Bar: Establishing a Common Baseline in DFIR*, https://brettshavers.com/brett-s-blog/entry/raising-the-bar-establishing-a-common-baseline-in-dfir

> "AI accelerates confident mistakes… It can't be accountable… What it can't do is reliably decide what artefacts mean in context, or whether the story it is telling matches the evidence at all."
> — *Why AI Will Replace Every DFIR Tool Operator by 2027*, https://brettshavers.com/brett-s-blog/entry/ai-wont-replace-df-ir-but-it-will-replace-the-non-df-ir-investigators

> "It's easy to use a documentation system before you begin working a case. It's impossible to start one after your case is done."
> — quoted in Josh Brunty's *Writing DFIR Reports* primer

**Top-quotable passages (flagged):**

1. "Tools do not equal analytical knowledge." (paraphrased into a one-liner; original full quote above).
2. "AI accelerates confident mistakes." — quote in any "honest about limits" section.
3. "Can't be accountable" — informs the human-final-authority frame.

---

## I.2 Mari DeGrazia — Forensic 4cast / Another Forensics Blog

**URL:** https://az4n6.blogspot.com/ (Another Forensics Blog)
**Type:** DFIR practitioner blog

`[summary]`

DeGrazia is a longtime DFIR practitioner whose blog covers Windows artifacts deep-dives (browser history, registry artifacts, ShellBags, EventLogs). Her posts emphasize artifact-mechanics over tool-output trust — the same investigator-vs-operator pattern as Shavers. No specific verbatim quotes surfaced in research subagent runs; cite specific posts directly when needed.

**Top-quotable passages (flagged):**

1. The artifact-deep-dive style is the model for any agent's "how do you actually interpret this output" doc.

---

## I.3 Harlan Carvey — Windows Incident Response blog

**URL:** http://windowsir.blogspot.com/
**Type:** DFIR practitioner blog

**Faithful excerpts (verbatim from cited posts):**

> "And at this point, I'm not even talking about hallucinations, just models being trained with incorrect information."
> — *The Role of AI in DFIR*, http://windowsir.blogspot.com/2025/02/the-role-of-ai-in-dfir.html

`[summary]` Carvey's wider blog covers RegRipper development, Windows artifact parsers, and IR methodology. His framing on AI: training-data quality is a different and arguably harder problem than runtime hallucination.

**Top-quotable passages (flagged):**

1. The training-data-quality framing — informs any "we cite verified-deterministic-tool-output" pitch.
2. Carvey is the RegRipper author — quote when discussing registry-artifact parsing.

---

## I.4 Lesley Carhart — tisiphone.net

**URL:** https://tisiphone.net/
**Type:** DFIR / IR / OT-security practitioner blog
**Author:** Lesley Carhart (Dragos, formerly Motorola)

`[summary]`

Carhart writes on IR career paths, OT/ICS forensics, and the human side of incident response (burnout, on-call rotations, post-incident dynamics). Her voice is grounded in active IR engagements. No specific verbatim quote surfaced in research subagent runs; cite individual posts directly when needed.

**Top-quotable passages (flagged):**

1. The human-side framing is useful for the "the senior analyst is the customer" framing.

---

## I.5 Andrew Case — Volatility Foundation

**URL:** https://volatility-labs.blogspot.com/ (Volatility Labs)
**Type:** memory-forensics blog
**Author:** Andrew Case (Volatility Foundation core team)

`[summary]`

Case is a core developer of Volatility 3. Blog covers plugin development, memory-forensics methodology, and rootkit detection patterns. Authoritative source on Volatility plugin behavior.

**Top-quotable passages (flagged):**

1. Case-authored posts are the canonical reference for Volatility plugin semantics — cite when designing memory-forensics tool wrappers.

---

## I.6 Brian Carrier — Sleuth Kit + Cyber Triage

**URL:** https://www.cybertriage.com/about/
**Type:** vendor blog + tool maker (Sleuth Kit, Autopsy, Cyber Triage)

**Faithful excerpts (verbatim):**

> "It's not enough to just collect lots of data. Investigators need their tools to also reduce the data to the small subset that is relevant."
> — Brian Carrier, *About Cyber Triage*, https://www.cybertriage.com/about/

`[summary]` Carrier has also published a 7-principle "AI doctrine" for forensic tools. Principle #6 (paraphrased): "Verify generative AI: cross-check structured data against source evidence." Principle #7 (paraphrased): AI should "attempt to both refute and support its hypotheses." Principles #3 + #4 (paraphrased): explainability + disclose non-determinism.

**Top-quotable passages (flagged):**

1. **"Reduce the data to the small subset that is relevant."** Carrier's volume-problem framing.
2. Carrier's 7-principle AI doctrine — the closest thing to a public forensic-AI standard from a respected tool vendor.

---

## I.7 DFIR Diva

**URL:** https://www.dfirdiva.com/
**Type:** DFIR career / training blog

`[summary]`

DFIR Diva catalogues free DFIR training, career advice, and entry-into-the-field guides. The audience is junior + aspiring DFIR practitioners. Her voice represents the training-gap pain that senior practitioners (Shavers, Knutson) name. No specific verbatim quote surfaced; cite individual posts directly when needed.

**Top-quotable passages (flagged):**

1. The "training cost" framing — SANS courses run ~$8K. Cite when discussing why junior-training is a real pain.

---

## I.8 13Cubed — Richard Davis

**URL:** https://www.13cubed.com/
**Type:** DFIR video training / YouTube channel

`[summary]`

13Cubed is Richard Davis's video-format DFIR training. Topics: Windows internals, memory forensics, network forensics, tool walkthroughs. Audience overlap with FOR500/FOR508 students. Davis's content models the senior-analyst "walk through artifact-by-artifact" methodology. No specific verbatim quote surfaced; cite individual videos directly when needed.

**Top-quotable passages (flagged):**

1. The walkthrough-style methodology is the implicit benchmark for any "explainable agent" demo.

---

## I.9 Additional practitioner voices cited in research

For completeness, the following are quoted in research subagent material with verbatim attributions:

- **Tony Knutson (SANS DFIR Summit 2025 keynote):** "Tools do not equal analytical knowledge." Recapped at https://www.sans.org/blog/2025-sans-dfir-summit-recap-human-element
- **Josh Brunty (Marshall University):** "A process that should have taken a few weeks took months and hours of fruitless searches… everything should distilled down to make sense to 'your 80 old grandmother.'" — *Writing DFIR Reports: A Primer*, https://joshbrunty.github.io/2021/01/27/reporting.html
- **DFIR Training editorial line:** "Plenty of practitioners can operate tools, generate timelines, and produce reports that look professional while still being a liability to the case." — https://www.dfir.training/blog/a-word-on-dfir-credentials
- **SANS Report Writing for Digital Forensics Part II:** "Explaining certain forensic terminology in a non-technical manner can be difficult even for the most seasoned examiner." — https://www.sans.org/blog/report-writing-for-digital-forensics-part-ii
- **Magnet Forensics:** "If an AI-enabled tool does not disclose how it came to a result in the way an end user can explain in court, the use of that tool may be inadmissible in legal proceedings." — https://www.magnetforensics.com/blog/evaluating-the-use-of-ai-in-digital-evidence-and-courtroom-admissibility/
- **Ovie Carroll** (judge / DOJ CCIPS / SANS FOR500 co-author): "Digital devices are silent witnesses. The Digital Investigative Analyst acts as their voice, meticulously translating the data into an objective narrative." — public-statement excerpt. Also: "Through meticulous examination, they extract the unvarnished story from electrons, a chronicle free from bias or embellishment."

---

# Appendix — Canonical URL Bibliography

Rapid lookup for downstream agents. URLs verified by research subagents at 2026-06-02.

**Rob T. Lee:**
- Substack root: https://robtlee73.substack.com/
- Introducing Protocol SIFT: https://robtlee73.substack.com/p/introducing-protocol-sift-meeting
- Registration is OPEN: https://robtlee73.substack.com/p/registration-is-open-find-evil-hackathon
- [un]prompted talk: https://robtlee73.substack.com/p/dangerous-new-attack-techniques-rsac-2026-preview-protocol-sift
- Why 47?: https://robtlee73.substack.com/p/why-47-the-math-behind-ai-attacks
- AI Isn't a Tool: https://robtlee73.substack.com/p/ai-isnt-a-tool-anymore-its-an-operator
- [un]prompted YouTube: https://www.youtube.com/watch?v=OsUg3TlAqjQ (alt cut: https://www.youtube.com/watch?v=oHDnEnx_zhg)
- X handle: https://x.com/robtlee

**SANS:**
- Protocol SIFT blog: https://www.sans.org/blog/protocol-sift-experimental-research-initiative-ai-assisted-dfir
- Two Words press release: https://www.sans.org/press/announcements/two-words-changed-cybersecurity-find-evil-builders-answer-call-defend-infrastructure
- Launch blog: https://www.sans.org/blog/sans-launches-first-hackathon-autonomous-incident-response
- SIFT Workstation: https://www.sans.org/tools/sift-workstation
- FOR508: https://www.sans.org/cyber-security-courses/advanced-incident-response-threat-hunting-training
- FOR500: https://www.sans.org/cyber-security-courses/windows-forensic-analysis
- FOR526: https://www.sans.org/cyber-security-courses/advanced-memory-forensics-threat-detection

**Steve Anson / Valhuntir:**
- Valhuntir repo: https://github.com/AppliedIR/Valhuntir
- AppliedIR org: https://github.com/AppliedIR
- sift-mcp: https://github.com/AppliedIR/sift-mcp
- AppliedIR consultancy: https://appliedincidentresponse.com/
- Informed Defense: https://informeddefense.com/
- Anson SANS profile: https://www.sans.org/profiles/steve-anson

**GTG-1002 / Anthropic:**
- GTG-1002 blog post: https://www.anthropic.com/news/disrupting-AI-espionage
- GTG-1002 PDF: https://assets.anthropic.com/m/ec212e6566a0d47/original/Disrupting-the-first-reported-AI-orchestrated-cyber-espionage-campaign.pdf
- Citations API: https://claude.com/blog/introducing-citations-api
- Building agents: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

**Industry reports:**
- CrowdStrike 2024 GTR press: https://www.crowdstrike.com/en-us/press-releases/2024-crowdstrike-global-threat-report-release/
- CrowdStrike GTR home: https://www.crowdstrike.com/global-threat-report/
- Mandiant M-Trends: https://www.mandiant.com/m-trends
- Verizon DBIR: https://www.verizon.com/business/resources/reports/dbir/
- Microsoft Digital Defense Report: https://www.microsoft.com/en-us/security/security-insider/intelligence-reports/microsoft-digital-defense-report

**Academic papers:**
- DFIR-Metric: https://arxiv.org/abs/2505.19973
- CyberSleuth: https://arxiv.org/abs/2508.20643
- Digital Forensics in the Age of LLMs: https://arxiv.org/abs/2504.02963
- DFIR Pipeline Ready for Text Threats: https://arxiv.org/abs/2407.17870
- MCP in DFIR: https://arxiv.org/abs/2506.00274
- Multi-Agent IR with LLMs: https://arxiv.org/abs/2412.00652
- NABAOS: https://arxiv.org/abs/2603.10060
- CiteCheck: https://arxiv.org/abs/2502.10881
- RetroLLM: https://arxiv.org/abs/2412.11919
- Span-level hallucination: https://arxiv.org/abs/2504.18639
- SymGen: https://arxiv.org/abs/2311.09188
- InteGround: https://arxiv.org/abs/2509.16534
- Subsentence-level citations: https://arxiv.org/abs/2406.06125
- Lost in the Middle: https://arxiv.org/abs/2307.03172
- Sycophancy: https://arxiv.org/abs/2310.13548

**MCP:**
- Spec: https://modelcontextprotocol.io/
- Python SDK: https://github.com/modelcontextprotocol/python-sdk
- TypeScript SDK: https://github.com/modelcontextprotocol/typescript-sdk

**Citation patterns:**
- Instructor validate-citations: https://python.useinstructor.com/blog/2023/11/18/validate-citations/

**Hackathon:**
- Devpost: https://findevil.devpost.com/
- Rules: https://findevil.devpost.com/rules
- Resources: https://findevil.devpost.com/resources
- Slack: https://join.slack.com/t/sansaihackathon/shared_invite/zt-3zhbphvt0-3mMkKpBeUvll1DYwnr1yOA
- Discord: https://discord.com/invite/HP4BhW3hnp
- NotebookLM: https://notebooklm.google.com/notebook/f0957a60-6fb2-452b-93d4-ecd73ba47779?authuser=1

**Practitioner blogs:**
- Brett Shavers: https://brettshavers.com/
- Mari DeGrazia: https://az4n6.blogspot.com/
- Harlan Carvey: http://windowsir.blogspot.com/
- Lesley Carhart: https://tisiphone.net/
- Volatility Labs (Andrew Case): https://volatility-labs.blogspot.com/
- Cyber Triage (Brian Carrier): https://www.cybertriage.com/
- DFIR Diva: https://www.dfirdiva.com/
- 13Cubed: https://www.13cubed.com/
- Josh Brunty: https://joshbrunty.github.io/
- DFIR Training: https://www.dfir.training/

---

**End of corpus.**

Downstream agents: when you need a quote not present here, fetch the canonical URL above. When you need a longer passage than what's reproduced here, fetch the canonical URL above. This document is the quotable index, not the long-form library.
