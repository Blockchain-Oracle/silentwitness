"""The four specialists must inherit a non-Anthropic SILENTWITNESS_MODEL.

Without this, setting SILENTWITNESS_MODEL=openai:* switches the investigator
to OpenAI but leaves the specialists pinned to the Anthropic default — which
fails under an OpenAI-only key. These tests lock the model-agnostic contract
(PRD §5 FR3) at the specialist resolution layer.
"""

from __future__ import annotations

import pytest
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel

from silentwitness_agent.specialists.disk import (
    _resolve_specialist_model as resolve_disk,
)
from silentwitness_agent.specialists.log import (
    _resolve_specialist_model as resolve_log,
)
from silentwitness_agent.specialists.memory import (
    _resolve_specialist_model as resolve_memory,
)
from silentwitness_agent.specialists.network import (
    _resolve_specialist_model as resolve_network,
)

_RESOLVERS = [
    ("disk", resolve_disk, "SILENTWITNESS_SPECIALIST_MODEL_DISK"),
    ("log", resolve_log, "SILENTWITNESS_SPECIALIST_MODEL_LOG"),
    ("memory", resolve_memory, "SILENTWITNESS_SPECIALIST_MODEL_MEMORY"),
    ("network", resolve_network, "SILENTWITNESS_SPECIALIST_MODEL_NETWORK"),
]

_ALL_ENV = [
    "SILENTWITNESS_MODEL",
    "SILENTWITNESS_MODEL_QUALITY",
    "SILENTWITNESS_SPECIALIST_MODEL_DISK",
    "SILENTWITNESS_SPECIALIST_MODEL_LOG",
    "SILENTWITNESS_SPECIALIST_MODEL_MEMORY",
    "SILENTWITNESS_SPECIALIST_MODEL_NETWORK",
]


def _clear(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _ALL_ENV:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")  # pragma: allowlist secret
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")  # pragma: allowlist secret


@pytest.mark.parametrize(("name", "resolve", "_env"), _RESOLVERS)
def test_specialist_inherits_global_openai_model(
    name: str,
    resolve: object,
    _env: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("SILENTWITNESS_MODEL", "openai:gpt-4o")
    model = resolve(None)  # type: ignore[operator]
    assert isinstance(model, OpenAIChatModel), f"{name} ignored global model"


@pytest.mark.parametrize(("name", "resolve", "env_key"), _RESOLVERS)
def test_per_specialist_env_still_wins_over_global(
    name: str,
    resolve: object,
    env_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("SILENTWITNESS_MODEL", "openai:gpt-4o")
    monkeypatch.setenv(env_key, "anthropic:claude-haiku-4-5")
    model = resolve(None)  # type: ignore[operator]
    assert isinstance(model, AnthropicModel), f"{name} per-specialist override lost"


@pytest.mark.parametrize(("name", "resolve", "_env"), _RESOLVERS)
def test_default_is_anthropic_when_no_global_set(
    name: str,
    resolve: object,
    _env: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear(monkeypatch)
    model = resolve(None)  # type: ignore[operator]
    assert isinstance(model, AnthropicModel), f"{name} default drifted"


@pytest.mark.parametrize(("name", "resolve", "_env"), _RESOLVERS)
def test_invalid_global_model_raises_clear_error(
    name: str,
    resolve: object,
    _env: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("SILENTWITNESS_MODEL", "not-a-valid-model-string")
    with pytest.raises(ValueError, match="SILENTWITNESS_MODEL"):
        resolve(None)  # type: ignore[operator]
