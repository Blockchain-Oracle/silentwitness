"""Shared orchestrator for the disk tool family — parallel to
:func:`silentwitness_mcp.tools._vol_pipeline._run_wrapper` but for the
dotnet-EZ-Tools/CSV pattern. Pre-spawn gates → subprocess → CSV
glob+read+normalize+blob → parse → audit-row + success envelope."""

from __future__ import annotations

import hashlib
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, ValidationError

from silentwitness_common.types import DataProvenance, ToolResponse
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._disk_common import (
    DEFAULT_TIMEOUT_S,
    DiskFailureReason,
    blob_path_for,
    check_evidence_and_mount_gates,
    cmd_argv_for,
    delete_orphan_blob,
    glob_csv_output,
    persist_blob,
    read_csv_with_truncation_from_bytes,
    refuse,
    run_dotnet_ez_tool,
    truncated_stderr,
    write_audit_row,
)
from silentwitness_mcp.verification.normalizer import normalize_output

# AmcacheParser + AppCompatCacheParser call Environment.Exit(0) even on
# errors — exit code alone cannot signal failure. Check stderr for Serilog
# [ERR]/[FTL] markers (CLAUDE.md §SIFT 2026 paths note).
_SERILOG_ERR_RE: Final = re.compile(r"^\[\d{2}:\d{2}:\d{2} (?:ERR|FTL)\]", re.MULTILINE)


def _has_serilog_error(stderr: bytes) -> bool:
    return bool(_SERILOG_ERR_RE.search(stderr.decode("utf-8", errors="replace")))


def _is_under(child: Path, parent: Path) -> bool:
    """``True`` iff ``child.resolve()`` lives under ``parent.resolve()``.
    Closes the caller-controlled-path escape (an agent passing
    ``csv_out=/etc`` would otherwise drop a CSV outside the case dir
    AND have the wrapper create that directory tree on a refuse path)."""
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


