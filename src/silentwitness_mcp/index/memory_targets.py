"""Target selection for bounded Volatility memory malware scans."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from silentwitness_mcp.index.feeders_memory import (
    MALFIND_PLUGIN,
)

CMDLINE_PLUGIN: Final[str] = "windows.cmdline.CmdLine"
NETSCAN_PLUGIN: Final[str] = "windows.netscan.NetScan"
PSLIST_PLUGIN: Final[str] = "windows.pslist.PsList"
PSSCAN_PLUGIN: Final[str] = "windows.psscan.PsScan"

_SUSPICIOUS_TOKENS: Final[tuple[str, ...]] = (
    "powershell",
    "pwsh",
    "cmd.exe",
    "wscript",
    "cscript",
    "mshta",
    "rundll32",
    "regsvr32",
    "certutil",
    "bitsadmin",
    "wmic",
    "psexec",
    "mimikatz",
    "procdump",
    "rclone",
    "anydesk",
    "teamviewer",
    "vnc",
    "wget",
    "curl",
    "http://",
    "https://",
    "frombase64string",
    "encodedcommand",
    "-enc",
    "bypass",
    "invoke-",
)


def _pid(value: object) -> int | None:
    if not isinstance(value, int | str | bytes | bytearray):
        return None
    try:
        pid = int(value)  # Volatility JSON may render numeric columns as strings.
    except (TypeError, ValueError):
        return None
    return pid if pid > 4 else None


def _contains_suspicious_token(row: Mapping[str, Any]) -> bool:
    text = " ".join(
        str(row.get(key) or "") for key in ("Process", "ImageFileName", "Args", "CommandLine")
    ).lower()
    return any(token in text for token in _SUSPICIOUS_TOKENS)


def select_malfind_pids(
    rows_by_plugin: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    max_pids: int,
) -> tuple[int, ...]:
    """Select a bounded PID set for targeted ``malfind``.

    Signals are intentionally simple and explainable:
    - process owns a network object from ``netscan``;
    - process/cmdline contains common LOLBin or downloader tokens;
    - process appears in ``psscan`` but not ``pslist``.
    """

    candidates: set[int] = set()

    for row in rows_by_plugin.get(NETSCAN_PLUGIN, ()):
        if pid := _pid(row.get("PID")):
            candidates.add(pid)

    for plugin in (CMDLINE_PLUGIN, PSLIST_PLUGIN, PSSCAN_PLUGIN):
        for row in rows_by_plugin.get(plugin, ()):
            if _contains_suspicious_token(row):
                if pid := _pid(row.get("PID")):
                    candidates.add(pid)

    pslist_pids = {
        pid
        for row in rows_by_plugin.get(PSLIST_PLUGIN, ())
        if (pid := _pid(row.get("PID"))) is not None
    }
    psscan_pids = {
        pid
        for row in rows_by_plugin.get(PSSCAN_PLUGIN, ())
        if (pid := _pid(row.get("PID"))) is not None
    }
    candidates.update(psscan_pids - pslist_pids)

    return tuple(sorted(candidates)[: max(0, max_pids)])


__all__ = ["MALFIND_PLUGIN", "select_malfind_pids"]
