# Story — Vol3 windows.malfind tool wrapper

**ID:** story-vol-malfind
**Epic:** Epic 5 — Tool wrappers: memory (Volatility 3)
**Depends on:** story-vol-pslist (provides `_run_vol`, `_VolResult`, audit-blob writer, output-model pattern)
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** wrap Volatility 3 `windows.malfind` as a typed MCP tool that returns the classic injected-code candidates (RWX private VADs + no mapped file, with hexdump preview)
**So that** the investigator agent can detect reflective DLL loading, process hollowing residue, shellcode VADs, and Cobalt Strike / Meterpreter / Sliver beacons in one call — the canonical "find evil" memory primitive (PRD FR #5; judging criteria: Breadth+Depth + IR Accuracy + Audit Trail Quality — malfind hits map directly to MITRE ATT&CK T1055).

---

## File modification map

- `src/silentwitness_mcp/tools/memory.py` — UPDATE — add `vol_malfind(...)` async function; add `MalfindHit` + `MalfindOutput` Pydantic models; extend `_VOL_CAVEATS` with `"malfind"`. ~50 LOC added (target ≤240 LOC total after this story).
- `src/silentwitness_mcp/server.py` — UPDATE — register `vol_malfind` with FastMCP.
- `tests/unit/test_vol_malfind.py` — NEW — ≥6 behavioural test cases: valid JSON with hexdump field parses, `--pid` filter argv forwarded correctly, RWX-protection hit detected, empty results (clean system), `EVIDENCE_NOT_REGISTERED`, `TOOL_FAILED`.
- `tests/integration/test_memory_e2e.py` — UPDATE — add `test_malfind_against_nist_image` (skipped if fixture absent).

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a valid Windows memory image at /evidence/case-001/memdump.vmem registered and SHA256-matched
When  vol_malfind is called with evidence_path="/evidence/case-001/memdump.vmem" and pid=None
Then  the response is ResponseEnvelope with success=True
And   data is a MalfindOutput containing list[MalfindHit]
And   each MalfindHit has typed fields: pid: int, process: str, start_vpn: int, end_vpn: int, vad_tag: str, protection: str, commit_charge: int, private_memory: bool, file_output: str | None, hexdump_first_128: str (hex-encoded), disasm_preview: str | None
And   cmd_argv == ["/opt/silentwitness/vol3-venv/bin/vol", "-f", "/evidence/case-001/memdump.vmem", "-r", "json", "windows.malware.malfind.Malfind"]
And   caveats includes "RWX private memory with no mapped file is the classic injection pattern — but legitimate JIT engines (.NET CLR, Java JVM, V8/Node, Chromium) also allocate RWX; corroborate with vol_ldrmodules and process lineage before claiming injection"
And   caveats includes "windows.malfind misses RX-only code (attacker VirtualProtect'd from RWX to RX post-write) and misses file-backed hollowed images (use vol_ldrmodules for hollowing detection)"
And   caveats includes "hexdump_first_128 captures the first 128 bytes of the suspicious VAD — MZ + PE\\0\\0 pattern indicates a PE payload; lone 0xE8/0xE9 + nop sled indicates shellcode"

Given vol_malfind is called with pid=4242
When  the subprocess argv is captured
Then  argv includes ["--pid", "4242"] after the plugin name
And   only that PID's VADs are inspected (Vol3-side filter, not server-side)

Given the Vol3 output contains a hit with protection="PAGE_EXECUTE_READWRITE" and private_memory=True and file_output=None
When  parsed
Then  the corresponding MalfindHit.protection == "PAGE_EXECUTE_READWRITE"
And   private_memory is True
And   file_output is None
And   the hexdump field contains the hex-encoded first 128 bytes verbatim from Vol3 output

Given vol_malfind is called against an unregistered evidence path
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_NOT_REGISTERED"

Given Vol3 exits non-zero (e.g., symbol-table mismatch on a Windows 11 24H2 build with no cached ISF)
Then  the response is ResponseEnvelope with success=False reason="TOOL_FAILED"
And   advisories[0] is the first 500 chars of stderr (this is the demo-time 3:00–3:30 self-correction trigger — agent reads stderr, downloads symbols, retries)

Given the registered evidence's current SHA256 does not match the manifest
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_TAMPERED"
```

---

## Shell verification

```bash
uv run pytest tests/unit/test_vol_malfind.py -v
# Must show ≥6 passing test cases

uv run pytest tests/integration/test_memory_e2e.py::test_malfind_against_nist_image -v
# Must pass when NIST fixture present; SKIPPED otherwise

uv run ruff check src/silentwitness_mcp/tools/memory.py
uv run mypy --strict src/silentwitness_mcp/tools/memory.py
# Both exit 0

wc -l src/silentwitness_mcp/tools/memory.py
# Must show ≤400 (target ≤240 after this story)
```

---

## Notes for coding agent

- **Volatility 3 strategy:** SilentWitness uses its OWN venv at `/opt/silentwitness/vol3-venv/bin/vol` (pinned `volatility3==2.27.0`). Do NOT use SIFT-managed `/opt/volatility3/bin/vol` — SIFT pins no Vol3 version (`pip.installed: upgrade: True`), and the SIFT install may pull 2.28.0 which has open issue #1985 (layer-detection regression on large memory dumps). Pre-fetch Windows ISF bundle from `https://downloads.volatilityfoundation.org/volatility3/symbols/windows.zip` into `~/.cache/volatility3/` at init.
- **CRITICAL: Plugin path migration.** As of Volatility 3 ≥2.29.0 (expected late 2026-06), `windows.malfind.Malfind` is removed — use `windows.malware.malfind.Malfind` exclusively. The deprecation stub at `framework/plugins/windows/malfind.py:11-20` has `removal_date="2026-06-07"`. This story MUST use the new path or the wrapper will fail.
- **Hexdump in JSON renderer.** Vol3's `-r json windows.malware.malfind.Malfind` includes the first hex bytes of each hit under a `Hexdump` key as a multi-line string. Capture it verbatim (do NOT re-encode), then in `MalfindHit.hexdump_first_128` store the first 128 bytes' worth of hex chars (strip whitespace, take the first 256 hex chars). Verified shape in `context/domain/03` §7.6.
- **`--pid` filter pass-through.** Add `if input_model.pid is not None: extra_argv = ["--pid", str(input_model.pid)]`. The Vol3 plugin accepts this. Server-side filter would force scanning all processes — wasteful.
- **Why this matters for the demo.** Per `context/domain/03` §1.3 and §6.1 of architecture: reflective DLL loading + Cobalt Strike + Meterpreter all produce RWX private VADs that `malfind` flags. This is the "find evil" moment in the memory pipeline. The caveat about JIT false positives is critical — the entity gate (Epic 3) will catch over-claims, but the caveat seeds the right interpretation in the model's context.
- **Reuse `_run_vol`.** Two-liner over the skeleton — only the plugin name + extra-argv build + output-model class change.
- **Caveats source.** `context/domain/03` §7.6 Gotchas. Three caveats from the spec source — do NOT trim; the false-positive caveat is load-bearing for IR Accuracy scoring.
- **Plugin name string.** `windows.malware.malfind.Malfind` — class-suffixed form.
- **The "symbol-table mismatch" failure path is the demo crown jewel.** When Vol3 stderr contains `No suitable symbol table found` or `Win32k symbol failure`, the agent's hook layer (Epic 8) will read the stderr advisory, dispatch a symbol-rebuild side-quest, and retry — that is the 3:00–3:30 demo moment. This story does NOT implement the retry — it just ensures the stderr first 500 chars land in `advisories[0]` so the upstream hook can match on it.
- **No raw hex-to-bytes conversion needed.** Store the hex string. The citation gate later will hash the normalized stdout, not the decoded hex.
- **Output-model field names.** Use snake_case Python names with Pydantic `Field(alias=...)` for Vol3's `Start VPN`, `End VPN`, `Tag`, `Protection`, `CommitCharge`, `PrivateMemory`, `File output`, `Hexdump`, `Disasm`.
