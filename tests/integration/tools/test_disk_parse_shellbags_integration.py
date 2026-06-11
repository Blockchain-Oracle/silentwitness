"""Integration test for parse_shellbags.

Skipped on non-SIFT runners lacking the dotnet SDK and SBECmd DLL.
On a SIFT workstation this test invokes the real SBECmd.dll against a
UsrClass.dat sample from tests/fixtures/disk/Shellbags_test/ (skipped
if the fixture directory or any .dat files are absent)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools.disk import parse_shellbags

_SBECMD_DLL = Path("/opt/zimmermantools/SBECmd.dll")
_DOTNET = Path("/usr/bin/dotnet")

_SKIP = pytest.mark.skipif(
    not (_SBECMD_DLL.exists() and _DOTNET.exists()),
    reason="SBECmd.dll and/or dotnet SDK not present in this environment",
)

_SHELLBAGS_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "disk"


@_SKIP
def test_parse_shellbags_integration(tmp_path: Path) -> None:
    """Real SBECmd invocation against a hive from tests/fixtures/disk/Shellbags_test/."""
    hive_dir = _SHELLBAGS_DIR / "Shellbags_test"
    if not hive_dir.exists():
        pytest.skip("Shellbags_test fixture directory not present in tests/fixtures/disk/")
    dat_files = list(hive_dir.glob("*.dat"))
    if not dat_files:
        pytest.skip("No .dat files found in tests/fixtures/disk/Shellbags_test/")
    hive_file = dat_files[0]

    case_dir = tmp_path / "case-int-shellbags"
    case_dir.mkdir()
    csv_out = case_dir / "tmp" / "shellbags_out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(hive_file, EvidenceType.OTHER, audit_id="sift-int-20260611-004")
    envelope = asyncio.run(
        parse_shellbags(
            hive_file,
            csv_out,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=AuditLogger(case_dir, examiner="integration"),
            model_used="claude-sonnet-4-6",
        )
    )
    assert envelope.success is True
    assert envelope.data is not None
    assert len(envelope.data.entries) > 0
