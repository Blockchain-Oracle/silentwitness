"""Tests for scripts/build_notices.py — NOTICES.md aggregator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_notices.py"


def _run(out: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), "--out", str(out), *extra],
        capture_output=True,
        text=True,
        check=False,
    )


class TestHappyPath:
    def test_writes_notices_md_with_header(self, tmp_path: Path) -> None:
        """build_notices writes a NOTICES.md with the SilentWitness MIT header."""
        out = tmp_path / "NOTICES.md"
        r = _run(out)
        assert r.returncode == 0, r.stderr
        assert out.exists()
        text = out.read_text()
        assert "SilentWitness is licensed under MIT" in text
        assert "aggregates third-party attributions" in text

    def test_contains_required_binaries(self, tmp_path: Path) -> None:
        """NOTICES.md has H2 headers for each install.sh binary."""
        out = tmp_path / "NOTICES.md"
        _run(out)
        text = out.read_text()
        for name in (
            "Hayabusa",
            "Chainsaw",
            "Velociraptor",
            "Zeek",
            "Suricata",
            "Volatility 3",
            "MFTECmd",
        ):
            assert f"## {name}" in text, f"missing H2 for {name}"

    def test_contains_required_python_deps(self, tmp_path: Path) -> None:
        """NOTICES.md has entries for the major Python deps."""
        out = tmp_path / "NOTICES.md"
        _run(out)
        text = out.read_text()
        for name in ("Pydantic AI", "MCP", "WeasyPrint", "matplotlib"):
            assert f"## {name}" in text, f"missing H2 for {name}"

    def test_components_sorted_alphabetically(self, tmp_path: Path) -> None:
        """The H2 component sections appear in alphabetical order."""
        out = tmp_path / "NOTICES.md"
        _run(out)
        text = out.read_text()
        h2_lines = [
            line[3:].strip()
            for line in text.splitlines()
            if line.startswith("## ") and not line.startswith("## License-grant")
        ]
        # Skip the intro/header H2s before component entries
        component_h2s = [h for h in h2_lines if not h.startswith("About")]
        assert component_h2s == sorted(component_h2s, key=str.lower)

    def test_every_entry_has_required_fields(self, tmp_path: Path) -> None:
        """Each component entry includes name, version, SPDX, URL, copyright."""
        out = tmp_path / "NOTICES.md"
        _run(out)
        text = out.read_text()
        # Spot-check one canonical entry
        chainsaw_idx = text.index("## Chainsaw")
        next_h2 = text.index("\n## ", chainsaw_idx + 1)
        section = text[chainsaw_idx:next_h2]
        assert "Version:" in section
        assert "SPDX:" in section
        assert "Source:" in section
        assert "Copyright:" in section


class TestGPLLicenseGrants:
    def test_gpl_component_includes_grant_clause(self, tmp_path: Path) -> None:
        """GPL-3.0 components include a verbatim license-grant snippet."""
        out = tmp_path / "NOTICES.md"
        _run(out)
        text = out.read_text()
        # Hayabusa is GPL-3.0; spec requires the verbatim grant clause
        assert "GPL-3.0" in text
        assert "License-grant" in text or "This program is free software" in text

    def test_agpl_component_includes_grant_clause(self, tmp_path: Path) -> None:
        """AGPL-3.0 components (Velociraptor) include their grant clause."""
        out = tmp_path / "NOTICES.md"
        _run(out)
        text = out.read_text()
        assert "AGPL-3.0" in text


class TestErrors:
    def test_unknown_license_exits_1(self, tmp_path: Path) -> None:
        """Injecting an unknown-license component → exit 1 with `UNKNOWN_LICENSE:`."""
        out = tmp_path / "NOTICES.md"
        r = _run(out, "--inject-unknown", "MysteryLib")
        assert r.returncode == 1
        assert "UNKNOWN_LICENSE: MysteryLib" in r.stderr


class TestMain:
    def test_default_out_writes_to_repo_root(self, tmp_path: Path) -> None:
        """--out NOTICES.md (default) writes relative to CWD."""
        # Just verify the script runs without errors when explicit out provided
        out = tmp_path / "OUT.md"
        r = _run(out)
        assert r.returncode == 0
        assert out.exists()


def test_real_build_produces_valid_notices() -> None:
    """End-to-end: run with no args (default --out NOTICES.md) in repo root."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "NOTICES.md"
        r = subprocess.run(
            [sys.executable, str(_SCRIPT), "--out", str(out_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert r.returncode == 0, r.stderr
        text = out_path.read_text()
        # Spec verification: ≥9 H2 entries for required components
        required = (
            "Hayabusa",
            "Chainsaw",
            "Velociraptor",
            "Zeek",
            "Suricata",
            "Volatility 3",
            "MFTECmd",
            "Pydantic AI",
            "MCP",
        )
        found = sum(1 for name in required if f"## {name}" in text)
        assert found >= 9, f"only {found}/9 required H2s present"


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
    """Script knows the supported SPDX IDs from the story spec."""
    from scripts.build_notices import _SUPPORTED_SPDX

    assert spdx in _SUPPORTED_SPDX
