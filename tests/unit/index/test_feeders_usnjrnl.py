"""Unit tests for the pure USN_RECORD_V2 parser (no real $J file needed)."""

from __future__ import annotations

import struct
from datetime import UTC, datetime

from silentwitness_mcp.index.feeders_usnjrnl import (
    _decode_reason,
    _filetime_to_iso,
    _parse_usn_record,
    _record_from_fields,
    _UsnFields,
)

_EPOCH = datetime(1601, 1, 1, tzinfo=UTC)


def _filetime(dt: datetime) -> int:
    return int((dt - _EPOCH).total_seconds() * 10_000_000)


def _pack_usn(*, usn: int, ft: int, reason: int, attrs: int, name: str) -> bytes:
    name_bytes = name.encode("utf-16-le")
    name_offset = 0x3C
    record_length = name_offset + len(name_bytes)
    record_length = (record_length + 7) & ~7  # 8-byte align
    buf = bytearray(record_length)
    struct.pack_into("<I", buf, 0x00, record_length)
    struct.pack_into("<H", buf, 0x04, 2)  # MajorVersion
    struct.pack_into("<Q", buf, 0x18, usn)
    struct.pack_into("<Q", buf, 0x20, ft)
    struct.pack_into("<I", buf, 0x28, reason)
    struct.pack_into("<I", buf, 0x34, attrs)
    struct.pack_into("<H", buf, 0x38, len(name_bytes))
    struct.pack_into("<H", buf, 0x3A, name_offset)
    buf[name_offset : name_offset + len(name_bytes)] = name_bytes
    return bytes(buf)


def test_filetime_decodes_to_iso() -> None:
    ft = _filetime(datetime(2020, 11, 14, 22, 10, 5, tzinfo=UTC))
    assert _filetime_to_iso(ft) == "2020-11-14T22:10:05+00:00"
    assert _filetime_to_iso(0) == ""
    assert _filetime_to_iso(-1) == ""


def test_decode_reason_flags() -> None:
    assert _decode_reason(0x00000100) == "FILE_CREATE"
    assert _decode_reason(0x00000102) == "FILE_CREATE|DATA_EXTEND"
    assert _decode_reason(0x00000200 | 0x80000000) == "FILE_DELETE|CLOSE"
    assert _decode_reason(0) == "0x00000000"


def test_parse_single_record() -> None:
    rec = _pack_usn(
        usn=99,
        ft=_filetime(datetime(2020, 11, 14, tzinfo=UTC)),
        reason=0x00000200,
        attrs=0x20,
        name="staged-secrets.7z",
    )
    fields, nxt = _parse_usn_record(rec, 0)
    assert fields is not None
    assert fields.name == "staged-secrets.7z"
    assert fields.usn == 99 and fields.reason == 0x00000200
    assert nxt == len(rec)


def test_zero_padding_advances_eight() -> None:
    fields, nxt = _parse_usn_record(b"\x00" * 64, 0)
    assert fields is None and nxt == 8


def test_bogus_length_resyncs() -> None:
    buf = struct.pack("<I", 0xFFFFFFFF) + b"\x00" * 60  # absurd record length
    fields, nxt = _parse_usn_record(buf, 0)
    assert fields is None and nxt == 8


def test_record_at_exact_end_of_buffer() -> None:
    # Header-only record (empty name) ending exactly at len(buf): every fixed-offset
    # field read (up to 0x3C) must stay in bounds with no trailing slack.
    rec = _pack_usn(usn=7, ft=0, reason=0x00000100, attrs=0, name="")
    assert rec[-4:] == b"\x00\x00\x00\x00"  # 8-byte alignment padding, still parseable
    fields, nxt = _parse_usn_record(rec, 0)
    assert fields is not None and fields.usn == 7 and nxt == len(rec)


def test_name_offset_overlapping_header_rejected() -> None:
    rec = bytearray(_pack_usn(usn=1, ft=0, reason=0, attrs=0, name="ok"))
    struct.pack_into("<H", rec, 0x3A, 0x10)  # name_offset inside the header -> reject
    fields, _ = _parse_usn_record(bytes(rec), 0)
    assert fields is None


def test_iterates_records_separated_by_padding() -> None:
    r1 = _pack_usn(
        usn=1,
        ft=_filetime(datetime(2020, 1, 1, tzinfo=UTC)),
        reason=0x00000100,
        attrs=0,
        name="a.txt",
    )
    r2 = _pack_usn(
        usn=2,
        ft=_filetime(datetime(2020, 1, 2, tzinfo=UTC)),
        reason=0x00000200,
        attrs=0,
        name="b.txt",
    )
    buf = r1 + b"\x00" * 16 + r2
    names: list[str] = []
    offset = 0
    while offset < len(buf):
        fields, offset = _parse_usn_record(buf, offset)
        if fields is not None:
            names.append(fields.name)
    assert names == ["a.txt", "b.txt"]


def test_record_from_fields_is_searchable() -> None:
    fields = _UsnFields(
        usn=42,
        timestamp=_filetime(datetime(2020, 11, 14, tzinfo=UTC)),
        reason=0x00000200,
        attributes=0x20,
        name="secrets.7z",
    )
    rec = _record_from_fields(
        fields, cite="usnjrnl/_UsnJrnl", audit_id="a", host="ROCBA", sha256="s"
    )
    assert "USN file=secrets.7z" in rec.text
    assert "FILE_DELETE" in rec.text
    assert rec.source_tool == "usnjrnl"
    assert rec.artifact_path == "usnjrnl/_UsnJrnl#42"
    assert rec.ts.startswith("2020-11-14")
    assert rec.host == "ROCBA"
