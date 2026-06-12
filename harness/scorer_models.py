"""Pydantic v2 models for the accuracy scorer (split from scorer.py per ≤400 LOC gate)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class FindingClassification(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    finding_id: str = Field(min_length=1)
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
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_paired_evidence(self) -> FindingClassification:
        # argv and hits must be both-None or both-non-None (FALSE_NEGATIVE is both-None)
        if (self.evidence_shellout_argv is None) != (self.evidence_shellout_hits is None):
            # Allow legacy HALLUCINATION case where argv=None but hits=0 (no cited paths)
            if not (
                self.classification == "HALLUCINATION"
                and self.evidence_shellout_argv is None
                and self.evidence_shellout_hits == 0
            ):
                raise ValueError("evidence_shellout_argv and evidence_shellout_hits must pair")
        return self


class HallucinationExample(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    side: Literal["baseline", "silentwitness"]
    finding_id: str
    cited_artifact_path: str
    evidence_shellout_argv: list[str]
    evidence_shellout_hits: int
    excerpt: str = Field(max_length=200)


class ScoringMetrics(BaseModel):
    # extra="ignore" — computed_field properties (precision/recall/hallucination_rate)
    # are serialized to JSON but must be ignored on re-validation (they re-derive from ints).
    model_config = ConfigDict(frozen=True, extra="ignore")

    dataset_id: str
    side: Literal["baseline", "silentwitness"]
    true_positives: int = Field(ge=0)
    false_positives: int = Field(ge=0)
    hallucinations: int = Field(ge=0)
    false_negatives: int = Field(ge=0)
    time_to_first_finding_seconds: float | None = Field(default=None, ge=0.0)
    time_to_handoff_ready_report_seconds: float | None = Field(default=None, ge=0.0)
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

    dataset_id: str = Field(min_length=1)
    commit_sha: str = Field(min_length=1)
    scored_at: datetime
    baseline: ScoringMetrics
    silentwitness: ScoringMetrics
    classifications: list[FindingClassification]
    notes: list[str]
    hallucination_examples: list[HallucinationExample]

    @model_validator(mode="after")
    def _check_invariants(self) -> ScoringReport:
        if self.baseline.side != "baseline":
            raise ValueError("baseline.side must equal 'baseline'")
        if self.silentwitness.side != "silentwitness":
            raise ValueError("silentwitness.side must equal 'silentwitness'")
        if self.baseline.dataset_id != self.dataset_id:
            raise ValueError("baseline.dataset_id must match report.dataset_id")
        if self.silentwitness.dataset_id != self.dataset_id:
            raise ValueError("silentwitness.dataset_id must match report.dataset_id")
        for m in (self.baseline, self.silentwitness):
            if m.true_positives + m.false_positives + m.hallucinations != m.total_findings_emitted:
                raise ValueError(
                    f"{m.side} counts mismatch: "
                    f"tp+fp+hall={m.true_positives + m.false_positives + m.hallucinations} "
                    f"!= total_findings_emitted={m.total_findings_emitted}"
                )
        return self
