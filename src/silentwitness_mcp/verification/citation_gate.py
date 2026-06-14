"""Citation gate — verbatim-substring verification against the evidence index (§4.5).

Every ``record_observation`` call routes its citations through
:func:`verify_citation` before persistence. Each :class:`CitedSpan` names one
parsed evidence row by ``record_id`` and quotes the ``span_text`` it relies on.
The gate resolves the record from the supplied lookup and verifies the quote is
a verbatim substring of the record's stored text.

What this gate delivers, scoped honestly per ADR-004: the agent's words must
appear as a verbatim substring of bytes the evidence index actually holds for a
record that actually exists. **Closure against quoting the right substring from
the wrong record is the entity gate's job (§4.7)** — that layer proves every
named IOC/path/account appears in a cited span. This gate alone constrains
hallucination to "the quote is real and the record is real," a real but partial
guarantee.

Two steps, in order:

  1. **Record lookup** — ``span.record_id in records``. Missing key →
     :attr:`CitationRejectReason.RECORD_NOT_FOUND` (the agent cited a row that
     is not in the index — a fabricated or stale id).
  2. **Verbatim substring** — ``span.span_text in record.text``. The record's
     ``text`` is the authoritative stored evidence (what the feeder indexed);
     the sanitized+wrapped form the agent reads at the query boundary leaves
     clean evidence bytes unchanged, so a faithful quote matches. A quote that
     is not a substring → :attr:`CitationRejectReason.SPAN_NOT_IN_RECORD`.

Provenance (``audit_id`` / ``source_tool`` / ``sha256``) is read by callers from
the resolved record, never trusted from the agent — the agent cannot forge the
chain of custody of a citation it merely points at.

The function is pure: no I/O, no global state, no time/random/locale
dependencies. The record lookup is dependency-injected so callers control
exactly which rows are in scope (the cited ones) and unit tests need no store.
"""

from __future__ import annotations

from collections.abc import Mapping

from silentwitness_common.types import CitedSpan
from silentwitness_mcp.index.store import IndexRecord
from silentwitness_mcp.verification._types import CitationRejectReason, CitationResult


def verify_citation(span: CitedSpan, records: Mapping[int, IndexRecord]) -> CitationResult:
    """Run the two-step citation-gate algorithm. See module docstring."""
    record = records.get(span.record_id)
    if record is None:
        return CitationResult.reject(
            CitationRejectReason.RECORD_NOT_FOUND, record_id=span.record_id
        )

    if span.span_text not in record.text:
        return CitationResult.reject(
            CitationRejectReason.SPAN_NOT_IN_RECORD,
            record_id=span.record_id,
            span_text=span.span_text,
        )

    return CitationResult.accept(span)


__all__ = ["verify_citation"]
