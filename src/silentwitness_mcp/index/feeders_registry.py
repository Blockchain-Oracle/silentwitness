"""Registry feeder — parse Windows registry hives into :class:`IndexRecord` rows.

Uses ``regipy`` (pure-Python, MIT) and its own plugin knowledge: ``run_relevant_plugins``
runs every plugin relevant to the hive type (Run keys, services, shimcache, shellbags,
UserAssist, network profiles, …) and returns structured entries. Each entry becomes one
searchable row, so a keyword query (``run``, a service name, a path) surfaces the
persistence / execution evidence behind the "how was it stolen" question.

``_entry_to_record`` is a pure, unit-tested mapper that flattens one plugin entry into a
searchable line; ``registry_hive_records`` runs regipy over a real hive (forensics box).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from silentwitness_mcp.index._feeder_util import sha256_file
from silentwitness_mcp.index.store import IndexRecord

_LOG = logging.getLogger(__name__)

# Cap per-entry text so a pathological registry blob can't bloat the DB / a query.
_MAX_TEXT = 8192
# Keys regipy plugins use for the event time, in priority order.
_TS_KEYS = ("timestamp", "last_write", "last_modified", "last_write_timestamp", "modified")


def _flatten(obj: Any, key: str | None = None) -> list[str]:
    """Flatten a nested plugin entry into ``key=value`` (or bare ``value``) tokens.

    Nested dicts keep their inner key names (the outer key is dropped); list elements
    inherit their parent key. Scalars become ``key=value`` or a bare value at the root."""
    if isinstance(obj, dict):
        tokens: list[str] = []
        for inner_key, value in obj.items():
            tokens.extend(_flatten(value, str(inner_key)))
        return tokens
    if isinstance(obj, list):
        tokens = []
        for element in obj:
            tokens.extend(_flatten(element, key))
        return tokens
    scalar = str(obj)
    if not scalar:
        return []
    return [f"{key}={scalar}" if key else scalar]


def _entry_to_record(
    entry: dict[str, Any], *, plugin: str, hive_path: str, audit_id: str, host: str
) -> IndexRecord | None:
    """Map one regipy plugin entry to an :class:`IndexRecord`, or None if empty.

    The text is every flattened field (names, paths, values) so the entry is fully
    searchable; the event time is lifted from whichever ``_TS_KEYS`` field is present."""
    tokens = _flatten(entry)
    text = " ".join(tokens).strip()
    if not text:
        return None
    ts = ""
    for ts_key in _TS_KEYS:
        value = entry.get(ts_key)
        if value:
            ts = str(value)
            break
    return IndexRecord(
        text=text[:_MAX_TEXT],
        source_tool=f"regipy:{plugin}",
        artifact_path=hive_path,
        host=host,
        ts=ts,
        audit_id=audit_id,
    )


def registry_hive_records(
    path: Path, *, audit_id: str, host: str = "", source_path: str | None = None
) -> Iterator[IndexRecord]:
    """Stream :class:`IndexRecord`s from every relevant regipy plugin over one hive.

    ``regipy`` is imported lazily (forensics extra). A plugin that raises is logged and
    skipped so one bad plugin can't abort the hive."""
    from regipy.plugins.utils import run_relevant_plugins
    from regipy.registry import RegistryHive

    cite = source_path if source_path is not None else str(path)
    sha = sha256_file(path)
    try:
        hive = RegistryHive(str(path))
        results: dict[str, Any] = run_relevant_plugins(hive, as_json=True)
    except Exception as exc:  # regipy raises bare Exceptions on malformed hives
        _LOG.warning("regipy failed to open %s: %s", path.name, exc)
        return
    for plugin_name, data in results.items():
        entries = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            rec = _entry_to_record(
                entry, plugin=plugin_name, hive_path=cite, audit_id=audit_id, host=host
            )
            if rec is not None:
                yield IndexRecord(
                    text=rec.text,
                    source_tool=rec.source_tool,
                    artifact_path=rec.artifact_path,
                    host=rec.host,
                    ts=rec.ts,
                    audit_id=rec.audit_id,
                    sha256=sha,
                )


__all__ = ["registry_hive_records"]
