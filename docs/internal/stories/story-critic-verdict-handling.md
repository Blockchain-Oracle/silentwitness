# Story — Critic verdict handler (AGREE / CHALLENGE / REJECT routing)

**ID:** story-critic-verdict-handling
**Epic:** Epic 10 — Closed-loop critic agent
**Depends on:** story-critic-agent, story-critic-trigger, story-investigator-agent, story-audit-logger
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** build the critic verdict handler in `src/silentwitness_agent/critic_handler.py` — a function that receives `list[CriticVerdict]` from the critic and routes each verdict: AGREE → mark finding critic-approved (no-op for the investigator); CHALLENGE → push the verdict onto the investigator's `pending_critiques` so the agent reads it on its next turn; REJECT → auto-archive the finding to `cases/<case_id>/findings.archived.json` with the reason — and emit one JSONL line per verdict to `cases/<case_id>/audit/critic.jsonl` regardless of disposition
**So that** the demo's 4:00–4:30 critic CHALLENGE moment closes the loop architecturally (investigator gets the challenge, corroborates via the network specialist, revises the interpretation), REJECTed findings are never silently deleted (always archived + audit-logged), and the `audit/critic.jsonl` file IS the defensible record of every critic decision (architecture.md §5.5 — verdict routing semantics).

---

## File modification map

- `src/silentwitness_agent/critic_handler.py` — NEW — verdict handler module. Exports:
  - `handle_critic_verdicts(case_dir: Path, examiner: str, verdicts: list[CriticVerdict], pending_critiques: list[CriticVerdict]) -> CriticHandlerResult` — top-level entry. For each verdict, routes per the table below. Returns a structured summary of (agree_count, challenge_count, reject_count, archived_finding_ids, audit_lines_written).
  - `_handle_agree(case_dir, examiner, verdict) -> None` — emits a `{type:"agree", finding_id, reason, ts}` line to `audit/critic.jsonl`. Updates `findings.json` to mark `finding.critic_status="AGREED"`. No investigator-side state change.
  - `_handle_challenge(case_dir, examiner, verdict, pending_critiques) -> None` — emits a `{type:"challenge", finding_id, reason, suggested_revision, missing_corroboration, ts}` line to `audit/critic.jsonl`. Appends the verdict to `pending_critiques` (the shared mutable list from `InvestigatorDeps` per story-investigator-agent). Updates `findings.json` to mark `finding.critic_status="CHALLENGED"` and stores the challenge reason inline on the finding for report-rendering.
  - `_handle_reject(case_dir, examiner, verdict) -> None` — emits a `{type:"reject", finding_id, reason, ts}` line to `audit/critic.jsonl`. Moves the finding from `findings.json` to `findings.archived.json` (atomic). Sets `finding.status="ARCHIVED"` and `finding.critic_status="REJECTED"` + `finding.archival_reason=verdict.reason` on the archived record. The finding is NEVER silently deleted — the audit trail is the architectural commitment.
  - `CriticHandlerResult` Pydantic BaseModel: `agree_count: int`, `challenge_count: int`, `reject_count: int`, `archived_finding_ids: list[str]`, `audit_lines_written: int`.
  - Target ≤300 LOC.
- `tests/unit/test_critic_handler.py` — NEW — ≥12 behavioural tests:
  - AGREE verdict appends one line to `audit/critic.jsonl` with `"type":"agree"`;
  - AGREE marks finding.critic_status="AGREED" in findings.json;
  - AGREE does NOT touch pending_critiques;
  - CHALLENGE appends one line to `audit/critic.jsonl` with `"type":"challenge"` + `suggested_revision`;
  - CHALLENGE appends the verdict to `pending_critiques` (assert list grows by 1);
  - CHALLENGE marks finding.critic_status="CHALLENGED";
  - REJECT appends one line to `audit/critic.jsonl` with `"type":"reject"` + reason;
  - REJECT removes the finding from `findings.json`;
  - REJECT appends the finding to `findings.archived.json` with full provenance (original observation_id, interpretation_id, archival_reason, archived_at);
  - REJECT NEVER silently deletes — the archived file is the post-condition;
  - mixed-verdict batch (1 AGREE + 1 CHALLENGE + 1 REJECT) produces correct counts in `CriticHandlerResult`;
  - `audit/critic.jsonl` lines parse back via `json.loads` with all required fields.
- `tests/integration/test_critic_loop_closed.py` — NEW — 1 e2e scenario: stage 3 findings, fire the critic (via FunctionModel returning 1 AGREE / 1 CHALLENGE / 1 REJECT), call `handle_critic_verdicts`; assert `findings.json` has 2 entries (AGREE + CHALLENGE remain); `findings.archived.json` has 1 entry (REJECT); `pending_critiques` has 1 entry (the CHALLENGE); `audit/critic.jsonl` has 3 lines.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Verdict routing semantics (table — write into module docstring)

