# Story — `silentwitness install --claude-code` (namespaced drop-in for SIFT 2026 Claude Code v2.0.61)

**ID:** story-cli-install-claude-code
**Epic:** Epic 12 — CLI (Typer) + Claude Code drop-in config
**Depends on:** story-cli-init, story-fastmcp-server-bootstrap
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** judge on the SIFT 2026 VM who wants to demo SilentWitness via the pre-installed Claude Code v2.0.61 with zero pyproject editing
**I want to** run `silentwitness install --claude-code` and have the command (1) verify the Claude Code binary at `/usr/local/bin/claude` (per `context/.raw-design-research/03`), (2) copy `claude-code-config/CLAUDE.md` and `claude-code-config/settings.json` into `$HOME/.claude/silentwitness/` (namespaced so it does NOT clobber any existing global config), (3) verify the MCP server registration in the copied `settings.json`, and (4) refuse to overwrite an existing config that differs unless `--force` is passed
**So that** the zero-setup judge convenience PRD §10 promises is real and reproducible — and so the drop-in is namespaced under `silentwitness/` per architecture §6.3 ("namespaced under our project so it does not collide with any pre-existing Claude Code config") (architecture §6.1/6.2/6.3 Claude Code integration; ux-spec §2.2 `install --claude-code` flag; PRD FR1 stock SIFT 2026; FR8 Claude Code drop-in config; PRD §10 deliverables).

---

## File modification map

- `src/silentwitness_agent/cli.py` — UPDATE — add `@app.command("install")` function. Signature: `def install(claude_code: bool = typer.Option(False, "--claude-code"), cursor: bool = typer.Option(False, "--cursor"), continue_ide: bool = typer.Option(False, "--continue"), dry_run: bool = typer.Option(False, "--dry-run"), force: bool = typer.Option(False, "--force"))`. Body delegates to `cli_commands.install.run(...)`. (~20 LOC delta to cli.py.)
- `src/silentwitness_agent/cli_commands/install.py` — NEW — owns: (a) detect Claude Code binary via `shutil.which("claude")` AND verify path `/usr/local/bin/claude` exists (per `.raw-design-research/03`); refuse with exit 2 if neither found; (b) locate the source config bundle at `<repo_root>/claude-code-config/CLAUDE.md` + `<repo_root>/claude-code-config/settings.json`; (c) target dir `$HOME/.claude/silentwitness/` (namespaced — does NOT use `$HOME/.claude/` directly); (d) if target exists with differing content AND no `--force` → exit 1 with diff hint; (e) copy via atomic write (story-atomic-io); (f) verify the copied `settings.json` parses as JSONC and contains the `mcpServers.silentwitness` block with `type: "stdio"` and `command: "python"` + `args: ["-m", "silentwitness_mcp"]`; (g) print the install path + a "to use with Claude Code: cd into a SilentWitness case directory" hint. Cursor/Continue branches are stubbed (out of v1 scope per architecture §6 — Claude Code only). (~180 LOC.)
- `tests/integration/test_cli_install_claude_code.py` — NEW — ≥10 BDD scenarios: happy-path install with claude binary present copies both files to `$HOME/.claude/silentwitness/`; missing claude binary at `/usr/local/bin/claude` exits 2 with the path quoted; existing `$HOME/.claude/silentwitness/CLAUDE.md` with same content is idempotent (no error, no write); existing file with different content and NO `--force` exits 1 with diff hint; `--force` overwrites; `--dry-run` shows what would be copied without writing; copied `settings.json` parses as JSONC; copied `settings.json` contains `mcpServers.silentwitness` block; the deny list contains `Bash(silentwitness approve*)` per architecture §6.2; SIFT 2026 path `/usr/local/bin/claude` is cited verbatim in error wording.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given /usr/local/bin/claude exists (SIFT 2026 pre-installed Claude Code v2.0.61)
And   claude-code-config/CLAUDE.md and claude-code-config/settings.json exist in the repo
And   $HOME/.claude/silentwitness/ does NOT exist
When  `uv run silentwitness install --claude-code` runs
Then  exit code is 0
And   $HOME/.claude/silentwitness/CLAUDE.md exists with matching content
And   $HOME/.claude/silentwitness/settings.json exists with matching content
And   stdout contains "[green]✓[/green] installed to $HOME/.claude/silentwitness/"
And   stdout contains a "to use" hint mentioning Claude Code

Given /usr/local/bin/claude does NOT exist
And   shutil.which("claude") returns None
When  `silentwitness install --claude-code` runs
Then  exit code is 2
And   stderr contains "/usr/local/bin/claude" (the exact SIFT 2026 path)
And   stderr contains "Claude Code v2.0.61" or "not found" wording
And   no files are copied

