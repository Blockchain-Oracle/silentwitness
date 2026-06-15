"""SQLite FTS5 evidence index — the queryable store the agent searches.

One ``index.db`` per case. Phase-1 parsers (plaso / regipy / Volatility3) ingest
one :class:`IndexRecord` per evidence record — a timeline event, a registry
value, a memory artifact. The agent then *queries* by keyword (FTS5, with
optional host / source-tool filters) instead of streaming a 24 GB image into its
context. Every row carries ``audit_id`` so a finding traces back to the exact
tool execution that produced it (the audit-trail judging criterion).

Design: an external-content FTS5 table over the ``text`` (and ``artifact_path``)
columns of a plain ``record`` table. The plain table gives structured filtering
(``WHERE host = ?``) and stable row ids; FTS5 gives ranked full-text MATCH. We
only ever append (parsers produce immutable evidence rows), so there are no
update/delete triggers to keep in sync — ``ingest`` writes both tables together.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

_SCHEMA = """
CREATE TABLE IF NOT EXISTS record(
    id            INTEGER PRIMARY KEY,
    host          TEXT NOT NULL DEFAULT '',
    source_tool   TEXT NOT NULL DEFAULT '',
    artifact_path TEXT NOT NULL DEFAULT '',
    ts            TEXT NOT NULL DEFAULT '',
    audit_id      TEXT NOT NULL DEFAULT '',
    sha256        TEXT NOT NULL DEFAULT '',
    text          TEXT NOT NULL DEFAULT ''
);
CREATE VIRTUAL TABLE IF NOT EXISTS record_fts USING fts5(
    text, artifact_path, content='record', content_rowid='id', tokenize='unicode61'
);
CREATE INDEX IF NOT EXISTS idx_record_host ON record(host);
CREATE INDEX IF NOT EXISTS idx_record_source_tool ON record(source_tool);
"""

_COLUMNS = ("id", "host", "source_tool", "artifact_path", "ts", "audit_id", "sha256", "text")

# Literal SQL (no f-strings → no spurious S608); filters below append only
# constant fragments, every value still bound through a ? parameter.
_SEARCH_BASE = (
    "SELECT r.id, r.host, r.source_tool, r.artifact_path, r.ts, r.audit_id, "
    "r.sha256, r.text FROM record_fts JOIN record r ON r.id = record_fts.rowid "
    "WHERE record_fts MATCH ?"
)
_GET_SQL = (
    "SELECT id, host, source_tool, artifact_path, ts, audit_id, sha256, text "
    "FROM record WHERE id = ?"
)
_RECENT_BASE = (
    "SELECT id, host, source_tool, artifact_path, ts, audit_id, sha256, text "
    "FROM record WHERE 1 = 1"
)


class EvidenceIndexError(Exception):
    """Raised on a bad query or an index that cannot be opened."""


@dataclass(frozen=True)
class IndexRecord:
    """One searchable evidence row.

    ``text`` is the human-readable, FTS-indexed content (a timeline line, a
    registry value, a memory-plugin row). ``audit_id`` ties it to the tool
    execution that produced it; ``id`` is assigned by the store on ingest."""

    text: str
    source_tool: str = ""
    artifact_path: str = ""
    host: str = ""
    ts: str = ""
    audit_id: str = ""
    sha256: str = ""
    id: int | None = None


class EvidenceIndex:
    """A per-case SQLite FTS5 index. Use as a context manager or call ``close()``."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._conn = sqlite3.connect(str(db_path))
            self._conn.executescript(_SCHEMA)
        except sqlite3.Error as exc:
            raise EvidenceIndexError(f"cannot open evidence index at {db_path}: {exc}") from exc

    def ingest(self, records: Iterable[IndexRecord]) -> int:
        """Append rows to the index; return the number written.

        Writes the plain row and its FTS entry together in one transaction so a
        crash leaves the index consistent (either both or neither). For high-volume
        ingest prefer :meth:`bulk_ingest` + :meth:`rebuild_fts`."""
        written = 0
        try:
            with self._conn:  # transaction
                for rec in records:
                    cur = self._conn.execute(
                        "INSERT INTO record(host, source_tool, artifact_path, ts, audit_id, "
                        "sha256, text) VALUES(?, ?, ?, ?, ?, ?, ?)",
                        (
                            rec.host,
                            rec.source_tool,
                            rec.artifact_path,
                            rec.ts,
                            rec.audit_id,
                            rec.sha256,
                            rec.text,
                        ),
                    )
                    self._conn.execute(
                        "INSERT INTO record_fts(rowid, text, artifact_path) VALUES(?, ?, ?)",
                        (cur.lastrowid, rec.text, rec.artifact_path),
                    )
                    written += 1
        except sqlite3.Error as exc:
            raise EvidenceIndexError(f"index ingest failed after {written} rows: {exc}") from exc
        return written

    def bulk_ingest(self, records: Iterable[IndexRecord], *, batch: int = 10_000) -> int:
        """Append rows fast via batched ``executemany`` in ONE transaction, deferring FTS.

        Atomic per call: every row commits together or none does, so a mid-load
        ``sqlite3.Error`` can't leave a half-ingested artifact in the index (the caller
        skips the artifact cleanly). Skips per-row FTS maintenance (the dominant cost on
        million-row ingests); callers MUST call :meth:`rebuild_fts` once after all
        bulk_ingest calls so search works — ``rebuild`` reconstructs the FTS from the
        ``record`` content table, so content and FTS stay consistent."""
        insert = (
            "INSERT INTO record(host, source_tool, artifact_path, ts, audit_id, sha256, text) "
            "VALUES(?, ?, ?, ?, ?, ?, ?)"
        )
        written = 0
        chunk: list[tuple[str, str, str, str, str, str, str]] = []
        try:
            with self._conn:  # single transaction: all rows of this call, or none
                for rec in records:
                    chunk.append(
                        (
                            rec.host,
                            rec.source_tool,
                            rec.artifact_path,
                            rec.ts,
                            rec.audit_id,
                            rec.sha256,
                            rec.text,
                        )
                    )
                    if len(chunk) >= batch:
                        self._conn.executemany(insert, chunk)
                        written += len(chunk)
                        chunk.clear()
                if chunk:
                    self._conn.executemany(insert, chunk)
                    written += len(chunk)
        except sqlite3.Error as exc:
            raise EvidenceIndexError(f"bulk ingest failed: {exc}") from exc
        return written

    def begin_bulk(self) -> None:
        """Apply PRAGMAs that speed a large one-shot load (durability relaxed for build).

        Safe for an index rebuilt from immutable evidence: if the load crashes we just
        re-run ``index``; :meth:`rebuild_fts` restores full searchability."""
        for pragma in (
            "PRAGMA journal_mode=WAL",
            "PRAGMA synchronous=NORMAL",
            "PRAGMA temp_store=MEMORY",
            "PRAGMA cache_size=-262144",  # ~256 MB page cache
        ):
            self._conn.execute(pragma)

    def rebuild_fts(self) -> None:
        """Rebuild the FTS index from the ``record`` content table in one pass.

        Call once after :meth:`bulk_ingest` loads. Idempotent: it reconstructs the whole
        FTS from content, so mixing ``ingest`` and ``bulk_ingest`` rows stays correct."""
        try:
            with self._conn:
                self._conn.execute("INSERT INTO record_fts(record_fts) VALUES('rebuild')")
        except sqlite3.Error as exc:
            raise EvidenceIndexError(f"FTS rebuild failed: {exc}") from exc

    def search(
        self,
        query: str,
        *,
        host: str | None = None,
        source_tool: str | None = None,
        limit: int = 50,
    ) -> list[IndexRecord]:
        """Full-text search ``query`` (FTS5 syntax), newest-relevant first.

        ``host`` / ``source_tool`` apply exact-match structured filters on top of
        the text match. Raises :class:`EvidenceIndexError` on malformed FTS5
        syntax (so the agent gets a clear message, not a stack trace)."""
        sql = _SEARCH_BASE
        params: list[object] = [query]
        if host is not None:
            sql += " AND r.host = ?"
            params.append(host)
        if source_tool is not None:
            sql += " AND r.source_tool = ?"
            params.append(source_tool)
        sql += " ORDER BY record_fts.rank LIMIT ?"
        params.append(max(1, limit))
        try:
            rows = self._conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError as exc:
            raise EvidenceIndexError(f"invalid search query {query!r}: {exc}") from exc
        return [self._row_to_record(row) for row in rows]

    def get(self, record_id: int) -> IndexRecord | None:
        """Return the record with ``record_id``, or None if absent.

        Raises :class:`EvidenceIndexError` if the underlying database cannot be
        read (corrupt image, locked file) — callers get a structured error to
        convert into a rejection rather than a raw ``sqlite3.Error`` stack trace."""
        try:
            row = self._conn.execute(_GET_SQL, (record_id,)).fetchone()
        except sqlite3.Error as exc:
            raise EvidenceIndexError(f"cannot read record id={record_id}: {exc}") from exc
        return self._row_to_record(row) if row is not None else None

    def recent(
        self,
        *,
        host: str | None = None,
        source_tool: str | None = None,
        limit: int = 50,
    ) -> list[IndexRecord]:
        """Return records newest-first by timestamp (the timeline view), filtered.

        Unlike :meth:`search` this needs no text query — it answers "what happened,
        in order" with optional host / source-tool narrowing."""
        sql = _RECENT_BASE
        params: list[object] = []
        if host is not None:
            sql += " AND host = ?"
            params.append(host)
        if source_tool is not None:
            sql += " AND source_tool = ?"
            params.append(source_tool)
        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(max(1, limit))
        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def count(self) -> int:
        """Total rows in the index."""
        return int(self._conn.execute("SELECT COUNT(*) FROM record").fetchone()[0])

    def count_by_source_prefix(self, prefix: str) -> dict[str, int]:
        """Map ``source_tool`` -> row count for every tool whose name starts with ``prefix``.

        Used to summarise detection rows (``sigma:<level>``) accurately without streaming
        the (potentially tens of thousands of) matching rows into memory. ``prefix`` is a
        literal string; ``%``/``_`` in it are escaped so it can't act as a LIKE wildcard."""
        escaped = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        rows = self._conn.execute(
            "SELECT source_tool, COUNT(*) FROM record "
            "WHERE source_tool LIKE ? ESCAPE '\\' GROUP BY source_tool",
            (escaped + "%",),
        ).fetchall()
        return {str(name): int(n) for name, n in rows}

    @staticmethod
    def _row_to_record(row: tuple[object, ...]) -> IndexRecord:
        data = dict(zip(_COLUMNS, row, strict=True))
        raw_id = data["id"]
        return IndexRecord(
            id=int(raw_id) if isinstance(raw_id, int) else None,
            host=str(data["host"]),
            source_tool=str(data["source_tool"]),
            artifact_path=str(data["artifact_path"]),
            ts=str(data["ts"]),
            audit_id=str(data["audit_id"]),
            sha256=str(data["sha256"]),
            text=str(data["text"]),
        )

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> EvidenceIndex:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


__all__ = ["EvidenceIndex", "EvidenceIndexError", "IndexRecord"]
