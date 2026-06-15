# Story — Evidence registry (SHA256 manifest + refuse-on-unregistered)

**ID:** story-evidence-registry
**Epic:** Epic 2 — Common types + audit infrastructure
**Depends on:** story-common-types, story-atomic-io
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** build the evidence registry in `src/silentwitness_mcp/evidence/registry.py` that maintains `cases/<case_id>/evidence.json` with SHA256-on-register, exposes `assert_registered(path)` as a refuse-gate every tool wrapper calls first, and provides `verify_hash(path)` for case-resume integrity checks
**So that** the agent cannot run a tool against a hallucinated/forged evidence path — the registry check fails first, making evidence path fabrication structurally impossible (architecture §4.10 — registry; PRD §8 Constraint Implementation row; FR4).

---

## File modification map

- `src/silentwitness_mcp/evidence/__init__.py` — NEW — empty package marker.
- `src/silentwitness_mcp/evidence/registry.py` — NEW — `EvidenceRegistry` class. Fields: `case_dir: Path`, `manifest_path: Path` (= `case_dir / "evidence.json"`). Methods: `register(path: Path, type: EvidenceType, audit_id: str) -> EvidenceRecord` — opens `path` in binary mode, computes SHA256 streaming (8KB chunks), appends an `EvidenceRecord` to the manifest atomically (read JSON → mutate → atomic write via story-atomic-io); refuses if the path is already registered (idempotent re-register raises `AlreadyRegisteredError` UNLESS the existing record's SHA256 matches the recomputed one — then returns the existing record); `assert_registered(path: Path) -> EvidenceRecord` — loads the manifest, looks up by absolute path (resolved + case-insensitive on macOS), raises `EvidenceNotRegisteredError(path)` if absent; `verify_hash(path: Path) -> VerifyResult` — recomputes SHA256, compares to stored, returns `VerifyResult(matches: bool, expected: str, actual: str)`; `list_all() -> list[EvidenceRecord]` returns sorted by `registered_at`. (~280 LOC, splits if over.)
- `src/silentwitness_common/types.py` — UPDATE — add `EvidenceRecord` Pydantic model with fields `path: Path`, `type: EvidenceType`, `sha256: str` (`^[a-f0-9]{64}$`), `size_bytes: int >= 0`, `registered_at: datetime`, `registered_audit_id: str`; add `VerifyResult` Pydantic model. (~30 LOC delta — keep parent file under 400.)
- `tests/unit/test_evidence_registry.py` — NEW — 11 behavioral tests: register a file produces correct SHA256 (precomputed against a known-content fixture); manifest at `case/evidence.json` contains the record after register; double-register same path same content returns the existing record; double-register same path DIFFERENT content raises `AlreadyRegisteredError`; assert_registered raises `EvidenceNotRegisteredError` on unknown path; assert_registered succeeds on registered path; assert_registered handles symlinks by resolving to real path; verify_hash detects bit-rot (file mutated after register → matches=False, actual != expected); list_all returns sorted by registered_at; manifest file is mode 0644 readable (not 0600 — this is not the ledger); manifest write is atomic (kill the process mid-write → reader sees prior state or new state, never half-written JSON).
- `tests/property/test_evidence_registry_properties.py` — NEW — 2 Hypothesis property tests: for any byte payload of size 0..1MB, register/verify_hash round-trip is identity; for any list of distinct files, register/list_all/assert_registered are all consistent (no record loss, no false negatives).

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given an empty case directory at /tmp/case-xyz/
And   a fixture file /tmp/evidence-fixture.bin with known SHA256 X
When  EvidenceRegistry(case_dir=/tmp/case-xyz/).register(/tmp/evidence-fixture.bin, EvidenceType.DISK_IMAGE, audit_id="sift-aj-20260613-001") runs
Then  /tmp/case-xyz/evidence.json exists
And   the manifest contains exactly one EvidenceRecord
And   record.sha256 == X
And   record.size_bytes == os.stat(fixture).st_size

Given /tmp/evidence-fixture.bin has been registered
When  register is called again with the SAME path and the file is UNCHANGED
Then  no error is raised
And   the existing record is returned
And   the manifest still has exactly one record

Given /tmp/evidence-fixture.bin has been registered
And   the file's contents are then modified
When  register is called again with the same path
Then  AlreadyRegisteredError is raised with reason "sha256_mismatch_on_reregister"

Given an EvidenceRegistry exists with one registered file
When  assert_registered is called with an unregistered path "/evidence/not-here.E01"
Then  EvidenceNotRegisteredError is raised with the path in the message

Given /tmp/evidence-fixture.bin has been registered with SHA256 X
And   the file is then corrupted (bit flipped)
When  verify_hash(/tmp/evidence-fixture.bin) runs
Then  result.matches is False
And   result.expected == X
And   result.actual != X

Given an EvidenceRegistry exists
And   /tmp/symlink -> /tmp/evidence-fixture.bin
When  assert_registered(/tmp/symlink) is called
Then  it succeeds (symlink resolved to canonical path before lookup)

Given the manifest is being written by register()
When  the process is killed between the tmp-file write and the rename
Then  the prior manifest is intact (atomic-rename invariant from story-atomic-io)

Given tests/unit/test_evidence_registry.py exists
When  `uv run pytest tests/unit/test_evidence_registry.py -v` runs
Then  exit code is 0
And   11 tests pass

Given tests/property/test_evidence_registry_properties.py exists
When  `HYPOTHESIS_PROFILE=ci uv run pytest tests/property/test_evidence_registry_properties.py -v` runs
Then  exit code is 0
And   2 property tests pass
```

---

## Shell verification

```bash
# Unit tests
uv run pytest tests/unit/test_evidence_registry.py -v
# Must show 11 passing

# Property tests
HYPOTHESIS_PROFILE=ci uv run pytest tests/property/test_evidence_registry_properties.py -v --hypothesis-show-statistics
# Must show 2 passing

# Strict typing
uv run mypy --strict src/silentwitness_mcp/evidence/

# Lint clean
uv run ruff check src/silentwitness_mcp/evidence/

# File size guard
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_mcp/evidence/registry.py

# Manifest file mode check (manual fixture)
python -c "
from pathlib import Path; import os, tempfile
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_common.types import EvidenceType
with tempfile.TemporaryDirectory() as d:
    fix = Path(d) / 'fix.bin'; fix.write_bytes(b'hello')
    reg = EvidenceRegistry(case_dir=Path(d))
    reg.register(fix, EvidenceType.DISK_IMAGE, audit_id='sift-aj-20260613-001')
    mode = os.stat(Path(d) / 'evidence.json').st_mode & 0o777
    assert mode == 0o644, f'expected 0644, got 0o{mode:o}'
    print('manifest mode 0644 ok')
"

# §14 no-mocks check
git diff main...HEAD -- 'src/silentwitness_mcp/evidence/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded)" | grep -v "test\|spec"
# Must output nothing
```

---

## Notes for coding agent

- Reference: architecture.md §4.10 (Evidence registry — manifest schema verbatim, "refuse to operate on unregistered evidence" structural defense, hash re-verification at case-resume time), §4.11 (Mount validation — DO NOT implement here; that lives in `evidence/mount.py`, separate concern, can be its own follow-up story).
- Reference: PRD.md FR4 (architectural rejection of finding claims citing evidence not present), §8 Constraint Implementation row (the registry is one of the six architectural boundaries).
- Reference: BRAINSTORM.md §3.7 (folder structure — `evidence/registry.py`).
- Use `silentwitness_common.atomic_io.write_json_atomic(path, data)` from story-atomic-io for the manifest write. NEVER `json.dump` directly to the manifest path — a crashed half-write leaves the case unrecoverable.
- SHA256 computation: stream in 8KB chunks via `hashlib.sha256().update(chunk)`. Do NOT load the file into memory — disk images and memory dumps can be 10+ GB. This is a hard rule per the IR consultant pain point in PRD §3 ("works the case the way a senior analyst works it" includes not OOMing on a 20GB image).
- Path resolution: always `path.resolve(strict=True)` before lookup AND before storing. This handles symlinks, `..` segments, and case differences. Store the resolved path in the manifest.
- The manifest is a JSON object with shape `{"records": [EvidenceRecord, ...], "schema_version": 1}` — NOT a bare array. Allows future schema migrations.
- DO NOT make the manifest append-only at the filesystem level (no `chattr +a` — root required). The architectural "append-only conceptually" guarantee is enforced by (a) the Claude Code deny rule on `Edit(cases/*/evidence.json)` per architecture §6.2 settings.json, and (b) `register` refusing same-path-different-content re-registration. Both lines of defense matter.
- The manifest file mode is **0644** (world-readable, owner-writable). This is intentional and DIFFERENT from the HMAC ledger (0600). The evidence manifest is not a secret — it lists files and hashes; anyone with the case directory should be able to read it. The HMAC ledger contains derived keys' outputs and lives in `/var/lib/silentwitness/verification/` with 0600.
- The macOS HFS+/APFS case-insensitivity quirk: store the path resolved + lowercased in the lookup index, but display the original-case path in `EvidenceRecord.path`. Tests should cover this — see acceptance criterion on symlinks.
- DO NOT call `assert_registered` from inside this module's own methods (it would create a chicken-and-egg with `register`). The gate is consumed by tool wrappers (Epic 5/6/7) — each wrapper's first call.
- Library docs to consult via Context7 BEFORE coding:
  - `hashlib` is stdlib (no Context7 needed) but the streaming SHA256 pattern is well-known: `h = hashlib.sha256(); while chunk := f.read(8192): h.update(chunk); return h.hexdigest()`.
  - `pydantic` topic `Path field serialization` — Pydantic v2 serializes `Path` as a string; verify the round-trip behaviour for the manifest.
- Future story (NOT this one): `src/silentwitness_mcp/evidence/mount.py` implements `findmnt -n -o OPTIONS --target /evidence/` and refuses if `ro,noexec,nosuid` are not all present (architecture §4.11). That can be a separate story under E2 or pushed to E4 — orchestrator decision.
