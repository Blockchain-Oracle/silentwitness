"""Unit tests for silentwitness_agent.config.load_config (≥6 scenarios)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from silentwitness_agent.config import load_config

# ---------------------------------------------------------------------------
# 1. Defaults when no RC files exist and no env vars set
# ---------------------------------------------------------------------------


def test_defaults_no_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    for key in (
        "SILENTWITNESS_MODEL",
        "SILENTWITNESS_CRITIC_MODEL",
        "SILENTWITNESS_MAX_STEPS",
        "SILENTWITNESS_MAX_TOKENS",
        "SILENTWITNESS_EXAMINER",
        "SILENTWITNESS_COLOR",
    ):
        monkeypatch.delenv(key, raising=False)
    cfg = load_config()
    assert cfg.model.default == "anthropic:claude-opus-4-7-1m"
    assert cfg.model.critic == "anthropic:claude-haiku-4-5"
    assert cfg.budget.max_steps == 200
    assert cfg.budget.max_tokens == 800_000
    assert cfg.hud.enabled is False
    assert cfg.evidence.require_ro_mount is True
    assert cfg.output.color == "auto"


# ---------------------------------------------------------------------------
# 2. ~/.silentwitnessrc.toml is loaded
# ---------------------------------------------------------------------------


def test_home_rc_loaded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: home)
    (home / ".silentwitnessrc.toml").write_text(
        '[model]\ndefault = "openai:gpt-5"\n', encoding="utf-8"
    )
    cfg = load_config()
    assert cfg.model.default == "openai:gpt-5"


# ---------------------------------------------------------------------------
# 3. ./.silentwitnessrc.toml overrides home RC (cwd wins)
# ---------------------------------------------------------------------------


def test_cwd_rc_overrides_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    cwd = tmp_path / "project"
    home.mkdir()
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(Path, "home", lambda: home)
    (home / ".silentwitnessrc.toml").write_text(
        '[model]\ndefault = "openai:gpt-5"\n', encoding="utf-8"
    )
    (cwd / ".silentwitnessrc.toml").write_text(
        '[model]\ndefault = "anthropic:claude-opus-4-7"\n', encoding="utf-8"
    )
    cfg = load_config()
    assert cfg.model.default == "anthropic:claude-opus-4-7"


# ---------------------------------------------------------------------------
# 4. SILENTWITNESS_MODEL env var overrides file
# ---------------------------------------------------------------------------


def test_env_var_overrides_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: home)
    (home / ".silentwitnessrc.toml").write_text(
        '[model]\ndefault = "openai:gpt-5"\n', encoding="utf-8"
    )
    monkeypatch.setenv("SILENTWITNESS_MODEL", "anthropic:claude-sonnet-4-6")
    cfg = load_config()
    assert cfg.model.default == "anthropic:claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# 5. --config-file overrides env var (highest precedence)
# ---------------------------------------------------------------------------


def test_config_file_overrides_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SILENTWITNESS_MODEL", "openai:gpt-5")
    explicit = tmp_path / "explicit.toml"
    explicit.write_text('[model]\ndefault = "anthropic:claude-opus-4-7"\n', encoding="utf-8")
    cfg = load_config(config_file=explicit)
    assert cfg.model.default == "anthropic:claude-opus-4-7"


# ---------------------------------------------------------------------------
# 6. Precedence table: defaults < home < cwd < env < config_file
# ---------------------------------------------------------------------------


def test_full_precedence_chain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(Path, "home", lambda: home)

    (home / ".silentwitnessrc.toml").write_text("[budget]\nmax_steps = 50\n", encoding="utf-8")
    (cwd / ".silentwitnessrc.toml").write_text("[budget]\nmax_steps = 100\n", encoding="utf-8")
    monkeypatch.setenv("SILENTWITNESS_MAX_STEPS", "150")
    explicit = tmp_path / "explicit.toml"
    explicit.write_text("[budget]\nmax_steps = 200\n", encoding="utf-8")

    cfg = load_config(config_file=explicit)
    assert cfg.budget.max_steps == 200


# ---------------------------------------------------------------------------
# 7. Integer env vars are coerced correctly
# ---------------------------------------------------------------------------


def test_int_env_var_coercion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SILENTWITNESS_MAX_STEPS", "42")
    monkeypatch.setenv("SILENTWITNESS_MAX_TOKENS", "100000")
    cfg = load_config()
    assert cfg.budget.max_steps == 42
    assert cfg.budget.max_tokens == 100_000


# ---------------------------------------------------------------------------
# 8. SilentWitnessConfig is frozen (immutable after construction)
# ---------------------------------------------------------------------------


def test_config_is_frozen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    cfg = load_config()
    with pytest.raises((ValidationError, TypeError)):
        cfg.model = cfg.model  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 9. Malformed TOML raises ValueError with path in message
# ---------------------------------------------------------------------------


def test_malformed_toml_raises_value_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    bad = tmp_path / ".silentwitnessrc.toml"
    bad.write_text("[[not valid toml\n", encoding="utf-8")
    with pytest.raises(ValueError, match=str(bad)):
        load_config()


# ---------------------------------------------------------------------------
# 10. Bad integer env var raises ValueError with env key in message
# ---------------------------------------------------------------------------


def test_bad_int_env_var_raises_value_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SILENTWITNESS_MAX_STEPS", "not-an-int")
    with pytest.raises(ValueError, match="SILENTWITNESS_MAX_STEPS"):
        load_config()
