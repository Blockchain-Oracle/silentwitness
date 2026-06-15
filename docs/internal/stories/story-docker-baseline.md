# Story — Docker baseline (multi-stage Dockerfile + compose)

**ID:** story-docker-baseline
**Epic:** Epic 1 — Project scaffolding + CI/CD on commit 1
**Depends on:** story-scaffold-uv-pyproject
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** ship a multi-stage `Dockerfile` + `docker-compose.yml` per CICD_SPEC §11
**So that** a judge on any non-SIFT host can `docker compose up` and run the MCP server with `/evidence/` mounted `ro,noexec,nosuid` and the HMAC ledger persisted to a named volume (PRD §10 deliverable 7 "Try-It-Out" two-command Docker path; FR10).

---

## File modification map

- `Dockerfile` — NEW — verbatim from CICD_SPEC §11.1: multi-stage build (`python:3.12-slim-bookworm` build + runtime — bookworm-pinned per audit F-PY-4 to avoid the floating tag flipping to trixie/forky mid-hackathon), `uv 0.11.18` install (per audit B-PY-2 — 0.5.x has breaking semantics changes), `uv sync --frozen --no-dev`, SBOM bake-in at `/app/sbom.cdx.json`, WeasyPrint native deps (libcairo2 / libpango-1.0-0 / libpangocairo-1.0-0 / libpangoft2-1.0-0 / libgdk-pixbuf-2.0-0 / libharfbuzz-subset0 / libffi8 / shared-mime-info / fonts-dejavu / fonts-liberation — the extra harfbuzz/pangoft2/font packages closed audit F-PY-3), non-root user `silentwitness:10001`, OCI labels (~70 LOC).
- `docker-compose.yml` — NEW — single service `silentwitness` built from `Dockerfile`; binds `/evidence` host directory read-only with `noexec,nosuid` mount options; mounts `./cases` writable; named volume `silentwitness-ledger` mapped to `/var/lib/silentwitness`; healthcheck via `python -c "import silentwitness_mcp"` (~35 LOC).
- `.dockerignore` — NEW — excludes `.venv/`, `.git/`, `htmlcov/`, `coverage.xml`, `*.cdx.json`, `cases/`, `var/lib/silentwitness/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.hypothesis/`, `tests/`, `docs/`, `harness/datasets/` (binaries) (~25 LOC).
- `tests/unit/test_docker_compose.py` — NEW — 5 behavioral tests: docker-compose.yml parses as valid YAML; declares the `silentwitness` service; evidence mount carries `ro` + `noexec` + `nosuid`; the ledger named-volume is declared and mapped to `/var/lib/silentwitness`; the image build context is `.`.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given Dockerfile exists at the repo root
When  `docker build --target build -t silentwitness:build-test .` runs
Then  exit code is 0
And   the build stage installs uv and runs `uv sync --frozen`

Given Dockerfile exists at the repo root
When  `docker build -t silentwitness:test .` runs
Then  exit code is 0
And   `docker run --rm silentwitness:test python -c "import silentwitness_mcp; print(silentwitness_mcp.__version__)"` exits 0 and prints a SemVer string

Given the built image
When  `docker run --rm silentwitness:test cat /app/sbom.cdx.json | head -c 50` runs
Then  output starts with `{"bomFormat":"CycloneDX"` (CycloneDX 1.6 JSON bundled per CICD_SPEC §10.1)

Given the built image
When  `docker run --rm silentwitness:test whoami` runs
Then  output is `silentwitness` (non-root, UID 10001 per CICD_SPEC §11.1)

Given docker-compose.yml exists
When  `uv run python -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"` runs
Then  exit code is 0

Given docker-compose.yml declares the evidence mount
When  `grep -E 'ro,noexec,nosuid' docker-compose.yml` runs
Then  the line is present (PRD §6 evidence mount NFR)

Given docker-compose.yml declares the ledger volume
When  `grep -E 'silentwitness-ledger.*/var/lib/silentwitness' docker-compose.yml` runs
Then  the volume mount is present

