"""Integration test for :func:`zeek_run` — runs real Zeek binary.

Skipped when Zeek is not installed (not available on SIFT 2026 without
install.sh provisioning). The test pcap fixture is synthetic — 10 packets
created with scapy/tcpdump during project setup.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp._lifecycle import MountCheckResult
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._network_common import ZEEK_BIN, ZEEK_BIN_FALLBACK
from silentwitness_mcp.tools.network import zeek_run

_ZEEK_AVAILABLE = ZEEK_BIN.exists() or ZEEK_BIN_FALLBACK.exists()
_PCAP_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "network" / "tiny.pcap"

pytestmark = pytest.mark.skipif(
    not _ZEEK_AVAILABLE or not _PCAP_FIXTURE.exists(),
    reason="Zeek not installed or tiny.pcap fixture missing",
)


def test_zeek_run_real_binary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end Zeek run on a tiny synthetic pcap fixture."""
    case_dir = tmp_path / "case-zeek-integration"
    case_dir.mkdir()
    out_dir = case_dir / "tmp" / "zeek-out"

    pcap_dest = tmp_path / "evidence" / "tiny.pcap"
    pcap_dest.parent.mkdir()
    pcap_dest.write_bytes(_PCAP_FIXTURE.read_bytes())

    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(pcap_dest, EvidenceType.PCAP, audit_id="sift-aj-integration-001")
    logger = AuditLogger(case_dir, examiner="aj")

    monkeypatch.setattr(
        "silentwitness_mcp.tools.network.check_mount",
        lambda: MountCheckResult(ok=True, advisories=[]),
    )

    resp = asyncio.run(
        zeek_run(
            pcap_dest,
            out_dir,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used="claude-sonnet-4-6",
        )
    )

    assert resp.success is True
    assert resp.data is not None
    assert resp.data.total_logs > 0
    assert resp.data.conn_log is not None
    assert resp.data.conn_log.line_count > 0
    log_path = case_dir / "audit" / "network.jsonl"
    assert log_path.exists()
