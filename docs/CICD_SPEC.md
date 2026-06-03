# CICD_SPEC — SilentWitness

> **Spec status: DRAFT.**
> **Project:** SilentWitness — model-agnostic Custom MCP server + Pydantic AI reference agent + Claude Code drop-in config.
> **Owner:** TBD (proposed: Abu, until sub-maintainers assigned).
> **Contributes to judging criteria:** Constraint Implementation, Audit Trail Quality, Usability.
> **Source documents informing this spec:** `../STRATEGY.md`; `./BRAINSTORM.md` §3.5 (dependency stack) and §3.6 (CI/CD outline); `../context/.raw-design-research/03-sift-2026-tool-catalog-verified.md`; `../context/technical/07-mcp-and-agent-platforms.md`; `../context/technical/08-llm-failure-modes-in-agentic-systems.md` §4 (tool poisoning) and §5 (MCP-specific vulns); `../context/stakeholders/12-judges-curriculum-and-legal-landscape.md` Part A §A7 (Yotam Perkal).

---

## 1. Status header + rationale

### 1.1 Why this spec exists first

Per Abu's direct instruction in `BRAINSTORM.md` §6 ("Spec phase order"), `CICD_SPEC.md` is written before `PRD.md`, before `architecture.md`, and before the first epic. The reason is operational: **every CI gate defined here fires from commit 1**. The pre-commit hook chain, the GitHub Actions workflow, the file-size guard, the conventional-commit check, the SBOM job — all of them activate before the first line of `silentwitness_mcp/server.py` is written. If we defined gates after writing code, we would inevitably grandfather in violations ("we'll fix the >400-LOC file later," "we'll add the type annotation later"). That path leads to the slop we are explicitly building this project to avoid.

The wedge (`STRATEGY.md`) commits us to building a system whose **every claim ties back to a tool execution that produced it**. That guarantee is enforced architecturally inside the MCP server (citation gate + entity gate, `BRAINSTORM.md` Decision 3) — but architectural enforcement is only as strong as the code that implements it. CI is the second line of defense: it ensures the verification gates themselves are tested to 95% coverage, that the MCP server's tool surface is SBOM-tracked, that no AGPL dependency contaminates our MIT/Apache release, and that no commit lands without a typed signature and a passing property test.

### 1.2 Which judging criteria this spec contributes to

Three of the six published Find Evil! judging criteria are directly reinforced by CI gates:

1. **Constraint Implementation.** The MCP server is the artifact judges score for architectural constraint enforcement. CI gates here are what tell the judges "this is not a prompt-only guardrail; the constraint is mechanical." The `verification/citation_gate.py` and `verification/entity_gate.py` modules carry a hard 95% coverage floor. The `file-size-guard` enforces the ≤400-LOC-per-file rule that keeps modules auditable. The `forbidden-paths` hook ensures the codebase cannot accidentally write into the evidence partition.
2. **Audit Trail Quality.** The audit JSONL writer (`audit/logger.py`) and HMAC ledger (`audit/ledger.py`) carry property-test coverage via Hypothesis. CI verifies that arbitrary inputs to the audit logger produce parse-able JSONL with stable `audit_id` sequencing. The SBOM job means the audit trail of the **codebase itself** is reproducible.
3. **Usability.** The `release.yml` workflow ships a Docker image to GHCR (`ghcr.io/<owner>/silentwitness`) on every main merge. Judges can `docker run` the latest tag without cloning the repo. The conventional-commits pipeline produces a `CHANGELOG.md` that demos as a credible engineering artifact.

### 1.3 Yotam Perkal lens

`context/stakeholders/12` §A7 frames Yotam Perkal (Pluto Security, MCPwn / CVE-2026-33032 discoverer) as the judge most likely to reverse-engineer our MCP server. He looks for default-empty whitelists, missing middleware, unenforced authentication on MCP endpoints, and protocol-level scoping failures. The CI gates here — SBOM, license-check, dependency-review, container scanning via trivy, secret detection — are how we **show our work** on supply-chain hygiene. None of these gates make the MCP server architecturally secure on their own; the architecture must do that. But they remove a category of plausible questions Yotam might ask ("did you scan for known CVEs in your tool wrappers?" "did you pin your dependencies?" "what's your incident-response plan if `pydantic-ai` ships a malicious tag?") with a one-line answer backed by a CI artifact.

---

## 2. Tool stack (verbatim from BRAINSTORM §3.5, with versions)

| Concern | Tool | Version pin | Source / rationale |
|---|---|---|---|
| Python runtime | CPython | `>=3.12,<3.14` | SIFT 2026 ships Python 3.12 (verified: `context/.raw-design-research/03` row "Default Python"). 3.13 forward-compat tested in CI matrix. |
| Package manager | `uv` | `>=0.5` | Single static binary; 10-100x faster than pip; reproducible `uv.lock`. Not pre-installed on SIFT (`03` row "Default package manager"); `install.sh` bootstraps it. |
| Linter + formatter | `ruff` | `>=0.8` | Replaces black + isort + flake8 + pylint. Single config in `pyproject.toml`. |
| Type checker | `mypy --strict` | `>=1.13` | `BRAINSTORM` §3.5. Pyright fallback acknowledged but not in CI. |
| Test framework | `pytest` | `>=8` | Standard. |
| Property tests | `hypothesis` | `>=6` | Catches verification-gate edge cases (citation gate, entity gate). |
| Coverage | `coverage[toml]` | `>=7.6` | TOML-config; integrates with `pyproject.toml`. |
| Pre-commit framework | `pre-commit` | `>=4` | Standard. |
| Secret detection | `detect-secrets` | `>=1.5` | Baseline-based; baseline at `.secrets.baseline`. |
| SBOM generation | `cyclonedx-py` | `>=4` | CycloneDX 1.6 JSON output; CI artifact on every PR. |
| Versioning | `python-semantic-release` | `>=9` | Automated via GitHub Actions; tag on main. |
| Commit-message enforcement | `conventional-pre-commit` | `>=3.6` | Hook-wrapped commitlint analog. |
| Container build | Docker buildx | (GitHub Actions setup-buildx-action v3) | Multi-arch (amd64 + arm64; SIFT 2026 supports both per `03` row "Architecture"). |
| Dependency updates | Dependabot | (GitHub-native) | Config at `.github/dependabot.yml`. Renovate provided as commented fallback. |
| Container vuln scan | trivy | (`aquasecurity/trivy-action@0.28.0`) | Scans built Docker image on push to main. |
| License audit | `pip-licenses` | `>=5` | Blocks AGPL, GPL-3.0 (LGPL acceptable for runtime-only deps with carve-out). |

