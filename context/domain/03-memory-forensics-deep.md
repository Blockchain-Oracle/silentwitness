# Memory Forensics, Deep

> Reference manual on volatile-memory forensics for the design-phase agent and any later builder. Pure domain knowledge: what is true about memory, how it gets acquired, how Volatility (and friends) parse it, what artifacts each plugin produces, what each artifact tells you about adversary behavior, and where the whole enterprise breaks. No prescriptions about what the SilentWitness agent should do with this knowledge — only what is true so that downstream design choices can be made on a real footing.
>
> The companion document for non-volatile artifacts is `02-windows-artifacts-encyclopedia.md` (disk/registry/log) and `04-disk-network-log-forensics-deep.md` (NTFS internals, plaso, pcap, EID schema). This file lives between them: it covers the artifact that disappears the moment you pull the plug.

---

## 1. Why memory forensics matters

### 1.1 The order of volatility

The phrase **order of volatility** appears in RFC 3227 ("Guidelines for Evidence Collection and Archiving", Brezinski & Killalea, 2002) and is the moral spine of incident response. The principle is simple: evidence with shorter half-life should be captured first, because it can vanish during the act of capturing slower evidence. RFC 3227's ordering, lightly modernized:

1. CPU registers, cache, MMU TLB entries
2. Routing tables, ARP cache, process table, kernel statistics, kernel modules
3. RAM contents (the entire physical address space, including kernel pools and user-mode VADs)
4. Temporary file systems (`/tmp`, `%TEMP%`, page file, hibernation file)
5. Persistent disk
6. Remote logging / monitoring data relevant to the system
7. Physical configuration / topology
8. Archival media

RAM sits at the top of what is practically capturable. Registers and TLB are gone before any acquisition tool can read them. So in operational terms: **memory is the most volatile thing a forensicator can reliably get**. Pull the plug and it is gone. Reboot and it is gone (modulo cold-boot residue, which is a research curiosity, not a triage tool). Even leaving the machine running while you run a tool is enough to shift the contents: every plugin you execute creates allocations, every command updates `lastaccessed` flags in kernel objects, every page that gets swapped out is no longer in RAM.

This is the foundational reason memory acquisition is treated as a one-shot, time-sensitive operation distinct from disk imaging.

### 1.2 What lives only in RAM

A non-exhaustive list of evidence types that are typically RAM-only or RAM-first, with a note on why each one matters:

- **Running processes and their parent/child relationships at the moment of capture.** Disk has `Amcache`, `Prefetch`, `Sysmon EID 1`, `Security 4688`; memory has the live `EPROCESS` graph with handle tables and thread state. Disk tells you a process ran; memory tells you it was running and what it was doing.
- **Network connections in `ESTABLISHED`, `LISTEN`, `TIME_WAIT`, `CLOSE_WAIT` states.** Disk has Sysmon EID 3 if Sysmon was configured and not tampered with; memory has the live `TCB`, `UDP`, and `_LISTENER` structures regardless.
- **Decrypted payloads.** Packed/encrypted malware on disk is opaque. Once it runs and unpacks itself in memory, the deciphered code is sitting in RWX or RX private memory pages that `windows.malfind` and `yarascan` can find.
- **In-memory-only credentials.** `lsass.exe` holds NT hashes, Kerberos TGTs, plaintext passwords (depending on Credential Guard state), DPAPI master keys, and WDigest credentials. Disk has none of this except the SAM/SECURITY hives (which Volatility can also extract from memory).
- **Command history not yet persisted.** Open `cmd.exe` consoles hold their full history in the `conhost.exe` heap. PowerShell consoles hold their input/output buffers similarly. Disk has `PSReadLine` history (since PowerShell 5.1) only after the session is closed and the buffer is flushed.
- **Mutex / event / semaphore handles.** Malware families fingerprint themselves with named kernel objects to prevent re-infection or to coordinate. These exist in the handle table but rarely on disk.
- **Open handles to deleted files.** A process can have a handle to a file the adversary already `del`-ed. The file content is still allocated on disk (until the handle closes), and memory has both the file object and the handle. This is how IR teams recover wiped staging payloads.
- **Loaded but disk-deleted modules.** A DLL loaded from a path that has since been deleted still has its `LDR_DATA_TABLE_ENTRY` in memory, its sections mapped, and its image header sitting in RAM. `dlllist`, `modules`, and `dumpfiles` can recover it.
- **Reflectively-loaded code.** Modules loaded via `LoadLibrary` go on the three loader lists (`InLoadOrder`, `InMemoryOrder`, `InInitializationOrder`). Reflectively-loaded modules (Cobalt Strike beacon, Meterpreter, Sliver, custom reflective loaders) do not appear on any of the lists; they only exist as private RWX VADs with PE headers visible to `malfind`/`yarascan`.
- **Kernel callbacks, SSDT hooks, IRP function pointers.** Rootkit-style modifications to kernel object dispatch tables exist only in kernel memory. Disk has the driver file (if it was loaded from disk), but the runtime modification is RAM-only.
- **Window hooks, keyboard hooks, mouse hooks.** Implemented via `SetWindowsHookEx`. Their target DLLs and hook chains live in `win32k.sys` data structures.

### 1.3 Malware behavior that requires execution

Modern adversary tooling assumes a memory-only operating model. The reasons are practical:

- **Static AV evasion.** A packed/encrypted binary on disk is opaque to signature scanners. Once memory-resident and decrypted, it is signature-able — but by then it is in RAM only, and the on-disk artifact may have been deleted.
- **Reflective DLL loading.** Stephen Fewer's reflective loader (2008) and every variant since (Cobalt Strike's `ReflectiveLoader`, sRDI, etc.) puts a DLL into memory without ever calling `LoadLibrary`, so the module never appears in the PEB loader lists. This is why `ldrmodules` exists as a plugin: to cross-check whether a VAD looks like a PE but is missing from all three loader lists.
- **Process hollowing / process replacement.** The attacker spawns a legitimate `svchost.exe` suspended, unmaps its image section, allocates RWX memory, copies malicious PE bytes in, sets the EIP/RIP to the malicious entry point, and resumes. On disk the process looks legitimate (the image file is the real `svchost.exe`). In memory, the loaded code does not match the on-disk image — `ldrmodules` and `dlllist` will show the discrepancy.
- **Process doppelgänging (Liberman & Kogan, BlackHat EU 2017).** Uses NTFS transactions to load a transacted-and-rolled-back PE into a process. On disk the malicious image never exists post-transaction. Only memory holds the truth.
- **Process Herpaderping (Johnson, 2020) and Process Ghosting (Kolsek, 2021).** Variants that defeat scan-on-modify AV by mutating the image on disk after the section is mapped or by loading from a delete-pending file. Memory is the only place the executed code can be examined intact.
- **Living-off-the-land binaries (LOLBins).** `rundll32.exe`, `regsvr32.exe`, `mshta.exe`, `msbuild.exe`, `installutil.exe` execute attacker code from a benign signed binary's process space. The PE on disk is Microsoft-signed. The malicious code is only visible in memory as injected sections, suspicious VADs, or in-process loaded scriptlets.
- **In-memory C2 implants.** Cobalt Strike beacon, Meterpreter, Sliver implant, Brute Ratel badger, Mythic Apollo — all default to memory-resident operation, with disk persistence as an opt-in. Their configurations (C2 URLs, sleep times, jitter, malleable profiles) are decrypted into RAM at runtime and never written to disk.
- **Fileless persistence via WMI / registry blobs / scheduled tasks containing base64 PowerShell.** The persistence vector is on disk; the executed code only fully assembles in memory.

Operationally: if your investigation skips memory, you skip the layer at which most modern intrusions are observable.

---

## 2. Memory acquisition

Acquisition is the act of writing the physical address space of a live system to a stable file. The acquisition layer is conceptually separate from analysis: you must acquire before you can analyze, and the acquisition tool's choices (what it includes, in what order, with what consistency) constrain everything downstream.

### 2.1 General properties of memory acquisition

A memory dump is, ideally, a byte-for-byte copy of physical memory at a single instant. In practice it never is, because:

