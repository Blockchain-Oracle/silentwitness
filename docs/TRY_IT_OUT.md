# Try SilentWitness

Two paths from clean machine to a finished investigation: **(a) SIFT 2026 native (3 commands)** for judges with a SANS Protocol SIFT 2026 VM, and **(b) Docker Compose (2 commands)** for developers on macOS/Linux/Windows-WSL2. The README's `## Quick start` callout (`README.md` §3) summarizes both; this document is the long-form walkthrough with troubleshooting + a step-by-step Nitroba smoke test. Time budget: SIFT path ≤15 min cold; Docker path ≤10 min cold.

## Before you start — prerequisites

| Path | Required |
|---|---|
| SIFT 2026 native | SANS Protocol SIFT 2026 OVA (Ubuntu 24.04.2 Noble + Python 3.12 + Claude Code v2.0.61), 16 GB RAM, 80 GB disk, internet access, `ANTHROPIC_API_KEY` (or alternate provider key) |
| Docker Compose | Docker 24+, Docker Compose v2, 16 GB RAM, 80 GB disk, internet access, `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY` / `OPENROUTER_API_KEY` for model-agnostic switching per PRD §5 FR3) |
| Either path | A verified evidence binary — Nitroba pcap is the recommended smoke test; download per [`DATASETS.md`](./DATASETS.md) and verify SHA256 against `harness/datasets/nitroba.manifest.json` |

## Path A — SIFT 2026 native (3 commands)

```bash
# 1) Install (one-liner — bootstraps uv, registers .claude/ Code drop-in, installs the MCP server)
curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/Blockchain-Oracle/silentwitness/main/install.sh | bash

# 2) Register the case + evidence
silentwitness init nitroba-smoke-001 --examiner $USER
silentwitness register-evidence nitroba-smoke-001 --path /evidence/nitroba.pcap

# 3) Investigate
silentwitness investigate nitroba-smoke-001
```

Expected timing: install ~5 min on clean SIFT; investigate against Nitroba ~3 min wall-clock with the default model.

### What you should see

```
┌─ HYPOTHESIS STACK ─────────────────────┐ ┌─ CURRENT TOOL CALL ────────────┐
│ H-001  formed  "SMTP timing identifies │ │ network/parse_pcap             │
│        the harassment-email sender"    │ │ elapsed: 4.2s                  │
│        dispatch → network specialist   │ │ stdout sha256: 11f9c283…       │
│ H-002  formed  "DHCP lease window      │ └────────────────────────────────┘
│        narrows the suspect MAC"        │ ┌─ FINDINGS ─────────────────────┐
│        dispatch → log specialist       │ │ F-001 DRAFT  SMTP-to-Yahoo at  │
└────────────────────────────────────────┘ │       21:30 confirms suspect   │
┌─ BUDGET ──────────────────────────────┐  │       [verify:sift-…-001]      │
│ tokens: 142k / 800k                   │  └────────────────────────────────┘
│ tool calls: 14 / 50                   │
└───────────────────────────────────────┘
```

### Viewing the report

```bash
cat cases/nitroba-smoke-001/report.md
cat cases/nitroba-smoke-001/audit/hypothesis.jsonl | jq '.transition'
# Expect: form → dispatch → confirm → pivot → confirm
```

## Path B — Docker Compose (2 commands)

```bash
# 1) Boot the stack (pulls ghcr.io/Blockchain-Oracle/silentwitness:latest; mounts ./evidence + ./cases)
docker compose up -d

# 2) Run an investigation
docker compose exec silentwitness silentwitness investigate nitroba-smoke-001 \
    --evidence /evidence/nitroba.pcap --examiner $USER
```

Expected timing: image pull ~2 min on first run; investigate ~3 min.

### Compose file layout

```yaml
services:
  silentwitness:
    image: ghcr.io/Blockchain-Oracle/silentwitness:latest
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - SILENTWITNESS_MODEL=anthropic:claude-opus-4-7-1m
    volumes:
      - ./evidence:/evidence:ro
      - ./cases:/cases
```

### Pre-built image

```bash
docker pull ghcr.io/Blockchain-Oracle/silentwitness:latest
# Image SHA256 is pinned in README's badge row + the dependency-review CI gate.
```

## Step-by-step against Nitroba (recommended first run)

