"""Extra coverage for parse_evtx edge cases not fitting in the primary test file."""

from __future__ import annotations

import asyncio
import secrets
import shutil
from pathlib import Path
from typing import Any

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp._lifecycle import MountCheckResult
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import (
    EvidenceMissingOnDiskError,
    EvidenceRegistry,
    EvidenceRegistryError,
)
from silentwitness_mcp.tools._log_common import LogFailureReason, _LogResult
from silentwitness_mcp.tools.log import parse_evtx

MODEL = "claude-sonnet-4-6"
_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "log"
_EVTX_SAMPLE = _FIXTURE_DIR / "evtx_sample.csv"


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-evtx-extra"
    case_dir.mkdir()
    evidence = tmp_path / "Security.evtx"
    evidence.write_bytes(secrets.token_bytes(256))
    csv_out = case_dir / "tmp" / "evtx_csv_out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.EVTX, audit_id="sift-aj-20260611-021")
    return case_dir, evidence, csv_out, AuditLogger(case_dir, examiner="aj"), registry


def _invoke(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    *,
    channel: str | None = None,
) -> Any:
    case_dir, evidence, csv_out, logger, registry = env
    return asyncio.run(
        parse_evtx(
            evidence,
            csv_out,
            channel,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


def _force_gates_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "silentwitness_mcp.tools.log.check_mount",
        lambda: MountCheckResult(ok=True, advisories=[]),
    )
    fake_dotnet = tmp_path / "fake_dotnet"
    fake_dotnet.touch()
    monkeypatch.setattr("silentwitness_mcp.tools.log.DOTNET_BIN", fake_dotnet)
    fake_evtx = tmp_path / "EvtxECmd.dll"
    fake_evtx.touch()
    monkeypatch.setattr("silentwitness_mcp.tools.log.EVTXECMD_DLL", fake_evtx)


# ---------------------------------------------------------------------------
# TOOL_SPAWN_FAILED: OSError from subprocess — untested _fail() call site
# ---------------------------------------------------------------------------


def test_parse_evtx_spawn_failed_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """OSError from _run_dotnet_log_tool → TOOL_FAILED; cmd_argv in provenance."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _fake(dll: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        raise OSError("exec failed")

    monkeypatch.setattr("silentwitness_mcp.tools.log._run_dotnet_log_tool", _fake)
    resp = _invoke(env)
    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.TOOL_FAILED
    assert len(resp.data_provenance.cmd_argv) > 0


# ---------------------------------------------------------------------------
# Binary/corrupt CSV: UnicodeDecodeError should refuse, not return success=True
# ---------------------------------------------------------------------------


def test_parse_evtx_binary_csv_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Non-UTF-8 CSV bytes → OUTPUT_PARSE_FAILED (not false success with 0 records)."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _fake(dll: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        d = env[2]
        d.mkdir(parents=True, exist_ok=True)
        (d / "out.csv").write_bytes(b"\xff\xfe\x00binary garbage\x01\x02\x03")
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools.log._run_dotnet_log_tool", _fake)
    resp = _invoke(env)
    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.OUTPUT_PARSE_FAILED


# ---------------------------------------------------------------------------
# Unrecognised channel: advisory warns; tool still runs unfiltered
# ---------------------------------------------------------------------------


def test_parse_evtx_unknown_channel_warns(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Non-Security channel → success with 'unrecognised channel' advisory."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _fake(dll: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        d = env[2]
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy(_EVTX_SAMPLE, d / "out.csv")
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools.log._run_dotnet_log_tool", _fake)
    resp = _invoke(env, channel="Application")
    assert resp.success is True
    assert any("unrecognised channel" in a for a in resp.advisories)
    assert any("Application" in a for a in resp.advisories)


# ---------------------------------------------------------------------------
# assert_registered exceptions: missing/registry-error at first gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("exc_type", [EvidenceMissingOnDiskError, EvidenceRegistryError])
def test_parse_evtx_assert_registered_exception_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    exc_type: type,
) -> None:
    """EvidenceMissingOnDiskError/EvidenceRegistryError from assert_registered → TAMPERED."""

    def _raise(*_: Any) -> None:
        raise exc_type("gone")

    monkeypatch.setattr(EvidenceRegistry, "assert_registered", _raise)
    resp = _invoke(env)
    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.EVIDENCE_TAMPERED
