"""Integration tests for harness/baseline/runner.py — all network and subprocess calls mocked."""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from harness.baseline.runner import (
    BaselineInstallError,
    BaselineRunConfig,
    BaselineRunResult,
    BaselineTimeoutError,
    install_baseline,
    run_baseline,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_SCRIPT = b"#!/bin/bash\necho installed\n"


def _make_httpx_response(content: bytes, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


def _make_popen(stdout_lines: list[bytes], returncode: int = 0) -> MagicMock:
    """Return a Popen mock whose stdout yields the given lines then EOF."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = io.BytesIO(b"".join(stdout_lines))
    proc.wait = MagicMock(return_value=returncode)
    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    return proc


# ---------------------------------------------------------------------------
# install_baseline
# ---------------------------------------------------------------------------


class TestInstallBaseline:
    def test_verifies_sha256_and_runs_bash(self, tmp_path: Path) -> None:
        """install_baseline fetches script, verifies SHA256, runs bash, returns sift_dir."""
        import hashlib

        real_script = b"#!/bin/bash\necho installed\n"
        real_sha = hashlib.sha256(real_script).hexdigest()

        fake_run = MagicMock()
        fake_run.returncode = 0

        with (
            patch("harness.baseline.runner.INSTALL_SCRIPT_SHA256", real_sha),
            patch("harness.baseline.runner.httpx") as mock_httpx,
            patch("harness.baseline.runner.subprocess.run", return_value=fake_run),
        ):
            mock_httpx.get.return_value = _make_httpx_response(real_script)
            mock_httpx.HTTPError = Exception

            sift_dir = install_baseline(tmp_path)

        assert sift_dir == tmp_path / "protocol-sift"
        assert (tmp_path / "install.sh").read_bytes() == real_script

    def test_sha256_mismatch_raises_baseline_install_error(self, tmp_path: Path) -> None:
        """install_baseline raises BaselineInstallError when SHA256 does not match pin."""
        with (
            patch("harness.baseline.runner.httpx") as mock_httpx,
        ):
            mock_httpx.get.return_value = _make_httpx_response(b"tampered content")
            mock_httpx.HTTPError = Exception

            with pytest.raises(BaselineInstallError, match=r"install-script-sha256\.txt"):
                install_baseline(tmp_path)

    def test_network_error_raises_baseline_install_error(self, tmp_path: Path) -> None:
        """install_baseline wraps httpx network errors in BaselineInstallError."""

        class FakeHTTPError(Exception):
            pass

        with patch("harness.baseline.runner.httpx") as mock_httpx:
            mock_httpx.HTTPError = FakeHTTPError
            mock_httpx.get.side_effect = FakeHTTPError("connection refused")

            with pytest.raises(BaselineInstallError, match="Network error"):
                install_baseline(tmp_path)

    def test_httpx_none_raises_baseline_install_error(self, tmp_path: Path) -> None:
        """install_baseline raises when httpx is not installed."""
        with patch("harness.baseline.runner.httpx", None):
            with pytest.raises(BaselineInstallError, match="httpx is required"):
                install_baseline(tmp_path)


# ---------------------------------------------------------------------------
# run_baseline
# ---------------------------------------------------------------------------


def _make_config(evidence_path: Path, **kwargs: object) -> BaselineRunConfig:
    return BaselineRunConfig(
        dataset_id="nitroba",
        evidence_path=evidence_path,
        **kwargs,  # type: ignore[arg-type]
    )


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

    def test_timeout_raises_baseline_timeout_error(self, tmp_path: Path) -> None:
        """run_baseline raises BaselineTimeoutError when timeout_seconds is exceeded."""
        evidence = tmp_path / "evidence"
        evidence.mkdir()
        work_dir = tmp_path / "work"
        self._fake_sift_bin(work_dir)

        # Simulate a process that keeps yielding lines for a very long time.
        # We mock time.monotonic to always return past the deadline.
        popen_mock = _make_popen([b"line\n"] * 5)

        config = _make_config(evidence, work_dir=work_dir, timeout_seconds=1)

        call_count = 0

        def fast_clock() -> float:
            nonlocal call_count
            call_count += 1
            # First two calls set t0, after that return well past timeout.
            return 0.0 if call_count <= 2 else 999.0

        with (
            patch("harness.baseline.runner.subprocess.run") as mock_run,
            patch("harness.baseline.runner.subprocess.Popen", return_value=popen_mock),
            patch("harness.baseline.runner.time.monotonic", side_effect=fast_clock),
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="HEAD\n")
            with pytest.raises(BaselineTimeoutError):
                run_baseline(config)

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
            # First call: git rev-parse; second call: --help with --plan-mode
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="abc123\n"),
                MagicMock(returncode=0, stdout="--plan-mode  Run in plan mode\n", stderr=""),
            ]
            run_baseline(_make_config(evidence, work_dir=work_dir))

        assert "--plan-mode" in captured_cmd[0]

    def test_dry_run_fallback_noted(self, tmp_path: Path) -> None:
        """run_baseline falls back to --dry-run and records a note when --plan-mode absent."""
        evidence = tmp_path / "evidence"
        evidence.mkdir()
        work_dir = tmp_path / "work"
        self._fake_sift_bin(work_dir)

        popen_mock = _make_popen([])

        with (
            patch("harness.baseline.runner.subprocess.run") as mock_run,
            patch("harness.baseline.runner.subprocess.Popen", return_value=popen_mock),
        ):
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="abc123\n"),
                MagicMock(returncode=0, stdout="--dry-run  Dry run\n", stderr=""),
            ]
            result = run_baseline(_make_config(evidence, work_dir=work_dir))

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
            model="anthropic:claude-opus-4-7-1m",
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
        assert restored.findings[0].id == original.findings[0].id
        assert restored.tool_calls[0].tool_name == original.tool_calls[0].tool_name
        assert restored.notes == original.notes


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCLI:
    def test_nonexistent_evidence_exits_2(self, tmp_path: Path) -> None:
        """CLI returns exit code 2 and mentions evidence_path when evidence dir missing."""
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
