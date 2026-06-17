"""Rich progress helpers for the index command."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from silentwitness_mcp.index.ingest_artifacts import ArtifactProgressEvent
from silentwitness_mcp.index.ingest_memory import MemoryPluginEvent


@contextmanager
def index_progress(console: Console) -> Iterator[Progress | None]:
    """Yield a Progress instance for interactive terminals, otherwise ``None``."""
    if not console.is_terminal:
        yield None
        return
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(compact=True),
        console=console,
        transient=False,
    ) as progress:
        yield progress


class IndexProgressTracker:
    """Small adapter from index progress events to Rich tasks."""

    def __init__(self, progress: Progress | None) -> None:
        self._progress = progress
        self._parser_task: TaskID | None = None
        self._plaso_task: TaskID | None = None
        self._memory_task: TaskID | None = None
        self._memory_done = 0
        self._fts_task: TaskID | None = None

    @staticmethod
    def _brief(value: str, *, limit: int = 34) -> str:
        return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"

    def artifact(self, event: ArtifactProgressEvent) -> None:
        if self._progress is None:
            return
        if event.status == "start":
            self._parser_task = self._progress.add_task("targeted parsers", total=event.total)
            return
        if self._parser_task is None:
            return
        name = self._brief(event.name)
        self._progress.update(
            self._parser_task,
            completed=event.completed,
            description=f"targeted parsers [{event.kind}] {name}",
        )

    def start_plaso(self, total: int) -> None:
        if self._progress is not None and total:
            self._plaso_task = self._progress.add_task("plaso super-timeline", total=total)

    def plaso_item(self, name: str) -> None:
        if self._progress is not None and self._plaso_task is not None:
            self._progress.update(
                self._plaso_task,
                description=f"plaso {self._brief(name)}",
            )

    def plaso_done(self) -> None:
        if self._progress is not None and self._plaso_task is not None:
            self._progress.advance(self._plaso_task)

    def start_memory(self, total_plugins: int) -> None:
        if self._progress is not None and total_plugins:
            self._memory_task = self._progress.add_task("vol3 memory plugins", total=total_plugins)

    def memory(self, event: MemoryPluginEvent) -> None:
        if self._progress is None or self._memory_task is None:
            return
        description = f"vol3 {event.short_name}"
        if event.status == "start":
            self._progress.update(self._memory_task, description=f"{description} running")
            return
        self._memory_done += 1
        self._progress.update(
            self._memory_task,
            completed=self._memory_done,
            description=f"{description} {event.status}",
        )

    def start_fts(self) -> None:
        if self._progress is not None:
            self._fts_task = self._progress.add_task("building full-text search index", total=None)

    def finish_fts(self) -> None:
        if self._progress is not None and self._fts_task is not None:
            self._progress.update(
                self._fts_task,
                total=1,
                completed=1,
                description="full-text search index built",
            )


__all__ = ["IndexProgressTracker", "index_progress"]
