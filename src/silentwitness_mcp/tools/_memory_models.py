"""Pydantic row + payload models for the Vol3 memory family.

Split from :mod:`memory` to keep the wrapper-body file under the
400-LOC CI cap as more vol_* plugins land. Every model uses
``extra="forbid"`` so Vol3 schema drift surfaces as
:attr:`VolFailureReason.OUTPUT_PARSE_FAILED` — a forensic audit
trail cannot quietly elide unknown columns."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

_ROW_CONFIG = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)
_OUT_CONFIG = ConfigDict(frozen=True, extra="forbid")


class PslistEntry(BaseModel):
    """Vol3 ``windows.pslist`` row."""

    model_config = _ROW_CONFIG

    pid: int = Field(alias="PID")
    ppid: int = Field(alias="PPID")
    image_file_name: str = Field(alias="ImageFileName")
    offset_v: int = Field(alias="Offset(V)")
    threads: int = Field(alias="Threads")
    handles: int | None = Field(default=None, alias="Handles")
    session_id: int | None = Field(default=None, alias="SessionId")
    wow64: bool = Field(alias="Wow64")
    create_time: datetime | None = Field(default=None, alias="CreateTime")
    exit_time: datetime | None = Field(default=None, alias="ExitTime")
    file_output: str | None = Field(default=None, alias="File output")


class PslistOutput(BaseModel):
    model_config = _OUT_CONFIG
    entries: tuple[PslistEntry, ...]


class PstreeEntry(PslistEntry):
    """Flattened pstree row. audit/cmd/path are pstree-only extras;
    depth is NOT a column (recomputable downstream from pid pairs)."""

    audit: str | None = Field(default=None, alias="Audit")
    cmd: str | None = Field(default=None, alias="Cmd")
    path: str | None = Field(default=None, alias="Path")


class PstreeOutput(BaseModel):
    model_config = _OUT_CONFIG
    entries: tuple[PstreeEntry, ...]


class PsscanEntry(PslistEntry):
    """psscan returns the same columns as pslist (context/domain/03
    §7.3). Intentionally empty — preserves the nominal type so a
    PsscanOutput cannot carry PslistEntry rows. Do NOT collapse."""


class PsscanOutput(BaseModel):
    model_config = _OUT_CONFIG
    entries: tuple[PsscanEntry, ...]


class MalfindHit(BaseModel):
    """Vol3 ``windows.malware.malfind`` row — one suspect VAD with
    its hexdump preview. Field aliases map Vol3's renderer keys to
    snake_case Python (context/domain/03 §7.6)."""

    model_config = _ROW_CONFIG

    pid: int = Field(alias="PID")
    process: str = Field(alias="Process")
    start_vpn: int = Field(alias="Start VPN")
    end_vpn: int = Field(alias="End VPN")
    vad_tag: str = Field(alias="Tag")
    protection: str = Field(alias="Protection")
    commit_charge: int = Field(alias="CommitCharge")
    private_memory: bool = Field(alias="PrivateMemory")
    file_output: str | None = Field(default=None, alias="File output")
    hexdump_first_128: str | None = Field(default=None, alias="Hexdump")
    disasm_preview: str | None = Field(default=None, alias="Disasm")


class MalfindOutput(BaseModel):
    model_config = _OUT_CONFIG
    entries: tuple[MalfindHit, ...]


__all__ = [
    "MalfindHit",
    "MalfindOutput",
    "PslistEntry",
    "PslistOutput",
    "PsscanEntry",
    "PsscanOutput",
    "PstreeEntry",
    "PstreeOutput",
]
