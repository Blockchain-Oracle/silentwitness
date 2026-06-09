"""Pydantic-level tests for :class:`NetscanEntry`.

These exercise the model's validator chain directly (no subprocess
mock, no orchestrator). The pipeline-level refusal contract — that
a model :class:`ValidationError` surfaces as
:attr:`VolFailureReason.OUTPUT_PARSE_FAILED` — is covered separately
in :mod:`test_vol_netscan`."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from silentwitness_mcp.tools._memory_models import NetscanEntry


def _tcp_row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "Offset": 0xFA8001234567,
        "Proto": "TCPv4",
        "LocalAddr": "10.0.0.5",
        "LocalPort": 49152,
        "ForeignAddr": "203.0.113.42",
        "ForeignPort": 443,
        "State": "ESTABLISHED",
        "PID": 1234,
        "Owner": "svchost.exe",
        "Created": "2026-06-09T08:00:00+00:00",
    }
    base.update(overrides)
    return base


def _udp_row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "Offset": 0xFA8001112222,
        "Proto": "UDPv4",
        "LocalAddr": "0.0.0.0",  # noqa: S104
        "LocalPort": 53,
        "ForeignAddr": "*",
        "ForeignPort": "*",
        "State": "*",
        "PID": 968,
        "Owner": "svchost.exe",
        "Created": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Wildcard normalisation (mode="before")
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("foreign_addr", "foreign_port", "state"),
    [
        ("*", "*", "*"),
        ("*", "*", None),
        ("*", 0, None),
        ("1.2.3.4", "*", None),
    ],
)
def test_udp_wildcard_combinations_normalised_per_field(
    foreign_addr: object, foreign_port: object, state: object
) -> None:
    """Each wildcard field rewrites independently. A regression that
    gates ForeignPort-rewrite on ForeignAddr-being-wildcard would leak
    ``"*"`` into the typed ``int | None`` field on row #4 (1.2.3.4 /
    ``"*"`` / None) and explode at Pydantic validation."""
    entry = NetscanEntry.model_validate(
        _udp_row(ForeignAddr=foreign_addr, ForeignPort=foreign_port, State=state)
    )
    assert entry.foreign_addr == (None if foreign_addr == "*" else foreign_addr)
    assert entry.foreign_port == (None if foreign_port == "*" else foreign_port)
    assert entry.state is None  # cross-field UDP rule


# ---------------------------------------------------------------------------
# Sentinel rejection — "*" is the ONLY recognised wildcard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "non_ip",
    [
        # Round-1 sentinels (regex-rejected) — kept as baseline.
        "-",
        "",
        "null",
        "?",
        # Round-2 silent-failure additions — these PASSED the loose
        # ``[.:]`` shape gate but are NOT parseable IPs. Locks in the
        # ipaddress.ip_address() tightening.
        ".",
        ":",
        "..",
        "null:",
        "X:",
        "..foo",
        "<error>.",
        # Whitespace / control characters that ``$`` would have
        # silently accepted at end-of-string on the state regex.
        "127.0.0.1\n",
        "127.0.0.1 ",
        " 127.0.0.1",
        "127.0.0.1\t",
    ],
)
def test_non_parseable_sentinel_in_foreign_addr_rejected_loud(non_ip: str) -> None:
    """The IP defence is ``ipaddress.ip_address()`` in try/except, not
    a regex — anything stdlib can't parse fails loud regardless of
    shape. Round-1 ``[.:]`` regex passed ``"null:"`` / ``"X:"`` /
    ``"127.0.0.1\\n"`` silently; the closed defence rejects them.
    NB: ``"::"`` IS the valid IPv6 unspecified address (all-zeros)
    and is intentionally accepted — caller's caveat list still flags
    LISTENING on a non-loopback bind as a backdoor candidate."""
    with pytest.raises(ValidationError):
        NetscanEntry.model_validate(_udp_row(ForeignAddr=non_ip, ForeignPort=None, State=None))


@pytest.mark.parametrize("non_ip", ["-", "null", ":", "127.0.0.1\n", "null:"])
def test_non_parseable_sentinel_in_local_addr_rejected_loud(non_ip: str) -> None:
    """Same closed defence applies to local_addr."""
    with pytest.raises(ValidationError):
        NetscanEntry.model_validate(_tcp_row(LocalAddr=non_ip))


@pytest.mark.parametrize(
    "bad_state",
    [
        # Round-1 sentinels — baseline.
        "-",
        "",
        "null",
        "?",
        "established",
        # Round-2 silent-failure addition: trailing newline. The
        # round-1 ``$``-anchored regex matched BEFORE the newline,
        # silently accepting ``"ESTABLISHED\\n"``. ``\\A\\Z`` rejects.
        "ESTABLISHED\n",
        "ESTABLISHED ",
        " ESTABLISHED",
        "ESTABLISHED\t",
    ],
)
def test_non_uppercase_token_state_rejected_loud(bad_state: str) -> None:
    """``state`` must be ``\\A[A-Z][A-Z0-9_]+\\Z`` or None.
    End-of-string anchors close the trailing-newline silent path."""
    with pytest.raises(ValidationError):
        NetscanEntry.model_validate(_tcp_row(State=bad_state))


# ---------------------------------------------------------------------------
# Cross-field invariants (mode="after")
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "missing_field",
    ["ForeignAddr", "ForeignPort", "State"],
)
def test_tcp_entry_missing_foreign_side_rejected(missing_field: str) -> None:
    """TCP entries must carry all three of foreign_addr, foreign_port,
    state. A TCP row missing any of them is schema-impossible and
    would let a downstream "TCP connection to <none>" citation slip
    into the IR report."""
    row = _tcp_row()
    row[missing_field] = None
    with pytest.raises(ValidationError):
        NetscanEntry.model_validate(row)


def test_udp_entry_with_non_null_state_rejected() -> None:
    """UDP is connectionless; an entry claiming UDP + state="LISTENING"
    is schema-impossible (TCP listeners use TCPv*, not UDPv*)."""
    with pytest.raises(ValidationError):
        NetscanEntry.model_validate(_udp_row(ForeignAddr=None, ForeignPort=None, State="LISTENING"))


# ---------------------------------------------------------------------------
# Verbatim preservation — the entity gate's load-bearing invariant
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "addr",
    [
        "192.168.1.50",
        "::ffff:192.168.1.50",  # IPv4-mapped IPv6 — must NOT canonicalise
        "fe80::1",
        "2001:db8::1",
        "::1",
    ],
)
def test_addresses_preserved_verbatim_no_canonicalisation(addr: str) -> None:
    """The entity gate matches typed observations against verbatim
    cited spans in tool output. Canonicalising ``::ffff:192.168.1.50``
    to ``192.168.1.50`` here would cause every IPv6-cited observation
    to fail the gate."""
    proto = "TCPv6" if ":" in addr else "TCPv4"
    entry = NetscanEntry.model_validate(_tcp_row(Proto=proto, ForeignAddr=addr))
    assert entry.foreign_addr == addr  # byte-identical, no normalisation


# ---------------------------------------------------------------------------
# Future-compat: novel TCB states forward through unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "novel_state",
    ["SYN_RECV2", "ESTABLISHED2", "NEW_TCB_STATE"],
)
def test_novel_tcb_states_forwarded_not_rejected(novel_state: str) -> None:
    """``state: str`` (not ``Literal``) is a deliberate forward-compat
    choice — Windows kernel evolution should not silently break the
    netscan tool. ``_TCB_STATE`` shape (uppercase + underscore + digit)
    accepts plausible future states."""
    entry = NetscanEntry.model_validate(_tcp_row(State=novel_state))
    assert entry.state == novel_state
