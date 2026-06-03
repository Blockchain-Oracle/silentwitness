# Valhuntir Design Rationale

## Methodology

What I read and where:

1. **Valhuntir repo** (cloned to `/tmp/valhuntir-rationale-check`, depth 1, single commit on `main` — dependabot only, no commit-message archaeology available). Read in full:
   - `README.md` (820 lines — the primary motivational document)
   - `docs/architecture.md` (412 lines — system invariants, 9-layer HITL model)
   - `docs/security.md` (250 lines — explicit threat model + L1–L9 controls)
   - `docs/getting-started.md` + `docs/index.md` + `docs/user-guide.md` (workflow framing)
   - `SECURITY.md` + `.github/` issue templates
   - GitHub releases (v0.5.0 first cut Feb 28 2026, v0.6.1 latest Apr 16 2026 — so Valhuntir is ~3.5 months old at hackathon-judging time)
2. **AppliedIR org page** — 5 repos, all MIT, all Python, Steve Anson is the sole architect; Claude Code is the sole implementer per the README's "Clear Disclosure".
3. **Steve Anson public profiles**: SANS profile, AppliedIncidentResponse.com About page, Informed Defense services page (his consultancy), RSAC speaker profile (403'd), Crunchbase, LinkedIn (999'd — auth required).
4. **Find Evil! hackathon Devpost rules page + Resources page** (the page that names Valhuntir as the "level of quality to meet/exceed").
5. **Rob T. Lee's Substack** announcing Protocol SIFT (the tool Valhuntir is positioned against).
6. **SANS blogs**: "FOR508 Evolves as Threat Hunting Shifts In-House" + "FOR508 Spring 2025 Course Update" (the closest thing to Anson's curriculum worldview in writing).
7. **techUK "Accelerating agentic AI in digital forensics"** — adjacent industry view, not Anson.

What I could NOT get: Anson's LinkedIn timeline (auth-walled), his X account (didn't find one active), his RSAC abstracts (403), any podcast appearances about Valhuntir specifically (none found in search), any blog post by him explaining "why I built Valhuntir" outside the README itself. **The README's "Clear Disclosure" section is the closest thing to a public motivation statement.**

## Steve Anson — bio + worldview

- **25+ years DFIR.** Former Defense Criminal Investigative Service, FBI task-force agent (computer crime). Trained national cyber units in 60+ countries. Taught at the FBI Academy and US State Department.
- **SANS Principal Instructor.** Co-author of FOR508 (Advanced Incident Response, Threat Hunting, and Digital Forensics) and instructor for SEC504. FOR508 is the flagship DFIR course — the customer for Valhuntir's design choices is almost certainly a FOR508 graduate.
- **Author of two books**: *Applied Incident Response* (Wiley, 2020) and *Mastering Windows Network Forensics and Investigation* (2nd ed., Sybex, 2012). The naming of his GitHub org (AppliedIR) is a direct callback to his book.
- **Consultancies**: Informed Defense (vCISO + training + policy; he describes 30 years of "digital investigations and cyber security" across "national government agencies and multinational companies"). Also co-founder of Forward Defense and Applied Incident Response (consultancy of the same name as the book).
- **Notably**: Informed Defense's published service list does NOT include "incident response" as a billable service line. He sells **training, mentoring, policy, security testing, security design, and vCISO**. This is important — see "day after Valhuntir" section below.
- **Worldview signal**: Anson is a *practitioner who teaches*. Everything he ships is built to be defensible in court (FBI/DCIS background) AND teachable to a SANS classroom (FOR508 background). Both pressures are visible in Valhuntir's design.

## Target user (per Anson's own framing)

The README is unusually explicit. Direct quotes:

> "Valhuntir turns a single incident response analyst into the manager of an agentic AI incident response team."

> "The AI, like a hex editor, is a tool to be used by properly trained incident response professionals."

> "I do DFIR. I am not a developer." (Clear Disclosure section)

