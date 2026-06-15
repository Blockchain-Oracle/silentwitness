# Story — Try-It-Out documentation (`docs/TRY_IT_OUT.md`; Rules deliverable #7; two paths — SIFT 2026 native + Docker Compose)

**ID:** story-try-it-out-doc
**Epic:** Epic 16 — Documentation polish + submission
**Depends on:** story-docker-baseline, story-cli-install-claude-code, story-cli-init, story-cli-register-evidence, story-cli-investigate, story-readme-polish, story-dataset-manifests
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent assembling the Devpost Rules §4 deliverable set
**I want to** ship `docs/TRY_IT_OUT.md` — the long-form judge-facing walkthrough behind the README's `## Quick start` callout — with two end-to-end paths (SIFT 2026 native via `install.sh` + `silentwitness init` + `silentwitness investigate`, and Docker Compose via `docker compose up` + `docker compose exec ... investigate`), step-by-step screenshots/anchors against the Nitroba smoke dataset, plus troubleshooting answers for the top-N issues a judge will hit
**So that** PRD §10 deliverable 7 ("Try-It-Out instructions") is satisfied with a single Markdown file that a judge can follow from clean SIFT VM to a finished demo run in ≤15 minutes, AND a developer without SIFT can follow the Docker path on macOS/Linux/Windows-WSL2 in ≤10 minutes, per epics.md Epic 16 DoD + PRD §11 README shape + judging criterion Usability and Documentation (PRD §8 row 6).

---

## File modification map

