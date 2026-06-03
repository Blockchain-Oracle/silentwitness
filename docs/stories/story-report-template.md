# Story — Report template (FOR508-shaped Markdown skeleton + YAML frontmatter)

**ID:** story-report-template
**Epic:** Epic 11 — Report-as-state (Markdown + PDF)
**Depends on:** story-common-types, story-scaffold-uv-pyproject
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** ship `src/silentwitness_agent/report/template.py` which defines the FOR508-shaped Markdown section template — YAML frontmatter (`case_id`, `examiner`, `status: DRAFT|REVIEWED|FINAL`, `content_hash`, `created_at`, `updated_at`, `silentwitness_version`, `model_used`), the 9-section ordered skeleton (Executive Summary → Engagement Overview → Methodology → Findings → Timeline → IOCs → Recommendations → Gaps → Appendix-Audit), per-section formatters that produce the canonical Markdown body, and stable section anchors the writer / verify-link renderer / PDF exporter all consume
**So that** every `cases/<case_id>/report.md` has a single source of truth for shape — the writer (story-report-writer) renders against this template, the verify-link renderer (story-report-verify-links) finds claims at known anchors, and the PDF exporter (story-report-pdf-export) styles known section headings (architecture.md §5.4 — `case_id` / `examiner` / `status` / `content_hash` / `created_at` / `updated_at` frontmatter; 9-section skeleton; `ux-spec.md` §5.1–5.2 — exact frontmatter sample + section list mapped 1:1 to `context/user/09 §D.2`).

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `src/silentwitness_agent/report/__init__.py` — NEW — Empty package init exporting `ReportTemplate`, `Frontmatter`, `ReportSection` re-exports for downstream sibling modules (~10 LOC).
- `src/silentwitness_agent/report/template.py` — NEW — Pure-Python (no Jinja) template module. Defines `Frontmatter(BaseModel)` Pydantic v2 model with fields `case_id: str`, `examiner: str`, `status: ReportStatus` (StrEnum `DRAFT|REVIEWED|FINAL`), `content_hash: str` (`sha256:<64 hex>` pattern validated by regex), `created_at: datetime` (UTC, tz-aware), `updated_at: datetime` (UTC, tz-aware), `silentwitness_version: str`, `model_used: str`. Exposes `dump_frontmatter(fm: Frontmatter) -> str` that emits the YAML frontmatter block wrapped in `---\n...\n---\n` (uses `yaml.safe_dump` with `sort_keys=False, default_flow_style=False`). Exposes `parse_frontmatter(md_text: str) -> tuple[Frontmatter, str]` returning `(frontmatter, body)` — splits on `^---\n` boundary, parses YAML with `yaml.safe_load`, validates via `Frontmatter.model_validate`. Defines `SECTION_ORDER: tuple[ReportSection, ...]` matching `Confidence`-style enum ordering exactly: `EXECUTIVE_SUMMARY, ENGAGEMENT_OVERVIEW, METHODOLOGY, FINDINGS, TIMELINE, IOCS, RECOMMENDATIONS, GAPS, APPENDIX_AUDIT` (reuses `ReportSection` from `silentwitness_common.types`). Defines `SECTION_HEADINGS: dict[ReportSection, str]` mapping enum → human heading (`"Executive Summary"`, `"Engagement Overview"`, etc.). Defines `SECTION_ANCHORS: dict[ReportSection, str]` mapping enum → Markdown anchor slug (`"executive-summary"`, `"appendix-audit"`, etc.) — used by verify-link renderer to compute hrefs. Defines `ReportTemplate` class with classmethods `render_skeleton(fm: Frontmatter, *, gaps_placeholder: str = "(no gaps identified)") -> str` (renders frontmatter + all 9 section headings with empty bodies; populates Gaps with the placeholder line so the section is never empty per architecture §5.4); `render_section(section: ReportSection, body: str) -> str` (returns `"## {heading}\n\n{body}\n"`); `compute_content_hash(body: str) -> str` (returns `"sha256:" + sha256(body.encode("utf-8")).hexdigest()`). Module-level constant `REPORT_SCHEMA_VERSION = "1.0.0"` documented in the docstring for forward-compat. (~280 LOC; splits to `template.py` + `frontmatter.py` if it crosses 400.)
- `tests/unit/test_report_template.py` — NEW — 12 behavioral tests: `dump_frontmatter` produces YAML wrapped in `---` fences; `dump_frontmatter` output is stable (sort_keys=False yields the architecture-§5.4 field order); `parse_frontmatter` round-trips with `dump_frontmatter` exactly; `parse_frontmatter` raises `pydantic.ValidationError` on malformed `content_hash` (not matching `^sha256:[a-f0-9]{64}$`); `parse_frontmatter` raises on missing `case_id`; `parse_frontmatter` rejects naive (tz-naive) `created_at`; `render_skeleton` produces a string containing all 9 SECTION_HEADINGS in order; `render_skeleton` Gaps section contains `"(no gaps identified)"` placeholder by default; `render_skeleton` Gaps section is overridable via the `gaps_placeholder` kwarg; `compute_content_hash` returns `sha256:` prefix + 64 hex; `compute_content_hash("")` is `"sha256:e3b0c442..."` (the empty-string SHA256); `SECTION_ORDER` length equals 9.
- `tests/unit/test_report_frontmatter_fixtures.py` — NEW — 4 fixture tests: the architecture.md §5.4 verbatim example parses; the ux-spec.md §5.1 verbatim example parses; `status` accepts all three of `DRAFT`, `REVIEWED`, `FINAL`; an unknown `status` value (e.g., `"SUBMITTED"`) is rejected.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Sample frontmatter (target shape for the coding agent)

