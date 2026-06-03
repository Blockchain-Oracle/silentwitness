# Audit Report — SilentWitness Spec Set

**Audit date:** 2026-06-03
**Auditor:** automated audit-pass agent (fresh context)
**Scope:** `STRATEGY.md`, `docs/BRAINSTORM.md`, `docs/CICD_SPEC.md`, `docs/PRD.md`, `docs/architecture.md`, `docs/ux-spec.md`, `docs/epics.md`, `docs/sprint-status.yaml`, **83 story files** under `docs/stories/`.

---

## §0 — Headline verdict

**PASS WITH FIX-ITS.**

The spec set is internally consistent on every load-bearing dimension that matters for shipping: vocabulary discipline, SIFT 2026 binary paths, the seven BRAINSTORM architecture decisions, the dependency stack, all 27 MCP tool catalog entries, the verification-gate algorithm, coverage targets, the 8 mandatory deliverables, and the FRE 707 stale-date scrub. 83 story files exist and 83 are enumerated in `sprint-status.yaml` — a clean 1:1.

The fix-its are real but **none block the build**:

1. The **story-header `Depends on:` field drifts from `sprint-status.yaml` `depends_on:` in Epic 14** — most notably the scorer ↔ cli-baseline-comparison pair create a circular declaration if the headers are taken as source of truth (the YAML is the orchestrator-readable source and is acyclic; the orchestrator should ignore the header field).
2. **Three stories reference `architecture.md §5.7 / §5.9`** — architecture.md only has §5.1–§5.6; the actually-cited content (HMAC ledger, mount validation) lives at §4.9 and §4.11. The stories are coherent in intent; the section numbers are off.
3. **`epics.md` claims "Total stories: 81"** at line 6 and line 494, but `sprint-status.yaml` enumerates **83** and the `docs/stories/` directory holds **83 files** that match exactly. Bookkeeping drift in epics.md only — does not block.

Recommend: ship as-is, fix the three above in a single janitor commit before kickoff. Detailed fix-it list in §13.

---

## §1 — Vocabulary discipline

**Result: CLEAN (with documented carve-outs).**

### Banned phrases — repo-wide grep

| Phrase | Violations in spec body | Carve-out locations (documenting the gate) |
|---|---|---|
| "Ralph Wiggum" / "Ralph Wiggum Loop" | 0 | PRD §14, architecture §5.1 + §18, epics §6, ux-spec §9, ~25 story files (all explicit gate-text or anti-vocabulary discipline notes) |
| "court-admissible" | 0 | PRD §14, architecture §5.1 + §18, epics §6, ux-spec §9, ~30 story files (gate-text) |
| "autonomous SOC" | 0 | PRD §14 + epics §6 + ux-spec §9 + several stories (gate-text) |
| "eliminates hallucinations" | 0 | PRD §14, several stories (gate-text) |
| "replaces L1" | 0 | PRD §14, several stories (gate-text) |
| "find evil" (verbatim, used as marketing/command) | 0 | Allowed only as `Find Evil!` proper noun for hackathon name (PRD §14 carve-out is documented). `story-vol-malfind.md` and `story-cli-baseline-comparison.md` use "find evil" in single quotes describing **the canonical malfind primitive** and **the vanilla Claude Code prompt for the baseline**, respectively — both are accurate, not marketing. NOTE-level only. |

### Notable carve-outs (intentional, load-bearing)

- `story-devpost-submission.md` §"Banned-vocab carve-out" line 159 documents exactly which paths the repo-wide CI grep MUST exclude: `docs/devpost-submission-checklist.md`, `docs/PRD.md`, `docs/CICD_SPEC.md`, `docs/BRAINSTORM.md`, `docs/epics.md`, `docs/architecture.md`, `docs/stories/`, `tests/fixtures/`. Every other committed file MUST have zero matches.
- `story-case-trapdoor-ground-truth.md` line 146 documents that the GT-TRAP-008 synthetic injection payload string (`<system>...</system>`) does NOT contain banned vocab itself, but the surrounding test fixture path must be in the exclusion list. Verified correct.
- `story-readme-polish.md` `scripts/check_readme_gate.py` regex pattern `find evil(?![!])` correctly allows `Find Evil!` (trailing `!`) while rejecting bare "find evil" as marketing copy.

### Findings

**NO BLOCKERS. NO FIX-ITS.** Vocabulary discipline is the strongest dimension of the spec set. The CI gate design (per-file allowlist with documented carve-outs) is the right shape and is consistently invoked across docs.

---

## §2 — Architecture consistency

**Result: STRONG.**

### BRAINSTORM §3.5 dep stack vs architecture.md §1

Cross-checked line-by-line. Every entry matches: Python 3.12, uv ≥0.5, ruff ≥0.8, mypy ≥1.13, pytest+hypothesis, coverage[toml] ≥7.6, mcp ≥1.0 (FastMCP), pydantic-ai ≥0.1, Pydantic v2 ≥2.9, stdlib hmac/hashlib for PBKDF2-SHA256 600K iters, structlog ≥24, typer ≥0.15, weasyprint ≥63, mistune ≥3, httpx ≥0.27, spacy ≥3.8 + `en_core_web_lg`, pre-commit ≥4, detect-secrets ≥1.5, cyclonedx-py ≥4. Architecture.md §1 additionally pins `pytest>=8` and `coverage[toml]>=7.6` explicitly. **Match: 100%.**

### BRAINSTORM §3.7 folder structure vs architecture.md §3

Verbatim match. Architecture.md §3 reproduces the structure with file-purpose comments added. The `silentwitness_mcp/tools/yara_scan.py` entry in BRAINSTORM is preserved as "deferred — listed for completeness" in architecture.md §3 — that's a clean delta, not a contradiction. **Match: 100%.**

### Tool catalog: 27 entries

