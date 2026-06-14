"""Unit tests for the pure MFT mapper (no mft library / real $MFT needed)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from silentwitness_mcp.index._feeder_util import MAX_TEXT
from silentwitness_mcp.index.feeders_mft import (
    _entry_to_record,
    _modified_iso,
    _pick_std_info_modified,
)


@dataclass
class _Content:
    modified: object


def test_modified_iso_handles_datetime_and_none() -> None:
    dt = datetime(2020, 11, 14, 22, 10, 5, tzinfo=UTC)
    assert _modified_iso(dt) == "2020-11-14T22:10:05+00:00"
    assert _modified_iso(None) == ""
    assert _modified_iso("not-a-datetime") == ""  # no .isoformat -> ""


def test_pick_std_info_modified_selects_type16_among_others() -> None:
    dt = datetime(2020, 10, 29, 13, 26, 22, tzinfo=UTC)
    attrs = [
        (48, _Content(modified=datetime(1999, 1, 1, tzinfo=UTC))),  # X30 $FILE_NAME, ignored
        (16, _Content(modified=dt)),  # X10 $STANDARD_INFORMATION -> picked
    ]
    assert _pick_std_info_modified(attrs) == "2020-10-29T13:26:22+00:00"


def test_pick_std_info_modified_empty_when_absent_or_null() -> None:
    assert _pick_std_info_modified([]) == ""
    assert _pick_std_info_modified([(48, _Content(modified=None))]) == ""  # no X10 at all
    assert _pick_std_info_modified([(16, _Content(modified=None))]) == ""  # X10 but null ts


def test_mft_entry_is_searchable_and_provenanced() -> None:
    rec = _entry_to_record(
        full_path="Users/fred/Documents/Projects/Q4-merger-plan.docx",
        entry_id=123456,
        file_size=204800,
        flags="ALLOCATED | FILE",
        ts="2020-11-14T22:10:05+00:00",
        mft_path="img/mft/_MFT",
        audit_id="sift-m-1",
        host="ROCBA",
        sha256="d" * 64,
    )
    assert "MFT path=Users/fred/Documents/Projects/Q4-merger-plan.docx" in rec.text
    assert "size=204800" in rec.text
    assert "flags=ALLOCATED | FILE" in rec.text
    assert rec.source_tool == "mft"
    assert rec.artifact_path == "img/mft/_MFT#123456"
    assert rec.ts == "2020-11-14T22:10:05+00:00"
    assert rec.audit_id == "sift-m-1"
    assert rec.host == "ROCBA"
    assert rec.sha256 == "d" * 64


def test_mft_entry_text_is_truncated() -> None:
    rec = _entry_to_record(
        full_path="z" * (MAX_TEXT + 500),
        entry_id=1,
        file_size=0,
        flags="",
        ts="",
        mft_path="p",
        audit_id="a",
        host="",
        sha256="s",
    )
    assert len(rec.text) == MAX_TEXT
