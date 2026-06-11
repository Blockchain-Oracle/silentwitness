"""Unit tests for :func:`chainsaw_hunt` — gate refusals, error handling, audit trail."""

from __future__ import annotations

import asyncio
import secrets
from pathlib import Path
from typing import Any

import pytest

import silentwitness_mcp.tools._log_chainsaw as _chainsaw_mod
from silentwitness_common.types import EvidenceType
from silentwitness_mcp._lifecycle import MountCheckResult
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import (
    EvidenceMissingOnDiskError,
    EvidenceRegistry,
    EvidenceRegistryError,
)
from silentwitness_mcp.tools._log_chainsaw import chainsaw_hunt
from silentwitness_mcp.tools._log_common import LogFailureReason, _LogResult

MODEL = "claude-sonnet-4-6"
_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "log"
_CHAINSAW_SAMPLE = _FIXTURE_DIR / "chainsaw_sample.json"


@pytest.fixture
def evtx_dir(tmp_path: Path) -> Path:
    d = tmp_path / "evtx"
    d.mkdir()
    return d


@pytest.fixture
def env(tmp_path: Path, evtx_dir: Path) -> tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-chainsaw-gates"
    case_dir.mkdir()
    evidence = evtx_dir / "Security.evtx"
    evidence.write_bytes(secrets.token_bytes(256))
    json_out = case_dir / "tmp" / "chainsaw_out.json"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.EVTX, audit_id="sift-aj-20260611-041")
    return (
        case_dir,
        evtx_dir,
        json_out,
        AuditLogger(case_dir, examiner="aj"),
        registry,
    )


def _invoke(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    *,
    evtx_dir_override: Path | None = None,
    json_out_override: Path | None = None,
    level: str | None = None,
) -> Any:
    case_dir, evtx_dir, json_out, logger, registry = env
    return asyncio.run(
        chainsaw_hunt(
            evtx_dir_override or evtx_dir,
            json_out_override or json_out,
            _chainsaw_mod.SIGMA_RULES_DIR,
            _chainsaw_mod.CHAINSAW_MAPPING_DEFAULT,
            level=level,  # type: ignore[arg-type]
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
    mount_ok: bool = True,
    bin_present: bool = True,
    with_rules: bool = True,
    with_mapping: bool = True,
) -> None:
    monkeypatch.setattr(
        "silentwitness_mcp.tools._log_chainsaw.check_mount",
        lambda: MountCheckResult(ok=mount_ok, advisories=[] if mount_ok else ["missing ro"]),
    )
    fake_bin = tmp_path / "chainsaw"
    if bin_present:
        fake_bin.touch()
    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw.CHAINSAW_BIN", fake_bin)

    sigma_dir = tmp_path / "sigma"
    if with_rules:
        sigma_dir.mkdir(exist_ok=True)
        (sigma_dir / "proc_create.yml").touch()
    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw.SIGMA_RULES_DIR", sigma_dir)

    mapping = tmp_path / "mappings" / "sigma-event-logs-all.yml"
    if with_mapping:
        mapping.parent.mkdir(exist_ok=True)
        mapping.touch()
    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw.CHAINSAW_MAPPING_DEFAULT", mapping)


def _install_mock(
    monkeypatch: pytest.MonkeyPatch,
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    *,
    exit_code: int = 0,
    stderr: bytes = b"",
) -> None:
    _case_dir, _evtx_dir, json_out, *_ = env
    result = _LogResult(exit_code=exit_code, stdout=b"", stderr=stderr, elapsed_ms=1.0)

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        if exit_code == 0 and not stderr:
            json_out.parent.mkdir(parents=True, exist_ok=True)
            json_out.write_bytes(_CHAINSAW_SAMPLE.read_bytes())
        return result

    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw._run_native_log_tool", _fake)


# ---------------------------------------------------------------------------
# Gate refusal tests
# ---------------------------------------------------------------------------


def test_chainsaw_no_evtx_files_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Empty evtx_dir → EVIDENCE_NOT_REGISTERED advisory."""
    _force_gates_ok(monkeypatch, tmp_path)
    empty_dir = tmp_path / "empty_evtx"
    empty_dir.mkdir()

    resp = _invoke(env, evtx_dir_override=empty_dir)

    assert resp.success is False
    assert any("EVIDENCE_NOT_REGISTERED" in a for a in resp.advisories)
    assert resp.advisories[1] == LogFailureReason.EVIDENCE_NOT_REGISTERED.value


def test_chainsaw_unregistered_evidence_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """An evtx file not registered in EvidenceRegistry → EVIDENCE_NOT_REGISTERED."""
    _force_gates_ok(monkeypatch, tmp_path)
    unregistered_dir = tmp_path / "unregistered"
    unregistered_dir.mkdir()
    (unregistered_dir / "Application.evtx").write_bytes(secrets.token_bytes(64))

    resp = _invoke(env, evtx_dir_override=unregistered_dir)

    assert resp.success is False
    assert any("EVIDENCE_NOT_REGISTERED" in a for a in resp.advisories)


def test_chainsaw_evidence_tampered_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """SHA256 mismatch on registered evidence → EVIDENCE_TAMPERED advisory."""
    _force_gates_ok(monkeypatch, tmp_path)
    _, evtx_dir, _, _, _registry = env
    evidence = evtx_dir / "Security.evtx"
    evidence.write_bytes(secrets.token_bytes(512))  # mutate after registration

    resp = _invoke(env)

    assert resp.success is False
    assert any("EVIDENCE_TAMPERED" in a for a in resp.advisories)


def test_chainsaw_bad_mount_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Unhealthy mount → MOUNT_NOT_RO_NOEXEC_NOSUID advisory."""
    _force_gates_ok(monkeypatch, tmp_path, mount_ok=False)

    resp = _invoke(env)

    assert resp.success is False
    assert any("MOUNT_NOT_RO_NOEXEC_NOSUID" in a for a in resp.advisories)


def test_chainsaw_not_installed_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CHAINSAW_BIN absent → CHAINSAW_NOT_INSTALLED advisory."""
    _force_gates_ok(monkeypatch, tmp_path, bin_present=False)

    resp = _invoke(env)

    assert resp.success is False
    assert any("CHAINSAW_NOT_INSTALLED" in a for a in resp.advisories)
    assert resp.advisories[1] == LogFailureReason.CHAINSAW_NOT_INSTALLED.value


def test_chainsaw_mapping_missing_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """mapping_file absent → CHAINSAW_MAPPING_MISSING advisory."""
    _force_gates_ok(monkeypatch, tmp_path, with_mapping=False)

    resp = _invoke(env)

    assert resp.success is False
    assert any("CHAINSAW_MAPPING_MISSING" in a for a in resp.advisories)
    assert resp.advisories[1] == LogFailureReason.CHAINSAW_MAPPING_MISSING.value


def test_chainsaw_sigma_rules_missing_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sigma_rules_dir absent or empty → SIGMA_RULES_MISSING advisory."""
    _force_gates_ok(monkeypatch, tmp_path, with_rules=False)

    resp = _invoke(env)

    assert resp.success is False
    assert any("SIGMA_RULES_MISSING" in a for a in resp.advisories)
    assert resp.advisories[1] == LogFailureReason.SIGMA_RULES_MISSING.value


def test_chainsaw_nonzero_exit_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Non-zero exit code → TOOL_FAILED advisory."""
    _force_gates_ok(monkeypatch, tmp_path)
    _install_mock(monkeypatch, env, exit_code=1, stderr=b"fatal error parsing evtx")

    resp = _invoke(env)

    assert resp.success is False
    assert any("TOOL_FAILED" in a for a in resp.advisories)
    assert resp.advisories[1] == LogFailureReason.TOOL_FAILED.value


def test_chainsaw_timeout_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """TimeoutError from subprocess → TOOL_TIMEOUT advisory."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _fake_timeout(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        raise TimeoutError

    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw._run_native_log_tool", _fake_timeout)
    resp = _invoke(env)

    assert resp.success is False
    assert any("TOOL_TIMEOUT" in a for a in resp.advisories)
    assert resp.advisories[1] == LogFailureReason.TOOL_TIMEOUT.value


def test_chainsaw_json_not_produced_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Exit 0 but no JSON file → OUTPUT_PARSE_FAILED advisory."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _fake_no_output(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr(
        "silentwitness_mcp.tools._log_chainsaw._run_native_log_tool", _fake_no_output
    )
    resp = _invoke(env)

    assert resp.success is False
    assert any("OUTPUT_PARSE_FAILED" in a for a in resp.advisories)


