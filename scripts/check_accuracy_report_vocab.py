#!/usr/bin/env python3
"""Gate for docs/ACCURACY_REPORT.md.

Validates what *matters* about the accuracy report (per the Find Evil! rules' Stage-One
check 8 and the panel rubric), not a frozen section template:

  * no banned marketing vocab (and no verbatim organizer quotes);
  * the rubric-required substance is present — a recall/measurement section, the
    hallucination controls we catch, an evidence-integrity section, and an honest
    limitations/known-issues section (false negatives / misses);
  * no unfilled placeholders (TBD/DRAFT);
  * stays within a readable length.

Exit 0 = pass; exit 1 = fail with a `gate: <rule> — <detail>` line on stderr.
"""

from __future__ import annotations

import sys
from pathlib import Path

_DOC = Path(__file__).resolve().parents[1] / "docs" / "ACCURACY_REPORT.md"

_BANNED = (
    "court-admissible",
    "autonomous soc",
    "ralph wiggum",
    "replaces l1",
    "eliminates hallucinations",
)
_VERBATIM_FORBIDDEN = (
    "Claude doesn't get defensive when you call it out",
    "Protocol SIFT works. It also hallucinates more than we'd like",
)
# Substance the report must address (case-insensitive substring match). Each entry is a
# tuple of acceptable synonyms — any one satisfies the requirement.
_REQUIRED = (
    ("recall",),
    ("hallucination", "citation gate", "entity gate"),
    ("evidence integrity",),
    ("known issue", "false negative", "limitation", "not hiding", "what is noisy"),
    ("self-correction", "critic"),
)
_MAX_LINES = 500


def _fail(rule: str, detail: str = "") -> int:
    print(f"gate: {rule} — {detail}", file=sys.stderr)
    return 1


def check(doc_path: Path = _DOC) -> int:
    if not doc_path.exists():
        return _fail("missing", str(doc_path))
    text = doc_path.read_text(encoding="utf-8")
    lower = text.lower()

    if len(text.splitlines()) > _MAX_LINES:
        return _fail("too_long", f">{_MAX_LINES} lines")
    for phrase in _BANNED:
        if phrase in lower:
            return _fail("banned", repr(phrase))
    for phrase in _VERBATIM_FORBIDDEN:
        if phrase in text:
            return _fail("verbatim_quote", repr(phrase))
    for placeholder in ("tbd", "todo:", "lorem ipsum"):
        if placeholder in lower:
            return _fail("placeholder", repr(placeholder))
    for synonyms in _REQUIRED:
        if not any(s in lower for s in synonyms):
            return _fail("section_missing", " / ".join(synonyms))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    doc = _DOC
    if "--doc" in args:
        doc = Path(args[args.index("--doc") + 1])
    elif args:
        doc = Path(args[0])
    return check(doc)


if __name__ == "__main__":
    sys.exit(main())
