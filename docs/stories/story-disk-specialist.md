# Story — Disk specialist subagent (Pydantic AI agent-delegation)

**ID:** story-disk-specialist
**Epic:** Epic 9 — Specialist subagents (memory / disk / network / log)
**Depends on:** story-memory-specialist, story-parse-mft, story-parse-amcache-shimcache, story-parse-prefetch, story-parse-shellbags, story-regripper, story-record-observation-tool, story-record-interpretation-tool
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** build the disk specialist as its own Pydantic AI `Agent[SpecialistDeps, SpecialistReport]` in `src/silentwitness_agent/specialists/disk.py`, invoked by the investigator via agent-delegation, with a tight MCP allowlist limited to disk + registry tools (MFT, Amcache, Shimcache, Prefetch, Shellbags, RegRipper) plus `record_*` and evidence-registry tools
**So that** disk-and-NTFS-artifact reasoning (the "what was executed when" question that takes up Hours 6–14 of any IR engagement per context/user/09) runs in a focused context window and produces structured findings the investigator can chain into a coherent timeline (architecture.md §5.2 — Disk specialist; matches PRD demo arc 1:00–3:00 "disk-corroboration step: Ethereal install at C:\Program Files\Ethereal\").

---

## File modification map

- `src/silentwitness_agent/specialists/disk.py` — NEW — disk specialist. Exports:
  - `DISK_TOOL_ALLOWLIST` (frozenset[str]): `{"parse_mft", "parse_amcache", "parse_shimcache", "parse_prefetch", "parse_shellbags", "regripper_run", "record_observation", "record_interpretation", "register_evidence", "verify_evidence_hash"}` (10 total).
  - `build_disk_specialist(model: str | None = None) -> Agent[SpecialistDeps, SpecialistReport]` — factory. Model from `SILENTWITNESS_SPECIALIST_MODEL_DISK` env (default `anthropic:claude-haiku-4-5`; opus if `SILENTWITNESS_MODEL_QUALITY=high`). Imports `SpecialistDeps` + `SpecialistReport` from `_base`. Toolset is `MCPServerStdio(...).filtered(lambda ctx, td: td.name in DISK_TOOL_ALLOWLIST)` (see "Pydantic AI tool_filter correction" note below).

> **Pydantic AI tool_filter correction:** `MCPServerStdio(..., tool_filter=...)` does NOT exist. Use `MCPServerStdio(...).filtered(lambda ctx, td: td.name in ALLOWLIST)`. The real primitive is `pydantic_ai.FilteredToolset` (source: `pydantic_ai_slim/pydantic_ai/toolsets/filtered.py`). Pass the filtered toolset via `toolsets=[filtered]` (NOT `mcp_servers=[...]`, which is deprecated). For streamable-HTTP transport use `MCPServerStreamableHTTP` (NOT `MCPServerHTTP`).
  - `register_as_investigator_tool(investigator: Agent, disk_specialist: Agent) -> None` — registers `dispatch_disk_specialist(question: str, hypothesis_id: str) -> SpecialistReport`.
  - Target ≤180 LOC (~80 LOC less than memory because `_base.py` carries the shared types).
- `src/silentwitness_agent/prompts/specialist_disk.md` — NEW — system prompt for the disk specialist (~50 lines; see §"System prompt" below).
- `tests/unit/test_disk_specialist_build.py` — NEW — ≥6 unit tests: factory honours env override; default model; quality=high upgrade; allowlist contains exactly 10 expected tools; dispatch_disk_specialist registered on investigator; system prompt loaded with NTFS + Shimcache vocabulary fragments.
- `tests/integration/test_disk_specialist_allowlist.py` — NEW — 1 scenario: disk specialist asked to call `vol_pslist` (a memory tool) is refused by the toolset filter.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## System prompt (verbatim — write into `prompts/specialist_disk.md`)

```
You are a disk and NTFS-artifact forensics specialist working under a
senior incident response analyst. The analyst hands you exactly one
hypothesis at a time and asks you to test it against the disk and registry
evidence registered for this case.

Your toolset is limited to MFT, Amcache, Shimcache, Prefetch, and Shellbags
parsers (Eric Zimmerman's EZ Tools), plus RegRipper for registry hive
plugins, plus record_observation, record_interpretation, register_evidence,
and verify_evidence_hash. You cannot call memory, log, or network tools. If
your hypothesis needs corroboration from another artifact family, set
next_specialist_suggested in your report so the analyst can dispatch the
right specialist.

You know the artifact discipline:
- MFT records prove file PRESENCE and timestamps but not EXECUTION.
- Amcache records the first-time SHA1 + file size of a portable executable
  ever loaded, plus driver staging. Strong execution evidence.
- Shimcache records the file presence on the volume at the time the cache
  was written. PROVES PRESENCE, NOT EXECUTION. State this constraint
  whenever you cite a Shimcache entry.
- Prefetch records an actual execution event with first-and-last run
  timestamps and run count. Strong execution evidence.
- Shellbags record folder-navigation by the user via Explorer. Proves
  USER VIEWED a folder, not that anything was executed in it.
- RegRipper plugins surface persistence keys (Run, RunOnce, Image File
  Execution Options), USB device history, network history, service
  registrations.

For every finding you record, you cite the specific tool-execution
audit_id. You quote the exact line from the tool's CSV output rather than
paraphrasing.

When a parser returns an error, read stderr. Common failures: corrupted
hive, NTFS journal too short, parser version skew. You adjust your call
(re-extract, fall back to a different parser, log a gap) rather than
rerunning the same call.

When evidence contradicts the hypothesis you were assigned, you record the
contradicting evidence as a finding with HIGH confidence and a note in
notes_for_investigator. The analyst pivots; you do not.

Vocabulary: report findings in plain forensic language. Do not use the
phrases "court-admissible" or "eliminates hallucinations."

Return a SpecialistReport with findings, tokens_spent, tool_calls,
time_elapsed_ms, confidence_assessment, next_specialist_suggested,
notes_for_investigator.
```

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the disk specialist module is importable
When  `uv run python -c "from silentwitness_agent.specialists.disk import build_disk_specialist, DISK_TOOL_ALLOWLIST; print(len(DISK_TOOL_ALLOWLIST))"` runs
Then  exit code is 0
And   stdout is "10"

Given SILENTWITNESS_SPECIALIST_MODEL_DISK is unset and SILENTWITNESS_MODEL_QUALITY is unset
When  build_disk_specialist() is called
Then  agent.model resolves to "anthropic:claude-haiku-4-5"

Given SILENTWITNESS_MODEL_QUALITY="high" is set in the env
When  build_disk_specialist() is called
Then  agent.model resolves to "anthropic:claude-opus-4-7"

Given the DISK_TOOL_ALLOWLIST is inspected
When  the set is read
Then  it contains parse_mft, parse_amcache, parse_shimcache, parse_prefetch, parse_shellbags, regripper_run, record_observation, record_interpretation, register_evidence, verify_evidence_hash
And   it does NOT contain vol_pslist, zeek_run, parse_evtx, or any other non-disk tool

Given the system prompt is loaded from prompts/specialist_disk.md
When  the file is read
Then  the string "disk and NTFS-artifact forensics specialist" is present
And   the string "Shimcache" and "PROVES PRESENCE, NOT EXECUTION" both appear
And   the string "court-admissible" does NOT appear

Given a disk specialist is constructed and registered on an investigator
When  the investigator.toolset is inspected
Then  a tool named "dispatch_disk_specialist" is registered

Given an attempted call to vol_pslist through the disk specialist's toolset
When  the specialist tries to invoke vol_pslist
Then  the call is refused by the toolset filter

Given tests/unit/test_disk_specialist_build.py exists
When  `uv run pytest tests/unit/test_disk_specialist_build.py -v` runs
Then  exit code is 0
And   ≥6 tests pass

Given tests/integration/test_disk_specialist_allowlist.py exists
When  `uv run pytest tests/integration/test_disk_specialist_allowlist.py -v` runs
Then  exit code is 0
```

---

## Shell verification

```bash
# Import smoke
uv run python -c "from silentwitness_agent.specialists.disk import build_disk_specialist, DISK_TOOL_ALLOWLIST; assert len(DISK_TOOL_ALLOWLIST) == 10; print('ok')"

# Default model
uv run python -c "
import os
for k in ('SILENTWITNESS_SPECIALIST_MODEL_DISK', 'SILENTWITNESS_MODEL_QUALITY'): os.environ.pop(k, None)
from silentwitness_agent.specialists.disk import build_disk_specialist
a = build_disk_specialist()
assert 'haiku' in repr(a.model).lower(), repr(a.model)
print('default OK')
"

# Vocabulary discipline
! grep -i 'court-admissible\|ralph wiggum\|autonomous soc' src/silentwitness_agent/prompts/specialist_disk.md

# Artifact-discipline vocabulary present
grep -q 'PROVES PRESENCE, NOT EXECUTION' src/silentwitness_agent/prompts/specialist_disk.md

# Allowlist clean
uv run python -c "
from silentwitness_agent.specialists.disk import DISK_TOOL_ALLOWLIST
banned = {'vol_pslist','vol_pstree','vol_psscan','vol_malfind','vol_netscan','vol_cmdline','vol_dlllist','vol_handles','vol_lsadump','zeek_run','suricata_run','parse_evtx','hayabusa_csv_timeline','chainsaw_hunt'}
assert not (DISK_TOOL_ALLOWLIST & banned), DISK_TOOL_ALLOWLIST & banned
print('allowlist clean')
"

# Tests
uv run pytest tests/unit/test_disk_specialist_build.py tests/integration/test_disk_specialist_allowlist.py -v
# Must show ≥7 passing total

# Coverage ≥85%
uv run coverage run -m pytest tests/unit/test_disk_specialist_build.py tests/integration/test_disk_specialist_allowlist.py
uv run coverage report --include="src/silentwitness_agent/specialists/disk.py" --fail-under=85

# Strict typing + lint + file-size guard
uv run mypy --strict src/silentwitness_agent/specialists/disk.py
uv run ruff check src/silentwitness_agent/specialists/disk.py
uv run ruff format --check src/silentwitness_agent/specialists/disk.py
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_agent/specialists/disk.py
```

---

## Notes for coding agent

- Reference: architecture.md §5.2 — Disk specialist:
  - Tools: MFTECmd, AmcacheParser, AppCompatCacheParser, PECmd, SBECmd + Sleuth Kit subset.
  - Model: `SILENTWITNESS_SPECIALIST_MODEL_DISK` env (default haiku, opus on quality=high).
  - System prompt: disk + NTFS-artifact frame.
- Reference: PRD §2 row "1:00–3:00 Live terminal" — the disk specialist is the one that corroborates the Ethereal install via MFT record dated 2004-08-19 22:48 UTC. The Shimcache discipline ("PROVES PRESENCE, NOT EXECUTION") is the canonical artifact-interpretation gotcha that distinguishes a senior analyst from a junior one (Valhuntir's caveat catalog encodes this verbatim — context/competitive/11 §2 Forensic Knowledge enrichment).
- Reference: context/domain/03 (memory) + context/domain/04 (disk) — NTFS artifact families. Shimcache/Amcache/Prefetch/MFT distinctions are senior-level discipline; the system prompt encodes them so the specialist's interpretation language is calibrated.
- Pattern reference: story-memory-specialist. Same shape, different allowlist + prompt + model env var. Reuse `_base.py` (SpecialistDeps, SpecialistReport, SpecialistFinding, ToolCallRecord) and `_load_specialist_prompt` from `_base`. Do NOT redeclare them.
- Allowlist enforcement: same `MCPServerStdio(...).filtered(lambda ctx, td: td.name in DISK_TOOL_ALLOWLIST)` pattern as memory specialist (real `FilteredToolset` primitive; `tool_filter=` kwarg does NOT exist). The list of 10 tools above is the only surface; everything else is invisible to the specialist's model. Pass via `toolsets=[filtered]`; do NOT use the deprecated `mcp_servers=[...]` kwarg. For streamable-HTTP transport use `MCPServerStreamableHTTP` (NOT `MCPServerHTTP`).
- Agent-delegation registration: same `@investigator.tool` pattern as memory specialist. Returns `SpecialistReport`. `usage=ctx.usage` propagation is mandatory for budget accounting.
- Library docs to consult via Context7 BEFORE coding:
  - `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic-ai"` topic `"agent delegation @agent.tool usage propagation"`.
- Vocabulary discipline: never "court-admissible." Prompts use "disk and NTFS-artifact forensics specialist." The Shimcache "PROVES PRESENCE, NOT EXECUTION" phrasing is intentionally uppercase in the prompt for emphasis — coding agent must preserve case verbatim.
- LOC budget: ~180. The shared types are in `_base.py` from story-memory-specialist.
- Pitfall: this story does NOT modify `_base.py`. If a new field is genuinely needed in `SpecialistReport` (it isn't — the existing shape covers all four specialists), refactor `_base.py` in a follow-up story, NOT here.
