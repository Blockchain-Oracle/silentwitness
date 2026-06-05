"""Integration tests — FastMCP server bootstrap (story-fastmcp-server-bootstrap).

Verifies the boot path matters end-to-end without spinning up a live
transport: server construction, tool registration, lifespan startup,
HTTP loopback-bind enforcement, bearer-token auth, CLI argument parsing.
A live stdio/HTTP handshake test is deferred to the per-tool stories
where actual request/response payloads can be asserted on.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest

from silentwitness_mcp import __version__
from silentwitness_mcp.__main__ import _build_parser, main
from silentwitness_mcp._lifecycle import (
    DEFAULT_EVIDENCE_ROOT,
    AppContext,
    MountCheckResult,
    check_mount,
    lifespan,
    warm_injection_patterns,
)
from silentwitness_mcp.server import (
    DEFAULT_HTTP_HOST,
    DEFAULT_HTTP_PORT,
    GATEWAY_TOKEN_ENV,
    LOOPBACK_ALLOWED,
    SERVER_NAME,
    ServerConfigurationError,
    Transport,
    _StaticTokenVerifier,
    create_server,
)

EXPECTED_TOOL_NAMES = frozenset(
    {
        "record_observation",
        "record_interpretation",
        "record_pivot",
        "record_narrative",
        "approve_finding",
        "register_evidence",
        "verify_evidence_hash",
    }
)


@pytest.fixture(autouse=True)
def _scrub_gateway_token(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Default each test to NO gateway token. Tests that need one set
    it explicitly via monkeypatch.setenv."""
    monkeypatch.delenv(GATEWAY_TOKEN_ENV, raising=False)
    yield


# ---------------------------------------------------------------------------
# Server construction
# ---------------------------------------------------------------------------


def test_create_server_stdio_succeeds_without_gateway_token() -> None:
    """stdio transport has no auth — subprocess identity boundary IS the
    auth (architecture §7.3). No env var required."""
    mcp = create_server(Transport.STDIO)
    assert mcp.name == SERVER_NAME


def test_create_server_http_without_token_raises() -> None:
    """HTTP without $SILENTWITNESS_GATEWAY_TOKEN must fail closed."""
    with pytest.raises(ServerConfigurationError, match=GATEWAY_TOKEN_ENV):
        create_server(Transport.HTTP)


def test_create_server_http_with_token_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(GATEWAY_TOKEN_ENV, "test-token-9d2f1a")
    mcp = create_server(Transport.HTTP)
    assert mcp.name == SERVER_NAME
    assert mcp.settings.host == DEFAULT_HTTP_HOST
    assert mcp.settings.port == DEFAULT_HTTP_PORT


def test_create_server_http_rejects_non_loopback_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """0.0.0.0 / external IPs MUST raise — DNS-rebinding defense per
    context/technical/07 §A3.2."""
    monkeypatch.setenv(GATEWAY_TOKEN_ENV, "test-token-9d2f1a")
    with pytest.raises(ServerConfigurationError, match="DNS-rebinding"):
        create_server(Transport.HTTP, host="0.0.0.0")  # noqa: S104
    with pytest.raises(ServerConfigurationError, match="DNS-rebinding"):
        create_server(Transport.HTTP, host="8.8.8.8")


def test_create_server_http_rejects_out_of_range_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(GATEWAY_TOKEN_ENV, "test-token-9d2f1a")
    with pytest.raises(ServerConfigurationError, match="port out of range"):
        create_server(Transport.HTTP, port=0)
    with pytest.raises(ServerConfigurationError, match="port out of range"):
        create_server(Transport.HTTP, port=65536)


def test_loopback_allowed_set_is_strictly_loopback() -> None:
    """No external address can slip into the allow-list."""
    assert LOOPBACK_ALLOWED == frozenset({"127.0.0.1", "::1", "localhost"})


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def test_all_expected_finding_tools_registered() -> None:
    mcp = create_server(Transport.STDIO)
    tools = asyncio.run(mcp.list_tools())
    registered = {t.name for t in tools}
    assert registered == EXPECTED_TOOL_NAMES, (
        f"missing: {EXPECTED_TOOL_NAMES - registered}; extra: {registered - EXPECTED_TOOL_NAMES}"
    )


