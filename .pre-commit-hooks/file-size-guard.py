"""File-size guard — reject any tracked .py file over 400 lines.

The 400-LOC cap (architecture.md §14 — CI gates / file-size-guard) keeps
modules auditable for the judges: small enough that a reviewer can hold every
branch of a verification gate or tool wrapper in their head at once. Imported
by both:

  - ``.pre-commit-config.yaml`` (story-pre-commit-hooks — runs on every commit)
  - ``.github/workflows/ci.yml`` ``file-size-guard`` job (this story — runs in CI)

LOC = total newline-terminated lines, including blanks and comments. The cap
is intentionally simple: we don't strip comments or docstrings because the
intent is "this file is small," not "this file is dense."

Skip patterns (matches CICD_SPEC §6.1 reference implementation):

  - Non-``.py`` suffixes               — guard is .py-only
  - ``tests/**/fixtures/**``           — fixture blobs can be large generated text
  - ``vendored/**``                    — third-party drop-ins ship their own caps
  - ``.pre-commit-hooks/**``           — self-exempt so the guard can grow if
                                         genuinely needed (it can't grow far —
                                         the script itself is ~70 LOC and the
                                         cap is 400)

A non-existent path is loud (stderr warn) rather than silent — pre-commit and
``git ls-files`` only emit real paths, so a missing path indicates an upstream
caller bug worth surfacing.

Usage::

    python .pre-commit-hooks/file-size-guard.py path/to/file.py [more.py ...]
"""

from __future__ import annotations

import sys
from pathlib import Path, PurePosixPath

_LIMIT = 400
# Glob-like prefix patterns (matched against POSIX form of the path).
_SKIP_PREFIXES: tuple[str, ...] = (
    "vendored/",
    ".pre-commit-hooks/",
)
_SKIP_CONTAINS: tuple[str, ...] = ("/fixtures/",)


def _should_skip(posix_path: str) -> bool:
    if any(posix_path.startswith(p) for p in _SKIP_PREFIXES):
        return True
    if any(c in posix_path for c in _SKIP_CONTAINS):
        return True
    return False


def _line_count(raw: str) -> int:
    """Return raw newline count, or -1 if the file does not exist."""
    real = Path(raw)
    if not real.exists():
        return -1
    with real.open("rb") as fh:
        return sum(1 for _ in fh)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return 0
    offenders: list[tuple[str, int]] = []
    missing: list[str] = []
    for raw in argv[1:]:
        posix = PurePosixPath(raw).as_posix()
        if not posix.endswith(".py"):
            continue
        if _should_skip(posix):
            continue
        n = _line_count(raw)
        if n < 0:
            missing.append(raw)
            continue
        if n > _LIMIT:
            offenders.append((raw, n))
    if missing:
        print(
            "file-size-guard: WARN: the following paths do not exist and were skipped:",
            file=sys.stderr,
        )
        for p in missing:
            print(f"  - {p}", file=sys.stderr)
    if offenders:
        print(
            "file-size-guard: files exceed 400-LOC cap (architecture.md §14):",
            file=sys.stderr,
        )
        for path, n in offenders:
            print(f"  - {path}: {n} lines (> {_LIMIT})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
