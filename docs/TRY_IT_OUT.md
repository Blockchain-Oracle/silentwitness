# Try SilentWitness

Two paths from clean machine to a finished investigation: **(a) SIFT 2026 native** for judges with a SANS Protocol SIFT 2026 VM, and **(b) Docker Compose** for developers on macOS/Linux/Windows-WSL2. The README's `## Quick start` callout summarizes both; this document is the long-form walkthrough with troubleshooting + a step-by-step Nitroba smoke test.

> **Time budgets below are estimated (not yet measured end-to-end on this branch).** The demo-session run during `story-devpost-submission` produces the first measured numbers; until then, treat the ~15 min SIFT / ~10 min Docker targets as the design budget, not a stopwatch promise.

## Before you start — prerequisites

| Path | Required |
|---|---|
| SIFT 2026 native | SANS Protocol SIFT 2026 OVA (Ubuntu 24.04.2 Noble + Python 3.12 + Claude Code v2.0.61), 16 GB RAM, 80 GB disk, internet access, `ANTHROPIC_API_KEY` (or alternate provider key) |
| Docker Compose | Docker 24+, Docker Compose v2, 16 GB RAM, 80 GB disk, internet access, `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY` / `OPENROUTER_API_KEY` for model-agnostic switching) |
| Either path | A verified evidence binary — Nitroba pcap is the recommended smoke test; download per [`STARTER_CASES.md`](./STARTER_CASES.md) and verify SHA256 against `harness/datasets/nitroba.manifest.json` |

## Path A — SIFT 2026 native

```bash
# 1) Install (one-liner — bootstraps uv, registers .claude/ Code drop-in, installs the MCP server)
curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/Blockchain-Oracle/silentwitness/main/install.sh | bash

# 2) Register the case + evidence
silentwitness init nitroba-smoke-001 --examiner $USER
silentwitness register-evidence nitroba-smoke-001 /evidence/nitroba.pcap

# 3) Prepare + index the registered evidence
silentwitness prepare nitroba-smoke-001
silentwitness index nitroba-smoke-001

# 4) Investigate
silentwitness investigate nitroba-smoke-001

# 5) Review, verify, and export the report
silentwitness review nitroba-smoke-001
silentwitness verify --audit-chain nitroba-smoke-001
silentwitness export nitroba-smoke-001 --md
```

Expected timing: install ~5 min on clean SIFT; investigate against Nitroba ~3 min wall-clock with the default model.

### What you should see

Illustrative panel layout — the real rich layout is column-split (HYPOTHESIS STACK left, CURRENT TOOL CALL right) with a 3-pane footer (FINDINGS, BUDGET, LAST EVENT) per `src/silentwitness_agent/cli_commands/_live_layout.py`:

```
┌─ HYPOTHESIS STACK ─────────────────────┐ ┌─ CURRENT TOOL CALL ────────────┐
│ H-001  formed  "SMTP timing identifies │ │ network/parse_pcap             │
│        the harassment-email sender"    │ │ elapsed: 4.2s                  │
│        dispatch → network specialist   │ │ stdout sha256: 11f9c283…       │
│ H-002  formed  "DHCP lease window      │ │                                │
│        narrows the suspect MAC"        │ │                                │
│        dispatch → log specialist       │ │                                │
└────────────────────────────────────────┘ └────────────────────────────────┘
┌─ FINDINGS ──────────┐ ┌─ BUDGET ────────────┐ ┌─ LAST EVENT ─────────────┐
│ staged: 1           │ │ tokens: 142k/800k   │ │ vol_pslist OK            │
│ tool calls: 14      │ │ steps: 14/50        │ │ 4.2s, sha 11f9c283…      │
│ elapsed: 47s        │ │                     │ │                          │
└─────────────────────┘ └─────────────────────┘ └──────────────────────────┘
```

### Viewing the report

```bash
cat cases/nitroba-smoke-001/report.md
cat cases/nitroba-smoke-001/audit/hypothesis.jsonl | jq '.transition'
# Expect: form → dispatch → confirm → pivot → confirm
```

## Path B — Docker Compose

```bash
# 1) Build + boot the stack (local image silentwitness:local; mounts /evidence + ./cases)
docker compose up -d --build

# 2) Run an investigation — same init + register-evidence + prepare + index + investigate
#    sequence as Path A,
#    executed inside the container so the host needs no SIFT install.
docker compose exec silentwitness silentwitness init nitroba-smoke-001 --examiner $USER
docker compose exec silentwitness silentwitness register-evidence nitroba-smoke-001 /evidence/nitroba.pcap
docker compose exec silentwitness silentwitness prepare nitroba-smoke-001
docker compose exec silentwitness silentwitness index nitroba-smoke-001
docker compose exec silentwitness silentwitness investigate nitroba-smoke-001
docker compose exec silentwitness silentwitness review nitroba-smoke-001
docker compose exec silentwitness silentwitness verify --audit-chain nitroba-smoke-001
docker compose exec silentwitness silentwitness export nitroba-smoke-001 --md
```

Expected timing (estimated, unmeasured on this branch — verified during the demo session): image build ~2 min on first run; init + register ≤10 s; investigate ~3 min.

### Compose file layout

The committed `docker-compose.yml` builds a local `silentwitness:local` image (no ghcr image is published yet — `story-devpost-submission` is the publish gate). Excerpt:

```yaml
services:
  silentwitness:
    build: {context: ., dockerfile: Dockerfile}
    image: silentwitness:local
    user: "silentwitness"
    security_opt: ["no-new-privileges:true"]
    volumes:
      # /evidence is host-side; ro,noexec,nosuid intent declared (Docker enforces ro;
      # noexec/nosuid require host mount flags — see docker-compose.yml top comment).
      - "/evidence:/evidence:ro,noexec,nosuid"
      - "./cases:/cases"
      # Named volume for the HMAC ledger so chown 0700/0600 mode survives restart.
      - silentwitness-ledger:/var/lib/silentwitness
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - SILENTWITNESS_MODEL=anthropic:claude-opus-4-7

volumes:
  silentwitness-ledger: {driver: local}
```

