"""MFT feeder — the NTFS Master File Table ($MFT) into :class:`IndexRecord` rows.

The $MFT records every file/dir on the volume with its path, size and MACB timestamps —
the backbone for "what files existed, where, and when" (staged archives, project files,
tools dropped in user dirs). Parsed with the Rust ``mft`` library (``PyMftParser``, MIT,
same fast/permissive lineage as the EVTX reader).

Each entry with a resolved ``full_path`` becomes one searchable row; the timestamp is the
``$STANDARD_INFORMATION`` modified time. Entries the parser yields as errors, and entries
with no path (unallocated/corrupt records carrying no useful filename), are skipped.

``_entry_to_record`` is a pure, unit-tested mapper; ``mft_entry_records`` drives the Rust
parser (forensics box).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from silentwitness_mcp.index._feeder_util import MAX_TEXT, Feeder, sha256_file
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


def _std_info_modified(entry: Any) -> str:
    """ISO modified time from the entry's $STANDARD_INFORMATION, or "" if unavailable."""
    try:
        attributes = entry.attributes()
    except Exception:  # entry with an unreadable attribute list
        return ""
    for attr in attributes:
        if isinstance(attr, Exception):
            continue
        if getattr(attr, "type_code", None) != _STD_INFO:
            continue
        content = getattr(attr, "attribute_content", None)
        modified = getattr(content, "modified", None)
        if modified is not None:
            try:
                return str(modified.isoformat())
            except (AttributeError, ValueError):
                return ""
        return ""
    return ""


def mft_entry_records(
    path: Path, *, audit_id: str, host: str = "", source_path: str | None = None
) -> Iterator[IndexRecord]:
    """Stream one :class:`IndexRecord` per named $MFT entry. ``mft`` is imported lazily."""
    import mft

    cite = source_path if source_path is not None else str(path)
    sha = sha256_file(path)
    for entry in mft.PyMftParser(str(path)).entries():
        if isinstance(entry, Exception):  # the parser yields errors inline
            _LOG.debug("mft: skipped unreadable entry in %s: %s", path.name, entry)
            continue
        full_path = getattr(entry, "full_path", "") or ""
        if not full_path:  # unallocated/corrupt record with no usable filename
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
