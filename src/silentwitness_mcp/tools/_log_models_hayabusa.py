"""Hayabusa csv-timeline output models — HayabusaHit, HayabusaOutput, caveats."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Final

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, computed_field


def _parse_dt(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=UTC)
    s = str(v).strip()
    dt = datetime.fromisoformat(s)
    return dt.astimezone(UTC) if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _split_csv_tags(v: Any) -> list[str]:
    """Split a comma-joined Hayabusa tag string into a list; empty string → []."""
    if not isinstance(v, str):
        return []
    stripped = v.strip()
    if not stripped:
        return []
    return [t.strip() for t in stripped.split() if t.strip()]


def _str_or_none(v: Any) -> str | None:
    if not isinstance(v, str):
        return None
    stripped = v.strip()
    return stripped if stripped else None


_DT = Annotated[datetime, BeforeValidator(_parse_dt)]
_Tags = Annotated[list[str], BeforeValidator(_split_csv_tags)]
_OptStr = Annotated[str | None, BeforeValidator(_str_or_none)]


class HayabusaHit(BaseModel):
    """One detection row from Hayabusa super-verbose CSV output.

    `Details` column (rule match explanation) is aliased to `Detection`
    so callers use idiomatic Python. MitreTags/MitreTactics are split
    from space-separated strings into lists.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    Timestamp: _DT
    RuleTitle: str
    Level: str
    Computer: str
    Channel: str
    EventID: Annotated[int, Field(ge=0, le=65535)]
    RecordID: Annotated[int, Field(ge=0)]
    Detection: _OptStr = Field(default=None, alias="Details")
    MitreTactics: _Tags = Field(default_factory=list)
    MitreTags: _Tags = Field(default_factory=list)
    OtherTags: _OptStr = Field(default=None)
    RuleAuthor: _OptStr = Field(default=None)
    RuleFile: str
    EvtxFile: str


class HayabusaOutput(BaseModel):
    """Parsed output from a Hayabusa csv-timeline run."""

    model_config = ConfigDict(frozen=True)

    hits: tuple[HayabusaHit, ...]
    truncated: bool = Field(
        default=False,
        description="True if parse halted before EOF — hits is an incomplete prefix.",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def row_count(self) -> int:
        return len(self.hits)


HAYABUSA_CAVEATS: Final[tuple[str, ...]] = (
    "Hayabusa output is detection-centric — there is no 'show all 4624 events' mode;"
    " use parse_evtx for raw event enumeration",
    "Hayabusa Sigma rule coverage reflects upstream — rules for very recent threats"
    " may lag; some Sigma correlation features (multi-event sequences) are partially"
    " implemented and may not fire",
    "Channel column may differ on non-English Windows (Windows localizes channel"
    " names in some metadata)",
    "Hayabusa cannot read XML or JSON-dumped events — EVTX format only",
)

_HAYABUSA_CORROBORATION: Final[tuple[str, ...]] = (
    "chainsaw_hunt — cross-engine Sigma corroboration (different mappings → different blind spots)",
    "parse_evtx — raw event enumeration for channels not covered by Hayabusa rules",
)

__all__ = [
    "HAYABUSA_CAVEATS",
    "_HAYABUSA_CORROBORATION",
    "HayabusaHit",
    "HayabusaOutput",
]
