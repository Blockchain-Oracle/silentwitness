"""Architecture §4.2 tool-stub registry (extracted from
:mod:`server` to keep ``server.py`` under the 400-LOC CI cap).

Each ``@mcp.tool()`` decorator surfaces a typed FastMCP tool. Bodies
are placeholders (the real wiring lives in :mod:`tools.*` and
:mod:`findings.*` and is bound in a later story's case-context
plumbing); every stub mount-guards via :func:`_guard_mount` so an
invocation against a misconfigured ``/evidence`` mount fails with the
typed ``MOUNT_NOT_RO_NOEXEC_NOSUID`` rejection rather than a generic
``NotImplementedError``."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from silentwitness_mcp._lifecycle import AppContext

_GuardFn = Callable[[str, Context[ServerSession, AppContext]], None]


def register_finding_tool_stubs(mcp: FastMCP, guard_mount: _GuardFn) -> None:
    """Bind every architecture §4.2 tool as a mount-guarded stub.

    ``guard_mount`` is injected so this module stays decoupled from
    the server's mount-check internals — the only side effect from
    here is decorator-driven FastMCP registration."""

    @mcp.tool()
    def record_observation(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Record a verifiable observation (§4.5/§4.7). Stub."""
        guard_mount("record_observation", ctx)
        raise NotImplementedError("record_observation is registered but not yet implemented")

    @mcp.tool()
    def record_interpretation(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Link observations to a hypothesis. Stub."""
        guard_mount("record_interpretation", ctx)
        raise NotImplementedError("record_interpretation is registered but not yet implemented")

    @mcp.tool()
    def record_pivot(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Pivot the active hypothesis. Stub."""
        guard_mount("record_pivot", ctx)
        raise NotImplementedError("record_pivot is registered but not yet implemented")

    @mcp.tool()
    def record_narrative(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Append a narrative section to the case report. Stub."""
        guard_mount("record_narrative", ctx)
        raise NotImplementedError("record_narrative is registered but not yet implemented")

    @mcp.tool()
    def approve_finding(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Examiner-only HMAC-ledger approval. Stub."""
        guard_mount("approve_finding", ctx)
        raise NotImplementedError("approve_finding is registered but not yet implemented")

    @mcp.tool()
    def register_evidence(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Hash + manifest registration (§4.10). Stub."""
        guard_mount("register_evidence", ctx)
        raise NotImplementedError("register_evidence is registered but not yet implemented")

    @mcp.tool()
    def verify_evidence_hash(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Re-hash on case resume to catch bit-rot. Stub."""
        guard_mount("verify_evidence_hash", ctx)
        raise NotImplementedError("verify_evidence_hash is registered but not yet implemented")

    @mcp.tool()
    def vol_pslist(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Volatility3 windows.pslist. Stub pending case-context binding."""
        guard_mount("vol_pslist", ctx)
        raise NotImplementedError("vol_pslist body pending case-context binding")

    @mcp.tool()
    def vol_psscan(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Volatility3 windows.psscan. Stub pending case-context binding."""
        guard_mount("vol_psscan", ctx)
        raise NotImplementedError("vol_psscan body pending case-context binding")

    @mcp.tool()
    def vol_pstree(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Volatility3 windows.pstree. Stub pending case-context binding."""
        guard_mount("vol_pstree", ctx)
        raise NotImplementedError("vol_pstree body pending case-context binding")

    @mcp.tool()
    def vol_malfind(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Vol3 windows.malware.malfind. Stub pending case-context binding."""
        guard_mount("vol_malfind", ctx)
        raise NotImplementedError("vol_malfind body pending case-context binding")

    @mcp.tool()
    def vol_netscan(ctx: Context[ServerSession, AppContext]) -> dict[str, str]:
        """Vol3 windows.netscan. Stub pending case-context binding."""
        guard_mount("vol_netscan", ctx)
        raise NotImplementedError("vol_netscan body pending case-context binding")


__all__ = ["register_finding_tool_stubs"]