async def run_disk_wrapper[TPayload: BaseModel](
    *,
    tool_name: str,
    ez_tool: str,
    ez_argv: list[str],
    csv_glob_pattern: str,
    csv_out_dir: Path,
    output_cls: type[TPayload],
    parse_csv: Callable[[list[dict[str, str | None]], bool], TPayload],
    caveats: tuple[str, ...],
    evidence_path: Path,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    check_serilog_stderr: bool = False,
    corroboration: tuple[str, ...] = (),
) -> ToolResponse[TPayload]:
    """Drive one EZ-Tools wrapper end-to-end. Errors at any stage fall
    through to :func:`refuse` with the appropriate
    :class:`DiskFailureReason`. Caveats + audit row propagate on
    every refuse path (architecture §4.6, PRD FR #5).

    ``check_serilog_stderr=True`` enables post-exit-0 stderr scanning for
    Serilog ``[ERR]``/``[FTL]`` markers — required for tools whose exit
    code is unreliable (AmcacheParser, AppCompatCacheParser, PECmd, SBECmd).
    ``corroboration`` is forwarded verbatim to :class:`ToolResponse`."""
    pre_audit_id = audit_logger.next_audit_id()
    start = time.monotonic()
    cmd_argv = tuple(cmd_argv_for(ez_tool, ez_argv))
    refuse_kw: dict[str, Any] = {
        "tool_name": tool_name,
        "pre_audit_id": pre_audit_id,
        "case_dir": case_dir,
        "audit_logger": audit_logger,
        "evidence_path": evidence_path,
        "model_used": model_used,
        "caveats": caveats,
        "cmd_argv": cmd_argv,
    }

    gate = check_evidence_and_mount_gates(evidence_path, evidence_registry=evidence_registry)
    if gate is not None:
        reason, advisory = gate
        return refuse(
            reason,
            elapsed_ms=(time.monotonic() - start) * 1000.0,
            advisories=(advisory,),
            **refuse_kw,
        )

    # csv_out path-traversal guard — only AFTER the evidence gate so a
    # refused call has no filesystem side-effects (no surprise mkdir).
    if not _is_under(csv_out_dir, case_dir):
        return refuse(
            DiskFailureReason.OUTPUT_PARSE_FAILED,
            elapsed_ms=(time.monotonic() - start) * 1000.0,
            advisories=(
                f"csv_out_dir {csv_out_dir} is not under case_dir {case_dir}; "
                "refusing to write CSV outside the case directory",
            ),
            **refuse_kw,
        )
    csv_out_dir.mkdir(parents=True, exist_ok=True)
    # Capture wall-clock before spawn so stale residue (a CSV that
    # predates this run) can be detected via mtime.
    spawn_wall = time.time()

    try:
        result = await run_dotnet_ez_tool(ez_tool, ez_argv, timeout_s=timeout_s)
    except TimeoutError:
        return refuse(
            DiskFailureReason.TOOL_TIMEOUT,
            elapsed_ms=timeout_s * 1000.0,
            advisories=(f"dotnet {ez_tool} exceeded {timeout_s}s timeout",),
            **refuse_kw,
        )

    if result.exit_code != 0:
        # MFTECmd's exit code is reliable; other EZ Tools require Serilog
        # stderr parsing. Per-tool wrappers can pre-flight that check
        # before calling run_disk_wrapper if needed.
        advisory = truncated_stderr(result.stderr) or (
            f"dotnet {ez_tool} exited {result.exit_code} with no stderr output"
        )
        return refuse(
            DiskFailureReason.TOOL_FAILED,
            elapsed_ms=result.elapsed_ms,
            advisories=(advisory,),
            exit_code=result.exit_code,
            **refuse_kw,
        )

    if check_serilog_stderr and _has_serilog_error(result.stderr):
        advisory = truncated_stderr(result.stderr) or (
            f"dotnet {ez_tool} Serilog [ERR]/[FTL] on stderr with exit 0"
        )
        return refuse(
            DiskFailureReason.TOOL_FAILED,
            elapsed_ms=result.elapsed_ms,
            advisories=(advisory,),
            exit_code=result.exit_code,
            **refuse_kw,
        )

    csv_path = glob_csv_output(csv_out_dir, csv_glob_pattern)
    if csv_path is None:
        return refuse(
            DiskFailureReason.OUTPUT_PARSE_FAILED,
            elapsed_ms=result.elapsed_ms,
            advisories=(
                f"no CSV matching {csv_glob_pattern!r} under {csv_out_dir} "
                f"after dotnet {ez_tool} exit 0 — output-name drift",
            ),
            exit_code=result.exit_code,
            **refuse_kw,
        )

    # Stale-residue guard — a CSV that predates the spawn means we
    # got someone else's output (prior run, racing dotnet). One-second
    # slack absorbs mtime granularity on coarse filesystems.
    if csv_path.stat().st_mtime < spawn_wall - 1.0:
        return refuse(
            DiskFailureReason.OUTPUT_PARSE_FAILED,
            elapsed_ms=result.elapsed_ms,
            advisories=(
                f"CSV {csv_path.name} mtime predates spawn — stale residue, "
                "refusing to surface as parse_mft output",
            ),
            exit_code=result.exit_code,
            **refuse_kw,
        )

    try:
        raw_bytes = csv_path.read_bytes()
    except OSError as exc:
        return refuse(
            DiskFailureReason.TOOL_FAILED,
            elapsed_ms=result.elapsed_ms,
            advisories=(f"CSV read failed: {type(exc).__name__}: {exc}",),
            exit_code=result.exit_code,
            **refuse_kw,
        )

    normalized = normalize_output(raw_bytes, tool_name)
    result_sha256 = hashlib.sha256(normalized).hexdigest()

    try:
        blob_path = persist_blob(case_dir, pre_audit_id, normalized)
    except OSError as exc:
        delete_orphan_blob(blob_path_for(case_dir, pre_audit_id))
        return refuse(
            DiskFailureReason.TOOL_FAILED,
            elapsed_ms=result.elapsed_ms,
            advisories=(f"blob persist failed: {type(exc).__name__}: {exc}",),
            exit_code=result.exit_code,
            result_sha256=result_sha256,
            **refuse_kw,
        )

    # Parse from the SAME bytes we hashed + persisted — re-reading
    # the CSV from disk would open a TOCTOU window where blob_sha256
    # and the parsed rows could diverge (housekeeping race, MFTECmd
    # retry, etc.).
    rows, truncated = read_csv_with_truncation_from_bytes(normalized)

    try:
        output = parse_csv(rows, truncated)
    except (ValidationError, ValueError) as exc:
        return refuse(
            DiskFailureReason.OUTPUT_PARSE_FAILED,
            elapsed_ms=result.elapsed_ms,
            advisories=(f"CSV row parse failed: {type(exc).__name__}: {exc}",),
            blob_path=blob_path,
            exit_code=result.exit_code,
            result_sha256=result_sha256,
            **refuse_kw,
        )

    # Surface partial parse on EITHER the CSV-level truncation flag
    # (MFTECmd cut mid-write) OR the post-parse truncated flag set by
    # parse_csv when it skipped per-row ValidationErrors. row-by-row
    # skips are hidden inside parse_csv and only surface via the
    # output model's truncated property.
    success_advisories: tuple[str, ...] = ()
    output_truncated = getattr(output, "truncated", False)
    if truncated or output_truncated:
        trunc_reason = "CSV truncated mid-write" if truncated else "rows skipped on validation"
        # row_count from output preferred over len(rows) — len(rows) counts pre-skip
        # input rows; output.row_count reflects only entries that passed validation.
        # getattr bridges until TPayload gains a typed Protocol (tracked tech debt).
        row_count: int = getattr(output, "row_count", len(rows))
        success_advisories = (f"partial parse: {row_count} rows recovered ({trunc_reason})",)

    try:
        write_audit_row(
            tool_name=tool_name,
            case_dir=case_dir,
            audit_logger=audit_logger,
            audit_id=pre_audit_id,
            evidence_path=evidence_path,
            elapsed_ms=result.elapsed_ms,
            model_used=model_used,
            result=output.model_dump(mode="json"),
            result_sha256=result_sha256,
            blob_path=blob_path,
            exit_code=0,
        )
    except OSError as exc:
        delete_orphan_blob(blob_path)
        return refuse(
            DiskFailureReason.TOOL_FAILED,
            elapsed_ms=result.elapsed_ms,
            advisories=(f"audit row write failed: {type(exc).__name__}: {exc}",),
            exit_code=result.exit_code,
            result_sha256=result_sha256,
            **refuse_kw,
        )

    return ToolResponse[TPayload](
        success=True,
        data=output,
        audit_id=pre_audit_id,
        examiner=audit_logger.examiner,
        advisories=success_advisories,
        caveats=caveats,
        corroboration=corroboration,
        data_provenance=DataProvenance(
            tool=tool_name,
            stdout_path=blob_path,
            result_sha256=result_sha256,
            elapsed_ms=result.elapsed_ms,
            cmd_argv=cmd_argv,
        ),
    )


__all__ = ["run_disk_wrapper"]
