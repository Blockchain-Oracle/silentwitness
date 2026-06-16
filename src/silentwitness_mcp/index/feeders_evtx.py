"""EVTX feeder — parse Windows Event Logs into :class:`IndexRecord` rows.

Hybrid parser, chosen by measurement on the real ROCBA EVTX:

* **Fast path — Rust ``evtx`` (``PyEvtxParser``)**: parses the large majority of the
  case's logs in seconds.
* **Opt-in tolerant fallback — pure-Python ``python-evtx`` (``Evtx``)**: a tail of
  files have malformed chunks that crash *both* the Rust parser and libevtx/pyevtx.
  ``python-evtx`` can recover some of them, but can also monopolize a demo run on badly
  damaged files, so it is enabled only when ``SILENTWITNESS_EVTX_TOLERANT_FALLBACK=1``.

The default path is fast and bounded: try Rust per file, buffer its output, and record a
structured artifact failure when a malformed file cannot be parsed by Rust. A missing
Rust parser (``ImportError``) is re-raised rather than masked as a slow fallback. Both
parsers yield per-record XML, so the single pure mapper handles both when deep recovery
is explicitly requested.

``_event_xml_to_record`` is a pure, unit-tested mapper; the file readers are exercised
on the forensic box (both parsers installed via the forensics extra).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from pathlib import Path
from xml.etree.ElementTree import Element, ParseError

from defusedxml.ElementTree import fromstring

from silentwitness_mcp.index._feeder_util import MAX_TEXT, Feeder, FeederStats, sha256_file
from silentwitness_mcp.index.store import IndexRecord

_LOG = logging.getLogger(__name__)
_TOLERANT_FALLBACK_ENV = "SILENTWITNESS_EVTX_TOLERANT_FALLBACK"

# Salient identity fields appended to a detection row so 18k brute-force hits aren't
# indistinguishable — the account/host/IP/command is what makes a hit actionable and
# searchable. Order is the display order; absent fields are skipped.
_DETECTION_CONTEXT_FIELDS = (
    "TargetUserName",
    "SubjectUserName",
    "IpAddress",
    "WorkstationName",
    "LogonType",
    "NewProcessName",
    "Image",
    "CommandLine",
    "ScriptBlockText",
)


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


def _event_fields(system: dict[str, str], root: Element) -> dict[str, str]:
    """The flat field dict a Sigma rule matches against: System fields + EventData pairs.

    EventData ``Name=value`` pairs win over System keys on a name clash (the event-specific
    value is the one a detection rule means)."""
    fields = dict(system)
    fields.update(_event_data_pairs(root))
    return fields


def _record_from_root(
    root: Element,
    system: dict[str, str],
    eid: str,
    *,
    path: str,
    sha256: str,
    audit_id: str,
    host: str,
) -> IndexRecord:
    """Build the searchable event row from an already-parsed event (channel, fields, ts)."""
    channel = system.get("Channel", "")
    parts = [
        f"EventID={eid}",
        channel,
        f"provider={system.get('Provider', '')}",
        f"computer={system.get('Computer', '')}",
    ]
    parts.extend(f"{name}={value}" for name, value in _event_data_pairs(root))
    text = " ".join(p for p in parts if p).strip()
    return IndexRecord(
        text=text[:MAX_TEXT],
        source_tool=f"evtx:{channel}" if channel else "evtx",
        artifact_path=path,
        host=host,
        ts=system.get("TimeCreated", ""),
        audit_id=audit_id,
        sha256=sha256,
    )


def _detection_records(
    fields: dict[str, str],
    system: dict[str, str],
    eid: str,
    *,
    path: str,
    sha256: str,
    audit_id: str,
    host: str,
) -> Iterator[IndexRecord]:
    """Yield a ``sigma:<level>`` row per Sigma rule that fires on this event.

    Detection hits seed the agent's opening context (it starts from named alerts, not blind
    search); ``artifact_path`` is the same EventRecordID citation as the event row so a hit
    is traceable back to its source event."""
    from silentwitness_mcp.detect.sigma_eval import evaluate_event

    channel = system.get("Channel", "")
    ts = system.get("TimeCreated", "")
    context = " ".join(
        f"{name}={fields[name]}" for name in _DETECTION_CONTEXT_FIELDS if fields.get(name)
    )
    try:
        detections = evaluate_event(fields)
    except Exception as exc:  # a detection-engine fault must not cost the event evidence
        _LOG.warning("evtx: sigma evaluation failed on an event (%s) — event row kept", exc)
        return
    for det in detections:
        tags = ",".join(det.tags)
        text = (
            f"SIGMA DETECTION level={det.level} rule={det.title} "
            f"tags={tags} event_id={eid} channel={channel} {context}"
        ).strip()
        yield IndexRecord(
            text=text[:MAX_TEXT],
            source_tool=f"sigma:{det.level}",
            artifact_path=path,
            host=host,
            ts=ts,
            audit_id=audit_id,
            sha256=sha256,
        )


def _records_from_xml(
    xml: str, *, source_path: str, sha256: str, audit_id: str, host: str
) -> Iterator[IndexRecord]:
    """Parse one rendered EVTX event once and yield its event row + any Sigma detections.

    Drops events with no ``EventID`` (malformed render) or unparseable XML. The event text
    is a single compact, FTS-searchable line (EventID, channel, provider, computer, and
    every ``EventData`` value); ``artifact_path`` carries the EventRecordID so a citation
    resolves to the exact event."""
    try:
        root = fromstring(xml)
    except ParseError:
        return
    system = _find_system(root)
    eid = system.get("EventID")
    if not eid:
        return
    record_id = system.get("EventRecordID", "")
    path = f"{source_path}#{record_id}" if record_id else source_path
    yield _record_from_root(
        root, system, eid, path=path, sha256=sha256, audit_id=audit_id, host=host
    )
    yield from _detection_records(
        _event_fields(system, root),
        system,
        eid,
        path=path,
        sha256=sha256,
        audit_id=audit_id,
        host=host,
    )


def _event_xml_to_record(
    xml: str, *, source_path: str, sha256: str, audit_id: str, host: str
) -> IndexRecord | None:
    """Map one rendered EVTX event to its event :class:`IndexRecord`, or None if unusable.

    Thin wrapper over :func:`_records_from_xml` returning just the event row (no detection
    rows) — kept for the pure-mapper unit tests."""
    try:
        root = fromstring(xml)
    except ParseError:
        return None
    system = _find_system(root)
    eid = system.get("EventID")
    if not eid:
        return None
    record_id = system.get("EventRecordID", "")
    path = f"{source_path}#{record_id}" if record_id else source_path
    return _record_from_root(
        root, system, eid, path=path, sha256=sha256, audit_id=audit_id, host=host
    )


def _rust_evtx_records(
    path: Path, *, sha: str, cite: str, audit_id: str, host: str
) -> Iterator[IndexRecord]:
    """Fast path: parse with Rust ``evtx``. Raises if the file has a bad chunk."""
    from evtx import PyEvtxParser  # lazy: forensics extra only

    for record in PyEvtxParser(str(path)).records():
        if record is None:  # the binding types records() as Optional; never None in practice
            continue
        yield from _records_from_xml(
            record["data"], source_path=cite, sha256=sha, audit_id=audit_id, host=host
        )


def _python_evtx_records(
    path: Path, *, sha: str, cite: str, audit_id: str, host: str, stats: FeederStats | None
) -> Iterator[IndexRecord]:
    """Tolerant fallback: pure-Python ``python-evtx`` reads malformed-chunk files."""
    from Evtx.Evtx import Evtx  # lazy: forensics extra only

    with Evtx(str(path)) as log:
        for record in log.records():
            try:
                xml = record.xml()
            except Exception:  # one corrupt record must not kill the whole file
                _LOG.debug("evtx: skipped unrenderable record in %s", path)
                if stats is not None:
                    stats.skip("evtx_unrenderable_record")
                continue
            yield from _records_from_xml(
                xml, source_path=cite, sha256=sha, audit_id=audit_id, host=host
            )


def _tolerant_fallback_enabled() -> bool:
    value = os.environ.get(_TOLERANT_FALLBACK_ENV, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def evtx_file_records(
    path: Path,
    *,
    audit_id: str,
    host: str = "",
    source_path: str | None = None,
    stats: FeederStats | None = None,
) -> Iterator[IndexRecord]:
    """Stream one :class:`IndexRecord` per event in a single ``.evtx`` file.

    Tries the fast Rust parser, buffering its output so that a mid-stream chunk error
    records a whole-artifact failure without partial+duplicate emission. Set
    ``SILENTWITNESS_EVTX_TOLERANT_FALLBACK=1`` for the slower python-evtx fallback.
    ``source_path`` overrides the stored citation path (default: the on-disk path)."""
    sha = sha256_file(path)
    cite = source_path if source_path is not None else str(path)
    try:
        records = list(_rust_evtx_records(path, sha=sha, cite=cite, audit_id=audit_id, host=host))
    except ImportError:
        raise  # a missing Rust parser is an environment defect — surface it, don't mask it
    except Exception as exc:  # malformed EVTX: record failure unless deep recovery is explicit
        if stats is not None:
            stats.skip("evtx_rust_failed_file")
        if not _tolerant_fallback_enabled():
            raise RuntimeError(
                f"rust EVTX parser failed on {path.name}; tolerant python-evtx fallback "
                f"disabled (set {_TOLERANT_FALLBACK_ENV}=1 for deep recovery): {exc}"
            ) from exc
        _LOG.warning("evtx: rust parser failed on %s (%s) — using python-evtx", path.name, exc)
        if stats is not None:
            stats.skip("evtx_python_fallback_file")
        yield from _python_evtx_records(
            path, sha=sha, cite=cite, audit_id=audit_id, host=host, stats=stats
        )
        return
    yield from records


# Compile-time assertion that the feeder still matches the shared contract.
_: Feeder = evtx_file_records

__all__ = ["evtx_file_records"]
