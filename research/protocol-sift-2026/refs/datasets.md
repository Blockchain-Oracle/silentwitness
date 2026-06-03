# refs/datasets — Validation Datasets

10 datasets are mentioned in the hackathon brief (curated by Anna Tchijova). Verified by deep-research agents on 2026-06-02. Tier ranking reflects "can you SCORE on this?" — Tier 1 has authoritative answer keys, Tier 4 is unverified or dead.

## TL;DR — pick these

| Priority | Dataset | Size | Tier | Why |
|---|---|---|---|---|
| 1 | **Nitroba University Harassment** | 60 MB pcap | Tier 1 | Smallest, fastest iteration, network-only, password-protected solution exists |
| 2 | **NIST Data Leakage (Iaman Informant)** | ~20 GB E01 + 102 MB removable | Tier 1 | **Public answer-key PDF** = automated scoring possible |
| 3 | **NIST Hacking Case (Greg Schardt / "Mr. Evil")** | DD multi-part + EnCase | Tier 1 | On-brand "Find Mr. Evil" name; public writeups |
| 4 | **Ali Hadi #1 — Web Server Compromise** | 1.4 GB disk + 110 MB memory | Tier 2 | Memory+disk pairing — great for multi-source corroboration demo |
| 5 | **DFRWS 2008 Linux Memory Challenge** | 94 MB | Tier 2 | 3 evidence types in one case (memory + disk + network) |

**Use 1+2+3 for the accuracy report.** Use 4+5 for development practice.

---

## Tier 1 — score against these (authoritative answer keys)

### 1.1 Nitroba University Harassment

| Field | Value |
|---|---|
| URL | https://digitalcorpora.org/corpora/scenarios/nitroba-university-harassment-scenario/ |
| Download | https://downloads.digitalcorpora.org/corpora/scenarios/2008-nitroba/nitroba.pcap |
| File | `nitroba.pcap` |
| Size | ~60 MB |
| MD5 | `9981827f11968773ff815e39f5458ec8` |
| SHA1 | `65656392412add15f93f8585197a8998aaeb50a1` |
| SHA256 | `2b77a9eaefc1d6af163d1ba793c96dbccacb04e6befdf1a0b01f8c67553ec2fb` |
| Scenario | Chemistry teacher at fictional Nitroba State U. receives harassing emails. Sender used dorm-room IP, then "willselfdestruct.com" auto-delete email service. |
| Investigation question | Identify which Chemistry 109 student sent the emails. Provide conclusive evidence. |
| Materials | pcap + screenshots of headers + class roster + dorm wifi info |
| Answer key | Password-protected solution for accredited faculty only. Not public — must reconstruct from pcap. |
| Expected pivot | HTTP traffic → identify the willselfdestruct.com POST → correlate IP + MAC + timestamp to roster |
| Hackathon-relevance | **LOW–MEDIUM difficulty.** Network-only forensics. Smallest dataset. **Start here for smoke test + CI.** |

Quick fetch:
```bash
mkdir -p ~/cases/nitroba && cd ~/cases/nitroba
curl -L -o nitroba.pcap https://downloads.digitalcorpora.org/corpora/scenarios/2008-nitroba/nitroba.pcap
echo "9981827f11968773ff815e39f5458ec8  nitroba.pcap" | md5sum -c
```

---

### 1.2 NIST CFReDS — Data Leakage Case (Iaman Informant)

| Field | Value |
|---|---|
| Landing | https://cfreds.nist.gov/all/NIST/DataLeakageCase (dynamic) |
| Static archive | https://cfreds-archive.nist.gov/data_leakage_case/data-leakage-case.html |
| **Answer key (PUBLIC PDF)** | **https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf** |
| PC image | `cfreds_2015_data_leakage_pc` — E01 format, ~20 GB uncompressed (~7 GB compressed) |
| PC image MD5 / SHA1 | `A49D1254C873808C58E6F1BCD60B5BDE` / `AFE5C9AB487BD47A8A9856B1371C2384D44FD` |
| Removable media | `cfreds_2015_data_leakage_rm#3_type` — RAW ISO/CUE, ~102 MB |
| RM MD5 / SHA1 | `858C7250183A44DD83EB706F3F` / `471D3EEDCA9ADD872FC0708297284E1960FF44F` |
| Scenario | "Iaman Informant" — tech-division manager planned to leak data to "Spy Conspirator." Caught at security checkpoint. USB stick + CD checked with portable write-blocker (no apparent evidence), transferred to forensics lab. |
| Question | Find evidence of data leakage. |
| Expected pivot | Disk forensics, USB artifact analysis, anti-forensics (suspect tried to wipe) |
| Hackathon-relevance | **HIGH difficulty. Full Windows disk image + removable media. Answer key is PUBLIC PDF.** **Best Tier-1 target for automated accuracy reporting.** |

