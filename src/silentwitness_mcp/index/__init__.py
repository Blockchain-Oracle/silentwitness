"""Per-case evidence index (SQLite FTS5) — the queryable store the agent searches
instead of reading raw artifacts (Phase 1 of the real-evidence re-architecture)."""

from silentwitness_mcp.index.store import (
    EvidenceIndex,
    EvidenceIndexError,
    IndexRecord,
)

__all__ = ["EvidenceIndex", "EvidenceIndexError", "IndexRecord"]
