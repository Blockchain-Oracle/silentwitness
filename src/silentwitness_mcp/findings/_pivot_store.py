"""Hypothesis-log readers for ``record_pivot``. Mirrors the split
``observation.py``/``_id_gen.py`` and ``interpretation.py``/
``_interpretation_store.py`` use — scanner helpers + the dedicated
store-corruption exception live here so the tool body stays under the
400-LOC CI cap (architecture.md §14)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Final

_PIVOT_ID_PATTERN: Final = re.compile(r"^P-(\d{3,})$")


class HypothesisStoreError(ValueError):
    """Raised when ``hypothesis.jsonl`` violates the persistence
    contract (missing/malformed ``hypothesis_id`` or ``pivot_id``).
    Inherits from ``ValueError`` so the catch in
    :func:`silentwitness_mcp.findings.pivot.record_pivot` maps it to
    ``AUDIT_STORE_CORRUPTED`` — same fail-closed pattern as
    :class:`~silentwitness_mcp.findings._interpretation_store.FindingsStoreError`."""


def existing_hypothesis_ids(hypothesis_log: Path) -> set[str]:
    """Set of every persisted ``hypothesis_id``, regardless of event
    ``type`` — chained pivots from a prior ``pivot`` row must match.
    Raises :class:`HypothesisStoreError` if a dict row carries a
    non-string ``hypothesis_id``; non-dict rows are tolerated."""
    if not hypothesis_log.exists():
        return set()
    ids: set[str] = set()
    for line in hypothesis_log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            continue
        if "hypothesis_id" not in record:
            continue
        hid = record["hypothesis_id"]
        if not isinstance(hid, str):
            raise HypothesisStoreError(f"hypothesis_id must be a string; got {type(hid).__name__}")
        ids.add(hid)
    return ids


def max_pivot_seq(hypothesis_log: Path) -> int:
    """Highest existing ``P-NNN`` sequence; allocator uses ``+1`` for
    the next pivot_id. Raises :class:`HypothesisStoreError` if any
    dict row's ``pivot_id`` is non-string or doesn't match ``P-NNN``;
    silent skip would risk a collision with an unseen existing ID."""
    if not hypothesis_log.exists():
        return 0
    highest = 0
    for line in hypothesis_log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            continue
        if "pivot_id" not in record:
            continue
        pid = record["pivot_id"]
        if not isinstance(pid, str):
            raise HypothesisStoreError(f"pivot_id must be a string; got {type(pid).__name__}")
        match = _PIVOT_ID_PATTERN.match(pid)
        if match is None:
            raise HypothesisStoreError(f"pivot_id {pid!r} does not match P-NNN format")
        seq = int(match.group(1))
        if seq > highest:
            highest = seq
    return highest


__all__ = ["HypothesisStoreError", "existing_hypothesis_ids", "max_pivot_seq"]
