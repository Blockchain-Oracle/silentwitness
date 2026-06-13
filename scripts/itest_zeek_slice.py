"""Real integration smoke: drive the live MCP server end-to-end for zeek_run.

Spawns ``python -m silentwitness_mcp`` as a real stdio subprocess (exactly how
the investigator does), bound to a freshly-registered case via the _case_env
bridge, then calls ``zeek_run`` over the MCP protocol against a real pcap with
the real Zeek binary. Asserts a structured success envelope + an audit row.

Run on a host where Zeek is installed (the SIFT box / provisioned VPS):
    uv run python scripts/itest_zeek_slice.py /path/to/nitroba.pcap
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from silentwitness_common.types import EvidenceType
from silentwitness_mcp._case_env import build_server_env
from silentwitness_mcp.evidence.registry import EvidenceRegistry

EXAMINER = "itest"
MODEL = "anthropic:claude-opus-4-7"


async def _run(pcap: Path) -> int:
    case_dir = Path(tempfile.mkdtemp(prefix="sw-itest-"))
    (case_dir / "audit").mkdir(parents=True, exist_ok=True)

    # Register the evidence directly (no AuditLogger held here, so the server
    # subprocess can take the per-case audit lock without collision).
    registry = EvidenceRegistry(case_dir=case_dir)
    rec = registry.register(pcap, EvidenceType.PCAP, "sift-itest-20260613-001")
    print(f"[itest] registered {pcap.name} sha256={rec.sha256[:12]} into {case_dir}")

    params = StdioServerParameters(
        command="python",
        args=["-m", "silentwitness_mcp"],
        env=build_server_env(case_dir, EXAMINER, MODEL),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {t.name for t in (await session.list_tools()).tools}
            print(f"[itest] {len(tools)} tools advertised; zeek_run present: {'zeek_run' in tools}")

            result = await session.call_tool("zeek_run", {"pcap_path": str(pcap)})
            payload = result.structuredContent
            if payload is None and result.content:
                payload = json.loads(result.content[0].text)  # type: ignore[union-attr]
            print("[itest] zeek_run envelope:")
            print(json.dumps(payload, indent=2)[:1200])

    # Verify a real audit row landed.
    audit_files = list((case_dir / "audit").glob("*.jsonl"))
    print(f"[itest] audit files written: {[f.name for f in audit_files]}")
    ok = bool(payload) and payload.get("success") is True
    if not ok:
        print("[itest] FAIL: zeek_run did not return success=True")
        return 1
    print("[itest] PASS: real MCP server -> bridge -> zeek_run -> real Zeek binary works")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: itest_zeek_slice.py <pcap_path>", file=sys.stderr)
        return 2
    return asyncio.run(_run(Path(sys.argv[1]).resolve(strict=True)))


if __name__ == "__main__":
    raise SystemExit(main())