| Verdict | Audit JSONL emitted | findings.json mutation | findings.archived.json mutation | pending_critiques mutation |
|---|---|---|---|---|
| AGREE | `{type:"agree", finding_id, reason, ts}` | `critic_status="AGREED"` | (none) | (none) |
| CHALLENGE | `{type:"challenge", finding_id, reason, suggested_revision, missing_corroboration, ts}` | `critic_status="CHALLENGED"`, `critic_challenge_reason=reason` | (none) | `append(verdict)` |
| REJECT | `{type:"reject", finding_id, reason, ts}` | finding REMOVED | finding APPENDED with `status="ARCHIVED"`, `critic_status="REJECTED"`, `archival_reason=reason`, `archived_at=now` | (none) |

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a CriticVerdict(finding_id="F-001", verdict="AGREE", reason="evidence supports interpretation")
When  handle_critic_verdicts(case_dir, examiner, [verdict], pending_critiques=[]) is called
Then  cases/<case>/audit/critic.jsonl gains exactly 1 line with "type":"agree"
And   findings.json entry for F-001 has critic_status="AGREED"
And   pending_critiques is unchanged (still empty)

Given a CriticVerdict(finding_id="F-002", verdict="CHALLENGE", reason="interpretation overstates evidence", suggested_revision="downgrade confidence to MEDIUM", missing_corroboration=["network/zeek pcap"])
When  handle_critic_verdicts(case_dir, examiner, [verdict], pending_critiques=[]) is called
Then  cases/<case>/audit/critic.jsonl gains exactly 1 line with "type":"challenge" and the suggested_revision present
And   findings.json entry for F-002 has critic_status="CHALLENGED" and critic_challenge_reason populated
And   pending_critiques has exactly 1 entry, equal to the input verdict

Given a CriticVerdict(finding_id="F-003", verdict="REJECT", reason="entity not in cited blobs")
And   findings.json contains the F-003 finding
When  handle_critic_verdicts(case_dir, examiner, [verdict], pending_critiques=[]) is called
Then  cases/<case>/audit/critic.jsonl gains exactly 1 line with "type":"reject"
And   findings.json no longer contains F-003
And   findings.archived.json contains F-003 with status="ARCHIVED" and critic_status="REJECTED" and archival_reason equal to the verdict.reason
And   the original finding fields (observation_id, interpretation_id, etc.) are preserved on the archived record

Given a REJECT verdict is processed
When  the audit/critic.jsonl line is inspected
Then  it carries finding_id, reason, and ts — the finding is NEVER silently deleted

Given a mixed-verdict batch of [AGREE F-001, CHALLENGE F-002, REJECT F-003]
When  handle_critic_verdicts is called once with all three
Then  the returned CriticHandlerResult is agree_count=1, challenge_count=1, reject_count=1, archived_finding_ids=["F-003"], audit_lines_written=3

Given the audit/critic.jsonl file is appended to atomically
When  10 verdicts are processed concurrently from multiple threads
Then  audit/critic.jsonl contains exactly 10 well-formed lines (no interleaving)

Given findings.json and findings.archived.json are written atomically
When  the handler is interrupted mid-batch (simulated via injected exception after 2 of 3 verdicts)
Then  the files reflect a consistent state — no half-written records

