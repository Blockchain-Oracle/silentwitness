"""Suricata pcap replay wrapper — architecture §4.2, story-suricata-run.

Zeek answers "what protocols ran in this pcap"; Suricata answers "which rules
fired". Both run against the same pcap for complementary coverage (§21 domain).

Rules file IS evidence: the rules drive which alerts fire, so a SHA256 mismatch
on the rules file means the detection set is unknowable. Both pcap AND rules must
be registered + hash-verified before any subprocess is spawned.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Final

from pydantic import BaseModel, ConfigDict, Field

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
    _run_suricata,
    _tally_eve_events,
    get_suricata_bin,
)

_LOG = logging.getLogger(__name__)
_AUDIT_LOG: Final = "network.jsonl"
_STDERR_CAP: Final = 500

SURICATA_CAVEATS: Final[tuple[str, ...]] = (
    "Suricata alert event_type entries are rule matches — the rule SID + msg identifies"
    " the detection; corroborate against ET Open ruleset version"
    " (rules drift across releases)",
    "Suricata's flow event_type is similar to Zeek's conn.log but with rule-match"
    " decoration; cross-check with zeek_run for protocol parsing fidelity",
    "EVE JSON is one JSON object per line — use jq or line-by-line parse; the schema is"
    " documented at https://docs.suricata.io/en/latest/output/eve/eve-json-format.html",
    "--runmode single is forced for deterministic event ordering; multi-threaded mode"
    " would break SHA256 reproducibility across runs on the same pcap",
)

SURICATA_CORROBORATION: Final[tuple[str, ...]] = (
    "if suricata_run produced 0 alerts on a pcap, run zeek_run for protocol-aware"
    " coverage (notice.log + weird.log may surface anomalies Suricata's rules miss)",
)


class SuricataRunResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    eve_json_path: Path
    eve_json_sha256: Sha256Hex
    alert_count: Annotated[int, Field(ge=0)]
    flow_count: Annotated[int, Field(ge=0)]
    http_count: Annotated[int, Field(ge=0)]
    dns_count: Annotated[int, Field(ge=0)]
    tls_count: Annotated[int, Field(ge=0)]
    fileinfo_count: Annotated[int, Field(ge=0)]
    anomaly_count: Annotated[int, Field(ge=0)]
    stats_count: Annotated[int, Field(ge=0)]
    total_events: Annotated[int, Field(ge=0)]
    event_type_breakdown: dict[str, int] = Field(default_factory=dict)


def _build_suricata_manifest(eve_sha256: str, total_events: int, counts: dict[str, int]) -> bytes:
    lines = [f"eve.json {eve_sha256} {total_events}\n"]
    lines += [f"{et} {cnt}\n" for et, cnt in sorted(counts.items())]
    return "".join(lines).encode()


def _to_suricata_result(
    eve_json_path: Path, eve_sha: str, counts: dict[str, int]
) -> SuricataRunResult:
    total = sum(counts.values())
    return SuricataRunResult(
        eve_json_path=eve_json_path,
        eve_json_sha256=eve_sha,
        alert_count=counts.get("alert", 0),
        flow_count=counts.get("flow", 0),
        http_count=counts.get("http", 0),
        dns_count=counts.get("dns", 0),
        tls_count=counts.get("tls", 0),
        fileinfo_count=counts.get("fileinfo", 0),
        anomaly_count=counts.get("anomaly", 0),
        stats_count=counts.get("stats", 0),
        total_events=total,
        event_type_breakdown=counts,
    )


async def suricata_run(
    pcap_path: Path,
    rules_path: Path,
    out_dir: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = 900.0,
) -> ToolResponse[SuricataRunResult]:
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
    ) -> ToolResponse[SuricataRunResult]:
        _LOG.warning("suricata_run refused: %s | %s", r.value, advisory[:200])
        ms = (time.monotonic() - t0) * 1000.0
        _sha = sha or "0" * 64
        params: dict[str, Any] = {
            "pcap_path": str(pcap_path),
            "rules_path": str(rules_path),
            "out_dir": str(out_dir),
        }
        if extra_params:
            params.update(extra_params)
        try:
            append_jsonl_line(
                _log,
                AuditEntry(
                    ts=datetime.now(UTC),
                    audit_id=audit_id,
                    tool="suricata_run",
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
            _LOG.error("suricata_run: audit write failed: %s", _ae, exc_info=True)
        prov = (
            DataProvenance(
                tool="suricata_run",
                stdout_path=bp or Path("/dev/null"),
                result_sha256=_sha,
                elapsed_ms=ms,
                cmd_argv=argv,
            )
            if (bp or argv)
            else make_empty_provenance("suricata_run")
        )
        return ToolResponse[SuricataRunResult](
            success=False,
            data=None,
            audit_id=audit_id,
            examiner=audit_logger.examiner,
            advisories=(advisory, r.value),
            caveats=SURICATA_CAVEATS,
            corroboration=SURICATA_CORROBORATION,
            data_provenance=prov,
        )

    # §4.10: assert_registered first, then verify_hash, for each evidence input
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
        evidence_registry.assert_registered(rules_path)
    except EvidenceNotRegisteredError:
        return _fail(
            NetworkFailureReason.EVIDENCE_NOT_REGISTERED,
            f"EVIDENCE_NOT_REGISTERED: {rules_path}"
            " — Suricata rules files ARE evidence and must be registered before use",
        )
    except EvidenceMissingOnDiskError:
        return _fail(
            NetworkFailureReason.EVIDENCE_TAMPERED,
            f"EVIDENCE_MISSING_ON_DISK: {rules_path} absent at assert_registered",
        )
    except EvidenceRegistryError as exc:
        return _fail(
            NetworkFailureReason.EVIDENCE_TAMPERED,
            f"EVIDENCE_REGISTRY_ERROR at assert_registered: {type(exc).__name__}: {exc}",
        )

    for path in (pcap_path, rules_path):
        try:
            verify = evidence_registry.verify_hash(path)
        except EvidenceMissingOnDiskError:
            return _fail(
                NetworkFailureReason.EVIDENCE_TAMPERED,
                f"EVIDENCE_MISSING_ON_DISK: {path} vanished since registration",
            )
        except EvidenceRegistryError as exc:
            return _fail(
                NetworkFailureReason.EVIDENCE_TAMPERED,
                f"EVIDENCE_REGISTRY_ERROR: {type(exc).__name__}: {exc}",
            )
        if not verify.matches:
            return _fail(
                NetworkFailureReason.EVIDENCE_TAMPERED,
                f"EVIDENCE_TAMPERED: SHA256 drift on {path}"
                f" expected={verify.expected} actual={verify.actual}",
            )

    mount = check_mount()
    if not mount.ok:
        return _fail(
            NetworkFailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID,
            f"MOUNT_NOT_RO_NOEXEC_NOSUID: {'; '.join(mount.advisories) or 'no detail'}",
        )

    suricata_bin = get_suricata_bin()
    if suricata_bin is None:
        return _fail(
            NetworkFailureReason.SURICATA_NOT_INSTALLED,
            "Suricata is NOT pre-installed on SIFT 2026 — run install.sh to add it"
            " (see context/.raw-design-research/03 §'Tools our install script MUST add')",
        )

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _fail(NetworkFailureReason.TOOL_FAILED, f"OUT_DIR_FAILED: {exc}")

    cmd_argv = (
        str(suricata_bin),
        "-r",
        str(pcap_path),
        "-S",
        str(rules_path),
        "-l",
        str(out_dir),
        "--runmode",
        "single",
        "-k",
        "none",
    )

    try:
        result: _NetworkResult = await _run_suricata(
            suricata_bin, pcap_path, rules_path, out_dir, timeout_s=timeout_s
        )
    except TimeoutError:
        return _fail(
            NetworkFailureReason.TOOL_TIMEOUT,
            f"TOOL_TIMEOUT: suricata timed out after {timeout_s}s",
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

    eve_json_path = out_dir / "eve.json"
    if not eve_json_path.exists():
        return _fail(
            NetworkFailureReason.OUTPUT_PARSE_FAILED,
            f"OUTPUT_PARSE_FAILED: eve.json missing from {out_dir} after Suricata"
            " exit 0 — verify suricata.yaml outputs.eve-log.enabled: yes",
            argv=cmd_argv,
        )

    counts = _tally_eve_events(eve_json_path)
    if counts is None:
        return _fail(
            NetworkFailureReason.OUTPUT_PARSE_FAILED,
            f"OUTPUT_PARSE_FAILED: I/O error reading {eve_json_path}",
            argv=cmd_argv,
        )

    eve_raw = eve_json_path.read_bytes()
    eve_sha = hashlib.sha256(eve_raw).hexdigest()
    manifest = _build_suricata_manifest(eve_sha, sum(counts.values()), counts)
    sha = hashlib.sha256(manifest).hexdigest()

    try:
        blob_path = persist_blob(case_dir, audit_id, manifest)
    except OSError as exc:
        return _fail(NetworkFailureReason.TOOL_FAILED, f"BLOB_PERSIST_FAILED: {exc}", argv=cmd_argv)

    output = _to_suricata_result(eve_json_path, eve_sha, counts)
    elapsed = (time.monotonic() - t0) * 1000.0

    try:
        append_jsonl_line(
            _log,
            AuditEntry(
                ts=datetime.now(UTC),
                audit_id=audit_id,
                tool="suricata_run",
                params={
                    "pcap_path": str(pcap_path),
                    "rules_path": str(rules_path),
                    "out_dir": str(out_dir),
                },
                result_summary={
                    "total_events": output.total_events,
                    "alert_count": output.alert_count,
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
        _LOG.error("suricata_run: success audit write failed: %s", _ae, exc_info=True)
        delete_orphan_blob(blob_path)
        return _fail(
            NetworkFailureReason.TOOL_FAILED,
            f"AUDIT_WRITE_FAILED: result produced but audit trail could not be written; {_ae}",
            argv=cmd_argv,
        )

    return ToolResponse[SuricataRunResult](
        success=True,
        data=output,
        audit_id=audit_id,
        examiner=audit_logger.examiner,
        advisories=(),
        caveats=SURICATA_CAVEATS,
        corroboration=SURICATA_CORROBORATION,
        data_provenance=DataProvenance(
            tool="suricata_run",
            stdout_path=blob_path,
            result_sha256=sha,
            elapsed_ms=elapsed,
            cmd_argv=cmd_argv,
        ),
    )


__all__ = [
    "SURICATA_CAVEATS",
    "SURICATA_CORROBORATION",
    "SuricataRunResult",
    "suricata_run",
]
