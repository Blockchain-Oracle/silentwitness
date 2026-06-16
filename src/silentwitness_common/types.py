"""Shared Pydantic v2 contracts — single source of truth across MCP + agent.

Centralises shared types to prevent drift across tool-wrappers,
report-renderer, and audit-logger (architecture.md §4.3 ToolResponse,
§4.4 AuditEntry, §5.4 report-as-state).
All models use ``frozen=True`` + ``extra="forbid"`` except ``Finding``.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Generic, TypeVar

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from silentwitness_common.ids import assert_audit_id_format, require_audit_id_str


def _normalise_hex(value: object) -> str:
    """Lowercase + reject non-``str`` (incl. ``bytes``, which Pydantic would
    otherwise UTF-8-decode silently — PR-92 silent-failure surface)."""
    if not isinstance(value, str):
        raise ValueError(f"Sha256Hex requires str, got {type(value).__name__}")
    return value.lower()


# 64-char lowercase SHA-256 hex digest. Used by every model that carries the
# citation-gate primitive. Pydantic v2 reads the ``Annotated[...]`` metadata
# and applies the BeforeValidator + StringConstraints automatically.
type Sha256Hex = Annotated[
    str,
    BeforeValidator(_normalise_hex),
    StringConstraints(pattern=r"^[a-f0-9]{64}$"),
]

# AuditId (architecture §4.4). Order matters: BeforeValidator rejects
# non-str (PR-92 bytes-coercion) → core validation does
# str_strip_whitespace + min_length → AfterValidator enforces the
# sift-<slug>-<YYYYMMDD>-<NNN> shape. Do NOT swap the format check to
# BeforeValidator (would skip the whitespace strip).
type AuditId = Annotated[
    str,
    BeforeValidator(require_audit_id_str),
    StringConstraints(min_length=1),
    AfterValidator(assert_audit_id_format),
]


# ---------------------------------------------------------------------------
# Enums — string-valued so JSON round-trips preserve them as readable strings
# (vs IntEnum which would round-trip as opaque integers).
# ---------------------------------------------------------------------------


class Confidence(StrEnum):
    """Interpretation strength. Overrides ``<``/``>`` to semantic rank and
    raises ``TypeError`` on non-Confidence comparands (returning
    ``NotImplemented`` would let the reflected fallback re-dispatch to
    ``str.__lt__`` and silently compare alphabetically — PR-92 catch).
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

    @property
    def rank(self) -> int:
        return {"LOW": 0, "MEDIUM": 1, "HIGH": 2}[self.value]

    def _ranked(self, other: object) -> int:
        if not isinstance(other, Confidence):
            raise TypeError(
                f"Confidence comparison expects another Confidence, got {type(other).__name__}"
            )
        return other.rank

    def __lt__(self, other: object) -> bool:
        return self.rank < self._ranked(other)

    def __le__(self, other: object) -> bool:
        return self.rank <= self._ranked(other)

    def __gt__(self, other: object) -> bool:
        return self.rank > self._ranked(other)

    def __ge__(self, other: object) -> bool:
        return self.rank >= self._ranked(other)


class EvidenceType(StrEnum):
    DISK_IMAGE = "disk_image"
    MEMORY_DUMP = "memory_dump"
    EVTX = "evtx"
    PCAP = "pcap"
    HIVE = "hive"
    IDS_RULES = "ids_rules"
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
    ATTACK = "attack"
    RECOMMENDATIONS = "recommendations"
    GAPS = "gaps"
    APPENDIX_AUDIT = "appendix_audit"


class LedgerItemType(StrEnum):
    """Kind of item recorded in the HMAC-signed approval ledger (architecture §4.9)."""

    FINDING = "finding"
    OBSERVATION = "observation"
    INTERPRETATION = "interpretation"
    TIMELINE_EVENT = "timeline_event"


class FindingStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    FINAL = "FINAL"
    ARCHIVED = "ARCHIVED"


# ---------------------------------------------------------------------------
# Core types — citation + provenance
# ---------------------------------------------------------------------------

_BASE_CONFIG = ConfigDict(
    frozen=True,
    extra="forbid",
    str_strip_whitespace=True,
)


class CitedSpan(BaseModel):
    """Agent-emitted citation against the evidence index (architecture §4.5).

    The agent cites one parsed evidence row by its ``record_id`` (the ``id``
    returned on a ``search_evidence`` / ``get_record`` hit) and quotes the
    exact ``span_text`` it relies on. The citation gate resolves the record
    and verifies ``span_text`` is a verbatim substring of the record's stored
    text; provenance (``audit_id`` / ``source_tool`` / ``sha256``) is read
    from the authoritative record, never supplied by the agent."""

    model_config = _BASE_CONFIG

    record_id: int = Field(ge=1)
    span_text: str = Field(min_length=1)


