"""Unit tests for the dfVFS evidence-access layer.

The image-reading hot path is covered end-to-end (no mocks) in
``tests/integration/evidence/test_access_image.py`` against a real FAT image.
Here we cover the parts that need no disk image: the ``open_image`` safety guard
(a non-image must raise, never enumerate the host), nested-archive
decompression against the real 7-Zip binary, and the pure helpers.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

# dfVFS is the opt-in `forensics` extra (libyal C-extensions; Linux analysis box
# only). Skip the whole module when it is absent rather than failing collection.
pytest.importorskip("dfvfs", reason="forensics extra not installed (uv sync --extra forensics)")

from silentwitness_mcp.evidence import access, artifacts

_HAVE_7Z = any(shutil.which(name) for name in ("7z", "7za", "7zr"))


# --------------------------------------------------------------------------- #
# open_image safety guard — must reject non-images rather than fall back to OS
# --------------------------------------------------------------------------- #


def test_open_image_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(access.EvidenceAccessError, match="not found"):
        access.open_image(tmp_path / "nope.e01")


def test_open_image_random_bytes_raises_not_host_enumeration(tmp_path: Path) -> None:
    """A file that is not a recognised image must raise — dfVFS would otherwise
    fall back to an OS path spec rooted at the host filesystem."""
    junk = tmp_path / "junk.bin"
    junk.write_bytes(os.urandom(100_000))
    with pytest.raises(access.EvidenceAccessError, match="no supported filesystem"):
        access.open_image(junk)


def test_open_image_empty_file_raises(tmp_path: Path) -> None:
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    with pytest.raises(access.EvidenceAccessError):
        access.open_image(empty)


# --------------------------------------------------------------------------- #
# decompress_archive — real 7-Zip, the ROCBA zip -> 7z -> raw nest
# --------------------------------------------------------------------------- #


def _seven_zip() -> str:
    for name in ("7z", "7za", "7zr"):
        found = shutil.which(name)
        if found:
            return found
    raise RuntimeError("no 7z")


@pytest.mark.skipif(not _HAVE_7Z, reason="7-Zip not installed")
def test_decompress_nested_zip_then_7z(tmp_path: Path) -> None:
    """zip(7z(raw)) unwraps to the raw leaf, byte-for-byte."""
    sz = _seven_zip()
    staging = tmp_path / "staging"
    staging.mkdir()
    payload = b"RAW-MEMORY-IMAGE-" + os.urandom(2048)
    raw = staging / "memory.raw"
    raw.write_bytes(payload)
    subprocess.run([sz, "a", "-bso0", "-bsp0", str(staging / "inner.7z"), str(raw)], check=True)
    raw.unlink()
    subprocess.run(
        [sz, "a", "-bso0", "-bsp0", "-tzip", str(staging / "outer.zip"), str(staging / "inner.7z")],
        check=True,
    )

    leaves = access.decompress_archive(staging / "outer.zip", tmp_path / "out")

    assert len(leaves) == 1
    assert Path(leaves[0]).read_bytes() == payload


@pytest.mark.skipif(not _HAVE_7Z, reason="7-Zip not installed")
def test_decompress_plain_zip(tmp_path: Path) -> None:
    sz = _seven_zip()
    payload = b"hello-evidence"
    (tmp_path / "a.txt").write_bytes(payload)
    subprocess.run(
        [sz, "a", "-bso0", "-bsp0", "-tzip", str(tmp_path / "z.zip"), str(tmp_path / "a.txt")],
        check=True,
    )
    leaves = access.decompress_archive(tmp_path / "z.zip", tmp_path / "out")
    assert [Path(p).read_bytes() for p in leaves] == [payload]


def test_resolve_7z_missing_gives_actionable_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no 7-Zip on PATH, decompress raises a clear install hint."""
    monkeypatch.setattr(access.shutil, "which", lambda _name: None)
    with pytest.raises(access.EvidenceAccessError, match="p7zip-full"):
        access.decompress_archive(tmp_path / "whatever.zip", tmp_path / "out")


# --------------------------------------------------------------------------- #
# pure helpers
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("/$MFT", "_MFT"),
        ("/Windows/System32/config/SOFTWARE", "Windows/System32/config/SOFTWARE"),
        ("/$Extend/$UsnJrnl", "_Extend/_UsnJrnl"),
        ("///", "artifact"),
        ("/a/../b", "a/b"),
    ],
)
def test_sanitise_location(location: str, expected: str) -> None:
    assert artifacts._sanitise_location(location) == expected


def test_artifact_targets_cover_rocba_high_value_set() -> None:
    labels = {t.label for t in artifacts.ROCBA_ARTIFACT_TARGETS}
    # The probe-confirmed ROCBA artifacts must all be addressed.
    assert {"mft", "hive_software", "hive_system", "amcache", "srum", "evtx", "ntuser"} <= labels
    # Hives are exact-file lookups; EVTX/Prefetch are directory globs; user hives per-user.
    by_label = {t.label: t for t in artifacts.ROCBA_ARTIFACT_TARGETS}
    assert by_label["hive_software"].kind == "file"
    assert by_label["evtx"].kind == "dir_glob"
    assert by_label["ntuser"].kind == "per_user"
