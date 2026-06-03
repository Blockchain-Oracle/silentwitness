# Domain Knowledge — DFIR + SIFT + MCP + Agentic

Compiled June 2026 for the Find Evil! / Protocol SIFT hackathon. This document gives the coding agent enough domain knowledge to design a winning submission without re-doing the research. Sources are cited inline; the prized one is **Valhuntir / AppliedIR's `sift-mcp`** monorepo, which is a near-complete reference architecture for the winning pattern.

---

## A. DFIR fundamentals (what we're automating)

### A.1 IR phases & triage methodology

**NIST SP 800-61 r2 IR lifecycle (canonical):**

1. **Preparation** — tooling, runbooks, baselines, jump bag.
2. **Identification** — first signal: alert, anomaly, IOC hit, user report. Goal: confirm there *is* an incident and classify severity.
3. **Containment** — short-term (isolate host) and long-term (re-image, segment). Stops the bleed without destroying evidence.
4. **Eradication** — remove malware, close persistence, rotate credentials, patch the entry vector.
5. **Recovery** — restore services, verify clean, monitor for re-compromise.
6. **Lessons Learned** — post-mortem, detection gaps, update runbooks.

**SANS PICERL is the same six steps with slightly different naming** (Preparation → Identification → Containment → Eradication → Recovery → Lessons Learned).

**Triage is the bridge between Identification and Containment.** It answers four questions FAST:

- Is this a real incident or a false positive?
- What's the blast radius (one host, ten hosts, whole domain)?
- What TTPs is the adversary using (so we know what to look for elsewhere)?
- Is the adversary still active?

**Two triage philosophies — pick one:**

| Approach | Description | When it wins | Failure mode |
|---|---|---|---|
| **Kitchen sink** | Run every parser against every artifact, build a 50k-row super-timeline, grep for evil | Junior analysts, unknown unknowns, post-mortem with time | Drowns in noise; spends hours in dead lanes |
| **Hypothesis-driven** | Form a hypothesis from the initial signal ("phishing → mshta → C2"), pull only the artifacts that prove/disprove it, pivot fast | Senior analysts, live incident, AI agents with budget | If hypothesis is wrong, you confirm it wrongly (confirmation bias) |

**The Protocol SIFT design target is hypothesis-driven with kitchen-sink fallback.** Rob T. Lee's "Find Evil" demo did C-drive analysis in 14:27 — that's hypothesis-driven plus broad sweep, not pure dump-everything. The senior-analyst skill the hackathon is rewarding is **knowing when to stop digging and pivot.**

### A.2 "Finding Evil" — what senior analysts look for

"Find Evil: Know Normal" is a **SANS poster series** (initially "Find Evil", revised "Hunt Evil" in 2018) by the SANS DFIR faculty. Rob T. Lee adopted "find evil" as the Protocol SIFT command-line incantation specifically because the poster makes baseline knowledge of normal Windows the prerequisite for spotting abnormal.

**The senior-analyst mental model — what they actually scan for on a Windows host:**

