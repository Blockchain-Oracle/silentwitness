"""SHA-256-locked evidence registry — refuse-on-unregistered gate.

One :class:`EvidenceRegistry` instance per case (constructed from the case
directory). The registry persists every artefact's canonical path, SHA-256,
size, and the audit_id of the registering call to
``cases/<case_id>/evidence.json`` via :func:`silentwitness_common.atomic_io.write_json_atomic`
so a crashed half-write cannot leave the case unrecoverable.

Three operations make up the gate (architecture.md §4.10):

* :meth:`EvidenceRegistry.register` — hash-then-record. Streams the file in
  8 KB chunks so 20 GB disk images don't OOM. Idempotent for re-register of
  the same (path, sha256); raises :class:`AlreadyRegisteredError` if the same
  path now hashes to a different digest (a real corruption signal, not noise).
* :meth:`EvidenceRegistry.assert_registered` — the gate every tool wrapper
  calls first. Raises :class:`EvidenceNotRegisteredError` for paths the agent
  has not earned the right to touch.
* :meth:`EvidenceRegistry.verify_hash` — case-resume integrity check.
  Re-streams the file and reports a :class:`~silentwitness_common.types.VerifyResult`
  comparing the live digest against the recorded one.

Lookup uses :func:`os.path.normcase` over the resolved path so the registry
correctly survives macOS HFS+/APFS case-insensitive lookups while still
displaying the original-case path in :class:`~silentwitness_common.types.EvidenceRecord`.

The manifest file mode is **0644** (intentionally world-readable: it lists
files and hashes, no secrets — those live in the HMAC ledger at 0600 under
``/var/lib/silentwitness/verification/``). Conceptual append-only is enforced
by two complementary defences: the Claude Code ``Edit(cases/*/evidence.json)``
deny rule (architecture §6.2 ``settings.json``) and ``register``'s own
sha256-mismatch refusal on re-registration.
"""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from silentwitness_common.atomic_io import write_json_atomic
from silentwitness_common.types import EvidenceRecord, EvidenceType, VerifyResult

_MANIFEST_FILENAME: Final = "evidence.json"
_MANIFEST_MODE: Final = 0o644
_SCHEMA_VERSION: Final = 1
_HASH_CHUNK_BYTES: Final = 8192


class EvidenceRegistryError(Exception):
    """Base class for evidence-registry-raised errors."""


class AlreadyRegisteredError(EvidenceRegistryError):
    """Raised when a path is re-registered with different content (sha256 drift).

    Idempotent re-register of the SAME content does NOT raise — it returns
    the existing record. The mismatch case is a real corruption signal worth
    halting the case for.
    """

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"evidence already registered with different content: {path} ({reason})")
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


