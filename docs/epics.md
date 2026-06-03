# Epics — SilentWitness

**Hackathon:** SANS Find Evil! (Protocol SIFT 2026)
**Status:** DRAFT
**Total epics:** 16 (14 mandatory, 2 optional)
**Total stories:** 83
**Estimated total build time:** ~30–32h coding-agent time (mandatory path ~26h)
**Source documents:** `STRATEGY.md`, `docs/BRAINSTORM.md`, `docs/PRD.md`, `docs/architecture.md`, `docs/ux-spec.md`, `docs/CICD_SPEC.md`

> Vertical, dispatchable epics. Each epic ≤2h coding-agent time. Each story is a kebab-case slug; story files are authored in Wave 4 (one file per slug at `docs/stories/story-<slug>.md`). Orchestrator dispatches per §4. Risk-weighted cuts in §5.

---

## 1. Epic overview (dependency order)

| Epic | Title | Stories | Estimate | Depends on |
|---|---|---|---|---|
| E1 | Project scaffolding + CI/CD on commit 1 | 5 | ~2h | None |
| E2 | Common types + audit infrastructure | 5 | ~2h | E1 |
| E3 | Verification gates (citation + entity + sanitizer) | 5 | ~2h | E2 |
| E4 | MCP server skeleton + finding-state tools | 7 | ~2h | E3 |
| E5 | Tool wrappers — memory (Volatility 3) | 7 | ~2h | E4 |
| E6 | Tool wrappers — disk + registry (EZ Tools + RegRipper) | 5 | ~2h | E4 |
| E7 | Tool wrappers — log + network (EVTX + Hayabusa + Chainsaw + Zeek + Suricata) | 5 | ~2h | E4 |
| E8 | Hypothesis state machine + investigator agent (Pydantic AI) | 5 | ~2h | E4 |
| E9 | Specialist subagents (memory / disk / network / log) | 4 | ~2h | E5 + E6 + E7 + E8 |
| E10 | Closed-loop critic agent | 3 | ~2h | E8 |
| E11 | Report-as-state (Markdown + PDF) | 4 | ~2h | E4 |
| E12 | CLI (Typer) + Claude Code drop-in config | 10 | ~2h | E4 + E8 + E11 |
| E13 | Streaming HUD (OPTIONAL — stretch) | 3 | ~2h | E8 |
| E14 | Accuracy harness + baseline comparison | 6 | ~2h | E8 + E11 |
| E15 | Adversary-pair case-trapdoor (OPTIONAL) | 2 | ~2h | E14 |
| E16 | Documentation polish + submission | 7 | ~2h | All preceding |

Mandatory path (drop E13 + E15): 14 epics, 78 stories, ~28h. Full path: 16 epics, 83 stories, ~32h.

---

## 2. Per-epic detail

### Epic 1 — Project scaffolding + CI/CD on commit 1

**Business value:** Every CI gate fires from commit 1. If we skip this, we grandfather in 400-LOC violations, missing type annotations, AGPL contamination — the slop SilentWitness is built to prevent.
**Dependencies:** None.
**Stories:** `scaffold-uv-pyproject`, `ci-workflows`, `pre-commit-hooks`, `docker-baseline`, `justfile-targets`.
**Estimate:** ~2h.
**Story files:** `docs/stories/story-{slug}.md` for each slug above.
**Definition of done:** Empty `src/` tree passes `just ci` locally; first push triggers green CI; branch protection applied (CICD_SPEC §5); SBOM artifact published.
**Demo contribution:** None (foundational).
**Judging criteria:** Usability (try-it-out, Docker, conventional commits visible to judges browsing); Audit Trail Quality (defensible build process — the codebase itself is auditable).

---

### Epic 2 — Common types + audit infrastructure

