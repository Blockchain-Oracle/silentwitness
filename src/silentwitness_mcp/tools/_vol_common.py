"""Shared Volatility 3 subprocess infrastructure (architecture §4.6,
PRD FR #5).

Every ``vol_*`` wrapper imports :func:`_run_vol`, the family-shared
refusal helpers (:func:`refuse`, :func:`write_audit_row`,
:func:`persist_blob`, :func:`delete_orphan_blob`), and the
:class:`VolFailureReason` enum from here. The skeleton story
(story-vol-pslist) landed the subprocess helper; the pstree+psscan
story extracted the refusal-envelope plumbing so subsequent stories
add ~5 LOC of body, not ~80.

Vol3 binary path is pinned to SilentWitness's OWN venv at
``/opt/silentwitness/vol3-venv/bin/vol`` — see CLAUDE.md "Critical pin
reminders": SIFT pins no Vol3 version (open issue #1985 on Vol3 2.28
regresses layer detection on large dumps), so we install our own.
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel

from silentwitness_common.atomic_io import append_jsonl_line, write_bytes_atomic
from silentwitness_common.types import AuditEntry, DataProvenance, ToolResponse
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.envelope import make_empty_provenance
from silentwitness_mcp.verification.normalizer import normalize_output

_BLOB_DIR: Final = "audit/blobs"
_SENTINEL_PATH: Final = Path("/dev/null")

VOL_BIN: Final = Path("/opt/silentwitness/vol3-venv/bin/vol")
"""Vol3 binary. CLAUDE.md non-negotiable: never `/opt/volatility3/...`."""

DEFAULT_TIMEOUT_S: Final = 300.0
"""Default subprocess timeout (5 min). Heavy plugins like ``malfind``
override per-call but the floor is here."""

_TERMINATE_GRACE_S: Final = 5.0
"""SIGTERM → SIGKILL grace window on timeout."""

_STDERR_ADVISORY_CAP: Final = 500
"""Bytes of stderr quoted into a ``TOOL_FAILED`` advisory."""


class VolFailureReason(StrEnum):
    """Closed reject-reason set for ``vol_*`` wrappers. Architecture
    §4.6 + §4.10 + §4.11 surface all four failure modes through one
    typed enum so the agent's reason-branching logic stays uniform
    across the memory family."""

    EVIDENCE_NOT_REGISTERED = "EVIDENCE_NOT_REGISTERED"
    EVIDENCE_TAMPERED = "EVIDENCE_TAMPERED"
    MOUNT_NOT_RO_NOEXEC_NOSUID = "MOUNT_NOT_RO_NOEXEC_NOSUID"
    TOOL_FAILED = "TOOL_FAILED"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    OUTPUT_PARSE_FAILED = "OUTPUT_PARSE_FAILED"


_VOL_CAVEATS: Final[Mapping[str, tuple[str, ...]]] = {
    # context/domain/03 §7.2 Gotchas — quoted verbatim.
    "pslist": (
        (
            "windows.pslist walks PsActiveProcessHead — DKOM-hidden "
            "processes are invisible; corroborate with vol_psscan"
        ),
        ("ImageFileName is truncated to 15 chars; use vol_cmdline or vol_dlllist for full paths"),
        ("ExitTime may be set for processes still referenced by other handles (orphan teardown)"),
    ),
    "pstree": (
        ("Parent PIDs can refer to dead processes via PID reuse — cross-check CreateTime ordering"),
        (
            "Process hollowing produces legitimate-looking lineage with "
            "malicious code — vol_pstree alone cannot detect it; "
            "corroborate with vol_malfind + ldrmodules"
        ),
    ),
    "psscan": (
        (
            "windows.psscan may show terminated processes that pslist no "
            "longer sees — entries with ExitTime set are normal teardown "
            "artifacts, not malice"
        ),
        (
            "diff vs vol_pslist: processes in psscan but NOT in pslist "
            "are DKOM-hidden OR terminated; ExitTime distinguishes the two"
        ),
        (
            "pool-tag scan can produce false positives from non-process "
            "allocations — validate Threads/Handles plausibility before "
            "trusting an entry"
        ),
    ),
    "malfind": (
        (
            "RWX private memory with no mapped file is the classic injection "
            "pattern — but legitimate JIT engines (.NET CLR, Java JVM, "
            "V8/Node, Chromium) also allocate RWX; corroborate with "
            "vol_ldrmodules and process lineage before claiming injection"
        ),
        (
            "windows.malfind misses RX-only code (attacker VirtualProtect'd "
            "from RWX to RX post-write) and misses file-backed hollowed "
            "images (use vol_ldrmodules for hollowing detection)"
        ),
        (
            "hexdump_first_128 captures the first 128 bytes of the suspicious "
            "VAD — MZ + PE\\0\\0 pattern indicates a PE payload; lone "
            "0xE8/0xE9 + nop sled indicates shellcode"
        ),
    ),
    "netscan": (
        # Ordered: action-shaping caveat first, build-fragility CYA second,
        # owner resolution third, listening-state interpretation fourth.
        (
            "windows.netscan pool-tag scan returns both active AND "
            "recently-closed endpoints — filter state to ESTABLISHED for "
            "live C2 evidence; TIME_WAIT / CLOSE_WAIT / FIN_WAIT_* are "
            "historical"
        ),
        (
            "windows.netscan is build-fragile on Windows 10/11 — symbol "
            "drift across builds can drop entries or surface artifacts; "
            "cross-check with vol_netstat when available"
        ),
        (
            "Owner process resolution requires the PID still being valid "
            "in pslist — owner may be blank for endpoints whose process "
            "has exited"
        ),
        (
            "LISTENING state on a non-loopback bind from a non-standard "
            "process is a backdoor candidate; LISTENING on loopback is "
            "normal IPC"
        ),
    ),
}


def caveats_for(plugin_key: str) -> tuple[str, ...]:
    """Return the caveat list for ``plugin_key`` or ``()`` if unknown.
    Tools that pass an unknown key get empty caveats — caller should
    have registered them first; a silent ``KeyError`` here would let
    a typo strip safety guidance from the audit row."""
    return _VOL_CAVEATS.get(plugin_key, ())


@dataclasses.dataclass(slots=True, frozen=True)
class _VolResult:
    """Outcome of one :func:`_run_vol` invocation. ``stdout_normalized``
    is the post-normalizer bytes — citation gates and the audit-blob
    SHA256 both use this canonical form (architecture §4.6)."""

    exit_code: int
    stdout_normalized: bytes
    stderr: bytes
    elapsed_ms: float
    result_sha256: str


async def _run_vol(
    plugin_name: str,
    evidence_path: Path,
    *,
    extra_argv: list[str] | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    normalizer_key: str = "vol_pslist",
) -> _VolResult:
    """Spawn Vol3 in JSON-renderer mode (`-r json`) against
    ``evidence_path`` and return the typed result.

    Caller MUST have already cleared evidence-registry +
    mount-validator gates — this helper does NOT enforce them. Raises
    :class:`asyncio.TimeoutError` on subprocess timeout (caller maps
    to :attr:`VolFailureReason.TOOL_TIMEOUT`)."""
    cmd_argv = [
        str(VOL_BIN),
        "-f",
        str(evidence_path),
        "-r",
        "json",
        plugin_name,
        *(extra_argv or []),
    ]
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
            # Bounded — a process in uninterruptible disk wait can
            # ignore SIGKILL until the syscall completes; without this
            # cap the coroutine would hang forever and the caller's
            # TOOL_TIMEOUT envelope would never fire.
            try:
                await asyncio.wait_for(proc.wait(), timeout=_TERMINATE_GRACE_S)
            except TimeoutError:
                pass
        raise
    elapsed_ms = (time.monotonic() - start) * 1000.0
    normalized = normalize_output(stdout, normalizer_key)
    return _VolResult(
        exit_code=proc.returncode if proc.returncode is not None else -1,
        stdout_normalized=normalized,
        stderr=stderr,
        elapsed_ms=elapsed_ms,
        result_sha256=hashlib.sha256(normalized).hexdigest(),
    )


def truncated_stderr(stderr: bytes) -> str:
    """First :data:`_STDERR_ADVISORY_CAP` chars of stderr, UTF-8
    surrogate-escape decoded. Used in the ``TOOL_FAILED`` advisory."""
    return stderr.decode("utf-8", errors="surrogateescape")[:_STDERR_ADVISORY_CAP]


def cmd_argv_for(
    plugin_name: str, evidence_path: Path, extra: list[str] | None = None
) -> list[str]:
    """Public mirror of the argv :func:`_run_vol` builds. Lets the
    tool wrapper record cmd_argv in :class:`DataProvenance` without
    re-spawning."""
    return [
        str(VOL_BIN),
        "-f",
        str(evidence_path),
        "-r",
        "json",
        plugin_name,
        *(extra or []),
    ]


# ---------------------------------------------------------------------------
# Family-shared audit / blob / refusal infrastructure
# ---------------------------------------------------------------------------


def persist_blob(case_dir: Path, audit_id: str, normalized: bytes) -> Path:
    """Atomic write of the normalized stdout to
    ``cases/<id>/audit/blobs/<audit_id>.txt`` (architecture §4.6)."""
    blob_dir = case_dir / _BLOB_DIR
    blob_dir.mkdir(parents=True, exist_ok=True)
    blob_path = blob_dir / f"{audit_id}.txt"
    write_bytes_atomic(blob_path, normalized)
    return blob_path


def delete_orphan_blob(blob_path: Path | None) -> None:
    """Drop a blob whose audit-row write failed post-persist."""
    if blob_path is None:
        return
    try:
        blob_path.unlink(missing_ok=True)
    except OSError:
        pass


def write_audit_row(
    *,
    tool_name: str,
    case_dir: Path,
    audit_log_filename: str,
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
    """Architecture §4.4 canonical audit row writer. ``/dev/null`` is
    the documented sentinel for pre-execution refusals (blob was never
    persisted) so audit-log readers can grep for the sentinel rather
    than treat a missing blob as corruption."""
    audit_log = case_dir / "audit" / audit_log_filename
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    summary_json = json.dumps(result, sort_keys=True)
    fallback_sha = hashlib.sha256(summary_json.encode("utf-8")).hexdigest()
    params: dict[str, object] = {"evidence_path": str(evidence_path)}
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
    reason: VolFailureReason,
    *,
    tool_name: str,
    plugin_name: str,
    audit_log_filename: str,
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
    extra_argv: list[str] | None = None,
) -> ToolResponse[TPayload]:
    """Build refusal envelope + audit row. Pre-subprocess refusals get
    an empty-sentinel :class:`DataProvenance`; post-subprocess refusals
    carry the real blob path + hash so the verifier can re-check."""
    write_audit_row(
        tool_name=tool_name,
        case_dir=case_dir,
        audit_log_filename=audit_log_filename,
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
            cmd_argv=tuple(cmd_argv_for(plugin_name, evidence_path, extra_argv)),
        )
    return ToolResponse[TPayload](
        success=False,
        data=None,
        audit_id=pre_audit_id,
        examiner=audit_logger.examiner,
        advisories=(*advisories, reason.value),
        data_provenance=provenance,
    )


__all__ = [
    "DEFAULT_TIMEOUT_S",
    "VOL_BIN",
    "VolFailureReason",
    "_VolResult",
    "_run_vol",
    "caveats_for",
    "cmd_argv_for",
    "delete_orphan_blob",
    "persist_blob",
    "refuse",
    "truncated_stderr",
    "write_audit_row",
]
