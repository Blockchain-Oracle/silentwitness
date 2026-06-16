"""Regression checks for packaged wheel contents."""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path


def test_wheel_includes_evidence_package(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    out_dir = tmp_path / "dist"
    result = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out_dir)],
        cwd=repo,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    wheel = next(out_dir.glob("silentwitness-*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    required = {
        "silentwitness_mcp/evidence/__init__.py",
        "silentwitness_mcp/evidence/access.py",
        "silentwitness_mcp/evidence/artifacts.py",
        "silentwitness_mcp/evidence/registry.py",
    }
    missing = sorted(required - names)
    assert not missing, f"{wheel.name} missing evidence package files: {missing}"


def test_wheel_can_import_evidence_registry_after_install(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    out_dir = tmp_path / "dist"
    venv = tmp_path / "venv"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out_dir)],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )
    subprocess.run(["uv", "venv", str(venv)], check=True, text=True, capture_output=True)
    wheel = next(out_dir.glob("silentwitness-*.whl"))
    python = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    subprocess.run(
        ["uv", "pip", "install", "--python", str(python), str(wheel)],
        check=True,
        text=True,
        capture_output=True,
    )
    snippet = (
        "from silentwitness_mcp.evidence.registry import EvidenceRegistry; "
        "print(EvidenceRegistry.__name__)"
    )
    result = subprocess.run(
        [
            str(python),
            "-c",
            snippet,
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "EvidenceRegistry"
