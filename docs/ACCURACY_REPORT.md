# SilentWitness — Accuracy Report

> Self-assessment of findings accuracy on the SANS **Find Evil!** judged case (ROCBA).
> Honesty is the point: this documents what works, what is noisy, what we catch, and what
> still leaks — measured end-to-end on real evidence, not asserted.

---

## 1. What was measured, and how

- **Case:** the official SANS Find Evil! *Standard Forensic Case* — "The Fred Rocba Case"
  (one Windows 10 host: ~22 GB E01 disk + memory capture). See [`STARTER_CASES.md`](STARTER_CASES.md).
- **Ground truth:** 10 hand-crafted findings (`harness/ground_truth/rocba.handcrafted.json`)
  keyed to the case's **5 Key Questions** (projects accessed / what was taken / where it went /
  how / when). Expectations come from the SANS briefing deck — **not** from the disk the agent
  reads — so scoring is non-circular.
- **Scorer:** `harness/score_case.py` reads the agent's recorded observations from
  `findings.json`, resolves each cited `record_id` to its evidence-index `artifact_path`, and
  marks a ground-truth finding **recalled** when one of its expected substrings appears in the
  finding text **or** a cited artifact path. Recall = recalled / 10.
- **Runs:** the full pipeline (`register-evidence → prepare → index → investigate`) was run on
  real evidence for several model/configuration points. Raw logs for the headline run are
  committed under [`docs/execution_logs/`](execution_logs/).

---

## 2. Recall — the honest progression

Recall is **not** a single number; it depends on the architecture, the breadth-enforcement
gate, and the model. This progression is the real story and the most important thing here:

| Configuration | Recall | What happened |
|---|---:|---|
| Baseline (pre-rearchitecture raw-tool agent) | 40% | original |
| New index spine, **coverage gate OFF** (gpt-5.2) | **20%** | the agent confirmed one brute-force hypothesis from the loudest detection signal and concluded — never addressing the other questions, though the evidence was indexed |
| + enforced coverage gate (gpt-5.2) | 30–50% | breadth restored, but **high run-to-run variance** (see §3) |
| Archived larger-model benchmark | **100% (10/10)** | 9 findings, 6 confirmed hypotheses; every Key-Question finding recalled |

**Headline:** with the coverage gate and a capable model, the system recalled **all 10**
ground-truth findings on the real case — the stolen SRL R&D projects (LNK targets
`SRL-Projects - Airwolf / Gunstar / Blue Thunder`), the exfiltration channels
(`G:\My Drive\…\Exported-PST\SRL-EMAIL-EXPORT`, OneDrive, Dropbox), the RDP access vector, the
SDelete anti-forensics, the BACKUPADMIN brute-force, and the intrusion window.

**The caveats in §3 matter as much as the headline.**

---

## 3. What is noisy, and why (false negatives / variance)

This is a **nondeterministic system on a framework known to hallucinate**; we engineered around
that, but we do not claim a stable 100%.

- **Run-to-run variance is real.** With gpt-5.2 + the gate, two runs scored 50% and 30% and
  overlapped on only *one* finding — yet **both covered all five investigative dimensions**.
  The variance is not the gate failing: several Key Questions have **multiple** ground-truth
  findings (Q3 = OneDrive *and* Dropbox *and* Office365; Q4 = RDP *and* SDelete *and*
  BACKUPADMIN), the gate enforces *one* cited observation per question, and which sibling the
  model surfaces is stochastic.
- **Recall scales with model capability.** gpt-5.2 varied between 30–50%, while an archived
  higher-cost benchmark reached 100% on the *same* architecture, index, and gate. We report both,
  not only the best, but the higher-cost run is not the recommended default operating posture.
- **Premature convergence is the failure mode we found and fixed.** Without the coverage gate,
  even a capable model collapsed onto the single loudest signal (~540k brute-force detections)
  and scored *below* baseline (20%). The gate — a framework-level `output_validator` that
  refuses to finalize until every Key Question has a supporting observation — is what prevents
  this.

### False positives

The scorer separates **false positives** from hallucinations. A hallucination is a cited artifact
that cannot be found in the mounted evidence. A false positive is grounded in a real artifact but
does not match the hand-crafted ground-truth finding set.

Known false-positive risk in the ROCBA runs is over-broad interpretation, not fabricated artifacts:
for example, cloud-sync and logon observations can be evidence-present while still too broad until
the critic narrows them to the specific cited records. The headline run includes that challenge and
revision loop for O-004/O-007 in `docs/execution_logs/rocba_headline_run/critic.jsonl` and
`findings.jsonl`. We treat those as noisy claims that must be narrowed, not as proof the raw
artifact was invented.

