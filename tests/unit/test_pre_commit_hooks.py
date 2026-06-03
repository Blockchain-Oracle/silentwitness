"""Behavioural tests for the pre-commit hook scripts.

Subprocess-driven against the real scripts under ``.pre-commit-hooks/`` — no
mocks, per architecture §14. The 8 tests map to the BDD criteria in
story-pre-commit-hooks.md:

  1. file-size-guard accepts a 400-LOC .py file.
  2. file-size-guard rejects a 401-LOC .py file with a useful stderr.
  3. file-size-guard skips ``uv.lock`` even when oversized.
  4. file-size-guard skips ``tests/<x>/fixtures/*`` (forensic blobs).
  5. forbidden-paths accepts ``src/silentwitness_mcp/server.py``.
  6. forbidden-paths rejects ``cases/case-001/audit/x.jsonl``.
  7. forbidden-paths rejects ``evidence/raw.E01``.
  8. forbidden-paths honours the ``tests/integration/fixtures/`` carve-out.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FILE_SIZE_GUARD = _REPO_ROOT / ".pre-commit-hooks" / "file-size-guard.py"
_FORBIDDEN_PATHS = _REPO_ROOT / ".pre-commit-hooks" / "forbidden-paths.py"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# file-size-guard
# ---------------------------------------------------------------------------


def test_file_size_guard_accepts_400_loc(tmp_path: Path) -> None:
    target = tmp_path / "exactly_400.py"
    target.write_text("x = 1\n" * 400, encoding="utf-8")
    result = _run(_FILE_SIZE_GUARD, str(target))
    assert result.returncode == 0, f"expected exit 0, got {result.returncode}: {result.stderr}"


def test_file_size_guard_rejects_401_loc(tmp_path: Path) -> None:
    target = tmp_path / "over_by_one.py"
    target.write_text("x = 1\n" * 401, encoding="utf-8")
    result = _run(_FILE_SIZE_GUARD, str(target))
    assert result.returncode == 1, f"expected exit 1, got {result.returncode}: {result.stderr}"
    assert "401" in result.stderr, f"stderr should name the offending count: {result.stderr!r}"
    assert str(target) in result.stderr, "stderr should name the offending file"
    assert (
        "split at a natural module boundary" in result.stderr
    ), "stderr should include the canonical split hint from CICD_SPEC §6.1"


def test_file_size_guard_skips_uv_lock(tmp_path: Path) -> None:
    """``uv.lock`` is in SKIP_PATTERNS — it's auto-generated and routinely >400 LOC."""
    target = tmp_path / "uv.lock"
    target.write_text("entry\n" * 5000, encoding="utf-8")
    result = _run(_FILE_SIZE_GUARD, str(target))
    assert result.returncode == 0, f"uv.lock should have been skipped: {result.stderr}"


def test_file_size_guard_skips_test_fixture_path(tmp_path: Path) -> None:
    """The ``tests/**/fixtures/*`` glob is in SKIP_PATTERNS."""
    fixture_dir = tmp_path / "tests" / "integration" / "fixtures"
    fixture_dir.mkdir(parents=True)
    target = fixture_dir / "huge.py"
    target.write_text("x\n" * 1000, encoding="utf-8")
    # Invoke from tmp_path so the relative path the guard sees matches the SKIP_PATTERNS glob.
    result = subprocess.run(
        [sys.executable, str(_FILE_SIZE_GUARD), "tests/integration/fixtures/huge.py"],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, f"fixture path should have been skipped: {result.stderr}"


# ---------------------------------------------------------------------------
# forbidden-paths
# ---------------------------------------------------------------------------


def test_forbidden_paths_accepts_src_file() -> None:
    result = _run(_FORBIDDEN_PATHS, "src/silentwitness_mcp/server.py")
    assert result.returncode == 0, f"src/ paths must pass: {result.stderr}"


def test_forbidden_paths_rejects_case_audit_jsonl() -> None:
    target = "cases/case-001/audit/foo.jsonl"
    result = _run(_FORBIDDEN_PATHS, target)
    assert result.returncode == 1, f"expected exit 1, got {result.returncode}: {result.stderr}"
    assert target in result.stderr


def test_forbidden_paths_rejects_evidence_file() -> None:
    result = _run(_FORBIDDEN_PATHS, "evidence/raw.E01")
    assert result.returncode == 1
    assert "evidence/raw.E01" in result.stderr


def test_forbidden_paths_honours_integration_fixtures_carveout() -> None:
    """Synthetic case fixtures live under ``tests/integration/fixtures/`` and are allowed."""
    target = "tests/integration/fixtures/cases/sample/audit/x.jsonl"
    result = _run(_FORBIDDEN_PATHS, target)
    assert result.returncode == 0, f"carve-out path was rejected: {result.stderr}"
