"""Tests for harness/baseline/runner.py — install_baseline function."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from harness.baseline.runner import (
    BaselineInstallError,
    install_baseline,
)


def _make_httpx_response(content: bytes, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


class TestInstallBaseline:
    def test_verifies_sha256_and_runs_bash(self, tmp_path: Path) -> None:
        """install_baseline fetches script, verifies SHA256, runs bash, returns sift_dir."""
        real_script = b"#!/bin/bash\necho installed\n"
        real_sha = hashlib.sha256(real_script).hexdigest()

        def fake_run(*args: object, **kwargs: object) -> MagicMock:
            # Simulate successful install: create the expected sift_dir.
            (tmp_path / "protocol-sift").mkdir(parents=True, exist_ok=True)
            return MagicMock(returncode=0)

        with (
            patch("harness.baseline.runner.INSTALL_SCRIPT_SHA256", real_sha),
            patch("harness.baseline.runner.httpx") as mock_httpx,
            patch("harness.baseline.runner.subprocess.run", side_effect=fake_run),
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

    def test_raise_for_status_error_raises_baseline_install_error(self, tmp_path: Path) -> None:
        """install_baseline raises BaselineInstallError on HTTP 4xx/5xx responses."""

        class FakeHTTPError(Exception):
            pass

        with patch("harness.baseline.runner.httpx") as mock_httpx:
            mock_httpx.HTTPError = FakeHTTPError
            resp = _make_httpx_response(b"Not Found", status_code=404)
            resp.raise_for_status.side_effect = FakeHTTPError("404 not found")
            mock_httpx.get.return_value = resp

            with pytest.raises(BaselineInstallError, match="Network error"):
                install_baseline(tmp_path)

    def test_httpx_none_raises_baseline_install_error(self, tmp_path: Path) -> None:
        """install_baseline raises when httpx is not installed."""
        with patch("harness.baseline.runner.httpx", None):
            with pytest.raises(BaselineInstallError, match="httpx is required"):
                install_baseline(tmp_path)

    def test_script_nonzero_exit_raises_baseline_install_error(self, tmp_path: Path) -> None:
        """install_baseline raises BaselineInstallError when bash script exits non-zero."""
        real_script = b"#!/bin/bash\nexit 1\n"
        real_sha = hashlib.sha256(real_script).hexdigest()

        with (
            patch("harness.baseline.runner.INSTALL_SCRIPT_SHA256", real_sha),
            patch("harness.baseline.runner.httpx") as mock_httpx,
            patch(
                "harness.baseline.runner.subprocess.run",
                return_value=MagicMock(returncode=1),
            ),
        ):
            mock_httpx.get.return_value = _make_httpx_response(real_script)
            mock_httpx.HTTPError = Exception

            with pytest.raises(BaselineInstallError, match="Install script exited 1"):
                install_baseline(tmp_path)
