"""Real integration test of the read_tool_output -> cite -> record_observation loop.

Proves the demo-critical path: the agent can read a tool-output file's content,
quote an exact line, and record an observation that PASSES the citation + entity
gates. Runs fully locally (needs the spaCy en_core_web_lg model for the entity
gate; no forensic binary required).

    uv run python scripts/itest_citation_loop.py
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from silentwitness_mcp._case_env import build_server_env


def _payload(result: object) -> dict[str, object]:
    sc = getattr(result, "structuredContent", None)
    if sc:
        return dict(sc)
    content = getattr(result, "content", None)
    if content:
        return dict(json.loads(content[0].text))
    return {}


async def _run() -> int:
    case_dir = Path(tempfile.mkdtemp(prefix="sw-itest-cite-"))
    (case_dir / "audit").mkdir(parents=True, exist_ok=True)
    # Simulate a zeek conn.log that a prior zeek_run would have produced.
    log = case_dir / ".tool-output" / "zeek" / "abc123" / "conn.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("ts\tuid\tid.orig_h\tid.resp_h\n1234\tCabc\t10.0.0.5\tevil.example.com\n")

    params = StdioServerParameters(
        command="python",
        args=["-m", "silentwitness_mcp"],
        env=build_server_env(case_dir, "itest", "anthropic:claude-opus-4-7"),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {t.name for t in (await session.list_tools()).tools}
            print(f"[itest] read_tool_output advertised: {'read_tool_output' in tools}")

            rd = _payload(await session.call_tool("read_tool_output", {"output_path": str(log)}))
            meta = {k: v for k, v in rd.items() if k != "content"}
            print("[itest] read_tool_output ->", json.dumps(meta))
            print("[itest] content:\n" + str(rd.get("content")))

            # Quote the exact line (index 1) verbatim and cite it.
            obs = _payload(
                await session.call_tool(
                    "record_observation",
                    {
                        "text": "The host 10.0.0.5 connected to evil.example.com.",
                        "audit_ids": [rd["audit_id"]],
                        "cited_spans": [
                            {
                                "audit_id": rd["audit_id"],
                                "sha256_of_normalized_output": rd["sha256_of_normalized_output"],
                                "line_start": 1,
                                "line_end": 2,
                                "span_text": "10.0.0.5\tevil.example.com",
                            }
                        ],
                    },
                )
            )
            print("[itest] record_observation ->", json.dumps(obs))

            # Negative case: a span that is NOT in the cited output must REJECT,
            # and the rejection envelope must carry the read_tool_output fix-hint
            # (the strongest-lever, at-failure guidance).
            bad = _payload(
                await session.call_tool(
                    "record_observation",
                    {
                        "text": "The host 10.0.0.5 did something.",
                        "audit_ids": [rd["audit_id"]],
                        "cited_spans": [
                            {
                                "audit_id": rd["audit_id"],
                                "sha256_of_normalized_output": rd["sha256_of_normalized_output"],
                                "line_start": 1,
                                "line_end": 2,
                                "span_text": "this text is definitely not in the log",
                            }
                        ],
                    },
                )
            )
            bad_advisories = " ".join(str(a) for a in (bad.get("advisories") or []))
            bad_data = bad.get("data") if isinstance(bad.get("data"), dict) else {}
            rejected = bad_data.get("success") is False
            hint_present = "read_tool_output" in bad_advisories
            print(f"[itest] bad-citation rejected={rejected} fix-hint-in-advisories={hint_present}")

    data = obs.get("data")
    if not isinstance(data, dict):
        data = {}
    ok = (
        data.get("success") is True
        and isinstance(data.get("observation_id"), str)
        and rejected
        and hint_present
    )
    print(
        "[itest]",
        f"PASS — observation {data.get('observation_id')} accepted via read_tool_output citation"
        if ok
        else f"FAIL — observation not accepted: {data.get('reason')}",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
