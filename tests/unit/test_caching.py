"""Unit tests for silentwitness_agent._caching.cache_settings.

The caching helper is provider-gated: Anthropic models get prompt-caching
settings (1h TTL on tool definitions + instructions); any non-Anthropic model
returns ``None`` so the model-agnostic contract (PRD §5 FR3) holds.
"""

from __future__ import annotations

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
