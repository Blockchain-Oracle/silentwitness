"""Unit tests for the targeted-parser ingest orchestrator (no real artifacts needed)."""

from __future__ import annotations

import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.index import ingest_artifacts
from silentwitness_mcp.index.ingest_artifacts import (
    _citation_path,
    _kind_for,
    ingest_prepared_artifacts,
)
from silentwitness_mcp.index.store import EvidenceIndex, IndexRecord


@pytest.mark.parametrize(
    ("evidence_type", "name", "expected"),
    [
        (EvidenceType.EVTX, "Security.evtx", "evtx"),
        (EvidenceType.HIVE, "SOFTWARE", "registry"),
        (EvidenceType.OTHER, "SRUDB.dat", "srum"),  # case-insensitive match
        (EvidenceType.OTHER, "srudb.DAT", "srum"),
        (EvidenceType.OTHER, "$MFT", "mft"),
        (EvidenceType.OTHER, "_MFT", "mft"),
        (EvidenceType.OTHER, "_UsnJrnl", "usnjrnl"),
        (EvidenceType.OTHER, "NOTEPAD.EXE-12345678.pf", "prefetch"),  # suffix route
        (EvidenceType.OTHER, "RCLONE.EXE-AABBCCDD.PF", "prefetch"),  # suffix is lowercased
        (EvidenceType.OTHER, "report.docx.lnk", "lnk"),
        (EvidenceType.OTHER, "5f7b5f1e01b83767.automaticDestinations-ms", "jumplist"),
        (EvidenceType.OTHER, "PowerShell_transcript.HOST.abc.20201113.txt", "pstranscript"),
        (EvidenceType.OTHER, "powershell_transcript.x.txt", "pstranscript"),  # name lowercased
        (EvidenceType.OTHER, "PowerShell_transcript.HOST.log", None),  # right prefix, wrong ext
        (EvidenceType.OTHER, "notes.txt", None),  # plain .txt is not a transcript
        (EvidenceType.OTHER, "UsrClass.dat", None),  # unmapped OTHER -> not ingested
        (EvidenceType.PCAP, "nitroba.pcap", "pcap"),
        (EvidenceType.DISK_IMAGE, "img.e01", None),  # plaso path, not a targeted feeder
    ],
)
def test_kind_for_routing(evidence_type: EvidenceType, name: str, expected: str | None) -> None:
    assert _kind_for(evidence_type, name) == expected


@dataclass(frozen=True)
class _Rec:
    type: EvidenceType
    path: Path


class _FakeRegistry:
    def __init__(self, recs: list[_Rec]) -> None:
        self._recs = recs

    def list_all(self) -> list[_Rec]:
        return self._recs


def _one_record_feeder(label: str) -> Any:
    def feeder(
        path: Path,
        *,
        audit_id: str,
        host: str = "",
        source_path: str | None = None,
        stats: Any = None,
    ) -> Iterator[IndexRecord]:
        yield IndexRecord(text=f"{label} from {path.name}", source_tool=label, audit_id=audit_id)

    return feeder


def test_citation_path_is_relative_to_prepared() -> None:
    p = Path("/root/sw/cases/rocba/prepared/rocba-cdrive/evtx/Windows/Logs/Security.evtx")
    assert _citation_path(p) == "rocba-cdrive/evtx/Windows/Logs/Security.evtx"


def test_citation_path_fallback_keeps_context_to_avoid_collisions() -> None:
    # Outside a prepared/ tree: keep the last few components so two same-named hives
    # don't collide on a bare-filename citation.
    assert _citation_path(Path("/somewhere/odd/Security.evtx")) == "somewhere/odd/Security.evtx"
    assert _citation_path(Path("SOFTWARE")) == "SOFTWARE"


def test_evtx_and_hive_dispatched_and_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ingest_artifacts, "evtx_file_records", _one_record_feeder("evtx:Security"))
    monkeypatch.setattr(ingest_artifacts, "registry_hive_records", _one_record_feeder("regipy:run"))
    registry = _FakeRegistry(
        [
            _Rec(EvidenceType.EVTX, Path("/c/prepared/img/evtx/Security.evtx")),
            _Rec(EvidenceType.HIVE, Path("/c/prepared/img/hive/SOFTWARE")),
            _Rec(EvidenceType.EVTX, Path("/c/prepared/img/evtx/System.evtx")),
            _Rec(EvidenceType.DISK_IMAGE, Path("/c/img.e01")),  # not a targeted feeder -> ignored
        ]
    )
    with EvidenceIndex(tmp_path / "index.db") as idx:
        result = ingest_prepared_artifacts(
            registry, idx, audit_id="sift-a-1", host="ROCBA", max_workers=1
        )
        idx.rebuild_fts()
        assert result.counts == {"evtx": 2, "registry": 1}
        assert result.failures == []
        assert idx.count() == 3


