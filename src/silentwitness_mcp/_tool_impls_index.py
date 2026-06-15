"""Evidence-index query tools — the agent's primary discovery interface.

``search_evidence`` / ``get_record`` / ``timeline`` query the per-case parsed
index (``cases/<id>/index.db``) instead of streaming a multi-GB artifact into the
model's context. They are case-bound (they read the case index), NOT
evidence-bound — they take no external path, so they need no mount guard.

This is the structural replacement for the raw ``read_tool_output`` discovery
pattern: the agent searches an index of parsed evidence and only pulls the exact
records it needs, each carrying the ``audit_id`` of the tool execution that
produced it (the audit-trail criterion).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from silentwitness_mcp._lifecycle import AppContext
from silentwitness_mcp._tool_impls import _case_deps, _GuardFn, _refuse
from silentwitness_mcp.audit.chain import append_chained_jsonl_line
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.index.store import EvidenceIndex, EvidenceIndexError, IndexRecord
from silentwitness_mcp.verification.sanitizer import StripEvent, StripEventWriter, sanitize

_LOG = logging.getLogger(__name__)

INDEX_TOOLS: frozenset[str] = frozenset(
    {"search_evidence", "get_record", "timeline", "list_detections"}
)

# Detection rows are tagged ``sigma:<level>``; severity order for summary + sampling.
_DETECTION_PREFIX = "sigma:"
_DETECTION_LEVELS = ("critical", "high", "medium", "low", "informational")
_DETECTION_SAMPLE_DEFAULT = 20

_INDEX_DB = "index.db"
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 500
# Sanitizer strip-event log lives OUTSIDE audit/ so the audit-logger's backend scan
# (which globs audit/*.jsonl) never mistakes these StripEvents for tool-execution records.
_SANITIZER_DIR = "sanitizer"
_SANITIZER_LOG = "index_sanitizer.jsonl"
_REDACTED = "[sanitizer error — record withheld from the model, see sanitizer log]"
_NO_INDEX = (
    "no evidence index for this case — run `silentwitness prepare <case>` then "
    "index ingest to build it before searching"
)


class _StripWriter(StripEventWriter):
    """Append sanitizer strip events to the case's index-sanitizer audit log."""

    def __init__(self, log_path: Path) -> None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._path = log_path

    def emit(self, event: StripEvent) -> None:
        append_chained_jsonl_line(self._path, event.model_dump_json())


def _record_dict(rec: IndexRecord, *, sanitize_text: str | None = None) -> dict[str, Any]:
    """The LLM-facing shape of one index record (provenance-complete).

    ``sanitize_text`` replaces the raw ``text`` with its sanitized+wrapped form — index
    rows are evidence-derived free text the agent reads, i.e. a prompt-injection surface,
    so the query boundary (where rows reach the LLM) sanitizes them."""
    return {
        "id": rec.id,
        "ts": rec.ts,
        "host": rec.host,
        "source_tool": rec.source_tool,
        "artifact_path": rec.artifact_path,
        "audit_id": rec.audit_id,
        "text": rec.text if sanitize_text is None else sanitize_text,
    }


def _sanitized_records(
    records: list[IndexRecord], *, audit_id: str, case_dir: Path
) -> list[dict[str, Any]]:
    """Sanitize each record's evidence text before it reaches the LLM-bound response.

    Sanitization is guarded PER RECORD: if ``sanitize`` raises on one row (e.g. a bad
    injection-catalog reload), that single row is withheld with a redaction marker rather
    than failing the whole query and silently erasing every other hit."""
    writer = _StripWriter(case_dir / _SANITIZER_DIR / _SANITIZER_LOG)
    out: list[dict[str, Any]] = []
    for rec in records:
        try:
            text = sanitize(rec.text, audit_id, audit_writer=writer).wrapped_text
        except Exception:  # one record's sanitizer failure must not drop the whole result set
            _LOG.warning("index sanitizer failed on record id=%s — withholding it", rec.id)
            text = _REDACTED
        out.append(_record_dict(rec, sanitize_text=text))
    return out


def _detection_summary(
    counts: dict[str, int],
    fetch: Callable[[str, int], list[IndexRecord]],
    limit: int,
) -> tuple[int, dict[str, int], list[IndexRecord]]:
    """Reduce ``source_tool -> count`` into (total, by_level, samples).

    ``by_level`` is ordered highest-severity-first and ALWAYS reconciles with ``total``: any
    ``sigma:*`` tool whose level isn't one of the standard severities lands in an ``other``
    bucket rather than being silently dropped from the summary. Samples are drawn
    highest-severity-first until the (clamped) ``limit`` budget is exhausted."""
    total = sum(counts.values())
    by_level: dict[str, int] = {}
    samples: list[IndexRecord] = []
    remaining = min(max(1, limit), _MAX_LIMIT)
    for level in _DETECTION_LEVELS:
        count = counts.get(f"{_DETECTION_PREFIX}{level}", 0)
        if not count:
            continue
        by_level[level] = count
        if remaining > 0:
            rows = fetch(f"{_DETECTION_PREFIX}{level}", remaining)
            samples.extend(rows)
            remaining -= len(rows)
    known = {f"{_DETECTION_PREFIX}{lvl}" for lvl in _DETECTION_LEVELS}
    other = sum(n for tool, n in counts.items() if tool not in known)
    if other:
        by_level["other"] = other
    return total, by_level, samples


