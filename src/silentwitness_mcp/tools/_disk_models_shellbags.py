"""Typed models for parse_shellbags (SBECmd wrapper).

Column reality (verified against context/domain/06 §5.8 + encyclopedia §23):
 - MRUPosition is an int when present; Win10+ rows often leave it blank.
 - FirstInteracted / LastInteracted are derived from BagMRU tree traversal.
   LastInteracted is frequently blank on Win10+ rows — keep both fields
   distinct so the agent sees missing data honestly (do not fall back to
   LastWriteTime to fill either).
 - HasExplored is "True"/"False" in the CSV — coerced to bool on parse.
 - MFTEntry / MFTSequenceNumber are integers when SBECmd resolves the MFT
   record; blank otherwise.
 - AbsolutePath is verbatim SBECmd tree reconstruction — backslash
   separators are preserved as-is (even on POSIX hosts).
 - IconReference carries the literal path stored in the BagMRU ShellItem
   (e.g. "C:\\Tools\\Ethereal\\ethereal.ico") — forensically significant."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

_ROW_CONFIG = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)
_OUT_CONFIG = ConfigDict(frozen=True, extra="forbid")

_OPTIONAL_INT_FIELDS = ("MRUPosition", "MFTEntry", "MFTSequenceNumber")
_OPTIONAL_STR_FIELDS = ("FirstInteracted", "LastInteracted", "IconReference")


class ShellbagEntry(BaseModel):
    """One row from SBECmd CSV output."""

    model_config = _ROW_CONFIG

    bag_path: str = Field(alias="BagPath")
    slot: int = Field(alias="Slot")
    node_slot: int = Field(alias="NodeSlot")
    mru_position: int | None = Field(default=None, alias="MRUPosition")
    absolute_path: str = Field(alias="AbsolutePath")
    shell_type: str = Field(alias="ShellType")
    value: str = Field(alias="Value")
    child_bags: int = Field(alias="ChildBags")
    first_interacted: datetime | None = Field(default=None, alias="FirstInteracted")
    last_interacted: datetime | None = Field(default=None, alias="LastInteracted")
    last_write_time: datetime = Field(alias="LastWriteTime")
    mft_entry: int | None = Field(default=None, alias="MFTEntry")
    mft_sequence_number: int | None = Field(default=None, alias="MFTSequenceNumber")
    icon_reference: str | None = Field(default=None, alias="IconReference")
    has_explored: bool = Field(default=False, alias="HasExplored")
    hive: str = Field(alias="Hive")
    registry_path: str = Field(alias="RegistryPath")

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # Coerce empty/whitespace-only optional fields → None.
        for k in _OPTIONAL_INT_FIELDS + _OPTIONAL_STR_FIELDS:
            if not (data.get(k) or "").strip():
                data[k] = None
        # Coerce HasExplored string → bool.
        he = (data.get("HasExplored") or "False").strip()
        data["HasExplored"] = he in ("True", "true", "1", "Yes", "yes")
        return data


class ShellbagsOutput(BaseModel):
    """Parsed SBECmd CSV. Entries preserve SBECmd output order."""

    model_config = _OUT_CONFIG
    entries: tuple[ShellbagEntry, ...]
    truncated: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def row_count(self) -> int:
        return len(self.entries)


SHELLBAGS_CAVEATS: tuple[str, ...] = (
    (
        "ShellBags persist folder navigation including deleted, external, and network "
        "locations — a path in ShellBags does not require the folder to exist now"
    ),
    (
        "ShellBag entries are created by Explorer rendering — cmd.exe / PowerShell / "
        "Get-ChildItem activity does NOT produce ShellBags"
    ),
    (
        "ShellBag LastInteracted reflects when the user last opened the folder in Explorer; "
        "absence of LastInteracted on Win10+ rows is common and not an error"
    ),
    (
        "Roaming profiles can sync ShellBags between hosts — a ShellBag does not prove "
        "the browse happened on THIS machine"
    ),
)

SHELLBAGS_CORROBORATION: tuple[str, ...] = (
    "parse_mft — find the same path in the MFT for creation/access timestamps",
    "parse_amcache — confirm executable presence in folders referenced by ShellBags",
    "regripper_run plugin=usbstor — cross-reference external-drive serial from ShellBag Value",
    "regripper_run plugin=mountdev — confirm volume serial for removable media",
    "regripper_run plugin=mp2 — correlate MountedDevices with drive letters in AbsolutePath",
)


__all__ = [
    "SHELLBAGS_CAVEATS",
    "SHELLBAGS_CORROBORATION",
    "ShellbagEntry",
    "ShellbagsOutput",
]
