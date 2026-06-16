# SilentWitness — Devpost Submission Draft

> Paste these sections into the Devpost project page. Image callouts are marked
> **[IMAGE: …]** — those go in the Devpost gallery; specs for each are in
> [`DESIGN_BRIEF.md`](DESIGN_BRIEF.md). Keep the honest framing — the rules reward it.

**Tagline (one line under the title):**
*The AI incident-response analyst that has to prove every claim — and won't conclude until
it's answered every question.*

**[IMAGE: Banner]** — the branded banner (see design brief) goes at the very top.

---

## Inspiration

AI agents are being pointed at forensic evidence, and the problem is obvious to anyone who has
done incident response: the model is fluent, confident, and **wrong just often enough to be
dangerous**. Protocol SIFT's own README concedes that if you just tell an LLM to "find evil," it
will hallucinate. A confidently fabricated finding in a real investigation isn't a bug — it's a
liability. We wanted to build the opposite: an autonomous DFIR analyst that **physically cannot
make a claim it can't prove**, catches its own mistakes, and is honest about what it doesn't
know.

## What it does

SilentWitness investigates a Windows forensic image (disk + memory) on the SANS SIFT Workstation
and produces a cited, defensible report. Given the SANS **ROCBA** case, it autonomously:

- started from auto-staged detections, formed and pivoted forensic **hypotheses**, and confirmed
  them against evidence;
- recovered the full theft story — the stolen Stark Research Labs projects (*Airwolf, Gunstar,
  Blue Thunder*), exfiltration to Google Drive + a PST email export, the RDP access vector, the
  SDelete anti-forensics, the brute-forced BACKUPADMIN account, and the intrusion window;
- recalled **10 of 10** ground-truth findings on the real case (with a capable model);
- and — this is the point — **caught and revised its own over-broad claims** via a live critic,
  and **refused to finalize** until it had answered all five Key Questions.

Every claim in the report quotes a real evidence record, verified server-side. A fabricated quote
is rejected before it can reach the report.

**[IMAGE: Diagram E — Recall Improvement chart]** (40% → 20% → 30–50% → 100%).

## How we built it

A **Custom MCP Server** (the recommended Protocol SIFT pattern), MIT-licensed, model-agnostic
(OpenAI / Anthropic / Google / Ollama), with a Pydantic AI reference agent.

- **Evidence is parsed once** into a per-case SQLite FTS5 index by nine targeted forensic parsers
  (EVTX, MFT, registry, SRUM, USN journal, LNK, jumplists, prefetch, PowerShell transcripts) plus
  a **Sigma detection engine** running the community SigmaHQ rule pack.
- **The agent never touches raw evidence** — its only interface is a search over that index, so
  there is no tool by which it could read or modify the original image. Guardrails are
  **architectural, not prompt-based**: a citation gate (verbatim quote ⊆ cited record), an entity
  gate (every IOC must appear in the evidence), an adversarial sanitizer, and a hash-chained audit
  trail where every row carries a SHA-256 + the audit-id of the tool that produced it.
- **Two self-correction mechanisms:** a live critic (a separate agent, fresh context) that
  challenges weak findings, and an enforced **coverage gate** — a framework-level output validator
  that bounces the agent back until all five investigative questions are answered.

**[IMAGE: Diagram A — System Architecture]** and **[IMAGE: Diagram B — the 10-layer hallucination
firewall]**.

## Challenges we ran into

- **Premature convergence.** Our biggest finding: when we first wired in the new capabilities,
  recall *dropped* (40% → 20%). The agent latched onto the single loudest signal — ~540,000
  brute-force detections — confirmed one hypothesis, and quit, even though the rest of the evidence
  was indexed. This is exactly the failure mode autonomous agents are prone to.
- **The fix had to be structural, not a prompt.** We built the enforced coverage gate so breadth
  is guaranteed by the framework, not hoped for from the model. That took recall to 50% and then,
  with a stronger model, to 100%.
- **Honesty about variance.** Recall is nondeterministic and scales with the model (gpt-5.2:
  30–50%; gpt-5.5: 100%). We report the distribution and the failure modes, not just the peak.
- **Plaso extracts 0 events** from the ROCBA event logs (a libevtx defect on this image); we
  route around it with our own parsers and document it rather than hide the empty pass.

## Accomplishments / what we learned

- **Architectural guardrails beat prompts.** The most reliable way to stop an AI from hallucinating
  in forensics is to remove the *ability* to, at the tool boundary — not to ask it nicely.
- **Enforced completeness is a real differentiator.** Making the agent prove it answered every
  question changed it from "lucky one-shot" to "thorough investigator."
- **Honest failure analysis is a feature.** We catch hallucinations, document our misses, and
  publish a self-critical accuracy report — which is exactly the discipline real IR requires.

## What's next

- Wire **memory analysis** (Volatility) into the recall path for disk⊕memory corroboration.
- A provenance/MITRE ATT&CK overlay on every finding and a corroboration gate for multi-source
  confirmation.
- Multi-host correlation for APT-scale cases.

## Built with

Python · Pydantic AI · Model Context Protocol (MCP) · SQLite FTS5 · dfVFS · pySigma · spaCy ·
SANS SIFT Workstation · OpenAI / Anthropic / Google / Ollama (model-agnostic).

## Links (fill in)

- **Repo:** <https://github.com/Blockchain-Oracle/silentwitness>
- **Demo video:** _<https://vimeo.com/1201573890>_
- **Accuracy report:** [`docs/ACCURACY_REPORT.md`](ACCURACY_REPORT.md) ·
  **Architecture:** [`docs/architecture.md`](architecture.md) ·
  **Three-claim trace:** [`docs/THREE_CLAIM_TRACE.md`](THREE_CLAIM_TRACE.md)
