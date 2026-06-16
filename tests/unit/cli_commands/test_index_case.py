"""Unit test for the forensics-free path of ``silentwitness index``.

The real targeted-parser + plaso ingest is validated on the Linux box; here we cover
the no-op early return (empty registry), which must work without the forensics extra
installed — the parser stack is imported lazily only once there is something to index."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

from rich.console import Console

from silentwitness_agent.cli_commands.index_case import (
    _print_artifact_failure_summary,
    _print_skip_summary,
    run,
)


def test_run_returns_1_when_nothing_registered(tmp_path: Path) -> None:
    case_dir = tmp_path / "cases" / "c1"
    case_dir.mkdir(parents=True)
    # Empty evidence registry -> nothing prepared to index -> early return 1 before
    # the targeted/plaso parser stack is imported, so this runs anywhere.
    assert run(case_dir, "c1", examiner="examiner", no_color=True) == 1


def test_artifact_failure_summary_keeps_terminal_compact() -> None:
    stream = StringIO()
    console = Console(file=stream, force_terminal=False, color_system=None, width=200)
    failures = [
        ("prefetch", f"bad-{i}.pf", "very long parser internals that belong in audit only")
        for i in range(7)
    ]

    _print_artifact_failure_summary(console, failures)

    output = stream.getvalue()
    assert "7 artifact parser failure(s) recorded" in output
    assert "prefetch=7" in output
    assert "+2 more" in output
    assert "full details in audit" in output
    assert "very long parser internals" not in output


def test_skip_summary_keeps_terminal_compact() -> None:
    stream = StringIO()
    console = Console(file=stream, force_terminal=False, color_system=None, width=200)
    diagnostics = [("evtx", f"Archive-{i}.evtx", {"corrupt_record": 2}) for i in range(6)]

    _print_skip_summary(console, diagnostics)

    output = stream.getvalue()
    assert "12 parser record skip(s) recorded" in output
    assert "evtx=6" in output
    assert "+1 more" in output
    assert "full details in audit" in output
    assert "corrupt_record" not in output
