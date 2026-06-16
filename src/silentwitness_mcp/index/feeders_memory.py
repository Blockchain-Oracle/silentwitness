"""Per-plugin pure mappers — Volatility 3 JSON rows -> :class:`IndexRecord`.

The driver (:mod:`silentwitness_mcp.index.ingest_memory`) runs vol3 as a subprocess
per plugin and hands the parsed JSON list to the mapper for that plugin. The mappers
are pure, kwarg-only, and unit-testable against captured vol3 fixtures
(:file:`tests/fixtures/vol3/*.json`) — same per-plugin / pure-mapper / one-place-per-
artifact pattern as the disk-side :mod:`silentwitness_mcp.index.feeders_*`.

Provenance: ``source_tool="vol:<plugin>"`` (so :func:`list_detections` and the
citation gate can tell a memory row apart from a disk row); ``artifact_path`` is the
image's prepared-relative path plus a ``#vol:<plugin>`` fragment so a citation
pin-points the plugin that produced the row.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from typing import Any, Final, Protocol

from silentwitness_mcp.index._feeder_util import MAX_TEXT
from silentwitness_mcp.index.store import IndexRecord


class Mapper(Protocol):
    """The contract every per-plugin mapper shares (enforced at type-check time).

    Conform with a module-level ``_: Mapper = my_mapper`` line so a renamed keyword
    (e.g. ``sha256`` -> ``image_sha256``) is caught by mypy rather than failing at
    runtime inside the driver loop. Mirrors the :class:`Feeder` pattern in
    :mod:`silentwitness_mcp.index._feeder_util`."""

    def __call__(
        self,
        rows: Iterable[dict[str, Any]],
        *,
        artifact_path: str,
        audit_id: str,
        host: str,
        sha256: str,
    ) -> Iterator[IndexRecord]: ...


# Standard memory inventory used by the CLI's default index profile. These produce
# useful process/network corroboration without the expensive all-process VAD scan.
STANDARD_PLUGINS: Final[tuple[str, ...]] = (
    "windows.pslist.PsList",
    "windows.cmdline.CmdLine",
    "windows.netscan.NetScan",
    "windows.psscan.PsScan",
)

# Deep memory scan used when explicitly requested. Keep expensive scanners last so
# a slow malware sweep cannot delay basic process/network memory rows.
DEEP_PLUGINS: Final[tuple[str, ...]] = (
    *STANDARD_PLUGINS,
    "windows.malware.malfind.Malfind",
)

PLUGINS: Final[tuple[str, ...]] = DEEP_PLUGINS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _short_plugin(plugin: str) -> str:
    """``windows.pslist.PsList`` -> ``pslist`` — the short form used in source_tool."""
    return plugin.rsplit(".", 1)[-1].lower()


def _row_text(prefix: str, **fields: Any) -> str:
    """``Process pid=4 ppid=0 name=System`` — stable space-joined ``key=value`` line.

    Skips ``None`` so an absent column doesn't read as the literal string ``None`` in
    the FTS-indexed text (which would be searchable and misleading)."""
    parts = [prefix]
    for key, value in fields.items():
        if value is None or value == "":
            continue
        parts.append(f"{key}={value}")
    return " ".join(parts)


def _make_record(
    *,
    text: str,
    plugin: str,
    artifact_path: str,
    host: str,
    ts: str,
    audit_id: str,
    sha256: str,
) -> IndexRecord:
    return IndexRecord(
        text=text[:MAX_TEXT],
        source_tool=f"vol:{_short_plugin(plugin)}",
        artifact_path=f"{artifact_path}#vol:{_short_plugin(plugin)}",
        host=host,
        ts=ts,
        audit_id=audit_id,
        sha256=sha256,
    )


# ---------------------------------------------------------------------------
# Mappers — one per plugin.
# ---------------------------------------------------------------------------


def _pslist_to_records(
    rows: Iterable[dict[str, Any]],
    *,
    artifact_path: str,
    audit_id: str,
    host: str,
    sha256: str,
) -> Iterator[IndexRecord]:
    for row in rows:
        text = _row_text(
            "Process",
            pid=row.get("PID"),
            ppid=row.get("PPID"),
            name=row.get("ImageFileName"),
            threads=row.get("Threads"),
            wow64=row.get("Wow64"),
            exited=row.get("ExitTime"),
        )
        yield _make_record(
            text=text,
            plugin="windows.pslist.PsList",
            artifact_path=artifact_path,
            host=host,
            ts=str(row.get("CreateTime") or ""),
            audit_id=audit_id,
            sha256=sha256,
        )


def _cmdline_to_records(
    rows: Iterable[dict[str, Any]],
    *,
    artifact_path: str,
    audit_id: str,
    host: str,
    sha256: str,
) -> Iterator[IndexRecord]:
    for row in rows:
        args = row.get("Args")
        # Skip processes vol3 couldn't read a cmdline for — their PID still shows in
        # pslist; emitting a row with no Args adds noise without investigative value.
        if not args:
            continue
        text = _row_text(
            "Cmdline",
            pid=row.get("PID"),
            process=row.get("Process"),
            args=args,
        )
        yield _make_record(
            text=text,
            plugin="windows.cmdline.CmdLine",
            artifact_path=artifact_path,
            host=host,
            ts="",  # cmdline is a snapshot — no per-row timestamp
            audit_id=audit_id,
            sha256=sha256,
        )


def _netscan_to_records(
    rows: Iterable[dict[str, Any]],
    *,
    artifact_path: str,
    audit_id: str,
    host: str,
    sha256: str,
) -> Iterator[IndexRecord]:
    for row in rows:
        text = _row_text(
            "NetConn",
            proto=row.get("Proto"),
            local=f"{row.get('LocalAddr')}:{row.get('LocalPort')}"
            if row.get("LocalAddr")
            else None,
            foreign=f"{row.get('ForeignAddr')}:{row.get('ForeignPort')}"
            if row.get("ForeignAddr")
            else None,
            state=row.get("State"),
            pid=row.get("PID"),
            owner=row.get("Owner"),
        )
        yield _make_record(
            text=text,
            plugin="windows.netscan.NetScan",
            artifact_path=artifact_path,
            host=host,
            ts=str(row.get("Created") or ""),
            audit_id=audit_id,
            sha256=sha256,
        )


def _malfind_to_records(
    rows: Iterable[dict[str, Any]],
    *,
    artifact_path: str,
    audit_id: str,
    host: str,
    sha256: str,
) -> Iterator[IndexRecord]:
    """Malfind emits one row per suspicious VAD region (executable + private memory).

    The Hexdump column is large and noisy for FTS; we keep the structural fields
    (process, address, protection, tag) since those are what an analyst correlates.
    ``ts=""`` because a VAD has no per-row allocation timestamp in vol3's malfind
    output — same rationale as cmdline (snapshot, not a temporal event)."""
    for row in rows:
        text = _row_text(
            "Malfind",
            pid=row.get("PID"),
            process=row.get("Process"),
            start=row.get("Start VPN") or row.get("Start"),
            end=row.get("End VPN") or row.get("End"),
            tag=row.get("Tag"),
            protection=row.get("Protection"),
            commit=row.get("CommitCharge"),
            private=row.get("PrivateMemory"),
        )
        yield _make_record(
            text=text,
            plugin="windows.malware.malfind.Malfind",
            artifact_path=artifact_path,
            host=host,
            ts="",
            audit_id=audit_id,
            sha256=sha256,
        )


def _psscan_to_records(
    rows: Iterable[dict[str, Any]],
    *,
    artifact_path: str,
    audit_id: str,
    host: str,
    sha256: str,
) -> Iterator[IndexRecord]:
    """Same shape as pslist but found by pool scanning (catches unlinked / hidden procs).

    A process visible in psscan but absent from pslist is a strong rootkit signal —
    keeping them as separate ``vol:psscan`` rows lets a query / detector compare."""
    for row in rows:
        text = _row_text(
            "ProcessScan",
            pid=row.get("PID"),
            ppid=row.get("PPID"),
            name=row.get("ImageFileName"),
            threads=row.get("Threads"),
            exited=row.get("ExitTime"),
        )
        yield _make_record(
            text=text,
            plugin="windows.psscan.PsScan",
            artifact_path=artifact_path,
            host=host,
            ts=str(row.get("CreateTime") or ""),
            audit_id=audit_id,
            sha256=sha256,
        )


# Compile-time conformance — a renamed kwarg in any mapper fails mypy here, not at
# runtime inside the driver loop. Same pattern as the disk-side Feeder protocol.
_: Mapper = _pslist_to_records
_: Mapper = _cmdline_to_records  # type: ignore[no-redef]
_: Mapper = _netscan_to_records  # type: ignore[no-redef]
_: Mapper = _malfind_to_records  # type: ignore[no-redef]
_: Mapper = _psscan_to_records  # type: ignore[no-redef]

MAPPERS: Final[Mapping[str, Mapper]] = {
    "windows.pslist.PsList": _pslist_to_records,
    "windows.cmdline.CmdLine": _cmdline_to_records,
    "windows.netscan.NetScan": _netscan_to_records,
    "windows.malware.malfind.Malfind": _malfind_to_records,
    "windows.psscan.PsScan": _psscan_to_records,
}

# PLUGINS and MAPPERS keys must agree — a plugin without a mapper would silently
# show up as a "no mapper registered" failure on every run instead of being caught
# here, at import.
if set(MAPPERS) != set(PLUGINS):  # load-time invariant
    raise AssertionError("PLUGINS and MAPPERS keys diverged")


__all__ = ["DEEP_PLUGINS", "MAPPERS", "PLUGINS", "STANDARD_PLUGINS", "Mapper"]
