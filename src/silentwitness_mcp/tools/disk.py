"""EZ-Tools disk-family wrappers (architecture §4.2 row 10,
context/.raw-design-research/03 §EZ Tools, context/domain/02 §1).

This module owns the public ``parse_*`` coroutines that wrap each EZ
Tool. Subprocess orchestration + audit-row writing live in
:mod:`_disk_pipeline`; failure-enum + helpers in :mod:`_disk_common`;
typed models + caveats in :mod:`_disk_models`. Aggregate ≤400 LOC per
PRD §6."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from pydantic import ValidationError

from silentwitness_common.types import ToolResponse
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._disk_common import DEFAULT_TIMEOUT_S, dll_path_for
from silentwitness_mcp.tools._disk_models import MFT_CAVEATS, MFTEntry, MftOutput
from silentwitness_mcp.tools._disk_models_amcache import (
    AMCACHE_CAVEATS,
    AMCACHE_CORROBORATION,
    SHIMCACHE_CAVEATS,
    SHIMCACHE_CORROBORATION,
    AmcacheEntry,
    AmcacheOutput,
    ShimcacheEntry,
    ShimcacheOutput,
)
from silentwitness_mcp.tools._disk_models_prefetch import (
    PREFETCH_CAVEATS,
    PREFETCH_CORROBORATION,
    PrefetchEntry,
    PrefetchOutput,
)
from silentwitness_mcp.tools._disk_pipeline import run_disk_wrapper

# PECmd is NOT pre-installed on stock SIFT 2026 — absence produces
# PECMD_NOT_INSTALLED advisory. Testable via monkeypatch on this constant.
_PECMD_DLL: Final[Path] = dll_path_for("PECmd")


def _parse_mft_rows(rows: list[dict[str, str | None]], truncated: bool) -> MftOutput:
    """Map MFTECmd CSV ``DictReader`` rows to typed :class:`MFTEntry`.

    Row-by-row try/except so a single malformed row (e.g. a deleted
    record with a ``DateTime.MinValue`` sentinel that .NET emits
    verbatim, or a recovered entry with corrupt FN timestamps) does
    NOT abort the entire 1M-row parse — partial recovery is
    forensically preferable. Per-row failures push ``truncated=True``
    so the caller surfaces the partial-parse advisory."""
    entries: list[MFTEntry] = []
    skipped = 0
    for row in rows:
        try:
            entries.append(MFTEntry.model_validate(row))
        except ValidationError:
            skipped += 1
    return MftOutput(
        entries=tuple(entries),
        truncated=truncated or skipped > 0,
    )


async def parse_mft(
    evidence_path: Path,
    csv_out: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ToolResponse[MftOutput]:
    """Parse an NTFS ``$MFT`` via MFTECmd → typed :class:`MftOutput`.

    Pre-spawn gates (mount + evidence-registered + SHA256-stable +
    dotnet on disk + ``csv_out`` under ``case_dir``) fail-closed
    before MFTECmd is invoked. MFTECmd is the only EZ Tool with a
    reliable exit code (per CLAUDE.md), so the pipeline can trust
    ``exit_code != 0`` for fatal-error detection without parsing
    Serilog stderr markers.

    MFTECmd writes the CSV to ``--csv <csv_out>``; the wrapper globs
    ``*_MFTECmd_*Output.csv`` and reads the most recent match. A
    truncated CSV (MFTECmd killed mid-write) or per-row validation
    failures surface as ``MftOutput.truncated=True`` plus a
    ``partial parse`` advisory."""
    return await run_disk_wrapper(
        tool_name="parse_mft",
        ez_tool="MFTECmd",
        ez_argv=["--csv", str(csv_out), "-f", str(evidence_path)],
        csv_glob_pattern="*_MFTECmd_*Output.csv",
        csv_out_dir=csv_out,
        output_cls=MftOutput,
        parse_csv=_parse_mft_rows,
        caveats=MFT_CAVEATS,
        evidence_path=evidence_path,
        case_dir=case_dir,
        evidence_registry=evidence_registry,
        audit_logger=audit_logger,
        model_used=model_used,
        timeout_s=timeout_s,
    )


def _parse_amcache_rows(rows: list[dict[str, str | None]], truncated: bool) -> AmcacheOutput:
    """Row-by-row parse of AmcacheParser UnassociatedFileEntries CSV.
    Per-row ValidationErrors are skipped (partial-success preferred
    over hard reject — same rationale as _parse_mft_rows)."""
    entries: list[AmcacheEntry] = []
    skipped = 0
    for row in rows:
        try:
            entries.append(AmcacheEntry.model_validate(row))
        except ValidationError:
            skipped += 1
    return AmcacheOutput(entries=tuple(entries), truncated=truncated or skipped > 0)


async def parse_amcache(
    evidence_path: Path,
    csv_out: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ToolResponse[AmcacheOutput]:
    """Parse an Amcache.hve via AmcacheParser → typed :class:`AmcacheOutput`.

    Consumes the ``UnassociatedFileEntries`` table (glob
    ``**/*_UnassociatedFileEntries.csv`` — AmcacheParser may nest output
    by hostname). AmcacheParser exit code is unreliable; Serilog stderr
    scanning is mandatory (``check_serilog_stderr=True``).

    An empty entries list (fresh install / Appraiser never ran) is a
    valid success — the caller surfaces the advisory from caveats."""
    envelope = await run_disk_wrapper(
        tool_name="parse_amcache",
        ez_tool="AmcacheParser",
        ez_argv=["--csv", str(csv_out), "-f", str(evidence_path)],
        csv_glob_pattern="**/*_UnassociatedFileEntries.csv",
        csv_out_dir=csv_out,
        output_cls=AmcacheOutput,
        parse_csv=_parse_amcache_rows,
        caveats=AMCACHE_CAVEATS,
        corroboration=AMCACHE_CORROBORATION,
        check_serilog_stderr=True,
        evidence_path=evidence_path,
        case_dir=case_dir,
        evidence_registry=evidence_registry,
        audit_logger=audit_logger,
        model_used=model_used,
        timeout_s=timeout_s,
    )
    if envelope.success and envelope.data is not None and len(envelope.data.entries) == 0:
        return envelope.model_copy(
            update={
                "advisories": (
                    *envelope.advisories,
                    "no InventoryApplicationFile entries — confirm Appraiser "
                    "scheduled task has run on this host",
                )
            }
        )
    return envelope


