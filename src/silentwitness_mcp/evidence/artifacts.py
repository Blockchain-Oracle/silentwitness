"""Artifact extraction from an opened evidence image.

The high-value Windows artifact set (``$MFT``, registry hives, EVTX, Prefetch,
Amcache, SRUM, per-user hives) and the logic that copies each one out of an
:class:`~silentwitness_mcp.evidence.access.OpenedImage`. The image-opening +
file-reading mechanics live in ``access``; this module is re-exported through it
(``access.extract_artifacts`` etc.) so callers see one namespace.
"""

from __future__ import annotations

import contextlib
import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from dfvfs.lib import errors as dfvfs_errors

from silentwitness_mcp.evidence.access import (
    _COPY_CHUNK_BYTES,
    OpenedImage,
    _open_location,
)

_LOG = logging.getLogger(__name__)
_USERS_DIR = "/Users"


@dataclass(frozen=True)
class ArtifactTarget:
    """A high-value artifact to extract.

    * ``kind="file"`` — ``location`` is an absolute path; the single file is
      copied if present.
    * ``kind="dir_glob"`` — ``location`` is a directory; every immediate child
      whose name matches ``name_pattern`` (case-insensitive) is copied.
    * ``kind="per_user"`` — ``location`` is relative to each ``/Users/<name>/``
      directory; copied for every user profile present.
    * ``kind="per_user_glob"`` — ``location`` is a directory relative to each
      ``/Users/<name>/``; every immediate child whose *basename* matches
      ``name_pattern`` is copied (e.g. Recent ``*.lnk``, PowerShell transcripts).
    """

    label: str
    kind: Literal["file", "dir_glob", "per_user", "per_user_glob"]
    location: str
    name_pattern: str = ""
    # Named NTFS alternate data stream to copy instead of the default ($DATA) stream;
    # the USN journal content lives in $UsnJrnl's "$J" ADS, not its default stream.
    data_stream: str = ""


# ROCBA Windows-10 high-value set (confirmed present by the VPS probe). Explicit
# live /Windows paths avoid the Windows.old duplicate tree.
ROCBA_ARTIFACT_TARGETS: tuple[ArtifactTarget, ...] = (
    ArtifactTarget("mft", "file", "/$MFT"),
    ArtifactTarget("usnjrnl", "file", "/$Extend/$UsnJrnl", data_stream="$J"),
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
    ArtifactTarget("usrclass", "per_user", "AppData/Local/Microsoft/Windows/UsrClass.dat"),
    # Per-user activity artifacts — "what was opened / where it was sent."
    ArtifactTarget("lnk", "per_user_glob", "AppData/Roaming/Microsoft/Windows/Recent", r"\.lnk$"),
    ArtifactTarget(
        "jumplist_auto",
        "per_user_glob",
        "AppData/Roaming/Microsoft/Windows/Recent/AutomaticDestinations",
        r"\.automaticDestinations-ms$",
    ),
    ArtifactTarget(
        "ps_transcript",
        "per_user_glob",
        "Documents",
        r"^PowerShell_transcript\..*\.txt$",
    ),
)


@dataclass(frozen=True)
class ExtractedArtifact:
    """One artifact copied out of an image: where it came from, where it landed.

    ``truncated`` is True when the copy stopped early on an unrecoverable read (a
    corrupt NTFS-compressed cluster in the source image): the readable prefix is
    kept and recorded so downstream parsing gets what evidence exists."""

    label: str
    source_location: str
    output_path: Path
    size_bytes: int
    truncated: bool = False


def _sanitise_location(location: str) -> str:
    """Turn a ``/``-location into a safe relative output path component."""
    cleaned = location.replace("\\", "/").lstrip("/")
    cleaned = cleaned.replace("$", "_").replace(":", "_")
    parts = [p for p in cleaned.split("/") if p not in ("", ".", "..")]
    return "/".join(parts) or "artifact"


def _iter_dir(opened: OpenedImage, dir_location: str) -> Iterator[tuple[str, Any]]:
    """Yield canonical ``(/-location, file_entry)`` for a directory's children."""
    entry = _open_location(opened, dir_location)
    if entry is None or not entry.IsDirectory():
        return
    for sub in entry.sub_file_entries:
        raw = getattr(sub.path_spec, "location", "") or ""
        yield raw.replace("\\", "/"), sub  # normalise NTFS backslash -> "/"


