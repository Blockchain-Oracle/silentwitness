"""Tests for the retroactive PR-118 silent-failure fixes:

* ``_guard_mount`` LIFESPAN_CONTEXT_MISSING — when an evidence-bound
  tool is invoked outside the FastMCP lifespan scope (broken test
  harness, lifespan startup race), the previous code raised a raw
  ``AttributeError`` that FastMCP wrapped as an unhelpful ``ToolError``
  string. The fix surfaces a structured ``MountValidationError`` with
  ``reason="LIFESPAN_CONTEXT_MISSING"``.
* ``MountValidationError.reason`` typed Literal — downstream code can
  branch on the reason without parsing the ``str(err)`` message.
* ``run_server`` defense-in-depth host re-check — FastMCP itself
  accepts any host string, so a future refactor that moved or removed
  ``_validate_http_config`` would silently bypass the DNS-rebinding
  gate. The re-check at handoff time keeps the gate load-bearing.
* ``main()`` structured exit codes — ServerConfigurationError → 78
  (EX_CONFIG), OSError → 74 (EX_IOERR). Previously these dumped raw
  tracebacks into the JSON-RPC framing seam.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from silentwitness_mcp.__main__ import _EX_CONFIG, _EX_IOERR, main
from silentwitness_mcp._lifecycle import DEFAULT_EVIDENCE_ROOT, AppContext, MountCheckResult
from silentwitness_mcp.server import (
    EVIDENCE_BOUND_TOOLS,
    LOOPBACK_ALLOWED,
    MountValidationError,
    ServerConfigurationError,
    Transport,
    _guard_mount,
    run_server,
)

# ---------------------------------------------------------------------------
# _guard_mount — LIFESPAN_CONTEXT_MISSING branch
# ---------------------------------------------------------------------------


def _ctx_with_lifespan(lifespan_context: AppContext | None) -> Any:
    """Build a minimal ctx surface mirroring ``Context.request_context``
    structure that `_guard_mount` reads. The real ``Context`` Pydantic
    model is heavier than the guard actually exercises."""

    class _RC:
        pass

    rc = _RC()
    rc.lifespan_context = lifespan_context  # type: ignore[attr-defined]

    class _Ctx:
        pass

    ctx = _Ctx()
    ctx.request_context = rc  # type: ignore[attr-defined]
    return ctx


def _ok_app_ctx() -> AppContext:
    return AppContext(
        mount=MountCheckResult(ok=True),
        evidence_root=DEFAULT_EVIDENCE_ROOT,
        injection_pattern_count=1,
    )


def test_guard_mount_raises_lifespan_context_missing_when_none() -> None:
    """Evidence-bound tool invoked outside the FastMCP lifespan scope
    (lifespan_context is None) must surface
    LIFESPAN_CONTEXT_MISSING — NOT a raw AttributeError."""
    ctx = _ctx_with_lifespan(lifespan_context=None)
    for tool_name in EVIDENCE_BOUND_TOOLS:
        with pytest.raises(MountValidationError) as exc_info:
            _guard_mount(tool_name, ctx)
        assert exc_info.value.reason == "LIFESPAN_CONTEXT_MISSING"
        assert "did not yield an AppContext" in exc_info.value.advisories[0]


def test_guard_mount_passes_through_non_evidence_tools_even_when_lifespan_missing() -> None:
    """A None lifespan_context only matters for evidence-bound tools.
    Non-evidence tools see no AppContext access and pass through silently."""
    ctx = _ctx_with_lifespan(lifespan_context=None)
    # Pass through (no exception) for the non-evidence members.
    _guard_mount("record_interpretation", ctx)
    _guard_mount("record_pivot", ctx)


def test_guard_mount_uses_mount_failure_reason_default_for_bad_mount() -> None:
    """When the AppContext IS bound but mount.ok=False, reason defaults
    to MOUNT_NOT_RO_NOEXEC_NOSUID — preserves the original semantics."""
    bad_ctx = AppContext(
        mount=MountCheckResult(ok=False, advisories=["missing ro"]),
        evidence_root=DEFAULT_EVIDENCE_ROOT,
        injection_pattern_count=1,
    )
    ctx = _ctx_with_lifespan(lifespan_context=bad_ctx)
    with pytest.raises(MountValidationError) as exc_info:
        _guard_mount("record_observation", ctx)
    assert exc_info.value.reason == "MOUNT_NOT_RO_NOEXEC_NOSUID"


# ---------------------------------------------------------------------------
# MountValidationError typed reason
# ---------------------------------------------------------------------------


def test_mount_validation_error_reason_is_typed() -> None:
    """The reason attribute is a typed Literal — downstream code can
    branch on it without parsing str(err) or .advisories."""
    err = MountValidationError(["mount missing ro"])
    assert err.reason == "MOUNT_NOT_RO_NOEXEC_NOSUID"
    err2 = MountValidationError(["no app ctx"], reason="LIFESPAN_CONTEXT_MISSING")
    assert err2.reason == "LIFESPAN_CONTEXT_MISSING"


def test_mount_validation_error_str_is_stable_for_log_dedup() -> None:
    """str(err) starts with the reason code so log dedup (Sentry,
    ELK) groups failures by stable prefix, not by the variable
    advisories list. The previous embedded-advisories format made
    every distinct ordering a distinct issue."""
    err = MountValidationError(["a", "b"])
    err2 = MountValidationError(["b", "a"])
    # Both render with the same reason prefix.
    assert str(err).startswith("MOUNT_NOT_RO_NOEXEC_NOSUID")
    assert str(err2).startswith("MOUNT_NOT_RO_NOEXEC_NOSUID")


# ---------------------------------------------------------------------------
# run_server defense-in-depth host re-check (H4)
# ---------------------------------------------------------------------------


def test_run_server_rechecks_host_before_handoff_to_streamable_http() -> None:
    """A misconfigured server.settings.host slipping past
    _validate_http_config (future refactor) must still fail-closed
    before mcp.run('streamable-http') gets called."""
    with patch("silentwitness_mcp.server.create_server") as mock_create:
        # Synthesize a server whose .settings.host is not in LOOPBACK_ALLOWED.
        # This simulates a future bug where _validate_http_config was
        # bypassed but the host still made it through.
        mock_server = mock_create.return_value
        mock_server.settings.host = "0.0.0.0"  # noqa: S104 — testing the gate that rejects this
        with pytest.raises(ServerConfigurationError, match="defense-in-depth"):
            run_server(Transport.HTTP, host="127.0.0.1", port=4508)
    # mcp.run() was never reached.
    mock_server.run.assert_not_called()


def test_run_server_stdio_does_not_recheck_host() -> None:
    """The defense-in-depth check is HTTP-only — stdio has no bound
    host and the re-check would be a noop, so it's correctly skipped."""
    with patch("silentwitness_mcp.server.create_server") as mock_create:
        mock_server = mock_create.return_value
        # Don't set host — confirm the stdio path doesn't read it.
        run_server(Transport.STDIO)
    mock_server.run.assert_called_once_with(transport="stdio")


