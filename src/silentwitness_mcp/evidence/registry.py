"""SHA-256-locked evidence registry — refuse-on-unregistered gate (architecture §4.10).

Three operations make up the gate:

* :meth:`EvidenceRegistry.register` — hash-then-record under an exclusive
  ``fcntl.flock`` on ``cases/<case_id>/.evidence.lock`` so two parallel
  specialists (architecture §5.2) cannot lose updates.
* :meth:`EvidenceRegistry.assert_registered` — every tool wrapper's first
  call. Distinct :class:`EvidenceNotRegisteredError` vs
  :class:`EvidenceMissingOnDiskError` so wrappers map each to its own
  :class:`~silentwitness_common.types.ToolResponse` failure reason.
* :meth:`EvidenceRegistry.verify_hash` — case-resume bit-rot check.

Lookup combines ``os.path.normcase`` (Windows/POSIX) and ``Path.samefile``
inode-equality (macOS APFS + POSIX hardlinks). ``samefile`` only swallows
``FileNotFoundError``; ``EIO`` / ``EACCES`` / ``ELOOP`` propagate as
:class:`EvidenceRegistryError` — bit-rot on registered evidence must never
be silently downgraded to "not found".

Manifest file mode 0644 (not a secret; lists files + hashes). HMAC ledger
lives separately at 0600 in ``/var/lib/silentwitness/verification/``.
Conceptual append-only enforced by (a) the Claude Code
``Edit(cases/*/evidence.json)`` deny rule per architecture §6.2 and
(b) ``register``'s own sha256-mismatch refusal on re-registration.

TOCTOU note: SHA-256 is computed before the manifest write. A replace
between hash and write records the pre-replacement digest; ``verify_hash``
catches it on case-resume. The window is one filesystem write; on the
production ``ro,noexec,nosuid`` evidence mount (architecture §4.11) it
is unreachable.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any, Final

from pydantic import ValidationError

from silentwitness_common.atomic_io import write_json_atomic
from silentwitness_common.types import EvidenceRecord, EvidenceType, VerifyResult

_MANIFEST_FILENAME: Final = "evidence.json"
_LOCK_FILENAME: Final = ".evidence.lock"
_MANIFEST_MODE: Final = 0o644
_SCHEMA_VERSION: Final = 1
_HASH_CHUNK_BYTES: Final = 8192


class EvidenceRegistryError(Exception):
    """Base class for evidence-registry-raised errors."""


class EvidenceContentDriftError(EvidenceRegistryError):
    """A path is re-registered with content that no longer matches the prior digest.

    The mismatch case is a real corruption signal worth halting the case for —
    deliberately NOT named ``AlreadyRegisteredError`` so a downstream
    ``except`` clause can't accidentally read as benign idempotency. The
    idempotent same-content re-register path does not raise; it returns the
    existing record.
    """

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"evidence content drift on re-register: {path} ({reason})")
        self.path = path
        self.reason = reason


class EvidenceNotRegisteredError(EvidenceRegistryError):
    """The gate raised by :meth:`EvidenceRegistry.assert_registered`.

    Tool wrappers that catch this should refuse the call rather than
    catching-and-continuing — a tool invocation against an unregistered path
    is the exact failure mode the wedge is built to prevent.
    """

    def __init__(self, path: Path) -> None:
        super().__init__(f"evidence path not registered: {path}")
        self.path = path


class EvidenceMissingOnDiskError(EvidenceRegistryError):
    """The path IS registered but the file has been removed from disk.

    Distinct from :class:`EvidenceNotRegisteredError` so tool wrappers can map
    the two outcomes to different :class:`~silentwitness_common.types.ToolResponse`
    failure reasons — "agent forgot to register" vs "evidence vanished" are
    different analyst-debugging journeys.
    """

    def __init__(self, path: Path) -> None:
        super().__init__(f"registered evidence missing on disk: {path}")
        self.path = path


class EvidenceRegistry:
    """Per-case evidence manifest with hash-locked register / assert / verify.

    Concurrency contract:
      * :meth:`register` takes an exclusive ``fcntl.flock`` on
        ``cases/<case_id>/.evidence.lock`` for the read-modify-write of
        ``evidence.json``. Cross-process and cross-thread safe.
      * Read operations (:meth:`assert_registered`, :meth:`verify_hash`,
        :meth:`list_all`) do NOT take the lock. Concurrent reads are safe;
        a read concurrent with a register sees either the prior or the new
        manifest (atomic-replace semantics from
        :func:`silentwitness_common.atomic_io.write_json_atomic`).
    """

    def __init__(self, case_dir: Path) -> None:
        self._case_dir = case_dir
        self._case_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path = case_dir / _MANIFEST_FILENAME
        self._lock_path = case_dir / _LOCK_FILENAME

    # ------------------------------------------------------------------ Public
    @property
    def case_dir(self) -> Path:
        return self._case_dir

    @property
    def manifest_path(self) -> Path:
        return self._manifest_path

    def register(
        self,
        path: Path,
        evidence_type: EvidenceType,
        audit_id: str,
        *,
        now: datetime | None = None,
    ) -> EvidenceRecord:
        """Hash ``path``, append an :class:`EvidenceRecord` to the manifest.

        Resolves ``path`` strictly (must exist) so symlinks and ``..`` segments
        canonicalise to the on-disk target. If the resolved path is already
        present:
          * Same SHA-256 ⇒ returns the existing record (idempotent re-register).
          * Different SHA-256 ⇒ raises :class:`EvidenceContentDriftError` with
            ``reason="sha256_mismatch_on_reregister"``.

        The read-modify-write of ``evidence.json`` runs under an exclusive
        ``fcntl.flock`` on ``.evidence.lock`` so two parallel specialists
        (architecture §5.2) cannot lose updates. The manifest write itself
        goes through :func:`write_json_atomic` so a killed process either
        leaves the prior manifest intact or commits the new one — never a
        torn JSON document.

        ``now`` is injected for deterministic tests; defaults to ``datetime.now(UTC)``.
        """
        resolved = path.resolve(strict=True)
        sha256, size_bytes = self._hash_and_size(resolved)
        with self._exclusive_manifest_lock():
            manifest = self._load_manifest()
            existing = self._find_record(manifest, resolved)
            if existing is not None:
                if existing.sha256 == sha256:
                    return existing
                raise EvidenceContentDriftError(
                    path=resolved, reason="sha256_mismatch_on_reregister"
                )
            record = EvidenceRecord(
                path=resolved,
                type=evidence_type,
                sha256=sha256,
                size_bytes=size_bytes,
                registered_at=now if now is not None else datetime.now(UTC),
                registered_audit_id=audit_id,
            )
            manifest["records"].append(record.model_dump(mode="json"))
            write_json_atomic(self._manifest_path, manifest, mode=_MANIFEST_MODE)
        return record

    def assert_registered(self, path: Path) -> EvidenceRecord:
        """Return the :class:`EvidenceRecord` for ``path``, raise if absent or gone.

        Raises:
          * :class:`EvidenceNotRegisteredError` — the path was never registered.
          * :class:`EvidenceMissingOnDiskError` — registered, but the file is
            no longer on disk (deleted, unmounted, renamed away).

        These are distinct so tool wrappers map them to distinct
        :class:`~silentwitness_common.types.ToolResponse` failure reasons.
        """
        resolved = self._resolve_lenient(path)
        manifest = self._load_manifest()
        existing = self._find_record(manifest, resolved)
        if existing is None:
            raise EvidenceNotRegisteredError(path=resolved)
        # Registry hit. Verify on-disk presence — registered-but-gone is its
        # own failure class so the gate caller can distinguish it.
        if not existing.path.exists():
            raise EvidenceMissingOnDiskError(path=existing.path)
        return existing

    def verify_hash(self, path: Path) -> VerifyResult:
        """Re-stream ``path`` and compare against the recorded SHA-256.

        Used at case-resume time (architecture §4.10 — "hash re-verification
        at case-resume time") to catch silent bit-rot between sessions.
        Raises :class:`EvidenceMissingOnDiskError` for registered-then-deleted
        paths (uniform with :meth:`assert_registered`) rather than leaking a
        raw ``FileNotFoundError``.
        """
        record = self.assert_registered(path)
        actual, _ = self._hash_and_size(record.path)
        return VerifyResult(matches=record.sha256 == actual, expected=record.sha256, actual=actual)

    def list_all(self) -> list[EvidenceRecord]:
        """Return every record sorted by ``registered_at`` ascending."""
        manifest = self._load_manifest()
        records: list[EvidenceRecord] = []
        for idx, raw in enumerate(manifest["records"]):
            records.append(self._validate_record(raw, idx))
        records.sort(key=lambda r: r.registered_at)
        return records

    # ------------------------------------------------------------------ Internal
    @staticmethod
    def _hash_and_size(path: Path) -> tuple[str, int]:
        """Stream-hash + count bytes in 8 KB chunks with a defensive fstat check.

        After the streaming loop completes, an ``os.fstat`` cross-check
        ensures we read the file we expected: a partial-read regression or
        concurrent truncation would otherwise produce a digest of less than
        the full file, silently. ``OSError`` mid-read (the bit-rot signal
        the registry exists to surface) is wrapped with byte-offset context
        so the caller's error message tells the analyst which file and where.
        """
        digest = hashlib.sha256()
        size = 0
        try:
            with path.open("rb") as fh:
                while chunk := fh.read(_HASH_CHUNK_BYTES):
                    digest.update(chunk)
                    size += len(chunk)
                stat_size = os.fstat(fh.fileno()).st_size
        except OSError as exc:
            raise EvidenceRegistryError(
                f"hash stream failed on {path} after {size} bytes: "
                f"errno={exc.errno} ({exc.strerror})"
            ) from exc
        if size != stat_size:
            raise EvidenceRegistryError(
                f"hash stream read {size} bytes from {path} but fstat reports "
                f"{stat_size} — refusing to register a partial digest"
            )
        return digest.hexdigest(), size

    @staticmethod
    def _resolve_lenient(path: Path) -> Path:
        """Resolve symlinks and ``..`` without requiring the leaf to exist.

        ``Path.resolve(strict=False)`` is the right primitive on POSIX. The
        try/except over ``strict=True`` is purely a perf optimization — the
        strict form is cheaper when the file exists (no double walk).
        """
        try:
            return path.resolve(strict=True)
        except FileNotFoundError:
            return path.resolve(strict=False)

    @staticmethod
    def _index_key(path: Path) -> str:
        """Canonical lookup key — ``os.path.normcase`` over the path string.

        ``normcase`` is a no-op on POSIX but lowercases on Windows. The
        inode-equality fallback in :meth:`_find_record` handles macOS APFS
        case-insensitivity (where ``normcase`` would not help).
        """
        return os.path.normcase(str(path))

    def _find_record(self, manifest: dict[str, Any], resolved: Path) -> EvidenceRecord | None:
        """Look up a record by canonical path with inode-equality fallback.

        Iterates raw dicts (no per-record Pydantic round-trip) — only the
        matched record is validated, so a single malformed record in the
        manifest doesn't break lookup of every record after it (it's caught
        in :meth:`list_all` at index time, which is the right place).

        ``samefile`` only swallows :class:`FileNotFoundError` (the benign
        one-side-deleted case). Genuine ``OSError`` (``EIO``, ``EACCES``,
        ``ELOOP``, etc.) on the registered path is the exact bit-rot signal
        the wedge defends against — propagate it as
        :class:`EvidenceRegistryError` so the gate never silently downgrades
        corruption into "not found."
        """
        key = self._index_key(resolved)
        resolved_exists = resolved.exists()
        for idx, raw in enumerate(manifest["records"]):
            raw_path_str = raw.get("path") if isinstance(raw, dict) else None
            if not isinstance(raw_path_str, str):
                continue
            raw_path = Path(raw_path_str)
            if self._index_key(raw_path) == key:
                return self._validate_record(raw, idx)
            if not resolved_exists:
                continue
            try:
                if raw_path.exists() and raw_path.samefile(resolved):
                    return self._validate_record(raw, idx)
            except FileNotFoundError:
                # Benign: a race between `.exists()` and `.samefile()`.
                continue
            except OSError as exc:
                raise EvidenceRegistryError(
                    f"samefile() failed on registered path {raw_path} vs "
                    f"lookup {resolved}: errno={exc.errno} ({exc.strerror}) — "
                    "refusing to fall back; this is the bit-rot signal the "
                    "gate exists to surface"
                ) from exc
        return None

    @staticmethod
    def _validate_record(raw: dict[str, Any], idx: int) -> EvidenceRecord:
        """Wrap Pydantic validation so a single malformed record reports its index."""
        try:
            return EvidenceRecord.model_validate(raw)
        except ValidationError as exc:
            raise EvidenceRegistryError(
                f"evidence manifest record #{idx} is malformed: {exc}"
            ) from exc

    def _load_manifest(self) -> dict[str, Any]:
        """Read + parse the manifest, or return a fresh skeleton on first use.

        Wraps every non-benign read error (``json.JSONDecodeError``,
        ``UnicodeDecodeError``, ``OSError`` other than the TOCTOU
        ``FileNotFoundError``) as :class:`EvidenceRegistryError` so tool
        wrappers can catch one exception family for "manifest unusable."
        Validates ``schema_version`` so a future-version manifest in front of
        an older codebase fails loud rather than silently sliding through.
        """
        if not self._manifest_path.exists():
            return {"schema_version": _SCHEMA_VERSION, "records": []}
        try:
            with self._manifest_path.open("r", encoding="utf-8") as fh:
                manifest = json.load(fh)
        except FileNotFoundError:
            # TOCTOU with the existence check above — concurrent delete.
            # Treat as first-use, identical to the no-file branch.
            return {"schema_version": _SCHEMA_VERSION, "records": []}
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise EvidenceRegistryError(
                f"evidence manifest at {self._manifest_path} is unreadable or "
                f"malformed ({type(exc).__name__}: {exc}) — refusing to "
                "silently reset the gate; restore from backup or halt the case"
            ) from exc
        if not isinstance(manifest, dict):
            raise EvidenceRegistryError(
                f"evidence manifest at {self._manifest_path} is not a JSON object"
            )
        schema_version = manifest.get("schema_version")
        if schema_version != _SCHEMA_VERSION:
            raise EvidenceRegistryError(
                f"evidence manifest at {self._manifest_path} has "
                f"schema_version={schema_version!r}, this code understands "
                f"only {_SCHEMA_VERSION}; refusing to silently operate on a "
                "manifest from a different codebase version"
            )
        records = manifest.get("records")
        if not isinstance(records, list):
            raise EvidenceRegistryError(
                f"evidence manifest at {self._manifest_path} missing 'records' list"
            )
        return manifest

    @contextmanager
    def _exclusive_manifest_lock(self) -> Generator[None, None, None]:
        """fcntl.flock the manifest critical section. Cross-process safe."""
        handle: IO[bytes] = self._lock_path.open("ab")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()


__all__ = [
    "EvidenceContentDriftError",
    "EvidenceMissingOnDiskError",
    "EvidenceNotRegisteredError",
    "EvidenceRegistry",
    "EvidenceRegistryError",
]
