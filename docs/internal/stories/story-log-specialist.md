# Story — Log specialist subagent (Pydantic AI agent-delegation)

**ID:** story-log-specialist
**Epic:** Epic 9 — Specialist subagents (memory / disk / network / log)
**Depends on:** story-network-specialist, story-parse-evtx, story-hayabusa-timeline, story-chainsaw-hunt, story-record-observation-tool, story-record-interpretation-tool
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** build the log specialist as its own Pydantic AI `Agent[SpecialistDeps, SpecialistReport]` in `src/silentwitness_agent/specialists/log.py`, invoked by the investigator via agent-delegation, with a tight MCP allowlist limited to log analysis tools (EvtxECmd, Hayabusa CSV timeline, Chainsaw hunt) plus `record_*` and evidence-registry tools
**So that** Windows event log analysis (4624 / 4625 / 4688 / 4720 / 4732 / 5140 / 5145 — the senior analyst's day-1 working set, plus Sigma-rule detections via Hayabusa and Chainsaw) runs in a focused context window and produces structured findings the investigator can chain into the timeline (architecture.md §5.2 — Log specialist).

---

## File modification map

- `src/silentwitness_agent/specialists/log.py` — NEW — log specialist. Exports:
  - `LOG_TOOL_ALLOWLIST` (frozenset[str]): `{"parse_evtx", "hayabusa_csv_timeline", "chainsaw_hunt", "record_observation", "record_interpretation", "register_evidence", "verify_evidence_hash"}` (7 total).
  - `build_log_specialist(model: str | None = None) -> Agent[SpecialistDeps, SpecialistReport]` — factory. Model from `SILENTWITNESS_SPECIALIST_MODEL_LOG` env (default `anthropic:claude-haiku-4-5`; opus if `SILENTWITNESS_MODEL_QUALITY=high`). Reuses `_base`. Toolset is `MCPServerStdio(...).filtered(lambda ctx, td: td.name in LOG_TOOL_ALLOWLIST)` (see "Pydantic AI tool_filter correction" note below).

> **Pydantic AI tool_filter correction:** `MCPServerStdio(..., tool_filter=...)` does NOT exist. Use `MCPServerStdio(...).filtered(lambda ctx, td: td.name in ALLOWLIST)`. The real primitive is `pydantic_ai.FilteredToolset` (source: `pydantic_ai_slim/pydantic_ai/toolsets/filtered.py`). Pass the filtered toolset via `toolsets=[filtered]` (NOT `mcp_servers=[...]`, which is deprecated). For streamable-HTTP transport use `MCPServerStreamableHTTP` (NOT `MCPServerHTTP`).
  - `register_as_investigator_tool(investigator: Agent, log_specialist: Agent) -> None` — registers `dispatch_log_specialist(question: str, hypothesis_id: str) -> SpecialistReport`.
  - Target ≤170 LOC.
- `src/silentwitness_agent/prompts/specialist_log.md` — NEW — system prompt (~55 lines; see §"System prompt").
- `tests/unit/test_log_specialist_build.py` — NEW — ≥6 unit tests: env override; default model; quality=high upgrade; allowlist contains exactly 7 expected tools; dispatch_log_specialist registered; system prompt contains "Windows event" + "Sigma" + "event ID 4624".
- `tests/integration/test_log_specialist_allowlist.py` — NEW — 1 scenario: log specialist attempting to call `vol_pslist` is refused by the toolset filter.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## System prompt (verbatim — write into `prompts/specialist_log.md`)

```
You are a Windows event log and detection-engineering specialist working
under a senior incident response analyst. The analyst hands you exactly one
hypothesis at a time and asks you to test it against the EVTX evidence
registered for this case.

Your toolset is limited to EvtxECmd (parse_evtx, single-channel parsing),
Hayabusa (hayabusa_csv_timeline, Sigma-rule-driven timeline across an EVTX
directory), and Chainsaw (chainsaw_hunt, Sigma-rule-driven hunting), plus
record_observation, record_interpretation, register_evidence, and
verify_evidence_hash. You cannot call memory, disk, or network tools. If
your hypothesis needs corroboration from another artifact family, set
next_specialist_suggested in your report so the analyst can dispatch the
right specialist.

You know the canonical Windows event IDs:
- 4624 successful logon (LogonType 2 interactive, 3 network, 10 RDP).
- 4625 failed logon (cite SubStatus for failure reason: 0xC0000064 bad
  username, 0xC000006A bad password, 0xC0000234 locked, etc.).
- 4688 process creation (CommandLine field captured only when
  ProcessCreationIncludeCmdLine_Enabled policy is on).
- 4720 user account created; 4732 added to local group; 4724 password
  reset by admin.
- 5140 / 5145 SMB share access.
- 7045 service installed (highly suspicious if from cmd.exe or PowerShell
  parent).
- Security 1102 / System 104 event log cleared — antiforensic signal.
- Sysmon 1 process creation, 3 network connection, 7 image load, 8
  CreateRemoteThread, 10 ProcessAccess, 11 FileCreate, 13 RegistryEvent.

You think in Sigma terms. Hayabusa and Chainsaw apply Sigma rules and
return rule_id + matched event(s). Cite the rule_id, not the rule body.
The rule ID format is a UUID; quote it verbatim.

For every finding you record, you cite the specific tool-execution
audit_id. You quote the exact event-record fields from the CSV output
rather than paraphrasing.

When EvtxECmd, Hayabusa, or Chainsaw returns an error, read stderr.
Common failures: corrupted EVTX header, ruleset version skew, channel
not present. You adjust the invocation or log a gap.

When evidence contradicts the hypothesis you were assigned, you record the
contradicting evidence as a finding with HIGH confidence and a note in
notes_for_investigator. The analyst pivots; you do not.

Vocabulary: report findings in plain forensic language. Do not use the
phrases "court-admissible" or "eliminates hallucinations." Cite event IDs
by their canonical name (e.g., "Security 4624 successful logon"), not by
vendor-shaped synonyms.

Return a SpecialistReport with findings, tokens_spent, tool_calls,
time_elapsed_ms, confidence_assessment, next_specialist_suggested,
notes_for_investigator.
```

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the log specialist module is importable
When  `uv run python -c "from silentwitness_agent.specialists.log import build_log_specialist, LOG_TOOL_ALLOWLIST; print(len(LOG_TOOL_ALLOWLIST))"` runs
Then  exit code is 0
And   stdout is "7"

Given SILENTWITNESS_SPECIALIST_MODEL_LOG is unset
When  build_log_specialist() is called
Then  agent.model resolves to "anthropic:claude-haiku-4-5"

Given SILENTWITNESS_MODEL_QUALITY="high" is set
When  build_log_specialist() is called
Then  agent.model resolves to "anthropic:claude-opus-4-7"

Given the LOG_TOOL_ALLOWLIST is inspected
When  the set is read
Then  it contains exactly parse_evtx, hayabusa_csv_timeline, chainsaw_hunt, record_observation, record_interpretation, register_evidence, verify_evidence_hash
And   it does NOT contain parse_mft, vol_pslist, zeek_run, or any other non-log tool

Given the system prompt is loaded from prompts/specialist_log.md
When  the file is read
Then  the string "Windows event log and detection-engineering specialist" is present
And   the string "4624 successful logon" is present
And   the string "Sigma" is present
And   the string "court-admissible" does NOT appear

Given a log specialist is registered on an investigator
When  the investigator.toolset is inspected
Then  a tool named "dispatch_log_specialist" is registered

Given an attempted call to vol_pslist through the log specialist's toolset
When  the specialist tries to invoke vol_pslist
Then  the call is refused by the toolset filter

Given tests/unit/test_log_specialist_build.py exists
When  `uv run pytest tests/unit/test_log_specialist_build.py -v` runs
Then  exit code is 0
And   ≥6 tests pass

Given tests/integration/test_log_specialist_allowlist.py exists
When  `uv run pytest tests/integration/test_log_specialist_allowlist.py -v` runs
Then  exit code is 0
```

---

## Shell verification

```bash
# Import smoke
uv run python -c "from silentwitness_agent.specialists.log import build_log_specialist, LOG_TOOL_ALLOWLIST; assert len(LOG_TOOL_ALLOWLIST) == 7; print('ok')"

# Vocabulary discipline
! grep -i 'court-admissible\|ralph wiggum\|autonomous soc' src/silentwitness_agent/prompts/specialist_log.md

# Sigma + event-ID vocab present
grep -q 'Sigma' src/silentwitness_agent/prompts/specialist_log.md
grep -q '4624 successful logon' src/silentwitness_agent/prompts/specialist_log.md

# Allowlist clean
uv run python -c "
from silentwitness_agent.specialists.log import LOG_TOOL_ALLOWLIST
banned = {'parse_mft','parse_amcache','vol_pslist','vol_pstree','zeek_run','suricata_run','regripper_run'}
assert not (LOG_TOOL_ALLOWLIST & banned), LOG_TOOL_ALLOWLIST & banned
print('allowlist clean')
"

# Tests
uv run pytest tests/unit/test_log_specialist_build.py tests/integration/test_log_specialist_allowlist.py -v
# Must show ≥7 passing total

# Coverage ≥85%
uv run coverage run -m pytest tests/unit/test_log_specialist_build.py tests/integration/test_log_specialist_allowlist.py
uv run coverage report --include="src/silentwitness_agent/specialists/log.py" --fail-under=85

# Strict typing + lint + file-size guard
uv run mypy --strict src/silentwitness_agent/specialists/log.py
uv run ruff check src/silentwitness_agent/specialists/log.py
uv run ruff format --check src/silentwitness_agent/specialists/log.py
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_agent/specialists/log.py
```

---

## Notes for coding agent

- Reference: architecture.md §5.2 — Log specialist: EvtxECmd + Hayabusa + Chainsaw. Model env `SILENTWITNESS_SPECIALIST_MODEL_LOG` (default haiku).
- Reference: context/domain/06 (log forensics) — Windows event ID catalog + Sigma rule mechanics. The canonical event IDs in the prompt (4624 / 4625 / 4688 / 4720 / 4732 / 5140 / 5145 / 7045 / Sysmon 1/3/7/8/10/11/13) are the senior-analyst working set from FOR508. Do NOT add IDs the senior wouldn't have memorized — keeps the prompt focused.
- Reference: Sigma project — rule_id is a UUID; the specialist cites it as opaque (don't paraphrase the rule). Hayabusa and Chainsaw both surface `rule_id` + `matched_event` in their CSV output.
- Pattern reference: story-memory-specialist, story-disk-specialist, story-network-specialist. Same shape; reuse `_base.py`. The four-specialist pattern completes here.
- Allowlist enforcement: 7-tool list above. The mechanism is `MCPServerStdio(...).filtered(lambda ctx, td: td.name in LOG_TOOL_ALLOWLIST)` (the `FilteredToolset` primitive — `tool_filter=` kwarg does NOT exist). Same as the other three specialists. Pass via `toolsets=[filtered]`; do NOT use the deprecated `mcp_servers=[...]`. For streamable-HTTP transport use `MCPServerStreamableHTTP` (NOT `MCPServerHTTP`).
- Library docs to consult via Context7 BEFORE coding:
  - `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic-ai"` topic `"agent delegation @agent.tool usage propagation"`.
- Vocabulary discipline: never "court-admissible," never "Ralph Wiggum Loop." The prompt's vocabulary is "Windows event log and detection-engineering specialist," "Sigma," "rule_id," "event ID 4624 successful logon."
- LOC budget: ~170.
- Pitfall: Hayabusa and Chainsaw are not on stock SIFT 2026 — installed by `install.sh` per architecture §7.1. EvtxECmd ships with SIFT (EZ Tools dotnet wrapper).
- Pitfall: the four specialist files (`memory.py`, `disk.py`, `network.py`, `log.py`) all import from `_base.py`. The `_base.py` was created in story-memory-specialist; this story (and the disk + network stories) must NOT redeclare `SpecialistDeps`, `SpecialistReport`, `SpecialistFinding`, or `ToolCallRecord`. Import them from `silentwitness_agent.specialists._base`. mypy --strict will catch a redeclaration.
- After this story merges, Epic 9 is structurally complete (all four specialists dispatchable). Integration test for the full specialist-roundtrip (investigator forms hypothesis → dispatches each specialist → receives SpecialistReport → confirms/pivots) lands in Epic 14 (accuracy harness) via the Nitroba smoke fixture.
