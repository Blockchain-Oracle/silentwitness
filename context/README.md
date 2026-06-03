# context/ — Domain Knowledge Base

> **Read this first if you are a downstream agent.**
> This folder is pure domain knowledge for the Find Evil! / Protocol SIFT 2026 hackathon.
> It does NOT prescribe architecture. It teaches what is true about the domain so that you can design well.

---

## The wedge we are designing for (one paragraph)

We are building **SilentWitness** — a hypothesis-first IR investigator that drafts its own structured incident report as the case unfolds, with every claim verifiably linked to the tool execution that produced it. The user is the senior IR consultant who currently spends ~half their billable time running tools by hand and writing the report afterward. The headline metric is **time to handoff-ready incident report** on a representative forensic case. Full wedge commitment in `../STRATEGY.md`.

## What this folder gives you (and what it does not)

**It DOES give you:**
- Deep DFIR domain knowledge (what investigators actually do, every Windows artifact, every tool, every attack pattern, anti-forensics catalog)
- The user's actual reality (a day in the life of an IR consultant, typical engagements, what their reports look like)
- The technical substrate (Model Context Protocol, Claude Agent SDK, LLM failure modes in agentic systems)
- The competitive context (reference implementations decomposed)
- The judging context (judge personas, SANS curriculum, legal landscape)
- The evaluation context (validation datasets, ground truth, scoring methodology)
- Primary source material (Rob T. Lee corpus, Steve Anson corpus, GTG-1002, key academic papers)

**It DOES NOT give you:**
- Architectural prescriptions ("use MCP," "use a critic agent," "build N layers")
- Implementation choices ("use Pydantic," "use Postgres," "use FastMCP")
- Step-by-step build plans
- Anything that pre-decides how you should design the system

Those decisions are YOURS to make in the design phase, informed by what you read here.

## Why we separated knowledge from prescription

Earlier strategy documents in this project (see `../STRATEGY-v1.md`) prescribed an architecture — typed MCP server, three-layer Investigation Record, HMAC-signed approval ledger, etc. Abu pointed out (correctly) that pre-deciding architecture defeats the purpose of the design phase. The right shape of this project is:

1. **Wedge committed** → `../STRATEGY.md` (problem + user + headline metric)
2. **Domain knowledge built** → `context/` (this folder; pure facts)
3. **Design phase happens** → produces SPEC.md (this is where architecture decisions get made, by humans + design-phase agents, informed by `context/`)
4. **Implementation phase** → builds against SPEC.md

You are most likely an agent in phase 3 or 4. Use this folder accordingly. If you find yourself wanting to know something the folder doesn't cover, surface that — don't fabricate.

## Folder map (with actual sizes)

| Path | Words | Filesize | Role |
|---|---|---|---|
| `README.md` | — | this file | Entry point |
| `COMPLETENESS.md` | — | ~10K | Coverage matrix, gaps, inconsistencies, cross-refs, quality stamps for downstream agents |
| `domain/01-dfir-foundations.md` | 15,563 | 108K | IR phases, mental models, vocabulary |
| `domain/02-windows-artifacts-encyclopedia.md` | 32,859 | 238K | Every Windows forensic artifact, what it means, gotchas |
| `domain/03-memory-forensics-deep.md` | 17,729 | 127K | Volatility 3, plugins, common failure modes |
| `domain/04-disk-network-log-forensics-deep.md` | 20,599 | 143K | NTFS internals, plaso, pcap, Windows event IDs, Sysmon |
| `domain/05-anti-forensics-and-attack-patterns.md` | 20,641 | 154K | Anti-forensics catalog + real-world attack playbooks + MITRE |
| `domain/06-sift-toolchain-deep.md` | 25,110 | 192K | Every important SIFT tool, deep usage reference |
| `technical/07-mcp-and-agent-platforms.md` | 14,160 | 112K | MCP protocol, Python SDK, Claude Agent SDK at the protocol level |
| `technical/08-llm-failure-modes-in-agentic-systems.md` | 14,093 | 95K | Context rot, prompt injection, hallucination taxonomy |
| `user/09-ir-consultant-reality.md` | 17,177 | 117K | Persona, day-in-the-life, engagement flow, report anatomy |
| `evaluation/10-datasets-and-evaluation-methodology.md` | 16,060 | 113K | Every validation dataset deeply, scoring approaches, baselines |
| `competitive/11-reference-implementations-decomposed.md` | 19,863 | 144K | Valhuntir, Protocol SIFT, every visible competitor decomposed |
| `stakeholders/12-judges-curriculum-and-legal-landscape.md` | 15,688 | 120K | Judge personas, SANS curriculum, FRE 707 + Daubert |
| `reference/13-source-corpus.md` | 11,510 | 89K | Raw primary source quotations |
| **TOTAL** | **241,052** | ~1.85 MB | |

