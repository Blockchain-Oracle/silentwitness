"""Round-2 review-fix tests for evidence registry (split from main file for
the 400-LOC cap). Covers wrapped manifest read errors, missing-on-disk,
fstat cross-check, hardlink resolution, schema-version, concurrent register
under fcntl.flock, direct Pydantic validation, and malformed-record index.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from silentwitness_common.types import EvidenceRecord, EvidenceType
from silentwitness_mcp.evidence.registry import (
    EvidenceContentDriftError,
    EvidenceMissingOnDiskError,
    EvidenceRegistry,
    EvidenceRegistryError,
)

_AUDIT_ID = "sift-aj-20260613-001"


def _write_fixture(path: Path, payload: bytes = b"hello world\n") -> str:
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Round-2 review fixes — wrapped manifest errors, missing-on-disk, fstat,
# hardlinks, schema version, concurrent register
# ---------------------------------------------------------------------------


def test_load_unicode_decode_error_wraps_to_registry_error(tmp_path: Path) -> None:
    """Non-UTF-8 bytes in the manifest must wrap as EvidenceRegistryError."""
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "evidence.json").write_bytes(b"\xff\xfe not utf-8")
    reg = EvidenceRegistry(case_dir=case_dir)
    with pytest.raises(EvidenceRegistryError, match="unreadable or malformed") as excinfo:
        reg.list_all()
    assert isinstance(excinfo.value.__cause__, UnicodeDecodeError)


def test_load_unreadable_manifest_wraps_to_registry_error(tmp_path: Path) -> None:
    """PermissionError on manifest open must wrap as EvidenceRegistryError."""
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    target = case_dir / "evidence.json"
    target.write_text(json.dumps({"schema_version": 1, "records": []}), encoding="utf-8")
    target.chmod(0o000)
    reg = EvidenceRegistry(case_dir=case_dir)
    try:
        with pytest.raises(EvidenceRegistryError, match="unreadable or malformed"):
            reg.list_all()
    finally:
        target.chmod(0o644)


def test_load_manifest_wrong_schema_version_raises(tmp_path: Path) -> None:
    """A future-version manifest must NOT silently slip through an older codebase."""
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "evidence.json").write_text(
        json.dumps({"schema_version": 2, "records": []}), encoding="utf-8"
    )
    reg = EvidenceRegistry(case_dir=case_dir)
    with pytest.raises(EvidenceRegistryError, match="schema_version=2"):
        reg.list_all()


def test_assert_registered_raises_missing_on_deleted_file(tmp_path: Path) -> None:
    """Registered-then-deleted must surface as EvidenceMissingOnDiskError,
    NOT as EvidenceNotRegisteredError — the analyst-debugging journey is
    different (re-mount vs forgot-to-register)."""
    case_dir = tmp_path / "case"
    fixture = tmp_path / "fix.bin"
    _write_fixture(fixture)
    reg = EvidenceRegistry(case_dir=case_dir)
    record = reg.register(path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)
    fixture.unlink()
    with pytest.raises(EvidenceMissingOnDiskError) as excinfo:
        reg.assert_registered(fixture)
    assert excinfo.value.path == record.path


def test_verify_hash_on_deleted_file_raises_missing(tmp_path: Path) -> None:
    """verify_hash on a registered-but-gone file must raise the missing-on-disk
    error uniformly with assert_registered — no raw FileNotFoundError leak."""
    case_dir = tmp_path / "case"
    fixture = tmp_path / "fix.bin"
    _write_fixture(fixture)
    reg = EvidenceRegistry(case_dir=case_dir)
    reg.register(path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)
    fixture.unlink()
    with pytest.raises(EvidenceMissingOnDiskError):
        reg.verify_hash(fixture)


@pytest.mark.parametrize(
    "payload",
    [b"", b"x", b"\x00" * 8192, b"\xff" * 8193, b"hello" * 2000],
    ids=["empty", "one-byte", "exact-chunk", "chunk+1", "middle"],
)
def test_hash_and_size_chunk_boundary_correctness(tmp_path: Path, payload: bytes) -> None:
    """Chunk-boundary correctness: SHA-256 + size must match stdlib for any
    payload including 0 bytes, exact 8 KB chunks, and chunk+1."""
    case_dir = tmp_path / "case"
    fixture = tmp_path / "fix.bin"
    fixture.write_bytes(payload)
    reg = EvidenceRegistry(case_dir=case_dir)
    record = reg.register(path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)
    assert record.sha256 == hashlib.sha256(payload).hexdigest()
    assert record.size_bytes == len(payload)


def test_hardlink_resolves_to_same_record(tmp_path: Path) -> None:
    """Two distinct path strings pointing to the same inode (hardlink) must
    resolve to the same record via Path.samefile() — portable across
    case-sensitive filesystems where normcase wouldn't help."""
    case_dir = tmp_path / "case"
    real = tmp_path / "real.bin"
    _write_fixture(real)
    link = tmp_path / "hardlink.bin"
    os.link(real, link)
    reg = EvidenceRegistry(case_dir=case_dir)
    reg.register(path=real, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)
    looked_up = reg.assert_registered(link)
    assert looked_up.path == real.resolve()


