# Showcase runs

This directory is for demo-facing investigation bundles copied from live local
or VPS case workspaces and committed to GitHub. A run appearing here means it is
ready for judges to inspect as a static artifact; it does not imply the VPS
syncs results into the repository automatically.

## Clean model showcase bundles

- [`rocba_openai_gpt_4_1_clean/`](rocba_openai_gpt_4_1_clean/) - ROCBA clean
  model showcase run using `openai-chat:gpt-4.1`. The snapshot captured
  `4M / 6M` tokens, 5 confirmed hypotheses, and 6 approved findings. Its
  investigation status is preserved as `ERROR` because the process exited
  non-zero after narrative/finalization, even though the reviewed report and
  approval ledger were generated.

## Resume bundle

- [`mr_evil_openai_gpt_5_2_resume/`](mr_evil_openai_gpt_5_2_resume/) - current
  Mr. Evil VPS showcase snapshot. `silentwitness status` captured the case under
  `openai-chat:gpt-5.2` with 7 approved findings and `3M / 6M` tokens used.

The `resume` suffix is intentional: this case was resumed after earlier
OpenAI-mini activity, so it should not be presented as a clean model comparison.