## What each document actually contains

**`01-dfir-foundations.md` — 15.6K words.** The mental-model layer. NIST SP 800-61 / SANS PICERL / ENISA / ISO 27035 lifecycle comparison, triage as a discipline (kitchen-sink vs hypothesis-driven), the senior-analyst mental model (hypothesis-driven, multi-artifact corroboration, timeline-as-spine, known-good baseline, threat-intel grounding, pivot discipline), order of volatility (RFC 3227), the SANS "Hunt Evil" doctrine (canonical Windows boot/login process tree), the Pyramid of Pain, multi-artifact corroboration patterns per claim type, operational chain of custody, a sketched DFIR analyst's day, and a 200+ term vocabulary glossary.

**`02-windows-artifacts-encyclopedia.md` — 32.9K words (the biggest doc).** Per-artifact reference: `$MFT`, `$LogFile`, `$UsnJrnl:$J`, NTFS metadata files, VSS, Prefetch, ShimCache / AppCompatCache, Amcache, BAM/DAM, SRUM, every registry hive, Run keys (autoruns taxonomy), Services, Scheduled Tasks, WMI persistence, Sysmon, Security/System/PowerShell/RDP/Defender event logs, ConsoleHost_history, ShellBags, LNK + Jump Lists, Recycle Bin, browser artifacts, MUICache + UserAssist, USB device chain, pagefile/hiberfil/swapfile, ESE databases, ADS + Zone.Identifier, wpndatabase, ActivitiesCache. Closes with 20 cross-artifact corroboration patterns ("Pattern: persistence + execution + network exfil"). Per artifact: what it IS, what it RECORDS, FORMAT, retention behavior, parsers, canonical insight, gotchas, anti-forensics interactions.

**`03-memory-forensics-deep.md` — 17.7K words.** Why memory matters (order of volatility, what lives only in RAM). Acquisition: WinPMEM, MRC, DumpIt, MS Crash Dump, hibernation file, VM snapshot files, LiME/AVML on Linux, pitfalls. Image formats: raw, AFF4, LiME, ELF core, .dmp, VMEM, E01. Volatility 3 architecture (layered abstraction, symbol cache, automagic, contexts, translation layers, plugins, volshell). Vol2 vs Vol3. ISF symbol cache mechanics (the load-bearing piece for the "Ralph Wiggum Loop" demo Rob T. Lee shows). Per-plugin catalog for Windows (~40 plugins), Linux, Mac, then Linux memory specifics including container memory.

**`04-disk-network-log-forensics-deep.md` — 20.6K words.** Three parts. **Part A — Disk:** NTFS internals (clusters, MFT, resident/non-resident attrs, compression, sparse), slack types, `$LogFile` mechanics, USN Journal, VSS, plaso/log2timeline architecture, Sleuth Kit family (mmls, fls, icat, istat, ils, tsk_recover, fcat, blk*), EWF/E01, imaging tools, ext4/HFS+/APFS basics, FAT32 brief, file carving theory, encrypted volumes (BitLocker, VeraCrypt, FileVault, LUKS), the hibernation-file-as-crypto-bypass move. **Part B — Network:** pcap, tshark, Zeek, Suricata, JA3, RITA, beacon detection, DNS exfil, C2 patterns. **Part C — Logs:** Windows Event Log architecture, full EID catalog, Sysmon reference, Hayabusa, Chainsaw, Sigma.

