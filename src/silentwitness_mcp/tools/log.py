"""Log/network tool wrappers — architecture §4.2 rows 15-17.

First wrapper: ``parse_evtx`` (EvtxECmd, §4.2 row 15).
Domain: context/domain/06 §5.2 — EvtxECmd invocation, CSV column shapes,
Security-channel EID catalog; context/domain/02 §16-18 (Sysmon catalog).

Shared helpers ``_run_dotnet_log_tool`` / ``serilog_has_errors`` in
:mod:`_log_common` are imported by the Hayabusa and Chainsaw wrappers.
"""

from __future__ import annotations

import csv
import hashlib
import io
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Final

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, computed_field

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
from silentwitness_mcp.tools._disk_common import DOTNET_BIN, persist_blob
from silentwitness_mcp.tools._log_common import (
    EVTXECMD_DLL,
    LogFailureReason,
    _LogResult,
    _run_dotnet_log_tool,
    serilog_has_errors,
)

_AUDIT_LOG: Final = "log.jsonl"
_STDERR_CAP: Final = 500


def _parse_dt(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=UTC)
    s = str(v).strip()
    # EvtxECmd emits UTC without a 'Z' suffix: "2024-01-15 08:30:00.0000000"
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


_DT = Annotated[datetime, BeforeValidator(_parse_dt)]
_OptStr = Annotated[str | None, BeforeValidator(lambda v: v if v else None)]


class EvtxRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)

    EventId: int
    Channel: str
    Provider: str
    Computer: str
    TimeCreated: _DT
    EventRecordId: str  # string in EvtxECmd output — NOT an int
    Level: str
    UserId: _OptStr = Field(default=None)
    MapDescription: _OptStr = Field(default=None)
    Payload: _OptStr = Field(default=None)
    PayloadData1: _OptStr = Field(default=None)
    PayloadData2: _OptStr = Field(default=None)
    PayloadData3: _OptStr = Field(default=None)
    PayloadData4: _OptStr = Field(default=None)
    PayloadData5: _OptStr = Field(default=None)
    PayloadData6: _OptStr = Field(default=None)


class EvtxOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    records: tuple[EvtxRecord, ...]
    truncated: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def row_count(self) -> int:
        return len(self.records)


PARSE_EVTX_CAVEATS: Final[tuple[str, ...]] = (
    "EvtxECmd cannot parse old EVT (Windows XP/2003) format; cannot render data"
    " for custom event providers whose manifests are missing — fields may appear"
    " as raw template binding",
    "Application/System logs referencing absent provider manifests render EventData"
    " as raw XML payload rather than friendly columns; corroborate with"
    " hayabusa_csv_timeline for rule-tagged interpretation",
)

_PARSE_EVTX_CORROBORATION: Final[tuple[str, ...]] = (
    "hayabusa_csv_timeline — Sigma-rule-driven timeline over the same EVTX channel",
    "chainsaw_hunt — lateral-movement and persistence rule set over the same EVTX",
)


# Canonical Security-channel EID list for --inc translation.
# EvtxECmd's --inc filters by EID, NOT by channel name literal.
def _security_channel_eid_list() -> list[int]:
    return [
        1102,
        4624,
        4625,
        4634,
        4647,
        4648,
        4672,
        4673,
        4674,
        4688,
        4697,
        4698,
        4702,
        4720,
        4722,
        4723,
        4724,
        4725,
        4732,
        4738,
        4740,
        4756,
        4768,
        4769,
        4771,
        4776,
        5140,
        5145,
        5156,
        5158,
    ]


def _parse_evtx_csv(raw_bytes: bytes) -> tuple[tuple[EvtxRecord, ...], bool]:
    records: list[EvtxRecord] = []
    truncated = False
    try:
        text = raw_bytes.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text, newline=""))
        for row in reader:
            if any(v is None for v in row.values()):
                truncated = True
                break
            try:
                records.append(EvtxRecord.model_validate(row))
            except Exception:
                truncated = True
                break
    except csv.Error:
        truncated = True
    return tuple(records), truncated


