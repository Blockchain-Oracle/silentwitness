"""Unit tests for :func:`chainsaw_hunt` — happy path and flag injection."""

from __future__ import annotations

import asyncio
import json
import secrets
from pathlib import Path
from typing import Any

import pytest

import silentwitness_mcp.tools._log_chainsaw as _chainsaw_mod
from silentwitness_common.types import EvidenceType
from silentwitness_mcp._lifecycle import MountCheckResult
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._log_chainsaw import chainsaw_hunt
from silentwitness_mcp.tools._log_common import _LogResult
from silentwitness_mcp.tools._log_models_chainsaw import ChainsawOutput

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
    case_dir = tmp_path / "case-chainsaw-01"
    case_dir.mkdir()
    evidence = evtx_dir / "Security.evtx"
    evidence.write_bytes(secrets.token_bytes(256))
    json_out = case_dir / "tmp" / "chainsaw_out.json"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.EVTX, audit_id="sift-aj-20260611-040")
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
    # Read module attributes at call time so monkeypatch overrides take effect.
    # Default-argument values are bound at function-definition time and would
    # capture the original (non-existent on dev boxes) SIFT paths instead.
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
    with_rules: bool = True,
    with_mapping: bool = True,
) -> tuple[Path, Path, Path]:
    monkeypatch.setattr(
        "silentwitness_mcp.tools._log_chainsaw.check_mount",
        lambda: MountCheckResult(ok=True, advisories=[]),
    )
    fake_bin = tmp_path / "chainsaw"
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
    return fake_bin, sigma_dir, mapping


def _install_mock(
    monkeypatch: pytest.MonkeyPatch,
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    *,
    json_fixture: Path = _CHAINSAW_SAMPLE,
    exit_code: int = 0,
    stderr: bytes = b"",
) -> None:
    """Patch _run_native_log_tool to write the fixture JSON and return a controlled result."""
    _case_dir, _evtx_dir, json_out, *_ = env
    result = _LogResult(exit_code=exit_code, stdout=b"", stderr=stderr, elapsed_ms=1.0)

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        if exit_code == 0 and not stderr:
            json_out.parent.mkdir(parents=True, exist_ok=True)
            json_out.write_bytes(json_fixture.read_bytes())
        return result

    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw._run_native_log_tool", _fake)


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


def test_chainsaw_canonical_json_returns_typed_hits(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Valid JSON round-trips; ChainsawOutput has typed hits with MitreAttack extracted."""
    _force_gates_ok(monkeypatch, tmp_path)
    _install_mock(monkeypatch, env)

    resp = _invoke(env)

    assert resp.success is True
    assert resp.data is not None
    out: ChainsawOutput = resp.data
    assert out.row_count == 3
    assert out.truncated is False
    hit = out.hits[0]
    assert hit.Name == "Suspicious PowerShell Encoded Command"
    assert hit.RuleLevel == "high"
    assert hit.RuleSource == "sigma"
    assert hit.EventID == 4104
    assert hit.Channel == "Microsoft-Windows-PowerShell/Operational"
    assert hit.Timestamp.tzinfo is not None
    assert "T1059.001" in hit.MitreAttack
    hit3 = out.hits[2]
    assert hit3.RuleSource == "chainsaw"
    assert hit3.RuleLevel == "medium"
    assert "T1055" in hit3.MitreAttack


def test_chainsaw_audit_jsonl_written_on_success(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Success path writes a JSONL audit entry with correct row_count."""
    case_dir, *_ = env
    _force_gates_ok(monkeypatch, tmp_path)
    _install_mock(monkeypatch, env)

    resp = _invoke(env)

    assert resp.success is True
    log_path = case_dir / "audit" / "log.jsonl"
    assert log_path.exists()
    entry = json.loads(log_path.read_text().strip())
    assert entry["tool"] == "chainsaw_hunt"
    assert entry["result_summary"]["row_count"] == 3
    assert "evtx_dir" in entry["params"]


def test_chainsaw_level_high_injects_high_critical(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """level='high' → --level high,critical in cmd_argv (architecture convention)."""
    _force_gates_ok(monkeypatch, tmp_path)
    captured: list[str] = []

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        captured.extend(argv)
        _, _, json_out, *_ = env
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_bytes(_CHAINSAW_SAMPLE.read_bytes())
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw._run_native_log_tool", _fake)
    resp = _invoke(env, level="high")

    assert resp.success is True
    assert "--level" in captured
    idx = captured.index("--level")
    assert captured[idx + 1] == "high,critical"


def test_chainsaw_level_critical_injects_exact(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """level='critical' → --level critical (no expansion)."""
    _force_gates_ok(monkeypatch, tmp_path)
    captured: list[str] = []

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        captured.extend(argv)
        _, _, json_out, *_ = env
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_bytes(_CHAINSAW_SAMPLE.read_bytes())
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw._run_native_log_tool", _fake)
    resp = _invoke(env, level="critical")

    assert resp.success is True
    assert "--level" in captured
    idx = captured.index("--level")
    assert captured[idx + 1] == "critical"


def test_chainsaw_zero_hits_not_truncated_is_success(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Empty JSON array (0 hits, truncated=False) is a valid 'no threats' result."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        _, _, json_out, *_ = env
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_bytes(b"[]")
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw._run_native_log_tool", _fake)
    resp = _invoke(env)

    assert resp.success is True
    assert resp.data is not None
    assert resp.data.row_count == 0
    assert resp.data.truncated is False


def test_chainsaw_metadata_flag_in_cmd_argv(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """--metadata must be in cmd_argv (load-bearing for Authors/Tags in output)."""
    _force_gates_ok(monkeypatch, tmp_path)
    captured: list[str] = []

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        captured.extend(argv)
        _, _, json_out, *_ = env
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_bytes(_CHAINSAW_SAMPLE.read_bytes())
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw._run_native_log_tool", _fake)
    resp = _invoke(env)

    assert resp.success is True
    assert "--metadata" in captured
    assert "hunt" in captured
    assert "-j" in captured
    assert resp.data_provenance.cmd_argv[0].endswith("chainsaw")


def test_chainsaw_level_none_omits_level_flag(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """level=None (default) must NOT inject --level into argv."""
    _force_gates_ok(monkeypatch, tmp_path)
    captured: list[str] = []

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        captured.extend(argv)
        _, _, json_out, *_ = env
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_bytes(b"[]")
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw._run_native_log_tool", _fake)
    resp = _invoke(env)

    assert resp.success is True
    assert "--level" not in captured
