# Story — parse_amcache + parse_shimcache tool wrappers (AmcacheParser + AppCompatCacheParser)

**ID:** story-parse-amcache-shimcache
**Epic:** Epic 6 — Tool wrappers: disk + registry (EZ Tools + RegRipper)
**Depends on:** story-parse-mft (owns the `tools/disk.py` skeleton + shared helpers)
**Estimate:** ~1.5h (two tools in one file, shared CSV + dotnet plumbing)
**Status:** PENDING

---

## User story

**As a** SilentWitness investigator agent (or disk specialist subagent)
**I want to** call `parse_amcache` and `parse_shimcache` against registered Amcache.hve and SYSTEM hive evidence and receive typed lists of program-execution-or-presence rows
**So that** the "did binary X exist / run on this host?" question — central to Hour 6–14 of any IR engagement per the encyclopedia's §7 + §8 — is answerable with cited rows, including the per-tool methodology caveats that distinguish "ShimCache means evaluated for shim" from "Amcache means inventoried" from "Prefetch means executed."

---

## File modification map

- `src/silentwitness_mcp/tools/disk.py` — UPDATE — append `AmcacheInput`, `AmcacheEntry`, `AmcacheOutput`, `parse_amcache`; `ShimcacheInput`, `ShimcacheEntry`, `ShimcacheOutput`, `parse_shimcache`. Reuse `_run_dotnet_ez_tool` + `_assert_registered_or_envelope` helpers from story-parse-mft. Aggregate addition ~130 LOC across both tools (running total for `disk.py` ~210 LOC; budget ≤400).
- `tests/unit/tools/test_disk_parse_amcache.py` — NEW — ≥5 behavioral tests using `tests/fixtures/disk/amcache_sample.csv`.
- `tests/unit/tools/test_disk_parse_shimcache.py` — NEW — ≥5 behavioral tests using `tests/fixtures/disk/shimcache_sample.csv`.
- `tests/fixtures/disk/amcache_sample.csv` — NEW — small CSV mirroring AmcacheParser output (≤15 rows; one Ethereal-shaped, one with empty SHA1, one publisher-unknown row).
- `tests/fixtures/disk/shimcache_sample.csv` — NEW — small CSV mirroring AppCompatCacheParser output (≤15 rows; ordered by CacheEntryPosition 0..N; one with `Executed="Yes"` for Win7-flavor, one `Executed="NA"` for Win10).
- `tests/integration/tools/test_disk_amcache_shimcache_integration.py` — NEW — two skipif-guarded tests invoking the real `dotnet /opt/zimmermantools/AmcacheParser.dll` and `dotnet /opt/zimmermantools/AppCompatCacheParser.dll` against tiny hive samples.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

### parse_amcache

```
Given a registered Amcache.hve at /evidence/case-001/Amcache.hve
And the evidence registry contains its SHA256
When parse_amcache is called with AmcacheInput(evidence_path=…, csv_out=…)
Then ResponseEnvelope.success == True
And data is AmcacheOutput with entries: list[AmcacheEntry]
And every AmcacheEntry has SHA1: str | None, FullPath: str, Size: int | None, Publisher: str | None, ProductName: str | None, ProductVersion: str | None, FileKeyLastWriteTimestamp: datetime
And data_provenance.cmd_argv[1] == "/opt/zimmermantools/AmcacheParser.dll"
And caveats includes "Amcache proves file PRESENCE / inventory by the Compatibility Telemetry service, never execution. Corroborate with Prefetch or Sysmon EID 1 for execution proof."
And caveats includes "Amcache stores SHA-1, not SHA-256 — translate via VirusTotal or recompute if the binary is still on disk for modern-IOC comparison"
And corroboration includes hints pointing at parse_prefetch + parse_shimcache + vol_pslist

Given an unregistered Amcache path
When parse_amcache is called
Then ResponseEnvelope.success == False
And advisories[0] contains "EVIDENCE_NOT_REGISTERED"
And no AmcacheParser subprocess is spawned

Given an Amcache.hve that is a valid registry hive but contains no InventoryApplicationFile subkeys (empty / fresh install)
When parse_amcache is called
Then ResponseEnvelope.success == True
And data.entries == []
And advisories includes "no InventoryApplicationFile entries — confirm Appraiser scheduled task has run on this host"

Given an Amcache.hve registered but the file on disk has been replaced (tampering)
When parse_amcache is called
Then ResponseEnvelope.success == False
And advisories[0] contains "EVIDENCE_HASH_MISMATCH"
```

