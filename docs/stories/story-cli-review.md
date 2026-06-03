# Story — `silentwitness review <case-id>` (DRAFT findings list + per-finding plain-print examiner prompt)

**ID:** story-cli-review
**Epic:** Epic 12 — CLI (Typer) + Claude Code drop-in config
**Depends on:** story-cli-init, story-cli-status, story-record-observation-tool, story-record-interpretation-tool
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As an** examiner who needs to triage staged findings before approving them for the report
**I want to** run `silentwitness review <case-id>` and either get a table of all DRAFT findings (no `--finding-id`) or step through a single finding's observation + interpretation + cited audit_ids + caveats + advisories with `[a]pprove [r]eject [m]odify [s]kip [q]uit` keystroke options
**So that** I can sequence through findings the way ux-spec §2.2 sample shows — plain print + prompt, no TUI, robust over `ssh -tt` on flaky hotel Wi-Fi — handing off approve/reject decisions to `silentwitness approve` (story-cli-approve) without ever exposing a write surface (ux-spec.md §2.2 `review` sample output verbatim, Open Question §8 resolution "v1 = plain print + prompt, no TUI"; architecture §5.4 report-as-state DRAFT/REVIEWED/APPROVED).

---

## File modification map

- `src/silentwitness_agent/cli.py` — UPDATE — add `@app.command("review")` function. Signature: `def review(case_id: str = typer.Argument(...), finding_id: str | None = typer.Option(None, "--finding-id", "-f"), status_filter: str = typer.Option("DRAFT", "--status"), non_interactive: bool = typer.Option(False, "--non-interactive"))`. Body delegates to `cli_commands.review.run(...)`. (~20 LOC delta to cli.py.)
- `src/silentwitness_agent/cli_commands/review.py` — NEW — two modes:
  - **List mode** (no `--finding-id`): reads `findings.json` filtered by `--status` (default DRAFT), renders a `rich.table.Table` with columns `id`, `staged_at`, `observation_snippet` (first 60 chars), `cited_audit_ids` (truncated), `confidence`. Sorted by `staged_at` ascending.
  - **Detail mode** (`--finding-id F-001`): renders the full finding block per ux-spec §2.2 sample (observation, interpretation, cited audit_ids, caveats, advisories, MITRE), then prompts with `[a]pprove  [r]eject  [m]odify  [s]kip  [q]uit  > `. Keystrokes:
    - `a` → exit 0 with a stdout hint "to approve: silentwitness approve <case-id> <finding-id>" (this story does NOT call approve_finding directly — that lives in story-cli-approve to keep the password-prompt surface single-source).
    - `r` → prompt for reason, call into `silentwitness_mcp.findings.reject_finding(...)` if available, OR write a REJECT marker to `findings.json`. Reject does NOT need a password; the citation/entity gate handles the hallucination floor (architecture §4.5 + §4.7).
    - `m` → opens `$EDITOR` with the observation + interpretation text; the edited text is staged for the next approve call (writes to `findings.json` updating the DRAFT entry). The HMAC will sign the **edited** text at approve time per ux-spec §2.4.
    - `s` → skip; advance to next finding if list mode was the entrypoint (in detail mode, exit 0).
    - `q` → exit 0 immediately, no state change.
  - `--non-interactive` skips the prompt and prints the finding block only (useful for `silentwitness review ... | less`).
  - ~180 LOC.
- `tests/integration/test_cli_review.py` — NEW — ≥10 BDD scenarios: list mode shows DRAFT findings only; `--status APPROVED` shows approved only; `--finding-id F-001` renders the full block matching ux-spec §2.2 sample; keystroke `q` exits 0 with no state change; keystroke `a` prints the approve-hint and exits 0; keystroke `s` advances or exits 0; keystroke `r` with a reason updates findings.json with REJECT; keystroke `m` invokes `$EDITOR` (test sets `EDITOR=true` so it returns immediately) and re-displays; missing finding-id exits 1; `--non-interactive` skips the prompt; corrupted `findings.json` exits 2.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given case mr-evil-001 has findings.json with 9 DRAFT findings
When  `uv run silentwitness review mr-evil-001` runs
Then  exit code is 0
And   stdout contains a rich.table with 9 rows
And   each row shows id, staged_at, observation_snippet (≤60 chars), cited audit_ids, confidence
And   findings are sorted by staged_at ascending

