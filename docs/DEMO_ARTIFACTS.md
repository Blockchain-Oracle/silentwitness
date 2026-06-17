# Demo artifacts

This page is the pointer to use at the end of the demo. It shows where the
human report, findings JSON, and audit JSONL live after an investigation, and
which committed GitHub artifacts a judge can inspect without rerunning the case.

## After a local or VPS run

From the case workspace:

```bash
export SILENTWITNESS_CASES_DIR=/root/silentwitness-demo
silentwitness export mr-evil-001 --md

cat cases/mr-evil-001/report.md
jq '.[] | select(.status == "APPROVED")' cases/mr-evil-001/findings.json
ls cases/mr-evil-001/audit/*.jsonl
```

The important files are:

| File | What it proves |
|---|---|
| `cases/<case-id>/report.md` | The examiner-facing report. Frontmatter is `REVIEWED` once approved findings exist. |
| `cases/<case-id>/findings.json` | Observations, interpretations, DRAFT/APPROVED finding records, and cited spans. |
| `cases/<case-id>/audit/findings.jsonl` | Every `record_observation` / `record_interpretation` tool call, including rejected attempts. |
| `cases/<case-id>/audit/index.jsonl` | Evidence search and record-fetch tool calls that surfaced cited records. |
| `cases/<case-id>/audit/hypothesis.jsonl` | Hypothesis lifecycle: form, dispatch, confirm, pivot, abandon. |
| `cases/<case-id>/audit/critic.jsonl` | Live critic AGREE/CHALLENGE/REJECT records. |
| `/var/lib/silentwitness/verification/<case-id>.jsonl` | HMAC-signed approval ledger for accepted findings. |

## GitHub artifacts to show judges

- [Synthetic full report](EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/report.md)
- [Synthetic findings JSON](EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/findings.json)
- [Synthetic audit JSONL directory](EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/audit/)
- [Synthetic HMAC approval ledger](EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/ledger.jsonl)
- [ROCBA headline trace findings JSON](execution_logs/rocba_headline_run/findings.json)
- [ROCBA headline trace findings tool log](execution_logs/rocba_headline_run/findings.jsonl)
- [ROCBA headline trace index tool log](execution_logs/rocba_headline_run/index.jsonl)
- [ROCBA headline trace critic log](execution_logs/rocba_headline_run/critic.jsonl)
- [ROCBA headline trace hypothesis log](execution_logs/rocba_headline_run/hypothesis.jsonl)

The synthetic case exists so the whole report plus ledger can be inspected
without a large evidence image. The ROCBA headline trace exists to show the real
case's finding-to-evidence path. When a new GPT 5.2 run is approved for the
submission, replace the ROCBA headline trace files with that run's
`findings.json` and `audit/*.jsonl`, then update
[`THREE_CLAIM_TRACE.md`](THREE_CLAIM_TRACE.md) if the finding IDs or audit IDs
changed.

## Report status wording

`report.md` can contain both approved findings and unreviewed observations.
The report lifecycle is the frontmatter `status`:

```yaml
status: REVIEWED
```

Unapproved material appears under `Unreviewed observations` and is not signed
report material until the examiner runs `silentwitness approve`.
