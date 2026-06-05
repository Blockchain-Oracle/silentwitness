"""Round-2 + round-3 review-fix tests for the envelope (split from the
main file for the 400-LOC file-size guard)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from silentwitness_common.types import AuditEntry, CitedSpan
from silentwitness_mcp.envelope import (
    DataProvenance,
    FailureReason,
    ToolResponse,
    make_empty_provenance,
    make_failure_envelope,
)

_AUDIT_ID = "sift-aj-20260613-007"
_EXAMINER = "aj"
_SHA = "a" * 64


class _SamplePayload(BaseModel):
    pid: int
    name: str


def _provenance() -> DataProvenance:
    return DataProvenance(
        tool="vol_pslist",
        stdout_path=Path("/cases/case-01/blobs/sift-aj-20260613-007.txt"),
        result_sha256=_SHA,
        elapsed_ms=234.5,
        cmd_argv=("/opt/silentwitness/vol3-venv/bin/vol", "-f", "/x.raw", "pslist"),
    )


# ---------------------------------------------------------------------------
# Round-2 silent-failure C2: bytes coercion (PR-92 surface)
# ---------------------------------------------------------------------------


def test_audit_id_rejects_bytes_input() -> None:
    """PR-92 silent-failure surface — Pydantic v2's default str-coercion
    UTF-8-decodes bytes silently. AuditId's BeforeValidator mirrors the
    Sha256Hex _normalise_hex isinstance check so bytes are rejected at
    every carrier site."""
    with pytest.raises(ValidationError, match=r"AuditId requires str"):
        ToolResponse[_SamplePayload](
            success=False,
            data=None,
            audit_id=b"sift-aj-20260613-007",  # type: ignore[arg-type]
            examiner=_EXAMINER,
            data_provenance=_provenance(),
        )


# ---------------------------------------------------------------------------
# Round-2 type-design S2: tuple-element propagation
# ---------------------------------------------------------------------------


def test_audit_id_format_gate_propagates_into_tuple_elements() -> None:
    """Observation.audit_ids: tuple[AuditId, ...] — validator fires PER
    ELEMENT, not just on the container."""
    from silentwitness_common.types import Observation

    valid_span = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output=_SHA,
        line_start=0,
        line_end=1,
        span_text="x",
    )
    with pytest.raises(ValidationError, match=r"does not match sift-"):
        Observation(
            id="O-001",
            summary="x",
            cited_spans=(valid_span,),
            audit_ids=(_AUDIT_ID, "bogus-second-element"),
        )


# ---------------------------------------------------------------------------
# Round-2 silent-failure C1 + round-2 code-reviewer Important:
# StripEvent.audit_id migrated to AuditId
# ---------------------------------------------------------------------------


def test_audit_id_format_gate_also_applies_to_strip_event() -> None:
    """Sanitizer's per-strip JSONL row carries audit_id — same AuditId
    alias so malformed values can't slip into sanitizer.jsonl."""
    from silentwitness_mcp.verification.sanitizer import StripEvent

    with pytest.raises(ValidationError, match=r"does not match sift-"):
        StripEvent(
            ts=datetime(2026, 6, 13, 14, 27, tzinfo=UTC),
            audit_id="bogus-id",
            pattern_id="xml-role-tag",
            position_in_intermediate=0,
            op_sequence=0,
            original_excerpt_hash=_SHA,
        )


def test_audit_entry_format_gate_via_model_validate_json() -> None:
    """Round-2 silent-failure: confirm AfterValidator fires on the
    JSONL deserialise path, not just on direct construction."""
    bad_line = (
        '{"ts":"2026-06-13T14:27:00Z","audit_id":"NOT-VALID","tool":"vol_pslist",'
        '"params":{},"result_summary":{},'
        f'"result_sha256":"{_SHA}",'
        '"stdout_path":"/cases/case-01/x.txt","elapsed_ms":10.0,"examiner":"aj",'
        '"model_used":"anthropic:claude-opus-4-7","model_token_count":{}}'
    )
    with pytest.raises(ValidationError, match=r"does not match sift-"):
        AuditEntry.model_validate_json(bad_line)


# ---------------------------------------------------------------------------
# pr-test-analyzer Medium: required-field discipline rebuild after the
# round-2 trim removed these from test_envelope.py
# ---------------------------------------------------------------------------


