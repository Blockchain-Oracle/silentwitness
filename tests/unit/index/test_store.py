"""Unit tests for the SQLite FTS5 evidence index (pure stdlib — runs anywhere)."""

from __future__ import annotations

from pathlib import Path

import pytest

from silentwitness_mcp.index.store import EvidenceIndex, EvidenceIndexError, IndexRecord


def _records() -> list[IndexRecord]:
    return [
        IndexRecord(
            text="powershell.exe spawned by winword.exe on host DC1",
            source_tool="plaso",
            artifact_path="/Windows/System32/winevt/Logs/Security.evtx",
            host="DC1",
            ts="2020-11-15T19:46:42Z",
            audit_id="sift-analyst-20201115-001",
            sha256="a" * 64,
        ),
        IndexRecord(
            text="Run key HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run set to evil.exe",
            source_tool="regipy",
            artifact_path="/Windows/System32/config/SOFTWARE",
            host="DC1",
            ts="2020-11-15T20:01:00Z",
            audit_id="sift-analyst-20201115-002",
        ),
        IndexRecord(
            text="benign chrome.exe browsing session",
            source_tool="plaso",
            artifact_path="/Users/fred/AppData",
            host="WKSTN1",
            ts="2020-11-15T18:00:00Z",
            audit_id="sift-analyst-20201115-003",
        ),
    ]


def test_ingest_and_count(tmp_path: Path) -> None:
    with EvidenceIndex(tmp_path / "index.db") as idx:
        assert idx.ingest(_records()) == 3
        assert idx.count() == 3


def test_bulk_ingest_then_rebuild_fts_is_searchable(tmp_path: Path) -> None:
    with EvidenceIndex(tmp_path / "index.db") as idx:
        idx.begin_bulk()
        assert idx.bulk_ingest(_records(), batch=2) == 3  # batch < len exercises chunking
        assert idx.count() == 3
        # Before rebuild, the deferred FTS has no rows -> search finds nothing.
        assert idx.search("powershell") == []
        idx.rebuild_fts()
        hits = idx.search("powershell")
        assert len(hits) == 1 and "powershell.exe" in hits[0].text


def test_bulk_and_per_row_ingest_mix_is_consistent_after_rebuild(tmp_path: Path) -> None:
    with EvidenceIndex(tmp_path / "index.db") as idx:
        idx.ingest(_records()[:1])  # per-row path keeps its own FTS entry
        idx.bulk_ingest(_records()[1:])  # bulk path defers FTS
        idx.rebuild_fts()  # reconstructs FTS for ALL content rows
        assert idx.count() == 3
        assert len(idx.search("evil")) == 1
        assert len(idx.search("powershell")) == 1


def test_bulk_ingest_exact_batch_multiple_and_empty(tmp_path: Path) -> None:
    with EvidenceIndex(tmp_path / "index.db") as idx:
        # exact multiple of batch -> the trailing `if chunk:` flush must be skipped
        recs = _records()[:2]
        assert idx.bulk_ingest(recs, batch=2) == 2
        assert idx.count() == 2
        # empty input writes nothing and returns 0
        assert idx.bulk_ingest([]) == 0
        assert idx.count() == 2


def test_rebuild_fts_is_idempotent_across_incremental_loads(tmp_path: Path) -> None:
    with EvidenceIndex(tmp_path / "index.db") as idx:
        idx.bulk_ingest(_records()[:1])
        idx.rebuild_fts()
        idx.bulk_ingest(_records()[1:])
        idx.rebuild_fts()  # second rebuild must not duplicate or drop FTS rows
        assert idx.count() == 3
        assert len(idx.search("powershell")) == 1
        assert len(idx.search("chrome")) == 1


def test_search_matches_keyword(tmp_path: Path) -> None:
    with EvidenceIndex(tmp_path / "index.db") as idx:
        idx.ingest(_records())
        hits = idx.search("powershell")
        assert len(hits) == 1
        assert "powershell.exe" in hits[0].text
        assert hits[0].source_tool == "plaso"
        # provenance preserved end-to-end
        assert hits[0].audit_id == "sift-analyst-20201115-001"
        assert hits[0].id is not None


def test_search_host_filter(tmp_path: Path) -> None:
    with EvidenceIndex(tmp_path / "index.db") as idx:
        idx.ingest(_records())
        # "exe" matches rows on both hosts; the host filter narrows to DC1.
        dc1 = idx.search("exe", host="DC1")
        assert {r.host for r in dc1} == {"DC1"}
        assert {r.host for r in idx.search("exe")} == {"DC1", "WKSTN1"}


def test_search_source_tool_filter(tmp_path: Path) -> None:
    with EvidenceIndex(tmp_path / "index.db") as idx:
        idx.ingest(_records())
        assert {r.source_tool for r in idx.search("exe", source_tool="regipy")} == {"regipy"}


def test_search_fts_boolean_syntax(tmp_path: Path) -> None:
    with EvidenceIndex(tmp_path / "index.db") as idx:
        idx.ingest(_records())
        assert len(idx.search("powershell AND winword")) == 1
        assert len(idx.search("powershell OR chrome")) == 2
        assert len(idx.search("evil*")) == 1  # prefix query


def test_search_limit(tmp_path: Path) -> None:
    with EvidenceIndex(tmp_path / "index.db") as idx:
        idx.ingest(_records())
        assert len(idx.search("exe", limit=1)) == 1


def test_malformed_query_raises(tmp_path: Path) -> None:
    with EvidenceIndex(tmp_path / "index.db") as idx:
        idx.ingest(_records())
        with pytest.raises(EvidenceIndexError, match="invalid search query"):
            idx.search('"unterminated')


def test_get_by_id_and_absent(tmp_path: Path) -> None:
    with EvidenceIndex(tmp_path / "index.db") as idx:
        idx.ingest(_records())
        first = idx.search("powershell")[0]
        assert first.id is not None
        got = idx.get(first.id)
        assert got is not None and got.text == first.text
        assert idx.get(999999) is None


def test_recent_orders_by_ts_desc_with_filter(tmp_path: Path) -> None:
    with EvidenceIndex(tmp_path / "index.db") as idx:
        idx.ingest(_records())
        all_recent = idx.recent()
        ts_order = [r.ts for r in all_recent]
        assert ts_order == sorted(ts_order, reverse=True)  # newest first
        dc1 = idx.recent(host="DC1")
        assert {r.host for r in dc1} == {"DC1"}
        assert len(idx.recent(limit=1)) == 1


def test_persists_across_reopen(tmp_path: Path) -> None:
    db = tmp_path / "index.db"
    with EvidenceIndex(db) as idx:
        idx.ingest(_records())
    with EvidenceIndex(db) as reopened:
        assert reopened.count() == 3
        assert len(reopened.search("powershell")) == 1
