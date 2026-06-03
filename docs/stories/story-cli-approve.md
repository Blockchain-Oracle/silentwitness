# Story — `silentwitness approve <case-id> <finding-id>` (password-gated HMAC ledger write via getpass)

**ID:** story-cli-approve
**Epic:** Epic 12 — CLI (Typer) + Claude Code drop-in config
**Depends on:** story-cli-init, story-approve-finding-tool, story-hmac-ledger, story-fastmcp-server-bootstrap
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As an** examiner who has just triaged a DRAFT finding via `silentwitness review` and decided to approve it
**I want to** run `silentwitness approve <case-id> <finding-id>`, see the finding block one more time, be prompted for my examiner password via `getpass.getpass()` (echo OFF, terminal restored on signal), and on correct password have the HMAC ledger entry sealed and the finding promoted to APPROVED — with three wrong attempts triggering exit 4 and no ledger entry
**So that** the audit-trail seal at ux-spec §2.4 holds (every approved finding carries a forgery-resistant HMAC over the substantive text; password is the HMAC key per BRAINSTORM §4 — caching defeats the threat model; the password is **never** printed, logged, or persisted) and so `silentwitness verify` can reconcile post-handoff (architecture §4.9 HMAC-signed approval ledger; PRD §8 row 5 Audit Trail Quality).

---

## File modification map

- `src/silentwitness_agent/cli.py` — UPDATE — add `@app.command("approve")` function. Signature: `def approve(case_id: str = typer.Argument(...), finding_id: str = typer.Argument(...), note: str | None = typer.Option(None, "--note"), ledger: Path | None = typer.Option(None, "--ledger"))`. Body delegates to `cli_commands.approve.run(...)`. (~20 LOC delta to cli.py.)
- `src/silentwitness_agent/cli_commands/approve.py` — NEW — owns: load the finding from `findings.json`; display the finding block (re-uses the `_render_finding_block` helper from story-cli-review — extract to `_finding_render.py` if needed); prompt for examiner password via `getpass.getpass("examiner password: ")` (echo OFF); call into `silentwitness_mcp.findings.approval.approve_finding(...)` (story-approve-finding-tool) with the password wrapped as `SecretStr`; on success print the green sealed-entry block per ux-spec §2.4; on wrong password print `[red]✗[/red] incorrect (N attempts remain)` and re-prompt; bail after 3 wrong attempts with exit 4; signal-safe — SIGINT during password prompt restores terminal echo and exits 130. (~140 LOC.)
- `src/silentwitness_agent/cli_commands/_finding_render.py` — NEW — pure function `render_finding_block(finding: Finding) -> RenderableType` used by both `review` (story-cli-review) and `approve`. (~50 LOC.) IF story-cli-review already extracted this, that story owns it; this story just imports.
- `tests/integration/test_cli_approve.py` — NEW — ≥12 BDD scenarios: correct password approves; wrong password once + correct password approves with a "2 attempts remain" warning shown; wrong password three times exits 4 with NO ledger entry; SIGINT during password prompt exits 130 + terminal echo restored; finding not found exits 1; case not found exits 1; missing CASE.yaml salt exits 2; ledger dir mode 0755 exits 2 with LEDGER_DIR_PERMISSIONS_WEAK; finding already APPROVED exits 1 with ALREADY_APPROVED; password is never echoed (verifiable by snooping stdout/stderr capture); password is never written to audit/cli.jsonl; on success, `findings.json` shows status=APPROVED and `/var/lib/silentwitness/verification/<case_id>.jsonl` gains one entry.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given case mr-evil-001 has a DRAFT finding F-mr-evil-001-001 with observation + interpretation
And   cases/mr-evil-001/CASE.yaml has a per-case salt
And   /var/lib/silentwitness/verification/ exists with mode 0700
When  `uv run silentwitness approve mr-evil-001 F-mr-evil-001-001` runs
And   the examiner enters the correct password at the getpass prompt
Then  exit code is 0
And   /var/lib/silentwitness/verification/mr-evil-001.jsonl gains exactly one new line
And   that line has {ts, item_id: "F-mr-evil-001-001", item_type: "finding", content_hash, hmac, examiner}
And   findings.json shows F-mr-evil-001-001.status == "APPROVED"
And   stdout matches ux-spec §2.4 sealed-entry block (lines 193–198)
And   the derived HMAC key was zeroed in process memory (verified via cli-approve story's note — story-approve-finding-tool's contract)

Given the examiner enters a wrong password on the first attempt
And   enters the correct password on the second attempt
When  the second attempt completes
Then  exit code is 0
And   stdout (or stderr) contains "[red]✗[/red] incorrect (2 attempts remain)"
And   the ledger gains exactly one entry (not two)

