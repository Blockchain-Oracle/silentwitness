"""``silentwitness index`` — parse the prepared artifacts into the per-case
evidence index (Phase 1).

Two spines feed ``cases/<id>/index.db`` (which the agent then queries via
``search_evidence`` / ``timeline`` instead of raw-reading artifacts):

1. **Targeted parsers (the reliable spine)** over the extracted ``prepared/``
   artifacts — a hybrid Rust-``evtx`` / ``python-evtx`` reader for EVTX, ``regipy`` for
   hives (see ``index.feeders_*``). This is load-bearing: plaso's libevtx-backed
   ``winevtx`` parser extracts 0 events from the ROCBA EVTX (libevtx crashes on them),
   so the targeted feeders are what actually populate the index. Any artifact that fails
   to parse is reported (operator summary + audit advisories), never silently dropped.
2. **plaso super-timeline (best-effort breadth)** by mounting each registered E01.
   This adds timeline breadth where it works but is treated as non-fatal — a plaso
   failure must not zero out the index the targeted spine already filled.

Both ingests are imported lazily (the ``forensics`` extra), so this module loads on
a machine without them.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from rich.console import Console

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.index.store import EvidenceIndex

_INDEX_DB = "index.db"
_SUMMARY_SAMPLE_LIMIT = 5


def _counts_by_kind(items: Sequence[tuple[str, object, object]]) -> str:
    counts: dict[str, int] = {}
    for kind, _, _ in items:
        counts[kind] = counts.get(kind, 0) + 1
    return ", ".join(f"{kind}={count}" for kind, count in sorted(counts.items()))


def _print_artifact_failure_summary(
    err: Console,
    failures: list[tuple[str, str, str]],
) -> None:
    if not failures:
        return
    samples = ", ".join(f"{kind}:{name}" for kind, name, _ in failures[:_SUMMARY_SAMPLE_LIMIT])
    more = len(failures) - _SUMMARY_SAMPLE_LIMIT
    more_note = f"; +{more} more" if more > 0 else ""
    err.print(
        f"[yellow]⚠[/yellow] {len(failures)} artifact parser failure(s) recorded "
        f"({_counts_by_kind(failures)}; samples: {samples}{more_note}; full details in audit)",
        highlight=False,
    )


def _print_skip_summary(
    err: Console,
    diagnostics: list[tuple[str, str, dict[str, int]]],
) -> None:
    if not diagnostics:
        return
    skipped_total = sum(sum(skipped.values()) for _, _, skipped in diagnostics)
    samples = ", ".join(f"{kind}:{name}" for kind, name, _ in diagnostics[:_SUMMARY_SAMPLE_LIMIT])
    more = len(diagnostics) - _SUMMARY_SAMPLE_LIMIT
    more_note = f"; +{more} more" if more > 0 else ""
    err.print(
        f"[yellow]⚠[/yellow] {skipped_total} parser record skip(s) recorded "
        f"({_counts_by_kind(diagnostics)}; samples: {samples}{more_note}; full details in audit)",
        highlight=False,
    )


def _brief(message: str, *, limit: int = 220) -> str:
    compact = " ".join(message.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def run(
    case_dir: Path,
    case_id: str,
    *,
    examiner: str,
    host: str = "",
    no_color: bool,
    memory_profile: Literal["standard", "targeted", "deep"] = "standard",
) -> int:
    """Run the targeted parsers (+ best-effort plaso) over prepared artifacts.

    Returns 0 once the index is populated, 1 if there is nothing registered to index.
    A plaso failure is reported as an advisory, not a hard error: the targeted spine
    is the source of truth."""
    out = Console(no_color=no_color)
    err = Console(stderr=True, no_color=no_color)
    registry = EvidenceRegistry(case_dir)
    artifacts = registry.list_all()
    if not artifacts:
        err.print(
            "[yellow]⚠[/yellow] nothing to index — register + prepare evidence first "
            f"(`silentwitness register-evidence {case_id} <image.E01>` then `prepare {case_id}`)",
            highlight=False,
        )
        return 1

    # Lazy: parsers + mount tools live in the forensics extra / install.sh.
    from silentwitness_mcp.index.feeders_memory import (
        DEEP_PLUGINS,
        STANDARD_PLUGINS,
        TARGETED_PLUGINS,
    )
    from silentwitness_mcp.index.ingest import IngestError, ingest_image_timeline
    from silentwitness_mcp.index.ingest_artifacts import IngestResult, ingest_prepared_artifacts
    from silentwitness_mcp.index.ingest_memory import MemoryPluginEvent, ingest_memory_image

    audit = AuditLogger(case_dir, examiner)
    t0 = time.monotonic()
    counts: dict[str, int] = {}
    plaso_rows = 0
    memory_counts: dict[str, int] = {}
    memory_total = 0
    advisories: list[str] = []
    if memory_profile == "deep":
        memory_plugins = DEEP_PLUGINS
    elif memory_profile == "targeted":
        memory_plugins = TARGETED_PLUGINS
    else:
        memory_plugins = STANDARD_PLUGINS
    # Sentinel so the post-finally summary doesn't UnboundLocalError if the try block
    # raised before `ingested` was assigned (e.g. EvidenceIndex open fails).
    ingested = IngestResult()
    try:
        audit_id = audit.next_audit_id()
        out.print(
            "[cyan]…[/cyan] parsing prepared artifacts in parallel (targeted parsers)",
            highlight=False,
        )
        with EvidenceIndex(case_dir / _INDEX_DB) as idx:
            idx.begin_bulk()  # bulk-load PRAGMAs; FTS is built once at the end
            ingested = ingest_prepared_artifacts(registry, idx, audit_id=audit_id, host=host)
            counts = ingested.counts
            for kind, name, message in ingested.failures:
                advisories.append(f"{kind} parse FAILED on {name}: {message}")
            _print_artifact_failure_summary(err, ingested.failures)
            for kind, name, skipped in ingested.diagnostics:
                detail = ", ".join(f"{r}={c}" for r, c in sorted(skipped.items()))
                advisories.append(f"{kind} {name}: skipped records ({detail})")
            _print_skip_summary(err, ingested.diagnostics)

            images = [r for r in artifacts if r.type == EvidenceType.DISK_IMAGE]
            for rec in images:
                out.print(
                    f"[cyan]…[/cyan] plaso super-timeline over {rec.path.name} "
                    "(mount + parse; best-effort, can take minutes)",
                    highlight=False,
                )
                try:
                    plaso_rows += ingest_image_timeline(rec.path, idx, audit_id=audit_id, host=host)
                except IngestError as exc:
                    advisories.append(f"plaso skipped {rec.path.name}: {exc}")
                    err.print(
                        f"[yellow]⚠[/yellow] plaso breadth unavailable for {rec.path.name} "
                        "— targeted spine still indexed (see advisory)",
                        highlight=False,
                    )
            memory_images = [r for r in artifacts if r.type == EvidenceType.MEMORY_DUMP]
            for rec in memory_images:
                out.print(
                    f"[cyan]…[/cyan] vol3 memory pass over {rec.path.name}",
                    highlight=False,
                )

                def _memory_progress(event: MemoryPluginEvent) -> None:
                    if event.status == "start":
                        timeout = (
                            "timeout disabled"
                            if event.timeout_seconds is None
                            else f"timeout {event.timeout_seconds:g}s"
                        )
                        out.print(
                            f"[cyan]…[/cyan] vol3 {event.short_name} "
                            f"({timeout}{'; ' + event.message if event.message else ''})",
                            highlight=False,
                        )
                    elif event.status == "ok":
                        rows = event.rows if event.rows is not None else 0
                        out.print(
                            f"[green]✓[/green] vol3 {event.short_name}: {rows} row(s) "
                            f"in {event.elapsed_seconds:.1f}s",
                            highlight=False,
                        )
                    elif event.status == "skipped":
                        out.print(
                            f"[yellow]↷[/yellow] vol3 {event.short_name}: {_brief(event.message)}",
                            highlight=False,
                        )
                    else:
                        err.print(
                            f"[yellow]⚠[/yellow] vol3 {event.short_name}: {_brief(event.message)}",
                            highlight=False,
                        )

                mem = ingest_memory_image(
                    rec.path,
                    idx,
                    audit_id=audit_id,
                    artifact_path=str(rec.path.name),
                    host=host,
                    plugins=memory_plugins,
                    progress=_memory_progress,
                    targeted_malfind=memory_profile == "targeted",
                )
                for plugin, written in mem.counts.items():
                    memory_counts[plugin] = memory_counts.get(plugin, 0) + written
                for plugin, message in mem.failures:
                    advisories.append(f"vol3 {plugin} failed on {rec.path.name}: {message}")
            out.print("[cyan]…[/cyan] building the full-text search index", highlight=False)
            idx.rebuild_fts()
        memory_total = sum(memory_counts.values())
        total = sum(counts.values()) + plaso_rows + memory_total
        summary: dict[str, object] = {
            "rows": total,
            "targeted_counts": counts,
            "plaso_rows": plaso_rows,
            "memory_counts": memory_counts,
            "failed_artifacts": len(ingested.failures),
            "skipped_records": sum(sum(s.values()) for _, _, s in ingested.diagnostics),
            "host": host,
            "advisories": advisories,
        }
        audit.emit(
            backend="index",
            tool="index.ingest",
            params={"case": case_id, "host": host},
            result_summary=summary,
            result_sha256=hashlib.sha256(json.dumps(summary, sort_keys=True).encode()).hexdigest(),
            stdout_path=case_dir / _INDEX_DB,
            elapsed_ms=(time.monotonic() - t0) * 1000.0,
            model_used="cli",
        )
    finally:
        audit.close()

    total = sum(counts.values()) + plaso_rows + memory_total
    if total == 0:
        err.print(
            "[red]✗[/red] indexed 0 records — check that `prepare` extracted artifacts "
            "and the forensics extra is installed",
            highlight=False,
        )
        return 1
    detail = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "none"
    mem_detail = ", ".join(f"{k}={v}" for k, v in sorted(memory_counts.items())) or "none"
    failed = len(ingested.failures)
    mark = "[yellow]✓[/yellow]" if failed else "[green]✓[/green]"
    suffix = f" — [yellow]{failed} artifact(s) FAILED (see advisories)[/yellow]" if failed else ""
    out.print(
        f"{mark} indexed {total} records "
        f"(targeted: {detail}; plaso: {plaso_rows}; memory: {mem_detail}) "
        f"into {case_dir / _INDEX_DB}{suffix}",
        highlight=False,
    )
    return 0