**`05-anti-forensics-and-attack-patterns.md` — 20.6K words.** Part A: 35 anti-forensics techniques (timestomping, log clearing/filtering, ADS, LOLBins by binary, process hollowing/doppelgänging/herpaderping/atom-bombing/APC injection/reflective DLL/process hopping, AppInit_DLLs / IFEO debugger, DLL search-order hijacking, COM hijacking, BYOVD, PsExec residue, encrypted containers, wipe tools, VSS deletion, Defender disable, EDR unhooking, MAC-time attacks, Sysmon EID 25 tampering, WMI persistence, hidden scheduled tasks, UEFI persistence, Defender exclusion abuse, PowerShell/AMSI bypass, fileless, Kerberos abuse (Golden/Silver/Kerberoasting/AS-REP), account-log obfuscation, time manipulation). Each has mechanism, motive, detection signals, residue that remains. Part B: 20 real-world attack playbooks (ransomware kill chain, APT29, APT41, Lazarus, FIN7, insider exfil, BEC, supply chain, LotL lateral, cloud-native incl Azure/Entra/AWS/GCP). Part C: MITRE ATT&CK subset for host forensics, all 12 tactics with key techniques.

**`06-sift-toolchain-deep.md` — 25.1K words.** Tool-by-tool reference for the SANS SIFT Workstation. Memory acquisition + Volatility 2/3, MemProcFS, hibr2bin, WinPMEM, LiME, AVML. Disk acquisition (ewfacquire/ewfmount, dc3dd, dcfldd, ddrescue, xmount, imagemounter), libvshadow, libbde, libfvde, libluksde. Sleuth Kit family + mactime. plaso family (log2timeline, psort, psteal, pinfo, image_export, dftimewolf). Eric Zimmerman tools (MFTECmd, EvtxECmd, AmcacheParser, AppCompatCacheParser, PECmd, RECmd, RBCmd, SBECmd, LECmd, JLECmd, SrumECmd, SQLECmd, bstrings, WxTCmd, Timeline Explorer). Registry analysis (RegRipper3.0, Registry Explorer, python-registry). EVTX analysis (Hayabusa, Chainsaw, evtxtract, python-evtx). YARA, capa, FLOSS, ssdeep, TLSH. Carving (bulk_extractor, foremost, scalpel, photorec, binwalk, lightgrep). Network (Wireshark, tshark, tcpdump, Zeek, Suricata, NetworkMiner, RITA, argus). Malware triage. KAPE, Velociraptor, UAC. Anti-forensics detection. Closes with 6 canonical tool chains (disk super-timeline, memory triage, network triage, EVTX rapid-hunt, PE/malware triage, registry triage), a section "what is missing on stock SIFT," and an output-format reference (l2tcsv, plaso JSON, EZ tools CSV columns, Zeek/Suricata/Hayabusa schema).

**`07-mcp-and-agent-platforms.md` — 14.2K words.** MCP spec at protocol level (revision tracked: 2025-11-25). Part A: history/motivation, client/server/host model, transports (stdio, Streamable HTTP, SSE legacy), JSON-RPC 2.0 layer, lifecycle, capabilities exchange, the three primitives (Tools, Resources, Prompts), Sampling/Roots/Logging/Progress/Cancellation/Completions/Elicitation/Tasks, auth/authz, security model and trust boundaries, MCP CVEs (CVE-2026-33032 "MCPwn," OWASP MCP Top 10 2026). Part B: Python SDK (FastMCP high-level, low-level Server API, testing utilities, Client, in-process SDK MCP server), TypeScript SDK, other languages. Part C: Claude Agent SDK (renaming history, primitives, built-in tools, custom tools via in-process MCP, mcp_servers, hooks, subagents, permission system, context management/compaction, agent loop internals, message type surface, skills/slash commands, cost model effective Jun 15 2026, output streaming, multi-turn vs single-turn, Stop hook). Part D: Claude Code as host (CLAUDE.md, settings.json, .claude/ layout, skills, permission modes, sandbox). Part E: alternatives (OpenClaw, LangGraph, CrewAI, AutoGen, Aider/Cline/Cursor/Windsurf). Part F: 8 glue/composition patterns. Appendix of quick reference cards.