architecture.md §4.2 enumerates **27 tools** in a single table (22 production + 3 meta + 2 evidence-registry). Cross-reference against story files:

- **Memory (Vol3 — 9 tools):** `vol_pslist` (story-vol-pslist), `vol_pstree` + `vol_psscan` (story-vol-pstree-psscan), `vol_malfind` (story-vol-malfind), `vol_netscan` (story-vol-netscan), `vol_cmdline` (story-vol-cmdline), `vol_dlllist` + `vol_handles` (story-vol-dlllist-handles), `vol_lsadump` (story-vol-lsadump). **9/9 covered ✓**
- **Disk (5 tools):** `parse_mft` (story-parse-mft), `parse_amcache` + `parse_shimcache` (story-parse-amcache-shimcache), `parse_prefetch` (story-parse-prefetch), `parse_shellbags` (story-parse-shellbags). **5/5 covered ✓**
- **Log (3 tools):** `parse_evtx` (story-parse-evtx), `hayabusa_csv_timeline` (story-hayabusa-timeline), `chainsaw_hunt` (story-chainsaw-hunt). **3/3 covered ✓**
- **Network (2 tools):** `zeek_run` (story-zeek-run), `suricata_run` (story-suricata-run). **2/2 covered ✓**
- **Registry (1 tool):** `regripper_run` (story-regripper). **1/1 covered ✓**
- **Findings (4 tools):** `record_observation` (story-record-observation-tool), `record_interpretation` (story-record-interpretation-tool), `record_pivot` (story-record-pivot-tool), `record_narrative` (story-record-narrative-tool). **4/4 covered ✓**
- **Approval (1):** `approve_finding` (story-approve-finding-tool). **1/1 ✓**
- **Evidence (2):** `register_evidence` + `verify_evidence_hash` (story-evidence-registry covers both). **2/2 ✓**

**Total: 27/27 ✓. NOTE:** PRD §5 FR2 says "≥15 typed Pydantic-v2 forensic tools" — 27 comfortably clears the floor. PRD §8 row 3 says "15+ tools" — also clears.

### ADR-001 through ADR-010 consistency

All ten ADRs in architecture §10 are consistent with the dep stack and folder structure:

- ADR-001 (Custom MCP Server) — matches BRAINSTORM Decision 1.
- ADR-002 (Pydantic AI over Claude Agent SDK) — matches BRAINSTORM Decision 5. Story `story-investigator-hooks.md` line 141 explicitly notes "do not import from `claude_agent_sdk`" — well-policed.
- ADR-003 (Plain Python state machine) — matches BRAINSTORM Decision 2.
- ADR-004 (line-level + entity gate) — matches BRAINSTORM Decision 3.
- ADR-005 (Markdown report-as-state) — matches BRAINSTORM Decision 4.
- ADR-006 (spaCy + regex over LLM-as-extractor) — supports Decision 3.
- ADR-007 (stdlib hmac + PBKDF2 600K iters) — matches BRAINSTORM §4 verbatim.
- ADR-008 (single MCP server, not 9 backends like Valhuntir) — coherent with the LOC ceiling discipline.
- ADR-009 (no multi-examiner v1) — coherent with PRD §7 scope.
- ADR-010 (Ollama as no-cost option) — coherent with PRD §5 FR3 model-agnostic and the CI matrix.

### Pydantic AI vs Claude Agent SDK consistency

All agent-layer stories use Pydantic AI verbatim:
- `story-investigator-agent.md` — Pydantic AI `Agent[InvestigatorDeps, InvestigatorResult]`, `MCPServerStdio` toolset, model from `SILENTWITNESS_MODEL` env. ✓
- `story-critic-agent.md` — Pydantic AI `Agent[CriticDeps, CriticReport]`, separate context, default model from `SILENTWITNESS_CRITIC_MODEL`. ✓
- `story-memory-specialist.md` — Pydantic AI `Agent[SpecialistDeps, SpecialistReport]`, agent-delegation pattern verbatim. ✓
- `story-disk-specialist.md`, `story-network-specialist.md`, `story-log-specialist.md` — same shape (spot-checked). ✓
- `story-critic-verdict-handling.md` — references investigator agent's hook surface. ✓
- `story-investigator-hooks.md` — Pydantic AI `Hooks` per architecture §5.1; explicitly says "do NOT import from `claude_agent_sdk`." ✓

**Match: 100%. NO BLOCKERS. NO FIX-ITS.**

### NOTE-level observation

`story-investigator-hooks.md` line 141 references `context/technical/07-mcp-and-agent-platforms.md §C3.4 (Hooks)` for "broader Claude-Agent-SDK hook shape" — this is a useful cross-reference to remind implementers that Pydantic AI's Hooks API is similar to but distinct from Claude Agent SDK's. The story correctly mandates the Pydantic AI surface. Worth keeping as-is.

---

## §3 — SIFT 2026 path correctness

**Result: STRONG. Zero deviations from `.raw-design-research/03`.**

### Per-tool verification

