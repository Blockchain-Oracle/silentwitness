"""The investigator must be able to DRIVE its HypothesisStack via tools.

The stack was built and unit-tested but never exposed to the model, so every
live run reported zero hypotheses. These tests lock the wiring: the four
lifecycle tools are registered, the live investigate path registers them, and a
scripted form_hypothesis tool call actually mutates the stack.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from silentwitness_agent.hypothesis.budget import BudgetEnforcer
from silentwitness_agent.hypothesis.stack import HypothesisStack
from silentwitness_agent.hypothesis_tools import (
    _coerce_specialist,
    register_hypothesis_tools,
)
from silentwitness_agent.investigator import InvestigatorDeps, InvestigatorResult
from silentwitness_common.types import SpecialistName

_LIFECYCLE_TOOLS = {
    "form_hypothesis",
    "confirm_hypothesis",
    "pivot_hypothesis",
    "abandon_hypothesis",
}


def _bare_investigator() -> Agent[InvestigatorDeps, InvestigatorResult]:
    return Agent(
        FunctionModel(lambda m, i: ModelResponse(parts=[])),
        deps_type=InvestigatorDeps,
        output_type=InvestigatorResult,
    )


def test_register_adds_all_four_lifecycle_tools() -> None:
    agent = _bare_investigator()
    register_hypothesis_tools(agent)
    assert _LIFECYCLE_TOOLS <= set(agent._function_toolset.tools)


def test_coerce_specialist_accepts_canonical_and_lowercase() -> None:
    assert _coerce_specialist("NETWORK") is SpecialistName.NETWORK
    assert _coerce_specialist("memory") is SpecialistName.MEMORY


def test_coerce_specialist_rejects_unknown_with_helpful_error() -> None:
    with pytest.raises(ValueError, match="unknown specialist"):
        _coerce_specialist("filesystem")


def test_live_investigate_path_registers_hypothesis_tools() -> None:
    # Guard against the wiring being dropped again: the live runner module must
    # import and call register_hypothesis_tools.
    src = Path("src/silentwitness_agent/cli_commands/investigate.py").read_text(encoding="utf-8")
    assert "register_hypothesis_tools" in src
    assert "register_hypothesis_tools(cfg.agent)" in src


@pytest.mark.anyio
async def test_form_hypothesis_tool_drives_the_stack(tmp_path: Path) -> None:
    """A scripted form_hypothesis tool call must produce an active hypothesis."""
    calls: list[int] = []

    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        calls.append(1)
        if len(calls) == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="form_hypothesis",
                        args={
                            "statement": "Exfil over HTTP to an external host.",
                            "specialist": "network",
                        },
                    )
                ]
            )
        # Second turn: emit the final structured result via the output tool.
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name=info.output_tools[0].name,
                    args={
                        "hypotheses_formed": 1,
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

    agent: Agent[InvestigatorDeps, InvestigatorResult] = Agent(
        FunctionModel(_fn),
        deps_type=InvestigatorDeps,
        output_type=InvestigatorResult,
    )
    register_hypothesis_tools(agent)

    stack = HypothesisStack(case_dir=tmp_path, examiner="tester")
    deps = InvestigatorDeps(
        case_dir=tmp_path,
        examiner="tester",
        stack=stack,
        budget=BudgetEnforcer(),
    )
    await agent.run("investigate", deps=deps)

    snap = stack.snapshot()
    assert snap.active is not None, "form_hypothesis tool did not drive the stack"
    assert snap.active.statement == "Exfil over HTTP to an external host."
    assert snap.active.assigned_specialist is SpecialistName.NETWORK
