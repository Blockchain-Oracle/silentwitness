"""Integration test — memory specialist allowlist blocks non-memory tools."""

from __future__ import annotations

from pydantic_ai.tools import ToolDefinition

from silentwitness_agent.specialists.memory import MEMORY_TOOL_ALLOWLIST


def _td(name: str) -> ToolDefinition:
    return ToolDefinition(name=name)


# ---------------------------------------------------------------------------
# 1. parse_mft is not in MEMORY_TOOL_ALLOWLIST
# ---------------------------------------------------------------------------


def test_parse_mft_not_in_allowlist() -> None:
    assert "parse_mft" not in MEMORY_TOOL_ALLOWLIST


# ---------------------------------------------------------------------------
# 2. Filter function blocks disk/network/log tools
# ---------------------------------------------------------------------------


def test_filter_blocks_disk_tools() -> None:
    """The allowlist filter rejects disk and non-memory tools."""
    _filter = lambda _ctx, td: td.name in MEMORY_TOOL_ALLOWLIST  # noqa: E731
    for blocked in ("parse_mft", "parse_amcache", "zeek_run", "parse_evtx", "regripper_run"):
        assert not _filter(None, _td(blocked)), f"{blocked!r} should be blocked"


# ---------------------------------------------------------------------------
# 3. Filter function passes every MEMORY_TOOL_ALLOWLIST name
# ---------------------------------------------------------------------------


def test_filter_passes_all_allowlist_tools() -> None:
    """The allowlist filter accepts every name in MEMORY_TOOL_ALLOWLIST."""
    _filter = lambda _ctx, td: td.name in MEMORY_TOOL_ALLOWLIST  # noqa: E731
    for name in MEMORY_TOOL_ALLOWLIST:
        assert _filter(None, _td(name)), f"{name!r} should pass"


# ---------------------------------------------------------------------------
# 4. Allowlist has no overlap with canonical disk/network/log tool names
# ---------------------------------------------------------------------------


def test_allowlist_clean_from_non_memory_tools() -> None:
    non_memory = {
        "parse_mft",
        "parse_amcache",
        "parse_shimcache",
        "parse_prefetch",
        "parse_shellbags",
        "regripper_run",
        "zeek_run",
        "suricata_run",
        "parse_evtx",
        "hayabusa_csv_timeline",
        "chainsaw_hunt",
    }
    overlap = MEMORY_TOOL_ALLOWLIST & non_memory
    assert not overlap, f"Allowlist leaks non-memory tools: {overlap}"
