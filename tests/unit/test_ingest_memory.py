"""Unit tests for ingest_memory mappers (pure functions, no vol3 subprocess).

Driver tests use monkeypatching to stub :func:`subprocess.run` so they validate the
wiring (JSON parse, failure capture, bulk_ingest) without needing a real memory image.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from silentwitness_mcp.index import ingest_memory as im
from silentwitness_mcp.index.store import EvidenceIndex, IndexRecord

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "vol3"


def _load(name: str) -> list[dict[str, Any]]:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# pslist
# ---------------------------------------------------------------------------


def test_pslist_real_fixture_produces_rows_with_create_time_as_ts() -> None:
    rows = list(
        im._pslist_to_records(
            _load("pslist.json"),
            artifact_path="memory/Rocba.raw",
            audit_id="A1",
            host="DESKTOP",
            sha256="abc",
        )
    )
    assert len(rows) == 5
    first = rows[0]
    assert first.source_tool == "vol:pslist"
    assert first.artifact_path == "memory/Rocba.raw#vol:pslist"
    assert first.text.startswith("Process pid=4 ppid=0 name=System")
    assert first.ts.startswith("2020-")  # CreateTime preserved


def test_pslist_skips_none_columns_in_text() -> None:
    rows = list(
        im._pslist_to_records(
            [{"PID": 100, "PPID": None, "ImageFileName": "x.exe", "Threads": 1}],
            artifact_path="m.raw",
            audit_id="A",
            host="",
            sha256="s",
        )
    )
    assert "ppid=" not in rows[0].text
    assert "pid=100" in rows[0].text


# ---------------------------------------------------------------------------
# cmdline
# ---------------------------------------------------------------------------


def test_cmdline_skips_rows_without_args_keeps_rest() -> None:
    fixture = _load("cmdline.json")
    rows = list(
        im._cmdline_to_records(
            fixture,
            artifact_path="m.raw",
            audit_id="A",
            host="",
            sha256="s",
        )
    )
    # Kept rows == fixture rows with non-null Args.
    expected = sum(1 for r in fixture if r.get("Args"))
    assert len(rows) == expected
    assert all("args=" in r.text for r in rows)
    assert all(r.source_tool == "vol:cmdline" for r in rows)


def test_cmdline_emits_row_with_args() -> None:
    rows = list(
        im._cmdline_to_records(
            [{"PID": 1234, "Process": "powershell.exe", "Args": "-EncodedCommand AAA"}],
            artifact_path="m.raw",
            audit_id="A",
            host="",
            sha256="s",
        )
    )
    assert len(rows) == 1
    assert rows[0].source_tool == "vol:cmdline"
    assert rows[0].ts == ""
    assert "EncodedCommand" in rows[0].text


# ---------------------------------------------------------------------------
# netscan / malfind / psscan — synthetic rows (real fixtures pending scanner runs)
# ---------------------------------------------------------------------------


def test_netscan_formats_local_and_foreign_endpoints() -> None:
    rows = list(
        im._netscan_to_records(
            [
                {
                    "Proto": "TCPv4",
                    "LocalAddr": "10.0.0.5",
                    "LocalPort": 49152,
                    "ForeignAddr": "1.2.3.4",
                    "ForeignPort": 443,
                    "State": "ESTABLISHED",
                    "PID": 4444,
                    "Owner": "chrome.exe",
                    "Created": "2020-11-15T20:00:00+00:00",
                }
            ],
            artifact_path="m.raw",
            audit_id="A",
            host="H",
            sha256="s",
        )
    )
    assert rows[0].text == (
        "NetConn proto=TCPv4 local=10.0.0.5:49152 foreign=1.2.3.4:443 "
        "state=ESTABLISHED pid=4444 owner=chrome.exe"
    )
    assert rows[0].ts == "2020-11-15T20:00:00+00:00"


def test_malfind_emits_one_row_per_hit() -> None:
    rows = list(
        im._malfind_to_records(
            [
                {
                    "PID": 9999,
                    "Process": "explorer.exe",
                    "Start VPN": "0x1000000",
                    "End VPN": "0x100ffff",
                    "Tag": "VadS",
                    "Protection": "PAGE_EXECUTE_READWRITE",
                }
            ],
            artifact_path="m.raw",
            audit_id="A",
            host="",
            sha256="s",
        )
    )
    assert rows[0].source_tool == "vol:malfind"
    assert "PAGE_EXECUTE_READWRITE" in rows[0].text


def test_psscan_separate_from_pslist() -> None:
    rows = list(
        im._psscan_to_records(
            [{"PID": 50, "PPID": 4, "ImageFileName": "ghost.exe"}],
            artifact_path="m.raw",
            audit_id="A",
            host="",
            sha256="s",
        )
    )
    assert rows[0].source_tool == "vol:psscan"
    assert rows[0].text.startswith("ProcessScan")


# ---------------------------------------------------------------------------
# Driver — subprocess stubbed
# ---------------------------------------------------------------------------


class _FakeCompleted:
    def __init__(self, stdout: bytes) -> None:
        self.stdout = stdout
        self.returncode = 0


def test_driver_missing_vol_binary_returns_driver_failure(tmp_path: Path) -> None:
    image = tmp_path / "mem.raw"
    image.write_bytes(b"x")
    with EvidenceIndex(tmp_path / "idx.db") as idx:
        idx.begin_bulk()
        result = im.ingest_memory_image(
            image,
            idx,
            audit_id="A",
            vol_bin="/nonexistent/vol",
        )
    assert result.counts == {}
    assert result.failures == [("__driver__", "vol3 binary not found at /nonexistent/vol")]


def test_driver_runs_each_plugin_and_counts_rows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = tmp_path / "mem.raw"
    image.write_bytes(b"hello-world-as-image")

    plugin_outputs = {
        "windows.pslist.PsList": [
            {
                "PID": 4,
                "PPID": 0,
                "ImageFileName": "System",
                "CreateTime": "2020-11-11T08:13:00+00:00",
            }
        ],
        "windows.cmdline.CmdLine": [{"PID": 100, "Process": "x.exe", "Args": "-flag"}],
    }

    def fake_run(cmd: list[str], **_: object) -> _FakeCompleted:
        plugin = cmd[-1]
        return _FakeCompleted(json.dumps(plugin_outputs.get(plugin, [])).encode())

    monkeypatch.setattr(im.subprocess, "run", fake_run)
    monkeypatch.setattr(im.shutil, "which", lambda _: "/fake/vol")

    with EvidenceIndex(tmp_path / "idx.db") as idx:
        idx.begin_bulk()
        result = im.ingest_memory_image(
            image,
            idx,
            audit_id="A",
            host="H",
            plugins=("windows.pslist.PsList", "windows.cmdline.CmdLine"),
            vol_bin="/fake/vol",
        )
    assert result.counts == {"pslist": 1, "cmdline": 1}
    assert result.failures == []
    assert result.image_sha256  # hashed once


def test_driver_records_plugin_timeout_as_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = tmp_path / "mem.raw"
    image.write_bytes(b"x")

    def boom(cmd: list[str], **_: object) -> _FakeCompleted:
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=1)

    monkeypatch.setattr(im.subprocess, "run", boom)
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
    assert result.counts == {}
    assert len(result.failures) == 1
    assert result.failures[0][0] == "windows.pslist.PsList"


def test_driver_records_malformed_json_as_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = tmp_path / "mem.raw"
    image.write_bytes(b"x")
    monkeypatch.setattr(im.subprocess, "run", lambda *_a, **_k: _FakeCompleted(b"not-json{{{"))
    monkeypatch.setattr(im.shutil, "which", lambda _: "/fake/vol")

    with EvidenceIndex(tmp_path / "idx.db") as idx:
        idx.begin_bulk()
        result = im.ingest_memory_image(
            image, idx, audit_id="A", plugins=("windows.pslist.PsList",), vol_bin="/fake/vol"
        )
    assert "windows.pslist.PsList" in [p for p, _ in result.failures]


def test_driver_unknown_plugin_records_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = tmp_path / "mem.raw"
    image.write_bytes(b"x")
    monkeypatch.setattr(im.shutil, "which", lambda _: "/fake/vol")
    with EvidenceIndex(tmp_path / "idx.db") as idx:
        idx.begin_bulk()
        result = im.ingest_memory_image(
            image, idx, audit_id="A", plugins=("windows.unknown.Foo",), vol_bin="/fake/vol"
        )
    assert result.failures == [("windows.unknown.Foo", "no mapper registered")]


def test_make_record_truncates_at_max_text() -> None:
    # 20_000-char text should be capped at MAX_TEXT.
    from silentwitness_mcp.index._feeder_util import MAX_TEXT

    huge = "x" * 20_000
    rows = list(
        im._malfind_to_records(
            [{"PID": 1, "Process": "p", "Protection": huge}],
            artifact_path="m",
            audit_id="A",
            host="",
            sha256="s",
        )
    )
    assert len(rows[0].text) == MAX_TEXT


def test_artifact_path_carries_plugin_fragment() -> None:
    rows = list(
        im._pslist_to_records(
            [{"PID": 4, "PPID": 0, "ImageFileName": "x"}],
            artifact_path="memory/Rocba.raw",
            audit_id="A",
            host="",
            sha256="s",
        )
    )
    assert rows[0].artifact_path == "memory/Rocba.raw#vol:pslist"


def test_index_record_actually_inserts_via_bulk(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """End-to-end inside the test process — fake vol3, real SQLite + FTS."""
    image = tmp_path / "m.raw"
    image.write_bytes(b"x")
    monkeypatch.setattr(
        im.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(
            json.dumps(
                [
                    {
                        "PID": 4,
                        "PPID": 0,
                        "ImageFileName": "System",
                        "CreateTime": "2020-11-11T08:13:00+00:00",
                    }
                ]
            ).encode()
        ),
    )
    monkeypatch.setattr(im.shutil, "which", lambda _: "/fake/vol")

    db = tmp_path / "idx.db"
    with EvidenceIndex(db) as idx:
        idx.begin_bulk()
        im.ingest_memory_image(
            image, idx, audit_id="A1", plugins=("windows.pslist.PsList",), vol_bin="/fake/vol"
        )
        idx.rebuild_fts()
        # Round-trip: search the FTS for "System" -> our row.
        hits = list(idx.search("System", limit=10))
    assert any(isinstance(h, IndexRecord) and h.source_tool == "vol:pslist" for h in hits)
