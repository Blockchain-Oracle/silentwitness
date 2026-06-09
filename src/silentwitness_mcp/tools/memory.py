"""Volatility 3 memory-family tool bodies (architecture §4.6, PRD FR #5).

Subprocess + audit + blob + refusal plumbing lives in
:mod:`_vol_common`. Plugin names use the class-suffixed form
(``windows.pslist.PsList``). The ``-r json`` renderer emits a flat
array for pslist/psscan and an ``__children`` tree for pstree."""

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
from silentwitness_mcp.tools._memory_models import (
    MalfindHit,
    MalfindOutput,
    PslistEntry,
    PslistOutput,
    PsscanEntry,
    PsscanOutput,
    PstreeEntry,
    PstreeOutput,
)
from silentwitness_mcp.tools._vol_common import (
    DEFAULT_TIMEOUT_S,
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

_PSLIST_PLUGIN: Final = "windows.pslist.PsList"
_PSTREE_PLUGIN: Final = "windows.pstree.PsTree"
_PSSCAN_PLUGIN: Final = "windows.psscan.PsScan"
# Vol3 ≥2.29 removes windows.malfind — windows.malware path is future-safe.
_MALFIND_PLUGIN: Final = "windows.malware.malfind.Malfind"
_AUDIT_LOG_FILENAME: Final = "memory.jsonl"
_PARSE_PREVIEW_BYTES: Final = 200
_MALFIND_HEXDUMP_CAP: Final = 256  # = 128 bytes of hex


async def vol_pslist(
    evidence_path: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ToolResponse[PslistOutput]:
    return await _run_wrapper(
        tool_name="vol_pslist",
        plugin_name=_PSLIST_PLUGIN,
        caveat_key="pslist",
        output_cls=PslistOutput,
        parse_rows=lambda raw: _parse_flat(raw, PslistEntry, PslistOutput),
        evidence_path=evidence_path,
        case_dir=case_dir,
        evidence_registry=evidence_registry,
        audit_logger=audit_logger,
        model_used=model_used,
        timeout_s=timeout_s,
    )


async def vol_psscan(
    evidence_path: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ToolResponse[PsscanOutput]:
    return await _run_wrapper(
        tool_name="vol_psscan",
        plugin_name=_PSSCAN_PLUGIN,
        caveat_key="psscan",
        output_cls=PsscanOutput,
        parse_rows=lambda raw: _parse_flat(raw, PsscanEntry, PsscanOutput),
        evidence_path=evidence_path,
        case_dir=case_dir,
        evidence_registry=evidence_registry,
        audit_logger=audit_logger,
        model_used=model_used,
        timeout_s=timeout_s,
    )


async def vol_pstree(
    evidence_path: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ToolResponse[PstreeOutput]:
    """``__children`` tree → flat list, breadth-first. Depth omitted —
    downstream consumers recompute from parent/child pid pairs."""
    return await _run_wrapper(
        tool_name="vol_pstree",
        plugin_name=_PSTREE_PLUGIN,
        caveat_key="pstree",
        output_cls=PstreeOutput,
        parse_rows=lambda raw: PstreeOutput(entries=tuple(_flatten_pstree(raw))),
        evidence_path=evidence_path,
        case_dir=case_dir,
        evidence_registry=evidence_registry,
        audit_logger=audit_logger,
        model_used=model_used,
        timeout_s=timeout_s,
    )


async def vol_malfind(
    evidence_path: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    pid: int | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ToolResponse[MalfindOutput]:
    """RWX-private-no-mapped-file VAD detection. ``pid=None`` scans
    all processes; an int filters at the Vol3 plugin layer."""
    return await _run_wrapper(
        tool_name="vol_malfind",
        plugin_name=_MALFIND_PLUGIN,
        caveat_key="malfind",
        output_cls=MalfindOutput,
        parse_rows=_parse_malfind,
        evidence_path=evidence_path,
        case_dir=case_dir,
        evidence_registry=evidence_registry,
        audit_logger=audit_logger,
        model_used=model_used,
        timeout_s=timeout_s,
        extra_argv=["--pid", str(pid)] if pid is not None else None,
    )


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
    rows = json.loads(raw.decode("utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"Vol3 JSON renderer returned {type(rows).__name__}, expected list")
    entries = tuple(row_cls.model_validate(row) for row in rows)
    return output_cls(entries=entries)


_HEX_CHARS: Final = frozenset("0123456789abcdefABCDEF")


def _parse_malfind(raw: bytes) -> MalfindOutput:
    """Trim Hexdump to 256 hex chars (first 128 bytes). Vol3 emits
    offset-prefixed + ASCII-suffixed lines; filtering to [0-9a-fA-F]
    keeps the field name honest (silent-failure LOW from PR #140)."""
    rows = json.loads(raw.decode("utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"malfind JSON must be a list, got {type(rows).__name__}")
    hits: list[MalfindHit] = []
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("Hexdump"), str):
            hex_only = "".join(c for c in row["Hexdump"] if c in _HEX_CHARS)
            row = {**row, "Hexdump": hex_only[:_MALFIND_HEXDUMP_CAP]}
        hits.append(MalfindHit.model_validate(row))
    return MalfindOutput(entries=tuple(hits))


def _flatten_pstree(raw: bytes) -> list[PstreeEntry]:
    """BFS flatten of Vol3 pstree's ``__children`` tree. A non-list/
    non-null ``__children`` raises — silent subtree drop would let
    schema drift hide a whole branch from the audit trail."""
    rows = json.loads(raw.decode("utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"pstree root must be a list, got {type(rows).__name__}")
    flat: list[PstreeEntry] = []
    stack: list[Any] = list(rows)
    while stack:
        node = stack.pop(0)
        if not isinstance(node, dict):
            raise ValueError(f"pstree node must be a dict, got {type(node).__name__}")
        children = node.pop("__children", None)
        flat.append(PstreeEntry.model_validate(node))
        if children is None:
            continue
        if not isinstance(children, list):
            raise ValueError(f"__children must be a list or null, got {type(children).__name__}")
        stack.extend(children)
    return flat


def hidden_or_terminated_candidates(pslist_pids: set[int], psscan_pids: set[int]) -> set[int]:
    """Rootkit-detection diff: processes in psscan but NOT in pslist.
    exit_time=None ⇒ DKOM-hidden candidate; populated ⇒ terminated
    teardown. Interpretation lives downstream."""
    return psscan_pids - pslist_pids


__all__ = [
    "MalfindHit",
    "MalfindOutput",
    "PslistEntry",
    "PslistOutput",
    "PsscanEntry",
    "PsscanOutput",
    "PstreeEntry",
    "PstreeOutput",
    "hidden_or_terminated_candidates",
    "vol_malfind",
    "vol_pslist",
    "vol_psscan",
    "vol_pstree",
]
