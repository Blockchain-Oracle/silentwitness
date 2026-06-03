"""Behavioural tests for the pre-commit hook scripts.

Subprocess-driven against the real scripts under ``.pre-commit-hooks/`` — no
mocks, per architecture §14.

Coverage:
  * The pytest-targeted BDD criteria from story-pre-commit-hooks.md (the
    five behavioural Givens: 400-LOC pass, 401-LOC fail, cases/.../audit
    reject, tests/integration/fixtures/ carve-out, src/ accept).
  * Defensive coverage of SKIP_PATTERNS and FORBIDDEN_PREFIXES branches the
    story doesn't BDD-test (``uv.lock`` skip, fixture-glob skip, ``evidence/``
    reject, ``var/lib/silentwitness/`` reject, ``cases/*/report.md`` reject).
  * Regression tests for the silent-failure surface that PR-89 review
    found: deep ``cases/**`` paths bypassing the §6.2 fnmatch globs, and
    leading-``./`` paths bypassing both the forbidden check and the
    carve-out asymmetrically.

The ``pre-commit install`` / ``pre-commit run --all-files`` / conventional-
commit accept-reject BDDs are covered by the story's Shell verification
block — those require a real git repo + installed hook chain and aren't
pytest's domain.
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
    assert "split at a natural module boundary" in result.stderr, (
        "stderr should include the canonical split hint from CICD_SPEC §6.1"
    )


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


def test_forbidden_paths_rejects_var_lib_ledger() -> None:
    """``var/lib/silentwitness/*`` is one of three runtime-only roots in §6.2."""
    target = "var/lib/silentwitness/ledger.jsonl"
    result = _run(_FORBIDDEN_PATHS, target)
    assert result.returncode == 1
    assert target in result.stderr


def test_forbidden_paths_rejects_case_report() -> None:
    """``cases/<id>/report.md`` is forbidden — it's drafted at runtime, never committed."""
    target = "cases/case-001/report.md"
    result = _run(_FORBIDDEN_PATHS, target)
    assert result.returncode == 1
    assert target in result.stderr


def test_forbidden_paths_rejects_deep_cases_path() -> None:
    """Regression for the §6.2 fnmatch hole — deep ``cases/**`` paths must NOT slip through.

    The verbatim §6.2 patterns ``cases/*`` / ``cases/*/*`` only match 1-2 segments
    after ``cases/``. A path like ``cases/case-001/notes/analyst-scratch.md``
    evaded EVERY §6.2 pattern in the original silent-failure surface.
    """
    target = "cases/case-001/notes/analyst-scratch.md"
    result = _run(_FORBIDDEN_PATHS, target)
    assert result.returncode == 1, f"deep cases path silently passed: {result.stderr}"
    assert target in result.stderr


def test_forbidden_paths_normalises_dot_slash_prefix() -> None:
    """Regression for the leading-``./`` bypass.

    ``./cases/case-001/audit/foo.jsonl`` used to evade both the forbidden check
    AND the carve-out asymmetrically because ``str.startswith`` was applied
    raw. Normalisation now strips the prefix before either check.
    """
    target = "./cases/case-001/audit/foo.jsonl"
    result = _run(_FORBIDDEN_PATHS, target)
    assert result.returncode == 1, f"./ prefix slipped past gate: {result.stderr}"
    assert "cases/case-001/audit/foo.jsonl" in result.stderr


def test_forbidden_paths_rejects_absolute_path() -> None:
    """Regression for round-2 finding A: absolute paths used to silently PASS.

    ``/abs/path/cases/x`` would not start with ``cases/`` after PurePosixPath
    conversion, so the prefix match returned False → silent allow on what is
    very likely an attempt to commit a real case path. Gate now exits 2 (gate
    broken: pre-commit doesn't emit absolute paths).
    """
    target = "/abs/path/cases/case-001/audit/x.jsonl"
    result = _run(_FORBIDDEN_PATHS, target)
    assert result.returncode == 2, f"absolute path slipped past gate: {result.stderr}"
    assert "ABSOLUTE PATH" in result.stderr


def test_forbidden_paths_normalises_backslash_separators() -> None:
    """Regression for round-2 finding A2: Windows-style backslash paths used to slip.

    ``cases\\foo\\x.txt`` would not start with ``cases/`` (PurePosixPath
    preserves backslashes literally), so the prefix match returned False →
    silent allow. Gate now normalises ``\\`` → ``/`` before the match.
    """
    target = "cases\\case-001\\audit\\x.jsonl"
    result = _run(_FORBIDDEN_PATHS, target)
    assert result.returncode == 1, f"backslash path slipped past gate: {result.stderr}"


def test_forbidden_paths_handles_empty_arg() -> None:
    """Regression for round-2 finding A3: empty-string arg should not blow up.

    Pre-commit shouldn't pass empty strings, but if it ever does, the script
    must not raise — it should treat the arg as out-of-scope and exit 0.
    """
    result = _run(_FORBIDDEN_PATHS, "")
    assert result.returncode == 0
