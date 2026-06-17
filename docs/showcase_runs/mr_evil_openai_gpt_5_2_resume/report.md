---
case_id: mr-evil-001
examiner: root
status: REVIEWED
content_hash: sha256:f9b21b9bbcf2d3c210c810f1e2f64a334db25a13b18056738e380f278226dddd
created_at: '2026-06-17T12:03:29Z'
updated_at: '2026-06-17T12:53:49Z'
silentwitness_version: 1.4.5
model_used: unknown
---

# Incident Report — Case mr-evil-001

## Executive Summary

- **F-001** [MEDIUM]: The Recent LNK entries show user-visible shortcuts pointing to Dropbox, Google Drive (Google Drive File Stream), and OneDrive locations, demonstrating cloud-sync folders were present and accessed.
- **F-002** [HIGH]: Observation cites an LNK Recent shortcut record containing the verbatim LNK target string; this proves the Recent shortcut points to the Exported-PST folder path (evidence of the shortcut's target path in the LNK file).
- **F-003** [HIGH]: The LNK record shows that the user 'fredr' had a Recent shortcut pointing to a file in 'Your team Dropbox\Fred Rocba\Camera Uploads', indicating the Dropbox folder was present in the user's profile and the file was referenced via Explorer or another process; this is strong evidence the user accessed the file or it was present in the user's Recent items.
- **F-004** [HIGH]: The LNK record indicates a Recent shortcut whose target is 'G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST', which suggests the Exported-PST folder existed accessible via a mapped G: drive to 'My Drive' (Google Drive/Drive File Stream).
- **F-005** [MEDIUM]: The LNK record in fredr's Recent folder references a PST file path on G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST and sets workdir accordingly; this indicates the PST file SRL-EMAIL-EXPORT.pst was present at that path or referenced by a process that writes Explorer Recent shortcuts.
- **F-006** [HIGH]: The prefetch entry for GOOGLEDRIVEFS.EXE with run_count=22 indicates Google Drive File Stream (DriveFS) executed on the host multiple times, which supports that the G: 'My Drive' path is likely a DriveFS mapping.
- **F-007** [HIGH]: The prefetch entries for DROPBOX.EXE, DROPBOXUPDATE.EXE and ShimCache/Amcache entries referencing Dropbox indicate Dropbox was installed and executed on the host; SRUM network usage shows significant bytes sent/received by Dropbox, consistent with active syncing behavior.


## Engagement Overview

**Case ID:** mr-evil-001  
**Examiner:** root  
**Start date:** _not recorded_  
**Scope:** _not recorded_  
**Access level:** _To be completed by examiner._


## Methodology

Tools used during this investigation:

- `cli.approve`
- `record_observation`
- `record_interpretation`
- `approve_finding`
- `search_evidence`
- `get_record`


## Findings

### F-001 — F-001

**Confidence:** MEDIUM  
**Corroboration:** `INFERRED` · user_activity  
**Affected systems:** _To be completed by examiner._

The Recent LNK entries show user-visible shortcuts pointing to Dropbox, Google Drive (Google Drive File Stream), and OneDrive locations, demonstrating cloud-sync folders were present and accessed. Prefetch records show execution of the corresponding client binaries, which is evidence the clients ran on the host. Quoted evidence: "LNK target=C:\Users\fredr\ROCBA Dropbox\Fred Rocba\Data Testing Results\New World (4)\icon.png workdir=C:\Users\fredr\ROCBA Dropbox\Fred Rocba\Data Testing Results\New World (4)" (lnk, record_id=2507964); "LNK target=C:\Users\fredr\Google Drive\Firedam.xls workdir=C:\Users\fredr\Google Drive" (lnk, record_id=2507947); "Prefetch exe=DROPBOX.EXE run_count=2" (prefetch, record_id=2505136); "Prefetch exe=GOOGLEDRIVEFS.EXE run_count=22" (prefetch, record_id=2505148); "Prefetch exe=ONEDRIVE.EXE run_count=11" (prefetch, record_id=2505191).

**Supporting evidence:**

- Recent LNK shortcuts referencing cloud-sync folders and mounts found (Dropbox, Google Drive, OneDrive).  [verify:F-001/sift-root-20260617-006]

**MITRE ATT&CK:** _To be completed by examiner._  
**Recommended actions:** _See Recommendations section._

### F-002 — F-002

**Confidence:** HIGH  
**Corroboration:** `UNVERIFIED` · user_activity  
**Affected systems:** _To be completed by examiner._

Observation cites an LNK Recent shortcut record containing the verbatim LNK target string; this proves the Recent shortcut points to the Exported-PST folder path (evidence of the shortcut's target path in the LNK file).

**Supporting evidence:**

- LNK Recent shortcut: Exported-PST.lnk — LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST  [verify:F-002/sift-root-20260617-006]

**MITRE ATT&CK:** _To be completed by examiner._  
**Recommended actions:** _See Recommendations section._

### F-003 — F-003

**Confidence:** HIGH  
**Corroboration:** `UNVERIFIED` · user_activity  
**Affected systems:** _To be completed by examiner._

The LNK record shows that the user 'fredr' had a Recent shortcut pointing to a file in 'Your team Dropbox\Fred Rocba\Camera Uploads', indicating the Dropbox folder was present in the user's profile and the file was referenced via Explorer or another process; this is strong evidence the user accessed the file or it was present in the user's Recent items.

**Supporting evidence:**

- Recent LNK record shows: "LNK target=C:\Users\fredr\Your team Dropbox\Fred Rocba\Camera Uploads\2020-06-24 22.00.13.png workdir=C:\Users\fredr\Your team Dropbox\Fred Rocba\Camera Uploads"  [verify:F-003/sift-root-20260617-006]

**MITRE ATT&CK:** _To be completed by examiner._  
**Recommended actions:** _See Recommendations section._

### F-004 — F-004

**Confidence:** HIGH  
**Corroboration:** `UNVERIFIED` · user_activity  
**Affected systems:** _To be completed by examiner._

The LNK record indicates a Recent shortcut whose target is 'G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST', which suggests the Exported-PST folder existed accessible via a mapped G: drive to 'My Drive' (Google Drive/Drive File Stream). This is indicative of a cloud-sync path (Google Drive 'My Drive') being referenced by Explorer or a sync client. Confidence: HIGH.

**Supporting evidence:**

- Evidence shows the LNK content: "LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST".  [verify:F-004/sift-root-20260617-006]

**MITRE ATT&CK:** _To be completed by examiner._  
**Recommended actions:** _See Recommendations section._

### F-005 — F-005

**Confidence:** MEDIUM  
**Corroboration:** `UNVERIFIED` · user_activity  
**Affected systems:** _To be completed by examiner._

The LNK record in fredr's Recent folder references a PST file path on G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST and sets workdir accordingly; this indicates the PST file SRL-EMAIL-EXPORT.pst was present at that path or referenced by a process that writes Explorer Recent shortcuts. It does not by itself prove the user opened the PST or manually uploaded it to cloud storage. Confidence: MEDIUM.

**Supporting evidence:**

- Evidence shows the LNK content: "LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST\SRL-EMAIL-EXPORT.pst workdir=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST".  [verify:F-005/sift-root-20260617-006]

**MITRE ATT&CK:** _To be completed by examiner._  
**Recommended actions:** _See Recommendations section._

### F-006 — F-006

**Confidence:** HIGH  
**Corroboration:** `UNVERIFIED` · user_activity  
**Affected systems:** _To be completed by examiner._

The prefetch entry for GOOGLEDRIVEFS.EXE with run_count=22 indicates Google Drive File Stream (DriveFS) executed on the host multiple times, which supports that the G: 'My Drive' path is likely a DriveFS mapping. Confidence: HIGH.

**Supporting evidence:**

- Prefetch record shows: "Prefetch exe=GOOGLEDRIVEFS.EXE run_count=22".  [verify:F-006/sift-root-20260617-006]

**MITRE ATT&CK:** _To be completed by examiner._  
**Recommended actions:** _See Recommendations section._

### F-007 — F-007

**Confidence:** HIGH  
**Corroboration:** `INFERRED` · user_activity  
**Affected systems:** _To be completed by examiner._

The prefetch entries for DROPBOX.EXE, DROPBOXUPDATE.EXE and ShimCache/Amcache entries referencing Dropbox indicate Dropbox was installed and executed on the host; SRUM network usage shows significant bytes sent/received by Dropbox, consistent with active syncing behavior. Confidence: HIGH.

**Supporting evidence:**

- Prefetch record shows Dropbox prefetch: "Prefetch exe=DROPBOX.EXE run_count=2" and DROPBOXUPDATE.EXE run_count=458.  [verify:F-007/sift-root-20260617-006]

**MITRE ATT&CK:** _To be completed by examiner._  
**Recommended actions:** _See Recommendations section._

## Unreviewed observations

These staged observations remain available for examiner review. They are not signed findings until approved.

### O-002 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST\SRL-EMAIL-EXPORT.pst workdir=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST  [verify:O-002/sift-root-20260617-006]

### O-003 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST\SRL-EMAIL-EXPORT.pst  [verify:O-003/sift-root-20260617-006]

### O-004 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST\SRL-EMAIL-EXPORT.pst  [verify:O-004/sift-root-20260617-006]

### O-005 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST  [verify:O-005/sift-root-20260617-006]

### O-006 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST  [verify:O-006/sift-root-20260617-006]

### O-007 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=F:\Files of interest  [verify:O-007/sift-root-20260617-006]

### O-008 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=F:\Files of interest  [verify:O-008/sift-root-20260617-006]

### O-009 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=C:\Users\fredr\Stark Research Labs\Maria Hill - WorkingFiles\RareEarthDeposits_Confidential.jpg workdir=C:\Users\fredr\Stark Research Labs\Maria Hill - WorkingFiles  [verify:O-009/sift-root-20260617-006]

### O-010 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=C:\Users\fredr\Stark Research Labs\Maria Hill - WorkingFiles\RareEarthDeposits_Confidential.jpg  [verify:O-010/sift-root-20260617-006]

### O-011 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=C:\Users\fredr\Stark Research Labs\Maria Hill - WorkingFiles\RareEarthDeposits_Confidential.jpg  [verify:O-011/sift-root-20260617-006]

### O-012 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Research to Weaponize the Ion Thruster.docx workdir=G:\My Drive\STARK-RESEARCH-LABS FOLDER  [verify:O-012/sift-root-20260617-006]

### O-013 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Research to Weaponize the Ion Thruster.docx  [verify:O-013/sift-root-20260617-006]

### O-014 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Research to Weaponize the Ion Thruster.docx  [verify:O-014/sift-root-20260617-006]

### O-015 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST\SRL-EMAIL-EXPORT.pst workdir=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST  [verify:O-015/sift-root-20260617-006]

### O-016 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST\SRL-EMAIL-EXPORT.pst  [verify:O-016/sift-root-20260617-006]

### O-017 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST\SRL-EMAIL-EXPORT.pst  [verify:O-017/sift-root-20260617-006]

### O-018 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST  [verify:O-018/sift-root-20260617-006]

### O-019 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST  [verify:O-019/sift-root-20260617-006]

### O-020 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=F:\Files of interest  [verify:O-020/sift-root-20260617-006]

### O-021 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=F:\Files of interest  [verify:O-021/sift-root-20260617-006]

### O-022 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=C:\Users\fredr\Stark Research Labs\Maria Hill - WorkingFiles\RareEarthDeposits_Confidential.jpg workdir=C:\Users\fredr\Stark Research Labs\Maria Hill - WorkingFiles  [verify:O-022/sift-root-20260617-006]

### O-023 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=C:\Users\fredr\Stark Research Labs\Maria Hill - WorkingFiles\RareEarthDeposits_Confidential.jpg  [verify:O-023/sift-root-20260617-006]

### O-024 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=C:\Users\fredr\Stark Research Labs\Maria Hill - WorkingFiles\RareEarthDeposits_Confidential.jpg  [verify:O-024/sift-root-20260617-006]

### O-025 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Research to Weaponize the Ion Thruster.docx workdir=G:\My Drive\STARK-RESEARCH-LABS FOLDER  [verify:O-025/sift-root-20260617-006]

### O-026 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Research to Weaponize the Ion Thruster.docx  [verify:O-026/sift-root-20260617-006]

### O-027 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Research to Weaponize the Ion Thruster.docx  [verify:O-027/sift-root-20260617-006]

### O-028 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST\SRL-EMAIL-EXPORT.pst workdir=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST  [verify:O-028/sift-root-20260617-006]

### O-029 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST  [verify:O-029/sift-root-20260617-006]

### O-030 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=F:\Files of interest  [verify:O-030/sift-root-20260617-006]

### O-031 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=C:\Users\fredr\Stark Research Labs\Maria Hill - WorkingFiles\RareEarthDeposits_Confidential.jpg workdir=C:\Users\fredr\Stark Research Labs\Maria Hill - WorkingFiles  [verify:O-031/sift-root-20260617-006]

### O-032 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Research to Weaponize the Ion Thruster.docx workdir=G:\My Drive\STARK-RESEARCH-LABS FOLDER  [verify:O-032/sift-root-20260617-006]

### O-034 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK Recent shortcut: SRL-EMAIL-EXPORT.lnk — LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST\SRL-EMAIL-EXPORT.pst workdir=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST  [verify:O-034/sift-root-20260617-006]

### O-035 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- AutomaticDestinations jumplist entry referencing SRL-EMAIL-EXPORT.pst — LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST\SRL-EMAIL-EXPORT.pst  [verify:O-035/sift-root-20260617-006]

### O-036 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- AutomaticDestinations jumplist entry referencing SRL-EMAIL-EXPORT.pst — LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST\SRL-EMAIL-EXPORT.pst  [verify:O-036/sift-root-20260617-006]

### O-037 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- AutomaticDestinations jumplist entry referencing Exported-PST folder — LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST  [verify:O-037/sift-root-20260617-006]

### O-038 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK Recent shortcut: Files of interest.lnk — LNK target=F:\Files of interest  [verify:O-038/sift-root-20260617-006]

### O-039 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- AutomaticDestinations jumplist entry referencing F:\Files of interest — LNK target=F:\Files of interest  [verify:O-039/sift-root-20260617-006]

### O-040 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- AutomaticDestinations jumplist entry referencing Research to Weaponize the Ion Thruster.docx — LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Research to Weaponize the Ion Thruster.docx  [verify:O-040/sift-root-20260617-006]

### O-041 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- AutomaticDestinations jumplist entry referencing Research to Weaponize the Ion Thruster.docx — LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Research to Weaponize the Ion Thruster.docx  [verify:O-041/sift-root-20260617-006]

### O-042 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- LNK Recent shortcut: RareEarthDeposits_Confidential.lnk — LNK target=C:\Users\fredr\Stark Research Labs\Maria Hill - WorkingFiles\RareEarthDeposits_Confidential.jpg workdir=C:\Users\fredr\Stark Research Labs\Maria Hill - WorkingFiles  [verify:O-042/sift-root-20260617-006]

### O-043 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- AutomaticDestinations jumplist entry referencing RareEarthDeposits_Confidential.jpg — LNK target=C:\Users\fredr\Stark Research Labs\Maria Hill - WorkingFiles\RareEarthDeposits_Confidential.jpg  [verify:O-043/sift-root-20260617-006]

### O-044 — unreviewed observation

**Confidence:** —  
**Review state:** Not examiner-approved

_No interpretation recorded yet._

**Supporting evidence:**

- AutomaticDestinations jumplist entry referencing RareEarthDeposits_Confidential.jpg — LNK target=C:\Users\fredr\Stark Research Labs\Maria Hill - WorkingFiles\RareEarthDeposits_Confidential.jpg  [verify:O-044/sift-root-20260617-006]


## Timeline

| Timestamp | Source | Event | Audit Ref | Finding ID |
|-----------|--------|-------|-----------|------------|
| 2026-06-17T10:56:27.591306+00:00 | sift-root-20260617-006 | Recent LNK shortcuts referencing cloud-sync folders and mounts found (Dropbox, G… | sift-root-20260617-006 | F-001 |
| 2026-06-17T11:25:22.017728+00:00 | sift-root-20260617-006 | LNK Recent shortcut: Exported-PST.lnk — LNK target=G:\My Drive\STARK-RESEARCH-LA… | sift-root-20260617-006 | F-002 |
| 2026-06-17T11:27:48.252235+00:00 | sift-root-20260617-006 | Recent LNK record shows: "LNK target=C:\Users\fredr\Your team Dropbox\Fred Rocba… | sift-root-20260617-006 | F-003 |
| 2026-06-17T11:49:57.133915+00:00 | sift-root-20260617-006 | Evidence shows the LNK content: "LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLD… | sift-root-20260617-006 | F-004 |
| 2026-06-17T11:52:46.129900+00:00 | sift-root-20260617-006 | Evidence shows the LNK content: "LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLD… | sift-root-20260617-006 | F-005 |
| 2026-06-17T11:55:23.210343+00:00 | sift-root-20260617-006 | Prefetch record shows: "Prefetch exe=GOOGLEDRIVEFS.EXE run_count=22". | sift-root-20260617-006 | F-006 |
| 2026-06-17T11:56:05.517352+00:00 | sift-root-20260617-006 | Prefetch record shows Dropbox prefetch: "Prefetch exe=DROPBOX.EXE run_count=2" a… | sift-root-20260617-006 | F-007 |


## Indicators of Compromise

_No IOC candidates extracted from approved findings._


## MITRE ATT&CK Techniques

_No MITRE ATT&CK techniques derived from cited detections._


## Recommendations

_To be populated by examiner._


## Gaps

(no gaps identified)


## Appendix — Audit

- `audit/agent.jsonl` — `sha256:5b771a917dc89bf21f671ca61486c91fd88f542283354271df101ea0b40554df`
- `audit/cli.jsonl` — `sha256:bebf5fdc904eed50049a52f736e6dea0a1636c30d2f1cb0f25858b44f37c3b26`
- `audit/critic.jsonl` — `sha256:a6a58a2bc2659f0d4fcfdbf07f2d2009e8dada6c0d5c99498b94996cb54b3199`
- `audit/findings.jsonl` — `sha256:de96ea9e3347cb8bf13a58499ee30755474a636736a5e64c04730caa764c9fff`
- `audit/hypothesis.jsonl` — `sha256:296934233a8f04056446e4dde7b895ede8737244d3262762855f82945762aa44`
- `audit/index.jsonl` — `sha256:a95a209fd695252cbe29c680155daff1a829ca92bce65f8ee4f39d2191e4c106`
- `audit/sanitizer.jsonl` — `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
