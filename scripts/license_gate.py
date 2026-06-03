"""License gate — fail CI if any installed dep ships under a denied license.

Invoked from .github/workflows/ci.yml `license-check` job after pip-licenses
emits licenses.json. The deny list is the hackathon rules' AGPL-3.0 / GPL-3.0
ban plus "UNKNOWN" / "Proprietary" — see CICD_SPEC §4.1 and architecture.md §13.

LGPL is allowed for runtime-linked deps only; Python dynamic linking means we
never trip the LGPL static-link clause (CICD_SPEC §2).

Usage::

    uv run python scripts/license_gate.py licenses.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Denied SPDX identifiers (case-insensitive match). The hyphenated suffixes
# come from CycloneDX-style outputs; the bare forms come from pip-licenses
# Trove classifiers.
_DENIED: frozenset[str] = frozenset(
    {
        "agpl-3.0",
        "agpl-3.0-only",
        "agpl-3.0-or-later",
        "gpl-3.0",
        "gpl-3.0-only",
        "gpl-3.0-or-later",
        "unknown",
        "proprietary",
    }
)


def _entries(payload: object) -> list[dict[str, object]]:
    """pip-licenses emits a top-level JSON array; tolerate a wrapping object too."""
    if isinstance(payload, list):
        return [e for e in payload if isinstance(e, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("packages"), list):
        return [e for e in payload["packages"] if isinstance(e, dict)]
    return []


def _license_strings(entry: dict[str, object]) -> list[str]:
    """A package may list its license under `License` (pip-licenses) or as a
    `Classifier` list. Normalise both to lowercase strings for matching."""
    out: list[str] = []
    lic = entry.get("License")
    if isinstance(lic, str):
        out.append(lic.strip().lower())
    classifiers = entry.get("LicenseClassifier")
    if isinstance(classifiers, list):
        out.extend(c.strip().lower() for c in classifiers if isinstance(c, str))
    return out


def audit(path: Path) -> list[tuple[str, str]]:
    """Return a list of ``(package_name, denied_license)`` for any offenders."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    offenders: list[tuple[str, str]] = []
    for entry in _entries(payload):
        name_raw = entry.get("Name", "<unknown>")
        name = name_raw if isinstance(name_raw, str) else "<unknown>"
        for lic in _license_strings(entry):
            if lic in _DENIED:
                offenders.append((name, lic))
                break
    return offenders


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <licenses.json>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.exists():
        print(f"license_gate: {path} does not exist", file=sys.stderr)
        return 2
    offenders = audit(path)
    if offenders:
        print("license_gate: DENIED licenses detected:", file=sys.stderr)
        for name, lic in offenders:
            print(f"  - {name}: {lic.upper()}", file=sys.stderr)
        print(
            "Hackathon rules require MIT / Apache-2.0 / BSD-style; "
            "AGPL and GPL-3.0 are release blockers (CICD_SPEC §4.1).",
            file=sys.stderr,
        )
        return 1
    print(f"license_gate: OK ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
