# Novelty Check: Evidence-Locked Findings

Date: 2026-06-02
Repos audited at HEAD: `AppliedIR/Valhuntir`, `AppliedIR/sift-mcp` (depth=1 clones)

---

## Q1: Valhuntir / AppliedIR code paths

**Verdict:** **novel** — the architecture explicitly does NOT do byte-level citation verification or entity-vs-evidence checking. The closest existing primitives stop one architectural step short.

**Evidence (with file:line citations of what each Valhuntir gate ACTUALLY does):**

### 1. `record_finding` MCP tool — `forensic-mcp/server.py:126-254`
- Accepts `finding` dict with `observation`, `interpretation`, `audit_ids`, `confidence`, etc.
- Schema validates string lengths only (`_validate_str_length` at lines 178-188).
- Passes through to `manager.record_finding` for actual gating.
- **Does NOT load the referenced audit_id tool outputs.**
- **Does NOT verify any observation/interpretation text appears in the cited evidence.**
- **Does NOT extract entities from finding text.**

### 2. `manager.record_finding` — `forensic-mcp/case/manager.py:660-1158`
The gating it DOES perform:
- Schema validation via `validate_finding_data` (lines 679-687).
- `audit_id` existence check on artifacts (lines 821-862): "artifact has an `audit_id` → look up that ID in `audit/*.jsonl` → if not present, REJECT". This is **ID existence**, not content matching.
- Hash-based provenance chain resolution (lines 940-1100) — uses `input_files` and `output_files` to trace which evidence file produced an artifact's audit_id. Sets `provenance_grade = FULL/PARTIAL`. Again, this is provenance chain integrity, not claim-vs-content matching.
- "Hard reject: artifact sources must be in evidence registry" (line 1121). Path-level check that source filenames are registered evidence. Still not content-level.

### 3. `validate()` (the "validate_finding" tool's implementation) — `forensic-mcp/discipline/validation.py:23-105`
This is the entire body of "validate":
```python
required = ["title", "observation", "interpretation", "confidence", "type"]
for field in required:
    if not finding.get(field): errors.append(...)
# audit_ids must be a list
# type must be in {finding, attribution, conclusion, exclusion}
# confidence must be in known set
# attribution requires 3+ audit_ids
# event_timestamp regex check
```
That is the whole thing. **It is pure schema validation with one count constraint (attribution requires ≥3 audit_ids).** It does not open any audit file. It does not read any tool output. It does not check that the observation text references entities present in the evidence. Calling it "advisory" is being generous — it's purely structural.

### 4. `_score_grounding` — `forensic-mcp/case/manager.py:1593-1671`
Scores STRONG/PARTIAL/WEAK based on whether `forensic-rag-mcp.jsonl`, `windows-triage-mcp.jsonl`, or `opencti-mcp.jsonl` exist and are non-empty in the audit dir. That's it. **It checks IF other MCPs were called during the case, not whether the finding's claims actually appear in those tools' outputs.** The score is informational and the system stages the DRAFT regardless.

### 5. `_reconcile_verification` (report-mcp) — `report-mcp/server.py:618-685`
The "bidirectional report reconciliation" is **post-approval integrity checking**: compares canonical JSON of currently-approved finding against the snapshot stored in the HMAC ledger at approval time. Flags `DESCRIPTION_MISMATCH` if the finding text was modified after approval. **This proves "no tampering since approval" — it does NOT prove "the finding text was ever supported by evidence in the first place."**

