"""Per-module coverage floors — CICD_SPEC §8.1 / §8.2.

coverage.py only enforces a single global ``fail_under`` floor. The wedge
demands tighter floors on the verification gates (95 %) and the audit trail
(90 %) — this script parses ``coverage.xml`` (Cobertura format) and asserts
per-directory line-rate floors.

Floors:
    src/silentwitness_mcp/verification/  →  95 %
    src/silentwitness_mcp/audit/         →  90 %
    everything else under src/           →  85 %

Invoked from .github/workflows/ci.yml `test` job after `coverage xml`. Exits:
    0  every bucket meets its floor (or the bucket genuinely has no files yet)
    1  one or more buckets miss their floor
    2  the XML is broken or empty (gate cannot run — fail loud)

A gate that defaults to PASS on weird input is worse than useless — this
script fails loud on empty / no-``<class>`` XML so an upstream pytest or
coverage-xml regression cannot silently neuter the per-module check.

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
_DEFAULT_LABEL = "src/ (default)"


def _bucket(filename: str) -> tuple[str, int]:
    """Return ``(label, floor)`` for the directory bucket a file belongs to."""
    for prefix, floor in _FLOORS:
        if filename.startswith(prefix):
            return prefix.rstrip("/"), floor
    return _DEFAULT_LABEL, _DEFAULT_FLOOR


def _aggregate(xml_path: Path) -> tuple[int, dict[tuple[str, int], tuple[int, int]]]:
    """Return ``(class_count, {bucket: (covered, total)})`` from Cobertura XML.

    ``class_count`` is the number of ``<class>`` elements seen — used by the
    caller to distinguish "no coverage at all" (broken upstream) from "the
    relevant bucket genuinely has no files yet."
    """
    # S314: coverage.xml is our own CI artifact written by coverage.py one
    # step prior in the same job; not untrusted input.
    tree = ET.parse(xml_path)  # noqa: S314
    totals: dict[tuple[str, int], list[int]] = defaultdict(lambda: [0, 0])
    class_count = 0
    for cls in tree.iter("class"):
        filename = cls.attrib.get("filename", "")
        if not filename:
            # Defensive: real coverage.py output always has filenames. We don't
            # count these toward class_count so an XML with only empty-filename
            # entries still surfaces as "broken" (class_count == 0).
            continue
        class_count += 1
        # Cobertura paths can be relative or prefixed with ./ — normalise so
        # the prefix match against _FLOORS is robust to either form.
        if filename.startswith("./"):
            filename = filename[2:]
        bucket = _bucket(filename)
        for line in cls.iter("line"):
            totals[bucket][1] += 1
            if int(line.attrib.get("hits", "0")) > 0:
                totals[bucket][0] += 1
    return class_count, {k: (v[0], v[1]) for k, v in totals.items()}


def check(xml_path: Path) -> list[tuple[str, int, float]]:
    """Return ``(label, floor, actual_pct)`` for any bucket below its floor.

    Raises ``ValueError`` if the XML contains zero ``<class>`` elements —
    that means the coverage run produced no data and the gate cannot meaningfully
    fire. The caller should surface this as exit 2 (gate broken), distinct from
    exit 1 (gate fired, floors not met).
    """
    class_count, aggregated = _aggregate(xml_path)
    if class_count == 0:
        raise ValueError(
            f"coverage_gate: {xml_path} contains zero <class> elements; "
            "upstream `coverage run` produced no data. Gate cannot run."
        )
    failures: list[tuple[str, int, float]] = []
    for (label, floor), (covered, total) in aggregated.items():
        if total == 0:
            # bucket has files but no executable lines — coverage.py edge case
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
    try:
        failures = check(xml_path)
    except ValueError as exc:
        print(f"coverage_gate: gate broken — {exc}", file=sys.stderr)
        return 2
    except ET.ParseError as exc:
        print(f"coverage_gate: malformed XML at {xml_path}: {exc}", file=sys.stderr)
        return 2
    if failures:
        print("coverage_gate: per-module floors NOT met:", file=sys.stderr)
        for label, floor, pct in failures:
            print(f"  - {label}: {pct:.2f}% < {floor}% (CICD_SPEC §8.1)", file=sys.stderr)
        return 1
    print(f"coverage_gate: OK ({xml_path})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
