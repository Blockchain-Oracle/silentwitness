"""Unit tests for :func:`vol_cmdline`. Real Vol3 is exercised only by
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
from silentwitness_mcp.tools.memory import CmdlineOutput, vol_cmdline

MODEL = "claude-sonnet-4-6"
_CASE_ID = "case-cmdline-01"


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


def _invoke(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    *,
    evidence_override: Path | None = None,
    pid: int | None = None,
) -> Any:
    case_dir, evidence, logger, registry = env
    return asyncio.run(
        vol_cmdline(
            evidence_override or evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
            pid=pid,
        )
    )


def _row(pid: int, process: str, args: object) -> dict[str, Any]:
    return {"PID": pid, "Process": process, "Args": args}


def test_cmdline_typical_powershell_invocation_parses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canonical happy path: a PowerShell row with a long base64
    Args round-trips verbatim. The LOLBin caveat documents the
    follow-up; the type layer preserves the citation span."""
    encoded = "JABjAD0AKAAnAGgAdAB0AHAAcwA6AC8ALwBlAHYAaQBsAC4AaQBvAC8AeAAuAGUAeABlACcAKQ=="
    rows = [
        _row(1234, "powershell.exe", f"powershell.exe -enc {encoded}"),
        _row(5678, "explorer.exe", "C:\\Windows\\Explorer.EXE"),
    ]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is True
    assert isinstance(envelope.data, CmdlineOutput)
    assert len(envelope.data.entries) == 2
    ps = envelope.data.entries[0]
    assert ps.pid == 1234
    assert ps.process == "powershell.exe"
    assert ps.args is not None
    assert encoded in ps.args  # verbatim — entity gate matches cited spans


@pytest.mark.parametrize(
    "args_value",
    [
        None,
        "",
        "null",  # JSON-stringy null — Vol3 occasionally emits literal
        "Required memory at 0x7ffe4dc8 is not valid (process exited?)",
    ],
)
def test_cmdline_empty_or_paged_out_args_normalised_to_none(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    args_value: object,
) -> None:
    """Story BDD §48-51: System (PID 4), Registry, smss.exe, and
    paged-out PEBs all surface as Args=None. The forensic invariant
    is that ``args is None`` honestly means "no string available" —
    not the literal string "null", not a smear-artifact placeholder."""
    rows = [_row(4, "System", args_value)]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data.entries[0].pid == 4
    assert envelope.data.entries[0].args is None


def test_cmdline_pid_filter_forwarded_to_vol3_argv(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Story BDD §43-46: ``pid=4242`` MUST surface as ``--pid 4242``
    AFTER the plugin name in cmd_argv — Vol3-side filter is cheaper
    than scan-then-server-filter."""
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env, pid=4242)
    argv = calls[0]
    assert "--pid" in argv
    assert "4242" in argv
    plugin_idx = argv.index("windows.cmdline.CmdLine")
    assert argv.index("--pid") > plugin_idx
    assert "--pid" in envelope.data_provenance.cmd_argv


def test_cmdline_empty_output_clean_system(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data is not None
    assert envelope.data.entries == ()


def test_cmdline_unregistered_evidence_refuses_without_spawning(
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


def test_cmdline_evidence_tampered_returns_evidence_tampered(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env[1].write_bytes(b"DIFFERENT bytes after registration")
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.EVIDENCE_TAMPERED.value
    assert calls == []


def test_cmdline_tool_failed_surfaces_truncated_stderr(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Vol3 non-zero exit → TOOL_FAILED. The advisory must carry
    diagnostic context so a downstream agent's symbol-rebuild side-
    quest hook reads the stderr from advisories[0]."""
    stderr = b"Vol3: PEB read failed at 0x7ffe4dc8 - paged-out region\n" + b"X" * 1000
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"", stderr=stderr, returncode=1))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.TOOL_FAILED.value
    assert "PEB read failed" in envelope.advisories[0]
    assert len(envelope.advisories[0]) <= 500
    assert len(calls) == 1


def test_cmdline_cmd_argv_is_class_suffixed_plugin_name(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Plugin path MUST be the class-suffixed ``windows.cmdline.CmdLine``
    (note capital-L) — bare ``windows.cmdline`` targets the module
    and Vol3 rejects it."""
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    argv = calls[0]
    assert argv[-1] == "windows.cmdline.CmdLine"
    assert "/opt/silentwitness/vol3-venv/bin/vol" in argv
    assert envelope.data_provenance.cmd_argv[-1] == "windows.cmdline.CmdLine"


def test_cmdline_caveats_verbatim_with_action_shaping_first(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All 5 caveats from context/domain/03 §7.12 must appear verbatim.
    Action-shaping ("beats Sysmon EID 1") MUST appear first; tamper +
    LOLBin + paged-out + empty-args follow in that order."""
    _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    caveats = envelope.caveats
    assert "beats Sysmon EID 1" in caveats[0]
    blob = " | ".join(caveats)
    assert "PEB-tamper-overwritten" in blob
    assert "RtlInitUnicodeString" in blob
    assert "rundll32 / regsvr32 / mshta / msbuild / installutil" in blob
    assert "PEB may be paged out" in blob
    assert "System (PID 4), Registry, smss.exe" in blob


def test_cmdline_non_int_pid_triggers_output_parse_failed(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A row with PID="??" (Vol3 unresolved-process emission) MUST
    surface as OUTPUT_PARSE_FAILED — silent coercion would let
    downstream consumers compare against bogus int values."""
    bad = [_row(0, "smss.exe", "smss"), {**_row(0, "x", "y"), "PID": "??"}]
    calls = _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(bad).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.OUTPUT_PARSE_FAILED.value
    assert len(calls) == 1


def test_cmdline_unknown_column_triggers_output_parse_failed(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Vol3 column drift (e.g. a future ``ImageName`` flag) MUST
    trigger OUTPUT_PARSE_FAILED, not silent drop."""
    drifted = [{**_row(1, "smss.exe", "smss"), "ImageName": "smss.exe"}]
    calls = _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(drifted).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.OUTPUT_PARSE_FAILED.value
    assert len(calls) == 1
