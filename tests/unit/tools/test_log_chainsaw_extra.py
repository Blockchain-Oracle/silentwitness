"""Extra coverage for chainsaw_hunt — exception branches and partial-parse paths."""

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

# Fixture with two valid entries and one structurally bad entry (missing "level")
# to exercise the partial-parse path (truncated=True but row_count > 0).
_PARTIAL_JSON = b"""
[
  {
    "group": "Execution",
    "kind": "individual",
    "document": {"data": {"Event": {"System": {
        "Channel": "Microsoft-Windows-PowerShell/Operational",
        "EventID": 4104,
        "EventRecordID": 1001
    }}}},
    "name": "PowerShell Encoded Command",
    "timestamp": "2025-01-15T08:23:41Z",
    "authors": ["Florian Roth"],
    "level": "high",
    "source": "sigma",
    "tags": ["attack.t1059.001"]
  },
  {
    "group": "Defense Evasion",
    "kind": "individual",
    "document": {"data": {"Event": {"System": {
        "Channel": "Security",
        "EventID": 1102,
        "EventRecordID": 2048
    }}}},
    "name": "Audit Log Cleared",
    "timestamp": "2025-01-15T09:11:22Z",
    "authors": [],
    "level": "INVALID_LEVEL_VALUE_NOT_IN_LITERAL",
    "source": "sigma",
    "tags": []
  }
]
"""


@pytest.fixture
def evtx_dir(tmp_path: Path) -> Path:
    d = tmp_path / "evtx"
    d.mkdir()
    return d


@pytest.fixture
def env(tmp_path: Path, evtx_dir: Path) -> tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-chainsaw-extra"
    case_dir.mkdir()
    evidence = evtx_dir / "Security.evtx"
    evidence.write_bytes(secrets.token_bytes(256))
    json_out = case_dir / "tmp" / "chainsaw_out.json"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.EVTX, audit_id="sift-aj-20260611-042")
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
) -> Any:
    case_dir, evtx_dir, json_out, logger, registry = env
    return asyncio.run(
        chainsaw_hunt(
            evtx_dir_override or evtx_dir,
            json_out_override or json_out,
            _chainsaw_mod.SIGMA_RULES_DIR,
            _chainsaw_mod.CHAINSAW_MAPPING_DEFAULT,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


def _force_gates_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "silentwitness_mcp.tools._log_chainsaw.check_mount",
        lambda: MountCheckResult(ok=True, advisories=[]),
    )
    fake_bin = tmp_path / "chainsaw"
    fake_bin.touch()
    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw.CHAINSAW_BIN", fake_bin)
    sigma_dir = tmp_path / "sigma"
    sigma_dir.mkdir()
    (sigma_dir / "proc_create.yml").touch()
    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw.SIGMA_RULES_DIR", sigma_dir)
    mapping = tmp_path / "mappings" / "map.yml"
    mapping.parent.mkdir()
    mapping.touch()
    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw.CHAINSAW_MAPPING_DEFAULT", mapping)


def _install_mock_with_json(
    monkeypatch: pytest.MonkeyPatch,
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    content: bytes,
) -> None:
    _case_dir, _evtx_dir, json_out, *_ = env

    async def _fake(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_bytes(content)
        return _LogResult(exit_code=0, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools._log_chainsaw._run_native_log_tool", _fake)


# ---------------------------------------------------------------------------
# verify_hash exception branches
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exc",
    [
        EvidenceMissingOnDiskError("vanished"),
        EvidenceRegistryError("internal"),
    ],
)
def test_chainsaw_verify_hash_exception_refuses(
    exc: Exception,
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """verify_hash raising registry errors → EVIDENCE_TAMPERED refusal."""
    _force_gates_ok(monkeypatch, tmp_path)

    def _raise(_path: Path) -> Any:
        raise exc

    _, _, _, _, registry = env
    monkeypatch.setattr(registry, "verify_hash", _raise)
    resp = _invoke(env)

    assert resp.success is False
    assert any("EVIDENCE_TAMPERED" in a for a in resp.advisories)
    assert resp.advisories[1] == LogFailureReason.EVIDENCE_TAMPERED.value


# ---------------------------------------------------------------------------
# Subprocess spawn failure
# ---------------------------------------------------------------------------


def test_chainsaw_spawn_failed_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """OSError from _run_native_log_tool → TOOL_FAILED with non-empty cmd_argv."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _raise_oserror(bin_path: Any, argv: Any, *, timeout_s: Any = 600.0) -> _LogResult:
        raise OSError("exec permission denied")

    monkeypatch.setattr(
        "silentwitness_mcp.tools._log_chainsaw._run_native_log_tool", _raise_oserror
    )
    resp = _invoke(env)

    assert resp.success is False
    assert any("TOOL_SPAWN_FAILED" in a for a in resp.advisories)
    assert resp.advisories[1] == LogFailureReason.TOOL_FAILED.value
    assert len(resp.data_provenance.cmd_argv) > 0


# ---------------------------------------------------------------------------
# Blob persistence failure
# ---------------------------------------------------------------------------


def test_chainsaw_blob_persist_failed_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """OSError from persist_blob → BLOB_PERSIST_FAILED advisory."""
    _force_gates_ok(monkeypatch, tmp_path)
    _install_mock_with_json(monkeypatch, env, _CHAINSAW_SAMPLE.read_bytes())

    monkeypatch.setattr(
        "silentwitness_mcp.tools._log_chainsaw.persist_blob",
        lambda *_a, **_kw: (_ for _ in ()).throw(OSError("disk full")),
    )
    resp = _invoke(env)

    assert resp.success is False
    assert any("BLOB_PERSIST_FAILED" in a for a in resp.advisories)


# ---------------------------------------------------------------------------
# Partial-parse success path
# ---------------------------------------------------------------------------


def test_chainsaw_partial_parse_succeeds_with_advisory(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Mixed JSON (some valid hits, one bad entry) → success=True with partial advisory."""
    _force_gates_ok(monkeypatch, tmp_path)
    _install_mock_with_json(monkeypatch, env, _PARTIAL_JSON)

    resp = _invoke(env)

    assert resp.success is True
    assert resp.data is not None
    assert resp.data.row_count == 1
    assert resp.data.truncated is True
    assert any("partial parse" in a for a in resp.advisories)
    log_path = env[0] / "audit" / "log.jsonl"
    entry = json.loads(log_path.read_text().strip())
    assert entry["result_summary"]["truncated"] is True


# ---------------------------------------------------------------------------
# group entries do NOT mark truncated
# ---------------------------------------------------------------------------


def test_chainsaw_group_entries_skipped_without_truncated(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """kind='group' (native correlated rule summary) skipped without truncated=True."""
    _force_gates_ok(monkeypatch, tmp_path)
    mixed = (
        b'[{"group":"G","kind":"group","document":{},"name":"Group","timestamp":'
        b'"2025-01-15T08:00:00Z","level":"high","source":"sigma","tags":[],"authors":[]}, '
    ) + _CHAINSAW_SAMPLE.read_bytes()[1:]  # prepend a group entry before the real hits
    _install_mock_with_json(monkeypatch, env, mixed)

    resp = _invoke(env)

    assert resp.success is True
    assert resp.data is not None
    assert resp.data.truncated is False
    assert resp.data.row_count == 3
