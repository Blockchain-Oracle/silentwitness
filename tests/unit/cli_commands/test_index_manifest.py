from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from silentwitness_agent.cli_commands.index_manifest import (
    build_expected_manifest,
    current_index_row_count,
    index_is_current,
    index_manifest_path,
    write_index_manifest,
)
from silentwitness_common.types import EvidenceRecord, EvidenceType
from silentwitness_mcp.index.store import EvidenceIndex, IndexRecord


def _record(path: Path, *, sha: str = "a" * 64) -> EvidenceRecord:
    return EvidenceRecord(
        path=path,
        type=EvidenceType.EVTX,
        sha256=sha,
        size_bytes=123,
        registered_at=datetime(2026, 6, 17, tzinfo=UTC),
        registered_audit_id="sift-root-20260617-001",
    )


def _manifest(
    tmp_path: Path, *, profile: str = "standard", with_plaso: bool = False
) -> dict[str, object]:
    return build_expected_manifest(
        case_id="case-1",
        host="host-a",
        memory_profile=profile,
        memory_plugins=("windows.pslist.PsList",),
        with_plaso=with_plaso,
        artifacts=(_record(tmp_path / "Security.evtx"),),
    )


def test_index_is_not_current_without_db(tmp_path: Path) -> None:
    assert index_is_current(tmp_path, _manifest(tmp_path)) == (False, None)


def test_index_manifest_marks_matching_db_current(tmp_path: Path) -> None:
    with EvidenceIndex(tmp_path / "index.db") as index:
        index.bulk_ingest([IndexRecord(text="EventID=4624", source_tool="evtx:Security")])
        index.rebuild_fts()

    expected = _manifest(tmp_path)
    write_index_manifest(tmp_path, expected, rows=1, summary={"rows": 1})

    assert index_manifest_path(tmp_path).is_file()
    assert current_index_row_count(tmp_path) == 1
    assert index_is_current(tmp_path, expected) == (True, 1)


def test_index_manifest_invalidates_profile_change(tmp_path: Path) -> None:
    with EvidenceIndex(tmp_path / "index.db") as index:
        index.bulk_ingest([IndexRecord(text="EventID=4624")])
        index.rebuild_fts()

    write_index_manifest(tmp_path, _manifest(tmp_path, profile="standard"), rows=1, summary={})

    assert index_is_current(tmp_path, _manifest(tmp_path, profile="targeted")) == (False, 1)


def test_index_manifest_invalidates_plaso_change(tmp_path: Path) -> None:
    with EvidenceIndex(tmp_path / "index.db") as index:
        index.bulk_ingest([IndexRecord(text="EventID=4624")])
        index.rebuild_fts()

    write_index_manifest(tmp_path, _manifest(tmp_path), rows=1, summary={})

    assert index_is_current(tmp_path, _manifest(tmp_path, with_plaso=True)) == (False, 1)
