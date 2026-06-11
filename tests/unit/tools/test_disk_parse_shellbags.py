"""Unit tests for :func:`parse_shellbags` — SBECmd CSV wrapper."""

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
    force_sbecmd,
    install_dotnet_mock,
)

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._disk_common import DiskFailureReason
from silentwitness_mcp.tools._disk_models_shellbags import (
    SHELLBAGS_CAVEATS,
    SHELLBAGS_CORROBORATION,
)
from silentwitness_mcp.tools.disk import parse_shellbags

MODEL = "claude-sonnet-4-6"

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "disk"
_SHELLBAGS_SAMPLE = _FIXTURE_DIR / "shellbags_sample.csv"
# SBECmd names output after the hive: <Username>_UsrClass.csv / <Username>_NTUSER.csv
_CSV_FILENAME = "AJ_UsrClass.csv"


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-shellbags-01"
    case_dir.mkdir()
    evidence = tmp_path / "UsrClass.dat"
    evidence.write_bytes(secrets.token_bytes(256))
    csv_out = case_dir / "tmp" / "shellbags_csv_out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.OTHER, audit_id="sift-aj-20260611-010")
    return (
        case_dir,
        evidence,
        csv_out,
        AuditLogger(case_dir, examiner="aj"),
        registry,
    )


def _invoke(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    *,
    evidence_override: Path | None = None,
    csv_out_override: Path | None = None,
) -> Any:
    case_dir, evidence, csv_out, logger, registry = env
    return asyncio.run(
        parse_shellbags(
            evidence_override or evidence,
            csv_out_override or csv_out,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


def test_parse_shellbags_canonical_csv_parses_with_verbatim_caveats(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Canonical CSV round-trips; caveats == SHELLBAGS_CAVEATS verbatim;
    corroboration matches SHELLBAGS_CORROBORATION; cmd_argv[1] is the
    SBECmd DLL path; row_count matches fixture (5 rows)."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path)
    case_dir, _, csv_out, _, _ = env
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=csv_out,
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data is not None
    assert envelope.data.row_count == 5
    assert envelope.data.truncated is False
    assert envelope.caveats == SHELLBAGS_CAVEATS
    assert envelope.corroboration == SHELLBAGS_CORROBORATION
    assert envelope.data_provenance.cmd_argv[1] == "/opt/zimmermantools/SBECmd.dll"
    assert (case_dir / "audit" / "disk.jsonl").exists()


def test_parse_shellbags_external_drive_row_has_icon_reference(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """External drive row (ShellType=Root) has icon_reference populated
    and AbsolutePath contains 'E:'."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    ext_entries = [e for e in envelope.data.entries if "E:" in e.absolute_path]
    assert len(ext_entries) == 1
    ext = ext_entries[0]
    assert ext.shell_type == "Root"
    assert ext.icon_reference is not None
    assert "ethereal.ico" in ext.icon_reference
    assert ext.hive == "UsrClass.dat"


def test_parse_shellbags_network_share_has_unc_path(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Network resource row AbsolutePath contains UNC path (\\\\server\\share);
    mru_position is None (blank in CSV) and last_interacted is populated."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    net_entries = [e for e in envelope.data.entries if e.shell_type == "Network Resource"]
    assert len(net_entries) == 1
    net = net_entries[0]
    assert "fileserver" in net.absolute_path
    assert net.mru_position is None
    assert net.first_interacted is None
    assert net.last_interacted is not None


def test_parse_shellbags_deleted_folder_has_no_last_interacted(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Deleted folder row: has_explored=False, last_interacted=None,
    mft_entry=None — all optional fields absent from a recovered entry."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    deleted = [e for e in envelope.data.entries if "deleted_folder" in e.absolute_path]
    assert len(deleted) == 1
    d = deleted[0]
    assert d.has_explored is False
    assert d.last_interacted is None
    assert d.mft_entry is None
    assert d.mft_sequence_number is None


def test_parse_shellbags_file_evidence_uses_f_flag(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Single hive file as evidence → SBECmd invoked with -f flag."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path)
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    _invoke(env)  # env[1] is a file (UsrClass.dat)
    # cmd_argv: [dotnet, sbecmd.dll, --csv, csv_out, -f/-d, evidence_path]
    assert calls[0][4] == "-f"


def test_parse_shellbags_directory_uses_d_flag(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Directory evidence → SBECmd invoked with -d flag."""
    force_dotnet(monkeypatch, tmp_path)
    force_sbecmd(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "silentwitness_mcp.tools._disk_pipeline.check_evidence_and_mount_gates",
        lambda *_a, **_kw: None,
    )
    hive_dir = tmp_path / "HiveDir"
    hive_dir.mkdir()
    # Add both hive files so UsrClass advisory doesn't fire.
    (hive_dir / "NTUSER.DAT").write_bytes(b"fake ntuser")
    (hive_dir / "UsrClass.dat").write_bytes(b"fake usrclass")
    case_dir, _, csv_out, logger, registry = env
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=csv_out,
        csv_filename=_CSV_FILENAME,
    )
    asyncio.run(
        parse_shellbags(
            hive_dir,
            csv_out,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert calls[0][4] == "-d"


def test_parse_shellbags_missing_usrclass_emits_advisory(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Directory with NTUSER.DAT only (no UsrClass.dat) → success=True
    and advisory about sparse results."""
    force_dotnet(monkeypatch, tmp_path)
    force_sbecmd(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "silentwitness_mcp.tools._disk_pipeline.check_evidence_and_mount_gates",
        lambda *_a, **_kw: None,
    )
    hive_dir = tmp_path / "NtUserOnlyDir"
    hive_dir.mkdir()
    (hive_dir / "NTUSER.DAT").write_bytes(b"fake ntuser")
    # No UsrClass.dat — advisory should fire.
    case_dir, _, csv_out, logger, registry = env
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=csv_out,
        csv_filename=_CSV_FILENAME,
    )
    envelope = asyncio.run(
        parse_shellbags(
            hive_dir,
            csv_out,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is True
    assert any("UsrClass.dat absent" in a for a in envelope.advisories)
    assert any("sparse" in a for a in envelope.advisories)


def test_parse_shellbags_sbecmd_not_installed_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """SBECmd DLL absent → EZ_TOOL_NOT_FOUND; no subprocess spawn."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path, exists=False)
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.EZ_TOOL_NOT_FOUND.value
    assert calls == []


def test_parse_shellbags_serilog_error_on_exit_zero_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """SBECmd exits 0 with [FTL] on stderr → TOOL_FAILED advisory.
    This is the primary reliability hazard: SBECmd calls Environment.Exit(0)
    on errors — only Serilog stderr parsing detects the failure."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path)
    serilog_stderr = b"[08:00:01 FTL] SBECmd: unable to open hive\n"
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
        proc=FakeProc(stdout=b"", stderr=serilog_stderr, returncode=0),
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.TOOL_FAILED.value


def test_parse_shellbags_corroboration_propagates_on_refuse(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Refused envelope (EZ_TOOL_NOT_FOUND) must carry SHELLBAGS_CORROBORATION."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path, exists=False)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.corroboration == SHELLBAGS_CORROBORATION


def test_parse_shellbags_audit_row_tool_name(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Audit JSONL row must carry tool == 'parse_shellbags'."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path)
    case_dir, _, csv_out, _, _ = env
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=csv_out,
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is True
    audit_log = case_dir / "audit" / "disk.jsonl"
    rows = [json.loads(line) for line in audit_log.read_text().splitlines() if line]
    assert rows[-1]["tool"] == "parse_shellbags"
