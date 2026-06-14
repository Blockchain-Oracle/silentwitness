"""Unit tests for the targeted-parser ingest orchestrator (no real artifacts needed)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.index import ingest_artifacts
from silentwitness_mcp.index.ingest_artifacts import _citation_path, ingest_prepared_artifacts
from silentwitness_mcp.index.store import EvidenceIndex, IndexRecord


@dataclass(frozen=True)
class _Rec:
    type: EvidenceType
    path: Path


class _FakeRegistry:
    def __init__(self, recs: list[_Rec]) -> None:
        self._recs = recs

    def list_all(self) -> list[_Rec]:
        return self._recs


def test_citation_path_is_relative_to_prepared() -> None:
    p = Path("/root/sw/cases/rocba/prepared/rocba-cdrive/evtx/Windows/Logs/Security.evtx")
    assert _citation_path(p) == "rocba-cdrive/evtx/Windows/Logs/Security.evtx"


def test_citation_path_falls_back_to_name() -> None:
    assert _citation_path(Path("/somewhere/odd/Security.evtx")) == "Security.evtx"


def _one_record_feeder(label: str) -> object:
    def feeder(
        path: Path, *, audit_id: str, host: str = "", source_path: str | None = None
    ) -> Iterator[IndexRecord]:
        yield IndexRecord(text=f"{label} from {path.name}", source_tool=label, audit_id=audit_id)

    return feeder


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
        counts = ingest_prepared_artifacts(
            registry, idx, audit_id="sift-a-1", host="ROCBA", max_workers=1
        )
        assert counts == {"evtx": 2, "registry": 1}
        assert idx.count() == 3


def test_feeder_error_on_one_artifact_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def flaky_feeder(
        path: Path, *, audit_id: str, host: str = "", source_path: str | None = None
    ) -> Iterator[IndexRecord]:
        if "bad" in path.name:
            raise OSError("corrupt evtx")
        yield IndexRecord(text="ok", source_tool="evtx:Security", audit_id=audit_id)

    monkeypatch.setattr(ingest_artifacts, "evtx_file_records", flaky_feeder)
    registry = _FakeRegistry(
        [
            _Rec(EvidenceType.EVTX, Path("/c/prepared/img/evtx/bad.evtx")),
            _Rec(EvidenceType.EVTX, Path("/c/prepared/img/evtx/good.evtx")),
        ]
    )
    with EvidenceIndex(tmp_path / "index.db") as idx:
        counts = ingest_prepared_artifacts(registry, idx, audit_id="a", host="", max_workers=1)
        assert counts == {"evtx": 1}
