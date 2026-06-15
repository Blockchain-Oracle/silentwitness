# Story — HMAC-signed approval ledger

**ID:** story-hmac-ledger
**Epic:** Epic 2 — Common types + audit infrastructure
**Depends on:** story-common-types, story-atomic-io
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** build the HMAC-signed approval ledger in `src/silentwitness_mcp/audit/ledger.py` using stdlib `hmac` + `hashlib.pbkdf2_hmac` (PBKDF2-SHA256, 600,000 iterations) with the ledger file at `/var/lib/silentwitness/verification/<case_id>.jsonl` (directory 0700, file 0600), and constant-time HMAC comparison via `hmac.compare_digest`
**So that** every examiner-approved finding carries a forgery-resistant signature tied to the case-scoped password (architecture §4.9 — Valhuntir pattern reuse; PRD §8 row 5 Audit Trail Quality; FR — defensible audit trail).

---

## File modification map

- `src/silentwitness_mcp/audit/ledger.py` — NEW — `HMACLedger` class. Static methods: `derive_key(password: str, salt: bytes, iterations: int = 600_000) -> bytes` returns 32-byte derived key via `hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations, dklen=32)`; `compute_hmac(key: bytes, message: bytes) -> str` returns hex HMAC-SHA256; `verify_hmac(key: bytes, message: bytes, expected_hex: str) -> bool` uses `hmac.compare_digest`. Instance methods: `__init__(self, ledger_dir: Path, case_id: str)` — creates ledger_dir at mode 0700 if absent, refuses to proceed if existing dir mode is weaker than 0700; `append(self, key: bytes, item_id: str, item_type: LedgerItemType, content_hash: str, examiner: str) -> LedgerEntry` — composes the entry, computes HMAC over the substantive bytes per architecture §4.9, appends to `<ledger_dir>/<case_id>.jsonl` via atomic-io helper, chmods to 0600 after first write; `read_all(self) -> list[LedgerEntry]` — parses the JSONL; `verify_entry(self, key: bytes, entry: LedgerEntry, content_bytes: bytes) -> bool` — recomputes HMAC, calls verify_hmac; `zero_key(key_buf: bytearray) -> None` — best-effort zero of a key buffer in process memory. (~320 LOC, splits if over.)
- `src/silentwitness_common/types.py` — UPDATE — add `LedgerItemType` enum (finding/observation/interpretation/timeline_event) and `LedgerEntry` Pydantic model with fields `ts: datetime`, `item_id: str`, `item_type: LedgerItemType`, `content_hash: str` (`^[a-f0-9]{64}$`), `hmac: str` (`^[a-f0-9]{64}$`), `examiner: str`. (~25 LOC delta.)
- `tests/unit/test_hmac_ledger.py` — NEW — 13 behavioral tests: derive_key(password, salt, 600_000) produces deterministic 32-byte output; derive_key with iterations<600_000 raises ValueError (enforce OWASP floor); compute_hmac is deterministic for same key+message; verify_hmac returns True on match, False on single-bit-flip; verify_hmac uses constant-time compare (timing test — see notes); ledger_dir creation sets mode 0700; ledger file is chmod 0600 after first append; ledger refuses to operate if pre-existing ledger_dir mode is 0755 (raises PermissionError-like); append writes well-formed JSONL parseable by read_all; verify_entry round-trip succeeds with correct key + content; verify_entry fails on tampered content; verify_entry fails on tampered HMAC field; zero_key zeroes bytes in-place.
- `tests/property/test_hmac_ledger_properties.py` — NEW — 4 Hypothesis property tests: derive_key is deterministic for any (password, salt) pair; compute_hmac collisions absent over 1000 random messages with fixed key (sanity); a forged HMAC of any non-matching content with the wrong key fails verify_entry; append/read_all round-trip preserves all entries in order.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given derive_key is called with password='p', salt=b'\x00'*16, iterations=600_000
When  the call returns
Then  the return value is exactly 32 bytes
And   the value matches a precomputed-fixture HMAC test vector (hardcoded in the test)

Given derive_key is called with iterations=100_000
When  the call is made
Then  ValueError is raised with reason mentioning "OWASP minimum 600000"