- The acquisition tool itself runs on the system being acquired, using CPU, allocating memory, scheduling threads.
- Acquisition takes seconds to minutes; the system continues to execute and modify pages during that window. This produces **memory smear**: the contents of the dump reflect different points in time, leading to inconsistent kernel structures (e.g., a process listed in `PsActiveProcessHead` but with a zeroed handle table, because the process exited mid-acquisition).
- Hardware-protected regions (SMRAM, certain memory-mapped device buffers, PCI MMIO ranges) may not be readable by software acquisition.
- On modern Windows, **Virtualization-Based Security (VBS)** and **Hypervisor-Protected Code Integrity (HVCI)** allocate memory in the secure kernel (VTL1) that the normal kernel (VTL0) cannot read. Memory acquisition runs in VTL0 and produces gaps or zero-pages for VTL1-protected content (notably Credential Guard's isolated LSA).

### 2.2 WinPMEM

WinPMEM is the most commonly cited Windows kernel-mode memory acquisition driver. It originated in the Rekall project (Mike Cohen) and continues to be maintained as part of the velociraptor.app / rekall lineages. Key properties:

- Ships as a single executable that loads a signed kernel driver, reads physical memory via the driver, and writes to disk or a pipe.
- Outputs raw, AFF4, or ELF formats depending on flags.
- Has flags for selecting page-table walking method: `-i` (`MmGetPhysicalMemoryRanges`-based), PTE walking, or PCI-config space probing.
- Can stream over the network (`-o -` to stdout, piped through netcat or similar).
- Microsoft-signed driver historically; current versions require code-signing maintenance because Windows demands it.

Operational behaviors and gotchas:

- Loading the driver creates Sysmon EID 6 (`Driver loaded`) and Security 4673 if auditing is on. The acquisition itself leaves traces. This is unavoidable.
- WinPMEM allocates memory for its own buffers; those allocations appear in the acquired dump.
- On Windows 10/11 with Memory Integrity (HVCI) enabled, the driver may fail to load if not in the HVCI-compatible state.

### 2.3 Magnet RAM Capture (MRC)

Free Windows tool from Magnet Forensics. GUI-driven, single-binary, no installer required. Outputs raw (`.raw`/`.dmp`/`.bin`) memory dumps. Notes:

- Designed for first-responder ease of use; minimal options.
- Loads a kernel driver (signed by Magnet).
- Captures `MmGetPhysicalMemoryRanges`-reported ranges.
- Does not capture VTL1 protected memory.
- Defaults to writing to the location specified in the GUI. The output filename includes a timestamp.

### 2.4 DumpIt

Originally from MoonSols (Matthieu Suiche). The free version is now distributed by Comae (Magnet acquired Comae in 2023). Properties:

- Single-binary, runs as Administrator, prompts for confirmation.
- Outputs Microsoft Crash Dump (`.dmp`) format by default, which is convenient because Windbg and Volatility both accept it natively.
- Recent versions support Microsoft Full Memory Crash Dump format with metadata structures.
- Comae cloud version (paid) uploads directly to a cloud bucket.

### 2.5 Microsoft Crash Dump format

A Microsoft kernel-mode crash dump (`.dmp`) is the native format Windows itself produces when the kernel bugchecks (BSOD). Variants:

- **Small/Minidump** (~64KB to several MB): just bugcheck info, registers, stack of the bugcheck thread, and a small set of pages. Not useful for forensics — too narrow.
- **Kernel memory dump** (a few hundred MB): kernel-mode memory only. Useful for kernel debugging but missing user-mode process content. Generally not enough for IR.
- **Complete memory dump** (size of physical RAM): everything. This is what acquisition tools that produce `.dmp` aim for, and what Volatility 3's `windows.info` happily reads.
- **Automatic memory dump** (Windows 8+): variant of kernel dump with size hint, written to a smaller pagefile.
- **Active memory dump** (Windows 10+): kernel + active user processes, excluding zero pages and memory of paused virtual machines.

Volatility 3 reads complete and active memory dumps without ceremony. Kernel-only dumps work for kernel-mode plugins (`modules`, `driverscan`, `callbacks`, `ssdt`) but yield empty results for user-mode plugins (`pslist` may show structures but with unmapped user VADs).

The `.dmp` format has a `DUMP_HEADER` / `DUMP_HEADER64` at offset 0, with `Signature = "PAGE"`, `ValidDump = "DUMP"`, version info, directory table base (CR3), PsLoadedModuleList pointer, PsActiveProcessHead pointer, and a `PhysicalMemoryBlock` describing the physical-page runs. Volatility 3 uses this header to bootstrap its translation layer.

### 2.6 Hibernation file (`hiberfil.sys`)

When a Windows system hibernates, the kernel writes a compressed snapshot of physical memory to `C:\hiberfil.sys` on the system volume. This file is a **time-travel forensic goldmine**: it contains the state of the system at the moment it hibernated, which may be hours, days, or weeks before incident response begins.

Format properties:

- The file has a `PO_MEMORY_IMAGE` header (the structure name is internal Microsoft nomenclature) describing the layout.
- Pages are stored in compressed segments. Compression algorithm has changed across Windows versions: NT5/XP used a Xpress variant; Windows 7 and later use **Xpress Huffman**. Windows 10 introduced additional compression variants.
- Not all of physical RAM is in `hiberfil.sys` — only the working sets that the kernel deemed worth preserving plus kernel-resident pages. Pages backed by file-mapped sections that can be restored from the file system are not duplicated in `hiberfil.sys`.

Two paths to analyze it:

1. **Decompress first, then point Volatility at the raw image.** The classic tool is `hibr2bin` from Comae/Suiche's hibernation work (originally part of `MoonSols Windows Memory Toolkit`, later folded into Comae and Magnet). It reads the hibernation file, expands all compressed segments, and writes a flat raw image. Modern equivalents: `volatility/hibr2bin`, `python-evtx`-unrelated `arsenal hibernation recon`, and Hibernation Recon (Arsenal Recon, paid).
2. **Read `hiberfil.sys` directly in Volatility 3.** Volatility 3 has a hibernation layer (`volatility3.framework.layers.crash`, `vmware`, `lime`, plus a hibernation handler in the layer chain). For Windows 7-era hibernation, this often works directly. For Windows 10/11 hibernation with newer compression formats, pre-decompression with a current `hibr2bin` is the more reliable path.

Operational notes:

- `hiberfil.sys` is locked while the system is up. Acquire it via raw disk read, FTK Imager, or `Get-FileHash`-style access through a mounted forensic image.
- The system clears hibernation state on resume; if the user resumed before you image the disk, `hiberfil.sys` may be present but stale or marked invalid (`PO_MEMORY_IMAGE` signature zeroed or status set to "Resume").
- `powercfg /hibernate off` deletes the file. On systems where hibernation is disabled by policy (common on enterprise desktops and servers), this artifact never exists.
- On Windows 10/11 systems with **Fast Startup** enabled, the system writes a partial hibernation file on shutdown containing the kernel state. This means even on systems that "never hibernate" by user action, `hiberfil.sys` may contain kernel-mode memory from the last shutdown.

### 2.7 Virtual machine snapshot files (VMSS / VMEM / VMSN)

Virtual machines run their guest physical memory inside files on the host. VMware ESXi, VMware Workstation/Fusion, VirtualBox, Hyper-V, and KVM all expose memory differently.

**VMware** uses two relevant files:

- `.vmem` — flat raw image of guest physical RAM when the VM is suspended or has a snapshot taken. Same byte layout as a software-acquired raw dump. Volatility 3 reads this directly.
- `.vmss` / `.vmsn` — snapshot state files containing CPU state, registers, device state, and metadata. Volatility's `vmware` layer understands these for cases where the `.vmem` is not present (some snapshot configurations bundle memory into the `.vmsn`).

Acquisition for VMware is often **just copying the file** while the VM is suspended — much cleaner than software acquisition because there is no smear, no driver load, no shifting working sets. This is why "suspend the VM and grab the `.vmem`" is the default IR move when the target is virtualized.

**Hyper-V** uses `.bin` and `.vsv` files (saved-state) and `.vmrs` (VM runtime state). Hyper-V memory dumps are extractable via `Save-VM` followed by a raw read of the saved-state file. Volatility 3 does not always have native Hyper-V layer support; the practical move is converting via a tool like `vm2dmp` or using Microsoft's debugger to produce a `.dmp`.

**VirtualBox** can dump memory of a paused VM via `VBoxManage debugvm <vm> dumpvmcore --filename=<file>`. Output is ELF core format readable by Volatility's ELF/LiME-compatible layer paths.

**KVM/QEMU** dumps via `virsh dump <domain> <file> --memory-only` produce ELF core dumps. Volatility 3 reads these via its ELF layer.

Practical implication: any time the target is virtual, acquisition can be hypervisor-mediated, which is faster, cleaner, and leaves no driver footprint inside the guest.

### 2.8 Other acquisition methods

- **FireWire / Thunderbolt DMA.** Legacy hardware acquisition by abusing the DMA capability of FireWire and pre-Thunderbolt-3 ports. Functionally dead on modern Windows due to **Kernel DMA Protection** and `IOMMU`/VT-d enforcement.
- **Cold boot attack.** Halting the machine with chilled RAM and re-imaging in a recovery environment. Real but firmly in the academic/red-team box; not a routine IR move.
- **PCILeech / DMA over PCIe.** Ulf Frisk's work — uses a PCIe device (Screamer, FPGA) to read host memory over DMA. Bypasses VBS depending on configuration. More red-team than IR but worth knowing about.
- **AVML (Acquire Volatile Memory for Linux).** Microsoft's open-source Linux memory acquisition tool. Reads `/proc/kcore` or `/dev/crash` and writes LiME-compatible output. Runs as a single static binary.
- **LiME (Linux Memory Extractor).** Loadable kernel module (LKM) that exposes a `/dev/lime` interface, writes raw or LiME format. The de facto Linux acquisition tool.
- **`/proc/kcore`.** Pseudo-file on Linux providing kernel-mapped physical memory. Readable by root. Truncatable to a complete dump with appropriate tooling. Useful when LKM loading is blocked.
- **`fmem`.** Older Linux kernel module exposing `/dev/fmem`. Largely superseded by LiME.

### 2.9 Acquisition pitfalls (cross-cutting)

- **Atomicity.** No software acquisition is atomic. Process tables, handle tables, network connection tables, and VADs may be inconsistent between the time they are read at the start of acquisition and the end. Hibernation files and VM snapshots are closer to atomic because the OS itself froze execution before serialization.
- **Memory smear.** Different regions reflect different timestamps. Symptoms: a process appears in `pslist` but its threads have already exited; a handle table references freed objects; a network connection structure points to a freed socket. Plugins may emit error lines or skip records when smear corrupts pointers.
- **Driver-load footprint.** Every software acquisition tool that loads a kernel driver leaves Sysmon EID 6, Security 4673, and a row in the driver list. Acquisition itself is an evidentiary event.
- **Acquisition-tool memory footprint.** The tool's own process and buffers appear in the dump. `pslist` will show `winpmem.exe` or `DumpIt.exe`. Investigators ignore these but they are not "wrong" — they really were running.
- **Working set vs full RAM.** Some tools default to capturing only the active working set rather than the full physical address space. Verify the size against installed RAM; a 1 GB dump from a 64 GB system is usually a partial capture.
- **Sparse files vs dense files.** Some `.dmp` writers create sparse files where un-mapped physical pages are filesystem holes. Tools that copy the dump may inflate or deflate it depending on copy semantics. SHA-256 of the dump file is therefore brittle to copy method; compare via plugin output instead.
- **VBS-protected pages.** On systems with Credential Guard, the VTL1 LSA isolation means `lsadump` and `hashdump` will yield empty or partial results even though acquisition succeeded — the kernel never had the bytes in VTL0.
- **Encrypted hibernation.** Windows 10/11 can encrypt `hiberfil.sys` (related to BitLocker and Windows Hello-derived keys). An encrypted hibernation file is forensically opaque without the key.

---

## 3. Memory image formats

The bytes Volatility 3 reads can be in a variety of container formats. Each format encodes the physical address space differently and carries different metadata.

### 3.1 Raw (`.raw`, `.bin`, `.dd`, `.mem`)

The simplest format: a flat sequence of bytes where offset `n` in the file corresponds to physical address `n` in RAM. No header, no metadata, no compression. Most acquisition tools support raw output; it is the lingua franca of memory imaging.

Pros: trivial to parse, supported by every analysis tool.
Cons: file size equals installed RAM (a 128 GB-RAM workstation produces a 128 GB dump), no built-in integrity metadata, gaps in physical-memory ranges (MMIO holes) are usually written as zeros, inflating the file.

Volatility 3 handles raw via the `FileLayer` directly; the OS-detection automagic determines whether to apply a Windows, Linux, or Mac symbol stack on top.

### 3.2 AFF4 (`.aff4`)

Advanced Forensic Format 4, a successor to AFF/AFF1. Container format using ZIP-style packaging with embedded streams, metadata in RDF/Turtle, and pluggable compression (snappy, zlib, deflate). WinPMEM emits AFF4 as one of its formats.

Properties:

- Multi-stream container: physical memory, page file(s), kernel debugger structures, and arbitrary auxiliary data can be packed together.
- Compressed by default. A 64 GB RAM dump may produce a 10–20 GB AFF4.
- Integrity: each stream has hashes.
- Volatility 3 reads AFF4 via `volatility3.framework.layers.aff4`.

### 3.3 LiME (Linux Memory Extractor format)

Linux-native format produced by the LiME LKM and by AVML. Header per physical-memory range:

```
typedef struct {
    unsigned int magic;       // 0x4C694D45 = "LiME"
    unsigned int version;
    unsigned long long s_addr;
    unsigned long long e_addr;
    unsigned char reserved[8];
} lime_header_t;
```

The file is a concatenation of (header, payload) tuples covering each physically present range. This is more efficient than raw for Linux systems with sparse physical-memory layouts.

Volatility 3 reads LiME via its LiME-specific layer.

### 3.4 ELF core (Linux, BSD, hypervisor dumps)

Linux's standard core-dump format extended for full-system memory. Used by `virsh dump`, `VBoxManage dumpvmcore`, `kdump`, and `makedumpfile`. ELF program headers describe `LOAD` segments mapping to physical-memory ranges.

Properties:

- Standard ELF parsing applies; tools like `readelf -l` can inspect segment layout.
- `makedumpfile` can filter out userspace and zero pages, producing a kernel-only dump.
- Volatility 3 reads ELF-core directly.

### 3.5 Microsoft Crash Dump (`.dmp`)

Discussed in §2.5. Native Windows format with `DUMP_HEADER`, `PhysicalMemoryBlock`, and metadata pointers (`DirectoryTableBase`, `PsActiveProcessHead`, `PsLoadedModuleList`). Volatility 3 reads via `volatility3.framework.layers.crash`.

A crash dump has the advantage that the kernel itself produced it (or a kernel-mode acquisition tool produced it with the kernel's data structures already canonicalized). It carries the directory table base (`CR3`) explicitly, avoiding the automagic dance of guessing it.

### 3.6 VMware VMEM / VMSN

Discussed in §2.7. `.vmem` is essentially raw guest-physical layout. `.vmsn` is a snapshot container that may include the memory inline. Volatility 3's `vmware` layer parses both.

### 3.7 EnCase / Expert Witness Format (`.E01`)

EnCase's container format, also used by FTK Imager and `ewfacquire`. Originally a disk-imaging format, occasionally pressed into service for memory dumps. Properties:

- Chunked, compressed, MD5/SHA-1 hashed.
- Proprietary but reverse-engineered (`libewf`).
- Volatility 3 does not natively read `.E01`; the conventional workflow is `ewfmount` or `ewfexport` to expose the underlying raw image, then Volatility on the raw.

### 3.8 Hibernation file (`hiberfil.sys`)

Discussed in §2.6. Compressed Xpress Huffman segments wrapping kernel pages. Volatility 3 reads modern hiberfil via its `crash` or `hibernation` layer in some versions; for newer Windows 10/11 compression, pre-decompression with `hibr2bin` is the conservative path.

### 3.9 Page file (`pagefile.sys`, `swapfile.sys`)

Not a memory acquisition format per se, but an essential companion. When Volatility encounters paged-out content, it cannot read the page from the RAM dump (the page is on disk). Supplying the page file as a secondary layer lets Volatility 3 satisfy reads against paged-out addresses.

Volatility 3 supports this via `--single-location` for the RAM dump plus `--swap-locations` for one or more swap files. Without page file, certain plugin output may include `(swapped)` notes or simply produce gaps for paged-out content.

---

## 4. Volatility 3 architecture

Volatility 3 is the second-generation rewrite of the Volatility Framework, released in 2019 by the Volatility Foundation under Andrew Case, Aaron Walters, Michael Ligh, and contributors. The core conceptual change from Volatility 2 is replacing OS "profiles" with a **symbol-cache architecture** driven by Microsoft PDB files (Windows) and DWARF (Linux/Mac).

### 4.1 Layered abstraction model

Volatility 3 frames memory analysis as a stack of **translation layers**, each consuming the layer below and exposing a different view:

```
+--------------------------------------------+
|  Plugins (windows.pslist, windows.malfind) |
+--------------------------------------------+
|  Symbol-aware Object Model                  |
+--------------------------------------------+
|  Intel32 / Intel64 / AArch64 translation    |
|  (virtual → physical page walks)            |
+--------------------------------------------+
|  PageFile layer (optional)                  |
+--------------------------------------------+
|  Crash / LiME / AFF4 / VMware / Raw layer   |
+--------------------------------------------+
|  Physical file on disk (memory image)       |
+--------------------------------------------+
```

Each layer is a Python class implementing the `DataLayerInterface`. A layer accepts read requests at an address space appropriate to that layer (file offset, physical address, virtual address) and translates downward.

The Intel32 / Intel64 / AArch64 layers walk x86 / x86-64 / ARM64 page tables. Given a virtual address and a `DTB` (Directory Table Base, the CR3 value for a process), the layer walks `PML4 → PDPT → PD → PT` and returns the physical address. The process-specific virtual address space is just an Intel64 layer initialized with that process's CR3.

This composability is the architectural difference from Volatility 2. In Vol2, profile selection was a global parameter and the address-space stack was less abstract. In Vol3, plugins ask the layer chain for a virtual read and the framework finds the right page-table walker.

### 4.2 Symbol cache (PDB-driven)

Volatility 3 needs to know the layout of kernel structures (`_EPROCESS`, `_KPROCESS`, `_PEB`, `_LDR_DATA_TABLE_ENTRY`, etc.) at the **exact build** of the kernel that produced the memory dump. Microsoft compiles `ntoskrnl.exe` (and friends) with private PDB symbol files that describe every structure's field offsets, sizes, and types. These PDBs are publicly hosted at `https://msdl.microsoft.com/download/symbols`.

The Vol3 workflow:

1. **Read the kernel base's `IMAGE_DEBUG_DIRECTORY`** out of the memory image. This contains a CodeView record with the PDB filename (`ntkrnlmp.pdb`) and a GUID + age that uniquely identifies that build.
2. **Look up an Intermediate Symbol File (ISF)** in the local cache. Vol3 distributes pre-converted ISF files and can also generate them on demand from raw PDBs.
3. **If not cached, fetch the PDB from Microsoft's symbol server** and convert it to ISF (a JSON format Vol3 consumes).
4. **Bind kernel structure types** to the symbol table. Now `_EPROCESS.ImageFileName` resolves to a concrete offset and size for this exact kernel build.

The big practical wins of this design:

- No need to maintain a static profile per Windows build. Microsoft ships new kernel builds via Patch Tuesday roughly monthly; Vol2 required a community member to author a new profile per build. Vol3 just fetches the PDB.
- The same plugin code works across all Windows versions Microsoft supports, modulo structure-evolution edge cases.
- Custom kernels (Windows Insiders, internal builds, debug kernels) work as long as a PDB is available.

The big practical losses:

- Requires either prior caching or live internet access to `msdl.microsoft.com`. Air-gapped analysis requires pre-staging ISFs.
- Microsoft can (and occasionally does) take down old PDBs. If a memory image is from a kernel build whose PDB has rotated off the symbol server and you have no local cache, Vol3 cannot construct types for that build.
- Linux and Mac do not have an equivalent canonical symbol server. Linux symbols come from DWARF in `vmlinux` or kernel debug packages; Mac symbols come from `kernel.dSYM`. Both are end-user-built or distribution-specific.

### 4.3 Automagic

"Automagic" is Vol3's term for the layered detection that runs before plugins. Its job: given a file path, figure out the OS, kernel version, KASLR slide, directory table base, and the right layer stack to expose to plugins.

The flow:

1. **`StackerLayer`** tries each known stacker (`Aff4Stacker`, `CrashStacker`, `ElfStacker`, `LimeStacker`, `VmwareStacker`, etc.) in order, asking "does this file look like your format?" Stackers stack a typed layer atop the raw file.
2. **`PdbSignatureScanner`** scans the physical address space for `RSDS` PDB record signatures and known kernel PDB names. Finds the kernel image's PDB GUID.
3. **`SymbolCacheResolver`** looks up the ISF (cached or fetched).
4. **`KernelModule`** binds kernel symbols and types.
5. **`KernelPDBScanner`** confirms the DTB (CR3 of the System process, conventionally PID 4) by trying candidate values until kernel structures are reachable and consistent.
6. **`WindowsIntelStacker`** stacks the Intel32/Intel64 layer atop everything with the discovered DTB.

By the time `vol -f image.raw windows.pslist` runs the `pslist` plugin, all of the above has already happened invisibly. The user sees this as a few seconds of "Progress: ..." output.

Failure modes:

- No stacker recognizes the file: usually means a corrupted dump or an unsupported format.
- PDB signature scan fails: hibernation files with the kernel paged out, or a partial dump that doesn't include the kernel image. Vol3 cannot proceed without identifying the kernel.
- ISF fetch fails: no network, or the PDB has been rotated off the Microsoft symbol server. Vol3 errors with an ISF-not-found message.
- DTB candidate validation fails: smeared dump where kernel pointers are inconsistent. Vol3 may report "unable to determine DTB" or pick a wrong DTB that gives partial but inconsistent results.

### 4.4 Contexts

A **context** in Vol3 is a runtime container that holds the layer stack, the symbol table, the configuration, and the loaded objects. Multiple contexts can exist in the same Python process; this is the mechanism by which Vol3 can analyze multiple memory images in one Python interpreter (`volshell` sessions, batch scripts).

Plugins receive a `Context` object and operate on layers and symbols within it. This is the API boundary between the framework and the plugin author.

### 4.5 Translation layers in detail

- **`Intel`** (32-bit non-PAE): 2-level page table, 4 KB pages, 32-bit virtual addresses.
- **`IntelPAE`**: 3-level page table (PDPT, PD, PT), 4 KB pages, 32-bit virtual addresses with 36-bit physical addresses.
- **`Intel32e`** (x86-64): 4-level page table (PML4, PDPT, PD, PT), 4 KB pages, 48-bit virtual addresses canonical-extended to 64-bit.
- **`AArch64`** (ARM64): 4-level page table with configurable granule (4 KB, 16 KB, 64 KB) and configurable TTBR ranges. Required for Windows on ARM and modern macOS / Apple Silicon Linux.
- **`WindowsIntel`**, `WindowsIntel32e`: Windows-flavored variants that know how to interpret Windows-specific page table entries (e.g., software-managed swap pointers, transition PTEs).

Each layer exposes `read(offset, length)` and `mapping(offset, length)` calls. `mapping()` returns the chain of underlying offsets that satisfy a read — useful for understanding which physical pages back a given virtual region (and which are paged out).

### 4.6 Plugins as the user-facing layer

Plugins are Python classes inheriting from `volatility3.plugins.PluginInterface`. Each declares its `requirements` (which layer types, which symbol tables, which options it needs), implements a `run()` method, and yields rows as `TreeGrid` records.

The `TreeGrid` is Vol3's structured output abstraction. Each row has typed columns; the framework renders it to text, CSV, JSON, or pretty tables based on the `--renderer` flag. This matters operationally: every plugin already emits structured output, no parsing required.

### 4.7 `volshell` and the Python API

Beyond `vol`, the framework ships `volshell` — an interactive Python shell pre-loaded with the framework's context and layers. Investigators script ad-hoc analysis here. `volshell` is the closest thing memory forensics has to `gdb` for live triage.

Programmatic access: the framework can be imported (`from volatility3.framework import contexts, ...`), a context constructed in code, and plugins invoked directly. This is the entry point for any wrapper, agent, or batch system that wants to drive Vol3 without shelling out.

---

## 5. Volatility 2 vs Volatility 3

Volatility 2.6.1 (last release 2019) is the legacy line. Volatility 3 is the current line. The conventional wisdom in DFIR circles in 2025–2026 is **Vol3 is mainstream for new work; Vol2 is the fallback for specific gaps**.

### 5.1 Where Vol2 still wins

- **Linux profile coverage.** Vol2's Linux support depends on community-built profiles tied to specific kernel builds. Many distributions have a long catalog of Vol2 profiles already published. Vol3's Linux support relies on DWARF symbols from `vmlinux`, which are not always trivially available. For old Linux memory images where a profile already exists, Vol2 is the path of least resistance.
- **Mac coverage.** Similar story: Vol2 has profiles for many macOS builds; Vol3's Mac support is younger.
- **Plugin breadth.** Vol2 accumulated 10+ years of community plugins. Not all have been ported to Vol3. Niche plugins (Bitcoin wallet finder, specific malware family decoders, some rootkit-specific analyzers) may still exist only in Vol2.
- **Legacy memory images.** Memory dumps from old systems (Windows XP, Server 2003, early 2008, RHEL 5) are well-served by Vol2 and may hit edge cases in Vol3.

### 5.2 Where Vol3 dominates

- **Windows coverage going forward.** Symbol cache means every new Patch Tuesday build is automatically supported, no profile maintenance.
- **Architecture quality.** Layered design, programmatic API, structured output, modern Python.
- **Active development.** New plugins, bug fixes, and features land in Vol3. Vol2 is in maintenance only.
- **Cleaner output.** `TreeGrid` produces JSON/CSV/HTML out of the box; Vol2's text-only output requires post-parsing.

### 5.3 Compatibility note

Vol2 and Vol3 do not share plugin code or profiles. A Vol2 plugin port to Vol3 is a non-trivial rewrite. The two tools can coexist on the same workstation without conflict; many SIFT installs ship both.

---

## 6. Symbol cache mechanics

This section drills into the symbol cache workflow because it is the most common failure point when Vol3 misbehaves.

### 6.1 First-step pattern

The conventional first plugin run against an unknown image is:

```
vol -f image.dmp windows.info
```

`windows.info` does the following:

- Triggers full automagic (stacker discovery, PDB scan, symbol resolution, DTB confirmation).
- Identifies the OS (Windows version, build number, service pack, kernel base address, KASLR slide).
- Emits a small table: `Kernel Base`, `DTB`, `Symbols`, `Is64Bit`, `IsPAE`, `Major/Minor Version`, `KdDebuggerDataBlock`, `KdCopyDataBlock`, `PfnDataBase`, `PsLoadedModuleList`, `PsActiveProcessHead`, `NtSystemRoot`.

If `windows.info` works, all other Windows plugins will work. If it fails, the failure message tells you exactly what's wrong:

- "Unable to validate the location of the kernel directory table base" → DTB autodetection failed (smear or partial dump).
- "Unable to find a suitable kernel image" → kernel image not in dump, or PDB signature missing.
- ISF-related errors → symbol cache miss.

### 6.2 ISF file fetching

When Vol3 needs an ISF (Intermediate Symbol File) for a Windows kernel build it hasn't seen, it queries:

```
https://msdl.microsoft.com/download/symbols/<pdbname>/<guid_age>/<pdbname>
```

For the kernel, `pdbname` is usually `ntkrnlmp.pdb` (multi-processor build) or `ntoskrnl.pdb` (single-processor). The `<guid_age>` is the 33-character hex string from the CodeView record.

Vol3 caches converted ISFs in:

- `~/.cache/volatility3/` on Linux
- Platform-equivalent caches elsewhere
- A bundled subdirectory in the Vol3 install (`volatility3/symbols/`)

### 6.3 `--symbol-dirs`

The `--symbol-dirs` flag (deprecated alias) and the modern equivalent specify additional locations Vol3 searches for ISFs:

```
vol --symbol-dirs /path/to/local/isfs -f image.dmp windows.pslist
```

Useful when:

- Pre-staging ISFs for air-gapped analysis.
- Using community-contributed ISFs (e.g., from the Volatility Foundation's `volatility3-symbols` GitHub repo).
- Using internally-built ISFs for custom kernels.

### 6.4 Offline operation gotchas

- **Pre-stage ISFs before going offline.** Visit `https://downloads.volatilityfoundation.org/volatility3/symbols/windows.zip` (Windows ISF bundle), `linux.zip`, `mac.zip` — download in advance, extract into the symbol directory.
- **The bundled symbol packs lag.** They are updated periodically but a kernel from last week's Patch Tuesday may not yet be in the bundle. Live network access is the catch-up path.
- **PDB conversion needs `pdbparse` or `ctypes`-based parsing.** Vol3 includes the conversion logic, but if it has to convert a raw PDB locally rather than fetching a pre-built ISF, the operation can take tens of seconds per PDB.
- **PDB on disk vs PDB on Microsoft symbol server.** A local Windows install has its kernel PDB if `symchk` or Visual Studio populated the symbol cache. Vol3 can be pointed at this cache to skip the network fetch.
- **Symbol server rotation.** Microsoft occasionally removes very old PDBs. Beta and Insider builds may never have public PDBs.

### 6.5 Generating ISFs manually

For an in-the-weeds situation (custom kernel, removed PDB), the ISF can be hand-built:

```
python3 -m volatility3.framework.symbols.intermed --convert <pdb_or_dwarf> --output <out.json>
```

Or, for DWARF:

```
dwarf2json windows --pdb <ntkrnlmp.pdb> --pdb-symstore <symstore> > ntkrnlmp.json
```

The Volatility Foundation provides `dwarf2json` for the Linux/Mac side.

---

## 7. Plugin catalog — Windows

This section catalogs the Windows plugins most central to IR triage. Each entry covers what the plugin scans/parses, the output schema (columns), and operational gotchas.

### 7.1 `windows.info`

**Purpose.** OS and kernel identification.

**Mechanism.** Runs full automagic; emits the kernel build identification.

**Output columns.** `Variable`, `Value`. Variables include `Kernel Base`, `DTB`, `Symbols`, `Is64Bit`, `IsPAE`, `Major/Minor Version`, `KdDebuggerDataBlock`, `KdCopyDataBlock`, `PfnDataBase`, `PsLoadedModuleList`, `PsActiveProcessHead`, `NtSystemRoot`, `KeNumberProcessors`, `SystemTime`, `NtProductType`, `NtMajorVersion`, `NtMinorVersion`.

**Gotchas.**
- The `SystemTime` is the time the dump was taken (boot time + uptime). Critical for correlating with other artifacts.
- `NtSystemRoot` tells you where Windows was installed (usually `C:\Windows`); useful for sanity-checking process image paths.
- If this plugin fails, nothing else will work.

### 7.2 `windows.pslist`

**Purpose.** List active processes by walking the kernel's `PsActiveProcessHead` doubly-linked list.

**Mechanism.** Starts at `PsActiveProcessHead`, follows the `ActiveProcessLinks` member of each `_EPROCESS` structure, yields a row per process.

**Output columns.** `PID`, `PPID`, `ImageFileName`, `Offset(V)`, `Threads`, `Handles`, `SessionId`, `Wow64`, `CreateTime`, `ExitTime`, `File output`.

**Gotchas.**
- Only sees processes still linked into `PsActiveProcessHead`. DKOM rootkits unlink entries; their processes are invisible to `pslist`.
- `CreateTime` is the kernel-recorded creation time. `ExitTime` is non-empty for processes that have exited but still have outstanding references (orphan parent-child relationships, lingering handle holders).
- Threads/Handles columns can be `0` for processes mid-teardown.
- `ImageFileName` is truncated to 15 characters (the `_EPROCESS.ImageFileName` field is `char[15]`). Use `cmdline` or `dlllist` for full paths.

### 7.3 `windows.psscan`

**Purpose.** List processes by **scanning** physical memory for `_EPROCESS` pool tag signatures, independent of any linked list.

**Mechanism.** Scans for the `Proc` pool tag (`\x50\x72\x6f\x63`) preceding a `_POOL_HEADER`. Validates candidate `_EPROCESS` structures by checking field sanity (DTB validity, thread count plausibility, name printability).

**Output columns.** Same as `pslist`, plus `Offset(P)` (physical offset).

**Gotchas.**
- Finds processes hidden from `pslist` by DKOM unlinking — this is the rootkit-detection move.
- Finds **terminated but not yet reaped** processes whose `_EPROCESS` is still in the pool. These appear with `ExitTime` set.
- Can find pool-tag collisions (false positives from non-process allocations). Validation reduces but does not eliminate them.
- The killer move: **diff `pslist` against `psscan`**. Processes in `psscan` but not in `pslist` = hidden or terminated. Processes in `pslist` but not in `psscan` = recently created and not yet pool-tagged completely (rare).

### 7.4 `windows.pstree`

**Purpose.** Render the process tree using parent-child relationships.

**Mechanism.** Walks `pslist` output and groups by `PPID`. Renders ASCII tree.

**Output columns.** `PID`, `PPID`, `ImageFileName`, `Offset(V)`, `Threads`, `Handles`, `SessionId`, `Wow64`, `CreateTime`, `ExitTime`, with indentation reflecting tree depth.

**Gotchas.**
- Parent PIDs can refer to long-dead processes (PID reuse), causing the tree to root processes under unrelated parents. Sanity check using `CreateTime` ordering.
- `SYSTEM` (PID 4) parents many kernel processes; `services.exe` parents most service processes; `svchost.exe` parents many shared-service-host processes; `explorer.exe` parents most user-launched processes; `csrss.exe` parents conhost instances. Deviations from these expected lineages are interesting.
- Process hollowing produces a process whose lineage looks legitimate but whose code is malicious; the tree alone cannot detect this.

### 7.5 `windows.psxview`

**Purpose.** Cross-reference up to eight process-listing methods to find inconsistencies that indicate hiding.

**Mechanism.** Runs multiple discovery methods in parallel:
- `pslist` (ActiveProcessLinks)
- `psscan` (pool tag scan)
- `Thrdproc` (walk threads back to their owning process)
- `Pspcid` (kernel's PID-handle table)
- `CSRSS` (csrss.exe's internal process handle table)
- `Sessions` (per-session process lists)
- `Deskthrd` (window stations / desktops)
- `Bigpools` (large pool allocations)

For each method, marks whether the process was found.

**Output columns.** `PID`, `ImageFileName`, plus a column per discovery method (`pslist`, `psscan`, `thrdproc`, `pspcid`, `csrss`, `session`, `deskthrd`, `bigpools`).

**Gotchas.**
- Vol3's `psxview` is more limited than Vol2's; not all methods are equally implemented across versions.
- Legitimate transient processes (e.g., processes in the middle of creation or termination) can show up in some methods and not others without being malicious.
- The interesting cell is "found by `psscan` but not by `pslist` AND not by `csrss` AND not by `pspcid`" — that pattern is hard to produce accidentally.

### 7.6 `windows.malfind`

**Purpose.** Identify suspicious memory regions that look like injected code.

**Mechanism.** For each process, walks the VAD tree and flags VADs that:
- Are private memory (not backed by a mapped file).
- Have execute permission (typically `PAGE_EXECUTE_READWRITE` — RWX — or `PAGE_EXECUTE_READ`).
- Optionally contain identifiable content (PE header `MZ`, shellcode patterns).

**Output columns.** `PID`, `Process`, `Start VPN`, `End VPN`, `Tag` (VAD tag, e.g., `VadS`), `Protection`, `CommitCharge`, `PrivateMemory`, `File output`, `Hexdump`, `Disasm`.

**Gotchas.**
- RWX private memory is the classic shellcode/reflective-DLL signature, but legitimate JIT engines (.NET CLR, Java JVM, V8) also allocate RWX. Expect false positives in browsers and managed-runtime processes.
- Vol3's `malfind` includes a hex dump and a disassembly preview, which is enough to distinguish JIT prologue patterns from shellcode visually.
- Misses code that is RX-only (some attackers `VirtualProtect` from RWX to RX after writing; the moment of write is gone by the time you image).
- Misses code that is mapped from a file (process hollowing — that's why `ldrmodules` is the complementary plugin).
- `--dump` writes the suspicious region to disk for YARA scanning or further analysis.

### 7.7 `windows.dlllist`

**Purpose.** List DLLs loaded into each process via the standard loader.

**Mechanism.** For each process, walks the `_PEB_LDR_DATA.InLoadOrderModuleList` doubly-linked list of `_LDR_DATA_TABLE_ENTRY` entries.

**Output columns.** `PID`, `Process`, `Base`, `Size`, `Name`, `Path`, `LoadTime`, `File output`.

**Gotchas.**
- Only finds DLLs loaded via `LoadLibrary`/`LoadLibraryEx`. Reflectively loaded DLLs are absent.
- `LoadTime` reflects when the DLL was added to the loader list, useful for timeline reconstruction.
- A DLL with a name that mimics a system DLL but loaded from a non-standard path is suspicious (e.g., `ntdll.dll` loaded from `C:\Users\Public\`).

### 7.8 `windows.ldrmodules`

**Purpose.** Cross-reference module presence across the three loader lists and the VAD tree.

**Mechanism.** For each process, checks for each VAD that's a file mapping whether the corresponding module appears in:
- `InLoadOrderModuleList` (load order)
- `InMemoryOrderModuleList` (memory order)
- `InInitializationOrderModuleList` (init order)

**Output columns.** `PID`, `Process`, `Base`, `InLoad`, `InInit`, `InMem`, `MappedPath`, `File output`.

**Gotchas.**
- A module mapped as a section but absent from all three lists = injected via low-level techniques (manual mapping, reflective loading).
- A module in `InLoadOrderModuleList` but not in `InInitializationOrderModuleList` can be normal for DLLs that have not yet had `DllMain` called.
- A module in `InInitializationOrderModuleList` but not in `InLoadOrderModuleList` is highly anomalous (unlinking from the load list to hide).
- This is the canonical cross-check for **process hollowing detection** — the main image is in the loader list and on the VAD as a mapped file, but the actual code in memory doesn't match the mapped file (the hollowed PE was overwritten in memory).

### 7.9 `windows.handles`

**Purpose.** List open handles in each process.

**Mechanism.** Walks the kernel's handle table for each process, dereferencing each handle to its target object.

**Output columns.** `PID`, `Process`, `Offset`, `HandleValue`, `Type`, `GrantedAccess`, `Name`.

**Gotchas.**
- Handle types include `Process`, `Thread`, `File`, `Key` (registry), `Section`, `Event`, `Mutant` (mutex), `Semaphore`, `Token`, `Directory`, `SymbolicLink`, etc.
- Handles to `\Device\PhysicalMemory` or unusual `\Device\` paths are interesting (driver communication, rootkit IPC).
- Mutex names (`Mutant`) are malware fingerprints: many families use distinctive named mutexes (e.g., `\BaseNamedObjects\Global\<random>`).
- File handles to deleted files persist; the file is still allocated on disk until the handle closes.
- Cross-process handles (Process A has a handle to Process B) with `PROCESS_VM_WRITE`, `PROCESS_CREATE_THREAD`, or `PROCESS_ALL_ACCESS` are the injection prerequisites.

### 7.10 `windows.netscan`

**Purpose.** Find network endpoints by **scanning** physical memory for `TCB`, `UDA0`, `UdpA` pool tags.

**Mechanism.** Pool-tag scan for `_TCPE`, `_TCPL`, `_UDPE` endpoint structures. Parses each to extract local/remote addresses, ports, state, and owner process.

**Output columns.** `Offset`, `Proto`, `LocalAddr`, `LocalPort`, `ForeignAddr`, `ForeignPort`, `State`, `PID`, `Owner`, `Created`.

**Gotchas.**
- Finds connections that have terminated but whose endpoint structures are still in the pool. Investigators see closed connections this way.
- Owner process resolution requires the process's PID still being valid; if the process has exited, the owner may be blank or stale.
- States include `LISTENING`, `ESTABLISHED`, `CLOSE_WAIT`, `TIME_WAIT`, `FIN_WAIT_1`, `FIN_WAIT_2`, `CLOSED`. Closed/TIME_WAIT entries reflect history.
- The plugin works well across Windows 7 / 8 / 10 / 11, but the underlying pool tags have shifted across builds; some plugin versions miss edge cases on the newest kernels.

### 7.11 `windows.netstat`

**Purpose.** List network endpoints by walking authoritative kernel data structures (not pool scanning).

**Mechanism.** Walks `tcpip.sys`'s `PartitionTable` for TCP and UDP endpoints.

**Output columns.** Same shape as `netscan`.

**Gotchas.**
- Finds only currently-tracked endpoints; misses recently-closed connections that `netscan` would find.
- More authoritative than `netscan` for live state.
- Diffing `netscan` vs `netstat` is the network analog of `psscan` vs `pslist` — entries in `netscan` only = historical or hidden.

### 7.12 `windows.cmdline`

**Purpose.** Extract the command line each process was launched with.

**Mechanism.** Reads `_EPROCESS.Peb.ProcessParameters.CommandLine` (a `UNICODE_STRING`) for each process.

**Output columns.** `PID`, `Process`, `Args`.

**Gotchas.**
- Lower-PID `System`, `Registry`, `smss.exe`, and some service-host processes have null or empty command lines.
- Command lines can be tampered with by an attacker who calls `RtlInitUnicodeString` to overwrite the PEB string after process creation (technique seen in some Cobalt Strike profiles, defeats naïve telemetry).
- Long command lines (especially base64-encoded PowerShell) are immediate red flags.
- `PEB` is in user-mode memory and may be paged out; missing command lines for paged-out PEBs.

### 7.13 `windows.consoles`

**Purpose.** Recover the contents of console windows (`cmd.exe`, `powershell.exe` with `conhost.exe`).

**Mechanism.** Parses `conhost.exe` heap structures, recovering the screen buffer, history buffer, and titles.

**Output.** Console title, command history, screen buffer contents.

**Gotchas.**
- Recovers commands the user typed, including ones that have scrolled off screen.
- Recovers output the commands produced.
- Works only for consoles that are still open at the moment of acquisition.
- Newer Windows Terminal (`WindowsTerminal.exe`) uses a different architecture (`OpenConsole.exe` as the pty host); plugin coverage for newer terminal hosts is less complete.

### 7.14 `windows.cmdscan`

**Purpose.** Scan for `COMMAND_HISTORY` structures regardless of process linkage.

**Mechanism.** Scans `conhost.exe` (and historically `csrss.exe`) memory for command history records.

**Output.** Same shape as `consoles` history but found via signature scanning.

**Gotchas.**
- Complements `consoles`: finds history fragments in conhost instances that may have been closed but not yet had their heap reclaimed.
- Can find command lines from previously-exited cmd.exe sessions still resident in conhost heap.

### 7.15 `windows.svcscan`

**Purpose.** List Windows services.

**Mechanism.** Scans `services.exe` memory for `_SERVICE_RECORD` structures.

**Output columns.** `Offset`, `Order`, `PID`, `Start`, `State`, `Type`, `Name`, `Display`, `Binary`.

**Gotchas.**
- Reveals services configured to start (regardless of whether running) and their binary paths.
- Newly-registered malicious services (a common persistence vector) appear here.
- `Type` field distinguishes user-mode services, kernel drivers, file-system drivers, interactive services.
- The `Binary` field gives the executable path or command line; `svchost.exe -k <group>` indicates a shared-service host.

### 7.16 `windows.registry.hivelist`

**Purpose.** List loaded registry hives.

**Mechanism.** Walks the kernel's `CmpHiveListHead` list of `_CMHIVE` structures.

**Output columns.** `Offset`, `FileFullPath`, `FileName`, `HiveOffset`.

**Gotchas.**
- Hives include `SYSTEM`, `SOFTWARE`, `SAM`, `SECURITY`, `DEFAULT`, plus a `NTUSER.DAT` per loaded user profile.
- `\REGISTRY\MACHINE\SYSTEM` etc. are the kernel's view; `FileFullPath` shows the underlying file path on disk.
- The hive offset is the input to `printkey`, `userassist`, and similar registry plugins.

### 7.17 `windows.registry.printkey`

**Purpose.** Print a registry key's values from memory.

**Mechanism.** Walks the hive's key tree to find the specified key, then enumerates its values.

**Output columns.** `Hive Offset`, `Key`, `Last Write Time`, `Name`, `Type`, `Data`, `Volatile`.

**Gotchas.**
- Works against the in-memory hive, which may have more recent changes than the on-disk hive (registry writes are buffered).
- Volatile keys (`Volatile == True`) exist only in memory and never hit disk — important for transient session data.
- `LastWriteTime` is per-key (not per-value); useful for timelining.

### 7.18 `windows.registry.userassist`

**Purpose.** Decode the `UserAssist` registry keys recording GUI program executions.

**Mechanism.** Reads `NTUSER.DAT\Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist\<GUID>\Count` values, ROT13-decodes the value names, and parses the `_UEME_RUNPATH` structures.

**Output.** Program path, execution count, focus count, focus time, last execution time.

**Gotchas.**
- Memory copy of UserAssist may be more current than the on-disk hive.
- Records only GUI-launched programs (typically things started via Explorer); CLI-launched programs are not here.

### 7.19 `windows.modules`

**Purpose.** List loaded kernel-mode drivers.

**Mechanism.** Walks `PsLoadedModuleList` of `_KLDR_DATA_TABLE_ENTRY` structures.

**Output columns.** `Offset`, `Base`, `Size`, `Name`, `Path`, `File output`.

**Gotchas.**
- Drivers loaded via the standard loader appear here.
- Rootkit drivers that unlink from `PsLoadedModuleList` are absent — use `modscan`.
- `Path` is the on-disk path the driver was loaded from; comparing to expected paths reveals dropped drivers in suspicious locations.

### 7.20 `windows.modscan`

**Purpose.** Scan physical memory for kernel driver structures (the `modules`/`psscan` analog).

**Mechanism.** Pool-tag scan for `MmLd` (`_KLDR_DATA_TABLE_ENTRY` pool tag).

**Output columns.** Same as `modules`.

**Gotchas.**
- Finds unlinked drivers (rootkit hiding).
- The diff between `modules` and `modscan` is the kernel-side equivalent of the `pslist`/`psscan` diff.

### 7.21 `windows.driverscan`

**Purpose.** Scan for `_DRIVER_OBJECT` structures.

**Mechanism.** Pool-tag scan for `Driv` (`_DRIVER_OBJECT` pool tag).

**Output columns.** `Offset(P)`, `Start`, `Size`, `ServiceKey`, `Name`, `DriverName`.

**Gotchas.**
- Each driver object has a `DriverObject->FastIoDispatch` and `DriverObject->MajorFunction[28]` array — these are the IRP handler pointers and the targets of `driverirp` hooks.
- A driver object's `DeviceObject` chain shows the device stack — useful for filter driver analysis.

### 7.22 `windows.ssdt`

**Purpose.** Dump the System Service Descriptor Table.

**Mechanism.** Reads `KeServiceDescriptorTable` and resolves each entry to a function symbol.

**Output columns.** `Index`, `Address`, `Module`, `Symbol`.

**Gotchas.**
- On modern x64 Windows, SSDT hooking is largely mitigated by **PatchGuard** (Kernel Patch Protection). Most SSDT hooks are now infeasible on production kernels.
- Still useful on x86 systems and as a baseline check.
- Entries should resolve to `ntoskrnl.exe` or `win32k.sys`. Anything else (e.g., entries pointing to addresses in an unknown driver) is a hook.

### 7.23 `windows.callbacks`

**Purpose.** List kernel callback registrations.

**Mechanism.** Walks `PsSetCreateProcessNotifyRoutine`, `PsSetCreateThreadNotifyRoutine`, `PsSetLoadImageNotifyRoutine`, `CmRegisterCallback`, `IoRegisterShutdownNotification`, `KeBugCheckCallbackListHead`, and several others.

**Output columns.** `Type`, `Callback`, `Module`, `Detail`.

**Gotchas.**
- Legitimate AV/EDR products register callbacks. Defender, CrowdStrike, SentinelOne, Sophos, Carbon Black, etc., all show up here. This is expected.
- Suspicious callbacks: those pointing to unknown drivers or to addresses with no associated module.
- Rootkits that install callbacks to intercept process creation / image loading appear here unless they unlink themselves from the callback array (some advanced rootkits do).

### 7.24 `windows.driverirp`

**Purpose.** Dump the IRP (I/O Request Packet) major function table for each driver.

**Mechanism.** For each driver object, lists the 28 `MajorFunction` entries.

**Output columns.** `Driver`, `Index`, `Function Name`, `Address`, `Module`.

**Gotchas.**
- Each major function should point into the driver's own image. A `MajorFunction[IRP_MJ_READ]` for `Ntfs.sys` pointing into an unknown module = filter driver or rootkit IRP hook.
- Legitimate filter drivers (file system filters, network filters) hook IRPs as part of their normal operation. Distinguishing requires knowing what's expected.

### 7.25 `windows.dumpfiles`

**Purpose.** Extract files from memory.

**Mechanism.** Reads `_FILE_OBJECT` structures and their associated `_SECTION_OBJECT_POINTERS` (DataSectionObject, SharedCacheMap, ImageSectionObject) to recover the file contents from the cache manager and section objects.

**Output.** Files written to the output directory. Naming: `file.<offset>.dat`, `file.<offset>.img`, etc., based on which section pointer was used.

**Gotchas.**
- Recovers file contents that are mapped or cached. Not all bytes are guaranteed (sparse caching).
- Multiple files may be extracted per `_FILE_OBJECT` reflecting different views (Data, Image, Cache).
- Useful for: recovering deleted-but-still-open files, recovering executables that were loaded but the on-disk copy was wiped, getting at content for static analysis after dumping.
- Filter by PID with `--pid` or by physical offset.

### 7.26 `windows.memmap`

**Purpose.** Print the virtual-to-physical mappings for a process (or the kernel).

**Mechanism.** Walks the page tables for the specified DTB and emits every mapped page.

**Output columns.** `Virtual`, `Physical`, `Size`, `Offset in File`.

**Gotchas.**
- Very verbose for a process with a large address space.
- Useful for understanding fragmentation, paged-out content, and shared mappings.
- `windows.memmap.Memmap --dump --pid <pid>` writes the full process address space to a file — essentially a per-process memory dump.

### 7.27 `windows.vadinfo`

**Purpose.** Display the VAD (Virtual Address Descriptor) tree for each process.

**Mechanism.** Walks the AVL tree rooted at `_EPROCESS.VadRoot`, emitting one row per VAD.

**Output columns.** `PID`, `Process`, `Offset`, `Start VPN`, `End VPN`, `Tag`, `Protection`, `CommitCharge`, `PrivateMemory`, `File`.

**Gotchas.**
- The VAD tree is how Windows tracks virtual memory allocations. Each VAD represents a contiguous range of virtual pages with the same backing (file mapping or private) and same protection.
- `Tag` is the VAD pool tag: `VadS` (short VAD, common), `Vadl` (long VAD), `Vadm` (memory-mapped file).
- `Protection`: `PAGE_NOACCESS`, `PAGE_READONLY`, `PAGE_READWRITE`, `PAGE_EXECUTE`, `PAGE_EXECUTE_READ`, `PAGE_EXECUTE_READWRITE` (RWX), `PAGE_EXECUTE_WRITECOPY`, `PAGE_GUARD`, `PAGE_NOCACHE`, `PAGE_WRITECOMBINE`.
- `PrivateMemory == True` and `File == None` and `Protection` contains EXECUTE = shellcode candidate (this is `malfind`'s heuristic).
- The VAD's `File` field contains the mapped file path for file-backed VADs.

### 7.28 `windows.vadwalk`

**Purpose.** Walk the VAD tree structurally (parent, left, right links) to verify integrity.

**Mechanism.** AVL tree walk.

**Output columns.** Tree structure with parent/child relationships.

**Gotchas.**
- Used for low-level VAD analysis when integrity is in question.
- Less commonly run during triage.

### 7.29 `windows.vaddump`

**Purpose.** Dump VAD contents to disk.

**Mechanism.** For specified VADs (filtered by PID, address, protection), writes the bytes to disk.

**Output.** Files named per VAD: `pid.<pid>.vad.<start>-<end>.dmp`.

**Gotchas.**
- Use to extract suspicious VADs for YARA / disassembly / submission to sandboxes.
- Combine with `malfind`'s `--dump` for the same effect.

### 7.30 `windows.lsadump`

**Purpose.** Extract LSA secrets from memory.

**Mechanism.** Uses the `SYSTEM` hive's `PolicySecrets` and the encrypted LSA secrets in the `SECURITY` hive. Decrypts using the SysKey derived from `SYSTEM` hive's `LSA\Data`.

**Output.** Secret name (e.g., `$MACHINE.ACC`, `DPAPI_SYSTEM`, `NL$KM`, `_SC_<service>`, `DefaultPassword`), hex/printable decrypted content.

**Gotchas.**
- `DefaultPassword` may contain auto-logon plaintext credentials.
- `$MACHINE.ACC` is the machine account password hash (NTLM).
- `_SC_<service>` contains the password for services configured with non-default credentials.
- Requires both `SYSTEM` and `SECURITY` hives present (they are, by default).
- VBS / Credential Guard does not protect LSA secrets the same way it protects LSASS; lsadump output is generally intact even on Credential Guard systems.

### 7.31 `windows.hashdump`

**Purpose.** Extract NTLM password hashes from the SAM hive.

**Mechanism.** Reads SAM hive's user accounts (`SAM\Domains\Account\Users\<RID>`), pulls the `V` value (encrypted hashes), decrypts using the BootKey from the SYSTEM hive.

**Output.** `user:rid:LM_hash:NT_hash:::` format (the classic hashdump output).

**Gotchas.**
- Local SAM accounts only (machine-local users). Domain credentials are not in SAM.
- `LM_hash` is empty/`aad3b435b51404eeaad3b435b51404ee` on modern Windows (LM disabled).
- Hashes are crackable offline. NT hashes are MD4(unicode_password); modern attacks (rainbow tables, hashcat with GPU) crack short passwords trivially.

### 7.32 `windows.cachedump`

**Purpose.** Extract cached domain credentials (MSCache, MSCACHEv2).

**Mechanism.** Reads `SECURITY\Cache` entries.

**Output.** Username, domain, MSCACHEv2 hash.

**Gotchas.**
- These are the credentials cached for domain users so they can log on when the DC is unreachable. By default 10 cached entries.
- MSCACHEv2 is much slower to crack than NTLM (10240 PBKDF2 iterations + DCC2 algorithm).
- Useful for identifying which domain users have authenticated to this machine.

### 7.33 `windows.mbrscan`

**Purpose.** Find Master Boot Record / Boot Sector structures in memory.

**Mechanism.** Scans for signature `0x55AA` at offset 510 of 512-byte aligned chunks; further validates partition table structure.

**Output.** Offsets of MBR-like structures.

**Gotchas.**
- Used for bootkit analysis. Some bootkits modify the MBR or VBR; the memory copy may differ from the disk copy.
- Diffing memory MBR vs disk MBR reveals runtime modifications.

### 7.34 `windows.mftscan`

**Purpose.** Find NTFS Master File Table records in memory.

**Mechanism.** Scans for `FILE0` or `BAAD` signatures of MFT entries.

**Output.** MFT entry contents (file name, timestamps, file attributes, $DATA contents for resident files).

**Gotchas.**
- Cached MFT entries appear in memory because the cache manager keeps recently-accessed MFT records.
- Resident files (small files stored entirely within the MFT entry) can be recovered fully.
- Provides a window into recent file system activity even when disk imaging is not immediately available.

### 7.35 `windows.envars`

**Purpose.** Extract environment variables for each process.

**Mechanism.** Reads `_RTL_USER_PROCESS_PARAMETERS.Environment` for each process.

**Output columns.** `PID`, `Process`, `Block`, `Variable`, `Value`.

**Gotchas.**
- Useful for spotting:
  - `PATH` modifications (a malicious process prepending an attacker-controlled directory).
  - Custom variables that malware uses to pass state.
  - Auto-set variables like `TEMP`, `APPDATA`, `USERPROFILE` indicating which user account the process belongs to.

### 7.36 `windows.getservicesids`

**Purpose.** Compute the SID for each service.

**Mechanism.** Hashes service names per Microsoft's service-SID algorithm (SHA1 of UPPERCASE(service name)) to produce `S-1-5-80-...`.

**Output.** Service name, computed SID.

**Gotchas.**
- Used to map handle/token entries that reference service SIDs back to service names.

### 7.37 `windows.privileges`

**Purpose.** List token privileges for each process.

**Mechanism.** Walks `_EPROCESS.Token` to find `_TOKEN.Privileges` and decodes the enabled/disabled state of each privilege.

**Output columns.** `PID`, `Process`, `Value`, `Privilege`, `Attributes`, `Description`.

**Gotchas.**
- `SeDebugPrivilege` enabled on a non-SYSTEM, non-admin process is a strong indicator of privilege escalation.
- `SeTcbPrivilege`, `SeImpersonatePrivilege`, `SeAssignPrimaryTokenPrivilege` are interesting when enabled on unexpected processes.
- Token tampering by malware (modifying privileges in-place rather than using `AdjustTokenPrivileges`) leaves the kernel structures inconsistent with what the API would have logged.

### 7.38 `windows.skeleton_key_check`

**Purpose.** Detect the "skeleton key" attack on domain controllers.

**Mechanism.** Looks for `cryptdll.dll` modifications in `lsass.exe`, specifically for hooks at the location where Kerberos preauthentication is validated. The skeleton key technique modifies these functions to accept a known attacker password in addition to the correct one.

**Output.** Indication of skeleton key presence in `lsass.exe`.

**Gotchas.**
- Only relevant on domain controllers.
- Skeleton key implantation requires DC-local code execution; if you suspect DC compromise, this is one of the targeted plugins.

### 7.39 `windows.suspended_threads`

**Purpose.** List threads in suspended state.

**Mechanism.** Walks threads, checks `_KTHREAD.SuspendCount > 0`.

**Output columns.** `PID`, `Process`, `TID`, `SuspendCount`, `CreateTime`.

**Gotchas.**
- Process hollowing creates a process in suspended state, replaces its image, then resumes the main thread. At the moment of acquisition, if the resume hasn't happened, the main thread is suspended.
- Legitimate suspended-thread patterns exist (debuggers, certain runtime hooks).

### 7.40 `yarascan`

**Purpose.** Run YARA rules against memory.

**Mechanism.** Scans either the kernel address space or each process's address space (configurable) and applies a YARA rule set to the bytes.

**Output columns.** `Offset`, `Rule`, `Component`, `Value` (hex/preview).

**Gotchas.**
- Default scan is kernel address space; use `--pid` to scan a specific process or `--processes` to scan all processes.
- `--yara-file <path>` to specify rule file; `--yara-rules <inline>` for short inline rules.
- Pre-built rule sets: Florian Roth's `signature-base`, YARA-Forge, ReversingLabs YARA rules, Volatility's bundled rules.
- Memory scanning catches in-memory-only signatures: decoded shellcode, decrypted strings, runtime config blobs.
- False positives are common with permissive rules; tune rule quality.

### 7.41 `windows.dumpfiles` and process image extraction

To extract a suspect process's image for static analysis:

- `windows.pslist --pid <pid> --dump` writes the process executable image.
- `windows.dlllist --pid <pid> --dump` writes each loaded DLL.
- `windows.memmap --pid <pid> --dump` writes the entire process address space.
- `windows.vaddump --pid <pid>` writes each VAD individually.

The extracted PE may be incomplete (relocations applied, IAT resolved, sections zero-padded where pages weren't mapped). Tools like `pe-sieve`, `Hollows Hunter`, and Volatility's `procdump` plugin (Vol2) try harder to reconstruct a usable binary.

---

## 8. Plugin catalog — Linux

Vol3's Linux support has parity gaps with Windows but covers the essentials. Plugins require a kernel symbol table (ISF generated from `vmlinux` + DWARF debugging info or from `System.map` + a parsed `dwarf2json` output).

### 8.1 `linux.pslist`

**Purpose.** List processes by walking the kernel's `init_task` `tasks` list.

**Mechanism.** Starts at `init_task`, walks `task_struct.tasks` doubly-linked list.

**Output columns.** `OFFSET (V)`, `PID`, `TID`, `PPID`, `COMM`, `EUID`.

**Gotchas.**
- Linux equivalent of Windows `pslist`.
- `COMM` is `task_struct.comm[16]` — truncated to 16 bytes.
- `EUID == 0` is root.

### 8.2 `linux.psscan`

**Purpose.** Scan for `task_struct` structures.

**Mechanism.** Heuristic scan for `task_struct` patterns in memory.

**Output columns.** Same as `pslist`.

**Gotchas.**
- Finds processes unlinked from the task list.
- The Linux task list is doubly-linked and easy to unlink in-place; rootkits like Diamorphine demonstrate the technique.

### 8.3 `linux.pstree`

**Purpose.** Process tree, like Windows version.

### 8.4 `linux.lsof`

**Purpose.** List open file descriptors per process.

**Mechanism.** Walks `task_struct.files->fdt->fd[]` array.

**Output columns.** `PID`, `Process`, `FD`, `Path`.

**Gotchas.**
- Reveals open files, sockets (with `socket:[inode]`-style names), pipes, deleted-but-still-open files.

### 8.5 `linux.bash`

**Purpose.** Recover bash command history from memory.

**Mechanism.** Scans `bash` process heap for history list entries.

**Output columns.** `PID`, `Process`, `CommandTime`, `Command`.

**Gotchas.**
- Recovers commands typed in bash sessions even if `~/.bash_history` hasn't been flushed or was deleted.
- Each entry has a timestamp (bash records `HISTTIMEFORMAT`).
- Equivalent for `zsh` is missing; recent community work on zsh memory parsing exists but is less mature.

### 8.6 `linux.malfind`

**Purpose.** Linux equivalent of Windows `malfind` — find suspicious memory regions.

**Mechanism.** Walks each process's VMA list (`mm_struct.mmap`), flags `VM_EXEC + VM_WRITE` private mappings without backing file.

**Output columns.** `PID`, `Process`, `Start`, `End`, `Path`, `Protection`, `Hexdump`.

**Gotchas.**
- Catches injected code in Linux processes (shellcode, runtime patches).
- False positives from JIT engines (V8, JVM, .NET on Linux).

### 8.7 `linux.check_modules`

**Purpose.** Cross-check kernel module lists for hidden modules.

**Mechanism.** Compares `modules` linked list (`module.list`) with the `/sys/module` representation and other module-tracking structures.

**Output.** Modules found in one structure but not another.

**Gotchas.**
- Diamorphine-style rootkits unlink their `module` from `modules` to hide; cross-reference reveals them.

### 8.8 `linux.lsmod`

**Purpose.** List loaded kernel modules from the `modules` list.

### 8.9 `linux.check_syscall`

**Purpose.** Check syscall table for hooks.

**Mechanism.** Walks `sys_call_table[]` and resolves each entry against expected kernel symbol.

**Output.** Syscall index, expected symbol, actual address, hook status.

**Gotchas.**
- Linux equivalent of Windows `ssdt`. Syscall hooking is a classic Linux rootkit technique.

### 8.10 `linux.check_creds`

**Purpose.** Find processes sharing `cred` structures (a sign of credential theft / privilege escalation).

**Mechanism.** Walks all processes, groups by `cred` pointer.

**Output.** Groups of PIDs sharing the same `cred`.

**Gotchas.**
- Legitimately, child processes share `cred` until they call `setuid`/`setgid`. Sharing across unrelated processes is suspicious.

### 8.11 `linux.envars`

**Purpose.** Environment variables for each process.

### 8.12 `linux.proc.Maps`

**Purpose.** Per-process memory maps (`/proc/<pid>/maps` equivalent).

### 8.13 `linux.sockstat`

**Purpose.** Open sockets and their bindings.

### 8.14 Plugin coverage gap

Vol3's Linux plugin set is meaningfully smaller than Windows. Many Vol2 Linux plugins (e.g., `linux_dynamic_env`, `linux_route_cache`, `linux_arp`, `linux_iomem`, `linux_check_idt`, `linux_check_inline_kernel`) have not been fully ported. For sophisticated Linux rootkit analysis, the practical move is either:

- Use Vol2 with a community Linux profile.
- Use `MemProcFS` with Linux support.
- Drop into `volshell` and write the analysis by hand against the kernel symbol table.

---

## 9. Common failure modes

Memory analysis fails in characteristic ways. Knowing these failure modes lets the analyst (or any downstream system) distinguish "the dump is broken" from "the plugin found nothing interesting".

### 9.1 OS misdetection

Rare with Vol3's symbol cache. The automagic stack normally finds the kernel image, fetches the right ISF, and proceeds. Where it does fail:

- **Hibernation files with the kernel image paged out.** The PDB signature scan fails because the kernel image isn't in the dump.
- **Partial dumps that omitted kernel pages.** Crash dumps that were truncated mid-write may have non-kernel content with a valid `DUMP_HEADER` but no kernel image.
- **Corrupted or zeroed file headers.** Acquisition tool failures that wrote zero pages where header bytes should be.

Diagnostic: `windows.info` errors with "Unable to find a suitable kernel image" or "Unable to validate the location of the kernel directory table base."

### 9.2 KASLR and PageHeap interactions

**Kernel Address Space Layout Randomization (KASLR)** in Windows means the kernel base address changes per boot. Vol3 finds the kernel base via PDB scanning regardless of slide.

**PageHeap** is a Windows debugging feature that places guard pages around allocations. PageHeap-enabled processes have unusual VAD layouts and may produce confusing `malfind` output (large numbers of `PAGE_NOACCESS` guard pages between normal allocations).

Neither breaks Vol3, but both can produce surprising output.

### 9.3 Paged-out content

When Vol3 walks a structure and the page is paged out (the kernel had decided this page belongs in `pagefile.sys`), the read fails. Common results:

- `cmdline`: empty command line for some processes whose PEB is paged out.
- `dlllist`: missing DLL entries when the `_LDR_DATA_TABLE_ENTRY` is paged out.
- `dumpfiles`: incomplete files.

Mitigations:
- Acquire the page file (`pagefile.sys`, `swapfile.sys`) alongside the memory dump.
- Use `--swap-locations <file>` to point Vol3 at the swap file.
- Accept partial output.

### 9.4 Encrypted hibernation

`hiberfil.sys` on Windows 10/11 may be encrypted (depending on BitLocker and Hibernate-related policies). Without the decryption key, the file is opaque. Symptoms: `hibr2bin` fails or produces garbage; Vol3 cannot stack a layer atop it.

### 9.5 Windows 11 Memory Compression Store

Starting in Windows 10 and continuing in Windows 11, the OS implements **memory compression**: a kernel component compresses cold pages and stores them in a special process (`MemCompression` / `Memory Compression`) rather than paging them out. This is highly effective for system performance but creates a forensic challenge:

- Compressed pages are not directly readable as their original content.
- The compression algorithm is Xpress, with a per-region key stored in kernel data.
- Vol3 must decompress on demand when a read targets a compressed page.

Vol3's handling has matured over time. Current versions (3.x) include a `Windows 10 memory compression layer` (also referred to as `MemCompression` decompression) that recognizes when a page has been compressed and decompresses transparently. Older Vol3 versions and pre-2020 community work did not handle this, leading to apparent gaps in process address spaces.

The diagnostic indicator: `pslist` shows a `MemCompression` process (or `Memory Compression`, depending on Windows build). Its presence indicates the compression mechanism is active, and Vol3 needs to handle it.

### 9.6 Smeared dumps

Discussed in §2.9. The most common smear symptoms during analysis:

- `pslist` and `psscan` show different counts that change between runs (shouldn't happen for a static file, but smear can produce intermittent parse errors).
- Handle table dereferences fail with "invalid object" messages.
- Network connection state inconsistent with the process owner.
- Cross-process handles point to PIDs that don't exist in the dump.

There is no fix for smear post-hoc; the dump is what it is.

### 9.7 ISF mismatch

If the analyst supplies a wrong ISF (e.g., a manually-built ISF for a similar but not identical kernel build), structure offsets are slightly off. Symptoms:

- `pslist` parses but `ImageFileName` shows garbage.
- `cmdline` produces nonsense Unicode.
- `dlllist` shows DLL bases at impossible addresses.

The fix: re-run with the correct ISF, or let Vol3 fetch it.

### 9.8 Driver-modified kernel structures

Some EDR products and some rootkits modify kernel structures in-place (e.g., overwriting function pointers, padding fields). Vol3 reads what's there; if a rootkit has corrupted a structure to evade detection, the plugin output reflects the corruption, not the original.

This is rarely "Vol3 is broken" — it's "the attacker tampered with the data". Cross-checking multiple plugins that derive the same information from different sources (`pslist` vs `psscan` vs `psxview`) is the way to detect this.

---

## 10. Memory artifact patterns

This section maps known attacker techniques to the memory signatures they leave. The goal is recognition: when you see signature X, technique Y is in play.

### 10.1 DKOM rootkit

**Technique.** Direct Kernel Object Manipulation. Attacker unlinks `_EPROCESS` from `PsActiveProcessHead` to hide a process, or unlinks `_KLDR_DATA_TABLE_ENTRY` from `PsLoadedModuleList` to hide a driver.

**Memory signature.**
- `pslist` does not show the process; `psscan` does.
- Similarly for `modules` vs `modscan`.
- `psxview` flags discrepancy: process is in `psscan`, `thrdproc`, `pspcid` but not `pslist`.
- The hidden process's threads still exist and still execute (the kernel scheduler uses thread structures, not the process list, for scheduling).

**Disambiguators.**
- Legitimate terminated-but-pool-resident processes appear in `psscan` and not `pslist`. These have `ExitTime` set. Hidden processes have `ExitTime` empty and active threads.

### 10.2 Process hollowing

**Technique.** Spawn a legitimate process suspended, unmap its primary image, allocate replacement memory, write malicious PE into it, set EIP/RIP to the new entry point, resume the main thread.

**Memory signature.**
- `pslist` shows the process with its legitimate image name (e.g., `svchost.exe`).
- `dlllist` shows the main module entry — but the module is no longer mapped from the file; it's private memory or section-mapped from a non-file backing.
- `ldrmodules` flags the main module: it's in the loader list but the associated VAD is private (not file-backed) OR the file path doesn't match the loader entry.
- `malfind` may flag the main image VAD as RWX private (depending on the hollowing variant).
- `vadinfo` shows the main image VAD with `PrivateMemory == True` and `File == None`, which is anomalous for a primary image.
- `dumpfiles` on the process image yields the legitimate `svchost.exe` from disk (because the kernel still maps the section object for the file), but `vaddump` of the actual loaded region yields the malicious code.

### 10.3 Process doppelgänging

**Technique.** Use NTFS transactions: create a transaction, write malicious PE to a file inside the transaction, create a section from the transacted file, rollback the transaction. The section persists in memory but the file content was rolled back.

**Memory signature.**
- Process exists in `pslist`.
- The main image VAD is mapped from a section whose `_SECTION_OBJECT.Segment.ControlArea.FilePointer` references a file that, on disk, has different content than what is in memory.
- `dumpfiles` reads the on-disk file (legitimate content) vs `vaddump` (malicious content) — these differ.
- File on disk may not even exist if the transaction was fully aborted.

### 10.4 Process Herpaderping

**Technique.** Write malicious PE to disk → create section from file → overwrite file on disk with benign content → CreateProcess from file. The section was bound while content was malicious; the file as scanned by AV is benign.

**Memory signature.**
- Process exists normally in `pslist`.
- The on-disk image at the file path is benign or different from the executed code.
- `vaddump` of the main image VAD yields the malicious PE.
- File hash on disk (e.g., `Get-FileHash` of the image path) does not match the in-memory PE.

### 10.5 Process Ghosting

**Technique.** Create a file → open delete-pending → write malicious PE → create section from the delete-pending file → close handle (file is deleted) → create process from the now-deleted section. The file never existed in a discoverable state.

**Memory signature.**
- Process exists in `pslist`.
- The main image's `_FILE_OBJECT.FileName` may be null or point to a deleted file.
- On-disk image is not present.
- `vaddump` recovers the malicious PE.

### 10.6 Classic DLL injection (CreateRemoteThread + LoadLibrary)

**Technique.** Open target process, allocate memory in it, write the DLL path as a string, create a remote thread starting at `LoadLibraryA` with the path as argument.

**Memory signature.**
- The DLL appears in `dlllist` of the target process (because it was loaded via the standard loader).
- `ldrmodules` shows it in all three loader lists (legitimate-looking).
- The DLL's path is on disk and matches what's loaded.
- The detection vector: the DLL is in an unexpected process (e.g., `windefend.dll` in a non-Defender context, or a random DLL loaded into `notepad.exe`).
- Process handle list (`handles --type Process`) on the injecting process shows a handle to the target with `PROCESS_VM_WRITE | PROCESS_CREATE_THREAD`.

### 10.7 Reflective DLL load

**Technique.** Allocate memory in target process, write the entire DLL (PE format) into it, call a custom `ReflectiveLoader` function inside the DLL that performs the loading itself: parsing its own PE headers, relocating, resolving imports.

**Memory signature.**
- The DLL is **not** in `dlllist` (never went through `LoadLibrary`).
- `ldrmodules` shows nothing for the region.
- `malfind` flags the region: private memory, RWX or RX, containing PE header bytes (`MZ` at the start, `PE\0\0` later).
- `yarascan` with a reflective-loader-shape rule (looking for the prologue patterns) catches it.

### 10.8 APC injection

**Technique.** Queue an Asynchronous Procedure Call to a thread in the target process. When the thread enters an alertable state, the APC runs, calling attacker code.

**Memory signature.**
- The APC queue (`_KTHREAD.ApcState`) of a target thread contains an APC pointing to attacker code.
- Vol3 does not have a high-level "list pending APCs" plugin out of the box, but `volshell` can walk thread structures.
- Side effects: the injected code (often shellcode) sits in private memory in the target process, where `malfind` can find it.

### 10.9 Atom bombing

**Technique.** Use global atom tables (`AddAtomA` / `FindAtomA`) to plant strings, then use `NtQueueApcThread` and `GlobalGetAtomName` to write attacker data into a target process and trigger its execution via ROP.

**Memory signature.**
- Suspicious atom table entries (queryable via `volshell`).
- Injected code visible in target process VADs.
- Now mitigated by **AppContainer** and modern process hardening; rarely seen in 2026 intrusions but still in some malware family lineages.

### 10.10 PROPagate

**Technique.** Use `SetWindowSubclass` on a window in another process to hijack its message handler.

**Memory signature.**
- `win32k.sys` data structures showing window procedures pointing at attacker code.
- Requires deep GUI subsystem analysis; not covered by a standard Vol3 plugin.

### 10.11 Token impersonation

**Technique.** Steal an access token from a higher-privileged process and use it (`OpenProcessToken` + `DuplicateTokenEx` + `ImpersonateLoggedOnUser`, or `SeImpersonatePrivilege`-based moves like JuicyPotato/RoguePotato variants).

**Memory signature.**
- `privileges` plugin shows unexpected privilege sets on processes that should not have them.
- `getservicesids` correlation: a process token referencing a service SID that doesn't match the process's own service.
- `_EPROCESS.Token` vs `_ETHREAD.ClientSecurityContext` differing — a thread is impersonating something other than the process token.
- Token `_SEP_TOKEN_PRIVILEGES.Enabled` flags showing privileges that have never been audited as being granted (no 4672 event).

### 10.12 SeDebugPrivilege grants

**Technique.** A process holding `SeDebugPrivilege` can open any other process with full access and inject code into it.

**Memory signature.**
- `privileges --pid <pid>` shows `SeDebugPrivilege` as `Present | Enabled`.
- Legitimately held by: Local System processes, processes started by users in the local Debuggers group, certain admin tools (Process Explorer when elevated, debuggers, etc.).
- Anomaly: `SeDebugPrivilege` enabled on a process running as a low-privilege user.

### 10.13 LSASS access

**Technique.** Read `lsass.exe` memory (via `MiniDumpWriteDump`, `OpenProcess + ReadProcessMemory`, or `comsvcs.dll MiniDump`) to extract credentials.

**Memory signature.**
- `handles` plugin: a non-system process holding a handle to `lsass.exe` with `PROCESS_VM_READ` access.
- `lsadump` shows secrets; combined with foreign-process handle, you have both the action and the artifact.
- LSASS itself may show injected DLLs (`dlllist --pid <lsass_pid>`) if the credential theft was implemented as an injected harvester.

### 10.14 Pass-the-hash / pass-the-ticket residue

**Technique.** Use stolen NTLM hash or Kerberos ticket to authenticate as another user without knowing the password.

**Memory signature.**
- `lsadump` / `hashdump` recovers hashes that were used.
- `_LOGON_SESSION` structures in `lsass.exe` show logon types and authentication packages used.
- Kerberos ticket structures in `lsass` heap can be parsed by `mimikatz`-style tooling; Volatility's coverage of Kerberos in-memory tickets is partial.

### 10.15 Keylogger

**Technique.** Install a Windows hook (`SetWindowsHookEx WH_KEYBOARD_LL`) that intercepts keystrokes, log them to a buffer or file.

**Memory signature.**
- The hook handler DLL is mapped into every process that receives input messages — visible in `dlllist` for many processes.
- `csrss.exe` and `winlogon.exe` may show unexpected DLLs loaded.
- Low-level hooks specifically run in the hooking process, so the hook target is queryable from `win32k.sys` structures.

### 10.16 Cobalt Strike beacon

**Technique.** Memory-resident C2 implant.

**Memory signature.**
- Private RWX VAD in a benign-named process (often `svchost.exe`, `rundll32.exe`, `werfault.exe`).
- VAD size typically several hundred KB.
- Contains beacon configuration block: encrypted with one-byte XOR or 4-byte XOR. Public decoders (`1768.py` from Didier Stevens, `parse_config.py` from Sentinel One) extract C2 URLs, sleep times, jitter.
- YARA rules from the community (Florian Roth, Elastic, JPCERT) catch beacon patterns reliably.
- Named pipes (`\\.\pipe\msagent_*`, `\\.\pipe\status_*`, etc., depending on profile) visible in `handles --type File`.

### 10.17 Mimikatz residue

**Technique.** Run mimikatz to extract credentials.

**Memory signature.**
- `mimikatz.exe` in `pslist` (rare — usually run from another tool's context).
- `lsass.exe` has been opened with `PROCESS_VM_READ` (visible in `handles` of mimikatz or its host).
- Specific DLL loads in `lsass.exe` if mimikatz used `MISC::Skeleton` or other in-process modifications.
- `cmdline` for the parent process may show mimikatz commands if the parent was `cmd.exe`.
- Mimikatz strings in memory: `mimikatz`, `sekurlsa`, `kerberos::list`, etc. — `yarascan` with mimikatz-string rules catches even renamed builds.

### 10.18 Living-off-the-land processes

**Pattern.** Processes like `powershell.exe`, `cmd.exe`, `wmic.exe`, `rundll32.exe`, `regsvr32.exe`, `mshta.exe`, `installutil.exe`, `msbuild.exe` running with suspicious command lines.

**Memory signature.**
- `cmdline` shows the suspect command line.
- `consoles` recovers what the user/attacker typed.
- `cmdscan` recovers historical commands from closed conhost instances.
- The PE on disk is signed Microsoft — disk-side detection is hard. Command-line analysis is the high-yield path.

---

## 11. Standard memory triage chain

A canonical order in which Volatility plugins are run during early IR triage, with what each step rules in or out. This is descriptive (what investigators actually do) not prescriptive.

### Step 1: `windows.info`

Confirms the dump is valid and identifies the OS. Without this, nothing else works.

### Step 2: `windows.pslist`

First look at the process tree. Establishes the baseline of what was running.

### Step 3: `windows.psscan`

Find anything hidden or terminated-but-pool-resident. Diff against `pslist`.

### Step 4: `windows.pstree`

Visualize parent-child relationships. Look for:
- Suspicious child processes of `winword.exe`, `excel.exe`, `outlook.exe`, browser processes (initial access payloads).
- `cmd.exe` / `powershell.exe` children of unexpected parents.
- Processes whose parent has long exited (PID 0 or stale parent).
- Processes claiming to be system services but launched from user contexts.

### Step 5: `windows.cmdline`

Read command lines. Look for:
- Base64-encoded PowerShell (`-EncodedCommand`, `-enc`).
- Unusual command-line flags (`-WindowStyle Hidden`, `-NoProfile`, `-ExecutionPolicy Bypass`).
- Long obfuscated command strings.
- Commands invoking known LOLBins with suspicious arguments.

### Step 6: `windows.netscan`

Open and recently-closed network connections. Look for:
- Connections to external IPs from unexpected processes.
- High-numbered ephemeral ports listening on internal-facing processes.
- Connections to known-malicious IPs/domains (cross-reference with threat intel).
- Listening services that shouldn't be listening.

### Step 7: `windows.malfind`

Suspicious memory regions. Look for:
- RWX private memory in non-JIT processes.
- PE headers in private memory.
- Shellcode patterns.

### Step 8: `windows.ldrmodules`

Cross-check loader lists. Look for:
- Modules in VADs but not in any loader list (reflective loads).
- Primary image VAD without file backing (process hollowing).
- DLLs in `InInit` but not `InLoad` (anomalous unlinking).

### Step 9: `windows.dlllist`

Per-process DLL inventory. Look for:
- DLLs loaded from unusual paths (`%TEMP%`, `%APPDATA%`, user-writable directories).
- DLLs with system-DLL names from non-system paths.
- DLL load times clustered around suspected intrusion time.

### Step 10: `windows.handles`

Cross-process handles, suspicious file/registry handles. Look for:
- Handles to `lsass.exe` from non-system processes.
- Cross-process handles with `WRITE`/`CREATE_THREAD` access.
- Handles to deleted files (recover them with `dumpfiles`).
- Mutex names matching known malware families.

### Step 11: `windows.svcscan`

Services configured on the system. Look for:
- New services pointing to executables in user-writable directories.
- Services with `auto-start` configured for unusual binaries.
- Services with display names that mimic legitimate services.

### Step 12: `windows.registry.hivelist` + targeted `printkey`

Read Run keys, AppInit_DLLs, Image File Execution Options, BootExecute, Winlogon entries from memory hives.

### Step 13: `windows.modules` + `windows.modscan` + `windows.driverscan`

Kernel driver inventory. Look for:
- Drivers loaded from non-standard paths.
- Drivers absent from the loaded list but present via scan.
- Suspicious driver names.

### Step 14: `windows.callbacks` + `windows.ssdt` + `windows.driverirp`

Kernel-level hooking surfaces. Look for:
- Callbacks pointing into unknown drivers.
- SSDT entries not resolving to `ntoskrnl` or `win32k`.
- IRP function tables pointing outside the owning driver.

### Step 15: `yarascan` with curated rules

Final pass with known-bad signatures.

### Step 16: `windows.lsadump` + `hashdump` + `cachedump`

Credential material extraction, if the case calls for it.

### Step 17: `windows.dumpfiles` / `vaddump` for selected targets

Extract suspect binaries for static analysis.

This 17-step chain is not gospel; competent analysts adjust based on initial hypothesis. But these are the moves they run.

---

## 12. Memory-only IOC types

Indicators of compromise that exist in memory but not (or not as cleanly) on disk.

### 12.1 Carved strings from RAM

Strings present in memory that don't appear in any disk artifact. Common case: an attacker downloaded a payload, executed it, the on-disk copy was deleted, but strings (URLs, mutex names, internal version banners) are still in process memory.

`strings memory.raw | grep <pattern>` works at the bulk level. For process-scoped string extraction, `vaddump --pid <pid>` then `strings` on the dumped VAD files.

### 12.2 Cached credentials

NTLM hashes, Kerberos tickets, DPAPI master keys, WDigest plaintexts (where applicable), SAM hashes (if reading from SAM hive in memory rather than disk).

These are sometimes in memory before they're flushed to disk; sometimes only in memory (Kerberos tickets are entirely in-memory short-lived structures).

### 12.3 Decrypted payloads

Packed/encrypted binaries on disk become readable PEs after they're unpacked in memory. The unpacked PE in memory is the analysis-quality artifact.

### 12.4 In-memory C2 configs

Cobalt Strike beacon configs, Sliver implant configs, custom RAT configs. These are decoded at runtime; the on-disk loader contains only the encoded version.

### 12.5 Mutex names

Malware uses named mutexes to prevent re-infection. Names like `Global\<random_hex>`, `MicrosoftUpdateSecurity`, `_x86_x64_compat_`. Visible via `handles --type Mutant`.

### 12.6 Named pipes

C2 frameworks use named pipes for inter-process or inter-host communication. `\\.\pipe\msagent_*`, `\\.\pipe\status_*`, `\\.\pipe\<custom>` patterns. Visible via `handles --type File` filtered to `\Device\NamedPipe`.

### 12.7 Window class names

Some malware creates hidden windows for message-based IPC. Window class names are queryable from `win32k.sys` structures.

### 12.8 In-memory scripts

PowerShell ScriptBlocks, JScript code, VBScript code that was loaded into a script-host process and is sitting in the heap. PowerShell's AST cache and script block cache are particularly rich; `yarascan` on `powershell.exe` memory often surfaces decoded scripts that were never written to disk.

### 12.9 In-memory event logs

Recent Sysmon, Security, and other event log records sit in the relevant logging service's heap before being flushed. `evtxtract`-style tooling can carve event records from memory even when the on-disk log was cleared.

### 12.10 Cleartext network protocol payloads

If a process has just received an HTTP response, the response body is sitting in its receive buffer. Decrypted TLS content (HTTPS POST bodies, response bodies) is briefly in memory during processing.

---

## 13. MemProcFS

MemProcFS is an alternative memory analysis paradigm developed by **Ulf Frisk**. Instead of treating the memory image as something to be queried by plugins, MemProcFS **mounts the memory image as a filesystem**. Once mounted, the analyst navigates processes, files, registries, and analysis output as directories and files.

### 13.1 Architecture

- Single binary (`MemProcFS.exe` on Windows, `memprocfs` on Linux).
- Uses Dokany (Windows) or FUSE (Linux) to expose a virtual filesystem.
- Mount point typically `M:\` on Windows or `/tmp/MemProcFS/` on Linux.
- Backend: Ulf Frisk's `vmm.dll` / `libvmm.so` library, which can also be called programmatically.

### 13.2 Filesystem layout (Windows memory image)

After mounting, the filesystem looks like:

```
M:\
├── name\
│   ├── powershell-1234\
│   │   ├── files\           # files mapped/cached for this process
│   │   ├── handles\         # process handles
│   │   ├── modules\         # loaded modules
│   │   ├── threads\         # threads
│   │   ├── vmemd            # virtual memory dump
│   │   ├── ...
│   └── ...
├── pid\
│   └── 1234\                # same as name\powershell-1234\
├── sys\
│   ├── modules\             # kernel modules
│   ├── tasks\               # scheduled tasks
│   ├── services\            # services
│   ├── pool\                # pool allocations
│   ├── proc\                # processes
│   └── ...
├── conf\                    # MemProcFS config
├── forensic\                # YARA, NTFS MFT, registry, web, etc.
│   ├── yara\
│   ├── ntfs\
│   ├── reg\
│   ├── timeline.txt         # combined timeline
│   ├── web.txt              # browser history extracted
│   └── ...
├── misc\
│   ├── findevil\            # MemProcFS's built-in Find-Evil heuristics
│   └── ...
```

### 13.3 The `findevil` directory

MemProcFS ships its own automated "find evil" pass. Heuristics include:

- Suspicious processes (no DLLs, no main image, parent mismatch).
- DLLs loaded from suspicious paths.
- Injected memory regions (its own malfind equivalent).
- Suspicious driver behavior.
- Kernel callbacks pointing at non-driver memory.
- Process hollowing indicators.
- Known-bad strings via integrated YARA.

This produces a flat file listing findings — the same conceptual output as a Volatility plugin sweep, but materialized as files.

### 13.4 Comparison with Volatility 3

- Different mental model: filesystem navigation vs plugin invocation.
- MemProcFS is generally faster for ad-hoc exploration (you can `cd`, `cat`, `grep`).
- Volatility's plugin output is more structured (TreeGrid) and easier to programmatically consume.
- MemProcFS supports live-memory analysis on Windows (reading from `\\.\PhysicalMemory` or via PCILeech), which Vol3 does not.
- MemProcFS has its own symbol caching (it parses PDBs similarly).
- Both can be scripted; MemProcFS exposes a Python API via `vmmpy`.

### 13.5 Operational note

MemProcFS and Vol3 are complementary. Many analysts use MemProcFS for exploration and Vol3 for specific plugin output, or vice versa. They can analyze the same memory image at the same time.

---

## 14. Tool ecosystem around Vol3

A non-exhaustive map of related tools.

### 14.1 Rekall

Originally a Google fork of Volatility 2 (2013) by Michael Cohen and Andrew Case. Introduced many ideas later folded back into Vol3 (symbol cache, layered architecture). **Effectively dead as of 2020**; no active maintenance. Its WinPMEM lineage is the main surviving descendant.

For new work: ignore Rekall, use Vol3 or MemProcFS.

### 14.2 Memory Baseliner

Heuristic tool that compares a memory image against a known-clean baseline of the same OS build, flagging deviations. Niche but useful in enterprise IR where many endpoints share an image.

### 14.3 `evtxtract` (in memory)

`evtxtract.py` and related tools carve event log records from memory or disk fragments. The format of in-memory event log chunks is parseable, so even when the on-disk `.evtx` was cleared, the recently-emitted records may be recoverable from `EventLog` service heap.

### 14.4 `bulk_extractor`

Simson Garfinkel's tool that runs many feature extractors (email addresses, URLs, credit cards, Bitcoin addresses, GPS coordinates) across raw memory dumps. Volatility-agnostic — works on any byte stream.

### 14.5 `strings` (binutils) + `xxd`

Universal: `strings -el memory.raw | grep` for UTF-16LE Unicode strings (most Windows strings are wide); `-a` for all encodings. Cheap pivot tool for keyword hunts.

### 14.6 `yara` standalone

YARA can scan memory dumps directly (`yara rules.yar memory.raw`), bypassing Vol3 if all you need is signature matching. Faster for bulk scans.

### 14.7 `mftparser` / `MFTECmd`

Operate on MFT files. When `windows.mftscan` recovers MFT records from memory, these tools can parse them.

### 14.8 `regripper`

Operates on registry hives. When `windows.dumpfiles` extracts a registry hive from memory, regripper plugins can be applied.

### 14.9 `pe-sieve` / `Hollows Hunter`

Hasherezade's tools for detecting in-process injection. Originally live-system tools; can be applied to extracted process memory.

### 14.10 Velociraptor (live)

Mike Cohen's live forensic agent. Can be told to run memory acquisition (via WinPMEM under the hood) and ship the result to a server for offline analysis with Vol3.

### 14.11 SANS SIFT Workstation

The SANS Investigative Forensic Toolkit. Ships pre-installed: Volatility 3, Vol2 (`vol.py`), MemProcFS (recent versions), plaso, log2timeline, sleuthkit, autopsy, regripper, yara, bulk_extractor, network analysis tools, the Cellebrite/Magnet ecosystem connectors. SIFT is the prescribed substrate for this hackathon (Rules §4). All of the above tools coexist in a SIFT install.

---

## 15. Memory + disk + log corroboration patterns

A claim about adversary activity is stronger when supported by independent artifacts from memory, disk, and logs. This section catalogs corroboration patterns — the specific signatures that should align for a given observation.

### 15.1 "Process X ran on this system"

If a process appears in `pslist`/`psscan`, the strong-corroboration profile is:

- **Disk:** Amcache entry for the executable's path, hash, and first-execution time. Prefetch file `XXX.EXE-<hash>.pf` recording each execution. ShimCache (`AppCompatCache`) entry. UserAssist entry (if GUI-launched). Recent Windows builds also have `BAM\State` (Background Activity Moderator) entries.
- **Memory:** `pslist` entry, `psscan` entry, command line in `cmdline`, parent process in `pstree`, threads consistent with `_KPROCESS`, handles open, modules loaded.
- **Logs:** Sysmon EID 1 (Process Create) with command line, parent PID, parent image, hash, user. Security EID 4688 (Process Creation) — same data, requires Process Creation auditing enabled.
- **Network:** If the process made network connections, Sysmon EID 3 with source/destination/protocol.

If a process is in `pslist` but missing from Amcache, Prefetch, Sysmon EID 1, AND ShimCache, then either:
- The auditing was disabled / Sysmon wasn't running.
- The process was started very recently (logs not yet flushed).
- The artifacts were cleaned (anti-forensics).
- The process was created by an unusual path (kernel-mode injection into `userinit.exe` etc.).

### 15.2 "A user logged on at time T"

- **Memory:** `_LOGON_SESSION` entries in `lsass.exe` (via `volshell`-level analysis) reflecting active logon sessions.
- **Logs:** Security EID 4624 (Logon) with `LogonType`, `IpAddress`, `WorkstationName`. Security EID 4648 (explicit credential logon). RDP-specific events in `Microsoft-Windows-TerminalServices-LocalSessionManager%4Operational.evtx`.
- **Disk:** UserAssist updates after login. `NTUSER.DAT` timestamp updates.

### 15.3 "Network connection to attacker IP"

- **Memory:** `netscan` / `netstat` entries with the IP.
- **Logs:** Sysmon EID 3 (Network Connect). DNS query logs (Sysmon EID 22, or DNS service logs).
- **Network capture (if available):** pcap entries with the matching 5-tuple.
- **Disk:** Firewall logs (`pfirewall.log`) if Windows Firewall logging enabled.

### 15.4 "DLL injected into LSASS"

- **Memory:** Unexpected DLL in `dlllist --pid <lsass>`. `ldrmodules` may show it absent from loader lists (if injected reflectively).
- **Logs:** Sysmon EID 7 (Image Load) for `lsass.exe` showing the unexpected DLL.
- **Disk:** The DLL on disk (if standard-loaded) with hash, signer.

### 15.5 "Persistence via Run key"

- **Memory:** `windows.registry.printkey` against `\Software\Microsoft\Windows\CurrentVersion\Run` showing the entry.
- **Disk:** Same registry hive on disk showing the same value (in-memory copy may be ahead).
- **Logs:** Sysmon EID 12 (RegistryEvent) or Security EID 4657 (Registry change) if registry auditing enabled.

### 15.6 "Scheduled task added"

- **Memory:** Task structures in memory (visible via specific Vol3 plugins or MemProcFS).
- **Disk:** `\Windows\System32\Tasks\<name>` XML file. `\Windows\System32\config\SOFTWARE` registry key `\Microsoft\Windows NT\CurrentVersion\Schedule\TaskCache\Tree\<name>`.
- **Logs:** Security EID 4698 (Scheduled Task Created), `Microsoft-Windows-TaskScheduler/Operational` EID 106 (Task Registered).

### 15.7 "Service installed"

- **Memory:** `svcscan` entry.
- **Disk:** `SYSTEM` hive `\ControlSet\Services\<name>` key with `ImagePath`.
- **Logs:** Security EID 7045 (Service Installed) in System log. EID 4697 (Service Installed) in Security log.

### 15.8 "Credentials accessed via LSASS dump"

- **Memory:** `handles --pid <attacker>` showing handle to lsass with `PROCESS_VM_READ`. Possibly `comsvcs.dll MiniDump` or `MiniDumpWriteDump` recently called.
- **Logs:** Sysmon EID 10 (Process Access) for `lsass.exe` with non-system source process.
- **Disk:** A `.dmp` file dropped, often in `%TEMP%`.

### 15.9 Discrepancies are evidence

When memory says something different from disk or logs, this is itself a finding:

- Process in memory but not in any log → log tampering, Sysmon disabled, or unusual launch path.
- File handle in memory to a path that doesn't exist on disk → file deleted post-open.
- Registry value in memory that disk hive doesn't have → in-memory edit not yet persisted, OR memory copy is from before the disk was tampered.
- Driver in `modscan` but not in `modules` → unlinking.
- DLL in `dlllist` whose backing file on disk hash-mismatches the in-memory copy → process hollowing or herpaderping.

---

## 16. Memory acquisition pitfalls (continued)

§2.9 already covered the basics. This section drills into the failure modes that bite during analysis.

### 16.1 Atomicity revisited — what smear looks like

A smeared dump is not "corrupted" in the bit-flip sense; it's internally inconsistent in the structural sense. Concrete examples:

- `_EPROCESS.ActiveProcessLinks.Flink` points at an address that no longer has an `_EPROCESS` (the process exited mid-walk). Vol3's pslist may emit an error or skip past it.
- `_HANDLE_TABLE` references an object that has been freed. Handle dereferences fail.
- A network connection's owner PID points to a process that doesn't exist in `pslist` because that process exited between when the connection was recorded and when the process table was recorded.
- A VAD's mapped file pointer points to a `_FILE_OBJECT` that has been freed.

These manifest in plugin output as missing fields, error annotations, or row counts that don't match cross-references.

### 16.2 Acquisition driver footprint

Every kernel-mode acquisition tool creates:

- A driver loaded entry (visible in `windows.modules`).
- A Sysmon EID 6 event (Driver Loaded).
- A Security EID 4673 event (if Privilege Use auditing is enabled).
- A new kernel module signing chain validation event (if Code Integrity events are enabled).
- The driver service registry entry under `\SYSTEM\CurrentControlSet\Services\<driver name>`.
- Allocations in non-paged pool for the driver's runtime data.

The acquired dump contains all of this. Investigators learn to recognize the acquisition tool's footprint and exclude it from suspicion.

### 16.3 Acquisition tool process footprint

The acquisition utility's own process (`winpmem.exe`, `DumpIt.exe`, `MagnetRAMCapture.exe`) appears in `pslist`. Its command line is in `cmdline`. Its handles are in `handles`. The handle to the output file (`memory.raw`) is open, often with multi-GB ranges referenced in the cache manager.

### 16.4 Antivirus / EDR interference

Real-time AV/EDR may flag the acquisition tool's driver as suspicious, block it, or quarantine it. Common results:

- Acquisition driver load fails.
- Acquisition tool exits with a generic "access denied" or "driver could not be loaded".
- The acquired dump is empty or truncated.

Operationally, before acquisition, IR teams often temporarily allowlist the acquisition tool in the AV/EDR console. This itself produces audit events.

### 16.5 Working set vs full physical RAM

Default acquisition mode varies by tool. Some tools (older Microsoft `livekd` paths, some quick-capture utilities) capture only the working set — pages currently mapped and not paged out. The dump file is smaller than installed RAM. This is intentional sometimes (faster acquisition) but always loses the contents of paged-out pages.

Verification: compare dump file size to physical RAM (allowing for header overhead and unmapped MMIO holes). A 4 GB dump from a 32 GB system is almost certainly partial.

### 16.6 BitLocker / disk encryption interactions

If the system disk is BitLocker-encrypted and the IR team images both disk and memory, the in-memory cache of file content is unencrypted (the cache manager works on plaintext). This means memory-side `dumpfiles` may recover files that on-disk imaging cannot decrypt without the BitLocker key.

This is operationally important: capture memory before powering down a BitLocker-protected box, because power-down may evict the volume key from memory.

### 16.7 Wake-from-sleep timing

If the system was asleep and was woken to perform memory acquisition, the wake transition itself modifies hundreds of pages (kernel timer wheels, deferred procedure calls, suspended thread restoration). The dump reflects post-wake state, which may differ from sleep-state forensic interest.

For maximum fidelity on sleep-state systems, image the disk first (which captures `hiberfil.sys` if hibernation was used) and analyze the hibernation file rather than a live-wake dump.

---

## 17. Compressed memory analysis

A deeper look at the Memory Compression Store, because it is the single most disruptive change to Windows memory forensics in the last decade.

### 17.1 What Memory Compression is

Introduced in Windows 10 (and present in all Windows 11 builds), Memory Compression replaces a portion of traditional paging behavior. When the system needs to reclaim memory, instead of writing pages to `pagefile.sys`, the kernel compresses them using **Xpress** and stores them in a dedicated process (`MemCompression` or `Memory Compression`, the name has varied).

The performance benefit: decompression is faster than disk paging. The forensic cost: the compressed pages are no longer directly readable in the original process's address space.

### 17.2 How it works at the kernel level

The kernel maintains a **compression store** — a pool of compressed regions inside the `MemCompression` process. When a page is selected for compression:

1. The kernel compresses the page content (typically Xpress).
2. The compressed bytes are stored in the `MemCompression` process's address space at some offset.
3. The original process's PTE is modified to point to the compression store entry rather than to a physical frame.
4. When the original process touches the page, a page fault occurs; the kernel decompresses on demand.

### 17.3 Forensic implications

When Vol3 walks the page tables of a process whose pages have been compressed, it encounters PTEs that look like swap PTEs but reference the compression store rather than `pagefile.sys`. Without compression-store awareness, the read fails: Vol3 sees "this page is not in physical memory" and gives up.

### 17.4 Vol3's handling

Vol3 maintained 3.x has added **compressed memory layer** support. The flow:

1. During automagic, Vol3 identifies the `MemCompression` process.
2. It parses the `_SM_BIG_PAGE_ENTRY` and related structures that index the compression store.
3. When a downstream read targets a page whose PTE indicates compression, Vol3 looks up the compressed region, decompresses it, and returns the original page content.

This is transparent to plugins — `pslist`, `cmdline`, `dlllist` all see the decompressed view.

### 17.5 Failure modes

- Older Vol3 versions (pre-2020) lack the layer. Output for any process with cold pages is incomplete.
- The compression algorithm has shifted across Windows builds (Xpress to LZ77 variants in places). New build = layer needs updating.
- If the `MemCompression` process structures are smeared or corrupted, the decompression fails and the page is unreadable. Plugins may still operate on the pages that are uncompressed.

### 17.6 Detecting compression activity

The presence of a `MemCompression` (or `Memory Compression`) process in `pslist` indicates the system has the feature enabled and was actively compressing. Its size (`Handles`, working set) correlates with how much memory was under compression at the time.

---

## 18. Linux memory specifics

Linux memory forensics has different mechanics than Windows. This section catalogs the differences relevant to Vol3 (and Vol2 fallback).

### 18.1 Kernel symbol map (System.map, kallsyms)

Linux kernels do not have PDBs. Symbols come from one of:

- `System.map` — a flat text file mapping symbols to addresses, generated at kernel build time. Located at `/boot/System.map-<version>` on most distributions.
- `/proc/kallsyms` — runtime export of kernel symbols. Readable as root (with `kptr_restrict` setting permitting).
- `vmlinux` — the uncompressed kernel image with DWARF debugging info if the distribution shipped a debug build.

For Vol3, the symbol table needs to be converted to an ISF using **`dwarf2json`** (Volatility Foundation tool):

```
dwarf2json linux --elf /path/to/vmlinux > linux.json
```

If `vmlinux` is not available, but `System.map` is, the conversion is harder — `System.map` doesn't carry type information. The fallback is finding a debug package matching the running kernel version.

For Vol2, the equivalent process produces a `.zip` profile combining a System.map-like layout with a `module.dwarf` file built from a kernel module compiled with debugging info against the target kernel's headers.

### 18.2 Kernel version specificity

Linux structure layouts change between minor versions, especially between major kernels (5.x → 6.x). The ISF must match the exact running kernel. Vol3 will refuse to proceed or emit garbage if the symbols don't match.

Common operational pain: a target system runs `5.15.0-100-generic` and the IR team doesn't have the matching `vmlinux`. Building one requires:

1. Boot a matching kernel in a sandbox.
2. Install `linux-image-5.15.0-100-dbgsym` or distribution equivalent.
3. Run `dwarf2json linux --elf vmlinux-5.15.0-100-generic > 5.15.0-100.json`.
4. Place the JSON in the symbol cache.

Step 1 alone requires having a system that can run the matching kernel.

### 18.3 LiME-format acquisition

LiME is the standard Linux memory acquisition method. The LiME LKM is built against the target kernel's headers:

```
make -C /lib/modules/$(uname -r)/build M=$(pwd) modules
insmod lime.ko "path=/tmp/memory.lime format=lime"
```

The LiME format is read by Vol3 directly.

### 18.4 `/proc/kcore`

A pseudo-file that exposes the kernel's view of physical memory as an ELF core dump. Readable as root with appropriate sysctl settings:

```
cat /proc/kcore > /tmp/memory.core
```

Vol3 reads ELF core format directly.

Limitations: `/proc/kcore` represents kernel-mapped memory, not all physical pages. Some forensic content (user-mode pages of processes the kernel hasn't mapped recently) may not be reachable.

### 18.5 AVML

Microsoft's `avml` tool (Acquire Volatile Memory for Linux) is a single static binary, no LKM required:

```
./avml /tmp/memory.lime
```

It uses `/proc/kcore` or `/dev/crash` under the hood. Convenient for incident response where LKM building is impractical.

### 18.6 eBPF programs

eBPF (extended Berkeley Packet Filter) lets userspace load programs into the kernel for tracing, networking, and security. Loaded eBPF programs are kernel-resident and execute in kernel context.

Forensic relevance: malicious eBPF programs can hide processes, hide network connections, harvest credentials, intercept syscalls. They live in kernel memory but are not loaded as kernel modules — they live in a separate eBPF subsystem.

Vol3's eBPF coverage is partial. Plugins to enumerate eBPF programs (`linux.ebpf.list_programs`-style) are community contributions of varying maturity. The kernel data structures for eBPF (`struct bpf_prog`, `struct bpf_map`) are documented in kernel source and parseable via `volshell` if needed.

Real-world eBPF rootkits in 2024-2026 include **TripleCross**, **boopkit**, **ebpfkit**. These have established eBPF as a forensic target worth attention.

### 18.7 Kernel module rootkits

Classic Linux rootkit family — Diamorphine, Reptile, Suterusu, Adore-Ng — install as kernel modules and hook syscalls, kernel functions, or VFS operations.

Vol3 detection paths:

- `linux.check_modules` for unlinked modules.
- `linux.check_syscall` for hooked syscalls.
- `linux.lsmod` baseline.
- `linux.malfind` for injected user-mode code.

### 18.8 Linux container considerations

Containers (Docker, containerd, Kubernetes) run as processes on the host kernel with namespace isolation. A single Linux memory dump contains all processes from all containers in the same task list.

Volatility plugins do not distinguish "container A's process" from "container B's process" out of the box. To attribute processes to containers, walk `task_struct.nsproxy` (namespace proxy) and group by `pid_ns`, `mnt_ns`, etc.

`/proc/<pid>/cgroup` would normally identify container membership; in memory, this requires parsing cgroup structures from the kernel directly.

### 18.9 Linux file system caching

The Linux page cache caches file content for accelerated reads. When `linux.lsof` shows an open file, the file's content may be in the page cache and recoverable. The kernel structure is `struct address_space` per inode, with `i_pages` (formerly `page_tree`) holding cached pages.

Vol3's Linux file-recovery support is more limited than Windows-side `dumpfiles`. Community plugins exist for specific use cases.

---

## 19. Summary of what each plugin produces (quick reference matrix)

For the design-phase agent: which plugin maps to which question.

| Question | Primary plugin | Cross-check |
|---|---|---|
| What OS, kernel version? | `windows.info` | – |
| What processes were running? | `windows.pslist` | `windows.psscan`, `windows.psxview` |
| What processes were hidden? | `windows.psscan` | `windows.psxview` |
| What was the parent of this process? | `windows.pstree` | – |
| What was the command line? | `windows.cmdline` | `windows.consoles`, `windows.cmdscan` |
| What's running in this console? | `windows.consoles` | `windows.cmdscan` |
| What network connections were live? | `windows.netstat` | `windows.netscan` |
| What network connections recently closed? | `windows.netscan` | – |
| What DLLs were loaded? | `windows.dlllist` | `windows.ldrmodules` |
| Was code injected into a process? | `windows.malfind` | `windows.ldrmodules`, `yarascan` |
| Process hollowing? | `windows.ldrmodules` | `windows.vadinfo`, comparing `dumpfiles` to `vaddump` |
| Reflective DLL? | `windows.malfind` | `windows.ldrmodules` (absent from all 3 lists) |
| What handles is this process holding? | `windows.handles` | – |
| What services are configured? | `windows.svcscan` | – |
| What's in this registry key? | `windows.registry.printkey` | – |
| What drivers are loaded? | `windows.modules` | `windows.modscan`, `windows.driverscan` |
| Hidden drivers? | `windows.modscan` | `windows.modules` |
| Kernel callbacks? | `windows.callbacks` | – |
| SSDT hooks? | `windows.ssdt` | – |
| IRP hooks? | `windows.driverirp` | – |
| Extract files from memory? | `windows.dumpfiles` | `windows.vaddump` |
| Extract suspicious memory regions? | `windows.vaddump` | `windows.malfind --dump` |
| LSA secrets? | `windows.lsadump` | – |
| Local password hashes? | `windows.hashdump` | – |
| Cached domain creds? | `windows.cachedump` | – |
| Token privileges? | `windows.privileges` | – |
| Suspended threads? | `windows.suspended_threads` | – |
| YARA scan? | `yarascan` | – |
| Process environment? | `windows.envars` | – |
| MFT records in memory? | `windows.mftscan` | – |
| MBR check? | `windows.mbrscan` | – |
| Skeleton key (DC)? | `windows.skeleton_key_check` | – |

---

## 20. Closing notes on the state of the art

Memory forensics in 2026 sits in an interesting place. The tooling has matured (Vol3 stable since 2019, MemProcFS broadly adopted, both with active development) but the adversary has shifted:

- **Memory-only operation is the default for serious tooling.** Cobalt Strike, Sliver, Brute Ratel, Mythic implants, BlackCat ransomware loaders, FIN7 toolsets — all expect to live in memory.
- **VBS/HVCI/Credential Guard reshape what's available.** LSASS protection means hash dumping is harder; the credential-extraction repertoire has shifted to ticket harvesting, Kerberoasting (which doesn't require LSASS reads), and AS-REP roasting.
- **Process injection is well-understood but still pervasive.** New variants (HellsGate, HalosGate, Unhooked syscalls) try to evade EDR's userland hooks, but their in-memory artifacts (RWX regions, PE headers, suspicious VADs) are still detectable by Vol3 / MemProcFS / `malfind` / `yarascan`.
- **eBPF rootkits on Linux are the rising threat.** Detection lags; Vol3 is catching up.
- **Memory compression on Windows 10/11 broke older tools.** Modern Vol3 handles it; many older blog posts and scripts do not.
- **VBS-protected secrets are forensically opaque.** What can't be read out of VTL1 can't be analyzed.

Practical implication for any system that wraps memory forensics tooling: the underlying primitives are stable (process listing, network listing, VAD walking, registry-from-memory) and the plugin set is unlikely to fundamentally change. New plugins arrive for new attacker techniques. Cross-plugin reasoning (the diff-`pslist`-against-`psscan` pattern, the `ldrmodules` cross-check pattern) is where forensic-quality conclusions come from.

This file is a knowledge base, not a recipe. The decisions about how a downstream agent uses this knowledge — which plugins to run when, how to combine output, how to surface findings, how to report — are decisions for the design phase, made against the wedge committed in `STRATEGY.md`.

---

## References and sources

- Volatility Foundation. Volatility 3 documentation. `https://volatility3.readthedocs.io/`
- Volatility Foundation. Symbol packs. `https://downloads.volatilityfoundation.org/volatility3/symbols/`
- Volatility Foundation. dwarf2json. `https://github.com/volatilityfoundation/dwarf2json`
- Andrew Case, Aaron Walters, Jamie Levy, Michael Ligh. *The Art of Memory Forensics*. Wiley, 2014. (Vol2-era but still the canonical text on the underlying structures.)
- Andrew Case et al. DFRWS papers on Volatility architecture, 2007–2022.
- Ulf Frisk. MemProcFS. `https://github.com/ufrisk/MemProcFS`
- Ulf Frisk. PCILeech. `https://github.com/ufrisk/pcileech`
- Brian Carrier. *File System Forensic Analysis*. Addison-Wesley, 2005. (Companion for the disk side of corroboration.)
- Stephen Fewer. Reflective DLL loader. 2008.
- Tal Liberman, Eugene Kogan. Lost in Transaction: Process Doppelgänging. Black Hat EU 2017.
- Johnny Shaw. Process Herpaderping. 2020.
- Mitja Kolsek. Process Ghosting. 2021.
- Microsoft. PDB symbol server. `https://msdl.microsoft.com/download/symbols`
- Microsoft. Windows Internals (Russinovich, Solomon, Ionescu, Yosifovich). Multiple editions for Windows version coverage.
- Brezinski & Killalea. RFC 3227 — Guidelines for Evidence Collection and Archiving. 2002.
- Matthieu Suiche. Hibernation file research, MoonSols Windows Memory Toolkit. 2008–2017.
- Arsenal Recon. Hibernation Recon documentation.
- Microsoft. AVML. `https://github.com/microsoft/avml`
- LiME. `https://github.com/504ensicslabs/lime`
- Florian Roth. signature-base YARA rules. `https://github.com/Neo23x0/signature-base`
- Hasherezade. pe-sieve, Hollows Hunter. `https://github.com/hasherezade/`
- Didier Stevens. `1768.py` Cobalt Strike beacon config decoder.
- Mike Cohen. WinPMEM, Rekall, Velociraptor.
- Volatility Plugin Contest entries, 2015–2024. (Community plugin work.)
- SANS FOR526 (Memory Forensics In-Depth) course materials. (Curriculum reference, paywalled.)
- SANS FOR508 (Advanced Incident Response, Threat Hunting, and Digital Forensics) course materials.