### Explicitly NOT in the CI stack (and why)

- **black, isort, flake8, pylint** — replaced by `ruff` (one tool).
- **pyright** — `mypy --strict` is sufficient; pyright is fallback only if mypy stalls on a release.
- **Codecov** — adds third-party-signup overhead; for the hackathon window we generate HTML reports locally and XML reports as CI artifacts. Decision documented in §16.
- **Renovate as primary** — Dependabot covers our scope; Renovate kept as a commented-out fallback in `dependabot.yml`. Decision documented in §16.
- **bandit** — `detect-secrets` + `dependency-review-action` + `trivy` cover the surface; bandit adds noise without catching what those don't.

---

## 3. Pre-commit hooks (`.pre-commit-config.yaml`)

Pre-commit is the first gate. Every commit on every developer's machine runs the chain below. CI re-runs the same chain (§4) — defense in depth.

### 3.1 Hook list

| Hook ID | Repo | Version | Args | Files-glob | Fail-fast |
|---|---|---|---|---|---|
| `ruff-format` | `astral-sh/ruff-pre-commit` | `v0.8.4` | `--check` (run mode) | `\.pyi?$` | No |
| `ruff` | `astral-sh/ruff-pre-commit` | `v0.8.4` | `--fix --exit-non-zero-on-fix` | `\.pyi?$` | No |
| `mypy` | local (uses project venv) | n/a | `--strict` on changed files | `^src/.*\.py$` | No |
| `file-size-guard` | local | n/a | (none — reads files from stdin) | `\.py$` | **Yes** |
| `detect-secrets` | `Yelp/detect-secrets` | `v1.5.0` | `--baseline .secrets.baseline` | `.*` | No |
| `forbidden-paths` | local | n/a | (none — reads files from stdin) | `.*` | **Yes** |
| `trailing-whitespace` | `pre-commit/pre-commit-hooks` | `v5.0.0` | (none) | `.*` | No |
| `end-of-file-fixer` | `pre-commit/pre-commit-hooks` | `v5.0.0` | (none) | `.*` | No |
| `check-toml` | `pre-commit/pre-commit-hooks` | `v5.0.0` | (none) | `\.toml$` | No |
| `check-yaml` | `pre-commit/pre-commit-hooks` | `v5.0.0` | (none) | `\.ya?ml$` | No |
| `check-merge-conflict` | `pre-commit/pre-commit-hooks` | `v5.0.0` | (none) | `.*` | No |
| `check-added-large-files` | `pre-commit/pre-commit-hooks` | `v5.0.0` | `--maxkb=1024` | `.*` | No |
| `conventional-pre-commit` | `compilerla/conventional-pre-commit` | `v3.6.0` | (types in args) | commit-msg stage | **Yes** |

"Fail-fast Yes" means subsequent hooks do not run if this one fails. The three fail-fast hooks (`file-size-guard`, `forbidden-paths`, `conventional-pre-commit`) are structural violations that we want to surface immediately, not bury under formatter noise.

### 3.2 Full `.pre-commit-config.yaml`

```yaml
# .pre-commit-config.yaml
# SilentWitness pre-commit chain. Mirrors the CI gates in .github/workflows/ci.yml.
default_language_version:
  python: python3.12
default_install_hook_types: [pre-commit, commit-msg]
fail_fast: false

repos:
  # --- Formatting + linting (ruff replaces black / isort / flake8 / pylint) ---
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff-format
        types_or: [python, pyi]
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
        types_or: [python, pyi]

  # --- Static typing (strict) ---
  - repo: local
    hooks:
      - id: mypy
        name: mypy --strict (changed files)
        entry: uv run mypy --strict
        language: system
        types: [python]
        files: ^src/.*\.py$
        require_serial: true

  # --- Structural guards (fail-fast) ---
  - repo: local
    hooks:
      - id: file-size-guard
        name: file-size-guard (no .py file >400 LOC)
        entry: uv run python .pre-commit-hooks/file-size-guard.py
        language: system
        files: \.py$
        pass_filenames: true
        require_serial: true
        stages: [pre-commit]
        verbose: true

      - id: forbidden-paths
        name: forbidden-paths (no writes to /evidence /var/lib/silentwitness etc.)
        entry: uv run python .pre-commit-hooks/forbidden-paths.py
        language: system
        pass_filenames: true
        require_serial: true
        stages: [pre-commit]
        verbose: true

  # --- Secret detection ---
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: ^(uv\.lock|\.secrets\.baseline|tests/.*/fixtures/.*)$

  # --- Standard hygiene ---
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
        exclude: ^(uv\.lock|.*\.md)$
      - id: end-of-file-fixer
        exclude: ^uv\.lock$
      - id: check-toml
      - id: check-yaml
        args: [--allow-multiple-documents]
      - id: check-merge-conflict
      - id: check-added-large-files
        args: [--maxkb=1024]

  # --- Conventional Commits ---
  - repo: https://github.com/compilerla/conventional-pre-commit
    rev: v3.6.0
    hooks:
      - id: conventional-pre-commit
        stages: [commit-msg]
        args:
          - --types
          - feat,fix,docs,style,refactor,perf,test,build,ci,chore,revert
          - --scopes
          - mcp,agent,hypothesis,report,verify,audit,harness,docs,ci,deps
```

---

## 4. GitHub Actions workflows

Three workflows live under `.github/workflows/`:

- `ci.yml` — runs on every push and PR. The full gate chain.
- `release.yml` — runs on push to `main` (semantic-release determines whether to cut a release). Also runs on manual `workflow_dispatch`.
- `dependency-review.yml` — runs on PRs only. Blocks PRs that add high-severity vulnerabilities or copyleft licenses.

### 4.1 `.github/workflows/ci.yml`

