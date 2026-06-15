# Story — Vol3 windows.dlllist + windows.handles tool wrappers

**ID:** story-vol-dlllist-handles
**Epic:** Epic 5 — Tool wrappers: memory (Volatility 3)
**Depends on:** story-vol-pslist (provides `_run_vol`, `_VolResult`, audit-blob writer)
**Estimate:** ~1h (two wrappers, both formulaic over the skeleton)
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** wrap Volatility 3 `windows.dlllist` (loaded DLLs per process via PEB loader-list walk) and `windows.handles` (open handle table per process) as typed MCP tools
**So that** the investigator agent can detect side-loaded malicious DLLs, identify cross-process handles enabling injection (`PROCESS_VM_WRITE` + `PROCESS_CREATE_THREAD`), enumerate malware-fingerprint mutexes, and recover deleted-but-still-open file payloads (PRD FR #5; judging criteria: Breadth+Depth + IR Accuracy — handles to lsass.exe with `PROCESS_VM_READ` is the classic Mimikatz signature).

---

## File modification map

- `src/silentwitness_mcp/tools/memory.py` — UPDATE — add `vol_dlllist(...)` and `vol_handles(...)` async functions; add `DllEntry` + `DllListOutput` + `HandleEntry` + `HandlesOutput` Pydantic models; extend `_VOL_CAVEATS` with `"dlllist"` and `"handles"`. ~70 LOC added (target ≤380 LOC total after this story — close to ceiling; see split note below).
- `src/silentwitness_mcp/server.py` — UPDATE — register `vol_dlllist` and `vol_handles` with FastMCP.
- `tests/unit/test_vol_dlllist.py` — NEW — ≥5 behavioural test cases: valid JSON parses, `--pid` filter argv forwarded, DLL with non-standard path detected, `EVIDENCE_NOT_REGISTERED`, `TOOL_FAILED`.
- `tests/unit/test_vol_handles.py` — NEW — ≥6 behavioural test cases: valid JSON parses for File / Mutant / Process / Key handle types, `--pid` + `--object-types` filter argv forwarded correctly, Process handle with `PROCESS_VM_WRITE | PROCESS_CREATE_THREAD` granted-access detected, `EVIDENCE_NOT_REGISTERED`, `TOOL_FAILED`, malformed handle-value field.
- `tests/integration/test_memory_e2e.py` — UPDATE — add `test_dlllist_against_nist_image` and `test_handles_against_nist_image` (both skipped if fixture absent).

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a valid Windows memory image at /evidence/case-001/memdump.vmem registered and SHA256-matched
When  vol_dlllist is called with evidence_path="/evidence/case-001/memdump.vmem" and pid=None
Then  the response is ResponseEnvelope with success=True
And   data is a DllListOutput containing list[DllEntry]
And   each DllEntry has typed fields: pid: int, process: str, base: int, size: int, name: str, path: str | None, load_time: datetime | None, file_output: str | None
And   cmd_argv == ["/opt/silentwitness/vol3-venv/bin/vol", "-f", "/evidence/case-001/memdump.vmem", "-r", "json", "windows.dlllist.DllList"]
And   caveats includes "windows.dlllist walks the PEB InLoadOrderModuleList — reflectively-loaded DLLs (Cobalt Strike sRDI, Meterpreter, custom reflective loaders) are INVISIBLE here; corroborate with vol_malfind + ldrmodules"
And   caveats includes "a system DLL name loaded from a non-standard path (e.g., ntdll.dll from C:\\Users\\Public\\) is a side-loading red flag"
And   caveats includes "LoadTime is when the DLL entered the loader list — usable for per-process timeline reconstruction"
And   caveats includes "suspicious-DLL detection requires a baseline of expected DLLs per process — without it, false-positive rate is high for anything more interesting than the system-DLL-from-wrong-path pattern"

Given vol_dlllist is called with pid=4242
Then  argv includes ["--pid", "4242"] after the plugin name

Given the same registered image
When  vol_handles is called with pid=None and object_types=None
Then  the response is ResponseEnvelope with success=True
And   data is a HandlesOutput containing list[HandleEntry]
And   each HandleEntry has typed fields: pid: int, process: str, offset: int, handle_value: int, type: str, granted_access: int, name: str | None
And   cmd_argv == ["/opt/silentwitness/vol3-venv/bin/vol", "-f", "/evidence/case-001/memdump.vmem", "-r", "json", "windows.handles.Handles"]
And   caveats includes "cross-process handles (Process A → Process B) with PROCESS_VM_WRITE | PROCESS_CREATE_THREAD | PROCESS_ALL_ACCESS access are the injection prerequisites — flag these"
And   caveats includes "mutex (Mutant) names are malware family fingerprints — many families use distinctive Global\\<random> names to prevent re-infection"
And   caveats includes "handles to \\Device\\PhysicalMemory or unusual \\Device\\ paths are driver-IPC / rootkit candidates"
And   caveats includes "file handles to deleted files persist while the handle is open — vol_dumpfiles can recover the content even after del"
And   caveats includes "a non-system process holding a handle to lsass.exe with PROCESS_VM_READ is the classic Mimikatz signature"

Given vol_handles is called with pid=1234 and object_types=["File","Mutant"]
When  the subprocess argv is captured
Then  argv includes ["--pid", "1234"]
And   argv includes ["--object-types", "File,Mutant"]
And   only those handle types are returned

Given vol_dlllist or vol_handles is called against an unregistered evidence path
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_NOT_REGISTERED"

Given the registered evidence's SHA256 mismatches the manifest
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_TAMPERED"

Given Vol3 exits non-zero on either wrapper
Then  the response is ResponseEnvelope with success=False reason="TOOL_FAILED"
And   advisories[0] is the first 500 chars of stderr
```

---

## Shell verification

```bash
uv run pytest tests/unit/test_vol_dlllist.py tests/unit/test_vol_handles.py -v
# Must show ≥11 passing test cases combined

uv run pytest tests/integration/test_memory_e2e.py::test_dlllist_against_nist_image tests/integration/test_memory_e2e.py::test_handles_against_nist_image -v
# Must pass when NIST fixture present; SKIPPED otherwise

uv run ruff check src/silentwitness_mcp/tools/memory.py
uv run mypy --strict src/silentwitness_mcp/tools/memory.py
# Both exit 0

wc -l src/silentwitness_mcp/tools/memory.py
# Must show ≤400 (target ≤380 after this story — last story will need to split if vol-lsadump pushes over)
```

---

## Notes for coding agent

- **Volatility 3 strategy:** SilentWitness uses its OWN venv at `/opt/silentwitness/vol3-venv/bin/vol` (pinned `volatility3==2.27.0`). Do NOT use SIFT-managed `/opt/volatility3/bin/vol` — SIFT pins no Vol3 version (`pip.installed: upgrade: True`), and the SIFT install may pull 2.28.0 which has open issue #1985 (layer-detection regression on large memory dumps). Pre-fetch Windows ISF bundle from `https://downloads.volatilityfoundation.org/volatility3/symbols/windows.zip` into `~/.cache/volatility3/` at init.
- **dlllist output columns.** Per `context/domain/03` §7.7: `PID`, `Process`, `Base`, `Size`, `Name`, `Path`, `LoadTime`, `File output`. `Path` may be None for paged-out entries.
- **handles output columns.** Per `context/domain/03` §7.9: `PID`, `Process`, `Offset`, `HandleValue`, `Type`, `GrantedAccess`, `Name`. `granted_access` is an integer bitmask; do NOT decode here — the model and the entity gate cite the raw value and decode contextually.
- **handle-type allowlist for filtering.** Vol3 `--object-types` accepts comma-separated list: `Process`, `Thread`, `File`, `Key`, `Section`, `Event`, `Mutant`, `Semaphore`, `Token`, `Directory`, `SymbolicLink`. Pass-through verbatim — no server-side validation beyond "must be non-empty list".
- **`--object-types` argv form.** Vol3 wants `--object-types File,Mutant` (single string, comma-separated). Build as `["--object-types", ",".join(object_types)]`.
- **Reflective DLL caveat is load-bearing.** `context/domain/03` §7.7 + §1.3: reflectively loaded DLLs do NOT appear in the loader list. If the agent claims "process X is clean because dlllist shows no malicious DLLs", it has missed Cobalt Strike beacons. The caveat seeds the right interpretation; the critic (Epic 10) uses it to CHALLENGE such claims.
- **Mimikatz signature caveat.** `context/domain/03` §"hashdump / lsadump section" + §6.2 attack patterns: "non-system process holding a handle to lsass.exe with PROCESS_VM_READ". This is one of the highest-signal patterns for credential theft and worth the caveat slot.
- **Reuse `_run_vol`.** Both wrappers under 40 LOC each when `_run_vol` handles the skeleton.
- **Plugin name strings.** `windows.dlllist.DllList` and `windows.handles.Handles` — class-suffixed.
- **LOC budget warning.** After this story `memory.py` is at ~380 LOC. The next story (`vol-lsadump`) adds ~30 LOC and pushes the file to ~410 — over the 400 cap. The next story's notes will direct the agent to split `vol_lsadump` (and only `vol_lsadump`) into a separate `tools/memory_extras.py` file, keeping `memory.py` at ~380 and `memory_extras.py` at ~50 LOC. Do NOT pre-emptively split here — leave that decision to `story-vol-lsadump` where the LOC counter actually trips.
