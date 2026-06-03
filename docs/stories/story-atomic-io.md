# Story — Atomic-write IO helpers

**ID:** story-atomic-io
**Epic:** Epic 2 — Common types + audit infrastructure
**Depends on:** story-scaffold-uv-pyproject
**Estimate:** ~1.5h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** ship atomic-write helpers in `src/silentwitness_common/atomic_io.py` — `write_bytes_atomic`, `write_text_atomic`, `write_json_atomic`, `append_jsonl_line` — using the tmp-write + fsync + rename + dir-fsync pattern
**So that** every report write, manifest update, audit append, and ledger append is crash-safe: a killed process never leaves a half-written file (architecture §5.4 — atomic-save invariant on report.md; §4.4 — JSONL discipline with fsync; consumed by story-audit-logger, story-evidence-registry, story-hmac-ledger, and Epic 11 report writer).

---

## File modification map

- `src/silentwitness_common/atomic_io.py` — NEW — Pure functions (no class needed): `write_bytes_atomic(path: Path, data: bytes, mode: int = 0o644) -> None` — write to `path.with_suffix(path.suffix + ".tmp.<pid>.<rand>")`, `fsync(tmp_fd)`, close, `os.replace(tmp, final)`, `fsync(parent_dir_fd)`; `write_text_atomic(path: Path, text: str, *, encoding: str = "utf-8", mode: int = 0o644) -> None`; `write_json_atomic(path: Path, data: Any, *, indent: int | None = None, mode: int = 0o644) -> None` (JSON-serializes then calls write_bytes_atomic); `append_jsonl_line(path: Path, line: str, *, mode: int = 0o644) -> None` — opens in append mode, writes line + "\n", fsync, close (NO rename — appends are intrinsically atomic at the byte level on POSIX for writes ≤ PIPE_BUF, BUT we still fsync for durability); `_fsync_dir(dir_path: Path) -> None` helper; context manager `atomic_writer(path: Path, mode: int = 0o644) -> ContextManager[BinaryIO]` for streaming-write use cases (Epic 11 report renderer). (~220 LOC.)
- `tests/unit/test_atomic_io.py` — NEW — 12 behavioral tests: write_bytes_atomic creates the final file with correct contents; write_bytes_atomic does NOT leave a `.tmp.*` artifact on success; write_text_atomic round-trip preserves UTF-8 (including emojis, Chinese chars, BOM); write_json_atomic produces parseable JSON; write_json_atomic with indent=2 pretty-prints; append_jsonl_line creates the file on first call; append_jsonl_line preserves prior lines on subsequent calls; append_jsonl_line always terminates with "\n"; concurrent append_jsonl_line from 10 threads × 10 calls = 100 well-formed JSON lines (no torn writes); kill-mid-write simulation — if rename fails (simulated via patch), the final file still contains prior content (atomicity); mode bits honored — write_bytes_atomic with mode=0o600 produces a 0600 file; atomic_writer context manager rolls back on exception (final file unchanged if `__exit__` sees an exception).
- `tests/property/test_atomic_io_properties.py` — NEW — 2 Hypothesis property tests: for any byte payload 0..1MB, write_bytes_atomic / read round-trip is identity; for any list of JSONL lines, sequential append_jsonl_line / read produces exactly the input list in order.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a target path /tmp/case-xyz/foo.json that does not exist
When  write_json_atomic(/tmp/case-xyz/foo.json, {"a": 1}) runs
Then  /tmp/case-xyz/foo.json exists
And   json.loads(file.read_text()) == {"a": 1}
And   no /tmp/case-xyz/foo.json.tmp.* artifact remains

Given write_bytes_atomic is called with mode=0o600
When  the call returns
Then  os.stat(path).st_mode & 0o777 == 0o600

Given a JSONL file with 5 lines pre-existing
When  append_jsonl_line(path, '{"k":6}') runs
Then  the file has 6 lines
And   the 6th line is '{"k":6}\n'
And   prior 5 lines are unchanged

Given 10 threads each call append_jsonl_line 10 times concurrently on the same path
When  all threads complete
Then  the file contains exactly 100 lines
And   each line is well-formed JSON

Given write_bytes_atomic targets a path on a filesystem where rename across mount points fails
When  rename fails
Then  the prior file content is intact (no partial write visible)
And   the .tmp file is cleaned up (best-effort try/finally)

Given atomic_writer(path) is used as a context manager
When  an exception is raised inside the `with` block
Then  the final file at `path` is unchanged (the temp write is discarded)

Given tests/unit/test_atomic_io.py exists
When  `uv run pytest tests/unit/test_atomic_io.py -v` runs
Then  exit code is 0
And   12 tests pass

Given tests/property/test_atomic_io_properties.py exists
When  `HYPOTHESIS_PROFILE=ci uv run pytest tests/property/test_atomic_io_properties.py -v` runs
Then  exit code is 0
And   2 property tests pass
```

---

## Shell verification

```bash
# Unit tests
uv run pytest tests/unit/test_atomic_io.py -v
# Must show 12 passing

