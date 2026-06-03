# STRATEGY — Find Evil! Wedge Commitment

> Single page. The wedge we committed to.
> Architecture decisions are NOT made here — they happen in the design phase, informed by `context/`.
> Earlier version at `STRATEGY-v1.md` (rubric-rooted, deprecated).

---

## The problem we solve (for the user)

**Senior incident response consultants lose half their billable time to two things they hate:**

1. **Running tools by hand.** Two-thirds of an investigation is typing forensic CLI commands, parsing CSV output, copy-pasting between tools, and waiting. Rob T. Lee calls senior analysts "command-line stenographers." A typical engagement: 8-12 hours of work, most of it mechanical.

2. **Writing the report afterward.** Once the investigation is done, the consultant spends another 2-3 hours turning their notes into a structured incident report the client can read, a lawyer can defend, and an executive can act on. This is the part practitioners complain about most in public — and the part nobody is building for.

**SilentWitness closes both gaps.** It works the case the way a FOR508-graduate senior analyst works the case — forming hypotheses, testing them with the right tools, pivoting when evidence contradicts — and produces a structured incident report **as the case unfolds**, not after. Every claim in the report ties back to the tool execution that produced it.

The target user is the senior IR consultant or in-house IR lead at a midsize firm. The day-after-deploying-SilentWitness story is: they take more cases per month because the per-case grunt work is gone.

---

## The wedge in one sentence

> A hypothesis-first IR investigator that drafts its own structured incident report as the case unfolds, with every claim verifiably linked to the tool execution that produced it.

---

## Why this wins the hackathon

Three independent reasons:

| Reason | Evidence |
|---|---|
| Solves the highest-volume practitioner pain (speed + reporting), not the one the field is already crowded on (anti-hallucination). | Agent 12 found ~60 visible hackathon repos; ~85% are running architectural-anti-hallucination variants. Agent 9 found report-writing is pervasively complained about by practitioners but nobody addresses it. |
| Aligns with the head judge's #1 mechanism in his exact vocabulary. | Rob T. Lee names "senior-analyst sequencing + self-correct" as the desired AI behavior in 4+ public artifacts. The hypothesis-pivot loop IS that behavior, literally. |
| Aligns with the practitioner judge tier's substance (defensible findings, cross-examination survival) without using their vocabulary (court-admissibility). | Steve Anson built Valhuntir as a cross-examination survival platform. Ovie Carroll / Cheri Carr / Amanda Rankhorn carry the same instincts. Our report-with-verifiable-claims serves the substance without the trigger words Rob avoids. |

Full validation evidence: `research/protocol-sift-2026/.raw/06-09*.md` (the four validation passes).

---

## Headline metric

**Time to handoff-ready incident report** on a representative case (e.g., NIST Hacking Case = the "Mr. Evil" wardriving image).

Anchored against Rob T. Lee's published 14:27 demo and against vanilla Protocol SIFT baseline. The pitch is the delta on this number, not on hallucination rate (which is the saturated lane's metric).

Secondary metrics:
- Number of pivots logged (proves hypothesis-driven, not kitchen-sink)
- % of report claims that resolve to a tool execution (proves verifiable, without saying "court-admissible")
- Epistemic honesty: explicit list of what the agent could NOT verify or did NOT check (Rob's "Claude doesn't get defensive when you call it out")

---

## What the demo must show (5 minutes)

1. The 3 AM IR pain (30s)
2. `silentwitness investigate /evidence/<case>` (30s)
3. The hypothesis log — formed, tested, pivoted live (90s)
4. The report writing itself as findings appear (60s)
5. A self-correction moment — the agent recognizing something doesn't add up and changing approach (30s)
6. The finished report with click-through `[verify]` links on every claim (30s)
7. Time-delta vs baseline (30s)

The order, framing, and exact moments are architecture / design decisions made in the next phase.

---

## What is NOT decided yet (defer to design phase)

These ALL stay open for the design-phase agent + Abu to decide, informed by the `context/` knowledge base:

- Whether to build on Claude Code, OpenClaw, or a custom Agent SDK setup
- Whether to use MCP, a different tool-use protocol, or a hybrid
- Whether the agent is single or multi-agent (and if multi, what coordination)
- How the hypothesis stack is represented (state machine? DAG? finite list? rolling buffer?)
- How verifiability is enforced (byte-level? line-level? entity-extraction? semantic? hybrid?)
- How the report is rendered (template-driven? LLM-rendered? hybrid? what format?)
- Which specific forensic tools to wrap (the encyclopedia in `context/domain/06-sift-toolchain-deep.md` lists every option)
- How human approval / examiner workflow is handled (or if it's needed at all)
- The deployment shape (CLI? web UI? Docker? SIFT VM only?)
- The model selection and orchestration (Claude Opus only? Sonnet for some tasks?)
- The persistence layer (filesystem? SQLite? Postgres? In-memory?)

These choices should emerge from reading the context and stress-testing against the wedge, not from this document.

---

## Constraints we must respect (from the rules)

| Must | Source |
|---|---|
| Build on or integrate with SANS SIFT Workstation | Rules §4 |
| Use an agentic framework as primary execution engine (Claude Code or OpenClaw preferred; AutoGen / CrewAI / LangGraph / Cursor / Cline / Aider permitted) | Rules §4 |
| Demonstrate self-correction, accuracy validation, and analytical reasoning | Rules §4 |
| Linux terminal environment | Rules §4 |
| Substantially new work built Apr 15 – Jun 15 2026 (pre-existing libraries and SIFT codebase as foundation OK) | Rules §4 |
| MIT or Apache 2.0 license | Rules §4 |
| 8 mandatory deliverables (repo, video ≤5min w/ live terminal, architecture diagram, write-up, dataset doc, accuracy report, setup instructions, structured execution logs) | Rules §4 |

These are constraints. They define the lane. They do not define the architecture.

---

## File index

| File | Purpose |
|---|---|
| `STRATEGY.md` | This file. The wedge commitment. |
| `STRATEGY-v1.md` | Rubric-rooted v1 (deprecated, kept for traceability). |
| `context/` | Domain knowledge base for design-phase decisions. Pure facts, no architectural prescription. |
| `research/` | Validation research that LED to the wedge (provenance trail). |

---

**Status: WEDGE COMMITTED.** Architecture decisions deferred to design phase. `context/` build is the next milestone.