**Business value:** Every component below this layer depends on shared Pydantic models, deterministic IDs, the JSONL audit writer, and the HMAC ledger. Without it there is no provenance trail, and no defensible report.
**Dependencies:** E1.
**Stories:** `common-types`, `audit-logger`, `evidence-registry`, `hmac-ledger`, `atomic-io`.
**Estimate:** ~2h.
**Story files:** `docs/stories/story-{slug}.md` for each slug above.
**Definition of done:** `audit/` at 90%+ coverage; property tests on audit-id sequence resume; stubbed `silentwitness verify <case>` reads a hand-written ledger entry and recomputes HMAC.
**Demo contribution:** Backs the `[verify:...]` click-through at 4:50–5:00 and the `silentwitness verify` post-handoff command.
**Judging criteria:** Audit Trail Quality (primary — this IS the audit trail); Constraint Implementation (HMAC ledger + mount validation are architectural boundaries).

---

### Epic 3 — Verification gates (citation + entity + sanitizer)

**Business value:** The wedge primitive. Citation gate + entity gate are why hallucinated findings are **architecturally impossible** to record. This is the killer demo moment (3:30–4:00) and the cleanest expression of Constraint Implementation. If this epic fails, SilentWitness is just another Valhuntir clone with prompt-only guardrails.
**Dependencies:** E2.
**Stories:** `output-normalizer`, `citation-gate`, `entity-gate`, `sanitizer`, `gates-property-tests`.
**Estimate:** ~2h.
**Story files:** `docs/stories/story-{slug}.md` for each slug above.
**Definition of done:** `verification/` at 95%+ coverage; hand-crafted observation citing a fake path is rejected with the exact REJECTED reason; observation citing a real path passes; the rejection demo reproducible from a pytest fixture.
**Demo contribution:** The rejection moment at 3:30–4:00 — "`C:\Tools\Ethereal\` is not in any cited span — REJECTED".
**Judging criteria:** Constraint Implementation (primary — architectural enforcement vs prompt-only); IR Accuracy (hallucination floor is mechanical, not statistical).

---

### Epic 4 — MCP server skeleton + finding-state tools

