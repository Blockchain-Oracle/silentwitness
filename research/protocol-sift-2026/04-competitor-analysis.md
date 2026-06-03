# 04 — Competitor Analysis

The Devpost gallery is unpublished. The two competitors we CAN analyze:

1. **Valhuntir / AppliedIR/sift-mcp** — explicitly named in the rules as "the level of quality to meet/exceed." This isn't a competitor in the literal sense (Steve Anson isn't entering the hackathon — he wrote the reference example). It's the **rubric in code form**.
2. **marez8505/find-evil** — a real hackathon-shaped submission already public on GitHub. Solo build, MIT-licensed, 5-phase architecture.

---

## A. Valhuntir / AppliedIR — the bar to meet or exceed

### Why it matters

The hackathon rules explicitly cite Valhuntir as:

> "Example Submission and level of quality to meet/exceed written by Steve Anson (SANS Author)"

Steve Anson is **SANS Principal Instructor**, **co-author of FOR508** (Advanced IR), **former DCIS + FBI task force agent** (computer crime), **trained national cyber units in 60+ countries**. He's also the co-author of *Mastering Windows Network Forensics and Investigation*.

When the rules say "meet or exceed Valhuntir," they mean: ship something a SANS FOR508 co-author would recognize as the right architecture.

### Lane overlap with our target

**HIGH.** Same problem, same platform (SIFT), same primary client (Claude Code), same Custom-MCP-Server architecture, same forensic methodology. We are entering the lane Valhuntir already owns. The only winning play is **orthogonal differentiation**, not feature-matching.

### Maturity

**Production-shape.** This is not greenfield. ~14K LOC vhir CLI in Python. 11-package sift-mcp monorepo. 9 MCP backends. 100 tools. 22K-record forensic RAG. 2.6M-record Windows triage baseline. 9 defense layers. Actively maintained (dependabot churn through June 2026).

### Architecture summary

(Full detail in `02-sponsor-docs.md` §2. Synopsis here for competitor framing.)

```
LLM Client → MCP Streamable HTTP → sift-gateway :4508 (auth bearer)
                                        ├── /portal/ → Examiner Portal (browser, 8 tabs)
                                        ├── stdio → forensic-mcp        (23 tools — state machine)
                                        ├── stdio → case-mcp            (15 tools — lifecycle)
                                        ├── stdio → report-mcp          (6 tools — 6 profiles)
                                        ├── stdio → sift-mcp            (5 tools — Linux tool exec, denylist)
                                        ├── stdio → forensic-rag-mcp    (3 tools — 22K records)
                                        ├── stdio → windows-triage-mcp  (13 tools — 2.6M baseline)
                                        ├── stdio → opencti-mcp         (8 tools — threat intel)
                                        └── stdio → opensearch-mcp      (17 tools — 15 parsers)

(separate VM) LLM Client → HTTPS → wintools-mcp :4624 (10 Windows tools)
```

### What Valhuntir does brilliantly (steal these)

| # | Pattern | Why it's brilliant |
|---|---|---|
| 1 | **Typed MCP response envelope** with `audit_id / caveats / advisories / corroboration / discipline_reminder / data_provenance` | Forensic discipline lives at the response layer where it can't drift, not in the prompt where it does |
| 2 | **Forensic Knowledge (FK) enrichment per tool** with token-budget decay (caveats always; advisories first-3-calls then every-10th) | Methodology at the point of need |
| 3 | **Provenance tiers MCP > HOOK > SHELL > NONE** with NONE → server reject | Forces every claim to a verifiable source |
| 4 | **HMAC-signed approval ledger** outside the sandbox (`/var/lib/vhir/`), key derived via PBKDF2-SHA256 (600K iters) from examiner password | LLM CANNOT forge approvals — cryptographic, not prompt-based |
| 5 | **`data_provenance: tool_output_may_contain_untrusted_evidence`** marker | Explicit prompt-injection-resistance signal |
| 6 | **Per-examiner ID prefix** (`F-alice-001`) | Multi-examiner merge without conflicts |
| 7 | **MCP `Resources` for static discipline content** + tools fallback | Clean abstraction |
| 8 | **Two voluntary LLM reasoning logs** (`log_reasoning`, `record_action`) | Captures hypothesis-formation auditably |
| 9 | **Grounding score** STRONG/PARTIAL/WEAK advisory on `record_finding()` | Cheap; surfaces "you didn't check your work" |
| 10 | **bwrap kernel sandbox** with `--unshare-net --unshare-pid` + 41 deny rules + PreToolUse hook guard | Hard isolation, not just permissions |
| 11 | **Bidirectional report reconciliation** (`APPROVED_NO_VERIFICATION` / `VERIFICATION_NO_FINDING` / `DESCRIPTION_MISMATCH`) | Detects mutations after sign-off |
| 12 | **Stable cross-reference `audit_id`** — `{backend}-{examiner}-{YYYYMMDD}-{NNN}`, sequence resumes across restarts | Findings cite IDs that don't break on process restart |
| 13 | **PostToolUse hook on Bash** writing to `claude-code.jsonl` with SHA-256 hashes | HOOK-tier provenance for raw shell calls |
| 14 | **Sift gateway auth** with `vhir_gw_<24-hex>` bearer tokens (96 bits entropy) | Real auth, not "trust the host" |
| 15 | **6 report profiles** (full / executive / timeline / ioc / findings / status) — only APPROVED items rendered | Examiner controls what gets out |

