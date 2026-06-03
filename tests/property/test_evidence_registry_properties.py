"""Hypothesis property tests for EvidenceRegistry invariants."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from hypothesis import given, settings, strategies as st

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.evidence.registry import EvidenceRegistry

_AUDIT_ID = "sift-aj-20260613-001"


@given(payload=st.binary(min_size=0, max_size=1 * 1024 * 1024))
@settings(max_examples=15, deadline=None)
def test_register_verify_round_trip(payload: bytes) -> None:
    """For any payload up to 1 MB, register-then-verify always reports
    ``matches=True`` and the recorded SHA-256 equals the stdlib hash."""
    expected = hashlib.sha256(payload).hexdigest()
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        case_dir = root / "case"
        fixture = root / "fix.bin"
        fixture.write_bytes(payload)
        reg = EvidenceRegistry(case_dir=case_dir)
        record = reg.register(
            path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID
        )
        assert record.sha256 == expected
        assert record.size_bytes == len(payload)
        result = reg.verify_hash(fixture)
        assert result.matches is True
        assert result.expected == expected
        assert result.actual == expected


@given(
    payloads=st.lists(
        st.binary(min_size=1, max_size=4096),
        min_size=1,
        max_size=10,
        unique=True,
    )
)
@settings(max_examples=10, deadline=None)
def test_multi_register_list_all_and_assert_are_consistent(payloads: list[bytes]) -> None:
    """For any set of distinct files, every registered path round-trips
    through list_all and assert_registered with no loss or false negatives."""
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        case_dir = root / "case"
        reg = EvidenceRegistry(case_dir=case_dir)
        expected_hashes: dict[Path, str] = {}
        for idx, payload in enumerate(payloads):
            fixture = root / f"fix-{idx}.bin"
            fixture.write_bytes(payload)
            sha = hashlib.sha256(payload).hexdigest()
            expected_hashes[fixture.resolve()] = sha
            reg.register(path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)
        # list_all returns every registered record, no duplicates, no loss
        listed = reg.list_all()
        assert len(listed) == len(payloads)
        listed_by_path = {r.path: r.sha256 for r in listed}
        assert listed_by_path == expected_hashes
        # assert_registered succeeds for every registered path
        for path, sha in expected_hashes.items():
            record = reg.assert_registered(path)
            assert record.sha256 == sha
