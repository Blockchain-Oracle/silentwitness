"""Tests for the MCP tool response envelope import surface."""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, strategies as st
from pydantic import BaseModel, ValidationError

from silentwitness_common.ids import make_audit_id
from silentwitness_mcp.envelope import (
    EMPTY_PROVENANCE,
    AuditId,
    Confidence,
    DataProvenance,
    FailureReason,
    ResponseEnvelope,
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
        cmd_argv=(
            "/opt/silentwitness/vol3-venv/bin/vol",
            "-f",
            "/evidence/mem.raw",
            "windows.pslist.PsList",
        ),
    )


# ---------------------------------------------------------------------------
# Import-surface identity
# ---------------------------------------------------------------------------


def test_response_envelope_is_tool_response_alias() -> None:
    """The architecture-doc name and the code name MUST be one class
    (identity, not equality) so consumers can use either import."""
    assert ResponseEnvelope is ToolResponse


def test_auditid_alias_is_re_exported() -> None:
    """The MCP server side imports ``AuditId`` from envelope, not from
    common.types directly. The re-export must resolve to the same alias."""
    from silentwitness_common.types import AuditId as SourceAuditId

    assert AuditId is SourceAuditId


# ---------------------------------------------------------------------------
# audit_id format gate — applied via the AuditId Annotated alias
# ---------------------------------------------------------------------------


def test_audit_id_format_validator_accepts_canonical() -> None:
    """Architecture §4.4 happy path — every canonical shape accepted."""
    for valid in (
        "sift-aj-20260613-001",
        "sift-aj-20260613-999",
        "sift-mallory-20260101-1234",
        "sift-abu-20251225-42",
        "sift-ab-20260613-99999",  # 5-digit widening
        "sift-cd-20260613-123456",  # 6-digit widening
    ):
        env = ToolResponse[_SamplePayload](
            success=False,
            data=None,
            audit_id=valid,
            examiner=_EXAMINER,
            data_provenance=_provenance(),
        )
        assert env.audit_id == valid


@pytest.mark.parametrize(
    "bad_id",
    [
        "test-audit-id",
        "sift-AJ-20260613-001",
        "sift-aj-2026-06-13-001",
        "sift-aj-20260613",
        "sift--20260613-001",
        "sift-aj-20269999-001",
    ],
)
def test_audit_id_format_validator_rejects_non_canonical(bad_id: str) -> None:
    """Format violations must surface the canonical inner ValueError —
    either "does not match sift-..." (regex miss) or "has invalid date"
    (calendar check). Pinning either string catches a Pydantic upgrade
    that strips the inner detail."""
    with pytest.raises(ValidationError, match=r"(does not match sift-|has invalid date)"):
        ToolResponse[_SamplePayload](
            success=False,
            data=None,
            audit_id=bad_id,
            examiner=_EXAMINER,
            data_provenance=_provenance(),
        )


def test_audit_id_empty_string_rejected_by_length_constraint() -> None:
    """Empty string is rejected by ``StringConstraints(min_length=1)`` —
    NOT by the format validator. Pinning this separately so a regression
    removing the format validator still fails the other test cases
    loudly instead of being masked by the length check."""
    with pytest.raises(ValidationError, match=r"at least 1 character|string_too_short"):
        ToolResponse[_SamplePayload](
            success=False,
            data=None,
            audit_id="",
            examiner=_EXAMINER,
            data_provenance=_provenance(),
        )


def test_audit_id_whitespace_stripped_then_validated() -> None:
    """``_BASE_CONFIG.str_strip_whitespace=True`` strips before the
    AfterValidator runs, so a padded canonical id is accepted and the
    stored value is the trimmed one. Pinning the policy."""
    env = ToolResponse[_SamplePayload](
        success=False,
        data=None,
        audit_id="  sift-aj-20260613-007  \n",
        examiner=_EXAMINER,
        data_provenance=_provenance(),
    )
    assert env.audit_id == _AUDIT_ID


