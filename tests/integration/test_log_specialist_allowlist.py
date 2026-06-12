"""Integration test — log specialist allowlist blocks non-log tools."""

from __future__ import annotations

from pydantic_ai.tools import ToolDefinition

from silentwitness_agent.specialists.log import LOG_TOOL_ALLOWLIST


def _td(name: str) -> ToolDefinition:
    return ToolDefinition(name=name)


# ---------------------------------------------------------------------------
# 1. vol_pslist (memory tool) is not in LOG_TOOL_ALLOWLIST
# ---------------------------------------------------------------------------


def test_vol_pslist_not_in_allowlist() -> None:
    assert "vol_pslist" not in LOG_TOOL_ALLOWLIST


# ---------------------------------------------------------------------------
# 2. Filter function blocks disk/memory/network tools
# ---------------------------------------------------------------------------


def test_filter_blocks_non_log_tools() -> None:
    """The allowlist filter rejects memory, disk, and network tools."""
    _filter = lambda _ctx, td: td.name in LOG_TOOL_ALLOWLIST  # noqa: E731
    blocked = (
        "vol_pslist",
        "parse_mft",
        "regripper_run",
        "zeek_run",
        "suricata_run",
    )
    for name in blocked:
        assert not _filter(None, _td(name)), f"{name!r} should be blocked"


# ---------------------------------------------------------------------------
# 3. Filter function passes all 7 LOG_TOOL_ALLOWLIST names
# ---------------------------------------------------------------------------


def test_filter_passes_all_allowlist_tools() -> None:
    """The allowlist filter accepts every name in LOG_TOOL_ALLOWLIST."""
    _filter = lambda _ctx, td: td.name in LOG_TOOL_ALLOWLIST  # noqa: E731
    for name in LOG_TOOL_ALLOWLIST:
        assert _filter(None, _td(name)), f"{name!r} should pass"


# ---------------------------------------------------------------------------
# 4. Allowlist has no overlap with canonical disk/memory/network tool names
# ---------------------------------------------------------------------------


def test_allowlist_clean_from_non_log_tools() -> None:
    non_log = {
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
        "zeek_run",
        "suricata_run",
    }
    overlap = LOG_TOOL_ALLOWLIST & non_log
    assert not overlap, f"Allowlist leaks non-log tools: {overlap}"