### parse_shimcache

```
Given a registered SYSTEM hive at /evidence/case-001/SYSTEM
And the evidence registry contains its SHA256
When parse_shimcache is called with ShimcacheInput(evidence_path=…, csv_out=…)
Then ResponseEnvelope.success == True
And data is ShimcacheOutput with entries: list[ShimcacheEntry]
And every ShimcacheEntry has CacheEntryPosition: int, Path: str, LastModifiedTimeUTC: datetime | None, Executed: Literal["Yes", "No", "NA"], ControlSet: int
And entries are ordered by CacheEntryPosition ascending (CacheEntryPosition 0 == most-recent)
And data_provenance.cmd_argv[1] == "/opt/zimmermantools/AppCompatCacheParser.dll"
And caveats includes "ShimCache records files the AppCompat layer evaluated for shimming — it may include programs that were prompted for compatibility shimming but never actually ran. ShimCache proves PRESENCE / shim-evaluation, not execution."
And caveats includes "ShimCache LastModifiedUTC is the file's $SI Modified time at evaluation, NOT the time the binary ran"
And caveats includes "ShimCache flushes to the SYSTEM hive only on clean shutdown — a hive captured live may be stale"
And corroboration includes hints pointing at vol_shimcachemem (memory ShimCache via Volatility), parse_amcache, parse_prefetch

Given a SYSTEM hive registered but it is not a valid registry hive (truncated)
When parse_shimcache is called
Then ResponseEnvelope.success == False
And advisories[0] contains "PARSE_FAILED" with the AppCompatCacheParser stderr substring captured

Given the SYSTEM hive on a Win7 build where ShimCache entries carry the Executed flag
When parse_shimcache parses tests/fixtures/disk/shimcache_sample.csv
Then at least one ShimcacheEntry has Executed == "Yes"
And at least one ShimcacheEntry has Executed == "NA" (Win10/11 rows in the same fixture do not carry the flag)
```

---

## Shell verification

```bash
# Unit tests pass for both tools
uv run pytest tests/unit/tools/test_disk_parse_amcache.py tests/unit/tools/test_disk_parse_shimcache.py -v
# Must show ≥10 passing (≥5 per tool)

# Integration tests skipped on non-SIFT, green on SIFT
uv run pytest tests/integration/tools/test_disk_amcache_shimcache_integration.py -v

# Lint + format + types
uv run ruff check src/silentwitness_mcp/tools/disk.py tests/unit/tools/test_disk_parse_amcache.py tests/unit/tools/test_disk_parse_shimcache.py
uv run ruff format --check src/silentwitness_mcp/tools/disk.py
uv run mypy --strict src/silentwitness_mcp/tools/disk.py

# Aggregate LOC budget holds
wc -l src/silentwitness_mcp/tools/disk.py | awk '{ if ($1 > 400) exit 1 }'

# §14 clean
git diff main...HEAD -- 'src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec\|§14 carve-out"
```

---

## Notes for coding agent

