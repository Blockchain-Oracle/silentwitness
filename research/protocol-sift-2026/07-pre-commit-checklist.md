# 07 — Pre-Commit Checklist

A go/no-go review before committing 13 days to this hackathon. Each section gates the next.

## §1. The hackathon is real and legitimate

- [x] **Sponsor verifiable** — SANS Institute (495 Lowell St, Lexington MA), 18 years of DFIR community work
- [x] **Prize pool real** — $22K cash + courses worth ~$13K/member + Summit pass + webcast slot. Total realistic value $50-75K for 1st-place 5-person team.
- [x] **Listing live** — findevil.devpost.com, accessible, 3,861 registered participants
- [x] **Sponsor activity authentic** — Rob T. Lee's substack posts, SANS blog post, press release, [un]prompted YouTube talk, X engagement, NotebookLM share, 48-judge panel
- [x] **Rules complete + machine-readable** — full rules at findevil.devpost.com/rules
- [x] **No scam signals** — no pay-to-enter, no upsell, no captive code review, no token-locked submission, public open-source license required

**Verdict: LEGITIMATE.** This is a SANS-flagship hackathon, first of its kind for them.

## §2. Hidden-field check passed

- [x] **Devpost gallery is unpublished** until after Jun 15 close. Implication: blind competition, all builders working without competitor intel. EQUAL playing field.
- [x] **Known public competitors mapped:**
  - Valhuntir / AppliedIR (the bar, not a competitor) ← reference
  - marez8505/find-evil (1 star, solo build, Direct Extension) ← beatable
- [x] **Lane saturation analyzed** (see `06-hidden-field.md`):
  - 🔴 Tool coverage breadth (Valhuntir owns)
  - 🟢 Closed-loop critic agent (open)
  - 🟢 Adversarial-evidence defense (open)
  - 🟢 Memory-first Vol3 reasoning (open)
  - 🟢 Hallucination harness (open)
  - 🟢 Real-time HUD (open)
- [x] **Wedge identified:** Custom MCP Server + closed-loop critic + hallucination harness + adversarial-evidence sanitizer

**Verdict: WEDGE EXISTS. Field is not pre-won.**

## §3. Winner shape understood

- [x] **No prior winners** (first edition). Winning-shape proxied through Valhuntir architecture (see `05-prior-winners.md`)
- [x] **Judging rubric decoded** (see `01-prizes-tracks.md`):
  - 6 equally-weighted criteria, **Autonomous Execution Quality is the tiebreaker**
  - Closed-loop critic agent directly maps to tiebreaker + Rob T. Lee's #1 quoted complaint
- [x] **Judge psychology mapped** (see `refs/judges.md`):
  - Rob T. Lee (CAIO SANS) — primary; wants senior-analyst sequencing + Ralph Wiggum Loop + measurable hallucination reduction
  - Ovie Carroll / Cheri Carr / Amanda Rankhorn — court-admissibility instincts
  - Yotam Perkal / Jens Ernstberger — will audit MCP server itself for security
  - Adam Nasreldin / 14+ enterprise SOC judges — want production-shape, not research demo
- [x] **Unwritten rubric mapped:** measured hallucination rate, 14:27 time-to-finding anchor, SANS-style narrative, court-admissibility, honesty over polish

**Verdict: WINNER SHAPE CLEAR.**

## §4. Sponsor docs / primitives available

- [x] **Protocol SIFT install** — `curl -fsSL https://raw.githubusercontent.com/teamdfir/protocol-sift/main/install.sh | bash` works on SIFT VM
- [x] **SIFT OVA available** — sans.org/tools/sift-workstation, free download
- [x] **MCP Python SDK** — `mcp` on PyPI, fully documented, used in Valhuntir
- [x] **Claude Code / Agent SDK** — Python + TS, MCP-native
- [x] **Sample case data** — sansorg.egnyte.com/fl/HhH7crTYT4JK (private starter cases)
- [x] **Public validation datasets** — Nitroba (60 MB pcap), NIST Data Leakage (20 GB + answer key PDF), NIST Hacking Case (DD images + writeups)
- [x] **Valhuntir reference code** — github.com/AppliedIR/Valhuntir + sift-mcp + wintools-mcp + opensearch-mcp, MIT-licensed, study-able
- [x] **Slack + Discord** — community channels live

