"""Anthropic prompt-caching settings for the agent loop (Phase 4 — performance).

The investigator can run many iterations per case (bounded by
``investigator._DEFAULT_MAX_ITERS``), and every iteration re-sends
the *unchanged* tool-definition schemas (the largest stable block) plus the system
instructions. Without caching that prefix is billed at full input price every
iteration — the dominant, repeated cost.

Anthropic prompt caching turns iterations 2..N into a 0.1x cache *read* of that
prefix (a 90% discount), refreshing the TTL for free on each hit. We cache both
the tool definitions and the system instructions.

Two deliberate choices:

* **1-hour TTL, not 5 minutes.** Forensic tool calls (Volatility / Zeek) take
  minutes per step, so a 5-minute cache would expire between iterations and waste
  the 2x 1-hour cache write (vs the cheaper 1.25x 5-minute write we deliberately
  forgo). 1h keeps the prefix warm across a whole run.
* **Anthropic-only, gated on the resolved model.** ``cache_control`` is an
  Anthropic-specific API, so ``AnthropicModelSettings`` only applies to Anthropic
  models. Returning ``None`` for any other provider preserves the model-agnostic
  contract: OpenAI and Gemini cache the prefix *automatically* server-side, so
  they need no explicit setting — they are not running "uncached".
"""

from __future__ import annotations

import logging
from typing import Final, Literal

from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

_LOG = logging.getLogger(__name__)

_CACHE_TTL: Final[Literal["1h"]] = "1h"


def cache_settings(model: Model) -> ModelSettings | None:
    """Return prompt-caching ``ModelSettings`` for an Anthropic model, else ``None``.

    Pass the result as ``Agent(..., model_settings=cache_settings(resolved))``.
    """
    from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings

    model_name = getattr(model, "model_name", type(model).__name__)
    if not isinstance(model, AnthropicModel):
        # Not a bug: non-Anthropic providers cache automatically server-side. We
        # log so a billing diff can confirm explicit cache_control was off here.
        _LOG.debug("prompt caching: %s is non-Anthropic; no explicit cache_control", model_name)
        return None
    _LOG.debug("prompt caching: enabled (1h TTL) for %s", model_name)
    return AnthropicModelSettings(
        anthropic_cache_tool_definitions=_CACHE_TTL,
        anthropic_cache_instructions=_CACHE_TTL,
    )


__all__ = ["cache_settings"]