Verbatim from architecture.md §5.4 + ux-spec.md §5.1 — both must round-trip:

```yaml
---
case_id: hacking-case-001
examiner: aj
status: DRAFT                              # DRAFT | REVIEWED | FINAL
content_hash: sha256:0000000000000000000000000000000000000000000000000000000000000000
created_at: 2026-06-13T14:27:03Z
updated_at: 2026-06-13T14:42:17Z
silentwitness_version: 1.0.0
model_used: anthropic:claude-opus-4-7
---
```

Sample rendered skeleton (output of `ReportTemplate.render_skeleton`):

```markdown
---
case_id: hacking-case-001
examiner: aj
status: DRAFT
content_hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
created_at: 2026-06-02T12:00:00Z
updated_at: 2026-06-02T12:00:00Z
silentwitness_version: 1.0.0
model_used: anthropic:claude-opus-4-7-1m
---

# Incident Report — Case hacking-case-001

## Executive Summary

## Engagement Overview

## Methodology

## Findings

## Timeline

## Indicators of Compromise

## Recommendations

## Gaps

(no gaps identified)

## Appendix — Audit
```

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a valid Frontmatter instance with case_id="hacking-case-001", examiner="aj", status=DRAFT
When  dump_frontmatter(fm) is called
Then  the return value starts with "---\n" and ends with "---\n"
And   the YAML block round-trips via parse_frontmatter to the same Frontmatter instance

Given a Markdown string with a malformed content_hash field (not matching ^sha256:[a-f0-9]{64}$)
When  parse_frontmatter is called
Then  pydantic.ValidationError is raised

Given a Markdown string whose frontmatter has a naive (tz-naive) created_at value
When  parse_frontmatter is called
Then  pydantic.ValidationError is raised
And   the error message mentions "timezone"

Given ReportTemplate.render_skeleton(fm) is called with a valid Frontmatter
When  the output is inspected
Then  it contains all 9 section headings ("## Executive Summary", ..., "## Appendix — Audit") in SECTION_ORDER
And   the Gaps section body contains "(no gaps identified)"

Given compute_content_hash(b"") is called
When  the value is checked
Then  the value is "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

Given the architecture.md §5.4 verbatim frontmatter sample
When  parse_frontmatter is called on it
Then  no exception is raised
And   the parsed status is ReportStatus.DRAFT