Given a CHALLENGE verdict has been pushed to pending_critiques
When  the investigator's next agent.run consults ctx.deps.pending_critiques
Then  the challenge is visible and can be acted on (the investigator's prompt template per story-investigator-agent surfaces pending_critiques to the model)

Given tests/unit/test_critic_handler.py exists
When  `uv run pytest tests/unit/test_critic_handler.py -v` runs
Then  exit code is 0
And   ≥12 tests pass

Given tests/integration/test_critic_loop_closed.py exists
When  `uv run pytest tests/integration/test_critic_loop_closed.py -v` runs
Then  exit code is 0
```

---

## Shell verification

```bash
# Import smoke
uv run python -c "from silentwitness_agent.critic_handler import handle_critic_verdicts, CriticHandlerResult; print('ok')"

# Unit tests
uv run pytest tests/unit/test_critic_handler.py -v
# Must show ≥12 passing

# Integration (closed loop)
uv run pytest tests/integration/test_critic_loop_closed.py -v
# Must show 1 passing

# REJECT-never-deletes audit
uv run python -c "
import json, tempfile
from pathlib import Path
from silentwitness_common.types import CriticVerdict
from silentwitness_agent.critic_handler import handle_critic_verdicts
with tempfile.TemporaryDirectory() as d:
    case = Path(d)
    (case/'findings.json').write_text(json.dumps([{'id':'F-001','status':'DRAFT','observation_id':'O-001','interpretation_id':'I-001'}]))
    (case/'audit').mkdir()
    v = CriticVerdict(finding_id='F-001', verdict='REJECT', reason='hallucinated entity', suggested_revision=None, missing_corroboration=[])
    handle_critic_verdicts(case_dir=case, examiner='aj', verdicts=[v], pending_critiques=[])
    fjson = json.loads((case/'findings.json').read_text())
    assert not any(f['id']=='F-001' for f in fjson), 'F-001 should have been removed from findings.json'
    fa = json.loads((case/'findings.archived.json').read_text())
    assert any(f['id']=='F-001' and f['critic_status']=='REJECTED' for f in fa), 'F-001 must be in archived with REJECTED status'
    cjsonl = (case/'audit'/'critic.jsonl').read_text().strip().split('\n')
    assert len(cjsonl) == 1 and '\"type\":\"reject\"' in cjsonl[0], cjsonl
    print('REJECT-never-deletes OK')
"

# Coverage ≥85%
uv run coverage run -m pytest tests/unit/test_critic_handler.py tests/integration/test_critic_loop_closed.py
uv run coverage report --include="src/silentwitness_agent/critic_handler.py" --fail-under=85

# Strict typing + lint + file-size guard
uv run mypy --strict src/silentwitness_agent/critic_handler.py
uv run ruff check src/silentwitness_agent/critic_handler.py
uv run ruff format --check src/silentwitness_agent/critic_handler.py
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_agent/critic_handler.py
```

---

## Notes for coding agent

- Reference: architecture.md §5.5 verbatim:
  - "AGREE → mark the finding as critic-approved; no further action."
  - "CHALLENGE → return the verdict to the investigator with the reason and suggested_revision. The investigator may run additional tools to corroborate and re-stage the interpretation. Logged to audit/critic.jsonl."
  - "REJECT → auto-archive the finding to cases/<case_id>/findings.archived.json with the reason. The finding does not appear in the report. Logged to audit/critic.jsonl."
  - "The critic does **not** approve findings (only the examiner does, via HMAC ledger). It is an internal quality gate, not an authorization step."
- Reference: architecture.md §8.3 sequence diagram — the CHALLENGE → corroboration → re-stage interpretation flow. The handler's job is to push the CHALLENGE onto `pending_critiques`; the investigator's next-turn instructions (story-investigator-agent) surface it to the model; the model dispatches the appropriate specialist; the specialist returns corroborating evidence; the investigator calls `record_interpretation` again with revised confidence.
- Reference: architecture.md §5.4 — `Finding.status` mutations are DRAFT → REVIEWED → FINAL → ARCHIVED. The REJECT path sets ARCHIVED.
- Reference: PRD §2 row "4:00–4:30 Critic moment" — the verbatim demo example carries the CHALLENGE reason "interpretation requires intercepted-traffic evidence; only tool installation shown; downgrade confidence or corroborate via captured-pcap." This story's handler does NOT generate this reason — it just routes the CriticVerdict object the critic agent (story-critic-agent) produced. But the handler's audit JSONL line must preserve the reason verbatim so the demo's verify-link click-through resolves.
- The REJECT-never-silently-deletes commitment is architectural. The audit/critic.jsonl line is the durable record; the findings.archived.json is the readable archive. The two-channel approach is intentional: critic.jsonl is the audit trail; findings.archived.json is the queryable archive. Both are produced atomically.
- Atomic writes: `findings.json` and `findings.archived.json` are full-file documents (not JSONL). Use the atomic-rename pattern from story-atomic-io: write to `.tmp`, fsync, rename. The critic.jsonl uses the append-with-fsync pattern from story-audit-logger.
- `pending_critiques` is the shared mutable list from `InvestigatorDeps` (story-investigator-agent). The handler `.append()`s to it; the investigator reads it on the next turn via an instructions callback. The list is the bridge — no message queue, no broker, just shared state in the same Python process.
- Library docs to consult via Context7 BEFORE coding:
  - `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic"` topic `"BaseModel field mutation update model_copy"` — when archiving, we copy the finding with mutations (status=ARCHIVED, archival_reason=...); Pydantic v2's `model_copy(update={...})` is the idiomatic path.
- Vocabulary discipline: never "court-admissible," never "Ralph Wiggum Loop." Docstrings: "Routes critic verdicts: AGREE noop; CHALLENGE → investigator's pending list; REJECT → archive with audit log."
- Pitfall: thread safety on findings.json + findings.archived.json + critic.jsonl. Use a single `threading.Lock` shared across all three file writes; the architecture commits to "one finding mutation at a time" so a coarse lock is fine.
- Pitfall: the `pending_critiques` list is shared mutable state across coroutines. Python's GIL makes `list.append` atomic, but the investigator's read-then-clear pattern (story-investigator-agent) needs the same lock. Document this clearly in the docstring so the investigator-side reader uses the same lock.
- Pitfall: a CHALLENGE verdict that names a finding the investigator never staged (corrupt input) should NOT crash — log a structured error to critic.jsonl with `type:"skip"` and reason, and continue. The handler is defensive.
- LOC budget: ~300. If approaching 400, extract the three `_handle_*` functions to `critic_handler_routes.py`.
- After this story merges, Epic 10 is structurally complete: critic agent (separate fresh context) + trigger (interval-based) + handler (routes verdicts). The closed loop runs end-to-end in `silentwitness investigate` (Epic 12 CLI orchestrates the loop).
