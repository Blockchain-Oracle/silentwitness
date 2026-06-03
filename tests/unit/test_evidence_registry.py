"""Behavioural tests for src/silentwitness_mcp/evidence/registry.py.

Real filesystem (tmp_path), real Pydantic models — no mocks per
architecture §14. Time is dependency-injected through the optional ``now=``
kwarg so the list-ordering test is deterministic.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.evidence.registry import (
    AlreadyRegisteredError,
    EvidenceNotRegisteredError,
    EvidenceRegistry,
    EvidenceRegistryError,
)

_AUDIT_ID = "sift-aj-20260613-001"
_FIXED_NOW = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)


def _write_fixture(path: Path, payload: bytes = b"hello world\n") -> str:
    """Create a fixture file and return its expected SHA-256 hex digest."""
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# register() — basic shape + manifest persistence
# ---------------------------------------------------------------------------


def test_register_produces_correct_sha256_and_manifest(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-xyz"
    fixture = tmp_path / "fixture.bin"
    expected_sha = _write_fixture(fixture, b"the quick brown fox\n")
    expected_size = fixture.stat().st_size

    reg = EvidenceRegistry(case_dir=case_dir)
    record = reg.register(
        path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID, now=_FIXED_NOW
    )

    assert record.sha256 == expected_sha
    assert record.size_bytes == expected_size
    assert record.type == EvidenceType.DISK_IMAGE
    assert record.registered_audit_id == _AUDIT_ID
    assert record.registered_at == _FIXED_NOW
    # Path stored is resolved (canonical)
    assert record.path == fixture.resolve()

    # Manifest on disk contains exactly the one record
    manifest_path = case_dir / "evidence.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert len(manifest["records"]) == 1
    assert manifest["records"][0]["sha256"] == expected_sha


def test_manifest_is_mode_0644(tmp_path: Path) -> None:
    """The manifest is not a secret — owner-write, world-read."""
    case_dir = tmp_path / "case"
    fixture = tmp_path / "fix.bin"
    _write_fixture(fixture)
    reg = EvidenceRegistry(case_dir=case_dir)
    reg.register(path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)
    mode = os.stat(case_dir / "evidence.json").st_mode & 0o777
    assert mode == 0o644, f"expected 0644, got 0o{mode:o}"


# ---------------------------------------------------------------------------
# register() — idempotency + corruption detection
# ---------------------------------------------------------------------------


def test_double_register_same_content_returns_existing(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    fixture = tmp_path / "fix.bin"
    _write_fixture(fixture)
    reg = EvidenceRegistry(case_dir=case_dir)

    first = reg.register(
        path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID, now=_FIXED_NOW
    )
    second = reg.register(
        path=fixture,
        evidence_type=EvidenceType.DISK_IMAGE,
        audit_id="sift-aj-20260613-002",
        now=datetime(2026, 6, 14, 0, 0, tzinfo=UTC),
    )

    assert first == second
    # The manifest still has exactly one record
    manifest = json.loads((case_dir / "evidence.json").read_text(encoding="utf-8"))
    assert len(manifest["records"]) == 1


def test_double_register_different_content_raises(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    fixture = tmp_path / "fix.bin"
    _write_fixture(fixture, b"original content\n")
    reg = EvidenceRegistry(case_dir=case_dir)
    reg.register(path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)

    fixture.write_bytes(b"tampered content\n")
    with pytest.raises(AlreadyRegisteredError) as excinfo:
        reg.register(
            path=fixture,
            evidence_type=EvidenceType.DISK_IMAGE,
            audit_id="sift-aj-20260613-002",
        )
    assert excinfo.value.reason == "sha256_mismatch_on_reregister"
    assert excinfo.value.path == fixture.resolve()


# ---------------------------------------------------------------------------
# assert_registered() — the gate
# ---------------------------------------------------------------------------


def test_assert_registered_raises_on_unknown_path(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    reg = EvidenceRegistry(case_dir=case_dir)
    bogus = Path("/evidence/not-here.E01")
    with pytest.raises(EvidenceNotRegisteredError) as excinfo:
        reg.assert_registered(bogus)
    assert "not-here.E01" in str(excinfo.value)


def test_assert_registered_succeeds_on_registered_path(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    fixture = tmp_path / "fix.bin"
    _write_fixture(fixture)
    reg = EvidenceRegistry(case_dir=case_dir)
    record = reg.register(path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)
    looked_up = reg.assert_registered(fixture)
    assert looked_up == record


def test_assert_registered_follows_symlinks(tmp_path: Path) -> None:
    """Symlink-to-registered must succeed — the gate canonicalises first."""
    case_dir = tmp_path / "case"
    real = tmp_path / "real.bin"
    _write_fixture(real)
    reg = EvidenceRegistry(case_dir=case_dir)
    reg.register(path=real, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)
    link = tmp_path / "link.bin"
    link.symlink_to(real)
    looked_up = reg.assert_registered(link)
    assert looked_up.path == real.resolve()


# ---------------------------------------------------------------------------
# verify_hash() — bit-rot detector
# ---------------------------------------------------------------------------


def test_verify_hash_detects_bit_rot(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    fixture = tmp_path / "fix.bin"
    expected_sha = _write_fixture(fixture, b"original\n")
    reg = EvidenceRegistry(case_dir=case_dir)
    reg.register(path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)

    fixture.write_bytes(b"corrupted!\n")
    result = reg.verify_hash(fixture)
    assert result.matches is False
    assert result.expected == expected_sha
    assert result.actual != expected_sha


def test_verify_hash_returns_match_on_intact_file(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    fixture = tmp_path / "fix.bin"
    expected_sha = _write_fixture(fixture)
    reg = EvidenceRegistry(case_dir=case_dir)
    reg.register(path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)
    result = reg.verify_hash(fixture)
    assert result.matches is True
    assert result.expected == expected_sha
    assert result.actual == expected_sha


# ---------------------------------------------------------------------------
# list_all()
# ---------------------------------------------------------------------------


def test_list_all_returns_records_sorted_by_registered_at(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    fixtures = [tmp_path / f"f{i}.bin" for i in range(3)]
    for i, fix in enumerate(fixtures):
        _write_fixture(fix, payload=f"payload-{i}".encode())
    reg = EvidenceRegistry(case_dir=case_dir)
    # Register out of chronological order
    reg.register(
        path=fixtures[2],
        evidence_type=EvidenceType.DISK_IMAGE,
        audit_id=_AUDIT_ID,
        now=datetime(2026, 6, 13, 10, 0, tzinfo=UTC),
    )
    reg.register(
        path=fixtures[0],
        evidence_type=EvidenceType.DISK_IMAGE,
        audit_id=_AUDIT_ID,
        now=datetime(2026, 6, 13, 8, 0, tzinfo=UTC),
    )
    reg.register(
        path=fixtures[1],
        evidence_type=EvidenceType.DISK_IMAGE,
        audit_id=_AUDIT_ID,
        now=datetime(2026, 6, 13, 9, 0, tzinfo=UTC),
    )
    records = reg.list_all()
    expected_order = [fixtures[0].resolve(), fixtures[1].resolve(), fixtures[2].resolve()]
    assert [r.path for r in records] == expected_order


# ---------------------------------------------------------------------------
# Atomicity — manifest write is crash-safe
# ---------------------------------------------------------------------------


def test_register_atomic_write_preserves_prior_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If write_json_atomic raises mid-write the prior manifest is untouched."""
    case_dir = tmp_path / "case"
    first_fix = tmp_path / "first.bin"
    second_fix = tmp_path / "second.bin"
    _write_fixture(first_fix, b"first\n")
    _write_fixture(second_fix, b"second\n")
    reg = EvidenceRegistry(case_dir=case_dir)
    reg.register(path=first_fix, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)
    prior_manifest = (case_dir / "evidence.json").read_text(encoding="utf-8")

    from silentwitness_mcp.evidence import registry as registry_mod

    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated disk-full")

    monkeypatch.setattr(registry_mod, "write_json_atomic", boom)
    with pytest.raises(OSError, match="simulated"):
        reg.register(
            path=second_fix, evidence_type=EvidenceType.DISK_IMAGE, audit_id="sift-aj-20260613-002"
        )
    # Prior manifest is byte-identical
    assert (case_dir / "evidence.json").read_text(encoding="utf-8") == prior_manifest


