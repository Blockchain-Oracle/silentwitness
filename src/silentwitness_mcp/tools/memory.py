"""Volatility 3 memory-family MCP tools (architecture §4.6, PRD FR #5).

This module is the per-family file every ``vol_*`` story modifies.
:func:`vol_pslist` is the skeleton wrapper landed here; subsequent
stories (vol_psscan, vol_cmdline, vol_dlllist, ...) add their own
``vol_*`` wrappers + caveat catalogue entries in
:mod:`silentwitness_mcp.tools._vol_common`.

Vol3 plugin name is the class-suffixed form ``windows.pslist.PsList``
— the dotted prefix alone (``windows.pslist``) currently works but is
not future-proof.

Vol3 JSON renderer (``-r json``) emits a top-level array of row
objects. Column names are Vol3's CamelCase form (``PID``, ``PPID``,
``ImageFileName``, ``Offset(V)``, ...) — :class:`PslistEntry` maps
them to snake_case via Pydantic ``Field(alias=...)``.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field

from silentwitness_common.atomic_io import append_jsonl_line, write_bytes_atomic
from silentwitness_common.types import (
    AuditEntry,
    DataProvenance,
    ToolResponse,
)
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.envelope import make_empty_provenance
from silentwitness_mcp.evidence.registry import (
    EvidenceNotRegisteredError,
    EvidenceRegistry,
)
from silentwitness_mcp.tools._vol_common import (
    DEFAULT_TIMEOUT_S,
    VolFailureReason,
    _run_vol,
    caveats_for,
    cmd_argv_for,
    truncated_stderr,
)

_PSLIST_PLUGIN: Final = "windows.pslist.PsList"
_AUDIT_LOG_FILENAME: Final = "memory.jsonl"
_BLOB_DIR: Final = "audit/blobs"
_PARSE_PREVIEW_BYTES: Final = 200


class PslistEntry(BaseModel):
    """One row from Vol3 ``windows.pslist`` JSON renderer. Field
    aliases map Vol3's CamelCase keys (architecture-source-of-truth in
    ``context/domain/03`` §7.2) to snake_case Python."""

    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    pid: int = Field(alias="PID")
    ppid: int = Field(alias="PPID")
    image_file_name: str = Field(alias="ImageFileName")
    offset_v: int = Field(alias="Offset(V)")
    threads: int = Field(alias="Threads")
    handles: int | None = Field(default=None, alias="Handles")
    session_id: int | None = Field(default=None, alias="SessionId")
    wow64: bool = Field(alias="Wow64")
    create_time: datetime | None = Field(default=None, alias="CreateTime")
    exit_time: datetime | None = Field(default=None, alias="ExitTime")


class PslistOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    entries: tuple[PslistEntry, ...]


async def vol_pslist(
    evidence_path: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ToolResponse[PslistOutput]:
    """List Windows processes via Vol3 ``windows.pslist``. See module
    docstring for the JSON-renderer contract."""
    pre_audit_id = audit_logger.next_audit_id()
    start = time.monotonic()

    try:
        evidence_registry.assert_registered(evidence_path)
    except EvidenceNotRegisteredError:
        return _refuse(
            VolFailureReason.EVIDENCE_NOT_REGISTERED,
            pre_audit_id=pre_audit_id,
            case_dir=case_dir,
            audit_logger=audit_logger,
            evidence_path=evidence_path,
            elapsed_ms=(time.monotonic() - start) * 1000.0,
            model_used=model_used,
            advisories=(f"evidence path not registered: {evidence_path}",),
        )
    verify = evidence_registry.verify_hash(evidence_path)
    if not verify.matches:
        return _refuse(
            VolFailureReason.EVIDENCE_TAMPERED,
            pre_audit_id=pre_audit_id,
            case_dir=case_dir,
            audit_logger=audit_logger,
            evidence_path=evidence_path,
            elapsed_ms=(time.monotonic() - start) * 1000.0,
            model_used=model_used,
            advisories=(
                f"SHA256 drift on registered evidence: "
                f"expected={verify.expected} actual={verify.actual}",
            ),
        )

    try:
        result = await _run_vol(_PSLIST_PLUGIN, evidence_path, timeout_s=timeout_s)
    except TimeoutError:
        return _refuse(
            VolFailureReason.TOOL_TIMEOUT,
            pre_audit_id=pre_audit_id,
            case_dir=case_dir,
            audit_logger=audit_logger,
            evidence_path=evidence_path,
            elapsed_ms=timeout_s * 1000.0,
            model_used=model_used,
            advisories=(f"Vol3 windows.pslist exceeded {timeout_s}s timeout",),
        )

    blob_path = _persist_blob(case_dir, pre_audit_id, result.stdout_normalized)
    if result.exit_code != 0:
        return _refuse(
            VolFailureReason.TOOL_FAILED,
            pre_audit_id=pre_audit_id,
            case_dir=case_dir,
            audit_logger=audit_logger,
            evidence_path=evidence_path,
            elapsed_ms=result.elapsed_ms,
            model_used=model_used,
            advisories=(truncated_stderr(result.stderr),),
            blob_path=blob_path,
            exit_code=result.exit_code,
            result_sha256=result.result_sha256,
        )

    try:
        rows = json.loads(result.stdout_normalized.decode("utf-8"))
        if not isinstance(rows, list):
            raise ValueError(f"Vol3 JSON renderer returned {type(rows).__name__}, expected list")
        entries = tuple(PslistEntry.model_validate(row) for row in rows)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        preview = result.stdout_normalized[:_PARSE_PREVIEW_BYTES].decode("utf-8", errors="replace")
        return _refuse(
            VolFailureReason.OUTPUT_PARSE_FAILED,
            pre_audit_id=pre_audit_id,
            case_dir=case_dir,
            audit_logger=audit_logger,
            evidence_path=evidence_path,
            elapsed_ms=result.elapsed_ms,
            model_used=model_used,
            advisories=(f"unparseable Vol3 stdout: {type(exc).__name__}: {preview}",),
            blob_path=blob_path,
            exit_code=result.exit_code,
            result_sha256=result.result_sha256,
        )

    output = PslistOutput(entries=entries)
    _write_audit_row(
        case_dir=case_dir,
        audit_logger=audit_logger,
        audit_id=pre_audit_id,
        evidence_path=evidence_path,
        elapsed_ms=result.elapsed_ms,
        model_used=model_used,
        result=output.model_dump(mode="json"),
        result_sha256=result.result_sha256,
        blob_path=blob_path,
        exit_code=0,
    )
    return ToolResponse[PslistOutput](
        success=True,
        data=output,
        audit_id=pre_audit_id,
        examiner=audit_logger.examiner,
        caveats=caveats_for("pslist"),
        data_provenance=DataProvenance(
            tool="vol_pslist",
            stdout_path=blob_path,
            result_sha256=result.result_sha256,
            elapsed_ms=result.elapsed_ms,
            cmd_argv=tuple(cmd_argv_for(_PSLIST_PLUGIN, evidence_path)),
        ),
    )


def _refuse(
    reason: VolFailureReason,
    *,
    pre_audit_id: str,
    case_dir: Path,
    audit_logger: AuditLogger,
    evidence_path: Path,
    elapsed_ms: float,
    model_used: str,
    advisories: tuple[str, ...],
    blob_path: Path | None = None,
    exit_code: int | None = None,
    result_sha256: str | None = None,
) -> ToolResponse[PslistOutput]:
    """Build the refusal envelope + audit row uniformly. The audit row
    is written on EVERY refusal so the trail records why we declined
    (architecture §4.4). Refusals fired BEFORE the subprocess get an
    empty-sentinel DataProvenance; refusals AFTER (TOOL_FAILED,
    OUTPUT_PARSE_FAILED) carry the real blob path + hash so the audit
    chain can re-validate."""
    _write_audit_row(
        case_dir=case_dir,
        audit_logger=audit_logger,
        audit_id=pre_audit_id,
        evidence_path=evidence_path,
        elapsed_ms=elapsed_ms,
        model_used=model_used,
        result={"reason": reason.value, "advisories": list(advisories)},
        result_sha256=result_sha256,
        blob_path=blob_path,
        exit_code=exit_code,
    )
    if blob_path is None or result_sha256 is None:
        provenance = make_empty_provenance("vol_pslist")
    else:
        provenance = DataProvenance(
            tool="vol_pslist",
            stdout_path=blob_path,
            result_sha256=result_sha256,
            elapsed_ms=elapsed_ms,
            cmd_argv=tuple(cmd_argv_for(_PSLIST_PLUGIN, evidence_path)),
        )
    return ToolResponse[PslistOutput](
        success=False,
        data=None,
        audit_id=pre_audit_id,
        examiner=audit_logger.examiner,
        advisories=(*advisories, reason.value),
        data_provenance=provenance,
    )


def _persist_blob(case_dir: Path, audit_id: str, normalized: bytes) -> Path:
    """Write the normalized stdout to ``audit/blobs/<audit_id>.txt``
    (architecture §4.6). Atomic so a kill mid-write leaves either the
    full blob or nothing — the citation gate must never read a
    half-written blob."""
    blob_dir = case_dir / _BLOB_DIR
    blob_dir.mkdir(parents=True, exist_ok=True)
    blob_path = blob_dir / f"{audit_id}.txt"
    write_bytes_atomic(blob_path, normalized)
    return blob_path


def _write_audit_row(
    *,
    case_dir: Path,
    audit_logger: AuditLogger,
    audit_id: str,
    evidence_path: Path,
    elapsed_ms: float,
    model_used: str,
    result: dict[str, Any],
    result_sha256: str | None,
    blob_path: Path | None,
    exit_code: int | None,
) -> None:
    audit_log = case_dir / "audit" / _AUDIT_LOG_FILENAME
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    summary_json = json.dumps(result, sort_keys=True)
    fallback_sha = hashlib.sha256(summary_json.encode("utf-8")).hexdigest()
    extras: dict[str, object] = {"evidence_path": str(evidence_path)}
    if exit_code is not None:
        extras["exit_code"] = exit_code
    entry = AuditEntry(
        ts=datetime.now(UTC),
        audit_id=audit_id,
        tool="vol_pslist",
        params={"evidence_path": str(evidence_path), **extras},
        result_summary=result,
        result_sha256=result_sha256 or fallback_sha,
        # /dev/null sentinel for pre-subprocess refusals — matches the
        # convention from make_empty_provenance so audit-log readers
        # can grep for the sentinel to find pre-execution refusals.
        stdout_path=blob_path if blob_path is not None else Path("/dev/null"),
        elapsed_ms=elapsed_ms,
        examiner=audit_logger.examiner,
        model_used=model_used,
        model_token_count={},
    )
    append_jsonl_line(audit_log, entry.model_dump_json())


__all__ = [
    "PslistEntry",
    "PslistOutput",
    "vol_pslist",
]
