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
import time
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from silentwitness_common.atomic_io import append_jsonl_line
from silentwitness_common.types import AuditEntry, CitedSpan
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings._id_gen import allocate_observation_id
from silentwitness_mcp.verification.citation_gate import verify_citation
from silentwitness_mcp.verification.entity_gate import verify_entities
from silentwitness_mcp.verification.sanitizer import (
    StripEvent,
    StripEventWriter,
    sanitize,
)


class ObservationRejectReason(StrEnum):
    """Union of citation-gate + entity-gate reject codes that
    ``record_observation`` surfaces in its ``ObservationResult``."""

    AUDIT_ID_NOT_FOUND = "AUDIT_ID_NOT_FOUND"
    OUTPUT_HASH_MISMATCH = "OUTPUT_HASH_MISMATCH"
    SPAN_NOT_IN_LINES = "SPAN_NOT_IN_LINES"
    LINE_RANGE_OUT_OF_BOUNDS = "LINE_RANGE_OUT_OF_BOUNDS"
    STDOUT_PATH_MISSING = "STDOUT_PATH_MISSING"
    STDOUT_PATH_UNREADABLE = "STDOUT_PATH_UNREADABLE"
    TOOL_NOT_REGISTERED = "TOOL_NOT_REGISTERED"
    HALLUCINATED_ENTITIES = "HALLUCINATED_ENTITIES"


_RESULT_CONFIG = ConfigDict(frozen=True, extra="forbid")


class ObservationInput(BaseModel):
    """Agent-emitted observation (architecture §4.2 record_observation row).
    Cited spans are re-verified before persistence; the audit_ids list is
    the superset every cited_span's audit_id must appear in."""

    model_config = _RESULT_CONFIG

    text: str = Field(min_length=1)
    cited_spans: tuple[CitedSpan, ...] = Field(min_length=1)
    audit_ids: tuple[str, ...] = Field(min_length=1)


class ObservationResult(BaseModel):
    """Result payload carried as ``ToolResponse[ObservationResult].data``.

    On accept: ``success=True`` + ``observation_id`` populated; all other
    fields empty. On reject: ``success=False`` + ``reason`` set + context
    fields populated for the agent's self-correction loop (architecture
    §8.4 — ``suggested`` is the verbatim string from the cited span the
    agent should resubmit with after a HALLUCINATED_ENTITIES rejection).
    """

    model_config = _RESULT_CONFIG

    success: bool
    observation_id: str | None = None
    reason: ObservationRejectReason | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    hallucinated: tuple[str, ...] = Field(default_factory=tuple)
    suggested: str | None = None


# ---------------------------------------------------------------------------
# Citation-gate → ObservationRejectReason mapping
# ---------------------------------------------------------------------------


_CITATION_REASON_MAP: Mapping[str, ObservationRejectReason] = {
    "AUDIT_ID_NOT_FOUND": ObservationRejectReason.AUDIT_ID_NOT_FOUND,
    "OUTPUT_HASH_MISMATCH": ObservationRejectReason.OUTPUT_HASH_MISMATCH,
    "SPAN_NOT_IN_LINES": ObservationRejectReason.SPAN_NOT_IN_LINES,
    "LINE_RANGE_OUT_OF_BOUNDS": ObservationRejectReason.LINE_RANGE_OUT_OF_BOUNDS,
    "STDOUT_PATH_MISSING": ObservationRejectReason.STDOUT_PATH_MISSING,
    "STDOUT_PATH_UNREADABLE": ObservationRejectReason.STDOUT_PATH_UNREADABLE,
    "TOOL_NOT_REGISTERED": ObservationRejectReason.TOOL_NOT_REGISTERED,
}


# ---------------------------------------------------------------------------
# StripEventWriter wiring → sanitizer.jsonl
# ---------------------------------------------------------------------------


