# Story — Vol3 windows.pslist tool wrapper

**ID:** story-vol-pslist
**Epic:** Epic 5 — Tool wrappers: memory (Volatility 3)
**Depends on:** story-fastmcp-server-bootstrap, story-response-envelope, story-audit-logger, story-evidence-registry, story-output-normalizer
**Estimate:** ~1.5h (skeleton story for the memory family — first vol_* wrapper; subsequent stories reuse the subprocess + parse + audit pattern)
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** wrap Volatility 3 `windows.pslist` as a typed MCP tool
**So that** the investigator agent can list the active process table over a typed contract with server-side parsing, evidence-registry enforcement, and audit logging (PRD FR #5; judging criteria: Breadth+Depth + IR Accuracy + Audit Trail Quality).

This is the **skeleton story** for Epic 5 — it lands the subprocess invocation helper, JSON-renderer parser, audit-blob writer, and Pydantic output-model pattern that all six remaining vol_* stories reuse.

---

## File modification map

- `src/silentwitness_mcp/tools/__init__.py` — NEW — empty package marker.
- `src/silentwitness_mcp/tools/memory.py` — NEW — module skeleton: `_run_vol(...)` async subprocess helper, `_normalize_and_store(...)` audit-blob writer, `vol_pslist(...)` first wrapper, `PslistEntry` + `PslistOutput` Pydantic models. Target ≤120 LOC after this story (room for ~280 LOC across the remaining 8 vol_* wrappers under the 400-LOC ceiling per CICD_SPEC §6.1).
- `src/silentwitness_mcp/tools/_vol_common.py` — NEW — shared constants (`VOL_BIN = Path("/opt/silentwitness/vol3-venv/bin/vol")`, default timeout 300s), `VolFailureReason` enum (`EVIDENCE_NOT_REGISTERED`, `EVIDENCE_TAMPERED`, `MOUNT_NOT_RO_NOEXEC_NOSUID`, `TOOL_FAILED`, `TOOL_TIMEOUT`, `OUTPUT_PARSE_FAILED`), `_VOL_CAVEATS` per-plugin caveat catalog (entries added per story). ~80 LOC.
- `src/silentwitness_mcp/server.py` — UPDATE — register `vol_pslist` with the FastMCP `Server` instance from story-fastmcp-server-bootstrap.
- `tests/unit/test_vol_pslist.py` — NEW — ≥7 behavioural test cases: (a) valid Vol3 JSON parses into `PslistOutput`, (b) empty `[]` returns `success=True` with empty list, (c) unregistered evidence path returns `success=False` reason `EVIDENCE_NOT_REGISTERED`, (d) SHA256 mismatch returns `success=False` reason `EVIDENCE_TAMPERED`, (e) Vol3 non-zero exit returns `success=False` reason `TOOL_FAILED` with first 500 chars of stderr captured in advisories, (f) timeout returns `success=False` reason `TOOL_TIMEOUT`, (g) malformed JSON output returns `success=False` reason `OUTPUT_PARSE_FAILED`. Subprocess mocked via `monkeypatch` on `asyncio.create_subprocess_exec`.
- `tests/integration/test_memory_e2e.py` — NEW — one e2e case `test_pslist_against_nist_image` invoking the real `/opt/silentwitness/vol3-venv/bin/vol` against `tests/fixtures/memory/nist-hacking-case.mem` (skipped via `pytest.mark.skipif` if fixture absent so CI on a fresh checkout does not red-bar before the fixture lands in Epic 14).

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a valid Windows memory image at /evidence/case-001/memdump.vmem
And   the image is registered in cases/case-001/evidence.json with a SHA256 matching its current content
And   /evidence/ is mounted ro,noexec,nosuid (mount validation passes)
When  the MCP tool vol_pslist is called with evidence_path="/evidence/case-001/memdump.vmem"
Then  the response is ResponseEnvelope with success=True
And   data is a PslistOutput containing a list[PslistEntry]
And   each PslistEntry has typed fields: pid: int, ppid: int, image_file_name: str, offset_v: int, threads: int, handles: int | None, session_id: int | None, wow64: bool, create_time: datetime | None, exit_time: datetime | None
And   one JSONL line is appended to cases/case-001/audit/memory.jsonl with audit_id matching format sift-<examiner>-<YYYYMMDD>-<NNN>
And   that JSONL line carries result_sha256 == SHA256 of the normalized full Vol3 stdout
And   the normalized stdout is persisted at cases/case-001/audit/blobs/<audit_id>.txt
And   data_provenance.cmd_argv == ["/opt/silentwitness/vol3-venv/bin/vol", "-f", "/evidence/case-001/memdump.vmem", "-r", "json", "windows.pslist.PsList"]
And   elapsed_ms is a positive float
And   caveats includes "windows.pslist walks PsActiveProcessHead — DKOM-hidden processes are invisible; corroborate with vol_psscan"
And   caveats includes "ImageFileName is truncated to 15 chars; use vol_cmdline or vol_dlllist for full paths"

Given the evidence path is not registered in cases/<case_id>/evidence.json
When  vol_pslist is called with that path
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_NOT_REGISTERED"
And   no Vol3 subprocess is spawned (verified by mocked spawn count == 0)
And   one JSONL line is still written to memory.jsonl recording the refusal (exit_code field omitted)

Given the registered evidence file's current SHA256 does not match the manifest entry (file modified post-registration)
When  vol_pslist is called
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_TAMPERED"
And   no Vol3 subprocess is spawned

Given /evidence/ is mounted without one of ro / noexec / nosuid
When  vol_pslist is called
Then  the response is ResponseEnvelope with success=False reason="MOUNT_NOT_RO_NOEXEC_NOSUID"
And   advisories includes the missing-flag list

Given Vol3 exits with a non-zero return code (e.g., wrong OS — Linux dump passed to a windows.* plugin)
When  vol_pslist is called against a valid registered path
Then  the response is ResponseEnvelope with success=False reason="TOOL_FAILED"
And   advisories[0] is the first 500 chars of stderr
And   the audit JSONL line records exit_code != 0 and elapsed_ms

Given Vol3 exceeds the 300s timeout
When  vol_pslist is called
Then  the subprocess is terminated (SIGKILL after SIGTERM grace)
And   the response is ResponseEnvelope with success=False reason="TOOL_TIMEOUT"

Given Vol3 emits stdout that is not valid JSON (renderer crash mid-stream)
When  vol_pslist is called
Then  the response is ResponseEnvelope with success=False reason="OUTPUT_PARSE_FAILED"
And   advisories includes the first 200 chars of the unparseable bytes
```

---

## Shell verification

```bash
uv run pytest tests/unit/test_vol_pslist.py -v
# Must show ≥7 passing test cases

uv run pytest tests/integration/test_memory_e2e.py::test_pslist_against_nist_image -v
# Must pass when the NIST memory fixture is present; SKIPPED otherwise (not red)

uv run ruff check src/silentwitness_mcp/tools/memory.py src/silentwitness_mcp/tools/_vol_common.py
uv run ruff format --check src/silentwitness_mcp/tools/memory.py src/silentwitness_mcp/tools/_vol_common.py
uv run mypy --strict src/silentwitness_mcp/tools/memory.py src/silentwitness_mcp/tools/_vol_common.py
# All three must exit 0

# File-size guard (CICD_SPEC §6.1)
wc -l src/silentwitness_mcp/tools/memory.py
# Must show ≤400

# Coverage floor for tools/ family per CICD_SPEC §6 (target 85% project, 90% per-tool)
uv run coverage run -m pytest tests/unit/test_vol_pslist.py
uv run coverage report --include="src/silentwitness_mcp/tools/memory.py,src/silentwitness_mcp/tools/_vol_common.py" --fail-under=85
# Must exit 0
```

---

## Notes for coding agent

- **Volatility 3 strategy:** SilentWitness uses its OWN venv at `/opt/silentwitness/vol3-venv/bin/vol` (pinned `volatility3==2.27.0`). Do NOT use SIFT-managed `/opt/volatility3/bin/vol` — SIFT pins no Vol3 version (`pip.installed: upgrade: True`), and the SIFT install may pull 2.28.0 which has open issue #1985 (layer-detection regression on large memory dumps). Pre-fetch Windows ISF bundle from `https://downloads.volatilityfoundation.org/volatility3/symbols/windows.zip` into `~/.cache/volatility3/` at init.
- **Vol3 JSON renderer.** Pass `-r json` — produces a single JSON document per plugin run (top-level array of row-objects with column names as keys). Do NOT parse the default pretty-printed text — that path is brittle across Vol3 releases (`context/domain/06` §"Output formats produced"). `-r jsonl` is also available (one row per line); for `pslist` the row count is bounded so single-document `json` is fine. Document the renderer choice in the module docstring.
- **Subprocess pattern.** `asyncio.create_subprocess_exec(*cmd_argv, stdout=PIPE, stderr=PIPE)` with `asyncio.wait_for(proc.communicate(), timeout=300)`. On `asyncio.TimeoutError`: `proc.terminate()`, then after a 5s grace `proc.kill()`, then return `TOOL_TIMEOUT`. Capture stderr first 500 chars for `TOOL_FAILED` advisory.
- **Audit blob storage.** Full normalized stdout is persisted at `cases/<case_id>/audit/blobs/<audit_id>.txt` per architecture §4.6. This is what the citation gate reads later — without this blob the verify chain breaks. SHA256 the normalized bytes (NOT raw — normalization stripped Vol3 banner + ANSI per story-output-normalizer) and store the hash in the audit JSONL.
- **Evidence-registry call ordering.** First action of `vol_pslist` is `evidence_registry.assert_registered(evidence_path)`. Architecture §4.10: refuse to operate on unregistered evidence. Second action: `evidence_registry.verify_hash(evidence_path)` to catch post-registration tampering. Third: `mount.assert_safe_options("/evidence")`. Only then spawn the subprocess.
- **Pydantic output model.** Define `PslistEntry` with the 11 documented columns from `context/domain/03` §7.2. Vol3 JSON keys are CamelCase (`PID`, `PPID`, `ImageFileName`, `Offset(V)`, `Threads`, `Handles`, `SessionId`, `Wow64`, `CreateTime`, `ExitTime`, `File output`); use Pydantic `Field(alias=...)` to map to snake_case Python names. `CreateTime`/`ExitTime` are ISO-8601 strings in the JSON renderer — parse to `datetime` with timezone awareness; `None` if Vol3 emits `"N/A"` or empty.
- **Caveats source.** Use the exact wording catalogued in `_VOL_CAVEATS["pslist"]`: `["windows.pslist walks PsActiveProcessHead — DKOM-hidden processes are invisible; corroborate with vol_psscan", "ImageFileName is truncated to 15 chars; use vol_cmdline or vol_dlllist for full paths", "ExitTime may be set for processes still referenced by other handles (orphan teardown)"]`. Source: `context/domain/03` §7.2 Gotchas. Append to `ResponseEnvelope.caveats` verbatim.
- **Plugin name string.** Vol3 v3.x plugin names are dotted: pass `windows.pslist.PsList` (the class form) — `windows.pslist` alone also works on current versions but the class-suffixed form is explicit and future-proof.
- **No shell interpolation.** Build `cmd_argv` as `list[str]` and pass to `create_subprocess_exec`. Never use `subprocess.run(..., shell=True)`. Architecture §2 trust boundary 2: "subprocesses are invoked with explicit argv (no shell interpolation)."
- **Skeleton helpers MUST be reusable.** `_run_vol(plugin_name: str, evidence_path: Path, extra_argv: list[str] | None, timeout_s: float, case_id: str) -> _VolResult` is the helper every subsequent vol_* story imports. `_VolResult` carries `exit_code`, `stdout_normalized`, `stderr`, `elapsed_ms`, `audit_id`, `stdout_path`, `result_sha256`. Get the signature right here — the next six stories depend on it.
- **LOC budget tracking.** After this story `tools/memory.py` should sit at ~120 LOC. Remaining six stories add ~280 LOC across 8 more wrappers (~35 LOC each). If approaching 400, the last story (`vol-lsadump`) splits the file by moving the 3 simplest wrappers into `tools/memory_extras.py`.
