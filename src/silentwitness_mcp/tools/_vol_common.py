"""Shared Volatility 3 subprocess infrastructure (architecture §4.6,
PRD FR #5).

Every ``vol_*`` wrapper imports :func:`_run_vol` and the
:class:`VolFailureReason` enum from here. The skeleton story
(story-vol-pslist) lands this helper; subsequent stories add caveat
catalogue entries and call :func:`_run_vol` directly.

Vol3 binary path is pinned to SilentWitness's OWN venv at
``/opt/silentwitness/vol3-venv/bin/vol`` — see CLAUDE.md "Critical pin
reminders": SIFT pins no Vol3 version (open issue #1985 on Vol3 2.28
regresses layer detection on large dumps), so we install our own.
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import time
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Final

from silentwitness_mcp.verification.normalizer import normalize_output

VOL_BIN: Final = Path("/opt/silentwitness/vol3-venv/bin/vol")
"""Vol3 binary. CLAUDE.md non-negotiable: never `/opt/volatility3/...`."""

DEFAULT_TIMEOUT_S: Final = 300.0
"""Default subprocess timeout (5 min). Heavy plugins like ``malfind``
override per-call but the floor is here."""

_TERMINATE_GRACE_S: Final = 5.0
"""SIGTERM → SIGKILL grace window on timeout."""

_STDERR_ADVISORY_CAP: Final = 500
"""Bytes of stderr quoted into a ``TOOL_FAILED`` advisory."""


class VolFailureReason(StrEnum):
    """Closed reject-reason set for ``vol_*`` wrappers. Architecture
    §4.6 + §4.10 + §4.11 surface all four failure modes through one
    typed enum so the agent's reason-branching logic stays uniform
    across the memory family."""

    EVIDENCE_NOT_REGISTERED = "EVIDENCE_NOT_REGISTERED"
    EVIDENCE_TAMPERED = "EVIDENCE_TAMPERED"
    MOUNT_NOT_RO_NOEXEC_NOSUID = "MOUNT_NOT_RO_NOEXEC_NOSUID"
    TOOL_FAILED = "TOOL_FAILED"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    OUTPUT_PARSE_FAILED = "OUTPUT_PARSE_FAILED"


_VOL_CAVEATS: Final[Mapping[str, tuple[str, ...]]] = {
    # context/domain/03 §7.2 Gotchas — quoted verbatim.
    "pslist": (
        (
            "windows.pslist walks PsActiveProcessHead — DKOM-hidden "
            "processes are invisible; corroborate with vol_psscan"
        ),
        ("ImageFileName is truncated to 15 chars; use vol_cmdline or vol_dlllist for full paths"),
        ("ExitTime may be set for processes still referenced by other handles (orphan teardown)"),
    ),
}


def caveats_for(plugin_key: str) -> tuple[str, ...]:
    """Return the caveat list for ``plugin_key`` or ``()`` if unknown.
    Tools that pass an unknown key get empty caveats — caller should
    have registered them first; a silent ``KeyError`` here would let
    a typo strip safety guidance from the audit row."""
    return _VOL_CAVEATS.get(plugin_key, ())


@dataclasses.dataclass(slots=True, frozen=True)
class _VolResult:
    """Outcome of one :func:`_run_vol` invocation. ``stdout_normalized``
    is the post-normalizer bytes — citation gates and the audit-blob
    SHA256 both use this canonical form (architecture §4.6)."""

    exit_code: int
    stdout_normalized: bytes
    stderr: bytes
    elapsed_ms: float
    result_sha256: str


async def _run_vol(
    plugin_name: str,
    evidence_path: Path,
    *,
    extra_argv: list[str] | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    normalizer_key: str = "vol_pslist",
) -> _VolResult:
    """Spawn Vol3 in JSON-renderer mode (`-r json`) against
    ``evidence_path`` and return the typed result.

    Caller MUST have already cleared evidence-registry +
    mount-validator gates — this helper does NOT enforce them. Raises
    :class:`asyncio.TimeoutError` on subprocess timeout (caller maps
    to :attr:`VolFailureReason.TOOL_TIMEOUT`)."""
    cmd_argv = [
        str(VOL_BIN),
        "-f",
        str(evidence_path),
        "-r",
        "json",
        plugin_name,
        *(extra_argv or []),
    ]
    start = time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        *cmd_argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except TimeoutError:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=_TERMINATE_GRACE_S)
        except TimeoutError:
            proc.kill()
            await proc.wait()
        raise
    elapsed_ms = (time.monotonic() - start) * 1000.0
    normalized = normalize_output(stdout, normalizer_key)
    return _VolResult(
        exit_code=proc.returncode if proc.returncode is not None else -1,
        stdout_normalized=normalized,
        stderr=stderr,
        elapsed_ms=elapsed_ms,
        result_sha256=hashlib.sha256(normalized).hexdigest(),
    )


def truncated_stderr(stderr: bytes) -> str:
    """First :data:`_STDERR_ADVISORY_CAP` chars of stderr, UTF-8
    surrogate-escape decoded. Used in the ``TOOL_FAILED`` advisory."""
    return stderr.decode("utf-8", errors="surrogateescape")[:_STDERR_ADVISORY_CAP]


def cmd_argv_for(
    plugin_name: str, evidence_path: Path, extra: list[str] | None = None
) -> list[str]:
    """Public mirror of the argv :func:`_run_vol` builds. Lets the
    tool wrapper record cmd_argv in :class:`DataProvenance` without
    re-spawning."""
    return [
        str(VOL_BIN),
        "-f",
        str(evidence_path),
        "-r",
        "json",
        plugin_name,
        *(extra or []),
    ]


__all__ = [
    "DEFAULT_TIMEOUT_S",
    "VOL_BIN",
    "VolFailureReason",
    "_VolResult",
    "_run_vol",
    "caveats_for",
    "cmd_argv_for",
    "truncated_stderr",
]
