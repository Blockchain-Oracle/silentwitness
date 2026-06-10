"""Unit tests for :func:`parse_shimcache` — AppCompatCacheParser CSV wrapper."""

from __future__ import annotations

import asyncio
import json
import secrets
from pathlib import Path
from typing import Any

import pytest
from tests.unit.tools._disk_test_helpers import (
    FakeProc,
    force_dotnet,
    force_mount_fail,
    force_mount_ok,
    install_dotnet_mock,
)

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._disk_common import DiskFailureReason
from silentwitness_mcp.tools._disk_models_amcache import SHIMCACHE_CAVEATS, SHIMCACHE_CORROBORATION
from silentwitness_mcp.tools.disk import parse_shimcache

MODEL = "claude-sonnet-4-6"

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "disk"
_SHIMCACHE_SAMPLE = _FIXTURE_DIR / "shimcache_sample.csv"
_SHIMCACHE_BAD_ROW = _FIXTURE_DIR / "shimcache_with_bad_row.csv"

# AppCompatCacheParser names output <timestamp>_AppCompatCache_<hostname>_<controlset>.csv
_CSV_FILENAME = "20260610150000_AppCompatCache_DESKTOP-ABC_ControlSet001.csv"


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-shimcache-01"
    case_dir.mkdir()
    evidence = tmp_path / "SYSTEM"
    evidence.write_bytes(secrets.token_bytes(256))
    csv_out = case_dir / "tmp" / "shimcache_csv_out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.OTHER, audit_id="sift-aj-20260610-003")
    return (
        case_dir,
        evidence,
        csv_out,
        AuditLogger(case_dir, examiner="aj"),
        EvidenceRegistry(case_dir),
    )


def _invoke(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    *,
    evidence_override: Path | None = None,
    csv_out_override: Path | None = None,
) -> Any:
    case_dir, evidence, csv_out, logger, registry = env
    return asyncio.run(
        parse_shimcache(
            evidence_override or evidence,
            csv_out_override or csv_out,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


def test_parse_shimcache_canonical_csv_parses_with_verbatim_caveats(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Canonical CSV round-trips; caveats == SHIMCACHE_CAVEATS verbatim;
    corroboration matches SHIMCACHE_CORROBORATION; cmd_argv[1] is the
    AppCompatCacheParser DLL path."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    case_dir, _, csv_out, _, _ = env
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHIMCACHE_SAMPLE,
        csv_out_dir=csv_out,
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data is not None
    assert envelope.data.row_count == 7
    assert envelope.data.truncated is False
    assert envelope.caveats == SHIMCACHE_CAVEATS
    assert envelope.corroboration == SHIMCACHE_CORROBORATION
    assert envelope.data_provenance.cmd_argv[1] == "/opt/zimmermantools/AppCompatCacheParser.dll"
    assert (case_dir / "audit" / "disk.jsonl").exists()


def test_parse_shimcache_executed_tristate_present(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """At least one entry has Executed=='Yes' (Win7-style) and at least
    one has Executed=='NA' (Win10/11-style) — tri-state is preserved."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHIMCACHE_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    executed_values = {e.executed for e in envelope.data.entries}
    assert "Yes" in executed_values
    assert "No" in executed_values
    assert "NA" in executed_values


def test_parse_shimcache_entries_sorted_by_position(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Entries must be sorted by (cache_entry_position, control_set) asc —
    position 0 is the most-recently-evaluated entry."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHIMCACHE_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    positions = [(e.cache_entry_position, e.control_set) for e in envelope.data.entries]
    assert positions == sorted(positions)


def test_parse_shimcache_serilog_error_on_exit_zero_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """AppCompatCacheParser may exit 0 with [FTL] on stderr — must
    surface as TOOL_FAILED."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    serilog_stderr = b"[08:00:01 FTL] Could not find SYSTEM hive ControlSet\n"
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHIMCACHE_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
        proc=FakeProc(stdout=b"", stderr=serilog_stderr, returncode=0),
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.TOOL_FAILED.value


def test_parse_shimcache_unregistered_evidence_refuses_without_spawn(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Unregistered hive → EVIDENCE_NOT_REGISTERED; no subprocess spawn."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    unreg = env[0].parent / "SYSTEM_HALLUCINATED"
    unreg.write_bytes(b"x")
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHIMCACHE_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env, evidence_override=unreg)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.EVIDENCE_NOT_REGISTERED.value
    assert calls == []
    assert envelope.caveats == SHIMCACHE_CAVEATS


def test_parse_shimcache_audit_row_tool_name(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Audit JSONL row must carry tool == 'parse_shimcache'."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    case_dir, _, csv_out, _, _ = env
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHIMCACHE_SAMPLE,
        csv_out_dir=csv_out,
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is True
    audit_log = case_dir / "audit" / "disk.jsonl"
    rows = [json.loads(line) for line in audit_log.read_text().splitlines() if line]
    assert rows[-1]["tool"] == "parse_shimcache"


def test_parse_shimcache_dotnet_missing_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """dotnet not installed → DOTNET_NOT_FOUND; no subprocess spawn."""
    force_dotnet(monkeypatch, tmp_path, exists=False)
    force_mount_ok(monkeypatch)
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHIMCACHE_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.DOTNET_NOT_FOUND.value
    assert "install.sh" in envelope.advisories[0]
    assert calls == []


def test_parse_shimcache_mount_not_ro_noexec_nosuid_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Mount missing ro/noexec/nosuid flags → MOUNT_NOT_RO_NOEXEC_NOSUID; no spawn."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_fail(monkeypatch)
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHIMCACHE_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID.value
    assert calls == []


def test_parse_shimcache_tampered_evidence_returns_hash_mismatch(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """SHA256 drift after registration → EVIDENCE_HASH_MISMATCH; no spawn."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    env[1].write_bytes(b"TAMPERED_BYTES_AFTER_REGISTRATION")
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHIMCACHE_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.EVIDENCE_HASH_MISMATCH.value
    assert calls == []


def test_parse_shimcache_partial_parse_surfaces_truncated_advisory(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CSV with one unparseable row → success=True, truncated=True, partial advisory."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHIMCACHE_BAD_ROW,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data is not None
    assert envelope.data.truncated is True
    assert envelope.data.row_count == 6
    assert any("partial parse" in a for a in envelope.advisories)


def test_parse_shimcache_csv_out_outside_case_dir_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """csv_out outside case_dir → OUTPUT_PARSE_FAILED; path-traversal guard."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    outside = tmp_path.parent / "outside_case_dir"
    envelope = _invoke(env, csv_out_override=outside)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.OUTPUT_PARSE_FAILED.value