| Lane | "Known normal" | "Find evil" signals |
|---|---|---|
| Process tree | smss → csrss/wininit → services.exe → svchost.exe instances. lsass.exe is a singleton, child of wininit. explorer.exe is child of userinit. | svchost with no `-k` group; lsass with non-System parent; powershell.exe spawned by Office; rundll32.exe with no DLL arg; processes running from `%TEMP%`, `%APPDATA%`, `\Users\Public`; mismatched parent/child (e.g. cmd.exe child of services.exe directly) |
| Image paths | `C:\Windows\System32\*`, `C:\Program Files\*` | Anything in `\Users\Public\`, `C:\PerfLogs`, `\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`, `C:\Windows\Temp` |
| Network | Known sysvols, DC IPs, internal subnets | Outbound to unfamiliar ASN, DNS for newly-registered domains, beacon cadence (every 60s ± jitter), DGA-pattern hostnames |
| Persistence | Office, Defender, Edge auto-updaters | `Run`/`RunOnce` keys, WMI event subscriptions, scheduled tasks under `\Microsoft\Windows\` clones, service binaries in user-writable paths |
| Accounts | Domain user logging in interactively from their workstation; service accounts running services | Privileged account logging in via Type 3 from a workstation (lateral movement); brand-new local admin; `krbtgt` password recently changed; suspicious `SeDebugPrivilege` grants |
| Execution evidence | App in Prefetch, Amcache, BAM with consistent timestamps; matching Authenticode signer | Execution evidence in Prefetch but missing on disk (deleted); Amcache entries for unsigned binaries in user-writable paths; mismatched `SHA1` between Amcache and the on-disk binary |

The crucial mental shift: **don't ask "is this evil?"; ask "what's the parent process and the user context, and does that combination make sense for what I'm seeing?"**

### A.3 Disk forensics — must-know artifacts

| Artifact | What it tells you | Tool to parse |
|---|---|---|
| `$MFT` (NTFS Master File Table) | Every file/dir on the volume — name, size, timestamps (SI + FN), resident data | MFTECmd, analyzeMFT, fls (Sleuth Kit) |
| `$LogFile` (NTFS journal) | Recent MFT transactions — recovers deleted file names, helps detect timestomping | LogFileParser, ANJP |
| `$UsnJrnl:$J` (USN Change Journal) | Every file create/modify/delete with reason flags. Crucial for catching short-lived files | MFTECmd `--csv` + USN flag, UsnJrnl2Csv |
| Prefetch (`C:\Windows\Prefetch\*.pf`) | Up to 1024 entries (Win 7+). First/last 8 run times, files/dirs accessed during first 10s of execution | PECmd (EZ tool), Prefetch.py |
| ShimCache / AppCompatCache (registry `SYSTEM\ControlSet001\Control\Session Manager\AppCompatCache`) | Programs that ran or were *prompted* for compatibility shimming — up to ~1024 entries | AppCompatCacheParser (EZ), RegRipper `appcompatcache.pl` |
| Amcache (`C:\Windows\AppCompat\Programs\Amcache.hve`) | Every PE the system saw — full path, SHA1, file size, publisher, last modified, first run | AmcacheParser (EZ), RegRipper |
| Registry hives (SYSTEM, SOFTWARE, SAM, SECURITY, NTUSER.DAT, UsrClass.dat) | Persistence, configuration, user activity, account info | RegRipper, RECmd (EZ), Registry Explorer |
| `Run` / `RunOnce` keys | Autorun persistence | RegRipper `softrun.pl`, `userrun.pl` |
| Windows Event Logs (`*.evtx`) | Authentication, process creation, service install, log clear, RDP | EvtxECmd (EZ), Hayabusa, Chainsaw, evtx_dump |
| Sysmon log (`Microsoft-Windows-Sysmon/Operational.evtx`) | High-fidelity process create, network, file create, registry, image load | EvtxECmd, Hayabusa, Chainsaw |
| PowerShell logs (4103 module, 4104 script block) | Decoded PS scripts even if obfuscated/encoded | EvtxECmd, Chainsaw |
| ShellBags (`UsrClass.dat\Local Settings\Software\Microsoft\Windows\Shell\BagMRU`) | Every folder the user navigated in Explorer (even deleted/external) | ShellBags Explorer, sbecmd (EZ) |
| LNK files / Jump Lists | Recently-opened files, including remote shares | LECmd, JLECmd (EZ) |
| Recycle Bin (`$Recycle.Bin\<SID>\$I*`, `$R*`) | Deleted file name, original path, deletion time, original size | RBCmd (EZ) |
| Browser history (Chrome `History`, Edge `WebCacheV01.dat`, Firefox `places.sqlite`) | URLs, downloads, search terms | BrowsingHistoryView, hindsight, sqlite3 |
| MUICache (`NTUSER.DAT\Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache`) | GUI app first-run by user | RegRipper `muicache.pl` |
| UserAssist (NTUSER\...\UserAssist) | GUI app run counts & last run, ROT13 encoded | RegRipper `userassist.pl` |
| BAM / DAM (`SYSTEM\ControlSet001\Services\bam\State\UserSettings\<SID>`) | Background Activity Moderator — every program run by user with last-execution time | RegRipper `bam.pl`, BAMParser |
| SRUM (`C:\Windows\System32\sru\SRUDB.dat`) | System Resource Usage Monitor: per-app network bytes sent/received, CPU, last 30 days. Gold for exfil sizing | srum-dump, srum_dump (EZ) |
| Scheduled tasks (`C:\Windows\System32\Tasks\*`) | Persistence — XML task definitions | Task scheduler XML reader, RegRipper |
| WMI repository (`C:\Windows\System32\wbem\Repository\OBJECTS.DATA`) | WMI event subscription persistence | PyWMIPersistenceFinder |
| Volume Shadow Copies | Earlier versions of all the above — bypasses timestomping/log clearing | vssadmin / libvshadow / vshadowinfo on SIFT |
| Pagefile.sys / hiberfil.sys / swapfile.sys | Memory fragments on disk — strings, keys, URLs | bulk_extractor, strings, Volatility (hibr2bin) |

### A.4 Memory forensics — must-know artifacts

Memory wins because malware can hide on disk but **must execute in RAM**. RFC 3227 puts memory above disk for the same reason: most volatile = highest priority. Acquire with WinPMEM, Magnet RAM Capture, or DumpIt; analyze with Volatility 3.

| Plugin | What it shows | Senior-analyst pivot |
|---|---|---|
| `windows.info` | OS, build, KDBG | Sanity-check before anything else |
| `windows.pslist` | Active EPROCESS doubly-linked list | Get baseline of processes |
| `windows.psscan` | Memory-scanned for EPROCESS — finds hidden/terminated | If PID in psscan ≠ pslist → DKOM rootkit |
| `windows.pstree` | Parent/child hierarchy | Spot orphans, weird parents |
| `windows.psxview` | Cross-references pslist, psscan, thrdproc, csrss handles, etc. | Hidden process detection |
| `windows.malfind` | Pages that are RWX with no mapped file — classic injection | Best single hallmark of code injection |
| `windows.dlllist` | Loaded DLLs per process | Spot unsigned/wrong-path DLLs |
| `windows.handles` | Open handles (files, registry, mutexes) | Find C2 mutexes, file locks |
| `windows.netscan` | Active connections + listeners + recently-closed | Identify C2 endpoints |
| `windows.cmdline` | Process command lines | Beats Sysmon when Sysmon wasn't deployed |
| `windows.consoles` / `windows.cmdscan` | conhost history — what the attacker typed | Recover attacker keystrokes |
| `windows.svcscan` | Services in memory — including hidden | Service-based persistence |
| `windows.registry.hivelist` + `printkey` | Live registry from memory | Bypass on-disk anti-forensics |
| `windows.modules` / `windows.modscan` | Kernel modules — `modscan` finds hidden | Rootkit detection |
| `windows.ssdt` | System Service Descriptor Table hooks | Rootkit syscall hooks |
| `windows.dumpfiles` / `windows.memmap.dump` | Carve PE / page contents | Feed to YARA / capa |
| `windows.lsadump` / `windows.hashdump` / `windows.cachedump` | Credential material from LSASS | Mimikatz residue, lateral risk |

**Standard memory triage chain:**
```
windows.info → pstree → psxview → malfind → netscan → cmdline → handles → dumpfiles | yara
```

### A.5 Network forensics

| Tool | Use | Output |
|---|---|---|
| Wireshark / `tshark` | Per-packet GUI/CLI analysis | pcap, CSV, JSON |
| Zeek (formerly Bro) | Protocol-aware connection log: `conn.log`, `http.log`, `dns.log`, `ssl.log`, `files.log`, `x509.log` | TSV/JSON per protocol |
| Suricata | IDS/IPS — runs Emerging Threats rules against pcap or live | eve.json (alerts, flows, http, dns, tls) |
| `bulk_extractor` | Carves IPs, URLs, emails, ccns from any blob (memory, disk, pcap) | text reports + histograms |
| `mergecap` / `editcap` | Manipulate pcaps | pcap |
| RITA | Beacon detection on Zeek conn.log — connection cadence + jitter | analyst report |
| JA3/JA3S | TLS client/server fingerprint — survives cert rotation | hash string |

**C2 signals:** periodic connections (same dst + ~constant interval), long-running TCP sessions, low payload entropy in HTTP POST (encoded but uniform), DNS queries with high-entropy subdomains (DGA / DNS-tunnel exfil), TLS to certs with no SAN matching host, unusual JA3 (`72a589da586844d7f0818ce684948eea` is sslsearch / well-known scanner).

### A.6 Log analysis — critical Windows events

| Event ID | Source | What it means | DFIR use |
|---|---|---|---|
| 4624 | Security | Successful logon. **LogonType 2** = interactive, **3** = network (SMB), **4** = batch, **5** = service, **7** = unlock, **8** = network-cleartext (HTTP basic), **9** = newcredentials (runas), **10** = RemoteInteractive (RDP), **11** = cached interactive | Lateral movement, account takeover |
| 4625 | Security | Failed logon | Password spray, brute force |
| 4634 / 4647 | Security | Logoff / user-initiated logoff | Session duration |
| 4648 | Security | Explicit credential use (runas) | Lateral movement with stolen creds |
| 4672 | Security | Special privileges assigned (incl SeDebugPrivilege) | Privileged session start |
| 4688 | Security | Process creation (requires audit policy + command-line audit GPO) | Killer pivot |
| 4697 | Security | Service installed | Persistence |
| 4698 / 4702 | Security | Scheduled task created / updated | Persistence |
| 4720 / 4732 | Security | User account created / added to local group | Backdoor account |
| 4768 / 4769 / 4771 | Security (DC) | Kerberos TGT request / service ticket / pre-auth fail | Kerberoasting, golden ticket |
| 4776 | Security | NTLM authentication | Pass-the-hash signal |
| 5140 / 5145 | Security | Network share accessed / detailed file share access | Lateral, exfil, ransomware enum |
| 5156 | Security | WFP connection allowed | Network telemetry without Sysmon |
| 1102 | Security | Audit log cleared | Anti-forensics — **always pivot to investigate** |
| 7045 | System | Service installed (no audit policy required) | Persistence — paired with 4697 |
| 7036 | System | Service started/stopped | PsExec leaves `PSEXESVC` here |
| 6005 / 6006 / 6008 | System | System start / clean shutdown / unexpected shutdown | Reboot timeline |
| 104 | System | System log cleared | Anti-forensics |
| 1149 | TerminalServices-RemoteConnectionManager | User authentication succeeded for RDP | Pre-actual logon — useful for IP source |
| 21 / 23 / 24 / 25 | TerminalServices-LocalSessionManager | RDP session start / logoff / disconnect / reconnect | RDP timeline |
| 4103 | PowerShell/Operational | Module/pipeline logging | What cmdlets ran |
| 4104 | PowerShell/Operational | Script block logging — decoded even if `-EncodedCommand` | Recovers payload |
| 600 / 800 | PowerShell (classic) | Engine state / pipeline | Legacy PS logging |

**Sysmon events (config-dependent, SwiftOnSecurity baseline assumed):**

| Sysmon EID | Meaning | Pivot |
|---|---|---|
| 1 | Process create — with cmdline, parent, image hashes | Cmdline > 4688 — captures even if 4688 disabled |
| 2 | File creation time changed | Timestomp detection |
| 3 | Network connection — pid + cmdline | Tie network to process |
| 5 | Process terminated | Closes 1 |
| 6 | Driver loaded | Bring-Your-Own-Vulnerable-Driver |
| 7 | Image loaded — DLL | DLL sideload detection |
| 8 | CreateRemoteThread | Code injection |
| 10 | ProcessAccess (e.g. lsass) | Mimikatz, credential theft |
| 11 | File create | Dropper output |
| 12/13/14 | Registry create/set/rename | Persistence registry mods |
| 15 | FileCreateStreamHash | Alternate Data Streams (download-from-internet, hidden payloads) |
| 17/18 | Pipe create/connect | C2-over-named-pipe, Cobalt Strike SMB beacon |
| 22 | DNS query | DNS exfil, C2 lookup |
| 23 | File delete (archived) | Anti-forensics catch |
| 25 | Process tampering (image change/hollowing) | Process hollowing |

### A.7 Anti-forensics — what to look for

| Technique | Detection |
|---|---|
| **Timestomping** | `$STANDARD_INFORMATION` (SI) timestamps don't match `$FILE_NAME` (FN) — FN is set only at file rename/move and is harder to fake. Sub-second precision: SI is normally 100ns granularity; PowerShell timestomp leaves zeroes in the lower digits. USN journal entry mismatches. |
| **Log clearing** | EID 1102 (Security cleared) / EID 104 (System cleared) leave behind a marker. Pivot to memory (`windows.eventlogs` if Vol3 plugin available) and `$UsnJrnl` for evidence of the cleared records' files |
| **Alternate Data Streams** | Sysmon EID 15 (FileCreateStreamHash). `dir /r`, `streams.exe` (Sysinternals), `fsutil`. On SIFT: `tsk_recover`, `mmls`, or `icat` on the resident attribute. `Zone.Identifier` is normal; everything else is suspicious |
| **Process hollowing / injection** | Volatility `malfind` (RWX + no file mapping), `windows.ldrmodules` (image not in `InLoadOrderModuleList` but mapped), Sysmon 25 (process tampering), 8 (CreateRemoteThread) |
| **Living off the land** | `certutil -urlcache`, `bitsadmin /transfer`, `rundll32 javascript:`, `regsvr32 /s /n /u /i:` (Squiblydoo), `mshta vbscript:`, `wmic process call create`. All legitimate binaries — detected by **parent process anomaly** + cmdline patterns |
| **Disable Defender / EDR** | `Set-MpPreference -DisableRealtimeMonitoring`, EID 5001 (real-time disabled), EID 5007 (config changed). Services 7045 install of EDR-killer drivers |
| **Encrypted volumes / containers** | VeraCrypt / BitLocker — high entropy file with no header. libbde (SIFT) for BitLocker. Look for password in memory pagefile |
| **Wiping tools (sdelete, cipher /w)** | Free-space patterns of zeroes or single-byte fills detectable via bulk_extractor entropy plots |
| **Shadow copy deletion** | `vssadmin delete shadows` — EID 524 (Backup), 8194 (VSS) — paired with subsequent ransomware encryption |
| **Account log obfuscation** | `wevtutil cl Security` (clears log), `auditpol /clear` (resets policy) |

### A.8 MITRE ATT&CK as the narrative skeleton

ATT&CK is the lingua franca for what an attacker did. The 14 tactics (initial access → impact) provide the **narrative spine** the agent must produce — that's what turns a list of artifacts into a report a human reads.

The **Pyramid of Pain** (David Bianco, 2013) explains why MITRE matters:

```
TTPs           ← hardest for attacker to change ← gold for defender
Tools
Network/Host artifacts
Domain names
IP addresses
Hashes          ← trivial for attacker to change ← noise
```

A winning Protocol SIFT submission should output findings at the **TTP level**, not just IOC level. Don't say "found powershell.exe with -EncodedCommand"; say "**T1059.001 (PowerShell)** + **T1027 (Obfuscated Files or Information)**, executed from `C:\Users\bob\AppData\Local\Temp\1.ps1` via parent winword.exe at 2026-02-10 14:23:09 UTC, decoded payload downloads from 23.x.x.x (T1105 Ingress Tool Transfer)."

ATT&CK tactic ordering (memorize this — it's the report structure):

1. Reconnaissance
2. Resource Development
3. **Initial Access** ← where most cases start
4. **Execution**
5. **Persistence**
6. **Privilege Escalation**
7. **Defense Evasion**
8. **Credential Access**
9. **Discovery**
10. **Lateral Movement**
11. **Collection**
12. **Command and Control**
13. **Exfiltration**
14. **Impact**

### A.9 The pivot decision — the senior analyst skill

The single most important thing an agent must do is **know when to stop digging in a lane and pivot to a new one.** This is what separates senior analysts from juniors and what the hackathon judging explicitly rewards under "Autonomous Execution Quality" (the tiebreaker).

Heuristics a senior analyst uses (and the agent should encode):

- **Two corroborating artifacts beats one strong one.** If pslist + Amcache + Prefetch all agree, stop. If they disagree, that disagreement IS the finding — pivot to anti-forensics check.
- **If a lane returns >100 candidate evil indicators, the lane was wrong** — re-narrow or pivot.
- **If a tool errors three times with different inputs, the tool is the problem** — try the equivalent tool, don't retry forever (this is Lee's "Ralph Wiggum Loop" anti-pattern at its worst).
- **Network → process → user → persistence** is the standard pivot chain in a live IR.
- **Time-box per hypothesis.** Senior analysts give a lane 15–30 minutes; an agent should give itself a token budget (~5–10k output tokens / lane) and a step budget (~10 tool calls).
- **The empty result is a result.** If `windows.malfind` returns nothing on a process the user flagged, that's a clearance, not a need to run it again with different flags.

The agent should expose this decision as an *explicit log line* — "PIVOT: memory triage clean across 6 indicators, moving to network beacon analysis" — because that's exactly the kind of audit trail the judges want to see.

---

## B. SIFT Workstation — tool reference

### B.1 Platform overview

- Created ~2007 by Rob T. Lee (SANS, also creator of Protocol SIFT) — currently the SANS Chief AI Officer.
- Ubuntu-based — latest build is **22.04 Jammy (Feb 2024)**.
- Maintained by [teamdfir](https://github.com/teamdfir/sift) (SaltStack-driven install).
- Install: `sudo cast install teamdfir/sift-saltstack` after dropping the Cast binary.
- SANS markets "200+ forensic tools" pre-installed; canonical list lives in the `sift-saltstack` salt states.
- Default user `sansforensics`. `mount_ewf.py` and `imagemounter` for evidence mounting.

### B.2 MUST-KNOW tools

| Tool | Category | Typical invocation | Output | What it parses / produces |
|---|---|---|---|---|
| **Volatility 3 (`vol.py` / `vol`)** | Memory | `vol -f mem.dmp windows.pslist` | Text / JSON / CSV (`--renderer csv`, `--renderer json`) | Plugins per A.4 table above |
| **Volatility 2 (`vol.py`)** | Memory (legacy) | `vol.py -f mem.vmem --profile=Win10x64_19041 pslist` | Text | Profile-based (deprecated for fresh work) |
| **plaso / log2timeline (`log2timeline.py`)** | Timeline | `log2timeline.py --storage_file timeline.plaso disk.E01` | `.plaso` storage file | Super-timeline of every parser plaso supports (~270 parsers) |
| **psort (`psort.py`)** | Timeline | `psort.py -o l2tcsv -w timeline.csv timeline.plaso "date > '2026-02-10' AND date < '2026-02-11'"` | CSV / JSON / Elasticsearch | Filtered super-timeline |
| **RegRipper (`rip.pl` / `rip.exe`)** | Registry | `rip.pl -r SYSTEM -p compname` or `-f system` for a profile | Text | Hive-specific plugins (300+) |
| **bulk_extractor** | Carving | `bulk_extractor -o out/ disk.dd` | text histograms per scanner (email, ip, url, cc, exif, json, kml, pii) | Carves from any blob: disk, mem, pcap |
| **Sleuth Kit (`mmls`, `fls`, `icat`, `istat`, `ils`, `tsk_recover`)** | Filesystem | `mmls disk.E01` → `fls -r -m / -o <offset> disk.E01 > bodyfile` | Bodyfile / text | Low-level filesystem; bodyfile is mactime input |
| **mactime** | Timeline | `mactime -b bodyfile -d > timeline.csv` | CSV | File system timeline from Sleuth Kit bodyfile |
| **Autopsy** | GUI | (GUI) | Case directory | Front-end on Sleuth Kit — not for agents |
| **YARA** | Pattern match | `yara -r rules/ target/` | Text matches (`-s` for strings, `-m` for metadata) | Pattern matching against files / memory |
| **ClamAV (`clamscan`)** | AV | `clamscan -r /evidence` | Text | Known malware signatures |
| **ssdeep** | Fuzzy hash | `ssdeep -r dir/ > fuzzy.txt`, `ssdeep -m fuzzy.txt suspect` | Text | Context-triggered piecewise hash for similarity |
| **strings** | Triage | `strings -e l binary` (unicode) | Text | ASCII / Unicode strings |
| **binwalk** | Carving | `binwalk -e firmware.bin` | Extracted files | Embedded files / firmware analysis |
| **foremost / scalpel** | Carving | `foremost -t all -i disk.dd -o out/` | Files | Header-footer carving |
| **dc3dd / dcfldd / ewfacquire** | Imaging | `ewfacquire disk` (interactive) → .E01 | E01 / raw | Forensic imaging w/ hash + log |
| **ewfmount / ewfinfo / ewfverify** | Imaging | `ewfmount image.E01 /mnt/ewf` | Mounted raw | Mount/inspect E01 |
| **imagemounter / mount_ewf.py** | Mounting | `imount image.E01` | Mounted FS | Auto-mount with VSS handling |
| **libvshadow (`vshadowinfo`, `vshadowmount`)** | VSS | `vshadowmount image.dd /mnt/vss` | Mount points per VSS | Volume Shadow Copy access |
| **libbde (`bdeinfo`, `bdemount`)** | Decrypt | `bdemount -p PASSWORD image /mnt/bde` | Decrypted vol | BitLocker volume decryption |
| **libfvde** | Decrypt | `fvdemount` | Decrypted vol | macOS FileVault |
| **libesedb (`esedbexport`)** | Parse | `esedbexport WebCacheV01.dat` | Tab-separated tables | ESE DB (Edge history, SRUM, Windows Update, DHCP leases) |
| **libevt / libevtx (`evtxexport`)** | Parse | `evtxexport -o xml log.evtx` | XML | Win event logs (use EvtxECmd for cleaner output) |
| **lightgrep** | Search | `lightgrep -p pattern disk.dd` | Hits | Multi-pattern parallel grep |
| **capa** | Malware | `capa suspect.exe` | Text / JSON | Identifies capabilities (e.g. "encrypt data using RC4", "communicate over HTTP") |
| **FLOSS** | Malware | `floss suspect.exe` | Text | Deobfuscates stack/heap/decoded strings |
| **Zeek** | Network | `zeek -r capture.pcap` | TSV logs per protocol | Protocol metadata |
| **Suricata** | Network | `suricata -r capture.pcap -S rules.rules -l out/` | eve.json | IDS alerts on pcap |
| **tshark / tcpdump** | Network | `tshark -r cap.pcap -Y "http.request" -T fields -e http.host` | Text / fields | Packet filtering |
| **Wireshark** | Network GUI | (GUI) | n/a | Interactive — not for agents |
| **NetworkMiner** | Network | (GUI/CLI) | Parsed artifacts | Pcap → files, credentials, hosts |
| **rifiuti2** | Recycle bin | `rifiuti-vista $I*` | CSV | Recycle bin parser |
| **pdf-parser / pdfid / peepdf** | Doc malware | `pdfid suspect.pdf` then `pdf-parser` | Text | PDF object analysis |
| **oledump / oletools** | Doc malware | `olevba suspect.doc` | Text | Office macro extraction |
| **steghide / stegdetect** | Stego | `steghide extract -sf image.jpg` | Files | Steganography |
| **xmount** | Mounting | `xmount --in ewf image.E01 /mnt/x` | Raw / VDI / VMDK | Convert image formats live |
| **dfvfs / dftimewolf** | Plumbing | (library / pipeline) | n/a | Forensic VFS, pipeline orchestration |
| **velociraptor** | Live EDR | `velociraptor --config server.config.yaml frontend` | VQL results | Live endpoint queries + hunts |
| **WMI / Sysmon parsing scripts** | Misc | various | various | |

**Tools NOT in default SIFT (need install, but commonly added by examiners — and a winning submission likely installs them):**

- **Eric Zimmerman (EZ) tools**: MFTECmd, EvtxECmd, AmcacheParser, AppCompatCacheParser, PECmd, RECmd, RBCmd, SBECmd, LECmd, JLECmd, SrumECmd. .NET 6 single-file binaries — run native on Linux per SANS' Aug 2023 guide. **Best-in-class Windows artifact parsing, CSV output is the de-facto standard for input to Timeline Explorer.**
- **Hayabusa** (Yamato Security): Sigma-rule-driven event log threat hunting in Rust. `hayabusa csv-timeline -d <evtx_dir> -o timeline.csv` — 4000+ Sigma rules + 170 native. Fast, native Sigma v2 correlation support.
- **Chainsaw** (WithSecure): Same domain as Hayabusa in Rust, plus built-in detection logic. `chainsaw hunt evtx/ --sigma rules/ --mapping mappings/sigma-event-logs-all.yml`.
- **KAPE** (Kroll Artifact Parser and Extractor): Targets + Modules — collect artifacts, then process with EZ tools. Windows binary; can run via Mono on SIFT.

### B.3 Tools that pair well — the canonical chains

**Disk triage (super-timeline) chain:**
```
ewfmount  →  imagemounter  →  log2timeline.py --storage_file t.plaso /mnt
                            →  psort.py -o l2tcsv -w timeline.csv t.plaso
                            →  filter window (date, source) → CSV
                            →  grep / Timeline Explorer
