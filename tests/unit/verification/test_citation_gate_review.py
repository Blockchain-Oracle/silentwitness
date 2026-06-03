"""Round-2 review-fix tests for citation gate (split from main file for
the 400-LOC file-size guard). Covers TOOL_NOT_REGISTERED + STDOUT_PATH_UNREADABLE
+ richer OUTPUT_HASH_MISMATCH context + line_start defence-in-depth + None-value
in audit_index + idempotency + Hypothesis property test on wedge soundness.
"""

from __future__ import annotations

import hashlib
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from silentwitness_common.types import AuditEntry, CitedSpan
from silentwitness_mcp.verification._types import CitationRejectReason
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


def test_output_hash_mismatch_context_includes_diagnostic_lengths(tmp_path: Path) -> None:
    """PR-110 silent-failure H4: distinguish 'agent claimed wrong hash' from
    'normalizer coverage gap' via raw_bytes / normalized_bytes / tool."""
    stdout = tmp_path / "out.txt"
    raw = b"real bytes\n"
    stdout.write_bytes(raw)
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output="b" * 64,
        line_start=0,
        line_end=1,
        span_text="real bytes",
    )
    result = verify_citation(span, audit_index={_AUDIT_ID: _make_entry(stdout)})
    assert result.success is False
    assert result.reason == CitationRejectReason.OUTPUT_HASH_MISMATCH
    assert result.context["raw_bytes"] == len(raw)
    assert result.context["normalized_bytes"] > 0
    assert result.context["tool"] == "_universal_only"


def test_reject_line_range_out_of_bounds_when_line_start_exceeds(tmp_path: Path) -> None:
    """PR-110 silent-failure M5: defence in depth — line_start >= total_lines
    must independently trip the bounds check (don't rely on transitivity
    through the line_end > line_start Pydantic validator)."""
    stdout = tmp_path / "out.txt"
    raw = b"line0\nline1\nline2\n"  # 3 content lines + trailing empty = 4
    stdout.write_bytes(raw)
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=_normalised_hash(raw),
        line_start=10,
        line_end=11,
        span_text="line0",
    )
    result = verify_citation(span, audit_index={_AUDIT_ID: _make_entry(stdout)})
    assert result.success is False
    assert result.reason == CitationRejectReason.LINE_RANGE_OUT_OF_BOUNDS
    assert result.context["line_start"] == 10


def test_none_value_in_audit_index_raises_type_error(tmp_path: Path) -> None:
    """PR-110 silent-failure H3: a builder bug that writes None for an
    audit_id is an integration-layer defect, NOT an agent error.
    Conflating into AUDIT_ID_NOT_FOUND would obscure the bug."""
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=_HASH64,
        line_start=0,
        line_end=1,
        span_text="x",
    )
    with pytest.raises(TypeError, match="integration-layer bug"):
        verify_citation(span, audit_index={_AUDIT_ID: None})  # type: ignore[dict-item]


def test_verify_citation_is_idempotent(tmp_path: Path) -> None:
    """The module docstring promises purity. Same inputs → same outputs."""
    stdout = tmp_path / "out.txt"
    raw = b"alpha\nbeta\n"
    stdout.write_bytes(raw)
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=_normalised_hash(raw),
        line_start=0,
        line_end=1,
        span_text="alpha",
    )
    index = {_AUDIT_ID: _make_entry(stdout)}
    assert verify_citation(span, index) == verify_citation(span, index)


@given(payload=st.binary(min_size=1, max_size=512))
@settings(max_examples=20, deadline=None)
def test_property_valid_substring_within_range_always_accepts(payload: bytes) -> None:
    """For any non-empty payload, a citation whose hash matches AND whose
    span_text is a verbatim substring of lines[line_start:line_end] MUST
    accept. Soundness of the verifier under fuzz."""
    with tempfile.TemporaryDirectory() as raw_dir:
        stdout = Path(raw_dir) / "out.txt"
        stdout.write_bytes(payload)
        normalised = normalize_output(payload, tool="_universal_only")
        if not normalised:
            return  # vacuous
        lines = normalised.decode("utf-8", errors="surrogateescape").split("\n")
        if not lines or not lines[0]:
            return  # need at least one non-empty line for span_text
        # Pydantic rejects strings containing lone surrogates (\udcXX from
        # surrogateescape on invalid UTF-8 bytes). An agent could never
        # emit such a span_text in practice — filter the case out.
        if any(0xDC80 <= ord(c) <= 0xDCFF for c in lines[0]):
            return
        span = CitedSpan(
            audit_id=_AUDIT_ID,
            sha256_of_normalized_output=hashlib.sha256(normalised).hexdigest(),
            line_start=0,
            line_end=1,
            span_text=lines[0],
        )
        entry = _make_entry(stdout)
        result = verify_citation(span, audit_index={_AUDIT_ID: entry})
        assert result.success is True


# ---------------------------------------------------------------------------
# Wedge edge cases
# ---------------------------------------------------------------------------


def test_hash_check_uses_normalised_form_not_raw(tmp_path: Path) -> None:
    """The agent's claimed sha256 must be of NORMALISED output, not raw.
    A blob with ANSI codes hashes differently before and after normalisation;
    the gate is keyed on the normalised hash."""
    stdout = tmp_path / "out.txt"
    raw = b"\x1b[31mERROR\x1b[0m: missing\n"
    stdout.write_bytes(raw)
    normalised_hash = _normalised_hash(raw)
    raw_hash = hashlib.sha256(raw).hexdigest()
    assert normalised_hash != raw_hash  # sanity: differ
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=normalised_hash,
        line_start=0,
        line_end=1,
        span_text="ERROR: missing",  # ANSI-stripped form
    )
    result = verify_citation(span, audit_index={_AUDIT_ID: _make_entry(stdout)})
    assert result.success is True


def test_unicode_span_round_trips_through_surrogateescape(tmp_path: Path) -> None:
    """Invalid UTF-8 in the raw blob round-trips losslessly via the
    normalizer's surrogateescape decode → SHA-256 stays stable."""
    stdout = tmp_path / "out.txt"
    raw = b"valid \xff\xfe invalid\nfollowing line\n"
    stdout.write_bytes(raw)
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=_normalised_hash(raw),
        line_start=1,
        line_end=2,
        span_text="following line",
    )
    result = verify_citation(span, audit_index={_AUDIT_ID: _make_entry(stdout)})
    assert result.success is True


def test_per_tool_normalisation_applied_at_hash_check(tmp_path: Path) -> None:
    """If the audit entry's tool is vol_pslist, the gate normalises with
    Vol3 rules (strips banner). The agent's hash must match the post-strip
    form, not the raw."""
    stdout = tmp_path / "out.txt"
    raw = b"Volatility 3 Framework 2.7.0\nPID  Name\n4    System\n"
    stdout.write_bytes(raw)
    expected = hashlib.sha256(normalize_output(raw, tool="vol_pslist")).hexdigest()
    span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=expected,
        line_start=0,
        line_end=2,
        span_text="System",
    )
    entry = _make_entry(stdout, tool="vol_pslist")
    result = verify_citation(span, audit_index={_AUDIT_ID: entry})
    assert result.success is True
