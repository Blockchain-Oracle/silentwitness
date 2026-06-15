# Story — parse_shellbags tool wrapper (SBECmd)

**ID:** story-parse-shellbags
**Epic:** Epic 6 — Tool wrappers: disk + registry (EZ Tools + RegRipper)
**Depends on:** story-parse-mft (owns the `tools/disk.py` skeleton + shared helpers)
**Estimate:** ~45 min
**Status:** PENDING

---

## User story

**As a** SilentWitness investigator agent (or disk specialist subagent)
**I want to** call `parse_shellbags` against a registered NTUSER.DAT or UsrClass.dat hive (or a directory containing both) and receive a typed list of `ShellbagEntry` rows recording every folder Explorer rendered — including external drives, network shares, and deleted folders
**So that** the "where did the user browse?" question — central to insider-threat, USB-exfil, and lateral-movement investigations per encyclopedia §23 — is answerable with cited rows.

---

## File modification map

- `src/silentwitness_mcp/tools/disk.py` — UPDATE — append `ShellbagsInput`, `ShellbagEntry`, `ShellbagsOutput`, `parse_shellbags`. Reuse shared helpers. ~65 LOC added (running total for `disk.py` ~345 LOC; budget ≤400).
- `tests/unit/tools/test_disk_parse_shellbags.py` — NEW — ≥5 behavioral tests using `tests/fixtures/disk/shellbags_sample.csv`.
- `tests/fixtures/disk/shellbags_sample.csv` — NEW — small CSV mirroring SBECmd output (≤15 rows; one local-folder row, one external-drive row with VolumeSerial, one network-share row with `\\server\share` AbsolutePath, one deleted-folder row).
- `tests/integration/tools/test_disk_parse_shellbags_integration.py` — NEW — skipif-guarded test invoking `dotnet /opt/zimmermantools/SBECmd.dll` against a tiny UsrClass.dat sample.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a registered hive directory at /evidence/case-001/hives/ containing NTUSER.DAT + UsrClass.dat
And the evidence registry contains SHA256 entries for both files
When parse_shellbags is called with ShellbagsInput(evidence_path=Path(".../hives/"), csv_out=Path(".../out/"))
Then ResponseEnvelope.success == True
And data is ShellbagsOutput with entries: list[ShellbagEntry]
And every ShellbagEntry has BagPath: str, Slot: int, NodeSlot: int, MRUPosition: int | None, AbsolutePath: str, ShellType: str, Value: str, ChildBags: int, FirstInteracted: datetime | None, LastInteracted: datetime | None, LastWriteTime: datetime, MFTEntry: int | None, MFTSequenceNumber: int | None, IconReference: str | None
And data_provenance.cmd_argv[1] == "/opt/zimmermantools/SBECmd.dll"
And caveats includes "ShellBags persist folder navigation including deleted, external, and network locations — a path in ShellBags does not require the folder to exist now"
And caveats includes "ShellBag entries are created by Explorer rendering — cmd.exe / PowerShell / Get-ChildItem activity does NOT produce ShellBags"
And caveats includes "ShellBag LastInteracted reflects when the user last opened the folder in Explorer; absence of LastInteracted on Win10+ rows is common and not an error"
And caveats includes "Roaming profiles can sync ShellBags between hosts — a ShellBag does not prove the browse happened on THIS machine"
And corroboration includes hints pointing at parse_mft (for the same path's MFT record), parse_amcache, and regripper plugin "usbstor" for external-drive cross-reference

Given a registered single hive file UsrClass.dat (not a directory)
When parse_shellbags is called with ShellbagsInput(evidence_path=Path(".../UsrClass.dat"), …)
Then ResponseEnvelope.success == True
And entries are populated from the single hive

Given an unregistered hive path
When parse_shellbags is called
Then ResponseEnvelope.success == False
And advisories[0] contains "EVIDENCE_NOT_REGISTERED"
And no SBECmd subprocess is spawned

Given the hive directory contains NTUSER.DAT only (no UsrClass.dat)
When parse_shellbags is called on a Win10+ system
Then ResponseEnvelope.success == True
And advisories includes "UsrClass.dat absent — Win10+ stores the bulk of ShellBags in UsrClass.dat; results from NTUSER.DAT alone will be sparse"
And entries may be empty without that being a parse failure

Given a hive registered but the file on disk has been replaced (tampering)
When parse_shellbags is called
Then ResponseEnvelope.success == False
And advisories[0] contains "EVIDENCE_HASH_MISMATCH"

Given a ShellBag row referencing an external USB volume with VolumeSerial populated
When parse_shellbags parses tests/fixtures/disk/shellbags_sample.csv
Then the ShellbagEntry.AbsolutePath contains the drive letter at parse time
And the ShellbagEntry.Value contains the volume label or serial
And corroboration advises cross-referencing with regripper plugin "mountdev"
```

---

## Shell verification

```bash
# Unit tests
uv run pytest tests/unit/tools/test_disk_parse_shellbags.py -v
# Must show ≥5 passing

# Integration (skipped on non-SIFT)
uv run pytest tests/integration/tools/test_disk_parse_shellbags_integration.py -v

# Lint + format + types
uv run ruff check src/silentwitness_mcp/tools/disk.py tests/unit/tools/test_disk_parse_shellbags.py
uv run ruff format --check src/silentwitness_mcp/tools/disk.py
uv run mypy --strict src/silentwitness_mcp/tools/disk.py

# Aggregate LOC budget holds (final)
wc -l src/silentwitness_mcp/tools/disk.py | awk '{ if ($1 > 400) exit 1 }'

# §14 clean
git diff main...HEAD -- 'src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec\|§14 carve-out"
```

---

## Notes for coding agent

- **EZ Tools path (verified — `context/.raw-design-research/03` line 124).** `dotnet /opt/zimmermantools/SBECmd.dll --csv <out_dir> -d <hive_dir>` for batch (recommended — picks up NTUSER.DAT + UsrClass.dat together) or `-f <hive_path>` for a single hive. SBECmd is a FLAT-install EZ Tool (DLL sits directly under `/opt/zimmermantools/`, NOT in a nested subdir — see `_NESTED_TOOLS` rule in story-parse-mft). Default to `-d` when the input is a directory; fall back to `-f` when it's a file.
- **Exit-code WARNING:** SBECmd calls `Environment.Exit(0)` even on errors. Wrapper MUST parse stderr for Serilog `[ERR]` / `[FTL]` markers via regex `^\[\d{2}:\d{2}:\d{2} (ERR|FTL)\]`.
- **SBECmd CSV columns to map** (per `context/domain/06` §5.8 lines 1343–1349 + encyclopedia §23 lines 1934–2014): `BagPath`, `Slot`, `NodeSlot`, `MRUPosition`, `AbsolutePath`, `ShellType`, `Value`, `ChildBags`, `FirstInteracted`, `LastInteracted`, `LastWriteTime`, `MFTEntry`, `MFTSequenceNumber`, `IconReference`, `HasExplored`, `Hive`, `RegistryPath`.
- **`FirstInteracted` / `LastInteracted` semantics.** Per encyclopedia §23 + SBECmd behavior: these are derived from the BagMRU `LastWriteTime` of the bag's parent node and the slot ordering. Both fields are `Optional[datetime]` because Win10+ rows often have `LastInteracted` blank. Do NOT fall back to `LastWriteTime` to fill `LastInteracted` — keep them distinct so the agent sees missing data honestly.
- **`AbsolutePath` reconstruction.** SBECmd walks the BagMRU tree and stitches the parent chain into `AbsolutePath` (e.g. `Desktop\My Computer\E:\confidential\`). For network paths it surfaces `\\server\share\subpath`. The string is verbatim from SBECmd — do not normalize separators, even though backslashes vs forward slashes differ from POSIX hosts; the citation gate needs the literal bytes.
- **`IconReference` is forensically interesting.** Per encyclopedia §23 line 1934 the IconReference can point at a file outside the system (e.g. `C:\Tools\Ethereal\ethereal.ico` proving the user opened that folder). Surface it as `Optional[str]`.
- **NTUSER.DAT vs UsrClass.dat.** Per encyclopedia §23 line 1949: "Modern Windows (Win10+) writes the bulk of ShellBag data to UsrClass.dat, not NTUSER.DAT." If the input directory has NTUSER.DAT only, results will be sparse — emit the advisory above so the agent doesn't form a wrong "user browsed nothing" conclusion.
- **Caveats are the wedge.** Use the four caveats verbatim. The "Explorer-only" caveat (cmd.exe / PowerShell don't produce ShellBags) is the single most common analyst error — it prevents the model from concluding "no ShellBag → no access."
- **Corroboration cross-references.** `parse_mft` (for the same path's MFT record), `parse_amcache` (PRESENCE of executables in that folder), `regripper_run` with plugins `usbstor` / `mountdev` / `mp2` for external-volume serial cross-reference. Cite the regripper plugin names verbatim — they exist (see `context/domain/06` §6.1 plugin catalog).
- **LOC discipline.** Final running total: ~345 LOC. Stay under 400.
- **Vocab discipline.** No "court-admissible," no "Ralph Wiggum." Use "persist," "navigation," "evidence of folder access" — not "proof of presence at the keyboard."