Given $HOME/.claude/silentwitness/CLAUDE.md already exists with IDENTICAL content
When  the install command runs without --force
Then  exit code is 0
And   stdout contains "[yellow]⚠[/yellow] CLAUDE.md unchanged (already installed)"
And   no atomic-write occurs (mtime unchanged)

Given $HOME/.claude/silentwitness/CLAUDE.md already exists with DIFFERENT content
When  the install command runs without --force
Then  exit code is 1
And   stderr contains "[red]✗[/red] existing $HOME/.claude/silentwitness/CLAUDE.md differs"
And   stderr contains a hint "use --force to overwrite"
And   the existing file is NOT modified

Given $HOME/.claude/silentwitness/CLAUDE.md exists with different content
When  the install command runs WITH --force
Then  exit code is 0
And   the existing CLAUDE.md is overwritten with the repo version
And   a backup at $HOME/.claude/silentwitness/CLAUDE.md.bak.<ts> is created

Given `--dry-run` is passed
When  the install command runs
Then  exit code is 0
And   stdout lists the files that WOULD be copied (CLAUDE.md, settings.json)
And   $HOME/.claude/silentwitness/ is NOT created
And   no files are written

Given the install command completes successfully
When  the copied settings.json is parsed as JSON (after JSONC comment stripping)
Then  parsed.mcpServers.silentwitness.type == "stdio"
And   parsed.mcpServers.silentwitness.command == "python"
And   parsed.mcpServers.silentwitness.args == ["-m", "silentwitness_mcp"]

Given the install command completes successfully
When  the copied settings.json deny list is parsed
Then  the list contains "Bash(silentwitness approve*)"
And   the list contains "Edit(cases/*/audit/*.jsonl)"
And   the list contains "Edit(cases/*/evidence.json)"
And   the list contains "Edit(/var/lib/silentwitness/**)"
And   the deny list is a SUPERSET of the rules in architecture §6.2

Given `--cursor` or `--continue` is passed
When  the command runs
Then  exit code is 0 (no-op in v1)
And   stdout contains "[yellow]⚠[/yellow] --cursor / --continue not yet implemented; Claude Code only in v1"

Given the source claude-code-config/CLAUDE.md does NOT exist in the repo
When  the install command runs
Then  exit code is 2
And   stderr contains "claude-code-config/CLAUDE.md not found in repo (expected at <path>)"

Given tests/integration/test_cli_install_claude_code.py exists
When  `uv run pytest tests/integration/test_cli_install_claude_code.py -v` runs
Then  exit code is 0
And   ≥10 tests pass
```

---

## Shell verification

```bash
uv run pytest tests/integration/test_cli_install_claude_code.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥10

uv run mypy --strict src/silentwitness_agent/cli_commands/install.py
uv run ruff check src/silentwitness_agent/cli_commands/install.py

[ "$(wc -l < src/silentwitness_agent/cli_commands/install.py)" -le 220 ]

# /usr/local/bin/claude path is cited verbatim per .raw-design-research/03
grep -q "/usr/local/bin/claude" src/silentwitness_agent/cli_commands/install.py

# Namespaced target — never writes to bare $HOME/.claude/
! grep -E '"~/\.claude/[^s]' src/silentwitness_agent/cli_commands/install.py
grep -q '\.claude/silentwitness' src/silentwitness_agent/cli_commands/install.py

