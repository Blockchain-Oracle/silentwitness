"""Unit tests for CriticTrigger.staged_findings_for_review.

All tests are deterministic: clock injection replaces datetime.now(UTC),
tmp_path provides a fresh case directory per test, and no real I/O
beyond the local tmp_path.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from silentwitness_agent.critic_trigger import CriticTrigger
from silentwitness_common.types import Confidence


def _make_trigger(
    tmp_path: Path,
    *,
    interval_findings: int = 5,
    interval_minutes: float = 10.0,
    clock_offset: timedelta = timedelta(0),
) -> CriticTrigger:
    base = datetime.now(UTC)
    return CriticTrigger(
        case_dir=tmp_path,
        examiner="aj",
        interval_findings=interval_findings,
        interval_minutes=interval_minutes,
        clock=lambda: base + clock_offset,
    )


def _write_findings(path: Path, count: int) -> None:
    """Write `count` minimal observation records to findings.json."""
    findings = [
        {
            "observation_id": f"O-{i + 1:03d}",
            "text": f"Observation {i + 1}",
            "audit_ids": [f"sift-aj-2026-{i + 1:03d}"],
            "cited_spans": [],
            "interpretations": [
                {
                    "interpretation_id": f"I-{i + 1:03d}",
                    "text": f"Interpretation {i + 1}",
                    "confidence": "HIGH",
                }
            ],
        }
        for i in range(count)
    ]
    path.write_text(json.dumps(findings), encoding="utf-8")


# ---------------------------------------------------------------------------
# 12. staged_findings_for_review returns only post-watermark findings
# ---------------------------------------------------------------------------


def test_staged_findings_for_review_returns_post_watermark(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.json"
    _write_findings(findings_path, 7)
    trigger = _make_trigger(tmp_path, interval_findings=5)
    trigger.mark_fired(3)
    findings = trigger.staged_findings_for_review(findings_path)
    assert len(findings) == 4
    assert findings[0].finding_id == "O-004"
    assert findings[3].finding_id == "O-007"


# ---------------------------------------------------------------------------
# 13. staged_findings_for_review populates cited_blob_paths
# ---------------------------------------------------------------------------


def test_staged_findings_for_review_populates_blob_paths(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.json"
    _write_findings(findings_path, 2)
    trigger = _make_trigger(tmp_path, interval_findings=5)
    findings = trigger.staged_findings_for_review(findings_path)
    assert len(findings) == 2
    for f in findings:
        assert len(f.cited_blob_paths) == 1
        assert f.cited_blob_paths[0].parent == tmp_path / "audit" / "blobs"


# ---------------------------------------------------------------------------
# 14. staged_findings_for_review skips observations without interpretations
# ---------------------------------------------------------------------------


def test_staged_findings_skips_uninterpreted_observations(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(
        json.dumps(
            [
                {
                    "observation_id": "O-001",
                    "text": "obs",
                    "audit_ids": [],
                    "cited_spans": [],
                    "interpretations": [],  # no interpretations → skip
                },
                {
                    "observation_id": "O-002",
                    "text": "obs2",
                    "audit_ids": [],
                    "cited_spans": [],
                    "interpretations": [
                        {"interpretation_id": "I-001", "text": "interp", "confidence": "LOW"}
                    ],
                },
            ]
        ),
        encoding="utf-8",
    )
    trigger = _make_trigger(tmp_path)
    findings = trigger.staged_findings_for_review(findings_path)
    assert len(findings) == 1
    assert findings[0].finding_id == "O-002"


# ---------------------------------------------------------------------------
# 15. staged_findings_for_review on missing file returns empty list
# ---------------------------------------------------------------------------


def test_staged_findings_missing_file_returns_empty(tmp_path: Path) -> None:
    trigger = _make_trigger(tmp_path)
    result = trigger.staged_findings_for_review(tmp_path / "nonexistent.json")
    assert result == []


# ---------------------------------------------------------------------------
# 18. staged_findings_for_review skips empty observation text
# ---------------------------------------------------------------------------


def test_staged_findings_skips_empty_observation_text(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(
        json.dumps(
            [
                {
                    "observation_id": "O-001",
                    "text": "",  # empty — should be skipped
                    "audit_ids": [],
                    "interpretations": [
                        {"interpretation_id": "I-001", "text": "interp", "confidence": "HIGH"}
                    ],
                },
                {
                    "observation_id": "O-002",
                    "text": "valid obs",
                    "audit_ids": [],
                    "interpretations": [
                        {"interpretation_id": "I-002", "text": "valid interp", "confidence": "HIGH"}
                    ],
                },
            ]
        ),
        encoding="utf-8",
    )
    trigger = _make_trigger(tmp_path)
    result = trigger.staged_findings_for_review(findings_path)
    assert len(result) == 1
    assert result[0].finding_id == "O-002"


# ---------------------------------------------------------------------------
# 19. staged_findings_for_review handles corrupt findings.json (bad JSON)
# ---------------------------------------------------------------------------


def test_staged_findings_corrupt_json_returns_empty(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.json"
    findings_path.write_text("{not valid json[", encoding="utf-8")
    trigger = _make_trigger(tmp_path)
    assert trigger.staged_findings_for_review(findings_path) == []


# ---------------------------------------------------------------------------
# 20. staged_findings_for_review handles non-list findings.json
# ---------------------------------------------------------------------------


def test_staged_findings_non_list_findings_json_returns_empty(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(json.dumps({"findings": [], "meta": {}}), encoding="utf-8")
    trigger = _make_trigger(tmp_path)
    assert trigger.staged_findings_for_review(findings_path) == []


# ---------------------------------------------------------------------------
# 21. staged_findings_for_review skips non-dict entries in findings array
# ---------------------------------------------------------------------------


def test_staged_findings_skips_non_dict_entries(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(
        json.dumps(
            [
                "a bare string",
                42,
                {
                    "observation_id": "O-001",
                    "text": "real obs",
                    "audit_ids": [],
                    "interpretations": [{"text": "real interp", "confidence": "HIGH"}],
                },
            ]
        ),
        encoding="utf-8",
    )
    trigger = _make_trigger(tmp_path)
    result = trigger.staged_findings_for_review(findings_path)
    assert len(result) == 1
    assert result[0].finding_id == "O-001"


# ---------------------------------------------------------------------------
# 22. staged_findings_for_review falls back to LOW for unknown confidence
# ---------------------------------------------------------------------------


def test_staged_findings_invalid_confidence_falls_back_to_low(tmp_path: Path) -> None:
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(
        json.dumps(
            [
                {
                    "observation_id": "O-001",
                    "text": "obs",
                    "audit_ids": [],
                    "interpretations": [{"text": "interp", "confidence": "VERY_HIGH"}],
                }
            ]
        ),
        encoding="utf-8",
    )
    trigger = _make_trigger(tmp_path)
    result = trigger.staged_findings_for_review(findings_path)
    assert len(result) == 1
    assert result[0].confidence == Confidence.LOW
