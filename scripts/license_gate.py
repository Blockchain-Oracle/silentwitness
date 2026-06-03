"""License gate — fail CI if any installed dep ships under a denied license.

Invoked from .github/workflows/ci.yml `license-check` job after pip-licenses
emits licenses.json. The deny list is:

  * AGPL-3.0 variants (hackathon-rules ban — see CICD_SPEC §2 and §4.3)
  * GPL-3.0 variants  (hackathon-rules ban — same)
  * UNKNOWN            (deny-by-default: pip-licenses emits this for deps with
                       unparseable metadata; treating unparseable as ALLOW would
                       be a silent supply-chain hole — see CICD_SPEC §1173 runbook)
  * Proprietary        (same rationale — closed-source bundled deps would not
                       satisfy the MIT/Apache submission rules)

LGPL is allowed for runtime-linked deps only; Python dynamic linking means we
never trip the LGPL static-link clause (CICD_SPEC §2 + §4.3).

An optional ``--allowlist <path>`` argument points at a JSON file with
per-package overrides for deps that have upstream-packaging gaps but whose
actual LICENSE file has been audited. Schema::

    {
      "package_name": {
        "spdx_license": "Apache-2.0",
        "rationale": "Why this is OK — must reference the audit."
      },
      ...
    }

A gate that defaults to PASS on weird input is worse than useless — this
script raises on an unrecognised payload shape and on entries that expose no
license keys at all, so a future pip-licenses output-format change cannot
silently neuter the check (architecture.md §14).

Usage::

    uv run python scripts/license_gate.py licenses.json
    uv run python scripts/license_gate.py licenses.json --allowlist .license-allowlist.json
"""

from __future__ import annotations

import argparse
import json
import re
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

# pip-licenses may emit multiple SPDX IDs joined by ``;``, ``/``, or ``OR``
# (case-insensitive) inside a single ``License`` string. Tokenise before
# matching so e.g. ``"MIT; AGPL-3.0"`` does not slip past the gate.
_LICENSE_SEPARATOR = re.compile(r"[;/]|\sOR\s", re.IGNORECASE)


def _entries(payload: object) -> list[dict[str, object]]:
    """pip-licenses emits a top-level JSON array; tolerate a wrapping object too.

    Raises ``ValueError`` on any other shape — silently returning ``[]`` would
    convert an output-format change into a green CI run.
    """
    if isinstance(payload, list):
        return [e for e in payload if isinstance(e, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("packages"), list):
        return [e for e in payload["packages"] if isinstance(e, dict)]
    raise ValueError(
        "unrecognised pip-licenses payload — expected a list of objects, or an "
        f"object with a `packages` array. Got top-level type {type(payload).__name__}."
    )


def _license_strings(entry: dict[str, object]) -> list[str]:
    """Return every lowercased license identifier extracted from an entry.

    Handles both the ``License`` (string, possibly multi-license-joined) and
    ``LicenseClassifier`` (list) keys. Raises ``ValueError`` if neither key
    is present in a recognisable form — an entry with no exposed license
    surface means pip-licenses changed shape and the gate cannot evaluate it.
    """
    out: list[str] = []
    lic = entry.get("License")
    if isinstance(lic, str):
        for tok in _LICENSE_SEPARATOR.split(lic):
            cleaned = tok.strip().lower()
            if cleaned:
                out.append(cleaned)
    classifiers = entry.get("LicenseClassifier")
    if isinstance(classifiers, list):
        # Symmetry with the `License` string branch: split classifier entries
        # on the same separators in case a future tool emits a combined value
        # there too. Trove classifiers don't normally carry joined strings,
        # but applying the separator costs nothing and closes the path.
        for c in classifiers:
            if not isinstance(c, str):
                continue
            for tok in _LICENSE_SEPARATOR.split(c):
                cleaned = tok.strip().lower()
                if cleaned:
                    out.append(cleaned)
    if not out:
        name = entry.get("Name", "<unknown>")
        raise ValueError(
            f"entry {name!r} exposes no `License` or `LicenseClassifier` key — "
            "pip-licenses output shape changed; gate cannot evaluate this package."
        )
    return out


def _load_allowlist(path: Path) -> dict[str, str]:
    """Return ``{package_name: spdx_license}`` for the allowlist file.

    Raises ``ValueError`` on any entry missing the required ``spdx_license``
    or ``rationale`` keys — every override must be justified in writing.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: top-level must be a JSON object")
    out: dict[str, str] = {}
    for name, entry in payload.items():
        if name.startswith("_"):
            # Underscore-prefixed keys are metadata (e.g. ``_meta``).
            continue
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: entry for {name!r} must be an object")
        spdx = entry.get("spdx_license")
        rationale = entry.get("rationale")
        if not isinstance(spdx, str) or not spdx.strip():
            raise ValueError(f"{path}: {name!r} missing required `spdx_license`")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(f"{path}: {name!r} missing required `rationale`")
        out[name] = spdx
    return out


def audit(path: Path, allowlist: dict[str, str] | None = None) -> list[tuple[str, str]]:
    """Return a list of ``(package_name, denied_license)`` for any offenders.

    Packages present in ``allowlist`` are skipped after a stderr note.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    offenders: list[tuple[str, str]] = []
    allow = allowlist or {}
    for entry in _entries(payload):
        name_raw = entry.get("Name", "<unknown>")
        name = name_raw if isinstance(name_raw, str) else "<unknown>"
        for lic in _license_strings(entry):
            if lic in _DENIED:
                if name in allow:
                    print(
                        f"license_gate: allowlist hit — {name}: {lic.upper()} → "
                        f"audited as {allow[name]}",
                        file=sys.stderr,
                    )
                    break
                offenders.append((name, lic))
                break
    return offenders


def _parse_argv(argv: list[str]) -> tuple[Path, Path | None]:
    parser = argparse.ArgumentParser(
        prog=Path(argv[0]).name,
        description="Audit licenses.json against the deny list (with optional allowlist).",
    )
    parser.add_argument("licenses_json", type=Path, help="Path to the pip-licenses JSON output.")
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=None,
        help="Optional JSON file of per-package overrides (see module docstring).",
    )
    ns = parser.parse_args(argv[1:])
    return ns.licenses_json, ns.allowlist


def main(argv: list[str]) -> int:
    try:
        licenses_path, allowlist_path = _parse_argv(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    if not licenses_path.exists():
        print(f"license_gate: {licenses_path} does not exist", file=sys.stderr)
        return 2
    allowlist: dict[str, str] | None = None
    if allowlist_path is not None:
        if not allowlist_path.exists():
            print(f"license_gate: {allowlist_path} does not exist", file=sys.stderr)
            return 2
        try:
            allowlist = _load_allowlist(allowlist_path)
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"license_gate: allowlist invalid — {exc}", file=sys.stderr)
            return 2
    try:
        offenders = audit(licenses_path, allowlist)
    except json.JSONDecodeError as exc:
        print(f"license_gate: {licenses_path} is not valid JSON: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"license_gate: gate broken — {exc}", file=sys.stderr)
        return 2
    if offenders:
        print("license_gate: DENIED licenses detected:", file=sys.stderr)
        for name, lic in offenders:
            print(f"  - {name}: {lic.upper()}", file=sys.stderr)
        print(
            "Hackathon rules require MIT / Apache-2.0 / BSD-style; "
            "AGPL and GPL-3.0 are release blockers (CICD_SPEC §2 + §4.3).",
            file=sys.stderr,
        )
        return 1
    print(f"license_gate: OK ({licenses_path})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
