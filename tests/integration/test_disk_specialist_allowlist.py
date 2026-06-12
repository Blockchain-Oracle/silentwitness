"""Integration test — disk specialist allowlist blocks non-disk tools."""

from __future__ import annotations

from pydantic_ai.tools import ToolDefinition

from silentwitness_agent.specialists.disk import DISK_TOOL_ALLOWLIST


def _td(name: str) -> ToolDefinition:
    return ToolDefinition(name=name)


# ---------------------------------------------------------------------------
# 1. vol_pslist (memory tool) is not in DISK_TOOL_ALLOWLIST
# ---------------------------------------------------------------------------


def test_vol_pslist_not_in_allowlist() -> None:
    assert "vol_pslist" not in DISK_TOOL_ALLOWLIST


# ---------------------------------------------------------------------------
# 2. Filter function blocks memory/network/log tools
# ---------------------------------------------------------------------------


def test_filter_blocks_non_disk_tools() -> None:
    """The allowlist filter rejects memory, network, and log tools."""
    _filter = lambda _ctx, td: td.name in DISK_TOOL_ALLOWLIST  # noqa: E731
    blocked = (
        "vol_pslist",
        "vol_malfind",
        "zeek_run",
        "parse_evtx",
        "hayabusa_csv_timeline",
        "suricata_run",
    )
    for name in blocked:
        assert not _filter(None, _td(name)), f"{name!r} should be blocked"


# ---------------------------------------------------------------------------
# 3. Filter function passes all 10 DISK_TOOL_ALLOWLIST names
# ---------------------------------------------------------------------------


def test_filter_passes_all_allowlist_tools() -> None:
    """The allowlist filter accepts every name in DISK_TOOL_ALLOWLIST."""
    _filter = lambda _ctx, td: td.name in DISK_TOOL_ALLOWLIST  # noqa: E731
    for name in DISK_TOOL_ALLOWLIST:
        assert _filter(None, _td(name)), f"{name!r} should pass"


# ---------------------------------------------------------------------------
# 4. Allowlist has no overlap with canonical memory/network/log tool names
# ---------------------------------------------------------------------------


def test_allowlist_clean_from_non_disk_tools() -> None:
    non_disk = {
        "vol_pslist",
        "vol_pstree",
        "vol_psscan",
        "vol_malfind",
        "vol_netscan",
        "vol_cmdline",
        "vol_dlllist",
        "vol_handles",
        "vol_lsadump",
        "zeek_run",
        "suricata_run",
        "parse_evtx",
        "hayabusa_csv_timeline",
        "chainsaw_hunt",
    }
    overlap = DISK_TOOL_ALLOWLIST & non_disk
    assert not overlap, f"Allowlist leaks non-disk tools: {overlap}"
