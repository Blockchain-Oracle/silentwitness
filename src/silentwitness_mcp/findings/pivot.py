"""``record_pivot`` tool body (architecture §4.2 + §5.3).

Pipeline: sanitize reason → post-sanitize emptiness check →
abandoning_evidence non-empty → from_hypothesis_id exists in
``hypothesis.jsonl`` (``to_hypothesis_id`` shape is constructor-enforced
by :class:`PivotInput`) → allocate ``P-NNN`` → append :class:`_PivotEvent`
to ``audit/hypothesis.jsonl`` → audit row to ``audit/findings.jsonl``
REGARDLESS of accept/reject (rejections are evidence — §4.4).

PRD §4 secondary metric: ``grep -c '"type":"pivot"' hypothesis.jsonl``.

This tool refines the architecture's
``(from_hypothesis_id, to_statement, reason)`` triple. The agent-side
recorder owns hypothesis allocation; the MCP tool only records the
transition. The child ``to_hypothesis_id`` may not exist yet — the
tool does NOT validate its existence. ``abandoning_evidence`` is
frozen to a tuple at parse time so a handler cannot mutate the input
between the pipeline pass and the audit-row pass.

Persistence note: ``_PivotEvent.reason`` is the **unwrapped** sanitized
content (task #20). The sanitizer's ``[UNTRUSTED EVIDENCE BEGIN/END]``
wrap is a hot-path LLM-prompt visibility seam — it is applied at
gate time and stripped before persistence so the markers do not leak
into ``hypothesis.jsonl``.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from silentwitness_common.atomic_io import append_jsonl_line
from silentwitness_common.types import AuditEntry, ToolResponse
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings._pivot_store import (
    HypothesisStoreError,
    existing_hypothesis_ids,
    max_pivot_seq,
)
from silentwitness_mcp.findings._scrub import scrub_line_terminators
from silentwitness_mcp.findings._wrap import content_after_wrap
from silentwitness_mcp.verification.sanitizer import (
    StripEvent,
    StripEventWriter,
    sanitize,
)


class PivotRejectReason(StrEnum):
    """Closed rejection-code set — re-declared rather than aliased so
    adding a new failure mode is an explicit decision."""

    HYPOTHESIS_NOT_FOUND = "HYPOTHESIS_NOT_FOUND"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    MISSING_ABANDONING_EVIDENCE = "MISSING_ABANDONING_EVIDENCE"
    AUDIT_STORE_CORRUPTED = "AUDIT_STORE_CORRUPTED"
    AUDIT_STORE_UNWRITABLE = "AUDIT_STORE_UNWRITABLE"
    PIPELINE_INTERNAL_ERROR = "PIPELINE_INTERNAL_ERROR"


_RESULT_CONFIG = ConfigDict(frozen=True, extra="forbid")
# Zero-padded 3-digit form matches the allocator output.
_HYPOTHESIS_ID_PATTERN: Final = re.compile(r"^H-\d{3,}$")
_HYPOTHESIS_JSONL: Final = "hypothesis.jsonl"


class PivotInput(BaseModel):
    """Agent-submitted pivot payload. ``abandoning_evidence`` is frozen
    to a tuple at parse-time so a handler cannot mutate the input list
    between the pipeline pass and the audit-row pass."""

    model_config = _RESULT_CONFIG

    from_hypothesis_id: str = Field(min_length=1)
    to_hypothesis_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    abandoning_evidence: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _hypothesis_id_shape(self) -> PivotInput:
        for label, value in (
            ("from_hypothesis_id", self.from_hypothesis_id),
            ("to_hypothesis_id", self.to_hypothesis_id),
        ):
            if _HYPOTHESIS_ID_PATTERN.match(value) is None:
                raise ValueError(f"{label} must match H-NNN; got {value!r}")
        return self


class PivotResult(BaseModel):
    model_config = _RESULT_CONFIG

    success: bool
    pivot_id: str | None = None
    reason: PivotRejectReason | None = None
    context: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_tag(self) -> PivotResult:
        if self.success:
            if self.pivot_id is None:
                raise ValueError("success=True requires pivot_id")
            if self.reason is not None:
                raise ValueError("success=True must not carry reason")
        else:
            if self.reason is None:
                raise ValueError("success=False requires reason")
            if self.pivot_id is not None:
                raise ValueError("success=False must not carry pivot_id")
        return self


class _PivotEvent(BaseModel):
    """Pivot-specific subset of the architecture §5.3 HypothesisEvent
    schema. ``type`` is narrowed to ``"pivot"`` — the other event types
    (form/confirm/abandon) are owned by the agent-side recorder.
    ``tokens_spent`` and ``steps_spent`` default to 0; the agent-side
    recorder populates them when it owns the call."""

    model_config = ConfigDict(extra="forbid")

    ts: datetime
    type: Literal["pivot"] = "pivot"
    hypothesis_id: str = Field(pattern=r"^H-\d{3,}$")
    pivot_id: str = Field(pattern=r"^P-\d{3,}$")
    to_hypothesis_id: str = Field(pattern=r"^H-\d{3,}$")
    reason: str = Field(min_length=1)
    related_audit_ids: tuple[str, ...]
    tokens_spent: int = Field(ge=0, default=0)
    steps_spent: int = Field(ge=0, default=0)


class _JsonlStripWriter(StripEventWriter):
    def __init__(self, sanitizer_log: Path) -> None:
        sanitizer_log.parent.mkdir(parents=True, exist_ok=True)
        sanitizer_log.touch(exist_ok=True)
        self._path = sanitizer_log

    def emit(self, event: StripEvent) -> None:
        append_jsonl_line(self._path, event.model_dump_json())


def _hypothesis_log(case_dir: Path) -> Path:
    return case_dir / "audit" / _HYPOTHESIS_JSONL


def record_pivot(
    payload: PivotInput,
    *,
    case_dir: Path,
    audit_logger: AuditLogger,
    model_used: str,
) -> ToolResponse[PivotResult]:
    """Pipeline (described in module docstring). Audit row lands in a
    ``finally`` so corruption / disk-full mid-write still produces an
    audit trail. Envelope's transport-layer ``success`` is ALWAYS True;
    gate verdicts ride inside ``data`` per architecture §4.3."""
    sanitizer_log = case_dir / "audit" / "sanitizer.jsonl"
    findings_log = case_dir / "audit" / "findings.jsonl"
    hypothesis_log = _hypothesis_log(case_dir)
    start = time.monotonic()
    pre_audit_id = audit_logger.next_audit_id()
    result: PivotResult | None = None
    try:
        result = _run_pipeline(payload, hypothesis_log, sanitizer_log, pre_audit_id)
    except (json.JSONDecodeError, UnicodeDecodeError, HypothesisStoreError) as exc:
        # Narrow to the read-path exceptions we explicitly raise so a
        # ValidationError or unrelated ValueError can't masquerade as a
        # hypothesis.jsonl corruption.
        result = PivotResult(
            success=False,
            reason=PivotRejectReason.AUDIT_STORE_CORRUPTED,
            context={"stage": "hypothesis_read", "error_type": type(exc).__name__},
        )
    except OSError as exc:
        result = PivotResult(
            success=False,
            reason=PivotRejectReason.AUDIT_STORE_UNWRITABLE,
            context={"stage": "hypothesis_write", "error_type": type(exc).__name__},
        )
    except Exception as exc:
        result = PivotResult(
            success=False,
            reason=PivotRejectReason.PIPELINE_INTERNAL_ERROR,
            context={"stage": "pipeline", "error_type": type(exc).__name__},
        )
    finally:
        if result is None:  # pragma: no cover — defensive
            result = PivotResult(
                success=False,
                reason=PivotRejectReason.PIPELINE_INTERNAL_ERROR,
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
            preserved = {
                "stage": "audit_write",
                "error_type": type(audit_exc).__name__,
                "audit_write_failed": True,
                "original_reason": (result.reason.value if result.reason else None),
                "original_context": dict(result.context),
            }
            result = PivotResult(
                success=False,
                reason=PivotRejectReason.AUDIT_STORE_UNWRITABLE,
                context=preserved,
            )
    return _wrap_envelope(result, audit_id=pre_audit_id, examiner=audit_logger.examiner)


def _run_pipeline(
    payload: PivotInput,
    hypothesis_log: Path,
    sanitizer_log: Path,
    pre_audit_id: str,
) -> PivotResult:
    writer = _JsonlStripWriter(sanitizer_log)
    s_reason = sanitize(payload.reason, pre_audit_id, audit_writer=writer).wrapped_text

    if not content_after_wrap(s_reason).strip():
        return PivotResult(
            success=False,
            reason=PivotRejectReason.MISSING_REQUIRED_FIELD,
            context={"field": "reason", "pre_sanitize_length": len(payload.reason)},
        )

    if not payload.abandoning_evidence:
        return PivotResult(
            success=False,
            reason=PivotRejectReason.MISSING_ABANDONING_EVIDENCE,
        )

    existing = existing_hypothesis_ids(hypothesis_log)
    if payload.from_hypothesis_id not in existing:
        return PivotResult(
            success=False,
            reason=PivotRejectReason.HYPOTHESIS_NOT_FOUND,
            context={"field": "from_hypothesis_id", "value": payload.from_hypothesis_id},
        )

    pivot_id = f"P-{max_pivot_seq(hypothesis_log) + 1:03d}"
    # Strip the sanitizer wrap before persisting (task #20). Gates above ran on the
    # wrapped form; on-disk form is unwrapped so markers don't leak into hypothesis.jsonl.
    event = _PivotEvent(
        ts=datetime.now(UTC),
        hypothesis_id=payload.from_hypothesis_id,
        pivot_id=pivot_id,
        to_hypothesis_id=payload.to_hypothesis_id,
        reason=content_after_wrap(s_reason),
        related_audit_ids=payload.abandoning_evidence,
    )
    hypothesis_log.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl_line(hypothesis_log, event.model_dump_json())
    return PivotResult(success=True, pivot_id=pivot_id)


def _write_audit_row(
    result: PivotResult,
    *,
    payload: PivotInput,
    findings_log: Path,
    case_dir: Path,
    audit_id: str,
    examiner: str,
    start: float,
    model_used: str,
) -> None:
    """Canonical :class:`AuditEntry` (architecture §4.4). Scrub U+2028
    / U+2029 from agent-controlled text so a line-terminator attack
    can't make append_jsonl_line raise inside this function."""
    elapsed_ms = (time.monotonic() - start) * 1000.0
    summary_json = result.model_dump_json()
    artefact_path = (
        _hypothesis_log(case_dir) if result.success else case_dir / "audit" / "findings.jsonl"
    )
    scrubbed_params: dict[str, object] = {
        "from_hypothesis_id": payload.from_hypothesis_id,
        "to_hypothesis_id": payload.to_hypothesis_id,
        "reason": scrub_line_terminators(payload.reason),
        "abandoning_evidence": list(payload.abandoning_evidence),
    }
    entry = AuditEntry(
        ts=datetime.now(UTC),
        audit_id=audit_id,
        tool="record_pivot",
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
    result: PivotResult, *, audit_id: str, examiner: str
) -> ToolResponse[PivotResult]:
    from silentwitness_mcp.envelope import make_empty_provenance

    return ToolResponse[PivotResult](
        success=True,
        data=result,
        audit_id=audit_id,
        examiner=examiner,
        advisories=() if result.success else (str(result.reason),),
        data_provenance=make_empty_provenance("record_pivot"),
    )


__all__ = ["PivotInput", "PivotRejectReason", "PivotResult", "record_pivot"]
