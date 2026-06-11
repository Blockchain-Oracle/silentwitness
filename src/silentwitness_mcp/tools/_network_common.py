"""Shared subprocess infrastructure for the network tool family
(zeek_run, suricata_run) — architecture §4.2,
context/.raw-design-research/03 §Network forensics line 160.

:func:`_run_zeek` wraps Zeek offline pcap replay.
:func:`_run_suricata` (story-suricata-run) will share :class:`_NetworkResult`.
"""

from __future__ import annotations

import asyncio
import dataclasses
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

_DEFAULT_NETWORK_TIMEOUT_S: Final = 900.0
_TERMINATE_GRACE_S: Final = 5.0


def get_zeek_bin() -> Path | None:
    if ZEEK_BIN.exists():
        return ZEEK_BIN
    if ZEEK_BIN_FALLBACK.exists():
        return ZEEK_BIN_FALLBACK
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
    """Subprocess result bundle shared by zeek_run and suricata_run."""

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


__all__ = [
    "NetworkFailureReason",
    "_NetworkResult",
    "_run_zeek",
    "get_zeek_bin",
]