def _parse_shimcache_rows(rows: list[dict[str, str | None]], truncated: bool) -> ShimcacheOutput:
    """Row-by-row parse of AppCompatCacheParser CSV."""
    entries: list[ShimcacheEntry] = []
    skipped = 0
    for row in rows:
        try:
            entries.append(ShimcacheEntry.model_validate(row))
        except ValidationError:
            skipped += 1
    return ShimcacheOutput(entries=tuple(entries), truncated=truncated or skipped > 0)


async def parse_shimcache(
    evidence_path: Path,
    csv_out: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ToolResponse[ShimcacheOutput]:
    """Parse a SYSTEM hive via AppCompatCacheParser → typed
    :class:`ShimcacheOutput`. Entries are sorted by
    ``(cache_entry_position, control_set)`` ascending.

    AppCompatCacheParser exit code is unreliable; Serilog stderr
    scanning is mandatory (``check_serilog_stderr=True``)."""
    return await run_disk_wrapper(
        tool_name="parse_shimcache",
        ez_tool="AppCompatCacheParser",
        ez_argv=["--csv", str(csv_out), "-f", str(evidence_path)],
        csv_glob_pattern="**/*_AppCompatCache_*.csv",
        csv_out_dir=csv_out,
        output_cls=ShimcacheOutput,
        parse_csv=_parse_shimcache_rows,
        caveats=SHIMCACHE_CAVEATS,
        corroboration=SHIMCACHE_CORROBORATION,
        check_serilog_stderr=True,
        evidence_path=evidence_path,
        case_dir=case_dir,
        evidence_registry=evidence_registry,
        audit_logger=audit_logger,
        model_used=model_used,
        timeout_s=timeout_s,
    )


def _parse_prefetch_rows(rows: list[dict[str, str | None]], truncated: bool) -> PrefetchOutput:
    """Row-by-row parse of PECmd CSV. Per-row ValidationErrors are skipped
    (partial-success preferred over hard reject)."""
    entries: list[PrefetchEntry] = []
    skipped = 0
    for row in rows:
        try:
            entries.append(PrefetchEntry.model_validate(row))
        except ValidationError:
            skipped += 1
    return PrefetchOutput(entries=tuple(entries), truncated=truncated or skipped > 0)


async def parse_prefetch(
    evidence_path: Path,
    csv_out: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ToolResponse[PrefetchOutput]:
    """Parse a Prefetch directory or .pf file via PECmd → typed
    :class:`PrefetchOutput`.

    ``evidence_path`` may be a directory (batch ``-d``) or a single .pf
    file (``-f``). PECmd is NOT pre-installed on stock SIFT 2026;
    ``EZ_TOOL_NOT_FOUND`` fires if the DLL is absent. PECmd exit code is
    unreliable; Serilog stderr scanning is mandatory
    (``check_serilog_stderr=True``).

    Post-success advisories are added for: entries exceeding the 1024
    historical cap, and entries with ``ParsingError=True``."""
    ez_argv = [
        "--csv",
        str(csv_out),
        "-d" if evidence_path.is_dir() else "-f",
        str(evidence_path),
    ]
    envelope = await run_disk_wrapper(
        tool_name="parse_prefetch",
        ez_tool="PECmd",
        ez_argv=ez_argv,
        csv_glob_pattern="*_PECmd_Output.csv",
        csv_out_dir=csv_out,
        output_cls=PrefetchOutput,
        parse_csv=_parse_prefetch_rows,
        caveats=PREFETCH_CAVEATS,
        corroboration=PREFETCH_CORROBORATION,
        check_serilog_stderr=True,
        dll_check_override=_PECMD_DLL,
        evidence_path=evidence_path,
        case_dir=case_dir,
        evidence_registry=evidence_registry,
        audit_logger=audit_logger,
        model_used=model_used,
        timeout_s=timeout_s,
    )
    if not envelope.success or envelope.data is None:
        return envelope
    extra: list[str] = []
    if envelope.data.row_count > 1024:
        extra.append(
            f"Prefetch directory contains {envelope.data.row_count} entries; "
            "historical cap is 1024 — older entries may have been LRU-evicted"
        )
    if envelope.data.parsing_error_count > 0:
        bad = [e.executable_name for e in envelope.data.entries if e.parsing_error]
        extra.append(
            f"{envelope.data.parsing_error_count} entr"
            f"{'y' if envelope.data.parsing_error_count == 1 else 'ies'} "
            f"had PECmd parsing errors: {', '.join(bad[:5])}"
        )
    if extra:
        return envelope.model_copy(update={"advisories": (*envelope.advisories, *extra)})
    return envelope


__all__ = ["parse_amcache", "parse_mft", "parse_prefetch", "parse_shimcache"]
