"""SilentWitness MCP server — typed-tool MCP server for SANS SIFT forensics.

THE product of the SilentWitness submission. Wraps SIFT forensic tools as
Pydantic-typed MCP tools, gated by citation + entity verifiability checks.
See ``docs/architecture.md`` §4 for the deep spec.
"""

# ``__version__`` is the source of truth for the package version; mirrored in
# pyproject.toml at ``project.version`` and bumped automatically on Conventional
# Commits via python-semantic-release in CI (see ``docs/CICD_SPEC.md`` §7.3).
# Triple-quoted strings after module-level assignments do NOT attach as
# docstrings to the variable in CPython — keep this rationale as a real ``#``
# comment so it survives ``help()`` / ``__doc__`` lookups truthfully.
__version__ = "1.4.1"
