# 04 — Disk, Network, and Log Forensics: Deep Reference

> Pure domain knowledge. Three big sections:
> - **Part A:** Disk and filesystem forensics (NTFS internals, $LogFile, USN Journal, VSS, Plaso, Sleuth Kit, EWF, carving, encryption, hashes)
> - **Part B:** Network forensics (PCAP, tshark, Zeek, Suricata, JA3, RITA, beacon theory, DNS exfil, C2 patterns)
> - **Part C:** Log analysis (Windows Event Log architecture, full event ID catalog, Sysmon reference, Hayabusa, Chainsaw, Sigma)
>
> No "the agent should." Domain only. Reference material to be consulted while designing.

---

# PART A — DISK + FILESYSTEM FORENSICS

## 1. NTFS Internals (Deep)

NTFS (New Technology File System) is the default filesystem on every modern Windows installation. Understanding NTFS internals at the data-structure level is what separates surface-level Windows forensics from real forensics — every artifact recovery, every timeline question, every anti-forensics defeat ultimately comes back to how NTFS lays its bytes out on disk.

### 1.1 Cluster Size and Sector Geometry

A cluster (sometimes called an allocation unit) is the smallest unit of space NTFS allocates. The cluster size is set at format time and stored in the boot sector. Common defaults:

| Volume Size | Default Cluster Size |
|---|---|
| 7 MB – 16 TB | 4 KB |
| 16 TB – 32 TB | 8 KB |
| 32 TB – 64 TB | 16 KB |
| 64 TB – 128 TB | 32 KB |
| 128 TB – 256 TB | 64 KB |

A physical sector is 512 bytes on legacy drives, 4096 bytes (4Kn) on modern Advanced Format drives. Clusters are always a multiple of sectors. The fact that cluster size is almost always 4 KB on practitioner systems is the engine behind both file slack (Section 2) and the inability to recover certain small files exactly — they live inside MFT records, not in independent clusters.

The boot sector (sector 0 of the partition) holds the BIOS Parameter Block (BPB), which records: bytes-per-sector, sectors-per-cluster, MFT cluster location, MFT mirror location, MFT record size, index record size, volume serial number, and the bootstrap code. A backup boot sector is at the very end of the volume. If the primary boot sector is wiped, the backup often allows reconstruction.

### 1.2 The Master File Table (MFT)

Every file and directory on NTFS has a record in the MFT, including the MFT itself. The MFT lives in a special file named `$MFT` (the dollar sign prefix is reserved for NTFS metadata files; user files cannot start with `$`). MFT records are fixed size — almost always 1024 bytes regardless of cluster size.

The first 16 records of the MFT are reserved for NTFS system files:

| Record # | File | Purpose |
|---|---|---|
| 0 | $MFT | The MFT itself |
| 1 | $MFTMirr | First 4 records mirrored (recovery) |
| 2 | $LogFile | Transaction log (see Section 3) |
| 3 | $Volume | Volume metadata, label, serial |
| 4 | $AttrDef | Attribute type definitions |
| 5 | . (root) | Root directory |
| 6 | $Bitmap | Cluster allocation bitmap |
| 7 | $Boot | Boot sector copy |
| 8 | $BadClus | Bad cluster list |
| 9 | $Secure | Security descriptors (NTFS 3.0+) |
| 10 | $UpCase | Unicode uppercase mapping |
| 11 | $Extend | Container for $UsnJrnl, $Quota, $ObjId, $Reparse |
| 12-15 | (reserved) | — |

Records 16 and beyond hold user files and directories.

Each MFT record begins with a `FILE` signature (older Windows used `BAAD` for corrupt records) followed by an update sequence number, then a sequence of attributes. The record itself has flags indicating: in use vs deleted, file vs directory, has index, has view index. The "in use" bit is what `fls -r` reports as the difference between live and deleted entries — when a file is deleted the in-use bit clears but the record content (including filename, timestamps, $DATA runs) often remains intact until that record slot is reused.

When a file is too large to fit in a single 1024-byte record (e.g., heavily fragmented files with hundreds of data runs), NTFS uses an `$ATTRIBUTE_LIST` attribute that points to additional MFT records holding the overflow attributes. These continuation records are themselves MFT entries — they consume MFT slots.

### 1.3 Resident vs Non-Resident Attributes

Each MFT record holds attributes. An attribute can be **resident** (data stored inline in the record) or **non-resident** (data stored in clusters elsewhere, with the MFT record holding a "data run" list).

A small file — say a 500-byte text file — typically has its `$DATA` attribute stored resident, meaning the entire file content lives inside the 1024-byte MFT record. There is no separate cluster allocated. This has two forensic consequences:

1. **Resident file recovery from MFT alone** — Even if the filesystem is otherwise wiped, recovering the MFT recovers all resident file content.
2. **No file slack for resident files** — Slack space (Section 2) is a property of cluster allocation. Resident files don't allocate clusters.

A larger file (say, 100 KB) has a non-resident `$DATA` attribute. The MFT record contains data runs in the form `(length, offset)` pairs in compressed runlist encoding. For example: `21 04 0000 28 00` decodes as one run of 4 clusters starting at cluster 40. The actual file content lives in those 4 clusters.

### 1.4 Key Attribute Types

NTFS defines many attribute types, identified by a 4-byte type code. The most forensically important:

#### $STANDARD_INFORMATION (0x10) — "SI" or "$SI"

Holds the four canonical MAC timestamps plus DOS attributes:
- **Created** (file creation time)
- **Modified** (last data write)
- **MFT Modified** (last metadata change — the "C" or "ctime" in Unix terms; this includes permission changes, rename, attribute changes)
- **Accessed** (last read access — disabled by default on NTFS since Windows Vista, controlled by `NtfsDisableLastAccessUpdate`)

Critically, `$STANDARD_INFORMATION` is the timestamp source that user-mode APIs (the `dir` command, Windows Explorer property dialog, `GetFileTime`) report. It is also the only set of timestamps an attacker can modify trivially using user-mode "timestomp" tools — `SetFileTime()` operates on `$SI`.

#### $FILE_NAME (0x30) — "FN" or "$FN"

Holds the same four timestamps but updated by the kernel only on filename-related operations (file creation, rename, move). User-mode timestomp tools cannot directly modify these without kernel-level techniques.

This asymmetry is the heart of NTFS timestomp detection:
- `$SI created` < `$FN created` → suspicious (file appears older in user metadata than its name-allocation record)
- `$SI` shows sub-second precision of `.0000000` (zeros) while `$FN` shows real sub-second precision → tooling fingerprint (early timestomp tools wrote whole-second precision; the kernel writes 100-nanosecond precision)
- `$SI modified` < `$SI created` → physically impossible naturally, certain hand-edits produce this

The fact that NTFS keeps two timestamp records by design is one of the most useful anti-anti-forensics properties of the filesystem. `MFTECmd`, `analyzeMFT.py`, and `fls -m` all expose both sets.

A single MFT record can hold multiple `$FILE_NAME` attributes: one for the Win32 long name, one for the DOS 8.3 short name (when 8.3 name generation is enabled — controlled by `NtfsDisable8dot3NameCreation`), and additional ones if the file has hard links.

#### $DATA (0x80)

The file content itself. As noted above, resident for small files, non-resident for large. The unnamed `$DATA` attribute is the primary stream.

**Alternate Data Streams (ADS):** NTFS allows multiple `$DATA` attributes per file, distinguished by name. The syntax is `filename:streamname` — e.g., `report.pdf:hidden.exe`. The primary stream has no name. Alternate streams do not show up in directory listings, do not contribute to the reported file size, and historically have been used to hide payloads. They are also used legitimately — `Zone.Identifier` is the most common ADS in the wild, added by Internet Explorer / Edge / Chrome to mark downloaded files (this is what Mark-of-the-Web detection reads). The PowerShell command `Get-Item -Path file.ext -Stream *` enumerates streams; `dir /R` does the same. `streams.exe` from Sysinternals predates these. `fls` and `MFTECmd` enumerate all $DATA attributes including alternates.

#### $INDEX_ROOT (0x90) and $INDEX_ALLOCATION (0xA0)

Directories use B+ tree indexes. Small directories store the index resident in `$INDEX_ROOT`. Larger directories spill into `$INDEX_ALLOCATION`, which references index buffer (`INDX`) records (4096 bytes each by default, stored in clusters).

`$I30` is the conventional name for the index that maps filename→MFT-record. Forensically, `$I30` slack — the unused space at the end of an INDX buffer — preserves the names of deleted files long after the MFT record has been reused. Tools like `INDXParse.py` and `MFTECmd` (with `--ds` flag) extract these "ghost" filenames. This is one of the cleaner residue artifacts for proving a file existed without recovering the file itself.

#### $BITMAP (0xB0)

Two distinct uses: (a) as an MFT record attribute, marks which clusters are allocated to a non-resident attribute or which INDX buffers in `$INDEX_ALLOCATION` are in use; (b) as the `$Bitmap` system file (MFT record 6), a single bit per volume cluster indicating allocated/free.

#### $OBJECT_ID (0x40)

Holds the file's object ID — a GUID assigned by the Distributed Link Tracking service. Object IDs survive renames and moves within a volume. Useful for correlating LNK files (which embed the object ID) back to their target even if the target was renamed.

#### $REPARSE_POINT (0xC0)

Junction points, symbolic links, mount points, and OneDrive-style placeholders all use reparse points. Holds a reparse tag identifying the type and data interpreted by the relevant driver.

#### $LOGGED_UTILITY_STREAM (0x100)

