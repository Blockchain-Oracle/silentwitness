"""Hayabusa csv-timeline wrapper — architecture §4.2 row 16.

Domain: context/domain/06 §7.1 — Hayabusa invocation, CSV column shapes,
super-verbose profile, MITRE ATT&CK column extraction.

Hayabusa is NOT pre-installed on SIFT 2026; install.sh provisions it.
context/.raw-design-research/03 §Network forensics line 167 + §"Tools our
install script MUST add" lines 271, 279.
"""

from __future__ import annotations

import csv
import hashlib
import io
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal

from pydantic import ValidationError

from silentwitness_common.atomic_io import append_jsonl_line
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
from silentwitness_mcp.tools._disk_common import delete_orphan_blob, persist_blob
from silentwitness_mcp.tools._log_common import (
    HAYABUSA_BIN,
    HAYABUSA_RULES_DIR,
    LogFailureReason,
    _LogResult,
    _run_native_log_tool,
)
from silentwitness_mcp.tools._log_models_hayabusa import (
    _HAYABUSA_CORROBORATION,
    HAYABUSA_CAVEATS,
    HayabusaHit,
    HayabusaOutput,
)

_LOG = logging.getLogger(__name__)
_AUDIT_LOG: Final = "log.jsonl"
_STDERR_CAP: Final = 500

HayabusaLevel = Literal["informational", "low", "medium", "high", "critical"]


def _parse_hayabusa_csv(raw_bytes: bytes) -> tuple[tuple[HayabusaHit, ...], bool]:
    hits: list[HayabusaHit] = []
    truncated = False
    try:
        text = raw_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text, newline=""))
        for row in reader:
            if any(v is None for v in row.values()):
                truncated = True
                break
            try:
                hits.append(HayabusaHit.model_validate(row))
            except ValidationError:
                truncated = True
                continue
    except (csv.Error, UnicodeDecodeError):
        truncated = True
    return tuple(hits), truncated


