# SilentWitness — Design & Content Brief

> One file for the designer (branded diagrams) **and** the website/UI copy. Everything needed
> to produce the visuals and a single-page docs/landing site is here. Nothing in this file is
> secret; it's all describing the public project.

---

## 0. What SilentWitness is (read this first)

**SilentWitness is a hypothesis-first AI incident-response investigator for the SANS SIFT
Workstation.** You point it at a Windows disk/memory image; it forms forensic hypotheses, pulls
evidence from a parsed index, and produces a cited, defensible report — with **architectural
guardrails** that structurally prevent the AI from hallucinating or modifying evidence.

**One-liner:** *"An autonomous DFIR analyst that has to prove every claim against the evidence —
and can't finalize until it has answered every question."*

**The wedge (why it's different):** most AI-DFIR tools let the model free-read raw evidence and
trust its output. SilentWitness inverts that: the agent's *only* interface is a search over
pre-parsed evidence, every claim must quote a real record (verified server-side), and a
framework-level gate refuses to let it conclude until all five investigative questions are
answered. Guardrails are **architectural, not prompt-based.**

---

## 1. Brand / visual direction

- **Logo:** top-right on every diagram and page header.
- **Tone:** forensic, precise, trustworthy — think "defensible audit trail," not "hacker neon."
  Clean, technical, confident.
- **Suggested palette (designer's call):** deep navy / slate as the base (matches the SANS judge
  pack header), a single confident accent (amber or teal) for the "evidence/trust boundary" and
  the "self-correction" highlights, neutral greys for infrastructure. Red used *only* for
  detections/findings, never for chrome.
- **Type:** a clean geometric sans for headings, a mono for any code/log snippets.
- **Motif:** a "chain of custody / provenance chain" visual language — every finding links back
  to evidence. Consider a subtle connecting-line motif throughout.
- **Diagram style:** boxes with rounded corners, clear groupings (swimlanes/containers), dashed
  borders = "prompt-based / supplementary," solid = "architectural / enforced." Label trust
  boundaries explicitly.

---

## 2. Diagrams to produce

There is a rough Mermaid-rendered reference at `docs/diagrams/architecture.png` (functional but
unbranded). Please re-create these as polished branded visuals.

### Diagram A — System Architecture (hero diagram)
Shows the whole system. Reference: `docs/diagrams/architecture.mmd`. Four main groups + two
externals:

1. **Examiner / SIFT workstation** — the `silentwitness` CLI: `register-evidence → prepare →
   index → investigate → review → export`.
2. **Evidence volume** — `/evidence`, **read-only (ro, noexec, nosuid)**. Mark this as a **TRUST
   BOUNDARY** (the agent never crosses it). Contents: ROCBA E01 disk + memory capture.
3. **Offline ingest spine** (one-time, parallel across CPU cores) — *architectural*:
   - `prepare`: dfVFS extracts artifacts read-only ($MFT, $UsnJrnl, EVTX, registry hives, SRUM,
     Amcache, Prefetch, **LNK, jumplists, PowerShell transcripts**).
   - **targeted parsers** (feeders): evtx / mft / registry / srum / usnjrnl / lnk / jumplist /
     prefetch / pstranscript.
   - **Sigma detection engine** (pySigma + the community SigmaHQ rule pack) → stages `sigma:<level>` alerts.
   - → **per-case FTS5 evidence index** (`index.db`). *Every row carries a sha256 + an audit_id.*
4. **silentwitness-mcp — the Custom MCP Server (THE PRODUCT)** — *architectural*. Contains:
   - **index query tools** (the agent's ONLY discovery surface): `search_evidence`, `timeline`,
     `get_record`, `list_detections`.
   - **adversarial sanitizer** (strips prompt-injection from evidence text).
   - **citation gate** (verbatim quote must be a substring of the cited record).
   - **entity gate** (every named IOC/PERSON/ORG must appear in the cited evidence).
   - **audit logger** (hash-chained JSONL) + **HMAC-signed approval ledger**.
5. **silentwitness-agent — the reference agent (Pydantic AI)** — *architectural*:
   - **investigator** (hypothesis loop: form / pivot / confirm / abandon).
   - **coverage gate** (refuses to finalize until all 5 Key Questions are answered).
   - **live critic** (separate agent, fresh context) + contradiction detectors.
   - **report** (Markdown source of truth).
6. **External, dashed (prompt-based / supplementary):** the optional **claude-code config**
   (CLAUDE.md + settings.json), and the **model-agnostic LLM provider** (anthropic / openai /
   google / ollama).

Key flows to draw: CLI → prepare → parsers+Sigma → index. Agent → (MCP) → query tools → index.
Query results → sanitizer → citation gate → entity gate → audit. Coverage gate → "ModelRetry:
question N uncovered" → back to investigator (a **loop arrow**, label it "self-correction").
Critic → "CHALLENGE → revise" → investigator (another loop). Everything → audit log.

### Diagram B — The Hallucination Firewall (10 layers)
A vertical stack / funnel: an LLM claim enters at the top, only a *grounded, cited* finding
exits at the bottom. Label each layer; mark which are architectural (solid) vs supplementary:
1. No raw-evidence surface (the agent can't free-read evidence)
2. Typed tool vocabulary + wiredness gate
3. Adversarial sanitizer on evidence text
4. **Citation gate** (claim words = verbatim substring of cited bytes)
5. **Entity gate** (every IOC appears in cited evidence)
6. Grounding score + provenance tier
7. ≥2-source corroboration → CONFIRMED label
8. Contradiction detectors (execution-overclaim / ghost-process / timestamp-paradox)
9. **Live closed-loop critic** (challenge → revise)
10. **Enforced coverage gate** + DRAFT→APPROVED HMAC ledger

Tagline for this diagram: *"Ten places a hallucination has to survive — and doesn't."*

### Diagram C — Ingest Pipeline (linear)
A clean left-to-right pipeline: **Evidence image (read-only)** → **dfVFS extract** → **targeted
parsers + Sigma detections** → **FTS5 index (sha256 + audit_id per row)** → **agent queries**.
Emphasize: the heavy parsing is **one-time/offline**; the agent only ever runs fast bounded
queries (10× performance story).

### Diagram D — Investigation Loop (sequence/flow)
The hypothesis-first loop: `list_detections` (start from staged alerts) → form hypothesis →
`search_evidence` / `get_record` → `record_observation` → **citation gate** → `record_interpretation`
→ confirm/pivot. Overlay the two self-correction mechanisms: the **critic** (challenges a
finding mid-run) and the **coverage gate** (blocks finalization until all 5 questions answered).

### Diagram E — Recall Improvement (bar chart) — IMPORTANT for the landing page
A simple bar chart telling the headline story (data from `ACCURACY_REPORT.md`):
- Baseline (old architecture): **40%**
- New capabilities, **no coverage gate**: **20%** (label: "premature convergence")
- + coverage gate (gpt-5.2): **30–50%** (show as a range)
- **+ coverage gate (gpt-5.5): 100%** (highlight this bar in the accent color)
Caption: *"The architecture put the evidence in reach; the coverage gate forced breadth; a
capable model found all 10 of 10."* Keep the honest framing — the 100% bar with a small footnote
"single run; recall varies by model — see accuracy report."

### Diagram F (optional) — Three-Claim Trace (provenance chain)
A horizontal chain for one finding: **Finding** → **cited record_id + verbatim quote** →
**search_evidence call (audit_id + timestamp)** → **source artifact (read-only image)**.
Shows "any finding is traceable to the tool execution that produced it."

---

## 3. Website / UI content (single-page docs + landing)

A single page is perfect. Suggested sections (copy below is ready to use, edit freely):

### Hero
**SilentWitness** — *The AI incident-response analyst that has to prove every claim.*
Sub: *Hypothesis-first DFIR for the SANS SIFT Workstation. It investigates a Windows image,
cites every finding to real evidence, catches its own hallucinations, and won't conclude until
it's answered every question.*
CTA buttons: **Read the docs** · **View on GitHub** · **Watch the demo**.

### What it does (3 cards)
- **Investigates autonomously.** Forms forensic hypotheses, pivots when the evidence disagrees,
  and self-corrects in real time — the whole reasoning arc is in the logs.
- **Proves every claim.** Each finding quotes a real evidence record, verified server-side. A
  fabricated quote is rejected before it reaches the report.
- **Answers the whole question.** An enforced coverage gate blocks the agent from finalizing
  until all five investigative questions (who/what/where/how/when) are addressed.

### How it works (use Diagram A or C)
Short paragraph: evidence is parsed once into a searchable index; the agent only ever queries
that index (it never free-reads raw evidence); every result passes a sanitizer, a citation gate,
and an entity gate before it can become a finding; a live critic and a coverage gate keep it
honest and complete.

### The hallucination firewall (use Diagram B)
Lead with: *"AI hallucinates. We made that structurally hard."* Then the 10 layers.

### Results (use Diagram E + a pull-quote)
Headline: *"10 of 10 findings recalled on the real SANS case."* Then the honest caveat:
*"Recall scales with the model and varies run-to-run; we publish the full distribution and the
failure modes we found and fixed."* Link to the accuracy report.

### Why it's built this way (the differentiators)
- **Architectural guardrails, not prompt-based** — enforced at the server/filesystem boundary,
  so they hold even if the model ignores its instructions.
- **Evidence integrity by construction** — read-only evidence, no write surface, tamper-evident
  provenance (sha256 + audit_id per row, hash-chained logs).
- **Honest by design** — a recall harness and an accuracy report that document false negatives,
  variance, and the hallucinations the gates caught.

### Quickstart (code block)
```bash
# on a SANS SIFT 2026 workstation
curl -fsSL https://raw.githubusercontent.com/Blockchain-Oracle/silentwitness/main/install.sh | bash
export OPENAI_API_KEY=...        # or ANTHROPIC_API_KEY — model-agnostic
silentwitness register-evidence rocba /path/to/rocba.E01
silentwitness prepare rocba && silentwitness index rocba
silentwitness investigate rocba
```

### Footer
Built for SANS **Find Evil!** 2026 · MIT licensed · extends Protocol SIFT.

---

## 4. Facts the designer/site can quote (all verifiable in the repo)

- Custom **MCP Server** architecture; **model-agnostic** (OpenAI / Anthropic / Google / Ollama).
- **MIT licensed**, runs on the SANS SIFT 2026 Workstation, one-line `install.sh`.
- Evidence index built from **9 targeted parsers** + a **Sigma detection engine** over the full
  community SigmaHQ rule pack.
- **100% recall (10/10)** on the real ROCBA case in the headline run; full honest measurement
  and the 40% → 20% → 30–50% → 100% progression in `docs/ACCURACY_REPORT.md`.
- Self-correction is real and logged: in the headline run the **live critic challenged 3 of 7
  findings** and the agent revised them.
- Every finding is traceable to the tool execution that produced it — see
  `docs/THREE_CLAIM_TRACE.md`.
