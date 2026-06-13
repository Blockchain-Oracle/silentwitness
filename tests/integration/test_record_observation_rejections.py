"""Rejection-path tests for ``record_observation`` (split for 400-LOC discipline).

One test per ObservationRejectReason — closes the BDD spec criterion
that every reject reason is exercised end-to-end."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from silentwitness_common.types import AuditEntry, CitedSpan
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings.observation import (
    ObservationInput,
    ObservationRejectReason,
    record_observation,
)

_EXAMINER = "aj"
_MODEL = "anthropic:claude-opus-4-7"
_FIXED_NOW = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)


def _write_blob_and_entry(
    blobs_dir: Path, *, audit_id: str, content: bytes, tool: str = "_universal_only"
) -> AuditEntry:
    blobs_dir.mkdir(parents=True, exist_ok=True)
    blob_path = blobs_dir / f"{audit_id}.txt"
    blob_path.write_bytes(content)
    return AuditEntry(
        ts=_FIXED_NOW,
        audit_id=audit_id,
        tool=tool,
        params={},
        result_summary={},
        result_sha256=hashlib.sha256(content).hexdigest(),
        stdout_path=blob_path,
        elapsed_ms=10.0,
        examiner=_EXAMINER,
        model_used=_MODEL,
    )


def _cited_span_for(content: bytes, audit_id: str, *, span_text: str) -> CitedSpan:
    text = content.decode("utf-8", errors="surrogateescape")
    for idx, line in enumerate(text.split("\n")):
        if span_text in line:
            return CitedSpan(
                audit_id=audit_id,
                sha256_of_normalized_output=hashlib.sha256(content).hexdigest(),
                line_start=idx,
                line_end=idx + 1,
                span_text=line,
            )
    raise AssertionError(f"span_text {span_text!r} not in content")


def _make_case_env(tmp_path: Path) -> tuple[Path, Path, AuditLogger]:
    case_dir = tmp_path / "case-01"
    case_dir.mkdir()
    return case_dir, case_dir / "blobs", AuditLogger(case_dir, examiner=_EXAMINER)


def test_audit_id_not_found_rejection(tmp_path: Path) -> None:
    case_dir, _, logger = _make_case_env(tmp_path)
    bogus = CitedSpan(
        audit_id="sift-aj-20260613-998",
        sha256_of_normalized_output="a" * 64,
        line_start=0,
        line_end=1,
        span_text="anything",
    )
    payload = ObservationInput(
        text="claim",
        cited_spans=(bogus,),
        audit_ids=("sift-aj-20260613-998",),
    )
    envelope = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.AUDIT_ID_NOT_FOUND
    assert (case_dir / "audit" / "findings.jsonl").exists()


def test_output_hash_mismatch_rejection(tmp_path: Path) -> None:
    case_dir, blobs_dir, logger = _make_case_env(tmp_path)
    aid = logger.next_audit_id()
    content = b"row one\nrow two\n"
    entry = _write_blob_and_entry(blobs_dir, audit_id=aid, content=content)
    bad = CitedSpan(
        audit_id=aid,
        sha256_of_normalized_output="0" * 64,
        line_start=0,
        line_end=1,
        span_text="row one",
    )
    payload = ObservationInput(
        text="row one is the first row",
        cited_spans=(bad,),
        audit_ids=(aid,),
    )
    envelope = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.OUTPUT_HASH_MISMATCH
    assert "expected_sha256" in envelope.data.context
    assert "actual_sha256" in envelope.data.context


def test_span_not_in_lines_rejection(tmp_path: Path) -> None:
    case_dir, blobs_dir, logger = _make_case_env(tmp_path)
    aid = logger.next_audit_id()
    content = b"row alpha\nrow beta\nrow gamma\n"
    entry = _write_blob_and_entry(blobs_dir, audit_id=aid, content=content)
    wrong = CitedSpan(
        audit_id=aid,
        sha256_of_normalized_output=hashlib.sha256(content).hexdigest(),
        line_start=0,
        line_end=1,
        span_text="row delta",
    )
    payload = ObservationInput(
        text="row delta noted",
        cited_spans=(wrong,),
        audit_ids=(aid,),
    )
    envelope = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.SPAN_NOT_IN_LINES


def test_line_range_out_of_bounds_rejection(tmp_path: Path) -> None:
    case_dir, blobs_dir, logger = _make_case_env(tmp_path)
    aid = logger.next_audit_id()
    content = b"one\ntwo\n"
    entry = _write_blob_and_entry(blobs_dir, audit_id=aid, content=content)
    oob = CitedSpan(
        audit_id=aid,
        sha256_of_normalized_output=hashlib.sha256(content).hexdigest(),
        line_start=99,
        line_end=100,
        span_text="anything",
    )
    payload = ObservationInput(
        text="claim",
        cited_spans=(oob,),
        audit_ids=(aid,),
    )
    envelope = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.LINE_RANGE_OUT_OF_BOUNDS


def test_hallucinated_entities_ethereal_demo(tmp_path: Path) -> None:
    """Architecture §8.4 demo case: cites real Program-Files-x86 path but
    emits Program Files\\Ethereal. Entity gate catches it."""
    case_dir, blobs_dir, logger = _make_case_env(tmp_path)
    aid = logger.next_audit_id()
    content = b"C:\\Program Files (x86)\\Ethereal\\ethereal.exe last run 2024-11-12\n"
    entry = _write_blob_and_entry(blobs_dir, audit_id=aid, content=content)
    span = _cited_span_for(content, aid, span_text="C:\\Program Files (x86)\\Ethereal")
    payload = ObservationInput(
        text="Ethereal installed under C:\\Program Files\\Ethereal",
        cited_spans=(span,),
        audit_ids=(aid,),
    )
    envelope = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.HALLUCINATED_ENTITIES
    assert envelope.data.hallucinated
    assert envelope.data.suggested is not None


def test_hallucinated_entities_carries_suggested(tmp_path: Path) -> None:
    case_dir, blobs_dir, logger = _make_case_env(tmp_path)
    aid = logger.next_audit_id()
    content = b"hash 9f8e7d6c5b4a3210000000000000000000000000000000000000000000000000\n"
    entry = _write_blob_and_entry(blobs_dir, audit_id=aid, content=content)
    span = _cited_span_for(
        content,
        aid,
        span_text="9f8e7d6c5b4a3210000000000000000000000000000000000000000000000000",
    )
    payload = ObservationInput(
        text=("malware hash 1111222233334444555566667777888899990000aaaabbbbccccdddd11112222"),
        cited_spans=(span,),
        audit_ids=(aid,),
    )
    envelope = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.HALLUCINATED_ENTITIES
    suggested = envelope.data.suggested or ""
    # The hint must NAME the offending (hallucinated) entity and give the
    # actionable re-cite path, so the agent corrects by construction.
    assert "1111222233334444" in suggested
    assert "read_tool_output" in suggested


def test_agent_self_correction_after_hallucination(tmp_path: Path) -> None:
    """Architecture §8.4: agent re-submits with verbatim path; second call succeeds."""
    case_dir, blobs_dir, logger = _make_case_env(tmp_path)
    aid = logger.next_audit_id()
    content = b"C:\\Program Files (x86)\\Ethereal\\ethereal.exe last run 2024-11-12\n"
    entry = _write_blob_and_entry(blobs_dir, audit_id=aid, content=content)
    span = _cited_span_for(content, aid, span_text="C:\\Program Files (x86)\\Ethereal")

    first = ObservationInput(
        text="Ethereal installed under C:\\Program Files\\Ethereal",
        cited_spans=(span,),
        audit_ids=(aid,),
    )
    first_envelope = record_observation(
        first,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert first_envelope.data.success is False

    second = ObservationInput(
        text="Ethereal installed under C:\\Program Files (x86)\\Ethereal",
        cited_spans=(span,),
        audit_ids=(aid,),
    )
    second_envelope = record_observation(
        second,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert second_envelope.data.success is True
    assert second_envelope.data.observation_id == "O-001"


def test_stdout_path_missing_rejection(tmp_path: Path) -> None:
    """Code-reviewer I2: STDOUT_PATH_MISSING — audit entry exists but
    the stored blob has been deleted from disk."""
    case_dir, blobs_dir, logger = _make_case_env(tmp_path)
    aid = logger.next_audit_id()
    content = b"PID 4 System\n"
    entry = _write_blob_and_entry(blobs_dir, audit_id=aid, content=content)
    entry.stdout_path.unlink()
    span = CitedSpan(
        audit_id=aid,
        sha256_of_normalized_output=hashlib.sha256(content).hexdigest(),
        line_start=0,
        line_end=1,
        span_text="PID 4 System",
    )
    payload = ObservationInput(
        text="PID 4 System",
        cited_spans=(span,),
        audit_ids=(aid,),
    )
    envelope = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.STDOUT_PATH_MISSING


def test_tool_not_registered_rejection(tmp_path: Path) -> None:
    """Code-reviewer I2: TOOL_NOT_REGISTERED — audit entry's tool field
    isn't in the normalizer registry."""
    case_dir, blobs_dir, logger = _make_case_env(tmp_path)
    aid = logger.next_audit_id()
    content = b"PID 4 System\n"
    entry = _write_blob_and_entry(blobs_dir, audit_id=aid, content=content, tool="nonexistent_tool")
    span = CitedSpan(
        audit_id=aid,
        sha256_of_normalized_output=hashlib.sha256(content).hexdigest(),
        line_start=0,
        line_end=1,
        span_text="PID 4 System",
    )
    payload = ObservationInput(
        text="PID 4 System",
        cited_spans=(span,),
        audit_ids=(aid,),
    )
    envelope = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.TOOL_NOT_REGISTERED