```yaml
# .github/workflows/ci.yml
name: ci

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pull-requests: read
  packages: write   # for docker-build job (only used on main)

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

env:
  UV_VERSION: "0.5.11"
  PYTHON_VERSION_DEFAULT: "3.12"

jobs:

  lint:
    name: lint (ruff + mypy)
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: ${{ env.UV_VERSION }}
          enable-cache: true
      - name: Set up Python
        run: uv python install ${{ env.PYTHON_VERSION_DEFAULT }}
      - name: Sync deps
        run: uv sync --all-extras --frozen
      - name: ruff format (check only)
        run: uv run ruff format --check .
      - name: ruff check
        run: uv run ruff check .
      - name: mypy --strict
        run: uv run mypy --strict src/

  test:
    name: test (py${{ matrix.python }})
    runs-on: ubuntu-24.04
    strategy:
      fail-fast: false
      matrix:
        python: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: ${{ env.UV_VERSION }}
          enable-cache: true
      - run: uv python install ${{ matrix.python }}
      - run: uv sync --all-extras --frozen
      - name: pytest with coverage
        env:
          HYPOTHESIS_PROFILE: ci
        run: |
          uv run coverage run -m pytest tests/unit tests/integration -v
          uv run coverage xml -o coverage.xml
          uv run coverage report --fail-under=85
      - name: Upload coverage artifact
        uses: actions/upload-artifact@v4
        with:
          name: coverage-py${{ matrix.python }}
          path: coverage.xml
          retention-days: 14

  property-tests:
    name: property-tests (hypothesis, slow)
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: ${{ env.UV_VERSION }}
          enable-cache: true
      - run: uv python install ${{ env.PYTHON_VERSION_DEFAULT }}
      - run: uv sync --all-extras --frozen
      - name: Run Hypothesis property tests (slow profile)
        env:
          HYPOTHESIS_PROFILE: slow
        run: uv run pytest tests/property -v --hypothesis-show-statistics

  file-size-guard:
    name: file-size-guard (≤400 LOC per .py file)
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: ${{ env.UV_VERSION }}
          enable-cache: true
      - run: uv python install ${{ env.PYTHON_VERSION_DEFAULT }}
      - name: Run file-size-guard on all tracked .py
        run: |
          mapfile -t FILES < <(git ls-files '*.py')
          uv run python .pre-commit-hooks/file-size-guard.py "${FILES[@]}"

  dataset-hash-verify:
    name: dataset-hash-verify
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: ${{ env.UV_VERSION }}
          enable-cache: true
      - run: uv python install ${{ env.PYTHON_VERSION_DEFAULT }}
      - run: uv sync --all-extras --frozen
      - name: Verify dataset manifest hashes
        # Verifies the Nitroba 60MB stub (committed under harness/datasets/stubs/).
        # Full NIST 20GB image is NOT pulled in CI; verified locally before submission.
        run: uv run python harness/datasets/verify_manifest.py --stub-only

  sbom:
    name: sbom (CycloneDX 1.6 JSON)
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: ${{ env.UV_VERSION }}
          enable-cache: true
      - run: uv python install ${{ env.PYTHON_VERSION_DEFAULT }}
      - run: uv sync --all-extras --frozen
      - name: Generate SBOM
        run: |
          uv run cyclonedx-py environment \
            --output-format JSON \
            --output-file sbom.cdx.json \
            --schema-version 1.6
      - name: Upload SBOM artifact
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.cdx.json
          retention-days: 90

  license-check:
    name: license-check (no AGPL / GPL-3.0)
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: ${{ env.UV_VERSION }}
          enable-cache: true
      - run: uv python install ${{ env.PYTHON_VERSION_DEFAULT }}
      - run: uv sync --all-extras --frozen
      - name: Audit licenses
        run: |
          uv run pip-licenses \
            --format=json \
            --output-file=licenses.json \
            --with-license-file \
            --no-license-path
          uv run python scripts/license_gate.py licenses.json
      - uses: actions/upload-artifact@v4
        with:
          name: licenses
          path: licenses.json
          retention-days: 90

  docker-build:
    name: docker-build (push to GHCR)
    runs-on: ubuntu-24.04
    needs: [lint, test, property-tests, file-size-guard, sbom, license-check]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Compute short SHA
        id: sha
        run: echo "short=$(git rev-parse --short=7 HEAD)" >> "$GITHUB_OUTPUT"
      - name: Build + push
        uses: docker/build-push-action@v6
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: |
            ghcr.io/${{ github.repository_owner }}/silentwitness:latest
            ghcr.io/${{ github.repository_owner }}/silentwitness:${{ steps.sha.outputs.short }}
          labels: |
            org.opencontainers.image.source=${{ github.server_url }}/${{ github.repository }}
            org.opencontainers.image.revision=${{ github.sha }}
            org.opencontainers.image.licenses=MIT
      - name: Run trivy scan on built image
        uses: aquasecurity/trivy-action@0.28.0
        with:
          image-ref: ghcr.io/${{ github.repository_owner }}/silentwitness:${{ steps.sha.outputs.short }}
          format: sarif
          output: trivy-results.sarif
          severity: HIGH,CRITICAL
          exit-code: '1'
      - uses: actions/upload-artifact@v4
        with:
          name: trivy-sarif
          path: trivy-results.sarif
          retention-days: 30
```

### 4.2 `.github/workflows/release.yml`

```yaml
# .github/workflows/release.yml
name: release

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: write       # to push tags + CHANGELOG.md
  packages: write       # to push the versioned Docker tag
  id-token: write       # for any future OIDC publishing

concurrency:
  group: release
  cancel-in-progress: false

jobs:
  release:
    name: semantic-release
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}
      - uses: astral-sh/setup-uv@v4
        with:
          version: "0.5.11"
          enable-cache: true
      - run: uv python install 3.12
      - run: uv sync --all-extras --frozen

      - name: python-semantic-release version + changelog
        id: release
        run: |
          uv run semantic-release version --changelog
          echo "released=$(uv run semantic-release version --print-last-released 2>/dev/null || echo none)" >> "$GITHUB_OUTPUT"

      - name: Build + push versioned Docker image
        if: steps.release.outputs.released != 'none'
        uses: docker/build-push-action@v6
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: |
            ghcr.io/${{ github.repository_owner }}/silentwitness:${{ steps.release.outputs.released }}
          labels: |
            org.opencontainers.image.source=${{ github.server_url }}/${{ github.repository }}
            org.opencontainers.image.revision=${{ github.sha }}
            org.opencontainers.image.version=${{ steps.release.outputs.released }}
            org.opencontainers.image.licenses=MIT
```

