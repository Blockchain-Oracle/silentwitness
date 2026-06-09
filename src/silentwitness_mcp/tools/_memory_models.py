"""Pydantic row + payload models for the Vol3 memory family.

Every model uses ``extra="forbid"`` so Vol3 schema drift surfaces as
:attr:`VolFailureReason.OUTPUT_PARSE_FAILED` — a forensic audit
trail cannot quietly elide unknown columns."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


_WILDCARD: Final = "*"
"""Vol3 emits the literal ``"*"`` for UDP foreign endpoints — the ONLY
recognised sentinel. Any other non-IP-shaped value on a foreign-side
field (``"-"``, ``""``, ``"null"``, ``"?"``) is treated as schema
drift and rejected by the IP-shape / TCB-state field validators."""

_IP_SHAPE: Final = re.compile(r"[.:]")
"""Rough IP-shape: must contain a dot (IPv4) or colon (IPv6). Tight
enough to reject sentinel strings, loose enough to forward-compat
verbatim IPv4-mapped IPv6 like ``::ffff:192.168.1.50`` per spec."""

_TCB_STATE: Final = re.compile(r"^[A-Z][A-Z0-9_]+$")
"""TCB state shape: uppercase alphanumeric + underscore, ≥2 chars.
Matches ESTABLISHED / LISTENING / TIME_WAIT / SYN_RECV / future
states; rejects sentinel strings + lowercase fallbacks."""


class NetscanEntry(BaseModel):
    """Vol3 ``windows.netscan`` row — one TCP/UDP endpoint.

    Two design choices look unusual on first read; both are deliberate
    forensic-accuracy decisions:

    1. **Addresses are ``str`` not ``IPv4Address``/``IPv6Address``.**
       The downstream entity gate matches typed observations against
       verbatim cited spans in tool output. Normalising
       ``::ffff:192.168.1.50`` to ``192.168.1.50`` here would cause
       every observation citing the IPv6-mapped form to fail the gate.
       IP-shape validation (``_IP_SHAPE``) only rejects sentinel
       strings — it does NOT canonicalise.

    2. **``state`` is ``str | None`` not ``Literal[...]``.** Vol3
       forwards kernel TCB state verbatim. Future Windows builds may
       add states (e.g. ``SYN_RECV2``); we'd rather forward them than
       fail closed. The action-shaping caveat ("filter to ESTABLISHED
       for live C2 evidence") lives at the caveat layer, not the type
       layer. ``_TCB_STATE`` validates shape only.

    Cross-field invariants:

    - TCP entries MUST carry ``foreign_addr``, ``foreign_port``, and
      ``state`` (live or historical connection state).
    - UDP entries have ``state=None`` (connectionless).

    Wildcard handling: Vol3 emits ``"*"`` for UDP foreign endpoints.
    The ``mode="before"`` validator rewrites it to ``None`` so the
    typed nullable invariants hold. ``"*"`` is the ONLY recognised
    sentinel — other strings fail the shape validators."""

    model_config = _ROW_CONFIG

    offset: int = Field(alias="Offset")
    proto: Literal["TCPv4", "TCPv6", "UDPv4", "UDPv6"] = Field(alias="Proto")
    local_addr: str = Field(alias="LocalAddr")
    local_port: int = Field(alias="LocalPort")
    foreign_addr: str | None = Field(default=None, alias="ForeignAddr")
    foreign_port: int | None = Field(default=None, alias="ForeignPort")
    state: str | None = Field(default=None, alias="State")
    pid: int | None = Field(default=None, alias="PID")
    owner: str | None = Field(default=None, alias="Owner")
    created: datetime | None = Field(default=None, alias="Created")

    @model_validator(mode="before")
    @classmethod
    def _normalise_udp_wildcards(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        overrides: dict[str, Any] = {}
        for key in ("ForeignAddr", "ForeignPort", "State"):
            if data.get(key) == _WILDCARD:
                overrides[key] = None
        return {**data, **overrides} if overrides else data

    @field_validator("local_addr", "foreign_addr")
    @classmethod
    def _check_ip_shape(cls, value: str | None) -> str | None:
        if value is not None and not _IP_SHAPE.search(value):
            raise ValueError(f"address field has non-IP shape (no '.' or ':'): {value!r}")
        return value

    @field_validator("state")
    @classmethod
    def _check_state_shape(cls, value: str | None) -> str | None:
        if value is not None and not _TCB_STATE.match(value):
            raise ValueError(f"state has non-TCB shape: {value!r}")
        return value

    @model_validator(mode="after")
    def _check_cross_field_invariants(self) -> NetscanEntry:
        is_tcp = self.proto in ("TCPv4", "TCPv6")
        if is_tcp:
            missing = [
                name
                for name, val in (
                    ("foreign_addr", self.foreign_addr),
                    ("foreign_port", self.foreign_port),
                    ("state", self.state),
                )
                if val is None
            ]
            if missing:
                raise ValueError(
                    f"TCP {self.proto} entry missing required field(s): {', '.join(missing)}"
                )
        elif self.state is not None:
            raise ValueError(f"UDP {self.proto} entry must have state=None, got {self.state!r}")
        return self


class NetscanOutput(BaseModel):
    model_config = _OUT_CONFIG
    entries: tuple[NetscanEntry, ...]


__all__ = [
    "MalfindHit",
    "MalfindOutput",
    "NetscanEntry",
    "NetscanOutput",
    "PslistEntry",
    "PslistOutput",
    "PsscanEntry",
    "PsscanOutput",
    "PstreeEntry",
    "PstreeOutput",
]
