"""JSONL audit logger with restart-resume sequencing.

One ``AuditLogger`` instance per case directory — enforced at runtime via an
``flock``-style lock on ``case_dir/audit/.lock``. Every MCP tool call invokes
:meth:`emit` which:

  1. Atomically reserves the next ``audit_id`` for today (per architecture §4.4
     format ``sift-<examiner>-<YYYYMMDD>-<NNN>``) under an internal threading
     lock so two concurrent callers never collide.
  2. Constructs an :class:`silentwitness_common.types.AuditEntry`, validating
     the shape via Pydantic (extra='forbid', frozen=True).
  3. Serialises via ``model_dump_json`` (Decision A — drop structlog, use
     Pydantic directly per DEEP_AUDIT_REPORT) and appends to
     ``case_dir/audit/<backend>.jsonl`` via
     :func:`silentwitness_common.atomic_io.append_jsonl_line`.

Restart-resume semantics (architecture §4.4): on construction the logger
scans every ``case_dir/audit/*.jsonl`` file, parses each line's ``audit_id``,
and tracks the highest sequence number seen per date. The next emit for that
date returns ``max + 1``. Cross-restart monotonicity is preserved.

Singleton-per-case contract: ``__init__`` acquires an exclusive ``fcntl.flock``
on ``case_dir/audit/.lock`` and HOLDS IT for the logger's lifetime. A second
:class:`AuditLogger` for the same ``case_dir`` raises ``RuntimeError`` rather
than silently colliding sequence numbers with the first instance. The flock
releases when the process exits or the logger is explicitly closed.

Failure-loud policy (PR-100 silent-failure review):
  * I/O errors reading prior audit files at startup propagate — a file we
    just ``glob``-ed but cannot ``open`` is a real corruption, not noise.
  * Malformed JSON / unrecognised audit_id format on a line is skipped (the
    line stays on disk for human review).
  * Disk-append failures during ``emit`` do NOT consume the sequence number.

This module is import-clean (no I/O at import time). All filesystem touches
go through the constructor or :meth:`emit`.
"""

from __future__ import annotations

import fcntl
import json
import re
import threading
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import IO

from silentwitness_common.atomic_io import append_jsonl_line
from silentwitness_common.ids import make_audit_id, parse_audit_id
from silentwitness_common.types import AuditEntry
from silentwitness_mcp.audit.chain import compute_record_hash

_BACKEND_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_LOCK_FILENAME = ".lock"


def _default_clock() -> datetime:
    """UTC now — extracted so tests can substitute a deterministic clock."""
    return datetime.now(UTC)