def _emit(
    audit: AuditLogger,
    tool: str,
    params: dict[str, object],
    summary: dict[str, object],
    index_path: Path,
    t0: float,
    model: str,
) -> None:
    audit.emit(
        backend="index",
        tool=tool,
        params=params,
        result_summary=summary,
        result_sha256=hashlib.sha256(json.dumps(summary, sort_keys=True).encode()).hexdigest(),
        stdout_path=index_path,
        elapsed_ms=(time.monotonic() - t0) * 1000.0,
        model_used=model,
    )


def register_index_tools(mcp: FastMCP, guard_mount: _GuardFn) -> None:
    """Register the evidence-index query tools in :data:`INDEX_TOOLS`.

    ``guard_mount`` is accepted for a uniform registrant signature but unused —
    these tools query the case index, not a mounted evidence path."""

    @mcp.tool()
    async def search_evidence(
        ctx: Context[ServerSession, AppContext],
        query: str,
        host: str | None = None,
        source_tool: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        """Full-text search the parsed evidence index. ``query`` accepts FTS5 syntax
        (``a AND b``, ``a OR b``, ``prefix*``). Optional ``host`` / ``source_tool``
        narrow the hits. Returns ranked records; use get_record to re-fetch one."""
        case_dir, _registry, audit, model = _case_deps(ctx)
        index_path = case_dir / _INDEX_DB
        if not index_path.exists():
            return _refuse("INDEX_NOT_BUILT", _NO_INDEX)
        t0 = time.monotonic()
        audit_id = audit.next_audit_id()
        try:
            with EvidenceIndex(index_path) as idx:
                hits = idx.search(
                    query, host=host, source_tool=source_tool, limit=min(limit, _MAX_LIMIT)
                )
        except EvidenceIndexError as exc:
            return _refuse("INVALID_QUERY", str(exc))
        results = _sanitized_records(hits, audit_id=audit_id, case_dir=case_dir)
        _emit(
            audit,
            "search_evidence",
            {"query": query, "host": host, "source_tool": source_tool},
            {"hit_count": len(results)},
            index_path,
            t0,
            model,
        )
        return {
            "success": True,
            "audit_id": audit_id,
            "hit_count": len(results),
            "results": results,
        }

    @mcp.tool()
    async def get_record(ctx: Context[ServerSession, AppContext], record_id: int) -> dict[str, Any]:
        """Re-fetch one evidence-index record by ``record_id`` (from a search hit) to
        inspect its full text. The returned text is sanitized + wrapped (untrusted
        evidence) for display; the citation gate verifies a quoted span against the
        record's authoritative stored text by this same ``record_id``."""
        case_dir, _registry, audit, model = _case_deps(ctx)
        index_path = case_dir / _INDEX_DB
        if not index_path.exists():
            return _refuse("INDEX_NOT_BUILT", _NO_INDEX)
        t0 = time.monotonic()
        audit_id = audit.next_audit_id()
        with EvidenceIndex(index_path) as idx:
            rec = idx.get(record_id)
        if rec is None:
            return _refuse("RECORD_NOT_FOUND", f"no evidence-index record id={record_id}")
        _emit(audit, "get_record", {"record_id": record_id}, {"found": True}, index_path, t0, model)
        record = _sanitized_records([rec], audit_id=audit_id, case_dir=case_dir)[0]
        return {"success": True, "record": record}

    @mcp.tool()
    async def list_detections(
        ctx: Context[ServerSession, AppContext],
        limit: int = _DETECTION_SAMPLE_DEFAULT,
    ) -> dict[str, Any]:
        """Summarise the Sigma auto-detection hits staged during ingest — the recommended
        STARTING point for an investigation. Returns accurate per-severity counts plus the
        top sample detections (highest severity first), each a citable index record. Use
        this before blind search to anchor on what the rules already flagged."""
        case_dir, _registry, audit, model = _case_deps(ctx)
        index_path = case_dir / _INDEX_DB
        if not index_path.exists():
            return _refuse("INDEX_NOT_BUILT", _NO_INDEX)
        t0 = time.monotonic()
        audit_id = audit.next_audit_id()
        with EvidenceIndex(index_path) as idx:
            counts = idx.count_by_source_prefix(_DETECTION_PREFIX)
            total, by_level, samples = _detection_summary(
                counts,
                lambda tool, lim: idx.recent(source_tool=tool, limit=lim),
                limit,
            )
        results = _sanitized_records(samples, audit_id=audit_id, case_dir=case_dir)
        _emit(
            audit,
            "list_detections",
            {"limit": limit},
            {"total": total, "by_level": by_level},
            index_path,
            t0,
            model,
        )
        return {
            "success": True,
            "audit_id": audit_id,
            "total": total,
            "by_level": by_level,
            "samples": results,
        }

    @mcp.tool()
    async def timeline(
        ctx: Context[ServerSession, AppContext],
        host: str | None = None,
        source_tool: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        """Return evidence-index records newest-first (the chronological view),
        optionally filtered by ``host`` / ``source_tool``. Use for "what happened,
        in order" rather than a keyword hunt."""
        case_dir, _registry, audit, model = _case_deps(ctx)
        index_path = case_dir / _INDEX_DB
        if not index_path.exists():
            return _refuse("INDEX_NOT_BUILT", _NO_INDEX)
        t0 = time.monotonic()
        audit_id = audit.next_audit_id()
        with EvidenceIndex(index_path) as idx:
            rows = idx.recent(host=host, source_tool=source_tool, limit=min(limit, _MAX_LIMIT))
        results = _sanitized_records(rows, audit_id=audit_id, case_dir=case_dir)
        _emit(
            audit,
            "timeline",
            {"host": host, "source_tool": source_tool},
            {"count": len(results)},
            index_path,
            t0,
            model,
        )
        return {"success": True, "count": len(results), "results": results}


__all__ = ["INDEX_TOOLS", "register_index_tools"]
