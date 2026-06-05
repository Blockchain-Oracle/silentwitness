"""Tests for ``silentwitness_mcp._lifecycle.check_mount`` covering the
findmnt subprocess branches. The pre-existing test only exercised the
"evidence dir absent" early-return; the actual findmnt execution path
(lines 98-125 in the merged version) had 0% coverage. Architecture
§4.11 makes this validator the gate that protects /evidence integrity,
so each branch — happy, missing-options, timeout, nonzero return —
needs an explicit pin.

The ``findmnt`` absent + ``target.exists()`` branch returns
``ok=False`` (fail-closed) — a production-shaped /evidence with the
mount validator effectively disabled (util-linux stripped, PATH
manipulated) would otherwise silently boot writable. The ``target``
absent + ``findmnt`` absent combination is still a soft-skip —
that's the dev/macOS environment.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from silentwitness_mcp._lifecycle import (
    REQUIRED_MOUNT_OPTS,
    AppContext,
    MountCheckResult,
    check_mount,
    lifespan,
    warm_injection_patterns,
)


@pytest.fixture
def existing_target(tmp_path: Path) -> Path:
    """A directory that exists on disk so check_mount progresses past
    the ``target.exists()`` early-return."""
    target = tmp_path / "evidence"
    target.mkdir()
    return target


def _completed(
    stdout: str = "", returncode: int = 0, stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["findmnt"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_check_mount_skips_when_target_absent(tmp_path: Path) -> None:
    """target.exists()==False ⇒ ok=True soft-skip (dev/test env)."""
    target = tmp_path / "never_created"
    result = check_mount(target)
    assert result.ok is True
    assert any("does not exist" in a for a in result.advisories)


def test_check_mount_fails_closed_when_findmnt_absent_and_target_exists(
    existing_target: Path,
) -> None:
    """Production-shaped /evidence present + findmnt absent → fail-closed.
    Previously this branch returned ok=True, which would have left the
    mount validator a no-op on a SIFT image with util-linux stripped."""
    with patch("silentwitness_mcp._lifecycle.shutil.which", return_value=None):
        result = check_mount(existing_target)
    assert result.ok is False
    assert any("findmnt absent" in a for a in result.advisories)


def test_check_mount_happy_path(existing_target: Path) -> None:
    """findmnt returns OPTIONS containing all required ro,noexec,nosuid."""
    with (
        patch("silentwitness_mcp._lifecycle.shutil.which", return_value="/usr/bin/findmnt"),
        patch(
            "silentwitness_mcp._lifecycle.subprocess.run",
            return_value=_completed(stdout="rw,ro,noexec,nosuid,relatime\n"),
        ),
    ):
        result = check_mount(existing_target)
    assert result.ok is True
    assert result.advisories == []


def test_check_mount_rejects_missing_required_options(existing_target: Path) -> None:
    """findmnt returns valid OPTIONS but missing one of ro/noexec/nosuid."""
    with (
        patch("silentwitness_mcp._lifecycle.shutil.which", return_value="/usr/bin/findmnt"),
        patch(
            "silentwitness_mcp._lifecycle.subprocess.run",
            return_value=_completed(stdout="ro,nosuid"),
        ),
    ):
        result = check_mount(existing_target)
    assert result.ok is False
    advisory = " ".join(result.advisories)
    assert "missing required options" in advisory
    assert "noexec" in advisory


def test_check_mount_rejects_nonzero_returncode(existing_target: Path) -> None:
    """findmnt exits nonzero — return ok=False with stderr in the advisory."""
    with (
        patch("silentwitness_mcp._lifecycle.shutil.which", return_value="/usr/bin/findmnt"),
        patch(
            "silentwitness_mcp._lifecycle.subprocess.run",
            return_value=_completed(returncode=1, stderr="findmnt: target not found"),
        ),
    ):
        result = check_mount(existing_target)
    assert result.ok is False
    advisory = " ".join(result.advisories)
    assert "returncode=1" in advisory
    assert "target not found" in advisory


def test_check_mount_handles_timeout(existing_target: Path) -> None:
    """findmnt subprocess times out — return ok=False with the timeout
    surfaced in the advisory instead of letting TimeoutExpired escape
    the lifespan setup."""
    with (
        patch("silentwitness_mcp._lifecycle.shutil.which", return_value="/usr/bin/findmnt"),
        patch(
            "silentwitness_mcp._lifecycle.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["findmnt"], timeout=5),
        ),
    ):
        result = check_mount(existing_target)
    assert result.ok is False
    advisory = " ".join(result.advisories)
    assert "execution failed" in advisory


def test_check_mount_handles_oserror(existing_target: Path) -> None:
    """A bare OSError (e.g. permissions, ENOMEM) from the subprocess
    layer must also surface as ok=False — not propagate as a startup
    crash."""
    with (
        patch("silentwitness_mcp._lifecycle.shutil.which", return_value="/usr/bin/findmnt"),
        patch(
            "silentwitness_mcp._lifecycle.subprocess.run",
            side_effect=OSError("permission denied"),
        ),
    ):
        result = check_mount(existing_target)
    assert result.ok is False


def test_check_mount_empty_stderr_renders_placeholder(existing_target: Path) -> None:
    """If findmnt exits nonzero with no stderr (rare but possible) the
    advisory still parses — operator gets a clean diagnostic, not a
    stray `(no stderr)` next to a real error."""
    with (
        patch("silentwitness_mcp._lifecycle.shutil.which", return_value="/usr/bin/findmnt"),
        patch(
            "silentwitness_mcp._lifecycle.subprocess.run",
            return_value=_completed(returncode=2, stderr=""),
        ),
    ):
        result = check_mount(existing_target)
    assert result.ok is False
    assert any("(no stderr)" in a for a in result.advisories)


def test_required_mount_opts_strict_subset() -> None:
    """If REQUIRED_MOUNT_OPTS ever loosens (architecture §4.11 mandates
    exactly these three), this test fails so the change requires
    deliberate review."""
    assert REQUIRED_MOUNT_OPTS == frozenset({"ro", "noexec", "nosuid"})


def test_mount_check_result_default_advisories_is_empty_list() -> None:
    """Default-factory contract: each instance gets its own list (no
    shared mutable default that would let one failure leak advisories
    into the next call)."""
    a = MountCheckResult(ok=True)
    b = MountCheckResult(ok=True)
    a.advisories.append("leak-canary")
    assert "leak-canary" not in b.advisories


def test_warm_injection_patterns_returns_count() -> None:
    """Smoke: the warmup actually loads patterns and returns a
    positive count. If this returns 0, the YAML resource is missing or
    the loader regressed."""
    count = warm_injection_patterns()
    assert count > 0


@pytest.mark.anyio
async def test_lifespan_yields_app_context_with_warmup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: the asynccontextmanager binds an AppContext with the
    mount result and a populated pattern count, then unbinds cleanly."""
    # Force the soft-skip branch by pointing at a non-existent path so
    # the test doesn't depend on the host's /evidence presence.
    monkeypatch.setattr(
        "silentwitness_mcp._lifecycle.DEFAULT_EVIDENCE_ROOT",
        Path("/no/such/path/for/test"),
    )
    async with lifespan(server=None) as ctx:  # type: ignore[arg-type]
        assert isinstance(ctx, AppContext)
        assert ctx.mount.ok is True
        assert ctx.injection_pattern_count > 0


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
