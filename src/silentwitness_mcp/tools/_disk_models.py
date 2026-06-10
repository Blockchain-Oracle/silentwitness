"""Typed models for the disk tool family. Field names follow the
PslistEntry / NetscanEntry / HandleEntry / LsaSecretEntry convention
established by PR #148: snake_case Python attribute API + PascalCase
``alias=`` declarations matching the MFTECmd wire columns.

MFTECmd column reality (verified against ``context/domain/06`` §5.1
and the story-parse-mft BDD):
 - ``IsDeleted`` is a server-side @computed_field over ``not in_use``
   (NOT a wire column; never look for an ``IsDeleted`` header).
 - ``SiFnDelta`` is a server-side @computed_field aliasing
   ``Timestomped`` for backward-compat reading callers.
 - ``Timestomped`` and ``uSecZeros`` are wire boolean columns
   surfaced verbatim from MFTECmd.
 - The wider MFTECmd column set (``ReferenceCount``, ``IsAds``,
   ``Copied``, ``SiFlags``, ``NameType``, ``LoggedUtilStream``,
   ``ZoneIdContents``, ``ReparseTarget``) is declared as optional
   so ``extra="forbid"`` continues to catch true schema drift
   without rejecting every real MFTECmd row."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

_ROW_CONFIG = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)
_OUT_CONFIG = ConfigDict(frozen=True, extra="forbid")
_IN_CONFIG = ConfigDict(frozen=True, extra="forbid")


class MftInput(BaseModel):
    """Inputs for :func:`parse_mft`. Both paths are validated by the
    evidence registry and the mount gate before MFTECmd is spawned.

    ``csv_out`` MUST be absolute — a relative path would resolve
    against the dotnet subprocess cwd (typically the SilentWitness
    server cwd, not the case dir) and silently land the CSV in the
    wrong place."""

    model_config = _IN_CONFIG
    evidence_path: Path
    csv_out: Path

    @model_validator(mode="after")
    def _check_csv_out_absolute(self) -> MftInput:
        if not self.csv_out.is_absolute():
            raise ValueError(f"MftInput.csv_out must be absolute; got {self.csv_out!r}")
        return self


def _coerce_bool(value: Any) -> bool:
    """MFTECmd CSV emits booleans as ``"True"`` / ``"False"`` via
    .NET ``Boolean.ToString``. Empty string / ``None`` → ``False``
    matching MFTECmd's "column was unset on this row" behaviour.
    Any other input raises ``ValueError`` — a column-drift bug
    (e.g. MFTECmd switching to ``"1"``/``"0"`` digit format)
    surfaces as ``OUTPUT_PARSE_FAILED`` rather than silently
    inverting every boolean field."""
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return False
    if isinstance(value, str):
        s = value.strip().lower()
        if s == "true":
            return True
        if s == "false":
            return False
    raise ValueError(f"unrecognised MFTECmd boolean: {value!r}")


class MFTEntry(BaseModel):
    """One row from MFTECmd CSV — typed per ``context/domain/06`` §5.1.

    The Python attribute API is snake_case; PascalCase wire-schema
    names live only as ``alias=`` declarations. Consumers that access
    ``entry.entry_number`` are decoupled from MFTECmd renderer naming.

    The wide column set (``reference_count``, ``is_ads``, ``copied``,
    ``si_flags``, ``name_type``, ``logged_util_stream``,
    ``zone_id_contents``, ``reparse_target``) is declared as optional
    ``str | None`` so a real MFTECmd CSV row validates without
    relaxing ``extra="forbid"`` — true schema drift (a brand-new
    column landing) still fail-closes to OUTPUT_PARSE_FAILED.

    No cross-field ``timestomped`` vs ``Created0x10/0x30`` consistency
    invariant by design — MFTECmd's ``Timestomped`` computation may
    consider more than just Created divergence (LastModified,
    LastAccess too), and forcing a tighter rule would over-reject
    legitimate rows whose ``Timestomped`` flag MFTECmd set for a
    reason we don't model here. The caveat layer flags the
    interpretation; the type permits the row."""

    model_config = _ROW_CONFIG

    entry_number: int = Field(alias="EntryNumber")
    sequence_number: int = Field(alias="SequenceNumber")
    parent_entry_number: int | None = Field(default=None, alias="ParentEntryNumber")
    parent_sequence_number: int | None = Field(default=None, alias="ParentSequenceNumber")
    parent_path: str = Field(default="", alias="ParentPath")
    file_name: str = Field(default="", alias="FileName")
    extension: str | None = Field(default=None, alias="Extension")
    file_size: int = Field(default=0, alias="FileSize")
    is_directory: bool = Field(default=False, alias="IsDirectory")
    in_use: bool = Field(default=True, alias="InUse")
    has_ads: bool = Field(default=False, alias="HasAds")
    # SI ($STANDARD_INFORMATION) timestamps
    created_0x10: datetime | None = Field(default=None, alias="Created0x10")
    last_modified_0x10: datetime | None = Field(default=None, alias="LastModified0x10")
    last_record_change_0x10: datetime | None = Field(default=None, alias="LastRecordChange0x10")
    last_access_0x10: datetime | None = Field(default=None, alias="LastAccess0x10")
    # FN ($FILE_NAME) timestamps
    created_0x30: datetime | None = Field(default=None, alias="Created0x30")
    last_modified_0x30: datetime | None = Field(default=None, alias="LastModified0x30")
    last_record_change_0x30: datetime | None = Field(default=None, alias="LastRecordChange0x30")
    last_access_0x30: datetime | None = Field(default=None, alias="LastAccess0x30")
    # MFTECmd-emitted booleans
    timestomped: bool = Field(default=False, alias="Timestomped")
    u_sec_zeros: bool = Field(default=False, alias="uSecZeros")
    # Wider MFTECmd CSV column set — declared optional so real
    # MFTECmd output validates under extra="forbid" without
    # relaxing the schema-drift guard.
    reference_count: str | None = Field(default=None, alias="ReferenceCount")
    reparse_target: str | None = Field(default=None, alias="ReparseTarget")
    is_ads: bool = Field(default=False, alias="IsAds")
    copied: bool = Field(default=False, alias="Copied")
    si_flags: str | None = Field(default=None, alias="SiFlags")
    name_type: str | None = Field(default=None, alias="NameType")
    logged_util_stream: str | None = Field(default=None, alias="LoggedUtilStream")
    zone_id_contents: str | None = Field(default=None, alias="ZoneIdContents")

    @model_validator(mode="before")
    @classmethod
    def _coerce_mftecmd_empty_sentinels(cls, data: Any) -> Any:
        """Coerce MFTECmd's empty-string sentinels for the $MFT system
        entry and other special rows ($LogFile etc.) into typed
        defaults so Pydantic's int / bool validators don't choke.
        Runs before field validation."""
        if not isinstance(data, dict):
            return data
        if data.get("FileSize") == "":
            data["FileSize"] = 0
        for k in ("ParentEntryNumber", "ParentSequenceNumber"):
            if data.get(k) == "":
                data[k] = None
        # Tolerate empty-string bools so the parser's row-by-row
        # path (see disk._parse_mft_rows) surfaces unknown truth
        # values as per-row OUTPUT_PARSE_FAILED rather than a global
        # abort on the first $MFT-system entry.
        for k in ("InUse", "IsDirectory", "HasAds", "Timestomped", "uSecZeros", "IsAds", "Copied"):
            v = data.get(k)
            if isinstance(v, str):
                data[k] = _coerce_bool(v)
        return data

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_deleted(self) -> bool:
        """Server-side-derived: ``not in_use``. NOT a wire column.
        Surfaced as a Pydantic ``@computed_field`` (not a stored
        field) so the derivation cannot be desync'd by a caller
        supplying both ``InUse`` and ``IsDeleted`` to
        ``model_validate``."""
        return not self.in_use

    @computed_field  # type: ignore[prop-decorator]
    @property
    def si_fn_delta(self) -> bool:
        """Server-side-derived alias for ``timestomped`` — retained
        for backward-compat readers that grep for SI/FN-divergence
        signals by name. Same ``@computed_field`` rationale as
        :attr:`is_deleted`."""
        return self.timestomped


class MftOutput(BaseModel):
    """Parsed MFT CSV. ``truncated`` is ``True`` when MFTECmd died
    mid-write OR per-row validation failures forced rows to be
    dropped — partial-success is preferred over hard reject so the
    agent can still cite the rows that did parse.

    ``(entry_number, sequence_number)`` is the NTFS canonical record
    identifier; duplicates in the output indicate either CSV
    concatenation bugs, glob-picked-stale-residue, or schema drift.
    The :meth:`_check_record_identity_unique` model_validator fails
    closed."""

    model_config = _OUT_CONFIG
    entries: tuple[MFTEntry, ...]
    truncated: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def row_count(self) -> int:
        """Derived from ``len(entries)`` — cannot drift."""
        return len(self.entries)

    @model_validator(mode="after")
    def _check_record_identity_unique(self) -> MftOutput:
        seen: set[tuple[int, int]] = set()
        for e in self.entries:
            key = (e.entry_number, e.sequence_number)
            if key in seen:
                raise ValueError(
                    f"duplicate MFT record identity {key} — "
                    "indicates CSV concatenation, stale-glob, or schema drift"
                )
            seen.add(key)
        return self


# Caveat block surfaced verbatim in :attr:`ToolResponse.caveats`
# (architecture §4.3). Order matters: the timestomp action-shaping
# caveat FIRST so an agent skimming caveats[0] gets the analytical
# directive. Story spec at story-parse-mft.md line 45 dictates the
# exact wording of caveat[0].
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
        "is_deleted is server-side-derived from `not in_use`; si_fn_delta "
        "is the wrapper @computed_field alias of MFTECmd's Timestomped "
        "column — neither is a wire column"
    ),
    (
        "u_sec_zeros (zero microseconds across timestamps) often co-occurs "
        "with timestomping; corroborate with parse_amcache and "
        "parse_prefetch for execution evidence"
    ),
)


__all__ = ["MFT_CAVEATS", "MFTEntry", "MftInput", "MftOutput"]
