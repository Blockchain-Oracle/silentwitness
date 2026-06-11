"""FindingEvent model and ReportSubscriber protocol for the report event bus.

The hypothesis stack (Epic 8) emits FindingEvent instances; ReportWriter
subscribes via the ReportSubscriber protocol.
"""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class FindingEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_type: Literal[
        "observation_staged",
        "interpretation_staged",
        "pivot_staged",
        "finding_approved",
        "finding_archived",
    ]
    finding_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    ts: AwareDatetime


class ReportSubscriber(Protocol):
    def on_finding_event(self, event: FindingEvent) -> None: ...


__all__ = ["FindingEvent", "ReportSubscriber"]