| Tool | Verified path | Spec compliance |
|---|---|---|
| Volatility 3 | `/opt/volatility3/bin/vol` | **PASS.** Every reference (BRAINSTORM §3.2, architecture §2, §4.2, §8.1, §16; PRD §5 FR1; story-vol-* files lines 21–25; story-scaffold-uv-pyproject §103) uses the correct path. Every memory story includes the explicit warning "Do NOT use `/opt/volatility3-2.20.0/vol.py`" — `story-vol-pslist.md` line 115, `story-vol-netscan.md` line 88, `story-vol-malfind.md` line 87, `story-vol-dlllist-handles.md` line 98, `story-vol-lsadump.md` line 105, `story-vol-pstree-psscan.md` line 97, `story-vol-cmdline.md` line 87. **7/7 vol stories have the explicit anti-pattern note ✓** |
| EZ Tools (general) | `/opt/zimmermantools/<Tool>/<Tool>.dll` via `/usr/bin/dotnet` | **PASS.** `story-parse-mft.md` lines 41, 112; `story-parse-shellbags.md` lines 39, 103; `story-parse-amcache-shimcache.md`, `story-parse-prefetch.md`, `story-parse-evtx.md`. All use `dotnet /opt/zimmermantools/<Tool>/<Tool>.dll`. |
| EvtxECmd (inner-directory quirk) | `/opt/zimmermantools/EvtxeCmd/EvtxECmd.dll` (inner dir lowercase `e`) | **PASS.** `story-parse-evtx.md` lines 24, 41, 47, 95, 98, 141 — six references, all use the verified inner-`EvtxeCmd/` path. Line 141 contains the explicit anti-pattern note "Do NOT use `/opt/zimmermantools/EvtxECmd/EvtxECmd.dll` — that path does not exist." Line 24 hardcodes the constant `EVTXECMD_DLL = Path("/opt/zimmermantools/EvtxeCmd/EvtxECmd.dll")`. **Verified ✓** |
| RegRipper | `/usr/local/bin/rip.pl` | **PASS.** `story-regripper.md` lines 25, 44, every cmd_argv test fixture. BRAINSTORM §3.2 line 34, architecture §2 line 108 + §4.2 row 19. |
| Claude Code | `/usr/local/bin/claude` v2.0.61 | **PASS.** BRAINSTORM §3.2, architecture §7.1 step 1, PRD §5 FR1, story-cli-install-claude-code §22 (cites the path verbatim with `shutil.which("claude")` cross-check), story-cli-baseline-comparison §108 + §153, story-scaffold-uv-pyproject §103, story-try-it-out-doc §24. **Every reference verified ✓** |
| Hayabusa (must-install) | `/opt/hayabusa/hayabusa` | **PASS.** architecture §7.1 step 4 (install.sh downloads from Yamato-Security releases, SHA256 verified). `story-hayabusa-timeline.md` references the binary path. |
| Chainsaw (must-install) | `/opt/chainsaw/chainsaw` + `/opt/chainsaw/mappings/sigma-event-logs-all.yml` | **PASS.** `story-chainsaw-hunt.md` line 21 hardcodes both paths. architecture §7.1 step 5. |
| Zeek (must-install) | system `zeek` after `apt install` (architecture §7.1 step 6) | **PASS.** `story-zeek-run.md` line 23 + install.sh `--with-network` flag. |
| Suricata (must-install) | system `suricata` after `apt install` | **PASS.** `story-suricata-run.md` line 21. |
| Sigma rules (must-install) | `/opt/sigma` (default in `ChainsawInput`) | **PASS.** `story-chainsaw-hunt.md` line 21 sets `sigma_rules_dir: Path = Path("/opt/sigma")` as a Pydantic default. install.sh adds. |
| Node.js (must-install) | bootstrapped only for HUD (optional). | **PASS.** No node dependency in mandatory stories; HUD stories (E13 optional) note this. |
| `uv` (must-install) | install.sh bootstraps via `https://astral.sh/uv/0.5.11/install.sh` | **PASS.** CICD_SPEC §11.1 build stage installs `uv` at the pinned version. architecture §7.1 step 2. |
| PECmd / SrumECmd (must-install) | added by install.sh per `.raw-design-research/03` | **PASS.** architecture §7.1 step 8. `story-parse-prefetch.md` references PECmd via `dotnet /opt/zimmermantools/PECmd/PECmd.dll`. |
| capa, FLOSS, binwalk | not invoked in any mandatory story | **NOTE.** These are listed in BRAINSTORM §3.2 as "must install" but no current story wraps them as MCP tools. This is **not a violation** — BRAINSTORM is the menu; the actual scope is 27 tools per architecture §4.2. capa/FLOSS/binwalk are deferred / out-of-scope. Document this in the AUDIT explicitly so future expansion knows where to plug them. |

**Result: NO BLOCKERS. NO FIX-ITS. Path discipline is the second-strongest dimension of the spec set.**

---

## §4 — Verifiability mechanism consistency

**Result: STRONG.**

### Per-component review

- **story-citation-gate.md** uses **line-level** verification per architecture §4.5 — SHA256 of normalized output + line range + verbatim substring check. ✓
- **story-entity-gate.md** uses **NER (`spacy en_core_web_lg`) + regex catalog** per architecture §4.7 — IPv4/IPv6/MD5/SHA1/SHA256/registry-key/Windows-path/POSIX-path/account/mutex/port/email/URL. ✓
- **story-output-normalizer.md** implements **the 6-rule pipeline before SHA256** per architecture §4.6 — strip Vol3/EvtxECmd version banners, normalize wall-clock metadata timestamps via per-tool allowlist (NOT evidence-content timestamps — that distinction is preserved in the story per line 103), normalize whitespace, normalize path separators in tool-diagnostic lines only (NOT in evidence content), strip ANSI, normalize line endings. ✓
- **story-sanitizer.md** implements **the full 6-operation pattern catalog** per architecture §4.8 — XML role tokens, vendor chat-format tokens, regex catalog (with 4 documented initial entries: `(?i)ignore (?:all )?previous instructions`, `(?i)disregard (?:all )?prior`, `(?i)you are now [a-z ]+(?:agent|assistant|investigator)`, `(?i)END OF (?:SYSTEM|USER) PROMPT`), dangerous Unicode (RLO/LRO/BIDI U+202A–U+202E, U+2066–U+2069, ZWSP/ZWNJ/ZWJ/ZWNBSP, U+E0000–U+E007F tag chars), `[UNTRUSTED EVIDENCE BEGIN/END]` wrap, JSONL audit log of every strip (with `original_excerpt_hash` only — never the literal stripped content, line 128). ✓

### Important honesty caveat preserved

