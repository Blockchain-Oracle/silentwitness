"""Integration tests — investigator agent provider switching via SILENTWITNESS_MODEL.

Verifies that the factory selects the correct provider for the two primary
providers (Anthropic and OpenAI).  No network calls are made — the agent is
constructed only, not run.  A fake API key is supplied so the provider can
instantiate its client (keys are validated at call-time, not construction-time).
"""

from __future__ import annotations

import pytest

from silentwitness_agent.investigator import build_investigator


def test_anthropic_provider_selected_by_model_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SILENTWITNESS_MODEL=anthropic:... routes through the Anthropic provider."""
    monkeypatch.setenv("SILENTWITNESS_MODEL", "anthropic:claude-opus-4-7")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-construction")

    cfg = build_investigator()

    assert cfg.model_str == "anthropic:claude-opus-4-7"
    assert "anthropic" in repr(cfg.agent.model).lower()


def test_openai_provider_selected_by_model_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SILENTWITNESS_MODEL=openai:... routes through the OpenAI provider."""
    monkeypatch.setenv("SILENTWITNESS_MODEL", "openai:gpt-5")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-construction")

    cfg = build_investigator()

    assert cfg.model_str == "openai:gpt-5"
    assert "openai" in repr(cfg.agent.model).lower()
