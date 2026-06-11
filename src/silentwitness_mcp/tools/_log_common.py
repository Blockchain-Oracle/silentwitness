"""Shared subprocess infrastructure for the log tool family
(parse_evtx, hayabusa_csv_timeline, chainsaw_hunt) — architecture §4.2 rows 15-17,
context/.raw-design-research/03-sift-2026-tool-catalog-verified.md §EZ Tools.

:func:`_run_dotnet_log_tool` wraps dotnet DLL invocations (parse_evtx).
:func:`_run_native_log_tool` wraps native Rust binaries (hayabusa_csv_timeline,
chainsaw_hunt) — same ``_LogResult`` shape so the audit-blob writer is shared.

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

# Hayabusa v3.9.0 — NOT pre-installed on SIFT 2026; install.sh provisions it.
# context/.raw-design-research/03 §"Tools our install script MUST add" line 271.
HAYABUSA_BIN: Final = Path("/opt/hayabusa/hayabusa")
HAYABUSA_RULES_DIR: Final = Path("/opt/hayabusa-rules")

_DEFAULT_LOG_TIMEOUT_S: Final = 600.0
_TERMINATE_GRACE_S: Final = 5.0
_SERILOG_ERR_RE: Final = re.compile(r"\[\d{2}:\d{2}:\d{2} (ERR|FTL)\]")


class LogFailureReason(StrEnum):
    EVIDENCE_NOT_REGISTERED = "EVIDENCE_NOT_REGISTERED"
    EVIDENCE_TAMPERED = "EVIDENCE_TAMPERED"
    MOUNT_NOT_RO_NOEXEC_NOSUID = "MOUNT_NOT_RO_NOEXEC_NOSUID"
    DOTNET_NOT_FOUND = "DOTNET_NOT_FOUND"
    EVTXECMD_NOT_FOUND = "EVTXECMD_NOT_FOUND"
    HAYABUSA_NOT_INSTALLED = "HAYABUSA_NOT_INSTALLED"
    HAYABUSA_RULES_MISSING = "HAYABUSA_RULES_MISSING"
    TOOL_FAILED = "TOOL_FAILED"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    OUTPUT_PARSE_FAILED = "OUTPUT_PARSE_FAILED"


@dataclasses.dataclass(frozen=True, slots=True)
class _LogResult:
    """Subprocess result bundle. exit_code=-1 means returncode was None post-communicate."""

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
        try:
            proc.terminate()
        except ProcessLookupError:
            pass  # already exited between timeout and signal — proceed to wait
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
                _LOG.error("dotnet %s ignored SIGKILL", dll_path.name)
        raise
    return _LogResult(
        exit_code=proc.returncode if proc.returncode is not None else -1,
        stdout=stdout,
        stderr=stderr,
        elapsed_ms=(time.monotonic() - start) * 1000.0,
    )


async def _run_native_log_tool(
    bin_path: Path,
    argv: list[str],
    *,
    timeout_s: float = _DEFAULT_LOG_TIMEOUT_S,
) -> _LogResult:
    """Spawn ``bin_path *argv`` and return the typed result.

    Mirrors :func:`_run_dotnet_log_tool` for native Rust binaries (Hayabusa,
    Chainsaw) so the audit-blob writer downstream is identical. Raises
    :class:`TimeoutError` on subprocess timeout; raises :class:`OSError` on
    spawn failure.
    """
    cmd = [str(bin_path), *argv]
    start = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        raise OSError(f"failed to spawn {bin_path.name}: {exc}") from exc
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except TimeoutError:
        try:
            proc.terminate()
        except ProcessLookupError:
            pass
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
                _LOG.error("%s ignored SIGKILL", bin_path.name)
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
    "EVTXECMD_DLL",
    "HAYABUSA_BIN",
    "HAYABUSA_RULES_DIR",
    "LogFailureReason",
    "_LogResult",
    "_run_dotnet_log_tool",
    "_run_native_log_tool",
    "serilog_has_errors",
]