The target user is **a credentialed DFIR examiner** — specifically:
1. **Single analyst on a case** (the "team-of-one" framing). Not a SOC, not Tier-1 triage — the senior IR practitioner who normally has to do everything themselves.
2. **Court-facing or report-facing**: every choice (HMAC, examiner-named IDs `F-alice-001`, chain-of-custody log, evidence registry with SHA-256, lockable evidence directory, examiner password as the gate) screams "this finding might be cross-examined."
3. **Multi-examiner consultancy or team**: the merge/export workflow (`F-alice-001` vs `F-bob-003`, last-write-wins by `modified_at`, APPROVED protected from overwrite) shows he expects multiple consultants on the same case.
4. **Already a FOR508 graduate**: he assumes the reader knows what Shimcache vs Amcache means, what KAPE/Velociraptor/EZ Tools/Hayabusa are, why "presence ≠ execution" is a discipline reminder, why grounding against Sigma/MITRE matters.

Anson is NOT building for: tier-1 SOC analysts, students, internal IT teams, MSSPs running cookie-cutter playbooks, or law enforcement officers who'd need hand-holding. He's building **for a consultant who looks like himself**.

## The stated motivation

There is no published "why I built this" essay. The motivation has to be reverse-engineered from:

1. **The repeated "Find Evil will hallucinate" warning** (appears verbatim in BOTH the README and user-guide — repeated TWICE for emphasis):

   > "ALWAYS verify results and guide the investigative process. If you just tell Valhuntir to 'Find Evil' it will more than likely hallucinate rather than provide meaningful results. The AI can accelerate, but the human must guide it and review all decisions."

   This is a direct, named shot at Rob T. Lee's Protocol SIFT demo ("two words: 'find evil'"). Anson is making a public technical claim that the demo is unsafe.

2. **The "Clear Disclosure" section** — the closest thing to a confessional:

   > "I do DFIR. I am not a developer. This project would not exist without Claude Code handling the implementation. While an immense amount of effort has gone into design, testing, and review, I fully acknowledge that I may have been working hard and not smart in places. **My intent is to jumpstart discussion around ways this technology can be leveraged for efficiency in incident response while ensuring that the ultimate responsibility for accuracy remains with the human examiner.**"

   The motivation is **methodology preservation under AI acceleration**, not productivity. He wants to show what "AI-assisted IR done responsibly" looks like — as a SANS instructor's reference standard, not as a commercial product. Note: the platform is MIT-licensed, given away free.

3. **The hackathon framing**. Rob T. Lee at RSAC 2026 demoed Protocol SIFT typing "find evil" → 14:27 to a complete C drive analysis. Anson's response is an entire platform whose README opens with a warning that EXACTLY that workflow ("just tell Valhuntir to Find Evil") hallucinates. Valhuntir was conceived and shipped in a 2–3 month window after RSAC 2026 (v0.5.0 = Feb 28 2026; RSAC was earlier that month). **Valhuntir is, in part, a methodologist's reply to Protocol SIFT.**

4. **FOR508 curriculum signal**. SANS FOR508 "concludes with a discussion on agentic AI for further enhancing and accelerating DFIR investigations." Anson teaches the AI-in-IR module — Valhuntir is effectively the working example his students are sent home with.

So: stated motivation = **demonstrate that AI can accelerate IR WITHOUT abandoning evidentiary rigor**. The unstated motivation = **claim the reference architecture for agentic DFIR before someone less methodological does**.

## Pain prioritization (per architectural choices)

What the architecture *signals* about pain ranking:

