"""Memory-image ingest — Volatility 3 plugin output into :class:`IndexRecord` rows.

The disk feeders are per-artifact (one ``.evtx`` / one hive / one ``.pf`` -> one feeder
call); a memory image is the inverse — one big raw blob driven by **many** vol3 plugins.
Each plugin call is a ``subprocess`` of the vendored vol3 venv (own Python, own deps,
own crash domain), invoked with ``-r json`` so its output is a stable list-of-dicts we
can map deterministically to flat index rows. The mappers are pure (unit-testable
against the captured schemas in :file:`tests/fixtures/vol3/*.json`); the driver is the
thin I/O wrapper.

Why a separate module from :mod:`ingest_artifacts`:
    The :class:`Feeder` protocol there is per-file. A memory pass is per-plugin over
    one image, with a long-running subprocess (netscan/psscan/malfind sweep all of
    physical memory). Forcing it into the Feeder shape would obscure the per-plugin
    failure surface — and a vol3 plugin that crashes mid-scan must be **counted and
    reported**, never silently dropped (CLAUDE.md: silent evidence loss is the worst
    bug). We mirror :class:`IngestResult` semantics here so the operator + audit see
    the same structured outcome.

Provenance: ``source_tool="vol:<plugin>"`` (so `list_detections` and the citation gate
can tell a memory row apart from a disk row); ``artifact_path`` is the image's
prepared-relative path plus a ``#vol:<plugin>`` fragment so a citation pin-points the
plugin that produced the row. ``sha256`` is hashed once per image and reused across
plugin invocations — the image bytes are the same artifact across every plugin pass.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import subprocess
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from silentwitness_mcp.index._feeder_util import MAX_TEXT, sha256_file
from silentwitness_mcp.index.store import EvidenceIndex, IndexRecord

_LOG = logging.getLogger(__name__)

# Per-process child caps: pslist/psscan never nest; malfind's __children carry the
# hit-list. We never recurse beyond one level — vol3 only ever emits one.
_VOL_BIN: Final[str] = "/opt/silentwitness/vol3-venv/bin/vol"

# The plugins we ingest. Order is irrelevant for correctness (each is an independent
# subprocess); kept stable for reproducible audit-summary output.
PLUGINS: Final[tuple[str, ...]] = (
    "windows.pslist.PsList",
    "windows.cmdline.CmdLine",
    "windows.netscan.NetScan",
    "windows.malware.malfind.Malfind",
    "windows.psscan.PsScan",
)


@dataclass
class MemoryIngestResult:
    """Per-plugin row counts + per-plugin failures (mirrors :class:`IngestResult`).

    A plugin that crashes or times out lands in ``failures``; the caller MUST surface
    it. A successful plugin that emitted zero rows is recorded in ``counts`` as 0 (so
    "the plugin ran and the image legitimately had nothing" is distinguishable from
    "the plugin never ran"). ``image_sha256`` is the one-time hash of the raw image."""

    counts: dict[str, int] = field(default_factory=dict)
    failures: list[tuple[str, str]] = field(default_factory=list)  # (plugin, error)
    image_sha256: str = ""


# ---------------------------------------------------------------------------
# Pure mappers — one per plugin. Unit-tested against captured vol3 JSON.
# ---------------------------------------------------------------------------


def _short_plugin(plugin: str) -> str:
    """``windows.pslist.PsList`` -> ``pslist`` — the short form used in source_tool."""
    return plugin.rsplit(".", 1)[-1].lower()


def _row_text(prefix: str, **fields: Any) -> str:
    """``Process pid=4 ppid=0 name=System`` — stable space-joined ``key=value`` line.

    Skips ``None`` so an absent column doesn't read as the literal string ``None`` in
    the FTS-indexed text (which would be searchable and misleading)."""
    parts = [prefix]
    for key, value in fields.items():
        if value is None or value == "":
            continue
        parts.append(f"{key}={value}")
    return " ".join(parts)


def _make_record(
    *,
    text: str,
    plugin: str,
    artifact_path: str,
    host: str,
    ts: str,
    audit_id: str,
    sha256: str,
) -> IndexRecord:
    return IndexRecord(
        text=text[:MAX_TEXT],
        source_tool=f"vol:{_short_plugin(plugin)}",
        artifact_path=f"{artifact_path}#vol:{_short_plugin(plugin)}",
        host=host,
        ts=ts,
        audit_id=audit_id,
        sha256=sha256,
    )


def _pslist_to_records(
    rows: Iterable[dict[str, Any]],
    *,
    artifact_path: str,
    audit_id: str,
    host: str,
    sha256: str,
) -> Iterator[IndexRecord]:
    for row in rows:
        text = _row_text(
            "Process",
            pid=row.get("PID"),
            ppid=row.get("PPID"),
            name=row.get("ImageFileName"),
            threads=row.get("Threads"),
            wow64=row.get("Wow64"),
            exited=row.get("ExitTime"),
        )
        yield _make_record(
            text=text,
            plugin="windows.pslist.PsList",
            artifact_path=artifact_path,
            host=host,
            ts=str(row.get("CreateTime") or ""),
            audit_id=audit_id,
            sha256=sha256,
        )


def _cmdline_to_records(
    rows: Iterable[dict[str, Any]],
    *,
    artifact_path: str,
    audit_id: str,
    host: str,
    sha256: str,
) -> Iterator[IndexRecord]:
    for row in rows:
        args = row.get("Args")
        # Skip processes vol3 couldn't read a cmdline for — their PID still shows in
        # pslist; emitting a row with no Args adds noise without investigative value.
        if not args:
            continue
        text = _row_text(
            "Cmdline",
            pid=row.get("PID"),
            process=row.get("Process"),
            args=args,
        )
        yield _make_record(
            text=text,
            plugin="windows.cmdline.CmdLine",
            artifact_path=artifact_path,
            host=host,
            ts="",  # cmdline is a snapshot — no per-row timestamp
            audit_id=audit_id,
            sha256=sha256,
        )


def _netscan_to_records(
    rows: Iterable[dict[str, Any]],
    *,
    artifact_path: str,
    audit_id: str,
    host: str,
    sha256: str,
) -> Iterator[IndexRecord]:
    for row in rows:
        text = _row_text(
            "NetConn",
            proto=row.get("Proto"),
            local=f"{row.get('LocalAddr')}:{row.get('LocalPort')}"
            if row.get("LocalAddr")
            else None,
            foreign=f"{row.get('ForeignAddr')}:{row.get('ForeignPort')}"
            if row.get("ForeignAddr")
            else None,
            state=row.get("State"),
            pid=row.get("PID"),
            owner=row.get("Owner"),
        )
        yield _make_record(
            text=text,
            plugin="windows.netscan.NetScan",
            artifact_path=artifact_path,
            host=host,
            ts=str(row.get("Created") or ""),
            audit_id=audit_id,
            sha256=sha256,
        )


def _malfind_to_records(
    rows: Iterable[dict[str, Any]],
    *,
    artifact_path: str,
    audit_id: str,
    host: str,
    sha256: str,
) -> Iterator[IndexRecord]:
    """Malfind emits one row per suspicious VAD region (executable + private memory).

    The Hexdump column is large and noisy for FTS; we keep the structural fields
    (process, address, protection, tag) since those are what an analyst correlates."""
    for row in rows:
        text = _row_text(
            "Malfind",
            pid=row.get("PID"),
            process=row.get("Process"),
            start=row.get("Start VPN") or row.get("Start"),
            end=row.get("End VPN") or row.get("End"),
            tag=row.get("Tag"),
            protection=row.get("Protection"),
            commit=row.get("CommitCharge"),
            private=row.get("PrivateMemory"),
        )
        yield _make_record(
            text=text,
            plugin="windows.malware.malfind.Malfind",
            artifact_path=artifact_path,
            host=host,
            ts="",
            audit_id=audit_id,
            sha256=sha256,
        )


def _psscan_to_records(
    rows: Iterable[dict[str, Any]],
    *,
    artifact_path: str,
    audit_id: str,
    host: str,
    sha256: str,
) -> Iterator[IndexRecord]:
    """Same shape as pslist but found by pool scanning (catches unlinked / hidden procs).

    A process visible in psscan but absent from pslist is a strong rootkit signal —
    keeping them as separate ``vol:psscan`` rows lets a query / detector compare."""
    for row in rows:
        text = _row_text(
            "ProcessScan",
            pid=row.get("PID"),
            ppid=row.get("PPID"),
            name=row.get("ImageFileName"),
            threads=row.get("Threads"),
            exited=row.get("ExitTime"),
        )
        yield _make_record(
            text=text,
            plugin="windows.psscan.PsScan",
            artifact_path=artifact_path,
            host=host,
            ts=str(row.get("CreateTime") or ""),
            audit_id=audit_id,
            sha256=sha256,
        )


_MAPPERS: Final[dict[str, Any]] = {
    "windows.pslist.PsList": _pslist_to_records,
    "windows.cmdline.CmdLine": _cmdline_to_records,
    "windows.netscan.NetScan": _netscan_to_records,
    "windows.malware.malfind.Malfind": _malfind_to_records,
    "windows.psscan.PsScan": _psscan_to_records,
}


# ---------------------------------------------------------------------------
# Driver — subprocess + JSON parse + bulk ingest.
# ---------------------------------------------------------------------------


def _run_vol_json(
    image: Path, plugin: str, *, timeout: int, vol_bin: str = _VOL_BIN
) -> list[dict[str, Any]]:
    """Run ``vol -r json -f <image> <plugin>`` and return its parsed JSON array.

    Raises :class:`subprocess.CalledProcessError` on non-zero exit, ``TimeoutExpired``
    on hang, ``json.JSONDecodeError`` on garbled output, ``FileNotFoundError`` if vol3
    isn't installed — each becomes one ``(plugin, error)`` entry in the driver."""
    completed = subprocess.run(  # noqa: S603  # fixed vendored vol3 binary, validated args
        [vol_bin, "-q", "-r", "json", "-f", str(image), plugin],
        capture_output=True,
        check=True,
        timeout=timeout,
    )
    parsed = json.loads(completed.stdout)
    if not isinstance(parsed, list):
        raise ValueError(f"vol3 {plugin} JSON output was not a list (got {type(parsed).__name__})")
    return [row for row in parsed if isinstance(row, dict)]


