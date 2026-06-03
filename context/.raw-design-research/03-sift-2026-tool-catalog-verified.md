# SIFT Workstation 2026 — Verified Tool Catalog

> **Sources (cloned `--depth 1` 2026-06-02):**
> - `teamdfir/sift-saltstack` HEAD (VERSION file = `v2020.01.01-rc1`, but actively maintained — `claude-code.sls` v2.0.61 is recent)
> - `teamdfir/sift-packer` HEAD (`variables.pkr.hcl` line 38–41: `ubuntu_version = "24.04.2"`)
> - `sans-dfir/sift` README (metadata repo only)
> - `protocol-sift-2026` research notes (`02-sponsor-docs.md` Valhuntir tool inventory)
>
> All `[verified]` entries cite the exact `.sls` file. `[unverified]` = inferred, not in repo. Where a `.sls` is committed, the tool **is installed** when `cast install --mode=desktop` runs.

---

## Base platform

| Field | Value | Source |
|---|---|---|
| Distro | **Ubuntu 24.04.2 LTS (Noble)** | `sift-packer/variables.pkr.hcl:38–41` `default = "24.04.2"` |
| Architecture | amd64 default; arm64 supported | `variables.pkr.hcl:31–35` + branching in `radare2.sls`, `claude-code.sls`, `aws-cli.sls` |
| Default user | **`sansforensics`** | `variables.pkr.hcl:19–23` + `sans-dfir/sift/README.md` |
| Default password | `forensics` | `variables.pkr.hcl:25–29` |
| Default Python | **Python 3.12** (Noble system Python) | `python3.sls` installs `python3` + `python-is-python3`; `indxparse.sls:11–13` confirms `oscodename == 'noble'` → `py_ver = '3.12'`; `python-evtx.sls:11–15` same |
| Jammy fallback Python | 3.10 (legacy, deprecated path still in code) | `indxparse.sls:9–10`, `python-evtx.sls:13–14` |
| Default package manager | **pip + virtualenv** (NOT uv) — every Python tool uses `virtualenv.managed` to `/opt/<tool>/bin/python3` + `pip.installed` | e.g. `python3-packages/volatility3.sls:14–38`, `mvt.sls:14–31`, `hindsight.sls`, `analyzemft.sls` |
| Pip baseline pin | `pip>=24.1.3`, `setuptools>=70.0.0`, `wheel>=0.38.4` in every venv | repeated across all `python3-packages/*.sls` |
| **Node.js** | **NOT installed** (no `nodejs.sls` exists in repo) | grep of `/tmp/sift-saltstack-research/sift/` returns no match for `nodejs` outside of `pdfid.py` doc comment |
| Docker daemon | **Pre-installed** (docker-ce from official Docker repo) | `packages/docker.sls:13–17`, `repos/docker.sls` |
| docker-compose | v2.32.4 binary in `/usr/local/bin/docker-compose` | `scripts/docker-compose.sls:1` `version = "2.32.4"` |
| Apache2 | **Pre-installed** (used by CyberChef static-host at `/var/www/html/cyberchef`) | `packages/apache2.sls`, `scripts/cyberchef.sls:7–18` |
| nginx | **NOT installed** | no `.sls` in repo |
| .NET SDK | **dotnet-sdk-9.0** pre-installed (for EZ Tools) | `packages/dotnet.sls:5` `pkg.installed: dotnet-sdk-9.0`; repo: `repos/dotnet-backports.sls` (PPA `dotnet/backports`) |
| Claude Code CLI | **v2.0.61** pre-installed at `/usr/local/bin/claude` | `packages/claude-code.sls:1–17` (this is a recent addition — strong signal SIFT 2026 ships for AI-agent dev) |
| PowerShell | **7.4.6** pre-installed (amd64 only) | `packages/powershell.sls:9–11` `version = "7.4.6"` |
| AWS CLI | **2.15.24** pre-installed | `packages/aws-cli.sls:9–10` `version = '2.15.24'` |
| Java | OpenJDK default-jre pre-installed (Autopsy dep) | `packages/openjdk.sls`, `packages/default-jre.sls` |
| Wine | Pre-installed (Windows binary support) | `packages/wine.sls` |
| Cast installer | v0.16.0-next.6 (used at provisioning, not for runtime) | `sift-packer/custom_scripts/cast-install.sh:3` |

---

