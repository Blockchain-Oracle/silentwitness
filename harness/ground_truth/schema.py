"""Pydantic v2 schema for ground-truth findings (Epic 14 — accuracy harness)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class GroundTruthFinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Annotated[str, Field(min_length=1)]
    dataset_id: Literal["nitroba", "nist-data-leakage", "nist-hacking-case", "case-trapdoor"]
    category: Literal[
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
    summary: Annotated[str, Field(min_length=1, max_length=200)]
    expected_artifact_substrings: Annotated[
        list[Annotated[str, Field(min_length=1)]], Field(min_length=1)
    ]
    expected_path_globs: list[Annotated[str, Field(min_length=1)]]
    supporting_question_id: str | None
    source: Literal["nist_pdf", "community_writeup", "hand_crafted", "synthetic_spec"]
    source_url: HttpUrl | None
    source_excerpt: Annotated[str, Field(min_length=1, max_length=500)] | None


class SHA256MismatchError(Exception):
    """Raised when a cached file's SHA256 does not match the committed pin."""
