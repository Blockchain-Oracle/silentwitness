"""Shared Vol3 wrapper pipeline (architecture §4.6).

Every ``vol_*`` family member runs the same pre-flight, subprocess,
persist, parse, audit-write sequence and only differs in the plugin
name, payload model, caveat key, and row→model parser. This module
holds that shared body so per-tool entry points in :mod:`memory` stay
short enough to keep the file under the 400-LOC CI cap.

Three responsibilities live here, ordered the way ``_run_wrapper``
calls them:

1. :func:`_check_evidence_gates` — registry ``assert_registered`` +
   ``verify_hash``. Returns a typed :class:`VolFailureReason` tuple
   on failure so the orchestrator can refuse without spawning Vol3.
2. :func:`_run_wrapper` — the orchestrator itself. Takes the
   plugin-specific bits as parameters (tool_name, plugin_name,
   caveat_key, output_cls, parse_rows, extra_argv).
3. :func:`_parse_flat` — the default flat-JSON row parser used by
   pslist / psscan / netscan / cmdline / dlllist / handles. Tools
   with bespoke output (pstree's ``__children`` tree, malfind's
   hexdump) ship their own parser into ``parse_rows``.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, ValidationError

from silentwitness_common.types import DataProvenance, ToolResponse
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import (
    EvidenceMissingOnDiskError,
    EvidenceNotRegisteredError,
    EvidenceRegistry,
    EvidenceRegistryError,
)
from silentwitness_mcp.tools._vol_common import (
    VolFailureReason,
    _run_vol,
    caveats_for,
    cmd_argv_for,
    delete_orphan_blob,
    persist_blob,
    refuse,
    truncated_stderr,
    write_audit_row,
)

_AUDIT_LOG_FILENAME: Final = "memory.jsonl"
_PARSE_PREVIEW_BYTES: Final = 200


def _check_evidence_gates(
    evidence_path: Path, *, evidence_registry: EvidenceRegistry
) -> tuple[VolFailureReason, str] | None:
    """assert_registered + verify_hash. File-vanished race between
    the two surfaces as EVIDENCE_TAMPERED."""
    try:
        evidence_registry.assert_registered(evidence_path)
    except EvidenceNotRegisteredError:
        return VolFailureReason.EVIDENCE_NOT_REGISTERED, (
            f"evidence path not registered: {evidence_path}"
        )
    try:
        verify = evidence_registry.verify_hash(evidence_path)
    except EvidenceMissingOnDiskError:
        return VolFailureReason.EVIDENCE_TAMPERED, (
            f"evidence file vanished between assert_registered and verify_hash: {evidence_path}"
        )
    except EvidenceRegistryError as exc:
        return VolFailureReason.EVIDENCE_TAMPERED, (
            f"registry error during verify_hash: {type(exc).__name__}: {exc}"
        )
    if not verify.matches:
        return VolFailureReason.EVIDENCE_TAMPERED, (
            f"SHA256 drift on registered evidence: "
            f"expected={verify.expected} actual={verify.actual}"
        )
    return None


async def _run_wrapper[TPayload: BaseModel](
    *,
    tool_name: str,
    plugin_name: str,
    caveat_key: str,
    output_cls: type[TPayload],
    parse_rows: Callable[[bytes], TPayload],
    evidence_path: Path,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float,
    extra_argv: list[str] | None = None,
) -> ToolResponse[TPayload]:
    """Drive one vol_* invocation end-to-end.

    ``output_cls`` is part of the signature to constrain the generic —
    the parser produces it, the envelope carries it. ``parse_rows``
    keeps the orchestrator agnostic to whether the row stream is a
    flat list (psXXXX family), a nested ``__children`` tree (pstree),
    or a custom-cleaned hexdump (malfind)."""
    pre_audit_id = audit_logger.next_audit_id()
    start = time.monotonic()
    # dict[str, Any] for the splat; refuse() checks types at the call.
    refuse_kw: dict[str, Any] = {
        "tool_name": tool_name,
        "plugin_name": plugin_name,
        "audit_log_filename": _AUDIT_LOG_FILENAME,
        "pre_audit_id": pre_audit_id,
        "case_dir": case_dir,
        "audit_logger": audit_logger,
        "evidence_path": evidence_path,
        "model_used": model_used,
        "extra_argv": extra_argv,
    }

    gate = _check_evidence_gates(evidence_path, evidence_registry=evidence_registry)
    if gate is not None:
        reason, advisory = gate
        return refuse(
            reason,
            elapsed_ms=(time.monotonic() - start) * 1000.0,
            advisories=(advisory,),
            **refuse_kw,
        )

    try:
        result = await _run_vol(
            plugin_name, evidence_path, extra_argv=extra_argv, timeout_s=timeout_s
        )
    except TimeoutError:
        return refuse(
            VolFailureReason.TOOL_TIMEOUT,
            elapsed_ms=timeout_s * 1000.0,
            advisories=(f"Vol3 {plugin_name} exceeded {timeout_s}s timeout",),
            **refuse_kw,
        )

    try:
        blob_path = persist_blob(case_dir, pre_audit_id, result.stdout_normalized)
    except OSError as exc:
        return refuse(
            VolFailureReason.TOOL_FAILED,
            elapsed_ms=result.elapsed_ms,
            advisories=(f"blob persist failed: {type(exc).__name__}: {exc}",),
            exit_code=result.exit_code,
            result_sha256=result.result_sha256,
            **refuse_kw,
        )

    if result.exit_code != 0:
        return refuse(
            VolFailureReason.TOOL_FAILED,
            elapsed_ms=result.elapsed_ms,
            advisories=(truncated_stderr(result.stderr),),
            blob_path=blob_path,
            exit_code=result.exit_code,
            result_sha256=result.result_sha256,
            **refuse_kw,
        )

    try:
        output = parse_rows(result.stdout_normalized)
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError, ValueError) as exc:
        preview = result.stdout_normalized[:_PARSE_PREVIEW_BYTES].decode("utf-8", errors="replace")
        return refuse(
            VolFailureReason.OUTPUT_PARSE_FAILED,
            elapsed_ms=result.elapsed_ms,
            advisories=(f"unparseable Vol3 stdout: {type(exc).__name__}: {preview}",),
            blob_path=blob_path,
            exit_code=result.exit_code,
            result_sha256=result.result_sha256,
            **refuse_kw,
        )

    try:
        write_audit_row(
            tool_name=tool_name,
            case_dir=case_dir,
            audit_log_filename=_AUDIT_LOG_FILENAME,
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
    except OSError as exc:
        delete_orphan_blob(blob_path)
        return refuse(
            VolFailureReason.TOOL_FAILED,
            elapsed_ms=result.elapsed_ms,
            advisories=(f"audit row write failed: {type(exc).__name__}: {exc}",),
            exit_code=result.exit_code,
            result_sha256=result.result_sha256,
            **refuse_kw,
        )

    return ToolResponse[TPayload](
        success=True,
        data=output,
        audit_id=pre_audit_id,
        examiner=audit_logger.examiner,
        caveats=caveats_for(caveat_key),
        data_provenance=DataProvenance(
            tool=tool_name,
            stdout_path=blob_path,
            result_sha256=result.result_sha256,
            elapsed_ms=result.elapsed_ms,
            cmd_argv=tuple(cmd_argv_for(plugin_name, evidence_path, extra_argv)),
        ),
    )


def _parse_flat[TPayload: BaseModel, TEntry: BaseModel](
    raw: bytes, row_cls: type[TEntry], output_cls: type[TPayload]
) -> TPayload:
    """Flat-list JSON → Pydantic output. Default parser used by the
    pslist / psscan / netscan / cmdline / dlllist / handles tools."""
    rows = json.loads(raw.decode("utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"Vol3 JSON renderer returned {type(rows).__name__}, expected list")
    entries = tuple(row_cls.model_validate(row) for row in rows)
    return output_cls(entries=entries)


__all__ = [
    "_check_evidence_gates",
    "_parse_flat",
    "_run_wrapper",
]