| Architectural choice | Pain signal |
|---|---|
| **HMAC-signed approvals (PBKDF2, 600K iters, password-gated, /var/lib/vhir/ outside the case dir)** | **Court admissibility + post-hoc tampering defense.** Not anti-hallucination. The cryptographic gate is so a judge/defense lawyer can verify that a finding was approved by examiner X using their password at time T. This is FBI-brain. |
| **bwrap kernel sandbox + 41 deny rules + L9 unprivileged user namespaces** | **Defense against the AI itself modifying case data** — protecting the audit trail from the LLM, not protecting the host from malware. Pain = "the LLM could overwrite findings.json mid-investigation and I'd never know." This is paranoia about agentic AI's blast radius, not about hallucination per se. |
| **22K-record forensic RAG (Sigma, MITRE ATT&CK, LOLBAS, Atomic, KAPE, Velociraptor, Hayabusa rules…)** | **Grounding against authoritative sources** to replace LLM training-data recall. Pain = "the LLM will make up a Sigma rule that doesn't exist, or misattribute a MITRE technique." This IS anti-hallucination — but specifically anti-fabrication-of-known-references, not anti-misinterpretation-of-evidence. |
| **Examiner Portal browser UI (8 tabs, keyboard shortcuts, challenge-response auth)** | **Reduce review friction so the human-in-the-loop actually happens.** Pain = "if approval requires CLI gymnastics, examiners will rubber-stamp and lose the discipline benefit." Anson is solving for examiner laziness/fatigue. |
| **9 defense layers (L1 structural → L9 kernel)** | **Defense in depth because no single control is trusted.** Pain = "any one control will be bypassed, the LLM is adversarial-by-incompetence." |
| **100 MCP tools across 9 backends (forensic-mcp, case-mcp, report-mcp, sift-mcp, opensearch-mcp, forensic-rag-mcp, windows-triage-mcp, opencti-mcp, wintools-mcp, remnux-mcp)** | **Tool-coverage parity with the SIFT/REMnux/Windows triage ecosystem.** Pain = "if the AI can't reach the tool the human would reach for, it'll invent a finding from incomplete data or hallucinate the tool's output." Anson is buying off the "context completeness" axis. |
| **Provenance tiers (MCP > HOOK > SHELL > NONE, NONE rejected)** | **Make findings without evidence chains structurally impossible.** Pain = "the LLM will write a finding that looks confident but has no audit trail back to evidence." This is the most direct anti-hallucination architectural choice — and it's *structural*, not prompt-based. |
| **Grounding score (STRONG/PARTIAL/WEAK based on RAG/triage/CTI consultation)** | **Make "did you check your work" measurable and visible.** Pain = "the LLM will produce a plausible interpretation without consulting authoritative references." Anti-fabrication, advisory not blocking. |
| **Discipline reminder rotation (15 rotating reminders, ~50 tokens/response, e.g. "Shimcache and Amcache prove file PRESENCE, never execution")** | **Combat LLM session drift over long investigations.** Pain = "the system prompt fades; methodology has to be re-injected at every tool call." Anti-drift, not anti-hallucination. |
| **Adversarial-evidence markers (`data_provenance: tool_output_may_contain_untrusted_evidence`)** | **Prompt injection from evidence itself.** Pain = "the malware's strings/log messages/registry values can be crafted to manipulate the LLM." |
| **Findings staged as DRAFT, no MCP tool for approval, password-gated** | **Structurally impossible for the AI to publish a finding into a report.** This is the *single most load-bearing control* — without it, every other layer is decoration. |
| **Token-budget-aware FK enrichment (caveats always, advisories decay after 3 calls)** | **Long-session pragmatism.** Pain = "delivering full forensic context on every call burns the context window before the investigation finishes." |

The architecture ranks pain roughly as:
1. **Court-admissibility / chain-of-custody integrity** (L1/L2/L7 + HMAC ledger + approvals.jsonl + examiner-named IDs)
2. **Defense against the AI's blast radius** (L3/L4/L5/L9 + deny rules + chmod 444)
3. **Anti-hallucination via structural grounding** (provenance tiers + grounding score + 22K RAG + windows-triage baseline)
4. **Methodology drift over long sessions** (FK enrichment + discipline reminders)
5. **Multi-examiner collaboration** (export/merge + named IDs)
6. **Token-cost efficiency** (OpenSearch indexing replacing raw-token reads)
7. **Reviewer ergonomics** (Examiner Portal, keyboard shortcuts)

