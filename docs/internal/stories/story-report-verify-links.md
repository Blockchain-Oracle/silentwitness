# Story — Verify-link renderer (inline `[verify:F-id/audit_id]` resolver + validator)

**ID:** story-report-verify-links
**Epic:** Epic 11 — Report-as-state (Markdown + PDF)
**Depends on:** story-report-template, story-report-writer, story-audit-logger, story-common-types
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** ship `src/silentwitness_agent/report/verify_links.py` containing the `VerifyLinkRenderer` class — it scans Markdown bodies for inline `[verify:F-id/audit_id]` references, validates each referenced `audit_id` resolves in the case's `audit/*.jsonl` files, raises `BrokenVerifyLink` on any unresolved reference, and at PDF-export time expands each reference to a clickable hyperlink (relative href into the Appendix-Audit anchor for that `audit_id`) — leaving plain `[verify:...]` syntax intact for Markdown / terminal display
**So that** the demo's killer 4:50–5:00 moment — examiner clicks a `[verify:...]` link, the PDF jumps to the Appendix-Audit entry, the audit JSONL row + SHA256 + verbatim cited span renders — actually works, and the architectural invariant ("every claim in the report points to an audit entry") is enforced by a hard validator, not a hope (architecture.md §5.4 — inline verify references; ux-spec.md §5.3 — inline verify-link rendering, superscript `#5ba3d0` link styling, jumps to Appendix-Audit anchored on that audit_id; PRD §2 — 4:50–5:00 killer moment; PRD secondary metric — "% of report claims that resolve to a tool execution").

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `src/silentwitness_agent/report/verify_links.py` — NEW — `VerifyLinkRenderer` class. Methods: `extract(self, body: str) -> list[VerifyRef]` (regex-extracts every `[verify:F-NNN/sift-<slug>-<YYYYMMDD>-NNN]` match — returns `VerifyRef(finding_id, audit_id, span_start, span_end)` per match; uses anchored regex `\[verify:(F-\d{3,})/(sift-[a-z0-9]+-\d{8}-\d{3,})\]`); `validate(self, body: str, *, audit_dir: Path) -> ValidationReport` (calls `extract`, then for each `VerifyRef` checks that the `audit_id` appears in at least one line of `audit_dir/*.jsonl`; returns `ValidationReport(total_refs, resolved_refs, broken_refs)`; if any are broken, raises `BrokenVerifyLink` with the offending `audit_id` and the surrounding context); `expand_for_pdf(self, body: str, *, audit_dir: Path) -> str` (replaces each `[verify:F-id/audit_id]` with a Markdown link `[<sup>verify:F-id/audit_id</sup>](#audit-<audit_id>)` pointing at the Appendix-Audit anchor — the PDF anchor convention is `audit-<audit_id>`, matching what the appendix-audit composer emits; preserves leading whitespace and surrounding punctuation); `expand_for_markdown(self, body: str) -> str` (no-op — returns body unchanged; Markdown / terminal display keeps the plain `[verify:...]` syntax). Module-level `BrokenVerifyLink(Exception)` carries `audit_id: str`, `finding_id: str`, `context: str` (the ±40-char window around the broken ref). Module-level Pydantic models `VerifyRef(BaseModel)` and `ValidationReport(BaseModel)`. (~280 LOC.)
- `src/silentwitness_agent/report/audit_index.py` — NEW — `AuditIndex` lightweight helper class. Built once per validation pass via `AuditIndex.from_dir(audit_dir: Path) -> AuditIndex` — scans every `*.jsonl` under `audit_dir`, parses each line as JSON, and builds a `dict[str, AuditEntryRef]` keyed by `audit_id`. Method `contains(audit_id: str) -> bool`; method `lookup(audit_id: str) -> AuditEntryRef | None` (returns `(source_file, line_number, audit_id, tool, ts)`). Avoids re-reading audit files for every `VerifyRef`. (~140 LOC.)
- `tests/integration/test_report_verify_links.py` — NEW — ≥10 integration tests against synthetic case directories: `extract` finds 0 refs in body without any; `extract` finds 3 refs in a body with 3 inline `[verify:...]`; `extract` rejects malformed refs (`[verify:bogus]` does not match — invariant: malformed shapes are ignored, not silently included); `validate` returns `total_refs=N, resolved_refs=N, broken_refs=0` when all audit_ids exist in audit dir; `validate` raises `BrokenVerifyLink` when one audit_id is missing; `BrokenVerifyLink.audit_id` matches the offending ID; `BrokenVerifyLink.context` shows ±40 chars around the broken ref; `expand_for_pdf` produces a `[<sup>...</sup>](#audit-...)` Markdown link for every ref; `expand_for_pdf` leaves non-verify text unchanged; `expand_for_markdown` is a no-op (body identical).
- `tests/unit/test_audit_index.py` — NEW — 5 unit tests on `AuditIndex`: `from_dir` returns an empty index for empty dir; `from_dir` indexes one audit_id per JSONL line; `from_dir` handles multi-file scan (5 JSONL files × 10 lines each = 50 audit_ids indexed); `contains` returns True for indexed audit_id; `lookup` returns the source file + line number for the indexed audit_id.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a Markdown body containing 3 inline references "[verify:F-001/sift-aj-20260613-007]", "[verify:F-002/sift-aj-20260613-008]", "[verify:F-003/sift-aj-20260613-009]"
When  VerifyLinkRenderer.extract(body) is called
Then  the result is a list of 3 VerifyRef instances
And   each VerifyRef.finding_id matches the F-NNN portion
And   each VerifyRef.audit_id matches the sift-<slug>-<YYYYMMDD>-NNN portion