## Pre-installed forensic tools (authoritative — from `sift-saltstack` states)

> Every row below is a committed `.sls` file. The `--mode=desktop` cast install pulls all of `sift.packages.init`, `sift.python3-packages.init`, and `sift.scripts.init`.

### Memory analysis
| Tool | Version | Install method | Path | Source `.sls` |
|---|---|---|---|---|
| **Volatility 3** | `volatility3` latest from pip (`upgrade: True`) | virtualenv at `/opt/volatility3` + symlinks `vol`, `volshell` → `/usr/local/bin/` | `/opt/volatility3/bin/vol` (symlinked `/usr/local/bin/vol`, `/usr/local/bin/volshell`) | `python3-packages/volatility3.sls:14–48` |
| Volatility 3 deps (in venv) | yara-python>=4.5.1<5, pycryptodome>=3.21<4, capstone>=5.0.3<6, leechcorepyc>=2.19.2<3, pillow>=10<11, pefile>=2024.8.26, yara-x | pip in venv | `/opt/volatility3/lib/python3.12/site-packages/` | `python3-packages/volatility3.sls:18–28` |
| Memory Baseliner | [unverified] not in saltstack — Valhuntir docs claim it's on SIFT; no `.sls` | — | — | — |
| winpmem | [unverified] not in saltstack | — | — | — |

> **Note re `02-sponsor-docs.md` claim of `/opt/volatility3-2.20.0/vol.py`:** the saltstack installs at **`/opt/volatility3/`** (no version suffix). Either the Valhuntir reference is outdated or refers to an older SIFT — our MCP must invoke `/opt/volatility3/bin/vol` or rely on the `/usr/local/bin/vol` symlink.

### Timeline / plaso
| Tool | Version | Install method | Path | Source `.sls` |
|---|---|---|---|---|
| **plaso-tools** (log2timeline.py, psort.py, psteal.py, pinfo.py) | `pkg.latest` from `ppa:gift/stable` | apt | `/usr/bin/log2timeline.py`, `/usr/bin/psort.py`, `/usr/bin/psteal.py` | `packages/plaso-tools.sls:12–16` + `repos/gift.sls` |
| python3-plaso | apt latest from gift PPA | apt | system site-packages | `packages/python3-plaso.sls:11–27` |
| python3-dfvfs | apt latest from gift PPA | apt | system | `packages/python3-dfvfs.sls:4–13` |

### Disk / filesystem
| Tool | Version | Install method | Path | Source `.sls` |
|---|---|---|---|---|
| Sleuth Kit (mmls, fls, icat, istat, tsk_recover, mactime, blkls, blkcat) | apt latest from Noble | apt `sleuthkit` | `/usr/bin/` | `packages/sleuthkit.sls:1–3` |
| libewf2 / libewf-dev / libewf-python3 / ewf-tools (ewfacquire, ewfmount, ewfverify, ewfinfo) | apt from gift PPA | apt | `/usr/bin/ewf*` | `packages/libewf*.sls`, `packages/ewf-tools.sls:1–10` |
| afflib-tools | apt | apt | `/usr/bin/` | `packages/afflib-tools.sls` |
| libbde / libbde-tools (BitLocker) | apt from gift PPA | apt | system | `packages/libbde.sls`, `packages/libbde-tools.sls` |
| libvshadow / libvshadow-dev / libvshadow-tools / libvshadow-python3 (VSS) | apt from gift PPA | apt | `/usr/bin/vshadow*` | `packages/libvshadow*.sls` |
| libvmdk | apt from gift PPA | apt | system | `packages/libvmdk.sls` |
| libfvde / libfvde-tools (FileVault2) | apt from gift PPA | apt | system | `packages/libfvde*.sls` |
| libfsapfs-tools (APFS) | apt from gift PPA | apt | system | `packages/libfsapfs-tools.sls` |
| libregf / libregf-tools / libregf-python3 (registry) | apt from gift PPA | apt | system | `packages/libregf*.sls` |
| libesedb / libesedb-tools (ESE/EDB) | apt from gift PPA | apt | system | `packages/libesedb*.sls` |
| libevt / libevt-tools / libevtx / libevtx-tools (event logs) | apt from gift PPA | apt | `/usr/bin/evtxexport` etc. | `packages/libevt*.sls`, `packages/libevtx*.sls` |
| libpff / libpff-dev / pff-tools (PST/OST) | apt from gift PPA | apt | system | `packages/libpff*.sls`, `packages/pff-tools.sls` |
| libmsiecf / libolecf | apt from gift PPA | apt | system | `packages/libmsiecf.sls`, `packages/libolecf.sls` |
| pytsk3 (python3-pytsk3) | apt from gift PPA | apt | system Python | `packages/python3-pytsk3.sls` |
| dc3dd / dcfldd / gddrescue / safecopy | apt | apt | `/usr/bin/` | `packages/dc3dd.sls` etc. |
| testdisk / photorec | apt (`testdisk` package ships both) | apt | `/usr/bin/` | `packages/testdisk.sls` |
| disktype, hashdeep, dislocker, xmount | apt | apt | `/usr/bin/` | respective `.sls` |
| imagemounter (`imount`) | pip in venv | `/opt/imagemounter/bin/imount` → `/usr/local/bin/imount` | symlink | `python3-packages/imagemounter.sls:69–84` |

