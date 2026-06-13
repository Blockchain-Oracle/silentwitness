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
    build_disk_specialist,
)
from silentwitness_agent.specialists.log import (
    _resolve_specialist_model as resolve_log,
    build_log_specialist,
)
from silentwitness_agent.specialists.memory import (
    _resolve_specialist_model as resolve_memory,
    build_memory_specialist,
)
from silentwitness_agent.specialists.network import (
    _resolve_specialist_model as resolve_network,
    build_network_specialist,
)

_RESOLVERS = [
    ("disk", resolve_disk, "SILENTWITNESS_SPECIALIST_MODEL_DISK"),
    ("log", resolve_log, "SILENTWITNESS_SPECIALIST_MODEL_LOG"),
    ("memory", resolve_memory, "SILENTWITNESS_SPECIALIST_MODEL_MEMORY"),
    ("network", resolve_network, "SILENTWITNESS_SPECIALIST_MODEL_NETWORK"),
]

_BUILDERS = [
    ("disk", build_disk_specialist),
    ("log", build_log_specialist),
    ("memory", build_memory_specialist),
    ("network", build_network_specialist),
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
    # Error names the env var AND the specialist, so an operator knows which.
    with pytest.raises(ValueError, match=rf"{name} specialist: SILENTWITNESS_MODEL"):
        resolve(None)  # type: ignore[operator]


@pytest.mark.parametrize(("name", "resolve", "_env"), _RESOLVERS)
def test_global_model_outranks_quality_high(
    name: str,
    resolve: object,
    _env: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The explicit global provider must win over the quality knob, whose
    # high-quality id is hardcoded Anthropic — otherwise an OpenAI-only key
    # would 401. This pins the deliberate precedence (regression guard for a
    # future reorder of the two branches).
    _clear(monkeypatch)
    monkeypatch.setenv("SILENTWITNESS_MODEL", "openai:gpt-4o")
    monkeypatch.setenv("SILENTWITNESS_MODEL_QUALITY", "high")
    model = resolve(None)  # type: ignore[operator]
    assert isinstance(model, OpenAIChatModel), f"{name}: quality=high defeated global model"


@pytest.mark.parametrize(("name", "resolve", "_env"), _RESOLVERS)
def test_quality_high_applies_when_no_global(
    name: str,
    resolve: object,
    _env: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("SILENTWITNESS_MODEL_QUALITY", "high")
    model = resolve(None)  # type: ignore[operator]
    assert isinstance(model, AnthropicModel), f"{name}: quality=high not honoured"


@pytest.mark.parametrize(("name", "resolve", "_env"), _RESOLVERS)
def test_empty_global_falls_through_to_default(
    name: str,
    resolve: object,
    _env: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Empty string must behave like unset, not raise.
    _clear(monkeypatch)
    monkeypatch.setenv("SILENTWITNESS_MODEL", "")
    model = resolve(None)  # type: ignore[operator]
    assert isinstance(model, AnthropicModel), f"{name}: empty global mishandled"


@pytest.mark.parametrize(("name", "build"), _BUILDERS)
def test_build_site_runs_on_inherited_global_model(
    name: str,
    build: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The hot path: build_*_specialist() must produce an Agent whose model is
    # the inherited global one — the resolver being correct is necessary but
    # not sufficient if the builder dropped it.
    _clear(monkeypatch)
    monkeypatch.setenv("SILENTWITNESS_MODEL", "openai:gpt-4o")
    agent = build()  # type: ignore[operator]
    assert isinstance(agent.model, OpenAIChatModel), f"{name}: builder lost the global model"
