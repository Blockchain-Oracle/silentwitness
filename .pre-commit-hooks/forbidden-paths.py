#!/usr/bin/env python3
"""forbidden-paths.py — block commits that touch runtime-only paths.

These paths are mutated by the MCP server at runtime and must never live in
the repo. Catching this at pre-commit prevents:

  - accidentally committing real evidence (PII / PHI / privileged material)
  - accidentally committing a case audit log
  - accidentally committing the HMAC ledger

Allowed exception: ``tests/integration/fixtures/`` may contain synthetic
case fixtures shipped for integration testing (CICD_SPEC §6.2).

------------------------------------------------------------------------------
Deviation from CICD_SPEC §6.2 verbatim
------------------------------------------------------------------------------
The §6.2 reference impl uses ``fnmatch`` against patterns like
``cases/*/audit/*.jsonl``. ``fnmatch`` does NOT cross ``/`` boundaries, so a
path like ``cases/case-001/notes/analyst-scratch.md`` evades EVERY ``cases/*``
pattern in §6.2 — silently. PR-89 silent-failure review found this as the
primary attack-surface bypass for the exact PII/PHI leak the hook claims to
defend.

The same review found that ``str.startswith("tests/integration/fixtures/")``
doesn't normalise ``./`` or absolute paths, so ``./cases/...`` evades both
the forbidden check AND the carve-out asymmetrically.

This implementation:

  1. Normalises every input to a repo-relative POSIX form (strip leading
     ``./``, resolve ``..`` if any).
  2. Matches forbidden roots via ``startswith`` prefix-check, which is
     recursive by construction — ``cases/`` blocks everything under it.
  3. Layers the carve-out on top using the same normalised prefix.

CICD_SPEC §6.2 text should be updated to match.

Exit codes:
  0 — clean
  1 — at least one forbidden write
"""

from __future__ import annotations

import sys
from pathlib import PurePosixPath

FORBIDDEN_PREFIXES: tuple[str, ...] = (
    "evidence/",
    "var/lib/silentwitness/",
    "cases/",
)

ALLOWED_EXCEPTION_PREFIX = "tests/integration/fixtures/"


def _normalise(raw: str) -> str:
    """Repo-relative POSIX form. Strips leading ``./`` and converts ``\\`` → ``/``."""
    s = PurePosixPath(raw).as_posix()
    while s.startswith("./"):
        s = s[2:]
    return s


def is_allowed_exception(path: str) -> bool:
    return path.startswith(ALLOWED_EXCEPTION_PREFIX)


def matches_forbidden(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)


def main(argv: list[str]) -> int:
    violations: list[str] = []
    for arg in argv:
        p = _normalise(arg)
        if is_allowed_exception(p):
            continue
        if matches_forbidden(p):
            violations.append(p)

    if not violations:
        return 0

    print(
        "\nforbidden-paths: the following files write to runtime-only paths "
        "(architecture.md §14):\n",
        file=sys.stderr,
    )
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