```

**Eric Zimmerman triage (faster, structured CSV per artifact):**
```
KAPE Targets / manual collect  →  MFTECmd ($MFT)        → mft.csv
                              →  EvtxECmd (Logs)       → evtx.csv
                              →  AmcacheParser         → amcache.csv
                              →  PECmd (Prefetch)      → pf.csv
                              →  AppCompatCacheParser  → shimcache.csv
                              →  SBECmd (UsrClass.dat) → shellbags.csv
                              →  Hayabusa csv-timeline → sigma_hits.csv
                              →  consolidate in Timeline Explorer
```

**Memory triage chain:**
```
WinPMEM / DumpIt  →  mem.dmp
vol -f mem.dmp windows.info
vol -f mem.dmp windows.pstree              → spot anomalies
vol -f mem.dmp windows.malfind             → injection candidates
vol -f mem.dmp windows.netscan             → C2 endpoints
vol -f mem.dmp windows.cmdline             → attacker commands
vol -f mem.dmp windows.dumpfiles --pid <p> → dump suspect
yara -r rules/ dumped/                      → confirm malware family
capa dumped_pe                              → describe behavior
```

**Network triage chain:**
```
capture.pcap  →  zeek -r capture.pcap        → conn.log, dns.log, http.log, ssl.log
              →  suricata -r capture.pcap    → eve.json (alerts)
              →  bulk_extractor              → email/url/ip carving
              →  rita import ./logs          → beacon detection
              →  tshark filters              → targeted extraction
