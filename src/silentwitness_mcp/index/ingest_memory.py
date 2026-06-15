"""Memory-image driver — Volatility 3 subprocess + bulk-ingest into the case index.

The disk feeders are per-artifact (one ``.evtx`` / one hive / one ``.pf`` -> one feeder
call); a memory image is the inverse — one big raw blob driven by **many** vol3 plugins.
Each plugin call is a ``subprocess`` of the vendored vol3 venv (own Python, own deps,
own crash domain), invoked with ``-r json`` so its output is a stable list-of-dicts the
per-plugin mappers in :mod:`silentwitness_mcp.index.feeders_memory` map deterministically
to flat index rows.

Why a separate module from :mod:`ingest_artifacts`:
    The :class:`Feeder` protocol there is per-file. A memory pass is per-plugin over
    one image, with a long-running subprocess (netscan/psscan/malfind sweep all of
    physical memory). Forcing it into the Feeder shape would obscure the per-plugin
    failure surface — and a vol3 plugin that crashes mid-scan must be **counted and
    reported**, never silently dropped (CLAUDE.md: silent evidence loss is the worst
    bug). We mirror :class:`IngestResult` semantics here so the operator + audit see
    the same structured outcome.

``sha256`` is hashed once per image (before the vol3-binary check, so provenance
lands even on driver abort) and reused across plugin invocations — the image bytes
are the same artifact across every plugin pass.
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Protocol

from silentwitness_mcp.index._feeder_util import sha256_file
from silentwitness_mcp.index.feeders_memory import MAPPERS, PLUGINS, _short_plugin
from silentwitness_mcp.index.store import EvidenceIndex, IndexRecord

_LOG = logging.getLogger(__name__)

# CLAUDE.md pins this as the canonical SIFT/OVA install path; the driver accepts a
# `vol_bin=` override so tests and non-SIFT installs can point at their own venv.
_VOL_BIN: Final[str] = "/opt/silentwitness/vol3-venv/bin/vol"


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
# vol3 subprocess
# ---------------------------------------------------------------------------


def _run_vol_json(
    image: Path, plugin: str, *, timeout: int, vol_bin: str = _VOL_BIN
) -> list[dict[str, Any]]:
    """Run ``vol -r json -f <image> <plugin>`` and return its parsed JSON rows.

    Raises :class:`subprocess.CalledProcessError` on non-zero exit, ``TimeoutExpired``
    on hang, ``json.JSONDecodeError`` on garbled output, and ``ValueError`` on the
    two failure modes that look like success: empty stdout (some vol3 versions exit 0
    with no output when symbol resolution fails — observed on ROCBA Malfind) and a
    top-level dict instead of a list (some plugin renderers wrap rows as
    ``{"renderer": "json", "rows": [...]}``)."""
    completed = subprocess.run(  # noqa: S603  # fixed vendored vol3 binary, validated args
        [vol_bin, "-q", "-r", "json", "-f", str(image), plugin],
        capture_output=True,
        check=True,
        timeout=timeout,
    )
    if not completed.stdout.strip():
        raise ValueError(
            f"vol3 {plugin} produced empty output (exit 0) — likely symbol/profile failure"
        )
    parsed = json.loads(completed.stdout)
    if isinstance(parsed, dict) and isinstance(parsed.get("rows"), list):
        # Renderer-wrapped form: {"renderer": "json", "columns": [...], "rows": [...]}.
        # Older / future vol3 versions sometimes emit this instead of a bare list.
        parsed = parsed["rows"]
    if not isinstance(parsed, list):
        raise ValueError(f"vol3 {plugin} JSON output was not a list (got {type(parsed).__name__})")
    return [row for row in parsed if isinstance(row, dict)]


def _record_subprocess_failure(
    result: MemoryIngestResult, plugin: str, exc: subprocess.CalledProcessError
) -> None:
    """Fold vol3's stderr tail into the failure message — ``str(exc)`` alone only
    shows the exit code, dropping the actual diagnostic."""
    stderr_tail = (exc.stderr or b"").decode("utf-8", errors="replace").strip()[-500:]
    message = f"{exc} | stderr: {stderr_tail}" if stderr_tail else str(exc)
    _LOG.warning("vol3 %s failed: %s", plugin, message)
    result.failures.append((plugin, message))


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


class _IndexWriter(Protocol):
    """Structural protocol for the bulk_ingest sink. Lets tests inject a stub."""

    def bulk_ingest(self, records: Iterable[IndexRecord]) -> int: ...


def ingest_memory_image(
    image: Path,
    index: _IndexWriter | EvidenceIndex,
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
    # Hash up front (cheap relative to vol3) so the provenance hash is recorded even
    # if the vol3 binary is missing — a "vol3 absent" failure on a registered image
    # still produces a complete audit trail.
    result = MemoryIngestResult(image_sha256=sha256_file(image))
    if shutil.which(vol_bin) is None and not Path(vol_bin).exists():
        result.failures.append(("__driver__", f"vol3 binary not found at {vol_bin}"))
        return result
    cite = artifact_path if artifact_path is not None else image.name

    for plugin in plugins:
        mapper = MAPPERS.get(plugin)
        if mapper is None:
            result.failures.append((plugin, "no mapper registered"))
            continue
        try:
            rows = _run_vol_json(image, plugin, timeout=timeout_seconds, vol_bin=vol_bin)
        except subprocess.CalledProcessError as exc:
            _record_subprocess_failure(result, plugin, exc)
            continue
        except (
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
        except sqlite3.Error as exc:  # documented store failure mode — record, don't abort
            _LOG.warning("bulk ingest failed for %s: %s", plugin, exc)
            result.failures.append((plugin, f"bulk_ingest: {exc}"))
            continue
        result.counts[_short_plugin(plugin)] = written
    return result


__all__ = ["PLUGINS", "MemoryIngestResult", "ingest_memory_image"]
