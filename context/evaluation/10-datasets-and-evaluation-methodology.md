# Datasets and Evaluation Methodology — Reference Catalog

> **Read this if you need to know:** what public DFIR validation datasets exist, what's actually in each one, what the published evaluation methodologies in the AI-DFIR literature measure, and what the metric vocabulary around hallucination / faithfulness / calibration / citation accuracy actually means.
>
> **What this is NOT:** a recommendation for which datasets the project should use, in what order, with what weighting. Those are design decisions. This document is a knowledge base: every dataset, every methodology, the trade-offs and contamination risks, the legal evaluation overlays. Pick from it.

---

## Table of contents

- [Part A — Validation Datasets Deep Catalog](#part-a--validation-datasets-deep-catalog)
  - [A.1 Nitroba University Harassment](#a1-nitroba-university-harassment-2008-digital-corpora)
  - [A.2 NIST CFReDS Data Leakage Case (Iaman Informant)](#a2-nist-cfreds--data-leakage-case-iaman-informant-2015)
  - [A.3 NIST CFReDS Hacking Case (Greg Schardt / "Mr. Evil")](#a3-nist-cfreds--hacking-case-greg-schardt--mr-evil-2004)
  - [A.4 Ali Hadi Case 1 — Web Server Compromise](#a4-ali-hadi-case-1--web-server-compromise)
  - [A.5 Ali Hadi Case 7 — SysInternals Malware](#a5-ali-hadi-case-7--sysinternals-malware)
  - [A.6 Ali Hadi Case 9 — Encrypt Them All (Anti-Forensics Case 2)](#a6-ali-hadi-case-9--encrypt-them-all-anti-forensics-case-2)
  - [A.7 DFRWS 2008 Linux Memory Challenge](#a7-dfrws-2008-linux-memory-challenge)
  - [A.8 DFRWS 2011 Android Challenge](#a8-dfrws-2011-android-challenge-two-cases)
  - [A.9 DFRWS 2018/2019/2020/2021/2023 Challenges](#a9-dfrws-2018201920202021-and-2023-challenges)
  - [A.10 M57-Jean](#a10-m57-jean-digital-corpora)
  - [A.11 M57-Patents Corpus](#a11-m57-patents-corpus)
  - [A.12 Volatility Cridex Memory Dump](#a12-volatility-cridex-memory-dump)
  - [A.13 Volatility Foundation Sample Memory Dumps](#a13-volatility-foundation-public-sample-memory-dumps)
  - [A.14 CFReDS Russian Tea Room](#a14-cfreds-russian-tea-room)
  - [A.15 CFReDS Rhino Hunt](#a15-cfreds-rhino-hunt)
  - [A.16 PoliceCTF Datasets](#a16-policectf--police-academy-style-forensic-ctfs)
  - [A.17 NSRL — Computer Forensics Reference Data Set](#a17-nsrl--computer-forensics-reference-data-set)
  - [A.18 MITRE Cybersecurity Forensic Datasets](#a18-mitre-cybersecurity-forensic-datasets)
  - [A.19 Magnet Forensics Sample Data](#a19-magnet-forensics-sample-data-community)
  - [A.20 TraceLabs OSINT CTF Datasets](#a20-tracelabs-osint-ctf-datasets)
  - [A.21 Belkasoft Sample Images](#a21-belkasoft-sample-images)
  - [A.22 Hacking Lab / CTFd Forensic Challenges](#a22-hacking-lab--ctfd-forensic-challenges)
  - [A.23 VxUnderground Malware Samples](#a23-vxunderground-malware-samples)
  - [A.24 MalwareBazaar / Abuse.ch Feeds](#a24-malwarebazaar--abusech-feeds)
  - [A.25 VirusShare / VirusTotal Academic](#a25-virusshare--virustotal-academic)
- [Part B — VIGIA: the Unverified Reference](#part-b--vigia-the-unverified-reference)
- [Part C — Evaluation Methodologies for AI-DFIR](#part-c--evaluation-methodologies-for-ai-dfir)
  - [C.1 DFIR-Metric (arXiv:2505.19973)](#c1-dfir-metric-arxiv250519973)
  - [C.2 CyberSleuth (arXiv:2508.20643)](#c2-cybersleuth-arxiv250820643)
  - [C.3 Digital Forensics in the Age of LLMs (arXiv:2504.02963)](#c3-digital-forensics-in-the-age-of-llms-arxiv250402963)
  - [C.4 NIST SP 800-53 / 800-218 evaluation overlay](#c4-nist-sp-800-53--800-218-evaluation-overlay)
  - [C.5 Daubert standard considerations](#c5-daubert-standard-considerations)
  - [C.6 FRE 707 — Federal Rule on AI Evidence](#c6-fre-707--federal-rule-on-ai-evidence-post-2024)
- [Part D — Hallucination / Accuracy Metric Families](#part-d--hallucination--accuracy-metric-families)
- [Part E — Baseline Establishment for AI-DFIR Systems](#part-e--baseline-establishment-for-ai-dfir-systems)
- [Part F — Public Answer Key Sources](#part-f--public-answer-key-sources)
- [Part G — Common Evaluation Pitfalls](#part-g--common-evaluation-pitfalls)
- [Sources](#sources)

---

## Part A — Validation Datasets Deep Catalog

The DFIR community has a small canon of widely-cited public forensic images. They were built between 2004 and ~2023 by NIST, academic groups (Digital Corpora, DFRWS, NPS), independent educators (Ali Hadi), and tool vendors. They are uneven in quality, in answer-key availability, in evidentiary fidelity, and — increasingly important for AI evaluation — in the degree to which their solutions have already been indexed by large-scale web crawls and pulled into LLM training corpora.

This section catalogs them.

For each dataset the relevant fields are:

- **Custodian** — who hosts and maintains it
- **Year / provenance** — when it was created, by whom, for what purpose
- **Size** — compressed and (where the image is split or compressed) uncompressed
- **Format** — E01 / Ex01 (EnCase Expert Witness), raw DD, AFF4, pcap/pcapng, EVTX archive, tar.gz of OS files, MFT carve, etc.
- **Hashes** — MD5 / SHA1 / SHA256 of the canonical artifact, where verified against the custodian
- **Download URL(s)** — direct and mirror
- **Scenario** — plain-English summary of what is alleged to have happened
- **Investigation questions** — what the analyst is supposed to answer
- **Materials provided** — image only, image + supplemental docs, image + roster + screenshots, etc.
- **Expected investigation path** — the canonical pivot chain a senior analyst would walk
- **Ground truth status** — public answer key, gated answer key, internal-only, none
- **Difficulty + senior-analyst time** — low / medium / high and an estimate of how long a FOR508-grade analyst takes to fully resolve
- **LLM-memorization risk** — likelihood the case + answers are already in OpenAI / Anthropic / Google / Mistral pretraining data
- **Anti-forensics elements** — timestomping, log clearing, encryption, BitLocker, GPG, secure deletion, alternate data streams, etc.
- **Recommended use category** — smoke test, development, training, scoring (without prescribing which)
- **Known issues** — mislabeled hashes, broken links, dataset drift, missing files, etc.

The cases are presented in a stable order. Difficulty is calibrated against a senior IR consultant (FOR508 graduate or equivalent) working unattended.

---

### A.1 Nitroba University Harassment (2008, Digital Corpora)

| Field | Value |
|---|---|
| Custodian | Naval Postgraduate School (Simson Garfinkel originally) → now hosted on Digital Corpora |
| Year | 2008 |
| Landing | https://digitalcorpora.org/corpora/scenarios/nitroba-university-harassment-scenario/ |
| Direct download | https://downloads.digitalcorpora.org/corpora/scenarios/2008-nitroba/nitroba.pcap |
| File | `nitroba.pcap` |
| Size (compressed = uncompressed) | ~60 MB (single file, not compressed) |
| Format | libpcap (`tcpdump` capture) |
| MD5 | `9981827f11968773ff815e39f5458ec8` |
| SHA1 | `65656392412add15f93f8585197a8998aaeb50a1` |
| SHA256 | `2b77a9eaefc1d6af163d1ba793c96dbccacb04e6befdf1a0b01f8c67553ec2fb` |

**Scenario.** Chemistry professor Lily Tuckrige at fictional Nitroba State University is receiving a stream of harassing emails from `lilytuckrige@yahoo.com` to her personal Yahoo account. The emails escalate over days. The university IT department captured a packet trace of the dorm wireless network during the relevant window. Investigators are given the pcap, screenshots of email headers, a class roster, and dorm-WiFi network notes.

The sender eventually used `willselfdestruct.com` — a now-defunct service that delivered an email and then auto-deleted it on read — to obscure their tracks. The capture contains the HTTP POST that submitted the message before the service auto-deleted it.

**Investigation questions.** Identify which of the students in Tuckrige's Chemistry 109 class sent the harassing emails. Provide conclusive evidence: IP, MAC, timestamp, and the content of the willselfdestruct.com payload. The roster contains ~20 students; the capture has many devices in flight.

**Materials provided.** `nitroba.pcap`; PDFs of received email screenshots; a class roster (names + dorm rooms); a short explanatory PDF describing the wireless infrastructure.

**Expected investigation path.** Open in Wireshark or tshark → filter on HTTP POST traffic → find the willselfdestruct.com submission → extract the form data containing the harassment email body → correlate the source IP + MAC of that POST to the roster information (the dorm's IP-to-room mapping is recoverable from DHCP traffic) → name the student. A network-only case, no host artifacts.

**Ground truth.** A solution document exists but is password-protected, distributed only to accredited faculty by NPS/Digital Corpora to preserve the dataset's pedagogical value. The community has reverse-engineered the answer in many writeups, but those writeups vary in correctness and in how much of the chain they reproduce.

**Difficulty.** Low to medium. A skilled network analyst finishes in 30 to 90 minutes. The case is solvable from the pcap alone if you know to look for willselfdestruct.com — but if you don't, the volume of dorm traffic can mislead.

**Senior-analyst time.** ~45 minutes for a first-time attempt; ~15 minutes once they know the trick.

**LLM-memorization risk.** **Medium.** Nitroba is one of the most-taught network forensics datasets in academia. Discussion of the willselfdestruct.com trick, the suspect's identity, and the pivot chain has been published in classroom slides, GitHub writeups, and lab manuals for over a decade. Major LLMs have likely seen partial solutions. The official solution PDF is gated, but enough of the answer is in the wild that any model with broad pretraining can take a credible guess at the suspect name.

**Anti-forensics elements.** Use of willselfdestruct.com to delete email after delivery (an evasion technique, not on-host anti-forensics). No host-side anti-forensics — there's no host image.

**Recommended use category.** Smoke test or fast iteration: smallest possible case, no disk processing required, pure pcap, can be re-run in seconds. Good for harness CI. Less useful for testing disk + memory pivots. The lack of host artifacts also means it can't exercise tool-chain breadth.

**Known issues.** None significant. The pcap is clean, well-documented, and the canonical hash has held since 2008. The only minor friction: the gated solution PDF means automated scoring requires reconstructing the answer key from inspection rather than parsing a published document.

---

### A.2 NIST CFReDS — Data Leakage Case (Iaman Informant, 2015)

| Field | Value |
|---|---|
| Custodian | NIST Computer Forensic Reference Data Sets (CFReDS) program |
| Year | 2015 (curated by Yongseok Kim and team) |
| Dynamic landing | https://cfreds.nist.gov/all/NIST/DataLeakageCase |
| Static archive landing | https://cfreds-archive.nist.gov/data_leakage_case/data-leakage-case.html |
| **Answer key (PUBLIC PDF)** | **https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf** |
| PC image file | `cfreds_2015_data_leakage_pc.zip` containing `pc.E01` (E01 format) |
| PC image size | ~7 GB compressed / ~20 GB uncompressed disk |
| PC image MD5 | `A49D1254C873808C58E6F1BCD60B5BDE` |
| PC image SHA1 | `AFE5C9AB487BD47A8A9856B1371C2384D44FD` (note: per refs/datasets.md — verify before relying) |
| Removable media file | `cfreds_2015_data_leakage_rm#3_type.zip` containing a raw ISO/CUE pair |
| RM size | ~102 MB |
| RM MD5 | `858C7250183A44DD83EB706F3F` (note: short form on record — verify) |
| RM SHA1 | `471D3EEDCA9ADD872FC0708297284E1960FF44F` (verify) |

**Scenario.** A tech-division manager — codenamed "Iaman Informant" — at a fictional employer has been suspected of planning to leak proprietary data to a competitor codenamed "Spy Conspirator." Iaman is caught at a security checkpoint as he tries to leave the building; his USB stick and CD are inspected with a portable write-blocker on-site. The on-site inspection finds no obvious evidence, but the devices are still escorted to the forensics lab along with Iaman's company-issued workstation. The investigator's job is to find any evidence — anywhere across the workstation, the USB stick, and the CD — of the planned data leak.

**Investigation questions.** The official PDF contains 31 numbered questions covering:

- File-system and registry timeline reconstruction of the suspect's last days on the machine
- USB device history and removable-media artifact correlation
- Webmail / cloud upload activity (Gmail, Naver)
- Encrypted container detection and recovery
- Anti-forensics: file wiping, USN journal artifacts, Recycle Bin
- Cross-device correlation: does the same file appear on the workstation and the removable media at consistent timestamps?

**Materials provided.** PC E01 image; removable-media raw image; the public **leakage-answers.pdf** with all 31 questions, the expected answers, and which artifacts support each answer.

**Expected investigation path.** Mount the E01 read-only → run a full plaso timeline → look at $MFT, $LogFile, $UsnJrnl/$J for file activity → carve browser history (Chrome / IE / Edge depending on case build year) for webmail uploads → parse ShellBags, LNK files, JumpLists for navigation history → enumerate USB devices via SYSTEM hive (USBSTOR, MountedDevices, MountPoints2) → check encrypted-container indicators (TrueCrypt/VeraCrypt headers in pagefile and slack) → carve the removable media for any deleted files that match exfiltration candidates → cross-reference file hashes between PC and removable media. The case is deliberately constructed to require multi-source correlation across the workstation, the USB, and the CD.

**Ground truth.** **Public PDF** at the URL above. The PDF is structured: each question has a numbered answer plus a "this is supported by artifact X at path Y" reference. This makes it the single most parseable answer key in the public DFIR corpus.

**Difficulty.** High. A senior analyst needs hours to complete all 31 questions, and many require running specific tools and reading specific artifacts in sequence.

**Senior-analyst time.** 6 to 10 hours for full coverage of all 31 questions; ~3 hours for the "headline" findings (exfiltration channel + USB device + encrypted container).

**LLM-memorization risk.** **High for the scenario summary, medium for the per-artifact answers.** The PDF has been online for nearly a decade, accessible from cfreds-archive.nist.gov, and has been cited in dozens of GitHub writeups, academic papers, and SANS course materials. A model that pretrained on Common Crawl data has almost certainly seen "Iaman Informant" and could regurgitate the high-level conclusion. The detailed artifact-by-artifact path (specific hex offsets, specific INDX records, specific timeline rows) is less likely to be memorized verbatim.

**Anti-forensics elements.** Yes — significant. The suspect attempted to wipe traces using a number of techniques (the answer PDF enumerates them). Recoverable via $LogFile and $UsnJrnl forensics, Volume Shadow Copies, slack space, and Recycle Bin metadata. Encrypted container present and detectable.

**Recommended use category.** Development, training, and (potentially) scoring. The public structured PDF answer key makes it one of the few cases where automated comparison of agent findings to ground truth is practical.

**Known issues.**
- The hashes on record in some derivative documentation are truncated (e.g., the SHA1 strings shown above are short of 40 chars). Re-verify against the custodian before relying on them as integrity proofs.
- Some Wayback-archived copies have stale download links. The cfreds-archive.nist.gov host is the source of truth as of 2026.
- The case build year is 2015, which means some artifacts (e.g., Edge legacy, IE 11) are now historically irrelevant. The forensic tooling still parses them, but the user behaviors look dated.

---

### A.3 NIST CFReDS — Hacking Case (Greg Schardt / "Mr. Evil", 2004)

| Field | Value |
|---|---|
| Custodian | NIST CFReDS |
| Year | 2004 (originally), republished multiple times |
| Dynamic landing | https://cfreds.nist.gov/all/NIST/HackingCase |
| Static archive | https://cfreds-archive.nist.gov/Hacking_Case.html |
| Format | DD image (split into 8 parts: `SCHARDT.001` … `SCHARDT.008`) plus an EnCase E01 variant |
| Size (DD parts) | ~4.5 GB total uncompressed (the original disk was a ~5 GB Compaq drive) |
| MD5 (of reassembled DD) | `aee4fcd9301c03b3b054623ca261959a` (verify against custodian) |
| Download | Multiple mirrors; the static archive at cfreds-archive.nist.gov has the canonical links |

**Scenario.** On 09/20/2004 an abandoned Dell CPi laptop (serial number `VLQLW`) is found at a Starbucks. It has a wireless PCMCIA card and a homemade 802.11b antenna attached. The suspect is one Greg Schardt, who is rumored to use the handle "Mr. Evil." Schardt is believed to have been wardriving the Starbucks and other T-Mobile hotspots, intercepting credit-card numbers and credentials from other patrons. The laptop has Ethereal (pre-Wireshark) installed and configured to capture in promiscuous mode. The case file delivered to the analyst is a forensic image of the laptop's hard drive.

**Investigation questions.** The classic set:
1. What is the MAC address of the wireless adapter?
2. What is the laptop's hostname?
3. What is the SMTP email address of "Mr. Evil"?
4. What is the IP address of the laptop?
5. Show the wireless networks the laptop connected to.
6. Tie Schardt to the laptop (registry SAM, Outlook, browser data).
7. Identify the hacking tools installed (Ethereal, Cain & Abel, etc.).
8. Where in the file system is the wardriving evidence?

**Materials provided.** Disk image only. No memory dump, no separate pcap (the pcap is on the disk, inside Schardt's Ethereal capture file). No roster, no supplemental docs. The case description is the entirety of the briefing.

**Expected investigation path.** Mount the image read-only → SAM/SOFTWARE/SYSTEM registry parse → owner name "Greg Schardt" lives in SAM and the registered-owner SOFTWARE value → hostname from SYSTEM hive → MAC from the registry network-config keys → look in `Documents and Settings\Mr. Evil` for the user profile (the user account is literally `Mr. Evil`) → enumerate Program Files for hacking tools (Ethereal, Network Stumbler, Cain & Abel, 123 Write All Stored Passwords, Anonymizer) → check email artifacts (Outlook PST, browser cached mail) → extract pcap captures from the Ethereal config folder → carve wireless network history.

**Ground truth.** No single canonical answer PDF from NIST. The community has written it down many times: notable writeups include intrinsicode.net (2021), zarat.hatenablog.com (2021), and numerous GitHub repos under search terms like "cfreds hacking case writeup." NIST's static archive page does list the canonical investigation questions but not signed answers.

**Difficulty.** Medium to medium-high. Conceptually straightforward — it's a 2004 Windows XP disk with deliberate breadcrumbs — but the breadth of artifacts (registry + user profile + Program Files + browser + email + pcap inside the disk) makes it a good full-spectrum test. A senior analyst can finish in 2 to 4 hours.

**Senior-analyst time.** 2 to 4 hours for the standard answer set; ~6 hours if they also extract and analyze the on-disk Ethereal captures.

**LLM-memorization risk.** **Very high.** "Greg Schardt," "Mr. Evil," "CFReDS Hacking Case," and the canonical answers (MAC address, IP, hostname, email) appear in hundreds of indexed writeups. A large LLM with broad pretraining can plausibly produce most of the high-level findings purely from pretraining without ever touching the image. **This means a model passing this case is not evidence of working forensic capability — it is evidence the model has seen the writeups.** Any honest evaluation must distinguish between "found from evidence" and "regurgitated from memory."

**Anti-forensics elements.** Modest. Schardt did not deliberately wipe or timestomp. The case is more "find the smoking gun" than "find the gun the suspect tried to hide."

**Recommended use category.** Development, training, and demo. Scoring is heavily compromised by the memorization risk. If used for scoring, the methodology must include controls for memorization (e.g., paraphrased questions, or partial-credit only for findings that include a citation to a specific verifiable artifact location).

**Known issues.** The original NIST URL has moved several times. The DD parts must be reassembled before mount; some derivative writeups skip the reassembly step. The EnCase E01 variant has a different hash than the reassembled DD, which has caused confusion in mirror sites. The case build assumes Windows XP, which makes some modern forensic tools complain about missing registry keys.

---

### A.4 Ali Hadi Case 1 — Web Server Compromise

| Field | Value |
|---|---|
| Custodian | Ali Hadi (Champlain College / private researcher), self-hosted; mirrored on archive.org |
| Year | ~2016 (uploaded to Internet Archive 2019) |
| Landing | https://archive.org/details/dfir-case1 |
| Components | Memory dump + disk image |
| Memory dump | ~110 MB (raw, taken with FTK Imager) |
| Disk image | ~1.4 GB (E01 format) |
| Total package | ~4.4 GB including supporting docs and a password file |
| Hashes | Published in the case README on archive.org — verify before reliance |

**Scenario.** A company's public-facing IIS web server (Windows Server) has been compromised. The intrusion was first noticed by IT operations when the server's behavior changed. The IR team captured memory and pulled the disk. Investigator's job: reconstruct how the attacker got in, what they did once in, what they left behind, and what (if anything) was exfiltrated. The case explicitly emphasizes memory + disk correlation — many of the answers are visible in only one of the two sources and must be cross-checked against the other.

**Investigation questions.** The case ships with an investigator brief listing questions:
- How was the server compromised? (Initial access vector)
- What account was used for the initial compromise?
- What persistence was installed?
- Were any tools dropped on disk? Were they running in memory at capture time?
- What lateral movement was attempted?
- What data was exfiltrated, if any?

**Materials provided.** `memory.E01` (memory dump in EWF), disk `disk.E01`, an investigator-brief PDF, and a passwords file with credentials for accounts on the server.

**Expected investigation path.** Convert memory.E01 to raw → run Volatility 3 plugins (`windows.pslist`, `windows.pstree`, `windows.netscan`, `windows.malfind`, `windows.cmdline`, `windows.dlllist`, `windows.handles`) → identify suspicious processes (non-standard binaries in non-standard locations, processes with no parent, processes communicating to external IPs) → pivot to disk: mount disk.E01, walk the file system to find the dropped binaries on disk, hash them, check against IOCs → review IIS logs for the initial access pattern → check $MFT for file creation timeline → confirm persistence (services, registry Run keys, scheduled tasks).

**Ground truth.** No public answer key from Ali Hadi. The case has community writeups (search "ali hadi dfir case 1 writeup") but no single canonical document. The "ground truth" is what the community has converged on.

**Difficulty.** Medium. The case is well-scoped, the memory dump is small enough that Volatility runs in seconds, and the disk image is small enough that timeline generation is fast. A senior analyst finishes in 3 to 5 hours.

**LLM-memorization risk.** Medium. The case has been written up on a number of forensic blogs but is less viral than the NIST cases. Major models likely know the scenario shape but may not have memorized the specific attacker IPs / binary names / persistence mechanisms.

**Anti-forensics elements.** Modest. Some log cleanup may be present depending on the case version; the attacker does not heavily anti-forensic their tooling.

**Recommended use category.** Development and training — clean memory+disk pair, fast to run, good full-stack exercise. Scoring is harder due to lack of a canonical answer key.

**Known issues.** The archive.org URL has been stable but the file names have changed between revisions. The password file is in plaintext alongside the evidence, which is a tutorial choice — real cases don't ship credentials. Some users have reported the memory E01 file fails to open in older Volatility 2 builds; conversion to raw with `ewfexport` is the safe path.

---

### A.5 Ali Hadi Case 7 — SysInternals Malware

| Field | Value |
|---|---|
| Custodian | Ali Hadi |
| Year | ~2018 |
| Directory listing | https://archive.org/download/sysinternals-case |
| Format | E01 disk image |
| Size | ~7.2 GB |
| Hashes | Posted alongside the image on archive.org |

**Scenario.** A user downloaded what they believed was the official Microsoft SysInternals tool suite. The downloaded executables did not open and the system slowed dramatically. The user's IR team imaged the disk. Investigator's job: identify the malware, classify it, find the persistence mechanism, identify any C2.

**Investigation questions.** Identify the fake SysInternals dropper. Identify the malicious payload it installs. Determine the persistence mechanism. Identify C2 infrastructure if present. Distinguish between the legitimate SysInternals binaries (which the user may have downloaded earlier) and the malicious replacements.

**Materials provided.** Disk image only. No memory dump (the malware is dormant after the user closed the failed launch; some detection requires examining unpacked images on disk).

**Expected investigation path.** Triage on $MFT to find the dropped `sysinternals.exe` → notice the file appears twice in the MFT (first instance is corrupted / has no MZ header, second instance is the working malicious file) → hash the second file, submit to VirusTotal context → it returns ~32 detections → static analysis of the binary reveals imports of `URLDownloadToFileA`, `InternetOpenUrlA`, and `ShellExecuteA` — classic second-stage downloader pattern → trace what the binary tried to download (URL artifacts in strings or in a sandbox run) → check Prefetch for evidence of execution → check Schtasks / Run keys / Services for persistence.

**Ground truth.** No published answer PDF. Community writeups exist on windowsir.blogspot.com (Harlan Carvey), hackdefendlabs.com, and on Medium under the user "walshcat."

**Difficulty.** Medium. The case is a focused malware-analysis exercise with clear breadcrumbs. ~2-3 hours for a senior analyst.

**LLM-memorization risk.** Medium. The case is known but less famous than CFReDS. Detailed answers (specific hashes, specific URLs) are less likely to be memorized than the overall shape.

**Anti-forensics elements.** Minimal. The malware uses simple deception (impersonating SysInternals) and does not actively wipe traces.

**Recommended use category.** Development practice, especially for testing malware-triage workflows that integrate VirusTotal / IOC lookup with static binary analysis.

**Known issues.** None significant. The case is clean and the archive.org hosting has been stable.

---

### A.6 Ali Hadi Case 9 — Encrypt Them All (Anti-Forensics Case 2)

| Field | Value |
|---|---|
| Custodian | Ali Hadi, uploaded by AHMK on archive.org |
| Year | 2023 |
| Landing | https://archive.org/details/anti-forensics-case-2 |
| Size | ~7.4 GB |
| Format | E01 disk image plus supplemental files, distributed as archive (torrent available) |

**Scenario.** User Jane is suspected of using encrypted channels to communicate with unknown counterparties. The disk shows extensive use of consumer encryption tools. The case is deliberately constructed to test whether the analyst (or an AI agent) **over-calls intent**: encryption is not by itself malicious, and a good forensic analyst flags it as suspicious but not conclusive. The case has three sub-challenges that exercise different crypto primitives:

1. **"Lost in Space"** — recover an AES-encrypted README. The key is recoverable from another artifact on disk; the analyst must find the key, recognize what cipher and mode, and decrypt.
2. **"Do Not Be Deceived!"** — decrypt a BitLocker volume named `R2D2`. Recovery key is hidden somewhere on disk; locate, mount, exfiltrate contents.
3. **"Reality Focus"** — extract GPG keys from the user profile, decrypt an asymmetric-encrypted message that ties Jane to a counterparty.

**Investigation questions.** Each sub-challenge has a question set. Across them: identify all encryption tools in use; recover all keys recoverable from the system; report what's inside each encrypted container; **do not assert that the user is guilty of anything criminal**, only that they used encryption and what was protected.

**Materials provided.** Disk image; case briefing PDF; the three sub-challenge descriptions.

**Expected investigation path.** $MFT scan for crypto-tool footprints (BitLocker, VeraCrypt, GPG, OpenSSL) → registry mining for BitLocker recovery key cache → user-profile carving for GPG keyring → memory analysis if memory dump available (the case file does not always include one) → patient sub-challenge-by-sub-challenge work.

**Ground truth.** Per case-author convention: not a public PDF; you have to register or contact the author. Community writeups exist for parts 1 and 2; part 3 has fewer public writeups.

**Difficulty.** High. Crypto-aware and requires careful operational tradecraft (e.g., don't blast the BitLocker recovery key into logs). 6 to 12 hours for a senior analyst.

**LLM-memorization risk.** Low to medium. The case is recent (2023) and the answer key is gated, so contamination is limited. The general shape (BitLocker + GPG + AES challenges) is widely discussed but the specific keys / paths are not.

**Anti-forensics elements.** Yes — explicitly the point of the case. BitLocker, AES, GPG, plus deliberate hiding of keys.

**Recommended use category.** Hardest test for AI epistemic honesty (does the agent over-conclude criminal intent from the mere presence of encryption?) and for testing crypto-aware workflows.

**Known issues.** Torrent distribution is sometimes flaky; archive.org direct download is the more reliable route. The case is large enough that bandwidth budget matters for repeat runs.

---

### A.7 DFRWS 2008 Linux Memory Challenge

| Field | Value |
|---|---|
| Custodian | DFRWS (Digital Forensics Research Workshop) |
| Year | 2008 |
| Landing / mirror | https://github.com/dfrws/dfrws2008-challenge |
| Components | Memory dump + hard disk image + pcap |
| Total size | ~94 MB |
| Format | Raw memory, raw DD disk, libpcap |

**Scenario.** A CentOS Linux host has been compromised. The challenge ships memory, disk, and network captures from the moment of the incident. The narrative: an employee downloads files from an admin share, runs a downloaded local privilege escalation exploit, and exfiltrates data through an external HTTP proxy. The challenge was DFRWS's annual benchmark for 2008, and the explicit point was **"fusion of evidence from memory, hard disk, and network."**

**Investigation questions.** Reconstruct the timeline. Identify the exploit used. Identify what data was exfiltrated. Identify the external proxy. Identify the user account involved. Catch evidence of evidence tampering (the suspect attempted to alter logs).

**Materials provided.** Three artifacts (memory.img, disk.dd, capture.pcap), case briefing, plus the original DFRWS rules document.

**Expected investigation path.** Parallel triage on all three sources: Volatility for memory (process tree, network connections, command-line history); plaso / log2timeline for disk; tshark for pcap. Then cross-correlate at the temporal axis: the memory snapshot was taken at time T, so anything on disk modified before T should be consistent with the memory state; anything in pcap before T should be consistent with the memory's network state.

**Ground truth.** The winning submissions (Cohen, Collett, and Walters) are published in the `/results` folder of the GitHub repo. They are detailed writeups, not a flat answer JSON.

**Difficulty.** High — requires Linux memory forensics (Volatility 2 plugins for Linux), Linux disk forensics, and packet analysis. 4 to 8 hours for a senior analyst.

**LLM-memorization risk.** Medium. The case is well-documented in the DFRWS proceedings; the winning writeups are public. A model that has read DFRWS proceedings (academic papers are well-represented in pretraining) may have seen the answer chain.

**Anti-forensics elements.** Yes — evidence tampering of logs is part of the case. The winning writeups demonstrate detection of the tampering.

**Recommended use category.** Excellent for testing multi-source correlation workflows. The three-modality structure makes it one of the few small datasets that exercises memory + disk + network simultaneously.

**Known issues.** Linux memory forensics requires building a Volatility profile matching the CentOS kernel version. Volatility 3 has spotty Linux support compared to Volatility 2; the canonical answer used Volatility 2. Modern tooling may require kernel-symbol extraction work.

---

### A.8 DFRWS 2011 Android Challenge (two cases)

| Field | Value |
|---|---|
| Custodian | DFRWS |
| Year | 2011 |
| Landing | https://github.com/dfrws/dfrws2011-challenge |
| Case 1 | "Suspicious Death" — Donald Norby's Android device. `Case1.tgz` 157 MB compressed / 16.5 GB uncompressed |
| Case 2 | "IP Theft" — Yob Taog allegedly stole "Palomino" product designs. `Case2.tgz` 338 MB compressed / 16.5 GB uncompressed |
| Distribution | Dropbox links (legacy) |

**Scenario.**
- **Case 1 ("Suspicious Death")** — a man is found dead under unclear circumstances; his Android device is recovered. Investigators are asked to reconstruct his last days, identify any people or locations of interest, and assess whether the device shows evidence of foul play.
- **Case 2 ("IP Theft")** — Yob Taog is suspected of having stolen the product designs for an internal project codenamed "Palomino." His Android device is imaged. Investigators must locate the stolen IP, trace its exfiltration, and tie it to communications with external parties.

**Investigation questions.** Reconstruct device timeline; mine SMS / call logs / contacts; identify app data of interest (email apps, browsers, IM clients); cross-correlate location data with timeline; extract any documents that match the "Palomino" project description.

**Materials provided.** Full Android device image including system partition, userdata partition, and (for some revisions) SD card image. Briefing PDFs for each case.

**Ground truth.** Winning submissions are in the repo's results folder, with detailed walkthroughs. Like 2008, the answer is a writeup not a parseable JSON.

**Difficulty.** High. Android internals are evolving and the 2011 cases use Gingerbread (2.3) / Honeycomb (3.x) — analyzing them with modern tools requires knowing what's been deprecated. SQLite databases dominate; tools like sqlitebrowser and Belkasoft SQLite Viewer apply.

**LLM-memorization risk.** Low to medium. Android forensics writeups are more sparse than Windows; the answer keys are public but specific details are less viral.

**Anti-forensics elements.** Modest — typical mobile-data quirks (call-log deletion, app private storage).

**Recommended use category.** Specialist mobile-forensics exercise. Not relevant for cases targeting Windows-only or Linux-only scopes.

**Known issues — significant.**
- The README publishes hashes labeled "MD5" that are actually **40-char SHA1 strings**. This has confused multiple downstream users into thinking the files are corrupted.
- Dropbox distribution is fragile; mirrors come and go.
- The 16.5 GB uncompressed extraction is large for what the case actually requires.

The combination of mislabeled hashes + flaky distribution + niche scope is why some practitioners deprioritize this dataset.

---

### A.9 DFRWS 2018/2019/2020/2021 and 2023 Challenges

DFRWS has continued running an annual forensic challenge. Status of each:

- **DFRWS 2018 (IoT Forensics Challenge)** — multi-IoT-device case (smart hub, smart bulb, mobile). Hosted on https://dfrws.org/dfrws-forensic-challenge/. Materials remain available; ground truth is winning team writeups.
- **DFRWS 2019 (User Activity Reconstruction)** — focus on reconstructing user behavior across multiple synced devices. Materials available; less academically cited than earlier years.
- **DFRWS 2020 — Continued under DFRWS-EU.** The Europe chapter has run challenges since 2020. Materials behind a registration wall but generally available.
- **DFRWS 2021 — IoT pivot continued.** Smart device telemetry, cloud-backed data, more diverse than disk/memory cases.
- **DFRWS 2023 (Forensic Triage Challenge / Smart Devices)** — the most recent at the time of writing. Materials posted to the DFRWS website; expected to be moved to the GitHub mirror over time.

For each, the **ground truth pattern is the same**: winning submissions are writeups, not a structured JSON. Difficulty varies but is generally high (multi-source, often non-Windows). LLM-memorization risk is lower than CFReDS but rising for the older challenges.

**Practical caveat:** the DFRWS website occasionally re-organizes; the GitHub mirrors are more durable but lag the website by a year or two for new challenges.

---

### A.10 M57-Jean (Digital Corpora)

| Field | Value |
|---|---|
| Custodian | Naval Postgraduate School → Digital Corpora |
| Year | 2008 |
| Landing | https://digitalcorpora.org/corpora/scenarios/m57-jean/ |
| Files | `nps-2008-jean.E01` (~1.5 GB) and `nps-2008-jean.E02` (~1.4 GB) — multi-volume E01 |
| Format | E01 |
| Hashes | Published on the Digital Corpora landing page |

**Scenario.** Jean is a fictional employee at fictional startup M57. A confidential salary spreadsheet was posted on a public competitor's forum. Jean is the prime suspect; she claims she was hacked. The disk image is of her work laptop.

**Investigation questions.** Reconstruct how the spreadsheet left her machine. Determine whether her "I was hacked" story holds up. If she was hacked, identify the attacker; if she did it herself, identify the channel.

**Materials provided.** Two-part E01 disk image; a case briefing.

**Expected investigation path.** Mount → timeline → browser history → email client (Outlook PST) → IM clients → look for spreadsheet creation/access/email/upload event sequence → check user-installed software for unusual tools.

**Ground truth.** Encrypted PDF (password-protected, distributed to faculty). **However, this case has been written up and the answers distributed widely online** — see warning below.

**Difficulty.** Medium. ~2-4 hours for a senior analyst.

**LLM-memorization risk.** **VERY HIGH — DO NOT USE FOR SCORING UNDER ANY CONDITIONS WITHOUT EXPLICIT MEMORIZATION CONTROLS.** M57-Jean is the most heavily-spoiled forensic case on the open internet. The answers (which channel, which timing, what Jean did) are reproduced in slides, blog posts, GitHub repos, and academic course notes. The case has been part of teaching DFIR for over 15 years. Any LLM with broad pretraining can produce the answer chain from pretraining alone.

**Anti-forensics elements.** Minimal — Jean is not a sophisticated suspect.

**Recommended use category.** Sanity-check the harness (does it run end-to-end?) but not for accuracy claims. Useful for prompt development. Not useful for benchmarking.

**Known issues.** The "over-published answer" problem dominates. The encrypted-PDF answer key is moot.

---

### A.11 M57-Patents Corpus

| Field | Value |
|---|---|
| Custodian | Naval Postgraduate School → Digital Corpora |
| Year | 2009-2010 |
| Landing | https://digitalcorpora.org/corpora/scenarios/m57-patents-scenario/ |
| Components | Multiple desktops + servers + memory dumps + network captures from a fictional small company over multiple "days" |
| Total size | ~150 GB raw |

**Scenario.** M57 (same fictional company as M57-Jean) is a startup developing search-engine patents. The scenario simulates a multi-week timeline of normal business activity interspersed with security incidents: insider data theft, malware infection, contractor misbehavior. Each "day" produces a set of images and captures.

**Investigation questions.** Different for each day; the scenario was designed for academic classes that take students through a multi-week investigation. Questions span insider threat, malware, policy violation, intellectual property theft.

**Materials provided.** Day-by-day archives, each with disk images, memory snapshots, and pcap. The set is enormous.

**Expected investigation path.** Multi-day, multi-source: this is the dataset closest to a real long-running investigation in terms of scale.

**Ground truth.** Some days have published answer keys; others are exercises for students. The Digital Corpora landing page links to course materials that include partial answers.

**Difficulty.** Variable per day; overall, high in aggregate (the scale is the difficulty).

**LLM-memorization risk.** Medium to high for specific days that have been heavily taught.

**Anti-forensics elements.** Multiple, scattered across days.

**Recommended use category.** Long-form testing of investigation workflows over multi-day evidence. Useful for stress-testing context-management. Not a single-pass benchmark.

**Known issues.** Sheer size makes downloading and storage non-trivial. Different days have different schemas and different host operating systems, requiring tooling breadth.

---

### A.12 Volatility Cridex Memory Dump

| Field | Value |
|---|---|
| Custodian | Volatility Foundation |
| Year | ~2014 |
| Originally hosted | files.volatilityfoundation.org (now returning 403) |
| Status | **Effectively dead.** |

**Scenario.** A Windows XP host infected with the Cridex banking trojan. The memory dump captures the infected state. This was the iconic "first Volatility tutorial" memory image for nearly a decade — every introductory Volatility tutorial used it.

**Investigation questions.** Identify the malicious process; identify the injected DLL; identify the C2 IP and port; show the process tree anomaly.

**Materials provided.** Memory dump only.

**Expected investigation path.** `vol.py -f cridex.vmem --profile=WinXPSP2x86 pslist` → spot the suspicious process → `malfind` → identify the injection → `connscan` for the C2.

**Ground truth.** The expected answers are reproduced in dozens of Volatility tutorials and blog posts.

**Difficulty.** Low. The case is a deliberately-simple introductory example.

**LLM-memorization risk.** **Extremely high.** Cridex is the canonical Volatility example. Every model with broad pretraining knows the answers.

**Status.** The canonical download from files.volatilityfoundation.org returns 403. The Volatility repository was set to read-only in May 2025; the broken pointer will not be fixed. There is no published known-good hash with strong provenance.

**Workarounds.** Some community mirrors carry the file (search GitHub for `cridex.vmem`), but none have authoritative provenance, and there are at least two distinct files in circulation under the same name that produce different Volatility output. This is a non-trivial integrity problem for any work that wants to compare results.

**Recommended use category.** Historical reference only. The combination of (dead link) + (no canonical hash) + (extreme memorization risk) means this is not usable for current benchmarking.

---

### A.13 Volatility Foundation Public Sample Memory Dumps

The Volatility Foundation historically hosted a small set of public memory-analysis samples beyond Cridex. As of the 2025 read-only transition, the status is:

- **Cridex** — broken (see above).
- **Zeus** — community mirror; same memorization caveats.
- **Stuxnet** — academic sample of the Stuxnet dropper-infected host; some mirrors. Heavily written up; high memorization.
- **TigerLily, Jackcr** — older challenge samples, sporadic availability.
- **Volatility 3 sample set** — the Volatility 3 repo's `samples/` historically included small synthetic images for unit tests. Status as of June 2026: the GitHub repo is the most reliable source.

The general pattern: Volatility's official sample set is sufficient for *learning Volatility* but inadequate for *evaluating AI forensic capability*, both because the samples are small and synthetic and because they are heavily memorized.

---

### A.14 CFReDS Russian Tea Room

| Field | Value |
|---|---|
| Custodian | NIST CFReDS |
| Year | ~2010 (early CFReDS case) |
| Landing | Reachable from https://cfreds-archive.nist.gov/ |
| Format | DD image |

**Scenario.** A drug-trafficking investigation focused on a fictional location called the "Russian Tea Room." The disk image is from a suspect's machine. Investigators look for evidence of trafficking activity — communications, customer lists, transaction records.

**Investigation questions.** Identify communications with co-conspirators; reconstruct the suspect's contact list; identify any electronic transaction records.

**Materials provided.** Disk image only.

**Expected investigation path.** Standard Windows forensic triage: registry, browser history, email, documents, deleted files.

**Ground truth.** Limited public answer key. NIST documents the questions but not signed answers.

**Difficulty.** Medium. Older case using older Windows (XP era).

**LLM-memorization risk.** Medium. Less famous than the Hacking Case or Data Leakage Case but still indexed.

**Recommended use category.** Practice / additional variety; not a primary scoring target.

**Known issues.** Some referenced links on the NIST archive have aged; verify file integrity before use.

---

### A.15 CFReDS Rhino Hunt

| Field | Value |
|---|---|
| Custodian | NIST CFReDS |
| Year | ~2008 |
| Landing | Reachable from https://cfreds-archive.nist.gov/ |
| Format | Mixed — image fragments plus pcap |

**Scenario.** Stylized "rhino smuggling" case. Image fragments (file carving exercise) plus a packet capture. The case is structured as a series of mini-challenges. It is one of the earliest CFReDS cases and was designed to teach file carving (forensic recovery of files from raw bytes) as much as anything.

**Investigation questions.** Recover the rhino images that have been carved out of the file system. Trace the network capture for indications of file transfer and smuggling negotiation.

**Materials provided.** Three or four small files (depending on revision).

**Expected investigation path.** File carving with `foremost` / `scalpel` / `bulk_extractor`; network analysis of the pcap.

**Ground truth.** Limited; community writeups exist but no signed answer doc.

**Difficulty.** Low to medium. The case is a teaching exercise.

**LLM-memorization risk.** Medium — the case is known but specific carving offsets are not memorable.

**Recommended use category.** File-carving capability test; not a full IR workflow.

---

### A.16 PoliceCTF — Police-Academy-style Forensic CTFs

A loose category of forensic CTF datasets published by police academies, national CERTs, and academic CTF events. Examples:

- **NCL (National Cyber League) Forensic Challenges** — semi-public, occasionally archived.
- **NCFTA / state-level law-enforcement training cases** — typically not public.
- **EU-Cyber-Resilience-Act-driven academies** — emerging post-2024.

These tend to be: small in size, very focused (one or two questions), variable in quality, and almost always lacking durable ground truth. They are useful for **mock realism** (real-investigator workflow) but not for benchmarking.

LLM-memorization risk for these is generally low (low visibility on the public internet) but the trade-off is that ground truth is often only a few flag strings, which is too coarse for evaluating multi-stage AI investigation.

---

### A.17 NSRL — Computer Forensics Reference Data Set

| Field | Value |
|---|---|
| Custodian | NIST (National Software Reference Library) |
| Landing | https://www.nist.gov/itl/ssd/software-quality-group/nsrl |
| Format | RDS (Reference Data Set) hash database |
| Size | Multiple GB compressed (the full Modern RDS is large) |

**What it is.** NSRL is not a forensic case — it is a database of hash values (MD5, SHA1, SHA256) of known, legitimate software files. The forensic use is **whitelist-style triage**: hash everything on a suspect disk against NSRL, exclude the matches (because they are known-good operating-system files, library files, vendor software files), and focus analysis on the unrecognized files.

**Why it matters for AI-DFIR evaluation.** Any agent that does file-level analysis should know that NSRL exists; failing to use it leads to enormous false positives (the agent flagging `kernel32.dll` as suspicious because it doesn't recognize it). Evaluating an agent's effectiveness without NSRL-style filtering is a common methodological flaw.

**Ground truth role.** Not a case; rather, a known-good baseline. Useful as a control in evaluations of false-positive rates.

**Difficulty / memorization / etc.** Not applicable — it's a hash database, not a scenario.

**Known issues.** NSRL is licensed for use in forensic contexts; large-scale redistribution may require attention. The "Modern RDS" is updated; older RDS releases (2016-2020) are commonly used in training because they are smaller and freely mirrored.

---

### A.18 MITRE Cybersecurity Forensic Datasets

MITRE publishes several relevant datasets, none of which is a single "forensic case" in the CFReDS sense:

- **MITRE ATT&CK** — not a dataset; a knowledge base of adversary tactics and techniques. Relevant for evaluation as a vocabulary for **classifying agent findings** (e.g., "the agent identified the attack as T1055 Process Injection").
- **MITRE Caldera** — an adversary-emulation platform. Can generate synthetic incident telemetry on demand. Useful for building custom evaluation cases where ground truth is known by construction.
- **MITRE D3FEND** — defensive countermeasure mapping. Useful for evaluating agent recommendations.
- **MITRE CALDERA-generated PCAPs / telemetry** — published in various academic papers; mirrors exist.

For AI-DFIR evaluation: MITRE data is more useful as a **schema / vocabulary** layer (do the agent's findings map cleanly onto ATT&CK tactics?) than as a benchmark image.

---

### A.19 Magnet Forensics Sample Data (community)

Magnet Forensics (vendor of AXIOM) maintains a community sample set:

- **Landing** — https://www.magnetforensics.com/free-tools/ → "Magnet CTF" page
- **Cases** — various; including their annual CTF cases (Magnet Weekly CTF, Magnet User Summit CTF)
- **Format** — varies; commonly includes mobile (iOS/Android) and Windows
- **Difficulty** — variable; their CTFs are deliberately approachable
- **Ground truth** — published after the CTF window closes
- **LLM-memorization risk** — Medium; CTF writeups proliferate after the close

The Magnet Weekly CTF (running since 2020) has produced a large pool of small forensic challenges with public answers. Each challenge is narrowly scoped (one or two questions) but the aggregate is useful as a breadth tester.

---

### A.20 TraceLabs OSINT CTF Datasets

TraceLabs runs OSINT-focused CTFs (finding missing persons via public information). These are **not traditional DFIR datasets** — they don't involve disk or memory analysis. They are listed in the AI-DFIR adjacent ecosystem because:

- The methodology overlaps with the "intelligence + correlation" side of DFIR
- Some AI-investigation projects fold OSINT and DFIR

For traditional disk/memory/network forensic agent evaluation, TraceLabs is not directly applicable.

---

### A.21 Belkasoft Sample Images

Belkasoft (vendor of X / Triage X) publishes a small community sample set:

- **Landing** — https://belkasoft.com/get → sample images section
- **Cases** — Android device, iPhone backup, Windows USB sample, drone image, others
- **Format** — varies (E01, OFB Belkasoft format, raw)
- **Ground truth** — partial; typically the case ships with a documented summary of what to expect to find
- **LLM-memorization risk** — Low to medium; Belkasoft samples have less viral writeup distribution than CFReDS or Digital Corpora

Belkasoft samples are useful for testing **non-traditional artifact** handling (drones, cars, IoT) where the Windows-centric public datasets fall short.

---

### A.22 Hacking Lab / CTFd Forensic Challenges

A grab-bag category of forensic CTF challenges published on Hack The Box, TryHackMe, CTFd-based platforms, and HackingLab.com:

- **Difficulty** — variable
- **Format** — typically small (single artifact: a pcap, a memory image, a single file)
- **Ground truth** — typically a single flag string
- **LLM-memorization risk** — variable; popular HTB rooms are heavily written-up

For AI-DFIR evaluation: these are **point challenges**, not full investigations. They evaluate a specific forensic capability (decode a custom encoded blob, carve a JPG from a memory dump, etc.) rather than the full investigative loop. Useful for testing one capability at a time.

---

### A.23 VxUnderground Malware Samples

VxUnderground (https://vx-underground.org/) is the largest public malware sample collection. **Not a forensic case dataset** — it is raw malware corpus.

**Why it matters for AI-DFIR evaluation.** Building custom evaluation memory dumps that match production reality requires malware. Researchers building synthetic test cases (a clean Windows VM + a known malware family infection + a snapshot at known time T) often source the malware from VxUnderground because the corpus is broad, family-labeled, and free.

**Considerations.**
- Live malware. Handle in isolated sandboxes; do not detonate on production hosts.
- License: VxUnderground samples are typically published under permissive distribution norms for research, but each sample's chain of custody varies.
- Versioning: malware families evolve; the same family name may map to dozens of distinct samples.

For evaluation purposes, VxUnderground is most useful as the malware-injection source when constructing custom ground-truth memory dumps.

---

### A.24 MalwareBazaar / Abuse.ch Feeds

Abuse.ch operates MalwareBazaar (https://bazaar.abuse.ch/) — a real-time threat intelligence feed of malware samples + IOCs. Related Abuse.ch projects: ThreatFox (IOCs), URLhaus (malicious URLs), SSL Blacklist.

**Why it matters for AI-DFIR evaluation.** Live IOC enrichment. An agent that pulls IP / domain / hash reputation against these feeds can corroborate findings against current threat intelligence. From an evaluation standpoint, **using live feeds during evaluation introduces non-determinism** (the same query at different times returns different results because the feed updates), which complicates reproducibility.

**Recommended evaluation considerations.** Snapshot the feed at a known time and use the snapshot during evaluation, rather than querying live. This preserves reproducibility while still exercising the enrichment workflow.

---

### A.25 VirusShare / VirusTotal Academic

Two complementary services for hash-based malware identification:

- **VirusShare** (https://virusshare.com/) — researcher-distribution of malware samples. Requires an invitation. Useful when building custom evaluation cases.
- **VirusTotal Academic** — VirusTotal offers an academic-research program with elevated API quotas and access to historical analysis data. Required for any agent that does VirusTotal lookups at scale during evaluation.

For evaluation: similar to Abuse.ch feeds, live VirusTotal lookups during evaluation introduce time-dependent variability (a sample may have N detections today and N+1 detections tomorrow as more vendors scan it). Cache responses for reproducibility.

---

## Part B — VIGIA: the Unverified Reference

The Find Evil! / Protocol SIFT 2026 hackathon brief references **VIGIA ground-truth files** attributed to **Anna Tchijova**. These are described as ready-to-use ground-truth annotations for selected forensic challenges (notably DFRWS 2008 and Volatility Cridex). The brief implies VIGIA is a structured machine-readable artifact that any submission can compare its agent output against.

**What is known publicly:**
- The name "VIGIA" appears in the hackathon brief.
- Anna Tchijova is named as the author.
- The pairing with DFRWS 2008 and Volatility Cridex suggests these are the targeted cases.

**What is not findable in public sources (as of June 2026, after multiple search passes):**
- No GitHub repository under "VIGIA" tied to Anna Tchijova.
- No public ArXiv, Zenodo, or academia.edu artifact under that name in DFIR context.
- No LinkedIn / X public artifact tying Anna Tchijova to a published VIGIA ground-truth corpus.
- No Google Scholar entry.

**Probable explanations:**
1. **Internal SANS / Protocol SIFT artifact** — Tchijova may have built VIGIA as internal work for SANS or the Protocol SIFT project, with distribution limited to hackathon participants via the official NotebookLM or Slack rather than the open web.
2. **Slack-only distribution** — distribution may be via the Protocol SIFT Slack workspace, accessible only after hackathon registration.
3. **Embedded in NotebookLM** — VIGIA may be one of the source documents in the official Protocol SIFT NotebookLM (https://notebooklm.google.com/notebook/f0957a60-6fb2-452b-93d4-ecd73ba47779) and never extracted as a standalone artifact.
4. **Not yet published** — the brief may be referencing a future artifact not yet released.

**Where to ask.**
- Protocol SIFT NotebookLM — search for "VIGIA" within the notebook.
- Protocol SIFT Slack — `#general`, `#datasets`, or a direct message to organizers.
- Hackathon Devpost discussion forum.

**Implication for evaluation work.** Until VIGIA is located, any AI-DFIR submission evaluating against DFRWS 2008 or Cridex must construct its own ground-truth scoring. This is a constraint on automation, not on feasibility — both cases have community writeups that can be encoded into structured answer keys by hand. The cost of doing so is meaningful (perhaps an analyst-day per case) but bounded.

If VIGIA does surface and is structured (JSON, YAML, MARKDOWN with consistent headers), it may be directly parseable into a scoring oracle. If it is prose, it requires the same hand-encoding as community writeups.

**Worth noting for evaluation honesty.** A submission that says "we evaluated against VIGIA" when VIGIA is not publicly available is unverifiable. A submission that says "we evaluated against a hand-encoded answer key derived from community writeups for DFRWS 2008 and from the published Volatility tutorial answers for Cridex, both included in this repo" is verifiable and defensible.

---

## Part C — Evaluation Methodologies for AI-DFIR

This section is a deep treatment of the published evaluation methodologies that an AI-DFIR project's accuracy report can engage with — what they measure, what they don't, how to read the headline numbers honestly.

### C.1 DFIR-Metric (arXiv:2505.19973)

**Full citation:** *DFIR-Metric: A Benchmark Dataset for Evaluating LLMs in Digital Forensics and Incident Response*, arXiv:2505.19973, May 2025.

**Author scope.** Academic team (full author list in the paper). The paper is positioned explicitly as a benchmark: it does not propose new tooling, only a way to measure existing tooling.

**Structure — three modules.**

**Module I — Forensic Knowledge MCQs.** 700 multiple-choice questions drawn from professional forensic training material. Covers Windows artifacts, Linux artifacts, mobile, malware analysis, network forensics, legal procedure, chain of custody, anti-forensics, memory analysis. The format is intentionally similar to certification exams (e.g., the EnCase Certified Examiner exam style). The point of Module I is to measure pure **declarative knowledge**: does the model know what a Prefetch file is, what an MFT $UsnJrnl record contains, what the FRE 902(14) rule says about self-authenticating digital records.

**Module II — CTF Challenges.** 150 forensic CTF questions where the answer is a specific string (a flag, a hash, an IP, a process name). These exercise the model's ability to extract a precise answer from a small piece of evidence — typically a single file or small pcap. The format is **single-question forensic puzzle**: "Given this memory dump, what was the malicious process's PID?" The CTF set is drawn from various publicly available CTFs and filtered for unambiguous single-string answers.

**Module III — Realistic NIST Disk and Memory Tasks.** 500 tasks built on top of real NIST CFReDS disk and memory cases (and adjacent). These are **investigation tasks**, not single questions: the model is asked to perform actions ("identify the persistence mechanism," "list all installed hacking tools," "determine the timeline of the initial compromise") on a real forensic image. Each task has a graded answer set — partial credit is awarded for partial completion. The grading rubric is published in the paper.

**Models evaluated.** 14 models, including GPT-4.1 (and the GPT-4o variants), Claude 3.5 Sonnet, Claude 3 Opus, Gemini 1.5 Pro, several Llama 3 variants, DeepSeek, Mistral Large, and others. The paper covers both commercial and open-weight models.

**Headline results.**
- **Module I (MCQs).** Best model: GPT-4.1 at **92.75%**. Most frontier models cluster in the 80-92% range. Open-weight models trail by 10-20 points.
- **Module II (CTFs).** Best model: in the 60-75% range. Models that succeed at the MCQ level often fail at extracting precise strings.
- **Module III (Realistic NIST tasks).** **0% complete solutions across all 14 models.** Partial credit was the only credit awarded. The paper's key finding is that **practical, multi-step forensic investigation is not yet within the capability of any tested LLM**.

**Task Understanding Score (TUS).** Because Module III was producing near-zero accuracy across the board (making standard accuracy meaningless as a discriminator), the authors introduce TUS — a measure of whether the model **understood the task** even if it failed to complete it. TUS is computed by asking the model to enumerate the steps it would take, and grading the plan rather than the result. Models that scored 0% on Module III still scored 30-70% on TUS, suggesting models understand DFIR conceptually but cannot execute it autonomously.

**What counts as a "complete solution."** Module III defines complete solution as: producing all of the required findings for a task at the correct level of specificity, citing the artifacts that support each finding, and not introducing any hallucinated artifacts or paths. A finding is **invalidated** if it cites a path / file / hash that does not exist in the image. This is a strict criterion — a model that gets most things right but invents one path counts as not-complete on that task.

**Specific failure mode the paper highlights.** "Models hallucinate files, bash commands, paths or libraries that are absent from the image." This finding is the empirical basis for the "anti-hallucination" track that several hackathon submissions are targeting.

**What DFIR-Metric measures well.**
- Breadth of forensic knowledge (Module I).
- Atomic forensic extraction skill (Module II).
- Whether a model can produce a plausible investigation plan (TUS).
- Whether a model can complete an end-to-end investigation without hallucinating (Module III, complete-solution criterion).

**What DFIR-Metric does NOT measure.**
- Tool-use proficiency in a real shell environment (the benchmark is text-based; models are not given live access to plaso, Volatility, etc., during evaluation).
- Self-correction or iterative pivot (the benchmark is one-shot or limited-turn).
- Report generation quality.
- Time-to-result (no latency metric).
- Cost-to-result (no token-budget metric).
- Run-to-run consistency (the benchmark reports averaged scores but not variance).

**Methodological notes for any project evaluating against DFIR-Metric.**
- The Module III ground truth is held by the authors; full access requires contacting them or working from the partial public release.
- Module I and Module II have public release subsets that are usable for self-evaluation.
- The benchmark assumes a single-pass evaluation; testing an iterative agent's performance requires adapting the protocol.

---

### C.2 CyberSleuth (arXiv:2508.20643)

**Full citation:** *CyberSleuth: Autonomous Blue-Team LLM Agent for Web Attack Forensics*, arXiv:2508.20643, August 2025.

**Author scope.** Academic team; the paper positions CyberSleuth as both a tool and an evaluation framework.

**Scope.** CyberSleuth is a multi-agent system for **web attack forensics specifically**. The agent reads packet captures and web server logs, identifies suspicious activity, attributes CVEs, and produces a structured incident summary. It does NOT cover disk forensics, memory forensics, or non-web incidents.

**Architecture under test.** The paper compares **three architectures**:
1. **Single agent.** One LLM with access to all tools.
2. **Flat multi-agent.** N specialist agents (packet parser, log parser, CVE lookup, attribution, summarizer) coordinated by a flat orchestrator.
3. **Nested hierarchical multi-agent.** Agents organized in a hierarchy with sub-team leads.

Each architecture is tested with **six LLM backends** (GPT-4o, GPT-5, Claude 3.5 Sonnet, Claude 3 Opus, DeepSeek R1, and Llama 3 70B).

**Evaluation set.** 30 controlled web-attack cases. Each case is a constructed pcap + log set with known ground truth (which CVE was exploited, which endpoints were attacked, what response was sent). Ground truth was authored by the paper team alongside the case.

**Headline result.** Best architecture × backend combination achieved **80% accuracy**. The architecture comparison: **flat multi-agent beat nested hierarchical multi-agent across all backends**, and **flat multi-agent beat single agent on harder cases (those requiring cross-source correlation)** but single agent kept up on easier cases.

**Key methodological observation from the paper.** "Multi-agent specialisation is key to sustained reasoning" — the paper attributes flat multi-agent's win to the reduced context-load per specialist (each specialist handles only its share of the evidence). "Simple orchestration outperforms nested hierarchical architectures" — nested hierarchies introduced coordination overhead that didn't pay off at this scale.

**What CyberSleuth measures well.**
- Comparative architecture performance under controlled conditions.
- Multi-source correlation success rate (pcap + logs at known timestamps).
- CVE attribution accuracy.

**What CyberSleuth does NOT measure.**
- Disk or memory forensic capability.
- Performance on real-world (non-constructed) evidence.
- Hallucination rate specifically (the paper reports accuracy but does not distinguish accuracy failures from outright hallucinations).
- Long-running investigations (the cases are short).

**Methodological notes.**
- The 30-case set is small. The variance per (architecture, backend) cell is meaningful; the paper reports averages but the spread is wide.
- Cases are constructed; real-world web attacks may exercise different failure modes.
- The paper does not include any architectural anti-hallucination gate — it acknowledges "long-term reasoning, contextual memory, consistent evidence correlation" as open problems and treats them as future work.

**For an AI-DFIR project's evaluation.** CyberSleuth's case set is the closest publicly-documented multi-agent web-forensics benchmark. Its architecture comparison is generalizable: if a project chooses single-agent versus multi-agent, CyberSleuth's evidence is that **flat multi-agent is the default winner** for cross-source-correlation problems at this scale, and that nesting agents adds coordination cost without commensurate benefit.

---

### C.3 Digital Forensics in the Age of LLMs (arXiv:2504.02963)

**Full citation:** *Digital Forensics in the Age of Large Language Models*, arXiv:2504.02963, April 2025. Survey paper.

**Type.** Survey, not a benchmark. The paper does not present its own numerical results; it summarizes the landscape of LLM applications in forensics.

**Key topics covered.**
- Use cases: triage, log summarization, report drafting, IOC extraction, malware classification, evidence translation.
- Failure modes: hallucination, non-determinism, prompt sensitivity, broken chain of custody, no community standards.
- Proposed direction: human-in-loop deployment, grounding via deterministic-tool outputs, restricted-domain fine-tuning, evaluation against shared benchmarks (the authors specifically point to DFIR-Metric as the emerging standard).

**Key quote.** "Non-determinism undermines reproducibility — LLMs are inherently probabilistic and may produce variable outputs." This is the paper's central pitch for why deterministic forensic tools must remain the source of truth and LLMs must operate as orchestrators / translators of those tools' outputs rather than as standalone analysts.

**Proposed evaluation criteria** (the paper does not implement these — it proposes them):
1. **Faithfulness** — does the LLM accurately reflect what the tool output said?
2. **Determinism / reproducibility** — does the same input produce the same output across runs?
3. **Chain-of-custody integrity** — can each claim be traced back to a tool invocation?
4. **Hallucination rate** — what fraction of generated claims are not supported by evidence?
5. **Time and cost efficiency** — what's the budget required per case?

The paper does not specify how each of these should be operationalized. That gap is exactly the gap a serious accuracy report can fill.

**For AI-DFIR evaluation.** This survey provides the vocabulary (faithfulness, determinism, hallucination) more than measurement protocols. Use it to frame the evaluation, not to define the metric.

---

### C.4 NIST SP 800-53 / 800-218 evaluation overlay

NIST Special Publications 800-53 and 800-218 are control catalogs (not benchmarks). They are relevant to AI-DFIR evaluation because **a forensic tool that produces evidence used in regulated environments is implicitly evaluated against the controls a customer organization is required to implement**. If the tool violates the controls the customer must comply with, the tool cannot be deployed.

**NIST SP 800-53 (Rev 5)** — Security and Privacy Controls for Information Systems and Organizations. The catalog is organized into 20 control families:

- **AC** (Access Control) — relevant for: read-only mounting, examiner-portal access controls, role-based access to evidence.
- **AT** (Awareness and Training) — relevant for: documenting what AI augmentation does so analysts understand the system.
- **AU** (Audit and Accountability) — **directly relevant**: a forensic AI tool that does not produce a full audit trail of its actions cannot meet AU-2 (Event Logging), AU-3 (Content of Audit Records), AU-12 (Audit Record Generation).
- **CA** (Assessment and Authorization) — relevant for the deployment process.
- **CM** (Configuration Management) — relevant for: locking down the tool's configuration in deployed environments.
- **CP** (Contingency Planning) — adjacent.
- **IA** (Identification and Authentication) — relevant for: who is invoking the AI agent, how is that identity attested.
- **IR** (Incident Response) — directly the operational context.
- **MA** (Maintenance) — adjacent.
- **MP** (Media Protection) — relevant for: how the AI agent handles evidence media (read-only mounts, no writes).
- **PE** (Physical and Environmental Protection) — out of scope for software-only forensic AI.
- **PL** (Planning) — adjacent.
- **PM** (Program Management) — adjacent.
- **PS** (Personnel Security) — adjacent.
- **RA** (Risk Assessment) — relevant for: how the customer assesses the AI agent's residual risk.
- **SA** (System and Services Acquisition) — relevant for procurement.
- **SC** (System and Communications Protection) — relevant for: how the agent isolates evidence (sandboxing, network segregation).
- **SI** (System and Information Integrity) — **directly relevant**: SI-7 (Software, Firmware, and Information Integrity) addresses whether the AI agent's outputs can be tampered with.
- **SR** (Supply Chain Risk Management) — relevant for: where the LLM weights come from.

**NIST SP 800-218** — Secure Software Development Framework (SSDF). Less applicable to AI-DFIR evaluation directly; relevant if the project is shipping a tool that ends up in customer environments and must be developed against SSDF practices.

**Practical implication for AI-DFIR evaluation.** An accuracy report that engages with 800-53 will identify which specific controls the project respects and which it deliberately defers. Examples of typical engagement:

- **AU-2 / AU-3 / AU-12.** The system must log all agent actions in a tamper-evident form. Evaluation: can a forensic auditor recreate the agent's decision-making from the log alone?
- **SI-7.** Outputs must be integrity-checked. Evaluation: are findings signed, hashed, or otherwise tamper-evident before being stored?
- **MP-2 / MP-4.** Evidence media must be protected (read-only). Evaluation: does the system enforce read-only mount, or does it merely advise it?

**Note.** 800-53 is not a benchmark. There is no "score" on 800-53. It is a checklist of practices. The honest evaluation engagement is to enumerate the controls relevant to the system's deployment context and show how each is addressed.

---

### C.5 Daubert standard considerations

**Source.** *Daubert v. Merrell Dow Pharmaceuticals, Inc.*, 509 U.S. 579 (1993). Supreme Court decision establishing the standard for admissibility of expert testimony in U.S. federal courts.

**The Daubert criteria** (the "Daubert factors" — non-exhaustive but canonical):

1. **Testing.** Has the technique or theory been tested?
2. **Peer review and publication.** Has it been subjected to peer review and publication?
3. **Known or potential error rate.** What is the known or potential rate of error of the technique?
4. **Standards.** Are there standards controlling the technique's operation, and are they maintained?
5. **General acceptance.** Is the technique generally accepted in the relevant scientific community?

**Application to forensic AI.** Each of these is a question a defense attorney can ask at cross-examination, and each requires a defensible answer:

1. **Testing.** Has the AI system been tested on independent forensic challenges with known ground truth? An evaluation that includes a documented benchmark run (with reproducible commands, fixed seeds, fixed model versions) is the answer.
2. **Peer review.** Has the methodology been described in a paper or technical report a peer can critique? The AI-DFIR field's published literature (DFIR-Metric, CyberSleuth, etc.) provides the comparative basis.
3. **Error rate.** **This is the hardest one for AI tools.** A defense attorney will ask "what is the error rate of this LLM on disk forensics?" An honest answer must include hallucination rate, false-positive rate, false-negative rate, and the variance of each across runs. Any honest evaluation must measure these.
4. **Standards.** Are there published standards governing operation? NIST SP 800-86 (Guide to Integrating Forensic Techniques into Incident Response) and SP 800-101r1 (Guidelines on Mobile Device Forensics) exist; AI-augmented forensics has no parallel standard yet.
5. **General acceptance.** Has the community broadly accepted AI augmentation? The community is currently divided. This factor cuts against any forensic AI tool seeking court admission today.

**Practical implication for AI-DFIR evaluation.** A project whose evaluation report can answer Daubert factor 3 (a quantified error rate with confidence intervals) and factor 1 (a reproducible testing protocol) is positioned to engage seriously with courtroom-grade discussion. A project whose evaluation reports only ad-hoc anecdotal results cannot.

**Note: Daubert applies in federal court. State courts may apply Frye (older, simpler "general acceptance" standard) or local variants.**

---

### C.6 FRE 707 — Federal Rule on AI Evidence (post-2024)

**Source.** Federal Rules of Evidence Rule 707, as adopted via the December 2024 amendments to the FRE. (FRE 707 was promulgated by the Committee on Rules of Practice and Procedure and adopted by the Judicial Conference, taking effect in 2024.)

**Background.** FRE 702 governs admissibility of expert testimony generally (the Daubert standard is operationalized through FRE 702). FRE 707, new, specifically addresses **evidence generated by artificial intelligence**. The rule provides:

> Machine-generated evidence is admissible to the same extent as expert testimony under Rule 702 if its proponent can demonstrate:
> (a) the AI system's purpose and use are appropriate to the evidence sought;
> (b) the AI system is reliable, including consideration of its testing, error rate, and validation;
> (c) the system was operated correctly in the instance at issue;
> (d) the operator was competent to interpret the AI system's output.

The rule reflects a deliberate decision by the rulemaking body to **import Daubert-style reliability analysis into AI-generated evidence**, rather than treating AI outputs as ordinary documentary evidence.

**Implications for AI-DFIR evaluation.**

(a) **Purpose and use.** The evaluation must articulate what the AI system is intended to do and what evidentiary claims it supports. An AI agent that drafts findings must distinguish between findings it has substantiated and findings it has merely surfaced for human review.

(b) **Reliability** (testing / error rate / validation) — this is the substance. The system needs:
- A documented testing protocol against public datasets with known ground truth.
- An error rate that can be cited.
- Validation work that compares system output against ground truth at scale.

(c) **Correct operation.** The system's operation in the specific case must be reproducible. Audit logs that allow reconstruction are the deliverable.

(d) **Operator competence.** The human analyst running the system must be able to interpret its output. Evaluation: is the system's output expressed in a way an analyst can reason about (not just trust)?

**For AI-DFIR projects.** FRE 707 is the legal scaffolding around which any "court-admissible forensic AI" claim must be built. Note: **most current projects, including Protocol SIFT itself, explicitly disclaim court-admissibility** and operate as analyst-augmentation rather than evidence-generation. That disclaimer is itself a position; the alternative is to commit to FRE 707 engagement.

**Caveat.** State courts have not uniformly adopted FRE 707 analogues yet. The federal rule applies in federal court; state-court admissibility of AI-generated forensic evidence is a patchwork in 2026.

---

## Part D — Hallucination / Accuracy Metric Families

This section catalogs the metric families a serious AI-DFIR evaluation can engage with. It does not prescribe which to use.

### D.1 Precision / Recall / F1 — classical IR metrics

The classical information-retrieval triplet, applied to a finding-vs-ground-truth setting:

- **True Positive (TP).** Agent produces a finding that matches a ground-truth finding.
- **False Positive (FP).** Agent produces a finding with no ground-truth match, but the underlying artifact exists.
- **False Negative (FN).** Ground-truth finding not produced by agent.

Plus the AI-specific variant:

- **Hallucination (HALL).** Agent produces a finding that cites an artifact / path / file / hash that does NOT EXIST in the evidence. Verifiable by running `find`, `hash`, or `grep` against the mounted image.

**Derived metrics:**
- **Precision** = TP / (TP + FP + HALL)
- **Recall** = TP / (TP + FN)
- **F1** = 2 × Precision × Recall / (Precision + Recall)
- **Hallucination rate** = HALL / (total agent findings)

**What this captures.** End-state accuracy of the agent's findings. **Treats hallucinations as worse than false positives** — a hallucination is a finding that cites an artifact that does not exist, which is a different failure mode from a finding about a real artifact that just isn't the smoking gun.

**What this does NOT capture.** Process quality (did the agent reason well?), efficiency (how many tool calls did it take?), confidence calibration (did the agent express appropriate uncertainty?), or coverage of negative findings (what did the agent declare it did NOT find?).

---

### D.2 Hallucination rate — variant definitions

Different research traditions define hallucination differently. Three distinct variants matter:

**NIH-style hallucination.** Used in medical AI literature. A claim is hallucinated if it is not supported by the source(s) the model was given. Operationally: take each claim, retrieve the source, check whether the source supports the claim.

**Microsoft-style hallucination** (from Microsoft's responsible AI research). A claim is hallucinated if it contains a factual assertion that is not verifiable from any available source — even a source not given to the model. Operationally: take each claim, verify against the entire available knowledge base.

**Cyber Triage / DFIR-specific hallucination.** A claim is hallucinated if it cites an artifact (file, path, hash, IP, registry key, process name) that does not exist in the evidence. Operationally: extract the entity from the claim, run a deterministic lookup against the mounted evidence, check for presence.

**The choice matters.** A model that paraphrases evidence accurately but produces no novel claims has 0% NIH-style hallucination, may have some Microsoft-style hallucination (paraphrases may drift from external truth), and has 0% DFIR-specific hallucination. A model that invents a process name has 0% NIH-style hallucination if the cited source is irrelevant, high Microsoft-style hallucination, and high DFIR-specific hallucination.

**For AI-DFIR evaluation:** the DFIR-specific variant is the one Daubert factor 3 is asking about. An agent's published "hallucination rate" claim should specify which variant.

---

### D.3 Faithfulness vs Factuality

A subtle but important distinction from the RAG literature:

**Faithfulness** — does the model's output reflect what its sources said? A faithful model never contradicts its sources. A faithful model can still be wrong if its sources are wrong.

**Factuality** — does the model's output match objective truth? A factual model is right about the world. A factual model can be unfaithful if it relies on world knowledge rather than the sources it was given.

**For AI-DFIR.** Forensic tooling values **faithfulness over factuality**. The deterministic tool output is the ground truth for the agent's purposes; the agent's job is to faithfully report what the tool said. If the agent contradicts the tool because the agent "knows" the tool is wrong, that is a failure of faithfulness — and in a forensic context, dangerous, because the audit trail is the tool output, not the LLM's prior beliefs.

---

### D.4 Calibration metrics

**Calibration** measures whether the model's expressed confidence matches its actual accuracy. A well-calibrated model that says "I'm 80% confident" is right 80% of the time on those claims.

**Expected Calibration Error (ECE).** Bin predictions by confidence (e.g., 0.0-0.1, 0.1-0.2, ..., 0.9-1.0). For each bin, compute the average confidence and the actual accuracy. ECE is the weighted average of the absolute difference between average confidence and actual accuracy.

**Brier score.** Mean squared error between confidence and outcome (1 if right, 0 if wrong). Lower is better. Brier penalizes both miscalibration and inaccuracy together.

**AURC (Area Under Risk-Coverage curve).** Risk-coverage curves plot the risk (error rate) against coverage (fraction of predictions accepted) when ranking predictions by confidence. A well-calibrated model has low AURC.

**For AI-DFIR.** An agent that expresses uncertainty on uncertain findings and confidence on confident findings is more useful than one that expresses uniform confidence. Calibration metrics let evaluation engage with that property directly.

---

### D.5 Epistemic honesty — abstention metrics

Distinct from calibration: did the model abstain (decline to answer / decline to assert) when it should have? Variants:

- **Coverage** — fraction of questions / sub-investigations the model attempted.
- **Abstention recall** — of questions the model should have abstained on (because the evidence was insufficient), what fraction did it actually abstain on?
- **Abstention precision** — of the questions the model abstained on, what fraction were truly insufficient-evidence?

A common pathology: models given enough hints answer everything, abstain on nothing, and produce confidently-wrong answers. A model with high abstention recall is honest about uncertainty.

**For AI-DFIR.** The judge persona known to value epistemic honesty (Rob T. Lee, in this hackathon's specific context) has explicitly said the absence of false confidence is more valuable than answer breadth — "know what you couldn't find as much as what you did find." An evaluation that does not measure abstention misses one of the key value dimensions.

---

### D.6 Citation accuracy

For agents that produce findings with citations to specific evidence:

- **Citation existence** — does the cited source exist? (0% means hallucinated citation; 100% means all cited sources are real.)
- **Citation support** — does the cited source actually support the claim? (Even real citations can be misapplied.)
- **Citation precision** — is the claim's scope no broader than what the citation supports?
- **Citation recall** — does the claim cite all the sources that bear on it?

**Operationalization.** For each (claim, citation) pair, retrieve the citation, run an alignment check (substring match for verbatim quote, NLI for paraphrase). The match rate is the citation accuracy.

---

### D.7 Atomic-claim decomposition — FActScore, CiteCheck

The state-of-the-art for content-grounded evaluation involves **decomposing each generated response into atomic claims**, scoring each atomically, and aggregating.

**FActScore** (Min et al., 2023). Decomposes a generation into atomic factoids; for each, retrieves supporting evidence and labels as Supported, Not Supported, or Irrelevant. The system's FActScore is the fraction of atomic claims that are Supported. Originally developed for biography generation but the methodology generalizes.

**CiteCheck** (arXiv:2502.10881, February 2025). *Accurate Citation Faithfulness Detection*. Decomposes an answer into atomic claims and checks each against the cited passage; produces a faithfulness verdict per claim and aggregates. Framed as a detection benchmark and as a dataset.

**For AI-DFIR.** Atomic decomposition is the path to fine-grained evaluation. A finding like "PID 1234 svchost.exe spawned cmd.exe at 03:42:17 UTC" contains four atomic claims (the PID, the process name, the child process name, the timestamp). Each is independently verifiable against tool output. Aggregate per-finding score = fraction of atomic claims supported.

The cost is engineering: atomic decomposition + per-atom verification is substantially more work than coarse end-to-end correctness scoring. It also produces much more diagnostic information about *what* the agent gets wrong.

---

### D.8 Span-level grounding (arXiv:2504.18639)

**Source.** *Verifiable Generation with Subsentence-Level Fine-Grained Citations*, arXiv:2406.06125 (June 2024) and follow-up arXiv:2504.18639 (April 2025).

Sentence-level citation is too coarse — a sentence may contain multiple facts, some supported and some not. **Sub-sentence (span-level) grounding** assigns each token range in the generation to a span in the source. Evaluation: for each generated span, is it grounded in the cited source span?

For forensic findings: a single finding sentence may cite an audit-ID. Span-level grounding asks whether the cited audit-ID's stored output actually contains the substring corresponding to the finding's specific claim about an IP / process / hash.

This is the methodology behind several proposed AI-DFIR architectural anti-hallucination gates: substring-verifying the cited byte range against the finding text.

---

### D.9 Tool-call accuracy — NABAOS (arXiv:2603.10060)

**Source.** *NABAOS: Tool Receipts, Not Zero-Knowledge Proofs*, arXiv:2603.10060, March 2026.

NABAOS (Norway/Anthropic/Berkeley Authentication Of Stuff — name reconstructed from context) proposes a runtime that emits **HMAC-signed receipts** of every tool execution. The LLM's later claims about tool execution can be cross-checked against the signed receipts. This catches three classes of hallucination:

1. **Fabricated tool references** — the LLM claims a tool was called when it was not. Detection rate: **94.2%**.
2. **Count misstatements** — the LLM claims a different count (number of files, number of results) than the receipt shows. Detection rate: **87.6%**.
3. **False absence claims** — the LLM claims a tool did not find something when it did. Detection rate: **91.3%**.

NABAOS operates as **post-hoc detection** (<15ms verification overhead per response), classifying the LLM output by epistemic source. It does not function as a hard rejection gate — the system reports detection results to a downstream consumer who decides how to act.

**For AI-DFIR evaluation.** NABAOS is the strongest published prior art on tool-call faithfulness. Its detection rates (94/87/91%) are the bar against which any tool-faithfulness metric should be calibrated. A system that achieves higher detection rates than NABAOS at lower overhead is meaningfully advancing the state of the art; a system that does not approach NABAOS's numbers is below the literature baseline.

**Limitation of NABAOS for the DFIR setting.** NABAOS signs *that a tool was called and what it returned*. It does not verify that a claim like "PID 4 SYSTEM ran child process powershell.exe" actually appears in the byte range of the tool's stored output. That additional verification — content-level rather than execution-level — is a layer above NABAOS.

---

### D.10 Other metric families to know

**ROUGE / BLEU / METEOR.** Lexical-overlap metrics from machine translation, generally **inappropriate for forensic findings evaluation** because lexical overlap is not what matters. A finding can paraphrase the ground truth perfectly and score zero on BLEU. Mentioned only to note that these are usually wrong choices in the DFIR setting.

**BERTScore.** Embedding-similarity metric. Better than lexical overlap for paraphrase-tolerance but still not specific to claim verification.

**LLM-as-judge / G-Eval.** Use a separate LLM to evaluate the candidate's outputs against ground truth. Useful when ground truth is complex enough that exact-match scoring is too brittle. **Introduces its own bias** (the judge LLM has biases) and **non-determinism** (the judge LLM's score varies across runs); pair with calibration of the judge against human ratings on a sample.

**RAGAS metrics** (the open-source RAG evaluation framework). Faithfulness, Answer Relevance, Context Precision, Context Recall. Designed for RAG, applicable to AI-DFIR with adaptation.

**TruLens evaluations.** Similar to RAGAS; commercial / open-source toolkit for LLM-app evaluation including faithfulness and relevance.

---

## Part E — Baseline Establishment for AI-DFIR Systems

For an AI-DFIR project (or any agent system) to make accuracy claims, **the comparison baseline must be controlled**. This section enumerates the variables that need to be held constant for a fair comparison.

### E.1 What is a "baseline"?

A baseline is the comparison system. In the Find Evil! / Protocol SIFT hackathon context, the **most natural baseline is "vanilla Protocol SIFT"** — Rob T. Lee's reference Claude Code skill bundle, installed stock, run on the same evidence with the same prompt patterns.

Protocol SIFT itself is a **Claude Code configuration**, not a custom agent runtime. The skill files (`skills/memory/`, `skills/timeline/`, `skills/filesystem/`, `skills/windows-artifacts/`, `skills/yara/`) are markdown specifications that Claude Code's skill system loads as context. The `settings.json` enforces read-only operation. The system is essentially "Claude Code + DFIR skill files + read-only enforcement."

This makes the baseline definition tractable:
- **Baseline = stock Protocol SIFT install + fixed Claude Code version + fixed Anthropic model version + identical evidence mount + identical opening prompt.**

Any deviation from any of these variables breaks the comparison.

### E.2 Variables that must be held constant for comparison

The variables that, if unmatched, render the comparison invalid:

**Model identity and version.** "Claude 3.5 Sonnet" is not enough — the snapshot identifier (e.g., `claude-3-5-sonnet-20241022` vs `claude-3-5-sonnet-20250115`) matters because Anthropic updates models. Same for OpenAI: `gpt-4-1106-preview` differs from `gpt-4-0125-preview`. **Always record the exact model snapshot.**

**Temperature and sampling.** Temperature 0 reduces non-determinism but does not eliminate it (top-p sampling, batching effects, server-side variation). Higher temperatures produce different output. Record `temperature`, `top_p`, `top_k` if applicable.

**Context budget.** Total tokens available, system prompt budget, conversation budget. A baseline with 200K context comparing to a system with 1M context is not the same comparison.

**Tool budget.** Maximum tool calls per turn, maximum tool calls per session, maximum total session duration. A system allowed 100 tool calls outperforms one limited to 10 trivially.

**Prompt.** The exact system prompt and user prompt. Differences in framing, role assignment, or output format constraints affect outcomes significantly.

**Evidence mount.** The exact same image, mounted the same way, with the same paths. Differences in path conventions (case sensitivity, trailing slashes) can affect agent behavior.

**Seed.** For systems exposing a seed parameter, the same seed. For systems that don't, run N replicates and report variance.

**Pre-loaded knowledge.** What's in the agent's context window at start. Pre-loading evidence summaries vs starting fresh changes outcomes.

**External lookups.** If the agent queries external services (VirusTotal, MalwareBazaar), pin the queries to a fixed time snapshot. Live queries introduce time-dependent variability.

### E.3 Run-to-run variance — the under-reported problem

Even with everything controlled, the same input can produce different outputs across runs. Causes:

- Server-side load balancing affecting batch composition.
- Stochastic dropout in some model serving paths.
- Tool-call interleaving differences.

**Honest evaluation reports N replicates** (typically N = 5 to 10) and provides per-metric mean + variance, not a single-run number. A single-run claim "we got 87% accuracy" omits the variance that may span ±10 percentage points across replicates.

### E.4 Cross-system comparisons

If the comparison is across **agent frameworks** (Claude Code vs OpenClaw vs LangGraph vs CrewAI), additional variables matter:

- **Framework version.** Claude Code 2.1 differs from 2.5; the harness behavior changes.
- **Framework configuration.** What hooks are enabled, what settings.json contains.
- **Underlying transport.** MCP server config, tool registration.

It is generally **not fair** to compare an early-2025 Claude Code build to a late-2026 OpenClaw build because the underlying capability of the frameworks has shifted. Comparisons should be **within a fixed framework + fixed configuration** OR **explicitly cross-version with all versions disclosed**.

### E.5 Negative controls

A strong evaluation also runs:

- **Baseline without LLM** — a script that just runs the underlying forensic tools without LLM orchestration. What's the LLM actually adding?
- **LLM without forensic tools** — the LLM with general knowledge alone, no tool access. What's the tool integration adding?
- **Random / scripted baseline** — a system that produces fixed boilerplate findings. Random and scripted should be the floor; the agent should obviously beat both.

When the agent fails to beat the scripted baseline, that is a finding.

---

## Part F — Public Answer Key Sources

This section catalogs where ground truth for the canonical DFIR cases can be obtained.

### F.1 NIST Data Leakage Case answer PDF

**Primary URL.** `https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf`

**What it contains.** 31 numbered questions with answers, each tied to specific supporting artifacts (registry keys, files, MFT records). Structured enough to parse semi-automatically: question heading → answer → "Supporting evidence: [path]".

**Status.** Public, free, hosted by NIST. Stable URL since 2015.

**Usage notes.** The PDF is parseable but not ideally so — some answers span multiple pages and reference figures. A clean extract requires careful PDF processing (the `pdftotext` utility handles it tolerably; OCR is not required because the PDF is text-based).

**Provenance.** The CFReDS team (Yongseok Kim et al.) authored the answer key alongside the case.

### F.2 NIST Hacking Case public writeups

**Status.** No single canonical NIST answer document. The community has reconstructed the answers many times.

**Notable writeups.**
- `intrinsicode.net/2021/05/19/cfreds-hacking-case-report/` — detailed walkthrough by an independent researcher.
- `zarat.hatenablog.com/entry/2021/12/19/223735` — Japanese-language writeup; thorough.
- GitHub: search `cfreds hacking case` for many community writeups, e.g., the `n3xtchen/wiki` repo and several university CS course pages.

**Quality varies.** Writeups disagree on minor details (the exact form of the MAC address representation, whether the case includes the on-disk pcap). The convergent consensus on the headline answers (Greg Schardt is the suspect; MAC address is X; hostname is Y) is reliable.

**Usage for ground truth.** Constructing a structured answer key requires manual triage across multiple writeups. Estimated effort: half a day of careful comparison.

### F.3 Nitroba

**Status.** The official solution PDF is **password-protected** and distributed only to accredited faculty. Community writeups exist but are sparse.

**Public sketch.** The community knows the suspect was identified via the willselfdestruct.com POST traffic and that the IP / MAC maps back to a specific student via DHCP traces. Specific name and DHCP details are circulating but not authoritatively confirmed.

**Usage for ground truth.** Manual reconstruction of the answer chain from the pcap is the most defensible approach. Treat anything in community writeups as "consistent with reconstruction" not "authoritative ground truth."

### F.4 DFRWS challenges

**Status.** Winning entries published in the `/results` folder of each challenge's GitHub repository (`github.com/dfrws/dfrwsYYYY-challenge`).

**Format.** PDF writeups by the winning teams. Detailed but not flat answer keys — each writeup walks through the team's investigation, including dead ends.

**Usage for ground truth.** Cross-reference the top 2-3 winning writeups; where they agree, that's high-confidence ground truth; where they disagree, treat as ambiguous.

### F.5 M57-Jean — widely-distributed answers

**Status.** The official answer is in a password-protected PDF; the answer chain has been **published in dozens of locations** including academic course slides, Medium posts, GitHub, and SANS course materials.

**Warning.** **High LLM contamination.** Any model trained on the public web is likely to have seen M57-Jean answers. Using M57-Jean for AI accuracy claims requires explicit memorization controls (paraphrased questions, fresh model with cutoff before the case became viral).

### F.6 CTF writeups — Medium / GitHub / blog ecosystem

For the Hadi cases, the DFRWS Android cases, the Magnet Weekly CTF, and various Hack The Box / TryHackMe rooms, the ground truth exists primarily as community writeups. The pattern:

- Search `<case name> writeup` on Google, GitHub Search, and Medium.
- Cross-reference multiple writeups; where they converge, treat as ground truth.
- Reasonable confidence threshold: 3 independent writeups agree.

This is **manual ground-truth construction**. It is the labor-intensive backbone of any honest AI-DFIR evaluation against the community case corpus.

### F.7 Tools that can help parse ground truth at scale

- **`pdftotext`** (Poppler) — converts PDF answer keys to plaintext.
- **`pandoc`** — converts HTML writeups to clean Markdown for structured parsing.
- **Simple Python scrapers** — to collect community writeups from known URLs.
- **Manual review** — irreplaceable. Auto-extraction always produces residual errors.

---

## Part G — Common Evaluation Pitfalls

Pitfalls that consistently appear in AI-DFIR evaluation work and that an honest accuracy report should explicitly avoid (or, if unavoidable, explicitly acknowledge).

### G.1 Dataset contamination

**Pitfall.** Evaluating an LLM against a case whose answers are widely published online. The model produces correct answers not by working the case but by recalling its training data.

**Why it bites.** A model that scores 95% on the NIST Hacking Case may have a 0% real-world capability and 95% recall accuracy. Conflating the two misleads readers about what the system can actually do.

**Mitigations.**
- Choose cases with non-public answer keys (Nitroba, recent Hadi cases).
- Paraphrase questions so the canonical wording isn't a search anchor.
- Run with models whose training cutoff predates the case publication.
- Compare against a "model alone, no evidence access" baseline — if the model gets the answer with the evidence redacted, you have contamination.

**Honest disclosure.** "We evaluated against the NIST Hacking Case knowing it is heavily indexed. Our model's performance on this case should be interpreted as performance-on-recall-plus-evidence-access, not performance-on-fresh-evidence-only."

### G.2 Cherry-picking cases

**Pitfall.** Reporting results on the 3 cases the agent did well on, omitting the 5 cases where it failed.

**Why it bites.** A 90% accuracy on a cherry-picked subset is meaningless. A 60% accuracy on the full set is informative.

**Mitigations.**
- Pre-register the case set before running evaluations.
- Report all cases attempted, including failures.
- If reporting a subset, justify the subset criterion and report the omitted cases' results in an appendix.

### G.3 Comparing across different model versions

**Pitfall.** Comparing system A on `claude-3-5-sonnet-20241022` to system B on `claude-3-5-sonnet-20250115`. The underlying model is different; the comparison is not measuring the systems' contributions.

**Mitigations.**
- Pin model versions in the evaluation protocol.
- Run both systems on the same model snapshot.
- Report the exact model identifier.

### G.4 Confusing "happened to find it" with "reliably finds it"

**Pitfall.** Single-run results presented as the system's typical performance. The system happened to get it right this time; if you re-ran, it might fail.

**Why it bites.** Forensic claims need to be reliable. A system that works 60% of the time is fundamentally different from one that works 99% of the time, but a single successful run shows neither.

**Mitigations.**
- Run N replicates (N ≥ 5).
- Report mean + standard deviation per metric.
- Report success rate, not just success existence.

### G.5 Ignoring negative tests

**Pitfall.** Measuring only what the system found correctly; ignoring what it claimed that wasn't there.

**Why it bites.** A system that produces 10 correct findings and 50 confidently-wrong hallucinations is worse than a system that produces 5 correct findings and no hallucinations, but only the first system "wins" on recall.

**Mitigations.**
- Track precision, not just recall.
- Track hallucination rate specifically.
- Have an explicit category for "claim X is asserted by the agent and is not supported by evidence."
- Track abstention — what did the agent decline to claim?

### G.6 Comparing agentic systems with different tool budgets

**Pitfall.** System A runs with 200 tool calls; System B runs with 20. A produces deeper investigations and looks "smarter," but the comparison is really about budget.

**Mitigations.**
- Fix tool-call budgets across compared systems.
- Report cost-per-finding alongside accuracy.
- Build a Pareto frontier (accuracy vs cost) rather than a single number.

### G.7 Evaluating against a moving target

**Pitfall.** External services (VirusTotal, threat intel) evolve. Re-running the same evaluation a month later produces different numbers, because the external services returned different data.

**Mitigations.**
- Snapshot external service responses at evaluation start; replay against the snapshot.
- Note the evaluation timestamp; treat the result as time-bounded.

### G.8 Tool-output mistaken for ground truth

**Pitfall.** The agent runs `plaso` and reports plaso's output. The evaluator scores the agent against plaso's output, not against an independent ground truth.

**Why it bites.** The agent's accuracy collapses to "did the agent faithfully report what the tool said?" rather than "did the agent investigate correctly?" If plaso has bugs or misclassifies events, the agent inherits those errors.

**Mitigations.**
- Use ground truth independent of the tools the agent uses (case writeups, hand-encoded answer keys).
- Where forced to use tool output as ground truth, acknowledge the limitation.

### G.9 Counting tool calls as "self-correction"

**Pitfall.** The agent calls a tool, gets unexpected output, calls a different tool. This is sometimes counted as "self-correction." It may be — or it may just be the agent flailing.

**Mitigations.**
- Define self-correction operationally: agent explicitly identifies a prior claim as incorrect and revises it, with the revision recorded.
- Distinguish from "exploration" (trying multiple tools without committing to any claim yet).
- Distinguish from "context-rot drift" (later turns contradict earlier turns without anyone noticing).

### G.10 Confusing demo success with system success

**Pitfall.** A live demo works. The system "works." But the demo was rehearsed, on a known case, with the evaluator over its shoulder; the system has not been shown to work in the wild.

**Mitigations.**
- Distinguish demo runs from evaluation runs.
- Evaluation runs are hands-off, on cases not used during development.
- Report evaluation results in the accuracy report; report demos in the video.

### G.11 Underspecified prompts

**Pitfall.** "We asked the agent to investigate the case." But what exactly was the prompt? Subtle prompt wording changes outcomes substantially.

**Mitigations.**
- Publish the exact prompts.
- Test prompt sensitivity (small variants of the prompt; measure variance).
- Treat the prompt as part of the system, not a free parameter.

### G.12 No human-baseline comparison

**Pitfall.** Reporting agent accuracy without a human-analyst comparison. Without that, "92% accuracy" has no reference frame.

**Mitigations.**
- Note where possible the published human-analyst performance on the same case (some training cases have published timing / accuracy numbers).
- Run at least one case through a human analyst as a control.
- Treat human performance as the floor for "obviously valuable" tooling.

### G.13 Optimizing for the metric rather than the goal

**Pitfall.** The evaluation metric becomes the target; the system is tuned to score well on the metric in ways that may not generalize to real cases.

**Mitigations.**
- Hold out test cases not used in development.
- Periodically refresh the evaluation set.
- Track real-world deployment outcomes (when available) and check against benchmark numbers.

---

## Sources

This document draws on:

- **Digital Corpora landing pages and download archives** — https://digitalcorpora.org/, especially the Nitroba and M57 scenario pages.
- **NIST CFReDS archive** — https://cfreds-archive.nist.gov/, including the Data Leakage Case answer PDF, the Hacking Case landing, and the older case pages.
- **NIST CFReDS live site** — https://cfreds.nist.gov/.
- **Ali Hadi case archives on archive.org** — https://archive.org/details/dfir-case1, https://archive.org/details/sysinternals-case, https://archive.org/details/anti-forensics-case-2.
- **DFRWS challenge repositories** — https://github.com/dfrws/dfrws2008-challenge, https://github.com/dfrws/dfrws2011-challenge, and https://dfrws.org/dfrws-forensic-challenge/.
- **DFIR-Metric paper** — *DFIR-Metric: A Benchmark Dataset for Evaluating LLMs in Digital Forensics and Incident Response*, arXiv:2505.19973 (May 2025), at https://arxiv.org/abs/2505.19973.
- **CyberSleuth paper** — *CyberSleuth: Autonomous Blue-Team LLM Agent for Web Attack Forensics*, arXiv:2508.20643 (August 2025), at https://arxiv.org/abs/2508.20643.
- **Digital Forensics in the Age of LLMs** — arXiv:2504.02963 (April 2025), survey paper.
- **Chances and Challenges of MCP in DFIR** — arXiv:2506.00274v1 (June 2025), survey.
- **Multi-Agent Collaboration in Incident Response with LLMs** — arXiv:2412.00652 (December 2024).
- **Is the DFIR Pipeline Ready for Text-Based Threats in the LLM Era?** — arXiv:2407.17870 (July 2024).
- **CiteCheck — Accurate Citation Faithfulness Detection** — arXiv:2502.10881 (February 2025).
- **Verifiable Generation with Subsentence-Level Fine-Grained Citations** — arXiv:2406.06125 (June 2024).
- **NABAOS — Tool Receipts, Not Zero-Knowledge Proofs** — arXiv:2603.10060 (March 2026).
- **RetroLLM — Empowering LLMs to Retrieve Fine-grained Evidence within Generation** — arXiv:2412.11919 (December 2024).
- **Min et al., FActScore** — Min, Krishna, Lyu, et al., "FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation" (EMNLP 2023).
- **Federal Rules of Evidence Rule 707** (adopted via December 2024 FRE amendments) — text via U.S. Courts website.
- **Federal Rules of Evidence Rule 702** — text via U.S. Courts website.
- **Daubert v. Merrell Dow Pharmaceuticals, Inc.**, 509 U.S. 579 (1993) — Supreme Court opinion.
- **NIST SP 800-53 Rev 5** — *Security and Privacy Controls for Information Systems and Organizations*, https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final.
- **NIST SP 800-218** — *Secure Software Development Framework (SSDF) Version 1.1*, https://csrc.nist.gov/publications/detail/sp/800-218/final.
- **NIST SP 800-86** — *Guide to Integrating Forensic Techniques into Incident Response*.
- **NIST SP 800-101r1** — *Guidelines on Mobile Device Forensics*.
- **NSRL** — https://www.nist.gov/itl/ssd/software-quality-group/nsrl.
- **Volatility Foundation** — https://volatilityfoundation.org/ (read-only since May 2025).
- **MITRE ATT&CK** — https://attack.mitre.org/.
- **Magnet Forensics CTF archives** — https://www.magnetforensics.com/.
- **Belkasoft sample-data page** — https://belkasoft.com/get.
- **VxUnderground** — https://vx-underground.org/.
- **MalwareBazaar / Abuse.ch** — https://bazaar.abuse.ch/, https://urlhaus.abuse.ch/, https://threatfox.abuse.ch/.
- **VirusShare** — https://virusshare.com/.
- **Public community writeups** for the NIST Hacking Case at intrinsicode.net and zarat.hatenablog.com.

For internal cross-reference: the wedge commitment that frames this domain knowledge is at `STRATEGY.md`; the project's research provenance (including the original Tier 1-4 dataset triage that informed parts of Section A) is at `research/protocol-sift-2026/refs/datasets.md` and at `research/protocol-sift-2026/.raw/04-signals-and-data.md`.
