"""Shared dotnet subprocess infrastructure for the log/network tool family
(parse_evtx, hayabusa_csv_timeline, chainsaw_hunt) — architecture §4.2 rows 17-19,
context/.raw-design-research/03-sift-2026-tool-catalog-verified.md §EZ Tools.

:func:`_run_dotnet_log_tool` is the reusable subprocess helper. Callers
(parse_evtx; hayabusa_csv_timeline and chainsaw_hunt when implemented) build
their own cmd argv and pass it here so the audit log records exact invocations.

Unlike MFTECmd, EvtxECmd calls ``Environment.Exit(0)`` on errors (PECmd, SBECmd,
AmcacheParser, AppCompatCacheParser do too — see CLAUDE.md §EZ Tools exit codes).
:func:`serilog_has_errors` parses stderr for ``[ERR]``/``[FTL]`` Serilog markers,
the only reliable failure signal. Hayabusa and Chainsaw are Rust binaries and use
standard exit codes — they do not need this helper.
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import re
import time
from enum import StrEnum
from pathlib import Path
from typing import Final

from silentwitness_mcp.tools._disk_common import DOTNET_BIN

_LOG = logging.getLogger(__name__)

# EvtxeCmd inner-directory quirk: directory is ``EvtxeCmd`` (lowercase ``e``)
# but the DLL is ``EvtxECmd.dll`` (uppercase ``EC``). Verified:
# context/.raw-design-research/03-sift-2026-tool-catalog-verified.md line 115.
EVTXECMD_DLL: Final = Path("/opt/zimmermantools/EvtxeCmd/EvtxECmd.dll")

_DEFAULT_LOG_TIMEOUT_S: Final = 600.0
_TERMINATE_GRACE_S: Final = 5.0
_SERILOG_ERR_RE: Final = re.compile(r"^\[\d{2}:\d{2}:\d{2} (ERR|FTL)\]", re.MULTILINE)


class LogFailureReason(StrEnum):
    EVIDENCE_NOT_REGISTERED = "EVIDENCE_NOT_REGISTERED"
    EVIDENCE_TAMPERED = "EVIDENCE_TAMPERED"
    MOUNT_NOT_RO_NOEXEC_NOSUID = "MOUNT_NOT_RO_NOEXEC_NOSUID"
    DOTNET_NOT_FOUND = "DOTNET_NOT_FOUND"
    EVTXECMD_NOT_FOUND = "EVTXECMD_NOT_FOUND"
    TOOL_FAILED = "TOOL_FAILED"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    OUTPUT_PARSE_FAILED = "OUTPUT_PARSE_FAILED"


@dataclasses.dataclass(frozen=True, slots=True)
class _LogResult:
    exit_code: int
    stdout: bytes
    stderr: bytes
    elapsed_ms: float


async def _run_dotnet_log_tool(
    dll_path: Path,
    argv: list[str],
    *,
    timeout_s: float = _DEFAULT_LOG_TIMEOUT_S,
) -> _LogResult:
    """Spawn ``dotnet <dll_path> *argv`` and return the typed result.

    Caller MUST have already cleared all pre-spawn gates. Raises
    :class:`TimeoutError` on subprocess timeout (caller maps to
    :attr:`LogFailureReason.TOOL_TIMEOUT`)."""
    cmd = [str(DOTNET_BIN), str(dll_path), *argv]
    start = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        raise OSError(f"failed to spawn dotnet {dll_path.name}: {exc}") from exc
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except TimeoutError:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=_TERMINATE_GRACE_S)
        except TimeoutError:
            proc.kill()
            try:
                await asyncio.wait_for(proc.wait(), timeout=_TERMINATE_GRACE_S)
            except TimeoutError:
                _LOG.error("dotnet %s ignored SIGKILL", dll_path.name)
        raise
    return _LogResult(
        exit_code=proc.returncode if proc.returncode is not None else -1,
        stdout=stdout,
        stderr=stderr,
        elapsed_ms=(time.monotonic() - start) * 1000.0,
    )


def serilog_has_errors(stderr: bytes) -> bool:
    """Return ``True`` if stderr contains Serilog ``[ERR]`` or ``[FTL]`` markers.

    EvtxECmd, PECmd, SBECmd, AmcacheParser, and AppCompatCacheParser call
    ``Environment.Exit(0)`` on errors — exit code alone cannot detect failures.
    This regex is the reliable signal per CLAUDE.md §EZ Tools exit codes."""
    return bool(_SERILOG_ERR_RE.search(stderr.decode("utf-8", errors="replace")))


__all__ = [
    "DOTNET_BIN",
    "EVTXECMD_DLL",
    "LogFailureReason",
    "_LogResult",
    "_run_dotnet_log_tool",
    "serilog_has_errors",
]
