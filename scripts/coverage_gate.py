"""Per-module coverage floors — CICD_SPEC §8.1 / §8.2.

coverage.py only enforces a single global ``fail_under`` floor. The wedge
demands tighter floors on the verification gates (95 %) and the audit trail
(90 %) — this script parses ``coverage.xml`` (Cobertura format) and asserts
per-directory line-rate floors.

Floors:
    src/silentwitness_mcp/verification/  →  95 %
    src/silentwitness_mcp/audit/         →  90 %
    everything else under src/           →  85 %

Invoked from .github/workflows/ci.yml `test` job after `coverage xml`. Exits
non-zero with a stderr message naming every directory that misses its floor.

Usage::

    uv run python scripts/coverage_gate.py coverage.xml
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

_FLOORS: tuple[tuple[str, int], ...] = (
    ("src/silentwitness_mcp/verification/", 95),
    ("src/silentwitness_mcp/audit/", 90),
)
_DEFAULT_FLOOR = 85


def _bucket(filename: str) -> tuple[str, int]:
    """Return ``(label, floor)`` for the directory bucket a file belongs to."""
    for prefix, floor in _FLOORS:
        if filename.startswith(prefix):
            return prefix.rstrip("/"), floor
    return "src/ (default)", _DEFAULT_FLOOR


def _aggregate(xml_path: Path) -> dict[tuple[str, int], tuple[int, int]]:
    """Sum ``(covered_lines, total_lines)`` per bucket from a Cobertura XML."""
    tree = ET.parse(xml_path)  # noqa: S314 — our own CI artifact, not untrusted input
    totals: dict[tuple[str, int], list[int]] = defaultdict(lambda: [0, 0])
    for cls in tree.iter("class"):
        filename = cls.attrib.get("filename", "")
        if not filename:
            continue
        bucket = _bucket(filename)
        for line in cls.iter("line"):
            totals[bucket][1] += 1
            if int(line.attrib.get("hits", "0")) > 0:
                totals[bucket][0] += 1
    return {k: (v[0], v[1]) for k, v in totals.items()}


def check(xml_path: Path) -> list[tuple[str, int, float]]:
    """Return ``(label, floor, actual_pct)`` for any bucket below its floor."""
    failures: list[tuple[str, int, float]] = []
    for (label, floor), (covered, total) in _aggregate(xml_path).items():
        if total == 0:
            continue
        pct = 100.0 * covered / total
        if pct < floor:
            failures.append((label, floor, pct))
    return failures


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <coverage.xml>", file=sys.stderr)
        return 2
    xml_path = Path(argv[1])
    if not xml_path.exists():
        print(f"coverage_gate: {xml_path} does not exist", file=sys.stderr)
        return 2
    failures = check(xml_path)
    if failures:
        print("coverage_gate: per-module floors NOT met:", file=sys.stderr)
        for label, floor, pct in failures:
            print(f"  - {label}: {pct:.2f}% < {floor}% (CICD_SPEC §8.1)", file=sys.stderr)
        return 1
    print(f"coverage_gate: OK ({xml_path})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
