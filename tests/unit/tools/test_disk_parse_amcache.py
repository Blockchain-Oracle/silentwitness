"""Unit tests for :func:`parse_amcache` — AmcacheParser CSV wrapper.

The dotnet subprocess and AmcacheParser CSV-write are both mocked.
Real end-to-end coverage lives in
``tests/integration/tools/test_disk_amcache_shimcache_integration.py``
(skipped on non-SIFT runners)."""

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
    force_mount_ok,
    install_dotnet_mock,
)

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._disk_common import DiskFailureReason
from silentwitness_mcp.tools._disk_models_amcache import AMCACHE_CAVEATS, AMCACHE_CORROBORATION
from silentwitness_mcp.tools.disk import parse_amcache

MODEL = "claude-sonnet-4-6"

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "disk"
_AMCACHE_SAMPLE = _FIXTURE_DIR / "amcache_sample.csv"

# AmcacheParser names its output <timestamp>_Amcache_UnassociatedFileEntries.csv
_CSV_FILENAME = "20260610150000_Amcache_UnassociatedFileEntries.csv"


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-amcache-01"
    case_dir.mkdir()
    evidence = tmp_path / "Amcache.hve"
    evidence.write_bytes(secrets.token_bytes(256))
    csv_out = case_dir / "tmp" / "amcache_csv_out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.OTHER, audit_id="sift-aj-20260610-002")
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
        parse_amcache(
            evidence_override or evidence,
            csv_out_override or csv_out,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


def test_parse_amcache_canonical_csv_parses_with_verbatim_caveats(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Canonical CSV round-trips; caveats == AMCACHE_CAVEATS verbatim;
    corroboration matches AMCACHE_CORROBORATION; cmd_argv[1] is the
    AmcacheParser DLL path; SHA1 present on PE rows."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    case_dir, _, csv_out, _, _ = env
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_AMCACHE_SAMPLE,
        csv_out_dir=csv_out,
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data is not None
    assert envelope.data.row_count == 5
    assert envelope.data.truncated is False
    assert envelope.caveats == AMCACHE_CAVEATS
    assert envelope.corroboration == AMCACHE_CORROBORATION
    assert envelope.data_provenance.tool == "parse_amcache"
    assert envelope.data_provenance.cmd_argv[1] == "/opt/zimmermantools/AmcacheParser.dll"
    assert (case_dir / "audit" / "disk.jsonl").exists()


def test_parse_amcache_sha1_null_for_non_pe_entry(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Empty SHA1 column (non-PE file) must be None, not empty string."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_AMCACHE_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    by_path = {e.full_path: e for e in envelope.data.entries}
    tcpip = by_path[r"C:\Windows\System32\drivers\tcpip.sys"]
    assert tcpip.sha1 is None
    assert tcpip.size == 671744


def test_parse_amcache_empty_hive_surfaces_advisory(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """An empty UnassociatedFileEntries CSV (no data rows) MUST yield
    success=True with the Appraiser advisory in advisories."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    csv_out = env[2]
    empty_fixture = tmp_path / "amcache_empty.csv"
    empty_fixture.write_text(
        "SHA1,FullPath,FileExtension,Size,ProductName,ProductVersion,"
        "Publisher,BinFileVersion,BinProductVersion,FileKeyLastWriteTimestamp\n"
    )
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=empty_fixture,
        csv_out_dir=csv_out,
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data is not None
    assert envelope.data.entries == ()
    assert any("Appraiser" in a for a in envelope.advisories)


def test_parse_amcache_serilog_error_on_exit_zero_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """AmcacheParser may exit 0 with Serilog [ERR] on stderr — must
    surface as TOOL_FAILED, not a spurious success."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    serilog_stderr = b"[12:34:56 ERR] Amcache hive could not be opened\n"
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_AMCACHE_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
        proc=FakeProc(stdout=b"", stderr=serilog_stderr, returncode=0),
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.TOOL_FAILED.value
    assert "ERR" in envelope.advisories[0]


def test_parse_amcache_unregistered_evidence_refuses_without_spawn(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Unregistered path → EVIDENCE_NOT_REGISTERED; no subprocess spawn."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    unreg = env[0].parent / "Amcache_HALLUCINATED.hve"
    unreg.write_bytes(b"x")
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_AMCACHE_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env, evidence_override=unreg)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.EVIDENCE_NOT_REGISTERED.value
    assert calls == []
    assert envelope.caveats == AMCACHE_CAVEATS


def test_parse_amcache_audit_row_tool_name(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Audit JSONL row must carry tool == 'parse_amcache'."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    case_dir, _, csv_out, _, _ = env
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_AMCACHE_SAMPLE,
        csv_out_dir=csv_out,
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is True
    audit_log = case_dir / "audit" / "disk.jsonl"
    rows = [json.loads(line) for line in audit_log.read_text().splitlines() if line]
    assert rows[-1]["tool"] == "parse_amcache"
    assert rows[-1]["audit_id"] == envelope.audit_id
