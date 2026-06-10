"""Integration tests for parse_amcache + parse_shimcache.

Skipped on non-SIFT runners that lack the dotnet SDK and EZ Tools DLLs.
On a SIFT workstation these tests invoke the real AmcacheParser.dll and
AppCompatCacheParser.dll against tiny synthetic hive samples."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools.disk import parse_amcache, parse_shimcache

_AMCACHE_DLL = Path("/opt/zimmermantools/AmcacheParser.dll")
_SHIM_DLL = Path("/opt/zimmermantools/AppCompatCacheParser.dll")
_DOTNET = Path("/usr/bin/dotnet")

_SKIP_AMCACHE = pytest.mark.skipif(
    not (_AMCACHE_DLL.exists() and _DOTNET.exists()),
    reason="AmcacheParser.dll and/or dotnet SDK not present in this environment",
)
_SKIP_SHIM = pytest.mark.skipif(
    not (_SHIM_DLL.exists() and _DOTNET.exists()),
    reason="AppCompatCacheParser.dll and/or dotnet SDK not present in this environment",
)

_HIVE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "hives"


@_SKIP_AMCACHE
def test_parse_amcache_integration(tmp_path: Path) -> None:
    """Real AmcacheParser invocation against a test hive fixture."""
    hive = _HIVE_DIR / "Amcache_test.hve"
    if not hive.exists():
        pytest.skip("Amcache_test.hve fixture not present")
    case_dir = tmp_path / "case-int-amcache"
    case_dir.mkdir()
    csv_out = case_dir / "tmp" / "amcache_out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(hive, EvidenceType.OTHER, audit_id="sift-int-20260610-001")
    envelope = asyncio.run(
        parse_amcache(
            hive,
            csv_out,
            case_dir=case_dir,
            evidence_registry=EvidenceRegistry(case_dir),
            audit_logger=AuditLogger(case_dir, examiner="integration"),
            model_used="claude-sonnet-4-6",
        )
    )
    assert envelope.success is True
    assert envelope.data is not None


@_SKIP_SHIM
def test_parse_shimcache_integration(tmp_path: Path) -> None:
    """Real AppCompatCacheParser invocation against a test SYSTEM hive."""
    hive = _HIVE_DIR / "SYSTEM_test"
    if not hive.exists():
        pytest.skip("SYSTEM_test fixture not present")
    case_dir = tmp_path / "case-int-shim"
    case_dir.mkdir()
    csv_out = case_dir / "tmp" / "shim_out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(hive, EvidenceType.OTHER, audit_id="sift-int-20260610-002")
    envelope = asyncio.run(
        parse_shimcache(
            hive,
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