EFS-encrypted file metadata (DDFs, DRFs — the data decryption fields holding the per-file FEK encrypted with each authorized user's RSA public key) lives in this attribute as the `$EFS` named stream. This is what `efsdump.exe` and EFS recovery tooling reads.

### 1.5 NTFS Compression

NTFS supports per-file LZNT1 compression (set with `compact /c`). Compressed files have `$DATA` runs interleaved with sparse runs. A 64-cluster "compression unit" (the LZNT1 chunk size) is the smallest unit compressed. Carving compressed file content requires reversing LZNT1 — `ntfscat` (Sleuth Kit's `icat` for NTFS) handles this transparently.

### 1.6 NTFS Sparse Files

Sparse files have logical clusters not mapped to physical clusters; reads return zeros. Common with VM disk images (.vhd, .vhdx with the sparse flag), database files, and tracking databases. The sparse range encoding is in the data runs.

## 2. File Slack — RAM Slack vs File Slack vs Partition Slack

Slack space is unused space within an allocated region. There are three distinct kinds:

### 2.1 RAM Slack (sector slack)

When a file's last sector is partially used, the operating system pads the rest of the sector with whatever happens to be in memory at write time. Older Windows (Win9x, NT4) padded with raw RAM contents, leaking passwords, fragments of other documents, and similar data — hence the name. Modern Windows zeros this padding, eliminating that leak. RAM slack is the region from the end-of-file marker to the end of the current sector.

### 2.2 File Slack (cluster slack)

After the last sector of the file is fully accounted for, the cluster usually still has additional sectors. Those sectors were previously used by some prior file and were never overwritten when the new file was allocated to that cluster — Windows zeroes only the metadata, not the data. This region from the end of the file's last sector to the end of the cluster holds whatever was there before.

For a 4 KB cluster (8 sectors of 512 bytes) holding a file of size 1500 bytes:
- Sector 0: 512 bytes of file
- Sector 1: 512 bytes of file
- Sector 2: bytes 0-475 are file content; bytes 476-511 are RAM slack
- Sectors 3-7: file slack (3.5 KB of old data)

For 4Kn drives (4096-byte sectors with 4096-byte clusters), there is no file slack — one cluster, one sector. This is increasingly common.

### 2.3 Partition Slack (volume slack)

The space between the last cluster of an allocated volume and the end of the partition. Created when a volume is shrunk, or when the partition was sized larger than the volume. Sometimes contains a deleted volume's residue.

### 2.4 Slack Tooling

- `bulk_extractor` — scans entire image including slack for regex patterns (emails, URLs, credit cards, BTC addresses)
- `blkls -s` (Sleuth Kit) — extracts slack space
- `dls` (older Sleuth Kit) — extracts unallocated space
- Manual: `icat` to extract the file, calculate physical cluster span, then `blkcat` the trailing clusters

## 3. $LogFile Mechanics

`$LogFile` (MFT record 2) is NTFS's transaction log. It is the mechanism that lets NTFS recover from an interrupted operation — a crash mid-rename, a power loss during a write. Forensically, it is a goldmine of recently-undone or recently-redone metadata operations.

### 3.1 Structure

The log is divided into two regions:
- **Restart area** (first ~8 KB) — pointers to the current and previous restart records, used at mount time
- **Logging area** (remainder) — a circular buffer of log records

Each log record is a **redo/undo pair**: the action taken (redo), the action that would reverse it (undo), plus the target MFT record and attribute, the LSN (Log Sequence Number), the transaction ID, and the client (almost always `NTFS`).

The log file is fixed-size (typically 65 MB by default — `chkdsk /l:N` sets size in KB). Once full, it wraps. So the log holds **only recent activity** — minutes on a busy system, hours or days on a quiet one. There is no archive.

### 3.2 What Gets Logged

NTFS logs metadata operations, not file content. The standard logged operations:
- File/directory creation (MFT record allocation, $FILE_NAME assignment)
- File deletion (MFT record deallocation)
- Rename / move
- Attribute changes (resident → non-resident transitions)
- Security descriptor changes ($Secure updates)
- Cluster allocations and deallocations ($Bitmap updates)
- Index entry insertions and deletions ($I30 changes)

File data writes are not logged (the data itself isn't journaled, only the metadata). USN Journal entries are logged.

### 3.3 Forensic Use

The combination of redo+undo records means each operation has both states recorded. A delete operation logs:
- Undo: the original $FILE_NAME entry to re-insert in the parent $I30
- Redo: the removal action

So even after deletion, `$LogFile` may hold the deleted filename, parent directory MFT reference, and timestamps. Combined with `$UsnJrnl:$J` (Section 4) and `$MFT` residue, the picture of recent filesystem activity is detailed.

### 3.4 Tools

- **LogFileParser** (David Cowen / Joachim Metz) — parses redo/undo records to readable output
- **NTFSLogTracker** (Blackbag-era tool, now defunct)
- **Eric Zimmerman's LECmd / MFTECmd** — MFTECmd does $LogFile-adjacent parsing; LECmd is for LNK files
- **`fsutil resource setlog growthsize`** — administrative; not forensic
- Raw extraction: `icat -f ntfs <image> 2` extracts the $LogFile contents

The big practical caveat: $LogFile is volatile. Reboots after the incident may roll the log over. Many real engagements find the log already wrapped.

## 4. USN Change Journal ($UsnJrnl:$J)

The USN (Update Sequence Number) Change Journal is a separate, longer-lived log of filesystem changes maintained for applications that need to know "what changed since last time" (indexers, antivirus, backup software). It lives as the `$J` ADS of the `$UsnJrnl` file under `$Extend`.

### 4.1 Architecture

`$UsnJrnl` has two streams:
- `$J` — the actual journal records (typically dozens to hundreds of MB)
- `$Max` — current and maximum journal size, lowest valid USN

The journal is sparse — only the active region holds data. As new records are appended, the journal grows; once the size limit is hit, the oldest entries are zeroed out from the front. The default size on Windows 10+ is around 32 MB but Windows raises this dynamically.

Each USN record has:
- USN (file change sequence number)
- Timestamp (FILETIME)
- File reference number (MFT record number + sequence)
- Parent file reference number
- Filename (as a Unicode string)
- File attributes
- Reason flags (bitmask describing what changed)
- Source info (whether the change came from a normal app, an auxiliary file create like log file rotation, replication management, etc.)

### 4.2 Reason Flags Table

The Reason field is a bitmask. Multiple flags can be set on one record, and records for the same file accumulate as the file's state evolves until a CLOSE reason finalizes the change set. The official Microsoft documentation lists these flags:

| Flag | Value | Meaning |
|---|---|---|
| USN_REASON_DATA_OVERWRITE | 0x00000001 | Data in primary $DATA changed (overwrite) |
| USN_REASON_DATA_EXTEND | 0x00000002 | File grew |
| USN_REASON_DATA_TRUNCATION | 0x00000004 | File shrunk |
| USN_REASON_NAMED_DATA_OVERWRITE | 0x00000010 | ADS data overwritten |
| USN_REASON_NAMED_DATA_EXTEND | 0x00000020 | ADS extended |
| USN_REASON_NAMED_DATA_TRUNCATION | 0x00000040 | ADS truncated |
| USN_REASON_FILE_CREATE | 0x00000100 | File created |
| USN_REASON_FILE_DELETE | 0x00000200 | File deleted |
| USN_REASON_EA_CHANGE | 0x00000400 | Extended attributes changed |
| USN_REASON_SECURITY_CHANGE | 0x00000800 | ACL changed |
| USN_REASON_RENAME_OLD_NAME | 0x00001000 | Rename — old name record |
| USN_REASON_RENAME_NEW_NAME | 0x00002000 | Rename — new name record |
| USN_REASON_INDEXABLE_CHANGE | 0x00004000 | Search indexer flag change |
| USN_REASON_BASIC_INFO_CHANGE | 0x00008000 | $STANDARD_INFORMATION changed |
| USN_REASON_HARD_LINK_CHANGE | 0x00010000 | Hard link added or removed |
| USN_REASON_COMPRESSION_CHANGE | 0x00020000 | Compression flag toggled |
| USN_REASON_ENCRYPTION_CHANGE | 0x00040000 | Encryption flag toggled |
| USN_REASON_OBJECT_ID_CHANGE | 0x00080000 | Object ID set/changed |
| USN_REASON_REPARSE_POINT_CHANGE | 0x00100000 | Reparse point added/changed |
| USN_REASON_STREAM_CHANGE | 0x00200000 | Named stream added/removed |
| USN_REASON_TRANSACTED_CHANGE | 0x00400000 | TxF transaction |
| USN_REASON_INTEGRITY_CHANGE | 0x00800000 | ReFS integrity stream change |
| USN_REASON_DESIRED_STORAGE_CLASS_CHANGE | 0x01000000 | Storage tier hint changed |
| USN_REASON_CLOSE | 0x80000000 | All accumulated reasons; final record for this change set |

### 4.3 What Gets Recorded vs Not

The USN journal records:
- All metadata operations (creates, deletes, renames, attribute changes)
- All write operations as DATA_EXTEND / DATA_OVERWRITE
- Stream operations as NAMED_DATA_*
- Closures as CLOSE records

It does NOT record:
- The content of the change (no before/after data)
- Reads (no access logging)
- Operations on files outside the journaled volume

USN entries are pruned when the journal hits its max size — oldest entries (sparse zeroed) are dropped. Disabling the journal (`fsutil usn deletejournal /D <vol>`) zeroes the active range. Re-enabling creates a fresh, empty journal — the prior contents are gone (though residue in unallocated clusters that previously held journal pages may still be carveable).

### 4.4 Tools

- **MFTECmd** (Eric Zimmerman) — `-f $J --csv` outputs the entire journal as CSV with reason flags decoded
- **UsnJrnl2Csv** (older)
- **fsutil usn readjournal C: csv** — administrative; not full
- **Plaso** — `usnjrnl` parser

Common forensic queries:
- All FILE_CREATE records in a time window → newly created files
- All FILE_DELETE records → recently deleted files (often correlated with $LogFile undo records to recover names)
- All RENAME_OLD_NAME + RENAME_NEW_NAME pairs → renames (useful when an attacker stages a binary under a benign name then renames)

The USN journal also catches `$Recycle.Bin` movements — when a file is "deleted" via Explorer, USN sees a RENAME from the original path to `\$Recycle.Bin\<SID>\$R<id>.<ext>`.

## 5. Volume Shadow Copies (VSS)

Volume Shadow Copy Service is Windows's filesystem-level snapshot mechanism, used by System Restore, File History, the WMI `BackupIntent`, Windows Backup, third-party backup products, and the `vssadmin` command. Forensically, VSS gives access to the filesystem state at past points in time.

### 5.1 Architecture

VSS uses a copy-on-write block-level snapshot. When a snapshot is created, a sparse "diff area" is allocated (default 10% of volume size, stored at `\System Volume Information\{GUID}`). The filesystem then tracks block writes:
- A write to a previously unmodified block (relative to the snapshot) first copies the original block into the diff area, then performs the write.
- Reads of the snapshot through VSS resolve from the diff area for changed blocks, from the live volume for unchanged blocks.

This means shadow copies are not full file copies — they are a logical view of the filesystem at the snapshot time, reconstructed from the live volume + the diff area. If the diff area is destroyed, the shadow copies are unrecoverable.

Snapshots are identified by GUIDs. The metadata file structure lives under `\System Volume Information\` and includes the `{3808876b-c176-4e48-b7ae-04046e6cc752}` files (the WMI Repository CIM database is also in that folder, but it's unrelated).

### 5.2 VSS API vs Raw Block Reads

There are two ways to access shadow copies:

**Via the VSS API** — `vssadmin list shadows` to enumerate, `mklink /D` against `\\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy<N>` to access. This is the "live" route — requires the volume mounted and the VSS service running.

**Via raw block reads against the image** — Joachim Metz's `libvshadow` library reads the VSS metadata directly from a disk image. This is the forensic route, working on offline acquired images:
- `vshadowinfo <image>` — lists all shadow copies present
- `vshadowmount <image> /mnt/vshadow/` — mounts each shadow copy as a file (e.g., `vss1`, `vss2`)
- After `vshadowmount`, each `vssN` file can be mounted with `mmls`/`fls`/loop device as a full filesystem at the point-in-time

This is the canonical method used by SIFT and most modern toolkits.

### 5.3 What to Look For in Older Shadow Copies

The forensic value of VSS comes from the *delta* — what's in an older shadow copy that's not in the live volume:

- **Files deleted between snapshot and present** — recover from the older copy directly
- **Earlier registry hive snapshots** — `SOFTWARE`, `SYSTEM`, `SAM`, `SECURITY`, `NTUSER.DAT` from past states. An attacker who modifies `Run` keys, adds services, or clears autorun entries leaves a trail in earlier hive snapshots.
- **Earlier `$MFT`** — files that existed in the past and were never in the live MFT
- **Earlier `$UsnJrnl`** — USN entries that have since rolled out of the live journal
- **Earlier event logs** — `.evtx` files from a prior state, especially useful if the attacker cleared logs after the snapshot
- **Earlier prefetch / amcache / shimcache** — execution evidence from past states
- **Earlier browser history** — InPrivate browsing leaves nothing in the live history, but the shadow copy from before the user purged history holds it

A common attacker action is `vssadmin delete shadows /all /quiet` (also: `wmic shadowcopy delete`, `vssadmin resize shadowstorage`). This is now a near-canonical ransomware behavior. Microsoft Defender flags this as a high-severity event (event 1116 / 1117). Both attackers and forensic examiners know shadow copies are useful.

### 5.4 ShadowExplorer / WinShadow

GUI tools for browsing shadow copies on live or imaged systems. Useful for non-CLI workflows. Largely superseded by `vshadowmount` for batch / scripting work.

## 6. Plaso / log2timeline (Super-Timeline)

Plaso (formerly `log2timeline`, the tool is now called `plaso`, the parsing engine retained the name `log2timeline.py`) is the modular timelining framework that produces the **super-timeline** — every parseable timestamped event from every artifact on the system, merged into a single timeline.

### 6.1 Architecture

Plaso has four layered components:

**PVFS / dfVFS** (digital forensics Virtual File System) — Joachim Metz's abstraction layer for accessing filesystems from raw images, E01 files, VHD/VHDX, VMDK, partition tables, BitLocker volumes, etc. dfVFS speaks libtsk, libewf, libvshadow, libqcow, libvhdi, libvmdk underneath. This is the layer that gives Plaso the ability to recursively process a disk image as if it were a directory tree, including shadow copies.

**Plaso parsers** (~270 in current Plaso, growing) — small Python modules each focused on one artifact type. Each parser declares what it parses, extracts events, and emits them as event objects with timestamps, descriptions, and metadata. Examples: `winevtx` (Windows Event Logs), `pe` (PE header timestamps), `prefetch`, `mft`, `usnjrnl`, `lnk`, `recycle_bin`, `mactime` (for $MACB body file output), `chrome_history`, `firefox_history`, `bash_history`, `syslog`, `safari_history`, `mac_keychain`, `pcap`, `winreg` (registry hives — itself wraps dozens of plugins for individual keys).

**Plaso storage** — events are serialized to a SQLite database (the `plaso.sqlite` storage file format; older versions used a custom format called `plaso_storage_file`). The storage file is single-writer, multiple-reader. It is processed by `psort.py`.

**Psort** — sorts events, applies filters, deduplicates, and emits the final output in one of many formats.

### 6.2 The `storage_file` Format

The storage file is a SQLite database with tables for:
- `event_data` — per-parser extracted event records (file references, descriptions)
- `event` — the timestamped events themselves
- `event_data_stream` — file content streams referenced by events
- `event_tag` — tags applied by post-processing analyzers (e.g., "browser_search", "malicious_file_hit")
- `analysis_report` — output from analysis plugins
- `task` — internal processing state
- `metadata` — collection metadata, runtime info

This format is well-documented and stable. It can be queried directly with SQL for custom workflows.

### 6.3 Parser Plugins and Filters

Plaso parsers are organized by category. The current categories include `windows`, `linux`, `mac`, `web`, `chat`, `cloud`, `mobile`, `database`, `compressed`. A parser can be enabled or disabled via the `--parsers` flag — e.g., `--parsers='winreg,winevtx,prefetch'`.

Filters operate either at collection time (`--filter_file` with a YETI-like rule list specifying which paths to process) or at psort time (event filter language: `parser is 'winevtx' AND timestamp > '2024-01-01' AND message contains 'rundll32'`).

### 6.4 Output Formats

`psort.py -o <format>` supports many output formats; the canonical three for IR work:

**l2tcsv** — the original log2timeline CSV format. Columns: date, time, timezone, MACB, source, sourcetype, type, user, host, short, desc, version, filename, inode, notes, format, extra. Verbose but human-readable, opens in Excel.

**l2ttln** — a newer tabular format also CSV but ordered for timeline diff: time, source, host, user, description. Compact.

**dynamic** — user-specified field list. `--fields 'datetime,timestamp_desc,source,source_long,message,parser,display_name'`. The most common modern choice.

Other formats: `json`, `json_line`, `kml` (for geolocation events), `tln` (Carvey's TLN), `mactime` (compatible with the older `mactime` body file), `xlsx`, `4n6time_sqlite`.

### 6.5 The Super-Timeline Concept

The "super-timeline" is the idea that every timestamp-bearing artifact on a system can be merged into one giant chronological view. Each event has a "timestamp_desc" indicating which timestamp it represents — `creation time`, `last access time`, `program executed`, `entry written`, `last logon`, etc. The same file might appear in the super-timeline multiple times: once for its MFT $SI created, once for its $SI modified, once for its Prefetch last-run, once for its LNK file's target-creation, once for an event log mention.

This is the most powerful and most overwhelming forensic artifact. A modest system produces millions of events. Filtering, time-windowing, and tagging are essential.

Plaso has built-in **analysis plugins** that post-process the timeline: `tagging` (apply tags from rule files like `tag_windows.txt` / `tag_linux.txt` shipped with Plaso), `nsrlsvr_analyzer` (whitelist by NSRL hash), `virustotal` (lookup hashes), `browser_search` (extract searches from history events), `windows_services` (correlate service install events).

### 6.6 Mactime — the Older Alternative

Before Plaso, `mactime` (Sleuth Kit) was the canonical timelining tool. The workflow:
1. `fls -r -m / <image>` generates a body file with $MACB timestamps for every MFT entry
2. `mactime -b body.txt -d > timeline.csv`

The body file format is pipe-separated: `MD5|name|inode|mode_as_string|UID|GID|size|atime|mtime|ctime|crtime`. Timestamps are Unix epoch.

Mactime timelines only cover filesystem metadata — they miss Event Logs, registry, browser history, prefetch. They are still useful for fast first-pass filesystem timelining when Plaso is overkill, and for cross-checking Plaso output.

### 6.7 Practical Reference

- `log2timeline.py <storage.plaso> <image_or_mount>` — collect
- `log2timeline.py --parsers='!filestat' ...` — exclude (the leading `!`)
- `log2timeline.py --vss-stores=all ...` — recurse into all shadow copies
- `pinfo.py <storage.plaso>` — show metadata about a plaso storage file (parsers used, errors, time range)
- `psort.py -o dynamic --fields 'datetime,timestamp_desc,source,message' -w timeline.csv <storage.plaso>` — emit CSV
- `psort.py -o l2tcsv -w out.csv <storage.plaso> "timestamp > DATETIME('2024-01-01')"` — emit with event filter

## 7. The Sleuth Kit (TSK) — Deep Reference

The Sleuth Kit is Brian Carrier's command-line forensic toolkit. It is filesystem-aware (NTFS, FAT, ext2/3/4, HFS+, ISO9660, YAFFS2) and operates directly on disk images. TSK is the substrate beneath Autopsy and beneath much of Plaso.

The TSK tool naming convention is regular: prefix = layer, suffix = action.
- `mm*` — media/partition layer
- `fs*` — filesystem layer (rarely used directly)
- `f*` — file layer (file-level operations)
- `i*` — inode/metadata layer
- `blk*` — block/data layer

### 7.1 mmls — Partition Table Listing

`mmls <image>` lists partitions in the image, with start sector, length, and partition type. Supports DOS partition tables, GPT, Mac partition map, BSD disklabel, Sun VTOC. Output:

```
DOS Partition Table
Offset Sector: 0
Units are in 512-byte sectors

      Slot    Start        End          Length       Description
000:  Meta    0000000000   0000000000   0000000001   Primary Table (#0)
001:  -----   0000000000   0000002047   0000002048   Unallocated
002:  000:000 0000002048   0204798015   0204795968   NTFS / exFAT (0x07)
003:  -----   0204798016   0205000703   0000202688   Unallocated
```

The "Unallocated" rows are partition slack — important.

### 7.2 fls — Filesystem Listing

`fls -r -o <offset> <image>` lists files in a partition. Flags:
- `-r` — recursive
- `-o N` — partition offset (from mmls)
- `-m /` — mactime body file output
- `-l` — long format with timestamps
- `-p` — full paths
- `-d` — display deleted entries only
- `-u` — display only undeleted

A `*` prefix in the output marks a deleted entry. The inode (MFT record) is shown. Example: `r/r * 12345-128-3: pwned.exe` means a regular file, deleted, MFT 12345, attribute type 128 ($DATA), attribute ID 3.

### 7.3 icat — Extract by Inode

`icat -o <offset> <image> <inode>` writes the file content to stdout. For alternate streams: `icat <image> 12345-128-2`. For non-resident attributes, follows data runs. For resident attributes, extracts from the MFT record directly.

### 7.4 istat — Inode Detail Dump

`istat <image> <inode>` prints everything TSK knows about an MFT entry: attribute list, timestamps ($SI and $FN), data run list, security descriptor SID (where available), parent directory.

### 7.5 ils — Deleted Inodes

`ils <image>` lists inodes (all by default, deleted-only with `-r`). For NTFS, lists MFT records — useful when an entry is unlinked from any directory but the MFT record still has data.

### 7.6 tsk_recover

`tsk_recover -e <image> <output_dir>` extracts all files (allocated and unallocated, with `-e` flag) to a directory tree mirroring the source layout. The fastest way to bulk-extract.

### 7.7 fcat

`fcat -o <offset> <image> <path>` extracts a file by path rather than inode. Useful when the path is known.

### 7.8 blkls / blkcat / blkstat

- `blkls <image>` — extracts unallocated clusters as one stream (useful for piping to `bulk_extractor` or `foremost`)
- `blkls -s <image>` — extracts slack space only
- `blkcat <image> <addr>` — dumps a single cluster's content
- `blkstat <image> <addr>` — reports allocation status of a cluster

### 7.9 Other Useful TSK Commands

- `fsstat` — filesystem statistics (cluster size, MFT location, volume serial)
- `img_stat` — image format details (raw, E01, etc.)
- `img_cat` — extract the raw image content (for format conversion)
- `srch_strings` — TSK's `strings` with awareness of clusters
- `sigfind` — locate a hex signature in the image (header carving primitive)
- `sorter` — sort files by extension/category (older)
- `hfind` — hash database lookup (for NSRL whitelist filtering)

## 8. EWF / E01 Format

The EnCase Evidence File (EWF, file extension `.E01`) is the de facto forensic image format. Designed by Guidance Software (now OpenText) for EnCase, the format is documented and supported by open-source tools via Joachim Metz's `libewf`.

### 8.1 Properties

- **Compressed** — built-in deflate; image often 30-70% of original size
- **Chunked** — typically 32 KB sectors per chunk with CRC; corruption of one chunk localizes the damage
- **Hashed** — MD5 and/or SHA-1 of each chunk plus the full image
- **Split** — large images split into `.E01`, `.E02`, ... `.Exx` segments (default segment size around 2 GB for backward compatibility)
- **Metadata** — case number, examiner name, evidence number, notes, acquisition date stored in the header

### 8.2 Tools

- `ewfacquire` — interactive acquisition. Prompts for source, destination, case metadata, compression level. Writes the E01.
- `ewfmount` — mounts an E01 as a raw image at a mount point (e.g., `/mnt/ewf/ewf1`). After mount, the raw image can be processed with `mmls`, `fls`, `loop` device, etc.
- `ewfverify` — recomputes hashes, compares to stored hashes. Reports any mismatched chunks.
- `ewfinfo` — prints the metadata header
- `ewfexport` — converts an E01 to raw, or to a different EWF variant (E01, Ex01, L01)
- `ewfrecover` — attempts to repair a damaged E01

`libewf` underpins `ewfmount`, `dfvfs` (and thus Plaso), Sleuth Kit's E01 support, Autopsy.

### 8.3 Hash Verification

A valid E01 holds the per-image MD5 and (newer Ex01) SHA-1 / SHA-256. `ewfverify` reads the stored hash, recomputes, and exits 0 on match. This is the formal chain-of-custody check — examiners frequently log this output as proof the image was not corrupted in storage or transfer.

### 8.4 The Ex01 Variant

EnCase 7+ introduced Ex01 — uses LZMA compression, supports SHA-1 and SHA-256, supports encryption with bzip2 / deflate compression options. Less common in the wild but supported by libewf.

## 9. Forensic Imaging Tool Comparison

The choice of imaging tool affects throughput, error handling, and metadata completeness. Five common tools:

### 9.1 `dd`

The original. Block-level copy. No forensic features beyond raw copy. Cannot handle read errors well — abort or pad? — depends on `conv=` flags. Not recommended for forensic acquisition but useful for image manipulation.

### 9.2 `dc3dd`

US DoD Cyber Crime Center's fork of `dd`. Adds:
- Multiple hash algorithms computed during read (MD5, SHA-1, SHA-256, SHA-512)
- Progress reporting (bytes copied, throughput, ETA)
- Verify mode (recompute hash on the output and compare)
- Logging of read errors with sector addresses
- Direct E01-like split output (`hofs=...`)
- Wiping mode (`wipe=...`)

Syntax: `dc3dd if=/dev/sda hash=sha256 log=acq.log of=image.dd`.

### 9.3 `dcfldd`

Defense Computer Forensics Lab's older fork of `dd`, similar feature set to `dc3dd`. Mostly superseded by `dc3dd` but still widely deployed on SANS SIFT and Kali.

Key differences from `dc3dd`: dcfldd computes hashes incrementally and can split output. `dc3dd` is considered more actively maintained.

### 9.4 `ewfacquire`

Produces E01 (or Ex01) directly. Compresses on the fly. Logs the case metadata. The standard tool when the destination format is E01.

### 9.5 FTK Imager

GUI (Windows) and CLI (`ftkimager` on Windows/Linux). Free download. Writes E01 / S01 (smart) / AD1 (FTK proprietary) / raw. Verifies hashes.

### 9.6 Tableau Imager / Logicube Falcon / Atola Insight

Hardware imagers, used in enterprise forensic labs. Higher throughput than software, write-blocker built in. Not in the SIFT workflow but worth knowing.

### 9.7 The Hash Question

The standard practice: hash with both MD5 (legacy compatibility, fast) and SHA-256 (collision resistance). MD5 alone is now considered insufficient for new evidence — preimage and collision attacks are theoretical for evidence integrity but easily avoided by computing both.

## 10. ext4 Forensics Basics

The SIFT VM runs Ubuntu, and Linux server compromises remain common forensic cases. ext4 is the dominant Linux filesystem.

### 10.1 Inodes

ext4 inodes hold timestamps:
- `atime` — last access
- `mtime` — last data modification
- `ctime` — last inode change (metadata)
- `crtime` — file creation time (added in ext4 — ext2/3 had no creation time)
- `dtime` — deletion time (set when the inode is deleted; in deleted inodes this is the time of deletion, useful for timelining)

All timestamps are nanosecond precision (in modern ext4). The inode also stores: UID, GID, mode (permissions), block pointers (or extent tree, see below), link count, flags.

### 10.2 Extents

ext4 uses **extents** (contiguous block ranges) rather than indirect block pointers. The extent tree lives inside the inode for small files (up to 4 extents inline) and spills into an extent tree for larger files. This is more efficient for both allocation and traversal than ext3's indirect blocks.

### 10.3 The Journal

ext4 has a journal at `/.journal` (or external). Three modes: `journal` (full data + metadata journaling), `ordered` (default; metadata journaled, data written first), `writeback` (metadata only, no ordering). Tools: `debugfs`, `extundelete`, `ext4magic` for journal traversal and recovery.

### 10.4 lost+found

Each ext4 filesystem has a `lost+found` directory at the root. When `fsck.ext4` finds an inode that has no parent directory reference but is allocated and apparently valid, it links it into `lost+found` as `#<inode>`. Forensically, files in `lost+found` may be the residue of attempted anti-forensics or a crash mid-write.

### 10.5 Sleuth Kit ext4 Support

TSK's `fls`/`icat`/`istat` all work on ext4. `fls -r -m / image.dd` produces a body file. `extundelete` is purpose-built for ext recovery and is often more aggressive than TSK.

## 11. macOS HFS+ / APFS Basics

### 11.1 HFS+

Hierarchical File System Plus, used by macOS through 10.12. Catalog file (a B-tree) holds the directory structure and per-file metadata. Extents Overflow file holds non-inline extent records. Allocation file is the bitmap. Attributes file holds extended attributes and named forks.

Timestamps: `creation`, `modification`, `attribute_modification`, `access`, `backup`. HFS+ Journal (`.journal`) provides crash consistency.

Resource forks — HFS+'s alternate-stream equivalent — are now mostly historical (macOS apps stopped using them by Mac OS X 10.4).

### 11.2 APFS

Apple File System, default since macOS 10.13. Copy-on-write, supports clones (instant deduped copies — read references), supports native encryption (per-container, per-volume), supports snapshots (similar to ZFS / btrfs).

APFS has:
- A container superblock at offset 0x0
- Each volume is a B-tree of objects
- Object map maps object IDs to physical addresses
- Snapshots reference older object map states
- File records hold timestamps: `create_time`, `mod_time`, `change_time`, `access_time` — all nanosecond

Tools: `apfs-fuse` (open source mount), Plaso's APFS parser, `apfsstats`. Sleuth Kit added partial APFS support; coverage is incomplete compared to NTFS / ext4.

## 12. FAT32 Brief

Still seen on USB drives, SD cards, ESP partitions. FAT32's directory entry holds: short name (8.3), long name (in supplementary entries), attributes, create date+time, last access date (no time), last modified date+time, first cluster, file size. Timestamps are in DOS date+time format (2-second granularity for create modified, 1-day granularity for access). Subdirectories are themselves files holding directory entries.

Recovery: when a file is deleted, the first character of the short-name 8.3 entry is replaced with 0xE5 (the deletion marker), and the FAT chain entries are zeroed (the clusters are freed). The directory entry's other fields — name, size, first cluster — often survive intact until the slot is reused. PhotoRec / Foremost / scalpel work well on FAT recovery because file content is contiguous more often than on NTFS.

## 13. File Carving Theory

File carving is the recovery of files from unallocated space, slack, or arbitrary byte streams based on file format signatures rather than filesystem metadata. Necessary when the filesystem is corrupted, the file is in unallocated space, or there is no filesystem at all (e.g., a memory image).

### 13.1 Header-Footer Carving

The classical technique: identify a known file header signature (magic bytes), scan to a corresponding footer signature, extract the bytes in between.

Examples:
- JPEG: header `FF D8 FF E0` or `FF D8 FF E1`, footer `FF D9`
- PNG: header `89 50 4E 47 0D 0A 1A 0A`, footer `49 45 4E 44 AE 42 60 82`
- PDF: header `%PDF-`, footer `%%EOF`
- ZIP: header `PK 03 04`, footer `PK 05 06`
- Office Open XML: ZIP container; detect via inner stream signatures

Limitations: fragmented files (the body crosses non-contiguous clusters with intervening clusters from other files) cannot be reconstructed by simple header-to-footer carving — output is corrupted. NTFS sparse files and small fragmented allocations on aged disks are common worst cases.

### 13.2 Tools

**Foremost** — original header-footer carver from Air Force OSI. Config-driven (`foremost.conf` lists header/footer/max-size per type). Fast.

**Scalpel** — Foremost-style carver, faster on large images due to two-pass design. Same config syntax.

**PhotoRec** — TestDisk family. More sophisticated: knows about Office files, can carve FAT/ext/NTFS fragmented files in some cases by walking filesystem structures. The most-recommended general carver.

**Bulk Extractor** — Simson Garfinkel's tool. Doesn't carve whole files; instead carves *features* by regex: emails, URLs, credit card numbers, MAC addresses, IPs, BTC addresses, JPEGs (only the first carver match), KML, EXIF metadata, language hits. Output is per-feature text files. Scales to multi-TB images by parallelizing chunk scans.

### 13.3 Bulk Extractor Specifically

Bulk Extractor's strength is feature extraction across an entire image without filesystem traversal. The scanners include:
- `email` — RFC822 addresses
- `url` — HTTP/HTTPS/FTP URLs
- `domain` — DNS names
- `ccn` — credit card numbers (Luhn-checked)
- `ip` — IPv4/IPv6 addresses
- `aes` — AES key candidates
- `kml` — geographic coordinates
- `gps` — EXIF GPS data
- `exif` — EXIF metadata
- `lightgrep` — user-supplied regex
- `pii` — PII (SSN-shaped, ABA bank route numbers)

Output: a directory of `*.txt` files (`email.txt`, `url.txt`, ...) plus a `report.xml`. The `histogram` files rank by frequency, useful for pinning down primary actors among many.

## 14. Encrypted Volumes

### 14.1 BitLocker

Microsoft's full-volume encryption. Three protectors: TPM-only, TPM+PIN, TPM+startup-key. Recovery key (48-digit numeric) can decrypt the volume offline.

**libbde** (Joachim Metz) — open-source BitLocker library. Tools:
- `bdeinfo <image>` — reports BitLocker version, encryption algorithm (AES-128 / AES-256 / XTS-AES-128 / XTS-AES-256), protector list, volume GUID
- `bdemount <image> /mnt/bde -r <recovery_key>` — mounts the decrypted volume as a file; can also use `-p <password>` for password protector, `-k <startup_key_file>` for the startup key file
- `bdedecrypt` — produces a decrypted raw image

Acquisition strategies for BitLocker:
- **Live acquisition** — capture the volume in its decrypted state from the running OS
- **Recovery key** — if the recovery key is recorded (Active Directory, MS account, paper backup), decrypt offline with `bdemount`
- **TPM passthrough** — much harder offline; sometimes requires hardware-level work
- **Memory key extraction** — if a memory dump is available from the running system, `volatility3` plugin `windows.bitlocker.Bitlocker` extracts the volume master key

### 14.2 VeraCrypt (formerly TrueCrypt)

Open-source full-disk and file-container encryption. Hidden volume support, plausible deniability.

Detection: VeraCrypt volumes have no signature — they are designed to be indistinguishable from random data. Heuristic detection:
- Entropy near maximum (8.0 bits/byte for AES output)
- Volume header at the first 64 KB, encrypted with the user key
- Backup header at the last 64 KB

`hashcat` mode `-m 137xx` can attempt offline key recovery. Aaron Hambleton's `VolDiff` and `wTools` provide some volume detection heuristics. Memory-based key extraction from a running VeraCrypt session is feasible via Volatility plugins or `aeskeyfind`.

### 14.3 FileVault / FileVault 2

Apple's full-volume encryption. Uses the user's login password (or recovery key) to derive the volume key.

**libfvde** (Joachim Metz) — analogous to libbde:
- `fvdeinfo` — reports volume metadata
- `fvdemount -p <password> <image> /mnt/fvde`

T2 / Apple Silicon Macs encrypt by default at the SoC level (Secure Enclave). Offline decryption typically requires the password and a cooperative SoC — harder than legacy FileVault.

### 14.4 LUKS

Linux Unified Key Setup, the dominant Linux full-disk encryption format. LUKS volume header at offset 0 contains key slots (default 8), each holding an encrypted master key encrypted by a derived passphrase.

Tools:
- `cryptsetup luksDump <image>` — dumps the LUKS header (cipher, key size, master-key digest, key slot occupancy, PBKDF parameters)
- `cryptsetup luksOpen <image> name` — opens with passphrase
- After open, the decrypted volume is at `/dev/mapper/name`

LUKS2 (the current default on most distros) adds PBKDF2/Argon2id KDF options and JSON metadata. `hashcat` mode `-m 14600` handles LUKS1 passphrase cracking offline.

### 14.5 Hibernation Files as Crypto Bypass

`hiberfil.sys` (Windows) and `swap.img`/swap partitions (Linux) can contain a snapshot of memory taken when the system suspended. If full-disk encryption was unlocked at suspend time, the disk encryption keys are present in the hibernation file. Tools like `hibr2bin` (Comae) convert the hibernation file to a memory image, after which Volatility extracts keys.

## 15. Filesystem Timestamps — Full Reference

### 15.1 NTFS

Both `$STANDARD_INFORMATION` and `$FILE_NAME` hold four timestamps:
- Created (C)
- Modified (M)
- MFT-changed (E — entry modified)
- Accessed (A)

Precision: 100 nanoseconds (FILETIME — 64-bit count of 100ns intervals since 1601-01-01 UTC).

Update rules:
- Last access is *disabled by default* since Vista on NTFS (registry value `HKLM\SYSTEM\CurrentControlSet\Control\FileSystem\NtfsDisableLastAccessUpdate`).
- `$FN` updates only on filename operations.
- `$SI` updates on the corresponding operation, but `Modified` and `Accessed` may lag by an hour (last-access update bunches).

Tunneling: an obscure NTFS behavior where renaming-and-recreating a file within a short window (15 seconds by default) preserves the original $SI created time of the prior file with the same name. Used to be a problem for incident timelines; rare today but still possible.

### 15.2 FAT / FAT32 / exFAT

FAT directory entry timestamps:
- Create date + time (2-second precision)
- Last write date + time (2-second precision)
- Last access date (1-day precision; no time)

All timestamps are in local time (no timezone). exFAT adds a UTC offset field per timestamp.

### 15.3 ext4

- atime, mtime, ctime, crtime, dtime (in deleted inodes)
- Nanosecond precision since ext4
- `noatime` mount option disables atime updates; `relatime` updates only when mtime is newer than atime or atime is >24h old (the default on most distros)

### 15.4 HFS+

- Creation, Modification, Attribute-modification, Access, Backup
- 1-second precision

### 15.5 APFS

- create_time, mod_time, change_time, access_time
- Nanosecond precision

Combined with the time-zone reasoning needed (NTFS stores UTC; FAT stores local; many event sources mix), timestamps require deliberate handling. A common timeline error is mixing UTC and local across artifacts. Plaso's "system time zone" detection and `psort -z` flag handle this — but the analyst still has to think about it.

## 16. Hash Families

### 16.1 Cryptographic Hash Functions

- **MD5** (128-bit) — collision-broken (2004), preimage not yet broken. Still used for evidence-integrity (where collisions don't matter — you're not adversarial-checking but file-integrity-checking). Fast.
- **SHA-1** (160-bit) — collision-broken (2017 SHAttered, Google). Phased out but still common.
- **SHA-256** (256-bit) — SHA-2 family, considered strong. Standard for new evidence.
- **SHA-3** (Keccak) — different design family from SHA-2; no widespread use in forensic tooling beyond academic.

### 16.2 Fuzzy / Similarity Hashing

When two files differ by small amounts (a malicious binary repacked, a document with one paragraph changed), cryptographic hashes give completely different outputs. Fuzzy hashes preserve similarity.

**ssdeep** (CTPH — Context Triggered Piecewise Hashing) — Jesse Kornblum's algorithm. Computes a rolling hash, triggers a block boundary at hash-value milestones, then hashes each block with a small piecewise hash. Output: `blocksize:hash1:hash2`. Comparison: edit distance between hashes, percentage similarity. Useful for identifying near-identical files. Tooling: `ssdeep -r <directory>`.

Limitations: ssdeep is sensitive to the proportion of changed bytes; effective for ~30% or less change. Doesn't handle structurally-modified files (e.g., a different compiler output for the same source).

**TLSH** (Trend Micro Locality Sensitive Hash) — bucket-based statistical hash. More robust to large differences than ssdeep; designed for malware similarity. Output is a 70-character hex string. Better for clustering large malware corpora.

**SDHash** (Roussev) — feature-extraction-based; bloom-filter representation; supposedly more robust on highly variable inputs.

**imphash** (Mandiant) — for PE files specifically; hashes the import table. Two PE binaries built with the same imports (often a malware family) get the same imphash even if other content differs.

**ImpFuzzy** — fuzzy version of imphash combining ssdeep over the import table.

**Authentihash** — Microsoft Authenticode-defined hash that excludes the certificate region; used for code-signing verification.

When to use which:
- File integrity / chain of custody → SHA-256 (and MD5 alongside for legacy compatibility)
- Near-identical file detection across many systems → ssdeep
- Malware family clustering → TLSH or imphash
- PE file family identification → imphash
- Generic NSRL-style whitelist matching → SHA-1 (NSRL's stored hash) or SHA-256

NSRL (NIST National Software Reference Library) publishes a Reference Data Set (RDS) of hashes for known-good software (originally SHA-1 and MD5, with SHA-256 added). Filtering known-good before analysis is the canonical use — `hfind` (Sleuth Kit) plus the NSRL hashes is the typical setup.

---

# PART B — NETWORK FORENSICS

## 17. PCAP File Format

Packet capture files store network traffic captured at the link layer. Two main formats coexist.

### 17.1 libpcap (.pcap / .cap)

The original format, defined by libpcap (Wireshark's predecessor). Structure:
- Global file header (24 bytes): magic number, major/minor version, timezone offset, sigfigs, snaplen, link-layer type
- Per-packet record: timestamp seconds, timestamp microseconds, captured length, original length, packet data

Limitations:
- Microsecond timestamp precision (1 µs)
- One interface per file
- No metadata for the capture environment
- Endianness implicit in magic number

### 17.2 pcapng (.pcapng)

Modern format. Block-based:
- Section Header Block — file-level metadata
- Interface Description Block — per-interface metadata (link type, snaplen, hardware, OS)
- Enhanced Packet Block — packet with full metadata (timestamp with nanosecond resolution, comments, drop counts)
- Name Resolution Block — DNS / IP→name pairs captured during capture
- Interface Statistics Block — per-interface stats
- Custom Block — vendor extensions

Wireshark since 1.8 (2012) writes pcapng by default. tshark, dumpcap, tcpdump (recent versions) all support both formats. Pcapng is preferred for multi-interface captures, comments, nanosecond timestamps.

### 17.3 Capture Filters vs Display Filters

A core source of confusion. Both use different syntax.

**Capture filters** — BPF (Berkeley Packet Filter) syntax. Applied at kernel level during capture; packets not matching are never written to disk. Examples:
- `host 10.0.0.5`
- `port 53`
- `tcp port 443 and not host 192.168.1.1`
- `ether host aa:bb:cc:dd:ee:ff`
- `net 10.0.0.0/24`

Used by `tcpdump -i eth0 <filter>` and Wireshark's "Capture options" filter field.

**Display filters** — Wireshark's own syntax. Applied to already-captured packets. Examples:
- `ip.addr == 10.0.0.5`
- `dns.qry.name contains "evil"`
- `tcp.flags.syn == 1 and tcp.flags.ack == 0`
- `http.request.method == "POST"`
- `ssl.handshake.extensions_server_name == "example.com"`
- `frame.time > "2024-01-01 00:00:00"`

Display filters have access to every dissected protocol field. BPF capture filters are limited to a smaller set.

### 17.4 Pcap Manipulation Utilities

- `editcap` — slice, merge, deduplicate pcap files, convert formats, adjust timestamps
- `mergecap` — merge multiple pcaps
- `tcprewrite` — rewrite L2/L3/L4 headers in a pcap (used for replay testing)
- `tcpreplay` — replay a pcap onto a live interface
- `capinfos` — pcap metadata (capture start/end, packet count, link type)
- `randpkt` — generate random packets (testing)

## 18. tshark and tcpdump — Practical Syntax

### 18.1 tcpdump

The classic packet capture tool. Linux/BSD/macOS native.

```
tcpdump -i eth0                                  # live capture on eth0
tcpdump -r capture.pcap                          # read from file
tcpdump -w out.pcap                              # write to file
tcpdump -nn                                      # no name resolution (faster, deterministic)
tcpdump -X                                       # hex + ASCII payload
tcpdump -A                                       # ASCII only
tcpdump -s 0                                     # full packet capture (no snaplen)
tcpdump -c 100                                   # capture 100 packets and exit
tcpdump 'host 10.0.0.5 and port 443'             # BPF filter
tcpdump 'src host 10.0.0.5 and dst port 53'      # directional filter
tcpdump 'tcp[tcpflags] & (tcp-syn) != 0'         # SYN packets
tcpdump 'icmp[icmptype] == icmp-echo'            # ICMP echo requests
```

### 18.2 tshark

The CLI Wireshark. Heavier than tcpdump but with full Wireshark dissection.

```
tshark -r capture.pcap                                                                    # basic read
tshark -r capture.pcap -Y "http.request"                                                  # display filter
tshark -r capture.pcap -Y "ip.addr == 10.0.0.5" -T fields -e frame.time -e ip.src -e ip.dst -e http.host
tshark -r capture.pcap -z conv,ip                                                          # conversation summary by IP
tshark -r capture.pcap -z conv,tcp                                                         # conversation summary by TCP 4-tuple
tshark -r capture.pcap -z io,phs                                                           # protocol hierarchy
tshark -r capture.pcap -q -z http,tree                                                     # HTTP request tree
tshark -r capture.pcap -q -z dns,tree                                                      # DNS request tree
tshark -r capture.pcap --export-objects http,/tmp/out/                                     # extract HTTP objects (files)
tshark -r capture.pcap --export-objects smb,/tmp/out/                                      # extract SMB files
tshark -r capture.pcap -Y "tcp.stream eq 0" -T fields -e tcp.payload                        # one stream's payload
tshark -r capture.pcap -z follow,tcp,raw,0                                                  # follow TCP stream 0 raw
```

The `-T fields -e <field>` pattern is the workhorse for extracting structured data from a pcap. `-E header=y -E separator=,` makes it CSV-friendly.

### 18.3 Following Streams

In Wireshark, right-click → Follow → TCP Stream / UDP Stream / TLS Stream. Shows the reassembled application-layer conversation. Display filter set to `tcp.stream eq <N>` afterward, isolating that flow.

In tshark: `tshark -r in.pcap -z follow,tcp,ascii,0` for stream 0 in ASCII.

### 18.4 Time Range Filtering

```
tshark -r in.pcap -Y "frame.time >= \"2024-01-15 14:30:00\" and frame.time <= \"2024-01-15 14:45:00\""
editcap -A "2024-01-15 14:30:00" -B "2024-01-15 14:45:00" in.pcap out.pcap
```

`editcap`'s `-A`/`-B` is faster because it operates on records without full dissection.

## 19. Wireshark — Practitioner Mental Model

Wireshark is the GUI counterpart to tshark. Its statistical and visualization features are heavily used in IR.

### 19.1 Statistics → Conversations

Tabulates every L2/L3/L4 conversation seen: source-destination pair, packet count, byte count, duration. Tabs for Ethernet, IPv4, IPv6, TCP, UDP, etc. Right-click → Apply as Filter to drill in.

For IR, the IPv4 / TCP / UDP tabs are first stops:
- High-volume conversations to external IPs → possible exfil
- Many conversations to a few IPs → possible C2
- Long-duration low-byte conversations → possible beacon

### 19.2 Statistics → Endpoints

Per-host (single IP / MAC) statistics rather than pair. Useful for ranking which host is responsible for most traffic, which is reaching most distinct external hosts.

### 19.3 Statistics → IO Graphs

Plot packets-per-second, bytes-per-second, or filter-matched counts over time. Useful for spotting periodic traffic (beacons), exfil bursts, scan storms.

Multiple graphs can be overlaid — e.g., total DNS vs total HTTPS in 5-minute buckets reveals if DNS volume spikes during HTTPS quiet times (possible DNS tunneling).

### 19.4 Protocol Dissection Mental Model

Wireshark dissectors parse each layer in order: L2 (Ethernet, Wi-Fi) → L3 (IP) → L4 (TCP/UDP) → L7 (HTTP, DNS, TLS, SMB, ...). Each dissector exposes named fields (e.g., `dns.qry.name`, `http.request.uri`, `tls.handshake.ja3`). Display filter syntax targets these fields.

When a packet is selected, the bottom pane shows the byte breakdown by field — clicking a field highlights its bytes. This is how unknown protocols are reverse-engineered against documentation.

Dissectors can be enabled/disabled (Analyze → Enabled Protocols). Helpful when a port collides — e.g., a custom binary protocol on port 80 that Wireshark misidentifies as HTTP.

### 19.5 Expert Information

Analyze → Expert Information lists every "expert" finding from dissectors: retransmissions, dup-ACKs, out-of-order packets, malformed packets, suspect TCP behavior (zero window, keep-alive abuse). Categorized as Chat / Note / Warning / Error.

## 20. Zeek (formerly Bro)

Zeek is the dominant open-source network security monitoring (NSM) platform. It parses traffic into structured logs and runs a scripting language (Zeek script) for detection and analysis. Renamed from Bro to Zeek in 2018.

### 20.1 Architecture

Zeek has three layers:

**Event engine** — packet capture (libpcap or AF_PACKET) → protocol analyzers (HTTP, DNS, SSL, SSH, FTP, SMB, SMTP, MySQL, PostgreSQL, IRC, RDP, Kerberos, ...) → events emitted as named functions with typed arguments (e.g., `http_request(c: connection, method: string, uri: string, ...)`).

**Script layer** — Zeek scripts subscribe to events, accumulate state, emit logs, raise notices. The base scripts handle log generation; custom scripts implement detections.

**Logging framework** — events are written to log files (TSV by default; JSON with the appropriate script). Logs are rotated hourly by default (controlled by `Log::default_rotation_interval`).

Zeek deployments use the `zeekctl` (formerly `broctl`) tool for cluster management — manager, proxies, and workers running on multi-core / multi-host setups.

### 20.2 Scripts vs Logs

A common confusion: Zeek scripts produce logs, but the scripts themselves don't ship the logs anywhere — that's a separate concern (Logstash, Filebeat, Kafka, etc., usually).

The base scripts shipping with Zeek produce a fixed set of logs. Custom scripts can produce additional logs.

### 20.3 conn.log

The connection log — every flow (4-tuple over time) gets one entry. Fields:

| Field | Type | Meaning |
|---|---|---|
| ts | time | Connection start time |
| uid | string | Unique per-connection ID |
| id.orig_h | addr | Originating IP |
| id.orig_p | port | Originating port |
| id.resp_h | addr | Responder IP |
| id.resp_p | port | Responder port |
| proto | enum | TCP / UDP / ICMP |
| service | string | Identified application-layer protocol (http, dns, ssl, smb, ...) |
| duration | interval | Connection duration |
| orig_bytes | count | Bytes from originator (L7) |
| resp_bytes | count | Bytes from responder (L7) |
| conn_state | string | Connection state (S0, S1, SF, REJ, ...) |
| local_orig | bool | Originator local? |
| local_resp | bool | Responder local? |
| missed_bytes | count | Dropped/missed bytes |
| history | string | TCP history codes (S, A, D, F, R, ...) |
| orig_pkts | count | Pkts from originator |
| orig_ip_bytes | count | IP bytes from originator |
| resp_pkts | count | Pkts from responder |
| resp_ip_bytes | count | IP bytes from responder |
| tunnel_parents | set[string] | Parent tunnel uids if encapsulated |

`conn.log` is the spine of nearly every Zeek-based analysis.

### 20.4 http.log

| Field | Meaning |
|---|---|
| ts | request time |
| uid | connection uid (joins to conn.log) |
| id.* | 4-tuple |
| trans_depth | request number in pipelined sequence |
| method | GET, POST, etc. |
| host | Host header |
| uri | request URI |
| referrer | Referer header |
| user_agent | UA header |
| request_body_len | body bytes |
| response_body_len | body bytes |
| status_code | HTTP code |
| status_msg | reason phrase |
| info_code | first informational code (100, etc.) |
| tags | URI tags (uri-too-long, etc.) |
| username, password | basic auth credentials |
| proxied | proxy headers seen |
| orig_fuids, orig_filenames, orig_mime_types | file UIDs from request |
| resp_fuids, resp_filenames, resp_mime_types | file UIDs from response |

### 20.5 dns.log

| Field | Meaning |
|---|---|
| ts | query time |
| uid | conn uid |
| id.* | 4-tuple |
| proto | tcp/udp |
| trans_id | DNS transaction ID |
| query | query name |
| qclass, qclass_name | class |
| qtype, qtype_name | type (A, AAAA, MX, TXT, CNAME, ...) |
| rcode, rcode_name | response code (NOERROR, NXDOMAIN, ...) |
| AA, TC, RD, RA | flags |
| answers | answer list |
| TTLs | answer TTLs |
| rejected | did the responder reject? |

`dns.log` is the workhorse for DNS-based detection (tunneling, DGAs, fast-flux, NXDOMAIN bursts).

### 20.6 ssl.log

| Field | Meaning |
|---|---|
| ts | handshake start |
| uid | conn uid |
| id.* | 4-tuple |
| version | TLS version |
| cipher | negotiated cipher suite |
| curve | elliptic curve |
| server_name | SNI (Server Name Indication) |
| resumed | resumed session? |
| last_alert | alert if any |
| next_protocol | ALPN protocol |
| established | handshake completed? |
| cert_chain_fuids | cert file UIDs (link to files.log/x509.log) |
| client_cert_chain_fuids | client cert UIDs |
| subject | server cert subject |
| issuer | server cert issuer |
| client_subject | client cert subject |
| client_issuer | client cert issuer |
| ja3 | JA3 client fingerprint (with ja3 script) |
| ja3s | JA3S server fingerprint |

### 20.7 files.log

| Field | Meaning |
|---|---|
| ts | first seen |
| fuid | file UID |
| tx_hosts | transmitter IPs (set) |
| rx_hosts | receiver IPs (set) |
| conn_uids | conn uids |
| source | protocol source (HTTP, SMTP, FTP_DATA, ...) |
| depth | nested level |
| analyzers | analyzers run |
| mime_type | detected MIME type |
| filename | filename (where known) |
| duration | transfer duration |
| seen_bytes | bytes seen |
| total_bytes | claimed bytes |
| md5, sha1, sha256 | file hashes (with hash plugin) |

### 20.8 x509.log

| Field | Meaning |
|---|---|
| ts | first seen |
| id | cert fuid |
| certificate.version | X.509 version |
| certificate.serial | serial number |
| certificate.subject | subject DN |
| certificate.issuer | issuer DN |
| certificate.not_valid_before | validity start |
| certificate.not_valid_after | validity end |
| certificate.key_alg | key algorithm |
| certificate.sig_alg | signature algorithm |
| certificate.key_type | RSA, ECDSA, ... |
| certificate.key_length | bits |
| san.dns, san.uri, san.email, san.ip | SAN extensions |
| basic_constraints.ca | CA bit |
| basic_constraints.path_len | max path length |

### 20.9 notice.log

Generated by the Zeek Notice framework — scripts emit notices when a condition warrants alerting. Common notice types (controlled by scripts):
- `SSL::Invalid_Server_Cert`
- `HTTP::SQL_Injection_Attacker`
- `Scan::Port_Scan`
- `Scan::Address_Scan`
- `SSH::Login_From_Crowdstrike_Intel`
- `Intel::Notice` (any indicator hit)

Notices have severity, suppress windows, action handlers.

### 20.10 weird.log

Anomalies detected by Zeek's parsers: malformed packets, protocol violations, unexpected fields. Often the first hint of a misbehaving or evasive C2.

### 20.11 Other Common Logs

- `ssh.log` — SSH connection events (client/server software, auth attempt outcomes — though Zeek can't decrypt, it observes the handshake)
- `smb_files.log` / `smb_mapping.log` — SMB file access and share mappings
- `kerberos.log` — Kerberos ticket events
- `rdp.log` — RDP cookie, keyboard, RDPDR channel
- `dhcp.log` — DHCP transactions
- `ftp.log` — FTP commands
- `smtp.log` — SMTP transactions
- `irc.log` — IRC (still relevant: many older botnets used IRC)
- `dpd.log` — Dynamic Protocol Detection — when a port disagrees with the protocol observed
- `loaded_scripts.log` — runtime configuration audit
- `software.log` — software version detected from banners
- `tunnel.log` — tunneled flows (Teredo, AYIYA, IPv6-in-IPv4)
- `intel.log` — Intel framework hits (matched threat indicators)
- `signatures.log` — Zeek signature matches

## 21. Suricata

Suricata is the dominant open-source IDS / IPS / NSM, developed by OISF. Multi-threaded packet processing, rule-based detection, EVE JSON event output.

### 21.1 Architecture

Threads partition packets by flow (hash-based load balancing). Each thread:
1. Decode packet
2. Apply flow tracking, defrag, stream reassembly
3. Identify protocol via app-layer parser
4. Match against rules
5. Emit logs / alerts

Outputs: fast.log (legacy CSV), unified2 (binary, fading), EVE JSON (canonical modern format), packet log (PCAP of matched packets).

### 21.2 EVE JSON Output

`eve.json` is the standard output. One JSON object per line, with `event_type` field:
- `alert` — rule match
- `http` — HTTP transaction
- `dns` — DNS query/response
- `tls` — TLS handshake (with JA3/JA3S, certificate subject, SNI)
- `flow` — flow termination (similar to Zeek conn.log)
- `fileinfo` — file extracted
- `smb` — SMB transaction
- `ssh` — SSH handshake
- `ftp` — FTP command
- `smtp` — SMTP
- `anomaly` — protocol anomaly
- `stats` — periodic engine stats

The schema is documented at https://docs.suricata.io/en/latest/output/eve/eve-json-format.html.

### 21.3 Rule Format

```
action header (options)
```

Action: `alert`, `drop`, `pass`, `reject`.

Header: `protocol src_ip src_port -> dst_ip dst_port` (or `<>` for bidirectional). Variables `$HOME_NET`, `$EXTERNAL_NET`, `$HTTP_PORTS` defined in `suricata.yaml`.

Options (semicolon-separated `key:value;`):
- `msg:"..."` — alert message
- `sid:NNNN` — signature ID
- `rev:N` — revision
- `classtype:...` — classification (attempted-recon, trojan-activity, ...)
- `reference:...` — URL/CVE
- Content matches: `content:"..."`, `nocase`, `offset:N`, `depth:N`, `distance:N`, `within:N`
- Modifiers: `http_uri`, `http_header`, `http_method`, `dns_query`, `tls_sni`, `tls.cert_subject`, `ja3.hash`, `ja3s.hash`, `dotprefix`
- PCRE: `pcre:"/regex/Ui"`
- Flow: `flow:established,to_server`
- Threshold/limit: `threshold:type both, track by_src, count 5, seconds 60;`

Example rule:
```
alert tls $HOME_NET any -> $EXTERNAL_NET any (
  msg:"ET TROJAN Cobalt Strike Default Certificate";
  tls.cert_subject; content:"CN=Major Cobalt Strike";
  classtype:trojan-activity; sid:2027894; rev:1;
)
```

Ruleset sources: Emerging Threats Open (ET Open, free), ET Pro (commercial), Snort Subscriber Rule Set, custom organizational rules.

## 22. Snort — Historical Context

Snort, written by Martin Roesch in 1998, was the original open-source IDS. Single-threaded design eventually became the limiting factor as 10G/40G/100G links became common. Snort 3 (2021) addressed this with multi-threading and a new rule language, but Suricata had already captured the mindshare.

The rule format Suricata uses is descended from Snort's, and most ET Open rules work in both engines. In current practice:
- Suricata is the typical first choice for new deployments
- Snort 3 is in use where Cisco Talos rules (Snort Subscriber) are licensed
- Snort 2 is in maintenance mode and rare

The "Snort vs Suricata" debates of 2012-2018 are largely settled; both are competent engines with similar capability surfaces.

## 23. JA3 / JA3S — TLS Fingerprints

JA3 (Salesforce, 2017) is a TLS Client Hello fingerprint. The Client Hello contains client-controlled fields that vary by TLS library, library version, and configured cipher list. JA3 deterministically fingerprints those.

### 23.1 JA3 Construction

JA3 string format: `Version,Ciphers,Extensions,EllipticCurves,EllipticCurvePointFormats` — where each is a hyphen-separated list of numeric IDs from the Client Hello. Then MD5 of that string is the JA3 hash.

Worked example: a TLS 1.2 Client Hello with cipher list `[0xc02f, 0xc030, 0xcca9, ...]`, extensions `[0, 23, 65281, 10, 11, 35, ...]`, curves `[29, 23, 24, ...]`, point formats `[0]`, version 771.

String: `771,49199-49200-52393-...,0-23-65281-10-11-35-...,29-23-24-...,0`

JA3 hash: MD5 of that string.

### 23.2 What Changes JA3

- TLS library (OpenSSL vs Schannel vs NSS vs Go's crypto/tls vs BoringSSL)
- Library version
- Application configuration (which ciphers/extensions explicitly enabled or disabled)
- ALPN list (extension 16) — though ALPN content is in the extension data, the extension ID's presence is captured
- Cipher list order (matters)

A given browser version on a given OS has a stable JA3. Common JA3s:
- Chrome on Windows
- Firefox on Linux
- curl with default OpenSSL
- Python requests/urllib3 (the Python-default JA3 is a well-known one)
- Go programs (`net/http` default)
- Cobalt Strike default profile
- Sliver default profile
- Empire-style PowerShell stagers

### 23.3 JA3S

JA3S is the server-side counterpart: Server Hello's TLS version + cipher chosen + extensions list. Hashed the same way. Used in combination, a `JA3 + JA3S` pair identifies a client-server stack precisely.

### 23.4 Practical Use and Caveats

JA3 alone is not high-fidelity for detection — many benign apps share a JA3, and TLS libraries upgrade (causing JA3 drift). JA3 in combination with destination, SNI, and JA3S is much more useful.

JA3 is included in modern Zeek (`ssl.log.ja3` with the `policy/protocols/ssl/ja3.zeek` script enabled), Suricata (`tls.ja3.hash`), Wireshark (`tls.handshake.ja3`).

**JA4** (FoxIO, 2023) is a newer variant designed to be human-readable, version-prefixed, more robust to library upgrades. JA4 is gaining adoption but JA3 is still dominant in published threat intel.

## 24. RITA — Beacon Detection

RITA (Real Intelligence Threat Analytics, Active Countermeasures) is an open-source tool specifically for finding C2 beacons in Zeek logs. The original RITA was MongoDB-based; the rewrite "RITA 2" / RITAv5 uses a standalone binary with no external database.

### 24.1 Methodology

RITA ingests Zeek `conn.log` (and ancillary logs) and runs analyses targeting C2 patterns:

**Beacon analysis** — for each (source, destination) pair with N or more connections, computes:
- Connection count
- Average interval between connections (timing periodicity)
- Coefficient of variation in interval (jitter)
- Average byte size (per request)
- Coefficient of variation in byte size
- Score combining periodicity strength and byte-size strength

Pairs with high score (>0.9, configurable) are flagged. The principle: human-driven communications have wide jitter and varying byte sizes; automated beacons are tighter on both even when randomized.

**Long-connection analysis** — identifies single connections lasting longer than a threshold (default 1 hour). Useful for tunneled C2 (SSH, custom protocols).

**DNS analysis** — flags hosts making queries for unusually high counts of subdomains under one apex (DNS-over-subdomain exfil/C2) and hosts making queries for many distinct domains in tight windows.

**Strobe analysis** — identifies pairs with many connections in a short window (signs of automation).

**Blacklist hits** — IPs/domains matched against intel feeds.

### 24.2 Output

CLI tables for each analysis. Score thresholds adjustable. Modern RITA outputs JSON for downstream integration.

The principal value of RITA is that the underlying math (top-N IP frequency × jitter × byte-size variance) is already implemented. A practitioner can compute their own if they want; RITA saves the effort.

## 25. NetworkMiner

NetworkMiner (Netresec) is a Windows-native tool (with Linux Mono support) that processes pcaps into "host views" and extracts artifacts. Two key features:

**Host view** — per-host page with hostname, MAC, IP, OS guesses (passive OS fingerprinting via TCP/IP stack), open ports observed, sessions, files transferred, credentials seen, parameters in HTTP, DNS queries.

**File extraction** — reassembles files transferred via HTTP, FTP, SMB, SMTP, TFTP, POP3, IMAP. Saves to disk with original filenames. Computes hashes. Optional VirusTotal lookup.

NetworkMiner is mostly used as a complement to Wireshark when artifact-extraction is the goal, not packet-level inspection. The free edition is sufficient for most IR; Professional adds OS fingerprinting depth, PCAP-over-IP, and some report generation.

`tshark --export-objects` provides equivalent file-extraction in CLI form for HTTP, SMB, IMF, DICOM, TFTP.

## 26. Beacon Detection Theory

C2 traffic patterns share characteristics regardless of the specific C2 framework:

**Periodicity** — beacons phone home on a schedule. Even with jitter, the average interval is statistically tighter than human-driven traffic.

**Jitter** — randomization around the average to thwart simple period-detectors. Cobalt Strike's `sleep` and `jitter` options literally configure this. Typical jitter values: 0% (rare; trivially detectable), 25% (common), 50% (default-ish in some kits). Beyond ~80% jitter, the period blurs and analytics need other features.

**Dwell time / connection duration** — most beacons are brief HTTP POSTs (a few hundred ms). Long-poll or tunneled C2 holds longer.

**Byte-size cadence** — beacon "check-in" payloads are small and uniformly small when there's no command. The variance is what stands out: human traffic byte-size variance is large; beacon variance is small.

**Mathematical formulation:**
- Inter-arrival time series: `[t1, t2, t3, ...]`
- `mean(t)`, `stddev(t)`, `CV(t) = stddev/mean` — low CV implies periodicity
- FFT or autocorrelation on the time series reveals fundamental frequencies
- Combined score: `(1 - CV_time) * (1 - CV_bytes) * log(connection_count)` — high score = periodic + uniform size + many connections

**Window size** — needed before detection works. Short windows (a few hours) miss long-interval beacons (1+ hour sleep). Long windows (days) increase chance of intervening user activity blurring the pattern. Production deployments often run multiple time windows in parallel.

**Caveats** — legitimate beacons exist: telemetry, software update checks, anti-virus signature pulls, OCSP requests, NTP. Any production detector needs a whitelist of expected periodic traffic. The pattern is necessary but not sufficient evidence.

## 27. DNS Exfil Detection

DNS over UDP is permitted from almost every network to almost every recursive resolver. Adversaries exploit this by encoding data in subdomains, querying `<encoded>.attacker.com`, and the authoritative DNS at attacker.com receives the data via the query log.

### 27.1 Indicators

**High-entropy subdomains** — base32/64-encoded data looks like high-entropy gibberish. Shannon entropy of subdomain labels:
- Normal subdomains: low entropy (`api`, `mail`, `www`)
- DGAs and encoded data: high entropy (`y2dnt5fghkqr7zwa`)
- Threshold around 3.5 bits/char is a reasonable starting point

**Long subdomain labels** — DNS labels can be up to 63 characters. Encoded data tends toward the max. Normal subdomains rarely exceed 20.

**Many queries to one apex domain** — exfil splits payloads across queries. A burst of 100+ queries to subdomains of one apex from one host in a minute is anomalous.

**TXT record abuse** — TXT can return arbitrary text up to 255 bytes per string, multiple strings per record. Used both for outbound (very rarely; the query carries data) and inbound (response is the C2 command). DNSExfiltrator, dnscat2, and Iodine all exploit TXT/NULL/CNAME.

**NULL records** — RFC 1035 NULL record (type 10) returns up to 65535 bytes. Iodine uses these. Almost no legitimate use.

**CNAME chains** — long CNAME chains can carry data. Less common than TXT/NULL.

**A-record abuse** — IPv4 address encodes 4 bytes. Each subdomain query returns 4 bytes of command. Slow but stealthy.

### 27.2 Base Encoding Patterns

- Base32 alphabet: `A-Z2-7=` (DNS-label-safe — case-insensitive; padded with `=` if required)
- Base64 alphabet: `A-Za-z0-9+/=` (NOT DNS-safe due to `+` and `/`; modified URL-safe variants substitute `-` and `_`)
- Base32hex: alternative base32 with `0-9A-V` characters
- Hex: `0-9a-f`

Detecting base32 in subdomain labels: regex `^[A-Z2-7]{16,}$` (uppercase) or case-insensitive variant. Detecting base64: presence of `-_` mixed with letters/digits in a long label.

### 27.3 Tooling

- **dnscat2** — encrypted DNS C2 tunnel (Ron Bowes). Distinctive query patterns: TXT records, MX records, CNAME chains.
- **Iodine** — IP-over-DNS tunnel. Uses NULL records primarily. High volume.
- **DNSExfiltrator** — exfil tool by Arno0x. POSTs files via subdomain encoding.
- **Cobalt Strike DNS C2** — TXT/CNAME/A modes; `mode dns-txt` typical.
- **PyExfil**, **DET** — generic exfil frameworks supporting DNS.

### 27.4 Detection Tools

- Zeek `dns.log` — query volume by source/apex
- RITA DNS analysis — top-N query targets, exfil scoring
- Suricata DNS rules — patterns over `dns.query`
- Spamhaus / NXDOMAIN baselines — sudden NXDOMAIN bursts from one host hint at DGAs

## 28. C2 Framework Traffic Signatures

Recognizing C2 frameworks by traffic patterns is a core capability.

### 28.1 Cobalt Strike

The single most-encountered C2 framework in IR. Default behaviors:

- **HTTPS beacon** — defaults to GET to a checkin URI like `/login`, `/api/getit`, `/admin/get.php` (varies by Malleable profile). POST for tasking. Default profile has identifiable URIs; serious operators use custom Malleable C2 profiles to mimic legitimate traffic.
- **DNS beacon** — TXT/A records to subdomains of the C2 domain. Default beacon DNS pattern queries `<hex>.<c2_domain>`.
- **SMB beacon** — named pipe `\\.\pipe\msagent_<random>` or similar; lateral pivot inside a network.
- **HTTP/S server self-signed cert** — many older defaults: CN `Major Cobalt Strike` with specific OID; detectable via SSL/TLS rules.
- **JA3 signatures** — Cobalt Strike's Java-based teamserver has known JA3s.
- **Stager** — beacon stager (~100-200 bytes) requests `/<8-char-checksum>`.
- **HTTP user-agent** — default profile uses `Mozilla/5.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/5.0; ...)` style — varies.
- **Payload format** — beacon traffic is encrypted; defaults to AES with a key established at handshake.

Reference IOCs: ET ruleset has hundreds of CS-specific rules; Did Cobalt Strike Just Talk To Me? (Florian Roth / etc.) catalogs profile signatures.

### 28.2 Empire

PowerShell-based C2, historical (mainline Empire is archived; forks like Empire 4.0 / Starkiller persist). Traffic:
- HTTP GET to `/login/process.php`, `/admin/get.php`, `/news.php` (default profile URIs)
- User-agent default: `Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko`
- POSTs with base64-encoded payloads in body
- Session cookie pattern

### 28.3 Sliver

Go-based C2 (BishopFox), gaining popularity. Traffic:
- HTTPS by default, with multiple protocols available (HTTP, mTLS, DNS, WireGuard)
- JA3 signature distinct (Go's crypto/tls fingerprint with Sliver's options)
- Certificate defaults: self-signed or LetsEncrypt
- Beacon mode similar timing to CS

### 28.4 Mythic

Go-based C2 framework (Cody Thomas / SpecterOps), modular agent design. Multiple agents (Apollo for .NET, Poseidon for Go, Athena, etc.) each with their own traffic signature. Mythic itself is the framework; the agent determines what shows up in traffic. Mythic's strength is configurability — operators often build custom profiles.

### 28.5 Metasploit Meterpreter

The classic. Default reverse_https payload uses HTTPS with a checkin URI pattern `/<4-byte-random>` and POST body containing the encrypted command channel. JA3 of Meterpreter is well-known. Legacy but still common in lower-end engagements.

### 28.6 Other Frameworks Worth Knowing

- **Brute Ratel** (commercial, license-locked; leaked variants in the wild)
- **Havoc** (Open-source; gaining traction as a CS replacement)
- **NimPlant** (Nim-based; smaller footprint, less-known JA3)
- **PoshC2** (PowerShell, similar to Empire)
- **Merlin** (Go, HTTP/2 focused)
- **Covenant** (.NET, Roselle-style web UI)

## 29. Tunneled C2

Adversaries hide C2 inside legitimate protocols to bypass deep-packet-inspection assumptions.

### 29.1 DNS over HTTPS (DoH)

DNS queries tunneled through HTTPS to `https://<resolver>/dns-query`. Standard resolvers: Cloudflare (`1.1.1.1`), Google (`8.8.8.8`), Quad9 (`9.9.9.9`), Mozilla / NextDNS. C2 over DoH means traditional DNS-log-based detection (Zeek `dns.log`) misses everything — DoH traffic appears as ordinary HTTPS to one of these resolvers.

Indicators: a host generating consistent HTTPS to a known DoH endpoint at near-DNS-frequency (every few seconds), with small consistent payloads. The TLS-level fingerprint (JA3) might point to a non-browser client.

### 29.2 HTTP/S CONNECT Abuse

The HTTP CONNECT method establishes a TCP tunnel through a proxy. Legitimately used for HTTPS-through-proxy. Abusable: an attacker-controlled "proxy" accepts CONNECT to anywhere, becoming a passthrough.

In a Zeek `http.log`, CONNECT requests are recorded. High volume from one host to one external proxy is suspect.

### 29.3 Tor

Tor traffic recognition has two angles:

**Entry-node lookups** — Tor publishes its consensus, including all entry guards. Matching destination IPs against the Tor consensus identifies Tor users.

**Relay fingerprints** — Tor traffic has characteristic TLS:
- Certificate subject patterns: random-looking common names `www.<random>.com`
- Cipher / extension lists characteristic of Tor's tls library
- JA3 of Tor browser distinct from regular browsers

Tools: ET ruleset includes Tor exit-node lists; `bro/zeek-tor-detector` scripts; CIRCL's tor-tracker.

Tor's pluggable transports (obfs4, meek) are designed to evade fingerprinting. obfs4 traffic looks like random bytes over TCP — high entropy, no protocol fingerprint. meek tunnels through HTTPS to a fronting CDN (e.g., Azure, CloudFront) which then forwards to the bridge.

### 29.4 SSH Tunneling

`ssh -D` (SOCKS proxy), `ssh -L` (local port forward), `ssh -R` (remote port forward). SSH traffic is encrypted at L4; from outside, all you see is the SSH handshake and a stream of opaque bytes. Indicators:
- Long-lived SSH connections from internal to external (unusual direction)
- High byte volume on SSH sessions
- SSH client version banners that don't match expected internal tooling

### 29.5 ICMP Tunneling

Ping payload abuse — ICMP echo with attacker data in the payload. Older technique (Loki, ptunnel). Modern detection: unusually large ICMP packets, ICMP volume from one source above baseline, ICMP payloads with high entropy.

## 30. SSL/TLS Forensics

### 30.1 Cert SAN Mismatches

A TLS server cert lists SANs (Subject Alternative Names). If the visited hostname (SNI / Host header) doesn't appear in any SAN, the connection should fail — but C2 with self-signed certs often skips this check. Forensically, a connection to a server whose cert SAN says `localhost` or `example.com` while the SNI says `microsoft-update.com` is suspect.

### 30.2 JA3 Anomalies

JA3 inconsistencies relative to user-agent: a request with user-agent claiming Chrome on Windows but JA3 matching Python's urllib3 means the user-agent is forged. This is a common detection pattern.

### 30.3 Self-Signed Leaf Certs on Public Endpoints

For server certs presented by external hosts, a self-signed leaf (issuer == subject) outside the trusted CA system is highly anomalous in 2024+ (Let's Encrypt is free). Common in malware C2 stood up quickly.

### 30.4 Cert Subject Patterns

Cobalt Strike default subject: `CN=Major Cobalt Strike` or single-letter org / org unit fields. Many older Metasploit defaults: `CN=localhost`. Suricata rules on these patterns catch lazy operators.

### 30.5 Certificate Transparency

CT logs (Google Argon, Cloudflare Nimbus, etc.) record every cert issued by participating CAs. Tools like `crt.sh` lookup historical certs for a domain. Useful retroactively for adversary infrastructure mapping — find all certs ever issued for `*.evil.com`, pivot on shared issuance patterns.

### 30.6 TLS 1.3 vs 1.2 Forensics Note

TLS 1.3 encrypts the certificate exchange — the server cert is sent inside an encrypted record, not in cleartext. This breaks the JA3S signature of the cert content and breaks cert-based inspection at the network sensor. JA3 (Client Hello) is still cleartext. SNI is also still cleartext in 1.3 unless ECH (Encrypted Client Hello) is in use — ECH adoption is still limited but growing.

## 31. NetFlow / IPFIX / sFlow

When full packet capture is impractical (multi-Gbps backbones, multi-TB/day volumes), flow records summarize traffic.

### 31.1 NetFlow

Cisco-originated. Versions:
- **v5** — fixed-format records: 5-tuple (src/dst IP, ports, protocol), packets, bytes, start/end time, TCP flags, AS numbers, next-hop, ToS
- **v9** — template-based, extensible
- **v10 (IPFIX)** — IETF standard derived from v9

A flow record represents a unidirectional sequence of packets sharing the 5-tuple, terminated by inactivity timeout, connection FIN/RST, or active timeout (typically 30 minutes).

### 31.2 IPFIX

The standard formalization of NetFlow v9. Supports more fields (TCP flags, packet length histograms, HTTP host, DNS query, etc., depending on exporter). JSON variants exist.

### 31.3 sFlow

Sampled flow — exports every Nth packet (with N typically 1000+). Statistically representative for high-throughput analytics; not useful for IR.

### 31.4 Practitioner Tools

- **SiLK** (CERT NetSA) — NetFlow analytic tooling: `rwfilter`, `rwcount`, `rwsetbuild`. Designed for large-scale flow corpus analytics.
- **nfdump / nfcapd** — Linux-native NetFlow collector and query tool
- **Argus** — flow generator + analytics, generates own flow records from raw pcap or live traffic
- **Elastiflow** — Elasticsearch-based NetFlow viewer (commercial / free tiers)

Flow records lack payload, so URI / domain / hash detection isn't possible from flow alone. But flow volume analytics (top talkers, anomalous destinations, beacon-period detection on flow inter-arrival) are quite usable. RITA's beacon detection works on flow records when full pcap isn't available.

---

# PART C — LOG ANALYSIS

## 32. Windows Event Log Architecture

Since Vista / 2008 the Windows Event Log is a separately-architected service from the legacy NT Event Log. The new system supports channels, providers, manifests, and the binary `.evtx` format.

### 32.1 Channels

A channel is a named log destination. There are four types:
- **Admin** — events for administrators (e.g., `Application`, `System`, `Security`)
- **Operational** — events for IT pros (e.g., `Microsoft-Windows-PowerShell/Operational`)
- **Analytic** — high-volume diagnostic events (disabled by default)
- **Debug** — developer-targeted events (disabled by default)

Standard system channels:
- `Application`
- `Security`
- `System`
- `Setup`
- `ForwardedEvents` (events forwarded from other machines)

Each application or component can register its own channels — `Microsoft-Windows-Sysmon/Operational`, `Microsoft-Windows-PowerShell/Operational`, `Microsoft-Windows-WMI-Activity/Operational`, etc.

Channels live as `.evtx` files at `%SystemRoot%\System32\winevt\Logs\`. The naming convention turns `/` into `%4` — so `Microsoft-Windows-PowerShell/Operational` becomes `Microsoft-Windows-PowerShell%4Operational.evtx`.

### 32.2 Providers

A provider is the source of events — a DLL/EXE that emits events through `EventWrite`. Providers register against channels; the registration says which channel each event goes to and which events the provider can emit.

Each provider has a GUID and a friendly name. The provider's events are described by a manifest (XML) bundled with the provider binary.

### 32.3 Manifests

A provider manifest declares:
- Provider name, GUID
- Channels it writes to
- Event definitions (ID, version, level, opcode, task, keywords)
- Template definitions (the structured data payload schema for each event)
- Localization strings

`wevtutil ep` lists registered providers; `wevtutil gp <provider>` dumps the manifest.

### 32.4 .evtx Binary Format

The .evtx file is a binary XML format optimized for write performance and partial reading. Structure:
- File header (4096 bytes, including magic `ElfFile`)
- Chunks (64 KB each), each holding:
  - Chunk header (CRC, first/last record IDs, etc.)
  - String table (deduplication for strings within the chunk)
  - Template table (deduplication for event schemas)
  - Records: timestamp + EventRecordID + serialized BinaryXML

The binary XML refers to templates and strings by table index, so a serialized event is small. Full event reconstruction requires the templates table from the chunk.

The format is documented by Joachim Metz (libevtx) and Andreas Schuster ("Windows Event Log Format").

### 32.5 Tools

**EvtxLogReader** — Microsoft's official `wevtutil`. Read with `wevtutil qe <channel> /q:<XPath> /f:text` for filtering. Limited XPath support but built-in.

**Get-WinEvent** (PowerShell) — query with `-FilterHashtable @{LogName='Security'; Id=4624; StartTime=...}` or `-FilterXPath`. Built-in, slow on large logs.

**EvtxECmd** (Eric Zimmerman) — fast .evtx parser, produces CSV/JSON. Supports custom maps that label events with MITRE techniques and human-readable descriptions. Single binary, designed for offline forensic work. The community-maintained map files (`EvtxECmd\Maps\`) cover hundreds of events.

**libevtx / evtxparse.py / pyevtx** — Joachim Metz's library; pyevtx the Python binding. Lower-level than EvtxECmd; useful for custom parsers.

**Hayabusa / Chainsaw** — see Sections 47-48; built on libevtx-style parsing with Sigma rule engines.

**LogParser** (Microsoft, older) — pre-Vista era, still works on .evtx. SQL-like syntax.

### 32.6 Subscriptions and Forwarding

Windows Event Forwarding (WEF) pushes selected events from many endpoints to a central collector via WS-Management. Useful for centralized log collection without a heavy agent. Events arrive on the collector's `ForwardedEvents` channel.

WEC (Windows Event Collector) is the collector role. Microsoft Sentinel, Splunk, Elastic all have ingestion paths for WEF-collected logs.

## 33. Security Event ID Reference (Full)

The Security channel is the canonical authentication / authorization audit log. Every IR engagement involves these IDs. Each requires the corresponding audit policy enabled (via `secpol.msc` → Advanced Audit Policy Configuration, or GPO).

### 33.1 4624 — Account Logon

Generated when a user successfully logs on. The most consulted Security event ID.

Key fields:
- `SubjectUserSid`, `SubjectUserName`, `SubjectLogonId` — context account (often SYSTEM if the event represents a network logon initiating)
- `TargetUserSid`, `TargetUserName`, `TargetDomainName` — the account that logged on
- `TargetLogonId` — unique session ID (joins to 4634 logoff and to many subsequent events in the session)
- `LogonType` — see table below
- `LogonProcessName` — `User32`, `NtLmSsp`, `Kerberos`, `Advapi`, `Negotiat`, `Schedule`, ...
- `AuthenticationPackageName` — `NTLM`, `Kerberos`, `Negotiate`
- `WorkstationName` — source workstation (NetBIOS name; empty for local)
- `LogonGuid` — Kerberos TGT GUID (correlates Kerberos events)
- `TransmittedServices`, `LmPackageName`, `KeyLength`
- `ProcessId`, `ProcessName` — process that issued LogonUser
- `IpAddress`, `IpPort` — source IP/port (for network logon)
- `ImpersonationLevel` — None, Identification, Impersonation, Delegation
- `RestrictedAdminMode` — RDP RestrictedAdmin used?
- `TargetOutboundUserName`, `TargetOutboundDomainName` — for tiered scenarios
- `VirtualAccount`, `TargetLinkedLogonId`, `ElevatedToken` — UAC-related

#### Logon Types

| LogonType | Name | Description |
|---|---|---|
| 2 | Interactive | Console logon (sitting at the keyboard) |
| 3 | Network | Connection from network (SMB, RPC over TCP) |
| 4 | Batch | Scheduled task run |
| 5 | Service | Service starting under an account |
| 7 | Unlock | Workstation unlock after lock |
| 8 | NetworkCleartext | Network logon with cleartext password (basic auth, IIS) |
| 9 | NewCredentials | RunAs with /netonly (different network credentials) |
| 10 | RemoteInteractive | RDP / Terminal Services |
| 11 | CachedInteractive | Interactive logon with cached credentials (offline DC) |
| 12 | CachedRemoteInteractive | Cached + RDP (rare) |
| 13 | CachedUnlock | Unlock with cached creds |

In IR:
- **Type 3 from external IP** to a non-server host → likely lateral movement (SMB, RDP RPC layer)
- **Type 10 from external IP** to any host → likely RDP attack
- **Type 9** appears with `runas /netonly` and overpass-the-hash; often suspicious
- **Type 4** for an unexpected scheduled task → persistence
- **Type 5** for a new service install → persistence (correlate with 7045)

### 33.2 4625 — Failed Logon

Failed authentication attempt. Same fields as 4624 plus:
- `Status`, `SubStatus` — NTSTATUS codes describing the failure reason. Notable values:
  - `0xC0000064` — username does not exist
  - `0xC000006A` — bad password
  - `0xC000006D` — bad username or auth info
  - `0xC000006E` — account restriction (logon hours, expired)
  - `0xC000006F` — outside allowed logon hours
  - `0xC0000070` — workstation restriction
  - `0xC0000071` — password expired
  - `0xC0000072` — account disabled
  - `0xC000015B` — logon type not granted
  - `0xC0000133` — clock skew (Kerberos)
  - `0xC0000193` — account expired
  - `0xC0000224` — must change password
  - `0xC0000234` — account locked out

Bursts of 4625 with `bad password` status are password spray / brute force; with `username does not exist` they're enumeration; with `account disabled` they often hit former-employee credentials.

### 33.3 4634 — Logoff

Account logoff. Joins to 4624 via `TargetLogonId`. Used to compute session duration. Note: many logons (especially service / network) don't produce matched 4634 — the session ends in process termination, not explicit logoff. Use 4647 (user-initiated logoff) for clean interactive session bounds.

### 33.4 4647 — User-Initiated Logoff

Interactive user logged off voluntarily. Cleaner bound than 4634 for type 2/10 sessions.

### 33.5 4648 — Logon Using Explicit Credentials

Generated when a process specifies credentials explicitly (`runas /user:OTHER`, scheduled task with stored credentials, `net use \\host /user:OTHER`, mstsc with stored credentials).

Fields:
- `SubjectUserSid` — current process owner
- `TargetUserName` — credentials used
- `TargetServerName` — target host (or "localhost")
- `ProcessName` — calling process

4648 is one of the cleanest indicators of pivot attempts and of `runas`-based privilege use. Adversaries pivoting laterally via PsExec / WMI / SMB with alternate credentials trip 4648 on the source.

### 33.6 4672 — Special Privileges Assigned to New Logon

A logon was granted one or more sensitive privileges:
- SeAssignPrimaryTokenPrivilege
- SeBackupPrivilege
- SeCreateTokenPrivilege
- SeDebugPrivilege
- SeImpersonatePrivilege
- SeLoadDriverPrivilege
- SeRestorePrivilege
- SeSecurityPrivilege
- SeSystemEnvironmentPrivilege
- SeTakeOwnershipPrivilege
- SeTcbPrivilege

4672 fires alongside 4624 for administrator-equivalent logons. Frequent in normal operations, but combined with the right context (anomalous user, off-hours, unusual host) it's high-value.

### 33.7 4673 / 4674 — Privileged Service Called / Operation on Privileged Object

4673 — a privileged system service was called (e.g., `SeAuditPrivilege` invoked). 4674 — an operation was attempted on a privileged object. Both produce massive volume and are typically disabled or filtered.

### 33.8 4688 — Process Creation

A process was created. The single most important Sysmon-like event from the Security channel.

Default fields:
- `NewProcessId`, `NewProcessName`, `CommandLine` (only if Audit Process Command Line GPO is enabled)
- `TokenElevationType` (`%%1936` Default/Limited/Full)
- `MandatoryLabel` — integrity level SID
- `CreatorProcessId`, `CreatorProcessName`, `ParentProcessName`
- `TargetUserSid`, `TargetDomainName`, `TargetLogonId`
- `SubjectUserSid` (creator), `SubjectUserName`, `SubjectLogonId`

By default the command line is NOT recorded. To capture it, enable `Computer Configuration → Administrative Templates → System → Audit Process Creation → Include command line in process creation events`. Without this, 4688 events are missing the most useful field for IR.

4688 is heavily duplicative with Sysmon Event ID 1 (process create) when both are enabled. Sysmon's version is richer: includes hash, parent command line, user, original filename. Where Sysmon isn't deployed, 4688 with command line audit is the baseline.

### 33.9 4697 — Service Installed

A new service was installed in the system. Fields:
- `ServiceName`
- `ServiceFileName` — binary path and command line
- `ServiceType` — kernel driver, file system driver, own process, share process, interactive
- `ServiceStartType` — boot, system, auto, on-demand, disabled
- `ServiceAccount` — LocalSystem, NetworkService, LocalService, or user

Reported on both DC (for installs there) and member servers. System log 7045 reports the same event from a different angle — both fire for most service installs. Persistence implant: `4697` of a service named `svchost` running from `C:\Users\<user>\AppData\Local\Temp\<random>.exe`.

### 33.10 4698 — Scheduled Task Created

A new scheduled task was created on the system. Fields:
- `TaskName`
- `TaskContent` — full XML of the task definition

The XML reveals trigger (boot, logon, time, event), action (binary + args), principal (which account runs it), conditions. Persistence: an attacker who creates `\Microsoft\Windows\<existing>\<new task>` to hide among legitimate Microsoft tasks; the XML shows the actual action.

### 33.11 4702 — Scheduled Task Updated

A scheduled task was modified. Similar payload to 4698. Common with attackers modifying existing tasks (`\Microsoft\Windows\Wininet\CacheTask` is a real example used in the wild).

Other task events (less common): 4699 (deleted), 4700 (enabled), 4701 (disabled).

### 33.12 4720 — User Account Created

Local SAM user created (on a workstation/server) or domain user created (on a DC). Fields: target name, SID, attributes.

### 33.13 4722 — User Account Enabled

A disabled account was enabled.

### 33.14 4723 — Password Changed

A user changed their own password (must succeed for 4723; failures produce 4724).

### 33.15 4724 — Password Reset Attempt

An admin reset a user's password. Distinct from 4723 (own password change). Highly auditable — kerberoasting prep, account takeover, etc.

### 33.16 4725 — User Account Disabled

### 33.17 4732 — Member Added to Security-Enabled Local Group

A user was added to a local group. The "Administrators" local group is the canonical target — adding a domain user to local Administrators on a server is a privilege escalation persistence step.

Fields: target group SID/name, member SID/name, who did it.

### 33.18 4756 — Member Added to Security-Enabled Universal Group

Same idea, universal group (which exists across the forest). Domain Admins, Enterprise Admins, Schema Admins are universal groups.

Related: 4728 (member added to global group), 4757 (universal removed), 4729 (global removed), 4733 (local removed).

### 33.19 4738 — User Account Changed

A user account property changed. Many sub-categories: password change, account expiry, primary group, name, UPN. Used together with 4740 to detect lockout-induced changes.

### 33.20 4740 — User Account Locked Out

The account was locked out due to too many failed logons. Generated on the DC for domain accounts. The `CallerComputerName` field tells where the failed attempts originated — useful for attributing brute force to specific hosts.

### 33.21 4768 — Kerberos TGT Requested (AS-REQ)

A TGT (Ticket Granting Ticket) was requested. Generated on DCs.

Fields:
- `TargetUserName` — the requesting account
- `ServiceName` — usually `krbtgt`
- `IpAddress`, `IpPort` — source
- `TicketEncryptionType` — `0x17` (RC4), `0x12` (AES256), `0x11` (AES128). RC4 has historically been the kerberoast / AS-REP-roast target.
- `PreAuthType` — `2` (encrypted timestamp), `0` (none — AS-REP roastable accounts)
- `Status`, `FailureCode` — Kerberos error codes

4768 with `PreAuthType=0` indicates AS-REP roasting precondition (account has `Do not require Kerberos preauthentication` set).

### 33.22 4769 — Kerberos Service Ticket Requested (TGS-REQ)

A service ticket was requested. The canonical kerberoasting event.

Fields:
- `TargetUserName` — the requesting user
- `ServiceName` — the SPN (e.g., `MSSQLSvc/db01.corp.local:1433`) of the target service account
- `ServiceSid` — SID of the service account
- `TicketEncryptionType` — `0x17` (RC4) is the kerberoast indicator
- `IpAddress`

Kerberoasting fingerprint: many 4769s from one source IP requesting many different SPNs with RC4 encryption type. Suspect SPNs include those of service accounts with weak passwords.

### 33.23 4771 — Kerberos Pre-Authentication Failed

The TGT request failed pre-auth (bad password). FailureCode `0x18` = wrong password — equivalent to 4625 for Kerberos. Bursts indicate Kerberos brute force / password spray against DCs.

### 33.24 4776 — NTLM Authentication

The domain controller validated an NTLM credential. Fields:
- `TargetUserName`
- `WorkstationName` — the requesting host
- `Status` — `0x0` (success) or various failure codes

NTLM authentication going to the DC means a downstream service used NTLM (rather than Kerberos). Common in Windows authentication chains for older services or for LM-fallback scenarios. Pass-the-hash leverages NTLM — 4776 captures the validation.

### 33.25 5140 — Network Share Accessed

A user accessed a share. Fields: shared resource, share name, share path, source IP. Generated on the server hosting the share.

Heavy 5140 from one user to many shares = file-share enumeration.

### 33.26 5145 — Detailed File Share Access

Detailed object access on a share, including read/write/delete attempts. Even higher fidelity than 5140 — captures every file accessed. Volume is high; usually filtered to sensitive shares.

### 33.27 5156 — Windows Filtering Platform Allowed Connection

WFP (the Windows firewall API surface) allowed a connection. Fields: source/dest IP, source/dest port, protocol, app name, direction.

5156 is essentially a per-connection log of all network activity touching the filtering platform. Extremely high volume; rarely enabled in full production. When enabled, comprehensive — comparable to Zeek conn.log for the local host's perspective.

### 33.28 5158 — WFP Permitted Bind

WFP allowed a socket to bind to a local port. Useful for detecting unusual local listeners (a process suddenly binding to 4444).

### 33.29 1102 — Audit Log Cleared

The Security event log was cleared. Generated on clearance, on the channel that was cleared.

Fields:
- `SubjectUserSid`, `SubjectUserName`, `SubjectDomainName`, `SubjectLogonId` — who cleared

1102 is one of the strongest indicators of in-progress incident response evasion. Combined with USN journal residue showing the .evtx file deleted/recreated, this confirms tampering. Note: 1102 only fires for the Security log; other channels cleared produce ID 104 (Section 34).

## 34. System Event Log Reference

The System channel holds OS-level events.

### 34.1 7045 — Service Installed

A service was installed. The System-log counterpart to Security 4697. Fields:
- `ServiceName`
- `ImagePath` — binary path
- `ServiceType`
- `StartType`
- `AccountName`

7045 fires on member servers and workstations regardless of audit policy. The most reliable cross-corpus indicator of service-based persistence. PsExec creates a service named `PSEXESVC`; this is one of the most-seen 7045 patterns in IR.

### 34.2 7036 — Service Start/Stop

A service changed state. High volume. Useful for sequencing: a malicious service installed (7045) followed shortly by 7036 "started" confirms it ran.

### 34.3 6005 / 6006 / 6008

- **6005** — Event Log service started (system boot)
- **6006** — Event Log service stopped (clean shutdown)
- **6008** — Previous shutdown was unexpected (crash / power loss / forced shutdown without 6006)

6008 in sequence with other events identifies hard reboots. Adversaries pulling the plug or `bcdedit /set safeboot` chains produce 6008 patterns.

### 34.4 104 — Event Log Cleared

A non-Security log was cleared. Fields: channel cleared, user that cleared, SID. The non-Security analog of 1102.

In IR: 104 entries for `Microsoft-Windows-PowerShell/Operational` or `Sysmon/Operational` indicate targeted log clearing. EvtxECmd against the `Microsoft-Windows-Eventlog/Operational` channel surfaces these.

### 34.5 7034 — Service Crashed

A service terminated unexpectedly. Repeated 7034 for the same service suggests injection failure, AV killing the service, or attacker testing.

### 34.6 7022 / 7011 — Service Hung

A service hung at startup (7022) or while running (7011 — timeout on a transaction). Less common; sometimes seen with malicious driver loads.

## 35. Application Event Log

### 35.1 Windows Error Reporting (WER)

- **1000** — Application crash. Fields: application name, version, faulting module, exception code, faulting offset.
- **1001** — WER bucket assignment. Less actionable forensically.
- **1002** — Application hung.

For IR: 1000 events on `lsass.exe`, `winlogon.exe`, or `services.exe` are major findings — those processes rarely crash in production. A crash of `lsass.exe` correlated with credential dumping attempts is a known pattern.

### 35.2 MSI Installer Errors

- **1033** — Installation completed
- **1034** — Installation removed
- **11707** — Successful install (MsiInstaller provider)
- **11708** — Failed install
- **11724** — Removal successful

### 35.3 .NET Runtime Events

- **1023** — .NET CLR error
- **1026** — .NET unhandled exception

Useful for fragile in-memory payloads and PowerShell-launched .NET execution failures.

## 36. PowerShell Logging

PowerShell logging has three main feature sets, each with its own events.

### 36.1 PowerShell Module Logging (4103)

Module logging records pipeline execution for specific modules. Configured via `EnableModuleLogging` registry key. Records:

- **4103** — Pipeline execution detail. Fields: User, HostApplication, ConnectedUser, ModuleName, ModuleVersion, Payload (the parameter values).

Low-detail compared to 4104 but cheap.

### 36.2 PowerShell Script Block Logging (4104)

Script Block logging records the actual code executed, *post-deobfuscation*. Configured via `EnableScriptBlockLogging`.

- **4104** — Script block compiled. Fields: ScriptBlockText (the code), ScriptBlockId (GUID), Path (script file if any), MessageNumber, MessageTotal (script blocks > 20 KB split across multiple events).

This is the most-valuable PowerShell forensic event. Even if the attacker uses heavy `Invoke-Expression` chains, base64-encoded payloads, character substitution — by the time 4104 fires, the PowerShell engine has deobfuscated enough to compile the script block, and the recorded text shows real readable code. 4104 events level `Verbose` (5) include scripts that the engine deemed suspicious; level `Warning` (3) is always logged.

### 36.3 PowerShell Transcription

Transcription writes a session transcript to a file (configured location). Less common in modern setups; events generated:
- **4100** — Provider lifecycle event
- **600** — Provider start (Windows PowerShell, legacy)
- **800** — Pipeline started (Windows PowerShell, legacy)

### 36.4 Channels

- `Microsoft-Windows-PowerShell/Operational` — 4103, 4104
- `Windows PowerShell` (legacy classic log) — 600, 800, 400 (engine state)

### 36.5 Deobfuscation in 4104

A specific anti-AMSI bypass example:
```
$a = [Reflection.Assembly]::LoadWithPartialName('System.Management.Automation');
$b = $a.GetType('System.Management.Automation.AmsiUtils').GetField('amsiInitFailed','NonPublic,Static');
$b.SetValue($null, $true)
```

When this runs, the engine logs the literal text above — even if the input was `$([char]36 + 'a'...)` style obfuscation. The script block boundary is post-tokenization, so 4104 captures the canonical form.

Heavily obfuscated attacks producing many small script blocks (each obfuscation stage as a separate block) generate dozens of 4104 events in sequence. Looking at them in order reconstructs the layers.

## 37. Sysmon Full Event Reference

Sysinternals System Monitor (Sysmon) is a Microsoft-distributed agent providing high-fidelity endpoint telemetry. Events go to `Microsoft-Windows-Sysmon/Operational`. Each event ID has specific fields and a specific detection use case.

### 37.1 Event ID 1 — Process Create

The most-consulted Sysmon event. Fields:
- `RuleName` — matched rule name (from config)
- `UtcTime`
- `ProcessGuid` — unique per-process; spans event IDs
- `ProcessId`
- `Image` — full path of process binary
- `FileVersion`, `Description`, `Product`, `Company`, `OriginalFileName` — PE resource fields (highly useful for renamed binaries; `OriginalFileName` is the binary's original name as compiled)
- `CommandLine`
- `CurrentDirectory`
- `User`
- `LogonGuid`, `LogonId`, `TerminalSessionId`, `IntegrityLevel`
- `Hashes` — MD5, SHA-1, SHA-256, IMPHASH (configurable)
- `ParentProcessGuid`, `ParentProcessId`, `ParentImage`, `ParentCommandLine`, `ParentUser`

The combination of `OriginalFileName` (immutable in PE; not changed by renaming the file) plus `Image` (current file path; changes with renaming) makes Sysmon 1 a powerful detection input for renamed binaries.

### 37.2 Event ID 2 — File Creation Time Changed

A process changed the creation timestamp of a file. The canonical timestomp detection event. Fields: Image (process), TargetFilename, CreationUtcTime (new), PreviousCreationUtcTime (old).

### 37.3 Event ID 3 — Network Connection

A network connection was made by a process. Sysmon doesn't intercept; it observes via WFP. Fields:
- ProcessGuid, ProcessId, Image, User
- Protocol (tcp/udp)
- Initiated (true if outbound from this process)
- SourceIsIpv6, SourceIp, SourceHostname, SourcePort, SourcePortName
- DestinationIsIpv6, DestinationIp, DestinationHostname, DestinationPort, DestinationPortName

Combined with Sysmon 1 process create, gives precise (process, dest) attribution. Standard config skips localhost and well-known port noise.

### 37.4 Event ID 4 — Sysmon Service State Changed

Sysmon started or stopped. Useful for tamper detection — when Sysmon stops mid-incident, an event is logged that survives.

### 37.5 Event ID 5 — Process Terminated

A process exited. ProcessGuid, ProcessId, Image. Useful for session bounds; less for direct detection.

### 37.6 Event ID 6 — Driver Loaded

A kernel driver was loaded. Fields:
- ImageLoaded — driver file path
- Hashes
- Signed (bool), Signature, SignatureStatus

The canonical detection for unsigned driver loads, BYOVD (bring-your-own-vulnerable-driver) attacks, and rootkit installs. SignatureStatus values: `Valid`, `Invalid`, `Unavailable`, `Expired`, `Untrusted`, `Reset`, etc.

### 37.7 Event ID 7 — Image Loaded

A DLL was loaded into a process. High volume by default; most configs filter to specific images. Useful for:
- DLL sideloading detection (legitimate process loading unexpected DLL from unusual path)
- Unsigned DLL loads in protected processes
- AMSI/ETW bypass DLL injections

Fields: ProcessGuid, ProcessId, Image, ImageLoaded, Hashes, Signed, Signature, SignatureStatus.

### 37.8 Event ID 8 — CreateRemoteThread

A thread was created in another process — classic injection primitive. Fields:
- SourceProcessGuid, SourceProcessId, SourceImage
- TargetProcessGuid, TargetProcessId, TargetImage
- NewThreadId
- StartAddress, StartModule, StartFunction

Patterns:
- `lsass.exe` → another process: rare, usually attacker code in lsass injecting elsewhere
- `cmd.exe` / PowerShell → lsass.exe: credential dumping via remote thread injection
- Any process → `winlogon.exe`: persistence injection

### 37.9 Event ID 9 — RawAccessRead

A process opened a handle for raw disk access (`\\.\C:`). Fields:
- ProcessGuid, ProcessId, Image
- Device

Direct disk reads bypass filesystem ACLs. Used by `vssadmin`-bypassing tools to read `$MFT`, `SAM`, or other locked files. Rare in benign processes — backup software is the typical legit case.

### 37.10 Event ID 10 — ProcessAccess

A process opened a handle to another process with specific access rights. Fields:
- SourceProcessGUID, SourceProcessId, SourceThreadId, SourceImage
- TargetProcessGUID, TargetProcessId, TargetImage
- GrantedAccess — hex bitmask
- CallTrace — stack trace

The canonical detection for `lsass.exe` credential dumping (Mimikatz, Pypykatz, etc.). Mimikatz needs `PROCESS_VM_READ` (0x0010) plus `PROCESS_QUERY_LIMITED_INFORMATION` (0x1000) at minimum. The CallTrace shows which DLL initiated the access — `dbghelp.dll` and `dbgcore.dll` are common dumping callers, but defenders look for unsigned DLLs in the trace.

### 37.11 Event ID 11 — FileCreate

A file was created. Fields: Image (creator), TargetFilename, CreationUtcTime. Used to detect drop staging.

### 37.12 Event ID 12 — RegistryEvent (Object Create / Delete)

A registry key was created or deleted. Fields:
- EventType (CreateKey, DeleteKey, CreateValue, DeleteValue, SetValue, RenameKey)
- ProcessGuid, ProcessId, Image
- TargetObject — registry key path

### 37.13 Event ID 13 — RegistryEvent (Value Set)

A registry value was set. Fields: as 12, plus `Details` — the new value.

12 and 13 together cover registry persistence (Run keys, AppInit_DLLs, scheduled task definitions, service entries). Heavy volume; config filters to interesting key paths.

### 37.14 Event ID 14 — RegistryEvent (Key/Value Rename)

A registry key or value was renamed. Less common; used for advanced persistence concealment.

### 37.15 Event ID 15 — FileCreateStreamHash

A file with an alternate data stream was created. The standard detection for Mark-of-the-Web (`Zone.Identifier`) writes — used to detect attachment downloads, browser-saved files. Fields: TargetFilename including the stream suffix, Contents (for Zone.Identifier, this is the zone number — 3 means Internet).

### 37.16 Event ID 16 — ServiceConfigurationChange

Sysmon's service config was changed. Tamper-resistance event.

### 37.17 Event ID 17 — PipeEvent (Pipe Created)

A named pipe was created. Cobalt Strike's SMB beacon creates pipes; tools using IPC create pipes. Fields: PipeName, Image. Distinctive pipe names are signature material.

### 37.18 Event ID 18 — PipeEvent (Pipe Connected)

A client connected to a named pipe. Fields: PipeName, Image (the client). Pairs with 17 to show pipe-mediated IPC.

### 37.19 Event ID 19 — WmiEvent (WmiEventFilter)

A WMI event filter was registered. WMI persistence consists of three pieces: filter (the condition), consumer (the action), filter-to-consumer binding. 19/20/21 cover these.

### 37.20 Event ID 20 — WmiEvent (WmiEventConsumer)

A WMI event consumer was registered. ActiveScriptEventConsumer and CommandLineEventConsumer are the typical malicious variants — they run a script or command in response to the filter trigger.

### 37.21 Event ID 21 — WmiEvent (WmiEventConsumerToFilter)

A filter was bound to a consumer. The completed persistence chain.

### 37.22 Event ID 22 — DNSEvent

A DNS query was made by a process. Fields:
- ProcessGuid, ProcessId, Image, User
- QueryName
- QueryStatus — Win32 result code
- QueryResults — answers list (semicolon-separated)

Process-attributed DNS — invaluable. Without this, network captures show queries but not their process origin (without elaborate netlink tracing).

### 37.23 Event ID 23 — FileDelete

A file was deleted. Captures the deleted file's content into the Sysmon archive directory (configured path) before logging. Useful for recovering deleted payloads.

Fields: Image (deleter), TargetFilename, Hashes, Archived (true/false — was it archived).

### 37.24 Event ID 24 — ClipboardChange

Clipboard contents changed. Captures the clipboard content (text) to the archive. Used to detect credential pasting, sensitive data exfil staging. Privacy-heavy; usually filtered.

### 37.25 Event ID 25 — ProcessTampering

A process modified its own image — typically a sign of process hollowing or process doppelgänging. Fields: ProcessGuid, Image, Type (Image is replaced / Image is modified).

Newer Sysmon versions also include:
- **26** — FileDeleteDetected (file deleted, no archive)
- **27** — FileBlockExecutable (blocked due to FileBlockExecutable filter)
- **28** — FileBlockShredding (shred blocked)
- **29** — FileExecutableDetected (detected executable file create)

## 38. Sysmon Config Baselines

### 38.1 SwiftOnSecurity sysmon-config

The most-used community Sysmon configuration. Conservative — designed to log enough for detection without overwhelming volume. Maintained at github.com/SwiftOnSecurity/sysmon-config. Single-file XML, well-commented. The README is essentially a Sysmon tutorial.

Filter approach: include rules for known-suspicious patterns, broad exclusion of system noise. Tagging with `RuleName` makes filtered events self-documenting.

### 38.2 Olaf Hartong's sysmon-modular

A modular alternative — separate XML files per technique area, combined at config-generation time. Located at github.com/olafhartong/sysmon-modular. Supports MITRE ATT&CK technique mapping in rule names. The `merge_sysmon_config.py` script combines selected modules into one config.

Heavier than SwiftOnSecurity by default — more events logged, more telemetry. Used by mature security operations centers.

### 38.3 Microsoft Default Config

When Sysmon runs without `-c`, default behavior: only Event ID 4 logged (service state). Not useful — config is required for any real telemetry.

The "default config" sometimes referred to is the example XML included in the Sysmon ZIP (`sysmonconfig-export.xml` or similar). It's minimal — not used in production directly.

### 38.4 Other Configs Worth Knowing

- **ION-Storm** — older, mostly merged into SwiftOnSecurity
- **mthcht/PurpleSharp** — adversary-simulation-tuned config
- **TaranisAi** — actively maintained, comprehensive

## 39. RDP-Related Events

RDP traffic produces events across several channels.

### 39.1 RemoteConnectionManager

`Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational`. The handler at the RDP connection level.

- **1149** — User authenticated. Fields: User, Domain, source IP. Generated *before* logon success. Used to attribute RDP connection source even when authentication fails.

### 39.2 LocalSessionManager

`Microsoft-Windows-TerminalServices-LocalSessionManager/Operational`. Tracks user sessions.

- **21** — Session logon succeeded. Fields: User, Session ID, source network address.
- **22** — Shell start notification received.
- **23** — Session logoff succeeded.
- **24** — Session has been disconnected (RDP client closed; session still exists).
- **25** — Session reconnection succeeded.

These pair: 21 followed eventually by 23 = full session; 21/24/25/23 = a disconnect/reconnect within one session.

### 39.3 TerminalServices-LSM

`Microsoft-Windows-TerminalServices-LocalSessionManager/Admin` for admin events.

### 39.4 Security-Channel RDP

4624 with `LogonType=10` (RemoteInteractive) is the Security-channel reflection of RDP logon. Cross-correlate with TerminalServices 1149 to get the source IP even for failed logons (which 4624 doesn't fire on).

### 39.5 Distinct Event for RDP from External IP

In IR, the canonical RDP investigation sequence:
1. Filter 1149 by `Param3` (source IP) for external addresses
2. Cross-reference with 4624 type 10 by `TargetLogonId`
3. Walk the session activity (Sysmon 1 events tagged by `LogonGuid`) within the session bounds (21 to 23)
4. Look for 4648 events (use of other credentials) within the session — lateral movement from the RDP entry point

## 40. Defender Events

`Microsoft-Windows-Windows Defender/Operational` channel.

### 40.1 1006 — Malware Detected

Defender detected malware. Fields: ProcessName, Path, ThreatName, ThreatID, SeverityName, CategoryName, FWLink (Microsoft's threat-info URL).

### 40.2 1007 — Action Taken

Defender took action against detected malware. Fields include `ActionName` (Quarantine, Remove, Allow, etc.).

### 40.3 1009 — Quarantined Item Restored

A user/admin restored a quarantined item. Suspicious in IR — sometimes legitimate (false positive), sometimes attacker restoring their payload.

### 40.4 1116 / 1117

- **1116** — Malware detection. Similar to 1006 but Defender variant.
- **1117** — Action taken on malware. Pairs with 1116.

In modern Windows (10/11/Server 2019+), 1116/1117 are the standard real-time protection alerts. 1006/1007 are legacy.

### 40.5 5001 / 5007

- **5001** — Real-time protection disabled. Critical event — adversary action.
- **5007** — Defender configuration changed.

5001 fires when a user (or attacker with privilege) turns off real-time protection. The chain `5001` + new file drop + `Set-MpPreference -DisableRealtimeMonitoring $true` in PowerShell 4104 is a tight signal.

### 40.6 Other Defender IDs

- **2000** — Signature update finished
- **2001** — Signature update failed
- **2003** — Engine update
- **3002** — Real-time protection failed
- **5000** — Real-time protection enabled
- **5004** — Real-time protection feature disabled

## 41. WMI Events

WMI is the privileged interface to system management — and a popular persistence and lateral movement target. Logging is split across channels.

### 41.1 Microsoft-Windows-WMI-Activity/Operational

- **5857** — Provider started. Fields: ProviderName, ProviderGuid, ProcessId, ResultCode. Useful for tracking WMI provider load — legitimate providers reload predictably; novel providers warrant inspection.
- **5858** — Operational error in WMI. Often noise; sometimes reveals failed remote WMI calls.
- **5859** — WMI temporary or permanent event subscription created. The most important WMI persistence detection. Fields: ConsumerType (CommandLineEventConsumer, ActiveScriptEventConsumer, ...), TargetInstance, PossibleCause, OperationsId.
- **5860** — WMI event subscription used. The trigger fired and the consumer ran. Pairs with 5859.
- **5861** — Permanent event subscription created. Permanent subscriptions survive reboot — full persistence. Fields: TargetInstance (the WMI consumer object), ResourceUrl, User.

Sysmon 19/20/21 covers the same persistence chain from a different angle. The two should align.

## 42. Task Scheduler Events

`Microsoft-Windows-TaskScheduler/Operational`. Disabled by default on some Windows variants — enable for IR usability.

### 42.1 Important Event IDs

- **106** — Task registered. Fields: TaskName, UserContext. A new task was scheduled.
- **140** — Task updated. The XML or properties of an existing task changed.
- **141** — Task deleted.
- **200** — Action started. Fields: TaskName, ActionName (the path to the binary). When a task fires and runs a binary.
- **201** — Action completed.
- **129** — Task launched. Similar to 200 but reported by a different component.
- **100** — Task started (similar context to 200).
- **102** — Task completed.
- **111** — Task terminated.
- **322** — Launch request ignored, instance already running.

The 106/140/141 sequence shows task lifecycle. 200/201 show runtime. Persistence via task: an attacker creates with 106, runs with 200 each time the trigger fires.

`schtasks.exe` from cmd.exe creates tasks via the standard interface — these generate 106 events. PowerShell `Register-ScheduledTask` produces the same. Direct API calls (ITaskService COM) also produce 106. Direct registry writes to `\SYSTEM\CurrentControlSet\Services\Schedule\TaskCache\Tasks\` bypass the API and may not generate 106 — a notable evasion pattern.

## 43. Hayabusa Rule Engine

Hayabusa (Yamato Security, github.com/Yamato-Security/hayabusa) is a Windows Event Log analytic tool that consumes Sigma rules and emits a timeline. Built in Rust for speed.

### 43.1 Architecture

Hayabusa loads:
- Built-in detection rules (~3000+ in the bundled `rules/` directory, organized by technique)
- Sigma rules from a Sigma rule repository
- Channel mappings (which Sigma fields map to which .evtx fields)

It walks `.evtx` files (or a directory of them) and emits CSV output annotating each matched event with the rule that matched, mapped MITRE ATT&CK techniques, severity, and timeline-friendly fields.

### 43.2 `csv-timeline` Command

The primary detection command. Schema of output:

| Column | Meaning |
|---|---|
| Timestamp | event time |
| Computer | hostname |
| Channel | source channel |
| EventID | event ID |
| Level | severity (informational, low, medium, high, critical) |
| MitreTactics | ATT&CK tactics (TA0001, ...) |
| MitreTags | ATT&CK techniques (T1059, ...) |
| OtherTags | additional categorical tags |
| RecordID | event record ID |
| Details | rule description |
| ExtraFieldInfo | event-specific data |
| RuleFile | path to rule that matched |

The output is sortable / filterable as CSV. The `--profile` flag controls which columns appear: `minimal`, `standard`, `verbose`, `super-verbose`, `all-field-info`.

### 43.3 Other Useful Hayabusa Commands

- `update-rules` — pulls latest rules from the Hayabusa rules repo
- `eid-metrics` — counts events by ID per channel
- `logon-summary` — summarizes logon events (4624/4625) per user/source
- `metrics` — overall corpus statistics
- `pivot-keywords-list` — extract keywords for pivoting
- `update` — update Hayabusa itself

### 43.4 MITRE Field Mapping

Rules tag matched events with ATT&CK techniques. Hayabusa's `eid-metrics` and `csv-timeline` aggregate these. A typical IR workflow: run `csv-timeline`, filter by MitreTags for the techniques of interest (e.g., `T1059.001` PowerShell), then pivot to source events.

The rule files themselves are YAML in Sigma format with Hayabusa-specific extensions. Levels are critical/high/medium/low/informational mapped from Sigma's level field.

## 44. Chainsaw

Chainsaw (F-Secure / WithSecure Labs, github.com/WithSecureLabs/chainsaw) is an alternate Sigma engine for Windows logs. Rust-based.

### 44.1 Compared to Hayabusa

- **Chainsaw** ships with built-in detection rules (Chainsaw-format YAML) for canonical IR patterns: lateral movement, lsass dumps, password sprays, etc. Faster on raw event ID detection than Sigma-driven workflows.
- **Hayabusa** is Sigma-rule-centric, with more rules. Output is more verbose.

Both are first-class options. Many practitioners run both — Chainsaw's `hunt` command for built-in detections, Hayabusa for Sigma rule coverage.

### 44.2 Key Commands

```
chainsaw hunt <path> -s sigma-rules/ --mapping mappings/sigma-event-logs-all.yml
chainsaw hunt <path> --rule chainsaw-rules/
chainsaw search <path> -t "powershell.exe"        # literal search
chainsaw search <path> -e "EventID: 4624"
chainsaw analyse shimcache --shimcache-path ...
```

Output formats: terminal table (default), CSV, JSON, JSONL.

### 44.3 Chainsaw Detection Rules Format

YAML, distinct from Sigma but conceptually similar:
```yaml
title: Suspicious PsExec Service Created
status: stable
description: ...
authors: [withsecure]
level: high
kind: evtx
group: PsExec
timestamp: Event.System.TimeCreated
fields: [Event.System.EventID, Event.EventData.ServiceName]
filter:
  Event.System.EventID: 7045
  Event.EventData.ServiceName:
    - 'PSEXESVC'
    - 'PAEXEC'
```

## 45. Sigma Rule Format

Sigma (github.com/SigmaHQ/sigma) is the open standard for SIEM-agnostic detection rules. A Sigma rule expresses a detection in YAML; converters translate to Splunk SPL, Elastic KQL, Sentinel KQL, Suricata, Hayabusa, Chainsaw, etc.

### 45.1 Structure

```yaml
title: Suspicious LDAP Query from Non-Standard Tool
id: <uuid>
status: experimental | test | stable | deprecated | unsupported
description: <prose>
references:
  - https://...
author: <name>
date: 2024/01/15
modified: 2024/06/15
tags:
  - attack.discovery
  - attack.t1087.002
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    EventID: 4688
    NewProcessName|endswith:
      - '\ldifde.exe'
      - '\adfind.exe'
  filter:
    User:
      - 'corp\sysadmin'
  condition: selection and not filter
falsepositives:
  - Legitimate system administration
level: high
```

### 45.2 Logsource

The `logsource` field declares what kind of data the rule expects. Categories include `process_creation`, `network_connection`, `file_event`, `registry_event`, `dns_query`. Products: `windows`, `linux`, `macos`. Services: specific log channels.

The converter uses logsource to map field names (`NewProcessName` for Windows process_creation maps to Sysmon `Image` or Security `NewProcessName` etc.).

### 45.3 Detection Selectors

`selection`, `filter`, `selection_1`, etc. are arbitrary names. Each is a map of field → value (or list of values, with `|<modifier>` field-name suffixes).

Modifiers:
- `|contains` — substring match
- `|startswith` / `|endswith`
- `|re` — regex
- `|all` — all values match (with list values, requires each)
- `|base64` / `|base64offset` — base64 encoded
- `|wide` / `|utf16` / `|utf16le` — Unicode variants

### 45.4 Condition

The `condition` field is a Boolean expression over selectors. Examples:
- `selection`
- `selection and not filter`
- `1 of selection_* and not filter`
- `all of them`

### 45.5 Converter Tools

- `sigma-cli` — official converter (`sigma convert -t splunk rule.yml`)
- `pySigma` — Python library
- `sigconverter.io` — web UI

For Hayabusa / Chainsaw, the converter is built in — they read Sigma rules directly without pre-conversion.

## 46. EvtxECmd JSON Output Schema

EvtxECmd's CSV/JSON output schema (with `--json` flag) for each event includes:

- `PayloadData1` through `PayloadData6` — first six EventData fields (often the most-useful)
- `Payload` — the full EventData as JSON / XML
- `MapDescription` — if a map exists, the human-readable description
- `RecordNumber` — event record ID
- `TimeCreated` — UTC timestamp
- `EventId`, `Level`, `Provider`, `Channel`, `Computer`, `UserId`
- `ProcessId`, `ThreadId`
- `ExecutableInfo` — for events containing process info, parsed
- `UserName`, `RemoteHost`

For filtering: load into PowerShell, jq, or Pandas. `jq 'select(.EventId == 4624) | select(.PayloadData1 == "LogonType: 10")'` filters RDP logons.

EvtxECmd maps live at github.com/EricZimmerman/evtx/tree/master/evtx/Maps. The map files transform raw EventData into structured fields with `MapDescription` annotations — a 4624 event with a logon type 10 from external IP gets `MapDescription="RDP logon from <ip>"` automatically.

## 47. Log Clearing Detection

Adversaries who clear logs to hide their tracks leave their own artifacts:

### 47.1 Direct Indicators

- **Security 1102** — Security log cleared. Fires before the cleared state takes effect; the cleared state captures only this event.
- **System 104** — Application or System log cleared.
- Equivalent 104 on Sysmon/Operational, PowerShell/Operational, etc., for non-default channels.

### 47.2 Gap Detection

When 1102/104 isn't generated (cleared by tampered API, deleted .evtx file directly), gaps in event timestamps can hint at clearing:
- Sysmon Event ID 4 (service state change) on Sysmon stop+start
- 6005/6006/6008 gaps in System log
- Unusual gaps in 4624 logon records — a working workstation has logons at expected times
- Sequence breaks in EventRecordID

### 47.3 USN Journal Residue

When the .evtx file is deleted and recreated (a way to "clear" without using the API), `$UsnJrnl:$J` shows:
- USN_REASON_FILE_DELETE for `Security.evtx`
- USN_REASON_FILE_CREATE for `Security.evtx`
- Sequence USN gap consistent with a brief deletion window

Even if the new Security log is empty, USN journal entries pre-dating the delete remain and prove the clear happened.

### 47.4 $LogFile Residue

NTFS $LogFile records the delete+create as redo/undo records. Even if the new .evtx is empty, the $LogFile shows the rename/move operations.

### 47.5 VSS Snapshot Recovery

If a Volume Shadow Copy exists from before the clearing, the prior .evtx file is preserved in the shadow. `vshadowmount` followed by `cp` recovers the original.

### 47.6 EventLog Service Stop Indicators

Adversaries stop the EventLog service before clearing (so concurrent writes don't recreate entries). 7036 events in System log show the stop and restart. Sometimes attackers use `wevtutil cl <channel>` or PowerShell `Clear-EventLog`; both generate 1102/104 unless the service is already stopped.

### 47.7 Counter-Forensic Tooling Awareness

Known anti-forensic tools that wipe .evtx selectively (rather than clearing wholesale) — Invoke-Phant0m, Mimikatz `event::drop`, etc. — operate by stopping the EventLog service's logging threads and never officially clearing the log. Indicators:
- Sysmon stops logging mid-incident with no 1116/1102
- Gaps in EventRecordID sequence within an otherwise-active log
- Sysmon ID 8 / 10 events showing process injection into `svchost.exe` (the EventLog service host)

The combination of `$UsnJrnl` deletes + 104/1102 + Sysmon process injection + Sysmon service-state changes paints the full clearing picture even when individual artifacts are missing.

## 48. Putting It Together — Cross-Artifact Reasoning

The artifacts in this document — NTFS metadata, USN journal, VSS, Plaso timelines, Zeek logs, Suricata alerts, Windows Event Log, Sysmon — overlap heavily. A single attacker action typically leaves traces in multiple places, and the canonical analytic technique is cross-corroboration. Two examples:

### 48.1 Lateral Movement via SMB

A single PsExec lateral movement leaves:

- **Source host Sysmon 1** — `psexec.exe \\target -accepteula -s cmd.exe` with command line, hashes, parent process (likely cmd.exe or pwsh.exe).
- **Source host Sysmon 3** — outbound TCP 445 (SMB) and 135 (RPC) to target IP.
- **Source host Security 4648** — explicit credentials used for `target\administrator` from `psexec.exe`.
- **Target host Security 4624 type 3** — network logon as `administrator` from source IP.
- **Target host Security 4672** — special privileges assigned.
- **Target host System 7045** — service `PSEXESVC` installed with `ImagePath=C:\Windows\PSEXESVC.exe`.
- **Target host Security 4697** — same service (Security-channel reflection).
- **Target host System 7036** — `PSEXESVC` started.
- **Target host Sysmon 1** — `psexesvc.exe` running, parent `services.exe`.
- **Target host Sysmon 1** — child `cmd.exe` of `psexesvc.exe`.
- **Target host NTFS $MFT** — new file `C:\Windows\PSEXESVC.exe` created.
- **Target host $UsnJrnl** — USN_REASON_FILE_CREATE for PSEXESVC.exe.
- **Network sensor Zeek conn.log** — TCP 445 flow source → target with `service=smb`.
- **Network sensor Zeek smb_mapping.log** — share `\\target\ADMIN$` mounted.
- **Network sensor Suricata** — likely ET POLICY rule for PSEXESVC.
- **Target host Sysmon 17** — named pipe `\\.\pipe\psexesvc` created.

Any one indicator alone might be a false positive; the convergence is what makes the diagnosis defensible.

### 48.2 Credential Dumping Inside Cobalt Strike Beacon

A Cobalt Strike beacon running `mimikatz sekurlsa::logonpasswords`:

- **Sysmon 1** — beacon process (often masquerading as legitimate name) with no parent or odd parent.
- **Sysmon 8** — CreateRemoteThread into lsass.exe (if Mimikatz technique uses injection) or
- **Sysmon 10** — ProcessAccess of lsass.exe with `GrantedAccess=0x1010` or `0x1410`, CallTrace including unsigned DLL.
- **Sysmon 7** — DLL load into the beacon process for the Mimikatz functionality.
- **Application 1000** — possible lsass.exe crash if the operation is unstable.
- **Defender 1116/1117** — if real-time protection catches it.
- **Network Zeek ssl.log** — beacon → C2 with characteristic JA3.
- **Network Suricata** — Cobalt Strike rules likely firing on the cert subject, JA3, or URI.

The Sysmon 10 with `lsass.exe` target and an unsigned DLL in CallTrace is one of the highest-fidelity credential-dump indicators in the corpus.

---

## Closing Notes on Source Material

The reference content above synthesizes:
- Microsoft Win32 Event Documentation (events.microsoft.com and ultimatewindowssecurity.com cross-reference)
- Sysinternals Sysmon README (github.com/Sysinternals/SysmonForLinux for the cross-platform docs; Sysmon Windows version on docs.microsoft.com)
- SwiftOnSecurity sysmon-config (github.com/SwiftOnSecurity/sysmon-config)
- Olaf Hartong sysmon-modular (github.com/olafhartong/sysmon-modular)
- Hayabusa documentation (github.com/Yamato-Security/hayabusa)
- Chainsaw documentation (github.com/WithSecureLabs/chainsaw)
- Sigma rule format documentation (sigmahq.io)
- Active Countermeasures RITA documentation
- Zeek Project documentation (docs.zeek.org)
- Suricata documentation (suricata.io / docs.suricata.io)
- Plaso documentation (plaso.readthedocs.io)
- The Sleuth Kit documentation (sleuthkit.org/sleuthkit/docs)
- Joachim Metz libyal documentation (github.com/libyal — libewf, libvshadow, libbde, libfvde, libevtx, libusnjrnl)
- SANS posters (FOR500 / FOR508 / FOR572 / FOR526), the SANS Windows Forensic Analysis poster, the SANS Hunt Evil poster
- Eric Zimmerman tools documentation (ericzimmerman.github.io)
- David Cowen's "Computer Forensics InfoSec Pro Guide" and "Hacking Exposed Computer Forensics" for $LogFile / USN Journal coverage
- Brian Carrier "File System Forensic Analysis" for NTFS internals

Field-level event documentation can drift across Windows versions and Sysmon releases; treat field names here as conventional but consult current docs when working with a specific corpus.