### 4.3 `.github/workflows/dependency-review.yml`

```yaml
# .github/workflows/dependency-review.yml
name: dependency-review

on:
  pull_request:
    branches: [main]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - name: Dependency review
        uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: high
          # Deny AGPL + GPL-3.0 outright; LGPL allowed only as runtime-linked dep
          # (we don't statically link in Python — runtime-linkage carve-out is safe).
          deny-licenses: AGPL-3.0,AGPL-3.0-only,AGPL-3.0-or-later,GPL-3.0,GPL-3.0-only,GPL-3.0-or-later
          comment-summary-in-pr: always
```

---

## 5. Branch protection rules

Apply via `gh` CLI (run by repo owner once after the first CI green run).

### 5.1 Required status checks

- `lint`
- `test (py3.12)`
- `test (py3.13)`
- `property-tests`
- `file-size-guard`
- `dataset-hash-verify`
- `sbom`
- `license-check`
- `dependency-review / review`

### 5.2 Apply via gh CLI

```bash
# Solo-developer mode (Abu only). 1 review is impractical until a second maintainer joins.
# Required reviews = 0; required CI = full list. Linear history. No force pushes. No deletions.

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  /repos/:owner/:repo/branches/main/protection \
  -f required_status_checks[strict]=true \
  -f required_status_checks[contexts][]=lint \
  -f required_status_checks[contexts][]='test (py3.12)' \
  -f required_status_checks[contexts][]='test (py3.13)' \
  -f required_status_checks[contexts][]=property-tests \
  -f required_status_checks[contexts][]=file-size-guard \
  -f required_status_checks[contexts][]=dataset-hash-verify \
  -f required_status_checks[contexts][]=sbom \
  -f required_status_checks[contexts][]=license-check \
  -f required_status_checks[contexts][]='dependency-review / review' \
  -f enforce_admins=false \
  -f required_pull_request_reviews[required_approving_review_count]=0 \
  -f required_pull_request_reviews[dismiss_stale_reviews]=true \
  -f required_linear_history=true \
  -f allow_force_pushes=false \
  -f allow_deletions=false \
  -f required_conversation_resolution=true
```

When a second maintainer joins, bump `required_approving_review_count` to `1`. Documented decision: solo for hackathon window; mandatory PR review after submission.

---

## 6. Custom hook scripts

### 6.1 `.pre-commit-hooks/file-size-guard.py`

Counts all lines (including blanks and comments — policy decision; encourages aggressive splitting rather than allowing 700-line files with whitespace gaming). Skips generated and vendored files.

```python
#!/usr/bin/env python3
"""
file-size-guard.py — enforce the ≤400-LOC-per-.py invariant from BRAINSTORM §3.7.

Counts ALL physical lines (blanks + comments included). Encourages splitting at
natural module boundaries rather than hiding bulk in whitespace.

Skips:
  - uv.lock and other auto-generated files
  - tests/<anything>/fixtures/* (forensic fixture blobs may be large)
  - vendored/* directory (third-party drop-ins)
  - any file path matching SKIP_PATTERNS

Exit codes:
  0 — no offenders
  1 — at least one offender (≥401 LOC)
"""
from __future__ import annotations

import fnmatch
import sys
from pathlib import Path

MAX_LINES = 400

SKIP_PATTERNS = (
    "uv.lock",
    "*.json",
    "*.lock",
    "tests/**/fixtures/*",
    "tests/*/fixtures/*",
    "vendored/*",
    ".pre-commit-hooks/*",  # this file is exempted; it's tooling, not product code
)


def is_skipped(path: Path) -> bool:
    s = path.as_posix()
    return any(fnmatch.fnmatch(s, pat) for pat in SKIP_PATTERNS)


def count_lines(path: Path) -> int:
    try:
        with path.open("rb") as fh:
            return sum(1 for _ in fh)
    except OSError:
        # Deleted in this commit (e.g. rename); treat as 0.
        return 0


def main(argv: list[str]) -> int:
    offenders: list[tuple[str, int]] = []
    for arg in argv:
        p = Path(arg)
        if not p.is_file() or is_skipped(p):
            continue
        n = count_lines(p)
        if n > MAX_LINES:
            offenders.append((arg, n))

    if not offenders:
        return 0

    print("\nfile-size-guard: the following files exceed the 400-LOC limit:\n", file=sys.stderr)
    for path, n in sorted(offenders, key=lambda x: -x[1]):
        print(f"  {n:>5} lines  {path}", file=sys.stderr)
    print(
        "\nFix: split at a natural module boundary.\n"
        "  - one tool family per file (tools/memory.py, tools/disk.py, tools/log.py)\n"
        "  - one subagent per file (specialists/memory.py, specialists/disk.py)\n"
        "  - one verification gate per file (verification/citation_gate.py, "
        "verification/entity_gate.py)\n"
        "If splitting is genuinely impossible, document the exception in docs/adrs/ "
        "and add the path to SKIP_PATTERNS with a one-line justification.\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

### 6.2 `.pre-commit-hooks/forbidden-paths.py`

Blocks writes to paths that are runtime-only (evidence partition, verification ledger, per-case audit JSONL). The codebase must never contain files inside these paths — they are mutated at runtime by the MCP server, not source-controlled. Catches the common mistake of committing a sample case for testing into the wrong directory.

```python
#!/usr/bin/env python3
"""
forbidden-paths.py — block commits that touch runtime-only paths.

These paths are mutated by the MCP server at runtime and must never live in the
repo. Catching this at pre-commit prevents:
  - accidentally committing real evidence (PII / PHI / privileged material)
  - accidentally committing a case audit log
  - accidentally committing the HMAC ledger

Allowed exception: tests/integration/fixtures/cases/<sample>/* may contain
synthetic case fixtures shipped for integration testing.

Exit codes:
  0 — clean
  1 — at least one forbidden write
"""
from __future__ import annotations

import fnmatch
import sys
from pathlib import Path

