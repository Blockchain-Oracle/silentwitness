"""Anthropic prompt-caching settings for the agent loop (Phase 4 — performance).

The investigator runs up to ~50 iterations per case, and every iteration re-sends
the *unchanged* tool-definition schemas (the largest stable block) plus the system
instructions. Without caching that prefix is billed at full input price every
iteration — the dominant, repeated cost.

Anthropic prompt caching turns iterations 2..N into a 0.1x cache *read* of that
prefix (a 90% discount), refreshing the TTL for free on each hit. We cache both
the tool definitions and the system instructions.

Two deliberate choices:

* **1-hour TTL, not 5 minutes.** Forensic tool calls (Volatility / Zeek) take
  minutes per step, so a 5-minute cache would expire between iterations and waste
  the (1.25x-2x) cache write. 1h keeps the prefix warm across a whole run.
* **Anthropic-only, gated on the resolved model.** ``AnthropicModelSettings`` is
  provider-specific; returning ``None`` for any non-Anthropic model preserves the
  model-agnostic contract (PRD §5 FR3) — OpenAI/other models simply run uncached.
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

_CACHE_TTL: Final[Literal["1h"]] = "1h"


def cache_settings(model: Model) -> ModelSettings | None:
    """Return prompt-caching ``ModelSettings`` for an Anthropic model, else ``None``.

    Pass the result as ``Agent(..., model_settings=cache_settings(resolved))``.
    """
    from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings

    if not isinstance(model, AnthropicModel):
        return None
    return AnthropicModelSettings(
        anthropic_cache_tool_definitions=_CACHE_TTL,
        anthropic_cache_instructions=_CACHE_TTL,
    )


__all__ = ["cache_settings"]