def test_chainsaw_invalid_json_marks_truncated(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Unparseable JSON (0 usable entries, truncated=True) → OUTPUT_PARSE_FAILED."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        _, _, json_out, *_ = env
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_bytes(b"not valid json {{{{")
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw._run_native_log_tool", _fake)
    resp = _invoke(env)

    assert resp.success is False
    assert any("OUTPUT_PARSE_FAILED" in a for a in resp.advisories)


# ---------------------------------------------------------------------------
# Evidence registry exception branches
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exc",
    [
        EvidenceMissingOnDiskError("gone"),
        EvidenceRegistryError("internal"),
    ],
)
def test_chainsaw_assert_registered_exception_refuses(
    exc: Exception,
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """assert_registered raising registry errors → refuse with EVIDENCE_TAMPERED."""
    _force_gates_ok(monkeypatch, tmp_path)

    def _raise(_path: Path) -> None:
        raise exc

    _, _, _, _, registry = env
    monkeypatch.setattr(registry, "assert_registered", _raise)
    resp = _invoke(env)

    assert resp.success is False
    tampered = LogFailureReason.EVIDENCE_TAMPERED.value
    not_registered = LogFailureReason.EVIDENCE_NOT_REGISTERED.value
    assert any(a in (tampered, not_registered) for a in resp.advisories)


# ---------------------------------------------------------------------------
# Audit-write failure
# ---------------------------------------------------------------------------


def test_chainsaw_audit_write_failure_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Audit JSONL write failure → deletes orphan blob and returns TOOL_FAILED."""
    _force_gates_ok(monkeypatch, tmp_path)
    _install_mock(monkeypatch, env)

    deleted_blobs: list[Path] = []

    def _capture_delete(blob_path: Path) -> None:
        deleted_blobs.append(blob_path)

    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw.delete_orphan_blob", _capture_delete)
    monkeypatch.setattr(
        "silentwitness_mcp.tools._log_chainsaw.append_jsonl_line",
        lambda *_a, **_kw: (_ for _ in ()).throw(OSError("disk full")),
    )
    resp = _invoke(env)

    assert resp.success is False
    assert any("AUDIT_WRITE_FAILED" in a for a in resp.advisories)
    assert len(deleted_blobs) == 1
