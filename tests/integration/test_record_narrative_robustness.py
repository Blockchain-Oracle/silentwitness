"""Input-model + corruption / failure scenarios for ``record_narrative``.
Separated from the BDD acceptance file to stay under the 400-LOC CI
cap (architecture.md §14)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from silentwitness_common.types import ReportSection
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings.narrative import (
    AttackChainStep,
    NarrativeInput,
    NarrativeRejectReason,
    NarrativeResult,
    record_narrative,
)
from tests.integration.conftest import MODEL

_VALID_HYPOTHESIS = (
    "if wardriving, expect promiscuous-mode capture tool plus intercepted credentials"
)


def _seed_observations(case_dir: Path, observation_ids: tuple[str, ...] = ("O-001",)) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    records = [
        {"observation_id": oid, "text": "seed", "cited_spans": [], "audit_ids": []}
        for oid in observation_ids
    ]
    (case_dir / "findings.json").write_text(json.dumps(records), encoding="utf-8")


def _seed_pivots(case_dir: Path, pivot_ids: tuple[str, ...]) -> None:
    log = case_dir / "audit" / "hypothesis.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for pid in pivot_ids:
        record = {
            "ts": datetime.now(UTC).isoformat(),
            "type": "pivot",
            "hypothesis_id": "H-001",
            "pivot_id": pid,
            "to_hypothesis_id": "H-002",
            "reason": "seed",
            "related_audit_ids": [],
            "tokens_spent": 0,
            "steps_spent": 0,
        }
        lines.append(json.dumps(record))
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _valid_payload(**overrides: object) -> NarrativeInput:
    base = {
        "section": ReportSection.FINDINGS,
        "text": "text",
        "initial_hypothesis": _VALID_HYPOTHESIS,
        "attack_chain": (AttackChainStep(observation_id="O-001"),),
    }
    base.update(overrides)
    return NarrativeInput(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Input-model validation
# ---------------------------------------------------------------------------


def test_input_rejects_malformed_observation_id_in_attack_chain() -> None:
    with pytest.raises(ValueError, match="observation_id must match O-NNN"):
        AttackChainStep(observation_id="O-1")


def test_input_rejects_malformed_pivot_id() -> None:
    with pytest.raises(ValueError, match="pivot id must match P-NNN"):
        NarrativeInput(
            section=ReportSection.FINDINGS,
            text="text",
            initial_hypothesis=_VALID_HYPOTHESIS,
            attack_chain=(AttackChainStep(observation_id="O-001"),),
            pivots=("P-1",),
        )


# ---------------------------------------------------------------------------
# Result discriminator
# ---------------------------------------------------------------------------


def test_result_discriminator_rejects_success_without_narrative_id() -> None:
    with pytest.raises(ValueError, match="success=True requires narrative_id"):
        NarrativeResult(success=True)


def test_result_discriminator_rejects_failure_without_reason() -> None:
    with pytest.raises(ValueError, match="success=False requires reason"):
        NarrativeResult(success=False)


def test_result_discriminator_rejects_success_with_reason() -> None:
    with pytest.raises(ValueError, match="success=True must not carry reason"):
        NarrativeResult(
            success=True,
            narrative_id="N-001",
            reason=NarrativeRejectReason.PIPELINE_INTERNAL_ERROR,
        )


def test_result_discriminator_rejects_failure_with_narrative_id() -> None:
    with pytest.raises(ValueError, match="success=False must not carry narrative_id"):
        NarrativeResult(
            success=False,
            narrative_id="N-001",
            reason=NarrativeRejectReason.PIPELINE_INTERNAL_ERROR,
        )


# ---------------------------------------------------------------------------
# Multiple narratives + global N-NNN sequence
# ---------------------------------------------------------------------------


def test_multiple_narratives_allocate_n001_then_n002(
    case_env: tuple[Path, AuditLogger],
) -> None:
    case_dir, logger = case_env
    _seed_observations(case_dir, ("O-001",))
    kw = {"case_dir": case_dir, "audit_logger": logger, "model_used": MODEL}
    e1 = record_narrative(_valid_payload(), **kw)
    e2 = record_narrative(_valid_payload(text="second"), **kw)
    assert e1.data.narrative_id == "N-001"
    assert e2.data.narrative_id == "N-002"


def test_narrative_id_is_case_wide_across_sections(
    case_env: tuple[Path, AuditLogger],
) -> None:
    """The N-NNN sequence is case-wide — a critic citing N-005 is
    unambiguous regardless of section."""
    case_dir, logger = case_env
    _seed_observations(case_dir, ("O-001",))
    kw = {"case_dir": case_dir, "audit_logger": logger, "model_used": MODEL}
    e1 = record_narrative(_valid_payload(section=ReportSection.FINDINGS), **kw)
    e2 = record_narrative(_valid_payload(section=ReportSection.TIMELINE), **kw)
    assert e1.data.narrative_id == "N-001"
    assert e2.data.narrative_id == "N-002"


def test_pivot_scanner_tolerates_whitespace_missing_keys_and_non_dict(
    case_env: tuple[Path, AuditLogger],
) -> None:
    """The pivot-id scanner tolerates blank lines, non-dict scalars,
    and dicts missing the ``pivot_id`` key; valid pivot rows still
    drive the existence check."""
    case_dir, logger = case_env
    _seed_observations(case_dir, ("O-001",))
    log = case_dir / "audit" / "hypothesis.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        "\n   \n"  # blank + whitespace lines
        '"a stray string"\n'  # non-dict
        + json.dumps({"type": "form", "hypothesis_id": "H-001"})
        + "\n"  # missing pivot_id
        + json.dumps(
            {  # valid pivot row
                "ts": datetime.now(UTC).isoformat(),
                "type": "pivot",
                "hypothesis_id": "H-001",
                "pivot_id": "P-001",
                "to_hypothesis_id": "H-002",
                "reason": "ok",
                "related_audit_ids": [],
                "tokens_spent": 0,
                "steps_spent": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    payload = _valid_payload(pivots=("P-001",))
    envelope = record_narrative(payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL)
    assert envelope.data.success is True


# ---------------------------------------------------------------------------
# Corruption-recovery scenarios
# ---------------------------------------------------------------------------


def test_audit_store_corrupted_when_findings_json_not_a_list(
    case_env: tuple[Path, AuditLogger],
) -> None:
    """A findings.json whose top level is not a JSON array → AUDIT_
    STORE_CORRUPTED. Audit row still written (architecture §4.4)."""
    case_dir, logger = case_env
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "findings.json").write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    payload = _valid_payload()
    envelope = record_narrative(payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL)
    assert envelope.data.success is False
    assert envelope.data.reason == NarrativeRejectReason.AUDIT_STORE_CORRUPTED
    audit_log = case_dir / "audit" / "findings.jsonl"
    assert audit_log.exists()


def test_audit_store_corrupted_when_observation_id_is_non_string(
    case_env: tuple[Path, AuditLogger],
) -> None:
    """A previously-persisted observation with a non-string
    observation_id violates the contract → AUDIT_STORE_CORRUPTED."""
    case_dir, logger = case_env
    case_dir.mkdir(parents=True, exist_ok=True)
    findings = [{"observation_id": 42, "text": "broken"}]
    (case_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
    payload = _valid_payload()
    envelope = record_narrative(payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL)
    assert envelope.data.success is False
    assert envelope.data.reason == NarrativeRejectReason.AUDIT_STORE_CORRUPTED


def test_audit_store_corrupted_when_narrative_id_malformed(
    case_env: tuple[Path, AuditLogger],
) -> None:
    """A persisted narrative entry whose ``narrative_id`` doesn't match
    N-NNN violates the contract; silent skip would risk a collision."""
    case_dir, logger = case_env
    case_dir.mkdir(parents=True, exist_ok=True)
    findings = [
        {"observation_id": "O-001", "text": "seed"},
        {"narrative_id": "garbage-not-N-NNN", "text": "bad"},
    ]
    (case_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
    payload = _valid_payload()
    envelope = record_narrative(payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL)
    assert envelope.data.success is False
    assert envelope.data.reason == NarrativeRejectReason.AUDIT_STORE_CORRUPTED


def test_corrupted_pivot_log_with_non_string_pivot_id(
    case_env: tuple[Path, AuditLogger],
) -> None:
    """Citing a pivot when hypothesis.jsonl has a malformed pivot_id
    surfaces as AUDIT_STORE_CORRUPTED, not silently as PIVOT_NOT_FOUND."""
    case_dir, logger = case_env
    _seed_observations(case_dir, ("O-001",))
    log = case_dir / "audit" / "hypothesis.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps({"type": "pivot", "pivot_id": 42}) + "\n", encoding="utf-8")
    payload = _valid_payload(pivots=("P-001",))
    envelope = record_narrative(payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL)
    assert envelope.data.success is False
    assert envelope.data.reason == NarrativeRejectReason.AUDIT_STORE_CORRUPTED


# ---------------------------------------------------------------------------
# Failure paths — OSError, generic Exception, audit-write preservation
# ---------------------------------------------------------------------------


def test_audit_store_unwritable_when_findings_write_raises(
    case_env: tuple[Path, AuditLogger],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disk-write failure during findings.json allocation →
    AUDIT_STORE_UNWRITABLE."""
    case_dir, logger = case_env
    _seed_observations(case_dir, ("O-001",))

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated disk full")

    monkeypatch.setattr("silentwitness_mcp.findings._narrative_store.write_json_atomic", _raise)
    payload = _valid_payload()
    envelope = record_narrative(payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL)
    assert envelope.data.success is False
    assert envelope.data.reason == NarrativeRejectReason.AUDIT_STORE_UNWRITABLE


