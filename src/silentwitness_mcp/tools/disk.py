"""EZ-Tools disk-family wrappers (architecture §4.2 row 10,
context/.raw-design-research/03 §EZ Tools, context/domain/02 §1).

This module owns the public ``parse_*`` coroutines that wrap each EZ
Tool. Subprocess orchestration + audit-row writing live in
:mod:`_disk_pipeline`; failure-enum + helpers in :mod:`_disk_common`;
typed models + caveats in :mod:`_disk_models`. Aggregate ≤400 LOC per
PRD §6."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from silentwitness_common.types import ToolResponse
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._disk_common import DEFAULT_TIMEOUT_S
from silentwitness_mcp.tools._disk_models import MFT_CAVEATS, MFTEntry, MftOutput
from silentwitness_mcp.tools._disk_pipeline import run_disk_wrapper


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


__all__ = ["parse_mft"]
