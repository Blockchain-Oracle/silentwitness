"""Unit tests for the _case_env bridge — the load-bearing contract that carries
the case across the MCP stdio boundary. Pure functions, no I/O.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from silentwitness_mcp._case_env import (
    ENV_CASE_DIR,
    ENV_EXAMINER,
    ENV_MODEL_USED,
    build_server_env,
    read_case_env,
)


def test_build_server_env_carries_case_vars() -> None:
    env = build_server_env(Path("/cases/c1"), "aj", "anthropic:claude-opus-4-7")
    assert env[ENV_CASE_DIR] == "/cases/c1"
    assert env[ENV_EXAMINER] == "aj"
    assert env[ENV_MODEL_USED] == "anthropic:claude-opus-4-7"


def test_build_server_env_passes_present_vars_and_drops_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-value")  # pragma: allowlist secret
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    env = build_server_env(Path("/c"), "aj", "m")
    # A regression that drops ANTHROPIC_API_KEY/PATH from PASSTHROUGH_ENV would
    # silently break MCP sampling / shutil.which on the box — this guards it.
    assert env["ANTHROPIC_API_KEY"] == "fake-key-value"  # pragma: allowlist secret
    assert "OPENAI_API_KEY" not in env  # unset passthrough var is not emitted


def test_read_case_env_roundtrips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_CASE_DIR, "/cases/c2")
    monkeypatch.setenv(ENV_EXAMINER, "bob")
    monkeypatch.setenv(ENV_MODEL_USED, "anthropic:claude-sonnet-4-6")
    case = read_case_env()
    assert case is not None
    assert case.case_dir == Path("/cases/c2")
    assert case.examiner == "bob"
    assert case.model_used == "anthropic:claude-sonnet-4-6"


def test_read_case_env_is_none_when_any_var_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    # The all-or-nothing contract _case_deps depends on: a partial env is None,
    # so a half-bound server never reaches a tool body.
    monkeypatch.setenv(ENV_CASE_DIR, "/cases/c3")
    monkeypatch.setenv(ENV_EXAMINER, "bob")
    monkeypatch.delenv(ENV_MODEL_USED, raising=False)
    assert read_case_env() is None
