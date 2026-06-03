# Story — parse_evtx tool wrapper (EvtxECmd)

**ID:** story-parse-evtx
**Epic:** Epic 7 — Tool wrappers: log + network (EVTX + Hayabusa + Chainsaw + Zeek + Suricata)
**Depends on:** story-fastmcp-server-bootstrap, story-response-envelope, story-audit-logger, story-evidence-registry, story-output-normalizer
**Estimate:** ~1.5h (skeleton story for the log family — first `log.py` wrapper; subsequent log stories reuse the dotnet subprocess + JSON parse + audit pattern)
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** wrap EvtxECmd as a typed MCP tool `parse_evtx`
**So that** the investigator agent can extract structured Windows Event Log records (`EventId`, `Channel`, `Provider`, `Computer`, `TimeCreated`, `EventRecordId`, `Level`, `UserId`, `Payload`, `PayloadData1`..`PayloadData6`, `MapDescription`) over a typed contract with server-side parsing, evidence-registry enforcement, and audit logging — covering FOR508 high-value EIDs (4624/4625/4672/4688/1102, Sysmon 1/3/7/11, PowerShell 4104) for downstream Hayabusa + Chainsaw corroboration (PRD FR #5; judging criteria: Breadth+Depth + IR Accuracy + Audit Trail Quality).

This is the **skeleton story** for Epic 7's log family — it lands the `_run_dotnet_log_tool` async subprocess helper, the shared `_LogResult` adapter, the audit-blob writer, and the Pydantic output-model pattern that `hayabusa_csv_timeline` and `chainsaw_hunt` (the next two stories in this epic) reuse.

---

## File modification map

- `src/silentwitness_mcp/tools/log.py` — NEW — module skeleton + first wrapper. Docstring cites `architecture.md` §4.2 row 15 (`parse_evtx`) + `context/.raw-design-research/03` §EZ Tools line 115 (the `EvtxeCmd` inner-directory quirk — EvtxECmd is in the `_NESTED_TOOLS` set; see story-parse-mft for the FLAT-vs-nested rule) + `context/domain/06` §5.2 (EvtxECmd invocation patterns) + `context/domain/02` §17/18 + §16 (Sysmon EID catalog). Public API: `parse_evtx(input: EvtxInput) -> ToolResponse[EvtxOutput]`. Private helpers: `_run_dotnet_log_tool(dll_path: Path, argv: list[str], timeout_s: float) -> _LogResult` (shared by hayabusa/chainsaw stories — gets the signature right HERE), `_normalize_and_store(stdout: bytes, case_id: str, audit_id: str) -> tuple[Path, str]` (audit-blob writer returning `(stdout_path, result_sha256)`), `_security_channel_eid_list() -> list[int]` (returns the canonical Security-channel EIDs the wrapper uses when translating logical `channel="Security"` into the `--inc <comma-joined EIDs>` form EvtxECmd expects), `_LogResult` dataclass (`exit_code`, `stdout_normalized`, `stderr`, `elapsed_ms`, `audit_id`, `stdout_path`, `result_sha256`). Pydantic models: `EvtxInput(evidence_path: Path, channel: str | None, csv_out: Path)`, `EvtxRecord(EventId: int, Channel: str, Provider: str, Computer: str, TimeCreated: datetime, EventRecordId: str, Level: str, UserId: str | None, MapDescription: str | None, Payload: str | None, PayloadData1: str | None, PayloadData2: str | None, PayloadData3: str | None, PayloadData4: str | None, PayloadData5: str | None, PayloadData6: str | None)` (Pydantic `Field(alias=...)` to map EvtxECmd CSV PascalCase columns to typed Python names; note `EventRecordId` is a **string** in EvtxECmd output, NOT an int), `EvtxOutput(records: list[EvtxRecord], row_count: int, truncated: bool)`. Target ≤140 LOC after this story (leaves ~260 LOC across the remaining 2 log wrappers under the 400-LOC ceiling per CICD_SPEC §6.1).
- `src/silentwitness_mcp/tools/_log_common.py` — NEW — shared constants: `EVTXECMD_DLL = Path("/opt/zimmermantools/EvtxeCmd/EvtxECmd.dll")` (note: inner `EvtxeCmd/` directory with lowercase `e` — **verified `context/.raw-design-research/03` §EZ Tools line 115 + §Bottom line line 299**; do NOT use `/opt/zimmermantools/EvtxECmd/EvtxECmd.dll`), `DOTNET_BIN = Path("/usr/bin/dotnet")`, default timeout 600s, `LogFailureReason` enum (`EVIDENCE_NOT_REGISTERED`, `EVIDENCE_TAMPERED`, `MOUNT_NOT_RO_NOEXEC_NOSUID`, `DOTNET_NOT_FOUND`, `EVTXECMD_NOT_FOUND`, `TOOL_FAILED`, `TOOL_TIMEOUT`, `OUTPUT_PARSE_FAILED`), `_LOG_CAVEATS` per-tool caveat catalog (entries added per story). ~80 LOC.
- `src/silentwitness_mcp/server.py` — UPDATE — register `parse_evtx` with the FastMCP `Server` instance from story-fastmcp-server-bootstrap.
- `tests/fixtures/log/evtx_sample.csv` — NEW — small CSV (≤15 rows) mirroring real EvtxECmd output columns (Security 4624 row + Sysmon 1 row + PowerShell 4104 row + Security 1102 audit-log-cleared row).
- `tests/fixtures/log/evtx_truncated.csv` — NEW — CSV cut mid-row (simulates aborted EvtxECmd run).
- `tests/unit/tools/test_log_parse_evtx.py` — NEW — ≥7 behavioural test cases: (a) valid EvtxECmd CSV parses into `EvtxOutput` with all typed columns populated (incl. `EventRecordId: str`, `UserId`, `MapDescription`, `Payload`, `PayloadData1..6`), (b) logical `channel="Security"` is translated by the wrapper into `--inc <comma-joined Security EIDs>` (NOT a literal channel-name filter — EvtxECmd's `--inc` filters by EID list, not channel), (c) unregistered evidence returns `success=False` reason `EVIDENCE_NOT_REGISTERED`, (d) SHA256 mismatch returns `success=False` reason `EVIDENCE_TAMPERED`, (e) EvtxECmd non-zero exit returns `success=False` reason `TOOL_FAILED` with first 500 chars of stderr captured in advisories — AND wrapper additionally parses stderr for Serilog `[ERR]`/`[FTL]` markers since EvtxECmd's exit code is unreliable, (f) truncated CSV returns `success=True` with `truncated=True` and advisory `"partial parse: <N> rows recovered before truncation"`, (g) missing dotnet binary returns `success=False` reason `DOTNET_NOT_FOUND` pointing the agent at `install.sh`. Subprocess mocked via `monkeypatch` on `asyncio.create_subprocess_exec`.
- `tests/integration/tools/test_log_parse_evtx_integration.py` — NEW — single end-to-end test that invokes the real `dotnet /opt/zimmermantools/EvtxeCmd/EvtxECmd.dll -f <Security.evtx> --csv <out>` path against a tiny synthetic EVTX fixture (skipped via `pytest.mark.skipif(not Path('/opt/zimmermantools/EvtxeCmd/EvtxECmd.dll').exists())` so CI on non-SIFT runners still passes).

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a registered Windows EVTX at /evidence/case-001/Security.evtx
And   the file is registered in cases/case-001/evidence.json with a SHA256 matching its current content
And   /evidence/ is mounted ro,noexec,nosuid (mount validation passes)
And   /opt/zimmermantools/EvtxeCmd/EvtxECmd.dll exists on disk
And   /usr/bin/dotnet exists on disk
When  the MCP tool parse_evtx is called with EvtxInput(evidence_path=Path("/evidence/case-001/Security.evtx"), channel=None, csv_out=Path("/tmp/evtx_out"))
Then  the response is ResponseEnvelope with success=True
And   data is an EvtxOutput containing a list[EvtxRecord]
And   each EvtxRecord has typed fields: EventId: int, Channel: str, Provider: str, Computer: str, TimeCreated: datetime (timezone-aware UTC), EventRecordId: str (string, NOT int — EvtxECmd surfaces it as a string), Level: str, UserId: str | None (the SID), MapDescription: str | None, Payload: str | None (XML payload), PayloadData1..PayloadData6: str | None (map-populated columns)
And   data_provenance.cmd_argv == ["/usr/bin/dotnet", "/opt/zimmermantools/EvtxeCmd/EvtxECmd.dll", "-f", "/evidence/case-001/Security.evtx", "--csv", "/tmp/evtx_out"]
And   data_provenance.result_sha256 is a 64-hex-character string
And   data_provenance.stdout_path points to a file under cases/case-001/audit/blobs/
And   one JSONL line is appended to cases/case-001/audit/log.jsonl with audit_id matching format sift-<examiner>-<YYYYMMDD>-<NNN>
And   that JSONL line carries result_sha256 == SHA256 of the normalized CSV bytes
And   elapsed_ms is a positive float
And   caveats includes "EvtxECmd cannot parse old EVT (Windows XP/2003) format; cannot render data for custom event providers whose manifests are missing — fields may appear as raw template binding"
And   caveats includes "Application/System logs referencing absent provider manifests render EventData as raw XML payload rather than friendly columns; corroborate with hayabusa_csv_timeline for rule-tagged interpretation"
And   corroboration includes a hint pointing at hayabusa_csv_timeline and chainsaw_hunt for Sigma-rule-driven interpretation of the same channel

Given the evidence path is not registered in cases/<case_id>/evidence.json
When  parse_evtx is called with that path
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_NOT_REGISTERED"
And   no dotnet subprocess is spawned (verified by mocked spawn count == 0)
And   one JSONL line is still written to log.jsonl recording the refusal (exit_code field omitted)

Given the registered evidence file's current SHA256 does not match the manifest entry
When  parse_evtx is called
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_TAMPERED"
And   no dotnet subprocess is spawned

Given /evidence/ is mounted without one of ro / noexec / nosuid
When  parse_evtx is called
Then  the response is ResponseEnvelope with success=False reason="MOUNT_NOT_RO_NOEXEC_NOSUID"
And   advisories includes the missing-flag list

Given EvtxInput.channel == "Security"
When  parse_evtx is called against a registered evidence path
Then  the wrapper translates the logical channel name into the canonical Security-EID list via _security_channel_eid_list()
And   data_provenance.cmd_argv includes "--inc" followed by the comma-joined EID list (NOT a channel-name literal — EvtxECmd's --inc filters by EID, not channel)
And   the resulting EvtxOutput.records all have EventId in _security_channel_eid_list()

Given EvtxECmd exits with a non-zero return code (e.g., corrupted EVTX chunk checksum)
When  parse_evtx is called against a valid registered path
Then  the response is ResponseEnvelope with success=False reason="TOOL_FAILED"
And   advisories[0] is the first 500 chars of stderr
And   the audit JSONL line records exit_code != 0 and elapsed_ms

Given EvtxECmd writes a CSV that is truncated mid-row (process killed)
When  parse_evtx is called
Then  the response is ResponseEnvelope with success=True
And   data.truncated == True
And   advisories includes "partial parse: <N> rows recovered before truncation" with N matching the count of fully-parsed rows

Given /usr/bin/dotnet does not exist on this host
When  parse_evtx is called
Then  the response is ResponseEnvelope with success=False reason="DOTNET_NOT_FOUND"
And   advisories[0] points the agent at install.sh for SIFT bootstrap

Given /opt/zimmermantools/EvtxeCmd/EvtxECmd.dll does not exist on this host
When  parse_evtx is called
Then  the response is ResponseEnvelope with success=False reason="EVTXECMD_NOT_FOUND"
And   advisories[0] mentions the inner-directory quirk (EvtxeCmd vs EvtxECmd) per context/.raw-design-research/03

Given EvtxECmd emits a CSV that fails Pydantic validation (mid-stream renderer crash producing a header-only file)
When  parse_evtx is called
Then  the response is ResponseEnvelope with success=False reason="OUTPUT_PARSE_FAILED"
And   advisories includes the first 200 chars of the unparseable bytes
```

---

## Shell verification

```bash
# Unit tests pass with ≥7 behavioural cases
uv run pytest tests/unit/tools/test_log_parse_evtx.py -v
# Must show ≥7 passing

# Integration test skipped on non-SIFT, runs green on SIFT
uv run pytest tests/integration/tools/test_log_parse_evtx_integration.py -v

# Lint + format + strict types
uv run ruff check src/silentwitness_mcp/tools/log.py src/silentwitness_mcp/tools/_log_common.py
uv run ruff format --check src/silentwitness_mcp/tools/log.py src/silentwitness_mcp/tools/_log_common.py
uv run mypy --strict src/silentwitness_mcp/tools/log.py src/silentwitness_mcp/tools/_log_common.py
# All three must exit 0

# File-size guard (CICD_SPEC §6.1) — aggregate cap across all 3 log tools is ≤400
wc -l src/silentwitness_mcp/tools/log.py | awk '{ if ($1 > 400) exit 1 }'

# Coverage floor for tools/* family per CICD_SPEC §8.1 (target 85% project)
uv run coverage run -m pytest tests/unit/tools/test_log_parse_evtx.py
uv run coverage report --include="src/silentwitness_mcp/tools/log.py,src/silentwitness_mcp/tools/_log_common.py" --fail-under=85
# Must exit 0

# §13 banned patterns: no shell=True, no mock/fake/dummy in src/
git diff main...HEAD -- 'src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated|shell=True)" | grep -v "test\|spec\|§14 carve-out"
# Must output nothing
```

---

## Notes for coding agent

- **EvtxECmd DLL path on SIFT 2026 — INNER-DIRECTORY QUIRK.** The verified path is `/opt/zimmermantools/EvtxeCmd/EvtxECmd.dll` — note the inner directory is `EvtxeCmd` (lowercase `e`) but the DLL filename is `EvtxECmd.dll` (uppercase `E` in `EC`). Source: `context/.raw-design-research/03` §EZ Tools line 115 + §"Deployment-instruction implications" line 299 ("**EZ Tool note for EvtxECmd:** the `.dll` lives at `/opt/zimmermantools/EvtxeCmd/EvtxECmd.dll` (note inner `EvtxeCmd/` dir — lowercase `e`). Wrapper handles this — don't hardcode the path."). Hardcode this exact path in `_log_common.py::EVTXECMD_DLL`. Do NOT use `/opt/zimmermantools/EvtxECmd/EvtxECmd.dll` — that path does not exist and the tool call will fail with `EVTXECMD_NOT_FOUND`.
- **EvtxECmd invocation pattern** (per `context/domain/06` §5.2 + verified flag catalog). Build `cmd_argv` as: `["/usr/bin/dotnet", "/opt/zimmermantools/EvtxeCmd/EvtxECmd.dll", "-f", str(evidence_path), "--csv", str(csv_out)]`. When `EvtxInput.channel` is set, the wrapper calls `_security_channel_eid_list()` to fetch the canonical EID list for that logical channel and appends `["--inc", ",".join(str(e) for e in eids)]`. The canonical Security-channel EID list returned by `_security_channel_eid_list()` is: `[1102, 4624, 4625, 4634, 4647, 4648, 4672, 4673, 4674, 4688, 4697, 4698, 4702, 4720, 4722, 4723, 4724, 4725, 4732, 4738, 4740, 4756, 4768, 4769, 4771, 4776, 5140, 5145, 5156, 5158]`. EvtxECmd's `--inc` filters by **EID list, NOT by channel name** — the wrapper translates the logical `channel="Security"` into the EID set so the audit log records deterministic argv.
- **CSV column mapping.** EvtxECmd CSV headers (verified against the maps catalog at `context/domain/06` §5.2 line 1205 + `context/domain/04` §EVTX EID catalog at line 1600 + real EvtxECmd headers): `RecordNumber`, `EventRecordId` (**string**, not int), `TimeCreated`, `EventId`, `Level`, `Provider`, `Channel`, `Computer`, `UserId` (the SID — NOT `UserSid`), `MapDescription` (the rendered human-readable description — NOT `RenderedDescription`), `UserName`, `RemoteHost`, `PayloadData1`..`PayloadData6` (map-populated columns), `ExecutableInfo`, `HiddenRecord`, `SourceFile`, `Keywords`, `Payload` (XML payload string). Map to `EvtxRecord` via Pydantic `Field(alias=...)`. `TimeCreated` is ISO-8601 UTC in EvtxECmd output — parse to timezone-aware `datetime`. `EventRecordId` stays a string (it is **NOT** a typed int in EvtxECmd output). The `Payload` XML and the six `PayloadData<N>` columns are surfaced separately — they are NOT collapsed into a single `EventData: dict`. EvtxECmd's `--fj` flag emits one JSON event per line; the CSV path is preferred here because it survives schema drift better.
- **Exit-code WARNING:** EvtxECmd calls `Environment.Exit(0)` even on errors. Wrapper MUST parse stderr for Serilog `[ERR]` / `[FTL]` markers via regex `^\[\d{2}:\d{2}:\d{2} (ERR|FTL)\]` and surface as `TOOL_FAILED` — exit code alone misses failures.
- **Subprocess pattern** (reusable across all 3 log tools). `_run_dotnet_log_tool(dll_path: Path, argv: list[str], timeout_s: float = 600.0) -> _LogResult` uses `asyncio.create_subprocess_exec(*argv, stdout=PIPE, stderr=PIPE)` with `asyncio.wait_for(proc.communicate(), timeout=timeout_s)`. On `asyncio.TimeoutError`: `proc.terminate()`, then after a 5s grace `proc.kill()`, return `TOOL_TIMEOUT`. Capture stderr first 500 chars for `TOOL_FAILED` advisory. **Get the signature right HERE — the next two log stories depend on it.**
- **Audit blob storage** (per architecture §4.6). The full normalized CSV is persisted at `cases/<case_id>/audit/blobs/<audit_id>.txt`. This is what the citation gate reads later — without this blob the verify chain breaks. SHA256 the normalized bytes (post-normalizer: EvtxECmd version banner stripped per `verification/normalizer.py`, ANSI sequences stripped, line endings normalized to `\n`) and store the hash in the audit JSONL.
- **Evidence-registry call ordering** (per architecture §4.10). First action of `parse_evtx` is `await evidence_registry.assert_registered(evidence_path)`. If it raises `EvidenceNotRegistered`, return `ToolResponse(success=False, advisories=["EVIDENCE_NOT_REGISTERED: <path>"], …)` — do NOT spawn dotnet. Second: `await evidence_registry.verify_hash(evidence_path)` to catch post-registration tampering → `EVIDENCE_TAMPERED`. Third: `mount.assert_safe_options("/evidence")` → `MOUNT_NOT_RO_NOEXEC_NOSUID`. Fourth: `Path(DOTNET_BIN).exists()` → `DOTNET_NOT_FOUND` with advisory pointing the agent at `install.sh`. Fifth: `EVTXECMD_DLL.exists()` → `EVTXECMD_NOT_FOUND` with advisory citing the inner-directory quirk. Only then spawn the subprocess.
- **Truncation detection** (mirror story-parse-mft §truncation). Parse the CSV with `csv.DictReader`. Wrap the row iterator in a try/except. On `csv.Error` or short-row exception, count the rows parsed so far, set `EvtxOutput.truncated=True`, append the advisory `"partial parse: <N> rows recovered before truncation"`, and return success=True. This is partial-success — the agent should still be able to cite the rows that did parse.
- **Caveats — verbatim discipline** (per architecture §4.3). The caveat strings on a successful response are sourced VERBATIM from `_LOG_CAVEATS["parse_evtx"]` populated from `context/domain/06` §5.2 (Limitations section): `["EvtxECmd cannot parse old EVT (Windows XP/2003) format; cannot render data for custom event providers whose manifests are missing — fields may appear as raw template binding", "Application/System logs referencing absent provider manifests render EventData as raw XML payload rather than friendly columns; corroborate with hayabusa_csv_timeline for rule-tagged interpretation"]`. Caveats are user-visible in the report's Appendix-Audit; never paraphrase.
- **Skeleton helpers MUST be reusable.** `_run_dotnet_log_tool(dll_path, argv, timeout_s)` is imported by `hayabusa_csv_timeline` and `chainsaw_hunt`. `_normalize_and_store(stdout, case_id, audit_id)` is imported by both. `_LogResult` is the return type both consume. Get all three signatures right HERE — story-hayabusa-timeline and story-chainsaw-hunt are written assuming they exist.
- **LOC budget tracking** (per architecture §4.2 line 321 + CICD_SPEC §6.1). After this story `tools/log.py` should sit at ~140 LOC. Remaining two log stories (`hayabusa_csv_timeline` + `chainsaw_hunt`) add ~130 LOC each → aggregate ~400 LOC at epic close. If your draft pushes past ~160 LOC for this story alone, factor more aggressively into `_log_common.py`.
- **No shell interpolation** (per architecture §2 trust boundary 2). Build `cmd_argv` as `list[str]` and pass to `create_subprocess_exec`. Never use `subprocess.run(..., shell=True)`. The DLL path and evidence path go in as separate argv elements — never concatenated into a shell string.
- **Vocabulary discipline** (per PRD §14 / architecture §6 line 497). Never "court-admissible" in any caveat or docstring; describe the audit chain as "defensible audit trail" or "structural rejection" if the language is needed. Never "Ralph Wiggum Loop" in either code or comments.
- **Context7 hint.** When in doubt about EvtxECmd CSV column shapes, the authoritative source is the EZ Tools maps repo (https://github.com/EricZimmerman/evtx/tree/master/evtx/Maps). Per CICD_SPEC §12 + architecture §12, call `context7` for "EvtxECmd output schema" before guessing at column names.