Given the ux-spec.md §5.1 verbatim frontmatter sample
When  parse_frontmatter is called on it
Then  no exception is raised
And   the parsed examiner is "sansforensics"

Given tests/unit/test_report_template.py and tests/unit/test_report_frontmatter_fixtures.py exist
When  `uv run pytest tests/unit/test_report_template.py tests/unit/test_report_frontmatter_fixtures.py -v` runs
Then  exit code is 0
And   16 tests pass (12 + 4)

Given the report module is in scope for coverage
When  `uv run coverage report --include="src/silentwitness_agent/report/template.py"` runs
Then  the line coverage on template.py is ≥ 85%
```

---

## Shell verification

```bash
# Import smoke
uv run python -c "
from silentwitness_agent.report.template import (
    Frontmatter, ReportTemplate, SECTION_ORDER, SECTION_HEADINGS,
    SECTION_ANCHORS, dump_frontmatter, parse_frontmatter,
)
assert len(SECTION_ORDER) == 9
print('template import ok')
"

# Round-trip smoke
uv run python -c "
from datetime import datetime, timezone
from silentwitness_agent.report.template import Frontmatter, dump_frontmatter, parse_frontmatter
fm = Frontmatter(
    case_id='hacking-case-001', examiner='aj', status='DRAFT',
    content_hash='sha256:' + 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    created_at=datetime(2026,6,13,14,27,3,tzinfo=timezone.utc),
    updated_at=datetime(2026,6,13,14,42,17,tzinfo=timezone.utc),
    silentwitness_version='1.0.0', model_used='anthropic:claude-opus-4-7',
)
md = dump_frontmatter(fm) + '\n# stub\n'
fm2, body = parse_frontmatter(md)
assert fm2 == fm
assert body.strip() == '# stub'
print('roundtrip ok')
"

# Unit tests
uv run pytest tests/unit/test_report_template.py tests/unit/test_report_frontmatter_fixtures.py -v
# Must show 16 passing (12 + 4)

# Strict typing
uv run mypy --strict src/silentwitness_agent/report/template.py

# Lint clean
uv run ruff check src/silentwitness_agent/report/

# Format clean
uv run ruff format --check src/silentwitness_agent/report/

# File-size guard
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_agent/report/template.py
# Must exit 0 (≤400 LOC)

# Coverage on this file
uv run coverage run -m pytest tests/unit/test_report_template.py tests/unit/test_report_frontmatter_fixtures.py
uv run coverage report --include="src/silentwitness_agent/report/template.py" --fail-under=85

