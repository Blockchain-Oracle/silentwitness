# Story — PDF export (WeasyPrint render with clickable verify-link anchors)

**ID:** story-report-pdf-export
**Epic:** Epic 11 — Report-as-state (Markdown + PDF)
**Depends on:** story-report-template, story-report-writer, story-report-verify-links, story-docker-baseline
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** ship `src/silentwitness_agent/report/pdf.py` containing the `PdfRenderer` class — it loads `cases/<case_id>/report.md`, parses frontmatter via `template.parse_frontmatter`, expands inline `[verify:F-id/audit_id]` references to clickable anchors via `VerifyLinkRenderer.expand_for_pdf` (story-report-verify-links), converts Markdown to HTML via `mistune`, applies the project WeasyPrint stylesheet (ux-spec.md §5.4 — Source Serif Pro headings, JetBrains Mono for evidence, accent `#5ba3d0`, A4 portrait), generates the title page from the frontmatter, and emits `cases/<case_id>/report.pdf` via WeasyPrint — wired to the CLI `silentwitness export --pdf` (Epic 12 / story-cli-export consumes this module)
**So that** the demo's 4:50–5:00 killer moment works end-to-end: examiner clicks a `[verify:F-014/sift-001-20260613-042]` link in the rendered PDF, the PDF jumps to the Appendix-Audit entry showing the JSONL row + SHA256 + verbatim cited span — proving the architectural guarantee to the judges in one click (architecture.md §5.4 — "PDF export. `silentwitness report --pdf cases/<case_id>/report.pdf` invokes WeasyPrint via `report/pdf.py`. The PDF is regenerated each call; it is **not** the source of truth."; ux-spec.md §5.4 — WeasyPrint stylesheet; PRD §2 — 4:50–5:00; Epic 11 DoD — "PDF passes WeasyPrint with no errors; clicking a `[verify:...]` link in the rendered PDF anchors to the Appendix-Audit entry").

---

## File modification map

Exact files the coding agent creates or modifies for this story:

- `src/silentwitness_agent/report/pdf.py` — NEW — `PdfRenderer` class with constructor `__init__(self, case_dir: Path, *, stylesheet_path: Path | None = None)`. Methods: `render(self, *, output_path: Path | None = None) -> PdfRenderResult` (loads `report.md`, calls `template.parse_frontmatter`, expands verify-links via `VerifyLinkRenderer.expand_for_pdf`, converts Markdown → HTML via `mistune.create_markdown(escape=False, plugins=["table", "url", "strikethrough"])`, prepends the title-page HTML composed from frontmatter, applies the stylesheet via `weasyprint.CSS`, renders to PDF via `weasyprint.HTML(string=html).write_pdf(output_path, stylesheets=[css])`, returns a result with `output_path`, `bytes_written`, `page_count`, `title_page_rendered`, `verify_links_expanded_count`); private helpers `_compose_title_page(fm: Frontmatter, case_id: str) -> str` (returns title-page HTML: case ID heading, examiner, dates, status pill, content_hash); `_load_stylesheet() -> str` (loads bundled stylesheet from `silentwitness_agent/report/assets/report.css` if `stylesheet_path` not provided); `_html_wrapper(title_page_html: str, body_html: str) -> str` (wraps everything in `<!DOCTYPE html><html><head>...<title>{case_id}</title></head><body>{title_page}{body}</body></html>`). Module-level Pydantic model `PdfRenderResult(BaseModel)`. (~280 LOC.)
- `src/silentwitness_agent/report/assets/report.css` — NEW — WeasyPrint stylesheet matching ux-spec §5.4: A4 portrait via `@page { size: A4 portrait; margin: 2cm 1.8cm 2cm 1.8cm; @bottom-right { content: counter(page) }; @top-left { content: string(case-id) } }`. Header font Source Serif Pro (loaded from bundled font file or system fallback `Georgia, serif`). Body font also Source Serif Pro. Monospace for evidence / IOCs JetBrains Mono (fallback `'Courier New', monospace`). Accent color `#5ba3d0` for verify-link `<sup>` elements: `a sup { color: #5ba3d0; font-size: 0.7em; vertical-align: super; text-decoration: none; }`. Status pill styling: `.status-pill.draft { background: #fef3c7; color: #92400e; }`, REVIEWED green, FINAL solid blue. Title page break: `.title-page { page-break-after: always; }`. Appendix-Audit page break: `#appendix-audit { page-break-before: always; }`. (~180 LOC of CSS.)
- `src/silentwitness_agent/report/assets/__init__.py` — NEW — Empty marker file so `importlib.resources` can locate the assets folder as a package (~5 LOC).
- `tests/integration/test_report_pdf_export.py` — NEW — ≥8 integration tests against a synthetic case directory: `render` produces a non-zero-byte `report.pdf` file; the PDF is valid (starts with `%PDF-1.` magic bytes); the PDF has ≥2 pages (title page + body); `verify_links_expanded_count` matches the number of `[verify:...]` refs in the source Markdown; calling `render` on a Markdown with a broken verify-link raises `BrokenVerifyLink` from `validate` BEFORE invoking WeasyPrint (no partial PDF emitted); title page contains the case_id text (extracted via `pypdf` text extraction); the rendered PDF contains the literal `verify:F-001/sift-aj-20260613-007` text in the body (via `pypdf` extraction); `render` honors the `output_path` kwarg; `render` falls back to `cases/<case_id>/report.pdf` when `output_path` is None.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

