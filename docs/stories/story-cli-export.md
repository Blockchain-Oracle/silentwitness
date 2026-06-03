# Story — `silentwitness export <case-id> [--pdf|--md]` (report path emit + WeasyPrint PDF render)

**ID:** story-cli-export
**Epic:** Epic 12 — CLI (Typer) + Claude Code drop-in config
**Depends on:** story-cli-init, story-report-pdf-export, story-report-writer
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As an** examiner finalizing a case for handoff to the client / breach-coach / insurance carrier
**I want to** run `silentwitness export <case-id>` and get the path to `cases/<case_id>/report.md` (default `--md`) OR run with `--pdf` to render `cases/<case_id>/report.pdf` via WeasyPrint and get that path
**So that** I can hand off the canonical deliverable without copy-pasting paths, and the PDF render goes through the single render module (Epic 11 `report/pdf.py`) so the verify-link superscript styling per ux-spec §5.4 is consistent (ux-spec §2.2 `export` invocation; architecture §3 `report/pdf.py` location, §5.4 report-as-state; PRD FR6 Markdown report with FOR508 sections + Appendix-Audit).

---

## File modification map

- `src/silentwitness_agent/cli.py` — UPDATE — add `@app.command("export")` function. Signature: `def export(case_id: str = typer.Argument(...), pdf: bool = typer.Option(False, "--pdf"), md: bool = typer.Option(False, "--md"), include_appendix_audit: bool = typer.Option(True, "--include-appendix-audit/--no-appendix-audit"), ioc_format: str = typer.Option("csv", "--ioc-format"), out: Path | None = typer.Option(None, "--out"))`. Body delegates to `cli_commands.export.run(...)`. (~20 LOC delta to cli.py.)
- `src/silentwitness_agent/cli_commands/export.py` — NEW — owns: mode resolution (`--pdf` wins; if neither `--pdf` nor `--md`, default is `--md`; if both → exit 1 with conflicting-flags error); for `--md`: verify `cases/<case_id>/report.md` exists, print its absolute path to stdout (clean line, parseable by shell `$(silentwitness export ...)`); for `--pdf`: call `silentwitness_agent.report.pdf.render_pdf(report_md_path, out_path)` (story-report-pdf-export), print the absolute output path on success; `--out` overrides the default `cases/<case_id>/report.pdf`; `--ioc-format` is passed through to the IOC sidecar generation (csv | stix | misp | openioc). (~110 LOC.)
- `tests/integration/test_cli_export.py` — NEW — ≥8 BDD scenarios: default `--md` mode prints the report.md path; `--pdf` mode renders the PDF and prints the output path; `--out /tmp/custom.pdf --pdf` overrides default location; both `--pdf` AND `--md` exits 1 conflicting-flags; case not found exits 1; missing `report.md` exits 2 with "report.md not generated; run investigate first"; WeasyPrint render error exits 2 with the error wording; `--ioc-format stix` triggers the STIX sidecar generation (verifiable by file presence).

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given case mr-evil-001 has a generated cases/mr-evil-001/report.md
When  `uv run silentwitness export mr-evil-001` runs (default mode — implicit --md)
Then  exit code is 0
And   stdout is a single clean line containing the absolute path to report.md
And   the path is parseable by shell: `path=$(silentwitness export mr-evil-001); test -f "$path"` succeeds

Given case mr-evil-001 has a generated report.md
When  `uv run silentwitness export mr-evil-001 --pdf` runs
Then  exit code is 0
And   cases/mr-evil-001/report.pdf exists
And   stdout is a single clean line containing the absolute path to report.pdf
And   the PDF is well-formed (verifiable via `file <path>` showing `PDF document`)

Given `--out /tmp/custom-report.pdf --pdf` is passed
When  the command runs
Then  exit code is 0
And   /tmp/custom-report.pdf exists
And   cases/mr-evil-001/report.pdf does NOT exist (custom out path used instead)

Given both --pdf AND --md are passed
When  the command runs
Then  exit code is 1
And   stderr contains "[red]✗[/red] --pdf and --md are mutually exclusive"

Given case mr-evil-001 has no report.md (just-initialized case, never investigated)
When  `silentwitness export mr-evil-001` runs
Then  exit code is 2
And   stderr contains "report.md not generated; run `silentwitness investigate` first"

Given the WeasyPrint render fails (test fixture: injects a broken CSS in the template)
When  `silentwitness export mr-evil-001 --pdf` runs
Then  exit code is 2
And   stderr contains "PDF render failed" with the underlying error wording

Given `--ioc-format stix` is passed
When  the command runs (with --pdf or --md)
Then  exit code is 0
And   cases/mr-evil-001/iocs.stix.json exists (STIX 2.1 sidecar)

Given case mr-evil-999 does not exist
When  `silentwitness export mr-evil-999` runs
Then  exit code is 1
And   stderr contains "case 'mr-evil-999' not found"

Given tests/integration/test_cli_export.py exists
When  `uv run pytest tests/integration/test_cli_export.py -v` runs
Then  exit code is 0
And   ≥8 tests pass
```

---

## Shell verification

```bash
uv run pytest tests/integration/test_cli_export.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥8

uv run mypy --strict src/silentwitness_agent/cli_commands/export.py
uv run ruff check src/silentwitness_agent/cli_commands/export.py

