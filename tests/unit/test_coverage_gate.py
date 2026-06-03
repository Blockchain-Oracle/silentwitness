"""Behavioural tests for scripts/coverage_gate.py.

Subprocess-driven against the real script (no mocks per architecture §14).
Split out from test_ci_scripts.py per file-size-guard 400-LOC cap.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COVERAGE_GATE = _REPO_ROOT / "scripts" / "coverage_gate.py"


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
# BDD-mapped tests
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
# Silent-failure surface fixes (PR-86 review)
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
