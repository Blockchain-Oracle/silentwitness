"""Typed models for the disk tool family — parallel to
:mod:`_memory_models` but for EZ-Tools CSV row shapes (context/domain
/02 §1 + context/domain/06 §5.1).

MFTECmd column reality (verified against real MFTECmd output, NOT the
saltstack-suggested column list which was stale):
 - ``IsDeleted`` is server-side-derived from ``not InUse`` (NOT a wire
   column — never look for an ``IsDeleted`` header).
 - ``SiFnDelta`` is a wrapper-computed derived alias for ``Timestomped``
   retained as a model attribute for backward-compat reading callers.
   The model_validator below populates it from the input row.
 - ``Timestomped`` and ``uSecZeros`` are real MFTECmd boolean columns
   (zero microseconds across timestamps — common timestomp byproduct)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

_ROW_CONFIG = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)
_OUT_CONFIG = ConfigDict(frozen=True, extra="forbid")
_IN_CONFIG = ConfigDict(frozen=True, extra="forbid")


class MftInput(BaseModel):
    """Inputs for :func:`parse_mft`. Both paths are validated by the
    evidence registry and the mount gate before MFTECmd is spawned."""

    model_config = _IN_CONFIG
    evidence_path: Path
    csv_out: Path


class MFTEntry(BaseModel):
    """One row from MFTECmd CSV. Field names mirror the wire columns
    so the entity gate's citation spans can match by header name; the
    derived ``IsDeleted`` and ``SiFnDelta`` attrs are populated by the
    model_validator from ``InUse`` and ``Timestomped`` respectively."""

    model_config = _ROW_CONFIG

    EntryNumber: int
    SequenceNumber: int
    ParentEntryNumber: int | None = None
    ParentSequenceNumber: int | None = None
    ParentPath: str = ""
    FileName: str = ""
    Extension: str | None = None
    FileSize: int = 0
    IsDirectory: bool = False
    InUse: bool = True
    HasAds: bool = False
    Created0x10: datetime | None = None
    LastModified0x10: datetime | None = None
    LastRecordChange0x10: datetime | None = None
    LastAccess0x10: datetime | None = None
    Created0x30: datetime | None = None
    LastModified0x30: datetime | None = None
    LastRecordChange0x30: datetime | None = None
    LastAccess0x30: datetime | None = None
    Timestomped: bool = False
    uSecZeros: bool = False  # noqa: N815 — mirrors MFTECmd wire column name
    # Server-side-derived columns: NOT in the MFTECmd CSV, populated by
    # the @model_validator below from InUse / Timestomped respectively.
    IsDeleted: bool = False
    SiFnDelta: bool = False

    @model_validator(mode="before")
    @classmethod
    def _derive_isdeleted_and_sifndelta(cls, data: Any) -> Any:
        """Map ``not InUse`` → ``IsDeleted``, ``Timestomped`` →
        ``SiFnDelta``. Also coerces MFTECmd's empty-string sentinels
        (the ``$MFT`` system entry has no FileSize / Extension /
        Parent*) into typed defaults so Pydantic's int validator
        doesn't choke on ``""``. Runs before field validation so the
        typed bool fields land populated."""
        if not isinstance(data, dict):
            return data
        # Empty-string-to-typed-default coercion for the MFTECmd
        # columns that may be blank on system entries ($MFT, $LogFile,
        # etc. — these have no parent and no file size).
        for k in ("FileSize", "ParentEntryNumber", "ParentSequenceNumber"):
            if data.get(k) == "":
                data[k] = None if k != "FileSize" else 0
        if "InUse" in data and "IsDeleted" not in data:
            data["IsDeleted"] = not _coerce_bool(data["InUse"])
        if "Timestomped" in data and "SiFnDelta" not in data:
            data["SiFnDelta"] = _coerce_bool(data["Timestomped"])
        return data


def _coerce_bool(value: Any) -> bool:
    """MFTECmd CSV emits booleans as the strings ``"True"`` / ``"False"``
    via .NET ``Boolean.ToString``. Tolerate empty string + None as
    False, matching MFTECmd's "column was unset on this row" behaviour."""
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return False
    return str(value).strip().lower() == "true"


class MftOutput(BaseModel):
    """Parsed MFT CSV. ``truncated`` is ``True`` when MFTECmd died
    mid-write OR the CSV reader hit a short row — partial-success is
    preferred over a hard reject so the agent can still cite the
    rows that did parse."""

    model_config = _OUT_CONFIG
    entries: tuple[MFTEntry, ...]
    row_count: int
    truncated: bool = False


# Caveat block surfaced verbatim in :attr:`ToolResponse.caveats`
# (architecture §4.3). Order matters: the timestomp action-shaping
# caveat FIRST so an agent skimming caveats[0] gets the analytical
# directive before the build-fragility / column-pin caveats.
MFT_CAVEATS: tuple[str, ...] = (
    (
        "FN ($30) timestamps update only on rename/move; SI ($10) updates on "
        "most file ops — SI/FN divergence on a single record is a classic "
        "timestomping indicator"
    ),
    (
        "MFTECmd writes the CSV to --csv <dir> with a tool-picked filename "
        "(timestamp prefix); the wrapper globs *_MFTECmd_*Output.csv and "
        "reads the most recent match"
    ),
    (
        "IsDeleted is server-side-derived from `not InUse`; SiFnDelta is "
        "the wrapper-computed alias of MFTECmd's Timestomped column — both "
        "are populated by the @model_validator, not the CSV"
    ),
    (
        "uSecZeros (zero microseconds across timestamps) often co-occurs "
        "with timestomping; corroborate with parse_amcache and parse_prefetch "
        "for execution evidence"
    ),
)


__all__ = ["MFT_CAVEATS", "MFTEntry", "MftInput", "MftOutput"]
