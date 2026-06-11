"""Unit tests for :func:`hayabusa_csv_timeline` — Hayabusa csv-timeline wrapper."""

from __future__ import annotations

import asyncio
import json
import secrets
import shutil
from pathlib import Path
from typing import Any

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp._lifecycle import MountCheckResult
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import (
    EvidenceRegistry,
)
from silentwitness_mcp.tools._log_common import LogFailureReason, _LogResult
from silentwitness_mcp.tools._log_hayabusa import hayabusa_csv_timeline
from silentwitness_mcp.tools._log_models_hayabusa import HayabusaOutput

MODEL = "claude-sonnet-4-6"
_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "log"
_HAYABUSA_SAMPLE = _FIXTURE_DIR / "hayabusa_sample.csv"


@pytest.fixture
def evtx_dir(tmp_path: Path) -> Path:
    d = tmp_path / "evtx"
    d.mkdir()
    return d


@pytest.fixture
def env(tmp_path: Path, evtx_dir: Path) -> tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-hayabusa-01"
    case_dir.mkdir()
    evidence = evtx_dir / "Security.evtx"
    evidence.write_bytes(secrets.token_bytes(256))
    csv_out = case_dir / "tmp" / "hayabusa_out.csv"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.EVTX, audit_id="sift-aj-20260611-030")
    return (
        case_dir,
        evtx_dir,
        csv_out,
        AuditLogger(case_dir, examiner="aj"),
        registry,
    )


