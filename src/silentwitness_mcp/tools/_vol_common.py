"""Shared Volatility 3 subprocess infrastructure (architecture §4.6,
PRD FR #5).

Vol3 binary is pinned to SilentWitness's OWN venv at
``/opt/silentwitness/vol3-venv/bin/vol`` — see CLAUDE.md "Critical pin
reminders": SIFT pins no Vol3 version (open issue #1985 on Vol3 2.28
regresses layer detection on large dumps), so we install our own."""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import logging
import time
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel

from silentwitness_common.atomic_io import append_jsonl_line, write_bytes_atomic
from silentwitness_common.types import AuditEntry, DataProvenance, ToolResponse
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.envelope import make_empty_provenance
from silentwitness_mcp.tools._vol_caveats import caveats_for
from silentwitness_mcp.verification.normalizer import normalize_output

_LOG = logging.getLogger(__name__)

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
    """Closed reject-reason set for ``vol_*`` wrappers — every Vol3
    failure mode surfaces through one typed enum so the agent's
    reason-branching logic stays uniform across the memory family."""

    EVIDENCE_NOT_REGISTERED = "EVIDENCE_NOT_REGISTERED"
    EVIDENCE_TAMPERED = "EVIDENCE_TAMPERED"
    MOUNT_NOT_RO_NOEXEC_NOSUID = "MOUNT_NOT_RO_NOEXEC_NOSUID"
    TOOL_FAILED = "TOOL_FAILED"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    OUTPUT_PARSE_FAILED = "OUTPUT_PARSE_FAILED"


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
    normalizer_key: str,
    extra_argv: list[str] | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
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


def blob_path_for(case_dir: Path, audit_id: str) -> Path:
    """Single source of truth for the blob path scheme. Persist AND
    orphan-cleanup paths both go through here — silent drift between
    a writer and a cleaner would otherwise let orphaned blobs survive
    on disk past their audit row's death."""
    return case_dir / _BLOB_DIR / f"{audit_id}.txt"


def persist_blob(case_dir: Path, audit_id: str, normalized: bytes) -> Path:
    """Atomic write of the normalized stdout to
    ``cases/<id>/audit/blobs/<audit_id>.txt`` (architecture §4.6)."""
    blob_path = blob_path_for(case_dir, audit_id)
    blob_path.parent.mkdir(parents=True, exist_ok=True)
    write_bytes_atomic(blob_path, normalized)
    return blob_path


def delete_orphan_blob(blob_path: Path | None) -> None:
    """Drop a blob whose audit-row write failed post-persist.

    Logs at ERROR if the unlink itself fails — a swallowed failure
    here is a forensic-trail integrity question, not noise. The
    caller's refusal envelope still surfaces TOOL_FAILED, so the
    operator sees both signals: the original write failure (in the
    envelope advisory) and the orphan-cleanup failure (in the log)."""
    if blob_path is None:
        return
    try:
        blob_path.unlink(missing_ok=True)
    except OSError as exc:
        _LOG.error("orphan blob cleanup failed: path=%s errno=%s: %s", blob_path, exc.errno, exc)


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
    caveats: tuple[str, ...] = (),
    discipline_reminder: str | None = None,
    blob_path: Path | None = None,
    exit_code: int | None = None,
    result_sha256: str | None = None,
    extra_argv: list[str] | None = None,
) -> ToolResponse[TPayload]:
    """Build refusal envelope + audit row. Pre-subprocess refusals get
    an empty-sentinel :class:`DataProvenance`; post-subprocess refusals
    carry the real blob path + hash so the verifier can re-check.

    ``caveats`` and ``discipline_reminder`` propagate from the wrapper
    on the refuse path so downstream agents can still tell which tool
    refused and at what classification — empty/refused output is the
    case where action-shaping caveats matter most (an agent reading a
    blank vol_lsadump result must not infer Credential Guard from
    silence; an agent reading a refused vol_pslist must not assume the
    process list is empty)."""
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
        caveats=caveats,
        discipline_reminder=discipline_reminder,
        data_provenance=provenance,
    )


__all__ = [
    "DEFAULT_TIMEOUT_S",
    "VOL_BIN",
    "VolFailureReason",
    "_VolResult",
    "_run_vol",
    "blob_path_for",
    "caveats_for",
    "cmd_argv_for",
    "delete_orphan_blob",
    "persist_blob",
    "refuse",
    "truncated_stderr",
    "write_audit_row",
]
