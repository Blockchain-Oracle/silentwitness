"""USN journal feeder — $UsnJrnl:$J change journal into :class:`IndexRecord` rows.

The USN journal records every file create / delete / rename / data-extend on the volume
with a timestamp and reason flags — the most direct answer to "what was staged,
exfiltrated, or deleted, and when" (a deleted staging archive leaves no $MFT entry but a
``FILE_DELETE`` USN record). The on-disk format (USN_RECORD_V2) is a simple packed binary
struct, parsed here directly (no clean importable library exists; the struct is stable).

``_parse_usn_record``, ``_decode_reason`` and ``_filetime_to_iso`` are pure and
unit-tested; ``usnjrnl_records`` streams a real ``$J`` (forensics box). The ``$J`` is a
multi-GB sparse file, so it is ``mmap``-ed and its long zero runs are skipped a block at
a time (validated: 4 GB / ~384K records in ~13 s).
"""

from __future__ import annotations

import logging
import mmap
import struct
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from silentwitness_mcp.index._feeder_util import MAX_TEXT, Feeder, sha256_file
from silentwitness_mcp.index.store import IndexRecord

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class _UsnFields:
    """The fields lifted from one USN_RECORD_V2 (the rest of the struct is unused here)."""

    usn: int
    timestamp: int
    reason: int
    attributes: int
    name: str


# FILETIME epoch (100-ns intervals since 1601-01-01).
_FILETIME_EPOCH = datetime(1601, 1, 1, tzinfo=UTC)
# Smallest possible USN_RECORD_V2 (header through FileNameOffset) and a sane cap.
_MIN_RECORD = 0x3C
_MAX_RECORD = 0x10000
# The $J is a large sparse file (multi-GB of zero runs between records); skip zero
# regions a block at a time instead of 8 bytes, or the scan is O(filesize).
_ZERO_SKIP = 4096
# USN reason flags -> name, high-value first.
_REASONS: tuple[tuple[int, str], ...] = (
    (0x00000100, "FILE_CREATE"),
    (0x00000200, "FILE_DELETE"),
    (0x00001000, "RENAME_OLD_NAME"),
    (0x00002000, "RENAME_NEW_NAME"),
    (0x00000001, "DATA_OVERWRITE"),
    (0x00000002, "DATA_EXTEND"),
    (0x00000004, "DATA_TRUNCATION"),
    (0x00000800, "SECURITY_CHANGE"),
    (0x00040000, "ENCRYPTION_CHANGE"),
    (0x00100000, "REPARSE_POINT_CHANGE"),
    (0x00200000, "STREAM_CHANGE"),
    (0x80000000, "CLOSE"),
)


def _filetime_to_iso(filetime: int) -> str:
    """Windows FILETIME (100-ns since 1601) -> ISO-8601, or "" if zero/out-of-range."""
    if filetime <= 0:
        return ""
    try:
        return (_FILETIME_EPOCH + timedelta(microseconds=filetime / 10)).isoformat()
    except (OverflowError, ValueError):
        return ""


def _decode_reason(reason: int) -> str:
    """Join the set reason flag names (e.g. ``FILE_CREATE|DATA_EXTEND``)."""
    names = [name for bit, name in _REASONS if reason & bit]
    return "|".join(names) if names else f"0x{reason:08x}"


def _parse_usn_record(buf: bytes | mmap.mmap, offset: int) -> tuple[_UsnFields | None, int]:
    """Parse one USN_RECORD_V2 at ``offset``; return ``(fields | None, next_offset)``.

    Returns ``None`` fields for zero-padding / malformed regions, advancing 8 bytes so the
    scan resynchronises (records are 8-byte aligned). ``next_offset`` always advances so
    the caller's loop terminates."""
    if offset + 4 > len(buf):
        return None, len(buf)
    record_length = struct.unpack_from("<I", buf, offset)[0]
    if record_length == 0:
        return None, offset + 8  # sparse padding
    too_long = record_length > _MAX_RECORD or offset + record_length > len(buf)
    if record_length < _MIN_RECORD or too_long:
        return None, offset + 8  # bogus length -> resync
    if struct.unpack_from("<H", buf, offset + 4)[0] != 2:  # MajorVersion must be 2
        return None, offset + 8
    name_length = struct.unpack_from("<H", buf, offset + 0x38)[0]
    name_offset = struct.unpack_from("<H", buf, offset + 0x3A)[0]
    if name_offset < _MIN_RECORD or name_offset + name_length > record_length:
        return None, offset + record_length  # name span overlaps header / overflows -> skip
    fields = _UsnFields(
        usn=struct.unpack_from("<Q", buf, offset + 0x18)[0],
        timestamp=struct.unpack_from("<Q", buf, offset + 0x20)[0],
        reason=struct.unpack_from("<I", buf, offset + 0x28)[0],
        attributes=struct.unpack_from("<I", buf, offset + 0x34)[0],
        name=buf[offset + name_offset : offset + name_offset + name_length].decode(
            "utf-16-le", "replace"
        ),
    )
    return fields, offset + record_length


def _record_from_fields(
    fields: _UsnFields, *, cite: str, audit_id: str, host: str, sha256: str
) -> IndexRecord:
    """Build one searchable USN row."""
    text = (
        f"USN file={fields.name} reason={_decode_reason(fields.reason)} "
        f"attrs=0x{fields.attributes:08x}"
    )
    return IndexRecord(
        text=text[:MAX_TEXT],
        source_tool="usnjrnl",
        artifact_path=f"{cite}#{fields.usn}",
        host=host,
        ts=_filetime_to_iso(fields.timestamp),
        audit_id=audit_id,
        sha256=sha256,
    )


def usnjrnl_records(
    path: Path, *, audit_id: str, host: str = "", source_path: str | None = None
) -> Iterator[IndexRecord]:
    """Stream one :class:`IndexRecord` per USN_RECORD_V2 in a ``$UsnJrnl:$J`` file.

    The ``$J`` is multi-GB and mostly sparse, so it is ``mmap``-ed (not read into memory)
    and zero regions are skipped a block at a time."""
    cite = source_path if source_path is not None else str(path)
    sha = sha256_file(path)
    with path.open("rb") as handle:
        if handle.read(1) == b"":  # empty file -> nothing to parse
            return
        with mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as buf:
            size = len(buf)
            offset = 0
            yielded = 0
            resyncs = 0  # non-zero regions that failed to parse (potential desync)
            while offset < size:
                if buf[offset : offset + 4] == b"\x00\x00\x00\x00":
                    block = buf[offset : offset + _ZERO_SKIP]
                    offset += len(block) if block.count(0) == len(block) else 8
                    continue
                fields, offset = _parse_usn_record(buf, offset)
                if fields is None:
                    resyncs += 1
                    continue
                yielded += 1
                yield _record_from_fields(
                    fields, cite=cite, audit_id=audit_id, host=host, sha256=sha
                )
            # A large malformed-resync count relative to records signals a desync /
            # partial parse — surface it so a degraded $J doesn't read as a clean one.
            if resyncs > 100 and resyncs > yielded // 10:
                _LOG.warning(
                    "usnjrnl: %d malformed regions vs %d records in %s — possible desync",
                    resyncs,
                    yielded,
                    cite,
                )


# Compile-time assertion that the feeder still matches the shared contract.
_: Feeder = usnjrnl_records

__all__ = ["usnjrnl_records"]
