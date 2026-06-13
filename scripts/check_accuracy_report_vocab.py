#!/usr/bin/env python3
"""Gate: docs/ACCURACY_REPORT.md — PRD §14 vocab + Rob T. Lee verbatim-quote ban.

Rules: doc_exists / max_lines / sixteen_h2 / first_h2 / last_h2 / no_banned /
no_verbatim_quote / tldr_table / residuals_caught / residuals_uncaught.

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
_AUDIT_ID_RE = re.compile(r"sift-[a-z0-9]+-\d{8}-\d{3}")


def _fail(rule: str, detail: str = "") -> int:
    print(
        f"ACCURACY_REPORT gate FAIL: {rule}" + (f" — {detail}" if detail else ""), file=sys.stderr
    )
    return 1


def check(doc_path: Path = _DOC) -> int:
    if not doc_path.exists():
        return _fail("doc_exists", str(doc_path))
    try:
        text = doc_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _fail("doc_unreadable", str(exc))
    lines = text.splitlines()
    if len(lines) > _MAX:
        return _fail("max_lines", f"{len(lines)} > {_MAX}")
    h2s = [ln for ln in lines if ln.startswith("## ")]
    if len(h2s) < 16:
        return _fail("sixteen_h2", f"only {len(h2s)} H2 sections; require 16")
    if not h2s[0].startswith(_FIRST_H2):
        return _fail("first_h2", f"expected {_FIRST_H2!r}, got {h2s[0]!r}")
    if not any(ln.startswith(_LAST_H2) for ln in h2s):
        return _fail("last_h2", f"expected {_LAST_H2!r}")
    for phrase in _BANNED:
        if phrase.lower() in text.lower():
            return _fail("no_banned", f"{phrase!r}")
    for phrase in _VERBATIM_FORBIDDEN:
        if phrase in text:
            return _fail("no_verbatim_quote", f"{phrase[:40]!r}...")
    # TL;DR table: 3 dataset rows with no "TBD" placeholders
    tldr_idx = text.find("## TL;DR")
    next_h2 = text.find("\n## ", tldr_idx + 1)
    tldr_section = text[tldr_idx : next_h2 if next_h2 > 0 else len(text)]
    if "TBD" in tldr_section:
        return _fail("tldr_table", "TL;DR contains 'TBD' placeholder")
    for dataset in ("Nitroba", "Data Leakage", "Hacking Case"):
        if dataset not in tldr_section:
            return _fail("tldr_table", f"missing {dataset!r} row")
    # Residual hallucinations sections
    caught_idx = text.find("## Residual hallucinations we caught")
    if caught_idx < 0:
        return _fail("residuals_caught", "section missing")
    next_h2 = text.find("\n## ", caught_idx + 1)
    caught_section = text[caught_idx : next_h2 if next_h2 > 0 else len(text)]
    audit_ids = _AUDIT_ID_RE.findall(caught_section)
    if len(audit_ids) < 3:
        return _fail(
            "residuals_caught",
            f"need >=3 audit_id citations matching {_AUDIT_ID_RE.pattern}; found {len(audit_ids)}",
        )
    uncaught_idx = text.find("## Residual hallucinations we did NOT catch")
    if uncaught_idx < 0:
        return _fail("residuals_uncaught", "section missing")
    next_h2 = text.find("\n## ", uncaught_idx + 1)
    uncaught_section = text[uncaught_idx : next_h2 if next_h2 > 0 else len(text)]
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
