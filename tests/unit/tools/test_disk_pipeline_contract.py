"""Cross-cutting contract tests for the disk-family pipeline.

Parallel to :mod:`tests.unit.test_vol_pipeline_contract` — pins
invariants that hold for EVERY ``parse_*`` wrapper through the
shared ``run_disk_wrapper`` orchestrator, not just ``parse_mft``."""

from __future__ import annotations

import asyncio
import secrets
import shutil
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from tests.unit.tools._disk_test_helpers import (
    FakeProc,
    force_dotnet,
    force_mount_ok,
    install_dotnet_mock,
)

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._disk_common import (
    DiskFailureReason,
    read_csv_with_truncation_from_bytes,
)
from silentwitness_mcp.tools._disk_models import MFT_CAVEATS, MftOutput
from silentwitness_mcp.tools.disk import parse_mft

_MFT_SAMPLE = Path(__file__).resolve().parents[2] / "fixtures" / "disk" / "mft_sample.csv"
_MFT_BAD_ROW = Path(__file__).resolve().parents[2] / "fixtures" / "disk" / "mft_with_bad_row.csv"

# ---------------------------------------------------------------------------
# read_csv_with_truncation_from_bytes — exception-branch coverage
# ---------------------------------------------------------------------------


def test_read_csv_truncation_handles_invalid_utf8_via_truncated_flag() -> None:
    """A UTF-8 decode failure mid-stream MUST surface as ``truncated``
    rather than blowing up the wrapper — partial recovery is the
    forensic-preferred shape (story-parse-mft, 'Truncation detection')."""
    # Raw bytes that are not valid UTF-8 (lone continuation 0xFF).
    raw = b"\xff\xfe garbage bytes that are not utf-8"
    rows, truncated = read_csv_with_truncation_from_bytes(raw)
    assert rows == []
    assert truncated is True


def test_read_csv_truncation_handles_unbalanced_quote() -> None:
    """A row with an unclosed quoted field raises ``csv.Error`` mid-
    stream — caught + surfaced as truncated."""
    raw = b'h1,h2\n"unclosed,value\n'
    _rows, truncated = read_csv_with_truncation_from_bytes(raw)
    # csv.Error or post-read None-scan; either way truncated=True.
    assert truncated is True


def test_read_csv_truncation_short_last_row_dropped_via_post_read_scan() -> None:
    """When the LAST row has fewer cells than the header, DictReader
    silently pads with None. The post-read scan drops that row and
    flags ``truncated`` — the dual mechanism (csv.Error catch +
    post-read None-scan) catches both mid-stream and silently-padded
    short rows."""
    raw = b"a,b,c\n1,2,3\n4,5\n"
    rows, truncated = read_csv_with_truncation_from_bytes(raw)
    assert len(rows) == 1
    assert rows[0] == {"a": "1", "b": "2", "c": "3"}
    assert truncated is True


def test_read_csv_truncation_clean_input_returns_truncated_false() -> None:
    """No truncation, no false-positive — the canary against an
    overzealous post-read scan."""
    raw = b"a,b,c\n1,2,3\n4,5,6\n"
    rows, truncated = read_csv_with_truncation_from_bytes(raw)
    assert len(rows) == 2
    assert truncated is False


# ---------------------------------------------------------------------------
# MftOutput — record-identity uniqueness invariant
# ---------------------------------------------------------------------------


def _entry(entry_number: int = 1, sequence_number: int = 1) -> dict[str, Any]:
    """Minimal MFTEntry-shape dict for direct model_validate calls."""
    return {"EntryNumber": entry_number, "SequenceNumber": sequence_number}


def test_mft_output_rejects_duplicate_record_identity() -> None:
    """``(entry_number, sequence_number)`` is NTFS-canonical; duplicates
    in the output indicate CSV concatenation, stale-glob residue, or
    schema drift. The validator at MftOutput._check_record_identity_unique
    MUST fail closed."""
    from silentwitness_mcp.tools._disk_models import MFTEntry

    dup_a = MFTEntry.model_validate(_entry(42, 1))
    dup_b = MFTEntry.model_validate(_entry(42, 1))
    with pytest.raises(ValidationError, match="duplicate MFT record identity"):
        MftOutput(entries=(dup_a, dup_b))


def test_mft_output_accepts_distinct_record_identities() -> None:
    """Same EntryNumber + different SequenceNumber is legitimate
    (NTFS record-reuse semantics)."""
    from silentwitness_mcp.tools._disk_models import MFTEntry

    a = MFTEntry.model_validate(_entry(42, 1))
    b = MFTEntry.model_validate(_entry(42, 2))
    out = MftOutput(entries=(a, b))
    assert out.row_count == 2


# ---------------------------------------------------------------------------
# MFTEntry — extra="forbid" defense-in-depth on @computed_field migration
# ---------------------------------------------------------------------------


