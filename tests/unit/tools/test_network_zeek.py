"""Unit tests for :func:`zeek_run` — happy path and gate refusals."""

from __future__ import annotations

import asyncio
import json
import secrets
from pathlib import Path
from typing import Any

import pytest

import silentwitness_mcp.tools._network_common as _net_mod
from silentwitness_common.types import EvidenceType
from silentwitness_mcp._lifecycle import MountCheckResult
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import (
    EvidenceMissingOnDiskError,
    EvidenceRegistry,
    EvidenceRegistryError,
)
from silentwitness_mcp.tools._network_common import NetworkFailureReason, _NetworkResult
from silentwitness_mcp.tools.network import ZeekLogInfo, ZeekRunResult, zeek_run

MODEL = "claude-sonnet-4-6"
_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "network"
_CONN_SAMPLE = _FIXTURE_DIR / "zeek_conn_sample.log"
_DNS_SAMPLE = _FIXTURE_DIR / "zeek_dns_sample.log"


@pytest.fixture
def pcap_file(tmp_path: Path) -> Path:
    p = tmp_path / "evidence" / "wardrive.pcap"
    p.parent.mkdir()
    p.write_bytes(secrets.token_bytes(256))
    return p


@pytest.fixture
def env(tmp_path: Path, pcap_file: Path) -> tuple[Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-zeek-01"
    case_dir.mkdir()
    out_dir = case_dir / "tmp" / "zeek-out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(pcap_file, EvidenceType.PCAP, audit_id="sift-aj-20260611-050")
    return (case_dir, out_dir, AuditLogger(case_dir, examiner="aj"), registry)


def _invoke(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    *,
    pcap_override: Path | None = None,
    out_dir_override: Path | None = None,
) -> Any:
    case_dir, out_dir, logger, registry = env
    return asyncio.run(
        zeek_run(
            pcap_override or pcap_file,
            out_dir_override or out_dir,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


def _force_gates_ok(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    zeek_present: bool = True,
    mount_ok: bool = True,
) -> Path:
    if mount_ok:
        monkeypatch.setattr(
            "silentwitness_mcp.tools.network.check_mount",
            lambda: MountCheckResult(ok=True, advisories=[]),
        )
    else:
        monkeypatch.setattr(
            "silentwitness_mcp.tools.network.check_mount",
            lambda: MountCheckResult(ok=False, advisories=["missing: ro"]),
        )

    fake_bin = tmp_path / "zeek"
    if zeek_present:
        fake_bin.touch()
        monkeypatch.setattr("silentwitness_mcp.tools.network.get_zeek_bin", lambda: fake_bin)
    else:
        monkeypatch.setattr("silentwitness_mcp.tools.network.get_zeek_bin", lambda: None)
    return fake_bin


def _install_zeek_mock(
    monkeypatch: pytest.MonkeyPatch,
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    *,
    exit_code: int = 0,
    populate_logs: bool = True,
) -> None:
    _case_dir, out_dir, *_ = env

    async def _fake(*_a: Any, **_kw: Any) -> _NetworkResult:
        if exit_code == 0 and populate_logs:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "conn.log").write_bytes(_CONN_SAMPLE.read_bytes())
            (out_dir / "dns.log").write_bytes(_DNS_SAMPLE.read_bytes())
        return _NetworkResult(exit_code=exit_code, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools.network._run_zeek", _fake)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_zeek_run_happy_path_returns_log_info(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Valid pcap → ZeekRunResult with typed log entries, SHA256, and audit trail."""
    case_dir, *_ = env
    _force_gates_ok(monkeypatch, tmp_path)
    _install_zeek_mock(monkeypatch, env)

    resp = _invoke(env, pcap_file)

    assert resp.success is True
    assert resp.data is not None
    out: ZeekRunResult = resp.data
    assert isinstance(out.conn_log, ZeekLogInfo)
    assert out.conn_log.line_count > 0
    assert len(out.conn_log.sha256) == 64
    assert out.dns_log is not None
    assert out.dns_log.line_count > 0
    assert out.total_logs == 2
    assert out.total_lines > 0
    assert resp.data_provenance.cmd_argv[0].endswith("zeek")
    assert "-r" in resp.data_provenance.cmd_argv
    assert "-C" in resp.data_provenance.cmd_argv
    assert resp.caveats
    log_path = case_dir / "audit" / "network.jsonl"
    assert log_path.exists()
    entry = json.loads(log_path.read_text().strip())
    assert entry["tool"] == "zeek_run"
    assert entry["result_summary"]["total_logs"] == 2
    assert "pcap_path" in entry["params"]


def test_inventory_oserror_output_parse_failed(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """_inventory_zeek_logs returning None → OUTPUT_PARSE_FAILED."""
    _force_gates_ok(monkeypatch, tmp_path)
    _install_zeek_mock(monkeypatch, env)
    monkeypatch.setattr("silentwitness_mcp.tools.network._inventory_zeek_logs", lambda _: None)

    resp = _invoke(env, pcap_file)

    assert resp.success is False
    assert any("OUTPUT_PARSE_FAILED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.OUTPUT_PARSE_FAILED.value


# ---------------------------------------------------------------------------
# Gate refusals
# ---------------------------------------------------------------------------


def test_zeek_not_installed_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Zeek binary absent → ZEEK_NOT_INSTALLED advisory."""
    _force_gates_ok(monkeypatch, tmp_path, zeek_present=False)
    monkeypatch.setattr(
        "silentwitness_mcp.tools.network.check_mount",
        lambda: MountCheckResult(ok=True, advisories=[]),
    )

    resp = _invoke(env, pcap_file)

    assert resp.success is False
    assert any("ZEEK_NOT_INSTALLED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.ZEEK_NOT_INSTALLED.value
    assert any("install.sh" in a for a in resp.advisories)


def test_unregistered_pcap_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unregistered pcap path → EVIDENCE_NOT_REGISTERED."""
    _force_gates_ok(monkeypatch, tmp_path)
    unregistered = tmp_path / "evidence" / "unregistered.pcap"
    unregistered.parent.mkdir(exist_ok=True)
    unregistered.write_bytes(secrets.token_bytes(32))

    resp = _invoke(env, unregistered, pcap_override=unregistered)

    assert resp.success is False
    assert any("EVIDENCE_NOT_REGISTERED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.EVIDENCE_NOT_REGISTERED.value


def test_tampered_pcap_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """SHA256 mismatch → EVIDENCE_TAMPERED."""
    _force_gates_ok(monkeypatch, tmp_path)
    pcap_file.write_bytes(secrets.token_bytes(256))  # mutate after registration

    resp = _invoke(env, pcap_file)

    assert resp.success is False
    assert any("EVIDENCE_TAMPERED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.EVIDENCE_TAMPERED.value


def test_bad_mount_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Bad mount flags → MOUNT_NOT_RO_NOEXEC_NOSUID."""
    _force_gates_ok(monkeypatch, tmp_path, mount_ok=False)

    resp = _invoke(env, pcap_file)

    assert resp.success is False
    assert any("MOUNT_NOT_RO_NOEXEC_NOSUID" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID.value


def test_nonzero_exit_refuses_with_stderr(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Zeek exits non-zero → TOOL_FAILED with stderr in advisory."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _bad(*_a: Any, **_kw: Any) -> _NetworkResult:
        return _NetworkResult(exit_code=1, stdout=b"", stderr=b"truncated pcap", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools.network._run_zeek", _bad)
    resp = _invoke(env, pcap_file)

    assert resp.success is False
    assert any("TOOL_FAILED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.TOOL_FAILED.value
    assert any("truncated pcap" in a for a in resp.advisories)


def test_no_logs_produced_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Zeek exits 0 but produces no *.log → NO_LOGS_PRODUCED."""
    _force_gates_ok(monkeypatch, tmp_path)
    _install_zeek_mock(monkeypatch, env, exit_code=0, populate_logs=False)

    _case_dir, out_dir, *_ = env
    out_dir.mkdir(parents=True, exist_ok=True)

    resp = _invoke(env, pcap_file)

    assert resp.success is False
    assert any("NO_LOGS_PRODUCED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.NO_LOGS_PRODUCED.value
    assert any("tcpdump" in a for a in resp.advisories)


def test_timeout_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """TimeoutError from _run_zeek → TOOL_TIMEOUT."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _timeout(*_a: Any, **_kw: Any) -> _NetworkResult:
        raise TimeoutError("timed out")

    monkeypatch.setattr("silentwitness_mcp.tools.network._run_zeek", _timeout)
    resp = _invoke(env, pcap_file)

    assert resp.success is False
    assert any("TOOL_TIMEOUT" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.TOOL_TIMEOUT.value


def test_spawn_oserror_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """OSError from _run_zeek → TOOL_FAILED with cmd_argv populated."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _spawn_error(*_a: Any, **_kw: Any) -> _NetworkResult:
        raise OSError("exec permission denied")

    monkeypatch.setattr("silentwitness_mcp.tools.network._run_zeek", _spawn_error)
    resp = _invoke(env, pcap_file)

    assert resp.success is False
    assert any("TOOL_SPAWN_FAILED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.TOOL_FAILED.value
    assert len(resp.data_provenance.cmd_argv) > 0


# ---------------------------------------------------------------------------
# Exception branches on verify_hash
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method, exc",
    [
        ("assert_registered", EvidenceMissingOnDiskError("vanished")),
        ("assert_registered", EvidenceRegistryError("internal")),
        ("verify_hash", EvidenceMissingOnDiskError("vanished")),
        ("verify_hash", EvidenceRegistryError("internal")),
    ],
)
def test_registry_exception_refuses(
    method: str,
    exc: Exception,
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """assert_registered / verify_hash raising registry errors → EVIDENCE_TAMPERED."""
    _force_gates_ok(monkeypatch, tmp_path)
    _case_dir, _out_dir, _logger, registry = env
    monkeypatch.setattr(registry, method, lambda _path: (_ for _ in ()).throw(exc))

    resp = _invoke(env, pcap_file)

    assert resp.success is False
    assert any("EVIDENCE_TAMPERED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.EVIDENCE_TAMPERED.value


# ---------------------------------------------------------------------------
# get_zeek_bin fallback behavior
# ---------------------------------------------------------------------------


def test_get_zeek_bin_primary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from silentwitness_mcp.tools._network_common import get_zeek_bin

    primary = tmp_path / "zeek"
    primary.touch()
    fallback = tmp_path / "zeek_fb"
    fallback.touch()
    monkeypatch.setattr(_net_mod, "ZEEK_BIN", primary)
    monkeypatch.setattr(_net_mod, "ZEEK_BIN_FALLBACK", fallback)
    assert get_zeek_bin() == primary


def test_get_zeek_bin_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from silentwitness_mcp.tools._network_common import get_zeek_bin

    fallback = tmp_path / "zeek_fb"
    fallback.touch()
    monkeypatch.setattr(_net_mod, "ZEEK_BIN", tmp_path / "absent")
    monkeypatch.setattr(_net_mod, "ZEEK_BIN_FALLBACK", fallback)
    assert get_zeek_bin() == fallback


def test_get_zeek_bin_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from silentwitness_mcp.tools._network_common import get_zeek_bin

    monkeypatch.setattr(_net_mod, "ZEEK_BIN", tmp_path / "absent")
    monkeypatch.setattr(_net_mod, "ZEEK_BIN_FALLBACK", tmp_path / "also_absent")
    assert get_zeek_bin() is None
