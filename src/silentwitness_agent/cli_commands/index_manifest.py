"""Freshness manifest for ``silentwitness index`` reruns.

The case index is derived data. If the registered prepared artifacts, indexing
profile, and relevant parser settings have not changed, rebuilding millions of
SQLite/FTS rows only wastes demo and analyst time. The manifest records a stable
fingerprint of those inputs after a successful build so later reruns can skip
work unless the operator passes ``--force``.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from silentwitness_common.atomic_io import write_json_atomic
from silentwitness_common.types import EvidenceRecord

_MANIFEST_PATH: Final = Path(".silentwitness") / "index-manifest.json"
_SCHEMA_VERSION: Final = 1
_INDEXER_SIGNATURE: Final = "index-v3-bulk-manifest-20260617"


def _canonical(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def build_expected_manifest(
    *,
    case_id: str,
    host: str,
    memory_profile: str,
    memory_plugins: Sequence[str],
    artifacts: Sequence[EvidenceRecord],
) -> dict[str, Any]:
    """Return the input fingerprint payload for the current index request."""
    inputs = {
        "schema_version": _SCHEMA_VERSION,
        "indexer_signature": _INDEXER_SIGNATURE,
        "case_id": case_id,
        "host": host,
        "memory_profile": memory_profile,
        "memory_plugins": list(memory_plugins),
        "settings": {
            "evtx_tolerant_fallback": os.environ.get("SILENTWITNESS_EVTX_TOLERANT_FALLBACK", ""),
            "malfind_max_pids": os.environ.get("SILENTWITNESS_VOL3_MALFIND_MAX_PIDS", ""),
            "parser_timeout": os.environ.get("SILENTWITNESS_PARSER_TIMEOUT_SEC", ""),
            "vol3_timeout": os.environ.get("SILENTWITNESS_VOL3_TIMEOUT_SEC", ""),
        },
        "artifacts": sorted(
            (
                {
                    "path": str(rec.path),
                    "type": rec.type.value,
                    "sha256": rec.sha256,
                    "size_bytes": rec.size_bytes,
                }
                for rec in artifacts
            ),
            key=lambda item: (item["path"], item["type"]),
        ),
    }
    return {
        "fingerprint": hashlib.sha256(_canonical(inputs).encode()).hexdigest(),
        "inputs": inputs,
    }


def index_manifest_path(case_dir: Path) -> Path:
    return case_dir / _MANIFEST_PATH


def current_index_row_count(case_dir: Path) -> int | None:
    """Return the current record count, or ``None`` if the DB is absent/unreadable."""
    db_path = case_dir / "index.db"
    if not db_path.is_file():
        return None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            return int(conn.execute("SELECT COUNT(*) FROM record").fetchone()[0])
        finally:
            conn.close()
    except sqlite3.Error:
        return None


def index_is_current(case_dir: Path, expected: dict[str, Any]) -> tuple[bool, int | None]:
    """Return ``(is_current, row_count)`` for the existing index."""
    rows = current_index_row_count(case_dir)
    if rows is None or rows <= 0:
        return False, rows
    path = index_manifest_path(case_dir)
    try:
        actual = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, rows
    return actual.get("fingerprint") == expected.get("fingerprint"), rows


def write_index_manifest(
    case_dir: Path,
    expected: dict[str, Any],
    *,
    rows: int,
    summary: dict[str, Any],
) -> None:
    """Persist the successful build fingerprint and compact build summary."""
    document = {
        **expected,
        "rows": rows,
        "summary": summary,
        "written_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    path = index_manifest_path(case_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, document, mode=0o644)


__all__ = [
    "build_expected_manifest",
    "current_index_row_count",
    "index_is_current",
    "index_manifest_path",
    "write_index_manifest",
]