> Note: `src/silentwitness_agent/report/pdf.py` is **excluded from coverage** per CICD_SPEC §8.1 (line 788: "src/silentwitness_agent/report/pdf.py — (excluded) — WeasyPrint render shim; covered by integration smoke."). The integration tests above ARE the smoke. No unit test floor.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a synthetic case at cases/test-001/ with a complete report.md (frontmatter + 3 approved findings + 2 verify refs + a Gaps section)
And   all audit_ids referenced resolve in cases/test-001/audit/*.jsonl
When  PdfRenderer(case_dir).render() is called
Then  cases/test-001/report.pdf exists
And   the file starts with the bytes b"%PDF-1."
And   PdfRenderResult.bytes_written > 0
And   PdfRenderResult.verify_links_expanded_count == 2
And   PdfRenderResult.page_count >= 2

Given the source report.md contains one broken [verify:F-002/sift-fake-20260101-999] reference
When  PdfRenderer(case_dir).render() is called
Then  BrokenVerifyLink is raised
And   no report.pdf is written (the file does not exist OR retains its prior content)

Given the bundled stylesheet at silentwitness_agent/report/assets/report.css
When  PdfRenderer is constructed without a stylesheet_path kwarg
Then  _load_stylesheet returns the bundled CSS content

Given PdfRenderer.render is called with output_path=Path("/tmp/custom.pdf")
When  render completes
Then  /tmp/custom.pdf exists
And   cases/<case_id>/report.pdf is NOT modified (custom path overrides default)

Given the rendered PDF
When  pypdf extracts the text of page 1 (title page)
Then  the case_id appears in the extracted text
And   the examiner name appears in the extracted text
And   the status value appears in the extracted text

Given the rendered PDF body contains expanded verify-link superscripts
When  pypdf extracts the text of the body pages
Then  the literal "verify:F-001/sift-aj-20260613-007" string appears

Given tests/integration/test_report_pdf_export.py exists
When  `uv run pytest tests/integration/test_report_pdf_export.py -v` runs
Then  exit code is 0
And   ≥ 8 tests pass

Given pdf.py is excluded from coverage per CICD_SPEC §8.1
When  `uv run coverage report --include="src/silentwitness_agent/report/pdf.py"` runs
Then  the include match is empty (file is omitted)
```

---

## Shell verification

```bash
# Tests pass
uv run pytest tests/integration/test_report_pdf_export.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥ 8

# End-to-end smoke — produces a real PDF
uv run python -c "
import tempfile, pathlib, json
from datetime import datetime, timezone
from silentwitness_agent.report.writer import ReportWriter
from silentwitness_agent.report.pdf import PdfRenderer
with tempfile.TemporaryDirectory() as d:
    case_dir = pathlib.Path(d) / 'cases' / 'hacking-case-001'
    (case_dir / 'audit').mkdir(parents=True)
    (case_dir / 'findings.json').write_text(json.dumps({'findings': []}))
    (case_dir / 'CASE.yaml').write_text('case_id: hacking-case-001\nexaminer: aj\n')
    ReportWriter(case_dir, examiner='aj', model_used='anthropic:claude-opus-4-7', silentwitness_version='1.0.0').render()
    result = PdfRenderer(case_dir).render()
    pdf = case_dir / 'report.pdf'
    assert pdf.exists()
    assert pdf.read_bytes()[:7] == b'%PDF-1.'
    print(f'pdf smoke ok, bytes={result.bytes_written}, pages={result.page_count}')
"

# Strict typing
uv run mypy --strict src/silentwitness_agent/report/pdf.py

# Lint clean
uv run ruff check src/silentwitness_agent/report/pdf.py

# CSS file present + non-empty
test -s src/silentwitness_agent/report/assets/report.css

# Verify CSS contains the ux-spec §5.4 invariants
grep -q "A4" src/silentwitness_agent/report/assets/report.css
grep -q "portrait" src/silentwitness_agent/report/assets/report.css
grep -q "#5ba3d0" src/silentwitness_agent/report/assets/report.css
grep -qE "Source Serif|Georgia" src/silentwitness_agent/report/assets/report.css
grep -qE "JetBrains Mono|Courier" src/silentwitness_agent/report/assets/report.css

# File-size guard
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_agent/report/pdf.py
# Must exit 0 (≤400 LOC)

# Coverage check — pdf.py is OMITTED per CICD_SPEC §8.1
uv run coverage run -m pytest tests/integration/test_report_pdf_export.py
uv run coverage report 2>&1 | grep -E "report/pdf\.py" && { echo "ERROR: pdf.py should be excluded from coverage"; exit 1; } || echo "pdf.py correctly excluded"

# §14 no-mocks check (source files only)
git diff main...HEAD -- 'src/silentwitness_agent/report/pdf.py' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded|simulated)" | grep -v "test\|spec"
# Must output nothing

# WeasyPrint native deps must be available — sanity ping
uv run python -c "import weasyprint; print(f'weasyprint {weasyprint.__version__} ok')"
```

---

## Notes for coding agent

- Source of truth: architecture.md §5.4 — "PDF export. `silentwitness report --pdf cases/<case_id>/report.pdf` invokes WeasyPrint via `report/pdf.py`. The PDF is regenerated each call; it is **not** the source of truth." Critical: NEVER treat the PDF as authoritative state. Re-render on every call. The Markdown `report.md` is the SoT (story-report-writer).
- Source of truth: ux-spec.md §5.4 — verbatim stylesheet requirements: "Source Serif Pro headings (bundled), JetBrains Mono for evidence/IOCs (same as HUD), single accent `#5ba3d0`. A4 portrait. Page 1 = exec summary; case ID in header. Failure modes from §D.4 mitigated: Appendix-Audit paginated separately (avoids death-by-appendix); tool output lives in audit JSONL only, referenced by ID (no cut-and-paste); finding format enforced by Pydantic schema (no inconsistency); confidence is a required field rendered in a colored pill (no overclaim drift)."
- Source of truth: Epic 11 DoD (epics.md line 178) — "PDF passes WeasyPrint with no errors; clicking a `[verify:...]` link in the rendered PDF anchors to the Appendix-Audit entry showing JSONL row + SHA256 + verbatim span." The integration test for PDF anchor click-through is the hardest assertion to write — use `pypdf` to extract the link-annotation list and assert at least one points to an internal anchor matching `#audit-<audit_id>`.
- Source of truth: CICD_SPEC §8.1 line 788 — `src/silentwitness_agent/report/pdf.py` is EXCLUDED from coverage (rationale: "WeasyPrint render shim; covered by integration smoke"). This means: the file should be added to the `tool.coverage.run.omit` list in `pyproject.toml`. Do NOT chase 85% coverage on this file via unit tests. Integration tests above are the gate.
- Source of truth: story-docker-baseline — WeasyPrint native deps are pre-installed in the project Dockerfile. **Required apt packages for WeasyPrint 68.x on Debian bookworm / Ubuntu 24.04.2 Noble**: `pango1.0`, `harfbuzz`, `cairo`, `gdk-pixbuf2.0`, `libffi`, `fontconfig`, **`libharfbuzz-subset0`** (font-subsetting required by 68.x), **`libpangoft2-1.0-0`** (Pango/FreeType binding required by 68.x), and font packages (`fonts-source-serif-pro`, `fonts-jetbrains-mono` or equivalents in the chosen base image). On a fresh dev macOS, `brew install pango cairo gdk-pixbuf libffi harfbuzz` is required and documented in README. Do NOT bundle WeasyPrint native deps in this story; cite the docker baseline.
- WeasyPrint API contract (from Context7 query — confirm version-pinned API):
  - `weasyprint.HTML(string=html_text, base_url=case_dir).write_pdf(target=output_path, stylesheets=[weasyprint.CSS(string=css_text)])` — primary call.
  - **WeasyPrint pin: `weasyprint>=68.1,<70.0`** in `pyproject.toml`. The previous `>=60,<62` floor ships known CVE-2025-68616 (closed in 68.1). Pin to `>=68.1,<70.0` to inherit the fix and stay within a tested major. Matches `astral-sh/uv`'s 3.12 resolver.
  - Anchors: WeasyPrint honors `<a href="#anchor-name">` → jumps to the element with `id="anchor-name"`. The Appendix-Audit composer (story-report-writer) emits `<h3 id="audit-<audit_id>">` for each appendix entry; the verify-link renderer (story-report-verify-links) emits `<a href="#audit-<audit_id>">`. These must align — both stories use the `APPENDIX_ANCHOR_PREFIX = "audit-"` constant from `report/__init__.py`.
- mistune setup: `markdown = mistune.create_markdown(escape=False, plugins=["table", "url", "strikethrough"])`. `escape=False` is REQUIRED so the `<sup>` tags inside link text (from `VerifyLinkRenderer.expand_for_pdf`) pass through. The `table` plugin renders the Timeline section's table syntax. `url` auto-links bare URLs in IOCs. `strikethrough` is incidental but harmless.
- Title page composition: HTML emitted as one `<div class="title-page">` block before the body. Contents: `<h1>{case_id}</h1>`, `<p class="meta">Examiner: {examiner}</p>`, `<p class="meta">Created: {created_at}</p>`, `<p class="meta">Updated: {updated_at}</p>`, `<p class="meta">Model: {model_used}</p>`, `<p class="meta">SilentWitness {silentwitness_version}</p>`, `<span class="status-pill status-pill-{status_lower}">{status}</span>`, `<p class="content-hash"><code>{content_hash}</code></p>`. CSS `.title-page { page-break-after: always; }` ensures the body starts on page 2.
- The stylesheet font fallback chain: Source Serif Pro is referenced first; if WeasyPrint can't find it on the system, it falls back to `Georgia, 'Times New Roman', serif`. On SIFT 2026, install Source Serif Pro via `fonts-source-serif-pro` apt package (documented in README + Dockerfile). Do NOT bundle the .ttf in the assets folder (license + repo bloat); use system fonts only.
- `#5ba3d0` accent color: applied to `a sup` (verify-link superscripts), `h2` heading underline border-bottom, status pill REVIEWED background. Match the HUD color scheme exactly (ux-spec §3.5 design tokens — same accent for consistency).
- Failure mode mitigation per ux-spec §5.4:
  - **Death by appendix** → `#appendix-audit { page-break-before: always; }` puts the appendix on its own page block; readers can stop at the body.
  - **Tool output cut-and-paste** → enforced upstream by story-report-writer (tool output stays in `audit/blobs/`).
  - **Inconsistent finding format** → enforced upstream by the per-finding compose template.
  - **Confidence overclaim drift** → confidence is rendered in a colored pill: LOW=`#f3f4f6`/`#374151`, MEDIUM=`#fef3c7`/`#92400e`, HIGH=`#fee2e2`/`#991b1b`. The pill makes overclaim visually obvious.
- Validation before render: `PdfRenderer.render` calls `VerifyLinkRenderer.validate(body, audit_dir=case_dir / 'audit')` FIRST. If `BrokenVerifyLink` raises, the WeasyPrint call is skipped and the prior `report.pdf` (if any) is unchanged. The exception propagates to the CLI for surface. This enforces "no broken verify-link ever lands in a rendered PDF" — same architectural invariant as the writer.
- CLI integration (Epic 12 / story-cli-export — out of scope this story but referenced): `silentwitness export <case_id> --pdf [path]` calls `PdfRenderer(case_dir).render(output_path=path)`. The CLI is the only place that wires `--pdf`. This story's `PdfRenderer` is the engine; the CLI is the trigger.
- Reproducibility: WeasyPrint is deterministic for the same input HTML + CSS + font set. The PDF byte-content varies by WeasyPrint version + font version (timestamp metadata embeds the WeasyPrint version string). The architecture acknowledges this is fine because the PDF is regenerated each call.
- DO NOT use `reportlab`, `fpdf2`, or any other PDF library. ADR-005 (architecture §10) commits to WeasyPrint for the rationale: "Markdown with YAML frontmatter as the single source of truth at `cases/<case_id>/report.md`. PDF rendered via WeasyPrint at export time."
- DO NOT pass `base_url=None` to WeasyPrint — pass `base_url=str(case_dir)` so any future relative-image references (logos, attack diagrams) resolve to the case dir.
- DO NOT cache the rendered PDF. Every `render` call re-renders from `report.md`. The PDF is disposable; the Markdown is canonical.
- DO NOT modify `report.md` from this module. Read-only from the Markdown SoT.
- Vocabulary discipline (PRD §14): no "court-admissible." For exception messages or docstrings, use "defensible audit trail" or "survives cross-examination." The title page does not need any defensibility language.
- Pitfall: WeasyPrint logs go to stdout/stderr unless silenced. Wire a Python `logging.getLogger("weasyprint").setLevel(logging.ERROR)` at module load to suppress the page-rendering chatter — the CLI uses its own rich output for progress reporting, and WeasyPrint's debug noise would clobber it.
- Pitfall: WeasyPrint's first call after process start is slow (font cache warmup, ~2–3s on cold cache). Subsequent renders are sub-second. Document this in the module docstring; do NOT add a warmup hack.
- Library docs to consult via Context7 BEFORE coding:
  - `mcp__plugin_context7_context7__resolve-library-id libraryName="weasyprint"` then query topic "html to pdf with custom css internal anchors page breaks." Confirm the `write_pdf(target=...)` signature for v60.x and the `stylesheets=` parameter type.
  - `mcp__plugin_context7_context7__resolve-library-id libraryName="mistune"` then query topic "create_markdown plugins table escape false html passthrough."
  - For `pypdf` text extraction (test side): `mcp__plugin_context7_context7__resolve-library-id libraryName="pypdf"` then query topic "extract text from page link annotations." Used to validate the PDF in tests; install as a dev dep only.
- Estimate: 1.5h. The CSS file is the slow part (visual iteration on the title page + status pill); the Python is ~50 LOC of glue. The integration test for verify-link click-through resolution is the hardest assertion — budget 30min for it.
