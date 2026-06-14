"""MFT feeder — the NTFS Master File Table ($MFT) into :class:`IndexRecord` rows.

The $MFT records every file/dir on the volume with its path, size and MACB timestamps —
the backbone for "what files existed, where, and when" (staged archives, project files,
tools dropped in user dirs). Parsed with the Rust ``mft`` library (``PyMftParser``, MIT).

Each entry with a resolved ``full_path`` becomes one searchable row; the ``ts`` is the
``$STANDARD_INFORMATION`` modified time, or empty when SI is unavailable (the row is
still indexed on its path). Entries the parser yields as errors, and entries with no path
(unallocated/corrupt records carrying no useful filename), are skipped.

The pure mappers (``_entry_to_record``, ``_pick_std_info_modified``, ``_modified_iso``)
are unit-tested; ``mft_entry_records`` drives the Rust parser (forensics box).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from silentwitness_mcp.index._feeder_util import MAX_TEXT, Feeder, FeederStats, sha256_file
from silentwitness_mcp.index.store import IndexRecord

_LOG = logging.getLogger(__name__)

# $STANDARD_INFORMATION attribute type code (0x10).
_STD_INFO = 16


def _entry_to_record(
    *,
    full_path: str,
    entry_id: int,
    file_size: int,
    flags: str,
    ts: str,
    mft_path: str,
    audit_id: str,
    host: str,
    sha256: str,
) -> IndexRecord:
    """Build one searchable MFT row (path is the dominant search key)."""
    text = f"MFT path={full_path} size={file_size} flags={flags}"
    return IndexRecord(
        text=text[:MAX_TEXT],
        source_tool="mft",
        artifact_path=f"{mft_path}#{entry_id}",
        host=host,
        ts=ts,
        audit_id=audit_id,
        sha256=sha256,
    )


def _modified_iso(modified: Any) -> str:
    """ISO string from a datetime-like ``modified`` value, or "" if absent/unusable."""
    if modified is None:
        return ""
    try:
        return str(modified.isoformat())
    except (AttributeError, ValueError):
        return ""


def _pick_std_info_modified(attrs: Iterable[tuple[int, Any]]) -> str:
    """From ``(type_code, content)`` pairs, the $STANDARD_INFORMATION modified time."""
    for type_code, content in attrs:
        if type_code == _STD_INFO:
            return _modified_iso(getattr(content, "modified", None))
    return ""


def _std_info_modified(entry: Any) -> str:
    """ISO $STANDARD_INFORMATION modified time for an MFT entry, or "" if unavailable."""
    try:
        attributes = entry.attributes()
    except Exception:  # best-effort: a bad attribute list costs only the timestamp
        return ""

    def _pairs() -> Iterator[tuple[int, Any]]:
        for attr in attributes:
            if isinstance(attr, Exception):
                continue
            type_code = getattr(attr, "type_code", None)
            if type_code is not None:
                yield type_code, getattr(attr, "attribute_content", None)

    return _pick_std_info_modified(_pairs())


def mft_entry_records(
    path: Path,
    *,
    audit_id: str,
    host: str = "",
    source_path: str | None = None,
    stats: FeederStats | None = None,
) -> Iterator[IndexRecord]:
    """Stream one :class:`IndexRecord` per named $MFT entry. ``mft`` is imported lazily."""
    import mft

    cite = source_path if source_path is not None else str(path)
    sha = sha256_file(path)
    for entry in mft.PyMftParser(str(path)).entries():
        if isinstance(entry, Exception):  # the parser yields errors inline
            _LOG.debug("mft: skipped unreadable entry in %s: %s", path.name, entry)
            if stats is not None:
                stats.skip("mft_unreadable_entry")
            continue
        full_path = getattr(entry, "full_path", "") or ""
        if not full_path:  # unallocated/corrupt record with no usable filename
            if stats is not None:
                stats.skip("mft_no_path_entry")
            continue
        yield _entry_to_record(
            full_path=full_path,
            entry_id=getattr(entry, "entry_id", 0),
            file_size=getattr(entry, "file_size", 0),
            flags=str(getattr(entry, "flags", "")),
            ts=_std_info_modified(entry),
            mft_path=cite,
            audit_id=audit_id,
            host=host,
            sha256=sha,
        )


# Compile-time assertion that the feeder still matches the shared contract.
_: Feeder = mft_entry_records

__all__ = ["mft_entry_records"]
