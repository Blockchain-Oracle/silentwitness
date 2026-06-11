"""Extra coverage for hayabusa_csv_timeline edge cases not fitting in the primary test."""

from __future__ import annotations

import asyncio
import json
import secrets
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
from silentwitness_mcp.tools._log_hayabusa import hayabusa_csv_timeline

MODEL = "claude-sonnet-4-6"


@pytest.fixture
def evtx_dir(tmp_path: Path) -> Path:
    d = tmp_path / "evtx"
    d.mkdir()
    return d


@pytest.fixture
def env(tmp_path: Path, evtx_dir: Path) -> tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-hayabusa-extra"
    case_dir.mkdir()
    evidence = evtx_dir / "Security.evtx"
    evidence.write_bytes(secrets.token_bytes(256))
    csv_out = case_dir / "tmp" / "hayabusa_out.csv"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.EVTX, audit_id="sift-aj-20260611-031")
    return (
        case_dir,
        evtx_dir,
        csv_out,
        AuditLogger(case_dir, examiner="aj"),
        registry,
    )


def _invoke(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
) -> Any:
    case_dir, evtx_dir, csv_out, logger, registry = env
    return asyncio.run(
        hayabusa_csv_timeline(
            evtx_dir,
            csv_out,
            None,
            None,
            "super-verbose",
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


def _force_gates_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "silentwitness_mcp.tools._log_hayabusa.check_mount",
        lambda: MountCheckResult(ok=True, advisories=[]),
    )
    fake_bin = tmp_path / "hayabusa"
    fake_bin.touch()
    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa.HAYABUSA_BIN", fake_bin)
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir(exist_ok=True)
    (rules_dir / "test_rule.yml").touch()
    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa.HAYABUSA_RULES_DIR", rules_dir)


# ---------------------------------------------------------------------------
# Process-level failures: timeout, OSError spawn, no-CSV output
# ---------------------------------------------------------------------------


def test_hayabusa_nonzero_exit_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Non-zero exit → TOOL_FAILED; exit_code recorded in audit JSONL params."""
    case_dir, _evtx_dir, _csv_out, *_ = env
    _force_gates_ok(monkeypatch, tmp_path)

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        return _LogResult(exit_code=1, stdout=b"", stderr=b"uh oh", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa._run_native_log_tool", _fake)
    resp = _invoke(env)
    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.TOOL_FAILED
    assert len(resp.data_provenance.cmd_argv) > 0
    log_path = case_dir / "audit" / "log.jsonl"
    entry = json.loads(log_path.read_text().strip())
    assert entry["params"]["exit_code"] == 1


def test_hayabusa_timeout_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Subprocess timeout → TOOL_TIMEOUT; cmd_argv in provenance."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        raise TimeoutError

    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa._run_native_log_tool", _fake)
    resp = _invoke(env)
    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.TOOL_TIMEOUT
    assert len(resp.data_provenance.cmd_argv) > 0


def test_hayabusa_spawn_failed_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """OSError from _run_native_log_tool → TOOL_FAILED; cmd_argv in provenance."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        raise OSError("exec failed")

    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa._run_native_log_tool", _fake)
    resp = _invoke(env)
    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.TOOL_FAILED
    assert len(resp.data_provenance.cmd_argv) > 0


def test_hayabusa_no_csv_output_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Tool exits 0 but produces no CSV at the output path → OUTPUT_PARSE_FAILED."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        return _LogResult(exit_code=0, stdout=b"done", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa._run_native_log_tool", _fake)
    resp = _invoke(env)
    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.OUTPUT_PARSE_FAILED


# ---------------------------------------------------------------------------
# assert_registered exception branches
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("exc_type", [EvidenceMissingOnDiskError, EvidenceRegistryError])
def test_hayabusa_assert_registered_exception_refuses(
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


# ---------------------------------------------------------------------------
# verify_hash exception branches
# ---------------------------------------------------------------------------

_PARTIAL_CSV = (
    "Timestamp,RuleTitle,Level,Computer,Channel,EventID,RecordID,Details,"
    "MitreTactics,MitreTags,OtherTags,RuleFile,EvtxFile\n"
    "2025-01-01T00:00:00Z,Good Rule,high,PC1,Security,4624,1,,,,,rules/t.yml,Security.evtx\n"
    "BADINPUT,Bad Rule,high,PC1,Security,4624,2,,,,,rules/t.yml,Security.evtx\n"
)


@pytest.mark.parametrize("exc_type", [EvidenceMissingOnDiskError, EvidenceRegistryError])
def test_hayabusa_verify_hash_exception_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    exc_type: type,
) -> None:
    """EvidenceMissingOnDiskError/EvidenceRegistryError from verify_hash → TAMPERED."""

    def _raise(*_: Any) -> None:
        raise exc_type("hash check failed")

    monkeypatch.setattr(EvidenceRegistry, "verify_hash", _raise)
    resp = _invoke(env)
    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.EVIDENCE_TAMPERED


def test_hayabusa_partial_parse_succeeds_with_advisory(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Some valid rows + one bad row → success=True, truncated=True, advisory present."""
    _force_gates_ok(monkeypatch, tmp_path)
    _case_dir, _evtx_dir, csv_out, *_ = env

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        csv_out.parent.mkdir(parents=True, exist_ok=True)
        csv_out.write_text(_PARTIAL_CSV)
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa._run_native_log_tool", _fake)
    resp = _invoke(env)

    assert resp.success is True
    assert resp.data is not None
    assert resp.data.truncated is True
    assert resp.data.row_count == 1
    assert any("partial parse" in a for a in resp.advisories)


def test_hayabusa_audit_write_failure_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Audit JSONL write failure after success → TOOL_FAILED, orphan blob deleted."""
    _force_gates_ok(monkeypatch, tmp_path)
    _case_dir, _evtx_dir, csv_out, *_ = env

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        csv_out.parent.mkdir(parents=True, exist_ok=True)
        csv_out.write_text(_PARTIAL_CSV)
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    def _always_raise(*_: Any, **__: Any) -> None:
        raise OSError("disk full")

    deleted_blobs: list[Path] = []

    def _capture_delete(blob_path: Path) -> None:
        deleted_blobs.append(blob_path)

    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa._run_native_log_tool", _fake)
    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa.append_jsonl_line", _always_raise)
    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa.delete_orphan_blob", _capture_delete)
    resp = _invoke(env)

    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.TOOL_FAILED
    assert any("AUDIT_WRITE_FAILED" in a for a in resp.advisories)
    assert len(deleted_blobs) == 1
