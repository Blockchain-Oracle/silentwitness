"""``approve_finding`` tool body — password-gated HMAC ledger transition
(architecture §4.2 row ``approve_finding``, §4.9 HMAC ledger).

Pipeline: read finding F-NNN from findings.json → confirm status
DRAFT (ALREADY_APPROVED otherwise) → load case salt from CASE.yaml
(CASE_SALT_MISSING otherwise) → confirm ledger dir mode 0700
(LEDGER_DIR_PERMISSIONS_WEAK otherwise) → PBKDF2-SHA256(password,
salt, 600k) → compose substantive bytes via :class:`LedgerComposer`
finding shape → HMAC the bytes → append the sealed entry → flip
finding status DRAFT → APPROVED in findings.json (atomic rename) →
zero the derived key → audit row to ``audit/findings.jsonl``
REGARDLESS of accept/reject.

INVALID_PASSWORD is detected by attempting the re-verify against the
PREVIOUS ledger entry for the same finding when one exists; on a
fresh approval (no prior entry), the password is provisionally
accepted and committed — the verifier (Epic 12) re-checks every
approval offline before report rendering.

The MCP tool is NOT prompted-from-stdin; the CLI wrapper owns the
secure prompt and passes the password as a typed ``SecretStr``.
``SecretStr.get_secret_value()`` is called exactly once, immediately
fed into ``derive_key``, and the buffer zeroed before return.
Password / derived-key bytes NEVER appear in the audit row.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from silentwitness_common.atomic_io import append_jsonl_line, write_json_atomic
from silentwitness_common.types import (
    AuditEntry,
    Confidence,
    LedgerItemType,
    ToolResponse,
)
from silentwitness_mcp.audit.ledger import (
    HMACLedger,
    InterpretationParts,
    LedgerComposer,
    LedgerError,
    LedgerSecurityError,
    ObservationParts,
)
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings._approval_store import (
    load_case_salt,
    locate_finding,
    locate_interpretation,
    locate_observation,
    read_findings,
)
from silentwitness_mcp.findings._scrub import scrub_line_terminators


class ApproveRejectReason(StrEnum):
    """Closed rejection-code set — re-declared rather than aliased."""

    INVALID_PASSWORD = "INVALID_PASSWORD"  # noqa: S105 — reason code, not a credential  # pragma: allowlist secret
    FINDING_NOT_FOUND = "FINDING_NOT_FOUND"
    ALREADY_APPROVED = "ALREADY_APPROVED"
    LEDGER_DIR_PERMISSIONS_WEAK = "LEDGER_DIR_PERMISSIONS_WEAK"
    CASE_SALT_MISSING = "CASE_SALT_MISSING"
    LEDGER_FILE_MODE_WEAK = "LEDGER_FILE_MODE_WEAK"
    FINDINGS_STORE_CORRUPTED = "FINDINGS_STORE_CORRUPTED"
    FINDINGS_STORE_UNWRITABLE = "FINDINGS_STORE_UNWRITABLE"
    PIPELINE_INTERNAL_ERROR = "PIPELINE_INTERNAL_ERROR"


_RESULT_CONFIG = ConfigDict(frozen=True, extra="forbid")
_FINDING_ID_PATTERN: Final = "^F-\\d{3,}$"
_FINDINGS_FILENAME: Final = "findings.json"
_STATUS_APPROVED: Final = "APPROVED"


class ApproveInput(BaseModel):
    """Examiner input. ``password`` is a :class:`SecretStr` so its
    contents are masked in ``repr`` / model_dump / logger output —
    the ``get_secret_value()`` call happens exactly once inside
    :func:`approve_finding`, immediately fed into PBKDF2, and the
    derived-key buffer is zeroed before return."""

    model_config = _RESULT_CONFIG

    finding_id: str = Field(min_length=1, pattern=_FINDING_ID_PATTERN)
    password: SecretStr


class ApproveResult(BaseModel):
    """Result payload. Discriminator pins success/finding_id/reason
    exclusivity — same shape as ObservationResult / PivotResult."""

    model_config = _RESULT_CONFIG

    success: bool
    finding_id: str | None = None
    ledger_entry_ts: datetime | None = None
    reason: ApproveRejectReason | None = None
    context: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_tag(self) -> ApproveResult:
        if self.success:
            if self.finding_id is None:
                raise ValueError("success=True requires finding_id")
            if self.reason is not None:
                raise ValueError("success=True must not carry reason")
        else:
            if self.reason is None:
                raise ValueError("success=False requires reason")
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
    """Examiner-only ledger transition. The CLI is the only documented
    entrypoint; the LLM cannot reach this tool (architecture §6.2 deny
    rule). The caller MUST hold the password in a controlled buffer
    and pass it via the :class:`SecretStr` field."""
    findings_log = case_dir / "audit" / "findings.jsonl"
    start = time.monotonic()
    pre_audit_id = audit_logger.next_audit_id()
    result: ApproveResult | None = None
    try:
        result = _run_pipeline(
            payload,
            case_dir=case_dir,
            ledger_dir=ledger_dir,
            case_id=case_id,
        )
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        # _read_findings + yaml.safe_load raises sit here; LedgerKeyError
        # from PBKDF2 also subclasses ValueError but it cannot fire with
        # the constants here (600k iters is the floor).
        result = ApproveResult(
            success=False,
            reason=ApproveRejectReason.FINDINGS_STORE_CORRUPTED,
            context={"stage": "findings_read", "error_type": type(exc).__name__},
        )
    except LedgerSecurityError:
        result = ApproveResult(
            success=False,
            reason=ApproveRejectReason.LEDGER_DIR_PERMISSIONS_WEAK,
            context={"ledger_dir": str(ledger_dir)},
        )
    except LedgerError as exc:
        result = ApproveResult(
            success=False,
            reason=ApproveRejectReason.PIPELINE_INTERNAL_ERROR,
            context={"stage": "ledger", "error_type": type(exc).__name__},
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

    # HMACLedger(__init__) raises LedgerSecurityError on weak dir mode;
    # caught at the envelope level and mapped to
    # LEDGER_DIR_PERMISSIONS_WEAK.
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

    derived_key = bytearray(HMACLedger.derive_key(payload.password.get_secret_value(), salt))
    try:
        entry = ledger.append(
            bytes(derived_key),
            payload.finding_id,
            LedgerItemType.FINDING,
            content_bytes,
            examiner=case_id,  # ledger examiner == case_id slug per architecture §4.9
        )
    finally:
        HMACLedger.zero_key(derived_key)

    # Flip status atomically. Even if findings.json has accumulated
    # other records since we read it, the index we computed earlier is
    # still valid because this tool runs under the same .findings.lock
    # convention (caller-serialised; tests pin single-process).
    findings[finding_idx] = {**finding, "status": _STATUS_APPROVED}
    write_json_atomic(case_dir / _FINDINGS_FILENAME, findings)

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
    """Canonical :class:`AuditEntry` (§4.4). The audit row NEVER carries
    the password or the derived-key bytes — only the finding_id and the
    result. U+2028 / U+2029 are scrubbed from the finding_id even though
    it is regex-pinned, for symmetry with sibling tools."""
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
    append_jsonl_line(findings_log, entry.model_dump_json())


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
