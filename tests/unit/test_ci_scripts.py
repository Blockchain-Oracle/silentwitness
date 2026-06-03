"""Behavioural tests for the CI gate scripts.

These tests shell out to the real scripts under ``scripts/`` and the real
``.pre-commit-hooks/file-size-guard.py`` — no mocks, per architecture §14.

The six pytest-targeted BDD criteria from story-ci-workflows.md are covered
here; the YAML / job-shape criteria (job count, release wiring, dependency-
review wiring, dependabot ecosystem count) are covered by ``grep`` checks in
the story's Shell-verification block, not by pytest.

In addition to the BDD set, this file pins the gate-script silent-failure
surface that PR-86 review found: empty / malformed coverage XML, unrecognised
license payload shape, combined-license strings like ``"MIT; AGPL-3.0"``,
``UNKNOWN`` / ``Proprietary`` denial paths, default-floor branch, and
usage-error exit-code 2.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LICENSE_GATE = _REPO_ROOT / "scripts" / "license_gate.py"


def _run_license_gate(payload: object, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    licenses_json = tmp_path / "licenses.json"
    licenses_json.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(_LICENSE_GATE), str(licenses_json)],
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# license_gate — BDD-mapped tests
# ---------------------------------------------------------------------------


def test_license_gate_accepts_mit_apache_bsd(tmp_path: Path) -> None:
    result = _run_license_gate(
        [
            {"Name": "a", "License": "MIT"},
            {"Name": "b", "License": "Apache-2.0"},
            {"Name": "c", "License": "BSD-3-Clause"},
        ],
        tmp_path,
    )
    assert result.returncode == 0, f"expected exit 0, got {result.returncode}: {result.stderr}"


def test_license_gate_rejects_agpl(tmp_path: Path) -> None:
    result = _run_license_gate([{"Name": "evil-pkg", "License": "AGPL-3.0"}], tmp_path)
    assert result.returncode == 1, f"expected exit 1, got {result.returncode}"
    assert "AGPL" in result.stderr, f"stderr missing AGPL marker: {result.stderr!r}"


def test_license_gate_rejects_gpl3(tmp_path: Path) -> None:
    result = _run_license_gate([{"Name": "evil-pkg", "License": "GPL-3.0-or-later"}], tmp_path)
    assert result.returncode == 1
    assert "GPL" in result.stderr


def test_license_gate_accepts_lgpl(tmp_path: Path) -> None:
    """LGPL is allowed via runtime-linkage carve-out (CICD_SPEC §4.3)."""
    result = _run_license_gate([{"Name": "ok-pkg", "License": "LGPL-3.0"}], tmp_path)
    assert result.returncode == 0, f"expected exit 0, got {result.returncode}: {result.stderr}"


# ---------------------------------------------------------------------------
# license_gate — silent-failure surface fixes (PR-86 review)
# ---------------------------------------------------------------------------


def test_license_gate_rejects_unknown(tmp_path: Path) -> None:
    """`UNKNOWN` is in _DENIED — pip-licenses emits this for unparseable deps."""
    result = _run_license_gate([{"Name": "mystery", "License": "UNKNOWN"}], tmp_path)
    assert result.returncode == 1
    assert "UNKNOWN" in result.stderr


def test_license_gate_rejects_proprietary(tmp_path: Path) -> None:
    result = _run_license_gate([{"Name": "vendor", "License": "Proprietary"}], tmp_path)
    assert result.returncode == 1
    assert "PROPRIETARY" in result.stderr


def test_license_gate_rejects_combined_string_with_agpl(tmp_path: Path) -> None:
    """`"MIT; AGPL-3.0"` and `"MIT OR AGPL-3.0"` must NOT slip past the gate."""
    for combined in ("MIT; AGPL-3.0", "MIT / AGPL-3.0", "MIT OR AGPL-3.0"):
        result = _run_license_gate([{"Name": "sneaky", "License": combined}], tmp_path)
        assert result.returncode == 1, f"combined-license {combined!r} slipped past gate"
        assert "AGPL" in result.stderr


def test_license_gate_inspects_classifier_list(tmp_path: Path) -> None:
    """A package exposing only `LicenseClassifier` must still be checked."""
    result = _run_license_gate([{"Name": "trove-pkg", "LicenseClassifier": ["AGPL-3.0"]}], tmp_path)
    assert result.returncode == 1
    assert "AGPL" in result.stderr


def test_license_gate_fails_loud_on_unknown_payload_shape(tmp_path: Path) -> None:
    """An unrecognised payload shape must NOT silently exit 0 (would be a no-op gate)."""
    result = _run_license_gate({"foo": "bar"}, tmp_path)
    assert result.returncode == 2, f"expected exit 2 (gate broken), got {result.returncode}"
    assert "unrecognised" in result.stderr.lower() or "shape" in result.stderr.lower()


def test_license_gate_fails_loud_on_entry_without_license_keys(tmp_path: Path) -> None:
    """An entry missing both License and LicenseClassifier must surface as exit 2."""
    result = _run_license_gate([{"Name": "shapeshift"}], tmp_path)
    assert result.returncode == 2
    assert "shapeshift" in result.stderr


def test_license_gate_accepts_empty_array(tmp_path: Path) -> None:
    result = _run_license_gate([], tmp_path)
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# license_gate — allowlist (PR-93 chore-ci fixes)
# ---------------------------------------------------------------------------

_LONG_RATIONALE = (
    "Transitive dep with upstream packaging gap. dist-info LICENSE confirmed "
    "Apache-2.0 (verified 2026-06-03 — test fixture)."
)


def _allowlist_payload(
    name: str,
    *,
    actual_license: str = "Apache-2.0",
    permitted: list[str] | None = None,
    rationale: str = _LONG_RATIONALE,
) -> dict[str, object]:
    return {
        name: {
            "actual_license": actual_license,
            "permitted_pip_licenses": permitted if permitted is not None else ["UNKNOWN"],
            "rationale": rationale,
        }
    }


def _run_with_allowlist(
    licenses: list[dict[str, object]],
    allowlist: dict[str, object],
    tmp_path: Path,
) -> subprocess.CompletedProcess[str]:
    licenses_json = tmp_path / "licenses.json"
    licenses_json.write_text(json.dumps(licenses), encoding="utf-8")
    allowlist_json = tmp_path / "allowlist.json"
    allowlist_json.write_text(json.dumps(allowlist), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(_LICENSE_GATE),
            str(licenses_json),
            "--allowlist",
            str(allowlist_json),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_license_gate_allowlist_skips_documented_denied_value(tmp_path: Path) -> None:
    """A package whose pip-licenses reports a permitted denied value (e.g.
    UNKNOWN) should clear — and stderr must surface the actual_license +
    rationale so the audit trail travels with the override."""
    result = _run_with_allowlist(
        [{"Name": "mistralai", "License": "UNKNOWN"}],
        _allowlist_payload("mistralai"),
        tmp_path,
    )
    assert result.returncode == 0, f"expected 0, got {result.returncode}: {result.stderr}"
    assert "allowlist hit" in result.stderr
    assert "actual_license=Apache-2.0" in result.stderr
    assert "Transitive dep" in result.stderr, "rationale must appear at hit-time"


def test_license_gate_allowlist_does_not_smuggle_other_denied_licenses(tmp_path: Path) -> None:
    """Regression for PR-93 silent-failure-hunter critical finding: if a
    package's allowlist permits UNKNOWN and a future upstream drift emits
    `License = "AGPL-3.0; UNKNOWN"`, the AGPL must still fire."""
    result = _run_with_allowlist(
        [{"Name": "caio", "License": "AGPL-3.0; UNKNOWN"}],
        _allowlist_payload("caio", permitted=["UNKNOWN"]),
        tmp_path,
    )
    assert result.returncode == 1, "AGPL-3.0 must NOT be smuggled past the gate"
    assert "AGPL" in result.stderr
    assert "allowlist hit" in result.stderr, "the UNKNOWN side should still clear visibly"


def test_license_gate_allowlist_rejects_denied_actual_license(tmp_path: Path) -> None:
    """Regression for PR-93 N1: a maintainer cannot write
    `"actual_license": "GPL-3.0"` to smuggle a real GPL dep — the loader
    rejects any actual_license that itself appears in the deny list."""
    result = _run_with_allowlist(
        [{"Name": "trojan", "License": "GPL-3.0"}],
        _allowlist_payload("trojan", actual_license="GPL-3.0"),
        tmp_path,
    )
    assert result.returncode == 2
    assert "deny list" in result.stderr.lower()


def test_license_gate_allowlist_rejects_permitted_outside_deny(tmp_path: Path) -> None:
    """`permitted_pip_licenses` entries must themselves be in the deny list —
    otherwise listing them does nothing and signals a misunderstanding."""
    result = _run_with_allowlist(
        [{"Name": "x", "License": "MIT"}],
        _allowlist_payload("x", permitted=["MIT"]),
        tmp_path,
    )
    assert result.returncode == 2
    assert "NOT in the deny list" in result.stderr


def test_license_gate_allowlist_rejects_placeholder_rationale(tmp_path: Path) -> None:
    """Placeholder rationales (todo / tbd / fixme / xxx / n-a) must fail load."""
    for placeholder in ("TODO", "tbd", "fixme", "n/a"):
        result = _run_with_allowlist(
            [{"Name": "x", "License": "UNKNOWN"}],
            _allowlist_payload("x", rationale=placeholder),
            tmp_path,
        )
        assert result.returncode == 2, f"placeholder {placeholder!r} slipped past"
        assert "placeholder" in result.stderr.lower()


def test_license_gate_allowlist_rejects_short_rationale(tmp_path: Path) -> None:
    """Rationales shorter than 40 chars fail load — the override exists to
    force thinking, not to be a write-only escape hatch."""
    result = _run_with_allowlist(
        [{"Name": "x", "License": "UNKNOWN"}],
        _allowlist_payload("x", rationale="too short to be useful"),
        tmp_path,
    )
    assert result.returncode == 2
    assert "at least" in result.stderr.lower()


def test_license_gate_allowlist_rejects_missing_permitted_list(tmp_path: Path) -> None:
    """`permitted_pip_licenses` is required — without it, the override has
    no signal about which specific deny-list value to clear."""
    licenses_json = tmp_path / "licenses.json"
    licenses_json.write_text(json.dumps([{"Name": "x", "License": "UNKNOWN"}]), encoding="utf-8")
    allowlist = tmp_path / "allowlist.json"
    allowlist.write_text(
        json.dumps(
            {
                "x": {
                    "actual_license": "Apache-2.0",
                    "rationale": _LONG_RATIONALE,
                    # permitted_pip_licenses missing
                }
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(_LICENSE_GATE),
            str(licenses_json),
            "--allowlist",
            str(allowlist),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "permitted_pip_licenses" in result.stderr


def test_license_gate_allowlist_skips_underscore_prefixed_meta_keys(tmp_path: Path) -> None:
    """``_meta`` and other underscore-prefixed keys are documentation, not
    package overrides. They must not be validated as entries."""
    licenses_json = tmp_path / "licenses.json"
    licenses_json.write_text(json.dumps([{"Name": "pkg", "License": "MIT"}]), encoding="utf-8")
    allowlist = tmp_path / "allowlist.json"
    allowlist.write_text(
        json.dumps(
            {
                "_meta": {"description": "documentation only; no validation"},
                **_allowlist_payload("pkg"),
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(_LICENSE_GATE),
            str(licenses_json),
            "--allowlist",
            str(allowlist),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0


def test_license_gate_exits_2_on_missing_file(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(_LICENSE_GATE), str(tmp_path / "nope.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
