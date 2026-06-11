"""Shared subprocess infrastructure for the network tool family
(zeek_run, suricata_run) — architecture §4.2,
context/.raw-design-research/03 §Network forensics line 160.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import time
from enum import StrEnum
from pathlib import Path
from typing import Final

_LOG = logging.getLogger(__name__)

# Zeek is NOT pre-installed on SIFT 2026.
# context/.raw-design-research/03 §"Tools NEEDED but NOT pre-installed" line 217.
# OpenSUSE security:zeek package installs to /opt/zeek/bin/zeek; install.sh
# creates a /usr/local/bin/zeek symlink. Source-built installs also use /opt/zeek/.
ZEEK_BIN: Final = Path("/usr/local/bin/zeek")
ZEEK_BIN_FALLBACK: Final = Path("/opt/zeek/bin/zeek")

# Suricata is NOT pre-installed on SIFT 2026; install.sh adds it via apt (Noble universe).
# context/.raw-design-research/03 §"Tools NEEDED but NOT pre-installed" line 218.
SURICATA_BIN: Final = Path("/usr/bin/suricata")
SURICATA_BIN_FALLBACK: Final = Path("/usr/local/bin/suricata")

_DEFAULT_NETWORK_TIMEOUT_S: Final = 900.0
_TERMINATE_GRACE_S: Final = 5.0


def get_zeek_bin() -> Path | None:
    if ZEEK_BIN.exists():
        return ZEEK_BIN
    if ZEEK_BIN_FALLBACK.exists():
        return ZEEK_BIN_FALLBACK
    return None


def get_suricata_bin() -> Path | None:
    if SURICATA_BIN.exists():
        return SURICATA_BIN
    if SURICATA_BIN_FALLBACK.exists():
        return SURICATA_BIN_FALLBACK
    return None


class NetworkFailureReason(StrEnum):
    EVIDENCE_NOT_REGISTERED = "EVIDENCE_NOT_REGISTERED"
    EVIDENCE_TAMPERED = "EVIDENCE_TAMPERED"
    MOUNT_NOT_RO_NOEXEC_NOSUID = "MOUNT_NOT_RO_NOEXEC_NOSUID"
    ZEEK_NOT_INSTALLED = "ZEEK_NOT_INSTALLED"
    SURICATA_NOT_INSTALLED = "SURICATA_NOT_INSTALLED"
    TOOL_FAILED = "TOOL_FAILED"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    OUTPUT_PARSE_FAILED = "OUTPUT_PARSE_FAILED"
    NO_LOGS_PRODUCED = "NO_LOGS_PRODUCED"


@dataclasses.dataclass(frozen=True, slots=True)
class _NetworkResult:
    exit_code: int
    stdout: bytes
    stderr: bytes
    elapsed_ms: float


async def _run_zeek(
    zeek_bin: Path,
    pcap_path: Path,
    out_dir: Path,
    *,
    timeout_s: float = _DEFAULT_NETWORK_TIMEOUT_S,
) -> _NetworkResult:
    t0 = time.monotonic()
    argv = [str(zeek_bin), "-r", str(pcap_path), "-C"]
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(out_dir),  # Zeek writes log files to cwd, not a --log-path flag
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except TimeoutError:
        try:
            proc.terminate()
        except ProcessLookupError:
            pass  # process exited between timeout and SIGTERM — proceed to wait
        try:
            await asyncio.wait_for(proc.wait(), timeout=_TERMINATE_GRACE_S)
        except TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(proc.wait(), timeout=_TERMINATE_GRACE_S)
            except TimeoutError:
                _LOG.error("zeek process did not die after SIGKILL; pid=%s", proc.pid)
        raise TimeoutError(f"zeek timed out after {timeout_s}s") from None
    elapsed = (time.monotonic() - t0) * 1000.0
    return _NetworkResult(
        exit_code=proc.returncode if proc.returncode is not None else -1,
        stdout=stdout_b,
        stderr=stderr_b,
        elapsed_ms=elapsed,
    )


async def _run_suricata(
    suricata_bin: Path,
    pcap_path: Path,
    rules_path: Path,
    out_dir: Path,
    *,
    timeout_s: float = _DEFAULT_NETWORK_TIMEOUT_S,
) -> _NetworkResult:
    t0 = time.monotonic()
    argv = [
        str(suricata_bin),
        "-r",
        str(pcap_path),
        "-S",
        str(rules_path),
        "-l",
        str(out_dir),
        "--runmode",
        "single",  # deterministic event ordering for reproducible SHA256
        "-k",
        "none",  # skip checksum validation; many evidence pcaps have bad sums
    ]
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except TimeoutError:
        try:
            proc.terminate()
        except ProcessLookupError:
            pass  # process exited between timeout and SIGTERM — proceed to wait
        try:
            await asyncio.wait_for(proc.wait(), timeout=_TERMINATE_GRACE_S)
        except TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass  # process exited between SIGTERM and SIGKILL — proceed to wait
            try:
                await asyncio.wait_for(proc.wait(), timeout=_TERMINATE_GRACE_S)
            except TimeoutError:
                _LOG.error("suricata process did not die after SIGKILL; pid=%s", proc.pid)
        raise TimeoutError(f"suricata timed out after {timeout_s}s") from None
    elapsed = (time.monotonic() - t0) * 1000.0
    return _NetworkResult(
        exit_code=proc.returncode if proc.returncode is not None else -1,
        stdout=stdout_b,
        stderr=stderr_b,
        elapsed_ms=elapsed,
    )


def _tally_eve_events(eve_bytes: bytes) -> tuple[dict[str, int], int]:
    """Parse EVE JSONL bytes; returns (event_type_counts, malformed_line_count).

    Caller reads the file once and passes the bytes — avoids TOCTOU between
    the SHA256 computation and the parse step.
    """
    counts: dict[str, int] = {}
    malformed = 0
    for raw_line in eve_bytes.decode("utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            _LOG.error("_tally_eve_events: malformed JSON line (first 100 chars: %r)", line[:100])
            continue
        if isinstance(parsed, dict):
            et = parsed.get("event_type", "unknown")
            counts[et] = counts.get(et, 0) + 1
        else:
            malformed += 1
            _LOG.error("_tally_eve_events: non-object JSON line skipped: %r", line[:100])
    return counts, malformed


__all__ = [
    "SURICATA_BIN",
    "SURICATA_BIN_FALLBACK",
    "NetworkFailureReason",
    "_NetworkResult",
    "_run_suricata",
    "_run_zeek",
    "_tally_eve_events",
    "get_suricata_bin",
    "get_zeek_bin",
]
