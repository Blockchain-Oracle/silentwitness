"""Unit tests for :func:`vol_netscan`. Real Vol3 exercised only by
the skip-marked e2e test in ``test_memory_e2e.py``."""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
from pathlib import Path
from typing import Any

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._vol_common import VolFailureReason
from silentwitness_mcp.tools.memory import NetscanOutput, vol_netscan

MODEL = "claude-sonnet-4-6"
_CASE_ID = "case-netscan-01"


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


def _invoke(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    *,
    evidence_override: Path | None = None,
) -> Any:
    """Drive vol_netscan with the shared env tuple. ``evidence_override``
    lets the EVIDENCE_NOT_REGISTERED test pass an unregistered path
    without re-typing every kwarg."""
    case_dir, evidence, logger, registry = env
    return asyncio.run(
        vol_netscan(
            evidence_override or evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


def _tcp_v4(
    *,
    state: str = "ESTABLISHED",
    pid: int | None = 1234,
    local_addr: str = "10.0.0.5",
    foreign_addr: str = "203.0.113.42",
    foreign_port: int | None = 443,
    owner: str | None = "svchost.exe",
    created: str | None = "2026-06-09T08:00:00+00:00",
    offset: int = 0xFA8001234567,
) -> dict[str, Any]:
    return {
        "Offset": offset,
        "Proto": "TCPv4",
        "LocalAddr": local_addr,
        "LocalPort": 49152,
        "ForeignAddr": foreign_addr,
        "ForeignPort": foreign_port,
        "State": state,
        "PID": pid,
        "Owner": owner,
        "Created": created,
    }


def test_netscan_established_listening_time_wait_all_parse(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Story BDD §32-36: three canonical states must round-trip
    through the typed model with verbatim state preservation."""
    rows = [
        _tcp_v4(state="ESTABLISHED"),
        _tcp_v4(state="LISTENING", foreign_addr="0.0.0.0", foreign_port=0, pid=4),  # noqa: S104
        _tcp_v4(state="TIME_WAIT"),
    ]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is True
    assert isinstance(envelope.data, NetscanOutput)
    states = [e.state for e in envelope.data.entries]
    assert states == ["ESTABLISHED", "LISTENING", "TIME_WAIT"]


def test_netscan_ipv6_and_ipv4_mapped_ipv6_preserved_verbatim(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Story BDD §42-45: ``::ffff:192.168.1.50`` MUST NOT be
    normalised. The downstream entity gate matches against the
    verbatim cited span in tool output — normalisation here would
    cause every IPv6-cited observation to fail the gate."""
    rows = [
        _tcp_v4(local_addr="2001:db8::1", foreign_addr="::ffff:192.168.1.50"),
        {**_tcp_v4(), "Proto": "TCPv6", "LocalAddr": "fe80::1", "ForeignAddr": "::1"},
    ]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is True
    addrs = [(e.local_addr, e.foreign_addr) for e in envelope.data.entries]
    assert ("2001:db8::1", "::ffff:192.168.1.50") in addrs
    assert ("fe80::1", "::1") in addrs


def test_netscan_udp_wildcard_foreign_normalised_to_none(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Story BDD §47-51: Vol3 emits ``"*"`` for UDP foreign addr/port
    because UDP is connectionless. Pydantic does NOT coerce that
    literal string to None — the parser's wildcard-override step is
    what keeps the typed ``int | None`` / ``str | None`` invariant."""
    rows = [
        {
            "Offset": 0xFA8001112222,
            "Proto": "UDPv4",
            "LocalAddr": "0.0.0.0",  # noqa: S104
            "LocalPort": 53,
            "ForeignAddr": "*",
            "ForeignPort": "*",
            "State": "*",
            "PID": 968,
            "Owner": "svchost.exe",
            "Created": None,
        }
    ]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is True
    udp = envelope.data.entries[0]
    assert udp.proto == "UDPv4"
    assert udp.foreign_addr is None
    assert udp.foreign_port is None
    assert udp.state is None
    # Local side still preserved verbatim.
    assert udp.local_addr == "0.0.0.0"  # noqa: S104
    assert udp.local_port == 53


def test_netscan_empty_output_clean_system(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data is not None
    assert envelope.data.entries == ()


def test_netscan_unregistered_evidence_refuses_without_spawning(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Story BDD §53-54: ``EVIDENCE_NOT_REGISTERED`` MUST be returned
    before any subprocess spawn — the registry gate runs first."""
    case_dir = env[0]
    unreg = case_dir.parent / "not-registered.vmem"
    unreg.write_bytes(b"x")
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env, evidence_override=unreg)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.EVIDENCE_NOT_REGISTERED.value
    assert calls == []


def test_netscan_evidence_tampered_returns_evidence_tampered(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Story BDD §56-57: tamper-after-register MUST surface as
    ``EVIDENCE_TAMPERED`` before any subprocess spawn."""
    env[1].write_bytes(b"DIFFERENT bytes after registration")
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.EVIDENCE_TAMPERED.value
    assert calls == []


def test_netscan_tool_failed_surfaces_truncated_stderr(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Story BDD §59-62: Vol3 non-zero exit → ``TOOL_FAILED`` with
    ``advisories[0]`` carrying the first 500 chars of stderr."""
    stderr = b"Vol3: build-fragility - symbol drift on Win10 22H2\n" + b"Y" * 1000
    _install_mock(monkeypatch, _FakeProc(stdout=b"", stderr=stderr, returncode=1))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.TOOL_FAILED.value
    assert "symbol drift" in envelope.advisories[0]
    assert len(envelope.advisories[0]) <= 500


def test_netscan_malformed_pid_field_triggers_output_parse_failed(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-int PID (e.g. Vol3 emitting "??" for an unresolvable
    owner) MUST surface as OUTPUT_PARSE_FAILED — silent coercion
    would let downstream consumers compare against bogus int values."""
    bad = [{**_tcp_v4(), "PID": "??"}]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(bad).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.OUTPUT_PARSE_FAILED.value


def test_netscan_cmd_argv_is_class_suffixed_plugin_name(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Story BDD §36: cmd_argv MUST end with the class-suffixed
    ``windows.netscan.NetScan`` plugin path — bare ``windows.netscan``
    targets the module and Vol3 rejects it."""
    calls = _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    argv = calls[0]
    assert argv[-1] == "windows.netscan.NetScan"
    assert "/opt/silentwitness/vol3-venv/bin/vol" in argv
    assert "-r" in argv
    assert "json" in argv
    # Also recorded in DataProvenance for replay.
    assert envelope.data_provenance.cmd_argv[-1] == "windows.netscan.NetScan"


def test_netscan_caveats_verbatim_with_filter_to_established_first(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Story BDD §37-40 + spec "Caveat ordering matters": action-
    shaping caveat MUST appear first so an agent skimming caveats[0]
    sees the directive ("filter ESTABLISHED") before the CYA flag."""
    _install_mock(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _invoke(env)
    assert envelope.success is True
    caveats = envelope.caveats
    assert "ESTABLISHED for live C2 evidence" in caveats[0]
    blob = " | ".join(caveats)
    assert "build-fragile on Windows 10/11" in blob
    assert "Owner process resolution" in blob
    assert "LISTENING state on a non-loopback bind" in blob


def test_netscan_audit_row_result_sha256_matches_blob_hash(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audit-trail contract: the audit row's ``result_sha256`` MUST
    equal sha256(persisted blob bytes). C2/exfil findings will cite
    this hash — drift between row and blob would break verification."""
    rows = [_tcp_v4()]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(rows).encode("utf-8")))
    case_dir = env[0]
    envelope = _invoke(env)
    assert envelope.success is True
    audit_log = case_dir / "audit" / "memory.jsonl"
    audit_rows = [
        json.loads(line) for line in audit_log.read_text(encoding="utf-8").splitlines() if line
    ]
    row = next(r for r in audit_rows if r["tool"] == "vol_netscan")
    blob_path = case_dir / "audit" / "blobs" / f"{envelope.audit_id}.txt"
    assert row["result_sha256"] == hashlib.sha256(blob_path.read_bytes()).hexdigest()
    assert row["stdout_path"] == str(blob_path)


def test_netscan_unknown_column_triggers_output_parse_failed(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Vol3 column drift (e.g. a future ``Family`` flag) MUST trigger
    OUTPUT_PARSE_FAILED, not silent drop — forensic audit cannot
    quietly elide schema drift on network-attribution findings."""
    drifted = [{**_tcp_v4(), "Family": "AF_INET"}]
    _install_mock(monkeypatch, _FakeProc(stdout=json.dumps(drifted).encode("utf-8")))
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.OUTPUT_PARSE_FAILED.value