def test_pcap_dispatched_and_counted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ingest_artifacts, "pcap_records", _one_record_feeder("zeek:conn"))
    registry = _FakeRegistry([_Rec(EvidenceType.PCAP, Path("/evidence/nitroba.pcap"))])
    with EvidenceIndex(tmp_path / "index.db") as idx:
        result = ingest_prepared_artifacts(
            registry, idx, audit_id="sift-a-1", host="nitroba", max_workers=1
        )
        idx.rebuild_fts()
        assert result.counts == {"pcap": 1}
        assert result.failures == []
        assert idx.count() == 1


def test_feeder_error_on_one_artifact_is_skipped_and_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def flaky_feeder(
        path: Path,
        *,
        audit_id: str,
        host: str = "",
        source_path: str | None = None,
        stats: Any = None,
    ) -> Iterator[IndexRecord]:
        if "bad" in path.name:
            raise RuntimeError("corrupt evtx")  # not OSError/ValueError -> must still be caught
        yield IndexRecord(text="ok", source_tool="evtx:Security", audit_id=audit_id)

    monkeypatch.setattr(ingest_artifacts, "evtx_file_records", flaky_feeder)
    registry = _FakeRegistry(
        [
            _Rec(EvidenceType.EVTX, Path("/c/prepared/img/evtx/bad.evtx")),
            _Rec(EvidenceType.EVTX, Path("/c/prepared/img/evtx/good.evtx")),
        ]
    )
    with EvidenceIndex(tmp_path / "index.db") as idx:
        result = ingest_prepared_artifacts(registry, idx, audit_id="a", host="", max_workers=1)
        assert result.counts == {"evtx": 1}
        # The failure is COUNTED, not silently swallowed (the non-negotiable invariant).
        assert len(result.failures) == 1
        assert result.failures[0][1] == "bad.evtx" and "corrupt" in result.failures[0][2]


def test_per_record_skips_are_surfaced_in_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def skipping_feeder(
        path: Path,
        *,
        audit_id: str,
        host: str = "",
        source_path: str | None = None,
        stats: Any = None,
    ) -> Iterator[IndexRecord]:
        if stats is not None:
            stats.skip("corrupt_record")
            stats.skip("corrupt_record")
        yield IndexRecord(text="kept", source_tool="evtx:Security", audit_id=audit_id)

    monkeypatch.setattr(ingest_artifacts, "evtx_file_records", skipping_feeder)
    registry = _FakeRegistry([_Rec(EvidenceType.EVTX, Path("/c/prepared/img/evtx/a.evtx"))])
    with EvidenceIndex(tmp_path / "index.db") as idx:
        result = ingest_prepared_artifacts(registry, idx, audit_id="a", host="", max_workers=1)
        assert result.counts == {"evtx": 1}
        # The 2 swallowed records are visible, not hidden behind the green count.
        assert len(result.diagnostics) == 1
        kind, name, skipped = result.diagnostics[0]
        assert kind == "evtx" and name == "a.evtx" and skipped == {"corrupt_record": 2}


def test_feeder_stdout_stderr_noise_is_suppressed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def noisy_feeder(
        path: Path,
        *,
        audit_id: str,
        host: str = "",
        source_path: str | None = None,
        stats: Any = None,
    ) -> Iterator[IndexRecord]:
        print("raw parser stdout warning")
        print("raw parser stderr warning", file=sys.stderr)
        yield IndexRecord(text="kept", source_tool="evtx:Security", audit_id=audit_id)

    monkeypatch.setattr(ingest_artifacts, "evtx_file_records", noisy_feeder)
    registry = _FakeRegistry([_Rec(EvidenceType.EVTX, Path("/c/prepared/img/evtx/a.evtx"))])
    with EvidenceIndex(tmp_path / "index.db") as idx:
        result = ingest_prepared_artifacts(registry, idx, audit_id="a", host="", max_workers=1)

    captured = capsys.readouterr()
    assert result.counts == {"evtx": 1}
    assert "raw parser" not in captured.out
    assert "raw parser" not in captured.err


