# Story — `approve_finding` MCP tool (password-gated HMAC ledger transition)

**ID:** story-approve-finding-tool
**Epic:** Epic 4 — MCP server skeleton + finding-state tools
**Depends on:** story-fastmcp-server-bootstrap, story-response-envelope, story-record-observation-tool, story-record-interpretation-tool, story-hmac-ledger, story-audit-logger
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As an** examiner approving a staged finding for inclusion in the final report
**I want to** call `approve_finding(finding_id)` which prompts for my password, derives the HMAC key via PBKDF2-SHA256 (600,000 iterations), computes the HMAC over the substantive text, appends a sealed entry to the ledger, and transitions the finding from DRAFT to APPROVED
**So that** the audit trail carries a verifiable approval the report can render and `silentwitness verify` can re-check post-handoff — matching the Valhuntir L1 floor (architecture.md §4.9)

---

## File modification map

Exact files the coding agent creates or modifies:

- `src/silentwitness_mcp/findings/approval.py` — NEW — `@mcp.tool() async def approve_finding(...)` orchestrating the password-gated HMAC ledger write + state transition (≤300 LOC; architecture.md §4.2 row `approve_finding`, §4.9 HMAC ledger semantics)
- `src/silentwitness_common/types.py` — UPDATE — `ApproveInput`, `ApproveResult`, `FindingStatus` (DRAFT | REVIEWED | APPROVED | ARCHIVED) (≤30 LOC delta)
- `tests/integration/test_approve_finding.py` — NEW — ≥12 BDD scenarios: valid approval; wrong password; missing salt; finding not found; finding already approved; HMAC zeroization after; ledger entry verifiable via `hmac.compare_digest`

The coding agent must NOT modify files outside this map.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a staged finding F-001 with observation O-001 + interpretation I-001 in findings.json
And   case salt is registered in cases/<case_id>/CASE.yaml
And   the examiner-supplied password is correct (in the test harness, injected via dependency)
When  approve_finding(finding_id="F-001") is called
Then  the result is ApproveResult(success=True)
And   /var/lib/silentwitness/verification/<case_id>.jsonl gains exactly one new line
And   that line has {ts, item_id: "F-001", item_type: "finding", content_hash, hmac, examiner}
And   findings.json shows F-001.status == "APPROVED"
And   the derived HMAC key is zeroed from process memory after the call

Given approve_finding called with a password whose PBKDF2 derivation does not match the registered key
When  approve_finding is called
Then  the result is ApproveResult(success=False, reason="INVALID_PASSWORD")
And   no ledger entry is appended

Given approve_finding called for F-999 which does not exist
When  approve_finding is called
Then  the result is ApproveResult(success=False, reason="FINDING_NOT_FOUND")

Given F-001 is already status=APPROVED
When  approve_finding(finding_id="F-001") is called a second time
Then  the result is ApproveResult(success=False, reason="ALREADY_APPROVED")
And   the ledger is not modified

Given /var/lib/silentwitness/verification/ exists but with mode 0755 (looser than required 0700)
When  approve_finding is called
Then  the result is ApproveResult(success=False, reason="LEDGER_DIR_PERMISSIONS_WEAK")

Given a successful approval
When  hmac.compare_digest is used to re-verify the ledger entry's HMAC against a freshly-derived key from the same password and the substantive text loaded from findings.json
Then  the comparison returns True

Given a tampered ledger entry (hmac field modified by one byte)
When  hmac.compare_digest re-verifies
Then  the comparison returns False
And   `silentwitness verify` (which calls into the same ledger module) reports DESCRIPTION_MISMATCH

Given approve_finding succeeds
When  the ledger file mode is checked
Then  the file is 0600
And   the parent directory is 0700
And   an fsync of both the file and the parent directory occurred (verifiable via mocked syscall counter in test)

Given the test suite runs
When  uv run pytest tests/integration/test_approve_finding.py
Then  ≥12 tests pass
And   coverage on src/silentwitness_mcp/findings/approval.py is ≥90%
```

---

## Shell verification

```bash
# Tests pass with ≥12 cases
uv run pytest tests/integration/test_approve_finding.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥12

# Coverage ≥90% on this file; audit/ overall ≥90% per architecture.md §14
uv run coverage run -m pytest tests/integration/test_approve_finding.py
uv run coverage report --include="src/silentwitness_mcp/findings/approval.py" --fail-under=90

# All reject reasons tested
for r in INVALID_PASSWORD FINDING_NOT_FOUND ALREADY_APPROVED LEDGER_DIR_PERMISSIONS_WEAK; do
  grep -q "$r" tests/integration/test_approve_finding.py || { echo "missing test for $r"; exit 1; }
done

# Lint + types
uv run ruff check src/silentwitness_mcp/findings/approval.py
uv run mypy --strict src/silentwitness_mcp/findings/approval.py

# File-size guard
[ "$(wc -l < src/silentwitness_mcp/findings/approval.py)" -le 400 ]

# PBKDF2 iterations match architecture.md §4.9
grep -q "600_000\|600000" src/silentwitness_mcp/audit/ledger.py

