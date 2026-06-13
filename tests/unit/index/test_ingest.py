"""Unit tests for the plaso->IndexRecord mapping (no plaso install needed)."""

from __future__ import annotations

from pathlib import Path

from silentwitness_mcp.index.ingest import (
    _MAX_TEXT,
    _iter_json_lines,
    _plaso_event_to_record,
)


def test_event_maps_to_record() -> None:
    event = {
        "message": "powershell.exe spawned by winword.exe",
        "parser": "winevtx",
        "display_name": "/Windows/System32/winevt/Logs/Security.evtx",
        "datetime": "2020-11-15T19:46:42.000000+00:00",
    }
    rec = _plaso_event_to_record(event, audit_id="sift-a-1", host="DC1")
    assert rec is not None
    assert rec.text == "powershell.exe spawned by winword.exe"
    assert rec.source_tool == "plaso:winevtx"
    assert rec.artifact_path == "/Windows/System32/winevt/Logs/Security.evtx"
    assert rec.ts == "2020-11-15T19:46:42.000000+00:00"
    assert rec.audit_id == "sift-a-1"
    assert rec.host == "DC1"


def test_event_without_message_is_dropped() -> None:
    assert _plaso_event_to_record({"parser": "winevtx"}, audit_id="a", host="") is None
    assert _plaso_event_to_record({"message": "   "}, audit_id="a", host="") is None


def test_missing_parser_defaults_to_unknown() -> None:
    rec = _plaso_event_to_record({"message": "x"}, audit_id="a", host="")
    assert rec is not None and rec.source_tool == "plaso:unknown"


def test_filename_fallback_when_no_display_name() -> None:
    rec = _plaso_event_to_record({"message": "x", "filename": "/p/SOFTWARE"}, audit_id="a", host="")
    assert rec is not None and rec.artifact_path == "/p/SOFTWARE"


def test_long_message_is_truncated() -> None:
    rec = _plaso_event_to_record({"message": "z" * (_MAX_TEXT + 500)}, audit_id="a", host="")
    assert rec is not None and len(rec.text) == _MAX_TEXT


def test_iter_json_lines_skips_junk(tmp_path: Path) -> None:
    f = tmp_path / "out.jsonl"
    f.write_text(
        '[\n{"message": "a"},\n{"message": "b"}\n]\nnot-json\n{"message": "c"}\n',
        encoding="utf-8",
    )
    msgs = [obj["message"] for obj in _iter_json_lines(f)]
    assert msgs == ["a", "b", "c"]
