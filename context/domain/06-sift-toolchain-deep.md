# 06 — SIFT Toolchain Deep Reference

> Encyclopedic reference for every important tool in the SANS SIFT Workstation (and the community add-ons commonly installed alongside it). One section per tool. No architectural prescriptions. Pure tool knowledge.

The SANS SIFT Workstation is an Ubuntu-based (currently 20.04 LTS, transitioning to 22.04) forensic distribution maintained by SANS DFIR. "Stock SIFT" in this document refers to the SIFT 2024.x build of `sift-cli` applied to a clean Ubuntu installation. Where a tool is community-installed (not in stock), it is noted.

---

## Table of contents

1. Memory acquisition and analysis
2. Disk acquisition, imaging, and mounting
3. Filesystem analysis (Sleuth Kit family)
4. Volume decryption (BitLocker, FileVault, LUKS, VSS)
5. Timeline generation (plaso family)
6. Windows artifact parsers (Eric Zimmerman tools)
7. Registry analysis
8. Windows event log analysis
9. Pattern matching, capability detection, fuzzy hashing
10. Carving
11. Network forensics
12. Malware triage
13. Live triage and collection
14. Anti-forensics detection
15. Hashing and integrity
16. Canonical tool chains
17. What is missing on stock SIFT
18. License and provenance

---

# 1. MEMORY ACQUISITION AND ANALYSIS

## 1.1 Volatility 3 (`vol`, `vol.py`, `python3 -m volatility3`)

**Author / maintainer.** The Volatility Foundation. Current lead: Michael Ligh, Andrew Case, Jamie Levy. Source: https://github.com/volatilityfoundation/volatility3. Documentation: https://volatility3.readthedocs.io/.

**Purpose.** A Python 3 framework for extracting digital artifacts from volatile memory (RAM) samples of Windows, Linux, and macOS systems.

**Stock SIFT status.** Volatility 3 is included in SIFT 2024+ as a pip-installed package, invoked as `vol` (or `vol.py`). Symbol tables for current Windows builds may need refreshing — they live under `~/.cache/volatility3/` or in the volatility3 package's `symbols/` directory and can be downloaded from https://downloads.volatilityfoundation.org/volatility3/symbols/.

**Invocation syntax.** Volatility 3 abandoned the v2 profile system. Symbols are auto-detected from the image. Core form:

```
vol -f <image> [global-flags] <plugin> [plugin-flags]
```

Common patterns:

```
vol -f memory.raw windows.info                          # OS detect + KDBG verification
vol -f memory.raw windows.pslist
vol -f memory.raw windows.pstree
vol -f memory.raw windows.cmdline
vol -f memory.raw windows.netscan
vol -f memory.raw windows.dlllist --pid 4242
vol -f memory.raw windows.malfind                       # injected code detection
vol -f memory.raw windows.svcscan
vol -f memory.raw windows.handles --pid 4242 --object-types File
vol -f memory.raw windows.registry.hivelist
vol -f memory.raw windows.registry.printkey --offset 0xfffff8a000024010 --key 'Software\Microsoft\Windows\CurrentVersion\Run'
vol -f memory.raw windows.registry.userassist
vol -f memory.raw windows.dumpfiles --pid 4242 -o ./out/
vol -f memory.raw windows.memmap --pid 4242 --dump -o ./out/
vol -f memory.raw windows.modules
vol -f memory.raw windows.modscan
vol -f memory.raw windows.ssdt
vol -f memory.raw windows.callbacks
vol -f memory.raw timeliner.Timeliner                   # cross-plugin timeline
vol -f memory.raw -r json windows.pslist                # JSON output renderer
vol -f memory.raw -r csv windows.pslist                 # CSV renderer
vol -f memory.raw -r pretty windows.pslist              # default human-readable
vol -f memory.raw -r quick windows.pslist               # fastest renderer, less formatting
```

Linux:

```
vol -f vmlinux.raw linux.pslist
vol -f vmlinux.raw linux.bash                           # recover bash history from memory
vol -f vmlinux.raw linux.check_modules
vol -f vmlinux.raw linux.malfind
vol -f vmlinux.raw linux.lsmod
vol -f vmlinux.raw linux.netstat
```

macOS:

```
vol -f mac.lime mac.pslist
vol -f mac.lime mac.bash
vol -f mac.lime mac.netstat
```