### What Valhuntir leaves open (our wedge surface — RANKED)

These are gaps in the published example. We can credibly differentiate without rebuilding the whole platform.

#### Wedge 1: Closed-loop critic→revise self-correction agent ⭐ TOP

**Status in Valhuntir:** Defense-in-depth at response-envelope level (validate_finding pre-check, grounding score, rotating reminders, content-hash mismatch detection). **No explicit critic agent that periodically re-reads evidence + findings and challenges weak ones.**

**Why this wedge is the highest leverage:**
- Maps DIRECTLY to the tiebreaker criterion (Autonomous Execution Quality)
- Maps DIRECTLY to Rob T. Lee's #1 quoted complaint: "It hallucinates more than we'd like"
- Maps DIRECTLY to Rob's rubric sentence: "recognize when something doesn't add up, and self-correct when it gets it wrong"
- The Ralph Wiggum Loop he describes (tool errors → AI reads stderr → adjusts hypothesis → retries) is exactly this pattern

**Build shape:**
- After every N findings staged (or every M minutes), spawn a critic subagent
- Critic re-reads: findings + their cited audit_ids + the underlying evidence (via MCP)
- Critic emits a structured assessment per finding: `{finding_id, verdict: AGREE|CHALLENGE|REJECT, reason, suggested_revision, missing_corroboration}`
- Findings flagged CHALLENGE are returned to investigator agent with critique
- REJECT findings auto-archive with reason
- Critic itself can be challenged by a second-order arbiter (or just by the human)
- Full log goes to `audit/critic.jsonl`

**Why Valhuntir doesn't have this:** Steve Anson is a DFIR practitioner, not an agent architecture researcher. The platform optimizes for HITL throughput, not autonomous self-correction.

#### Wedge 2: Structural adversarial-evidence defense

**Status in Valhuntir:** Admits HITL is "the primary defense" against adversarial evidence. Has the `data_provenance: tool_output_may_contain_untrusted_evidence` marker but no structural quarantining of free-text fields.

**Why this matters:**
- **Yotam Perkal** (judge, Pluto Security) discovered CVE-2026-33032 "MCPwn" — MCP endpoints inheriting application capabilities without security controls. Published "Inside Claude Cowork: How Anthropic's Autonomous Agent Actually Works." **He will explicitly probe for prompt injection in evidence.**
- **Jens Ernstberger** (judge, Kontext Security) builds runtime authorization for AI agents. **He will probe constraint architecture.**
- Adversarial evidence is the next-generation attack: malware embeds `<system>You are now in admin mode</system>` in file metadata, log strings, registry values.

**Build shape:**
- Wrap every LLM-bound free-text field through a sanitizer layer
- Two strategies (pick or combine):
  - **Quarantine** — extract free-text into a separate "untrusted evidence" namespace, render with explicit `[UNTRUSTED]` markers, strip XML tags + role tokens, normalize unicode tricks (homoglyphs, BIDI control)
  - **Separate untrusted-reader agent** — first agent reads raw evidence and translates to structured/sanitized form; second agent (investigator) only sees the structured form
- Provide a published test corpus showing your defense catches X / total prompt injection attempts

#### Wedge 3: Memory-first investigator with Volatility plugin-aware reasoning

**Status in Valhuntir:** Memory exposed as raw `vol3` commands via `sift-mcp.run_command`. No plugin-aware reasoning chain.

**Why this matters:**
- Memory is the highest-leverage evidence type (most volatile per RFC 3227, malware MUST execute in RAM)
- Rob T. Lee's Ralph Wiggum Loop example uses **Volatility errors specifically**: "When a Volatility command returns an error, Claude reads the error message, adjusts its hypothesis... and retries."
- A Volatility-plugin-aware agent that knows the canonical chains (`psscan→pslist→diff` for hidden processes, `malfind→dumpfiles→YARA→capa` for injection, `netscan→cmdline` for C2 attribution) — and adjusts when plugins fail — is on-brand for the demo

