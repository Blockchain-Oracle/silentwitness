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
    def suricata_run(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Suricata IDS rule replay against a pcap — EVE JSON event tally. Stub."""
        guard_mount("suricata_run", ctx)
        raise NotImplementedError("suricata_run is registered but not yet implemented")


__all__ = ["register_finding_tool_stubs"]
