"""Shared dotnet-EZ-Tools subprocess infrastructure for the disk
tool family (parse_mft, parse_amcache, parse_shimcache,
parse_prefetch, parse_shellbags) — architecture §4.2 row 10,
context/.raw-design-research/03 §EZ Tools.

EZ Tools ship as .NET DLLs invoked via ``dotnet <Tool>.dll``. CLAUDE.md
non-negotiable: most tools are FLAT-installed at
``/opt/zimmermantools/<Tool>.dll``; the four exceptions in
:data:`_NESTED_TOOLS` sit at ``/opt/zimmermantools/<Tool>/<Tool>.dll``.
Building the path via this catalogue keeps every wrapper's argv
deterministic for the audit log.

MFTECmd is the ONLY EZ Tool with a reliable exit code; the rest emit
Serilog ``[HH:MM:SS ERR|FTL]`` markers on stderr (caller-specific
parsers). This module supports the reliable-exit pattern; per-tool
stderr parsing belongs in :mod:`disk.py`."""

from __future__ import annotations

import asyncio
import csv
import dataclasses
import hashlib
import logging
import time
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel

from silentwitness_common.atomic_io import append_jsonl_line, write_bytes_atomic
from silentwitness_common.types import AuditEntry, DataProvenance, ToolResponse
from silentwitness_mcp._lifecycle import check_mount
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.envelope import make_empty_provenance
from silentwitness_mcp.evidence.registry import (
    EvidenceMissingOnDiskError,
    EvidenceNotRegisteredError,
    EvidenceRegistry,
    EvidenceRegistryError,
)

_LOG = logging.getLogger(__name__)

DOTNET_BIN: Final = Path("/usr/bin/dotnet")
"""Pinned dotnet 9 SDK path on SIFT 2026."""

EZ_TOOLS_ROOT: Final = Path("/opt/zimmermantools")
"""EZ Tools installation root. See ``install.sh`` for the inventory."""

# EZ Tools that sit at ``/opt/zimmermantools/<Tool>/<Tool>.dll``.
# Everything else is FLAT at ``/opt/zimmermantools/<Tool>.dll``.
# Note: EvtxECmd has the lowercase-dir quirk (``EvtxeCmd/EvtxECmd.dll``)
# — caller of :func:`dll_path_for` for log-family tools handles it.
_NESTED_TOOLS: Final[frozenset[str]] = frozenset({"RECmd", "SQLECmd", "iisGeolocate", "EvtxECmd"})

DEFAULT_TIMEOUT_S: Final = 300.0
"""Default subprocess timeout (5 min) for EZ Tools on a typical
$MFT / Amcache / Prefetch corpus."""

_TERMINATE_GRACE_S: Final = 5.0
_STDERR_ADVISORY_CAP: Final = 500
_BLOB_DIR: Final = "audit/blobs"
_SENTINEL_PATH: Final = Path("/dev/null")
_AUDIT_DIR: Final = "audit"
_AUDIT_LOG_FILENAME: Final = "disk.jsonl"


class DiskFailureReason(StrEnum):
    """Closed reject-reason set for disk-family wrappers. Mirrors
    :class:`VolFailureReason` but adds ``DOTNET_NOT_FOUND`` because EZ
    Tools depend on the dotnet SDK being on disk at :data:`DOTNET_BIN`."""

    EVIDENCE_NOT_REGISTERED = "EVIDENCE_NOT_REGISTERED"
    EVIDENCE_HASH_MISMATCH = "EVIDENCE_HASH_MISMATCH"
    EVIDENCE_TAMPERED = "EVIDENCE_TAMPERED"
    MOUNT_NOT_RO_NOEXEC_NOSUID = "MOUNT_NOT_RO_NOEXEC_NOSUID"
    DOTNET_NOT_FOUND = "DOTNET_NOT_FOUND"
    TOOL_FAILED = "TOOL_FAILED"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    OUTPUT_PARSE_FAILED = "OUTPUT_PARSE_FAILED"


def dll_path_for(tool_name: str) -> Path:
    """Resolve the on-disk DLL path for an EZ Tool. Routes through
    :data:`_NESTED_TOOLS` for the four nested-install tools."""
    if tool_name in _NESTED_TOOLS:
        return EZ_TOOLS_ROOT / tool_name / f"{tool_name}.dll"
    return EZ_TOOLS_ROOT / f"{tool_name}.dll"


@dataclasses.dataclass(slots=True, frozen=True)
class DotnetEzResult:
    """Outcome of one :func:`run_dotnet_ez_tool` invocation."""

    exit_code: int
    stdout: bytes
    stderr: bytes
    elapsed_ms: float


