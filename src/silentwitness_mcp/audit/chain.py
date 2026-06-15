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
from typing import Any, Final

HASH_FIELDS: Final[frozenset[str]] = frozenset({"record_hash", "prev_record_hash"})


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
    "canonical_payload",
    "compute_record_hash",
    "verify_chain_lines",
]
