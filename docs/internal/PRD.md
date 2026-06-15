# PRD — SilentWitness

**Hackathon:** SANS Find Evil! (Protocol SIFT 2026)
**Track:** Custom MCP Server — approach #2 of 4, described verbatim in the Devpost overview as *"the most sound architecture in the evaluation"*
**Deadline:** 2026-06-15 23:45 EDT
**Status:** DRAFT (pending Abu approval)
**Approved by Abu:** [ ] pending

---

## 1. Goal

**SilentWitness** is a hypothesis-first AI incident-response investigator that drafts its own structured incident report **as the case unfolds**, with every claim architecturally locked to the tool execution that produced it. It is built for the senior IR consultant at a Tier-2 boutique (Aspen Forensics / Informed Defense / Stroz-scale) who spends ~half of every billable hour either typing forensic CLI commands by hand (Rob T. Lee's "command-line stenographer") or, afterward, turning notes into a structured report the client can read and a lawyer can defend. SilentWitness collapses both phases: a hypothesis-pivot loop works the case the way a FOR508-graduate works it, and a single Markdown report at `cases/<case_id>/report.md` is updated atomically on every staged observation — each finding tagged `[verify:audit_id]` that resolves to the exact JSONL audit entry, SHA256-pinned tool output, and verbatim cited span. Hallucinated findings are not merely unlikely; they are **architecturally rejected by the server** before they reach the report.

**One-line pitch (judge-facing):**

> **SilentWitness — a hypothesis-first DFIR investigator whose report writes itself, with every claim locked to the tool that produced it.**

**Sponsor-native fit:**

SilentWitness is a Custom MCP Server submission — the approach the Find Evil! Devpost overview explicitly labels *"the most sound architecture in the evaluation"* (verbatim, approach #2 of 4). It matches the model-agnostic precedent set by Valhuntir, the SANS-cited bar ("LLM client agnostic" verbatim per its README), and ships a drop-in `.claude/` config that lets a judge demo it on the pre-installed Claude Code v2.0.61 on SIFT 2026 with zero additional setup.

---

## 2. Demo moment — 5-minute video walkthrough

A judge who has never opened a DFIR tool must be able to follow this arc.

| Time | What happens | Why it lands |
|---|---|---|
| **0:00–0:30** — Context | Voice-over: "On November 14, 2025, Anthropic disclosed GTG-1002 — a Chinese state-sponsored operation where Claude Code autonomously executed 80–90% of an espionage campaign across 30+ targets. AI attackers move in minutes. Defenders still move in hours. SilentWitness is the defender." | Frames the stakes Rob T. Lee writes about. |
| **0:30–1:00** — Architecture | Single-frame diagram. Six boundaries marked **ARCHITECTURAL** (typed MCP tool surface; bwrap sandbox; ro,noexec,nosuid mount; citation gate; entity gate; HMAC-signed ledger). Two marked **PROMPT-BASED** (system prompt reminders; tool-call advisories) and labeled "supplementary, not load-bearing." | Resonates Perkal + Ernstberger; satisfies the Devpost requirement to "distinguish prompt-based vs architectural guardrails." |
| **1:00–3:00** — Live terminal | On the SIFT 2026 VM, examiner types `silentwitness investigate /evidence/hacking-case`. Agent forms a hypothesis ("If wardriving, expect promiscuous-mode capture tool + intercepted credentials"), dispatches disk specialist, registers `Documents and Settings\Mr. Evil\` as the user profile, pivots to memory + program-files enumeration, stages findings live. Right-pane report file updates in real time. | Resonates Rob T. Lee (senior-analyst sequencing), Ovie Carroll (audit-trail visibility), 3-AM-analyst tier (real triage, not slides). |
| **3:00–3:30** — Self-correction | Investigator dispatches `windows.netscan` against the memory image. Volatility returns symbol-table error (wrong profile). Agent reads stderr, falls back to `windows.info` to determine OS build, regenerates the symbol table, retries, succeeds. Logged as PIVOT transition with `reason: "vol3 symbol-table mismatch; rebuilt"`. | The self-correction the rules require — Rob's canonical Volatility behavior in his own words ("Claude reads the error message, adjusts its hypothesis... and retries"). |
| **3:30–4:00** — Citation-gate moment | Agent attempts `record_observation("Ethereal.exe was installed at C:\\Tools\\Ethereal\\")`. Entity gate: substring `C:\Tools\Ethereal\` is NOT in any cited tool output. **Server returns `REJECTED: entity not found in cited spans`.** Agent re-reads actual `windows.filescan` output, revises with verbatim path (`C:\Program Files\Ethereal\ethereal.exe`), retries, observation accepted. | The killer demo moment: hallucination caught **architecturally**, not by a system-prompt plea. Maps to Constraint + IR Accuracy. |
| **4:00–4:30** — Critic moment | Critic subagent fires after the 8th observation. Re-reads staged interpretation ("Schardt was actively exfiltrating credit cards"). Returns `verdict: CHALLENGE, reason: "interpretation requires intercepted-traffic evidence; only tool installation shown; downgrade confidence or corroborate via captured-pcap"`. Investigator runs `zeek -r /evidence/captures/wardrive.pcap`, finds intercepted SMTP credentials, revises with appropriate confidence band. Logged to `audit/critic.jsonl`. | Tiebreaker criterion live — Rob's exact sentence: "recognize when something doesn't add up." |
| **4:30–4:50** — Measured Δ vs baseline | Bar chart: time-to-handoff-ready-report on NIST Hacking Case, vanilla Protocol SIFT vs SilentWitness. Secondary bars: hallucinated-claim count (entity NOT in evidence, verifiable by `grep` against the mounted image, per CyberSleuth Module III) and epistemic-honesty count (claims agent abstained from). Numbers **measured, not estimated**; methodology link on screen. | Maps to Rob's permission to flag your own hallucinations and the unwritten rubric's #1 silent differentiator. |
| **4:50–5:00** — Final report | Markdown report renders. Camera zooms on Findings. Examiner clicks `[verify:F-014/sift-001-20260613-042]`. Side pane shows JSONL audit entry, SHA256-pinned full output, cited line range, entity-gate match list. Cut. | Resonates Cheri Carr / Ovie Carroll / Amanda Rankhorn — defensible audit trail; the report survives cross-examination. |

**The wow moment:** A judge will remember 10 minutes later that *the report wrote itself, and every claim had a verify link they could click — and one finding got rejected by the server because the agent tried to cite something that wasn't there.*

---

## 3. The user

Per `context/user/09-ir-consultant-reality.md` (Part A + Part F).

**Persona:** Senior IR consultant at a Tier-2 boutique — Aspen Forensics, Informed Defense, Volexity, TrustedSec IR, Hexordia, Sygnia. 5–15 years experience. SANS GCFA + GCFE + frequently GREM/GCIH/GNFA. Often came from law enforcement (FBI Cyber, Air Force OSI, NCIS) or a Big-4 forensic-technology practice. Speaks at SANS DFIR Summit / OSDFCon once a year. Lives on a laptop within arm's reach 24/7 because the IR hotline rings at 2 a.m.

**Day-in-the-life (active engagement):** 0800 read overnight Slack from offshore. 0930 daily standup. 1000–1230 and 1300–1500 at the keyboard running Volatility plugins, parsing registry hives, searching EVTX, pivoting memory→disk→back. 1530 draft notes + review junior's output. 1800 customer daily executive update. 2100 second wave if hot. Non-linear; constant context-switching between doing analysis, reviewing the junior, talking to the customer, and coordinating internally.

**Pain (verified practitioner voice):** Two complaints repeated on r/computerforensics, Forensic Focus, and OSDFCon panels: (1) "command-line stenography" (Rob T. Lee's phrase) — two-thirds of an engagement is typing CLI, parsing CSV, copy-pasting between tools. (2) The 2–3 evening hours turning notes into the deliverable, which has five audiences (CISO, GC, insurance carrier, customer IT, breach-coach attorney) and which the senior writes themselves because the junior can't yet. **No competitor in the visible 60-repo Find Evil! field is solving the report-writing pain.** ~85% of the visible field is running an architectural-anti-hallucination variant of Valhuntir.

**Wish-list (paraphrased from practitioner threads):** "Give me back the 2 hours of evening report-writing." "Let me run more cases per month — the boutique can't scale headcount." "Show me what you ran and what it said — I don't trust a black box on the stand." "Don't try to replace me; I'm the part the customer is paying for."

**Day-after-SilentWitness:** They take more cases per month because the per-case grunt work is gone. The report is ~80% drafted by the time they hand the keyboard back to themselves to write the executive narrative and recommendations. Every claim has a verify link they trust because the server won't let an unverified claim land in the report.

---

## 4. The headline metric

**Time to handoff-ready incident report** on a representative case.

| Metric | Definition | Source / methodology |
|---|---|---|
| **Primary: Time-to-handoff-ready-report** | Seconds from `silentwitness investigate <path>` until the report.md reaches DRAFT-with-executive-summary state, on the NIST Hacking Case. | Anchored against Rob T. Lee's published 14:27 demo of "find evil" → complete C-drive analysis. Anchored against vanilla Protocol SIFT baseline measured on the same case. |
| Secondary: Pivot count | Number of HypothesisEvent transitions logged of type `pivot` in `audit/hypothesis.jsonl`. | Proves hypothesis-driven (not kitchen-sink). |
| Secondary: Claim provenance rate | % of report claims that resolve to a tool execution (i.e., every `[verify:audit_id]` references a real audit entry whose stored output contains the cited span). | Proves "verifiable" without the trigger phrase "court-admissible." |
| Secondary: Hallucinated-claim count | Count of claims rejected by the citation/entity gate during a run (the architectural floor) AND count of claims that escaped and would have been flagged by an offline `grep`-the-mounted-image verifier (the residual). | Per CyberSleuth Module III + DFIR-Metric HALL definition. |
| Secondary: Epistemic-honesty count | Number of items in the report's `Gaps` section — things the agent could NOT verify or did NOT check. | Rob T. Lee's "Claude doesn't get defensive when you call it out" — abstention is a feature. |

Datasets for the harness: Nitroba (smoke test), NIST Data Leakage (quantitative benchmark, public answer key), NIST Hacking Case (primary demo, on-brand). See §10.

---

## 5. Functional requirements

The contract the build must meet. Numbered to match Epics.

1. **MUST** run on stock SIFT 2026 (Ubuntu 24.04.2 Noble, Python 3.12, Claude Code v2.0.61 at `/usr/local/bin/claude`, Volatility 3 at `/opt/volatility3/bin/vol`).
2. **MUST** ship a Custom MCP Server (Python, FastMCP) wrapping **≥15 typed Pydantic-v2 forensic tools** spanning memory, disk, log, network, registry. No generic `execute_shell()` exposed.
3. **MUST** be model-agnostic — switchable via `SILENTWITNESS_MODEL` env var (default `anthropic:claude-opus-4-7`); CI-tested against ≥2 providers. Matches Valhuntir's "LLM client agnostic" bar.
4. **MUST** architecturally reject finding claims citing evidence not present (citation + entity gates, BRAINSTORM Decision 3). Server returns `REJECTED` with reason; agent revises.
5. **MUST** log every MCP tool call to JSONL at `cases/<case_id>/audit/<backend>.jsonl` with stable `audit_id` (`sift-<examiner>-<YYYYMMDD>-<NNN>`, resumes across restarts).
6. **MUST** maintain a structured incident report (Markdown + YAML frontmatter) at `cases/<case_id>/report.md`, auto-saved by atomic rename on every staged Observation / Interpretation / Pivot, FOR508-shaped sections including **Gaps** (epistemic honesty) + Appendix-Audit.
7. **MUST** demonstrate ≥1 self-correction sequence in the demo (Rules §4).
8. **SHOULD** provide a Claude Code drop-in config under `claude-code-config/.claude/` (CLAUDE.md + settings.json with MCP registration + allow/deny) for zero-setup judge demo.
9. **SHOULD** include a reference Pydantic AI agent loop (`silentwitness-agent`) with the closed-loop critic firing every N observations.
10. **SHOULD** ship Docker Compose for non-SIFT environments. Pre-built image on GHCR.
11. **SHOULD** include a head-to-head accuracy harness running both vanilla Protocol SIFT and SilentWitness on Nitroba + NIST Data Leakage + NIST Hacking Case, emitting precision / recall / hallucination-rate per case vs baseline.

---

## 6. Non-functional requirements

| Concern | Constraint |
|---|---|
| Python | CPython 3.12 (pinned `>=3.12,<3.13` to match SIFT 2026) |
| Package manager | `uv >=0.5`; install script bootstraps the single binary |
| File-size cap | No `.py` file >400 lines; enforced by pre-commit hook + CI |
| Lint / format | `ruff >=0.8` (replaces black + isort + flake8 + pylint) |
| Type checking | `mypy >=1.13` strict |
| License | MIT |
| Test coverage | ≥85% on `src/`, ≥95% on `silentwitness_mcp/verification/` (citation + entity gates) |
| Security boundaries | Architecturally enforced (typed tool surface, bwrap kernel sandbox, ro,noexec,nosuid evidence mount, server-side citation + entity gates, HMAC-SHA256 PBKDF2-600K-iter approval ledger). **Not** prompt-based. |
| Reproducibility | `uv.lock` checked in; Docker image SHA pinned in README; SBOM emitted via `cyclonedx-py` in CI |
| Determinism | Tool output normalization (timestamp strip, whitespace, path separator) before SHA256 hashing so cited spans are byte-stable across re-runs |
| Network port | Optional streaming HUD on port **8088** (avoid 80 — Apache binds CyberChef there on SIFT 2026) |

---

## 7. Out of scope (this sprint)

Per BRAINSTORM §5 and the 13-day calendar.

- **Live-host triage via Velociraptor MCP** — stretch, post-hackathon.
- **Browser-based Examiner Portal** — Valhuntir ships 8 tabs; ours is CLI examiner approval only. Enough for the demo.
- **Multi-case management** — single-case for the demo; multi-case is post-hackathon.
- **OpenSearch evidence index** — JSONL + `grep` is enough at our scale; SQLite if perf needs it; OpenSearch deferred (heavy infra).
- **Streaming HUD on Server-Sent Events** — optional, time-permitting; port 8088 if built.
- **Mobile / Android forensics** — explicitly excluded.
- **Cloud forensics** (AWS / Azure / Entra / GCP) — out of v1.
- **macOS forensics** beyond memory basics — out of v1.
- **Real-time SIEM/SOAR integration** — out of scope.
- **Adversarial-evidence sanitizer at file-content scale** — gate the LLM-bound free-text fields; do not attempt to sanitize multi-GB evidence files.

---

## 8. Judging criteria alignment

Pulled verbatim from `research/protocol-sift-2026/01-prizes-tracks.md`. Six criteria, equally weighted; **Autonomous Execution Quality is the tiebreaker.**

| # | Criterion | Weight | How SilentWitness scores |
|---|---|---|---|
| 1 | **Autonomous Execution Quality** (tiebreaker) | equal | The hypothesis-pivot state machine IS the senior-analyst sequencing Rob T. Lee asks for. Three self-correction moments in the demo: (a) Volatility symbol-table error → rebuild → retry; (b) citation gate rejects unverified claim → agent re-reads output → revises with verbatim span; (c) critic CHALLENGES over-confident interpretation → corroborates → revises confidence. All transitions logged to `audit/hypothesis.jsonl`. |
| 2 | **IR Accuracy** | equal | Hallucinated claims are **architecturally impossible** to record. Citation gate rejects spans whose SHA256 doesn't match stored output. Entity gate rejects observations whose extracted entities don't appear in cited spans. Measured Δ vs vanilla Protocol SIFT on all three datasets, methodology disclosed honestly per Rob's rubric. |
| 3 | **Breadth and Depth** | equal | 15+ tools across **memory** (Volatility 3, ~10 plugins, plugin-aware reasoning), **disk** (Sleuth Kit + EZ Tools: MFTECmd / AmcacheParser / RECmd / PECmd), **log** (Hayabusa + Chainsaw + EvtxECmd), **network** (Zeek + Suricata + tshark), **registry** (RegRipper3.0). Each tool has typed Pydantic I/O, normalized output, downstream cross-artifact corroboration. |
| 4 | **Constraint Implementation** | equal | Six architectural boundaries (§2, 0:30–1:00). Custom MCP Server = destructive command literally does not exist. bwrap kernel sandbox + ro,noexec,nosuid evidence mount + 41-rule denylist (Valhuntir pattern ported). Citation + entity gates server-side. HMAC-SHA256 + PBKDF2-600K-iter approval ledger. Two prompt-based mechanisms labeled "supplementary, not load-bearing" in the diagram. |
| 5 | **Audit Trail Quality** | equal | Per-tool-call JSONL: `audit_id`, `tool`, typed `params`, truncated `result_summary`, `result_sha256`, `stdout_path`, `elapsed_ms`, `examiner`, `model_used`, `model_token_count`. Findings cite `audit_ids` inline as `[verify:audit_id]`. HMAC-signed approval ledger at `/var/lib/silentwitness/verification/<case_id>.jsonl`, mode 0600, PBKDF2-SHA256 from examiner password. |
| 6 | **Usability and Documentation** | equal | One-command SIFT install; two-command Docker Compose. Drop-in `.claude/` for pre-installed Claude Code v2.0.61. Inline-Mermaid diagram in README. 3-minute demo video above the fold. Model-agnostic by construction (rubric explicitly rewards portability). |

---

## 9. Demo dataset choice

Options reviewed from `context/evaluation/10-datasets-and-evaluation-methodology.md`:

| Dataset | Size | Role | Memorization risk | Why or why not |
|---|---|---|---|---|
| **NIST CFReDS Hacking Case (Mr. Evil / Greg Schardt)** | ~6 GB disk image | **Primary demo dataset** | **Very high** — canonical answers (MAC, IP, hostname, "Mr. Evil" email) appear in hundreds of indexed writeups | On-brand naming for "Find Evil!" — every judge recognizes Mr. Evil immediately. Memorization risk is addressed **honestly** in the accuracy report (per Rob T. Lee's honesty-over-polish principle): we state the model has likely seen writeups, and show the citation + entity gate forcing every claim to ground in evidence-present spans rather than regurgitated memory. The dataset demonstrates the gates work, not latent capability. |
| **Nitroba University Harassment** | ~200 MB pcap | CI smoke test + sub-1-minute live demo if time-constrained | Medium — answers in wild but solution PDF gated | Fast iteration; clean canonical hash stable since 2008. |
| **NIST Data Leakage Case** | ~20 GB disk image + answer key PDF | **Primary quantitative benchmark** | Lower — answer key is gated PDF; less indexed | Public PDF answer key parseable into a ground-truth fixture (parser at `harness/ground_truth/nist_data_leakage.py`). Source of the precision / recall / hallucination-rate-Δ numbers. |
| **Synthetic `case-trapdoor`** | ~500 MB | **Optional adversary-pair demo** | None (synthetic) | Custom: timestomp + log clear + process hollow + prompt-injection-in-registry-value. Shows the entity gate + sanitizer at the limit. Time-permitting. |

**Decision:** NIST Hacking Case primary live demo (on-brand, recognizable). Nitroba CI smoke test. NIST Data Leakage drives the bar chart at 4:30–4:50. **`case-trapdoor` CUT from v1** per `docs/DEEP_AUDIT_REPORT.md` Decision B / audit B-PY-3 — `regipy` and `python-evtx` are read-only libs and cannot synthesize registry hives or EVTX files as specced. Tracked in "Future work" for v2 (template-fixture pattern: check in clean NTUSER.DAT / Security.evtx fixtures, patch by byte offset). Headline metric is met without the synthetic adversary case (E14 delivers measured Δ on three real datasets).

---

## 10. The 8 mandatory deliverables

Per Devpost Rules §4. For each: where it lives and how it's produced.

| # | Deliverable | Repo location | How produced |
|---|---|---|---|
| 1 | **Public GitHub repo (MIT)** | `https://github.com/<org>/silentwitness` | `LICENSE` at root; MIT confirmed in CI license check via `cyclonedx-py` |
| 2 | **Demo video ≤5 min** | README badge + Loom/YouTube link in submission | Recorded against NIST Hacking Case on SIFT 2026 VM; live terminal narration; arc per §2 |
| 3 | **Architecture diagram** | `docs/architecture.md` + inline-Mermaid block in README | Mermaid source-of-truth; SVG export at `docs/diagrams/architecture.svg`; security boundaries labeled architectural vs prompt-based (Devpost requirement) |
| 4 | **Devpost write-up** | `docs/DEVPOST.md` (the Markdown source) | Written from PRD §1 (Goal) + §3 (User) + §8 (Judging) + §10 (Deliverables) at submission time |
| 5 | **Dataset documentation** | `harness/datasets/README.md` + per-dataset manifest at `harness/datasets/<name>.yaml` | Each manifest pins canonical SHA256, fetch URL, license, memorization-risk note, and answer-key path |
| 6 | **Accuracy report** | `docs/accuracy-report.md` (generated by `harness/scorer.py`) | Harness runs vanilla Protocol SIFT and SilentWitness on each dataset; emits precision / recall / hallucination-rate-Δ per case + per-tool; **explicitly flags own failure modes** (Rob's honesty rubric) |
| 7 | **Try-It-Out instructions** | `README.md` §"Quick Start" + `docs/setup.md` | 3-command path on SIFT 2026 (`curl install.sh \| bash` → `silentwitness install` → `silentwitness investigate <evidence>`); 2-command Docker Compose path |
| 8 | **Agent execution logs** | `cases/<case_id>/audit/*.jsonl` (one per MCP backend) + `cases/<case_id>/audit/hypothesis.jsonl` + `cases/<case_id>/audit/critic.jsonl` | Generated automatically per case; sample case shipped at `examples/case-hacking-case-001/` so judges can read logs without running the system |

---

## 11. README shape

Required order at the top of `README.md`:

1. **Project name + one-line pitch** (the §1 pitch verbatim)
2. **Live demo asset** — 3-minute demo video (Loom/YouTube embed) + a screenshot/GIF of the report-with-verify-links above the fold
3. **Run-locally steps** — 3-command path on SIFT 2026 (`curl ... install.sh | bash` → `silentwitness install` → `silentwitness investigate <evidence>`); 2-command Docker Compose path (`docker compose up` → `docker compose exec silentwitness investigate <evidence>`)
4. **Architecture diagram** — inline Mermaid, with the six architectural boundaries labeled and the two prompt-based ones labeled separately (Devpost requirement satisfied at the README level)
5. **License** — MIT

Everything below the fold is supplementary: deeper architecture explanation, contributor guide, accuracy report link, citation, acknowledgments to Valhuntir (the published bar) and to teamdfir/protocol-sift (the baseline).

---

## 12. Risks + mitigations

| Risk | Mitigation |
|---|---|
| Pydantic AI is newer (17.5K stars, rapid evolution); API may change mid-sprint. | Pin minor version in `uv.lock`; vendor critical patterns; agent-delegation is the only Pydantic-AI-specific surface we depend on. |
| SIFT 2026 install footprint requires Hayabusa + Chainsaw + Zeek + Suricata + `uv`. | `install.sh` one-liner; idempotent; ~5 min on clean SIFT VM; tested in CI on SIFT 2026 OVA. |
| Demo dataset hashes drift if SANS updates Egnyte share. | Pin to canonical public Nitroba + NIST hashes (stable 15+ years); manifests at `harness/datasets/<name>.yaml` document expected vs observed. |
| Judge tests with non-Claude model + default prompts under-performs. | Model-string switching tested in CI for **≥2** providers (Anthropic + OpenAI). Default prompts model-neutral. Provider overrides via `prompts/<provider>.toml`. |
| Competitor ships same wedge. | Devpost gallery unpublished until Jun 15. Of 60 visible repos, ~85% are anti-hallucination variants; **none** address report-writing pain. The citation + entity gate + report-as-state combination remains the architecturally cleanest expression. |

---

## 13. Open questions for Abu

None expected (BRAINSTORM v2 was approved 2026-06-02). Items deferred to architecture-spec / ADR phase rather than left open here:

- Critic subagent model selection (Opus for the investigator; Sonnet or Haiku for the critic?) — decide in `docs/architecture.md`.
- Streaming HUD on port 8088 — build only if time permits; ADR if built.
- Examiner-portal CLI ergonomics (Typer prompt style; auto-approve mode for benchmarks) — finalize in story BDD.

---

## 14. Spec metadata

- **Status:** DRAFT pending Abu approval
- **Project name:** SilentWitness (verbatim; never paraphrase)
- **Track:** Custom MCP Server (Devpost overview approach #2 of 4 — *"the most sound architecture in the evaluation"*)
- **Architectural floor matched against:** AppliedIR/Valhuntir (the SANS-cited "level of quality to meet/exceed")
- **Architectural wedge above the floor:** hypothesis-first investigator with **report-as-state** + **architecturally-enforced citation + entity gate on every recorded observation** (no visible competitor addresses report-writing pain)
- **Contributes to judging criteria:** all 6 (see §8 table)
- **Source documents (read in order):** `STRATEGY.md` → `docs/BRAINSTORM.md` → `context/README.md` → `research/protocol-sift-2026/CONTEXT.md` → `research/protocol-sift-2026/01-prizes-tracks.md` → `research/protocol-sift-2026/refs/judges.md` → `context/user/09-ir-consultant-reality.md` → `context/.raw-design-research/01-rules-model-agnostic-verification.md` → `context/evaluation/10-datasets-and-evaluation-methodology.md`
- **Downstream specs that consume this PRD:** `docs/architecture.md`, `docs/ux-spec.md` (CLI ergonomics), `docs/epics.md`, `docs/stories/story-<slug>.md`
- **Vocabulary discipline:** never use "court-admissible" (Rob T. Lee anti-vocabulary; use "defensible audit trail" or "survives cross-examination"); never use "Ralph Wiggum Loop" in the doc itself (community jargon, not Rob's vocabulary — describe the behavior instead); never use "autonomous SOC" / "replaces L1" / "eliminates hallucinations" (vendor-marketing trigger phrases Rob penalizes).

---

**End of PRD. Awaiting Abu approval.**
