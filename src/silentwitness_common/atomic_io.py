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
content invariant still holds (the caller still sees the exception so they
know durability isn't confirmed).

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

Concurrency note: if two writers race the same path with different ``mode``
values, the final permissions reflect whichever ``os.chmod`` ran last, NOT
whichever ``os.replace`` won. Content and mode are committed in separate
syscalls and the order between racing writers is undefined. In practice every
caller in this project writes a path with a single canonical mode so this
race is theoretical.
"""

from __future__ import annotations

import contextlib
import json
import os
import secrets
from collections.abc import Generator
from pathlib import Path
from typing import IO, Any

# Characters that ``str.splitlines()`` treats as line terminators. JSONL is
# defined by ``\n`` only, but downstream consumers commonly call
# ``content.splitlines()`` which splits on a wider set — if any of these slips
# into an audit line the audit JSONL silently de-syncs. PR-99 silent-failure
# review found this gap (the property test blacklists Cc/Cs/Zl/Zp but the
# production guard only rejected ``\n``).
_FORBIDDEN_LINE_CHARS: frozenset[str] = frozenset("\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029")

# O_CLOEXEC prevents a forked child from inheriting our tmp/audit fds and
# accidentally racing the replace. Forensic tool runners commonly fork.
_OPEN_FLAGS_TMP = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
_OPEN_FLAGS_APPEND = os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_CLOEXEC


def _tmp_path_for(path: Path) -> Path:
    """Return a sibling temp path for atomic-rename. Same directory as ``path``
    so the eventual ``os.replace`` is an intra-filesystem rename (atomic)."""
    suffix = f".tmp.{os.getpid()}.{secrets.token_hex(4)}"
    return path.with_name(path.name + suffix)


def _fsync_dir(dir_path: Path) -> None:
    """fsync the directory so a rename or first-create inside it is durable.

    Some filesystems (ext4 with ``data=writeback``, tmpfs) ignore the dir
    fsync; we still call it because on the filesystems that DO honour it the
    invariant becomes meaningfully stronger.
    """
    fd = os.open(str(dir_path), os.O_RDONLY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_all(fd: int, data: bytes) -> None:
    """``os.write`` may return short (signal interruption, EAGAIN on weird fds).
    Loop until every byte is committed. Required for crash-safety: a single
    truncated ``os.write`` would otherwise produce a partial file that passes
    fsync + replace and corrupts the audit trail silently."""
    view = memoryview(data)
    while view:
        n = os.write(fd, view)
        if n == 0:  # pragma: no cover — defensive, should never happen on regular files
            raise OSError("os.write returned 0 — refusing to spin")
        view = view[n:]


def write_bytes_atomic(path: Path, data: bytes, *, mode: int = 0o644) -> None:
    """Write ``data`` to ``path`` atomically. Creates parent dir if missing.

    If ``os.replace`` succeeds but a later step (``_fsync_dir`` or
    ``os.chmod``) fails, the file ON DISK contains the new content but the
    caller sees the exception. Treat any exception from this function as
    "write may or may not have committed" until you inspect the file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = _tmp_path_for(path)
    fd = os.open(str(tmp_path), _OPEN_FLAGS_TMP, mode)
    try:
        try:
            _write_all(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp_path, path)
        _fsync_dir(path.parent)
    except BaseException:
        # On any failure before/at replace, drop the tmp artefact. After
        # replace, the tmp_path no longer points at a file — FileNotFoundError
        # is the expected outcome and is suppressed.
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_path)
        raise
    # Re-apply mode in case the OS clamped via umask on open. Discrepancy
    # documented in module docstring.
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
    hashing in the citation gate (architecture §4.5).
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

    Rejects any character that ``str.splitlines()`` treats as a line
    terminator (LF, CR, VT, FF, FS, GS, RS, NEL, U+2028, U+2029). Downstream
    consumers that call ``content.splitlines()`` would otherwise mis-split
    the JSONL and the audit trail would silently de-sync.

    On first-time file creation, fsyncs the parent dir so the new dirent
    is durable.

    ``mode`` is only honoured on first-time file creation; subsequent appends
    do not chmod (a long-running case directory mode is set by the case
    bootstrap, not by every append).
    """
    forbidden = _FORBIDDEN_LINE_CHARS & set(line)
    if forbidden:
        codes = ", ".join(f"\\u{ord(c):04x}" for c in sorted(forbidden))
        raise ValueError(f"append_jsonl_line: line contains line-terminator char(s): {codes}")
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    fd = os.open(str(path), _OPEN_FLAGS_APPEND, mode)
    try:
        _write_all(fd, line.encode("utf-8") + b"\n")
        os.fsync(fd)
    finally:
        os.close(fd)
    if not existed:
        os.chmod(path, mode)
        _fsync_dir(path.parent)


@contextlib.contextmanager
def atomic_writer(path: Path, *, mode: int = 0o644) -> Generator[IO[bytes], None, None]:
    """Context manager yielding a writable binary handle to a sibling temp.

    On normal exit: fsync the temp, close, replace, fsync the parent dir.
    On exception: close + delete the temp; the target file is untouched.

    Use for streaming writes (e.g. Epic 11 WeasyPrint PDF render piping into
    ``cases/<case_id>/report.pdf``); single-shot writes should use
    ``write_bytes_atomic`` directly.

    ``committed`` flips to True immediately after ``os.replace`` — a later
    ``_fsync_dir`` or ``chmod`` failure does NOT trigger rollback because the
    file IS at the target path. The caller sees the exception but the file is
    committed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = _tmp_path_for(path)
    fd = os.open(str(tmp_path), _OPEN_FLAGS_TMP, mode)
    handle = os.fdopen(fd, "wb", closefd=True)
    committed = False
    try:
        yield handle
        # Caller exited the `with` cleanly — commit.
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.replace(tmp_path, path)
        committed = True  # COMMITTED: do not rollback even if later steps fail.
        _fsync_dir(path.parent)
        os.chmod(path, mode)
    finally:
        if not committed:
            # Narrow the suppress to OSError (close-during-rollback is the
            # specific failure mode we tolerate; MemoryError / KeyboardInterrupt
            # propagate per CLAUDE.md "don't catch what you can't handle").
            with contextlib.suppress(OSError):
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
