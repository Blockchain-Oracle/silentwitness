#!/usr/bin/env python3
"""Gate: docs/DATASETS.md is structurally complete per story-dataset-doc.

Enforces 13 rules (see check() body). All failures route through _fail() so the
CI log carries a grep-able rule slug instead of a Python traceback.

Rules: doc_exists / doc_unreadable / max_lines / h1 / required_section /
section_order / memorization_risk_disclosure / nitroba_sha_xref /
manifest_missing / manifest_corrupt / results_link / repro_recipe /
banned_vocab.

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

# Memorization-risk first SENTENCE. We deliberately match only the first
# sentence; extending the gate to the full paragraph would force this script
# to embed prose that itself drifts. The doc still carries the full paragraph;
# this gate proves the verbatim signature line is present.
_MEMO_RISK_SENTENCE = (
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
    "## Gitignored evidence binaries",
    "## Verification",
    "## Sources + licenses",
)


def _fail(rule: str, detail: str = "") -> int:
    msg = f"DATASETS gate FAIL: {rule}"
    if detail:
        msg += f" — {detail}"
    print(msg, file=sys.stderr)
    return 1


def check(doc_path: Path = _DOC, manifest_dir: Path = _MANIFEST_DIR) -> int:
    """Run all gate rules. Args injected for hermetic test paths."""
    if not doc_path.exists():
        return _fail("doc_exists", f"{doc_path} missing")
    try:
        text = doc_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _fail("doc_unreadable", f"{doc_path}: {exc}")
    lines = text.splitlines()

    if len(lines) > _MAX_LINES:
        return _fail("max_lines", f"{len(lines)} > {_MAX_LINES}")

    if not any(line.startswith("# Datasets") for line in lines[:5]):
        return _fail("h1", "expected `# Datasets ...` within first 5 lines")

    for heading in _REQUIRED_H2:
        if heading not in text:
            return _fail("required_section", f"missing {heading!r}")

    # safe: required_section check above guarantees every heading appears
    last_idx = -1
    for heading in _REQUIRED_H2:
        idx = text.index(heading)
        if idx < last_idx:
            return _fail("section_order", f"{heading!r} appears out of order")
        last_idx = idx

    hacking_idx = text.index("## NIST CFReDS Hacking Case")
    next_idx = text.find("\n## ", hacking_idx + 1)
    hacking_section = text[hacking_idx : next_idx if next_idx > 0 else len(text)]
    if _MEMO_RISK_SENTENCE not in hacking_section:
        return _fail("memorization_risk_disclosure", "verbatim sentence missing")

    nitroba_path = manifest_dir / "nitroba.manifest.json"
    if not nitroba_path.exists():
        return _fail("manifest_missing", f"{nitroba_path}")
    try:
        nitroba_manifest = json.loads(nitroba_path.read_text())
        nitroba_sha = nitroba_manifest["sha256"]
    except (json.JSONDecodeError, KeyError, OSError) as exc:
        return _fail("manifest_corrupt", f"{nitroba_path}: {exc}")
    if nitroba_sha not in text:
        return _fail("nitroba_sha_xref", f"manifest sha256 {nitroba_sha} missing in doc")

    for slug in ("nitroba", "nist-data-leakage", "nist-hacking-case"):
        if f"harness/results/{slug}/" not in text:
            return _fail("results_link", f"missing harness/results/{slug}/ pointer")

    if "verify_manifest.py" not in text or "--strict" not in text:
        return _fail("repro_recipe", "recipe missing verify_manifest.py --strict")
    if "uv run python -m harness" not in text:
        return _fail("repro_recipe", "recipe missing harness module invocation")

    for phrase in _BANNED_VOCAB:
        if phrase.lower() in text.lower():
            return _fail("banned_vocab", f"phrase {phrase!r} present")

    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Check docs/DATASETS.md against story gate.")
    parser.add_argument("--doc", type=Path, default=_DOC)
    parser.add_argument("--manifest-dir", type=Path, default=_MANIFEST_DIR)
    args = parser.parse_args(argv)
    return check(args.doc, args.manifest_dir)


if __name__ == "__main__":
    sys.exit(main())
