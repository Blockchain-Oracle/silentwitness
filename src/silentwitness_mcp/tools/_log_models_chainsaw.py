"""Chainsaw hunt output models — ChainsawHit, ChainsawOutput, caveats."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated, Any, Final, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, computed_field

ChainsawLevel = Literal["info", "low", "medium", "high", "critical"]
ChainsawRuleSource = Literal["sigma", "chainsaw"]

_MITRE_RE: Final = re.compile(r"attack\.(t\d+(?:\.\d+)*)", re.IGNORECASE)


def _parse_dt(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=UTC)
    s = str(v).strip()
    dt = datetime.fromisoformat(s)
    return dt.astimezone(UTC) if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _str_list(v: Any) -> list[str]:
    if isinstance(v, list):
        return [str(x) for x in v if x]
    if isinstance(v, str):
        return [v] if v.strip() else []
    return []


def _extract_mitre(v: Any) -> list[str]:
    tags = _str_list(v)
    return [m.group(1).upper() for t in tags if (m := _MITRE_RE.search(t))]


_DT = Annotated[datetime, BeforeValidator(_parse_dt)]
_StrList = Annotated[list[str], BeforeValidator(_str_list)]
_MitreList = Annotated[list[str], BeforeValidator(_extract_mitre)]


class ChainsawHit(BaseModel):
    """One detection row from Chainsaw hunt JSON output.

    Chainsaw v2 JSON output is a flat array; each entry is a single
    matched event. ``RuleSource`` ("sigma"/"chainsaw") distinguishes
    rule origin; mapped from the raw JSON ``source`` key. ``MitreAttack``
    is parsed from T-code tokens in ``Tags`` (e.g., "attack.t1059.001" →
    "T1059.001"). ``FoundInLine`` is the raw event payload from
    ``document.data``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    Name: Annotated[str, Field(min_length=1)]
    Authors: _StrList = Field(default_factory=list)
    Tags: _StrList = Field(default_factory=list)
    MitreAttack: _MitreList = Field(default_factory=list)
    RuleLevel: ChainsawLevel
    RuleSource: ChainsawRuleSource
    Channel: Annotated[str, Field(min_length=1)]
    EventID: Annotated[int, Field(ge=0, le=65535)]
    RecordID: Annotated[int, Field(ge=0)]
    Timestamp: _DT
    FoundInLine: dict[str, Any]


class ChainsawOutput(BaseModel):
    """Parsed output from a Chainsaw hunt run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    hits: tuple[ChainsawHit, ...]
    truncated: bool = Field(
        default=False,
        description=(
            "True if at least one entry failed validation or could not be flattened."
            " hits may contain non-contiguous rows when individual bad entries were skipped."
        ),
    )
    rules_loaded: Annotated[int, Field(ge=0)] | None = Field(
        default=None,
        description="Number of rules loaded; always None — stderr parsing not yet implemented.",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def row_count(self) -> int:
        return len(self.hits)


CHAINSAW_CAVEATS: Final[tuple[str, ...]] = (
    "Chainsaw hunt operates on Windows EVTX only; analyse sub-commands cover"
    " ShimCache and SRUM but are not a general artifact framework",
    "Chainsaw is slightly slower than Hayabusa on identical workloads; different"
    " parser behaviour means the two engines occasionally fire different rules on"
    " the same input — cross-engine corroboration is the intended pattern",
    "Chainsaw needs a mapping YAML to translate Sigma field names to the EVTX event"
    " XML structure; absent or wrong mapping → silent zero-detection result",
)

CHAINSAW_CORROBORATION: Final[tuple[str, ...]] = (
    "if hayabusa_csv_timeline fired no detections, also run chainsaw_hunt for"
    " cross-engine corroboration",
    "if hayabusa_csv_timeline fired a critical, run chainsaw_hunt as second opinion"
    " before staging as a finding",
)

__all__ = [
    "CHAINSAW_CAVEATS",
    "CHAINSAW_CORROBORATION",
    "ChainsawHit",
    "ChainsawLevel",
    "ChainsawOutput",
    "ChainsawRuleSource",
]
