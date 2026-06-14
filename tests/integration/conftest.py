"""Shared fixtures for the record_observation integration tests.

Extracted per round-1 pr-test-analyzer M2 + round-3 M2 (duplicated
helpers across the two integration files had drifted into cosmetic-only
differences that would entrench across additional round-4 tests).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from silentwitness_common.types import CitedSpan
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.index.store import IndexRecord

EXAMINER = "aj"
MODEL = "anthropic:claude-opus-4-7"


def make_record(text: str, *, record_id: int, audit_id: str) -> IndexRecord:
    """Build an evidence-index record the citation gate can resolve by id."""
    return IndexRecord(
        text=text,
        source_tool="evtx:Security",
        audit_id=audit_id,
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        id=record_id,
    )


def cited_span_for(text: str, *, record_id: int, span_text: str) -> CitedSpan:
    """A CitedSpan quoting ``span_text`` (must be a substring of ``text``)."""
    assert span_text in text, f"span_text {span_text!r} not in record text"
    return CitedSpan(record_id=record_id, span_text=span_text)


@pytest.fixture
def case_env(tmp_path: Path) -> tuple[Path, AuditLogger]:
    """Per-test case directory + AuditLogger."""
    case_dir = tmp_path / "case-01"
    case_dir.mkdir()
    return case_dir, AuditLogger(case_dir, examiner=EXAMINER)
