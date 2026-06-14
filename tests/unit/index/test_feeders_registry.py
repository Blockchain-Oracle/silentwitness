"""Unit tests for the registry-entry->IndexRecord mapping (no regipy / real hive needed).

The integration path (regipy running plugins over a real hive) is exercised on the
forensic box; here we pin the pure mapper that flattens one plugin entry into a
searchable, provenance-complete index row.
"""

from __future__ import annotations

from silentwitness_mcp.index.feeders_registry import _MAX_TEXT, _entry_to_record


def test_run_key_entry_maps_to_record() -> None:
    entry = {
        "name": "Updater",
        "value": "C:\\Users\\fred\\AppData\\Roaming\\evil.exe",
        "key": "\\Microsoft\\Windows\\CurrentVersion\\Run",
        "last_write": "2020-11-15T19:46:42+00:00",
    }
    rec = _entry_to_record(
        entry,
        plugin="ntuser_run",
        hive_path="img/hive/SOFTWARE",
        audit_id="sift-r-1",
        host="ROCBA",
    )
    assert rec is not None
    assert "name=Updater" in rec.text
    assert "evil.exe" in rec.text
    assert "CurrentVersion\\Run" in rec.text
    assert rec.source_tool == "regipy:ntuser_run"
    assert rec.ts == "2020-11-15T19:46:42+00:00"
    assert rec.artifact_path == "img/hive/SOFTWARE"
    assert rec.audit_id == "sift-r-1"
    assert rec.host == "ROCBA"


def test_nested_and_list_values_are_flattened() -> None:
    entry = {
        "service": "RemoteSvc",
        "config": {"Start": 2, "ImagePath": "svc.exe"},
        "tags": ["a", "b"],
    }
    rec = _entry_to_record(entry, plugin="services", hive_path="SYSTEM", audit_id="a", host="")
    assert rec is not None
    assert "service=RemoteSvc" in rec.text
    assert "ImagePath=svc.exe" in rec.text
    assert "Start=2" in rec.text
    assert "a" in rec.text and "b" in rec.text


def test_empty_entry_is_dropped() -> None:
    assert _entry_to_record({}, plugin="p", hive_path="h", audit_id="a", host="") is None


def test_timestamp_key_variants_are_picked_up() -> None:
    for key in ("timestamp", "last_modified", "last_write"):
        rec = _entry_to_record(
            {"x": "y", key: "2020-01-02T03:04:05+00:00"},
            plugin="p",
            hive_path="h",
            audit_id="a",
            host="",
        )
        assert rec is not None and rec.ts == "2020-01-02T03:04:05+00:00"


def test_long_entry_text_is_truncated() -> None:
    rec = _entry_to_record(
        {"blob": "z" * (_MAX_TEXT + 500)}, plugin="p", hive_path="h", audit_id="a", host=""
    )
    assert rec is not None and len(rec.text) == _MAX_TEXT
