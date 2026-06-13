"""dfVFS-backed evidence access — open an E01/raw image and extract artifacts.

Phase-0 evidence-access layer (plan: ``story-evidence-access``). It replaces the
prior assumption that tools receive an already-extracted ``$MFT`` / hive. The
real judged case (ROCBA) is a 24 GB E01 (87 GB uncompressed) whose disk image
has **no partition table** — the NTFS filesystem sits at offset 0.

dfVFS's :class:`~dfvfs.helpers.volume_scanner.VolumeScanner` resolves both the
partition-less case (ROCBA) and partitioned images (e.g. the NIST XP E01 with
NTFS at sector 63) without manual offset arithmetic, so one code path serves
every case. We drive it non-interactively (``partitions=all``, ``volumes=none``)
— no mediator, no prompts.

We address artifacts by **exact location** (direct path-spec lookup) or by
listing a single known directory, rather than walking the whole tree: an 87 GB
NTFS volume has hundreds of thousands of entries, and a per-target full walk
would blow the "extraction is minutes" budget. Using explicit live ``/Windows``
paths also sidesteps the ROCBA ``Windows.old`` duplicate hive set for free.

Safety: ``VolumeScanner`` falls back to an OS path spec for a source it cannot
identify as a disk image — which would enumerate the *host* filesystem. We guard
against that by accepting only filesystem-type base specs.

This module is pure evidence mechanics. Audit provenance + evidence-registry
recording are the caller's job (``cli_commands/prepare.py``) so the access layer
stays unit-testable in isolation.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from dfvfs.helpers import volume_scanner
from dfvfs.lib import definitions as dfvfs_definitions, errors as dfvfs_errors
from dfvfs.path import factory as path_spec_factory
from dfvfs.resolver import resolver

# Read window for in-process file copies — bounds peak memory on a multi-GB
# artifact ($MFT on a large NTFS volume can be hundreds of MB).
_COPY_CHUNK_BYTES = 4 * 1024 * 1024

# Archive suffixes we recursively unwrap. ROCBA memory is a zip -> 7z -> raw nest.
_ARCHIVE_SUFFIXES = frozenset({".zip", ".7z", ".gz", ".tar", ".tgz", ".bz2", ".xz"})
# Bound on nested-archive recursion so a zip-bomb / cycle can't loop forever.
_MAX_ARCHIVE_DEPTH = 4

# Base path specs we accept from VolumeScanner: real filesystem types only.
# FAKE is the in-memory test filesystem; OS would be the host root. Excluding
# both means a non-image source raises rather than enumerating the host.
_ACCEPTED_FS_INDICATORS: frozenset[str] = frozenset(
    dfvfs_definitions.FILE_SYSTEM_TYPE_INDICATORS
) - {dfvfs_definitions.TYPE_INDICATOR_FAKE}


class EvidenceAccessError(Exception):
    """Raised when an image cannot be opened or extraction fails."""


@dataclass(frozen=True)
class ArtifactTarget:
    """A high-value artifact to extract.

    * ``kind="file"`` — ``location`` is an absolute filesystem path; the single
      file is copied if present.
    * ``kind="dir_glob"`` — ``location`` is a directory; every immediate child
      whose name matches ``name_pattern`` (case-insensitive) is copied.
    * ``kind="per_user"`` — ``location`` is a path *relative to* each
      ``/Users/<name>/`` directory; copied for every user profile present.
    """

    label: str
    kind: Literal["file", "dir_glob", "per_user"]
    location: str
    name_pattern: str = ""


# ROCBA Windows-10 high-value set (confirmed present by the VPS probe). Explicit
# live /Windows paths avoid the Windows.old duplicate tree. $UsnJrnl is
# best-effort (its content is the $J alternate data stream; full ADS extraction
# is a Phase-1 refinement).
ROCBA_ARTIFACT_TARGETS: tuple[ArtifactTarget, ...] = (
    ArtifactTarget("mft", "file", "/$MFT"),
    ArtifactTarget("usnjrnl", "file", "/$Extend/$UsnJrnl"),
    ArtifactTarget("hive_software", "file", "/Windows/System32/config/SOFTWARE"),
    ArtifactTarget("hive_system", "file", "/Windows/System32/config/SYSTEM"),
    ArtifactTarget("hive_sam", "file", "/Windows/System32/config/SAM"),
    ArtifactTarget("hive_security", "file", "/Windows/System32/config/SECURITY"),
    ArtifactTarget("hive_default", "file", "/Windows/System32/config/DEFAULT"),
    ArtifactTarget("amcache", "file", "/Windows/appcompat/Programs/Amcache.hve"),
    ArtifactTarget("srum", "file", "/Windows/System32/sru/SRUDB.dat"),
    ArtifactTarget("evtx", "dir_glob", "/Windows/System32/winevt/Logs", r"\.evtx$"),
    ArtifactTarget("prefetch", "dir_glob", "/Windows/Prefetch", r"\.pf$"),
    ArtifactTarget("ntuser", "per_user", "NTUSER.DAT"),
    ArtifactTarget(
        "usrclass", "per_user", "AppData/Local/Microsoft/Windows/UsrClass.dat"
    ),
)

_USERS_DIR = "/Users"


@dataclass
class OpenedImage:
    """A scanned source image plus the filesystem base path specs dfVFS found.

    ROCBA yields one base spec (the offset-0 NTFS volume); partitioned images
    yield one per filesystem. Lookups try every base spec so multi-partition
    cases work unchanged."""

    source_path: Path
    # dfVFS path-spec objects (untyped third-party lib) — Any by necessity.
    base_path_specs: list[Any] = field(default_factory=list)


@dataclass(frozen=True)
class ExtractedArtifact:
    """One artifact copied out of an image: where it came from, where it landed."""

    label: str
    source_location: str
    output_path: Path
    size_bytes: int


def open_image(path: Path) -> OpenedImage:
    """Scan ``path`` (E01/raw/dd) and return its filesystem base path specs.

    VolumeScanner runs non-interactively so a partition-less volume image
    resolves to its filesystem at offset 0 and a partitioned image to each
    partition's filesystem. Base specs that are not a real filesystem type
    (e.g. an OS fallback for an unrecognised source) are rejected — otherwise a
    bad input could enumerate the host filesystem. Raises
    :class:`EvidenceAccessError` on any failure."""
    if not path.is_file():
        raise EvidenceAccessError(f"evidence image not found: {path}")
    options = volume_scanner.VolumeScannerOptions()
    options.partitions = ["all"]
    options.volumes = ["none"]
    options.snapshots = ["none"]
    scanner = volume_scanner.VolumeScanner()
    try:
        scanned = scanner.GetBasePathSpecs(str(path), options=options)
    except dfvfs_errors.ScannerError as exc:
        raise EvidenceAccessError(f"dfVFS could not scan {path}: {exc}") from exc
    specs = [s for s in (scanned or []) if s.type_indicator in _ACCEPTED_FS_INDICATORS]
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
        path_spec = path_spec_factory.Factory.NewPathSpec(
            base_spec.type_indicator, location=location, parent=base_spec.parent
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


def _write_entry(file_entry: Any, out_path: Path) -> int:
    """Stream a dfVFS file entry to ``out_path``; return bytes written."""
    file_object = file_entry.GetFileObject()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with out_path.open("wb") as handle:
        if file_object is None:
            return 0
        while True:
            chunk: bytes = file_object.read(_COPY_CHUNK_BYTES)
            if not chunk:
                break
            handle.write(chunk)
            written += len(chunk)
    return written


def _iter_dir(opened: OpenedImage, dir_location: str) -> Iterator[tuple[str, Any]]:
    """Yield ``(location, file_entry)`` for immediate children of a directory."""
    entry = _open_location(opened, dir_location)
    if entry is None or not entry.IsDirectory():
        return
    for sub in entry.sub_file_entries:
        location = getattr(sub.path_spec, "location", "") or ""
        yield location, sub


def _sanitise_location(location: str) -> str:
    """Turn a dfVFS ``/``-location into a safe relative output path component."""
    cleaned = location.replace("\\", "/").lstrip("/")
    cleaned = cleaned.replace("$", "_").replace(":", "_")
    parts = [p for p in cleaned.split("/") if p not in ("", ".", "..")]
    return "/".join(parts) or "artifact"


def _extract_one(
    label: str, location: str, file_entry: Any, workdir: Path
) -> ExtractedArtifact:
    out_path = workdir / label / _sanitise_location(location)
    size = _write_entry(file_entry, out_path)
    return ExtractedArtifact(
        label=label, source_location=location, output_path=out_path, size_bytes=size
    )


def extract_artifacts(
    opened: OpenedImage,
    workdir: Path,
    *,
    targets: tuple[ArtifactTarget, ...] = ROCBA_ARTIFACT_TARGETS,
) -> list[ExtractedArtifact]:
    """Copy every matching artifact into ``workdir`` and return what was written.

    A target that matches nothing is silently skipped (a host may legitimately
    lack SRUM/Amcache); the caller decides whether an empty result is fatal.
    Output layout: ``<workdir>/<label>/<sanitised-source-path>``."""
    workdir.mkdir(parents=True, exist_ok=True)
    results: list[ExtractedArtifact] = []
    for target in targets:
        if target.kind == "file":
            entry = _open_location(opened, target.location)
            if entry is not None and entry.IsFile():
                results.append(
                    _extract_one(target.label, target.location, entry, workdir)
                )
        elif target.kind == "dir_glob":
            pattern = re.compile(target.name_pattern, re.IGNORECASE)
            for location, sub in _iter_dir(opened, target.location):
                if sub.IsFile() and pattern.search(location):
                    results.append(_extract_one(target.label, location, sub, workdir))
        else:  # per_user
            for user_location, user_entry in _iter_dir(opened, _USERS_DIR):
                if not user_entry.IsDirectory():
                    continue
                child = f"{user_location.rstrip('/')}/{target.location}"
                entry = _open_location(opened, child)
                if entry is not None and entry.IsFile():
                    results.append(_extract_one(target.label, child, entry, workdir))
    return results


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
