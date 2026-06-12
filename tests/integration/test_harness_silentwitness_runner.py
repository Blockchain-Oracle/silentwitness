"""Integration tests for harness/silentwitness — run_silentwitness and CLI."""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "case-harness"


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

    def test_case_dir_none_auto_creates_note(self, tmp_path: Path) -> None:
        """run_silentwitness with case_dir=None adds auto-created note to result."""
        from harness.silentwitness.runner import SilentWitnessRunConfig, run_silentwitness

        config = SilentWitnessRunConfig(dataset_id="nitroba", evidence_path=tmp_path)
        proc_mock = _make_proc(returncode=0)

        with (
            patch("harness.silentwitness.runner.subprocess.Popen", return_value=proc_mock),
            patch("harness.silentwitness.runner.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="abc\n")
            result = run_silentwitness(config)

        assert any("auto-created case_dir" in n for n in result.notes)

    def test_handoff_not_reached_note(self, tmp_path: Path) -> None:
        """Without report.md Executive Summary, handoff-not-reached note is appended."""
        from harness.silentwitness.runner import SilentWitnessRunConfig, run_silentwitness

        config = SilentWitnessRunConfig(
            dataset_id="nitroba", evidence_path=tmp_path, case_dir=tmp_path
        )
        proc_mock = _make_proc(returncode=0)

        with (
            patch("harness.silentwitness.runner.subprocess.Popen", return_value=proc_mock),
            patch("harness.silentwitness.runner.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="abc\n")
            result = run_silentwitness(config)

        assert any("handoff-ready threshold not reached" in n for n in result.notes)


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

    def test_runner_error_exits_5(self, tmp_path: Path) -> None:
        """CLI returns exit code 5 when run_silentwitness raises an exception."""
        from harness.silentwitness import runner as runner_module

        evidence = tmp_path / "ev"
        evidence.mkdir()
        with patch(
            "harness.silentwitness.runner.run_silentwitness",
            side_effect=RuntimeError("boom"),
        ):
            rc = runner_module.main(["--dataset", "nitroba", "--evidence", str(evidence)])
        assert rc == 5

    def test_nonzero_proc_returncode_exits_5(self, tmp_path: Path) -> None:
        """CLI returns exit code 5 when investigator subprocess exits non-zero."""
        from harness.silentwitness import runner as runner_module

        evidence = tmp_path / "ev"
        evidence.mkdir()
        proc_mock = _make_proc(returncode=1)

        with (
            patch("harness.silentwitness.runner.subprocess.Popen", return_value=proc_mock),
            patch("harness.silentwitness.runner.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="abc\n")
            rc = runner_module.main(
                [
                    "--dataset",
                    "nitroba",
                    "--evidence",
                    str(evidence),
                    "--case-dir",
                    str(tmp_path),
                ]
            )
        assert rc == 5
