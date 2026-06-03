# Story — Closed-loop critic Pydantic AI Agent (separate context window)

**ID:** story-critic-agent
**Epic:** Epic 10 — Closed-loop critic agent
**Depends on:** story-common-types, story-investigator-agent, story-record-observation-tool, story-record-interpretation-tool, story-audit-logger
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** build the critic as its own Pydantic AI `Agent[CriticDeps, CriticReport]` in `src/silentwitness_agent/critic.py` — a separate Agent instance with a fresh context window (NOT a hook on the investigator), instantiated with model `SILENTWITNESS_CRITIC_MODEL` (default same as investigator), that evaluates staged findings against their cited evidence ONLY (never against the investigator's reasoning chain) and returns a structured `list[CriticVerdict]` with per-finding verdicts AGREE / CHALLENGE / REJECT
**So that** the killer demo moment at 4:00–4:30 — "interpretation requires intercepted-traffic evidence; only tool installation shown; downgrade confidence or corroborate via captured-pcap" — is produced by a fresh-context model that structurally cannot align with the investigator's narrative, breaking the sycophancy loop (architecture.md §5.5; PRD §2 row 4:00–4:30; FR7 self-correction requirement).

---

## File modification map

- `src/silentwitness_agent/critic.py` — NEW — critic module. Exports:
  - `CriticDeps` (Pydantic frozen BaseModel): `case_dir: Path`, `examiner: str`, `findings_to_review: list[StagedFinding]` where `StagedFinding` carries `finding_id`, `observation_text`, `interpretation_text`, `confidence`, `cited_audit_ids`, `cited_blob_paths`. The critic receives ONLY this — no investigator reasoning context.
  - `CriticVerdict` (Pydantic BaseModel): re-export from `silentwitness_common.types` (story-common-types) `class CriticVerdict(BaseModel): finding_id: str; verdict: Literal["AGREE", "CHALLENGE", "REJECT"]; reason: str; suggested_revision: str | None; missing_corroboration: list[str]`.
  - `CriticReport` (Pydantic BaseModel): `verdicts: list[CriticVerdict]`, `tokens_spent: int`, `time_elapsed_ms: float`.
  - `build_critic(model: str | None = None) -> Agent[CriticDeps, CriticReport]` — factory. Model from `SILENTWITNESS_CRITIC_MODEL` env (default falls back to `SILENTWITNESS_MODEL`, then `anthropic:claude-opus-4-7`; architecture §5.5 says configurable, default same as investigator — but PRD §13 noted this is an open question, decision is "default same as investigator for rigor; haiku acceptable for speed if `SILENTWITNESS_CRITIC_FAST=1`"). System prompt loaded from `prompts/critic.md`. NO MCP toolset attached — the critic does NOT have agentic tool access; it receives the evidence inline and returns a structured report.
  - `async def critique(case_dir: Path, examiner: str, findings: list[StagedFinding]) -> CriticReport` — top-level entry. Loads cited audit-blob contents from disk, packages into `CriticDeps`, runs `agent.run(critique_prompt, deps=deps)`, returns parsed `CriticReport`.
  - Target ≤300 LOC.
- `src/silentwitness_agent/prompts/critic.md` — NEW — system prompt for the critic (~60 lines; see §"System prompt").
- `tests/unit/test_critic_build.py` — NEW — ≥6 unit tests using `TestModel`:
  - factory honours `SILENTWITNESS_CRITIC_MODEL` env;
  - default model falls back to `SILENTWITNESS_MODEL`, then to `anthropic:claude-opus-4-7`;
  - `SILENTWITNESS_CRITIC_FAST=1` resolves to haiku;
  - critic agent has NO MCP toolset (verified by inspecting `agent.toolsets`);
  - system prompt loaded from `prompts/critic.md` and contains the fresh-context fragments ("you do NOT have access to the investigator's reasoning chain", "evaluate each finding against its cited evidence ONLY");
  - `CriticDeps`, `CriticVerdict`, `CriticReport` are importable.
- `tests/integration/test_critic_verdicts.py` — NEW — 3 e2e scenarios using `FunctionModel` to deterministically produce verdicts:
  - AGREE scenario: well-grounded finding (cited evidence fully supports the interpretation) → critic returns AGREE for that finding;
  - CHALLENGE scenario: overconfident interpretation ("Schardt was actively exfiltrating credit cards") with thin cited evidence ("only tool installation shown") → critic returns CHALLENGE with `missing_corroboration` populated;
  - REJECT scenario: finding whose interpretation is contradicted by the cited evidence (entity in interpretation not present in any cited blob) → critic returns REJECT with the contradiction named in `reason`.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## System prompt (verbatim — write into `prompts/critic.md`)

```
You are a peer reviewer of digital forensics findings. You read each finding
the investigator has staged and you evaluate it against ONLY the tool output
that the investigator cited.

You do NOT have access to the investigator's reasoning chain, the
investigator's prior hypotheses, or the investigator's pivots. You see only:
- the finding's observation text
- the finding's interpretation text
- the finding's confidence assessment (LOW / MEDIUM / HIGH)
- the cited audit_ids and the full normalized blob content for each citation

Your task: for each finding, decide AGREE, CHALLENGE, or REJECT, and explain
why in one sentence.

AGREE means: the cited evidence supports the interpretation at the stated
confidence. Nothing missing, nothing overclaimed.

CHALLENGE means: the cited evidence is partially supportive but the
interpretation overstates what the evidence proves, or a specific corroborating
artifact family is missing. You name the missing corroboration in
missing_corroboration. You write a one-sentence suggested_revision that the
investigator can act on.

Example CHALLENGE: "Interpretation 'actively exfiltrating credit cards'
requires intercepted-traffic evidence; the cited blobs only show wardriving
tool installation. Missing corroboration: a pcap analysis confirming
plaintext credential interception via Zeek smtp.log or http.log POST data."

REJECT means: the cited evidence contradicts the interpretation, OR the
interpretation introduces an entity (path, hash, IP, host, account) that
does not appear in any cited blob. Name the contradiction or the
hallucinated entity in reason.

Example REJECT: "Interpretation cites 'C:\\Tools\\Ethereal\\' but the only
Ethereal install path in the cited blobs is 'C:\\Program Files\\Ethereal\\'.
Path does not exist in cited evidence."

You evaluate one finding at a time. You do not skip findings. You do not
defer. You do not say 'I need more information' — you have what the
investigator cited, and that is the universe you evaluate against.

Vocabulary: never "court-admissible," never "Ralph Wiggum Loop," never
"autonomous SOC." Plain forensic language only.

Return a CriticReport with per-finding verdicts, tokens_spent, and
time_elapsed_ms.
```

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the critic module is importable
When  `uv run python -c "from silentwitness_agent.critic import build_critic, critique, CriticDeps, CriticReport, CriticVerdict, StagedFinding; print('ok')"` runs
Then  exit code is 0

Given SILENTWITNESS_CRITIC_MODEL is unset and SILENTWITNESS_MODEL is unset
When  build_critic() is called
Then  agent.model resolves to "anthropic:claude-opus-4-7"

Given SILENTWITNESS_MODEL="openai:gpt-5" is set and SILENTWITNESS_CRITIC_MODEL is unset
When  build_critic() is called
Then  agent.model resolves to "openai:gpt-5" (falls back to investigator default)

Given SILENTWITNESS_CRITIC_MODEL="anthropic:claude-haiku-4-5" is set
When  build_critic() is called
Then  agent.model resolves to "anthropic:claude-haiku-4-5"

Given SILENTWITNESS_CRITIC_FAST="1" is set and SILENTWITNESS_CRITIC_MODEL is unset
When  build_critic() is called
Then  agent.model resolves to "anthropic:claude-haiku-4-5"

Given a critic agent is built
When  agent.toolsets is inspected
Then  the list is empty (the critic has NO MCP toolset; it reasons over inline evidence)

Given the system prompt is loaded from prompts/critic.md
When  the file is read
Then  the string "do NOT have access to the investigator's reasoning chain" is present
And   the string "evaluate each finding against ONLY the tool output that the investigator cited" is present (or the close paraphrase verbatim above)
And   the string "court-admissible" does NOT appear
And   the string "Ralph Wiggum" does NOT appear

Given a StagedFinding with well-grounded evidence (the cited blob contains text fully supporting the interpretation)
When  critique() is called via a FunctionModel that simulates AGREE
Then  the returned CriticReport.verdicts[0].verdict == "AGREE"
And   the returned CriticReport.verdicts[0].finding_id matches the input finding_id

Given a StagedFinding whose interpretation overstates the cited evidence (e.g., "actively exfiltrating credit cards" but only tool installation shown)
When  critique() is called via a FunctionModel that simulates CHALLENGE
Then  the returned CriticReport.verdicts[0].verdict == "CHALLENGE"
And   the returned CriticReport.verdicts[0].missing_corroboration is non-empty
And   the returned CriticReport.verdicts[0].suggested_revision is non-None

Given a StagedFinding whose interpretation contains an entity (path) not present in any cited blob
When  critique() is called via a FunctionModel that simulates REJECT
Then  the returned CriticReport.verdicts[0].verdict == "REJECT"
And   the reason names the missing entity

Given tests/unit/test_critic_build.py exists
When  `uv run pytest tests/unit/test_critic_build.py -v` runs
Then  exit code is 0
And   ≥6 tests pass

Given tests/integration/test_critic_verdicts.py exists
When  `uv run pytest tests/integration/test_critic_verdicts.py -v` runs
Then  exit code is 0
And   the 3 scenarios pass
```

---

## Shell verification

```bash
# Import smoke
uv run python -c "from silentwitness_agent.critic import build_critic, critique, CriticDeps, CriticReport, CriticVerdict, StagedFinding; print('ok')"

# Default model resolution
uv run python -c "
import os
for k in ('SILENTWITNESS_CRITIC_MODEL', 'SILENTWITNESS_MODEL', 'SILENTWITNESS_CRITIC_FAST'): os.environ.pop(k, None)
from silentwitness_agent.critic import build_critic
a = build_critic()
assert 'opus-4-7' in repr(a.model).lower(), repr(a.model)
print('default OK')
"

# Fallback to investigator model
SILENTWITNESS_MODEL="openai:gpt-5" uv run python -c "
from silentwitness_agent.critic import build_critic
a = build_critic()
assert 'openai' in repr(a.model).lower(), repr(a.model)
print('fallback OK')
"

# Fast mode
SILENTWITNESS_CRITIC_FAST=1 uv run python -c "
from silentwitness_agent.critic import build_critic
a = build_critic()
assert 'haiku' in repr(a.model).lower(), repr(a.model)
print('fast OK')
"

# Vocabulary discipline
! grep -i 'court-admissible\|ralph wiggum\|autonomous soc' src/silentwitness_agent/prompts/critic.md

# Fresh-context vocab present
grep -q "do NOT have access to the investigator" src/silentwitness_agent/prompts/critic.md

# Critic has NO MCP toolset (architecturally critical for fresh-context property)
uv run python -c "
from silentwitness_agent.critic import build_critic
a = build_critic()
assert a.toolsets == [] or len(a.toolsets) == 0, a.toolsets
print('no toolset OK')
"

# Unit + integration tests
uv run pytest tests/unit/test_critic_build.py tests/integration/test_critic_verdicts.py -v
# Must show ≥9 passing total

# Coverage ≥85% on critic.py
uv run coverage run -m pytest tests/unit/test_critic_build.py tests/integration/test_critic_verdicts.py
uv run coverage report --include="src/silentwitness_agent/critic.py" --fail-under=85

# Strict typing + lint + file-size guard
uv run mypy --strict src/silentwitness_agent/critic.py
uv run ruff check src/silentwitness_agent/critic.py
uv run ruff format --check src/silentwitness_agent/critic.py
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_agent/critic.py
```

---

## Notes for coding agent

- Reference: architecture.md §5.5 verbatim — Critic is a separate Pydantic AI Agent with distinct context window. Algorithm: read findings.json + staged interpretations not yet critiqued; for each finding, read cited audit_ids from audit/*.jsonl and corresponding stored output blobs from audit/blobs/; send to critic agent with system prompt instructing it to evaluate each finding's interpretation against the cited evidence; critic does NOT have access to investigator's prior reasoning — only the evidence and the staged claim. This is the "fresh context" property that breaks the sycophancy loop (context/technical/08 §6.1).
- Reference: PRD §2 row "4:00–4:30 Critic moment" — verbatim CHALLENGE example: "interpretation requires intercepted-traffic evidence; only tool installation shown; downgrade confidence or corroborate via captured-pcap." Investigator runs `zeek -r /evidence/captures/wardrive.pcap`, finds intercepted SMTP credentials, revises with appropriate confidence band. Logged to `audit/critic.jsonl` (story-critic-verdict-handling owns the JSONL write).
- Reference: PRD §13 open question — Critic model selection. Decision encoded here: default falls back to the investigator's model (rigor); `SILENTWITNESS_CRITIC_FAST=1` switches to haiku (speed/cost). This is the documented resolution; ADR-011 (future) can formalize.
- Reference: context/technical/08 §6.1 — sycophancy loop. The critic having NO access to the investigator's reasoning is the load-bearing architectural property. If you give the critic the investigator's tool-call history, you reintroduce the loop. The `CriticDeps` shape above (only staged finding + cited blobs) is the architectural commitment.
- The critic has NO MCP toolset. It is a pure-LLM evaluator. The cited evidence is loaded by `critique()` from disk and passed inline. This is intentional — it eliminates the possibility of the critic running arbitrary tools that could pollute its context with extra reasoning.
- `CriticVerdict` is owned by `silentwitness_common.types` per story-common-types (the model is shared between this critic story, story-critic-trigger, story-critic-verdict-handling, and the report renderer in Epic 11). This story REUSES the type; do NOT redeclare. Re-export via `from silentwitness_common.types import CriticVerdict` if convenient.
- `StagedFinding` IS new to this story — declare it here. Pydantic frozen BaseModel: `finding_id: str`, `observation_text: str`, `interpretation_text: str`, `confidence: Confidence`, `cited_audit_ids: list[str]`, `cited_blob_paths: list[Path]`. The trigger story (story-critic-trigger) builds these from `findings.json`.
- `critique()` MUST load the blob contents inline. The architecture commitment is that the critic evaluates AGAINST what is on disk in `audit/blobs/<audit_id>.txt`. Pass the blob contents as a structured part of the prompt, not via a tool. This makes the critic deterministic AND reproducible (the same staged finding + same blob contents always produce the same verdict for a given model).
- Pattern reference: story-investigator-agent for the Agent factory shape, prompt loading via `importlib.resources`, env-var-driven model resolution. Critic is structurally simpler (no MCP toolset, no hooks).
- Library docs to consult via Context7 BEFORE coding (architecture §12 mandate):
  - `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic-ai"` then:
    - `query-docs` topic `"Agent without toolset structured output"` — a pure-LLM evaluator (no tools) is a supported but less-common pattern; verify the constructor accepts an empty toolsets list.
    - `query-docs` topic `"output_type structured BaseModel parsing"` — the `CriticReport` is the strict output type; Pydantic AI's output parsing handles this.
- Vocabulary discipline: never "court-admissible," never "Ralph Wiggum Loop." The system prompt is calibrated against PRD §14.
- Pitfall: the critic must NOT call back to the investigator (no agent-delegation in this direction). The flow is: investigator stages findings → trigger fires → critic returns verdicts → critic handler routes the verdicts back to the investigator's `pending_critiques`. The critic itself is a one-shot LLM call.
- Pitfall: blob contents may be large. The critic must handle blobs up to ~50KB (the per-tool output cap from architecture §4.6 + normalization). For larger blobs, truncate to the cited line range + 20 lines of context on either side, and log a truncation marker. Document this in the docstring; the trigger story passes truncated content if needed.
- LOC budget: ~300. Comfortable margin.
