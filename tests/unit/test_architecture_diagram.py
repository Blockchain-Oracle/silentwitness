"""Tests for docs/diagrams/architecture.{mmd,png} (story-architecture-diagram-png)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_MMD = _REPO / "docs" / "diagrams" / "architecture.mmd"
_PNG = _REPO / "docs" / "diagrams" / "architecture.png"
_ARCHITECTURE_MD = _REPO / "docs" / "architecture.md"


def test_mmd_exists_and_is_utf8() -> None:
    assert _MMD.exists()
    text = _MMD.read_text(encoding="utf-8")
    assert text  # decodes as UTF-8


def test_mmd_uses_lf_line_endings() -> None:
    """Per spec: LF only (mmdc is sensitive on macOS)."""
    data = _MMD.read_bytes()
    assert b"\r\n" not in data
    assert data.endswith(b"\n")


def test_mmd_has_six_architectural_labels() -> None:
    text = _MMD.read_text(encoding="utf-8")
    assert text.count("(architectural)") >= 6


def test_mmd_has_two_prompt_based_labels() -> None:
    text = _MMD.read_text(encoding="utf-8")
    assert text.count("(prompt-based") >= 2


def test_png_exists_and_has_magic_bytes() -> None:
    assert _PNG.exists()
    data = _PNG.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_png_size_under_500kb() -> None:
    assert _PNG.stat().st_size <= 512_000


@pytest.mark.skipif(
    shutil.which("mmdc") is None,
    reason="mmdc not installed (run ./install.sh --diagrams)",
)
def test_mmd_renders_via_mmdc(tmp_path: Path) -> None:
    """mmdc can parse + render the .mmd file (proves it's valid Mermaid)."""
    out = tmp_path / "render.png"
    r = subprocess.run(
        [
            "mmdc",
            "-i",
            str(_MMD),
            "-o",
            str(out),
            "-t",
            "dark",
            "-b",
            "transparent",
            "-w",
            "1600",
            "-H",
            "1000",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert out.exists()
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_architecture_md_mermaid_block_matches_mmd() -> None:
    """The first ```mermaid block in architecture.md must equal the .mmd file."""
    md_text = _ARCHITECTURE_MD.read_text(encoding="utf-8")
    lines = md_text.splitlines()
    # Find first ```mermaid fence and matching ```
    start = next(i for i, ln in enumerate(lines) if ln.strip() == "```mermaid")
    end = next(i for i, ln in enumerate(lines[start + 1 :], start + 1) if ln.strip() == "```")
    block = "\n".join(lines[start + 1 : end]) + "\n"
    mmd_text = _MMD.read_text(encoding="utf-8")
    assert block == mmd_text, (
        "architecture.md mermaid block diverged from architecture.mmd; "
        "re-sync via copy-paste or run scripts/render_diagrams.sh after edit."
    )


def test_install_sh_provisions_mmdc() -> None:
    """install.sh has the --diagrams gated provisioning block."""
    install = (_REPO / "install.sh").read_text(encoding="utf-8")
    assert "--diagrams" in install
    assert "mermaid-cli" in install
    assert "nvm" in install or "node" in install.lower()


def test_render_script_exists_and_executable() -> None:
    script = _REPO / "scripts" / "render_diagrams.sh"
    assert script.exists()
    assert script.stat().st_mode & 0o111  # at least one execute bit set


def test_render_script_fails_when_mmdc_missing(tmp_path: Path) -> None:
    """When mmdc is not on PATH, the script exits 1 with a helpful pointer."""
    script = _REPO / "scripts" / "render_diagrams.sh"
    # Run with a deliberately-empty PATH (only /usr/bin for bash itself).
    empty_path_env = {"PATH": "/usr/bin:/bin"}
    r = subprocess.run(
        ["/bin/bash", str(script)],
        capture_output=True,
        text=True,
        check=False,
        env=empty_path_env,
    )
    assert r.returncode == 1
    assert "mmdc not installed" in r.stderr
    assert "--diagrams" in r.stderr
