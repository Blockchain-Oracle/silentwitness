"""``record_observation`` tool body (architecture §4.2, §4.5, §4.7, §4.8, §8.4).

Pipeline (load-bearing order): sanitize text → citation gate per
cited_span (first reject short-circuits) → entity gate on sanitized
text → allocate observation_id + atomic findings.json append → audit
row to audit/findings.jsonl REGARDLESS of accept/reject (rejected
attempts are evidence too, architecture §4.4 + §8.4)."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from silentwitness_common.atomic_io import append_jsonl_line
from silentwitness_common.types import AuditEntry, CitedSpan, ToolResponse
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings._id_gen import allocate_observation_id
from silentwitness_mcp.findings._scrub import scrub_line_terminators
from silentwitness_mcp.index.store import IndexRecord
from silentwitness_mcp.verification.citation_gate import verify_citation
from silentwitness_mcp.verification.entity_gate import (
    EntityGateModelError,
    verify_entities,
)
from silentwitness_mcp.verification.sanitizer import (
    StripEvent,
    StripEventWriter,
    sanitize,
)


class ObservationRejectReason(StrEnum):
    """Architectural seam — mirror of CitationRejectReason values
    (citation_gate) plus HALLUCINATED_ENTITIES (entity_gate) plus
    three pipeline-failure codes split per round-2 type-design Critical
    (a catch-all collapses agent self-correction signals; the agent
    cannot distinguish "retry might help" from "escalate, the store
    is corrupted").

    Re-declared rather than imported so adding a new citation gate
    code is an explicit decision, not a silent surface widening."""

    RECORD_NOT_FOUND = "RECORD_NOT_FOUND"
    SPAN_NOT_IN_RECORD = "SPAN_NOT_IN_RECORD"
    HALLUCINATED_ENTITIES = "HALLUCINATED_ENTITIES"
    # Pipeline-failure codes (split per round-2 type-design Critical):
    ENTITY_GATE_UNAVAILABLE = "ENTITY_GATE_UNAVAILABLE"
    FINDINGS_STORE_CORRUPTED = "FINDINGS_STORE_CORRUPTED"
    FINDINGS_STORE_UNWRITABLE = "FINDINGS_STORE_UNWRITABLE"
    PIPELINE_INTERNAL_ERROR = "PIPELINE_INTERNAL_ERROR"  # uncategorised


_RESULT_CONFIG = ConfigDict(frozen=True, extra="forbid")


class ObservationInput(BaseModel):
    """Agent-emitted observation (architecture §4.2 record_observation row).

    Each cited_span names one evidence-index record by ``record_id`` and quotes
    the ``span_text`` it relies on. Provenance (``audit_id`` / ``source_tool``)
    is resolved from the authoritative records by the pipeline, not declared by
    the agent — so there is no agent-supplied audit_id superset to validate."""

    model_config = _RESULT_CONFIG

    text: str = Field(min_length=1)
    cited_spans: tuple[CitedSpan, ...] = Field(min_length=1)


class ObservationResult(BaseModel):
    """Result payload. ``suggested`` is the verbatim cited string the agent
    re-submits with after HALLUCINATED_ENTITIES (architecture §8.4)."""

    model_config = _RESULT_CONFIG

    success: bool
    observation_id: str | None = None
    reason: ObservationRejectReason | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    hallucinated: tuple[str, ...] = Field(default_factory=tuple)
    suggested: str | None = None

    @model_validator(mode="after")
    def _check_tag(self) -> ObservationResult:
        """Discriminator (round-1 type-design Critical). Mirrors
        :class:`CitationResult._check_tag` in verification/_types.py."""
        if self.success:
            if self.observation_id is None:
                raise ValueError("success=True requires observation_id")
            if self.reason is not None:
                raise ValueError("success=True must not carry reason")
            if self.hallucinated:
                raise ValueError("success=True must have empty hallucinated")
        else:
            if self.reason is None:
                raise ValueError("success=False requires reason")
            if self.observation_id is not None:
                raise ValueError("success=False must not carry observation_id")
        return self


# ---------------------------------------------------------------------------
# StripEventWriter wiring → sanitizer.jsonl
# ---------------------------------------------------------------------------


class _JsonlStripWriter(StripEventWriter):
    """The sanitizer is the only producer of ``audit/sanitizer.jsonl``."""

    def __init__(self, sanitizer_log: Path) -> None:
        sanitizer_log.parent.mkdir(parents=True, exist_ok=True)
        # touch so a zero-strip pipeline still creates the file —
        # absent file is indistinguishable from "never ran"
        # (round-1 silent-failure H1).
        sanitizer_log.touch(exist_ok=True)
        self._path = sanitizer_log

    def emit(self, event: StripEvent) -> None:
        append_jsonl_line(self._path, event.model_dump_json())


# ---------------------------------------------------------------------------
# Self-correction hint builder (architecture §8.4)
# ---------------------------------------------------------------------------


def _suggested_for_hallucination(hallucinated_texts: tuple[str, ...]) -> str | None:
    """Build actionable self-correction guidance for a HALLUCINATED_ENTITIES reject.

    The gate found one or more entities in ``observation_text`` that do not
    appear verbatim in ANY cited span — typically because the agent described
    lines it read but cited a *different* line. We name EVERY offending entity
    (not just the first) and give the two — and only two — valid fixes, so the
    agent corrects by construction rather than guessing (architecture §8.4).
    The agent's reasoning loop reads ``ObservationResult.suggested`` and
    re-submits."""
    if not hallucinated_texts:
        return None
    offending = ", ".join(repr(t) for t in hallucinated_texts)
    return (
        f"Entity gate: {offending} do not appear verbatim in any span you cited "
        "— you are likely describing evidence you read but did not cite. Fix by "
        "EITHER (a) for each entity, add a cited_span {record_id, span_text} whose "
        "span_text is the exact text containing it — use search_evidence (or "
        "get_record) to find that record_id — OR (b) remove the entity from "
        "observation_text. Quote every entity you name byte-for-byte; do not "
        "paraphrase it."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def record_observation(
    payload: ObservationInput,
    *,
    case_dir: Path,
    records: Mapping[int, IndexRecord],
    audit_logger: AuditLogger,
    model_used: str,
) -> ToolResponse[ObservationResult]:
    """Pipeline: sanitize → citation gate per-span → entity gate → allocate
    observation_id → audit row. The audit row lands in a ``finally`` block
    so any pipeline exception (corrupted findings.json, spaCy unavailable,
    disk-full mid-write) still produces an audit trail (round-1
    silent-failure C1/C2/C3/H3/H4). Returns the canonical ``ToolResponse``
    envelope per story-response-envelope (round-1 silent-failure H2)."""
    sanitizer_log = case_dir / "audit" / "sanitizer.jsonl"
    findings_log = case_dir / "audit" / "findings.jsonl"
    start = time.monotonic()
    pre_audit_id = audit_logger.next_audit_id()
    result: ObservationResult | None = None
    try:
        result = _run_pipeline(
            payload,
            case_dir=case_dir,
            sanitizer_log=sanitizer_log,
            records=records,
            pre_audit_id=pre_audit_id,
        )
    except EntityGateModelError as exc:
        result = ObservationResult(
            success=False,
            reason=ObservationRejectReason.ENTITY_GATE_UNAVAILABLE,
            context={"stage": "entity_gate", "error": str(exc)},
        )
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        # Findings-store reads/parses (round-2 silent-failure H4).
        result = ObservationResult(
            success=False,
            reason=ObservationRejectReason.FINDINGS_STORE_CORRUPTED,
            context={"stage": "findings_read", "error_type": type(exc).__name__},
        )
    except OSError as exc:
        # Disk-side failures during write (round-1 silent-failure C1).
        result = ObservationResult(
            success=False,
            reason=ObservationRejectReason.FINDINGS_STORE_UNWRITABLE,
            context={"stage": "findings_write", "error_type": type(exc).__name__},
        )
    except Exception as exc:
        # Round-2 silent-failure C3: broad catch so TypeError/ImportError/
        # RuntimeError don't leak past the envelope. BaseException
        # subclasses (KeyboardInterrupt/SystemExit) still propagate.
        result = ObservationResult(
            success=False,
            reason=ObservationRejectReason.PIPELINE_INTERNAL_ERROR,
            context={"stage": "pipeline", "error_type": type(exc).__name__},
        )
    finally:
        if result is None:  # pragma: no cover — defensive
            result = ObservationResult(
                success=False,
                reason=ObservationRejectReason.PIPELINE_INTERNAL_ERROR,
                context={"stage": "pipeline", "error_type": "unknown"},
            )
        # Round-2 silent-failure C1: guard the audit-write so a failure
        # here doesn't mask the original pipeline error and erase the
        # row. If both fail, the audit-write error is logged via the
        # context dict on a best-effort second attempt.
        try:
            _write_audit_row(
                result,
                payload=payload,
                records=records,
                findings_log=findings_log,
                case_dir=case_dir,
                audit_id=pre_audit_id,
                examiner=audit_logger.examiner,
                start=start,
                model_used=model_used,
            )
        except Exception as audit_exc:
            # Audit write failed (disk full, permission, schema validation,
            # etc.). Surface the gap inside data.context so the agent and
            # downstream auditor can detect it. The envelope still returns
            # to the caller — better a response with audit_write_failed=True
            # than a raw exception leaking past the contract boundary.
            result = ObservationResult(
                success=False,
                reason=ObservationRejectReason.FINDINGS_STORE_UNWRITABLE,
                context={
                    "stage": "audit_write",
                    "error_type": type(audit_exc).__name__,
                    "audit_write_failed": True,
                },
            )
    return _wrap_envelope(result, audit_id=pre_audit_id, examiner=audit_logger.examiner)


def _run_pipeline(
    payload: ObservationInput,
    *,
    case_dir: Path,
    sanitizer_log: Path,
    records: Mapping[int, IndexRecord],
    pre_audit_id: str,
) -> ObservationResult:
    sanitize_result = sanitize(
        payload.text,
        pre_audit_id,
        audit_writer=_JsonlStripWriter(sanitizer_log),
    )
    sanitized_text = sanitize_result.wrapped_text

    for span in payload.cited_spans:
        verdict = verify_citation(span, records)
        if not verdict.success:
            return ObservationResult(
                success=False,
                reason=ObservationRejectReason(str(verdict.reason)),
                context=dict(verdict.context),
            )

    entity_result = verify_entities(sanitized_text, payload.cited_spans)
    if not entity_result.success:
        hallucinated_texts = tuple(e.text for e in entity_result.hallucinated)
        return ObservationResult(
            success=False,
            reason=ObservationRejectReason.HALLUCINATED_ENTITIES,
            hallucinated=hallucinated_texts,
            suggested=_suggested_for_hallucination(hallucinated_texts),
        )

    observation_record = {
        "text": payload.text,
        "cited_spans": [s.model_dump(mode="json") for s in payload.cited_spans],
        "audit_ids": _resolved_audit_ids(payload.cited_spans, records),
    }
    observation_id = allocate_observation_id(case_dir, observation_record)
    return ObservationResult(success=True, observation_id=observation_id)


def _resolved_audit_ids(
    cited_spans: tuple[CitedSpan, ...], records: Mapping[int, IndexRecord]
) -> list[str]:
    """Provenance for the audit trail, read from the authoritative records the
    agent cited (never agent-supplied). Sorted + de-duplicated; a span whose
    record_id is absent contributes nothing (the citation gate already rejects
    that case before we reach here on the accept path)."""
    audit_ids = {records[s.record_id].audit_id for s in cited_spans if s.record_id in records}
    return sorted(a for a in audit_ids if a)


def _write_audit_row(
    result: ObservationResult,
    *,
    payload: ObservationInput,
    records: Mapping[int, IndexRecord],
    findings_log: Path,
    case_dir: Path,
    audit_id: str,
    examiner: str,
    start: float,
    model_used: str,
) -> None:
    """Build the canonical :class:`AuditEntry` shape (architecture §4.4)
    and append. Round-1 code-reviewer C1: schema follows AuditEntry, not
    a forked dict. ``stdout_path`` points at the artefact the call
    actually produces (findings.json on accept; the audit log on reject)."""
    elapsed_ms = (time.monotonic() - start) * 1000.0
    summary_json = result.model_dump_json()
    artefact_path = (
        case_dir / "findings.json" if result.success else case_dir / "audit" / "findings.jsonl"
    )
    # Scrub line-terminator chars from observation text BEFORE building
    # params dict — round-2 silent-failure C2: attacker-controlled
    # U+2028/U+2029 in payload.text would otherwise make
    # append_jsonl_line raise inside this function and erase the row.
    scrubbed_params: dict[str, object] = {
        "text": scrub_line_terminators(payload.text),
        "cited_spans": [s.model_dump(mode="json") for s in payload.cited_spans],
        "audit_ids": _resolved_audit_ids(payload.cited_spans, records),
    }
    entry = AuditEntry(
        ts=datetime.now(UTC),
        audit_id=audit_id,
        tool="record_observation",
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
    result: ObservationResult, *, audit_id: str, examiner: str
) -> ToolResponse[ObservationResult]:
    """Wrap in the canonical ``ToolResponse[ObservationResult]`` envelope.

    Semantics: ``envelope.success`` is the *transport-layer* success flag
    (the tool call completed and returned a well-formed payload). It is
    ALWAYS True for record_observation — even a corrupted findings.json
    or an audit-write failure surfaces as a structured rejection inside
    ``data``, not as an envelope-level error. The inner ``data.success``
    carries the gate verdict; ``data.reason`` / ``data.context`` /
    ``data.hallucinated`` / ``data.suggested`` carry the rich rejection
    details the agent's self-correction loop reads. When the audit row
    itself could not be written, ``data.context`` includes
    ``audit_write_failed=True`` so a downstream auditor can detect
    the audit-trail gap."""
    from silentwitness_mcp.envelope import make_empty_provenance

    return ToolResponse[ObservationResult](
        success=True,
        data=result,
        audit_id=audit_id,
        examiner=examiner,
        advisories=() if result.success else (str(result.reason),),
        data_provenance=make_empty_provenance("record_observation"),
    )


__all__ = [
    "ObservationInput",
    "ObservationRejectReason",
    "ObservationResult",
    "record_observation",
]
