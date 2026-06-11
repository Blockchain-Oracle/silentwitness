"""Unit tests for critic factory and types — ≥6 tests per story spec.

No network calls — uses pydantic-ai's built-in TestModel stub and fake API
keys (keys are validated at call-time, not at Agent construction for Anthropic).
"""

from __future__ import annotations

import pytest
from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel

from silentwitness_agent.critic import (
    CriticDeps,
    CriticReport,
    CriticVerdict,
    StagedFinding,
    _select_model_str,
    build_critic,
)
from silentwitness_common.types import Confidence

# ---------------------------------------------------------------------------
# 1. System prompt content
# ---------------------------------------------------------------------------


def test_system_prompt_contains_fresh_context_phrase() -> None:
    from silentwitness_agent.critic import _SYSTEM_PROMPT

    assert "do NOT have access to the investigator's reasoning chain" in _SYSTEM_PROMPT


def test_system_prompt_contains_evaluate_against_evidence_phrase() -> None:
    from silentwitness_agent.critic import _SYSTEM_PROMPT

    assert "evaluate" in _SYSTEM_PROMPT and "cited" in _SYSTEM_PROMPT


def test_system_prompt_excludes_forbidden_phrases() -> None:
    from silentwitness_agent.critic import _SYSTEM_PROMPT

    assert "court-admissible" not in _SYSTEM_PROMPT
    assert "Ralph Wiggum" not in _SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# 2. Factory — model resolution
# ---------------------------------------------------------------------------


def test_factory_default_model_is_opus(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SILENTWITNESS_CRITIC_MODEL", raising=False)
    monkeypatch.delenv("SILENTWITNESS_MODEL", raising=False)
    monkeypatch.delenv("SILENTWITNESS_CRITIC_FAST", raising=False)
    assert _select_model_str(None) == "anthropic:claude-opus-4-7"


def test_factory_honours_critic_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CRITIC_MODEL", "test")
    agent = build_critic()
    assert isinstance(agent.model, TestModel)


def test_factory_falls_back_to_silentwitness_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SILENTWITNESS_CRITIC_MODEL", raising=False)
    monkeypatch.delenv("SILENTWITNESS_CRITIC_FAST", raising=False)
    monkeypatch.setenv("SILENTWITNESS_MODEL", "test")
    agent = build_critic()
    assert isinstance(agent.model, TestModel)


def test_factory_critic_fast_selects_haiku(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SILENTWITNESS_CRITIC_MODEL", raising=False)
    monkeypatch.setenv("SILENTWITNESS_CRITIC_FAST", "1")
    assert "haiku" in _select_model_str(None)


def test_factory_direct_model_arg_overrides_all_envs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CRITIC_MODEL", "anthropic:claude-opus-4-7")
    monkeypatch.setenv("SILENTWITNESS_CRITIC_FAST", "1")
    agent = build_critic(model="test")
    assert isinstance(agent.model, TestModel)


# ---------------------------------------------------------------------------
# 3. No MCP toolset — architecturally required
# ---------------------------------------------------------------------------


def test_critic_agent_has_no_toolset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CRITIC_MODEL", "test")
    agent = build_critic()
    toolsets = getattr(agent, "_user_toolsets", [])
    assert len(toolsets) == 0, f"Critic must have no toolset; got: {toolsets}"


# ---------------------------------------------------------------------------
# 4. Type schema
# ---------------------------------------------------------------------------


def test_critic_deps_has_expected_fields() -> None:
    expected = {"case_dir", "examiner", "findings_to_review"}
    assert set(CriticDeps.model_fields) == expected


def test_critic_report_has_expected_fields() -> None:
    expected = {"verdicts", "tokens_spent", "time_elapsed_ms"}
    assert set(CriticReport.model_fields) == expected


def test_critic_verdict_has_expected_fields() -> None:
    expected = {"finding_id", "verdict", "reason", "suggested_revision", "missing_corroboration"}
    assert set(CriticVerdict.model_fields) == expected


def test_staged_finding_is_frozen() -> None:
    from pydantic import ValidationError

    f = StagedFinding(
        finding_id="f-001",
        observation_text="obs",
        interpretation_text="interp",
        confidence=Confidence.HIGH,
    )
    with pytest.raises((ValidationError, TypeError)):
        f.finding_id = "mutated"  # type: ignore[misc]


def test_staged_finding_is_importable() -> None:
    assert StagedFinding is not None


# ---------------------------------------------------------------------------
# 5. build_critic returns a Model instance
# ---------------------------------------------------------------------------


def test_build_critic_returns_model_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CRITIC_MODEL", "test")
    agent = build_critic()
    assert isinstance(agent.model, Model)
