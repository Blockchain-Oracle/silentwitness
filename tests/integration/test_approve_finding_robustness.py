"""Input-model + failure-path scenarios for ``approve_finding``.
Separated from the BDD acceptance file to stay under the 400-LOC CI
cap (architecture.md §14)."""

from __future__ import annotations

import json
import secrets
from pathlib import Path

import pytest
import yaml
from pydantic import SecretStr

from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings.approval import (
    ApproveInput,
    ApproveRejectReason,
    ApproveResult,
    approve_finding,
)
from tests.integration.conftest import MODEL

_VALID_PASSWORD = "correct horse battery staple"  # noqa: S105 — test fixture  # pragma: allowlist secret
_CASE_ID = "case-01"


def _seed_findings_for_approval(case_dir: Path) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "observation_id": "O-001",
            "text": "anomalous parent chain",
            "audit_ids": ["sift-aj-20260613-007"],
            "interpretations": [
                {"interpretation_id": "I-001", "text": "svchost anomaly", "confidence": "HIGH"}
            ],
        },
        {
            "finding_id": "F-001",
            "observation_id": "O-001",
            "interpretation_id": "I-001",
            "status": "DRAFT",
        },
    ]
    (case_dir / "findings.json").write_text(json.dumps(records), encoding="utf-8")


def _seed_case_salt(case_dir: Path) -> bytes:
    salt = secrets.token_bytes(16)
    (case_dir / "CASE.yaml").write_text(yaml.safe_dump({"salt_hex": salt.hex()}), encoding="utf-8")
    return salt


@pytest.fixture
def ledger_env(tmp_path: Path) -> tuple[Path, Path, AuditLogger]:
    case_dir = tmp_path / _CASE_ID
    case_dir.mkdir()
    ledger_dir = tmp_path / "ledger"
    ledger_dir.mkdir(mode=0o700)
    return case_dir, ledger_dir, AuditLogger(case_dir, examiner="aj")


# ---------------------------------------------------------------------------
# Input model + discriminator
# ---------------------------------------------------------------------------


def test_input_rejects_malformed_finding_id() -> None:
    with pytest.raises(ValueError):
        ApproveInput(finding_id="F-1", password=SecretStr("x"))


def test_input_rejects_non_pattern_finding_id() -> None:
    with pytest.raises(ValueError):
        ApproveInput(finding_id="bogus", password=SecretStr("x"))


def test_result_discriminator_rejects_success_without_finding_id() -> None:
    with pytest.raises(ValueError, match="success=True requires finding_id"):
        ApproveResult(success=True)


def test_result_discriminator_rejects_failure_without_reason() -> None:
    with pytest.raises(ValueError, match="success=False requires reason"):
        ApproveResult(success=False)


def test_result_discriminator_rejects_success_with_reason() -> None:
    with pytest.raises(ValueError, match="success=True must not carry reason"):
        ApproveResult(
            success=True,
            finding_id="F-001",
            reason=ApproveRejectReason.PIPELINE_INTERNAL_ERROR,
        )


def test_password_secret_str_is_masked_in_repr() -> None:
    payload = ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD))
    text = repr(payload)
    assert _VALID_PASSWORD not in text
    assert "SecretStr" in text


# ---------------------------------------------------------------------------
# Audit row + secret leakage
# ---------------------------------------------------------------------------


def test_password_not_in_audit_row_on_rejection(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    """Even on a rejection path, the audit row must NEVER carry the
    password (CLAUDE.md non-negotiable #1)."""
    case_dir, ledger_dir, logger = ledger_env
    _seed_findings_for_approval(case_dir)
    _seed_case_salt(case_dir)
    approve_finding(
        ApproveInput(finding_id="F-999", password=SecretStr(_VALID_PASSWORD)),
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    audit_log = case_dir / "audit" / "findings.jsonl"
    raw = audit_log.read_text(encoding="utf-8")
    assert _VALID_PASSWORD not in raw


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------


def test_findings_store_corrupted_when_not_a_list(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    case_dir, ledger_dir, logger = ledger_env
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "findings.json").write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    envelope = approve_finding(
        ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD)),
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ApproveRejectReason.FINDINGS_STORE_CORRUPTED


def test_empty_findings_file_treated_as_no_findings(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    """Whitespace-only findings.json → empty findings list → any
    finding_id surfaces as FINDING_NOT_FOUND."""
    case_dir, ledger_dir, logger = ledger_env
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "findings.json").write_text("   \n   ", encoding="utf-8")
    envelope = approve_finding(
        ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD)),
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ApproveRejectReason.FINDING_NOT_FOUND


