"""Atomic-write IO helpers — crash-safe writes for report, audit, manifest, ledger.

Every load-bearing file mutation in the project goes through one of these
helpers. The invariant: a killed process never leaves a half-written file.

Pattern (for replace-style writes):
  1. Write to ``<path>.tmp.<pid>.<rand>`` in the SAME directory as ``<path>``.
  2. ``os.fsync(tmp_fd)`` so the bytes hit disk.
  3. ``os.close(tmp_fd)``.
  4. ``os.replace(tmp, final)`` — atomic on POSIX (rename within same fs).
  5. ``os.fsync(parent_dir_fd)`` so the rename itself is durable.

If any step before (4) fails, the prior content of ``<path>`` is untouched and
the ``.tmp`` artefact is removed via ``try/finally``. If (4) succeeds but (5)
fails, the new content is on disk but may be lost after a power cut — the file
content invariant still holds.

Pattern (for append-style writes — JSONL audit/ledger lines):
  Open in append-binary mode, write the line + ``b"\\n"``, ``os.fsync(fd)``,
  close. NO long-lived file handles (per architecture §4.4) so concurrent
  writes from multiple tool calls cannot interleave bytes — every appender
  takes a fresh fd and the OS serialises ``O_APPEND`` writes < ``PIPE_BUF``.

References:
  - architecture.md §5.4 — Report-as-state atomic-save (writes report.md)
  - architecture.md §4.4 — Audit log JSONL discipline (appends + fsync)
  - architecture.md §4.9 — HMAC ledger append
  - PRD FR-CRASH-SAFE — crash safety invariant

Platform note: on macOS, ``os.fsync(fd)`` does NOT guarantee disk persistence
(it returns when bytes reach the drive cache; ``fcntl(F_FULLFSYNC)`` is needed
for true durability). For the hackathon we accept the Linux semantics — the
production deployment is SIFT/Linux and the test rig is Linux too.
"""

from __future__ import annotations

import contextlib
import json
import os
import secrets
from collections.abc import Generator
from pathlib import Path
from typing import IO, Any


def _tmp_path_for(path: Path) -> Path:
    """Return a sibling temp path for atomic-rename. Same directory as ``path``
    so the eventual ``os.replace`` is an intra-filesystem rename (atomic)."""
    suffix = f".tmp.{os.getpid()}.{secrets.token_hex(4)}"
    return path.with_name(path.name + suffix)


def _fsync_dir(dir_path: Path) -> None:
    """fsync the directory so a rename inside it is durable across crashes.

    Some filesystems (ext4 with ``data=writeback``, tmpfs) ignore the dir
    fsync; we still call it because on the filesystems that DO honour it the
    invariant becomes meaningfully stronger.
    """
    fd = os.open(str(dir_path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_bytes_atomic(path: Path, data: bytes, *, mode: int = 0o644) -> None:
    """Write ``data`` to ``path`` atomically. Creates parent dir if missing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = _tmp_path_for(path)
    fd = os.open(str(tmp_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp_path, path)
        _fsync_dir(path.parent)
    except BaseException:
        # On any failure before/at replace, drop the tmp artefact.
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_path)
        raise
    # Re-apply mode in case the OS clamped via umask on open.
    os.chmod(path, mode)


def write_text_atomic(path: Path, text: str, *, encoding: str = "utf-8", mode: int = 0o644) -> None:
    """Write ``text`` to ``path`` atomically with the named encoding."""
    write_bytes_atomic(path, text.encode(encoding), mode=mode)


def write_json_atomic(
    path: Path, data: Any, *, indent: int | None = None, mode: int = 0o644
) -> None:
    """Serialise ``data`` to JSON and write atomically.

    ``ensure_ascii=False`` so unicode round-trips cleanly (the report and the
    audit log both carry non-ASCII content). ``sort_keys=True`` so two writes
    of the same dict produce byte-identical output — important for content
    hashing in the citation gate.
    """
    payload = json.dumps(
        data,
        indent=indent,
        ensure_ascii=False,
        sort_keys=True,
    )
    write_text_atomic(path, payload, mode=mode)


def append_jsonl_line(path: Path, line: str, *, mode: int = 0o644) -> None:
    """Append a single JSONL line to ``path`` with ``\\n`` terminator + fsync.

    Concurrent appenders from multiple threads/processes are safe because each
    call takes a fresh ``O_APPEND`` fd; the OS atomically appends single
    write() calls below PIPE_BUF (4096 bytes on Linux), and our lines are
    well below that. NO long-lived file handles — explicit short-lived open/
    close per architecture §4.4.

    ``mode`` is only honoured on first-time file creation; subsequent appends
    do not chmod (a long-running case directory mode is set by the case
    bootstrap, not by every append).
    """
    if "\n" in line:
        raise ValueError("append_jsonl_line: line must not contain a newline")
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, mode)
    try:
        os.write(fd, line.encode("utf-8") + b"\n")
        os.fsync(fd)
    finally:
        os.close(fd)
    if not existed:
        os.chmod(path, mode)


@contextlib.contextmanager
def atomic_writer(path: Path, *, mode: int = 0o644) -> Generator[IO[bytes], None, None]:
    """Context manager yielding a writable binary handle to a sibling temp.

    On normal exit: fsync the temp, close, replace, fsync the parent dir.
    On exception: close + delete the temp; the target file is untouched.

    Use for streaming writes (e.g. Epic 11 WeasyPrint PDF render piping into
    ``cases/<case_id>/report.pdf``); single-shot writes should use
    ``write_bytes_atomic`` directly.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = _tmp_path_for(path)
    fd = os.open(str(tmp_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    handle = os.fdopen(fd, "wb", closefd=True)
    committed = False
    try:
        yield handle
        # Caller exited the `with` cleanly — commit.
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.replace(tmp_path, path)
        _fsync_dir(path.parent)
        os.chmod(path, mode)
        committed = True
    finally:
        if not committed:
            with contextlib.suppress(Exception):
                handle.close()
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp_path)


__all__ = [
    "append_jsonl_line",
    "atomic_writer",
    "write_bytes_atomic",
    "write_json_atomic",
    "write_text_atomic",
]
