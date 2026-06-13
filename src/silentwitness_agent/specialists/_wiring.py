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
    """Build + register dispatch_<x>_specialist for memory/disk/log/network."""
    memory.register_as_investigator_tool(
        investigator, memory.build_memory_specialist(model=model, shared_server=shared_server)
    )
    disk.register_as_investigator_tool(
        investigator, disk.build_disk_specialist(model=model, shared_server=shared_server)
    )
    log.register_as_investigator_tool(
        investigator, log.build_log_specialist(model=model, shared_server=shared_server)
    )
    network.register_as_investigator_tool(
        investigator, network.build_network_specialist(model=model, shared_server=shared_server)
    )


__all__ = ["register_all_specialists"]
