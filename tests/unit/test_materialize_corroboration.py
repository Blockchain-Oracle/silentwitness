"""End-to-end: `corroboration_tier` rides on every newly materialised finding.

The tier is computed at materialise time from the observation's cited record_ids
resolved against the case's `index.db`. These tests build a real EvidenceIndex,
seed it with rows from different evidence categories, and assert the tier the
materialised finding carries.
"""

from __future__ import annotations

import json
from pathlib import Path

from silentwitness_mcp.findings._approval_store import materialize_findings, read_findings
from silentwitness_mcp.findings.corroboration import CorroborationTier
from silentwitness_mcp.index.store import EvidenceIndex, IndexRecord


def _rec(source_tool: str, text: str = "row text") -> IndexRecord:
    return IndexRecord(
        text=text,
        source_tool=source_tool,
        artifact_path="m.raw",
        host="H",
        ts="2020-11-15T00:00:00+00:00",
        audit_id="A",
        sha256="s",
    )


def _seed_index(case_dir: Path, records: list[IndexRecord]) -> list[int]:
    """Bulk-ingest `records` into a fresh index.db; return the assigned ids."""
    with EvidenceIndex(case_dir / "index.db") as idx:
        idx.begin_bulk()
        idx.bulk_ingest(records)
        idx.rebuild_fts()
        # The ids are auto-assigned 1..N in insertion order.
        return list(range(1, len(records) + 1))


def _seed_observation(
    case_dir: Path, observation_id: str, record_ids: list[int], interpretation_id: str
) -> None:
    """Write findings.json with an observation pointing at the given record_ids."""
    cited_spans = [{"record_id": rid, "span_text": "row text"} for rid in record_ids]
    obs = {
        "observation_id": observation_id,
        "text": "the observation",
        "audit_ids": ["A"],
        "cited_spans": cited_spans,
        "interpretations": [{"interpretation_id": interpretation_id, "text": "interp text"}],
    }
    (case_dir / "findings.json").write_text(json.dumps([obs]), encoding="utf-8")


def test_confirmed_when_disk_and_memory_rows_cited(tmp_path: Path) -> None:
    """The headline disk + memory case: a Run-key (registry) + a netscan row
    (memory) → CONFIRMED across two categories."""
    rids = _seed_index(
        tmp_path,
        [_rec("regipy:NTUSER", "Run key value"), _rec("vol:netscan", "GoogleDriveFS")],
    )
    _seed_observation(tmp_path, "O-001", rids, "I-001")
    materialize_findings(tmp_path)

    finding = next(f for f in read_findings(tmp_path) if f.get("finding_id") == "F-001")
    assert finding["corroboration_tier"] == CorroborationTier.CONFIRMED.value
    assert "registry" in finding["corroboration_categories"]
    assert "memory" in finding["corroboration_categories"]


def test_inferred_when_two_same_category_rows_cited(tmp_path: Path) -> None:
    """Two vol:* rows both fall in `memory` → INFERRED."""
    rids = _seed_index(tmp_path, [_rec("vol:pslist"), _rec("vol:netscan")])
    _seed_observation(tmp_path, "O-001", rids, "I-001")
    materialize_findings(tmp_path)

    finding = next(f for f in read_findings(tmp_path) if f.get("finding_id") == "F-001")
    assert finding["corroboration_tier"] == CorroborationTier.INFERRED.value
    assert finding["corroboration_categories"] == ["memory"]


def test_unverified_when_single_record_cited(tmp_path: Path) -> None:
    rids = _seed_index(tmp_path, [_rec("sigma:critical")])
    _seed_observation(tmp_path, "O-001", rids, "I-001")
    materialize_findings(tmp_path)

    finding = next(f for f in read_findings(tmp_path) if f.get("finding_id") == "F-001")
    assert finding["corroboration_tier"] == CorroborationTier.UNVERIFIED.value
    assert finding["corroboration_categories"] == ["detection"]


def test_unverified_when_no_index_db_exists(tmp_path: Path) -> None:
    """Materialising before any indexing ran → tier defaults to UNVERIFIED rather
    than crashing. Realistic on a case approved before evidence registration."""
    _seed_observation(tmp_path, "O-001", [], "I-001")
    materialize_findings(tmp_path)

    finding = next(f for f in read_findings(tmp_path) if f.get("finding_id") == "F-001")
    assert finding["corroboration_tier"] == CorroborationTier.UNVERIFIED.value
    assert finding["corroboration_categories"] == []


def test_unverified_when_cited_record_ids_missing_from_index(tmp_path: Path) -> None:
    """An observation citing record_ids that aren't in index.db (stale citation)
    → UNVERIFIED, not a crash. Defensive — the citation gate would have rejected
    this earlier, but materialise must remain robust."""
    _seed_index(tmp_path, [_rec("mft")])  # populates id=1 only
    _seed_observation(tmp_path, "O-001", [999], "I-001")  # cites missing id
    materialize_findings(tmp_path)

    finding = next(f for f in read_findings(tmp_path) if f.get("finding_id") == "F-001")
    assert finding["corroboration_tier"] == CorroborationTier.UNVERIFIED.value


def test_categories_list_is_sorted_for_stable_rendering(tmp_path: Path) -> None:
    """report.md and the harness expect deterministic category ordering."""
    rids = _seed_index(tmp_path, [_rec("vol:pslist"), _rec("mft"), _rec("evtx:Security")])
    _seed_observation(tmp_path, "O-001", rids, "I-001")
    materialize_findings(tmp_path)

    finding = next(f for f in read_findings(tmp_path) if f.get("finding_id") == "F-001")
    cats = finding["corroboration_categories"]
    assert cats == sorted(cats)
    assert set(cats) == {"memory", "filesystem", "system_log"}
