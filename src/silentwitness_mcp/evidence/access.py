"""dfVFS-backed evidence access — open an E01/raw image and extract artifacts.

Phase-0 evidence-access layer (plan: ``story-evidence-access``). It replaces the
prior assumption that tools receive an already-extracted ``$MFT`` / hive. The
real judged case (ROCBA) is a 24 GB E01 (87 GB uncompressed) whose disk image
has **no partition table** — the NTFS filesystem sits at offset 0.

We build the dfVFS path spec by hand (OS [-> EWF] -> TSK filesystem) and read via
libtsk, which serves both the partition-less case (ROCBA, NTFS at offset 0) and
partitioned images (e.g. the NIST XP E01 with NTFS at sector 63). We do NOT use
dfVFS's ``VolumeScanner``: on real Windows images it probes the Volume Shadow
Copy volume system (libvshadow), which reads a backup NTFS header past the media
end and crashes the entire scan (observed on the 87 GB ROCBA NTFS). Going
straight to TSK skips VSS while still resolving every partition.

We address artifacts by **exact location** (direct path-spec lookup) or by
listing a single known directory, rather than walking the whole tree: an 87 GB
NTFS volume has hundreds of thousands of entries, and a per-target full walk
would blow the "extraction is minutes" budget. Using explicit live ``/Windows``
paths also sidesteps the ROCBA ``Windows.old`` duplicate hive set for free.

Safety: we only keep a filesystem spec whose TSK filesystem actually opens, so a
non-image source produces an empty list (-> ``EvidenceAccessError``) rather than
enumerating the *host* filesystem.

This module is pure evidence mechanics. Audit provenance + evidence-registry
recording are the caller's job (``cli_commands/prepare.py``) so the access layer
stays unit-testable in isolation.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dfvfs.lib import definitions as dfvfs_definitions, errors as dfvfs_errors
from dfvfs.path import factory as path_spec_factory
from dfvfs.resolver import resolver
from dfvfs.volume import tsk_volume_system

# Read window for in-process file copies — bounds peak memory on a multi-GB
# artifact ($MFT on a large NTFS volume can be hundreds of MB).
_COPY_CHUNK_BYTES = 4 * 1024 * 1024

# Archive suffixes we recursively unwrap. ROCBA memory is a zip -> 7z -> raw nest.
_ARCHIVE_SUFFIXES = frozenset({".zip", ".7z", ".gz", ".tar", ".tgz", ".bz2", ".xz"})
# Bound on nested-archive recursion so a zip-bomb / cycle can't loop forever.
_MAX_ARCHIVE_DEPTH = 4

# EnCase/EWF image suffixes — these get an EWF storage-media layer; everything
# else (dd/raw/img/001) is read as a raw storage-media file.
_EWF_SUFFIXES: frozenset[str] = frozenset({".e01", ".ex01", ".s01"})


class EvidenceAccessError(Exception):
    """Raised when an image cannot be opened or extraction fails."""


@dataclass
class OpenedImage:
    """A scanned source image plus the filesystem base path specs dfVFS found.

    ROCBA yields one base spec (the offset-0 NTFS volume); partitioned images
    yield one per filesystem. Lookups try every base spec so multi-partition
    cases work unchanged."""

    source_path: Path
    # dfVFS path-spec objects (untyped third-party lib) — Any by necessity.
    base_path_specs: list[Any] = field(default_factory=list)


def _storage_media_spec(path: Path) -> Any:
    """Build the storage-media path spec: OS, wrapped in EWF for E01 images.

    We deliberately do NOT use dfVFS's ``VolumeScanner``: on real Windows images
    it probes the Volume Shadow Copy (VSS/libvshadow) volume system, which reads
    a backup NTFS header past the media end and crashes the whole scan
    (observed on the ROCBA 87 GB NTFS). Building the spec by hand and reading via
    TSK (libtsk) skips VSS entirely while still serving partitioned and
    partition-less images alike."""
    os_spec = path_spec_factory.Factory.NewPathSpec(
        dfvfs_definitions.TYPE_INDICATOR_OS, location=str(path)
    )
    if path.suffix.lower() in _EWF_SUFFIXES:
        return path_spec_factory.Factory.NewPathSpec(
            dfvfs_definitions.TYPE_INDICATOR_EWF, parent=os_spec
        )
    return os_spec


# (type_indicator, root_location) tried per parent, in order. libfsntfs (NTFS)
# is preferred: it decodes NTFS-compressed files (Security.evtx, Prefetch) that
# TSK's LZNT1 decompressor crashes on. TSK is the fallback for non-NTFS (e.g.
# FAT). NTFS uses backslash locations, TSK forward-slash — see _to_spec_location.
_FS_BACKENDS: tuple[tuple[str, str], ...] = (
    (dfvfs_definitions.TYPE_INDICATOR_NTFS, "\\"),
    (dfvfs_definitions.TYPE_INDICATOR_TSK, "/"),
)


def _candidate_parents(storage_spec: Any) -> list[Any]:
    """Return the parent spec for each filesystem in the image.

    Uses the TSK partition table (libtsk ``mmls``): one parent per partition, or
    the storage media itself when there is no partition table (ROCBA: NTFS at
    offset 0)."""
    part_spec = path_spec_factory.Factory.NewPathSpec(
        dfvfs_definitions.TYPE_INDICATOR_TSK_PARTITION, location="/", parent=storage_spec
    )
    volume_system = tsk_volume_system.TSKVolumeSystem()
    try:
        volume_system.Open(part_spec)
        parents = [
            path_spec_factory.Factory.NewPathSpec(
                dfvfs_definitions.TYPE_INDICATOR_TSK_PARTITION,
                location=f"/{volume.identifier}",
                parent=storage_spec,
            )
            for volume in volume_system.volumes
        ]
    except dfvfs_errors.Error:
        parents = []
    return parents or [storage_spec]


def _filesystem_specs(storage_spec: Any) -> list[Any]:
    """Return one filesystem path spec per filesystem in the image.

    For each parent (partition or offset-0 media) the NTFS then TSK backend is
    tried; the first whose filesystem opens wins. Only opened specs are kept, so
    junk input yields an empty list rather than enumerating the host."""
    opened: list[Any] = []
    for parent in _candidate_parents(storage_spec):
        for type_indicator, root in _FS_BACKENDS:
            spec = path_spec_factory.Factory.NewPathSpec(
                type_indicator, location=root, parent=parent
            )
            try:
                file_system = resolver.Resolver.OpenFileSystem(spec)
            except dfvfs_errors.Error:
                continue
            if file_system is not None:
                opened.append(spec)
                break  # one filesystem per parent; NTFS preferred over TSK
    return opened


def _to_spec_location(type_indicator: str, location: str) -> str:
    """Convert a canonical ``/``-rooted location to the backend's convention.

    libfsntfs addresses files with backslashes (``\\Windows\\...``); TSK uses
    forward slashes. Targets and traversal speak canonical ``/`` everywhere;
    conversion happens only at the dfVFS path-spec boundary."""
    if type_indicator != dfvfs_definitions.TYPE_INDICATOR_NTFS:
        return location
    inner = location.strip("/")
    return "\\" + inner.replace("/", "\\") if inner else "\\"


def open_image(path: Path) -> OpenedImage:
    """Open ``path`` (E01/raw/dd) and return its TSK filesystem base path specs.

    Builds the path spec by hand (OS [-> EWF] -> TSK) and reads via libtsk,
    bypassing dfVFS's VolumeScanner so the Volume Shadow Copy probe that crashes
    on real Windows images is never run. A partition-less image resolves to its
    filesystem at offset 0; a partitioned image to each partition's filesystem.
    Raises :class:`EvidenceAccessError` if no filesystem opens."""
    if not path.is_file():
        raise EvidenceAccessError(f"evidence image not found: {path}")
    specs = _filesystem_specs(_storage_media_spec(path))
    if not specs:
        raise EvidenceAccessError(
            f"no supported filesystem found in {path} "
            "(unsupported container, empty image, or unrecognised source)"
        )
    return OpenedImage(source_path=path, base_path_specs=specs)


def _open_location(opened: OpenedImage, location: str) -> Any:
    """Open the file/dir entry at an absolute ``location``, trying each base spec.

    Returns the first existing dfVFS file entry or ``None``. Uses a direct
    path-spec build (no tree walk)."""
    for base_spec in opened.base_path_specs:
        spec_location = _to_spec_location(base_spec.type_indicator, location)
        path_spec = path_spec_factory.Factory.NewPathSpec(
            base_spec.type_indicator, location=spec_location, parent=base_spec.parent
        )
        try:
            file_entry = resolver.Resolver.OpenFileEntry(path_spec)
        except dfvfs_errors.BackEndError:
            continue
        if file_entry is not None:
            return file_entry
    return None


def location_exists(opened: OpenedImage, location: str) -> bool:
    """True if a file exists at the absolute ``location``."""
    entry = _open_location(opened, location)
    return bool(entry is not None and entry.IsFile())


def read_file(opened: OpenedImage, location: str) -> bytes:
    """Read the file at the absolute ``location`` and return its bytes.

    Raises :class:`EvidenceAccessError` if it is absent or not a file."""
    entry = _open_location(opened, location)
    if entry is None or not entry.IsFile():
        raise EvidenceAccessError(f"no file at {location!r} in {opened.source_path}")
    return _read_entry(entry)


def _read_entry(file_entry: Any) -> bytes:
    """Copy a dfVFS file entry's default data stream into memory in chunks."""
    file_object = file_entry.GetFileObject()
    if file_object is None:
        return b""
    buf = bytearray()
    while True:
        chunk: bytes = file_object.read(_COPY_CHUNK_BYTES)
        if not chunk:
            break
        buf.extend(chunk)
    return bytes(buf)


