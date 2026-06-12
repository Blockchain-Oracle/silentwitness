"""CLI: python harness/ground_truth/cli.py <dataset_id>

Prints the parsed GroundTruthFinding list as JSON to stdout.

Exit codes:
  0 — success
  1 — unknown dataset_id
  2 — parser error (fetch failure, SHA256 mismatch, parse error)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from harness.ground_truth import (  # noqa: E402
    case_trapdoor_parser,
    nist_data_leakage_parser,
    nist_hacking_case_parser,
    nitroba_parser,
)

_PARSERS = {
    "nitroba": nitroba_parser.parse,
    "nist-data-leakage": nist_data_leakage_parser.parse,
    "nist-hacking-case": nist_hacking_case_parser.parse,
    "case-trapdoor": case_trapdoor_parser.parse,
}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: cli.py <dataset_id>", file=sys.stderr)
        print(f"Known datasets: {', '.join(_PARSERS)}", file=sys.stderr)
        return 1

    dataset_id = argv[1]
    parser_fn = _PARSERS.get(dataset_id)
    if parser_fn is None:
        print(f"unknown dataset_id: {dataset_id!r}", file=sys.stderr)
        print(f"Known datasets: {', '.join(_PARSERS)}", file=sys.stderr)
        return 1

    try:
        findings = parser_fn()
    except Exception as exc:
        print(f"parser error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps([f.model_dump(mode="json") for f in findings], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