**Input formats accepted.** Raw memory dumps (.raw, .mem, .dmp), Microsoft crash dumps (.dmp), VMware suspended VMs (.vmem + .vmsn pair), VirtualBox saved states (.sav), Hyper-V .bin, LiME (.lime — preferred Linux capture format), EWF (.E01) of memory (rare), AFF4 (.aff4 — what WinPMEM and AVML produce). Hibernation files (`hiberfil.sys`) and pagefile.sys are NOT directly readable by Volatility 3 — hiberfil must be converted first (see hibr2bin / Hibr2Bin / Volatility's deprecated hibinfo). For pagefile combined analysis, Volatility 3 supports the `--single-swap-locations` flag to attach a pagefile to a raw image.

**Output formats produced.** Pretty-printed tabular text (default), CSV (`-r csv`), JSON (`-r json`), JSONL (`-r jsonl`), "quick" (minimal formatting for speed). Dumped binaries go to a directory specified by `-o`. There is no native HTML or SQLite output.

**Required and useful flags.**
- `-f <image>` — required. Path to memory image.
- `-o <dir>` — output directory for any plugin that dumps files (processes, DLLs, registry hives).
- `-r <renderer>` — renderer choice. `pretty`, `quick`, `csv`, `json`, `jsonl`.
- `--single-location` and `--stackers` — alternative image-loading mechanics for unusual formats.
- `--save-config <file.json>` — save the auto-detected layer stack so subsequent runs skip detection (large speedup on repeated runs of the same image).
- `--cache-path <dir>` — relocate the symbol cache.
- `-vvv` — debug logging. Useful when symbol auto-detection fails.
- `--write-config` — write a configuration JSON that records the detected layers and offsets; reusable with `-c <config.json>`.

**Plugin discovery.**

```
vol -h                          # full plugin list (long)
vol windows.pslist -h            # plugin-specific help
```

**Limitations and failure modes.**

- **Symbol mismatches.** If the target OS build (Windows kernel version, Linux kernel) lacks a matching symbol set in `~/.cache/volatility3/`, the OS-detection plugin (`windows.info` / `banners.Banners`) fails or returns garbage. For Linux this is the dominant failure mode — Linux symbol generation requires `dwarf2json` against the running kernel's vmlinux DWARF data; no pre-built symbol works across distros/kernels.
- **Profile-less Linux pain.** v3's "symbol packs" replace v2 profiles. They are per-kernel-build, not per-distro. Practitioners frequently fall back to Volatility 2 for Linux/macOS.
- **Hibernation files.** Native hiberfil.sys support was removed in v3 — convert with hibr2bin / Hibr2Bin / Comae DumpIt converters first.
- **Crash dump quirks.** BMP-format (bitmap) crash dumps are supported; the older "summary" dump is not.
- **Memory smear.** Long-acquisition smear (where structures are partially overwritten mid-capture) causes plugin failures that look like real corruption. WinPMEM and other paged acquisition tools mitigate this but cannot eliminate it.
- **Page file fusion.** Without `--single-swap-locations pagefile.sys`, paged-out structures are missing — `cmdline`, `envars`, `dlllist`, full `handles` may be partial.
- **netscan reliability.** On Windows 10/11, `windows.netscan` is fragile across builds; if symbols slightly disagree, output can be missing entries or contain artifacts. Compare against `netstat.Netstat` and `windows.sessions` for cross-check.
- **No GUI.** Volatility 3 is CLI-only. The legacy "volshell" interactive REPL exists (`vol -f img volshell`) but is for advanced users.
- **Performance scales with image size and renderer.** A 32 GB image with `pretty` rendering for `windows.dlllist` system-wide can take many minutes; `quick` or `csv` is much faster.

**Gotchas.**

- v3 plugin names are dotted (`windows.pslist`, `linux.pslist`) where v2 used flat names (`pslist`, `linux_pslist`). Old documentation will not run on v3.
- `pslist` reads the active process list; `psscan` walks pool tags and finds hidden/exited processes. Run BOTH and diff.
- `dumpfiles` for an extremely large file (e.g., a 4 GB log) will write a 4 GB binary; check disk space first.
- The `-r json` renderer emits one JSON document per plugin run, not JSONL. For per-row JSON use `-r jsonl`.
- Renderer column ordering changed across Volatility 3 versions. CSV consumers should pin a version or use JSON.
- Volatility 3 does NOT clear PII from output. CSV/JSON dumps contain command lines, usernames, hostnames.

**What it CANNOT do.**

- Cannot analyze a running system — only saved images.
- Cannot decrypt full-disk-encrypted volumes embedded inside the memory image (BitLocker keys can sometimes be extracted via `windows.cachedump` / `windows.lsadump` / `mimikatz`-style flows, but Volatility itself does not decrypt disk).
- Cannot reliably reconstruct mostly-overwritten structures (smeared captures).
- Cannot acquire memory.
- Cannot run YARA against an image without the `yarascan` plugin (which exists: `windows.vadyarascan`, `windows.yarascan`).

**Performance characteristics.**

- A 16 GB Windows 10 raw image runs `windows.info` in ~10–30 s on stock SIFT (SSD-backed).
- `windows.pslist` and `psscan` typically <60 s.
- `windows.malfind` system-wide: 1–5 minutes.
- `timeliner.Timeliner` (cross-plugin event timeline) can take 10+ minutes.
- `yarascan` is the slowest plugin family — scales with rule count × image size, often 30+ minutes on large rule sets.
- Memory footprint is modest (typically <2 GB RAM) because Volatility paginates through the image; it does not load the whole image into RAM.

**Example invocation and abbreviated output.**

```
$ vol -f memory.raw windows.pslist
Volatility 3 Framework 2.5.2
PID    PPID   ImageFileName     Offset(V)        Threads ...
4      0      System            0xfa8001c3a040   91      ...
312    4      smss.exe          0xfa8002cd2300   3       ...
400    312    csrss.exe         0xfa8002a1c060   10      ...
...
```

**Full plugin catalog (Windows — selected).** The Windows namespace alone exposes 70+ plugins. The ones investigators reach for most often:

| Plugin | What it does |
|---|---|
| `windows.info` | KDBG sanity check; emits OS build, kernel base, CR3, MajorOS / MinorOS, layer summary. Always run first. |
| `windows.pslist` | Active process list from `PsActiveProcessHead`. |
| `windows.psscan` | Scans physical memory for `_EPROCESS` pool tags; finds hidden/exited processes. Compare against `pslist` — diff reveals unlinked processes. |
| `windows.pstree` | Parent-child rendering of the process list. |
| `windows.cmdline` | Process command lines (from PEB; requires pagefile for paged-out PEBs). |
| `windows.dlllist` | Loaded DLLs per process. |
| `windows.envars` | Process environment variables. |
| `windows.getsids` | Token SIDs per process. |
| `windows.privileges` | Token privileges (granted vs enabled). |
| `windows.sessions` | Logon sessions (UIs + service sessions). |
| `windows.handles` | Open handle table per process. Filter by `--object-types File,Key,Mutant,Event,Section`. |
| `windows.filescan` | Pool scan for `_FILE_OBJECT`; finds files referenced even if not in any process handle table. |
| `windows.dumpfiles` | Reconstruct file contents from cached pages. Files only partially in memory may dump as zero-padded. |
| `windows.memmap` | Per-process VAD walk; `--dump` writes mapped pages. |
| `windows.vadinfo` | VAD tree details, including private/shared/mapped attributes. |
| `windows.malfind` | Find injected code: VADs with executable+writable protection and PE-header-looking bytes or unmapped paths. |
| `windows.hollowprocesses` | Detect process hollowing: process whose VAD-mapped image differs from on-disk image. |
| `windows.netscan` | TCP/UDP endpoints + connections. Build-fragile. Sometimes augmented by `windows.netstat`. |
| `windows.netstat` | Newer connection scanner; cross-check with `netscan`. |
| `windows.svcscan` | Scan service control manager database in memory. |
| `windows.svclist` | Active service list. |
| `windows.modules` | Active kernel modules. |
| `windows.modscan` | Pool-tag scan for `LDR_DATA_TABLE_ENTRY`; finds unlinked drivers. |
| `windows.driverirp` | Display driver IRP function pointers (rootkit hook detection). |
| `windows.driverscan` | Scan for kernel driver objects. |
| `windows.devicetree` | Kernel device tree. |
| `windows.callbacks` | Kernel callbacks: image-load, process-create, thread-create, registry, FastSysCall. EDR products and rootkits both register here. |
| `windows.ssdt` | System Service Descriptor Table — historical rootkit hook surface. Mostly clean on modern Windows. |
| `windows.ldrmodules` | Cross-check three module lists (InLoadOrder, InMemoryOrder, InInitializationOrder); hidden modules disagree. |
| `windows.mutantscan` | Pool scan for mutex objects; many malware families use distinctive mutex names. |
| `windows.symlinkscan` | Pool scan for symbolic links. |
| `windows.iat` | Process IAT contents (import resolution check). |
| `windows.threads` | Thread objects with start addresses. |
| `windows.thrdscan` | Pool scan for `_ETHREAD`. |
| `windows.virtmap` | Virtual address space layout. |
| `windows.registry.hivelist` | Live registry hives mapped in memory. |
| `windows.registry.hivescan` | Pool scan for hives. |
| `windows.registry.printkey` | Print key + values; needs `--offset` of hive or `--hive-offset`. |
| `windows.registry.userassist` | Decoded UserAssist (ROT13). |
| `windows.registry.amcache` | Parse Amcache from in-memory hive. |
| `windows.registry.shimcache` | Parse ShimCache. |
| `windows.registry.cachedump` | LSA cached domain credentials (DCC hashes). |
| `windows.hashdump` | NTLM hashes from SAM. Requires SYSTEM + SAM hives in memory. |
| `windows.lsadump` | LSA secrets. |
| `windows.cmdscan` | Console host command history (replacement for v2 cmdscan; partial). |
| `windows.consoles` | Console buffer contents. |
| `windows.statistics` | Pool/allocator stats. |
| `windows.symbols` | Display loaded symbol packs. |
| `windows.vadyarascan` | YARA scan VAD ranges only (much faster than full-image yarascan). |
| `windows.yarascan` | YARA scan entire memory image. |
| `windows.suspicious_threads` | Threads whose start addresses fall in unbacked memory (shellcode indicator). |
| `windows.bigpools` | Large pool allocations. |
| `windows.poolscanner` | Generic pool-tag scanner driver. |
| `windows.scheduled_tasks` | Parse in-memory scheduled task structures. |
| `windows.skeleton_key_check` | Heuristic for "skeleton key" LSASS patching. |
| `windows.unloadedmodules` | Kernel unloaded-module list (driver historical record). |
| `windows.crashinfo` | If image is a Microsoft crash dump, summary metadata. |
| `windows.pe_symbols` | Symbols from PE images mapped in memory. |
| `windows.mbrscan`, `windows.mftscan` | Carve MBR / MFT records from raw memory. |
| `windows.shimcachemem` | Memory-resident ShimCache. |
| `windows.crashdump` | Convert raw to crash dump. |
| `timeliner.Timeliner` | Cross-plugin event timeline (many event types into one stream). |

**Plugin namespace prefixes.**
- `windows.*` — Windows.
- `linux.*` — Linux.
- `mac.*` — macOS.
- `timeliner.*` — multi-OS timeline.
- `banners.*` — kernel banner scan (used in auto-OS-detect).
- `frameworkinfo.*` — Volatility self-description.
- `configwriter.*` — config dump utilities.
- `isfinfo.*` — symbol pack info.
- `layerwriter.*` — extract a memory layer.
- `regexscan.*`, `vmscan.*` — generic scanners.

**Renderer details.**
- `pretty` (default): aligned columns, headers, separators. Best for humans; worst for parsing.
- `quick`: minimal formatting, tab-ish output. Fastest. Use when wrapping in shell pipelines.
- `csv`: RFC-4180 CSV with header. Embedded commas are quoted. Embedded newlines may break naive consumers.
- `json`: single JSON document per plugin run, top-level array of row-objects with columns as keys.
- `jsonl`: newline-delimited JSON, one row per line. Streaming-friendly.
- `xlsx`: not built-in to base v3 (was an extension; use csv → xlsx conversion downstream).

**Reusing layer configuration.** Auto-detection of layer stacks (raw → intel32/intel64 → kernel) can take seconds on small images, minutes on multi-OS or unusual images. Save once, reuse:

```
vol -f memory.raw --write-config saved.json windows.info
vol -f memory.raw -c saved.json windows.pslist        # skip detection
```

**Pagefile fusion.** Volatility 3 supports attaching a pagefile so paged-out user-mode pages can be read:

```
vol -f memory.raw --single-swap-locations pagefile.sys windows.cmdline
```

For multiple pagefiles (page.sys + swap files on other drives), specify each `--single-swap-locations` repeatedly.

**YARA scan plugins.**

```
vol -f mem.raw windows.vadyarascan --yara-rules rules.yar              # only VADs
vol -f mem.raw windows.vadyarascan --yara-rules rules.yar --pid 4242   # one PID
vol -f mem.raw windows.yarascan --yara-rules rules.yar                  # whole image
vol -f mem.raw windows.yarascan --yara-rules '/.{4,8}\.evil/' --yara-string  # inline rule
```

`yarascan` accepts a compiled YARA file (`.yarc`) or source `.yar`. Compiled rules load faster on repeat runs.

**Memory smear failure mode (deeper).** When a kernel structure is partially overwritten mid-capture, plugins detect inconsistencies in pool tags / linked-list pointers / object headers. Symptoms:
- `pslist` returns fewer processes than the system actually ran.
- `dlllist` misses DLLs known to be loaded.
- `cmdline` shows truncated or garbled command lines.
- `netscan` returns spurious entries with implausible PIDs.
Mitigations: rerun acquisition with a more pause-heavy tool (DumpIt) or accept the smear and cross-check against `psscan`, `filescan` (which work from raw pool scan and tolerate more damage).

---

## 1.2 Volatility 2 (`vol.py`) — legacy

**Author / maintainer.** The Volatility Foundation. Source: https://github.com/volatilityfoundation/volatility. End-of-life status, still widely used for Linux/macOS work.

**Purpose.** Python 2.7 framework predating v3. Profile-driven (you specify `--profile=Win10x64_19041`).

**Stock SIFT status.** Sometimes included alongside v3 in SIFT for compatibility (Python 2.7 install + the v2 source tree). Many newer SIFT builds omit it; community installs as needed.

**Invocation.**

```
vol.py -f memory.raw imageinfo                          # suggests profile
vol.py -f memory.raw --profile=Win10x64_19041 pslist
vol.py -f memory.raw --profile=Win10x64_19041 cmdscan
vol.py -f memory.raw --profile=Win10x64_19041 consoles
vol.py -f memory.raw --profile=Win10x64_19041 mftparser
vol.py -f memory.raw --profile=Win10x64_19041 shimcache
vol.py -f memory.raw --profile=LinuxUbuntu1804x64 linux_pslist
```

**Why anyone still runs v2.**
- Some plugins never ported: `mftparser` (parses MFT records found in memory), `shimcache`, `cmdscan` (recovers `cmd.exe` history), `consoles` (full console buffer recovery), `screenshot` (GDI window reconstruction), `editbox`, `cryptoscan`.
- Linux / macOS support is older and more profiles are available.
- Community plugins (volatility plugins by FireEye, Splunk Forensic Investigator, etc.) target v2 API.

**Limitations.** Python 2.7 EOL; no security fixes. Profile creation for new Windows builds is manual and slow. CSV output is uneven across plugins.

**Output.** Default tabular text; `--output=csv` / `--output=html` for some plugins; `--dump-dir=<dir>` for plugins that dump.

**Common gotchas.** Wrong profile silently produces garbage — always start with `imageinfo` and cross-check with `kdbgscan`. Profile names like `Win10x64_19041` correspond to specific Windows build numbers (find yours in registry SOFTWARE\Microsoft\Windows NT\CurrentVersion\CurrentBuild).

**v2 plugins still worth running** (not all ported to v3):

| Plugin | Why investigators reach for it |
|---|---|
| `mftparser` | Recovers MFT entries from memory pages — supplements disk MFT when disk is offline. |
| `shimcache` | Pre-v3 ShimCache extraction; v3 `windows.registry.shimcache` is equivalent now. |
| `cmdscan` | Reconstructs command history from `csrss.exe`/`conhost.exe` heap structures. |
| `consoles` | Recovers full console screen buffers (output text). |
| `screenshot` | GDI-based reconstruction of window contents at acquisition time. Renders PNGs. |
| `editbox` | Recovers contents of EDIT controls (text boxes) at acquisition time — useful for chat-window forensics. |
| `cryptoscan` | Scan for TrueCrypt passphrases. |
| `truecryptpassphrase` / `truecryptsummary` / `truecryptmaster` | TrueCrypt-specific recovery. |
| `linux_bash` (v2) | More mature than v3 `linux.bash` historically. |
| `linux_psaux` | Process+args with full path. |
| `linux_check_*` family | check_fop, check_idt, check_syscall, check_modules — rootkit checks. |

**v2 profile build flow (Linux).** For Linux memory you must build a profile matching the target kernel:

```
make -C /lib/modules/$(uname -r)/build M=$PWD/tools/linux modules
dwarfdump -di module.ko > module.dwarf
zip Ubuntu1804_5.4.zip module.dwarf /boot/System.map-5.4.0-x
cp Ubuntu1804_5.4.zip volatility/plugins/overlays/linux/
vol.py --info | grep Linux
vol.py -f mem.lime --profile=LinuxUbuntu1804_5.4x64 linux_pslist
```

This is the reason v2 is painful for Linux work and why most Linux memory triage now uses v3 with a fresh symbol pack generated by `dwarf2json`.

---

## 1.3 Memory Baseliner

**Author / maintainer.** Mike Cohen / Velocidex Enterprises (the same group behind Velociraptor). Source: https://github.com/Velocidex/Memory-Baseliner.

**Purpose.** Compares a memory image against a known-good baseline image of the same OS build, flagging processes, modules, drivers, and handles that diverge from baseline. The "find evil by diffing against clean" approach.

**Stock SIFT status.** Not stock. Pure-Python; pip-installable.

**Invocation.**

```
python3 memory_baseliner.py --baseline good.raw --target suspicious.raw --output diff.csv
```

**Limitations.** Requires a baseline of the same OS build, ideally same patch level. Cross-build diffs produce too many false positives. Best used when an enterprise has clean golden images.

**What it CANNOT do.** Does not perform attribution. Does not identify malware family. It only says "this is different from baseline."

---

## 1.4 MemProcFS (`MemProcFS.exe`, `memprocfs`)

**Author / maintainer.** Ulf Frisk. Source: https://github.com/ufrisk/MemProcFS. Documentation: https://github.com/ufrisk/MemProcFS/wiki.

**Purpose.** Mounts a memory image as a virtual filesystem so the analyst can `cd` into processes, browse handles, read mapped files, dump injected code, etc., as if memory were a directory tree.

**Stock SIFT status.** Not stock on Linux SIFT historically — MemProcFS originated as a Windows tool. Linux port (with FUSE backend) is available and runs on Ubuntu. Symbol packs (the PDB-based "vmm" module) auto-download from Microsoft's Symbol Server on first run.

**Invocation.**

```
MemProcFS -device memory.raw -mount /mnt/mem -forensic 1
ls /mnt/mem/
# name/         pid/        misc/       conf/       sys/        forensic/
ls /mnt/mem/name/svchost.exe-944/
cat /mnt/mem/name/svchost.exe-944/info.txt
ls /mnt/mem/forensic/timeline/
cat /mnt/mem/forensic/timeline/timeline_all.txt | less
```

`-forensic 1` enables the forensic mode (timeline generation, NTFS MFT carving from memory, registry parsing, YARA scan, event reconstruction). It can take 20–60 minutes on a large image but produces dense output.

**Input formats.** Raw, ELF core, Hyper-V .save, VMware .vmem, Microsoft crash dumps, and live targets via PCILeech hardware.

**Output formats.** A virtual filesystem hierarchy:
- `pid/<pid>/` — per-process tree (modules, handles, VAD, threads, files, registry hooks)
- `name/<name>-<pid>/` — same, sorted by image name
- `forensic/timeline/` — composite timeline (TSV/CSV)
- `forensic/findevil/` — anomalies (injected code, hidden modules, suspicious handles)
- `forensic/yara/` — YARA scan results
- `forensic/ntfs/` — recovered MFT records, $J $LogFile fragments
- `forensic/registry/` — parsed registry hives
- `misc/` — system info, kernel version, etc.

**Limitations.**
- Best supported OS: Windows. Linux support exists for some plugins, weaker.
- Symbol auto-download requires internet on first run (offline pre-cache possible).
- `-forensic 1` mode requires significant RAM (often 8–16 GB) and disk for the output.
- Linux build requires `libleechcore` and FUSE.

**What it CANNOT do.** Cannot acquire memory. Cannot analyze macOS images. Cannot replace Volatility for novel plugin development (no Python plugin API of comparable maturity).

**Performance.** A 32 GB Windows 11 image, `-forensic 1`, on a modern laptop: 30–90 minutes initial parse, then sub-second filesystem reads thereafter (everything is cached).

---

## 1.5 WinPMEM, DumpIt — memory acquisition

**WinPMEM.** Maintainer: Velocidex / Mike Cohen (continuation of the original Google Rekall team's pmem family). Source: https://github.com/Velocidex/WinPmem. License: Apache 2.0.

Open-source Windows kernel driver + user-mode loader. Produces raw or AFF4 memory images. Invocation:

```
winpmem_mini_x64_rc2.exe memory.raw                  # raw
winpmem_mini_x64_rc2.exe -o memory.aff4              # AFF4 container
```

Driver signing is required on Windows 10+; the Velocidex builds are properly signed.

**DumpIt.** Originally from MoonSols (Matthieu Suiche); current maintenance under Comae Technologies / Magnet Forensics. Closed-source freeware (free for personal/IR use; commercial license may apply).

```
DumpIt.exe                          # writes <hostname>-<timestamp>.raw to working dir
DumpIt.exe /F output.raw            # explicit output
DumpIt.exe /T DMP /OUTPUT crash.dmp  # produce Microsoft crash dump format
```

DumpIt can produce raw, Microsoft crash dump, or "MAGNET RAM Capture" formats. Magnet RAM Capture (`MRAMCapture64.exe`) is a related tool from Magnet Forensics.

**Limitations of all live memory acquisition.** Smear is unavoidable on busy systems; tools that pause more threads (DumpIt, Magnet RAM) reduce smear but increase user-visible system impact. Acquired image size = physical RAM, not virtual.

**Stock SIFT status.** Neither WinPMEM nor DumpIt runs on Linux — they are Windows agents executed on the target. SIFT may store the resulting images for analysis.

---

## 1.6 hibr2bin / Hibr2Bin — hibernation file extraction

**Author.** Originally Matthieu Suiche; Comae / Magnet Forensics maintains current builds. Closed-source freeware on Windows. Open-source clones exist (e.g., `hibr2bin` in the `forensicstools` PyPI package).

**Purpose.** Decompresses `hiberfil.sys` (the Windows hibernation file) into a raw memory image consumable by Volatility, MemProcFS, etc.

**Invocation (Comae binary, Windows or Wine).**

```
Hibr2Bin /PLATFORM X64 /MAJOR 10 /MINOR 0 /INPUT hiberfil.sys /OUTPUT mem.raw
```

`/MAJOR` and `/MINOR` specify Windows version. Win 10 = 10/0; Win 7 = 6/1; Win 8 = 6/2; Win 8.1 = 6/3.

**Limitations.** Hibernation file may be partial or corrupt if the system did not cleanly suspend. The Xpress compression format used by hiberfil changed between Windows versions; tools must match. Modern Windows 10/11 use "Modern Standby" or fast-startup which can leave a non-standard hiberfil layout.

**What it CANNOT do.** Does not analyze the resulting image — that is Volatility/MemProcFS territory.

---

## 1.7 LiME, AVML — Linux memory acquisition

**LiME (Linux Memory Extractor).** Author: Joe Sylve. Source: https://github.com/504ensicsLabs/LiME. License: GPLv2.

Kernel module that exports physical memory to a file or over the network. Build per target kernel:

```
make
insmod ./lime-<kernel-version>.ko "path=/mnt/usb/mem.lime format=lime"
insmod ./lime.ko "path=tcp:4444 format=lime"           # network export
```

Formats: `raw`, `padded`, `lime` (the native LiME format with section metadata — preferred for Volatility 3).

**AVML (Acquire Volatile Memory for Linux).** Author: Microsoft. Source: https://github.com/microsoft/avml. License: MIT.

Userland tool (no kernel module to build per kernel). Reads `/dev/crash`, `/proc/kcore`, or `/dev/mem` and writes an LiME-format image. Linux only.

```
sudo avml /tmp/mem.lime
sudo avml --compress /tmp/mem.lime.zst        # zstd-compressed output
sudo avml --source /proc/kcore /tmp/mem.lime
```

**linpmem.** Velocidex revival of the historical Rekall Linux pmem driver. Source: https://github.com/Velocidex/c-aff4 (linpmem branch). Less commonly used today than AVML for triage because AVML needs no module build.

**Limitations.** All Linux memory acquisition requires root. Kernel hardening (`kernel.kptr_restrict`, `kernel.dmesg_restrict`, lockdown mode, Secure Boot) can block access to `/proc/kcore` and `/dev/mem`. AVML automatically tries multiple sources and falls back. Container hosts that run under hypervisor escape protections may simply refuse.

**Linux memory analysis specifics.** Once an image is acquired:

- Volatility 3 needs a symbol pack for the exact kernel. Generate with `dwarf2json linux --elf vmlinux > kernel.json`, place in `volatility3/symbols/linux/`.
- Useful Volatility 3 Linux plugins:
  - `linux.pslist` — task list walk.
  - `linux.psscan` — pool scan equivalent for `task_struct`.
  - `linux.pstree` — process tree.
  - `linux.psaux` — full process args.
  - `linux.bash` — bash history from heap.
  - `linux.lsmod` — loaded kernel modules.
  - `linux.check_modules` — modules in dependency list but not in module list (rootkit indicator).
  - `linux.check_syscall` — syscall table integrity.
  - `linux.check_idt` — IDT integrity.
  - `linux.check_creds` — credentials shared across unrelated processes.
  - `linux.malfind` — anomalous VMAs.
  - `linux.elfs` — ELF images in memory.
  - `linux.bash_env` — environment of bash processes.
  - `linux.netstat` — network connections.
  - `linux.tty_check` — `tty_struct` integrity.
  - `linux.proc_maps` — `/proc/<pid>/maps` reconstruction.
  - `linux.iomem` — `/proc/iomem` reconstruction.
  - `linux.kmsg` — kernel ring buffer.
  - `linux.envars` — environment variables.
  - `linux.library_list` — shared libraries.
  - `linux.boottime` — boot timestamp.
  - `linux.mountinfo` — mount table.
  - `linux.sockstat` — socket stats.
  - `linux.psscan` — pool scan for stealth process detection.
  - `linux.tracing.tracefs` — eBPF / tracefs program inspection.

**eBPF rootkits** are increasingly common; `linux.tracing.tracefs` and `linux.tracing.ftrace` are the relevant plugins, complemented by Velociraptor's `Linux.Detection.Tracee` artifact.

---

# 2. DISK ACQUISITION, IMAGING, AND MOUNTING

## 2.1 ewfacquire, ewfmount, ewfverify, ewfinfo (libewf)

**Author / maintainer.** Joachim Metz. Source: https://github.com/libyal/libewf. License: LGPLv3.

**Purpose.** Read/write/verify EnCase Expert Witness Format (E01/Ex01/L01) forensic disk images.

**Stock SIFT status.** Installed.

**Invocations.**

```
ewfacquire /dev/sda                       # interactive acquisition wizard
ewfacquire -t case_001 -d sha256 -e Operator -c IR-2026-01 -E "case notes" \
           -m removable -M logical -f encase6 -S 2G /dev/sda

ewfinfo image.E01                         # case header + segment metadata
ewfverify image.E01                       # recompute hash, compare embedded
ewfmount image.E01 /mnt/ewf                # FUSE-mount E01 set as a flat raw view
ls /mnt/ewf
# ewf1                                     <- treat /mnt/ewf/ewf1 as a raw disk
mmls /mnt/ewf/ewf1                        # partition table via Sleuth Kit
```

`ewfmount` is critical — it bridges E01 to every tool that only reads raw images.

**Output formats produced.** EWF (.E01 / .Ex01), EWF-L (.L01 logical), SMART (.s01), raw (`-f raw`). `ewfinfo` outputs human text or `-f dfxml` for DFXML.

**Useful flags (ewfacquire).**
- `-d <hash>` — md5, sha1, sha256 (multiple allowed: `-d sha256 -d sha1`).
- `-c <case>` — case number metadata.
- `-D <description>` — evidence description.
- `-e <examiner>` — examiner name.
- `-E <notes>` — notes (multi-line).
- `-m removable|fixed|optical|memory` — media type.
- `-M physical|logical` — physical drive vs logical volume.
- `-f encase5|encase6|encase7|smart|ewf|raw` — output format.
- `-S <size>` — segment size (commonly 1G, 2G, 4G).
- `-b 64|128|256|512|1024|2048|4096|8192|16384|32768` — sector-per-chunk.
- `-c best|fast|empty-block|none` — compression. `empty-block` is the speed/compression sweet spot for SSDs.

**Limitations.**
- `ewfacquire` cannot acquire to .E01 over the network in a single command (use `ewfacquirestream`).
- `ewfmount` provides a flat raw view but no partition slicing — you need Sleuth Kit / loop devices to mount partitions.
- Cannot read AFF or AFF4.
- Cannot acquire BitLocker-encrypted disks in unlocked form (acquires ciphertext; decryption is separate).

**Performance.** SHA-256 + best compression on a 1 TB drive at full SATA speed: typically 6–10 hours, bottlenecked by source disk read speed and CPU (compression). `empty-block` compression on SSDs runs much faster.

**Gotchas.** E01 segment files (`.E02`, `.E03`...) must all be present and named consistently. `ewfverify` reads the embedded hash from the case header and recomputes — if the segments were tampered with or truncated, it will fail loudly.

---

## 2.2 dc3dd, dcfldd, dd_rescue

**dc3dd.** Author: Jesse Kornblum (originally), DoD Cyber Crime Center fork. Source: https://sourceforge.net/projects/dc3dd/. License: GPL.

Forensic-aware `dd` with on-the-fly hashing, progress bar, and split output. Installed on SIFT.

```
dc3dd if=/dev/sda hash=sha256 hash=md5 log=case.log hashlog=case.hashes of=image.raw
dc3dd if=/dev/sda hash=sha256 of=image.raw ofs=split.000 ofsz=2G
```

**dcfldd.** Forensic `dd` by the Defense Computer Forensics Lab. Similar feature set. Pre-dates `dc3dd`. Less actively maintained.

```
dcfldd if=/dev/sda hash=sha256 hashlog=hashes.log of=image.raw bs=4M
```

**dd_rescue (ddrescue is different — section 2.3).** Author: Kurt Garloff. Recovery-oriented `dd` with error retry. Less used today than GNU `ddrescue`.

**Gotchas.** Block size matters for performance — 4M is typical; 64K is the kernel default for `dd` and is slow. None of these can recover unreadable sectors from a failing disk as well as GNU `ddrescue`.

---

## 2.3 GNU ddrescue

**Author / maintainer.** Antonio Diaz Diaz / GNU. Source: https://www.gnu.org/software/ddrescue/. License: GPLv2.

**Purpose.** Imaging dying drives. Reads good sectors first, skips bad areas, then retries the bad areas with smaller reads. Maintains a "map file" (formerly "log file") of progress, supporting resumable imaging.

```
ddrescue -d -r3 /dev/sda image.raw map.log         # 3 retries, direct I/O
ddrescue -R -r10 /dev/sda image.raw map.log        # second pass, reverse direction
ddrescuelog -t map.log                              # summary of recovery status
```

**Output.** Raw image + a map file. The map file is text describing which byte ranges were OK, skipped, retried, failed.

**Limitations.** Not forensically integrity-stamped on its own — pipe through `sha256sum` after, or wrap with `dc3dd`.

---

## 2.4 xmount

**Author / maintainer.** Daniel Gillen. Source: https://www.pinguin.lu/xmount. License: GPLv3.

**Purpose.** FUSE mount that converts on the fly between disk image formats. Read an E01 and present it as raw, VMDK, VDI, VHD — useful for booting an image in a VM without re-imaging.

```
xmount --in ewf image.E01 --out raw /mnt/xmount
xmount --in ewf image.E01 --out vmdk /mnt/xmount     # then add to VirtualBox/VMware
xmount --in ewf --cache cache.ovl image.E01 --out vdi /mnt/xmount   # write-cached
```

Write cache lets you boot the image read-write without modifying the original — writes go to the overlay file.

---

## 2.5 imagemounter

**Author / maintainer.** Ralph Broenink. Source: https://github.com/ralphje/imagemounter. License: MIT.

**Purpose.** Python wrapper that orchestrates `ewfmount` + `mmls` + loop devices + LVM detection + VSS expansion + LUKS unlock, so one command mounts every partition (and every shadow copy) of a forensic image at sensible mountpoints.

```
imount image.E01                                    # mount everything mountable
imount --vss image.E01                              # also expose Volume Shadow Copies
imount --reconstruct image.E01                      # recreate Windows drive letters under /mnt
imount --unmount                                    # clean up
```

**Stock SIFT status.** Installed.

**Limitations.** BitLocker requires the recovery key passed in. Some exotic filesystems (ReFS) cannot be mounted because Linux kernel lacks a driver — imagemounter cannot fix that.

**Mount-edge-case reference.**

- **Dirty NTFS.** A non-cleanly-unmounted NTFS often refuses read-only mount via `ntfs-3g` without `recover` or `remove_hiberfile` options. `mount -o ro,loop,show_sys_files,streams_interface=windows,recover /dev/loop0p2 /mnt/x` is the canonical incantation. Imagemounter does this automatically.
- **Hibernated NTFS.** `hiberfil.sys` present + system was hibernated → ntfs-3g refuses unless `-o remove_hiberfile` (which would modify; for forensic READ use `-o ro,recover,norecover`).
- **Dynamic disks (LDM).** Microsoft LDM (legacy dynamic disks) require `ldmtool` to assemble before mounting.
- **Storage Spaces (newer Windows).** Far less Linux-friendly. Often requires booting Windows to extract data; some progress in `dislocker`-style tools but not universally reliable.
- **GPT + protective MBR.** `mmls` handles both; if it only shows the protective MBR, force `-t gpt`.
- **APFS.** Linux read support via `apfs-fuse` (https://github.com/sgan81/apfs-fuse). Slow and limited; not via imagemounter directly.
- **HFS+ with case-sensitive volumes.** Mount with `-o ro,force` if dirty.
- **ext4 with metadata checksums.** Some old ddrescue images of ext4 fail mount due to journal replay attempts; mount with `-o ro,noload` to skip journal.
- **LVM volume groups.** Activated with `vgscan && vgchange -ay` after loop-device setup; imagemounter handles this.
- **VxVM / VxFS.** Veritas. Linux can mount read-only via the vxfs module on older kernels; modern kernels often lack support.
- **ZFS.** `zfs import` after exposing pool members via loop devices. Read-only import: `zpool import -o readonly=on -R /mnt/zfs <pool>`.
- **BTRFS with subvolumes.** Mount root, then `btrfs subvolume list` and mount subvolumes explicitly.

**Loop device life-cycle.**

```
losetup -f --show -r -P /path/to/image.raw     # -P creates partition devices /dev/loopXpY
mount -o ro,loop /dev/loop0p2 /mnt/p2
...
umount /mnt/p2
losetup -d /dev/loop0
```

`-r` makes the loop device read-only — essential for evidence preservation.

---

## 2.6 libvshadow (vshadowinfo, vshadowmount)

**Author / maintainer.** Joachim Metz. Source: https://github.com/libyal/libvshadow. License: LGPLv3.

**Purpose.** Read NTFS Volume Shadow Copies (VSS). Each shadow copy is a point-in-time snapshot; investigators routinely find deleted files and prior states of registry hives in VSS.

**Stock SIFT status.** Installed.

```
vshadowinfo /dev/loop0p2                            # list shadow copies on a mounted NTFS
vshadowmount /dev/loop0p2 /mnt/vss
ls /mnt/vss
# vss1  vss2  vss3
mount -o ro,loop /mnt/vss/vss1 /mnt/vss1            # then mount each shadow as a fs
```

**Limitations.** VSS only exists on NTFS volumes. Each shadow copy is a delta; missing block tables (corruption, partial image) break the mount.

---

## 2.7 libbde (BitLocker)

**Author / maintainer.** Joachim Metz. https://github.com/libyal/libbde.

```
bdeinfo /dev/loop0p2                                # show encryption metadata
bdemount -r <recovery-key> /dev/loop0p2 /mnt/bde
bdemount -p <password> /dev/loop0p2 /mnt/bde
bdemount -k <startup-key.bek> /dev/loop0p2 /mnt/bde
mount -o ro,loop /mnt/bde/bde1 /mnt/clear
```

Supports recovery password, user password, startup key (`.bek`), full volume master key (FVMK).

**Limitations.** Cannot brute force. Cannot bypass TPM-only protectors without the recovery key. Cannot read Windows 10 1903+ XTS-AES if compiled against an old libbde — recent releases support XTS-AES-128/256.

---

## 2.8 libfvde (FileVault 2)

**Author.** Joachim Metz. https://github.com/libyal/libfvde.

```
fvdeinfo -e EncryptedRoot.plist.wipekey -p <password> /dev/loop0
fvdemount -e EncryptedRoot.plist.wipekey -p <password> /dev/loop0 /mnt/fv
```

Requires the `EncryptedRoot.plist.wipekey` from the Recovery HD partition.

**Limitations.** APFS-FileVault (modern macOS) is supported partially; very recent macOS versions outpace the library. T2/Apple Silicon machines complicate the picture — keys live in the Secure Enclave.

---

## 2.9 libluksde

**Author.** Joachim Metz. https://github.com/libyal/libluksde.

Read-only access to LUKS1 and LUKS2 volumes given a passphrase or key file. Note: most Linux systems can simply use `cryptsetup luksOpen`; libluksde matters when working on a non-Linux SIFT-equivalent or when avoiding kernel mounts.

---

# 3. FILESYSTEM ANALYSIS — THE SLEUTH KIT FAMILY

## 3.1 The Sleuth Kit (TSK)

**Author / maintainer.** Brian Carrier. Source: https://github.com/sleuthkit/sleuthkit. License: CPL / IBM Public License (effectively open).

**Purpose.** Library + command-line tools for analyzing disk images at the filesystem and volume level — NTFS, FAT, ExFAT, ext2/3/4, HFS+, UFS, ISO9660, YAFFS2.

**Stock SIFT status.** Installed. Sleuth Kit is one of the most foundational pieces of SIFT.

The tools follow a naming convention: prefix indicates layer.

| Prefix | Layer | Examples |
|---|---|---|
| `mm` | media management (partitions, disk labels) | `mmls`, `mmstat`, `mmcat` |
| `fs` | filesystem | `fsstat`, `fls` |
| `i` | inode / MFT entry | `istat`, `icat`, `ils`, `ifind` |
| `f` | file (filename layer) | `fls`, `fcat`, `ffind` |
| `blk` | data block | `blkls`, `blkcat`, `blkstat`, `blkcalc` |
| `j` | journal (ext / NTFS $LogFile) | `jls`, `jcat` |
| `srch` | content search | `srch_strings` |

**Common patterns.**

```
mmls image.raw                                # partition table
fsstat -o 2048 image.raw                     # fs info for partition at offset 2048
fls -r -m C: -o 2048 image.raw > bodyfile    # full recursive filename listing in body-file format
fls -d -o 2048 image.raw                     # deleted files only
istat -o 2048 image.raw 12345                # info for MFT entry 12345
icat -o 2048 image.raw 12345 > recovered.bin # extract file contents by inode
icat -o 2048 image.raw 12345-128-3 > stream  # alternate data stream / specific attribute
ils -o 2048 image.raw                        # all inodes, with metadata
blkls -o 2048 image.raw > unallocated.bin    # extract unallocated space (then run bulk_extractor)
blkstat -o 2048 image.raw 1234567            # info about block 1234567
tsk_recover -e -o 2048 image.raw ./recovered/  # recover all files (allocated + unallocated)
tsk_recover -a -o 2048 image.raw ./allocated/  # allocated only
srch_strings -a -t d image.raw | grep cookie  # raw image strings with byte offsets
```

**Body-file format** (output of `fls -m`): a SleuthKit-defined pipe-delimited format:

```
MD5|name|inode|mode_as_string|UID|GID|size|atime|mtime|ctime|crtime
```

That body-file is the input to `mactime` (next section).

**Limitations.**
- TSK on NTFS does not parse $UsnJrnl, $LogFile journal records, or $TxF transactional logs — use Eric Zimmerman's `MFTECmd` for $LogFile/$J/$UsnJrnl.
- TSK reads MFT but does NOT interpret all NTFS attributes (sparse files, reparse points are partial).
- ReFS support: minimal/none.
- Encrypted volumes must be unlocked first (libbde / libfvde / libluksde).
- `tsk_recover` extracts named files; orphaned/carved-from-unallocated content needs `blkls` + `bulk_extractor`/`foremost`/`scalpel`.

**Performance.** `fls -r` on a 500 GB NTFS image: 10–40 minutes. `tsk_recover -e` of every file: hours, disk-bound.

**Tool-by-tool TSK detail.**

| Tool | Purpose | Key flags |
|---|---|---|
| `mmls` | List volume/partition table (DOS MBR, GPT, BSD disklabel, Apple, Sun VTOC) | `-t <type>` force type; `-B` show in 512-byte sectors |
| `mmstat` | Volume type info | none specific |
| `mmcat` | Output a partition's bytes to stdout | requires partition index |
| `fsstat` | Filesystem metadata (cluster size, volume serial, mount state, free space, MFT info) | `-o <offset>` partition offset |
| `fls` | List files at filename layer; recurse with `-r`, deleted with `-d`, body file with `-m` | `-r` recurse, `-d` deleted, `-u` allocated, `-m <mount>` mount-point prefix for body file, `-p` full path, `-s <seconds>` timestamp offset for time-zone correction, `-z <tz>` time zone, `-l` long listing |
| `ifind` | Inode that contains given block, or that points to given filename | `-d <unit>` find inode by block; `-n <name>` find by name |
| `ils` | Inode-layer metadata (every inode + state + sizes + MAC times) | `-e` every inode, `-O` orphans only, `-r` removed only, `-m <mount>` body file output |
| `istat` | Single-inode detail | `-z <tz>`, `-s <secs>` |
| `icat` | Extract content by inode (resp. inode-attribute-type-id triple) | `-r` recover (try harder for partial), `-s` slack, `-h` no holes |
| `ffind` | Filename pointing to given inode | `-a` all matches, `-d` deleted only |
| `blkls` | Stream of data unit content (default: unallocated) | `-a` allocated only, `-A` allocated+unallocated, `-e` every block, `-s` slack, `-l` walk and list |
| `blkcat` | Specific block contents | `-h <fmt>` hex/ascii/swap output |
| `blkstat` | Metadata about a single block (allocated? meta? sparse?) | none |
| `blkcalc` | Convert between image-block and unalloc-block addressing | `-d <addr>` dd-address to dls-address, `-s <addr>` reverse |
| `jls` | List filesystem journal entries (NTFS $LogFile, ext journal) | `-f <fstype>` |
| `jcat` | Dump specific journal entry | `<imgfile> <inum>` |
| `fcat` | Output file by filename path (instead of inode) | `-o <offset>` |
| `srch_strings` | Strings + offset (TSK-flavored) | `-a` all, `-t d|x` offset format, `-e b|l|L|B` Unicode endianness |
| `tsk_recover` | Recover all files (allocated, deleted, or all) | `-a` allocated, `-d` deleted, `-e` everything (allocated + unallocated by carving) |
| `tsk_loaddb` | Load image metadata into a sqlite DB for Autopsy | `-d <db>` |
| `tsk_gettimes` | Produce a TSK body file directly (older alternative to `fls -m`) | `-z <tz>` |
| `tsk_comparedir` | Compare a TSK image against a live directory (consistency check) | `-z <tz>`, `-n` no recurse |
| `disk_sreset` | Reset HPA/DCO on physical disk before imaging | live disk only |
| `hfind` | Lookup hash against a known-hash database | `-i nsrl-md5` |

**MFT-specific TSK behaviors.** On NTFS, inode numbers are MFT record numbers but TSK extends with a type-id and attribute-id triple: `inum-type-id` (e.g., `12345-128-3` is MFT entry 12345, attribute type 128 = $DATA, attribute id 3 = third data stream). This lets `icat 12345-128-3` extract a named alternate data stream.

**FILE_NAME ($30) vs STANDARD_INFORMATION ($10).** Both contain MACB timestamps. $10 is updated by most file operations; $30 is updated only on rename/move. Timestomp tools that overwrite $10 leave $30 telltales — a discrepancy between $10 and $30 timestamps on the same MFT entry is a classic timestomp signal. `MFTECmd` is generally clearer about this; TSK shows both via `istat`.

**Body file format (canonical column meaning).**

```
0|/Users/admin/notes.txt|12345|r/rrwxrwxrwx|0|0|2048|1748000000|1748000005|1748000010|1747999990
```

Columns:
1. MD5 (or 0 if not computed).
2. Full filename with mount-point prefix.
3. Inode number.
4. File mode (ls-like).
5. UID.
6. GID.
7. File size in bytes.
8. Access time (epoch).
9. Modification time (epoch).
10. Inode change time / NTFS MFT change (epoch).
11. Birth/creation time (epoch).

mactime then processes these into the human-friendly chronological view.

---

## 3.2 mactime

**Purpose.** Convert a body-file (from `fls` or other source) into a chronological CSV timeline.

```
fls -r -m C: -o 2048 image.raw > body
mactime -b body -d -y > timeline.csv          # -d = delimited (CSV), -y = ISO date
mactime -b body -d -y 2025-01-01..2025-01-15  # date-range filter
```

Output columns: `Date,Size,Type,Mode,UID,GID,Meta,File Name`. Type encodes the MAC attribute: `m...` modify, `.a..` access, `..c.` change, `...b` birth.

**Limitations.** Only produces a filesystem-MAC timeline — no registry events, no event log events, no browser history. For a super-timeline you need plaso. mactime is a building block, not a destination.

---

# 4. TIMELINE GENERATION (plaso)

## 4.1 plaso / log2timeline.py

**Author / maintainer.** Originally Kristinn Gudjonsson; project lead currently Joachim Metz. Source: https://github.com/log2timeline/plaso. License: Apache 2.0. Documentation: https://plaso.readthedocs.io/.

**Purpose.** Extract event-bearing artifacts from a disk image (or mounted directory) and store them in a Plaso storage file. plaso is the canonical "super-timeline" engine — it parses hundreds of artifact types into a unified event stream.

**Stock SIFT status.** Installed.

**Invocation.**

```
log2timeline.py --storage_file case.plaso image.E01
log2timeline.py --storage_file case.plaso /mnt/case_root
log2timeline.py --storage_file case.plaso --parsers "winreg,winevtx,prefetch" image.E01
log2timeline.py --storage_file case.plaso --partitions all --vss_stores all image.E01
log2timeline.py --storage_file case.plaso --hashers md5,sha256 image.E01
log2timeline.py --storage_file case.plaso --workers 8 image.E01
log2timeline.py --storage_file case.plaso --status_view window image.E01
```

**Useful flags.**

- `--parsers <list>` — restrict parsers. List with `log2timeline.py --parsers list`.
- `--partitions <indices|all>` — which partitions to process.
- `--vss_stores <indices|all>` — include Volume Shadow Copies (huge timeline growth).
- `--hashers <list>` — compute hashes during extraction (md5, sha1, sha256).
- `--workers N` — worker process count (defaults to CPU count - 1).
- `--unattended` — non-interactive; useful in scripts.
- `--yara_rules <file>` — run YARA rules during extraction and tag matches.
- `--status_view window|linear|none` — progress display.
- `--temporary_directory <dir>` — control where plaso writes spool data.
- `--profiling tasks` — emit profiling info to diagnose slow parsers.

**Parser categories.** plaso has 100+ parsers organized by artifact type. Key families:

- Windows: `mft`, `usnjrnl`, `prefetch`, `winreg` (with dozens of sub-plugins), `winevtx` (legacy `evt` also), `winjob` (scheduled tasks), `winfirewall`, `winlnk`, `winjlink` (jump lists), `winsetupapi`, `srum`, `recycle_bin`, `recycle_bin_info2`, `bagmru`, `mrulist`, `mrulistex`, `winuser_run`, `winrar`, `chrome_*`, `firefox_*`, `iexplore_*`, `edge_*`, `skype`, `mssql_errlog`.
- Linux: `bash_history`, `zsh_history`, `cups_ipp`, `syslog`, `selinux`, `utmp`, `wtmp`, `dpkg`, `apt_history`.
- macOS: `asl`, `bsm`, `cups_ipp`, `mac_appfirewall_log`, `mac_keychain`, `mac_securityd`, `mac_wifi`, `plist`, `spotlight_volume`, `spotlight_storedb`.
- Cross-platform: `filestat` (last-resort MAC stamps), `pcap` (network), `sqlite` (with plugin per app), `pe`, `winregistry` plugins.

**plaso storage file (`.plaso`).** A SQLite-based container holding parsed events with attributes, source metadata, and parser provenance. It is binary and is consumed by `psort.py`, `psteal.py`, and `pinfo.py`.

**Limitations.**
- Slow. A 250 GB Windows image with full parsers and VSS can take 6–24 hours.
- Memory hungry under parallelism; plaso 20240126+ improved but workers can OOM.
- Some plaso parsers have not kept pace with Windows changes (e.g., ETW recent events). Eric Zimmerman tools may produce better output for specific artifacts.
- Unicode + Windows codepage edge cases occasionally mangle filenames.
- Output is event-centric — there is no first-class "session" or "process" concept.

**Performance characteristics.**
- Disk image parsing is I/O-bound; SSD storage of the image cuts time dramatically.
- CPU-bound on the registry parser; `winreg` parser benefits most from more workers.
- A typical 50 GB triage VHD: 30–90 min depending on parser set.
- Storage file size: roughly 1–10% of source image size for a full timeline.

**Gotchas.**
- `--vss_stores all` can multiply runtime and storage by 10x.
- Time zone metadata: plaso records UTC and source TZ. If the image's TZ is not auto-detected, pass `--timezone "America/Los_Angeles"`.
- The progress display sometimes shows "0 events extracted" for long stretches — that means it is parsing $MFT silently, not stalled.
- `log2timeline.py` from a non-mounted E01 will internally mount via `dfvfs` (a layer of plaso) and may stumble on Bitlocker or unusual partitions — pre-mounting via `ewfmount` + `imagemounter` is often more reliable.

**Plaso parser catalog (deeper enumeration).** Parsers are organized into named "presets" — running `--parsers list` shows all. Major presets:

| Preset | What it includes |
|---|---|
| `win_gen` | Generic Windows parsers (no registry/eventlog details). |
| `win7` | Win7-specific extra parsers. |
| `win7_slow` | Slower Win7 parsers (USN journal, etc.). |
| `win_xp` | XP-specific (INFO2 recycle bin, etc.). |
| `webhist` | Browser history across Chrome, Firefox, IE, Edge, Safari, Opera. |
| `macos` | macOS plist + bsm + asl + keychain + cups. |
| `linux` | utmp + wtmp + bash_history + syslog + dpkg + apt + selinux. |

Selective parser invocation:

```
log2timeline.py --parsers '!filestat' ...                  # exclude filestat (default-on, very noisy)
log2timeline.py --parsers 'winreg,winevtx,prefetch' ...    # restrict
log2timeline.py --parsers 'webhist,linux' ...               # multi-preset
```

`filestat` is the catch-all parser that emits NTFS / ext / HFS+ MAC times from `fls`-equivalent walks. It is on by default and produces the largest event count by far. Investigators frequently exclude it when they only need event-bearing artifacts.

**Important parser-specific notes.**

- `winreg` parser has 60+ sub-plugins (`winreg/userassist`, `winreg/run`, `winreg/typedurls`, `winreg/mountpoints2`, `winreg/networkdrives`, etc.). To narrow inside winreg: `--parsers winreg --registry-plugins userassist,run`.
- `winevtx` parser does not apply EvtxECmd maps — fields appear under generic `xml_string` or `event_data` attributes. For map-style enrichment, run EvtxECmd separately.
- `sqlite` parser depends on per-app plugins. Without a plugin, an unknown sqlite DB is skipped silently.
- `pe` parser extracts PE compile timestamps for every PE on disk — useful but slow.
- `mft` parser produces $STANDARD_INFORMATION and $FILE_NAME timestamps for every MFT record (one record can produce 8+ events).
- `usnjrnl` parser can produce 10x more events than `mft` on a busy system.

**Plaso storage file structure.** A `.plaso` file is internally a SQLite-backed container with the following primary tables/streams:
- `metadata` — collection metadata, source paths, plaso version, timezone.
- `events` — per-event records: timestamp, parser, source, attributes (JSON blob).
- `event_data` — heavier per-event payload referenced by events.
- `event_tags` — tag annotations (Sigma matches, manual tags from `psort.py --tags`).
- `analysis_reports` — output of analysis plugins.
- `extraction_warnings` — parser errors.
- `recovery_warnings` — recovery events.

`pinfo.py --sections all <file>.plaso` enumerates every section.

**Analysis plugins.** plaso also has analysis-mode plugins that run at `psort.py` time:
- `tagging` — apply YAML rule files to tag events.
- `windows_services` — tag events related to service install/start.
- `viper` / `virustotal` — query external services (network required).
- `nsrlsvr` — known-good hash lookup via NSRL.
- `sessionize` — group events into sessions.
- `browser_search` — aggregate browser search queries.

Invoke:

```
psort.py --analysis tagging --tagging-file tag_windows.txt -o l2tcsv -w out.csv case.plaso
```

---

## 4.2 psort.py

**Purpose.** Sort, filter, and render a Plaso storage file into a human or machine output format.

```
psort.py -o l2tcsv -w timeline.csv case.plaso
psort.py -o json_line -w timeline.jsonl case.plaso
psort.py -o elastic --index_name case_001 case.plaso
psort.py -o l2tcsv -w timeline.csv case.plaso "date > '2025-06-01' AND date < '2025-06-08'"
psort.py -o l2tcsv -w timeline.csv case.plaso "parser is 'winevtx' AND source_long contains '4624'"
```

**Output modules.**
- `l2tcsv` — classic super-timeline CSV. Columns: `date,time,timezone,MACB,source,sourcetype,type,user,host,short,desc,version,filename,inode,notes,format,extra`.
- `l2ttln` — TLN (Timeline) format.
- `dynamic` — column selection: `-o dynamic --fields datetime,source,message`.
- `json_line` — JSONL, one event per line. Best for downstream tooling.
- `elastic` / `elastic_ts` — index directly into Elasticsearch / Timesketch.
- `kml` — geographic events.
- `xlsx` — Excel.
- `4n6time_sqlite` / `4n6time_mysql` — SQLite/MySQL output.
- `null` — count events, write nothing.

**Filter language.** A SQL-like syntax operating on plaso event attributes:

```
date > '2025-06-01 00:00:00' AND parser is 'winreg' AND message contains 'Run'
attribute_data_type is 'windows:registry:userassist' AND user is 'mr.evil'
```

Performance note: filters at output time still scan the whole storage file. For repeated queries against the same case, push events into Elasticsearch / Timesketch.

---

## 4.3 psteal.py

**Purpose.** Combines `log2timeline.py` + `psort.py` in one command — extract and render in a single shot. Convenient but less flexible.

```
psteal.py --source image.E01 -o l2tcsv -w timeline.csv
```

---

## 4.4 pinfo.py

**Purpose.** Inspect a Plaso storage file. Counts of events per parser, processing statistics, errors.

```
pinfo.py case.plaso
pinfo.py --output_format json case.plaso
pinfo.py --sections events case.plaso
pinfo.py --sections errors case.plaso       # parser errors during extraction
pinfo.py --compare case_a.plaso case_b.plaso
```

---

## 4.5 image_export.py

**Purpose.** Extract files of interest from a forensic image using filters or a "Forensic Artifact" definition file (https://github.com/ForensicArtifacts/artifacts).

```
image_export.py --artifact_filters WindowsEventLogs -w out/ image.E01
image_export.py --names "*.evtx,*.lnk,*.pf" -w out/ image.E01
image_export.py --extensions evtx,lnk,pf,dat -w out/ image.E01
image_export.py --signatures lnk,exe,zip -w out/ image.E01
image_export.py --date-filter 'ctime,2025-06-01,2025-06-08' -w out/ image.E01
```

The Forensic Artifacts project provides hundreds of pre-defined artifact bundles (e.g., `WindowsPrefetchFiles`, `WindowsEventLogs`, `LinuxAuthLogs`).

**Selected widely-used artifact bundles.**

| Bundle | Contents |
|---|---|
| `WindowsEventLogs` | All EVTX in `%SystemRoot%\System32\winevt\Logs`. |
| `WindowsXMLEventLogs` | XML-exported event logs. |
| `WindowsRegistryFilesAndTransactionLogs` | SAM, SECURITY, SYSTEM, SOFTWARE, NTUSER.DAT, UsrClass.dat + LOG/LOG1/LOG2. |
| `WindowsPrefetchFiles` | `%SystemRoot%\Prefetch\*.pf`. |
| `WindowsAmCacheHveFile` | `Amcache.hve`. |
| `WindowsRecycleBin` | `\$Recycle.Bin\**`. |
| `WindowsLnkFiles` | All `.lnk` under user profiles. |
| `WindowsScheduledTasks` | Task XML and Job legacy formats. |
| `WindowsAppCompatCache` | SYSTEM hive (then post-process with AppCompatCacheParser). |
| `WindowsSRUMDatabase` | `SRUDB.dat` + SOFTWARE hive for resolution. |
| `WindowsActivitiesCacheDatabase` | Per-user `ActivitiesCache.db`. |
| `WindowsBrowserCacheAndCookies` | Major browsers' cache + cookies. |
| `WindowsServicesAndDrivers` | Driver and service-config files. |
| `WindowsPowerShellTranscripts` | `%SystemDrive%\Users\*\Documents\PowerShell_transcript*`. |
| `WindowsWMIRepository` | `\System32\wbem\Repository\*`. |
| `LinuxAuthLogs` | `/var/log/auth.log*`, `/var/log/secure*`. |
| `LinuxCronLogs` | cron log family. |
| `LinuxSyslogFiles` | `/var/log/syslog*`, `/var/log/messages*`. |
| `LinuxBashHistoryFile` | Per-user `.bash_history`. |
| `LinuxSudoConfiguration` | `/etc/sudoers`, `/etc/sudoers.d/*`. |
| `MacOSAppleSystemLogs` | ASL+unified-logging tracev3 files. |
| `MacOSKeychainFiles` | Keychain files. |
| `MacOSQuarantineEvents` | `com.apple.LaunchServices.QuarantineEventsV2`. |
| `MacOSSpotlightDatabase` | `.Spotlight-V100/store.db`. |

The full list is at https://github.com/ForensicArtifacts/artifacts/tree/main/artifacts/data.

---

## 4.6 dftimewolf

**Author / maintainer.** Google / Tomchop. Source: https://github.com/log2timeline/dftimewolf. License: Apache 2.0.

**Purpose.** Orchestration framework for chaining plaso (and other) tools into reproducible recipes. Recipes are YAML-defined sequences of "modules" (collect from GCS, run log2timeline, push to Timesketch, etc.).

```
dftimewolf recipe_name <recipe_args>
dftimewolf list_recipes
```

Common bundled recipes: `local_plaso`, `gcp_turbinia`, `ts_timesketch`, `grr_artifact_hosts`.

**Limitations.** Built-in recipes are Google-flavored (GCS, GRR, Turbinia). Custom recipes are straightforward to write but undocumented for many edge modules.

**Module categories.** dftimewolf modules fall into four categories:

| Category | Examples |
|---|---|
| `collectors` | `LocalFilesystemCollector`, `GRRArtifactCollector`, `GCSCollector`, `S3Collector`, `AzureCollector`, `BigQueryCollector` |
| `preprocessors` | `FilterDirectory`, `LocalImagerCopy`, `Unzip` |
| `processors` | `LocalPlasoProcessor`, `TurbiniaProcessor`, `PsortProcessor`, `HashesCollector` |
| `exporters` | `TimesketchExporter`, `BigQueryExporter`, `LocalFilesystemCopy`, `SCPExporter`, `GCSExporter` |

**Recipe YAML structure.**

```yaml
name: local_plaso
description: Process a local image through plaso to Timesketch
preflights: []
modules:
  - name: LocalFilesystemCollector
    args:
      paths: "@source_path"
  - name: LocalPlasoProcessor
    args:
      timezone: "@timezone"
  - name: TimesketchExporter
    args:
      sketch_id: "@sketch_id"
      incident_id: "@incident_id"
args:
  - ["source_path", "Path to image"]
  - ["timezone", "Timezone of evidence"]
  - ["sketch_id", "Timesketch sketch ID"]
  - ["incident_id", "Incident reference"]
```

The `@`-prefixed values are positional CLI parameters.

---

# 5. WINDOWS ARTIFACT PARSERS — ERIC ZIMMERMAN TOOLS

The Eric Zimmerman (EZ) tools are a suite of .NET single-file binaries that parse specific Windows artifacts with high fidelity. They are the de facto standard for many Windows artifact categories. As of .NET 6+, they run natively on Linux without Mono. Source: https://ericzimmerman.github.io/. License: MIT.

**Stock SIFT status.** Not stock. Per SANS guidance (Aug 2023 onward), install via `dotnet tool install` or download the published binaries and run with `dotnet`. They DO run on Linux SIFT once .NET 6/7/8 runtime is present (`apt install dotnet-runtime-8.0`).

Common conventions across EZ tools:
- All emit CSV by default; many also emit JSON.
- `-d <dir>` recursively processes a directory.
- `-f <file>` processes a single file.
- `--csv <dir>` writes output CSV.
- `--json <dir>` writes JSON.
- Tools use sub-second timestamp precision and emit ISO-8601 UTC.
- "Timeline Explorer" (Windows GUI) is the canonical viewer; on Linux, the CSV is consumed by spreadsheets, jq, or Timesketch.

## 5.1 MFTECmd

**Purpose.** Parse NTFS `$MFT`, `$Boot`, `$J` (USN Journal), `$LogFile`, `$SDS` (security descriptors), and `$I30` index entries.

```
MFTECmd.exe -f \$MFT --csv ./out/
MFTECmd.exe -f \$J  --csv ./out/                  # USN journal
MFTECmd.exe -f \$LogFile --csv ./out/             # transactional log
MFTECmd.exe -f \$Boot --csv ./out/
MFTECmd.exe -f \$SDS  --csv ./out/                # security descriptors
MFTECmd.exe -d C:\evidence\NTFS -csv ./out/       # batch process
MFTECmd.exe -f \$MFT --csvf MFT.csv --de 12345    # dump entry 12345 + parent chain
```

**Output columns (MFT CSV).** EntryNumber, SequenceNumber, ParentEntryNumber, ParentSequenceNumber, InUse, ParentPath, FileName, Extension, FileSize, ReferenceCount, ReparseTarget, IsDirectory, HasAds, IsAds, SI<Create0x10>, SI<LastModified0x10>, SI<LastRecordChange0x10>, SI<LastAccess0x10>, FN<Create0x30>, ..., USecZero, Copied, SiFlags, NameType, LoggedUtilStream, ZoneIdContents.

**Useful flags.**
- `--bodyfile out.body` — produce TSK body-file for `mactime`.
- `--dr` — include DOS-style 8.3 short names.
- `--blf` — produce $LogFile dump.
- `--bdl` — produce $Boot dump.

**Limitations.** Cannot parse ReFS. Cannot parse encrypted $MFT entries. $LogFile parsing is best-effort (binary format Microsoft does not document).

---

## 5.2 EvtxECmd

**Purpose.** Parse Windows Event Logs (`.evtx`) into CSV / JSON / XML, with embedded "maps" (YAML rule files) that extract domain-specific fields (e.g., for 4624, extract LogonType, TargetUserName, IpAddress as first-class columns).

```
EvtxECmd.exe -f Security.evtx --csv ./out/
EvtxECmd.exe -d C:\WinEvt --csv ./out/ --json ./out_json/
EvtxECmd.exe -d C:\WinEvt --maps C:\EvtxECmd\Maps --csv ./out/
EvtxECmd.exe -f Security.evtx --inc 4624,4625,4672 --csv ./out/
EvtxECmd.exe -f Security.evtx --xml ./xml/
```

**Maps directory.** YAML files at https://github.com/EricZimmerman/evtx/tree/master/evtx/Maps. Each map defines: ChannelName, EventId, Provider, mappings of XML XPath → flat CSV column. Community contributes new maps regularly. Examples: `Security_4624.map`, `Sysmon_1.map`, `WindowsDefender_1116.map`.

**Useful flags.**
- `--inc <ids>` / `--exc <ids>` — event ID include/exclude.
- `--sd <date>` / `--ed <date>` — start/end date filters.
- `--fj` — fast JSON (one event per line).
- `--vss` — parse logs from Volume Shadow Copies too (Windows host only).

**Limitations.** Cannot parse Application or System logs that reference custom event providers whose manifests are missing (event "data" may render as raw template binding rather than friendly text). Old EVT (Windows XP/2003) format is NOT supported by EvtxECmd — use the legacy `LogParser` or plaso `evt` parser.

**High-value Windows event IDs investigators focus on.** EvtxECmd maps cover most of these with first-class columns:

| EID | Channel | What it tells you |
|---|---|---|
| 4624 | Security | Successful logon. LogonType column distinguishes interactive (2), network (3), batch (4), service (5), unlock (7), networkclear (8), newcred (9), remoteinteractive=RDP (10), cached (11). |
| 4625 | Security | Failed logon. Bursts suggest brute force. |
| 4634 / 4647 | Security | Logoff / user-initiated logoff. |
| 4648 | Security | Logon with explicit credentials (`runas`, scheduled task). Lateral movement indicator. |
| 4672 | Security | Admin-rights-equivalent token assigned. |
| 4688 | Security | Process creation (if audit policy enabled). Better than nothing if Sysmon absent. |
| 4697 | Security | New service installed. |
| 4698-4702 | Security | Scheduled task created/modified/deleted/enabled/disabled. |
| 4720, 4722, 4724, 4726, 4732, 4738 | Security | User account life-cycle: created, enabled, password reset, deleted, added-to-group, modified. |
| 4768, 4769, 4770, 4771, 4776 | Security | Kerberos TGT request, service ticket request, ticket renewal, pre-auth failure, NTLM auth. |
| 1102 | Security | Audit log cleared. |
| 7045 | System | New service installed. |
| 6005, 6006, 6008, 6013 | System | System start, clean shutdown, dirty shutdown, system uptime. |
| 41 | System | Kernel-Power: unexpected shutdown. |
| 1, 3, 7, 8, 10, 11, 12, 13, 17, 22 | Microsoft-Windows-Sysmon/Operational | Sysmon event family: process create, net connection, image load, create-remote-thread, process access, file create, registry create/modify, registry rename, named pipe, DNS. |
| 4104, 4103, 4100 | Microsoft-Windows-PowerShell/Operational | PowerShell script block log, pipeline log, parser log. Look for `EncodedCommand`, `-w hidden`, `IEX`. |
| 800 | Windows PowerShell | Pre-PSv5 pipeline log. |
| 4624 LogonType 10 + RDP | Multiple | RDP login chain — start with TerminalServices-LocalSessionManager EID 21, 24, 25 for full session lifecycle. |
| 1149 | TerminalServices-RemoteConnectionManager | RDP successful logon. |
| 4634, 4647 + LogonType 10 | Security | RDP logoff. |
| 5140 | Security | Network share accessed. |
| 5145 | Security | Detailed share access (file-level). |
| 5156 | Security | Filtering Platform connection allowed. Noisy but useful with care. |
| 8001-8004 | WLAN-AutoConfig | Wi-Fi association events (SSID, AP MAC). |
| 1116, 1117, 1118, 1119, 1006-1010 | Microsoft-Windows-Windows Defender/Operational | Threat detected / remediated / failed remediation. |

EvtxECmd maps for each of these surface the relevant fields as columns rather than burying them in raw XML.

---

## 5.3 AmcacheParser

**Purpose.** Parse `Amcache.hve` — Windows artifact that records executed PE files with SHA1 hashes, install paths, and metadata. Excellent for "what binaries existed and ran on this host."

```
AmcacheParser.exe -f Amcache.hve --csv ./out/
AmcacheParser.exe -f Amcache.hve --csv ./out/ -i      # include "InventoryApplicationFile"
```

**Output.** CSV with columns: Application, FullPath, FileExtension, Sha1, SizeInBytes, ProductName, ProductVersion, CompanyName, LinkDate, BinFileVersion, FileVersion, IsPeFile, IsOsComponent.

---

## 5.4 AppCompatCacheParser

**Purpose.** Parse the Application Compatibility Cache (ShimCache) from SYSTEM hive. Tracks executable paths and metadata across last reboot.

```
AppCompatCacheParser.exe -f SYSTEM --csv ./out/
AppCompatCacheParser.exe -f SYSTEM --csv ./out/ -c 0   # control set 0 (most recent)
```

**Gotcha.** ShimCache execution flag interpretation varies by Windows version. On Windows 8+ the "execution flag" was removed; presence in ShimCache means "Windows knew about this binary," not necessarily "this binary was executed."

---

## 5.5 PECmd (Prefetch)

**Purpose.** Parse Windows Prefetch files (`.pf`). Each .pf records last 8 execution times, run count, files referenced during startup, and volumes touched.

```
PECmd.exe -f C:\Windows\Prefetch\NOTEPAD.EXE-D8414F97.pf --csv ./out/
PECmd.exe -d C:\Windows\Prefetch --csv ./out/
PECmd.exe -d C:\Windows\Prefetch --csv ./out/ -q       # quiet
```

**Output columns.** SourceFilename, SourceCreated, SourceModified, SourceAccessed, ExecutableName, Hash, Size, Version, RunCount, LastRun, PreviousRun0..6, Volume0Name, Volume0Serial, Volume0Created, FileCount, FileNames (semicolon-delimited).

**Limitations.** Prefetch is disabled on Windows Server by default. On SSD-equipped systems some Win10/11 builds reduce Prefetch creation. Up to 1024 prefetch entries kept (Windows 8+); older Windows kept 128.

---

## 5.6 RECmd (Registry, with batch capability)

**Purpose.** Parse Windows registry hives. Two modes: interactive single-key, and BATCH mode (RECmd "batch files" are YAML rule files that extract many keys at once).

```
RECmd.exe -d C:\Hives --bn BatchExamples\RECmd_Batch_MC.reb --csv ./out/
RECmd.exe -f NTUSER.DAT --kn 'Software\Microsoft\Windows\CurrentVersion\Run'
RECmd.exe -f NTUSER.DAT --sa "evilcorp"            # search all values for string
RECmd.exe -f NTUSER.DAT --sk "Run"                 # search key names
```

**Batch files.** Hundreds of community-maintained batch rules at https://github.com/EricZimmerman/RECmd/tree/master/BatchExamples cover artifacts across hives:

```yaml
Keys:
  - Description: 'Programs run at user logon'
    HiveType: NTUSER
    Category: Persistence
    KeyPath: Software\Microsoft\Windows\CurrentVersion\Run
    Recursive: false
    Comment: 'Run key for current user'
```

Output is a unified CSV with Description, Category, HivePath, KeyPath, ValueName, ValueData, etc., suitable for Timeline Explorer or jq.

**Limitations.** Does not decrypt DPAPI-protected blobs (that requires SECRETS / MASTERKEY decryption, separate tools). Does not interpret all binary values — batch files have to know the format.

**Selected RECmd batch files** (community-maintained at https://github.com/EricZimmerman/RECmd/tree/master/BatchExamples):

- `RECmd_Batch_MC.reb` — the "kitchen sink" community-maintained batch (~500 keys across all hives).
- `RECmd_Batch_SansEzTools.reb` — SANS-curated subset.
- `RECmd_Batch_Lateral_Movement.reb` — keys relevant to lateral movement (RDP, WinRM, PsExec, SMB).
- `RECmd_Batch_Persistence.reb` — autostart / persistence locations.
- `RECmd_Batch_RecentlyActivity.reb` — recent-document and last-touched-item keys.

Each rule in a batch file produces output columns: `HivePath, Description, Category, KeyPath, ValueName, ValueType, ValueData, ValueData2, ValueData3, Comment, Recursive, DeleteValue, KeyLastWriteTime, ValueResolved`. The `ValueResolved` column is the most useful for at-a-glance review — it shows the decoded data (e.g., resolved SID → username).

---

## 5.7 RBCmd (Recycle Bin)

**Purpose.** Parse `$I` (Vista+) and `INFO2` (XP) Recycle Bin index files.

```
RBCmd.exe -f '\$Recycle.Bin\S-1-5-21-...\$IXXXXX'
RBCmd.exe -d '\$Recycle.Bin' --csv ./out/
```

Output: original full path, deleted timestamp, file size.

---

## 5.8 SBECmd (ShellBags Explorer CLI)

**Purpose.** Parse ShellBags (NTUSER.DAT + UsrClass.dat). Records every folder a user navigated through — including network shares, removable drives, since-deleted folders.

```
SBECmd.exe -d C:\Hives --csv ./out/
SBECmd.exe -d C:\Hives --csv ./out/ --dt          # include only first-interaction details
```

**Output.** Hierarchical CSV of bag entries: BagPath, Slot, NodeSlot, MRUPosition, AbsolutePath, ShellType, CreatedOn, ModifiedOn, AccessedOn, FirstInteracted, LastInteracted.

**Why investigators love ShellBags.** Records persistent "I went here" evidence that survives even after the folder is deleted and even after Explorer is closed.

---

## 5.9 LECmd (LNK)

**Purpose.** Parse `.lnk` shortcut files. Each contains target path, target MAC times, target size, drive serial, NetBIOS name, MAC of host that created the shortcut.

```
LECmd.exe -f file.lnk --csv ./out/
LECmd.exe -d C:\Recent --csv ./out/ -q
```

---

## 5.10 JLECmd (Jump Lists)

**Purpose.** Parse Windows Jump Lists — `AutomaticDestinations-ms` and `CustomDestinations-ms` files. These are app-specific "recent items" stores keyed by application ID.

```
JLECmd.exe -d C:\Users\X\AppData\Roaming\Microsoft\Windows\Recent\AutomaticDestinations --csv ./out/
JLECmd.exe -f mostsignificantsuffix.automaticDestinations-ms --csv ./out/
```

**Output.** AppId, AppIdDescription (mapped to known applications), EntryNumber, Hostname, MACAddress, Path, Created, Modified, Accessed, FileSize.

---

## 5.11 SrumECmd (SRUM)

**Purpose.** Parse the System Resource Usage Monitor database (`SRUDB.dat`). Per-process network bytes sent/received, energy use, foreground time, by-application-and-by-user windows. Goldmine for data exfiltration cases.

```
SrumECmd.exe -f C:\Windows\System32\sru\SRUDB.dat -r SOFTWARE --csv ./out/
```

Requires the SOFTWARE hive (provides interface mapping).

**Output tables.** AppResourceUseInfo, NetworkUsages, NetworkConnections, EnergyUsage, PushNotifications.

**Gotcha.** SRUDB.dat updates roughly hourly while the system runs; recent activity may not be flushed.

---

## 5.12 SQLECmd (SQLite, with batch maps)

**Purpose.** Generic SQLite parser driven by YAML "maps" that select queries and column rules. Targets browser histories, Skype, iMessage, application databases.

```
SQLECmd.exe -d ./databases --csv ./out/                # batch
SQLECmd.exe -f history.sqlite --csv ./out/
SQLECmd.exe -d ./databases --maps ./Maps --csv ./out/
```

Map files at https://github.com/EricZimmerman/SQLECmd/tree/master/SQLMap/Maps cover Chrome History, Edge History, Firefox places, Skype main.db, Telegram, Signal, Slack, Notion, Outlook.

---

## 5.13 bstrings

**Purpose.** Faster `strings`-equivalent with regex filtering, base64 detection, prebuilt regex bundles (email, URL, IPv4, IPv6, MAC, GUID, credit card).

```
bstrings.exe -f unallocated.bin --lr email --csv emails.csv
bstrings.exe -f memory.raw --lr ip --csv ips.csv
bstrings.exe -f file.bin --ls "MZ"                  # plain literal
bstrings.exe -f file.bin --b64
```

`--lr` selects a built-in regex; `--ls` is a literal string. `--ar` is a custom regex. Custom regex bundles can be loaded from a YAML file via `--rb`.

---

## 5.14 WxTCmd (Windows Timeline / ActivitiesCache)

**Purpose.** Parse the Windows Timeline `ActivitiesCache.db` (a SQLite database). Tracks every application activity, document touched, with start/end timestamps, durations, foreground time.

```
WxTCmd.exe -f ActivitiesCache.db --csv ./out/
```

Output tables: Activity (general events), ActivityOperationProvider (app names), ActivityPackageId, AppLaunchActivities, FileOpenCloseActivities.

**Limitations.** Windows Timeline was de-emphasized in Windows 11 (sync disabled by default), but local ActivitiesCache.db is still populated for many users.

---

## 5.15 Timeline Explorer (Windows GUI)

Cross-listed for completeness. Windows-only `.NET` GUI (https://ericzimmerman.github.io/#!index.md). Loads CSV/Excel, provides column filtering, color tagging, time-window selection. On Linux SIFT it does not run natively (no GUI Mono support reliable); equivalent workflow uses jq + spreadsheet + Timesketch.

---

# 6. REGISTRY ANALYSIS

## 6.1 RegRipper3.0 (rip.pl)

**Author / maintainer.** Harlan Carvey. Source: https://github.com/keydet89/RegRipper3.0. License: GPL.

**Purpose.** Plugin-driven Perl tool that runs hundreds of focused parsers against a registry hive, each plugin extracting one artifact category (USB devices, run keys, network history, etc.) with analyst-friendly commentary.

**Stock SIFT status.** Installed.

**Invocation.**

```
rip.pl -r NTUSER.DAT -f ntuser                  # run all NTUSER plugins
rip.pl -r SOFTWARE   -f software                # run all SOFTWARE plugins
rip.pl -r SYSTEM     -f system
rip.pl -r SAM        -f sam
rip.pl -r SECURITY   -f security
rip.pl -r NTUSER.DAT -p userassist              # run a single plugin
rip.pl -l                                       # list all plugins
rip.pl -l -c                                    # list with category
rip.pl -uP                                      # update plugin profiles
```

**Plugin catalog (selected — there are 350+).**

| Plugin | Hive | Purpose |
|---|---|---|
| `userassist` | NTUSER | ROT13-encoded program execution counts and last-run |
| `runmru` | NTUSER | Run dialog history |
| `recentdocs` | NTUSER | Recently opened documents per file extension |
| `typedurls` | NTUSER | URLs typed into IE/Edge |
| `shellbags` | NTUSER, UsrClass | Folder navigation (RegRipper3 implementation; SBECmd is generally preferred) |
| `mountdev2` | SYSTEM | Mounted devices and volumes |
| `usbstor` | SYSTEM | USB device history |
| `usb` | SYSTEM | USB enumeration |
| `services` | SYSTEM | Service install/run config |
| `compname` | SYSTEM | Computer name |
| `nic` | SYSTEM | Network interfaces |
| `networklist` | SOFTWARE | Wi-Fi SSIDs joined with first/last connect timestamps |
| `winver` | SOFTWARE | Windows version |
| `profilelist` | SOFTWARE | User SIDs |
| `appcompatcache` | SYSTEM | ShimCache (AppCompatCacheParser usually preferred) |
| `samparse` | SAM | Local user accounts |
| `runkeys` | NTUSER, SOFTWARE | Autoruns |

**Output.** Plain text reports per plugin, easy to grep. Recent versions add `-csv` for selected plugins.

**Limitations.**
- Perl-based; output formatting varies by plugin author.
- Some plugins flag "TODO" or "incomplete" — read the plugin source.
- Does not decrypt DPAPI-protected values.
- Plugin coverage for Windows 11 / Server 2022 lags Eric Zimmerman tools in places.

**Gotcha.** Two RegRippers exist: `regripper` (2.x by Carvey, original) and `RegRipper3.0` (active). Plugin compatibility differs.

**Comprehensive plugin reference (selected, by hive).**

*SYSTEM hive plugins:*

- `compname` — computer name from CurrentControlSet\Control\ComputerName.
- `timezone` — TimeZoneInformation; critical for timeline normalization.
- `services` — services list (key per service).
- `services_*` — service-related variants (deleted services, services with binPath anomalies).
- `usbstor` — USB device enumeration from Enum\USBSTOR; serial number, friendly name, first install, last connect, last removal.
- `usbstor2` — extended USBSTOR with mount-point correlation.
- `usb` — generic USB enum.
- `mountdev` — mounted devices, drive-letter to volume mapping.
- `mp2`, `mountdev2` — mountpoints, MountPoints2 cross-reference.
- `bthport` — Bluetooth devices ever paired.
- `network` — interfaces.
- `nic` — NIC list.
- `lsa` — LSA configuration.
- `audit` — audit policy.
- `bam` / `dam` — Background Activity Moderator / Desktop Activity Moderator (last execution times per user per binary, Windows 10+).
- `routes` — IP routes.
- `kerberos` — Kerberos policy.
- `shutdown` — last shutdown time.

*SOFTWARE hive plugins:*

- `winver` — Windows version, install date, registered owner.
- `profilelist` — user SIDs to profile paths.
- `networklist` — Wi-Fi SSID / wired networks ever connected, first/last connect.
- `installed` — installed applications.
- `uninstall` — Add/Remove Programs.
- `appcompatcache` — ShimCache from SOFTWARE (legacy location).
- `appcompatflags` — AppCompat flags by binary.
- `runonceex` — autostart RunOnceEx entries.
- `autorunsdisabled` — autoruns disabled by user/policy.
- `tracing` — tracing config.
- `dvr` — DVR/Game DVR.
- `defender` — Windows Defender config + Exclusions.

*NTUSER.DAT plugins:*

- `userassist` — UserAssist with ROT13 decoding, execution counts, last run.
- `runmru` — Run dialog history.
- `recentdocs` — RecentDocs per file extension.
- `typedurls` — IE/Edge typed URLs.
- `typedpaths` — Explorer typed paths.
- `mountpoints2` — user-specific mount points.
- `network` — user-specific network info.
- `winrar`, `winzip` — archive tool history.
- `comdlg32` — Common Dialog "Last Visited", "Open Saved MRU".
- `bagmru`, `shellbags` — folder navigation history (use SBECmd preferentially).
- `tsclient` — RDP Terminal Server Client connections + saved credentials path.
- `wordwheelquery` — Start menu / search bar searches.
- `cmd_aliases` — cmd.exe doskey aliases.
- `powershell` — PowerShell-related keys (ExecutionPolicy).
- `office_recent_docs` — Office Last Used / Recent Files per Office version.

*UsrClass.dat plugins:*

- `shellbags_usrclass` — modern ShellBags.
- `office_msstreams` — Office MS streams.

*SAM hive plugins:*

- `samparse` — local user accounts: SID, full name, last login, last password change, login count, lockout, password hint, account flags.
- `samgroup` — local groups + members.

*SECURITY hive plugins:*

- `polacdms` — domain SID + local domain trust SIDs.
- `secrets` — LSA secrets reference (decryption requires SYSTEM hive too).

*Amcache.hve plugins (in addition to AmcacheParser):*

- `amcache_tln` — Amcache in TLN timeline format.

**Transaction log handling.** Registry hives have associated .LOG / .LOG1 / .LOG2 transaction logs that may contain dirty / uncommitted changes. A hive copied while the system was running may be inconsistent without log replay. RegRipper3.0 and RECmd both handle dirty hives with log replay; older RegRipper 2.x does not — leading to "this Run key value is gone" mysteries that resolve when the LOG is replayed.

**Time-of-key interpretation.** Every registry key has a "Last Write Time" timestamp. RegRipper plugins surface this; RECmd does too. Note: only the key, not individual values, has a timestamp. A key with LastWriteTime of 2025-06-07T22:18:00 only means *some* value changed in it at that time — not which one.

**MRUListEx interpretation.** Many MRU lists store ordering in a `MRUListEx` binary value of little-endian uint32 entries indexing the sibling values. The first uint32 is the most recently used. Tools that don't decode MRUListEx will show MRU lists in random order.

---

## 6.2 Registry Explorer / RECmd

Cross-referenced from §5.6. Registry Explorer is the Windows GUI sibling of RECmd. On Linux SIFT, RECmd is the CLI you use.

---

## 6.3 python-registry

**Author.** Willi Ballenthin. Source: https://github.com/williballenthin/python-registry. License: Apache 2.0.

Python library for programmatic registry hive access. Not a CLI artifact tool but the substrate behind several plaso parsers and custom scripts.

```python
from Registry import Registry
reg = Registry.Registry("NTUSER.DAT")
key = reg.open("Software\\Microsoft\\Windows\\CurrentVersion\\Run")
for v in key.values():
    print(v.name(), v.value())
```

Handles both standard hives and "transaction log" recovery for dirty hives (LOG/LOG1/LOG2 replay) since v1.3.

---

# 7. WINDOWS EVENT LOG ANALYSIS

## 7.1 Hayabusa

**Author / maintainer.** Yamato Security. Source: https://github.com/Yamato-Security/hayabusa. License: AGPL-3.0.

**Purpose.** Rust-based Sigma-rule engine for Windows EVTX. Hayabusa converts Sigma rules to internal representation and applies them at high throughput across event log corpora, producing a tagged, time-sorted CSV/JSON of detections.

**Stock SIFT status.** Not stock. Community-installed (Hayabusa is widely added by SANS instructors to teaching SIFT builds, and is part of the community DFIR Tools collection). Single static Rust binary; trivial install.

**Invocation.**

```
hayabusa csv-timeline -d /evtx -o detections.csv             # primary mode
hayabusa csv-timeline -d /evtx -o detections.csv --no-summary
hayabusa csv-timeline -d /evtx -o detections.csv --min-level high --no-frequency
hayabusa json-timeline -d /evtx -o detections.json
hayabusa json-timeline -f Security.evtx -o sec.json
hayabusa update-rules                                         # pull latest rule set
hayabusa list-profiles
hayabusa csv-timeline -d /evtx -o det.csv -p super-verbose   # output profile
hayabusa pivot-keywords-list -d /evtx
hayabusa logon-summary -d /evtx -o logon.csv
hayabusa metrics -d /evtx
hayabusa eid-metrics -d /evtx
hayabusa search -d /evtx -k 'powershell -enc'
```

**Output columns (default profile).** Timestamp, RuleTitle, Level (informational, low, medium, high, critical), Computer, Channel, EventID, RecordID, Details, MitreTactics, MitreTags, OtherTags, RuleFile, EvtxFile.

**Rule set.** Hayabusa ships with both the upstream Sigma rules repository (https://github.com/SigmaHQ/sigma) AND its own bundled rules in `hayabusa-rules` (https://github.com/Yamato-Security/hayabusa-rules) optimized for Hayabusa's matching engine. As of 2024+, 3,500+ Sigma rules + 100+ Hayabusa-specific rules.

**Output profiles.** Hayabusa profiles select which columns to render: `minimal`, `standard`, `verbose`, `super-verbose`, `all-field-info`, `timesketch-minimal`, `timesketch-verbose`. Custom profiles live in `config/profiles.yaml`.

**Performance.**
- Hayabusa is genuinely fast. A 10 GB EVTX corpus across 50 hosts: typically <5 min on a modern laptop.
- Rule load: 1–3 seconds for the full rule set.
- Memory: well under 2 GB even on large corpora because processing is streaming.

**Useful flags.**
- `--min-level <level>` — drop detections below this severity.
- `--enable-deprecated-rules` — include rules upstream Sigma has deprecated.
- `--enable-noisy-rules` — include rules tagged "noisy."
- `--timeline-start <date>` / `--timeline-end <date>` — date window.
- `--utc` / `--RFC-3339` / `--European-time` — timestamp format.
- `--quiet` — suppress banners.
- `--no-color` — for piping.
- `--profile <name>` — column profile.
- `--include-tag <list>` / `--exclude-tag <list>` — MITRE/category filters.

**Limitations.**
- Windows-only EVTX. Does not parse syslog, Linux journald, or macOS unified logging.
- Rule coverage reflects Sigma upstream — rules for very recent threats may lag.
- Some Sigma "correlation" features (multi-event sequences) are partially implemented; advanced correlations may not fire.
- Does not parse archived (.zip) EVTX automatically.
- Output is detection-centric — there is no "show all 4624 events" mode (use EvtxECmd for that, or `hayabusa csv-timeline` then filter).

**Gotchas.**
- The `--min-level` default behavior changes across versions; pin it explicitly.
- Hayabusa expects EVTX files; it cannot read XML or JSON-dumped events.
- The "Channel" column in output may differ from what humans expect on non-English Windows (Windows localizes channel names in some metadata).
- Rule update via `update-rules` requires internet.

**What it CANNOT do.**
- Cannot create new EVTX (read-only).
- Cannot write a Sigma rule.
- Cannot extract underlying event XML payload (use EvtxECmd or `wevtutil`).
- Cannot correlate events with disk artifacts, memory, or network — Sigma is intra-log.

**Example abbreviated output.**

```
2025-06-07 22:18:01.123 +00:00  Suspicious PowerShell EncodedCommand  high  WS01  Microsoft-Windows-PowerShell/Operational  4104  ...  T1059.001  ...
```

**Hayabusa command catalog (full).**

| Command | Purpose |
|---|---|
| `csv-timeline` | Primary detection mode. Apply all (or filtered) rules; emit timeline CSV of detections. |
| `json-timeline` | Same but JSON output. |
| `update-rules` | Pull latest hayabusa-rules from GitHub. |
| `level-tuning` | Adjust rule levels per local policy. |
| `set-default-profile` | Set default output profile. |
| `list-profiles` | Show available output profiles. |
| `list-contributors` | List rule contributors. |
| `pivot-keywords-list` | Extract pivot keywords (rare values, anomalous strings) for follow-up search. |
| `logon-summary` | Cross-event logon summary: users, source IPs, logon types, success/failure counts. |
| `eid-metrics` | Per-channel, per-EventID counts. Quick characterization of corpus shape. |
| `metrics` | Higher-level corpus statistics. |
| `search` | Full-text search across EVTX without rule application. Supports keyword and field-based filter. |
| `computer-metrics` | Per-host stats (events seen, time range). |
| `log-metrics` | Per-channel log-file stats. |
| `extract-base64` | Surface base64-encoded payloads (decoded as best-effort). |
| `expand-cmd` | Expand environment variables / aliases in command-line fields. |

**Sigma rule levels.** Sigma defines 5 levels: `informational`, `low`, `medium`, `high`, `critical`. Hayabusa's `--min-level` filters by these. A clean corpus baselines mostly at `informational`/`low`; `high`/`critical` hits are the ones investigators chase first.

**Rule categories (Hayabusa-specific tags).** Hayabusa-bundled rules use tags like `Hayabusa`, `Sysmon`, `Security`, `PowerShell`, `Application`, `WindowsDefender`, `MSExchange`. Filter:

```
hayabusa csv-timeline -d /evtx -o det.csv --include-tag PowerShell,Sysmon
hayabusa csv-timeline -d /evtx -o det.csv --exclude-tag Application
```

**MITRE ATT&CK mapping.** Most rules carry MITRE tactic and technique tags. Hayabusa output includes these in dedicated `MitreTactics` and `MitreTags` columns when the profile contains them. Useful for ATT&CK-coverage reports.

**Performance benchmarks** (from Hayabusa benchmarks and SANS testing):
- 100 GB Windows EVTX corpus (~10M events) with full rule set: ~10–15 min on 8-core modern CPU.
- Memory footprint scales with concurrent event buffering, typically 500 MB – 2 GB.
- I/O bound on slower disks; CPU bound on NVMe.

**Sigma rule structure (for context).** Hayabusa and Chainsaw both ingest Sigma rules. The Sigma rule format:

```yaml
title: Suspicious Encoded PowerShell Command
id: 12345678-90ab-cdef-1234-567890abcdef
status: stable
description: Detects PowerShell EncodedCommand usage with suspicious patterns
references:
  - https://attack.mitre.org/techniques/T1059/001/
author: ExampleAuthor
date: 2024-01-01
tags:
  - attack.execution
  - attack.t1059.001
logsource:
  product: windows
  service: powershell
  category: ps_script
detection:
  selection:
    EventID: 4104
    ScriptBlockText|contains:
      - '-EncodedCommand'
      - '-enc '
      - '-e '
  filter:
    ScriptBlockText|contains:
      - 'BenignSignedScript'
  condition: selection and not filter
level: high
```

The `logsource` block (product/service/category) is mapped to Windows event channels via the engine's mapping file. The `detection` block names selection criteria; `condition` combines them.

**Sigma modifier reference.**

| Modifier | Meaning |
|---|---|
| `contains` | Substring match. |
| `startswith` / `endswith` | Anchored substring. |
| `re` | Regex. |
| `cidr` | CIDR range match (IP). |
| `base64`, `base64offset` | Match base64-encoded value of input. |
| `wide` | Match UTF-16LE encoded. |
| `windash` | Match command-line dash variants (`-`, `/`, `−`, `–`, `—`). |
| `cased` | Case-sensitive. |
| `utf16le`, `utf16be`, `utf16` | Wide encodings. |
| `all` | All listed values must match (default is "any"). |

**Hayabusa-native rule format.** In addition to Sigma, Hayabusa supports a slightly extended native YAML with `correlation` blocks for multi-event detection:

```yaml
correlation:
  type: event_count
  rules:
    - rule_id_a
    - rule_id_b
  group-by:
    - Computer
  timespan: 5m
  condition:
    gte: 10
```

---

## 7.2 Chainsaw

**Author / maintainer.** WithSecure Labs. Source: https://github.com/WithSecure-Labs/chainsaw. License: GPL-3.0.

**Purpose.** Alternative Rust-based Sigma engine + native rule format. Often used alongside Hayabusa as a cross-check. Chainsaw shines at: ad-hoc hunting with a search syntax, JSON/CSV output, and "Sigma + native" rule layering.

**Stock SIFT status.** Not stock. Community-installed. Single binary.

**Invocation.**

```
chainsaw hunt /evtx --sigma sigma-rules --mapping mappings/sigma-event-logs-all.yml --csv out.csv
chainsaw hunt /evtx -r rules/ --csv out.csv
chainsaw hunt /evtx --sigma sigma-rules --mapping mappings/sigma-event-logs-all.yml --json out.json
chainsaw search 'cmd.exe' /evtx
chainsaw search -t 'Event.System.EventID: =4624' /evtx
chainsaw dump /evtx -o evtx_xml/         # extract EVTX to XML
chainsaw analyse shimcache appcompat.bin -o shimcache.json
chainsaw analyse srum SRUDB.dat -o srum.json
```

**Mapping files.** Chainsaw needs a mapping YAML to translate Sigma field names to the EVTX event XML structure. The repository ships canonical mappings under `mappings/`.

**Rule sources.**
- Upstream Sigma (https://github.com/SigmaHQ/sigma) — via mapping.
- Chainsaw native rules — YAML in `rules/` dir, similar to but more expressive than Sigma for multi-event chains.

**Outputs.** CSV, JSON, JSONL, plain ASCII table.

**Useful flags.**
- `--full` — emit complete event data per detection.
- `--from <date>` / `--to <date>` — window.
- `--level critical,high` — severity filter.
- `--quiet` — suppress banner.
- `--no-color`.
- `--metadata` — include rule metadata in output.

**Limitations.** Similar to Hayabusa — Windows EVTX only for `hunt`; the `analyse` sub-commands cover ShimCache and SRUM but are not a general artifact framework. Chainsaw is slightly slower than Hayabusa on identical workloads in published benchmarks but the gap is small.

**Why investigators run both.** Different mappings and minor parser differences mean Hayabusa and Chainsaw occasionally fire different rules on the same input. Cross-running is cheap and reduces blind spots.

**Chainsaw subcommands (full).**

| Subcommand | Purpose |
|---|---|
| `hunt` | Apply rules (Sigma + native) to EVTX or other supported input. Primary detection mode. |
| `search` | Ad-hoc search by keyword, regex, or field expression. |
| `dump` | Convert EVTX to XML, JSON, or JSONL. |
| `analyse shimcache` | Parse `appcompat.bin` (ShimCache). |
| `analyse srum` | Parse `SRUDB.dat`. |
| `lint` | Validate Sigma rules / mappings without scanning. |

**Search query language (Chainsaw).** Supports two forms:

```
chainsaw search 'powershell' /evtx                           # substring
chainsaw search -e 'powershell' /evtx                        # regex
chainsaw search -t 'Event.System.EventID: =4624' /evtx       # tau (Sigma-like) expression
chainsaw search -t 'Event.EventData.CommandLine: ~"whoami"' /evtx
```

The `-t` tau expression syntax supports `=`, `~` (contains), `>=`, `<=`, AND/OR/NOT, field-path navigation via dotted notation.

**Native rule format.** Chainsaw's native YAML rules add features Sigma lacks — multi-event correlation by session ID, time-window aggregation, count thresholds:

```yaml
title: Brute force followed by success
group: authentication
description: Multiple 4625 failures from same source IP followed by 4624 success within 60 seconds
authors: [example]
kind: chainsaw
level: high
status: stable
timestamp: Event.System.TimeCreated_attributes.SystemTime
fields:
  - from: 4625
    name: src
    to: Event.EventData.IpAddress
filter:
  Event.System.EventID:
    - 4624
    - 4625
container:
  field: Event.EventData.IpAddress
  group_by: 60s
  count:
    "4625": 5
    "4624": 1
```

---

## 7.3 EvtxECmd JSON/CSV piped to jq

Already covered in §5.2; the pattern worth noting:

```
EvtxECmd.exe -d /evtx --json /tmp/evt
for f in /tmp/evt/*.json; do
  jq 'select(.EventId == 4624 and .LogonType == 10)' "$f"
done
```

`jq` is the canonical post-processor on Linux for EZ JSON output. Hayabusa/Chainsaw answer "what's suspicious?"; jq + EvtxECmd answer "show me every X."

---

## 7.4 evtxtract

**Author.** Willi Ballenthin. Source: https://github.com/williballenthin/EVTXtract. License: Apache 2.0.

**Purpose.** Carve EVTX records from unallocated space, pagefile, hibernation files, or partial files. Useful when EVTX files were deleted, wiped, or only fragments survive.

```
evtxtract unallocated.bin > recovered_records.xml
```

Output is XML of recovered records (which may be incomplete — only the fields that survived).

**Limitations.** Recovery is best-effort. Output XML may need handcrafted handling — most downstream EVTX tools expect a complete `.evtx` container, not raw records. Carved records have no MFT timestamp anchor.

---

## 7.5 EVTX_to_XML, dump-evtx, python-evtx

**python-evtx.** Willi Ballenthin. https://github.com/williballenthin/python-evtx. Library + CLI:

```
evtx_dump.py Security.evtx > security.xml
evtx_eventid.py Security.evtx 4624
evtx_record.py Security.evtx 12345
evtx_filter_records.py Security.evtx ChannelXPath
```

**libevtx (Joachim Metz).** https://github.com/libyal/libevtx. C library with `evtxexport`, `evtxinfo` utilities. Often used in pipelines:

```
evtxinfo Security.evtx
evtxexport -f xml Security.evtx > security.xml
```

---

# 8. PATTERN MATCHING, CAPABILITY DETECTION, FUZZY HASHING

## 8.1 YARA

**Author / maintainer.** Victor Manuel Alvarez (originally Virustotal); now community + Avast/Gen Digital. Source: https://github.com/VirusTotal/yara. Documentation: https://yara.readthedocs.io/. License: BSD-3.

**Purpose.** Pattern-matching engine for malware identification and content classification. YARA rules describe binary or text patterns and meta-conditions; the engine scans files, processes, or memory and reports matches.

**Stock SIFT status.** Installed. The `yara` CLI plus the libyara C library and Python bindings.

**Rule structure.**

```
import "pe"
import "math"
import "hash"

rule example_rule
{
    meta:
        author = "ir@findevil"
        description = "Example"
        date = "2025-06-01"
        hash = "abc123..."

    strings:
        $a = "EvilCorp" wide ascii nocase
        $b = { 4D 5A 90 00 ?? ?? ?? ?? 03 00 00 00 }
        $re = /https?:\/\/[a-z0-9.-]+\.evilcorp\.com\/[a-z]+/ nocase

    condition:
        uint16(0) == 0x5A4D and
        pe.imports("kernel32.dll", "WriteProcessMemory") and
        math.entropy(0, filesize) > 7.0 and
        (any of ($a, $b) and #re > 2)
}
```

**Modules** (built-in extensions enabled at compile time):

- `pe` — PE header fields, imports, exports, signatures, sections, version info.
- `elf` — ELF parsing.
- `macho` — Mach-O.
- `dotnet` — .NET assembly metadata.
- `math` — entropy, mean, monte_carlo_pi.
- `hash` — md5, sha1, sha256 of substrings.
- `cuckoo` (deprecated for new use) — sandbox report features.
- `magic` — libmagic-style file type.
- `dex` — Android DEX.
- `time` — match-time filters.
- `string` — case manipulation, conversion.

**Invocation.**

```
yara rules.yar suspect.exe
yara -r rules.yar /mnt/case                       # recursive
yara -s rules.yar suspect.exe                     # print matching strings
yara -p 8 -r rules.yar /mnt/case                  # 8 threads
yara -d filename=suspect.exe rules.yar suspect.exe  # define external variable
yara -m rules.yar suspect.exe                     # print meta
yara -L rules.yar                                 # list rule names
yara -n rules.yar suspect.exe                     # negate: print non-matches
yara -i rule_name rules.yar suspect.exe           # match only this rule name
yara -t tag rules.yar suspect.exe                 # match only rules with this tag
yara -w rules.yar suspect.exe                     # warnings only
yara --scan-list rules.yar list.txt               # scan files listed in list.txt
yara -C compiled.yarc suspect.exe                 # use pre-compiled ruleset
yarac rules.yar compiled.yarc                     # compile rules
```

**Performance ordering.** YARA evaluates condition lazily — cheap predicates should appear first:

```
condition:
    uint16(0) == 0x5A4D and          // very cheap, short-circuits non-PE
    pe.imports("...") and             // moderate
    math.entropy(0, filesize) > 7     // expensive, evaluate last
```

For string matching: short atoms (4+ bytes) are indexed; very short or `nocase` regex without atoms forces full-file linear scan and is slow. The compiler warns about poor-quality atoms with `-w`.

**Limitations.**
- No multi-file correlation. Each scan is per-file (or per-process / per-memory-range).
- Cannot decompile or unpack — runs on bytes as presented.
- Regex engine is bounded — backtracking-heavy regexes are rejected or slow.
- `nocase` on a large hex pattern can be very expensive.
- The `cuckoo` module is largely abandoned.

**Performance characteristics.**
- 10K-file directory, ~500 rules, average file 200 KB: ~30 s on stock SIFT.
- 1 GB memory image with `windows.yarascan` (Volatility plugin): 10–30 minutes for 500 rules.
- `yara` is multi-threaded for filesystem scanning (`-p`); not for single large files.

**Gotchas.**
- Wide vs ASCII: by default a string is ASCII only. `wide` matches UTF-16LE. Many Windows strings are wide.
- `fullword` qualifier prevents substring matches but disqualifies non-alphabetic boundaries.
- `private` rules don't appear in output but can be referenced from condition of other rules.
- Module imports must precede rules in the file.
- `external variables` (`-d`) must be declared but can be redefined per scan.

**What it CANNOT do.**
- Identify capabilities at a behavioral level (that is `capa`).
- Reason about control flow (that is r2/Ghidra/RetDec).
- Survive simple packing without unpacking step.

**YARA-X.** A Rust rewrite of YARA, https://github.com/VirusTotal/yara-x, is the current direction VirusTotal is taking. Same rule syntax (with minor strictness improvements), faster compile time, better error messages. Stock SIFT still ships YARA 4.x; YARA-X is community-installable. CLI is `yr` instead of `yara`. Most rules port unchanged.

**Common operator reference.**

| Operator | Meaning |
|---|---|
| `$a at <off>` | string at specific offset |
| `$a in (<lo>..<hi>)` | string within byte range |
| `#a` | count of matches of $a |
| `@a[i]` | offset of i-th match of $a |
| `!a[i]` | length of i-th match of $a |
| `for any i in (1..#a): (@a[i] > 0x1000)` | iterate string matches |
| `any of them` | any string matched |
| `all of them` | all strings matched |
| `N of ($a, $b, $c)` | exactly/at-least N of these |
| `$a and not $b` | logical |
| `filesize` | total file size |
| `entrypoint` | PE entrypoint offset (deprecated; use pe module) |
| `uintXX(off)`, `intXX(off)` | read integer at offset, native endianness |
| `uintXXbe(off)` | big-endian variant |

**Optimization checklist for slow rules.**
1. Ensure every `strings` has an atom of ≥4 contiguous, non-wildcard bytes.
2. Put cheap predicates (`filesize`, `uint16(0)==0x5A4D`) first in `condition`.
3. Avoid `nocase` on long strings — duplicate with explicit case variants if needed.
4. Replace overly broad regex with anchored / atom-friendly form.
5. Use `private` rules to encapsulate expensive shared checks.
6. Pre-compile with `yarac` for production scanning.

---

## 8.2 capa

**Author / maintainer.** Mandiant (Google Cloud). Source: https://github.com/mandiant/capa. License: Apache 2.0.

**Purpose.** Identify capabilities of an executable (e.g., "encrypts data with RC4," "communicates over HTTP," "checks for VM environment") by matching expert-curated rules against statically analyzed code.

**Stock SIFT status.** Not stock; pip-installable. Standalone binaries published.

**Invocation.**

```
capa suspect.exe
capa -v suspect.exe                   # verbose: show evidence
capa -vv suspect.exe                  # very verbose: show offsets
capa -j suspect.exe > capa.json       # JSON output
capa -f freeze -o frozen.bin suspect.exe   # freeze analysis for reuse
capa --signatures sigs/ suspect.exe   # library signature dir (FLIRT-like)
capa -r rules/ suspect.exe            # alternate rule path
capa -t cryptography suspect.exe       # filter by tactic/tag
```

**Rule format.** YAML with logical structure of "features" (api, string, mnemonic, characteristic, instruction, basic block, function offset). Rules live at https://github.com/mandiant/capa-rules and are categorized by ATT&CK technique.

**Input formats.** PE32/PE32+, ELF, .NET, shellcode (with `-f sc32` or `sc64`), or a "freeze" file.

**Output format (default).** Hierarchical text grouping capabilities by ATT&CK tactic and MBC (Malware Behavior Catalog) category. JSON output is well-structured for downstream consumption — every capability includes match locations and the rule that fired.

**Limitations.**
- Static analysis only — packed/encrypted code yields little until unpacked.
- 32/64-bit PE, ELF, .NET, and shellcode supported; macOS Mach-O support is recent and lighter.
- vivisect (the backend) can struggle on unusual binaries.
- Rule coverage is best for Windows malware and adversary tooling; commodity scripts (PowerShell, Python) get less.

**Gotchas.**
- The first run downloads/sets up rules and signatures. Use `--rules <dir>` to pin.
- capa uses vivisect by default; alternative backends include IDA, Ghidra, Binary Ninja (with appropriate `-b` flag and licensed tools).

**What it CANNOT do.**
- Cannot give a verdict ("malicious / benign") — capa is descriptive, not classificatory.
- Cannot dynamically execute.
- Cannot read encrypted resources.

**Rule feature reference.**

capa rule features describe what to look for at the function/basic-block/instruction level:

- `api: <api>` — API call (e.g., `kernel32.CreateFileA`, `ws2_32.send`).
- `string: <string>` — strings present in function.
- `regex: /pattern/` — regex over strings.
- `mnemonic: <op>` — assembly mnemonic.
- `number: <n>` — immediate number used (good for magic constants).
- `bytes: <hex>` — byte sequence in function.
- `offset: <off>` — referenced offset.
- `section: <name>` — PE section.
- `import: <import>` — PE import.
- `export: <export>` — PE export.
- `characteristic: <name>` — flow/heuristic property (`indirect call`, `peb access`, `stack string`, `tight loop`, `forwarded export`, etc.).
- `class: <name>` — .NET class.
- `namespace: <name>` — .NET namespace.
- `os: <name>`, `arch: <name>`, `format: <name>` — restrict to OS/arch/format.

**Logical combinators in rule conditions.**

```yaml
features:
  - and:
    - or:
      - api: kernel32.WriteFile
      - api: kernel32.WriteProcessMemory
    - api: kernel32.VirtualAllocEx
    - count(api(kernel32.OpenProcess)): >= 1
```

**capa-explorer.** Companion IDA/Ghidra/Binary Ninja plugin that highlights rule matches in the disassembly. Out of scope for headless SIFT.

---

## 8.3 FLOSS (FLARE Obfuscated String Solver)

**Author / maintainer.** Mandiant FLARE team. Source: https://github.com/mandiant/flare-floss. License: Apache 2.0.

**Purpose.** Recover obfuscated, encoded, or stack-built strings from binaries that ordinary `strings` misses.

**Invocation.**

```
floss suspect.exe
floss --no-static-strings suspect.exe    # only stack/decoded strings
floss --only stack tight suspect.exe
floss -j suspect.exe > floss.json        # JSON output
floss --large-strings suspect.exe        # also recover unusually long strings
floss --minimum-length 8 suspect.exe
```

**Modes.**
- Static ASCII / UTF-16 strings.
- Stack strings (assembled byte-by-byte on the stack at runtime).
- Tight strings (similar but tighter scope).
- Decoded strings (emulated decoder function output).

**Performance.** Emulation is slow — a packed 5 MB binary may take 5–20 minutes. The `--only static` mode is fast (just `strings`-equivalent).

**Limitations.** Anti-emulation techniques can throw FLOSS off. Architecture support: x86 and x64 PE primarily; ELF support is newer and lighter.

---

## 8.4 strings (GNU binutils)

```
strings file.bin                          # ASCII, min len 4
strings -a file.bin                       # scan entire file (not just data sections)
strings -n 8 file.bin                     # min length 8
strings -e l file.bin                     # 16-bit little-endian (UTF-16LE Windows)
strings -e b file.bin                     # 16-bit big-endian
strings -e L file.bin                     # 32-bit little-endian
strings -t d file.bin                     # show byte offset (decimal)
strings -t x file.bin                     # show byte offset (hex)
strings -f *.bin                          # prefix output with filename
```

**Gotchas.** Default scans only "loadable" sections of object files; `-a` scans everything. Default encoding is single-byte; Windows strings are often UTF-16LE — re-run with `-e l` and concatenate.

---

## 8.5 ssdeep

**Author / maintainer.** Jesse Kornblum. Source: https://github.com/ssdeep-project/ssdeep. License: GPL.

**Purpose.** "Context-triggered piecewise hashing" (fuzzy hashing). Computes a hash that allows similarity comparison between files. Two files differing by a small percentage produce hashes with measurable similarity.

```
ssdeep file.bin
ssdeep -b file.bin                       # bare output, no header
ssdeep -r -m sigs.txt /mnt/case         # match against signature list
ssdeep -p file1 file2                   # pretty compare two files
ssdeep -d /dir1 /dir2                   # cross-compare two directories
ssdeep -c                                # CSV output
ssdeep -t 80 -m sigs.txt file.bin       # only matches >= 80%
```

**Limitations.** Small files (under ~4 KB) hash poorly; ssdeep documentation recommends only comparing similar-sized files. Tightly-packed malware variants may have radically different ssdeep hashes despite similar source.

---

## 8.6 TLSH (Trend Locality Sensitive Hash)

**Author / maintainer.** Trend Micro. Source: https://github.com/trendmicro/tlsh. License: Apache 2.0.

Modern alternative to ssdeep, particularly for malware clustering. Distance metric is more robust on small differences.

```
tlsh -f file.bin                          # compute hash
tlsh -c file1 file2                       # compare two
tlsh -r dir/                              # batch
```

Python and Go bindings exist; many threat-intel platforms (MalwareBazaar, VirusTotal) publish TLSH alongside SHA-256.

---

# 9. CARVING

## 9.1 bulk_extractor

**Author / maintainer.** Simson Garfinkel (originally); now NPS / community. Source: https://github.com/simsong/bulk_extractor. License: Public domain / MIT (per file).

**Purpose.** Carve features (emails, URLs, IPs, credit cards, GPS coordinates, EXIF, AES key schedules, JSON, KML, ...) from disk images, memory, network captures, or any binary blob — without parsing the underlying filesystem.

**Stock SIFT status.** Installed.

**Invocation.**

```
bulk_extractor -o ./out image.E01
bulk_extractor -o ./out -e email -e url -e ip image.E01     # only specific scanners
bulk_extractor -o ./out -x email image.E01                  # disable specific scanner
bulk_extractor -o ./out -E lightgrep -F patterns.txt image.E01   # custom pattern scanner
bulk_extractor -o ./out -j 8 image.E01                      # 8 threads
bulk_extractor -o ./out -s 0M image.E01                     # sampling mode
bulk_extractor -o ./out -R image.E01                        # roots only (skip recursive)
```

**Scanners.**

| Scanner | Output file | Notes |
|---|---|---|
| `email` | `email.txt`, `email_histogram.txt` | RFC-822 addresses + occurrence histogram |
| `url` | `url.txt`, `url_histogram.txt`, `url_searches.txt`, `url_facebook-id.txt` | URLs with Google, Bing, Facebook ID extraction |
| `ip` | `ip.txt`, `ip_histogram.txt` | IPv4 + IPv6 |
| `ccn` | `ccn.txt`, `ccn_histogram.txt`, `ccn_track2.txt` | Luhn-validated credit card numbers |
| `exif` | `exif.txt` | EXIF metadata from carved JPEGs |
| `json` | `json.txt` | JSON documents |
| `kml` | `kml.txt` | Geo data |
| `gps` | `gps.txt` | GPS coordinates from various formats |
| `lightgrep` | configurable | Custom regex scanner — see §9.7 |
| `aes` | `aes_keys.txt` | Candidate AES key schedules (entropy + structure) |
| `pii` | `pii.txt` | US PII (SSN-shape, phone, etc.) |
| `accts` | `domain.txt`, `telephone.txt` | Account-like strings |
| `winpe` | `winpe.txt` | PE headers found in raw |
| `winprefetch` | `winprefetch.txt` | Prefetch records |
| `vcard` | `vcard.txt` | vCards |
| `evtx` | `evtx_carved.txt` | EVTX record fragments |
| `hiber` | `hiber.txt` | Hibernation file artifacts |

**Output format.** Tab-separated text. Each feature line: `<offset>\t<feature>\t<context>`. Histograms collapse duplicates with counts.

**Useful flags.**
- `-o <dir>` — output directory (must not exist).
- `-e <scanner>` — enable specific scanner (default is most enabled).
- `-x <scanner>` — disable.
- `-S <name>=<value>` — scanner-specific setting.
- `-j <N>` — thread count.
- `-G <size>` — page size (default 16 MB).
- `-s <size>` — sample size (sampling mode, randomly samples instead of scanning all).
- `-R` — recurse over zip/gzip contents.
- `-r <file>` — alert list (auto-flag known-bad IOCs).
- `-w <file>` — stop list (suppress known-good).

**Performance.**
- A 500 GB disk image, full scanners: 4–12 hours.
- Linear in image size; CPU-bound (regex + decompression).
- Output histograms can themselves be large — millions of unique URLs is common.

**Limitations.**
- Carving by content alone — no filesystem context. The `offset` field is the raw byte offset, useful only if you have the image to seek into.
- False positives on random-looking strings (especially `ccn` on binary-encoded numerics).
- Memory usage with `-R` and many recursion levels can balloon.
- The `aes` scanner finds candidate keys but does not link them to encrypted blobs.

**Gotchas.**
- Output directory must NOT pre-exist (safety feature).
- `bulk_extractor` does NOT carve files (use `foremost` / `scalpel` / `photorec` for that). It extracts features (strings/numbers), not files.

**Full scanner list (current versions).**

| Scanner | Output | Notes |
|---|---|---|
| `accts` | `accts.txt`, `telephone.txt`, `domain.txt` | US-format account-style strings |
| `aes` | `aes_keys.txt` | Candidate AES-128/192/256 key schedules |
| `base16` | `base16.txt` | Base16-encoded blobs (hex) detected by frequency |
| `base64` | `base64.txt` | Base64-encoded blobs |
| `ccn` | `ccn.txt`, `ccn_track2.txt`, `ccn_histogram.txt` | Luhn-validated credit card #s + magstripe track2 |
| `email` | `email.txt`, `email_histogram.txt`, `rfc822.txt`, `domain.txt`, `domain_histogram.txt` | Email + sender domains from RFC822 headers |
| `evtx` | `evtx_carved.txt` | Recovered EVTX records |
| `exif` | `exif.txt` | EXIF blocks (carved JPEG metadata) |
| `find` | `find.txt` | User-provided regex via `-F` |
| `gps` | `gps.txt` | GPS coords (NMEA-style and EXIF) |
| `gzip` | recursive expansion | Gzip stream decompression |
| `hiber` | `hiber.txt` | Hibernation file Xpress blocks |
| `httpheaders` | `httpheaders.txt` | HTTP headers from raw |
| `httplogs` | `httplogs.txt` | Common-log-format HTTP server logs |
| `iso` | recursive | ISO9660 recursion |
| `jpeg` | recursive | JPEG recursion |
| `json` | `json.txt` | JSON documents |
| `kml` | `kml.txt` | KML geo data |
| `msdomain` | `msdomain.txt` | Microsoft domain-style strings |
| `net` | `ip.txt`, `ip_histogram.txt` | IPv4 and IPv6 |
| `outlook` | recursive | Outlook PST recursion |
| `pdf` | recursive + `pdf.txt` | PDF decompression and feature extraction |
| `pii` | `pii.txt` | US-style PII (SSN-shape, etc.) |
| `rar` | recursive | RAR recursion |
| `sqlite` | recursive | SQLite recursion |
| `vcard` | `vcard.txt` | vCards |
| `windirs` | `windirs.txt` | Windows directory entry fragments |
| `winlnk` | `winlnk.txt` | LNK fragments |
| `winpe` | `winpe.txt` | PE headers found anywhere in input |
| `winprefetch` | `winprefetch.txt` | Prefetch records (or fragments) |
| `xor` | XOR brute-force | Single-byte XOR descrambling pass (re-runs scanners on descrambled views) |
| `zip` | recursive + `zip.txt` | ZIP recursion |
| `lightgrep` | per-pattern | Custom regex via lightgrep DFA |

**Alert/stop list format.**

```
[alert]    1.2.3.4
[stop]     example.com
```

Loaded via `-r alerts.txt` or `-w stoplist.txt`. Stops suppress features matching the list (a "known good" list) from output. Alerts add `alerted=Y` marking to output.

---

## 9.2 foremost

**Author.** Originally Kris Kendall + Jesse Kornblum (AFOSI); now community. Source: https://github.com/korczis/foremost. License: GPL.

**Purpose.** Carve files from raw images by header/footer signature.

```
foremost -i image.raw -o ./carved -t jpg,png,pdf,zip
foremost -i image.raw -o ./carved -t all
foremost -c /etc/foremost.conf -i image.raw -o ./carved
```

Configurable via `/etc/foremost.conf` — define new signatures with header bytes, footer bytes, max size.

**Limitations.** Cannot reassemble fragmented files. Quality depends on signature definitions. Default conf supports ~20 file types.

---

## 9.3 scalpel

**Author.** Originally Golden Richard. Sources have diverged; the actively used variant is https://github.com/sleuthkit/scalpel.

`scalpel` is a high-performance fork of foremost focused on speed and configurability. Same general use pattern with `scalpel.conf`.

```
scalpel -c /etc/scalpel/scalpel.conf -o ./out image.raw
```

---

## 9.4 photorec

**Author.** Christophe Grenier (TestDisk project). Source: https://www.cgsecurity.org/. License: GPL.

**Purpose.** File carving with broader signature library than foremost/scalpel, plus filesystem-aware optimizations (NTFS, FAT, ext, HFS+).

```
photorec /d ./out image.raw
photorec /log /d ./out image.raw            # log everything
```

Interactive curses UI by default; `/cmd` for scripted mode.

**Strengths.** Best signature library out of the three carvers. Photorec recovers 480+ file types out of the box.

**Limitations.** Interactive UI complicates scripting (the `/cmd` flag mitigates). Recovery of fragmented files is limited.

---

## 9.5 binwalk

**Author / maintainer.** Originally Craig Heffner; current fork actively maintained at https://github.com/ReFirmLabs/binwalk. License: MIT.

**Purpose.** Identify and extract embedded files/firmware from binary blobs. Primary tool for firmware analysis but also useful for forensic carving of mixed-content blobs.

```
binwalk firmware.bin                       # signature scan
binwalk -e firmware.bin                    # extract identified embedded files
binwalk -M -e firmware.bin                 # matryoshka: recursively extract
binwalk -E firmware.bin                    # entropy analysis
binwalk -A firmware.bin                    # opcode scan
binwalk -B firmware.bin                    # signature + strings
binwalk -Y firmware.bin                    # CPU architecture detection
binwalk --dd='.*' firmware.bin             # dump all signature matches
```

**Output.** Tabular: decimal offset, hex offset, description.

**Limitations.** Firmware-oriented. Forensic carvers (foremost/photorec) recover documents better for typical IR cases.

---

## 9.6 lightgrep

**Author.** Lightbox Technologies / now part of bulk_extractor ecosystem. Source: https://github.com/strozfriedberg/lightgrep. License: Apache 2.0.

**Purpose.** Multi-pattern regex search optimized for forensic-scale scanning. Used as a bulk_extractor scanner or standalone.

```
lightgrep -p patterns.txt image.raw
lightgrep -k 'cookie' image.raw
```

Pattern file is one regex per line. Internally builds a DFA over all patterns simultaneously — much faster than running grep iteratively.

---

# 10. NETWORK FORENSICS

## 10.1 Wireshark (GUI mention)

GTK/Qt GUI for pcap analysis. On Linux SIFT, available but rarely run by an automated investigation. `tshark` is the scriptable equivalent and is what an investigator uses headless.

---

## 10.2 tshark

**Author / maintainer.** Wireshark Foundation / Gerald Combs et al. Source: https://www.wireshark.org/. License: GPLv2.

**Purpose.** CLI of Wireshark. Read pcap/pcapng, filter using the Wireshark display-filter language, decode 3000+ protocols, output text/CSV/JSON/ek.

**Stock SIFT status.** Installed.

**Common patterns.**

```
tshark -r capture.pcap                                          # human-readable
tshark -r capture.pcap -V                                       # verbose dissection
tshark -r capture.pcap -Y 'http.request' -T fields -e ip.src -e http.host -e http.request.uri
tshark -r capture.pcap -q -z conv,tcp                           # TCP conversation summary
tshark -r capture.pcap -q -z io,stat,60                         # 60-second I/O graph
tshark -r capture.pcap -q -z http,tree                          # HTTP request tree
tshark -r capture.pcap -q -z dns,tree                           # DNS request tree
tshark -r capture.pcap -Y 'dns' -T fields -e dns.qry.name | sort -u
tshark -r capture.pcap --export-objects http,./http_objects/    # carve HTTP-transferred files
tshark -r capture.pcap --export-objects smb,./smb_objects/
tshark -r capture.pcap -T ek > capture.ek.json                  # Elastic-bulk format
tshark -r capture.pcap -T json                                  # full JSON
```

**Display filter language.** Distinct from the BPF capture filter:

```
http.request and ip.src == 10.0.0.5
tcp.port == 443 and ssl.handshake.extensions_server_name contains "evil"
dns.qry.name matches "[a-z0-9]{20,}\.com"
tcp.analysis.flags                                              # TCP problem packets
```

**Limitations.** Memory grows with capture size during dissection. Large pcaps (>10 GB) are painful — split with `editcap` first. Some proprietary protocols dissect partially.

**Performance.** A 1 GB pcap with `-q -z conv,tcp`: 1–3 min. Full `-V` dump: 5–20 min. `-T json` doubles or triples runtime.

**Gotchas.**
- Display filter `tcp.port == 443` differs from `tcp.dstport == 443`.
- TLS-only inspection without SSLKEYLOGFILE is limited to SNI / cert / handshake.
- Default DNS reverse-lookup can be slow; pass `-n` to disable.

---

## 10.3 tcpdump

**Author / maintainer.** Tcpdump Group. https://www.tcpdump.org/. License: BSD.

**Purpose.** Live capture and basic pcap read using BPF filters. The capture tool; tshark/Wireshark handle deep dissection.

```
tcpdump -i eth0 -w out.pcap                       # capture
tcpdump -r in.pcap                                # read
tcpdump -r in.pcap -nn -X 'tcp port 80'           # hex+ASCII for HTTP
tcpdump -r in.pcap -A                             # ASCII payload
tcpdump -r in.pcap -c 100                         # first 100 packets
tcpdump -r in.pcap -s 0                           # no snap-length truncation
```

BPF filter examples:

```
host 10.0.0.5
host 10.0.0.5 and port 443
net 10.0.0.0/24
tcp[tcpflags] & (tcp-syn|tcp-fin) != 0
icmp and not src host 10.0.0.1
```

---

## 10.4 Zeek (formerly Bro)

**Author / maintainer.** Corelight / Zeek community. Source: https://github.com/zeek/zeek. License: BSD. Documentation: https://docs.zeek.org/.

**Purpose.** Network security monitoring framework. Reads live traffic or pcaps and writes per-protocol structured logs (rather than packet dumps). Output logs are the canonical input to many network-IR pipelines.

**Stock SIFT status.** Installed in most SIFT builds. Pcap-mode invocation:

```
zeek -r capture.pcap                              # process pcap, write logs to CWD
zeek -r capture.pcap LogAscii::use_json=T          # JSON output
zeek -C -r capture.pcap                            # ignore checksums (offline pcaps)
zeek -r capture.pcap local                         # load the "local" policy
zeek -r capture.pcap policy/protocols/ssl/validate-certs
```

**Log catalog (canonical).** Each .log is TSV (or JSON) with named fields:

| Log | Notes |
|---|---|
| `conn.log` | Every L4 connection: 5-tuple, duration, bytes, state |
| `dns.log` | Every DNS query + answer |
| `http.log` | Every HTTP transaction: host, URI, user-agent, status, response size, MIME |
| `ssl.log` | TLS handshake: SNI, JA3, cert chain pointer |
| `x509.log` | Certificate details |
| `files.log` | Every file transferred over any protocol Zeek understands |
| `ftp.log` | FTP commands |
| `smtp.log` | SMTP sessions |
| `ssh.log` | SSH versions, client/server software, JA3-like hash |
| `smb_files.log`, `smb_mapping.log` | SMB activity |
| `kerberos.log` | Kerberos tickets requested |
| `ntlm.log` | NTLM challenges |
| `dhcp.log` | DHCP leases |
| `dpd.log` | Dynamic protocol detection |
| `weird.log` | Protocol anomalies |
| `notice.log` | Policy-script-generated notices |
| `intel.log` | Intel framework matches |
| `software.log` | Detected software versions |
| `pe.log` | PE files transferred (with detected metadata) |

**Scripts.** Zeek's policy scripts live in `share/zeek/site/` and `share/zeek/policy/`. Common useful ones:

- `policy/protocols/conn/known-hosts.zeek` — track new internal IPs.
- `policy/protocols/conn/known-services.zeek` — track new services per host.
- `policy/protocols/ssl/validate-certs.zeek` — flag invalid TLS certs.
- `policy/frameworks/intel/seen/` — match indicators (domains, IPs, file hashes) against an intel feed.
- `policy/protocols/http/detect-sqli.zeek` — heuristic SQLi detection.
- `policy/misc/scan.zeek` — port scan detection.

**Useful invocations.**

```
zeek -r capture.pcap LogAscii::use_json=T policy/protocols/ssl/validate-certs
zeek -r capture.pcap local Site::local_nets='[10.0.0.0/8, 192.168.0.0/16]'
zeek -i eth0 local                              # live capture
zeekctl deploy                                   # cluster mode
```

**Limitations.**
- Single-threaded per worker; large pcaps need `zeek-cut` post-processing or pcap splitting.
- Some encrypted protocols yield little (TLS without SSLKEYLOGFILE — Zeek records SNI/JA3 but not payload).
- Zeek does not signature-match like Suricata — it observes and logs; detection rules live in scripts.

**Performance.** A 1 GB mixed pcap on stock SIFT: 2–10 minutes. Live capture at gigabit line rate requires PF_RING / AF_XDP / DPDK and CPU pinning.

**zeek-cut.** Companion tool. Zeek TSV logs have a `#fields` header; `zeek-cut` extracts named columns:

```
cat conn.log | zeek-cut id.orig_h id.resp_h id.resp_p service duration orig_bytes resp_bytes
cat dns.log  | zeek-cut -d ts query qtype_name answers   # -d adds Zeek-time formatting
cat http.log | zeek-cut id.orig_h host uri user_agent | sort -u
```

**JA3 / JA3S / JASS3 fingerprints.** Zeek's `ssl.log` records `ja3` (client TLS fingerprint) and `ja3s` (server). These are widely used IOCs because malware TLS stacks tend to produce stable JA3s. Modern Zeek versions also support JA4 (https://github.com/FoxIO-LLC/ja4) via plugin.

**Selected high-value Zeek policy scripts.**

- `policy/protocols/conn/known-hosts.zeek` — first-seen internal hosts.
- `policy/protocols/conn/known-services.zeek` — first-seen services per host.
- `policy/protocols/conn/weirds.zeek` — connection anomalies.
- `policy/protocols/ftp/detect.zeek` — FTP anomalies.
- `policy/protocols/http/detect-sqli.zeek` — heuristic SQLi.
- `policy/protocols/http/detect-webapps.zeek` — web app fingerprinting.
- `policy/protocols/smtp/detect-suspicious-orig.zeek` — SMTP from suspicious sources.
- `policy/protocols/ssh/detect-bruteforcing.zeek` — SSH brute force.
- `policy/protocols/ssl/known-certs.zeek` — first-seen certificates.
- `policy/protocols/ssl/log-hostcerts-only.zeek` — only log host certs.
- `policy/protocols/ssl/validate-certs.zeek` — cert chain validation.
- `policy/protocols/ssl/expiring-certs.zeek` — expiring cert detection.
- `policy/frameworks/intel/seen/*` — intel framework consumers.
- `policy/frameworks/files/extract-all-files.zeek` — extract every transferred file.
- `policy/frameworks/files/hash-all-files.zeek` — md5/sha1/sha256 every transferred file.
- `policy/misc/dump-events.zeek` — dump raw events for debugging.
- `policy/misc/scan.zeek` — port scan / address scan detection.
- `policy/misc/detect-traceroute/main.zeek` — traceroute detection.

**Loaded by default** in the `local` policy (`site/local.zeek`) on most installations: protocol-conn-known-services, protocol-conn-weirds, ssl/log-hostcerts-only, ssl/validate-certs, frameworks/intel/seen, frameworks/files/hash-all-files. Production tuning typically extends `local.zeek`.

**Intel framework.** Zeek's intel framework ingests indicator feeds in a tab-separated format:

```
#fields	indicator	indicator_type	meta.source	meta.desc
1.2.3.4	Intel::ADDR	threatfeed	C2 server
evil.com	Intel::DOMAIN	threatfeed	Phishing
abc123...	Intel::FILE_HASH	misp	Known malware
```

Matches against any observation of an indicator value land in `intel.log` with which protocol context surfaced the indicator.

---

## 10.5 Suricata

**Author / maintainer.** Open Information Security Foundation. Source: https://github.com/OISF/suricata. License: GPLv2.

**Purpose.** Signature-based IDS/IPS + network protocol logger. Reads live traffic or pcaps, applies Snort/Suricata-syntax rules, and emits alerts plus EVE JSON event stream covering protocols, files, anomalies.

**Stock SIFT status.** Installed.

**Invocation.**

```
suricata -r capture.pcap -l ./logs -k none                       # offline, skip checksum
suricata -r capture.pcap -l ./logs -S rules/local.rules
suricata -c /etc/suricata/suricata.yaml -r capture.pcap -l ./logs
suricata-update                                                   # pull Emerging Threats OPEN rules
suricata --build-info                                             # show capabilities
```

**Rule format (Snort-compatible).**

```
alert http any any -> any any (msg:"Suspicious POST"; flow:to_server,established; \
   http.method; content:"POST"; http.uri; content:".php"; sid:1000001; rev:1;)

alert tls any any -> any any (msg:"TLS SNI to evil.com"; tls.sni; content:"evil.com"; \
   nocase; sid:1000002; rev:1;)
```

**EVE JSON.** `eve.json` is the unified event output: alerts, http, dns, tls, files, flow, anomaly, fileinfo, stats. One JSON object per line.

```
cat logs/eve.json | jq 'select(.event_type=="alert") | {ts:.timestamp, sig:.alert.signature, src:.src_ip, dst:.dest_ip}'
cat logs/eve.json | jq 'select(.event_type=="dns" and .dns.type=="query")'
```

**Limitations.**
- Performance ceiling: software-only Suricata on commodity hardware peaks ~5–10 Gbps with good rules.
- Rule quality matters; bad rules cause floods.
- Some protocol parsers (Kerberos, NFS) are partial.

**EVE event_type catalog.**

| event_type | Contents |
|---|---|
| `alert` | Rule fired; signature ID, msg, action, severity, metadata, packet/flow context |
| `anomaly` | Stream / protocol anomaly (decoder events) |
| `http` | HTTP transaction |
| `dns` | DNS query and response (separate events) |
| `tls` | TLS handshake summary |
| `tls_handshake` | (newer) granular TLS step events |
| `files` | File transferred over HTTP/SMB/FTP/SMTP |
| `fileinfo` | Hashes + magic + file path of transferred file |
| `flow` | L4 flow summary at end-of-flow |
| `netflow` | NetFlow-style record |
| `ssh` | SSH handshake summary |
| `smtp` | SMTP transaction |
| `dhcp` | DHCP message |
| `krb5` | Kerberos message |
| `nfs` | NFS RPC |
| `tftp` | TFTP message |
| `smb` | SMB transaction |
| `dcerpc` | DCE/RPC message |
| `ftp` / `ftp_data` | FTP command and data channel |
| `rdp` | RDP handshake summary |
| `snmp` | SNMP message |
| `sip` | SIP message |
| `rfb` | VNC / RFB handshake |
| `ikev2` | IKE phase-1 / phase-2 events |
| `mqtt` | MQTT message |
| `quic` | QUIC handshake |
| `stats` | Periodic engine stats |
| `engine` | Engine lifecycle events |

**Useful rule keywords (beyond classic Snort).**

- `http.method`, `http.uri`, `http.user_agent`, `http.host`, `http.request_body`, `http.response_body`, `http.header`, `http.cookie`, `http.stat_code`, `http.stat_msg`.
- `tls.sni`, `tls.cert_subject`, `tls.cert_issuer`, `tls.cert_serial`, `tls.cert_fingerprint`, `tls.version`, `tls.cipher`, `tls.ja3.hash`, `tls.ja3s.hash`.
- `dns.query`, `dns.opcode`, `dns.answer.name`.
- `ssh.proto`, `ssh.software`, `ssh.hassh`.
- `dcerpc.iface`, `dcerpc.iface_version`, `dcerpc.opnum`.
- `smb.named_pipe`, `smb.share`.
- `flow.bytes_toserver`, `flow.bytes_toclient`, `flow.pkts_toserver`.
- `byte_test`, `byte_jump`, `byte_extract`, `byte_math` — binary-protocol scrutiny.

**Suricata-update.** Mainstream rule-management tool:

```
suricata-update enable-source et/open
suricata-update enable-source ptresearch/attackdetection
suricata-update list-sources
suricata-update update-sources
suricata-update
```

After update, validate with `suricata -T -c /etc/suricata/suricata.yaml`.

---

## 10.6 NetworkMiner

**Author / maintainer.** NETRESEC AB (Erik Hjelmvik). Source: https://www.netresec.com/. License: Free edition (closed source); Professional (paid).

**Purpose.** Passive network forensic analyzer with strong file/credential/image extraction from pcaps. GUI-first; CLI mode exists in the Pro edition.

**Stock SIFT status.** Free edition typically pre-installed (Windows .NET binary, run on Linux via Mono historically, or natively on .NET 6+).

**What it extracts.**
- Files transferred over HTTP/FTP/SMB/SMTP/POP3.
- Credentials (cleartext + many hashed forms) from authentication exchanges.
- Images from HTTP and email attachments.
- Host info (OS via fingerprinting, MAC, NetBIOS, mDNS).
- Session lists.
- DNS queries.

**Limitations.** GUI-centric on free edition. Pro edition adds CLI + Office document extraction + better scripting.

---

## 10.7 RITA (Real Intelligence Threat Analytics)

**Author / maintainer.** Originally Black Hills Information Security / Active Countermeasures. Active maintenance under Active Countermeasures. Source: https://github.com/activecm/rita. License: GPLv3.

**Purpose.** Beacon detection and long-connection analysis on Zeek logs. Identifies command-and-control communication patterns (periodic beacons, long-lived connections, suspicious DNS, blacklisted IPs).

**Stock SIFT status.** Sometimes installed; community-installable. RITA is Go-based; ships with MongoDB backend.

**Workflow.**

```
zeek -r capture.pcap LogAscii::use_json=T
rita import -l ./zeek-logs my_dataset
rita show-beacons my_dataset
rita show-long-connections my_dataset
rita show-strobes my_dataset
rita show-exploded-dns my_dataset
rita show-bl-hostnames my_dataset
rita show-bl-source-ips my_dataset
rita show-bl-dest-ips my_dataset
rita html-report my_dataset                         # HTML output
```

**Output.** CSV (default) or HTML report. Beacon scoring 0–1 (higher = more periodic).

**Limitations.**
- Requires Zeek logs as input. Does not read raw pcaps.
- Beaconing detection needs sufficient observation time — short pcaps yield low confidence.
- MongoDB dependency (RITA v5+ also supports ClickHouse).

**Why it matters.** Modern C2 (Cobalt Strike, Sliver, Brute Ratel) often uses periodic check-ins. RITA is the canonical open-source tool for finding these.

---

## 10.8 argus

**Author / maintainer.** QoSient (Carter Bullard). Source: https://qosient.com/argus/. License: GPLv3.

**Purpose.** Flow-record generator and analyzer — produces NetFlow-style records from packets, with extensive filter/query language. Older tool, still useful for flow aggregation when Zeek is overkill.

```
argus -r capture.pcap -w flows.argus
ra -r flows.argus -nn                       # human-readable
racluster -r flows.argus -nn                # aggregate
ragator -r flows.argus -nn                  # merge flow records
```

---

## 10.9 mergecap, editcap

**Wireshark utilities.**

```
mergecap -w merged.pcap part1.pcap part2.pcap part3.pcap        # concatenate
mergecap -w merged.pcap -a part1.pcap part2.pcap                 # preserve order by append
editcap -A "2025-06-01 00:00:00" -B "2025-06-08 23:59:59" in.pcap out.pcap   # time slice
editcap -i 600 in.pcap out.pcap                                  # split into 10-min files
editcap -c 1000000 in.pcap out.pcap                              # split into 1M-packet files
editcap -F pcap in.pcapng out.pcap                               # convert pcapng to pcap
editcap -d in.pcap out.pcap                                      # remove exact-duplicate packets
editcap -r in.pcap out.pcap 1-100 200-500                        # extract packet ranges
```

---

# 11. MALWARE TRIAGE

## 11.1 ClamAV (clamscan)

**Author / maintainer.** Cisco Talos. Source: https://www.clamav.net/. License: GPLv2.

**Purpose.** Open-source antivirus. In IR triage: fast first-pass scan of mounted images or extracted files.

```
clamscan -r /mnt/case                              # recursive
clamscan -r --infected /mnt/case                   # only show infected
clamscan -r --infected --log=clam.log /mnt/case
clamscan -r --bell -i /mnt/case
clamscan -r --max-filesize=200M --max-scansize=2000M /mnt/case
clamscan -r -d custom.ldb /mnt/case                # custom signature db
freshclam                                          # update signatures
```

**Output.** Plain text per file. Summary at end with engine version, signature count, scan time.

**Limitations.** ClamAV signature coverage of modern targeted malware is limited; treat hits as worth investigating but absence as weak evidence. Performance is moderate compared to commercial AV.

---

## 11.2 PEStudio (Windows note)

Closed-source freeware Windows GUI (https://www.winitor.com/) — surfaces PE indicators (imports, sections, strings, certificate, signature, signed by, indicators of compromise). Not Linux-native. Out of scope for headless SIFT but commonly invoked manually on extracted samples.

---

## 11.3 pdf-parser, pdfid, peepdf

**pdf-parser / pdfid.** Author: Didier Stevens. Source: https://blog.didierstevens.com/programs/pdf-tools/. License: Public domain.

```
pdfid.py suspect.pdf                              # quick statistics
pdf-parser.py -a suspect.pdf                      # statistics + per-object summary
pdf-parser.py -o 5 suspect.pdf                    # show object 5
pdf-parser.py -s JavaScript suspect.pdf           # find objects with /JavaScript
pdf-parser.py -f suspect.pdf                      # try to find compressed/decoded content
pdf-parser.py -O -o 5 suspect.pdf                 # decode object 5 streams
```

**pdfid** counts indicator tokens (`/JS`, `/JavaScript`, `/AA`, `/OpenAction`, `/Launch`, `/EmbeddedFile`, `/JBIG2Decode`, `/RichMedia`, `/XFA`) — fast first-glance triage.

**peepdf.** Author: Jose Miguel Esparza. Source: https://github.com/jesparza/peepdf. Interactive PDF analyzer with deeper structure handling. Less actively maintained.

---

## 11.4 oledump, olevba, oleid (Office macro analysis)

**Author / maintainer.** Philippe Lagadec / decalage2. Source: https://github.com/decalage2/oletools. License: BSD-2.

Suite for analyzing Microsoft Office files. The forensic-critical tools:

```
oleid.py suspect.docx                                # quick indicators
olevba suspect.docm                                  # extract + analyze VBA macros
olevba --decode suspect.docm                         # decode common obfuscations
olevba --reveal suspect.docm                         # show deobfuscated source
oledump.py suspect.doc                               # list OLE streams
oledump.py -s 3 -v suspect.doc                       # decompress + dump stream 3
oledump.py -s 3 -d suspect.doc > stream.bin          # dump raw bytes
olemap.py suspect.doc                                # disk layout map
rtfdump.py suspect.rtf                                # RTF analysis
mraptor suspect.docm                                  # heuristic macro suspicion
```

**olevba detection categories.** Suspicious keywords (Shell, WScript, ADODB, etc.), AutoExec (AutoOpen, Document_Open), IOCs (URLs, IPs, exe names), VBA obfuscation patterns (Chr() construction, base64).

**Limitations.** Encrypted Office documents cannot be opened. Some XLM 4.0 macros (Excel 4 macros) need `XLMMacroDeobfuscator` (separate tool).

**oletools companion tools.**
- `pyxswf.py` — extract embedded SWF from Office docs.
- `msodde.py` — extract DDE links (CVE-2017-11826-style attacks).
- `rtfobj.py` — extract OLE objects from RTF.
- `mraptor` — heuristic classifier: rates documents Suspicious / Macro / Clean.
- `mraptor3` — Python 3 version.

**oledump filter strings.**
- `s` — single stream.
- `v` — vba decompress.
- `d` — dump raw bytes.
- `D` — dump with decompression.
- `S` — strings within stream.
- `r` — raw view.
- `M` — macros only.
- `f` — find a string pattern.
- `p` — plugin (e.g., `plugin_biff.py` for Excel BIFF analysis).

`oledump.py -p plugin_biff.py -s 5 suspect.xls` runs the BIFF plugin against stream 5 — surfaces Excel 4 macro formulas, Sheet1 cell formulas, named ranges.

---

## 11.5 binwalk (cross-listed)

Covered in §9.5 — also useful for malware triage of packed/embedded binaries.

---

## 11.6 RetDec

**Author / maintainer.** Avast Software (originally). Source: https://github.com/avast/retdec. License: MIT.

Open-source decompiler producing C-like output from PE/ELF/Mach-O/COFF binaries. Backend of several malware-analysis frameworks.

```
retdec-decompiler.py suspect.exe
retdec-decompiler.py --select-functions main --select-functions DllMain suspect.exe
retdec-decompiler.py -o output.c suspect.exe
```

**Limitations.** Output is best-effort C; complex obfuscation degrades quality. Slow on large binaries. No interactive UI; pipeline tool only.

---

## 11.7 radare2 / r2

**Author / maintainer.** pancake + community. Source: https://github.com/radareorg/radare2. License: LGPLv3.

**Purpose.** Reverse-engineering framework (disassembly, debugging, hex view, decompilation via r2dec/r2ghidra plugins). Headless-friendly.

```
r2 suspect.exe                            # interactive
r2 -A suspect.exe                         # full analysis on startup
r2 -q -c 'aaa; afl' suspect.exe          # list functions, then quit
r2 -q -c 'iz' suspect.exe                # data strings
r2 -q -c 'izz' suspect.exe               # all strings, including non-data
r2 -q -c 'ii' suspect.exe                # imports
r2 -q -c 'iE' suspect.exe                # exports
r2 -q -c 'iS' suspect.exe                # sections
r2 -q -c 'pdf @ main' suspect.exe        # decompile main (with r2dec plugin)
r2 -q -c 'agf @ main' suspect.exe        # control flow graph (ASCII)
```

`r2pipe` library lets Python/JS drive radare2 programmatically.

**Plugins.** `r2ghidra` (Ghidra decompiler), `r2dec` (lightweight decompiler), `r2frida` (instrumentation).

**Limitations.** Steep learning curve. Idiosyncratic command syntax. The "Rizin" fork (https://rizin.re/) emerged from a community split — similar capabilities, different command stability.

---

## 11.8 Ghidra (note)

NSA's open-source reverse-engineering suite (https://github.com/NationalSecurityAgency/ghidra). Java-based GUI with a strong decompiler. Headless mode (`analyzeHeadless`) supports scripted batch decompilation:

```
analyzeHeadless /tmp/proj proj_name -import suspect.exe -postscript MyScript.java
```

Out of scope for inline IR scripting but standard for deep malware analysis.

---

## 11.9 PE-sieve / Moneta / Hollows Hunter

**Author / maintainer.** Aleksandra Doniec (hasherezade). Source: https://github.com/hasherezade/pe-sieve, https://github.com/hasherezade/hollows_hunter. License: BSD-2.

**Purpose.** Detect anomalies in running processes — injected code, hollowed PE images, replaced module bytes, suspicious memory patches. Windows-native tools.

```
pe-sieve.exe /pid 4242                     # scan one process
pe-sieve.exe /pid 4242 /dmode 2 /imp 3     # dump implants + rebuild imports
hollows_hunter.exe                         # scan all processes
hollows_hunter.exe /shellc 1 /data 1       # detect shellcode + suspicious data
```

**Linux ports / equivalents.** None of these run natively on Linux (they instrument Windows process memory). Equivalent capability on Linux memory images is provided by Volatility 3's `windows.malfind` and `windows.hollowfind`/`windows.injected` family.

**Moneta** (https://github.com/forrest-orr/moneta) is similar — process memory anomaly scanner, Windows-only.

---

# 12. LIVE TRIAGE AND COLLECTION

## 12.1 KAPE (Kroll Artifact Parser and Extractor)

**Author / maintainer.** Eric Zimmerman / Kroll. Source: https://www.kroll.com/en/services/cyber-risk/incident-response-litigation-support/kroll-artifact-parser-extractor-kape. License: Closed source, free for non-commercial / certain commercial use.

**Purpose.** Targeted live collection + parsing on Windows endpoints. Two-phase model: **Targets** (collect files matching artifact definitions) and **Modules** (parse the collected files using bundled tools, including EZ tools).

**Stock SIFT status.** Windows .NET binary. Runs via Mono on Linux historically; with .NET 6+ portability, modern KAPE versions are easier. Often run on the Windows endpoint and the output is shipped back to SIFT for further analysis.

**Invocation.**

```
kape.exe --tsource C: --target !SANS_Triage --tdest C:\KapeOut\tout
kape.exe --tsource C: --target KapeTriage --tdest .\tout \
         --msource .\tout --module !EZParser --mdest .\mout
kape.exe --tlist                                    # list all Target definitions
kape.exe --mlist                                    # list all Module definitions
```

**Target definitions.** YAML at https://github.com/EricZimmerman/KapeFiles. Each target enumerates artifact paths to collect (e.g., `KapeTriage` collects every commonly-needed artifact; `!SANS_Triage` is the SANS-curated subset).

**Module definitions.** YAML that runs external binaries (EZ tools, RegRipper, Hayabusa, etc.) against collected artifacts.

**Limitations.**
- Windows-centric (Targets are Windows paths; Modules wrap Windows tools).
- Closed-source license: free for non-commercial; commercial IR use is permitted under specific Kroll terms (read the EULA).
- Targets/Modules YAML is community-maintained; quality varies.

**Target file structure.**

```yaml
Description: Description of artifact
Author: Author name
Version: 1.0
Id: <guid>
RecreateDirectories: true
Targets:
  -
    Name: All EVTX
    Category: EventLogs
    Path: C:\Windows\System32\winevt\Logs\*.evtx
    Recursive: true
  -
    Name: SRUM
    Category: Telemetry
    Path: C:\Windows\System32\sru\SRUDB.dat
```

**Module file structure.**

```yaml
Description: Run EvtxECmd against collected EVTX
Author: ...
Version: 1.0
Id: <guid>
BinaryUrl: https://f001.backblazeb2.com/file/EricZimmermanTools/net6/EvtxECmd.zip
ExportFormat: csv
Processors:
  -
    Executable: EvtxECmd.exe
    CommandLine: -d %sourceDirectory% --csv %destinationDirectory% --csvf EvtxECmd_Output.csv
    ExportFormat: csv
```

KAPE's "compound targets" use the `!` prefix and reference other targets in a list — `!SANS_Triage`, `!BasicCollection`, `KapeTriage` etc. are widely-used compounds.

---

## 12.2 Velociraptor

**Author / maintainer.** Velocidex Enterprises / Mike Cohen + community. Source: https://github.com/Velocidex/velociraptor. License: Apache 2.0. Documentation: https://docs.velociraptor.app/.

**Purpose.** Endpoint visibility and digital forensics framework. Server collects from deployed clients across an enterprise; analyst queries with VQL (Velociraptor Query Language).

**Architecture.**
- Server — Go binary, single process, embedded datastore (file system or MySQL).
- Client (agent) — Go binary deployed to endpoints (Windows, Linux, macOS, ARM).
- GUI — web UI for hunt creation, artifact review, dashboards.
- API — gRPC for automation.

**VQL.** SQL-like query language operating on plugins (data sources) and functions:

```sql
SELECT Pid, Name, Exe, CommandLine
FROM pslist()
WHERE Name =~ "powershell"

SELECT * FROM glob(globs="C:/Users/*/AppData/Local/Microsoft/Windows/Explorer/*")

LET hits = SELECT * FROM yara(rules=YaraRule, files=glob(globs="/tmp/**"))
SELECT * FROM hits

SELECT * FROM Artifact.Windows.EventLogs.Evtx(EvtxFilter="EventID=4624")
```

**Artifacts.** YAML bundles of VQL queries packaged for reuse. The Velociraptor Artifact Exchange (https://docs.velociraptor.app/exchange/) ships hundreds of pre-built artifacts: `Windows.System.Pslist`, `Windows.EventLogs.Hayabusa`, `Linux.Sys.LastUserLogin`, `Generic.Detection.Yara.Process`, `Windows.Forensics.Lnk`, `Custom.Server.Utils.RunHayabusa`, etc.

**Hunts.** Server-driven multi-client collections. Define artifact + parameters, target a subset of clients, schedule, harvest.

**Common limitations.**
- Server-client model adds operational overhead. Standalone mode (`velociraptor.exe --config standalone.yaml`) allows local-only operation, useful for single-host triage.
- VQL is powerful but performance can surprise — expensive globs over network drives are slow.
- Some Windows artifacts require `winpmem` (bundled in the client for memory acquisition).
- Memory acquisition is supported but for very large memory images consider acquiring out-of-band.
- The bundled YARA can be older than standalone yara CLI.
- Windows EVTX parsing through artifacts is reasonably fast but slower than Hayabusa on the same corpus.

**Useful operational features.**
- "Offline collector" — build a self-contained ZIP for an endpoint to run with no network connection; outputs an evidence file for ingestion.
- "Notebooks" — VQL scratchpads per hunt, persistent.
- "Decorators" — VQL-based enrichment that fires on event flows.

**License.** Apache 2.0, free for any use. Commercial support available from Velocidex/Rapid7.

**VQL deeper reference.** VQL is plugin-based: every data source is a callable plugin that returns a row stream. Common plugins:

| Plugin | Returns |
|---|---|
| `pslist()` | Running processes (cross-platform). |
| `pstree()` | Process tree. |
| `glob()` | Filesystem globbing with extended modifiers (`**`, `[abc]`, `{a,b}`). |
| `stat()` | File metadata. |
| `read_file()` | Read file contents. |
| `parse_evtx()` | Parse a `.evtx` file event-by-event. |
| `parse_pe()` | Extract PE metadata. |
| `parse_csv()` | Read CSV as rows. |
| `parse_json()`, `parse_jsonl()` | JSON ingest. |
| `parse_xml()` | XML ingest. |
| `parse_sqlite()` | Run SQL against a SQLite file. |
| `parse_lnk()` | LNK shortcut parsing. |
| `parse_prefetch()` | Prefetch parser. |
| `parse_amcache()` | Amcache parser. |
| `parse_appcompatcache()` | ShimCache parser. |
| `parse_recyclebin()` | Recycle Bin index. |
| `parse_mft()` | Walk MFT entries. |
| `parse_usn()` | USN journal. |
| `parse_lines()` | Line-oriented file. |
| `yara()` | YARA scan files. |
| `proc_yara()` | YARA scan running processes. |
| `winreg.list()` / `winreg.get_value()` | Live registry access. |
| `winreg.parse_hive()` | Offline hive parsing. |
| `hash()` | md5/sha1/sha256. |
| `netstat()` | Network connections. |
| `users()` | Logged-on users. |
| `wmi()` | Live WMI query. |
| `pe_dump_so()` | Dump in-memory PE images. |
| `connect()` | Raw TCP/HTTP outbound (for upload to S3/HTTP). |

**Common VQL idioms.**

```sql
-- Multi-host hunt: list every persistence Run key value
SELECT Hostname, FullPath, Value
FROM clients(client_id=ClientId)
LET hits = SELECT * FROM glob(
   globs="C:/Users/*/NTUSER.DAT",
   accessor="ntfs")

-- YARA scan with hash join to a feed
LET feed = SELECT * FROM parse_jsonl(filename="/feeds/iocs.jsonl")
SELECT * FROM yara(
   rules=YaraRule,
   files=glob(globs="C:/Windows/Temp/*"))
WHERE Rule IN feed.rule_names

-- Memory acquisition + upload
LET mem_file = winpmem(format="raw")
LET upload = upload(file=mem_file, name="mem.raw")
SELECT * FROM upload
```

**Artifact YAML structure.**

```yaml
name: Windows.Sysmon.ProcessCreation
description: Returns Sysmon EventID 1 records
type: CLIENT
parameters:
  - name: EvtxPath
    default: 'C:/Windows/System32/winevt/Logs/Microsoft-Windows-Sysmon%4Operational.evtx'
sources:
  - query: |
       SELECT System.TimeCreated.SystemTime AS Time,
              EventData.ProcessId AS Pid,
              EventData.Image AS Image,
              EventData.CommandLine AS CommandLine,
              EventData.User AS User,
              EventData.Hashes AS Hashes
       FROM parse_evtx(filename=EvtxPath)
       WHERE System.EventID.Value = 1
```

Artifacts auto-appear in the GUI under their namespace; parameters become form fields.

**Offline collector packaging.**

```
velociraptor.exe --config server.config.yaml \
   collector \
   --artifacts Windows.KapeFiles.Targets \
   --parameters '{"Device":"C:","_BasicCollection":"Y"}' \
   --output collector.exe
```

The resulting `collector.exe` is a self-contained binary an analyst can run on an air-gapped or VPN-isolated endpoint. It writes evidence to a zip the analyst then imports.

**VQL accessor concept.** A given path can be read via different "accessors":

| Accessor | What it does |
|---|---|
| `file` | Standard OS file API. Subject to ACLs and locked files. |
| `ntfs` | Raw NTFS parser. Bypasses ACLs and locks; can read $MFT, $UsnJrnl, $LogFile, locked SYSTEM hive. |
| `auto` | Try OS first, fall back to NTFS on failure. |
| `raw_ntfs` | Like `ntfs` but on raw disk image rather than live volume. |
| `registry` | Live registry navigation. |
| `raw_reg` | Parse an offline hive file. |
| `data` | In-memory byte buffer. |
| `zip` | Treat zip file as filesystem. |
| `gzip` / `bzip2` / `xz` | Compressed file accessors. |
| `vss` | Browse a VSS shadow copy. |
| `ewf` | Read EWF / E01 image. |
| `vmdk` | Read VMDK. |
| `pst` | Read Outlook PST. |
| `mft` | Walk MFT entries. |

The accessor is a parameter to `glob()`, `read_file()`, etc.:

```sql
SELECT FullPath, Size FROM glob(globs="C:/Windows/System32/config/SAM", accessor="ntfs")
```

**Server-driven hunts (lifecycle).**
1. Analyst creates a hunt in GUI: select artifact, set parameters, set client filter (labels, OS, or all).
2. Server pushes flow definitions to matched clients.
3. Clients run flows, upload results.
4. Notebook attached to the hunt aggregates results via VQL.
5. Notebook cells can drive follow-on artifacts (collect from any client showing a match).

**Memory acquisition via Velociraptor.** The bundled `Windows.Memory.Acquisition` artifact uses an embedded WinPMEM driver:

```
SELECT * FROM Artifact.Windows.Memory.Acquisition()
```

Output is uploaded as an AFF4 or raw memory image, viewable in the server's file store, downloadable for Volatility/MemProcFS analysis.

---

## 12.3 UAC (Unix-like Artifact Collector)

**Author / maintainer.** Tclahr. Source: https://github.com/tclahr/uac. License: Apache 2.0.

**Purpose.** Bash shell script for live artifact collection from Unix-like systems (Linux, macOS, FreeBSD, AIX, Solaris). The Unix counterpart to KAPE Targets.

```
sudo ./uac -p ir_triage /mnt/uac_output
sudo ./uac -p full /mnt/uac_output
sudo ./uac --profile ir_triage --case-number CASE-001 /mnt/out
```

**Profiles.** `ir_triage` (fast triage), `full` (everything), `offline` (analyze a mounted image instead of running system).

**Output.** Tarball with structured directory tree containing collected files + UAC's own logs.

**Limitations.** Shell script — slow on huge filesystems. Some collectors require root.

**UAC artifact categories collected (selected).**

| Category | Examples |
|---|---|
| `bodyfile` | TSK-style bodyfile across mounted filesystems |
| `chkrootkit_output` | If chkrootkit installed, runs and captures output |
| `live_response/process` | `ps`, `ps -ef`, `lsof`, `pstree`, `/proc/*/cmdline`, `/proc/*/status`, `/proc/*/maps` |
| `live_response/network` | `netstat`, `ss`, `ip addr`, `route`, `iptables -L`, `arp -an` |
| `live_response/system` | `uname -a`, `uptime`, `dmesg`, `lscpu`, `lsblk` |
| `live_response/storage` | `df`, `mount`, `lsmod`, `mtab` |
| `live_response/users` | `who`, `w`, `last`, `lastb`, `lastlog`, `/etc/passwd`, `/etc/group`, `/etc/shadow` (read by root) |
| `logs` | `/var/log/**` (auth.log, syslog, messages, cron, dpkg, apt, yum, kern.log, audit/audit.log) |
| `system_files` | `/etc/cron*`, `/etc/init.d`, `/etc/systemd`, `/etc/rc*.d`, `/etc/profile.d`, `/etc/sudoers*` |
| `user_files` | Per-user `.bash_history`, `.zsh_history`, `.ssh/authorized_keys`, `.ssh/known_hosts`, `.viminfo`, `.lesshst`, `.python_history`, `.mysql_history` |
| `containers` | Docker/Podman container metadata |
| `applications` | Common application config (nginx, apache, sshd, postfix, mysql) |
| `package_managers` | Installed package lists per pkg manager |
| `samba` | smb.conf, log files |
| `webservers` | Web server logs and configs |

**UAC profile structure.** YAML files under `uac/profiles/`. Each profile lists artifacts to collect. Custom profiles are easy to drop in.

---

## 12.4 AVML (cross-listed)

Covered in §1.7 — Linux memory acquisition.

---

# 13. ANTI-FORENSICS DETECTION

## 13.1 densityscout

**Author / maintainer.** CERT.at / L. Aaron Kaplan. Source: https://www.cert.at/en/downloads/software/software-densityscout. License: GPLv2.

**Purpose.** Compute byte-density score across files. Packed and encrypted files have characteristic high density — densityscout sorts files by density to surface candidates for malware/anti-forensics review.

```
densityscout -pe -r -o densities.csv /mnt/case
```

`-pe` restricts to PE files. Output is one line per file with density value.

**Limitations.** Density is one signal among many — many legitimate files (JPEGs, PDFs with images, video) have high density too.

---

## 13.2 Detect It Easy (DiE)

**Author / maintainer.** horsicq. Source: https://github.com/horsicq/Detect-It-Easy. License: MIT.

**Purpose.** Identify packer, compiler, linker, .NET version, protector for PE/ELF/Mach-O files. Successor to the older PEiD.

```
diec suspect.exe                                # CLI: full info
diec --json suspect.exe                          # JSON output
diec -r /mnt/case                                # recursive
die suspect.exe                                  # GUI (if X available)
```

**Output.** Identified packer/compiler/protector + entropy + file type. Scriptable JSON output is the IR-relevant interface.

**Limitations.** Detection-by-signature: new or unusual packers may register as "unknown."

**Other anti-forensics-adjacent signals worth looking for.** These are not single-tool surfaces; they are conditions investigators check via the tools above:

- **Timestomp.** $STANDARD_INFORMATION vs $FILE_NAME mismatches in MFTECmd output. The `nanos_set_to_zero` heuristic (timestamps with .0000000) suggests timestamps set programmatically.
- **Wiped event logs.** Event ID 1102 in Security log = "audit log was cleared." Event 104 in System log = log was cleared by user.
- **Disabled telemetry.** Registry checks: `HKLM\SYSTEM\CurrentControlSet\Services\eventlog\<channel>\Start`, `HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\EventLog-*\Start`, Sysmon driver entries.
- **USN journal deletion or truncation.** `MFTECmd -f \$J` returns truncated count vs. expected — telltale.
- **Prefetch deletion.** Empty `C:\Windows\Prefetch\` on a workstation that has been in use for weeks.
- **VSS deletion.** `vssadmin delete shadows` left no shadows; check System.evtx event 8224.
- **NTFS alternate data streams.** `MFTECmd` flags `HasAds`; investigate `:Zone.Identifier` (MOTW) for download provenance, but custom names ($DATA streams with arbitrary names) are classic hiding spots.
- **Restored boot timestamps via SetSystemTimeAdjustment.** Look for System.evtx event 1 (Kernel-General time change) and event 4616 (Security log: system time changed).
- **Defender exclusion list.** `HKLM\SOFTWARE\Policies\Microsoft\Windows Defender\Exclusions\*` — a populated exclusion list with paths matching suspicious binaries is high-value evidence of staging.

---

# 14. HASHING AND INTEGRITY

## 14.1 md5sum, sha256sum (GNU coreutils)

```
md5sum file.bin
sha256sum file.bin
find /mnt/case -type f -exec sha256sum {} \; > hashes.txt
sha256sum -c hashes.txt                        # verify against existing hash list
```

Performance: hardware-accelerated on modern CPUs (sha-ni). 1 GB file: ~3 s.

---

## 14.2 hashdeep

**Author.** Jesse Kornblum. Source: https://github.com/jessek/hashdeep. License: Public domain.

**Purpose.** Recursive hashing with multiple algorithms in one pass, matching against known-good/known-bad lists, audit-mode comparison.

```
hashdeep -r -c md5,sha256 /mnt/case > hashes.txt
hashdeep -r -c md5,sha256 -m -k known_good.txt /mnt/case          # known-mode (match)
hashdeep -r -c md5,sha256 -x -k known_bad.txt /mnt/case           # find anything matching list
hashdeep -r -c md5,sha256 -a -k baseline.txt /mnt/case            # audit mode
```

Output: one line per file with file path and each algorithm's hash. The audit mode (`-a`) reports added/removed/modified files vs the baseline — ideal for change-detection between two timepoints of the same volume.

---

## 14.3 ssdeep, tlsh (cross-listed)

Covered in §8.5, §8.6.

---

## 14.4 mactime (cross-listed)

Covered in §3.2. mactime produces timestamps from a TSK body-file, not hashes — but it is integrity-relevant because it allows comparing temporal evidence across hosts.

---

# 15. CANONICAL TOOL CHAINS

The chains below are commonly executed pipelines investigators run. They are not prescriptions for any particular architecture — they describe how tools in this reference compose in practice.

## 15.1 Disk super-timeline chain

```
ewfacquire           -> image.E01
ewfverify image.E01                                     # integrity
imount image.E01                                        # mount partitions + VSS
log2timeline.py --storage_file case.plaso /mnt          # full plaso parse (hours)
psort.py -o l2tcsv -w timeline.csv case.plaso
                                                         # filter/render
psort.py -o json_line -w timeline.jsonl case.plaso
                                                         # ingest into Timesketch / Elastic
```

Variant — narrower triage (just MFT and event logs):

```
image_export.py --artifact_filters WindowsEventLogs,NTFSMFT -w out/ image.E01
MFTECmd -f out/\$MFT --csv ./parsed/
EvtxECmd -d out/ --csv ./parsed/
hayabusa csv-timeline -d out/ -o ./parsed/detections.csv
```

## 15.2 Memory triage chain

```
# acquisition
DumpIt.exe                                              # on Windows endpoint, ship mem.raw

# basic recon
vol -f mem.raw windows.info
vol -f mem.raw windows.pslist
vol -f mem.raw windows.pstree
vol -f mem.raw windows.cmdline
vol -f mem.raw windows.netscan

# anomalies
vol -f mem.raw windows.malfind -o ./malfind_dumps/
vol -f mem.raw windows.svcscan
vol -f mem.raw windows.modscan
vol -f mem.raw windows.callbacks

# deep / forensic
MemProcFS -device mem.raw -mount /mnt/mem -forensic 1
# then browse /mnt/mem/forensic/timeline, /mnt/mem/forensic/findevil, /mnt/mem/forensic/yara

# yara
vol -f mem.raw windows.yarascan --yara-rules rules.yar
```

## 15.3 Network triage chain

```
# split & shape
editcap -A "2025-06-01" -B "2025-06-08" raw.pcap window.pcap

# Zeek pass
zeek -C -r window.pcap LogAscii::use_json=T policy/protocols/ssl/validate-certs

# Suricata pass
suricata -r window.pcap -l ./surilogs -k none -c /etc/suricata/suricata.yaml

# beacon / long-conn analytics
rita import -l ./zeek-logs case
rita show-beacons case
rita show-long-connections case

# manual / question-driven dissection
tshark -r window.pcap -Y 'dns.qry.name matches "[a-z0-9]{20,}"' -T fields -e dns.qry.name
tshark -r window.pcap --export-objects http,./http_objects/

# extract files / images / credentials
NetworkMiner --read window.pcap
```

## 15.4 EVTX rapid-hunt chain

```
EvtxECmd -d /evtx --json ./evt_json/
hayabusa csv-timeline -d /evtx -o ./hayabusa.csv
chainsaw hunt /evtx --sigma sigma-rules --mapping mappings/sigma-event-logs-all.yml --csv ./chainsaw.csv

# cross-check rule fires
diff <(awk -F, 'NR>1 {print $2}' hayabusa.csv | sort -u) \
     <(awk -F, 'NR>1 {print $4}' chainsaw.csv | sort -u)

# pivot on logon events
jq 'select(.EventId == 4624) | {ts:.TimeCreated, user:.TargetUserName, src:.IpAddress, type:.LogonType}' \
    evt_json/Security.evtx.json
```

## 15.5 PE / malware sample triage chain

```
sha256sum sample.bin
ssdeep sample.bin
tlsh -f sample.bin
diec --json sample.bin                                  # packer ID
strings -a -el sample.bin | head
floss --no-static-strings sample.bin
yara rules.yar sample.bin
capa -j sample.bin > capa.json
clamscan sample.bin
```

## 15.6 Registry triage chain

```
image_export.py --artifact_filters WindowsRegistryFilesAndTransactionLogs -w hives/ image.E01

# heavy lifting via batch
RECmd -d hives/ --bn BatchExamples\RECmd_Batch_MC.reb --csv ./reg/

# RegRipper deep narrative
rip.pl -r hives/SYSTEM -f system  > reg/system.txt
rip.pl -r hives/SOFTWARE -f software > reg/software.txt
rip.pl -r hives/NTUSER.DAT -f ntuser > reg/ntuser.txt

# artifact-specific
AppCompatCacheParser -f hives/SYSTEM --csv ./reg/
AmcacheParser -f hives/Amcache.hve --csv ./reg/
SBECmd -d hives/ --csv ./reg/
SrumECmd -f hives/SRUDB.dat -r hives/SOFTWARE --csv ./reg/
```

---

# 16. WHAT IS MISSING ON STOCK SIFT

SANS SIFT ships a curated baseline; the community extends it. The notable gaps as of SIFT 2024:

- **Eric Zimmerman tools.** Not on stock SIFT. Per SANS guidance (Aug 2023 onward — https://www.sans.org/blog/ez-tools-on-linux/), install via `dotnet tool install` after adding the .NET SDK/runtime. EZ tools are .NET 6+ binaries that run natively on Linux:
  ```
  sudo apt install dotnet-sdk-8.0
  dotnet tool install --global EZTools.MFTECmd
  dotnet tool install --global EZTools.EvtxECmd
  ...
  ```
  Or download the published single-file binaries from https://ericzimmerman.github.io/.

- **Hayabusa.** Not stock. Single static Rust binary; download from https://github.com/Yamato-Security/hayabusa/releases.

- **Chainsaw.** Not stock. Single Rust binary; download from https://github.com/WithSecure-Labs/chainsaw/releases.

- **KAPE.** Closed-source Windows-centric binary. Runs on Linux via Mono historically and via .NET 6+ for recent versions. Available after registering at Kroll.

- **MemProcFS.** Linux build is available but typically community-installed.

- **Velociraptor.** Single Go binary, easy install.

- **RITA.** Available via Active Countermeasures download; requires MongoDB (or ClickHouse in v5).

- **Volatility 2.** Often omitted on newer SIFT in favor of v3. If you need plugins that didn't port (mftparser, shimcache, cmdscan, consoles), install manually.

- **Recent Sigma rules.** Hayabusa/Chainsaw bundle a snapshot; `hayabusa update-rules` and Chainsaw's git submodule update pull fresh rules.

- **YARA modules.** Stock SIFT yara may not have dotnet/dex modules compiled in; rebuild if needed.

- **Suricata rules.** ET Open is configured but not always auto-updating; run `suricata-update` to refresh.

- **bulk_extractor scanners.** All built-in scanners are compiled in; the `lightgrep` scanner depends on lightgrep being linked at build time.

- **dftimewolf custom modules.** Bundled recipes work; custom ones need the dftimewolf source tree.

- **GUI tools (Timeline Explorer, Wireshark, NetworkMiner).** Available in X11 mode; headless SIFT workflows skip them.

---

# 17. LICENSE AND PROVENANCE NOTES

A summary of license categories for the tools in this document. "Commercially usable" means a downstream product can use and distribute the tool under the listed license without per-seat fees, subject to the license's specific requirements.

| Category | License | Commercially usable? | Notes |
|---|---|---|---|
| Apache 2.0 | Apache 2.0 | Yes, with attribution | plaso, dftimewolf, Velociraptor, AVML, evtxtract, python-evtx, capa, lightgrep, AVML, TLSH, MemProcFS, bulk_extractor (mixed), pyaff4 |
| MIT | MIT | Yes, with attribution | EZ Tools (all), AVML, RetDec, Detect It Easy, imagemounter, FLOSS |
| BSD | BSD 2/3-clause | Yes, with attribution | YARA, oletools, tcpdump, libpcap, PE-sieve, Hollows Hunter, Zeek |
| GPLv2 | GPLv2 | Yes, copyleft applies to derivatives | Sleuth Kit (CPL is similar), ClamAV, dc3dd, foremost, scalpel, dd, LiME, ddrescue, densityscout, Wireshark/tshark |
| GPLv3 | GPLv3 | Yes, strong copyleft | xmount, photorec, RITA, argus, Volatility 3 mostly (some files differ — see source) |
| LGPLv3 | LGPLv3 | Yes, with attribution; library linking permits closed callers | libewf, libvshadow, libbde, libfvde, libluksde, libevtx |
| AGPLv3 | AGPLv3 | Yes, but network-use triggers source disclosure | Hayabusa |
| Public domain | PD | Yes | hashdeep, parts of bulk_extractor, ssdeep (with caveats), pdf-parser/pdfid |
| Closed freeware | proprietary | Use per EULA | KAPE, NetworkMiner Free, DumpIt, PEStudio, Detect It Easy (some builds), Magnet RAM Capture |

**Provenance considerations for evidence chain.** The forensic value of a tool's output depends on the tool being reproducible. Open-source tools are preferred for findings that may face cross-examination because the parsing logic is auditable. Closed-source tools (KAPE, DumpIt, PEStudio) are widely accepted in IR but a defense expert may challenge specific outputs. Mixed pipelines — open-source ingest with closed parsers — are the norm.

**Hash chain documentation.** Standard practice: record SHA-256 of every original artifact at acquisition, every intermediate at each tool stage, and every output. Tools that integrate hash-on-the-fly (dc3dd, ewfacquire with `-d sha256`, hashdeep) reduce this overhead.

**Time normalization.** All evidence is best normalized to UTC. Eric Zimmerman tools emit UTC by default. plaso records both UTC and source TZ. Hayabusa supports UTC/RFC-3339/European-time output. Mixing local-time and UTC in a single timeline is the classic timeline-misinterpretation bug.

**Tool source-of-truth URLs (canonical).**

| Tool | Repo / docs |
|---|---|
| Volatility 3 | https://github.com/volatilityfoundation/volatility3 — https://volatility3.readthedocs.io |
| Volatility 2 | https://github.com/volatilityfoundation/volatility |
| MemProcFS | https://github.com/ufrisk/MemProcFS — https://github.com/ufrisk/MemProcFS/wiki |
| WinPMEM | https://github.com/Velocidex/WinPmem |
| AVML | https://github.com/microsoft/avml |
| LiME | https://github.com/504ensicsLabs/LiME |
| Memory Baseliner | https://github.com/Velocidex/Memory-Baseliner |
| libewf | https://github.com/libyal/libewf |
| libvshadow | https://github.com/libyal/libvshadow |
| libbde | https://github.com/libyal/libbde |
| libfvde | https://github.com/libyal/libfvde |
| libluksde | https://github.com/libyal/libluksde |
| libevtx | https://github.com/libyal/libevtx |
| TSK | https://github.com/sleuthkit/sleuthkit |
| plaso | https://github.com/log2timeline/plaso — https://plaso.readthedocs.io |
| dftimewolf | https://github.com/log2timeline/dftimewolf |
| Forensic Artifacts | https://github.com/ForensicArtifacts/artifacts |
| Eric Zimmerman tools | https://ericzimmerman.github.io |
| RegRipper3.0 | https://github.com/keydet89/RegRipper3.0 |
| python-registry | https://github.com/williballenthin/python-registry |
| python-evtx | https://github.com/williballenthin/python-evtx |
| evtxtract | https://github.com/williballenthin/EVTXtract |
| Hayabusa | https://github.com/Yamato-Security/hayabusa |
| Hayabusa rules | https://github.com/Yamato-Security/hayabusa-rules |
| Sigma | https://github.com/SigmaHQ/sigma |
| Chainsaw | https://github.com/WithSecure-Labs/chainsaw |
| YARA | https://github.com/VirusTotal/yara — https://yara.readthedocs.io |
| YARA-X | https://github.com/VirusTotal/yara-x |
| capa | https://github.com/mandiant/capa |
| capa rules | https://github.com/mandiant/capa-rules |
| FLOSS | https://github.com/mandiant/flare-floss |
| ssdeep | https://github.com/ssdeep-project/ssdeep |
| TLSH | https://github.com/trendmicro/tlsh |
| bulk_extractor | https://github.com/simsong/bulk_extractor |
| foremost | https://github.com/korczis/foremost |
| photorec / TestDisk | https://www.cgsecurity.org |
| binwalk | https://github.com/ReFirmLabs/binwalk |
| lightgrep | https://github.com/strozfriedberg/lightgrep |
| Wireshark / tshark | https://www.wireshark.org |
| tcpdump | https://www.tcpdump.org |
| Zeek | https://github.com/zeek/zeek — https://docs.zeek.org |
| Suricata | https://github.com/OISF/suricata |
| NetworkMiner | https://www.netresec.com |
| RITA | https://github.com/activecm/rita |
| argus | https://qosient.com/argus |
| ClamAV | https://www.clamav.net |
| PEStudio | https://www.winitor.com |
| pdf-tools | https://blog.didierstevens.com/programs/pdf-tools |
| peepdf | https://github.com/jesparza/peepdf |
| oletools | https://github.com/decalage2/oletools |
| RetDec | https://github.com/avast/retdec |
| radare2 | https://github.com/radareorg/radare2 |
| Ghidra | https://github.com/NationalSecurityAgency/ghidra |
| PE-sieve | https://github.com/hasherezade/pe-sieve |
| Hollows Hunter | https://github.com/hasherezade/hollows_hunter |
| Moneta | https://github.com/forrest-orr/moneta |
| KAPE | https://www.kroll.com — https://github.com/EricZimmerman/KapeFiles |
| Velociraptor | https://github.com/Velocidex/velociraptor — https://docs.velociraptor.app |
| UAC | https://github.com/tclahr/uac |
| densityscout | https://www.cert.at/en/downloads/software/software-densityscout |
| Detect It Easy | https://github.com/horsicq/Detect-It-Easy |
| hashdeep | https://github.com/jessek/hashdeep |
| imagemounter | https://github.com/ralphje/imagemounter |
| xmount | https://www.pinguin.lu/xmount |
| ddrescue | https://www.gnu.org/software/ddrescue |
| dc3dd | https://sourceforge.net/projects/dc3dd |

---

# 19. CHEAT-SHEET — ARTIFACT TO TOOL MAPPING

The following maps the most common forensic question to the typical first-pass tool, organized by category. This is descriptive — not prescriptive — and consolidates material above.

**Filesystem / disk.**

| Question | First-pass tool |
|---|---|
| What partitions exist? | `mmls` |
| What filesystem on partition? | `fsstat` |
| List all files (allocated + deleted)? | `fls -r` |
| Recover one file by inode/MFT entry? | `icat` |
| Recover everything? | `tsk_recover -e` |
| Body file for mactime? | `fls -r -m` |
| Carve files from unallocated? | `blkls` → `photorec` / `foremost` |
| MFT-level NTFS detail? | `MFTECmd` |
| USN journal? | `MFTECmd -f \$J` |
| Mount E01? | `ewfmount` + `imagemounter` |
| Volume Shadow Copies? | `vshadowinfo` + `vshadowmount` |
| BitLocker volume? | `bdeinfo` + `bdemount` |

**Windows artifacts.**

| Question | First-pass tool |
|---|---|
| What ran on this host? | `PECmd` (Prefetch), `AmcacheParser`, `AppCompatCacheParser` |
| What programs did this user open? | `RECmd` UserAssist plugin, JLECmd, LECmd |
| What folders did this user navigate? | `SBECmd` |
| What is in the recycle bin? | `RBCmd` |
| Per-process network bytes? | `SrumECmd` |
| Recent activity timeline? | `WxTCmd` (ActivitiesCache) |
| Registry autoruns / persistence? | `RECmd` with Persistence batch + `rip.pl -p runkeys` |
| Lateral movement registry indicators? | `RECmd` Lateral_Movement batch |
| Suspicious browser history? | plaso `webhist` parsers + `SQLECmd` |

**Event logs.**

| Question | First-pass tool |
|---|---|
| Quick threat hunt across many EVTX? | `hayabusa csv-timeline` |
| Cross-check Sigma hits? | `chainsaw hunt` |
| Get specific EID extracted as CSV? | `EvtxECmd --inc <id> --csv` |
| Reconstruct logon timeline? | `hayabusa logon-summary` |
| Recover deleted EVTX records? | `evtxtract` |

**Memory.**

| Question | First-pass tool |
|---|---|
| Sanity check / OS? | `vol windows.info` |
| Running processes + hidden? | `vol windows.pslist` + `psscan` |
| Injected code? | `vol windows.malfind` |
| Hidden DLLs / modules? | `vol windows.ldrmodules` + `modscan` |
| Connections at acquisition time? | `vol windows.netscan` |
| Forensic timeline of memory? | `MemProcFS -forensic 1` |
| Bash history (Linux)? | `vol linux.bash` |

**Network.**

| Question | First-pass tool |
|---|---|
| Structured per-protocol logs from pcap? | `zeek -r` |
| Signature detections from pcap? | `suricata -r` |
| Beacon / C2 detection? | `rita` |
| Extract files from pcap? | `tshark --export-objects`, NetworkMiner |
| Ad-hoc query on pcap? | `tshark -Y` |
| File-transfer + cred forensics from pcap? | NetworkMiner |

**Malware triage.**

| Question | First-pass tool |
|---|---|
| What is this binary packed with? | `diec` |
| What capabilities does it have? | `capa` |
| Obfuscated strings? | `floss` |
| Pattern-match for known badness? | `yara` |
| Family / variant fuzzy match? | `ssdeep` / `tlsh` |
| Quick AV scan? | `clamscan` |
| Office macro extraction? | `olevba` |
| PDF object structure? | `pdfid` → `pdf-parser` |
| Decompile a function? | `r2 -q -c 'pdf @ main'` / `Ghidra` headless / `retdec` |

**Live triage / collection.**

| Question | First-pass tool |
|---|---|
| Windows endpoint targeted collection? | KAPE |
| Linux/Unix endpoint collection? | UAC |
| Memory acquisition (Windows)? | DumpIt / WinPMEM |
| Memory acquisition (Linux)? | AVML |
| Enterprise hunt-and-collect? | Velociraptor |

This mapping is a starting point, not a one-step playbook. Real investigations cross-validate via multiple tools per question and pivot based on what they find.

---

# 20. OUTPUT FORMAT REFERENCE

A consolidated reference of the structured output schemas the major tools produce. Useful when an investigator (or downstream automation) needs to know exactly which column / field carries which value.

## 20.1 l2tcsv (plaso super-timeline)

Header row:

```
date,time,timezone,MACB,source,sourcetype,type,user,host,short,desc,version,filename,inode,notes,format,extra
```

Field semantics:

- `date` — date in `MM/DD/YYYY`.
- `time` — time in `HH:MM:SS`.
- `timezone` — TZ identifier or offset.
- `MACB` — four-letter MACB indicating which timestamp attribute fired this row: M=modify, A=access, C=metadata change, B=birth/creation. `M...`, `.A..`, etc.
- `source` — short parser source code (`FILE`, `LOG`, `REG`, `EVT`, etc.).
- `sourcetype` — long source description.
- `type` — event-type description from the parser (e.g., `mtime`, `Last Visited Time`).
- `user` — associated user if known.
- `host` — hostname if known.
- `short` — short event summary.
- `desc` — longer event message.
- `version` — l2t version.
- `filename` — source file path.
- `inode` — inode of source file when applicable.
- `notes` — analyst-added notes.
- `format` — parser name.
- `extra` — key=value pairs of non-mapped attributes.

`l2ttln` is the same data in TLN (Timeline) format: `Time|Source|Host|User|Description`.

## 20.2 Plaso JSON line

Each line is a JSON object with a flat key-value structure. Common keys:

```json
{
  "__container_type__": "event",
  "__type__": "AttributeContainer",
  "data_type": "windows:registry:userassist",
  "timestamp": 1733260981123456,
  "timestamp_desc": "Last Time Executed",
  "parser": "winreg",
  "pathspec": "/mnt/case/Users/admin/NTUSER.DAT",
  "key_path": "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\UserAssist\\{...}\\Count",
  "value_name": "...",
  "number_of_executions": 3,
  "application_focus_count": 12,
  "application_focus_duration": 4321
}
```

`data_type` is the canonical identifier for the event flavor — useful for downstream filtering.

## 20.3 EZ tools CSV common columns

EZ tools emit per-tool CSV with mostly-unique columns, but the following columns recur:

- `SourceFile` — full path to the artifact that produced the row.
- `SourceCreated`, `SourceModified`, `SourceAccessed` — MAC stamps of the artifact file itself, ISO-8601 UTC with seven decimal places of precision.
- `SourceVolume` — volume serial when relevant.
- `Comment` — analyst comment column (blank from tool; usable in Timeline Explorer).

Timestamps in EZ tools are always UTC by default; pass `--utc` or `--local` if a tool offers it.

## 20.4 Zeek log columns (selected)

**conn.log.**

```
ts uid id.orig_h id.orig_p id.resp_h id.resp_p proto service duration orig_bytes resp_bytes \
   conn_state local_orig local_resp missed_bytes history orig_pkts orig_ip_bytes \
   resp_pkts resp_ip_bytes tunnel_parents
```

`conn_state` codes: `S0` (attempt, no reply), `S1` (established, not terminated), `SF` (established, completed), `REJ` (rejected), `S2`/`S3` (half-closed states), `RSTO`/`RSTR` (reset by orig/resp), `RSTOS0`/`RSTRH` (reset variants), `SH`/`SHR` (no SYN seen), `OTH` (no SYN, midstream).

`history` is a compact string of character codes per packet observed: lowercase = orig→resp, uppercase = resp→orig. `s` SYN, `h` SYN-ACK, `a` ACK, `d` data, `f` FIN, `r` RST, `c` bad checksum, `i` inconsistent, `q` truncated.

**dns.log.**

```
ts uid id.orig_h id.orig_p id.resp_h id.resp_p proto trans_id rtt query qclass qclass_name \
   qtype qtype_name rcode rcode_name AA TC RD RA Z answers TTLs rejected
```

`AA`, `TC`, `RD`, `RA` are DNS header flag bits. `rcode_name` is `NOERROR`, `NXDOMAIN`, `SERVFAIL`, etc.

**http.log.**

```
ts uid id.orig_h id.orig_p id.resp_h id.resp_p trans_depth method host uri referrer \
   version user_agent origin request_body_len response_body_len status_code status_msg \
   info_code info_msg tags username password proxied orig_fuids orig_filenames \
   orig_mime_types resp_fuids resp_filenames resp_mime_types
```

**ssl.log.**

```
ts uid id.orig_h id.orig_p id.resp_h id.resp_p version cipher curve server_name \
   resumed last_alert next_protocol established cert_chain_fuids client_cert_chain_fuids \
   subject issuer client_subject client_issuer validation_status ja3 ja3s
```

`fuids` columns reference file IDs in `files.log` and `x509.log`.

**files.log.**

```
ts fuid tx_hosts rx_hosts conn_uids source depth analyzers mime_type filename duration \
   local_orig is_orig seen_bytes total_bytes missing_bytes overflow_bytes timedout \
   parent_fuid md5 sha1 sha256 extracted extracted_cutoff extracted_size
```

`md5`/`sha1`/`sha256` populated by `policy/frameworks/files/hash-all-files.zeek`.

## 20.5 Suricata EVE JSON keys (top-level)

```json
{
  "timestamp": "2026-06-02T14:32:01.234567+0000",
  "flow_id": 12345678901234,
  "in_iface": "eth0",
  "event_type": "alert",
  "src_ip": "10.0.0.5",
  "src_port": 51234,
  "dest_ip": "1.2.3.4",
  "dest_port": 443,
  "proto": "TCP",
  "tx_id": 0,
  "alert": {
    "action": "allowed",
    "gid": 1,
    "signature_id": 2024897,
    "rev": 5,
    "signature": "ET MALWARE Suspicious User-Agent",
    "category": "A Network Trojan was detected",
    "severity": 1,
    "metadata": {...}
  },
  "http": {...},
  "tls": {...},
  "flow": {...},
  "payload": "...",
  "payload_printable": "...",
  "stream": 1,
  "packet": "...",
  "packet_info": {...}
}
```

For non-alert events the relevant key (`http`, `dns`, `tls`, `flow`, etc.) contains the per-protocol payload.

## 20.6 Hayabusa CSV (default profile)

```
Timestamp,RuleTitle,Level,Computer,Channel,EventID,RecordID,Details,MitreTactics,MitreTags,OtherTags,RuleFile,EvtxFile
```

The `verbose` and `super-verbose` profiles add `RuleAuthor`, `RuleModifiedDate`, `Status`, `RuleCreationDate`, full event data fields, raw XML, source file offset.

## 20.7 Chainsaw output

Default CSV columns:

```
timestamp,detections,path,event_id,record_id,computer,channel,...
```

`detections` is a semicolon-separated list of rule names that fired on the event. JSON output nests this as an array.

## 20.8 capa JSON

```json
{
  "meta": {
    "argv": [...],
    "format": "pe",
    "sample": {"md5": "...", "sha1": "...", "sha256": "..."},
    "analysis": {"format": "pe", "arch": "amd64", "os": "windows", "extractor": "vivisect"}
  },
  "rules": {
    "encrypt data using RC4 PRGA": {
      "meta": {
        "name": "encrypt data using RC4 PRGA",
        "namespace": "data-manipulation/encryption/rc4",
        "attack": [{"id": "T1573.001", "tactic": "Command and Control"}],
        "mbc": [...]
      },
      "matches": [
        [{"type": "absolute", "value": 4294978032},
         {"success": true, "node": {...}}]
      ]
    }
  }
}
```

`matches[*][0]` is the address; `matches[*][1]` is the match tree (which sub-features fired).

## 20.9 YARA CLI output

Default (no `-s`):

```
rule_name file_path
rule_name file_path
```

With `-s`:

```
rule_name file_path
0x100:$a: matched_bytes_or_text
0x200:$b: matched_bytes_or_text
```

With `-m`:

```
rule_name [author="...",description="..."] file_path
```

With `--print-tags`:

```
rule_name [tag1,tag2] file_path
```

JSON output is not native; community wrappers (`yara-python`, custom scripts) produce JSON.

---

# 21. CLOSING NOTES

The SIFT toolchain is wide. No real investigation uses every tool documented here. A given case touches 5–15 of them depending on what evidence is available, what hypotheses get tested, and what the analyst's preferred tools are. The selection per case is itself part of investigator skill — recognizing that a question is best answered by `windows.malfind` rather than `windows.pslist`, or that ShellBags will answer "did this user know about this folder?" more cleanly than file MAC times will.

The tools split roughly by orientation:

- **Production / extraction tools.** Pull artifacts out of evidence into structured form. Examples: TSK, plaso, MFTECmd, EvtxECmd, log2timeline.
- **Detection tools.** Apply rules / patterns / heuristics over extracted data. Examples: YARA, Hayabusa, Chainsaw, Suricata, RITA, capa.
- **Reasoning tools.** Help an analyst form and verify hypotheses. Examples: Timeline Explorer (GUI), Volatility plugins of the `*scan` family, MemProcFS `findevil` mode, Velociraptor notebooks.
- **Acquisition tools.** Get evidence in the door without contaminating it. Examples: ewfacquire, DumpIt, WinPMEM, AVML, LiME.

These categories are leaky — `MFTECmd` extracts but also flags timestomp; `plaso` extracts but its tagging plugins detect; `capa` matches patterns but reasons over them too. The mental model matters less than the tool's actual surface area, documented above per-tool.

Software ages. Tool flags change between major versions. Specific invocations in this document reflect roughly the 2024–2026 surface; verify against `--help` of any tool used on a current SIFT build. The conceptual scope of each tool — what it parses, what it can and cannot do — is more durable than its CLI flags.

**A final note on tool selection epistemics.** Two tools that claim to parse the same artifact will sometimes disagree. ShimCache as parsed by `appcompatcache` (RegRipper) vs `AppCompatCacheParser` (EZ) can produce slightly different row counts on the same SYSTEM hive due to differences in how each handles deleted/overwritten entries. Volatility 3 `windows.netscan` and `windows.netstat` can produce different connection lists from the same memory image due to differing pool-scan heuristics. EVTX events parsed by EvtxECmd, plaso's `winevtx`, and Hayabusa's internal parser will agree on event content but may disagree on which channel name normalizes how (Windows localization edge cases) and on whether to emit one row per data field or one row per event.

The correct interpretation is not "one tool is buggy"; it is "these are independent implementations of an under-specified binary format, and the divergences themselves carry information." The discipline is to use two parsers on critical artifacts when the finding is consequential, and to note the source tool alongside the finding so that any later examiner can reproduce.

This is the substrate. Specific case decisions — which subset of tools to run, in what order, with what cross-checks — emerge from the case, not from this document.


---

# 18. REFERENCE INDEX

A flat index of the tools covered:

- Memory: Volatility 3, Volatility 2, Memory Baseliner, MemProcFS, WinPMEM, DumpIt, hibr2bin, LiME, AVML, linpmem
- Disk acquisition / mounting: ewfacquire, ewfmount, ewfverify, ewfinfo, dc3dd, dcfldd, dd_rescue, ddrescue, xmount, imagemounter, vshadowinfo, vshadowmount, bdeinfo, bdemount, fvdeinfo, fvdemount, libluksde
- Filesystem: TSK (mmls, fls, icat, istat, ils, blkls, tsk_recover, fcat, srch_strings), mactime
- Timeline: log2timeline.py, psort.py, psteal.py, pinfo.py, image_export.py, dftimewolf
- Windows artifact parsers (EZ): MFTECmd, EvtxECmd, AmcacheParser, AppCompatCacheParser, PECmd, RECmd, RBCmd, SBECmd, LECmd, JLECmd, SrumECmd, SQLECmd, bstrings, WxTCmd, Timeline Explorer
- Registry: RegRipper3.0, RECmd, python-registry
- Event logs: Hayabusa, Chainsaw, EvtxECmd + jq, evtxtract, python-evtx, libevtx
- Pattern matching: YARA, capa, FLOSS, strings, ssdeep, TLSH
- Carving: bulk_extractor, foremost, scalpel, photorec, binwalk, lightgrep
- Network: Wireshark, tshark, tcpdump, Zeek, Suricata, NetworkMiner, RITA, argus, mergecap, editcap
- Malware triage: ClamAV, PEStudio, pdf-parser/pdfid/peepdf, oletools (olevba/oleid/oledump), RetDec, radare2, Ghidra, PE-sieve, Moneta, Hollows Hunter
- Live triage / collection: KAPE, Velociraptor, UAC, AVML
- Anti-forensics detection: densityscout, Detect It Easy
- Hashing / integrity: md5sum, sha256sum, hashdeep, ssdeep, TLSH, mactime

This list is the encyclopedic surface area an IR-tooling investigator works against in a SIFT-class environment. Specific tool selection per case is a design decision, informed by — but not dictated by — this reference.
