"""JSONL audit logger with restart-resume sequencing.

One ``AuditLogger`` instance per case directory. Every MCP tool call invokes
:meth:`emit` which:

  1. Atomically reserves the next ``audit_id`` for today (per architecture §4.4
     format ``sift-<examiner>-<YYYYMMDD>-<NNN>``) under an internal lock so
     two concurrent callers never collide.
  2. Constructs an :class:`silentwitness_common.types.AuditEntry`, validating
     the shape via Pydantic (extra='forbid', frozen=True).
  3. Serialises via ``model_dump_json`` (Decision A — drop structlog, use
     Pydantic directly per DEEP_AUDIT_REPORT) and appends to
     ``case_dir/audit/<backend>.jsonl`` via
     :func:`silentwitness_common.atomic_io.append_jsonl_line` (fsync + short-
     lived O_APPEND fd per architecture §4.4).

Restart-resume semantics (architecture §4.4): on construction the logger
scans every ``case_dir/audit/*.jsonl`` file, parses each line's ``audit_id``,
and tracks the highest sequence number seen per date. The next emit for that
date returns ``max + 1``. Cross-restart monotonicity is preserved.

This module is import-clean (no I/O at import time). All filesystem touches
go through the constructor or :meth:`emit`.
"""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path

from silentwitness_common.atomic_io import append_jsonl_line
from silentwitness_common.ids import make_audit_id, parse_audit_id
from silentwitness_common.types import AuditEntry

_BACKEND_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


def _default_clock() -> datetime:
    """UTC now — extracted so tests can substitute a deterministic clock."""
    return datetime.now(UTC)


class AuditLogger:
    """Thread-safe append-only JSONL writer for per-case MCP audit lines."""

    def __init__(
        self,
        case_dir: Path,
        examiner: str,
        clock: Callable[[], datetime] = _default_clock,
    ) -> None:
        """Build a logger rooted at ``case_dir`` for the given examiner handle.

        The ``audit/`` subdirectory is created on demand by the first
        :meth:`emit` call. Sequence state is loaded eagerly from any extant
        ``audit/*.jsonl`` files so a restarted server resumes monotonically.
        """
        self._case_dir = case_dir
        self._examiner = examiner
        self._clock = clock
        self._audit_dir = case_dir / "audit"
        self._lock = threading.Lock()
        # Map date → highest sequence number we've handed out (or seen on disk)
        # for that date. Other dates are unrepresented and start at 0 implicitly.
        self._seq_by_date: dict[date, int] = self._load_sequence_state()

    # ------------------------------------------------------------------ Public
    @property
    def case_dir(self) -> Path:
        return self._case_dir

    @property
    def examiner(self) -> str:
        return self._examiner

    def next_audit_id(self) -> str:
        """Reserve and return the next ``sift-<slug>-<YYYYMMDD>-<NNN>`` for today.

        Thread-safe: callers from multiple threads receive distinct sequence
        numbers in a contiguous range.
        """
        today = self._clock().date()
        with self._lock:
            seq = self._seq_by_date.get(today, 0) + 1
            self._seq_by_date[today] = seq
        return make_audit_id(self._examiner, today, seq)

    def emit(
        self,
        backend: str,
        tool: str,
        params: dict[str, object],
        result_summary: dict[str, object],
        result_sha256: str,
        stdout_path: Path,
        elapsed_ms: float,
        model_used: str,
        model_token_count: dict[str, int] | None = None,
    ) -> AuditEntry:
        """Compose an :class:`AuditEntry`, append it to
        ``case_dir/audit/<backend>.jsonl``, and return the entry.

        The next-audit-id reservation and the file append happen under the same
        internal lock so the on-disk sequence is monotonic for the current
        date — concurrent emit calls cannot interleave a "younger" line ahead
        of an "older" one.
        """
        self._check_backend_name(backend)
        target = self._audit_dir / f"{backend}.jsonl"
        with self._lock:
            today = self._clock().date()
            seq = self._seq_by_date.get(today, 0) + 1
            audit_id = make_audit_id(self._examiner, today, seq)
            entry = AuditEntry(
                ts=self._clock(),
                audit_id=audit_id,
                tool=tool,
                params=params,
                result_summary=result_summary,
                result_sha256=result_sha256,
                stdout_path=stdout_path,
                elapsed_ms=elapsed_ms,
                examiner=self._examiner,
                model_used=model_used,
                model_token_count=model_token_count or {},
            )
            # Pydantic v2 serialises Path as a string, datetime as ISO-8601.
            line = entry.model_dump_json()
            append_jsonl_line(target, line)
            # Only commit the sequence reservation AFTER a successful write —
            # if the append raised, the seq is NOT consumed and the next caller
            # gets the same number (correct: we never emitted a line for it).
            self._seq_by_date[today] = seq
        return entry

    def audit_id_of(self, entry: AuditEntry) -> str:
        """Trivial accessor for callers reading-through to the audit_id field."""
        return entry.audit_id

    # ------------------------------------------------------------------ Private
    @staticmethod
    def _check_backend_name(backend: str) -> None:
        if not _BACKEND_NAME_PATTERN.fullmatch(backend):
            raise ValueError(
                f"invalid backend name {backend!r} — must match "
                f"{_BACKEND_NAME_PATTERN.pattern} (no path separators, no leading "
                "digit, max 32 chars)"
            )

    def _load_sequence_state(self) -> dict[date, int]:
        """Scan ``case_dir/audit/*.jsonl`` and return ``{day: max_seq}``.

        Tolerates a missing audit dir, empty files, and malformed lines (the
        latter are skipped with no error — the parser is read-only and the
        line will still appear in the file for human inspection).
        """
        out: dict[date, int] = {}
        if not self._audit_dir.exists():
            return out
        for jsonl in sorted(self._audit_dir.glob("*.jsonl")):
            try:
                content = jsonl.read_text(encoding="utf-8")
            except OSError:
                continue
            for raw in content.splitlines():
                audit_id = self._extract_audit_id(raw)
                if audit_id is None:
                    continue
                try:
                    parts = parse_audit_id(audit_id)
                except ValueError:
                    continue
                prior = out.get(parts.day, 0)
                if parts.seq > prior:
                    out[parts.day] = parts.seq
        return out

    @staticmethod
    def _extract_audit_id(line: str) -> str | None:
        """Pull the ``audit_id`` field from a JSONL line; ``None`` if absent."""
        if not line.strip():
            return None
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return None
        value = obj.get("audit_id") if isinstance(obj, dict) else None
        return value if isinstance(value, str) else None


__all__ = ["AuditLogger"]