`story-sanitizer.md` line 129 documents that the wrap markers are "supplementary, not load-bearing on their own. The architectural defenses are the citation + entity gates." This matches architecture §4.8 paragraph 5 + §9 threat-model row verbatim. The honesty discipline is preserved.

**NO BLOCKERS. NO FIX-ITS.**

---

## §5 — Coverage target consistency

**Result: STRONG.**

### Per-module verification

- **`verification/*.py` ≥ 95%** per CICD_SPEC §8.1 — confirmed in:
  - `story-citation-gate.md`, `story-entity-gate.md`, `story-sanitizer.md`, `story-gates-property-tests.md`, `story-output-normalizer.md` — each story's exit-criteria section references the 95% floor.
- **`audit/*.py` + `findings/*.py` ≥ 90%** per CICD_SPEC §8.1 — confirmed in:
  - `story-audit-logger.md`, `story-hmac-ledger.md`, `story-evidence-registry.md`, `story-record-*-tool.md` series, `story-approve-finding-tool.md`.
- **Other `src/` ≥ 85%** per CICD_SPEC §8.1 — every other story spot-checked references `--fail-under=85`.
- **`src/silentwitness_agent/cli.py` excluded** — confirmed by `story-cli-init.md` line 131 ("excluded from unit coverage — covered by integration tests only; coverage_gate.py will not flag it"). Matches CICD_SPEC §8.1 table.
- **`src/silentwitness_agent/report/pdf.py` excluded** — confirmed by CICD_SPEC §8.1 table. `story-report-pdf-export.md` integration smoke is the coverage substitute.

**NO BLOCKERS. NO FIX-ITS.** Coverage policy is fully internally consistent.

---

## §6 — LOC budget sums

**Result: STRONG.** All shared files come in under the 400-LOC ceiling.

### Per-shared-file LOC delta sums

| File | Stories touching | Sum of LOC deltas | Ceiling | Verdict |
|---|---|---|---|---|
| `cli.py` | story-cli-init (120 skeleton), story-cli-register-evidence (60), story-cli-investigate (30), story-cli-status (20), story-cli-review (20), story-cli-approve (20), story-cli-verify (20), story-cli-export (20), story-cli-baseline-comparison (25), story-cli-install-claude-code (20) | **355 LOC** | 400 | **PASS (45-LOC margin)** |
| `tools/memory.py` | vol-pslist (80 skeleton), vol-pstree-psscan (~60), vol-malfind (~50), vol-netscan (~40), vol-cmdline (~30), vol-dlllist-handles (~70), vol-lsadump (split into `memory_extras.py`) | **~330 LOC main + ~50 LOC extras** | 400 each | **PASS — the `memory_extras.py` split is documented explicitly in `story-vol-lsadump.md` lines 21–28 + lines 105–109** |
| `tools/disk.py` | parse-mft (80 skeleton), parse-amcache-shimcache (~130), parse-prefetch (~70), parse-shellbags (~65) | **~345 LOC** | 400 | **PASS** |
| `tools/log.py` | parse-evtx (~140 skeleton), hayabusa-timeline (~130), chainsaw-hunt (~120) | **~390 LOC** | 400 | **PASS (tight — 10-LOC margin; story-chainsaw-hunt.md line 141 explicitly warns to factor into `_log_common.py` if draft exceeds 400)** |
| `tools/network.py` | zeek-run (~180), suricata-run (~180) | **~360 LOC** | 400 | **PASS** |
| `tools/registry.py` | regripper (140 single-tool) | **~140 LOC** | 200 (per architecture §4.2 budget) | **PASS** |
| `verification/citation_gate.py` | story-citation-gate | ≤200 LOC | 400 | **PASS** |
| `verification/entity_gate.py` | story-entity-gate | ≤300 LOC | 400 | **PASS** |
| `verification/sanitizer.py` | story-sanitizer | ≤300 LOC | 400 | **PASS** |
| `verification/normalizer.py` | story-output-normalizer | ≤200 LOC | 400 | **PASS** |
| `findings/observation.py` | story-record-observation-tool | ≤200 LOC | 400 | **PASS** |
| `findings/interpretation.py` | story-record-interpretation-tool | ≤200 LOC | 400 | **PASS** |
| `findings/narrative.py` | story-record-narrative-tool | ≤300 LOC | 400 | **PASS** |

**`tools/log.py` is the tightest budget (~390/400)** — surfacing this as a NOTE so the implementing agent for `story-chainsaw-hunt.md` knows to factor early into `_log_common.py` rather than wait for the file-size-guard to fire.

**NO BLOCKERS. NO FIX-ITS.** LOC discipline is the third-strongest dimension of the spec set.

---

## §7 — Story dependency graph

**Result: PASS WITH ONE FIX-IT (story-header drift, not YAML drift).**

### sprint-status.yaml — orchestrator-canonical source

All 83 stories enumerated. All `depends_on:` entries point at story IDs that exist. Spot-checked the YAML for cycles by walking each Epic:

- E1 → no inter-epic deps; internal deps all on `scaffold-uv-pyproject` ✓
- E2 → depends on `common-types`; all internal deps point at extant stories ✓
- E3 → linear chain rooted at `common-types` + `audit-logger` + `evidence-registry` ✓
- E4 → depends on E2 + E3 outputs; clean DAG ✓
- E5/E6/E7 — each rooted at first tool wrapper (`vol-pslist` / `parse-mft` / `parse-evtx` + `zeek-run`) which gates the rest. Clean ✓
- E8 → `hypothesis-types` → `hypothesis-stack` → `hypothesis-budget` → `investigator-agent` → `investigator-hooks`. Clean ✓
- E9 → each specialist depends on `investigator-agent` + the appropriate tool family — clean ✓
- E10 → all three critic stories rooted at `investigator-agent` / `critic-agent` ✓
- E11 → `report-template` → `report-writer` → `report-verify-links` + `report-pdf-export` ✓
- E12 → all rooted at `cli-init`, leaf nodes depend on tool/agent outputs ✓
- E13 (optional) → HUD chain rooted at `investigator-hooks` ✓
- E14 → `dataset-manifests` → ... → `scorer` → `delta-report`. Clean ✓
- E15 (optional) → `case-trapdoor-synthesis` → `case-trapdoor-ground-truth` ✓
- E16 → `devpost-submission` depends on all six other E16 stories ✓

