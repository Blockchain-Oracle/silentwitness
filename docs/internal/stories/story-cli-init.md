# Story — `silentwitness init <case-id>` (case skeleton + cli.py Typer scaffolding)

**ID:** story-cli-init
**Epic:** Epic 12 — CLI (Typer) + Claude Code drop-in config
**Depends on:** story-common-types, story-atomic-io, story-evidence-registry, story-hmac-ledger, story-audit-logger
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As an** IR consultant opening a new engagement on a SIFT 2026 VM
**I want to** run `silentwitness init <case-id>` and get a fully-prepared case directory at `cases/<case_id>/` with `audit/`, `evidence/`, `.tool-output/` subdirs plus an empty `evidence.json` manifest and a `report.md` with frontmatter only
**So that** every downstream command (`register-evidence`, `investigate`, `review`, `approve`, `verify`, `export`) has the skeleton it expects without ad-hoc `mkdir`s — and so the Typer app instance + shared CLI helpers (`_resolve_case_dir`, `_load_config`, global flags) are landed for the remaining 9 stories to extend (architecture §3 repo structure, §5.6 CLI verb grammar; ux-spec §2.2 `init` invocation + sample output; PRD FR1 stock-SIFT 2026 install).

---

## File modification map

- `src/silentwitness_agent/__init__.py` — NEW — exports `__version__` (read from `silentwitness_common.version`); empty package marker if absent.
- `src/silentwitness_agent/cli.py` — NEW — the Typer entry point + all shared CLI scaffolding the other 9 stories extend. Lands ≤120 LOC for this story (skeleton + `init`); the file ceiling is **400 LOC across all 10 commands** per architecture §3 + CICD_SPEC §6.1. Contents:
  - `app = typer.Typer(no_args_is_help=True, add_completion=False, rich_markup_mode="rich")` — top-level Typer app.
  - Global callback registering `--config-file PATH`, `--no-color`, `--quiet`, `--debug` (per ux-spec §2.6 precedence: defaults → `~/.silentwitnessrc.toml` → `./.silentwitnessrc.toml` → env vars → CLI flags — CLI wins).
  - Three shared helpers (private — leading underscore): `_resolve_case_dir(case_id: str, root: Path | None = None) -> Path` resolves `<root>/cases/<case_id>` (root defaults to `$SILENTWITNESS_CASES_DIR` or `Path.cwd()`); `_load_config(config_file: Path | None) -> SilentWitnessConfig` walks the precedence chain and returns a frozen Pydantic config; `_console(no_color: bool, quiet: bool) -> rich.console.Console` builds the console honouring `NO_COLOR`/`TERM=dumb`/`--no-color` (ux-spec §2.5 — three-prefix rule; stdout clean for piping; errors → stderr).
  - `@app.command("init")` function. Signature: `def init(case_id: str = typer.Argument(...), examiner: str = typer.Option(default_factory=lambda: os.environ.get("USER", "examiner"), "--examiner"), model: str | None = typer.Option(None, "--model"), force: bool = typer.Option(False, "--force"), no_mount: bool = typer.Option(False, "--no-mount", hidden=True))`.
  - `init` behaviour: resolves case dir; if exists and not `--force` → exit 1 with `[red]✗[/red] case '<id>' already exists` to stderr; else creates `audit/`, `evidence/`, `.tool-output/` subdirs (mode 0755); writes empty `evidence.json` via `write_json_atomic` (`{"records": [], "schema_version": 1}` per story-evidence-registry manifest shape); writes `report.md` with YAML frontmatter only (`case_id`, `examiner`, `created_at` UTC ISO-8601, `updated_at`, `status: DRAFT`, `content_hash: sha256:0`*placeholder*, `silentwitness_version`, `model_used`) per ux-spec §5.1; emits initial audit entry to `audit/cli.jsonl` via `silentwitness_mcp.audit.logger.AuditLogger` with `tool="cli.init"`; prints the tree-shaped success message verbatim from ux-spec §2.2 sample output. Exit 0.
- `src/silentwitness_agent/config.py` — NEW — `SilentWitnessConfig` Pydantic model + `load_config(path: Path | None) -> SilentWitnessConfig` that merges TOML layers per ux-spec §2.6 precedence. Fields: `model: ModelConfig`, `budget: BudgetConfig`, `examiner: ExaminerConfig`, `hud: HudConfig`, `evidence: EvidenceConfig`, `output: OutputConfig`. All nested models `model_config = ConfigDict(frozen=True, extra="forbid")`. (~140 LOC.)
- `pyproject.toml` — UPDATE — add `[project.scripts]` entry `silentwitness = "silentwitness_agent.cli:app"` so `uv run silentwitness ...` and the installed entry point both resolve. (~3 LOC delta.)
- `tests/integration/test_cli_init.py` — NEW — ≥8 BDD scenarios via Typer's `CliRunner` (`typer.testing.CliRunner`): happy-path init creates all expected paths; idempotent re-init without `--force` exits 1; `--force` overwrites; `--examiner aj` lands in report frontmatter; `NO_COLOR=1` strips ANSI from output; missing parent (cases root unwritable) exits 2; `init` emits one entry to `audit/cli.jsonl` with `tool="cli.init"`; `--debug` flag dumps the resolved config to stderr.
- `tests/unit/test_cli_config.py` — NEW — ≥6 scenarios on `load_config`: defaults when no file; `~/.silentwitnessrc.toml` loaded; `./.silentwitnessrc.toml` overrides home; env vars override file; `--config-file` overrides env; precedence ordering tested with a hypothesis-style table.

