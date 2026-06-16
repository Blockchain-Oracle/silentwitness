"""License gate — fail CI if any installed dep ships under a denied license.

Invoked from .github/workflows/ci.yml `license-check` job after pip-licenses
emits licenses.json. The deny list is:

  * AGPL-3.0 variants (hackathon-rules ban)
  * GPL-3.0 variants  (hackathon-rules ban)
  * UNKNOWN            (deny-by-default: pip-licenses emits this for deps with
                       unparseable metadata; treating unparseable as ALLOW would
                       be a silent supply-chain hole)
  * Proprietary        (same rationale — closed-source bundled deps would not
                       satisfy the MIT/Apache submission rules)

LGPL is allowed for runtime-linked deps only; Python dynamic linking means we
never trip the LGPL static-link clause.

An optional ``--allowlist <path>`` argument points at a JSON file with
per-package overrides for deps that have upstream-packaging gaps but whose
actual LICENSE file has been audited. Schema::

    {
      "package_name": {
        "actual_license": "Apache-2.0",
        "permitted_pip_licenses": ["UNKNOWN"],
        "rationale": "Why this is OK — must reference the audit (40+ chars)."
      },
      ...
    }

Two-field design (PR-93 silent-failure-hunter caught the single-field smuggling
vector):

  * ``actual_license`` is what the package REALLY licenses as (the audited
    SPDX from the dist-info LICENSE file or upstream repo). Must NOT be in
    the deny list — otherwise the allowlist becomes a tunnel for genuinely-
    denied licenses.
  * ``permitted_pip_licenses`` is the specific deny-list values the gate is
    permitted to see for this package (e.g. ``["UNKNOWN"]`` when pip-licenses
    reports UNKNOWN due to missing metadata). Each entry MUST itself be in
    the deny list — otherwise the allowlist would do nothing.
  * Other denied licenses on the same package — values NOT in
    ``permitted_pip_licenses`` — still fire the gate. So if ``caio`` is
    allowlisted for ``["UNKNOWN"]`` and a future version emits
    ``"License = AGPL-3.0; UNKNOWN"``, only the UNKNOWN clears; the AGPL-3.0
    becomes a loud offender.

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

_RATIONALE_MIN_LENGTH = 40
_RATIONALE_BANLIST: frozenset[str] = frozenset({"todo", "tbd", "fixme", "xxx", "n/a"})


class _AllowlistEntry:
    """Per-package allowlist record. Carries the rationale through to hit-time
    so CI logs surface the audit trail at the point of the override."""

    __slots__ = ("actual_license", "permitted_pip_licenses", "rationale")

    def __init__(
        self,
        actual_license: str,
        permitted_pip_licenses: frozenset[str],
        rationale: str,
    ) -> None:
        self.actual_license = actual_license
        self.permitted_pip_licenses = permitted_pip_licenses
        self.rationale = rationale


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


def _load_allowlist(path: Path) -> dict[str, _AllowlistEntry]:
    """Parse the allowlist file and validate every entry.

    Raises ``ValueError`` on any structural defect so a malformed file can't
    silently widen the gate.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: top-level must be a JSON object")
    out: dict[str, _AllowlistEntry] = {}
    for name, entry in payload.items():
        if name.startswith("_"):
            # Underscore-prefixed keys are metadata (e.g. ``_meta``).
            continue
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: entry for {name!r} must be an object")
        out[name] = _validate_allowlist_entry(path, name, entry)
    return out


def _validate_allowlist_entry(path: Path, name: str, entry: dict[str, object]) -> _AllowlistEntry:
    """Validate a single allowlist entry and return the parsed record."""
    actual_raw = entry.get("actual_license")
    if not isinstance(actual_raw, str) or not actual_raw.strip():
        raise ValueError(f"{path}: {name!r} missing required `actual_license`")
    actual = actual_raw.strip()
    if actual.lower() in _DENIED:
        raise ValueError(
            f"{path}: {name!r} declares actual_license={actual!r}, which is "
            "itself in the deny list. The allowlist documents that the gate's "
            "denied signal is wrong upstream; it cannot permit a genuinely-denied "
            "license."
        )

    permitted_raw = entry.get("permitted_pip_licenses")
    if not isinstance(permitted_raw, list) or not permitted_raw:
        raise ValueError(
            f"{path}: {name!r} `permitted_pip_licenses` must be a non-empty list of "
            "deny-list values that pip-licenses is permitted to report for this "
            'package (e.g. ["UNKNOWN"] when metadata is missing).'
        )
    permitted: set[str] = set()
    for item in permitted_raw:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"{path}: {name!r} `permitted_pip_licenses` entries must be non-empty strings"
            )
        normalised = item.strip().lower()
        if normalised not in _DENIED:
            raise ValueError(
                f"{path}: {name!r} `permitted_pip_licenses` includes {item!r} which "
                "is NOT in the deny list — listing it in the allowlist would do "
                "nothing. Remove the entry or replace it with the actual denied "
                "value pip-licenses reports."
            )
        permitted.add(normalised)

    rationale_raw = entry.get("rationale")
    if not isinstance(rationale_raw, str) or not rationale_raw.strip():
        raise ValueError(f"{path}: {name!r} missing required `rationale`")
    rationale = rationale_raw.strip()
    if rationale.lower() in _RATIONALE_BANLIST:
        raise ValueError(
            f"{path}: {name!r} rationale {rationale!r} is a placeholder; write the "
            "actual audit reasoning."
        )
    if len(rationale) < _RATIONALE_MIN_LENGTH:
        raise ValueError(
            f"{path}: {name!r} rationale must be at least "
            f"{_RATIONALE_MIN_LENGTH} chars (got {len(rationale)}); the structured "
            "override exists to force thinking, not to be a write-only escape hatch."
        )

    return _AllowlistEntry(
        actual_license=actual,
        permitted_pip_licenses=frozenset(permitted),
        rationale=rationale,
    )


def audit(path: Path, allowlist: dict[str, _AllowlistEntry] | None = None) -> list[tuple[str, str]]:
    """Return a list of ``(package_name, denied_license)`` for any offenders.

    A package present in ``allowlist`` clears ONLY the specific denied
    licenses its entry permits. Any OTHER denied license on the same entry
    still fires — so a future upstream drift (e.g. caio bumps from UNKNOWN
    to AGPL-3.0) trips the gate loudly.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    offenders: list[tuple[str, str]] = []
    allow = allowlist or {}
    for entry in _entries(payload):
        name_raw = entry.get("Name", "<unknown>")
        name = name_raw if isinstance(name_raw, str) else "<unknown>"
        allow_entry = allow.get(name)
        for lic in _license_strings(entry):
            if lic not in _DENIED:
                continue
            if allow_entry is not None and lic in allow_entry.permitted_pip_licenses:
                # Documented override hit — log the audit trail at the point of
                # use so CI investigators see WHY this exception exists.
                print(
                    f"license_gate: allowlist hit — {name}: {lic.upper()} → "
                    f"actual_license={allow_entry.actual_license}. "
                    f"Rationale: {allow_entry.rationale}",
                    file=sys.stderr,
                )
                continue
            offenders.append((name, lic))
            # Don't break: a single entry can carry multiple denied licenses in
            # a `License = "MIT; AGPL-3.0; UNKNOWN"` string; we want to see every
            # offense, not just the first.
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
    allowlist: dict[str, _AllowlistEntry] | None = None
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
            "AGPL and GPL-3.0 are release blockers.",
            file=sys.stderr,
        )
        return 1
    print(f"license_gate: OK ({licenses_path})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
