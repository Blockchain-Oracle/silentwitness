# Hackathon Builder Discourse — Find Evil! (as of 2026-06-02)

Snapshot taken **13 days before submission close** (Jun 15, 2026).
Method: GitHub repo + code search across `find-evil`, `protocol-sift`, `sift-sentinel`, `findevil.devpost.com` (50+ queries before rate-limit), Devpost public surface, WebSearch/WebFetch for X/Reddit/blog presence. Devpost gallery is unpublished — direct submission counts impossible. **Public GitHub repos are the primary visible signal.**

Headline: the public field is **large, well-formed, and stylistically saturated**. I found **60+ named hackathon-shaped public repos**, characterized the top **30** in depth, and read READMEs/architecture for **22**. ~85% follow the same recipe: Custom MCP server wrapping read-only SIFT tools + LLM-driven self-correction loop + spoliation-resistance hooks + audit JSONL. The reference platform (AppliedIR/Valhuntir, 73 stars) sets the de facto baseline everyone benchmarks against. **No court-admissibility wedge. No tier-1 analyst training wedge. No insider-threat / BEC wedge. No live-response / EDR wedge.**

---

## Public builds discovered (with characterization)

Top 32 hackathon-tagged repos sorted by signal-of-effort. Stars are nearly all 0 because Devpost discourages drive-by stars during judging. I use `size_kb` + push recency + README depth as effort proxies.

