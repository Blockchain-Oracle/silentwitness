# Mr. Evil OpenAI GPT-5.2 resume showcase

This directory is a point-in-time snapshot copied from:

```text
/root/silentwitness-demo/cases/mr-evil-001
```

It preserves the current VPS run artifacts used for the judge/demo showcase.
VPS runs do not update GitHub automatically; the files here were copied from the
VPS case workspace and committed to the repository.

## Snapshot status

- Case: `mr-evil-001`
- Status at capture: `ERROR`
- Model reported by `silentwitness status`: `openai-chat:gpt-5.2`
- Token use at capture: `3M / 6M`
- Findings records: `56`
- Approved finding records: `7` (`F-001` through `F-007`)
- Observation records still staged/unapproved: `49`
- Report frontmatter status: `REVIEWED`

The `ERROR` status is preserved intentionally. The report can still be
`REVIEWED` because examiner-approved findings exist and were exported before the
snapshot.

This is a resumed case snapshot, not a clean model-comparison run. The captured
case status reports `openai-chat:gpt-5.2`, but earlier approved-finding audit
rows still contain `openai-chat:gpt-5-mini` because the case had already been
run and reviewed before the GPT-5.2 resume.

## Files

| File | Meaning |
|---|---|
| `report.md` | Reviewed report generated from approved findings. |
| `findings.json` | Mixed observation records plus approved finding records. |
| `audit/findings.jsonl` | Observation/interpretation tool calls and rejected attempts. |
| `audit/index.jsonl` | Evidence-search and record-fetch tool calls. |
| `audit/hypothesis.jsonl` | Hypothesis lifecycle events. |
| `audit/critic.jsonl` | Live critic verdicts. |
| `audit/agent.jsonl` | Agent step and tool-call telemetry. |
| `verification/mr-evil-001.jsonl` | HMAC approval ledger records. |
| `status.txt` | Exact `silentwitness status mr-evil-001` output at capture. |
| `processes.txt` | Matching process list at capture. |
| `summary.json` | Machine-readable snapshot summary. |

For judge-facing links, start from `docs/DEMO_ARTIFACTS.md` and
`docs/THREE_CLAIM_TRACE.md`.
