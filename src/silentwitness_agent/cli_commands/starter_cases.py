"""Official starter-case catalog/download commands."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table

from silentwitness_agent.starter_cases.egnyte_share import (
    human_size,
    list_contents,
    open_session,
    resolve_case_root,
    stream_file,
    verify_sidecar,
    walk,
)

app = typer.Typer(no_args_is_help=True, add_completion=False, rich_markup_mode="rich")
_CATALOG_CASE_ARG = typer.Argument(
    None,
    help="Official case folder name. Omit to summarize every case at the share root.",
)
_DOWNLOAD_CASE_ARG = typer.Argument(
    ...,
    help="Official case folder name from `starter-cases catalog`.",
)
_DOWNLOAD_TARGET_ARG = typer.Argument(
    None,
    help="Target directory. Defaults to evidence/<case-slug>.",
)
_DRY_RUN_OPT = typer.Option(False, "--dry-run", help="Print files without downloading bytes.")


def _case_slug(case_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", case_name.strip()).strip("-").lower()
    return slug or "starter-case"


def _close(client: Any) -> None:
    close = getattr(client, "close", None)
    if callable(close):
        close()


def _download_progress(console: Console) -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )


@app.command("catalog")
def catalog(
    ctx: typer.Context,
    case: str | None = _CATALOG_CASE_ARG,
) -> None:
    """Show official starter cases and file contents."""
    no_color = bool(getattr(ctx.obj, "no_color", False))
    out = Console(no_color=no_color)
    err = Console(stderr=True, no_color=no_color)
    client = open_session()
    try:
        root = resolve_case_root(client, case)
        if case is None:
            table = Table(title="Official Find Evil 2026 starter cases")
            table.add_column("Case")
            table.add_column("Files", justify="right")
            table.add_column("Size", justify="right")
            for sub in list_contents(client, root):
                if sub.type != "folder":
                    continue
                sub_size = 0
                sub_files = 0
                for entry in walk(client, sub.path):
                    sub_size += entry.size or 0
                    sub_files += 1
                table.add_row(sub.name, str(sub_files), human_size(sub_size))
            out.print(table)
            return

        table = Table(title=root)
        table.add_column("Size", justify="right")
        table.add_column("Path")
        total_size = 0
        file_count = 0
        for entry in walk(client, root):
            total_size += entry.size or 0
            file_count += 1
            table.add_row(human_size(entry.size), entry.path)
        out.print(table)
        out.print(f"Total: {file_count} files, {human_size(total_size)}", highlight=False)
    except SystemExit as exc:
        err.print(f"[red]✗[/red] {exc}", highlight=False)
        raise typer.Exit(code=1) from exc
    finally:
        _close(client)


@app.command("download")
def download(
    ctx: typer.Context,
    case: str = _DOWNLOAD_CASE_ARG,
    target: Path | None = _DOWNLOAD_TARGET_ARG,
    dry_run: bool = _DRY_RUN_OPT,
) -> None:
    """Download an official starter case with resumable SHA256 sidecars."""
    no_color = bool(getattr(ctx.obj, "no_color", False))
    out = Console(no_color=no_color)
    err = Console(stderr=True, no_color=no_color)
    client = open_session()
    try:
        root = resolve_case_root(client, case)
        target_root = (target or Path("evidence") / _case_slug(case)).resolve()
        target_root.mkdir(parents=True, exist_ok=True)
        out.print(f"downloading {root} -> {target_root}", highlight=False)
        total_size = 0
        file_count = 0
        with _download_progress(err) as progress:
            for entry in walk(client, root):
                rel = entry.path[len(root) :].lstrip("/")
                destination = target_root / rel
                total_size += entry.size or 0
                file_count += 1
                if dry_run:
                    out.print(f"DRY  {human_size(entry.size):>10}  {destination}", highlight=False)
                    continue
                if (
                    destination.exists()
                    and entry.size is not None
                    and destination.stat().st_size == entry.size
                    and verify_sidecar(destination)
                ):
                    out.print(
                        f"SKIP {human_size(entry.size):>10}  {destination}  (sha256 verified)",
                        highlight=False,
                    )
                    continue
                if (
                    destination.exists()
                    and entry.size is not None
                    and destination.stat().st_size == entry.size
                ):
                    err.print(
                        f"REDO {human_size(entry.size):>10}  {destination}  (sha256 mismatch)",
                        highlight=False,
                    )
                    destination.unlink()
                part = destination.with_suffix(destination.suffix + ".part")
                completed = part.stat().st_size if part.exists() else 0
                out.print(f"GET  {human_size(entry.size):>10}  {destination}", highlight=False)
                task_id = progress.add_task(
                    destination.name,
                    total=entry.size,
                    completed=completed,
                )
                progress.refresh()

                def _update(done: int, total: int | None, task_id: Any = task_id) -> None:
                    progress.update(task_id, completed=done, total=total)

                digest = stream_file(client, entry, destination, progress=_update)
                progress.update(task_id, completed=entry.size or completed)
                out.print(
                    f"OK   {human_size(entry.size):>10}  {destination}  sha256={digest[:12]}...",
                    highlight=False,
                )
        out.print(f"Done: {file_count} files, {human_size(total_size)}", highlight=False)
    except SystemExit as exc:
        err.print(f"[red]✗[/red] {exc}", highlight=False)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        err.print(f"[red]✗[/red] starter-case download failed: {exc}", highlight=False)
        raise typer.Exit(code=2) from exc
    finally:
        _close(client)


__all__ = ["app", "catalog", "download"]
