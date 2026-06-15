"""ROCBA hand-crafted ground-truth parser.

SANS ships no formal answer key with the "Fred Rocba" training case — only the
5 Key Questions and the scenario in ROCBA-BACKGROUND.pptx. This parser loads a
ground truth hand-crafted from those briefing facts (subject identity, employer,
remote-access method, cloud-sync exfil channels, intrusion window) — the same
methodology as the nitroba hand-crafted key. It is NON-circular: the expectations
come from the briefing deck, not from the disk evidence the agent reads.

source="hand_crafted" — never "verified" or "official"; there is no official key.
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

_JSON_PATH = Path(__file__).resolve().parent / "rocba.handcrafted.json"


def parse() -> list[GroundTruthFinding]:
    """Return the GroundTruthFinding objects for the ROCBA 5 Key Questions."""
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
