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


def test_corrupted_interpretation_entries_in_existing_findings(
    case_env: tuple[Path, Path, AuditLogger],
) -> None:
    """Garbage interpretation entries (non-dict, non-string ID, non-
    matching pattern) must be filtered by the seq scanner so allocation
    still proceeds with the highest VALID seq. Defends against a
    partial-write race or hand-edited file."""
    case_dir, _, logger = case_env
    case_dir.mkdir(parents=True, exist_ok=True)
    findings = [
        {
            "observation_id": "O-001",
            "text": "seed",
            "cited_spans": [],
            "audit_ids": [],
            "interpretations": [
                "not a dict",
                {"interpretation_id": 42},
                {"interpretation_id": "garbage-not-I-NNN"},
                {"interpretation_id": "I-007"},
            ],
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
