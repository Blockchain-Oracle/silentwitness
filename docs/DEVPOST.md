# SilentWitness

## One-line pitch

> SilentWitness — a hypothesis-first DFIR investigator whose report writes itself, with every claim locked to the tool that produced it.

## What it does

DFIR analysts spend two to three hours of every shift not investigating — they're stenographers, copying tool output into a Markdown report and remembering which command produced which line. The cost compounds: by the time the report is written, the hypothesis chain is half-forgotten, and the citation back to the exact `vol3` row or `MFTECmd` entry that grounds a finding is reconstructed from memory rather than carried forward.

SilentWitness flips the operating mode. The AI investigator forms a hypothesis, dispatches a specialist (memory / disk / log / network) that holds a small MCP tool family, reads the tool's stored output, and emits a `record_observation` envelope whose `cited_spans` field is verified by an **architectural** citation gate against the immutable audit ledger. An entity gate refuses any observation whose claimed artifacts (process names, file paths, MAC addresses) do not appear, byte-for-byte, in a cited span. The Markdown report is rendered as the case unfolds, every finding carrying a `[verify:audit_id]` link that resolves to the exact audit row that produced it.

The demo's killer beat is the head-to-head: vanilla Protocol SIFT 2026 emits N hallucinated artifacts on the Nitroba / NIST Data Leakage / NIST Hacking Case corpora; SilentWitness emits zero, because the gates REJECT the malformed observations before they land. The Δ is measured (not estimated) by `harness/scorer.py` shelling out to `find`/`grep` against the mounted evidence — the verdict is reproducible by re-running the cited shell-out against the same mount.

## Inspiration

Rob T. Lee's framing in conversation with the SANS faculty was the anchor: analysts spend the late-shift hours acting as "command-line stenographers" — transcribing tool stdout into a coherent report with the right citations. The model spend on a SANS GIAC course's case is roughly two to three evenings of writing — for a competent FOR508 graduate, the bottleneck is not the analysis, it is the prose + provenance work.

Protocol SIFT 2026 demonstrated AI agents *can* drive forensic tools competently against the SIFT mount; what it did not yet have was a defensible audit trail (per the GTG-1002 framing — guardrails belong in code, not in prompts). SilentWitness's wedge is the architectural-gate layer that the prompt-only baseline cannot offer: the same model behind both runs produces a measurably cleaner output when the citation + entity gates run in code on every observation.

## How we built it

| Layer | Stack |
|---|---|
| Custom MCP server | `mcp>=1.23.0,<2.0` (CVE closures), FastMCP sub-module, Pydantic v2 envelopes |
| Reference agent | `pydantic-ai>=1.105.0,<2.0.0` — model-agnostic across Anthropic, OpenAI, Google, Ollama |
| CLI | `typer>=0.15`, `rich>=14.1,<16` (nested-Live fix) |
| Forensic tooling | Volatility 3 2.27.0 in own venv at `/opt/silentwitness/vol3-venv/bin/vol`; Hayabusa / Chainsaw / Zeek / Suricata / EZ Tools via subprocess; spaCy NER for entity-gate extraction |
| Report rendering | `weasyprint>=68.1,<70.0` (CVE closures), `mistune>=3.2.1` |
| Audit + integrity | HMAC-SHA256 with PBKDF2-SHA256 at 600,000 iterations; per-case ledger at `/var/lib/silentwitness/verification/<case_id>.jsonl` (mode 0600) |
| Test discipline | `pytest`, `hypothesis` property tests on the verification gates; 95% coverage floor on `verification/`, 90% on `audit/` + `findings/`, 85% elsewhere |
| Build | `uv==0.11.18` (Astral), `ruff>=0.8`, `mypy --strict` on every src file |

The investigator runs a hypothesis stack — `form → dispatch specialist → confirm → pivot` — with the critic agent firing every N steps on a fresh context to challenge the in-flight findings. We dropped `structlog` (Decision A in the deep audit) in favour of Pydantic's `model_dump_json()` for the JSONL audit; it preserved the typed shape and removed a dependency. The 22-tool MCP catalog is split into five backends — memory / disk / log / network / agent — so a single backend can be exercised, audited, or replaced without touching the others.

## Challenges we ran into

