"""Input-model validation + corruption/failure scenarios for
``record_pivot``. Separated from the BDD acceptance file to stay
under the 400-LOC CI cap (architecture.md §14)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings.pivot import (
    PivotInput,
    PivotRejectReason,
    PivotResult,
    record_pivot,
)
from tests.integration.conftest import MODEL

_VALID_REASON = "vol3 symbol-table mismatch on netscan; pivot to windows.info to determine OS build"


def _seed(case_dir: Path, hypothesis_ids: tuple[str, ...] = ("H-001",)) -> None:
    log = case_dir / "audit" / "hypothesis.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for hid in hypothesis_ids:
        record = {
            "ts": datetime.now(UTC).isoformat(),
            "type": "form",
            "hypothesis_id": hid,
            "reason": "seed",
            "related_audit_ids": [],
            "tokens_spent": 0,
            "steps_spent": 0,
        }
        lines.append(json.dumps(record))
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Input-model validation
# ---------------------------------------------------------------------------


def test_input_rejects_malformed_from_hypothesis_id() -> None:
    """Pydantic-level rejection at construction — a typo doesn't even
    reach the pipeline."""
    with pytest.raises(ValueError, match="from_hypothesis_id must match H-NNN"):
        PivotInput(
            from_hypothesis_id="H-1",
            to_hypothesis_id="H-002",
            reason=_VALID_REASON,
            abandoning_evidence=["sift-aj-20260613-007"],
        )


def test_input_rejects_malformed_to_hypothesis_id() -> None:
    with pytest.raises(ValueError, match="to_hypothesis_id must match H-NNN"):
        PivotInput(
            from_hypothesis_id="H-001",
            to_hypothesis_id="bogus",
            reason=_VALID_REASON,
            abandoning_evidence=["sift-aj-20260613-007"],
        )


def test_input_rejects_empty_reason() -> None:
    with pytest.raises(ValueError):
        PivotInput(
            from_hypothesis_id="H-001",
            to_hypothesis_id="H-002",
            reason="",
            abandoning_evidence=["sift-aj-20260613-007"],
        )


def test_result_discriminator_rejects_success_without_pivot_id() -> None:
    with pytest.raises(ValueError, match="success=True requires pivot_id"):
        PivotResult(success=True)


def test_result_discriminator_rejects_failure_without_reason() -> None:
    with pytest.raises(ValueError, match="success=False requires reason"):
        PivotResult(success=False)


def test_result_discriminator_rejects_success_with_reason() -> None:
    with pytest.raises(ValueError, match="success=True must not carry reason"):
        PivotResult(
            success=True,
            pivot_id="P-001",
            reason=PivotRejectReason.PIPELINE_INTERNAL_ERROR,
        )


def test_result_discriminator_rejects_failure_with_pivot_id() -> None:
    with pytest.raises(ValueError, match="success=False must not carry pivot_id"):
        PivotResult(
            success=False,
            pivot_id="P-001",
            reason=PivotRejectReason.PIPELINE_INTERNAL_ERROR,
        )


# ---------------------------------------------------------------------------
# Audit-trail invariants
# ---------------------------------------------------------------------------


def test_audit_row_written_even_on_rejection(
    case_env: tuple[Path, Path, AuditLogger],
) -> None:
    """Architecture §4.4: rejections are evidence too."""
    case_dir, _, logger = case_env
    _seed(case_dir)
    payload = PivotInput(
        from_hypothesis_id="H-999",
        to_hypothesis_id="H-002",
        reason=_VALID_REASON,
        abandoning_evidence=["sift-aj-20260613-007"],
    )
    record_pivot(payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL)
    audit_log = case_dir / "audit" / "findings.jsonl"
    rows = [json.loads(line) for line in audit_log.read_text(encoding="utf-8").splitlines() if line]
    assert any(r.get("tool") == "record_pivot" for r in rows)


def test_pipeline_internal_error_on_unexpected_exception(
    case_env: tuple[Path, Path, AuditLogger],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected exception → PIPELINE_INTERNAL_ERROR; broad catch
    prevents leakage past the envelope."""
    case_dir, _, logger = case_env
    _seed(case_dir)

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise TypeError("simulated sanitizer regression")

    monkeypatch.setattr("silentwitness_mcp.findings.pivot.sanitize", _boom)
    payload = PivotInput(
        from_hypothesis_id="H-001",
        to_hypothesis_id="H-002",
        reason=_VALID_REASON,
        abandoning_evidence=["sift-aj-20260613-007"],
    )
    envelope = record_pivot(payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL)
    assert envelope.data.success is False
    assert envelope.data.reason == PivotRejectReason.PIPELINE_INTERNAL_ERROR


