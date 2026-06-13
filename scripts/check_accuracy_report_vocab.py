#!/usr/bin/env python3
"""Gate: docs/ACCURACY_REPORT.md — PRD §14 vocab + Rob T. Lee verbatim-quote ban.

11 rules — each routes through _fail() so the CI log carries a grep-able slug
instead of a Python traceback:

  doc_exists / doc_unreadable / max_lines / sixteen_h2 / first_h2 / last_h2 /
  section_missing / no_banned / no_verbatim_quote / tldr_table /
  residuals_caught / residuals_uncaught

Exit 0 on pass; 1 with rule slug on stderr.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_DOC = _REPO / "docs" / "ACCURACY_REPORT.md"
_MAX = 500
_BANNED = (
    "court-admissible",
    "autonomous SOC",
    "Ralph Wiggum",
    "replaces L1",
    "eliminates hallucinations",
)
_VERBATIM_FORBIDDEN = (
    "Claude doesn't get defensive when you call it out",
    "Protocol SIFT works. It also hallucinates more than we'd like",
)
_FIRST_H2 = "## Status + scope"
_LAST_H2 = "## Appendix B — Glossary"
_REQUIRED_SECTIONS = (
    "## TL;DR",
    "## Residual hallucinations we caught",
    "## Residual hallucinations we did NOT catch",
)
_AUDIT_ID_RE = re.compile(r"sift-[a-z0-9]+-\d{8}-\d{3}")


def _fail(rule: str, detail: str = "") -> int:
    print(
        f"ACCURACY_REPORT gate FAIL: {rule}" + (f" — {detail}" if detail else ""), file=sys.stderr
    )
    return 1


def _section_slice(text: str, heading: str) -> str:
    """Return the text from `heading` up to the next ## (or EOF)."""
    idx = text.find(heading)
    if idx < 0:
        return ""
    next_h2 = text.find("\n## ", idx + 1)
    return text[idx : next_h2 if next_h2 > 0 else len(text)]


def check(doc_path: Path = _DOC) -> int:
    if not doc_path.exists():
        return _fail("doc_exists", str(doc_path))
    try:
        text = doc_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _fail("doc_unreadable", str(exc))
    # Normalize Unicode apostrophe to ASCII so paste-from-Notion doesn't bypass
    # the verbatim-quote ban.
    text = text.replace("’", "'")  # noqa: RUF001  Unicode → ASCII normalization
    lines = text.splitlines()
    if len(lines) > _MAX:
        return _fail("max_lines", f"{len(lines)} > {_MAX}")
    h2s = [ln for ln in lines if ln.startswith("## ")]
    if len(h2s) < 16:
        return _fail("sixteen_h2", f"only {len(h2s)} H2 sections; require >=16")
    if not h2s[0].startswith(_FIRST_H2):
        return _fail("first_h2", f"expected {_FIRST_H2!r}, got {h2s[0]!r}")
    if not any(ln.startswith(_LAST_H2) for ln in h2s):
        return _fail("last_h2", f"expected {_LAST_H2!r}")
    # Preflight: required sections must exist before we slice into them.
    for heading in _REQUIRED_SECTIONS:
        if heading not in text:
            return _fail("section_missing", heading)
    for phrase in _BANNED:
        if phrase.lower() in text.lower():
            return _fail("no_banned", f"{phrase!r}")
    for phrase in _VERBATIM_FORBIDDEN:
        if phrase in text:
            return _fail("no_verbatim_quote", f"{phrase[:40]!r}...")
    tldr_section = _section_slice(text, "## TL;DR")
    if "TBD" in tldr_section:
        return _fail("tldr_table", "TL;DR contains 'TBD' placeholder")
    for dataset in ("Nitroba", "Data Leakage", "Hacking Case"):
        if dataset not in tldr_section:
            return _fail("tldr_table", f"missing {dataset!r} row")
    caught_section = _section_slice(text, "## Residual hallucinations we caught")
    audit_ids = set(_AUDIT_ID_RE.findall(caught_section))
    if len(audit_ids) < 3:
        return _fail(
            "residuals_caught",
            f"need >=3 unique audit_id citations matching {_AUDIT_ID_RE.pattern}; "
            f"found {len(audit_ids)}",
        )
    uncaught_section = _section_slice(text, "## Residual hallucinations we did NOT catch")
    bullets = sum(1 for ln in uncaught_section.splitlines() if ln.strip().startswith("- "))
    if bullets < 2:
        return _fail("residuals_uncaught", f"need >=2 bullet entries; found {bullets}")
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Check docs/ACCURACY_REPORT.md against story gate.",
    )
    parser.add_argument("--doc", type=Path, default=_DOC)
    args = parser.parse_args(argv)
    return check(args.doc)


if __name__ == "__main__":
    sys.exit(main())