class DataProvenance(BaseModel):
    """Per-tool-call provenance carried inside ``ToolResponse``."""

    model_config = _BASE_CONFIG

    tool: str = Field(min_length=1, description="snake_case tool name (e.g. `vol_pslist`).")
    stdout_path: Path = Field(description="Absolute path to the stored normalised output blob.")
    result_sha256: Sha256Hex = Field(
        description="SHA-256 of the full normalised output (NOT just a prefix)."
    )
    elapsed_ms: float = Field(ge=0.0, description="Wall-clock time the tool ran for.")
    cmd_argv: tuple[str, ...] = Field(
        description="The exact argv used to invoke the underlying CLI. Stored as "
        "tuple so frozen=True propagates immutability — architecture.md §4.3 "
        "types this as list[str]; the tuple is a code-level tightening since a "
        "frozen=True model with a list field would still allow .append()."
    )


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
    audit_ids: tuple[AuditId, ...] = Field(
        min_length=1,
        description="audit_ids of every MCP tool call this observation derives from.",
    )

    @field_validator("cited_spans")
    @classmethod
    def _non_empty_spans(cls, value: tuple[CitedSpan, ...]) -> tuple[CitedSpan, ...]:
        if not value:
            raise ValueError("Observation.cited_spans must contain at least one span")
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
        if any(not o.strip() for o in value):
            raise ValueError(
                "Interpretation.observation_ids cannot contain empty/whitespace entries"
            )
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

    Not frozen — ``status`` transitions DRAFT → REVIEWED → FINAL → ARCHIVED
    over the case lifecycle. ``validate_assignment=True`` ensures runtime
    mutations go through the same validation as construction (PR-92 fix).
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)

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


class EvidenceRecord(BaseModel):
    """Persisted entry in ``cases/<case_id>/evidence.json`` (architecture §4.10).
    The (path, sha256) pair is the citation gate's ground truth."""

    model_config = _BASE_CONFIG

    path: Path = Field(description="Canonical resolved absolute path.")
    type: EvidenceType
    sha256: Sha256Hex
    size_bytes: int = Field(ge=0)
    registered_at: datetime
    registered_audit_id: AuditId


class VerifyResult(BaseModel):
    """Outcome of :meth:`EvidenceRegistry.verify_hash` — bit-rot detector."""

    model_config = _BASE_CONFIG

    matches: bool
    expected: Sha256Hex
    actual: Sha256Hex


class LedgerEntry(BaseModel):
    """One line of HMAC-signed approval ledger (architecture §4.9). No
    ``str_strip_whitespace`` — forensic integrity demands exact bytes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ts: datetime
    item_id: str = Field(
        min_length=1,
        pattern=r"^[^\x00\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029]+$",
        description="e.g. F-001, O-042, I-007. NUL-free + line-terminator-free.",
    )
    item_type: LedgerItemType
    content_hash: Sha256Hex
    hmac: Sha256Hex
    examiner: str = Field(
        min_length=1,
        pattern=r"^[^\x00\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029]+$",
        description="Line-terminator-free so JSONL append cannot break the ledger.",
    )


class AuditEntry(BaseModel):
    """One line of audit/<backend>.jsonl — canonical schema for the audit row.

    Consumers MUST NOT extend or relax this model (``extra='forbid'``,
    ``frozen=True``). ``prev_record_hash`` is ``None`` for the first row of
    a chain; ``record_hash`` is mandatory once chaining is enabled and
    ``None`` on the legacy plain-JSONL fallback path. The chain is verified
    by :func:`silentwitness_mcp.audit.chain.verify_chain_lines`."""

    model_config = _BASE_CONFIG

    ts: datetime
    audit_id: AuditId
    tool: str = Field(min_length=1)
    params: dict[str, object]
    result_summary: dict[str, object]
    result_sha256: Sha256Hex
    stdout_path: Path
    elapsed_ms: float = Field(ge=0.0)
    examiner: str = Field(min_length=1)
    model_used: str = Field(min_length=1)
    model_token_count: dict[str, int] = Field(default_factory=dict)
    prev_record_hash: Sha256Hex | None = None
    record_hash: Sha256Hex | None = None


TPayload = TypeVar("TPayload", bound=BaseModel)


# Pydantic <2.11 loses PEP 695 generic narrowing on model_validate_json — drop
# the noqa once the lockfile floor reaches 2.11+.
class ToolResponse(BaseModel, Generic[TPayload]):  # noqa: UP046
    """MCP tool envelope (architecture.md §4.3). Invariant: ``success=True``
    ⇒ ``data`` not None; ``success=False`` ⇒ ``data=None`` and ``caveats``
    explains. Aliased as ``ResponseEnvelope`` for arch-doc readers."""

    model_config = _BASE_CONFIG

    success: bool
    data: TPayload | None = None
    audit_id: AuditId
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


class WorkflowError(Exception):
    """Base class for agent workflow lifecycle errors (budget, state violations)."""


ResponseEnvelope = ToolResponse
