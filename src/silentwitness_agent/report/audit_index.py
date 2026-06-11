"""AuditIndex — lightweight per-validation-pass index of audit/*.jsonl entries.

Built fresh on every validate call (audit JSONL files are append-only during
an investigation; a cached index would miss entries added after construction).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

_LOG = logging.getLogger(__name__)

_AUDIT_ID_PATTERN = r"^sift-[a-z0-9]+-\d{8}-\d{3,}$"


class AuditEntryRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    audit_id: str = Field(min_length=1, pattern=_AUDIT_ID_PATTERN)
    source_file: Path
    line_number: int = Field(ge=1)
    tool: str = Field(default="")
    ts: str | None = Field(
        default=None,
        description="ISO-8601 timestamp string from the audit record, or None if absent",
    )


class AuditIndex:
    """Plain class (not Pydantic) to allow mutable construction in from_dir.

    Callers should treat instances as read-only after construction.
    """

    def __init__(self, entries: dict[str, AuditEntryRef]) -> None:
        self._entries = entries

    @classmethod
    def from_dir(cls, audit_dir: Path) -> AuditIndex:
        """Scan all *.jsonl under audit_dir (non-recursive) and build the index."""
        entries: dict[str, AuditEntryRef] = {}
        if not audit_dir.exists():
            _LOG.warning(
                "Audit directory %s does not exist — index will be empty. "
                "All verify refs will fail validation.",
                audit_dir,
            )
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
                    _LOG.warning(
                        "Malformed JSON at %s line %d — skipping. Raw: %.120r",
                        jsonl_path.name,
                        lineno,
                        raw,
                    )
                    continue
                if not isinstance(record, dict):
                    _LOG.warning(
                        "Unexpected non-dict JSON at %s line %d (type=%s) — skipping",
                        jsonl_path.name,
                        lineno,
                        type(record).__name__,
                    )
                    continue
                audit_id = record.get("audit_id")
                if not isinstance(audit_id, str) or not audit_id:
                    _LOG.debug(
                        "Record at %s line %d has no audit_id — skipping",
                        jsonl_path.name,
                        lineno,
                    )
                    continue
                tool = record.get("tool") or ""
                ts = record.get("ts") or record.get("timestamp") or None
                if audit_id not in entries:
                    try:
                        entries[audit_id] = AuditEntryRef(
                            audit_id=audit_id,
                            source_file=jsonl_path,
                            line_number=lineno,
                            tool=str(tool),
                            ts=str(ts) if ts is not None else None,
                        )
                    except Exception:
                        _LOG.debug(
                            "Skipping malformed audit_id %r at %s line %d",
                            audit_id,
                            jsonl_path.name,
                            lineno,
                        )

        return cls(entries)

    def contains(self, audit_id: str) -> bool:
        return audit_id in self._entries

    def lookup(self, audit_id: str) -> AuditEntryRef | None:
        return self._entries.get(audit_id)

    def audit_ids(self) -> frozenset[str]:
        """Return the set of all indexed audit IDs (read-only snapshot)."""
        return frozenset(self._entries)

    def __len__(self) -> int:
        return len(self._entries)


__all__ = ["AuditEntryRef", "AuditIndex"]