def test_evidence_content_drift_error_has_reason_attribute(tmp_path: Path) -> None:
    """The rename from AlreadyRegisteredError to EvidenceContentDriftError
    preserves the .reason attribute downstream consumers rely on."""
    case_dir = tmp_path / "case"
    fixture = tmp_path / "fix.bin"
    _write_fixture(fixture, b"original\n")
    reg = EvidenceRegistry(case_dir=case_dir)
    reg.register(path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)
    fixture.write_bytes(b"drifted\n")
    with pytest.raises(EvidenceContentDriftError) as excinfo:
        reg.register(
            path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id="sift-aj-20260613-002"
        )
    assert excinfo.value.reason == "sha256_mismatch_on_reregister"


def test_concurrent_register_with_flock_loses_no_records(tmp_path: Path) -> None:
    """20 threads each register a distinct file. With fcntl.flock around the
    read-modify-write, all 20 records must persist — no lost updates."""
    case_dir = tmp_path / "case"
    fixtures = [tmp_path / f"fix-{i}.bin" for i in range(20)]
    for i, fix in enumerate(fixtures):
        fix.write_bytes(f"content-{i}\n".encode())
    reg = EvidenceRegistry(case_dir=case_dir)

    errors: list[Exception] = []

    def worker(target: Path) -> None:
        try:
            reg.register(path=target, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)
        except Exception as exc:  # pragma: no cover — we want zero errors
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(f,)) for f in fixtures]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    listed = reg.list_all()
    assert len(listed) == 20
    paths_seen = {r.path for r in listed}
    assert paths_seen == {f.resolve() for f in fixtures}


def test_concurrent_register_across_processes_lock_is_exclusive(tmp_path: Path) -> None:
    """The flock must be cross-process (LOCK_EX, not LOCK_SH). Verified by
    holding the lock externally and ensuring register() blocks then succeeds
    after release."""
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    fixture = tmp_path / "fix.bin"
    _write_fixture(fixture)
    lock_path = case_dir / ".evidence.lock"
    lock_path.touch()

    # External lock holder.
    external = lock_path.open("ab")
    fcntl.flock(external.fileno(), fcntl.LOCK_EX)

    reg = EvidenceRegistry(case_dir=case_dir)
    register_done = threading.Event()

    def registerer() -> None:
        reg.register(path=fixture, evidence_type=EvidenceType.DISK_IMAGE, audit_id=_AUDIT_ID)
        register_done.set()

    thread = threading.Thread(target=registerer)
    thread.start()
    # Verify register is blocked while the external lock is held.
    time.sleep(0.2)
    assert not register_done.is_set(), "register should block while external flock is held"

    fcntl.flock(external.fileno(), fcntl.LOCK_UN)
    external.close()
    thread.join(timeout=5.0)
    assert register_done.is_set(), "register should complete after lock is released"
    assert len(reg.list_all()) == 1


def test_evidence_record_validation_rejects_bad_inputs() -> None:
    """Direct construction with invalid inputs must raise ValidationError —
    not silently slip through via the manifest round-trip."""
    from pydantic import ValidationError as _ValidationError

    valid_sha = "a" * 64
    valid_args = {
        "type": EvidenceType.DISK_IMAGE,
        "size_bytes": 0,
        "registered_at": datetime(2026, 6, 13, tzinfo=UTC),
        "registered_audit_id": "sift-aj-20260613-001",
    }
    # Bad sha256: too short
    with pytest.raises(_ValidationError):
        EvidenceRecord(path=Path("/x"), sha256="a" * 63, **valid_args)  # type: ignore[arg-type]
    # Bad sha256: uppercase normalises but contains non-hex
    with pytest.raises(_ValidationError):
        EvidenceRecord(path=Path("/x"), sha256="g" * 64, **valid_args)  # type: ignore[arg-type]
    # Bad size: negative
    bad_size_args = dict(valid_args)
    bad_size_args["size_bytes"] = -1
    with pytest.raises(_ValidationError):
        EvidenceRecord(path=Path("/x"), sha256=valid_sha, **bad_size_args)  # type: ignore[arg-type]
    # Bad audit_id: empty
    bad_audit_args = dict(valid_args)
    bad_audit_args["registered_audit_id"] = ""
    with pytest.raises(_ValidationError):
        EvidenceRecord(path=Path("/x"), sha256=valid_sha, **bad_audit_args)  # type: ignore[arg-type]


def test_malformed_record_in_list_all_reports_index(tmp_path: Path) -> None:
    """A single malformed record must raise with its index for human triage."""
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "evidence.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "records": [
                    {
                        "path": "/x",
                        "type": "disk_image",
                        "sha256": "a" * 64,
                        "size_bytes": 0,
                        "registered_at": "2026-06-13T00:00:00Z",
                        "registered_audit_id": "sift-aj-20260613-001",
                    },
                    {"path": "/y", "sha256": "nope"},  # malformed
                ],
            }
        ),
        encoding="utf-8",
    )
    reg = EvidenceRegistry(case_dir=case_dir)
    with pytest.raises(EvidenceRegistryError, match="record #1"):
        reg.list_all()