def decompress_archive(archive: Path, workdir: Path) -> list[Path]:
    """Recursively unwrap ``archive`` into ``workdir`` and return leaf files.

    Handles the ROCBA memory capture's ``zip -> 7z -> raw`` nest: 7-Zip extracts
    both container types, so we extract, then re-extract any nested archive up to
    :data:`_MAX_ARCHIVE_DEPTH`. Returns the non-archive leaf files produced (the
    decompressed memory image is the largest)."""
    seven_zip = _resolve_7z()
    workdir.mkdir(parents=True, exist_ok=True)
    pending: list[tuple[Path, int]] = [(archive, 0)]
    leaves: list[Path] = []
    stage = 0
    while pending:
        current, depth = pending.pop()
        if depth >= _MAX_ARCHIVE_DEPTH:
            raise EvidenceAccessError(
                f"archive nesting exceeded {_MAX_ARCHIVE_DEPTH} levels at {current.name}"
            )
        stage += 1
        out_dir = workdir / f"stage{stage}"
        out_dir.mkdir(parents=True, exist_ok=True)
        _run_7z(seven_zip, current, out_dir)
        for produced in sorted(p for p in out_dir.rglob("*") if p.is_file()):
            if produced.suffix.lower() in _ARCHIVE_SUFFIXES:
                pending.append((produced, depth + 1))
            else:
                leaves.append(produced)
    if not leaves:
        raise EvidenceAccessError(f"no files produced from {archive}")
    return leaves


