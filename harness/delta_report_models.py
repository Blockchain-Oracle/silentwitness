"""Pydantic v2 models for the delta report (split from delta_report.py per ≤400 LOC gate)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Direction = Literal["higher_is_better", "lower_is_better", "neutral"]
MetricName = Literal[
    "precision",
    "recall",
    "hallucination_rate",
    "time_to_first_finding_seconds",
    "time_to_handoff_ready_report_seconds",
    "pivot_count",
    "epistemic_honesty_count",
]
METRIC_DIRECTIONS: dict[MetricName, Direction] = {
    "precision": "higher_is_better",
    "recall": "higher_is_better",
    "hallucination_rate": "lower_is_better",
    "time_to_first_finding_seconds": "lower_is_better",
    "time_to_handoff_ready_report_seconds": "lower_is_better",
    "pivot_count": "neutral",
    "epistemic_honesty_count": "higher_is_better",
}


class DeltaRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: MetricName
    baseline_value: float | None
    silentwitness_value: float | None
    delta: float | None
    direction: Direction
    interpretation: str = Field(min_length=1)


class HallucinationCallout(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    cited_artifact_path: str
    side: Literal["baseline", "silentwitness"]
    excerpt: str = Field(max_length=200)
    evidence_shellout_argv: list[str]
    evidence_shellout_hits: int = Field(ge=0)


class DeltaReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_id: str = Field(min_length=1)
    baseline_result_path: Path
    silentwitness_result_path: Path
    scoring_result_path: Path
    generated_at: datetime
    rows: list[DeltaRow]
    baseline_hallucinated_callouts: list[HallucinationCallout]
    silentwitness_refused_callouts: list[HallucinationCallout]
