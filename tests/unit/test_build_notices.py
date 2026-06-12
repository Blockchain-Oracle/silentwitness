"""Tests for scripts/build_notices.py — NOTICES.md aggregator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_notices.py"
_REQUIRED_BINARIES = (
    "Hayabusa",
    "Chainsaw",
    "Velociraptor",
    "Zeek",
    "Suricata",
    "Volatility 3",
    "MFTECmd",
)
_REQUIRED_PY_DEPS = ("Pydantic AI", "MCP", "WeasyPrint", "matplotlib")


def _run(out: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), "--out", str(out), *extra],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def built(tmp_path: Path) -> str:
    """Run the script once per test and return the generated NOTICES.md text."""
    out = tmp_path / "NOTICES.md"
    r = _run(out)
    assert r.returncode == 0, r.stderr
    return out.read_text()


class TestHappyPath:
    def test_writes_notices_md_with_header(self, built: str) -> None:
        assert "SilentWitness is licensed under MIT" in built
        assert "aggregates third-party attributions" in built

    def test_about_this_file_section_present(self, built: str) -> None:
        """Auditor-facing 'About this file' section explains linkage and grant-clause caveat."""
        assert "## About this file" in built
        assert "Linkage analysis" in built
        assert "paraphrased summaries" in built
        assert "subprocess-invoked" in built

    def test_contains_required_binaries(self, built: str) -> None:
        for name in _REQUIRED_BINARIES:
            assert f"## {name}" in built, f"missing H2 for {name}"

    def test_contains_required_python_deps(self, built: str) -> None:
        for name in _REQUIRED_PY_DEPS:
            assert f"## {name}" in built, f"missing H2 for {name}"

    def test_components_sorted_alphabetically(self, built: str) -> None:
        h2_lines = [line[3:].strip() for line in built.splitlines() if line.startswith("## ")]
        component_h2s = [h for h in h2_lines if not h.startswith("About")]
        assert component_h2s == sorted(component_h2s, key=str.lower)

    def test_every_component_has_required_fields(self, built: str) -> None:
        """BDD AC #3 — EVERY entry has Version/SPDX/Source/Copyright (not just spot-check)."""
        # Split by H2 component headers
        component_names = (
            "Chainsaw",
            "Hayabusa",
            "Jinja2",
            "MCP",
            "MFTECmd",
            "Mistune",
            "Pydantic AI",
            "Pydantic",
            "Rich",
            "Suricata",
            "Typer",
            "Velociraptor",
            "Volatility 3",
            "WeasyPrint",
            "Zeek",
            "en_core_web_lg",
            "httpx",
            "matplotlib",
            "spaCy",
            "uv",
        )
        for name in component_names:
            idx = built.index(f"## {name}\n")
            # Find next H2 after this one (or EOF)
            next_idx = built.find("\n## ", idx + 1)
            section = built[idx:] if next_idx == -1 else built[idx:next_idx]
            assert "Version:" in section, f"{name}: missing Version"
            assert "SPDX:" in section, f"{name}: missing SPDX"
            assert "Source:" in section, f"{name}: missing Source"
            assert "Copyright:" in section, f"{name}: missing Copyright"


class TestGrantClauses:
    @pytest.mark.parametrize(
        "component,spdx,grant_marker",
        [
            ("Chainsaw", "GPL-3.0-only", "Summary grant clause (GPL-3.0-only"),
            ("Hayabusa", "GPL-3.0-only", "Summary grant clause (GPL-3.0-only"),
            ("Suricata", "GPL-2.0-only", "Summary grant clause (GPL-2.0-only"),
            ("Velociraptor", "AGPL-3.0-only", "Summary grant clause (AGPL-3.0-only"),
        ],
    )
    def test_grant_clause_per_license(
        self, built: str, component: str, spdx: str, grant_marker: str
    ) -> None:
        """Each GPL/AGPL component has its license-specific summary grant clause."""
        idx = built.index(f"## {component}\n")
        next_idx = built.find("\n## ", idx + 1)
        section = built[idx:] if next_idx == -1 else built[idx:next_idx]
        assert f"SPDX: {spdx}" in section
        assert grant_marker in section


class TestErrors:
    def test_unknown_license_exits_1(self, tmp_path: Path) -> None:
        out = tmp_path / "NOTICES.md"
        r = _run(out, "--inject-unknown", "MysteryLib")
        assert r.returncode == 1
        assert "UNKNOWN_LICENSE: MysteryLib" in r.stderr


class TestDeterminism:
    def test_two_builds_byte_equal(self, tmp_path: Path) -> None:
        """Same catalog → byte-identical output across runs (no dict-iteration drift)."""
        a = tmp_path / "a.md"
        b = tmp_path / "b.md"
        _run(a)
        _run(b)
        assert a.read_bytes() == b.read_bytes()


class TestCriticalAttributions:
    def test_vol3_uses_licenseref_not_osl(self, built: str) -> None:
        """Vol3 uses VSL (LicenseRef-Volatility-VSL-1.0), NOT OSL-3.0 (reviewer C1 fix)."""
        idx = built.index("## Volatility 3\n")
        next_idx = built.find("\n## ", idx + 1)
        section = built[idx:next_idx]
        assert "LicenseRef-Volatility-VSL-1.0" in section
        assert "OSL-3.0" not in section

    def test_spacy_lg_model_is_mit_not_ccbysa(self, built: str) -> None:
        """en_core_web_lg is MIT per upstream meta.json (reviewer C2 fix)."""
        idx = built.index("## en_core_web_lg\n")
        next_idx = built.find("\n## ", idx + 1)
        section = built[idx:next_idx]
        assert "SPDX: MIT" in section
        assert "CC-BY-SA" not in section

    def test_no_redundant_fastmcp_entry(self, built: str) -> None:
        """We use mcp.server.fastmcp (sub-module of MCP), not standalone FastMCP."""
        assert "## FastMCP" not in built


@pytest.mark.parametrize(
    "spdx",
    [
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "GPL-2.0-only",
        "GPL-3.0-only",
        "AGPL-3.0-only",
        "MPL-2.0",
        "ISC",
    ],
)
def test_supported_spdx_ids(spdx: str) -> None:
    from scripts._notices_catalog import SUPPORTED_SPDX

    assert spdx in SUPPORTED_SPDX
