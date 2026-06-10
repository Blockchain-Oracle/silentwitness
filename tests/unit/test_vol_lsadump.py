"""Unit tests for :func:`vol_lsadump`. Credential-material code path
— the only vol_* wrapper carrying a non-empty ``discipline_reminder``,
so the discipline-reminder contract is part of the test bar."""

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
from silentwitness_mcp.tools.memory_extras import LsaDumpOutput, vol_lsadump

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
    case_dir = tmp_path / "case-lsadump-01"
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
) -> Any:
    case_dir, evidence, logger, registry = env
    return asyncio.run(
        vol_lsadump(
            evidence_override or evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


def _utf16le_hex(text: str) -> str:
    """Encode ``text`` as UTF-16LE bytes + null-terminator, hex-encoded
    (the shape Vol3's lsadump renderer emits in the ``Hex`` field)."""
    return (text.encode("utf-16-le") + b"\x00\x00").hex()


def _row(key: str, hex_bytes: str) -> dict[str, Any]:
    return {"Key": key, "Hex": hex_bytes}


def test_lsadump_canonical_secret_set_parses_with_discipline_reminder(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canonical LSA secret keys ($MACHINE.ACC + DefaultPassword +
    _SC_<service> + DPAPI_SYSTEM + NL$KM) round-trip through the typed
    model, and the discipline_reminder fires for the credential-
    material code path (the load-bearing distinction across all 9
    vol_* tools)."""
    rows = [
        _row("$MACHINE.ACC", "deadbeefdeadbeef"),
        _row("DefaultPassword", _utf16le_hex("AutoLogonPass123")),
        _row("_SC_MSSQLServer", _utf16le_hex("ServiceSecret!")),
        _row("DPAPI_SYSTEM", "0102030405060708090a0b0c0d0e0f10"),
        _row("NL$KM", "1111222233334444"),
    ]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is True
    assert isinstance(envelope.data, LsaDumpOutput)
    assert len(envelope.data.entries) == 5
    keys = [e.Key for e in envelope.data.entries]
    assert keys == ["$MACHINE.ACC", "DefaultPassword", "_SC_MSSQLServer", "DPAPI_SYSTEM", "NL$KM"]
    # Discipline reminder MUST fire — Restricted classification + HMAC.
    assert envelope.discipline_reminder is not None
    assert "Restricted" in envelope.discipline_reminder
    assert "HMAC" in envelope.discipline_reminder


def test_lsadump_default_password_decodes_utf16le_printable_to_secret(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A DefaultPassword with printable UTF-16LE bytes surfaces a
    decoded ``Secret`` (operational comfort) AND the verbatim ``Hex``
    (authoritative — what the entity gate cites)."""
    plaintext = "AutoLogonPass123"
    hex_bytes = _utf16le_hex(plaintext)
    _install_mock(
        monkeypatch,
        _FakeProc(stdout=json.dumps([_row("DefaultPassword", hex_bytes)]).encode("utf-8")),
    )
    envelope = _invoke(env)
    assert envelope.success is True
    entry = envelope.data.entries[0]
    assert entry.Hex == hex_bytes
    assert entry.Secret == plaintext


def test_lsadump_non_printable_hex_keeps_secret_none(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A row whose ``Hex`` is binary garbage (e.g. $MACHINE.ACC raw
    hash) MUST surface ``Secret=None`` — silently mangling non-
    printable bytes into a string would corrupt the audit chain. The
    Vol3 renderer-side ``Secret`` field, if present, is IGNORED."""
    binary_hex = "deadbeefcafebabe1122334455667788"  # pragma: allowlist secret
    rows = [
        {
            **_row("$MACHINE.ACC", binary_hex),
            "Secret": "garbled-vol3-render",  # pragma: allowlist secret
        }
    ]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is True
    entry = envelope.data.entries[0]
    assert entry.Hex == binary_hex
    assert entry.Secret is None  # we discard Vol3's rendering and decode locally


def test_lsadump_empty_output_does_not_imply_credential_guard(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty result is legitimate (LSA partial-protection or no
    secrets present); discipline_reminder STILL fires because any
    follow-up observation built off this run carries the same
    credential-material classification expectation."""
    _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data.entries == ()
    assert envelope.discipline_reminder is not None


def test_lsadump_cmd_argv_uses_registry_lsadump_class_path(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Plugin path MUST be ``windows.registry.lsadump.Lsadump`` — the
    pre-2.29 path ``windows.lsadump.Lsadump`` is removed in Vol3 ≥2.29
    (CLAUDE.md). A regression to the old path would surface as
    TOOL_FAILED on every invocation."""
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    argv = calls[0]
    assert argv[-1] == "windows.registry.lsadump.Lsadump"
    assert "windows.lsadump.Lsadump" not in argv
    assert envelope.data_provenance.cmd_argv[-1] == "windows.registry.lsadump.Lsadump"


def test_lsadump_caveats_verbatim_with_credential_guard_first(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All 6 caveats appear in the prescribed order. Action-shaping
    FIRST — the Credential-Guard misconception correction — so an
    agent skimming ``caveats[0]`` reads the "empty output does NOT
    mean Credential Guard" directive before any other caveat."""
    _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    caveats = envelope.caveats
    assert len(caveats) == 6
    assert "Credential Guard does NOT" in caveats[0]
    blob = " | ".join(caveats)
    assert "DefaultPassword may contain auto-logon" in blob
    assert "$MACHINE.ACC is the machine account password hash" in blob
    assert "_SC_<service> contains passwords" in blob
    assert "SysKey from the SYSTEM hive" in blob
    assert "Secret field is best-effort UTF-16LE" in blob


def test_lsadump_unregistered_evidence_refuses_without_spawning(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BDD: no Vol3 subprocess is spawned (no credential material is
    ever touched)."""
    case_dir = env[0]
    unreg = case_dir.parent / "not-registered.vmem"
    unreg.write_bytes(b"x")
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env, evidence_override=unreg)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.EVIDENCE_NOT_REGISTERED.value
    assert calls == []


def test_lsadump_evidence_tampered_returns_evidence_tampered(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env[1].write_bytes(b"DIFFERENT bytes after registration")
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.EVIDENCE_TAMPERED.value
    assert calls == []


def test_lsadump_tool_failed_surfaces_truncated_stderr(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stderr = b"Vol3: SECURITY hive not present in memory dump\n" + b"X" * 1000
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"", stderr=stderr, returncode=1))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.TOOL_FAILED.value
    assert "SECURITY hive not present" in envelope.advisories[0]
    assert len(envelope.advisories[0]) <= 500
    assert len(calls) == 1


def test_lsadump_unicode_control_chars_keep_secret_none(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UTF-16LE bytes that decode to a string containing a C-class
    (control) codepoint MUST keep Secret=None — control chars are
    not "printable Unicode" by the audit contract."""
    # "Hi\x01" → contains C0 control U+0001.
    hex_with_control = "4800690001000000"
    _install_mock(
        monkeypatch,
        _FakeProc(stdout=json.dumps([_row("DefaultPassword", hex_with_control)]).encode("utf-8")),
    )
    envelope = _invoke(env)
    assert envelope.data.entries[0].Secret is None


def test_lsadump_malformed_hex_field_triggers_output_parse_failed(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-str ``Hex`` field (Vol3 schema drift) MUST surface as
    OUTPUT_PARSE_FAILED — credential-material audit cannot silently
    elide schema drift on a Restricted finding."""
    rows = [{"Key": "DefaultPassword", "Hex": 12345}]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.OUTPUT_PARSE_FAILED.value


def test_lsadump_unknown_column_triggers_output_parse_failed(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Vol3 column drift on this surface is a credential-material
    audit-elision risk — fail-closed."""
    rows = [{"Key": "DefaultPassword", "Hex": "deadbeef", "ExtraField": True}]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.OUTPUT_PARSE_FAILED.value