# §14 no-mocks check (source files only)
git diff main...HEAD -- 'src/silentwitness_agent/report/template.py' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec"
# Must output nothing
```

---

## Notes for coding agent

- Source of truth: architecture.md §5.4 — verbatim YAML frontmatter block + the 9-section list. The field order in `dump_frontmatter` MUST match architecture §5.4 exactly: `case_id, examiner, status, content_hash, created_at, updated_at, silentwitness_version, model_used`. Use `yaml.safe_dump(..., sort_keys=False)` to lock the order — `pyyaml` defaults to alphabetical, which would scramble the example.
- Source of truth: ux-spec.md §5.2 — section ordering is fixed and mapped 1:1 to `context/user/09 §D.2` ("Report sections universal across templates"). The 9 sections come from the real IR templates surveyed there: Mandiant M-Trends, CrowdStrike OverWatch, SANS GIAC GCFA, Stroz Friedberg, NIST SP 800-61 Annex A, ENISA Good Practice, The DFIR Report, FIRST.org. Do NOT add a 10th section or reorder.
- Source of truth: `context/user/09 §D.4` — failure mode #9 ("Missing 'what we did not examine'"). The Gaps section MUST always render (placeholder `"(no gaps identified)"` allowed but the section heading is mandatory). Section #10 (raw-tool-output cut-and-paste) is mitigated by keeping tool output in the audit JSONL only, referenced by `[verify:...]` — the template does NOT include a `Raw Tool Output` section.
- `ReportSection` enum is already defined in `silentwitness_common.types` (story-common-types). Import it; do NOT redeclare. If the enum is missing the `APPENDIX_AUDIT` value at the time you start this story, that is a blocker — update the common-types story before proceeding.
- `ReportStatus` is the same shape as `FindingStatus` but distinct semantically — declare it locally as a StrEnum in `template.py` (only three values: `DRAFT`, `REVIEWED`, `FINAL`; finding's `ARCHIVED` does not apply to reports).
- The Appendix-Audit heading is rendered as `"## Appendix — Audit"` with a literal em-dash (U+2014), matching architecture §5.4 verbatim. The SECTION_ANCHORS slug for it is `"appendix-audit"` (ASCII hyphen) — this is what CommonMark slugifies the heading to and what GitHub-style heading anchors will use; verify-link renderer relies on this slug.
- `Frontmatter.content_hash`: validate via `Field(pattern=r"^sha256:[a-f0-9]{64}$")`. The writer story (story-report-writer) computes the hash; this story just enforces the format.
- `Frontmatter.created_at` and `updated_at`: tz-aware datetimes only. Use `AwareDatetime` from Pydantic v2 or a field validator that rejects `tzinfo is None`. Emit as ISO-8601 with `Z` suffix in YAML — `yaml.safe_dump` will serialize as a string per the custom representer; register one if needed.
- Pure-Python template (no Jinja2 dependency) — architecture.md §11 does not list Jinja in the runtime deps, and the template shape is fixed enough that f-string composition is clearer. Module-level constants for headings + a single `render_skeleton` function that joins them via `"\n\n".join`. The 400-LOC ceiling is comfortable.
- For the section body interpolation (used by story-report-writer): provide `render_section(section: ReportSection, body: str) -> str` that returns `f"## {SECTION_HEADINGS[section]}\n\n{body.rstrip()}\n"`. The writer composes the final report by concatenating sections in `SECTION_ORDER`.
- `compute_content_hash` operates on the *body* only (everything after the closing `---\n`), NOT including the frontmatter — otherwise the hash would change every time `updated_at` ticks, defeating the integrity check. Document this in the docstring.
- The empty-string SHA256 acceptance criterion (`sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`) is a stable canary — if `compute_content_hash(b"")` ever returns a different value, something has corrupted the hasher.
- Vocabulary discipline (PRD §14, ux-spec §9): no "court-admissible" — say "defensible audit trail" or "survives cross-examination" if needed. The template does not introduce either phrase; just don't add one.
- Coverage floor for this module: 85% (CICD_SPEC §8.1 — `src/silentwitness_agent/` standard). The 16 unit tests above should easily clear it.
- Library docs to consult via Context7 BEFORE coding:
  - `pyyaml` topic `safe_dump sort_keys representer` (the custom datetime representer for `Z` suffix).
  - `pydantic` topic `AwareDatetime field validator timezone` (rejecting naive datetimes in v2).
- DO NOT pull in `jinja2` — not in the runtime deps; pure-Python string composition only.
- DO NOT use `frontmatter` (the PyPI package). Manual split + `yaml.safe_load` is simpler and one fewer dep.
- **mistune pin (downstream invariant):** the PDF exporter (story-report-pdf-export) and any future Markdown renderer that consumes this template MUST pin `mistune>=3.2.1` (NOT the loose `mistune>=3` or `mistune>=3.0` floor). The 3.0.x–3.2.0 range admits six 2026 CVEs (CVE-2026-44708 XSS in math plugin, CVE-2026-44896 figure-directive injection, CVE-2026-44897 heading-ID injection, CVE-2026-44899 CSS injection, CVE-2026-33441 DoS, CVE-2026-33079 ReDoS) — all fixed in 3.2.1. This story does NOT import mistune (pure-Python frontmatter only); the pin lives in story-scaffold-uv-pyproject + story-report-pdf-export. Cited here so that any future template renderer added to this module inherits the floor.
- This story is the smallest in Epic 11; the writer / verify-links / PDF stories all depend on it. Finish first.