Hallucination is in the top 3 but it's NOT #1. **Evidentiary integrity is #1.**

## On hallucination specifically

Anson mentions hallucination explicitly in only ONE place in the README/docs, and it appears verbatim twice (README + user-guide):

> "If you just tell Valhuntir to 'Find Evil' it will more than likely hallucinate rather than provide meaningful results. The AI can accelerate, but the human must guide it and review all decisions."

That's the only literal "hallucination" word in the entire docs corpus. Hallucination is treated as a *symptom* of giving the LLM too much autonomy — and the *cure* is the human-in-the-loop architecture, not a model-level intervention.

The architecture also addresses fabrication indirectly:
- **Grounding score** measures whether RAG/triage/CTI were consulted before claiming
- **22K record RAG** replaces "LLM knows Sigma rules from training" with "LLM looks up Sigma rules from a deterministic index"
- **windows-triage offline DB** replaces "LLM knows Windows internals" with "LLM checks a 2.6M-row baseline"
- **Provenance NONE rejected** structurally blocks findings invented out of nothing

So hallucination *is* addressed, but Anson's framing is: **"hallucination is what happens when you don't enforce methodology — fix methodology, not the model."** This is a *DFIR practitioner's* framing, not an *AI researcher's* framing.

Compare to Rob T. Lee's framing in his Protocol SIFT Substack: "Protocol SIFT works. It also hallucinates more than we'd like." Lee treats hallucination as a model-level limitation to be reduced. Anson treats it as a workflow-level discipline failure to be structurally prevented.

**Ranking**: Hallucination is one of MANY concerns — call it #3 on the pain list, behind admissibility (#1) and AI-blast-radius (#2), tied with methodology drift. It is NOT the singular focus the way it might be framed for the hackathon.

## The "day after Valhuntir deployment" story

What changes in the consultant's life:

1. **They can take cases they couldn't before.** A solo consultant called in for a ransomware response on 5 hosts with 200 GB of triage data — previously a 2-week engagement just to ingest and timeline — can now do it in 2–3 days. Anson explicitly says Valhuntir "turns a single analyst into the manager of an agentic AI IR team."

2. **They bill the same flat fee with higher margin, or bill more cases.** This isn't AI-replaces-the-consultant; this is AI-multiplies-the-consultant. The consultant is still the one on the phone with the client, still the one writing the executive summary, still the one cross-examined in court — but the grunt work (parse Amcache, run Hayabusa, correlate timeline, IOC enrichment) is offloaded.

3. **They produce defensible reports faster.** The report-mcp + Zeltser IR Writing MCP integration auto-generates IR reports from approved findings with MITRE mappings and IOC aggregation. Bidirectional HMAC reconciliation detects post-approval tampering. This is the deliverable a consultant hands to the client + insurer + potentially to law enforcement.

4. **They survive defense-side scrutiny.** Every finding has provenance (MCP > HOOK > SHELL > NONE), every approval has an HMAC signature tied to the examiner's password, every tool call is in the audit JSONL. A defense expert witness CAN'T credibly say "you don't know what the AI did" — because every tool call is logged with arguments and outputs.

5. **They onboard junior examiners faster.** Multi-examiner export/merge + the discipline reminder system + the FK enrichment + the AGENTS.md/CLAUDE.md docs all mean a junior IR analyst with the AI can produce work approaching senior quality, with the senior reviewing in the Portal.

The customer Anson is silently designing for: **a small DFIR consultancy or an in-house IR team at a regulated org (finance, healthcare, defense contractor) where the lead examiner has billable-hour pressure AND court-witness pressure AND junior staff to train.** That's the Informed Defense / Applied Incident Response customer profile.

Notably absent: anything about MSSP-scale, anything about SOC tier-1 triage, anything about real-time detection (this is post-incident DFIR, not detection engineering).

## On Protocol SIFT

Anson never names Rob T. Lee or Protocol SIFT in the docs corpus. But:

