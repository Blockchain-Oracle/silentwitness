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
    src = Path("src/silentwitness_agent/cli_commands/_investigate_runner.py").read_text(
        encoding="utf-8"
    )
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


_FINAL_RESULT = {
    "hypotheses_formed": 1,
    "hypotheses_confirmed": 0,
    "hypotheses_pivoted": 0,
    "hypotheses_abandoned": 0,
    "findings_staged": 0,
    "total_tool_calls": 0,
    "total_tokens_consumed": 0,
    "time_elapsed_ms": 0.0,
    "final_state": "COMPLETED",
    "model_used": "test",
}


async def _run_tool_steps(
    tmp_path: Path, steps: list[tuple[str, dict[str, object]]]
) -> HypothesisStack:
    """Drive the investigator through a scripted sequence of hypothesis-tool
    calls, then emit the final result. Returns the resulting stack."""
    calls: list[int] = []

    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        idx = len(calls)
        calls.append(1)
        if idx < len(steps):
            name, args = steps[idx]
            return ModelResponse(parts=[ToolCallPart(tool_name=name, args=args)])
        return ModelResponse(
            parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=_FINAL_RESULT)]
        )

    agent: Agent[InvestigatorDeps, InvestigatorResult] = Agent(
        FunctionModel(_fn), deps_type=InvestigatorDeps, output_type=InvestigatorResult
    )
    register_hypothesis_tools(agent)
    stack = HypothesisStack(case_dir=tmp_path, examiner="tester")
    deps = InvestigatorDeps(
        case_dir=tmp_path, examiner="tester", stack=stack, budget=BudgetEnforcer()
    )
    await agent.run("go", deps=deps)
    return stack


@pytest.mark.anyio
async def test_confirm_hypothesis_moves_it_to_history(tmp_path: Path) -> None:
    stack = await _run_tool_steps(
        tmp_path,
        [
            ("form_hypothesis", {"statement": "C2 beacon", "specialist": "network"}),
            ("confirm_hypothesis", {"hypothesis_id": "H-001", "evidence_audit_ids": ["aid-1"]}),
        ],
    )
    snap = stack.snapshot()
    assert snap.active is None
    assert any(h.id == "H-001" and h.status.value == "CONFIRMED" for h in snap.history)


@pytest.mark.anyio
async def test_pivot_hypothesis_activates_child(tmp_path: Path) -> None:
    stack = await _run_tool_steps(
        tmp_path,
        [
            ("form_hypothesis", {"statement": "first theory", "specialist": "memory"}),
            (
                "pivot_hypothesis",
                {
                    "from_hypothesis_id": "H-001",
                    "to_statement": "better theory",
                    "reason": "contradicted by the http.log",
                },
            ),
        ],
    )
    snap = stack.snapshot()
    assert snap.active is not None and snap.active.id == "H-002"
    assert any(h.id == "H-001" and h.status.value == "PIVOTED" for h in snap.history)


@pytest.mark.anyio
async def test_abandon_hypothesis_records_abandoned(tmp_path: Path) -> None:
    stack = await _run_tool_steps(
        tmp_path,
        [
            ("form_hypothesis", {"statement": "dead end", "specialist": "disk"}),
            ("abandon_hypothesis", {"hypothesis_id": "H-001", "reason": "no supporting evidence"}),
        ],
    )
    assert any(h.id == "H-001" and h.status.value == "ABANDONED" for h in stack.snapshot().history)


@pytest.mark.anyio
async def test_invalid_transition_returns_guidance_not_crash(tmp_path: Path) -> None:
    # Confirming a non-active hypothesis must return a guidance string (the tool
    # catches InvalidTransition), not raise — the run completes cleanly.
    stack = await _run_tool_steps(
        tmp_path,
        [("confirm_hypothesis", {"hypothesis_id": "H-999", "evidence_audit_ids": []})],
    )
    assert stack.snapshot().active is None
