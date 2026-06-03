"""Citation gate — SHA-256 + line-range + verbatim substring verification (architecture §4.5).

Every ``record_observation`` call routes its citations through
:func:`verify_citation` before persistence. Any failure returns a
structured :class:`CitationResult` naming the rejection code and the
context the agent needs to self-correct.

What this gate actually delivers, scoped honestly per ADR-004: SHA-256
of the re-normalised stored blob + line-range bounds + verbatim
substring within ``"\\n".join(lines[line_start:line_end])``. **Closure
against same-range wrong-row matches is the entity gate's job (§4.7).**
This gate alone constrains hallucination to "the agent's words must
appear as a verbatim substring of bytes the tool actually produced" —
a real but partial guarantee.

The four steps, in order:

  1. **Audit-entry lookup** — ``span.audit_id in audit_index``. Missing
     key → :attr:`CitationRejectReason.AUDIT_ID_NOT_FOUND`. An explicit
     ``None`` value in the mapping is an integration-layer bug, not an
     agent error; ``TypeError`` propagates (PR-110 silent-failure H3).
  2. **Read the stored blob** — ``FileNotFoundError`` →
     :attr:`CitationRejectReason.STDOUT_PATH_MISSING`. Other ``OSError``
     (``PermissionError``, ``IsADirectoryError``, ``EIO`` from bit-rot)
     → :attr:`CitationRejectReason.STDOUT_PATH_UNREADABLE` with
     ``errno`` + ``strerror`` (PR-110 silent-failure C2).
  3. **Re-normalise + hash** — uses the recorded ``entry.tool``. If
     the tool was removed from ``TOOL_PATTERNS`` between record and
     verify, :class:`silentwitness_mcp.verification.normalizer.UnknownToolError`
     maps to :attr:`CitationRejectReason.TOOL_NOT_REGISTERED` (PR-110
     silent-failure C1). Hash mismatch →
     :attr:`CitationRejectReason.OUTPUT_HASH_MISMATCH` with
     ``expected_sha256`` / ``actual_sha256`` / ``raw_bytes`` /
     ``normalized_bytes`` / ``tool`` so the agent can distinguish
     "claimed wrong hash" from "normalizer coverage gap" (PR-110 H4).
  4. **Slice + substring** — split into lines; bounds-check
     ``line_start`` AND ``line_end`` against ``len(lines)`` (defence
     in depth per PR-110 M5); verify ``span_text`` is a verbatim
     substring of ``"\\n".join(lines[line_start:line_end])``.

Line indexing convention: ``str.split("\\n")`` on a blob ending in
``\\n`` produces a trailing empty string, so ``"alpha\\nbeta\\n"`` has
``total_lines=3`` with ``lines[2]=""``. This phantom line is harmless
because :class:`silentwitness_common.types.CitedSpan.span_text` is
``min_length=1`` — the empty trailing line can never satisfy a
substring claim.

The function is pure: no global state, no caches across calls, no
time/random/locale dependencies. Multi-span complexity is
O(N · blob_size + N · normalize_cost); for 100 MB Vol3 dumps cited
5-10 times in one observation, callers SHOULD cache
``(raw, normalized, lines)`` per audit_id (Epic 5+ tool-wrapper concern).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

from silentwitness_common.types import AuditEntry, CitedSpan
from silentwitness_mcp.verification._types import CitationRejectReason, CitationResult
from silentwitness_mcp.verification.normalizer import UnknownToolError, normalize_output


def verify_citation(span: CitedSpan, audit_index: Mapping[str, AuditEntry]) -> CitationResult:
    """Run the four-step citation-gate algorithm. See module docstring."""
    if span.audit_id not in audit_index:
        return CitationResult.reject(
            CitationRejectReason.AUDIT_ID_NOT_FOUND, audit_id=span.audit_id
        )
    entry = audit_index[span.audit_id]
    if not isinstance(entry, AuditEntry):
        raise TypeError(
            f"audit_index[{span.audit_id!r}] is {type(entry).__name__}; expected "
            "AuditEntry. This is an integration-layer bug, not a citation failure."
        )

    try:
        raw = entry.stdout_path.read_bytes()
    except FileNotFoundError:
        return CitationResult.reject(
            CitationRejectReason.STDOUT_PATH_MISSING,
            audit_id=span.audit_id,
            stdout_path=str(entry.stdout_path),
        )
    except OSError as exc:
        return CitationResult.reject(
            CitationRejectReason.STDOUT_PATH_UNREADABLE,
            audit_id=span.audit_id,
            stdout_path=str(entry.stdout_path),
            errno=exc.errno,
            strerror=exc.strerror,
        )

    try:
        normalized = normalize_output(raw, tool=entry.tool)
    except UnknownToolError:
        return CitationResult.reject(
            CitationRejectReason.TOOL_NOT_REGISTERED,
            audit_id=span.audit_id,
            tool=entry.tool,
        )
    actual_hash = hashlib.sha256(normalized).hexdigest()
    if actual_hash != span.sha256_of_normalized_output:
        return CitationResult.reject(
            CitationRejectReason.OUTPUT_HASH_MISMATCH,
            audit_id=span.audit_id,
            expected_sha256=span.sha256_of_normalized_output,
            actual_sha256=actual_hash,
            raw_bytes=len(raw),
            normalized_bytes=len(normalized),
            tool=entry.tool,
        )

    lines = normalized.decode("utf-8", errors="surrogateescape").split("\n")
    total_lines = len(lines)
    if span.line_start >= total_lines or span.line_end > total_lines:
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