Given a key K and message M
When  compute_hmac(K, M) is called twice
Then  both return values are identical hex strings of length 64

Given verify_hmac(K, M, compute_hmac(K, M))
When  the call returns
Then  result is True

Given verify_hmac(K, M, expected_hex) where expected_hex has one bit flipped
When  the call returns
Then  result is False
And   the call used hmac.compare_digest (verified by patching and asserting it was called)

Given the ledger_dir does NOT exist
When  HMACLedger(ledger_dir=/tmp/v1/, case_id='c1') is constructed
Then  /tmp/v1/ exists with mode 0700
And   the directory is owned by the current process owner

Given the ledger_dir exists at mode 0755 (group-readable)
When  HMACLedger(ledger_dir=/tmp/v1/, case_id='c1') is constructed
Then  an error is raised (refuse-to-proceed on weak mode)

Given an HMACLedger.append is called for the first time
When  the call returns
Then  /tmp/v1/c1.jsonl exists with mode 0600
And   the file contains exactly one well-formed JSONL line
And   the line parses to LedgerEntry via model_validate_json

Given an entry is appended with key K, content_hash H, hmac=HMAC(K, content_bytes)
When  verify_entry(K, entry, content_bytes) is called
Then  result is True

Given the same as above but with content_bytes mutated by one byte
When  verify_entry(K, entry, mutated_bytes) is called
Then  result is False

Given tests/unit/test_hmac_ledger.py exists
When  `uv run pytest tests/unit/test_hmac_ledger.py -v` runs
Then  exit code is 0
And   13 tests pass

Given tests/property/test_hmac_ledger_properties.py exists
When  `HYPOTHESIS_PROFILE=ci uv run pytest tests/property/test_hmac_ledger_properties.py -v` runs
Then  exit code is 0
And   4 property tests pass
```

---

## Shell verification

```bash
# Unit tests
uv run pytest tests/unit/test_hmac_ledger.py -v
# Must show 13 passing

# Property tests
HYPOTHESIS_PROFILE=ci uv run pytest tests/property/test_hmac_ledger_properties.py -v --hypothesis-show-statistics
# Must show 4 passing

# Coverage on the audit subtree must be ≥90%
uv run coverage run -m pytest tests/unit/test_hmac_ledger.py tests/property/test_hmac_ledger_properties.py tests/unit/test_audit_logger.py tests/property/test_audit_logger_properties.py
uv run coverage report --include="src/silentwitness_mcp/audit/*" --fail-under=90

# Strict typing
uv run mypy --strict src/silentwitness_mcp/audit/

# Lint clean
uv run ruff check src/silentwitness_mcp/audit/

# File size guard
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_mcp/audit/ledger.py

# Mode bits verified inside a tempdir
uv run python -c "
import os, tempfile, pathlib
from silentwitness_mcp.audit.ledger import HMACLedger
from silentwitness_common.types import LedgerItemType
with tempfile.TemporaryDirectory() as d:
    led_dir = pathlib.Path(d) / 'verification'
    led = HMACLedger(ledger_dir=led_dir, case_id='c1')
    assert oct(os.stat(led_dir).st_mode & 0o777) == '0o700'
    key = HMACLedger.derive_key('pw', b'\\x00'*16, 600_000)
    led.append(key, 'F-001', LedgerItemType.FINDING, 'a'*64, 'aj')
    mode = oct(os.stat(led_dir / 'c1.jsonl').st_mode & 0o777)
    assert mode == '0o600', f'expected 0o600, got {mode}'
    print('mode 0o700 dir + 0o600 file ok')
"

# Constant-time compare must be used (gate: hmac.compare_digest appears in source)
grep -E 'hmac\.compare_digest' src/silentwitness_mcp/audit/ledger.py

