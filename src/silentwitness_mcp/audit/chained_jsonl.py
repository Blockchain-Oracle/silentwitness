"""Hash-chained JSONL append helper for non-tool audit streams.

``AuditLogger`` owns MCP tool-call rows and audit-id sequencing. Agent hooks,
critic verdicts, sanitizer events, and hypothesis transitions are separate audit
streams, so they cannot safely create another ``AuditLogger`` for the same case.
This helper gives those streams the same per-file hash chain without touching
audit-id allocation.
"""

from __future__ import annotations

import fcntl
import json
from pathlib import Path
from typing import Any

from silentwitness_common.atomic_io import append_jsonl_line
from silentwitness_mcp.audit.chain import compute_record_hash


def append_chained_jsonl(
    path: Path, record: dict[str, Any], *, mode: int = 0o644
) -> dict[str, Any]:
    """Append ``record`` to ``path`` with ``prev_record_hash`` and ``record_hash``.

    A sibling lock file serializes read-last-hash + append, so concurrent writers
    do not fork the per-file chain. The output uses ``ensure_ascii=True`` to keep
    Unicode line separators escaped before ``append_jsonl_line`` validates the
    physical JSONL line.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.chain.lock")
    with lock_path.open("ab") as lock_fh:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        try:
            prev_hash = _last_record_hash(path)
            entry = {
                k: v for k, v in record.items() if k not in {"prev_record_hash", "record_hash"}
            }
            entry["prev_record_hash"] = prev_hash
            entry["record_hash"] = compute_record_hash(prev_hash, entry)
            append_jsonl_line(
                path,
                json.dumps(entry, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
                mode=mode,
            )
            return entry
        finally:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)


def _last_record_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    last_hash: str | None = None
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("record_hash"), str):
                last_hash = obj["record_hash"]
    return last_hash


__all__ = ["append_chained_jsonl"]
