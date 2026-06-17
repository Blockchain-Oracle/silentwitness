---
case_id: rocba-gpt-5-mini-001
examiner: root
status: REVIEWED
content_hash: sha256:05fb03237399462f94bee816c6495dd4d13796375f12ab94e3be3feaa22abaac
created_at: '2026-06-17T14:22:30Z'
updated_at: '2026-06-17T14:27:25Z'
silentwitness_version: 1.4.5
model_used: openai-chat:gpt-5-mini
---

# Incident Report — Case rocba-gpt-5-mini-001

## Executive Summary

- **F-001** [HIGH]: The record indicates a remote interactive/remote desktop type logon (LogonType=10) for the MicrosoftAccount srl-helpdesk@outlook.com where the process name is svchost.exe and the source IP is 174.196.200.9; this indicates an incoming RDP/remote interactive session from that IP into the host under that MicrosoftAccount identity.
- **F-002** [HIGH]: The record indicates a remote interactive logon (LogonType=10) for MicrosoftAccount fred.rocba@outlook.com from external IP 52.249.198.56; ProcessName svchost.exe and LogonProcessName User32 suggest an RDP or remote interactive authentication proxied via a system service.
- **F-003** [HIGH]: The LNK indicates the PST file was located under Google Drive path 'G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST\SRL-EMAIL-EXPORT.pst', suggesting the user synced or stored the exported PST in Google Drive (My Drive) accessible to the host.


## Engagement Overview

**Case ID:** rocba-gpt-5-mini-001
**Examiner:** root
**Start date:** _not recorded_
**Scope:** _not recorded_
**Access level:** _To be completed by examiner._


## Methodology

Tools used during this investigation:

- `cli.init`
- `record_observation`
- `record_interpretation`
- `approve_finding`
- `search_evidence`
- `get_record`
- `list_detections`


## Findings

### F-001 — F-001

**Confidence:** HIGH
**Corroboration:** `UNVERIFIED` · system_log
**Affected systems:** _To be completed by examiner._

The record indicates a remote interactive/remote desktop type logon (LogonType=10) for the MicrosoftAccount srl-helpdesk@outlook.com where the process name is svchost.exe and the source IP is 174.196.200.9; this indicates an incoming RDP/remote interactive session from that IP into the host under that MicrosoftAccount identity.

**Supporting evidence:**

- Security.evtx record shows a successful remote logon (EventID=4624) for TargetUserName=srl-helpdesk@outlook.com with LogonType=10 and IpAddress=174.196.200.9.  [verify:F-001/sift-root-20260617-006]

**MITRE ATT&CK:** _To be completed by examiner._
**Recommended actions:** _See Recommendations section._

### F-002 — F-002

**Confidence:** HIGH
**Corroboration:** `UNVERIFIED` · system_log
**Affected systems:** _To be completed by examiner._

The record indicates a remote interactive logon (LogonType=10) for MicrosoftAccount fred.rocba@outlook.com from external IP 52.249.198.56; ProcessName svchost.exe and LogonProcessName User32 suggest an RDP or remote interactive authentication proxied via a system service.

**Supporting evidence:**

- Security.evtx record shows a successful remote logon (EventID=4624) for TargetUserName=fred.rocba@outlook.com with LogonType=10 and IpAddress=52.249.198.56.  [verify:F-002/sift-root-20260617-006]

**MITRE ATT&CK:** _To be completed by examiner._
**Recommended actions:** _See Recommendations section._

### F-003 — F-003

**Confidence:** HIGH
**Corroboration:** `UNVERIFIED` · user_activity
**Affected systems:** _To be completed by examiner._

The LNK indicates the PST file was located under Google Drive path 'G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST\SRL-EMAIL-EXPORT.pst', suggesting the user synced or stored the exported PST in Google Drive (My Drive) accessible to the host.

**Supporting evidence:**

- Recent LNK evidence shows SRL-EMAIL-EXPORT.lnk with target path pointing to G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST\SRL-EMAIL-EXPORT.pst, indicating a PST export was accessed.  [verify:F-003/sift-root-20260617-006]

**MITRE ATT&CK:** _To be completed by examiner._
**Recommended actions:** _See Recommendations section._


## Timeline

| Timestamp | Source | Event | Audit Ref | Finding ID |
|-----------|--------|-------|-----------|------------|
| 2026-06-17T14:24:44.318376+00:00 | sift-root-20260617-006 | Security.evtx record shows a successful remote logon (EventID=4624) for TargetUs… | sift-root-20260617-006 | F-001 |
| 2026-06-17T14:25:23.000610+00:00 | sift-root-20260617-006 | Security.evtx record shows a successful remote logon (EventID=4624) for TargetUs… | sift-root-20260617-006 | F-002 |
| 2026-06-17T14:25:56.187652+00:00 | sift-root-20260617-006 | Recent LNK evidence shows SRL-EMAIL-EXPORT.lnk with target path pointing to G:\M… | sift-root-20260617-006 | F-003 |


## Indicators of Compromise

**Domain**

- `outlook.com` — [sift-root-20260617-006]

**IP**

- `174.196.200.9` — [sift-root-20260617-006]

- `52.249.198.56` — [sift-root-20260617-006]


## MITRE ATT&CK Techniques

_No MITRE ATT&CK techniques derived from cited detections._


## Recommendations

_To be populated by examiner._


## Gaps

(no gaps identified)


## Appendix — Audit

- `audit/agent.jsonl` — `sha256:c5f2e32ec615199f6496069303450b7bce53722c6fce49ab56deb2e3b8b2347b`
- `audit/cli.jsonl` — `sha256:a829dc14c8480cd5ce40a76dd0944295216bd8682582b294711f8c0ca1faf14b`
- `audit/critic.jsonl` — `sha256:83425c5f362a5a3b9e56b5a1d4e51da143b627a4bb4f529c6f2be64e771e9f2e`
- `audit/findings.jsonl` — `sha256:0ca2a44c412d34414133e47fc5d39267bbdd28cae4be15d4c51e626db5c163b2`
- `audit/hypothesis.jsonl` — `sha256:d9969b04371e55dcc47a7e716b03593d592b08b1f6c802fd483d0fc3cbedf80a`
- `audit/index.jsonl` — `sha256:24bcb07a5bbd0dff5074477e2a9948da185308baabfbb31b344c4b7660bdbc5e`
- `audit/sanitizer.jsonl` — `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
