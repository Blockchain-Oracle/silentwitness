"""Unit tests for silentwitness_agent._caching.cache_settings.

The caching helper is provider-gated: Anthropic models get prompt-caching
settings (1h TTL on tool definitions + instructions); any non-Anthropic model
returns ``None`` so the model-agnostic contract (PRD §5 FR3) holds.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from silentwitness_agent._caching import cache_settings


def _anthropic(model_name: str) -> AnthropicModel:
    # Dummy key — cache_settings never makes a network call, it only inspects type.
    provider = AnthropicProvider(api_key="sk-ant-test")  # pragma: allowlist secret
    return AnthropicModel(model_name, provider=provider)


def test_anthropic_model_gets_cache_settings() -> None:
    settings = cache_settings(_anthropic("claude-opus-4-7"))
    assert settings is not None
    assert settings["anthropic_cache_tool_definitions"] == "1h"
    assert settings["anthropic_cache_instructions"] == "1h"


def test_anthropic_settings_only_expected_cache_keys() -> None:
    settings = cache_settings(_anthropic("claude-haiku-4-5"))
    assert settings is not None
    # Only the two stable-prefix blocks are cached; messages are intentionally not.
    assert set(settings) == {
        "anthropic_cache_tool_definitions",
        "anthropic_cache_instructions",
    }


def test_non_anthropic_model_returns_none() -> None:
    # TestModel is a non-Anthropic Model — the agnostic path must not cache.
    assert cache_settings(TestModel()) is None


def test_non_anthropic_path_logs_debug(caplog: pytest.LogCaptureFixture) -> None:
    # The no-op is billing-relevant; a DEBUG breadcrumb must be observable.
    with caplog.at_level(logging.DEBUG, logger="silentwitness_agent._caching"):
        cache_settings(TestModel())
    assert any("non-Anthropic" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Wiring: the six Agent build sites must actually pass model_settings.
# The existing 189 construction tests resolve to TestModel (cache_settings ->
# None), so a silent drop of this kwarg would go unnoticed. These assert the
# settings reach the constructor for a real Anthropic model, and are absent for
# a non-Anthropic one — locking the model-agnostic contract at the wiring layer.
# ---------------------------------------------------------------------------

_ANTHROPIC_MODEL = "anthropic:claude-haiku-4-5"


def _build_all(model: str, case_dir: Path) -> dict[str, object]:
    from silentwitness_agent.critic import build_critic
    from silentwitness_agent.investigator import build_investigator
    from silentwitness_agent.specialists.disk import build_disk_specialist
    from silentwitness_agent.specialists.log import build_log_specialist
    from silentwitness_agent.specialists.memory import build_memory_specialist
    from silentwitness_agent.specialists.network import build_network_specialist

    return {
        "investigator": build_investigator(case_dir, "examiner", model=model).agent,
        "critic": build_critic(model=model),
        "disk": build_disk_specialist(model=model),
        "log": build_log_specialist(model=model),
        "memory": build_memory_specialist(model=model),
        "network": build_network_specialist(model=model),
    }


def test_all_build_sites_wire_cache_for_anthropic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")  # pragma: allowlist secret
    for name, agent in _build_all(_ANTHROPIC_MODEL, tmp_path).items():
        settings = agent.model_settings  # type: ignore[attr-defined]
        assert settings is not None, f"{name}: model_settings not wired"
        assert settings["anthropic_cache_instructions"] == "1h", name
        assert settings["anthropic_cache_tool_definitions"] == "1h", name


def test_all_build_sites_leave_cache_none_for_non_anthropic(tmp_path: Path) -> None:
    # 'test' resolves to TestModel — every site must leave model_settings None.
    for name, agent in _build_all("test", tmp_path).items():
        assert agent.model_settings is None, f"{name}: should be uncached"  # type: ignore[attr-defined]