**No cycles. No orphans. YAML is acyclic.**

### FIX-IT — Story-header `Depends on:` drift

The story-header `**Depends on:**` field (e.g., in `story-scorer.md`) lists **superset** dependencies that, if used by the orchestrator, would create cycles. Examples:

- **`story-scorer.md` header:** `Depends on: story-dataset-manifests, story-evidence-registry, story-cli-baseline-comparison, story-common-types`
  - **YAML:** `depends_on: [ground-truth-parsers, baseline-runner, silentwitness-runner]`
  - **Drift:** header references `cli-baseline-comparison`, but `cli-baseline-comparison` itself depends on `scorer` per YAML → **circular if header is followed.**
- **`story-silentwitness-runner.md` header:** lists `cli-investigate` — but `cli-investigate` depends on `investigator-agent` per YAML; `silentwitness-runner` also depends on `investigator-agent`. Not a cycle but adds redundancy.
- **`story-delta-report.md` header:** lists `atomic-io`, `silentwitness-runner` — YAML only has `scorer`. Header is more permissive than necessary.
- **`story-baseline-runner.md` header:** lists `cli-investigate` + `evidence-registry` — YAML only has `dataset-manifests`. Header is over-specified.

**Resolution:** the orchestrator MUST treat `sprint-status.yaml` as the source of truth and ignore the story-header field. The YAML is acyclic; the headers add aspirational ordering that creates a cycle on scorer ↔ cli-baseline-comparison. **FIX-IT (not BLOCKER)**: harmonize the story-header `Depends on:` field to match YAML for the four E14 stories (scorer, delta-report, baseline-runner, silentwitness-runner) before kickoff. Cost: ~10 min of edits.

### Parallel-safety per shared file