class _JsonlStripWriter(StripEventWriter):
    """Append each StripEvent as a JSONL row to
    ``cases/<case_id>/audit/sanitizer.jsonl``. The sanitizer is the
    only producer of this file."""

    def __init__(self, sanitizer_log: Path) -> None:
        self._path = sanitizer_log

    def emit(self, event: StripEvent) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
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
) -> ObservationResult:
    """Run the four-stage pipeline.

    ``case_dir`` is the per-case directory (``cases/<case_id>``).
    ``audit_index`` is the in-memory lookup of audit_id → AuditEntry
    that the citation gate reads. ``audit_logger`` is the singleton
    JSONL writer for this case. ``model_used`` flows into the audit
    entry so the report renderer can attribute the call.
    """
    sanitizer_log = case_dir / "audit" / "sanitizer.jsonl"
    findings_log = case_dir / "audit" / "findings.jsonl"
    start = time.monotonic()
    pre_audit_id = audit_logger.next_audit_id()

    sanitize_result = sanitize(
        payload.text,
        pre_audit_id,
        audit_writer=_JsonlStripWriter(sanitizer_log),
    )
    sanitized_text = sanitize_result.wrapped_text

    for span in payload.cited_spans:
        verdict = verify_citation(span, audit_index)
        if not verdict.success:
            return _audit_and_return(
                _reject_from_citation(verdict.reason, verdict.context),
                payload=payload,
                case_dir=case_dir,
                findings_log=findings_log,
                audit_id=pre_audit_id,
                start=start,
                model_used=model_used,
            )

    entity_result = verify_entities(sanitized_text, payload.cited_spans)
    if not entity_result.success:
        hallucinated_texts = tuple(e.text for e in entity_result.hallucinated)
        result = ObservationResult(
            success=False,
            reason=ObservationRejectReason.HALLUCINATED_ENTITIES,
            hallucinated=hallucinated_texts,
            suggested=_suggested_for_hallucination(hallucinated_texts, payload.cited_spans),
        )
        return _audit_and_return(
            result,
            payload=payload,
            case_dir=case_dir,
            findings_log=findings_log,
            audit_id=pre_audit_id,
            start=start,
            model_used=model_used,
        )

    observation_record = {
        "text": payload.text,
        "cited_spans": [s.model_dump(mode="json") for s in payload.cited_spans],
        "audit_ids": list(payload.audit_ids),
    }
    observation_id = allocate_observation_id(case_dir, observation_record)
    accepted = ObservationResult(success=True, observation_id=observation_id)
    return _audit_and_return(
        accepted,
        payload=payload,
        case_dir=case_dir,
        findings_log=findings_log,
        audit_id=pre_audit_id,
        start=start,
        model_used=model_used,
    )


def _reject_from_citation(reason: object, context: dict[str, Any]) -> ObservationResult:
    code = _CITATION_REASON_MAP[str(reason)]
    return ObservationResult(success=False, reason=code, context=context)


def _audit_and_return(
    result: ObservationResult,
    *,
    payload: ObservationInput,
    case_dir: Path,
    findings_log: Path,
    audit_id: str,
    start: float,
    model_used: str,
) -> ObservationResult:
    """Write one audit JSONL row (architecture §4.4) and return ``result``."""
    elapsed_ms = (time.monotonic() - start) * 1000.0
    summary = result.model_dump(mode="json")
    summary_json = result.model_dump_json()
    summary_truncated = summary_json[:1024]
    findings_log.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "audit_id": audit_id,
        "tool": "record_observation",
        "params": payload.model_dump(mode="json"),
        "result_summary": summary,
        "result_summary_truncated": summary_truncated,
        "result_sha256": hashlib.sha256(summary_json.encode("utf-8")).hexdigest(),
        "stdout_path": str(case_dir / "audit" / "findings.jsonl"),
        "elapsed_ms": elapsed_ms,
        "examiner": audit_id.split("-")[1],
        "model_used": model_used,
    }
    import json

    append_jsonl_line(findings_log, json.dumps(entry, ensure_ascii=False))
    return result


__all__ = [
    "ObservationInput",
    "ObservationRejectReason",
    "ObservationResult",
    "record_observation",
]
