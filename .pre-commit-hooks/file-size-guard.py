#!/usr/bin/env python3
"""file-size-guard.py — enforce the ≤400-LOC-per-.py invariant.

The 400-LOC cap (architecture.md §14 — CI gates; rationale in BRAINSTORM
Decisions 6 + 7) keeps modules auditable for the judges: small enough that a
reviewer can hold every branch of a verification gate or tool wrapper in
their head at once.

Counts ALL physical lines (blanks + comments included). Encourages splitting
at natural module boundaries rather than hiding bulk in whitespace.

Skips (CICD_SPEC §6.1 SKIP_PATTERNS):
  - ``uv.lock`` and other auto-generated files
  - ``tests/<anything>/fixtures/*`` (forensic fixture blobs may be large)
  - ``vendored/*`` (third-party drop-ins)
  - ``.pre-commit-hooks/*`` (this hook is tooling, not product code)

------------------------------------------------------------------------------
Two deviations from CICD_SPEC §6.1 verbatim
------------------------------------------------------------------------------
1. ``count_lines`` catches ``FileNotFoundError`` (not the broader ``OSError``).
   The verbatim version's ``except OSError`` silently swallows
   ``PermissionError`` / ``IsADirectoryError`` / disk-read failures — a 5000-
   LOC file chmod 000 would exit clean. The docstring's stated intent is
   ONLY "deleted-in-this-commit (rename)," which ``FileNotFoundError``
   covers exactly. PR-89 silent-failure review flagged this.

2. ``main()`` warns to stderr when a passed path doesn't exist (instead of
   silently skipping). Pre-commit + ``git ls-files`` only emit existing
   paths, so this fires only when an upstream caller has a bug. Story 2's
   version had this warning; the §6.1 rewrite lost it.

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
    ".pre-commit-hooks/*",
    # Typer command registry — every CLI command registers on a single `app =
    # typer.Typer(...)` module-level object. Splitting requires typer.add_typer
    # sub-apps which changes the public CLI surface (docs/ux-spec §2 contract).
    "src/silentwitness_agent/cli.py",
)


def is_skipped(path: Path) -> bool:
    s = path.as_posix()
    return any(fnmatch.fnmatch(s, pat) for pat in SKIP_PATTERNS)


def count_lines(path: Path) -> int:
    """Return raw newline count, or 0 if the file was deleted in this commit."""
    try:
        with path.open("rb") as fh:
            return sum(1 for _ in fh)
    except FileNotFoundError:
        return 0


def main(argv: list[str]) -> int:
    offenders: list[tuple[str, int]] = []
    missing: list[str] = []
    for arg in argv:
        p = Path(arg)
        if not p.exists():
            missing.append(arg)
            continue
        if not p.is_file() or is_skipped(p):
            continue
        n = count_lines(p)
        if n > MAX_LINES:
            offenders.append((arg, n))

    if missing:
        print(
            "file-size-guard: WARN: the following paths do not exist and were skipped:",
            file=sys.stderr,
        )
        for m in missing:
            print(f"  - {m}", file=sys.stderr)

    if not offenders:
        return 0

    print(
        "\nfile-size-guard: files exceed 400-LOC limit (architecture.md §14):\n",
        file=sys.stderr,
    )
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
