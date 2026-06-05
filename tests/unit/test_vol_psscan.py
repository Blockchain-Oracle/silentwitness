"""Unit tests for :func:`vol_psscan`. Same subprocess-mock pattern as
:mod:`test_vol_pslist` — psscan returns the same column set as pslist
so PsscanEntry inherits from PslistEntry."""

from __future__ import annotations

import asyncio
import json
import secrets
from pathlib import Path
from typing import Any

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._vol_common import VolFailureReason
from silentwitness_mcp.tools.memory import PsscanOutput, vol_psscan

MODEL = "claude-sonnet-4-6"
_CASE_ID = "case-psscan-01"


class _FakeProc:
    def __init__(
        self,
        *,
        stdout: bytes = b"",
        stderr: bytes = b"",
        returncode: int = 0,
    ) -> None:
        self._stdout = stdout
        self._stderr = stderr
        self.returncode: int | None = returncode

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr

    def terminate(self) -> None: ...
    def kill(self) -> None:
        self.returncode = -9

    async def wait(self) -> int:
        return self.returncode if self.returncode is not None else -1


def _install_mock(monkeypatch: pytest.MonkeyPatch, proc: _FakeProc) -> list[tuple[str, ...]]:
    calls: list[tuple[str, ...]] = []

    async def _fake(*argv: str, **_kw: Any) -> _FakeProc:
        calls.append(argv)
        return proc

    monkeypatch.setattr("silentwitness_mcp.tools._vol_common.asyncio.create_subprocess_exec", _fake)
    return calls


def _seed(tmp_path: Path) -> tuple[Path, Path]:
    case_dir = tmp_path / _CASE_ID
    case_dir.mkdir()
    evidence = tmp_path / "memdump.vmem"
    evidence.write_bytes(secrets.token_bytes(128))
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.MEMORY_DUMP, audit_id="sift-aj-20260605-001")
    return case_dir, evidence


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir, evidence = _seed(tmp_path)
    return case_dir, evidence, AuditLogger(case_dir, examiner="aj"), EvidenceRegistry(case_dir)


def _row(pid: int, **extras: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "PID": pid,
        "PPID": 0,
        "ImageFileName": f"proc_{pid}.exe",
        "Offset(V)": 0x1000 * pid,
        "Threads": 1,
        "Handles": None,
        "SessionId": None,
        "Wow64": False,
        "CreateTime": None,
        "ExitTime": None,
    }
    base.update(extras)
    return base


def test_psscan_parses_terminated_entry_with_exit_time(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """psscan can return pool-resident terminated processes — entries
    with ExitTime populated. This is the canonical psscan-vs-pslist
    diff signal (story BDD line 95)."""
    rows = [
        _row(4, ExitTime=None),  # live
        _row(1000, ExitTime="2026-06-05T10:00:00Z"),  # terminated, pool-resident
    ]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    case_dir, evidence, logger, registry = env
    envelope = asyncio.run(
        vol_psscan(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is True
    assert isinstance(envelope.data, PsscanOutput)
    assert len(envelope.data.entries) == 2
    terminated = next(e for e in envelope.data.entries if e.pid == 1000)
    assert terminated.exit_time is not None


def test_psscan_caveats_include_pslist_diff_guidance(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    case_dir, evidence, logger, registry = env
    envelope = asyncio.run(
        vol_psscan(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    blob = " | ".join(envelope.caveats)
    assert "may show terminated processes" in blob
    assert "DKOM-hidden OR terminated" in blob
    assert "pool-tag scan can produce false positives" in blob


def test_psscan_plugin_name_in_argv(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    case_dir, evidence, logger, registry = env
    asyncio.run(
        vol_psscan(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert "windows.psscan.PsScan" in calls[0]


def test_psscan_tamper_returns_evidence_tampered(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir, evidence, logger, registry = env
    evidence.write_bytes(b"DIFFERENT bytes after registration")
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = asyncio.run(
        vol_psscan(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.EVIDENCE_TAMPERED.value
    assert calls == []


def test_psscan_unregistered_evidence_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir, _, logger, registry = env
    unreg = case_dir.parent / "not-registered.vmem"
    unreg.write_bytes(b"x")
    _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = asyncio.run(
        vol_psscan(
            unreg,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.EVIDENCE_NOT_REGISTERED.value


def test_psscan_inherits_pslist_schema_drift_contract(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same extra="forbid" contract as PslistEntry: a hypothetical
    future Vol3 column triggers OUTPUT_PARSE_FAILED, not silent drop."""
    drifted = [{**_row(4), "Protected": "PsProtectedSignerWindows-Light"}]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(drifted).encode("utf-8")))
    case_dir, evidence, logger, registry = env
    envelope = asyncio.run(
        vol_psscan(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.OUTPUT_PARSE_FAILED.value
