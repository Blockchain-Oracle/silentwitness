# Story — Vol3 windows.netscan tool wrapper

**ID:** story-vol-netscan
**Epic:** Epic 5 — Tool wrappers: memory (Volatility 3)
**Depends on:** story-vol-pslist (provides `_run_vol`, `_VolResult`, audit-blob writer)
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** wrap Volatility 3 `windows.netscan` as a typed MCP tool that returns active TCP/UDP connections, listeners, and recently-closed endpoints with owning PID and timestamps
**So that** the investigator agent can identify C2 traffic, data-exfiltration channels, and listening backdoor sockets without depending on Sysmon EID 3 being deployed (PRD FR #5; judging criteria: Breadth+Depth + IR Accuracy — netscan is the network-side equivalent of psscan for finding history the live OS no longer reports).

---

## File modification map

- `src/silentwitness_mcp/tools/memory.py` — UPDATE — add `vol_netscan(...)` async function; add `NetscanEntry` + `NetscanOutput` Pydantic models; extend `_VOL_CAVEATS` with `"netscan"`. ~40 LOC added (target ≤280 LOC total after this story).
- `src/silentwitness_mcp/server.py` — UPDATE — register `vol_netscan` with FastMCP.
- `tests/unit/test_vol_netscan.py` — NEW — ≥6 behavioural test cases: valid JSON with ESTABLISHED + LISTENING + TIME_WAIT entries parses, IPv4 and IPv6 local/foreign addresses both parse, empty results, `EVIDENCE_NOT_REGISTERED`, `TOOL_FAILED`, malformed PID field handled.
- `tests/integration/test_memory_e2e.py` — UPDATE — add `test_netscan_against_nist_image` (skipped if fixture absent).

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a valid Windows memory image at /evidence/case-001/memdump.vmem registered and SHA256-matched
When  vol_netscan is called with evidence_path="/evidence/case-001/memdump.vmem"
Then  the response is ResponseEnvelope with success=True
And   data is a NetscanOutput containing list[NetscanEntry]
And   each NetscanEntry has typed fields: offset: int, proto: Literal["TCPv4","TCPv6","UDPv4","UDPv6"], local_addr: str, local_port: int, foreign_addr: str | None, foreign_port: int | None, state: str | None, pid: int | None, owner: str | None, created: datetime | None
And   cmd_argv == ["/opt/silentwitness/vol3-venv/bin/vol", "-f", "/evidence/case-001/memdump.vmem", "-r", "json", "windows.netscan.NetScan"]
And   caveats includes "windows.netscan pool-tag scan returns both active AND recently-closed endpoints — filter state to ESTABLISHED for live C2 evidence; TIME_WAIT / CLOSE_WAIT / FIN_WAIT_* are historical"
And   caveats includes "windows.netscan is build-fragile on Windows 10/11 — symbol drift across builds can drop entries or surface artifacts; cross-check with vol_netstat when available"
And   caveats includes "Owner process resolution requires the PID still being valid in pslist — owner may be blank for endpoints whose process has exited"
And   caveats includes "LISTENING state on a non-loopback bind from a non-standard process is a backdoor candidate; LISTENING on loopback is normal IPC"

Given the Vol3 JSON contains an entry with proto="TCPv6" and a foreign address like "::ffff:192.168.1.50"
When  parsed into NetscanEntry
Then  local_addr and foreign_addr preserve the verbatim string (IPv4-mapped IPv6 is NOT normalised — the entity gate compares against verbatim cited spans)
And   the state field preserves Vol3's verbatim value (e.g., "ESTABLISHED", "LISTENING", "TIME_WAIT")

Given a UDP entry where Vol3 emits the foreign_addr and foreign_port as "*" and "*"
When  parsed
Then  foreign_addr is None
And   foreign_port is None
And   state is None

Given vol_netscan is called against an unregistered evidence path
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_NOT_REGISTERED"

Given vol_netscan is called and the registered evidence's SHA256 mismatches the manifest
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_TAMPERED"

Given Vol3 exits non-zero
Then  the response is ResponseEnvelope with success=False reason="TOOL_FAILED"
And   advisories[0] is the first 500 chars of stderr
And   the audit JSONL line records exit_code != 0
```

---

## Shell verification

```bash
uv run pytest tests/unit/test_vol_netscan.py -v
# Must show ≥6 passing test cases

uv run pytest tests/integration/test_memory_e2e.py::test_netscan_against_nist_image -v
# Must pass when NIST fixture present; SKIPPED otherwise

uv run ruff check src/silentwitness_mcp/tools/memory.py
uv run mypy --strict src/silentwitness_mcp/tools/memory.py
# Both exit 0

wc -l src/silentwitness_mcp/tools/memory.py
# Must show ≤400 (target ≤280 after this story)
```

---

## Notes for coding agent

- **Volatility 3 strategy:** SilentWitness uses its OWN venv at `/opt/silentwitness/vol3-venv/bin/vol` (pinned `volatility3==2.27.0`). Do NOT use SIFT-managed `/opt/volatility3/bin/vol` — SIFT pins no Vol3 version (`pip.installed: upgrade: True`), and the SIFT install may pull 2.28.0 which has open issue #1985 (layer-detection regression on large memory dumps). Pre-fetch Windows ISF bundle from `https://downloads.volatilityfoundation.org/volatility3/symbols/windows.zip` into `~/.cache/volatility3/` at init.
- **Output columns.** Per `context/domain/03` §7.10: `Offset`, `Proto`, `LocalAddr`, `LocalPort`, `ForeignAddr`, `ForeignPort`, `State`, `PID`, `Owner`, `Created`. Map to snake_case with Pydantic `Field(alias=...)`. Vol3 JSON keys preserve the column names verbatim.
- **State enum vs str.** Vol3 emits states including `LISTENING`, `ESTABLISHED`, `CLOSE_WAIT`, `TIME_WAIT`, `FIN_WAIT_1`, `FIN_WAIT_2`, `CLOSED`, `SYN_SENT`, `SYN_RECV`. Use `str` not `Literal` to forward-compat new states across Vol3 releases. The caveat documents the demo-relevant subset.
- **IPv6 + IPv4-mapped handling.** The entity gate later runs an IPv4 regex AND an IPv6 regex over observation text and checks each entity against cited spans. The verbatim-preservation rule for `local_addr` / `foreign_addr` is what lets the entity gate succeed — if we normalise `::ffff:192.168.1.50` to `192.168.1.50` here, the gate will reject any observation citing the original IPv6 form.
- **Build-fragility caveat is mandatory.** `context/domain/06` §"netscan reliability": "On Windows 10/11, `windows.netscan` is fragile across builds; if symbols slightly disagree, output can be missing entries or contain artifacts." This is the kind of caveat that distinguishes a defensible report from an overclaim — keep it verbatim.
- **No `--include-corrupt` flag.** Vol3 supports it; do NOT pass it. Corrupt entries should be excluded from the typed list — they introduce false positives downstream.
- **Reuse `_run_vol`.** Same skeleton as previous wrappers — only plugin-name + output-model change.
- **Plugin name string.** `windows.netscan.NetScan` — class-suffixed form.
- **Caveat ordering matters.** Put the "filter to ESTABLISHED" caveat first — that is the action-shaping caveat for the agent. The build-fragility caveat is the CYA caveat for the report.
- **No `vol_netstat` in Epic 5 catalog.** Architecture §4.2 lists 9 vol_* tools; `windows.netstat` is mentioned in caveats but not as a separate tool — netscan is the workhorse. If a future story adds `vol_netstat` it goes in a follow-up epic.