async def hayabusa_csv_timeline(
    evtx_dir: Path,
    csv_out: Path,
    min_level: HayabusaLevel | None = None,
    include_tags: list[str] | None = None,
    profile: Literal[
        "minimal", "standard", "verbose", "super-verbose", "all-field-info"
    ] = "super-verbose",
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = 600.0,
) -> ToolResponse[HayabusaOutput]:
    t0 = time.monotonic()
    audit_id = audit_logger.next_audit_id()
    _log = case_dir / "audit" / _AUDIT_LOG

    def _fail(
        r: LogFailureReason,
        advisory: str,
        *,
        bp: Path | None = None,
        sha: str | None = None,
        argv: tuple[str, ...] = (),
        extra_params: dict[str, object] | None = None,
    ) -> ToolResponse[HayabusaOutput]:
        _LOG.warning("hayabusa_csv_timeline refused: %s | %s", r.value, advisory[:200])
        ms = (time.monotonic() - t0) * 1000.0
        _sha = sha or "0" * 64
        params: dict[str, object] = {
            "evtx_dir": str(evtx_dir),
            "min_level": min_level,
            "include_tags": include_tags,
            "profile": profile,
        }
        if extra_params:
            params.update(extra_params)
        try:
            append_jsonl_line(
                _log,
                AuditEntry(
                    ts=datetime.now(UTC),
                    audit_id=audit_id,
                    tool="hayabusa_csv_timeline",
                    params=params,
                    result_summary={"reason": r.value},
                    result_sha256=_sha,
                    stdout_path=bp or Path("/dev/null"),
                    elapsed_ms=ms,
                    examiner=audit_logger.examiner,
                    model_used=model_used,
                    model_token_count={},
                ).model_dump_json(),
            )
        except Exception as _ae:
            _LOG.error("hayabusa_csv_timeline: audit write failed: %s", _ae, exc_info=True)
        if bp or argv:
            prov = DataProvenance(
                tool="hayabusa_csv_timeline",
                stdout_path=bp or Path("/dev/null"),
                result_sha256=_sha,
                elapsed_ms=ms,
                cmd_argv=argv,
            )
        else:
            prov = make_empty_provenance("hayabusa_csv_timeline")
        return ToolResponse[HayabusaOutput](
            success=False,
            data=None,
            audit_id=audit_id,
            examiner=audit_logger.examiner,
            advisories=(advisory, r.value),
            caveats=HAYABUSA_CAVEATS,
            corroboration=_HAYABUSA_CORROBORATION,
            data_provenance=prov,
        )

    # §4.10: assert_registered for each *.evtx file in the directory
    try:
        evtx_files = sorted(evtx_dir.glob("*.evtx"))
    except OSError as exc:
        return _fail(
            LogFailureReason.EVIDENCE_NOT_REGISTERED,
            f"EVIDENCE_DIR_UNREADABLE: cannot enumerate {evtx_dir}: {exc}",
        )
    if not evtx_files:
        return _fail(
            LogFailureReason.EVIDENCE_NOT_REGISTERED,
            f"EVIDENCE_NOT_REGISTERED: no *.evtx files found in {evtx_dir}",
        )
    unregistered: list[str] = []
    for evtx_path in evtx_files:
        try:
            evidence_registry.assert_registered(evtx_path)
        except EvidenceNotRegisteredError:
            unregistered.append(str(evtx_path))
        except EvidenceMissingOnDiskError:
            return _fail(
                LogFailureReason.EVIDENCE_TAMPERED,
                f"EVIDENCE_MISSING_ON_DISK: {evtx_path} absent at assert_registered",
            )
        except EvidenceRegistryError as exc:
            return _fail(
                LogFailureReason.EVIDENCE_TAMPERED,
                f"EVIDENCE_REGISTRY_ERROR at assert_registered: {type(exc).__name__}: {exc}",
            )
    if unregistered:
        return _fail(
            LogFailureReason.EVIDENCE_NOT_REGISTERED,
            f"EVIDENCE_NOT_REGISTERED: {len(unregistered)} file(s) not registered:"
            f" {unregistered[:3]}{'...' if len(unregistered) > 3 else ''}",
        )
    for evtx_path in evtx_files:
        try:
            verify = evidence_registry.verify_hash(evtx_path)
        except EvidenceMissingOnDiskError:
            return _fail(
                LogFailureReason.EVIDENCE_TAMPERED,
                f"EVIDENCE_MISSING_ON_DISK: {evtx_path} vanished since registration",
            )
        except EvidenceRegistryError as exc:
            return _fail(
                LogFailureReason.EVIDENCE_TAMPERED,
                f"EVIDENCE_REGISTRY_ERROR: {type(exc).__name__}: {exc}",
            )
        if not verify.matches:
            return _fail(
                LogFailureReason.EVIDENCE_TAMPERED,
                f"EVIDENCE_TAMPERED: SHA256 drift on {evtx_path}"
                f" expected={verify.expected} actual={verify.actual}",
            )
    mount = check_mount()
    if not mount.ok:
        return _fail(
            LogFailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID,
            f"MOUNT_NOT_RO_NOEXEC_NOSUID: {'; '.join(mount.advisories) or 'no detail'}",
        )
    if not HAYABUSA_BIN.exists():
        return _fail(
            LogFailureReason.HAYABUSA_NOT_INSTALLED,
            "Hayabusa is NOT pre-installed on SIFT 2026 — run install.sh to add it"
            " (see context/.raw-design-research/03 §'Tools our install script MUST add')",
        )
    if not HAYABUSA_RULES_DIR.exists() or not any(HAYABUSA_RULES_DIR.glob("**/*.yml")):
        return _fail(
            LogFailureReason.HAYABUSA_RULES_MISSING,
            "HAYABUSA_RULES_MISSING: install.sh runs"
            " `git clone https://github.com/Yamato-Security/hayabusa-rules"
            " /opt/hayabusa-rules`",
        )
    try:
        csv_out.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _fail(
            LogFailureReason.TOOL_FAILED,
            f"CSV_OUT_DIR_FAILED: cannot create {csv_out.parent}: {exc}",
        )
    argv_list: list[str] = [
        "csv-timeline",
        "-d",
        str(evtx_dir),
        "-o",
        str(csv_out),
        "-p",
        profile,
        "--quiet",
        "--no-color",
        "--UTC",
        "-r",
        str(HAYABUSA_RULES_DIR),
    ]
    if min_level is not None:
        argv_list += ["--min-level", min_level]
    if include_tags:
        argv_list += ["--include-tag", ",".join(include_tags)]
    cmd_argv = (str(HAYABUSA_BIN), *argv_list)
    try:
        result: _LogResult = await _run_native_log_tool(
            HAYABUSA_BIN, argv_list, timeout_s=timeout_s
        )
    except TimeoutError:
        return _fail(
            LogFailureReason.TOOL_TIMEOUT,
            f"TOOL_TIMEOUT: Hayabusa timed out after {timeout_s}s",
            argv=cmd_argv,
        )
    except OSError as exc:
        return _fail(
            LogFailureReason.TOOL_FAILED,
            f"TOOL_SPAWN_FAILED: could not exec hayabusa: {exc}",
            argv=cmd_argv,
        )
    if result.exit_code != 0:
        stderr_snippet = result.stderr[:_STDERR_CAP].decode("utf-8", errors="replace")
        return _fail(
            LogFailureReason.TOOL_FAILED,
            f"TOOL_FAILED: exit {result.exit_code}; stderr: {stderr_snippet}",
            argv=cmd_argv,
            extra_params={"exit_code": result.exit_code},
        )
    try:
        raw_csv = csv_out.read_bytes()
    except FileNotFoundError:
        return _fail(
            LogFailureReason.OUTPUT_PARSE_FAILED,
            f"OUTPUT_PARSE_FAILED: Hayabusa produced no CSV at {csv_out}",
            argv=cmd_argv,
        )
    except OSError as exc:
        return _fail(
            LogFailureReason.OUTPUT_PARSE_FAILED,
            f"OUTPUT_PARSE_FAILED: cannot read {csv_out}: {exc}",
            argv=cmd_argv,
        )
    sha = hashlib.sha256(raw_csv).hexdigest()
    hits, truncated = _parse_hayabusa_csv(raw_csv)
    if not hits and truncated:
        return _fail(
            LogFailureReason.OUTPUT_PARSE_FAILED,
            f"OUTPUT_PARSE_FAILED: CSV produced 0 usable rows (truncated=True);"
            f" first 200 bytes: {raw_csv[:200]!r}",
            argv=cmd_argv,
        )
    try:
        blob_path = persist_blob(case_dir, audit_id, raw_csv)
    except OSError as exc:
        return _fail(
            LogFailureReason.TOOL_FAILED,
            f"BLOB_PERSIST_FAILED: could not write evidence blob: {exc}",
            argv=cmd_argv,
        )
    output = HayabusaOutput(hits=hits, truncated=truncated)
    elapsed = (time.monotonic() - t0) * 1000.0
    advisories: tuple[str, ...] = ()
    if truncated:
        advisories = (
            *advisories,
            f"partial parse: {len(hits)} rows recovered before truncation",
        )
    _audit_advisory: tuple[str, ...] = ()
    try:
        append_jsonl_line(
            _log,
            AuditEntry(
                ts=datetime.now(UTC),
                audit_id=audit_id,
                tool="hayabusa_csv_timeline",
                params={
                    "evtx_dir": str(evtx_dir),
                    "min_level": min_level,
                    "include_tags": include_tags,
                    "profile": profile,
                },
                result_summary={"row_count": output.row_count, "truncated": truncated},
                result_sha256=sha,
                stdout_path=blob_path,
                elapsed_ms=elapsed,
                examiner=audit_logger.examiner,
                model_used=model_used,
                model_token_count={},
            ).model_dump_json(),
        )
    except Exception as _ae:
        _LOG.error("hayabusa_csv_timeline: success audit write failed: %s", _ae, exc_info=True)
        _audit_advisory = ("AUDIT_WRITE_FAILED: audit trail entry missing for this result",)
        delete_orphan_blob(blob_path)
    return ToolResponse[HayabusaOutput](
        success=True,
        data=output,
        audit_id=audit_id,
        examiner=audit_logger.examiner,
        advisories=(*advisories, *_audit_advisory),
        caveats=HAYABUSA_CAVEATS,
        corroboration=_HAYABUSA_CORROBORATION,
        data_provenance=DataProvenance(
            tool="hayabusa_csv_timeline",
            stdout_path=blob_path,
            result_sha256=sha,
            elapsed_ms=elapsed,
            cmd_argv=cmd_argv,
        ),
    )


__all__ = ["HayabusaLevel", "hayabusa_csv_timeline"]