### Carving / strings
| Tool | Version | Install method | Source `.sls` |
|---|---|---|---|
| bulk_extractor | apt from sift PPA + openjdk repo | apt | `packages/bulk-extractor.sls:13–18` |
| foremost | apt | apt | `packages/foremost.sls` |
| scalpel | apt | apt | `packages/scalpel.sls` |
| photorec | bundled with `testdisk` package | apt | `packages/testdisk.sls` |
| bstrings | via EZ Tools | dotnet wrapper | `scripts/zimmerman.sls:9` |

### Registry / Windows artifacts
| Tool | Version | Install method | Path | Source `.sls` |
|---|---|---|---|---|
| **RegRipper3.0** | latest `master` of `keydet89/RegRipper3.0` (git pull) | git clone to `/usr/local/src/regripper`, copies to `/usr/share/regripper/rip.pl`, symlink `/usr/local/bin/rip.pl` | **`/usr/local/bin/rip.pl`** (plugins at `/usr/share/regripper/plugins/`) | `scripts/regripper.sls:13–162` |
| Parse::Win32Registry perl | apt | apt | system | `packages/libparse-win32registry-perl.sls` |
| AnalyzeMFT | commit `b1d0e6a0aa58d42000bfdb8e6588513bd62eaeab` pinned | git+pip in venv → `/opt/analyzemft/bin/analyzemft` → `/usr/local/bin/analyzemft` | symlink | `python3-packages/analyzemft.sls:9, 26–41` |
| python-evtx | commit `1a1357accd3a75524794a6d6dcdec03c09e1660d` pinned | git+pip in venv `/opt/python-evtx/` → symlinks `evtx_dump.py`, `evtx_dump_json.py`, etc. | `/usr/local/bin/evtx_*.py` | `python3-packages/python-evtx.sls:10, 21–60` |
| INDXParse (10 scripts) | commit `038e8ec836cf23600124db74b40757b7184c08c5` | git+pip in venv `/opt/indxparse/` → symlinks `INDXParse.py`, `MFTINDX.py`, `MFTView.py`, `tree_mft.py`, etc. | `/usr/local/bin/` | `python3-packages/indxparse.sls:14, 48–65` |
| amcache.py (Willi Ballenthin) | apt + bundled file from saltstack `files/amcache` | venv `/opt/amcache/` → `/usr/local/bin/amcache.py` | `/usr/local/bin/amcache.py` | `scripts/amcache.sls:24–46` |
| usnparser | latest from `digitalsleuth/USN-Journal-Parser` | venv `/opt/usnparser/` → `/usr/local/bin/usnparser` | `/usr/local/bin/usnparser` | `python3-packages/usnparser.sls:23–37` |
| keydet89 Perl tools (`bodyfile.pl, evtparse.pl, evtxparse.pl, fb.pl, ff.pl, idx.pl, idxparse.pl, jl.pl, lnk.pl, mft.pl, parsei30.pl, parseie.pl, pref.pl, recbin.pl, regslack.pl, regtime.pl, rfc.pl, rlo.pl, tln.pl, usnj.pl` + 28 total) | latest `master` git | git clone `/usr/local/src/keydet-tools` + copy to `/usr/local/bin/*.pl` | `/usr/local/bin/*.pl` | `scripts/keydet-tools.sls:4, 9–37` |
| dump-mft-entry.pl | commit `ee681a07a0c32a5ccaea788cd7d012d19872f181` | direct download | `/usr/local/bin/dump-mft-entry.pl` | `scripts/dump-mft-entry.sls:4–13` |
| 4n6-scripts (Cheeky4N6Monkey) — 30+ Python/Perl utilities | latest `master` git | venv `/opt/4n6-scripts/` + symlinks to `/usr/local/bin/` for `.py` files; perl `.pl` files directly copied | `/usr/local/bin/` | `scripts/4n6.sls:9–105` |
| windowsprefetch (Python) | pip | venv | `python3-packages/windowsprefetch.sls` (file present) |
| pe-carver, pe-scanner, packerid | pip in venvs | `/opt/pe-carver`, `/opt/pe-scanner` | `python3-packages/pe-carver.sls`, `pe-scanner.sls`, `scripts/packerid.sls` |
| python3-pefile | apt | apt | system | `packages/python3-pefile.sls:1–3` |

