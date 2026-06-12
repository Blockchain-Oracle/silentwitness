"""case-trapdoor ground-truth parser (Epic 15 stub).

Returns [] if case-trapdoor.synthetic.json is absent (Epic 15 optional).
Does NOT raise on absence — the scorer skips this dataset gracefully when empty.
Raises RuntimeError if the file is present but invalid (corrupt JSON or schema mismatch).
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

_SYNTHETIC_JSON = Path(__file__).resolve().parent / "case-trapdoor.synthetic.json"


def parse() -> list[GroundTruthFinding]:
    """Return synthetic findings if Epic 15 has shipped, else []."""
    if not _SYNTHETIC_JSON.exists():
        print(
            "case-trapdoor not yet synthesised (Epic 15 optional)",
            file=sys.stderr,
        )
        return []
    try:
        raw = json.loads(_SYNTHETIC_JSON.read_text(encoding="utf-8"))
        return [GroundTruthFinding.model_validate(item) for item in raw]
    except (json.JSONDecodeError, OSError, ValidationError) as exc:
        raise RuntimeError(
            f"case-trapdoor synthetic JSON at {_SYNTHETIC_JSON} is present but invalid: {exc}"
        ) from exc