def test_pipeline_internal_error_on_unexpected_exception(
    case_env: tuple[Path, AuditLogger],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected exception (TypeError from a sanitizer regression) →
    PIPELINE_INTERNAL_ERROR; broad catch prevents leakage."""
    case_dir, logger = case_env
    _seed_observations(case_dir, ("O-001",))

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise TypeError("simulated sanitizer regression")

    monkeypatch.setattr("silentwitness_mcp.findings.narrative.sanitize", _boom)
    payload = _valid_payload()
    envelope = record_narrative(payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL)
    assert envelope.data.success is False
    assert envelope.data.reason == NarrativeRejectReason.PIPELINE_INTERNAL_ERROR


def test_audit_write_failure_preserves_original_rejection(
    case_env: tuple[Path, AuditLogger],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When audit/findings.jsonl append fails, the original rejection
    (SECTION_NOT_AGENT_WRITABLE) survives under context.original_reason
    so the agent's self-correction loop still sees the real verdict."""
    case_dir, logger = case_env
    _seed_observations(case_dir, ("O-001",))

    monkeypatch.setattr(
        "silentwitness_mcp.findings.narrative.append_chained_jsonl",
        lambda *_a, **_kw: (_ for _ in ()).throw(OSError("audit fail")),
    )
    payload = _valid_payload(section=ReportSection.RECOMMENDATIONS)
    envelope = record_narrative(payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL)
    assert envelope.data.success is False
    assert envelope.data.reason == NarrativeRejectReason.AUDIT_STORE_UNWRITABLE
    assert envelope.data.context["audit_write_failed"] is True
    assert (
        envelope.data.context["original_reason"]
        == NarrativeRejectReason.SECTION_NOT_AGENT_WRITABLE.value
    )


def test_audit_row_written_on_rejection(
    case_env: tuple[Path, AuditLogger],
) -> None:
    """Architecture §4.4: rejections are evidence — audit row written
    even on SECTION_NOT_AGENT_WRITABLE."""
    case_dir, logger = case_env
    _seed_observations(case_dir, ("O-001",))
    payload = _valid_payload(section=ReportSection.RECOMMENDATIONS)
    record_narrative(payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL)
    audit_log = case_dir / "audit" / "findings.jsonl"
    rows = [json.loads(line) for line in audit_log.read_text(encoding="utf-8").splitlines() if line]
    assert any(r.get("tool") == "record_narrative" for r in rows)


# ---------------------------------------------------------------------------
# Scanner tolerance
# ---------------------------------------------------------------------------


def test_scanner_tolerates_non_dict_findings_entries(
    case_env: tuple[Path, AuditLogger],
) -> None:
    """Hand-edited findings.json with stray non-dict entries — the
    scanner skips them and allocation proceeds."""
    case_dir, logger = case_env
    case_dir.mkdir(parents=True, exist_ok=True)
    findings = [
        "stray string",
        {"observation_id": "O-001", "text": "seed"},
    ]
    (case_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
    payload = _valid_payload()
    envelope = record_narrative(payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL)
    assert envelope.data.success is True


def test_empty_findings_file_treated_as_no_observations(
    case_env: tuple[Path, AuditLogger],
) -> None:
    """Whitespace-only findings.json → empty observation set, so any
    attack_chain reference fails OBSERVATION_NOT_FOUND."""
    case_dir, logger = case_env
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "findings.json").write_text("   \n   ", encoding="utf-8")
    payload = _valid_payload()
    envelope = record_narrative(payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL)
    assert envelope.data.success is False
    assert envelope.data.reason == NarrativeRejectReason.OBSERVATION_NOT_FOUND