```

**Hunt-Evil log chain (rapid initial triage):**
```
collect .evtx  →  EvtxECmd --csv all.csv
              →  Hayabusa csv-timeline       → sigma hits with MITRE mapping
              →  Chainsaw hunt --sigma       → corroboration
              →  pivot on top-confidence hits
```

---

## C. MCP — the protocol

### C.1 Architecture

**Model Context Protocol** (Anthropic, open standard, late-2024) is a JSON-RPC 2.0 protocol over **stdio** (subprocess pipes) or **Streamable HTTP** transports. Three primitives:

- **Tools** — callable functions with typed input + output schemas. (What the agent invokes.)
- **Resources** — readable data (files, DB rows, API responses). Addressed by URI. (What the agent reads.)
- **Prompts** — server-supplied prompt templates. (Reusable scaffolds.)

Client (the agent / Claude Code / Claude Desktop / etc.) spawns the server subprocess (stdio) or connects over HTTP. They handshake via `initialize` → exchange capabilities → the client enumerates tools/resources/prompts → invokes them.

Tagline Rob T. Lee uses: **"USB-C for AI."** Same plug, any tool.

### C.2 Python SDK — building a server

`mcp` on PyPI. Two API levels: high-level **FastMCP** (decorators) and low-level Server (explicit handlers, more control).

**FastMCP — minimal SIFT example:**

```python
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession
from pydantic import BaseModel, Field
import subprocess
import shlex

