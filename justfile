# justfile — SilentWitness local dev convenience.
# https://github.com/casey/just
#
# Verbatim from CICD_SPEC §13.1 plus one story-mandated additions: header
# preamble (this block), macOS Xcode pitfall comment on `install`, and the
# `build` recipe at the bottom.
#
# Quickstart:
#   curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash
#   just install
#   just ci
#
# `just --list` (the `default` target) is the discoverability surface — every
# new contributor runs it first, so each recipe has a one-line comment above
# it explaining what it does.

set shell := ["bash", "-cu"]
set dotenv-load := true

default:
    @just --list

# macOS pitfall: if `uv sync` triggers an Xcode prompt, run `xcode-select --install` once.
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
# cyclonedx-py drops --schema-version (not recognised by cyclonedx-bom 7.x;
# default IS 1.6); license_gate uses --allowlist. Matches ci.yml deviations
# 6 + 7.
ci: lint test property
    uv run python .pre-commit-hooks/file-size-guard.py $(git ls-files '*.py')
    uv run cyclonedx-py environment --output-format JSON --output-file sbom.cdx.json
    uv run pip-licenses --format=json --output-file=licenses.json
    uv run python scripts/license_gate.py licenses.json --allowlist .license-allowlist.json

# Clean caches + build artifacts.
clean:
    rm -rf .ruff_cache .mypy_cache .pytest_cache .hypothesis htmlcov dist build .coverage coverage.xml sbom.cdx.json licenses.json
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Build the Docker image locally (final image = runtime stage from Dockerfile).
build:
    docker build -t silentwitness:local .

# Render docs/diagrams/*.mmd to PNG via mmdc. Run `./install.sh --diagrams` first.
diagrams:
    ./scripts/render_diagrams.sh