Given tests/unit/test_docker_compose.py exists
When  `uv run pytest tests/unit/test_docker_compose.py -v` runs
Then  exit code is 0
And   5 tests pass
```

---

## Shell verification

```bash
# Dockerfile parses + image builds (build stage + full)
docker build --target build -t silentwitness:build-test .
docker build -t silentwitness:test .

# Import works inside container
docker run --rm silentwitness:test python -c "import silentwitness_mcp; print(silentwitness_mcp.__version__)"

# SBOM baked into image
docker run --rm silentwitness:test test -f /app/sbom.cdx.json
docker run --rm silentwitness:test head -c 30 /app/sbom.cdx.json | grep -q "bomFormat"

# Non-root user enforced
test "$(docker run --rm silentwitness:test whoami)" = "silentwitness"

# Compose YAML valid
uv run python -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"

# Mount flags + named volume present
grep -qE 'ro,noexec,nosuid' docker-compose.yml
grep -qE 'silentwitness-ledger' docker-compose.yml
grep -qE '/var/lib/silentwitness' docker-compose.yml

# Unit tests
uv run pytest tests/unit/test_docker_compose.py -v
# Must show 5 passing

# §14 no-mocks check
git diff main...HEAD -- 'src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded)" | grep -v "test\|spec"
# Must output nothing

# Cleanup
docker image rm silentwitness:test silentwitness:build-test
```

---

## Notes for coding agent

- Reference: CICD_SPEC.md §11 (Dockerfile shape verbatim — copy character-for-character), §11.2 (SIFT-compat note explaining when Docker vs native install), §11.3 (trivy scan policy — runs in CI, not in this story), §11.4 (push policy).
- Reference: PRD.md §10 deliverable 7 (Try-It-Out: 2-command Docker Compose path), §6 NFR (evidence mount `ro,noexec,nosuid`).
- Reference: architecture.md §7.2 (deployment topology — Docker Compose mounts).
- Copy the Dockerfile from CICD_SPEC §11.1 character-for-character. Do NOT change the `uv` version (0.5.11 — pinned in CI matrix env). Do NOT switch the base image (`python:3.12-slim`) — SIFT 2026 is Python 3.12.
- WeasyPrint runtime native deps are NOT optional. Without `libcairo2`, `libpango-1.0-0`, `libpangocairo-1.0-0`, `libgdk-pixbuf-2.0-0`, `libffi8`, `shared-mime-info`, the report PDF export (Epic 11) breaks at runtime with confusing C-extension errors. Architecture §1 / §1.10 cites this.
- The compose `volumes:` block must use the long-form mount syntax to express `ro,noexec,nosuid` (the short form does not support `noexec`/`nosuid` reliably across docker-compose versions). Reference docker-compose schema v3.8+.
- The ledger volume is a **named volume**, NOT a bind mount. The HMAC ledger at `/var/lib/silentwitness/verification/<case>.jsonl` is mode 0600 inside a 0700 directory (architecture §4.9); bind-mounting from the host would inherit host permissions and break the mode enforcement. Named volume survives container restart per architecture §7.2.
- The Dockerfile creates the `silentwitness` user at UID 10001. Do not change the UID — it is referenced from `.github/workflows/ci.yml` Trivy scan expectations and from the compose healthcheck.
- The `ENTRYPOINT ["python", "-m", "silentwitness_mcp"]` is the MCP stdio entrypoint. Compose overrides this with `command:` if the user wants `silentwitness investigate ...`. Both paths supported.
- This story does NOT register the server with Claude Code — that lives in story-cli-install-claude-code (Epic 12). The container is for non-SIFT, non-Claude-Code clients (Cherry Studio, custom Python agents, etc.).
- Library docs to consult via Context7 BEFORE writing:
  - `docker compose` topic `volumes bind mount options noexec nosuid` (the long-form syntax).
  - `weasyprint` topic `linux native dependencies` (the libcairo / libpango family list — may have shifted in weasyprint 63+).
- DO NOT run `apt-get upgrade` in the Dockerfile — pin to base image vulns, let Trivy + Dependabot bump the base.