- **EZ Tools paths (verified — `context/.raw-design-research/03` lines 112–113).** AmcacheParser at `/opt/zimmermantools/AmcacheParser.dll` (FLAT install); AppCompatCacheParser at `/opt/zimmermantools/AppCompatCacheParser.dll` (FLAT install). Both invoked via `dotnet /opt/zimmermantools/<Tool>.dll --csv <out_dir> -f <hive_path>`. Reuse `_run_dotnet_ez_tool` from story-parse-mft (which knows the FLAT-vs-nested rule via `_NESTED_TOOLS`).
- **AmcacheParser emits MULTIPLE CSVs.** Per real-tool behavior, a single AmcacheParser run produces multiple `<timestamp>_Amcache_*.csv` files: `_UnassociatedFileEntries.csv`, `_AssociatedFileEntries.csv`, `_ProgramEntries.csv`, `_DeviceContainers.csv`, etc. The wrapper consumes the `UnassociatedFileEntries` table for this story — glob `<csv_out>/**/*_UnassociatedFileEntries.csv` (recursive glob — AmcacheParser may nest by hostname) and read the most-recent match. Document the multi-file output strategy in the file-modification-map note so callers can target sibling tables in future stories.
- **CSV output discovery, not stdout.** Same pattern as MFTECmd: pass `--csv <dir>`, glob the output filenames per table (AmcacheParser → multiple `<timestamp>_Amcache_<Table>.csv` files; AppCompatCacheParser → single `<timestamp>_AppCompatCache_<hostname>_<controlSet>.csv`), read with `csv.DictReader`. Stdout is for progress only.
- **Amcache CSV columns to map (UnassociatedFileEntries table)** (per `context/domain/06` §5.3 + `context/domain/02` §8 + real AmcacheParser headers): `SHA1`, `FullPath`, `FileExtension`, `Size` (NOT `FileSize`), `ProductName`, `ProductVersion`, `Publisher`, `BinFileVersion`, `BinProductVersion`, `FileKeyLastWriteTimestamp` (NOT `KeyLastWriteTimestamp`). SHA1 may be empty for non-PE entries; treat as `None`. Run `AmcacheParser` with `-i` flag if `architecture.md` test fixture needs `InventoryApplicationFile` rows (optional — default is enough for MVP).
- **Shimcache CSV columns to map** (per `context/domain/06` §5.4 + `context/domain/02` §7 + real AppCompatCacheParser headers): `ControlSet`, `CacheEntryPosition`, `Path`, `LastModifiedTimeUTC`, `Executed`. `Executed` is a tri-state STRING column (`Literal["Yes", "No", "NA"]`) — NOT a `bool`. Win10+ rows have `Executed == "NA"`; Win7 rows carry `"Yes"` or `"No"`. There is NO `FileSize` column — drop it. Multiple ControlSets (001, 002) produce duplicate paths across ControlSets — preserve both; the agent uses ControlSet to choose recent vs prior boot state.
- **Exit-code WARNING:** Both AmcacheParser AND AppCompatCacheParser call `Environment.Exit(0)` even on errors. Wrapper MUST parse stderr for Serilog `[ERR]` / `[FTL]` markers via regex `^\[\d{2}:\d{2}:\d{2} (ERR|FTL)\]` — exit code alone misses failures.
- **Caveats are the wedge.** ShimCache + Amcache caveats are the per-tool methodology notes that prevent the model from overclaiming. The Amcache "PRESENCE not execution" caveat is verbatim from the encyclopedia §8 line 689. The ShimCache "evaluated for shimming, may not have run" caveat is verbatim from §7 lines 544–550. These strings appear in the report's Appendix-Audit — the citation gate cannot fix a misinterpretation of a row, but the caveat prevents it being written in the first place.
- **`Executed` semantics.** Per `context/domain/02` §7 lines 540–550: Win7 ShimCache carries an "Executed" flag (parser surfaces it as `"Yes"`/`"No"`); Win8/10/11 do NOT — so `Executed == "NA"` (tri-state string Literal, NOT a `bool`). Tests must include both shapes.
- **AmcacheParser `-i` flag.** Per `context/domain/06` line 1255, `-i` includes `InventoryApplicationFile` (full driver/program list). MVP runs without `-i` (faster, smaller); add as an optional `AmcacheInput.include_inventory: bool = False` field for downstream stories — do NOT scope-creep into v1.
- **ControlSet selection for ShimCache.** AppCompatCacheParser supports `-c <controlSet>` for a specific control set. Default behavior reads all ControlSets present; MVP keeps default and returns all rows tagged with their `ControlSet` integer. A downstream story can add `ShimcacheInput.control_set: int | None` to filter.
- **LOC discipline.** Running total after this story: `disk.py` ~210 LOC. Stories `parse-prefetch` + `parse-shellbags` add ~70 + ~65 LOC → final ~345 LOC; comfortably under 400.
- **Vocab discipline.** Caveats must use "PRESENCE" / "evaluated for shimming" / "inventoried" — not "proof," not "evidence of execution," not "court-admissible."
