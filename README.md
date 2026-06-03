# SilentWitness

> A hypothesis-first DFIR investigator whose report writes itself, with every claim locked to the tool that produced it.

Built for the SANS [Find Evil!](https://findevil.devpost.com/) hackathon (2026).

## What this is

SilentWitness extends the SANS SIFT Workstation with an AI investigator that works the case the way a FOR508-graduate senior analyst would — forming hypotheses, dispatching the right tool for each one, pivoting when evidence contradicts — and produces a structured incident report _as the case unfolds_. Every claim in the report ties back to the tool execution that produced it via a verifiable `[verify:audit_id]` link.

The architecture pattern is **Custom MCP Server (Python, FastMCP) + Pydantic AI reference agent + Claude Code drop-in config**. Model-agnostic: configurable across Anthropic Claude, OpenAI GPT-5, Google Gemini, and local Ollama via a single `SILENTWITNESS_MODEL` env var.

> Quick orient for future agents: read [`CLAUDE.md`](./CLAUDE.md), then [`STRATEGY.md`](./STRATEGY.md), then the spec set in [`docs/`](./docs/).

## Status

🏗️ **Build phase — Epic 1 (project scaffolding + CI/CD on commit 1).** No product code yet. Specs are locked. See [`docs/sprint-status.yaml`](./docs/sprint-status.yaml) for live progress against the 83 implementation stories.

## Project layout

```
silentwitness/
├── CLAUDE.md                            ← Minimal agent guide (always loaded)
├── STRATEGY.md                          ← Wedge commitment
├── context/                             ← ~241K-word domain knowledge corpus
├── research/                            ← Wedge-validation research artefacts
├── docs/
│   ├── PRD.md                           ← Product requirements
│   ├── architecture.md                  ← Component architecture, 27-tool catalog, 10 ADRs
│   ├── ux-spec.md                       ← CLI (12 commands) + optional HUD
│   ├── CICD_SPEC.md                     ← Pre-commit + GitHub Actions + Dockerfile
│   ├── epics.md                         ← 16 epics, 6-wave dispatch queue
│   ├── sprint-status.yaml               ← Orchestrator-readable tracker
│   ├── stories/                         ← 84 BDD-style implementation stories
│   ├── AUDIT_REPORT.md                  ← Internal-consistency audit
│   ├── DEEP_AUDIT_REPORT.md             ← External SDK audit (21 BLOCKERs patched)
│   └── .audit/                          ← Per-library source-code verification
└── src/
    ├── silentwitness_mcp/               ← Custom MCP server (THE product)
    ├── silentwitness_agent/             ← Reference Pydantic AI agent
    └── silentwitness_common/            ← Shared Pydantic types
```

## Run-locally (post-Epic 1)

```bash
uv sync --frozen
uv run pytest tests/unit -v
```

Full Try-It-Out instructions land at the close of Epic 16; see [`docs/stories/story-try-it-out-doc.md`](./docs/stories/story-try-it-out-doc.md).

## License

[MIT](./LICENSE) — see `NOTICES.md` (post-Epic 16) for third-party attributions.
