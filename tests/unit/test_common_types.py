"""Behavioural tests for src/silentwitness_common/types.py.

Each test maps 1:1 to a BDD criterion in story-common-types.md OR pins one
of the load-bearing model invariants (citation gate verifies CitedSpan
shape; audit logger reads AuditEntry; agent reads ToolResponse).
"""

from __future__ import annotations

import operator
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from silentwitness_common.types import (
    AuditEntry,
    CitedSpan,
    Confidence,
    CriticVerdict,
    DataProvenance,
    EvidenceType,
    Finding,
    FindingStatus,
    HypothesisStatus,
    Interpretation,
    Observation,
    Pivot,
    ReportSection,
    ResponseEnvelope,
    SpecialistName,
    ToolResponse,
)

_HASH64 = "a" * 64


def _cited_span() -> CitedSpan:
    return CitedSpan(
        stdout_path=Path("/var/lib/silentwitness/stdout/pslist-001.out"),
        line_start=10,
        line_end=12,
        content_sha256=_HASH64,
    )


def _data_provenance() -> DataProvenance:
    return DataProvenance(
        tool="vol_pslist",
        stdout_path=Path("/var/lib/silentwitness/stdout/pslist-001.out"),
        result_sha256=_HASH64,
        elapsed_ms=120.5,
        cmd_argv=("/opt/silentwitness/vol3-venv/bin/vol", "-f", "mem.raw", "windows.pslist"),
    )


# ---------------------------------------------------------------------------
# Round-trip + extra=forbid
# ---------------------------------------------------------------------------


def test_cited_span_roundtrips_through_json() -> None:
    span = _cited_span()
    re_parsed = CitedSpan.model_validate_json(span.model_dump_json())
    assert re_parsed == span


def test_observation_roundtrips_through_json() -> None:
    obs = Observation(
        id="O-001",
        summary="powershell.exe ran with -EncodedCommand",
        cited_spans=(_cited_span(),),
        audit_ids=("sift-aj-20260613-007",),
    )
    re_parsed = Observation.model_validate_json(obs.model_dump_json())
    assert re_parsed == obs


def test_observation_rejects_unknown_field() -> None:
    """extra='forbid' must reject typo'd keys at construction time."""
    with pytest.raises(ValidationError):
        Observation(
            id="O-001",
            summary="x",
            cited_spans=(_cited_span(),),
            audit_ids=("a",),
            typoed_field="oops",  # type: ignore[call-arg]
        )


# ---------------------------------------------------------------------------
# CitedSpan invariants
# ---------------------------------------------------------------------------


def test_cited_span_rejects_negative_line_start() -> None:
    with pytest.raises(ValidationError):
        CitedSpan(
            stdout_path=Path("/x"),
            line_start=-1,
            line_end=5,
            content_sha256=_HASH64,
        )


def test_cited_span_rejects_line_end_before_start() -> None:
    with pytest.raises(ValidationError):
        CitedSpan(
            stdout_path=Path("/x"),
            line_start=10,
            line_end=5,
            content_sha256=_HASH64,
        )


def test_cited_span_accepts_single_line_span() -> None:
    """line_end == line_start is a legitimate single-line citation."""
    span = CitedSpan(stdout_path=Path("/x"), line_start=10, line_end=10, content_sha256=_HASH64)
    assert span.line_start == span.line_end == 10


# ---------------------------------------------------------------------------
# Observation invariants
# ---------------------------------------------------------------------------


def test_observation_rejects_empty_cited_spans() -> None:
    with pytest.raises(ValidationError):
        Observation(id="O-1", summary="x", cited_spans=(), audit_ids=("a",))


def test_observation_rejects_empty_audit_ids() -> None:
    with pytest.raises(ValidationError):
        Observation(id="O-1", summary="x", cited_spans=(_cited_span(),), audit_ids=())


# ---------------------------------------------------------------------------
# Finding lifecycle
# ---------------------------------------------------------------------------


def test_finding_defaults_to_status_draft() -> None:
    finding = Finding(id="F-001", observation_id="O-007", interpretation_id="I-007")
    assert finding.status == FindingStatus.DRAFT


# ---------------------------------------------------------------------------
# ToolResponse / ResponseEnvelope
# ---------------------------------------------------------------------------


class _Sample(BaseModel):
    name: str


