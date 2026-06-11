"""Unit tests for :func:`suricata_run` — happy path and gate refusals."""

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
from silentwitness_mcp.tools._network_suricata import SuricataRunResult, suricata_run

MODEL = "claude-sonnet-4-6"
_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "network"
_EVE_SAMPLE = _FIXTURE_DIR / "suricata_eve_sample.json"
_RULES_SAMPLE = _FIXTURE_DIR / "suricata_minimal.rules"


@pytest.fixture
def pcap_file(tmp_path: Path) -> Path:
    p = tmp_path / "evidence" / "wardrive.pcap"
    p.parent.mkdir()
    p.write_bytes(secrets.token_bytes(256))
    return p


@pytest.fixture
def rules_file(tmp_path: Path) -> Path:
    p = tmp_path / "evidence" / "suricata.rules"
    p.write_bytes(_RULES_SAMPLE.read_bytes())
    return p


@pytest.fixture
def env(
    tmp_path: Path, pcap_file: Path, rules_file: Path
) -> tuple[Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-suricata-01"
    case_dir.mkdir()
    out_dir = case_dir / "tmp" / "suricata-out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(pcap_file, EvidenceType.PCAP, audit_id="sift-aj-20260611-060")
    registry.register(rules_file, EvidenceType.IDS_RULES, audit_id="sift-aj-20260611-061")
    return (case_dir, out_dir, AuditLogger(case_dir, examiner="aj"), registry)


def _invoke(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    rules_file: Path,
    *,
    pcap_override: Path | None = None,
    rules_override: Path | None = None,
    out_dir_override: Path | None = None,
) -> Any:
    case_dir, out_dir, logger, registry = env
    return asyncio.run(
        suricata_run(
            pcap_override or pcap_file,
            rules_override or rules_file,
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
    suricata_present: bool = True,
    mount_ok: bool = True,
) -> None:
    monkeypatch.setattr(
        "silentwitness_mcp.tools._network_suricata.check_mount",
        lambda: MountCheckResult(ok=mount_ok, advisories=[] if mount_ok else ["missing: ro"]),
    )
    fake_bin = tmp_path / "suricata"
    if suricata_present:
        fake_bin.touch()
        monkeypatch.setattr(
            "silentwitness_mcp.tools._network_suricata.get_suricata_bin", lambda: fake_bin
        )
    else:
        monkeypatch.setattr(
            "silentwitness_mcp.tools._network_suricata.get_suricata_bin", lambda: None
        )


def _install_suricata_mock(
    monkeypatch: pytest.MonkeyPatch,
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    *,
    exit_code: int = 0,
    produce_eve: bool = True,
) -> None:
    _case_dir, out_dir, *_ = env

    async def _fake(*_a: Any, **_kw: Any) -> _NetworkResult:
        if exit_code == 0 and produce_eve:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "eve.json").write_bytes(_EVE_SAMPLE.read_bytes())
        return _NetworkResult(exit_code=exit_code, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools._network_suricata._run_suricata", _fake)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_suricata_run_happy_path(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    rules_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Valid pcap + rules → SuricataRunResult with event counts and audit trail."""
    case_dir, *_ = env
    _force_gates_ok(monkeypatch, tmp_path)
    _install_suricata_mock(monkeypatch, env)

    resp = _invoke(env, pcap_file, rules_file)

    assert resp.success is True
    assert resp.data is not None
    out: SuricataRunResult = resp.data
    assert out.alert_count == 1
    assert out.tls_count == 1
    assert out.dns_count == 1
    assert out.http_count == 1
    assert out.flow_count == 1
    assert out.fileinfo_count == 1
    assert out.anomaly_count == 1
    assert out.stats_count == 1
    assert out.total_events == 8
    assert len(out.eve_json_sha256) == 64
    assert out.event_type_breakdown["alert"] == 1
    assert resp.data_provenance.cmd_argv[0].endswith("suricata")
    assert "-r" in resp.data_provenance.cmd_argv
    assert "-S" in resp.data_provenance.cmd_argv
    assert "--runmode" in resp.data_provenance.cmd_argv
    assert "-k" in resp.data_provenance.cmd_argv
    assert resp.caveats
    # Audit JSONL
    log_path = case_dir / "audit" / "network.jsonl"
    assert log_path.exists()
    entry = json.loads(log_path.read_text().strip())
    assert entry["tool"] == "suricata_run"
    assert entry["result_summary"]["total_events"] == 8
    assert entry["result_summary"]["alert_count"] == 1
    assert "pcap_path" in entry["params"]
    assert "rules_path" in entry["params"]


# ---------------------------------------------------------------------------
# Gate refusals
# ---------------------------------------------------------------------------


def test_suricata_not_installed_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    rules_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Suricata binary absent → SURICATA_NOT_INSTALLED advisory."""
    _force_gates_ok(monkeypatch, tmp_path, suricata_present=False)

    resp = _invoke(env, pcap_file, rules_file)

    assert resp.success is False
    assert any("SURICATA_NOT_INSTALLED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.SURICATA_NOT_INSTALLED.value
    assert any("install.sh" in a for a in resp.advisories)


def test_unregistered_pcap_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    rules_file: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unregistered pcap → EVIDENCE_NOT_REGISTERED."""
    _force_gates_ok(monkeypatch, tmp_path)
    unregistered = tmp_path / "evidence" / "unregistered.pcap"
    unregistered.parent.mkdir(exist_ok=True)
    unregistered.write_bytes(secrets.token_bytes(32))

    resp = _invoke(env, unregistered, rules_file, pcap_override=unregistered)

    assert resp.success is False
    assert any("EVIDENCE_NOT_REGISTERED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.EVIDENCE_NOT_REGISTERED.value


def test_unregistered_rules_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unregistered rules file → EVIDENCE_NOT_REGISTERED with rules-specific advisory."""
    _force_gates_ok(monkeypatch, tmp_path)
    unregistered = tmp_path / "evidence" / "unregistered.rules"
    unregistered.parent.mkdir(exist_ok=True)
    unregistered.write_bytes(b"alert tcp any any -> any any (sid:1;)")

    resp = _invoke(env, pcap_file, unregistered, rules_override=unregistered)

    assert resp.success is False
    assert any("EVIDENCE_NOT_REGISTERED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.EVIDENCE_NOT_REGISTERED.value
    assert any("rules files ARE evidence" in a for a in resp.advisories)


def test_tampered_pcap_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    rules_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """SHA256 mismatch on pcap → EVIDENCE_TAMPERED."""
    _force_gates_ok(monkeypatch, tmp_path)
    pcap_file.write_bytes(secrets.token_bytes(256))

    resp = _invoke(env, pcap_file, rules_file)

    assert resp.success is False
    assert any("EVIDENCE_TAMPERED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.EVIDENCE_TAMPERED.value


def test_bad_mount_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    rules_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Bad mount flags → MOUNT_NOT_RO_NOEXEC_NOSUID."""
    _force_gates_ok(monkeypatch, tmp_path, mount_ok=False)

    resp = _invoke(env, pcap_file, rules_file)

    assert resp.success is False
    assert any("MOUNT_NOT_RO_NOEXEC_NOSUID" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID.value


def test_nonzero_exit_refuses_with_stderr(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    rules_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Suricata exits non-zero → TOOL_FAILED with stderr in advisory."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _bad(*_a: Any, **_kw: Any) -> _NetworkResult:
        return _NetworkResult(exit_code=1, stdout=b"", stderr=b"bad rules", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools._network_suricata._run_suricata", _bad)
    resp = _invoke(env, pcap_file, rules_file)

    assert resp.success is False
    assert any("TOOL_FAILED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.TOOL_FAILED.value
    assert any("bad rules" in a for a in resp.advisories)


def test_no_eve_json_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    rules_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Suricata exits 0 but eve.json absent → OUTPUT_PARSE_FAILED."""
    _force_gates_ok(monkeypatch, tmp_path)
    _install_suricata_mock(monkeypatch, env, exit_code=0, produce_eve=False)
    _case_dir, out_dir, *_ = env
    out_dir.mkdir(parents=True, exist_ok=True)

    resp = _invoke(env, pcap_file, rules_file)

    assert resp.success is False
    assert any("OUTPUT_PARSE_FAILED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.OUTPUT_PARSE_FAILED.value
    assert any("eve.json missing" in a for a in resp.advisories)


def test_timeout_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    rules_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """TimeoutError from _run_suricata → TOOL_TIMEOUT."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _timeout(*_a: Any, **_kw: Any) -> _NetworkResult:
        raise TimeoutError("timed out")

    monkeypatch.setattr("silentwitness_mcp.tools._network_suricata._run_suricata", _timeout)
    resp = _invoke(env, pcap_file, rules_file)

    assert resp.success is False
    assert any("TOOL_TIMEOUT" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.TOOL_TIMEOUT.value


# ---------------------------------------------------------------------------
# Registry exception branches
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
    rules_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Registry exceptions on pcap path → EVIDENCE_TAMPERED."""
    _force_gates_ok(monkeypatch, tmp_path)
    _case_dir, _out_dir, _logger, registry = env
    monkeypatch.setattr(registry, method, lambda _path: (_ for _ in ()).throw(exc))

    resp = _invoke(env, pcap_file, rules_file)

    assert resp.success is False
    assert any("EVIDENCE_TAMPERED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.EVIDENCE_TAMPERED.value


# ---------------------------------------------------------------------------
# get_suricata_bin fallback behavior
# ---------------------------------------------------------------------------


def test_get_suricata_bin_primary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from silentwitness_mcp.tools._network_common import get_suricata_bin

    primary = tmp_path / "suricata"
    primary.touch()
    monkeypatch.setattr(_net_mod, "SURICATA_BIN", primary)
    monkeypatch.setattr(_net_mod, "SURICATA_BIN_FALLBACK", tmp_path / "absent")
    assert get_suricata_bin() == primary


def test_get_suricata_bin_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from silentwitness_mcp.tools._network_common import get_suricata_bin

    fallback = tmp_path / "suricata_fb"
    fallback.touch()
    monkeypatch.setattr(_net_mod, "SURICATA_BIN", tmp_path / "absent")
    monkeypatch.setattr(_net_mod, "SURICATA_BIN_FALLBACK", fallback)
    assert get_suricata_bin() == fallback


def test_get_suricata_bin_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from silentwitness_mcp.tools._network_common import get_suricata_bin

    monkeypatch.setattr(_net_mod, "SURICATA_BIN", tmp_path / "absent")
    monkeypatch.setattr(_net_mod, "SURICATA_BIN_FALLBACK", tmp_path / "also_absent")
    assert get_suricata_bin() is None