Given a Markdown body with 0 inline verify references
When  extract is called
Then  the result is an empty list

Given a malformed inline like "[verify:not-a-finding-id/bogus]"
When  extract is called
Then  the malformed line is NOT included in the result
And   no exception is raised

Given a finding cites audit_id sift-aj-20260613-007 that exists in audit/findings.jsonl
When  VerifyLinkRenderer.validate is called
Then  ValidationReport.total_refs == 1
And   ValidationReport.resolved_refs == 1
And   ValidationReport.broken_refs == 0

Given a finding cites audit_id sift-alice-20260602-007 that doesn't exist in the audit JSONL
When  VerifyLinkRenderer.validate is called
Then  it raises BrokenVerifyLink with the offending audit_id

Given BrokenVerifyLink is raised for audit_id sift-alice-20260602-007
When  the exception is caught and inspected
Then  exc.audit_id == "sift-alice-20260602-007"
And   exc.finding_id is the F-id that cited the broken ref
And   exc.context contains the ±40-char window around the broken ref

Given a Markdown body containing "[verify:F-001/sift-aj-20260613-007]"
When  expand_for_pdf is called with a valid audit_dir
Then  the output contains "[<sup>verify:F-001/sift-aj-20260613-007</sup>](#audit-sift-aj-20260613-007)"

Given expand_for_markdown is called on a body with verify refs
When  the output is inspected
Then  the body is identical to the input (no expansion)

Given AuditIndex.from_dir is called on an audit_dir with 5 JSONL files × 10 lines each
When  index.contains is called with any of the 50 indexed audit_ids
Then  the result is True
And   index.contains("sift-fake-99999999-999") returns False

Given tests/integration/test_report_verify_links.py and tests/unit/test_audit_index.py exist
When  `uv run pytest tests/integration/test_report_verify_links.py tests/unit/test_audit_index.py -v` runs
Then  exit code is 0
And   ≥15 tests pass (10 + 5)

Given the report module is in scope for coverage
When  `uv run coverage report --include="src/silentwitness_agent/report/verify_links.py,src/silentwitness_agent/report/audit_index.py"` runs
Then  the line coverage is ≥ 85%
```

---

## Shell verification

```bash
# Tests pass
uv run pytest tests/integration/test_report_verify_links.py tests/unit/test_audit_index.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥ 15

# Broken-link smoke
uv run python -c "
import tempfile, pathlib, json
from silentwitness_agent.report.verify_links import VerifyLinkRenderer, BrokenVerifyLink
with tempfile.TemporaryDirectory() as d:
    audit = pathlib.Path(d) / 'audit'
    audit.mkdir()
    (audit / 'findings.jsonl').write_text(json.dumps({'audit_id': 'sift-aj-20260613-007', 'tool': 'vol_pslist'}) + '\n')
    body = 'Real ref [verify:F-001/sift-aj-20260613-007]. Broken ref [verify:F-002/sift-alice-20260602-009].'
    r = VerifyLinkRenderer()
    try:
        r.validate(body, audit_dir=audit)
        print('FAIL: should have raised')
    except BrokenVerifyLink as e:
        assert e.audit_id == 'sift-alice-20260602-009'
        assert e.finding_id == 'F-002'
        print('broken-link smoke ok')
