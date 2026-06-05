"""``record_interpretation`` tool body (architecture §4.2, §5.5, §8.1 step 23).

Pipeline: sanitize text + justification + falsification → validate
observation_id exists → post-sanitize required-field non-emptiness →
conditional confidence-vs-justification length floor (HIGH ≥ 50,
MEDIUM ≥ 30) → allocate ``I-NNN`` under the observation in
findings.json → audit row to ``audit/findings.jsonl`` REGARDLESS of
accept/reject (rejections are evidence too — architecture §4.4).

The story spec EXTENDS the architecture's minimal
``(observation_id, text, confidence)`` input with ``justification``
and ``what_would_change_this_confidence`` — both structurally required
by the critic pipeline (Epic 10) and the report's confidence-banded
shape (Epic 11). The conditional length floor is the architectural
defense against overclaim drift.
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
from silentwitness_common.types import AuditEntry, Confidence, ToolResponse
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings._interpretation_store import allocate_interpretation_id
from silentwitness_mcp.findings._scrub import scrub_line_terminators
from silentwitness_mcp.verification.sanitizer import (
    StripEvent,
    StripEventWriter,
    sanitize,
)


class InterpretationRejectReason(StrEnum):
    """Closed rejection-code set; re-declared rather than aliased upstream
    so adding a new failure mode is an explicit decision."""

    OBSERVATION_NOT_FOUND = "OBSERVATION_NOT_FOUND"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    JUSTIFICATION_TOO_SHORT_FOR_CONFIDENCE = "JUSTIFICATION_TOO_SHORT_FOR_CONFIDENCE"
    INVALID_CONFIDENCE = "INVALID_CONFIDENCE"
    FINDINGS_STORE_CORRUPTED = "FINDINGS_STORE_CORRUPTED"
    FINDINGS_STORE_UNWRITABLE = "FINDINGS_STORE_UNWRITABLE"
    PIPELINE_INTERNAL_ERROR = "PIPELINE_INTERNAL_ERROR"


_RESULT_CONFIG = ConfigDict(frozen=True, extra="forbid")
_OBSERVATION_ID_PATTERN: Final = re.compile(r"^O-\d+$")
_HIGH_MIN_JUSTIFICATION: Final = 50
_MEDIUM_MIN_JUSTIFICATION: Final = 30
_WRAP_BEGIN: Final = "[UNTRUSTED EVIDENCE BEGIN]\n"
_WRAP_END: Final = "\n[UNTRUSTED EVIDENCE END]"
_FALSIFICATION_FIELD: Final = "what_would_change_this_confidence"


class InterpretationInput(BaseModel):
    """Agent-emitted interpretation. The ``min_length=1`` floors here are
    the *constructor* gate; the semantic floor (HIGH 50 / MEDIUM 30)
    runs post-sanitize because sanitization may shrink the strings."""

    model_config = _RESULT_CONFIG

    observation_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    confidence: Confidence
    justification: str = Field(min_length=1)
    what_would_change_this_confidence: str = Field(min_length=1)

    @model_validator(mode="after")
    def _observation_id_shape(self) -> InterpretationInput:
        if _OBSERVATION_ID_PATTERN.match(self.observation_id) is None:
            raise ValueError(f"observation_id must match O-NNN; got {self.observation_id!r}")
        return self


class InterpretationResult(BaseModel):
    """Result payload. Discriminator pins the success/reason exclusivity
    invariant — same shape as ObservationResult."""

    model_config = _RESULT_CONFIG

    success: bool
    interpretation_id: str | None = None
    reason: InterpretationRejectReason | None = None
    context: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_tag(self) -> InterpretationResult:
        if self.success:
            if self.interpretation_id is None:
                raise ValueError("success=True requires interpretation_id")
            if self.reason is not None:
                raise ValueError("success=True must not carry reason")
        else:
            if self.reason is None:
                raise ValueError("success=False requires reason")
            if self.interpretation_id is not None:
                raise ValueError("success=False must not carry interpretation_id")
        return self


class _JsonlStripWriter(StripEventWriter):
    def __init__(self, sanitizer_log: Path) -> None:
        sanitizer_log.parent.mkdir(parents=True, exist_ok=True)
        sanitizer_log.touch(exist_ok=True)
        self._path = sanitizer_log

    def emit(self, event: StripEvent) -> None:
        append_jsonl_line(self._path, event.model_dump_json())


def _required_justification_length(confidence: Confidence) -> int:
    """Floor scales with claim strength — overclaim defense."""
    if confidence is Confidence.HIGH:
        return _HIGH_MIN_JUSTIFICATION
    if confidence is Confidence.MEDIUM:
        return _MEDIUM_MIN_JUSTIFICATION
    return 0


def record_interpretation(
    payload: InterpretationInput,
    *,
    case_dir: Path,
    audit_logger: AuditLogger,
    model_used: str,
) -> ToolResponse[InterpretationResult]:
    """Pipeline: sanitize → validate observation exists → required-field
    floors → confidence-vs-justification floor → allocate ``I-NNN`` →
    audit row.

    The audit row lands in a ``finally`` so a corrupted findings.json or
    a disk-full mid-write still produces an audit trail. The envelope's
    transport-layer ``success`` is ALWAYS True; gate verdicts ride
    inside ``data`` per architecture §4.3."""
    sanitizer_log = case_dir / "audit" / "sanitizer.jsonl"
    findings_log = case_dir / "audit" / "findings.jsonl"
    start = time.monotonic()
    pre_audit_id = audit_logger.next_audit_id()
    result: InterpretationResult | None = None
    try:
        result = _run_pipeline(
            payload,
            case_dir=case_dir,
            sanitizer_log=sanitizer_log,
            pre_audit_id=pre_audit_id,
        )
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        result = InterpretationResult(
            success=False,
            reason=InterpretationRejectReason.FINDINGS_STORE_CORRUPTED,
            context={"stage": "findings_read", "error_type": type(exc).__name__},
        )
    except OSError as exc:
        result = InterpretationResult(
            success=False,
            reason=InterpretationRejectReason.FINDINGS_STORE_UNWRITABLE,
            context={"stage": "findings_write", "error_type": type(exc).__name__},
        )
    except Exception as exc:
        result = InterpretationResult(
            success=False,
            reason=InterpretationRejectReason.PIPELINE_INTERNAL_ERROR,
            context={"stage": "pipeline", "error_type": type(exc).__name__},
        )
    finally:
        if result is None:  # pragma: no cover — defensive
            result = InterpretationResult(
                success=False,
                reason=InterpretationRejectReason.PIPELINE_INTERNAL_ERROR,
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
            result = InterpretationResult(
                success=False,
                reason=InterpretationRejectReason.FINDINGS_STORE_UNWRITABLE,
                context={
                    "stage": "audit_write",
                    "error_type": type(audit_exc).__name__,
                    "audit_write_failed": True,
                },
            )
    return _wrap_envelope(result, audit_id=pre_audit_id, examiner=audit_logger.examiner)


def _run_pipeline(
    payload: InterpretationInput,
    *,
    case_dir: Path,
    sanitizer_log: Path,
    pre_audit_id: str,
) -> InterpretationResult:
    writer = _JsonlStripWriter(sanitizer_log)
    s_text = sanitize(payload.text, pre_audit_id, audit_writer=writer).wrapped_text
    s_just = sanitize(payload.justification, pre_audit_id, audit_writer=writer).wrapped_text
    s_fals = sanitize(
        payload.what_would_change_this_confidence, pre_audit_id, audit_writer=writer
    ).wrapped_text

    fields = (
        ("text", payload.text, s_text),
        ("justification", payload.justification, s_just),
        (_FALSIFICATION_FIELD, payload.what_would_change_this_confidence, s_fals),
    )
    for field_name, raw, sanitized in fields:
        if not _content_after_wrap(sanitized).strip():
            return InterpretationResult(
                success=False,
                reason=InterpretationRejectReason.MISSING_REQUIRED_FIELD,
                context={"field": field_name, "pre_sanitize_length": len(raw)},
            )

    floor = _required_justification_length(payload.confidence)
    j_content = _content_after_wrap(s_just).strip()
    if len(j_content) < floor:
        return InterpretationResult(
            success=False,
            reason=InterpretationRejectReason.JUSTIFICATION_TOO_SHORT_FOR_CONFIDENCE,
            context={
                "confidence": payload.confidence.value,
                "required_min_length": floor,
                "actual_length": len(j_content),
            },
        )

    interpretation_record = {
        "text": s_text,
        "confidence": payload.confidence.value,
        "justification": s_just,
        _FALSIFICATION_FIELD: s_fals,
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    iid = allocate_interpretation_id(case_dir, payload.observation_id, interpretation_record)
    if iid is None:
        return InterpretationResult(
            success=False,
            reason=InterpretationRejectReason.OBSERVATION_NOT_FOUND,
            context={"observation_id": payload.observation_id},
        )
    return InterpretationResult(success=True, interpretation_id=iid)


def _content_after_wrap(sanitized: str) -> str:
    """Strip the sanitizer's outer envelope so length / emptiness checks
    operate on the content, not the wrap markers."""
    if sanitized.startswith(_WRAP_BEGIN) and sanitized.endswith(_WRAP_END):
        return sanitized[len(_WRAP_BEGIN) : -len(_WRAP_END)]
    return sanitized


def _write_audit_row(
    result: InterpretationResult,
    *,
    payload: InterpretationInput,
    findings_log: Path,
    case_dir: Path,
    audit_id: str,
    examiner: str,
    start: float,
    model_used: str,
) -> None:
    """Canonical :class:`AuditEntry` (architecture §4.4). U+2028/U+2029
    are scrubbed from agent-controlled text before serialization so a
    line-terminator attack can't make append_jsonl_line raise inside
    this function and erase the row."""
    elapsed_ms = (time.monotonic() - start) * 1000.0
    summary_json = result.model_dump_json()
    artefact_path = (
        case_dir / "findings.json" if result.success else case_dir / "audit" / "findings.jsonl"
    )
    scrubbed_params: dict[str, object] = {
        "observation_id": payload.observation_id,
        "text": scrub_line_terminators(payload.text),
        "confidence": payload.confidence.value,
        "justification": scrub_line_terminators(payload.justification),
        _FALSIFICATION_FIELD: scrub_line_terminators(payload.what_would_change_this_confidence),
    }
    entry = AuditEntry(
        ts=datetime.now(UTC),
        audit_id=audit_id,
        tool="record_interpretation",
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
    result: InterpretationResult, *, audit_id: str, examiner: str
) -> ToolResponse[InterpretationResult]:
    """``envelope.success`` is the transport-layer flag — always True;
    the inner ``data.success`` carries the gate verdict."""
    from silentwitness_mcp.envelope import make_empty_provenance

    return ToolResponse[InterpretationResult](
        success=True,
        data=result,
        audit_id=audit_id,
        examiner=examiner,
        advisories=() if result.success else (str(result.reason),),
        data_provenance=make_empty_provenance("record_interpretation"),
    )


__all__ = [
    "InterpretationInput",
    "InterpretationRejectReason",
    "InterpretationResult",
    "record_interpretation",
]
