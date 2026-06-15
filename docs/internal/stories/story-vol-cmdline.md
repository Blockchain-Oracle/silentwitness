# Story — Vol3 windows.cmdline tool wrapper

**ID:** story-vol-cmdline
**Epic:** Epic 5 — Tool wrappers: memory (Volatility 3)
**Depends on:** story-vol-pslist (provides `_run_vol`, `_VolResult`, audit-blob writer)
**Estimate:** ~45min
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** wrap Volatility 3 `windows.cmdline` as a typed MCP tool returning per-process command lines from each `_EPROCESS.Peb.ProcessParameters.CommandLine`
**So that** the investigator agent can identify malicious invocations (base64-encoded PowerShell, `rundll32` with suspicious args, LOLBin abuse) when Sysmon 4688 / EID 1 was never deployed — the most common reality on the kinds of hosts in this hackathon's case corpus (PRD FR #5; judging criteria: Breadth+Depth + IR Accuracy).

---

## File modification map

- `src/silentwitness_mcp/tools/memory.py` — UPDATE — add `vol_cmdline(...)` async function; add `CmdlineEntry` + `CmdlineOutput` Pydantic models; extend `_VOL_CAVEATS` with `"cmdline"`. ~30 LOC added (target ≤310 LOC total after this story).
- `src/silentwitness_mcp/server.py` — UPDATE — register `vol_cmdline` with FastMCP.
- `tests/unit/test_vol_cmdline.py` — NEW — ≥5 behavioural test cases: valid JSON parses, empty args entry (System / Registry processes), `--pid` filter argv forwarded, `EVIDENCE_NOT_REGISTERED`, `TOOL_FAILED`.
- `tests/integration/test_memory_e2e.py` — UPDATE — add `test_cmdline_against_nist_image` (skipped if fixture absent).

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a valid Windows memory image at /evidence/case-001/memdump.vmem registered and SHA256-matched
When  vol_cmdline is called with evidence_path="/evidence/case-001/memdump.vmem" and pid=None
Then  the response is ResponseEnvelope with success=True
And   data is a CmdlineOutput containing list[CmdlineEntry]
And   each CmdlineEntry has typed fields: pid: int, process: str, args: str | None
And   cmd_argv == ["/opt/silentwitness/vol3-venv/bin/vol", "-f", "/evidence/case-001/memdump.vmem", "-r", "json", "windows.cmdline.CmdLine"]
And   caveats includes "windows.cmdline reads each process's PEB ProcessParameters — beats Sysmon EID 1 / Security 4688 when Sysmon was never deployed (the common reality on legacy hosts)"
And   caveats includes "System (PID 4), Registry, smss.exe, and some service-host processes have empty or null Args — this is normal, not malicious"
And   caveats includes "Command lines can be PEB-tamper-overwritten post-creation (RtlInitUnicodeString trick used by some Cobalt Strike profiles) — for tamper detection corroborate against ImageFileName lineage and vol_handles"
And   caveats includes "long base64 strings in Args (encoded PowerShell) and rundll32 / regsvr32 / mshta / msbuild / installutil arguments are LOLBin red flags worth follow-up"
And   caveats includes "PEB may be paged out — missing Args for paged-out PEBs is a smear artifact, not evidence of tampering; rerun with --single-swap-locations pagefile.sys if pagefile is available"

Given vol_cmdline is called with pid=1234
When  the subprocess argv is captured
Then  argv includes ["--pid", "1234"] after the plugin name
And   only PID 1234's command line is queried (Vol3-side filter)

Given the Vol3 output contains an entry with PID=4 and Args=null
When  parsed
Then  CmdlineEntry.pid == 4
And   args is None (not the literal string "null")

Given vol_cmdline is called against an unregistered evidence path
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_NOT_REGISTERED"

Given vol_cmdline is called and the registered evidence's SHA256 mismatches the manifest
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_TAMPERED"

Given Vol3 exits non-zero
Then  the response is ResponseEnvelope with success=False reason="TOOL_FAILED"
And   advisories[0] is the first 500 chars of stderr
```

---

## Shell verification

```bash
uv run pytest tests/unit/test_vol_cmdline.py -v
# Must show ≥5 passing test cases

uv run pytest tests/integration/test_memory_e2e.py::test_cmdline_against_nist_image -v
# Must pass when NIST fixture present; SKIPPED otherwise

uv run ruff check src/silentwitness_mcp/tools/memory.py
uv run mypy --strict src/silentwitness_mcp/tools/memory.py
# Both exit 0

wc -l src/silentwitness_mcp/tools/memory.py
# Must show ≤400 (target ≤310 after this story)
```

---

## Notes for coding agent

- **Volatility 3 strategy:** SilentWitness uses its OWN venv at `/opt/silentwitness/vol3-venv/bin/vol` (pinned `volatility3==2.27.0`). Do NOT use SIFT-managed `/opt/volatility3/bin/vol` — SIFT pins no Vol3 version (`pip.installed: upgrade: True`), and the SIFT install may pull 2.28.0 which has open issue #1985 (layer-detection regression on large memory dumps). Pre-fetch Windows ISF bundle from `https://downloads.volatilityfoundation.org/volatility3/symbols/windows.zip` into `~/.cache/volatility3/` at init.
- **Output columns.** Per `context/domain/03` §7.12: `PID`, `Process`, `Args`. Map to snake_case via Pydantic `Field(alias=...)`. `Args` may be a string, the literal `null`, an empty string, or a Vol3 placeholder `"Required memory at <addr> is not valid"` for paged-out PEBs — coerce all non-string placeholders to `None`.
- **`--pid` filter pass-through.** `if input_model.pid is not None: extra_argv = ["--pid", str(input_model.pid)]`. Forward to Vol3.
- **Why this matters (caveat #1).** `context/domain/03` §1.2: "Command history not yet persisted... cmd.exe consoles hold their full history" + §7.12: cmdline reads the PEB directly. On hosts without Sysmon, this is the ONLY way to recover what a process was actually launched with. The caveat says this explicitly — the investigator's specialist (Epic 9 memory specialist) reads it and prioritises cmdline early.
- **PEB-tamper caveat.** `context/domain/03` §7.12: "Command lines can be tampered with by an attacker who calls RtlInitUnicodeString to overwrite the PEB string after process creation (technique seen in some Cobalt Strike profiles)." Keep this verbatim — the critic agent (Epic 10) uses it as a CHALLENGE seed when a suspicious process has an innocuous-looking cmdline.
- **LOLBin caveat.** From `context/domain/03` §1.3 — `rundll32.exe`, `regsvr32.exe`, `mshta.exe`, `msbuild.exe`, `installutil.exe`. Verbatim list in the caveat.
- **Reuse `_run_vol`.** Smallest wrapper in Epic 5 — ~30 LOC for everything.
- **Plugin name string.** `windows.cmdline.CmdLine` — class-suffixed form (capital-L).
- **No pagefile injection.** This story does NOT add `--single-swap-locations`; that is a future enhancement once `vol_info` lands and a pagefile is registered as separate evidence. The caveat documents the limitation so over-claims on paged-out cmdlines do not happen.
