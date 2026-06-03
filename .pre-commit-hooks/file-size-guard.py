"""File-size guard — reject any tracked .py file over 400 lines.

The 400-LOC cap (architecture.md §13) keeps modules auditable for the judges:
small enough that a reviewer can hold every branch of a verification gate or
tool wrapper in their head at once. Imported by both:

  - `.pre-commit-config.yaml` (story-pre-commit-hooks — runs on every commit)
  - `.github/workflows/ci.yml` `file-size-guard` job (this story — runs in CI)

LOC = total newline-terminated lines, including blanks and comments. The cap
is intentionally simple: we don't strip comments or docstrings because the
intent is "this file is small," not "this file is dense."

Usage::

    python .pre-commit-hooks/file-size-guard.py path/to/file.py [more.py ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

_LIMIT = 400


def _line_count(path: Path) -> int:
    with path.open("rb") as fh:
        return sum(1 for _ in fh)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return 0
    offenders: list[tuple[Path, int]] = []
    for raw in argv[1:]:
        path = Path(raw)
        if not path.exists() or path.suffix != ".py":
            continue
        n = _line_count(path)
        if n > _LIMIT:
            offenders.append((path, n))
    if offenders:
        print("file-size-guard: files exceed 400-LOC cap (architecture.md §13):", file=sys.stderr)
        for path, n in offenders:
            print(f"  - {path}: {n} lines (> {_LIMIT})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
