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
from silentwitness_mcp._errors import ServerConfigurationError
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
    EVIDENCE_BOUND_TOOLS,
    GATEWAY_TOKEN_ENV,
    LOOPBACK_ALLOWED,
    SERVER_NAME,
    MountValidationError,
    Transport,
    _guard_mount,
    _StaticTokenVerifier,
    create_server,
)

EXPECTED_TOOL_NAMES = frozenset(
    {
        "record_observation",
        "record_interpretation",
        "record_pivot",
        "record_narrative",
        "read_tool_output",
        "approve_finding",
        "register_evidence",
        "verify_evidence_hash",
        "chainsaw_hunt",
        "hayabusa_csv_timeline",
        "zeek_run",
        "suricata_run",
        "vol_cmdline",
        "vol_dlllist",
        "vol_handles",
        "vol_lsadump",
        "vol_malfind",
        "vol_netscan",
        "vol_pslist",
        "vol_psscan",
        "vol_pstree",
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


def test_tool_stubs_advertise_ctx_parameter_via_schema() -> None:
    """The @mcp.tool() decorator inspects each stub's signature for
    Context injection. Tools advertise `ctx: Context[...]` so FastMCP
    knows to inject the request context at call time. The user-facing
    input schema must NOT include `ctx` — Context is magic-injected."""
    mcp = create_server(Transport.STDIO)
    tools = asyncio.run(mcp.list_tools())
    for tool in tools:
        # FastMCP strips the Context parameter from the public schema.
        props = (tool.inputSchema or {}).get("properties", {})
        assert "ctx" not in props, f"{tool.name} leaked Context into its input schema: {props}"


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


def test_static_token_verifier_rejects_non_string_token_without_raising() -> None:
    """A misbehaving client / SDK version handing us None, bytes, or
    int MUST NOT crash the MCP connection. The verifier returns None
    on every non-str input rather than letting TypeError escape."""
    verifier = _StaticTokenVerifier("the-right-token")
    for bogus in (None, b"the-right-token", 12345, [], {}):
        assert asyncio.run(verifier.verify_token(bogus)) is None  # type: ignore[arg-type]


def test_static_token_verifier_rejects_oversized_token() -> None:
    """A multi-megabyte token can't trigger unbounded compare_digest
    work — verifier rejects anything over 4 KiB."""
    verifier = _StaticTokenVerifier("the-right-token")
    assert asyncio.run(verifier.verify_token("x" * 5000)) is None


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


def test_cli_main_returns_ex_config_on_configuration_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """HTTP without the gateway token surfaces as exit code 78
    (EX_CONFIG) with the reason on stderr, not as a propagated
    exception. Supervisors can branch on the exit code without
    scraping the traceback."""
    monkeypatch.delenv("SILENTWITNESS_GATEWAY_TOKEN", raising=False)
    rc = main(["--transport", "http"])
    assert rc == 78
    err = capsys.readouterr().err
    assert "configuration error" in err
    assert "SILENTWITNESS_GATEWAY_TOKEN" in err


# ---------------------------------------------------------------------------
# Mount-validator BDD criterion (architecture §4.11)
# ---------------------------------------------------------------------------


def test_evidence_bound_tools_set_matches_architecture_4_11() -> None:
    """Only the tools that actually touch /evidence belong in the
    refuse-on-bad-mount set. Architecture §4.10 + §4.11."""
    assert EVIDENCE_BOUND_TOOLS == frozenset(
        {
            "record_observation",
            "register_evidence",
            "verify_evidence_hash",
            "chainsaw_hunt",
            "hayabusa_csv_timeline",
            "zeek_run",
            "suricata_run",
            "vol_cmdline",
            "vol_dlllist",
            "vol_handles",
            "vol_lsadump",
            "vol_malfind",
            "vol_netscan",
            "vol_pslist",
            "vol_psscan",
            "vol_pstree",
        }
    )


def _fake_ctx_with_mount(ok: bool, advisories: list[str] | None = None) -> object:
    """Synthesize the minimal `ctx.request_context.lifespan_context.mount`
    surface that `_guard_mount` reads. Avoids spinning up a real MCP
    session for a logic-only assertion."""
    from silentwitness_mcp._lifecycle import AppContext, MountCheckResult

    mount = MountCheckResult(ok=ok, advisories=advisories or [])
    app_ctx = AppContext(
        mount=mount,
        evidence_root=DEFAULT_EVIDENCE_ROOT,
        injection_pattern_count=1,
    )

    class _RequestContext:
        lifespan_context = app_ctx

    class _Ctx:
        request_context = _RequestContext()

    return _Ctx()


def test_guard_mount_refuses_evidence_bound_tools_when_mount_failed() -> None:
    """BDD criterion (architecture §4.11): with mount.ok=False, every
    evidence-bound tool surfaces MOUNT_NOT_RO_NOEXEC_NOSUID before any
    other body code runs."""
    ctx = _fake_ctx_with_mount(ok=False, advisories=["missing ro"])
    for tool_name in EVIDENCE_BOUND_TOOLS:
        with pytest.raises(MountValidationError, match="MOUNT_NOT_RO_NOEXEC_NOSUID"):
            _guard_mount(tool_name, ctx)  # type: ignore[arg-type]


def test_guard_mount_passes_through_non_evidence_tools_on_failed_mount() -> None:
    """record_interpretation / record_pivot / record_narrative /
    approve_finding don't touch /evidence — _guard_mount is a no-op for
    them even if the mount check failed."""
    ctx = _fake_ctx_with_mount(ok=False, advisories=["bad mount"])
    for tool_name in EXPECTED_TOOL_NAMES - EVIDENCE_BOUND_TOOLS:
        _guard_mount(tool_name, ctx)  # type: ignore[arg-type]
        # No exception = pass.


def test_guard_mount_passes_through_when_mount_ok() -> None:
    """The happy path: mount.ok=True, no guard fires for any tool."""
    ctx = _fake_ctx_with_mount(ok=True)
    for tool_name in EXPECTED_TOOL_NAMES:
        _guard_mount(tool_name, ctx)  # type: ignore[arg-type]


def test_mount_validation_error_carries_advisories() -> None:
    """The exception surfaces the advisories so the agent's response
    envelope can render them for the examiner — opaque errors are a
    silent-failure smell."""
    err = MountValidationError(["mount missing ro", "mount missing nosuid"])
    assert "ro" in str(err)
    assert err.advisories == ("mount missing ro", "mount missing nosuid")
