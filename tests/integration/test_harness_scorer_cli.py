"""CLI + helper + edge-case tests for harness.scorer (split from test_harness_scorer.py)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

_EVIDENCE = Path(__file__).resolve().parents[1] / "fixtures" / "mock-evidence" / "case-001"

pytestmark = pytest.mark.skipif(
    shutil.which("find") is None or shutil.which("grep") is None,
    reason="requires POSIX find + grep on PATH",
)


def _gt(id: str, substrings: list[str], dataset_id: str = "nitroba") -> object:
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


class TestCLI:
    def test_missing_baseline_exits_3(self, tmp_path: Path) -> None:
        """--baseline pointing to missing file → exit code 3 with stderr mention."""
        from harness import scorer as scorer_module

        sw = tmp_path / "sw.json"
        sw.write_text("{}")
        rc = scorer_module.main(
            [
                "--dataset",
                "nitroba",
                "--baseline",
                str(tmp_path / "missing.json"),
                "--silentwitness",
                str(sw),
                "--evidence",
                str(_EVIDENCE),
            ]
        )
        assert rc == 3

    def test_empty_ground_truth_exits_4(self, tmp_path: Path) -> None:
        """case-trapdoor (empty GT) → exit code 4, stderr mentions 'ground truth returned empty'."""
        import io

        from harness import scorer as scorer_module

        b = tmp_path / "b.json"
        s = tmp_path / "s.json"
        b.write_text('{"findings": []}')
        s.write_text('{"findings": []}')

        captured_err = io.StringIO()
        with patch("sys.stderr", captured_err):
            rc = scorer_module.main(
                [
                    "--dataset",
                    "case-trapdoor",
                    "--baseline",
                    str(b),
                    "--silentwitness",
                    str(s),
                    "--evidence",
                    str(_EVIDENCE),
                ]
            )
        assert rc == 4
        assert "ground truth returned empty" in captured_err.getvalue()

    def test_successful_run_writes_json(self, tmp_path: Path) -> None:
        """Happy path writes scoring-*.json to out dir, exit code 0."""
        from harness import scorer as scorer_module

        payload = (
            '{"findings": [], "time_to_first_finding_seconds": null,'
            ' "time_to_handoff_ready_report_seconds": null}'
        )
        b = tmp_path / "b.json"
        s = tmp_path / "s.json"
        b.write_text(payload)
        s.write_text(payload)
        out = tmp_path / "out"
        gt_modules = {"nitroba": "harness.ground_truth.nitroba_parser"}

        with patch("harness.scorer._GT_MODULES", gt_modules):
            rc = scorer_module.main(
                [
                    "--dataset",
                    "nitroba",
                    "--baseline",
                    str(b),
                    "--silentwitness",
                    str(s),
                    "--evidence",
                    str(_EVIDENCE),
                    "--out",
                    str(out),
                ]
            )
        assert rc == 0
        files = list(out.glob("nitroba/scoring-*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text())
        assert data["dataset_id"] == "nitroba"

    def test_unknown_dataset_exits_2(self, tmp_path: Path) -> None:
        """Unknown --dataset value → exit 2 with config/validation message."""
        from harness import scorer as scorer_module

        b = tmp_path / "b.json"
        s = tmp_path / "s.json"
        b.write_text("{}")
        s.write_text("{}")
        rc = scorer_module.main(
            [
                "--dataset",
                "bogus",
                "--baseline",
                str(b),
                "--silentwitness",
                str(s),
                "--evidence",
                str(_EVIDENCE),
            ]
        )
        assert rc == 2


class TestTimeoutAndExamples:
    def test_timeout_indeterminate_marks_not_hallucination(self, tmp_path: Path) -> None:
        """subprocess.TimeoutExpired → hits=-1, NOT classified as HALLUCINATION."""
        import subprocess as sp

        from harness.scorer import classify_finding

        with patch("harness.scorer.subprocess.run", side_effect=sp.TimeoutExpired("find", 60)):
            result = classify_finding(
                {"id": "F-T1", "cited_artifact_paths": ["any.exe"]},
                [],
                _EVIDENCE,
                "baseline",
            )
        # Timeout means indeterminate; -1 sentinel + note surfaces in output
        assert result.classification == "FALSE_POSITIVE"
        assert result.evidence_shellout_hits == -1
        assert any("timed out" in n for n in result.notes)

    def test_multi_cited_partial_hit_yields_true_positive(self) -> None:
        """Real find: one cited path hits, another misses → TRUE_POSITIVE, hits>0 preserved."""
        from harness.scorer import classify_finding

        result = classify_finding(
            {
                "id": "F-MX",
                "text": "Wireshark + ghost",
                "cited_artifact_paths": [
                    r"C:\Program Files\Ethereal\ethereal.exe",
                    r"C:\Tools\NotReal.exe",
                ],
            },
            [_gt("GT-MX", ["ethereal.exe"])],
            _EVIDENCE,
            "baseline",
        )
        assert result.classification == "TRUE_POSITIVE"
        # Audit trail surfaces the path that actually hit, not the miss
        assert result.evidence_shellout_hits is not None and result.evidence_shellout_hits > 0

    def test_basename_starting_with_dash_rejected(self) -> None:
        """Basename starting with '-' is rejected (no find -iname injection per CWE-88)."""
        from harness.scorer import verify_artifact_present_in_evidence

        found, argv, hits = verify_artifact_present_in_evidence("-delete", _EVIDENCE)
        assert found is False
        assert argv == []
        assert hits == 0

    def test_scoring_report_round_trips_json(self, tmp_path: Path) -> None:
        """ScoringReport survives model_dump_json → model_validate_json."""
        from datetime import UTC, datetime

        from harness.scorer import ScoringMetrics, ScoringReport

        def _m(side: str) -> ScoringMetrics:
            return ScoringMetrics(
                dataset_id="nitroba",
                side=side,  # type: ignore[arg-type]
                true_positives=1,
                false_positives=0,
                hallucinations=0,
                false_negatives=0,
                total_findings_emitted=1,
                time_to_first_finding_seconds=5.0,
                time_to_handoff_ready_report_seconds=42.0,
            )

        report = ScoringReport(
            dataset_id="nitroba",
            commit_sha="abc123",
            scored_at=datetime.now(UTC),
            baseline=_m("baseline"),
            silentwitness=_m("silentwitness"),
            classifications=[],
            notes=["test"],
            hallucination_examples=[],
        )
        restored = ScoringReport.model_validate_json(report.model_dump_json())
        assert restored.dataset_id == report.dataset_id
        assert restored.baseline.precision == pytest.approx(1.0)
        assert restored.silentwitness.time_to_handoff_ready_report_seconds == pytest.approx(42.0)

    def test_scoring_report_count_invariant_rejects_mismatch(self) -> None:
        """ScoringReport validator rejects tp+fp+hall != total_findings_emitted."""
        from datetime import UTC, datetime

        from harness.scorer import ScoringMetrics, ScoringReport
        from pydantic import ValidationError

        bad = ScoringMetrics(
            dataset_id="nitroba",
            side="baseline",
            true_positives=2,
            false_positives=0,
            hallucinations=0,
            false_negatives=0,
            total_findings_emitted=5,  # mismatch
            time_to_first_finding_seconds=None,
            time_to_handoff_ready_report_seconds=None,
        )
        good = ScoringMetrics(
            dataset_id="nitroba",
            side="silentwitness",
            true_positives=0,
            false_positives=0,
            hallucinations=0,
            false_negatives=0,
            total_findings_emitted=0,
            time_to_first_finding_seconds=None,
            time_to_handoff_ready_report_seconds=None,
        )
        with pytest.raises(ValidationError, match="counts mismatch"):
            ScoringReport(
                dataset_id="nitroba",
                commit_sha="abc",
                scored_at=datetime.now(UTC),
                baseline=bad,
                silentwitness=good,
                classifications=[],
                notes=[],
                hallucination_examples=[],
            )

    def test_main_missing_evidence_dir_exits_3(self, tmp_path: Path) -> None:
        """evidence_root that doesn't exist → exit 3."""
        from harness import scorer as scorer_module

        b = tmp_path / "b.json"
        s = tmp_path / "s.json"
        b.write_text("{}")
        s.write_text("{}")
        rc = scorer_module.main(
            [
                "--dataset",
                "nitroba",
                "--baseline",
                str(b),
                "--silentwitness",
                str(s),
                "--evidence",
                str(tmp_path / "no-such-dir"),
            ]
        )
        assert rc == 3

    def test_main_malformed_json_exits_3(self, tmp_path: Path) -> None:
        """JSONDecodeError on result file → exit 3 (not 2)."""
        from harness import scorer as scorer_module

        b = tmp_path / "b.json"
        s = tmp_path / "s.json"
        b.write_text("{this is not json")
        s.write_text("{}")
        rc = scorer_module.main(
            [
                "--dataset",
                "nitroba",
                "--baseline",
                str(b),
                "--silentwitness",
                str(s),
                "--evidence",
                str(_EVIDENCE),
            ]
        )
        assert rc == 3

    def test_get_commit_sha_fallbacks(self) -> None:
        """get_commit_sha returns sentinels for FileNotFoundError / TimeoutExpired / OSError."""
        import subprocess as sp

        from harness.scorer_helpers import get_commit_sha

        with patch("harness.scorer_helpers.subprocess.run", side_effect=FileNotFoundError):
            assert "git not found" in get_commit_sha()
        with patch(
            "harness.scorer_helpers.subprocess.run", side_effect=sp.TimeoutExpired("git", 10)
        ):
            assert "timed out" in get_commit_sha()
        with patch("harness.scorer_helpers.subprocess.run", side_effect=PermissionError("denied")):
            assert "PermissionError" in get_commit_sha()
        with patch(
            "harness.scorer_helpers.subprocess.run",
            return_value=type("R", (), {"returncode": 1, "stdout": ""})(),
        ):
            assert "git exit 1" in get_commit_sha()

    def test_check_mount_writable_oserror_emits_note(self, tmp_path: Path) -> None:
        """statvfs failure appends a note instead of being silent."""
        from harness.scorer_helpers import check_mount_writable

        notes: list[str] = []
        with patch("harness.scorer_helpers.os.statvfs", side_effect=OSError("ENOENT")):
            check_mount_writable(tmp_path, notes)
        assert any("could not statvfs" in n for n in notes)

    def test_safe_findings_rejects_malformed_inputs(self) -> None:
        """safe_findings: non-list dropped; non-dict skipped; bad cited_artifact_paths coerced."""
        from harness.scorer_helpers import safe_findings

        notes: list[str] = []
        out = safe_findings("not-a-list", notes, "baseline")
        assert out == []
        assert any("is not a list" in n for n in notes)

        notes2: list[str] = []
        out2 = safe_findings(
            [{"id": "ok", "cited_artifact_paths": "should-be-list"}, "not-a-dict"],
            notes2,
            "silentwitness",
        )
        # entry 0 coerced (cited→[]), entry 1 skipped
        assert len(out2) == 1
        assert out2[0]["cited_artifact_paths"] == []
        assert any("cited_artifact_paths" in n for n in notes2)
        assert any("not a dict" in n for n in notes2)

    def test_cited_from_argv_branches(self) -> None:
        """cited_from_argv correctly extracts cited substring for find/grep/other."""
        from harness.scorer_helpers import cited_from_argv

        assert cited_from_argv([]) == ""
        assert cited_from_argv(["find", "/ev", "-iname", "x.exe"]) == "x.exe"
        assert cited_from_argv(["grep", "-r", "-l", "-F", "needle", "/ev"]) == "needle"
        assert cited_from_argv(["unknown", "fallback"]) == "fallback"

    def test_hallucination_examples_sorted_by_length(self) -> None:
        """score_run hallucination_examples sorted longest first, capped at 10."""
        from harness.scorer import classify_finding
        from harness.scorer_helpers import top_hallucination_examples

        findings = [
            {"id": f"F-H{i}", "cited_artifact_paths": [f"C:\\Tools\\NotReal{i}{'x' * i}.exe"]}
            for i in range(3)
        ]
        classifications = [classify_finding(f, [], _EVIDENCE, "baseline") for f in findings]
        examples = top_hallucination_examples(classifications, "baseline")
        assert len(examples) == 3
        # Longest cited path first
        lengths = [len(e.cited_artifact_path) for e in examples]
        assert lengths == sorted(lengths, reverse=True)
