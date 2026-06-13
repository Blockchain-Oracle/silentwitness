# SilentWitness

> SilentWitness — a hypothesis-first DFIR investigator whose report writes itself, with every claim locked to the tool that produced it.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE) [![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](pyproject.toml) [![CI](https://img.shields.io/badge/ci-passing-brightgreen.svg)](.github/workflows/ci.yml) [![Model-agnostic](https://img.shields.io/badge/model-agnostic-purple.svg)](docs/architecture.md)

Built for the SANS [Find Evil!](https://findevil.devpost.com/) hackathon (2026).

## Demo

📺 **2-minute demo:** <!-- DEMO_VIDEO_URL --> [youtu.be/PLACEHOLDER](https://youtu.be/PLACEHOLDER)

![Markdown report with inline `[verify:audit_id]` links resolving to JSONL audit entries](./docs/assets/report-verify-links.png)

## Quick start

### (a) SIFT 2026 native — 3 commands

```bash
# 1. install
curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/Blockchain-Oracle/silentwitness/main/install.sh | bash
# 2. register a case + its evidence (one step, two sub-actions on a single line)
silentwitness init mr-evil-001 --examiner $USER && silentwitness register-evidence mr-evil-001 /evidence/hacking-case
# 3. investigate
silentwitness investigate mr-evil-001
```

### (b) Docker Compose — 2 commands

```bash
docker compose up -d
docker compose exec silentwitness silentwitness investigate mr-evil-001
```

## Architecture

```mermaid
flowchart TB
  subgraph CLI[silentwitness CLI (architectural)]
    INIT[init / register-evidence / investigate]
  end
  subgraph AGENT[Pydantic AI investigator (architectural)]
    ORCH[Hypothesis-first orchestrator]
    CRITIC[Critic + entity gate + citation gate (architectural)]
  end
  subgraph MCP[Custom FastMCP server (architectural)]
    MEMSPEC[Memory specialist (architectural)]
    DISK[Disk specialist (architectural)]
    LOG[Log specialist (architectural)]
    NETSPEC[Network specialist (architectural)]
  end
  subgraph EVIDENCE[Read-only evidence mount (architectural)]
    MOUNT[/evidence ro,noexec,nosuid (architectural)]
  end
  subgraph AUDIT[Audit JSONL ledger (architectural)]
    LEDGER[verify-links + HMAC chain (architectural)]
  end
  subgraph PROMPTS[System prompts (prompt-based — supplementary, not load-bearing)]
    AGENT_PROMPT[Investigator system prompt (prompt-based — supplementary, not load-bearing)]
    CRITIC_PROMPT[Critic agreement prompt (prompt-based — supplementary, not load-bearing)]
  end
  CLI --> AGENT
  AGENT --> MCP
  MCP --> EVIDENCE
  AGENT --> AUDIT
  MCP --> AUDIT
  AGENT_PROMPT -.-> AGENT
  CRITIC_PROMPT -.-> CRITIC
```

**Eight boundaries, six of them architectural.** Verification gates (entity gate, citation gate, HMAC audit chain), the `ro,noexec,nosuid` evidence mount, and the per-specialist MCP toolset run in code — not in prompts. The two prompt-based guardrails (investigator system prompt + critic agreement prompt) are *supplementary*: removing them degrades quality but does not unlock hallucinations against unmounted artifacts.

## What's novel

SilentWitness is the first hypothesis-first DFIR agent to ship the *architectural* guardrails the IR community has been asking prompt-based agents to fake. The investigator cannot claim against an artifact the entity gate cannot resolve; the report cannot include a finding the citation gate cannot link to a real audit-JSONL line. Every Δ vs vanilla Protocol SIFT in the [accuracy report](./docs/ACCURACY_REPORT.md) is **measured, not estimated** — `silentwitness baseline-comparison <case-id>` reruns the comparison on demand.

## Try it out

Per-dataset walkthroughs (Nitroba, NIST Hacking Case, NIST Data Leakage): see [`docs/TRY_IT_OUT.md`](./docs/TRY_IT_OUT.md).

## Accuracy report

Measured Δ vs vanilla Protocol SIFT 2026 baseline: see [`docs/ACCURACY_REPORT.md`](./docs/ACCURACY_REPORT.md).

## Datasets

Provenance + memorization-risk disclosure per case: see [`docs/DATASETS.md`](./docs/DATASETS.md).

## Example execution logs

Real audit JSONL output from past runs: see [`docs/EXAMPLE_EXECUTION_LOGS/`](./docs/EXAMPLE_EXECUTION_LOGS/).

## Architecture deep-dive

Component architecture, the 27-tool MCP catalog, and 10 ADRs: see [`docs/architecture.md`](./docs/architecture.md).

## License

[MIT](./LICENSE) — see [`NOTICES.md`](./NOTICES.md) for third-party attributions.

## Acknowledgments

Built against the **AppliedIR / Valhuntir** bar SANS cites as the IR-agent target; baseline comparison against **teamdfir / protocol-sift** for the vanilla SIFT 2026 reference path. Datasets sourced from Nitroba (Wireshark University) and NIST (DFR / CFReDS).