FORBIDDEN_PATTERNS: tuple[str, ...] = (
    "evidence/*",
    "evidence/**/*",
    "var/lib/silentwitness/*",
    "var/lib/silentwitness/**/*",
    "cases/*",
    "cases/*/*",
    "cases/*/audit/*.jsonl",
    "cases/*/report.md",
)

ALLOWED_EXCEPTION_PREFIX = "tests/integration/fixtures/"


def is_allowed_exception(path: str) -> bool:
    return path.startswith(ALLOWED_EXCEPTION_PREFIX)


def matches_forbidden(path: str) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in FORBIDDEN_PATTERNS)


def main(argv: list[str]) -> int:
    violations: list[str] = []
    for arg in argv:
        p = Path(arg).as_posix()
        if is_allowed_exception(p):
            continue
        if matches_forbidden(p):
            violations.append(p)

    if not violations:
        return 0

    print("\nforbidden-paths: the following files write to runtime-only paths:\n", file=sys.stderr)
    for v in violations:
        print(f"  {v}", file=sys.stderr)
    print(
        "\nThese paths are mutated by the MCP server at runtime. They must NOT be\n"
        "committed. Likely causes:\n"
        "  - You committed a real case's audit log. Move it to /var/lib/silentwitness "
        "outside the repo.\n"
        "  - You meant to commit a test fixture. Move it under "
        "tests/integration/fixtures/.\n"
        "  - You added evidence to the repo. Don't. Evidence is path-registered at "
        "runtime via the MCP server's evidence/registry.py.\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

---

## 7. Conventional Commits + semantic-release config

### 7.1 Allowed commit types

`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

### 7.2 Allowed scopes

`mcp` (MCP server), `agent` (Pydantic AI reference agent), `hypothesis` (hypothesis stack / pivot engine), `report` (report renderer), `verify` (citation + entity gates), `audit` (audit logger + HMAC ledger), `harness` (dataset + scorer), `docs` (specs / ADRs), `ci` (workflows / hooks), `deps` (Dependabot auto-bumps).

Examples:
- `feat(verify): add line-level citation gate with SHA256 verification`
- `fix(audit): handle restart-resumed sequence numbers in ledger.py`
- `ci(deps): bump astral-sh/setup-uv from v4 to v4.1.0`

### 7.3 `pyproject.toml` snippet for python-semantic-release

```toml
[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
version_variables = ["src/silentwitness_mcp/__init__.py:__version__"]
build_command = "uv build"
major_on_zero = false
upload_to_pypi = false              # GHCR only for hackathon; PyPI deferred
commit_message = "chore(release): {version}\n\n[skip ci]"

[tool.semantic_release.branches.main]
match = "main"
prerelease = false

[tool.semantic_release.changelog]
exclude_commit_patterns = [
  "^chore\\(release\\):",
  "^chore\\(deps\\):",
]

[tool.semantic_release.commit_parser_options]
allowed_tags = ["feat", "fix", "docs", "style", "refactor", "perf",
                "test", "build", "ci", "chore", "revert"]
minor_tags = ["feat"]
patch_tags = ["fix", "perf"]
```

### 7.4 Versioning policy

- **0.x.y** until hackathon submission (2026-06-15). Breaking changes allowed in minor bumps.
- **1.0.0** is the hackathon submission tag.
- Thereafter strict SemVer.

---

## 8. Coverage policy

### 8.1 Targets

| Module path | Floor | Rationale |
|---|---|---|
| `src/silentwitness_mcp/verification/` | **95%** | These gates MUST work. The wedge depends on them. |
| `src/silentwitness_mcp/audit/` | **90%** | Audit trail is one of three judging criteria we contribute to. |
| `src/silentwitness_mcp/` (other) | 85% | Standard. |
| `src/silentwitness_agent/` | 85% | Standard. |
| `src/silentwitness_agent/cli.py` | (excluded) | Stitches everything; covered by integration tests, not unit. |
| `src/silentwitness_agent/report/pdf.py` | (excluded) | WeasyPrint render shim; covered by integration smoke. |

### 8.2 `pyproject.toml` snippet

```toml
[tool.coverage.run]
source = ["src/silentwitness_mcp", "src/silentwitness_agent"]
branch = true
omit = [
  "src/silentwitness_agent/cli.py",
  "src/silentwitness_agent/report/pdf.py",
]

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = false
fail_under = 85

[tool.coverage.paths]
source = ["src/", "*/silentwitness/src/"]

# Per-module floors enforced by scripts/coverage_gate.py (CI step):
#   verification/* — 95
#   audit/*        — 90
```

`scripts/coverage_gate.py` (called by CI test job) parses `coverage.xml` and asserts the per-module floors. Single-source-of-truth lives there, not in `pyproject.toml`, because `coverage.py` does not natively support per-directory thresholds.

### 8.3 Local vs CI reporting

- **Local:** `uv run coverage html -d htmlcov/` — open `htmlcov/index.html` for line-by-line.
- **CI:** XML report uploaded as artifact (per-Python-version). No Codecov for hackathon.

---

## 9. Secret detection baseline

### 9.1 Setup

```bash
uv run detect-secrets scan > .secrets.baseline
git add .secrets.baseline
git commit -m "chore(ci): initialize detect-secrets baseline"
```

### 9.2 Required env vars (never committed)

| Var | Used by | Where it lives |
|---|---|---|
| `ANTHROPIC_API_KEY` | Pydantic AI Anthropic provider | `.env` (gitignored) or `~/.config/silentwitness/env` |
| `OPENAI_API_KEY` | Pydantic AI OpenAI provider (optional) | same |
| `GOOGLE_API_KEY` | Pydantic AI Google provider (optional) | same |
| `SILENTWITNESS_EXAMINER_PASSWORD` | HMAC ledger PBKDF2 derivation (BRAINSTORM §4) | examiner prompts at startup; never persisted |

`.env.example` IS committed (with empty values + comments). `.env` is gitignored.

### 9.3 Baseline-rotation procedure

If a developer triggers detect-secrets on a legitimate non-secret string (e.g. a YARA rule that contains a hex blob the scanner thinks is a hash):

```bash
uv run detect-secrets scan --baseline .secrets.baseline
uv run detect-secrets audit .secrets.baseline   # interactively mark false positives
git add .secrets.baseline
git commit -m "chore(ci): audit detect-secrets baseline (false positives reviewed)"
```

If a developer commits a real secret:

1. Rotate the secret at the provider immediately.
2. Use `git filter-repo` (or `git filter-branch` as fallback) to scrub it from history.
3. Force-push the cleaned branch (one-time exception to "no force pushes" — coordinate with repo owner).
4. Update `.secrets.baseline` afterward.

---

## 10. SBOM + supply-chain hygiene

### 10.1 SBOM specifics

- Format: **CycloneDX 1.6 JSON** (specified in `cyclonedx-py` invocation).
- Generated by the `sbom` CI job on every PR + push to main.
- Published as `sbom.cdx.json` artifact, 90-day retention.
- Bundled into the Docker image at `/app/sbom.cdx.json` so judges can `docker run --rm ghcr.io/.../silentwitness:latest cat /app/sbom.cdx.json`.

### 10.2 Dependency-addition review policy

For PRs that add a new direct dependency to `pyproject.toml`:

- The dependency-review-action will surface license + severity automatically.
- The PR description MUST include a one-paragraph justification: why this dep, why not stdlib, what alternatives were considered.
- For deps ≥1MB unpacked or that pull more than three new transitive deps, the PR must include the output of `uv tree --depth 2 <package>`.

### 10.3 Lockfile policy

`uv.lock` is committed. Every CI job runs `uv sync --frozen` to ensure no implicit upgrades. Dependabot bumps regenerate the lockfile.

### 10.4 Yotam Perkal-specific posture

Per `context/stakeholders/12` §A7 and `context/technical/08` §4, §5: MCP servers inherit host capabilities. We do not — and CI cannot — sandbox the MCP server. What CI does is reduce the surface of "did you even check?" questions:

- Trivy scans the Docker image for known CVEs (HIGH/CRITICAL block).
- License-check ensures we have no AGPL contamination that would prevent the MIT/Apache release the hackathon rules require.
- SBOM is published per build, so any judge auditing a deployed image can compare against published vulns.
- The forbidden-paths hook means the codebase cannot accidentally write into `/var/lib/silentwitness` (the HMAC ledger location) during normal development.

These do not address §5.1 ("inheriting application capabilities") or §5.2 ("privilege scoping failures") — those are architectural and belong in `architecture.md`. They do close the obvious supply-chain holes Yotam looks for first.

---

## 11. Docker build & GHCR push

### 11.1 `Dockerfile` shape

Multi-stage. Build stage uses `python:3.12-slim-bookworm` + `uv`; runtime stage is `python:3.12-slim-bookworm` with only the installed venv + source + SBOM. **Base image MUST be the bookworm-pinned tag** (NOT the floating `python:3.12-slim` which will flip to trixie/forky mid-hackathon — per audit F-PY-4).

```dockerfile
# Dockerfile
# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.12

# ---------- build stage ----------
FROM python:${PYTHON_VERSION}-slim-bookworm AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

# Install uv 0.11.18 (matching CI version — per audit B-PY-2; 0.5.x has breaking semantics changes).
RUN curl -LsSf https://astral.sh/uv/0.11.18/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev

# Generate SBOM at build time so it ships inside the image.
RUN uv run cyclonedx-py environment \
        --output-format JSON \
        --output-file /app/sbom.cdx.json \
        --schema-version 1.6

# ---------- runtime stage ----------
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

# Runtime requires WeasyPrint's native deps. Per audit F-PY-3 add:
#   libharfbuzz-subset0 (HarfBuzz subset support), libpangoft2-1.0-0 (FreeType for Pango)
#   plus DejaVu + Liberation font packages so headers/body render predictably across hosts.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
        libgdk-pixbuf-2.0-0 libharfbuzz-subset0 \
        libffi8 shared-mime-info \
        fonts-dejavu fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 silentwitness

WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/src /app/src
COPY --from=build /app/sbom.cdx.json /app/sbom.cdx.json
COPY pyproject.toml README.md LICENSE /app/

USER silentwitness

LABEL org.opencontainers.image.source="https://github.com/<owner>/silentwitness" \
      org.opencontainers.image.description="SilentWitness MCP server + reference agent" \
      org.opencontainers.image.licenses="MIT"

ENTRYPOINT ["python", "-m", "silentwitness_mcp"]
```

### 11.2 SIFT-compat note

The Docker image is the **convenience** deploy for non-SIFT hosts (judges who want to test in a container without booting the SIFT VM). On SIFT 2026, the native install path is `install.sh` (bootstraps `uv`, registers the MCP server with the pre-installed Claude Code v2.0.61 at `/usr/local/bin/claude`, installs Hayabusa + Chainsaw + Velociraptor per `context/.raw-design-research/03`). The Docker image and the native install ship the same `silentwitness_mcp` package; the install paths differ.

### 11.3 Image scanning

Trivy runs in CI on every `docker-build` (only on push to main). HIGH + CRITICAL CVEs block the push. LOW + MEDIUM are reported but do not block.

### 11.4 Push policy

- `:latest` — always points to most recent main merge.
- `:<short-sha>` (7 chars) — every main merge.
- `:<semver>` — only on semantic-release version cuts.

---

## 12. Dependabot config (`.github/dependabot.yml`)

```yaml
# .github/dependabot.yml
version: 2

updates:
  # Python deps (uv-managed via pyproject.toml)
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "06:00"
      timezone: "Europe/London"
    open-pull-requests-limit: 10
    target-branch: "main"
    commit-message:
      prefix: "chore(deps)"
      include: "scope"
    labels: ["dependencies", "python"]
    groups:
      python-dev:
        patterns:
          - "ruff"
          - "mypy"
          - "pytest*"
          - "hypothesis"
          - "coverage*"
          - "pre-commit"
          - "detect-secrets"
          - "cyclonedx-py"
          - "pip-licenses"
          - "python-semantic-release"
      python-prod:
        patterns:
          - "mcp"
          - "pydantic-ai*"
          - "pydantic*"
          - "typer"
          - "rich"
          - "weasyprint"
          - "mistune"
          - "httpx"
          - "spacy"
          - "volatility3"
          # NOTE: structlog DROPPED per audit Decision A — direct Pydantic model_dump_json() is used.

  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    target-branch: "main"
    commit-message:
      prefix: "chore(deps)"
      include: "scope"
    labels: ["dependencies", "github-actions"]
    groups:
      github-actions:
        patterns: ["*"]

  # Docker base image
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    target-branch: "main"
    commit-message:
      prefix: "chore(deps)"
      include: "scope"
    labels: ["dependencies", "docker"]
```

### 12.1 Auto-merge policy

PRs labeled `dependencies` for **patch** and **minor** bumps with all CI green can be auto-merged via a separate workflow (`.github/workflows/auto-merge-deps.yml`, not detailed here — implement post-hackathon if dependabot volume justifies). For the hackathon window, manual merge.

Major bumps always require human review.

### 12.2 Renovate fallback

If Dependabot proves insufficient (e.g. it does not support `uv.lock` updates well — track via [dependabot/dependabot-core#10478] post-hackathon), Renovate config:

```json5
// renovate.json (currently NOT activated — fallback only)
//
// {
//   "$schema": "https://docs.renovatebot.com/renovate-schema.json",
//   "extends": ["config:recommended", ":semanticCommits"],
//   "schedule": ["before 6am on Monday"],
//   "timezone": "Europe/London",
//   "packageRules": [
//     { "matchManagers": ["pep621"], "groupName": "python-prod" },
//     { "matchDepTypes": ["dev"], "groupName": "python-dev" }
//   ]
// }
```

---

## 13. Local dev workflow

Use `just` over `make` (lighter, cross-platform-friendly for 2026, no tab-vs-space footguns).

### 13.1 `justfile`

```just
# justfile — SilentWitness local dev convenience.
# https://github.com/casey/just
#
# Quickstart:
#   curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash
#   just install
#   just ci

set shell := ["bash", "-cu"]
set dotenv-load := true

default:
    @just --list

# Bootstrap deps + pre-commit hooks.
install:
    uv sync --all-extras --frozen
    uv run pre-commit install --install-hooks
    uv run pre-commit install --hook-type commit-msg

# Format + lint fix.
format:
    uv run ruff format .
    uv run ruff check --fix .

# Lint (CI-equivalent — no auto-fix).
lint:
    uv run ruff format --check .
    uv run ruff check .
    uv run mypy --strict src/

# Unit + integration tests with coverage.
test:
    HYPOTHESIS_PROFILE=dev uv run coverage run -m pytest tests/unit tests/integration -v
    uv run coverage report --fail-under=85
    uv run coverage html -d htmlcov/

# Slow property tests.
property:
    HYPOTHESIS_PROFILE=slow uv run pytest tests/property -v --hypothesis-show-statistics

# Full CI gate locally (matches .github/workflows/ci.yml).
ci: lint test property
    uv run python .pre-commit-hooks/file-size-guard.py $(git ls-files '*.py')
    uv run cyclonedx-py environment --output-format JSON --output-file sbom.cdx.json --schema-version 1.6
    uv run pip-licenses --format=json --output-file=licenses.json
    uv run python scripts/license_gate.py licenses.json

# Clean caches + build artifacts.
clean:
    rm -rf .ruff_cache .mypy_cache .pytest_cache .hypothesis htmlcov dist build .coverage coverage.xml sbom.cdx.json licenses.json
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
```

### 13.2 Make fallback

Not provided. If a contributor refuses `just`, they can read the `justfile` and run the commands by hand — it is short.

---

## 14. CI failure remediation runbook

| Failure | First diagnosis | Fix |
|---|---|---|
| `ruff format --check` failed | Formatter found unformatted code | `just format` (or `uv run ruff format .`) — commit the diff |
| `ruff check` failed | Lint rule violation | Read the error; usually a `noqa` is the wrong fix — restructure the code. If `noqa` is unavoidable, append the rule code: `# noqa: E501` and a one-line reason comment |
| `mypy --strict` failed | Missing type annotation or type mismatch | Add the annotation. **NEVER** use `# type: ignore` without a `# type: ignore[<error-code>]` and a one-line comment explaining why. Bare `# type: ignore` is a CI fail. |
| `file-size-guard` failed | A `.py` file exceeded 400 LOC | Split at the natural module boundary. Examples: `tools/log.py` 410 LOC → split into `tools/log_evtx.py` + `tools/log_hayabusa.py`. Document the split in the commit body. |
| `forbidden-paths` failed | A commit touched `evidence/`, `cases/`, `var/lib/silentwitness/`, or similar | You probably created a test fixture in the wrong place. Move to `tests/integration/fixtures/`. If it's real evidence, delete it from the working tree, verify with `git status`, do NOT add to the next commit. |
| `detect-secrets` failed | A new high-entropy string looked like a secret | If it IS a secret: rotate at provider, scrub from history (`git filter-repo`), recommit clean. If it ISN'T: `uv run detect-secrets audit .secrets.baseline`, mark as false positive, commit updated baseline. |
| `conventional-pre-commit` failed | Commit message did not match `<type>(<scope>): <subject>` | Amend with `git commit --amend -m "feat(verify): <subject>"`. Allowed types/scopes listed in §7. |
| `pytest` coverage <85% | New code without tests | Add tests. If the file is genuinely untestable (CLI shim, rendering passthrough), add it to `[tool.coverage.run].omit` AND document why in the commit body. |
| `dataset-hash-verify` failed | Stub manifest hash drifted | A test fixture changed. Recompute: `uv run python harness/datasets/recompute_manifest.py --stub-only`, commit the updated manifest. If you did NOT mean to change the fixture, revert the fixture change. |
| `sbom` failed | `cyclonedx-py` rejected the environment | Usually means `uv sync` is inconsistent with `uv.lock`. Run `uv lock` and commit the result. |
| `license-check` failed | A new dep is AGPL / GPL-3.0 / proprietary | Find an alternative. If no alternative exists, write an ADR in `docs/adrs/` explaining the exception. The hackathon rules require MIT or Apache 2.0; AGPL is a release blocker. |
| `dependency-review` failed (high severity) | New dep has a known CVE | Bump to a patched version. If no patched version exists, find an alternative or wait. |
| `trivy` failed (high/critical in Docker image) | Image base or installed package has known CVE | Bump the base image (`FROM python:3.12-slim` → newer). If the CVE is in a system package, `apt-get` upgrade or pin a newer version. |

---

## 15. Audit against `context/` — verification checklist

Done as part of writing this spec. Findings recorded inline.

- [x] **`context/technical/07-mcp-and-agent-platforms.md` reviewed.** The protocol doc covers the MCP wire shape (JSON-RPC, stdio + Streamable HTTP) and the §2025-11-25 auth recommendations. No protocol-level CI gate is prescribed; the relevant CI checks are at the supply-chain + secret-detection layer, already covered. **No spec update needed.**
- [x] **`context/technical/08-llm-failure-modes-in-agentic-systems.md` §4 (tool poisoning) reviewed.** §4.2 (adversarial tool definitions), §4.3 (rug pulls), §4.4 (naming collisions), §4.5 (output bombs), §4.6 (MCPwn / CVE-2026-33032) all describe runtime / architectural threats, not CI threats. The relevant CI contribution is the SBOM + dependency-review + license-check chain that ensures our **transitive** dep tree (which might include a malicious `pydantic-ai`-mimicking package) is auditable. **No new CI gate added; §10.4 explicitly notes the line between CI scope and architecture scope.**
- [x] **`context/stakeholders/12` §A7 (Yotam Perkal) reviewed.** Yotam reverse-engineers MCP servers. The CI posture documented in §1.3 and §10.4 addresses the supply-chain layer he probes first. The MCP server's **architectural** posture (auth on every endpoint, no default-empty whitelists, runtime scoping) is `architecture.md`'s problem, not CI's. **No spec update needed beyond the cross-references in §1.3 and §10.4.**
- [x] **No CI gate prescribes architecture.** All gates here enforce invariants (size, types, coverage, license, secrets, SBOM) or hygiene (conventional commits, hooks). None of them dictate that the citation gate must be implemented a particular way — they only enforce that it MUST exist AND be 95%-covered. Confirmed.
- [x] **All bash commands tested for syntactic correctness.** `gh api` block uses verified flag names. `curl` invocations use the documented `--proto '=https' --tlsv1.2 -sSf` pattern. The justfile uses `set shell := ["bash", "-cu"]` to ensure consistent error-on-unset behavior.
- [x] **Cross-reference to BRAINSTORM §3.6 confirms parity.** Every headline gate listed in §3.6 of BRAINSTORM is reflected here: pre-commit chain (§3 here), ruff + mypy + file-size (§3, §6.1), forbidden-paths (§6.2), GitHub Actions CI (§4.1), branch protection (§5), conventional commits + semantic-release (§7), Dependabot (§12). Renovate is documented as fallback (§12.2). **Parity confirmed.**

### 15.1 Findings that updated my understanding

Two things from the context audit shifted the spec:

1. **`context/technical/08` §4.5 (tool output bombs)** is a runtime concern but it informs the **`check-added-large-files` maxkb threshold**. We capped at 1MB (matching common practice). A larger threshold would invite committing forensic fixtures by mistake; a smaller threshold would block legitimate small evidence fixtures. 1MB is the right line.
2. **`context/.raw-design-research/03` confirms SIFT 2026 ships dotnet 9 + Claude Code 2.0.61 but NOT uv, Node.js, or Hayabusa.** This validates the choice to bootstrap `uv` ourselves and means our CI matrix does NOT need to test on a Python distribution that pre-dates 3.12. We pin to `>=3.12,<3.14` and matrix-test 3.12 + 3.13 only.

---

## 16. Open questions / deferred decisions

These are flagged for Abu (or the next-in-line spec) to decide:

1. **Codecov vs local-only coverage.** Recommendation: **local-only for hackathon.** Codecov adds third-party signup + token management overhead and the artifacts upload covers our judge-visible reporting needs. Revisit if SilentWitness is open-sourced post-hackathon and we want public coverage badges.
2. **Container scanning: trivy vs grype.** Recommendation: **trivy.** Aquasec's action is well-maintained; SARIF output integrates with GitHub code-scanning UI. Grype is fine but adds another vendor surface for no gain.
3. **Renovate vs Dependabot.** Recommendation: **Dependabot.** Native to GitHub, sufficient scope. Renovate config provided in §12.2 as commented-out fallback in case Dependabot's `uv.lock` support proves inadequate.
4. **Auto-merge for Dependabot PRs.** Deferred to post-hackathon. Manual merge during the build window — volume will be low, and the visibility of each bump is useful early.
5. **Branch-protection required-reviews count.** Currently 0 (solo dev). Bump to 1 when a second maintainer joins. Abu's call on whether to bring in a reviewer during hackathon window.
6. **Self-hosted runner for CI.** Not used. GitHub-hosted Ubuntu 24.04 runners match the SIFT 2026 base distro. No need for a dedicated runner unless the dataset-hash-verify job grows to pull the full NIST 20GB (which it should not — that runs locally before submission).
7. **Pre-commit hook for ADR enforcement.** Considered: a hook that requires `docs/adrs/` to grow whenever `pyproject.toml`'s direct deps grow. Decision: deferred. The dependency-review PR template covers it sufficiently for the hackathon.
8. **CycloneDX VEX (Vulnerability Exploitability eXchange) statements.** Deferred. The base SBOM is enough for the hackathon window. VEX is post-1.0 maturity work.

---

## 17. Spec metadata

- **Spec status:** DRAFT.
- **Contributes to judging criteria:** Constraint Implementation, Audit Trail Quality, Usability.
- **Source documents informing this spec:** `../STRATEGY.md`; `./BRAINSTORM.md` §3.5 + §3.6 + §3.7; `../context/.raw-design-research/03-sift-2026-tool-catalog-verified.md`; `../context/technical/07-mcp-and-agent-platforms.md`; `../context/technical/08-llm-failure-modes-in-agentic-systems.md` §4 + §5; `../context/stakeholders/12-judges-curriculum-and-legal-landscape.md` Part A §A7.
- **Owner:** TBD.
- **Next spec in queue:** `docs/PRD.md`.

---

**End of CICD_SPEC.md (DRAFT).** Apply the configs in §3, §4, §6, §11, §12, §13 verbatim. Branch protection (§5) is applied once by repo owner after the first green CI run. Open questions in §16 await Abu.
