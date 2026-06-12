"""Integration tests for harness/silentwitness — case_dir_reader and run_silentwitness."""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "case-harness"


# ---------------------------------------------------------------------------
# case_dir_reader — reader functions against the seeded fixture
# ---------------------------------------------------------------------------


class TestReadFindingsJson:
    def test_returns_at_least_five_findings(self) -> None:
        """read_findings_json returns ≥5 SwFinding objects from the fixture."""
        from harness.silentwitness.case_dir_reader import read_findings_json

        findings = read_findings_json(_FIXTURE)
        assert len(findings) >= 5

    def test_finding_ids_are_f_prefix(self) -> None:
        """Every returned SwFinding.id starts with 'F-'."""
        from harness.silentwitness.case_dir_reader import read_findings_json

        findings = read_findings_json(_FIXTURE)
        assert all(f.id.startswith("F-") for f in findings)

    def test_cited_audit_ids_propagated_from_observation(self) -> None:
        """cited_audit_ids on SwFinding are lifted from the linked observation record."""
        from harness.silentwitness.case_dir_reader import read_findings_json

        findings = read_findings_json(_FIXTURE)
        f1 = next(f for f in findings if f.id == "F-001")
        assert "sift-harness-20260612-001" in f1.cited_audit_ids

    def test_missing_findings_json_returns_empty(self, tmp_path: Path) -> None:
        """read_findings_json returns [] when findings.json does not exist."""
        from harness.silentwitness.case_dir_reader import read_findings_json

        assert read_findings_json(tmp_path) == []


class TestReadHypothesisJsonl:
    def test_returns_at_least_eight_events(self) -> None:
        """read_hypothesis_jsonl returns ≥8 SwHypothesisEvent objects."""
        from harness.silentwitness.case_dir_reader import read_hypothesis_jsonl

        events = read_hypothesis_jsonl(_FIXTURE)
        assert len(events) >= 8

    def test_exactly_two_pivots(self) -> None:
        """Exactly 2 hypothesis events have type='pivot'."""
        from harness.silentwitness.case_dir_reader import read_hypothesis_jsonl

        events = read_hypothesis_jsonl(_FIXTURE)
        pivots = [e for e in events if e.type == "pivot"]
        assert len(pivots) == 2

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        from harness.silentwitness.case_dir_reader import read_hypothesis_jsonl

        assert read_hypothesis_jsonl(tmp_path) == []


class TestReadAuditJsonl:
    def test_merges_across_files_returns_at_least_twelve(self) -> None:
        """read_audit_jsonl merges memory.jsonl + disk.jsonl + findings.jsonl (≥12 entries)."""
        from harness.silentwitness.case_dir_reader import read_audit_jsonl

        tool_calls, _notes = read_audit_jsonl(_FIXTURE)
        assert len(tool_calls) >= 12

    def test_skips_hypothesis_and_critic_files(self) -> None:
        """read_audit_jsonl does not include hypothesis or critic JSONL entries."""
        from harness.silentwitness.case_dir_reader import read_audit_jsonl

        tool_calls, _ = read_audit_jsonl(_FIXTURE)
        tool_names = {tc.tool for tc in tool_calls}
        assert "form" not in tool_names
        assert "agree" not in tool_names

    def test_missing_audit_dir_returns_empty(self, tmp_path: Path) -> None:
        from harness.silentwitness.case_dir_reader import read_audit_jsonl

        tool_calls, notes = read_audit_jsonl(tmp_path)
        assert tool_calls == []
        assert notes == []


class TestCountGapsInReport:
    def test_returns_exactly_three(self) -> None:
        """count_gaps_in_report returns exactly 3 for the fixture report.md."""
        from harness.silentwitness.case_dir_reader import count_gaps_in_report

        assert count_gaps_in_report(_FIXTURE / "report.md") == 3

    def test_returns_zero_for_missing_file(self, tmp_path: Path) -> None:
        from harness.silentwitness.case_dir_reader import count_gaps_in_report

        assert count_gaps_in_report(tmp_path / "report.md") == 0

    def test_returns_zero_when_no_gaps_heading(self, tmp_path: Path) -> None:
        report = tmp_path / "report.md"
        report.write_text("## Executive Summary\nSome content.\n")
        from harness.silentwitness.case_dir_reader import count_gaps_in_report

        assert count_gaps_in_report(report) == 0


# ---------------------------------------------------------------------------
# run_silentwitness — subprocess mocked against the fixture case dir
# ---------------------------------------------------------------------------


