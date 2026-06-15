"""Targeted-parser ingest — the reliable, parallel evidence-index spine.

The agent queries ``index.db``; this module fills it from the **extracted prepared
artifacts** (regular files), using purpose-built parsers per artifact type. This is
the spine, not plaso: plaso's libevtx-backed ``winevtx`` parser extracts 0 events from
the ROCBA EVTX (libevtx crashes on them), whereas the EVTX feeder reads them cleanly.

Performance: artifacts are parsed **in parallel across the cores** — registry hives are
CPU-bound in regipy and would otherwise pin a single core while the rest idle. Each
worker parses one artifact and returns its rows; the main process ``bulk_ingest``s them
(single SQLite writer, atomic per artifact) as each future completes.

Evidence integrity (CLAUDE.md: silently dropping evidence is the worst-case bug): a
feeder that raises on one artifact does NOT abort the run, but the failure is **counted
and returned** (:class:`IngestResult.failures`) so the caller can surface it in the
operator summary and the audit trail. A green result with hidden skips is exactly what
this guards against. Both the parallel and in-process (``max_workers=1``) paths use the
same broad ``except Exception`` so the tested path matches the shipped path.

Observability note: the authoritative failure signal is this **returned, structured**
:class:`IngestResult.failures` (not log scraping) — it survives the subprocess boundary,
where a worker's ``logging`` output may not reach the operator. Finer-grained
per-record / per-plugin diagnostics inside a worker are best-effort.
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.index._feeder_util import Feeder, FeederStats
from silentwitness_mcp.index.feeders_evtx import evtx_file_records
from silentwitness_mcp.index.feeders_jumplist import jumplist_records
from silentwitness_mcp.index.feeders_lnk import lnk_records
from silentwitness_mcp.index.feeders_mft import mft_entry_records
from silentwitness_mcp.index.feeders_prefetch import prefetch_records
from silentwitness_mcp.index.feeders_pstranscript import pstranscript_records
from silentwitness_mcp.index.feeders_registry import registry_hive_records
from silentwitness_mcp.index.feeders_srum import srum_records
from silentwitness_mcp.index.feeders_usnjrnl import usnjrnl_records
from silentwitness_mcp.index.store import EvidenceIndex, IndexRecord

_LOG = logging.getLogger(__name__)

# Marker dir written by `prepare`; citations are stored relative to it so they're
# stable regardless of where the case tree lives (dev box vs VPS vs OVA).
_PREPARED = "prepared"

# Closed set of artifact kinds; a Literal so a typo'd label is a type error, not a
# silent misroute.
Kind = Literal[
    "evtx", "registry", "srum", "mft", "usnjrnl", "prefetch", "lnk", "jumplist", "pstranscript"
]
# Direct artifact-type -> kind mapping.
_KINDS: dict[EvidenceType, Kind] = {
    EvidenceType.EVTX: "evtx",
    EvidenceType.HIVE: "registry",
}
# Artifacts registered as OTHER are disambiguated by exact filename.
_OTHER_BY_NAME: dict[str, Kind] = {
    "SRUDB.DAT": "srum",
    "$MFT": "mft",
    "_MFT": "mft",
    "_USNJRNL": "usnjrnl",
    "$USNJRNL": "usnjrnl",
}
# …or, failing an exact name, by file extension (the per-user activity glob set).
_OTHER_BY_SUFFIX: dict[str, Kind] = {
    ".pf": "prefetch",
    ".lnk": "lnk",
    ".automaticdestinations-ms": "jumplist",
}


def _kind_for(artifact_type: EvidenceType, name: str) -> Kind | None:
    """Resolve an artifact's feeder kind from its type, then OTHER name/suffix.

    OTHER routing tries the exact uppercased name first ($MFT, SRUDB.DAT, …), then
    the lowercased extension (.pf/.lnk/.automaticDestinations-ms), then the
    PowerShell-transcript filename convention — so a typo'd label is unrouted (and
    visibly skipped) rather than misrouted to the wrong parser."""
    direct = _KINDS.get(artifact_type)
    if direct is not None:
        return direct
    if artifact_type != EvidenceType.OTHER:
        return None
    by_name = _OTHER_BY_NAME.get(name.upper())
    if by_name is not None:
        return by_name
    lower = name.lower()
    by_suffix = _OTHER_BY_SUFFIX.get(Path(lower).suffix)
    if by_suffix is not None:
        return by_suffix
    if lower.startswith("powershell_transcript") and lower.endswith(".txt"):
        return "pstranscript"
    return None


@dataclass
class IngestResult:
    """Outcome of an ingest: rows per kind, failed artifacts, and per-record diagnostics.

    ``failures`` (whole-artifact errors) and ``diagnostics`` (per-record skips a feeder
    swallowed to keep going) are the load-bearing halves — the caller MUST surface both
    (operator summary + audit advisories) so neither a skipped artifact nor a partially
    parsed one hides behind a green result."""

    counts: dict[str, int] = field(default_factory=dict)
    failures: list[tuple[str, str, str]] = field(default_factory=list)  # (kind, name, error)
    # (kind, artifact name, {skip_reason: count}) for artifacts that dropped records.
    diagnostics: list[tuple[str, str, dict[str, int]]] = field(default_factory=list)


def _citation_path(path: Path) -> str:
    """Path relative to the ``prepared/`` root, for a stable, portable citation.

    Prepared artifacts always contain a ``prepared/`` segment, so the relative path is
    used. As a defensive fallback (path outside a prepared tree) we keep the last few
    components rather than a bare filename, so two same-named hives don't collide on an
    ambiguous citation."""
    parts = path.parts
    if _PREPARED in parts:
        return str(Path(*parts[parts.index(_PREPARED) + 1 :]))
    return str(Path(*parts[-3:])) if len(parts) >= 3 else path.name


def _feeder_for(kind: Kind) -> Feeder:
    """Resolve the feeder for ``kind`` from the (monkeypatchable) module globals.

    Built per call so tests can monkeypatch the feeder globals; an unknown kind raises
    ``KeyError`` rather than silently defaulting to one parser."""
    feeders: dict[Kind, Feeder] = {
        "evtx": evtx_file_records,
        "registry": registry_hive_records,
        "srum": srum_records,
        "mft": mft_entry_records,
        "usnjrnl": usnjrnl_records,
        "prefetch": prefetch_records,
        "lnk": lnk_records,
        "jumplist": jumplist_records,
        "pstranscript": pstranscript_records,
    }
    return feeders[kind]


def _parse_artifact(
    kind: Kind, path_str: str, cite: str, audit_id: str, host: str
) -> tuple[list[IndexRecord], dict[str, int]]:
    """Worker entry point: parse one artifact into ``(rows, skip_counts)``.

    Returns the skip counts alongside the rows so per-record drops survive the subprocess
    boundary and reach :class:`IngestResult.diagnostics`."""
    stats = FeederStats()
    feeder = _feeder_for(kind)
    rows = list(feeder(Path(path_str), audit_id=audit_id, host=host, source_path=cite, stats=stats))
    return rows, stats.skipped


def ingest_prepared_artifacts(
    registry: EvidenceRegistry,
    index: EvidenceIndex,
    *,
    audit_id: str,
    host: str = "",
    max_workers: int | None = None,
) -> IngestResult:
    """Parse every registered prepared artifact into ``index``; return counts + failures.

    Parses artifacts in parallel (default: cores-1) and bulk-inserts each artifact's rows
    (atomically) as it completes. ``max_workers=1`` runs in-process (used by tests). The
    caller must wrap this in ``index.begin_bulk()`` / ``index.rebuild_fts()`` for the
    deferred FTS build, and MUST surface :attr:`IngestResult.failures`."""
    tasks: list[tuple[Kind, Path, str]] = []
    for rec in registry.list_all():
        kind = _kind_for(rec.type, rec.path.name)
        if kind is not None:
            tasks.append((kind, rec.path, _citation_path(rec.path)))
    result = IngestResult()
    if not tasks:
        return result
    workers = max_workers if max_workers is not None else max(1, (os.cpu_count() or 2) - 1)
    if workers == 1:
        for kind, path, cite in tasks:
            _ingest_one(index, kind, path, cite, audit_id, host, result)
        return result

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_parse_artifact, kind, str(path), cite, audit_id, host): (kind, path)
            for kind, path, cite in tasks
        }
        for future in as_completed(futures):
            kind, path = futures[future]
            try:
                rows, skipped = future.result()
                written = index.bulk_ingest(rows)
            except Exception as exc:  # parse OR bulk-insert failure -> skip + record
                _LOG.warning("%s feeder failed on %s: %s", kind, path.name, exc)
                result.failures.append((kind, path.name, str(exc)))
                continue
            result.counts[kind] = result.counts.get(kind, 0) + written
            if skipped:
                result.diagnostics.append((kind, path.name, skipped))
    return result


def _ingest_one(
    index: EvidenceIndex,
    kind: Kind,
    path: Path,
    cite: str,
    audit_id: str,
    host: str,
    result: IngestResult,
) -> None:
    """In-process parse + atomic bulk-ingest of one artifact (the ``max_workers=1`` path).

    Same broad failure handling as the parallel path so the tested behaviour matches the
    shipped behaviour."""
    stats = FeederStats()
    try:
        written = index.bulk_ingest(
            _feeder_for(kind)(path, audit_id=audit_id, host=host, source_path=cite, stats=stats)
        )
    except Exception as exc:  # parse OR bulk-insert failure -> skip + record
        _LOG.warning("%s feeder failed on %s: %s", kind, path.name, exc)
        result.failures.append((kind, path.name, str(exc)))
        return
    result.counts[kind] = result.counts.get(kind, 0) + written
    if stats.skipped:
        result.diagnostics.append((kind, path.name, stats.skipped))


__all__ = ["IngestResult", "Kind", "ingest_prepared_artifacts"]
