---
case_id: case-example-001
examiner: example-sansforensics
status: APPROVED
content_hash: sha256:placeholder
created_at: 2026-06-13T12:00:00Z
updated_at: 2026-06-13T12:00:25Z
silentwitness_version: 0.1.0-example
model_used: example
---

# Incident report — case-example-001 (SYNTHETIC EXAMPLE)

## Executive Summary

This is a synthetic example case demonstrating the SilentWitness audit-trail
shape. Three tool calls (vol_pslist, parse_mft, parse_evtx) produced one
APPROVED finding after a critic CHALLENGE → APPROVED arc and one hypothesis
pivot.

## Findings

### F-example-001 — smss.exe spawned under System — boot baseline (APPROVED)

smss.exe (PID 388) child of System (PID 4) — typical Windows boot chain.
[verify:sift-example-20260613-001]

Process tree matches expected Windows boot chain. Corroborated via
parse_evtx 4624 logon trail.

## Gaps

- Only a single 4-byte synthetic evidence file is registered; a real case
  would carry disk + memory + EVTX corpora across the full attack window.

## Appendix-Audit

| audit_id | tool | backend | elapsed_ms | result_sha256 (first 16 hex) |
|---|---|---|---|---|
| sift-example-20260613-001 | vol_pslist | memory | 4200 | (see audit/memory.jsonl) |
| sift-example-20260613-002 | parse_mft | disk | 1800 | (see audit/disk.jsonl) |
| sift-example-20260613-003 | parse_evtx | log | 950 | (see audit/log.jsonl) |
