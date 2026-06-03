"""Behavioural tests for the CI gate scripts.

These tests shell out to the real scripts under ``scripts/`` and the real
``.pre-commit-hooks/file-size-guard.py`` — no mocks, per architecture §14.
Each test maps 1:1 to a BDD criterion in story-ci-workflows.md:

1. license_gate accepts MIT / Apache-2.0 / BSD-3-Clause.
2. license_gate rejects AGPL-3.0 (exit 1, stderr names "AGPL").
3. license_gate rejects GPL-3.0 (exit 1, stderr names "GPL").
4. license_gate accepts LGPL-3.0 (runtime-linkage carve-out, CICD_SPEC §4.3).
5. coverage_gate fails when verification/ is below the 95 % floor.
6. coverage_gate fails when audit/ is below the 90 % floor.
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


def _run_license_gate(
    payload: list[dict[str, str]], tmp_path: Path
) -> subprocess.CompletedProcess[str]:
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


def test_coverage_gate_fails_verification_below_95(tmp_path: Path) -> None:
    # 94 of 100 → 94 % on src/silentwitness_mcp/verification/citation_gate.py
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
    # 89 of 100 → 89 % on src/silentwitness_mcp/audit/logger.py
    xml_text = _coverage_xml("src/silentwitness_mcp/audit/logger.py", covered=89, total=100)
    result = _run_coverage_gate(xml_text, tmp_path)
    assert result.returncode == 1
    assert "audit" in result.stderr
    assert "90" in result.stderr
