"""Timeout and progress behavior for the Volatility memory ingest driver."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from silentwitness_mcp.index import ingest_memory as im
from silentwitness_mcp.index.store import EvidenceIndex


class _FakeCompleted:
    def __init__(self, stdout: bytes) -> None:
        self.stdout = stdout
        self.returncode = 0


def test_driver_uses_default_timeout_for_each_plugin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = tmp_path / "mem.raw"
    image.write_bytes(b"x")
    timeouts: list[object] = []

    def fake_run(_cmd: list[str], **kwargs: object) -> _FakeCompleted:
        timeouts.append(kwargs["timeout"])
        return _FakeCompleted(json.dumps([]).encode())

    monkeypatch.delenv("SILENTWITNESS_VOL3_TIMEOUT_SEC", raising=False)
    monkeypatch.delenv("SILENTWITNESS_VOL3_TIMEOUT_PSLIST_SEC", raising=False)
    monkeypatch.setattr(im.subprocess, "run", fake_run)
    monkeypatch.setattr(im.shutil, "which", lambda _: "/fake/vol")
    with EvidenceIndex(tmp_path / "idx.db") as idx:
        idx.begin_bulk()
        result = im.ingest_memory_image(
            image,
            idx,
            audit_id="A",
            plugins=("windows.pslist.PsList",),
            vol_bin="/fake/vol",
        )
    assert result.failures == []
    assert timeouts == [300.0]


def test_driver_allows_plugin_specific_timeout_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = tmp_path / "mem.raw"
    image.write_bytes(b"x")
    timeouts: list[object] = []

    def fake_run(cmd: list[str], **kwargs: object) -> _FakeCompleted:
        timeouts.append((cmd[-1], kwargs["timeout"]))
        return _FakeCompleted(json.dumps([]).encode())

    monkeypatch.setenv("SILENTWITNESS_VOL3_TIMEOUT_SEC", "120")
    monkeypatch.setenv("SILENTWITNESS_VOL3_TIMEOUT_MALFIND_SEC", "15")
    monkeypatch.setattr(im.subprocess, "run", fake_run)
    monkeypatch.setattr(im.shutil, "which", lambda _: "/fake/vol")
    with EvidenceIndex(tmp_path / "idx.db") as idx:
        idx.begin_bulk()
        result = im.ingest_memory_image(
            image,
            idx,
            audit_id="A",
            plugins=("windows.pslist.PsList", "windows.malware.malfind.Malfind"),
            vol_bin="/fake/vol",
        )
    assert result.failures == []
    assert timeouts == [
        ("windows.pslist.PsList", 120.0),
        ("windows.malware.malfind.Malfind", 15.0),
    ]


def test_driver_timeout_zero_disables_plugin_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = tmp_path / "mem.raw"
    image.write_bytes(b"x")
    timeouts: list[object] = []

    def fake_run(_cmd: list[str], **kwargs: object) -> _FakeCompleted:
        timeouts.append(kwargs["timeout"])
        return _FakeCompleted(json.dumps([]).encode())

    monkeypatch.setenv("SILENTWITNESS_VOL3_TIMEOUT_PSLIST_SEC", "0")
    monkeypatch.setattr(im.subprocess, "run", fake_run)
    monkeypatch.setattr(im.shutil, "which", lambda _: "/fake/vol")
    with EvidenceIndex(tmp_path / "idx.db") as idx:
        idx.begin_bulk()
        result = im.ingest_memory_image(
            image,
            idx,
            audit_id="A",
            plugins=("windows.pslist.PsList",),
            vol_bin="/fake/vol",
        )
    assert result.failures == []
    assert timeouts == [None]


def test_driver_emits_plugin_progress_events(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = tmp_path / "mem.raw"
    image.write_bytes(b"x")
    events: list[im.MemoryPluginEvent] = []

    def fake_run(_cmd: list[str], **_: object) -> _FakeCompleted:
        return _FakeCompleted(
            json.dumps([{"PID": 1, "PPID": 0, "ImageFileName": "System"}]).encode()
        )

    monkeypatch.setattr(im.subprocess, "run", fake_run)
    monkeypatch.setattr(im.shutil, "which", lambda _: "/fake/vol")
    with EvidenceIndex(tmp_path / "idx.db") as idx:
        idx.begin_bulk()
        result = im.ingest_memory_image(
            image,
            idx,
            audit_id="A",
            plugins=("windows.pslist.PsList",),
            vol_bin="/fake/vol",
            progress=events.append,
        )
    assert result.counts == {"pslist": 1}
    assert [(event.status, event.short_name) for event in events] == [
        ("start", "pslist"),
        ("ok", "pslist"),
    ]
    assert events[0].timeout_seconds == 300.0
    assert events[1].rows == 1