def _resolve_7z() -> str:
    """Return the 7-Zip executable path or raise a clear, actionable error."""
    for name in ("7z", "7za", "7zr"):
        found = shutil.which(name)
        if found:
            return found
    raise EvidenceAccessError(
        "7-Zip not found (need 7z/7za/7zr) — `apt install p7zip-full`; "
        "required to unwrap the nested memory archive"
    )


def _run_7z(seven_zip: str, archive: Path, out_dir: Path) -> None:
    """Invoke ``7z x`` into ``out_dir``; raise on non-zero exit."""
    try:
        # S603 ok: `seven_zip` is resolved via shutil.which to a fixed binary
        # name, argv is fully controlled (no shell, no untrusted exec).
        completed = subprocess.run(  # noqa: S603
            [seven_zip, "x", f"-o{out_dir}", "-y", "-bso0", "-bsp0", str(archive)],
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise EvidenceAccessError(f"failed to launch 7-Zip on {archive}: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace")[:500]
        raise EvidenceAccessError(
            f"7-Zip failed on {archive} (exit {completed.returncode}): {detail}"
        )


# Artifact extraction lives in the sibling module (keeps each file under the
# 400-LOC gate); re-export it so callers and tests see one ``access`` namespace.
# Imported at the bottom: artifacts imports the image core from here, so this
# order avoids a circular import (access is always the entry point).
from silentwitness_mcp.evidence.artifacts import (  # noqa: E402
    ROCBA_ARTIFACT_TARGETS,
    ArtifactTarget,
    ExtractedArtifact,
    extract_artifacts,
)

__all__ = [
    "ROCBA_ARTIFACT_TARGETS",
    "ArtifactTarget",
    "EvidenceAccessError",
    "ExtractedArtifact",
    "OpenedImage",
    "decompress_archive",
    "extract_artifacts",
    "location_exists",
    "open_image",
    "read_file",
]
