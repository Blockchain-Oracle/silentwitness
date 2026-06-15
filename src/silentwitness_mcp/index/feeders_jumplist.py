"""Jumplist feeder — AutomaticDestinations jumplists into :class:`IndexRecord` rows.

An ``*.automaticDestinations-ms`` file is an OLE compound document whose numbered streams
are each a serialised LNK structure (the recent items an app pinned/opened); the jumplist
filename is the app's AppID hash — an opaque identifier we carry verbatim in
``artifact_path`` but do NOT resolve to a program name (no AppID lookup table here), so a
jumplist row ties *one application's recent-file list* to the files it touched. We unpack
the container with ``olefile`` (BSD) and decode each LNK stream with the shared LNK mapper,
so a jumplist row carries the same target/network-share/timestamp fields as a Recent
``.lnk``.

CustomDestinations (``*.customDestinations-ms``) use a different, non-OLE concatenated-LNK
layout and are intentionally out of scope here (tracked as a follow-up) rather than parsed
half-way. The ``DestList`` metadata stream (MRU ordering) is skipped — its per-entry target
paths are already recovered from the LNK streams it indexes.

``jumplist_records`` drives ``olefile`` on a real container; the per-stream LNK mapping is
covered by the shared, unit-tested ``_lnk_to_record``.
"""

from __future__ import annotations

import io
import logging
from collections.abc import Iterator
from pathlib import Path

from silentwitness_mcp.index._feeder_util import Feeder, FeederStats, sha256_file
from silentwitness_mcp.index.feeders_lnk import _lnk_to_record
from silentwitness_mcp.index.store import IndexRecord

_LOG = logging.getLogger(__name__)


def jumplist_records(
    path: Path,
    *,
    audit_id: str,
    host: str = "",
    source_path: str | None = None,
    stats: FeederStats | None = None,
) -> Iterator[IndexRecord]:
    """Stream one row per LNK stream in an AutomaticDestinations jumplist.

    ``olefile`` + ``LnkParse3`` are imported lazily. A non-OLE input is skipped (counted);
    a single unreadable/undecodable stream is skipped without aborting the container."""
    import olefile

    cite = source_path if source_path is not None else str(path)
    sha = sha256_file(path)
    if not olefile.isOleFile(str(path)):
        if stats is not None:
            stats.skip("jumplist_not_ole")
        return

    import LnkParse3

    ole = olefile.OleFileIO(str(path))
    try:
        for stream in ole.listdir():
            name = stream[-1]
            if name.lower() == "destlist":
                continue
            try:
                raw = ole.openstream(stream).read()
                parsed = LnkParse3.lnk_file(io.BytesIO(raw)).get_json()
            except Exception as exc:  # malformed embedded LNK — skip just this stream
                _LOG.debug("jumplist: skipped stream %s in %s: %s", name, path.name, exc)
                if stats is not None:
                    stats.skip("jumplist_bad_stream")
                continue
            record = _lnk_to_record(
                parsed,
                artifact_path=f"{cite}#{name}",
                audit_id=audit_id,
                host=host,
                sha256=sha,
                source_tool="jumplist:auto",
            )
            if record is None:
                if stats is not None:
                    stats.skip("jumplist_empty_stream")
                continue
            yield record
    finally:
        ole.close()


# Compile-time assertion that the feeder still matches the shared contract.
_: Feeder = jumplist_records

__all__ = ["jumplist_records"]