Given the examiner enters a wrong password three times in succession
When  the third wrong attempt is submitted
Then  exit code is 4
And   stderr contains "[red]✗[/red] incorrect (0 attempts remain)" or "approval denied"
And   /var/lib/silentwitness/verification/mr-evil-001.jsonl is unchanged (no new line)
And   findings.json shows F-mr-evil-001-001.status == "DRAFT" (unchanged)

Given the password prompt is shown
When  the examiner presses Ctrl-C
Then  exit code is 130
And   terminal echo is restored (verifiable by running `stty -a` after — `echo` flag set)
And   no ledger entry is appended
And   no audit/cli.jsonl entry mentions the password or any partial input

Given finding F-not-found does not exist in findings.json
When  `silentwitness approve mr-evil-001 F-not-found` runs
Then  exit code is 1
And   stderr contains "finding 'F-not-found' not found"
And   no password prompt is shown

Given case mr-evil-999 does not exist
When  `silentwitness approve mr-evil-999 F-001` runs
Then  exit code is 1
And   stderr contains "case 'mr-evil-999' not found"

Given cases/mr-evil-001/CASE.yaml is missing the salt field
When  the approve command runs
Then  exit code is 2
And   stderr contains "CASE_SALT_MISSING"

Given /var/lib/silentwitness/verification/ has mode 0755 (too loose)
When  the approve command runs
Then  exit code is 2
And   stderr contains "LEDGER_DIR_PERMISSIONS_WEAK"

Given F-mr-evil-001-001 is already status=APPROVED
When  the approve command runs a second time
Then  exit code is 1
And   stderr contains "ALREADY_APPROVED"
And   no new ledger entry

Given the password is entered correctly
When  the command completes and a tool captures stdout + stderr
Then  the captured text contains zero characters matching the entered password (case-insensitive substring search)
And   audit/cli.jsonl entry for tool="cli.approve" contains no password or password-derived fields

Given `--note "matches reg key HKLM\Software\Ethereal"` is passed
When  approval succeeds
Then  the ledger entry includes the note field (architecture §4.9 allows additional fields; appended to the JSONL entry)
And   findings.json's F-mr-evil-001-001.approval_note matches the input

Given tests/integration/test_cli_approve.py exists
When  `uv run pytest tests/integration/test_cli_approve.py -v` runs
Then  exit code is 0
And   ≥12 tests pass
```

---

## Shell verification

```bash
uv run pytest tests/integration/test_cli_approve.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥12

uv run mypy --strict src/silentwitness_agent/cli_commands/approve.py
uv run ruff check src/silentwitness_agent/cli_commands/approve.py

[ "$(wc -l < src/silentwitness_agent/cli_commands/approve.py)" -le 200 ]

# Exit code 4 on three wrong passwords
printf "wrong\nwrong\nwrong\n" | uv run silentwitness approve test-case F-001 ; [ "$?" = "4" ]

# Password never echoed (script utility captures terminal output)
script -q /tmp/approve-trace.log -c "printf 'mysecret\n' | uv run silentwitness approve test-case F-001" >/dev/null
! grep -q "mysecret" /tmp/approve-trace.log

# getpass is used (not `input()` — the password must not appear in stdin echo)
grep -q "getpass.getpass" src/silentwitness_agent/cli_commands/approve.py

# §14 no-mocks check
git diff main...HEAD -- 'src/silentwitness_agent/cli_commands/approve.py' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded)" | grep -v "test\|spec"
```

---

## Notes for coding agent

- Source of truth: ux-spec.md §2.4 (examiner approval flow — re-prompt every time / re-prompt up to 3 then exit 4 / Ctrl-C → exit 130 with no ledger entry / sealed-entry block at lines 193–198 verbatim including `ledger: /var/lib/silentwitness/verification/mr-evil-001.jsonl#14` and `hmac: sha256:b4e1...09cf  (PBKDF2-SHA256, 600,000 iter)`), Open Question §8 resolution **"re-prompt every time. The password IS the HMAC key (BRAINSTORM §4). Caching defeats the threat model. The friction is the point."** — do NOT add a `--password-cache` flag or any keyring integration; architecture.md §4.9 (HMAC key derivation PBKDF2-SHA256 600,000 iter / per-case salt from CASE.yaml / constant-time hmac.compare_digest / 0700 dir + 0600 file / zeroize derived key after); story-approve-finding-tool (the MCP tool this CLI command calls — owns the actual HMAC computation, ledger append, finding state transition).
- **Password handling is the load-bearing security boundary of this entire command.** The contract:
  1. Read via `getpass.getpass("examiner password: ")` — and ONLY `getpass.getpass`. NEVER `input()`. NEVER read from stdin in any other way.
  2. Pass to `approve_finding(ApproveInput(finding_id=..., password=SecretStr(pw)))` immediately. Discard the local `pw` variable after.
  3. Do NOT echo, log, write to audit, include in error messages, or pass to `subprocess` env. The Pydantic `SecretStr` wrapper logs `**********` on `repr`; rely on it.
  4. On SIGINT during the prompt, `getpass` raises `KeyboardInterrupt`. Catch it, restore terminal echo (`getpass` does this automatically on raise — verify with a test), emit no ledger entry, exit 130.
