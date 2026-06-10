"""Pydantic-level tests for :class:`DllEntry`.

These exercise the model's validator chain directly (no subprocess
mock, no orchestrator). The pipeline-level refusal contract that
:class:`ValidationError` surfaces as
:attr:`VolFailureReason.OUTPUT_PARSE_FAILED` is covered in
:mod:`test_vol_dlllist`."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from silentwitness_mcp.tools._memory_models import DllEntry


def _row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "PID": 1234,
        "Process": "svchost.exe",
        "Base": 0x7FFE000000,
        "Size": 0x100000,
        "Name": "ntdll.dll",
        "Path": "C:\\Windows\\System32\\ntdll.dll",
        "LoadTime": "2026-06-10T08:00:00+00:00",
        "File output": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Path placeholder collapse (Vol3 paged-out emission)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "placeholder",
    [
        # Vol3 paged-out PEB placeholders (the round-1 fix target).
        "Required memory at 0x7ffe4dc8 is not valid",
        "required memory at 0x7ffe4dc8 is not valid",
        "REQUIRED MEMORY AT 0x7ffe4dc8 is not valid",
        " Required memory at 0x7ffe4dc8 is not valid",
        "Swap layer is not available",
        "swap layer is not available",
        # Empty-after-strip — structurally no value.
        "",
        "   ",
        "\x00 \x00",
        " \x00 \x00 ",
    ],
)
def test_path_placeholders_collapse_to_none(placeholder: str) -> None:
    """Vol3 paged-out placeholders MUST collapse to None — a
    placeholder string reaching the entity gate as a citable DLL
    load path is the silent-failure round-1 was filed against."""
    entry = DllEntry.model_validate(_row(Path=placeholder))
    assert entry.path is None


@pytest.mark.parametrize(
    "real_path",
    [
        "C:\\Windows\\System32\\ntdll.dll",
        "C:\\Users\\Public\\ntdll.dll",  # side-loading red flag
        "\\Device\\HarddiskVolume2\\Windows\\System32\\kernel32.dll",
        # Trap: starts with the unanchored placeholder prefix but
        # is a real cmdline-style argument (no hex suffix).
        "Required memory at boot loader v2.0",
        # Bare "null" / "none" — kernel namespace allows these as
        # legitimate names; path/name normaliser preserves them.
        "null",
        "NONE",
    ],
)
def test_real_paths_preserved_verbatim(real_path: str) -> None:
    """Real DLL paths (including the side-loading red flag and
    bare-sentinel-as-real-name cases) round-trip byte-identical."""
    entry = DllEntry.model_validate(_row(Path=real_path))
    assert entry.path == real_path


def test_native_none_path_preserved() -> None:
    entry = DllEntry.model_validate(_row(Path=None))
    assert entry.path is None


# ---------------------------------------------------------------------------
# Schema-drift catch — extra="forbid"
# ---------------------------------------------------------------------------


def test_unknown_column_rejected() -> None:
    """Vol3 column drift (e.g. a future ``Reflective`` flag) MUST
    fail validation — forensic audit cannot silently drop columns."""
    with pytest.raises(ValidationError):
        DllEntry.model_validate({**_row(), "Reflective": True})
