"""Typed models for parse_prefetch (PECmd wrapper).

Column reality (verified against context/domain/06 §5.5 + story notes):
 - PECmd emits PreviousRun0..PreviousRun6 (max 7 prior runs — Win10/11
   stores last 8 total: LastRun + 7 prior). Format version 17/23 (Win7/8)
   rows have all PreviousRunN columns present but empty in the CSV —
   previous_run_times will be () for those entries.
 - FilesLoaded and Directories are single CSV cells with items separated
   by ``", "`` (comma-space). Split on parse; do NOT deduplicate.
 - Volume columns are hardcoded max-2 (Volume0* / Volume1*). Overflow
   surfaces in the ``Note`` column via PECmd itself.
 - ParsingError is a string "True"/"False" in the CSV — coerced to bool."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

# extra="ignore": _coerce_and_extract extracts PreviousRunN columns before
# Pydantic's extra-field policy fires; remaining unknowns are PECmd-version-
# specific. Contrast with AmcacheEntry (extra="forbid") — stable schema.
_ROW_CONFIG = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)
_OUT_CONFIG = ConfigDict(frozen=True, extra="forbid")

_COMMA_SEP = ", "


class PrefetchEntry(BaseModel):
    """One row from PECmd CSV output."""

    model_config = _ROW_CONFIG

    executable_name: str = Field(alias="ExecutableName")
    hash: str = Field(alias="Hash")
    source_filename: str = Field(alias="SourceFilename")
    run_count: int = Field(alias="RunCount")
    last_run: datetime | None = Field(default=None, alias="LastRun")
    previous_run_times: tuple[datetime, ...] = Field(default=())
    volume0_name: str | None = Field(default=None, alias="Volume0Name")
    volume0_serial: str | None = Field(default=None, alias="Volume0Serial")
    volume0_created: datetime | None = Field(default=None, alias="Volume0Created")
    volume1_name: str | None = Field(default=None, alias="Volume1Name")
    volume1_serial: str | None = Field(default=None, alias="Volume1Serial")
    volume1_created: datetime | None = Field(default=None, alias="Volume1Created")
    note: str | None = Field(default=None, alias="Note")
    files_loaded: tuple[str, ...] = Field(default=(), alias="FilesLoaded")
    directories: tuple[str, ...] = Field(default=(), alias="Directories")
    parsing_error: bool = Field(default=False, alias="ParsingError")

    @model_validator(mode="before")
    @classmethod
    def _coerce_and_extract(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # Extract PreviousRun0..6 before extra="ignore" discards them.
        prev: list[str] = []
        for i in range(7):
            v = (data.get(f"PreviousRun{i}") or "").strip()
            if v:
                prev.append(v)
        data["previous_run_times"] = prev

        # Split comma-separated list cells.
        for col in ("FilesLoaded", "Directories"):
            raw = (data.get(col) or "").strip()
            data[col] = [x.strip() for x in raw.split(_COMMA_SEP) if x.strip()]

        # Coerce ParsingError string → bool.
        pe = (data.get("ParsingError") or "False").strip()
        data["ParsingError"] = pe in ("True", "true", "1", "Yes", "yes")

        # Coerce empty/whitespace-only strings → None for optional fields.
        for k in (
            "LastRun",
            "Volume0Name",
            "Volume0Serial",
            "Volume0Created",
            "Volume1Name",
            "Volume1Serial",
            "Volume1Created",
            "Note",
        ):
            if not (data.get(k) or "").strip():
                data[k] = None
        return data

    @model_validator(mode="after")
    def _check_run_times_bound(self) -> PrefetchEntry:
        if len(self.previous_run_times) > 7:
            raise ValueError(
                f"PECmd emits at most 7 PreviousRunN columns; got {len(self.previous_run_times)}"
            )
        return self


class PrefetchOutput(BaseModel):
    """Parsed PECmd CSV. Entries preserve PECmd output order."""

    model_config = _OUT_CONFIG
    entries: tuple[PrefetchEntry, ...]
    truncated: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def row_count(self) -> int:
        return len(self.entries)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def parsing_error_count(self) -> int:
        return sum(1 for e in self.entries if e.parsing_error)


PREFETCH_CAVEATS: tuple[str, ...] = (
    (
        "Prefetch confirms execution; Win10/11 records the last 8 run times per binary "
        "(Win7 records last 1) — read all eight, not just LastRun"
    ),
    (
        "Prefetch records files/DLLs loaded in the first ~10 seconds of execution only "
        "— later loads (e.g. side-loaded DLLs) do NOT appear"
    ),
    (
        "Up to 1024 .pf entries retained system-wide (historical cap); LRU eviction "
        "when full — absence is not proof of non-execution"
    ),
    (
        "Prefetcher is disabled by default on Windows Server — absence on a server host "
        r"is uninformative; check HKLM\SYSTEM\CurrentControlSet\Control\Session Manager"
        r"\Memory Management\PrefetchParameters\EnablePrefetcher first"
    ),
)

PREFETCH_CORROBORATION: tuple[str, ...] = (
    "parse_amcache — file presence from a separate evidence source",
    "parse_shimcache — AppCompat evaluation presence (different evidence source)",
    "vol_pslist — confirm if the process is still running",
)


__all__ = [
    "PREFETCH_CAVEATS",
    "PREFETCH_CORROBORATION",
    "PrefetchEntry",
    "PrefetchOutput",
]