def test_audit_id_format_gate_also_applies_to_audit_entry() -> None:
    """Architecture §4.4: the format gate is the load-bearing primitive
    joining the audit log + HMAC ledger + report. AuditEntry shares the
    AuditId alias so the JSONL read path can't accept a malformed id."""
    from datetime import UTC, datetime

    from silentwitness_common.types import AuditEntry

    with pytest.raises(ValidationError, match=r"does not match sift-"):
        AuditEntry(
            ts=datetime(2026, 6, 13, 14, 27, tzinfo=UTC),
            audit_id="NOT-A-VALID-AUDIT-ID",
            tool="vol_pslist",
            params={},
            result_summary={},
            result_sha256=_SHA,
            stdout_path=Path("/cases/case-01/blobs/x.txt"),
            elapsed_ms=10.0,
            examiner="aj",
            model_used="anthropic:claude-opus-4-7",
        )


def test_audit_id_format_gate_also_applies_to_cited_span() -> None:
    """Citation gate's input — an LLM-emitted CitedSpan — must refuse a
    malformed audit_id at parse time, before the gate even fires."""
    from silentwitness_common.types import CitedSpan

    with pytest.raises(ValidationError, match=r"does not match sift-"):
        CitedSpan(
            audit_id="bogus-id",
            sha256_of_normalized_output=_SHA,
            line_start=0,
            line_end=1,
            span_text="anything",
        )


@given(
    examiner=st.text(
        alphabet=st.characters(min_codepoint=0x61, max_codepoint=0x7A),
        min_size=2,
        max_size=20,
    ),
    seq=st.integers(min_value=1, max_value=999),
)
def test_make_audit_id_round_trips_through_envelope(examiner: str, seq: int) -> None:
    """Property: anything ``make_audit_id`` produces is accepted by the
    AuditId validator. Locks factory ↔ validator agreement so a future
    format change MUST update both."""
    from datetime import date

    aid = make_audit_id(examiner, date(2026, 6, 13), seq)
    env = ToolResponse[_SamplePayload](
        success=False,
        data=None,
        audit_id=aid,
        examiner=_EXAMINER,
        data_provenance=_provenance(),
    )
    assert env.audit_id == aid


# ---------------------------------------------------------------------------
# DataProvenance shape
# ---------------------------------------------------------------------------


def test_data_provenance_round_trips_path_to_string() -> None:
    p = _provenance()
    restored = DataProvenance.model_validate_json(p.model_dump_json())
    assert isinstance(restored.stdout_path, Path)
    assert restored.stdout_path == p.stdout_path


def test_data_provenance_accepts_empty_cmd_argv() -> None:
    """Empty cmd_argv is the canonical pre-tool-execution-failure shape
    (used by make_empty_provenance)."""
    p = DataProvenance(
        tool="vol_pslist",
        stdout_path=Path("/dev/null"),
        result_sha256="0" * 64,
        elapsed_ms=0.0,
        cmd_argv=(),
    )
    assert p.cmd_argv == ()


def test_data_provenance_accepts_zero_elapsed_ms() -> None:
    """``ge=0.0`` includes the boundary — used by empty provenance."""
    p = DataProvenance(
        tool="x",
        stdout_path=Path("/dev/null"),
        result_sha256="0" * 64,
        elapsed_ms=0.0,
        cmd_argv=(),
    )
    assert p.elapsed_ms == 0.0


# ---------------------------------------------------------------------------
# Confidence — re-exported enum identity (the value tests live in
# tests/unit/test_common_types.py; here we just prove the re-export
# binds the same enum, not a shadow with broken comparisons)
# ---------------------------------------------------------------------------


def test_confidence_re_export_is_source_enum() -> None:
    """Reflected `str.__lt__` re-dispatch trap (PR-92) was caught by the
    source enum's ``TypeError`` overrides. If the re-export were a shadow,
    `Confidence.LOW < "ZEBRA"` would silently return True via the str
    fallback. Confirm identity, not just structural equality."""
    from silentwitness_common.types import Confidence as SourceConfidence

    assert Confidence is SourceConfidence
    with pytest.raises(TypeError):
        _ = Confidence.LOW < "ZEBRA"  # type: ignore[operator]


# ---------------------------------------------------------------------------
# FailureReason catalog
# ---------------------------------------------------------------------------


def test_failure_reason_round_trips_as_string() -> None:
    """StrEnum serialises as its value — keeps JSON shape stable."""
    assert FailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID.value == "MOUNT_NOT_RO_NOEXEC_NOSUID"
    assert str(FailureReason.EVIDENCE_NOT_REGISTERED) == "EVIDENCE_NOT_REGISTERED"