def test_tool_response_generic_payload_resolves() -> None:
    """ToolResponse[T] resolves the payload type and round-trips."""
    envelope: ToolResponse[_Sample] = ToolResponse(
        success=True,
        data=_Sample(name="alice"),
        audit_id="sift-aj-20260613-007",
        examiner="aj",
        data_provenance=_data_provenance(),
    )
    re_parsed = ToolResponse[_Sample].model_validate_json(envelope.model_dump_json())
    assert re_parsed.data is not None
    assert re_parsed.data.name == "alice"


def test_tool_response_success_implies_data() -> None:
    """success=True with data=None is a contract violation."""
    with pytest.raises(ValidationError):
        ToolResponse[_Sample](
            success=True,
            data=None,
            audit_id="sift-aj-20260613-007",
            examiner="aj",
            data_provenance=_data_provenance(),
        )


def test_response_envelope_is_tool_response_alias() -> None:
    """architecture.md uses ResponseEnvelope; code uses ToolResponse; both refer to one model."""
    assert ResponseEnvelope is ToolResponse


# ---------------------------------------------------------------------------
# Enum stability + ordering
# ---------------------------------------------------------------------------


def test_string_enums_are_stable_strings() -> None:
    """JSON round-trip must preserve enum values as readable strings (not ints)."""
    for member in (
        Confidence.HIGH,
        EvidenceType.DISK_IMAGE,
        HypothesisStatus.ACTIVE,
        SpecialistName.MEMORY,
        ReportSection.FINDINGS,
        FindingStatus.DRAFT,
        CriticVerdict.AGREE,
    ):
        assert isinstance(member.value, str)
        assert member.value == str(member.value)


def test_confidence_is_orderable() -> None:
    """HIGH > MEDIUM > LOW lets the agent rank competing interpretations."""
    assert Confidence.HIGH > Confidence.MEDIUM > Confidence.LOW
    assert Confidence.LOW < Confidence.HIGH
    assert sorted([Confidence.HIGH, Confidence.LOW, Confidence.MEDIUM]) == [
        Confidence.LOW,
        Confidence.MEDIUM,
        Confidence.HIGH,
    ]


# ---------------------------------------------------------------------------
# Audit + pivot + interpretation smoke
# ---------------------------------------------------------------------------


def test_audit_entry_roundtrips() -> None:
    entry = AuditEntry(
        ts=datetime(2026, 6, 13, 14, 27, 3, tzinfo=UTC),
        audit_id="sift-aj-20260613-007",
        tool="vol_pslist",
        params={"image": "/evidence/mem.raw"},
        result_summary={"row_count": 142},
        result_sha256=_HASH64,
        stdout_path=Path("/var/lib/silentwitness/stdout/sift-aj-20260613-007.json"),
        elapsed_ms=120.5,
        examiner="aj",
        model_used="anthropic:claude-opus-4-7",
        model_token_count={"prompt": 1200, "completion": 80},
    )
    re_parsed = AuditEntry.model_validate_json(entry.model_dump_json())
    assert re_parsed == entry


def test_interpretation_requires_non_empty_observation_ids() -> None:
    with pytest.raises(ValidationError):
        Interpretation(
            id="I-1",
            summary="x",
            confidence=Confidence.HIGH,
            observation_ids=(),
            rationale="r",
        )


@pytest.mark.parametrize(
    "op",
    [operator.lt, operator.le, operator.gt, operator.ge],
)
def test_confidence_raises_typeerror_on_str_comparison(
    op: Callable[[object, object], bool],
) -> None:
    """Regression for PR-92 review C1: StrEnum's inherited str ordering used to
    silently fire when ``Confidence`` was compared to ``str``. Parametrising
    across all four ordering operators locks every dunder against drift."""
    with pytest.raises(TypeError):
        op(Confidence.HIGH, "ZZZ")
    with pytest.raises(TypeError):
        op(Confidence.LOW, "AAA")


def test_finding_validate_assignment_rejects_bogus_status() -> None:
    """Regression for PR-92 review C5: validate_assignment=True enforces the
    enum on runtime mutation, not just construction."""
    finding = Finding(id="F-001", observation_id="O-007", interpretation_id="I-007")
    with pytest.raises(ValidationError):
        finding.status = "BOGUS_STATUS"  # type: ignore[assignment]