def _write_entry(file_entry: Any, out_path: Path, *, data_stream: str = "") -> tuple[int, bool]:
    """Stream a dfVFS file entry to ``out_path``; return (bytes_written, truncated).

    ``data_stream`` names a non-default NTFS alternate data stream to copy (e.g. ``$J``);
    empty copies the default ($DATA) stream. ``truncated`` is True when a mid-stream read
    fails on a corrupt NTFS-compressed cluster (Security.evtx on the ROCBA image): we keep
    the bytes read so far rather than discard the whole file — the readable prefix still
    holds most of the records."""
    file_object = file_entry.GetFileObject(data_stream_name=data_stream)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    truncated = False
    with out_path.open("wb") as handle:
        if file_object is None:
            return 0, False
        while True:
            try:
                chunk: bytes = file_object.read(_COPY_CHUNK_BYTES)
            except (OSError, dfvfs_errors.Error):
                truncated = True
                break
            if not chunk:
                break
            handle.write(chunk)
            written += len(chunk)
    return written, truncated


def _extract_one(
    label: str, location: str, file_entry: Any, workdir: Path, *, data_stream: str = ""
) -> ExtractedArtifact | None:
    """Copy one artifact; recover the readable prefix if its data is partly corrupt.

    Some ROCBA NTFS-compressed event logs (incl. Security.evtx) have a corrupt
    LZNT1 cluster mid-file that TSK, libfsntfs AND ntfs-3g all fail on at the same
    offset — an image defect, not the reader. Keep the readable prefix and flag it
    ``truncated``; a fully unreadable / empty file is dropped and logged."""
    out_path = workdir / label / _sanitise_location(location)
    try:
        size, truncated = _write_entry(file_entry, out_path, data_stream=data_stream)
    except (OSError, dfvfs_errors.Error) as exc:
        with contextlib.suppress(OSError):
            out_path.unlink()
        _LOG.warning("skipped unreadable artifact %s %s: %s", label, location, exc)
        return None
    if size == 0:
        with contextlib.suppress(OSError):
            out_path.unlink()
        _LOG.warning("skipped empty/unreadable artifact %s %s", label, location)
        return None
    if truncated:
        _LOG.warning(
            "recovered truncated artifact %s %s: %d bytes (corrupt compressed cluster)",
            label,
            location,
            size,
        )
    return ExtractedArtifact(
        label=label,
        source_location=location,
        output_path=out_path,
        size_bytes=size,
        truncated=truncated,
    )


def _append_if_extracted(
    results: list[ExtractedArtifact],
    label: str,
    location: str,
    entry: Any,
    workdir: Path,
    *,
    data_stream: str = "",
) -> None:
    """Extract one artifact and append it unless its data was unreadable."""
    extracted = _extract_one(label, location, entry, workdir, data_stream=data_stream)
    if extracted is not None:
        results.append(extracted)


def extract_artifacts(
    opened: OpenedImage,
    workdir: Path,
    *,
    targets: tuple[ArtifactTarget, ...] = ROCBA_ARTIFACT_TARGETS,
) -> list[ExtractedArtifact]:
    """Copy every matching artifact into ``workdir`` and return what was written.

    A target that matches nothing is skipped (a host may legitimately lack
    SRUM/Amcache); the caller decides whether an empty result is fatal. Output
    layout: ``<workdir>/<label>/<sanitised-source-path>``."""
    workdir.mkdir(parents=True, exist_ok=True)
    results: list[ExtractedArtifact] = []
    for target in targets:
        if target.kind == "file":
            entry = _open_location(opened, target.location)
            if entry is not None and entry.IsFile():
                _append_if_extracted(
                    results,
                    target.label,
                    target.location,
                    entry,
                    workdir,
                    data_stream=target.data_stream,
                )
        elif target.kind == "dir_glob":
            pattern = re.compile(target.name_pattern, re.IGNORECASE)
            for location, sub in _iter_dir(opened, target.location):
                if sub.IsFile() and pattern.search(location):
                    _append_if_extracted(results, target.label, location, sub, workdir)
        else:  # per_user / per_user_glob
            for user_location, user_entry in _iter_dir(opened, _USERS_DIR):
                if not user_entry.IsDirectory():
                    continue
                base = f"{user_location.rstrip('/')}/{target.location}"
                if target.kind == "per_user":
                    entry = _open_location(opened, base)
                    if entry is not None and entry.IsFile():
                        _append_if_extracted(results, target.label, base, entry, workdir)
                    continue
                pattern = re.compile(target.name_pattern, re.IGNORECASE)
                for location, sub in _iter_dir(opened, base):
                    name = location.rsplit("/", 1)[-1]
                    if sub.IsFile() and pattern.search(name):
                        _append_if_extracted(results, target.label, location, sub, workdir)
    return results


__all__ = [
    "ROCBA_ARTIFACT_TARGETS",
    "ArtifactTarget",
    "ExtractedArtifact",
    "extract_artifacts",
]