# Constant-time comparison (no plain == on the hmac)
! grep -E "hmac.*==" src/silentwitness_mcp/findings/approval.py | grep -v "compare_digest"
```

---

## Notes for coding agent

- Source of truth: architecture.md §4.2 (`approve_finding` row — input `ApproveInput(finding_id: str)`, examiner-only, requires password); §4.9 (HMAC ledger semantics — PBKDF2-SHA256 600,000 iterations, per-case salt, ledger at `/var/lib/silentwitness/verification/<case_id>.jsonl`, dir 0700, file 0600, constant-time HMAC comparison via `hmac.compare_digest`); §8.2 (sequence: examiner approves → password prompt → derive key → compute HMAC → append → zero key); ADR-007 (stdlib hmac + hashlib over libsodium); `context/competitive/11` §2 L2 (Valhuntir pattern verbatim).
- This tool is NOT callable by the LLM in the standard configuration — architecture.md §6.2 deny rule blocks `Bash(silentwitness approve*)` and `mcp__silentwitness__approve_finding` is gated by examiner password. The tool exists for the CLI invocation path (`silentwitness approve` in Epic 12) and the in-process examiner workflow.
- Password handling:
  - Password is NEVER stored. Held in process memory ONLY during the call. Zeroed before return.
  - Use `getpass.getpass()` ONLY in CLI; the MCP tool itself takes the password via a typed input parameter from a trusted caller (the CLI). Do NOT prompt inside the MCP tool — that breaks the JSON-RPC contract.
  - The CLI wrapper is responsible for the secure prompt; the MCP tool receives the derived key OR a password string and immediately derives the key.
- HMAC inputs (architecture.md §4.9 verbatim):
  - For an `observation`: `text + "|" + sorted(audit_ids).join(",")`
  - For an `interpretation`: `observation_id + "|" + text + "|" + confidence.value`
  - For an approved `finding`: the concatenation of the observation HMAC input and the interpretation HMAC input with a `\x00` separator.
- Key derivation: `hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)` — 600,000 iterations is the OWASP 2023 minimum and Valhuntir's choice.
- Salt: loaded from `cases/<case_id>/CASE.yaml`. If missing, abort with `CASE_SALT_MISSING`.
- Ledger entry schema (architecture.md §4.9 verbatim):
  ```jsonc
  {
    "ts": "<iso8601 UTC>",
    "item_id": "F-001",
    "item_type": "finding",
    "content_hash": "<sha256 of substantive text>",
    "hmac": "<hex hmac-sha256>",
    "examiner": "<name>"
  }
  ```
- File operations:
  - Directory `/var/lib/silentwitness/verification/` created at `silentwitness case init` (story-hmac-ledger) with mode 0700. If found with weaker mode at approval time → reject `LEDGER_DIR_PERMISSIONS_WEAK`.
  - File opened with `os.open(path, O_CREAT | O_WRONLY | O_APPEND, 0o600)`; chmod after open to enforce 0600 even if umask leaks.
  - `fsync(file_fd)` after write, then `fsync(dir_fd)` for entry-creation durability.
  - Append-only conceptually; no rewrite path.
- Zeroization: after the HMAC is appended, overwrite the derived-key bytes with zeros (`bytearray` allows in-place zeroing; `bytes` does not). Use `bytearray` for the derived key throughout.
- State transition: update `findings.json` so the finding's status flips DRAFT → APPROVED. Atomic-rename write (story-atomic-io).
- Re-verification path: `silentwitness verify` (Epic 12 / `cli-verify` story) calls into the same ledger module with the same constant-time comparison. The verifier needs to load the substantive text from `findings.json`, recompute the HMAC against the supplied password, and compare. Mismatch → `DESCRIPTION_MISMATCH`. Missing finding-but-present ledger → `VERIFICATION_NO_FINDING`. Present finding-but-missing ledger → `APPROVED_NO_VERIFICATION`. Reuse Valhuntir's reconciliation vocabulary (architecture.md §4.9 final paragraph).
- `ApproveInput`:
  ```python
  class ApproveInput(BaseModel):
      finding_id: str
      password: SecretStr                     # Pydantic v2 SecretStr — does not log
  ```
- `ApproveResult`:
  ```python
  class ApproveResult(BaseModel):
      success: bool
      finding_id: str | None = None
      ledger_entry_ts: datetime | None = None
      reason: ApproveRejectReason | None = None
      context: dict[str, Any] = Field(default_factory=dict)
  ```
- `ApproveRejectReason` StrEnum: `INVALID_PASSWORD | FINDING_NOT_FOUND | ALREADY_APPROVED | LEDGER_DIR_PERMISSIONS_WEAK | CASE_SALT_MISSING | LEDGER_FILE_MODE_WEAK`.
- Audit JSONL emission for the approval call itself: write to `cases/<case_id>/audit/findings.jsonl` with `tool="approve_finding"`. Do NOT include the password or the derived key in the audit entry — only the result and finding_id.
- Context7 hints: stdlib only (`hmac`, `hashlib`, `os`, `secrets`). No external library for the crypto — ADR-007 commits this. For `Pydantic v2 SecretStr` behavior, `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic"` then query topic "SecretStr serialization JSON dump".
- Vocabulary: never "court-admissible." Architecture.md §4.9 uses "defensible audit trail" framing. Match it.
- Known pitfalls: (1) `hmac.compare_digest(a, b)` requires both args to be the same type (str or bytes); cast consistently; (2) `getpass.getpass` does NOT belong in this tool — CLI handles the prompt; (3) PBKDF2 600K iterations is slow (~100ms per derivation); document this in module docstring so callers don't issue rapid-fire approvals; (4) the ledger lives OUTSIDE the project tree at `/var/lib/silentwitness/...` — case directory rm -rf does NOT touch the ledger; that asymmetry is intentional per architecture.md §4.9; (5) `SecretStr.get_secret_value()` should be called exactly once per approval, immediately fed into `pbkdf2_hmac`, and then the `SecretStr` discarded.
