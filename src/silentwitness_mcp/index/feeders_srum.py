"""SRUM feeder — System Resource Usage Monitor (SRUDB.dat) into :class:`IndexRecord`s.

SRUM's Network Data Usage table records **per-application bytes sent/received** — the
single best on-disk answer to "what was stolen / where was it transferred." Each row
ties an app (resolved via ``SruDbIdMapTable``) to a byte count and a timestamp, so a
keyword query (an app name, ``bytes_sent``) surfaces large outbound transfers.

Parsed with ``pyesedb`` (libesedb, permissive) — note this is the *libesedb* stack, not
libevtx, so it reads the ROCBA ESE database cleanly. On this Win10 SRUDB.dat the network
table ``TimeStamp`` is an OLE automation date (8-byte double, days since 1899-12-30):
empirically verified — decoding the column as a double yields the 2020 incident dates,
whereas reading it as a 64-bit integer yields garbage. The column ordinals below are an
undocumented invariant of the SRUM schema version.

The pure helpers (``_ole_to_iso``, ``_decode_idblob``, ``_appid_map_from_rows``,
``_net_row_to_record``) are unit-tested; ``srum_records`` drives a real SRUDB.dat
(forensics box). A missing *primary* (network) table raises :class:`SrumError` so the
ingest counts it as a failed artifact rather than presenting a silent "no exfil"; a
single unreadable record is skipped (best-effort) with a per-artifact warning.
"""

from __future__ import annotations

import logging
import struct
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from silentwitness_mcp.index._feeder_util import MAX_TEXT, Feeder, sha256_file
from silentwitness_mcp.index.store import IndexRecord

_LOG = logging.getLogger(__name__)

# Network Data Usage Monitor table (the per-app bytes-sent/received table); _NET_TABLE
# is the single source of truth for the GUID.
_NET_TABLE = "{973F5D5C-1D90-4944-BE8E-24B94231A174}"
_IDMAP_TABLE = "SruDbIdMapTable"
# OLE automation date epoch.
_OLE_EPOCH = datetime(1899, 12, 30, tzinfo=UTC)


class SrumError(Exception):
    """Raised on a structural SRUM problem (e.g. the primary table is absent)."""


def _ole_to_iso(raw: bytes | None) -> str:
    """Decode an 8-byte little-endian OLE automation date to ISO-8601, or "" if invalid."""
    if not raw or len(raw) < 8:
        return ""
    try:
        days = struct.unpack("<d", raw[:8])[0]
    except struct.error:
        return ""
    if not days or days != days or abs(days) > 400_000:  # NaN / absurd -> unusable
        return ""
    try:
        return (_OLE_EPOCH + timedelta(days=days)).isoformat()
    except (OverflowError, ValueError):
        return ""


def _net_row_to_record(
    *,
    app: str,
    bytes_sent: int,
    bytes_recvd: int,
    interface_luid: int,
    ts: str,
    srudb_path: str,
    record_index: int,
    audit_id: str,
    host: str,
    sha256: str,
) -> IndexRecord:
    """Build one searchable SRUM network-usage row."""
    text = (
        f"SRUM network_usage app={app} bytes_sent={bytes_sent} "
        f"bytes_recvd={bytes_recvd} interface_luid={interface_luid}"
    )
    return IndexRecord(
        text=text[:MAX_TEXT],
        source_tool="srum:network_usage",
        artifact_path=f"{srudb_path}#{record_index}",
        host=host,
        ts=ts,
        audit_id=audit_id,
        sha256=sha256,
    )


def _decode_idblob(blob: bytes) -> str:
    """Decode a ``SruDbIdMapTable`` IdBlob (UTF-16LE app/path), hex on failure."""
    try:
        return blob.decode("utf-16-le").rstrip("\x00").strip()
    except (UnicodeDecodeError, ValueError):
        return blob[:32].hex()


def _appid_map_from_rows(rows: Iterable[tuple[int | None, bytes | None]]) -> dict[int, str]:
    """Build the IdIndex -> app string map, skipping null index/blob rows."""
    appmap: dict[int, str] = {}
    for id_index, blob in rows:
        if id_index is None or not blob:
            continue
        appmap[id_index] = _decode_idblob(blob)
    return appmap


def _build_appid_map(esedb_file: Any) -> dict[int, str]:
    """Map ``SruDbIdMapTable`` IdIndex -> app/path string. Best-effort per record."""
    table = _get_table(esedb_file, _IDMAP_TABLE)
    if table is None:
        return {}

    def _rows() -> Iterator[tuple[int | None, bytes | None]]:
        for ridx in range(table.number_of_records):
            try:
                record = table.get_record(ridx)
                yield record.get_value_data_as_integer(1), record.get_value_data(2)
            except (OSError, ValueError) as exc:  # pyesedb raises ValueError on type/width
                _LOG.debug("srum: skipped idmap record %d: %s", ridx, exc)

    return _appid_map_from_rows(_rows())


def _get_table(esedb_file: Any, name: str) -> Any:
    """Return the named ESE table, or None if absent."""
    for i in range(esedb_file.number_of_tables):
        table = esedb_file.get_table(i)
        if table.name == name:
            return table
    return None


def srum_records(
    path: Path, *, audit_id: str, host: str = "", source_path: str | None = None
) -> Iterator[IndexRecord]:
    """Stream per-app network-usage rows from a SRUDB.dat. ``pyesedb`` is imported lazily."""
    import pyesedb

    cite = source_path if source_path is not None else str(path)
    sha = sha256_file(path)
    esedb_file = pyesedb.file()
    esedb_file.open(str(path))
    try:
        appmap = _build_appid_map(esedb_file)
        table = _get_table(esedb_file, _NET_TABLE)
        if table is None:
            # A missing primary table is a structural anomaly, NOT "no exfil" — raise so
            # the ingest records a failed artifact instead of a silent empty result.
            present = [esedb_file.get_table(i).name for i in range(esedb_file.number_of_tables)]
            raise SrumError(
                f"SRUM network table {_NET_TABLE} not found in {cite}; tables present: {present}"
            )
        skipped = 0
        for ridx in range(table.number_of_records):
            try:
                record = table.get_record(ridx)
                ts = _ole_to_iso(record.get_value_data(1))
                app_id = record.get_value_data_as_integer(2)
                sent = record.get_value_data_as_integer(7) or 0
                recvd = record.get_value_data_as_integer(8) or 0
                luid = record.get_value_data_as_integer(4) or 0
            except (OSError, ValueError):  # pyesedb raises ValueError; skip just this row
                skipped += 1
                continue
            app = appmap.get(app_id, f"appid:{app_id if app_id is not None else 'unknown'}")
            yield _net_row_to_record(
                app=app,
                bytes_sent=sent,
                bytes_recvd=recvd,
                interface_luid=luid,
                ts=ts,
                srudb_path=cite,
                record_index=ridx,
                audit_id=audit_id,
                host=host,
                sha256=sha,
            )
        if skipped:
            _LOG.warning("srum: skipped %d unreadable record(s) in %s", skipped, cite)
    finally:
        esedb_file.close()


# Compile-time assertion that the feeder still matches the shared contract.
_: Feeder = srum_records

__all__ = ["srum_records"]
