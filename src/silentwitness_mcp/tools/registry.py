"""RegRipper3.0 (rip.pl) wrapper — architecture §4.2 row 19,
§4.4 registry audit channel, context/.raw-design-research/03 line 95.
Domain: context/domain/06 §6.1 — UserAssist, USB, BAM/DAM, run keys.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Final

from pydantic import BaseModel

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
from silentwitness_mcp.tools._disk_common import persist_blob

RIP_BIN: Final = Path("/usr/local/bin/rip.pl")
_AUDIT_LOG: Final = "registry.jsonl"
_DEFAULT_TIMEOUT_S: Final = 60.0
_TERMINATE_GRACE_S: Final = 5.0
_ANSI_RE: Final = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_KEY_RE: Final = re.compile(r"^\s*(?:Key|Key path):\s+(.+)$", re.MULTILINE)
_KNOWN_PLUGINS: frozenset[str] | None = None


class RegistryFailureReason(StrEnum):
    REGRIPPER_NOT_INSTALLED = "REGRIPPER_NOT_INSTALLED"
    PLUGIN_NOT_FOUND = "PLUGIN_NOT_FOUND"
    EVIDENCE_NOT_REGISTERED = "EVIDENCE_NOT_REGISTERED"
    EVIDENCE_HASH_MISMATCH = "EVIDENCE_HASH_MISMATCH"
    MOUNT_NOT_RO_NOEXEC_NOSUID = "MOUNT_NOT_RO_NOEXEC_NOSUID"
    PARSE_FAILED = "PARSE_FAILED"


class RegripperOutput(BaseModel, frozen=True):
    hive_path: str
    plugin_name: str
    output_text: str
    parsed_keys: list[str]
    line_count: int


REGRIPPER_CAVEATS: Final[tuple[str, ...]] = (
    "RegRipper output is structured text — values must be cited as verbatim lines"
    " from the stored blob, not paraphrased",
    "RegRipper3.0 replays dirty hive transaction logs (.LOG1/.LOG2); older RegRipper 2.x"
    " does not — confirm rip.pl version if a Run-key value seems missing",
    "Registry LastWriteTime is per-key, not per-value — a key's LastWriteTime tells you"
    " SOME value changed at that time, not which one",
)


async def _get_known_plugins() -> frozenset[str]:
    global _KNOWN_PLUGINS
    if _KNOWN_PLUGINS is not None:
        return _KNOWN_PLUGINS
    proc = await asyncio.create_subprocess_exec(
        str(RIP_BIN), "-l", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, _ = await asyncio.wait_for(proc.communicate(), timeout=30.0)
    _KNOWN_PLUGINS = frozenset(
        p[0]
        for line in out.decode("utf-8", errors="replace").splitlines()
        if (p := line.strip().split()) and p[0][0].isalpha()
    )
    return _KNOWN_PLUGINS


async def regripper_run(
    hive_path: Path,
    plugin_name: str,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> ToolResponse[RegripperOutput]:
    t0 = time.monotonic()
    audit_id = audit_logger.next_audit_id()
    _log = case_dir / "audit" / _AUDIT_LOG

    def _fail(
        r: RegistryFailureReason,
        advisory: str,
        *,
        bp: Path | None = None,
        sha: str | None = None,
        argv: tuple[str, ...] = (),
    ) -> ToolResponse[RegripperOutput]:
        ms = (time.monotonic() - t0) * 1000.0
        _sha = sha or hashlib.sha256(r.value.encode()).hexdigest()
        append_jsonl_line(
            _log,
            AuditEntry(
                ts=datetime.now(UTC),
                audit_id=audit_id,
                tool="regripper_run",
                params={"hive_path": str(hive_path), "plugin_name": plugin_name},
                result_summary={"reason": r.value},
                result_sha256=_sha,
                stdout_path=bp or Path("/dev/null"),
                elapsed_ms=ms,
                examiner=audit_logger.examiner,
                model_used=model_used,
                model_token_count={},
            ).model_dump_json(),
        )
        prov = (
            DataProvenance(
                tool="regripper_run",
                stdout_path=bp,
                result_sha256=_sha,
                elapsed_ms=ms,
                cmd_argv=argv,
            )
            if bp
            else make_empty_provenance("regripper_run")
        )
        return ToolResponse[RegripperOutput](
            success=False,
            data=None,
            audit_id=audit_id,
            examiner=audit_logger.examiner,
            advisories=(advisory, r.value),
            caveats=REGRIPPER_CAVEATS,
            corroboration=(),
            data_provenance=prov,
        )

    if not RIP_BIN.exists():
        return _fail(
            RegistryFailureReason.REGRIPPER_NOT_INSTALLED,
            f"REGRIPPER_NOT_INSTALLED — RegRipper3.0 expected at {RIP_BIN} per SIFT 2026 saltstack",
        )
    known = await _get_known_plugins()
    if plugin_name not in known:
        return _fail(
            RegistryFailureReason.PLUGIN_NOT_FOUND,
            f"PLUGIN_NOT_FOUND: {plugin_name} — run '{RIP_BIN} -l' to enumerate valid plugins",
        )
    mount = check_mount()
    if not mount.ok:
        return _fail(
            RegistryFailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID,
            f"MOUNT_NOT_RO_NOEXEC_NOSUID: {'; '.join(mount.advisories) or 'no detail'}",
        )
    try:
        evidence_registry.assert_registered(hive_path)
    except EvidenceNotRegisteredError:
        return _fail(
            RegistryFailureReason.EVIDENCE_NOT_REGISTERED,
            f"EVIDENCE_NOT_REGISTERED: {hive_path}",
        )
    try:
        verify = evidence_registry.verify_hash(hive_path)
    except (EvidenceMissingOnDiskError, EvidenceRegistryError):
        return _fail(
            RegistryFailureReason.EVIDENCE_HASH_MISMATCH,
            f"EVIDENCE_HASH_MISMATCH: evidence error for {hive_path}",
        )
    if not verify.matches:
        return _fail(
            RegistryFailureReason.EVIDENCE_HASH_MISMATCH,
            f"EVIDENCE_HASH_MISMATCH: SHA256 drift on {hive_path}",
        )
    cmd_argv = (str(RIP_BIN), "-r", str(hive_path), "-p", plugin_name)
    proc = await asyncio.create_subprocess_exec(
        *cmd_argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except TimeoutError:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=_TERMINATE_GRACE_S)
        except TimeoutError:
            proc.kill()
        return _fail(
            RegistryFailureReason.PARSE_FAILED,
            f"PARSE_FAILED: rip.pl timed out after {timeout_s}s",
            argv=cmd_argv,
        )
    exit_code = proc.returncode if proc.returncode is not None else -1
    raw = _ANSI_RE.sub("", stdout.decode("utf-8", errors="replace"))
    normalized = "\n".join(ln.rstrip() for ln in raw.replace("\r\n", "\n").splitlines())
    blob_bytes = normalized.encode("utf-8")
    sha = hashlib.sha256(blob_bytes).hexdigest()
    if exit_code != 0:
        bp = persist_blob(case_dir, audit_id, blob_bytes)
        return _fail(
            RegistryFailureReason.PARSE_FAILED,
            f"PARSE_FAILED: exit {exit_code}; stderr: {stderr[:500].decode('utf-8', 'replace')}",
            bp=bp,
            sha=sha,
            argv=cmd_argv,
        )
    blob_path = persist_blob(case_dir, audit_id, blob_bytes)
    parsed_keys = [m.group(1).strip() for m in _KEY_RE.finditer(normalized)]
    output = RegripperOutput(
        hive_path=str(hive_path),
        plugin_name=plugin_name,
        output_text=normalized,
        parsed_keys=parsed_keys,
        line_count=sum(1 for ln in normalized.splitlines() if ln.strip()),
    )
    elapsed = (time.monotonic() - t0) * 1000.0
    append_jsonl_line(
        _log,
        AuditEntry(
            ts=datetime.now(UTC),
            audit_id=audit_id,
            tool="regripper_run",
            params={"hive_path": str(hive_path), "plugin_name": plugin_name},
            result_summary={"line_count": output.line_count, "keys": parsed_keys[:10]},
            result_sha256=sha,
            stdout_path=blob_path,
            elapsed_ms=elapsed,
            examiner=audit_logger.examiner,
            model_used=model_used,
            model_token_count={},
        ).model_dump_json(),
    )
    return ToolResponse[RegripperOutput](
        success=True,
        data=output,
        audit_id=audit_id,
        examiner=audit_logger.examiner,
        advisories=(),
        caveats=REGRIPPER_CAVEATS,
        corroboration=(),
        data_provenance=DataProvenance(
            tool="regripper_run",
            stdout_path=blob_path,
            result_sha256=sha,
            elapsed_ms=elapsed,
            cmd_argv=cmd_argv,
        ),
    )


__all__ = ["REGRIPPER_CAVEATS", "RegistryFailureReason", "RegripperOutput", "regripper_run"]
