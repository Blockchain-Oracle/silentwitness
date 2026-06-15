# Story — parse_prefetch tool wrapper (PECmd)

**ID:** story-parse-prefetch
**Epic:** Epic 6 — Tool wrappers: disk + registry (EZ Tools + RegRipper)
**Depends on:** story-parse-mft (owns the `tools/disk.py` skeleton + shared helpers)
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** SilentWitness investigator agent (or disk specialist subagent)
**I want to** call `parse_prefetch` against a registered Prefetch directory (or single `.pf` file) and receive a typed list of `PrefetchEntry` rows with executable name, run count, the last-8 run timestamps, and loaded files/directories
**So that** the demo's "did this binary actually execute, and when, and what did it touch?" corroboration question — the durable execution-confirmation artifact per encyclopedia §6 — is answerable with cited rows.

---

## File modification map

- `src/silentwitness_mcp/tools/disk.py` — UPDATE — append `PrefetchInput`, `PrefetchEntry`, `PrefetchOutput`, `parse_prefetch`. Reuse `_run_dotnet_ez_tool` + `_assert_registered_or_envelope` helpers. ~70 LOC added (running total for `disk.py` ~280 LOC; budget ≤400).
- `tests/unit/tools/test_disk_parse_prefetch.py` — NEW — ≥5 behavioral tests using `tests/fixtures/disk/prefetch_sample.csv`.
- `tests/fixtures/disk/prefetch_sample.csv` — NEW — small CSV mirroring PECmd output (≤12 rows; one with 8 distinct run timestamps for a Win10 row, one Win7-flavor with only LastRun populated, one with a long files-accessed list, one with Volume0Name+Volume1Name populated + Note flagging ">2 volumes").
- `tests/integration/tools/test_disk_parse_prefetch_integration.py` — NEW — skipif-guarded test invoking the real `dotnet /opt/zimmermantools/PECmd.dll` against a tiny `.pf` sample (skipped if PECmd missing — see Notes on installation).

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a registered Prefetch directory at /evidence/case-001/Prefetch/
And the evidence registry contains its directory SHA256 manifest entry
When parse_prefetch is called with PrefetchInput(evidence_path=Path(".../Prefetch/"), csv_out=Path(".../out/"))
Then ResponseEnvelope.success == True
And data is PrefetchOutput with entries: list[PrefetchEntry]
And every PrefetchEntry has ExecutableName: str, Hash: str, SourceFilename: str, RunCount: int, LastRun: datetime | None, PreviousRunTimes: list[datetime] (length 0..7 — Win10/11 stores last 8 total), Volume0Name: str | None, Volume0Serial: str | None, Volume0Created: datetime | None, Volume1Name: str | None, Volume1Serial: str | None, Volume1Created: datetime | None, Note: str | None, FilesLoaded: list[str], Directories: list[str], ParsingError: bool
And data_provenance.cmd_argv[0] == "dotnet"
And data_provenance.cmd_argv[1] == "/opt/zimmermantools/PECmd.dll"
And caveats includes "Prefetch confirms execution; Win10/11 records the last 8 run times per binary (Win7 records last 1) — read all eight, not just LastRun"
And caveats includes "Prefetch records files/DLLs loaded in the first ~10 seconds of execution only — later loads (e.g. side-loaded DLLs) do NOT appear"
And caveats includes "Up to 1024 .pf entries retained system-wide (historical cap); LRU eviction when full — absence is not proof of non-execution"
And caveats includes "Prefetcher is disabled by default on Windows Server — absence on a server host is uninformative; check HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management\\PrefetchParameters\\EnablePrefetcher first"
And corroboration includes hints pointing at parse_amcache, parse_shimcache, vol_pslist

Given an unregistered Prefetch path
When parse_prefetch is called
Then ResponseEnvelope.success == False
And advisories[0] contains "EVIDENCE_NOT_REGISTERED"
And no PECmd subprocess is spawned

Given the Prefetch directory contains 1025+ .pf entries (over the historical cap)
When parse_prefetch returns
Then data.entries length is exactly the parsed count
And advisories includes "Prefetch directory contains <N> entries; historical cap is 1024 — older entries may have been LRU-evicted"

Given PECmd is missing at /opt/zimmermantools/PECmd.dll
When parse_prefetch is called
Then ResponseEnvelope.success == False
And advisories[0] contains "PECMD_NOT_INSTALLED — run install.sh per context/.raw-design-research/03 to add PECmd to the EZ Tools tree"
And the audit log records the install-pointer reason

Given a Win10/11 .pf file with 8 distinct run timestamps
When parse_prefetch parses the row in tests/fixtures/disk/prefetch_sample.csv
Then PrefetchEntry.LastRun equals the most-recent of the 8
And PrefetchEntry.PreviousRunTimes has length 7
And the 7 entries are ordered most-recent-first

Given a Win7-flavor .pf file with only the most-recent run timestamp
When parse_prefetch parses the row
Then PrefetchEntry.LastRun is populated
And PrefetchEntry.PreviousRunTimes == []

Given a .pf file referencing 3 volumes (Volume0+Volume1+Volume2)
When parse_prefetch parses the row
Then PrefetchEntry.Volume0Name and PrefetchEntry.Volume1Name are populated from the first two
And PrefetchEntry.Note contains a ">2 volumes" flagging string preserving the truncated extras

