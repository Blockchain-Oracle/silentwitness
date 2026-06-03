#!/usr/bin/env python3
"""forbidden-paths.py — block commits that touch runtime-only paths.

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
