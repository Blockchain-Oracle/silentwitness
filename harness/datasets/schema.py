"""Pydantic v2 schema for dataset manifests (Epic 14 — accuracy harness)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

_PLACEHOLDERS: frozenset[str] = frozenset({"<computed-on-fetch>", "<filled-by-epic-15>"})


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

    sha256 / size_bytes at the manifest level are synced from the first entry
    in evidence_files[] by recompute_manifest.py.  By convention this is the
    primary binary (E01 or pcap); the schema enforces consistency when both
    sides carry real hashes (not placeholders).
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
    expected_investigation_path: list[Annotated[str, Field(min_length=1)]]
    ground_truth_status: Literal["public_pdf", "public_writeups", "password_gated", "synthetic"]
    LLM_memorization_risk: Literal["low", "medium", "high", "very_high"]
    memorization_risk_note: Annotated[str, Field(min_length=20)]
    notes: Annotated[str, Field(min_length=1)] | None

    @model_validator(mode="after")
    def _sha256_consistent_with_primary(self) -> DatasetManifest:
        if self.sha256 in _PLACEHOLDERS:
            return self
        if self.evidence_files and self.evidence_files[0].sha256 not in _PLACEHOLDERS:
            if self.sha256 != self.evidence_files[0].sha256:
                raise ValueError(
                    f"manifest sha256 {self.sha256!r} does not match "
                    f"evidence_files[0].sha256 {self.evidence_files[0].sha256!r}"
                )
        return self
