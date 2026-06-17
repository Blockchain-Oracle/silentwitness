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

The current VPS demo bundle is under [`showcase_runs/`](showcase_runs/). These
files are copied from the VPS case directory, committed, and pushed; they do not
sync to GitHub automatically just because a VPS investigation finishes.

- [Mr. Evil GPT-5.2 resume report](showcase_runs/mr_evil_openai_gpt_5_2_resume/report.md)
- [Mr. Evil GPT-5.2 resume findings JSON](showcase_runs/mr_evil_openai_gpt_5_2_resume/findings.json)
- [Mr. Evil GPT-5.2 resume audit JSONL directory](showcase_runs/mr_evil_openai_gpt_5_2_resume/audit/)
- [Mr. Evil GPT-5.2 resume approval ledger](showcase_runs/mr_evil_openai_gpt_5_2_resume/verification/mr-evil-001.jsonl)
- [Mr. Evil GPT-5.2 resume status snapshot](showcase_runs/mr_evil_openai_gpt_5_2_resume/status.txt)
- [Mr. Evil GPT-5.2 resume snapshot summary](showcase_runs/mr_evil_openai_gpt_5_2_resume/summary.json)
- [ROCBA GPT-4.1 clean report](showcase_runs/rocba_openai_gpt_4_1_clean/report.md)
- [ROCBA GPT-4.1 clean findings JSON](showcase_runs/rocba_openai_gpt_4_1_clean/findings.json)
- [ROCBA GPT-4.1 clean audit JSONL directory](showcase_runs/rocba_openai_gpt_4_1_clean/audit/)
- [ROCBA GPT-4.1 clean approval ledger](showcase_runs/rocba_openai_gpt_4_1_clean/verification/rocba-gpt-4-1-001.jsonl)
- [ROCBA GPT-4.1 clean status snapshot](showcase_runs/rocba_openai_gpt_4_1_clean/status.txt)
- [ROCBA GPT-5 mini clean report](showcase_runs/rocba_openai_gpt_5_mini_clean/report.md)
- [ROCBA GPT-5 mini clean findings JSON](showcase_runs/rocba_openai_gpt_5_mini_clean/findings.json)
- [ROCBA GPT-5 mini clean audit JSONL directory](showcase_runs/rocba_openai_gpt_5_mini_clean/audit/)
- [ROCBA GPT-5 mini clean approval ledger](showcase_runs/rocba_openai_gpt_5_mini_clean/verification/rocba-gpt-5-mini-001.jsonl)
- [ROCBA GPT-5 mini clean status snapshot](showcase_runs/rocba_openai_gpt_5_mini_clean/status.txt)
- [ROCBA GPT-5.2 clean report](showcase_runs/rocba_openai_gpt_5_2_clean/report.md)
- [ROCBA GPT-5.2 clean findings JSON](showcase_runs/rocba_openai_gpt_5_2_clean/findings.json)
- [ROCBA GPT-5.2 clean audit JSONL directory](showcase_runs/rocba_openai_gpt_5_2_clean/audit/)
- [ROCBA GPT-5.2 clean approval ledger](showcase_runs/rocba_openai_gpt_5_2_clean/verification/rocba-gpt-5-2-001.jsonl)
- [ROCBA GPT-5.2 clean status snapshot](showcase_runs/rocba_openai_gpt_5_2_clean/status.txt)
- [ROCBA GPT-5.4 mini clean report](showcase_runs/rocba_openai_gpt_5_4_mini_clean/report.md)
- [ROCBA GPT-5.4 mini clean findings JSON](showcase_runs/rocba_openai_gpt_5_4_mini_clean/findings.json)
- [ROCBA GPT-5.4 mini clean audit JSONL directory](showcase_runs/rocba_openai_gpt_5_4_mini_clean/audit/)
- [ROCBA GPT-5.4 mini clean approval ledger](showcase_runs/rocba_openai_gpt_5_4_mini_clean/verification/rocba-gpt-5-4-mini-001.jsonl)
- [ROCBA GPT-5.4 mini clean status snapshot](showcase_runs/rocba_openai_gpt_5_4_mini_clean/status.txt)
- [Synthetic full report](EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/report.md)
- [Synthetic findings JSON](EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/findings.json)
- [Synthetic audit JSONL directory](EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/audit/)
- [Synthetic HMAC approval ledger](EXAMPLE_EXECUTION_LOGS/case-example-001_EXAMPLE/ledger.jsonl)

The Mr. Evil bundle is a point-in-time VPS snapshot. Its `status.txt` preserves
the run state at capture, including `openai-chat:gpt-5.2`, `ERROR`, `3M / 6M`
tokens, and 7 approved findings. It is labeled as a resume showcase because the
case was resumed after earlier OpenAI mini runs; some audit rows therefore still
record `openai-chat:gpt-5-mini`. Treat it as the current demo case snapshot, not
as a clean model-comparison benchmark.

The synthetic case exists so the whole report plus ledger can be inspected
without a large evidence image. When a newer run is chosen for final submission,
copy that run into a new folder under `showcase_runs/`, update this page, and
update [`THREE_CLAIM_TRACE.md`](THREE_CLAIM_TRACE.md) if the finding IDs or
audit IDs changed.

## Report status wording

`report.md` can contain both approved findings and unreviewed observations.
The report lifecycle is the frontmatter `status`:

```yaml
status: REVIEWED
```

Unapproved material appears under `Unreviewed observations` and is not signed
report material until the examiner runs `silentwitness approve`.
