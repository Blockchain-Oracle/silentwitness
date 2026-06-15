"""``record_narrative`` tool body (architecture §4.2 + §5.3 + §5.4).

Refines the architecture's ``(section, text)`` input with four
structurally required fields: ``initial_hypothesis`` (the WHY),
``attack_chain`` (dispatched observations), ``pivots`` (P-NNN refs),
and ``gaps`` (epistemic-honesty floor when the chain is deep).

The conditional gaps rule (>3 chain steps → ≥1 non-empty gap) defends
against fluent-but-unanchored prose. Section gating: RECOMMENDATIONS
and APPENDIX_AUDIT reject as SECTION_NOT_AGENT_WRITABLE — reserved
for the examiner / renderer.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field, model_validator

from silentwitness_common.atomic_io import append_jsonl_line
from silentwitness_common.types import AuditEntry, ReportSection, ToolResponse
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings._narrative_store import (
    NarrativeStoreError,
    allocate_narrative_id,
    existing_observation_ids,
    existing_pivot_ids,
)
from silentwitness_mcp.findings._scrub import scrub_line_terminators
from silentwitness_mcp.findings._wrap import content_after_wrap
from silentwitness_mcp.verification.sanitizer import (
    StripEvent,
    StripEventWriter,
    sanitize,
)


class NarrativeRejectReason(StrEnum):
    """Closed rejection-code set — re-declared rather than aliased."""

    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    MISSING_GAPS = "MISSING_GAPS"
    SECTION_NOT_AGENT_WRITABLE = "SECTION_NOT_AGENT_WRITABLE"
    OBSERVATION_NOT_FOUND = "OBSERVATION_NOT_FOUND"
    PIVOT_NOT_FOUND = "PIVOT_NOT_FOUND"
    AUDIT_STORE_CORRUPTED = "AUDIT_STORE_CORRUPTED"
    AUDIT_STORE_UNWRITABLE = "AUDIT_STORE_UNWRITABLE"
    PIPELINE_INTERNAL_ERROR = "PIPELINE_INTERNAL_ERROR"


_RESULT_CONFIG = ConfigDict(frozen=True, extra="forbid")
_OBSERVATION_ID_PATTERN: Final = re.compile(r"^O-\d{3,}$")
_PIVOT_ID_PATTERN: Final = re.compile(r"^P-\d{3,}$")
_INITIAL_HYPOTHESIS_MIN: Final = 20
_ATTACK_CHAIN_GAPS_THRESHOLD: Final = 3
# Sections architecture §5.4 reserves for the examiner / renderer.
_NON_AGENT_WRITABLE: Final[frozenset[ReportSection]] = frozenset(
    {ReportSection.RECOMMENDATIONS, ReportSection.APPENDIX_AUDIT}
)


class AttackChainStep(BaseModel):
    """One link in the attack-chain narrative — references an observation
    and (optionally) the interpretation that built on it."""

    model_config = _RESULT_CONFIG

    observation_id: str = Field(min_length=1)
    interpretation_id: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _observation_id_shape(self) -> AttackChainStep:
        if _OBSERVATION_ID_PATTERN.match(self.observation_id) is None:
            raise ValueError(f"observation_id must match O-NNN; got {self.observation_id!r}")
        return self


class NarrativeInput(BaseModel):
    """Agent-emitted narrative draft. Constructor enforces shape;
    conditional gaps rule runs post-sanitize."""

    model_config = _RESULT_CONFIG

    section: ReportSection
    text: str = Field(min_length=1)
    initial_hypothesis: str = Field(min_length=_INITIAL_HYPOTHESIS_MIN)
    attack_chain: tuple[AttackChainStep, ...] = Field(min_length=1)
    pivots: tuple[str, ...] = Field(default_factory=tuple)
    gaps: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _pivot_id_shapes(self) -> NarrativeInput:
        for pid in self.pivots:
            if _PIVOT_ID_PATTERN.match(pid) is None:
                raise ValueError(f"pivot id must match P-NNN; got {pid!r}")
        return self


class NarrativeResult(BaseModel):
    """Result payload. Discriminator pins success/narrative_id/reason
    exclusivity — same shape as ObservationResult / PivotResult."""

    model_config = _RESULT_CONFIG

    success: bool
    narrative_id: str | None = None
    reason: NarrativeRejectReason | None = None
    context: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_tag(self) -> NarrativeResult:
        if self.success:
            if self.narrative_id is None:
                raise ValueError("success=True requires narrative_id")
            if self.reason is not None:
                raise ValueError("success=True must not carry reason")
        else:
            if self.reason is None:
                raise ValueError("success=False requires reason")
            if self.narrative_id is not None:
                raise ValueError("success=False must not carry narrative_id")
        return self


class _JsonlStripWriter(StripEventWriter):
    def __init__(self, sanitizer_log: Path) -> None:
        sanitizer_log.parent.mkdir(parents=True, exist_ok=True)
        sanitizer_log.touch(exist_ok=True)
        self._path = sanitizer_log

    def emit(self, event: StripEvent) -> None:
        append_jsonl_line(self._path, event.model_dump_json())


def record_narrative(
    payload: NarrativeInput,
    *,
    case_dir: Path,
    audit_logger: AuditLogger,
    model_used: str,
) -> ToolResponse[NarrativeResult]:
    """Pipeline: section gating → sanitize fields → post-sanitize
    emptiness + gaps floor → observation + pivot existence → allocate
    N-NNN → append findings.json → audit row in finally{}."""
    sanitizer_log = case_dir / "audit" / "sanitizer.jsonl"
    findings_log = case_dir / "audit" / "findings.jsonl"
    hypothesis_log = case_dir / "audit" / "hypothesis.jsonl"
    start = time.monotonic()
    pre_audit_id = audit_logger.next_audit_id()
    result: NarrativeResult | None = None
    try:
        result = _run_pipeline(
            payload,
            case_dir=case_dir,
            sanitizer_log=sanitizer_log,
            hypothesis_log=hypothesis_log,
            pre_audit_id=pre_audit_id,
        )
    except (json.JSONDecodeError, UnicodeDecodeError, NarrativeStoreError) as exc:
        result = NarrativeResult(
            success=False,
            reason=NarrativeRejectReason.AUDIT_STORE_CORRUPTED,
            context={"stage": "findings_read", "error_type": type(exc).__name__},
        )
    except OSError as exc:
        result = NarrativeResult(
            success=False,
            reason=NarrativeRejectReason.AUDIT_STORE_UNWRITABLE,
            context={"stage": "findings_write", "error_type": type(exc).__name__},
        )
    except Exception as exc:
        result = NarrativeResult(
            success=False,
            reason=NarrativeRejectReason.PIPELINE_INTERNAL_ERROR,
            context={"stage": "pipeline", "error_type": type(exc).__name__},
        )
    finally:
        if result is None:  # pragma: no cover — defensive
            result = NarrativeResult(
                success=False,
                reason=NarrativeRejectReason.PIPELINE_INTERNAL_ERROR,
                context={"stage": "pipeline", "error_type": "unknown"},
            )
        try:
            _write_audit_row(
                result,
                payload=payload,
                findings_log=findings_log,
                case_dir=case_dir,
                audit_id=pre_audit_id,
                examiner=audit_logger.examiner,
                start=start,
                model_used=model_used,
            )
        except Exception as audit_exc:
            # Preserve narrative_id on success path: findings.json was
            # written, so silently losing N-NNN would let the agent
            # retry and duplicate-allocate.
            preserved = {
                "stage": "audit_write",
                "error_type": type(audit_exc).__name__,
                "audit_write_failed": True,
                "original_reason": (result.reason.value if result.reason else None),
                "original_context": dict(result.context),
                "original_narrative_id": result.narrative_id,
                "original_success": result.success,
            }
            result = NarrativeResult(
                success=False,
                reason=NarrativeRejectReason.AUDIT_STORE_UNWRITABLE,
                context=preserved,
            )
    return _wrap_envelope(result, audit_id=pre_audit_id, examiner=audit_logger.examiner)


def _run_pipeline(
    payload: NarrativeInput,
    *,
    case_dir: Path,
    sanitizer_log: Path,
    hypothesis_log: Path,
    pre_audit_id: str,
) -> NarrativeResult:
    # Section gating runs first — agent-writable check is cheap and a
    # rejection here saves sanitize cost.
    if payload.section in _NON_AGENT_WRITABLE:
        return NarrativeResult(
            success=False,
            reason=NarrativeRejectReason.SECTION_NOT_AGENT_WRITABLE,
            context={"section": payload.section.value},
        )

    writer = _JsonlStripWriter(sanitizer_log)
    s_text = sanitize(payload.text, pre_audit_id, audit_writer=writer).wrapped_text
    s_hyp = sanitize(payload.initial_hypothesis, pre_audit_id, audit_writer=writer).wrapped_text
    s_gaps = tuple(
        sanitize(g, pre_audit_id, audit_writer=writer).wrapped_text for g in payload.gaps
    )
    s_chain = tuple(
        AttackChainStep(
            observation_id=step.observation_id,
            interpretation_id=step.interpretation_id,
            note=(
                sanitize(step.note, pre_audit_id, audit_writer=writer).wrapped_text
                if step.note is not None
                else None
            ),
        )
        for step in payload.attack_chain
    )

    if not content_after_wrap(s_hyp).strip():
        return NarrativeResult(
            success=False,
            reason=NarrativeRejectReason.MISSING_REQUIRED_FIELD,
            context={"field": "initial_hypothesis"},
        )

    # Conditional gaps floor — count gaps with non-empty post-sanitize
    # content; an entry that sanitizes to wrap-markers-only would
    # otherwise degrade the floor to a tuple-length check.
    non_empty_gaps = [g for g in s_gaps if content_after_wrap(g).strip()]
    if len(s_chain) > _ATTACK_CHAIN_GAPS_THRESHOLD and not non_empty_gaps:
        return NarrativeResult(
            success=False,
            reason=NarrativeRejectReason.MISSING_GAPS,
            context={
                "field": "gaps",
                "attack_chain_length": len(s_chain),
                "threshold": _ATTACK_CHAIN_GAPS_THRESHOLD,
            },
        )

    # Validate every cited observation exists in findings.json.
    obs_ids = existing_observation_ids(case_dir)
    for step in s_chain:
        if step.observation_id not in obs_ids:
            return NarrativeResult(
                success=False,
                reason=NarrativeRejectReason.OBSERVATION_NOT_FOUND,
                context={"observation_id": step.observation_id},
            )

    # Validate every cited pivot exists in hypothesis.jsonl.
    if payload.pivots:
        pivot_ids = existing_pivot_ids(hypothesis_log)
        for pid in payload.pivots:
            if pid not in pivot_ids:
                return NarrativeResult(
                    success=False,
                    reason=NarrativeRejectReason.PIVOT_NOT_FOUND,
                    context={"pivot_id": pid},
                )

    # Strip the sanitizer's `[UNTRUSTED EVIDENCE BEGIN/END]` wrap before persisting.
    # Same task #20 invariant as record_interpretation: gates above run on the WRAPPED
    # form (injection defense intact); only the on-disk form is unwrapped so the
    # markers do not leak into findings.json.
    clean_chain = [
        AttackChainStep(
            observation_id=step.observation_id,
            interpretation_id=step.interpretation_id,
            note=content_after_wrap(step.note) if step.note is not None else None,
        )
        for step in s_chain
    ]
    narrative_record = {
        "section": payload.section.value,
        "text": content_after_wrap(s_text),
        "initial_hypothesis": content_after_wrap(s_hyp),
        "attack_chain": [step.model_dump(mode="json") for step in clean_chain],
        "pivots": list(payload.pivots),
        "gaps": [content_after_wrap(g) for g in s_gaps],
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    nid = allocate_narrative_id(case_dir, narrative_record)
    return NarrativeResult(success=True, narrative_id=nid)


def _write_audit_row(
    result: NarrativeResult,
    *,
    payload: NarrativeInput,
    findings_log: Path,
    case_dir: Path,
    audit_id: str,
    examiner: str,
    start: float,
    model_used: str,
) -> None:
    """Canonical :class:`AuditEntry` (§4.4). U+2028 / U+2029 are scrubbed
    from agent-controlled text so a line-terminator attack can't make
    append_jsonl_line raise inside this function."""
    elapsed_ms = (time.monotonic() - start) * 1000.0
    summary_json = result.model_dump_json()
    artefact_path = (
        case_dir / "findings.json" if result.success else case_dir / "audit" / "findings.jsonl"
    )
    # Pivots are regex-pinned but scrub keeps the row format symmetric
    # with the other agent-controlled string fields.
    scrubbed_params: dict[str, object] = {
        "section": payload.section.value,
        "text": scrub_line_terminators(payload.text),
        "initial_hypothesis": scrub_line_terminators(payload.initial_hypothesis),
        "attack_chain": [step.model_dump(mode="json") for step in payload.attack_chain],
        "pivots": [scrub_line_terminators(p) for p in payload.pivots],
        "gaps": [scrub_line_terminators(g) for g in payload.gaps],
    }
    entry = AuditEntry(
        ts=datetime.now(UTC),
        audit_id=audit_id,
        tool="record_narrative",
        params=scrubbed_params,
        result_summary=result.model_dump(mode="json"),
        result_sha256=hashlib.sha256(summary_json.encode("utf-8")).hexdigest(),
        stdout_path=artefact_path,
        elapsed_ms=elapsed_ms,
        examiner=examiner,
        model_used=model_used,
        model_token_count={},
    )
    findings_log.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl_line(findings_log, entry.model_dump_json())


def _wrap_envelope(
    result: NarrativeResult, *, audit_id: str, examiner: str
) -> ToolResponse[NarrativeResult]:
    """Transport-layer ``success`` is ALWAYS True; gate verdict rides
    inside ``data``."""
    from silentwitness_mcp.envelope import make_empty_provenance

    return ToolResponse[NarrativeResult](
        success=True,
        data=result,
        audit_id=audit_id,
        examiner=examiner,
        advisories=() if result.success else (str(result.reason),),
        data_provenance=make_empty_provenance("record_narrative"),
    )


__all__ = [
    "AttackChainStep",
    "NarrativeInput",
    "NarrativeRejectReason",
    "NarrativeResult",
    "record_narrative",
]
