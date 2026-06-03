# COMPLETENESS.md — Coverage Matrix, Gaps, and Quality Stamps

> Synthesis-pass review of `context/` for downstream design-phase and implementation-phase agents.
> Written on 2026-06-02, the same day the 13 domain docs were produced.
> This file does NOT prescribe architecture. It tells you what knowledge IS in `context/`, what is NOT, and where to look.

---

## How to use this file

If you are a fresh design-phase agent, read in this order:
1. `STRATEGY.md` (one page — the wedge)
2. `context/README.md` (the topical map)
3. The "Downstream readiness verdict" at the bottom of THIS file (the read-paths)
4. The doc(s) the read-path tells you to open
5. Come back here only when you need to verify coverage of a specific question

If you find a question is NOT answered in `context/`, the "Identified gaps" section tells you whether the corpus *chose not to cover it* (and why) or whether *nobody saw it as in scope* (in which case you must do additional research).

---

## A. Coverage matrix (75 questions a design-phase agent is likely to ask)

Format: question → file + section → notes. The notes column flags anything important about the entry (depth, caveats, where it's lightly covered vs deeply).

### DFIR fundamentals and mental models

| # | Question | Where covered | Notes |
|---|---|---|---|
| 1 | What are the canonical IR lifecycle models (NIST/SANS/ENISA/ISO)? | `domain/01` §2 | All four compared side-by-side; the "where they disagree" callout is in §2 closing |
| 2 | What does "triage" actually mean operationally? | `domain/01` §3 | Kitchen-sink vs hypothesis-driven distinction is the key framing |
| 3 | How do senior analysts actually think? | `domain/01` §4 | Six-bullet mental model: hypothesis-driven, multi-artifact corroboration, timeline-as-spine, baseline, threat-intel grounding, pivot discipline |
| 4 | What is the order of volatility (RFC 3227)? | `domain/01` §5, `domain/03` §1.1 | Both treat it; `03` adds memory-specific application |
| 5 | What is the SANS "Hunt Evil" / canonical Windows boot/login process tree? | `domain/01` §6 | The "what should be running and what should be its parent" reference is here |
| 6 | What is the Pyramid of Pain and why does it matter? | `domain/01` §7, `domain/05` Part C closing | `05` applies it operationally to detection design |
| 7 | What does hypothesis-driven investigation look like in practice? | `domain/01` §4, §8 | §8 walks an example case |
| 8 | What is chain of custody operationally vs legally? | `domain/01` §10 (operational), `stakeholders/12` C6 (legal) | Doc 01 explicitly cross-refs doc 12 |
| 9 | What does a DFIR analyst's day look like (sketch)? | `domain/01` §11, `user/09` A.3 | Doc 09 is the deeper version; doc 01 is the inline sketch |
| 10 | DFIR vocabulary — what does term X mean? | `domain/01` §12 | 200+ term glossary |
| 11 | What analytical anti-patterns should the agent avoid? | `domain/01` §14 | Confirmation bias, premature closure, single-source over-trust, etc. |

### Windows forensic artifacts (`domain/02` is the index for almost all of these)

| # | Question | Where covered | Notes |
|---|---|---|---|
| 12 | What is the binary format of $MFT and what attributes matter? | `domain/02` §1, `domain/04` Part A §1 | Resident vs non-resident, SI vs FN, $J, ADS |
| 13 | $LogFile and $UsnJrnl mechanics — what survives, what's overwritten? | `domain/02` §2-3, `domain/04` Part A §3-4 | Retention behavior + parsers |
| 14 | How does VSS work and what evidence lives there? | `domain/02` §5, `domain/04` Part A §5, `domain/06` §2.6 | libvshadow usage is in 06 |
| 15 | What does Prefetch tell us and what's the W10/W11 schema change? | `domain/02` §6 | Hashing algorithm + last-8 timestamps |
| 16 | ShimCache vs Amcache vs BAM/DAM — what does each prove? | `domain/02` §7-9 | The "does execution evidence really mean execution?" caveat is in §7 |
| 17 | SRUM — what does it record and how is it queried? | `domain/02` §10, `domain/06` §5.11 (SrumECmd) | The ESE/SQLite combo is the gotcha |
| 18 | Registry hives — which hive holds what? | `domain/02` §11-15 | All six main hives + UsrClass.dat |
| 19 | What are the autorun keys and persistence taxonomy? | `domain/02` §12, §13, §14, §15 | Run/Services/Scheduled Tasks/WMI; §15 (WMI) covers OBJECTS.DATA |
| 20 | Sysmon EID reference — what does each event mean? | `domain/02` §16, `domain/04` §37 | `04` is the full reference; `02` is summary |
| 21 | Windows Event Log architecture + full EID catalog | `domain/04` Part C §32-46 | All Security/System/PowerShell/RDP/Defender events |
| 22 | PowerShell evidence — script block, transcript, ConsoleHost | `domain/02` §19, §22, `domain/04` §36 | The "missing PSReadLine = wiped" inference is in `02` §22 |
| 23 | ShellBags, LNK files, Jump Lists — what do they prove? | `domain/02` §23, §24 | User activity reconstruction |
| 24 | USB device chain — full forensic story | `domain/02` §28 | MountedDevices + USBSTOR + EMDMgmt + setupapi.dev.log |
| 25 | Pagefile / hiberfil / swapfile — what can we get? | `domain/02` §29 | Plus the hibernation-file-as-crypto-bypass move |
| 26 | ESE databases — WebCacheV01, SRUDB, ntds.dit, Windows.edb | `domain/02` §30 | Parsers + ESEDatabaseView reference |
| 27 | Alternate Data Streams + Zone.Identifier | `domain/02` §31 | Mark-of-the-Web semantics |
| 28 | ActivitiesCache (Windows Timeline) | `domain/02` §33 | The "what apps were used and for how long" artifact |
| 29 | Cross-artifact corroboration patterns (the 20 canonical patterns) | `domain/02` §34 (20 patterns) | The most operationally important section for a hypothesis-pivot loop |

### Memory forensics

| # | Question | Where covered | Notes |
|---|---|---|---|
| 30 | Memory acquisition options + pitfalls | `domain/03` §2, §16 | WinPMEM, MRC, DumpIt, hiberfil, VM snapshot, LiME/AVML |
| 31 | What image formats exist and which does Vol3 read directly? | `domain/03` §3 | raw, AFF4, LiME, ELF core, .dmp, .vmem, E01 |
| 32 | Volatility 3 architecture — how is it different from Vol2? | `domain/03` §4-5 | Layered abstraction, symbol cache, automagic, contexts |
| 33 | How does the ISF symbol cache work (the "Ralph Wiggum Loop" piece)? | `domain/03` §6 | Load-bearing for any self-correction demo — see also `13` A.10 and `12` D4 |
| 34 | Per-plugin catalog for Windows | `domain/03` §7 (~40 plugins) | + summary matrix at §19 |
| 35 | Per-plugin catalog for Linux | `domain/03` §8 | Including container-aware plugins |
| 36 | What memory-only IOCs exist? | `domain/03` §12 | Injected code, unlinked DLLs, hidden processes, kernel hooks |
| 37 | Standard memory triage chain | `domain/03` §11 | Reference workflow: info → pslist/pstree → cmdline → netscan → malfind → ldrmodules → handles → svcscan → dump |
| 38 | Memory + disk + log corroboration patterns | `domain/03` §15 | Multi-artifact reasoning across substrates |
| 39 | What does MemProcFS give you that Vol3 doesn't? | `domain/03` §13, `domain/06` §1.4 | Filesystem-view abstraction |

### Disk / filesystem / network / logs

| # | Question | Where covered | Notes |
|---|---|---|---|
| 40 | NTFS internals deep — clusters, runs, resident attrs, compression | `domain/04` Part A §1 | Plus alternate data streams and sparse files |
| 41 | File slack types — RAM vs file vs partition | `domain/04` Part A §2 | What can be recovered from each |
| 42 | plaso / log2timeline architecture + l2tcsv schema | `domain/04` Part A §6, `domain/06` §4.1-§4.6 | + dftimewolf for higher-level orchestration |
| 43 | Sleuth Kit family — mmls, fls, icat, istat, etc. | `domain/04` Part A §7, `domain/06` §3 | All TSK commands with examples |
| 44 | File carving — theory + tools | `domain/04` Part A §13, `domain/06` §9 | bulk_extractor, foremost, scalpel, photorec, binwalk |
| 45 | Encrypted volumes — BitLocker, VeraCrypt, FileVault, LUKS | `domain/04` Part A §14, `domain/06` §2.7-§2.9 | The hibernation-file-as-crypto-bypass move is here |
| 46 | NTFS timestamps — SI vs FN vs MFT entry time, what's writable | `domain/04` Part A §15 | The timestomping detection seed |
| 47 | Hash families — MD5/SHA family + ssdeep/TLSH | `domain/04` Part A §16, `domain/06` §8.5-§8.6 | Fuzzy hashing for malware similarity |
| 48 | Network forensics — Zeek vs Suricata, when to use which | `domain/04` Part B §20-§21, `domain/06` §10.4-§10.5 | Doc 04 explains the framework difference; doc 06 has command-line examples |
| 49 | Beacon detection (RITA) — how does it work mathematically? | `domain/04` §24, §26, `domain/06` §10.7 | Inter-arrival time variance + connection count + size consistency |
| 50 | DNS exfil detection signals | `domain/04` §27 | TXT abuse, subdomain entropy, query rate, NXDOMAIN baseline |
| 51 | JA3/JA3S fingerprints — what they catch and miss | `domain/04` §23 | TLS-handshake hashing; what evades it |
| 52 | Hayabusa / Chainsaw / Sigma — rule engine comparison | `domain/04` §43-§45, `domain/06` §7.1-§7.2 | Hayabusa command-line + scoring is in `06` |
| 53 | Sysmon config baselines (SwiftOnSecurity, Olaf Hartong) | `domain/04` §38 | What gets logged by default and what doesn't |

### Anti-forensics and attack patterns

| # | Question | Where covered | Notes |
|---|---|---|---|
| 54 | What is the full anti-forensics catalog (35 techniques)? | `domain/05` Part A §1-§35 | Each: mechanism, motive, detection signals, residue |
| 55 | LOLBins by binary | `domain/05` §5 | Categorized by binary — certutil, wmic, rundll32, etc. |
| 56 | Process injection family — hollowing, doppelgänging, herpaderping, atom-bombing | `domain/05` §6-§12 | All variants + how they're detected in memory |
| 57 | Kerberos abuse — Golden, Silver, Kerberoasting, AS-REP | `domain/05` §32, Part B §19, §20 | Cross-referenced with EID 4769/4768 |
| 58 | Real-world kill chains — ransomware, APT29, APT41, Lazarus, FIN7, etc. | `domain/05` Part B §1-§20 | 20 attack playbooks with TTPs |
| 59 | GTG-1002 pattern (Anthropic Nov 2025) | `domain/05` Part B §11, `reference/13` Part C | The "AI-orchestrated cyber espionage" disclosure |
| 60 | Cloud-native attacks — Azure/Entra, AWS, GCP | `domain/05` Part B §10 | Token theft, IMDS abuse, IAM persistence |
| 61 | MITRE ATT&CK subset for host forensics — every tactic | `domain/05` Part C | All 12 tactics + key techniques |

### SIFT toolchain

| # | Question | Where covered | Notes |
|---|---|---|---|
| 62 | What ships with the SIFT Workstation? | `domain/06` (the full doc) | Tool-by-tool reference |
| 63 | Volatility 3 command-line + plugin list | `domain/06` §1.1 | Full reference |
| 64 | Eric Zimmerman tools — MFTECmd, EvtxECmd, etc. | `domain/06` §5 (all 15 EZ tools) | Output schemas + batch capability |
| 65 | RegRipper3.0 plugin catalog | `domain/06` §6.1 | Plus rip.pl invocation |
| 66 | YARA / capa / FLOSS — when to use which | `domain/06` §8.1-§8.3 | Pattern, capability, deobfuscation |
| 67 | KAPE — how it actually works | `domain/06` §12.1 | Targets vs Modules; tkape vs mkape |
| 68 | Velociraptor — VQL + artifact model | `domain/06` §12.2 | The most live-host-capable tool in the corpus |
| 69 | UAC (Unix-like Artifact Collector) | `domain/06` §12.3 | Linux/Mac counterpart to KAPE |
| 70 | Canonical tool chains (super-timeline, memory triage, etc.) | `domain/06` §15 | 6 chains with full command sequences |
| 71 | What is missing on stock SIFT? | `domain/06` §16 | What you must install or write yourself |
| 72 | Output format reference (l2tcsv, EZ CSV columns, Zeek/Hayabusa schemas) | `domain/06` §20 | For any pipeline that consumes tool output |

### MCP and agent platforms

| # | Question | Where covered | Notes |
|---|---|---|---|
| 73 | MCP spec — current revision and what changed | `technical/07` Part A | Revision 2025-11-25 tracked |
| 74 | Client / server / host model | `technical/07` A2 | Trust boundaries explicit |
| 75 | Transports — stdio vs Streamable HTTP vs SSE | `technical/07` A3 | When to use each; SSE deprecation |
| 76 | The three primitives — Tools, Resources, Prompts | `technical/07` A7 | + Sampling/Roots/Logging/Progress/Cancellation/Completions/Elicitation/Tasks in A8 |
| 77 | Auth/authz model | `technical/07` A9 | OAuth 2.1 + bearer tokens |
| 78 | MCP CVEs — MCPwn (CVE-2026-33032), OWASP MCP Top 10 | `technical/07` A12, `stakeholders/12` A7 (Yotam Perkal), `technical/08` §4.6, §5.4 | Cross-referenced multiple times |
| 79 | Python SDK — FastMCP vs low-level Server | `technical/07` B1 | Plus in-process SDK server pattern |
| 80 | Claude Agent SDK — primitives, hooks, subagents, permission system | `technical/07` Part C | C3 is primitives; C4 is the agent loop |
| 81 | Claude Agent SDK cost model | `technical/07` C5 | Effective Jun 15, 2026 |
| 82 | Multi-turn vs single-turn patterns | `technical/07` C7 | When each is the right shape |
| 83 | Stop hook + SubagentStop hook | `technical/07` C8 | For end-of-loop validation |
| 84 | Claude Code as host — CLAUDE.md, settings.json, skills | `technical/07` Part D | The host environment for Protocol SIFT / Valhuntir |
| 85 | Alternative frameworks (OpenClaw, LangGraph, CrewAI, AutoGen) | `technical/07` Part E | One-page summary each |
| 86 | Composition patterns | `technical/07` Part F | 8 glue patterns including hybrid framework + Agent SDK + MCP |

### LLM failure modes

| # | Question | Where covered | Notes |
|---|---|---|---|
| 87 | Hallucination taxonomy — what does "hallucination" actually mean? | `technical/08` §1 | Intrinsic vs extrinsic, faithfulness vs factuality, the "contested term" framing |
| 88 | Context rot / long-context degradation | `technical/08` §2 | U-shape, needle-in-haystack criticisms, Lost in the Middle |
| 89 | Prompt injection — direct, indirect, zero-click | `technical/08` §3 | Plus DFIR-specific vectors |
| 90 | Tool poisoning — adversarial defs, rug pulls, naming collisions, output bombs | `technical/08` §4 | + MCPwn at §4.6 |
| 91 | Sycophancy + reward hacking + spec gaming + mode collapse | `technical/08` §6 | Sharma sycophancy paper cited |
| 92 | Confidence miscalibration | `technical/08` §7 | The "models verbalize high confidence on low-evidence claims" finding |
| 93 | Jailbreak resistance + erosion | `technical/08` §8 | What works against current frontier models |
| 94 | Agentic loop failures (infinite loops, premature termination, rabbit hole, etc.) | `technical/08` §9 | All 9 named failure modes |
| 95 | DFIR-specific LLM-in-tool-loop failures | `technical/08` §10 | Hallucinated paths/hashes/flags, misreading tool output, over-confident attribution |
| 96 | Cost / latency failure modes | `technical/08` §11 | Including the "context bloat → unbounded cost" path |
| 97 | 2024-2026 academic findings catalog | `technical/08` §12 | Plus citation list in appendix |

### IR consultant reality

| # | Question | Where covered | Notes |
|---|---|---|---|
| 98 | Who is the user — persona, where they work, their day | `user/09` Part A | The most operationally-grounded persona doc |
| 99 | Hour-by-hour engagement flow (Hours 0 through 40+) | `user/09` Part B | 11 phases with "where AI helps most per phase" callouts |
| 100 | Engagement variants beyond ransomware | `user/09` Part C | Insider, BEC, APT, e-discovery, supply chain, cloud-native |
| 101 | Report anatomy — universal sections, audiences, real template breakdowns | `user/09` Part D | Three artifacts at three stages: triage, exec-summary, final |
| 102 | Stakeholder communication patterns | `user/09` Part E | CIO/CISO, legal/GC, insurance, regulatory, customer/public |
| 103 | What practitioners hate / love / complain about publicly | `user/09` Part F | The wedge in their own words |
| 104 | IR billing model + retainer expectations | `user/09` A.5, A.10 | $375-650/hr; the "show velocity" pressure |

### Datasets and evaluation

| # | Question | Where covered | Notes |
|---|---|---|---|
| 105 | What public DFIR datasets exist (25 of them)? | `evaluation/10` Part A | Each: scenario, materials, expected path, ground-truth availability, LLM memorization risk |
| 106 | What is VIGIA and where is it? | `evaluation/10` Part B | **Status: NOT publicly located as of 2026-06-02; may be in Protocol SIFT NotebookLM or SANS Slack** |
| 107 | DFIR-Metric benchmark | `evaluation/10` Part C, `reference/13` E.1 | The most relevant published AI-DFIR benchmark |
| 108 | CyberSleuth methodology | `evaluation/10` Part C, `reference/13` E.2 | Autonomous blue-team web-attack forensics |
| 109 | Hallucination metric families — what to measure | `evaluation/10` Part D | Precision/recall, faithfulness vs factuality, FActScore/CiteCheck atomic-claim decomposition, citation accuracy, NABAOS tool-call accuracy |
| 110 | Baseline establishment — what counts as baseline, variance, controls | `evaluation/10` Part E | Run-to-run variance is the load-bearing operational concept |
| 111 | Public answer-key sources | `evaluation/10` Part F | Where canonical solutions for each dataset live |
| 112 | Evaluation pitfalls to avoid | `evaluation/10` Part G | 13 specific failure modes (memorization-as-capability, etc.) |

### Competitive landscape

| # | Question | Where covered | Notes |
|---|---|---|---|
| 113 | What is Protocol SIFT and what does it actually do? | `competitive/11` §1 | 10-file Claude Code config bundle; NO MCP, NO daemon, NO runtime |
| 114 | Valhuntir architecture deep — 3 layers, 9 backends, 9 defense layers | `competitive/11` §2 | Plus file-line citations into the actual repo |
| 115 | Valhuntir HMAC ledger — full crypto detail | `competitive/11` §2 L2 | PBKDF2-600K + HMAC-SHA256, password-gated examiner identity binding |
| 116 | What does Valhuntir NOT do (the gaps competitors are filling)? | `competitive/11` §2.7 | No adversarial-evidence defense, no live triage, no multi-host |
| 117 | The 20+ other hackathon competitors | `competitive/11` §4 | One-paragraph decomp each |
| 118 | Non-hackathon forensic MCP servers | `competitive/11` §5 | Volatility-MCP, velociraptor-mcp, DFIR-IRIS MCP, etc. |
| 119 | Vendor "AI SOC" products | `competitive/11` §6 | Charlotte AI, Security Copilot + Sentinel MCP, Cortex AgentiX, etc. |
| 120 | Anti-hallucination patterns from outside DFIR | `competitive/11` §8 | Pydantic+Instructor, NABAOS, GitMCP, Anthropic Citations API |
| 121 | Observable patterns / gaps nobody is filling | `competitive/11` Closing | The wedge-validation lens |

### Judges, curriculum, legal

| # | Question | Where covered | Notes |
|---|---|---|---|
| 122 | Who is on the judge panel and what does each weight? | `stakeholders/12` Part A | 20 deep dives + ~28 thumbnails |
| 123 | What is Rob T. Lee's worldview in his own vocabulary? | `stakeholders/12` A1, `reference/13` Part A | The exact verbs to mirror |
| 124 | What does Steve Anson believe good agentic IR looks like? | `stakeholders/12` A9, `competitive/11` §2 | Valhuntir IS his answer; READ the code |
| 125 | What is Ovie Carroll's "silent witness" framing? | `stakeholders/12` A2 | Used as the project name origin |
| 126 | SANS DFIR curriculum — what does each course teach? | `stakeholders/12` Part B | FOR500/508/509/526/572/578/610/710 |
| 127 | The "SANS way" six-bullet doctrine | `stakeholders/12` B9 | What every FOR508 graduate has absorbed |
| 128 | What does FRE 707 actually say and when is it effective? | `stakeholders/12` C4 | **Status: PROPOSED as of June 2026; earliest effective Dec 1, 2026, possibly 2027.** Section explicitly corrects the "Dec 2024" date stated elsewhere in the corpus — see Inconsistency section below |
| 129 | FRE 702 + Daubert (2023 amendment) | `stakeholders/12` C2 | The current expert-testimony standard |
| 130 | Frye standard — which states still use it | `stakeholders/12` C3 | Plus a state-by-state note |
| 131 | Best evidence rule + hearsay considerations | `stakeholders/12` C7, C8 | FRE 1001-1008, FRE 801-807 |
| 132 | AI evidence in civil discovery (TAR precedent) | `stakeholders/12` C10 | Da Silva Moore + descendants |
| 133 | EU framework — GDPR + AI Act | `stakeholders/12` C12 | High-risk system implications |
| 134 | Black box / explainability problem | `stakeholders/12` C15 | Why the audit trail is structurally required, not optional |
| 135 | Audit trail framework anticipated by FRE 707 | `stakeholders/12` C16 | Synthesis of Carrier + Sedona Conference + the rule text |
| 136 | Cross-examination playbook against AI-generated findings | `stakeholders/12` D6 | The questions opposing counsel will ask |

### Primary sources

| # | Question | Where covered | Notes |
|---|---|---|---|
| 137 | Rob T. Lee primary writings (verbatim) | `reference/13` Part A | Substacks, SANS blog, press release, YouTube transcript, X posts |
| 138 | Steve Anson primary writings + Valhuntir docs | `reference/13` Part B | README, architecture.md, security.md, Clear Disclosure verbatim |
| 139 | GTG-1002 Anthropic disclosure (verbatim) | `reference/13` Part C | The first reported AI-orchestrated cyber espionage campaign |
| 140 | Industry threat reports — CrowdStrike, Mandiant, Verizon, Microsoft | `reference/13` Part D | Plus MIT ALFA-Chains, Horizon3 NodeZero, Anthropic engineering blog |
| 141 | Academic paper abstracts + key findings | `reference/13` Part E | 15 papers, each with quoted abstract |
| 142 | MCP spec excerpts | `reference/13` Part F | Plus Python SDK + TS SDK README excerpts |
| 143 | Hackathon official material (Devpost rules, resources) | `reference/13` Part H | The rules verbatim |
| 144 | Practitioner voices (Shavers, DeGrazia, Carvey, Carhart, Case, Carrier, etc.) | `reference/13` Part I | The non-judge corpus practitioners read |

That gets you to 144 questions. There are more — but if the above set is genuinely answerable by reading the corpus, the corpus is doing its job.

---

## B. Identified gaps — what `context/` does NOT cover deeply

A design-phase agent should know what is NOT here so they can decide whether to do additional research or to scope the build to avoid these areas.

### B.1 Cloud forensics depth (AWS / Azure / GCP)

**What's there:** brief mention in `user/09` C.6 (cloud-native engagements), `domain/05` Part B §10 (cloud-native attack patterns), `stakeholders/12` B3 (FOR509 course overview). The Cado / Mitiga / Wiz IR / AWS Detective tools are named.

**What's NOT there:**
- The CloudTrail event schema in detail
- Azure Activity Log schema
- GCP Audit Logs structure
- The specific cloud-side acquisition workflows (snapshot before terminate, IMDS data preservation, etc.)
- Cloud-specific anti-forensics (CloudTrail log evasion via region-skipping, etc.)
- M365 / Google Workspace forensics depth (UAL parsing, mailbox audit logs)
- Cross-tenant attacks (Entra ID token theft → graph API abuse)

**Implication:** If the build targets cloud forensics, additional research is required. The hackathon rules center on SIFT integration (i.e., on-prem disk + memory + Windows logs), so this gap is intentionally aligned with the brief. But if SilentWitness is to handle a cloud-native engagement variant, the corpus does not get you there.

### B.2 macOS forensics

**What's there:** `domain/03` §8.4 (Mac memory plugin catalog), `domain/04` Part A §11 (HFS+/APFS basics). Brief.

**What's NOT there:**
- Spotlight metadata forensics (`.Spotlight-V100`)
- FSEvents and the `/.fseventsd` databases
- Quarantine database (`QuarantineEventsV2`)
- macOS Unified Logging (`log` command, ASL)
- Keychain forensics
- KnowledgeC.db (the macOS equivalent of ActivitiesCache)
- macOS persistence taxonomy (LaunchAgents, LaunchDaemons, login items, kexts)
- TCC database
- APFS snapshots forensic recovery

**Implication:** If the build needs to handle Mac evidence, the corpus does not get you there. The hackathon focus is Windows + Linux memory.

### B.3 Linux desktop / server forensics depth

**What's there:** `domain/03` §8 + §18 (Linux memory deep), `domain/04` Part A §10 (ext4 basics), `domain/06` §1.7 (LiME/AVML), §12.3 (UAC). Server-side workflows are touched lightly.

**What's NOT there:**
- systemd unit forensics + systemd-journald binary log format
- auditd rules + audit.log analysis depth
- bash_history vs hsh_history vs zsh_history vs the new XDG patterns
- /var/log/* exhaustive reference
- Cron + at + systemd timer persistence catalog
- LD_PRELOAD, kernel module abuse
- eBPF rootkit detection
- container escape forensics (cgroup analysis, namespace inspection)
- Linux LOLBins catalog (gtfobins coverage in DFIR terms)

**Implication:** The corpus is Windows-heavy. If a target case is Linux-server intrusion (BlackBasta or similar 2024-2026 Linux ransomware lineage), additional research is required.

### B.4 Mobile forensics

**Explicitly out of scope.** The corpus mentions Mari DeGrazia and Hexordia as the mobile practitioners but does not go deeper. Find Evil! does not test mobile.

### B.5 ICS / SCADA / OT forensics

**Out of scope.** Mentioned only via Lesley Carhart and Robert M. Lee thumbnails. The corpus does not cover Modbus, DNP3, OPC-UA, PLC firmware forensics, or the Dragos/Claroty toolchain.

### B.6 Specific malware family reverse-engineering

**What's there:** generic RE tool reference (Ghidra, radare2, FLOSS) in `domain/06` §11. The capa rule pattern is referenced.

**What's NOT there:** family-specific unpacker walkthroughs, specific UPX/Themida/Enigma unwrapping procedures, specific Cobalt Strike beacon config extraction, specific Emotet/Qakbot/IcedID protocol parsing. The CrowdStrike/Mandiant threat-report citations cover the *what*; not the *how to reverse it*.

**Implication:** If the agent is to do deep malware RE inline, this is gap. SilentWitness is hypothesis-IR-investigator-shaped, not RE-engineer-shaped, so this gap may be aligned.

### B.7 Active Directory forensics depth

**What's there:** `domain/05` Part B §18 (AD compromise patterns), §32 (Kerberos abuse), `domain/02` §30 (ntds.dit as an ESE database).

**What's NOT there:**
- ntds.dit + SYSTEM hive offline parsing workflow (impacket secretsdump deep)
- SYSVOL / GPP cpassword forensics depth
- BloodHound output integration patterns
- AD replication forensics
- DSRM password reset evidence
- GPO modification audit
- Schema modification + ADAM patterns
- Operator group misconfigurations as IOCs (Print Operators, Backup Operators, etc.)

**Implication:** AD compromise is one of the most common real engagements. The corpus gives you the IOC pattern but not the deep parsing workflow. Additional research required if AD is the case substrate.

### B.8 Container / Kubernetes forensics depth

**What's there:** brief mention in `domain/03` §18.3 (Linux container memory carries all container processes). The "FOR509 covers k8s" thumbnail.

**What's NOT there:** Falco/sysdig audit, Kubernetes audit log schema, runtime IOCs (eBPF detection of container escape), container image forensic comparison, sidecar injection forensics, registry compromise detection.

### B.9 Live host triage workflows beyond KAPE/Velociraptor/UAC

**What's there:** the three named collectors are covered in `domain/06` §12.

**What's NOT there:** F-Response, Magnet AXIOM live, EnCase Endpoint, GRR Rapid Response, Osquery as a forensic substrate (vs operational substrate), CarbonBlack/CrowdStrike/SentinelOne RTR survey of triage commands.

### B.10 Specific eDiscovery / TAR workflow depth

**What's there:** `stakeholders/12` C10 covers the TAR precedent and the legal angle.

**What's NOT there:** Relativity, Everlaw, Brainspace operational workflow; CAL vs TAR vs predictive coding distinctions in operation. This is fine for Find Evil! — eDiscovery is not the wedge — but if a judge starts asking why the agent is not also doing TAR-shaped review, the corpus does not get you there.

### B.11 Specific tool versions / API drift

**What's there:** Volatility 3, plaso, Eric Zimmerman, Hayabusa, etc. — all current as of June 2026.

**What's NOT there:** version-pinned behavior matrices. If a tool ships a breaking change after the corpus is written (Vol3.4 vs Vol3.5 differences, plaso 20240315 vs 20240501 plugin set), the corpus may drift. Treat the corpus as a snapshot.

### B.12 Specific Anthropic / OpenAI / Gemini model behavior idiosyncrasies

**What's there:** generic LLM failure modes (`technical/08`), agent SDK behavior (`technical/07` Part C).

**What's NOT there:** model-specific failure modes (e.g., "Claude 4.5 Opus is sycophant-y when X; GPT-5 hallucinates dates when Y"). The corpus is model-agnostic on purpose, but a real build will hit model-specific quirks not documented here.

### B.13 Operational telemetry for IR-team management (Jira, ServiceNow IR, etc.)

**What's there:** brief mention in `user/09` A.4 of analyst tooling.

**What's NOT there:** how Jira-shaped or ServiceNow-shaped IR ticketing actually works, what fields matter, how the report is consumed by the team. SilentWitness produces a report — but a real customer consumes that report into a ticketing system, and the corpus does not deeply cover the consumption end.

### B.14 Threat intel platform integration

**What's there:** MISP and OpenCTI are named in passing; FOR578 curriculum is summarized.

**What's NOT there:** MISP event schema, taxonomy/galaxy structure, OpenCTI STIX 2.1 model depth, ThreatConnect/Recorded Future/Anomali specifics. If SilentWitness pushes findings to a TIP, additional research is required.

### B.15 The specific Protocol SIFT NotebookLM contents

**What's there:** the NotebookLM link, the framing that VIGIA may live inside it.

**What's NOT there:** the actual NotebookLM contents (gated). A design-phase agent should request access from Rob's Slack and consume directly.

### Frame for these gaps

If a design-phase agent needs ANY of B.1–B.15, they will have to do additional research. The corpus deliberately scopes to the SilentWitness wedge: Windows + Linux memory disk-image investigation with structured-report output. Stretching beyond that wedge requires additional knowledge gathering.

---

## C. Identified inconsistencies (with corrections)

### C.1 FRE 707 effective date — STALE in two places

**Status (authoritative):** `stakeholders/12` C4 has the corrected position: FRE 707 is **proposed**, not enacted; earliest likely effective date is **December 1, 2026**, possibly 2027.

**Stale references found:**

1. `stakeholders/12` line 21 (the doc's own table of contents): "FRE 702 / Daubert / FRE 707 (Dec 2024)" — wrong, contradicted by C4 of the same doc.
2. `evaluation/10` §C.6 line 939: "Federal Rules of Evidence Rule 707, as adopted via the December 2024 amendments to the FRE. (FRE 707 was promulgated by the Committee on Rules of Practice and Procedure and adopted by the Judicial Conference, taking effect in 2024.)" — wrong.
3. `evaluation/10` line 1419 (sources list): "Federal Rules of Evidence Rule 707 (adopted via December 2024 FRE amendments)" — wrong.
4. `user/09` line 722: "FRE 707, approved by Judicial Conference in 2025" — partial; FRE 707 has not been approved by the Judicial Conference; the prompt-stage drafting was in 2025; what was approved Dec 2024 was the FRE 702 amendment, not 707.
5. `domain/01` line 673: "FRE 707, Daubert, the 2024 FRE 707 AI-evidence amendment" — wrong (the 2024 amendment was to 702, not 707).

**Correct statement (sourced from `stakeholders/12` C4):**
> FRE 707 is proposed, having moved through Advisory Committee → Standing Committee → public comment. Earliest likely effective date is December 1, 2026, possibly 2027. The "December 1, 2024" date that some legal commentary attaches refers to the **earlier 2023 amendment of FRE 702**, not 707.

**Operational impact for a design-phase agent:** if the system claims FRE 707 compliance as a hard property, the legal landscape is still moving. Frame audit trail as "anticipated by the proposed FRE 707 framework" rather than "compliant with the enacted rule." Doc 12 C16 already does this correctly.

### C.2 The "FRE 707 effective Dec 2024" claim is also incompatible with the corpus's own June 2026 date stamp

The corpus is dated 2026-06-02. If FRE 707 had been effective since Dec 2024, there would be 18 months of case law to cite. The corpus does not cite any (`stakeholders/12` C11 covers "Notable Early AI Evidence Cases 2024-2026" and these are FRE 702-shaped cases, not FRE 707-shaped). This is consistent with the corrected position (FRE 707 is proposed, not effective) and inconsistent with the stale references.

### C.3 VIGIA framing — consistent

Cross-checked: `evaluation/10` Part B and the README both treat VIGIA as "unverified / possibly in Protocol SIFT NotebookLM or SANS Slack / not publicly located as of 2026-06-02." No inconsistency. The corpus correctly avoids treating VIGIA as a known artifact.

### C.4 Protocol SIFT baseline characterization — consistent

Cross-checked: `competitive/11` §1 says "10-file config bundle, no MCP, no daemon, no runtime"; README echoes "10-file Claude Code config bundle"; `stakeholders/12` references it as "Rob T. Lee's research project, not validated for forensic soundness or evidentiary reliability." All consistent.

### C.5 Valhuntir characterization — consistent

Cross-checked: `competitive/11` §2 says "Valhuntir is the published quality bar"; `stakeholders/12` A9 says "the hackathon brief explicitly cites as 'the quality bar to meet or exceed'"; `reference/13` Part B quotes the README verbatim with that exact framing. All consistent.

### C.6 HMAC + PBKDF2 — consistent

`competitive/11` says PBKDF2-600K + HMAC-SHA256; `stakeholders/12` A9 says "Approved findings are HMAC-signed with a PBKDF2-derived key"; the README echoes "HMAC-SHA256 + PBKDF2-600K iteration ledger." Consistent. Note: the 600K iteration count is itself drawn from the Valhuntir source as cited; if a design-phase agent reads the code directly, they should verify the count hasn't changed.

### C.7 MCPwn (CVE-2026-33032) — consistent

Cross-checked across `technical/07` A12, `technical/08` §4.6 and §5.4, `stakeholders/12` A7 (Yotam Perkal). All four references describe the same vulnerability (nginx-ui MCP integration, default-empty IP whitelist on `/mcp_message`, CVSS 9.8, disclosed early 2026, ~2,689 exposed instances at disclosure). Consistent.

### C.8 GTG-1002 — consistent

Cross-checked across `domain/05` Part B §11, `reference/13` Part C, `stakeholders/12` A1, README. All references describe the November 2025 Anthropic disclosure of a Chinese state-sponsored campaign using Claude Code + MCP for 80-90% of tactical operations. Consistent.

### C.9 The "Ralph Wiggum Loop" framing — consistent but with one important nuance

`reference/13` line 107 explicitly notes: **"Performing self-correction" is Rob T. Lee's exact verb. NEVER replace with "Ralph Wiggum Loop" in any user-visible artifact; that phrase is the agent-coding community's, not Rob's.**

`stakeholders/12` D4 respects this: "'the Ralph Wiggum Loop' framing, though he himself uses 'self-correction' rather than the meme."

The README at lines 70 and 116 uses "Ralph Wiggum Loop" — which is fine because the README is for downstream agents, not for user-facing artifacts. Consistent with the rule.

**Implication for design-phase agents:** when writing the demo script or the public-facing README of the build, use "self-correction." Internal docs can use either.

### C.10 Demo-time benchmark numbers — internally consistent but inherited from Rob's framing

`user/09` Part B and the wedge framing both cite Rob's "8-12 hours of work → ~25 minutes of agent-driven" target. This is downstream of Rob's framing in his Substack and SANS blog. Internally consistent; just be aware these are aspirational/marketing numbers, not measured.

---

## D. Cross-reference suggestions

Places where two docs SHOULD explicitly link to each other but don't (or only do so partially). These are SUGGESTIONS for design-phase agents — they do not require editing the existing docs.

### D.1 `domain/03-memory-forensics-deep` ↔ `domain/02-windows-artifacts-encyclopedia`

When `domain/03` discusses memory-based process tree (pslist/pstree), it should reference `domain/02` §11-15 (registry-based persistence) and `domain/02` §34.5 (Pattern: "Persistence + execution + network exfil") for the cross-substrate corroboration. The "Hunt Evil" canonical tree appears in `domain/01` §6; both `02` and `03` should link there.

### D.2 `technical/08-llm-failure-modes` ↔ `competitive/11-reference-implementations-decomposed`

Each of the 14 failure modes in `08` has a corresponding mitigation pattern visible in Valhuntir's source (covered in `11` §2). A design-phase agent picking a defense strategy for failure mode X would benefit from seeing how Valhuntir handled that exact failure mode. Specifically:
- `08` §3 (prompt injection) ↔ `11` §2 layer L4 (advisory injection guard)
- `08` §4 (tool poisoning) ↔ `11` §2 layer L3 (41 deny rules)
- `08` §6 (sycophancy) ↔ `11` §2 layer L7 (human-gate finding promotion)
- `08` §7 (confidence miscalibration) ↔ `11` §2 layer L6 (`record_finding` confidence-enum constraint)
- `08` §10 (hallucinated paths/hashes) ↔ `11` §2 layer L8 (forensic-rag enrichment)

### D.3 `domain/05-anti-forensics` ↔ `domain/02-windows-artifacts-encyclopedia`

Each anti-forensics technique in `domain/05` leaves residue in specific artifacts in `domain/02`. The "what evidence remains after the anti-forensics action" is split between the two docs and would benefit from explicit cross-refs (e.g., `05` §2 log clearing → `02` §17 EID 1102; `05` §20 VSS deletion → `02` §5 VSS).

### D.4 `user/09-ir-consultant-reality` ↔ `stakeholders/12-judges-curriculum-and-legal-landscape`

The "engagement → handoff → litigation" chain is covered as the analyst's perspective in `09` Part E and as the legal admissibility perspective in `12` Part C. They are the same workflow seen from two angles. A design-phase agent making decisions about audit-trail granularity needs both at once.

### D.5 `domain/06-sift-toolchain-deep` ↔ `domain/04-disk-network-log-forensics-deep`

`06` is "how to invoke each tool"; `04` is "what each output means." Each tool subsection in `06` would benefit from a one-line link to the corresponding evidence-type section in `04`. E.g., `06` §1.1 (Volatility 3) → `04` §0 (memory not covered here, see `03` instead — which is itself a missing cross-ref).

### D.6 `evaluation/10-datasets-and-evaluation-methodology` ↔ `reference/13-source-corpus`

The academic papers in `10` Part C are cited again in `13` Part E. `10` would benefit from explicit "see `13` E.X for the full abstract" links. Symmetrically, `13` would benefit from "see `10` Part C for methodology discussion" links.

### D.7 `competitive/11` §1 (Protocol SIFT) ↔ `reference/13` Part A (Rob T. Lee corpus)

The Protocol SIFT design choices in `11` §1 directly reflect Rob T. Lee's written framing in `13` Part A. A design-phase agent decoding "why did Protocol SIFT make decision X" needs both at once.

---

## E. Quality stamp per doc

For each of the 13 docs:
1. Verdict (strong / comprehensive / actionable, in one line)
2. Coverage gaps (anything notably missing within scope)
3. No-architecture discipline held (yes / no / partial)
4. Sources cited adequately (yes / no)

### E.1 `domain/01-dfir-foundations.md` (15.6K words)

- **Verdict:** Strong. The IR mental-model spine of the corpus.
- **Coverage gaps:** None within scope. The §14 "common anti-patterns" section is unusually valuable.
- **No-architecture discipline:** Yes.
- **Sources:** Yes. NIST SP 800-61, RFC 3227, SANS course material, Bianco's Pyramid of Pain origin post.

### E.2 `domain/02-windows-artifacts-encyclopedia.md` (32.9K words — the biggest doc)

- **Verdict:** Comprehensive. The most operationally load-bearing doc for any Windows-evidence pipeline.
- **Coverage gaps:** Light treatment of Outlook PST/OST and Edge Chromium SyncedSettings; deeper would help. ActivitiesCache schema details are thinner than Prefetch. §34 (20 cross-artifact patterns) is the standout section.
- **No-architecture discipline:** Yes.
- **Sources:** Yes. Per-artifact: SANS posts, Microsoft docs, Eric Zimmerman blog, Harlan Carvey blog, individual forensic researcher writeups.

### E.3 `domain/03-memory-forensics-deep.md` (17.7K words)

- **Verdict:** Strong. The "Ralph Wiggum Loop" piece (§6 symbol cache) is operationally important.
- **Coverage gaps:** Win11 24H2 memory compression specifics; the Windows kernel patch-guard interaction with memory acquisition. Mac and Linux plugin catalogs are present but lighter than Windows (which is fine for scope).
- **No-architecture discipline:** Yes.
- **Sources:** Yes. Volatility docs, Andrew Case talks, MemProcFS GitHub, Mark Russinovich Sysinternals.

### E.4 `domain/04-disk-network-log-forensics-deep.md` (20.6K words)

- **Verdict:** Comprehensive. The Security EID reference (§33) is the standout — it's the kind of reference a forensic agent would call out to as a substrate-of-knowledge.
- **Coverage gaps:** ext4 / APFS / FAT32 are present but at "basics" depth. The Suricata reference is thinner than Zeek. Sigma rule format is well-covered but the Sigma → Hayabusa translation could go deeper.
- **No-architecture discipline:** Yes.
- **Sources:** Yes. ULTRA-NTFS, Brian Carrier's *File System Forensic Analysis*, Sleuth Kit docs, Microsoft Event Viewer documentation, Sigma project README.

### E.5 `domain/05-anti-forensics-and-attack-patterns.md` (20.6K words)

- **Verdict:** Strong. The 35-technique catalog is the most actionable adversary-side reference.
- **Coverage gaps:** ARM-specific anti-forensics (relevant to Windows-on-ARM and Mac M-series, though Mac is out of scope). Recent UEFI implants beyond LoJax. Container-escape anti-forensics is thin (consistent with broader container gap).
- **No-architecture discipline:** Yes.
- **Sources:** Yes. MITRE ATT&CK, ATT&CK Evaluations, individual technique papers (process hollowing — Stuxnet origin; doppelgänging — Liberman/Kogan BlackHat 2017; etc.).

### E.6 `domain/06-sift-toolchain-deep.md` (25.1K words)

- **Verdict:** Comprehensive. Tool-by-tool deep reference. The §15 canonical tool chains are immediately reusable.
- **Coverage gaps:** Velociraptor VQL is covered well but the VQL artifact authoring workflow is light. KAPE module authoring is light. NetworkMiner is a brief mention (because it's GUI-only). Magnet AXIOM is mentioned only at vendor-product level (not on stock SIFT, correctly).
- **No-architecture discipline:** Yes — careful tool-reference framing throughout.
- **Sources:** Yes. Each tool's official docs + author blog where applicable.

### E.7 `technical/07-mcp-and-agent-platforms.md` (14.2K words)

- **Verdict:** Strong. Tracks the 2025-11-25 MCP spec revision explicitly. The Claude Agent SDK breakdown (Part C) is more current than most public references.
- **Coverage gaps:** OAuth 2.1 implementation specifics (token exchange, refresh flow) are light. The MCP `tasks` primitive is new and the doc treats it briefly. Anthropic SDK cost model is current (effective Jun 15 2026) but will drift.
- **No-architecture discipline:** Yes. The doc is careful to describe primitives, not prescribe their use.
- **Sources:** Yes. modelcontextprotocol.io, GitHub SDK READMEs, Anthropic engineering blog, MCP CVE disclosures.

### E.8 `technical/08-llm-failure-modes-in-agentic-systems.md` (14.1K words)

- **Verdict:** Strong. The contested-term framing in §1 is the right intellectual posture. The DFIR-specific failure modes in §10 are the operational payoff.
- **Coverage gaps:** Multi-modal failure modes (vision/audio injection) are not covered (correctly, for a text-substrate forensic task). Adversarial RAG attack surface is thinner than direct prompt injection.
- **No-architecture discipline:** Yes — describes failure modes, lets the design phase decide mitigations.
- **Sources:** Yes. Academic citations are extensive (Lost in the Middle, Sharma sycophancy, CiteCheck, FActScore, etc.).

### E.9 `user/09-ir-consultant-reality.md` (17.2K words)

- **Verdict:** Strong. The most operationally-grounded persona doc; Part F (practitioner voices) is the validation layer.
- **Coverage gaps:** Junior-analyst perspective is thinner than senior. The "MSSP delivering IR as a side business" engagement variant is mentioned but not deep. Insurance-driven IR (Tetra Defense / Coveware / etc.) gets less attention than retainer IR.
- **No-architecture discipline:** Yes.
- **Sources:** Yes — practitioner blog quotes, reddit threads, conference talks, vendor product pages.

### E.10 `evaluation/10-datasets-and-evaluation-methodology.md` (16.1K words)

- **Verdict:** Strong. The 25-dataset catalog (Part A) is the most actionable substrate for building an eval harness. The 13 pitfalls (Part G) are uncomfortably useful.
- **Coverage gaps:** **Note the FRE 707 inconsistency in C.6** (see Inconsistencies section above) — partial gap that misframes the rule. CFReDS has been refreshed since 2023 and some specific cases (Drone, Cell Phone) are not in the catalog. SANS Holiday Hack Challenge as a dataset substrate is not mentioned.
- **No-architecture discipline:** Yes.
- **Sources:** Yes — each dataset's landing page, academic citations for methodology.

### E.11 `competitive/11-reference-implementations-decomposed.md` (19.9K words)

- **Verdict:** Comprehensive. The Valhuntir 9-layer decomposition with file:line citations into the source is the standout — it's the closest thing to a reverse-engineered architecture spec.
- **Coverage gaps:** The 20+ other competitors are one-paragraph each (correctly, given the field size). Vendor AI SOC coverage is current as of June 2026; will drift. Some sift-bench / sift-sentinel / similar near-name builds may be different repos than expected.
- **No-architecture discipline:** Partial. The decomposition is descriptive (which is correct), but the closing-section "patterns observable across the field" walks close to prescriptive at times. A design-phase agent should treat the observable-patterns list as data, not as recommendations.
- **Sources:** Yes — every repo URL and HEAD commit cited; for vendor products, official product pages + recent reviews.

### E.12 `stakeholders/12-judges-curriculum-and-legal-landscape.md` (15.7K words)

- **Verdict:** Strong. The 20 deep judge personas + the cross-cutting synthesis in Part D give a clear "what they'll weight" map. Part C is the most legally-current treatment in the corpus.
- **Coverage gaps:** Discord/Slack analytics on judge participation are mentioned but not deeply tracked. The "judge of judges" (i.e., Rob T. Lee's voting power vs. the panel's collective) framing is implicit but not made explicit.
- **No-architecture discipline:** Yes — Part C correctly flags "whether to frame as court-admissible is a design-phase decision."
- **Sources:** Yes — judge LinkedIn, judge Substack/Twitter, judge employer pages; FRE official text via uscourts.gov; Daubert v. Merrell Dow citation.

### E.13 `reference/13-source-corpus.md` (11.5K words)

- **Verdict:** Strong as a pure quotation reference. Intentionally has no commentary.
- **Coverage gaps:** Some practitioner voices are referenced with "no specific verbatim quote surfaced" (Lesley Carhart). Steve Anson's books are summarized but not quoted at length (consistent with copyright caution).
- **No-architecture discipline:** Yes — by design, this doc has no synthesis at all.
- **Sources:** Yes — every quoted item has URL + access date.

---

## F. Downstream readiness verdict

**Is the corpus ready for design-phase agents? Yes — with three caveats.**

1. **The FRE 707 date inconsistency** must be flagged to any design-phase agent. The authoritative position lives in `stakeholders/12` C4; the stale references in `evaluation/10`, `user/09`, and `domain/01` should be read with that correction in mind. Any architecture decision touching legal admissibility should rely on `12` C4 not the others. (See Inconsistencies section above.)
2. **The corpus is Windows + Linux-memory shaped.** If the design phase decides to extend SilentWitness toward Mac, cloud, mobile, or ICS substrates, additional research is required. The gaps in Section B are precise.
3. **The corpus is dated 2026-06-02.** Cost models (Anthropic SDK Jun 15 2026 pricing), tool versions, vendor product releases, and the MCP spec revision (2025-11-25) will drift. Treat the corpus as a snapshot.

### Recommended first-read order for a fresh design-phase agent (this is the verbatim text the README points to)

Read `STRATEGY.md` first (one page — the wedge). Then `context/README.md` (the topical map). Then this file (Section F, the read-paths). Then dive in this order: `domain/01-dfir-foundations.md` (the mental-model spine — every other doc reads better after this), `user/09-ir-consultant-reality.md` (the user reality — every design decision is a tradeoff measured against this), `competitive/11-reference-implementations-decomposed.md` Sections 1 + 2 (the Protocol SIFT baseline and Valhuntir-decomposed — the published quality bar, so you know what you're competing against), `stakeholders/12-judges-curriculum-and-legal-landscape.md` Part A (judge personas — who weights what), `technical/07-mcp-and-agent-platforms.md` Parts A + C (MCP primitives + Claude Agent SDK — the substrate decisions live here), `technical/08-llm-failure-modes-in-agentic-systems.md` (failure modes — defenses are downstream of knowing the failures), `evaluation/10-datasets-and-evaluation-methodology.md` Parts A + E + G (datasets you might eval against + baseline establishment + the 13 pitfalls). At this point you have enough to write SPEC.md. Then return to the encyclopedia docs (`02`, `03`, `04`, `05`, `06`) as reference material during implementation phase — they are too dense to read end-to-end and are designed to be looked up by topic. `reference/13-source-corpus.md` is consulted only when you need to verify the exact wording of a quoted source.

### Read-paths for specific design tasks

**If you're picking the persistence layer for the case state / report state:** read `competitive/11` §2 (Valhuntir's JSONL-per-backend approach), then `domain/01` §10 (operational chain of custody), then `stakeholders/12` C6 + C16 (legal chain of custody + the FRE 707-anticipated audit trail framework). The "should it be HMAC-signed" question is downstream of these three together.

**If you're picking the report format / structure:** read `user/09` Part D (report anatomy + audiences) first, then `competitive/11` §2 finding-schema sections (how Valhuntir structures findings), then `domain/01` §9 (multi-artifact corroboration patterns — these are what report claims should reference). Skim `stakeholders/12` D6 (cross-examination playbook) for the survival test.

**If you're picking the agent framework / loop shape:** read `technical/07` Part C (Claude Agent SDK depth), then `technical/08` §9 (agentic loop failures — what the loop must defend against), then `competitive/11` §2 hook architecture (how Valhuntir wires Pre/PostToolUse + UserPromptSubmit). The "raw Agent SDK vs Claude Code as host vs framework" decision is downstream of these.

**If you're picking the tool surface (which forensic tools the agent calls):** read `domain/06` §15 (canonical tool chains) and §16 (what's missing on stock SIFT), then `domain/06` §1.1 (Volatility 3) + §5 (EZ tools) + §7.1 (Hayabusa) — these are the three most likely high-value tool surfaces. Cross-check against `competitive/11` §2 (Valhuntir's wintools-mcp + sift-mcp tool exposure) for the published baseline.

**If you're picking the evaluation methodology:** read `evaluation/10` Part A (datasets, choosing one with low LLM-memorization risk), Part D (metric families), Part E (baseline establishment), Part G (pitfalls). VIGIA is unavailable; plan for hand-encoded ground truth.

**If you're scoping the demo:** read `STRATEGY.md` §"What the demo must show", then `reference/13` Part A (Rob's writing — match his exact vocabulary), then `stakeholders/12` Synthesis-of-judge-psychology section. The "8-12 hour engagement → 25-minute agent run" framing is Rob's; SilentWitness's demo should respect that target shape.

**If you're handling the anti-hallucination / defensibility positioning:** read `technical/08` §1 (hallucination taxonomy) + §10 (DFIR-specific failure modes) + `competitive/11` §8 (anti-hallucination patterns from outside DFIR) + `stakeholders/12` C15 + C16 (black box problem + audit trail). The phrase "verifiable claim" should mean something concrete by the time you finish this read.

### A final operational rule

When you encounter a tension between two docs in this corpus, **prefer the more specific doc**. If `domain/02` says one thing about Prefetch and `domain/06` says another, the artifact-specific doc (`02`) wins for facts about Prefetch; the tool-specific doc (`06`) wins for facts about how PECmd parses Prefetch. If you encounter a tension that doesn't resolve this way, flag it in the build's NOTES file rather than picking arbitrarily.

The corpus is a snapshot. The build is downstream. Use what's here, surface what's not, and don't fabricate.