async def run_dotnet_ez_tool(
    tool_name: str,
    argv: list[str],
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> DotnetEzResult:
    """Spawn ``dotnet <dll_path_for(tool_name)> *argv`` and return the
    typed result. Caller MUST have already cleared
    :func:`check_evidence_and_mount_gates` and the dotnet-presence
    check — this helper does not enforce them. Raises
    :class:`TimeoutError` on subprocess timeout."""
    cmd_argv = [str(DOTNET_BIN), str(dll_path_for(tool_name)), *argv]
    start = time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        *cmd_argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except TimeoutError:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=_TERMINATE_GRACE_S)
        except TimeoutError:
            proc.kill()
            try:
                await asyncio.wait_for(proc.wait(), timeout=_TERMINATE_GRACE_S)
            except TimeoutError:
                _LOG.error("dotnet %s ignored SIGKILL", tool_name)
        raise
    return DotnetEzResult(
        exit_code=proc.returncode if proc.returncode is not None else -1,
        stdout=stdout,
        stderr=stderr,
        elapsed_ms=(time.monotonic() - start) * 1000.0,
    )


def cmd_argv_for(tool_name: str, argv: list[str]) -> list[str]:
    """Reconstruct the cmd argv for :class:`DataProvenance`. Same shape
    as :func:`run_dotnet_ez_tool` builds, used by both success and
    refuse paths so the provenance is consistent."""
    return [str(DOTNET_BIN), str(dll_path_for(tool_name)), *argv]


def glob_csv_output(csv_out_dir: Path, pattern: str) -> Path | None:
    """Pick the most recently modified CSV that matches ``pattern``
    under ``csv_out_dir``. EZ Tools name CSVs ``<timestamp>_<Tool>_
    <Input>_Output.csv`` and the caller supplies the per-tool glob."""
    matches = sorted(csv_out_dir.glob(pattern), key=lambda p: p.stat().st_mtime)
    return matches[-1] if matches else None


def read_csv_with_truncation_from_bytes(
    raw: bytes,
) -> tuple[list[dict[str, str | None]], bool]:
    """Parse CSV bytes via :class:`csv.DictReader`; return rows + a
    ``truncated`` flag.

    Partial-success: EZ Tools that die mid-write leave a CSV with a
    truncated final row, and that recovery surface is forensically
    preferable to a hard reject. Truncation is detected via two
    independent signals because :class:`csv.DictReader` silently pads
    short rows with ``None``:

    1. The exception branch catches encoding errors / malformed
       quoting — rare but real.
    2. The post-read scan inspects the last row's values; if any
       column ended up ``None`` (header column count > row column
       count), the row was cut short of the header — drop and flag.

    Input is bytes (NOT a path) so the caller can guarantee parse
    and blob-hash see the same byte stream — re-reading from disk
    would open a TOCTOU window."""
    import io

    rows: list[dict[str, str | None]] = []
    truncated = False
    try:
        text = raw.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text, newline=""))
        for row in reader:
            rows.append({k: v for k, v in row.items() if k is not None})
    except (csv.Error, UnicodeDecodeError):
        truncated = True
    if rows and any(v is None for v in rows[-1].values()):
        rows.pop()
        truncated = True
    return rows, truncated


def check_evidence_and_mount_gates(
    evidence_path: Path, *, evidence_registry: EvidenceRegistry
) -> tuple[DiskFailureReason, str] | None:
    """Run the three pre-spawn gates for a disk-family tool:
    1. :data:`DOTNET_BIN` exists,
    2. mount is ``ro,noexec,nosuid`` per architecture §4.11,
    3. evidence is registered + SHA256-stable.

    Order matters — :data:`DOTNET_BIN` first so a SIFT-bootstrap
    omission surfaces before any I/O. ``None`` on all-pass."""
    if not DOTNET_BIN.exists():
        return DiskFailureReason.DOTNET_NOT_FOUND, (
            f"dotnet SDK not found at {DOTNET_BIN}; "
            "rerun install.sh to provision SIFT 2026 dependencies"
        )
    mount = check_mount()
    if not mount.ok:
        return DiskFailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID, (
            f"evidence mount failed ro,noexec,nosuid check: "
            f"{'; '.join(mount.advisories) or 'no detail'}"
        )
    try:
        evidence_registry.assert_registered(evidence_path)
    except EvidenceNotRegisteredError:
        return DiskFailureReason.EVIDENCE_NOT_REGISTERED, (
            f"evidence path not registered: {evidence_path}"
        )
    try:
        verify = evidence_registry.verify_hash(evidence_path)
    except EvidenceMissingOnDiskError:
        return DiskFailureReason.EVIDENCE_TAMPERED, (
            f"evidence file vanished between assert_registered and verify_hash: {evidence_path}"
        )
    except EvidenceRegistryError as exc:
        return DiskFailureReason.EVIDENCE_TAMPERED, (
            f"registry error during verify_hash: {type(exc).__name__}: {exc}"
        )
    if not verify.matches:
        # Per story-parse-mft BDD §7 (line 81): SHA256 drift surfaces
        # as EVIDENCE_HASH_MISMATCH (the integrity failure mode);
        # generic EVIDENCE_TAMPERED covers "evidence vanished" /
        # "registry error" — semantically distinct.
        return DiskFailureReason.EVIDENCE_HASH_MISMATCH, (
            f"SHA256 drift on registered evidence: "
            f"expected={verify.expected} actual={verify.actual}"
        )
    return None


