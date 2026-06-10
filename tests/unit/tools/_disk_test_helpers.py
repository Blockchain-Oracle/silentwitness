"""Shared mock-subprocess + monkeypatch helpers for the disk-family
test suite. Extracted from ``test_disk_parse_mft.py`` so the per-tool
test files can stay under the 400-LOC CI budget while sharing the
dotnet-EZ-Tools mock infrastructure."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from silentwitness_mcp._lifecycle import MountCheckResult


class FakeProc:
    """Stand-in for :class:`asyncio.subprocess.Process` used to mock
    the dotnet subprocess at the asyncio layer."""

    def __init__(self, *, stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0) -> None:
        self._stdout, self._stderr = stdout, stderr
        self.returncode: int | None = returncode

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr

    def terminate(self) -> None: ...
    def kill(self) -> None:
        self.returncode = -9

    async def wait(self) -> int:
        return self.returncode if self.returncode is not None else -1


def install_dotnet_mock(
    monkeypatch: pytest.MonkeyPatch,
    *,
    csv_fixture: Path,
    csv_out_dir: Path,
    csv_filename: str = "20260610150000_MFTECmd_MFT_Output.csv",
    proc: FakeProc | None = None,
) -> list[tuple[str, ...]]:
    """Mock asyncio subprocess. Side-effect: on returncode==0, copy
    the chosen fixture CSV into csv_out_dir so the wrapper glob
    finds it."""
    calls: list[tuple[str, ...]] = []
    proc = proc or FakeProc(stdout=b"", stderr=b"", returncode=0)

    async def _fake(*argv: str, **_kw: Any) -> FakeProc:
        calls.append(argv)
        if proc.returncode == 0:
            csv_out_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(csv_fixture, csv_out_dir / csv_filename)
        return proc

    monkeypatch.setattr(
        "silentwitness_mcp.tools._disk_common.asyncio.create_subprocess_exec", _fake
    )
    return calls


def force_dotnet(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, exists: bool = True) -> None:
    """Point DOTNET_BIN at a tmp path. Cleaner than patching
    Path.exists globally."""
    fake = tmp_path / "fake_dotnet"
    if exists:
        fake.touch()
    monkeypatch.setattr("silentwitness_mcp.tools._disk_common.DOTNET_BIN", fake)


def force_mount_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the mount gate to pass independent of host config."""
    monkeypatch.setattr(
        "silentwitness_mcp.tools._disk_common.check_mount",
        lambda: MountCheckResult(ok=True, advisories=[]),
    )


def force_mount_fail(
    monkeypatch: pytest.MonkeyPatch,
    advisory: str = "mount missing noexec",
) -> None:
    """Force the mount gate to fail — tests MOUNT_NOT_RO_NOEXEC_NOSUID."""
    monkeypatch.setattr(
        "silentwitness_mcp.tools._disk_common.check_mount",
        lambda: MountCheckResult(ok=False, advisories=[advisory]),
    )


__all__ = [
    "FakeProc",
    "force_dotnet",
    "force_mount_fail",
    "force_mount_ok",
    "install_dotnet_mock",
]
