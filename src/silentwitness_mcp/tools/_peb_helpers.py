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
"""Case-insensitive sentinel strings Vol3 may emit in lieu of a real
command-line string. **Consumed ONLY by**
:func:`normalise_cmdline_args` — NOT by
:func:`normalise_peb_path_or_name`. Bare ``"null"`` is a legitimate
kernel-namespace object name (some malware uses it deliberately), so
the peb-path normaliser preserves it verbatim. If you add a sentinel
here, decide explicitly whether peb-paths should ALSO collapse it;
if yes, extract a separate ``_PEB_NULL_SENTINELS`` and consume in
both."""

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
"""Action-shaping catalogue of the common kernel object types an
investigator most often filters on with ``--object-types``. This is
a **caller-input allowlist for the Vol3 CLI filter**, NOT a schema
allowlist for Vol3's output: the kernel's ``ObTypeIndexTable`` is
open-ended (Job, Timer, IoCompletion, WindowStation, Desktop,
Driver, Device, ALPC Port, Mailslot, etc. all appear on real
images). :class:`HandleEntry.type` is ``str``; this tuple gates only
what the wrapper accepts as a filter argument."""


def normalise_cmdline_args(value: object) -> object:
    """Collapse Vol3 "no string available" cases for ``CmdlineEntry.args``.

    Used ONLY for cmdline.Args, where ``"null"`` / ``"none"`` /
    empty-after-strip are legitimate sentinels for "process had no
    command line". Vol3's renderer is the source of these strings,
    not the kernel namespace, so collapsing them is honest."""
    if not isinstance(value, str):
        return value
    folded = _OUTER_WHITESPACE_NUL.sub("", value).lower()
    if folded in _NULL_SENTINELS or any(folded.startswith(p) for p in _PEB_PLACEHOLDER_PREFIXES):
        return None
    return value


def normalise_peb_path_or_name(value: object) -> object:
    """Collapse only Vol3-emitted paged-out placeholders for fields
    sourced from the kernel object namespace (``DllEntry.path``,
    ``HandleEntry.name``). Unlike :func:`normalise_cmdline_args`,
    bare ``"null"`` / ``"none"`` strings are preserved verbatim —
    the kernel allows naming an object literally ``"null"`` (some
    malware does this), and collapsing would erase audit evidence.

    Empty-after-strip still collapses to ``None`` because an empty
    path/name is structurally "no value", not a legitimate name."""
    if not isinstance(value, str):
        return value
    stripped = _OUTER_WHITESPACE_NUL.sub("", value)
    if not stripped:
        return None
    folded = stripped.lower()
    if any(folded.startswith(p) for p in _PEB_PLACEHOLDER_PREFIXES):
        return None
    return value


_MIN_VALID_PID: Final = 1


def validate_pid_filter(tool_name: str, pid: int | None) -> None:
    """PID 0 (System Idle) and negative pids have no _EPROCESS / PEB —
    reject at the wrapper boundary so an LLM-driven typo gets a clean
    diagnostic before subprocess spawn. ``bool`` is excluded
    explicitly (Python's bool-as-int subclass trap)."""
    if pid is None:
        return
    if not isinstance(pid, int) or isinstance(pid, bool):
        raise TypeError(f"{tool_name}: pid must be int or None; got {type(pid).__name__}")
    if pid < _MIN_VALID_PID:
        raise ValueError(
            f"{tool_name}: pid must be >= {_MIN_VALID_PID} or None; got {pid} "
            f"(PID 0 = System Idle has no PEB / VAD)"
        )


def validate_object_types_filter(tool_name: str, object_types: list[str] | None) -> None:
    """``None`` = no filter; ``[]`` = caller-side typo.

    Three rejection layers:

    1. **Type guard**: must be a ``list``. ``set`` iterates non-
       deterministically and would corrupt audit-trail reproducibility
       via a different ``",".join`` ordering on each call. ``tuple`` is
       deterministic but rejected for signature consistency
       (annotation is ``list[str] | None``).
    2. **Per-entry shape**: non-str, empty, comma-bearing, or
       ``str.strip()``-bearing entries fail. ``str.strip()`` catches
       ASCII whitespace + NBSP + ideographic space; it does NOT catch
       zero-width-class characters (U+200B/C/D). Those rely on the
       catalogue check below for rejection.
    3. **Action-shaping catalogue**: entries not in
       :data:`HANDLE_OBJECT_TYPES`. Vol3 accepts arbitrary kernel
       object names, so this is the wrapper's curation, not Vol3's
       allowlist."""
    if object_types is None:
        return
    if not isinstance(object_types, list):
        raise TypeError(
            f"{tool_name}: object_types must be list[str] or None; got "
            f"{type(object_types).__name__} (set/tuple iteration order is "
            f"non-deterministic in comma-joined argv)"
        )
    if not object_types:
        raise ValueError(f"{tool_name}: object_types must be a non-empty list or None")
    bad = [t for t in object_types if not isinstance(t, str) or not t or t != t.strip() or "," in t]
    if bad:
        raise ValueError(
            f"{tool_name}: object_types entries must be non-empty, "
            f"non-whitespace-bearing, comma-free strings; got {bad!r}"
        )
    unknown = [t for t in object_types if t not in HANDLE_OBJECT_TYPES]
    if unknown:
        raise ValueError(
            f"{tool_name}: unknown object_type(s) {unknown!r}; "
            f"catalogue (action-shaping): {list(HANDLE_OBJECT_TYPES)}"
        )


__all__ = [
    "HANDLE_OBJECT_TYPES",
    "normalise_cmdline_args",
    "normalise_peb_path_or_name",
    "validate_object_types_filter",
    "validate_pid_filter",
]
