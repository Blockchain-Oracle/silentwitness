"""AuditIndex — lightweight per-validation-pass index of audit/*.jsonl entries.

Built fresh on every validate call (audit JSONL files are append-only during
an investigation; a cached index would miss entries added after construction).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, ConfigDict

_LOG = logging.getLogger(__name__)


class AuditEntryRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    audit_id: str
    source_file: Path
    line_number: int
    tool: str
    ts: str | None = None


class AuditIndex:
    """Dict-backed index of audit_id → AuditEntryRef built from audit/*.jsonl."""

    def __init__(self, entries: dict[str, AuditEntryRef]) -> None:
        self._entries = entries

    @classmethod
    def from_dir(cls, audit_dir: Path) -> AuditIndex:
        """Scan all *.jsonl under audit_dir (non-recursive) and build the index."""
        entries: dict[str, AuditEntryRef] = {}
        if not audit_dir.exists():
            return cls(entries)

        for jsonl_path in sorted(audit_dir.glob("*.jsonl")):
            try:
                text = jsonl_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                _LOG.warning("Could not read audit file %s for index build", jsonl_path)
                continue

            for lineno, raw in enumerate(text.splitlines(), start=1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    _LOG.debug("Malformed JSON at %s line %d — skipping", jsonl_path.name, lineno)
                    continue
                if not isinstance(record, dict):
                    continue
                audit_id = record.get("audit_id")
                if not isinstance(audit_id, str) or not audit_id:
                    continue
                tool = record.get("tool") or ""
                ts = record.get("ts") or record.get("timestamp") or None
                if audit_id not in entries:
                    entries[audit_id] = AuditEntryRef(
                        audit_id=audit_id,
                        source_file=jsonl_path,
                        line_number=lineno,
                        tool=str(tool),
                        ts=str(ts) if ts is not None else None,
                    )

        return cls(entries)

    def contains(self, audit_id: str) -> bool:
        return audit_id in self._entries

    def lookup(self, audit_id: str) -> AuditEntryRef | None:
        return self._entries.get(audit_id)

    def __len__(self) -> int:
        return len(self._entries)


__all__ = ["AuditEntryRef", "AuditIndex"]
