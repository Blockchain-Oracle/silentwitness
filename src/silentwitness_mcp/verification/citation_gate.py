"""Citation gate — SHA-256 + line-range + verbatim substring verification (architecture §4.5).

The wedge's load-bearing core. Every ``record_observation`` call routes
its citations through :func:`verify_citation` before persistence. An
observation whose cited span fails the four-step check is REJECTED with
a structured :class:`CitationResult` naming the failure mode and the
context the agent needs to self-correct. Closed-domain hallucination
("the bytes I claim to have read don't exist or don't say what I claim")
is therefore architecturally impossible — the agent's words and the
tool's bytes must agree, mechanically.

The four steps, in order:

  1. **Look up the audit entry** by ``span.audit_id`` in the injected
     ``audit_index``. Missing → :attr:`CitationRejectReason.AUDIT_ID_NOT_FOUND`.
  2. **Read the stored stdout blob** from ``entry.stdout_path``. Missing
     on disk → :attr:`CitationRejectReason.STDOUT_PATH_MISSING`.
  3. **Re-normalise** the raw bytes through
     :func:`silentwitness_mcp.verification.normalizer.normalize_output`
     using the entry's recorded ``tool`` and verify ``sha256`` matches
     ``span.sha256_of_normalized_output``. Mismatch →
     :attr:`CitationRejectReason.OUTPUT_HASH_MISMATCH` with
     ``expected_sha256`` + ``actual_sha256`` in the result's context.
  4. **Slice + substring**: split the normalised text into lines,
     bounds-check ``span.line_start`` and ``span.line_end`` against
     ``len(lines)`` (out of bounds →
     :attr:`CitationRejectReason.LINE_RANGE_OUT_OF_BOUNDS`), then verify
     ``span.span_text`` is a verbatim substring of
     ``lines[line_start:line_end]`` joined by ``\\n``. Missing →
     :attr:`CitationRejectReason.SPAN_NOT_IN_LINES`.

If all four steps pass, return
``CitationResult.accept(span)`` — the original span echoed back.

The function is **pure**: no global state, no caches across calls, no
time/random/locale dependencies. File reads are eager and inline so test
fixtures using ``tmp_path`` work transparently. If a single observation
ships multiple cited_spans against the same audit_id, the caller is
expected to perform the cheap caching outside this function (the tool
wrapper Epic 5+); the gate stays a verifier, not a state machine.

The audit_id-not-found path expects ``audit_index`` to be a
:class:`collections.abc.Mapping` keyed by audit_id. The integration layer
(Epic 4 MCP server bootstrap) builds it by replaying ``audit/*.jsonl``
at startup; this story takes the index as an injected dependency.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

from silentwitness_common.types import AuditEntry
from silentwitness_mcp.verification._types import (
    CitationRejectReason,
    CitationResult,
    CitedSpan,
)
from silentwitness_mcp.verification.normalizer import normalize_output


def verify_citation(span: CitedSpan, audit_index: Mapping[str, AuditEntry]) -> CitationResult:
    """Run the four-step citation-gate algorithm. See module docstring."""
    entry = audit_index.get(span.audit_id)
    if entry is None:
        return CitationResult.reject(
            CitationRejectReason.AUDIT_ID_NOT_FOUND, audit_id=span.audit_id
        )

    try:
        raw = entry.stdout_path.read_bytes()
    except FileNotFoundError:
        return CitationResult.reject(
            CitationRejectReason.STDOUT_PATH_MISSING,
            audit_id=span.audit_id,
            stdout_path=str(entry.stdout_path),
        )

    normalized = normalize_output(raw, tool=entry.tool)
    actual_hash = hashlib.sha256(normalized).hexdigest()
    if actual_hash != span.sha256_of_normalized_output:
        return CitationResult.reject(
            CitationRejectReason.OUTPUT_HASH_MISMATCH,
            audit_id=span.audit_id,
            expected_sha256=span.sha256_of_normalized_output,
            actual_sha256=actual_hash,
        )

    lines = normalized.decode("utf-8", errors="surrogateescape").split("\n")
    total_lines = len(lines)
    if span.line_end > total_lines:
        return CitationResult.reject(
            CitationRejectReason.LINE_RANGE_OUT_OF_BOUNDS,
            audit_id=span.audit_id,
            line_start=span.line_start,
            line_end=span.line_end,
            total_lines=total_lines,
        )

    sliced = "\n".join(lines[span.line_start : span.line_end])
    if span.span_text not in sliced:
        return CitationResult.reject(
            CitationRejectReason.SPAN_NOT_IN_LINES,
            audit_id=span.audit_id,
            line_start=span.line_start,
            line_end=span.line_end,
            span_text=span.span_text,
        )

    return CitationResult.accept(span)


__all__ = ["verify_citation"]
