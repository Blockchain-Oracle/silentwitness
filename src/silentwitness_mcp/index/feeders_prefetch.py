"""Prefetch feeder — Windows ``*.pf`` execution traces into :class:`IndexRecord` rows.

A prefetch file is written when a program runs, recording the executable name, a run
count, up to eight last-run timestamps and the full list of files/DLLs the process
referenced at startup — the on-disk answer to "what was executed, how often, when, and
what did it touch." Parsed with ``pyscca`` (libscca, the same libyal stack as our SRUM
``pyesedb`` reader), which transparently decompresses the Win10 MAM/Xpress-Huffman
container that pure-Python parsers stumble on.

``_prefetch_to_record`` is a pure mapper (unit-tested); ``prefetch_records`` drives pyscca
on a real ``.pf``. The most recent last-run time becomes the row ``ts``.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from silentwitness_mcp.index._feeder_util import MAX_TEXT, Feeder, FeederStats, sha256_file
from silentwitness_mcp.index.store import IndexRecord

# Cap referenced filenames per row — a prefetch can list hundreds; the first slice plus
# MAX_TEXT keeps the row searchable without bloating the index.
_MAX_FILES = 60


def _prefetch_to_record(
    *,
    executable: str,
    run_count: int,
    last_run_iso: str,
    volumes: list[str],
    filenames: list[str],
    pf_path: str,
    audit_id: str,
    host: str,
    sha256: str,
) -> IndexRecord:
    """Build one searchable prefetch row (executable + referenced files are the search keys)."""
    files = " ".join(filenames[:_MAX_FILES])
    vols = ",".join(volumes)
    text = f"Prefetch exe={executable} run_count={run_count} volumes={vols} files={files}"
    return IndexRecord(
        text=text[:MAX_TEXT],
        source_tool="prefetch",
        artifact_path=pf_path,
        host=host,
        ts=last_run_iso,
        audit_id=audit_id,
        sha256=sha256,
    )


def _latest_run_iso(times: list[datetime]) -> str:
    """ISO-8601 of the most recent non-null last-run time, or "" if none are recorded."""
    if not times:
        return ""
    return max(times).isoformat()


def _last_run_times(scca: Any) -> list[datetime]:
    """Collect the recorded (non-null) last-run datetimes, best-effort per slot."""
    times: list[datetime] = []
    for index in range(getattr(scca, "number_of_last_run_times", 0)):
        try:
            value = scca.get_last_run_time(index)
        except (OSError, ValueError):
            continue
        if isinstance(value, datetime):
            times.append(value)
    return times


def _volume_paths(scca: Any) -> list[str]:
    """Device paths of the volumes this prefetch references, best-effort per volume."""
    paths: list[str] = []
    for index in range(getattr(scca, "number_of_volumes", 0)):
        try:
            volume = scca.get_volume_information(index)
            device = volume.get_device_path()
        except (OSError, ValueError):
            continue
        if device:
            paths.append(str(device))
    return paths


def _filenames(scca: Any) -> list[str]:
    """The files/DLLs the process referenced at startup, best-effort per entry."""
    names: list[str] = []
    for index in range(getattr(scca, "number_of_filenames", 0)):
        try:
            name = scca.get_filename(index)
        except (OSError, ValueError):
            continue
        if name:
            names.append(str(name))
    return names


def prefetch_records(
    path: Path,
    *,
    audit_id: str,
    host: str = "",
    source_path: str | None = None,
    stats: FeederStats | None = None,
) -> Iterator[IndexRecord]:
    """Stream one :class:`IndexRecord` for a ``.pf`` file. ``pyscca`` is imported lazily."""
    import pyscca

    cite = source_path if source_path is not None else str(path)
    sha = sha256_file(path)
    scca = pyscca.file()
    scca.open(str(path))
    try:
        executable = str(scca.get_executable_filename() or "")
        run_count = int(scca.get_run_count() or 0)
        record = _prefetch_to_record(
            executable=executable,
            run_count=run_count,
            last_run_iso=_latest_run_iso(_last_run_times(scca)),
            volumes=_volume_paths(scca),
            filenames=_filenames(scca),
            pf_path=cite,
            audit_id=audit_id,
            host=host,
            sha256=sha,
        )
    finally:
        scca.close()
    yield record


# Compile-time assertion that the feeder still matches the shared contract.
_: Feeder = prefetch_records

__all__ = ["prefetch_records"]
