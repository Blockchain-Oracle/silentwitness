# Story — `silentwitness verify <case-id>` (re-derive HMAC key + constant-time ledger reconciliation)

**ID:** story-cli-verify
**Epic:** Epic 12 — CLI (Typer) + Claude Code drop-in config
**Depends on:** story-cli-init, story-cli-approve, story-hmac-ledger, story-approve-finding-tool
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As an** examiner, breach-coach attorney, or judge post-handoff who wants to confirm the report's approved findings have not been tampered with
**I want to** run `silentwitness verify <case-id>`, be prompted for the examiner password via `getpass.getpass()`, have PBKDF2-SHA256 (600,000 iter) re-derive the HMAC key from the per-case salt, walk every entry in `/var/lib/silentwitness/verification/<case_id>.jsonl`, recompute the HMAC over the substantive text from `findings.json` and compare via `hmac.compare_digest` (constant-time), and report VERIFIED / DESCRIPTION_MISMATCH / VERIFICATION_NO_FINDING / APPROVED_NO_VERIFICATION per finding
**So that** the audit trail's post-handoff reconciliation contract from architecture §4.9 holds — any tamper produces a structured mismatch report, exit 0 only if all entries reconcile, exit 1 (or 3 with `--strict`) otherwise — and so the Valhuntir-style bidirectional reconciliation vocabulary is preserved (architecture §4.9 final paragraph; ux-spec §2.2 `verify` sample output).

---

## File modification map

- `src/silentwitness_agent/cli.py` — UPDATE — add `@app.command("verify")` function. Signature: `def verify(case_id: str = typer.Argument(...), ledger: Path | None = typer.Option(None, "--ledger"), strict: bool = typer.Option(False, "--strict"))`. Body delegates to `cli_commands.verify.run(...)`. (~20 LOC delta to cli.py.)
- `src/silentwitness_agent/cli_commands/verify.py` — NEW — owns: prompt for password via `getpass.getpass()`; load per-case salt from `cases/<case_id>/CASE.yaml`; derive HMAC key via `silentwitness_mcp.audit.ledger.HMACLedger.derive_key(password, salt, iterations=600_000)`; load `findings.json` + `/var/lib/silentwitness/verification/<case_id>.jsonl` (override via `--ledger`); for each ledger entry: load substantive text from the corresponding finding, recompute HMAC inputs per architecture §4.9 ("text + | + sorted(audit_ids).join(,)" for observation; observation_id + | + text + | + confidence.value for interpretation; finding = obs_hmac_input + \\x00 + interp_hmac_input), call `verify_hmac(key, message, expected_hex)` using `hmac.compare_digest`, classify the result; pretty-print a rich.table with one row per finding + outcome; emit summary line per ux-spec §2.2 sample ("[green]✓[/green] ledger intact — 14 entries verified"); zeroize the derived key in process memory before exit; exit 0 if all VERIFIED, exit 1 otherwise (exit 3 with `--strict` — verification rejection per ux-spec §2.2 exit code policy). (~180 LOC.)
- `tests/integration/test_cli_verify.py` — NEW — ≥11 BDD scenarios: all-VERIFIED case exits 0; tampered finding text (one byte mutated in findings.json) produces DESCRIPTION_MISMATCH and exit 1; tampered ledger HMAC field produces DESCRIPTION_MISMATCH; APPROVED finding with no ledger entry produces APPROVED_NO_VERIFICATION; ledger entry pointing to nonexistent finding produces VERIFICATION_NO_FINDING; wrong password fails all entries (all DESCRIPTION_MISMATCH) and exits 1; correct password verifies; `hmac.compare_digest` is called (verified by patching + assertion); derived key is zeroized after the run (memory-snapshot test); `--strict` exits 3 on any mismatch; case not found exits 1; ledger file not found (no approvals yet) exits 0 with "no entries to verify"; rich.table renders per-entry rows with outcome column.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given case mr-evil-001 has 14 ledger entries in /var/lib/silentwitness/verification/mr-evil-001.jsonl
And   findings.json has the corresponding 14 APPROVED findings with the same substantive text
And   the salt in CASE.yaml matches the salt used at approval time
When  `uv run silentwitness verify mr-evil-001` runs
And   the examiner enters the correct password at getpass
Then  exit code is 0
And   stdout contains "[green]✓[/green] ledger intact — 14 entries verified"
And   stdout contains "PBKDF2-SHA256, 600,000 iter"
And   stdout contains the time window first→last ledger entry timestamps
And   per-finding rich.table shows all 14 outcomes as VERIFIED

Given finding F-001 has been tampered (one byte flipped in observation text in findings.json)
When  verify runs with correct password
Then  exit code is 1 (default) or 3 (with --strict)
And   stdout shows F-001 outcome=DESCRIPTION_MISMATCH
And   stdout shows the other 13 findings as VERIFIED
And   the summary line uses [red]✗[/red] prefix

