"""Pydantic v2 schema for ground-truth findings (Epic 14 — accuracy harness)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

CategoryLiteral = Literal[
    "user_profile",
    "installed_tool",
    "credential",
    "network_indicator",
    "timestamp",
    "file_artifact",
    "persistence",
    "exfiltration",
    "communication",
    "other",
]


class GroundTruthFinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Annotated[str, Field(min_length=1)]
    dataset_id: Literal[
        "rocba", "nitroba", "nist-data-leakage", "nist-hacking-case", "case-trapdoor"
    ]
    category: CategoryLiteral
    summary: Annotated[str, Field(min_length=1, max_length=200)]
    expected_artifact_substrings: Annotated[
        list[Annotated[str, Field(min_length=1)]], Field(min_length=1)
    ]
    expected_path_globs: list[Annotated[str, Field(min_length=1)]]
    supporting_question_id: Annotated[str, Field(min_length=1)] | None
    source: Literal["nist_pdf", "community_writeup", "hand_crafted", "synthetic_spec"]
    source_url: HttpUrl | None
    source_excerpt: Annotated[str, Field(min_length=1, max_length=500)] | None

    @model_validator(mode="after")
    def _require_url_for_external_source(self) -> GroundTruthFinding:
        if self.source != "hand_crafted" and self.source_url is None:
            raise ValueError(f"source_url is required when source={self.source!r}")
        return self


class SHA256MismatchError(Exception):
    """Raised when a cached file's SHA256 does not match the committed pin."""