def test_findings_store_unwritable_on_findings_write_failure(
    ledger_env: tuple[Path, Path, AuditLogger],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failure to atomically rewrite findings.json after appending
    the ledger entry surfaces as FINDINGS_STORE_UNWRITABLE.

    Note: the ledger entry IS already appended at this point — the
    partial-commit state is exactly what the original_finding_id
    preservation defends against."""
    case_dir, ledger_dir, logger = ledger_env
    _seed_findings_for_approval(case_dir)
    _seed_case_salt(case_dir)

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated disk full")

    monkeypatch.setattr("silentwitness_mcp.findings.approval.write_json_atomic", _raise)
    envelope = approve_finding(
        ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD)),
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ApproveRejectReason.FINDINGS_STORE_UNWRITABLE


def test_pipeline_internal_error_on_unexpected_exception(
    ledger_env: tuple[Path, Path, AuditLogger],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected exception (e.g. ledger module raising RuntimeError)
    surfaces as PIPELINE_INTERNAL_ERROR; broad catch prevents leakage."""
    case_dir, ledger_dir, logger = ledger_env
    _seed_findings_for_approval(case_dir)
    _seed_case_salt(case_dir)

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated ledger regression")

    monkeypatch.setattr("silentwitness_mcp.findings.approval.HMACLedger.derive_key", _boom)
    envelope = approve_finding(
        ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD)),
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ApproveRejectReason.PIPELINE_INTERNAL_ERROR


def test_audit_write_failure_preserves_original_finding_id(
    ledger_env: tuple[Path, Path, AuditLogger],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Success path: ledger appended + findings.json flipped, but
    audit-row append fails → context.original_finding_id MUST survive
    so the caller knows about the partial commit and does not retry."""
    case_dir, ledger_dir, logger = ledger_env
    _seed_findings_for_approval(case_dir)
    _seed_case_salt(case_dir)

    real_append = __import__(
        "silentwitness_mcp.findings.approval", fromlist=["append_jsonl_line"]
    ).append_jsonl_line

    def _raise_on_findings_log(path: Path, line: str, **kwargs: object) -> None:
        if path.name == "findings.jsonl":
            raise OSError("simulated audit fail")
        real_append(path, line, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        "silentwitness_mcp.findings.approval.append_jsonl_line", _raise_on_findings_log
    )
    envelope = approve_finding(
        ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD)),
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ApproveRejectReason.FINDINGS_STORE_UNWRITABLE
    assert envelope.data.context["audit_write_failed"] is True
    assert envelope.data.context["original_finding_id"] == "F-001"
    assert envelope.data.context["original_success"] is True


# ---------------------------------------------------------------------------
# Scanner / read helpers
# ---------------------------------------------------------------------------


def test_no_findings_file_treated_as_empty(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    """A case_dir without findings.json → empty findings list → any
    finding_id surfaces as FINDING_NOT_FOUND. The salt and ledger are
    moot at that point — the early-return fires before they're touched."""
    case_dir, ledger_dir, logger = ledger_env
    # Deliberately no _seed_findings_for_approval(...)
    envelope = approve_finding(
        ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD)),
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ApproveRejectReason.FINDING_NOT_FOUND


def test_non_dict_findings_entries_are_tolerated(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    """Stray non-dict entries in findings.json are skipped by the
    locators; valid records still drive resolution."""
    case_dir, ledger_dir, logger = ledger_env
    case_dir.mkdir(parents=True, exist_ok=True)
    findings: list[object] = [
        "stray string",
        {
            "observation_id": "O-001",
            "text": "x",
            "audit_ids": [],
            "interpretations": [{"interpretation_id": "I-001", "text": "x", "confidence": "LOW"}],
        },
        {
            "finding_id": "F-001",
            "observation_id": "O-001",
            "interpretation_id": "I-001",
            "status": "DRAFT",
        },
    ]
    (case_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
    _seed_case_salt(case_dir)
    envelope = approve_finding(
        ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD)),
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.data.success is True


def test_case_salt_yaml_non_dict_treated_as_missing(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    """A CASE.yaml whose top level is not a mapping → CASE_SALT_MISSING
    rather than crashing — defends against a hand-edit that turns the
    file into a list or a scalar."""
    case_dir, ledger_dir, logger = ledger_env
    _seed_findings_for_approval(case_dir)
    (case_dir / "CASE.yaml").write_text(yaml.safe_dump([1, 2, 3]), encoding="utf-8")
    envelope = approve_finding(
        ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD)),
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ApproveRejectReason.CASE_SALT_MISSING


def test_case_salt_yaml_missing_salt_hex_key(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    """CASE.yaml exists but lacks the ``salt_hex`` key → CASE_SALT_MISSING."""
    case_dir, ledger_dir, logger = ledger_env
    _seed_findings_for_approval(case_dir)
    (case_dir / "CASE.yaml").write_text(yaml.safe_dump({"other": "key"}), encoding="utf-8")
    envelope = approve_finding(
        ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD)),
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ApproveRejectReason.CASE_SALT_MISSING
