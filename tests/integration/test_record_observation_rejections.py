"""Rejection-path tests for ``record_observation`` (split for 400-LOC discipline).

One test per reachable ObservationRejectReason — closes the BDD spec criterion
that every reject reason is exercised end-to-end against the evidence index."""

from __future__ import annotations

import json
from pathlib import Path

from silentwitness_common.types import CitedSpan
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings.observation import (
    ObservationInput,
    ObservationRejectReason,
    record_observation,
)
from tests.integration.conftest import MODEL, cited_span_for, make_record


def _env(tmp_path: Path) -> tuple[Path, AuditLogger]:
    case_dir = tmp_path / "case-01"
    case_dir.mkdir()
    return case_dir, AuditLogger(case_dir, examiner="aj")


def test_record_not_found_rejection(tmp_path: Path) -> None:
    """A cited record_id absent from the index → RECORD_NOT_FOUND."""
    case_dir, logger = _env(tmp_path)
    bogus = CitedSpan(record_id=998, span_text="anything")
    payload = ObservationInput(text="claim", cited_spans=(bogus,))
    envelope = record_observation(
        payload, case_dir=case_dir, records={}, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.RECORD_NOT_FOUND
    assert (case_dir / "audit" / "findings.jsonl").exists()


def test_span_not_in_record_rejection(tmp_path: Path) -> None:
    """A quote that is not a verbatim substring of the cited record →
    SPAN_NOT_IN_RECORD (closed-domain hallucination caught)."""
    case_dir, logger = _env(tmp_path)
    aid = logger.next_audit_id()
    record = make_record("row alpha\nrow beta\nrow gamma", record_id=1, audit_id=aid)
    wrong = CitedSpan(record_id=1, span_text="row delta")
    payload = ObservationInput(text="row delta noted", cited_spans=(wrong,))
    envelope = record_observation(
        payload, case_dir=case_dir, records={1: record}, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.SPAN_NOT_IN_RECORD


def test_hallucinated_entities_ethereal_demo(tmp_path: Path) -> None:
    """Architecture §8.4 demo case: cites real Program-Files-x86 path but
    emits Program Files\\Ethereal. Entity gate catches it."""
    case_dir, logger = _env(tmp_path)
    aid = logger.next_audit_id()
    text = "C:\\Program Files (x86)\\Ethereal\\ethereal.exe last run 2024-11-12"
    record = make_record(text, record_id=1, audit_id=aid)
    span = cited_span_for(text, record_id=1, span_text="C:\\Program Files (x86)\\Ethereal")
    payload = ObservationInput(
        text="Ethereal installed under C:\\Program Files\\Ethereal",
        cited_spans=(span,),
    )
    envelope = record_observation(
        payload, case_dir=case_dir, records={1: record}, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.HALLUCINATED_ENTITIES
    assert envelope.data.hallucinated
    assert envelope.data.suggested is not None


def test_hallucinated_entities_carries_suggested(tmp_path: Path) -> None:
    case_dir, logger = _env(tmp_path)
    aid = logger.next_audit_id()
    text = "hash 9f8e7d6c5b4a3210000000000000000000000000000000000000000000000000"
    record = make_record(text, record_id=1, audit_id=aid)
    span = cited_span_for(
        text,
        record_id=1,
        span_text="9f8e7d6c5b4a3210000000000000000000000000000000000000000000000000",
    )
    payload = ObservationInput(
        text="malware hash 1111222233334444555566667777888899990000aaaabbbbccccdddd11112222",
        cited_spans=(span,),
    )
    envelope = record_observation(
        payload, case_dir=case_dir, records={1: record}, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.HALLUCINATED_ENTITIES
    suggested = envelope.data.suggested or ""
    # The hint must NAME the offending (hallucinated) entity and give the
    # actionable re-cite path (index-query tools), so the agent corrects by construction.
    assert "1111222233334444" in suggested
    assert "search_evidence" in suggested or "record_id" in suggested


def test_agent_self_correction_after_hallucination(tmp_path: Path) -> None:
    """Architecture §8.4: agent re-submits with verbatim path; second call succeeds."""
    case_dir, logger = _env(tmp_path)
    aid = logger.next_audit_id()
    text = "C:\\Program Files (x86)\\Ethereal\\ethereal.exe last run 2024-11-12"
    record = make_record(text, record_id=1, audit_id=aid)
    span = cited_span_for(text, record_id=1, span_text="C:\\Program Files (x86)\\Ethereal")

    first = ObservationInput(
        text="Ethereal installed under C:\\Program Files\\Ethereal",
        cited_spans=(span,),
    )
    first_envelope = record_observation(
        first, case_dir=case_dir, records={1: record}, audit_logger=logger, model_used=MODEL
    )
    assert first_envelope.data.success is False

    second = ObservationInput(
        text="Ethereal installed under C:\\Program Files (x86)\\Ethereal",
        cited_spans=(span,),
    )
    second_envelope = record_observation(
        second, case_dir=case_dir, records={1: record}, audit_logger=logger, model_used=MODEL
    )
    assert second_envelope.data.success is True
    assert second_envelope.data.observation_id == "O-001"


def test_corrupted_findings_json_returns_pipeline_internal_error(tmp_path: Path) -> None:
    """Silent-failure H4: a corrupted findings.json must surface as a
    structured FINDINGS_STORE_CORRUPTED reject AND emit an audit row —
    the round-2 try/finally guard's primary justification."""
    case_dir, logger = _env(tmp_path)
    (case_dir / "findings.json").write_text("not valid json{")
    aid = logger.next_audit_id()
    text = "PID 4 System"
    record = make_record(text, record_id=1, audit_id=aid)
    span = cited_span_for(text, record_id=1, span_text="PID 4 System")
    payload = ObservationInput(text="PID 4 System", cited_spans=(span,))
    envelope = record_observation(
        payload, case_dir=case_dir, records={1: record}, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.FINDINGS_STORE_CORRUPTED
    assert (case_dir / "audit" / "findings.jsonl").exists()


def test_u2028_in_text_does_not_break_audit_write(tmp_path: Path) -> None:
    """Round-3 silent-failure C2: attacker-controlled U+2028 in
    observation text must NOT break the audit-row write. The scrubber
    replaces it with U+FFFD so append_jsonl_line accepts the row."""
    case_dir, logger = _env(tmp_path)
    aid = logger.next_audit_id()
    text = "PID 4 System"
    record = make_record(text, record_id=1, audit_id=aid)
    span = cited_span_for(text, record_id=1, span_text="PID 4")
    payload = ObservationInput(
        text="PID 4 System\u2028harmful injection",
        cited_spans=(span,),
    )
    envelope = record_observation(
        payload, case_dir=case_dir, records={1: record}, audit_logger=logger, model_used=MODEL
    )
    # No raw ValueError leaks; audit row landed.
    findings_log = case_dir / "audit" / "findings.jsonl"
    assert findings_log.exists()
    row = json.loads(findings_log.read_text().strip().split("\n")[0])
    # The scrubbed text contains U+FFFD where U+2028 was.
    assert "\ufffd" in row["params"]["text"]
    assert "\u2028" not in row["params"]["text"]
    # Envelope returns cleanly (entity gate fires on the scrubbed text).
    assert envelope.success is True