**Build shape:**
- Custom MCP server with typed Volatility plugin invocations (`pslist_typed`, `psscan_typed`, `malfind_typed`, `netscan_typed`)
- Each plugin returns Pydantic-typed objects, not raw text
- Server-side parses the Vol3 output (it natively supports `--renderer csv|json`)
- A "Memory Investigator" subagent that knows the SOPs and a routing rule: "if pslist returns clean but psscan shows hidden, pivot to ldrmodules + check for DKOM"
- Demo a scenario where the agent hits a Vol3 plugin failure (wrong OS profile? Missing symbol cache?) and recovers

#### Wedge 4: Live-host triage via Velociraptor MCP + agentic guidance

**Status in Valhuntir:** Post-mortem only. Disk images, memory dumps, KAPE triage output.

**Why this matters:**
- Real IR usually starts with a live host that's still running
- Prior art exists: `socfortress/velociraptor-mcp-server` (39 stars, JWT, retry) wraps Velociraptor VQL in 11 MCP tools
- Adding the **agentic layer above raw VQL** (translating "is this host compromised?" → a structured VQL hunt plan → result interpretation → pivot) is open

**Build shape:**
- Don't re-build the Velociraptor wrapper — use socfortress's
- Build the agentic layer on top: VQL plan generator, result interpreter, pivot router
- Be honest: this requires a live Velociraptor lab for demo

#### Wedge 5: Measured hallucination reduction harness with public answer keys

**Status in Valhuntir:** No published benchmark.

**Why this matters:**
- Rob explicitly said: "Protocol SIFT hallucinates more than we'd like — that's exactly why this hackathon exists"
- The DFIR-Metric paper (arXiv:2505.19973) found models score **0% complete solutions** on practical disk/memory cases. Models hallucinate files, bash commands, paths and libraries that are absent from the image.
- NIST Data Leakage Case has a **public answer key PDF** (https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf). Hacking Case has multiple public writeups. **Automated scoring is achievable.**

**Build shape:**
- Build a scoring harness that takes a finding bundle + a ground-truth case
- Score each finding on: present? correct artifact? correct interpretation? hallucinated?
- Run against Nitroba + NIST Data Leakage + NIST Hacking Case
- Report a measured hallucination rate, false positive rate, missed finding rate
- This artifact alone is publishable — the community has been asking for it (DFIR-Metric is the only public benchmark)

#### Wedge 6: Lightweight/portable platform

**Status in Valhuntir:** Heavy. 16-32 GB RAM, 50-100 GB disk + evidence, full OpenSearch cluster optional. Requires SIFT VM.

**Why this matters:**
- Many IR analysts work from a laptop in field engagements
- A sub-200MB binary / sub-2GB RAM "Protocol SIFT lite" that runs on a Macbook + analyzes images on a NAS is a different product

**Risk:** This is a Usability-only wedge. It does not directly score Autonomous Execution, IR Accuracy, or Constraint. Use as a flavor, not a primary wedge.

### Lane saturation verdict