Given findings.json has 5 DRAFT + 2 APPROVED + 1 REJECTED
When  `silentwitness review mr-evil-001 --status APPROVED` runs
Then  exit code is 0
And   stdout shows exactly 2 rows (APPROVED-only)

Given findings.json contains F-mr-evil-001-001 with observation "Ethereal was present" + interpretation "wardriving" + cited [sift-001-20260602-014, sift-001-20260602-019] + caveats ["Installation alone..."]
When  `silentwitness review mr-evil-001 --finding-id F-mr-evil-001-001` runs in a TTY
Then  exit code is 0
And   stdout block matches ux-spec §2.2 sample shape (observation: / interpretation: / cited: / caveats: / mitre:)
And   stdout ends with the prompt "[a]pprove  [r]eject  [m]odify  [s]kip  [q]uit  > "

Given the prompt is shown and the examiner presses 'q'
When  the keystroke is received
Then  exit code is 0
And   findings.json is unchanged
And   stdout does NOT contain "to approve:" hint

Given the prompt is shown and the examiner presses 'a'
When  the keystroke is received
Then  exit code is 0
And   findings.json is unchanged (no state mutation in this command)
And   stdout contains "to approve: silentwitness approve mr-evil-001 F-mr-evil-001-001"

Given the prompt is shown and the examiner presses 'r' then types a reason "insufficient evidence"
When  the input is submitted
Then  exit code is 0
And   findings.json shows F-mr-evil-001-001.status == "REJECTED"
And   findings.json shows F-mr-evil-001-001.rejection_reason == "insufficient evidence"

Given the prompt is shown and the examiner presses 'm'
And   $EDITOR is set to `true` (no-op editor for the test)
When  the keystroke is received
Then  exit code is 0
And   findings.json shows the finding's modification_count incremented by 1
And   the original observation/interpretation text is preserved unless the editor wrote new content

Given --finding-id F-not-found is passed
When  the command runs
Then  exit code is 1
And   stderr contains "finding 'F-not-found' not found in case mr-evil-001"

Given --non-interactive is passed with --finding-id
When  the command runs
Then  exit code is 0
And   the finding block is printed
And   NO prompt appears
And   stdin is not read

Given findings.json is malformed JSON
When  the review command runs
Then  exit code is 2
And   stderr contains "findings.json parse error"

Given tests/integration/test_cli_review.py exists
When  `uv run pytest tests/integration/test_cli_review.py -v` runs
Then  exit code is 0
And   ≥10 tests pass
```

---

## Shell verification

```bash
uv run pytest tests/integration/test_cli_review.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥10

uv run mypy --strict src/silentwitness_agent/cli_commands/review.py
uv run ruff check src/silentwitness_agent/cli_commands/review.py

[ "$(wc -l < src/silentwitness_agent/cli_commands/review.py)" -le 250 ]

# 'q' keystroke exits 0 with no state change
echo "q" | uv run silentwitness review test-case --finding-id F-001 ; [ "$?" = "0" ]

