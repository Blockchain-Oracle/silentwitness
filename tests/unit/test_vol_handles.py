"""Unit tests for :func:`vol_handles`."""

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
from silentwitness_mcp.tools.memory import HandlesOutput, vol_handles

MODEL = "claude-sonnet-4-6"

# Bitmask constants — verified against Windows SDK <winnt.h> and Vol3
# windows.handles plugin. The granted_access field is raw int; these
# are documented here so test readers don't have to grep MSDN.
_PROCESS_VM_READ = 0x10
_PROCESS_VM_WRITE = 0x20
_PROCESS_CREATE_THREAD = 0x2


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
    case_dir = tmp_path / "case-handles-01"
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
    object_types: list[str] | None = None,
) -> Any:
    case_dir, evidence, logger, registry = env
    return asyncio.run(
        vol_handles(
            evidence_override or evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
            pid=pid,
            object_types=object_types,
        )
    )


def _row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "PID": 1234,
        "Process": "svchost.exe",
        "Offset": 0xFA8000123456,
        "HandleValue": 0x100,
        "Type": "File",
        "GrantedAccess": 0x120089,
        "Name": "\\REGISTRY\\MACHINE\\SOFTWARE\\Microsoft\\Cryptography",
    }
    base.update(overrides)
    return base


def test_handles_four_typical_handle_types_parse(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """File / Mutant / Process / Key all round-trip through the typed
    model with verbatim Name preservation."""
    rows = [
        _row(Type="File"),
        _row(
            Type="Mutant",
            Name="\\BaseNamedObjects\\Global\\evil-mutex-abc123",  # pragma: allowlist secret
        ),
        _row(Type="Process", Name="lsass.exe", GrantedAccess=_PROCESS_VM_READ),
        _row(Type="Key", Name="\\REGISTRY\\MACHINE\\SOFTWARE\\Run"),
    ]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is True
    assert isinstance(envelope.data, HandlesOutput)
    types = [e.type for e in envelope.data.entries]
    assert types == ["File", "Mutant", "Process", "Key"]
    # Mutex name verbatim (malware-family fingerprint citation).
    assert envelope.data.entries[1].name == "\\BaseNamedObjects\\Global\\evil-mutex-abc123"


def test_handles_mimikatz_signature_preserves_raw_bitmask(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Process handle to lsass.exe with PROCESS_VM_READ — the type
    layer MUST preserve the raw int bitmask verbatim. No decoding;
    downstream consumers do contextual decoding."""
    rows = [_row(Type="Process", Name="lsass.exe", GrantedAccess=_PROCESS_VM_READ)]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    envelope = _invoke(env)
    entry = envelope.data.entries[0]
    assert entry.granted_access == _PROCESS_VM_READ
    assert entry.granted_access & _PROCESS_VM_READ  # post-hoc bitmask check works
    assert entry.name == "lsass.exe"


def test_handles_injection_prerequisite_bitmask_preserved(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PROCESS_VM_WRITE | PROCESS_CREATE_THREAD — the injection
    prerequisite. Raw bitmask preserved for the caveat-flagged check."""
    combo = _PROCESS_VM_WRITE | _PROCESS_CREATE_THREAD
    rows = [_row(Type="Process", Name="firefox.exe", GrantedAccess=combo)]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    envelope = _invoke(env)
    ga = envelope.data.entries[0].granted_access
    assert ga & _PROCESS_VM_WRITE
    assert ga & _PROCESS_CREATE_THREAD


def test_handles_pid_and_object_types_forwarded_to_vol3_argv(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``object_types=["File","Mutant"]`` MUST surface as a single
    comma-joined ``--object-types File,Mutant`` argument; ``pid``
    surfaces separately."""
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    _invoke(env, pid=1234, object_types=["File", "Mutant"])
    argv = calls[0]
    pid_idx = argv.index("--pid")
    assert argv[pid_idx + 1] == "1234"
    types_idx = argv.index("--object-types")
    assert argv[types_idx + 1] == "File,Mutant"
    plugin_idx = argv.index("windows.handles.Handles")
    assert pid_idx > plugin_idx
    assert types_idx > plugin_idx


def test_handles_empty_object_types_list_rejected_synchronously(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty list is a wrapper-input error (vs None = "no filter").
    Reject loudly so an LLM-driven typo gets a clean diagnostic."""
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    with pytest.raises(ValueError, match="non-empty list"):
        _invoke(env, object_types=[])
    assert calls == []


def test_handles_no_filters_passes_no_extra_argv(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pid=None + object_types=None → no --pid / --object-types in
    argv. Plugin name is the last arg."""
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    _invoke(env)
    argv = calls[0]
    assert argv[-1] == "windows.handles.Handles"
    assert "--pid" not in argv
    assert "--object-types" not in argv


def test_handles_unregistered_evidence_refuses_without_spawning(
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


def test_handles_evidence_tampered_returns_evidence_tampered(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env[1].write_bytes(b"DIFFERENT bytes after registration")
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.EVIDENCE_TAMPERED.value
    assert calls == []


def test_handles_tool_failed_surfaces_truncated_stderr(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stderr = b"Vol3: handle table walk failed for PID 4 (kernel space)\n" + b"X" * 1000
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"", stderr=stderr, returncode=1))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.TOOL_FAILED.value
    assert "handle table walk failed" in envelope.advisories[0]
    assert len(envelope.advisories[0]) <= 500
    assert len(calls) == 1


def test_handles_malformed_handle_value_triggers_output_parse_failed(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-int HandleValue (e.g. Vol3 emitting "??" for an
    unresolvable handle) MUST surface as OUTPUT_PARSE_FAILED."""
    bad = [{**_row(), "HandleValue": "??"}]
    calls = _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(bad).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.OUTPUT_PARSE_FAILED.value
    assert len(calls) == 1


def test_handles_cmd_argv_is_class_suffixed_plugin_name(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    argv = calls[0]
    assert argv[-1] == "windows.handles.Handles"
    assert envelope.data_provenance.cmd_argv[-1] == "windows.handles.Handles"


def test_handles_caveats_verbatim_with_injection_prerequisites_first(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """5 caveats appear in the prescribed order: injection-
    prerequisites FIRST (action-shaping), then Mimikatz signature,
    mutex fingerprints, driver-IPC, deleted-but-open files."""
    _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    caveats = envelope.caveats
    assert len(caveats) == 5
    assert "PROCESS_VM_WRITE | PROCESS_CREATE_THREAD" in caveats[0]
    assert "Mimikatz signature" in caveats[1]
    assert "lsass.exe" in caveats[1]
    assert "PROCESS_VM_READ" in caveats[1]
    assert "Mutant" in caveats[2]
    assert "Global\\<random>" in caveats[2]
    assert "PhysicalMemory" in caveats[3]
    assert "deleted files" in caveats[4]