async def parse_evtx(
    evidence_path: Path,
    csv_out: Path,
    channel: str | None = None,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = 600.0,
) -> ToolResponse[EvtxOutput]:
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
    ) -> ToolResponse[EvtxOutput]:
        ms = (time.monotonic() - t0) * 1000.0
        _sha = sha or hashlib.sha256(r.value.encode()).hexdigest()
        params: dict[str, object] = {"evidence_path": str(evidence_path)}
        if extra_params:
            params.update(extra_params)
        append_jsonl_line(
            _log,
            AuditEntry(
                ts=datetime.now(UTC),
                audit_id=audit_id,
                tool="parse_evtx",
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
        prov = (
            DataProvenance(
                tool="parse_evtx",
                stdout_path=bp,
                result_sha256=_sha,
                elapsed_ms=ms,
                cmd_argv=argv,
            )
            if bp
            else make_empty_provenance("parse_evtx")
        )
        return ToolResponse[EvtxOutput](
            success=False,
            data=None,
            audit_id=audit_id,
            examiner=audit_logger.examiner,
            advisories=(advisory, r.value),
            caveats=PARSE_EVTX_CAVEATS,
            corroboration=_PARSE_EVTX_CORROBORATION,
            data_provenance=prov,
        )

    # Gate 1: evidence registered (§4.10 — first action)
    try:
        evidence_registry.assert_registered(evidence_path)
    except EvidenceNotRegisteredError:
        return _fail(
            LogFailureReason.EVIDENCE_NOT_REGISTERED,
            f"EVIDENCE_NOT_REGISTERED: {evidence_path}",
        )
    # Gate 2: hash stable
    try:
        verify = evidence_registry.verify_hash(evidence_path)
    except EvidenceMissingOnDiskError:
        return _fail(
            LogFailureReason.EVIDENCE_TAMPERED,
            f"EVIDENCE_MISSING_ON_DISK: {evidence_path} vanished since registration",
        )
    except EvidenceRegistryError as exc:
        return _fail(
            LogFailureReason.EVIDENCE_TAMPERED,
            f"EVIDENCE_REGISTRY_ERROR: {type(exc).__name__}: {exc}",
        )
    if not verify.matches:
        return _fail(
            LogFailureReason.EVIDENCE_TAMPERED,
            f"EVIDENCE_TAMPERED: SHA256 drift on {evidence_path}"
            f" expected={verify.expected} actual={verify.actual}",
        )
    # Gate 3: mount
    mount = check_mount()
    if not mount.ok:
        return _fail(
            LogFailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID,
            f"MOUNT_NOT_RO_NOEXEC_NOSUID: {'; '.join(mount.advisories) or 'no detail'}",
        )
    # Gate 4: dotnet
    if not DOTNET_BIN.exists():
        return _fail(
            LogFailureReason.DOTNET_NOT_FOUND,
            f"DOTNET_NOT_FOUND: {DOTNET_BIN} absent — rerun install.sh to provision SIFT 2026",
        )
    # Gate 5: EvtxECmd DLL
    if not EVTXECMD_DLL.exists():
        return _fail(
            LogFailureReason.EVTXECMD_NOT_FOUND,
            f"EVTXECMD_NOT_FOUND: {EVTXECMD_DLL} absent — note inner 'EvtxeCmd/' dir"
            " (lowercase 'e') per context/.raw-design-research/03 line 115",
        )
    # Build argv
    argv_list = ["-f", str(evidence_path), "--csv", str(csv_out)]
    if channel == "Security":
        eids = _security_channel_eid_list()
        argv_list += ["--inc", ",".join(str(e) for e in eids)]
    cmd_argv = (str(DOTNET_BIN), str(EVTXECMD_DLL), *argv_list)
    # Spawn
    result: _LogResult
    try:
        result = await _run_dotnet_log_tool(EVTXECMD_DLL, argv_list, timeout_s=timeout_s)
    except TimeoutError:
        return _fail(
            LogFailureReason.TOOL_TIMEOUT,
            f"TOOL_TIMEOUT: EvtxECmd timed out after {timeout_s}s",
            argv=cmd_argv,
        )
    # Serilog error detection (exit code unreliable — Environment.Exit(0) on errors)
    if result.exit_code != 0 or serilog_has_errors(result.stderr):
        stderr_snippet = result.stderr[:_STDERR_CAP].decode("utf-8", errors="replace")
        return _fail(
            LogFailureReason.TOOL_FAILED,
            f"TOOL_FAILED: exit {result.exit_code}; stderr: {stderr_snippet}",
            argv=cmd_argv,
            extra_params={"exit_code": result.exit_code},
        )
    # Find CSV output
    csv_files = sorted(csv_out.glob("*.csv"), key=lambda p: p.stat().st_mtime)
    if not csv_files:
        return _fail(
            LogFailureReason.OUTPUT_PARSE_FAILED,
            f"OUTPUT_PARSE_FAILED: no CSV produced in {csv_out}",
            argv=cmd_argv,
        )
    raw_csv = csv_files[-1].read_bytes()
    sha = hashlib.sha256(raw_csv).hexdigest()
    records, truncated = _parse_evtx_csv(raw_csv)
    if not records and not truncated:
        return _fail(
            LogFailureReason.OUTPUT_PARSE_FAILED,
            f"OUTPUT_PARSE_FAILED: CSV unparseable; first 200 bytes: {raw_csv[:200]!r}",
            argv=cmd_argv,
        )
    blob_path = persist_blob(case_dir, audit_id, raw_csv)
    output = EvtxOutput(records=records, truncated=truncated)
    elapsed = (time.monotonic() - t0) * 1000.0
    advisories: tuple[str, ...] = (
        (f"partial parse: {len(records)} rows recovered before truncation",) if truncated else ()
    )
    append_jsonl_line(
        _log,
        AuditEntry(
            ts=datetime.now(UTC),
            audit_id=audit_id,
            tool="parse_evtx",
            params={"evidence_path": str(evidence_path), "channel": channel},
            result_summary={"row_count": output.row_count, "truncated": truncated},
            result_sha256=sha,
            stdout_path=blob_path,
            elapsed_ms=elapsed,
            examiner=audit_logger.examiner,
            model_used=model_used,
            model_token_count={},
        ).model_dump_json(),
    )
    return ToolResponse[EvtxOutput](
        success=True,
        data=output,
        audit_id=audit_id,
        examiner=audit_logger.examiner,
        advisories=advisories,
        caveats=PARSE_EVTX_CAVEATS,
        corroboration=_PARSE_EVTX_CORROBORATION,
        data_provenance=DataProvenance(
            tool="parse_evtx",
            stdout_path=blob_path,
            result_sha256=sha,
            elapsed_ms=elapsed,
            cmd_argv=cmd_argv,
        ),
    )


__all__ = [
    "PARSE_EVTX_CAVEATS",
    "EvtxOutput",
    "EvtxRecord",
    "parse_evtx",
]