# ---------------------------------------------------------------------------
# Manifest corruption handling
# ---------------------------------------------------------------------------


def test_load_malformed_manifest_raises(tmp_path: Path) -> None:
    """A corrupt manifest must NOT silently masquerade as 'no evidence yet'."""
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "evidence.json").write_text("not even close to json", encoding="utf-8")
    reg = EvidenceRegistry(case_dir=case_dir)
    with pytest.raises(json.JSONDecodeError):
        reg.list_all()


def test_load_manifest_wrong_shape_raises(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "evidence.json").write_text(json.dumps({"oops": []}), encoding="utf-8")
    reg = EvidenceRegistry(case_dir=case_dir)
    with pytest.raises(EvidenceRegistryError, match="missing 'records'"):
        reg.list_all()


# ---------------------------------------------------------------------------
# Concurrency — thread safety isn't promised, but per-instance reads are OK
# ---------------------------------------------------------------------------


def test_concurrent_assert_registered_is_safe(tmp_path: Path) -> None:
    """Concurrent assert_registered reads must not race or corrupt state."""
    case_dir = tmp_path / "case"
    fixture = tmp_path / "fix.bin"
    _write_fixture(fixture)
    reg = EvidenceRegistry(case_dir=case_dir)
    reg.register(path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)

    errors: list[Exception] = []

    def worker() -> None:
        try:
            reg.assert_registered(fixture)
        except Exception as exc:  # pragma: no cover — we want no errors here
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []


# ---------------------------------------------------------------------------
# Case-insensitive lookup (filesystem-quirk defence-in-depth via normcase)
# ---------------------------------------------------------------------------


def test_case_insensitive_lookup_on_case_insensitive_filesystem(tmp_path: Path) -> None:
    """Self-skip if the test filesystem is case-sensitive (most linux + APFS
    default). Where the filesystem DOES alias ``Fix.bin`` to ``fix.bin``,
    ``assert_registered`` must reach the registered record either way —
    backed by :func:`os.path.normcase` over the resolved path."""
    case_dir = tmp_path / "case"
    fixture = tmp_path / "fix.bin"
    _write_fixture(fixture)
    alias = tmp_path / "FIX.bin"
    if not alias.exists():
        pytest.skip("test filesystem is case-sensitive; quirk does not apply here")
    reg = EvidenceRegistry(case_dir=case_dir)
    reg.register(path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)
    looked_up = reg.assert_registered(alias)
    assert looked_up.sha256 == hashlib.sha256(b"hello world\n").hexdigest()
