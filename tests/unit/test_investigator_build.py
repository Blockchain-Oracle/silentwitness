"""Unit tests for investigator factory — ≥7 tests per story spec.

No network calls — uses pydantic-ai's built-in TestModel stub and fake API
keys (key is validated at call-time, not at Agent construction).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models.test import TestModel

from silentwitness_agent.investigator import (
    _DEFAULT_MAX_ITERS,
    _DEFAULT_MODEL,
    _SYSTEM_PROMPT,
    InvestigatorDeps,
    InvestigatorResult,
    _AgentConfig,
    _resolve_model,
    build_investigator,
    investigate,
)

# ---------------------------------------------------------------------------
# System prompt content
# ---------------------------------------------------------------------------


def test_system_prompt_contains_hypothesis_phrase() -> None:
    assert "form one concrete hypothesis at a time" in _SYSTEM_PROMPT


def test_system_prompt_contains_pivot_phrase() -> None:
    assert "you log a pivot event" in _SYSTEM_PROMPT


@pytest.mark.parametrize(
    "forbidden",
    [
        "court-admissible",
        "autonomous SOC",
        "eliminates hallucinations",
        "Ralph Wiggum",
    ],
)
def test_system_prompt_excludes_forbidden_phrases(forbidden: str) -> None:
    assert forbidden not in _SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Factory — model string env var
# ---------------------------------------------------------------------------


def test_factory_reads_model_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_MODEL", "test")
    cfg = build_investigator()
    assert cfg.model_str == "test"


def test_factory_default_model_string() -> None:
    assert _DEFAULT_MODEL == "anthropic:claude-opus-4-7"


def test_factory_direct_model_param_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_MODEL", "anthropic:claude-opus-4-7")
    cfg = build_investigator(model="test")
    assert cfg.model_str == "test"


# ---------------------------------------------------------------------------
# Factory — max_iterations env var
# ---------------------------------------------------------------------------


def test_factory_honours_max_iters_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_MODEL", "test")
    monkeypatch.setenv("SILENTWITNESS_MAX_ITERS", "25")
    cfg = build_investigator()
    assert cfg.max_iters == 25


def test_factory_default_max_iters() -> None:
    assert _DEFAULT_MAX_ITERS == 50


def test_factory_max_iterations_param_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_MODEL", "test")
    monkeypatch.setenv("SILENTWITNESS_MAX_ITERS", "99")
    cfg = build_investigator(max_iterations=7)
    assert cfg.max_iters == 7


# ---------------------------------------------------------------------------
# Factory — MCP toolset
# ---------------------------------------------------------------------------


def test_mcp_toolset_is_mcpserverstdio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_MODEL", "test")
    cfg = build_investigator()
    toolsets = cfg.agent._user_toolsets
    assert len(toolsets) == 1
    assert isinstance(toolsets[0], MCPServerStdio)


def test_mcp_toolset_command_and_args(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_MODEL", "test")
    cfg = build_investigator()
    ts: MCPServerStdio = cfg.agent._user_toolsets[0]  # type: ignore[assignment]
    assert ts.command == "python"
    assert ts.args == ["-m", "silentwitness_mcp"]


# ---------------------------------------------------------------------------
# Schema — InvestigatorResult and InvestigatorDeps
# ---------------------------------------------------------------------------


def test_investigator_result_has_expected_fields() -> None:
    expected = {
        "hypotheses_formed",
        "hypotheses_confirmed",
        "hypotheses_pivoted",
        "hypotheses_abandoned",
        "findings_staged",
        "total_tool_calls",
        "total_tokens_consumed",
        "time_elapsed_ms",
        "final_state",
        "model_used",
    }
    assert set(InvestigatorResult.model_fields) == expected


def test_investigator_deps_has_expected_fields() -> None:
    expected = {"case_dir", "examiner", "stack", "budget", "pending_critiques"}
    assert set(InvestigatorDeps.model_fields) == expected


def test_investigator_result_is_frozen() -> None:
    from pydantic import ValidationError

    result = InvestigatorResult(
        hypotheses_formed=1,
        hypotheses_confirmed=1,
        hypotheses_pivoted=0,
        hypotheses_abandoned=0,
        findings_staged=1,
        total_tool_calls=3,
        total_tokens_consumed=500,
        time_elapsed_ms=120.0,
        final_state="COMPLETED",
        model_used="test",
    )
    with pytest.raises((ValidationError, TypeError)):
        result.model_used = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# _resolve_model — vllm routing
# ---------------------------------------------------------------------------


def test_resolve_model_vllm_returns_openai_chat_model() -> None:
    from pydantic_ai.models.openai import OpenAIChatModel

    result = _resolve_model("vllm:http://localhost:8000")
    assert isinstance(result, OpenAIChatModel)


def test_resolve_model_passthrough_returns_string() -> None:
    result = _resolve_model("anthropic:claude-opus-4-7")
    assert result == "anthropic:claude-opus-4-7"


# ---------------------------------------------------------------------------
# investigate() — success and MAX_ITERATIONS paths
# ---------------------------------------------------------------------------


def _make_test_cfg(model_str: str = "test") -> _AgentConfig:
    """Build an _AgentConfig backed by TestModel (no MCP server)."""
    test_agent: Agent[InvestigatorDeps, InvestigatorResult] = Agent(
        TestModel(
            custom_output_args={
                "hypotheses_formed": 2,
                "hypotheses_confirmed": 1,
                "hypotheses_pivoted": 0,
                "hypotheses_abandoned": 1,
                "findings_staged": 1,
                "total_tool_calls": 4,
                "total_tokens_consumed": 800,
                "time_elapsed_ms": 50.0,
                "final_state": "COMPLETED",
                "model_used": model_str,
            }
        ),
        output_type=InvestigatorResult,
    )
    return _AgentConfig(agent=test_agent, model_str=model_str, max_iters=5)


@pytest.mark.anyio
async def test_investigate_completed_path(tmp_path: Path) -> None:
    cfg = _make_test_cfg()
    with patch("silentwitness_agent.investigator.build_investigator", return_value=cfg):
        result = await investigate(tmp_path, "aj", "test prompt")
    assert result.final_state == "COMPLETED"
    assert result.model_used == "test"
    assert result.time_elapsed_ms >= 0


@pytest.mark.anyio
async def test_investigate_max_iterations_path(tmp_path: Path) -> None:
    from pydantic_ai.exceptions import UsageLimitExceeded

    cfg = _make_test_cfg()

    async def _fail(*_a: object, **_kw: object) -> None:
        raise UsageLimitExceeded("request limit reached")

    with (
        patch("silentwitness_agent.investigator.build_investigator", return_value=cfg),
        patch.object(cfg.agent, "run", side_effect=_fail),
    ):
        result = await investigate(tmp_path, "aj", "test prompt")
    assert result.final_state == "MAX_ITERATIONS"
    assert result.model_used == "test"
