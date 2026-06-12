"""Pydantic v2 models for the accuracy scorer (split from scorer.py per ≤400 LOC gate)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class FindingClassification(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    finding_id: str
    side: Literal["baseline", "silentwitness"]
    classification: Literal["TRUE_POSITIVE", "FALSE_POSITIVE", "HALLUCINATION", "FALSE_NEGATIVE"]
    matched_ground_truth_id: str | None
    reason: Literal[
        "CITED_ARTIFACT_PRESENT_AND_MATCHED",
        "CITED_ARTIFACT_PRESENT_BUT_GT_MISS",
        "CITED_ARTIFACT_NOT_PRESENT",
        "NO_FINDING_FOR_GT",
    ]
    evidence_shellout_argv: list[str] | None
    evidence_shellout_hits: int | None


class HallucinationExample(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    side: Literal["baseline", "silentwitness"]
    finding_id: str
    cited_artifact_path: str
    evidence_shellout_argv: list[str]
    evidence_shellout_hits: int
    excerpt: str = Field(max_length=200)


class ScoringMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_id: str
    side: Literal["baseline", "silentwitness"]
    true_positives: int = Field(ge=0)
    false_positives: int = Field(ge=0)
    hallucinations: int = Field(ge=0)
    false_negatives: int = Field(ge=0)
    time_to_first_finding_seconds: float | None
    time_to_handoff_ready_report_seconds: float | None
    total_findings_emitted: int = Field(ge=0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives + self.hallucinations
        return self.true_positives / denom if denom else 0.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 0.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def hallucination_rate(self) -> float:
        denom = self.true_positives + self.false_positives + self.hallucinations
        return self.hallucinations / denom if denom else 0.0


class ScoringReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_id: str
    commit_sha: str = Field(min_length=1)
    scored_at: datetime
    baseline: ScoringMetrics
    silentwitness: ScoringMetrics
    classifications: list[FindingClassification]
    notes: list[str]
    hallucination_examples: list[HallucinationExample]