| Repo | Builder | Pattern | Wedge / Differentiator | Maturity | Size KB | Last commit |
|---|---|---|---|---|---|---|
| [AppliedIR/Valhuntir](https://github.com/AppliedIR/Valhuntir) | AppliedIR org | Multi-MCP gateway + OpenSearch indexing | **Reference platform** — 17 OpenSearch query tools, examiner portal, gateway auth, LLM-client-agnostic. The thing everyone else differentiates *against*. **73 stars, 15 forks** | Production-shape | 2,514 | 2026-05-16 |
| [elchacal801/valkyrie](https://github.com/elchacal801/valkyrie) | elchacal801 | Custom MCP + Claude Code | **Structured Analytical Reasoning (ACH)** adapted from US IC doctrine; 3-tier evidence labels CONFIRMED/INFERRED/UNVERIFIED; **host+cloud (Entra ID/M365)** | Functional — 81 tests, sample reports, accuracy report | 10,847 | 2026-06-01 |
| [saivarun3407/DFIR-AI](https://github.com/saivarun3407/DFIR-AI) (MemoryHound) | saivarun3407 | Custom MCP + Claude Code skills/agents/hooks + LangGraph FSM | "Drop-in DFIR for Claude Code"; **31 typed tools / 14 skills / 4 subagents / 5 hooks / 20-node IR graph**; SHA256-chained audit; multi-framework (NIST/ISO/PICERL/ATT&CK/D3FEND) | Production-shape — 360 tests CI green, ~10K LoC | 740 | 2026-05-30 |
| [TimothyVang/Verdict](https://github.com/TimothyVang/Verdict) | TimothyVang | Mode-aware dual-LLM verifier-gateway | **Two AI models cross-check each other** (Qwen3 vs GLM-4.5-Air); HMAC-signed audit; FOR500 ≥2-artifact citation rule; **cloud/airgap/dual modes locked at case_init** | Functional, structured build plan | 2,064 | 2026-05-25 |
| [WooYoungSang/warvis-findEvil](https://github.com/WooYoungSang/warvis-findEvil) (W.A.R.V.I.S.) | WoopsFactory | Go orchestrator + Python MCP + Gemma 4 (local Ollama) | **Single Go binary control plane**; 5-state Hunt FSM with **compile-time tool whitelist**; budget-preserving resume + kill-switch; airgap focus | Production-shape | 42,724 | 2026-05-09 |
| [Hokutoman00/foveal-dfir](https://github.com/Hokutoman00/foveal-dfir) | Hokutoman00 | Custom MCP, **structurally different verifier** | **Blind independent grader** (sees raw evidence only, no anchoring); **N≥2 distinct sources counted in code** to reach CONFIRMED; quarantines instruction-like embedded text; **`MACHINE_PACED` vs `HUMAN_LIKELY` cadence detector for GTG-1002 attacker** | Functional — 13 verifier modules, ROCBA case validated (4,818 findings analyzed) | 3,350 | 2026-05-30 |
| [Nafsgerman/siftguard](https://github.com/Nafsgerman/siftguard) | Nafsgerman | Custom MCP, **5 orchestrators on 1 typed MCP** | Court-defensible framing; 19-col SQLite auditentry; **15/15 spoliation tests**; real F1 across 3 datasets; LLM-agnostic | Production-shape — demo video uploaded, Devpost link live | 6,057 | 2026-06-01 |
| [WilBtc/find-evil-sleuth](https://github.com/WilBtc/find-evil-sleuth) | WilBtc | **Postgres-substrate multi-agent** | **Postgres 17 + 11 extensions (pgvector, Apache AGE, TimescaleDB, pgaudit, pg_jsonschema)**; Rust broker; rootless podman + seccomp; BLAKE3 hashes; live judge `SELECT` queries during demo | Production-shape | 14,009 | 2026-06-02 |
| [chang6chang/SIFT-Guard](https://github.com/chang6chang/SIFT-Guard) | chang6chang | Custom MCP + analyst/validator subagents | "Autonomous iterative self-correction with cross-validation"; validator subagent has **deliberately restricted tool surface**; 4 hash-chained JSONL logs | Functional — 23 MB repo, setup script, mock-run mode | 22,886 | 2026-05-20 |
| [vinodhalaharvi/provenance](https://github.com/vinodhalaharvi/provenance) | vinodhalaharvi | **Go-native typed arrows** (no MCP) | Replaces "LLM + execute_shell_cmd + prompt" with **typed Go structs** — "misconfigurations are not expressible"; deterministic Go coordinator; multi-agent w/ independent critic | WIP — 25 unit tests, fixture-driven | 54 | 2026-05-13 |
| [aliyaalias19/glaive](https://github.com/aliyaalias19/glaive) (GLAIVE) | aliyaalias19 | **Typed evidence graph** + Custom MCP | "Hallucination architecturally impossible" — every finding must correspond to a path in a typed evidence graph; 327 tests passing; **5 bypass attack tests** | Functional | 220 | 2026-05-29 |
| [Lona44/find-evil-ir-agent](https://github.com/Lona44/find-evil-ir-agent) | Lona44 | **Multi-agent LangGraph** + misalignment-eval layer | Investigator → Validator → Reporter pipeline; "fabricated artefact citations" framed as the moat | Scaffold (declared) | 20 | 2026-05-21 |
| [tejasprasad2008-afk/evidencechain](https://github.com/tejasprasad2008-afk/evidencechain) | tejasprasad | Custom MCP, 21 typed tools | **7 contradiction detectors** named (`TIMESTAMP_PARADOX`, `EXECUTION_OVERCLAIM`, `GHOST_PROCESS`...); 4-pass self-correction; "Proves" column distinguishes execution from presence | Functional | 144 | 2026-04-22 |
| [marez8505/sift-sentinel](https://github.com/marez8505/sift-sentinel) | marez8505 | Custom MCP + skills | Self-correcting triage; Protocol SIFT baseline extension; co-located install with PSIFT_DIR | WIP | 106 | 2026-04-22 |
| [MukundaKatta/sift-sentinel](https://github.com/MukundaKatta/sift-sentinel) | MukundaKatta | Custom MCP, simulated backend | Runs offline w/ no API key — "60-second proof"; SHA-256 ledger; SANS Find Evil playbook walked deterministically | Functional | 304 | 2026-05-29 |
| [vandit98/sift-sentinel](https://github.com/vandit98/sift-sentinel) | vandit98 | Custom MCP, "Architecture Pattern: Custom MCP Server" | Self-correcting triage + EvidencePolicy guard + accuracy benchmark; clean Vercel project page | WIP | 200 | 2026-05-01 |
| [scastile/sift-sentinel](https://github.com/scastile/sift-sentinel) | scastile | Custom MCP | Generic "FIND EVIL submission" framing | Stub-WIP | 46 | 2026-06-01 |
| [FlemingJohn/sift-sentinel](https://github.com/FlemingJohn/sift-sentinel) | FlemingJohn | MCP server suite + orchestration + terminal UI | "TUI for forensic IR" angle | WIP | 479 | 2026-06-02 |
| [MuneebX65/protocol-sift-agent](https://github.com/MuneebX65/protocol-sift-agent) | MuneebX65 | Custom MCP, "safe typed functions" | "PROTOCOL SIFT — AI Incident Response Agent" banner | WIP | — | 2026-05-05 |
| [Forenly/protocol-sift-dfir](https://github.com/Forenly/protocol-sift-dfir) | Forenly | MCP, **cyber-physical robot forensics** | Compromised ROS 2 robots, SLAM logs, motion control overrides; cross-leverages Splunk Agentic Ops + UiPath Maestro entries | WIP, public Discord | 33 | 2026-05-30 |
| [kdsecdev/Aura-Forensics](https://github.com/kdsecdev/Aura-Forensics) | kdsecdev | Custom MCP, **Triangulation Engine** | **DKOM / unlinked-EPROCESS rootkit detection** — cross-reference pslist vs psscan; finds malware Volatility `malfind` misses; 19 GB memory dump physical scrape | WIP, but compelling demo case | 3 | 2026-05-16 |
| [aksoni/sift-bench](https://github.com/aksoni/sift-bench) | aksoni | Custom MCP + Claude Code | **Benchmark + eval framework first, agent second**; scores false-positive retractions and **negative assertions** ("certain behaviors did NOT occur"); deterministic replayable scorer w/ committed LLM-judge verdict cache | Functional — Run 6: 5/5 critical, 3/3 FP traps, 0.9833 score | 1,313 | 2026-06-01 |
| [annatchijova/vigia-cases](https://github.com/annatchijova/vigia-cases) | annatchijova | **Dataset only** | **10 real DFIR cases** (NIST CFReDS, DFRWS, Digital Corpora, Ali Hadi, Volatility Foundation) in canonical VIGÍA format w/ ground truth, IOCs, MITRE TTPs, **Peirce semiotic classification**; reports "classification applied by Rob T. Lee" | Functional — public, Apache-2.0 | 40 | 2026-05-29 |
| [Vasanthadithya-mundrathi/SANS-FIND-EVIL](https://github.com/Vasanthadithya-mundrathi/SANS-FIND-EVIL) (ProofSIFT) | Vasanthadithya | Custom MCP | "Evidence-gated autonomous DFIR" | WIP | 90 | 2026-05-12 |
| [voidd0/tracelock-find-evil](https://github.com/voidd0/tracelock-find-evil) | voidd0 | Read-only harness | Per-finding {event_id, tool, confidence, SHA-256 hash, self-check, final status}; includes **`splunk-ops/` extension** with 3-case Splunk accuracy suite (all P=R=1.0); public Devpost demo URL | Functional | — | 2026-05-16 |
| [Turbo31150/find-evil-jarvis](https://github.com/Turbo31150/find-evil-jarvis) | Turbo31150 | **Parallel multi-agent** (asyncio.gather) | 4 specialist agents (IOC / phishing / malware-pattern / log-anomaly) in <100ms; FastAPI | Functional but **archived** | — | 2026-05-28 |
| [jasmine-erkel/sift-autopilot](https://github.com/jasmine-erkel/sift-autopilot) | jasmine-erkel | Claude Code + MCP wrappers | Volatility 3 + Sleuth Kit + log2timeline | WIP | 53 | 2026-04-21 |
| [Prathameshsci369/ThreatPipe-v2-Autonomous-SIFT-IR-Agent-with-MCP](https://github.com/Prathameshsci369/ThreatPipe-v2-Autonomous-SIFT-IR-Agent-with-MCP) | Prathameshsci369 | LangGraph + Custom MCP | **4-Lens cross-referencing** (Hacker / Temporal / Kill Chain / Analyst); persistent "Hacker Mindset Graph"; predicts next ATT&CK move; Mistral backend | WIP | 779 | 2026-05-28 |
| [TimothyVang/sans-hackathon](https://github.com/TimothyVang/sans-hackathon) | TimothyVang | Investigation assistant | — | WIP | — | 2026-05-22 |
| [Vasanthadithya-mundrathi/SANS-FIND-EVIL](https://github.com/Vasanthadithya-mundrathi/SANS-FIND-EVIL) | (dup) | — | Already listed | — | — | — |
| [sgharlow/find-evil](https://github.com/sgharlow/find-evil) | sgharlow | Custom MCP | **Evidence Integrity Enforcer** — background daemon re-hashes every 30s + before every tool call; UUID-linked audit; DRS confidence gate | Production-shape | 61,774 | 2026-06-01 |
| [Forenly/protocol-sift-dfir](https://github.com/Forenly/protocol-sift-dfir) | Forenly | (dup) | — | — | — | — |
| [daideguchi/evidence-locked-dfir-agent](https://github.com/daideguchi/evidence-locked-dfir-agent) | daideguchi | Human-approval workflow | Live demo GitHub Pages; "AI claims must stay tied to artifacts and human approval" | WIP | — | 2026-05-20 |
| [AI-Nikitka93/find-evil-caseproof-analyst](https://github.com/AI-Nikitka93/find-evil-caseproof-analyst) | AI-Nikitka93 | Custom MCP, bounded scope | Honest scope: "narrow auditable path, not full reconstruction"; bounded CASE-RD01 evidence pass; explicit GO/NO-GO gating | WIP, honest | — | 2026-05-07 |
| [jechaviz/find_evil_sans_agentic_ir](https://github.com/jechaviz/find_evil_sans_agentic_ir) | jechaviz | V (Vlang!) CLI | Read-only triage; fixture suite + benchmark; negative-control hallucination check; MITRE/evidence-tier fields | WIP — unusual language | — | 2026-05-30 |
| [cheng-lin-max/sift-self-correction-agent](https://github.com/cheng-lin-max/sift-self-correction-agent) | cheng-lin-max | Self-correcting agent | (Shell) | WIP | 1,120 | 2026-06-02 |
| [Cayton-Tech/find-evil](https://github.com/Cayton-Tech/find-evil) | Cayton-Tech | Generic SIFT agent | — | WIP | 46 | 2026-05-31 |
| [Nafsgerman/siftguard](https://github.com/Nafsgerman/siftguard) | — | (dup) | — | — | — | — |
| [DithetoMash/sift-mcp-server](https://github.com/DithetoMash/sift-mcp-server) | DithetoMash | Custom MCP | Typed read-only wrappers + self-correcting loop | WIP | — | 2026-05-10 |
| [Louicamu/find-evil](https://github.com/Louicamu/find-evil) | Louicamu | Multi-agent | Self-correction + cross-artifact correlation | Stub | 72 | 2026-05-17 |
| [iffystrayer/find-evil-agent](https://github.com/iffystrayer/find-evil-agent) | iffystrayer | Generic SIFT agent | (Very large repo, 191MB — heavy assets) | Production-shape | 191,530 | 2026-05-27 |
| [Basit-Balogun10/find-evil](https://github.com/Basit-Balogun10/find-evil) | Basit-Balogun | — | Has full `docs/competition.txt` — read of the rules | WIP | — | 2026-05-02 |
| [mcp97/find-evil-sift-triage-loop](https://github.com/mcp97/find-evil-sift-triage-loop) | mcp97 | Custom MCP | "Evidence-safe SIFT-style triage loop" | WIP | 32 | 2026-05-11 |
| [umfhero/Forensic-AI](https://github.com/umfhero/Forensic-AI) | umfhero | Multi-person team (Yasmine/Jurgen/Khalid/Mauro/Majid) | Has per-member task files; **explicit EU AI Act + GDPR compliance research item** | Active team WIP | — | — |
| [samaritan0/dfir-agentic-suite](https://github.com/samaritan0/dfir-agentic-suite) | samaritan0 | Claude skills + 4 MCP servers | 5 forensic skills, IOC extractor, Windows artifacts, timeline merger, YARA gen; **9 stars, 4 forks** (highest after Valhuntir) | Functional, declared WIP | 107 | 2026-03-24 |

Additional repos found but lower-effort (stub, no README, or generic placeholder): `dhyabi2/findevil`, `swattyy/REAGENT-preview`, `benjamenhoffman/sift-sentinel`, `benjamenhoffman/evilhunter`, `kevin9327/protocol-sift-sentinel`, `Asher94/turbo-bengal`, `prakash023-hub/sift-analyst`, `0xshivangpatel/nighteye`, `yuzengbaao/find-evil-agent`, `leonongoing/find-evil-agent`, `Lona44/...`, `gap-yuta-inoue/find-evil`, `mowen628/sift-mcp`, `nurusyda/casefile`, `Hokutoman00/foveal-dfir` (counted), `macbere/nexus-ir`, `andretsche-ship-it/artar-fe`, `MukundaKatta/protocol-sift-agent`, `audin30/vbg-sans-find-evil-ai-agent`, `Awesomeav23/Find_Evil_Hackathon`, `laok775/hackathon-find-evil`, `kostasuser01gr/FindEvil-CyberSecurity`, `JafarBanar/findevil`, `marez8505/find-evil`, `dianaloveava/eviltrace-find-evil`, `gongahkia/kelp`, `Juwon1405/agentic-dart`, `mako1633-sketch/ORPHEUS`, `ShyamAlancode/echo-dfir`, `VietGamer-UIT/TaxLens-AI`, `charanbobby/sift-sentinel`, `zenithVeil/find-evil-agent`, `useaima/sentinel`, `sassom2112/veritas`. Plus 15+ unnamed stubs.

**Conservative public-build count: ~60 GitHub repos.** Devpost gallery is hidden, so true submission count is unknown — but with 3,861 registered and historical hackathon completion ~5-15%, expect **~200-580 final submissions**, of which perhaps 40-80 will be polished.

---

## Architectural pattern distribution

Across the 30 builds where I read the README:

| Pattern | Share | Examples |
|---|---|---|
| **Custom MCP server (typed read-only forensic tool wrappers)** | **~85%** | valkyrie, MemoryHound, siftguard, sift-sentinel × N, evidencechain, GLAIVE, foveal, sgharlow |
| **Multi-agent / LangGraph** | ~30% (often layered on Custom MCP) | find-evil-ir-agent (LangGraph), valkyrie, Verdict, ThreatPipe v2, find-evil-jarvis |
| **Direct Extension of Protocol SIFT (skills + hooks, no custom server)** | ~15% | MemoryHound (`.claude/` PAI pattern), samaritan0/dfir-agentic-suite, several stubs |
| **IDE / agentic-framework based (Claude Code / Claude Desktop only)** | rare | Most include some MCP layer; pure Claude Code skills minority |
| **Novel substrate / not MCP** | ~5% | vinodhalaharvi/provenance (Go typed arrows), warvis (Go FSM gateway), find-evil-sleuth (Postgres substrate) |
| **Dataset / benchmark only** | ~5% | vigia-cases (10 cases), sift-bench (eval framework w/ ref impl), aksoni/sift-bench |

**The default recipe is dead obvious to every builder**: read Protocol SIFT's POC → notice it gives the LLM raw `execute_shell_cmd` → wrap each SIFT tool as a typed MCP function → bolt on a self-correction validator → claim "architectural" guardrails. This is the line every README repeats almost verbatim.

---

## Wedge / angle distribution

What every public build is racing to claim. Heavy clustering at the top, almost nothing at the bottom.

### Over-represented (saturated)
| Wedge | Count of public builds claiming it |
|---|---|
| **Custom MCP server with typed read-only tools** | ~25 |
| **Self-correction / validator loop** | ~22 |
| **Spoliation resistance / SHA-256 evidence sealing** | ~18 |
| **Hash-chained or JSONL audit trail** | ~15 |
| **Architectural (not prompt-based) guardrails** | ~14 |
| **Hallucination-prevention via citation enforcement** | ~12 |
| **MITRE ATT&CK / sub-technique mapping** | ~10 |
| **Two-agent investigator/validator split** | ~9 |
| **Multi-agent LangGraph pipeline** | ~8 |
| **Confidence scoring + retract/promote rules** | ~8 |
| **Replayable / deterministic / no-API-key offline mode** | ~6 |

### Moderate
| Wedge | Count |
|---|---|
| **Benchmark / accuracy framework as primary deliverable** | 3 (sift-bench, vigia-cases, voidd0 tracelock-ops) |
| **Negative-assertion scoring ("did NOT occur")** | 1-2 (aksoni/sift-bench explicitly) |
| **Dual-LLM cross-check (different model families)** | 2 (Verdict, partially Lona44) |
| **Local-only LLM (Ollama, Gemma, Mistral)** | 4 (warvis, ThreatPipe, Aura-ish, sift-sentinel offline) |
| **Cross-OS (Windows + macOS + Linux artifacts)** | 2 (MemoryHound, samaritan0/dfir-agentic-suite) |
| **Adversary-cadence detection ("is this AI or human attacker?")** | **1 (Hokutoman00/foveal-dfir)** |
| **Cloud-plane forensics (Entra ID / M365 / Azure)** | 1 (valkyrie) |
| **Tier-1 SOC / Splunk operator workflow** | 1 (voidd0 splunk-ops extension) |
| **Live-system EDR-style response** | 0 visible |

### Absent or near-absent (open lanes)
| Wedge | Public builds |
|---|---|
| **Court-admissibility / Daubert / FRE 901 framing** | 0 public, 1 (Nafsgerman) uses the phrase "court-defensible" but no actual legal-rule mapping |
| **EU AI Act / GDPR compliance evidence for AI-derived findings** | 1 mention (umfhero/Forensic-AI has it as a research task — not implemented) |
| **Examiner notes / chain-of-custody form-fill (FBI/EnCase-style)** | 0 |
| **BEC / M365 unified audit log triage** | 0 (separate ecosystem of BEC tools exists but none target Find Evil) |
| **Insider threat / data-exfil specific** | 0 |
| **Live-host / live-response (Velociraptor-shape)** | 0 |
| **Cyber-physical / OT / robotics forensics** | 1 (Forenly — but Discord-led, narrow) |
| **Cloud-only forensics (no host disk image at all)** | 0 |
| **Mobile / iOS / Android** | 0 |
| **Network-only forensics (PCAP-first, no host)** | 0 |
| **Cost-aware / token-budget-optimal agent loop** | 0 (warvis has budget *resume*, not budget *minimization*) |
| **Specific known-bad operator catalogs (LOLBAS-driven, Atomic Red Team replay validation)** | 0 |
| **Real-time stream (Kafka/Splunk live tap, not disk image)** | 0 |
| **Adversary-emulation pair: attacker agent + defender agent in same repo** | 0 |
| **Multi-host correlation across an org (not single-host)** | 0 — siftguard claims "multi-host" but it's serial hosts in one case |
| **Hardware / firmware / UEFI rootkit detection** | 0 |
| **Privacy-preserving forensics (responder cannot see employee PII unless evidence)** | 0 |
| **Plain-English explanation for non-technical executives / GC** | 0 |
| **Cost-of-investigation report (was $X spent, would have cost analyst $Y hours)** | 0 |

---

## Community signal

**Star counts are essentially zero** across the field — only AppliedIR/Valhuntir (73), samaritan0/dfir-agentic-suite (9), AppliedIR/sift-mcp (8), vigia-cases (1), vinodhalaharvi/provenance (1). The signal "0 stars, real effort" is correct: Devpost actively discourages drive-by promotion during judging windows. Effort signal must come from repo size + push recency + README depth.

**Reddit:** No discoverable r/computerforensics, r/cybersecurity, r/AskNetsec, or r/SANS threads about Find Evil or Protocol SIFT in the indexed window. Either the community is in private Slack only or DFIR Twitter is doing the discourse.

**X / Twitter:** WebSearch returns the official Rob T. Lee announcement tweet (Apr 15 launch — "1,400 solo builders and teams registered as of this morning") and the Devpost promo. No surfaced builder devlog threads. WebFetch on Rob Lee's pinned tweet hit auth wall.

**LinkedIn:** No public posts discoverable via web search. Likely the bulk of practitioner-side discourse is happening here but behind login.

**YouTube:** Devpost rule requires demo videos be public on YouTube/Vimeo/Youku. As of Jun 2, the only one I confirmed live: **Nafsgerman/siftguard at https://www.youtube.com/watch?v=ALmArb3lGR8 (4:42 demo)**. Several READMEs say "Recording in W6 (May 31 – Jun 6, 2026)" — expect a flood of demo videos in the next 7-10 days.

**Discord (HP4BhW3hnp):** Forenly's README links a separate Discord (`discord.gg/qzs8PraeXS`) for their cyber-physical team. Suggests the official Protocol SIFT Slack is where the discourse lives — invite-gated, not surveyable.

**SANS instructor amplification:** Rob T. Lee Substack ([robtlee73.substack.com](https://robtlee73.substack.com/p/registration-is-open-find-evil-hackathon)) is the official builder communication channel. He has 2 launch posts. Ethan Troy's `unpromptedcon-2026-slides` repo has slides on Claude Code + SIFT DFIR. No surfaced practitioner shoutouts of specific submissions.

---

## Specific quotes from public builder posts

> "Protocol SIFT works. It also hallucinates more than we'd like. (That's exactly why this hackathon exists.) Unlike offensive teams that operate with three or four people in secret, we're putting the entire practitioner community on this problem simultaneously. Your job: teach an AI agent to think like a senior analyst — how to sequence its approach, recognize when something doesn't add up, and self-correct when it gets it wrong."
> — `Basit-Balogun10/find-evil/docs/competition.txt` (quoting the official brief)

> "Most forensic AI agents are tool runners — they wrap forensic tools behind an LLM and execute them in sequence. VALKYRIE is an analytical reasoner — it applies structured analytic techniques adapted from US Intelligence Community doctrine to investigate incidents with hypothesis testing, evidence tiering, and multi-layer self-correction."
> — elchacal801, **VALKYRIE README**

> "ALWAYS verify results and guide the investigative process. If you just tell Valhuntir to 'Find Evil' it will more than likely hallucinate rather than provide meaningful results. The AI can accelerate, but the human must guide it and review all decisions."
> — AppliedIR, **Valhuntir README** (the reference platform itself disclaims the autonomy framing)

> "The hackathon names its own open problem: an autonomous DFIR agent that 'just says find evil' hallucinates and needs a human to guide it. We take that at face value — the failure mode is self-deception — and answer it structurally rather than with more careful prompting. Most submissions build a 'more careful' agent. We build a structurally different one."
> — Hokutoman00, **foveal-dfir README**

> "Existing AI-assisted DFIR tooling (Protocol SIFT and similar) gives an LLM agent a generic `execute_shell_cmd` plus a long system prompt and hopes it stays on the rails. The hackathon brief flags this as the source of the autonomy gap: hallucination, evidence spoliation risk, loops that don't terminate."
> — vinodhalaharvi, **provenance README**

> "Most agentic DFIR demos run an agent and show the output. SIFT-Bench does three things that most won't: A benchmark that scores analytical reasoning, not just discovery. Ground truth includes severity-weighted findings, false-positive traps... and **negative assertions** ('certain behaviors did NOT occur')."
> — aksoni, **sift-bench README**

> "GLAIVE makes hallucination architecturally impossible by forcing every finding to correspond to a path in a typed evidence graph."
> — aliyaalias19, **GLAIVE README**

> "The architectural guardrail is not a system prompt — it is a Bash PreToolUse hook that exits 1 on any command other than `./bin/sb` or `./bin/es`, enforced at the Claude Code hook layer before the shell sees the command."
> — WilBtc, **find-evil-sleuth README**

> "An AI-powered adversary can go from initial access to full domain control in under 8 minutes... Find Evil! challenges you to build an AI defender that keeps pace with a 7-minute attack."
> — Rob T. Lee, Substack (the framing every builder echoes)

**The pattern of the discourse:** every README opens with the same diagnostic ("Protocol SIFT hallucinates, gives LLM raw shell, fails autonomy") and the same prescription ("typed MCP + self-correction + audit"). The builds differ in *how* they make the guardrail architectural — typed Go structs, FSMs, evidence graphs, Postgres rows, hook layers, blind graders, dual-LLM verifiers — but the conceptual wedge is essentially shared.

---

## Gaps in the visible field

Angles **no public builder has staked**, ranked by my confidence the lane is open:

1. **Court-admissibility and Daubert/FRE 901 mapping for AI-derived findings.** Nafsgerman uses "court-defensible" once but it's marketing, not a mapping. Nobody outputs a Rule 901 authentication packet, nobody produces an expert-witness report shape, nobody addresses the AI judge-explainability problem. **Truly open.**

2. **Tier-1 SOC analyst as the user, not the senior analyst.** Every build is racing to be "the senior analyst replacement." Nobody builds the **trainee co-pilot** that explains *why* a finding matters and asks the analyst to confirm — turning the agent into an upskilling tool. **Open.**

3. **Cost / token-economic optimization as a first-class metric.** Warvis has resume to preserve budget on interrupt. Nobody has the wedge "investigate the same case for 10x less LLM cost." Given Devpost rules permit Claude Code + Max sub, this is unsexy but real.

4. **Live response (Velociraptor / Falcon shape) instead of disk image.** Everyone assumes a captured E01 + memory dump. Nobody is doing the "agent runs on a live infected host and decides what to collect" angle. SIFT toolchain biases toward post-acquisition, but the brief never required it.

5. **Adversary-pair: include the attacker agent and demo defender catching it.** The hackathon's stated motivation is Anthropic's GTG-1002 — an autonomous attacker. Nobody ships their own toy GTG agent + lets their defender hunt it. foveal-dfir gets close with `MACHINE_PACED` cadence but doesn't actually emulate an attacker.

6. **Multi-host correlation across a realistic org (10+ hosts, 1 case).** All builds investigate 1 host or "host + DC + 2 workstations" SRL-style. Nobody handles "37 endpoints triaged in parallel, this one is the patient zero" — which is actual SOC-shape work.

7. **Cloud-only / SaaS / identity-plane only.** valkyrie touches Entra ID. Nobody does the wedge "no disk image — agent investigates only M365 UAL + Entra logs + Defender XDR exports."

8. **BEC / financial fraud investigation shape.** Whole separate BEC tool ecosystem exists (PwC-IR, SagaLabs, ForensicFoundry) — zero overlap with Find Evil submissions.

9. **Insider-threat / data-exfil narrative shape (DLP-flavored).** Different acceptance criteria than "find the C2 IP" — needs HR/legal-grade narrative.

10. **Mobile (iOS/Android) DFIR.** SIFT Workstation has Cellebrite-style readers; nobody is using them.

11. **Hardware / UEFI / firmware rootkit detection.** Aura-Forensics gets close with DKOM but stays in OS-level memory. UEFI is a wedge.

12. **Privacy-preserving / minimum-viewing forensics.** No build addresses "responder cannot see employee email contents unless they become evidence." Real concern in EU.

13. **Plain-English executive / GC summary as primary output.** All reports are forensic-technical. Nobody ships "the version you give the CEO."

14. **A reproducibility / replay-bit-exact-CI focus.** sift-bench gets closest. Nobody else makes the wedge "every claim in our report can be regenerated bit-exact from evidence in <5 min."

---

## Strategic implication for our wedge

The visible field is a **single, dense cluster around "Custom MCP server + typed read-only tools + self-correction validator + hash-chained audit"**, with two notable variants pushing further (typed evidence graphs, dual-LLM cross-check). Every README's "what makes us different" section is fighting over essentially the same 15-square-meter plot. The reference platform (Valhuntir) already exists at 73 stars and has shipped most of the spoliation/audit/governance story. **Builds that try to beat Valhuntir at "more tools, better audit, tighter MCP" are entering the most crowded lane and losing the differentiation game before they start.**

The cleanest open lanes are (a) **court-admissibility / Daubert authentication of AI findings** — zero builders, judge Rob T. Lee actively cares about the defensibility framing per SANS press materials, and it converts the spoliation/audit story everyone has into legal-grade output rather than a technical claim; (b) **adversary-pair demonstration** — directly addresses Anthropic GTG-1002 which is the hackathon's literal origin story, and a working attacker agent in the same repo is irresistible to demo judges; (c) **tier-1 analyst trainee co-pilot** — flips the wedge from "replace the senior" to "manufacture 100 more juniors," which maps to SANS's own training-business interest. Of the 10 lettered wedges A-J in our internal shortlist, the one most clearly **least saturated** based on this scan is whichever one points at **legal/Daubert defensibility** or **adversary-emulation pair**; the one most clearly **already saturated** is any flavor of "more tools / better self-correction / cleaner audit."