The coding agent must NOT touch `silentwitness_mcp/` from this story.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a clean SIFT 2026 working directory under /tmp/silentwitness-work/
When  `uv run silentwitness init mr-evil-001` runs
Then  exit code is 0
And   /tmp/silentwitness-work/cases/mr-evil-001/ exists
And   subdirs audit/, evidence/, .tool-output/ exist (mode 0755)
And   cases/mr-evil-001/evidence.json contains exactly {"records": [], "schema_version": 1}
And   cases/mr-evil-001/report.md begins with "---\ncase_id: mr-evil-001\n"
And   cases/mr-evil-001/audit/cli.jsonl has exactly one line with tool="cli.init"
And   stdout matches the sample tree-shape from ux-spec §2.2

Given mr-evil-001 already exists from a prior init
When  `uv run silentwitness init mr-evil-001` runs again WITHOUT --force
Then  exit code is 1
And   stderr contains "case 'mr-evil-001' already exists"
And   stdout is empty

Given mr-evil-001 already exists
When  `uv run silentwitness init mr-evil-001 --force` runs
Then  exit code is 0
And   the case directory is re-initialised
And   audit/cli.jsonl gains a second cli.init entry

Given the env var $USER is unset
And   `--examiner aj` is passed
When  `uv run silentwitness init mr-evil-002 --examiner aj` runs
Then  exit code is 0
And   cases/mr-evil-002/report.md frontmatter contains "examiner: aj"

Given NO_COLOR=1 is set in the environment
When  `uv run silentwitness init mr-evil-003` runs
Then  exit code is 0
And   stdout contains zero ANSI escape sequences (grep -P '\x1b\[' returns nothing)
And   the three-prefix indicators degrade to plain `✓` `⚠` `✗` (per ux-spec §2.5)

Given the cases root is not writable (chmod 0555)
When  `uv run silentwitness init mr-evil-004` runs
Then  exit code is 2
And   stderr contains "system error" wording (per exit-code policy ux-spec §2.2)

Given ~/.silentwitnessrc.toml sets [model] default = "openai:gpt-5"
And   ./.silentwitnessrc.toml sets [model] default = "anthropic:claude-opus-4-7"
And   neither --model nor SILENTWITNESS_MODEL is set
When  the resolved config is dumped via `silentwitness init mr-evil-005 --debug`
Then  stderr contains `model.default = anthropic:claude-opus-4-7` (cwd file wins over home)

Given tests/integration/test_cli_init.py exists
When  `uv run pytest tests/integration/test_cli_init.py -v` runs
Then  exit code is 0
And   ≥8 tests pass

Given src/silentwitness_agent/cli.py exists
When  `wc -l src/silentwitness_agent/cli.py` runs
Then  the line count is ≤120 (skeleton-only budget for this story; full 10-command ceiling is 400)
```

---

## Shell verification

```bash
# Tests pass
uv run pytest tests/integration/test_cli_init.py tests/unit/test_cli_config.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥14 (8 + 6)

# Strict typing
uv run mypy --strict src/silentwitness_agent/cli.py src/silentwitness_agent/config.py

# Lint clean
uv run ruff check src/silentwitness_agent/

# File-size guard — this story leaves cli.py at ≤120 LOC; future stories must keep it ≤400 total
[ "$(wc -l < src/silentwitness_agent/cli.py)" -le 120 ] || { echo "cli.py over story-cli-init budget"; exit 1; }

# Entry point resolves
uv run silentwitness --help | grep -q "init"

# Coverage policy: cli.py is excluded from unit coverage per CICD_SPEC §8.1 ("stitches everything; covered by integration tests").
# config.py is standard 85% floor.
uv run coverage run --rcfile=pyproject.toml -m pytest tests/unit/test_cli_config.py tests/integration/test_cli_init.py
uv run coverage report --include="src/silentwitness_agent/config.py" --fail-under=85

