"""Behavioural tests for src/silentwitness_common/ids.py.

Each test maps to a BDD criterion in story-common-types.md.
"""

from __future__ import annotations

from datetime import date

import pytest

from silentwitness_common.ids import (
    AuditIdParts,
    make_audit_id,
    make_finding_id,
    make_timeline_id,
    parse_audit_id,
    slug_examiner,
)


def test_make_audit_id_canonical_form() -> None:
    assert make_audit_id("ajweb3", date(2026, 6, 13), 7) == "sift-ajweb3-20260613-007"


def test_parse_audit_id_roundtrips() -> None:
    parts = parse_audit_id("sift-ajweb3-20260613-007")
    assert parts == AuditIdParts(examiner="ajweb3", day=date(2026, 6, 13), seq=7)


def test_make_finding_id_zero_pads_to_three_digits() -> None:
    assert make_finding_id(1) == "F-001"
    assert make_finding_id(42) == "F-042"
    assert make_finding_id(999) == "F-999"


def test_make_timeline_id_zero_pads_to_three_digits() -> None:
    assert make_timeline_id(42) == "T-042"


def test_slug_examiner_strips_punctuation_and_lowercases() -> None:
    assert slug_examiner("AJ Web3!") == "ajweb3"
    assert slug_examiner("aj-web3") == "ajweb3"
    assert slug_examiner("Alice") == "alice"


def test_slug_examiner_raises_on_empty_result() -> None:
    """A handle composed only of punctuation yields an empty slug — refuse loud."""
    with pytest.raises(ValueError):
        slug_examiner("!!!")
    with pytest.raises(ValueError):
        slug_examiner("")


def test_sequence_above_999_widens_cleanly() -> None:
    """≥1000 calls/day must auto-widen rather than truncate."""
    assert make_finding_id(1000) == "F-1000"
    assert make_timeline_id(42_424) == "T-42424"
    audit_id = make_audit_id("aj", date(2026, 6, 13), 4242)
    assert audit_id == "sift-aj-20260613-4242"
    parts = parse_audit_id(audit_id)
    assert parts.seq == 4242


def test_parse_audit_id_rejects_malformed_inputs() -> None:
    with pytest.raises(ValueError):
        parse_audit_id("not-a-real-id")
    with pytest.raises(ValueError):
        parse_audit_id("sift-aj-20260699-007")  # invalid date (no day 99)