# Dry-run does not write
rm -rf $HOME/.claude/silentwitness
uv run silentwitness install --claude-code --dry-run
[ ! -d "$HOME/.claude/silentwitness" ]
```

---

## Notes for coding agent

- Source of truth: architecture.md §6.1 (CLAUDE.md system-prompt content — senior-analyst frame from §5.1 verbatim + Claude-Code-specific instructions: write outputs only into `cases/<case_id>/`, never edit deny patterns, prefer MCP over Bash); architecture.md §6.2 (settings.json verbatim — `mcpServers.silentwitness` stdio block, the full allow/deny list including `Bash(silentwitness approve*)`); architecture.md §6.3 (install.sh `--claude-code` flag behaviour — copies CLAUDE.md + settings.json to `$HOME/.claude/silentwitness/` namespaced, runs `claude mcp add silentwitness ...` for registration, idempotent, backed-up if pre-existing); `context/.raw-design-research/03-sift-2026-tool-catalog-verified.md` line 31 ("Claude Code CLI v2.0.61 pre-installed at /usr/local/bin/claude" — `packages/claude-code.sls:1–17`); ux-spec.md §2.2 `install --claude-code` invocation and flag set (`--claude-code`, `--cursor`, `--continue`, `--dry-run`, `--force`); FR8 Claude Code drop-in config.
- **The Claude Code path `/usr/local/bin/claude` is cited verbatim in error wording**, AS-IS. This is the SIFT 2026 contract. Hard-coded path check via `Path("/usr/local/bin/claude").exists()` AND a `shutil.which("claude")` cross-check; either must pass. Document the citation (`.raw-design-research/03 line 31`) in an inline comment.
- **Namespacing is load-bearing**: the target is `$HOME/.claude/silentwitness/`, NEVER `$HOME/.claude/` directly. This is the architecture §6.3 commitment to non-collision with any pre-existing user Claude Code config. The shell verification grep enforces this.
- The `claude-code-config/` source directory lives at the repo root (architecture §3 repo structure). Path resolution: walk up from `Path(__file__).resolve()` until a `pyproject.toml` is found; that's the repo root; then `<repo_root>/claude-code-config/`. If not found, exit 2 with the source-missing wording.
- Diff detection: compare content via `hashlib.sha256(file_bytes).hexdigest()` — if hashes match, idempotent (no write). If different and no `--force`, exit 1 with the diff-hint wording. Do NOT show the diff in stdout (could leak settings); just point at the path.
- `--force` overwrites BUT writes a backup at `<target>.bak.<unix_ts>` first. Backup is plain `shutil.copy2(target, backup)` BEFORE the atomic-write overwrites it.
- `--dry-run` short-circuits before any writes (including the dir creation). Print the list of files that would be copied + their destinations to stdout.
- JSONC parsing of settings.json: the file contains `//` comments per the architecture §6.2 example. Strip comments via a simple regex (`re.sub(r"//.*$", "", line, flags=re.MULTILINE)`) BEFORE `json.loads`. The verification step must confirm the parsed structure matches the expected shape (the BDD scenarios check `mcpServers.silentwitness.type`, etc.).
- The Cursor / Continue branches are stubs in v1. Architecture §6 documents Claude Code only; the ux-spec §2.2 lists the flags for future-proofing. Implementing them is out of scope; just print the `[yellow]⚠[/yellow]` "not yet implemented" message and exit 0 (NOT 1 — these are valid flags, just deferred features).
- `claude mcp add silentwitness ...` registration: architecture §6.3 mentions this. In v1 we copy the settings.json directly (which contains the `mcpServers.silentwitness` block) — that's the registration. The `claude mcp add` command-line invocation is an alternative path documented in the Claude Code docs (Context7: `mcp__plugin_context7_context7__query-docs` library `claude-code` topic "mcp add stdio command args" — confirm before relying on it). For v1, the settings.json copy is sufficient; if the user wants programmatic registration, they can run `claude mcp add silentwitness python -m silentwitness_mcp` themselves.
- Print the "to use" hint after success:
  ```
  to use with Claude Code:
    1. cd into a SilentWitness case directory: cd cases/<case-id>/
    2. launch Claude Code: claude
    3. Claude Code will pick up $HOME/.claude/silentwitness/settings.json
       and connect to the SilentWitness MCP server automatically.
  ```
- Context7 hints BEFORE coding:
  - `claude-code` (via context7) topic "settings.json mcpServers stdio deny allow" — confirm the JSONC schema matches our architecture §6.2 example.
  - `shutil` (stdlib) `which` + `copy2` — for binary detection and backup.
  - Python stdlib `re` for the JSONC comment strip (do NOT add `json5` or `commentjson` as a dep — overkill).
- Known pitfalls:
  1. `$HOME/.claude/` may not exist (Claude Code creates it lazily). `Path.mkdir(parents=True, exist_ok=True)` for the namespaced subdir; do NOT touch the parent dir's mode bits.
  2. The settings.json deny list MUST be a SUPERSET of architecture §6.2 — verify via the BDD test (`Bash(silentwitness approve*)`, `Edit(cases/*/audit/*.jsonl)`, etc.). Drift here is a security regression.
  3. Backup file timestamp: use `int(datetime.utcnow().timestamp())` for the suffix, NOT `time.time()` (the latter returns a float on some platforms — ugly filename).
  4. JSONC stripping is naive (`//` only, no `/* */`). If the source file uses block comments, the strip breaks. Architecture §6.2 example uses only `//` — keep the source file in that style. If a future change adds block comments, this code must be updated.
  5. `--cursor` and `--continue` print a warning, NOT an error, and exit 0. The flags are valid; the *feature* is deferred. Don't confuse the user.
- Vocabulary discipline (PRD §14): "drop-in" not "auto-install"; "namespaced" not "sandboxed." The §6.3 wording is "drop-in" — match it.
