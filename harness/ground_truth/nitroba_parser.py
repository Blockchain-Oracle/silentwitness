"""Nitroba hand-crafted ground-truth parser.

The official DFRWS 2010 solution PDF is password-gated per evaluation
context §A.1. This parser loads the community-converged answer chain from
nitroba.handcrafted.json (committed) and returns the parsed findings.

source="hand_crafted" — never "verified" or "official".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from harness.ground_truth.schema import GroundTruthFinding  # noqa: E402

_JSON_PATH = Path(__file__).resolve().parent / "nitroba.handcrafted.json"


def parse() -> list[GroundTruthFinding]:
    """Return ≥6 GroundTruthFinding objects for the Nitroba wardrive challenge."""
    raw = json.loads(_JSON_PATH.read_text(encoding="utf-8"))
    return [GroundTruthFinding.model_validate(item) for item in raw]
