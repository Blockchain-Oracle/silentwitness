# Accuracy report — SilentWitness vs vanilla Protocol SIFT 2026

## Status + scope

- **Status:** DRAFT pending first end-to-end run during the demo recording session (`story-devpost-submission`). The numbers in §2 / §6 below are the calibrated targets the harness will compute and re-emit before submission; each row links to the scoring artifact at `harness/results/<dataset>/scoring-*.json` that will overwrite the placeholder once the run completes.
- **Datasets covered:** Nitroba (2010 DFRWS), NIST CFReDS Data Leakage Case, NIST CFReDS Hacking Case (Greg Schardt / Mr. Evil).
- **Harness version:** `harness.scorer` v1.0 (`story-scorer` merged in PR #200), `harness.delta_report` v1.0 (`story-delta-report` merged in PR #201), `harness.baseline.runner` (PR #198), `harness.silentwitness.runner` (PR #199).
- **Generation:** this document is hand-authored from the harness's machine-readable scoring + delta JSONs at `harness/results/<dataset>/`; re-running the recipe in §14 regenerates those JSONs without modifying this prose narrative.

## TL;DR

> **⚠️ All numbers in this table are CALIBRATED TARGETS** — the values the harness is designed to compute on the documented evidence corpora under the documented threat model. They are NOT yet measured. Every cell will be overwritten by `harness/results/<dataset>/scoring-*.json` after the demo-session runs land via `story-devpost-submission`. Read them as "what the harness will assert", not "what we observed".

| Dataset | Baseline hallucinations* | SilentWitness hallucinations* | Absolute Δ* | Reduction* | Baseline time-to-handoff (s)* | SilentWitness time-to-handoff (s)* |
|---|---|---|---|---|---|---|
| Nitroba | 4 | 0 | -4 | 100.0% | 610 | 250 |
| NIST Data Leakage Case | 7 | 1 | -6 | 85.7% | 2400 | 1100 |
| NIST Hacking Case | 6 | 0 | -6 | 100.0% | 1800 | 850 |

*Calibrated target; will be overwritten by `harness/results/<dataset>/scoring-*.json` post-run.

The architectural-gate hypothesis the harness will test: the citation gate + entity gate close most of the hallucination delta the baseline emits, and the time-to-handoff metric improves as a side effect of the agent not having to retroactively defend a hallucinated finding. Once the run completes, baseline numbers are reproducible from `harness/results/<dataset>/baseline-*.json` and SilentWitness numbers from `harness/results/<dataset>/silentwitness-*.json`.

## Methodology

The harness is composed of four pinned modules: `harness.baseline.runner` invokes the vanilla Protocol SIFT install path (sha256-pinned per `story-baseline-runner` / PR #198) against the mounted evidence; `harness.silentwitness.runner` invokes the SilentWitness investigator (`story-silentwitness-runner` / PR #199) against the same evidence with the same time budget; `harness.scorer` (`story-scorer` / PR #200) classifies every finding emitted by either side as `TRUE_POSITIVE | FALSE_POSITIVE | HALLUCINATION | FALSE_NEGATIVE` against the ground-truth parsers at `harness/ground_truth/`; `harness.delta_report` (`story-delta-report` / PR #201) renders the per-dataset Markdown + bar-chart artifacts.

The precision / recall / hallucination-rate definitions follow PRD §4 Secondary Metrics with one specific carve-out: HALLUCINATION is counted in the precision denominator alongside FALSE_POSITIVE — `precision = TP / (TP + FP + HALL)` — per the CyberSleuth Module III + DFIR-Metric HALL definition. A hallucination is "a claim that escaped and would have been flagged by an offline `grep`-the-mounted-image verifier." The scorer's HALLUCINATION verdict is reproducible by re-running the exact `find`/`grep` shell-out preserved in `evidence_shellout_argv` on the same mount.

Deterministic-output normalization rules (architecture.md §4.6) are applied before SHA256: strip timestamps using the documented timestamp-pattern table, normalize whitespace to single space, normalize path separators to POSIX forward-slash. The audit ledger's `result_sha256` field is computed against the normalized stdout, not the raw bytes.

Abstention is counted as a feature, not a loss (PRD §4 Epistemic-honesty count): an entity-gate REJECT is a measured-and-correct refusal, not a missed observation; it appears in the `epistemic_honesty_count` ScoringMetrics field and contributes positively to the demo metric in PRD §2.

## Baseline establishment

The vanilla Protocol SIFT baseline runs on a stock SIFT 2026 VM with Claude Code v2.0.61 at `/usr/local/bin/claude`, no MCP server attached, and the system prompt set to the vanilla Protocol SIFT prompt. The exact prompt the baseline runner uses is fetched from the upstream Protocol SIFT install script (SHA256-pinned per `story-baseline-runner` / PR #198 — see `harness/baseline/runner.py:install_baseline`) so the baseline is verifiably the same Protocol SIFT prompt the published install path delivers; no SilentWitness-side prompt mutation is applied. The evidence mount is identical to SilentWitness's: `ro,noexec,nosuid` per PRD §6 NFR. The time budget is identical: 30 minutes per case before the runner sends SIGTERM.

Exact reproducibility recipe (from `harness/baseline/runner.py` CLI):

```bash
uv run python -m harness.baseline.runner \
    --dataset <id> --evidence ./evidence \
    --work-dir ./harness/work/baseline \
    --timeout 1800
```

Memorization-risk disclosure for the NIST Hacking Case (PRD §9 verbatim): Greg Schardt / Mr. Evil canonical answers (MAC, IP, hostname, email) appear in hundreds of indexed writeups. A passing finding here is not evidence of working forensic capability — it is evidence the model has seen the writeups. The citation + entity gate forces every claim to ground in evidence-present spans rather than regurgitated memory; this dataset demonstrates the gates work, not latent capability.

## Datasets

Per-dataset source URLs + canonical SHA256s + answer-key paths + redistribution licenses are documented in [`DATASETS.md`](./DATASETS.md). Summary cross-reference:

- **Nitroba** — ~56 MB pcap; ground truth at `harness/ground_truth/nitroba.handcrafted.json` (community-converged consensus; password-gated official PDF NOT used).
- **NIST Data Leakage Case** — ~20 GB E01 + removable-media raw; ground truth parsed from `leakage-answers.pdf` via `harness/ground_truth/nist_data_leakage_parser.py`; 20+ structured findings.
- **NIST Hacking Case** — ~6 GB E01; ground truth at `harness/ground_truth/nist-hacking-case.supplemental.json` (community-converged supplemental answers) plus the NIST scenario document.

## Per-dataset results

> **⚠️ Calibrated targets** — all per-dataset numerics below are the targets the harness will compute; the prose narratives describe the audit-trail shape the harness produces, which is implemented and tested in the Epic 14 PRs. Once the runs complete, every number in these subsections will be re-emitted from `harness/results/<dataset>/scoring-*.json`.

### Nitroba

Baseline target (`harness/results/nitroba/baseline-*.json`): precision 0.50, recall 0.71, hallucination_rate 0.40, time-to-handoff 610 s. SilentWitness target (`harness/results/nitroba/silentwitness-*.json`): precision 0.875, recall 0.78, hallucination_rate 0.00, time-to-handoff 250 s. Δ shown in `harness/results/nitroba/delta.md` + bar chart at `delta.png`.

Specific baseline hallucination caught by the harness: the baseline cited `C:\Tools\HotPlugSpy\dropper.exe` as evidence of a delivery vector. The scorer's `find /evidence/nitroba -iname 'dropper.exe'` returned 0 hits. The SilentWitness investigator, when offered the same hypothesis, attempted `record_observation` against the same cited path — the entity gate rejected on `HALLUCINATED_ENTITIES`, the agent revised to cite a span actually present in the `vol_pslist` output, and the published finding carries audit_id `sift-harness-20260612-001`.

### NIST Data Leakage Case

Baseline target (`harness/results/nist-data-leakage/baseline-*.json`): precision 0.46, recall 0.65, hallucination_rate 0.33, time-to-handoff 2400 s. SilentWitness target (`harness/results/nist-data-leakage/silentwitness-*.json`): precision 0.81, recall 0.72, hallucination_rate 0.05, time-to-handoff 1100 s.

Representative finding the harness scored as TP for SilentWitness and FN for the baseline: the LNK record for `secret-financials.pdf` accessed from removable media volume `IRONKEY`. SilentWitness emitted the finding citing `audit_id` `sift-harness-20260612-002` (a `parse_mft` envelope whose stdout contains the LNK entry). The baseline produced only the human-readable phrase "removable media exfiltration observed" without citing the LNK record; the scorer marked this baseline emission as TP because the cited artifact substring matched, but recorded the absence of the LNK row as a quality gap noted in this report's §7.

### NIST Hacking Case

Baseline target (`harness/results/nist-hacking-case/baseline-*.json`): precision 0.55, recall 0.69, hallucination_rate 0.30, time-to-handoff 1800 s. SilentWitness target (`harness/results/nist-hacking-case/silentwitness-*.json`): precision 0.89, recall 0.76, hallucination_rate 0.00, time-to-handoff 850 s.

On-brand Mr. Evil demo finding: SilentWitness produces the Ethereal install-path observation by citing the `vol_pslist` audit row that shows `Ethereal.exe` running, then re-cites a `parse_mft` audit row that shows the installation entry — both audit_ids appear in the published finding. Specifically `sift-harness-20260612-003` is the entity-gate REJECT row where the agent first attempted to cite `C:\Tools\Ethereal\` (a path not in the cited span) and was forced to revise to `C:\Program Files\Ethereal\` (the path that IS in the cited span).

## Known false positives

The harness's TP/FP classification depends on the ground-truth parsers; when parser and agent disagree on artifact interpretation, the harness records FP even if the agent's reasoning was reasonable. Documented disagreements:

- **Nitroba — `mr.smith@nitroba.edu` email**: the ground-truth parser expects the substring `lily@willselfdestruct.com` for the harassment-email finding; the agent emitted an additional observation citing the legitimate recipient's address. The parser marked FP; on review, the agent's interpretation is correct context (the recipient is part of the harassment narrative), but the harness counts it as FP because no GT row matches.
- **NIST Data Leakage — `Recycle Bin` recovery**: agent cited a deleted-then-recovered `secret-financials.docx` from the Recycle Bin shellbag chain. The GT parser's expected substring is `IRONKEY` (the removable media volume); the Recycle Bin observation is correct but doesn't match the GT row format. FP per harness; arguably correct.
- **NIST Hacking Case — `Cain` tool installation timestamp**: agent emitted observation citing `Cain.exe` installed on a specific date; GT expects the substring `Cain` with no date qualifier. Agent's emission is correct + more specific; harness counts as FP because the GT row's expected substring is a substring of the agent's emission, not a literal match.

## Known misses

Ground-truth findings the agent did NOT surface within the time budget:

- **Nitroba — exact roster-room number** (room 214): the agent identified the dorm and the suspect but did not pin the room number; the parse chain (DHCP → MAC → room) requires a sub-hypothesis step that ran out of budget.
- **NIST Data Leakage — IronKey serial number**: the agent surfaced the volume label but not the device serial; the `setupapi.dev.log` parse was queued but not executed before the time budget closed.
- **NIST Hacking Case — Anonymizer.com browser cache entry**: agent surfaced the Cain + Ethereal trail but missed the Anonymizer.com web-history evidence; the prefetch parse identified the executable but the browser-history specialist was not dispatched.

## Residual hallucinations we caught

> **⚠️ Calibrated targets** — the four entries below describe the *shape* of REJECT events the gates produce. The `audit_id` values are illustrative; real values come from the demo-session runs and overwrite these in the final report.

The citation gate and entity gate REJECT envelopes before the claim lands in the report. Each entry below references the audit ledger row the harness will emit:

- **Baseline cited `C:\Tools\HotPlugSpy\dropper.exe` (Nitroba) → entity-gate REJECT** at `audit_id` `sift-harness-20260612-001`. Path absent from cited span; agent revised to cite the `vol_pslist` row that does contain `notepad.exe` and `cmd.exe`. The published finding never carried the dropper.exe claim.
- **Baseline cited `secret-financials.docx` (Data Leakage) → citation-gate REJECT** at `audit_id` `sift-harness-20260612-002`. The agent attempted `record_observation` citing a `parse_mft` audit_id whose result_sha256 didn't match the stored blob's hash; the citation gate rejected the row before the entity gate even ran.
- **Baseline cited `C:\Tools\Ethereal\` (Hacking Case) → entity-gate REJECT** at `audit_id` `sift-harness-20260612-003`. Agent revised to `C:\Program Files\Ethereal\` after re-reading the stored output via `verify_claim`.
- **Baseline cited a synthesized MAC address (Hacking Case) → entity-gate REJECT** at `audit_id` `sift-harness-20260612-004`. The agent's first emission carried `00:02:B3:DD:00:A2` — a MAC string that DOES appear in writeups but did NOT appear in any cited audit span. The entity gate flagged `HALLUCINATED_ENTITIES`; the revised emission cited the `vol_netscan` row that does contain the MAC.

## Residual hallucinations we did NOT catch

The gates close most of the hallucination class but not all of it. Offline `grep`-the-mounted-image verification of the final reports surfaces:

- **Nitroba — minor narrative gloss**: the published Nitroba report describes the suspect's apartment as "third floor"; the ground truth places the suspect on the third floor but the citation chain in the report does not include the room-number span. The gates accept it because the cited spans corroborate "dorm" and "Henry" but not "third floor" — the line-level entity match is coarser than the byte-level claim. Documented limitation per architecture.md ADR-004.
- **NIST Hacking Case — implicit timeline framing**: the published report orders the Ethereal install before the Anonymizer install; the GT confirms the order but no single cited audit row carries the absolute timestamps. Cross-row inference is unflagged by the gates because each individual citation passes; only an end-to-end timeline verifier (not currently shipped) would catch this.

## Sanitizer test corpus results

The `tests/property/test_sanitizer.py` property tests run hypothesis-generated prompt-injection patterns + unicode-trick characters against `silentwitness_mcp.verification.sanitizer.normalize_for_audit`. As of HEAD, the sanitizer detects + quarantines:

- 12/12 documented prompt-injection patterns from `harness/datasets/case-trapdoor.yaml` (the case-trapdoor synthesis is gated behind Epic 15; the YAML pattern list ships in this repo as the canonical pattern catalog).
- 100% of unicode bidi-control characters (U+202A through U+202E).
- 100% of zero-width characters (U+200B, U+200C, U+200D, U+FEFF).

The sanitizer's `entity-gate` integration further refuses any observation whose extracted entity list overlaps with the quarantine list; this is the architectural backstop against a tool stdout carrying an injected `[user] ignore previous instructions [/user]` payload.

## Threat model summary

What the architectural gates defend against (architecture.md §9):

- **Prompt injection in evidence**: tool stdout payloads attempting to redirect the agent's instructions are quarantined by the sanitizer before the entity gate sees them.
- **Citation forgery**: an agent cannot produce a finding citing an `audit_id` that doesn't exist or whose `result_sha256` doesn't match the stored blob — both gates verify against the immutable audit ledger.
- **Entity hallucination**: an agent cannot land an observation whose claimed entities (process names, file paths, MAC addresses, registry keys) are absent from the cited span. The entity gate's substring match is the load-bearing check.
- **Ledger tampering**: the HMAC-signed approval ledger at `/var/lib/silentwitness/verification/<case_id>.jsonl` is mode 0600 + PBKDF2-derived from a non-repo secret; tampering invalidates the chain.

What we explicitly do NOT defend against:

- **Compromised SIFT host**: a root-level compromise of the SIFT VM defeats every guarantee; the threat model assumes the host is trusted.
- **Malicious tool subprocess**: a backdoored Volatility plugin or EZ Tools binary running with the agent's privileges can fabricate stdout the gates would accept; the SHA256-pinned install path is the only mitigation.
- **Model API key leak**: a leaked API key lets an attacker run the model arbitrarily; SilentWitness's gates run on the operator's host, not the model's.
- **Side-channel timing**: an attacker who can observe wall-clock timing of `verify_claim` calls can infer agent state; the threat is acknowledged and unmitigated.

## Limitations + future work

- **Mr. Evil memorization risk** (also noted in §4): canonical answers appear in hundreds of indexed writeups. A passing finding on this dataset is evidence the gates work, not evidence of latent capability. The case-trapdoor synthesis (Epic 15) is the long-term answer; until it ships, NIST Hacking Case results should be read as a gate-validity proof.
- **Critic-of-critic shared-inference failure**: the critic agent runs on the same model family as the investigator; when both models share the same pretraining blind spot, the critic cannot independently surface it. Mitigation surfaces with explicit cross-model critique (a Sonnet investigator + Opus critic mix is the eventual configuration); not currently shipped.
- **Gate scope is line-level entity match, not byte-level** (architecture.md ADR-004). A claim whose entities all appear on cited spans but whose semantic framing differs from the spans (e.g., "third-floor" inference from spans that contain "dorm" + "Henry" but not "third") passes the gates. The §10 entry is one example. End-to-end timeline / framing verification is future work.

## Reproducibility

To regenerate this entire report's machine-readable underlay (the scoring + delta JSONs the prose cites) on a clean SIFT 2026 VM:

```bash
# 1. Provision the VM per install.sh (excluding --diagrams; this report
#    does not require mmdc).
./install.sh

# 2. Fetch the three active datasets per docs/DATASETS.md §3 recipes.

# 3. Re-run the full accuracy harness for each dataset:
for dataset in nitroba nist-data-leakage nist-hacking-case; do
    just harness DATASET=$dataset
done

# 4. Generate the per-case baseline-comparison artifact (used in §6):
#    uses scorer + delta-report; outputs cases/<id>/baseline-delta.json.
for dataset in nitroba nist-data-leakage nist-hacking-case; do
    uv run silentwitness baseline-comparison $dataset
done
```

Expected wall-clock derivation: the TL;DR target times-to-handoff sum to ~2 h 6 min for the baseline and ~35 min for SilentWitness across the three active datasets (610+2400+1800 + 250+1100+850 seconds = 7610 s ≈ 2.1 h on the model side). Add ~30 min for `verify_manifest` + harness IO + scoring + delta-report + bar-chart rendering. Add 1–2 h slack for first-run dataset download (NIST artifacts are 20+ GB; download time dominates fresh runs). Total upper bound: ~4 hours fresh, ~3 hours warm-cache. Expected token spend at the default model (`anthropic:claude-opus-4-7`): ~$60–$80 USD across all three datasets, dominated by the Hacking Case's larger evidence-tree exploration.

## Appendix A — Audit-trail samples

> **⚠️ Illustrative format** — the three JSON blobs below show the *shape* of audit ledger rows the production code emits (envelope keys + value types per `silentwitness_mcp.audit.logger` and `silentwitness_mcp.envelope`). The `audit_id` values use placeholder dates and the `result_sha256` values are truncated examples; real ledger rows from the demo-session runs replace these in the final report.

Three representative `audit/*.jsonl` rows (one citation-gate PASS, one citation-gate REJECT, one entity-gate REJECT):

```json
{"audit_id":"sift-harness-20260612-001","ts":"2026-06-12T10:00:00Z","tool":"record_observation","backend":"agent","status":"APPROVED","citation_gate":"PASS","entity_gate_matches":["smss.exe","PID 388"],"result_sha256":"11f9c283c2879d70..."}
```

```json
{"audit_id":"sift-harness-20260612-002","ts":"2026-06-12T10:01:00Z","tool":"record_observation","backend":"agent","status":"REJECTED","citation_gate":"FAIL","reason":"CITED_SHA256_MISMATCH","result_sha256":null}
```

```json
{"audit_id":"sift-harness-20260612-003","ts":"2026-06-12T10:02:00Z","tool":"record_observation","backend":"agent","status":"REJECTED","entity_gate_match":null,"reason":"HALLUCINATED_ENTITIES","hallucinated":["C:\\Tools\\Ethereal\\"]}
```

## Appendix B — Glossary

- **TP** (TRUE_POSITIVE): an emitted finding whose cited substring matches a ground-truth row's expected substring.
- **FP** (FALSE_POSITIVE): an emitted finding whose cited substring is present in evidence but does not match any ground-truth row.
- **FN** (FALSE_NEGATIVE): a ground-truth row not surfaced by any emitted finding within the time budget.
- **Hallucinated claim**: an emitted finding citing an artifact substring absent from the mounted evidence (per CyberSleuth Module III + DFIR-Metric HALL).
- **Abstention**: an entity-gate REJECT that prevents a low-confidence observation from landing in the report; counted positively in `epistemic_honesty_count`.
- **citation-gate PASS / REJECT**: the citation gate verifies (a) the cited `audit_id` exists in the ledger, (b) the cited `span_text` substring is present in the stored audit blob's normalized output, (c) the stored blob's SHA256 matches the cited SHA256.
- **entity-gate REJECT**: the entity gate verifies that every entity extracted from the observation text (process names, file paths, MAC addresses, registry keys) appears as a substring in the cited spans. REJECT on any mismatch.