def _invoke(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    *,
    evtx_dir_override: Path | None = None,
    csv_out_override: Path | None = None,
    min_level: str | None = None,
    include_tags: list[str] | None = None,
    profile: str = "super-verbose",
) -> Any:
    case_dir, evtx_dir, csv_out, logger, registry = env
    return asyncio.run(
        hayabusa_csv_timeline(
            evtx_dir_override or evtx_dir,
            csv_out_override or csv_out,
            min_level,  # type: ignore[arg-type]
            include_tags,
            profile,  # type: ignore[arg-type]
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
    with_rules: bool = True,
) -> None:
    monkeypatch.setattr(
        "silentwitness_mcp.tools._log_hayabusa.check_mount",
        lambda: MountCheckResult(ok=True, advisories=[]),
    )
    fake_bin = tmp_path / "hayabusa"
    fake_bin.touch()
    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa.HAYABUSA_BIN", fake_bin)
    rules_dir = tmp_path / "rules"
    if with_rules:
        rules_dir.mkdir(exist_ok=True)
        (rules_dir / "test_rule.yml").touch()
    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa.HAYABUSA_RULES_DIR", rules_dir)


def _install_mock(
    monkeypatch: pytest.MonkeyPatch,
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    *,
    csv_fixture: Path = _HAYABUSA_SAMPLE,
    exit_code: int = 0,
    stderr: bytes = b"",
) -> None:
    """Patch _run_native_log_tool to copy the fixture CSV and return a controlled result."""
    _case_dir, _evtx_dir, csv_out, *_ = env
    result = _LogResult(exit_code=exit_code, stdout=b"", stderr=stderr, elapsed_ms=1.0)

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        if exit_code == 0 and not stderr:
            csv_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(csv_fixture, csv_out)
        return result

    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa._run_native_log_tool", _fake)


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


def test_hayabusa_canonical_csv_returns_typed_hits(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Valid CSV round-trips; HayabusaOutput has typed hits with MITRE lists."""
    _force_gates_ok(monkeypatch, tmp_path)
    _install_mock(monkeypatch, env)

    resp = _invoke(env)

    assert resp.success is True
    assert resp.data is not None
    out: HayabusaOutput = resp.data
    assert out.row_count == 10
    assert out.truncated is False
    hit = out.hits[0]
    assert hit.RuleTitle == "PowerShell Encoded Command"
    assert hit.Level == "high"
    assert hit.EventID == 4104
    assert hit.Timestamp.tzinfo is not None
    assert isinstance(hit.MitreTags, list)
    assert "T1059.001" in hit.MitreTags
    assert isinstance(hit.MitreTactics, list)
    assert "execution" in hit.MitreTactics
    assert hit.Detection is not None
    assert resp.data_provenance.cmd_argv[0].endswith("hayabusa")
    assert "csv-timeline" in resp.data_provenance.cmd_argv


def test_hayabusa_audit_jsonl_written_on_success(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Success path writes a JSONL audit entry with row_count."""
    case_dir, *_ = env
    _force_gates_ok(monkeypatch, tmp_path)
    _install_mock(monkeypatch, env)

    resp = _invoke(env)

    assert resp.success is True
    log_path = case_dir / "audit" / "log.jsonl"
    assert log_path.exists()
    entry = json.loads(log_path.read_text().strip())
    assert entry["tool"] == "hayabusa_csv_timeline"
    assert entry["result_summary"]["row_count"] == 10
    assert entry["params"]["profile"] == "super-verbose"


def test_hayabusa_min_level_injects_flag(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """min_level='high' → --min-level high appears in cmd_argv."""
    _force_gates_ok(monkeypatch, tmp_path)
    captured: list[str] = []

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        captured.extend(argv)
        _, _, csv_out, *_ = env
        csv_out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(_HAYABUSA_SAMPLE, csv_out)
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa._run_native_log_tool", _fake)
    resp = _invoke(env, min_level="high")

    assert resp.success is True
    assert "--min-level" in captured
    idx = captured.index("--min-level")
    assert captured[idx + 1] == "high"


def test_hayabusa_include_tags_injects_comma_joined(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """include_tags=['PowerShell', 'Sysmon'] → --include-tag PowerShell,Sysmon."""
    _force_gates_ok(monkeypatch, tmp_path)
    captured: list[str] = []

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        captured.extend(argv)
        _, _, csv_out, *_ = env
        csv_out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(_HAYABUSA_SAMPLE, csv_out)
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa._run_native_log_tool", _fake)
    resp = _invoke(env, include_tags=["PowerShell", "Sysmon"])

    assert resp.success is True
    assert "--include-tag" in captured
    idx = captured.index("--include-tag")
    assert captured[idx + 1] == "PowerShell,Sysmon"


def test_hayabusa_zero_hits_not_truncated_is_success(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Header-only CSV (0 detections, not truncated) is a valid 'no threats' result."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        _, _, csv_out, *_ = env
        csv_out.parent.mkdir(parents=True, exist_ok=True)
        csv_out.write_bytes(
            b"Timestamp,RuleTitle,Level,Computer,Channel,EventID,RecordID,"
            b"Details,MitreTactics,MitreTags,OtherTags,RuleFile,EvtxFile\n"
        )
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa._run_native_log_tool", _fake)
    resp = _invoke(env)
    assert resp.success is True
    assert resp.data is not None
    assert resp.data.row_count == 0
    assert resp.data.truncated is False


# ---------------------------------------------------------------------------
# Gate refusals
# ---------------------------------------------------------------------------


def test_hayabusa_unregistered_evidence_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    tmp_path: Path,
) -> None:
    """Directory with unregistered EVTX → EVIDENCE_NOT_REGISTERED."""
    ghost_dir = tmp_path / "ghost_evtx"
    ghost_dir.mkdir()
    (ghost_dir / "Unknown.evtx").write_bytes(secrets.token_bytes(64))

    resp = _invoke(env, evtx_dir_override=ghost_dir)

    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.EVIDENCE_NOT_REGISTERED


def test_hayabusa_empty_evtx_dir_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    tmp_path: Path,
) -> None:
    """Directory with no *.evtx files → EVIDENCE_NOT_REGISTERED."""
    empty_dir = tmp_path / "empty_evtx"
    empty_dir.mkdir()

    resp = _invoke(env, evtx_dir_override=empty_dir)

    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.EVIDENCE_NOT_REGISTERED


def test_hayabusa_hash_mismatch_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
) -> None:
    """SHA256 drift on registered EVTX → EVIDENCE_TAMPERED."""
    _case_dir, evtx_dir, *_ = env
    (evtx_dir / "Security.evtx").write_bytes(secrets.token_bytes(256))

    resp = _invoke(env)

    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.EVIDENCE_TAMPERED


def test_hayabusa_mount_fail_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bad mount → MOUNT_NOT_RO_NOEXEC_NOSUID; audit JSONL written."""
    case_dir, *_ = env
    monkeypatch.setattr(
        "silentwitness_mcp.tools._log_hayabusa.check_mount",
        lambda: MountCheckResult(ok=False, advisories=["missing noexec"]),
    )

    resp = _invoke(env)

    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID
    assert (case_dir / "audit" / "log.jsonl").exists()


def test_hayabusa_not_installed_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """HAYABUSA_BIN absent → HAYABUSA_NOT_INSTALLED; advisory points at install.sh."""
    monkeypatch.setattr(
        "silentwitness_mcp.tools._log_hayabusa.check_mount",
        lambda: MountCheckResult(ok=True, advisories=[]),
    )
    ghost_bin = tmp_path / "no_hayabusa_here"
    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa.HAYABUSA_BIN", ghost_bin)

    resp = _invoke(env)

    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.HAYABUSA_NOT_INSTALLED
    assert "install.sh" in resp.advisories[0]


def test_hayabusa_rules_missing_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """HAYABUSA_RULES_DIR absent → HAYABUSA_RULES_MISSING; advisory points at install.sh."""
    monkeypatch.setattr(
        "silentwitness_mcp.tools._log_hayabusa.check_mount",
        lambda: MountCheckResult(ok=True, advisories=[]),
    )
    fake_bin = tmp_path / "hayabusa"
    fake_bin.touch()
    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa.HAYABUSA_BIN", fake_bin)
    ghost_rules = tmp_path / "no_rules_here"
    monkeypatch.setattr("silentwitness_mcp.tools._log_hayabusa.HAYABUSA_RULES_DIR", ghost_rules)

    resp = _invoke(env)

    assert resp.success is False
    assert resp.advisories[1] == LogFailureReason.HAYABUSA_RULES_MISSING
    assert "install.sh" in resp.advisories[0]