Given a .pf file that PECmd flagged with ParsingError=True (corrupt header)
When parse_prefetch parses the row
Then PrefetchEntry.ParsingError == True
And advisories includes the executable name + the parsing-error count
```

---

## Shell verification

```bash
# Unit tests
uv run pytest tests/unit/tools/test_disk_parse_prefetch.py -v
# Must show ≥5 passing

# Integration (skipped if PECmd not installed)
uv run pytest tests/integration/tools/test_disk_parse_prefetch_integration.py -v

# Lint + format + types
uv run ruff check src/silentwitness_mcp/tools/disk.py tests/unit/tools/test_disk_parse_prefetch.py
uv run ruff format --check src/silentwitness_mcp/tools/disk.py
uv run mypy --strict src/silentwitness_mcp/tools/disk.py

# Aggregate LOC budget holds
wc -l src/silentwitness_mcp/tools/disk.py | awk '{ if ($1 > 400) exit 1 }'

# §14 clean
git diff main...HEAD -- 'src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec\|§14 carve-out"
```

---

## Notes for coding agent

- **PECmd is NOT pre-installed on stock SIFT 2026** (per `context/.raw-design-research/03` lines 130, 223, 257, 275 — verbatim: "EZ Tools NOT pre-installed: PECmd, SrumECmd, srum-dump — must add"). The `install.sh` script delivered by Epic 1 / Epic 12 must download PECmd via `https://download.ericzimmermanstools.com/net9/PECmd.zip` and unpack to the FLAT install path `/opt/zimmermantools/PECmd.dll` (NOT a nested `PECmd/` subdir — PECmd is a FLAT-install EZ Tool, see `_NESTED_TOOLS` rule in story-parse-mft). This story does NOT own that install step — but the `PECMD_NOT_INSTALLED` advisory must point the agent at `install.sh` so the failure mode is actionable.
- **Invocation pattern.** `dotnet /opt/zimmermantools/PECmd.dll --csv <out_dir> -d <prefetch_dir>` for batch (entire Prefetch folder) or `-f <pf_path>` for a single .pf. The `PrefetchInput.evidence_path` field can be a directory or a file — branch on `is_dir()`. CSV output uses `--csv <dir>`, glob `<timestamp>_PECmd_Output.csv`.
- **PECmd CSV columns to map** (per `context/domain/06` §5.5 lines 1275–1282 + encyclopedia §6 lines 440–446 + real PECmd headers): `Note`, `ParsingError`, `RunCount`, `LastRun` (NOT `LastRunTime`), `PreviousRun0`..`PreviousRun6`, `Volume0Name`, `Volume0Serial`, `Volume0Created`, `Volume1Name`, `Volume1Serial`, `Volume1Created` (hardcoded max-2 volume columns — NOT an open-ended list; if >2 volumes are referenced, surface the overflow via the `Note` column), `Directories` (NOT `DirectoriesLoaded`), `FilesLoaded`, `SourceFilename`, `SourceCreated`, `SourceModified`, `SourceAccessed`, `ExecutableName`, `Hash`, `Size`, `Version` (Prefetch format version 17/23/26/30/31).
- **Exit-code WARNING:** PECmd calls `Environment.Exit(0)` even on errors. Wrapper MUST parse stderr for Serilog `[ERR]` / `[FTL]` markers via regex `^\[\d{2}:\d{2}:\d{2} (ERR|FTL)\]`.
- **PreviousRun columns are 7 wide on Win10/11.** PECmd emits `PreviousRun0`..`PreviousRun6` for the last 7 prior runs (LastRun + 7 prior = 8 total). Parse all 7, drop empty cells, keep ordering. Win7 rows have all `PreviousRunN` empty.
- **Volume columns are hardcoded max-2.** PECmd's CSV schema surfaces `Volume0*` and `Volume1*` columns ONLY — there is no `Volume2Name`/etc. The Pydantic model exposes these as six explicit fields (`Volume0Name`/`Volume0Serial`/`Volume0Created`/`Volume1Name`/`Volume1Serial`/`Volume1Created`), NOT a `list[VolumeRef]`. If a .pf actually references >2 volumes, PECmd surfaces the overflow in the `Note` column — the wrapper surfaces it as the `Note: str | None` field so the agent can detect the truncation.
- **FilesLoaded + Directories are comma-or-pipe-separated lists inside one CSV cell.** PECmd uses `, ` as the separator. Split, strip, keep order; do NOT deduplicate (the order matters for the "first 10 seconds" forensic narrative). If the list is very long (>500 entries) truncate in the advisory but keep the full list in the stored blob.
- **Caveat strings — verbatim discipline.** The four caveats are the per-tool methodology notes that prevent overclaim. Use the strings above exactly. Vocab: "confirms execution" is allowed for Prefetch (it IS the execution-confirmation artifact per §6 line 480); other tools use "PRESENCE" / "inventoried" instead.
- **Hash on .pf filename.** PECmd surfaces the path-based hash from the .pf filename. Per encyclopedia §6 lines 491, 495–496: same name in two paths produces two .pf files. Surface the `Hash` field on the entry as-is — analysts cross-correlate this with `parse_mft` to see the actual file path.
- **LOC discipline.** Running total: ~280 LOC after this story. Leaves ~120 LOC headroom for parse_shellbags. Keep PrefetchEntry compact — push columns we don't structurally consume (e.g. SourceCreated/Modified/Accessed) into a single `_raw: dict[str, str]` field instead of separate Pydantic fields if needed.
- **Vocab discipline.** Caveats use "confirms execution" / "absence is not proof of non-execution" / "LRU eviction" — never "court-admissible," never "Ralph Wiggum."
