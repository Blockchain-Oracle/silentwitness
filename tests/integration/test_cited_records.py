"""Coverage for ``_cited_records`` — the index-lookup that resolves an agent's
cited record_ids against the case ``index.db`` (the seam where the citation gate
meets real on-disk storage)."""

from __future__ import annotations

from pathlib import Path

import pytest

from silentwitness_mcp._tool_impls_findings import _cited_records
from silentwitness_mcp.index.store import EvidenceIndex, EvidenceIndexError, IndexRecord


def _build_index(case_dir: Path, *records: IndexRecord) -> None:
    with EvidenceIndex(case_dir / "index.db") as idx:
        idx.ingest(records)


def test_resolves_existing_rows_from_real_index(tmp_path: Path) -> None:
    """A real index.db with two rows resolves the cited ids to their records;
    rowids are assigned 1..N on ingest."""
    _build_index(
        tmp_path,
        IndexRecord(text="svchost.exe at PID 1208", source_tool="evtx:Security", audit_id="a1"),
        IndexRecord(text="cmd.exe at PID 4172", source_tool="evtx:Security", audit_id="a2"),
    )
    resolved = _cited_records(tmp_path, {1, 2})
    assert set(resolved) == {1, 2}
    assert resolved[1].text == "svchost.exe at PID 1208"
    assert resolved[2].audit_id == "a2"


def test_absent_ids_are_omitted_not_errored(tmp_path: Path) -> None:
    """An id with no row is simply missing from the map (→ RECORD_NOT_FOUND
    downstream), not an error."""
    _build_index(tmp_path, IndexRecord(text="only row", source_tool="mft", audit_id="a1"))
    resolved = _cited_records(tmp_path, {1, 999})
    assert set(resolved) == {1}


def test_no_index_returns_empty_without_creating_db(tmp_path: Path) -> None:
    """No index.db yet → empty map, and the lookup must NOT create an empty db
    as a side effect (that would mask 'index never built')."""
    resolved = _cited_records(tmp_path, {1})
    assert resolved == {}
    assert not (tmp_path / "index.db").exists()


def test_empty_id_set_short_circuits(tmp_path: Path) -> None:
    _build_index(tmp_path, IndexRecord(text="row", source_tool="mft", audit_id="a1"))
    assert _cited_records(tmp_path, set()) == {}


def test_corrupt_index_raises_evidence_index_error(tmp_path: Path) -> None:
    """A present-but-unreadable index (corrupt image) raises EvidenceIndexError —
    the MCP wrapper converts this into a FINDINGS_STORE_CORRUPTED reject rather
    than letting a raw sqlite error crash the tool body."""
    (tmp_path / "index.db").write_bytes(b"this is not a sqlite database, it is garbage" * 8)
    with pytest.raises(EvidenceIndexError):
        _cited_records(tmp_path, {1})
