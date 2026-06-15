"""PowerShell transcript feeder — ``PowerShell_transcript.*.txt`` into :class:`IndexRecord`.

When PowerShell transcription is enabled, every interactive/scripted session is logged to a
plain-text transcript carrying a header (start time, username, machine, host application)
followed by the verbatim commands and their output — the on-disk answer to "what commands
did the actor run," e.g. an ``Invoke-WebRequest``/``rclone``/cloud-upload exfil step. No
binary parser is needed; the value is the searchable command text itself.

``_parse_header``/``_start_iso``/``_transcript_to_record`` are pure (unit-tested);
``pstranscript_records`` reads the file and decodes it (transcripts are UTF-8/UTF-16,
sometimes BOM-prefixed). The whole transcript body is indexed (capped to ``MAX_TEXT``) so a
keyword query for a cloud host or a cmdlet name lands the session.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from silentwitness_mcp.index._feeder_util import MAX_TEXT, Feeder, FeederStats, sha256_file
from silentwitness_mcp.index.store import IndexRecord

# Header field labels PowerShell writes, in "Label: value" form, within the opening block.
_HEADER_KEYS = ("Start time", "Username", "RunAs User", "Machine", "Host Application")
# Only the opening block carries the header; cap the scan so a huge transcript body isn't
# walked line-by-line looking for fields that only appear up top.
_HEADER_SCAN_LINES = 40


def _decode(raw: bytes) -> str:
    """Decode transcript bytes, tolerating UTF-8(-BOM)/UTF-16; latin-1 as a lossless last resort."""
    for encoding in ("utf-8-sig", "utf-16", "utf-8"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1", errors="replace")


def _parse_header(text: str) -> dict[str, str]:
    """Pull the ``Label: value`` header fields from a transcript's opening block."""
    fields: dict[str, str] = {}
    for line in text.splitlines()[:_HEADER_SCAN_LINES]:
        for key in _HEADER_KEYS:
            prefix = f"{key}: "
            if line.startswith(prefix):
                fields[key] = line[len(prefix) :].strip()
    return fields


def _start_iso(raw: str) -> str:
    """Convert a ``Start time`` (``YYYYMMDDhhmmss``) to ISO-8601, or "" if unparseable."""
    raw = raw.strip()
    if len(raw) == 14 and raw.isdigit():
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}T{raw[8:10]}:{raw[10:12]}:{raw[12:14]}"
    return ""


def _transcript_to_record(
    *,
    header: dict[str, str],
    body: str,
    ps_path: str,
    audit_id: str,
    host: str,
    sha256: str,
) -> IndexRecord:
    """Build one searchable row carrying the transcript header + (capped) command body."""
    user = header.get("Username", "")
    host_app = header.get("Host Application", "")
    text = f"PowerShell transcript user={user} host_app={host_app} {body}"
    return IndexRecord(
        text=text[:MAX_TEXT],
        source_tool="powershell:transcript",
        artifact_path=ps_path,
        host=host,
        ts=_start_iso(header.get("Start time", "")),
        audit_id=audit_id,
        sha256=sha256,
    )


def pstranscript_records(
    path: Path,
    *,
    audit_id: str,
    host: str = "",
    source_path: str | None = None,
    stats: FeederStats | None = None,
) -> Iterator[IndexRecord]:
    """Stream one :class:`IndexRecord` for a PowerShell transcript file."""
    cite = source_path if source_path is not None else str(path)
    sha = sha256_file(path)
    text = _decode(path.read_bytes())
    yield _transcript_to_record(
        header=_parse_header(text),
        body=text,
        ps_path=cite,
        audit_id=audit_id,
        host=host,
        sha256=sha,
    )


# Compile-time assertion that the feeder still matches the shared contract.
_: Feeder = pstranscript_records

__all__ = ["pstranscript_records"]
