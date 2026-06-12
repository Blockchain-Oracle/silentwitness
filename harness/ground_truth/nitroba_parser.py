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

from pydantic import ValidationError  # noqa: E402

from harness.ground_truth.schema import GroundTruthFinding  # noqa: E402

_JSON_PATH = Path(__file__).resolve().parent / "nitroba.handcrafted.json"


def parse() -> list[GroundTruthFinding]:
    """Return ≥6 GroundTruthFinding objects for the Nitroba wardrive challenge."""
    try:
        text = _JSON_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"Cannot read {_JSON_PATH}: {exc}. This file must be committed in the repo."
        ) from exc
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in {_JSON_PATH}: {exc}") from exc
    findings: list[GroundTruthFinding] = []
    for i, item in enumerate(raw):
        try:
            findings.append(GroundTruthFinding.model_validate(item))
        except ValidationError as exc:
            raise ValueError(
                f"Validation error in {_JSON_PATH}, item {i} (id={item.get('id', '?')}): {exc}"
            ) from exc
    return findings
