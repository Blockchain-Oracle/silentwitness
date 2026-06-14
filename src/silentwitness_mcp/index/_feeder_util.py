"""Shared helpers and the feeder contract for the targeted-parser feeders."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from silentwitness_mcp.index.store import IndexRecord

# Cap per-record text so a pathological event/registry blob can't bloat the DB or a query.
MAX_TEXT = 8192


class Feeder(Protocol):
    """The contract every artifact feeder shares (enforced at type-check time).

    Conform with a module-level ``_: Feeder = my_feeder`` line so a renamed keyword
    is caught by mypy rather than failing at runtime inside a worker subprocess."""

    def __call__(
        self, path: Path, *, audit_id: str, host: str = "", source_path: str | None = None
    ) -> Iterator[IndexRecord]: ...


def sha256_file(path: Path) -> str:
    """SHA-256 of a file, streamed so a large artifact doesn't load into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = ["MAX_TEXT", "Feeder", "sha256_file"]
