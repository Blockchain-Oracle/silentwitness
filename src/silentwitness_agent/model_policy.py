"""Provider-aware model defaults used to avoid hidden expensive nested calls."""

from __future__ import annotations

DEFAULT_INVESTIGATOR_MODEL = "anthropic:claude-sonnet-4-6"
DEFAULT_CRITIC_MODEL = "anthropic:claude-haiku-4-5"
DEFAULT_SPECIALIST_MODEL = "anthropic:claude-haiku-4-5"
HIGH_QUALITY_ANTHROPIC_MODEL = "anthropic:claude-sonnet-4-6"

PROVIDER_COST_OPTIMIZED_MODELS = {
    "anthropic": "anthropic:claude-haiku-4-5",
    "openai": "openai:gpt-5-mini",
    "openai-chat": "openai-chat:gpt-5-mini",
    "openai-responses": "openai-responses:gpt-5-mini",
    "google": "google:gemini-2.5-flash",
    "google-gla": "google-gla:gemini-2.5-flash",
}


def cost_optimized_model_for_provider(model_str: str) -> str:
    """Return a cheaper same-provider sibling for nested agent calls."""
    provider, sep, model_name = model_str.partition(":")
    if not sep:
        return model_str

    normalized_model = model_name.lower()
    if provider == "anthropic" and "haiku" in normalized_model:
        return model_str
    if provider in {"openai", "openai-chat", "openai-responses"} and any(
        marker in normalized_model for marker in ("mini", "nano")
    ):
        return model_str
    if provider in {"google", "google-gla"} and "flash" in normalized_model:
        return model_str
    return PROVIDER_COST_OPTIMIZED_MODELS.get(provider, model_str)


__all__ = [
    "DEFAULT_CRITIC_MODEL",
    "DEFAULT_INVESTIGATOR_MODEL",
    "DEFAULT_SPECIALIST_MODEL",
    "HIGH_QUALITY_ANTHROPIC_MODEL",
    "PROVIDER_COST_OPTIMIZED_MODELS",
    "cost_optimized_model_for_provider",
]
