"""Unit test for the forensics-free path of ``silentwitness index``.

The real targeted-parser + plaso ingest is validated on the Linux box; here we cover
the no-op early return (empty registry), which must work without the forensics extra
installed — the parser stack is imported lazily only once there is something to index."""

from __future__ import annotations

from pathlib import Path

from silentwitness_agent.cli_commands.index_case import run


def test_run_returns_1_when_nothing_registered(tmp_path: Path) -> None:
    case_dir = tmp_path / "cases" / "c1"
    case_dir.mkdir(parents=True)
    # Empty evidence registry -> nothing prepared to index -> early return 1 before
    # the targeted/plaso parser stack is imported, so this runs anywhere.
    assert run(case_dir, "c1", examiner="examiner", no_color=True) == 1
