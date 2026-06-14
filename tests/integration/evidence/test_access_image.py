"""End-to-end test of dfVFS evidence access against a real filesystem image.

We build a small FAT image with ``mkfs.vfat`` + ``mtools`` (no root / no loop
mount needed) populated with a ROCBA-shaped artifact layout, then drive
``open_image`` / ``extract_artifacts`` / ``read_file`` for real — no mocks on the
hot path (CLAUDE.md non-negotiable). FAT exercises the same dfVFS
VolumeScanner -> FileSystem -> path-spec-lookup code path as the NTFS ROCBA E01;
the partition-less FAT image mirrors ROCBA's offset-0 (no partition table) shape.

Skipped when the image-building tools are absent (CI runners without
dosfstools/mtools).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

# dfVFS is the opt-in `forensics` extra (libyal C-extensions; Linux analysis box
# only). Skip the whole module when it is absent rather than failing collection.
pytest.importorskip("dfvfs", reason="forensics extra not installed (uv sync --extra forensics)")

from silentwitness_mcp.evidence import access

_TOOLS = ("dd", "mkfs.vfat", "mmd", "mcopy")
_HAVE_TOOLS = all(shutil.which(t) for t in _TOOLS)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _HAVE_TOOLS, reason=f"need {_TOOLS} to build a FAT fixture"),
]


def _build_fat_image(img: Path, files: dict[str, bytes]) -> None:
    """Create a 64 MiB FAT32 image at ``img`` containing ``files`` (path -> bytes)."""
    subprocess.run(
        ["dd", "if=/dev/zero", f"of={img}", "bs=1M", "count=64", "status=none"], check=True
    )
    subprocess.run(["mkfs.vfat", "-F", "32", str(img)], check=True, capture_output=True)
    # Parent dirs first: sort by path depth.
    dirs: set[str] = set()
    for path in files:
        parts = path.split("/")
        for i in range(1, len(parts)):
            dirs.add("/".join(parts[:i]))
    for d in sorted(dirs, key=lambda p: p.count("/")):
        subprocess.run(["mmd", "-i", str(img), f"::{d}"], check=True, capture_output=True)
    for path, content in files.items():
        src = img.parent / ("src_" + path.replace("/", "_"))
        src.write_bytes(content)
        subprocess.run(
            ["mcopy", "-i", str(img), str(src), f"::{path}"], check=True, capture_output=True
        )


@pytest.fixture
def rocba_shaped_image(tmp_path: Path) -> Path:
    img = tmp_path / "disk.img"
    _build_fat_image(
        img,
        {
            "Windows/System32/config/SOFTWARE": b"LIVE-SOFTWARE-HIVE",
            "Windows/System32/config/SYSTEM": b"LIVE-SYSTEM-HIVE",
            "Windows/System32/winevt/Logs/Security.evtx": b"SECURITY-EVTX",
            "Windows/System32/winevt/Logs/System.evtx": b"SYSTEM-EVTX",
            "Windows/Prefetch/EDGE.EXE-ABCD1234.pf": b"PREFETCH",
            "Users/fredr/NTUSER.DAT": b"FREDR-NTUSER",
            "Users/srl-h/NTUSER.DAT": b"SRLH-NTUSER",
            # A Windows.old duplicate that must NOT be extracted.
            "Windows.old/Windows/System32/config/SOFTWARE": b"OLD-SOFTWARE-HIVE",
        },
    )
    return img


def test_open_image_resolves_partitionless_volume(rocba_shaped_image: Path) -> None:
    opened = access.open_image(rocba_shaped_image)
    assert opened.base_path_specs  # exactly the offset-0 filesystem
    assert access.location_exists(opened, "/Windows/System32/config/SOFTWARE")
    assert not access.location_exists(opened, "/Windows/System32/config/NOPE")


def test_read_file_returns_exact_bytes(rocba_shaped_image: Path) -> None:
    opened = access.open_image(rocba_shaped_image)
    assert access.read_file(opened, "/Windows/System32/config/SOFTWARE") == b"LIVE-SOFTWARE-HIVE"
    with pytest.raises(access.EvidenceAccessError):
        access.read_file(opened, "/does/not/exist")


def test_extract_artifacts_files_globs_and_per_user(
    rocba_shaped_image: Path, tmp_path: Path
) -> None:
    opened = access.open_image(rocba_shaped_image)
    out = tmp_path / "prepared"
    results = access.extract_artifacts(opened, out)

    by_label: dict[str, list[access.ExtractedArtifact]] = {}
    for r in results:
        by_label.setdefault(r.label, []).append(r)

    # Exact-file hive.
    assert len(by_label["hive_software"]) == 1
    assert Path(by_label["hive_software"][0].output_path).read_bytes() == b"LIVE-SOFTWARE-HIVE"

    # dir_glob: both EVTX files, only .evtx.
    assert {Path(r.output_path).read_bytes() for r in by_label["evtx"]} == {
        b"SECURITY-EVTX",
        b"SYSTEM-EVTX",
    }

    # dir_glob: prefetch .pf.
    assert len(by_label["prefetch"]) == 1

    # per_user: one NTUSER.DAT per profile.
    assert {r.source_location for r in by_label["ntuser"]} == {
        "/Users/fredr/NTUSER.DAT",
        "/Users/srl-h/NTUSER.DAT",
    }


def test_extract_artifacts_skips_windows_old_duplicate(
    rocba_shaped_image: Path, tmp_path: Path
) -> None:
    """The live /Windows hive is taken; the Windows.old duplicate is never read."""
    opened = access.open_image(rocba_shaped_image)
    results = access.extract_artifacts(opened, tmp_path / "out")
    software = [r for r in results if r.label == "hive_software"]
    assert len(software) == 1
    assert all("windows.old" not in r.source_location.lower() for r in software)
    assert Path(software[0].output_path).read_bytes() == b"LIVE-SOFTWARE-HIVE"


def test_extract_artifacts_absent_targets_are_skipped(
    rocba_shaped_image: Path, tmp_path: Path
) -> None:
    """SRUM / Amcache absent from this fixture → simply not in the results."""
    opened = access.open_image(rocba_shaped_image)
    labels = {r.label for r in access.extract_artifacts(opened, tmp_path / "out")}
    assert "srum" not in labels
    assert "amcache" not in labels
    assert "hive_software" in labels
