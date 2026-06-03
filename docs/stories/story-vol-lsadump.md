# Story — Vol3 windows.lsadump tool wrapper

**ID:** story-vol-lsadump
**Epic:** Epic 5 — Tool wrappers: memory (Volatility 3)
**Depends on:** story-vol-pslist (provides `_run_vol`, `_VolResult`, audit-blob writer), story-vol-dlllist-handles (closes the LOC budget on `tools/memory.py`)
**Estimate:** ~45min
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** wrap Volatility 3 `windows.lsadump` as a typed MCP tool that extracts decrypted LSA secrets (machine account hash, DefaultPassword auto-logon credentials, service-account passwords, DPAPI master keys) from the in-memory SYSTEM + SECURITY hives
**So that** the investigator agent can identify credential-material exposure for the IR scope-of-compromise question — "what credentials must we rotate?" (PRD FR #5; judging criteria: Breadth+Depth + IR Accuracy + Audit Trail Quality — credential findings are the highest-sensitivity claims in any IR report, so the audit trail bar is highest here).

---

## File modification map

- `src/silentwitness_mcp/tools/memory.py` — **DO NOT MODIFY in this story** unless the file-size guard already passes after the split below. The LOC counter from story-vol-dlllist-handles closes at ~380. Adding `vol_lsadump` here would push over 400.
- `src/silentwitness_mcp/tools/memory_extras.py` — NEW — house `vol_lsadump(...)` async function alone; add `LsaSecretEntry` + `LsaDumpOutput` Pydantic models; import `_run_vol`, `_VolResult`, `_VOL_CAVEATS` from `tools/memory.py` (or refactor those into `tools/_vol_common.py` if not already there — check first). Add `"lsadump"` entry to `_VOL_CAVEATS`. Target ≤80 LOC.
- `src/silentwitness_mcp/server.py` — UPDATE — register `vol_lsadump` (imported from `tools.memory_extras`) with FastMCP.
- `tests/unit/test_vol_lsadump.py` — NEW — ≥6 behavioural test cases: valid JSON parses for $MACHINE.ACC + DefaultPassword + _SC_<service> + DPAPI_SYSTEM secret names (mapped to the `Key` field), empty output (Credential-Guarded LSA partial protection), `Hex` / `Secret` field preserved verbatim, `EVIDENCE_NOT_REGISTERED`, `EVIDENCE_TAMPERED`, `TOOL_FAILED`.
- `tests/integration/test_memory_e2e.py` — UPDATE — add `test_lsadump_against_nist_image` (skipped if fixture absent).

**LOC-budget split rationale.** Architecture §4.2 budgets `tools/memory.py` at "comfortably under 400" but the 9 wrappers across 5 stories accumulate to ~410 LOC. Splitting only `vol_lsadump` (the most sensitive and least-shared-with-other-memory-tools wrapper) into `memory_extras.py` keeps both files comfortably under 400 and physically isolates the credential-material code path for easier review. The file-size guard (CICD_SPEC §6.1) is the forcing function — the split happens here because here is where the counter trips.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a valid Windows memory image at /evidence/case-001/memdump.vmem registered and SHA256-matched
When  vol_lsadump is called with evidence_path="/evidence/case-001/memdump.vmem"
Then  the response is ResponseEnvelope with success=True
And   data is an LsaDumpOutput containing list[LsaSecretEntry]
And   each LsaSecretEntry has typed fields: Key: str (the secret name, e.g., "$MACHINE.ACC" / "DefaultPassword" / "_SC_<service>" / "DPAPI_SYSTEM" / "NL$KM"), Hex: str (hex-encoded raw bytes), Secret: str | None (best-effort UTF-16LE decode if printable, else None)
And   cmd_argv == ["/opt/silentwitness/vol3-venv/bin/vol", "-f", "/evidence/case-001/memdump.vmem", "-r", "json", "windows.registry.lsadump.Lsadump"]
And   caveats includes "windows.lsadump decrypts LSA secrets using the SysKey from the SYSTEM hive — requires both SYSTEM and SECURITY hives present in memory (true by default on a running system)"
And   caveats includes "DefaultPassword may contain auto-logon plaintext credentials — sensitive material, treat as Restricted in the report and the HMAC ledger"
And   caveats includes "$MACHINE.ACC is the machine account password hash (NTLM) — usable for silver-ticket attacks; report as credential-rotation requirement"
And   caveats includes "_SC_<service> contains passwords for services configured with non-default credentials"
And   caveats includes "VBS / Credential Guard does NOT protect LSA secrets the same way it protects LSASS process memory — lsadump output is generally intact even on Credential Guard systems; do not assume empty output means the host is Credential-Guarded"
And   caveats includes "the Secret field is best-effort UTF-16LE decode — the authoritative bytes are in Hex; cite Hex when recording the observation"
And   the response is logged to cases/case-001/audit/memory.jsonl with the standard envelope
And   discipline_reminder is set to "credential material — record_observation against this output should be reviewed at Restricted classification and HMAC-approved before report inclusion"

Given the Vol3 JSON contains a secret with Key="DefaultPassword" and printable Unicode bytes
When  parsed
Then  LsaSecretEntry.Key == "DefaultPassword"
And   Hex contains the verbatim hex bytes
And   Secret contains the UTF-16LE decoded string (only if all decoded chars are in the printable range U+0020–U+007E or common Unicode letter blocks; else None)

Given vol_lsadump is called against an unregistered evidence path
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_NOT_REGISTERED"
And   no Vol3 subprocess is spawned (no credential material is ever touched)

Given the registered evidence's SHA256 mismatches the manifest
Then  the response is ResponseEnvelope with success=False reason="EVIDENCE_TAMPERED"

Given Vol3 exits non-zero
Then  the response is ResponseEnvelope with success=False reason="TOOL_FAILED"
And   advisories[0] is the first 500 chars of stderr

Given the file-size guard from CICD_SPEC §6.1 runs after this story merges
When  wc -l is invoked on both files
Then  src/silentwitness_mcp/tools/memory.py is ≤400 LOC
And   src/silentwitness_mcp/tools/memory_extras.py is ≤400 LOC
And   the pre-commit file-size-guard hook exits 0
```

---

## Shell verification

```bash
uv run pytest tests/unit/test_vol_lsadump.py -v
# Must show ≥6 passing test cases

uv run pytest tests/integration/test_memory_e2e.py::test_lsadump_against_nist_image -v
# Must pass when NIST fixture present; SKIPPED otherwise

uv run ruff check src/silentwitness_mcp/tools/memory.py src/silentwitness_mcp/tools/memory_extras.py
uv run mypy --strict src/silentwitness_mcp/tools/memory.py src/silentwitness_mcp/tools/memory_extras.py
# All exit 0

wc -l src/silentwitness_mcp/tools/memory.py src/silentwitness_mcp/tools/memory_extras.py
# Each must show ≤400

# Epic 5 close-out: full memory-tool test suite
uv run pytest tests/unit/test_vol_pslist.py tests/unit/test_vol_pstree.py tests/unit/test_vol_psscan.py tests/unit/test_vol_malfind.py tests/unit/test_vol_netscan.py tests/unit/test_vol_cmdline.py tests/unit/test_vol_dlllist.py tests/unit/test_vol_handles.py tests/unit/test_vol_lsadump.py -v
# Must show ≥45 passing test cases combined (sum of per-story minimums)

# Coverage floor for the tools/memory family per CICD_SPEC §6
uv run coverage run -m pytest tests/unit/test_vol_*.py
uv run coverage report --include="src/silentwitness_mcp/tools/memory.py,src/silentwitness_mcp/tools/memory_extras.py,src/silentwitness_mcp/tools/_vol_common.py" --fail-under=85
# Must exit 0
```

---

## Notes for coding agent

- **Volatility 3 strategy:** SilentWitness uses its OWN venv at `/opt/silentwitness/vol3-venv/bin/vol` (pinned `volatility3==2.27.0`). Do NOT use SIFT-managed `/opt/volatility3/bin/vol` — SIFT pins no Vol3 version (`pip.installed: upgrade: True`), and the SIFT install may pull 2.28.0 which has open issue #1985 (layer-detection regression on large memory dumps). Pre-fetch Windows ISF bundle from `https://downloads.volatilityfoundation.org/volatility3/symbols/windows.zip` into `~/.cache/volatility3/` at init.
- **CRITICAL: Plugin path migration.** As of Volatility 3 ≥2.29.0 (expected late 2026-06), `windows.lsadump.Lsadump` is removed — use `windows.registry.lsadump.Lsadump` exclusively. This story MUST use the new path or the wrapper will fail.
- **Output schema.** Per `context/domain/03` §7.30: Vol3 emits a row per LSA secret with `Name`, hex bytes, and a best-effort printable rendering. Capture both — the hex is authoritative, the printable is operational comfort.
- **Plugin name string.** `windows.registry.lsadump.Lsadump` — class-suffixed form (note the capital-L Lsadump, single-word). The old `windows.lsadump.Lsadump` path is removed in Vol3 ≥2.29.0.
- **Why this story splits the file.** Two reasons. (1) Strict LOC ceiling per CICD_SPEC §6.1 — `tools/memory.py` is at ~380 LOC after `vol-dlllist-handles`; adding lsadump pushes over. (2) Credential material is the highest-review-priority code path in the tool family — physically isolating it in `memory_extras.py` is good for reviewer attention.
- **Shared helpers location check.** Before adding the import in `memory_extras.py`, check whether `_run_vol`, `_VolResult`, and `_VOL_CAVEATS` already live in `tools/_vol_common.py` (per `story-vol-pslist` file map). If they do, both `memory.py` and `memory_extras.py` import from there. If they were inlined into `memory.py` instead, the lsadump story refactors them out — that refactor counts against this story's LOC budget but is necessary.
- **`discipline_reminder` is set for THIS tool ONLY.** Across all 9 vol_* wrappers, `vol_lsadump` is the only one whose response carries a non-empty `discipline_reminder`. The reminder seeds the model toward Restricted classification on the observation and triggers an examiner prompt at approval time (Epic 4 `approve_finding` flow). This is a load-bearing detail.
- **Credential-Guard caveat is the most important one.** `context/domain/03` §7.30: "VBS / Credential Guard does not protect LSA secrets the same way it protects LSASS." Many investigators assume empty `vol_lsadump` output means Credential Guard is enabled. That assumption is wrong and the caveat explicitly counters it.
- **No `hashdump` / `cachedump` in this story.** Per architecture §4.2 Epic 5 catalog: only `vol_lsadump` is listed. `windows.hashdump` and `windows.cachedump` are deferred to a future epic — do not over-extend.
- **Secret field decoding.** Best-effort UTF-16LE (LSA secrets are typically Unicode strings). If decoding produces bytes outside the printable range, set `Secret = None` and rely on `Hex`. Do NOT strip / sanitize — the entity gate compares against verbatim cited spans.
- **Sensitive output handling.** The full normalized stdout still goes to `cases/<case_id>/audit/blobs/<audit_id>.txt` per architecture §4.6 — the audit blob is what the citation gate verifies. The blob file is created with `0o600` mode (per atomic-io story / architecture §4.9 storage rules). Do NOT add a separate "redact secrets" pass — the audit boundary is the case directory, and the case directory is the examiner's.
