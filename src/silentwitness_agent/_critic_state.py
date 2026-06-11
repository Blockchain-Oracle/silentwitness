"""Persisted state for CriticTrigger.

Stored as ``critic_state.json`` in the case directory so a server restart
resumes the firing cadence without re-reviewing already-critiqued findings.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict

_EPOCH: datetime = datetime.fromtimestamp(0, tz=UTC)


class _TriggerState(BaseModel):
    """Atomic snapshot of the critic-trigger watermarks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    last_critic_at: datetime = _EPOCH
    last_critic_finding_count: int = 0


__all__ = ["_EPOCH", "_TriggerState"]
