"""Typed models for parse_amcache and parse_shimcache. Follows the same
snake_case-attribute / PascalCase-alias convention as :mod:`_disk_models`.

Column reality (verified against ``context/domain/06`` §5.3-§5.4):
 - AmcacheParser UnassociatedFileEntries: ``SHA1`` may be empty for
   non-PE entries; ``Size`` NOT ``FileSize``; timestamp column is
   ``FileKeyLastWriteTimestamp`` NOT ``KeyLastWriteTimestamp``.
 - AppCompatCacheParser: ``Executed`` is a tri-state string
   (``"Yes"``/``"No"``/``"NA"``), NOT a bool; Win8/10/11 rows have
   ``"NA"``; Win7 rows carry ``"Yes"``/``"No"``."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

_ROW_CONFIG = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)
_OUT_CONFIG = ConfigDict(frozen=True, extra="forbid")
_IN_CONFIG = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Amcache (AmcacheParser — UnassociatedFileEntries table)
# ---------------------------------------------------------------------------


class AmcacheInput(BaseModel):
    """Inputs for :func:`parse_amcache`. ``csv_out`` MUST be absolute."""

    model_config = _IN_CONFIG
    evidence_path: Path
    csv_out: Path

    @model_validator(mode="after")
    def _check_csv_out_absolute(self) -> AmcacheInput:
        if not self.csv_out.is_absolute():
            raise ValueError(f"AmcacheInput.csv_out must be absolute; got {self.csv_out!r}")
        return self


class AmcacheEntry(BaseModel):
    """One row from AmcacheParser's UnassociatedFileEntries CSV.

    ``SHA1`` is empty for non-PE entries — coerced to ``None``.
    ``Size`` is the column name in AmcacheParser output (NOT ``FileSize``)."""

    model_config = _ROW_CONFIG

    sha1: str | None = Field(default=None, alias="SHA1")
    full_path: str = Field(alias="FullPath")
    file_extension: str | None = Field(default=None, alias="FileExtension")
    size: int | None = Field(default=None, alias="Size")
    product_name: str | None = Field(default=None, alias="ProductName")
    product_version: str | None = Field(default=None, alias="ProductVersion")
    publisher: str | None = Field(default=None, alias="Publisher")
    bin_file_version: str | None = Field(default=None, alias="BinFileVersion")
    bin_product_version: str | None = Field(default=None, alias="BinProductVersion")
    file_key_last_write_timestamp: datetime = Field(alias="FileKeyLastWriteTimestamp")

    @model_validator(mode="before")
    @classmethod
    def _coerce_empty_sentinels(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        for k in (
            "SHA1",
            "FileExtension",
            "ProductName",
            "ProductVersion",
            "Publisher",
            "BinFileVersion",
            "BinProductVersion",
        ):
            if data.get(k) == "":
                data[k] = None
        if data.get("Size") == "":
            data["Size"] = None
        return data


class AmcacheOutput(BaseModel):
    """Parsed AmcacheParser UnassociatedFileEntries CSV."""

    model_config = _OUT_CONFIG
    entries: tuple[AmcacheEntry, ...]
    truncated: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def row_count(self) -> int:
        return len(self.entries)


AMCACHE_CAVEATS: tuple[str, ...] = (
    (
        "Amcache proves file PRESENCE / inventory by the Compatibility Telemetry "
        "service, never execution. Corroborate with Prefetch or Sysmon EID 1 for "
        "execution proof."
    ),
    (
        "Amcache stores SHA-1, not SHA-256 — translate via VirusTotal or recompute "
        "if the binary is still on disk for modern-IOC comparison"
    ),
    (
        "AmcacheParser emits multiple CSVs per run; this tool consumes only the "
        "UnassociatedFileEntries table — call parse_prefetch + parse_shimcache for "
        "execution corroboration"
    ),
)

AMCACHE_CORROBORATION: tuple[str, ...] = (
    "parse_prefetch — execution evidence via prefetch file timestamps",
    "parse_shimcache — AppCompat evaluation presence (different evidence source)",
    "vol_pslist — confirm if the process is still running",
)


# ---------------------------------------------------------------------------
# Shimcache (AppCompatCacheParser — AppCompatCache table)
# ---------------------------------------------------------------------------


class ShimcacheInput(BaseModel):
    """Inputs for :func:`parse_shimcache`. ``csv_out`` MUST be absolute."""

    model_config = _IN_CONFIG
    evidence_path: Path
    csv_out: Path

    @model_validator(mode="after")
    def _check_csv_out_absolute(self) -> ShimcacheInput:
        if not self.csv_out.is_absolute():
            raise ValueError(f"ShimcacheInput.csv_out must be absolute; got {self.csv_out!r}")
        return self


class ShimcacheEntry(BaseModel):
    """One row from AppCompatCacheParser CSV.

    ``Executed`` is a tri-state string: ``"Yes"``/``"No"`` on Win7;
    ``"NA"`` on Win8/10/11 (flag removed). Empty string → ``"NA"``."""

    model_config = _ROW_CONFIG

    control_set: int = Field(alias="ControlSet")
    cache_entry_position: int = Field(alias="CacheEntryPosition")
    path: str = Field(alias="Path")
    last_modified_time_utc: datetime | None = Field(default=None, alias="LastModifiedTimeUTC")
    executed: Literal["Yes", "No", "NA"] = Field(alias="Executed")

    @model_validator(mode="before")
    @classmethod
    def _coerce_empty_sentinels(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("LastModifiedTimeUTC") == "":
            data["LastModifiedTimeUTC"] = None
        if data.get("Executed") in ("", None):
            data["Executed"] = "NA"
        return data


class ShimcacheOutput(BaseModel):
    """Parsed AppCompatCacheParser CSV. Entries are sorted by
    ``(cache_entry_position, control_set)`` ascending — position 0 is
    the most-recently-evaluated entry per ControlSet."""

    model_config = _OUT_CONFIG
    entries: tuple[ShimcacheEntry, ...]
    truncated: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def row_count(self) -> int:
        return len(self.entries)

    @model_validator(mode="after")
    def _sort_by_position(self) -> ShimcacheOutput:
        sorted_entries = tuple(
            sorted(self.entries, key=lambda e: (e.cache_entry_position, e.control_set))
        )
        object.__setattr__(self, "entries", sorted_entries)
        return self


SHIMCACHE_CAVEATS: tuple[str, ...] = (
    (
        "ShimCache records files the AppCompat layer evaluated for shimming — it "
        "may include programs that were prompted for compatibility shimming but "
        "never actually ran. ShimCache proves PRESENCE / shim-evaluation, not "
        "execution."
    ),
    (
        "ShimCache LastModifiedUTC is the file's $SI Modified time at evaluation, "
        "NOT the time the binary ran"
    ),
    (
        "ShimCache flushes to the SYSTEM hive only on clean shutdown — a hive "
        "captured live may be stale"
    ),
)

SHIMCACHE_CORROBORATION: tuple[str, ...] = (
    "vol_shimcachemem — memory ShimCache via Volatility (captures unflushed entries)",
    "parse_amcache — cross-reference file PRESENCE from a separate evidence source",
    "parse_prefetch — execution evidence if prefetch files are present",
)


__all__ = [
    "AMCACHE_CAVEATS",
    "AMCACHE_CORROBORATION",
    "SHIMCACHE_CAVEATS",
    "SHIMCACHE_CORROBORATION",
    "AmcacheEntry",
    "AmcacheInput",
    "AmcacheOutput",
    "ShimcacheEntry",
    "ShimcacheInput",
    "ShimcacheOutput",
]
