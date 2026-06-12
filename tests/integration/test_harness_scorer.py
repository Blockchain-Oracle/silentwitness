"""Integration tests for harness/scorer.py — real find/grep shell-outs, no mocks."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

_EVIDENCE = Path(__file__).resolve().parents[1] / "fixtures" / "mock-evidence" / "case-001"
_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

pytestmark = pytest.mark.skipif(
    shutil.which("find") is None or shutil.which("grep") is None,
    reason="requires POSIX find + grep on PATH (per spec, classification tests must shell out)",
)


def _gt(
    id: str,
    substrings: list[str],
    dataset_id: str = "nitroba",
) -> object:
    from harness.ground_truth.schema import GroundTruthFinding

    return GroundTruthFinding(
        id=id,
        dataset_id=dataset_id,  # type: ignore[arg-type]
        category="file_artifact",
        summary=f"GT {id}",
        expected_artifact_substrings=substrings,
        expected_path_globs=[],
        supporting_question_id=None,
        source="hand_crafted",
        source_url=None,
        source_excerpt=None,
    )


class TestVerifyArtifactPresentInEvidence:
    def test_existing_file_returns_hit(self) -> None:
        """find ethereal.exe in mock-evidence returns ≥1 hit."""
        from harness.scorer import verify_artifact_present_in_evidence

        found, argv, hits = verify_artifact_present_in_evidence(
            r"C:\Program Files\Ethereal\ethereal.exe", _EVIDENCE
        )
        assert found is True
        assert hits >= 1
        assert argv[0] == "find"

    def test_missing_file_returns_zero_hits(self) -> None:
        """find NotReal.exe in mock-evidence returns 0 hits (HALLUCINATION trigger)."""
        from harness.scorer import verify_artifact_present_in_evidence

        found, _argv, hits = verify_artifact_present_in_evidence(r"C:\Tools\NotReal.exe", _EVIDENCE)
        assert found is False
        assert hits == 0

    def test_case_insensitive_svchost(self) -> None:
        """find SVCHOST.EXE case-insensitively matches svchost.exe fixture file."""
        from harness.scorer import verify_artifact_present_in_evidence

        found, _, hits = verify_artifact_present_in_evidence("svchost.exe", _EVIDENCE)
        assert found is True
        assert hits >= 1

    def test_empty_basename_returns_zero(self) -> None:
        """Cited artifact with empty basename returns (False, [], 0)."""
        from harness.scorer import verify_artifact_present_in_evidence

        found, argv, hits = verify_artifact_present_in_evidence("", _EVIDENCE)
        assert found is False
        assert argv == []
        assert hits == 0

    def test_glob_metachar_uses_grep(self) -> None:
        """Basename with '[' routes to grep -F (literal match)."""
        from harness.scorer import verify_artifact_present_in_evidence

        _, argv, _ = verify_artifact_present_in_evidence("[weird].exe", _EVIDENCE)
        assert argv[0] == "grep"


class TestClassifyFinding:
    def test_hallucination_no_cited_paths(self) -> None:
        """Finding with no cited_artifact_paths → HALLUCINATION (zero provenance)."""
        from harness.scorer import classify_finding

        result = classify_finding(
            {"id": "F-001", "text": "Some claim", "cited_artifact_paths": []},
            [_gt("GT-001", ["NotReal.exe"])],
            _EVIDENCE,
            "baseline",
        )
        assert result.classification == "HALLUCINATION"
        assert result.reason == "CITED_ARTIFACT_NOT_PRESENT"
        assert result.evidence_shellout_hits == 0

    def test_hallucination_file_not_on_evidence(self) -> None:
        """Finding citing NotReal.exe → HALLUCINATION; argv starts with ['find', ...]."""
        from harness.scorer import classify_finding

        result = classify_finding(
            {"id": "F-002", "cited_artifact_paths": [r"C:\Tools\NotReal.exe"]},
            [],
            _EVIDENCE,
            "baseline",
        )
        assert result.classification == "HALLUCINATION"
        assert result.reason == "CITED_ARTIFACT_NOT_PRESENT"
        assert result.evidence_shellout_hits == 0
        assert result.evidence_shellout_argv is not None
        assert result.evidence_shellout_argv[:2] == ["find", str(_EVIDENCE)]
        assert "NotReal.exe" in " ".join(result.evidence_shellout_argv)

    def test_true_positive_gt_substring_in_text(self) -> None:
        """MAC substring in finding text → TRUE_POSITIVE when GT lists that substring."""
        from harness.scorer import classify_finding

        result = classify_finding(
            {
                "id": "F-003",
                "text": "Device 00:02:B3:DD:00:A2 seen",
                "cited_artifact_paths": ["network-config.txt"],
            },
            [_gt("GT-NHC-005", ["00:02:B3:DD:00:A2"])],
            _EVIDENCE,
            "silentwitness",
        )
        assert result.classification == "TRUE_POSITIVE"
        assert result.matched_ground_truth_id == "GT-NHC-005"

    def test_true_positive_gt_substring_in_cited_path(self) -> None:
        """GT substring matches the cited_artifact_path directly."""
        from harness.scorer import classify_finding

        result = classify_finding(
            {
                "id": "F-004",
                "text": "Wireshark found",
                "cited_artifact_paths": [r"C:\Program Files\Ethereal\ethereal.exe"],
            },
            [_gt("GT-ETH-001", ["ethereal.exe"])],
            _EVIDENCE,
            "silentwitness",
        )
        assert result.classification == "TRUE_POSITIVE"
        assert result.matched_ground_truth_id == "GT-ETH-001"

    def test_false_positive_artifact_present_but_no_gt_match(self) -> None:
        """Artifact present in evidence but no GT match → FALSE_POSITIVE."""
        from harness.scorer import classify_finding

        result = classify_finding(
            {"id": "F-005", "text": "notepad found", "cited_artifact_paths": ["notepad.exe"]},
            [_gt("GT-001", ["cmd.exe"])],  # GT only matches cmd.exe
            _EVIDENCE,
            "baseline",
        )
        assert result.classification == "FALSE_POSITIVE"
        assert result.reason == "CITED_ARTIFACT_PRESENT_BUT_GT_MISS"
        assert result.matched_ground_truth_id is None

    def test_title_field_used_when_text_absent(self) -> None:
        """SW findings use 'title' not 'text'; GT substring in title → TRUE_POSITIVE."""
        from harness.scorer import classify_finding

        result = classify_finding(
            {"id": "F-006", "title": "cmd.exe found", "cited_artifact_paths": ["cmd.exe"]},
            [_gt("GT-002", ["cmd.exe"])],
            _EVIDENCE,
            "silentwitness",
        )
        assert result.classification == "TRUE_POSITIVE"


class TestComputeFalseNegatives:
    def test_uncovered_gt_produces_fn(self) -> None:
        """GT-NHC-005 not covered by any finding → one FALSE_NEGATIVE row."""
        from harness.scorer import compute_false_negatives

        fns = compute_false_negatives(
            [_gt("GT-NHC-005", ["00:02:B3:DD:00:A2"])],
            [{"id": "F-001", "text": "Ethereal traffic", "cited_artifact_paths": []}],
            "baseline",
        )
        assert len(fns) == 1
        assert fns[0].classification == "FALSE_NEGATIVE"
        assert fns[0].matched_ground_truth_id == "GT-NHC-005"
        assert fns[0].finding_id == "FN-GT-NHC-005"

    def test_covered_gt_not_in_fn_list(self) -> None:
        """GT covered by a finding → no FALSE_NEGATIVE emitted for it."""
        from harness.scorer import compute_false_negatives

        fns = compute_false_negatives(
            [_gt("GT-001", ["ethereal.exe"])],
            [{"id": "F-001", "text": "ethereal.exe captured", "cited_artifact_paths": []}],
            "baseline",
        )
        assert fns == []


class TestScoringMetrics:
    def test_precision_recall_hallucination_rate(self) -> None:
        """TP=7, FP=1, HALL=2, FN=3 → precision=0.7, recall=0.7, hallucination_rate=0.2."""
        from harness.scorer import ScoringMetrics

        m = ScoringMetrics(
            dataset_id="nitroba",
            side="baseline",
            true_positives=7,
            false_positives=1,
            hallucinations=2,
            false_negatives=3,
            time_to_first_finding_seconds=None,
            time_to_handoff_ready_report_seconds=None,
            total_findings_emitted=10,
        )
        assert m.precision == pytest.approx(0.7)
        assert m.recall == pytest.approx(0.7)
        assert m.hallucination_rate == pytest.approx(0.2)

    def test_zero_denominator_precision_is_zero(self) -> None:
        """All-zero counts → precision 0.0, not ZeroDivisionError."""
        from harness.scorer import ScoringMetrics

        m = ScoringMetrics(
            dataset_id="nitroba",
            side="silentwitness",
            true_positives=0,
            false_positives=0,
            hallucinations=0,
            false_negatives=0,
            time_to_first_finding_seconds=None,
            time_to_handoff_ready_report_seconds=None,
            total_findings_emitted=0,
        )
        assert m.precision == 0.0
        assert m.recall == 0.0
        assert m.hallucination_rate == 0.0

    def test_time_fields_pass_through(self) -> None:
        """time_to_first_finding_seconds and time_to_handoff_ready_report_seconds are verbatim."""
        from harness.scorer import ScoringMetrics

        m = ScoringMetrics(
            dataset_id="nitroba",
            side="baseline",
            true_positives=1,
            false_positives=0,
            hallucinations=0,
            false_negatives=0,
            time_to_first_finding_seconds=42.5,
            time_to_handoff_ready_report_seconds=301.0,
            total_findings_emitted=1,
        )
        assert m.time_to_first_finding_seconds == pytest.approx(42.5)
        assert m.time_to_handoff_ready_report_seconds == pytest.approx(301.0)
