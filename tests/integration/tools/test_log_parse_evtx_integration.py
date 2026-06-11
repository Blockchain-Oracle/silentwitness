"""Integration test for parse_evtx.

Skipped on non-SIFT runners lacking dotnet SDK and EvtxECmd DLL.
On a SIFT workstation this test invokes the real EvtxECmd.dll against an
EVTX sample from tests/fixtures/log/ (skipped if no .evtx file is present)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools.log import parse_evtx

_EVTXECMD_DLL = Path("/opt/zimmermantools/EvtxeCmd/EvtxECmd.dll")
_DOTNET = Path("/usr/bin/dotnet")

_SKIP = pytest.mark.skipif(
    not (_EVTXECMD_DLL.exists() and _DOTNET.exists()),
    reason="EvtxECmd.dll and/or dotnet SDK not present in this environment",
)

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "log"


@_SKIP
def test_parse_evtx_integration(tmp_path: Path) -> None:
    """Real EvtxECmd invocation against an EVTX fixture."""
    evtx_files = list(_FIXTURE_DIR.glob("*.evtx"))
    if not evtx_files:
        pytest.skip("No .evtx files found in tests/fixtures/log/")
    evtx_file = evtx_files[0]

    case_dir = tmp_path / "case-int-evtx"
    case_dir.mkdir()
    csv_out = case_dir / "tmp" / "evtx_out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evtx_file, EvidenceType.OTHER, audit_id="sift-int-20260611-010")
    envelope = asyncio.run(
        parse_evtx(
            evtx_file,
            csv_out,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=AuditLogger(case_dir, examiner="integration"),
            model_used="claude-sonnet-4-6",
        )
    )
    assert envelope.success is True
    assert envelope.data is not None
    assert envelope.data.row_count > 0
