"""ID generators and parsers — shared between MCP server, agent, and report.

The audit_id format ``sift-<examiner>-<YYYYMMDD>-<NNN>`` is specified in
architecture.md §4.4 and is the load-bearing primitive that
joins the audit log, the HMAC ledger, the report's inline verify links, and
the citation gate. Centralising the generators here prevents string-template
drift across packages.

Sequence widths:
  - <1000 calls/day → ``NNN`` (3 digits, zero-padded)
  - ≥1000 calls/day → ``NNNN`` (auto-widens; the format stays parseable
    because the suffix is the LAST hyphen-separated token)
"""

from __future__ import annotations

import re
from datetime import date
from typing import NamedTuple


class AuditIdParts(NamedTuple):
    """Parsed audit_id components."""

    examiner: str
    day: date
    seq: int


_NON_ALNUM = re.compile(r"[^a-z0-9]")
# Matches sift-<examiner_slug>-<YYYYMMDD>-<NNN+> with the slug constrained
# to lowercase alnum (since slug_examiner enforces that) and seq capturing
# any non-empty digit run so 1000+ widens cleanly.
_AUDIT_ID_PATTERN = re.compile(r"^sift-([a-z0-9]+)-(\d{8})-(\d+)$")


def slug_examiner(name: str) -> str:
    """Return a stable, lowercase, alnum-only slug for an examiner handle.

    Raises ``ValueError`` if the result would be empty (the slug is part of
    every audit_id and the empty string would corrupt the regex parse).
    """
    if not isinstance(name, str):
        raise TypeError(f"examiner must be str, got {type(name).__name__}")
    slug = _NON_ALNUM.sub("", name.lower())
    if not slug:
        raise ValueError(f"slug_examiner({name!r}) yields empty slug")
    return slug


def _pad(seq: int, width: int = 3) -> str:
    """Zero-pad ``seq`` to at least ``width`` digits; auto-widen for larger.

    Rejects ``bool`` explicitly (Python treats ``True < 0`` as ``False``,
    which would let ``_pad(True)`` slip through with ``"001"``).
    """
    if not isinstance(seq, int) or isinstance(seq, bool):
        raise TypeError(f"sequence must be int (not bool); got {type(seq).__name__}")
    if seq < 0:
        raise ValueError(f"sequence number must be non-negative; got {seq}")
    return str(seq).zfill(width)


def make_finding_id(seq: int) -> str:
    """Return ``F-NNN`` (or ``F-NNNN+`` for seq ≥ 1000)."""
    return f"F-{_pad(seq)}"


def make_timeline_id(seq: int) -> str:
    """Return ``T-NNN`` (or ``T-NNNN+`` for seq ≥ 1000)."""
    return f"T-{_pad(seq)}"


def make_audit_id(examiner: str, day: date, seq: int) -> str:
    """Return ``sift-<slug>-<YYYYMMDD>-<NNN>`` for the given (examiner, day, seq).

    The slug is computed via :func:`slug_examiner` so callers can pass raw
    examiner handles.
    """
    if not isinstance(day, date):
        raise TypeError(f"day must be a date, got {type(day).__name__}")
    return f"sift-{slug_examiner(examiner)}-{day.strftime('%Y%m%d')}-{_pad(seq)}"


def require_audit_id_str(value: object) -> str:
    """BeforeValidator: reject non-str (incl. bytes — Pydantic v2 would
    silently UTF-8-decode; same PR-92 surface :func:`_normalise_hex`
    covers for Sha256Hex)."""
    if not isinstance(value, str):
        raise ValueError(f"AuditId requires str, got {type(value).__name__}")
    return value


def assert_audit_id_format(value: str) -> str:
    """AfterValidator: reject any value that doesn't match
    ``sift-<slug>-<YYYYMMDD>-<NNN>`` (architecture §4.4). Returns the
    input verbatim so byte-exact discipline for the audit log + HMAC
    ledger is preserved. See :func:`parse_audit_id` for the structured-
    parse variant audit-log readers + ledger verification use."""
    parse_audit_id(value)
    return value


def parse_audit_id(audit_id: str) -> AuditIdParts:
    """Parse a ``sift-<slug>-<YYYYMMDD>-<NNN>`` audit_id into its parts.

    Raises ``ValueError`` if the string does not match the canonical format
    or if the date component is not a real calendar date.
    """
    match = _AUDIT_ID_PATTERN.match(audit_id)
    if match is None:
        raise ValueError(f"audit_id {audit_id!r} does not match sift-<slug>-<YYYYMMDD>-<NNN>")
    examiner_slug, ymd, seq_str = match.groups()
    try:
        day = date(int(ymd[0:4]), int(ymd[4:6]), int(ymd[6:8]))
    except ValueError as exc:
        raise ValueError(f"audit_id {audit_id!r} has invalid date {ymd!r}") from exc
    return AuditIdParts(examiner=examiner_slug, day=day, seq=int(seq_str))


__all__ = [
    "AuditIdParts",
    "assert_audit_id_format",
    "make_audit_id",
    "make_finding_id",
    "make_timeline_id",
    "parse_audit_id",
    "require_audit_id_str",
    "slug_examiner",
]