- `docs/TRY_IT_OUT.md` — NEW — Markdown document, ≤400 lines. Section order locked:
  1. `# Try SilentWitness` — H1 + 1-paragraph framing tying back to PRD §11 README shape ("3-command SIFT path; 2-command Docker path") and pointing the reader at the 3-minute demo video.
  2. `## Before you start — prerequisites` — short table:
     - SIFT 2026 path: SANS Protocol SIFT 2026 OVA (Ubuntu 24.04.2 Noble, Python 3.12, Claude Code v2.0.61); 16 GB RAM; 80 GB disk; internet access for the install script + LLM provider
     - Docker path: Docker 24+; Docker Compose v2; 16 GB RAM; 80 GB disk; internet access; `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY` / `OPENROUTER_API_KEY` for model-agnostic provider switching per PRD §5 FR3)
     - Anywhere: a verified evidence binary (Nitroba pcap is the recommended smoke test; downloaded per `docs/DATASETS.md`)
  3. `## Path A — SIFT 2026 native (3 commands)` — verbatim shell, cite story-cli-install-claude-code + story-cli-init + story-cli-investigate:
     ```bash
     # 1) Install (one-liner — bootstraps uv, registers .claude/, installs MCP)
     curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/<org>/silentwitness/main/install.sh | bash
     # 2) Register the case + evidence
     silentwitness init nitroba-smoke-001 --examiner $USER
     silentwitness register-evidence nitroba-smoke-001 /evidence/nitroba.pcap
     # 3) Investigate
     silentwitness investigate nitroba-smoke-001
     ```
     Expected timing: install ~5 min on clean SIFT; investigate against Nitroba ~3 min wall-clock with the default model.
     Sub-section `### What you should see`: a rendered ASCII screenshot of the rich live layout (lifted from ux-spec §2.3 verbatim — the four-pane "HYPOTHESIS STACK / CURRENT TOOL CALL / FINDINGS / BUDGET" view).
     Sub-section `### Viewing the report`: `cat cases/nitroba-smoke-001/report.md` + `cat cases/nitroba-smoke-001/audit/hypothesis.jsonl | jq '.transition'` showing the per-tool audit trail.
  4. `## Path B — Docker Compose (2 commands)` — verbatim shell, cite story-docker-baseline:
     ```bash
     # 1) Boot the stack (pulls ghcr.io/<org>/silentwitness:latest; mounts ./evidence + ./cases)
     docker compose up -d
     # 2) Run an investigation
     docker compose exec silentwitness silentwitness investigate nitroba-smoke-001 \
        --evidence /evidence/nitroba.pcap --examiner $USER
     ```
     Expected timing: image pull ~2 min on first run; investigate ~3 min.
     Sub-section `### Compose file layout`: 8-line excerpt from `docker-compose.yml` (services: `silentwitness`; volumes: `./evidence:/evidence:ro`, `./cases:/cases`; env: `ANTHROPIC_API_KEY`).
     Sub-section `### Pre-built image`: `docker pull ghcr.io/<org>/silentwitness:latest` + image SHA pinned in README per PRD §6 reproducibility.
  5. `## Step-by-step against Nitroba (recommended first run)` — narrative walkthrough using Path A or Path B:
     - Step 1: `silentwitness init nitroba-smoke-001 --examiner $USER` — what gets created (`cases/nitroba-smoke-001/.silentwitness/case.toml`, `audit/`, `findings.json`).
     - Step 2: `silentwitness register-evidence nitroba-smoke-001 /evidence/nitroba.pcap` — SHA256 verification against the manifest at `harness/datasets/nitroba.manifest.json`.
     - Step 3: `silentwitness investigate nitroba-smoke-001` — what the live rich layout shows; what hypothesis events you should expect (form → dispatch network specialist → confirm SMTP-to-Yahoo timing → pivot to roster + MAC).
     - Step 4: `silentwitness review nitroba-smoke-001` — paging through staged findings; the `[a]pprove [r]eject [m]odify [s]kip` examiner UI per ux-spec §2.4.
     - Step 5: `silentwitness export nitroba-smoke-001 --pdf --out ./report.pdf` — WeasyPrint render with verify-link Appendix-Audit.
     - Step 6: `silentwitness verify nitroba-smoke-001` — HMAC-ledger recompute showing the audit trail is intact.
  6. `## Model selection (provider-agnostic)` — cite PRD §5 FR3:
     - `export SILENTWITNESS_MODEL="anthropic:claude-opus-4-7"` (default; recommended for the demo)
     - `export SILENTWITNESS_MODEL="openai:gpt-5"` (alternative — CI-tested per PRD §5 FR3)
     - `export SILENTWITNESS_MODEL="google-gla:gemini-2.5-pro"` (alternative)
     - `export SILENTWITNESS_MODEL="ollama:llama4-70b-instruct"` (local; longer-running on first cold cache)
     - Cite the model string mapping in `silentwitness_agent/investigator.py` (Pydantic AI provider extras per architecture §1).
  7. `## Running the head-to-head accuracy harness` — short walkthrough invoking `just harness DATASET=nitroba` (cite story-justfile-targets, story-baseline-runner, story-silentwitness-runner, story-scorer, story-delta-report):
     ```bash
     # Runs baseline + silentwitness + scorer + delta against Nitroba; writes harness/results/nitroba/
     just harness DATASET=nitroba
     # View the delta
     cat harness/results/nitroba/delta.md
     open harness/results/nitroba/delta.png    # or xdg-open on Linux
     ```
  8. `## Troubleshooting` — Q&A list, top-N issues judges will hit:
     - "install.sh fails on `uv` bootstrap" — `curl --proto '=https' -sSf https://astral.sh/uv/install.sh | sh` manually; rerun the install script.
     - "Apache binds port 80 on SIFT" — the HUD is OPTIONAL and binds 8088 by default; the install script does NOT touch port 80 (cite ux-spec §3.2 + context/.raw-design-research/03).
     - "evidence mount is not read-only" — `mount -o remount,ro,noexec,nosuid /evidence` (cite architecture.md §4.11 — mount validation); SilentWitness refuses to register evidence on a writable mount.
     - "Volatility 3 symbol-table mismatch on memory image" — this is INTENDED (PRD §2 demo 3:00–3:30 self-correction moment); the agent rebuilds via `windows.info` + retry; no manual intervention required.
     - "model exceeds budget" — `silentwitness investigate <case> --max-tokens 1_200_000` overrides the default 800k budget per ux-spec §2.6.
     - "Claude Code drop-in not picked up" — `silentwitness install --claude-code --force` overwrites `~/.claude/silentwitness.json`; restart Claude Code afterwards.
     - "HMAC verify fails after re-run on a different machine" — the HMAC key is derived from the examiner password via PBKDF2; verify on the SAME machine + SAME password used to approve; cite architecture.md §4.9 — HMAC-signed approval ledger.
  9. `## Where to go next` — pointers to `docs/DATASETS.md`, `docs/ACCURACY_REPORT.md`, `docs/architecture.md`, and the Devpost submission link.
  10. `## License` — MIT callout linking to `LICENSE`.
