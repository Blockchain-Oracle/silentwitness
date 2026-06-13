"""Guard that the live investigate path actually wires the 4 specialists.

build_*_specialist / register_as_investigator_tool were test-only for the whole
project history — never called in cli_commands/investigate.py. This guards
against that regression and asserts specialists share the investigator's MCP
server (one subprocess, one AuditLogger).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from silentwitness_agent.hypothesis.budget import BudgetEnforcer
from silentwitness_agent.hypothesis.stack import HypothesisStack
from silentwitness_agent.investigator import InvestigatorDeps, InvestigatorResult
from silentwitness_agent.specialists._base import SpecialistReport
from silentwitness_agent.specialists.disk import (
    build_disk_specialist,
    register_as_investigator_tool,
)
from silentwitness_agent.specialists.log import build_log_specialist
from silentwitness_agent.specialists.memory import build_memory_specialist
from silentwitness_agent.specialists.network import build_network_specialist
from silentwitness_common.types import Confidence

_BUILDERS = {
    "memory": build_memory_specialist,
    "disk": build_disk_specialist,
    "log": build_log_specialist,
    "network": build_network_specialist,
}

_INVESTIGATE_SRC = Path("src/silentwitness_agent/cli_commands/investigate.py").read_text(
    encoding="utf-8"
)


def test_register_all_specialists_wires_four_dispatch_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Behavioral: register_all_specialists attaches all 4 dispatch tools to the
    investigator, sharing one server. Guards against a builder typo (dropped or
    duplicated specialist) that a source-grep would miss."""
    from silentwitness_agent.specialists._wiring import register_all_specialists

    monkeypatch.setenv("SILENTWITNESS_MODEL", "test")
    investigator: Agent[InvestigatorDeps, InvestigatorResult] = Agent(
        "test", deps_type=InvestigatorDeps, output_type=InvestigatorResult
    )
    shared = MCPServerStdio("python", ["-c", "pass"])
    register_all_specialists(investigator, model="test", shared_server=shared)
    tools = investigator._function_toolset.tools
    for name in ("memory", "disk", "log", "network"):
        assert f"dispatch_{name}_specialist" in tools


def test_live_investigate_calls_register_all_specialists() -> None:
    # Historical-regression guard: builders were test-only the whole project
    # history; this pins that the live path now actually calls the aggregator.
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


@pytest.mark.anyio
async def test_dispatch_specialist_runs_and_returns_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cover the dispatch_<x>_specialist body: it builds SpecialistDeps, runs the
    specialist (stubbed here to avoid a live MCP subprocess), and returns the
    report. The investigator is driven by a FunctionModel that calls the tool."""
    monkeypatch.setenv("SILENTWITNESS_MODEL", "test")
    specialist = build_disk_specialist(
        model="test", shared_server=MCPServerStdio("python", ["-c", "pass"])
    )

    report = SpecialistReport(
        findings=[],
        tokens_spent=0,
        tool_calls=[],
        time_elapsed_ms=0.0,
        confidence_assessment=Confidence.LOW,
    )

    async def _fake_run(*_a: object, **_k: object) -> object:
        return SimpleNamespace(output=report)

    monkeypatch.setattr(specialist, "run", _fake_run)

    calls: list[int] = []

    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        idx = len(calls)
        calls.append(1)
        if idx == 0:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="dispatch_disk_specialist",
                        args={"question": "check the MFT", "hypothesis_id": "H-001"},
                    )
                ]
            )
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name=info.output_tools[0].name,
                    args={
                        "hypotheses_formed": 0,
                        "hypotheses_confirmed": 0,
                        "hypotheses_pivoted": 0,
                        "hypotheses_abandoned": 0,
                        "findings_staged": 0,
                        "total_tool_calls": 1,
                        "total_tokens_consumed": 0,
                        "time_elapsed_ms": 0.0,
                        "final_state": "COMPLETED",
                        "model_used": "test",
                    },
                )
            ]
        )

    investigator: Agent[InvestigatorDeps, InvestigatorResult] = Agent(
        FunctionModel(_fn), deps_type=InvestigatorDeps, output_type=InvestigatorResult
    )
    register_as_investigator_tool(investigator, specialist)
    deps = InvestigatorDeps(
        case_dir=tmp_path,
        examiner="aj",
        stack=HypothesisStack(case_dir=tmp_path, examiner="aj"),
        budget=BudgetEnforcer(),
    )
    result = await investigator.run("go", deps=deps)
    assert result.output.final_state == "COMPLETED"
