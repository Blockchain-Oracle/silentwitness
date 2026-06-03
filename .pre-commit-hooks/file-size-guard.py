#!/usr/bin/env python3
"""file-size-guard.py — enforce the ≤400-LOC-per-.py invariant from BRAINSTORM §3.7.

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
