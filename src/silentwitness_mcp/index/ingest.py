"""Parse extracted artifacts into the evidence index (Phase 1).

The broadest-coverage source is **plaso**: ``log2timeline.py`` runs hundreds of
artifact parsers over the prepared-artifacts directory and ``psort.py`` exports a
normalised super-timeline as JSON lines, which we map one-to-one into
:class:`~silentwitness_mcp.index.store.IndexRecord` rows. Running plaso over the
extracted artifacts (not the raw image) keeps it off the dfVFS VolumeScanner/VSS
path that crashes on the ROCBA E01 (see ``evidence/access.py``).

``_plaso_event_to_record`` is a pure mapping (unit-tested anywhere); the
``log2timeline``/``psort`` invocation is exercised on the Linux box where plaso is
installed (``uv sync --extra forensics``).
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path

from silentwitness_mcp.index.store import EvidenceIndex, IndexRecord

# Cap the per-event text we index so a pathological message can't bloat the DB.
_MAX_TEXT = 8192


class IngestError(Exception):
    """Raised when a parser tool fails or its output cannot be read."""


def _plaso_event_to_record(
    event: dict[str, object], *, audit_id: str, host: str
) -> IndexRecord | None:
    """Map one plaso ``json_line`` event to an :class:`IndexRecord`, or None.

    Events with no human-readable ``message`` carry no searchable content and are
    dropped. ``source_tool`` keeps the producing plaso parser so the agent can
    filter (e.g. ``source_tool='plaso:winevtx'``); ``artifact_path`` is the source
    file the event came from — the provenance the audit trail needs."""
    message = event.get("message")
    if not isinstance(message, str) or not message.strip():
        return None
    parser = event.get("parser")
    parser_name = parser if isinstance(parser, str) and parser else "unknown"
    path = event.get("display_name") or event.get("filename") or ""
    when = event.get("datetime")
    return IndexRecord(
        text=message[:_MAX_TEXT],
        source_tool=f"plaso:{parser_name}",
        artifact_path=str(path),
        host=host,
        ts=str(when) if isinstance(when, str) else "",
        audit_id=audit_id,
    )


def _iter_json_lines(path: Path) -> Iterator[dict[str, object]]:
    """Yield each JSON object from a ``psort`` json_line file, skipping junk lines."""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip().rstrip(",")  # json_line may comma-separate
            if not line or line in ("[", "]"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def ingest_plaso_timeline(
    source: Path,
    index: EvidenceIndex,
    *,
    audit_id: str,
    host: str = "",
    timeout: int = 3600,
) -> int:
    """Run plaso over ``source`` and ingest its super-timeline; return rows added.

    ``source`` is the prepared-artifacts directory (or a single artifact). Raises
    :class:`IngestError` if log2timeline / psort fail. plaso is imported lazily
    (it is the ``forensics`` extra), so this module loads without it installed."""
    log2timeline = _resolve_tool("log2timeline.py", "log2timeline")
    psort = _resolve_tool("psort.py", "psort")
    with tempfile.TemporaryDirectory(prefix="sw-plaso-") as tmp:
        storage = Path(tmp) / "timeline.plaso"
        json_out = Path(tmp) / "timeline.jsonl"
        _run(
            [log2timeline, "--status_view", "none", "--unattended", str(storage), str(source)],
            timeout=timeout,
            what="log2timeline",
        )
        _run(
            [psort, "-o", "json_line", "-w", str(json_out), str(storage)],
            timeout=timeout,
            what="psort",
        )
        if not json_out.is_file():
            raise IngestError(f"psort produced no output for {source}")
        records = (
            rec
            for event in _iter_json_lines(json_out)
            if (rec := _plaso_event_to_record(event, audit_id=audit_id, host=host)) is not None
        )
        return index.ingest(records)


def _resolve_tool(*names: str) -> str:
    """Return the path to the first plaso CLI name found, or raise."""
    import shutil

    for name in names:
        found = shutil.which(name)
        if found:
            return found
    raise IngestError(
        f"plaso tool not found (tried {names}) — install the forensics extra: "
        "`uv sync --extra forensics`"
    )


def _run(argv: list[str], *, timeout: int, what: str) -> None:
    """Run a plaso CLI step; raise :class:`IngestError` on failure/timeout."""
    try:
        completed = subprocess.run(  # noqa: S603
            argv, capture_output=True, check=False, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise IngestError(f"{what} failed to run: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace")[:500]
        raise IngestError(f"{what} exited {completed.returncode}: {detail}")


__all__ = ["IngestError", "ingest_plaso_timeline"]
