"""Real integration smoke for the binary-free tools (runs anywhere, incl. macOS).

Spawns the real ``python -m silentwitness_mcp`` stdio subprocess bound to a
fresh case via the _case_env bridge, then exercises ``register_evidence`` and
``verify_evidence_hash`` over the MCP protocol. This validates the whole spine
(env bridge -> lifespan AppContext -> wrapper dep-extraction -> real registry ->
audit emit -> dict envelope through FastMCP) WITHOUT needing a forensic binary.

    uv run python scripts/itest_evidence_slice.py
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from silentwitness_mcp._case_env import build_server_env


async def _run() -> int:
    case_dir = Path(tempfile.mkdtemp(prefix="sw-itest-ev-"))
    (case_dir / "audit").mkdir(parents=True, exist_ok=True)
    evidence = case_dir / "sample.pcap"
    evidence.write_bytes(b"\xd4\xc3\xb2\xa1fake-pcap-bytes-for-itest" * 64)

    params = StdioServerParameters(
        command="python",
        args=["-m", "silentwitness_mcp"],
        env=build_server_env(case_dir, "itest", "anthropic:claude-opus-4-7"),
    )

    def _payload(result: object) -> dict[str, object]:
        sc = getattr(result, "structuredContent", None)
        if sc:
            return dict(sc)
        content = getattr(result, "content", None)
        if content:
            return dict(json.loads(content[0].text))
        return {}

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {t.name for t in (await session.list_tools()).tools}
            print(
                f"[itest] {len(tools)} tools advertised; "
                f"register_evidence={'register_evidence' in tools} "
                f"verify_evidence_hash={'verify_evidence_hash' in tools}"
            )

            reg = _payload(
                await session.call_tool(
                    "register_evidence", {"evidence_path": str(evidence), "evidence_type": "pcap"}
                )
            )
            print("[itest] register_evidence ->", json.dumps(reg))
            ver = _payload(
                await session.call_tool("verify_evidence_hash", {"evidence_path": str(evidence)})
            )
            print("[itest] verify_evidence_hash ->", json.dumps(ver))

    audit_files = sorted(p.name for p in (case_dir / "audit").glob("*.jsonl"))
    print(f"[itest] audit files: {audit_files}")

    ok = (
        reg.get("success") is True
        and isinstance(reg.get("sha256"), str)
        and ver.get("success") is True
        and ver.get("matches") is True
        and "evidence.jsonl" in audit_files
    )
    print(
        "[itest]",
        "PASS — real MCP server + case bridge + registry wiring works"
        if ok
        else "FAIL — see envelopes above",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
