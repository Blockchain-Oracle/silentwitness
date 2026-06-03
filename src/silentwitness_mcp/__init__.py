"""SilentWitness MCP server — typed-tool MCP server for SANS SIFT forensics.

THE product of the SilentWitness submission. Wraps SIFT forensic tools as
Pydantic-typed MCP tools, gated by citation + entity verifiability checks.
See ``docs/architecture.md`` §5 for the deep spec.
"""

__version__ = "0.1.0"
"""Semantic version pinned by python-semantic-release.

Source of truth for the package version; mirrored in pyproject.toml at
``project.version``. Bumps happen automatically on Conventional Commits via
semantic-release in CI (see ``docs/CICD_SPEC.md`` §7.3).
"""
