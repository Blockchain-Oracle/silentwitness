---
case_id: rocba-gpt-5-2-001
examiner: root
status: REVIEWED
content_hash: sha256:6aeb7cd0918bbd811ac2609e9a64f8d4ab102bed59210b19428bda8937552573
created_at: '2026-06-17T14:34:07Z'
updated_at: '2026-06-17T14:40:08Z'
silentwitness_version: 1.4.5
model_used: openai-chat:gpt-5.2
---

# Incident Report — Case rocba-gpt-5-2-001

## Executive Summary

- **F-001** [HIGH]: The indexed Security 4624 activity on 2020-11-15 does not corroborate a successful remote logon during the observed 4625 burst; the only retrieved 4624 record is LogonType=5 (service) with IpAddress='-'.
- **F-002** [MEDIUM]: This indicates Outlook accessed (and likely loaded/indexed) a mailbox export file (SRL-EMAIL-EXPORT.pst) stored under a Google Drive “My Drive” path, which is consistent with staging email data into a cloud-synced location for transfer/off-host access.


## Engagement Overview

**Case ID:** rocba-gpt-5-2-001
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
- `list_detections`
- `search_evidence`
- `timeline`
- `get_record`


## Findings

### F-001 — F-001

**Confidence:** HIGH
**Corroboration:** `UNVERIFIED` · system_log
**Affected systems:** _To be completed by examiner._

The indexed Security 4624 activity on 2020-11-15 does not corroborate a successful remote logon during the observed 4625 burst; the only retrieved 4624 record is LogonType=5 (service) with IpAddress='-'. Additional searching for LogonType=3 (network) and LogonType=10 (RDP) on that date returned no hits in the evidence index, suggesting remote interactive access via RDP was not successfully established (or relevant event sources were not ingested/available).

**Supporting evidence:**

- Around the 2020-11-15 failed-logon activity, at least one Security 4624 successful logon event was present but it was a service logon, not a remote logon: TargetUserName=SYSTEM and LogonType=5 with IpAddress=-.  [verify:F-001/sift-root-20260617-006]

**MITRE ATT&CK:** _To be completed by examiner._
**Recommended actions:** _See Recommendations section._

### F-002 — F-002

**Confidence:** MEDIUM
**Corroboration:** `CONFIRMED` · system_log + user_activity
**Affected systems:** _To be completed by examiner._

This indicates Outlook accessed (and likely loaded/indexed) a mailbox export file (SRL-EMAIL-EXPORT.pst) stored under a Google Drive “My Drive” path, which is consistent with staging email data into a cloud-synced location for transfer/off-host access. This supports Q2 (what data) and Q3 (where transferred), but does not by itself prove the PST was created or uploaded during the session.

**Supporting evidence:**

- LNK artifacts for user fredr reference a PST email export located in Google Drive (“My Drive”).  [verify:F-002/sift-root-20260617-006]

**MITRE ATT&CK:** _To be completed by examiner._
**Recommended actions:** _See Recommendations section._


## Timeline

| Timestamp | Source | Event | Audit Ref | Finding ID |
|-----------|--------|-------|-----------|------------|
| 2026-06-17T14:35:37.839893+00:00 | sift-root-20260617-006 | Around the 2020-11-15 failed-logon activity, at least one Security 4624 successf… | sift-root-20260617-006 | F-001 |
| 2026-06-17T14:36:05.215831+00:00 | sift-root-20260617-006 | LNK artifacts for user fredr reference a PST email export located in Google Driv… | sift-root-20260617-006 | F-002 |


## Indicators of Compromise

_No IOC candidates extracted from approved findings._


## MITRE ATT&CK Techniques

_No MITRE ATT&CK techniques derived from cited detections._


## Recommendations

_To be populated by examiner._


## Gaps

(no gaps identified)


## Appendix — Audit

- `audit/agent.jsonl` — `sha256:390ac7ed0bee5d13bc7afb9963fc104e92045329301e8e16350a1f88b6be4558`
- `audit/cli.jsonl` — `sha256:e2015f47d3f5601f79fccd871d0fb5247a3f9b10899e0b063ac9e7795e2b31a4`
- `audit/critic.jsonl` — `sha256:008ebee36836753fb9009cc6148cb9f845c3c2824dff16e4c26786a4e5d838f7`
- `audit/findings.jsonl` — `sha256:b1a69be9f0ab14051580f923536a9f3b9ab5b1d931ff22349af86656c9b278f6`
- `audit/hypothesis.jsonl` — `sha256:14019f1be54c2be059018ecf780115d83e9b5b758049ea367101241f9b9a9bda`
- `audit/index.jsonl` — `sha256:f30de2e16ea4a69364942b4d7b1ae66bd20bbb86f9f1ea79dcdd35b61a74edfe`
- `audit/sanitizer.jsonl` — `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
