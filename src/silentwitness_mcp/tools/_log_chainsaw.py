"""Chainsaw hunt wrapper — architecture §4.2 row 17.

Domain: context/domain/06 §7.2 — Chainsaw invocation, JSON output shape,
MITRE ATT&CK extraction, cross-engine corroboration pattern.

Chainsaw is NOT pre-installed on SIFT 2026; install.sh provisions it.
context/.raw-design-research/03 §"Tools our install script MUST add" line 272.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

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
    CHAINSAW_BIN,
    CHAINSAW_MAPPING_DEFAULT,
    SIGMA_RULES_DIR,
    LogFailureReason,
    _LogResult,
    _run_native_log_tool,
)
from silentwitness_mcp.tools._log_models_chainsaw import (
    _CHAINSAW_CORROBORATION,
    CHAINSAW_CAVEATS,
    ChainsawHit,
    ChainsawLevel,
    ChainsawOutput,
)

_LOG = logging.getLogger(__name__)
_AUDIT_LOG: Final = "log.jsonl"
_STDERR_CAP: Final = 500


def _extract_system_field(entry: dict[str, Any], field: str) -> Any:
    return entry.get("document", {}).get("data", {}).get("Event", {}).get("System", {}).get(field)


def _parse_chainsaw_json(raw_bytes: bytes) -> tuple[tuple[ChainsawHit, ...], bool]:
    hits: list[ChainsawHit] = []
    truncated = False
    try:
        entries: list[Any] = json.loads(raw_bytes.decode("utf-8"))
        for entry in entries:
            if not isinstance(entry, dict):
                truncated = True
                continue
            if entry.get("kind", "individual") != "individual":
                truncated = True
                continue
            try:
                found_in = entry.get("document", {}).get("data", {})
                hits.append(
                    ChainsawHit.model_validate(
                        {
                            "Name": entry.get("name", ""),
                            "Authors": entry.get("authors", []),
                            "Tags": entry.get("tags", []),
                            "MitreAttack": entry.get("tags", []),
                            "RuleLevel": entry.get("level", ""),
                            "RuleSource": entry.get("source", "sigma"),
                            "Channel": _extract_system_field(entry, "Channel") or "",
                            "EventID": _extract_system_field(entry, "EventID") or 0,
                            "RecordID": _extract_system_field(entry, "EventRecordID") or 0,
                            "Timestamp": entry.get("timestamp", ""),
                            "FoundInLine": found_in,
                        }
                    )
                )
            except (ValidationError, TypeError, KeyError):
                truncated = True
                continue
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        truncated = True
    return tuple(hits), truncated


async def chainsaw_hunt(
    evtx_dir: Path,
    json_out: Path,
    sigma_rules_dir: Path = SIGMA_RULES_DIR,
    mapping_file: Path = CHAINSAW_MAPPING_DEFAULT,
    level: ChainsawLevel | None = None,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = 600.0,
) -> ToolResponse[ChainsawOutput]:
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
    ) -> ToolResponse[ChainsawOutput]:
        _LOG.warning("chainsaw_hunt refused: %s | %s", r.value, advisory[:200])
        ms = (time.monotonic() - t0) * 1000.0
        _sha = sha or "0" * 64
        params: dict[str, object] = {
            "evtx_dir": str(evtx_dir),
            "sigma_rules_dir": str(sigma_rules_dir),
            "mapping_file": str(mapping_file),
            "level": level,
        }
        if extra_params:
            params.update(extra_params)
        try:
            append_jsonl_line(
                _log,
                AuditEntry(
                    ts=datetime.now(UTC),
                    audit_id=audit_id,
                    tool="chainsaw_hunt",
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
            _LOG.error("chainsaw_hunt: audit write failed: %s", _ae, exc_info=True)
        prov = (
            DataProvenance(
                tool="chainsaw_hunt",
                stdout_path=bp or Path("/dev/null"),
                result_sha256=_sha,
                elapsed_ms=ms,
                cmd_argv=argv,
            )
            if (bp or argv)
            else make_empty_provenance("chainsaw_hunt")
        )
        return ToolResponse[ChainsawOutput](
            success=False,
            data=None,
            audit_id=audit_id,
            examiner=audit_logger.examiner,
            advisories=(advisory, r.value),
            caveats=CHAINSAW_CAVEATS,
            corroboration=_CHAINSAW_CORROBORATION,
            data_provenance=prov,
        )

    try:
        evtx_files = sorted(evtx_dir.glob("*.evtx"))
    except OSError as exc:
        return _fail(LogFailureReason.EVIDENCE_NOT_REGISTERED, f"EVIDENCE_DIR_UNREADABLE: {exc}")
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
    if not CHAINSAW_BIN.exists():
        return _fail(
            LogFailureReason.CHAINSAW_NOT_INSTALLED,
            "Chainsaw is NOT pre-installed on SIFT 2026 — run install.sh to add it"
            " (see context/.raw-design-research/03 §'Tools our install script MUST add')",
        )
    if not mapping_file.exists():
        return _fail(
            LogFailureReason.CHAINSAW_MAPPING_MISSING,
            f"CHAINSAW_MAPPING_MISSING: {mapping_file} absent — run install.sh"
            " (install_chainsaw extracts mappings to /opt/chainsaw/mappings/)",
        )
    if not sigma_rules_dir.exists() or not any(sigma_rules_dir.glob("**/*.yml")):
        return _fail(
            LogFailureReason.SIGMA_RULES_MISSING,
            f"SIGMA_RULES_MISSING: {sigma_rules_dir} missing or empty — run install.sh"
            " which runs `git clone https://github.com/SigmaHQ/sigma /opt/sigma`",
        )
    try:
        json_out.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _fail(LogFailureReason.TOOL_FAILED, f"JSON_OUT_DIR_FAILED: {exc}")

    argv_list: list[str] = [
        "hunt",
        "-e",
        str(evtx_dir),
        "--sigma",
        str(sigma_rules_dir),
        "--mapping",
        str(mapping_file),
        "-j",
        str(json_out),
        "--quiet",
        "--no-color",
    ]
    if level is not None:
        level_arg = "high,critical" if level == "high" else level
        argv_list += ["--level", level_arg]
    cmd_argv = (str(CHAINSAW_BIN), *argv_list)

    try:
        result: _LogResult = await _run_native_log_tool(
            CHAINSAW_BIN, argv_list, timeout_s=timeout_s
        )
    except TimeoutError:
        return _fail(
            LogFailureReason.TOOL_TIMEOUT,
            f"TOOL_TIMEOUT: timed out after {timeout_s}s",
            argv=cmd_argv,
        )
    except OSError as exc:
        return _fail(LogFailureReason.TOOL_FAILED, f"TOOL_SPAWN_FAILED: {exc}", argv=cmd_argv)

    if result.exit_code != 0:
        stderr_snippet = result.stderr[:_STDERR_CAP].decode("utf-8", errors="replace")
        return _fail(
            LogFailureReason.TOOL_FAILED,
            f"TOOL_FAILED: exit {result.exit_code}; stderr: {stderr_snippet}",
            argv=cmd_argv,
            extra_params={"exit_code": result.exit_code},
        )

    try:
        raw_json = json_out.read_bytes()
    except FileNotFoundError:
        return _fail(
            LogFailureReason.OUTPUT_PARSE_FAILED,
            f"OUTPUT_PARSE_FAILED: no JSON at {json_out}",
            argv=cmd_argv,
        )
    except OSError as exc:
        return _fail(
            LogFailureReason.OUTPUT_PARSE_FAILED,
            f"OUTPUT_PARSE_FAILED: {exc}",
            argv=cmd_argv,
        )

    sha = hashlib.sha256(raw_json).hexdigest()
    hits, truncated = _parse_chainsaw_json(raw_json)
    if not hits and truncated:
        return _fail(
            LogFailureReason.OUTPUT_PARSE_FAILED,
            f"OUTPUT_PARSE_FAILED: 0 usable entries; first 200 bytes: {raw_json[:200]!r}",
            argv=cmd_argv,
        )

    try:
        blob_path = persist_blob(case_dir, audit_id, raw_json)
    except OSError as exc:
        return _fail(LogFailureReason.TOOL_FAILED, f"BLOB_PERSIST_FAILED: {exc}", argv=cmd_argv)

    output = ChainsawOutput(hits=hits, truncated=truncated)
    elapsed = (time.monotonic() - t0) * 1000.0
    advisories: tuple[str, ...] = ()
    if truncated:
        advisories = (
            *advisories,
            f"partial parse: {len(hits)} entries recovered before truncation",
        )

    try:
        append_jsonl_line(
            _log,
            AuditEntry(
                ts=datetime.now(UTC),
                audit_id=audit_id,
                tool="chainsaw_hunt",
                params={
                    "evtx_dir": str(evtx_dir),
                    "sigma_rules_dir": str(sigma_rules_dir),
                    "mapping_file": str(mapping_file),
                    "level": level,
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
        _LOG.error("chainsaw_hunt: success audit write failed: %s", _ae, exc_info=True)
        delete_orphan_blob(blob_path)
        return _fail(
            LogFailureReason.TOOL_FAILED,
            f"AUDIT_WRITE_FAILED: result produced but audit trail could not be written; {_ae}",
            argv=cmd_argv,
        )
    return ToolResponse[ChainsawOutput](
        success=True,
        data=output,
        audit_id=audit_id,
        examiner=audit_logger.examiner,
        advisories=advisories,
        caveats=CHAINSAW_CAVEATS,
        corroboration=_CHAINSAW_CORROBORATION,
        data_provenance=DataProvenance(
            tool="chainsaw_hunt",
            stdout_path=blob_path,
            result_sha256=sha,
            elapsed_ms=elapsed,
            cmd_argv=cmd_argv,
        ),
    )


__all__ = ["ChainsawLevel", "chainsaw_hunt"]
