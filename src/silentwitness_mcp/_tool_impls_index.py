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
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from silentwitness_mcp._lifecycle import AppContext
from silentwitness_mcp._tool_impls import _case_deps, _GuardFn, _refuse
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.index.store import EvidenceIndex, EvidenceIndexError, IndexRecord

INDEX_TOOLS: frozenset[str] = frozenset({"search_evidence", "get_record", "timeline"})

_INDEX_DB = "index.db"
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 500
_NO_INDEX = (
    "no evidence index for this case — run `silentwitness prepare <case>` then "
    "index ingest to build it before searching"
)


def _record_dict(rec: IndexRecord) -> dict[str, Any]:
    """The LLM-facing shape of one index record (provenance-complete)."""
    return {
        "id": rec.id,
        "ts": rec.ts,
        "host": rec.host,
        "source_tool": rec.source_tool,
        "artifact_path": rec.artifact_path,
        "audit_id": rec.audit_id,
        "text": rec.text,
    }


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
        results = [_record_dict(h) for h in hits]
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
        """Re-fetch one evidence-index record by ``record_id`` (from a search hit) —
        e.g. to quote its full text verbatim when recording an observation."""
        case_dir, _registry, audit, model = _case_deps(ctx)
        index_path = case_dir / _INDEX_DB
        if not index_path.exists():
            return _refuse("INDEX_NOT_BUILT", _NO_INDEX)
        t0 = time.monotonic()
        with EvidenceIndex(index_path) as idx:
            rec = idx.get(record_id)
        if rec is None:
            return _refuse("RECORD_NOT_FOUND", f"no evidence-index record id={record_id}")
        _emit(audit, "get_record", {"record_id": record_id}, {"found": True}, index_path, t0, model)
        return {"success": True, "record": _record_dict(rec)}

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
        with EvidenceIndex(index_path) as idx:
            rows = idx.recent(host=host, source_tool=source_tool, limit=min(limit, _MAX_LIMIT))
        results = [_record_dict(r) for r in rows]
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