Given the ledger entry for F-002's HMAC field has been tampered (one hex digit changed)
When  verify runs
Then  exit code is 1
And   stdout shows F-002 outcome=DESCRIPTION_MISMATCH

Given F-003 has status=APPROVED in findings.json but NO corresponding ledger entry
When  verify runs
Then  exit code is 1
And   stdout shows F-003 outcome=APPROVED_NO_VERIFICATION

Given a ledger entry exists for F-999 but findings.json has no F-999
When  verify runs
Then  exit code is 1
And   stdout shows ledger-entry-for-F-999 outcome=VERIFICATION_NO_FINDING

Given the wrong password is entered
When  verify runs
Then  exit code is 1
And   ALL findings show DESCRIPTION_MISMATCH (wrong key derives wrong HMAC for every entry)
And   stdout WARNS about possible-wrong-password ([yellow]⚠[/yellow] all entries failed — re-check password)

Given `--strict` flag is passed AND any finding fails to verify
When  verify runs
Then  exit code is 3 (verification rejection per ux-spec §2.2 exit code policy)
And   stdout summary line says "verification REJECTED"

Given there are zero ledger entries (no approvals yet)
When  verify runs
Then  exit code is 0
And   stdout shows "[yellow]⚠[/yellow] no entries to verify (no findings approved yet)"

Given the verify run completes (success or failure)
When  the process memory is inspected (test harness uses ctypes mlock + memory snapshot)
Then  the derived HMAC key buffer is zeroed (all bytes 0x00)

Given grep -n "hmac.compare_digest" src/silentwitness_agent/cli_commands/verify.py
When  the grep runs
Then  at least one match is returned (constant-time compare is used, NOT `==`)

Given grep -nE 'hmac.*==' src/silentwitness_agent/cli_commands/verify.py | grep -v compare_digest
When  the grep runs
Then  zero matches are returned (no plain == on HMAC bytes anywhere)

Given case mr-evil-999 does not exist
When  `silentwitness verify mr-evil-999` runs
Then  exit code is 1
And   stderr contains "case 'mr-evil-999' not found"

Given tests/integration/test_cli_verify.py exists
When  `uv run pytest tests/integration/test_cli_verify.py -v` runs
Then  exit code is 0
And   ≥11 tests pass
```

---

## Shell verification

```bash
uv run pytest tests/integration/test_cli_verify.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥11

uv run mypy --strict src/silentwitness_agent/cli_commands/verify.py
uv run ruff check src/silentwitness_agent/cli_commands/verify.py

[ "$(wc -l < src/silentwitness_agent/cli_commands/verify.py)" -le 220 ]

# Constant-time compare is used
grep -q "hmac.compare_digest" src/silentwitness_agent/cli_commands/verify.py

# No plain == comparison on HMAC values anywhere
! grep -nE "hmac.*==" src/silentwitness_agent/cli_commands/verify.py | grep -v compare_digest

