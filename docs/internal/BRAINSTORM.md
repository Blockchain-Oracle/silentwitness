# BRAINSTORM — Approved Architecture for SilentWitness

> Brainstorming-phase output. v2, approved by Abu 2026-06-02.
> This document is the design baseline for the spec-writing phase.
> Architecture decisions live here; specs implement them.
> Wedge in `../STRATEGY.md`. Domain knowledge in `../context/`.

---

## §1 — The wedge (one paragraph, locked)

We are building **SilentWitness** — a hypothesis-first IR investigator that drafts its own structured incident report as the case unfolds, with every claim verifiably linked to the tool execution that produced it. The user is the senior IR consultant who currently spends ~half their billable time running tools by hand and writing the report afterward. The headline metric is **time to handoff-ready incident report** on a representative forensic case. Architecture must be model-agnostic to match the published quality bar (Valhuntir). Full wedge commitment in `../STRATEGY.md`.

---

## §2 — Verified rules + platform constraints

From three verification passes (results in `../context/.raw-design-research/`):

### Rules verification (`01-rules-model-agnostic-verification.md`)
- **Custom MCP Server is explicitly labeled "the most sound architecture in the evaluation."** (verbatim, Devpost overview, approach #2 of 4)
- Model-agnostic MCP servers ARE permitted. Valhuntir (the bar) is itself LLM-client agnostic — model-agnosticism is the floor, not above-and-beyond.
- The §4 Platforms requirement ("Claude Code or OpenClaw as the agentic framework") is satisfied by shipping a Claude Code config alongside the server; nothing prevents the server from also supporting other clients.
- 3 of 6 judging criteria (Constraint Implementation, Audit Trail Quality, Usability) directly reward architectural / model-agnostic enforcement.
- Catch-all verbatim: *"If another agentic framework can do the job, we won't disqualify it."*
- Devpost FAQ / discussions / NotebookLM / Slack are gated — no contradicting public Q&A exists.

### SIFT 2026 verification (`03-sift-2026-tool-catalog-verified.md`)
- **Ubuntu 24.04.2 Noble + Python 3.12 + user `sansforensics`**
- **Claude Code v2.0.61 ships pre-installed** at `/usr/local/bin/claude` — judges can demo with zero setup
- **EZ Tools pre-installed** via dotnet 9 SDK at `/opt/zimmermantools/` (MFTECmd, EvtxECmd in `/opt/zimmermantools/EvtxeCmd/`, AmcacheParser, etc.) — ~15 EZ Tools available
- **Docker + docker-compose 2.32.4 pre-installed** — enables containerized deploy
- **Volatility 3 at `/opt/volatility3/bin/vol`** (NOTE: earlier docs cited `/opt/volatility3-2.20.0/vol.py` — wrong path; correct in our specs)
- **Pre-installed:** Sleuth Kit, libewf/libvshadow/libbde/libregf/libesedb/libevtx (gift PPA), bulk_extractor, YARA, ClamAV, RegRipper3.0 (`/usr/local/bin/rip.pl`), plaso-tools, Wireshark/tshark, PowerShell 7.4.6, AWS CLI 2.15.24, ~20 Python forensic tools in `/opt/<tool>/` virtualenvs
- **Must install:** Hayabusa, Chainsaw, Velociraptor, Zeek, Suricata, Node.js, `uv`, PECmd, SrumECmd, capa, FLOSS, binwalk, Sigma rule corpora
- **Gotcha: Apache binds port 80** for CyberChef — pick another port for any HUD
- **Gotcha: pip + virtualenv is default**, not uv — our install script bootstraps uv as a single binary

### Library landscape (`02-model-agnostic-agent-libraries-survey.md`)
- **Pydantic AI** (MIT, 17.5K stars, daily commits, native MCP, model-string provider switching, Hooks for audit, agent-delegation for subagents) — **chosen as agent loop**
- OpenAI Agents SDK — strong runner-up
- mcp-agent (LastMile) — conceptually purest but **STALE since 2026-01-25** — mine patterns, don't depend
- **AVOID:** LiteLLM as primary loop (3,537 open issues — use only as translator if needed), Open Interpreter (AGPL blocker), smolagents CodeAgent (LLM-authored Python over evidence = spoliation risk), LangChain/CrewAI/AG2 (overshoot)

---

## §3 — The seven architecture decisions (committed)

### Decision 1: High-level shape

**Approved: Custom MCP Server (Python) + Pydantic AI reference agent + Claude Code config layer.**

Three artifacts ship together:
1. **`silentwitness-mcp`** — the standalone MCP server package. This is the **product**. Usable by any MCP client (Claude Code, Claude Desktop, Cherry Studio, LibreChat, Continue, custom Python agents).
2. **`silentwitness-agent`** — the reference agent. Pydantic AI, model-string switchable. Shows how to use the server with the hypothesis-pivot loop and report-as-state. This is the **showcase**.
3. **`silentwitness-claude-code`** — drop-in `.claude/` directory configuring pre-installed Claude Code to point at the server. This is the **zero-setup judge convenience**.

**Why this shape:**
- Maps directly to rules approach #2 (Custom MCP Server — "most sound").
- Matches Valhuntir's LLM-agnostic bar.
- Server is the artifact judges score on Constraint + Audit (3 of 6 criteria).
- Agent loop is reference; not locked to provider.
- Pre-installed Claude Code on SIFT 2026 means judges can test via the §4-named framework with zero work.

**Rejected:**
- Direct Agent Extension only: loses Constraint criterion (prompt-only guardrails).
- Pure LangGraph / CrewAI: heavyweight, locks orchestration, overshoots our shape.
- Claude Agent SDK as primary loop: locks provider (Anthropic-only). We use Pydantic AI's agent-delegation primitive instead — provider-agnostic equivalent.

### Decision 2: Hypothesis-pivot engine

**Approved: plain Python state machine, ~200 LOC, no framework.**

- `Hypothesis` dataclass: `id`, `statement`, `status` ∈ {ACTIVE, CONFIRMED, PIVOTED, ABANDONED}, `formed_at`, `formed_from`, `evidence_expected`, `evidence_observed`, `assigned_specialist`, `tokens_budgeted`, `tokens_consumed`.
- `HypothesisStack`: manages active hypotheses, enforces token / step budgets, emits `HypothesisEvent` per transition.
- `HypothesisEvent` logged to `audit/hypothesis.jsonl`: `{ts, type ∈ {form, dispatch, confirm, pivot, abandon}, hypothesis_id, reason, related_audit_ids, tokens_spent}`.
- Used by the main investigator agent (lives in `silentwitness_agent/hypothesis/`).

**Rationale:** Demo gold (the pivot moments) lives here. We control rendering and audit completely. ~200 LOC fits the 400-line constraint with room. Zero framework cost. Trivially testable.

### Decision 3: Verifiability mechanism

**Approved: line-level citation + entity gate, hybrid.**

`record_observation(observation_text, cited_spans, audit_ids)`:
1. **Citation gate.** Each `cited_span` is `{audit_id, sha256_of_normalized_output, line_start, line_end, span_text}`. Server loads stored tool output for `audit_id`, verifies the SHA256 matches the cited hash (output integrity), verifies `span_text` is a verbatim substring of the cited line range. Mismatch → REJECTED with reason.
2. **Entity gate.** Server runs NER + regex over `observation_text` to extract entities (file paths, IPs v4/v6, MD5/SHA1/SHA256 hashes, registry keys, process names, account names, mutex names, email addresses, URLs, port numbers). Every extracted entity must appear in at least one cited span (case-insensitive substring match with path normalization). Hallucinated entity → REJECTED with the entity list.
3. **Storage.** Cited tool output is normalized (strip timestamps, normalize whitespace, normalize path separators) before hashing, so re-runs are byte-stable.

**Rationale:** Byte-level was brittle to tool nondeterminism. Line-level + entity gate gives the same architectural guarantee with robustness. Matches the cleanest prior art (Pydantic Instructor citation pattern + NABAOS execution-attestation extended to content-attestation).

### Decision 4: Report-as-state

**Approved: structured Markdown with frontmatter + inline `[verify:audit_id]` references; auto-saved on every transition; PDF export at handoff.**

- Single source-of-truth Markdown file per case at `cases/<case_id>/report.md`.
- YAML frontmatter: `case_id`, `examiner`, `created_at`, `updated_at`, `status` ∈ {DRAFT, REVIEWED, FINAL}, `content_hash`.
- Sections (FOR508-shaped): Executive Summary, Engagement Overview, Methodology, Findings (per host, per TTP), Timeline, IOCs, Recommendations, **Gaps** (epistemic honesty — what we couldn't verify), Appendix-Audit.
- Every claim references its provenance: `... PowerShell ran [verify:F-001/sift-001-20260602-007]`. The verify link resolves to the audit JSONL entry at render time.
- Auto-saved (atomic rename) on every staged Observation / Interpretation / Pivot.
- PDF export via WeasyPrint at examiner approval.

**Rationale:** Markdown is editable, diffable, portable, version-controllable. PDF is the export, not the source. Inline verify references are the killer demo moment (click → audit log → tool execution).

### Decision 5: Dependency stack

**Approved as below.** Every choice is justified against the constraint that downstream agents may need to know WHY.

| Concern | Choice | Version pin | Why |
|---|---|---|---|
| Python | CPython 3.12 | `>=3.12,<3.13` | SIFT 2026 ships 3.12; pin to match |
| Package manager | **`uv`** | `==0.11.18` | 10-100x faster than poetry/pip; pinned exact per audit B-PY-2 (older versions had breaking semantics changes) |
| Linter + formatter | **`ruff`** | `>=0.8` | Replaces black + isort + flake8 + pylint; Rust-fast; single config |
| Type checker | **`mypy`** strict | `>=1.13` | Boring, works; pyright fallback if mypy stalls |
| Testing | **`pytest`** + **`hypothesis`** | `>=8` / `>=6` | Property tests catch verification-gate edge cases |
| Coverage | **`coverage[toml]`** | `>=7.6` | Standard |
| MCP server | **`mcp`** (FastMCP) | `>=1.23.0,<2.0` | Official SDK; Pydantic-native; stdio + Streamable HTTP. Pin floor closes **CVE-2025-66416** (DNS-rebinding default-off pre-1.23.0) + **CVE-2025-53366** (DoS, fixed 1.9.4). Ceiling avoids v2's `FastMCP→MCPServer` breaking rename. |
| Agent loop | **`pydantic-ai`** | `>=1.105.0,<2.0.0` | MIT; MCP-native; model-string provider switching; Hooks (via `capabilities=[hooks]`); agent-delegation. Pin to 1.105 floor (zero breaking changes since v1.0 Sep 2025); ceiling forces deliberate v2 migration. |
| Provider extras | `pydantic-ai[anthropic,openai,google,ollama,mcp,fastmcp]` | matching | One install, all providers |
| I/O typing | **Pydantic v2** | `>=2.9` | Ecosystem fit |
| Crypto | stdlib `hmac` + `hashlib` PBKDF2 | (stdlib) | No extra deps; PBKDF2-SHA256 600K iters (Valhuntir pattern) |
| Logging | direct Pydantic `model_dump_json()` | (stdlib + Pydantic) | **DROPPED `structlog`** per audit Decision A — direct `model_dump_json()` is right for our write rate; one fewer dep |
| CLI | **`typer`** | `>=0.15` | Type-driven; rich output |
| Terminal UI | **`rich`** | `>=14.1,<16` | Pinned floor for nested-Live fix (used in HUD); ceiling avoids breaking changes |
| Report PDF | **`weasyprint`** | `>=68.1,<70.0` | Matches Protocol SIFT pattern. Pin floor closes **CVE-2025-68616** (was `>=60,<62` — affected) |
| Markdown processing | **`mistune`** | `>=3.2.1` | Pin floor closes 6 CVEs (CVE-2026-44708, 44896, 44897, 44899, 33441, 33079) — all fixed in 3.2.1 (May 2026) |
| HTTP client | **`httpx`** | `>=0.27` | Async; modern |
| NER (entity gate) | **`spacy`** `en_core_web_lg` + regex | `spacy>=3.8.10,<3.9` + `en_core_web_lg==3.8.0` | KEEP per audit Decision A — pure regex can't catch hallucinated PERSON/ORG/GPE entities ("Lazarus Group") |
| Forensic memory toolkit | **`volatility3`** | `==2.27.0` | Pin in SilentWitness's OWN venv at `/opt/silentwitness/vol3-venv/bin/vol`. Do NOT use SIFT-managed `/opt/volatility3/bin/vol` (SIFT pins no version + 2.28.0 has open layer-detection regression #1985). Pre-fetch ISF symbol bundle into `~/.cache/volatility3/` at init. |
| Property-based test helpers | **`hypothesis`** | (above) | (above) |
| Pre-commit | **`pre-commit`** | `>=4` | Standard |
| File-size guard | custom `pre-commit` hook | (local) | Enforces ≤400 LOC per file |
| Secret detection | **`detect-secrets`** | `>=1.5` | Baseline |
| SBOM | **`cyclonedx-py`** | `>=4` | Supply-chain hygiene |

**Explicitly NOT using:** Claude Agent SDK (provider lock), LangGraph (overkill), CrewAI/AG2 (overshoot), LiteLLM as primary loop (3537 open issues; OK as translator under Pydantic AI if a niche provider is needed), Open Interpreter (AGPL — license blocker), smolagents (CodeAgent risk), pandas (Pydantic is enough), requests (httpx instead), Click (Typer wraps it with types), FastAPI / Flask (CLI is primary; minimal HTTP for stretch HUD only).

### Decision 6: CI/CD pipeline

**Approved.** Built day 0, enforced from commit 1. Details belong in `docs/CICD_SPEC.md` (next phase).

Headline gates:
- **`pre-commit`** (local, every commit): ruff format, ruff check --fix, mypy strict (changed files), file-size guard (≤400 lines), detect-secrets, forbidden-paths (no writes to evidence paths).
- **GitHub Actions `ci.yml`** (PR + push to main): full ruff + mypy strict + pytest + coverage report (target 85% on `src/`), hypothesis property tests, dataset hash verification, file-size guard re-run, SBOM via cyclonedx-py, license compatibility check, Docker build → GHCR on main.
- **Branch protection on `main`:** required PR, 1 review, green status checks, linear history.
- **Conventional Commits + semantic-release** for automated versioning.
- **Dependabot** weekly + Renovate fallback.

### Decision 7: Folder structure

**Approved.** Every Python file ≤400 lines. Splits at natural module boundaries.

```
silentwitness/
├── src/
│   ├── silentwitness_mcp/              # THE PRODUCT — standalone MCP server package
│   │   ├── __init__.py
│   │   ├── server.py                   # FastMCP entry point (<400 LOC)
│   │   ├── envelope.py                 # response envelope schema
│   │   ├── tools/                      # one .py per tool family
│   │   │   ├── memory.py               # Volatility 3 wrappers
│   │   │   ├── disk.py                 # MFT, EZ Tools wrappers
│   │   │   ├── log.py                  # EVTX, Hayabusa, Chainsaw wrappers
│   │   │   ├── network.py              # Zeek, Suricata wrappers
│   │   │   ├── registry.py             # RegRipper, EZ Tools registry wrappers
│   │   │   └── yara_scan.py            # YARA rule application
│   │   ├── verification/
│   │   │   ├── citation_gate.py        # span verification
│   │   │   ├── entity_gate.py          # NER + regex + verification
│   │   │   ├── sanitizer.py            # adversarial-evidence sanitizer
│   │   │   └── normalizer.py           # tool output normalization
│   │   ├── audit/
│   │   │   ├── logger.py               # JSONL writer with stable audit_id
│   │   │   └── ledger.py               # HMAC-signed approval ledger
│   │   ├── evidence/
│   │   │   ├── registry.py             # evidence file registration + SHA256
│   │   │   └── mount.py                # ro,noexec,nosuid mount validation
│   │   └── findings/
│   │       ├── observation.py          # record_observation MCP tool
│   │       ├── interpretation.py       # record_interpretation MCP tool
│   │       └── narrative.py            # record_narrative MCP tool
│   ├── silentwitness_agent/            # reference agent (Pydantic AI)
│   │   ├── __init__.py
│   │   ├── cli.py                      # typer entry point
│   │   ├── investigator.py             # main agent
│   │   ├── specialists/                # subagents via Pydantic AI delegation
│   │   │   ├── memory.py
│   │   │   ├── disk.py
│   │   │   ├── network.py
│   │   │   └── log.py
│   │   ├── hypothesis/
│   │   │   ├── stack.py                # state machine
│   │   │   ├── events.py               # event types
│   │   │   └── budget.py               # token + step budgeting
│   │   ├── report/
│   │   │   ├── renderer.py             # Markdown render
│   │   │   ├── pdf.py                  # WeasyPrint export
│   │   │   └── template.py             # FOR508-shaped section template
│   │   └── critic.py                   # closed-loop critic (interpretation challenger)
│   └── silentwitness_common/
│       ├── types.py                    # shared Pydantic models
│       └── ids.py                      # ID generators (F-, T-, audit_id)
├── claude-code-config/                 # drop-in .claude/ for SIFT-pre-installed Claude Code
│   ├── CLAUDE.md                       # system prompt
│   ├── settings.json                   # allow/deny + MCP server registration
│   └── skills/                         # optional skill files
├── tests/
│   ├── unit/                           # one test_<module>.py per src module
│   ├── property/                       # hypothesis tests for gates
│   └── integration/                    # end-to-end with Nitroba dataset
├── harness/
│   ├── datasets/                       # manifests (binaries gitignored)
│   ├── ground_truth/                   # parsed answer keys (Nitroba, NIST x2)
│   ├── scorer.py                       # precision/recall/hallucination per case
│   └── baseline/                       # Protocol SIFT baseline runner for delta
├── docs/                               # specs + ADRs + diagrams
│   ├── BRAINSTORM.md                   # this file
│   ├── CICD_SPEC.md                    # written first per Abu
│   ├── PRD.md
│   ├── architecture.md
│   ├── epics.md
│   ├── stories/
│   ├── adrs/                           # Architecture Decision Records
│   └── diagrams/                       # mermaid + draw.io exports
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── release.yml
├── .pre-commit-config.yaml
├── pyproject.toml                      # uv-managed
├── uv.lock
├── Dockerfile
├── docker-compose.yml
├── ruff.toml
├── mypy.ini
├── install.sh                          # bootstraps uv + community tools + .claude/ config
├── .gitignore
├── LICENSE                             # MIT
├── README.md
├── STRATEGY.md                         # → existing
└── STRATEGY-v1.md                      # → archived
```

---

## §4 — Audit trail design (cross-cutting)

Every MCP tool call emits a JSONL entry to `cases/<case_id>/audit/<backend>.jsonl`:

```jsonc
{
  "ts": "<iso8601 UTC>",
  "audit_id": "sift-<examiner>-<YYYYMMDD>-<NNN>",   // stable, sequence resumes across restarts
  "tool": "<tool name>",
  "params": { /* typed */ },
  "result_summary": { /* truncated, with sha256 of full output stored separately */ },
  "result_sha256": "<sha256 of normalized full output>",
  "stdout_path": "<path to full output blob>",
  "elapsed_ms": <float>,
  "examiner": "<name>",
  "model_used": "<model identifier — for provenance>",
  "model_token_count": { "prompt": N, "completion": M }
}
```

Findings cite `audit_ids`; verifier resolves them by reading the JSONL. The HMAC ledger signs the substantive text of approved findings (PBKDF2-SHA256 600K iters from examiner password, stored mode 0600 at `/var/lib/silentwitness/verification/<case_id>.jsonl`).

---

## §5 — Open questions deferred to spec phase

These are NOT decided here. They go into the spec phase with their own ADRs:

1. **Streaming HUD** — optional. Lightweight Server-Sent-Events on port 8088 (avoid 80 = Apache/CyberChef) emitting agent traces. Build only if time permits.
2. **Multi-case management** — for the demo we only need single-case. Multi-case is post-hackathon.
3. **OpenSearch / SQLite for the evidence index** — small cases work fine with JSONL + grep. SQLite if perf is needed. OpenSearch deferred (heavy infra).
4. **Live-host triage (Velociraptor MCP)** — out of v1 scope; mark as stretch.
5. **Examiner Portal (browser review UI)** — out of v1 scope; CLI examiner approval is enough for the demo.
6. **Model-cost optimization** — `claude-opus-4-7` for the main investigator, smaller model (`claude-haiku-4-5` or `gpt-5-mini`) for specialists/critic if cost matters. Decide in spec phase.

---

## §6 — Spec phase order (per Abu)

1. **`docs/CICD_SPEC.md`** — first, because CI gates are commit-1 enforced
2. **`docs/PRD.md`** — product requirements doc
3. **`docs/architecture.md`** — component architecture, sequence diagrams, deployment topology
4. **`docs/epics.md`** — feature epics broken from PRD
5. **`docs/stories/story-<slug>.md`** — implementation stories with BDD acceptance criteria

Each spec must be **audited against `../context/`** before declaration of done. Where context surfaces something not yet captured in the spec, the spec is updated.

Each spec must cite:
- Which `context/*` doc informed each major decision
- Which judging criterion the spec contributes to
- Any open question deferred to a later spec or ADR

---

## §7 — Provenance trail (so a downstream agent can follow our reasoning)

| Artifact | Where | What it answers |
|---|---|---|
| Wedge commitment | `../STRATEGY.md` | What user problem we solve, why |
| Validation passes | `../research/protocol-sift-2026/.raw/06-09*.md` | Why the wedge is the right wedge |
| Domain knowledge | `../context/` (13 docs, ~241K words) | Every domain fact a designer needs |
| Rules verification | `../context/.raw-design-research/01-rules-model-agnostic-verification.md` | Model-agnostic is permitted and rewarded |
| Library survey | `../context/.raw-design-research/02-model-agnostic-agent-libraries-survey.md` | Why Pydantic AI |
| SIFT 2026 catalog | `../context/.raw-design-research/03-sift-2026-tool-catalog-verified.md` | What ships pre-installed; what we install |
| Brainstorming result | `docs/BRAINSTORM.md` (this file) | The seven architecture decisions, committed |
| Coverage matrix | `../context/COMPLETENESS.md` | What context covers vs. gaps |

---

**Status: Architecture committed. Spec phase begins next.**
