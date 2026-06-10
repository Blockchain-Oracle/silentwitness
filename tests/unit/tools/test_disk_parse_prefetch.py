"""Unit tests for :func:`parse_prefetch` — PECmd CSV wrapper."""

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
    force_pecmd,
    install_dotnet_mock,
)

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._disk_common import DiskFailureReason
from silentwitness_mcp.tools._disk_models_prefetch import PREFETCH_CAVEATS, PREFETCH_CORROBORATION
from silentwitness_mcp.tools.disk import parse_prefetch

MODEL = "claude-sonnet-4-6"

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "disk"
_PREFETCH_SAMPLE = _FIXTURE_DIR / "prefetch_sample.csv"

# PECmd names its output <timestamp>_PECmd_Output.csv
_CSV_FILENAME = "20260610160000_PECmd_Output.csv"


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-prefetch-01"
    case_dir.mkdir()
    # Register a single .pf file (registry hashes files, not directories).
    # parse_prefetch detects is_dir() at call time; passing a file uses -f.
    evidence = tmp_path / "NOTEPAD.EXE-D8414F97.pf"
    evidence.write_bytes(secrets.token_bytes(256))
    csv_out = case_dir / "tmp" / "prefetch_csv_out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.OTHER, audit_id="sift-aj-20260610-004")
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
        parse_prefetch(
            evidence_override or evidence,
            csv_out_override or csv_out,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


def test_parse_prefetch_canonical_csv_parses_with_verbatim_caveats(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Canonical CSV round-trips; caveats == PREFETCH_CAVEATS verbatim;
    corroboration matches PREFETCH_CORROBORATION; cmd_argv[1] is the
    PECmd DLL path; row_count matches fixture."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_pecmd(monkeypatch, tmp_path)
    case_dir, _, csv_out, _, _ = env
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_SAMPLE,
        csv_out_dir=csv_out,
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data is not None
    assert envelope.data.row_count == 5
    assert envelope.data.truncated is False
    assert envelope.caveats == PREFETCH_CAVEATS
    assert envelope.corroboration == PREFETCH_CORROBORATION
    assert envelope.data_provenance.cmd_argv[1] == "/opt/zimmermantools/PECmd.dll"
    assert (case_dir / "audit" / "disk.jsonl").exists()


def test_parse_prefetch_win10_row_has_seven_previous_run_times(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Win10/11 row: LastRun populated + PreviousRunTimes has 7 entries
    ordered most-recent-first (PreviousRun0 newest, PreviousRun6 oldest)."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_pecmd(monkeypatch, tmp_path)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    by_name = {e.executable_name: e for e in envelope.data.entries}
    notepad = by_name["NOTEPAD.EXE"]
    assert notepad.last_run is not None
    assert len(notepad.previous_run_times) == 7
    # Most-recent-first: each entry should be older than the previous
    for i in range(len(notepad.previous_run_times) - 1):
        assert notepad.previous_run_times[i] > notepad.previous_run_times[i + 1]


def test_parse_prefetch_win7_row_has_empty_previous_run_times(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Win7-flavor row: LastRun populated, PreviousRunTimes == []."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_pecmd(monkeypatch, tmp_path)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    by_name = {e.executable_name: e for e in envelope.data.entries}
    cmd = by_name["CMD.EXE"]
    assert cmd.last_run is not None
    assert cmd.previous_run_times == []


def test_parse_prefetch_multi_volume_note_preserved(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Entry with >2 volumes carries Volume0/1 fields and Note with
    overflow info."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_pecmd(monkeypatch, tmp_path)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    by_name = {e.executable_name: e for e in envelope.data.entries}
    suspect = by_name["SUSPECT.EXE"]
    assert suspect.volume0_name is not None
    assert suspect.volume1_name is not None
    assert suspect.note is not None
    assert ">2 volumes" in suspect.note


def test_parse_prefetch_parsing_error_surfaces_advisory(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Entry with ParsingError=True → parsing_error_count > 0 and
    advisory includes the executable name."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_pecmd(monkeypatch, tmp_path)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.data.parsing_error_count == 1
    assert any("CORRUPT.EXE" in a for a in envelope.advisories)


def test_parse_prefetch_files_loaded_split_correctly(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """FilesLoaded CSV cell is split on ', ' into list[str]; order preserved."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_pecmd(monkeypatch, tmp_path)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    by_name = {e.executable_name: e for e in envelope.data.entries}
    evil = by_name["EVIL.EXE"]
    assert len(evil.files_loaded) == 3
    assert r"\WINDOWS\SYSTEM32\EVIL.DLL" in evil.files_loaded
    assert len(evil.directories) == 2


def test_parse_prefetch_pecmd_not_installed_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """PECmd DLL absent → EZ_TOOL_NOT_FOUND; advisory contains
    'PECMD_NOT_INSTALLED'; no subprocess spawn."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_pecmd(monkeypatch, tmp_path, exists=False)
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.EZ_TOOL_NOT_FOUND.value
    assert "PECMD_NOT_INSTALLED" in envelope.advisories[0]
    assert "install.sh" in envelope.advisories[0]
    assert calls == []


def test_parse_prefetch_dotnet_missing_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """dotnet runtime absent → DOTNET_NOT_FOUND; no subprocess spawn."""
    force_dotnet(monkeypatch, tmp_path, exists=False)
    force_mount_ok(monkeypatch)
    force_pecmd(monkeypatch, tmp_path)
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.DOTNET_NOT_FOUND.value
    assert calls == []


def test_parse_prefetch_mount_not_ro_noexec_nosuid_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Mount missing ro/noexec/nosuid → MOUNT_NOT_RO_NOEXEC_NOSUID; no spawn."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_fail(monkeypatch)
    force_pecmd(monkeypatch, tmp_path)
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID.value
    assert calls == []


def test_parse_prefetch_tampered_evidence_returns_hash_mismatch(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """SHA256 drift after registration → EVIDENCE_HASH_MISMATCH; no spawn."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_pecmd(monkeypatch, tmp_path)
    # Tamper: overwrite .pf file bytes after registration
    env[1].write_bytes(b"TAMPERED_BYTES_AFTER_REGISTRATION")
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.EVIDENCE_HASH_MISMATCH.value
    assert calls == []


def test_parse_prefetch_serilog_error_on_exit_zero_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """PECmd may exit 0 with [FTL] on stderr — must surface as TOOL_FAILED."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_pecmd(monkeypatch, tmp_path)
    serilog_stderr = b"[08:00:01 FTL] PECmd: no .pf files found in directory\n"
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
        proc=FakeProc(stdout=b"", stderr=serilog_stderr, returncode=0),
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.TOOL_FAILED.value


def test_parse_prefetch_over_1024_entries_surfaces_cap_advisory(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """More than 1024 parsed entries → advisory about LRU eviction cap."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_pecmd(monkeypatch, tmp_path)
    # Build a CSV with 1025 rows
    header = (
        "Note,SourceFilename,SourceCreated,SourceModified,SourceAccessed,"
        "ExecutableName,Hash,Size,Version,RunCount,LastRun,"
        "PreviousRun0,PreviousRun1,PreviousRun2,PreviousRun3,"
        "PreviousRun4,PreviousRun5,PreviousRun6,"
        "Volume0Name,Volume0Serial,Volume0Created,"
        "Volume1Name,Volume1Serial,Volume1Created,"
        "FilesLoaded,Directories,ParsingError\n"
    )
    row_tmpl = (
        ",PF{i}.pf,2024-01-01,2024-01-01,2024-01-01,PROG{i}.EXE,AABB{i:04d},4096,30,1,"
        "2024-01-01 00:00:00,,,,,,,,\\VOLUME{{1}},F8A12345,2023-01-01,"
        ",,,\\PROG{i}.EXE,\\WINDOWS,False\n"
    )
    big_csv = tmp_path / "big_prefetch.csv"
    big_csv.write_text(header + "".join(row_tmpl.format(i=i) for i in range(1025)))
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=big_csv,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data.row_count == 1025
    assert any("1024" in a and "LRU" in a for a in envelope.advisories)


def test_parse_prefetch_audit_row_tool_name(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Audit JSONL row must carry tool == 'parse_prefetch'."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_pecmd(monkeypatch, tmp_path)
    case_dir, _, csv_out, _, _ = env
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_SAMPLE,
        csv_out_dir=csv_out,
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is True
    audit_log = case_dir / "audit" / "disk.jsonl"
    rows = [json.loads(line) for line in audit_log.read_text().splitlines() if line]
    assert rows[-1]["tool"] == "parse_prefetch"