## Step-by-step against Nitroba (recommended first run)

1. **`silentwitness init nitroba-smoke-001 --examiner $USER`** — creates `cases/nitroba-smoke-001/.silentwitness/case.toml`, `audit/`, `report.md`, `CASE.yaml`, and an empty `evidence.json` registry.
2. **`silentwitness register-evidence nitroba-smoke-001 /evidence/nitroba.pcap`** — computes SHA256, classifies the artifact type, and refuses unsafe writable evidence mounts (`ro,noexec,nosuid` check per architecture.md §4.11).
3. **`silentwitness prepare nitroba-smoke-001`** — extracts high-value artifacts from the registered evidence without modifying the original file.
4. **`silentwitness index nitroba-smoke-001`** — parses the prepared artifacts into `cases/nitroba-smoke-001/index.db`, the searchable evidence index used by the agent.
5. **`silentwitness investigate nitroba-smoke-001`** — opens the live rich layout; the hypothesis sequence is `form → dispatch network specialist → confirm SMTP-to-Yahoo timing → pivot to roster + MAC → confirm`. Each tool call appears in `audit/<backend>.jsonl` with its `audit_id`, `result_sha256`, and `elapsed_ms`.
6. **`silentwitness review nitroba-smoke-001`** — paginates staged findings with the `[a]pprove [r]eject [m]odify [s]kip` examiner UI. Approval signs the HMAC ledger row at `/var/lib/silentwitness/verification/<case_id>.jsonl`.
7. **`silentwitness verify --audit-chain nitroba-smoke-001`** — recomputes every audit JSONL hash chain and exits non-zero if a row is missing or edited.
8. **`silentwitness export nitroba-smoke-001 --md`** — writes the final Markdown report. Use `--pdf --out ./report.pdf` when you want the WeasyPrint-rendered PDF.

## Model selection (provider-agnostic)

`SILENTWITNESS_MODEL` selects the provider + model. All four are CI-tested via `tests/integration/test_investigator_provider_switch.py`:

```bash
export SILENTWITNESS_MODEL="anthropic:claude-opus-4-7"        # default; recommended for the demo
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

The harness is documented end-to-end in [`ACCURACY_REPORT.md`](./ACCURACY_REPORT.md) — methodology, baseline establishment, per-case measured Δ, known false positives + misses + residual hallucinations.

## Troubleshooting

- **"install.sh fails on `uv` bootstrap"**: diagnostic order — (a) `~/.local/bin/uv --version` to confirm whether uv is half-installed; (b) re-run with `bash -x install.sh 2>&1 | tee install.log` to capture the exact failure step; (c) common causes are corporate proxy blocking `astral.sh` (workaround: `export HTTPS_PROXY=…`) or a previous half-install leaving a broken venv (workaround: `rm -rf ~/.local/share/uv && rerun`). `install.sh` exports `~/.local/bin` for its own process, so a PATH warning usually means a manual `uv tool install` was run outside the script; in that shell, run `export PATH=$HOME/.local/bin:$PATH`. If all three fail, install uv manually: `curl --proto '=https' -sSf https://astral.sh/uv/install.sh | sh`, run the PATH export, then rerun the SilentWitness one-liner.
- **"`silentwitness install` seems to hang / `apt-get` lock"**: the install script runs `sudo apt-get update` to provision Hayabusa, Chainsaw, Zeek, Suricata. Lock contention with an unattended-upgrade or another apt session is the usual cause — `sudo lsof /var/lib/dpkg/lock-frontend` identifies the holder. The HUD is **optional** and binds 8088 by default; the install script does NOT touch port 80, so a port-80 Apache binding on a stock SIFT VM is unrelated to install hang.
- **"evidence mount is not read-only — register-evidence refuses"**: remount with `mount -o remount,ro,noexec,nosuid /evidence` (architecture.md §4.11 — mount validation). SilentWitness intentionally refuses to register evidence on a writable mount to preserve audit integrity.
- **"Volatility 3 reports symbol-table mismatch on a memory image"**: this is the **intended** self-correction moment. The agent rebuilds via `windows.info` + retry; no manual intervention is required and the pivot is captured in `audit/hypothesis.jsonl` with `transition=pivot`.
- **"model exceeds the default 800k-token budget"**: override at invocation — `silentwitness investigate <case> --max-tokens 1_200_000`. The investigator aborts cleanly when the budget is reached, with a Gap entry in the report.
- **"Claude Code drop-in not picked up after install"**: force-rewrite the drop-in with `silentwitness install --claude-code --force`; this overwrites `~/.claude/silentwitness.json`. Restart Claude Code afterward.
- **"HMAC verify fails after re-running on a different machine"**: the HMAC key is derived from the examiner password via PBKDF2 (600,000 iters) and is machine-local; verify on the same machine + same password used to approve the finding (architecture.md §4.9 — HMAC-signed approval ledger). The ledger is intentionally non-portable.

## Where to go next

- Per-case reproducibility recipes: [`STARTER_CASES.md`](./STARTER_CASES.md).
- Cross-case accuracy report (Δ vs vanilla Protocol SIFT): [`ACCURACY_REPORT.md`](./ACCURACY_REPORT.md).
- Component architecture + ADRs: [`architecture.md`](./architecture.md).
- Devpost submission entry: see the README badge row for the gallery link.

## License

[MIT](../LICENSE) — see [`NOTICES.md`](../NOTICES.md) for third-party attributions.
