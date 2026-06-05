"""Unit tests for :func:`vol_pslist` (Epic 5 skeleton story).

Subprocess interactions are mocked via ``monkeypatch`` on
``asyncio.create_subprocess_exec`` — the real Vol3 binary is exercised
only by ``tests/integration/test_memory_e2e.py`` which is skip-marked
when the NIST fixture is absent."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._vol_common import VolFailureReason
from silentwitness_mcp.tools.memory import PslistOutput, vol_pslist

MODEL = "claude-sonnet-4-6"
_CASE_ID = "case-pslist-01"


# ---------------------------------------------------------------------------
# Subprocess mock
# ---------------------------------------------------------------------------


class _FakeProc:
    """Minimal stand-in for ``asyncio.subprocess.Process``. Captures
    SIGTERM / SIGKILL signals so the timeout test can assert escalation."""

    def __init__(
        self,
        *,
        stdout: bytes = b"",
        stderr: bytes = b"",
        returncode: int = 0,
        hang: bool = False,
    ) -> None:
        self._stdout = stdout
        self._stderr = stderr
        self.returncode: int | None = None if hang else returncode
        self._hang = hang
        self.terminated = False
        self.killed = False

    async def communicate(self) -> tuple[bytes, bytes]:
        if self._hang:
            await asyncio.sleep(60)  # blocked until wait_for kills us
        return self._stdout, self._stderr

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    async def wait(self) -> int:
        if self._hang and not self.killed:
            await asyncio.sleep(60)
        return self.returncode if self.returncode is not None else -1


def _install_subprocess_mock(
    monkeypatch: pytest.MonkeyPatch, proc: _FakeProc
) -> list[tuple[str, ...]]:
    """Patch ``asyncio.create_subprocess_exec`` to return ``proc`` and
    record the argv it was invoked with. Returns the recording list."""
    calls: list[tuple[str, ...]] = []

    async def _fake_create(*argv: str, **_kwargs: Any) -> _FakeProc:
        calls.append(argv)
        return proc

    monkeypatch.setattr(
        "silentwitness_mcp.tools._vol_common.asyncio.create_subprocess_exec", _fake_create
    )
    return calls


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _seed_registered_evidence(tmp_path: Path) -> tuple[Path, Path]:
    """Create a case dir + a registered "memdump" fixture file. The
    fixture content is arbitrary — Vol3 is mocked, so only the SHA256
    contract matters here."""
    case_dir = tmp_path / _CASE_ID
    case_dir.mkdir()
    evidence = tmp_path / "memdump.vmem"
    evidence.write_bytes(b"fake memory image bytes\n")
    registry = EvidenceRegistry(case_dir=case_dir)
    from silentwitness_common.types import EvidenceType

    registry.register(evidence, EvidenceType.MEMORY_DUMP, audit_id="sift-aj-20260605-001")
    return case_dir, evidence


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir, evidence = _seed_registered_evidence(tmp_path)
    return case_dir, evidence, AuditLogger(case_dir, examiner="aj"), EvidenceRegistry(case_dir)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_vol_pslist_parses_valid_json_into_typed_output(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir, evidence, logger, registry = env
    rows = [
        {
            "PID": 4,
            "PPID": 0,
            "ImageFileName": "System",
            "Offset(V)": 0xFFFFFA8000000000,
            "Threads": 95,
            "Handles": None,
            "SessionId": None,
            "Wow64": False,
            "CreateTime": "2026-01-01T00:00:00Z",
            "ExitTime": None,
        }
    ]
    proc = _FakeProc(stdout=json.dumps(rows).encode("utf-8"))
    _install_subprocess_mock(monkeypatch, proc)
    envelope = asyncio.run(
        vol_pslist(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is True
    assert isinstance(envelope.data, PslistOutput)
    assert len(envelope.data.entries) == 1
    entry = envelope.data.entries[0]
    assert entry.pid == 4
    assert entry.image_file_name == "System"
    # Audit row + blob persisted.
    audit_log = case_dir / "audit" / "memory.jsonl"
    assert audit_log.exists()
    audit_rows = [
        json.loads(line) for line in audit_log.read_text(encoding="utf-8").splitlines() if line
    ]
    assert audit_rows[0]["tool"] == "vol_pslist"
    blob_path = case_dir / "audit" / "blobs" / f"{envelope.audit_id}.txt"
    assert blob_path.exists()
    # Audit-trail contract (BDD line 45): result_sha256 in the audit row
    # matches SHA256 of the persisted blob bytes.
    import hashlib

    assert audit_rows[0]["result_sha256"] == hashlib.sha256(blob_path.read_bytes()).hexdigest()
    assert audit_rows[0]["stdout_path"] == str(blob_path)
    # All three caveats from _VOL_CAVEATS["pslist"] verbatim (BDD lines 49-51).
    caveats_blob = " | ".join(envelope.caveats)
    assert "PsActiveProcessHead" in caveats_blob
    assert "truncated to 15 chars" in caveats_blob
    assert "ExitTime may be set" in caveats_blob


def test_vol_pslist_empty_table_returns_empty_entries(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir, evidence, logger, registry = env
    _install_subprocess_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = asyncio.run(
        vol_pslist(
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


# ---------------------------------------------------------------------------
# Refusal paths
# ---------------------------------------------------------------------------


def test_unregistered_evidence_refuses_without_spawning(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir, _, logger, registry = env
    unregistered = case_dir.parent / "not-in-manifest.vmem"
    unregistered.write_bytes(b"x")
    calls = _install_subprocess_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = asyncio.run(
        vol_pslist(
            unregistered,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.EVIDENCE_NOT_REGISTERED.value
    assert calls == []  # subprocess NEVER spawned


def test_post_register_tamper_returns_evidence_tampered(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir, evidence, logger, registry = env
    evidence.write_bytes(b"DIFFERENT bytes after registration")
    calls = _install_subprocess_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = asyncio.run(
        vol_pslist(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.EVIDENCE_TAMPERED.value
    assert calls == []  # no spawn after hash drift


def test_tool_failed_captures_stderr_first_500_chars(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir, evidence, logger, registry = env
    stderr_msg = b"vol3 plugin windows.pslist failed: " + b"X" * 1000
    _install_subprocess_mock(monkeypatch, _FakeProc(stdout=b"", stderr=stderr_msg, returncode=2))
    envelope = asyncio.run(
        vol_pslist(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.TOOL_FAILED.value
    assert "vol3 plugin" in envelope.advisories[0]
    assert len(envelope.advisories[0]) <= 500


def test_tool_timeout_escalates_to_kill(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Shrink grace to keep the test under one second. The constant lives
    # in _vol_common; monkeypatching it preserves the production default.
    monkeypatch.setattr("silentwitness_mcp.tools._vol_common._TERMINATE_GRACE_S", 0.05)
    case_dir, evidence, logger, registry = env
    hanging = _FakeProc(hang=True)
    _install_subprocess_mock(monkeypatch, hanging)
    envelope = asyncio.run(
        vol_pslist(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
            timeout_s=0.05,
        )
    )
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.TOOL_TIMEOUT.value
    # SIGTERM → grace timeout → SIGKILL escalation must run end-to-end;
    # asserting only `terminated` would let a regression that breaks the
    # grace-timeout fallthrough pass silently.
    assert hanging.terminated is True
    assert hanging.killed is True


def test_malformed_json_returns_parse_failed_with_preview(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_dir, evidence, logger, registry = env
    garbage = b"[{not valid json mid-stream"
    _install_subprocess_mock(monkeypatch, _FakeProc(stdout=garbage))
    envelope = asyncio.run(
        vol_pslist(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.OUTPUT_PARSE_FAILED.value
    assert "{not valid json" in envelope.advisories[0]


def test_unknown_column_triggers_output_parse_failed(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Future Vol3 release adds a column the model doesn't know about
    → forbid catches it → OUTPUT_PARSE_FAILED. Forensic audit must not
    silently drop schema drift."""
    drifted_row = [
        {
            "PID": 4,
            "PPID": 0,
            "ImageFileName": "System",
            "Offset(V)": 0x1000,
            "Threads": 1,
            "Wow64": False,
            "Protected": "PsProtectedSignerWindows-Light",  # NEW column in hypothetical Vol3 2.29
        }
    ]
    case_dir, evidence, logger, registry = env
    _install_subprocess_mock(monkeypatch, _FakeProc(stdout=json.dumps(drifted_row).encode("utf-8")))
    envelope = asyncio.run(
        vol_pslist(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.OUTPUT_PARSE_FAILED.value
    assert "ValidationError" in envelope.advisories[0]


def test_cmd_argv_is_pinned_to_vol3_venv_with_plugin_class_name(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Architecture pin: must call /opt/silentwitness/vol3-venv/bin/vol
    with -r json + windows.pslist.PsList (class-suffixed form)."""
    case_dir, evidence, logger, registry = env
    calls = _install_subprocess_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    asyncio.run(
        vol_pslist(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert len(calls) == 1
    argv = calls[0]
    assert argv[0] == "/opt/silentwitness/vol3-venv/bin/vol"
    assert "-r" in argv and "json" in argv
    assert "windows.pslist.PsList" in argv