**Business value:** The MCP boundary the rules reward (approach #2 — *"the most sound architecture in the evaluation"*). Without this, E3 gates are unreachable by any MCP client. The response envelope is what makes the audit trail composable.
**Dependencies:** E3.
**Stories:** `fastmcp-server-bootstrap`, `response-envelope`, `record-observation-tool`, `record-interpretation-tool`, `record-pivot-tool`, `record-narrative-tool`, `approve-finding-tool`.
**Estimate:** ~2h.
**Story files:** `docs/stories/story-{slug}.md` for each slug above.
**Definition of done:** Any MCP client (Claude Code, Claude Desktop, Cherry Studio, Pydantic AI agent) can connect via stdio or HTTP and call `record_observation`; integration test asserts malformed observation is rejected, well-formed is accepted with an audit entry written.
**Demo contribution:** Backs every agent call during 1:00–4:30; the verify-link click-through resolves through this layer.
**Judging criteria:** Constraint Implementation (typed MCP surface IS the constraint); Audit Trail Quality (envelope schema IS the trail); Usability (any MCP client can connect — Valhuntir-style portability).

---

### Epic 5 — Tool wrappers: memory (Volatility 3)

**Business value:** Memory forensics is where the demo's self-correction moment lives (3:00–3:30 — symbol-table mismatch → rebuild → retry). Vol3 is the most-demanded family in DFIR and fails most often in interesting ways, making it the highest-value source of self-correction events the rules reward.
**Dependencies:** E4.
**Stories:** `vol-pslist`, `vol-pstree-psscan`, `vol-malfind`, `vol-netscan`, `vol-cmdline`, `vol-dlllist-handles`, `vol-lsadump`.
**Estimate:** ~2h (parallel-friendly across stories once skeleton lands).
**Story files:** `docs/stories/story-{slug}.md` for each slug above.
**Definition of done:** Each tool tested against NIST Hacking Case memory image; envelope contains valid `result_sha256` + `stdout_path`; `tools/memory.py` ≤400 LOC (split if over).
**Demo contribution:** Memory analysis moment (1:00–3:00) and the Volatility symbol-table self-correction (3:00–3:30).
**Judging criteria:** Breadth and Depth (10+ memory plugins under one typed family); IR Accuracy (server-side parse → consistent structured output).

---

### Epic 6 — Tool wrappers: disk + registry (EZ Tools + RegRipper)

**Business value:** Disk artifacts (MFT, Amcache, Shimcache, Prefetch, Shellbags) + registry (RegRipper) cover the "what was executed when" question — the bulk of Hours 6–14 of any IR engagement. Without these the demo's disk-corroboration step (Ethereal install at `C:\Program Files\Ethereal\`) cannot happen.
**Dependencies:** E4.
**Stories:** `parse-mft`, `parse-amcache-shimcache`, `parse-prefetch`, `parse-shellbags`, `regripper`.
**Estimate:** ~2h.
**Story files:** `docs/stories/story-{slug}.md` for each slug above.
**Definition of done:** Each tool tested against NIST Hacking Case disk image; tools refuse paths not in evidence registry; `tools/disk.py` and `tools/registry.py` each ≤400 LOC.
**Demo contribution:** Disk-artifacts moment (corroborating Ethereal install via MFT record dated 2004-08-19 22:48 UTC) inside 1:00–3:00.
**Judging criteria:** Breadth and Depth (5 disk + registry tools); IR Accuracy (structured CSV → typed Pydantic output).

---

### Epic 7 — Tool wrappers: log + network (EVTX + Hayabusa + Chainsaw + Zeek + Suricata)

**Business value:** Log triage + network analysis close the loop on the wardriving demo case — without these the "intercepted SMTP credentials" finding has no corroborating evidence and the critic CHALLENGE moment at 4:00–4:30 cannot resolve.
**Dependencies:** E4.
**Stories:** `parse-evtx`, `hayabusa-timeline`, `chainsaw-hunt`, `zeek-run`, `suricata-run`.
**Estimate:** ~2h.
**Story files:** `docs/stories/story-{slug}.md` for each slug above.
**Definition of done:** EVTX + Hayabusa + Chainsaw tested against sample EVTX corpus; Zeek + Suricata tested against Nitroba pcap; `tools/log.py` and `tools/network.py` each ≤400 LOC.
**Demo contribution:** Log + network analysis moments inside 1:00–3:00; the critic-CHALLENGE resolution at 4:00–4:30 (`zeek -r /evidence/captures/wardrive.pcap`).
**Judging criteria:** Breadth and Depth (closes the 4-family DFIR matrix); IR Accuracy (Sigma-based detection is the field-standard truth source).

---

### Epic 8 — Hypothesis state machine + investigator agent (Pydantic AI)

**Business value:** This IS the wedge. The hypothesis-pivot loop is the senior-analyst-sequencing mechanism Rob T. Lee names in 4+ public artifacts — and the criterion he calls the tiebreaker. Without this epic SilentWitness is a typed MCP wrapper with no behavioural differentiator from Valhuntir.
**Dependencies:** E4. Develops in parallel with E5/E6/E7 (agent's tool surface is the MCP boundary, not the individual wrappers).
**Stories:** `hypothesis-types`, `hypothesis-stack`, `hypothesis-budget`, `investigator-agent`, `investigator-hooks`.
**Estimate:** ~2h.
**Story files:** `docs/stories/story-{slug}.md` for each slug above.
**Definition of done:** Investigator runs end-to-end against Nitroba smoke pcap, forms ≥1 hypothesis, dispatches ≥1 specialist (stubbed if E9 not yet merged), logs every transition to `audit/hypothesis.jsonl`; budget enforcement triggers controlled abandon on synthetic test.
**Demo contribution:** The hypothesis-pivot moment at 3:00–3:30 (Vol symbol-table mismatch → rebuild → retry, logged as PIVOT); the live hypothesis stack in the rich layout 1:00–4:30.
**Judging criteria:** Autonomous Execution Quality (the tiebreaker — heaviest single contribution from one epic).

---

### Epic 9 — Specialist subagents (memory / disk / network / log)

**Business value:** Specialist dispatch is what makes the hypothesis log read as senior-analyst behaviour ("Memory specialist confirms Ethereal — hand off to network for pcap corroboration"). Without specialists the investigator looks like a chatty single agent.
**Dependencies:** E5 + E6 + E7 + E8.
**Stories:** `memory-specialist`, `disk-specialist`, `network-specialist`, `log-specialist`.
**Estimate:** ~2h.
**Story files:** `docs/stories/story-{slug}.md` for each slug above.
**Definition of done:** Investigator dispatches each specialist by name; specialist returns structured `SpecialistResult` consumed by hypothesis stack; each file ≤400 LOC; integration test asserts memory specialist cannot call disk tools (allowlist enforcement).
**Demo contribution:** Specialist dispatch visible in the hypothesis log and rich live layout.
**Judging criteria:** Autonomous Execution Quality (multi-agent sequencing); Breadth and Depth (each specialist demonstrates depth in one domain).

---

### Epic 10 — Closed-loop critic agent

**Business value:** The critic CHALLENGE at 4:00–4:30 is Rob T. Lee's exact sentence — "recognize when something doesn't add up" — performed live. This is the rarest behaviour in the visible 60-repo field (most Valhuntir clones do not ship a critic).
**Dependencies:** E8.
**Stories:** `critic-agent`, `critic-trigger`, `critic-verdict-handling`.
**Estimate:** ~2h.
**Story files:** `docs/stories/story-{slug}.md` for each slug above.
**Definition of done:** Critic fires at configured interval against a 10-finding fixture; CHALLENGE → investigator corroboration → confidence revision reproducible in integration test.
**Demo contribution:** The critic CHALLENGE moment at 4:00–4:30; the agent recognising over-confidence and corroborating via `zeek -r`.
**Judging criteria:** Autonomous Execution Quality (heavy — closed-loop self-correction); IR Accuracy (critic catches what the gates can't — overclaim drift).

---

### Epic 11 — Report-as-state (Markdown + PDF)

**Business value:** The report is the deliverable. PRD §3: the day-after-SilentWitness story is "the report is 80% drafted by the time the senior sits down to write the executive narrative." Without this the verify-link demo at 4:50–5:00 has nothing to click into.
**Dependencies:** E4 (uses `approve_finding` state to promote DRAFT → REVIEWED).
**Stories:** `report-template`, `report-writer`, `report-verify-links`, `report-pdf-export`.
**Estimate:** ~2h.
**Story files:** `docs/stories/story-{slug}.md` for each slug above.
**Definition of done:** Synthetic 5-finding case produces render-correct Markdown; PDF passes WeasyPrint with no errors; clicking a `[verify:...]` link in the rendered PDF anchors to the Appendix-Audit entry showing JSONL row + SHA256 + verbatim span.
**Demo contribution:** Report rendering at 4:30–5:00; verify-link click-through killer moment at 4:50–5:00.
**Judging criteria:** Usability (primary — the report is the deliverable five audiences read); Audit Trail Quality (Appendix-Audit + verify links ARE the audit-trail UX).

---

### Epic 12 — CLI (Typer) + Claude Code drop-in config

**Business value:** Every demo terminal command goes through this layer. `install --claude-code` is the zero-setup judge convenience — a judge on SIFT 2026 can immediately demo via the pre-installed Claude Code v2.0.61 without touching `pyproject.toml`.
**Dependencies:** E4 + E8 + E11.
**Stories:** `cli-init`, `cli-register-evidence`, `cli-investigate`, `cli-status`, `cli-review`, `cli-approve`, `cli-verify`, `cli-export`, `cli-baseline-comparison`, `cli-install-claude-code`.
**Estimate:** ~2h (each command is a thin Typer wrapper; stories parallel-friendly).
**Story files:** `docs/stories/story-{slug}.md` for each slug above.
**Definition of done:** All 10 commands implement exit-code semantics per ux-spec §2.2; `--version` prints bundle provenance; rich live layout degrades cleanly on `NO_COLOR=1` and `TERM=dumb`; drop-in config tested against pre-installed Claude Code on a SIFT 2026 VM.
**Demo contribution:** Every demo terminal command — `investigate`, `status`, `review`, `approve`, `verify`, `export`; `install` is the judges' first contact.
**Judging criteria:** Usability (heavy — primary surface); Constraint Implementation (typed CLI mirrors typed MCP); Autonomous Execution Quality (live rich layout makes senior-analyst sequencing visible).

---

### Epic 13 — Streaming HUD (OPTIONAL — stretch)

**Business value:** The HUD is the split-screen on the demo video (ux-spec §4) — terminal left, browser right, same data two surfaces. Makes the investigator's work watchable for a non-DFIR judge during 1:00–4:30. Cuttable: rich terminal layout alone carries the live-render value.
**Dependencies:** E8.
**Stories:** `hud-sse-server`, `hud-routes`, `hud-css`.
**Estimate:** ~2h.
**Story files:** `docs/stories/story-{slug}.md` for each slug above.
**Definition of done:** `silentwitness investigate --hud` auto-starts HUD on 127.0.0.1:8088; browser renders hypothesis stack + findings + last events in real time; banned patterns (Tailwind, frameworks, CDNs, charts) audited absent.
**Demo contribution:** The split-screen during 1:00–4:30.
**Judging criteria:** Usability (peripheral-glance second monitor); Autonomous Execution Quality (visible — invisible work doesn't score).
**OPTIONAL — drop if Wave 2 build runs hot.**

---

### Epic 14 — Accuracy harness + baseline comparison

**Business value:** The PRD §4 headline metric depends on this. Time-to-handoff-ready-report and hallucination-rate-Δ vs vanilla Protocol SIFT must be **measured, not estimated** per Rob T. Lee's honesty rubric. Without this the bar chart at 4:30–4:50 is hand-waving — the worst outcome for IR Accuracy.
**Dependencies:** E8 + E11.
**Stories:** `dataset-manifests`, `ground-truth-parsers`, `baseline-runner`, `silentwitness-runner`, `scorer`, `delta-report`.
**Estimate:** ~2h.
**Story files:** `docs/stories/story-{slug}.md` for each slug above.
**Definition of done:** `just harness` runs baseline + SilentWitness on Nitroba smoke set and emits Δ JSON + Markdown report; honest disclosure of NIST Hacking Case memorisation risk per PRD §9; per-case precision/recall/hallucination numbers consumed by the demo video's bar chart.
**Demo contribution:** The bar chart at 4:30–4:50.
**Judging criteria:** IR Accuracy (heavy — quantitative defensibility); Usability (accuracy report is a Devpost-mandated deliverable per PRD §10).

---

### Epic 15 — Adversary-pair case-trapdoor (**CUT for v1** per audit Decision B / B-PY-3)

**Status:** **CUT from v1 submission scope** per `docs/DEEP_AUDIT_REPORT.md` Decision B. Audit finding B-PY-3: `regipy` and `python-evtx` are read-only libraries — they cannot synthesize registry hives or EVTX files as this epic's spec required. Three of five `synth_*` helpers in `story-case-trapdoor-synthesis.md` cannot ship as written.

**Decision rationale:** PRD §9 already marked this epic as "time-permitting." E14 delivers measured Δ on three real datasets (Nitroba + NIST Data Leakage + NIST Hacking Case) — the headline metric is met without the synthetic adversary case. Demo loss is minor: the adversary-pair moment was a ~30s addendum to 4:30–4:50, not a load-bearing demo beat. Future-work track: rewrite to a template-fixture pattern (check in clean NTUSER.DAT / Security.evtx / dropper.exe fixtures, patch by byte offset) — see PRD §9 "Future work."

**Stories (DO NOT DISPATCH):** `case-trapdoor-synthesis`, `case-trapdoor-ground-truth` — story files retained on disk for the future-work track; orchestrator MUST skip them. `sprint-status.yaml` marks both `cut: true` + `optional: true`.

**Business value (preserved for future v2):** Most aggressive expression of entity gate + sanitizer at the limit — synthesise a case with timestomping, log clearing, process hollowing, and prompt-injection-in-registry, then show Δ vs baseline.

---

### Epic 16 — Documentation polish + submission

**Business value:** Judges read README before they demo. The 8 mandatory deliverables (PRD §10) must be present, linked, and verifiable. Cut this and the rules-§4 deliverables checklist fails — disqualification risk.
**Dependencies:** All preceding.
**Stories:** `readme-polish`, `architecture-diagram-png`, `accuracy-report-writeup`, `dataset-doc`, `try-it-out-doc`, `execution-logs-export`, `devpost-submission`, `third-party-notices` (new per audit F-DS-8 — license NOTICES file aggregating Hayabusa/Chainsaw/Velociraptor/Suricata/Vol3/EZ Tools/Pydantic AI/MCP/etc. attributions).
**Estimate:** ~2h.
**Story files:** `docs/stories/story-{slug}.md` for each slug above.
**Definition of done:** All 8 PRD §10 deliverables present + linked from README; Devpost submission confirmed; demo video published + embedded; rules §4 deliverable checklist passes a teammate audit.
**Demo contribution:** The full video deliverable + readable README + shipped sample case.
**Judging criteria:** Usability (judge's first contact); Audit Trail Quality (shipped sample case proves the audit trail without a run); rules §4 deliverable compliance (table-stakes for any score).

---

## 3. Component coverage audit

Cross-check against PRD §5 functional requirements + architecture component decomposition.

| Requirement / Component | Covered by |
|---|---|
| FR1 Run on stock SIFT 2026 | E1, E12, E16 |
| FR2 ≥15 typed MCP tools across families | E5 (memory, 7), E6 (disk + registry, 5), E7 (log + network, 5) — 20+ total |
| FR3 Model-agnostic via `SILENTWITNESS_MODEL` | E8, E9, E10 |
| FR4 Architectural rejection of unverified claims | E3, E4 |
| FR5 JSONL audit per tool call | E2, E4 |
| FR6 Markdown report with FOR508 sections + Gaps + Appendix-Audit | E11 |
| FR7 ≥1 self-correction in demo | E8 (PIVOT), E10 (critic CHALLENGE) |
| FR8 Claude Code drop-in config | E12 |
| FR9 Reference Pydantic AI agent + critic | E8, E10 |
| FR10 Docker Compose | E1 |
| FR11 Accuracy harness | E14 |
| Common types + IDs | E2 |
| Evidence registry + mount validation | E2 |
| HMAC ledger | E2, E4, E12 |
| FastMCP server + transports | E4 |
| Response envelope | E4 |
| Sanitizer | E3 |
| Hypothesis stack + events + budget | E8 |
| Specialists (4 × allowlisted) | E9 |
| Critic | E10 |
| Report renderer + PDF | E11 |
| CLI (10 commands per ux-spec §2.2) | E12 |
| Streaming HUD (optional) | E13 |
| Dataset manifests + ground truth + scorer + Δ | E14 |
| Case-trapdoor adversary pair (optional) | E15 |
| README + diagrams + sample case + Devpost | E16 |

No PRD FR or architecture component is unmapped. The two optional epics (E13, E15) are explicitly cuttable without leaving an FR unmet.

---

## 4. Implementation order (for orchestrator)

Stories marked `parallel:` can run concurrently with siblings at the same indentation. Epics marked `parallel-eligible: true` can run in parallel with sibling epics once their dependencies clear.

```yaml
dispatch_queue:

  # Wave 1 — foundation (sequential, blocks everything)
  - epic: E1
    parallel-eligible: false
    stories:
      - story-scaffold-uv-pyproject       # blocks rest of E1
      - story-ci-workflows                # parallel with pre-commit-hooks
      - story-pre-commit-hooks            # parallel with ci-workflows
      - story-docker-baseline
      - story-justfile-targets

  - epic: E2
    depends-on: [E1]
    parallel-eligible: false
    stories:
      - story-common-types                # blocks rest of E2
      - story-atomic-io                   # parallel with audit-logger
      - story-audit-logger                # parallel with atomic-io
      - story-evidence-registry
      - story-hmac-ledger

  - epic: E3
    depends-on: [E2]
    parallel-eligible: false
    stories:
      - story-output-normalizer           # blocks citation-gate + entity-gate
      - story-citation-gate               # parallel with entity-gate + sanitizer
      - story-entity-gate                 # parallel with citation-gate + sanitizer
      - story-sanitizer                   # parallel with citation-gate + entity-gate
      - story-gates-property-tests        # blocks epic close

  - epic: E4
    depends-on: [E3]
    parallel-eligible: false
    stories:
      - story-fastmcp-server-bootstrap    # blocks rest of E4
      - story-response-envelope
      - story-record-observation-tool     # parallel with interpretation/pivot/narrative
      - story-record-interpretation-tool
      - story-record-pivot-tool
      - story-record-narrative-tool
      - story-approve-finding-tool

  # Wave 2 — parallel tool wrappers + agent loop (4 epics in parallel)
  - epic: E5
    depends-on: [E4]
    parallel-eligible: true               # parallel with E6, E7, E8
    stories:
      - story-vol-pslist                  # blocks rest (skeleton)
      - story-vol-pstree-psscan
      - story-vol-malfind
      - story-vol-netscan
      - story-vol-cmdline
      - story-vol-dlllist-handles
      - story-vol-lsadump

  - epic: E6
    depends-on: [E4]
    parallel-eligible: true               # parallel with E5, E7, E8
    stories:
      - story-parse-mft                   # blocks rest (skeleton)
      - story-parse-amcache-shimcache
      - story-parse-prefetch
      - story-parse-shellbags
      - story-regripper

  - epic: E7
    depends-on: [E4]
    parallel-eligible: true               # parallel with E5, E6, E8
    stories:
      - story-parse-evtx                  # blocks rest (skeleton)
      - story-hayabusa-timeline
      - story-chainsaw-hunt
      - story-zeek-run
      - story-suricata-run

  - epic: E8
    depends-on: [E4]
    parallel-eligible: true               # parallel with E5, E6, E7
    stories:
      - story-hypothesis-types            # blocks rest
      - story-hypothesis-stack
      - story-hypothesis-budget
      - story-investigator-agent
      - story-investigator-hooks

  # Wave 3 — specialists + critic + report (parallel)
  - epic: E9
    depends-on: [E5, E6, E7, E8]
    parallel-eligible: true               # parallel with E10, E11
    stories:
      - story-memory-specialist           # all 4 parallel
      - story-disk-specialist
      - story-network-specialist
      - story-log-specialist

  - epic: E10
    depends-on: [E8]
    parallel-eligible: true               # parallel with E9, E11
    stories:
      - story-critic-agent
      - story-critic-trigger
      - story-critic-verdict-handling

  - epic: E11
    depends-on: [E4]
    parallel-eligible: true               # parallel with E9, E10
    stories:
      - story-report-template
      - story-report-writer
      - story-report-verify-links
      - story-report-pdf-export

  # Wave 4 — CLI + optional HUD
  - epic: E12
    depends-on: [E4, E8, E11]
    parallel-eligible: true               # parallel with E13
    stories:
      - story-cli-init
      - story-cli-register-evidence
      - story-cli-investigate             # consumes E8 live render
      - story-cli-status
      - story-cli-review
      - story-cli-approve
      - story-cli-verify
      - story-cli-export
      - story-cli-baseline-comparison
      - story-cli-install-claude-code

  - epic: E13
    depends-on: [E8]
    parallel-eligible: true               # parallel with E12
    optional: true
    stories:
      - story-hud-sse-server
      - story-hud-routes
      - story-hud-css

  # Wave 5 — harness + optional adversary pair
  - epic: E14
    depends-on: [E8, E11, E12]            # needs cli-baseline-comparison
    parallel-eligible: false
    stories:
      - story-dataset-manifests
      - story-ground-truth-parsers        # parallel with baseline-runner
      - story-baseline-runner             # parallel with ground-truth-parsers
      - story-silentwitness-runner
      - story-scorer
      - story-delta-report

  - epic: E15
    depends-on: [E14]
    parallel-eligible: false
    optional: true
    stories:
      - story-case-trapdoor-synthesis
      - story-case-trapdoor-ground-truth

  # Wave 6 — documentation + submission
  - epic: E16
    depends-on: [E1, E2, E3, E4, E5, E6, E7, E8, E9, E10, E11, E12, E14]
    parallel-eligible: false
    stories:
      - story-readme-polish               # parallel with diagram, accuracy, dataset, try-it-out
      - story-architecture-diagram-png
      - story-accuracy-report-writeup
      - story-dataset-doc
      - story-try-it-out-doc
      - story-execution-logs-export
      - story-devpost-submission          # blocks epic close
```

Wave 2's parallelism (E5 + E6 + E7 + E8 concurrent after E4 clears) is the largest single time saving — cuts Wave 2 wall-clock from ~8h sequential to ~2h parallel.

---

## 5. Risk-weighted prioritization

**Non-negotiable** (cannot cut without losing the wedge or violating rules §4): E1 (CI), E2 (audit), E3 (gates), E4 (MCP), E8 (hypothesis + investigator), E10 (critic), E11 (report), E12 (CLI), E14 (harness), E16 (submission).

**Cuttable** (already marked OPTIONAL): E13 (HUD) — rich terminal layout from E8 + E12 carries the live-render value; E15 (case-trapdoor) — E14 already delivers measured Δ on three real datasets.

**Reducible** (drop story count, not the epic):

- E5 — required: `vol-pslist`, `vol-pstree-psscan`, `vol-malfind`, `vol-netscan` (the symbol-table-mismatch demo tool). Droppable: `vol-cmdline`, `vol-dlllist-handles`, `vol-lsadump`.
- E6 — required: `parse-mft`, `parse-amcache-shimcache`, `regripper` (Ethereal install corroboration). Droppable: `parse-prefetch`, `parse-shellbags`.
- E7 — required: `parse-evtx`, `hayabusa-timeline`, `zeek-run` (intercepted-SMTP corroboration). Droppable: `chainsaw-hunt`, `suricata-run`.
- E9 — required: memory + disk specialists (demo dispatch path). Droppable: network + log specialists (collapse into investigator).

**Cannot reduce:** E2 (every story structurally required), E3 (95% coverage needs property tests), E4 (record-observation + approve-finding + envelope non-negotiable), E8 (entire machine end-to-end), E11 (all four needed for verify-link demo), E14 (Δ depends on every story chained), E16 (every story maps to a rules §4 deliverable).

**Aggressive-cut path** (all OPTIONAL + all reducible drops): 14 epics, ~58 stories, ~22h. Headline metric still measurable; verify-link demo still works; rules §4 deliverables still complete.

---

## 6. Spec metadata

- **Status:** DRAFT pending Abu approval.
- **Project name:** SilentWitness (verbatim; never paraphrase).
- **Total epics:** 16 (14 mandatory + 2 optional).
- **Total stories:** 83 (78 on the mandatory path).
- **Total estimate:** ~30–32h coding-agent time (full path); ~26–28h (mandatory); ~22h (aggressive cut).
- **Source documents:** `STRATEGY.md`, `docs/BRAINSTORM.md`, `docs/PRD.md`, `docs/architecture.md`, `docs/ux-spec.md`, `docs/CICD_SPEC.md`.
- **Vocabulary discipline (per PRD §14):** never "court-admissible" → "defensible audit trail" or "survives cross-examination"; never "autonomous SOC" / "replaces L1" / "eliminates hallucinations"; never "Ralph Wiggum Loop" in the doc itself — describe the behaviour instead.
- **Downstream artifacts:** `docs/stories/story-<slug>.md` files written in Wave 4 of the spec phase (one file per slug listed in §2 above).
- **Orchestrator entry-point:** §4 dispatch queue YAML; honour `parallel-eligible: true` for Wave 2 + Wave 3 maximum speedup.

---

**End of epics. Awaiting Abu approval.**
