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


def test_q5_needs_a_window_not_a_single_date(tmp_path: Path) -> None:
    # A single incidental date must NOT satisfy "when" (nearly every event carries one).
    _write_findings(tmp_path, [_obs(span="EventID=4624 at 2020-11-13T08:00:00Z")])
    assert "Q5" not in analyze_coverage(tmp_path).covered
    # Two distinct dates (a window) — or a temporal keyword — does.
    _write_findings(
        tmp_path,
        [_obs(span="logon 2020-11-10"), _obs(span="exfil 2020-11-13")],
    )
    assert "Q5" in analyze_coverage(tmp_path).covered


def test_q5_covered_by_temporal_keyword(tmp_path: Path) -> None:
    _write_findings(tmp_path, [_obs(justification="the intrusion window spans the weekend")])
    assert "Q5" in analyze_coverage(tmp_path).covered


def test_all_five_covered_completes(tmp_path: Path) -> None:
    _write_findings(
        tmp_path,
        [
            _obs(span="EventID=4624 LogonType=10 mstsc RDP"),  # Q4 + Q1(logon)
            _obs(span="OneDrive upload"),  # Q3
            _obs(span="report.docx shortcut"),  # Q2
            _obs(justification="timeline: 2020-11-10 to 2020-11-13"),  # Q5 (window)
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


def test_gate_cap_below_retry_budget_invariant() -> None:
    # Each coverage bounce consumes one shared output-retry; the cap must leave headroom
    # under the budget so tool/output retries don't trip pydantic-ai's exhaustion error.
    from silentwitness_agent.investigator import _MAX_COVERAGE_GATE_ATTEMPTS, _OUTPUT_RETRIES

    assert _MAX_COVERAGE_GATE_ATTEMPTS < _OUTPUT_RETRIES


def test_singular_cited_span_fallback_key(tmp_path: Path) -> None:
    # Older records use "cited_span" (singular); coverage must read it too.
    _write_findings(
        tmp_path,
        [{"observation_id": "O-1", "cited_span": [{"record_id": 1, "span_text": "OneDrive"}]}],
    )
    assert "Q3" in analyze_coverage(tmp_path).covered


def test_junk_list_items_are_skipped(tmp_path: Path) -> None:
    (tmp_path / "findings.json").write_text(
        json.dumps([{}, "not-a-dict", None, {"title": "   "}]), encoding="utf-8"
    )
    report = analyze_coverage(tmp_path)  # must not crash; nothing covered
    assert len(report.uncovered) == 5


def test_keyword_in_interpretation_justification_covers(tmp_path: Path) -> None:
    # Coverage can come from the interpretation justification, not only span text.
    _write_findings(tmp_path, [_obs(justification="the actor used rclone to a remote host")])
    assert "Q3" in analyze_coverage(tmp_path).covered  # rclone


def test_scans_past_nonmatching_observations(tmp_path: Path) -> None:
    _write_findings(
        tmp_path,
        [_obs(span="benign noise"), _obs(span="unrelated"), _obs(span="Dropbox sync")],
    )
    assert "Q3" in analyze_coverage(tmp_path).covered  # the 3rd obs matches