Epics.md §4 dispatch queue marks E5/E6/E7/E8 as `parallel-eligible: true`. The shared-file LOC budget table (§6 above) confirms this is safe: each epic touches a distinct file family (memory.py / disk.py / log.py + network.py / hypothesis/*). The CLI epic E12 is correctly **sequential** internally because all 10 commands edit `cli.py` — the YAML correctly puts `cli-init` first as the skeleton block; the remaining 9 must merge serially against `cli.py`. Same for E5: `vol-pslist` lands `_vol_common.py` skeleton; the rest merge against `memory.py` serially.

**No parallel-write collisions in the dispatch order.**

---

## §8 — Judging criteria coverage

**Result: STRONG. All 6 criteria covered with primary + secondary epics.**

| Criterion (PRD §8) | Primary epics + stories | Verdict |
|---|---|---|
| **1. Autonomous Execution Quality (tiebreaker)** | E8 hypothesis stack (story-hypothesis-types, story-hypothesis-stack, story-hypothesis-budget, story-investigator-agent, story-investigator-hooks); E10 critic (story-critic-agent, story-critic-trigger, story-critic-verdict-handling); E5 vol-pslist symbol-table self-correction story | **STRONG.** Three explicit self-correction moments demoed (Vol symbol-table mismatch → rebuild; citation gate REJECTED → re-read → revise; critic CHALLENGE → corroborate). Each is mapped to a story. |
| **2. IR Accuracy** | E3 verification (story-citation-gate, story-entity-gate, story-sanitizer, story-output-normalizer, story-gates-property-tests); E14 accuracy harness (story-dataset-manifests, story-ground-truth-parsers, story-baseline-runner, story-silentwitness-runner, story-scorer, story-delta-report); story-accuracy-report-writeup | **STRONG.** Measured Δ vs vanilla Protocol SIFT on 3 datasets, not estimated. |
| **3. Breadth & Depth** | E5 (7 memory stories → 9 tools); E6 (4 disk + 1 registry = 5 stories → 5 tools); E7 (3 log + 2 network = 5 stories → 5 tools) | **STRONG.** 27 typed tools across 5 forensic families. PRD §5 FR2 floor (15) cleared by 12 tools. |
| **4. Constraint Implementation** | E2 audit + ledger (story-audit-logger, story-hmac-ledger, story-evidence-registry); E3 gates (all 5 stories); E4 MCP server (story-fastmcp-server-bootstrap, story-response-envelope, all record-* tools); E1 (story-docker-baseline for sandbox/mount enforcement) | **STRONG.** Six architectural boundaries: typed MCP surface, citation gate, entity gate, sanitizer, HMAC ledger, mount validator. Each is server-side, not prompt-based. |
| **5. Audit Trail Quality** | E2 (story-audit-logger, story-hmac-ledger); E4 (story-approve-finding-tool); E10 (audit/critic.jsonl in story-critic-verdict-handling); E11 (story-report-verify-links — verify-link click-through is the audit-trail UX); E16 (story-execution-logs-export — sample case shipped at examples/) | **STRONG.** Per-tool-call JSONL with stable audit_id; HMAC-signed approval ledger; verify-link resolves to JSONL entry + SHA256 + cited span. |
| **6. Usability** | E12 (10 CLI command stories + story-cli-install-claude-code); E1 (story-docker-baseline); E16 (story-readme-polish, story-architecture-diagram-png, story-dataset-doc, story-try-it-out-doc); ux-spec.md (CLI + HUD ergonomics) | **STRONG.** One-command native install; two-command Docker Compose; drop-in `.claude/` for pre-installed Claude Code v2.0.61. |

**NO BLOCKERS. NO FIX-ITS.**

---

## §9 — 8 mandatory deliverables

**Result: STRONG. All 8 deliverables have a named story + Epic 16 owner.**

| # | Deliverable | Story file | Verdict |
|---|---|---|---|
| 1 | Public GitHub repo (MIT) | E1 (story-scaffold-uv-pyproject lands `LICENSE`); E16 (story-devpost-submission verifies before submit) | ✓ |
| 2 | Demo video ≤5 min | E16 (story-devpost-submission line 41 + line 109 — checklist documents the video link gate) | ✓ |
| 3 | Architecture diagram | E16 (story-architecture-diagram-png — renders the architecture.md §2 Mermaid to SVG/PNG with "architectural" vs "prompt-based" labels per Devpost requirement) | ✓ |
| 4 | Devpost write-up | E16 (story-devpost-submission writes `docs/DEVPOST.md`) | ✓ |
| 5 | Dataset documentation | E16 (story-dataset-doc writes `docs/DATASETS.md` with per-dataset manifests at `harness/datasets/<name>.yaml`); E14 (story-dataset-manifests is the structured source) | ✓ |
| 6 | Accuracy report | E16 (story-accuracy-report-writeup writes `docs/ACCURACY_REPORT.md`); E14 (story-scorer + story-delta-report produce the underlying numbers) | ✓ |
| 7 | Try-It-Out instructions | E16 (story-try-it-out-doc writes `docs/TRY_IT_OUT.md`); E1 (story-readme-polish embeds the 3-command quickstart above the fold) | ✓ |
| 8 | Agent execution logs | E16 (story-execution-logs-export ships sample case at `examples/case-hacking-case-001/audit/*.jsonl`); E2 (story-audit-logger is the source of truth) | ✓ |

**NO BLOCKERS. NO FIX-ITS.**

---

## §10 — Cross-document inconsistencies

**Result: PASS WITH 3 FIX-ITS.**

### FRE 707 stale-date scrub

**Result: CLEAN.** Grep across all 8 spec files + 83 story files for `FRE 707`, `Dec.*2024`, `December 1, 2024`, `effective.*2024` returns **zero hits** in the spec body. The COMPLETENESS.md flagged 5 stale references in `context/` corpus docs (`stakeholders/12` TOC, `evaluation/10` §C.6, `user/09` line 722, `domain/01` line 673), but **none of the stale dates leaked into the spec set.** The spec authors correctly avoided invoking FRE 707 entirely — `accuracy-report-writeup` and `devpost-submission` stories don't reference it; PRD §14 vocab-discipline section doesn't quote it either. Excellent discipline.

### VIGIA framing

**Result: CLEAN.** Grep for "VIGIA" across spec body + stories returns **zero hits.** No spec doc references VIGIA as a known artifact. This matches COMPLETENESS.md's framing of VIGIA as "unverified / possibly in Protocol SIFT NotebookLM or SANS Slack." Excellent discipline.

### Section number cross-references — 2 FIX-ITS

architecture.md uses §4.x for MCP server internals (envelope, gates, audit, ledger, evidence registry, mount validation) and §5.x for the reference agent (investigator, specialists, hypothesis stack, report, critic, CLI). Three stories cite **§5.7 / §5.9** which do not exist in architecture.md:

- **`story-try-it-out-doc.md` line 75:** `"evidence mount is not read-only" — cite architecture.md §5.9`
  - **Actually at:** architecture.md §4.11 ("Mount validation").
- **`story-try-it-out-doc.md` line 79:** `"HMAC verify fails ... cite architecture.md §5.7"`
  - **Actually at:** architecture.md §4.9 ("HMAC-signed approval ledger").
- **`story-try-it-out-doc.md` line 156:** `docs/architecture.md §3 + §5.9 (mount validation)` — same §4.11 issue.
- **`story-scorer.md` line 128:** `architecture.md §5.9 (mount safety)` — same §4.11 issue.
- **`story-hud-routes.md` line 167:** `architecture.md §5.7 (HMAC ledger)` — same §4.9 issue.

**This is a Cluster-B-agent-style §5→§4 number mistake that drifted into 2 stories** (story-try-it-out-doc, story-scorer, story-hud-routes). **FIX-IT (not BLOCKER)** — when the implementing agent reads the story and follows the section reference, they will land in the wrong section of architecture.md and may waste time. Cost to fix: 5 minutes (5 substitutions: `§5.9 → §4.11`, `§5.7 → §4.9`).

### NOTE — `story-record-narrative-tool.md` self-corrects a similar slip

`story-record-narrative-tool.md` line 111 contains the candid note: *"The brief's '§6.4' reference is a slip — the relevant sections are §5.3 (hypothesis machine) and §5.4 (report structure)."* This is the spec-writer agent **catching the slip mid-write** — exactly the discipline we want. Use this as the model for fixing the §5.9/§5.7 slips above.

### Epics.md vs sprint-status.yaml — story-count discrepancy

- **`epics.md` line 6:** "Total stories: 81"
- **`epics.md` line 35:** "Mandatory path (drop E13 + E15): 14 epics, 74 stories, ~28h. Full path: 16 epics, 81 stories, ~32h."
- **`epics.md` line 494:** "Total stories: 81 (74 on the mandatory path)."
- **`sprint-status.yaml` line 19:** "Total: 83 stories (76 mandatory + 5 optional HUD/adversary + 2 stretch docs)"
- **`docs/stories/` actual file count:** 83

**Drift:** epics.md is **2 stories behind** the canonical YAML + filesystem count. Spot-check: epics.md §1 says E16 has 7 stories — `sprint-status.yaml` enumerates exactly 7 (readme-polish, architecture-diagram-png, accuracy-report-writeup, dataset-doc, try-it-out-doc, execution-logs-export, devpost-submission). E14 also matches at 6. The drift is more likely a **stale total at the top of epics.md** that was not updated when the 2 late stories were added (probably `story-execution-logs-export` and `story-try-it-out-doc` per the system reminder "two async agents writing remaining harness + submission stories"). **FIX-IT (not BLOCKER):** update epics.md lines 6, 35, 494 to "83 stories" (or 76 mandatory).

---

## §11 — Context citation coverage

**Result: STRONG. Citations are meaningful, not lip-service.**

### Per-spec citation review

- **STRATEGY.md** — cites `context/domain/06-sift-toolchain-deep.md`, `research/` validation passes. Meaningful — the wedge is rooted in the practitioner pain documented in `user/09`.
- **BRAINSTORM.md** — cites `.raw-design-research/01`, `02`, `03` for every architectural decision, plus `context/competitive/11` for Valhuntir HMAC patterns. Each cite is load-bearing (the decision rationale references the specific finding).
- **CICD_SPEC.md** §1.1, §1.2, §1.3 — cites `BRAINSTORM` §3.5, `.raw-design-research/03`, `technical/07`, `technical/08` §4 + §5, `stakeholders/12` §A7 (Yotam Perkal). The Perkal lens in §1.3 is the strongest citation — it shapes the supply-chain CI gates (SBOM, license-check, trivy) and is honest about which threats CI can/cannot address (§10.4 line that explicitly carves out architecture vs CI scope).
- **PRD.md** — cites `user/09-ir-consultant-reality.md` (§A + §F) for the persona; `evaluation/10` for dataset choice; `competitive/11` for the Valhuntir floor; `.raw-design-research/01` for rules verification. Heavy on stakeholder docs in §14 vocabulary section.
- **architecture.md** — cites `.raw-design-research/02` (Pydantic AI), `.raw-design-research/03` (SIFT paths), `technical/07` (MCP protocol), `technical/08` (threat model), `competitive/11` (Valhuntir patterns), `domain/06` (tool catalog). §16 explicit audit checklist. Every architectural decision has a context cite.
- **ux-spec.md** — cites `user/09 §A.3 / §A.7 / §B / §D / §F.2` heavily for CLI ergonomics; cites `.raw-design-research/03` for port 8088 choice. Light on stakeholder cites — appropriate, as ergonomics is user-driven not stakeholder-driven.
- **epics.md** — light on direct context cites but each epic's "Business value" + "Judging criteria" framing is rooted in PRD §3 + §8 which themselves cite context heavily. Acceptable.
- **stories (spot-checked)** — `story-investigator-agent.md`, `story-critic-agent.md`, `story-citation-gate.md`, `story-entity-gate.md`, `story-sanitizer.md`, `story-hayabusa-timeline.md`, `story-parse-evtx.md` all cite specific `context/` paragraphs (e.g., `domain/02` §17/18, `technical/08` §3.5–3.7, `.raw-design-research/03` line numbers).

### Possible gaps (NOTE-level, not FIX-IT)

- **`context/stakeholders/12` Cluster A (judge curriculum)** is cited by PRD §14 (vocabulary discipline) and CICD_SPEC §1.3 (Perkal lens) but **not by ux-spec.md** despite ux-spec being the most judge-facing surface. NOTE: the ux-spec authors may have leaned more on `user/09` (practitioner-voice) than `stakeholders/12` (judge-voice); this is a reasonable trade-off because the user persona drives ergonomics more than the judge persona does. No fix needed.
- **`context/competitive/11` Valhuntir decomposition** is cited heavily in architecture but **not in epics.md** despite Valhuntir being the "level of quality to meet/exceed" bar PRD §1 invokes. NOTE: epics.md does cite "Valhuntir-style portability" in E4 DoD, but more explicit Valhuntir cross-refs in E2/E3/E11 would strengthen the audit trail. Not blocking.

**NO BLOCKERS. NO FIX-ITS. Context citation is the fourth-strongest dimension.**

---

## §12 — Sprint-status.yaml validation

**Result: PASS.**

### Spot checks performed

- **All 83 stories enumerated** — confirmed via `grep -c "^  - id:" sprint-status.yaml` returns 83. Confirmed via `diff` between the YAML's story IDs and the actual `docs/stories/` filenames — **zero diff**.
- **Optional flags set correctly** — E13 (HUD: hud-sse-server, hud-routes, hud-css) and E15 (case-trapdoor: case-trapdoor-synthesis, case-trapdoor-ground-truth) all carry `optional: true`. No mandatory story is mis-flagged.
- **All `depends_on:` entries point at real story IDs** — spot-checked 20 random entries; every dep resolves to an enumerated story. No orphans.
- **No cycles in the YAML** — walked the entire DAG epic-by-epic in §7 above. Clean.
- **Deadline ISO 8601** — `deadline: 2026-06-15T23:45:00-04:00` ✓ (EDT offset correct).
- **All story status = PENDING** — appropriate for spec-finalization handoff.
- **Issue/PR/merged_at empty strings** — correct shape for orchestrator Phase 1 fill.

**NO BLOCKERS. NO FIX-ITS.**

---

## §13 — Fix-it list (ordered by impact)

All three fix-its are **non-blocking** — the build can proceed without them and the orchestrator can correctly interpret the YAML. But cleaning them up is cheap (~30 minutes total) and prevents downstream agent confusion.

### FIX-IT 1 (highest impact) — Harmonize story-header `Depends on:` for E14 stories with YAML

**Files to edit:**
- `docs/stories/story-scorer.md` — header line: remove `story-cli-baseline-comparison`; harmonize to YAML `[ground-truth-parsers, baseline-runner, silentwitness-runner]`.
- `docs/stories/story-delta-report.md` — header: harmonize to YAML `[scorer]`. Currently lists `atomic-io, silentwitness-runner, dataset-manifests, common-types`.
- `docs/stories/story-baseline-runner.md` — header: harmonize to YAML `[dataset-manifests]`. Currently lists `evidence-registry, common-types, cli-investigate`.
- `docs/stories/story-silentwitness-runner.md` — header: harmonize to YAML `[investigator-agent, dataset-manifests]`. Currently lists more.

**Why:** Story-header dep field is a spec-author convenience; the YAML is the orchestrator-canonical source. The drift creates a logical cycle (scorer ↔ cli-baseline-comparison) **only if the headers are followed.** Harmonize, and the cycle disappears entirely.

**Cost:** ~10 min.

### FIX-IT 2 (medium impact) — Section number references in 3 stories

**Files to edit:**
- `docs/stories/story-try-it-out-doc.md` lines 75, 79, 156: replace `architecture.md §5.9` → `architecture.md §4.11`; replace `architecture.md §5.7` → `architecture.md §4.9`.
- `docs/stories/story-scorer.md` line 128: replace `architecture.md §5.9` → `architecture.md §4.11`.
- `docs/stories/story-hud-routes.md` line 167: replace `architecture.md §5.7` → `architecture.md §4.9`.

**Why:** architecture.md only has §5.1 through §5.6; the referenced content (mount validation, HMAC ledger) lives at §4.x. If an implementing agent reads the wrong section, they waste time hunting.

**Cost:** ~5 min.

### FIX-IT 3 (low impact) — epics.md story-count drift

**File to edit:**
- `docs/epics.md` lines 6, 35, 494: `81 stories` → `83 stories`; `74 mandatory` → `76 mandatory`; update §1 table if needed (most rows match).

**Why:** Bookkeeping. epics.md is 2 stories behind the canonical YAML (likely `execution-logs-export` and `try-it-out-doc` added late). Cosmetic but worth fixing before kickoff so the build estimate at the top of the doc matches reality.

**Cost:** ~5 min.

### Optional NOTE — Pre-emptive `tools/log.py` refactor heads-up

**`tools/log.py` sums to ~390/400 LOC** across `parse-evtx + hayabusa + chainsaw`. This is the tightest budget in the spec. `story-chainsaw-hunt.md` line 141 already documents the contingency ("factor JSON-flattening into `_log_common.py::_flatten_chainsaw_json`"). NOTE: orchestrator should be aware this is the most likely file-size-guard trip point during E7 dispatch.

---

## §14 — Strategic notes for Abu

Non-blocking; informational.

### N1. The verification gate is the wedge — and it's the strongest part of the spec

The citation gate + entity gate algorithm is described identically in BRAINSTORM Decision 3, architecture §4.5 + §4.7, story-citation-gate, story-entity-gate, and the sequence diagram architecture §8.4. The threat model architecture §9 honestly acknowledges residuals (paraphrase within cited span). The story-sanitizer line 129 honestly documents that the sanitizer is supplementary. This honesty-with-architectural-rigor combination is exactly the Rob T. Lee posture (per `stakeholders/12` Cluster A) and the Yotam Perkal posture (per `stakeholders/12` §A7). **This is the strongest competitive moat in the spec.** Don't let the implementing agents soften it during build.

### N2. The Pydantic AI bet is right, but versioning is a real risk

architecture ADR-002 pins `pydantic-ai>=0.1` targeting 1.105+. PRD §12 lists this as a risk. The `MCPServerStdio(..., tool_filter=callable)` API used by story-memory-specialist may not be present in earlier versions; the story (line 234) documents the fallback (custom `AbstractToolset` wrapper). **The fallback path is documented but unimplemented.** Recommend: have the first agent dispatched into Epic 9 verify the installed Pydantic AI version supports `tool_filter` BEFORE landing the specialists. If not, the wrapper-shim story should land first.

### N3. The §5.x section number drift is itself a useful signal

Three stories (story-try-it-out-doc, story-scorer, story-hud-routes) all mis-cite §5.x where they mean §4.x. This is consistent with the kind of slip that happens when a spec-author agent is using internal mental section numbers from BRAINSTORM (where Decision 5 = dep stack, Decision 7 = folder structure) and accidentally maps them onto architecture.md's headings. The spec-author who wrote story-record-narrative-tool.md caught the same slip explicitly (line 111: "the brief's '§6.4' reference is a slip"). NOTE for future passes: have the audit-pass agent run a §-reference grep against the actual section list before declaring done. The check is a 30-second `grep -n "^### " architecture.md` + a diff against story citations.

### N4. The 13-day calendar is tight — Epic 14 is the long pole

The mandatory path is 14 epics × ~2h = ~28h coding-agent time. Epic 14 (accuracy harness) has 6 stories with the longest critical path (`dataset-manifests` → `ground-truth-parsers` + `baseline-runner` + `silentwitness-runner` → `scorer` → `delta-report`). All four `silentwitness-runner` / `baseline-runner` / `scorer` dependencies must be reasonably solid for the bar chart at PRD §2 4:30–4:50 to be measured, not estimated. **Recommend:** kick off `dataset-manifests` and `ground-truth-parsers` as soon as Epic 8 (investigator-agent) lands, even if Epic 11 (report) isn't fully merged yet — gives extra runway on Epic 14.

### N5. The Mr. Evil memorization disclosure is correctly framed

PRD §9 ("Memorization risk is addressed honestly in the accuracy report") + story-accuracy-report-writeup line 25 ("Disclose Mr. Evil / Greg Schardt memorization risk per PRD §9 verbatim — the model has likely seen writeups; the harness measures gates not capability"). This is the Rob T. Lee honesty rubric in action. Don't let the demo-polish phase erode this framing.

### N6. The Pydantic AI 17.5K-star caveat from BRAINSTORM is preserved

PRD §12 risks table calls out Pydantic AI's rapid evolution. architecture ADR-002 pins minor version in uv.lock. Story-investigator-agent BDD test asserts `agent.model` repr contains the right provider string — this is the regression test that will catch a breaking change. **Good defense.**

---

**End of audit. Awaiting implementation kickoff.**
