# 06 — Hidden-Field Verdict (Lane Saturation)

The "hidden-field check" answers: **which architectural lanes are saturated by existing OSS / Valhuntir / SOC vendors, and which are open?**

Because the Devpost gallery is unpublished, this is built from:
1. Valhuntir's coverage (the explicit bar)
2. Vendor AI-SOC tools (Charlotte / Sentinel / AgentiX / Splunk)
3. OSS prior art (Velociraptor MCPs, Volatility MCP, DFIR-IRIS MCP, Sec-Gemini)
4. Academic prior work (DFIR-Metric, CyberSleuth, etc.)

## Verdict matrix

🟢 GREEN = open lane, credible wedge
🟡 YELLOW = partial coverage, can wedge with careful framing
🔴 RED = saturated, do not enter

### Lane 1: Tool-coverage breadth

| Sub-lane | Verdict | Reasoning |
|---|---|---|
| Single-purpose MCP for one tool (e.g., Volatility-only) | 🟡 | `bornpresident/Volatility-MCP-Server` exists. Not a hackathon winner. |
| Single-platform MCP for SIFT (disk + memory + Windows + network) | 🔴 | Valhuntir's `sift-mcp` has 73-100 tools across 7 backends. Cannot win on coverage. |
| Cross-platform MCP (SIFT + REMnux + Windows VM) | 🟡 | Valhuntir does this (sift-mcp + wintools-mcp + optional remnux-mcp). Coverage match possible but no differentiation. |

**Action:** Do NOT try to win on tool count. 15-25 well-chosen tools that demonstrate a wedge > 100 tools that look like Valhuntir copy.

### Lane 2: Self-correction architecture

| Sub-lane | Verdict | Reasoning |
|---|---|---|
| Prompt-based self-correction ("verify tool success") | 🔴 | Protocol SIFT baseline. Loses Constraint immediately. |
| Per-phase self-correction (re-run if inconsistent) | 🟡 | `marez8505/find-evil` does this. Marginal differentiation. |
| Response-envelope rotating reminders + structural gates | 🔴 | Valhuntir owns this. Can match but not exceed by recopying. |
| **Closed-loop critic→revise subagent** (periodic critic re-reads evidence + findings) | 🟢 | **Not in Valhuntir. Not in marez8505. Not in OSS prior art. THIS IS THE TOP WEDGE.** Maps directly to tiebreaker criterion + Rob T. Lee's quoted complaint. |
| Multi-agent debate ("investigator vs skeptic") | 🟢-🟡 | CyberSleuth paper has 3-agent variants. A debate pattern for finding-validation is novel but harder to land in 13 days. |

**Action:** Build the **closed-loop critic** as the primary wedge. Measure its impact (hallucination rate before/after critic).

### Lane 3: Adversarial-evidence defense

| Sub-lane | Verdict | Reasoning |
|---|---|---|
| Prompt-based "treat all evidence as untrusted" | 🔴 | Valhuntir has the `data_provenance: tool_output_may_contain_untrusted_evidence` marker — already exists |
| HITL as primary defense | 🔴 | Valhuntir says this is its primary defense. Not a wedge to copy. |
| **Structural sanitizer layer** (strip tags / roles / unicode tricks before LLM read) | 🟢 | Not in Valhuntir, not in marez8505, not in OSS. Maps directly to judges Perkal (MCPwn CVE author) + Ernstberger (Kontext). |
| **Separate "untrusted-evidence-reader" agent** (translates raw to structured before investigator sees it) | 🟢 | Same gap. Higher complexity. |

**Action:** Adversarial-evidence sanitizer is the **second wedge**. Cheap to build, big judge resonance.

### Lane 4: Memory forensics

