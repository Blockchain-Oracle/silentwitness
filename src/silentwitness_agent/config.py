"""SilentWitnessConfig — layered TOML + env-var configuration.

Precedence (lowest → highest): defaults → ~/.silentwitnessrc.toml →
./.silentwitnessrc.toml → SILENTWITNESS_* env vars → --config-file.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

_BASE = ConfigDict(frozen=True, extra="forbid")


class ModelConfig(BaseModel):
    model_config = _BASE
    default: str = "anthropic:claude-opus-4-7-1m"
    critic: str = "anthropic:claude-haiku-4-5"


class BudgetConfig(BaseModel):
    model_config = _BASE
    max_steps: int = Field(default=200, ge=1)
    max_tokens: int = Field(default=800_000, ge=1)


class ExaminerConfig(BaseModel):
    model_config = _BASE
    name: str = Field(default_factory=lambda: os.environ.get("USER", "examiner"))


class HudConfig(BaseModel):
    model_config = _BASE
    enabled: bool = False
    port: int = Field(default=8088, ge=1, le=65535)
    bind: str = "127.0.0.1"


class EvidenceConfig(BaseModel):
    model_config = _BASE
    require_ro_mount: bool = True


class OutputConfig(BaseModel):
    model_config = _BASE
    color: Literal["auto", "always", "never"] = "auto"
    emoji: Literal["status", "none"] = "status"


class SilentWitnessConfig(BaseModel):
    model_config = _BASE
    model: ModelConfig = Field(default_factory=lambda: ModelConfig())
    budget: BudgetConfig = Field(default_factory=lambda: BudgetConfig())
    examiner: ExaminerConfig = Field(default_factory=lambda: ExaminerConfig())
    hud: HudConfig = Field(default_factory=lambda: HudConfig())
    evidence: EvidenceConfig = Field(default_factory=lambda: EvidenceConfig())
    output: OutputConfig = Field(default_factory=lambda: OutputConfig())


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------


def _read_toml(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"invalid TOML in {path}: {exc}") from exc


def _merge(base: dict[str, object], overlay: dict[str, object]) -> dict[str, object]:
    """One-level deep dict merge — section keys merged, scalar keys overwritten.

    Depth is intentionally limited to one level because TOML config sections map
    directly to Pydantic sub-models; deeper merging would require schema introspection.
    """
    result = dict(base)
    for key, val in overlay.items():
        if isinstance(val, dict) and isinstance(result.get(key), dict):
            merged_sec = {**cast(dict[str, object], result[key]), **val}
            result[key] = merged_sec
        else:
            result[key] = val
    return result


_ENV_MAP: dict[str, tuple[str, str]] = {
    "SILENTWITNESS_MODEL": ("model", "default"),
    "SILENTWITNESS_CRITIC_MODEL": ("model", "critic"),
    "SILENTWITNESS_MAX_STEPS": ("budget", "max_steps"),
    "SILENTWITNESS_MAX_TOKENS": ("budget", "max_tokens"),
    "SILENTWITNESS_EXAMINER": ("examiner", "name"),
    "SILENTWITNESS_COLOR": ("output", "color"),
}

_INT_FIELDS = {"max_steps", "max_tokens"}


def _env_overrides() -> dict[str, object]:
    overrides: dict[str, object] = {}
    for env_key, (section, field) in _ENV_MAP.items():
        raw = os.environ.get(env_key)
        if raw is None:
            continue
        sec: dict[str, object] = overrides.setdefault(section, {})  # type: ignore[assignment]
        if field in _INT_FIELDS:
            try:
                sec[field] = int(raw)
            except ValueError as exc:
                raise ValueError(f"invalid value for {env_key}={raw!r} — expected integer") from exc
        else:
            sec[field] = raw
    return overrides


def load_config(config_file: Path | None = None) -> SilentWitnessConfig:
    """Merge all config layers and return a frozen SilentWitnessConfig."""
    home_rc = Path.home() / ".silentwitnessrc.toml"
    cwd_rc = Path.cwd() / ".silentwitnessrc.toml"
    merged: dict[str, object] = {}
    merged = _merge(merged, _read_toml(home_rc))
    if cwd_rc.resolve() != home_rc.resolve():
        merged = _merge(merged, _read_toml(cwd_rc))
    merged = _merge(merged, _env_overrides())
    if config_file is not None:
        merged = _merge(merged, _read_toml(config_file))
    return SilentWitnessConfig.model_validate(merged)


__all__ = [
    "BudgetConfig",
    "EvidenceConfig",
    "ExaminerConfig",
    "HudConfig",
    "ModelConfig",
    "OutputConfig",
    "SilentWitnessConfig",
    "load_config",
]
