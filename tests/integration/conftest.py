"""Shared fixtures for the record_observation integration tests.

Extracted per round-1 pr-test-analyzer M2 + round-3 M2 (duplicated
helpers across the two integration files had drifted into cosmetic-only
differences that would entrench across additional round-4 tests).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from silentwitness_common.types import AuditEntry, CitedSpan
from silentwitness_mcp.audit.logger import AuditLogger

EXAMINER = "aj"
MODEL = "anthropic:claude-opus-4-7"
FIXED_NOW = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)


def write_blob_and_entry(
    blobs_dir: Path, *, audit_id: str, content: bytes, tool: str = "_universal_only"
) -> AuditEntry:
    blobs_dir.mkdir(parents=True, exist_ok=True)
    blob_path = blobs_dir / f"{audit_id}.txt"
    blob_path.write_bytes(content)
    return AuditEntry(
        ts=FIXED_NOW,
        audit_id=audit_id,
        tool=tool,
        params={},
        result_summary={},
        result_sha256=hashlib.sha256(content).hexdigest(),
        stdout_path=blob_path,
        elapsed_ms=10.0,
        examiner=EXAMINER,
        model_used=MODEL,
    )


def cited_span_for(content: bytes, audit_id: str, *, span_text: str) -> CitedSpan:
    text = content.decode("utf-8", errors="surrogateescape")
    for idx, line in enumerate(text.split("\n")):
        if span_text in line:
            return CitedSpan(
                audit_id=audit_id,
                sha256_of_normalized_output=hashlib.sha256(content).hexdigest(),
                line_start=idx,
                line_end=idx + 1,
                span_text=line,
            )
    raise AssertionError(f"span_text {span_text!r} not in content")


@pytest.fixture
def case_env(tmp_path: Path) -> tuple[Path, Path, AuditLogger]:
    """Per-test case directory + blobs directory + AuditLogger."""
    case_dir = tmp_path / "case-01"
    case_dir.mkdir()
    return case_dir, case_dir / "blobs", AuditLogger(case_dir, examiner=EXAMINER)
