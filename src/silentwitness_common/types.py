"""Shared Pydantic v2 contracts — single source of truth across MCP + agent.

Every tool wrapper, hypothesis-pivot loop, report renderer, audit logger and
HMAC ledger imports from here. Splitting the types across packages would let
two parallel definitions of ``Observation`` drift; centralising them is the
forcing function that keeps the wedge ("every claim ties back to a tool
execution") mechanical.

References:
  - architecture.md §4.3 — Response envelope (``ToolResponse[TPayload]``)
  - architecture.md §4.4 — Audit log entry shape
  - architecture.md §5.4 — Report-as-state finding shape
  - PRD §FR5 — audit_id format

All models use ``frozen=True`` (no in-place mutation) and ``extra="forbid"``
(unknown fields raise) except ``Finding``, which has a mutable ``status``
field that legitimately transitions DRAFT → REVIEWED → FINAL → ARCHIVED
across the case lifecycle.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Enums — string-valued so JSON round-trips preserve them as readable strings
# (vs IntEnum which would round-trip as opaque integers).
# ---------------------------------------------------------------------------


class Confidence(StrEnum):
    """How strongly an interpretation is supported by its observations."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

    @property
    def rank(self) -> int:
        return {"LOW": 0, "MEDIUM": 1, "HIGH": 2}[self.value]

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Confidence):
            return NotImplemented
        return self.rank < other.rank

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Confidence):
            return NotImplemented
        return self.rank <= other.rank

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Confidence):
            return NotImplemented
        return self.rank > other.rank

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Confidence):
            return NotImplemented
        return self.rank >= other.rank


class EvidenceType(StrEnum):
    DISK_IMAGE = "disk_image"
    MEMORY_DUMP = "memory_dump"
    EVTX = "evtx"
    PCAP = "pcap"
    HIVE = "hive"
    OTHER = "other"


class HypothesisStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CONFIRMED = "CONFIRMED"
    PIVOTED = "PIVOTED"
    ABANDONED = "ABANDONED"


class SpecialistName(StrEnum):
    MEMORY = "MEMORY"
    DISK = "DISK"
    NETWORK = "NETWORK"
    LOG = "LOG"


class ReportSection(StrEnum):
    EXECUTIVE_SUMMARY = "executive_summary"
    ENGAGEMENT_OVERVIEW = "engagement_overview"
    METHODOLOGY = "methodology"
    FINDINGS = "findings"
    TIMELINE = "timeline"
    IOCS = "iocs"
    RECOMMENDATIONS = "recommendations"
    GAPS = "gaps"
    APPENDIX_AUDIT = "appendix_audit"


class FindingStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    FINAL = "FINAL"
    ARCHIVED = "ARCHIVED"


class CriticVerdict(StrEnum):
    AGREE = "AGREE"
    CHALLENGE = "CHALLENGE"
    REJECT = "REJECT"


# ---------------------------------------------------------------------------
# Core types — citation + provenance
# ---------------------------------------------------------------------------

_BASE_CONFIG = ConfigDict(
    frozen=True,
    extra="forbid",
    str_strip_whitespace=True,
)


class CitedSpan(BaseModel):
    """A byte- or line-range reference to a span of stored tool output.

    The MCP server's citation gate (architecture.md §4.5) re-reads the
    referenced file at evaluation time, hashes the cited slice, and refuses
    the observation if the recorded ``content_sha256`` does not match. This
    is the load-bearing primitive of the wedge.
    """

    model_config = _BASE_CONFIG

    stdout_path: Path = Field(
        description="Absolute path to the normalised tool-output blob produced "
        "by a prior MCP tool call (DataProvenance.stdout_path)."
    )
    line_start: int = Field(ge=1, description="1-indexed first line of the span (inclusive).")
    line_end: int = Field(ge=1, description="1-indexed last line of the span (inclusive).")
    content_sha256: str = Field(
        min_length=64,
        max_length=64,
        description="SHA-256 hex digest of the cited byte range. "
        "The citation gate verifies this on every observation.",
    )

    @model_validator(mode="after")
    def _check_line_range(self) -> CitedSpan:
        if self.line_end < self.line_start:
            msg = f"line_end ({self.line_end}) must be >= line_start ({self.line_start})"
            raise ValueError(msg)
        return self

    @field_validator("content_sha256")
    @classmethod
    def _check_hex(cls, value: str) -> str:
        try:
            int(value, 16)
        except ValueError as exc:
            raise ValueError(f"content_sha256 must be hex; got {value!r}") from exc
        return value.lower()


class DataProvenance(BaseModel):
    """Per-tool-call provenance carried inside ``ToolResponse``."""

    model_config = _BASE_CONFIG

    tool: str = Field(min_length=1, description="snake_case tool name (e.g. `vol_pslist`).")
    stdout_path: Path = Field(description="Absolute path to the stored normalised output blob.")
    result_sha256: str = Field(
        min_length=64,
        max_length=64,
        description="SHA-256 of the full normalised output (NOT just a prefix).",
    )
    elapsed_ms: float = Field(ge=0.0, description="Wall-clock time the tool ran for.")
    cmd_argv: tuple[str, ...] = Field(
        description="The exact argv used to invoke the underlying CLI. "
        "Stored as tuple so frozen=True propagates immutability."
    )

    @field_validator("result_sha256")
    @classmethod
    def _check_hex(cls, value: str) -> str:
        try:
            int(value, 16)
        except ValueError as exc:
            raise ValueError(f"result_sha256 must be hex; got {value!r}") from exc
        return value.lower()


