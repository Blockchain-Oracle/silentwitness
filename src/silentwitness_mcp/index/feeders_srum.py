"""SRUM feeder — System Resource Usage Monitor (SRUDB.dat) into :class:`IndexRecord`s.

SRUM's Network Data Usage table records **per-application bytes sent/received** — the
single best on-disk answer to "what was stolen / where was it transferred." Each row
ties an app (resolved via ``SruDbIdMapTable``) to a byte count and a timestamp, so a
keyword query (an app name, ``bytes_sent``) surfaces large outbound transfers.

Parsed with ``pyesedb`` (libesedb, permissive) — note this is the *libesedb* stack, not
libevtx, so it reads the ROCBA ESE database cleanly. The ``TimeStamp`` column is an OLE
automation date (an 8-byte double, days since 1899-12-30), decoded by ``_ole_to_iso``.

``_ole_to_iso`` and ``_net_row_to_record`` are pure, unit-tested; ``srum_records`` opens
a real SRUDB.dat (forensics box).
"""

from __future__ import annotations

import logging
import struct
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from silentwitness_mcp.index._feeder_util import MAX_TEXT, Feeder, sha256_file
from silentwitness_mcp.index.store import IndexRecord

_LOG = logging.getLogger(__name__)

# Network Data Usage Monitor table GUID (the per-app bytes-sent/received table).
_NET_TABLE = "{973F5D5C-1D90-4944-BE8E-24B94231A174}"
_IDMAP_TABLE = "SruDbIdMapTable"
# OLE automation date epoch.
_OLE_EPOCH = datetime(1899, 12, 30, tzinfo=UTC)


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


def _build_appid_map(esedb_file: Any) -> dict[int, str]:
    """Map ``SruDbIdMapTable`` IdIndex -> app/path string (UTF-16LE ``IdBlob``)."""
    appmap: dict[int, str] = {}
    table = _get_table(esedb_file, _IDMAP_TABLE)
    if table is None:
        return appmap
    for ridx in range(table.number_of_records):
        try:
            record = table.get_record(ridx)
            id_index = record.get_value_data_as_integer(1)
            blob = record.get_value_data(2)
        except OSError:
            continue
        if id_index is None or not blob:
            continue
        try:
            appmap[id_index] = blob.decode("utf-16-le").rstrip("\x00").strip()
        except (UnicodeDecodeError, ValueError):
            appmap[id_index] = blob[:32].hex()
    return appmap


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
            return
        for ridx in range(table.number_of_records):
            try:
                record = table.get_record(ridx)
                ts = _ole_to_iso(record.get_value_data(1))
                app_id = record.get_value_data_as_integer(2)
                sent = record.get_value_data_as_integer(7) or 0
                recvd = record.get_value_data_as_integer(8) or 0
                luid = record.get_value_data_as_integer(4) or 0
            except OSError as exc:  # a single unreadable page must not kill the table
                _LOG.debug("srum: skipped record %d: %s", ridx, exc)
                continue
            yield _net_row_to_record(
                app=appmap.get(app_id, f"appid:{app_id}"),
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
    finally:
        esedb_file.close()


# Compile-time assertion that the feeder still matches the shared contract.
_: Feeder = srum_records

__all__ = ["srum_records"]
