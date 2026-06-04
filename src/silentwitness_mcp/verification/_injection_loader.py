"""YAML loader + compiled-regex cache for the injection pattern catalog.

Loaded once at module import; ``reload()`` re-reads the file and re-compiles
the patterns so the Epic 4 server-level SIGHUP handler can ship new
patterns without a restart.

The pattern catalog lives at :data:`_PATTERNS_PATH`. Each entry has:
* ``id`` — stable wire identifier (used in audit log + tests).
* ``regex`` — Python ``re`` source (typically prefixed with ``(?i)`` for
  case-insensitive matching).
* ``description`` — human-readable rationale; not consumed by the
  sanitizer but visible to analysts grepping the YAML.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import Any

import yaml

_PATTERNS_PATH: Path = Path(__file__).parent / "_injection_patterns.yaml"


@dataclass(frozen=True, slots=True)
class InjectionPattern:
    """A compiled injection pattern entry. Frozen so the cache can't drift."""

    id: str
    pattern: Pattern[str]
    description: str


class InjectionCatalogError(ValueError):
    """Raised when the YAML catalog is missing required fields or shape."""


_patterns_cache: list[InjectionPattern] | None = None


def get_patterns(*, force_reload: bool = False) -> list[InjectionPattern]:
    """Return the cached pattern list, loading on first call.

    ``force_reload=True`` re-reads the YAML and re-compiles — used by
    :func:`reload` and by tests that need to inject a hot-swap pattern.
    """
    global _patterns_cache
    if _patterns_cache is None or force_reload:
        _patterns_cache = _load(_PATTERNS_PATH)
    return _patterns_cache


def reload() -> list[InjectionPattern]:
    """Re-read the catalog from disk. Returns the fresh list."""
    return get_patterns(force_reload=True)


def _load(path: Path) -> list[InjectionPattern]:
    """Parse + compile. Raises :class:`InjectionCatalogError` on shape issues."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise InjectionCatalogError(f"{path}: top-level must be a mapping")
    if raw.get("schema_version") != 1:
        raise InjectionCatalogError(
            f"{path}: schema_version must be 1, got {raw.get('schema_version')!r}"
        )
    entries = raw.get("patterns")
    if not isinstance(entries, list) or not entries:
        raise InjectionCatalogError(f"{path}: 'patterns' must be a non-empty list")
    out: list[InjectionPattern] = []
    seen_ids: set[str] = set()
    for idx, entry in enumerate(entries):
        out.append(_compile_entry(path, idx, entry, seen_ids))
    return out


def _compile_entry(path: Path, idx: int, entry: Any, seen_ids: set[str]) -> InjectionPattern:
    if not isinstance(entry, dict):
        raise InjectionCatalogError(f"{path}: patterns[{idx}] must be a mapping")
    for field in ("id", "regex", "description"):
        if field not in entry or not isinstance(entry[field], str):
            raise InjectionCatalogError(
                f"{path}: patterns[{idx}] missing or non-str field {field!r}"
            )
    pattern_id = entry["id"]
    if pattern_id in seen_ids:
        raise InjectionCatalogError(
            f"{path}: duplicate pattern id {pattern_id!r} at patterns[{idx}]"
        )
    seen_ids.add(pattern_id)
    try:
        compiled = re.compile(entry["regex"])
    except re.error as exc:
        raise InjectionCatalogError(
            f"{path}: patterns[{idx}] regex {entry['regex']!r} failed to compile: {exc}"
        ) from exc
    return InjectionPattern(id=pattern_id, pattern=compiled, description=entry["description"])


__all__ = [
    "InjectionCatalogError",
    "InjectionPattern",
    "get_patterns",
    "reload",
]
