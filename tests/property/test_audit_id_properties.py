"""Hypothesis property tests for audit_id round-trip invariants.

These properties pin the contract between make_audit_id and parse_audit_id
across the full input space the generators accept. They also catch the
class of bug where slug_examiner is non-idempotent (e.g. double-slugging
produces a different result).
"""

from __future__ import annotations

import string
from datetime import date

from hypothesis import given, strategies as st

from silentwitness_common.ids import make_audit_id, parse_audit_id, slug_examiner

# A real examiner handle has to slug-down to at least one alnum char. We
# generate names that DEFINITELY contain alnum so the slug is non-empty.
_examiner_chars = st.text(
    alphabet=string.ascii_letters + string.digits + " -_.!",
    min_size=1,
    max_size=24,
)
_examiner_names = _examiner_chars.filter(lambda s: any(c.isalnum() for c in s))

# Dates in the supported range — Python's date supports 1 ≤ year ≤ 9999.
_dates = st.dates(min_value=date(2000, 1, 1), max_value=date(2099, 12, 31))

# Sequence numbers within the realistic case range.
_seqs = st.integers(min_value=0, max_value=99_999)


@given(examiner=_examiner_names, day=_dates, seq=_seqs)
def test_round_trip_preserves_examiner_day_seq(examiner: str, day: date, seq: int) -> None:
    """parse_audit_id(make_audit_id(e, d, n)) recovers (slug(e), d, n)."""
    audit_id = make_audit_id(examiner, day, seq)
    parts = parse_audit_id(audit_id)
    assert parts.examiner == slug_examiner(examiner)
    assert parts.day == day
    assert parts.seq == seq


@given(examiner=_examiner_names, day=_dates, seq=_seqs)
def test_make_audit_id_starts_with_sift_prefix(examiner: str, day: date, seq: int) -> None:
    """Every generated audit_id has the architectural ``sift-`` prefix."""
    assert make_audit_id(examiner, day, seq).startswith("sift-")


@given(name=_examiner_names)
def test_slug_examiner_is_idempotent(name: str) -> None:
    """slug_examiner(slug_examiner(x)) == slug_examiner(x) for any valid input."""
    once = slug_examiner(name)
    twice = slug_examiner(once)
    assert once == twice


@given(examiner=_examiner_names, day=_dates, seq_a=_seqs, seq_b=_seqs)
def test_make_audit_id_is_injective_on_seq(
    examiner: str, day: date, seq_a: int, seq_b: int
) -> None:
    """Distinct sequence numbers produce distinct audit_ids for the same (e, d)."""
    if seq_a == seq_b:
        return  # vacuously true
    assert make_audit_id(examiner, day, seq_a) != make_audit_id(examiner, day, seq_b)
