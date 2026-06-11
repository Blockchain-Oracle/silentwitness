"""Integration test for :func:`hayabusa_csv_timeline` — skipped on non-SIFT hosts."""

from __future__ import annotations

import asyncio
import secrets
from pathlib import Path

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._log_hayabusa import hayabusa_csv_timeline

_HAYABUSA = Path("/opt/hayabusa/hayabusa")
_RULES = Path("/opt/hayabusa-rules")
_FIXTURE_EVTX = Path(__file__).resolve().parents[2] / "fixtures" / "log" / "Security.evtx"

pytestmark = pytest.mark.skipif(
    not _HAYABUSA.exists(),
    reason="Hayabusa not installed — run install.sh on SIFT 2026",
)


@pytest.fixture
def sift_env(tmp_path: Path) -> tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]:
    evtx_dir = tmp_path / "evtx"
    evtx_dir.mkdir()
    case_dir = tmp_path / "case-hayabusa-int"
    case_dir.mkdir()
    if _FIXTURE_EVTX.exists():
        import shutil

        target = evtx_dir / "Security.evtx"
        shutil.copy(_FIXTURE_EVTX, target)
    else:
        (evtx_dir / "Security.evtx").write_bytes(secrets.token_bytes(256))
    evidence = evtx_dir / "Security.evtx"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.EVTX, audit_id="sift-int-20260611-001")
    return (
        case_dir,
        evtx_dir,
        case_dir / "tmp" / "hayabusa_out.csv",
        AuditLogger(case_dir, examiner="integration"),
        registry,
    )


def test_hayabusa_real_binary_e2e(
    sift_env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
) -> None:
    """Real Hayabusa binary invocation on SIFT 2026."""
    case_dir, evtx_dir, csv_out, logger, registry = sift_env

    resp = asyncio.run(
        hayabusa_csv_timeline(
            evtx_dir,
            csv_out,
            None,
            None,
            "super-verbose",
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used="claude-sonnet-4-6",
        )
    )

    assert resp.success is True
    assert resp.data is not None
    assert resp.data_provenance.cmd_argv[0] == str(_HAYABUSA)
    assert "csv-timeline" in resp.data_provenance.cmd_argv
    assert "--UTC" in resp.data_provenance.cmd_argv
    assert "--no-color" in resp.data_provenance.cmd_argv
    assert (case_dir / "audit" / "log.jsonl").exists()