def ingest_memory_image(
    image: Path,
    index: EvidenceIndex,
    *,
    audit_id: str,
    artifact_path: str | None = None,
    host: str = "",
    plugins: tuple[str, ...] = PLUGINS,
    timeout_seconds: int = 3600,
    vol_bin: str = _VOL_BIN,
) -> MemoryIngestResult:
    """Run each ``plugins`` plugin against ``image``, ingest rows, return the result.

    ``artifact_path`` is the citation pin (typically prepared-relative); defaults to
    the image filename so a missing override still produces a stable citation. The
    caller is responsible for the outer ``index.begin_bulk()`` / ``rebuild_fts()`` —
    matching :func:`ingest_prepared_artifacts` so the disk + memory passes share one
    FTS build."""
    if shutil.which(vol_bin) is None and not Path(vol_bin).exists():
        return MemoryIngestResult(
            failures=[("__driver__", f"vol3 binary not found at {vol_bin}")],
        )
    result = MemoryIngestResult(image_sha256=sha256_file(image))
    cite = artifact_path if artifact_path is not None else image.name

    for plugin in plugins:
        mapper = _MAPPERS.get(plugin)
        if mapper is None:
            result.failures.append((plugin, "no mapper registered"))
            continue
        try:
            rows = _run_vol_json(image, plugin, timeout=timeout_seconds, vol_bin=vol_bin)
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            _LOG.warning("vol3 %s failed: %s", plugin, exc)
            result.failures.append((plugin, str(exc)))
            continue
        records = list(
            mapper(
                rows,
                artifact_path=cite,
                audit_id=audit_id,
                host=host,
                sha256=result.image_sha256,
            )
        )
        try:
            written = index.bulk_ingest(records)
        except Exception as exc:  # SQLite write failure -> count + record, don't abort
            _LOG.warning("bulk ingest failed for %s: %s", plugin, exc)
            result.failures.append((plugin, f"bulk_ingest: {exc}"))
            continue
        result.counts[_short_plugin(plugin)] = written
    return result


def _content_hash(rows: list[dict[str, Any]]) -> str:
    """Stable hash of a vol3 JSON list — useful for unit-test fixtures."""
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


__all__ = [
    "PLUGINS",
    "MemoryIngestResult",
    "ingest_memory_image",
]