# ---------------------------------------------------------------------------
# Domain objects — Observation → Interpretation → Pivot → Finding
# ---------------------------------------------------------------------------


class Observation(BaseModel):
    """A factual claim about an artefact, locked to its citation."""

    model_config = _BASE_CONFIG

    id: str = Field(min_length=1, description="Observation ID (typically O-NNN).")
    summary: str = Field(min_length=1, description="One-sentence factual statement.")
    cited_spans: tuple[CitedSpan, ...] = Field(
        description="Non-empty list of cited spans. The citation gate "
        "re-verifies each at evaluation time."
    )
    audit_ids: tuple[str, ...] = Field(
        description="audit_ids of every MCP tool call this observation derives from."
    )

    @field_validator("cited_spans")
    @classmethod
    def _non_empty_spans(cls, value: tuple[CitedSpan, ...]) -> tuple[CitedSpan, ...]:
        if not value:
            raise ValueError("Observation.cited_spans must contain at least one span")
        return value

    @field_validator("audit_ids")
    @classmethod
    def _non_empty_audit_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("Observation.audit_ids must contain at least one audit_id")
        return value


class Interpretation(BaseModel):
    """An inferential claim built on one or more observations."""

    model_config = _BASE_CONFIG

    id: str = Field(min_length=1, description="Interpretation ID (typically I-NNN).")
    summary: str = Field(min_length=1)
    confidence: Confidence
    observation_ids: tuple[str, ...] = Field(
        description="IDs of the Observations this interpretation rests on."
    )
    rationale: str = Field(
        min_length=1, description="Why these observations support this interpretation."
    )

    @field_validator("observation_ids")
    @classmethod
    def _non_empty(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("Interpretation.observation_ids must be non-empty")
        return value


class Pivot(BaseModel):
    """A hypothesis-stack transition: which leaf was abandoned, what we pursue next."""

    model_config = _BASE_CONFIG

    from_hypothesis_id: str = Field(min_length=1)
    to_hypothesis_id: str = Field(min_length=1)
    reason: str = Field(min_length=1, description="Why the prior hypothesis was abandoned.")
    at: datetime


class Finding(BaseModel):
    """A reportable finding — observation + interpretation pair with a lifecycle.

    NOTE: this is the only model in this module that is NOT frozen. The
    ``status`` field transitions DRAFT → REVIEWED → FINAL → ARCHIVED across
    the case lifecycle. Other fields are still effectively immutable by
    convention (the agent re-emits Findings rather than mutating in place).
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1, description="Finding ID (typically F-NNN).")
    observation_id: str = Field(min_length=1)
    interpretation_id: str = Field(min_length=1)
    status: FindingStatus = Field(default=FindingStatus.DRAFT)
    title: str = Field(default="", description="Short heading rendered in the report.")
    corroborating_finding_ids: tuple[str, ...] = Field(default_factory=tuple)
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Infrastructure — audit log entry + response envelope
# ---------------------------------------------------------------------------


class AuditEntry(BaseModel):
    """One line of audit/<backend>.jsonl. Verbatim BRAINSTORM §4 schema."""

    model_config = _BASE_CONFIG

    ts: datetime
    audit_id: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    params: dict[str, object]
    result_summary: dict[str, object]
    result_sha256: str = Field(min_length=64, max_length=64)
    stdout_path: Path
    elapsed_ms: float = Field(ge=0.0)
    examiner: str = Field(min_length=1)
    model_used: str = Field(min_length=1)
    model_token_count: dict[str, int] = Field(default_factory=dict)

    @field_validator("result_sha256")
    @classmethod
    def _check_hex(cls, value: str) -> str:
        try:
            int(value, 16)
        except ValueError as exc:
            raise ValueError(f"result_sha256 must be hex; got {value!r}") from exc
        return value.lower()


TPayload = TypeVar("TPayload", bound=BaseModel)


class ToolResponse(BaseModel, Generic[TPayload]):
    """The envelope every MCP tool returns. architecture.md §4.3.

    ``success=True`` ⇒ ``data is not None``. ``success=False`` ⇒ ``data is
    None`` and ``caveats`` carries the failure explanation. The MCP server
    enforces this invariant when constructing responses; downstream code can
    rely on it without re-checking.

    Aliased as ``ResponseEnvelope`` for sites that read the architecture-doc
    name; both names refer to the same model.
    """

    model_config = _BASE_CONFIG

    success: bool
    data: TPayload | None = None
    audit_id: str = Field(min_length=1)
    examiner: str = Field(min_length=1)
    caveats: tuple[str, ...] = Field(default_factory=tuple)
    advisories: tuple[str, ...] = Field(default_factory=tuple)
    corroboration: tuple[str, ...] = Field(default_factory=tuple)
    discipline_reminder: str | None = None
    data_provenance: DataProvenance

    @model_validator(mode="after")
    def _success_implies_data(self) -> ToolResponse[TPayload]:
        if self.success and self.data is None:
            raise ValueError("ToolResponse.success=True requires non-None data")
        if not self.success and self.data is not None:
            raise ValueError("ToolResponse.success=False requires data=None")
        return self


# Architecture-doc alias.
ResponseEnvelope = ToolResponse
