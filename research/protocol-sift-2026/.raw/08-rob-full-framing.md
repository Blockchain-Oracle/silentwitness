# Rob T. Lee — Full Problem Framing

> Validation research for the Find Evil! / Protocol SIFT 2026 wedge choice.
> Question being answered: **is hallucination Rob's #1 pain, or is it speed, sequencing, context rot, or something else?**
> Compiled 2026-06-02.

---

## Sources read (12 artifacts)

| # | Artifact | Date | Type | Quoted from |
|---|---|---|---|---|
| 1 | [Introducing Protocol SIFT: Meeting AI Threat Speed with Defensive AI Orchestration](https://robtlee73.substack.com/p/introducing-protocol-sift-meeting) | ~Jan 2026 | Substack post | Direct fetch |
| 2 | [Protocol SIFT: An Experimental Research Initiative for AI-Assisted DFIR](https://www.sans.org/blog/protocol-sift-experimental-research-initiative-ai-assisted-dfir) | ~Jan 2026 | SANS Blog | Direct fetch |
| 3 | [My talk at [un]prompted: SIFT - Find Evil! The Era of Autonomous Forensics](https://robtlee73.substack.com/p/dangerous-new-attack-techniques-rsac-2026-preview-protocol-sift) | Mar 2026 | Substack post | Direct fetch |
| 4 | [Why 47? The Math Behind "AI Attacks 47x Faster Than Humans"](https://robtlee73.substack.com/p/why-47-the-math-behind-ai-attacks) | Q1 2026 | Substack post | Direct fetch |
| 5 | [AI Isn't a Tool Anymore. It's an Operator.](https://robtlee73.substack.com/p/ai-isnt-a-tool-anymore-its-an-operator) | Q1 2026 | Substack post (SANS AI Summit notes) | Direct fetch |
| 6 | [Registration is OPEN: Find Evil! Hackathon](https://robtlee73.substack.com/p/registration-is-open-find-evil-hackathon) | Apr 2026 | Substack post | Direct fetch |
| 7 | [SIFT-FIND EVIL! I Gave Claude Code R00t on DFIR SIFT Workstation](https://www.youtube.com/watch?v=OsUg3TlAqjQ) | Mar 25, 2026 | YouTube ([un]prompted talk) | Full transcript via yt-dlp |
| 8 | [Claude Code + open source DFIR tools: SIFT Protocol](https://www.youtube.com/watch?v=oHDnEnx_zhg) | 2026 | YouTube (alt cut of same talk) | Full transcript |
| 9 | [Two Words That Changed Cybersecurity (SANS press release)](https://www.sans.org/press/announcements/two-words-changed-cybersecurity-find-evil-builders-answer-call-defend-infrastructure) | Apr 15, 2026 | SANS press release | Direct fetch |
| 10 | [Rob T. Lee on X — registration tweet](https://x.com/robtlee/status/2039476641903046820) | Apr 2026 | Tweet | Via search snippet (X gated 402) |
| 11 | [Rob T. Lee on X — "1,400 registered" tweet](https://x.com/robtlee/status/2044816200069230635) | Mar 2026 | Tweet | Via search snippet |
| 12 | [Rob T. Lee on X — unprompted preview tweet](https://x.com/robtlee/status/2027214405172089067) | Feb 2026 | Tweet | Via search snippet |

**Note on Substack home + X timeline:** Substack homepage didn't enumerate older posts via WebFetch; X is gated (HTTP 402). The 12 artifacts above are the verifiable Rob T. Lee voice corpus available. Hackathon-era Rob output is concentrated in this set.

---

## All distinct problem clusters

Counts are the number of distinct artifacts (out of 12) where the cluster appears named with non-trivial framing — not raw word counts. Quotes are verbatim.

| # | Cluster | Mentioned in N artifacts | Strongest verbatim quote | Source |
|---|---|---|---|---|
| **P1** | **Speed asymmetry / OODA gap** | **9/12** | "Defensive OODA loops are measured in hours while offensive loops are now measured in seconds. Defenders are out here bringing knives to a drone strike." | #1 Substack Introducing |
| **P2** | **Manual syntax / tool friction (cognitive load on analyst)** | **6/12** | "Analysts [were functioning as] command-line stenographers instead of investigators... memorizing that the correct invocation for parsing an MFT is `dotnet /usr/local/bin/MFTECmd.dll...` (a string that approximately zero humans can type correctly at 3 AM)." | #1 Substack Introducing |
| **P3** | **Hallucination / fabrication** | **6/12** | "Protocol SIFT works. It also hallucinates more than we'd like." + "the AI sometimes 'fabricated credentials' or overstated access levels" + "Fabricated evidence isn't just unhelpful but potentially career-ending and legally catastrophic." | #6 Registration / #1 Substack |
| **P4** | **Context rot (long-running session degradation)** | **4/12** | "AI weaknesses, context rot, self-correction. It works out of the box just like everything else in AI, but the more you repeat it and repeat it and repeat it, over time, it is going to slowly become more dumb." | #7 [un]prompted talk |
| **P5** | **Sequencing — "think like a senior analyst"** | **5/12** | "teach an AI agent to think like a senior analyst, how to sequence its approach, recognize when something doesn't add up, and self-correct when it gets it wrong." | #6 Registration |
| **P6** | **Self-correction on tool failure** | **6/12** | "If you receive an error, I would like you to start performing self-correction." + "When tools error, Claude reads the error message, adjusts its hypothesis...and retries." | #7 [un]prompted talk + #1 Substack |
| **P7** | **Workflow hasn't fundamentally changed in 27 years** | **3/12** | "I've been doing this for 27 years... watched the industry spend billions on detection capabilities while the actual investigation workflow hasn't fundamentally changed." | #1 Substack Introducing |
| **P8** | **AI as Operator (not Tool) — trust-boundary failure** | **3/12** | "Stop threat modeling AI like a tool and start threat modeling it like an operator." + "Any time AI-generated data crosses a trust boundary that assumes human input, failure is guaranteed." + failures occur "in the seams between components." | #5 AI Isn't a Tool |
| **P9** | **Verification under speed pressure** | **3/12** | "how we maintain forensic soundness when the verification loop runs faster than human cognition can follow." | #1 Substack Introducing |
| **P10** | **Domain knowledge gap (obscure artifact formats)** | **2/12** | Claude "sometimes guesses rather than admitting uncertainty" on obscure artifact formats. | #1 Substack Introducing |
| **P11** | **Lack of audit / "what couldn't I find" honesty** | **2/12** | System "either succeeds or tells you specifically why it couldn't" — "know what you couldn't find as much as what you did find." | #1 Substack Introducing |
| **P12** | **Tool parameter / failure-mode opacity (the actual hackathon track)** | **3/12** | "We have a bunch of tools. Cloud doesn't know how the parameters, outputs, and failure modes natively. I'd like you to take my proof of concept and accelerate it to 10 to 100x." | #7 [un]prompted talk |
| **P13** | **Scale to enterprise (cross-host correlation, 500-analyst SOCs)** | **2/12** | Scaling from "classroom pilots to enterprise SOCs running 500 analysts." + Q&A: "1000 systems doing prefetch analysis... that scale is going to create context rot pretty quickly." | #1 Substack + #7 [un]prompted Q&A |
| **P14** | **Detection-centric spending has missed the workflow** | **2/12** | "watched the industry spend billions on detection capabilities while the actual investigation workflow hasn't fundamentally changed." | #1 Substack Introducing |
| **P15** | **Adversary parity: same architecture used offensively** | **5/12** | "The architecture they used, an agentic AI connected to offensive tools via MCP, is the exact same architecture I'd been building for defense." | #1 Substack + #9 Press |

### Priority ranking by mention frequency

```
9 ★ P1  Speed asymmetry / OODA gap
6 ★ P2  Manual syntax / cognitive load
6 ★ P3  Hallucination / fabrication
6 ★ P6  Self-correction on tool failure
5    P5  Sequencing (think like senior analyst)
5    P15 Adversary parity (same arch for offense)
4    P4  Context rot
3    P7  27-year workflow stasis
3    P8  AI-as-Operator trust boundary
3    P9  Verification under speed pressure
3    P12 Tool parameter/failure-mode opacity
2    P10 Domain knowledge gap
2    P11 Audit / honest "couldn't find" reporting
2    P13 Scale to enterprise
2    P14 Detection over investigation
```

---

## Rob's preferred SOLUTION vocabulary (catalog with frequency)

These are the recurring phrases. **Memorize these — every README / video / write-up should use them.**

| Phrase | Count | What it signals |
|---|---|---|
| **"constrained workflow assistant"** | 3 | Position the AI as a coordinator, NOT an analyst. Anti-replacement framing. |
| **"sequence analytical steps"** + **"sequence its approach"** | 4 | The agent must plan in a senior-analyst's ordering — not parallel-fire all tools. Hypothesis-driven. |
| **"self-correct when it gets it wrong"** + **"performing self-correction"** | 5 | Loop that catches its own errors. (NOTE: Rob does NOT use the phrase "Ralph Wiggum Loop" — that term is from the agent-coding community. Our research synthesis previously misattributed it. Rob says "self-correction" / "self-correcting.") |
| **"augment — never replace — the human practitioner"** | 4 | The senior analyst is the customer. AI extends them. |
| **"AI-augmented defenders, matching AI speed with AI speed"** | 4 | The whole mission statement, one phrase. |
| **"deterministic DFIR utilities remain the sole source of analytical output"** | 3 | Ground-truth is the deterministic tool, never the LLM. LLM orchestrates, tool decides. |
| **"think like a senior analyst"** | 3 | Sequencing target. Senior-analyst is the standard the agent must reach. |
| **"recognize when something doesn't add up"** | 2 | Anomaly detection / corroboration awareness. |
| **"USB-C for AI"** | 2 | MCP shorthand for "same plug, any tool." |
| **"Tool User → Tool Orchestrator"** | 2 | The analyst transition that the system enables. |
| **"Inference Constraint layer where the AI directs the workflow"** | 1 | Architectural enforcement language. |
| **"hierarchical CLAUDE.md files inject forensic protocols"** | 1 | The mechanism for sequencing. |
| **"Claude doesn't get defensive when you call it out"** | 1 | Re hallucination handling — owned, not hidden. |
| **"deterministic boundaries"** | 2 | What CLAUDE.md provides. Hard-coded tool paths > letting agent guess. |
| **"trust but verify"** | 1 | Verification posture. |
| **"reduce friction in repetitive tasks"** | 2 | Workflow framing. |
| **"validation, interpretation, and reporting of analysis are always performed by the investigator"** | 2 | Court-admissibility / human-in-loop boundary. |
| **"orchestration layer hardening"** + **"validate untrusted AI output before privilege escalation"** | 2 | Adversarial-AI defense (from AI-Isn't-a-Tool post). |

**Anti-vocabulary — what Rob explicitly avoids:**

- Never says "autonomous SOC" / "replace analyst" / "AI L1"
- Never says "fully autonomous" without "with human oversight"
- Never claims court-admissibility — explicitly says **"not validated for forensic soundness or evidentiary reliability"** and **"not intended for evidentiary use in legal proceedings"**
- Never says "eliminates hallucination" — only "reduces" / "self-corrects" / "flags"

---

## What Rob NEVER mentions (notable gaps)

These are the pains other DFIR voices care about — but Rob does NOT cite as Protocol SIFT motivators:

1. **Report-writing as a distinct pain.** Rob says "comprehensive report" and "executive summary" emerge as outputs, but he never names report-writing as a stand-alone problem to solve. The agent producing a report is a *side effect* of orchestration, not the goal.
2. **Court-admissibility as a pain to optimize for.** Inverse — he explicitly says Protocol SIFT is **NOT** for court use. This is a notable disclaimer, not a goal.
3. **Junior-analyst training / skill-up loop.** Rob never says "this trains the next generation of analysts." He says the OPPOSITE — "only someone who knows DFIR can interpret the output." Junior-training is not a wedge he names.
4. **Multi-source correlation engine (TI + alerts + IDS + EDR).** Rob's framing is dead-disk + memory + logs — not pulling in external threat intel feeds. He acknowledges enterprise-feeds matters in Q&A but doesn't make it a hackathon pain.
5. **Cost / token efficiency.** Mentioned once in passing ("reached out to Anthropic for tokens") but never as a problem statement.
6. **Adversarial evidence / prompt-injection-via-artifact.** Conspicuously absent from his vocabulary even though it's something judges Perkal + Ernstberger care about. He talks about AI-as-operator threat boundary in P8 abstractly, but doesn't name evidence-side prompt injection as a Protocol SIFT pain. **GAP — wedge opportunity for those who want to be the one who names it.**
7. **Determinism / reproducibility across runs.** Mentioned in academic papers about LLM DFIR but Rob doesn't make it a top pain. He treats deterministic tool output as the floor — not the LLM-output reproducibility.
8. **Chain-of-custody hashing.** Implied via "constrained workflow assistant" but never named as a hackathon-prize pain.

---

## Wedge-by-wedge mapping

Mapping strength: **STRONG** (matches Rob's named #1-tier pain in his own vocabulary) / **MEDIUM** (matches a real but secondary pain) / **WEAK** (Rob doesn't name this as a pain) / **NEGATIVE** (Rob explicitly disclaims this).

| Wedge | Rob pain mapped | Mapping strength | Reasoning |
|---|---|---|---|
| **A. Anti-hallucination harness** (measured hallucination rate vs answer keys) | P3 Hallucination + P11 Audit honesty | **MEDIUM-STRONG** | Hallucination IS in his vocabulary and cited as the rationale for the hackathon — but it's #3 in mention count, not #1. The harness is real but doesn't address speed (P1) or sequencing (P5). |
| **B. Hypothesis-driven investigator** (matches "sequence its approach") | P5 Sequencing + P2 Cognitive load + P6 Self-correction | **STRONG** | This is the literal vocabulary he uses: "sequence its approach" + "think like a senior analyst" + "recognize when something doesn't add up." Directly addresses 3 distinct Rob-named pains. |
| **C. Junior-analyst training loop** | (none — Rob's anti-vocabulary) | **NEGATIVE** | Rob explicitly says "only someone who knows DFIR can interpret the output." Framing the agent as a teacher contradicts his "augment senior analyst" framing. |
| **D. Multi-source correlation engine** | P13 Scale + (loose) P5 Sequencing | **WEAK** | Rob discusses cross-host correlation in passing (Q&A) but never names "multi-source" as a hackathon pain. Risk: builds Valhuntir-shape coverage that loses on differentiation. |
| **E. Speed-first triage** (time-to-findings) | P1 Speed asymmetry — his #1 pain | **STRONG** | Highest mention-count pain in the corpus. He literally said "The answer is AI-augmented defenders, matching AI speed with AI speed." Measured by time-to-findings (the metric he uses: "Two-thirds showed meaningful improvement in time-to-findings"). |
| **F. Adversarial-robust investigator** (prompt-injection-via-evidence) | P8 Trust-boundary + (gap) | **WEAK-MEDIUM** | P8 is real but Rob hasn't explicitly named evidence-side prompt injection. Maps to OTHER judges (Perkal, Ernstberger) more than Rob. Strong novelty / weak Rob-alignment. |
| **G. Epistemic honesty** ("here's what I couldn't find" / confidence calibration) | P11 Audit honesty + P3 Hallucination + P10 Domain gap | **STRONG** | Three Rob-named pains. He explicitly praises "know what you couldn't find as much as what you did find" and "Claude doesn't get defensive when you call it out." This is high-Rob-resonance and under-named in the field. |
| **H. Report-first architecture** | (gap — Rob doesn't name) | **WEAK** | Rob's reports emerge as outputs, never as the optimization target. Not a Rob-named pain. |
| **I. Court-admissibility native** | (Rob's anti-vocabulary) | **NEGATIVE** | Rob explicitly disclaims this. Building for court-admissibility contradicts his stated framing. **A submission that claims court-admissibility loses Rob's vote.** |
| **J. Continuous learning loop / context retention across cases** | P4 Context rot + P13 Scale | **STRONG** | Context rot was Rob's literal **Track 2** in the original hackathon design ("cure the context rot issue"). The official rules merged the two tracks, but this is a Rob-named pain at the architecture-level. Under-served by current research. |
| **K. Self-correction loop** (closed-loop critic→revise) (the wedge already chosen) | P6 Self-correction + P3 Hallucination | **STRONG** | Rob explicitly says "performing self-correction" + "self-correct when it gets it wrong" — five-artifact mention. Closed-loop critic is a literal mechanism for what he asks for. |

### Wedge ranking (Rob-priority order)

1. **B. Hypothesis-driven / "sequence its approach"** — most-on-vocabulary, addresses 3 pains
2. **E. Speed-first triage** — addresses his #1 mentioned pain
3. **K. Self-correction / closed-loop critic** — directly maps his "performing self-correction" phrase
4. **J. Context-rot mitigation** — was a DEDICATED TRACK in his original framing
5. **G. Epistemic honesty / "couldn't find"** — addresses 3 pains, under-served
6. **A. Anti-hallucination harness** — real but secondary
7. **F. Adversarial robustness** — under-named by Rob, strong for OTHER judges
8. **D. Multi-source correlation** — Valhuntir territory
9. **H. Report-first** — gap territory
10. **C. Junior training** — anti-vocabulary
11. **I. Court-admissibility** — explicit anti-vocabulary; DO NOT FRAME WEDGE AS THIS

---

## The "Rob's #1 pain" verdict

**Rob's #1 named pain is NOT hallucination. It is SPEED ASYMMETRY** — the gap between offensive OODA loops (seconds) and defensive OODA loops (hours). This is the pain he mentions in **9 of 12 artifacts**, the pain he leads every press release with ("The answer is not faster humans. The answer is AI-augmented defenders, matching AI speed with AI speed"), the pain that gives the hackathon its founding myth (14:27 vs. a week), and the pain quantified in his "Why 47?" math post. The "Protocol SIFT works. It also hallucinates more than we'd like" line is real but it is one acknowledged honest caveat — not the strategic frame. The CONTEXT in which he names hallucination is *the hackathon registration post* where he is listing problems for the community to solve — it's an item on the to-do list, not the core thesis.

**However, Rob's #1 *MECHANISM*** — the *how* — is **sequencing + self-correction**, framed as "think like a senior analyst, sequence its approach, recognize when something doesn't add up, and self-correct when it gets it wrong." That sentence is the single highest-density Rob-vocabulary cluster in the entire corpus: it appears verbatim or near-verbatim in 4 artifacts and is the explicit problem decomposition he gives the community. If "speed asymmetry" is WHY the hackathon exists, "sequence-like-a-senior-analyst with self-correction" is the HOW he tells builders to solve it. **A submission that nails speed-as-outcome AND sequencing-as-mechanism speaks Rob's exact language. A submission that only nails hallucination-reduction speaks one of three secondary pains.**

---

## What this means for wedge choice

- **Lead the pitch with speed, not hallucination.** Open the video / README / executive summary with the time-to-findings delta vs. baseline Protocol SIFT. "Baseline X minutes → ours Y minutes" beats "baseline Z% hallucination → ours W%." Speed is his #1 pain. Hallucination-rate is a corroborating metric, not the headline.
- **Make sequencing visible.** The agent should produce explicit log lines like "HYPOTHESIS: phishing→mshta→C2; pulling email + Sysmon 1 + DNS" and "PIVOT: memory triage clean across 6 indicators, moving to network beacon analysis." That is the literal "sequence its approach" + "recognize when something doesn't add up" + "senior analyst" framing made tangible. **This is the single highest-Rob-vocabulary feature any submission can ship.**
- **Self-correction is the closed-loop critic — but frame it Rob's way.** Call it "the self-correction loop" — NEVER "Ralph Wiggum Loop" in the README. (Internal research uses the Ralph Wiggum framing but Rob himself says "performing self-correction." Match his vocabulary verbatim.)
- **Add context-rot mitigation as a stated feature.** Rob designed this as a separate hackathon TRACK in his original [un]prompted talk. Almost no submission will explicitly address it. A stated mechanism (per-case rolling summary, deterministic-replay-from-audit-log, working-memory compaction every N tool calls) is a Rob-shaped wedge most teams will miss. Even a simple, measured context-rot harness ("run the same case 5x, measure finding-divergence") would land.
- **Frame the hallucination harness as an honesty wedge, not an accuracy wedge.** Rob praises "Claude doesn't get defensive when you call it out" and "know what you couldn't find as much as what you did find." The harness should report not just `precision/recall` but also `findings_flagged_uncertain` and `findings_declined_for_insufficient_evidence`. This is Wedge G language and it is unowned in the field.
- **Drop court-admissibility from the pitch.** Rob explicitly disclaims it. Mentioning court-admissibility as a wedge actively contradicts his framing. Chain-of-custody hashing and read-only mounts are good *implementation hygiene* (Cheri Carr + Ovie Carroll on the judge panel care) — but **don't frame the wedge as "court-admissible." Frame it as "audit-trail-grade reproducibility."**
- **Re-check the composite wedge against this:** the current CONTEXT.md composite leads with "closed-loop critic→revise subagent" (K) + "adversarial-evidence sanitizer" (F) + "measured hallucination-reduction harness" (A). Of those: K is STRONG-Rob, F is WEAK-Rob (strong for Perkal/Ernstberger), A is MEDIUM-Rob. **Missing from the current composite:** explicit sequencing visibility (B) and explicit context-rot mitigation (J) — the two highest-resonance Rob wedges underweighted in current strategy. **Recommend adding a "Senior-Analyst Sequencer" subagent + a measured context-rot mitigation harness on top of the current K+F+A stack.** If forced to drop one, drop F (adversarial sanitizer) before dropping B (sequencer) — Rob will read sequencing first.

---

## One-sentence synthesis for the pitch

> "Protocol SIFT v2: a constrained workflow assistant that sequences its approach like a senior analyst, recognizes when something doesn't add up, self-corrects when it gets it wrong, and measures time-to-findings against baseline — closing the speed gap without inheriting the hallucination tax."

Every load-bearing noun and verb in that sentence is Rob T. Lee's vocabulary, in his order, addressing his named pains.
