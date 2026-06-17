"""Tests for targeted memory scan PID selection."""

from __future__ import annotations

from silentwitness_mcp.index.memory_targets import (
    CMDLINE_PLUGIN,
    NETSCAN_PLUGIN,
    PSLIST_PLUGIN,
    PSSCAN_PLUGIN,
    select_malfind_pids,
)


def test_select_malfind_pids_uses_network_cmdline_and_hidden_processes() -> None:
    rows = {
        PSLIST_PLUGIN: [
            {"PID": 10, "ImageFileName": "chrome.exe"},
            {"PID": 20, "ImageFileName": "powershell.exe"},
        ],
        CMDLINE_PLUGIN: [{"PID": 20, "Process": "powershell.exe", "Args": "-EncodedCommand x"}],
        NETSCAN_PLUGIN: [{"PID": 10, "Owner": "chrome.exe"}],
        PSSCAN_PLUGIN: [
            {"PID": 20, "ImageFileName": "powershell.exe"},
            {"PID": 30, "ImageFileName": "unlinked.exe"},
        ],
    }

    assert select_malfind_pids(rows, max_pids=64) == (10, 20, 30)


def test_select_malfind_pids_honors_cap_and_skips_kernel_pid() -> None:
    rows = {
        NETSCAN_PLUGIN: [
            {"PID": 4, "Owner": "System"},
            {"PID": 5, "Owner": "a.exe"},
            {"PID": 6, "Owner": "b.exe"},
        ]
    }

    assert select_malfind_pids(rows, max_pids=1) == (5,)
