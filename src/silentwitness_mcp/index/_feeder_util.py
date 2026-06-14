"""Shared helpers and the feeder contract for the targeted-parser feeders."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from silentwitness_mcp.index.store import IndexRecord

# Cap per-record text so a pathological event/registry blob can't bloat the DB or a query.
MAX_TEXT = 8192


@dataclass
class FeederStats:
    """Per-artifact diagnostics: how many records a feeder *skipped* (and why).

    Feeders swallow malformed/unreadable records to keep going, but a feeder that
    recovers 10% of records must not read as a clean run — so each skip is counted here
    and the orchestrator surfaces non-empty stats in the operator summary + audit trail.
    """

    skipped: dict[str, int] = field(default_factory=dict)

    def skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    @property
    def total_skipped(self) -> int:
        return sum(self.skipped.values())


class Feeder(Protocol):
    """The contract every artifact feeder shares (enforced at type-check time).

    Conform with a module-level ``_: Feeder = my_feeder`` line so a renamed keyword
    is caught by mypy rather than failing at runtime inside a worker subprocess. The
    optional ``stats`` collector lets a feeder report skipped records to the caller."""

    def __call__(
        self,
        path: Path,
        *,
        audit_id: str,
        host: str = "",
        source_path: str | None = None,
        stats: FeederStats | None = None,
    ) -> Iterator[IndexRecord]: ...


def sha256_file(path: Path) -> str:
    """SHA-256 of a file, streamed so a large artifact doesn't load into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = ["MAX_TEXT", "Feeder", "sha256_file"]
