"""materialize_findings bridges the observation→Finding seam.

record_observation stages OBSERVATION records but never creates the Finding
records (finding_id/status) that review/approve/report consume. Without this
bridge the review table is empty and report.md stays empty even though
observations exist.
"""

from __future__ import annotations

import json
from pathlib import Path

from silentwitness_mcp.findings._approval_store import materialize_findings, read_findings


def _write(case_dir: Path, records: list[dict]) -> None:  # type: ignore[type-arg]
    (case_dir / "findings.json").write_text(json.dumps(records), encoding="utf-8")


def _obs(n: int, interps: list[str]) -> dict:  # type: ignore[type-arg]
    return {
        "observation_id": f"O-{n:03d}",
        "text": f"observation {n}",
        "audit_ids": [f"aid-{n}"],
        "interpretations": [{"interpretation_id": i, "text": f"interp {i}"} for i in interps],
    }


def test_materializes_draft_finding_from_observation(tmp_path: Path) -> None:
    _write(tmp_path, [_obs(1, ["I-001"])])
    created = materialize_findings(tmp_path)
    assert created == ["F-001"]
    findings = read_findings(tmp_path)
    finding = next(f for f in findings if f.get("finding_id") == "F-001")
    assert finding["observation_id"] == "O-001"
    assert finding["interpretation_id"] == "I-001"
    assert finding["status"] == "DRAFT"
    assert "staged_at" in finding


def test_picks_latest_interpretation(tmp_path: Path) -> None:
    _write(tmp_path, [_obs(1, ["I-001", "I-002"])])
    materialize_findings(tmp_path)
    finding = next(f for f in read_findings(tmp_path) if f.get("finding_id"))
    assert finding["interpretation_id"] == "I-002"


def test_skips_observation_without_interpretation(tmp_path: Path) -> None:
    _write(tmp_path, [_obs(1, [])])
    assert materialize_findings(tmp_path) == []
    assert not any(isinstance(f, dict) and f.get("finding_id") for f in read_findings(tmp_path))


def test_is_idempotent(tmp_path: Path) -> None:
    _write(tmp_path, [_obs(1, ["I-001"])])
    assert materialize_findings(tmp_path) == ["F-001"]
    assert materialize_findings(tmp_path) == []  # no new Findings on re-run
    findings = read_findings(tmp_path)
    assert sum(1 for f in findings if isinstance(f, dict) and f.get("finding_id")) == 1


def test_preserves_observation_records(tmp_path: Path) -> None:
    _write(tmp_path, [_obs(1, ["I-001"]), _obs(2, ["I-002"])])
    materialize_findings(tmp_path)
    findings = read_findings(tmp_path)
    # both observations survive + two findings added
    assert sum(1 for f in findings if f.get("observation_id") and not f.get("finding_id")) == 2
    assert sum(1 for f in findings if f.get("finding_id")) == 2


def test_continues_finding_sequence(tmp_path: Path) -> None:
    _write(
        tmp_path,
        [
            {"finding_id": "F-001", "observation_id": "O-001", "status": "APPROVED"},
            _obs(2, ["I-002"]),
        ],
    )
    created = materialize_findings(tmp_path)
    assert created == ["F-002"]  # does not collide with existing F-001
