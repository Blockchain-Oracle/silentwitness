"""EVTX feeder — parse Windows Event Logs into :class:`IndexRecord` rows.

Hybrid parser, chosen by measurement on the real ROCBA EVTX:

* **Fast path — Rust ``evtx`` (``PyEvtxParser``)**: parses the large majority of the
  case's logs in seconds.
* **Tolerant fallback — pure-Python ``python-evtx`` (``Evtx``)**: a tail of files have
  malformed chunks that crash *both* the Rust parser (a ``Failed to parse chunk
  header``-class error) and libevtx/pyevtx — and therefore plaso's libevtx-backed
  ``winevtx`` parser, which extracts 0 events. ``python-evtx`` reads them anyway.

So we get full recall *and* a fast build: try Rust per file, buffer its output, and on
any parse error fall back to ``python-evtx`` for that file (no partial+duplicate
emission). A missing Rust parser (``ImportError``) is re-raised rather than masked as a
slow fallback. Both parsers yield per-record XML, so the single pure mapper handles both.

``_event_xml_to_record`` is a pure, unit-tested mapper; the file readers are exercised
on the forensic box (both parsers installed via the forensics extra).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from xml.etree.ElementTree import Element, ParseError

from defusedxml.ElementTree import fromstring

from silentwitness_mcp.index._feeder_util import MAX_TEXT, Feeder, sha256_file
from silentwitness_mcp.index.store import IndexRecord

_LOG = logging.getLogger(__name__)


def _local(tag: object) -> str:
    """Local element name with any ``{namespace}`` prefix stripped."""
    return str(tag).rsplit("}", 1)[-1]


def _find_system(root: Element) -> dict[str, str]:
    """Pull the salient ``<System>`` fields (namespace-agnostic) into a flat dict."""
    out: dict[str, str] = {}
    system = next((c for c in root if _local(c.tag) == "System"), None)
    if system is None:
        return out
    for child in system:
        name = _local(child.tag)
        if name == "Provider":
            out["Provider"] = child.attrib.get("Name", "")
        elif name == "TimeCreated":
            out["TimeCreated"] = child.attrib.get("SystemTime", "")
        elif child.text and child.text.strip():
            out[name] = child.text.strip()
    return out


def _event_data_pairs(root: Element) -> list[tuple[str, str]]:
    """Flatten ``<EventData>``/``<UserData>`` ``<Data Name=..>value</Data>`` pairs."""
    pairs: list[tuple[str, str]] = []
    for container in root:
        if _local(container.tag) not in ("EventData", "UserData"):
            continue
        for data in container.iter():
            if _local(data.tag) != "Data":
                continue
            value = (data.text or "").strip()
            if not value:
                continue
            pairs.append((data.attrib.get("Name", "Data"), value))
    return pairs


def _event_xml_to_record(
    xml: str, *, source_path: str, sha256: str, audit_id: str, host: str
) -> IndexRecord | None:
    """Map one rendered EVTX event to an :class:`IndexRecord`, or None if unusable.

    Drops events with no ``EventID`` (malformed render) or unparseable XML. The text
    is a single compact, FTS-searchable line: the EventID, channel, provider, computer,
    and every ``EventData`` value (usernames, IPs, paths) so a keyword query surfaces
    the event. ``artifact_path`` carries the EventRecordID so a citation resolves to the
    exact event."""
    try:
        root = fromstring(xml)
    except ParseError:
        return None
    system = _find_system(root)
    eid = system.get("EventID")
    if not eid:
        return None
    channel = system.get("Channel", "")
    parts = [
        f"EventID={eid}",
        channel,
        f"provider={system.get('Provider', '')}",
        f"computer={system.get('Computer', '')}",
    ]
    parts.extend(f"{name}={value}" for name, value in _event_data_pairs(root))
    text = " ".join(p for p in parts if p).strip()
    record_id = system.get("EventRecordID", "")
    path = f"{source_path}#{record_id}" if record_id else source_path
    return IndexRecord(
        text=text[:MAX_TEXT],
        source_tool=f"evtx:{channel}" if channel else "evtx",
        artifact_path=path,
        host=host,
        ts=system.get("TimeCreated", ""),
        audit_id=audit_id,
        sha256=sha256,
    )


def _rust_evtx_records(
    path: Path, *, sha: str, cite: str, audit_id: str, host: str
) -> Iterator[IndexRecord]:
    """Fast path: parse with Rust ``evtx``. Raises if the file has a bad chunk."""
    from evtx import PyEvtxParser  # lazy: forensics extra only

    for record in PyEvtxParser(str(path)).records():
        rec = _event_xml_to_record(
            record["data"], source_path=cite, sha256=sha, audit_id=audit_id, host=host
        )
        if rec is not None:
            yield rec


def _python_evtx_records(
    path: Path, *, sha: str, cite: str, audit_id: str, host: str
) -> Iterator[IndexRecord]:
    """Tolerant fallback: pure-Python ``python-evtx`` reads malformed-chunk files."""
    from Evtx.Evtx import Evtx  # lazy: forensics extra only

    with Evtx(str(path)) as log:
        for record in log.records():
            try:
                xml = record.xml()
            except Exception:  # one corrupt record must not kill the whole file
                _LOG.debug("evtx: skipped unrenderable record in %s", path)
                continue
            rec = _event_xml_to_record(
                xml, source_path=cite, sha256=sha, audit_id=audit_id, host=host
            )
            if rec is not None:
                yield rec


def evtx_file_records(
    path: Path, *, audit_id: str, host: str = "", source_path: str | None = None
) -> Iterator[IndexRecord]:
    """Stream one :class:`IndexRecord` per event in a single ``.evtx`` file.

    Tries the fast Rust parser, buffering its output so that a mid-stream chunk error
    falls back cleanly to tolerant ``python-evtx`` (no partial+duplicate emission).
    ``source_path`` overrides the stored citation path (default: the on-disk path)."""
    sha = sha256_file(path)
    cite = source_path if source_path is not None else str(path)
    try:
        records = list(_rust_evtx_records(path, sha=sha, cite=cite, audit_id=audit_id, host=host))
    except ImportError:
        raise  # a missing Rust parser is an environment defect — surface it, don't mask it
    except Exception as exc:  # a real parse error → tolerant python-evtx fallback
        _LOG.warning("evtx: rust parser failed on %s (%s) — using python-evtx", path.name, exc)
        yield from _python_evtx_records(path, sha=sha, cite=cite, audit_id=audit_id, host=host)
        return
    yield from records


# Compile-time assertion that the feeder still matches the shared contract.
_: Feeder = evtx_file_records

__all__ = ["evtx_file_records"]
