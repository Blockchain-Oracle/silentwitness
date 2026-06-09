"""FastMCP server construction — the typed-tool surface (architecture §4.1, §4.2).

Public entrypoint :func:`create_server` returns a configured
:class:`mcp.server.fastmcp.FastMCP` instance ready to run on either
stdio or Streamable HTTP transports. Tool bodies are stub placeholders
in this story (story-fastmcp-server-bootstrap); the actual finding-
recording logic lands in stories 8-12 of Epic 4 (one tool per story).

Loopback-only HTTP binding (``127.0.0.1`` — never ``0.0.0.0``) is the
DNS-rebinding defense from ``context/technical/07`` §A3.2. Enforcement
sits in :func:`_validate_http_config`, called before FastMCP construction
so a misconfigured invocation fails synchronously rather than after a
socket has bound. The ``host`` we pass into ``FastMCP(host=...)`` is then
the validated value — FastMCP itself does not re-validate, so the gate is
:func:`_validate_http_config`, not the SDK.

Bearer-token auth on HTTP uses
:class:`mcp.server.auth.provider.TokenVerifier` against
``$SILENTWITNESS_GATEWAY_TOKEN``. If the env var is unset, HTTP mode
refuses to start (fail-closed). stdio mode has no auth because the
subprocess identity boundary suffices (architecture §7.3).

FastMCP couples ``token_verifier`` with :class:`AuthSettings` — passing
a verifier without auth settings is rejected at construction time. The
minimal :class:`AuthSettings` we pass DOES cause FastMCP to expose an
RFC-9728 Protected-Resource-Metadata endpoint at
``/.well-known/oauth-protected-resource``; the only consumer of that
endpoint on a loopback-bound server is a local MCP client doing OAuth
discovery, which our static-bearer model ignores. We are not bypassing
OAuth discovery; we are coexisting with the SDK's exposure of it.

"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Sequence
from enum import StrEnum
from typing import Final, Literal

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from pydantic import AnyHttpUrl

from silentwitness_mcp import __version__
from silentwitness_mcp._lifecycle import AppContext, lifespan
from silentwitness_mcp._tool_stubs import register_finding_tool_stubs

# Tools touching /evidence refuse on bad mount (architecture §4.11).
# Lifespan still registers them so clients can introspect; each call
# returns MOUNT_NOT_RO_NOEXEC_NOSUID until the mount is fixed.
EVIDENCE_BOUND_TOOLS: Final[frozenset[str]] = frozenset(
    {
        "record_observation",
        "register_evidence",
        "verify_evidence_hash",
        "vol_malfind",
        "vol_netscan",
        "vol_pslist",
        "vol_psscan",
        "vol_pstree",
    }
)


MountFailureReason = Literal[
    "MOUNT_NOT_RO_NOEXEC_NOSUID",
    "LIFESPAN_CONTEXT_MISSING",
]


class MountValidationError(RuntimeError):
    """Raised by an evidence-bound tool when the lifespan-time mount
    check failed (or the lifespan never bound the AppContext). Surfaces
    a typed ``reason`` to the agent per architecture §4.11 so the
    failure is a structured rejection, not a generic ``AttributeError``
    wrapped as an unhelpful ``ToolError`` string.

    ``advisories`` is frozen to a ``tuple`` at construction so a
    handler cannot mutate the exception state post-raise; ``reason`` is
    keyword-only so a positional caller cannot accidentally swap the
    two arguments and silently bind a ``str`` reason into the
    ``Sequence[str]`` advisories slot.
    """

    def __init__(
        self,
        advisories: Sequence[str],
        *,
        reason: MountFailureReason = "MOUNT_NOT_RO_NOEXEC_NOSUID",
    ) -> None:
        super().__init__(reason)
        self.reason: MountFailureReason = reason
        self.advisories: tuple[str, ...] = tuple(advisories)

    def __str__(self) -> str:
        return f"{self.reason}: advisories={list(self.advisories)}"


logger = logging.getLogger(__name__)

SERVER_NAME: Final = "silentwitness"
DEFAULT_HTTP_HOST: Final = "127.0.0.1"
DEFAULT_HTTP_PORT: Final = 4508
LOOPBACK_ALLOWED: Final[frozenset[str]] = frozenset({"127.0.0.1", "::1", "localhost"})
GATEWAY_TOKEN_ENV: Final = "SILENTWITNESS_GATEWAY_TOKEN"  # noqa: S105  env var NAME, not a secret


class Transport(StrEnum):
    """CLI-selectable transport. Default stdio for the SIFT 2026 Claude
    Code subprocess pattern."""

    STDIO = "stdio"
    HTTP = "http"


class ServerConfigurationError(RuntimeError):
    """Raised when transport/host/port/auth configuration is rejected at
    startup. Fail-closed: HTTP without a gateway token is an immediate
    refusal, not a downgraded warning."""


# ---------------------------------------------------------------------------
# Bearer-token auth
# ---------------------------------------------------------------------------


class _StaticTokenVerifier(TokenVerifier):
    """Constant-time equality against ``$SILENTWITNESS_GATEWAY_TOKEN``.

    The token is read at construction time, NOT at every verify call —
    rotating the gateway token requires a server restart. That's the
    intended threat model: the env var is provisioned by SIFT setup
    scripts and rotation is a deploy event, not a hot operation.
    """

    def __init__(self, expected_token: str) -> None:
        if not expected_token:
            raise ServerConfigurationError(
                f"{GATEWAY_TOKEN_ENV} is empty; HTTP transport refuses to start"
            )
        self._expected = expected_token

    async def verify_token(self, token: str) -> AccessToken | None:
        # Defensive: a misbehaving client (or a future SDK change) could
        # hand us None, bytes, or an oversized string. All three must
        # reject cleanly without raising — a TypeError would crash the
        # whole MCP connection.
        if not isinstance(token, str) or not token or len(token) > 4096:
            return None
        # Constant-time comparison so token length cannot be inferred
        # from response timing.
        import hmac

        if not hmac.compare_digest(token, self._expected):
            return None
        return AccessToken(
            token=token,
            client_id=SERVER_NAME,
            scopes=["silentwitness.tools"],
            expires_at=None,
        )


# ---------------------------------------------------------------------------
# Configuration validation
# ---------------------------------------------------------------------------


def _validate_http_config(host: str, port: int) -> None:
    """Reject any non-loopback host (DNS-rebinding defense) or out-of-
    range port. Called BEFORE FastMCP construction so the failure
    surfaces synchronously."""
    if host not in LOOPBACK_ALLOWED:
        raise ServerConfigurationError(
            f"HTTP host must be one of {sorted(LOOPBACK_ALLOWED)} "
            f"(DNS-rebinding defense); got {host!r}"
        )
    if not (1 <= port <= 65535):
        raise ServerConfigurationError(f"HTTP port out of range: {port} (must be 1..65535)")


def _resolve_token_verifier(transport: Transport) -> TokenVerifier | None:
    """Return a :class:`TokenVerifier` for HTTP, ``None`` for stdio.

    Stdio has no auth — the subprocess identity boundary IS the auth
    (architecture §7.3). HTTP without ``$SILENTWITNESS_GATEWAY_TOKEN``
    is a configuration error.
    """
    if transport is Transport.STDIO:
        return None
    token = os.environ.get(GATEWAY_TOKEN_ENV, "").strip()
    if not token:
        raise ServerConfigurationError(
            f"HTTP transport requires {GATEWAY_TOKEN_ENV} env var to be set; "
            f"refusing to start without bearer-token gate"
        )
    return _StaticTokenVerifier(token)


# ---------------------------------------------------------------------------
# Tool stub registration
# ---------------------------------------------------------------------------


def _guard_mount(tool_name: str, ctx: Context[ServerSession, AppContext]) -> None:
    """Architecture §4.11 BDD: evidence-bound tools refuse to operate
    when the mount check failed. Non-evidence-bound tools pass through.

    Called as the FIRST action of every stub so future implementations
    can rely on this guard being in place. The lifespan-context-missing
    branch is reachable when an evidence-bound tool is invoked outside
    the FastMCP lifespan scope (broken test harness, lifespan startup
    race) — surfacing it as a structured rejection beats letting a
    raw ``AttributeError`` escape and confuse the examiner.
    """
    if tool_name not in EVIDENCE_BOUND_TOOLS:
        return
    app_ctx = ctx.request_context.lifespan_context
    # ``isinstance`` over ``is None``: defends against a MagicMock-
    # shaped substitute that a broken test harness might leak in. A
    # truthy MagicMock would silently pass ``is None`` and then read
    # ``mount.ok`` as another mock with default truthy value, bypassing
    # the guard.
    if not isinstance(app_ctx, AppContext):
        raise MountValidationError(
            advisories=[
                "server lifespan did not yield an AppContext; "
                "evidence-bound tool cannot verify mount state"
            ],
            reason="LIFESPAN_CONTEXT_MISSING",
        )
    if not app_ctx.mount.ok:
        raise MountValidationError(app_ctx.mount.advisories)


# _register_finding_tool_stubs lives in :mod:`_tool_stubs` (extracted
# to keep this file under the 400-LOC CI cap; imported below).


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------


def create_server(
    transport: Transport = Transport.STDIO,
    *,
    host: str = DEFAULT_HTTP_HOST,
    port: int = DEFAULT_HTTP_PORT,
) -> FastMCP:
    """Build the FastMCP server with lifespan + auth + tool stubs.

    For stdio, ``host`` and ``port`` are ignored. For http, both are
    validated synchronously — a malformed host (anything outside
    :data:`LOOPBACK_ALLOWED`) or out-of-range port raises
    :class:`ServerConfigurationError`.
    """
    verifier = _resolve_token_verifier(transport)
    if transport is Transport.HTTP:
        _validate_http_config(host, port)

    effective_host = host if transport is Transport.HTTP else DEFAULT_HTTP_HOST
    effective_port = port if transport is Transport.HTTP else DEFAULT_HTTP_PORT
    # FastMCP couples token_verifier with AuthSettings; even our static-
    # bearer model has to declare an issuer URL so the SDK's auth-config
    # invariant is satisfied. The verifier itself bypasses OAuth 2.1
    # discovery — verify_token is the single point of truth.
    auth_settings: AuthSettings | None = None
    if verifier is not None:
        base_url = AnyHttpUrl(f"http://{effective_host}:{effective_port}")
        auth_settings = AuthSettings(
            issuer_url=base_url,
            resource_server_url=base_url,
            required_scopes=["silentwitness.tools"],
        )

    mcp = FastMCP(
        SERVER_NAME,
        instructions=(
            f"SilentWitness v{__version__} - hypothesis-first DFIR investigator. "
            "Every finding must cite verifiable tool-output spans."
        ),
        lifespan=lifespan,
        token_verifier=verifier,
        auth=auth_settings,
        host=effective_host,
        port=effective_port,
    )
    register_finding_tool_stubs(mcp, _guard_mount)
    return mcp


def run_server(
    transport: Transport = Transport.STDIO,
    *,
    host: str = DEFAULT_HTTP_HOST,
    port: int = DEFAULT_HTTP_PORT,
) -> None:
    """Build then run. Banner to stderr only — stdio framing requires
    a clean stdout. See the SIFT 2026 Claude Code v2.0.61 subprocess
    pattern in architecture §7.3."""
    print(
        f"silentwitness v{__version__} starting (transport={transport.value})",
        file=sys.stderr,
    )
    server = create_server(transport, host=host, port=port)
    # ``match`` with explicit ``case _`` forces a future Transport
    # variant (e.g. WEBSOCKET) to land here as a structured rejection
    # rather than silently take the HTTP branch and get handed
    # ``transport="streamable-http"`` for the wrong protocol.
    match transport:
        case Transport.STDIO:
            server.run(transport="stdio")
            return
        case Transport.HTTP:
            # Defense-in-depth: re-validate the bound host immediately
            # before handing off to mcp.run(). FastMCP itself accepts
            # any host string; a future refactor that moved or removed
            # _validate_http_config (or constructed FastMCP directly
            # outside create_server) would silently bypass the
            # DNS-rebinding gate. Re-checking here keeps the gate
            # load-bearing even if the upstream check drifts.
            if server.settings.host not in LOOPBACK_ALLOWED:
                raise ServerConfigurationError(
                    f"defense-in-depth: server.settings.host="
                    f"{server.settings.host!r} is not in {sorted(LOOPBACK_ALLOWED)}"
                )
            server.run(transport="streamable-http")
        case _:
            raise ServerConfigurationError(f"unhandled transport: {transport!r}")
