"""Unit tests for CriticTrigger — ≥10 behavioural BDD scenarios.

All tests are deterministic: clock injection replaces datetime.now(UTC),
tmp_path provides a fresh case directory per test, and no real I/O
beyond the local tmp_path.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from silentwitness_agent.critic_trigger import CriticTrigger

# ---------------------------------------------------------------------------
# Clock helpers
# ---------------------------------------------------------------------------


def _clock_at(t: datetime) -> CriticTrigger:
    """Not used directly — helper for inline lambda factories below."""
    raise NotImplementedError


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


# ---------------------------------------------------------------------------
# 1. Fresh trigger with 0 findings → should_fire returns False
# ---------------------------------------------------------------------------


def test_fresh_trigger_zero_findings_returns_false(tmp_path: Path) -> None:
    trigger = _make_trigger(tmp_path)
    assert trigger.should_fire(0) is False


# ---------------------------------------------------------------------------
# 2. Fresh trigger with 5 findings → should_fire returns True (count threshold)
# ---------------------------------------------------------------------------


def test_fresh_trigger_five_findings_returns_true(tmp_path: Path) -> None:
    trigger = _make_trigger(tmp_path, interval_findings=5)
    assert trigger.should_fire(5) is True


# ---------------------------------------------------------------------------
# 3. should_fire is idempotent (calling twice without mark_fired → True twice)
# ---------------------------------------------------------------------------


def test_should_fire_is_idempotent(tmp_path: Path) -> None:
    trigger = _make_trigger(tmp_path, interval_findings=5)
    assert trigger.should_fire(5) is True
    assert trigger.should_fire(5) is True  # no side effects


# ---------------------------------------------------------------------------
# 4. After mark_fired(5), should_fire(5) returns False
# ---------------------------------------------------------------------------


def test_mark_fired_resets_should_fire(tmp_path: Path) -> None:
    trigger = _make_trigger(tmp_path, interval_findings=5)
    assert trigger.should_fire(5) is True
    trigger.mark_fired(5)
    assert trigger.should_fire(5) is False


# ---------------------------------------------------------------------------
# 5. After mark_fired(5) + 5 more findings, should_fire(10) is True
# ---------------------------------------------------------------------------


def test_five_more_findings_after_mark_fired_returns_true(tmp_path: Path) -> None:
    trigger = _make_trigger(tmp_path, interval_findings=5)
    trigger.mark_fired(5)
    assert trigger.should_fire(10) is True  # delta = 10 - 5 == interval threshold


# ---------------------------------------------------------------------------
# 6. Only 1 minute elapsed (M=10) AND below threshold → False
# ---------------------------------------------------------------------------


def test_not_enough_time_and_findings_returns_false(tmp_path: Path) -> None:
    trigger = _make_trigger(tmp_path, interval_findings=5, interval_minutes=10.0)
    trigger.mark_fired(0)
    # Rebuild with clock set to 1 minute after mark
    base = trigger._state.last_critic_at
    trigger2 = CriticTrigger(
        case_dir=tmp_path,
        examiner="aj",
        interval_findings=5,
        interval_minutes=10.0,
        clock=lambda: base + timedelta(minutes=1),
    )
    assert trigger2.should_fire(1) is False


# ---------------------------------------------------------------------------
# 7. 11 minutes elapsed (M=10) → True (time-based trigger)
# ---------------------------------------------------------------------------


def test_elapsed_time_triggers_even_below_count_threshold(tmp_path: Path) -> None:
    trigger = _make_trigger(tmp_path, interval_findings=5, interval_minutes=10.0)
    trigger.mark_fired(0)
    base = trigger._state.last_critic_at
    trigger2 = CriticTrigger(
        case_dir=tmp_path,
        examiner="aj",
        interval_findings=5,
        interval_minutes=10.0,
        clock=lambda: base + timedelta(minutes=11),
    )
    assert trigger2.should_fire(1) is True  # only 1 new finding, but time fired


# ---------------------------------------------------------------------------
# 8. Env override SILENTWITNESS_CRITIC_INTERVAL_FINDINGS=3
# ---------------------------------------------------------------------------


def test_env_override_interval_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CRITIC_INTERVAL_FINDINGS", "3")
    trigger = CriticTrigger(case_dir=tmp_path, examiner="aj")
    assert trigger.interval_findings == 3


# ---------------------------------------------------------------------------
# 9. Env override SILENTWITNESS_CRITIC_INTERVAL_MINUTES=2
# ---------------------------------------------------------------------------


def test_env_override_interval_minutes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CRITIC_INTERVAL_MINUTES", "2")
    trigger = CriticTrigger(case_dir=tmp_path, examiner="aj")
    assert trigger.interval_minutes == 2.0


# ---------------------------------------------------------------------------
# 10. State persists across construction
# ---------------------------------------------------------------------------


def test_state_persists_across_construction(tmp_path: Path) -> None:
    """Pre-write critic_state.json with count=3; fresh trigger sees count=3."""
    trigger = _make_trigger(tmp_path, interval_findings=5)
    trigger.mark_fired(3)
    # New trigger reads from disk
    trigger2 = _make_trigger(tmp_path, interval_findings=5)
    # delta = 5 - 3 == 2 < interval=5; time also not exceeded → False
    assert trigger2.should_fire(5) is False


# ---------------------------------------------------------------------------
# 11. mark_fired writes correct JSON fields to critic_state.json
# ---------------------------------------------------------------------------


def test_mark_fired_writes_correct_json(tmp_path: Path) -> None:
    trigger = _make_trigger(tmp_path, interval_findings=5)
    trigger.mark_fired(5)
    state_path = tmp_path / "critic_state.json"
    assert state_path.exists()
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["last_critic_finding_count"] == 5
    assert "last_critic_at" in data
    # Must be a parseable ISO-8601 string
    dt = datetime.fromisoformat(data["last_critic_at"])
    assert dt.tzinfo is not None


# ---------------------------------------------------------------------------
# 12. staged_findings_for_review returns only post-watermark findings
# ---------------------------------------------------------------------------


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
# 16. Corrupt state file falls back to epoch defaults
# ---------------------------------------------------------------------------


def test_corrupt_state_file_uses_defaults(tmp_path: Path) -> None:
    state_path = tmp_path / "critic_state.json"
    state_path.write_text("not valid json", encoding="utf-8")
    trigger = _make_trigger(tmp_path, interval_findings=5)
    # Fresh defaults: count=0 elapsed=epoch → 5 findings should fire
    assert trigger.should_fire(5) is True