# ---------------------------------------------------------------------------
# main() structured exit codes (H3)
# ---------------------------------------------------------------------------


def test_main_returns_ex_config_on_server_configuration_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """ServerConfigurationError → exit code 78 (EX_CONFIG) so
    supervisors can branch on configuration vs IO failures without
    scraping stderr."""
    with patch(
        "silentwitness_mcp.__main__.run_server",
        side_effect=ServerConfigurationError("missing token"),
    ):
        rc = main(["--transport", "stdio"])
    assert rc == _EX_CONFIG == 78
    err = capsys.readouterr().err
    assert "configuration error" in err
    assert "missing token" in err


def test_main_returns_ex_ioerr_on_oserror(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """OSError (port-bind collision, EACCES on bind, etc.) → exit code
    74 (EX_IOERR). Otherwise these would dump a Python traceback into
    the JSON-RPC framing seam and corrupt the stdio transport."""
    with patch(
        "silentwitness_mcp.__main__.run_server",
        side_effect=OSError("Address already in use"),
    ):
        rc = main(["--transport", "stdio"])
    assert rc == _EX_IOERR == 74
    err = capsys.readouterr().err
    assert "bind/IO error" in err


def test_main_still_returns_130_on_keyboard_interrupt(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """SIGINT path was already correct — pin it so the H3 fix didn't
    regress the existing happy-shutdown behavior."""
    with patch("silentwitness_mcp.__main__.run_server", side_effect=KeyboardInterrupt):
        rc = main(["--transport", "stdio"])
    assert rc == 130
    assert "interrupted" in capsys.readouterr().err


def test_main_returns_zero_on_clean_run() -> None:
    """Happy path: run_server returns without raising → exit 0."""
    with patch("silentwitness_mcp.__main__.run_server", return_value=None):
        rc = main(["--transport", "stdio"])
    assert rc == 0


# ---------------------------------------------------------------------------
# Anchor checks — sanity on the constants the fixes depend on
# ---------------------------------------------------------------------------


def test_loopback_allowed_unchanged_by_defense_in_depth() -> None:
    """The defense-in-depth re-check reads LOOPBACK_ALLOWED — pin its
    contents so a loosening (e.g. someone adds '0.0.0.0') trips the
    test, not the production DNS-rebinding gate."""
    assert LOOPBACK_ALLOWED == frozenset({"127.0.0.1", "::1", "localhost"})


def test_ex_codes_match_sysexits() -> None:
    """BSD sysexits.h values. If these drift, supervisor playbooks
    keyed on the exit code break."""
    assert _EX_CONFIG == 78
    assert _EX_IOERR == 74


def test_default_evidence_root_is_path() -> None:
    """Trivial pin — Path('/evidence') is what _lifecycle.check_mount
    defaults to. Any refactor that loosens this needs explicit review
    because the mount validator is the architectural gate."""
    assert DEFAULT_EVIDENCE_ROOT == Path("/evidence")