**Verdict: PRIMITIVES READY.**

## §5. Build feasibility in ~13 days (solo or small team)

- [x] **Total time:** Apr 15 – Jun 15 = 61 days. We are starting June 2 = **13 days remaining.**
- [x] **Effort estimate** (per `06-hidden-field.md`):
  - Custom MCP server with 15-25 tools: 4 days
  - Closed-loop critic→revise subagent: 3 days
  - Adversarial-evidence sanitizer: 1.5 days
  - Hallucination-rate harness vs Nitroba + NIST Data Leakage + NIST Hacking Case: 2.5 days
  - Court-admissibility annotation: 0.5 day
  - Real-time HUD: 2 days (optional, drop if time)
  - Docker compose install: 0.5 day
  - Demo video + write-up + architecture diagram + accuracy report: 2 days
  - **Total: ~13-15 days** ← tight but doable with discipline
- [⚠️] **Risk:** Solo build is tight. With 2 people, comfortable.
- [⚠️] **Dependency:** SIFT VM needs to download (~20 GB). Should start TODAY.

**Verdict: FEASIBLE WITH DISCIPLINE.** Solo possible but high-effort. Team of 2-3 ideal.

## §6. Personal fit / motivation

(Self-assess. Skip if not relevant.)

- [ ] Have we previously built MCP servers? (If yes, big head start.)
- [ ] Have we used Volatility 3, plaso, EZ Tools? (If no, allow 1-2 days for SIFT familiarization.)
- [ ] Have we written agentic systems before? (If no, allow 1-2 days for Claude Code / Agent SDK.)
- [ ] Is "DFIR + AI agent architecture" a domain we want to be known for? (If yes — webcast slot + winner-becomes-standard is the real prize. If no — the wedge is still real but less aligned.)

## §7. Architectural pre-commits (DO NOT skip these — they shape the whole build)

| Pre-commit | Choice | Rationale |
|---|---|---|
| **Framework pattern** | Custom MCP Server (Python, FastMCP) + Claude Code as client | Architectural guardrail wins Constraint. Direct Extension loses it. |
| **MCP transport** | stdio (subprocess pipes) for local, optional Streamable HTTP for remote | Match Valhuntir's pattern for credibility |
| **Tool I/O typing** | Pydantic models, strict | Schema = contract = no hallucinated args |
| **Response envelope** | `{success, data, audit_id, examiner, caveats, advisories, corroboration, discipline_reminder, data_provenance}` | Copy Valhuntir verbatim |
| **Finding schema** | Match Valhuntir (`F-<examiner>-<NNN>` IDs, `observation/interpretation/confidence/audit_ids/iocs/mitre_ids`) | The judges' mental model |
| **Audit log** | JSONL per backend in `case/audit/<backend>.jsonl`, stable `audit_id` = `{backend}-{examiner}-{YYYYMMDD}-{NNN}` | Copy Valhuntir verbatim |
| **Approval gate** | HMAC-SHA256 over substantive text + PBKDF2-derived key from examiner password, stored outside sandbox at `/var/lib/<our_name>/verification/` | Copy Valhuntir verbatim |
| **Provenance tiers** | MCP > HOOK > SHELL > NONE; NONE → server rejects finding | Copy Valhuntir verbatim |
| **Evidence mount** | `ro,noexec,nosuid` enforced at path validation in MCP tool definitions | Architectural, not prompt |
| **Sandbox** | bwrap (`--unshare-net --unshare-pid --bind /evidence/ /evidence/`) for the Claude Code client | Copy Valhuntir verbatim |
| **Deny rules** | Claude Code `.claude/settings.json` deny block for `Edit/Write` to case state files + `Bash(*vhir approve*)` patterns | Copy Valhuntir's 41-rule template |
| **Critic agent** | Subagent fires every 5 staged findings OR every 10 min; produces `{verdict, reason, suggested_revision, missing_corroboration}` per finding | OUR DIFFERENTIATION — wedge 1 |
| **Adversarial-evidence sanitizer** | Strip XML tags, role tokens, normalize unicode (homoglyph, BIDI), render with `[UNTRUSTED]` markers | OUR DIFFERENTIATION — wedge 3 |
| **Hallucination harness** | Score against Nitroba + NIST Data Leakage (public answer key PDF) + NIST Hacking Case (public writeups); report precision, recall, hallucination rate | OUR DIFFERENTIATION — wedge 2 |
| **License** | MIT | Required by rules |
| **Tooling primary tools (target 15-25)** | Volatility 3 (8 plugins), EZ Tools (8), Hayabusa, log2timeline + psort, YARA, bulk_extractor, RegRipper, fls/icat/mmls | Balanced disk + memory + log + carving coverage |
| **MITRE ATT&CK** | Tag every finding with MITRE IDs from `attack.mitre.org` v17+ | Required as table-stakes |

