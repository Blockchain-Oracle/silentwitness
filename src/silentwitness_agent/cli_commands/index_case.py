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

from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.index.store import EvidenceIndex

_PREPARED_SUBDIR = "prepared"
_INDEX_DB = "index.db"


def run(case_dir: Path, case_id: str, *, examiner: str, host: str = "", no_color: bool) -> int:
    """Index the case's prepared artifacts. Returns 0 on success, 1 otherwise."""
    out = Console(no_color=no_color)
    err = Console(stderr=True, no_color=no_color)
    prepared = case_dir / _PREPARED_SUBDIR
    if not prepared.is_dir() or not any(prepared.iterdir()):
        err.print(
            "[yellow]⚠[/yellow] nothing to index — run `silentwitness prepare "
            f"{case_id}` first to extract artifacts",
            highlight=False,
        )
        return 1

    # Lazy: plaso lives in the forensics extra and is only needed for real work.
    from silentwitness_mcp.index.ingest import IngestError, ingest_plaso_timeline

    audit = AuditLogger(case_dir, examiner)
    t0 = time.monotonic()
    try:
        audit_id = audit.next_audit_id()
        out.print(
            "[cyan]…[/cyan] running plaso over prepared artifacts (this can take several minutes)",
            highlight=False,
        )
        try:
            with EvidenceIndex(case_dir / _INDEX_DB) as idx:
                count = ingest_plaso_timeline(prepared, idx, audit_id=audit_id, host=host)
        except IngestError as exc:
            err.print(f"[red]✗[/red] index ingest failed: {exc}", highlight=False)
            return 1
        summary: dict[str, object] = {"rows": count, "host": host}
        audit.emit(
            backend="index",
            tool="index.ingest_plaso_timeline",
            params={"source": str(prepared), "host": host},
            result_summary=summary,
            result_sha256=hashlib.sha256(json.dumps(summary, sort_keys=True).encode()).hexdigest(),
            stdout_path=case_dir / _INDEX_DB,
            elapsed_ms=(time.monotonic() - t0) * 1000.0,
            model_used="cli",
        )
    finally:
        audit.close()

    out.print(
        f"[green]✓[/green] indexed {count} records into {case_dir / _INDEX_DB}", highlight=False
    )
    return 0
