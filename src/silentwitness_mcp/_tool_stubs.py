"""Architecture §4.2 tool-stub registry.

Every stub mount-guards via the injected ``guard_mount`` callback so
a misconfigured ``/evidence`` mount surfaces as the typed
``MOUNT_NOT_RO_NOEXEC_NOSUID`` rejection rather than a generic
``NotImplementedError``."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from silentwitness_mcp._errors import ServerConfigurationError
from silentwitness_mcp._lifecycle import AppContext
from silentwitness_mcp._tool_impls import register_real_tools

_GuardFn = Callable[[str, Context[ServerSession, AppContext]], None]


def register_finding_tool_stubs(mcp: FastMCP, guard_mount: _GuardFn) -> None:
    """Bind every architecture §4.2 tool as a mount-guarded stub.

    ``guard_mount`` is injected so this module stays decoupled from
    the server's mount-check internals. A ``None`` here would silently
    bind every stub to a NoneType-not-callable failure at FIRST tool
    invocation; reject it at config time instead — the typed
    ``MOUNT_NOT_RO_NOEXEC_NOSUID`` rejection is too load-bearing to
    let slip past a configuration footgun."""
    if guard_mount is None:
        raise ServerConfigurationError(
            "register_finding_tool_stubs requires a non-None guard_mount callable; got None"
        )

    # Wire the real implementations first; the stubs below cover only the names
    # not yet wired (see _tool_impls.WIRED_TOOLS), so every tool stays advertised
    # while the surface is wired incrementally.
    register_real_tools(mcp, guard_mount)

    @mcp.tool()
    def approve_finding(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Examiner-only HMAC-ledger approval. Stub."""
        guard_mount("approve_finding", ctx)
        raise NotImplementedError("approve_finding is registered but not yet implemented")

    @mcp.tool()
    def vol_pslist(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Volatility3 windows.pslist. Stub."""
        guard_mount("vol_pslist", ctx)
        raise NotImplementedError("vol_pslist is registered but not yet implemented")

    @mcp.tool()
    def vol_psscan(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Volatility3 windows.psscan. Stub."""
        guard_mount("vol_psscan", ctx)
        raise NotImplementedError("vol_psscan is registered but not yet implemented")

    @mcp.tool()
    def vol_pstree(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Volatility3 windows.pstree. Stub."""
        guard_mount("vol_pstree", ctx)
        raise NotImplementedError("vol_pstree is registered but not yet implemented")

    @mcp.tool()
    def vol_malfind(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Vol3 windows.malware.malfind. Stub."""
        guard_mount("vol_malfind", ctx)
        raise NotImplementedError("vol_malfind is registered but not yet implemented")

    @mcp.tool()
    def vol_netscan(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Vol3 windows.netscan. Stub."""
        guard_mount("vol_netscan", ctx)
        raise NotImplementedError("vol_netscan is registered but not yet implemented")

    @mcp.tool()
    def vol_cmdline(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Vol3 windows.cmdline. Stub."""
        guard_mount("vol_cmdline", ctx)
        raise NotImplementedError("vol_cmdline is registered but not yet implemented")

    @mcp.tool()
    def vol_dlllist(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Vol3 windows.dlllist. Stub."""
        guard_mount("vol_dlllist", ctx)
        raise NotImplementedError("vol_dlllist is registered but not yet implemented")

    @mcp.tool()
    def vol_handles(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Vol3 windows.handles. Stub."""
        guard_mount("vol_handles", ctx)
        raise NotImplementedError("vol_handles is registered but not yet implemented")

    @mcp.tool()
    def vol_lsadump(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Vol3 windows.registry.lsadump. Stub."""
        guard_mount("vol_lsadump", ctx)
        raise NotImplementedError("vol_lsadump is registered but not yet implemented")

    @mcp.tool()
    def chainsaw_hunt(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Chainsaw Sigma-rule hunt over an EVTX directory. Stub."""
        guard_mount("chainsaw_hunt", ctx)
        raise NotImplementedError("chainsaw_hunt is registered but not yet implemented")

    @mcp.tool()
    def hayabusa_csv_timeline(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Hayabusa Sigma-rule csv-timeline over an EVTX directory. Stub."""
        guard_mount("hayabusa_csv_timeline", ctx)
        raise NotImplementedError("hayabusa_csv_timeline is registered but not yet implemented")

    @mcp.tool()
    def suricata_run(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Suricata IDS rule replay against a pcap — EVE JSON event tally. Stub."""
        guard_mount("suricata_run", ctx)
        raise NotImplementedError("suricata_run is registered but not yet implemented")


__all__ = ["register_finding_tool_stubs"]
