"""Pydantic row + payload models for the Vol3 memory family.

Every model uses ``extra="forbid"`` so Vol3 schema drift surfaces as
:attr:`VolFailureReason.OUTPUT_PARSE_FAILED` — a forensic audit
trail cannot quietly elide unknown columns."""

from __future__ import annotations

import ipaddress
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
recognised sentinel. Any other non-IP value on a foreign-side field
(``"-"``, ``""``, ``"null"``, ``"null:"``, trailing whitespace) is
treated as schema drift and rejected by :meth:`NetscanEntry._check_ip`
(which parses via :func:`ipaddress.ip_address` and discards the result
so verbatim preservation still holds)."""

_UPPERCASE_TOKEN: Final = re.compile(r"\A[A-Z][A-Z0-9_]+\Z")
"""Uppercase token shape, end-of-string anchored. Matches ESTABLISHED
/ LISTENING / TIME_WAIT / SYN_RECV / future kernel TCB-state names;
rejects sentinels (``"-"``, ``""``, ``"null"``), lowercase, AND the
trailing-newline silent-acceptance case (``"$"`` matches before
``\\n``; ``\\A``/``\\Z`` are end-of-string-only)."""


class NetscanEntry(BaseModel):
    """Vol3 ``windows.netscan`` row — one TCP/UDP endpoint.

    Two design choices look unusual on first read; both are deliberate
    forensic-accuracy decisions:

    1. **Addresses are ``str`` not ``IPv4Address``/``IPv6Address``.**
       The downstream entity gate matches typed observations against
       verbatim cited spans in tool output. Normalising
       ``::ffff:192.168.1.50`` to ``192.168.1.50`` here would cause
       every observation citing the IPv6-mapped form to fail the gate.
       IP validation parses via :func:`ipaddress.ip_address` then
       discards the parsed object — verbatim preservation upheld,
       any sentinel rejected.

    2. **``state`` is ``str | None`` not ``Literal[...]``.** Vol3
       forwards kernel TCB state verbatim. Future Windows builds may
       add states (e.g. ``SYN_RECV2``); we'd rather forward them than
       fail closed. The action-shaping caveat ("filter to ESTABLISHED
       for live C2 evidence") lives at the caveat layer, not the type
       layer. ``_UPPERCASE_TOKEN`` validates token shape only.

    Bypass surface: :meth:`model_construct` (Pydantic's no-validation
    fast path) skips ALL of these defences. Do NOT reach for it as a
    performance optimisation — every forensic invariant above lives
    on the validator chain.

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
    def _check_ip(cls, value: str | None) -> str | None:
        if value is None:
            return value
        # Parse via stdlib then DISCARD the parsed object — the entity gate
        # downstream matches verbatim cited spans, so canonicalisation here
        # (e.g. "::ffff:192.168.1.50" -> "192.168.1.50") would break it.
        # try/except is the closed defence a regex shape can't be: rejects
        # "null:", "..", "X:", trailing newline, NUL byte, leading whitespace —
        # any string ipaddress.ip_address() cannot parse. NB: "::" IS the
        # valid IPv6 unspecified address and IS accepted; the netscan caveat
        # list flags LISTENING on a non-loopback bind separately.
        try:
            ipaddress.ip_address(value)
        except ValueError as exc:
            raise ValueError(f"address not a parseable IPv4/IPv6: {value!r}") from exc
        return value

    @field_validator("state")
    @classmethod
    def _check_state_shape(cls, value: str | None) -> str | None:
        if value is not None and not _UPPERCASE_TOKEN.match(value):
            raise ValueError(f"state has non-uppercase-token shape: {value!r}")
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


_PEB_PLACEHOLDER_PREFIXES: Final[tuple[str, ...]] = (
    # Anchored on Vol3's hex-address suffix so a real command line that
    # legitimately starts with "Required memory at" (some Windows
    # bootloader / firmware utilities) is preserved verbatim.
    "required memory at 0x",
    "swap layer is not available",
)
# Mechanical enforcement of the lowercase invariant: the match runs
# against ``.lower()``-folded input, so a future addition like
# ``"Paged Out"`` (mixed case) would silently fail to match and let
# a placeholder reach the entity gate as a citation. Raise at import
# (assert would strip under -O).
if any(p != p.lower() for p in _PEB_PLACEHOLDER_PREFIXES):
    raise ValueError("_PEB_PLACEHOLDER_PREFIXES entries must be pre-lowercased")
"""Closed catalogue of Vol3 "couldn't read this memory region"
sentinel string prefixes, pre-lowercased at module load. Match is
case-insensitive + whitespace+NUL-stripped so renderer drift on
capitalisation or leading indent doesn't silently let a placeholder
reach the entity gate as a citable evidence span.

Additions must be source-traced to a Vol3 commit — the
``args: str | None`` invariant on :class:`CmdlineEntry` is what lets
the caveat layer distinguish "no args" from "couldn't read args"
honestly; widening this set silently would break that distinction."""

_NULL_SENTINELS: Final[frozenset[str]] = frozenset({"", "null", "none"})
"""Case-insensitive set of sentinel strings Vol3 may emit in lieu of
a real ``args`` value."""

_OUTER_WHITESPACE_NUL: Final = re.compile(r"^[\s\x00]+|[\s\x00]+$")
"""Strip outer whitespace + NUL bytes in one pass. ``str.strip()``
alone leaves embedded NULs; chaining ``.strip().strip("\\x00")``
mishandles interleaved cases like ``"\\x00 \\x00"`` (outer NULs
removed, inner space remains, sentinel check then fails)."""


class CmdlineEntry(BaseModel):
    """Vol3 ``windows.cmdline`` row — one process's launch command line.

    ``args`` is ``str | None``:
    - ``str`` when Vol3 successfully read the PEB ProcessParameters
    - ``None`` for processes with empty args (System / Registry /
      smss.exe and some service-host processes have this legitimately)
      AND for paged-out PEBs (Vol3 placeholder collapsed to None)

    The caveat layer flags this ambiguity ("missing Args for paged-out
    PEBs is a smear artifact, not evidence of tampering"); the type
    layer just preserves the distinction between "real string" and
    "no string available".

    Intentionally no ``process``↔``args`` cross-field invariant —
    a "System with non-None args" row IS the threat model vol_cmdline
    exists to detect (PEB tamper via RtlInitUnicodeString). Encoding
    that pairing as a type invariant would make tampered rows
    un-representable, defeating the tool's purpose."""

    model_config = _ROW_CONFIG

    pid: int = Field(alias="PID")
    process: str = Field(alias="Process")
    args: str | None = Field(default=None, alias="Args")

    @field_validator("args", mode="before")
    @classmethod
    def _normalise_args(cls, value: object) -> object:
        # Non-str passes through; pydantic's outer str-typing then
        # loud-fails on int / list / bool with ValidationError, which
        # _run_wrapper surfaces as OUTPUT_PARSE_FAILED.
        if not isinstance(value, str):
            return value
        # Single-pass strip of outer whitespace AND NUL bytes — chained
        # .strip().strip("\x00") misses "\x00 \x00" (outer NULs go,
        # embedded space remains, the empty-string sentinel never fires).
        folded = _OUTER_WHITESPACE_NUL.sub("", value).lower()
        if folded in _NULL_SENTINELS or any(
            folded.startswith(p) for p in _PEB_PLACEHOLDER_PREFIXES
        ):
            return None
        return value  # verbatim preservation for the entity gate


class CmdlineOutput(BaseModel):
    model_config = _OUT_CONFIG
    entries: tuple[CmdlineEntry, ...]


__all__ = [
    "CmdlineEntry",
    "CmdlineOutput",
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
