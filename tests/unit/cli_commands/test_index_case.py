"""Unit test for the plaso-free path of ``silentwitness index``.

The real mount + plaso ingest is validated on the Linux box; here we cover the
no-op early return, which must work without the forensics extra installed."""

from __future__ import annotations

from pathlib import Path

from silentwitness_agent.cli_commands.index_case import run


def test_run_returns_1_when_no_disk_image_registered(tmp_path: Path) -> None:
    case_dir = tmp_path / "cases" / "c1"
    case_dir.mkdir(parents=True)
    # Empty evidence registry -> no disk image -> nothing to index; the mount +
    # plaso stack is never imported, so this runs anywhere.
    assert run(case_dir, "c1", examiner="examiner", no_color=True) == 1
