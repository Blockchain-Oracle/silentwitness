"""Integration test for regripper_run — skipped unless rip.pl is installed.

Runs the real /usr/local/bin/rip.pl against a tiny in-memory SYSTEM hive
fixture (or skips gracefully if rip.pl is absent from the SIFT environment).
"""

from __future__ import annotations

import asyncio
import secrets
from pathlib import Path

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools.registry import RIP_BIN, regripper_run

pytestmark = pytest.mark.skipif(
    not RIP_BIN.exists(),
    reason=f"rip.pl not installed at {RIP_BIN} — SIFT 2026 only",
)


@pytest.fixture
def live_env(tmp_path: Path) -> tuple[Path, Path, AuditLogger, EvidenceRegistry]:
    """Create a minimal case + register the SYSTEM hive fixture."""
    case_dir = tmp_path / "case-rr-live"
    case_dir.mkdir()
    # Use a real SYSTEM hive if available; otherwise a tiny stub that rip.pl
    # will reject (still exercises all gates up to the subprocess + parse-fail path).
    system_hive = Path("/evidence/case-001/SYSTEM")
    if not system_hive.exists():
        system_hive = tmp_path / "SYSTEM_stub"
        system_hive.write_bytes(secrets.token_bytes(512))
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(system_hive, EvidenceType.OTHER, audit_id="sift-aj-20260611-099")
    return case_dir, system_hive, AuditLogger(case_dir, examiner="aj"), registry


def test_regripper_run_live_compname(
    live_env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
) -> None:
    """Live rip.pl run with compname plugin: success or PARSE_FAILED (bad hive)."""
    case_dir, hive, logger, registry = live_env
    envelope = asyncio.run(
        regripper_run(
            hive,
            "compname",
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used="claude-sonnet-4-6",
        )
    )
    # Either success (real hive) or a PARSE_FAILED advisory (stub hive) —
    # both are correct outcomes from a real rip.pl invocation.
    assert envelope.success is True or "PARSE_FAILED" in envelope.advisories[-1]
    assert (case_dir / "audit" / "registry.jsonl").exists()
    assert envelope.data_provenance.tool == "regripper_run"