## §8. The 8 mandatory deliverables — production plan

| # | Deliverable | Plan |
|---|---|---|
| 1 | Public GitHub repo (MIT/Apache) | `<our_name>` org. MIT license. README with one-liner install + architecture + demo gif. |
| 2 | Demo video ≤ 5 min | Screencast: SIFT VM → start MCP server → "find evil" against NIST Hacking Case → live critic CHALLENGE moment → finding rendered with court-admissibility note → hallucination metric live → final report. Audio narration walks through. **Must show one self-correction sequence (this is in the rules).** |
| 3 | Architecture diagram | Mark architectural vs prompt-based boundaries explicitly. Show: SIFT tools → MCP backends → gateway → Examiner Portal + critic subagent + sanitizer layer. Diagram tool: Mermaid (committed in README) + draw.io export PNG. |
| 4 | Written description (Devpost story) | "What it does / How you built it / Challenges / What you learned / What's next." Tell the wedge story: "Valhuntir is the bar; we add the closed-loop critic and the hallucination harness." |
| 5 | Dataset documentation | Nitroba + NIST Data Leakage + NIST Hacking Case used. Hashes confirmed. Acquisition + verification steps. |
| 6 | Accuracy report | Headline: hallucination rate vs Protocol SIFT baseline on each of the 3 datasets. Methodology. Section on adversarial-evidence sanitizer test corpus. Be honest about misses. |
| 7 | Try-It-Out instructions | `docker compose up`. Or: SIFT VM + `bash install.sh`. Step-by-step in README. |
| 8 | Agent execution logs | `audit/*.jsonl` per backend + `audit/critic.jsonl`. Include in repo as a frozen example case run. |

## §9. Go / No-Go decision

| Gate | Status |
|---|---|
| Hackathon legitimate | ✅ |
| Wedge exists | ✅ |
| Winner shape clear | ✅ |
| Sponsor primitives available | ✅ |
| Feasible in 13 days | ⚠️ (with team of 2-3, comfortable) |
| Personal fit | (self-assess) |

**Default verdict: GO.** Caveat: solo build is tight for the full wedge stack. If solo, drop wedges 4 (memory-first Vol3 reasoning) and 6 (real-time HUD), keep 1+2+3+5+7.

## §10. Day-1 immediate actions (if GO)

1. Download SIFT OVA (~20 GB) — start now, takes hours
2. `git clone --depth 1 https://github.com/teamdfir/protocol-sift /tmp/protocol-sift` and read
3. `git clone --depth 1 https://github.com/AppliedIR/Valhuntir /tmp/valhuntir` and read
4. Join Protocol SIFT Slack + Discord (handles + lurk for signal)
5. Download Nitroba pcap (60 MB) for smoke-test dataset
6. Read NIST Data Leakage answer key PDF cover-to-cover
7. Set up local Python env with `mcp`, `pydantic`, `claude-code-sdk`
8. Sketch the architecture diagram (whiteboard photo OK initially)
9. Write the SPEC file: target wedges + tool list + deliverable plan
10. Start the GitHub repo, push initial README — public from day 1 demonstrates commitment + invites collaborators
