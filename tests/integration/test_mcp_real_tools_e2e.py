"""Regression guard: the MCP server must serve REAL tools, not NotImplementedError stubs.

This is the test that would have caught the original defect — a server that
registered 21 stubs while the agent (and only the agent) drove it through the
stdio boundary. The existing suite mocked ``_do_agent_run`` and called the tool
functions directly, so the agent->server->tool path was never exercised and the
stub server shipped "complete".

This test spawns the REAL ``python -m silentwitness_mcp`` stdio subprocess, bound
to a case via the ``_case_env`` bridge, and calls tools over the MCP protocol —
exactly as the investigator does. It asserts real envelopes come back (a stub
would surface as a tool error / NotImplementedError). It needs NO API key, NO
forensic binaries, and NO spaCy model, so it runs unconditionally in CI.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from silentwitness_mcp._case_env import build_server_env

# Firewall layer #1: the raw-evidence tools (vol_*/zeek/chainsaw/hayabusa/suricata) are
# demoted to ingest feeders and no longer advertised. The agent's surface is the index
# query tools + finding recorders + evidence register/verify + read_tool_output.
_EXPECTED_TOOL_COUNT = 12
# approve_finding stays a stub (CLI/examiner-only HMAC approval). Everything else is real.
_STILL_STUBBED = frozenset({"approve_finding"})


def _payload(result: object) -> dict[str, Any]:
    sc = getattr(result, "structuredContent", None)
    if sc:
        return dict(sc)
    content = getattr(result, "content", None)
    if content:
        return dict(json.loads(content[0].text))  # type: ignore[union-attr]
    return {}


async def _exercise(case_dir: Path) -> dict[str, Any]:
    (case_dir / "audit").mkdir(parents=True, exist_ok=True)
    evidence = case_dir / "sample.pcap"
    evidence.write_bytes(b"\xd4\xc3\xb2\xa1regression-fixture" * 32)
    blob = case_dir / ".tool-output" / "zeek" / "abc" / "conn.log"
    blob.parent.mkdir(parents=True, exist_ok=True)
    blob.write_text("ts\tuid\torig\tresp\n1\tC1\t10.0.0.5\tevil.example.com\n")

    params = StdioServerParameters(
        command="python",
        args=["-m", "silentwitness_mcp"],
        env=build_server_env(case_dir, "ci", "anthropic:claude-opus-4-7"),
    )
    out: dict[str, Any] = {}
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            out["tools"] = sorted(t.name for t in (await session.list_tools()).tools)
            out["register_evidence"] = _payload(
                await session.call_tool(
                    "register_evidence",
                    {"evidence_path": str(evidence), "evidence_type": "pcap"},
                )
            )
            out["verify_evidence_hash"] = _payload(
                await session.call_tool("verify_evidence_hash", {"evidence_path": str(evidence)})
            )
            out["read_tool_output"] = _payload(
                await session.call_tool("read_tool_output", {"output_path": str(blob)})
            )
            # Path-traversal: a file outside .tool-output must be refused.
            out["read_traversal"] = _payload(
                await session.call_tool("read_tool_output", {"output_path": "/etc/passwd"})
            )
            # record_observation over the wire with a bad citation: exercises the
            # JSON->ObservationInput coercion + citation gate + the at-failure
            # self-correction advisory, without needing spaCy (the citation gate
            # rejects the unknown record_id before the entity gate runs).
            out["record_observation_reject"] = _payload(
                await session.call_tool(
                    "record_observation",
                    {
                        "text": "Host 10.0.0.5 did something.",
                        "cited_spans": [{"record_id": 999999, "span_text": "something"}],
                    },
                )
            )
    return out


@pytest.fixture(scope="module")
def server_results() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="sw-e2e-") as tmp:
        return asyncio.run(_exercise(Path(tmp)))


def test_server_advertises_all_tools(server_results: dict[str, Any]) -> None:
    assert len(server_results["tools"]) == _EXPECTED_TOOL_COUNT


def test_register_evidence_is_real_not_a_stub(server_results: dict[str, Any]) -> None:
    res = server_results["register_evidence"]
    assert res.get("success") is True, f"register_evidence returned a non-real envelope: {res}"
    assert isinstance(res.get("sha256"), str) and len(res["sha256"]) == 64


def test_verify_evidence_hash_is_real_not_a_stub(server_results: dict[str, Any]) -> None:
    res = server_results["verify_evidence_hash"]
    assert res.get("success") is True
    assert res.get("matches") is True


def test_read_tool_output_refuses_path_traversal(server_results: dict[str, Any]) -> None:
    res = server_results["read_traversal"]
    assert res.get("success") is False
    assert res.get("reason") == "PATH_NOT_ALLOWED"


def test_record_observation_runs_over_the_wire_and_rejects_bad_citation(
    server_results: dict[str, Any],
) -> None:
    """The wrapper does real work the direct-call tests skip: JSON->pydantic
    coercion, the citation gate, and the at-failure read_tool_output advisory.
    A made-up audit_id must reject (citation gate) with the fix-hint over the
    stdio boundary — proving it's not a NotImplementedError stub."""
    res = server_results["record_observation_reject"]
    data = res.get("data") if isinstance(res.get("data"), dict) else {}
    assert data.get("success") is False
    assert data.get("reason") == "RECORD_NOT_FOUND"
    advisories = " ".join(str(a) for a in (res.get("advisories") or []))
    assert "search_evidence" in advisories or "record_id" in advisories


def test_read_tool_output_returns_citable_content(server_results: dict[str, Any]) -> None:
    res = server_results["read_tool_output"]
    assert res.get("success") is True
    assert isinstance(res.get("audit_id"), str)
    assert isinstance(res.get("sha256_of_normalized_output"), str)
    assert "evil.example.com" in str(res.get("content"))


def test_wired_tools_do_not_raise_not_implemented(server_results: dict[str, Any]) -> None:
    """Every tool we exercised returned a structured envelope. A stub would have
    surfaced as a NotImplementedError tool error (empty/error payload)."""
    for name in ("register_evidence", "verify_evidence_hash", "read_tool_output"):
        assert server_results[name].get("success") is True, f"{name} is not really wired"
