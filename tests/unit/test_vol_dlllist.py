"""Unit tests for :func:`vol_dlllist`."""

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
from silentwitness_mcp.tools.memory import DllListOutput, vol_dlllist

MODEL = "claude-sonnet-4-6"


class _FakeProc:
    def __init__(self, *, stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0) -> None:
        self._stdout, self._stderr = stdout, stderr
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


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-dlllist-01"
    case_dir.mkdir()
    evidence = tmp_path / "memdump.vmem"
    evidence.write_bytes(secrets.token_bytes(128))
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.MEMORY_DUMP, audit_id="sift-aj-20260610-001")
    return case_dir, evidence, AuditLogger(case_dir, examiner="aj"), EvidenceRegistry(case_dir)


def _invoke(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    *,
    evidence_override: Path | None = None,
    pid: int | None = None,
) -> Any:
    case_dir, evidence, logger, registry = env
    return asyncio.run(
        vol_dlllist(
            evidence_override or evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
            pid=pid,
        )
    )


def _row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "PID": 1234,
        "Process": "svchost.exe",
        "Base": 0x7FFE000000,
        "Size": 0x100000,
        "Name": "ntdll.dll",
        "Path": "C:\\Windows\\System32\\ntdll.dll",
        "LoadTime": "2026-06-09T08:00:00+00:00",
        "File output": None,
    }
    base.update(overrides)
    return base


def test_dlllist_typical_system_dll_parses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canonical happy path — ntdll.dll from System32 round-trips
    verbatim through the typed model."""
    rows = [_row(), _row(PID=5678, Name="kernel32.dll", Path="C:\\Windows\\System32\\kernel32.dll")]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is True
    assert isinstance(envelope.data, DllListOutput)
    assert len(envelope.data.entries) == 2
    ntdll = envelope.data.entries[0]
    assert ntdll.pid == 1234
    assert ntdll.name == "ntdll.dll"
    assert ntdll.path == "C:\\Windows\\System32\\ntdll.dll"
    assert ntdll.base == 0x7FFE000000


def test_dlllist_side_loaded_dll_path_preserved_verbatim(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Side-loading red flag (ntdll.dll from C:\\Users\\Public\\) MUST
    be preserved verbatim — the caveat says to flag it; the type layer
    just preserves the citation span."""
    rows = [_row(Path="C:\\Users\\Public\\ntdll.dll")]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is True
    entry = envelope.data.entries[0]
    assert entry.name == "ntdll.dll"
    assert entry.path == "C:\\Users\\Public\\ntdll.dll"


def test_dlllist_paged_out_path_is_none(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Path may be None for paged-out entries — the type carries it
    honestly, no string placeholder."""
    rows = [_row(Path=None)]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data.entries[0].path is None


def test_dlllist_pid_filter_forwarded_to_vol3_argv(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``pid=4242`` MUST surface as ``--pid 4242`` immediately after
    the plugin name in cmd_argv."""
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    _invoke(env, pid=4242)
    argv = calls[0]
    plugin_idx = argv.index("windows.dlllist.DllList")
    pid_flag_idx = argv.index("--pid")
    assert pid_flag_idx > plugin_idx
    assert argv[pid_flag_idx + 1] == "4242"


def test_dlllist_unregistered_evidence_refuses_without_spawning(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir = env[0]
    unreg = case_dir.parent / "not-registered.vmem"
    unreg.write_bytes(b"x")
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env, evidence_override=unreg)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.EVIDENCE_NOT_REGISTERED.value
    assert calls == []


def test_dlllist_evidence_tampered_returns_evidence_tampered(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env[1].write_bytes(b"DIFFERENT bytes after registration")
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.EVIDENCE_TAMPERED.value
    assert calls == []


def test_dlllist_tool_failed_surfaces_truncated_stderr(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stderr = b"Vol3: PEB loader-list walk failed at 0x7ffe...\n" + b"X" * 1000
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"", stderr=stderr, returncode=1))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.TOOL_FAILED.value
    assert "loader-list walk failed" in envelope.advisories[0]
    assert len(envelope.advisories[0]) <= 500
    assert len(calls) == 1


def test_dlllist_cmd_argv_is_class_suffixed_plugin_name(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Plugin path MUST be the class-suffixed ``windows.dlllist.DllList``
    — bare ``windows.dlllist`` targets the module and Vol3 rejects it."""
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    argv = calls[0]
    assert argv[-1] == "windows.dlllist.DllList"
    assert envelope.data_provenance.cmd_argv[-1] == "windows.dlllist.DllList"


def test_dlllist_caveats_verbatim_with_reflective_loader_first(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """4 caveats appear in the prescribed order: PEB loader-list +
    reflective-blind-spot FIRST (action-shaping), then side-loading
    red flag, LoadTime use, false-positive caveat."""
    _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    caveats = envelope.caveats
    assert len(caveats) == 4
    assert "InLoadOrderModuleList" in caveats[0]
    assert "reflectively-loaded DLLs" in caveats[0]
    blob = " | ".join(caveats)
    assert "non-standard path" in blob
    assert "LoadTime" in blob
    assert "false-positive rate is high" in blob


def test_dlllist_unknown_column_triggers_output_parse_failed(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Vol3 column drift MUST trigger OUTPUT_PARSE_FAILED, not silent
    drop — forensic audit cannot quietly elide schema drift."""
    drifted = [{**_row(), "Reflective": True}]
    calls = _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(drifted).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.OUTPUT_PARSE_FAILED.value
    assert len(calls) == 1