def test_corrupted_findings_json_returns_pipeline_internal_error(tmp_path: Path) -> None:
    """Silent-failure H4: a corrupted findings.json must surface as a
    structured PIPELINE_INTERNAL_ERROR reject AND emit an audit row —
    the round-2 try/finally guard's primary justification."""
    case_dir, blobs_dir, logger = _make_case_env(tmp_path)
    (case_dir / "findings.json").write_text("not valid json{")
    aid = logger.next_audit_id()
    content = b"PID 4 System\n"
    entry = _write_blob_and_entry(blobs_dir, audit_id=aid, content=content)
    span = _cited_span_for(content, aid, span_text="PID 4 System")
    payload = ObservationInput(
        text="PID 4 System",
        cited_spans=(span,),
        audit_ids=(aid,),
    )
    envelope = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.FINDINGS_STORE_CORRUPTED
    assert (case_dir / "audit" / "findings.jsonl").exists()


def test_u2028_in_text_does_not_break_audit_write(tmp_path: Path) -> None:
    """Round-3 silent-failure C2: attacker-controlled U+2028 in
    observation text must NOT break the audit-row write. The scrubber
    replaces it with U+FFFD so append_jsonl_line accepts the row."""
    case_dir, blobs_dir, logger = _make_case_env(tmp_path)
    aid = logger.next_audit_id()
    content = b"PID 4 System\n"
    entry = _write_blob_and_entry(blobs_dir, audit_id=aid, content=content)
    span = _cited_span_for(content, aid, span_text="PID 4")
    payload = ObservationInput(
        text="PID 4 System\u2028harmful injection",
        cited_spans=(span,),
        audit_ids=(aid,),
    )
    envelope = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
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
