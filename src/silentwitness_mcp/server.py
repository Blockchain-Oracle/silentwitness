"""FastMCP server construction — the typed-tool surface (architecture §4.1, §4.2).

Public entrypoint :func:`create_server` returns a configured
:class:`mcp.server.fastmcp.FastMCP` instance ready to run on either
stdio or Streamable HTTP transports. Tool bodies are stub placeholders
in this story (story-fastmcp-server-bootstrap); the actual finding-
recording logic lands in stories 8-12 of Epic 4 (one tool per story).

Loopback-only HTTP binding (``127.0.0.1`` — never ``0.0.0.0``) is the
DNS-rebinding defense from ``context/technical/07`` §A3.2 and is
enforced by both the FastMCP ``settings.host`` we set AND by
:func:`_validate_http_config` which refuses any other host value.

Bearer-token auth on HTTP uses
:class:`mcp.server.auth.provider.TokenVerifier` against
``$SILENTWITNESS_GATEWAY_TOKEN``. If the env var is unset, HTTP mode
refuses to start (fail-closed). stdio mode has no auth because the
subprocess identity boundary suffices (architecture §7.3).
"""

from __future__ import annotations

import logging
import os
import sys
from enum import StrEnum
from typing import Final

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from silentwitness_mcp import __version__
from silentwitness_mcp._lifecycle import lifespan

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


def _register_finding_tool_stubs(mcp: FastMCP) -> None:
    """Register the seven snake_case finding/evidence tools from
    architecture §4.2 as stubs.

    Each body raises :class:`NotImplementedError` so MCP clients see a
    structured error rather than a silent success. The actual bodies
    land in stories 8-12 of this epic.
    """

    @mcp.tool()
    def record_observation() -> dict[str, str]:
        """Record a verifiable observation (architecture §4.5/§4.7).

        Stub — implemented in story-record-observation-tool.
        """
        raise NotImplementedError(
            "record_observation is registered but not yet implemented; "
            "tracked by story-record-observation-tool"
        )

    @mcp.tool()
    def record_interpretation() -> dict[str, str]:
        """Record an interpretation that links observations to a
        hypothesis. Stub — implemented in story-record-interpretation-tool."""
        raise NotImplementedError(
            "record_interpretation is registered but not yet implemented; "
            "tracked by story-record-interpretation-tool"
        )

    @mcp.tool()
    def record_pivot() -> dict[str, str]:
        """Pivot the active hypothesis. Stub — story-record-pivot-tool."""
        raise NotImplementedError(
            "record_pivot is registered but not yet implemented; tracked by story-record-pivot-tool"
        )

    @mcp.tool()
    def record_narrative() -> dict[str, str]:
        """Append a narrative section to the case report. Stub —
        story-record-narrative-tool."""
        raise NotImplementedError(
            "record_narrative is registered but not yet implemented; "
            "tracked by story-record-narrative-tool"
        )

    @mcp.tool()
    def approve_finding() -> dict[str, str]:
        """Examiner-only HMAC-ledger approval. Stub —
        story-approve-finding-tool."""
        raise NotImplementedError(
            "approve_finding is registered but not yet implemented; "
            "tracked by story-approve-finding-tool"
        )

    @mcp.tool()
    def register_evidence() -> dict[str, str]:
        """Hash + manifest registration (architecture §4.10). Stub —
        story-evidence-register-tool."""
        raise NotImplementedError(
            "register_evidence is registered but not yet implemented; "
            "tracked by story-evidence-register-tool"
        )

    @mcp.tool()
    def verify_evidence_hash() -> dict[str, str]:
        """Re-hash on case resume to catch bit-rot. Stub —
        story-evidence-verify-tool."""
        raise NotImplementedError(
            "verify_evidence_hash is registered but not yet implemented; "
            "tracked by story-evidence-verify-tool"
        )


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
    _register_finding_tool_stubs(mcp)
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
    if transport is Transport.STDIO:
        server.run(transport="stdio")
    else:
        server.run(transport="streamable-http")
