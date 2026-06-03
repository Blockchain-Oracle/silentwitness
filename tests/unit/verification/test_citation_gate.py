"""Behavioural tests for src/silentwitness_mcp/verification/citation_gate.py.

Real filesystem (tmp_path), real Pydantic models, real normalisation pass —
no mocks per architecture §14. Each of the five :class:`CitationRejectReason`
codes has at least one dedicated test; the success path is covered by
multiple variants. Wedge invariants (tamper detection, line-range
discipline) get extra coverage to catch silent regressions.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from silentwitness_common.types import AuditEntry
from silentwitness_mcp.verification._types import (
    CitationRejectReason,
    CitationResult,
    CitedSpan,
)
from silentwitness_mcp.verification.citation_gate import verify_citation
from silentwitness_mcp.verification.normalizer import normalize_output

_HASH64 = "a" * 64
_AUDIT_ID = "sift-aj-20260613-007"
_FIXED_NOW = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)


def _make_entry(
    stdout_path: Path,
    *,
    audit_id: str = _AUDIT_ID,
    tool: str = "_universal_only",
) -> AuditEntry:
    return AuditEntry(
        ts=_FIXED_NOW,
        audit_id=audit_id,
        tool=tool,
        params={},
        result_summary={},
        result_sha256=_HASH64,
        stdout_path=stdout_path,
        elapsed_ms=120.5,
        examiner="aj",
        model_used="anthropic:claude-opus-4-7",
    )


def _normalised_hash(raw: bytes, tool: str = "_universal_only") -> str:
    return hashlib.sha256(normalize_output(raw, tool=tool)).hexdigest()


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


def test_success_on_valid_citation(tmp_path: Path) -> None:
    stdout = tmp_path / "out.txt"
    raw = b"line0\nline1\nline2 svchost.exe at PID 1208\nline3\n"
    stdout.write_bytes(raw)
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=_normalised_hash(raw),
        line_start=2,
        line_end=3,
        span_text="svchost.exe at PID 1208",
    )
    result = verify_citation(span, audit_index={_AUDIT_ID: _make_entry(stdout)})
    assert result.success is True
    assert result.span == span
    assert result.reason is None


def test_success_with_multi_line_span(tmp_path: Path) -> None:
    stdout = tmp_path / "out.txt"
    raw = b"header\nfoo\nbar\nbaz\nfooter\n"
    stdout.write_bytes(raw)
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=_normalised_hash(raw),
        line_start=1,
        line_end=4,
        span_text="bar\nbaz",
    )
    result = verify_citation(span, audit_index={_AUDIT_ID: _make_entry(stdout)})
    assert result.success is True


# ---------------------------------------------------------------------------
# AUDIT_ID_NOT_FOUND
# ---------------------------------------------------------------------------


def test_reject_audit_id_not_found_on_unknown_audit_id(tmp_path: Path) -> None:
    span = CitedSpan(
        audit_id="sift-aj-20260613-999",
        sha256_of_normalized_output=_HASH64,
        line_start=0,
        line_end=1,
        span_text="anything",
    )
    result = verify_citation(span, audit_index={})
    assert result.success is False
    assert result.reason == CitationRejectReason.AUDIT_ID_NOT_FOUND
    assert result.context["audit_id"] == "sift-aj-20260613-999"


# ---------------------------------------------------------------------------
# STDOUT_PATH_MISSING
# ---------------------------------------------------------------------------


def test_reject_stdout_path_missing_when_blob_deleted(tmp_path: Path) -> None:
    stdout = tmp_path / "vanished.txt"  # never created
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=_HASH64,
        line_start=0,
        line_end=1,
        span_text="anything",
    )
    result = verify_citation(span, audit_index={_AUDIT_ID: _make_entry(stdout)})
    assert result.success is False
    assert result.reason == CitationRejectReason.STDOUT_PATH_MISSING
    assert "vanished.txt" in result.context["stdout_path"]


# ---------------------------------------------------------------------------
# STDOUT_PATH_UNREADABLE (PR-110 silent-failure C2 — broader OSError catch)
# ---------------------------------------------------------------------------


def test_reject_stdout_path_unreadable_on_permission_denied(tmp_path: Path) -> None:
    import os

    stdout = tmp_path / "locked.txt"
    stdout.write_bytes(b"content\n")
    os.chmod(stdout, 0o000)
    try:
        span = CitedSpan(
            audit_id=_AUDIT_ID,
            sha256_of_normalized_output=_HASH64,
            line_start=0,
            line_end=1,
            span_text="anything",
        )
        result = verify_citation(span, audit_index={_AUDIT_ID: _make_entry(stdout)})
        assert result.success is False
        assert result.reason == CitationRejectReason.STDOUT_PATH_UNREADABLE
        assert result.context["errno"] is not None
    finally:
        os.chmod(stdout, 0o644)


# ---------------------------------------------------------------------------
# TOOL_NOT_REGISTERED (PR-110 silent-failure C1 — UnknownToolError caught)
# ---------------------------------------------------------------------------


def test_reject_tool_not_registered_on_unknown_tool(tmp_path: Path) -> None:
    """Round-2 fix: if an audit entry's tool field was removed from
    TOOL_PATTERNS between record and verify, normalize_output raises
    UnknownToolError; the gate now maps it to a structured rejection
    rather than letting the exception escape."""
    stdout = tmp_path / "out.txt"
    stdout.write_bytes(b"some content\n")
    entry = _make_entry(stdout, tool="vol_pslit")  # typo / removed tool
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=_HASH64,
        line_start=0,
        line_end=1,
        span_text="some content",
    )
    result = verify_citation(span, audit_index={_AUDIT_ID: entry})
    assert result.success is False
    assert result.reason == CitationRejectReason.TOOL_NOT_REGISTERED
    assert result.context["tool"] == "vol_pslit"


# ---------------------------------------------------------------------------
# OUTPUT_HASH_MISMATCH
# ---------------------------------------------------------------------------


def test_reject_output_hash_mismatch_with_wrong_hash(tmp_path: Path) -> None:
    stdout = tmp_path / "out.txt"
    raw = b"real bytes\n"
    stdout.write_bytes(raw)
    bogus_hash = "b" * 64  # known not to be sha256(raw)
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=bogus_hash,
        line_start=0,
        line_end=1,
        span_text="real bytes",
    )
    result = verify_citation(span, audit_index={_AUDIT_ID: _make_entry(stdout)})
    assert result.success is False
    assert result.reason == CitationRejectReason.OUTPUT_HASH_MISMATCH
    assert result.context["expected_sha256"] == bogus_hash
    assert result.context["actual_sha256"] == _normalised_hash(raw)


def test_reject_output_hash_mismatch_after_blob_tampering(tmp_path: Path) -> None:
    """Wedge: if the stored blob is mutated post-citation-recording, the
    recompute catches it. This is the load-bearing tamper detector."""
    stdout = tmp_path / "out.txt"
    raw = b"original content\n"
    stdout.write_bytes(raw)
    recorded_hash = _normalised_hash(raw)
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=recorded_hash,
        line_start=0,
        line_end=1,
        span_text="original content",
    )
    # Tamper after citation was recorded
    stdout.write_bytes(b"tampered content\n")
    result = verify_citation(span, audit_index={_AUDIT_ID: _make_entry(stdout)})
    assert result.success is False
    assert result.reason == CitationRejectReason.OUTPUT_HASH_MISMATCH


# ---------------------------------------------------------------------------
# LINE_RANGE_OUT_OF_BOUNDS
# ---------------------------------------------------------------------------


def test_reject_line_range_out_of_bounds_when_line_end_exceeds(tmp_path: Path) -> None:
    stdout = tmp_path / "out.txt"
    raw = b"line0\nline1\nline2\n"
    stdout.write_bytes(raw)
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=_normalised_hash(raw),
        line_start=1,
        line_end=99,  # exceeds line count
        span_text="line1",
    )
    result = verify_citation(span, audit_index={_AUDIT_ID: _make_entry(stdout)})
    assert result.success is False
    assert result.reason == CitationRejectReason.LINE_RANGE_OUT_OF_BOUNDS
    assert result.context["line_end"] == 99
    assert result.context["total_lines"] >= 3


# ---------------------------------------------------------------------------
# SPAN_NOT_IN_LINES
# ---------------------------------------------------------------------------


def test_reject_span_not_in_lines_when_text_absent(tmp_path: Path) -> None:
    """The agent claims a substring that isn't actually in the sliced range —
    closed-domain hallucination caught."""
    stdout = tmp_path / "out.txt"
    raw = b"line0\nline1\nline2\n"
    stdout.write_bytes(raw)
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=_normalised_hash(raw),
        line_start=0,
        line_end=3,
        span_text="this text does not exist anywhere",
    )
    result = verify_citation(span, audit_index={_AUDIT_ID: _make_entry(stdout)})
    assert result.success is False
    assert result.reason == CitationRejectReason.SPAN_NOT_IN_LINES
    assert result.context["line_start"] == 0
    assert result.context["line_end"] == 3
    assert result.context["span_text"] == "this text does not exist anywhere"


def test_reject_span_not_in_lines_when_text_in_wrong_lines(tmp_path: Path) -> None:
    """Substring exists in the blob but OUTSIDE the cited line range."""
    stdout = tmp_path / "out.txt"
    raw = b"target\nother\nother\n"
    stdout.write_bytes(raw)
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=_normalised_hash(raw),
        line_start=1,
        line_end=3,
        span_text="target",  # exists at line 0, not in slice [1:3]
    )
    result = verify_citation(span, audit_index={_AUDIT_ID: _make_entry(stdout)})
    assert result.success is False
    assert result.reason == CitationRejectReason.SPAN_NOT_IN_LINES


# ---------------------------------------------------------------------------
# Type-level invariants on CitedSpan / CitationResult
# ---------------------------------------------------------------------------


def test_cited_span_rejects_inverted_range() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="line_end"):
        CitedSpan(
            audit_id=_AUDIT_ID,
            sha256_of_normalized_output=_HASH64,
            line_start=5,
            line_end=5,  # equal → still rejected (half-open requires end > start)
            span_text="x",
        )


def test_cited_span_rejects_negative_line_start() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CitedSpan(
            audit_id=_AUDIT_ID,
            sha256_of_normalized_output=_HASH64,
            line_start=-1,
            line_end=2,
            span_text="x",
        )


def test_cited_span_sha256_lowercases_uppercase_input() -> None:
    """Sha256Hex BeforeValidator canonicalises to lowercase rather than rejecting."""
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output="A" * 64,
        line_start=0,
        line_end=1,
        span_text="x",
    )
    assert span.sha256_of_normalized_output == "a" * 64


def test_citation_result_rejects_success_without_span() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="span"):
        CitationResult(success=True)


def test_citation_result_rejects_failure_without_reason() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="reason"):
        CitationResult(success=False)


def test_citation_result_rejects_failure_with_span() -> None:
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=_HASH64,
        line_start=0,
        line_end=1,
        span_text="x",
    )
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="must not carry span"):
        CitationResult(success=False, reason=CitationRejectReason.AUDIT_ID_NOT_FOUND, span=span)