**`08-llm-failure-modes-in-agentic-systems.md` — 14.1K words.** Hallucination taxonomy (contested term, intrinsic vs extrinsic, faithfulness vs factuality, closed- vs open-domain, tool-use-specific, DFIR-specific shapes, self-consistency vs ground-truth, the "models rationalize using internal knowledge when grounding is incomplete" finding). Context rot / long-context degradation (U-shape, needle-in-haystack criticisms, where in context forensic work fails). Prompt injection (direct, indirect, zero-click, DFIR-specific vectors, delimiters, Unicode tricks, benchmarks, recent attacks). Tool poisoning (adversarial defs, rug pulls, naming collisions, output bombs, MCPwn). MCP-specific vulnerabilities. Sycophancy + reward hacking + sandbagging + spec gaming + mode collapse. Confidence miscalibration. Jailbreak resistance and erosion. Agentic loop failures (infinite loops, premature termination, the rabbit hole, tool-call thrashing, composition failure, planning failure, state-tracking failure, recovery failure, goal drift). DFIR-specific LLM-in-tool-loop failures (hallucinated file paths/hashes/flags, misreading tool output, over-confident attribution, etc.). Cost/latency failure modes. 2024–2026 academic findings catalog. Failure mode interaction matrix.

**`09-ir-consultant-reality.md` — 17.2K words.** Part A: persona (who they are, where they work, their day, tools, billing model, reading material, what they hate/love, senior/junior dynamic, retainer-customer expectations). Part B: hour-by-hour engagement flow (Hour 0–1 triage call → Hour 28–40 detailed final report → Hour 40+ remediation handoff), with "where AI helps most per phase." Part C: engagement variants beyond ransomware (insider exfil, BEC, APT/nation-state, compliance/e-discovery, supply chain, cloud-native). Part D: incident response reports — the 5 audiences, universal report sections, real template breakdowns, common failure modes, the handoff moment, three artifacts at three stages, where AI fits today, IOC export, threat intel handoff. Part E: stakeholder communication patterns (CIO/CISO, legal/GC, insurance, regulatory, customer/public). Part F: validation from practitioner voices — report-writing pain, command-line stenography pain, what they wish AI did, what they distrust, senior voice quotes, r/computerforensics sentiment, misconceptions, what they say in private, the wedge in the practitioner's own words.

**`10-datasets-and-evaluation-methodology.md` — 16.1K words.** Part A: 25 validation dataset deep dives (Nitroba, NIST CFReDS Data Leakage + Hacking Case / "Mr. Evil", Ali Hadi cases 1/7/9, DFRWS 2008/2011/2018/2019/2020/2021/2023, M57-Jean, M57-Patents, Volatility Cridex + Volatility Foundation samples, CFReDS Russian Tea Room + Rhino Hunt, PoliceCTF, NSRL, MITRE forensic datasets, Magnet samples, TraceLabs OSINT, Belkasoft samples, Hacking Lab, VxUnderground/MalwareBazaar/VirusShare). Per-dataset: scenario, materials, expected investigation path, ground-truth availability, LLM memorization risk, anti-forensics elements. Part B: VIGIA — the unverified ground-truth reference (status: not publicly located as of 2026-06-02; implications spelled out). Part C: evaluation methodologies (DFIR-Metric, CyberSleuth, "Digital Forensics in the Age of LLMs", NIST SP 800-53/218 overlay, Daubert considerations, FRE 707). Part D: hallucination/accuracy metric families (precision/recall/F1, hallucination rate variants, faithfulness vs factuality, calibration, epistemic-honesty abstention, citation accuracy, FActScore/CiteCheck atomic-claim decomp, span-level grounding, NABAOS tool-call accuracy). Part E: baseline establishment (what counts as baseline, variables to hold constant, run-to-run variance, cross-system comparison, negative controls). Part F: public answer key sources. Part G: 13 common evaluation pitfalls.

