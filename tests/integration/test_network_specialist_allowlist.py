"""Integration test — network specialist allowlist blocks non-network tools."""

from __future__ import annotations

from pydantic_ai.tools import ToolDefinition

from silentwitness_agent.specialists.network import NETWORK_TOOL_ALLOWLIST


def _td(name: str) -> ToolDefinition:
    return ToolDefinition(name=name)


# ---------------------------------------------------------------------------
# 1. parse_mft (disk tool) is not in NETWORK_TOOL_ALLOWLIST
# ---------------------------------------------------------------------------


def test_parse_mft_not_in_allowlist() -> None:
    assert "parse_mft" not in NETWORK_TOOL_ALLOWLIST


# ---------------------------------------------------------------------------
# 2. Filter function blocks disk/memory/log tools
# ---------------------------------------------------------------------------


def test_filter_blocks_non_network_tools() -> None:
    """The allowlist filter rejects disk, memory, and log tools."""
    _filter = lambda _ctx, td: td.name in NETWORK_TOOL_ALLOWLIST  # noqa: E731
    blocked = (
        "parse_mft",
        "vol_pslist",
        "regripper_run",
        "parse_evtx",
        "hayabusa_csv_timeline",
        "chainsaw_hunt",
    )
    for name in blocked:
        assert not _filter(None, _td(name)), f"{name!r} should be blocked"


# ---------------------------------------------------------------------------
# 3. Filter function passes all 6 NETWORK_TOOL_ALLOWLIST names
# ---------------------------------------------------------------------------


def test_filter_passes_all_allowlist_tools() -> None:
    """The allowlist filter accepts every name in NETWORK_TOOL_ALLOWLIST."""
    _filter = lambda _ctx, td: td.name in NETWORK_TOOL_ALLOWLIST  # noqa: E731
    for name in NETWORK_TOOL_ALLOWLIST:
        assert _filter(None, _td(name)), f"{name!r} should pass"


# ---------------------------------------------------------------------------
# 4. Allowlist has no overlap with canonical disk/memory/log tool names
# ---------------------------------------------------------------------------


def test_allowlist_clean_from_non_network_tools() -> None:
    non_network = {
        "parse_mft",
        "parse_amcache",
        "parse_shimcache",
        "parse_prefetch",
        "parse_shellbags",
        "regripper_run",
        "vol_pslist",
        "vol_pstree",
        "vol_psscan",
        "vol_malfind",
        "vol_netscan",
        "vol_cmdline",
        "vol_dlllist",
        "vol_handles",
        "vol_lsadump",
        "parse_evtx",
        "hayabusa_csv_timeline",
        "chainsaw_hunt",
    }
    overlap = NETWORK_TOOL_ALLOWLIST & non_network
    assert not overlap, f"Allowlist leaks non-network tools: {overlap}"