### EZ Tools (Eric Zimmerman) — **PRE-INSTALLED via dotnet 9**
| Tool | Install path | Wrapper |
|---|---|---|
| AmcacheParser | `/opt/zimmermantools/AmcacheParser.dll` | `/usr/local/bin/AmcacheParser` and `/usr/local/bin/amcacheparser` (lower-cased) |
| AppCompatCacheParser | `/opt/zimmermantools/AppCompatCacheParser.dll` | `/usr/local/bin/AppCompatCacheParser` + lowercase |
| bstrings | `/opt/zimmermantools/bstrings.dll` | `/usr/local/bin/bstrings` |
| **EvtxECmd** | `/opt/zimmermantools/EvtxeCmd/EvtxECmd.dll` (special-cased — note inner `EvtxeCmd/` dir) | `/usr/local/bin/EvtxECmd` + lowercase |
| iisGeolocate | `/opt/zimmermantools/iisGeolocate/iisGeolocate.dll` | `/usr/local/bin/iisGeolocate` + lowercase |
| JLECmd (Jump List) | `/opt/zimmermantools/JLECmd.dll` | `/usr/local/bin/JLECmd` + lowercase |
| LECmd (LNK) | `/opt/zimmermantools/LECmd.dll` | `/usr/local/bin/LECmd` + lowercase |
| **MFTECmd** | `/opt/zimmermantools/MFTECmd.dll` | `/usr/local/bin/MFTECmd` + lowercase |
| RBCmd (Recycle Bin) | `/opt/zimmermantools/RBCmd.dll` | `/usr/local/bin/RBCmd` + lowercase |
| RecentFileCacheParser | `/opt/zimmermantools/RecentFileCacheParser.dll` | `/usr/local/bin/RecentFileCacheParser` + lowercase |
| RECmd (Registry) | `/opt/zimmermantools/RECmd/RECmd.dll` | `/usr/local/bin/RECmd` + lowercase |
| rla | `/opt/zimmermantools/rla.dll` | `/usr/local/bin/rla` |
| SBECmd (Shellbag Explorer) | `/opt/zimmermantools/SBECmd.dll` | `/usr/local/bin/SBECmd` + lowercase |
| SQLECmd | `/opt/zimmermantools/SQLECmd/SQLECmd.dll` | `/usr/local/bin/SQLECmd` + lowercase |
| WxTCmd (Win10 Timeline) | `/opt/zimmermantools/WxTCmd.dll` | `/usr/local/bin/WxTCmd` + lowercase |

Source: `scripts/zimmerman.sls:9, 14–50`. Download base: `https://download.ericzimmermanstools.com/net9/<tool>.zip`. Wrappers always invoke `dotnet /opt/zimmermantools/<tool>.dll ${*}`.

> **EZ Tools NOT in the saltstack list (despite Valhuntir's claim):** `PECmd`, `SrumECmd`, `srum-dump`. These must be added by us if needed. (Valhuntir's `02-sponsor-docs.md` lists `PECmd, SrumECmd` — they are **missing** from `scripts/zimmerman.sls:9`.)

