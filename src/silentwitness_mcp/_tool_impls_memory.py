"""Real MCP wrappers for the Volatility 3 memory-analysis tool family.

Same adapter shape as :mod:`silentwitness_mcp._tool_impls` (mount-guard, pull
per-case deps from the lifespan AppContext, call the unit-tested impl, return a
JSON dict envelope). Split into its own module to keep each file under the
400-LOC CI cap. ``evidence_path`` is the registered memory image; the impls
derive their own blob output paths under ``case_dir``.

Unlike the file-decomposing tools (zeek/chainsaw/hayabusa), vol_* return parsed
rows in the envelope, so the agent cites them directly from this tool's audit_id
— there is no read_tool_output step, hence no read-to-cite advisory here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from silentwitness_mcp._lifecycle import AppContext
from silentwitness_mcp._tool_impls import _case_deps, _GuardFn
from silentwitness_mcp.tools.memory import (
    vol_cmdline as _impl_vol_cmdline,
    vol_dlllist as _impl_vol_dlllist,
    vol_handles as _impl_vol_handles,
    vol_malfind as _impl_vol_malfind,
    vol_netscan as _impl_vol_netscan,
    vol_pslist as _impl_vol_pslist,
    vol_psscan as _impl_vol_psscan,
    vol_pstree as _impl_vol_pstree,
)
from silentwitness_mcp.tools.memory_extras import vol_lsadump as _impl_vol_lsadump

MEMORY_TOOLS: frozenset[str] = frozenset(
    {
        "vol_pslist",
        "vol_psscan",
        "vol_pstree",
        "vol_malfind",
        "vol_netscan",
        "vol_cmdline",
        "vol_dlllist",
        "vol_handles",
        "vol_lsadump",
    }
)


def register_memory_tools(mcp: FastMCP, guard_mount: _GuardFn) -> None:
    """Register the Volatility 3 wrappers in :data:`MEMORY_TOOLS`."""

    @mcp.tool()
    async def vol_pslist(
        ctx: Context[ServerSession, AppContext], evidence_path: str
    ) -> dict[str, Any]:
        """Volatility3 windows.pslist — active processes from a memory image."""
        guard_mount("vol_pslist", ctx)
        case_dir, registry, audit, model = _case_deps(ctx)
        resp = await _impl_vol_pslist(
            Path(evidence_path),
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=audit,
            model_used=model,
        )
        return resp.model_dump(mode="json")

    @mcp.tool()
    async def vol_psscan(
        ctx: Context[ServerSession, AppContext], evidence_path: str
    ) -> dict[str, Any]:
        """Volatility3 windows.psscan — pool-scan for processes (incl. hidden/exited)."""
        guard_mount("vol_psscan", ctx)
        case_dir, registry, audit, model = _case_deps(ctx)
        resp = await _impl_vol_psscan(
            Path(evidence_path),
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=audit,
            model_used=model,
        )
        return resp.model_dump(mode="json")

    @mcp.tool()
    async def vol_pstree(
        ctx: Context[ServerSession, AppContext], evidence_path: str
    ) -> dict[str, Any]:
        """Volatility3 windows.pstree — parent/child process tree."""
        guard_mount("vol_pstree", ctx)
        case_dir, registry, audit, model = _case_deps(ctx)
        resp = await _impl_vol_pstree(
            Path(evidence_path),
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=audit,
            model_used=model,
        )
        return resp.model_dump(mode="json")

    @mcp.tool()
    async def vol_netscan(
        ctx: Context[ServerSession, AppContext], evidence_path: str
    ) -> dict[str, Any]:
        """Volatility3 windows.netscan — network connections/sockets in memory."""
        guard_mount("vol_netscan", ctx)
        case_dir, registry, audit, model = _case_deps(ctx)
        resp = await _impl_vol_netscan(
            Path(evidence_path),
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=audit,
            model_used=model,
        )
        return resp.model_dump(mode="json")

    @mcp.tool()
    async def vol_lsadump(
        ctx: Context[ServerSession, AppContext], evidence_path: str
    ) -> dict[str, Any]:
        """Volatility3 windows.registry.lsadump — LSA secrets from memory."""
        guard_mount("vol_lsadump", ctx)
        case_dir, registry, audit, model = _case_deps(ctx)
        resp = await _impl_vol_lsadump(
            Path(evidence_path),
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=audit,
            model_used=model,
        )
        return resp.model_dump(mode="json")

    @mcp.tool()
    async def vol_malfind(
        ctx: Context[ServerSession, AppContext],
        evidence_path: str,
        pid: int | None = None,
    ) -> dict[str, Any]:
        """Volatility3 windows.malware.malfind — injected/RWX memory regions.
        Optionally scope to a single ``pid``."""
        guard_mount("vol_malfind", ctx)
        case_dir, registry, audit, model = _case_deps(ctx)
        resp = await _impl_vol_malfind(
            Path(evidence_path),
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=audit,
            model_used=model,
            pid=pid,
        )
        return resp.model_dump(mode="json")

    @mcp.tool()
    async def vol_cmdline(
        ctx: Context[ServerSession, AppContext],
        evidence_path: str,
        pid: int | None = None,
    ) -> dict[str, Any]:
        """Volatility3 windows.cmdline — process command lines. Optional ``pid``."""
        guard_mount("vol_cmdline", ctx)
        case_dir, registry, audit, model = _case_deps(ctx)
        resp = await _impl_vol_cmdline(
            Path(evidence_path),
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=audit,
            model_used=model,
            pid=pid,
        )
        return resp.model_dump(mode="json")

    @mcp.tool()
    async def vol_dlllist(
        ctx: Context[ServerSession, AppContext],
        evidence_path: str,
        pid: int | None = None,
    ) -> dict[str, Any]:
        """Volatility3 windows.dlllist — loaded DLLs per process. Optional ``pid``."""
        guard_mount("vol_dlllist", ctx)
        case_dir, registry, audit, model = _case_deps(ctx)
        resp = await _impl_vol_dlllist(
            Path(evidence_path),
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=audit,
            model_used=model,
            pid=pid,
        )
        return resp.model_dump(mode="json")

    @mcp.tool()
    async def vol_handles(
        ctx: Context[ServerSession, AppContext],
        evidence_path: str,
        pid: int | None = None,
        object_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Volatility3 windows.handles — open handle table. Optional ``pid`` and
        ``object_types`` filter (e.g. Key, File, Mutant)."""
        guard_mount("vol_handles", ctx)
        case_dir, registry, audit, model = _case_deps(ctx)
        resp = await _impl_vol_handles(
            Path(evidence_path),
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=audit,
            model_used=model,
            pid=pid,
            object_types=object_types,
        )
        return resp.model_dump(mode="json")


__all__ = ["MEMORY_TOOLS", "register_memory_tools"]
