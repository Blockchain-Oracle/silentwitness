"""Unit tests for investigator factory — ≥7 tests per story spec.

No network calls — uses pydantic-ai's built-in TestModel stub and fake API
keys (keys are validated at call-time, not at Agent construction).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel

from silentwitness_agent.hypothesis.types import SpecialistName
from silentwitness_agent.investigator import (
    _DEFAULT_MAX_ITERS,
    _DEFAULT_MODEL,
    _SYSTEM_PROMPT,
    InvestigatorDeps,
    InvestigatorResult,
    _AgentConfig,
    _parse_max_iters_env,
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
    # The prompt must name the actual stack-driving tool, not prose.
    assert "pivot_hypothesis" in _SYSTEM_PROMPT
    assert "form_hypothesis" in _SYSTEM_PROMPT


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
    cfg = build_investigator(
        Path("sw-test-case"),
        "tester",
    )
    assert cfg.model_str == "test"


def test_factory_default_model_string() -> None:
    assert _DEFAULT_MODEL == "anthropic:claude-opus-4-7"


def test_factory_direct_model_param_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_MODEL", "anthropic:claude-opus-4-7")
    cfg = build_investigator(Path("sw-test-case"), "tester", model="test")
    assert cfg.model_str == "test"


# ---------------------------------------------------------------------------
# Factory — max_iterations env var
# ---------------------------------------------------------------------------


def test_factory_honours_max_iters_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_MODEL", "test")
    monkeypatch.setenv("SILENTWITNESS_MAX_ITERS", "25")
    cfg = build_investigator(
        Path("sw-test-case"),
        "tester",
    )
    assert cfg.max_iters == 25


def test_factory_default_max_iters() -> None:
    assert _DEFAULT_MAX_ITERS == 50


def test_factory_max_iterations_param_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_MODEL", "test")
    monkeypatch.setenv("SILENTWITNESS_MAX_ITERS", "99")
    cfg = build_investigator(Path("sw-test-case"), "tester", max_iterations=7)
    assert cfg.max_iters == 7


def test_factory_invalid_max_iters_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_MAX_ITERS", "not_a_number")
    with pytest.raises(ValueError, match="SILENTWITNESS_MAX_ITERS"):
        _parse_max_iters_env(50)


def test_factory_zero_max_iters_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_MAX_ITERS", "0")
    with pytest.raises(ValueError, match="must be >= 1"):
        _parse_max_iters_env(50)


# ---------------------------------------------------------------------------
# Factory — MCP toolset
# ---------------------------------------------------------------------------


def test_mcp_toolset_is_mcpserverstdio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_MODEL", "test")
    cfg = build_investigator(
        Path("sw-test-case"),
        "tester",
    )
    toolsets = cfg.agent._user_toolsets
    assert len(toolsets) == 1
    assert isinstance(toolsets[0], MCPServerStdio)


def test_mcp_toolset_command_and_args(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_MODEL", "test")
    cfg = build_investigator(
        Path("sw-test-case"),
        "tester",
    )
    ts: MCPServerStdio = cfg.agent._user_toolsets[0]  # type: ignore[assignment]
    # The running interpreter, not bare "python" (absent on the SIFT OVA / VPS).
    assert ts.command == sys.executable
    assert ts.args == ["-m", "silentwitness_mcp"]


def test_mcp_sampling_model_is_model_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    """sampling_model must be a Model instance (not a raw string) to avoid AttributeError."""
    monkeypatch.setenv("SILENTWITNESS_MODEL", "test")
    cfg = build_investigator(
        Path("sw-test-case"),
        "tester",
    )
    ts: MCPServerStdio = cfg.agent._user_toolsets[0]  # type: ignore[assignment]
    assert isinstance(ts.sampling_model, Model)


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


def test_investigator_result_rejects_negative_counters() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        InvestigatorResult(
            hypotheses_formed=-1,
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


# ---------------------------------------------------------------------------
# _resolve_model — vllm routing and passthrough
# ---------------------------------------------------------------------------


def test_resolve_model_vllm_returns_openai_chat_model() -> None:
    from pydantic_ai.models.openai import OpenAIChatModel

    result = _resolve_model("vllm:http://localhost:8000")
    assert isinstance(result, OpenAIChatModel)


def test_resolve_model_vllm_empty_url_raises() -> None:
    with pytest.raises(ValueError, match="vllm: prefix requires a full HTTP"):
        _resolve_model("vllm:")


def test_resolve_model_vllm_non_http_url_raises() -> None:
    with pytest.raises(ValueError, match="vllm: prefix requires a full HTTP"):
        _resolve_model("vllm:ftp://localhost:8000")


def test_resolve_model_passthrough_returns_model_instance() -> None:
    result = _resolve_model("test")
    assert isinstance(result, Model)


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
    # A dummy MCP server satisfies the dataclass; TestModel never invokes it.
    dummy_server = MCPServerStdio("python", ["-c", "pass"])
    return _AgentConfig(agent=test_agent, model_str=model_str, max_iters=5, mcp_server=dummy_server)


@pytest.mark.anyio
async def test_investigate_completed_path(tmp_path: Path) -> None:
    cfg = _make_test_cfg()
    with patch("silentwitness_agent.investigator.build_investigator", return_value=cfg):
        result = await investigate(tmp_path, "aj", "test prompt")
    assert result.final_state == "COMPLETED"
    assert result.model_used == "test"
    assert result.time_elapsed_ms >= 0
    assert result.findings_staged == 1
    assert result.total_tool_calls == 4
    assert result.hypotheses_formed == 0  # fresh stack, agent ran but no form() calls
    assert result.total_tokens_consumed >= 0


@pytest.mark.anyio
async def test_investigate_max_iterations_path(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    from pydantic_ai.exceptions import UsageLimitExceeded

    cfg = _make_test_cfg()

    async def _fail(*_a: object, **_kw: object) -> None:
        raise UsageLimitExceeded("request limit reached")

    with (
        patch("silentwitness_agent.investigator.build_investigator", return_value=cfg),
        patch.object(cfg.agent, "run", side_effect=_fail),
        caplog.at_level(logging.WARNING),
    ):
        result = await investigate(tmp_path, "aj", "test prompt")

    assert result.final_state == "MAX_ITERATIONS"
    assert result.model_used == "test"
    assert result.findings_staged == 0
    assert result.total_tokens_consumed == 0
    assert "UsageLimitExceeded" in caplog.text


@pytest.mark.anyio
async def test_investigate_max_iterations_abandons_active_hypothesis(tmp_path: Path) -> None:
    """stack.abandon() is called when an active hypothesis exists at MAX_ITERATIONS."""

    from pydantic_ai.exceptions import UsageLimitExceeded

    from silentwitness_agent.hypothesis.stack import HypothesisStack

    cfg = _make_test_cfg()
    pre_seeded_stack = HypothesisStack(case_dir=tmp_path, examiner="aj")
    pre_seeded_stack.form("If persistence, expect Run-key entry", SpecialistName.DISK)

    async def _fail(*_a: object, **_kw: object) -> None:
        raise UsageLimitExceeded("request limit reached")

    with (
        patch("silentwitness_agent.investigator.build_investigator", return_value=cfg),
        patch("silentwitness_agent.investigator.HypothesisStack", return_value=pre_seeded_stack),
        patch.object(cfg.agent, "run", side_effect=_fail),
    ):
        result = await investigate(tmp_path, "aj", "test prompt")

    assert result.final_state == "MAX_ITERATIONS"
    # The active hypothesis is abandoned — stack snapshot should reflect it
    snap = pre_seeded_stack.snapshot()
    from silentwitness_agent.hypothesis.types import HypothesisStatus

    assert snap.active is None  # abandoned, promoted queue was empty
    assert any(h.status == HypothesisStatus.ABANDONED for h in snap.history)