# §14 no-mocks check
git diff main...HEAD -- 'src/silentwitness_agent/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded)" | grep -v "test\|spec"
# Must output nothing
```

---

## Notes for coding agent

- Source of truth: architecture.md §3 (`src/silentwitness_agent/cli.py` location), §5.6 (verb-noun command grammar — `silentwitness init`, `silentwitness investigate`, etc.); ux-spec.md §2.2 (the exact tree-shape success message, the `--examiner`, `--model`, `--force`, `--no-mount` flag set, exit-code semantics 0=ok/1=user-error/2=system/130=SIGINT), §2.5 (three-prefix rule + errors to stderr), §2.6 (config precedence + `~/.silentwitnessrc.toml` TOML shape — copy verbatim into the test fixtures); CICD_SPEC.md §8.1 (`cli.py` is **excluded from unit coverage** — covered by integration tests only; coverage_gate.py will not flag it).
- This story **lands the cli.py skeleton**. The other 9 stories extend `@app.command(...)` into the same module. Total budget across all 10 commands is **≤400 LOC** per architecture §3 file ceiling. If a single command's body grows past ~50 LOC, the implementing story should split into `src/silentwitness_agent/cli_commands/<command>.py` and have `cli.py` `from .cli_commands.investigate import investigate as _investigate; app.command()(_investigate)`. Document the split in the commit body per CICD_SPEC §14.
- Three-prefix rule (verbatim from ux-spec §2.5): only `[green]✓[/green]` (success), `[yellow]⚠[/yellow]` (warning), `[red]✗[/red]` (error). No other emoji anywhere in CLI output. Errors → stderr; stdout stays clean for piping.
- Use `rich.console.Console(file=sys.stderr)` for error console; the success console writes to stdout. Both honour `NO_COLOR=1` automatically when the env var is set (rich does this; do not override).
- The tree-shape ASCII for `init`'s success message MUST be the verbatim ux-spec §2.2 sample (lines 53–60). Do not paraphrase. Coding agent: copy it character-for-character.
- The Typer global callback: register `--config-file`, `--no-color`, `--quiet`, `--debug` at the app level (not per-command). Pass through to commands via `typer.Context`. Pattern:
  ```python
  @app.callback()
  def _root(
      ctx: typer.Context,
      config_file: Path | None = typer.Option(None, "--config-file", exists=True, dir_okay=False),
      no_color: bool = typer.Option(False, "--no-color"),
      quiet: bool = typer.Option(False, "--quiet"),
      debug: bool = typer.Option(False, "--debug"),
  ) -> None:
      ctx.obj = _build_ctx_obj(config_file, no_color, quiet, debug)
  ```
- Config precedence (ux-spec §2.6 verbatim, lowest → highest): defaults → `~/.silentwitnessrc.toml` → `./.silentwitnessrc.toml` → env vars (`SILENTWITNESS_*`) → CLI flags. CLI wins. Implement in `config.py:load_config()` as five layered dict merges, then `SilentWitnessConfig.model_validate(merged)`.
- `silentwitness_version` in the report frontmatter comes from `silentwitness_common.version.__version__` (set by python-semantic-release; see story-scaffold-uv-pyproject). At dev time the value is the dev tag.
- `--no-mount` is a hidden flag (`hidden=True` in Typer) used by tests to skip the `evidence/mount.py` validation (architecture §4.11). Default behaviour at init time **does not** invoke mount validation — that runs at `register-evidence` time. The flag exists for future commands to inherit; this story just declares it.
- The `audit/cli.jsonl` write reuses `silentwitness_mcp.audit.logger.AuditLogger` (story-audit-logger). Do NOT roll a new JSONL writer here. The `tool` field is `"cli.init"`; the `audit_id` is generated via `silentwitness_common.ids.make_audit_id(examiner_slug, today_utc, next_seq)`.
- Context7 hints BEFORE coding:
  - `typer` topic "callback global options Context" — Typer's `@app.callback` pattern for sharing state across commands.
  - `rich` topic "Console NO_COLOR isatty" — confirm rich's auto-degrade rules match what ux-spec §2.5 promises.
  - Python stdlib `tomllib` (3.11+) for reading the rc files — no third-party TOML parser needed.
- Known pitfalls:
  1. Typer's `rich_markup_mode="rich"` is required for `[green]...[/green]` literals in docstrings/help to render — but it does NOT auto-render in `print()` calls. Use `console.print("[green]✓[/green] ...")`, not `typer.echo(...)`.
  2. `Path.mkdir(parents=True, exist_ok=False)` is correct for the non-`--force` path; the `exist_ok=False` is what gives exit 1 on re-init without `--force`. The `--force` path needs `shutil.rmtree(case_dir)` first.
  3. `tomllib.load()` requires the file opened in binary mode (`"rb"`). Easy to miss; test will catch.
  4. Don't `import typer.testing.CliRunner` in production code — only in tests.
- Vocabulary discipline (PRD §14, ux-spec §9): never "court-admissible," "autonomous SOC," "find evil" in CLI output. The init success message lists facts ("case initialized at <path>") — no marketing copy.
