"""Unit tests for the pure SRUM mappers (no pyesedb / real SRUDB.dat needed)."""

from __future__ import annotations

import struct

from silentwitness_mcp.index._feeder_util import MAX_TEXT
from silentwitness_mcp.index.feeders_srum import (
    _appid_map_from_rows,
    _decode_idblob,
    _net_row_to_record,
    _ole_to_iso,
)


def test_ole_date_decodes_to_exact_timestamp() -> None:
    # 44000 days after 1899-12-30 is a fixed point — pin it exactly, not just "2020".
    assert _ole_to_iso(struct.pack("<d", 44000.0)) == "2020-06-18T00:00:00+00:00"


def test_ole_date_rejects_garbage() -> None:
    assert _ole_to_iso(None) == ""
    assert _ole_to_iso(b"\x00\x00") == ""  # too short
    assert _ole_to_iso(struct.pack("<d", 0.0)) == ""  # 0 days -> unusable
    assert _ole_to_iso(struct.pack("<d", 1e9)) == ""  # absurdly far future -> rejected
    assert _ole_to_iso(struct.pack("<d", float("nan"))) == ""
    assert _ole_to_iso(struct.pack("<d", float("inf"))) == ""


def test_ole_date_boundary() -> None:
    assert _ole_to_iso(struct.pack("<d", 400_001.0)) == ""  # past cutoff -> rejected
    assert _ole_to_iso(struct.pack("<d", 399_999.0)) != ""  # within cutoff -> accepted


def test_decode_idblob_utf16_and_hex_fallback() -> None:
    assert _decode_idblob("Dropbox.exe\x00".encode("utf-16-le")) == "Dropbox.exe"
    # An odd-length / non-UTF16 blob can't decode -> hex fallback (never raises).
    assert _decode_idblob(b"\xff\xfe\xfa") == "fffefa"


def test_appid_map_skips_null_index_and_blob() -> None:
    rows = [
        (3, "lsass.exe\x00".encode("utf-16-le")),
        (None, "x\x00".encode("utf-16-le")),  # null index -> skipped
        (5, None),  # null blob -> skipped
    ]
    assert _appid_map_from_rows(rows) == {3: "lsass.exe"}


def test_net_row_is_searchable_and_provenanced() -> None:
    rec = _net_row_to_record(
        app="C:\\Users\\fred\\Dropbox\\Dropbox.exe",
        bytes_sent=10_485_760,
        bytes_recvd=2048,
        interface_luid=1689399632855040,
        ts="2020-11-15T19:46:42+00:00",
        srudb_path="img/srum/SRUDB.dat",
        record_index=42,
        audit_id="sift-s-1",
        host="ROCBA",
        sha256="c" * 64,
    )
    assert "SRUM network_usage" in rec.text
    assert "Dropbox.exe" in rec.text
    assert "bytes_sent=10485760" in rec.text
    assert rec.source_tool == "srum:network_usage"
    assert rec.artifact_path == "img/srum/SRUDB.dat#42"
    assert rec.ts == "2020-11-15T19:46:42+00:00"
    assert rec.audit_id == "sift-s-1"
    assert rec.host == "ROCBA"
    assert rec.sha256 == "c" * 64


def test_net_row_text_is_truncated() -> None:
    rec = _net_row_to_record(
        app="z" * (MAX_TEXT + 500),
        bytes_sent=0,
        bytes_recvd=0,
        interface_luid=0,
        ts="",
        srudb_path="p",
        record_index=0,
        audit_id="a",
        host="",
        sha256="s",
    )
    assert len(rec.text) == MAX_TEXT