[ "$(wc -l < src/silentwitness_agent/cli_commands/export.py)" -le 140 ]

# Default mode prints a single line parseable by shell
path=$(uv run silentwitness export test-case)
[ -n "$path" ] && [ -f "$path" ]

# PDF mode produces a valid PDF
uv run silentwitness export test-case --pdf
file cases/test-case/report.pdf | grep -q "PDF document"

# Mutual-exclusion exits 1
uv run silentwitness export test-case --pdf --md ; [ "$?" = "1" ]
```

---

## Notes for coding agent

- Source of truth: architecture.md §3 (`src/silentwitness_agent/report/pdf.py` location — WeasyPrint render shim; covered by integration smoke per CICD_SPEC §8.1 exclusion), §5.4 (report-as-state; report.md is the canonical artifact; PDF is a render of report.md, NOT a separate source of truth), §5.4 inline verify-link rendering (`[verify:F-id/sift-...]` superscript styled `#5ba3d0` jumping to Appendix-Audit anchored on that audit_id); ux-spec.md §2.2 `export` flags (`--pdf`, `--md`, `--include-appendix-audit / --no-appendix-audit`, `--ioc-format <csv|stix|misp|openioc>`, `--out`), §5.4 WeasyPrint stylesheet (Source Serif Pro headings, JetBrains Mono evidence, single accent `#5ba3d0`, A4 portrait, page 1 = exec summary, case ID in header); FR6 (Markdown report with FOR508 sections + Gaps + Appendix-Audit); PRD §10 deliverables (the report is the artifact judges read).
- This is a **thin** CLI command. The hard work is in `silentwitness_agent.report.pdf.render_pdf(...)` (story-report-pdf-export, Epic 11) — this CLI just resolves paths, validates flags, and prints the result path. The CLI must not duplicate WeasyPrint logic.
- **Mode resolution** is the only non-trivial logic:
  - Both `--pdf` and `--md` → exit 1 (conflicting flags).
  - Only `--pdf` → render mode.
  - Only `--md` OR neither flag → emit path mode (default).
- Output path resolution:
  - `--md` mode: always `cases/<case_id>/report.md`. The `--out` flag is **ignored** in `--md` mode (no copy is made; the file at the canonical path is the deliverable). If `--out` is passed with `--md`, warn `[yellow]⚠[/yellow] --out ignored in --md mode`.
  - `--pdf` mode: default `cases/<case_id>/report.pdf`; `--out` overrides.
- Stdout discipline: in both modes, stdout is a **single clean line** containing the absolute path. NO color, NO prefix, NO trailing newline glyphs. This is so the path is shell-parseable: `path=$(silentwitness export mr-evil-001 --pdf)` should just work. Status messages (`[green]✓[/green] PDF rendered to ...`) go to **stderr**, not stdout. Per ux-spec §2.5: stdout stays clean for piping.
- The `--ioc-format` sidecar generation: triggered as a side effect during export regardless of `--pdf` / `--md`. Generates `cases/<case_id>/iocs.<fmt>` where `<fmt>` is the format extension (`csv`, `stix.json`, `misp.json`, `openioc.xml`). Implementation lives in `silentwitness_agent.report.ioc_export.export_iocs(...)` (out of scope for this story — assume it exists from Epic 11 / Epic 16; if not yet implemented, log a `[yellow]⚠[/yellow] IOC export not yet available` and continue). DO NOT block the export command on the IOC sidecar.
- The `--include-appendix-audit / --no-appendix-audit` toggle: the Appendix-Audit section of report.md may be excluded from the PDF render for trimmed deliverables (executive-only). The flag is passed through to `render_pdf(include_appendix_audit=...)`. Default is True (include).
- WeasyPrint dependency: `weasyprint` is in the `[project.optional-dependencies]` set per story-scaffold-uv-pyproject. If not installed, `import weasyprint` fails and `report/pdf.py:render_pdf` raises a clean `ImportError`. The CLI catches this and exits 2 with `[red]✗[/red] WeasyPrint not installed; install with: uv sync --extra pdf`.
- Context7 hints BEFORE coding:
  - `typer` topic "Option BoolOption true/false flag combo" — for the `--include-appendix-audit / --no-appendix-audit` toggle pattern.
  - `weasyprint` is consumed indirectly via `report/pdf.py`; the CLI itself does not need WeasyPrint context.
- Known pitfalls:
  1. `cases/<case_id>/report.md` may have a `content_hash` in the YAML frontmatter that the report renderer updates atomically. Do NOT re-write the file from this CLI command; just read it (or pass the path to `render_pdf`).
  2. `--md` mode does NOT regenerate `report.md`. If the user wants a fresh render, they run `silentwitness investigate ... --resume` or invoke the report writer directly. The export command is a path-emit + PDF-render only.
  3. Absolute path: use `case_dir.resolve(strict=True) / "report.md"` and then `.resolve()` again on the result. Print via `print(str(path))` (NOT `console.print`, which may add ANSI).
  4. The PDF render may take 2–5 seconds on a 14-finding case (WeasyPrint is not fast). Show a spinner via `rich.progress.Progress` ON stderr (NOT stdout). Suppress the spinner if `NO_COLOR=1` or non-TTY stdout.
- Vocabulary discipline: "render" the PDF, not "generate" or "create." The report.md is the canonical artifact; the PDF is a render of it. Per architecture §5.4 wording.
