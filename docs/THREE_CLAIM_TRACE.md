# Three-Claim Trace — finding → tool execution → evidence

> The rules guarantee a judge "must be able to trace any finding back to the specific tool
> execution that produced it." This walks three findings from the headline 100% run end to end,
> using only the committed logs in [`execution_logs/rocba_headline_run/`](execution_logs/rocba_headline_run/).

Every claim traces through the same chain:

```
finding (findings.json, observation O-NNN)
  └─ cites record_id R + verbatim span_text  ← citation gate enforced span ⊆ record
       └─ R was surfaced to the agent by a query tool call  (index.jsonl: audit_id + query + hits)
            └─ R was produced by the offline ingest          (record.audit_id = sift-phase9-20260615-002)
                 └─ from a source artifact on the read-only image (artifact_path + sha256)
```

`index.jsonl` = the agent's tool executions (timestamped, with `audit_id`); `findings.json` =
the recorded observations; the ingest `audit_id` ties each index row to the extraction that
created it.

---

## Claim 1 — Q4 (how): privileged-account brute force

- **Finding:** observation **O-001** — failed-logon brute force against admin/backup accounts.
- **Cited record:** `record_id 2514145`, span `"SIGMA DETECTION level=medium rule=Failed Logon
  Attempt … event_id=4625 …"`.
- **Tool execution that produced it:** `list_detections` (audit **`sift-analyst-20260615-102`**)
  returned the staged Sigma alerts (total **542,704** detections), and `search_evidence`
  (audit **`sift-analyst-20260615-014`**, query `4625 OR "EventID=4625"`, 50 hits) pulled the
  specific failed-logon records.
- **Self-correction touchpoint:** the live critic returned **AGREE** on O-001
  (`critic.jsonl`), confirming the cited 4625 records support the claim.

## Claim 2 — Q2 (what was taken): the stolen SRL R&D projects

- **Finding:** observation **O-003** — Stark Research Labs project files were accessed/collected.
- **Cited record:** `record_id 2514417`, span
  `"LNK target=C:\Users\fredr\Stark Research Labs\SRL-Projects - Airwolf"`
  (siblings cite `SRL-Projects - Gunstar`, `Blue Thunder`, and an `F:\Key Data` collection folder).
- **Tool execution that produced it:** `search_evidence` (audit **`sift-analyst-20260615-209`**,
  query `"SRL-Projects"`, 20 hits) surfaced the Recent-folder LNK rows — produced by the **LNK
  feeder** during ingest.
- **Self-correction touchpoint:** critic **AGREE** on O-003 — the LNK targets directly name the
  SRL project folders.

## Claim 3 — Q3 (where it went): exfiltration to Google Drive + PST email export

- **Finding:** observation **O-004** — SRL data staged to cloud sync / exported as PST.
- **Cited record:** `record_id 2514416`, span
  `"LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER\Exported-PST\SRL-EMAIL-EXPORT…"`.
- **Tool executions that produced it:** `search_evidence` (audit **`sift-analyst-20260615-117`**,
  query `OneDrive OR Dropbox OR GoogleDriveFS OR rclone OR ftp`, 20 hits) found the cloud-sync
  paths; a follow-up `search_evidence` (audit **`sift-analyst-20260615-211`**, query
  `"LNK target=G:\My Drive\STARK-RESEARCH-LABS FOLDER"`) confirmed the `G:\My Drive` (Google
  Drive) staging location.
- **Self-correction touchpoint:** critic **CHALLENGE** on O-004 — it pushed back on an
  over-broad exfil claim; the investigator revised it (see O-007: *"This revised interpretation
  follows the critic guidance"*). This is a genuine challenge → revise loop.

---

## How to reproduce the trace yourself

```bash
# the cited record's verbatim text and source artifact:
grep -o 'record_id": 2514417[^}]*' docs/execution_logs/rocba_headline_run/findings.json
# the tool execution that surfaced it (audit_id + query + timestamp):
grep 'sift-analyst-20260615-209' docs/execution_logs/rocba_headline_run/index.jsonl
# the critic verdict on the finding:
grep 'O-003' docs/execution_logs/rocba_headline_run/critic.jsonl
```
