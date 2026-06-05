"""``record_observation`` tool body (architecture §4.2, §4.5, §4.7, §4.8, §8.4).

The wedge tool. Citation + entity + sanitizer pipeline. The 3:30-4:00
demo arc lives here: an LLM-emitted observation that cites a path NOT
in the cited evidence is REJECTED with HALLUCINATED_ENTITIES and a
suggested verbatim string the agent can re-submit with.

Pipeline order is LOAD-BEARING (architecture §8.4):

1. Sanitize the observation text — strips XML role tokens, BIDI,
   zero-width chars, etc. before either gate runs.
2. Citation gate over every cited_span — if any rejects, the whole
   observation rejects (the upstream failure short-circuits the gate
   pair so the agent fixes the citation first).
3. Entity gate over the SANITIZED text vs all cited_span bytes — only
   reached when citation gate accepts every span.
4. Allocate observation_id + atomically append to findings.json.
5. Emit one ``audit/findings.jsonl`` row whether accepted or rejected
   — rejected attempts are evidence too (architecture §4.4 + §8.4
   "the audit log is the truth of what the agent attempted").
"""

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
from silentwitness_common.types import AuditEntry, AuditId, CitedSpan, ToolResponse
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings._id_gen import allocate_observation_id
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
    PIPELINE_INTERNAL_ERROR (catch-all for spaCy unavailable,
    corrupted findings.json, etc., per round-1 silent-failure H3/H4).
    Re-declared rather than imported so adding a new citation gate code
    is an explicit decision, not a silent surface widening."""

    AUDIT_ID_NOT_FOUND = "AUDIT_ID_NOT_FOUND"
    OUTPUT_HASH_MISMATCH = "OUTPUT_HASH_MISMATCH"
    SPAN_NOT_IN_LINES = "SPAN_NOT_IN_LINES"
    LINE_RANGE_OUT_OF_BOUNDS = "LINE_RANGE_OUT_OF_BOUNDS"
    STDOUT_PATH_MISSING = "STDOUT_PATH_MISSING"
    STDOUT_PATH_UNREADABLE = "STDOUT_PATH_UNREADABLE"
    TOOL_NOT_REGISTERED = "TOOL_NOT_REGISTERED"
    HALLUCINATED_ENTITIES = "HALLUCINATED_ENTITIES"
    PIPELINE_INTERNAL_ERROR = "PIPELINE_INTERNAL_ERROR"


_RESULT_CONFIG = ConfigDict(frozen=True, extra="forbid")


class ObservationInput(BaseModel):
    """Agent-emitted observation (architecture §4.2 record_observation row)."""

    model_config = _RESULT_CONFIG

    text: str = Field(min_length=1)
    cited_spans: tuple[CitedSpan, ...] = Field(min_length=1)
    audit_ids: tuple[AuditId, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _cited_audit_ids_subset(self) -> ObservationInput:
        """The audit_ids tuple is the superset every cited_span's audit_id
        must appear in (round-1 type-design Important). Architecture §4.2
        — declared superset enforced, not documented-only."""
        cited = {span.audit_id for span in self.cited_spans}
        declared = set(self.audit_ids)
        missing = cited - declared
        if missing:
            raise ValueError(
                f"cited_spans reference audit_ids {sorted(missing)} not in "
                f"the declared audit_ids superset"
            )
        return self


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


def _suggested_for_hallucination(
    hallucinated_texts: tuple[str, ...], cited_spans: tuple[CitedSpan, ...]
) -> str | None:
    """Pick the first hallucinated entity and emit a one-line hint
    pointing the agent at the verbatim text in the cited spans.

    The agent's reasoning loop reads ``ObservationResult.suggested`` and
    composes a re-submission using the verbatim string. The hint format
    is deliberately terse — it's a single-shot prompt-layer nudge, not
    an explanation."""
    if not hallucinated_texts or not cited_spans:
        return None
    first = hallucinated_texts[0]
    sample_span = cited_spans[0].span_text
    return (
        f"observation_text mentioned {first!r} but the cited spans say "
        f"{sample_span!r}; re-cite the verbatim string from the evidence"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def record_observation(
    payload: ObservationInput,
    *,
    case_dir: Path,
    audit_index: Mapping[str, AuditEntry],
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
            audit_index=audit_index,
            pre_audit_id=pre_audit_id,
        )
    except EntityGateModelError as exc:
        result = ObservationResult(
            success=False,
            reason=ObservationRejectReason.PIPELINE_INTERNAL_ERROR,
            context={"stage": "entity_gate", "error": str(exc)},
        )
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
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
    return _wrap_envelope(result, audit_id=pre_audit_id, examiner=audit_logger.examiner)


def _run_pipeline(
    payload: ObservationInput,
    *,
    case_dir: Path,
    sanitizer_log: Path,
    audit_index: Mapping[str, AuditEntry],
    pre_audit_id: str,
) -> ObservationResult:
    sanitize_result = sanitize(
        payload.text,
        pre_audit_id,
        audit_writer=_JsonlStripWriter(sanitizer_log),
    )
    sanitized_text = sanitize_result.wrapped_text

    for span in payload.cited_spans:
        verdict = verify_citation(span, audit_index)
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
            suggested=_suggested_for_hallucination(hallucinated_texts, payload.cited_spans),
        )

    observation_record = {
        "text": payload.text,
        "cited_spans": [s.model_dump(mode="json") for s in payload.cited_spans],
        "audit_ids": list(payload.audit_ids),
    }
    observation_id = allocate_observation_id(case_dir, observation_record)
    return ObservationResult(success=True, observation_id=observation_id)


def _write_audit_row(
    result: ObservationResult,
    *,
    payload: ObservationInput,
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
    entry = AuditEntry(
        ts=datetime.now(UTC),
        audit_id=audit_id,
        tool="record_observation",
        params=payload.model_dump(mode="json"),
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
    """Wrap in the canonical ``ToolResponse[ObservationResult]`` envelope
    per story-response-envelope (round-1 silent-failure H2).

    Semantics: ``envelope.success=True`` means "the tool ran end-to-end
    and persisted an audit row" — ALWAYS True for record_observation
    because every call writes a row in the ``finally`` block. The inner
    ``data.success`` carries the gate verdict; ``data.reason`` /
    ``data.context`` / ``data.hallucinated`` / ``data.suggested`` carry
    the rich rejection details the agent's self-correction loop reads."""
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
