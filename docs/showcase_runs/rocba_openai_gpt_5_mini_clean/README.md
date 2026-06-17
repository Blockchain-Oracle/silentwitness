# ROCBA OpenAI GPT-5 mini clean showcase

This directory is a point-in-time snapshot copied from the VPS case workspace:

```text
/root/silentwitness-demo/cases/rocba-gpt-5-mini-001
```

It is a clean model showcase run against the already prepared/indexed ROCBA
dataset. The case ID is separate from the live demo case, and the GitHub bundle
was copied after approval/export so judges can inspect it without rerunning the
investigation.

## Snapshot status

- Case: `rocba-gpt-5-mini-001`
- Dataset: ROCBA / Standard Forensic Case
- Model: `openai-chat:gpt-5-mini`
- Token use at capture: `3M / 6M`
- Investigation status at capture: `ERROR`
- Hypotheses confirmed: `3`
- Approved finding records: `3`
- Draft finding records: `0`
- Report frontmatter status: `REVIEWED`

The `ERROR` status is preserved intentionally. The investigator confirmed three
hypotheses and produced a reviewed report, but the process exited non-zero
after the final agent step. The artifacts here are not edited to hide that
state.

## Files

| File | Meaning |
|---|---|
| `report.md` | Reviewed report generated from approved findings. |
| `findings.json` | Approved finding records captured by the run. |
| `audit/findings.jsonl` | Observation, interpretation, and approval tool calls. |
| `audit/index.jsonl` | Evidence search and record-fetch tool calls. |
| `audit/hypothesis.jsonl` | Hypothesis lifecycle events. |
| `audit/agent.jsonl` | Agent step and tool-call telemetry. |
| `audit/critic.jsonl` | Critic agreement records for approved findings. |
| `verification/rocba-gpt-5-mini-001.jsonl` | HMAC approval ledger records. |
| `approval-results.json` | Programmatic approval results for the DRAFT findings. |
| `status.txt` | Exact `silentwitness status rocba-gpt-5-mini-001` output at capture. |
| `summary.json` | Machine-readable snapshot summary. |