**`11-reference-implementations-decomposed.md` — 19.9K words.** Section 1: `teamdfir/protocol-sift` (the baseline) — 10-file config bundle, design choices, audit/logging story, what it doesn't do. Section 2: `AppliedIR/Valhuntir` + `sift-mcp` + `wintools-mcp` + `opensearch-mcp` — full architecture decomposition (3 layers, 9 backends), the 9 defense layers with code refs, 41 deny rules, hook architecture (Pre/PostToolUse + UserPromptSubmit), `forensic-mcp.record_finding` gate logic, forensic-knowledge enrichment, 22K-record RAG KB, 2.6M-record windows-triage baseline, Hayabusa 3,700+ Sigma rules, Examiner Portal (8 tabs), finding schema, 24 vhir CLI commands, JSONL audit trail per backend, bidirectional report reconciliation, the HMAC-SHA256 + PBKDF2-600K iteration ledger (load-bearing for any "defensible audit trail" discussion). Section 3: `marez8505/find-evil` solo competitor. Section 4: 20+ other competitor builds with one-paragraph decomps (VALKYRIE, foveal-dfir, GLAIVE, Verdict, find-evil-sleuth, provenance, sift-bench, SIFTGuard, MemoryHound, W.A.R.V.I.S., EvidenceChain, ThreatPipe v2, Aura-Forensics, Forenly, tracelock find-evil, find-evil-jarvis, Lona44, vigia-cases, sift-sentinel, MuneebX65, samaritan0, etc.). Section 5: existing forensic MCP servers not from this hackathon (Volatility-MCP, velociraptor-mcp, DFIR-IRIS MCP, winforensics-mcp, GitMCP). Section 6: vendor AI SOC products (Charlotte AI, Security Copilot + Sentinel MCP, Cortex AgentiX/XSIAM, Splunk ES 8.2, Cyber Triage, Magnet AI, Cellebrite Pathfinder, Belkasoft BelkaGPT, Talon, Talion). Section 7: adjacent OSS LLM-DFIR (Timesketch+Sec-Gemini, SocTalk). Section 8: anti-hallucination patterns from outside DFIR (Pydantic+Instructor, NABAOS, GitMCP, Anthropic Citations API). Closing: observable patterns across the field (3+ implementations, notable singletons, vendor overlap, where field has and hasn't converged, where there is a published gap nobody is filling).

