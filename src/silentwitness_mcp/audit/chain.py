"""Hash-chained audit primitives — tamper-evident JSONL audit trail (Phase 6b).

Today's ``audit/*.jsonl`` is plain append-only JSON. Anyone with write access can
silently rewrite a prior row. This module adds two fields to every audit line —
``record_hash`` (sha256 over the canonical payload) and ``prev_record_hash``
(the prior row's ``record_hash``, or ``None`` for the first row). Modifying any
row breaks both its own ``record_hash`` and the ``prev_record_hash`` of the row
that follows, so a single tamper detectable at ``silentwitness verify
--audit-chain`` time.

Pure module. The :class:`AuditLogger` consumes :func:`compute_record_hash` at
emit time; :mod:`silentwitness_agent.cli_commands.verify` consumes
:func:`verify_chain_lines` at verify time. No I/O here; both callers handle the
file boundary.

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
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from silentwitness_common.atomic_io import append_jsonl_line

HASH_FIELDS: Final[frozenset[str]] = frozenset({"record_hash", "prev_record_hash"})

# Process-scoped cache of the last record_hash per file path. Each entry is the
# chain head; the first write to a new path seeds it by reading the file's last
# row. Caller must be the sole writer to a given path within a process — two
# concurrent writers would race the cache and produce siblings sharing the same
# prev_record_hash. The audit files are single-writer by design (one backend per
# logical producer); this assumption is documented in the module docstring.
_LAST_HASH_CACHE: dict[Path, str | None] = {}


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
    """Read the file's last non-empty JSON line and extract ``record_hash``.

    Returns ``None`` if the file is missing, empty, contains no chain field
    yet (pre-chain rows), or the last line is malformed. The caller treats
    ``None`` as "start a fresh chain head" — the next chained write becomes
    the first chained row."""
    if not path.exists():
        return None
    last_hash: str | None = None
    try:
        with path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                stripped = raw.strip()
                if not stripped:
                    continue
                try:
                    entry = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(entry, dict):
                    candidate = entry.get("record_hash")
                    if isinstance(candidate, str):
                        last_hash = candidate
    except OSError:
        # Caller's atomic_io.append_jsonl_line will surface the real I/O error
        # at write time; a transient read failure here just means we start a
        # fresh chain head — annoying but not silent (the verifier reports the
        # break point with file:line).
        return None
    return last_hash


def append_chained_jsonl_line(path: Path, line: str) -> str:
    """Inject ``prev_record_hash`` + ``record_hash`` into a JSONL line, then
    atomically append it.

    ``line`` MUST be a valid JSON object — Pydantic ``model_dump_json()`` output
    is the canonical caller. The two hash fields are added (or overwritten if
    the caller naively set them) before the line is re-serialised + written.

    The chain head per ``path`` is cached in-process for amortised O(1) writes.
    On the first write to a path the helper seeks the file's last line to seed
    the cache; subsequent writes from the same process use the cached value.

    **Single-writer constraint.** Two writers (threads or processes) appending
    to the same path concurrently would race: both could read the same prior
    hash and produce siblings sharing a ``prev_record_hash``, which would
    silently break the chain at verify time. Today every audit backend file has
    one logical writer (one per producer module), so this assumption holds. If
    we ever multiplex writers per file, wrap callers in an external lock.

    Returns the assigned ``record_hash`` (useful for tests / callers that want
    to record what they just wrote)."""
    payload = json.loads(line)
    if not isinstance(payload, dict):
        raise ValueError(f"chained JSONL line must be a JSON object, got {type(payload).__name__}")

    if path in _LAST_HASH_CACHE:
        prev_hash = _LAST_HASH_CACHE[path]
    else:
        prev_hash = _read_last_record_hash(path)

    payload["prev_record_hash"] = prev_hash
    record_hash = compute_record_hash(prev_hash, payload)
    payload["record_hash"] = record_hash

    chained_line = json.dumps(payload, separators=(",", ":"), default=str)
    append_jsonl_line(path, chained_line)
    _LAST_HASH_CACHE[path] = record_hash
    return record_hash


def strip_chain_fields_from_line(line: str) -> str:
    """Return ``line`` with the two chain fields removed — for Pydantic models
    declared ``extra="forbid"`` that need to round-trip a chained JSONL row
    back through ``model_validate_json``. The model's invariants stay strict
    (no foreign fields allowed) while the audit-trail consumer still parses."""
    payload = json.loads(line)
    if not isinstance(payload, dict):
        return line
    payload.pop("prev_record_hash", None)
    payload.pop("record_hash", None)
    return json.dumps(payload, separators=(",", ":"), default=str)


def reset_chain_cache() -> None:
    """Drop the in-process last-hash cache. Test seam — production code should
    not call this. Useful when a test resets ``audit/`` mid-run and expects the
    next write to re-seed from disk."""
    _LAST_HASH_CACHE.clear()


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
    "ChainVerifyResult",
    "append_chained_jsonl_line",
    "canonical_payload",
    "compute_record_hash",
    "reset_chain_cache",
    "strip_chain_fields_from_line",
    "verify_chain_lines",
]
