"""Guard that the live investigate path actually wires the 4 specialists.

build_*_specialist / register_as_investigator_tool were test-only for the whole
project history — never called in cli_commands/investigate.py. This guards
against that regression and asserts specialists share the investigator's MCP
server (one subprocess, one AuditLogger).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

from silentwitness_agent.investigator import InvestigatorDeps, InvestigatorResult
from silentwitness_agent.specialists.disk import (
    build_disk_specialist,
    register_as_investigator_tool,
)
from silentwitness_agent.specialists.log import build_log_specialist
from silentwitness_agent.specialists.memory import build_memory_specialist
from silentwitness_agent.specialists.network import build_network_specialist

_BUILDERS = {
    "memory": build_memory_specialist,
    "disk": build_disk_specialist,
    "log": build_log_specialist,
    "network": build_network_specialist,
}

_WIRING_SRC = Path("src/silentwitness_agent/specialists/_wiring.py").read_text(encoding="utf-8")
_INVESTIGATE_SRC = Path("src/silentwitness_agent/cli_commands/investigate.py").read_text(
    encoding="utf-8"
)


@pytest.mark.parametrize("name", ["memory", "disk", "log", "network"])
def test_wiring_registers_each_specialist_with_shared_server(name: str) -> None:
    assert f"build_{name}_specialist(model=model, shared_server=shared_server)" in _WIRING_SRC
    assert f"{name}.register_as_investigator_tool" in _WIRING_SRC


def test_live_investigate_calls_register_all_specialists() -> None:
    assert "register_all_specialists(cfg.agent" in _INVESTIGATE_SRC


@pytest.mark.parametrize("name", ["memory", "disk", "log", "network"])
def test_specialist_reuses_shared_server_not_a_new_one(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SILENTWITNESS_MODEL", "test")
    shared = MCPServerStdio("python", ["-c", "pass"])
    specialist = _BUILDERS[name](model="test", shared_server=shared)
    # The specialist's filtered toolset must wrap the SHARED server instance.
    assert any(getattr(t, "wrapped", None) is shared for t in specialist.toolsets), (
        f"{name} specialist did not reuse the shared MCP server"
    )


def test_register_adds_dispatch_tool_on_investigator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_SPECIALIST_MODEL_DISK", "test")
    investigator: Agent[InvestigatorDeps, InvestigatorResult] = Agent(
        "test", deps_type=InvestigatorDeps, output_type=InvestigatorResult
    )
    shared = MCPServerStdio("python", ["-c", "pass"])
    register_as_investigator_tool(investigator, build_disk_specialist("test", shared))
    assert "dispatch_disk_specialist" in investigator._function_toolset.tools