# §14 no-mocks check
git diff main...HEAD -- 'src/silentwitness_mcp/audit/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded)" | grep -v "test\|spec"
# Must output nothing
```

---

## Notes for coding agent

- Reference: architecture.md §4.9 (HMAC-signed approval ledger — verbatim: PBKDF2-SHA256 with **600,000 iterations** OWASP 2023 minimum and Valhuntir's choice — `forensic-rag.../verification.py:33`; per-case salt; password never persisted; `hmac.compare_digest` constant-time), ADR-007 (stdlib `hmac` + `hashlib.pbkdf2_hmac` chosen over libsodium — verbatim rationale).
- Reference: PRD.md §6 NFR (HMAC-SHA256 PBKDF2-600K-iter approval ledger), §8 row 5 (Audit Trail Quality — HMAC-signed ledger at `/var/lib/silentwitness/verification/<case_id>.jsonl` mode 0600).
- Reference: BRAINSTORM.md §4 (entry schema verbatim).
- The HMAC composition rules per architecture §4.9 (verbatim):
  - For `observation`: `text + "|" + sorted(audit_ids).join(",")`
  - For `interpretation`: `observation_id + "|" + text + "|" + confidence.value`
  - For `finding` (bundles observation + interpretation): the concatenation of both with `\x00` separator
  - These composition rules belong in this story; expose them as `LedgerComposer` static methods (or pure functions) so the upstream callers (Epic 4 `approve_finding` tool, Epic 12 CLI `silentwitness approve`) can reuse.
- The `derive_key` MUST enforce iterations ≥ 600_000 (raise `ValueError` below). This is the architectural floor — never make it configurable downward.
- Password handling: `derive_key` takes `password: str` BUT the caller must hold the password in process memory only for the duration of one approve invocation and zero it after. Provide `zero_key(buf: bytearray) -> None` that overwrites in-place with `\x00`. Document the limitation honestly: Python strings are immutable so the password itself cannot be zeroed (interned in str cache); the *derived key* can be zeroed if held as `bytearray`. The honest documentation note matches PRD §14's vocabulary discipline.
- Directory mode enforcement: at construction, if `ledger_dir` does NOT exist, create it with `os.makedirs(ledger_dir, mode=0o700)` AND verify with `os.chmod(ledger_dir, 0o700)` (umask can mask the mode bits — chmod after makedirs is belt+suspenders). If the dir DOES exist, `os.stat(ledger_dir).st_mode & 0o777 == 0o700` or refuse-to-proceed with a `PermissionError` (per architecture §4.9 "If the directory exists with weaker mode, init aborts").
- File mode enforcement: open with `os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)` AND `os.chmod(path, 0o600)` after first write (per architecture §4.9). Wrap fd in `os.fdopen(fd, "ab")` to write JSONL lines.
- Constant-time compare: ALWAYS use `hmac.compare_digest(a, b)` where both are str or both are bytes. NEVER `a == b` for HMAC comparison — string equality short-circuits on first mismatched byte, leaking timing info.
- Constant-time test approach: do NOT write a timing-side-channel test (flaky in CI). Instead, patch `hmac.compare_digest` with a side-effect-tracking mock and assert it was called — proves the constant-time API is on the verify path.
- fsync after every write per architecture §4.9. Reuse `atomic_io.append_jsonl_line` from story-atomic-io.
- Do NOT log the password, the derived key, or the salt to the audit JSONL or to stdout. The ledger and the audit logger are intentionally separate paths (different directories, different lifecycles).
- Library docs to consult via Context7 BEFORE coding:
  - `hashlib pbkdf2_hmac` topic `dklen iterations 600000` (stdlib, but the dklen=32 conventions and SHA256 PRF are worth re-confirming for Python 3.12).
  - `hmac compare_digest` topic `constant time comparison` (Python 3.12 — confirm signature accepts `str | bytes`).
- Pitfall: macOS umask defaults to 022; without the explicit chmod, the dir lands at 0o755 not 0o700, and the construction-time check then refuses to proceed on subsequent runs in the same temp dir. Always chmod after makedirs.
- Future caller (NOT this story): Epic 12 `silentwitness approve <case> --finding <id>` will (a) prompt for the password via Typer's `prompt(hide_input=True)`, (b) load the per-case salt from `CASE.yaml`, (c) call `derive_key`, (d) load `findings.json`, (e) compose the substantive bytes, (f) call `append`, (g) call `zero_key`. This story only owns the ledger primitives.
