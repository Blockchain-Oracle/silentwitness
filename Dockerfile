# Dockerfile — verbatim from CICD_SPEC §11.1 with one substitution: the
# OCI label `org.opencontainers.image.source` resolves the spec's `<owner>`
# placeholder to the actual repo URL.
#
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

# Generate SBOM at build time so it ships inside the image. `cyclonedx-bom`
# is a dev-group dep (it's a build-time tool, never runs in production), so
# we install it ephemerally via `uv run --with` rather than pulling the
# whole dev group into the runtime venv. Spec (§11.1) invokes plain
# `uv run cyclonedx-py …` but that fails on the `--no-dev` venv produced
# above — PR-90 silent-failure review surfaced this.
RUN uv run --with 'cyclonedx-bom>=7' cyclonedx-py environment \
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

# Prepare runtime-mutable paths with the correct ownership BEFORE the USER
# directive. Without this, the silentwitness-ledger named volume (mounted at
# /var/lib/silentwitness in compose) masks any chown done at runtime, and the
# first ledger write fails with PermissionError. mode 0700 matches the
# architecture §4.9 enforcement.
RUN mkdir -p /var/lib/silentwitness \
    && chown -R 10001:10001 /var/lib/silentwitness \
    && chmod 0700 /var/lib/silentwitness

WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/src /app/src
COPY --from=build /app/sbom.cdx.json /app/sbom.cdx.json
COPY pyproject.toml README.md LICENSE /app/

USER silentwitness

LABEL org.opencontainers.image.source="https://github.com/Blockchain-Oracle/silentwitness" \
      org.opencontainers.image.description="SilentWitness MCP server + reference agent" \
      org.opencontainers.image.licenses="MIT"

# ENTRYPOINT is the MCP stdio server. NOTE for this PR: src/silentwitness_mcp/
# currently has no __main__.py, so a bare `docker run` will exit non-zero with
# "No module named __main__". Epic 2's first story ships the real
# silentwitness_mcp.__main__ entrypoint. Until then, the image is usable via
# `docker run silentwitness:test python -c 'import silentwitness_mcp'` (the
# healthcheck path) but not as a stdio server.
ENTRYPOINT ["python", "-m", "silentwitness_mcp"]
