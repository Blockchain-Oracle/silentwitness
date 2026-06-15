"""Unit tests for the enforced 5-Key-Questions coverage gate (pure, no agent run)."""

from __future__ import annotations

import json
from pathlib import Path

from silentwitness_agent.coverage import (
    KEY_QUESTIONS,
    analyze_coverage,
    coverage_gap_message,
)


def _write_findings(case_dir: Path, observations: list[dict]) -> None:
    (case_dir / "findings.json").write_text(json.dumps(observations), encoding="utf-8")


def _obs(title: str = "", span: str = "", justification: str = "") -> dict:
    return {
        "observation_id": "O-1",
        "title": title,
        "cited_spans": [{"record_id": 1, "span_text": span}],
        "interpretations": [{"interpretation_id": "I-1", "justification": justification}],
    }


def test_empty_case_covers_nothing(tmp_path: Path) -> None:
    report = analyze_coverage(tmp_path)  # no findings.json
    assert report.covered == frozenset()
    assert len(report.uncovered) == 5
    assert not report.is_complete


def test_brute_force_only_leaves_what_where_when_open(tmp_path: Path) -> None:
    # The exact Phase-9 failure: one brute-force observation, nothing else. It touches the
    # targeted account (Q1) and the access vector (Q4) — matching the run's 2 GT hits —
    # but leaves what-was-taken / where-transferred / when unanswered.
    _write_findings(tmp_path, [_obs(span="EventID=4625 TargetUserName=BACKUPADMIN")])
    report = analyze_coverage(tmp_path)
    assert {"Q1", "Q4"} <= report.covered
    assert {q.qid for q in report.uncovered} == {"Q2", "Q3", "Q5"}


def test_cloud_exfil_observation_covers_q3(tmp_path: Path) -> None:
    _write_findings(tmp_path, [_obs(span="LNK target=C:\\Users\\x\\OneDrive\\secret.docx")])
    covered = analyze_coverage(tmp_path).covered
    assert "Q3" in covered  # where transferred
    assert "Q2" in covered  # .docx also signals what-taken


def test_q5_covered_by_iso_date(tmp_path: Path) -> None:
    _write_findings(tmp_path, [_obs(justification="activity on 2020-11-13 in the window")])
    assert "Q5" in analyze_coverage(tmp_path).covered


def test_all_five_covered_completes(tmp_path: Path) -> None:
    _write_findings(
        tmp_path,
        [
            _obs(span="EventID=4624 LogonType=10 mstsc RDP"),  # Q4 + Q1(logon)
            _obs(span="OneDrive upload"),  # Q3
            _obs(span="report.docx opened recent"),  # Q2
            _obs(justification="occurred 2020-11-13"),  # Q5
        ],
    )
    report = analyze_coverage(tmp_path)
    assert report.is_complete
    assert coverage_gap_message(report) is None


def test_gap_message_names_open_questions_and_hints(tmp_path: Path) -> None:
    _write_findings(tmp_path, [_obs(span="EventID=4625 brute force")])
    msg = coverage_gap_message(analyze_coverage(tmp_path))
    assert msg is not None
    assert "Q3" in msg and "Q5" in msg
    assert "SRUM" in msg or "cloud" in msg  # artifact hint surfaced
    assert "Q4" not in msg  # the covered question is not listed as a gap


def test_malformed_findings_json_is_safe(tmp_path: Path) -> None:
    (tmp_path / "findings.json").write_text("{not json", encoding="utf-8")
    report = analyze_coverage(tmp_path)
    assert len(report.uncovered) == 5  # safe default: nothing covered


def test_question_set_is_the_five() -> None:
    assert {q.qid for q in KEY_QUESTIONS} == {"Q1", "Q2", "Q3", "Q4", "Q5"}
