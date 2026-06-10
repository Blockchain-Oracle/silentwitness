"""Integration test for parse_prefetch.

Skipped on non-SIFT runners lacking the dotnet SDK and PECmd DLL.
On a SIFT workstation this test invokes the real PECmd.dll against a
tiny Prefetch directory fixture (skipped if fixture absent)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools.disk import parse_prefetch

_PECMD_DLL = Path("/opt/zimmermantools/PECmd.dll")
_DOTNET = Path("/usr/bin/dotnet")

_SKIP = pytest.mark.skipif(
    not (_PECMD_DLL.exists() and _DOTNET.exists()),
    reason="PECmd.dll and/or dotnet SDK not present in this environment",
)

_PREFETCH_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "hives"


@_SKIP
def test_parse_prefetch_integration(tmp_path: Path) -> None:
    """Real PECmd invocation against a test Prefetch directory fixture."""
    prefetch_dir = _PREFETCH_DIR / "Prefetch_test"
    if not prefetch_dir.exists():
        pytest.skip("Prefetch_test fixture directory not present")
    case_dir = tmp_path / "case-int-prefetch"
    case_dir.mkdir()
    csv_out = case_dir / "tmp" / "prefetch_out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(prefetch_dir, EvidenceType.OTHER, audit_id="sift-int-20260610-003")
    envelope = asyncio.run(
        parse_prefetch(
            prefetch_dir,
            csv_out,
            case_dir=case_dir,
            evidence_registry=EvidenceRegistry(case_dir),
            audit_logger=AuditLogger(case_dir, examiner="integration"),
            model_used="claude-sonnet-4-6",
        )
    )
    assert envelope.success is True
    assert envelope.data is not None
    assert len(envelope.data.entries) > 0
