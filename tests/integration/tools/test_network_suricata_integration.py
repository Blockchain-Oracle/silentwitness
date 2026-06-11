"""Integration test for :func:`suricata_run` — runs real Suricata binary.

Skipped when Suricata is not installed. The test pcap and rules fixtures are
synthetic — tiny.pcap (network zeek integration fixture) + suricata_minimal.rules.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp._lifecycle import MountCheckResult
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._network_common import SURICATA_BIN, SURICATA_BIN_FALLBACK
from silentwitness_mcp.tools._network_suricata import suricata_run

_SURICATA_AVAILABLE = SURICATA_BIN.exists() or SURICATA_BIN_FALLBACK.exists()
_PCAP_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "network" / "tiny.pcap"
_RULES_FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "network" / "suricata_minimal.rules"
)

pytestmark = pytest.mark.skipif(
    not _SURICATA_AVAILABLE or not _PCAP_FIXTURE.exists(),
    reason="Suricata not installed or tiny.pcap fixture missing",
)


def test_suricata_run_real_binary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end Suricata run on a tiny synthetic pcap fixture."""
    case_dir = tmp_path / "case-suricata-integration"
    case_dir.mkdir()
    out_dir = case_dir / "tmp" / "suricata-out"

    pcap_dest = tmp_path / "evidence" / "tiny.pcap"
    pcap_dest.parent.mkdir()
    pcap_dest.write_bytes(_PCAP_FIXTURE.read_bytes())

    rules_dest = tmp_path / "evidence" / "suricata_minimal.rules"
    rules_dest.write_bytes(_RULES_FIXTURE.read_bytes())

    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(pcap_dest, EvidenceType.PCAP, audit_id="sift-aj-integration-002")
    registry.register(rules_dest, EvidenceType.IDS_RULES, audit_id="sift-aj-integration-003")
    logger = AuditLogger(case_dir, examiner="aj")

    monkeypatch.setattr(
        "silentwitness_mcp.tools._network_suricata.check_mount",
        lambda: MountCheckResult(ok=True, advisories=[]),
    )

    resp = asyncio.run(
        suricata_run(
            pcap_dest,
            rules_dest,
            out_dir,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used="claude-sonnet-4-6",
        )
    )

    assert resp.success is True
    assert resp.data is not None
    assert resp.data.total_events >= 0
    assert len(resp.data.eve_json_sha256) == 64
    log_path = case_dir / "audit" / "network.jsonl"
    assert log_path.exists()
