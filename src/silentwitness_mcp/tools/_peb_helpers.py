"""Shared helpers for Vol3 PEB-sourced string fields and Vol3 handle-
type catalogue. Consumed by :mod:`_memory_models` for field-level
normalisation and by :mod:`memory` for wrapper-input filter validation."""

from __future__ import annotations

import re
from typing import Final

_PEB_PLACEHOLDER_PREFIXES: Final[tuple[str, ...]] = (
    # Anchored on Vol3's hex-address suffix so a real command line that
    # legitimately starts with "Required memory at" (some Windows
    # bootloader / firmware utilities) is preserved verbatim.
    "required memory at 0x",
    "swap layer is not available",
)
"""Closed catalogue of Vol3 "couldn't read this memory region"
sentinel string prefixes, pre-lowercased at module load."""

# Mechanical enforcement of the lowercase invariant.
if any(p != p.lower() for p in _PEB_PLACEHOLDER_PREFIXES):
    raise ValueError("_PEB_PLACEHOLDER_PREFIXES entries must be pre-lowercased")

_NULL_SENTINELS: Final[frozenset[str]] = frozenset({"", "null", "none"})
"""Case-insensitive set of sentinel strings Vol3 may emit in lieu of
a real string value."""

_OUTER_WHITESPACE_NUL: Final = re.compile(r"^[\s\x00]+|[\s\x00]+$")
"""Strip outer whitespace + NUL bytes in one pass. Chained
``.strip().strip("\\x00")`` mishandles ``"\\x00 \\x00"`` (outer
NULs removed, inner space remains, sentinel check then fails)."""

HANDLE_OBJECT_TYPES: Final[tuple[str, ...]] = (
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
)
"""Closed kernel-object-type set Vol3 ``windows.handles`` emits.
Stable across Windows 7→11; a new type appearing here is schema
drift that SHOULD fail closed (downstream caveats hard-code these
names). Vol3 source: ``ObTypeIndexTable`` walk."""


def normalise_peb_string(value: object) -> object:
    """Collapse Vol3 "no string available" cases to None for any
    PEB-sourced ``str | None`` field (cmdline.Args, dlllist.Path,
    handles.Name). A real string round-trips verbatim. Non-str
    values fall through so Pydantic's outer typing loud-fails."""
    if not isinstance(value, str):
        return value
    folded = _OUTER_WHITESPACE_NUL.sub("", value).lower()
    if folded in _NULL_SENTINELS or any(folded.startswith(p) for p in _PEB_PLACEHOLDER_PREFIXES):
        return None
    return value


_MIN_VALID_PID: Final = 1


def validate_pid_filter(tool_name: str, pid: int | None) -> None:
    """PID 0 (System Idle) and negative pids have no _EPROCESS / PEB —
    reject at the wrapper boundary so an LLM-driven typo gets a clean
    diagnostic before subprocess spawn."""
    if pid is not None and pid < _MIN_VALID_PID:
        raise ValueError(
            f"{tool_name}: pid must be >= {_MIN_VALID_PID} or None; got {pid} "
            f"(PID 0 = System Idle has no PEB / VAD)"
        )


def validate_object_types_filter(tool_name: str, object_types: list[str] | None) -> None:
    """``None`` = no filter; ``[]`` = caller-side typo. Reject loudly
    so the diagnostic surfaces pre-spawn. Also rejects whitespace-only,
    comma-bearing (pre-joined by a bad caller), and non-allowlist
    entries — Vol3 would otherwise receive a malformed comma-joined
    arg and ship a success envelope with zero rows."""
    if object_types is None:
        return
    if not object_types:
        raise ValueError(f"{tool_name}: object_types must be a non-empty list or None")
    bad = [t for t in object_types if not isinstance(t, str) or not t.strip() or "," in t]
    if bad:
        raise ValueError(
            f"{tool_name}: object_types entries must be non-empty, "
            f"whitespace-free, comma-free strings; got {bad!r}"
        )
    unknown = [t for t in object_types if t not in HANDLE_OBJECT_TYPES]
    if unknown:
        raise ValueError(
            f"{tool_name}: unknown object_type(s) {unknown!r}; "
            f"Vol3 allowlist: {list(HANDLE_OBJECT_TYPES)}"
        )


__all__ = [
    "HANDLE_OBJECT_TYPES",
    "normalise_peb_string",
    "validate_object_types_filter",
    "validate_pid_filter",
]