| Sub-lane | Verdict | Reasoning |
|---|---|---|
| Raw Vol3 command exposure via MCP `run_command` | 🔴 | Valhuntir does this through `sift-mcp.run_command`. |
| Plugin-specific MCP tools (just typed wrappers) | 🟡 | `bornpresident/Volatility-MCP-Server` does this. Single-purpose. |
| **Plugin-aware reasoning chain** (`psscan→pslist→diff` for hidden, `malfind→dumpfiles→YARA→capa` for injection, `netscan→cmdline` for C2 attribution) | 🟢 | Not in Valhuntir's sift-mcp. Not in bornpresident's MCP. Demo-friendly because of Rob's Ralph Wiggum Loop Volatility example. |
| Memory-baseline subtraction across cases | 🟢 | Valhuntir's windows-triage-mcp does disk-level baseline (2.6M records). Memory baseline less covered. |

**Action:** A **memory-first investigator** with plugin-aware reasoning could be wedge 3 OR could replace wedge 2 depending on team strength. It's especially demo-friendly.

### Lane 5: Live-host triage

| Sub-lane | Verdict | Reasoning |
|---|---|---|
| Raw Velociraptor VQL via MCP | 🟡 | `socfortress/velociraptor-mcp-server` (39 stars) and `mgreen27/mcp-velociraptor` exist. Do NOT duplicate. |
| **Agentic layer above Velociraptor MCP** (VQL plan generation, result interpretation, pivot routing) | 🟢 | The agentic layer above the raw VQL wrapper is open. Valhuntir is post-mortem-only. |
| EDR-tool MCP integration (CrowdStrike Falcon, SentinelOne, Defender) | 🔴 | Vendor SOC tools dominate this space. Stay away. |

**Action:** Live-host triage is **optional wedge 4** if you have a Velociraptor lab. Skip if not.

### Lane 6: Threat intelligence / Sigma / MITRE ATT&CK enrichment

| Sub-lane | Verdict | Reasoning |
|---|---|---|
| Sigma rule auto-application post-EVTX ingest | 🔴 | Valhuntir's opensearch-mcp does this with Hayabusa (3,700+ rules). |
| Threat intel via OpenCTI MCP | 🔴 | Valhuntir's opencti-mcp does this. |
| MITRE ATT&CK tagging on findings | 🔴 | Valhuntir does this — `mitre_ids: ["T1021.002", "T1543.003"]` in finding schema. Required as table-stakes, not a wedge. |
| **YARA-rule auto-generation from observed IOCs** + in-process testing | 🟢 | Not in Valhuntir. Generates rules for the case-specific threat. |
| **Custom Sigma rule generation** from observed patterns | 🟢 | Not in Valhuntir. Same shape as YARA-gen but for log events. |

**Action:** Skip the saturated lanes. YARA / Sigma auto-generation is a *minor* wedge (interesting demo, low judging weight).

### Lane 7: Case management / multi-examiner workflow

| Sub-lane | Verdict | Reasoning |
|---|---|---|
| Case lifecycle CLI | 🔴 | Valhuntir has 24 vhir CLI commands |
| HMAC-signed examiner approval | 🔴 | Valhuntir's L2 layer |
| Multi-examiner ID prefix collision-free | 🔴 | Valhuntir does this (`F-alice-001`) |
| DFIR-IRIS-style case mgmt | 🟡 | `DFIR-IRIS MCP server` (35 functions) exists. Overlaps Valhuntir. |
| Real-time investigation HUD with streaming agent traces | 🟢 | Valhuntir's Examiner Portal is static HTML/JS. A live HUD would be a much better demo. |

**Action:** Skip case mgmt. Real-time HUD is a **demo upgrade**, not a primary wedge.

### Lane 8: Reporting / output

| Sub-lane | Verdict | Reasoning |
|---|---|---|
| Multi-profile reports (full / executive / timeline / IOC) | 🔴 | Valhuntir has 6 profiles. |
| MITRE ATT&CK narrative skeleton | 🔴 | Required, not a wedge. |
| **Court-admissibility annotation** (each finding gets a "would this survive cross-examination?" rating) | 🟢-🟡 | Not in Valhuntir. Maps directly to Ovie Carroll + Cheri Carr + Amanda Rankhorn (judges). Cheap addition. |
| **Adversary-attribution synthesis** (named threat actor likely based on TTPs) | 🟢-🟡 | Maps to Adam Nasreldin (Mandiant judge). |

