# 05 — Prior Winners

## Status: N/A — first-edition hackathon

The Find Evil! hackathon is the **first hackathon SANS Institute has run** focused on autonomous AI incident response. From the SANS press release:

> "Two Words That Changed Cybersecurity: 'Find Evil!' Builders Answer The Call To Defend Infrastructure."

> "SANS launches first hackathon for autonomous AI incident response."

There are no prior winners to reverse-engineer. The closest equivalents:

1. **DEF CON CTFs / Black Hat Arsenal projects** — different format, different judging
2. **DFRWS Challenge winners** (2008, 2011) — these are research challenges, not hackathons
3. **DFIR-Metric paper authors** — academic prior work, not hackathon

## Reframe: "Valhuntir as the winning-shape proxy"

Since we have no prior winners, the **shape of the winning submission is best inferred from Valhuntir** (which the rules explicitly cite as the quality bar to meet or exceed).

### What "Valhuntir-shape" tells us about winning judgments

A submission resembling Valhuntir in architecture will score well on the rubric because Valhuntir was deliberately built to embody Rob T. Lee's design principles. So Valhuntir IS the winning blueprint, modulo:
- It's not entered in the hackathon (Steve Anson is the example author, not a contestant)
- It cannot itself win — but its architecture is what wins

### Winning attributes derived from Valhuntir

| Attribute | Why it wins | Criterion it scores |
|---|---|---|
| Custom MCP Server (not Direct Extension) | "Most sound architecture" per rules | Constraint Implementation |
| Typed Pydantic I/O on every tool | Schema = contract, agent can't pass garbage | Constraint, IR Accuracy |
| Response envelope with caveats + corroboration + discipline reminders | Methodology at point of need | IR Accuracy, Autonomous Execution |
| Per-tool-call JSONL audit log with stable audit_id | Every finding traces to a specific call | Audit Trail |
| HMAC-signed approval ledger (PBKDF2-derived key, outside sandbox) | LLM cannot forge approvals — cryptographic | Constraint, Audit Trail |
| Provenance tier rejection (MCP > HOOK > SHELL > NONE → reject) | Forces traceability | Audit Trail, IR Accuracy |
| Multi-source corroboration (forensic-rag + windows-triage + opencti) | "Don't trust a single source" SANS principle | IR Accuracy |
| Examiner Portal with browser-based DRAFT→APPROVED gate | HITL is the cited "primary defense" | Constraint, Usability |
| Read-only evidence mount + bwrap kernel sandbox | Architectural, not prompt-based | Constraint |
| Open-source MIT license + clean install docs | Reproducible by other practitioners | Usability |

### How a winning submission differs from Valhuntir

Since Valhuntir is **already at "meet"** of "meet or exceed," winning requires **exceeding on at least one orthogonal axis**. The published gaps (per `04-competitor-analysis.md`):

1. **Closed-loop critic→revise self-correction** — the tiebreaker criterion is Autonomous Execution Quality
2. **Structural adversarial-evidence defense** — Perkal + Ernstberger will probe this
3. **Memory-first Volatility-plugin-aware investigator** — the canonical SANS demo material
4. **Measured hallucination reduction** with public answer key benchmarks
5. **Live-host triage** via Velociraptor MCP + agentic layer

### Translation to a build target

A submission that **(a) matches Valhuntir's architectural floor** and **(b) adds 1-2 of the orthogonal wedges above with measurable evidence** is positioned to score:

- Autonomous Execution: ✓✓✓ (closed-loop critic = top wedge for tiebreaker)
- IR Accuracy: ✓✓✓ (measured hallucination harness)
- Breadth: ✓✓ (don't try to match 100 tools; 15-25 well-chosen)
- Constraint: ✓✓✓ (Custom MCP + sandbox + adversarial-evidence defense)
- Audit Trail: ✓✓✓ (Valhuntir-style + critic logs + provenance tiers)
- Usability: ✓✓ (good README + reproducible install; not gunning for Usability win)

That's enough ✓✓✓s to win without trying to dominate Usability.

## A historical comparable: DFRWS 2008

The DFRWS 2008 Linux Memory Challenge (which is in our validation dataset list, Tier 2) is the closest historical comparable for *what a top DFIR challenge winner looks like*. The winning entry by Cohen, Collett, and Walters demonstrated:

- Password breaking
- File carving from memory
- Browser history parsing
- **Evidence tampering detection**
- Multi-modal evidence correlation (memory + disk + network)

**The thread that runs from DFRWS 2008 to Find Evil! 2026:** multi-source evidence correlation + adversarial-aware analysis + detection of attempted anti-forensics. The Find Evil! winning submission will almost certainly be the one that handles **at least two evidence types** (disk + memory or memory + network) with **explicit cross-source corroboration** and **demonstrated catch of evidence tampering / adversarial behavior**.

## Looking forward: post-hackathon

Rob T. Lee has stated:

> "Winning submissions will be reviewed for integration back into Protocol SIFT."

So the actual "prior winner" of the next SANS hackathon will be... whoever wins this one. Whoever ships the cleanest reference implementation becomes the post-hackathon Protocol SIFT standard — and inherits the leverage of being the default architectural reference for every future submission.

That's the meta-prize and arguably more valuable than the $10K cash for a builder trying to establish themselves in the AI-DFIR space.