1. **The "Find Evil will hallucinate" warning is a direct rhetorical reply** to the Lee RSAC demo's "find evil" prompt. Same verb, same noun, opposite conclusion. This is intentional.
2. **Architecture invariant #1**: "All client-to-server connections use MCP Streamable HTTP." Anson uses the same protocol as Protocol SIFT — he is NOT trying to replace MCP-on-SIFT; he is trying to add the *missing controls* on top.
3. **Naming**: Valhuntir's `sift-gateway`, `sift-mcp`, `sift-common` package names show he's positioning Valhuntir as the *layered platform* over the SIFT Workstation ecosystem, not as a competitor.
4. **The hackathon Resources page lists Valhuntir as "the level of quality to meet or exceed"** — meaning Lee/SANS have publicly endorsed Anson's architecture as the reference. So whatever rivalry exists is friendly: Lee says "Protocol SIFT works, hallucinates more than we'd like"; Anson says "here's what disciplined looks like, go beat this."

**Read**: Valhuntir is *the methodological correction to Protocol SIFT*, blessed by the same SANS leadership that ships Protocol SIFT. It is not a competitor — it is the reference implementation showing what "Protocol SIFT done right for production DFIR" looks like.

## What this tells us about wedge choice

Synthesis — what Anson's design teaches us about the 10 wedges (A–J):

- **Wedge most user-rooted in Anson's eyes**: Any wedge that puts **evidentiary integrity / court-admissibility / chain-of-custody / multi-examiner audit trail** at the center. Anson's #1 pain is "this finding has to survive defense-side cross-examination" — that's the deepest, hardest-to-fake user need in his architecture. Wedges centered on cryptographic provenance, examiner-bound signatures, or tamper-evident audit trails will resonate.
- **Wedge Anson would respect most**: One that demonstrates a *structural* (not prompt-based) control the LLM cannot bypass. He explicitly rejects "single system prompt that the LLM can drift from" — anything that ships a structural enforcement (deny rules, sandboxes, validators, schema gates, ledger reconciliation) over a prompt-engineering trick will look serious to him.
- **Wedge Anson would be skeptical of**: Pure anti-hallucination wedges framed as "we reduced the model's fabrication rate by X%". He doesn't believe hallucination is a model problem — he believes it's a methodology problem solved by structural workflow. A wedge that says "our LLM hallucinates less" without showing the workflow control will look naive to him.
- **Wedge that maps to his commercial reality**: One that helps a solo-to-small-team DFIR consultancy (his actual customer base via Informed Defense / Applied Incident Response) take a case they couldn't take before, OR survive a deposition they couldn't survive before. NOT a wedge for SOC-scale triage. NOT a wedge for "AI replaces the analyst." A wedge that explicitly accepts "the human examiner stays accountable, we just remove their drudgery and protect their reputation" will land.
- **Sleeper wedge signal**: His repeated emphasis on **methodology reinforcement at the tool-response level** (FK enrichment, discipline reminders, rotating reminders that "Shimcache proves presence not execution") suggests he believes a major unsolved pain is **teaching the AI forensic discipline incrementally during a session, not at session start**. A wedge that ships a novel "in-flight methodology injection" or "session-drift correction" mechanism would resonate as the next-step problem he himself hasn't fully solved.

Honest summary: **Anson built Valhuntir around evidentiary integrity first, AI-blast-radius containment second, and anti-hallucination third — and he sees all three as workflow/structural problems, not model problems.** The wedge that wins his respect either (a) ships a structural control he hasn't shipped, (b) closes a remaining attack surface in his 9-layer model, or (c) demonstrably helps the solo consultant take a case they couldn't take before — without compromising the audit trail he made load-bearing.

A wedge that reduces hallucination via prompt tricks, vibes-based "confidence scoring", or vendor-branded model marketing will look amateur. A wedge that ships HMAC-signed cross-examiner finding reconciliation, or a structural prompt-injection defense for adversarial evidence, or a "junior examiner sandbox where mistakes can't escape" will look senior.