**Action:** Add court-admissibility annotation as a **small flavor wedge**. Easy to ship. Maps to 3+ judges' worldviews.

### Lane 9: Benchmarking / measurement

| Sub-lane | Verdict | Reasoning |
|---|---|---|
| **Hallucination-rate harness against public answer keys** (Nitroba + NIST Data Leakage + NIST Hacking Case) | 🟢 | Not in Valhuntir. Not in OSS. DFIR-Metric paper exists but academic-only. **THIS IS A MAJOR WEDGE for IR Accuracy criterion.** |
| Time-to-finding benchmark | 🟢 | Rob T. Lee set the 14:27 anchor. A submission that reports a number (anchored vs anchored-faster) is the only way to score on the "speed" rhetoric. |
| Cross-evidence corroboration metric | 🟢-🟡 | Not standardized. Defining the metric IS the wedge. |

**Action:** Hallucination harness is **non-negotiable**. Build it.

### Lane 10: Platform footprint / deployability

| Sub-lane | Verdict | Reasoning |
|---|---|---|
| Heavy SIFT VM-resident (16-32 GB RAM, full OpenSearch) | 🔴 | Valhuntir. |
| Lightweight CLI-only on laptop | 🟢-🟡 | Easy wedge but low scoring leverage (only Usability). |
| Containerized (Docker) reproducible install | 🟢 | Valhuntir is SIFT-VM-shaped. A clean Docker compose would help Usability. |

**Action:** Ship a Docker compose for reproducible install. Don't over-invest in "lite mode" unless it's free.

## Composite recommendation (the synthesized wedge stack)

A submission that hits all of these is positioned to win:

| # | Wedge | Lane | Effort | Scoring impact |
|---|---|---|---|---|
| 1 | **Closed-loop critic→revise subagent** | Self-correction (Lane 2) | High (3-5 days) | ⭐⭐⭐ Autonomous Execution (tiebreaker), IR Accuracy |
| 2 | **Measured hallucination-reduction harness** (NIST cases + Nitroba) | Benchmarking (Lane 9) | Medium (2-3 days) | ⭐⭐⭐ IR Accuracy |
| 3 | **Adversarial-evidence sanitizer layer** | Constraint (Lane 3) | Low (1-2 days) | ⭐⭐ Constraint Implementation, judge resonance |
| 4 | **Memory-first Volatility-plugin-aware investigator** | Memory (Lane 4) | Medium (2-3 days) | ⭐⭐ Breadth+Depth, demo material |
| 5 | **Court-admissibility annotation per finding** | Reporting (Lane 8) | Low (0.5 day) | ⭐ Judge resonance (Ovie/Cheri/Amanda) |
| 6 | **Real-time investigation HUD** (streaming agent traces) | Case mgmt (Lane 7) | Medium (2-3 days) | ⭐⭐ Demo polish, Usability |
| 7 | **Docker compose reproducible install** | Deploy (Lane 10) | Low (0.5 day) | ⭐ Usability |

Total upper-bound: ~12-15 days. We have ~13 days to submit. **Trim wedges 4 and 6 if time gets tight.** Wedges 1, 2, 3, 5, 7 are non-negotiable for a winning submission.

## Hard rules from the hidden-field analysis

1. **Do not try to win on tool count.** Valhuntir's 100 tools is unmatchable in 13 days.
2. **Use Custom MCP Server architecture.** Direct Extension loses Constraint, costs the round.
3. **Build the closed-loop critic.** This is the differentiator. Don't omit it.
4. **Build the hallucination harness.** The accuracy report becomes the killer artifact.
5. **Steal Valhuntir's response envelope + finding schema verbatim.** It's the right floor; copy it.
6. **Match SIFT/MCP integration; don't try to replace SIFT.** Stay in the lane the rules define.