1. **`silentwitness init nitroba-smoke-001 --examiner $USER`** — creates `cases/nitroba-smoke-001/.silentwitness/case.toml`, `audit/`, `findings.json`, and an empty `evidence.json` registry.
2. **`silentwitness register-evidence nitroba-smoke-001 --path /evidence/nitroba.pcap`** — computes SHA256, verifies against the canonical hash in `harness/datasets/nitroba.manifest.json`, refuses to register if the mount is writable (`ro,noexec,nosuid` check per architecture.md §4.11).
3. **`silentwitness investigate nitroba-smoke-001`** — opens the live rich layout; the hypothesis sequence is `form → dispatch network specialist → confirm SMTP-to-Yahoo timing → pivot to roster + MAC → confirm`. Each tool call appears in `audit/<backend>.jsonl` with its `audit_id`, `result_sha256`, and `elapsed_ms`.
4. **`silentwitness review nitroba-smoke-001`** — paginates staged findings with the `[a]pprove [r]eject [m]odify [s]kip` examiner UI (ux-spec §2.4). Approval signs the HMAC ledger row at `/var/lib/silentwitness/verification/<case_id>.jsonl`.
5. **`silentwitness export nitroba-smoke-001 --pdf --out ./report.pdf`** — WeasyPrint renders the Markdown report with verify-link Appendix-Audit; pdf opens in any viewer.
6. **`silentwitness verify nitroba-smoke-001`** — recomputes the HMAC chain and asserts the audit trail is intact; exits non-zero on any drift.

## Model selection (provider-agnostic)

Per PRD §5 FR3, `SILENTWITNESS_MODEL` selects the provider + model. All four are CI-tested via `tests/integration/test_investigator_provider_switch.py`:

```bash
export SILENTWITNESS_MODEL="anthropic:claude-opus-4-7-1m"        # default; recommended for the demo
export SILENTWITNESS_MODEL="openai:gpt-5"                          # alternative — chat-completions API
export SILENTWITNESS_MODEL="google-gla:gemini-2.5-pro"             # alternative
export SILENTWITNESS_MODEL="ollama:llama4-70b-instruct"            # local; longer-running on first cold cache
```

The model string is parsed by Pydantic AI's `infer_model()` in `src/silentwitness_agent/investigator.py`; provider extras are pinned per architecture.md §1.

## Running the head-to-head accuracy harness

```bash
# Runs baseline + silentwitness + scorer + delta against Nitroba; writes harness/results/nitroba/
just harness DATASET=nitroba

# View the delta
cat harness/results/nitroba/delta.md
open harness/results/nitroba/delta.png    # or xdg-open on Linux
```

The harness is documented end-to-end in [`ACCURACY_REPORT.md`](./ACCURACY_REPORT.md) — methodology, baseline establishment, per-dataset measured Δ, known false positives + misses + residual hallucinations.

## Troubleshooting

- **"install.sh fails on `uv` bootstrap"**: install uv manually first — `curl --proto '=https' -sSf https://astral.sh/uv/install.sh | sh` — then rerun the SilentWitness install one-liner.
- **"Apache binds port 80 on SIFT and the install script seems to hang"**: the HUD is **optional** and binds 8088 by default; the install script does not touch port 80. If hung, the cause is upstream `apt-get` lock — `sudo apt-get update` once first (cite ux-spec §3.2 + `context/.raw-design-research/03`).
- **"evidence mount is not read-only — register-evidence refuses"**: remount with `mount -o remount,ro,noexec,nosuid /evidence` (architecture.md §4.11 — mount validation). SilentWitness intentionally refuses to register evidence on a writable mount to preserve audit integrity.
- **"Volatility 3 reports symbol-table mismatch on a memory image"**: this is the **intended** PRD §2 3:00–3:30 self-correction moment. The agent rebuilds via `windows.info` + retry; no manual intervention is required and the pivot is captured in `audit/hypothesis.jsonl` with `transition=pivot`.
- **"model exceeds the default 800k-token budget"**: override at invocation — `silentwitness investigate <case> --max-tokens 1_200_000` (ux-spec §2.6). The investigator aborts cleanly when the budget is reached, with a Gap entry in the report.
- **"Claude Code drop-in not picked up after install"**: force-rewrite the drop-in with `silentwitness install --claude-code --force`; this overwrites `~/.claude/silentwitness.json`. Restart Claude Code afterward.
- **"HMAC verify fails after re-running on a different machine"**: the HMAC key is derived from the examiner password via PBKDF2 (600,000 iters) and is machine-local; verify on the same machine + same password used to approve the finding (architecture.md §4.9 — HMAC-signed approval ledger). The ledger is intentionally non-portable.

## Where to go next

- Per-dataset reproducibility recipes: [`DATASETS.md`](./DATASETS.md).
- Cross-dataset accuracy report (Δ vs vanilla Protocol SIFT): [`ACCURACY_REPORT.md`](./ACCURACY_REPORT.md).
- Component architecture + ADRs: [`architecture.md`](./architecture.md).
- Devpost submission entry: see the README badge row for the gallery link.

## License

[MIT](../LICENSE) — see [`NOTICES.md`](../NOTICES.md) for third-party attributions.