def test_mft_entry_rejects_is_deleted_as_input_under_extra_forbid() -> None:
    """``IsDeleted`` is a ``@computed_field`` derived from ``not in_use``,
    not a wire column. ``extra="forbid"`` rejects any caller that passes
    it explicitly to ``model_validate``, preventing derivation desync."""
    from silentwitness_mcp.tools._disk_models import MFTEntry

    with pytest.raises(ValidationError, match="Extra inputs"):
        MFTEntry.model_validate({"EntryNumber": 1, "SequenceNumber": 1, "IsDeleted": True})


def test_mft_entry_rejects_si_fn_delta_as_input_under_extra_forbid() -> None:
    """``SiFnDelta`` is a ``@computed_field`` aliasing ``timestomped``,
    not a wire column. ``extra="forbid"`` rejects explicit supply."""
    from silentwitness_mcp.tools._disk_models import MFTEntry

    with pytest.raises(ValidationError, match="Extra inputs"):
        MFTEntry.model_validate({"EntryNumber": 1, "SequenceNumber": 1, "SiFnDelta": True})


# ---------------------------------------------------------------------------
# Pipeline behaviors exercised through parse_mft as representative caller
# (parallel to tests/unit/test_vol_pipeline_contract.py using vol_netscan).
# ---------------------------------------------------------------------------


@pytest.fixture
def disk_env(
    tmp_path: Path,
) -> tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-pipeline-01"
    case_dir.mkdir()
    evidence = tmp_path / "MFT"
    evidence.write_bytes(secrets.token_bytes(256))
    csv_out = case_dir / "tmp" / "csv_out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.OTHER, audit_id="sift-aj-20260610-001")
    return (
        case_dir,
        evidence,
        csv_out,
        AuditLogger(case_dir, examiner="aj"),
        EvidenceRegistry(case_dir),
    )


def _run_parse_mft(env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]) -> Any:
    case_dir, evidence, csv_out, logger, registry = env
    return asyncio.run(
        parse_mft(
            evidence,
            csv_out,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used="claude-sonnet-4-6",
        )
    )


def test_pipeline_timeout_refuses_with_caveats_intact(
    disk_env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A subprocess timeout MUST surface as TOOL_TIMEOUT (NOT
    TOOL_FAILED) so the agent can distinguish "MFTECmd hung on a
    corrupt $MFT" from "MFTECmd died". Caveats propagate verbatim."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)

    async def _timeout(*_a: Any, **_k: Any) -> FakeProc:
        raise TimeoutError("dotnet exceeded timeout")

    monkeypatch.setattr(
        "silentwitness_mcp.tools._disk_common.asyncio.create_subprocess_exec", _timeout
    )
    envelope = _run_parse_mft(disk_env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.TOOL_TIMEOUT.value
    assert envelope.caveats == MFT_CAVEATS


def test_pipeline_glob_miss_after_exit_zero_surfaces_output_parse_failed(
    disk_env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Glob-miss after exit 0: MFTECmd exited cleanly but no CSV
    matching the pattern exists — output-name drift."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    install_dotnet_mock(
        monkeypatch,
        csv_fixture=_MFT_SAMPLE,
        csv_out_dir=disk_env[2],
        csv_filename="WRONG_FILENAME.csv",
    )
    envelope = _run_parse_mft(disk_env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.OUTPUT_PARSE_FAILED.value
    assert "no CSV matching" in envelope.advisories[0]


def test_pipeline_stale_mtime_csv_surfaces_output_parse_failed(
    disk_env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A CSV whose mtime predates spawn_wall is stale residue."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    csv_out = disk_env[2]
    csv_filename = "20260610150000_MFTECmd_MFT_Output.csv"

    async def _fake(*_argv: str, **_kw: Any) -> FakeProc:
        csv_out.mkdir(parents=True, exist_ok=True)
        target = csv_out / csv_filename
        shutil.copy(_MFT_SAMPLE, target)
        import os
        import time as _time

        ago = _time.time() - 3600.0
        os.utime(target, (ago, ago))
        return FakeProc(stdout=b"", stderr=b"", returncode=0)

    monkeypatch.setattr(
        "silentwitness_mcp.tools._disk_common.asyncio.create_subprocess_exec", _fake
    )
    envelope = _run_parse_mft(disk_env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.OUTPUT_PARSE_FAILED.value
    assert "predates spawn" in envelope.advisories[0]


def test_pipeline_row_by_row_partial_parse_surfaces_skipped(
    disk_env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A row with malformed-but-CSV-shape content triggers per-row
    ValidationError. The row-by-row try/except surfaces success=True
    with truncated=True via the skipped-rows path."""
    force_dotnet(monkeypatch, tmp_path)
    force_mount_ok(monkeypatch)
    csv_out = disk_env[2]
    install_dotnet_mock(monkeypatch, csv_fixture=_MFT_BAD_ROW, csv_out_dir=csv_out)
    envelope = _run_parse_mft(disk_env)
    assert envelope.success is True
    assert envelope.data is not None
    assert envelope.data.row_count == 2
    assert envelope.data.truncated is True
    assert any("partial parse" in a for a in envelope.advisories)
