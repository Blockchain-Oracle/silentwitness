"""Unit test for the plaso-free path of ``silentwitness index``.

The real plaso ingest is validated on the Linux box; here we cover the no-op
early return, which must work without the forensics extra installed."""

from __future__ import annotations

from pathlib import Path

from silentwitness_agent.cli_commands.index_case import run


def test_run_returns_1_when_nothing_prepared(tmp_path: Path) -> None:
    case_dir = tmp_path / "cases" / "c1"
    case_dir.mkdir(parents=True)
    # No prepared/ dir -> nothing to index, and plaso is never imported.
    assert run(case_dir, "c1", examiner="examiner", no_color=True) == 1


def test_run_returns_1_when_prepared_is_empty(tmp_path: Path) -> None:
    case_dir = tmp_path / "cases" / "c1"
    (case_dir / "prepared").mkdir(parents=True)
    assert run(case_dir, "c1", examiner="examiner", no_color=True) == 1