def truncated_stderr(raw: bytes) -> str:
    """First :data:`_STDERR_ADVISORY_CAP` bytes of stderr, decoded."""
    return raw[:_STDERR_ADVISORY_CAP].decode("utf-8", errors="replace")


def blob_path_for(case_dir: Path, audit_id: str) -> Path:
    """Per-case blob path; ``.txt`` because EZ-Tools output is CSV."""
    return case_dir / _BLOB_DIR / f"{audit_id}.txt"


def persist_blob(case_dir: Path, audit_id: str, payload: bytes) -> Path:
    """Atomic write + parent-dir fsync. Raises :class:`OSError` on
    full disk / EACCES — caller maps to ``TOOL_FAILED`` with an
    orphan-cleanup attempt."""
    blob = blob_path_for(case_dir, audit_id)
    blob.parent.mkdir(parents=True, exist_ok=True)
    write_bytes_atomic(blob, payload)
    return blob


def delete_orphan_blob(blob: Path) -> None:
    """Best-effort cleanup of an orphan blob from a failed audit-row
    write. Silently swallows :class:`OSError` because we're already on
    a refuse path."""
    try:
        blob.unlink(missing_ok=True)
    except OSError:
        _LOG.warning("orphan blob cleanup failed: %s", blob, exc_info=True)


def write_audit_row(
    *,
    tool_name: str,
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
    """One audit JSONL row per tool invocation (PRD FR #5). Both
    success and refuse paths call this — the differentiator is
    ``result_summary``. Path follows architecture §4.4:
    ``cases/<case_id>/audit/<backend>.jsonl``."""
    audit_log = case_dir / _AUDIT_DIR / _AUDIT_LOG_FILENAME
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    fallback_sha = hashlib.sha256(repr(result).encode("utf-8")).hexdigest()
    params: dict[str, Any] = {"evidence_path": str(evidence_path)}
    if exit_code is not None:
        params["exit_code"] = exit_code
    entry = AuditEntry(
        ts=datetime.now(UTC),
        audit_id=audit_id,
        tool=tool_name,
        params=params,
        result_summary=result,
        result_sha256=result_sha256 or fallback_sha,
        stdout_path=blob_path if blob_path is not None else _SENTINEL_PATH,
        elapsed_ms=elapsed_ms,
        examiner=audit_logger.examiner,
        model_used=model_used,
        model_token_count={},
    )
    append_jsonl_line(audit_log, entry.model_dump_json())


def refuse[TPayload: BaseModel](
    reason: DiskFailureReason,
    *,
    tool_name: str,
    pre_audit_id: str,
    case_dir: Path,
    audit_logger: AuditLogger,
    evidence_path: Path,
    elapsed_ms: float,
    model_used: str,
    advisories: tuple[str, ...],
    caveats: tuple[str, ...],
    cmd_argv: tuple[str, ...],
    blob_path: Path | None = None,
    exit_code: int | None = None,
    result_sha256: str | None = None,
) -> ToolResponse[TPayload]:
    """Build refusal envelope + audit row. Mirrors
    :func:`silentwitness_mcp.tools._vol_common.refuse` shape so the
    forensic narrator's reason-branching logic stays uniform across
    families. Caveats propagate on the refuse path so the agent
    interpreting an empty/refused envelope still gets the action-
    shaping guidance."""
    write_audit_row(
        tool_name=tool_name,
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
        provenance = make_empty_provenance(tool_name)
    else:
        provenance = DataProvenance(
            tool=tool_name,
            stdout_path=blob_path,
            result_sha256=result_sha256,
            elapsed_ms=elapsed_ms,
            cmd_argv=cmd_argv,
        )
    return ToolResponse[TPayload](
        success=False,
        data=None,
        audit_id=pre_audit_id,
        examiner=audit_logger.examiner,
        advisories=(*advisories, reason.value),
        caveats=caveats,
        data_provenance=provenance,
    )


__all__ = [
    "DEFAULT_TIMEOUT_S",
    "DOTNET_BIN",
    "EZ_TOOLS_ROOT",
    "DiskFailureReason",
    "DotnetEzResult",
    "blob_path_for",
    "check_evidence_and_mount_gates",
    "cmd_argv_for",
    "delete_orphan_blob",
    "dll_path_for",
    "glob_csv_output",
    "persist_blob",
    "read_csv_with_truncation_from_bytes",
    "refuse",
    "run_dotnet_ez_tool",
    "truncated_stderr",
    "write_audit_row",
]
