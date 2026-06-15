"""``approve_finding`` — password-gated HMAC ledger transition (architecture
§4.2 + §4.9). Pipeline under :func:`findings_lock`: read F-NNN → DRAFT check →
CASE.yaml salt → HMACLedger bind → PBKDF2-SHA256 → HMAC → append → flip status →
atomic rename → zero key → audit row. Audit row writes on EVERY path. Zeroing is
honest but partial: ``SecretStr.get_secret_value()`` and ``HMACLedger.derive_key``
both return immutable copies we cannot wipe; only the bytearray buffer fed to
``ledger.append`` is zeroed. Password / derived key NEVER reach the audit row."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from silentwitness_common.atomic_io import write_json_atomic
from silentwitness_common.types import (
    AuditEntry,
    Confidence,
    LedgerItemType,
    ToolResponse,
)
from silentwitness_mcp.audit.chain import append_chained_jsonl_line
from silentwitness_mcp.audit.ledger import (
    HMACLedger,
    InterpretationParts,
    LedgerComposer,
    LedgerError,
    LedgerKeyError,
    LedgerSecurityError,
    ObservationParts,
)
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings._approval_store import (
    CaseSaltMalformedError,
    findings_lock,
    load_case_salt,
    locate_finding,
    locate_interpretation,
    locate_observation,
    read_findings,
)
from silentwitness_mcp.findings._scrub import scrub_line_terminators


class ApproveRejectReason(StrEnum):
    """Closed rejection-code set for ``approve_finding``. Every value here
    is produced by a code path in this module and asserted by a test.
    The offline verifier (Epic 12) will extend this enum with its own
    re-check codes when it lands — keeping the signer-side set minimal
    until then per CLAUDE.md non-negotiables (no premature interfaces)."""

    FINDING_NOT_FOUND = "FINDING_NOT_FOUND"
    ALREADY_APPROVED = "ALREADY_APPROVED"
    LEDGER_DIR_PERMISSIONS_WEAK = "LEDGER_DIR_PERMISSIONS_WEAK"
    CASE_SALT_MISSING = "CASE_SALT_MISSING"
    CASE_SALT_MALFORMED = "CASE_SALT_MALFORMED"
    FINDINGS_STORE_CORRUPTED = "FINDINGS_STORE_CORRUPTED"
    FINDINGS_STORE_UNWRITABLE = "FINDINGS_STORE_UNWRITABLE"
    LEDGER_COMMITTED_FINDINGS_UNFLIPPED = "LEDGER_COMMITTED_FINDINGS_UNFLIPPED"
    PIPELINE_INTERNAL_ERROR = "PIPELINE_INTERNAL_ERROR"


_RESULT_CONFIG = ConfigDict(frozen=True, extra="forbid")
_FINDING_ID_PATTERN: Final = "^F-\\d{3,}$"
_FINDINGS_FILENAME: Final = "findings.json"
_STATUS_APPROVED: Final = "APPROVED"


class ApproveInput(BaseModel):
    """``password`` is :class:`SecretStr` (masked in repr/dump). The
    ``get_secret_value()`` call happens exactly once inside
    :func:`approve_finding`."""

    model_config = _RESULT_CONFIG

    finding_id: str = Field(min_length=1, pattern=_FINDING_ID_PATTERN)
    password: SecretStr


class ApproveResult(BaseModel):
    """Discriminator validator forbids illegal combinations of
    (success, finding_id, reason, ledger_entry_ts)."""

    model_config = _RESULT_CONFIG

    success: bool
    finding_id: str | None = Field(default=None, pattern=_FINDING_ID_PATTERN)
    ledger_entry_ts: datetime | None = None
    reason: ApproveRejectReason | None = None
    context: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_tag(self) -> ApproveResult:
        if self.success:
            if self.finding_id is None:
                raise ValueError("success=True requires finding_id")
            if self.ledger_entry_ts is None:
                raise ValueError("success=True requires ledger_entry_ts")
            if self.reason is not None:
                raise ValueError("success=True must not carry reason")
        else:
            if self.reason is None:
                raise ValueError("success=False requires reason")
            if self.ledger_entry_ts is not None:
                raise ValueError("success=False must not carry ledger_entry_ts")
        return self


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def approve_finding(
    payload: ApproveInput,
    *,
    case_dir: Path,
    ledger_dir: Path,
    case_id: str,
    audit_logger: AuditLogger,
    model_used: str,
) -> ToolResponse[ApproveResult]:
    """Examiner-only ledger transition. CLI is the only entrypoint;
    LLM cannot reach this tool (architecture §6.2 deny rule)."""
    findings_log = case_dir / "audit" / "findings.jsonl"
    start = time.monotonic()
    pre_audit_id: str | None = None
    result: ApproveResult | None = None
    try:
        pre_audit_id = audit_logger.next_audit_id()
        # findings_lock serialises writers across processes.
        with findings_lock(case_dir):
            result = _run_pipeline(
                payload,
                case_dir=case_dir,
                ledger_dir=ledger_dir,
                case_id=case_id,
                examiner=audit_logger.examiner,
            )
    except LedgerSecurityError:
        result = ApproveResult(
            success=False,
            reason=ApproveRejectReason.LEDGER_DIR_PERMISSIONS_WEAK,
            context={"ledger_dir": str(ledger_dir)},
        )
    except LedgerKeyError as exc:
        # PBKDF2 floor breach surfaces as PIPELINE_INTERNAL_ERROR — must
        # not mask as findings corruption (would hide the crypto weakness).
        result = ApproveResult(
            success=False,
            reason=ApproveRejectReason.PIPELINE_INTERNAL_ERROR,
            context={"stage": "key_derivation", "error_type": type(exc).__name__},
        )
    except LedgerError as exc:
        result = ApproveResult(
            success=False,
            reason=ApproveRejectReason.PIPELINE_INTERNAL_ERROR,
            context={"stage": "ledger", "error_type": type(exc).__name__},
        )
    except CaseSaltMalformedError as exc:
        result = ApproveResult(
            success=False,
            reason=ApproveRejectReason.CASE_SALT_MALFORMED,
            context={"case_dir": str(case_dir), "error_type": type(exc).__name__},
        )
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        # Caught AFTER typed ledger errors (LedgerKeyError ⊂ ValueError).
        result = ApproveResult(
            success=False,
            reason=ApproveRejectReason.FINDINGS_STORE_CORRUPTED,
            context={"stage": "findings_read", "error_type": type(exc).__name__},
        )
    except OSError as exc:
        result = ApproveResult(
            success=False,
            reason=ApproveRejectReason.FINDINGS_STORE_UNWRITABLE,
            context={"stage": "findings_write", "error_type": type(exc).__name__},
        )
    except Exception as exc:
        result = ApproveResult(
            success=False,
            reason=ApproveRejectReason.PIPELINE_INTERNAL_ERROR,
            context={"stage": "pipeline", "error_type": type(exc).__name__},
        )
    finally:
        if pre_audit_id is None:
            pre_audit_id = audit_logger.next_audit_id()
        if result is None:  # pragma: no cover — defensive
            result = ApproveResult(
                success=False,
                reason=ApproveRejectReason.PIPELINE_INTERNAL_ERROR,
                context={"stage": "pipeline", "error_type": "unknown"},
            )
        try:
            _write_audit_row(
                result,
                payload=payload,
                findings_log=findings_log,
                case_dir=case_dir,
                audit_id=pre_audit_id,
                examiner=audit_logger.examiner,
                start=start,
                model_used=model_used,
            )
        except Exception as audit_exc:
            preserved = {
                "stage": "audit_write",
                "error_type": type(audit_exc).__name__,
                "audit_write_failed": True,
                "original_reason": (result.reason.value if result.reason else None),
                "original_context": dict(result.context),
                "original_finding_id": result.finding_id,
                "original_success": result.success,
            }
            result = ApproveResult(
                success=False,
                reason=ApproveRejectReason.FINDINGS_STORE_UNWRITABLE,
                context=preserved,
            )
    return _wrap_envelope(result, audit_id=pre_audit_id, examiner=audit_logger.examiner)


def _run_pipeline(
    payload: ApproveInput,
    *,
    case_dir: Path,
    ledger_dir: Path,
    case_id: str,
    examiner: str,
) -> ApproveResult:
    findings = read_findings(case_dir)
    located = locate_finding(findings, payload.finding_id)
    if located is None:
        return ApproveResult(
            success=False,
            reason=ApproveRejectReason.FINDING_NOT_FOUND,
            context={"finding_id": payload.finding_id},
        )
    finding_idx, finding = located

    if finding.get("status") == _STATUS_APPROVED:
        return ApproveResult(
            success=False,
            reason=ApproveRejectReason.ALREADY_APPROVED,
            context={"finding_id": payload.finding_id},
        )

    obs_id = finding.get("observation_id")
    interp_id = finding.get("interpretation_id")
    if not isinstance(obs_id, str) or not isinstance(interp_id, str):
        return ApproveResult(
            success=False,
            reason=ApproveRejectReason.FINDINGS_STORE_CORRUPTED,
            context={"finding_id": payload.finding_id, "missing": "obs_or_interp_id"},
        )
    obs_record = locate_observation(findings, obs_id)
    interp_record = locate_interpretation(findings, interp_id)
    if obs_record is None or interp_record is None:
        return ApproveResult(
            success=False,
            reason=ApproveRejectReason.FINDINGS_STORE_CORRUPTED,
            context={
                "finding_id": payload.finding_id,
                "observation_found": obs_record is not None,
                "interpretation_found": interp_record is not None,
            },
        )

    salt = load_case_salt(case_dir)
    if salt is None:
        return ApproveResult(
            success=False,
            reason=ApproveRejectReason.CASE_SALT_MISSING,
            context={"case_dir": str(case_dir)},
        )

    ledger = HMACLedger(ledger_dir=ledger_dir, case_id=case_id)
    obs_parts = ObservationParts(
        text=obs_record.get("text", ""),
        audit_ids=tuple(obs_record.get("audit_ids", []) or []),
    )
    interp_parts = InterpretationParts(
        observation_id=obs_id,
        text=interp_record.get("text", ""),
        confidence=Confidence(interp_record.get("confidence", "LOW")),
    )
    content_bytes = LedgerComposer.finding(obs_parts, interp_parts)

    # derive_key inside try so the finally always runs zero_key.
    derived_key: bytearray | None = None
    try:
        derived_key = bytearray(HMACLedger.derive_key(payload.password.get_secret_value(), salt))
        entry = ledger.append(
            bytes(derived_key),
            payload.finding_id,
            LedgerItemType.FINDING,
            content_bytes,
            examiner=examiner,
        )
    finally:
        if derived_key is not None:
            HMACLedger.zero_key(derived_key)

    # Partial-commit fence: surface content_hash on write fail.
    findings[finding_idx] = {**finding, "status": _STATUS_APPROVED}
    try:
        write_json_atomic(case_dir / _FINDINGS_FILENAME, findings)
    except OSError as exc:
        return ApproveResult(
            success=False,
            reason=ApproveRejectReason.LEDGER_COMMITTED_FINDINGS_UNFLIPPED,
            context={
                "finding_id": payload.finding_id,
                "ledger_content_hash": entry.content_hash,
                "ledger_entry_ts": entry.ts.isoformat(),
                "stage": "findings_flip",
                "error_type": type(exc).__name__,
            },
        )

    return ApproveResult(
        success=True,
        finding_id=payload.finding_id,
        ledger_entry_ts=entry.ts,
    )


# ---------------------------------------------------------------------------
# Audit row + envelope
# ---------------------------------------------------------------------------


def _write_audit_row(
    result: ApproveResult,
    *,
    payload: ApproveInput,
    findings_log: Path,
    case_dir: Path,
    audit_id: str,
    examiner: str,
    start: float,
    model_used: str,
) -> None:
    """Canonical :class:`AuditEntry` (§4.4). Audit row NEVER carries the
    password or derived-key bytes."""
    elapsed_ms = (time.monotonic() - start) * 1000.0
    summary_json = result.model_dump_json()
    artefact_path = (
        case_dir / _FINDINGS_FILENAME if result.success else case_dir / "audit" / "findings.jsonl"
    )
    scrubbed_params: dict[str, object] = {
        "finding_id": scrub_line_terminators(payload.finding_id),
    }
    entry = AuditEntry(
        ts=datetime.now(UTC),
        audit_id=audit_id,
        tool="approve_finding",
        params=scrubbed_params,
        result_summary=result.model_dump(mode="json"),
        result_sha256=hashlib.sha256(summary_json.encode("utf-8")).hexdigest(),
        stdout_path=artefact_path,
        elapsed_ms=elapsed_ms,
        examiner=examiner,
        model_used=model_used,
        model_token_count={},
    )
    findings_log.parent.mkdir(parents=True, exist_ok=True)
    append_chained_jsonl_line(findings_log, entry.model_dump_json())


def _wrap_envelope(
    result: ApproveResult, *, audit_id: str, examiner: str
) -> ToolResponse[ApproveResult]:
    from silentwitness_mcp.envelope import make_empty_provenance

    return ToolResponse[ApproveResult](
        success=True,
        data=result,
        audit_id=audit_id,
        examiner=examiner,
        advisories=() if result.success else (str(result.reason),),
        data_provenance=make_empty_provenance("approve_finding"),
    )


__all__ = [
    "ApproveInput",
    "ApproveRejectReason",
    "ApproveResult",
    "approve_finding",
]
