"""Behavioural tests for the project ``justfile``.

These tests parse the output of the real ``just`` CLI — no mocks per
architecture §14. They cover the BDD criteria in
story-justfile-targets.md that are testable without spawning the
recipes themselves (which would shell out to `uv`, `docker`, `pytest`,
etc. and turn the unit suite into an integration run).

The recipe-execution BDDs (`just install` actually installs, `just lint`
actually lints, etc.) live in the story's Shell verification block.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_JUSTFILE_PATH = _REPO_ROOT / "justfile"
_EXPECTED_TARGETS: frozenset[str] = frozenset(
    {"install", "format", "lint", "test", "property", "ci", "clean", "build"}
)


def _just_available() -> bool:
    return shutil.which("just") is not None


pytestmark = pytest.mark.skipif(
    not _just_available(),
    reason="`just` CLI not installed locally; CI provisions it.",
)


def _run_just(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["just", *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=_REPO_ROOT,
    )


def test_just_list_succeeds() -> None:
    """``just --list`` parses the justfile and exits 0."""
    result = _run_just("--list")
    assert result.returncode == 0, f"`just --list` failed: {result.stderr}"


def test_just_list_advertises_all_required_recipes() -> None:
    """Every recipe named in story-justfile-targets.md is present in `just --list`."""
    result = _run_just("--list")
    listed = {
        # `just --list` indents recipe names; strip + first token.
        line.strip().split()[0]
        for line in result.stdout.splitlines()
        if line.startswith("    ")
    }
    missing = _EXPECTED_TARGETS - listed
    assert (
        not missing
    ), f"justfile missing required recipes: {sorted(missing)} (listed: {sorted(listed)})"


def test_justfile_declares_strict_shell_and_dotenv_load() -> None:
    """The `set shell := ["bash", "-cu"]` and `set dotenv-load := true` directives are present.

    `-cu` makes unset-variable references abort the recipe rather than expand
    silently. `dotenv-load` reads `.env` so local API keys flow into the test
    process (CICD_SPEC §9.2).
    """
    text = _JUSTFILE_PATH.read_text(encoding="utf-8")
    assert (
        'set shell := ["bash", "-cu"]' in text
    ), 'missing `set shell := ["bash", "-cu"]` directive'
    assert "set dotenv-load := true" in text, "missing `set dotenv-load := true` directive"


def test_ci_recipe_depends_on_lint_test_property() -> None:
    """`just ci` chains lint + test + property as its declared dependencies.

    The story's BDD requires that ``just ci`` is the developer's local CI
    mirror. Recipe-level dependencies are the cleanest way to express
    "run these in order, fail fast."
    """
    text = _JUSTFILE_PATH.read_text(encoding="utf-8")
    assert (
        "ci: lint test property" in text
    ), "ci recipe must declare `ci: lint test property` so the gates fire in order"


def test_build_recipe_invokes_docker_build() -> None:
    """The added `build` recipe wraps `docker build` for story-docker-baseline's image."""
    text = _JUSTFILE_PATH.read_text(encoding="utf-8")
    assert "build:" in text, "missing `build` recipe"
    assert "docker build" in text, "build recipe must invoke `docker build`"
    assert "silentwitness:local" in text, "build recipe must tag the image as `silentwitness:local`"
