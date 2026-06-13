"""Real MCP wrappers for the EVTX log-analysis tools (Chainsaw, Hayabusa).

Same adapter shape as :mod:`silentwitness_mcp._tool_impls`. ``evtx_dir`` is a
registered directory of Windows event logs; output paths are derived under
``case_dir`` and the rule/mapping defaults come from the install.sh locations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from silentwitness_mcp._lifecycle import AppContext
from silentwitness_mcp._tool_impls import _case_deps, _GuardFn, _tool_out_dir
from silentwitness_mcp.tools._log_chainsaw import chainsaw_hunt as _impl_chainsaw_hunt
from silentwitness_mcp.tools._log_hayabusa import (
    hayabusa_csv_timeline as _impl_hayabusa_csv_timeline,
)

LOG_TOOLS: frozenset[str] = frozenset({"chainsaw_hunt", "hayabusa_csv_timeline"})


def register_log_tools(mcp: FastMCP, guard_mount: _GuardFn) -> None:
    """Register the Chainsaw + Hayabusa wrappers in :data:`LOG_TOOLS`."""

    @mcp.tool()
    async def chainsaw_hunt(
        ctx: Context[ServerSession, AppContext],
        evtx_dir: str,
    ) -> dict[str, Any]:
        """Chainsaw Sigma-rule hunt over a directory of EVTX logs. Uses the
        install.sh-provisioned SigmaHQ rules + event-log mapping by default."""
        guard_mount("chainsaw_hunt", ctx)
        case_dir, registry, audit, model = _case_deps(ctx)
        json_out = _tool_out_dir(case_dir, "chainsaw", evtx_dir) / "chainsaw.json"
        resp = await _impl_chainsaw_hunt(
            Path(evtx_dir),
            json_out,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=audit,
            model_used=model,
        )
        return resp.model_dump(mode="json")

    @mcp.tool()
    async def hayabusa_csv_timeline(
        ctx: Context[ServerSession, AppContext],
        evtx_dir: str,
    ) -> dict[str, Any]:
        """Hayabusa Sigma-rule CSV timeline over a directory of EVTX logs
        (super-verbose profile with MITRE ATT&CK columns)."""
        guard_mount("hayabusa_csv_timeline", ctx)
        case_dir, registry, audit, model = _case_deps(ctx)
        csv_out = _tool_out_dir(case_dir, "hayabusa", evtx_dir) / "hayabusa.csv"
        resp = await _impl_hayabusa_csv_timeline(
            Path(evtx_dir),
            csv_out,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=audit,
            model_used=model,
        )
        return resp.model_dump(mode="json")


__all__ = ["LOG_TOOLS", "register_log_tools"]
