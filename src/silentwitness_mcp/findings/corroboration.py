"""Corroboration tier — advisory label per finding (CONFIRMED / INFERRED / UNVERIFIED).

Computed from the diversity of evidence categories spanned by the finding's cited
records. The label rides alongside the finding in :file:`findings.json` and surfaces
in :file:`report.md`; it does NOT block APPROVED status (see the deadline-night plan
addendum for the rationale).

How it works
============

Every :class:`IndexRecord` carries a ``source_tool`` string set by the feeder that
produced the row (``evtx:Security``, ``vol:netscan``, ``regipy:NTUSER``,
``mft``, …). We map each ``source_tool`` to a coarse evidence **category**
(``memory``, ``system_log``, ``registry``, …) via :data:`_SOURCE_CATEGORY`. Two
records of the same category are not independent — they're the same investigative
lens. Two records of **different** categories triangulate; that diversity is what
"corroborated" actually means in practice.

  - **CONFIRMED**  — ≥ 2 distinct categories present
  - **INFERRED**   — 1 category, ≥ 2 records (multiple touchpoints, single lens)
  - **UNVERIFIED** — single record (or no resolvable cited records)

Why categories, not raw ``source_tool``: two ``evtx:*`` rows (Security log + System
log) are still both "system log" — counting them as independent would credit a
single-source claim. The category map is the architectural seam that decides what
counts as "another viewpoint."

Pure function. No I/O. Unit-testable against a hand-built list of records.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Final

from silentwitness_mcp.index.store import IndexRecord


class CorroborationTier(StrEnum):
    """Advisory tier surfaced on every materialised finding."""

    CONFIRMED = "CONFIRMED"
    INFERRED = "INFERRED"
    UNVERIFIED = "UNVERIFIED"


# source_tool prefix -> coarse evidence category.
#
# The prefix may be the full source_tool (no colon, e.g. ``mft``) or the
# ``<family>:`` prefix (e.g. ``vol:pslist`` -> ``vol``). Categorisation prefers
# exact match first, then the ``<family>:`` prefix. Anything not mapped lands in
# the catch-all ``other`` category so we never silently drop a row.
_SOURCE_CATEGORY: Final[dict[str, str]] = {
    # Memory (vol3 plugins) — vol:pslist, vol:netscan, vol:malfind, …
    "vol": "memory",
    # System / application event logs — evtx:Security/System/…; powershell:transcript.
    # NB: PowerShell-transcript rows are emitted as ``powershell:transcript`` by the
    # feeder, NOT ``pstranscript`` — keying it as ``powershell`` is load-bearing
    # (round-1 review caught this as a silent miscategorisation to ``other``).
    "evtx": "system_log",
    "powershell": "system_log",
    # Windows registry — regipy:NTUSER, regipy:Amcache_*, …
    # Amcache (program-execution registry hive) lives here, not under user_activity,
    # because the hive is the lens; bucketing Amcache rows separately from other
    # regipy rows would let a single-hive finding read as CONFIRMED.
    "regipy": "registry",
    # Filesystem metadata
    "mft": "filesystem",
    "usnjrnl": "filesystem",
    # User-activity artifacts. SRUM (System Resource Usage Monitor) covers
    # network + energy + app-usage tables; we bucket it as user_activity so it
    # pairs against Prefetch/LNK rather than double-counting against future
    # netflow feeders.
    "prefetch": "user_activity",
    "lnk": "user_activity",
    "jumplist": "user_activity",
    "srum": "user_activity",
    # Detection layer (Sigma) — single category regardless of severity bucket
    "sigma": "detection",
    # Plaso super-timeline breadth
    "plaso": "timeline_breadth",
}


def categorize(source_tool: str) -> str:
    """Map a ``source_tool`` string to its coarse category.

    Returns ``"other"`` for anything not in :data:`_SOURCE_CATEGORY` — surfacing
    such rows under their own bucket prevents an unmapped feeder from masquerading
    as corroboration (every unmapped source_tool clusters as one category)."""
    if not source_tool:
        return "other"
    # Exact match wins (the plain-form keys like ``mft`` / ``usnjrnl``).
    if source_tool in _SOURCE_CATEGORY:
        return _SOURCE_CATEGORY[source_tool]
    # Otherwise take the prefix before the first ``:`` (``vol:pslist`` -> ``vol``).
    family, sep, _ = source_tool.partition(":")
    if sep and family in _SOURCE_CATEGORY:
        return _SOURCE_CATEGORY[family]
    return "other"


def classify(records: Iterable[IndexRecord]) -> tuple[CorroborationTier, frozenset[str]]:
    """Return ``(tier, categories)`` for a finding's cited records.

    ``categories`` is the deduplicated set of evidence categories observed; report
    rendering uses it to label the badge (``CONFIRMED · memory+system_log``). An
    empty iterable lands as UNVERIFIED with no categories (a finding with zero
    resolvable cited records is, by definition, unverified)."""
    seen_categories: set[str] = set()
    record_count = 0
    for record in records:
        record_count += 1
        seen_categories.add(categorize(record.source_tool))

    categories = frozenset(seen_categories)
    if len(categories) >= 2:
        return CorroborationTier.CONFIRMED, categories
    if record_count >= 2:
        return CorroborationTier.INFERRED, categories
    return CorroborationTier.UNVERIFIED, categories


__all__ = ["CorroborationTier", "categorize", "classify"]
