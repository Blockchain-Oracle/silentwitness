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
from textwrap import dedent

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LICENSE_GATE = _REPO_ROOT / "scripts" / "license_gate.py"
_COVERAGE_GATE = _REPO_ROOT / "scripts" / "coverage_gate.py"


def _run_license_gate(payload: object, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    licenses_json = tmp_path / "licenses.json"
    licenses_json.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(_LICENSE_GATE), str(licenses_json)],
        capture_output=True,
        text=True,
        check=False,
    )


def _run_coverage_gate(xml_text: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    xml_path = tmp_path / "coverage.xml"
    xml_path.write_text(xml_text, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(_COVERAGE_GATE), str(xml_path)],
        capture_output=True,
        text=True,
        check=False,
    )


def _coverage_xml(filename: str, covered: int, total: int) -> str:
    """Minimal Cobertura-shaped XML covering one file at the given line rate."""
    lines = "\n".join(
        f'        <line number="{i + 1}" hits="{1 if i < covered else 0}"/>' for i in range(total)
    )
    return dedent(
        f"""\
        <?xml version="1.0" ?>
        <coverage>
          <packages>
            <package>
              <classes>
                <class filename="{filename}">
                  <lines>
        {lines}
                  </lines>
                </class>
              </classes>
            </package>
          </packages>
        </coverage>
        """
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


def test_license_gate_exits_2_on_missing_file(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(_LICENSE_GATE), str(tmp_path / "nope.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2


# ---------------------------------------------------------------------------
# coverage_gate — BDD-mapped tests
# ---------------------------------------------------------------------------


def test_coverage_gate_fails_verification_below_95(tmp_path: Path) -> None:
    xml_text = _coverage_xml(
        "src/silentwitness_mcp/verification/citation_gate.py",
        covered=94,
        total=100,
    )
    result = _run_coverage_gate(xml_text, tmp_path)
    assert result.returncode == 1, f"expected exit 1, got {result.returncode}: {result.stdout}"
    assert "verification" in result.stderr
    assert "95" in result.stderr


def test_coverage_gate_fails_audit_below_90(tmp_path: Path) -> None:
    xml_text = _coverage_xml("src/silentwitness_mcp/audit/logger.py", covered=89, total=100)
    result = _run_coverage_gate(xml_text, tmp_path)
    assert result.returncode == 1
    assert "audit" in result.stderr
    assert "90" in result.stderr


# ---------------------------------------------------------------------------
# coverage_gate — silent-failure surface fixes (PR-86 review)
# ---------------------------------------------------------------------------


def test_coverage_gate_passes_when_floors_met(tmp_path: Path) -> None:
    """Happy path: 96 % on verification/ → exit 0 (catches comparator-inversion regressions)."""
    xml_text = _coverage_xml(
        "src/silentwitness_mcp/verification/citation_gate.py", covered=96, total=100
    )
    result = _run_coverage_gate(xml_text, tmp_path)
    assert result.returncode == 0, f"expected exit 0, got {result.returncode}: {result.stderr}"


def test_coverage_gate_fails_default_below_85(tmp_path: Path) -> None:
    """A file outside verification/ and audit/ must enforce the 85 % default floor."""
    xml_text = _coverage_xml("src/silentwitness_mcp/mcp_tools/timeline.py", covered=84, total=100)
    result = _run_coverage_gate(xml_text, tmp_path)
    assert result.returncode == 1
    assert "85" in result.stderr


def test_coverage_gate_fails_loud_on_empty_xml(tmp_path: Path) -> None:
    """Empty coverage.xml (no <class> elements) must exit 2 (gate broken), NOT 0."""
    empty_xml = "<?xml version='1.0'?><coverage><packages/></coverage>"
    result = _run_coverage_gate(empty_xml, tmp_path)
    assert result.returncode == 2, f"empty XML was silently treated as PASS: {result.stderr}"
    assert "zero" in result.stderr.lower() or "no data" in result.stderr.lower()


def test_coverage_gate_normalises_leading_dot_slash(tmp_path: Path) -> None:
    """`./src/silentwitness_mcp/verification/x.py` must still hit the 95 % bucket."""
    xml_text = _coverage_xml("./src/silentwitness_mcp/verification/x.py", covered=94, total=100)
    result = _run_coverage_gate(xml_text, tmp_path)
    assert result.returncode == 1
    assert "verification" in result.stderr


def test_coverage_gate_exits_2_on_missing_file(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(_COVERAGE_GATE), str(tmp_path / "nope.xml")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
