"""Pydantic-level tests for :class:`HandleEntry`.

These exercise the model's validator chain directly. The pipeline-
level refusal contract is covered in :mod:`test_vol_handles`."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from silentwitness_mcp.tools._memory_models import HandleEntry


def _row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "PID": 1234,
        "Process": "svchost.exe",
        "Offset": 0xFA8000123456,
        "HandleValue": 0x100,
        "Type": "File",
        "GrantedAccess": 0x120089,
        "Name": "\\REGISTRY\\MACHINE\\SOFTWARE\\Microsoft\\Cryptography",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# type: str — Vol3 forwards _OBJECT_TYPE.Name verbatim (open set)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kernel_type",
    [
        # Documented common types covered by the action-shaping catalogue.
        "Process",
        "Thread",
        "File",
        "Key",
        "Section",
        "Event",
        "Mutant",
        "Semaphore",
        "Token",
        "Directory",
        "SymbolicLink",
        # Standard kernel object types Vol3 has been observed emitting
        # on Windows 7-11 images that would silently fail under a closed
        # Literal[...] catalogue. Presence is session/role-dependent
        # (e.g. DxgkSharedResource needs an active graphics session;
        # Composition is DWM-only).
        "Job",
        "Timer",
        "IoCompletion",
        "IoCompletionReserve",
        "WindowStation",
        "Desktop",
        "KeyedEvent",
        "WaitablePort",
        "TpWorkerFactory",
        "Adapter",
        "Controller",
        "Profile",
        "Driver",
        "Device",
        "DebugObject",
        "EtwRegistration",
        "ALPC Port",
        "Mailslot",
        "Callback",
        "Composition",
        "DxgkSharedResource",
        "FilterCommunicationPort",
        "PowerRequest",
        "TmTx",
    ],
)
def test_type_accepts_kernel_object_namespace_verbatim(kernel_type: str) -> None:
    """Vol3 walks ``ObTypeIndexTable`` and forwards ``_OBJECT_TYPE.Name``
    verbatim — the kernel-side set is open. A closed ``Literal[...]``
    would fail-closed at the first emission of any type not on the
    list."""
    entry = HandleEntry.model_validate(_row(Type=kernel_type))
    assert entry.type == kernel_type


# ---------------------------------------------------------------------------
# DWORD bounds on handle_value + granted_access
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "boundary_ok"),
    [
        ("HandleValue", 0),
        ("HandleValue", 0xFFFFFFFF),
        ("GrantedAccess", 0),
        ("GrantedAccess", 0xFFFFFFFF),
    ],
)
def test_dword_bounds_accept_boundary_values(field: str, boundary_ok: int) -> None:
    """0 and 0xFFFFFFFF are the unsigned DWORD edges — must accept."""
    entry = HandleEntry.model_validate({**_row(), field: boundary_ok})
    attr = "handle_value" if field == "HandleValue" else "granted_access"
    assert getattr(entry, attr) == boundary_ok


@pytest.mark.parametrize("field", ["HandleValue", "GrantedAccess"])
@pytest.mark.parametrize("bad_value", [-1, -0x100, 0x100000000, 0xFFFFFFFFFFFF])
def test_dword_bounds_reject_out_of_range(field: str, bad_value: int) -> None:
    """Windows ABI guarantees unsigned DWORD for HANDLE and
    ACCESS_MASK; negatives and >2^32 values are schema drift."""
    with pytest.raises(ValidationError):
        HandleEntry.model_validate({**_row(), field: bad_value})


# ---------------------------------------------------------------------------
# Name placeholder collapse vs verbatim preservation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "placeholder",
    [
        "Required memory at 0x7ffe4dc8 is not valid",
        "Swap layer is not available",
        # Empty-after-strip.
        "",
        "   ",
        "\x00 \x00",
    ],
)
def test_name_placeholders_collapse_to_none(placeholder: str) -> None:
    entry = HandleEntry.model_validate(_row(Name=placeholder))
    assert entry.name is None


@pytest.mark.parametrize(
    "real_name",
    [
        "\\REGISTRY\\MACHINE\\SOFTWARE\\Microsoft\\Cryptography",
        "\\Device\\HarddiskVolume2\\Windows",
        "\\Device\\PhysicalMemory",  # rootkit candidate
        "\\BaseNamedObjects\\Global\\mutex-abc",  # pragma: allowlist secret
        "lsass.exe",
        # Bare "null"/"none" — some malware deliberately picks
        # deceptive names; preserve verbatim (kernel namespace
        # concern, not Vol3-emission concern).
        "null",
        "NULL",
        "none",
    ],
)
def test_real_names_preserved_verbatim(real_name: str) -> None:
    entry = HandleEntry.model_validate(_row(Name=real_name))
    assert entry.name == real_name


def test_native_none_name_preserved() -> None:
    entry = HandleEntry.model_validate(_row(Name=None))
    assert entry.name is None


# ---------------------------------------------------------------------------
# No cross-field invariant — tampering detection is the tool's purpose
# ---------------------------------------------------------------------------


def test_no_process_to_name_cross_field_invariant() -> None:
    """Deliberate: a Process handle whose Name is anomalous (e.g.
    a device path) IS the tamper signal vol_handles exists to
    surface. Type-layer cross-field validation would make tampered
    rows un-representable. Mirrors CmdlineEntry's deliberate non-
    invariant."""
    entry = HandleEntry.model_validate(_row(Type="Process", Name="\\Device\\Mup\\evil.iso"))
    assert entry.type == "Process"
    assert entry.name == "\\Device\\Mup\\evil.iso"


# ---------------------------------------------------------------------------
# Schema-drift catch — extra="forbid"
# ---------------------------------------------------------------------------


def test_unknown_column_rejected() -> None:
    with pytest.raises(ValidationError):
        HandleEntry.model_validate({**_row(), "Reflective": True})