# PBKDF2 600K iteration count present (cite to architecture §4.9 / story-hmac-ledger)
grep -q "600_000\|600000" src/silentwitness_agent/cli_commands/verify.py || grep -q "600_000\|600000" src/silentwitness_mcp/audit/ledger.py
```

---

## Notes for coding agent

- Source of truth: architecture.md §4.9 (HMAC ledger semantics — "Verification. `silentwitness verify <case_id>` re-derives the key from the prompted password (no persistence; aborts on wrong password), recomputes HMAC for each ledger entry's substantive text (loaded from `findings.json` / `report.md`), and compares using `hmac.compare_digest` (constant-time — `context/competitive/11` §2 L2). Mismatches surface as `DESCRIPTION_MISMATCH`, missing ledger entries as `APPROVED_NO_VERIFICATION`, ledger-without-finding as `VERIFICATION_NO_FINDING`." — verbatim reconciliation vocabulary); ux-spec.md §2.2 `verify` sample output (lines 127–132 — copy verbatim: `[green]✓[/green] ledger intact — 14 entries verified` / `PBKDF2-SHA256, 600,000 iter` / `window: 2026-06-02T12:25:01Z → 13:48:30Z`); story-hmac-ledger (the `HMACLedger.verify_entry` method this command consumes — do NOT re-implement the HMAC compute or compare here; call the module).
- This command is the **post-handoff reconciliation surface**. It is what the breach-coach attorney runs to confirm the report's approved findings have not been tampered with. The Valhuntir-style three-outcome vocabulary (`DESCRIPTION_MISMATCH` / `APPROVED_NO_VERIFICATION` / `VERIFICATION_NO_FINDING`) is the load-bearing wording — judges familiar with the floor will recognize the shape. Do NOT invent alternative labels.
- Password prompt: same `getpass.getpass()` contract as story-cli-approve. Echo OFF. SIGINT during prompt → exit 130 + terminal restored. No password ever logged, echoed, or persisted.
- **Constant-time compare is non-negotiable.** Every HMAC comparison goes through `hmac.compare_digest(a, b)`. NEVER `a == b` on HMAC bytes. This is enforced by the shell-verification grep. Architecture §4.9 cites this as the Valhuntir L2 pattern.
- Key derivation: `HMACLedger.derive_key(password, salt, iterations=600_000)` — story-hmac-ledger owns this. Pass the password as bytes (PBKDF2 wants bytes); the derived key is a 32-byte `bytearray` (mutable for zeroize).
- Zeroize: after the full verify loop, overwrite the derived-key `bytearray` with zeros in-place: `for i in range(len(key)): key[i] = 0`. The `HMACLedger.zero_key(key_buf)` helper from story-hmac-ledger handles this. Call it in a `finally` block so it fires even on exception.
- The four outcomes (one per finding/ledger row):
  - `VERIFIED` — ledger entry exists, finding exists, HMAC matches (compare_digest True).
  - `DESCRIPTION_MISMATCH` — ledger entry exists, finding exists, HMAC does NOT match (substantive text has been altered OR wrong password OR HMAC field tampered).
  - `APPROVED_NO_VERIFICATION` — finding is APPROVED in findings.json but no ledger entry exists.
  - `VERIFICATION_NO_FINDING` — ledger entry references item_id that does not exist in findings.json.
- Rich table columns: `item_id`, `item_type` (finding | observation | interpretation), `outcome`, `ledger_line` (1-indexed JSONL line number; `-` for APPROVED_NO_VERIFICATION). Color the outcome column: VERIFIED → green, anything else → red.
- Summary line format (verbatim from ux-spec §2.2):
  - All VERIFIED: `[green]✓[/green] ledger intact — N entries verified` then on next line `       PBKDF2-SHA256, 600,000 iter` then `       window: <first_ts> → <last_ts>`.
  - Any mismatch: `[red]✗[/red] verification FAILED — N/M entries reconciled (K mismatches)` then a list of per-finding outcomes.
- Window timestamps: first and last `ts` field of the ledger JSONL entries (both UTC ISO-8601). Compute via `min()` / `max()` on the parsed datetimes.
- HMAC input recomputation per item_type (architecture §4.9 verbatim — copy into a `_hmac_input` helper):
  - `observation`: `text + "|" + ",".join(sorted(audit_ids))` encoded UTF-8.
  - `interpretation`: `f"{observation_id}|{text}|{confidence.value}"` encoded UTF-8.
  - `finding` (bundles obs + interp): `obs_hmac_input + b"\x00" + interp_hmac_input`.
  - `timeline_event`: future — out of scope for v1 verify.
- `--ledger <path>` flag: override the default ledger path. Same semantics as `silentwitness approve --ledger`.
- `--strict` flag: any mismatch → exit 3 (verification rejection per ux-spec §2.2 exit code policy). Without `--strict`, mismatches → exit 1 (user-facing error). The distinction is for CI pipelines: `--strict` means "fail loudly with the dedicated verification-reject code."
- Context7 hints BEFORE coding:
  - Python stdlib `hmac.compare_digest` — confirm signature requires both args same type (str or bytes).
  - Python stdlib `getpass.getpass` — confirm SIGINT behavior.
  - `pyyaml` topic "safe_load" — for the CASE.yaml salt read (NEVER use `yaml.load` without `safe_load` — RCE risk).
- Known pitfalls:
  1. `hmac.compare_digest(str_a, bytes_b)` raises `TypeError`. Always cast both to the same type before compare. Use `bytes.fromhex()` to convert the stored hex HMAC to bytes; the computed HMAC is also `.digest()` (bytes). Compare bytes-vs-bytes.
  2. The substantive text for a `finding` ledger entry is reconstructed from BOTH the observation and the interpretation, in the architecture-specified concatenation order. Reading just the finding's `summary` or `title` field will silently produce the wrong HMAC. Read the underlying `observation` + `interpretation` objects.
  3. The zeroize MUST happen in a `finally` block. If verify exits via an exception (e.g., corrupt JSONL), the key still gets zeroed.
  4. Wrong password ≠ tamper. If ALL findings fail with DESCRIPTION_MISMATCH, surface a `[yellow]⚠[/yellow]` hint: "all entries failed — most likely wrong password, not tamper. Re-run." The exit code is still 1 — but the user gets a recoverable path.
  5. Ledger path is OUTSIDE the case dir (architecture §4.9 — `/var/lib/silentwitness/verification/`). `rm -rf cases/mr-evil-001/` does NOT touch the ledger; that asymmetry is intentional. Document in the docstring.
- Vocabulary discipline: never "tampered finding" → "DESCRIPTION_MISMATCH" outcome. Never "broken seal" → "verification failed." Match architecture §4.9 reconciliation vocabulary exactly.
