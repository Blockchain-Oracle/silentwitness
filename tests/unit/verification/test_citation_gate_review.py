"""Review-pass tests for the index-era citation gate: rejection-context
richness, idempotency, multi-record lookups, and a soundness property
(a verbatim substring of a present record always accepts).
"""

from __future__ import annotations

from hypothesis import given, settings, strategies as st

from silentwitness_mcp.index.store import IndexRecord
from silentwitness_mcp.verification._types import CitationRejectReason, CitedSpan
from silentwitness_mcp.verification.citation_gate import verify_citation

_AUDIT_ID = "sift-aj-20260613-007"


def _record(text: str, *, record_id: int = 7) -> IndexRecord:
    return IndexRecord(
        text=text,
        source_tool="evtx:Security",
        audit_id=_AUDIT_ID,
        sha256="a" * 64,
        id=record_id,
    )


def test_reject_context_names_the_missing_record_id() -> None:
    result = verify_citation(CitedSpan(record_id=404, span_text="x"), {})
    assert result.reason == CitationRejectReason.RECORD_NOT_FOUND
    assert result.context["record_id"] == 404


def test_reject_context_echoes_the_unmatched_span() -> None:
    rec = _record("alpha beta gamma")
    result = verify_citation(CitedSpan(record_id=7, span_text="delta"), {7: rec})
    assert result.reason == CitationRejectReason.SPAN_NOT_IN_RECORD
    assert result.context["span_text"] == "delta"


def test_verify_citation_is_idempotent() -> None:
    rec = _record("svchost.exe at PID 1208")
    records = {7: rec}
    span = CitedSpan(record_id=7, span_text="PID 1208")
    assert verify_citation(span, records) == verify_citation(span, records)


def test_resolves_the_named_record_among_many() -> None:
    records = {
        1: _record("first row", record_id=1),
        2: _record("second row with target", record_id=2),
        3: _record("third row", record_id=3),
    }
    result = verify_citation(CitedSpan(record_id=2, span_text="target"), records)
    assert result.success is True


def test_substring_present_in_other_record_still_rejected() -> None:
    """The quote must be in the CITED record, not merely somewhere in the index."""
    records = {
        1: _record("the secret is here", record_id=1),
        2: _record("nothing relevant", record_id=2),
    }
    result = verify_citation(CitedSpan(record_id=2, span_text="secret"), records)
    assert result.success is False
    assert result.reason == CitationRejectReason.SPAN_NOT_IN_RECORD


def test_unicode_substring_accepts() -> None:
    rec = _record("user café logged on from 10.0.0.5")
    result = verify_citation(CitedSpan(record_id=7, span_text="café"), {7: rec})
    assert result.success is True


@given(text=st.text(min_size=1, max_size=200))
@settings(max_examples=50, deadline=None)
def test_property_verbatim_substring_of_present_record_always_accepts(text: str) -> None:
    """Soundness: any non-empty substring of a present record's text accepts.

    Lone surrogates can't be emitted as a Pydantic span_text, and an empty
    pick can't satisfy ``min_length=1`` — guard both."""
    pick = text[: max(1, len(text) // 2)]
    # CitedSpan strips surrounding whitespace (str_strip_whitespace) and requires
    # min_length=1, so a whitespace-only pick is not a constructable citation —
    # skip it (a real agent never quotes pure whitespace as evidence).
    if not pick.strip() or any(0xDC80 <= ord(c) <= 0xDCFF for c in pick):
        return
    pick = pick.strip()
    rec = _record(text, record_id=7)
    result = verify_citation(CitedSpan(record_id=7, span_text=pick), {7: rec})
    assert result.success is True