class EvidenceRegistry:
    """Per-case evidence manifest with hash-locked register / assert / verify.

    Construction is cheap (no I/O until the first operation that needs the
    manifest). The constructor ensures the case directory exists so a fresh
    case can register evidence without an explicit bootstrap step.
    """

    def __init__(self, case_dir: Path) -> None:
        self._case_dir = case_dir
        self._case_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path = case_dir / _MANIFEST_FILENAME

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
          * Different SHA-256 ⇒ raises :class:`AlreadyRegisteredError` with
            ``reason="sha256_mismatch_on_reregister"``.

        The manifest write goes through :func:`write_json_atomic` so a killed
        process either leaves the prior manifest intact or commits the new
        one — never a torn JSON document.

        ``now`` is injected for deterministic tests; defaults to ``datetime.now(UTC)``.
        """
        resolved = path.resolve(strict=True)
        sha256, size_bytes = self._hash_and_size(resolved)
        manifest = self._load_manifest()
        existing = self._find_record(manifest, resolved)
        if existing is not None:
            if existing.sha256 == sha256:
                return existing
            raise AlreadyRegisteredError(path=resolved, reason="sha256_mismatch_on_reregister")
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
        """Return the :class:`EvidenceRecord` for ``path``, raise if absent.

        ``path`` is resolved (symlinks followed) but NOT strict — an
        unregistered path that no longer exists should still produce a clean
        :class:`EvidenceNotRegisteredError` rather than ``FileNotFoundError``,
        because the gate's job is to answer "did the agent earn the right to
        touch this?" — not to validate disk presence.
        """
        resolved = self._resolve_lenient(path)
        manifest = self._load_manifest()
        existing = self._find_record(manifest, resolved)
        if existing is None:
            raise EvidenceNotRegisteredError(path=resolved)
        return existing

    def verify_hash(self, path: Path) -> VerifyResult:
        """Re-stream ``path`` and compare against the recorded SHA-256.

        Used at case-resume time (architecture §4.10 — "hash re-verification
        at case-resume time") to catch silent bit-rot between sessions.
        """
        resolved = path.resolve(strict=True)
        record = self.assert_registered(resolved)
        actual, _ = self._hash_and_size(resolved)
        return VerifyResult(matches=record.sha256 == actual, expected=record.sha256, actual=actual)

    def list_all(self) -> list[EvidenceRecord]:
        """Return every record sorted by ``registered_at`` ascending."""
        manifest = self._load_manifest()
        records = [EvidenceRecord.model_validate(r) for r in manifest["records"]]
        records.sort(key=lambda r: r.registered_at)
        return records

    # ------------------------------------------------------------------ Internal
    @staticmethod
    def _hash_and_size(path: Path) -> tuple[str, int]:
        """Stream-hash + count bytes in 8 KB chunks. Single pass over the file."""
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as fh:
            while chunk := fh.read(_HASH_CHUNK_BYTES):
                digest.update(chunk)
                size += len(chunk)
        return digest.hexdigest(), size

    @staticmethod
    def _resolve_lenient(path: Path) -> Path:
        """Resolve symlinks and ``..`` without requiring the leaf to exist.

        ``Path.resolve(strict=False)`` is the right primitive on POSIX. We
        absolutise non-existent paths via the parent so a fully missing path
        still gets a stable canonical form for the lookup index.
        """
        try:
            return path.resolve(strict=True)
        except FileNotFoundError:
            return path.resolve(strict=False)

    @staticmethod
    def _index_key(path: Path) -> str:
        """Canonical lookup key — ``os.path.normcase`` over the path string.

        ``normcase`` is a no-op on POSIX but lowercases on Windows, and the
        explicit call also covers macOS HFS+/APFS case-insensitivity at the
        comparison layer regardless of how ``resolve`` returned the case.
        """
        return os.path.normcase(str(path))

    def _find_record(self, manifest: dict[str, Any], resolved: Path) -> EvidenceRecord | None:
        """Look up a record by canonical path with inode-equality fallback.

        ``os.path.normcase`` is a no-op on POSIX, so two case-different paths
        on macOS APFS (case-insensitive by default) would otherwise miss. The
        ``samefile`` check compares inodes for paths that exist — that's the
        correct cross-filesystem definition of "same evidence." A failed
        ``samefile`` (one side deleted between register and lookup, EIO, etc.)
        falls through to the normcase string compare so a registered+then-
        deleted path still resolves via its stored canonical form.
        """
        key = self._index_key(resolved)
        resolved_exists = resolved.exists()
        for raw in manifest["records"]:
            record = EvidenceRecord.model_validate(raw)
            if self._index_key(record.path) == key:
                return record
            if resolved_exists and record.path.exists():
                try:
                    if record.path.samefile(resolved):
                        return record
                except OSError:
                    continue
        return None

    def _load_manifest(self) -> dict[str, Any]:
        """Read + parse the manifest, or return a fresh skeleton on first use.

        Raises if the manifest exists but is unreadable / malformed — silent
        skip here would let a corrupted manifest masquerade as "no evidence
        registered yet" and reset the gate.
        """
        if not self._manifest_path.exists():
            return {"schema_version": _SCHEMA_VERSION, "records": []}
        import json

        with self._manifest_path.open("r", encoding="utf-8") as fh:
            manifest = json.load(fh)
        if not isinstance(manifest, dict):
            raise EvidenceRegistryError(
                f"evidence manifest at {self._manifest_path} is not a JSON object"
            )
        records = manifest.get("records")
        if not isinstance(records, list):
            raise EvidenceRegistryError(
                f"evidence manifest at {self._manifest_path} missing 'records' list"
            )
        return manifest


__all__ = [
    "AlreadyRegisteredError",
    "EvidenceNotRegisteredError",
    "EvidenceRegistry",
    "EvidenceRegistryError",
]
