"""End-to-end test against the real MFTECmd binary on a synthetic $MFT.

Skipped when ``/opt/zimmermantools/MFTECmd.dll`` does not exist (the
CI runner and dev machines without SIFT 2026 installed)."""

from __future__ import annotations

import asyncio
import secrets
from pathlib import Path

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._disk_common import DOTNET_BIN, dll_path_for
from silentwitness_mcp.tools.disk import parse_mft


@pytest.mark.skipif(
    not dll_path_for("MFTECmd").exists() or not DOTNET_BIN.exists(),
    reason="MFTECmd.dll and/or dotnet SDK not present in this environment",
)
def test_parse_mft_against_synthetic_mft(tmp_path: Path) -> None:
    """Smoke-test the real dotnet → MFTECmd path. We do not assert on
    the row contents — a synthetic random-bytes $MFT will likely
    surface as TOOL_FAILED — but the test pins that the wrapper
    invokes the binary, captures stderr, and surfaces a structured
    envelope rather than crashing."""
    case_dir = tmp_path / "case-mft-integ"
    case_dir.mkdir()
    evidence = tmp_path / "MFT"
    evidence.write_bytes(secrets.token_bytes(4096))
    csv_out = tmp_path / "csv_out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.OTHER, audit_id="sift-aj-20260610-002")
    envelope = asyncio.run(
        parse_mft(
            evidence,
            csv_out,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=AuditLogger(case_dir, examiner="aj"),
            model_used="claude-sonnet-4-6",
        )
    )
    # Real MFTECmd will likely reject the random-bytes "MFT" with a
    # non-zero exit — that's expected. The contract is that the
    # wrapper produced a structured envelope at all.
    assert envelope is not None
    assert envelope.data_provenance.cmd_argv[0] == str(DOTNET_BIN)
    assert envelope.data_provenance.cmd_argv[1] == str(dll_path_for("MFTECmd"))
