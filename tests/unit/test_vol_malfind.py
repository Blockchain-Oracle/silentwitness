"""Unit tests for :func:`vol_malfind`. Real Vol3 exercised only by
the skip-marked e2e test in ``test_memory_e2e.py``."""

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
from silentwitness_mcp.tools.memory import MalfindOutput, vol_malfind

MODEL = "claude-sonnet-4-6"
_CASE_ID = "case-malfind-01"


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
    registry.register(evidence, EvidenceType.MEMORY_DUMP, audit_id="sift-aj-20260609-001")
    return case_dir, evidence


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir, evidence = _seed(tmp_path)
    return case_dir, evidence, AuditLogger(case_dir, examiner="aj"), EvidenceRegistry(case_dir)


def _hit(pid: int = 1234, **extras: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "PID": pid,
        "Process": "svchost.exe",
        "Start VPN": 0x70000,
        "End VPN": 0x7000F,
        "Tag": "VadS",
        "Protection": "PAGE_EXECUTE_READWRITE",
        "CommitCharge": 16,
        "PrivateMemory": True,
        "File output": None,
        "Hexdump": "4d 5a 90 00 03 00 00 00 04 00 00 00 ff ff 00 00",
        "Disasm": None,
    }
    base.update(extras)
    return base


def test_malfind_rwx_private_no_file_hit_parses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canonical injection-pattern row: RWX + PrivateMemory=True +
    File output=None. Must parse with all fields populated."""
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps([_hit()]).encode("utf-8")))
    case_dir, evidence, logger, registry = env
    envelope = asyncio.run(
        vol_malfind(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is True
    assert isinstance(envelope.data, MalfindOutput)
    hit = envelope.data.entries[0]
    assert hit.protection == "PAGE_EXECUTE_READWRITE"
    assert hit.private_memory is True
    assert hit.file_output is None
    # Hexdump whitespace-stripped, first 256 hex chars retained.
    assert hit.hexdump_first_128 is not None
    assert " " not in hit.hexdump_first_128
    assert hit.hexdump_first_128.startswith("4d5a9000")  # MZ + ... preserved verbatim


def test_malfind_empty_output_clean_system(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    case_dir, evidence, logger, registry = env
    envelope = asyncio.run(
        vol_malfind(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is True
    assert envelope.data is not None
    assert envelope.data.entries == ()


def test_malfind_pid_filter_forwarded_to_vol3_argv(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``pid=4242`` MUST surface as ``--pid 4242`` in the cmd_argv —
    Vol3-side filter is cheaper than scan-then-server-filter."""
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    case_dir, evidence, logger, registry = env
    envelope = asyncio.run(
        vol_malfind(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
            pid=4242,
        )
    )
    argv = calls[0]
    assert "--pid" in argv
    assert "4242" in argv
    # Plugin name comes BEFORE --pid (Vol3 v3 convention).
    plugin_idx = argv.index("windows.malware.malfind.Malfind")
    assert argv.index("--pid") > plugin_idx
    # cmd_argv in DataProvenance also records the filter.
    assert "--pid" in envelope.data_provenance.cmd_argv


def test_malfind_plugin_path_is_windows_malware(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLAUDE.md: must use windows.malware.malfind.Malfind (Vol3 ≥2.29
    removes windows.malfind.Malfind)."""
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    case_dir, evidence, logger, registry = env
    asyncio.run(
        vol_malfind(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    argv = calls[0]
    assert "windows.malware.malfind.Malfind" in argv
    assert "windows.malfind.Malfind" not in argv


def test_malfind_caveats_verbatim(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All 3 caveats from context/domain/03 §7.6 must appear verbatim —
    the JIT-false-positive caveat is load-bearing for IR Accuracy
    scoring per the story spec."""
    _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    case_dir, evidence, logger, registry = env
    envelope = asyncio.run(
        vol_malfind(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    blob = " | ".join(envelope.caveats)
    assert "RWX private memory with no mapped file" in blob
    assert "JIT engines" in blob
    assert "RX-only code" in blob
    assert "MZ + PE" in blob


def test_malfind_unregistered_evidence_refuses_without_spawning(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir, _, logger, registry = env
    unreg = case_dir.parent / "not-registered.vmem"
    unreg.write_bytes(b"x")
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = asyncio.run(
        vol_malfind(
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


def test_malfind_tool_failed_surfaces_stderr_for_symbol_table_self_correction(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Vol3 'No suitable symbol table found' stderr is the demo
    3:00-3:30 self-correction trigger — the agent's hook layer reads
    advisories[0] and dispatches a symbol-rebuild side-quest. The
    wrapper just needs to make sure the stderr first-500-chars land
    in the right slot."""
    stderr = b"Vol3: No suitable symbol table found for kernel Win32k\n" + b"X" * 1000
    _install_mock(monkeypatch, _FakeProc(stdout=b"", stderr=stderr, returncode=1))
    case_dir, evidence, logger, registry = env
    envelope = asyncio.run(
        vol_malfind(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.TOOL_FAILED.value
    assert "No suitable symbol table" in envelope.advisories[0]
    assert len(envelope.advisories[0]) <= 500


def test_malfind_hexdump_capped_at_128_bytes(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Vol3 emits the full VAD hex; the wrapper trims to 256 hex chars
    (128 bytes) to keep the audit blob bounded."""
    long_hex = "ab " * 1000  # 1000 bytes worth, with whitespace
    _install_mock(
        monkeypatch, _FakeProc(stdout=json.dumps([_hit(Hexdump=long_hex)]).encode("utf-8"))
    )
    case_dir, evidence, logger, registry = env
    envelope = asyncio.run(
        vol_malfind(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is True
    hit = envelope.data.entries[0]
    assert hit.hexdump_first_128 is not None
    assert len(hit.hexdump_first_128) == 256
