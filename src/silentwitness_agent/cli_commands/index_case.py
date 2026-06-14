"""``silentwitness index`` — parse the prepared artifacts into the per-case
evidence index (Phase 1).

Two spines feed ``cases/<id>/index.db`` (which the agent then queries via
``search_evidence`` / ``timeline`` instead of raw-reading artifacts):

1. **Targeted parsers (the reliable spine)** over the extracted ``prepared/``
   artifacts — ``python-evtx`` for EVTX, etc. This is load-bearing: plaso's
   libevtx-backed ``winevtx`` parser extracts 0 events from the ROCBA EVTX (libevtx
   crashes on them), so the targeted feeders are what actually populate the index.
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
from pathlib import Path

from rich.console import Console

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.index.store import EvidenceIndex

_INDEX_DB = "index.db"


def run(case_dir: Path, case_id: str, *, examiner: str, host: str = "", no_color: bool) -> int:
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
    from silentwitness_mcp.index.ingest import IngestError, ingest_image_timeline
    from silentwitness_mcp.index.ingest_artifacts import ingest_prepared_artifacts

    audit = AuditLogger(case_dir, examiner)
    t0 = time.monotonic()
    counts: dict[str, int] = {}
    plaso_rows = 0
    advisories: list[str] = []
    try:
        audit_id = audit.next_audit_id()
        out.print(
            "[cyan]…[/cyan] parsing prepared artifacts in parallel (targeted parsers)",
            highlight=False,
        )
        with EvidenceIndex(case_dir / _INDEX_DB) as idx:
            idx.begin_bulk()  # bulk-load PRAGMAs; FTS is built once at the end
            counts = ingest_prepared_artifacts(registry, idx, audit_id=audit_id, host=host)

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
            out.print("[cyan]…[/cyan] building the full-text search index", highlight=False)
            idx.rebuild_fts()
        total = sum(counts.values()) + plaso_rows
        summary: dict[str, object] = {
            "rows": total,
            "targeted_counts": counts,
            "plaso_rows": plaso_rows,
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

    total = sum(counts.values()) + plaso_rows
    if total == 0:
        err.print(
            "[red]✗[/red] indexed 0 records — check that `prepare` extracted artifacts "
            "and the forensics extra is installed",
            highlight=False,
        )
        return 1
    detail = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "none"
    out.print(
        f"[green]✓[/green] indexed {total} records "
        f"(targeted: {detail}; plaso: {plaso_rows}) into {case_dir / _INDEX_DB}",
        highlight=False,
    )
    return 0