def test_slow_feeder_times_out_and_is_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def slow_feeder(
        path: Path,
        *,
        audit_id: str,
        host: str = "",
        source_path: str | None = None,
        stats: Any = None,
    ) -> Iterator[IndexRecord]:
        time.sleep(0.2)
        yield IndexRecord(text="late", source_tool="evtx:Security", audit_id=audit_id)

    monkeypatch.setenv("SILENTWITNESS_PARSER_TIMEOUT_SEC", "0.05")
    monkeypatch.setattr(ingest_artifacts, "evtx_file_records", slow_feeder)
    registry = _FakeRegistry([_Rec(EvidenceType.EVTX, Path("/c/prepared/img/evtx/slow.evtx"))])
    with EvidenceIndex(tmp_path / "index.db") as idx:
        result = ingest_prepared_artifacts(registry, idx, audit_id="a", host="", max_workers=1)

    assert result.counts == {}
    assert len(result.failures) == 1
    assert result.failures[0][1] == "slow.evtx"
    assert "timeout" in result.failures[0][2]


# ---------------------------------------------------------------------------
# Parallel-path coverage: a synchronous ProcessPoolExecutor shim runs the
# real parallel branch in-process so its counts/skip/no-drop logic is exercised
# deterministically on every platform (real subprocesses can't see monkeypatches).
# ---------------------------------------------------------------------------


class _SyncFuture:
    def __init__(self, fn: Any, args: tuple[Any, ...]) -> None:
        try:
            self._result: Any = fn(*args)
            self._exc: BaseException | None = None
        except Exception as exc:  # mirror a worker raising
            self._exc = exc

    def result(self) -> Any:
        if self._exc is not None:
            raise self._exc
        return self._result


class _SyncPool:
    def __init__(self, max_workers: int | None = None) -> None:
        pass

    def __enter__(self) -> _SyncPool:
        return self

    def __exit__(self, *_: object) -> bool:
        return False

    def submit(self, fn: Any, *args: Any) -> _SyncFuture:
        return _SyncFuture(fn, args)


def _patch_sync_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ingest_artifacts, "ProcessPoolExecutor", _SyncPool)
    monkeypatch.setattr(ingest_artifacts, "as_completed", lambda futures: list(futures))


def test_parallel_path_keeps_every_record_and_records_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_sync_pool(monkeypatch)

    def feeder(
        path: Path,
        *,
        audit_id: str,
        host: str = "",
        source_path: str | None = None,
        stats: Any = None,
    ) -> Iterator[IndexRecord]:
        if "bad" in path.name:
            raise RuntimeError("Failed to parse chunk header")
        if "skipme" in path.name and stats is not None:
            stats.skip("test_skip")  # exercise the diagnostics channel
        # two rows per good artifact, to prove no rows are lost across the pool
        yield IndexRecord(text=f"a {path.name}", source_tool="evtx:Security", audit_id=audit_id)
        yield IndexRecord(text=f"b {path.name}", source_tool="evtx:Security", audit_id=audit_id)

    monkeypatch.setattr(ingest_artifacts, "evtx_file_records", feeder)
    monkeypatch.setattr(ingest_artifacts, "registry_hive_records", feeder)
    registry = _FakeRegistry(
        [
            _Rec(EvidenceType.EVTX, Path("/c/prepared/img/evtx/good1.evtx")),
            _Rec(EvidenceType.EVTX, Path("/c/prepared/img/evtx/bad.evtx")),
            _Rec(EvidenceType.HIVE, Path("/c/prepared/img/hive/SOFTWARE")),
        ]
    )
    with EvidenceIndex(tmp_path / "index.db") as idx:
        result = ingest_prepared_artifacts(registry, idx, audit_id="a", host="", max_workers=4)
        idx.rebuild_fts()
        # 2 good artifacts x 2 rows = 4 rows; none dropped.
        assert idx.count() == 4
        assert result.counts == {"evtx": 2, "registry": 2}
        assert len(result.failures) == 1 and result.failures[0][1] == "bad.evtx"
