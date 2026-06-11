"""Network tool wrappers — architecture §4.2 rows 18-19.

Wrappers: ``zeek_run`` (Zeek offline pcap replay, §4.2 row 18),
``suricata_run`` (story-suricata-run, §4.2 row 19).
Domain: context/domain/04 §20 — Zeek architecture + log catalog.

Unlike single-stream tools (Vol3, EvtxECmd), Zeek produces a directory of
logs. The audit blob is a deterministic manifest: one line per *.log file in
``<filename> <sha256> <line_count>`` format, sorted by filename. The SHA256
of that manifest is the result_sha256 for the run. Per-log SHA256s enable
citation-gate fine-grained evidence references (cite specific log files).
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Final

from pydantic import BaseModel, ConfigDict, Field, computed_field

from silentwitness_common.atomic_io import append_jsonl_line
from silentwitness_common.types import AuditEntry, DataProvenance, Sha256Hex, ToolResponse
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
from silentwitness_mcp.tools._network_common import (
    NetworkFailureReason,
    _NetworkResult,
    _run_zeek,
    get_zeek_bin,
)

_LOG = logging.getLogger(__name__)
_AUDIT_LOG: Final = "network.jsonl"
_STDERR_CAP: Final = 500

ZEEK_CAVEATS: Final[tuple[str, ...]] = (
    "Zeek base scripts produce a fixed set of logs; custom scripts"
    " (e.g., ja3.zeek for SSL fingerprints) must be loaded explicitly"
    " — absent custom scripts, ssl.log.ja3 will not populate",
    "Zeek runs from cwd by default — output landed in <out_dir>;"
    " weird.log entries are protocol anomalies, often the first hint of"
    " evasive C2 (corroborate with notice.log)",
    "conn.log is the spine — every flow has one entry; subsidiary logs"
    " (http.log, dns.log, ssl.log) join back via the uid field",
    "-C flag includes packets with bad checksums; cross-check weird.log"
    " for protocol anomalies before treating noisy conn.log entries as"
    " ground truth",
)

ZEEK_CORROBORATION: Final[tuple[str, ...]] = (
    "run suricata_run on the same pcap for IDS-rule-driven detection"
    " (Zeek answers 'what protocols ran'; Suricata answers 'which rules fired')",
    "cross-reference conn.log uid with http.log/dns.log/ssl.log to trace"
    " a specific flow through all protocol layers",
)


class ZeekLogInfo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    path: Path
    line_count: Annotated[int, Field(ge=0)]
    sha256: Sha256Hex


class ZeekRunResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    log_dir: Path
    conn_log: ZeekLogInfo
    http_log: ZeekLogInfo | None = None
    dns_log: ZeekLogInfo | None = None
    ssl_log: ZeekLogInfo | None = None
    files_log: ZeekLogInfo | None = None
    x509_log: ZeekLogInfo | None = None
    notice_log: ZeekLogInfo | None = None
    weird_log: ZeekLogInfo | None = None
    other_logs: dict[str, ZeekLogInfo] = Field(default_factory=dict)

    def _canonical(self) -> tuple[ZeekLogInfo | None, ...]:
        return (
            self.conn_log,
            self.http_log,
            self.dns_log,
            self.ssl_log,
            self.files_log,
            self.x509_log,
            self.notice_log,
            self.weird_log,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_logs(self) -> int:
        return sum(1 for f in self._canonical() if f is not None) + len(self.other_logs)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_lines(self) -> int:
        return sum(f.line_count for f in self._canonical() if f is not None) + sum(
            v.line_count for v in self.other_logs.values()
        )


_CANONICAL_LOGS: Final[frozenset[str]] = frozenset(
    {"conn", "http", "dns", "ssl", "files", "x509", "notice", "weird"}
)


def _inventory_zeek_logs(log_dir: Path) -> dict[str, ZeekLogInfo] | None:
    result: dict[str, ZeekLogInfo] = {}
    try:
        for p in sorted(log_dir.glob("*.log")):
            raw = p.read_bytes()
            line_count = raw.count(b"\n")
            sha = hashlib.sha256(raw).hexdigest()
            result[p.stem] = ZeekLogInfo(path=p, line_count=line_count, sha256=sha)
    except OSError as exc:
        _LOG.warning("zeek_run: log inventory error: %s", exc)
        return None
    return result


def _build_manifest(logs: dict[str, ZeekLogInfo]) -> bytes:
    lines = [f"{name}.log {info.sha256} {info.line_count}\n" for name, info in sorted(logs.items())]
    return "".join(lines).encode()


def _to_result(log_dir: Path, logs: dict[str, ZeekLogInfo]) -> ZeekRunResult:
    get = logs.get
    other = {k: v for k, v in logs.items() if k not in _CANONICAL_LOGS}
    return ZeekRunResult(
        log_dir=log_dir,
        conn_log=logs["conn"],
        http_log=get("http"),
        dns_log=get("dns"),
        ssl_log=get("ssl"),
        files_log=get("files"),
        x509_log=get("x509"),
        notice_log=get("notice"),
        weird_log=get("weird"),
        other_logs=other,
    )


async def zeek_run(
    pcap_path: Path,
    out_dir: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = 900.0,
) -> ToolResponse[ZeekRunResult]:
    t0 = time.monotonic()
    audit_id = audit_logger.next_audit_id()
    _log = case_dir / "audit" / _AUDIT_LOG

    def _fail(
        r: NetworkFailureReason,
        advisory: str,
        *,
        bp: Path | None = None,
        sha: str | None = None,
        argv: tuple[str, ...] = (),
        extra_params: dict[str, Any] | None = None,
    ) -> ToolResponse[ZeekRunResult]:
        _LOG.warning("zeek_run refused: %s | %s", r.value, advisory[:200])
        ms = (time.monotonic() - t0) * 1000.0
        _sha = sha or "0" * 64
        params: dict[str, Any] = {"pcap_path": str(pcap_path), "out_dir": str(out_dir)}
        if extra_params:
            params.update(extra_params)
        try:
            append_jsonl_line(
                _log,
                AuditEntry(
                    ts=datetime.now(UTC),
                    audit_id=audit_id,
                    tool="zeek_run",
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
        except (OSError, ValueError) as _ae:
            _LOG.error("zeek_run: audit write failed: %s", _ae, exc_info=True)
        prov = (
            DataProvenance(
                tool="zeek_run",
                stdout_path=bp or Path("/dev/null"),
                result_sha256=_sha,
                elapsed_ms=ms,
                cmd_argv=argv,
            )
            if (bp or argv)
            else make_empty_provenance("zeek_run")
        )
        return ToolResponse[ZeekRunResult](
            success=False,
            data=None,
            audit_id=audit_id,
            examiner=audit_logger.examiner,
            advisories=(advisory, r.value),
            caveats=ZEEK_CAVEATS,
            corroboration=ZEEK_CORROBORATION,
            data_provenance=prov,
        )

    # §4.10: assert_registered is the first action.
    try:
        evidence_registry.assert_registered(pcap_path)
    except EvidenceNotRegisteredError:
        return _fail(
            NetworkFailureReason.EVIDENCE_NOT_REGISTERED,
            f"EVIDENCE_NOT_REGISTERED: {pcap_path}",
        )
    except EvidenceMissingOnDiskError:
        return _fail(
            NetworkFailureReason.EVIDENCE_TAMPERED,
            f"EVIDENCE_MISSING_ON_DISK: {pcap_path} absent at assert_registered",
        )
    except EvidenceRegistryError as exc:
        return _fail(
            NetworkFailureReason.EVIDENCE_TAMPERED,
            f"EVIDENCE_REGISTRY_ERROR at assert_registered: {type(exc).__name__}: {exc}",
        )

    try:
        verify = evidence_registry.verify_hash(pcap_path)
    except EvidenceMissingOnDiskError:
        return _fail(
            NetworkFailureReason.EVIDENCE_TAMPERED,
            f"EVIDENCE_MISSING_ON_DISK: {pcap_path} vanished since registration",
        )
    except EvidenceRegistryError as exc:
        return _fail(
            NetworkFailureReason.EVIDENCE_TAMPERED,
            f"EVIDENCE_REGISTRY_ERROR: {type(exc).__name__}: {exc}",
        )
    if not verify.matches:
        return _fail(
            NetworkFailureReason.EVIDENCE_TAMPERED,
            f"EVIDENCE_TAMPERED: SHA256 drift on {pcap_path}"
            f" expected={verify.expected} actual={verify.actual}",
        )

    mount = check_mount()
    if not mount.ok:
        return _fail(
            NetworkFailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID,
            f"MOUNT_NOT_RO_NOEXEC_NOSUID: {'; '.join(mount.advisories) or 'no detail'}",
        )

    zeek_bin = get_zeek_bin()
    if zeek_bin is None:
        return _fail(
            NetworkFailureReason.ZEEK_NOT_INSTALLED,
            "Zeek is NOT pre-installed on SIFT 2026 — run install.sh to add it"
            " (see context/.raw-design-research/03 §'Tools our install script MUST add')",
        )

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _fail(NetworkFailureReason.TOOL_FAILED, f"OUT_DIR_FAILED: {exc}")

    cmd_argv = (str(zeek_bin), "-r", str(pcap_path), "-C")

    try:
        result: _NetworkResult = await _run_zeek(zeek_bin, pcap_path, out_dir, timeout_s=timeout_s)
    except TimeoutError:
        return _fail(
            NetworkFailureReason.TOOL_TIMEOUT,
            f"TOOL_TIMEOUT: zeek timed out after {timeout_s}s",
            argv=cmd_argv,
        )
    except OSError as exc:
        return _fail(
            NetworkFailureReason.TOOL_FAILED,
            f"TOOL_SPAWN_FAILED: {exc}",
            argv=cmd_argv,
        )

    if result.exit_code != 0:
        stderr_snippet = result.stderr[:_STDERR_CAP].decode("utf-8", errors="replace")
        return _fail(
            NetworkFailureReason.TOOL_FAILED,
            f"TOOL_FAILED: exit {result.exit_code}; stderr: {stderr_snippet}",
            argv=cmd_argv,
            extra_params={"exit_code": result.exit_code},
        )

    logs = _inventory_zeek_logs(out_dir)
    if logs is None:
        return _fail(
            NetworkFailureReason.OUTPUT_PARSE_FAILED,
            "OUTPUT_PARSE_FAILED: I/O error reading Zeek log directory",
            argv=cmd_argv,
        )
    if not logs or "conn" not in logs:
        return _fail(
            NetworkFailureReason.NO_LOGS_PRODUCED,
            "NO_LOGS_PRODUCED: conn.log absent or no *.log produced"
            " — verify the pcap is non-empty with `tcpdump -r <pcap> -c 5`",
            argv=cmd_argv,
        )

    manifest = _build_manifest(logs)
    sha = hashlib.sha256(manifest).hexdigest()

    try:
        blob_path = persist_blob(case_dir, audit_id, manifest)
    except OSError as exc:
        return _fail(
            NetworkFailureReason.TOOL_FAILED,
            f"BLOB_PERSIST_FAILED: {exc}",
            argv=cmd_argv,
        )

    output = _to_result(out_dir, logs)
    elapsed = (time.monotonic() - t0) * 1000.0

    try:
        append_jsonl_line(
            _log,
            AuditEntry(
                ts=datetime.now(UTC),
                audit_id=audit_id,
                tool="zeek_run",
                params={"pcap_path": str(pcap_path), "out_dir": str(out_dir)},
                result_summary={
                    "total_logs": output.total_logs,
                    "total_lines": output.total_lines,
                },
                result_sha256=sha,
                stdout_path=blob_path,
                elapsed_ms=elapsed,
                examiner=audit_logger.examiner,
                model_used=model_used,
                model_token_count={},
            ).model_dump_json(),
        )
    except Exception as _ae:
        _LOG.error("zeek_run: success audit write failed: %s", _ae, exc_info=True)
        delete_orphan_blob(blob_path)
        return _fail(
            NetworkFailureReason.TOOL_FAILED,
            f"AUDIT_WRITE_FAILED: result produced but audit trail could not be written; {_ae}",
            argv=cmd_argv,
        )

    return ToolResponse[ZeekRunResult](
        success=True,
        data=output,
        audit_id=audit_id,
        examiner=audit_logger.examiner,
        advisories=(),
        caveats=ZEEK_CAVEATS,
        corroboration=ZEEK_CORROBORATION,
        data_provenance=DataProvenance(
            tool="zeek_run",
            stdout_path=blob_path,
            result_sha256=sha,
            elapsed_ms=elapsed,
            cmd_argv=cmd_argv,
        ),
    )


__all__ = [
    "ZEEK_CAVEATS",
    "ZEEK_CORROBORATION",
    "ZeekLogInfo",
    "ZeekRunResult",
    "zeek_run",
]