class AuditLogger:
    """Thread-safe + process-singleton append-only JSONL writer.

    One instance per ``case_dir`` per process. The constructor takes an
    ``flock`` on ``case_dir/audit/.lock``; a second logger for the same dir
    raises ``RuntimeError`` immediately. Within one process, ``emit`` is
    thread-safe via an internal ``threading.Lock``.
    """

    def __init__(
        self,
        case_dir: Path,
        examiner: str,
        clock: Callable[[], datetime] = _default_clock,
    ) -> None:
        """Build a logger rooted at ``case_dir`` for the given examiner handle.

        Raises ``RuntimeError`` if another live ``AuditLogger`` already owns
        the case directory (singleton-per-case contract).
        """
        self._case_dir = case_dir
        self._examiner = examiner
        self._clock = clock
        self._audit_dir = case_dir / "audit"
        self._lock = threading.Lock()
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        self._lock_handle: IO[bytes] | None = None
        self._acquire_singleton_lock()
        self._seq_by_date: dict[date, int] = self._load_sequence_state()
        # Phase 6b: last record_hash per backend, loaded at startup so
        # cross-restart the chain continues. None = no chain on disk yet
        # (first append for that backend).
        self._last_hash_by_backend: dict[str, str | None] = self._load_chain_state()

    def close(self) -> None:
        """Release the singleton flock + close the lock fd. Idempotent."""
        handle = self._lock_handle
        if handle is None:
            return
        self._lock_handle = None
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    def __del__(self) -> None:
        # Best-effort release; close() is the documented path. __del__ must
        # never raise — Python ignores exceptions there silently, which is
        # exactly the contract we want here.
        try:
            self.close()
        except OSError:
            pass

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

        Both the ``audit_id`` and the ``ts`` field come from a single
        ``self._clock()`` call so they agree on the calendar day even at
        midnight rollover. The next-audit-id reservation and the file append
        happen under the same internal lock so the on-disk sequence is
        monotonic for the current date.

        If ``append_jsonl_line`` raises (disk full, line contains a forbidden
        char from the tool's params, etc.), the sequence number is NOT
        consumed — the next emit returns the same number.
        """
        self._check_backend_name(backend)
        target = self._audit_dir / f"{backend}.jsonl"
        with self._lock:
            now = self._clock()
            today = now.date()
            seq = self._seq_by_date.get(today, 0) + 1
            audit_id = make_audit_id(self._examiner, today, seq)
            prev_hash = self._last_hash_by_backend.get(backend)
            # Construct the entry once with placeholder hash fields, then
            # canonicalise via the same JSON-roundtrip that `verify` will use.
            # This guarantees the hash computed here matches the hash recomputed
            # at verify time even if Pydantic's datetime/Path serialisation
            # differs from a hand-built dict.
            draft = AuditEntry(
                ts=now,
                audit_id=audit_id,
                tool=tool,
                params=params,
                result_summary=result_summary,
                result_sha256=result_sha256,
                stdout_path=stdout_path,
                elapsed_ms=elapsed_ms,
                examiner=self._examiner,
                model_used=model_used,
                model_token_count=model_token_count if model_token_count is not None else {},
                prev_record_hash=prev_hash,
                record_hash=None,
            )
            draft_dict = json.loads(draft.model_dump_json())
            record_hash = compute_record_hash(prev_hash, draft_dict)
            entry = draft.model_copy(update={"record_hash": record_hash})
            line = entry.model_dump_json()
            append_jsonl_line(target, line)
            # Only commit the sequence reservation + chain advance AFTER a
            # successful write — if any step above raised, the seq is NOT
            # consumed and the chain head does not advance.
            self._seq_by_date[today] = seq
            self._last_hash_by_backend[backend] = record_hash
        return entry

    # ------------------------------------------------------------------ Private
    @staticmethod
    def _check_backend_name(backend: str) -> None:
        if not _BACKEND_NAME_PATTERN.fullmatch(backend):
            raise ValueError(
                f"invalid backend name {backend!r} — must match "
                f"{_BACKEND_NAME_PATTERN.pattern} (no path separators, no leading "
                "digit, max 32 chars)"
            )

    def _acquire_singleton_lock(self) -> None:
        """Take an exclusive ``flock`` on ``case_dir/audit/.lock``.

        Raises ``RuntimeError`` if another process / live logger holds it.
        """
        lock_path = self._audit_dir / _LOCK_FILENAME
        handle = lock_path.open("ab")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            handle.close()
            raise RuntimeError(
                f"another AuditLogger already owns {self._case_dir} — "
                "singleton-per-case contract violated"
            ) from exc
        self._lock_handle = handle

    def _load_sequence_state(self) -> dict[date, int]:
        """Scan ``case_dir/audit/<backend>.jsonl`` and return ``{day: max_seq}``.

        Streams each file line-by-line so a multi-MB audit log doesn't blow up
        startup memory. Filters glob results to the canonical backend-name
        pattern so editor swap files (``.memory.jsonl.swp``) and the lock
        file are not parsed as audit data.

        Raises ``OSError`` if a glob-matched file cannot be opened — silent
        skip here would let a permission/IO error on a file holding seq=999
        silently reset the sequence to 1 and break cross-restart monotonicity.
        Malformed JSON or wrong audit_id shape ON a readable line IS skipped
        (the line stays on disk for human review).
        """
        out: dict[date, int] = {}
        for jsonl in sorted(self._audit_dir.glob("*.jsonl")):
            backend_stem = jsonl.stem
            if not _BACKEND_NAME_PATTERN.fullmatch(backend_stem):
                continue
            with jsonl.open("r", encoding="utf-8") as fh:
                for raw in fh:
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

    def _load_chain_state(self) -> dict[str, str | None]:
        """Scan each backend file's LAST non-empty line for ``record_hash``.

        Returns ``{backend: last_hash_or_None}``. None means the file is empty
        or the last entry pre-dates chaining (no ``record_hash`` field). For an
        empty backend file the next emit starts a fresh chain (prev=None);
        for a legacy pre-chain file the next emit will likewise produce a
        chain-start row — the legacy rows fail ``verify --audit-chain`` but
        do not block new writes."""
        out: dict[str, str | None] = {}
        for jsonl in sorted(self._audit_dir.glob("*.jsonl")):
            backend_stem = jsonl.stem
            if not _BACKEND_NAME_PATTERN.fullmatch(backend_stem):
                continue
            last_hash: str | None = None
            with jsonl.open("r", encoding="utf-8") as fh:
                for raw in fh:
                    stripped = raw.strip()
                    if not stripped:
                        continue
                    try:
                        obj = json.loads(stripped)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(obj, dict):
                        candidate = obj.get("record_hash")
                        if isinstance(candidate, str):
                            last_hash = candidate
            out[backend_stem] = last_hash
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