"

# Expand-for-PDF smoke
uv run python -c "
from silentwitness_agent.report.verify_links import VerifyLinkRenderer
body = 'PowerShell ran [verify:F-001/sift-aj-20260613-007].'
out = VerifyLinkRenderer().expand_for_pdf(body, audit_dir=None)
assert '<sup>verify:F-001/sift-aj-20260613-007</sup>' in out
assert '(#audit-sift-aj-20260613-007)' in out
print('expand-for-pdf smoke ok')
"

# Expand-for-Markdown is no-op
uv run python -c "
from silentwitness_agent.report.verify_links import VerifyLinkRenderer
body = 'PowerShell ran [verify:F-001/sift-aj-20260613-007].'
assert VerifyLinkRenderer().expand_for_markdown(body) == body
print('expand-for-markdown no-op smoke ok')
"

# Strict typing
uv run mypy --strict src/silentwitness_agent/report/verify_links.py src/silentwitness_agent/report/audit_index.py

# Lint clean
uv run ruff check src/silentwitness_agent/report/

# File-size guard
uv run python .pre-commit-hooks/file-size-guard.py \
    src/silentwitness_agent/report/verify_links.py \
    src/silentwitness_agent/report/audit_index.py
# Must exit 0 (both ≤400 LOC)

# Coverage on these files
uv run coverage run -m pytest tests/integration/test_report_verify_links.py tests/unit/test_audit_index.py
uv run coverage report \
    --include="src/silentwitness_agent/report/verify_links.py,src/silentwitness_agent/report/audit_index.py" \
    --fail-under=85

