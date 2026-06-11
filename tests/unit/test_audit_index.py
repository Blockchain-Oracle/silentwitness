"""Unit tests for AuditIndex (9 tests)."""

from __future__ import annotations

import json
from pathlib import Path

from silentwitness_agent.report.audit_index import AuditIndex


def _write_jsonl(path: Path, records: list[dict]) -> None:  # type: ignore[type-arg]
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. from_dir returns empty index for empty dir
# ---------------------------------------------------------------------------


def test_from_dir_empty_dir(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    index = AuditIndex.from_dir(audit_dir)
    assert len(index) == 0
    assert not index.contains("sift-aj-20260613-001")


# ---------------------------------------------------------------------------
# 2. from_dir indexes one audit_id per JSONL line
# ---------------------------------------------------------------------------


def test_from_dir_indexes_single_file(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    _write_jsonl(
        audit_dir / "findings.jsonl",
        [
            {"audit_id": "sift-aj-20260613-001", "tool": "vol3"},
            {"audit_id": "sift-aj-20260613-002", "tool": "sbeCmd"},
        ],
    )
    index = AuditIndex.from_dir(audit_dir)
    assert len(index) == 2
    assert index.contains("sift-aj-20260613-001")
    assert index.contains("sift-aj-20260613-002")
    assert not index.contains("sift-aj-20260613-999")


# ---------------------------------------------------------------------------
# 3. from_dir handles multi-file scan (5 * 10 = 50 audit_ids indexed)
# ---------------------------------------------------------------------------


def test_from_dir_multi_file_scan(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    expected_ids: set[str] = set()
    for file_idx in range(5):
        records = []
        for line_idx in range(10):
            seq = file_idx * 10 + line_idx + 1
            aid = f"sift-aj-20260613-{seq:03d}"
            records.append({"audit_id": aid, "tool": f"tool{file_idx}"})
            expected_ids.add(aid)
        _write_jsonl(audit_dir / f"tool{file_idx}.jsonl", records)

    index = AuditIndex.from_dir(audit_dir)
    assert len(index) == 50
    for aid in expected_ids:
        assert index.contains(aid), f"Missing {aid}"
    assert not index.contains("sift-fake-99999999-999")


# ---------------------------------------------------------------------------
# 4. contains returns True for indexed audit_id
# ---------------------------------------------------------------------------


def test_contains_returns_true_for_indexed(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    _write_jsonl(
        audit_dir / "vol3.jsonl",
        [{"audit_id": "sift-aj-20260613-007", "tool": "vol3"}],
    )
    index = AuditIndex.from_dir(audit_dir)
    assert index.contains("sift-aj-20260613-007") is True


# ---------------------------------------------------------------------------
# 5. lookup returns source file + line number for indexed audit_id
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 6. from_dir returns empty index when audit_dir does not exist
# ---------------------------------------------------------------------------


def test_from_dir_nonexistent_dir_returns_empty(tmp_path: Path) -> None:
    index = AuditIndex.from_dir(tmp_path / "nonexistent")
    assert len(index) == 0


# ---------------------------------------------------------------------------
# 7. from_dir skips malformed JSON lines without crashing
# ---------------------------------------------------------------------------


def test_from_dir_skips_malformed_lines(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    (audit_dir / "mixed.jsonl").write_text(
        'not-json\n{"audit_id": "sift-aj-20260613-001", "tool": "vol3"}\n{bad}\n',
        encoding="utf-8",
    )
    index = AuditIndex.from_dir(audit_dir)
    assert len(index) == 1
    assert index.contains("sift-aj-20260613-001")


# ---------------------------------------------------------------------------
# 8. from_dir skips records without audit_id field; ts field is captured
# ---------------------------------------------------------------------------


def test_from_dir_captures_ts_and_skips_no_audit_id(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    _write_jsonl(
        audit_dir / "log.jsonl",
        [
            {"tool": "hayabusa"},  # no audit_id — should be skipped
            {"audit_id": "sift-aj-20260613-020", "tool": "hayabusa", "ts": "2026-06-13T10:00:00Z"},
        ],
    )
    index = AuditIndex.from_dir(audit_dir)
    assert len(index) == 1
    ref = index.lookup("sift-aj-20260613-020")
    assert ref is not None
    assert ref.ts == "2026-06-13T10:00:00Z"


# ---------------------------------------------------------------------------
# 9. from_dir deduplicates — first occurrence of an audit_id wins
# ---------------------------------------------------------------------------


def test_from_dir_deduplicates_audit_ids(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    (audit_dir / "a.jsonl").write_text(
        '{"audit_id": "sift-aj-20260613-001", "tool": "first"}\n', encoding="utf-8"
    )
    (audit_dir / "b.jsonl").write_text(
        '{"audit_id": "sift-aj-20260613-001", "tool": "second"}\n', encoding="utf-8"
    )
    index = AuditIndex.from_dir(audit_dir)
    assert len(index) == 1
    ref = index.lookup("sift-aj-20260613-001")
    assert ref is not None
    assert ref.tool == "first"  # first file (sorted: a before b) wins


def test_lookup_returns_source_and_line(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    jsonl_path = audit_dir / "disk.jsonl"
    _write_jsonl(
        jsonl_path,
        [
            {"audit_id": "sift-aj-20260613-010", "tool": "mftecmd"},
            {"audit_id": "sift-aj-20260613-011", "tool": "mftecmd"},
        ],
    )
    index = AuditIndex.from_dir(audit_dir)
    ref = index.lookup("sift-aj-20260613-011")
    assert ref is not None
    assert ref.source_file == jsonl_path
    assert ref.line_number == 2
    assert ref.tool == "mftecmd"
    assert index.lookup("sift-fake-99999999-001") is None
