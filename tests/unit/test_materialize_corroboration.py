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


def test_materialise_is_idempotent_tier_does_not_change_on_second_call(tmp_path: Path) -> None:
    """Running materialize_findings twice on the same case must not re-tier — the
    `covered` set skips already-materialised observations, so the tier is frozen
    on the first call. Round-1 review flagged this as a merge-blocker (a future
    refactor could silently re-tier against a later index state)."""
    rids = _seed_index(tmp_path, [_rec("regipy:NTUSER"), _rec("vol:netscan")])
    _seed_observation(tmp_path, "O-001", rids, "I-001")

    created_a = materialize_findings(tmp_path)
    findings_a = read_findings(tmp_path)
    finding_a = next(f for f in findings_a if f.get("finding_id") == "F-001")
    snapshot_tier = finding_a["corroboration_tier"]
    snapshot_cats = list(finding_a["corroboration_categories"])

    # Second call — no new observations to materialise.
    created_b = materialize_findings(tmp_path)
    assert created_a == ["F-001"]
    assert created_b == []  # no new findings

    findings_b = read_findings(tmp_path)
    finding_b = next(f for f in findings_b if f.get("finding_id") == "F-001")
    assert finding_b["corroboration_tier"] == snapshot_tier
    assert finding_b["corroboration_categories"] == snapshot_cats


def test_two_observations_independently_classified(tmp_path: Path) -> None:
    """The realistic flow: an investigation stages multiple observations with
    disjoint cited-record sets. Each must get its OWN tier, not a global rollup."""
    # 2 categories for O-001 → CONFIRMED; 1 record for O-002 → UNVERIFIED.
    rids = _seed_index(
        tmp_path,
        [_rec("regipy:NTUSER"), _rec("vol:netscan"), _rec("sigma:critical")],
    )
    obs_records = [
        {
            "observation_id": "O-001",
            "text": "first",
            "audit_ids": ["A"],
            "cited_spans": [
                {"record_id": rids[0], "span_text": "row text"},
                {"record_id": rids[1], "span_text": "row text"},
            ],
            "interpretations": [{"interpretation_id": "I-001", "text": "interp"}],
        },
        {
            "observation_id": "O-002",
            "text": "second",
            "audit_ids": ["A"],
            "cited_spans": [{"record_id": rids[2], "span_text": "row text"}],
            "interpretations": [{"interpretation_id": "I-002", "text": "interp"}],
        },
    ]
    (tmp_path / "findings.json").write_text(json.dumps(obs_records), encoding="utf-8")
    materialize_findings(tmp_path)

    findings = read_findings(tmp_path)
    f1 = next(f for f in findings if f.get("finding_id") == "F-001")
    f2 = next(f for f in findings if f.get("finding_id") == "F-002")
    assert f1["corroboration_tier"] == CorroborationTier.CONFIRMED.value
    assert f2["corroboration_tier"] == CorroborationTier.UNVERIFIED.value
    assert set(f1["corroboration_categories"]) == {"registry", "memory"}
    assert f2["corroboration_categories"] == ["detection"]


def test_powershell_transcript_classifies_as_system_log(tmp_path: Path) -> None:
    """Round-1 review caught `powershell:transcript` silently routing to `other`.
    This test pins the corrected categorisation end-to-end."""
    rids = _seed_index(tmp_path, [_rec("evtx:Security"), _rec("powershell:transcript")])
    _seed_observation(tmp_path, "O-001", rids, "I-001")
    materialize_findings(tmp_path)
    finding = next(f for f in read_findings(tmp_path) if f.get("finding_id") == "F-001")
    # Both rows are `system_log` → INFERRED (not CONFIRMED, not phantom 'other').
    assert finding["corroboration_tier"] == CorroborationTier.INFERRED.value
    assert finding["corroboration_categories"] == ["system_log"]