**`12-judges-curriculum-and-legal-landscape.md` — 15.7K words.** Part A: judge personas — 20 deep dives (Rob T. Lee, Ovie Carroll, Adam Nasreldin, Cheri Carr, Steve Cobb, Jens Ernstberger, Yotam Perkal, Brad Edwards, Steve Anson, Amanda Rankhorn, John Wilson, Mathieu Alcaina, Joshua McCray, Brett Cumming, Stephen Coston, Preston Fitzgerald, Khushi Gupta, Sneha Parmar, Maximilian Gutowski) plus a thumbnail of the remaining ~28 + synthesis of judge psychology. Part B: SANS DFIR curriculum (FOR500 → GCFE, FOR508 → GCFA, FOR509 cloud, FOR526 memory, FOR572 network, FOR578 CTI → GCTI, FOR610 RE, FOR710 advanced RE), plus the "SANS way" six-bullet doctrine. Part C: legal landscape — FRE 702 + Daubert (2023 amendment), Frye, FRE 707 status (PROPOSED as of June 2026; earliest likely effective Dec 1 2026 — this section explicitly corrects the "Dec 2024" date stated elsewhere), state variations, chain of custody, best evidence rule, hearsay, expert witness qualification, AI evidence in TAR civil discovery, notable early AI evidence cases 2024–2026, EU framework (GDPR + AI Act), sector-specific overlays, stipulations vs contested, the black-box/explainability problem, audit trail requirements as anticipated by FRE 707. Part D: cross-cutting observations — SANS faculty positions 2024–2026, practitioner discourse the panel reads, the implicit hypothesis-pivot mental model, Volatility plugin family depth (because Rob's canonical demo lives here), cross-examination playbook against AI-generated forensic findings, provenance markers.

**`13-source-corpus.md` — 11.5K words.** Pure quotation reference, no commentary. Part A: Rob T. Lee corpus (Substack posts, SANS blog, press release, [un]prompted YouTube transcript, X posts, SANS course pages). Part B: Steve Anson / Valhuntir corpus (README, architecture.md, security.md, getting-started.md, Clear Disclosure verbatim, SANS profile, his two books). Part C: GTG-1002 Anthropic disclosure + press coverage. Part D: other industry reports (CrowdStrike GTR, Mandiant M-Trends, Verizon DBIR, Microsoft Digital Defense, MIT ALFA-Chains, Horizon3 NodeZero, Anthropic engineering blog). Part E: academic paper abstracts + key findings (DFIR-Metric, CyberSleuth, Digital Forensics in the Age of LLMs, MCP-in-DFIR, multi-agent IR, NABAOS, CiteCheck, RetroLLM, span-level hallucination detection, SymGen, InteGround, sub-sentence citations, Lost in the Middle, Sharma sycophancy). Part F: MCP spec excerpts. Part G: Pydantic Instructor + NABAOS recap. Part H: hackathon official material. Part I: notable practitioner voices.

## Where to find specific things

**DFIR concepts and mental models**
- IR lifecycle (NIST/SANS/ENISA/ISO) → 01 §2
- Hypothesis-driven investigation → 01 §4, §8
- Order of volatility (RFC 3227) → 01 §5, 03 §1.1
- SANS "Hunt Evil" doctrine + canonical Windows process tree → 01 §6
- Pyramid of Pain → 01 §7, 05 Part C closing
- Multi-artifact corroboration patterns → 01 §9, 02 §34 (different angle)
- Chain of custody (operational) → 01 §10; (legal) → 12 C6, C16

**Windows forensic artifacts**
- What does artifact X mean? → 02, indexed by artifact name
- $MFT internals → 02 §1, 04 Part A §1
- $LogFile + $UsnJrnl → 02 §2-3, 04 Part A §3-4
- VSS → 02 §5, 04 Part A §5, 06 §2.6 (libvshadow)
- Prefetch + ShimCache + Amcache → 02 §6-8
- Registry hives → 02 §11-15, 06 §6 (parsers)
- Sysmon + Event Logs → 02 §16-21, 04 Part C
- PowerShell evidence → 02 §19, §22

**Memory forensics**
- Acquisition options → 03 §2
- Volatility 3 architecture → 03 §4
- Symbol cache (the "Ralph Wiggum Loop" piece) → 03 §6
- Per-plugin catalog (windows.*, linux.*, mac.*) → 03 §7+
- Linux memory specifics → 03 §18
- Volatility tooling on SIFT → 06 §1

**Disk / network / logs**
- NTFS internals → 04 Part A §1; slack → 04 Part A §2
- plaso super-timeline → 04 Part A §6, 06 §4
- Sleuth Kit → 04 Part A §7, 06 §3
- File carving → 04 Part A §13, 06 §9
- Encrypted volumes → 04 Part A §14
- Network forensics tools → 04 Part B, 06 §10
- Windows Event Log architecture + full EID catalog → 04 Part C
- Sigma rules, Hayabusa, Chainsaw → 04 Part C, 06 §7

**Anti-forensics and adversary patterns**
- Per-technique catalog (35 techniques) → 05 Part A
- LOLBins by binary → 05 Part A §5
- Process injection family → 05 Part A §6–§12
- Kerberos abuse → 05 Part A §32
- Real-world kill chains (ransomware, APT29, APT41, Lazarus, FIN7, etc.) → 05 Part B
- MITRE ATT&CK subset for host forensics → 05 Part C
- Cloud-native attacks (Azure/Entra, AWS, GCP) → 05 Part B §10

**SIFT toolchain (every tool that ships with SIFT)**
- Tool-by-tool deep reference → 06
- Canonical tool chains (super-timeline, memory triage, network triage, EVTX hunt, PE triage, registry triage) → 06 §15
- What is missing on stock SIFT → 06 §16
- Output format reference (l2tcsv, plaso JSON, EZ CSV columns, Zeek/Suricata/Hayabusa) → 06 §20

**MCP and Claude Agent SDK**
- MCP protocol facts → 07 Part A
- Python SDK / FastMCP → 07 Part B
- Claude Agent SDK → 07 Part C
- Claude Code as host → 07 Part D
- Alternative frameworks (OpenClaw, LangGraph, CrewAI, AutoGen, Aider, Cline, Cursor) → 07 Part E
- Composition patterns → 07 Part F
- MCP CVEs (MCPwn, OWASP MCP Top 10) → 07 A12

**LLM failure modes**
- Hallucination taxonomy → 08 §1
- Context rot → 08 §2
- Prompt injection → 08 §3
- Tool poisoning + MCP vulnerabilities → 08 §4–§5
- Sycophancy, reward hacking → 08 §6
- Confidence miscalibration → 08 §7
- Agentic loop failures → 08 §9
- DFIR-specific LLM failures → 08 §10
- Cost/latency failures → 08 §11

**IR consultant reality**
- Persona (who, how they bill, what they read, what they hate) → 09 Part A
- Hour-by-hour engagement → 09 Part B
- Beyond ransomware (insider, BEC, APT, e-discovery, supply chain, cloud) → 09 Part C
- Report anatomy + 5 audiences → 09 Part D
- Stakeholder communication → 09 Part E
- Practitioner voices + the wedge in their own words → 09 Part F

**Datasets and evaluation**
- Every public DFIR dataset deeply → 10 Part A
- VIGIA status (the hackathon's named-but-not-publicly-located ground truth) → 10 Part B
- AI-DFIR evaluation papers (DFIR-Metric, CyberSleuth, etc.) → 10 Part C
- Metric families (faithfulness, calibration, citation, abstention) → 10 Part D
- Baseline establishment + run-to-run variance → 10 Part E
- 13 evaluation pitfalls → 10 Part G

**Competitive landscape**
- Protocol SIFT baseline decomposed → 11 §1
- Valhuntir 9-layer architecture + HMAC ledger detail → 11 §2
- 20+ hackathon competitor builds → 11 §3–§4
- Existing non-hackathon DFIR MCP servers → 11 §5
- Vendor "AI SOC" products (Charlotte AI, Security Copilot, Cortex AgentiX, etc.) → 11 §6
- Anti-hallucination patterns from outside DFIR (Pydantic+Instructor, NABAOS, GitMCP) → 11 §8
- Observable patterns across the field + gaps nobody fills → 11 Closing

**Judges, curriculum, legal**
- Per-judge personas → 12 Part A
- SANS DFIR curriculum (FOR500/508/509/526/572/578/610/710) → 12 Part B
- FRE 702 + Daubert (2023 amendment) → 12 C2
- FRE 707 (proposed, status as of 2026-06-02 — see inconsistency note in COMPLETENESS.md) → 12 C4
- Chain of custody (legal) → 12 C6
- Best evidence rule, hearsay → 12 C7, C8
- EU framework (GDPR + AI Act) → 12 C12
- Cross-examination playbook against AI findings → 12 D6

**Primary sources**
- Rob T. Lee quotations → 13 Part A
- Steve Anson / Valhuntir quotations → 13 Part B
- GTG-1002 Anthropic disclosure → 13 Part C
- Industry threat reports → 13 Part D
- Academic paper abstracts → 13 Part E
- MCP spec excerpts → 13 Part F
- Hackathon official material → 13 Part H

## How to read this folder

If you only have time for one file: **`domain/01-dfir-foundations.md`** — it gives you the mental models DFIR people use, so everything else makes sense.

Recommended first-read order for a fresh design-phase agent: see the closing paragraph of `COMPLETENESS.md`.

## Provenance

These documents were produced by 13 parallel research subagents on 2026-06-02 from public web sources, official documentation, academic papers, and source code reads (Valhuntir, Protocol SIFT, MCP SDK, etc.). Citations are inline with URLs where possible. Raw subagent dumps are in `*/.raw/` if you need to trace a claim back to its source.

A synthesis pass on the same day reviewed the corpus for gaps, inconsistencies, and cross-references — output at `COMPLETENESS.md`.

## The earlier `research/` folder

There is also a `research/protocol-sift-2026/` folder with the validation work that LED to the wedge commitment (judge profiles, dataset deep-dives, novelty checks, user-pain validation, builder-discourse scans). That folder is the **provenance trail for the wedge decision**. This `context/` folder is the **domain knowledge for the build**. They serve different purposes.

## A meta-rule for downstream agents

When you encounter a claim in this folder that needs to inform an architecture decision: trust the FACT and own the DECISION. Don't ask "what does the context say I should build?" Ask "given what's true about this domain, what's the right architecture?"
