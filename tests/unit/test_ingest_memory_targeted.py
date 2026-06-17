"""Targeted malfind behavior for the Volatility memory ingest driver."""

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


def test_targeted_malfind_passes_selected_pid_args(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = tmp_path / "mem.raw"
    image.write_bytes(b"x")
    commands: list[list[str]] = []

    def fake_run(cmd: list[str], **_: object) -> _FakeCompleted:
        commands.append(cmd)
        plugin = cmd[cmd.index("-f") + 2]
        rows = {
            "windows.pslist.PsList": [
                {"PID": 100, "ImageFileName": "chrome.exe"},
                {"PID": 200, "ImageFileName": "powershell.exe"},
            ],
            "windows.cmdline.CmdLine": [
                {"PID": 200, "Process": "powershell.exe", "Args": "-enc abc"}
            ],
            "windows.netscan.NetScan": [{"PID": 100, "Owner": "chrome.exe"}],
            "windows.psscan.PsScan": [{"PID": 400, "ImageFileName": "hidden.exe"}],
            "windows.malware.malfind.Malfind": [],
        }[plugin]
        return _FakeCompleted(json.dumps(rows).encode())

    monkeypatch.setattr(im.subprocess, "run", fake_run)
    monkeypatch.setattr(im.shutil, "which", lambda _: "/fake/vol")

    with EvidenceIndex(tmp_path / "idx.db") as idx:
        idx.begin_bulk()
        result = im.ingest_memory_image(
            image,
            idx,
            audit_id="A",
            plugins=(
                "windows.pslist.PsList",
                "windows.cmdline.CmdLine",
                "windows.netscan.NetScan",
                "windows.psscan.PsScan",
                "windows.malware.malfind.Malfind",
            ),
            vol_bin="/fake/vol",
            targeted_malfind=True,
        )

    assert result.failures == []
    assert commands[-1][-5:] == [
        "windows.malware.malfind.Malfind",
        "--pid",
        "100",
        "200",
        "400",
    ]


def test_targeted_malfind_skips_when_no_candidate_pids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = tmp_path / "mem.raw"
    image.write_bytes(b"x")
    events: list[im.MemoryPluginEvent] = []

    def fake_run(_cmd: list[str], **_: object) -> _FakeCompleted:
        raise AssertionError("malfind should not run without selected PIDs")

    monkeypatch.setattr(im.subprocess, "run", fake_run)
    monkeypatch.setattr(im.shutil, "which", lambda _: "/fake/vol")

    with EvidenceIndex(tmp_path / "idx.db") as idx:
        idx.begin_bulk()
        result = im.ingest_memory_image(
            image,
            idx,
            audit_id="A",
            plugins=("windows.malware.malfind.Malfind",),
            vol_bin="/fake/vol",
            progress=events.append,
            targeted_malfind=True,
        )

    assert result.counts == {"malfind": 0}
    assert result.failures == []
    assert [(event.status, event.short_name) for event in events] == [("skipped", "malfind")]
