"""BDD-grade tests for the MCP tool response envelope (architecture §4.3).

The envelope's source model lives in :mod:`silentwitness_common.types`
(to preserve package dependency direction — the agent doesn't depend on
``silentwitness_mcp``). This module exercises the
:mod:`silentwitness_mcp.envelope` re-export surface so the MCP-server
side gets first-class test coverage independent of
``tests/unit/test_common_types.py``.

Coverage targets:
* every BDD criterion in ``docs/stories/story-response-envelope.md``
* the audit_id format validator added in this story
* the :func:`make_failure_envelope` factory
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from silentwitness_mcp.envelope import (
    Confidence,
    DataProvenance,
    ResponseEnvelope,
    ToolResponse,
    make_failure_envelope,
)

_AUDIT_ID = "sift-aj-20260613-007"
_EXAMINER = "aj"
_SHA = "a" * 64
_AUDIT_ID_RE = re.compile(r"^sift-[a-z0-9]+-\d{8}-\d+$")


class _SamplePayload(BaseModel):
    """Minimal Pydantic payload for TPayload parameterisation."""

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
# BDD: success path
# ---------------------------------------------------------------------------


def test_success_envelope_constructs_and_validates() -> None:
    """Given a successful tool call with typed payload P,
    When ToolResponse[P](success=True, data=payload, ...) is built,
    Then the envelope validates without error."""
    env = ToolResponse[_SamplePayload](
        success=True,
        data=_SamplePayload(pid=1, name="System"),
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        data_provenance=_provenance(),
    )
    assert env.success is True
    assert env.data is not None
    assert env.data.pid == 1


def test_success_envelope_round_trips_through_json() -> None:
    """model_dump_json() → model_validate_json() produces an equal envelope."""
    original = ToolResponse[_SamplePayload](
        success=True,
        data=_SamplePayload(pid=4, name="lsass.exe"),
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        data_provenance=_provenance(),
    )
    rendered = original.model_dump_json()
    restored = ToolResponse[_SamplePayload].model_validate_json(rendered)
    assert restored == original


# ---------------------------------------------------------------------------
# BDD: failure path
# ---------------------------------------------------------------------------


def test_failure_envelope_constructs_with_advisories() -> None:
    """A failure carries advisories explaining WHY and has data=None."""
    env = ToolResponse[_SamplePayload](
        success=False,
        data=None,
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        advisories=("MOUNT_NOT_RO_NOEXEC_NOSUID",),
        data_provenance=_provenance(),
    )
    assert env.success is False
    assert env.data is None
    assert env.advisories == ("MOUNT_NOT_RO_NOEXEC_NOSUID",)


def test_success_true_with_data_none_rejected() -> None:
    """The model_validator enforces: success=True ⇒ data not None."""
    with pytest.raises(ValidationError, match="non-None data"):
        ToolResponse[_SamplePayload](
            success=True,
            data=None,
            audit_id=_AUDIT_ID,
            examiner=_EXAMINER,
            data_provenance=_provenance(),
        )


def test_success_false_with_data_set_rejected() -> None:
    """The model_validator enforces: success=False ⇒ data is None."""
    with pytest.raises(ValidationError, match="data=None"):
        ToolResponse[_SamplePayload](
            success=False,
            data=_SamplePayload(pid=1, name="System"),
            audit_id=_AUDIT_ID,
            examiner=_EXAMINER,
            data_provenance=_provenance(),
        )


# ---------------------------------------------------------------------------
# BDD: required-field discipline
# ---------------------------------------------------------------------------


def test_missing_audit_id_rejected() -> None:
    with pytest.raises(ValidationError, match="audit_id"):
        ToolResponse[_SamplePayload](  # type: ignore[call-arg]
            success=False,
            data=None,
            examiner=_EXAMINER,
            data_provenance=_provenance(),
        )


def test_missing_examiner_rejected() -> None:
    with pytest.raises(ValidationError, match="examiner"):
        ToolResponse[_SamplePayload](  # type: ignore[call-arg]
            success=False,
            data=None,
            audit_id=_AUDIT_ID,
            data_provenance=_provenance(),
        )


def test_missing_data_provenance_rejected() -> None:
    """Every audit-log entry MUST carry provenance — even failures."""
    with pytest.raises(ValidationError, match="data_provenance"):
        ToolResponse[_SamplePayload](  # type: ignore[call-arg]
            success=False,
            data=None,
            audit_id=_AUDIT_ID,
            examiner=_EXAMINER,
        )


# ---------------------------------------------------------------------------
# BDD: audit_id format (new in this story)
# ---------------------------------------------------------------------------


def test_audit_id_format_validator_accepts_canonical() -> None:
    """sift-<slug>-<YYYYMMDD>-<NNN> — accepted."""
    for valid in (
        "sift-aj-20260613-001",
        "sift-aj-20260613-999",
        "sift-mallory-20260101-1234",  # widened seq
        "sift-abu-20251225-42",  # short slug + small seq
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
        "test-audit-id",  # wrong prefix
        "sift-AJ-20260613-001",  # uppercase examiner slug
        "sift-aj-2026-06-13-001",  # date with hyphens
        "sift-aj-20260613",  # missing seq
        "sift--20260613-001",  # empty examiner
        "sift-aj-20269999-001",  # invalid date (month 99)
        "",  # empty string
    ],
)
def test_audit_id_format_validator_rejects_non_canonical(bad_id: str) -> None:
    with pytest.raises(ValidationError):
        ToolResponse[_SamplePayload](
            success=False,
            data=None,
            audit_id=bad_id,
            examiner=_EXAMINER,
            data_provenance=_provenance(),
        )


# ---------------------------------------------------------------------------
# BDD: DataProvenance field shape
# ---------------------------------------------------------------------------


def test_data_provenance_carries_architecture_4_3_fields() -> None:
    """Architecture §4.3 mandates: tool, stdout_path, result_sha256,
    elapsed_ms, cmd_argv. Validates each is exposed + typed."""
    p = _provenance()
    assert p.tool == "vol_pslist"
    assert isinstance(p.stdout_path, Path)
    assert _AUDIT_ID_RE.match(p.stdout_path.stem)
    assert re.fullmatch(r"[a-f0-9]{64}", p.result_sha256)
    assert isinstance(p.elapsed_ms, float)
    assert isinstance(p.cmd_argv, tuple)
    assert p.cmd_argv[0].endswith("/vol")


def test_data_provenance_round_trips_path_to_string() -> None:
    """Path serialises to string in JSON; round-trips back to Path."""
    p = _provenance()
    rendered = p.model_dump_json()
    assert "/cases/case-01/blobs/" in rendered
    restored = DataProvenance.model_validate_json(rendered)
    assert isinstance(restored.stdout_path, Path)
    assert restored.stdout_path == p.stdout_path


# ---------------------------------------------------------------------------
# BDD: caveats / advisories / corroboration / discipline_reminder
# ---------------------------------------------------------------------------


def test_caveats_preserved_through_round_trip() -> None:
    """caveats carries per-tool methodology notes ('Shimcache proves
    PRESENCE not EXECUTION'). MUST round-trip via JSON."""
    env = ToolResponse[_SamplePayload](
        success=True,
        data=_SamplePayload(pid=1, name="System"),
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        caveats=("Shimcache proves PRESENCE not EXECUTION",),
        data_provenance=_provenance(),
    )
    restored = ToolResponse[_SamplePayload].model_validate_json(env.model_dump_json())
    assert restored.caveats == ("Shimcache proves PRESENCE not EXECUTION",)


def test_discipline_reminder_is_optional() -> None:
    """discipline_reminder is supplementary prompt-layer hint; None by default."""
    env = ToolResponse[_SamplePayload](
        success=True,
        data=_SamplePayload(pid=1, name="System"),
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        data_provenance=_provenance(),
    )
    assert env.discipline_reminder is None


# ---------------------------------------------------------------------------
# BDD: Confidence enum
# ---------------------------------------------------------------------------


def test_confidence_enum_renders_as_string_and_round_trips() -> None:
    """Confidence.HIGH serialises as 'HIGH' and parses back to the enum."""
    assert Confidence.HIGH.value == "HIGH"
    # JSON round-trip via a model carrying a Confidence field.

    class _Conf(BaseModel):
        c: Confidence

    rendered = _Conf(c=Confidence.HIGH).model_dump_json()
    assert '"HIGH"' in rendered
    assert _Conf.model_validate_json(rendered).c is Confidence.HIGH


# ---------------------------------------------------------------------------
# BDD: ResponseEnvelope alias
# ---------------------------------------------------------------------------


def test_response_envelope_is_tool_response_alias() -> None:
    """Architecture docs use ResponseEnvelope; code uses ToolResponse.
    Both must refer to ONE class."""
    assert ResponseEnvelope is ToolResponse


# ---------------------------------------------------------------------------
# BDD: make_failure_envelope factory
# ---------------------------------------------------------------------------


def test_make_failure_envelope_appends_reason_to_advisories() -> None:
    """The factory bundles the structured ``reason`` into advisories so
    downstream consumers find the code in one canonical field."""
    env = make_failure_envelope(
        _SamplePayload,
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        tool="vol_pslist",
        stdout_path=Path("/dev/null"),
        result_sha256=_SHA,
        elapsed_ms=0.0,
        cmd_argv=(),
        reason="MOUNT_NOT_RO_NOEXEC_NOSUID",
    )
    assert env.success is False
    assert env.data is None
    assert env.advisories[-1] == "MOUNT_NOT_RO_NOEXEC_NOSUID"


def test_make_failure_envelope_preserves_caller_advisories() -> None:
    """Pre-existing caller advisories are preserved; reason is appended."""
    env = make_failure_envelope(
        _SamplePayload,
        audit_id=_AUDIT_ID,
        examiner=_EXAMINER,
        tool="vol_pslist",
        stdout_path=Path("/dev/null"),
        result_sha256=_SHA,
        elapsed_ms=0.0,
        cmd_argv=(),
        reason="EVIDENCE_NOT_REGISTERED",
        advisories=("warm up step skipped",),
    )
    assert env.advisories == ("warm up step skipped", "EVIDENCE_NOT_REGISTERED")


def test_make_failure_envelope_rejects_invalid_audit_id() -> None:
    """The factory inherits the field validator — bad audit_id rejected."""
    with pytest.raises(ValidationError):
        make_failure_envelope(
            _SamplePayload,
            audit_id="not-a-real-audit-id",
            examiner=_EXAMINER,
            tool="vol_pslist",
            stdout_path=Path("/dev/null"),
            result_sha256=_SHA,
            elapsed_ms=0.0,
            cmd_argv=(),
            reason="MOUNT_NOT_RO_NOEXEC_NOSUID",
        )
