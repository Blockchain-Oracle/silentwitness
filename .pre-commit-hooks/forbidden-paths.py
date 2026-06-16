#!/usr/bin/env python3
"""forbidden-paths.py — block commits that touch runtime-only paths.

These paths are mutated by the MCP server at runtime and must never live in
the repo. Catching this at pre-commit prevents:

  - accidentally committing real evidence (PII / PHI / privileged material)
  - accidentally committing a case audit log
  - accidentally committing the HMAC ledger

Allowed exception: ``tests/integration/fixtures/`` may contain synthetic
case fixtures shipped for integration testing.

------------------------------------------------------------------------------
Implementation notes — prefix matching, not fnmatch
------------------------------------------------------------------------------
``fnmatch`` against patterns like ``cases/*/audit/*.jsonl`` does NOT cross
``/`` boundaries, so a path like
``cases/case-001/notes/x.md`` evades EVERY ``cases/*`` pattern silently.
That's the primary attack-surface bypass on the exact PII/PHI leak this hook
exists to defend.

This implementation closes the bypass by:

  1. ``_normalise``-ing every input to a repo-relative POSIX form
     (backslashes → forward slashes; strip leading ``./``).
  2. Matching forbidden ROOTS via ``startswith`` prefix-check — recursive
     by construction.
  3. Rejecting absolute paths (``/`` prefix) with exit 2: pre-commit and
     ``git ls-files`` emit relative paths only, so an absolute path means
     the upstream caller is mis-invoked and the gate cannot reason about
     repo-relative semantics.

What ``_normalise`` does NOT do — by design:

  - Resolve ``..`` parent segments. ``PurePosixPath`` doesn't, and
     calling ``Path.resolve()`` would couple to the filesystem and to
     ``cwd``. Pre-commit rejects ``..`` in staged paths upstream, so it's
     not in this gate's threat model.
  - Convert Windows drive letters (``C:\\``). Pre-commit on Windows
     emits POSIX-style paths; if someone passes ``C:\\...`` manually the
     leading-``/`` reject above catches it after backslash conversion.

Exit codes:
  0 — clean
  1 — at least one forbidden write
  2 — input shape unrecognisable (absolute path), gate cannot run
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


class AbsolutePathRejectedError(ValueError):
    """Raised when an absolute path is passed — the gate works on repo-relative inputs."""


def _normalise(raw: str) -> str:
    """Return a repo-relative POSIX form.

    - Converts ``\\`` → ``/`` (Windows-style input).
    - Strips one or more leading ``./`` segments.
    - Raises ``AbsolutePathRejectedError`` if the result still starts with ``/``
      after backslash conversion. Absolute paths are out of scope: pre-commit
      and ``git ls-files`` emit relative paths only.
    - Empty string is preserved (caller handles it).
    """
    s = raw.replace("\\", "/")
    if s.startswith("/"):
        raise AbsolutePathRejectedError(raw)
    while s.startswith("./"):
        s = s[2:]
    if not s:
        return ""
    return PurePosixPath(s).as_posix()


def is_allowed_exception(path: str) -> bool:
    return path.startswith(ALLOWED_EXCEPTION_PREFIX)


def matches_forbidden(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)


def main(argv: list[str]) -> int:
    violations: list[str] = []
    for arg in argv:
        try:
            p = _normalise(arg)
        except AbsolutePathRejectedError:
            print(
                f"forbidden-paths: ABSOLUTE PATH rejected: {arg!r}. "
                "This gate operates on repo-relative paths only — pre-commit and "
                "git ls-files emit relative paths. If you invoked the script "
                "manually with an absolute path, re-invoke from the repo root with "
                "the relative form.",
                file=sys.stderr,
            )
            return 2
        if not p:
            # Empty arg — pre-commit shouldn't emit these; skip silently.
            continue
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