def _make_proc(returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.poll = MagicMock(return_value=returncode)
    proc.wait = MagicMock(return_value=returncode)
    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    proc.stdout = io.BytesIO(b"")
    return proc


class TestRunSilentwitness:
    def test_successful_run_returns_result_with_fixture_data(self, tmp_path: Path) -> None:
        """run_silentwitness with mocked subprocess returns populated result from fixture."""
        from harness.silentwitness.runner import SilentWitnessRunConfig, run_silentwitness

        # Use fixture as the pre-seeded case dir
        config = SilentWitnessRunConfig(
            dataset_id="nitroba",
            evidence_path=tmp_path,  # doesn't matter; subprocess is mocked
            case_dir=_FIXTURE,
        )
        proc_mock = _make_proc(returncode=0)

        with patch("harness.silentwitness.runner.subprocess.Popen", return_value=proc_mock):
            with patch("harness.silentwitness.runner.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="abc123\n")
                result = run_silentwitness(config)

        assert len(result.findings) >= 5
        assert len(result.hypothesis_events) >= 8
        assert len(result.pivots) == 2
        assert len(result.tool_calls) >= 12
        assert len(result.critic_verdicts) == 2
        assert result.entity_gate_rejections == 1
        assert result.epistemic_honesty_count == 3
        assert result.time_to_handoff_ready_report_seconds is not None
        assert result.report_md_path is not None
        assert result.report_md_sha256 is not None
        assert result.exit_code == 0

    def test_timeout_sets_exit_code_4_and_notes(self, tmp_path: Path) -> None:
        """run_silentwitness returns exit_code=4 and notes contain 'silentwitness timeout'."""
        from harness.silentwitness.runner import SilentWitnessRunConfig, run_silentwitness

        config = SilentWitnessRunConfig(
            dataset_id="nitroba",
            evidence_path=tmp_path,
            case_dir=_FIXTURE,
            timeout_seconds=1,
        )

        call_count = 0

        def monotonic_fast() -> float:
            nonlocal call_count
            call_count += 1
            return 0.0 if call_count == 1 else 9999.0

        proc_mock = _make_proc()
        # Make poll() return None once (so loop body runs) then 0 (done)
        proc_mock.poll.side_effect = [None, 0]

        with (
            patch("harness.silentwitness.runner.subprocess.Popen", return_value=proc_mock),
            patch("harness.silentwitness.runner.subprocess.run") as mock_run,
            patch("harness.silentwitness.runner.time.monotonic", side_effect=monotonic_fast),
            patch("harness.silentwitness.runner.time.sleep"),
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="abc123\n")
            result = run_silentwitness(config)

        assert result.exit_code == 4
        assert any("silentwitness timeout" in note for note in result.notes)
        proc_mock.terminate.assert_called_once()

    def test_result_round_trips_json(self, tmp_path: Path) -> None:
        """SilentWitnessRunResult survives model_dump_json → model_validate_json."""
        from harness.silentwitness.runner import (
            SilentWitnessRunConfig,
            SilentWitnessRunResult,
            run_silentwitness,
        )

        config = SilentWitnessRunConfig(
            dataset_id="nitroba",
            evidence_path=tmp_path,
            case_dir=_FIXTURE,
        )
        proc_mock = _make_proc(returncode=0)

        with patch("harness.silentwitness.runner.subprocess.Popen", return_value=proc_mock):
            with patch("harness.silentwitness.runner.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="abc123\n")
                result = run_silentwitness(config)

        restored = SilentWitnessRunResult.model_validate_json(result.model_dump_json())
        assert restored.dataset_id == result.dataset_id
        assert restored.exit_code == result.exit_code
        assert len(restored.findings) == len(result.findings)
        assert len(restored.pivots) == len(result.pivots)
        assert restored.entity_gate_rejections == result.entity_gate_rejections

    def test_result_written_to_output_dir(self, tmp_path: Path) -> None:
        """run_silentwitness result serializes correctly; main() writes file to out dir."""
        from harness.silentwitness import runner as runner_module

        evidence = tmp_path / "evidence"
        evidence.mkdir()
        out_dir = tmp_path / "results"

        proc_mock = _make_proc(returncode=0)

        with (
            patch("harness.silentwitness.runner.subprocess.Popen", return_value=proc_mock),
            patch("harness.silentwitness.runner.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="abc123\n")
            rc = runner_module.main(
                [
                    "--dataset",
                    "nitroba",
                    "--evidence",
                    str(evidence),
                    "--case-dir",
                    str(_FIXTURE),
                    "--out",
                    str(out_dir),
                ]
            )

        assert rc == 0
        result_files = list(out_dir.glob("nitroba/silentwitness-*.json"))
        assert len(result_files) == 1
        data = json.loads(result_files[0].read_text())
        from harness.silentwitness.runner import SilentWitnessRunResult

        validated = SilentWitnessRunResult.model_validate(data)
        assert validated.time_to_handoff_ready_report_seconds is not None


# ---------------------------------------------------------------------------
# CLI edge cases
# ---------------------------------------------------------------------------


class TestCLI:
    def test_nonexistent_evidence_exits_2(self, tmp_path: Path) -> None:
        """CLI returns exit code 2 when evidence_path does not exist."""
        from harness.silentwitness import runner as runner_module

        rc = runner_module.main(
            ["--dataset", "nitroba", "--evidence", str(tmp_path / "no-such-dir")]
        )
        assert rc == 2

    def test_invalid_dataset_exits_2(self, tmp_path: Path) -> None:
        """CLI returns exit code 2 when dataset_id is not in the allowed Literal."""
        evidence = tmp_path / "ev"
        evidence.mkdir()
        from harness.silentwitness import runner as runner_module

        rc = runner_module.main(["--dataset", "INVALID_DATASET", "--evidence", str(evidence)])
        assert rc == 2

    def test_stderr_contains_evidence_path_on_missing_evidence(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """CLI stderr contains 'evidence_path' when evidence dir is missing."""
        from harness.silentwitness import runner as runner_module

        runner_module.main(["--dataset", "nitroba", "--evidence", str(tmp_path / "no-such-dir")])
        captured = capsys.readouterr()
        assert "evidence_path" in captured.err