- `scripts/check_try_it_out.py` — NEW — ≤120 LOC pure-Python CI gate. Reads `docs/TRY_IT_OUT.md`, asserts: (1) H1 is `# Try SilentWitness`; (2) the two `bash` code blocks for Path A (3 commands) and Path B (2 commands) are present and the SIFT path contains exactly `curl ... install.sh | bash`; (3) the Docker path contains exactly `docker compose up -d` and `docker compose exec silentwitness`; (4) the four model-string options for Path "Model selection" are present (anthropic, openai, google-gla, ollama); (5) the troubleshooting section has ≥6 Q&A entries; (6) banned vocab list zero hits (PRD §14); (7) total line count ≤400. Exit 0 on pass; exit 1 with failing rule name on fail.
- `tests/unit/test_try_it_out_doc.py` — NEW — ≥7 BDD scenarios via subprocess against `scripts/check_try_it_out.py` and a fixture `tests/fixtures/try-it-out/` (happy + 6 broken variants).

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given docs/TRY_IT_OUT.md is committed
When  `wc -l docs/TRY_IT_OUT.md` runs
Then  the line count is ≤ 400

Given docs/TRY_IT_OUT.md is committed
When  `grep -F 'curl --proto' docs/TRY_IT_OUT.md` runs
Then  exit code is 0 (Path A install one-liner present)

Given docs/TRY_IT_OUT.md is committed
When  `grep -F 'docker compose up -d' docs/TRY_IT_OUT.md` runs
Then  exit code is 0 (Path B Docker boot present)

Given docs/TRY_IT_OUT.md is committed
When  `grep -F 'silentwitness investigate nitroba-smoke-001' docs/TRY_IT_OUT.md` runs
Then  exit code is 0 (Nitroba walkthrough command present)

Given docs/TRY_IT_OUT.md is committed
When  `grep -iE '(court-admissible|Ralph Wiggum|autonomous SOC|replaces L1|eliminates hallucinations)' docs/TRY_IT_OUT.md` runs
Then  exit code is 1 (banned vocab zero hits)

Given docs/TRY_IT_OUT.md is committed
When  `grep -c '^## ' docs/TRY_IT_OUT.md` runs
Then  the integer is ≥ 9 (Before you start, Path A, Path B, Step-by-step, Model selection, Harness, Troubleshooting, Next, License)

Given `uv run python scripts/check_try_it_out.py` runs against committed docs/TRY_IT_OUT.md
When  the script completes
Then  exit code is 0

Given a fixture with a missing Docker Compose command
When  `uv run python scripts/check_try_it_out.py --file tests/fixtures/try-it-out/missing-docker.md` runs
Then  exit code is 1
And   stderr contains "docker compose up"

Given tests/unit/test_try_it_out_doc.py exists
When  `uv run pytest tests/unit/test_try_it_out_doc.py -v` runs
Then  exit code is 0
And   ≥7 tests pass
```

---

## Shell verification

```bash
# Tests
uv run pytest tests/unit/test_try_it_out_doc.py -v

# Lint
uv run ruff check scripts/check_try_it_out.py

# §14 vocab gate clean
grep -iE '(court-admissible|Ralph Wiggum|autonomous SOC|replaces L1|eliminates hallucinations)' docs/TRY_IT_OUT.md && exit 1 || true

# Line-count cap
test "$(wc -l < docs/TRY_IT_OUT.md)" -le 400

