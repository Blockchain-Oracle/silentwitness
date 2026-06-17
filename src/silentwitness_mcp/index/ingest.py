"""Parse a mounted evidence image into the index (Phase 1, Valhuntir-aligned).

Per the SANS reference (AppliedIR/Valhuntir), we **mount** the E01 and parse the
mounted filesystem, rather than walk the raw image in Python. Concretely:
``ewfmount`` exposes the E01 as a raw device, ``ntfs-3g`` mounts the NTFS volume
read-only, and ``log2timeline`` runs over the mount point. This sidesteps dfVFS's
``VolumeScanner``, whose Volume-Shadow-Copy probe (libvshadow) crashes on the
ROCBA E01 — even with ``--no_vss`` — by reading a backup NTFS header past the
media end. Mounting never auto-scans VSS, and a mounted live filesystem gives
plaso the preprocessing + registry/EVTX context it needs (parsing orphaned
extracted files yields ~0 events).

``_plaso_event_to_record`` / ``_iter_json_lines`` are pure (unit-tested anywhere);
the mount + plaso run is exercised on the Linux box (ewf-tools + ntfs-3g + plaso,
all from ``uv sync --extra forensics`` / ``install.sh``).
"""

from __future__ import annotations

import contextlib
import json
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from collections.abc import Iterator
from pathlib import Path

from silentwitness_mcp.index.store import EvidenceIndex, IndexRecord

# Cap per-event text so a pathological message can't bloat the DB.
_MAX_TEXT = 8192
# High-value Windows behavioral parsers (verified valid via `log2timeline
# --parsers list`). amcache / jumplists are PLUGINS under winreg / olecf — enabled
# by their parent parser. We deliberately omit mft/filestat (millions of rows).
_PARSERS = "winreg,winevtx,prefetch,lnk,olecf,recycle_bin,esedb,winjob,usnjrnl"


class IngestError(Exception):
    """Raised when mounting, a parser tool, or its output fails."""


def _plaso_event_to_record(
    event: dict[str, object], *, audit_id: str, host: str, strip_prefix: str = ""
) -> IndexRecord | None:
    """Map one plaso ``json_line`` event to an :class:`IndexRecord`, or None.

    Events with no human-readable ``message`` are dropped. ``strip_prefix`` (the
    temp mount root) is removed from the source path so citations are stable
    across runs. ``source_tool`` keeps the producing plaso parser for filtering."""
    message = event.get("message")
    if not isinstance(message, str) or not message.strip():
        return None
    parser = event.get("parser")
    parser_name = parser if isinstance(parser, str) and parser else "unknown"
    path = str(event.get("display_name") or event.get("filename") or "")
    if strip_prefix and strip_prefix in path:
        path = path.split(strip_prefix, 1)[1] or path
    when = event.get("datetime")
    return IndexRecord(
        text=message[:_MAX_TEXT],
        source_tool=f"plaso:{parser_name}",
        artifact_path=path,
        host=host,
        ts=str(when) if isinstance(when, str) else "",
        audit_id=audit_id,
    )