- The three-wrong-passwords flow:
  - Loop counter `attempts_remaining = 3`.
  - On wrong password: `console.print("[red]✗[/red] incorrect ({n} attempts remain)", style="bold")` to stderr. Decrement counter. Re-prompt.
  - On `attempts_remaining == 0`: print final `approval denied` line, emit audit/cli.jsonl entry with `tool="cli.approve.denied"`, exit 4.
  - On correct password: break out of loop, proceed to ledger write.
- The audit/cli.jsonl entry for the approve invocation MUST NOT contain the password, the derived key, or any partial password. Only: `tool`, `finding_id`, `case_id`, `examiner`, `outcome` (`approved` | `denied` | `error_<reason>`). Architecture §4.4 audit entry schema is the contract.
- Re-display the finding block BEFORE the password prompt (per ux-spec §2.4 step 2: "Display the finding (observation + interpretation + cited audit_ids + caveats + MITRE + confidence)"). Re-use the `_render_finding_block` helper from `cli_commands/_finding_render.py`.
- The sealed-entry sample output (ux-spec §2.4 verbatim, copy character-for-character):
  ```
  [green]✓[/green] F-mr-evil-001-001 APPROVED
         ledger:  /var/lib/silentwitness/verification/mr-evil-001.jsonl#14
         hmac:    sha256:b4e1...09cf  (PBKDF2-SHA256, 600,000 iter)
         report.md updated (atomic rename)
  ```
  The `#14` is the line number of the appended entry (1-indexed). The `b4e1...09cf` is the first-4 + last-4 hex chars of the full hmac. The `report.md updated` line means the report renderer was invoked to flip the finding's status; this story does NOT implement that — it's handled inside `approve_finding` (story-approve-finding-tool) which calls into Epic 11's report writer.
- `--note "<text>"` flag: free-text note attached to the ledger entry. Useful for the examiner to record context ("approved on advice of breach counsel"). Stored in the ledger entry's `note` field and in `findings.json:F-id.approval_note`.
- `--ledger <path>` flag: override the default ledger path `/var/lib/silentwitness/verification/<case_id>.jsonl`. Used by tests (with a tmp path) and by examiners who want the ledger on a different volume. Default behaviour is the architecture §4.9 path; only override on explicit flag.
- Context7 hints BEFORE coding:
  - Python stdlib `getpass.getpass` — confirm the signal-handler restoration behaviour on Ubuntu Noble.
  - `pydantic` topic "SecretStr serialization JSON dump" — confirm `SecretStr` does not leak in JSON output.
- Known pitfalls:
  1. `getpass.getpass` on some platforms falls back to stdin echo when no controlling TTY (e.g. piped input). Detect this via `sys.stdin.isatty()`. If False AND no test-injected env var is set → exit 2 with `[red]✗[/red] approve requires a TTY (use `silentwitness approve ... < /dev/tty`)`. This guards against accidental password-in-pipe situations. For tests, allow an env-var override `_SILENTWITNESS_TEST_PASSWORD` — but document this clearly as test-only, and gate it on a runtime check that the process is under pytest.
  2. `SecretStr.get_secret_value()` is called inside `approve_finding` (story-approve-finding-tool) — NOT inside this CLI command. The CLI just constructs the `SecretStr` and hands it off. Architecturally, the secret should only be unwrapped at the moment of PBKDF2 derivation.
  3. Wrong-password attempts MUST emit one audit/cli.jsonl entry each, with `outcome="error_INVALID_PASSWORD"`. This is a legitimate audit signal (repeated bad passwords could indicate an attempted attack); the JSONL must record the attempts even though they failed. Three failed attempts === three JSONL lines.
  4. The PBKDF2 derivation takes ~100ms per call (architecture §4.9 ADR-007 note). Three sequential wrong attempts is ~300ms wall time on top of network/I/O — acceptable but visible. Do NOT add artificial delays; the PBKDF2 is the brute-force defense.
  5. The `report.md updated (atomic rename)` line is printed ONLY if the report writer (Epic 11) actually ran. If Epic 11 is not yet merged and `approve_finding` cannot trigger a re-render, print `report.md update deferred (Epic 11 not installed)` with `[yellow]⚠[/yellow]`.
- Vocabulary discipline (PRD §14, ux-spec §9): never "court-admissible," "tamper-proof," "cryptographically guaranteed." Use "HMAC-sealed," "defensible audit trail," "verifiable approval." Match architecture §4.9 wording.
