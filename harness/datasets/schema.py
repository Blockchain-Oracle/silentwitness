"""Pydantic v2 schema for dataset manifests (Epic 14 — accuracy harness)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class EvidenceFileRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    relative_path: Annotated[str, Field(min_length=1)]
    sha256: Annotated[
        str,
        Field(pattern=r"^([a-f0-9]{64}|<computed-on-fetch>|<filled-by-epic-15>)$"),
    ]
    size_bytes: Annotated[int, Field(ge=0)]


class DatasetManifest(BaseModel):
    """Pinned description of a forensic evaluation dataset.

    sha256 / size_bytes at the manifest level refer to the *primary* evidence
    file (the E01 or pcap).  Per-file hashes live in evidence_files[].
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_id: Literal["nitroba", "nist-data-leakage", "nist-hacking-case", "case-trapdoor"]
    scenario_summary: Annotated[str, Field(min_length=80, max_length=800)]
    download_url: HttpUrl | None
    sha256: Annotated[
        str,
        Field(pattern=r"^([a-f0-9]{64}|<computed-on-fetch>|<filled-by-epic-15>)$"),
    ]
    size_bytes: Annotated[int, Field(ge=0)]
    evidence_files: list[EvidenceFileRecord]
    expected_investigation_path: list[str]
    ground_truth_status: Literal["public_pdf", "public_writeups", "password_gated", "synthetic"]
    LLM_memorization_risk: Literal["low", "medium", "high", "very_high"]
    memorization_risk_note: Annotated[str, Field(min_length=20)]
    notes: str | None
