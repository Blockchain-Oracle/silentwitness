"""Behavioural tests for src/silentwitness_mcp/verification/citation_gate.py.

Real Pydantic models, no mocks per architecture §14. The index-era gate has
exactly two rejection codes — RECORD_NOT_FOUND (the cited row is not in the
supplied lookup) and SPAN_NOT_IN_RECORD (the quote is not a verbatim substring
of the record's stored text) — plus the success path. Provenance is read from
the resolved record, never from the agent.
"""

from __future__ import annotations

import pytest

from silentwitness_mcp.index.store import IndexRecord
from silentwitness_mcp.verification._types import (
    CitationRejectReason,
    CitationResult,
    CitedSpan,
)
from silentwitness_mcp.verification.citation_gate import verify_citation

_AUDIT_ID = "sift-aj-20260613-007"
_SHA = "a" * 64


def _record(text: str, *, record_id: int = 7) -> IndexRecord:
    return IndexRecord(
        text=text,
        source_tool="evtx:Security",
        artifact_path="Security.evtx",
        host="WORKSTATION",
        ts="2026-06-13T14:27:00Z",
        audit_id=_AUDIT_ID,
        sha256=_SHA,
        id=record_id,
    )


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


def test_success_on_valid_citation() -> None:
    rec = _record("line0\nline1\nsvchost.exe at PID 1208\nline3")
    span = CitedSpan(record_id=7, span_text="svchost.exe at PID 1208")
    result = verify_citation(span, {7: rec})
    assert result.success is True
    assert result.span == span
    assert result.reason is None


def test_success_with_multi_line_span() -> None:
    rec = _record("header\nfoo\nbar\nbaz\nfooter")
    span = CitedSpan(record_id=7, span_text="bar\nbaz")
    result = verify_citation(span, {7: rec})
    assert result.success is True


# ---------------------------------------------------------------------------
# RECORD_NOT_FOUND
# ---------------------------------------------------------------------------


def test_reject_record_not_found_on_unknown_id() -> None:
    span = CitedSpan(record_id=999, span_text="anything")
    result = verify_citation(span, {})
    assert result.success is False
    assert result.reason == CitationRejectReason.RECORD_NOT_FOUND
    assert result.context["record_id"] == 999


def test_reject_record_not_found_when_only_other_ids_present() -> None:
    span = CitedSpan(record_id=42, span_text="anything")
    result = verify_citation(span, {7: _record("present", record_id=7)})
    assert result.success is False
    assert result.reason == CitationRejectReason.RECORD_NOT_FOUND


# ---------------------------------------------------------------------------
# SPAN_NOT_IN_RECORD — closed-domain hallucination caught
# ---------------------------------------------------------------------------


def test_reject_span_not_in_record_when_text_absent() -> None:
    rec = _record("line0\nline1\nline2")
    span = CitedSpan(record_id=7, span_text="this text does not exist anywhere")
    result = verify_citation(span, {7: rec})
    assert result.success is False
    assert result.reason == CitationRejectReason.SPAN_NOT_IN_RECORD
    assert result.context["record_id"] == 7
    assert result.context["span_text"] == "this text does not exist anywhere"


def test_reject_span_not_in_record_on_paraphrase() -> None:
    """A near-miss paraphrase is not a verbatim substring → rejected."""
    rec = _record("EventID 4624 logon type 10 user ADMIN")
    span = CitedSpan(record_id=7, span_text="EventID 4624 logon type 3 user ADMIN")
    result = verify_citation(span, {7: rec})
    assert result.success is False
    assert result.reason == CitationRejectReason.SPAN_NOT_IN_RECORD


# ---------------------------------------------------------------------------
# Provenance comes from the record, never the agent
# ---------------------------------------------------------------------------


def test_gate_ignores_agent_supplied_provenance() -> None:
    """CitedSpan carries no audit_id/sha256 — the agent cannot forge the chain
    of custody of a citation it merely points at; only record_id + span_text."""
    assert set(CitedSpan.model_fields) == {"record_id", "span_text"}


# ---------------------------------------------------------------------------
# Type-level invariants on CitedSpan / CitationResult
# ---------------------------------------------------------------------------


def test_cited_span_rejects_zero_record_id() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CitedSpan(record_id=0, span_text="x")


def test_cited_span_rejects_empty_span_text() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CitedSpan(record_id=1, span_text="")


def test_citation_result_rejects_success_without_span() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="span"):
        CitationResult(success=True)


def test_citation_result_rejects_failure_without_reason() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="reason"):
        CitationResult(success=False)


def test_citation_result_rejects_failure_with_span() -> None:
    span = CitedSpan(record_id=1, span_text="x")
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="must not carry span"):
        CitationResult(success=False, reason=CitationRejectReason.RECORD_NOT_FOUND, span=span)
