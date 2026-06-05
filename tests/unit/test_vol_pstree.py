"""Unit tests for :func:`vol_pstree`. Subprocess + Vol3 mocked via
``monkeypatch`` on ``asyncio.create_subprocess_exec``; the real
binary is exercised only by ``tests/integration/test_memory_e2e.py``
which is skip-marked until the NIST fixture lands."""

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
from silentwitness_mcp.tools.memory import PstreeEntry, PstreeOutput, vol_pstree

MODEL = "claude-sonnet-4-6"
_CASE_ID = "case-pstree-01"


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


def _row(pid: int, ppid: int, name: str, **extras: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "PID": pid,
        "PPID": ppid,
        "ImageFileName": name,
        "Offset(V)": 0x1000 * pid,
        "Threads": 1,
        "Handles": None,
        "SessionId": None,
        "Wow64": False,
        "CreateTime": None,
        "ExitTime": None,
        "Audit": None,
        "Cmd": None,
        "Path": None,
    }
    base.update(extras)
    return base


def test_pstree_tree_shape_flattens_breadth_first(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nested ``__children`` recursion in the Vol3 JSON renderer is
    flattened breadth-first by the parser; depth is NOT a column."""
    nested = [
        {
            **_row(4, 0, "System"),
            "__children": [
                {**_row(400, 4, "smss.exe"), "__children": [_row(401, 400, "csrss.exe")]},
                _row(402, 4, "wininit.exe"),
            ],
        },
    ]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(nested).encode("utf-8")))
    case_dir, evidence, logger, registry = env
    envelope = asyncio.run(
        vol_pstree(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is True
    assert isinstance(envelope.data, PstreeOutput)
    pids = [entry.pid for entry in envelope.data.entries]
    # Breadth-first: System -> smss + wininit -> csrss.
    assert pids == [4, 400, 402, 401]
    # No depth column on PstreeEntry.
    assert not any(hasattr(e, "depth") for e in envelope.data.entries)


def test_pstree_caveats_verbatim(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    case_dir, evidence, logger, registry = env
    envelope = asyncio.run(
        vol_pstree(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    blob = " | ".join(envelope.caveats)
    assert "Parent PIDs can refer to dead processes" in blob
    assert "Process hollowing produces legitimate-looking lineage" in blob


def test_pstree_pstree_class_plugin_name_in_argv(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    case_dir, evidence, logger, registry = env
    asyncio.run(
        vol_pstree(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert "windows.pstree.PsTree" in calls[0]


def test_pstree_unregistered_evidence_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir, _, logger, registry = env
    unreg = case_dir.parent / "not-registered.vmem"
    unreg.write_bytes(b"x")
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = asyncio.run(
        vol_pstree(
            unreg,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.EVIDENCE_NOT_REGISTERED.value
    assert calls == []


def test_pstree_tool_failed_captures_stderr(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_mock(
        monkeypatch, _FakeProc(stdout=b"", stderr=b"vol3 windows.pstree failed", returncode=2)
    )
    case_dir, evidence, logger, registry = env
    envelope = asyncio.run(
        vol_pstree(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.TOOL_FAILED.value
    assert "vol3 windows.pstree failed" in envelope.advisories[0]


def test_pstree_entry_extra_columns_present() -> None:
    """audit/cmd/path are pstree-only extras; PslistEntry doesn't have them."""
    entry = PstreeEntry.model_validate(
        _row(4, 0, "System", Audit="0:0", Cmd="C:\\cmd.exe /c x", Path="C:\\Windows\\cmd.exe")
    )
    assert entry.audit == "0:0"
    assert entry.cmd == "C:\\cmd.exe /c x"
    assert entry.path == "C:\\Windows\\cmd.exe"