def _iter_json_lines(path: Path) -> Iterator[dict[str, object]]:
    """Yield each JSON object from a ``psort`` json_line file, skipping junk lines."""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip().rstrip(",")
            if not line or line in ("[", "]"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def ingest_image_timeline(
    image: Path,
    index: EvidenceIndex,
    *,
    audit_id: str,
    host: str = "",
    timeout: int = 3600,
) -> int:
    """Mount ``image`` (E01), run plaso over the mount, ingest the timeline.

    Returns rows added. Always unmounts. Raises :class:`IngestError` on a mount or
    plaso failure. plaso / mount tools are resolved lazily, so this module imports
    without them installed."""
    log2timeline = _resolve("log2timeline.py", "log2timeline")
    psort = _resolve("psort.py", "psort")
    ewf_mnt, fs_mnt = _mount_image(image)
    try:
        with tempfile.TemporaryDirectory(prefix="sw-plaso-") as tmp:
            storage = Path(tmp) / "timeline.plaso"
            json_out = Path(tmp) / "timeline.jsonl"
            _run(
                [
                    log2timeline,
                    "-u",
                    "--status_view",
                    "none",
                    "--parsers",
                    _PARSERS,
                    "--storage_file",
                    str(storage),
                    str(fs_mnt),
                ],
                timeout=timeout,
                what="log2timeline",
            )
            _run(
                [psort, "-o", "json_line", "-w", str(json_out), str(storage)],
                timeout=timeout,
                what="psort",
            )
            if not json_out.is_file():
                raise IngestError(f"psort produced no output for {image}")
            prefix = str(fs_mnt)
            records = (
                rec
                for event in _iter_json_lines(json_out)
                if (
                    rec := _plaso_event_to_record(
                        event, audit_id=audit_id, host=host, strip_prefix=prefix
                    )
                )
                is not None
            )
            return index.ingest(records)
    finally:
        _unmount(ewf_mnt, fs_mnt)


def _mount_image(image: Path) -> tuple[Path, Path]:
    """ewfmount the E01, then ntfs-3g the NTFS volume read-only.

    Returns (ewf_mountpoint, fs_mountpoint). Raises :class:`IngestError` (after
    cleaning up a partial mount) on failure."""
    ewfmount = _resolve("ewfmount")
    ntfs3g = _resolve("ntfs-3g")
    ewf_mnt = Path(tempfile.mkdtemp(prefix="sw-ewf-"))
    fs_mnt = Path(tempfile.mkdtemp(prefix="sw-fs-"))
    try:
        _run([ewfmount, str(image), str(ewf_mnt)], timeout=300, what="ewfmount")
        raw = ewf_mnt / "ewf1"
        offset = _ntfs_offset(raw)
        _run(
            [ntfs3g, "-o", f"ro,loop,offset={offset}", str(raw), str(fs_mnt)],
            timeout=180,
            what="ntfs-3g",
        )
    except IngestError:
        _unmount(ewf_mnt, fs_mnt)
        raise
    return ewf_mnt, fs_mnt


def _ntfs_offset(raw: Path) -> int:
    """Byte offset of the first NTFS partition (0 if no partition table)."""
    mmls = shutil.which("mmls")
    if not mmls:
        return 0
    try:
        result = subprocess.run(  # noqa: S603
            [mmls, "-a", str(raw)], capture_output=True, text=True, timeout=120, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return 0
    for line in result.stdout.splitlines():
        if "NTFS" in line:
            parts = line.split()
            with contextlib.suppress(IndexError, ValueError):
                return int(parts[2]) * 512  # mmls 'start' column is in sectors
    return 0


def _unmount(ewf_mnt: Path, fs_mnt: Path) -> None:
    """Tear down the ntfs-3g + ewfmount FUSE mounts and remove the temp dirs."""
    for argv in (["umount", str(fs_mnt)], ["fusermount", "-u", str(ewf_mnt)]):
        tool = shutil.which(argv[0])
        if tool:
            with contextlib.suppress(OSError, subprocess.SubprocessError):
                subprocess.run(  # noqa: S603
                    [tool, *argv[1:]], capture_output=True, check=False, timeout=60
                )
    for mountpoint in (fs_mnt, ewf_mnt):
        with contextlib.suppress(OSError):
            mountpoint.rmdir()


def _resolve(*names: str) -> str:
    """Return the path to the first tool name found, or raise."""
    for name in names:
        found = shutil.which(name)
        if found:
            return found
        for directory in _tool_script_dirs():
            candidate = directory / name
            if candidate.is_file():
                return str(candidate)
    raise IngestError(
        f"required tool not found (tried {names}) — install the forensics extra "
        "and mount tools: `uv sync --extra forensics` + `bash install.sh`"
    )


def _tool_script_dirs() -> tuple[Path, ...]:
    """Script dirs to search when dependency CLIs live inside the uv tool venv."""
    candidates = [Path(sys.executable).parent, Path(sys.executable).resolve().parent]
    scripts = sysconfig.get_path("scripts")
    if scripts:
        candidates.append(Path(scripts))
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return tuple(unique)


def _run(argv: list[str], *, timeout: int, what: str) -> None:
    """Run a CLI step; raise :class:`IngestError` on failure/timeout."""
    try:
        completed = subprocess.run(  # noqa: S603
            argv, capture_output=True, check=False, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise IngestError(f"{what} failed to run: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace")[:500]
        raise IngestError(f"{what} exited {completed.returncode}: {detail}")


__all__ = ["IngestError", "ingest_image_timeline"]