# Drift check
uv run python scripts/check_try_it_out.py
```

---

## Notes for coding agent

- Reference: `docs/PRD.md` §10 deliverable 7 (Try-It-Out instructions) + §11 README shape (TRY_IT_OUT.md is the long-form behind the README quick-start callout) + §5 FR1 stock-SIFT-2026 + FR3 model-agnostic + FR10 Docker Compose; `docs/ux-spec.md` §2.2 (CLI verbs) + §2.3 (live rich layout — paste verbatim in "What you should see"); `docs/architecture.md` §3 + §4.11 (mount validation); `docs/epics.md` Epic 16 DoD; story-docker-baseline (Docker Compose path); story-cli-install-claude-code (3-command native path).
- **Verbatim shell discipline:** every shell line must be copy-paste-ready. No placeholder `<org>` outside the install URL line (`<org>` is the only acceptable placeholder; document it in the section preamble — the substitution happens at submission time via `sed -i "s|<org>|sansforensics-2026|g" docs/TRY_IT_OUT.md` per story-devpost-submission's checklist).
- **Two paths, no middle ground:** the README pitches two paths (PRD §11). This doc expands both. Do NOT introduce a third path (e.g., uv-only without Docker on macOS) — the cognitive load on a 5-minute judge scan is the constraint.
- **Nitroba as smoke test:** Nitroba is the right first-run target — small (60 MB), public, fast (≤3 min wall-clock). NIST datasets (Data Leakage, Hacking Case) are 20 GB + 6 GB respectively — they belong in `docs/DATASETS.md`, not in the first-time walkthrough.
- **Cite the demo arc:** Step 3 ("Investigate") should call out what the judge will see in the live rich layout — the hypothesis stack, the pivot transitions, the budget pane. Lift the layout snippet from ux-spec §2.3 verbatim so the visual matches the demo video.
- **Model-string discipline:** the four model strings (anthropic, openai, google-gla, ollama) match Pydantic AI provider extras per architecture §1. CI tests ≥2 per PRD §5 FR3. Document the actual CI-tested pair in the "Model selection" section.
- **Troubleshooting answers are operational, not aspirational.** Every Q&A entry must reference a real command + a real file path. If you cannot test the answer against a clean SIFT VM in <2 minutes, cut it.
- **Docker image SHA pin (PRD §6 reproducibility):** the README pins the image SHA. This doc references "pre-built image at ghcr.io/<org>/silentwitness:latest" + points the reader at the SHA-pinned tag in the README. Do NOT duplicate the SHA here — single source of truth.
- **`scripts/check_try_it_out.py` is a CI gate, not a generator** — same pattern as `scripts/check_readme_gate.py` (story-readme-polish) and `scripts/build_datasets_doc.py` (story-dataset-doc). The doc is human-edited; the script catches drift.
- Vocabulary discipline (PRD §14): never "court-admissible"; never "autonomous SOC"; never "Ralph Wiggum Loop". Use "live rich layout", "hypothesis-pivot loop", "examiner approval flow". The literal phrase "Find Evil!" is allowed for the hackathon name (PRD §14 carve-out).
- Library docs to consult via Context7 BEFORE coding:
  - None — this story is pure Markdown + a small Python check script. No library API surface.
- Known pitfalls:
  1. `<org>` placeholder must be EXACTLY `<org>` (not `{org}` or `${org}`) — the submission-time sed substitution is anchored on the literal `<org>` form. Document this in `docs/devpost-submission-checklist.md` via story-devpost-submission.
  2. The Docker Compose file path is `./docker-compose.yml` at repo root (story-docker-baseline); the `docker compose` v2 syntax (space, not hyphen) — older docs sometimes show `docker-compose up`; CI gate catches this.
  3. Total line cap 400 — if you exceed, cut the "Step-by-step against Nitroba" narrative to 6 lines per step (no screenshots committed inline; link out to `docs/assets/`).
  4. `silentwitness register-evidence` requires the manifest file under `harness/datasets/` to know the expected SHA256 — document this prerequisite in Step 2.
