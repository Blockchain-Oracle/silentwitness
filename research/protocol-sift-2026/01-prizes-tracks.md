# 01 — Prizes & Judging Criteria

## Prizes

| Place | Cash | Other |
|---|---|---|
| **1st — SLAYED EVIL** | $10,000 | SANS Summit pass + hotel **per team member** (next 12 mo) + 1 SANS OnDemand course per member + SANS Webcast/Livestream presentation slot |
| **2nd — HUNTED EVIL** | $7,500 | Same as 1st |
| **3rd — FOUND EVIL** | $4,500 | 1 SANS OnDemand course per member |

Each project is eligible for max 1 prize. Multiple distinct submissions per entrant allowed.

**Non-cash value:** A single SANS Summit + hotel package easily exceeds $5K. OnDemand course is ~$8K retail. For a 5-person team winning 1st, the package is roughly $10K cash + (5 × ~$13K) ≈ **$75K total value**.

The SANS Webcast slot for 1st/2nd is rare currency — that's distribution to the entire SANS community. Career-altering for non-SANS-name builders.

## Judging — two stages

### Stage 1 (pass/fail viability)

> "The first stage will determine via pass/fail whether the ideas meet a baseline level of viability, in that the Project reasonably fits the theme and reasonably applies the required APIs/SDKs featured in the Hackathon."

Baseline:
- ✅ Built on / integrates with SANS SIFT Workstation
- ✅ Uses agentic framework as primary execution engine (Claude Code / OpenClaw preferred, others permitted)
- ✅ Demonstrates self-correction, accuracy validation, and analytical reasoning
- ✅ Linux terminal environment
- ✅ Substantially new work created Apr 15 – Jun 15 2026
- ✅ All 8 deliverables present

Most submissions will clear Stage 1. The placing is decided in Stage 2.

### Stage 2 (equally-weighted criteria)

Six criteria, equally weighted. **Autonomous Execution Quality is the tiebreaker** when scores tie.

