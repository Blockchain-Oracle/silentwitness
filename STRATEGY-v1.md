# STRATEGY — Find Evil! / Protocol SIFT 2026

> **The commit document.** Research → first-principles → novelty check → DECISION.
> Read `research/protocol-sift-2026/CONTEXT.md` first for facts; this file is the commitment.
> Written 2026-06-02. Submission deadline 2026-06-15 11:45 PM EDT. **13 days to ship.**

---

## TL;DR — the wedge in one paragraph

**We build "EVIDENCE-LOCKED FINDINGS" — an MCP-server-side architectural gate that rejects any forensic finding whose claims cannot be verified, byte-for-byte, against the cited tool-execution output stored on disk.** Valhuntir (the published bar) has eight overlapping integrity gates — schema validation, audit-ID existence, evidence registry, provenance chains, HMAC signing, bidirectional report reconciliation, grounding-MCP presence score, IOC regex extraction — but ALL EIGHT assume the LLM's claim text is honest about the evidence it cites. None of them open the cited tool output and check the claim against its bytes. We add the missing seam: at `record_finding()` time, the server loads the cited audit output, substring-verifies cited spans, NER+regex-extracts entities from the observation text, and **rejects findings whose entities don't appear in cited evidence.** Hallucination stops being something we *mitigate*. It becomes something the architecture *cannot represent*. Plus a closed-loop critic agent (catches conceptual errors that evidence-lock doesn't), an adversarial-evidence sanitizer (judge-resonance with Yotam Perkal + Jens Ernstberger), and a head-to-head accuracy harness on NIST + Nitroba showing concrete baseline hallucinations our system refuses to make.

---

## §1 The atomic problem (first-principles)

**Rob T. Lee said it out loud:** *"Protocol SIFT works. It also hallucinates more than we'd like. That's exactly why this hackathon exists."*

The atomic problem is:
> **Make an LLM-driven forensic agent produce findings that cannot be hallucinated, where every claim traces to a specific artifact, while operating close to adversary speed and producing output a senior analyst would defend in court.**

Stripping to bedrock:

1. A forensic finding is a *claim* about evidence. Not a fact — an interpretation.
2. LLMs produce text that may or may not correspond to reality. Irreducible.
3. Tool outputs are deterministic — running `vol pslist` against the same dump = same bytes. The output IS a fact.
4. Verifying a claim against evidence is computable: substring match + entity lookup.
5. Judges score correctness, traceability, and constraint architecture — not breadth, not polish, not LOC.
6. The hackathon is a writing exercise as much as a coding exercise. 4 of 8 deliverables are communication artifacts.
7. ~3,861 registered participants. Most won't finish. Most who finish will build "Valhuntir but smaller." **Winning requires being categorically different, not incrementally better.**

The cross-domain analog is the same problem compilers solved with type systems, databases with constraints, and constrained-decoding LLM frameworks with grammar enforcement: **make the bad outcome structurally impossible, not "discouraged" by policy.**

Apply it to forensic findings.

---

## §2 The architecture — three-layer Investigation Record

The unit of output is NOT a Finding. It's an **Investigation Record** with three layers:

### Layer 1 — OBSERVATION (architecturally verified)
- "What was seen" — must be derivable from cited tool output.
- Every observation cites `cited_spans`: `[{audit_id, sha256_of_output, line_start, line_end, span_text}]`.
- **Server verifies** at `record_finding()` time:
  - Cited audit_id exists in the audit log
  - SHA256 of stored output matches what was cited (catches modified-after-citation)
  - `span_text` is a verbatim substring of the cited line range
  - All entities (IPs, hashes, file paths, registry keys, process names, account names) in `observation` text appear somewhere in the cited spans
- **Verdict gate:** `OK` / `SPAN_NOT_FOUND` / `ENTITY_HALLUCINATED` / `OUTPUT_MUTATED`
- If not OK → finding REJECTED, not staged.

### Layer 2 — INTERPRETATION (reasoned, structurally marked)
- "What it means" — inferential layer.
- Allowed to make leaps beyond the literal observation (this is what senior analysts do).
- Required fields: `confidence: HIGH|MEDIUM|LOW|SPECULATIVE`, `confidence_justification`, `what_would_change_this_confidence`.
- Cannot exist without a parent Observation.
- **Server runs the closed-loop critic** against the Interpretation + its Observation + the cited evidence. Critic returns `AGREE` / `CHALLENGE` / `REJECT`. CHALLENGE returns to investigator with critique; REJECT auto-archives.

### Layer 3 — NARRATIVE (the analytical-reasoning rubric)
- The investigative arc — required first-class structured field.
- Includes: starting hypothesis, evidence pursued, **at least one pivot** (a hypothesis abandoned because evidence contradicted it), dead-ends, final synthesis.
- References Observations and Interpretations by ID.
- This is the "structured investigative narrative, not raw execution log" the rules explicitly require — and what most submissions will treat as cosmetic.

### Plus three supporting mechanisms

| Mechanism | What it does | Why it's there |
|---|---|---|
| **Adversarial-evidence sanitizer** | Strips XML role tokens, BIDI controls, homoglyph tricks, prompt-injection patterns from any LLM-bound free-text evidence field. Renders with `[UNTRUSTED]` markers. | Yotam Perkal (MCPwn CVE) + Jens Ernstberger (Kontext) will probe the MCP for prompt injection. Bake the defense in architecturally. |
| **HMAC-signed approval ledger** (Valhuntir pattern, copied verbatim) | PBKDF2-SHA256 (600K iters) key from examiner password; HMAC-SHA256 over substantive text; stored at `/var/lib/protocol-sift-v2/verification/<case_id>.jsonl` outside the LLM sandbox. | Cryptographic > policy. LLM cannot forge approvals because it doesn't have the password. |
| **Head-to-head accuracy harness** | Runs vanilla Protocol SIFT + our system against Nitroba + NIST Data Leakage + NIST Hacking Case. Captures every claim each makes; classifies each as TP / FP / HALLUCINATION / FN against ground truth. | The killer artifact in the accuracy report. Concrete examples > metrics. |

---

## §3 What's genuinely new vs. what we honestly cite

The novelty check (`research/protocol-sift-2026/.raw/05-novelty-check.md`) surfaced two prior arts we MUST cite to avoid getting dismissed:

| Prior art | What they do | What we add |
|---|---|---|
| **Pydantic + Instructor `@field_validator` citation pattern** (Nov 2023, [python.useinstructor.com](https://python.useinstructor.com/blog/2023/11/18/validate-citations/)) | SDK-layer substring validator — Pydantic field validator does `if v in text_chunk` substring check; raises ValueError on mismatch | We port from SDK-layer to **MCP-server gate layer**. Substrate is **forensic tool-execution audit_ids** (not arbitrary text chunks). We add the **NER+regex entity gate** that pure substring doesn't have. We're inside a forensic MCP architecture (Valhuntir-shape) where the gate is integrated with HMAC ledger, examiner approval, audit log. |
| **NABAOS Tool Receipts** (March 2026, arXiv:2603.10060) | Runtime generates HMAC-signed tool execution **receipts** the LLM cannot forge. Cross-references LLM claims against receipts. 94% detection of fabricated tool references. Post-hoc detection (<15ms overhead). | NABAOS attests **that a tool was called**. We attest **the specific bytes of the tool's output**. NABAOS detects post-hoc. We **reject at server-gate before the finding is staged**. Plus the entity gate (NABAOS has no equivalent). |

What is **net-new** in our combination:
1. **MCP-server-side hard rejection at `record_finding()`** (not advisory; not SDK-optional; not post-hoc)
2. **Forensic tool-execution audit_ids as the citation substrate** (not arbitrary text chunks)
3. **NER+regex entity gate** that catches hallucinated entities (IPs, hashes, paths, process names) even when the claim text paraphrases the evidence accurately
4. **Deployed inside the SIFT/Valhuntir architecture** whose eight existing integrity gates demonstrably stop one step short of this verification

Frame the pitch as: *"We apply a known RAG-citation-verification pattern (Instructor) at the MCP-server gate layer, extending NABAOS-style execution attestation to content attestation, layering an entity gate the upstream patterns lack, against a SANS-grade benchmark."*

This is honesty + sharp differentiation. Judges who look up Instructor in 30 seconds will see we cited it.

---

## §4 Why this wins each judging criterion

| Criterion | Our angle | Score expectation |
|---|---|---|
| **Autonomous Execution Quality** (tiebreaker) | Closed-loop critic→revise + the Ralph Wiggum Loop (Volatility error → adjust → retry) explicit in demo. The CRITIC challenging a wrong Interpretation IS the self-correction moment. | ✓✓✓ |
| **IR Accuracy** | Hallucinations are *architecturally rejected*, not "mitigated." Head-to-head harness produces concrete examples: "baseline hallucinated X; ours refused." Honesty: any miss we have is documented. | ✓✓✓ |
| **Breadth and Depth** | Don't try to match Valhuntir's 100 tools. Pick 15-25 well-chosen tools: memory (Volatility 3 — plugin-aware reasoning), disk (Sleuth Kit + EZ Tools), Windows artifacts (Hayabusa Sigma), network (Zeek + Suricata). Depth on memory + disk + Windows beats shallow coverage of all. | ✓✓ |
| **Constraint Implementation** | Architecturally impossible-to-hallucinate findings. Bwrap kernel sandbox + 41 deny rules (Valhuntir pattern) + typed MCP I/O + Citation gate + Verification gate + Entity gate + Sanitizer. **Six layers, three of them novel.** | ✓✓✓ |
| **Audit Trail Quality** | Per-tool-call JSONL with stable `audit_id` (Valhuntir pattern). Every finding cites audit_ids that resolve back to tool calls with SHA256-hashed outputs. Critic logs in `audit/critic.jsonl`. Sanitizer logs flagged-and-stripped patterns. HMAC ledger outside sandbox. | ✓✓✓ |
| **Usability and Documentation** | One-liner `docker compose up`. Clean README. Architecture diagram with security boundaries explicitly labeled (architectural vs prompt). Quote bank for the demo. Reproducible by other practitioners. | ✓✓ |

A submission that scores ✓✓✓ on the top 3-4 criteria (especially the tiebreaker) wins.

---

## §5 The 13-day build plan

Today: 2026-06-02 (Mon)
Deadline: 2026-06-15 23:45 EDT (Sun)

| Day | Date | Goal | Deliverable end-of-day |
|---|---|---|---|
| 1 | Tue Jun 2 | SETUP. SIFT VM download (background, ~hours). Clone all sponsor + reference repos. Read Valhuntir architecture docs + `_extract_all_iocs` code. Project skeleton: Python repo, MIT license, README stub, MCP server skeleton with FastMCP. | Empty MCP server running on stdio. SIFT VM ready. Notebook of architecture decisions. |
| 2 | Wed Jun 3 | **Layer 1 — Observation gate.** Implement `record_observation()` with citation gate + verification gate. SHA256-of-normalized-output indexing. Substring verification. Unit tests with mock tool outputs. | Tool: `record_observation` rejects unverified claims. Demo on 2-3 hand-crafted test cases. |
| 3 | Thu Jun 4 | **Entity gate.** NER + regex extractors for: file paths (Windows + Linux), IPs (v4 + v6), hashes (MD5/SHA1/SHA256), registry keys, process names, account names, email addresses, URLs. Plug into `record_observation()`. Eval on known-good + known-bad observations. | Entity gate operational. Tunable false-positive rate. |
| 4 | Fri Jun 5 | **Tool MCP server.** Wrap 8 high-leverage tools as typed MCP functions: `vol_pslist`, `vol_pstree`, `vol_malfind`, `vol_netscan`, `vol_cmdline` (memory), `mft_parser` (MFTECmd), `evtx_parser` (EvtxECmd), `amcache_parser`. Each: Pydantic-typed I/O, server-side parse, JSONL audit log entry, full output persisted to disk. | First 8 tools usable end-to-end. Audit trail working. |
| 5 | Sat Jun 6 | **More tools + Sigma.** 7 more tools: `prefetch_parser` (PECmd), `shimcache_parser`, `regripper_run`, `yara_scan`, `bulk_extractor_run`, `hayabusa_csv_timeline`, `chainsaw_hunt`. Same shape. | 15 tools total. Verify Hayabusa pipeline. |
| 6 | Sun Jun 7 | **Layer 2 — Interpretation + critic.** Implement `record_interpretation()`. Build the critic subagent (separate Anthropic API call, system prompt of `refs/sdk-snippets.md` §3). Wire critic to fire every 5 staged interpretations. Critic logs to `audit/critic.jsonl`. | Critic challenging weak interpretations live. |
| 7 | Mon Jun 8 | **Layer 3 — Narrative + adversarial sanitizer.** `record_narrative()` with required pivot field. Adversarial-evidence sanitizer (`sanitize_evidence_text` from snippets). Wire into all evidence-reading tools. Test with prompt-injection payloads embedded in fake EVTX strings. | Three-layer record working end-to-end. Sanitizer catching test payloads. |
| 8 | Tue Jun 9 | **HMAC approval ledger + Examiner UI.** Copy Valhuntir's `verification.py` pattern. PBKDF2 600K-iter, HMAC-SHA256, mode 0600 storage at `/var/lib/protocol-sift-v2/verification/`. Minimal CLI for `approve <finding_id>`. Optional: streaming HUD (Flask + Server-Sent Events) showing live agent traces. | Approval works. UI optional but worth shipping if time. |
| 9 | Wed Jun 10 | **Hallucination harness.** Download Nitroba pcap + NIST Data Leakage E01 + NIST Hacking Case DD. Manifest each with SHA256. Build ground-truth set: parse Data Leakage PDF answer key; scrape Hacking Case writeups. Build scorer that classifies agent findings as TP/FP/HALLUCINATION/FN. | Harness operational on at least Nitroba. |
| 10 | Thu Jun 11 | **Baseline run + measurement.** Run vanilla Protocol SIFT (Direct Extension baseline) on Nitroba + NIST Data Leakage + NIST Hacking Case. Capture every finding. Score. Then run ours. Capture, score. Compute Δ. **This is the killer artifact.** | Accuracy report draft v1. |
| 11 | Fri Jun 12 | **Docker compose + setup docs.** `docker compose up` reproducible. README with one-liner install. Architecture diagram (Mermaid in repo + draw.io PNG). Court-admissibility annotation per finding type. | Anyone can deploy our submission in 10 minutes. |
| 12 | Sat Jun 13 | **Demo video.** Record 5-minute screencast: GTG-1002 framing (30s) → architecture diagram with security boundaries (30s) → "find evil" against NIST Hacking Case (2min) → Citation gate REJECTING a hallucinated finding (30s) → Critic CHALLENGE moment (30s) → measured Δ vs baseline (30s) → closing line. Audio narration. | Demo video uploaded to YouTube, unlisted. |
| 13 | Sun Jun 14 | **Polish + write-up.** Devpost story (What it does / How / Challenges / Learned / Next). Dataset doc. Accuracy report v2 with concrete hallucination examples + honest miss documentation. Final README pass. **Submit by 23:45 EDT.** | **SUBMITTED.** |
| -1 | Mon Jun 15 | Buffer day if anything slips. Don't slip past this. | Buffer. |

**Effort estimate vs. capacity:** 13 days × ~10 hr/day = ~130 hours.
- Build: ~80 hours (the typed MCP server is the biggest chunk)
- Deliverables (video, write-up, diagrams, accuracy report): ~30 hours
- Slack/buffer: ~20 hours

**Solo is achievable but tight.** Team of 2 is comfortable. Team of 3 is luxurious. If we have a co-builder, split: one on the MCP server + critic + sanitizer; one on the harness + deliverables. Both review each other's work.

---

## §6 The 5-minute demo arc (this IS the wedge)

```
0:00–0:30  CONTEXT
           Pull up the GTG-1002 framing.
           "AI threats strike in minutes. Build the defender that responds in seconds."
           Cite Rob T. Lee: "Defenders are out here bringing knives to a drone strike."

0:30–1:00  ARCHITECTURE DIAGRAM
           Walk through the 3-layer Investigation Record + 6 security boundaries marked
           ARCHITECTURAL (green) vs PROMPT-BASED (red).
           Highlight: "Citation gate + Verification gate + Entity gate — the missing seam."

1:00–3:00  LIVE TERMINAL: "find evil" against NIST Hacking Case
           Show the agent: vol pslist → finds Mr. Evil's processes.
           EvtxECmd → finds the wireless artifacts.
           AmcacheParser → finds the Ethereal install.
           Findings stream in, each with audit_id citations.

3:00–3:30  THE RALPH WIGGUM LOOP (self-correction #1)
           Show a Volatility plugin failing (wrong OS profile or missing symbol).
           Agent reads stderr, recognizes the failure mode, switches to a different plugin
           or different input. Tool call succeeds. Finding produced.

3:30–4:00  THE CITATION GATE (self-correction #2 — OUR WEDGE)
           Show the agent attempting to stage a finding:
              "Observation: PowerShell.exe with -EncodedCommand b64:..."
              cited: audit_id=memory-001
           Server loads stored memory-001 output. Substring check FAILS — the agent
           paraphrased; the actual output says "encoded".
           Server: REJECTED. Reason: SPAN_NOT_FOUND.
           Agent retries with the verbatim string. Finding stages.

4:00–4:30  THE CRITIC AGENT (self-correction #3)
           Critic fires. Re-reads the staged interpretation.
           Critic: CHALLENGE — "Confidence HIGH not supported. The cited evidence shows
           PowerShell ran; no evidence it executed malicious payload. Pivot to Sysmon EID 1
           or Prefetch to corroborate before claiming malicious."
           Investigator agent receives the critique, runs the suggested corroboration,
           revises the finding with new evidence + appropriate confidence.

4:30–4:50  MEASURED Δ vs BASELINE
           Bar chart: Vanilla Protocol SIFT vs Ours on Nitroba + NIST Data Leakage + NIST Hacking Case.
           "Baseline hallucinated 12 findings citing files that don't exist in the image.
            Ours: structurally rejected before staging. Hallucination rate: baseline 18%, ours 0%."
           "Time-to-first-finding on NIST Hacking Case: Baseline 22m. Ours 8m."

4:50–5:00  CLOSE
           "Protocol SIFT works. It also hallucinates more than we'd like.
            We made hallucination architecturally impossible. The full audit trail and
            the harness are in the repo. The wedge is reusable for every future
            Protocol SIFT submission. Find Evil — confidently."
```

Every second of the video resonates with at least one judge tier (per `research/protocol-sift-2026/refs/judges.md`). The two ARCHITECTURAL self-correction moments (3:30 + 4:00) are what the tiebreaker criterion explicitly rewards.

---

## §7 Risk register + mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Entity gate has high false-positive rate (rejects valid findings) | Medium | High (demo looks broken) | Tune on real Volatility output before Day 9. Each entity class gets unit-tested. Allow `force_accept` with examiner override (logged), not silent acceptance. |
| Tool output SHA256 changes between runs (non-determinism — e.g. Vol3 prints timestamps) | Medium | Medium (verification fails on re-run) | Normalize output before hashing: strip timestamps, normalize whitespace. Cite normalized form. |
| 13 days is too tight for solo | Medium (if solo) | High | Drop the streaming HUD (Day 8 optional). Drop court-admissibility annotation if needed. Keep harness + critic + sanitizer + Docker. |
| NIST Data Leakage download (20 GB) fails or is slow | Low | Medium | Start download Day 1 background. Have Nitroba (60 MB) as the smoke-test fallback. |
| Anthropic Agent SDK pricing change (Jun 15) burns credits | Medium | Low | Run the harness against cached Anthropic responses where possible. Budget caps via env var. |
| Judge dismisses wedge as "just Pydantic Instructor" | Low-Medium | High | Pre-emptively cite Instructor + NABAOS in README §1 ("prior art we built on") + accuracy report. Sharpen the entity gate differentiation. |
| Valhuntir ships a hotfix that adds something similar between now and Jun 15 | Low | Medium | Watch the AppliedIR repos. Date-stamp our commits. Document our diff against Valhuntir HEAD at submission time. |
| Demo video crashes (16:9 timing, audio sync) | Medium | Medium | Record on Day 12. Have Day 13 buffer. Run through the script twice before recording. |
| Sponsor changes rules late (e.g. additional deliverables) | Low | High | Check Devpost daily. Slack `#announcements` channel. |
| Wedge architecture has an unforeseen failure mode that surfaces during the harness run | Medium | High | This is the inverse of "honesty > polish." Document the failure mode IN the accuracy report. Don't hide it. Rob T. Lee explicitly rewards this. |

---

## §8 What we are NOT building (anti-scope)

- ❌ Re-wrapping all 100 of Valhuntir's tools. We pick 15-25 high-leverage.
- ❌ The forensic-rag MCP. Valhuntir's 22K-record RAG is heavy and not on our critical path.
- ❌ OpenSearch evidence indexer. Overkill for our scale.
- ❌ Live-host triage via Velociraptor. Cool wedge but post-mortem-only is enough for the demo.
- ❌ Multi-examiner workflow. Single-examiner, single-case is enough.
- ❌ A new SIFT distro. We deploy ON SIFT.
- ❌ A novel LLM. Claude Code as the client; standard Anthropic API for the critic.
- ❌ Real-time SIEM/SOAR integration. Not in scope.
- ❌ Mobile / Android forensics. Tier 4 datasets we already classified as skip.

If something doesn't directly contribute to scoring on Autonomous Execution / IR Accuracy / Constraint Implementation / Audit Trail, it doesn't ship.

---

## §9 The 8 mandatory deliverables — concrete plan

| # | Deliverable | What we ship |
|---|---|---|
| 1 | Public GitHub repo | `github.com/<abu>/protocol-sift-v2` or similar. MIT. Clear architecture in README. |
| 2 | Demo video ≤ 5 min | YouTube unlisted. The §6 arc. Live terminal, audio narration, at least one self-correction (we have THREE). |
| 3 | Architecture diagram | Mermaid in README + draw.io export PNG. Security boundaries labeled architectural vs prompt. Three-layer record visualized. |
| 4 | Devpost write-up | What it does / How built / Challenges (honest) / Learned / Next. Tell the wedge story. |
| 5 | Dataset documentation | Nitroba + NIST Data Leakage + NIST Hacking Case. Hashes confirmed. Acquisition + verification steps. |
| 6 | Accuracy report | Head-to-head bar chart vs baseline. Concrete hallucination examples we caught. Concrete misses we still have (honesty). Sanitizer test corpus results. Methodology section. |
| 7 | Try-It-Out instructions | `docker compose up` → done. OR SIFT VM + `bash install.sh`. Step-by-step. Login creds if needed. |
| 8 | Agent execution logs | `audit/*.jsonl` per backend + `audit/critic.jsonl` + `audit/sanitizer.jsonl` + frozen example case run committed to repo. |

---

## §10 Naming options (pick one in next 24h)

Working names — strong candidates only:

| Name | Why | Concerns |
|---|---|---|
| **SilentWitness** | Maps to Ovie Carroll's "digital devices are silent witnesses" quote — directly resonates with Tier 4 judges. The system is the analyst's translator. | Slightly grand |
| **Bedrock** | The architectural foundation. Findings rest on verifiable bedrock. | Generic |
| **Cite-Or-Die** | Memorable; literal description of the wedge. | Too aggressive for a SANS audience |
| **EvidenceLock** | Direct description of the wedge. | Slightly dry |
| **Witness Mark** | "Witness mark" is a real DFIR term for evidence indicators. The system marks its own claims with witness evidence. | Less recognizable outside DFIR |
| **GroundedSIFT** / **Grounded** | "Grounded findings" maps to RAG literature judges read. | Borrowing too much from RAG |
| **Protocol SIFT v2** | Direct extension framing — invites the "integration back into Protocol SIFT" outcome Rob mentioned. | Less catchy |

**My pick: SilentWitness.** Resonates with Ovie Carroll quote, captures the agent's role, sounds like something a SANS instructor would respect. Open to override.

---

## §11 Day-1 actions (start the moment Abu approves)

In this order, today (Mon Jun 2):

1. **Download SIFT OVA** (~20 GB, hours) — start now, runs in background.
2. **Reserve the repo name** — `github.com/<abu>/<chosen-name>`. Push README stub + MIT LICENSE + .gitignore.
3. **Clone reference repos** (run `clone-all-research-repos.sh` from `refs/sponsor-repos.md`).
4. **Read Valhuntir's `forensic-mcp/case/manager.py:660-1158`** (the `record_finding` method). This is the diff base for our wedge.
5. **Read Valhuntir's `report-mcp/server.py:286-349`** (the `_extract_all_iocs` regex). This is the code pattern we INVERT.
6. **Join Slack + Discord, change handle to a recognizable form, lurk for signal.**
7. **Set up Python project:** `uv` or `poetry`. Install `mcp`, `pydantic`, `anthropic`, `claude-agent-sdk`. Stub a FastMCP server.
8. **Set up Anthropic API key, claim budget.** Budget cap: $200 for the full hackathon.
9. **Pre-load the prompts** — drop `refs/quotes-for-pitch.md` into the project as `docs/PITCH_QUOTES.md` for the video.
10. **Write the SPEC** — single page in `docs/SPEC.md` enumerating: the 15-25 tools, the response envelope, the finding schema, the 3-layer record, the gate logic. Pin to repo. Don't iterate the spec mid-build.

---

## §12 Questions for Abu before we commit

Three calls I'd like Abu to make so the build doesn't stall:

### Q1: Solo or team?

If solo, we drop the optional streaming HUD and the court-admissibility annotation — keep the 3-layer record + critic + sanitizer + harness as the irreducible core.
If team of 2, we ship the full §5 plan.
If team of 3+, we add the live-host Velociraptor wedge as a stretch.

### Q2: Project name — SilentWitness, or something else?

This locks in the README, the Devpost title, the repo URL, the video title card. Don't want to bikeshed mid-build.

### Q3: Risk tolerance on the wedge framing?

Two options:
- **Aggressive:** Frame as "we made hallucination architecturally impossible — and here are the prior arts we extended (Instructor + NABAOS)." Owns the novelty + cites honestly.
- **Conservative:** Frame as "we extend Valhuntir with three new architectural gates." Lower-key. Less wedge, more incremental.

Aggressive wins more if the wedge holds up. Conservative survives better if a judge nitpicks. **My recommendation: aggressive with honest citation.**

---

## §13 The one-paragraph commit

> We commit to building **SilentWitness** — a Custom MCP Server submission for SANS Find Evil! that architecturally rejects forensic findings whose claims cannot be verified, byte-for-byte, against cited tool-output spans. We layer (a) closed-loop critic for interpretation challenges, (b) adversarial-evidence sanitizer for prompt-injection defense, (c) HMAC-signed approval ledger (Valhuntir pattern), (d) head-to-head accuracy harness vs baseline on Nitroba + NIST Data Leakage + NIST Hacking Case. The three-layer Investigation Record (Observation / Interpretation / Narrative) is the unit of output, with mandatory pivot field in Narrative. We honestly cite Pydantic Instructor (Nov 2023) and NABAOS Tool Receipts (March 2026) as prior art; we differ in MCP-server-side hard rejection at `record_finding()`, audit_ids as citation substrate, entity gate, and deployment inside the SIFT/Valhuntir architecture. Submission Jun 15 23:45 EDT. Demo video shows three self-correction moments (Ralph Wiggum Loop + Citation gate rejection + Critic challenge). Accuracy report shows measured Δ vs baseline with concrete hallucination examples we caught and honest misses we didn't. Anti-scope: no live-host triage, no 100-tool coverage chase, no multi-examiner workflow. Build solo or team of 2; days 1-7 are MCP server + wedge, days 8-10 are harness + measurement, days 11-13 are deliverables + polish. We optimize for the three highest-leverage criteria: Autonomous Execution (tiebreaker), IR Accuracy, Constraint Implementation.

---

## §14 File index for the build

| Path | Purpose |
|---|---|
| `STRATEGY.md` | This file. The commitment. |
| `docs/SPEC.md` | (Day 1) Pinned spec. Don't iterate mid-build. |
| `research/protocol-sift-2026/CONTEXT.md` | Research entrypoint. Background knowledge. |
| `research/protocol-sift-2026/refs/sdk-snippets.md` | Paste-ready code (MCP server, critic, sanitizer, HMAC ledger). |
| `research/protocol-sift-2026/refs/judges.md` | Judge personalities. Inform demo + write-up. |
| `research/protocol-sift-2026/refs/datasets.md` | Dataset details for the harness. |
| `research/protocol-sift-2026/refs/quotes-for-pitch.md` | Quote bank. |
| `research/protocol-sift-2026/.raw/05-novelty-check.md` | The wedge novelty proof. Cite in the accuracy report. |
| `src/` | The MCP server. |
| `tests/` | Unit tests for gates + entity extractor. |
| `harness/` | The accuracy harness + datasets. |
| `audit/` | Frozen example case run committed for judges. |
| `Dockerfile`, `docker-compose.yml` | Reproducible install. |
| `README.md` | The face. Architecture + install + quick start. |

---

**Status: READY TO BUILD.** Abu's call on §12 questions, then day 1 actions fire.
