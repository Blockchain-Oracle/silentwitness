"""Registry feeder — parse Windows registry hives into :class:`IndexRecord` rows.

Uses ``regipy`` (pure-Python, MIT) and its validated plugins (Run keys, services,
shimcache, shellbags, UserAssist, network profiles, …). Each plugin entry becomes one
searchable row, so a keyword query (``run``, a service name, a path) surfaces the
persistence / execution evidence behind the "how was it stolen" question.

Evidence integrity: plugins are run **individually with per-plugin isolation** — one
plugin that raises is logged and skipped so it can't zero out the whole hive (regipy's
own ``run_relevant_plugins`` only isolates ``ModuleNotFoundError``, not other parse
errors). A hive that fails to *open* is allowed to propagate so the ingest orchestrator
counts it as a failure rather than silently yielding nothing.

``_entry_to_record`` is a pure, unit-tested mapper that flattens one plugin entry into a
searchable line; ``registry_hive_records`` runs regipy over a real hive (forensics box).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from silentwitness_mcp.index._feeder_util import MAX_TEXT, Feeder, sha256_file
from silentwitness_mcp.index.store import IndexRecord

_LOG = logging.getLogger(__name__)

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
    entry: dict[str, Any], *, plugin: str, hive_path: str, audit_id: str, host: str, sha256: str
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
        text=text[:MAX_TEXT],
        source_tool=f"regipy:{plugin}",
        artifact_path=hive_path,
        host=host,
        ts=ts,
        audit_id=audit_id,
        sha256=sha256,
    )


def registry_hive_records(
    path: Path, *, audit_id: str, host: str = "", source_path: str | None = None
) -> Iterator[IndexRecord]:
    """Stream :class:`IndexRecord`s from every validated regipy plugin over one hive.

    ``regipy`` is imported lazily (forensics extra). Each plugin runs in isolation — a
    plugin that raises is logged and skipped. A hive that cannot be opened raises (the
    caller records it as a failed artifact)."""
    from regipy.plugins.utils import PLUGINS, is_plugin_validated
    from regipy.registry import RegistryHive

    cite = source_path if source_path is not None else str(path)
    sha = sha256_file(path)
    hive = RegistryHive(str(path))  # open failure propagates -> counted as a failed artifact
    for plugin_class in PLUGINS:
        plugin = plugin_class(hive, as_json=True)
        if not is_plugin_validated(plugin.NAME):
            continue
        try:
            if not plugin.can_run():
                continue
            plugin.run()
            entries = plugin.entries
        except Exception as exc:  # one bad plugin must not zero the whole hive
            _LOG.warning("regipy plugin %s failed on %s: %s", plugin.NAME, path.name, exc)
            continue
        if isinstance(entries, dict):
            rows: list[Any] = [entries]
        elif isinstance(entries, list):
            rows = entries
        else:
            rows = []
        for entry in rows:
            if not isinstance(entry, dict):
                continue
            rec = _entry_to_record(
                entry, plugin=plugin.NAME, hive_path=cite, audit_id=audit_id, host=host, sha256=sha
            )
            if rec is not None:
                yield rec


# Compile-time assertion that the feeder still matches the shared contract.
_: Feeder = registry_hive_records

__all__ = ["registry_hive_records"]
