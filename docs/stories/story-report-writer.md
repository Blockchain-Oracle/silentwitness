# Story — Report writer (atomic Markdown rendering, fires on every staged claim)

**ID:** story-report-writer
**Epic:** Epic 11 — Report-as-state (Markdown + PDF)
**Depends on:** story-report-template, story-atomic-io, story-approve-finding-tool, story-record-observation-tool, story-record-interpretation-tool, story-record-pivot-tool, story-audit-logger
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** ship `src/silentwitness_agent/report/writer.py` containing the `ReportWriter` class — it loads `cases/<case_id>/findings.json` + the active hypothesis stack, filters APPROVED-only findings for the body, composes each FOR508 section via `ReportTemplate` (from story-report-template), atomically writes `cases/<case_id>/report.md` via `atomic_writer` (from story-atomic-io), recomputes `content_hash` on every write, and fires automatically on every staged Observation / Interpretation / Pivot
**So that** the Markdown report at `cases/<case_id>/report.md` is the single source of truth, never partially written under crash, updated within ~one tick of any state change, and only ever surfaces APPROVED findings to the body — DRAFT findings live in `findings.json` until the examiner promotes them (architecture.md §5.4 — atomic-save invariant + report-as-state SoT; §8.1 sequence "report updated" hop; ux-spec.md §5 — the report is the deliverable judges read; PRD FR6 — "auto-saved by atomic rename on every staged Observation / Interpretation / Pivot, FOR508-shaped sections including Gaps + Appendix-Audit").

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `src/silentwitness_agent/report/writer.py` — NEW — `ReportWriter` class with constructor `__init__(self, case_dir: Path, *, examiner: str, model_used: str, silentwitness_version: str)`. Methods: `render(self) -> ReportRenderResult` (loads `findings.json`, partitions by status, composes the 9 sections, atomically writes `report.md`, returns a result envelope with `content_hash`, `bytes_written`, `sections_rendered`, `findings_approved_count`, `findings_draft_count`, `gaps_count`); `on_finding_event(self, event: FindingEvent) -> None` (subscriber callback — invoked by the hypothesis stack when an Observation / Interpretation / Pivot is staged or approved; debounces multiple events arriving within 50ms via a single `threading.Timer` reset; calls `render()`); private helpers `_compose_executive_summary(approved: list[Finding]) -> str` (extracts each approved finding's interpretation.text first sentence + the verify-link; ≤500-word ceiling enforced by truncation with `[...truncated]` marker per ux-spec §5.5); `_compose_engagement_overview(case_meta: CaseMeta) -> str`; `_compose_methodology(case_meta: CaseMeta, audit_entries: list[AuditEntry]) -> str` (lists tools used with versions per ux-spec §5.2 — populated from `data_provenance.tool` field of `AuditEntry`); `_compose_findings(approved: list[Finding]) -> str` (per-finding subsection: ID, title, severity, confidence, affected systems, description, supporting evidence with inline `[verify:F-id/audit_id]` references, MITRE ATT&CK mapping, recommended actions per ux-spec §5.2); `_compose_timeline(approved: list[Finding]) -> str` (chronological table — columns: timestamp, source, event, audit ref, finding ID per ux-spec §5.2); `_compose_iocs(approved: list[Finding]) -> str` (groups by IOC type — hashes / IPs / domains / regkeys / mutexes; cites observation audit_id that produced each); `_compose_recommendations() -> str` (returns auto-generated placeholder `"_To be populated by examiner._"` — agent does NOT write recommendations per architecture §5.4 finding #7); `_compose_gaps(case_state: CaseState) -> str` (lists `case_state.abandoned_hypotheses` + `case_state.exhausted_budgets` + any explicit gap entries; falls back to `"(no gaps identified)"` if empty per architecture §5.4); `_compose_appendix_audit(case_dir: Path) -> str` (auto-generated — agent does NOT write this; lists each `audit/*.jsonl` path + its SHA256 + the report body hash). Class-level Pydantic model `ReportRenderResult(BaseModel)` with frozen config. (~360 LOC; splits to `writer.py` + `compose.py` if it crosses.)
- `src/silentwitness_agent/report/events.py` — NEW — `FindingEvent(BaseModel)` model with `event_type: Literal["observation_staged", "interpretation_staged", "pivot_staged", "finding_approved", "finding_archived"]`, `finding_id: str`, `case_id: str`, `ts: datetime`. `ReportSubscriber(Protocol)` typing protocol the hypothesis-stack story (Epic 8) wires up — the writer satisfies it. (~80 LOC.)
- `tests/integration/test_report_writer.py` — NEW — ≥12 integration tests against a real `tmp_path` case directory: writer renders 9 sections in canonical order; APPROVED finding appears in Findings body; DRAFT finding does NOT appear in Findings body (only in the count footer); content_hash in frontmatter matches `compute_content_hash(body)`; atomic-rename behavior — kill-mid-write simulation leaves prior `report.md` intact; Recommendations section contains `"_To be populated by examiner._"` placeholder verbatim; Gaps section contains `"(no gaps identified)"` when no gaps registered; Gaps section lists each `abandoned_hypothesis` when present; Appendix-Audit lists every `audit/*.jsonl` path under the case dir with its SHA256; `on_finding_event` debounces — 5 events fired within 30ms triggers exactly 1 render; Executive Summary truncates at ≤500 words with `[...truncated]` marker; calling `render()` twice in a row with no state change produces identical `content_hash`.
- `tests/unit/test_report_writer_compose.py` — NEW — 8 unit tests on `_compose_*` helpers: `_compose_findings` emits inline `[verify:F-001/sift-aj-20260613-007]` references; `_compose_findings` handles the 0-finding case (returns `"_No findings approved yet._"`); `_compose_timeline` sorts by timestamp ascending; `_compose_iocs` groups IOCs by type; `_compose_iocs` deduplicates IOCs that appear in multiple findings; `_compose_executive_summary` ≤500 words; `_compose_methodology` lists each unique tool from `AuditEntry.data_provenance.tool`; `_compose_engagement_overview` includes the privilege statement placeholder per ux-spec §5.2.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a case directory with findings.json containing 3 APPROVED + 2 DRAFT findings
When  ReportWriter.render() is called
Then  cases/<case_id>/report.md exists
And   the Findings section contains exactly 3 finding subsections (one per APPROVED)
And   no DRAFT finding ID appears in the Findings section body
And   the frontmatter content_hash matches sha256 of the body bytes
And   the file mode is 0o644

Given ReportWriter.render() succeeds once with content_hash=H1
When  no state changes occur and render() is called again
Then  the second render produces content_hash=H1 (deterministic)
And   the file mtime advances (atomic-rename creates a new inode)

Given the writer is mid-render (between tmp write and rename) and the process is killed
When  the process restarts and reads cases/<case_id>/report.md
Then  the file contents are the PRIOR successful render (not the partial)
And   no cases/<case_id>/report.md.tmp.* artifact persists after restart-time cleanup

Given a finding F-001 cites audit_id sift-aj-20260613-007 in its observation
When  ReportWriter.render() composes the Findings section
Then  the rendered Markdown contains the literal string "[verify:F-001/sift-aj-20260613-007]"

Given the Recommendations section is composed
When  the rendered Markdown is inspected
Then  the section body is exactly "_To be populated by examiner._\n"
And   no agent-generated recommendation text appears

Given no gaps are registered in the case state
When  ReportWriter.render() composes the Gaps section
Then  the section body contains "(no gaps identified)"

Given the case state has 2 abandoned_hypotheses and 1 exhausted_budget item
When  ReportWriter.render() composes the Gaps section
Then  the section lists all 3 items as bullet points

Given the Appendix-Audit section is composed
When  the rendered Markdown is inspected
Then  every cases/<case_id>/audit/*.jsonl path is listed with its SHA256

Given the writer is subscribed to the hypothesis stack
When  5 FindingEvents arrive within 30ms
Then  ReportWriter._render_count increases by exactly 1
And   the final report reflects the state AFTER all 5 events

Given an Executive Summary composed from 12 approved findings with verbose interpretations
When  the section body word count is measured
Then  the count is ≤ 500
And   the section ends with "[...truncated]" if the natural composition would exceed 500 words

Given tests/integration/test_report_writer.py and tests/unit/test_report_writer_compose.py exist
When  `uv run pytest tests/integration/test_report_writer.py tests/unit/test_report_writer_compose.py -v` runs
Then  exit code is 0
And   ≥20 tests pass (12 + 8)

Given the report module is in scope for coverage
When  `uv run coverage report --include="src/silentwitness_agent/report/writer.py,src/silentwitness_agent/report/events.py"` runs
Then  the line coverage is ≥ 85%
```

---

## Shell verification

```bash
# Tests pass
uv run pytest tests/integration/test_report_writer.py tests/unit/test_report_writer_compose.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥ 20

# End-to-end smoke — synthetic 3-finding case
uv run python -c "
import tempfile, pathlib, json
from datetime import datetime, timezone
from silentwitness_agent.report.writer import ReportWriter
with tempfile.TemporaryDirectory() as d:
    case_dir = pathlib.Path(d) / 'cases' / 'hacking-case-001'
    (case_dir / 'audit').mkdir(parents=True)
    (case_dir / 'findings.json').write_text(json.dumps({'findings': []}))
    (case_dir / 'CASE.yaml').write_text('case_id: hacking-case-001\nexaminer: aj\n')
    w = ReportWriter(case_dir, examiner='aj', model_used='anthropic:claude-opus-4-7', silentwitness_version='1.0.0')
    result = w.render()
    rp = case_dir / 'report.md'
    text = rp.read_text()
    assert '## Executive Summary' in text
    assert '## Findings' in text
    assert '## Gaps' in text
    assert '## Appendix — Audit' in text
    assert '_To be populated by examiner._' in text
    assert '(no gaps identified)' in text
    print('writer smoke ok, content_hash=' + result.content_hash[:24] + '...')
"

# Strict typing
uv run mypy --strict src/silentwitness_agent/report/writer.py src/silentwitness_agent/report/events.py

# Lint clean
uv run ruff check src/silentwitness_agent/report/

# File-size guard
uv run python .pre-commit-hooks/file-size-guard.py \
    src/silentwitness_agent/report/writer.py \
    src/silentwitness_agent/report/events.py
# Must exit 0 (both ≤400 LOC)

# Coverage on these files
uv run coverage run -m pytest tests/integration/test_report_writer.py tests/unit/test_report_writer_compose.py
uv run coverage report \
    --include="src/silentwitness_agent/report/writer.py,src/silentwitness_agent/report/events.py" \
    --fail-under=85

# §14 no-mocks check (source files only)
git diff main...HEAD -- 'src/silentwitness_agent/report/' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec"
# Must output nothing

# Verify writer uses atomic_writer (not pathlib write_text)
grep -E "from silentwitness_common.atomic_io import|atomic_writer|write_text_atomic" src/silentwitness_agent/report/writer.py
# Must match at least one line
! grep -E "\.write_text\(" src/silentwitness_agent/report/writer.py
# Must output nothing (no non-atomic writes)
```

---

## Notes for coding agent

- Source of truth: architecture.md §5.4 — atomic-save pattern is non-negotiable (write to `report.md.tmp` → fsync(tmp) → os.replace → fsync(parent_dir)). DO NOT reimplement the atomic-rename — call `atomic_writer` from `silentwitness_common.atomic_io` (story-atomic-io). It already encodes the pattern.
- Source of truth: architecture.md §8.1 — sequence diagram shows the writer hop: observation staged → atomic rename `report.md.tmp → report.md`. The writer is the consumer of the hypothesis-stack event stream, not the producer.
- Source of truth: PRD FR6 — "auto-saved by atomic rename on every staged Observation / Interpretation / Pivot." This forces the subscriber pattern, NOT polling. The hypothesis stack (Epic 8) emits `FindingEvent` instances; this writer subscribes. The protocol is defined in `events.py`; the hypothesis stack imports `ReportSubscriber` from there.
- Source of truth: ux-spec.md §5.2 — section ordering is fixed; per-finding shape is fixed (ID, title, severity, confidence, affected systems, description, supporting evidence, MITRE ATT&CK, recommended actions). Match exactly.
- Source of truth: `context/user/09 §D.4` — failure mode #10 (tool output cut-and-paste). The writer MUST NOT inline tool output in the report body. Tool output lives in `audit/blobs/` referenced by `[verify:audit_id]` only. The Findings body cites; it does not quote.
- Source of truth: `context/user/09 §D.4` failure mode #5 (confidence overclaim) and #11 (inconsistent finding format). Mitigated by: (a) confidence is a required field rendered via the `Confidence` enum (LOW/MEDIUM/HIGH) — see story-common-types; (b) every finding goes through the same `_compose_findings` per-finding subsection template — no per-finding format drift possible.
- APPROVED-only invariant: the writer reads `findings.json`, partitions by `FindingStatus`, and ONLY renders `status == APPROVED` findings in the Findings section. DRAFT and REVIEWED findings appear in a summary count footer (`"_2 findings in DRAFT, 0 in REVIEWED._"`) but their content is not in the body. ARCHIVED findings are not mentioned. The HMAC ledger (story-hmac-ledger) is the source of APPROVED status — `findings.json` reflects what `approve_finding` (story-approve-finding-tool) has transitioned.
- Subscriber + debounce: the writer subscribes to the hypothesis-stack event bus. Use `threading.Timer(0.05, self._do_render)` reset-on-event pattern — every incoming `FindingEvent` cancels the prior timer and starts a fresh 50ms one. After 50ms of quiet, `_do_render` fires once. This means 5 events arriving within 30ms trigger exactly one render, not five. Use a `threading.Lock` to serialize `_do_render` calls so concurrent triggers don't race. Document this trade-off: in a crash window between event-stage and the 50ms tick, the staged event is captured in `findings.json` but the report won't reflect it until the next render. This is acceptable because `findings.json` is canonical state and the writer can re-render on resume.
- `content_hash` computation: hash the body bytes only (everything after the closing `---\n`), NOT including the frontmatter. `template.compute_content_hash` (story-report-template) does this. The writer composes the body, hashes it, fills the frontmatter `content_hash` field, then emits `dump_frontmatter(fm) + body`. Note: the frontmatter contains a hash of the body — so the *file* content is `frontmatter(hash=H) + body(hash=H)`. This is fine; the hash is over the body alone.
- `updated_at` semantics: set to `datetime.now(timezone.utc)` at every render. `created_at` is set once at the first render (when `report.md` does not exist) and preserved across subsequent renders by reading the existing frontmatter via `parse_frontmatter` before the new render.
- Section gating per architecture §5.4 + ux-spec §5.2:
  - **Executive Summary**: auto-composed from approved findings, ≤500 words. Acknowledged as senior-voice-written-last in practice (ux-spec §5.2); for v1 we auto-compose and the examiner edits before status flip to FINAL.
  - **Engagement Overview**: auto-composed from `CASE.yaml` metadata.
  - **Methodology**: auto-composed from `data_provenance.tool` field of each AuditEntry.
  - **Findings**: auto-composed, APPROVED-only.
  - **Timeline**: auto-composed from finding timestamps + audit_ids.
  - **IOCs**: auto-composed from `entity_gate` extracted entities per finding.
  - **Recommendations**: ALWAYS the placeholder `"_To be populated by examiner._"`. Agent does NOT write. (architecture §5.4 #7: "populated by the examiner, not the agent.")
  - **Gaps**: auto-composed from `case_state.abandoned_hypotheses + exhausted_budgets + explicit_gaps`. Falls back to `"(no gaps identified)"`. (architecture §5.4 #8: "mandatory; cannot be empty.")
  - **Appendix-Audit**: ALWAYS auto-generated. Lists `audit/*.jsonl` paths + their SHA256s + the body content_hash. Agent does NOT write.
- The writer is the SINGLE writer of `report.md`. Examiner edits during REVIEWED phase are handled by a separate path (out of scope this story): the examiner edits the file directly; on next render, the writer detects the body hash has diverged from frontmatter `content_hash` and either (a) merges or (b) preserves examiner edits with a `_local-edits.md` shadow file. Defer this to a follow-up story; current story renders only when state changes and assumes no concurrent examiner edits.
- IOC vocabulary: per ux-spec §5.2 — file hashes (MD5, SHA-1, SHA-256), IPs, domains, regkeys, file paths, mutex names, certificate fingerprints (JA3 / JA3S), user agent strings. Group by type. Each IOC line cites the observation audit_id that produced it (entity gate, story-entity-gate, tags each entity with its source audit_id).
- Executive Summary truncation: per ux-spec §5.5 / §D.2 ("1 page max"). Word count by `len(body.split())`. If natural composition exceeds 500 words, truncate at the last whole sentence boundary ≤500 words and append `"\n\n[...truncated — see Findings below.]"`.
- `_compose_appendix_audit` lists each audit JSONL path + SHA256. Use `hashlib.sha256` over the file bytes. Skip the report body hash here — the body hash is in the frontmatter, not the appendix.
- Recommendations placeholder is verbatim `"_To be populated by examiner._\n"` (with the trailing newline; italics via Markdown underscores). Tests assert the exact string — do not paraphrase.
- Gaps placeholder is verbatim `"(no gaps identified)"` (matches template story).
- File-size discipline: `writer.py` is at the high end of LOC budget. If it grows past 360 LOC at first cut, split `_compose_findings`, `_compose_timeline`, `_compose_iocs` into a sibling `compose.py` module and import. Document the split in the commit body per CICD_SPEC §14.
- Vocabulary discipline (PRD §14): no "court-admissible." If we ever need defensibility language in a section heading or placeholder, use "defensible audit trail" or "survives cross-examination." For this story, the only fixed phrases are `"_To be populated by examiner._"` and `"(no gaps identified)"` — neither carries the banned vocabulary.
- Coverage floor: 85% on `writer.py` + `events.py`. The 20+ tests cover the section-composition surface; debounce timing is tested via deterministic clock injection (pass a `time_source` callable to `__init__`, default `time.monotonic`).
- Library docs to consult via Context7 BEFORE coding:
  - `pydantic` topic `Protocol generic` (for `ReportSubscriber(Protocol)` declaration).
  - For `threading.Timer` debounce: stdlib only — no library doc needed. Confirm `Timer.cancel()` is safe to call after `start()` and after `finished` event in 3.12.
- DO NOT use `pathlib.Path.write_text` for `report.md` — only `atomic_writer` from story-atomic-io. The shell verification explicitly greps for `.write_text(` and asserts no match in writer.py.
- DO NOT write `recommendations` content beyond the placeholder. The writer is gated: even if the agent stages a `Pivot` or `Interpretation` that mentions remediation, it does NOT land in Recommendations. Recommendations is examiner-only territory.
- DO NOT subscribe to events during `__init__` — the constructor stays side-effect-free. Wire up subscription in a separate `subscribe(self, bus: EventBus) -> None` method. The CLI / agent loop (Epic 12 / Epic 8) calls `subscribe` after constructing the writer.
- DO NOT swallow exceptions in `_do_render`. If composition fails (e.g., malformed `findings.json`), let the exception propagate to the event bus's error handler. A silently-failing writer is a worse failure mode than a loud crash because the report stops updating while the agent thinks it succeeded.
