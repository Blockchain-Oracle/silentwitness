"""Gate + edge-case tests for parse_prefetch.

Separated from test_disk_parse_prefetch.py to stay under the 400-LOC
CI budget. Covers: path-traversal guard, EVIDENCE_NOT_REGISTERED,
partial-parse truncation advisory, directory-evidence (-d) argv,
and corroboration propagation on refuse paths."""

from __future__ import annotations

import asyncio
import secrets
from pathlib import Path
from typing import Any

import pytest
from tests.unit.tools._disk_test_helpers import (
    force_dotnet,
    force_mount_ok,
    force_pecmd,
    install_dotnet_mock,
)

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._disk_common import DiskFailureReason
from silentwitness_mcp.tools._disk_models_prefetch import PREFETCH_CORROBORATION
from silentwitness_mcp.tools.disk import parse_prefetch

MODEL = "claude-sonnet-4-6"

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "disk"
_PREFETCH_SAMPLE = _FIXTURE_DIR / "prefetch_sample.csv"
_PREFETCH_BAD_ROW = _FIXTURE_DIR / "prefetch_with_bad_row.csv"
_CSV_FILENAME = "20260610160000_PECmd_Output.csv"


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-prefetch-gates"
    case_dir.mkdir()
    evidence = tmp_path / "NOTEPAD.EXE-D8414F97.pf"
    evidence.write_bytes(secrets.token_bytes(256))
    csv_out = case_dir / "tmp" / "prefetch_csv_out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.OTHER, audit_id="sift-aj-20260611-005")
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
        parse_prefetch(
            evidence_override or evidence,
            csv_out_override or csv_out,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


def test_parse_prefetch_csv_out_outside_case_dir_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """csv_out outside case_dir → OUTPUT_PARSE_FAILED; no subprocess spawn."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_pecmd(monkeypatch, tmp_path)
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    outside = tmp_path / "escape"
    envelope = _invoke(env, csv_out_override=outside)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.OUTPUT_PARSE_FAILED.value
    assert calls == []


def test_parse_prefetch_unregistered_evidence_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Evidence path never registered → EVIDENCE_NOT_REGISTERED; no spawn."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_pecmd(monkeypatch, tmp_path)
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    unregistered = tmp_path / "UNREGISTERED.pf"
    unregistered.write_bytes(b"fake pf data")
    envelope = _invoke(env, evidence_override=unregistered)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.EVIDENCE_NOT_REGISTERED.value
    assert calls == []


def test_parse_prefetch_partial_parse_surfaces_truncated_advisory(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CSV with one invalid row → success=True, truncated=True,
    partial-parse advisory mentions dropped count."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_pecmd(monkeypatch, tmp_path)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_BAD_ROW,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data is not None
    assert envelope.data.truncated is True
    assert envelope.data.row_count == 1
    assert any("partial parse" in a for a in envelope.advisories)
    assert any("1 dropped" in a for a in envelope.advisories)


def test_parse_prefetch_directory_evidence_uses_d_flag(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Passing a directory as evidence_path → PECmd invoked with -d flag."""
    force_dotnet(monkeypatch, tmp_path)
    force_pecmd(monkeypatch, tmp_path)
    # Bypass evidence/mount gates so a directory (unhashable by EvidenceRegistry)
    # can be used as evidence without a registered hash.
    monkeypatch.setattr(
        "silentwitness_mcp.tools._disk_pipeline.check_evidence_and_mount_gates",
        lambda *_a, **_kw: None,
    )
    dir_evidence = tmp_path / "PrefetchDir"
    dir_evidence.mkdir()
    case_dir, _, csv_out, logger, registry = env
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_SAMPLE,
        csv_out_dir=csv_out,
        csv_filename=_CSV_FILENAME,
    )
    envelope = asyncio.run(
        parse_prefetch(
            dir_evidence,
            csv_out,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )
    assert envelope.success is True
    # cmd_argv: [dotnet, pecmd.dll, --csv, csv_out, -d/-f, evidence_path]
    assert calls[0][4] == "-d"


def test_parse_prefetch_corroboration_propagates_on_pecmd_not_found(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Refused envelope (EZ_TOOL_NOT_FOUND) must carry PREFETCH_CORROBORATION."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_pecmd(monkeypatch, tmp_path, exists=False)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_PREFETCH_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.corroboration == PREFETCH_CORROBORATION
