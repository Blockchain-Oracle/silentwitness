"""LNK feeder — Windows shortcut (.lnk) files into :class:`IndexRecord` rows.

Recent-folder ``.lnk`` shortcuts are written when a user *opens* a file, recording the
target's full path, command-line arguments, working directory, the originating machine's
NetBIOS name and (for files opened over the network) the UNC share — the single best
on-disk answer to "what file did the user open, and where did it live." Parsed with
``LnkParse3`` (pure-Python, MIT).

The header carries the *target* file's creation/access/modification (write) times at the
moment the shortcut was written (three FILETIMEs — not an MFT change time); we surface the
modified time (falling back to accessed/creation) as the row ``ts`` so a timeline query
lands the access near when it happened.

``_lnk_to_record`` is a pure mapper (also reused by the jumplist feeder for the LNK
streams embedded in an AutomaticDestinations jumplist); ``lnk_records`` drives LnkParse3
on a real file. A shortcut that resolves to neither a target path nor a network share
carries no investigative signal and is skipped (counted in ``stats``).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from silentwitness_mcp.index._feeder_util import MAX_TEXT, Feeder, FeederStats, sha256_file
from silentwitness_mcp.index.store import IndexRecord


def _iso(value: Any) -> str:
    """ISO-8601 string from a LnkParse3 time value (datetime or str), or "" if absent."""
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        return value
    try:
        return str(value.isoformat())
    except (AttributeError, ValueError):
        return ""


def _best_target(data: dict[str, Any], link_info: dict[str, Any]) -> str:
    """The richest available target path: local base (+ suffix), else the relative path."""
    local = str(link_info.get("local_base_path") or "").strip()
    if local:
        suffix = str(link_info.get("common_path_suffix") or "").strip()
        return f"{local}{suffix}" if suffix else local
    return str(data.get("relative_path") or "").strip()


def _network_share(link_info: dict[str, Any]) -> str:
    """The UNC share name for a target opened over the network, or "" for a local target."""
    cnrl = link_info.get("common_network_relative_link")
    if not isinstance(cnrl, dict):
        return ""
    return str(cnrl.get("net_name") or "").strip()


def _lnk_to_record(
    parsed: dict[str, Any],
    *,
    artifact_path: str,
    audit_id: str,
    host: str,
    sha256: str,
    source_tool: str = "lnk",
) -> IndexRecord | None:
    """Map one LnkParse3 ``get_json()`` dict to a searchable row, or None if empty.

    ``source_tool``/``artifact_path`` are parameterised so the jumplist feeder can reuse
    this for the LNK streams it unpacks from an AutomaticDestinations container."""
    data = parsed.get("data") or {}
    header = parsed.get("header") or {}
    link_info = parsed.get("link_info") or {}

    target = _best_target(data, link_info)
    share = _network_share(link_info)
    if not target and not share:
        return None

    parts = [f"LNK target={target}"] if target else ["LNK"]
    if share:
        parts.append(f"network_share={share}")
    for label, key in (
        ("args", "command_line_arguments"),
        ("workdir", "working_directory"),
        ("machine", "machine_identifier"),
    ):
        value = str(data.get(key) or "").strip()
        if value:
            parts.append(f"{label}={value}")
    ts = (
        _iso(header.get("modified_time"))
        or _iso(header.get("accessed_time"))
        or _iso(header.get("creation_time"))
    )
    return IndexRecord(
        text=" ".join(parts)[:MAX_TEXT],
        source_tool=source_tool,
        artifact_path=artifact_path,
        host=host,
        ts=ts,
        audit_id=audit_id,
        sha256=sha256,
    )


def lnk_records(
    path: Path,
    *,
    audit_id: str,
    host: str = "",
    source_path: str | None = None,
    stats: FeederStats | None = None,
) -> Iterator[IndexRecord]:
    """Stream one :class:`IndexRecord` for a ``.lnk`` file. ``LnkParse3`` is imported lazily."""
    import LnkParse3

    cite = source_path if source_path is not None else str(path)
    sha = sha256_file(path)
    with path.open("rb") as handle:
        parsed = LnkParse3.lnk_file(handle).get_json()
    record = _lnk_to_record(parsed, artifact_path=cite, audit_id=audit_id, host=host, sha256=sha)
    if record is None:
        if stats is not None:
            stats.skip("lnk_no_target")
        return
    yield record


# Compile-time assertion that the feeder still matches the shared contract.
_: Feeder = lnk_records

__all__ = ["lnk_records"]