# Property tests
HYPOTHESIS_PROFILE=ci uv run pytest tests/property/test_atomic_io_properties.py -v --hypothesis-show-statistics
# Must show 2 passing

# Strict typing
uv run mypy --strict src/silentwitness_common/atomic_io.py

# Lint clean
uv run ruff check src/silentwitness_common/atomic_io.py

# File size guard
uv run python .pre-commit-hooks/file-size-guard.py src/silentwitness_common/atomic_io.py

# Behavior smoke — write_json_atomic + append_jsonl_line
uv run python -c "
import tempfile, pathlib, json
from silentwitness_common.atomic_io import write_json_atomic, append_jsonl_line
with tempfile.TemporaryDirectory() as d:
    p = pathlib.Path(d) / 'foo.json'
    write_json_atomic(p, {'a': 1, 'b': 'utf8 é \U0001F600'})
    assert json.loads(p.read_text()) == {'a': 1, 'b': 'utf8 é \U0001F600'}
    j = pathlib.Path(d) / 'foo.jsonl'
    for i in range(3):
        append_jsonl_line(j, json.dumps({'i': i}))
    lines = j.read_text().splitlines()
    assert len(lines) == 3
    assert json.loads(lines[2]) == {'i': 2}
    print('atomic_io smoke ok')
"

# §14 no-mocks check
git diff main...HEAD -- 'src/silentwitness_common/atomic_io.py' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded)" | grep -v "test\|spec"
# Must output nothing
```

---

## Notes for coding agent

- Reference: architecture.md §5.4 (atomic-save pattern verbatim — "1. Write to `cases/<case_id>/report.md.tmp` with `O_CREAT | O_WRONLY | O_TRUNC`. 2. fsync(tmp_fd). 3. os.replace(tmp_path, final_path) (atomic on POSIX). 4. fsync(parent_dir_fd) for the rename durability."), §4.4 (JSONL discipline — fsync after each line, append mode, no long-lived file handles).
- Reference: PRD.md §6 NFR (Reproducibility — atomic-write invariant is what makes the audit trail reproducible across crashes).
- Reference: architecture.md §13 banned patterns: do NOT use `tempfile.mktemp()` (race vulnerability); use `tempfile.mkstemp()` or compose temp paths manually with `<final>.tmp.<pid>.<random8>`.
- The tmp-path convention: `<final>.tmp.<pid>.<8-hex-random>`. The PID + random suffix prevents collisions when two processes/threads write to the same target — each gets its own tmp file, and `os.replace` is the atomic commit point.
- POSIX `os.replace` semantics: atomic when source and target are on the same filesystem. If cross-filesystem (e.g., target is a bind-mount), the operation falls back to copy+delete, which is NOT atomic. The `cases/<case_id>/` directory is always on the same filesystem as its `.tmp` siblings — we never cross filesystems in normal use. Document this in a code comment.
- `_fsync_dir(dir_path)` opens the parent directory as `O_RDONLY` and calls `os.fsync(fd)` on the directory fd. This is required for rename durability — without it, a crash after `os.replace` but before the parent dir's metadata is flushed can leave the new file invisible on remount. Critical for ledger appends.
- Append-mode atomicity caveat: writes ≤ PIPE_BUF (typically 4096 bytes) are atomic at the kernel level on POSIX. JSONL lines for audit entries are typically <2KB — well within. For the rare large entry (e.g., truncated tool output excerpt > 4KB), the line may interleave under contention. The `AuditLogger` in story-audit-logger holds a thread lock for this reason. Document the line-size assumption in the docstring.
- The mode parameter: `write_bytes_atomic(path, data, mode=0o644)`. Use `os.open(tmp_path, O_CREAT|O_WRONLY|O_TRUNC, mode)` then `os.fdopen(fd, "wb")`. The mode bits are masked by umask — chmod after rename to enforce.
- UTF-8 encoding: `write_text_atomic` MUST use `encoding="utf-8"` (no system-locale fallback). Pass `errors="strict"` so any invalid UTF-8 raises rather than silent-replacing.
- Context manager `atomic_writer` — yield a file-like (BinaryIO) bound to the tmp path. On `__exit__` with no exception, flush + fsync + rename + dir-fsync. On `__exit__` with exception, unlink the tmp and re-raise. Caller-friendly for Epic 11's streaming markdown writer.
- DO NOT use `pathlib.Path.write_text` / `write_bytes` directly — they are NOT atomic.
- DO NOT use `shutil.move` — it falls back to copy on cross-FS, which breaks atomicity.
- Library docs to consult via Context7 BEFORE coding:
  - `python os fsync` stdlib (confirm os.fsync(fd) signature in 3.12).
  - `python os.replace` topic `atomic rename POSIX semantics` (the Windows quirk: in 3.3+ replace works on Windows too, with a separate path).
- Pitfall: Windows is NOT a supported runtime (SIFT 2026 is Linux), but tests may run on macOS dev machines. macOS `os.fsync` does NOT guarantee disk persistence (need `fcntl(F_FULLFSYNC)`). For the hackathon we accept Linux semantics; document this in a code comment and do NOT add Mac-specific branching that complicates the code.
