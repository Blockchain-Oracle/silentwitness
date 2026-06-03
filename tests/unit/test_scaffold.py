"""Scaffold sanity tests — story-scaffold-uv-pyproject acceptance criteria.

Three behavioural assertions, each mapping back to a BDD criterion in the
story file:

1. All three src/ packages import cleanly under Python 3.12+.
2. ``silentwitness_mcp.__version__`` is a SemVer string (semantic-release
   target — must round-trip through python-semantic-release's parser).
3. The interpreter actually running the test suite is Python 3.12 or newer
   (matches pyproject.toml ``requires-python = ">=3.12,<3.14"``).
"""

from __future__ import annotations

import re
import sys

import silentwitness_agent
import silentwitness_common
import silentwitness_mcp

# Strict SemVer 2.0.0 with optional prerelease/build metadata — same shape
# python-semantic-release parses.
_SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def test_all_three_packages_import() -> None:
    """All three src/ packages declared in pyproject.toml resolve via import."""
    assert silentwitness_mcp is not None
    assert silentwitness_agent is not None
    assert silentwitness_common is not None


def test_silentwitness_mcp_version_is_semver() -> None:
    """``silentwitness_mcp.__version__`` must satisfy strict SemVer.

    python-semantic-release parses this constant on every release; if the
    shape drifts to something non-SemVer, the release pipeline silently
    breaks. Pin the contract here.
    """
    version = silentwitness_mcp.__version__
    assert isinstance(version, str), f"expected str, got {type(version).__name__}"
    assert _SEMVER_PATTERN.match(version), f"__version__={version!r} is not strict SemVer 2.0.0"


def test_python_runtime_is_312_or_newer() -> None:
    """The CI matrix and local dev must run on Python ≥ 3.12.

    Matches ``requires-python = ">=3.12,<3.14"`` in pyproject.toml. If a 3.11
    venv tries to install us, this test fails loudly before any product code
    misbehaves on the older runtime.
    """
    major, minor = sys.version_info[:2]
    assert (major, minor) >= (3, 12), f"Python ≥3.12 required; running on {sys.version}"
