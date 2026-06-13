#!/usr/bin/env python3
"""Gate: docs/DATASETS.md is structurally complete per story-dataset-doc.

Validates section order, manifest cross-references, memorization-risk disclosure
verbatim, and PRD §14 vocab discipline.

Exit 0 on pass; 1 with the failing rule name on stderr.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_DOC = _REPO / "docs" / "DATASETS.md"
_MANIFEST_DIR = _REPO / "harness" / "datasets"
_MAX_LINES = 400

# PRD §9 verbatim memorization-risk paragraph (must appear in NIST Hacking Case section)
_MEMO_RISK_PARAGRAPH = (
    "Greg Schardt / Mr. Evil canonical answers (MAC, IP, hostname, email) "
    "appear in hundreds of indexed writeups."
)
_BANNED_VOCAB = (
    "court-admissible",
    "autonomous SOC",
    "Ralph Wiggum",
    "replaces L1",
    "eliminates hallucinations",
)
_REQUIRED_H2 = (
    "## At a glance",
    "## Reproducibility recipe",
    "## Nitroba University Harassment",
    "## NIST CFReDS Data Leakage Case",
    "## NIST CFReDS Hacking Case",
    "## case-trapdoor",
)


def _fail(rule: str, detail: str = "") -> int:
    msg = f"DATASETS gate FAIL: {rule}"
    if detail:
        msg += f" — {detail}"
    print(msg, file=sys.stderr)
    return 1


def check() -> int:
    if not _DOC.exists():
        return _fail("doc_exists", f"{_DOC} missing")
    text = _DOC.read_text(encoding="utf-8")
    lines = text.splitlines()

    if len(lines) > _MAX_LINES:
        return _fail("max_lines", f"{len(lines)} > {_MAX_LINES}")

    if not any(line.startswith("# Datasets") for line in lines[:5]):
        return _fail("h1", "expected `# Datasets ...` within first 5 lines")

    for heading in _REQUIRED_H2:
        if heading not in text:
            return _fail("required_section", f"missing {heading!r}")

    # Section ordering: each required H2 appears in declared order
    last_idx = -1
    for heading in _REQUIRED_H2:
        idx = text.index(heading)
        if idx < last_idx:
            return _fail("section_order", f"{heading!r} appears out of order")
        last_idx = idx

    # Memorization-risk disclosure must appear in Hacking Case section, verbatim
    hacking_idx = text.index("## NIST CFReDS Hacking Case")
    next_idx = text.find("\n## ", hacking_idx + 1)
    hacking_section = text[hacking_idx : next_idx if next_idx > 0 else len(text)]
    if _MEMO_RISK_PARAGRAPH not in hacking_section:
        return _fail("memorization_risk_disclosure", "verbatim PRD §9 paragraph missing")

    # Nitroba SHA256 cross-reference: must match the manifest
    nitroba_manifest = json.loads((_MANIFEST_DIR / "nitroba.manifest.json").read_text())
    nitroba_sha = nitroba_manifest["sha256"]
    if nitroba_sha not in text:
        return _fail("nitroba_sha_xref", f"manifest sha256 {nitroba_sha} missing in doc")

    # Each dataset section must reference the harness/results/<id>/ delta location
    for slug in ("nitroba", "nist-data-leakage", "nist-hacking-case"):
        if f"harness/results/{slug}/" not in text:
            return _fail("results_link", f"missing harness/results/{slug}/ pointer")

    # Reproducibility recipe must include verify_manifest.py + just harness
    if "verify_manifest.py" not in text:
        return _fail("repro_verify", "reproducibility recipe missing verify_manifest.py step")
    if "just harness" not in text and "harness/baseline" not in text:
        return _fail("repro_harness", "reproducibility recipe missing harness invocation")

    # Banned vocab
    for phrase in _BANNED_VOCAB:
        if phrase.lower() in text.lower():
            return _fail("banned_vocab", f"phrase {phrase!r} present (PRD §14)")

    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Check docs/DATASETS.md against story gate.")
    parser.parse_args(argv)
    return check()


if __name__ == "__main__":
    sys.exit(main())
