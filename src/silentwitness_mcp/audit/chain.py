"""Hash-chained audit primitives — tamper-evident JSONL audit trail (Phase 6b).

Today's ``audit/*.jsonl`` is plain append-only JSON. Anyone with write access can
silently rewrite a prior row. This module adds two fields to every audit line —
``record_hash`` (sha256 over the canonical payload) and ``prev_record_hash``
(the prior row's ``record_hash``, or ``None`` for the first row). Modifying any
row breaks both its own ``record_hash`` and the ``prev_record_hash`` of the row
that follows, so a single tamper detectable at ``silentwitness verify
--audit-chain`` time.

Three consumer patterns:

1. :class:`AuditLogger.emit` (``silentwitness_mcp.audit.logger``) consumes
   :func:`compute_record_hash` for its own internally-buffered writes.
2. Direct JSONL writers (hypothesis, findings, hooks, critic, CLI commands)
   consume :func:`append_chained_jsonl_line`, which injects the chain fields,
   serialises the read-prev/compute/append window under a per-path lock, and
   atomically appends through ``atomic_io.append_jsonl_line``.
3. :mod:`silentwitness_agent.cli_commands.verify` consumes
   :func:`verify_chain_lines` at verify time.

I/O is confined to :func:`append_chained_jsonl_line` and
:func:`_read_last_record_hash`; everything else is pure.

Design choices
==============

- **Plain SHA-256, not HMAC.** The approval ledger uses HMAC because approvals
  are forwarded out of band; the audit log is verified in-place from the file
  bytes, so chaining is sufficient. HMAC would add key-management cost without
  buying additional guarantees against a tampering attacker who controls the
  file.
- **Per-backend chain.** Each ``<backend>.jsonl`` is its own chain. Simpler than
  a global merge across backends, and matches how the file is naturally bounded.
- **Canonical JSON via sort_keys + tight separators.** ``record_hash`` is over
  ``json.dumps(payload_dict_without_hash_fields, sort_keys=True,
  separators=(",", ":"))``. The on-disk line uses Pydantic's default format
  (different key order), so verification re-canonicalises before hashing.
- **Loud failure over silent restart.** When the seed read fails (unreadable
  file, malformed tail, chain mid-file regression), we raise
  :class:`ChainSeedError` rather than starting a fresh chain head — the verifier
  runs on demand, so a silent restart could mask days of evidence.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from silentwitness_common.atomic_io import append_jsonl_line

HASH_FIELDS: Final[frozenset[str]] = frozenset({"record_hash", "prev_record_hash"})


class ChainSeedError(RuntimeError):
    """Raised when the chain helper can't safely seed itself from an existing
    audit file. Silently restarting the chain head would mask the corruption
    until the next ``silentwitness verify --audit-chain`` run, which can be
    days away. Operator-visible failure is the safer default."""


# Process-scoped cache of the last record_hash per RESOLVED file path. The cache
# is keyed on ``path.resolve()`` so ``Path("./x")`` and ``Path("/abs/x")`` share
# one entry. Each entry is the chain head; the first write to a new path seeds
# it by reading the file's last row. Cache mutation is protected by the
# per-path lock acquired in :func:`_chain_write_lock`.
_LAST_HASH_CACHE: dict[Path, str | None] = {}

# Per-path locks. Threading lock for in-process serialisation; ``fcntl.flock`` on
# a sidecar ``.<filename>.chain.lock`` for cross-process. The two compose: the
# threading lock is acquired first (cheap, no syscall) and the flock second
# (cross-process, single audit-file lockfile).
_THREAD_LOCKS: dict[Path, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def _get_thread_lock(resolved_path: Path) -> threading.Lock:
    """Return the per-path threading.Lock, creating it on first request.

    The guard lock around the dict mutation is only ever held briefly enough to
    insert into the dict — every other access goes through the path-specific
    lock returned here, so contention on the guard is negligible."""
    with _THREAD_LOCKS_GUARD:
        lock = _THREAD_LOCKS.get(resolved_path)
        if lock is None:
            lock = threading.Lock()
            _THREAD_LOCKS[resolved_path] = lock
        return lock


@contextmanager
def _chain_write_lock(resolved_path: Path) -> Iterator[None]:
    """Serialise the read-prev/compute/append/cache-update window for ``path``.

    In-process threads block on the per-path ``threading.Lock``; cross-process
    writers block on ``fcntl.flock`` against a sidecar lockfile. The sidecar
    pattern keeps the lock independent of the audit file itself so
    :func:`atomic_io.append_jsonl_line`'s ``O_APPEND`` fd is unaffected."""
    thread_lock = _get_thread_lock(resolved_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar = resolved_path.parent / f".{resolved_path.name}.chain.lock"
    with thread_lock:
        sidecar.touch(exist_ok=True)
        with sidecar.open("rb+") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def canonical_payload(entry: dict[str, Any]) -> bytes:
    """Return the canonical bytes hashed by :func:`compute_record_hash`.

    The two hash fields are excluded (the hash cannot depend on its own value).
    Keys are sorted; separators are tight to keep the canonical form deterministic
    across Python versions. ``default=str`` handles ``datetime``, ``Path`` etc."""
    payload = {k: v for k, v in entry.items() if k not in HASH_FIELDS}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def compute_record_hash(prev_record_hash: str | None, payload: dict[str, Any]) -> str:
    """SHA-256 of ``(prev_record_hash || canonical(payload))``.

    For the very first row of a file, pass ``prev_record_hash=None``; only the
    payload is hashed. For every subsequent row, prepend the prior row's
    ``record_hash`` so any in-place edit also breaks the next row's chain."""
    h = hashlib.sha256()
    if prev_record_hash is not None:
        h.update(prev_record_hash.encode("utf-8"))
    h.update(canonical_payload(payload))
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Chained-append helper — for direct JSONL writers (hypothesis, findings, hooks,
# critic) that bypass :class:`silentwitness_mcp.audit.logger.AuditLogger.emit`.
# ---------------------------------------------------------------------------


def _read_last_record_hash(path: Path) -> str | None:
    """Seed the cache from an existing audit file.

    Returns ``None`` when the file is genuinely absent / empty / pre-chain
    (no row has ever had a ``record_hash``). Raises :class:`ChainSeedError`
    when the file exists but the seed cannot be trusted — unreadable file,
    malformed JSON at the tail, non-object tail, or a tail that lacks
    ``record_hash`` while earlier rows have one (a mid-file chain regression).
    Silently starting a fresh chain head in any of those cases would mask the
    corruption until the next on-demand verify run."""
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            last_line: str | None = None
            saw_record_hash = False
            for raw in fh:
                stripped = raw.strip()
                if not stripped:
                    continue
                last_line = stripped
                try:
                    entry = json.loads(stripped)
                except json.JSONDecodeError:
                    # Defer; we only raise if the tail itself is malformed.
                    continue
                if isinstance(entry, dict) and isinstance(entry.get("record_hash"), str):
                    saw_record_hash = True
    except OSError as exc:
        raise ChainSeedError(f"failed to read audit chain seed from {path}: {exc}") from exc

    if last_line is None:
        return None  # file is whitespace-only

    try:
        last_entry = json.loads(last_line)
    except json.JSONDecodeError as exc:
        preview = last_line[:80]
        raise ChainSeedError(
            f"audit chain seed at {path} ends with malformed JSON: {preview!r}"
        ) from exc
    if not isinstance(last_entry, dict):
        raise ChainSeedError(
            f"audit chain seed at {path} ends with non-object JSON: {type(last_entry).__name__}"
        )
    last_hash = last_entry.get("record_hash")
    if isinstance(last_hash, str):
        return last_hash
    if saw_record_hash:
        raise ChainSeedError(
            f"audit chain seed at {path}: tail row has no record_hash but "
            "earlier rows do — refusing to silently restart the chain"
        )
    return None  # pre-chain file; safe to start a fresh chain head


def append_chained_jsonl_line(path: Path, line: str) -> str:
    """Inject ``prev_record_hash`` + ``record_hash`` into a JSONL line, then
    atomically append it.

    ``line`` MUST be a valid JSON object — Pydantic ``model_dump_json()`` output
    is the canonical caller. The two hash fields are added (or overwritten if
    the caller naively set them) before the line is re-serialised + written.

    **Concurrency.** The read-prev/compute/append/cache-update window runs
    under :func:`_chain_write_lock`: a per-path ``threading.Lock`` (in-process)
    plus ``fcntl.flock`` on a sidecar ``.<filename>.chain.lock`` (cross-process).
    Two concurrent writers cannot race the seed-read. Path keys are normalised
    via ``path.resolve()`` so relative and absolute references to the same file
    share one lock + one cache entry.

    The chain head per resolved path is cached in-process for amortised O(1)
    writes — only the first write per ``(process, path)`` reads the file to
    seed; subsequent writes use the cached value.

    **Failure modes are loud, not silent.** If the seed read fails (unreadable
    file, malformed tail, chain regression), :class:`ChainSeedError` propagates
    to the caller. If ``line`` is not a JSON object, :class:`ValueError` is
    raised. The byte-level append delegates to
    :func:`atomic_io.append_jsonl_line`, which also raises on ``OSError``.

    Returns the assigned ``record_hash`` (useful for tests and for callers that
    want to confirm what they just wrote)."""
    payload = json.loads(line)
    if not isinstance(payload, dict):
        raise ValueError(f"chained JSONL line must be a JSON object, got {type(payload).__name__}")

    resolved = path.resolve()
    with _chain_write_lock(resolved):
        if resolved in _LAST_HASH_CACHE:
            prev_hash = _LAST_HASH_CACHE[resolved]
        else:
            prev_hash = _read_last_record_hash(resolved)

        payload["prev_record_hash"] = prev_hash
        record_hash = compute_record_hash(prev_hash, payload)
        payload["record_hash"] = record_hash

        chained_line = json.dumps(payload, separators=(",", ":"), default=str)
        append_jsonl_line(resolved, chained_line)
        _LAST_HASH_CACHE[resolved] = record_hash
        return record_hash


def strip_chain_fields_from_line(line: str) -> str:
    """Return ``line`` with the two chain fields removed — for Pydantic models
    declared ``extra="forbid"`` that need to round-trip a chained JSONL row
    back through ``model_validate_json``. The model's invariants stay strict
    (no foreign fields allowed) while the audit-trail consumer still parses.

    Raises :class:`ValueError` on non-object input — symmetric with
    :func:`append_chained_jsonl_line`. A caller piping a corrupted line would
    otherwise see a confusing Pydantic ``ValidationError`` downstream with no
    pointer to the strip step.

    Note: the returned bytes are re-canonicalised (tight separators, sorted
    keys are NOT applied — only ``separators=(",", ":")``); byte equality with
    the original on-disk line is not preserved. Use :func:`verify_chain_lines`
    for tamper detection, not byte comparison."""
    payload = json.loads(line)
    if not isinstance(payload, dict):
        raise ValueError(
            f"strip_chain_fields_from_line expects a JSON object, got {type(payload).__name__}"
        )
    payload.pop("prev_record_hash", None)
    payload.pop("record_hash", None)
    return json.dumps(payload, separators=(",", ":"), default=str)


def _reset_chain_cache() -> None:
    """Drop the in-process last-hash cache and per-path lock registry.

    **Test-only seam — not exported, not for production use.** Production code
    cannot safely call this: any concurrent writer would lose chain continuity.
    Tests import the private name explicitly (``from ... chain import
    _reset_chain_cache``); the underscore is the contract. The companion
    autouse pytest fixture in ``tests/conftest.py`` invokes this between every
    test so cross-test cache leakage is impossible."""
    _LAST_HASH_CACHE.clear()
    with _THREAD_LOCKS_GUARD:
        _THREAD_LOCKS.clear()


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChainBreak:
    """A single mismatch found while walking a chain. ``index`` is the 0-based
    line index in the file; ``reason`` is one of:

    - ``record_hash_mismatch``: recomputed hash != stored ``record_hash``
    - ``prev_record_hash_mismatch``: stored ``prev_record_hash`` != prior row's hash
    - ``record_hash_missing``: row is missing the field (chain never enabled)
    - ``malformed_json``: row is not valid JSON
    """

    index: int
    reason: str
    expected: str | None
    actual: str | None


@dataclass(frozen=True)
class ChainVerifyResult:
    """Outcome of :func:`verify_chain_lines`. ``ok`` is True iff every line
    chained cleanly; ``breaks`` lists every detected mismatch (caller decides
    whether to short-circuit on the first or report all)."""

    ok: bool
    rows_checked: int
    breaks: tuple[ChainBreak, ...]


def verify_chain_lines(lines: Iterable[str]) -> ChainVerifyResult:
    """Walk an iterable of JSONL lines and verify the chain.

    Each line is parsed, the ``record_hash`` field is checked against a fresh
    recomputation over the canonical payload, and the ``prev_record_hash`` is
    checked against the prior row's stored ``record_hash``. Empty lines are
    skipped. Caller is responsible for the file boundary."""
    breaks: list[ChainBreak] = []
    prior_hash: str | None = None
    rows = 0
    for index, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped:
            continue
        try:
            entry = json.loads(stripped)
        except json.JSONDecodeError:
            breaks.append(ChainBreak(index, "malformed_json", None, None))
            continue
        if not isinstance(entry, dict):
            breaks.append(ChainBreak(index, "malformed_json", None, None))
            continue
        rows += 1
        stored = entry.get("record_hash")
        if not isinstance(stored, str):
            breaks.append(ChainBreak(index, "record_hash_missing", None, None))
            continue
        # Recompute hash on the same canonical payload Pydantic wrote.
        # First row: prev should be None in storage AND in our walker.
        stored_prev = entry.get("prev_record_hash")
        recomputed = compute_record_hash(stored_prev, entry)
        if recomputed != stored:
            breaks.append(
                ChainBreak(index, "record_hash_mismatch", expected=recomputed, actual=stored)
            )
            continue
        # Forward-link check: the row's prev_record_hash must equal the prior
        # row's record_hash. Skipped for the first row (prior_hash is None).
        if rows == 1:
            # First row of the chain.
            if stored_prev is not None:
                breaks.append(
                    ChainBreak(
                        index, "prev_record_hash_mismatch", expected=None, actual=stored_prev
                    )
                )
                continue
        elif stored_prev != prior_hash:
            breaks.append(
                ChainBreak(
                    index, "prev_record_hash_mismatch", expected=prior_hash, actual=stored_prev
                )
            )
            continue
        prior_hash = stored
    return ChainVerifyResult(ok=not breaks, rows_checked=rows, breaks=tuple(breaks))


__all__ = [
    "HASH_FIELDS",
    "ChainBreak",
    "ChainSeedError",
    "ChainVerifyResult",
    "append_chained_jsonl_line",
    "canonical_payload",
    "compute_record_hash",
    "strip_chain_fields_from_line",
    "verify_chain_lines",
]
