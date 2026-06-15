# Story — parse_mft tool wrapper (MFTECmd)

**ID:** story-parse-mft
**Epic:** Epic 6 — Tool wrappers: disk + registry (EZ Tools + RegRipper)
**Depends on:** story-response-envelope, story-evidence-registry, story-audit-logger, story-fastmcp-server-bootstrap
**Estimate:** ~45 min
**Status:** PENDING

---

## User story

**As a** SilentWitness investigator agent (or any MCP client)
**I want to** call `parse_mft` with a registered `$MFT` evidence path and receive a typed list of `MFTEntry` rows with both $STANDARD_INFORMATION and $FILE_NAME timestamps
**So that** downstream disk-corroboration steps (e.g. confirming the Ethereal install at `C:\Program Files\Ethereal\` via MFT record dated 2004-08-19 22:48 UTC for the demo) and timestomp-detection (SI vs FN divergence per `context/domain/02` §1) are answerable with verifiable, cited rows — never a hallucinated path.

---

## File modification map

- `src/silentwitness_mcp/tools/disk.py` — NEW (skeleton — blocks the other 4 disk stories) — module docstring citing `architecture.md` §4.2 row 10 + `context/.raw-design-research/03` §EZ Tools + `context/domain/02` §1; shared helpers `_run_dotnet_ez_tool(dll_path, argv) -> CompletedProcess` (constructs FLAT-vs-nested DLL paths via the `_NESTED_TOOLS` constant in `_disk_common.py` / `_log_common.py` — FLAT is the default for AmcacheParser/AppCompatCacheParser/MFTECmd/PECmd/SBECmd at `/opt/zimmermantools/<Tool>.dll`; nested tools are `_NESTED_TOOLS: set[str] = {"RECmd", "SQLECmd", "iisGeolocate", "EvtxECmd"}` which sit at `/opt/zimmermantools/<Tool>/<Tool>.dll`), `_read_csv(path) -> list[dict]`, `_assert_registered_or_envelope(evidence_path, examiner) -> ToolResponse | None`; Pydantic input `MftInput(evidence_path: Path, csv_out: Path)`; Pydantic output `MFTEntry` (EntryNumber: int, SequenceNumber: int, ParentPath: str, FileName: str, Extension: str | None, FileSize: int, IsDirectory: bool, InUse: bool, HasAds: bool, Created0x10: datetime | None, LastModified0x10: datetime | None, LastRecordChange0x10: datetime | None, LastAccess0x10: datetime | None, Created0x30: datetime | None, LastModified0x30: datetime | None, LastRecordChange0x30: datetime | None, LastAccess0x30: datetime | None, Timestomped: bool, uSecZeros: bool) — `IsDeleted` is server-side-derived from `not InUse` (NOT a real column); `SiFnDelta` is a wrapper-computed derived alias for `Timestomped` retained for backward-compat reading callers — see field comment in the Pydantic model. Wrapper `MftOutput(entries: list[MFTEntry], row_count: int, truncated: bool)`; `parse_mft(input: MftInput) -> ToolResponse[MftOutput]` (~80 LOC for this story; the 5-tool aggregate budget for `disk.py` is ≤400 LOC).
- `tests/unit/tools/test_disk_parse_mft.py` — NEW — ≥5 behavioral tests using a hand-crafted MFTECmd CSV fixture under `tests/fixtures/disk/mft_sample.csv` (Ethereal-shaped row + a timestomp-shaped row with SI ≠ FN + a deleted directory row).
- `tests/fixtures/disk/mft_sample.csv` — NEW — small CSV (≤15 rows) mirroring real MFTECmd output columns.
- `tests/fixtures/disk/mft_truncated.csv` — NEW — CSV cut mid-row (simulates aborted MFTECmd run).
- `tests/integration/tools/test_disk_parse_mft_integration.py` — NEW — single end-to-end test that invokes the real `dotnet /opt/zimmermantools/MFTECmd.dll --csv …` path against a tiny synthetic $MFT (skipped via `pytest.mark.skipif(not Path('/opt/zimmermantools/MFTECmd.dll').exists())` so CI on non-SIFT runners still passes).

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a registered NTFS MFT file at /evidence/case-001/$MFT
And the evidence registry contains its SHA256 entry
When parse_mft is called with MftInput(evidence_path=Path("/evidence/case-001/$MFT"), csv_out=Path("/tmp/mft_out.csv"))
Then ResponseEnvelope.success == True
And data is MftOutput with entries: list[MFTEntry] where every row has both Created0x10 and Created0x30 populated when present in source CSV
And every MFTEntry has EntryNumber: int and SequenceNumber: int (the two real MFTECmd columns) and InUse: bool (server-side-derived IsDeleted == not InUse) and Timestomped: bool + uSecZeros: bool (the REAL MFTECmd columns) — SiFnDelta is a wrapper-computed derived alias for Timestomped only
And data_provenance.tool == "parse_mft"
And data_provenance.cmd_argv[0] == "dotnet"
And data_provenance.cmd_argv[1] == "/opt/zimmermantools/MFTECmd.dll"
And data_provenance.result_sha256 is a 64-hex-character string
And data_provenance.stdout_path points to a file under cases/<case_id>/audit/blobs/
And caveats includes "FN ($30) timestamps update only on rename/move; SI ($10) updates on most file ops — SI/FN divergence on a single record is a classic timestomping indicator"
And corroboration includes a hint pointing at parse_amcache and parse_prefetch for execution corroboration

Given an unregistered MFT path /evidence/case-001/MFT_HALLUCINATED
When parse_mft is called
Then ResponseEnvelope.success == False
And ResponseEnvelope.advisories[0] contains "EVIDENCE_NOT_REGISTERED"
And no MFTECmd subprocess is spawned (mock asserts subprocess.run not called)
And no audit JSONL line is written for a successful invocation

Given the input CSV is truncated mid-row (MFTECmd was killed)
When parse_mft parses tests/fixtures/disk/mft_truncated.csv
Then ResponseEnvelope.success == True
And data.truncated == True
And advisories includes a "partial parse: <N> rows recovered before truncation" entry with N matching the count of fully-parsed rows
And the audit log records the truncation marker

Given an MFT row where Created0x10 differs from Created0x30 by more than 1 second
When parse_mft normalizes the row into MFTEntry
Then Timestomped is True for that entry (and the SiFnDelta derived alias is also True)
And caveats includes the timestomping note above

Given a registered MFT path but /evidence/ is mounted without ro,noexec,nosuid
When parse_mft is called
Then ResponseEnvelope.success == False
And ResponseEnvelope.advisories[0] contains "MOUNT_NOT_RO_NOEXEC_NOSUID"

Given the dotnet binary is missing at /usr/bin/dotnet
When parse_mft is called
Then ResponseEnvelope.success == False
And ResponseEnvelope.advisories[0] contains "DOTNET_NOT_FOUND"
And the error reason points the agent at `install.sh` for SIFT bootstrap

Given a tampered MFT (registered SHA256 no longer matches the file on disk)
When parse_mft is called
Then ResponseEnvelope.success == False
And ResponseEnvelope.advisories[0] contains "EVIDENCE_HASH_MISMATCH"
```

---

## Shell verification

```bash
# Unit + property tests pass
uv run pytest tests/unit/tools/test_disk_parse_mft.py -v
# Must show ≥5 passing

# Integration test skipped on non-SIFT, runs green on SIFT
uv run pytest tests/integration/tools/test_disk_parse_mft_integration.py -v

# Lint + format + strict types
uv run ruff check src/silentwitness_mcp/tools/disk.py tests/unit/tools/test_disk_parse_mft.py
uv run ruff format --check src/silentwitness_mcp/tools/disk.py
uv run mypy --strict src/silentwitness_mcp/tools/disk.py

# Aggregate LOC budget across all 5 disk tools holds (≤400)
wc -l src/silentwitness_mcp/tools/disk.py | awk '{ if ($1 > 400) exit 1 }'

# §14 no-mocks/no-fakes inside src/ (fixtures live in tests/)
git diff main...HEAD -- 'src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec\|§14 carve-out"
# Must output nothing
```

---

## Notes for coding agent

- **EZ Tools invocation pattern (verified — `context/.raw-design-research/03` §EZ Tools, lines 109–128).** Always shell `dotnet /opt/zimmermantools/MFTECmd.dll --csv <out_dir> -f <mft_path>` — note MFTECmd is a **FLAT-install** EZ Tool (DLL sits directly under `/opt/zimmermantools/`, NOT in a nested `MFTECmd/` subdir). FLAT-vs-nested rule: the constant `_NESTED_TOOLS: set[str] = {"RECmd", "SQLECmd", "iisGeolocate", "EvtxECmd"}` lives in `_disk_common.py` / `_log_common.py`; `_run_dotnet_ez_tool` uses it to construct the right path (FLAT for MFTECmd/AmcacheParser/AppCompatCacheParser/PECmd/SBECmd; nested for the four exceptions). The wrapper at `/usr/local/bin/MFTECmd` exists but call `dotnet` directly so `cmd_argv` is deterministic for the audit log and survives wrapper-script churn. The dotnet 9 SDK lives at `/usr/bin/dotnet`.
- **MFTECmd exit-code reality:** MFTECmd is the ONE EZ Tool whose exit code IS reliable (`Environment.Exit(-1)` on error). Unlike the other EZ Tools, we can trust `exit_code != 0` for fatal-error detection.
- **MFTECmd output is CSV, not stdout.** MFTECmd writes the CSV to `--csv <dir>` (it picks the filename, e.g. `<timestamp>_MFTECmd_$MFT_Output.csv`). After spawn, glob `<csv_out>/*_MFTECmd_*Output.csv`, read the most recent, then normalize + hash + store at `cases/<case_id>/audit/blobs/<audit_id>.txt`. Do NOT rely on stdout for the structured data — MFTECmd prints only progress to stdout.
- **MFTECmd CSV columns to map** (per `context/domain/06` §5.1 + real MFTECmd headers): `EntryNumber`, `SequenceNumber`, `InUse`, `ParentEntryNumber`, `ParentSequenceNumber`, `ParentPath`, `FileName`, `Extension`, `FileSize`, `IsDirectory`, `HasAds`, `Created0x10`, `Created0x30`, `LastModified0x10`, `LastModified0x30`, `LastRecordChange0x10`, `LastRecordChange0x30`, `LastAccess0x10`, `LastAccess0x30`, `Timestomped`, `uSecZeros`. `IsDeleted` is server-side-derived from `not InUse` (NOT a real column — never look for an `IsDeleted` header). `SiFnDelta` is a wrapper-computed derived alias for `Timestomped` (kept for backward-compat reading callers).
- **SI/FN divergence semantics** (per `context/domain/02` §1 + `context/domain/06` §5.1 line 833). $FILE_NAME ($30) only updates at file rename/move; $STANDARD_INFORMATION ($10) updates on most file operations. A record where $10 timestamps precede $30 timestamps is the classic timestomp signature. The `Timestomped` boolean on MFTEntry (sourced from MFTECmd's column directly) exposes this without forcing the agent to compute it; `SiFnDelta` is retained as a wrapper-side derived alias of `Timestomped` for backward-compat readers. The companion `uSecZeros` flag (zero microseconds across timestamps — common timestomp byproduct) is surfaced as its own boolean column.
- **Caveat text — verbatim discipline** (per architecture §4.3): the caveat string must be the timestomp note above, not paraphrased. Caveats are user-visible in the report's Appendix-Audit.
- **Evidence-registry first.** The first line of `parse_mft` is `await evidence_registry.assert_registered(input.evidence_path, examiner=ctx.examiner)`. If it raises `EvidenceNotRegistered`, return `ToolResponse(success=False, advisories=["EVIDENCE_NOT_REGISTERED: <path>"], …)`. Do NOT spawn the dotnet subprocess. Same for `MOUNT_NOT_RO_NOEXEC_NOSUID` (mount check) and `EVIDENCE_HASH_MISMATCH` (re-hash check at call time).
- **Truncation detection.** Parse the CSV with `csv.DictReader`. Wrap the row iterator in a try/except. On `csv.Error` or short-row exception, count the rows parsed so far, set `MftOutput.truncated=True`, append the advisory, and return success=True. This is partial-success — the agent should still be able to cite the rows that did parse.
- **MFT entries are large** ($MFT for a 500GB volume → ~1 GB CSV → millions of rows). The MVP returns ALL rows; do not paginate at this layer. Defer truncation/filtering to a future story. The advisory budget covers row-count warnings ("output is 1.2M rows; consider narrower query via downstream pivots").
- **Banner stripping.** MFTECmd emits a version banner on stdout but the CSV is clean. Run the normalizer (`verification/normalizer.py`) on the CSV before SHA256 hashing per architecture §4.6 — even though MFTECmd's CSV is timestamp-stable, the normalizer pipeline must be invoked uniformly so the citation gate's reproducibility holds.
- **`disk.py` LOC discipline.** This story owns the skeleton + parse_mft (~80 LOC). The 4 sibling stories (`parse_amcache`, `parse_shimcache`, `parse_prefetch`, `parse_shellbags`) each add ~50–70 LOC. Aggregate cap ≤400 LOC per architecture §4.2. If your draft pushes past ~95 LOC for this story alone, factor more aggressively into the shared `_run_dotnet_ez_tool` helper.
- **Vocab discipline** (per PRD §14 / architecture §6 line 497): never "court-admissible" in any caveat or docstring; never describe the timestomp note as "proof" — describe it as "indicator." Never use "Ralph Wiggum" in either code or comments.