# §14 no-mocks check (source files only)
git diff main...HEAD -- 'src/silentwitness_agent/report/verify_links.py' 'src/silentwitness_agent/report/audit_index.py' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec"
# Must output nothing
```

---

## Notes for coding agent

- Source of truth: architecture.md §5.4 — verbatim: "Inline verify references. Each finding claim renders as Markdown text with bracketed verify links: `... PowerShell ran with `-EncodedCommand` flag [verify:F-001/sift-aj-20260613-042].` The verify link resolves at render-time."
- Source of truth: ux-spec.md §5.3 — verbatim: "In WeasyPrint PDF: `[verify:...]` renders as superscript link styled `#5ba3d0`, jumping to Appendix-Audit anchored on that `audit_id`. The audit entry shows the JSONL row, SHA256 of the cited tool output, and the verbatim cited span. PRD §2 (4:50–5:00) killer moment."
- Source of truth: PRD §2 4:50–5:00 — "Examiner clicks `[verify:F-014/sift-001-20260613-042]`. Side pane shows JSONL audit entry, SHA256-pinned full output, cited line range, entity-gate match list." The verify-link demo IS the killer moment. If this story ships broken, the demo loses its closing beat.
- The reference regex: `\[verify:(F-\d{3,})/(sift-[a-z0-9]+-\d{8}-\d{3,})\]` — `F-\d{3,}` allows 3 or more digits (per story-common-types, sequence ≥1000 uses the natural width); `sift-[a-z0-9]+` matches the slugged examiner (per `slug_examiner` in story-common-types — lowercased alphanumeric); `\d{8}` matches `YYYYMMDD`; `\d{3,}` matches the audit sequence. Use `re.finditer` so you get span positions for the ±40-char context window.
- The Appendix-Audit anchor convention: `audit-<audit_id>` (e.g., `#audit-sift-aj-20260613-007`). This must match what story-report-writer's `_compose_appendix_audit` emits — coordinate via a shared module-level constant `APPENDIX_ANCHOR_PREFIX = "audit-"` exposed from `report/__init__.py`. The writer composes appendix entries with this anchor; this renderer references them.
- PDF expansion shape: the WeasyPrint stylesheet (ux-spec §5.4) styles `<sup>` elements within `<a>` tags as the small `#5ba3d0` superscript link. The Markdown shape `[<sup>verify:F-001/sift-aj-20260613-007</sup>](#audit-sift-aj-20260613-007)` renders via mistune to `<a href="#audit-..."><sup>verify:...</sup></a>` which CSS then styles. Do NOT embed HTML directly — let mistune do the conversion. The `<sup>` inside the Markdown link-text is the one HTML allowance that mistune passes through.
- Markdown / terminal display: leave `[verify:F-id/audit_id]` plain. The reasoning: examiners reading the raw `report.md` in `less` / `vim` / `bat` see the canonical ID syntax and can `silentwitness verify-claim F-001/sift-aj-20260613-007` (architecture §5.4) to open the audit entry from CLI. Expanding to HTML in the Markdown source would break that workflow.
- `BrokenVerifyLink` is RAISED, not swallowed. The writer (story-report-writer) calls `validate` AFTER composing the body and BEFORE atomic-renaming. If a broken link is detected, the write is aborted — the prior `report.md` stands. The agent then sees the exception bubble up to the audit log and can self-correct (or surface to the examiner). This implements the "% of report claims that resolve to a tool execution" PRD secondary metric as a hard architectural invariant: NO broken `[verify:...]` link ever lands in a written `report.md`.
- `BrokenVerifyLink.context`: extract the ±40-char window around the broken ref (handling string boundaries). This gives the agent / examiner enough context to identify WHICH finding has the broken ref without dumping the whole body in the exception.
- `AuditIndex` is built fresh per validation pass — do not cache across calls. The audit JSONL files are append-only during an investigation; an index built mid-investigation may miss entries appended after construction. Per-call construction is fast enough (typical case: <100 JSONL files × <1000 lines each = sub-100ms scan).
- `AuditIndex.from_dir` iterates `audit_dir.glob("*.jsonl")` — does NOT recurse. The audit layout is flat (`audit/findings.jsonl`, `audit/memory.jsonl`, `audit/disk.jsonl`, etc. per architecture §4.4). If a JSONL file has malformed lines, log the line number to `audit/audit_index_errors.jsonl` and continue (do not crash the index build over a single bad line).
- Validate that every extracted `audit_id` exists in the index. If the audit_id format is well-formed but absent from the index, that's a broken link. If the format is malformed (does not match the regex), `extract` already filtered it out.
- Performance: for a report with N=50 findings × avg 3 verify-refs = 150 refs against an index of M=2000 audit entries, the validate pass is O(N) dict lookups (constant per lookup). Should complete in <10ms. No optimization needed.
- The `extract` regex is anchored with `\[` and `\]` literal brackets. Inside-bracket text that doesn't match the F-id/audit_id pattern is silently skipped. This is intentional — Markdown bodies may contain other bracketed text (e.g., `[citation:NIST]`); we only want `[verify:...]`.
- The `expand_for_pdf` regex MUST handle multiple refs per line + refs at line boundaries. Use `re.sub` with a callable replacement, NOT a multi-pass string replace. Pre-compile the regex at module load.
- Do not URL-encode the anchor — `audit_id` is already URL-safe (lowercase alphanumeric, digits, hyphens).
- Vocabulary discipline (PRD §14): no "court-admissible." If a docstring or error message needs defensibility language, use "defensible audit trail" or "survives cross-examination." For this story, the natural phrasing is around "broken verify link" / "unresolved audit reference" — neither carries the banned vocabulary.
- Coverage floor: 85% on `verify_links.py` + `audit_index.py`. The 15+ tests above cover the regex extraction, validation, error path, expansion, and the index. No edge cases excluded.
- Library docs to consult via Context7 BEFORE coding:
  - `python re finditer` stdlib (confirm 3.12 behavior for overlapping matches — none expected here).
  - For `mistune` HTML escaping in link-text with `<sup>` tags: `mcp__plugin_context7_context7__resolve-library-id libraryName="mistune"` then query topic "html escape inline link allow sup tag." If `mistune` strips the `<sup>`, fall back to emitting the raw HTML link directly (`<a href="..."><sup>...</sup></a>`) — but only as a documented fallback. Pure Markdown is preferred.
- DO NOT call WeasyPrint here — that's story-report-pdf-export. This story only produces the Markdown that the PDF exporter then renders.
- DO NOT modify `audit/*.jsonl` files. This module is read-only over the audit dir. The audit logger (story-audit-logger) is the sole writer.
- DO NOT auto-fix broken links by inserting a placeholder. Raise. The writer must NOT silently emit a report with a broken ref — that defeats the entire architectural guarantee.
