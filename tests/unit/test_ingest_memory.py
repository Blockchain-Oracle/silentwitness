"""Unit tests for the vol3 driver — subprocess wiring + bulk-ingest + failure capture.

Driver tests monkeypatch :func:`subprocess.run` so they validate the wiring (JSON
parse, failure capture, bulk_ingest) without needing a real memory image. Pure-mapper
tests live in :file:`tests/unit/test_feeders_memory.py`.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from silentwitness_mcp.index import ingest_memory as im
from silentwitness_mcp.index.store import EvidenceIndex, IndexRecord


class _FakeCompleted:
    def __init__(self, stdout: bytes) -> None:
        self.stdout = stdout
        self.returncode = 0


# ---------------------------------------------------------------------------
# Vol-binary absence / image hashing
# ---------------------------------------------------------------------------


def test_driver_missing_vol_binary_returns_driver_failure(tmp_path: Path) -> None:
    image = tmp_path / "mem.raw"
    image.write_bytes(b"x")
    with EvidenceIndex(tmp_path / "idx.db") as idx:
        idx.begin_bulk()
        result = im.ingest_memory_image(image, idx, audit_id="A", vol_bin="/nonexistent/vol")
    assert result.counts == {}
    assert result.failures == [("__driver__", "vol3 binary not found at /nonexistent/vol")]
    # Hashing happens BEFORE the vol3-binary check so provenance lands even on driver
    # abort — image_sha256 must be the actual hash, not the empty-string sentinel.
    assert result.image_sha256 and result.image_sha256 != ""


# ---------------------------------------------------------------------------
# Happy path + per-plugin counts
# ---------------------------------------------------------------------------


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
    assert result.image_sha256


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
        hits = list(idx.search("System", limit=10))
    assert any(isinstance(h, IndexRecord) and h.source_tool == "vol:pslist" for h in hits)


# ---------------------------------------------------------------------------
# Per-plugin failure capture (no silent drops)
# ---------------------------------------------------------------------------


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
    assert "timed out after 300s" in result.failures[0][1]


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
            image,
            idx,
            audit_id="A",
            plugins=("windows.pslist.PsList",),
            vol_bin="/fake/vol",
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
            image,
            idx,
            audit_id="A",
            plugins=("windows.unknown.Foo",),
            vol_bin="/fake/vol",
        )
    assert result.failures == [("windows.unknown.Foo", "no mapper registered")]


def test_driver_empty_stdout_becomes_explicit_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Vol3 exit-0-with-no-output (observed on ROCBA Malfind) must surface as a real
    failure — NOT as a misleading "0 rows" success."""
    image = tmp_path / "m.raw"
    image.write_bytes(b"x")
    monkeypatch.setattr(im.subprocess, "run", lambda *_a, **_k: _FakeCompleted(b"   \n  "))
    monkeypatch.setattr(im.shutil, "which", lambda _: "/fake/vol")
    with EvidenceIndex(tmp_path / "idx.db") as idx:
        idx.begin_bulk()
        result = im.ingest_memory_image(
            image,
            idx,
            audit_id="A",
            plugins=("windows.malware.malfind.Malfind",),
            vol_bin="/fake/vol",
        )
    assert result.counts == {}
    assert len(result.failures) == 1
    assert "empty output" in result.failures[0][1]


def test_driver_handles_renderer_wrapped_rows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Some vol3 versions wrap output as {"renderer":"json","rows":[...]} — the
    driver must unwrap, not treat it as a non-list failure."""
    image = tmp_path / "m.raw"
    image.write_bytes(b"x")
    payload = json.dumps(
        {
            "renderer": "json",
            "columns": ["PID", "PPID", "ImageFileName"],
            "rows": [{"PID": 4, "PPID": 0, "ImageFileName": "System"}],
        }
    ).encode()
    monkeypatch.setattr(im.subprocess, "run", lambda *_a, **_k: _FakeCompleted(payload))
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
    assert result.counts == {"pslist": 1}
    assert result.failures == []


def test_driver_called_process_error_folds_stderr_into_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`str(CalledProcessError)` alone drops vol3's stderr — the operator needs it."""
    image = tmp_path / "m.raw"
    image.write_bytes(b"x")

    def boom(cmd: list[str], **_: object) -> _FakeCompleted:
        raise subprocess.CalledProcessError(
            returncode=1, cmd=cmd, output=b"", stderr=b"symbol lookup failed: ntkrnlmp"
        )

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
    assert len(result.failures) == 1
    assert "symbol lookup failed" in result.failures[0][1]


def test_driver_bulk_ingest_sqlite_error_recorded_as_plugin_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An SQLite write failure must land in `failures` — not abort the whole pass."""
    import sqlite3

    image = tmp_path / "m.raw"
    image.write_bytes(b"x")
    monkeypatch.setattr(
        im.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(
            json.dumps([{"PID": 1, "PPID": 0, "ImageFileName": "x"}]).encode()
        ),
    )
    monkeypatch.setattr(im.shutil, "which", lambda _: "/fake/vol")

    class _BrokenIndex:
        def bulk_ingest(self, _records: object) -> int:
            raise sqlite3.OperationalError("disk I/O error")

    result = im.ingest_memory_image(
        image,
        _BrokenIndex(),  # type: ignore[arg-type]
        audit_id="A",
        plugins=("windows.pslist.PsList",),
        vol_bin="/fake/vol",
    )
    assert result.counts == {}
    assert len(result.failures) == 1
    assert "bulk_ingest" in result.failures[0][1]


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


def test_artifact_path_defaults_to_image_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = tmp_path / "Rocba-Memory.raw"
    image.write_bytes(b"x")
    monkeypatch.setattr(
        im.subprocess,
        "run",
        lambda *_a, **_k: _FakeCompleted(
            json.dumps([{"PID": 1, "PPID": 0, "ImageFileName": "x"}]).encode()
        ),
    )
    monkeypatch.setattr(im.shutil, "which", lambda _: "/fake/vol")
    with EvidenceIndex(tmp_path / "idx.db") as idx:
        idx.begin_bulk()
        im.ingest_memory_image(
            image, idx, audit_id="A", plugins=("windows.pslist.PsList",), vol_bin="/fake/vol"
        )
        idx.rebuild_fts()
        hits = list(idx.search("x", limit=10))
    assert any(h.artifact_path == "Rocba-Memory.raw#vol:pslist" for h in hits)


def test_empty_plugin_tuple_is_noop_with_hash(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = tmp_path / "m.raw"
    image.write_bytes(b"x" * 4096)
    monkeypatch.setattr(im.shutil, "which", lambda _: "/fake/vol")
    with EvidenceIndex(tmp_path / "idx.db") as idx:
        idx.begin_bulk()
        result = im.ingest_memory_image(image, idx, audit_id="A", plugins=(), vol_bin="/fake/vol")
    assert result.counts == {}
    assert result.failures == []
    assert len(result.image_sha256) == 64  # SHA-256 hex
