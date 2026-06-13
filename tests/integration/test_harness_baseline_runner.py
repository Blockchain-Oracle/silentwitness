"""Integration tests for harness/baseline/runner.py — run_baseline, BaselineRunResult, CLI."""

from __future__ import annotations

import io
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from harness.baseline.runner import (
    BaselineInstallError,
    BaselineRunConfig,
    BaselineRunResult,
    BaselineTimeoutError,
    run_baseline,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_popen(stdout_lines: list[bytes], returncode: int = 0) -> MagicMock:
    """Return a Popen mock whose stdout yields the given lines then EOF."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = io.BytesIO(b"".join(stdout_lines))
    proc.wait = MagicMock(return_value=returncode)
    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    return proc


def _make_config(evidence_path: Path, **kwargs: object) -> BaselineRunConfig:
    return BaselineRunConfig(
        dataset_id="nitroba",
        evidence_path=evidence_path,
        **kwargs,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# run_baseline
# ---------------------------------------------------------------------------


class TestRunBaseline:
    def _fake_sift_bin(self, work_dir: Path) -> Path:
        sift_dir = work_dir / "protocol-sift" / "bin"
        sift_dir.mkdir(parents=True)
        sift_bin = sift_dir / "protocol-sift"
        sift_bin.touch()
        return sift_bin

    def test_parses_findings_and_tool_calls(self, tmp_path: Path) -> None:
        """run_baseline parses finding and tool_call events from subprocess stdout."""
        evidence = tmp_path / "evidence"
        evidence.mkdir()
        work_dir = tmp_path / "work"
        self._fake_sift_bin(work_dir)

        finding_line = (
            json.dumps(
                {
                    "type": "finding",
                    "id": "f1",
                    "text": "Suspicious process",
                    "cited_artifact_paths": ["mem.dmp"],
                }
            ).encode()
            + b"\n"
        )
        tool_line = (
            json.dumps(
                {
                    "type": "tool_call",
                    "seq": 1,
                    "tool_name": "volatility",
                    "argv": ["windows.pslist"],
                    "elapsed_ms": 200,
                    "exit_code": 0,
                }
            ).encode()
            + b"\n"
        )
        noise = b"not-json\n"

        popen_mock = _make_popen([finding_line, tool_line, noise])

        config = _make_config(evidence, work_dir=work_dir)
        with (
            patch("harness.baseline.runner.subprocess.run") as mock_run,
            patch("harness.baseline.runner.subprocess.Popen", return_value=popen_mock),
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="HEAD\n")
            result = run_baseline(config)

        assert len(result.findings) == 1
        assert result.findings[0].id == "f1"
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "volatility"
        # Non-JSON line should be counted in notes.
        assert any("skipped" in note for note in result.notes)

    def test_timeout_terminates_and_kills_process(self, tmp_path: Path) -> None:
        """run_baseline raises BaselineTimeoutError and escalates terminate→kill."""
        evidence = tmp_path / "evidence"
        evidence.mkdir()
        work_dir = tmp_path / "work"
        self._fake_sift_bin(work_dir)

        popen_mock = _make_popen([b"line\n"] * 5)
        # Simulate proc.wait(timeout=5) raising TimeoutExpired → triggers proc.kill().
        popen_mock.wait.side_effect = [
            subprocess.TimeoutExpired(cmd=[], timeout=5),  # first wait in timeout path
            0,  # second wait after kill in timeout path
            0,  # finally block wait
        ]

        config = _make_config(evidence, work_dir=work_dir, timeout_seconds=1)

        call_count = 0

        def fast_clock() -> float:
            nonlocal call_count
            call_count += 1
            # Call 1 sets t0; calls 2-3 are offset and timeout-check per line.
            return 0.0 if call_count <= 2 else 999.0

        with (
            patch("harness.baseline.runner.subprocess.run") as mock_run,
            patch("harness.baseline.runner.subprocess.Popen", return_value=popen_mock),
            patch("harness.baseline.runner.time.monotonic", side_effect=fast_clock),
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="HEAD\n")
            with pytest.raises(BaselineTimeoutError):
                run_baseline(config)

        popen_mock.terminate.assert_called_once()
        popen_mock.kill.assert_called_once()

    def test_plan_mode_flag_used_when_supported(self, tmp_path: Path) -> None:
        """run_baseline includes --plan-mode in the command when sift binary supports it."""
        evidence = tmp_path / "evidence"
        evidence.mkdir()
        work_dir = tmp_path / "work"
        self._fake_sift_bin(work_dir)

        popen_mock = _make_popen([])
        captured_cmd: list[list[str]] = []

        def fake_popen(cmd: list[str], **_: object) -> MagicMock:
            captured_cmd.append(cmd)
            return popen_mock

        with (
            patch("harness.baseline.runner.subprocess.run") as mock_run,
            patch("harness.baseline.runner.subprocess.Popen", side_effect=fake_popen),
        ):
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="abc123\n"),
                MagicMock(returncode=0, stdout="--plan-mode  Run in plan mode\n", stderr=""),
            ]
            result = run_baseline(_make_config(evidence, work_dir=work_dir))

        assert "--plan-mode" in captured_cmd[0]
        assert result.notes == []

    def test_dry_run_fallback_noted_and_in_command(self, tmp_path: Path) -> None:
        """run_baseline uses --dry-run in the command and records a note when --plan-mode absent."""
        evidence = tmp_path / "evidence"
        evidence.mkdir()
        work_dir = tmp_path / "work"
        self._fake_sift_bin(work_dir)

        popen_mock = _make_popen([])
        captured_cmd: list[list[str]] = []

        def fake_popen(cmd: list[str], **_: object) -> MagicMock:
            captured_cmd.append(cmd)
            return popen_mock

        with (
            patch("harness.baseline.runner.subprocess.run") as mock_run,
            patch("harness.baseline.runner.subprocess.Popen", side_effect=fake_popen),
        ):
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="abc123\n"),
                MagicMock(returncode=0, stdout="--dry-run  Dry run\n", stderr=""),
            ]
            result = run_baseline(_make_config(evidence, work_dir=work_dir))

        assert "--dry-run" in captured_cmd[0]
        assert any("dry-run" in note for note in result.notes)


# ---------------------------------------------------------------------------
# BaselineRunResult round-trip
# ---------------------------------------------------------------------------


class TestBaselineRunResultRoundTrip:
    def test_model_dump_json_round_trips(self, tmp_path: Path) -> None:
        """BaselineRunResult survives model_dump_json → model_validate_json without data loss."""
        from harness.baseline.runner import BaselineFinding, BaselineToolCall

        now = datetime.now(UTC)
        stdout_path = tmp_path / "out.stdout"
        stderr_path = tmp_path / "out.stderr"
        stdout_path.touch()
        stderr_path.touch()

        original = BaselineRunResult(
            dataset_id="nitroba",
            started_at=now,
            finished_at=now,
            elapsed_seconds=12.5,
            exit_code=0,
            model="anthropic:claude-opus-4-7",
            temperature=0.0,
            commit_sha="deadbeef",
            findings=[
                BaselineFinding(
                    type="finding",
                    id="f1",
                    text="Test finding",
                    cited_artifact_paths=["a.bin"],
                    cited_at_offset_seconds=5.0,
                )
            ],
            tool_calls=[
                BaselineToolCall(
                    type="tool_call",
                    seq=0,
                    tool_name="vol",
                    argv=["windows.pslist"],
                    elapsed_ms=100,
                    exit_code=0,
                )
            ],
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            report_md_path=None,
            notes=["test note"],
        )
        restored = BaselineRunResult.model_validate_json(original.model_dump_json())
        assert restored.dataset_id == original.dataset_id
        assert restored.started_at == original.started_at
        assert restored.elapsed_seconds == original.elapsed_seconds
        assert restored.findings[0].id == original.findings[0].id
        assert restored.tool_calls[0].tool_name == original.tool_calls[0].tool_name
        assert restored.notes == original.notes


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCLI:
    def test_nonexistent_evidence_exits_2(self, tmp_path: Path) -> None:
        """CLI returns exit code 2 when evidence dir is missing."""
        from harness.baseline import runner as runner_module

        rc = runner_module.main(
            ["--dataset", "nitroba", "--evidence", str(tmp_path / "no-such-dir")]
        )
        assert rc == 2

    def test_invalid_dataset_exits_2(self, tmp_path: Path) -> None:
        """CLI returns exit code 2 when dataset_id is not in the allowed Literal."""
        evidence = tmp_path / "evidence"
        evidence.mkdir()

        from harness.baseline import runner as runner_module

        rc = runner_module.main(["--dataset", "INVALID_DATASET", "--evidence", str(evidence)])
        assert rc == 2

    def test_install_failure_exits_3(self, tmp_path: Path) -> None:
        """CLI returns exit code 3 when install_baseline raises BaselineInstallError."""
        evidence = tmp_path / "evidence"
        evidence.mkdir()

        from harness.baseline import runner as runner_module

        with patch(
            "harness.baseline.runner.install_baseline",
            side_effect=BaselineInstallError("install failed"),
        ):
            rc = runner_module.main(
                ["--dataset", "nitroba", "--evidence", str(evidence), "--out", str(tmp_path)]
            )
        assert rc == 3

    def test_timeout_exits_4(self, tmp_path: Path) -> None:
        """CLI returns exit code 4 when run_baseline raises BaselineTimeoutError."""
        evidence = tmp_path / "evidence"
        evidence.mkdir()

        from harness.baseline import runner as runner_module

        with (
            patch("harness.baseline.runner.install_baseline"),
            patch(
                "harness.baseline.runner.run_baseline",
                side_effect=BaselineTimeoutError("timed out"),
            ),
        ):
            rc = runner_module.main(
                ["--dataset", "nitroba", "--evidence", str(evidence), "--out", str(tmp_path)]
            )
        assert rc == 4

    def test_baseline_error_exits_5(self, tmp_path: Path) -> None:
        """CLI returns exit code 5 when run_baseline raises an unexpected exception."""
        evidence = tmp_path / "evidence"
        evidence.mkdir()

        from harness.baseline import runner as runner_module

        with (
            patch("harness.baseline.runner.install_baseline"),
            patch(
                "harness.baseline.runner.run_baseline",
                side_effect=RuntimeError("unexpected"),
            ),
        ):
            rc = runner_module.main(
                ["--dataset", "nitroba", "--evidence", str(evidence), "--out", str(tmp_path)]
            )
        assert rc == 5
