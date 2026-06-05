"""Input-model validation + corruption-recovery scenarios for
``record_interpretation``. Split from
``tests/integration/test_record_interpretation.py`` to keep both files
under the 400-LOC CI cap (architecture.md §14)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from silentwitness_common.types import Confidence
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings.interpretation import (
    InterpretationInput,
    InterpretationRejectReason,
    InterpretationResult,
    record_interpretation,
)
from tests.integration.conftest import MODEL

# ---------------------------------------------------------------------------
# Input-model validation
# ---------------------------------------------------------------------------


def test_input_rejects_invalid_observation_id_shape() -> None:
    """Pydantic-level rejection at construction — the typo doesn't even
    reach the pipeline."""
    with pytest.raises(ValueError, match="observation_id must match O-NNN"):
        InterpretationInput(
            observation_id="bogus",
            text="x",
            confidence=Confidence.LOW,
            justification="brief",
            what_would_change_this_confidence="if X",
        )


def test_input_rejects_empty_text() -> None:
    with pytest.raises(ValueError):
        InterpretationInput(
            observation_id="O-001",
            text="",
            confidence=Confidence.LOW,
            justification="brief",
            what_would_change_this_confidence="if X",
        )


def test_input_rejects_empty_justification() -> None:
    with pytest.raises(ValueError):
        InterpretationInput(
            observation_id="O-001",
            text="x",
            confidence=Confidence.LOW,
            justification="",
            what_would_change_this_confidence="if X",
        )


def test_input_rejects_empty_falsification() -> None:
    with pytest.raises(ValueError):
        InterpretationInput(
            observation_id="O-001",
            text="x",
            confidence=Confidence.LOW,
            justification="brief",
            what_would_change_this_confidence="",
        )


def test_result_discriminator_rejects_success_without_id() -> None:
    """success=True requires interpretation_id (architectural seam)."""
    with pytest.raises(ValueError, match="success=True requires interpretation_id"):
        InterpretationResult(success=True)


def test_result_discriminator_rejects_failure_without_reason() -> None:
    with pytest.raises(ValueError, match="success=False requires reason"):
        InterpretationResult(success=False)


def test_result_discriminator_rejects_success_with_reason() -> None:
    """Cross-contamination direction: success=True must not carry a
    reason."""
    with pytest.raises(ValueError, match="success=True must not carry reason"):
        InterpretationResult(
            success=True,
            interpretation_id="I-001",
            reason=InterpretationRejectReason.PIPELINE_INTERNAL_ERROR,
        )


def test_result_discriminator_rejects_failure_with_interpretation_id() -> None:
    """Cross-contamination direction: success=False must not carry an
    interpretation_id."""
    with pytest.raises(ValueError, match="success=False must not carry interpretation_id"):
        InterpretationResult(
            success=False,
            interpretation_id="I-001",
            reason=InterpretationRejectReason.PIPELINE_INTERNAL_ERROR,
        )


# ---------------------------------------------------------------------------
# Corruption-recovery / audit-trail invariants
# ---------------------------------------------------------------------------


def test_corrupted_interpretations_list_returns_store_corrupted(
    case_env: tuple[Path, Path, AuditLogger],
) -> None:
    """A previous writer that left ``interpretations`` as a non-list
    must surface as FINDINGS_STORE_CORRUPTED — silent overwrite would
    erase legitimate state."""
    case_dir, _, logger = case_env
    case_dir.mkdir(parents=True, exist_ok=True)
    findings = [
        {
            "observation_id": "O-001",
            "text": "seed",
            "cited_spans": [],
            "audit_ids": [],
            "interpretations": "not a list",
        }
    ]
    (case_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
    payload = InterpretationInput(
        observation_id="O-001",
        text="x",
        confidence=Confidence.LOW,
        justification="brief",
        what_would_change_this_confidence="if X",
    )
    envelope = record_interpretation(
        payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is False
    assert envelope.data.reason == InterpretationRejectReason.FINDINGS_STORE_CORRUPTED


def test_empty_findings_file_falls_back_to_no_observations(
    case_env: tuple[Path, Path, AuditLogger],
) -> None:
    """Whitespace-only findings.json is treated as no-observations,
    leading to OBSERVATION_NOT_FOUND for any input."""
    case_dir, _, logger = case_env
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "findings.json").write_text("   \n  ", encoding="utf-8")
    payload = InterpretationInput(
        observation_id="O-001",
        text="x",
        confidence=Confidence.LOW,
        justification="brief",
        what_would_change_this_confidence="if X",
    )
    envelope = record_interpretation(
        payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is False
    assert envelope.data.reason == InterpretationRejectReason.OBSERVATION_NOT_FOUND


def test_non_dict_interpretation_entries_are_tolerated(
    case_env: tuple[Path, Path, AuditLogger],
) -> None:
    """A non-dict entry (e.g. a stray string from a hand-edit) is
    tolerated by the seq scanner; valid entries still drive allocation."""
    case_dir, _, logger = case_env
    case_dir.mkdir(parents=True, exist_ok=True)
    findings = [
        {
            "observation_id": "O-001",
            "text": "seed",
            "cited_spans": [],
            "audit_ids": [],
            "interpretations": ["not a dict", {"interpretation_id": "I-007"}],
        }
    ]
    (case_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
    payload = InterpretationInput(
        observation_id="O-001",
        text="next",
        confidence=Confidence.LOW,
        justification="brief",
        what_would_change_this_confidence="if X",
    )
    envelope = record_interpretation(
        payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is True
    assert envelope.data.interpretation_id == "I-008"


def test_missing_interpretation_id_raises_store_corrupted(
    case_env: tuple[Path, Path, AuditLogger],
) -> None:
    """An entry missing ``interpretation_id`` violates the persistence
    contract — next allocation could collide with an invisible existing
    ID. Surfaces as FINDINGS_STORE_CORRUPTED, not a silent skip."""
    case_dir, _, logger = case_env
    case_dir.mkdir(parents=True, exist_ok=True)
    findings = [
        {
            "observation_id": "O-001",
            "text": "seed",
            "cited_spans": [],
            "audit_ids": [],
            "interpretations": [{"text": "stub", "confidence": "LOW"}],
        }
    ]
    (case_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
    payload = InterpretationInput(
        observation_id="O-001",
        text="next",
        confidence=Confidence.LOW,
        justification="brief",
        what_would_change_this_confidence="if X",
    )
    envelope = record_interpretation(
        payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is False
    assert envelope.data.reason == InterpretationRejectReason.FINDINGS_STORE_CORRUPTED


def test_malformed_interpretation_id_raises_store_corrupted(
    case_env: tuple[Path, Path, AuditLogger],
) -> None:
    """A non-matching ``interpretation_id`` (wrong shape, non-string)
    also surfaces as FINDINGS_STORE_CORRUPTED — silent skip would risk
    a collision."""
    case_dir, _, logger = case_env
    case_dir.mkdir(parents=True, exist_ok=True)
    findings = [
        {
            "observation_id": "O-001",
            "text": "seed",
            "cited_spans": [],
            "audit_ids": [],
            "interpretations": [{"interpretation_id": "garbage-not-I-NNN"}],
        }
    ]
    (case_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
    payload = InterpretationInput(
        observation_id="O-001",
        text="next",
        confidence=Confidence.LOW,
        justification="brief",
        what_would_change_this_confidence="if X",
    )
    envelope = record_interpretation(
        payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is False
    assert envelope.data.reason == InterpretationRejectReason.FINDINGS_STORE_CORRUPTED


def test_audit_row_for_every_call_even_when_pipeline_corrupts(
    case_env: tuple[Path, Path, AuditLogger],
) -> None:
    """findings.json corrupted (not a list) → FINDINGS_STORE_CORRUPTED,
    audit row still written. Architecture §4.4: rejected attempts are
    evidence too."""
    case_dir, _, logger = case_env
    (case_dir / "findings.json").write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    payload = InterpretationInput(
        observation_id="O-001",
        text="x",
        confidence=Confidence.LOW,
        justification="brief",
        what_would_change_this_confidence="if X",
    )
    envelope = record_interpretation(
        payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is False
    assert envelope.data.reason == InterpretationRejectReason.FINDINGS_STORE_CORRUPTED
    audit_log = case_dir / "audit" / "findings.jsonl"
    assert audit_log.exists()
    rows = [json.loads(line) for line in audit_log.read_text(encoding="utf-8").splitlines() if line]
    assert any(row.get("tool") == "record_interpretation" for row in rows)


# ---------------------------------------------------------------------------
# Failure-path coverage — OSError, audit-write fail, generic Exception
# ---------------------------------------------------------------------------


def test_findings_store_unwritable_when_write_raises_oserror(
    case_env: tuple[Path, Path, AuditLogger],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disk-write failure → FINDINGS_STORE_UNWRITABLE; audit row still
    gets written via the finally block."""
    case_dir, _, logger = case_env
    _seed(case_dir)

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated disk full")

    monkeypatch.setattr(
        "silentwitness_mcp.findings._interpretation_store.write_json_atomic", _raise
    )
    payload = InterpretationInput(
        observation_id="O-001",
        text="x",
        confidence=Confidence.LOW,
        justification="brief",
        what_would_change_this_confidence="if X",
    )
    envelope = record_interpretation(
        payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is False
    assert envelope.data.reason == InterpretationRejectReason.FINDINGS_STORE_UNWRITABLE
    assert envelope.data.context["stage"] == "findings_write"
    assert envelope.data.context["error_type"] == "OSError"


def test_pipeline_internal_error_on_unexpected_exception(
    case_env: tuple[Path, Path, AuditLogger],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected exception (e.g. sanitizer regression raising
    TypeError) → PIPELINE_INTERNAL_ERROR; broad catch prevents leakage."""
    case_dir, _, logger = case_env
    case_dir.mkdir(parents=True, exist_ok=True)

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise TypeError("simulated sanitizer regression")

    monkeypatch.setattr("silentwitness_mcp.findings.interpretation.sanitize", _boom)
    payload = InterpretationInput(
        observation_id="O-001",
        text="x",
        confidence=Confidence.LOW,
        justification="brief",
        what_would_change_this_confidence="if X",
    )
    envelope = record_interpretation(
        payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is False
    assert envelope.data.reason == InterpretationRejectReason.PIPELINE_INTERNAL_ERROR
    assert envelope.data.context["error_type"] == "TypeError"


def test_audit_write_failure_preserves_original_rejection(
    case_env: tuple[Path, Path, AuditLogger],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audit-write failure preserves the original rejection under
    ``context.original_reason`` so the agent's self-correction loop
    still sees the real verdict."""
    case_dir, _, logger = case_env
    _seed(case_dir)
    monkeypatch.setattr(
        "silentwitness_mcp.findings.interpretation.append_jsonl_line",
        lambda *_a, **_kw: (_ for _ in ()).throw(OSError("audit fail")),
    )
    payload = InterpretationInput(
        observation_id="O-001",
        text="x",
        confidence=Confidence.HIGH,
        justification="too short",
        what_would_change_this_confidence="if X",
    )
    envelope = record_interpretation(
        payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is False
    assert envelope.data.reason == InterpretationRejectReason.FINDINGS_STORE_UNWRITABLE
    assert envelope.data.context["audit_write_failed"] is True
    assert (
        envelope.data.context["original_reason"]
        == InterpretationRejectReason.JUSTIFICATION_TOO_SHORT_FOR_CONFIDENCE.value
    )


def _seed(case_dir: Path) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "findings.json").write_text(
        json.dumps([{"observation_id": "O-001", "text": "seed"}]),
        encoding="utf-8",
    )
