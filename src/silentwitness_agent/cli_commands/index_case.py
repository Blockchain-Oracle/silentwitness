"""``silentwitness index`` — parse the prepared artifacts into the per-case
evidence index (Phase 1).

Runs plaso over ``cases/<id>/prepared`` (produced by ``prepare``) and ingests the
normalised super-timeline into ``cases/<id>/index.db``, which the agent then
queries via ``search_evidence`` / ``timeline`` instead of raw-reading artifacts.

The plaso ingest is imported lazily (the ``forensics`` extra), so this module
loads on a machine without it; the no-op path (nothing prepared) needs no plaso.
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
    """Mount each registered disk image, run plaso over it, index its timeline.

    Returns 0 on success, 1 if there's nothing to index or a parse fails."""
    out = Console(no_color=no_color)
    err = Console(stderr=True, no_color=no_color)
    images = [r for r in EvidenceRegistry(case_dir).list_all() if r.type == EvidenceType.DISK_IMAGE]
    if not images:
        err.print(
            "[yellow]⚠[/yellow] nothing to index — register a disk image first "
            f"(`silentwitness register-evidence {case_id} <image.E01>`)",
            highlight=False,
        )
        return 1

    # Lazy: plaso + mount tools live in the forensics extra / install.sh.
    from silentwitness_mcp.index.ingest import IngestError, ingest_image_timeline

    audit = AuditLogger(case_dir, examiner)
    t0 = time.monotonic()
    total = 0
    try:
        audit_id = audit.next_audit_id()
        out.print(
            "[cyan]…[/cyan] mounting image + running plaso over the filesystem "
            "(this can take several minutes)",
            highlight=False,
        )
        for rec in images:
            try:
                with EvidenceIndex(case_dir / _INDEX_DB) as idx:
                    total += ingest_image_timeline(rec.path, idx, audit_id=audit_id, host=host)
            except IngestError as exc:
                err.print(f"[red]✗[/red] {rec.path.name}: {exc}", highlight=False)
                return 1
        summary: dict[str, object] = {"rows": total, "host": host, "images": len(images)}
        audit.emit(
            backend="index",
            tool="index.ingest_image_timeline",
            params={"images": [str(r.path) for r in images], "host": host},
            result_summary=summary,
            result_sha256=hashlib.sha256(json.dumps(summary, sort_keys=True).encode()).hexdigest(),
            stdout_path=case_dir / _INDEX_DB,
            elapsed_ms=(time.monotonic() - t0) * 1000.0,
            model_used="cli",
        )
    finally:
        audit.close()

    out.print(
        f"[green]✓[/green] indexed {total} records into {case_dir / _INDEX_DB}", highlight=False
    )
    return 0
