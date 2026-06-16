"""Tests for scripts/check_readme_gate.py — README shape gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_GATE = Path(__file__).resolve().parents[2] / "scripts" / "check_readme_gate.py"
_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "readme"


def _run(fixture: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_GATE), str(_FIXTURES / fixture)],
        capture_output=True,
        text=True,
        check=False,
    )


_CASES: list[tuple[str, int, str | None]] = [
    ("happy_path.md", 0, None),
    ("no_h1.md", 1, "h1"),
    ("no_demo.md", 1, "demo_video"),
    ("no_image.md", 1, "image_embed"),
    ("no_sift_install.md", 1, "sift_install"),
    ("no_docker.md", 1, "docker_compose"),
    ("no_architecture_diagram.md", 1, "architecture_diagram"),
    ("no_mit.md", 1, "mit_license"),
    ("banned_vocab.md", 1, "banned_vocab"),
    ("banned_in_code.md", 1, "banned_vocab"),
    ("find_evil_marketing.md", 1, "find_evil_marketing"),
    ("too_long.md", 1, "max_lines"),
]


@pytest.mark.parametrize(
    "fixture,exit_code,rule",
    _CASES,
    ids=[c[0].removesuffix(".md") for c in _CASES],
)
def test_gate_rule(fixture: str, exit_code: int, rule: str | None) -> None:
    r = _run(fixture)
    assert r.returncode == exit_code, r.stderr
    if rule is not None:
        assert rule in r.stderr, f"expected rule={rule!r} in stderr, got: {r.stderr}"


def test_mit_word_boundary_not_matched_in_substrings(tmp_path: Path) -> None:
    """`MIT` rule must use word boundaries — `transMIT`/`commit` are not licenses."""
    bad = tmp_path / "bad.md"
    bad.write_text(
        # All-the-other-rules-pass shape, but the only "MIT" letters are inside `commit`.
        "# SilentWitness\n\n> pitch\n\n<!-- DEMO_VIDEO_URL -->\n\n![alt](x.png)\n\n"
        "![Architecture](docs/diagrams/architecture.svg)\n\n"
        "```bash\ncurl https://x/install.sh | bash\n```\n\n"
        "```bash\ndocker compose up -d\n```\n\n"
        "Please commit and transMIT your changes.\n"
    )
    r = subprocess.run(
        [sys.executable, str(_GATE), str(bad)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 1
    assert "mit_license" in r.stderr


def test_real_readme_passes() -> None:
    """The committed README.md passes the gate."""
    r = subprocess.run(
        [sys.executable, str(_GATE), str(_GATE.parents[1] / "README.md")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr


def test_missing_file_exits_1() -> None:
    """Pointing at a nonexistent file exits 1 with `readable` rule."""
    r = subprocess.run(
        [sys.executable, str(_GATE), str(_FIXTURES / "DOES_NOT_EXIST.md")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 1
    assert "readable" in r.stderr
