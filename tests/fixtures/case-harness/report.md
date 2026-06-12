# Case Harness — Test Investigation Report

## Executive Summary

A targeted intrusion was detected involving credential theft via LSASS memory
dumping, lateral movement via obfuscated PowerShell, and C2 beaconing to a
known malicious IP. Persistence was established via a scheduled task. Evidence
of Mimikatz execution is present in prefetch artifacts.

## Findings

### F-001: Credential theft via lsass dump

**Status:** APPROVED

The LSASS process was targeted for credential extraction. Prefetch and MFT
evidence corroborates execution of credential dumping utilities.

### F-002: Obfuscated PowerShell execution

**Status:** DRAFT

A Base64-encoded PowerShell command was executed during the intrusion window.

## Timeline

| Offset | Event |
|--------|-------|
| T+0    | Initial access |
| T+2min | LSASS dump |
| T+5min | C2 beaconing begins |
| T+12min | Scheduled task created |

## Gaps

- No memory image from secondary host is available for lateral movement confirmation.
- Network PCAP covering the full exfiltration window is absent from evidence.
- Registry hives from the SYSTEM account were not imaged prior to remediation.