---

## 4. Hallucination controls — what we catch (and how)

Per the rules' asymmetry ("honesty valued over perfection"; confident wrong answers get zero),
hallucination *prevention* is architectural here, not prompt-based:

- **Citation gate (server-side).** Every finding cites a `record_id` + a verbatim `span_text`;
  the gate rejects the observation unless `span_text` is a literal substring of the cited index
  record's stored bytes. A fabricated quote cannot pass — rejected at the tool boundary before
  it reaches the report.
- **Entity gate (spaCy NER).** Every IOC / PERSON / ORG named in an observation must appear in
  the cited evidence text, or it is rejected (`HALLUCINATED_ENTITIES`). In an earlier live run
  this gate caught 6 ungrounded entities the model tried to assert.
- **Adversarial sanitizer.** Evidence text is stripped of prompt-injection markers before it
  reaches the model.
- These are **architectural** (in `silentwitness_mcp`), so they hold even if the model ignores
  its instructions — see §6.

## 5. Self-correction — documented, in the logs

Self-correction is in the audit logs, not staged for the video. In the headline run
([`execution_logs/rocba_headline_run/critic.jsonl`](execution_logs/rocba_headline_run/critic.jsonl))
the live critic (separate agent, fresh context) **CHALLENGED 3 of 7 findings** (O-002, O-004,
O-005) on real grounds — e.g. O-002: the critic narrowed an over-broad logon claim to the
specific `LogonType=3 NTLM` / `LogonType=10 RDP` records actually cited. The investigator then
**revised**: O-006/O-007 record *"This revision removes the specific dates that were
challenged"* and *"This revised interpretation follows the critic guidance."* A genuine
challenge → revise loop, traceable end to end.

The enforced **coverage gate** is a second, structural self-correction: when the agent tries to
finalize with a Key Question unanswered, it is bounced back (`ModelRetry`) with the gap named,
and resumes investigating.

## 6. Evidence integrity — how the architecture prevents data modification

Evidence integrity is **architectural, not prompt-based** — there is no tool path by which the
agent could alter original evidence, regardless of what the model decides:

- **Read-only evidence.** Original images are opened read-only; extraction uses dfVFS over the
  E01 via libewf in read-only mode. The agent process never opens raw evidence at all.
- **No write surface.** The agent's *only* discovery interface is the index query tools
  (`search_evidence` / `timeline` / `get_record` / `list_detections`). The raw-evidence and
  tool-running surfaces were demoted off the agent (firewall layer #1): no registered tool
  writes to `/evidence`. A `forbidden-paths` guard additionally blocks writes to evidence/system
  paths.
- **Tamper-evident provenance.** Every indexed row carries a `sha256` of its source artifact and
  the `audit_id` of the extraction that produced it; the audit log is hash-chained JSONL;
  examiner approvals are HMAC-signed.
- **If the model ignores a restriction:** because enforcement is at the MCP-server / filesystem
  boundary (not the prompt), a model that "tries" to read or write raw evidence simply has no
  tool that does so — the call surface does not exist.

## 7. Known issues we are NOT hiding

- **`[UNTRUSTED EVIDENCE BEGIN]` marker leakage.** `get_record` wraps evidence text in
  untrusted-content markers for safe display; in the headline run the model copied those marker
  strings into some interpretation justifications (O-001…O-007). It does not affect recall or
  citations but pollutes report prose. Tracked as a cleanup item.
- **Single-run 100% is not a stability claim.** See §3 — we report the distribution, not the
  peak.
- **Memory analysis is not yet in the recall path.** Current recall is disk-derived;
  disk⊕memory corroboration is planned, not done.
- **Plaso super-timeline contributes 0 events on this image** (libevtx crashes on the ROCBA
  EVTX); we route around it with targeted parsers and say so rather than hide the empty pass.

---

## 8. Reproducing this

```bash
# on a SANS SIFT 2026 workstation, with your own LLM API key exported
silentwitness register-evidence rocba /path/to/rocba.E01
silentwitness prepare rocba           # dfVFS extract (read-only)
silentwitness index rocba             # targeted parsers + Sigma detections -> FTS index
SILENTWITNESS_MODEL=openai-chat:gpt-5.2 silentwitness investigate rocba --max-iterations 80
python -m harness.score_case --case cases/rocba --dataset rocba
```

The archived higher-cost benchmark logs are committed under
[`docs/execution_logs/rocba_headline_run/`](execution_logs/rocba_headline_run/) for the three-claim
trace (find → `record_id` → `search_evidence` execution in `index.jsonl`).