---

### 1.3 NIST CFReDS — Hacking Case (Greg Schardt / "Mr. Evil")

| Field | Value |
|---|---|
| Landing | https://cfreds.nist.gov/all/NIST/HackingCase (dynamic) |
| Static archive | https://cfreds-archive.nist.gov/Hacking_Case.html |
| Format | DD image in 7 parts + EnCase image |
| Scenario | 09/20/04 — abandoned Dell CPi notebook (serial #VLQLW) found with wireless PCMCIA card + homemade 802.11b antenna. Suspect Greg Schardt aka "Mr. Evil" — wardriving Starbucks / T-Mobile hotspots to intercept CC numbers, creds. Ethereal installed in promiscuous mode. |
| Question | Tie the notebook to Schardt. Identify hacking activity. |
| Expected pivot | Wireless artifacts, browser history, sniffer software config, registry → username, hostname, MAC |
| Public answer key writeups | intrinsicode.net/2021/05/19/cfreds-hacking-case-report/, zarat.hatenablog.com/entry/2021/12/19/223735, multiple GitHub writeups |
| Hackathon-relevance | **MEDIUM-HIGH. Most famous CFReDS case. Naming is rich: "find evil" → "find Mr. Evil" is on-brand. Strong demo material.** |

---

## Tier 2 — strong build-and-test (answer keys gated)

### 2.1 Ali Hadi #9 — "Encrypt Them All" (Anti-Forensics Case 2)

| Field | Value |
|---|---|
| URL | https://archive.org/details/anti-forensics-case-2 |
| Size | 7.4 GB |
| Format | Archive (torrent available) |
| Date added | March 24, 2023, by AHMK |
| 3 challenges | (1) "Lost in Space" — recover AES-encrypted README. (2) "Do Not Be Deceived!" — decrypt BitLocker volume named R2D2. (3) "Reality Focus" — extract GPG keys, decrypt asymmetric-encrypted message |
| Scenario | User Jane suspected of encrypted communications with unknowns |
| Hackathon-relevance | HIGH — crypto-heavy, anti-forensics. **Tests whether agent over-calls intent on lawful encryption.** VIGIA deliberately marks this SUSPICION, not MALICE — exactly the false-positive behavior judges weight. |

---

### 2.2 Ali Hadi #1 — Web Server Compromise

| Field | Value |
|---|---|
| URL | https://archive.org/details/dfir-case1 |
| Size | 4.4 GB total |
| Components | Memory dump (110 MB) + disk image (1.4 GB), E01 format. Includes password info + hashes. |
| Scenario | Company web server breached via the website. Windows |
| Hackathon-relevance | MEDIUM. Classic web-compromise case. **Memory + disk paired from same host → cleanest fit for multi-source correlation track.** |

---

### 2.3 DFRWS 2008 Linux Memory Challenge

| Field | Value |
|---|---|
| URL | https://github.com/dfrws/dfrws2008-challenge |
| Materials | Memory dump + hard disk + pcap (multi-source) |
| Scenario | "Fusion of evidence from memory, hard disk, and network." CentOS — employee copies files off admin share, escalates with downloaded exploit, exfiltrates through external HTTP proxy |
| Winning submission | Cohen, Collett, and Walters — password breaking, file carving, browser history parsing, evidence tampering detection |
| Answer key | Available in `/results` folder of repo (winning writeups) |
| Hackathon-relevance | HIGH — multi-modal evidence correlation + Linux coverage. Anna Tchijova reportedly built VIGIA ground truth for this one. |

---

## Tier 3 — practice only (do NOT score)

### 3.1 M57-Jean

| Field | Value |
|---|---|
| URL | https://digitalcorpora.org/corpora/scenarios/m57-jean/ |
| Files | `nps-2008-jean.E01` (1.5 GB), `nps-2008-jean.E02` (1.4 GB) — multi-volume EnCase |
| Scenario | Startup data theft — confidential salary spreadsheet posted online; suspect Jean claims she was hacked |
| Question | Determine how data was stolen — or whether Jean is lying |
| Answer key | Encrypted PDF (password-protected) |
| **WARNING** | **Solutions widely distributed online — LLMs likely memorized answers.** Use only for sanity-checking the harness. |

---

### 3.2 Ali Hadi #7 — SysInternals Malware

| Field | Value |
|---|---|
| Directory listing | https://archive.org/download/sysinternals-case |
| Size | 7.2 GB E01 |
| Scenario | User downloaded fake SysInternals tool suite; tools wouldn't open; system slowed |
| Expected findings | MFT shows 2× `sysinternals.exe` — first clean (corrupted, no MZ header), second malicious (32 VT hits). `sysinternals[1].exe` uses `URLDownloadToFileA`, `InternetOpenUrlA`, `ShellExecuteA` → second-stage downloader pattern |
| Public writeups | windowsir.blogspot.com, hackdefendlabs.com, walshcat on Medium |
| Hackathon-relevance | MEDIUM. Practice — answer-key contamination risk. |

---

## Tier 4 — not ready, skip

### 4.1 DFRWS 2011 Android Challenge

| Field | Value |
|---|---|
| URL | https://github.com/dfrws/dfrws2011-challenge |
| Case 1 | Suspicious Death — Donald Norby's Android. Case1.tgz 157 MB compressed / 16.5 GB uncompressed |
| Case 2 | IP Theft — Yob Taog stole "Palomino" product designs. Case2.tgz 338 MB compressed / 16.5 GB uncompressed |
| Distribution | Dropbox links — fragile |
| Problem | README's hashes are labeled MD5 but are actually 40-char SHA1 strings — mislabeled upstream |
| Status | "Not ready" per hackathon rules. SKIP unless mirror with recomputed hashes appears. |

---

### 4.2 Volatility Cridex

| Field | Value |
|---|---|
| Status | **DEAD.** Canonical download (files.volatilityfoundation.org) returns 403. Volatility repo went read-only in May 2025 — broken pointer will never be fixed. No published known-good hash. |
| Action | Skip. |

---

## Data flow into our pipeline

```
~/cases/
├── nitroba/
│   ├── nitroba.pcap
│   └── evidence.json (manifest — hashes, source, ground-truth answer key path)
├── nist-data-leakage/
│   ├── pc.E01
│   ├── removable.iso
│   ├── leakage-answers.pdf
│   └── evidence.json
├── nist-hacking-case/
│   ├── SchardtHD.E01
│   ├── public-writeups/
│   │   ├── intrinsicode.html
│   │   └── zarat.html
│   └── evidence.json
├── ali-hadi-1-webserver/
│   ├── memdump.E01
│   ├── disk.E01
│   └── evidence.json
└── dfrws-2008/
    ├── memory.img
    ├── disk.dd
    ├── capture.pcap
    └── evidence.json
```

Each case's `evidence.json` is the manifest:
```json
{
  "case_id": "nitroba-2008",
  "evidence_files": [
    {"path": "/evidence/nitroba/nitroba.pcap",
     "sha256": "2b77a9eaefc1d6af163d1ba793c96dbccacb04e6befdf1a0b01f8c67553ec2fb",
     "type": "pcap"}
  ],
  "ground_truth": {
    "source": "Nitroba official solution (password-gated for accredited faculty)",
    "expected_findings": [...]
  },
  "scoring_mode": "manual"  // or "auto" if PDF/JSON ground truth is parseable
}
```

---

## VIGIA ground truth — unresolved

Per the hackathon brief, **Anna Tchijova** reportedly built VIGIA ground-truth files for Volatility Cridex and DFRWS 2008. Searches across X, LinkedIn, Google Scholar, academia.edu did **not surface** any public VIGIA artifact tied to her in a DFIR / Protocol SIFT context.

**Likely explanations:**
- (a) Internal SANS work not yet published
- (b) Slack-only distribution
- (c) Embedded in Protocol SIFT NotebookLM and not extracted

**Action:**
- Check the [Protocol SIFT NotebookLM](https://notebooklm.google.com/notebook/f0957a60-6fb2-452b-93d4-ecd73ba47779) for VIGIA mentions
- Ask in the Protocol SIFT Slack `#general` or `#datasets`
- **If we can't find VIGIA, build our own ground-truth scoring against the public answer keys.** That itself becomes a defensible artifact in the accuracy report.

---

## Hallucination scoring methodology (target for our accuracy report)

For each dataset:

1. **Ground-truth set:** N expected findings extracted from the answer key (manual for password-protected; automated for public PDFs / writeups)
2. **Agent run:** capture all DRAFT findings produced
3. **Per-finding classification:**
   - `TRUE_POSITIVE` — agent finding matches a ground-truth finding (by artifact + interpretation)
   - `FALSE_POSITIVE` — agent finding has no ground-truth match AND artifact cited exists in the image
   - `HALLUCINATION` — agent finding cites artifact / file / path / hash that does NOT EXIST in the image (verifiable by running `find` / `grep` against the mount)
   - `FALSE_NEGATIVE` — ground-truth finding not produced by agent
4. **Metrics:**
   - **Precision** = TP / (TP + FP + HALL)
   - **Recall** = TP / (TP + FN)
   - **Hallucination rate** = HALL / total_agent_findings
5. **Baseline:** run vanilla Protocol SIFT on the same datasets; report Δ.

**Report this in the accuracy report.** It is the single most defensible artifact we can ship.
