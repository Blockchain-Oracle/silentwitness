"""End-to-end test against the real Vol3 binary + a real memory image.

The fixture ``tests/fixtures/memory/nist-hacking-case.mem`` lands in
Epic 14 (fixture provisioning). Until then this file's tests are
SKIPPED — never red — so a fresh checkout's CI run stays green."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._vol_common import VOL_BIN
from silentwitness_mcp.tools.memory import (
    vol_malfind,
    vol_netscan,
    vol_pslist,
    vol_psscan,
    vol_pstree,
)

_FIXTURE_NAME = "nist-hacking-case.mem"
_NIST_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "memory" / _FIXTURE_NAME


@pytest.mark.skipif(
    not _NIST_FIXTURE.exists() or not VOL_BIN.exists(),
    reason="NIST memory fixture and/or Vol3 binary not present in this environment",
)
def test_pslist_against_nist_image(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-nist"
    case_dir.mkdir()
    logger = AuditLogger(case_dir, examiner="aj")
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(_NIST_FIXTURE, EvidenceType.MEMORY_DUMP, audit_id="sift-aj-20260605-001")
    envelope = asyncio.run(
        vol_pslist(
            _NIST_FIXTURE,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used="claude-sonnet-4-6",
        )
    )
    assert envelope.success is True
    assert envelope.data is not None
    assert len(envelope.data.entries) > 0


@pytest.mark.skipif(
    not _NIST_FIXTURE.exists() or not VOL_BIN.exists(),
    reason="NIST memory fixture and/or Vol3 binary not present in this environment",
)
def test_pstree_against_nist_image(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-nist-pstree"
    case_dir.mkdir()
    logger = AuditLogger(case_dir, examiner="aj")
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(_NIST_FIXTURE, EvidenceType.MEMORY_DUMP, audit_id="sift-aj-20260605-001")
    envelope = asyncio.run(
        vol_pstree(
            _NIST_FIXTURE,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used="claude-sonnet-4-6",
        )
    )
    assert envelope.success is True
    assert envelope.data is not None
    assert len(envelope.data.entries) > 0


@pytest.mark.skipif(
    not _NIST_FIXTURE.exists() or not VOL_BIN.exists(),
    reason="NIST memory fixture and/or Vol3 binary not present in this environment",
)
def test_psscan_against_nist_image(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-nist-psscan"
    case_dir.mkdir()
    logger = AuditLogger(case_dir, examiner="aj")
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(_NIST_FIXTURE, EvidenceType.MEMORY_DUMP, audit_id="sift-aj-20260605-001")
    envelope = asyncio.run(
        vol_psscan(
            _NIST_FIXTURE,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used="claude-sonnet-4-6",
        )
    )
    assert envelope.success is True
    assert envelope.data is not None
    assert len(envelope.data.entries) > 0


@pytest.mark.skipif(
    not _NIST_FIXTURE.exists() or not VOL_BIN.exists(),
    reason="NIST memory fixture and/or Vol3 binary not present in this environment",
)
def test_malfind_against_nist_image(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-nist-malfind"
    case_dir.mkdir()
    logger = AuditLogger(case_dir, examiner="aj")
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(_NIST_FIXTURE, EvidenceType.MEMORY_DUMP, audit_id="sift-aj-20260609-001")
    envelope = asyncio.run(
        vol_malfind(
            _NIST_FIXTURE,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used="claude-sonnet-4-6",
        )
    )
    # Hit count is dataset-dependent; the e2e contract is "Vol3 invocation
    # + JSON parse succeeded".
    assert envelope.success is True
    assert envelope.data is not None


@pytest.mark.skipif(
    not _NIST_FIXTURE.exists() or not VOL_BIN.exists(),
    reason="NIST memory fixture and/or Vol3 binary not present in this environment",
)
def test_netscan_against_nist_image(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-nist-netscan"
    case_dir.mkdir()
    logger = AuditLogger(case_dir, examiner="aj")
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(_NIST_FIXTURE, EvidenceType.MEMORY_DUMP, audit_id="sift-aj-20260609-001")
    envelope = asyncio.run(
        vol_netscan(
            _NIST_FIXTURE,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used="claude-sonnet-4-6",
        )
    )
    assert envelope.success is True
    assert envelope.data is not None
