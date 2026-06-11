"""Persisted state for CriticTrigger.

Stored as ``critic_state.json`` in the case directory so a server restart
resumes the firing cadence without re-reviewing already-critiqued findings.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class _TriggerState(BaseModel):
    """Atomic snapshot of the critic-trigger watermarks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Default to now() so bare construction never triggers the time threshold.
    last_critic_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_critic_finding_count: int = Field(default=0, ge=0)


__all__ = ["_TriggerState"]