def test_failure_reason_catalog_covers_known_codes() -> None:
    """Architecture §4.11 + §4.10 + §4.5 + §4.7 names."""
    names = {r.value for r in FailureReason}
    for required in {
        "MOUNT_NOT_RO_NOEXEC_NOSUID",
        "EVIDENCE_NOT_REGISTERED",
        "CITATION_OUTPUT_HASH_MISMATCH",
        "CITATION_AUDIT_ID_NOT_FOUND",
        "HALLUCINATED_ENTITIES",
    }:
        assert required in names


# ---------------------------------------------------------------------------
# make_empty_provenance / EMPTY_PROVENANCE
# ---------------------------------------------------------------------------


def test_empty_provenance_uses_dev_null_and_zero_hash() -> None:
    """Sentinel that downstream readers grep for to distinguish
    "failed before the tool ran" from a real run."""
    assert EMPTY_PROVENANCE.stdout_path == Path("/dev/null")
    assert EMPTY_PROVENANCE.result_sha256 == "0" * 64
    assert EMPTY_PROVENANCE.elapsed_ms == 0.0
    assert EMPTY_PROVENANCE.cmd_argv == ()


def test_make_empty_provenance_sets_tool_name() -> None:
    p = make_empty_provenance("vol_pslist")
    assert p.tool == "vol_pslist"
    assert p.stdout_path == Path("/dev/null")


# ---------------------------------------------------------------------------
# make_failure_envelope factory
# ---------------------------------------------------------------------------


def test_make_failure_envelope_appends_reason_to_advisories() -> None:
    env = make_failure_envelope(
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        reason=FailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID,
    )
    assert env.success is False
    assert env.data is None
    assert env.advisories == ("MOUNT_NOT_RO_NOEXEC_NOSUID",)


def test_make_failure_envelope_with_only_reason_leaves_other_tuples_empty() -> None:
    """The actual production code path for ``_guard_mount`` — every
    optional tuple stays empty; only the reason populates advisories."""
    env = make_failure_envelope(
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        reason=FailureReason.EVIDENCE_NOT_REGISTERED,
    )
    assert env.caveats == ()
    assert env.corroboration == ()
    assert env.discipline_reminder is None
    assert env.advisories == ("EVIDENCE_NOT_REGISTERED",)


def test_make_failure_envelope_preserves_caller_advisories() -> None:
    env = make_failure_envelope(
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        reason=FailureReason.EVIDENCE_NOT_REGISTERED,
        advisories=("warm up step skipped",),
    )
    assert env.advisories == ("warm up step skipped", "EVIDENCE_NOT_REGISTERED")


def test_make_failure_envelope_allows_duplicate_reason_in_advisories() -> None:
    """Dedup is the caller's responsibility — locks the chosen policy
    so a future "smart" dedup change is visible."""
    env = make_failure_envelope(
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        reason=FailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID,
        advisories=("MOUNT_NOT_RO_NOEXEC_NOSUID",),
    )
    assert env.advisories == (
        "MOUNT_NOT_RO_NOEXEC_NOSUID",
        "MOUNT_NOT_RO_NOEXEC_NOSUID",
    )


def test_make_failure_envelope_rejects_invalid_audit_id() -> None:
    """The factory inherits the AuditId Annotated alias — bad audit_id
    rejected with the canonical error message."""
    with pytest.raises(ValidationError, match=r"does not match sift-"):
        make_failure_envelope(
            audit_id="not-a-real-audit-id",
            examiner=_EXAMINER,
            reason=FailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID,
        )


def test_make_failure_envelope_accepts_real_provenance_for_post_run_failures() -> None:
    """Failures that fire AFTER the tool ran (e.g., citation hash
    mismatch) pass a real DataProvenance instead of EMPTY_PROVENANCE."""
    env = make_failure_envelope(
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        reason=FailureReason.CITATION_OUTPUT_HASH_MISMATCH,
        data_provenance=_provenance(),
    )
    assert env.data_provenance.tool == "vol_pslist"
    assert env.data_provenance.stdout_path != Path("/dev/null")
