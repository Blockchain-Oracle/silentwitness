"""Tests for the MCP tool response envelope import surface."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from hypothesis import given, strategies as st
from pydantic import BaseModel, ValidationError

from silentwitness_common.failure import FailureReason as SourceFailureReason
from silentwitness_common.ids import make_audit_id
from silentwitness_common.types import (
    AuditEntry,
    AuditId as SourceAuditId,
    Confidence as SourceConfidence,
)
from silentwitness_mcp.envelope import (
    EMPTY_PROVENANCE_TOOL_NAME,
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
    assert AuditId is SourceAuditId


def test_failure_reason_is_re_exported_from_common() -> None:
    """FailureReason is the wire contract between MCP and agent — lives
    in common.failure. envelope re-exports it for MCP-side convenience."""
    assert FailureReason is SourceFailureReason


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
        "sift-ab-20260613-99999",
        "sift-cd-20260613-123456",
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
        "sift-aj-20250229-001",  # non-leap Feb 29
        "sift-aj-20260631-001",  # June 31
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
    NOT by the format validator. Pinned separately so a regression
    removing the format validator still fails the other tests loudly."""
    with pytest.raises(ValidationError, match=r"at least 1 (character|item)|too_short"):
        ToolResponse[_SamplePayload](
            success=False,
            data=None,
            audit_id="",
            examiner=_EXAMINER,
            data_provenance=_provenance(),
        )


def test_audit_id_whitespace_stripped_then_validated() -> None:
    """``_BASE_CONFIG.str_strip_whitespace=True`` strips before the
    AfterValidator runs. Pin the policy so an Annotated-order refactor
    swapping AfterValidator → BeforeValidator breaks this test."""
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


@given(
    examiner_seed=st.text(
        alphabet=st.characters(
            min_codepoint=0x30, max_codepoint=0x7A, blacklist_categories=("Cc", "Cs")
        ),
        min_size=1,
        max_size=24,
    ).filter(lambda s: any(c.isalnum() for c in s)),
    seq=st.integers(min_value=1, max_value=1_000_000),
    day=st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)),
)
def test_make_audit_id_round_trips_through_envelope(
    examiner_seed: str, seq: int, day: date
) -> None:
    """Property: every ``make_audit_id`` output is accepted by the
    AuditId validator. Examiner-seed includes digits + punctuation
    that slug_examiner strips (filtered to require ≥1 alnum so the
    slug isn't empty); seq covers widening past 999; day covers leap
    days + year boundaries. Locks factory ↔ validator agreement."""
    aid = make_audit_id(examiner_seed, day, seq)
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
    """Empty cmd_argv is the canonical pre-tool-execution shape."""
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
# discipline_reminder semantics
# ---------------------------------------------------------------------------


def test_discipline_reminder_is_optional() -> None:
    """Default is ``None`` — the "no reminder requested" sentinel."""
    env = ToolResponse[_SamplePayload](
        success=False,
        data=None,
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        data_provenance=_provenance(),
    )
    assert env.discipline_reminder is None


# ---------------------------------------------------------------------------
# Confidence — re-exported enum identity
# ---------------------------------------------------------------------------


def test_confidence_re_export_is_source_enum() -> None:
    """Reflected ``str.__lt__`` re-dispatch trap (PR-92) was caught by
    the source enum's ``TypeError`` overrides. If the re-export were a
    shadow, ``Confidence.LOW < "ZEBRA"`` would silently return True via
    the str fallback. Confirm identity, not just structural equality."""
    assert Confidence is SourceConfidence
    with pytest.raises(TypeError):
        _ = Confidence.LOW < "ZEBRA"  # type: ignore[operator]


# ---------------------------------------------------------------------------
# FailureReason catalog
# ---------------------------------------------------------------------------


def test_failure_reason_round_trips_as_string() -> None:
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
# make_empty_provenance (no module-level singleton — cross-envelope
# contamination via __dict__ / object.__setattr__ removed in round-3)
# ---------------------------------------------------------------------------


def test_empty_provenance_uses_dev_null_and_zero_hash() -> None:
    p = make_empty_provenance(EMPTY_PROVENANCE_TOOL_NAME)
    assert p.stdout_path == Path("/dev/null")
    assert p.result_sha256 == "0" * 64
    assert p.elapsed_ms == 0.0
    assert p.cmd_argv == ()
    assert p.tool == EMPTY_PROVENANCE_TOOL_NAME


def test_empty_provenance_tool_name_literal_pin() -> None:
    """Round-3 pr-test L3: catches a rename that grep would miss
    (analysts grep this exact string per the architecture §4.11 sentinel
    contract)."""
    assert EMPTY_PROVENANCE_TOOL_NAME == "_pre_tool_execution_"


def test_audit_id_bytes_rejected_before_min_length_constraint() -> None:
    """Round-3 pr-test H1: pins the BeforeValidator → core ordering. If
    require_audit_id_str were demoted to AfterValidator, b"" would fail
    too_short first and the AuditId-requires-str diagnostic would
    silently disappear."""
    with pytest.raises(ValidationError, match=r"AuditId requires str"):
        ToolResponse[_SamplePayload](
            success=False,
            data=None,
            audit_id=b"",  # type: ignore[arg-type]
            examiner=_EXAMINER,
            data_provenance=_provenance(),
        )


def test_make_empty_provenance_accepts_real_tool_name() -> None:
    p = make_empty_provenance("vol_pslist")
    assert p.tool == "vol_pslist"


# ---------------------------------------------------------------------------
# make_failure_envelope factory (round-3: data_provenance is REQUIRED;
# generic TPayload bind restored)
# ---------------------------------------------------------------------------


def test_make_failure_envelope_appends_reason_to_advisories() -> None:
    env = make_failure_envelope(
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        reason=FailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID,
        data_provenance=make_empty_provenance("vol_pslist"),
    )
    assert env.success is False
    assert env.data is None
    assert env.advisories == ("MOUNT_NOT_RO_NOEXEC_NOSUID",)
    # Pin the type: a future refactor dropping `reason.value` and
    # storing the enum instance would still pass tuple-equality
    # (StrEnum.__eq__ falls back to str), but the in-memory type would
    # diverge from the JSONL bytes.
    assert type(env.advisories[-1]) is str


def test_make_failure_envelope_preserves_caller_advisories() -> None:
    env = make_failure_envelope(
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        reason=FailureReason.EVIDENCE_NOT_REGISTERED,
        data_provenance=make_empty_provenance("vol_pslist"),
        advisories=("warm up step skipped",),
    )
    assert env.advisories == ("warm up step skipped", "EVIDENCE_NOT_REGISTERED")


def test_make_failure_envelope_rejects_invalid_audit_id() -> None:
    """The factory inherits the AuditId Annotated alias."""
    with pytest.raises(ValidationError, match=r"does not match sift-"):
        make_failure_envelope(
            audit_id="not-a-real-audit-id",
            examiner=_EXAMINER,
            reason=FailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID,
            data_provenance=make_empty_provenance("vol_pslist"),
        )
