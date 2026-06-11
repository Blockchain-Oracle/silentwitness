"""Integration test for chainsaw_hunt — skipped unless Chainsaw is installed."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._log_chainsaw import chainsaw_hunt
from silentwitness_mcp.tools._log_common import (
    CHAINSAW_BIN,
    CHAINSAW_MAPPING_DEFAULT,
    SIGMA_RULES_DIR,
)

MODEL = "claude-sonnet-4-6"

_EVTX_DIR = Path("/evidence/evtx")


@pytest.mark.skipif(
    not CHAINSAW_BIN.exists(),
    reason="Chainsaw not installed — run install.sh on SIFT 2026",
)
@pytest.mark.skipif(
    not _EVTX_DIR.exists(),
    reason="/evidence/evtx not mounted — integration test requires SIFT environment",
)
def test_chainsaw_hunt_live(tmp_path: Path) -> None:
    """Live Chainsaw run against /evidence/evtx — verifies tool executes and
    produces ChainsawOutput with at least one typed hit (or zero without truncation)."""
    case_dir = tmp_path / "case-chainsaw-live"
    case_dir.mkdir()
    json_out = case_dir / "tmp" / "chainsaw_out.json"

    evtx_files = sorted(_EVTX_DIR.glob("*.evtx"))
    assert evtx_files, "No *.evtx files found in /evidence/evtx"

    registry = EvidenceRegistry(case_dir=case_dir)
    for i, evtx in enumerate(evtx_files):
        registry.register(evtx, EvidenceType.EVTX, audit_id=f"sift-live-{i:03d}")

    resp = asyncio.run(
        chainsaw_hunt(
            _EVTX_DIR,
            json_out,
            SIGMA_RULES_DIR,
            CHAINSAW_MAPPING_DEFAULT,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=AuditLogger(case_dir, examiner="integration-test"),
            model_used=MODEL,
            timeout_s=300.0,
        )
    )

    assert resp.success is True
    assert resp.data is not None
    assert not resp.data.truncated or resp.data.row_count > 0
    log_path = case_dir / "audit" / "log.jsonl"
    assert log_path.exists(), "Audit JSONL not written on success"