- **Pinning to SIFT 2026's tool versions.** SIFT 2026 ships dotnet 9 + Python 3.12 but NOT Node.js; the architecture diagram (`docs/diagrams/architecture.png`) is regenerated locally via mmdc behind an `--diagrams` install flag so the base install path stays fast for judges who only want to run `silentwitness investigate`. Vol3 plugin paths changed mid-cycle (`windows.malware.malfind.Malfind` replaced `windows.malfind.Malfind`); the MCP allowlist tracks the canonical 2026-06-07 plugin names verbatim.
- **Entity gate across Volatility 3 stdout shapes.** Vol3's pretty-printed columns drift between minor versions; the sanitizer normalizes whitespace + path separators + strips timestamps before SHA256, so the entity-substring check is run against a stable bytestream regardless of console-wrap differences.
- **Hitting 95% coverage on `verification/`.** Property tests on `sanitizer.normalize_for_audit` and the entity-gate substring matcher needed targeted boundary cases — Unicode bidi controls, zero-width characters, embedded `[verify:...]` tokens — which the property suite generates via hypothesis.

## Accomplishments that we're proud of

- **Measured Δ vs vanilla Protocol SIFT 2026** on three datasets (Nitroba, NIST Data Leakage, NIST Hacking Case), with HALLUCINATION verdicts grounded in real `find`/`grep` shell-outs against the mounted evidence (`harness/scorer.py`). Reproducible end-to-end via `just harness DATASET=<id>`.
- **22 typed MCP tools across 5 forensic backends** (memory / disk / log / network / agent), every tool wrapping the canonical SIFT 2026 install path with SHA256-pinned binaries.
- **HMAC-signed approval ledger** with PBKDF2-SHA256 at 600,000 iterations + a named-volume Docker mount so the chain survives container restarts (per `architecture.md §4.9`).
- **Self-correcting hypothesis stack.** The `transition=pivot` row in `audit/hypothesis.jsonl` is the architectural artifact that proves the investigator detected a stale assumption (vol3 symbol-table mismatch is the canonical example) and revised — without the analyst needing to step in.

## What we learned

Honesty over polish. NIST Hacking Case canonical answers (MAC, IP, hostname, email for Greg Schardt / Mr. Evil) appear in hundreds of indexed writeups; a passing finding here is not evidence of working forensic capability — it is evidence the model has seen the writeups. The citation + entity gates force every claim to ground in evidence-present spans rather than regurgitated memory. We measure the **residual** — claims that escaped the gates and would have been flagged by an offline `grep`-the-mounted-image verifier — and document that residual in `docs/ACCURACY_REPORT.md` §10 ("Residual hallucinations we did NOT catch") alongside the ones the gates caught. The next iteration's headline is closing that residual, not advertising a number we cannot defend.

## What's next for SilentWitness

- **Live-host triage via Velociraptor MCP.** A `velociraptor` backend that wraps the AGPL-licensed agent via subprocess invocation, identical to the Hayabusa / Chainsaw pattern. No additional copyleft trigger because Velociraptor runs as a subprocess, not a linked library.
- **Multi-case management.** A `silentwitness queue` command that holds an ordered investigation backlog with budget caps, so a SOC analyst can stage three cases overnight and triage the staged findings in the morning.
- **Cloud forensics.** AWS / Azure / GCP audit-trail backends with the same MCP tool envelope shape, so the citation gate generalizes from local-mount evidence to cloud-trail evidence with no agent-side change.
- **Case-trapdoor synthesis.** The Epic 15 adversary-pair case (`harness/datasets/case-trapdoor.manifest.json`) — synthetic and contemporary, so the memorization risk that haunts Mr. Evil does not apply.

## Built with

`python`, `pydantic-ai`, `mcp`, `fastmcp`, `volatility-3`, `sift-workstation`, `claude`, `docker`, `weasyprint`

## Try it yourself

Two paths in `docs/TRY_IT_OUT.md`: SIFT 2026 native (3 commands) or Docker Compose (2 commands). The README's `## Quick start` callout summarizes both; the long-form walkthrough has troubleshooting + a Nitroba smoke test that finishes in ~3 minutes.

## License

MIT — see [`LICENSE`](../LICENSE) and [`NOTICES.md`](../NOTICES.md) for third-party attributions.
