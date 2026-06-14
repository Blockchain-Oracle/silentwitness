"""Targeted-parser ingest — the reliable, parallel evidence-index spine.

The agent queries ``index.db``; this module fills it from the **extracted prepared
artifacts** (regular files), using purpose-built parsers per artifact type. This is
the spine, not plaso: plaso's libevtx-backed ``winevtx`` parser extracts 0 events from
the ROCBA EVTX (libevtx crashes on them), whereas the EVTX feeder reads them cleanly.

Performance (the build is offline but must not waste the box): artifacts are parsed
**in parallel across the cores** — registry hives are CPU-bound in regipy (~minutes
each) and would otherwise pin a single core while the rest idle. Each worker parses one
artifact and returns its rows; the main process ``bulk_ingest``s them (single SQLite
writer) as each future completes, so peak memory is bounded by the few in-flight
artifacts, not the whole ~1M-row corpus. Correctness is never traded for speed: every
record is kept; only the *order* of work changes.

A parser failure on one artifact is logged and skipped so one bad file can't abort the
whole ingest. Returns per-type row counts. Callers wrap this in
``begin_bulk()`` / ``rebuild_fts()`` (see ``cli_commands/index_case``).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Iterator
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.index.feeders_evtx import evtx_file_records
from silentwitness_mcp.index.feeders_registry import registry_hive_records
from silentwitness_mcp.index.store import EvidenceIndex, IndexRecord

_LOG = logging.getLogger(__name__)

# Marker dir written by `prepare`; citations are stored relative to it so they're
# stable regardless of where the case tree lives (dev box vs VPS vs OVA).
_PREPARED = "prepared"

# A feeder streams index rows from one artifact; all share this keyword signature.
_Feeder = Callable[..., Iterator[IndexRecord]]

# Artifact type -> (label, feeder). Resolved via module globals so the in-process
# (max_workers=1) path stays monkeypatchable in tests.
_KINDS: dict[EvidenceType, str] = {
    EvidenceType.EVTX: "evtx",
    EvidenceType.HIVE: "registry",
}


def _citation_path(path: Path) -> str:
    """Path relative to the ``prepared/`` root, for a stable, portable citation."""
    parts = path.parts
    if _PREPARED in parts:
        return str(Path(*parts[parts.index(_PREPARED) + 1 :]))
    return path.name


def _feeder_for(kind: str) -> _Feeder:
    """Resolve the feeder for an artifact ``kind`` from the (monkeypatchable) globals."""
    return registry_hive_records if kind == "registry" else evtx_file_records


def _parse_artifact(
    kind: str, path_str: str, cite: str, audit_id: str, host: str
) -> list[IndexRecord]:
    """Worker entry point: parse one artifact into a list of rows (runs in a subprocess)."""
    feeder = _feeder_for(kind)
    return list(feeder(Path(path_str), audit_id=audit_id, host=host, source_path=cite))


def ingest_prepared_artifacts(
    registry: EvidenceRegistry,
    index: EvidenceIndex,
    *,
    audit_id: str,
    host: str = "",
    max_workers: int | None = None,
) -> dict[str, int]:
    """Parse every registered prepared artifact into ``index``; return per-type counts.

    Parses artifacts in parallel (default: cores-1) and bulk-inserts each artifact's
    rows as it completes. ``max_workers=1`` runs in-process (used by tests). The caller
    must wrap this in ``index.begin_bulk()`` / ``index.rebuild_fts()`` for the deferred
    FTS build. A feeder that raises on one artifact is logged and skipped."""
    tasks: list[tuple[str, Path, str]] = []
    for rec in registry.list_all():
        kind = _KINDS.get(rec.type)
        if kind is not None:
            tasks.append((kind, rec.path, _citation_path(rec.path)))
    if not tasks:
        return {}
    workers = max_workers if max_workers is not None else max(1, (os.cpu_count() or 2) - 1)
    counts: dict[str, int] = {}
    if workers == 1:
        for kind, path, cite in tasks:
            counts[kind] = counts.get(kind, 0) + _ingest_one(
                index, kind, path, cite, audit_id, host
            )
        return counts

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_parse_artifact, kind, str(path), cite, audit_id, host): (kind, path)
            for kind, path, cite in tasks
        }
        for future in as_completed(futures):
            kind, path = futures[future]
            try:
                records = future.result()
            except Exception as exc:  # any worker parse failure -> skip that artifact
                _LOG.warning("%s feeder failed on %s: %s", kind, path.name, exc)
                continue
            counts[kind] = counts.get(kind, 0) + index.bulk_ingest(records)
    return counts


def _ingest_one(
    index: EvidenceIndex, kind: str, path: Path, cite: str, audit_id: str, host: str
) -> int:
    """In-process parse + bulk-ingest of one artifact (the ``max_workers=1`` path)."""
    feeder = _feeder_for(kind)
    try:
        return index.bulk_ingest(feeder(path, audit_id=audit_id, host=host, source_path=cite))
    except (OSError, ValueError) as exc:
        _LOG.warning("%s feeder failed on %s: %s", kind, path.name, exc)
        return 0


__all__ = ["ingest_prepared_artifacts"]
