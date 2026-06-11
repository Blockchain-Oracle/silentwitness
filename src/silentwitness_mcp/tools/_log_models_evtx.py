"""EvtxECmd output models — EvtxRecord, EvtxOutput, caveats, EID list."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Final

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, computed_field


def _parse_dt(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=UTC)
    s = str(v).strip()
    # EvtxECmd emits 7-digit fractional-second UTC strings without 'Z' suffix;
    # fromisoformat (Python 3.11+) handles arbitrary fractional digits.
    # astimezone() on a naive datetime assumes system timezone — wrong for UTC data;
    # replace() stamps UTC without re-interpreting the wall-clock value.
    dt = datetime.fromisoformat(s)
    return dt.astimezone(UTC) if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _strip_or_none(v: Any) -> str | None:
    if not isinstance(v, str):
        return None
    stripped = v.strip()
    return stripped if stripped else None


_DT = Annotated[datetime, BeforeValidator(_parse_dt)]
_OptStr = Annotated[str | None, BeforeValidator(_strip_or_none)]


class EvtxRecord(BaseModel):
    # extra="forbid": EvtxECmd emits exactly these 23 columns for all channels.
    model_config = ConfigDict(frozen=True, extra="forbid")

    EventId: Annotated[int, Field(ge=0)]
    Channel: str
    Provider: str
    Computer: str
    TimeCreated: _DT
    EventRecordId: str  # string in EvtxECmd output — NOT an int
    Level: str
    RecordNumber: Annotated[int, Field(ge=0)]
    UserName: _OptStr = Field(default=None)
    RemoteHost: _OptStr = Field(default=None)
    ExecutableInfo: _OptStr = Field(default=None)
    HiddenRecord: _OptStr = Field(default=None)
    SourceFile: _OptStr = Field(default=None)
    Keywords: _OptStr = Field(default=None)
    UserId: _OptStr = Field(default=None)
    MapDescription: _OptStr = Field(default=None)
    Payload: _OptStr = Field(default=None)
    PayloadData1: _OptStr = Field(default=None)
    PayloadData2: _OptStr = Field(default=None)
    PayloadData3: _OptStr = Field(default=None)
    PayloadData4: _OptStr = Field(default=None)
    PayloadData5: _OptStr = Field(default=None)
    PayloadData6: _OptStr = Field(default=None)


class EvtxOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    records: tuple[EvtxRecord, ...]
    truncated: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def row_count(self) -> int:
        return len(self.records)


PARSE_EVTX_CAVEATS: Final[tuple[str, ...]] = (
    "EvtxECmd cannot parse old EVT (Windows XP/2003) format; cannot render data"
    " for custom event providers whose manifests are missing — fields may appear"
    " as raw template binding",
    "Application/System logs referencing absent provider manifests render EventData"
    " as raw XML payload rather than friendly columns; corroborate with"
    " hayabusa_csv_timeline for rule-tagged interpretation",
)

_PARSE_EVTX_CORROBORATION: Final[tuple[str, ...]] = (
    "hayabusa_csv_timeline — Sigma-rule-driven timeline over the same EVTX channel",
    "chainsaw_hunt — lateral-movement and persistence rule set over the same EVTX",
)

# Canonical Security-channel EID list for --inc translation.
# EvtxECmd's --inc filters by EID, NOT by channel name literal.
_SECURITY_CHANNEL_EIDS: Final[tuple[int, ...]] = (
    1102,
    4624,
    4625,
    4634,
    4647,
    4648,
    4672,
    4673,
    4674,
    4688,
    4697,
    4698,
    4702,
    4720,
    4722,
    4723,
    4724,
    4725,
    4732,
    4738,
    4740,
    4756,
    4768,
    4769,
    4771,
    4776,
    5140,
    5145,
    5156,
    5158,
)

__all__ = [
    "PARSE_EVTX_CAVEATS",
    "_PARSE_EVTX_CORROBORATION",
    "_SECURITY_CHANNEL_EIDS",
    "EvtxOutput",
    "EvtxRecord",
]