def test_missing_audit_id_rejected() -> None:
    with pytest.raises(ValidationError, match=r"audit_id"):
        ToolResponse[_SamplePayload](  # type: ignore[call-arg]
            success=False,
            data=None,
            examiner=_EXAMINER,
            data_provenance=_provenance(),
        )


def test_missing_examiner_rejected() -> None:
    with pytest.raises(ValidationError, match=r"examiner"):
        ToolResponse[_SamplePayload](  # type: ignore[call-arg]
            success=False,
            data=None,
            audit_id=_AUDIT_ID,
            data_provenance=_provenance(),
        )


def test_missing_data_provenance_rejected() -> None:
    """Every audit-log entry MUST carry provenance — even failures."""
    with pytest.raises(ValidationError, match=r"data_provenance"):
        ToolResponse[_SamplePayload](  # type: ignore[call-arg]
            success=False,
            data=None,
            audit_id=_AUDIT_ID,
            examiner=_EXAMINER,
        )


# ---------------------------------------------------------------------------
# silent-failure-hunter M1: discipline_reminder semantics
# ---------------------------------------------------------------------------


def test_discipline_reminder_preserves_real_strings() -> None:
    env = ToolResponse[_SamplePayload](
        success=False,
        data=None,
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        data_provenance=_provenance(),
        discipline_reminder="cross-check pstree before claiming malice",
    )
    assert env.discipline_reminder == "cross-check pstree before claiming malice"


# ---------------------------------------------------------------------------
# Round-3 H2 / type-design I2: shared EMPTY_PROVENANCE singleton removed
# ---------------------------------------------------------------------------


def test_make_empty_provenance_per_call_is_fresh_instance() -> None:
    """No shared singleton — each call returns a fresh instance so
    Pydantic's ``object.__setattr__`` frozen-bypass channel cannot
    contaminate sibling envelopes."""
    a = make_empty_provenance("vol_pslist")
    b = make_empty_provenance("vol_pslist")
    assert a is not b
    assert a == b


def test_make_failure_envelope_requires_data_provenance() -> None:
    """data_provenance has no default — round-3 removed the shared
    EMPTY_PROVENANCE singleton so callers can't accidentally leak the
    ``_pre_tool_execution_`` sentinel tool name into the audit log."""
    with pytest.raises(TypeError, match=r"data_provenance"):
        make_failure_envelope(  # type: ignore[call-arg]
            audit_id=_AUDIT_ID,
            examiner=_EXAMINER,
            reason=FailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID,
        )


# ---------------------------------------------------------------------------
# pr-test-analyzer Medium: factory advisory string-type + duplicate
# policy + production paths
# ---------------------------------------------------------------------------


def test_make_failure_envelope_with_only_reason_leaves_other_tuples_empty() -> None:
    """Production code path for guard refusals — every optional tuple
    stays empty; only the reason populates advisories."""
    env = make_failure_envelope(
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        reason=FailureReason.EVIDENCE_NOT_REGISTERED,
        data_provenance=make_empty_provenance("register_evidence"),
    )
    assert env.caveats == ()
    assert env.corroboration == ()
    assert env.discipline_reminder is None
    assert env.advisories == ("EVIDENCE_NOT_REGISTERED",)


def test_make_failure_envelope_allows_duplicate_reason_in_advisories() -> None:
    """Dedup is the caller's responsibility — locks the chosen policy
    so a future "smart" dedup change is visible."""
    env = make_failure_envelope(
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        reason=FailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID,
        data_provenance=make_empty_provenance("vol_pslist"),
        advisories=("MOUNT_NOT_RO_NOEXEC_NOSUID",),
    )
    assert env.advisories == (
        "MOUNT_NOT_RO_NOEXEC_NOSUID",
        "MOUNT_NOT_RO_NOEXEC_NOSUID",
    )


def test_make_failure_envelope_accepts_real_provenance_for_post_run_failures() -> None:
    """Failures fired AFTER the tool ran (e.g., citation hash mismatch)
    pass a real DataProvenance."""
    env = make_failure_envelope(
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        reason=FailureReason.CITATION_OUTPUT_HASH_MISMATCH,
        data_provenance=_provenance(),
    )
    assert env.data_provenance.tool == "vol_pslist"
    assert env.data_provenance.stdout_path != Path("/dev/null")
