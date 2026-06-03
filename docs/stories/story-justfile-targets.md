# Story — justfile targets

**ID:** story-justfile-targets
**Epic:** Epic 1 — Project scaffolding + CI/CD on commit 1
**Depends on:** story-scaffold-uv-pyproject, story-pre-commit-hooks, story-ci-workflows
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** ship the `justfile` with `install` / `format` / `lint` / `test` / `property` / `ci` / `clean` / `build` targets per CICD_SPEC §13.1
**So that** every developer (and every CI fallback path) has one command per workflow step and the local "full CI" target mirrors what `.github/workflows/ci.yml` runs (CICD_SPEC §1.1 defense-in-depth; PRD §10 deliverable 7 try-it-out friendliness).

---

## File modification map

- `justfile` — NEW — verbatim from CICD_SPEC §13.1 with one addition: a `build` target wrapping `docker build -t silentwitness:local .`. Targets: `default` (lists), `install`, `format`, `lint`, `test`, `property`, `ci`, `clean`, `build` (~75 LOC).
- `tests/unit/test_justfile.py` — NEW — 5 behavioral tests via `just --list` parsing: presence of each target (`install`, `format`, `lint`, `test`, `property`, `ci`, `clean`, `build`); `just --evaluate` produces no error on an empty environment.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given justfile exists at the repo root
When  `just --list` runs
Then  exit code is 0
And   output contains exactly the targets: install, format, lint, test, property, ci, clean, build

Given `just install` is executed from a clean checkout (with uv already on PATH)
When  the target completes
Then  exit code is 0
And   `.venv/` exists
And   `.git/hooks/pre-commit` exists (pre-commit hooks installed)

Given `just lint` is executed on the freshly scaffolded tree
When  the target completes
Then  exit code is 0 (ruff format --check + ruff check + mypy --strict all pass)

Given `just test` is executed
When  the target completes
Then  exit code is 0
And   coverage HTML report is produced at htmlcov/index.html
And   `coverage report --fail-under=85` does not abort the target (no source yet, treat as vacuous-pass via `|| true` is NOT permitted; the actual coverage gate fires once src/ has product code)

Given `just clean` is executed after a successful `just test`
When  the target completes
Then  exit code is 0
And   `.ruff_cache`, `.mypy_cache`, `.pytest_cache`, `.hypothesis`, `htmlcov/`, `coverage.xml` are all absent

Given tests/unit/test_justfile.py exists
When  `uv run pytest tests/unit/test_justfile.py -v` runs
Then  exit code is 0
And   5 tests pass

Given the `justfile` declares `set shell := ["bash", "-cu"]` and `set dotenv-load := true`
When  `grep -E '^set (shell|dotenv-load)' justfile` runs
Then  both directives are present
```

---

## Shell verification

```bash
# Recipe inventory
just --list
test "$(just --list 2>/dev/null | grep -cE '^\s+(install|format|lint|test|property|ci|clean|build)\b')" -ge 8

# Install target works
just install
test -d .venv
test -f .git/hooks/pre-commit
test -f .git/hooks/commit-msg

# Lint target green on empty src
just lint

# Test target (no product code yet — sanity test from story-scaffold-uv-pyproject covers ≥3 cases)
just test

# Clean removes caches
just clean
test ! -d .ruff_cache
test ! -d .mypy_cache
test ! -d .pytest_cache
test ! -d htmlcov

# Unit tests
uv run pytest tests/unit/test_justfile.py -v
# Must show 5 passing

# Shell + dotenv directives present
grep -qE '^set shell\s*:=\s*\["bash"' justfile
grep -qE '^set dotenv-load\s*:=\s*true' justfile

# §14 no-mocks check
git diff main...HEAD -- 'src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded)" | grep -v "test\|spec"
# Must output nothing
```

---

## Notes for coding agent

- Reference: CICD_SPEC.md §13.1 (full justfile verbatim — copy character-for-character), §13.2 (no make fallback — do not add a Makefile).
- The CICD_SPEC §13.1 justfile does NOT include a `build` target. Add it for this story: `build:` recipe runs `docker build -t silentwitness:local .` (story-docker-baseline produces the Dockerfile). Place it after `clean` to keep the order CICD_SPEC → docker-aware.
- The `ci` target in CICD_SPEC §13.1 chains `lint test property` + file-size-guard + SBOM + license-check. Keep ALL of these — they mirror `.github/workflows/ci.yml` (`lint`, `test`, `property-tests`, `file-size-guard`, `sbom`, `license-check` jobs). The local `just ci` is the developer's pre-push gate.
- `set dotenv-load := true` reads `.env` (gitignored) so the developer's local `ANTHROPIC_API_KEY` flows into the test process. Documented in CICD_SPEC §9.2.
- `set shell := ["bash", "-cu"]` ensures unset variable references abort the recipe (`-u`). Do NOT change this — silent unset-variable bugs in `just` recipes are a documented footgun.
- This story depends on story-pre-commit-hooks (for `pre-commit install`) and story-ci-workflows (for `scripts/license_gate.py`). If those have not landed, `just install` and `just ci` will fail with clear errors — that is fine; the orchestrator dispatches in order.
- Do NOT add a `coverage --fail-under=85 || true` escape hatch. The empty-src case is handled by the existing 3 sanity tests from story-scaffold-uv-pyproject; if they cover the `__version__` constant the coverage tool reports 100% on the trivially-tested package and fail-under=85 passes.
- `just --list` is the discoverability surface; new contributors run it first. Each recipe should have a one-line comment above it explaining what it does. Keep comments short — they are the docs.
- Library docs to consult via Context7 BEFORE writing:
  - `just` topic `recipes set directives` (the `set shell` / `set dotenv-load` syntax is stable but worth confirming for 1.36+).
- Pitfall: on macOS, `just install` may surface the Apple Xcode tooling prompt if the developer has never installed it. Document this in the recipe's comment ("if you see Xcode prompt, run `xcode-select --install` once") — but do NOT add macOS-specific branching to the recipe itself.
