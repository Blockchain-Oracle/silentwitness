"""Zeek-backed PCAP feeder for the evidence index.

The agent is only allowed to query ``index.db``. PCAP evidence therefore has to
be converted into searchable rows during ``silentwitness index``; otherwise a
clean Nitroba run registers the capture but leaves the investigator with an
empty index.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path

from silentwitness_mcp.index._feeder_util import MAX_TEXT, Feeder, FeederStats
from silentwitness_mcp.index.store import IndexRecord

_ZEEK_LOGS = (
    "conn.log",
    "dns.log",
    "http.log",
    "smtp.log",
    "ssl.log",
    "files.log",
    "notice.log",
    "weird.log",
)
_SKIP_BINARY_FIELD = "-"


class PcapFeederError(RuntimeError):
    """Raised when Zeek cannot process a PCAP."""


def _line_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _parse_zeek_log(
    log_path: Path,
    *,
    log_name: str,
    audit_id: str,
    host: str,
    artifact_path: str,
    stats: FeederStats | None,
) -> Iterator[IndexRecord]:
    fields: list[str] | None = None
    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.rstrip("\n")
                if not line:
                    continue
                if line.startswith("#fields\t"):
                    fields = line.split("\t")[1:]
                    continue
                if line.startswith("#"):
                    continue
                if fields is None:
                    if stats is not None:
                        stats.skip("zeek_missing_fields_header")
                    continue
                values = line.split("\t")
                if len(values) != len(fields):
                    if stats is not None:
                        stats.skip("zeek_field_count_mismatch")
                    continue
                row = {
                    key: value
                    for key, value in zip(fields, values, strict=True)
                    if value and value != _SKIP_BINARY_FIELD
                }
                if not row:
                    continue
                ts = row.get("ts", "")
                parts = [f"{key}={value}" for key, value in row.items()]
                text = f"ZEEK {log_name} " + " ".join(parts)
                yield IndexRecord(
                    text=text[:MAX_TEXT],
                    source_tool=f"zeek:{log_name}",
                    artifact_path=artifact_path,
                    host=host,
                    ts=ts,
                    audit_id=audit_id,
                    sha256=_line_sha256(text),
                )
    except OSError as exc:
        raise PcapFeederError(f"cannot read Zeek log {log_path}: {exc}") from exc


def pcap_records(
    path: Path,
    *,
    audit_id: str,
    host: str = "",
    source_path: str | None = None,
    stats: FeederStats | None = None,
) -> Iterator[IndexRecord]:
    """Run Zeek over ``path`` and stream selected logs into index records."""
    zeek = shutil.which("zeek")
    if zeek is None:
        raise PcapFeederError("zeek executable not found on PATH")
    cite = source_path or path.name
    with tempfile.TemporaryDirectory(prefix="silentwitness-zeek-") as tmp:
        workdir = Path(tmp)
        try:
            proc = subprocess.run(  # noqa: S603 - argv-only Zeek invocation; no shell.
                [zeek, "-C", "-r", str(path)],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise PcapFeederError(f"zeek timed out after {exc.timeout}s on {path.name}") from exc
        except OSError as exc:
            raise PcapFeederError(f"zeek failed to start: {exc}") from exc
        if proc.returncode != 0:
            stderr = (proc.stderr or proc.stdout or "").strip().splitlines()
            detail = stderr[-1] if stderr else f"exit code {proc.returncode}"
            raise PcapFeederError(f"zeek failed on {path.name}: {detail}")
        for log_name in _ZEEK_LOGS:
            log_path = workdir / log_name
            if not log_path.exists():
                continue
            yield from _parse_zeek_log(
                log_path,
                log_name=log_name.removesuffix(".log"),
                audit_id=audit_id,
                host=host,
                artifact_path=f"{cite}/{log_name}",
                stats=stats,
            )


_: Feeder = pcap_records

__all__ = ["PcapFeederError", "pcap_records"]
