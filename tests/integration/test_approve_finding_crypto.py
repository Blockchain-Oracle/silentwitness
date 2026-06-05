"""Crypto-path scenarios for ``approve_finding``: case-salt
malformation discrimination + zero_key finally-block contract. Split
from ``test_approve_finding_robustness.py`` to stay under the
400-LOC CI cap."""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import SecretStr

from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings.approval import (
    ApproveInput,
    ApproveRejectReason,
    approve_finding,
)
from tests.integration.conftest import MODEL

_VALID_PASSWORD = "correct horse battery staple"  # noqa: S105 # pragma: allowlist secret
_CASE_ID = "case-01"


def _seed_findings_for_approval(case_dir: Path) -> None:
    import json

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
# CASE.yaml malformation discrimination
# ---------------------------------------------------------------------------


def test_case_salt_malformed_yaml(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    """Bad YAML in CASE.yaml → CASE_SALT_MALFORMED, not the more
    generic FINDINGS_STORE_CORRUPTED. An operator reading the audit
    row needs to know which file to inspect."""
    case_dir, ledger_dir, logger = ledger_env
    _seed_findings_for_approval(case_dir)
    (case_dir / "CASE.yaml").write_text(": : not valid yaml : :", encoding="utf-8")
    envelope = approve_finding(
        ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD)),
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ApproveRejectReason.CASE_SALT_MALFORMED


def test_case_salt_malformed_hex(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    """salt_hex that is not valid hex → CASE_SALT_MALFORMED."""
    case_dir, ledger_dir, logger = ledger_env
    _seed_findings_for_approval(case_dir)
    (case_dir / "CASE.yaml").write_text(
        yaml.safe_dump({"salt_hex": "not-a-hex-string"}), encoding="utf-8"
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
    assert envelope.data.reason == ApproveRejectReason.CASE_SALT_MALFORMED


# ---------------------------------------------------------------------------
# zero_key finally-block contract
# ---------------------------------------------------------------------------


def _attach_zero_key_counter(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Replace HMACLedger.zero_key with a counter that still wipes the
    buffer. Returns the list — len(list) == call count."""
    from silentwitness_mcp.findings.approval import HMACLedger

    counter: list[int] = []
    original = HMACLedger.zero_key

    def _counting(buf: bytearray) -> None:
        counter.append(1)
        original(buf)

    monkeypatch.setattr(
        "silentwitness_mcp.findings.approval.HMACLedger.zero_key",
        staticmethod(_counting),
    )
    return counter


def test_derived_key_is_zeroed_on_success(
    ledger_env: tuple[Path, Path, AuditLogger],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """zero_key MUST fire exactly once on the happy path."""
    case_dir, ledger_dir, logger = ledger_env
    _seed_findings_for_approval(case_dir)
    _seed_case_salt(case_dir)
    counter = _attach_zero_key_counter(monkeypatch)
    envelope = approve_finding(
        ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD)),
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.data.success is True
    assert len(counter) == 1


def test_derived_key_is_zeroed_on_ledger_failure(
    ledger_env: tuple[Path, Path, AuditLogger],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """zero_key MUST fire even when ledger.append raises. This is the
    entire defence — break the finally and a derived key survives in
    a heap-readable bytearray after the function returns."""
    case_dir, ledger_dir, logger = ledger_env
    _seed_findings_for_approval(case_dir)
    _seed_case_salt(case_dir)
    counter = _attach_zero_key_counter(monkeypatch)

    def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("simulated ledger append failure")

    monkeypatch.setattr(
        "silentwitness_mcp.findings.approval.HMACLedger.append", lambda *a, **kw: _boom()
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
    assert envelope.data.reason == ApproveRejectReason.PIPELINE_INTERNAL_ERROR
    assert len(counter) == 1
