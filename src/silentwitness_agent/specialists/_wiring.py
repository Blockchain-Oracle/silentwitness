"""Register all four specialists onto a live investigator, sharing its MCP server.

Extracted from cli_commands/investigate.py to keep that module under the 400-LOC
gate. Each specialist reuses the investigator's ref-counted MCP server so there
is one case-bound subprocess + AuditLogger, not five.
"""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

from silentwitness_agent.investigator import InvestigatorDeps, InvestigatorResult
from silentwitness_agent.specialists import disk, log, memory, network


def register_all_specialists(
    investigator: Agent[InvestigatorDeps, InvestigatorResult],
    *,
    model: str | None,
    shared_server: MCPServerStdio,
) -> None:
    """Build + register dispatch_<x>_specialist for memory/disk/log/network.

    Build ALL FOUR first (model resolution is the failure-prone step), THEN
    register — so a bad model never leaves the investigator partially wired with
    only some dispatch tools attached.
    """
    if shared_server is None:  # defensive; the type already forbids this
        raise ValueError("register_all_specialists requires the investigator's shared MCP server")
    built = (
        (memory, memory.build_memory_specialist(model=model, shared_server=shared_server)),
        (disk, disk.build_disk_specialist(model=model, shared_server=shared_server)),
        (log, log.build_log_specialist(model=model, shared_server=shared_server)),
        (network, network.build_network_specialist(model=model, shared_server=shared_server)),
    )
    for module, specialist in built:
        module.register_as_investigator_tool(investigator, specialist)


__all__ = ["register_all_specialists"]
