"""Volatility 3 memory-family tool bodies (architecture §4.6, PRD FR #5).

Plugin names use the class-suffixed form (``windows.pslist.PsList``).
The ``-r json`` renderer emits a flat array for most plugins and a
nested ``__children`` tree for pstree — :mod:`_vol_pipeline` wires
the orchestrator; bespoke parsers live below."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from silentwitness_common.types import ToolResponse
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._memory_models import (
    CmdlineEntry,
    CmdlineOutput,
    MalfindHit,
    MalfindOutput,
    NetscanEntry,
    NetscanOutput,
    PslistEntry,
    PslistOutput,
    PsscanEntry,
    PsscanOutput,
    PstreeEntry,
    PstreeOutput,
)
from silentwitness_mcp.tools._vol_common import DEFAULT_TIMEOUT_S
from silentwitness_mcp.tools._vol_pipeline import _parse_flat, _run_wrapper

# Plugin paths (class-suffixed form Vol3 ≥2.27 expects).
_PSLIST_PLUGIN: Final = "windows.pslist.PsList"
_PSTREE_PLUGIN: Final = "windows.pstree.PsTree"
_PSSCAN_PLUGIN: Final = "windows.psscan.PsScan"
# Vol3 ≥2.29 removes windows.malfind — windows.malware path is future-safe.
_MALFIND_PLUGIN: Final = "windows.malware.malfind.Malfind"
_NETSCAN_PLUGIN: Final = "windows.netscan.NetScan"
# Capital-L: class-suffixed form Vol3 ≥2.27 expects.
_CMDLINE_PLUGIN: Final = "windows.cmdline.CmdLine"

# PID 0 (System Idle) and negative PIDs have no _EPROCESS / PEB —
# Vol3 returns empty results OR errors with confusing stderr. Reject
# at the wrapper boundary so an LLM-driven typo gets a clean message.
_MIN_VALID_PID: Final = 1


def _validate_pid_filter(tool_name: str, pid: int | None) -> None:
    if pid is not None and pid < _MIN_VALID_PID:
        raise ValueError(
            f"{tool_name}: pid must be >= {_MIN_VALID_PID} or None; got {pid} "
            f"(PID 0 = System Idle has no PEB / VAD)"
        )


_MALFIND_HEXDUMP_CAP: Final = 256  # = 128 bytes of hex
_HEX_CHARS: Final = frozenset("0123456789abcdefABCDEF")


async def vol_pslist(
    evidence_path: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ToolResponse[PslistOutput]:
    return await _run_wrapper(
        tool_name="vol_pslist",
        plugin_name=_PSLIST_PLUGIN,
        caveat_key="pslist",
        output_cls=PslistOutput,
        parse_rows=lambda raw: _parse_flat(raw, PslistEntry, PslistOutput),
        evidence_path=evidence_path,
        case_dir=case_dir,
        evidence_registry=evidence_registry,
        audit_logger=audit_logger,
        model_used=model_used,
        timeout_s=timeout_s,
    )


async def vol_psscan(
    evidence_path: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ToolResponse[PsscanOutput]:
    return await _run_wrapper(
        tool_name="vol_psscan",
        plugin_name=_PSSCAN_PLUGIN,
        caveat_key="psscan",
        output_cls=PsscanOutput,
        parse_rows=lambda raw: _parse_flat(raw, PsscanEntry, PsscanOutput),
        evidence_path=evidence_path,
        case_dir=case_dir,
        evidence_registry=evidence_registry,
        audit_logger=audit_logger,
        model_used=model_used,
        timeout_s=timeout_s,
    )


async def vol_pstree(
    evidence_path: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ToolResponse[PstreeOutput]:
    """``__children`` tree → flat list, breadth-first. Depth omitted —
    downstream consumers recompute from parent/child pid pairs."""
    return await _run_wrapper(
        tool_name="vol_pstree",
        plugin_name=_PSTREE_PLUGIN,
        caveat_key="pstree",
        output_cls=PstreeOutput,
        parse_rows=lambda raw: PstreeOutput(entries=tuple(_flatten_pstree(raw))),
        evidence_path=evidence_path,
        case_dir=case_dir,
        evidence_registry=evidence_registry,
        audit_logger=audit_logger,
        model_used=model_used,
        timeout_s=timeout_s,
    )


async def vol_malfind(
    evidence_path: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    pid: int | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ToolResponse[MalfindOutput]:
    """RWX-private-no-mapped-file VAD detection. ``pid=None`` scans
    all processes; an int filters at the Vol3 plugin layer."""
    _validate_pid_filter("vol_malfind", pid)
    return await _run_wrapper(
        tool_name="vol_malfind",
        plugin_name=_MALFIND_PLUGIN,
        caveat_key="malfind",
        output_cls=MalfindOutput,
        parse_rows=_parse_malfind,
        evidence_path=evidence_path,
        case_dir=case_dir,
        evidence_registry=evidence_registry,
        audit_logger=audit_logger,
        model_used=model_used,
        timeout_s=timeout_s,
        extra_argv=["--pid", str(pid)] if pid is not None else None,
    )


async def vol_cmdline(
    evidence_path: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    pid: int | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ToolResponse[CmdlineOutput]:
    """Per-process command-line recovery from each ``_EPROCESS.Peb.
    ProcessParameters.CommandLine``. ``pid=None`` scans all processes;
    an int filters at the Vol3 plugin layer."""
    _validate_pid_filter("vol_cmdline", pid)
    return await _run_wrapper(
        tool_name="vol_cmdline",
        plugin_name=_CMDLINE_PLUGIN,
        caveat_key="cmdline",
        output_cls=CmdlineOutput,
        parse_rows=lambda raw: _parse_flat(raw, CmdlineEntry, CmdlineOutput),
        evidence_path=evidence_path,
        case_dir=case_dir,
        evidence_registry=evidence_registry,
        audit_logger=audit_logger,
        model_used=model_used,
        timeout_s=timeout_s,
        extra_argv=["--pid", str(pid)] if pid is not None else None,
    )


async def vol_netscan(
    evidence_path: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ToolResponse[NetscanOutput]:
    """Pool-tag scan of TCP/UDP endpoints (active + recently closed).
    UDP wildcard ``*`` foreign endpoints surface as nulls — see the
    bespoke parser for the normalization rule."""
    return await _run_wrapper(
        tool_name="vol_netscan",
        plugin_name=_NETSCAN_PLUGIN,
        caveat_key="netscan",
        output_cls=NetscanOutput,
        parse_rows=_parse_netscan,
        evidence_path=evidence_path,
        case_dir=case_dir,
        evidence_registry=evidence_registry,
        audit_logger=audit_logger,
        model_used=model_used,
        timeout_s=timeout_s,
    )


def _parse_malfind(raw: bytes) -> MalfindOutput:
    """Trim Hexdump to 256 hex chars (first 128 bytes). Vol3 emits
    offset-prefixed + ASCII-suffixed lines; filtering to [0-9a-fA-F]
    keeps the field name honest (silent-failure LOW from PR #140)."""
    rows = json.loads(raw.decode("utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"malfind JSON must be a list, got {type(rows).__name__}")
    hits: list[MalfindHit] = []
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("Hexdump"), str):
            hex_only = "".join(c for c in row["Hexdump"] if c in _HEX_CHARS)
            row = {**row, "Hexdump": hex_only[:_MALFIND_HEXDUMP_CAP]}
        hits.append(MalfindHit.model_validate(row))
    return MalfindOutput(entries=tuple(hits))


def _parse_netscan(raw: bytes) -> NetscanOutput:
    """Thin JSON-list adapter. Wildcard normalisation + IP-shape +
    TCB-state + cross-field invariants all live on ``NetscanEntry``."""
    rows = json.loads(raw.decode("utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"netscan JSON must be a list, got {type(rows).__name__}")
    return NetscanOutput(entries=tuple(NetscanEntry.model_validate(row) for row in rows))


def _flatten_pstree(raw: bytes) -> list[PstreeEntry]:
    """BFS flatten of Vol3 pstree's ``__children`` tree. A non-list/
    non-null ``__children`` raises — silent subtree drop would let
    schema drift hide a whole branch from the audit trail."""
    rows = json.loads(raw.decode("utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"pstree root must be a list, got {type(rows).__name__}")
    flat: list[PstreeEntry] = []
    stack: list[Any] = list(rows)
    while stack:
        node = stack.pop(0)
        if not isinstance(node, dict):
            raise ValueError(f"pstree node must be a dict, got {type(node).__name__}")
        children = node.pop("__children", None)
        flat.append(PstreeEntry.model_validate(node))
        if children is None:
            continue
        if not isinstance(children, list):
            raise ValueError(f"__children must be a list or null, got {type(children).__name__}")
        stack.extend(children)
    return flat


def hidden_or_terminated_candidates(pslist_pids: set[int], psscan_pids: set[int]) -> set[int]:
    """Rootkit-detection diff: processes in psscan but NOT in pslist.
    exit_time=None ⇒ DKOM-hidden candidate; populated ⇒ terminated
    teardown. Interpretation lives downstream."""
    return psscan_pids - pslist_pids


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
    "hidden_or_terminated_candidates",
    "vol_cmdline",
    "vol_malfind",
    "vol_netscan",
    "vol_pslist",
    "vol_psscan",
    "vol_pstree",
]