# --non-interactive does not block on stdin
timeout 2 uv run silentwitness review test-case --finding-id F-001 --non-interactive < /dev/null ; [ "$?" = "0" ]
```

---

## Notes for coding agent

- Source of truth: ux-spec.md §2.2 `review` sample output (lines 102–117 — copy verbatim including the bracketed observation/interpretation strings, the `cited:` line shape `sift-001-20260602-014, sift-001-20260602-019`, the `caveats:` block, the `mitre: T1040 (Network Sniffing)` shape, the prompt line `[a]pprove  [r]eject  [m]odify  [s]kip  [q]uit  > `); ux-spec.md §8 Open Question resolution **"plain print+prompt, no TUI"** — do NOT use Textual or any other TUI framework; raw `input()` is the contract because it's robust over `ssh -tt` on flaky links.
- This command does **NOT** write to the HMAC ledger. Approve is a separate command (story-cli-approve) with the password prompt. The `[a]pprove` keystroke in `review` just hints at the next step; it never reads a password and never invokes `approve_finding`. This boundary is load-bearing: it keeps the password-prompt surface to a single function (`getpass.getpass`) in `cli-approve`, simplifying audit.
- `[r]eject` is benign — no password needed. The architectural defense against false-positive findings is the citation gate + entity gate (architecture §4.5 + §4.7); a manual reject just sets `findings.json:F-id.status = "REJECTED"` with a free-text reason. The reject path also emits one `audit/cli.jsonl` entry with `tool="cli.review.reject"`.
- `[m]odify` flow: open `$EDITOR` (env var; fallback to `/usr/bin/vi`, then `nano`) with a tempfile containing the observation + interpretation text formatted as YAML. On editor exit, parse the tempfile back, validate via Pydantic (`ObservationInput`, `InterpretationInput` — reuse the models from story-record-observation-tool / story-record-interpretation-tool), and update `findings.json` with `modification_count += 1`. If the editor exits non-zero, abort the modify with `[red]✗[/red] editor exited non-zero; modify aborted`.
- The list mode `rich.table.Table` columns (in this order): `ID`, `staged_at` (HH:MM:SS UTC), `confidence`, `observation_snippet`, `cited`. Default sort by `staged_at` ascending. Color the `confidence` column: HIGH → green, MEDIUM → yellow, LOW → dim. Per ux-spec §2.5 three-prefix rule, the table cells use color for the confidence column only (no other emoji).
- The detail-mode block format (ux-spec §2.2 verbatim):
  ```
  [1/9] F-mr-evil-001-001  staged 12:18:02Z
  ─────────────────────────────────────────
  observation: "C:\Program Files\Ethereal\ethereal.exe was present on
                Schardt's profile (MFT record dated 2004-08-19 22:48 UTC)."
  interpretation: "Ethereal (now Wireshark) is a packet-capture tool;
                   combined with promiscuous-mode capability this is
                   consistent with wardriving."
  cited:     sift-001-20260602-014, sift-001-20260602-019
  caveats:   "Tool installation alone does not prove use; corroborate
              via captured pcap or memory residue."
  mitre:     T1040 (Network Sniffing)

  [a]pprove  [r]eject  [m]odify  [s]kip  [q]uit  >
  ```
  The `[1/9]` prefix shows position within the current filtered list (only relevant when reviewing without `--finding-id`; in single-finding mode it's `[1/1]`).
- Use raw `input("[a]pprove  [r]eject  [m]odify  [s]kip  [q]uit  > ")` — NOT a rich prompt, NOT `getpass`. Plain stdin per the ux-spec §8 commitment. Strip + lowercase the input; accept first character; anything else re-prompts.
- `--non-interactive` mode: print the block, do NOT read stdin, exit 0. This is the `... | less` path. The test should pass `< /dev/null` to confirm no stdin read occurs.
- Filtering: `--status DRAFT` (default), `--status APPROVED`, `--status REJECTED`, `--status REVIEWED` per `FindingStatus` enum (story-common-types). Case-insensitive match.
- Context7 hints BEFORE coding:
  - `rich` topic "Table styling row color" — for the confidence column coloring.
  - `pydantic` topic "model_validate ObservationInput InterpretationInput" — reuse the input models from Epic 4 stories.
- Known pitfalls:
  1. Don't use `rich.prompt.Prompt.ask(...)` — it has a `\r`-mangling bug over flaky SSH (the precise pain ux-spec §8 cites). Plain `input()` is the contract.
  2. `$EDITOR` may be unset; the fallback chain MUST exist. Use `os.environ.get("EDITOR") or shutil.which("vi") or shutil.which("nano")`. If none found, error with `[red]✗[/red] no editor available; set $EDITOR`.
  3. `findings.json` updates MUST go through `silentwitness_common.atomic_io.write_json_atomic` (story-atomic-io). NEVER `json.dump` directly to the path. A crashed half-write leaves the case unrecoverable.
  4. The `[m]odify` path mutates the substantive text the HMAC will sign later. That's intentional per ux-spec §2.4: "the edited text is what gets signed." Document this in the modify-prompt copy: `(the edited text will be HMAC-signed at approve time)`.
- Vocabulary discipline: "staged" for DRAFT, "approved," "rejected." Never "confirm," "verified-by-examiner," "court-validated." Match architecture §5.4 status enum + ux-spec §2.5 banlist.