### 6. HMAC verification ledger — `Valhuntir/src/vhir_cli/verification.py:38-98`
```python
def compute_hmac(derived_key, description):
    return hmac.new(derived_key, description.encode("utf-8"), hashlib.sha256).hexdigest()
```
Signs `description` (the finding's text snapshot) with a password-derived key. **This is integrity protection on the CLAIM. It is not verification of the claim against evidence.** A perfectly hallucinated finding, once approved, gets a valid HMAC.

### 7. Tool output storage — `sift-mcp/src/sift_mcp/server.py:240-259`, `sift-common/src/sift_common/audit.py:335-341`
- Forensic tools (Zimmerman, Volatility, etc.) DO persist full output to disk as `output_file` / `full_output_path`.
- BUT the audit log only stores `result_summary` — `_summarize()` truncates to `str(result)[:500]` for non-dict/list results.
- So the raw data needed for byte-level verification IS preserved on disk per tool call, but **nothing in the finding pipeline reads it back to verify claim text**.

### 8. IOC regex extraction — `report-mcp/server.py:286-349`
`_extract_all_iocs()` runs regex (IPs, hashes, file paths, domains, SHA256/SHA1/MD5) against `observation + interpretation + description` text — but ONLY to populate the report's IOC index. **It does NOT check those extracted entities appear in the cited audit evidence.** This is the closest existing code to our "entity gate," and the direction is INVERTED: extraction for reporting, not extraction for verification.

### Summary of Q1
Valhuntir's pipeline has eight overlapping gates: schema, audit_id existence, evidence-registry path check, provenance chain, grounding-MCP presence score, HMAC integrity ledger, bidirectional reconciliation, IOC regex extraction. **None of them open the cited tool output and check that the finding's observation text or its extracted entities appear there.** The proposed "Citation gate + Verification gate + Entity gate" is a missing seam in the existing architecture, not a duplicate of any of the eight.

---

## Q2: Academic prior art

**Verdict:** **partially-overlapping** — the *technique* (substring/span verification of LLM claims against retrieved context) has appeared in RAG literature since 2023. The *application* (forensic-tool-execution audit IDs as the citable substrate, with a hard MCP-server-side gate) appears not to have been published.

**Evidence:**

### Closest priors (the technique exists, in RAG land)

1. **CiteCheck — Accurate Citation Faithfulness Detection (Feb 2025, arXiv:2502.10881).** Decomposes answer into atomic claims and checks each against cited passage. Framed as a detection benchmark and dataset, not an architectural gate.

2. **Verifiable Generation with Subsentence-Level Fine-Grained Citations (June 2024, arXiv:2406.06125).** Studies subsentence-level citations for precise localization. Measurement-oriented; doesn't deploy as a runtime hard gate.

3. **RetroLLM — Empowering LLMs to Retrieve Fine-grained Evidence within Generation (Dec 2024, arXiv:2412.11919).** Constrained decoding so generated tokens come from the corpus via hierarchical FM-Index constraint. Token-level constraint, not finding-vs-evidence post-generation verification. Operates at training/decoding time, not as a server-side gate.

4. **Towards Verifiable Text Generation with Symbolic References — SymGen (Nov 2023, arXiv:2311.09188).** LLM interleaves symbolic refs to JSON conditioning data so humans can verify spans. Streamlines human verification — advisory, not auto-gating.

5. **InteGround (Sep 2025, arXiv:2509.16534).** Retrieval+verification PLANNING for integrative grounding. Measures rather than prevents; key finding is "LLMs rationalize using internal knowledge when grounding is incomplete." Helps frame WHY architectural prevention is needed.

6. **Span-Level Hallucination Detection for LLM-Generated Answers (April 2025, arXiv:2504.18639).** Decomposes via Semantic Role Labeling, compares atomic roles against reference. Detection benchmark, not enforcement.

### Closest to our wedge in the agent/tool-use world

7. **Tool Receipts, Not Zero-Knowledge Proofs — NABAOS (March 2026, arXiv:2603.10060).** This is the single strongest prior art and we MUST cite it (and differentiate).
   - What it does: runtime generates HMAC-signed tool execution receipts the LLM cannot forge. Cross-references LLM claims against receipts to detect "fabricated tool references, count misstatements, false absence claims."
   - Detection rates: 94.2% / 87.6% / 91.3%.
   - Crucial gap: NABAOS detects **whether a tool was called and signs its EXECUTION**. It does NOT verify that a claim like "PID 4 SYSTEM ran child process powershell.exe" appears verbatim in the byte range of the tool's stored output. It signs the receipt; it doesn't substring-check the claim against the receipt's content. AND it's framed as post-hoc detection (<15ms verification overhead per response) with epistemic-source classification, not as a hard rejection gate.
   - Differentiation: ours is (a) byte-range substring of the CONTENT, (b) hard architectural reject inside the MCP server before finding is staged, (c) plus an entity gate that catches hallucinated entities (IPs, hashes, paths) even when the claim text doesn't quote evidence verbatim.

### DFIR-specific papers (none propose what we propose)

8. **DFIR-Metric (May 2025, arXiv:2505.19973).** Pure evaluation benchmark — 700 MCQs + 150 CTFs + 500 NIST cases. Introduces Task Understanding Score for near-zero-accuracy models. Measures hallucination, does not prevent it.

9. **CyberSleuth (Aug 2025, arXiv:2508.20643).** Multi-agent blue-team forensics with packet/log parsing sub-agents and CVE attribution. Compares 3 architectures × 6 LLMs. **Does NOT include any architectural anti-hallucination gate** — it acknowledges "long-term reasoning, contextual memory, consistent evidence correlation" as the open problems, then proposes specialization not enforcement.

10. **Digital Forensics in the Age of LLMs (April 2025, arXiv:2504.02963).** Survey paper. Notes LLM hallucination as a limitation of forensic deployment but proposes no architectural solution. Suggests human-in-loop and grounding as direction.

11. **Chances and Challenges of MCP in DFIR (June 2025, arXiv:2506.00274v1).** Surveys MCP for DFIR. Discusses provenance/audit logging as a forensic primitive but does not propose substring-verifying findings against tool output.

### Summary of Q2
The substring-citation-verification technique exists in RAG papers. The HMAC-tool-receipt approach exists in NABAOS. **No paper combines (substring verification + entity extraction + DFIR audit_id substrate + hard server-side rejection inside an MCP server) — and no DFIR paper proposes architectural prevention rather than measurement.** Frame our submission as "we apply known RAG-citation-verification technique to forensic findings, as a server-side architectural gate, extending NABAOS-style receipts from execution-attestation to content-attestation."

---

## Q3: OSS / agentic frameworks

**Verdict:** **partially-overlapping** — substring-validated citations exist as a Pydantic pattern in the Instructor library since 2023. No DFIR / forensic MCP server uses this pattern. No agent framework offers it as a built-in primitive.

**Evidence:**

### Closest direct prior art

1. **Pydantic + Instructor citation validators (Nov 2023, [python.useinstructor.com](https://python.useinstructor.com/blog/2023/11/18/validate-citations/)).** This is the closest implementation-level match to our Citation+Verification gates.
   - Approach: Pydantic `@field_validator` does `if v in text_chunk` substring check on every quoted citation; raises `ValueError` on mismatch → hard rejection at parse time.
   - Same paper also shows an LLM-judge variant for semantic alignment.
   - GitHub: `jxnl/instructor` — ~8k stars, very widely used.
   - Differentiation: Instructor is an SDK/library pattern for generic RAG. Ours is (a) an MCP-server-enforced gate (not optional SDK), (b) over forensic tool-execution audit_ids (not arbitrary text chunks), (c) with NER+regex entity gate layered on top, (d) integrated with HMAC ledger + human-approval workflow.
   - **This is the single most important pattern to cite to STRENGTHEN our pitch.** We're porting a known SDK pattern into a forensic MCP-server architecture, plus adding the entity layer.

### Constrained generation tooling (orthogonal, but often confused)

2. **Outlines (~10k stars), Guidance (~19k), XGrammar (~1k, default for vLLM/SGLang/TensorRT-LLM/MLC-LLM), lm-format-enforcer (~1.5k).** All enforce structural / grammar / regex / JSON-schema constraints during token decoding. **None verifies claim content against retrieved evidence.** They guarantee well-formed JSON, not well-grounded findings. We should explicitly disclaim "this is not just schema-constrained generation" to head off judge confusion.

### DFIR / SOC LLM MCPs (no prior art)

3. **mcp-velociraptor (`mgreen27/mcp-velociraptor`, SOCFortress fork).** Bridge exposing Velociraptor APIs as tools. No finding gate. Authors openly write: "It is not that I don't trust my tools, I must always validate their outputs" — human-validation philosophy, no architectural enforcement.

4. **DFIR-IRIS MCP Server (`dfirmesi-iris-mcp-server`).** 35 functions + KPI metrics over DFIR-IRIS incident response platform. CRUD + natural language. No finding-vs-evidence verification.

5. **`x746b/winforensics-mcp` (KALI Windows forensics MCP), `axdithyaxo/mcp-forensic-toolkit`.** Tool-execution MCPs. No verification gate.

6. **SOCFortress Talon (Apr 2026).** Autonomous SOC analyst, MCP pivots over SIEM, generates structured investigation reports. Anonymizing PII proxy is novel but unrelated. **No claim-vs-tool-output substring verification.**

### Citation-RAG libraries

7. **LlamaIndex citation modules, LangChain `with_citations`, RAGAS, DeepEval.** All produce citations as URL/chunk pointers and / or LLM-judge claim verification. None hard-gate via substring at server side. RAGAS / DeepEval are evaluation frameworks, not enforcement gates.

8. **GitMCP (`idosal/git-mcp`, ~2k stars).** Documentation MCP — claims to "end code hallucinations" by injecting up-to-date repo docs into context. Prevention by improved context, not by verification of claims against context.

9. **DepScope hallucinations dataset (`cuttalo/depscope-hallucinations-dataset`).** Catalog of hallucinated package names + MCP server to block them at install time. Domain-specific dictionary check, not general claim verification.

### AppliedIR ecosystem beyond what we've seen

10. AppliedIR org currently ships: `Valhuntir` (orchestrator), `sift-mcp` (forensic MCPs monorepo), and a separate `opensearch-mcp` (referenced from ARCHITECTURE.md). Spot-check of opensearch-mcp shows evidence-indexing focus, no finding-vs-evidence gating. **No undiscovered AppliedIR repo doing our wedge.**

### Summary of Q3
The Pydantic Instructor pattern is the OSS prior art we cannot ignore. We need to explicitly own that and frame as "MCP-server-enforced port of a known SDK validator pattern, into the DFIR audit_id domain, plus an entity gate that pure-substring validators don't have." No DFIR MCP currently implements anything close.

---

## Q4: Anthropic published patterns

**Verdict:** **building on documented primitive** — Anthropic Citations API (Jan 2025) is the marquee documented primitive for grounded-output verification. It is similar in spirit but operates at the LLM/API layer, not the MCP-server gate layer, and Anthropic does not advertise byte-level guarantees.

**Evidence:**

### Anthropic Citations API ([claude.com/blog/introducing-citations-api](https://claude.com/blog/introducing-citations-api), Jan 2025)
- Mechanism: server-side sentence chunking of source documents; Claude is given chunks; Claude generates output with citation markers pointing at chunks.
- Anthropic's stated guarantee: "trained to resist fabricating sources … more likely to acknowledge uncertainty or decline to cite."
- Anthropic does NOT claim byte-level architectural guarantees — citations are training-aligned, not constraint-enforced. The blog says cited text "will reference source documents to minimize hallucinations." Soft language.
- Available via direct Anthropic API + Vertex AI + Bedrock.

### Differentiation from our wedge
- Citations API does this at the **LLM layer** during generation. We do it at the **MCP server gate layer** at `record_finding()` time.
- Citations API uses **sentence chunks of provided documents** as the citation substrate. We use **forensic tool execution audit_ids of named SIFT tool runs** with byte-range offsets into stored tool output.
- Citations API is **soft (model trained to be faithful)**. We are **hard (server-side substring check; reject on mismatch)**.
- Citations API is **for arbitrary text generation**. We are **for forensic findings + entity-class verification (IPs, hashes, paths, processes, accounts) via NER+regex**.

### MCP `Resources` vs `Tools` patterns
Anthropic's MCP docs note Resources as a separate primitive (passive, read-only context) vs Tools (active operations). We can frame the cited tool-output snapshots as MCP **Resources** the server exposes for verification, while the audit IDs come from Tool calls. This is on-spec MCP usage; nothing in the MCP spec mandates or even hints at substring-verifying tool claims against tool outputs — that's an architectural choice we'd make.

### "Writing effective tools for AI agents" (Anthropic Engineering blog, 2025)
Recommends evaluation-driven tool development, grounding evals in real-world use cases, agent-aided analysis. **No published architectural pattern for "MCP server hard-rejects agent claims that don't substring-match tool output."** The wedge is consistent with Anthropic's design philosophy but is not a documented Anthropic primitive.

### Summary of Q4
Our wedge is consistent with Anthropic's "Citations" direction but goes architecturally further (hard server-side gate, byte-range, entity verification, MCP-layer). We should position as "the MCP-server-enforced extension of the Citations API design philosophy, for the DFIR domain where stakes are subpoena-level." Anthropic's documented primitives strengthen the pitch; they don't preempt it.

---

## Overall verdict

**Net: novel enough to win on Constraint Implementation, but only if framed correctly.**

The wedge has clear prior art in TWO places that we must cite, not hide:
1. **Pydantic+Instructor substring citation validators (Nov 2023)** — same technique, SDK-layer, generic.
2. **NABAOS Tool Receipts (March 2026)** — same anti-hallucination intent, HMAC of execution rather than content, post-hoc detection rather than gate.

What is genuinely net-new in our wedge: **the combination of (a) MCP-server-side hard rejection at `record_finding()`, (b) byte-range cited_spans into named tool-execution audit IDs as the citable substrate, (c) NER+regex entity gate that catches hallucinated IPs/hashes/paths/processes even when the claim text doesn't quote verbatim, (d) deployed inside an existing forensic MCP architecture (Valhuntir / SIFT) whose eight existing gates demonstrably stop one step short of this verification.** That combination, in the DFIR domain, at the MCP-server gate layer, against the SANS judging criteria, has no published or shipped prior.

Pure-novelty framing ("first ever hallucination-impossible findings") will get judges to dismiss the claim or find Pydantic Instructor in 30 seconds and bin the submission. **The strong move is "we apply a known RAG-citation pattern to forensic findings as an MCP-architectural gate, extending NABAOS-style execution receipts to content receipts, layering an entity gate the upstream patterns lack, and proving the resulting architectural barrier to hallucination on a SANS-grade benchmark."**

---

## Differentiation strategy

### What to say in the pitch (own the prior art, sharpen the delta)

1. **Lead with the diagnosis, not the cure.** "Eight gates already in Valhuntir all assume the LLM's text is honest about the evidence it ran. Schema, ID existence, provenance, hash, HMAC, reconciliation, grounding-MCP presence, regex IOC extraction — none of them open a cited tool output and check the claim against its bytes. We add the missing seam."

2. **Cite Pydantic Instructor up front as the closest pattern.** "Substring-validated citations are a known Pydantic pattern for RAG (Instructor, Nov 2023). We port that pattern from SDK-layer to MCP-server-gate layer, with audit_ids replacing arbitrary chunks as the citation substrate, and add an entity gate that catches hallucinated entities the pure-substring pattern misses."

3. **Cite NABAOS as the closest agent-domain pattern.** "NABAOS (March 2026) shows that HMAC-signed tool execution receipts catch 94% of fabricated tool references. We extend the same idea from execution attestation to **content** attestation: not just 'this tool ran' but 'this specific byte range of its output was cited and that exact text appears in the finding's observation.'"

4. **Own one entity-gate primitive that is unambiguously novel.** "Entity gate: extract IPs, SHA256/SHA1/MD5, file paths, registry keys, process names, account names from the finding's observation via regex+NER. For each extracted entity, check it appears somewhere in the cited byte ranges. If not present → entity is structurally hallucinated → finding rejected. This catches the failure mode where the LLM paraphrases the evidence accurately but invents a process name or hash that isn't in the audit trail."

5. **DFIR-grade demo.** Two before/after pairs:
   - **Citation gate caught.** LLM cites audit-id `sift-alice-007`, claims observation contains `PID 4924 powershell.exe ...`. Server loads stored output, substring check fails → REJECTED. Show the rejection log line.
   - **Entity gate caught.** LLM cites real audit-id `sift-alice-012` (a `pslist.txt`), but observation invents IOC IP `185.220.101.45`. Entity extractor pulls the IP from observation; server checks the cited byte ranges; not there → REJECTED. Show the entity diff.

6. **Disclaim what we are NOT.** "This is not constrained decoding (Outlines/XGrammar) — those guarantee JSON shape, not claim grounding. This is not the Anthropic Citations API — that is LLM-trained-faithful, not architecturally enforced. This is not RAGAS/DeepEval — those measure, we reject."

### Judging-criterion framing
Position against **Constraint Implementation** as the lead category: every prior gate measures, advises, or trains the model toward faithfulness. We are the only one that **rejects the LLM's text at architecture time, before it enters the case record**, using existing primitive forensic tool output stored on disk. Judges who care about reproducibility, examiner-time-savings, and audit-trail-integrity score this category hardest in a forensics context.
