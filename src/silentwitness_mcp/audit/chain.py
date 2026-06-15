"""Hash-chained audit primitives — tamper-evident JSONL audit trail (Phase 6b).

``audit/*.jsonl`` rows carry ``record_hash`` (sha256 over canonical payload) and
``prev_record_hash`` (the prior row's hash, or ``None`` for the first row).
Modifying any row breaks both its own hash and the next row's prev — detected at
``silentwitness verify --audit-chain`` time.

Three consumer patterns: (1) :class:`AuditLogger.emit` calls
:func:`compute_record_hash`; (2) direct JSONL writers call
:func:`append_chained_jsonl_line` (lock + seed + atomic append); (3) the verify
command calls :func:`verify_chain_lines`. I/O lives in
:func:`append_chained_jsonl_line` and :func:`_read_last_record_hash`; everything
else is pure.

Design choices: plain SHA-256 (HMAC is in the approval ledger because that ledger
ships out of band; this one is verified from file bytes). Per-backend chain — one
chain per ``<backend>.jsonl``, never a global merge. Canonical JSON via
``sort_keys`` + tight separators so Pydantic's default key order verifies
identically. **Loud failure over silent restart**: chain-specific corruption at
the tail (malformed JSON, non-object, mid-file regression) raises
:class:`ChainSeedError` rather than starting a fresh chain; raw ``OSError`` (file
layout / permissions) propagates unchanged so caller envelopes can translate it
into structured ``FINDINGS_STORE_UNWRITABLE`` without losing the operator signal.
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


# Cache: resolved-path → (file_size_after_our_write, last_record_hash). The size
# detects cross-process writes; under the lock we compare current stat().st_size
# to cached — if it grew, we re-read (otherwise the chain forks silently).
_LAST_HASH_CACHE: dict[Path, tuple[int, str | None]] = {}

# Per-path locks: threading.Lock (in-process) + fcntl.flock on a sidecar under
# audit/.locks/ (cross-process). The .locks/ dir is dot-prefixed so it's hidden
# from ls, default tarballers, and the verifier's *.jsonl glob.
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


def _sidecar_lock_path(resolved_path: Path) -> Path:
    """Locate the sidecar flock target for an audit file.

    ``<resolved_path.parent>/.locks/<resolved_path.name>.lock`` — hidden by the
    dot-prefix, ignored by the verifier's ``*.jsonl`` glob, and out of the way
    of ``ls`` and routine backup tooling."""
    return resolved_path.parent / ".locks" / f"{resolved_path.name}.lock"


@contextmanager
def _chain_write_lock(resolved_path: Path) -> Iterator[None]:
    """Serialise the read-prev/compute/append/cache-update window for ``path``.

    In-process threads block on the per-path ``threading.Lock``; cross-process
    writers block on ``fcntl.flock`` against a sidecar lockfile under
    ``audit/.locks/``. The sidecar pattern keeps the lock independent of the
    audit file itself so :func:`atomic_io.append_jsonl_line`'s ``O_APPEND`` fd
    is unaffected.

    All ``OSError`` failures during lock acquisition (mkdir, touch, open,
    flock) are wrapped in :class:`ChainSeedError` so the chain-corruption
    surface is uniform — callers don't need to distinguish a permission
    failure on the lockfile from a corrupt-tail audit log."""
    thread_lock = _get_thread_lock(resolved_path)
    sidecar = _sidecar_lock_path(resolved_path)
    with thread_lock:
        try:
            sidecar.parent.mkdir(parents=True, exist_ok=True)
            sidecar.touch(exist_ok=True)
            fh = sidecar.open("rb+")
        except OSError as exc:
            raise ChainSeedError(f"failed to acquire chain lock at {sidecar}: {exc}") from exc
        try:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            except OSError as exc:
                raise ChainSeedError(f"flock failed on chain lock {sidecar}: {exc}") from exc
            try:
                yield
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()


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
    ONLY for chain-specific corruption: malformed JSON at the tail,
    non-object tail, or a tail that lacks ``record_hash`` while earlier rows
    have one (a mid-file chain regression).

    Raw ``OSError`` from the open/read (EACCES, EISDIR, EIO etc.) propagates
    unchanged — that's a file-layout / permission / hardware concern, not
    chain corruption, and the existing ``except OSError`` clauses in caller
    modules translate it into structured ``FINDINGS_STORE_UNWRITABLE`` /
    ``AUDIT_STORE_UNWRITABLE`` envelopes. Silently restarting the chain on
    OSError would be wrong — but raw OSError is not silent (caller envelope
    sets ``audit_write_failed=True``)."""
    if not path.exists():
        return None
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
    atomically append it. ``line`` MUST be a JSON object (Pydantic
    ``model_dump_json()`` output is the canonical caller).

    Concurrency: the read-prev/compute/append/cache window runs under
    :func:`_chain_write_lock` (per-path ``threading.Lock`` + ``fcntl.flock`` on
    a sidecar in ``audit/.locks/``). Path keys are normalised via
    ``path.resolve()`` so relative and absolute references share one cache
    entry. Under the lock the helper compares current file size to the cached
    size; if another process appended between our writes, the cache is stale
    and we re-read disk (otherwise cross-process chains fork silently).

    Failure modes: malformed tail / chain regression → :class:`ChainSeedError`;
    failed lock acquisition (permission, EROFS, ENOSPC) → :class:`ChainSeedError`;
    non-object ``line`` → :class:`ValueError`; raw seed-read OSError propagates
    unchanged for caller envelopes to translate. Returns the assigned
    ``record_hash``."""
    payload = json.loads(line)
    if not isinstance(payload, dict):
        raise ValueError(f"chained JSONL line must be a JSON object, got {type(payload).__name__}")

    resolved = path.resolve()
    with _chain_write_lock(resolved):
        current_size = resolved.stat().st_size if resolved.exists() else 0
        cached = _LAST_HASH_CACHE.get(resolved)
        if cached is not None and cached[0] == current_size:
            prev_hash = cached[1]
        else:
            prev_hash = _read_last_record_hash(resolved)

        payload["prev_record_hash"] = prev_hash
        record_hash = compute_record_hash(prev_hash, payload)
        payload["record_hash"] = record_hash

        chained_line = json.dumps(payload, separators=(",", ":"), default=str)
        append_jsonl_line(resolved, chained_line)
        _LAST_HASH_CACHE[resolved] = (resolved.stat().st_size, record_hash)
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
