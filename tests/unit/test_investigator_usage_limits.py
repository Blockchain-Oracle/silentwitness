"""Focused tests for direct investigator run-wide usage limits."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic_ai import Agent
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models.test import TestModel

from silentwitness_agent.investigator import (
    InvestigatorDeps,
    InvestigatorResult,
    _AgentConfig,
    investigate,
)


def _make_test_cfg(model_str: str = "test") -> _AgentConfig:
    test_agent: Agent[InvestigatorDeps, InvestigatorResult] = Agent(
        TestModel(
            custom_output_args={
                "hypotheses_formed": 0,
                "hypotheses_confirmed": 0,
                "hypotheses_pivoted": 0,
                "hypotheses_abandoned": 0,
                "findings_staged": 0,
                "total_tool_calls": 0,
                "total_tokens_consumed": 0,
                "time_elapsed_ms": 0.0,
                "final_state": "COMPLETED",
                "model_used": model_str,
            }
        ),
        output_type=InvestigatorResult,
    )
    dummy_server = MCPServerStdio("python", ["-c", "pass"])
    return _AgentConfig(agent=test_agent, model_str=model_str, max_iters=5, mcp_server=dummy_server)


@pytest.mark.anyio
async def test_investigate_wires_total_token_limit(tmp_path: Path) -> None:
    cfg = _make_test_cfg()
    seen_limits: list[object] = []

    async def _capture(*_a: object, **kwargs: object) -> object:
        seen_limits.append(kwargs["usage_limits"])
        output = InvestigatorResult(
            hypotheses_formed=0,
            hypotheses_confirmed=0,
            hypotheses_pivoted=0,
            hypotheses_abandoned=0,
            findings_staged=0,
            total_tool_calls=0,
            total_tokens_consumed=0,
            time_elapsed_ms=0.0,
            final_state="COMPLETED",
            model_used="test",
        )
        return SimpleNamespace(output=output, usage=SimpleNamespace(total_tokens=0))

    with (
        patch("silentwitness_agent.investigator.build_investigator", return_value=cfg),
        patch.object(cfg.agent, "run", side_effect=_capture),
    ):
        await investigate(tmp_path, "aj", "test prompt", max_tokens=1_234_567)

    limit = seen_limits[0]
    assert limit.request_limit == 5
    assert limit.total_tokens_limit == 1_234_567
    assert limit.count_tokens_before_request is False


@pytest.mark.anyio
async def test_investigate_token_limit_path_returns_budget_exhausted(tmp_path: Path) -> None:
    cfg = _make_test_cfg()

    async def _fail(*_a: object, **_kw: object) -> None:
        raise UsageLimitExceeded("Exceeded the total_tokens_limit of 123")

    with (
        patch("silentwitness_agent.investigator.build_investigator", return_value=cfg),
        patch.object(cfg.agent, "run", side_effect=_fail),
    ):
        result = await investigate(tmp_path, "aj", "test prompt", max_tokens=123)

    assert result.final_state == "BUDGET_EXHAUSTED"
