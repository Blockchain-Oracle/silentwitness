"""Unit tests for the EVTX-XML->IndexRecord mapping (no real .evtx / python-evtx needed).

The ROCBA EVTX files crash libevtx/pyevtx (and thus plaso's winevtx parser); the
reliable reader is pure-Python ``python-evtx``. These tests pin the pure mapper that
turns one rendered event into a searchable index row — the file-iteration path is
exercised against real EVTX on the forensic box.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from silentwitness_mcp.index import feeders_evtx
from silentwitness_mcp.index._feeder_util import MAX_TEXT, FeederStats
from silentwitness_mcp.index.feeders_evtx import _event_xml_to_record, evtx_file_records
from silentwitness_mcp.index.store import IndexRecord

_LOGON_4624 = """<?xml version="1.0" encoding="utf-8"?>
<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <Provider Name="Microsoft-Windows-Security-Auditing" Guid="{abc}"/>
    <EventID>4624</EventID>
    <TimeCreated SystemTime="2020-11-15T19:46:42.123456Z"/>
    <EventRecordID>987654</EventRecordID>
    <Channel>Security</Channel>
    <Computer>DESKTOP-ROCBA</Computer>
  </System>
  <EventData>
    <Data Name="TargetUserName">fred.rocba</Data>
    <Data Name="LogonType">10</Data>
    <Data Name="IpAddress">10.0.0.5</Data>
  </EventData>
</Event>"""


def test_logon_event_maps_to_record() -> None:
    rec = _event_xml_to_record(
        _LOGON_4624,
        source_path="/Windows/System32/winevt/Logs/Security.evtx",
        sha256="a" * 64,
        audit_id="sift-e-1",
        host="ROCBA",
    )
    assert rec is not None
    # The salient fields are all FTS-searchable in one compact line.
    assert "EventID=4624" in rec.text
    assert "Security" in rec.text
    assert "fred.rocba" in rec.text
    assert "10.0.0.5" in rec.text
    assert "LogonType=10" in rec.text
    assert rec.ts == "2020-11-15T19:46:42.123456Z"
    assert rec.source_tool == "evtx:Security"
    # Stable per-event citation locator: file path + EventRecordID.
    assert rec.artifact_path == "/Windows/System32/winevt/Logs/Security.evtx#987654"
    assert rec.audit_id == "sift-e-1"
    assert rec.host == "ROCBA"
    assert rec.sha256 == "a" * 64


def test_event_without_eventid_is_dropped() -> None:
    xml = (
        '<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">'
        "<System><Channel>Security</Channel></System></Event>"
    )
    assert _event_xml_to_record(xml, source_path="p", sha256="s", audit_id="a", host="") is None


def test_malformed_xml_is_dropped() -> None:
    out = _event_xml_to_record("<not-xml", source_path="p", sha256="s", audit_id="a", host="")
    assert out is None


def test_namespaceless_event_still_parses() -> None:
    xml = "<Event><System><EventID>7045</EventID><Channel>System</Channel></System></Event>"
    rec = _event_xml_to_record(xml, source_path="p", sha256="s", audit_id="a", host="")
    assert rec is not None and "EventID=7045" in rec.text and rec.source_tool == "evtx:System"


def test_long_text_is_truncated() -> None:
    big = "<Data Name='Blob'>" + "z" * (MAX_TEXT + 500) + "</Data>"
    xml = (
        "<Event><System><EventID>1</EventID><Channel>App</Channel></System>"
        f"<EventData>{big}</EventData></Event>"
    )
    rec = _event_xml_to_record(xml, source_path="p", sha256="s", audit_id="a", host="")
    assert rec is not None and len(rec.text) == MAX_TEXT


def test_rust_failure_is_recorded_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    f = tmp_path / "Security.evtx"
    f.write_bytes(b"evtx-bytes")  # content irrelevant; readers are monkeypatched

    def boom(path: Path, **_: object) -> Iterator[IndexRecord]:
        raise RuntimeError("Failed to parse chunk header")
        yield  # pragma: no cover - makes this a generator

    def py_fallback(path: Path, **_: object) -> Iterator[IndexRecord]:
        raise AssertionError("fallback requires SILENTWITNESS_EVTX_TOLERANT_FALLBACK=1")
        yield  # pragma: no cover

    monkeypatch.setattr(feeders_evtx, "_rust_evtx_records", boom)
    monkeypatch.setattr(feeders_evtx, "_python_evtx_records", py_fallback)
    stats = FeederStats()
    with pytest.raises(RuntimeError, match="tolerant python-evtx fallback disabled"):
        list(evtx_file_records(f, audit_id="a", host="", stats=stats))
    assert stats.skipped == {"evtx_rust_failed_file": 1}


def test_rust_failure_falls_back_to_python_evtx_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    f = tmp_path / "Security.evtx"
    f.write_bytes(b"evtx-bytes")

    def boom(path: Path, **_: object) -> Iterator[IndexRecord]:
        raise RuntimeError("Failed to parse chunk header")
        yield  # pragma: no cover - makes this a generator

    def py_fallback(path: Path, **_: object) -> Iterator[IndexRecord]:
        yield IndexRecord(text="from python-evtx", source_tool="evtx:Security", audit_id="a")

    monkeypatch.setenv("SILENTWITNESS_EVTX_TOLERANT_FALLBACK", "1")
    monkeypatch.setattr(feeders_evtx, "_rust_evtx_records", boom)
    monkeypatch.setattr(feeders_evtx, "_python_evtx_records", py_fallback)
    stats = FeederStats()
    out = list(evtx_file_records(f, audit_id="a", host="", stats=stats))
    assert len(out) == 1 and out[0].text == "from python-evtx"
    assert stats.skipped == {"evtx_rust_failed_file": 1, "evtx_python_fallback_file": 1}


def test_rust_success_does_not_invoke_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    f = tmp_path / "System.evtx"
    f.write_bytes(b"evtx-bytes")

    def rust_ok(path: Path, **_: object) -> Iterator[IndexRecord]:
        yield IndexRecord(text="from rust", source_tool="evtx:System", audit_id="a")

    def fallback_must_not_run(path: Path, **_: object) -> Iterator[IndexRecord]:
        raise AssertionError("python-evtx fallback must not run when rust succeeds")

    monkeypatch.setattr(feeders_evtx, "_rust_evtx_records", rust_ok)
    monkeypatch.setattr(feeders_evtx, "_python_evtx_records", fallback_must_not_run)
    out = list(evtx_file_records(f, audit_id="a", host=""))
    assert len(out) == 1 and out[0].text == "from rust"


def test_rust_importerror_is_reraised_not_masked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A missing Rust parser is an environment defect — surface it, don't silently
    # degrade to the slow fallback (which would mask a broken install).
    f = tmp_path / "x.evtx"
    f.write_bytes(b"evtx-bytes")

    def missing(path: Path, **_: object) -> Iterator[IndexRecord]:
        raise ImportError("No module named 'evtx'")
        yield  # pragma: no cover

    def fallback_must_not_run(path: Path, **_: object) -> Iterator[IndexRecord]:
        raise AssertionError("fallback must not run on ImportError")

    monkeypatch.setattr(feeders_evtx, "_rust_evtx_records", missing)
    monkeypatch.setattr(feeders_evtx, "_python_evtx_records", fallback_must_not_run)
    with pytest.raises(ImportError):
        list(evtx_file_records(f, audit_id="a", host=""))
