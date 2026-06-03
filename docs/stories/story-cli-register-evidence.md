# Story — `silentwitness register-evidence <case-id> <path>` (SHA256 + manifest append)

**ID:** story-cli-register-evidence
**Epic:** Epic 12 — CLI (Typer) + Claude Code drop-in config
**Depends on:** story-cli-init, story-evidence-registry, story-audit-logger
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As an** IR consultant adding a new evidence artifact (disk image, memory dump, EVTX, pcap, hive) to an open case
**I want to** run `silentwitness register-evidence <case-id> <path>` and have the file SHA256'd, the type auto-detected, and an `EvidenceRecord` appended to `cases/<case-id>/evidence.json` via `EvidenceRegistry.register()`
**So that** every downstream tool wrapper's `assert_registered(path)` gate has a hash-verified manifest entry to look up — and the agent cannot run any forensic tool against a hallucinated/forged evidence path (architecture §4.10 evidence registry, FR4 architectural rejection of unverified claims; ux-spec §2.2 `register-evidence` invocation + sample output).

---

## File modification map

- `src/silentwitness_agent/cli.py` — UPDATE — add `@app.command("register-evidence")` function. Signature: `def register_evidence(case_id: str = typer.Argument(...), path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=True, readable=True, resolve_path=True), label: str | None = typer.Option(None, "--label"), recursive: bool = typer.Option(False, "--recursive"), dry_run: bool = typer.Option(False, "--dry-run"))`. Body: resolves case dir; loads `EvidenceRegistry`; detects `EvidenceType` from suffix (`.E01/.EWF/.dd/.img/.raw` → disk_image; `.mem/.vmem/.dmp` → memory_dump; `.evtx` → evtx; `.pcap/.pcapng` → pcap; `.hve/.hiv` or known hive names like `SYSTEM`, `SOFTWARE`, `SAM`, `NTUSER.DAT` → hive; otherwise `other`); if `--recursive` and path is a directory, walks all files and registers each; calls `registry.register(path, type, audit_id)` per file; prints sample output verbatim from ux-spec §2.2; emits one `audit/cli.jsonl` entry per call. (~60 LOC delta to cli.py.)
- `src/silentwitness_agent/cli_commands/__init__.py` — NEW — empty package marker; opens the door for future per-command splits if cli.py grows past 400 LOC.
- `tests/integration/test_cli_register_evidence.py` — NEW — ≥9 BDD scenarios via `CliRunner`: happy-path register of a known-content fixture produces correct SHA256 entry in `evidence.json`; non-existent path exits 1 (Typer's `exists=True` validation); unreadable path (chmod 0000) exits 1; auto-type-detection correctly maps `.E01` → disk_image, `.mem` → memory_dump, `.evtx` → evtx, `.pcap` → pcap, `SYSTEM` (no suffix) → hive, `.txt` → other; `--recursive` on a dir with 3 files registers all 3; `--dry-run` does NOT modify `evidence.json` but prints the SHA256s; double-register of unchanged file is idempotent (no error, returns existing record per story-evidence-registry); double-register with mutated content exits 1 with `AlreadyRegisteredError` reason.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a case mr-evil-001 initialized via `silentwitness init`
And   a fixture file /tmp/evidence/SchardtPC.E01 with known SHA256 X (precomputed)
When  `uv run silentwitness register-evidence mr-evil-001 /tmp/evidence/SchardtPC.E01` runs
Then  exit code is 0
And   cases/mr-evil-001/evidence.json contains exactly one EvidenceRecord
And   record.sha256 == X
And   record.type == "disk_image" (auto-detected from .E01 suffix)
And   stdout contains "[green]✓[/green] registered SchardtPC.E01" with sha256 prefix and human-readable size

Given mr-evil-001 has SchardtPC.E01 already registered
When  `uv run silentwitness register-evidence mr-evil-001 /tmp/evidence/SchardtPC.E01` runs again on the unchanged file
Then  exit code is 0
And   evidence.json still contains exactly one record (idempotent — story-evidence-registry guarantee)
And   stdout warns "[yellow]⚠[/yellow] already registered (sha256 matches)"

Given mr-evil-001 has SchardtPC.E01 registered
And   the fixture file's contents have been modified (one byte flipped)
When  `uv run silentwitness register-evidence mr-evil-001 /tmp/evidence/SchardtPC.E01` runs
Then  exit code is 1
And   stderr contains "AlreadyRegisteredError" or "sha256_mismatch_on_reregister"

Given a path that does not exist
When  `uv run silentwitness register-evidence mr-evil-001 /tmp/nonexistent.E01` runs
Then  exit code is 1 (Typer's exists=True validation)
And   stderr contains "does not exist"

Given a file with mode 0000 (unreadable)
When  the register command runs
Then  exit code is 1
And   stderr contains permission-denied wording

Given a directory /tmp/evidence/ containing 3 files (.E01, .mem, .evtx)
When  `uv run silentwitness register-evidence mr-evil-001 /tmp/evidence/ --recursive` runs
Then  exit code is 0
And   evidence.json contains exactly 3 records
And   the records' types are disk_image, memory_dump, evtx respectively (auto-detected)

Given a fixture file /tmp/evidence/SYSTEM (registry hive, no suffix)
When  the register command runs
Then  the recorded type is "hive" (detected from filename, not suffix)

Given --dry-run is passed
When  the register command runs against an un-registered file
Then  exit code is 0
And   evidence.json is NOT modified
And   stdout shows the computed SHA256 prefixed with "DRY-RUN"

Given the case mr-evil-001 does not exist
When  `uv run silentwitness register-evidence mr-evil-001 /tmp/foo.E01` runs
Then  exit code is 1
And   stderr contains "case 'mr-evil-001' not found"

Given tests/integration/test_cli_register_evidence.py exists
When  `uv run pytest tests/integration/test_cli_register_evidence.py -v` runs
Then  exit code is 0
And   ≥9 tests pass
```

---

## Shell verification

```bash
uv run pytest tests/integration/test_cli_register_evidence.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥9

# Strict typing on the cli.py delta
uv run mypy --strict src/silentwitness_agent/cli.py

# Lint clean
uv run ruff check src/silentwitness_agent/

# Cumulative cli.py size budget — init + register-evidence should be ≤180 LOC
[ "$(wc -l < src/silentwitness_agent/cli.py)" -le 180 ] || { echo "cli.py over running budget"; exit 1; }

# Exit code policy spot check
uv run silentwitness register-evidence mr-evil-001 /tmp/definitely-nonexistent.E01; [ "$?" = "1" ]

# §14 no-mocks check
git diff main...HEAD -- 'src/silentwitness_agent/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded)" | grep -v "test\|spec"
```

---

## Notes for coding agent

- Source of truth: architecture.md §4.10 (EvidenceRegistry — manifest schema, `register` returns the existing record on unchanged re-register, raises `AlreadyRegisteredError` on hash mismatch), §4.11 (mount validation — runs at registration time; `register-evidence` invokes it transitively via `EvidenceRegistry.register()`); ux-spec.md §2.2 (`register-evidence` sample output — copy the four-line tree shape verbatim including `mount: /mnt/evidence (ro,noexec,nosuid) [green]✓[/green]` line); FR4 (architectural rejection of unverified claims — this story is one of the structural lines of defense).
- The auto-type-detection table is fixed (no LLM in the loop here). Implement as a pure function `_detect_evidence_type(path: Path) -> EvidenceType` with a suffix lookup table + a known-hive-name allowlist (`{"SYSTEM", "SOFTWARE", "SAM", "SECURITY", "NTUSER.DAT", "DEFAULT", "USRCLASS.DAT"}`). The function lives in `cli.py` for now — if it crosses ~20 LOC, hoist to `cli_commands/_evidence_types.py`.
- Idempotency comes from `EvidenceRegistry.register()` (story-evidence-registry): same-path same-content → returns existing record + no error; same-path different-content → raises `AlreadyRegisteredError(reason="sha256_mismatch_on_reregister")`. CLI catches the latter and exits 1 with a clean stderr message.
- `--recursive` walks via `path.rglob("*")` filtered to `is_file()`. Each file gets one `register()` call and one stdout line. Errors on individual files do NOT abort the walk — they're collected and printed as a summary at the end, with exit code 0 if any succeeded and 1 if all failed (per ux-spec §2.5 "no hand-holding" — but the summary is honest).
- `--dry-run` short-circuits before the manifest write but still does the SHA256 (so the user sees what would be registered). Implement as `if dry_run: print(...); return` after computing the hash but before calling `registry.register(...)`.
- Use `EvidenceRegistry` exactly as defined in story-evidence-registry: `reg = EvidenceRegistry(case_dir=case_dir); reg.register(path, type, audit_id)`. The audit_id is generated via the same `make_audit_id` helper story-cli-init uses (`tool="cli.register-evidence"`).
- Stream the SHA256 (8KB chunks per story-evidence-registry §notes) — do NOT load the file into memory. Disk images are routinely 10+ GB on SIFT 2026. The `registry.register()` call already enforces this; the CLI must not pre-read the file for any reason.
- Use `rich.console.Console` from the shared `_console()` helper landed in story-cli-init. Do not instantiate a new Console.
- Sample-output formatting (ux-spec §2.2):
  ```
  [green]✓[/green] registered SchardtPC.E01
         sha256: 3a4f...c901    size: 4.2 GiB
         mount:  /mnt/evidence (ro,noexec,nosuid) [green]✓[/green]
  ```
  The sha256 is truncated to first 4 + last 4 hex chars; size is human-readable via a helper (1024-based — `KiB`, `MiB`, `GiB`). The mount line shows the resolved mount point of the parent dir of the evidence path; if mount validation refuses (`MOUNT_NOT_RO_NOEXEC_NOSUID`), the line shows `[red]✗[/red]` and exit code is 2 (system error). Re-use the mount validation result from `EvidenceRegistry.register()` — do not re-run `findmnt` here.
- Context7 hints BEFORE coding:
  - `typer` topic "Argument exists=True resolve_path" — Typer's path validation semantics.
  - `pathlib` (stdlib) `Path.rglob` for the `--recursive` walk; `Path.resolve(strict=True)` for symlink resolution.
- Known pitfalls:
  1. Typer's `exists=True` raises `BadParameter` BEFORE the command body runs; this gives exit code 2 by default. Override via a callback or accept the default. Either is fine — the test must just confirm exit is 1 (user error). Per ux-spec §2.2, missing-file is user error (1), not system error (2). If Typer's default conflicts, drop `exists=True` and validate manually in the function body.
  2. `--recursive` on a single-file path should still work (the rglob is a no-op for a file). Do not error.
  3. The `audit/cli.jsonl` entry is ONE per CLI invocation, not one per file (the per-file audit IDs live in the manifest's `registered_audit_id` field on each `EvidenceRecord`). This matches architecture §4.4 — one JSONL line per "tool call," and the tool call here is the CLI invocation.
- Vocabulary discipline: never "chain-of-custody-grade hash" — say "SHA256 manifest entry" or "registered hash." Architecture §4.10 uses "registered" everywhere; match it.