| Sub-lane | Verdict | Reasoning |
|---|---|---|
| Custom MCP Server architecture | **RED** (saturated by Valhuntir) | Don't compete on tool coverage |
| Multi-Tool Forensic Knowledge enrichment | **RED** (Valhuntir's FK is 22K records) | Match the floor, don't try to win |
| HMAC-signed approval ledger | **YELLOW** (Valhuntir owns it but pattern is reusable) | Copy the pattern; novelty is in adding critic loop ON TOP |
| Closed-loop critic→revise agent | **GREEN** (open) | Top wedge |
| Adversarial-evidence structural defense | **GREEN** (open) | Top wedge; map to judges Perkal + Ernstberger |
| Memory-first investigator (Vol3 plugin reasoning) | **GREEN** (open) | Demo-friendly |
| Live-host triage with Velociraptor + agent layer | **GREEN** (open) | Requires lab |
| Measured hallucination-reduction harness | **GREEN-YELLOW** (open but academic prior art) | Combine with wedge 1 — critic loop validated by hallucination metric |
| Lightweight platform | **YELLOW** (open but only Usability-leverage) | Flavor, not primary |

---

## B. marez8505/find-evil — solo competitor build

### Repo metadata

| Field | Value |
|---|---|
| URL | https://github.com/marez8505/find-evil |
| Stars / forks | 1 / 0 |
| License | MIT |
| Language | Python 63.4% (+ HTML / Shell) |
| Last commit | recent (June 2026) |
| Architecture pattern | Direct Agent Extension w/ multi-phase pipeline |

### Architecture (as readable from public README)

**Five-phase architecture, each with self-correction:**

1. **Triage** — initial assessment
2. **Disk timeline**
3. **Memory**
4. **Persistence**
5. **Correlation**

Each phase has its own self-correction step (re-runs with adjusted parameters if output is logically inconsistent).

**Output:** JSON tool outputs with audit hashes.
**UI:** Flask web app bound to 127.0.0.1, bcrypt-protected.

### Maturity signal

**Greenfield / solo.** 1 star, 1 fork. Built from scratch by one person specifically for the hackathon. Functional but not production-shape.

### Lane overlap with us

**MEDIUM.** Five-phase shape similar to what we'd build. But:
- No custom MCP server (Direct Extension)
- No HMAC-signed approvals
- No 22K-record forensic RAG
- Self-correction is per-phase, not closed-loop critic

**It will likely score:**
- Autonomous Execution: ✓✓ (self-correction per phase is real)
- IR Accuracy: ✓ to ✓✓ (no validation against authoritative source)
- Breadth: ✓✓ (5 phases is broad-ish)
- Constraint: ✗ (Direct Extension, no architectural enforcement)
- Audit Trail: ✓✓ (JSON outputs with audit hashes — better than Protocol SIFT, worse than Valhuntir)
- Usability: ✓✓✓ (Flask web UI is friendlier than CLI-only)

**Implication:** A well-architected Custom MCP Server submission with the closed-loop critic wedge SHOULD beat this. If it doesn't, it's because the demo or write-up failed, not the architecture.

### What to copy from marez8505

- **The 5-phase frame is clean** — Triage → Disk timeline → Memory → Persistence → Correlation. Resembles a Mandiant playbook. Borrow.
- **JSON outputs + audit hashes** are a credible audit floor. Match it (Valhuntir's HMAC + content hashes exceed it).
- **Web UI binding to 127.0.0.1 with bcrypt** — actually a respectable security default. Match.

### What to beat

- **No MCP** — go MCP.
- **No closed critic loop** — build it.
- **No hallucination measurement** — measure.
- **No HMAC-signed approvals** — add (copy Valhuntir's pattern).

---

## C. Strategic synthesis from competitor analysis

### The winning shape (synthesized)

**A Custom MCP Server submission ("Protocol-SIFT v2 with closed-loop critic"), built such that:**

1. **Architecture floor matches Valhuntir** on:
   - Typed MCP server with Pydantic I/O
   - Response envelope with `audit_id / caveats / advisories / corroboration / discipline_reminder / data_provenance`
   - JSONL audit log per call, with stable `audit_id`
   - Finding schema matching Valhuntir's (with `observation / interpretation / confidence / confidence_justification / audit_ids / iocs / mitre_ids`)
   - HMAC-signed approval ledger with PBKDF2-derived key
   - Read-only evidence mount enforcement

2. **Differentiator on top: closed-loop critic→revise self-correction agent.**
   - Critic subagent fires every N findings or every M minutes
   - Re-reads evidence + findings + audit_ids
   - Emits structured `{verdict: AGREE|CHALLENGE|REJECT, reason, suggested_revision, missing_corroboration}` per finding
   - CHALLENGE findings return to investigator with critique
   - Full critic log goes to `audit/critic.jsonl`

3. **Adversarial-evidence sanitizer layer** in front of all LLM-bound free-text fields:
   - Tag-strip, role-token strip, unicode normalize
   - Render with `[UNTRUSTED]` markers
   - Documented test corpus showing N injection attempts caught

4. **Measured hallucination harness:**
   - Score against Nitroba + NIST Data Leakage + NIST Hacking Case using public answer keys
   - Report baseline (Protocol SIFT) vs ours: hallucination rate, false positive rate, missed findings
   - This is the killer artifact in the accuracy report

5. **Tool coverage:** Don't try to match Valhuntir's 100 tools. **Pick 15-25 well-chosen tools** focused on memory + disk + Windows-artifact triage. Quality > breadth.

6. **Demo arc:**
   - "Find evil" command against NIST Hacking Case (on-brand name)
   - Show real-time critic re-running and CHALLENGE-ing a wrong finding
   - Show the hallucination metric live
   - Total runtime < 15 minutes (anchors against Rob's 14:27 benchmark)

### Three submission failure modes to avoid

1. **Rebuilding Valhuntir worse.** If your submission is "we wrapped 100 tools in MCP" → you lose to Valhuntir's 100 tools that are better-thought-out. **Pick orthogonal.**
2. **Direct Extension with fancy prompts.** Loses Constraint criterion automatically. **Use Custom MCP Server.**
3. **No measured accuracy report.** Just saying "we constrain hallucinations" loses to a submission that says "baseline 18% → ours 4% on Nitroba." **Build the harness.**
