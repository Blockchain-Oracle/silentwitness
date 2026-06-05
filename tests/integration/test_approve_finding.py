"""BDD acceptance scenarios for ``approve_finding`` (architecture §4.2
+ §4.9 HMAC ledger)."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

import pytest
import yaml
from pydantic import SecretStr

from silentwitness_common.types import LedgerItemType
from silentwitness_mcp.audit.ledger import (
    HMACLedger,
    InterpretationParts,
    LedgerComposer,
    ObservationParts,
)
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
    """Write findings.json containing observation O-001, its
    interpretation I-001 (nested), and a top-level finding F-001 in
    DRAFT status referencing both."""
    case_dir.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "observation_id": "O-001",
            "text": "anomalous parent chain suggests masquerading",
            "audit_ids": ["sift-aj-20260613-007"],
            "interpretations": [
                {
                    "interpretation_id": "I-001",
                    "text": "svchost rarely spawns from cmd.exe",
                    "confidence": "HIGH",
                }
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


def _seed_case_salt(case_dir: Path, salt: bytes | None = None) -> bytes:
    """Write CASE.yaml with a per-case salt — the verifier (Epic 12)
    will read from the same file so signer + verifier derive identical
    keys. Returns the salt bytes for the test to derive against."""
    salt = salt if salt is not None else secrets.token_bytes(16)
    (case_dir / "CASE.yaml").write_text(yaml.safe_dump({"salt_hex": salt.hex()}), encoding="utf-8")
    return salt


@pytest.fixture
def ledger_env(tmp_path: Path) -> tuple[Path, Path, AuditLogger]:
    """Per-test case_dir + ledger_dir + AuditLogger. The ledger_dir is
    created with mode 0o700 to satisfy the HMACLedger security floor."""
    case_dir = tmp_path / _CASE_ID
    case_dir.mkdir()
    ledger_dir = tmp_path / "ledger"
    ledger_dir.mkdir(mode=0o700)
    return case_dir, ledger_dir, AuditLogger(case_dir, examiner="aj")


# ---------------------------------------------------------------------------
# Happy path + re-verifiability
# ---------------------------------------------------------------------------


def test_approve_finding_happy_path_writes_ledger_and_flips_status(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    """Valid approval → ApproveResult(success=True, finding_id=F-001)
    + one new ledger line + findings.json flips F-001 to APPROVED
    + audit row written."""
    case_dir, ledger_dir, logger = ledger_env
    _seed_findings_for_approval(case_dir)
    _seed_case_salt(case_dir)
    payload = ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD))
    envelope = approve_finding(
        payload,
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.success is True
    assert envelope.data.success is True
    assert envelope.data.finding_id == "F-001"
    assert envelope.data.ledger_entry_ts is not None

    # findings.json status flipped DRAFT → APPROVED
    findings = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    finding = next(f for f in findings if f.get("finding_id") == "F-001")
    assert finding["status"] == "APPROVED"

    # Ledger has exactly one line
    ledger_path = ledger_dir / f"{_CASE_ID}.jsonl"
    assert ledger_path.exists()
    lines = [line for line in ledger_path.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["item_id"] == "F-001"
    assert entry["item_type"] == LedgerItemType.FINDING.value
    assert isinstance(entry["hmac"], str) and len(entry["hmac"]) == 64
    assert isinstance(entry["content_hash"], str) and len(entry["content_hash"]) == 64

    # Audit row written.
    audit_log = case_dir / "audit" / "findings.jsonl"
    audit_rows = [
        json.loads(line) for line in audit_log.read_text(encoding="utf-8").splitlines() if line
    ]
    assert any(r.get("tool") == "approve_finding" for r in audit_rows)
    # Crucially: no password / derived key surfaces in the audit row.
    for r in audit_rows:
        if r.get("tool") == "approve_finding":
            assert _VALID_PASSWORD not in json.dumps(r)


def test_ledger_entry_re_verifies_with_constant_time_compare(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    """A successful approval can be re-verified via hmac.compare_digest
    against a freshly-derived key from the same password — proving the
    signer and the offline verifier (Epic 12) produce identical bytes."""
    case_dir, ledger_dir, logger = ledger_env
    _seed_findings_for_approval(case_dir)
    salt = _seed_case_salt(case_dir)
    payload = ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD))
    approve_finding(
        payload,
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    entry = json.loads((ledger_dir / f"{_CASE_ID}.jsonl").read_text(encoding="utf-8").strip())

    # Re-derive key (verifier owns the same primitive).
    fresh_key = HMACLedger.derive_key(_VALID_PASSWORD, salt)
    findings = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    obs = next(f for f in findings if f.get("observation_id") == "O-001")
    interp = obs["interpretations"][0]
    content_bytes = LedgerComposer.finding(
        ObservationParts(text=obs["text"], audit_ids=tuple(obs["audit_ids"])),
        InterpretationParts(
            observation_id="O-001",
            text=interp["text"],
            confidence=__import__("silentwitness_common.types", fromlist=["Confidence"]).Confidence(
                interp["confidence"]
            ),
        ),
    )
    assert HMACLedger.verify_hmac(fresh_key, content_bytes, entry["hmac"]) is True


def test_tampered_ledger_entry_fails_re_verification(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    """A one-byte modification to the HMAC field MUST cause
    constant-time re-verification to fail — pins the tamper-evident
    contract."""
    case_dir, ledger_dir, logger = ledger_env
    _seed_findings_for_approval(case_dir)
    salt = _seed_case_salt(case_dir)
    approve_finding(
        ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD)),
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    entry = json.loads((ledger_dir / f"{_CASE_ID}.jsonl").read_text(encoding="utf-8").strip())
    # Flip the first hex char of the HMAC.
    tampered_hmac = ("0" if entry["hmac"][0] != "0" else "f") + entry["hmac"][1:]
    fresh_key = HMACLedger.derive_key(_VALID_PASSWORD, salt)
    findings = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    obs = next(f for f in findings if f.get("observation_id") == "O-001")
    interp = obs["interpretations"][0]
    content_bytes = LedgerComposer.finding(
        ObservationParts(text=obs["text"], audit_ids=tuple(obs["audit_ids"])),
        InterpretationParts(
            observation_id="O-001",
            text=interp["text"],
            confidence=__import__("silentwitness_common.types", fromlist=["Confidence"]).Confidence(
                interp["confidence"]
            ),
        ),
    )
    assert HMACLedger.verify_hmac(fresh_key, content_bytes, tampered_hmac) is False


# ---------------------------------------------------------------------------
# Rejections
# ---------------------------------------------------------------------------


def test_finding_not_found(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    case_dir, ledger_dir, logger = ledger_env
    _seed_findings_for_approval(case_dir)
    _seed_case_salt(case_dir)
    envelope = approve_finding(
        ApproveInput(finding_id="F-999", password=SecretStr(_VALID_PASSWORD)),
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ApproveRejectReason.FINDING_NOT_FOUND
    # Ledger NOT created.
    assert not (ledger_dir / f"{_CASE_ID}.jsonl").exists()


def test_already_approved(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    """Second approval of the same F-NNN → ALREADY_APPROVED; ledger
    NOT modified."""
    case_dir, ledger_dir, logger = ledger_env
    _seed_findings_for_approval(case_dir)
    _seed_case_salt(case_dir)
    kw = {
        "case_dir": case_dir,
        "ledger_dir": ledger_dir,
        "case_id": _CASE_ID,
        "audit_logger": logger,
        "model_used": MODEL,
    }
    approve_finding(ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD)), **kw)
    ledger_path = ledger_dir / f"{_CASE_ID}.jsonl"
    pre_size = ledger_path.stat().st_size
    envelope = approve_finding(
        ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD)), **kw
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ApproveRejectReason.ALREADY_APPROVED
    assert ledger_path.stat().st_size == pre_size  # unchanged


def test_case_salt_missing(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    """No CASE.yaml → CASE_SALT_MISSING; the cryptographic floor cannot
    be satisfied without a per-case salt."""
    case_dir, ledger_dir, logger = ledger_env
    _seed_findings_for_approval(case_dir)
    # Deliberately no _seed_case_salt(...) call.
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


def test_ledger_dir_permissions_weak(
    tmp_path: Path,
) -> None:
    """A ledger dir with mode 0o755 (looser than required 0o700) →
    LEDGER_DIR_PERMISSIONS_WEAK. HMACLedger refuses to bind."""
    case_dir = tmp_path / _CASE_ID
    case_dir.mkdir()
    ledger_dir = tmp_path / "ledger"
    ledger_dir.mkdir(mode=0o755)
    # Force the looser mode in case umask interfered.
    os.chmod(ledger_dir, 0o755)  # noqa: S103 — testing that the gate rejects this
    logger = AuditLogger(case_dir, examiner="aj")
    _seed_findings_for_approval(case_dir)
    _seed_case_salt(case_dir)
    envelope = approve_finding(
        ApproveInput(finding_id="F-001", password=SecretStr(_VALID_PASSWORD)),
        case_dir=case_dir,
        ledger_dir=ledger_dir,
        case_id=_CASE_ID,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ApproveRejectReason.LEDGER_DIR_PERMISSIONS_WEAK


def test_findings_store_corrupted_when_finding_missing_ref(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    """A finding record missing observation_id violates the persistence
    contract → FINDINGS_STORE_CORRUPTED."""
    case_dir, ledger_dir, logger = ledger_env
    case_dir.mkdir(parents=True, exist_ok=True)
    findings = [
        {"finding_id": "F-001", "status": "DRAFT"},  # no observation_id / interpretation_id
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
    assert envelope.data.success is False
    assert envelope.data.reason == ApproveRejectReason.FINDINGS_STORE_CORRUPTED


def test_findings_store_corrupted_when_observation_absent(
    ledger_env: tuple[Path, Path, AuditLogger],
) -> None:
    """Finding references O-999 which doesn't exist → CORRUPTED (the
    finding itself is malformed; observation existence is an upstream
    invariant)."""
    case_dir, ledger_dir, logger = ledger_env
    case_dir.mkdir(parents=True, exist_ok=True)
    findings = [
        {
            "finding_id": "F-001",
            "observation_id": "O-999",  # absent
            "interpretation_id": "I-999",
            "status": "DRAFT",
        }
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
    assert envelope.data.success is False
    assert envelope.data.reason == ApproveRejectReason.FINDINGS_STORE_CORRUPTED


# ---------------------------------------------------------------------------