mcp = FastMCP("sift-forensics")

class AmcacheEntry(BaseModel):
    """One Amcache program execution record."""
    file_name: str = Field(description="Executable name")
    full_path: str
    sha1: str
    file_size: int | None = None
    publisher: str | None = None
    first_run: str | None = Field(default=None, description="ISO 8601 UTC")

class AmcacheResult(BaseModel):
    entries: list[AmcacheEntry]
    total: int
    case_id: str
    audit_id: str

@mcp.tool()
async def parse_amcache(
    hive_path: str,
    case_id: str,
    ctx: Context[ServerSession, None],
) -> AmcacheResult:
    """Parse the Amcache.hve hive and return structured execution records.

    Input validation: hive_path MUST exist on the read-only evidence mount.
    Output is fully typed — no raw stdout returned to the agent.
    """
    if not hive_path.startswith("/evidence/"):
        raise ValueError("hive_path must be under /evidence/ (read-only mount)")

    await ctx.info(f"Parsing {hive_path}")
    # call AmcacheParser CLI, parse CSV server-side
    proc = subprocess.run(
        ["AmcacheParser", "-f", hive_path, "--csv", "/tmp/", "-c", case_id],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"AmcacheParser failed: {proc.stderr[:500]}")

    entries = _read_csv("/tmp/amcache.csv")  # server-side parse
    audit_id = _record_audit(case_id, "parse_amcache", hive_path, len(entries))
    return AmcacheResult(
        entries=entries,
        total=len(entries),
        case_id=case_id,
        audit_id=audit_id,
    )