def test_finding_accepts_each_status_transition() -> None:
    """The status field cycles DRAFT → REVIEWED → FINAL → ARCHIVED. Each
    target is a legitimate enum member, so assignment should succeed."""
    finding = Finding(id="F-001", observation_id="O-007", interpretation_id="I-007")
    for target in (
        FindingStatus.REVIEWED,
        FindingStatus.FINAL,
        FindingStatus.ARCHIVED,
        FindingStatus.DRAFT,
    ):
        finding.status = target
        assert finding.status is target


def test_observation_rejects_empty_string_audit_id_element() -> None:
    """Regression for PR-92 review HIGH #4: an empty-string entry inside the
    tuple used to pass the non-empty validator. Now rejected loudly."""
    with pytest.raises(ValidationError):
        Observation(
            id="O-1",
            summary="x",
            cited_spans=(_cited_span(),),
            audit_ids=("",),
        )
    with pytest.raises(ValidationError):
        Observation(
            id="O-1",
            summary="x",
            cited_spans=(_cited_span(),),
            audit_ids=("  ",),
        )


def test_tool_response_failure_forbids_data() -> None:
    """Regression for PR-92 review HIGH #6: success=False + data=Sample()
    is a contract violation just like success=True + data=None."""
    with pytest.raises(ValidationError):
        ToolResponse[_Sample](
            success=False,
            data=_Sample(name="leaks"),
            audit_id="sift-aj-20260613-007",
            examiner="aj",
            data_provenance=_data_provenance(),
        )


def test_sha256hex_lowercases_uppercase_input() -> None:
    """The Sha256Hex BeforeValidator must canonicalise to lowercase before
    the StringConstraints pattern check fires."""
    span = CitedSpan(
        stdout_path=Path("/x"),
        line_start=1,
        line_end=1,
        content_sha256="A" * 64,
    )
    assert span.content_sha256 == "a" * 64


def test_sha256hex_rejects_non_hex_characters() -> None:
    """A 64-char non-hex string (e.g. 64 'g' chars) must fail validation."""
    with pytest.raises(ValidationError):
        CitedSpan(
            stdout_path=Path("/x"),
            line_start=1,
            line_end=1,
            content_sha256="g" * 64,
        )


def test_sha256hex_rejects_wrong_length() -> None:
    """A short hex string (e.g. 32 chars) must fail the pattern length anchor."""
    with pytest.raises(ValidationError):
        CitedSpan(
            stdout_path=Path("/x"),
            line_start=1,
            line_end=1,
            content_sha256="a" * 32,
        )


def test_sha256hex_rejects_non_string_input() -> None:
    """A non-string value (int, bytes, None) must fail loudly at the type
    layer. _lower_if_str is identity for non-strings; StringConstraints then
    rejects the wrong type."""
    for bad in (12345, b"a" * 64, None):
        with pytest.raises(ValidationError):
            CitedSpan(
                stdout_path=Path("/x"),
                line_start=1,
                line_end=1,
                content_sha256=bad,  # type: ignore[arg-type]
            )


def test_data_provenance_cmd_argv_roundtrip_preserves_tuple() -> None:
    """The cmd_argv field is intentionally typed as tuple (not list) so
    frozen=True propagates immutability. JSON round-trip must preserve
    tuple-ness — otherwise the tightening is lost in transit."""
    prov = _data_provenance()
    re_parsed = DataProvenance.model_validate_json(prov.model_dump_json())
    assert isinstance(
        re_parsed.cmd_argv, tuple
    ), f"cmd_argv must round-trip as tuple, got {type(re_parsed.cmd_argv).__name__}"


def test_finding_validate_assignment_rejects_unknown_attribute() -> None:
    """validate_assignment + extra='forbid' must reject runtime setattr to a
    field that wasn't declared. Otherwise the assignment-time enforcement is
    asymmetric with construction-time."""
    finding = Finding(id="F-001", observation_id="O-007", interpretation_id="I-007")
    with pytest.raises(ValidationError):
        finding.bogus_new_field = "leaked"  # type: ignore[attr-defined]


def test_pivot_roundtrips() -> None:
    pivot = Pivot(
        from_hypothesis_id="H-001",
        to_hypothesis_id="H-002",
        reason="memory shows no malfind hits; pivoting to disk",
        at=datetime(2026, 6, 13, 14, 30, tzinfo=UTC),
    )
    re_parsed = Pivot.model_validate_json(pivot.model_dump_json())
    assert re_parsed == pivot