def test_audit_store_unwritable_when_append_fails(
    case_env: tuple[Path, Path, AuditLogger],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disk-write failure during hypothesis.jsonl append →
    AUDIT_STORE_UNWRITABLE; finally-block still writes the audit row."""
    case_dir, _, logger = case_env
    _seed(case_dir)

    real_append = __import__(
        "silentwitness_mcp.findings.pivot", fromlist=["append_jsonl_line"]
    ).append_jsonl_line

    def _raise_on_hypothesis(path: Path, line: str) -> None:
        if path.name == "hypothesis.jsonl":
            raise OSError("simulated disk full")
        real_append(path, line)

    monkeypatch.setattr("silentwitness_mcp.findings.pivot.append_jsonl_line", _raise_on_hypothesis)
    payload = PivotInput(
        from_hypothesis_id="H-001",
        to_hypothesis_id="H-002",
        reason=_VALID_REASON,
        abandoning_evidence=["sift-aj-20260613-007"],
    )
    envelope = record_pivot(payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL)
    assert envelope.data.success is False
    assert envelope.data.reason == PivotRejectReason.AUDIT_STORE_UNWRITABLE


def test_audit_write_failure_preserves_original_rejection(
    case_env: tuple[Path, Path, AuditLogger],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When audit/findings.jsonl append fails, the result rewrites to
    AUDIT_STORE_UNWRITABLE but preserves the original rejection reason
    under context.original_reason."""
    case_dir, _, logger = case_env
    _seed(case_dir)

    real_append = __import__(
        "silentwitness_mcp.findings.pivot", fromlist=["append_jsonl_line"]
    ).append_jsonl_line

    def _raise_on_findings(path: Path, line: str) -> None:
        if path.name == "findings.jsonl":
            raise OSError("simulated disk full")
        real_append(path, line)

    monkeypatch.setattr("silentwitness_mcp.findings.pivot.append_jsonl_line", _raise_on_findings)
    payload = PivotInput(
        from_hypothesis_id="H-999",
        to_hypothesis_id="H-002",
        reason=_VALID_REASON,
        abandoning_evidence=["sift-aj-20260613-007"],
    )
    envelope = record_pivot(payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL)
    assert envelope.data.success is False
    assert envelope.data.reason == PivotRejectReason.AUDIT_STORE_UNWRITABLE
    assert envelope.data.context["audit_write_failed"] is True
    assert envelope.data.context["original_reason"] == PivotRejectReason.HYPOTHESIS_NOT_FOUND.value


def test_audit_store_corrupted_when_hypothesis_jsonl_malformed(
    case_env: tuple[Path, Path, AuditLogger],
) -> None:
    """A malformed hypothesis.jsonl (non-JSON line) raises
    JSONDecodeError inside _existing_hypothesis_ids → mapped to
    AUDIT_STORE_CORRUPTED."""
    case_dir, _, logger = case_env
    log = case_dir / "audit" / "hypothesis.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("this is not json\n", encoding="utf-8")
    payload = PivotInput(
        from_hypothesis_id="H-001",
        to_hypothesis_id="H-002",
        reason=_VALID_REASON,
        abandoning_evidence=["sift-aj-20260613-007"],
    )
    envelope = record_pivot(payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL)
    assert envelope.data.success is False
    assert envelope.data.reason == PivotRejectReason.AUDIT_STORE_CORRUPTED