if __name__ == "__main__":
    mcp.run()  # stdio transport
```

Key points:
- `@mcp.tool()` auto-generates both `inputSchema` and `outputSchema` from type hints + Pydantic.
- Async tools get a `Context` for progress reporting, logging back to the client, sampling.
- Return type is structured — the SDK serializes to JSON and wraps in a `TextContent` block for old clients.
- Errors surfaced as exceptions become `CallToolResult.isError = true` with the message.

**Long-running ops:**
```python
@mcp.tool()
async def run_super_timeline(image: str, ctx: Context, steps: int = 5) -> str:
    await ctx.info(f"log2timeline starting on {image}")
    for i in range(steps):
        await ctx.report_progress(progress=(i+1)/steps, total=1.0,
                                  message=f"plaso phase {i+1}/{steps}")
    return "/cases/timeline.plaso"
```

Experimental task API (`server.experimental.enable_tasks()`) for true async-with-cancel.

### C.3 Typed tools vs. shell exec — the security argument

This is **the** Protocol SIFT hackathon argument. Quoting the official rules: "The agent physically cannot run destructive commands because the server doesn't have those tools."

| Risk | Generic `execute_shell` tool | Typed MCP tools |
|---|---|---|
| `dd if=/dev/zero of=/evidence/disk.E01` | Allowed | Tool doesn't exist |
| `rm -rf /evidence/case01` | Allowed | Tool doesn't exist |
| Mount evidence rw | Allowed | Function only does `ro,noexec,noload` |
| Run wrong tool on wrong artifact | Allowed (hallucinated cmdline) | Schema rejects mismatched input |
| Spoliate by writing to evidence | Allowed | Server enforces read-only paths via input validation |
| Audit trail | Shell history (junky) | Structured per-call audit IDs |
| Reproducibility | Cmdline string | Typed args = reproducible by replay |

**Architectural guardrail** (server doesn't have the function) **>** prompt guardrail ("don't write to /evidence"). Judges score this directly under "Constraint Implementation."

### C.4 Error handling & long-running ops

- Exceptions inside tool handlers become `{ isError: true, content: [...] }` with the error message — the agent sees the failure and self-corrects (the "Ralph Wiggum Loop").
- `ctx.report_progress(progress, total, message)` for long ops; client can render progress bar.
- `ctx.info()` / `ctx.debug()` / `ctx.warning()` / `ctx.error()` send log notifications back during execution.
- Cancellation: stdio close or `CancelledRequest`. Experimental tasks API has formal task lifecycle.
- For long-running forensic ops (log2timeline can take an hour on a full disk), return a task handle and let the agent poll — don't block.

**Best practices for SIFT MCP design (synthesized from Anthropic's docs + Valhuntir reference):**

1. **One tool = one forensic action.** `parse_mft`, `parse_amcache`, `run_volatility(plugin=...)`. Not `do_forensics`.
2. **Pydantic-typed I/O.** Schema is the contract; agent can't pass a path where you expect a hash.
3. **Validate paths against an allowlist** (`/evidence/`, `/cases/<case_id>/`). Never accept arbitrary writes.
4. **Wrap responses in an envelope** with `audit_id`, `caveats` ("Amcache may report files that never executed"), `corroboration` (suggested next tools to confirm), `discipline_reminder` (a rotating forensic methodology hint). Valhuntir does this — it's clearly what wins.
5. **Server-side parse** of tool output. Don't return raw stdout. Parse to typed objects. (Forces the hallucination-resistant pattern Rob describes: "Claude runs tools and interprets verified output only.")
6. **Log every invocation** to a JSONL audit file with `(timestamp, tool, args, result_hash, audit_id)`. That's the audit trail the judges grade.
7. **Denylist of destructive commands** as defense-in-depth even though the architectural guardrail is the primary control.

---

## D. Agentic patterns — the architectures

### D.1 Direct Agent Extension (Claude Code / OpenClaw)

**What it is:** Take the existing Claude Code (or OpenClaw) agent loop, add better system prompts, slash commands, hooks, and a tool sequencing playbook. No new MCP server, no new framework. Maybe a `CLAUDE.md` that teaches the agent the SIFT chains from B.3.

**Pros:**
- Fastest path to demo (a weekend).
- Inherits Claude Code's tool use, agent loop, context compaction, plan mode.
- Plays well with the hackathon's "preferred frameworks: Claude Code, OpenClaw" guidance.

**Cons:**
- Guardrails are **prompt-based** ("don't run rm"). Judges explicitly penalize this under Constraint Implementation.
- Limited audit-trail differentiation — you get Claude Code's hooks, but not typed-call provenance.
- Risk of being seen as "just a prompt" not architecture.

**Score profile:** good on Usability + Autonomous Execution, weak on Constraint, OK on Audit (hooks log Bash).

### D.2 Custom MCP Server — the winning pattern

**What it is:** Build a Python MCP server with 20–50 typed tools wrapping the SIFT toolkit. The agent (Claude Code, Claude Desktop, Cherry Studio — any MCP client) invokes those typed tools only. Generic shell is removed or denylisted.

**This is the explicit winning architecture per the rules: "the most sound architecture in the evaluation."**

Reference implementation already exists: **[AppliedIR/sift-mcp (Valhuntir)](https://github.com/AppliedIR/sift-mcp)** — 11-package monorepo, 8 MCP backends, 90+ tools, gateway, Examiner Portal, audit ledger, HMAC-signed findings. Architecture by Steve Anson, implementation by Claude Code. **This is the bar to beat or remix.**

Key Valhuntir patterns worth stealing:
- Response envelope with `success / data / audit_id / examiner / caveats / advisories / corroboration / discipline_reminder`.
- Provenance tiers: MCP (system-witnessed) > HOOK (Claude Code logged) > SHELL (self-reported) > NONE (rejected).
- Examiner Portal: 8-tab UI for review/approve (Findings, Timeline, Hosts, Accounts, Evidence, IOCs, TODOs, Overview).
- HMAC-signed findings + PBKDF2-derived key for tamper detection.
- Sandbox: bubblewrap kernel isolation + 41 deny rules + PreToolUse hook guard.
- LLM-agnostic — same server works with Claude Code, Claude Desktop, LibreChat.

**Pros:**
- Architectural guardrails win Constraint criterion.
- Typed audit trail wins Audit criterion.
- Reproducible by other practitioners (deploy server, point any MCP client at it) wins Usability.
- "We physically can't spoliate" is a one-liner the judges will remember.

**Cons:**
- More work than Direct Extension (week+ for a credible 20-tool server).
- Tool selection is its own design problem — pick wrong tools, lose IR Accuracy.

**Score profile:** strong on every criterion except possibly Breadth (you have to cover enough tools).

### D.3 Multi-Agent frameworks (AutoGen / CrewAI / LangGraph)

**What it is:** Specialist agents (Memory Specialist, Disk Specialist, Network Specialist, Log Hunter, Synthesizer). Each has its own context window, prompt, and (ideally) its own MCP server scoped to its domain. A coordinator routes work and merges findings.

**Framework deep dives (current 2026 state):**

| Framework | Strength | Weakness | Verdict for Protocol SIFT |
|---|---|---|---|
| **LangGraph (LangChain)** v0.4 | Stateful graph-based orchestration. First-class persistence (checkpointers), HITL, time travel, streaming. Production-grade. | Verbose; you write the graph yourself. | Best for a credible multi-agent submission — checkpoints become audit trail |
| **CrewAI** | Role-based ("you are the memory specialist"), backstories, quick to set up. Now has enterprise observability + scheduling. | Coordination is inferred — black-box for audit. Less control over message flow. | Fast to prototype but harder to defend on Constraint/Audit |
| **AutoGen / AG2** v1.0 GA (2026) | Event-driven, async-first, GroupChat coordination. Microsoft-backed. | More machinery; bigger surface area. | Solid if you want true async + pluggable orchestration |

**Pros:**
- Each agent's context stays small — better long-investigation scaling.
- Specialization arguably maps to senior-analyst mental model (network guy vs. memory guy).
- Inter-agent message logs are excellent audit evidence (judges explicitly require these for multi-agent submissions).

**Cons:**
- Infinite loop risk — judges require explicit max-iteration caps.
- Coordination overhead can degrade execution quality.
- You're still on top of an MCP layer (or generic shell) — multi-agent doesn't replace D.2, it sits on it. Best when *combined*.

**Score profile:** can win Breadth + Audit if combined with D.2. Risky if standalone over generic shell.

### D.4 Alternative agentic IDEs (Cursor / Cline / Aider)

**What it is:** Use Cursor or Cline as the agent shell, drive SIFT tools via integrated terminal or MCP.

**Hackathon rules verbatim:** "rely on prompt adherence for evidence protection, not architectural enforcement." **Explicitly weaker on Constraint.**

UI/UX is great for live demo, but no agent-loop control, no audit-trail guarantees, no constraint architecture. Use only if it's your day job tooling and you'll lose less time than learning Claude Code.

### D.5 Framework deep dives

**Claude Code SDK (Agent SDK as of late 2025):**
- Renamed from "Claude Code SDK" to "Agent SDK" to reflect broader use.
- Python + TypeScript. Same agent loop, tool use, context management as Claude Code.
- Four primitives: **tools, hooks, MCP servers, subagents**.
- MCP-native — pass `mcp_servers` dict; just works.
- Subagents = specialized agents with own context window, prompt, tool perms — main agent delegates and integrates.
- **Hooks** (PreToolUse, PostToolUse, Stop, etc.) — perfect for forensic audit (every Bash → JSONL with timestamps).
- Starting June 15, 2026, Agent SDK + `claude -p` usage on subscription plans draws from a new monthly Agent SDK credit, separate from interactive limits — **relevant to hackathon timing.**

**OpenClaw:**
- **Real project**, openclaw.ai + github.com/mergisi/awesome-openclaw-agents (200+ templates).
- **Config-first, no-code**: agents defined as **`SOUL.md`** markdown files declaring persona, capabilities, MCP tools, channels (Telegram/Slack/Discord/email), rules.
- Node.js runtime, ~150MB binary, ~512MB RAM. Local gateway on port `18789`.
- Multi-agent built in — spin up many specialized agents with isolated memory.
- Model-agnostic: Claude, GPT-4o, Gemini, local Ollama.
- Lifecycle: write SOUL.md → `openclaw agents add` → `openclaw gateway start`.
- Strong for a non-coder building specialized DFIR agents fast. Weaker for hard architectural guardrails (still depends on MCP-typed tools underneath).
- **Why SANS named it alongside Claude Code:** quickest path for a non-engineer DFIR pro to ship a credible multi-agent setup.

**AutoGen vs CrewAI vs LangGraph (quick framing for our use case):**
- **LangGraph** = pick this if you want production-shape stateful graphs with replayable checkpoints. Best audit story.
- **AutoGen / AG2** = pick this if you want event-driven async with formal GroupChat.
- **CrewAI** = pick this only if you need to ship the multi-agent demo in 48 hours and can defend a black-box coordinator.

### D.6 Pattern vs. judging criteria matrix

Scores: ✓✓✓ strong / ✓✓ ok / ✓ weak / ✗ penalty.

| Pattern | Autonomous Exec | IR Accuracy | Breadth | Constraint | Audit Trail | Usability |
|---|---|---|---|---|---|---|
| D.1 Direct Extension (Claude Code/OpenClaw + prompts) | ✓✓ | ✓✓ | ✓✓ | ✗ (prompt-based) | ✓✓ (hooks) | ✓✓✓ |
| D.2 Custom MCP Server (Valhuntir-shape) | ✓✓✓ | ✓✓✓ | ✓✓ (depends on tool count) | ✓✓✓ (architectural) | ✓✓✓ (typed) | ✓✓ (more setup) |
| D.3 Multi-Agent over MCP (D.2 + LangGraph) | ✓✓✓ | ✓✓✓ | ✓✓✓ | ✓✓✓ | ✓✓✓ (msg logs) | ✓ (complexity) |
| D.3 Multi-Agent over shell | ✓✓ | ✓ (no validation layer) | ✓✓ | ✗ | ✓✓ | ✓ |
| D.4 Alternative IDE (Cursor/Cline) | ✓✓ | ✓✓ | ✓✓ | ✗ (rules call this out) | ✓ | ✓✓✓ |

**The dominant pattern is D.2, optionally layered with D.3 (LangGraph or Agent SDK subagents) for breadth.** That's the path that scores ✓✓✓ on the heavy criteria — Autonomous Execution, IR Accuracy, Constraint, Audit Trail — which together drive the placing.

---

## Appendix: Sources

- SIFT Workstation: https://www.sans.org/tools/sift-workstation
- teamdfir/sift: https://github.com/teamdfir/sift
- teamdfir/sift-saltstack: https://github.com/teamdfir/sift-saltstack
- SIFT tool list (community): https://github.com/angeling11/SIFT-workstation-tools
- SANS Hunt Evil poster: https://www.sans.org/posters/hunt-evil
- SANS SIFT cheat sheet: https://www.sans.org/posters/sift-cheat-sheet
- Find Evil hackathon on Devpost: https://findevil.devpost.com/
- SANS launch blog: https://www.sans.org/blog/sans-launches-first-hackathon-autonomous-incident-response
- Rob T. Lee, "Introducing Protocol SIFT": https://robtlee73.substack.com/p/introducing-protocol-sift-meeting
- Rob T. Lee, "Find Evil: era of autonomous forensics": https://robtlee73.substack.com/p/dangerous-new-attack-techniques-rsac-2026-preview-protocol-sift
- AppliedIR Valhuntir / sift-mcp: https://github.com/AppliedIR/sift-mcp
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Anthropic Agent SDK (formerly Claude Code SDK): https://code.claude.com/docs/en/agent-sdk/overview
- Anthropic building agents post: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk
- OpenClaw: https://openclaw.ai/
- awesome-openclaw-agents: https://github.com/mergisi/awesome-openclaw-agents
- Volatility 3: https://github.com/volatilityfoundation/volatility3
- plaso/log2timeline: https://github.com/log2timeline/plaso
- Eric Zimmerman tools: https://ericzimmerman.github.io/
- SANS "Running EZ Tools on Linux": https://www.sans.org/blog/running-ez-tools-natively-on-linux-a-step-by-step-guide
- Hayabusa: https://github.com/Yamato-Security/hayabusa
- Chainsaw: https://github.com/WithSecureLabs/chainsaw
- RegRipper: https://github.com/keydet89/RegRipper3.0
- Velociraptor: https://docs.velociraptor.app/
- Zeek: https://zeek.org/
- Suricata: https://suricata.io/
- RFC 3227 (Order of Volatility): https://www.rfc-editor.org/rfc/rfc3227.html
- NIST SP 800-61r2 IR lifecycle: https://csrc.nist.gov/pubs/sp/800/61/r2/final
- MITRE ATT&CK: https://attack.mitre.org/
- Pyramid of Pain (David Bianco): https://detect-respond.blogspot.com/2013/03/the-pyramid-of-pain.html
- LangGraph/CrewAI/AutoGen 2026 comparison: https://pecollective.com/blog/ai-agent-frameworks-compared/
