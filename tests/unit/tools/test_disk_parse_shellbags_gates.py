"""Gate + edge-case tests for parse_shellbags.

Separated from test_disk_parse_shellbags.py to stay under the 400-LOC
CI budget. Covers: EVIDENCE_NOT_REGISTERED, EVIDENCE_HASH_MISMATCH,
DOTNET_NOT_FOUND, MOUNT_NOT_RO_NOEXEC_NOSUID, OUTPUT_PARSE_FAILED
(path-traversal), partial-parse truncation advisory, and corroboration
propagation on refuse paths."""

from __future__ import annotations

import asyncio
import secrets
from pathlib import Path
from typing import Any

import pytest
from tests.unit.tools._disk_test_helpers import (
    force_dotnet,
    force_mount_fail,
    force_mount_ok,
    force_sbecmd,
    install_dotnet_mock,
)

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._disk_common import DiskFailureReason
from silentwitness_mcp.tools._disk_models_shellbags import SHELLBAGS_CORROBORATION
from silentwitness_mcp.tools.disk import parse_shellbags

MODEL = "claude-sonnet-4-6"

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "disk"
_SHELLBAGS_SAMPLE = _FIXTURE_DIR / "shellbags_sample.csv"
_SHELLBAGS_BAD_ROW = _FIXTURE_DIR / "shellbags_with_bad_row.csv"
_CSV_FILENAME = "AJ_UsrClass.csv"


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-shellbags-gates"
    case_dir.mkdir()
    evidence = tmp_path / "UsrClass.dat"
    evidence.write_bytes(secrets.token_bytes(256))
    csv_out = case_dir / "tmp" / "shellbags_csv_out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.OTHER, audit_id="sift-aj-20260611-011")
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


def test_parse_shellbags_csv_out_outside_case_dir_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """csv_out outside case_dir → OUTPUT_PARSE_FAILED; no subprocess spawn."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path)
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    outside = tmp_path / "escape"
    envelope = _invoke(env, csv_out_override=outside)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.OUTPUT_PARSE_FAILED.value
    assert calls == []


def test_parse_shellbags_unregistered_evidence_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Evidence path never registered → EVIDENCE_NOT_REGISTERED; no spawn."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path)
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    unregistered = tmp_path / "UNREGISTERED.dat"
    unregistered.write_bytes(b"fake hive data")
    envelope = _invoke(env, evidence_override=unregistered)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.EVIDENCE_NOT_REGISTERED.value
    assert calls == []


def test_parse_shellbags_tampered_evidence_returns_hash_mismatch(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """SHA256 drift after registration → EVIDENCE_HASH_MISMATCH; no spawn."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path)
    env[1].write_bytes(b"TAMPERED_BYTES_AFTER_REGISTRATION")
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.EVIDENCE_HASH_MISMATCH.value
    assert calls == []


def test_parse_shellbags_dotnet_missing_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """dotnet runtime absent → DOTNET_NOT_FOUND; no subprocess spawn."""
    force_dotnet(monkeypatch, tmp_path, exists=False)
    force_mount_ok(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path)
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.DOTNET_NOT_FOUND.value
    assert calls == []


def test_parse_shellbags_mount_not_ro_noexec_nosuid_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Mount missing ro/noexec/nosuid → MOUNT_NOT_RO_NOEXEC_NOSUID; no spawn."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_fail(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path)
    calls = install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID.value
    assert calls == []


def test_parse_shellbags_partial_parse_surfaces_truncated_advisory(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CSV with one invalid row (unparseable LastWriteTime) → success=True,
    truncated=True, partial-parse advisory mentions dropped count."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_BAD_ROW,
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


def test_parse_shellbags_corroboration_propagates_on_dotnet_not_found(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Refused envelope (DOTNET_NOT_FOUND) must carry SHELLBAGS_CORROBORATION."""
    force_dotnet(monkeypatch, tmp_path, exists=False)
    force_mount_ok(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.corroboration == SHELLBAGS_CORROBORATION


def test_parse_shellbags_corroboration_propagates_on_mount_fail(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Refused envelope (MOUNT_NOT_RO_NOEXEC_NOSUID) carries SHELLBAGS_CORROBORATION."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_fail(monkeypatch)
    force_sbecmd(monkeypatch, tmp_path)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_SHELLBAGS_SAMPLE,
        csv_out_dir=env[2],
        csv_filename=_CSV_FILENAME,
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.corroboration == SHELLBAGS_CORROBORATION