### Malware triage
| Tool | Version | Install method | Path | Source `.sls` |
|---|---|---|---|---|
| YARA (libyara3 + python3-yara) | apt | apt | `/usr/bin/yara`, system Python `yara` | `packages/libyara3.sls`, `packages/python3-yara.sls:5–8` |
| yara-python (Volatility venv only) | 4.5.1≤x<5 | pip in volatility3 venv | `/opt/volatility3/lib/python3.12/site-packages/yara` | `python3-packages/volatility3.sls:22` |
| yara-x (in vol3 venv) | latest | pip | venv-scoped | `python3-packages/volatility3.sls:28` |
| ClamAV | apt latest | apt | `/usr/bin/clamscan`, `/usr/bin/freshclam` | `packages/clamav.sls:9–10` |
| ssdeep | apt | apt | `/usr/bin/ssdeep` | `packages/ssdeep.sls` |
| upx-ucl | apt | apt | `/usr/bin/upx` | `packages/upx-ucl.sls` |
| radare2 | **5.9.6** (pinned via dpkg from GitHub release deb) | `dpkg -i` | `/usr/bin/r2` | `packages/radare2.sls:2` |
| pev | apt | apt | `/usr/bin/pev` | `packages/pev.sls` |
| densityscout | build 45 from CERT.at zip | extract + symlink | `/usr/local/bin/densityscout` | `scripts/densityscout.sls:4, 14–30` |
| exiftool | latest (fetched live at install from exiftool.org) | perl install | `/usr/local/bin/exiftool` | `scripts/exiftool.sls:9–48` |
| pdf-tools (Didier Stevens — pdfid.py, pdf-parser.py, make-pdf-*.py + plugins) | bundled in saltstack `files/pdf-tools` | venv `/opt/pdf-tools/` + symlinks | `/usr/local/bin/pdfid.py`, `/usr/local/bin/pdf-parser.py`, etc. | `scripts/pdf-tools.sls:9, 25–39` |
| **capa** | [unverified — NOT in saltstack] | — | — | absent from `packages/init.sls`, `scripts/init.sls`, `python3-packages/init.sls` |
| **FLOSS** | [unverified — NOT in saltstack] | — | — | absent |
| **binwalk** | [unverified — NOT in saltstack] | — | — | absent (no `.sls`); may install via apt on Noble manually |
| moneta / hollows_hunter / sigcheck / 1768_cobalt | [unverified — NOT in saltstack] (Windows-native; Valhuntir lists but they don't run on Linux without Wine) | — | — | absent |

### Network forensics
| Tool | Version | Install method | Path | Source `.sls` |
|---|---|---|---|---|
| Wireshark / tshark | apt latest | apt | `/usr/bin/wireshark`, `/usr/bin/tshark` | `packages/wireshark.sls:1–3` |
| tcpdump | implicit dependency of net packages, [unverified standalone .sls] — `packages/net-tools.sls` ships net-tools | apt | `/usr/bin/tcpdump` | apt default Ubuntu |
| tcpflow, tcpick, tcpreplay, tcpslice, tcpstat, tcptrace, tcptrack, tcpxtract | apt | apt | `/usr/bin/` | individual `packages/tcp*.sls` |
| ngrep, netsed, netwox, nfdump, ssldump, sslsniff, stunnel4 | apt | apt | `/usr/bin/` | individual `.sls` |
| etherape, ettercap-graphical, driftnet, dsniff | apt | apt | `/usr/bin/` | individual `.sls` |
| p0f, nbtscan, arp-scan, nikto, hydra, aircrack-ng | apt | apt | `/usr/bin/` | individual `.sls` |
| **Zeek** | **NOT installed** | — | — | no `.sls` |
| **Suricata** | **NOT installed** | — | — | no `.sls` |
| **NetworkMiner** | **NOT installed** | — | — | no `.sls` |

### Threat hunting (Sigma/EDR)
| Tool | Status |
|---|---|
| **Hayabusa** | **NOT installed** (no `.sls`) — Valhuntir installs it themselves; SIFT base does not ship it |
| **Chainsaw** | **NOT installed** (no `.sls`) |
| **Velociraptor** (server or client) | **NOT installed** (no `.sls`) |
| Sigma rules corpus | **NOT shipped** as a system package |

### Browser forensics
| Tool | Version | Install method | Path | Source `.sls` |
|---|---|---|---|---|
| hindsight (pyhindsight) | latest pip + `ccl_chromium_reader` from CCL Group git | venv `/opt/pyhindsight/` → symlinks | `/usr/local/bin/hindsight.py`, `/usr/local/bin/hindsight_gui.py` | `python3-packages/hindsight.sls:11, 28–51` |
| chromium-browser | apt | apt | `/usr/bin/chromium-browser` | `packages/chromium-browser.sls` |
| BrowsingHistoryView | [unverified — NOT in saltstack] | — | — | absent |

### Mobile
| Tool | Version | Install | Path |
|---|---|---|---|
| mvt (mvt-android, mvt-ios) | latest pip | venv `/opt/mvt/` → symlinks | `/usr/local/bin/mvt-android`, `/usr/local/bin/mvt-ios` | `python3-packages/mvt.sls:7, 25–42` |
| android-sdk-platform-tools | apt | apt | `/usr/bin/adb` | `packages/android-sdk-platform-tools.sls` |
| ufade | pip in venv | venv | `python3-packages/ufade.sls` |

### Other notable (alphabetical)
| Tool | Pre-installed? | Source |
|---|---|---|
| autopsy | YES (apt) | `packages/autopsy.sls:9–10` |
| cabextract, ccrypt | YES | `.sls` files exist |
| **CyberChef** | YES, v9.55.0 served from Apache at `/var/www/html/cyberchef/index.html` | `scripts/cyberchef.sls:5–24` |
| Docker | YES | `packages/docker.sls` |
| dotnet-sdk-9.0 | YES | `packages/dotnet.sls` |
| ghex, hexedit, bless, vbindiff | YES | individual `.sls` |
| ipython3 | YES | `packages/ipython3.sls` |
| Java idx-parser (Python) | YES (venv) | `python3-packages/java-idx-parser.sls` |
| machinae (threat-intel CLI) | YES (venv) | `python3-packages/machinae.sls` |
| mac-apt | YES (venv) | `python3-packages/mac-apt.sls` |
| page-brute | YES (venv) | `python3-packages/page-brute.sls` |
| sqlite-carver | YES (venv) | `python3-packages/sqlite-carver.sls` |
| stix-validator | YES (venv) | `python3-packages/stix-validator.sls` |
| usbdeviceforensics | YES (venv) | `python3-packages/usbdeviceforensics.sls` |
| ioc-writer | YES (venv) | `python3-packages/ioc-writer.sls` |
| defang | YES (venv) | `python3-packages/defang.sls` |
| vim, htop, jq, curl, build-essential, gcc, g++, gdb, git, perl, qemu, qemu-utils | YES — all standard SIFT base | individual `.sls` |

---

## Tools NEEDED but NOT pre-installed

> These are the tools Valhuntir / Protocol SIFT reference but SIFT 2026 base **does not ship**. Our MCP server install script must add them (or our MCP must gracefully degrade).

| Tool | Reason needed | Install method | License |
|---|---|---|---|
| **Hayabusa** | Sigma-rule-driven evtx hunting (Valhuntir auto-runs 3,700 rules; CONTEXT.md references for our investigator) | `wget` release binary from `Yamato-Security/hayabusa` GitHub Releases → drop in `/opt/hayabusa/`. Single Rust static binary. | GPL-3.0 |
| **Chainsaw** | Faster Sigma + custom hunt rules across evtx/MFT/SRUM | `wget` release binary from `WithSecureLabs/chainsaw` GitHub Releases → `/opt/chainsaw/`. Single Rust static binary. | GPL-3.0 |
| **Zeek** | Network protocol parsing for pcap-driven investigations | `apt install zeek` after adding `https://download.opensuse.org/repositories/security:/zeek/` repo, OR build from source | BSD-3-Clause |
| **Suricata** | IDS rule-driven detection on pcap | `apt install suricata` (Noble has it in universe) | GPL-2.0 |
| **Velociraptor** (client + optional server) | Live-host triage MCP wrapping (one of our wedges) | `wget` single-binary from `Velocidex/velociraptor` GitHub Releases → `/opt/velociraptor/velociraptor` | AGPL-3.0 |
| **capa** | PE behavioral classification | `pipx install flare-capa` or wget release binary | Apache-2.0 |
| **FLOSS** | Obfuscated string extraction | wget release binary from `mandiant/flare-floss` | Apache-2.0 |
| **binwalk** | Firmware/embedded carving | `apt install binwalk` (in Noble universe) | MIT |
| **PECmd** (EZ Tool) | Prefetch parsing — **missing from SIFT 2026 zimmerman.sls list** | add to `scripts/zimmerman.sls` tools array (same .NET wrapper pattern) | MIT |
| **SrumECmd** (EZ Tool) | SRUM parsing — also missing | same as above | MIT |
| **srum-dump** | Alternative SRUM parser | pip install | Apache-2.0 |
| **Node.js + npm** | Required if we ship any TS/JS code or use OpenClaw | `apt install nodejs npm` (Noble has 18.x LTS) or `nvm` for 20+ | MIT-ish |
| **uv** (Python package manager) | If we want faster reproducible Python deps than pip | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (we install — SIFT does NOT ship it) | MIT/Apache-2.0 |
| **Hayabusa Sigma rules** | The actual rule corpus | `git clone https://github.com/Yamato-Security/hayabusa-rules /opt/hayabusa-rules` | Apache-2.0 |
| **Chainsaw Sigma/custom rules** | Hunt rules | `git clone https://github.com/SigmaHQ/sigma /opt/sigma` | Apache-2.0 |

---

## Tools commonly added by community / observed in references

| Tool | Adoption signal | Install method |
|---|---|---|
| KAPE (Kroll Artifact Parser/Extractor) | Mentioned by Valhuntir/Protocol SIFT — but Windows-only binary; runs under Wine on SIFT. **Not in saltstack** | manual zip from Kroll site; license restricts redistribution |
| jupyter / jupyterlab | Not in saltstack; common addition for notebook-driven analysis | `pip install jupyterlab` |
| OpenSearch + OpenSearch Dashboards | Valhuntir's `opensearch-mcp` uses them; **not in saltstack** | docker-compose |
| OpenCTI | Valhuntir `opencti-mcp`; not in saltstack | docker-compose |
| Sigma CLI | Used for compiling Sigma rules; not in saltstack | `pip install sigma-cli` |
| YARA-X CLI | The standalone yara-x binary (vs. embedded lib); only embedded version ships in vol3 venv | `cargo install yara-x-cli` |
| memprocfs / leechcorepyc CLI | Bundled in vol3 venv as Python lib; CLI not standalone | already present in vol3 venv |
| Volatility 2 | **Deprecated, not in saltstack** | pip if needed (Python 2 not present) |
| python3-magic | YES (apt) — confirms `python3-magic.sls` ships system-wide | `packages/python3-magic.sls` |

---

## Implications for our MCP server deployment

### Tools we can ASSUME present (no install step)
- All Sleuth Kit utilities (`mmls`, `fls`, `icat`, `istat`, `tsk_recover`, `mactime`, `blkls`)
- `vol`, `volshell` (Volatility 3, at `/usr/local/bin/vol` — backed by `/opt/volatility3/` venv on Python 3.12)
- All plaso CLIs (`log2timeline.py`, `psort.py`, `psteal.py`, `pinfo.py`) at `/usr/bin/`
- All libewf, libvshadow, libbde, libregf, libesedb, libevt(x), libpff utilities at `/usr/bin/`
- All EZ Tools listed in `scripts/zimmerman.sls:9` (15 of them) — invoked via `/usr/local/bin/<ToolName>` shell wrappers around `dotnet /opt/zimmermantools/...dll`
- **EZ Tools NOT pre-installed: PECmd, SrumECmd, srum-dump** — must add or skip
- RegRipper at `/usr/local/bin/rip.pl` (plugins at `/usr/share/regripper/plugins/`)
- bulk_extractor, foremost, scalpel, photorec
- YARA (system `yara` binary + system `python3-yara`)
- ClamAV (`clamscan`, `freshclam`)
- Wireshark/tshark, tcpdump, tcpflow
- Docker daemon + docker-compose v2.32.4 at `/usr/local/bin/docker-compose`
- dotnet 9 SDK at `/usr/bin/dotnet`
- Claude Code CLI at `/usr/local/bin/claude` (v2.0.61)
- System Python 3.12 with `python-is-python3` symlink → `/usr/bin/python3` and `/usr/bin/python`
- `pip` and `virtualenv` via system packages (NOT uv)
- INDXParse, python-evtx, analyzeMFT, amcache.py, usnparser, hindsight at `/usr/local/bin/<tool>` (each in its own `/opt/<tool>/` venv)

### Tools our install script MUST add
1. **Hayabusa** — `curl -L https://github.com/Yamato-Security/hayabusa/releases/latest/download/hayabusa-<ver>-lin-x64-gnu.zip` → `/opt/hayabusa/`
2. **Chainsaw** — same pattern from `WithSecureLabs/chainsaw`
3. **Velociraptor** binary — single-file release download to `/opt/velociraptor/`
4. **Zeek + Suricata** (if our wedge touches pcap) — `apt install`
5. **PECmd + SrumECmd** (if we surface prefetch/SRUM) — `dotnet` wrappers following `zimmerman.sls` pattern
6. **Node.js** if we ship JS/TS code or OpenClaw — `apt install nodejs npm` (Noble ships 18.x; for 20+ use NodeSource or `nvm`)
7. **uv** (optional, recommended) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
8. **capa / FLOSS / binwalk** — if our malware-triage wedge needs them
9. **Hayabusa rules + Sigma rules** — git clone to `/opt/<rules>/`

### Python / Node version constraints
- **Python 3.12** is the system Python on Ubuntu 24.04.2 Noble (confirmed in `indxparse.sls:11–12`, `python-evtx.sls:11–12`).
  - Any MCP server we ship should target **Python 3.12** as the floor.
  - If we use uv/poetry with `python_requires>=3.12`, we're aligned with the host.
  - If we want to support the older SIFT 2025 (Ubuntu 22.04 Jammy / Python 3.10), we need `python_requires>=3.10`.
- **Pip baseline:** SIFT pins `pip>=24.1.3, setuptools>=70.0.0, wheel>=0.38.4` across every venv. Safe to assume any modern pip features available.
- **No uv pre-installed.** If we use uv internally, our install script must `curl ... astral.sh/uv ... | sh` first.
- **Node.js is NOT pre-installed.** Any OpenClaw / TS / JS dependency requires an install step. Noble ships Node 18.19 in main; Claude Agent SDK and most modern MCP TS work needs Node 20+ — use NodeSource:
  ```bash
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
  apt install -y nodejs
  ```

### Deployment-instruction implications

1. **Target the AMI / OVA at `cast install --mode=desktop` SIFT 2026 freshly provisioned.** Don't assume the user ran any extra installs.
2. **Verify `/usr/local/bin/vol` exists** as a runtime check before claiming Volatility 3 support. If absent, fall back to `/opt/volatility3/bin/vol`.
3. **EZ Tool invocation pattern:** call the lowercase or PascalCase wrapper at `/usr/local/bin/` (e.g. `/usr/local/bin/MFTECmd --csv ...`) — these are bash scripts that invoke `dotnet`. Do **NOT** call `/opt/zimmermantools/MFTECmd.dll` directly unless using `dotnet`.
4. **EZ Tool note for EvtxECmd:** the `.dll` lives at `/opt/zimmermantools/EvtxeCmd/EvtxECmd.dll` (note inner `EvtxeCmd/` dir — lowercase `e`). Wrapper handles this — don't hardcode the path.
5. **Hayabusa/Chainsaw/Velociraptor are FIRST-PARTY install responsibilities for our MCP.** Our README must say "the install script will download and install Hayabusa v3.x, Chainsaw v2.x, Velociraptor v0.7x to `/opt/<tool>/`. SHA256 pinned. ~XYZ MB additional disk."
6. **Apache on port 80 is already serving CyberChef.** If our HUD uses port 80, we conflict. Use 8080 or 8443 by default.
7. **Default user `sansforensics` (sudoer).** Our install script can assume `sudo` works and `$HOME=/home/sansforensics`.
8. **Default SIFT auto-installs `claude` CLI v2.0.61 to `/usr/local/bin/claude`.** Our MCP needs to be discoverable by it via `~/.claude.json` or `claude mcp add`. **We do not need to install Claude Code itself.**
9. **There is no firewall layer** by default; if our MCP binds a port, we should default to `127.0.0.1`.

### Bottom line

**SIFT 2026 ships about 95% of the post-mortem disk/memory/Windows-artifact stack out of the box** (Volatility 3, plaso, Sleuth Kit, libewf/libvshadow/libbde, RegRipper, EZ Tools 15-of-17, bulk_extractor, YARA, ClamAV, Wireshark, Docker, dotnet 9, **Claude Code 2.0.61**). **It does NOT ship** Hayabusa, Chainsaw, Velociraptor, Zeek, Suricata, capa, FLOSS, binwalk, Node.js, uv, PECmd, or SrumECmd — these are our install-script responsibility.
