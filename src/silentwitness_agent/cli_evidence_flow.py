"""Evidence-flow Typer commands split out of the main CLI module."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console

_CASE_ID_ARG = typer.Argument(...)
_PATH_ARG = typer.Argument(..., readable=False)
_DRY_RUN_OPT = typer.Option(False, "--dry-run")
_RECURSIVE_OPT = typer.Option(False, "--recursive")
_AS_TYPE_OPT = typer.Option(
    None,
    "--as",
    help=(
        "Override auto-classification (suffix-based, see _evidence_types._SUFFIX_TYPE). "
        "Useful when a memory dump is named `.raw` (auto-classified as disk_image). "
        "Values: disk_image, memory_dump, evtx, pcap, hive, ids_rules, other."
    ),
)
_HOST_OPT = typer.Option("", "--host", help="Host label stamped on indexed rows (multi-host).")
_MEMORY_PROFILE_OPT = typer.Option(
    "standard",
    "--memory-profile",
    help="Memory indexing depth: standard is fast inventory; deep also runs malfind.",
)
_BASELINE_OPT = typer.Option("protocol-sift", "--baseline")
_OUT_OPT = typer.Option(None, "--out")
_METRICS_OPT = typer.Option("time,pivots,provenance,hallucinations,epistemic", "--metrics")
_RESULTS_DIR_OPT = typer.Option(None, "--results-dir")


def _resolve_case_dir(case_id: str, root: Path | None = None) -> Path:
    if root is None:
        root = Path(os.environ.get("SILENTWITNESS_CASES_DIR") or str(Path.cwd()))
    return root / "cases" / case_id


def _console(no_color: bool, *, stderr: bool = False) -> Console:
    return Console(stderr=stderr, no_color=no_color)


def _read_case_examiner(case_dir: Path, fallback: str) -> str:
    toml_path = case_dir / ".silentwitness" / "case.toml"
    if not toml_path.is_file():
        return fallback
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
        return str(data.get("examiner", fallback))
    except (tomllib.TOMLDecodeError, OSError):
        return fallback


def register_evidence(
    ctx: typer.Context,
    case_id: str = _CASE_ID_ARG,
    path: Path = _PATH_ARG,
    dry_run: bool = _DRY_RUN_OPT,
    recursive: bool = _RECURSIVE_OPT,
    as_type: str | None = _AS_TYPE_OPT,
) -> None:
    from silentwitness_agent.cli_commands.register_evidence import run as _run
    from silentwitness_common.types import EvidenceType

    cli_ctx = ctx.obj
    err = _console(cli_ctx.no_color, stderr=True)
    case_dir = _resolve_case_dir(case_id)
    if not case_dir.exists():
        err.print(f"[red]✗[/red] case '{case_id}' not found", highlight=False)
        raise typer.Exit(code=1)
    override: EvidenceType | None = None
    if as_type is not None:
        try:
            override = EvidenceType(as_type)
        except ValueError:
            allowed = ", ".join(t.value for t in EvidenceType)
            err.print(f"[red]✗[/red] invalid --as '{as_type}'. Allowed: {allowed}", highlight=False)
            raise typer.Exit(code=2) from None
    examiner = _read_case_examiner(case_dir, cli_ctx.config.examiner.name)
    code = _run(
        case_dir,
        case_id,
        path,
        dry_run=dry_run,
        recursive=recursive,
        as_type=override,
        examiner=examiner,
        no_color=cli_ctx.no_color,
    )
    raise typer.Exit(code=code)


def prepare(
    ctx: typer.Context,
    case_id: str = _CASE_ID_ARG,
) -> None:
    """Extract artifacts from registered disk images and decompress memory archives."""
    from silentwitness_agent.cli_commands.prepare import run as _run

    cli_ctx = ctx.obj
    err = _console(cli_ctx.no_color, stderr=True)
    case_dir = _resolve_case_dir(case_id)
    if not case_dir.exists():
        err.print(f"[red]✗[/red] case '{case_id}' not found", highlight=False)
        raise typer.Exit(code=1)
    examiner = _read_case_examiner(case_dir, cli_ctx.config.examiner.name)
    code = _run(case_dir, case_id, examiner=examiner, no_color=cli_ctx.no_color)
    raise typer.Exit(code=code)


def index(
    ctx: typer.Context,
    case_id: str = _CASE_ID_ARG,
    host: str = _HOST_OPT,
    memory_profile: str = _MEMORY_PROFILE_OPT,
) -> None:
    """Parse the prepared artifacts into the case's searchable evidence index."""
    from silentwitness_agent.cli_commands.index_case import run as _run

    cli_ctx = ctx.obj
    err = _console(cli_ctx.no_color, stderr=True)
    case_dir = _resolve_case_dir(case_id)
    if not case_dir.exists():
        err.print(f"[red]✗[/red] case '{case_id}' not found", highlight=False)
        raise typer.Exit(code=1)
    if memory_profile not in {"standard", "deep"}:
        err.print(
            "[red]✗[/red] --memory-profile must be 'standard' or 'deep'",
            highlight=False,
        )
        raise typer.Exit(code=2)
    profile: Literal["standard", "deep"] = "deep" if memory_profile == "deep" else "standard"
    examiner = _read_case_examiner(case_dir, cli_ctx.config.examiner.name)
    code = _run(
        case_dir,
        case_id,
        examiner=examiner,
        host=host,
        no_color=cli_ctx.no_color,
        memory_profile=profile,
    )
    raise typer.Exit(code=code)


def baseline_comparison(
    ctx: typer.Context,
    case_id: str = _CASE_ID_ARG,
    baseline: str = _BASELINE_OPT,
    out: Path | None = _OUT_OPT,
    metrics: str = _METRICS_OPT,
    results_dir: Path | None = _RESULTS_DIR_OPT,
) -> None:
    from silentwitness_agent.cli_commands.baseline_comparison import run as _run

    cli_ctx = ctx.obj
    raise typer.Exit(
        code=_run(
            _resolve_case_dir(case_id),
            case_id,
            baseline_mode=baseline,
            out=out,
            metrics_arg=metrics,
            no_color=cli_ctx.no_color,
            results_dir=results_dir,
        )
    )
