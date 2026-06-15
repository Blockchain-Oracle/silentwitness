# Story — Network specialist subagent (Pydantic AI agent-delegation)

**ID:** story-network-specialist
**Epic:** Epic 9 — Specialist subagents (memory / disk / network / log)
**Depends on:** story-disk-specialist, story-zeek-run, story-suricata-run, story-record-observation-tool, story-record-interpretation-tool
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** build the network specialist as its own Pydantic AI `Agent[SpecialistDeps, SpecialistReport]` in `src/silentwitness_agent/specialists/network.py`, invoked by the investigator via agent-delegation, with a tight MCP allowlist limited to network forensics tools (Zeek, Suricata) plus `record_*` and evidence-registry tools
**So that** pcap-derived corroboration (the demo's 4:00–4:30 moment where the critic challenges an interpretation and the agent runs `zeek -r /evidence/captures/wardrive.pcap` to find intercepted SMTP credentials) is dispatched to a focused specialist with the beacon-detection + connection-graph mental model, and the investigator's main context window stays lean (architecture.md §5.2 — Network specialist).

---

## File modification map

- `src/silentwitness_agent/specialists/network.py` — NEW — network specialist. Exports:
  - `NETWORK_TOOL_ALLOWLIST` (frozenset[str]): `{"zeek_run", "suricata_run", "record_observation", "record_interpretation", "register_evidence", "verify_evidence_hash"}` (6 total).
  - `build_network_specialist(model: str | None = None) -> Agent[SpecialistDeps, SpecialistReport]` — factory. Model from `SILENTWITNESS_SPECIALIST_MODEL_NETWORK` env (default `anthropic:claude-haiku-4-5`; opus if `SILENTWITNESS_MODEL_QUALITY=high`). Reuses `SpecialistDeps` + `SpecialistReport` from `_base`. Toolset is `MCPServerStdio(...).filtered(lambda ctx, td: td.name in NETWORK_TOOL_ALLOWLIST)` (see "Pydantic AI tool_filter correction" note below).

> **Pydantic AI tool_filter correction:** `MCPServerStdio(..., tool_filter=...)` does NOT exist. Use `MCPServerStdio(...).filtered(lambda ctx, td: td.name in ALLOWLIST)`. The real primitive is `pydantic_ai.FilteredToolset` (source: `pydantic_ai_slim/pydantic_ai/toolsets/filtered.py`). Pass the filtered toolset via `toolsets=[filtered]` (NOT `mcp_servers=[...]`, which is deprecated). For streamable-HTTP transport use `MCPServerStreamableHTTP` (NOT `MCPServerHTTP`).
  - `register_as_investigator_tool(investigator: Agent, network_specialist: Agent) -> None` — registers `dispatch_network_specialist(question: str, hypothesis_id: str) -> SpecialistReport`.
  - Target ≤160 LOC.
- `src/silentwitness_agent/prompts/specialist_network.md` — NEW — system prompt (~50 lines; see §"System prompt").
- `tests/unit/test_network_specialist_build.py` — NEW — ≥6 unit tests: env override; default model; quality=high upgrade; allowlist contains exactly 6 expected tools; dispatch_network_specialist registered; system prompt contains "network forensics" + "beacon detection".
- `tests/integration/test_network_specialist_allowlist.py` — NEW — 1 scenario: network specialist attempting to call `parse_mft` (a disk tool) is refused.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## System prompt (verbatim — write into `prompts/specialist_network.md`)

```
You are a network forensics specialist working under a senior incident
response analyst. The analyst hands you exactly one hypothesis at a time
and asks you to test it against the pcap evidence registered for this case.

Your toolset is limited to Zeek (zeek_run) and Suricata (suricata_run),
plus record_observation, record_interpretation, register_evidence, and
verify_evidence_hash. You cannot call memory, disk, or log tools. If your
hypothesis needs corroboration from another artifact family, set
next_specialist_suggested in your report so the analyst can dispatch the
right specialist.

You think in connection graphs and beacon patterns. Concretely:
- Zeek conn.log gives you the 5-tuple per session (src/dst IP, src/dst
  port, proto), duration, bytes, orig_bytes vs resp_bytes. Strong starting
  point for any pcap question.
- Zeek dns.log surfaces resolution patterns. Repeated short-TTL lookups to
  algorithmically-shaped domains are a beacon signal.
- Zeek http.log + ssl.log give you the application-layer view.
- Suricata fires rule-based alerts (ET Open rules; Emerging Threats Pro if
  registered). Useful for known-bad pattern matches; the rule_id is what
  you cite, not the rule body.
- Beacon detection lives in the time-delta histogram of conn.log entries
  to the same dst_ip. Periodicity (e.g., 60s ± jitter) over a 30+ minute
  window is a beacon. Note this in confidence_assessment.
- Intercepted plaintext credentials show up in Zeek's smtp.log, ftp.log,
  http.log (form-data POSTs), and weak_ssl.log. State the plaintext-vs-TLS
  distinction explicitly when you cite a credential observation.

For every finding you record, you cite the specific tool-execution
audit_id. You quote the exact log-line from Zeek's structured output or
the exact alert from Suricata's eve.json rather than paraphrasing.

When Zeek or Suricata returns an error, read stderr. Common failures:
truncated pcap, encrypted unsegmented streams, IP-fragment reassembly
disabled. You adjust the invocation (toggle reassembly, fall back to a
narrower BPF) or log a gap.

When evidence contradicts the hypothesis you were assigned, you record the
contradicting evidence as a finding with HIGH confidence and a note in
notes_for_investigator. The analyst pivots; you do not.

Vocabulary: report findings in plain forensic language. Do not use the
phrases "court-admissible" or "eliminates hallucinations." Do not name
attacker groups unless their TTPs are directly evidenced in your output.

Return a SpecialistReport with findings, tokens_spent, tool_calls,
time_elapsed_ms, confidence_assessment, next_specialist_suggested,
notes_for_investigator.
```

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the network specialist module is importable
When  `uv run python -c "from silentwitness_agent.specialists.network import build_network_specialist, NETWORK_TOOL_ALLOWLIST; print(len(NETWORK_TOOL_ALLOWLIST))"` runs
Then  exit code is 0
And   stdout is "6"

Given SILENTWITNESS_SPECIALIST_MODEL_NETWORK is unset
When  build_network_specialist() is called
Then  agent.model resolves to "anthropic:claude-haiku-4-5"

Given SILENTWITNESS_MODEL_QUALITY="high" is set
When  build_network_specialist() is called
Then  agent.model resolves to "anthropic:claude-opus-4-7"

Given the NETWORK_TOOL_ALLOWLIST is inspected
When  the set is read
Then  it contains exactly zeek_run, suricata_run, record_observation, record_interpretation, register_evidence, verify_evidence_hash
And   it does NOT contain parse_mft, vol_pslist, parse_evtx, or any other non-network tool

Given the system prompt is loaded from prompts/specialist_network.md
When  the file is read
Then  the string "network forensics specialist" is present
And   the string "Beacon detection" is present
And   the string "court-admissible" does NOT appear

Given a network specialist is registered on an investigator
When  the investigator.toolset is inspected
Then  a tool named "dispatch_network_specialist" is registered

Given an attempted call to parse_mft through the network specialist's toolset
When  the specialist tries to invoke parse_mft
Then  the call is refused by the toolset filter

Given tests/unit/test_network_specialist_build.py exists
When  `uv run pytest tests/unit/test_network_specialist_build.py -v` runs
Then  exit code is 0
And   ≥6 tests pass

Given tests/integration/test_network_specialist_allowlist.py exists
When  `uv run pytest tests/integration/test_network_specialist_allowlist.py -v` runs
Then  exit code is 0
```

---

## Shell verification

```bash
# Import smoke
uv run python -c "from silentwitness_agent.specialists.network import build_network_specialist, NETWORK_TOOL_ALLOWLIST; assert len(NETWORK_TOOL_ALLOWLIST) == 6; print('ok')"

# Vocabulary discipline
! grep -i 'court-admissible\|ralph wiggum\|autonomous soc' src/silentwitness_agent/prompts/specialist_network.md

# Beacon-detection vocab present
grep -q 'Beacon detection' src/silentwitness_agent/prompts/specialist_network.md

# Allowlist clean
uv run python -c "
from silentwitness_agent.specialists.network import NETWORK_TOOL_ALLOWLIST
banned = {'parse_mft','parse_amcache','vol_pslist','vol_pstree','parse_evtx','hayabusa_csv_timeline','chainsaw_hunt','regripper_run'}
assert not (NETWORK_TOOL_ALLOWLIST & banned), NETWORK_TOOL_ALLOWLIST & banned
print('allowlist clean')
"

# Tests
uv run pytest tests/unit/test_network_specialist_build.py tests/integration/test_network_specialist_allowlist.py -v
# Must show ≥7 passing total

# Coverage ≥85%
uv run coverage run -m pytest tests/unit/test_network_specialist_build.py tests/integration/test_network_specialist_allowlist.py
uv run coverage report --include="src/silentwitness_agent/specialists/network.py" --fail-under=85

# Strict typing + lint + file-size guard
uv run mypy --strict src/silentwitness_agent/specialists/network.py
uv run ruff check src/silentwitness_agent/specialists/network.py
uv run ruff format --check src/silentwitness_agent/specialists/network.py
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_agent/specialists/network.py
```

---

## Notes for coding agent

- Reference: architecture.md §5.2 — Network specialist: Zeek + Suricata. Model env `SILENTWITNESS_SPECIALIST_MODEL_NETWORK` (default haiku).
- Reference: PRD §2 row "4:00–4:30 Critic moment" — the network specialist is the one the investigator dispatches AFTER the critic CHALLENGE fires. The agent runs `zeek -r /evidence/captures/wardrive.pcap` and finds intercepted SMTP credentials in `smtp.log`. The system prompt's "plaintext-vs-TLS distinction explicitly" line is what produces the well-calibrated `confidence_assessment` after this dispatch.
- Reference: context/domain/05 (network forensics) — Zeek log family semantics. The system prompt encodes the senior-analyst mental model: connection graphs first, then beacon patterns from time-delta histograms, then alert correlation via Suricata rule IDs.
- Pattern reference: story-memory-specialist and story-disk-specialist. Same shape; reuse `_base.py` SpecialistDeps + SpecialistReport.
- Allowlist enforcement: 6-tool list above is the smallest of the four specialists. The mechanism is `MCPServerStdio(...).filtered(lambda ctx, td: td.name in NETWORK_TOOL_ALLOWLIST)` (the `FilteredToolset` primitive — `tool_filter=` kwarg does NOT exist). Same as memory/disk. Pass via `toolsets=[filtered]`; do NOT use the deprecated `mcp_servers=[...]`. For streamable-HTTP transport use `MCPServerStreamableHTTP` (NOT `MCPServerHTTP`).
- Library docs to consult via Context7 BEFORE coding:
  - `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic-ai"` topic `"agent delegation @agent.tool usage propagation"`.
- Vocabulary discipline: never "court-admissible," never "Ralph Wiggum Loop." The prompt's vocabulary is "network forensics specialist," "connection graphs," "beacon detection," "plaintext-vs-TLS distinction."
- LOC budget: ~160. Shortest specialist (only 2 tool families plus the standard record/registry tools).
- Pitfall: Zeek and Suricata are not on stock SIFT 2026 by default — `install.sh` installs them per architecture.md §7.1. The specialist's behavior is unchanged; this is just a deployment note for the dependent stories.