| # | Criterion | Question judges ask | What to optimize | What to avoid |
|---|---|---|---|---|
| 1 | **Autonomous Execution Quality** (tiebreaker) | Does the agent reason about next steps, handle failures, and self-correct in real time? | The "Ralph Wiggum Loop" Rob T. Lee describes: tool errors → AI reads stderr → adjusts hypothesis → retries with different params. Demo this explicitly. | Linear scripts. "I prompted Claude to be careful." Infinite loops. Agents that retry the same broken command 5 times. |
| 2 | **IR Accuracy** | Are findings correct? Hallucinations caught and flagged? Confirmed findings distinguished from inferences? | Server-side parsing of tool output → typed objects. Confidence levels per finding. Self-reported hallucination rate vs ground truth. | LLM summarizing raw hex. Findings without artifact citations. "High confidence" labels everywhere. |
| 3 | **Breadth and Depth of Analysis** | How much case data can the agent handle? **Depth on fewer types beats shallow coverage of many.** | Pick 2-3 evidence types (disk + memory + network) and go deep with corroboration across them. | Touching 12 artifact types shallowly. Just running `vol.py pslist` and calling it done. |
| 4 | **Constraint Implementation** | Are guardrails architectural or prompt-based? Tested for bypass? | Custom MCP server with typed functions (the destructive command literally doesn't exist). Bwrap/sandbox isolation. Read-only mount enforcement. Deny rules at the harness level. | Putting "do not delete evidence" in CLAUDE.md and calling it a control. Allowing generic `Bash(...)` with `rm` not in the denylist. |
| 5 | **Audit Trail Quality** | Can judges trace any finding back to the specific tool execution that produced it? | JSONL audit log per tool call with `(ts, tool, args, hash, audit_id, examiner)`. Findings cite `audit_ids`. Multi-agent: per-message logs. HMAC-signed ledger for tamper detection. | Logs that only fire on agent stop. Findings without audit_ids. Reports that say "found X" without showing the command. |
| 6 | **Usability and Documentation** | Can another practitioner deploy and build on this? | One-liner install. README with clear setup. Architecture diagram identifying which pattern + where security boundaries live. README that another DFIR analyst would actually use. | Hardcoded paths. "Run this script" with 14 undocumented dependencies. Diagrams that don't show trust boundaries. |

### Tie-breaking

Per official rules:

> "For each Prize, if two or more Submissions are tied, the tied Submission with the highest score in the first applicable criterion listed above will be considered the higher scoring Submission."

Order:
1. Autonomous Execution Quality
2. IR Accuracy
3. Breadth and Depth
4. Constraint Implementation
5. Audit Trail
6. Usability

So if you must trade off, trade off Usability and Audit Trail before Autonomous Execution and IR Accuracy.

## The unwritten rubric (synthesized from judge analysis)

These don't appear in the rules but will move scores:

### 1. Measured hallucination reduction (the silent #1 differentiator)

Rob T. Lee's exact admission:

> "Protocol SIFT works. It also hallucinates more than we'd like. (That's exactly why this hackathon exists.)"

Translation: any submission that ships a **measured before/after hallucination rate** — with a clear methodology — wins IR Accuracy AND Constraint Implementation simultaneously. The bar today is "we say we constrain." A submission that says "we constrain, and here's the proof: baseline 18% hallucination on these 10 cases, ours 4%" stands out.

### 2. The senior-analyst sentence

Verbatim from the registration-open post — this is the rubric in one sentence:

> "Teach an AI agent to think like a senior analyst, how to sequence its approach, recognize when something doesn't add up, and self-correct when it gets it wrong."

Decompose:
- **Sequence its approach** → explicit workflow, hypothesis chaining, not one-giant-prompt
- **Recognize when something doesn't add up** → anomaly self-detection across multi-source corroboration
- **Self-correct when it gets it wrong** → the Ralph Wiggum Loop

### 3. The 14:27 time-to-finding benchmark

The [un]prompted demo set the anchor at "typing 'find evil' produced complete C-drive analysis in fourteen minutes twenty-seven seconds." Submissions noticeably slower will look weak. Submissions meaningfully faster with comparable depth look elite. **Build a benchmark harness early. Report numbers.**

### 4. SANS-style narrative (the FOR508 mental model)

The judges grew up on SANS FOR508 / FOR500. Whether they admit it or not, they will subconsciously evaluate against:
- Hypothesis-driven investigation (not kitchen-sink)
- Multi-artifact corroboration (never trust one source)
- Timeline-as-spine
- Known-good baseline subtraction
- Threat-intel grounding (MITRE ATT&CK named, not just IOCs)
- Defensible findings (every claim traces to artifact + timestamp)

### 5. Court-admissibility instincts

Multiple judges come from law-enforcement / expert-witness backgrounds (Ovie Carroll = DOJ Cybercrime Lab, Cheri Carr = expert witness "dozens of times" in fed/state courts, Amanda Rankhorn = ex-FBI senior forensics examiner). Protocol SIFT isn't court-admissible itself — but findings should look like they could survive cross-examination: hash-verified evidence, chain-of-custody, no overstated confidence.

### 6. Honesty > polish

Rob T. Lee publicly admitted his "47x" stat was reverse-engineered for vibes ("Yes, that's the actual reason it's 47 and not 48. I wish I had a more rigorous justification. I don't."). He rewards honesty about limitations. An accuracy report that **flags its own failures** beats one that pretends to be perfect.

### 7. Security of the agent itself

**Jens Ernstberger** (Kontext Security — runtime authorization for AI agents) and **Yotam Perkal** (Pluto Security — discovered CVE-2026-33032 "MCPwn", an MCP endpoint vuln) are on the panel. They will look at your MCP server for:
- Prompt injection in evidence (free-text fields the LLM reads)
- Credential handling and tool-call authorization
- Tool-call chaining attacks
- Privilege scoping

**Bake in: scoped credentials, short-lived tokens, deny-lists, sanitization of LLM-bound evidence fields. Mark these explicitly in the architecture diagram.**

## What disqualifies (Stage 1 rejects)

- Missing any of the 8 deliverables
- License other than MIT / Apache 2.0
- Demo video longer than 5 minutes that has no live terminal execution (slides / marketing videos = pass/fail FAIL)
- Project not built on / integrated with SIFT Workstation
- Doesn't demonstrate all three required qualities (self-correction, accuracy validation, analytical reasoning)
- Pre-existing work without clearly documented novel contribution

## What's at stake beyond cash

1. **Webcast distribution** to the SANS Community — career-altering distribution if you're not already a SANS name.
2. **Reintegration into Protocol SIFT** — Rob has said winning submissions "will be reviewed for integration back into Protocol SIFT." Whoever wins becomes the architectural reference.
3. **48-judge LinkedIn impressions** — Palo Alto, Mandiant, AWS, Lockheed, Deutsche Bank, ING, Hilton, Roblox, etc. all see your work.
