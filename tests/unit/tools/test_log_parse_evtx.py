"""Unit tests for :func:`parse_evtx` — EvtxECmd EVTX wrapper."""

from __future__ import annotations

import asyncio
import json
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
from silentwitness_mcp.tools.log import (
    PARSE_EVTX_CAVEATS,
    EvtxOutput,
    parse_evtx,
)

MODEL = "claude-sonnet-4-6"

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "log"
_EVTX_SAMPLE = _FIXTURE_DIR / "evtx_sample.csv"
_EVTX_TRUNCATED = _FIXTURE_DIR / "evtx_truncated.csv"


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-evtx-01"
    case_dir.mkdir()
    evidence = tmp_path / "Security.evtx"
    evidence.write_bytes(secrets.token_bytes(256))
    csv_out = case_dir / "tmp" / "evtx_csv_out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.OTHER, audit_id="sift-aj-20260611-020")
    return (
        case_dir,
        evidence,
        csv_out,
        AuditLogger(case_dir, examiner="aj"),
        registry,
    )


def _invoke(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    *,
    evidence_override: Path | None = None,
    csv_out_override: Path | None = None,
    channel: str | None = None,
) -> Any:
    case_dir, evidence, csv_out, logger, registry = env
    return asyncio.run(
        parse_evtx(
            evidence_override or evidence,
            csv_out_override or csv_out,
            channel,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


def _install_log_mock(
    monkeypatch: pytest.MonkeyPatch,
    *,
    csv_fixture: Path,
    csv_out_dir: Path,
    csv_filename: str = "20260611_EvtxECmd_Output.csv",
    exit_code: int = 0,
    stdout: bytes = b"",
    stderr: bytes = b"",
) -> None:
    """Monkeypatch _run_dotnet_log_tool to return a controlled _LogResult.

    On exit_code==0, copies csv_fixture into csv_out_dir so the glob finds it."""
    result = _LogResult(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        elapsed_ms=1.0,
    )

    async def _fake(dll_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        if exit_code == 0 and not stderr:
            csv_out_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(csv_fixture, csv_out_dir / csv_filename)
        return result

    monkeypatch.setattr("silentwitness_mcp.tools.log._run_dotnet_log_tool", _fake)


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
# Happy-path tests
# ---------------------------------------------------------------------------


def test_parse_evtx_canonical_csv_returns_typed_records(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Valid CSV round-trips; EvtxOutput has typed records; caveats verbatim."""
    _case_dir, _evidence, csv_out, *_ = env
    _force_gates_ok(monkeypatch, tmp_path)
    _install_log_mock(monkeypatch, csv_fixture=_EVTX_SAMPLE, csv_out_dir=csv_out)

    resp = _invoke(env)

    assert resp.success is True
    assert resp.data is not None
    out: EvtxOutput = resp.data
    assert out.row_count == 10
    assert out.truncated is False
    assert resp.caveats == PARSE_EVTX_CAVEATS
    rec = out.records[0]
    assert rec.EventId == 4624
    assert rec.Channel == "Security"
    assert rec.EventRecordId == "12341"  # string, NOT int
    assert rec.TimeCreated.tzinfo is not None  # timezone-aware
    assert rec.RecordNumber == 1
    assert rec.UserName == "SYSTEM"
    assert resp.data_provenance.cmd_argv[1].endswith("EvtxECmd.dll")


def test_parse_evtx_security_channel_injects_inc_eid_list(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """channel='Security' → --inc <EIDs> appears in cmd_argv provenance."""
    _force_gates_ok(monkeypatch, tmp_path)
    captured: list[Any] = []

    async def _fake(dll_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        captured.extend(argv)
        _case_dir, _evidence, csv_out, *_ = env
        csv_out.mkdir(parents=True, exist_ok=True)
        shutil.copy(_EVTX_SAMPLE, csv_out / "20260611_EvtxECmd_Output.csv")
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools.log._run_dotnet_log_tool", _fake)

    resp = _invoke(env, channel="Security")

    assert resp.success is True
    assert "--inc" in captured
    inc_idx = captured.index("--inc")
    eid_csv = captured[inc_idx + 1]
    assert "4624" in eid_csv
    assert "4688" in eid_csv
    assert "1102" in eid_csv
    assert len(eid_csv.split(",")) == 30


def test_parse_evtx_truncated_csv_succeeds_with_advisory(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Partial CSV → success=True, truncated=True, advisory present."""
    _force_gates_ok(monkeypatch, tmp_path)
    _install_log_mock(monkeypatch, csv_fixture=_EVTX_TRUNCATED, csv_out_dir=env[2])

    resp = _invoke(env)

    assert resp.success is True
    assert resp.data is not None
    assert resp.data.truncated is True
    assert any("partial parse: 1 rows recovered" in a for a in resp.advisories)


def test_parse_evtx_audit_jsonl_written_on_success(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Success path writes a JSONL audit entry with row_count and channel param."""
    case_dir, *_ = env
    _force_gates_ok(monkeypatch, tmp_path)
    _install_log_mock(monkeypatch, csv_fixture=_EVTX_SAMPLE, csv_out_dir=env[2])

    resp = _invoke(env)

    assert resp.success is True
    log_path = case_dir / "audit" / "log.jsonl"
    assert log_path.exists()
    entry = json.loads(log_path.read_text().strip())
    assert entry["tool"] == "parse_evtx"
    assert entry["result_summary"]["row_count"] == 10
    assert entry["params"]["channel"] is None


# ---------------------------------------------------------------------------
# Gate refusals
# ---------------------------------------------------------------------------


def test_parse_evtx_unregistered_evidence_refuses(env, tmp_path) -> None:
    """Unregistered evidence path → EVIDENCE_NOT_REGISTERED refuse."""
    resp = _invoke(env, evidence_override=tmp_path / "ghost.evtx")

    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.EVIDENCE_NOT_REGISTERED


def test_parse_evtx_hash_mismatch_refuses(env, monkeypatch) -> None:
    """SHA256 drift on registered evidence → EVIDENCE_TAMPERED refuse."""
    _case_dir, evidence, *_ = env
    evidence.write_bytes(secrets.token_bytes(256))  # drift content after register

    resp = _invoke(env)

    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.EVIDENCE_TAMPERED


@pytest.mark.parametrize("exc_type", [EvidenceMissingOnDiskError, EvidenceRegistryError])
def test_parse_evtx_verify_hash_exception_refuses(env, monkeypatch, exc_type) -> None:
    """EvidenceMissingOnDiskError / EvidenceRegistryError from verify_hash → EVIDENCE_TAMPERED."""

    def _raise(*_: Any) -> None:
        raise exc_type("error")

    monkeypatch.setattr(EvidenceRegistry, "verify_hash", _raise)
    resp = _invoke(env)
    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.EVIDENCE_TAMPERED


def test_parse_evtx_mount_fail_refuses(env, monkeypatch) -> None:
    """Bad mount → MOUNT_NOT_RO_NOEXEC_NOSUID refuse; audit JSONL written."""
    case_dir, *_ = env
    monkeypatch.setattr(
        "silentwitness_mcp.tools.log.check_mount",
        lambda: MountCheckResult(ok=False, advisories=["missing noexec"]),
    )

    resp = _invoke(env)

    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID
    log_path = case_dir / "audit" / "log.jsonl"
    assert log_path.exists()


def test_parse_evtx_dotnet_missing_refuses(env, monkeypatch, tmp_path) -> None:
    """DOTNET_BIN absent → DOTNET_NOT_FOUND refuse."""
    monkeypatch.setattr(
        "silentwitness_mcp.tools.log.check_mount",
        lambda: MountCheckResult(ok=True, advisories=[]),
    )
    ghost = tmp_path / "no_dotnet_here"
    monkeypatch.setattr("silentwitness_mcp.tools.log.DOTNET_BIN", ghost)

    resp = _invoke(env)

    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.DOTNET_NOT_FOUND


def test_parse_evtx_evtxecmd_missing_refuses(env, monkeypatch, tmp_path) -> None:
    """EVTXECMD_DLL absent → EVTXECMD_NOT_FOUND refuse."""
    monkeypatch.setattr(
        "silentwitness_mcp.tools.log.check_mount",
        lambda: MountCheckResult(ok=True, advisories=[]),
    )
    fake_dotnet = tmp_path / "fake_dotnet"
    fake_dotnet.touch()
    monkeypatch.setattr("silentwitness_mcp.tools.log.DOTNET_BIN", fake_dotnet)
    ghost_dll = tmp_path / "no_evtxecmd_here.dll"
    monkeypatch.setattr("silentwitness_mcp.tools.log.EVTXECMD_DLL", ghost_dll)

    resp = _invoke(env)

    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.EVTXECMD_NOT_FOUND


@pytest.mark.parametrize(
    "serilog_stderr",
    [
        b"[12:34:56 ERR] Failed to open EVTX file\n",
        b"[08:00:01 FTL] EvtxECmd fatal\n",
    ],
)
def test_parse_evtx_serilog_marker_refuses(env, monkeypatch, tmp_path, serilog_stderr) -> None:
    """[ERR]/[FTL] in stderr on exit-0 → TOOL_FAILED refuse."""
    _force_gates_ok(monkeypatch, tmp_path)
    _install_log_mock(
        monkeypatch,
        csv_fixture=_EVTX_SAMPLE,
        csv_out_dir=env[2],
        exit_code=0,
        stderr=serilog_stderr,
    )
    resp = _invoke(env)
    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.TOOL_FAILED


def test_parse_evtx_nonzero_exit_refuses(env, monkeypatch, tmp_path) -> None:
    """Non-zero exit code → TOOL_FAILED refuse; exit_code in audit params."""
    case_dir, *_ = env
    _force_gates_ok(monkeypatch, tmp_path)
    _install_log_mock(
        monkeypatch,
        csv_fixture=_EVTX_SAMPLE,
        csv_out_dir=env[2],
        exit_code=1,
    )

    resp = _invoke(env)

    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.TOOL_FAILED
    log_path = case_dir / "audit" / "log.jsonl"
    entry = json.loads(log_path.read_text().strip())
    assert entry["params"]["exit_code"] == 1


def test_parse_evtx_no_csv_output_refuses(env, monkeypatch, tmp_path) -> None:
    """Tool succeeds but produces no CSV → OUTPUT_PARSE_FAILED refuse."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _fake_no_csv(dll: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        return _LogResult(exit_code=0, stdout=b"done", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools.log._run_dotnet_log_tool", _fake_no_csv)

    resp = _invoke(env)

    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.OUTPUT_PARSE_FAILED


def test_parse_evtx_header_only_csv_refuses(env, monkeypatch, tmp_path) -> None:
    """Header-only CSV (no data rows) → OUTPUT_PARSE_FAILED."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _fake(dll: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        d = env[2]
        d.mkdir(parents=True, exist_ok=True)
        (d / "out.csv").write_bytes(b"EventId,Channel,Provider\n")
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools.log._run_dotnet_log_tool", _fake)
    resp = _invoke(env)
    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.OUTPUT_PARSE_FAILED


def test_parse_evtx_timeout_refuses(env, monkeypatch, tmp_path) -> None:
    """Subprocess timeout → TOOL_TIMEOUT refuse."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _fake_timeout(dll: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        raise TimeoutError

    monkeypatch.setattr("silentwitness_mcp.tools.log._run_dotnet_log_tool", _fake_timeout)

    resp = _invoke(env)

    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.TOOL_TIMEOUT