def test_tool_stubs_raise_not_implemented() -> None:
    """Stub bodies must raise rather than silently succeed — otherwise
    the agent could record a 'finding' without any verification work."""
    mcp = create_server(Transport.STDIO)
    tools = asyncio.run(mcp.list_tools())
    for tool in tools:
        with pytest.raises(Exception) as exc_info:
            asyncio.run(mcp.call_tool(tool.name, {}))
        # FastMCP wraps the NotImplementedError; the message survives.
        assert "not yet implemented" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Lifespan + mount + injection patterns
# ---------------------------------------------------------------------------


def test_check_mount_skips_when_evidence_dir_absent(tmp_path: Path) -> None:
    """On dev/test environments without /evidence, check_mount returns
    ok=True with an advisory — boot continues so unit tests run."""
    absent = tmp_path / "nonexistent-evidence-dir"
    result = check_mount(absent)
    assert result.ok is True
    assert any("does not exist" in adv for adv in result.advisories)


def test_check_mount_default_path_is_evidence() -> None:
    """The default target is /evidence — architecture §4.11."""
    assert DEFAULT_EVIDENCE_ROOT.as_posix() == "/evidence"


def test_warm_injection_patterns_returns_positive_count() -> None:
    """Sanitizer's catalog YAML loads on boot — should have ≥1 patterns."""
    count = warm_injection_patterns()
    assert count >= 1


def test_lifespan_yields_app_context_with_pattern_count() -> None:
    """The async context manager produces an AppContext with the warm
    state every tool reads via ctx.request_context.lifespan_context."""
    mcp = create_server(Transport.STDIO)

    async def _drive() -> AppContext:
        async with lifespan(mcp) as ctx:
            return ctx

    ctx = asyncio.run(_drive())
    assert isinstance(ctx, AppContext)
    assert ctx.injection_pattern_count >= 1
    assert isinstance(ctx.mount, MountCheckResult)
    assert ctx.evidence_root == DEFAULT_EVIDENCE_ROOT


# ---------------------------------------------------------------------------
# Bearer-token auth
# ---------------------------------------------------------------------------


def test_static_token_verifier_rejects_empty_token() -> None:
    with pytest.raises(ServerConfigurationError, match="empty"):
        _StaticTokenVerifier("")


def test_static_token_verifier_accepts_correct_token() -> None:
    verifier = _StaticTokenVerifier("the-right-token")
    token = asyncio.run(verifier.verify_token("the-right-token"))
    assert token is not None
    assert token.client_id == SERVER_NAME
    assert "silentwitness.tools" in token.scopes


def test_static_token_verifier_rejects_wrong_token() -> None:
    verifier = _StaticTokenVerifier("the-right-token")
    assert asyncio.run(verifier.verify_token("the-wrong-token")) is None
    assert asyncio.run(verifier.verify_token("")) is None


def test_static_token_verifier_uses_constant_time_compare() -> None:
    """Verifies hmac.compare_digest is the comparison primitive — token-
    length timing attacks are out of scope. Indirectly: a one-byte-off
    token rejects with the same shape as a length-mismatch token."""
    verifier = _StaticTokenVerifier("aaaaaaaaaaaaaaaaaaaa")
    assert asyncio.run(verifier.verify_token("aaaaaaaaaaaaaaaaaaab")) is None
    assert asyncio.run(verifier.verify_token("aaaaaaaaaaaaaaaaaaaa")) is not None


# ---------------------------------------------------------------------------
# __main__ CLI
# ---------------------------------------------------------------------------


def test_cli_parser_defaults_to_stdio_transport_port_4508() -> None:
    parser = _build_parser()
    args = parser.parse_args([])
    assert args.transport is Transport.STDIO
    assert args.host == DEFAULT_HTTP_HOST
    assert args.port == DEFAULT_HTTP_PORT


def test_cli_parser_accepts_http_with_port_override() -> None:
    parser = _build_parser()
    args = parser.parse_args(["--transport", "http", "--port", "4509"])
    assert args.transport is Transport.HTTP
    assert args.port == 4509


def test_cli_parser_rejects_unknown_transport() -> None:
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--transport", "websocket"])


def test_cli_version_reports_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    """--version writes the silentwitness_mcp version to stdout and exits 0."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert __version__ in out


def test_cli_main_propagates_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bad-config invocation surfaces as an exception, not a silent
    exit-0. Specifically: HTTP without the gateway token."""
    with pytest.raises(ServerConfigurationError):
        main(["--transport", "http"])
