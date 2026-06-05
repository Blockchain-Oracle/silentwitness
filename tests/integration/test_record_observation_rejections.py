"""Rejection-path tests for ``record_observation`` (split for 400-LOC discipline).

One test per ObservationRejectReason — closes the BDD spec criterion
that every reject reason is exercised end-to-end."""

from __future__ import annotations

import hashlib
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
    result = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert result.success is False
    assert result.reason == ObservationRejectReason.AUDIT_ID_NOT_FOUND
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
    result = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert result.success is False
    assert result.reason == ObservationRejectReason.OUTPUT_HASH_MISMATCH
    assert "expected_sha256" in result.context
    assert "actual_sha256" in result.context


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
    result = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert result.success is False
    assert result.reason == ObservationRejectReason.SPAN_NOT_IN_LINES


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
    result = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert result.success is False
    assert result.reason == ObservationRejectReason.LINE_RANGE_OUT_OF_BOUNDS


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
    result = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert result.success is False
    assert result.reason == ObservationRejectReason.HALLUCINATED_ENTITIES
    assert result.hallucinated
    assert result.suggested is not None


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
    result = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert result.success is False
    assert result.reason == ObservationRejectReason.HALLUCINATED_ENTITIES
    assert "9f8e7d6c" in (result.suggested or "")


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
    first_result = record_observation(
        first,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert first_result.success is False

    second = ObservationInput(
        text="Ethereal installed under C:\\Program Files (x86)\\Ethereal",
        cited_spans=(span,),
        audit_ids=(aid,),
    )
    second_result = record_observation(
        second,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=_MODEL,
    )
    assert second_result.success is True
    assert second_result.observation_id == "O-001"
