"""SilentWitness CLI — Typer entry point (Epic 12)."""

from __future__ import annotations

import dataclasses
import hashlib
import os
import secrets
import shutil
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console

from silentwitness_agent.config import SilentWitnessConfig, load_config
from silentwitness_agent.report.template import Frontmatter, ReportStatus, dump_frontmatter
from silentwitness_common.atomic_io import write_json_atomic, write_text_atomic
from silentwitness_common.version import __version__ as _sw_version
from silentwitness_mcp.audit.logger import AuditLogger

app = typer.Typer(no_args_is_help=True, add_completion=False, rich_markup_mode="rich")


@dataclasses.dataclass(frozen=True, slots=True)
class _CliCtx:
    config: SilentWitnessConfig
    no_color: bool
    quiet: bool
    debug: bool


@app.callback()
def _root(
    ctx: typer.Context,
    config_file: Path | None = typer.Option(None, "--config-file", exists=True, dir_okay=False),
    no_color: bool = typer.Option(False, "--no-color"),
    quiet: bool = typer.Option(False, "--quiet"),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    ctx.ensure_object(dict)
    try:
        config = load_config(config_file)
    except ValueError as exc:
        Console(stderr=True, no_color=no_color).print(
            f"[red]✗[/red] system error: {exc}", highlight=False
        )
        raise typer.Exit(code=2) from exc
    ctx.obj = _CliCtx(config, no_color, quiet, debug)


def _resolve_case_dir(case_id: str, root: Path | None = None) -> Path:
    if root is None:
        root = Path(os.environ.get("SILENTWITNESS_CASES_DIR") or str(Path.cwd()))
    return root / "cases" / case_id


def _console(no_color: bool, *, stderr: bool = False) -> Console:
    return Console(stderr=stderr, no_color=no_color)


@app.command("init")
def init(
    ctx: typer.Context,
    case_id: str = typer.Argument(...),
    examiner: str = typer.Option(
        default_factory=lambda: os.environ.get("USER", "examiner"),
    ),
    model: str | None = typer.Option(None, "--model"),
    force: bool = typer.Option(False, "--force"),
    no_mount: bool = typer.Option(False, "--no-mount", hidden=True),
) -> None:
    cli_ctx: _CliCtx = ctx.obj
    out = _console(cli_ctx.no_color)
    err = _console(cli_ctx.no_color, stderr=True)
    if cli_ctx.debug:
        err.print(f"model.default = {cli_ctx.config.model.default}", highlight=False)
    case_dir = _resolve_case_dir(case_id)
    if case_dir.exists():
        if not force:
            err.print(f"[red]✗[/red] case '{case_id}' already exists", highlight=False)
            raise typer.Exit(code=1)
        for item in case_dir.iterdir():
            if item.name != "audit":
                shutil.rmtree(item) if item.is_dir() else item.unlink()
    try:
        case_dir.mkdir(parents=True, mode=0o755, exist_ok=True)
        for sub in ("audit", "evidence", ".tool-output", ".silentwitness"):
            (case_dir / sub).mkdir(mode=0o755, exist_ok=True)
        write_json_atomic(case_dir / "evidence.json", {"records": [], "schema_version": 1})
        now = datetime.now(UTC)
        fm = Frontmatter(
            case_id=case_id,
            examiner=examiner,
            status=ReportStatus.DRAFT,
            content_hash="sha256:" + "0" * 64,
            created_at=now,
            updated_at=now,
            silentwitness_version=_sw_version,
            model_used=model or cli_ctx.config.model.default,
        )
        write_text_atomic(case_dir / "report.md", dump_frontmatter(fm))
        (case_dir / ".silentwitness" / "case.toml").write_text(
            f'case_id = "{case_id}"\nexaminer = "{examiner}"\n', encoding="utf-8"
        )
        # Per-case HMAC salt for the approval ledger. Without this, `approve`
        # fails CASE_SALT_MISSING and no finding can ever be signed/approved.
        case_yaml = case_dir / "CASE.yaml"
        if not case_yaml.exists():
            case_yaml.write_text(f"salt_hex: {secrets.token_hex(32)}\n", encoding="utf-8")
    except (PermissionError, OSError) as exc:
        err.print(f"[red]✗[/red] system error: {exc}", highlight=False)
        raise typer.Exit(code=2) from exc
    t0 = time.monotonic()
    audit_log = AuditLogger(case_dir, examiner)
    try:
        audit_log.emit(
            backend="cli",
            tool="cli.init",
            params={"case_id": case_id, "examiner": examiner, "force": force},
            result_summary={"status": "ok"},
            result_sha256=hashlib.sha256(b"").hexdigest(),
            stdout_path=case_dir / "audit" / "cli.jsonl",
            elapsed_ms=(time.monotonic() - t0) * 1000,
            model_used="cli",
        )
    except OSError as exc:
        err.print(f"[red]✗[/red] system error writing audit entry: {exc}", highlight=False)
        raise typer.Exit(code=2) from exc
    finally:
        audit_log.close()
    out.print(
        f"[green]✓[/green] case '{case_id}' initialized at {case_dir}\n"
        "       ├─ audit/        (JSONL tool-call ledger)\n"
        "       ├─ evidence/     (registered symlinks — ro,noexec,nosuid mount)\n"
        "       ├─ report.md     (DRAFT — frontmatter only)\n"
        "       └─ .silentwitness/case.toml",
        highlight=False,
    )


def _read_case_examiner(case_dir: Path, fallback: str) -> str:
    """Return the examiner slug stored in case.toml; falls back on read/parse failure."""
    toml_path = case_dir / ".silentwitness" / "case.toml"
    if not toml_path.is_file():
        return fallback
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
        return str(data.get("examiner", fallback))
    except (tomllib.TOMLDecodeError, OSError):
        return fallback


@app.command("investigate")
def investigate(
    ctx: typer.Context,
    case_id: str = typer.Argument(...),
    model: str | None = typer.Option(None, "--model"),
    max_iterations: int = typer.Option(50, "--max-iterations"),
    max_tokens: int = typer.Option(800_000, "--max-tokens"),
    specialist: list[str] | None = typer.Option(None, "--specialist"),
    resume: bool = typer.Option(False, "--resume"),
    no_hud: bool = typer.Option(False, "--no-hud"),
    hud: bool = typer.Option(False, "--hud"),
) -> None:
    from silentwitness_agent.cli_commands.investigate import run as _run

    cli_ctx: _CliCtx = ctx.obj
    _run(
        case_id,
        cli_ctx.config,
        cli_ctx.no_color,
        cli_ctx.quiet,
        cli_ctx.debug,
        model=model,
        max_iterations=max_iterations,
        max_tokens=max_tokens,
        no_hud=no_hud,
        hud=hud,
        resume=resume,
    )


@app.command("status")
def status(
    ctx: typer.Context,
    case_id: str = typer.Argument(...),
    json_out: bool = typer.Option(False, "--json"),
    watch: bool = typer.Option(False, "--watch"),
    full: bool = typer.Option(False, "--full"),
) -> None:
    from silentwitness_agent.cli_commands.status import render as _render

    cli_ctx: _CliCtx = ctx.obj
    err = Console(stderr=True, no_color=cli_ctx.no_color)
    case_dir = _resolve_case_dir(case_id)
    if not case_dir.exists():
        err.print(f"[red]✗[/red] case '{case_id}' not found", highlight=False)
        raise typer.Exit(code=1)
    code = _render(
        case_dir,
        case_id,
        json_out=json_out,
        watch=watch,
        full=full,
        no_color=cli_ctx.no_color,
    )
    raise typer.Exit(code=code)


@app.command("review")
def review(
    ctx: typer.Context,
    case_id: str = typer.Argument(...),
    finding_id: str | None = typer.Option(None, "--finding-id", "-f"),
    status_filter: str = typer.Option("DRAFT", "--status"),
    non_interactive: bool = typer.Option(False, "--non-interactive"),
) -> None:
    from silentwitness_agent.cli_commands.review import run as _run

    cli_ctx: _CliCtx = ctx.obj
    err = Console(stderr=True, no_color=cli_ctx.no_color)
    case_dir = _resolve_case_dir(case_id)
    if not case_dir.exists():
        err.print(f"[red]✗[/red] case '{case_id}' not found", highlight=False)
        raise typer.Exit(code=1)
    examiner = _read_case_examiner(case_dir, fallback=os.environ.get("USER", "examiner"))
    code = _run(
        case_dir,
        case_id,
        finding_id,
        status_filter,
        non_interactive=non_interactive,
        no_color=cli_ctx.no_color,
        examiner=examiner,
    )
    raise typer.Exit(code=code)


@app.command("approve")
def approve(
    ctx: typer.Context,
    case_id: str = typer.Argument(...),
    finding_id: str = typer.Argument(...),
    note: str | None = typer.Option(None, "--note"),
    ledger: Path | None = typer.Option(None, "--ledger"),
) -> None:
    from silentwitness_agent.cli_commands.approve import (
        _DEFAULT_LEDGER_DIR,
        run as _run,
    )

    cli_ctx: _CliCtx = ctx.obj
    err = Console(stderr=True, no_color=cli_ctx.no_color)
    case_dir = _resolve_case_dir(case_id)
    if not case_dir.exists():
        err.print(f"[red]✗[/red] case '{case_id}' not found", highlight=False)
        raise typer.Exit(code=1)
    examiner = _read_case_examiner(case_dir, fallback=os.environ.get("USER", "examiner"))
    code = _run(
        case_dir,
        case_id,
        finding_id,
        ledger_dir=ledger if ledger is not None else _DEFAULT_LEDGER_DIR,
        note=note,
        no_color=cli_ctx.no_color,
        examiner=examiner,
    )
    raise typer.Exit(code=code)


@app.command("verify")
def verify(
    ctx: typer.Context,
    case_id: str = typer.Argument(...),
    ledger: Path | None = typer.Option(None, "--ledger"),
    strict: bool = typer.Option(False, "--strict"),
) -> None:
    from silentwitness_agent.cli_commands.verify import (
        _DEFAULT_LEDGER_DIR,
        run as _run,
    )

    cli_ctx: _CliCtx = ctx.obj
    err = Console(stderr=True, no_color=cli_ctx.no_color)
    case_dir = _resolve_case_dir(case_id)
    if not case_dir.exists():
        err.print(f"[red]✗[/red] case '{case_id}' not found", highlight=False)
        raise typer.Exit(code=1)
    examiner = _read_case_examiner(case_dir, fallback=os.environ.get("USER", "examiner"))
    code = _run(
        case_dir,
        case_id,
        ledger_dir=ledger if ledger is not None else _DEFAULT_LEDGER_DIR,
        strict=strict,
        no_color=cli_ctx.no_color,
        examiner=examiner,
    )
    raise typer.Exit(code=code)


@app.command("export")
def export(
    ctx: typer.Context,
    case_id: str = typer.Argument(...),
    pdf: bool = typer.Option(False, "--pdf"),
    md: bool = typer.Option(False, "--md"),
    ioc_format: str = typer.Option("csv", "--ioc-format"),
    out: Path | None = typer.Option(None, "--out"),
) -> None:
    from silentwitness_agent.cli_commands.export import run as _run

    cli_ctx: _CliCtx = ctx.obj
    err = _console(cli_ctx.no_color, stderr=True)
    case_dir = _resolve_case_dir(case_id)
    if not case_dir.exists():
        err.print(f"[red]✗[/red] case '{case_id}' not found", highlight=False)
        raise typer.Exit(code=1)
    code = _run(
        case_dir,
        case_id,
        pdf=pdf,
        md=md,
        out=out,
        ioc_format=ioc_format,
        no_color=cli_ctx.no_color,
    )
    raise typer.Exit(code=code)


@app.command("install")
def install(
    ctx: typer.Context,
    claude_code: bool = typer.Option(False, "--claude-code"),
    cursor: bool = typer.Option(False, "--cursor"),
    continue_ide: bool = typer.Option(False, "--continue"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    from silentwitness_agent.cli_commands.install import run as _run

    cli_ctx: _CliCtx = ctx.obj
    code = _run(
        claude_code=claude_code,
        cursor=cursor,
        continue_ide=continue_ide,
        dry_run=dry_run,
        force=force,
        no_color=cli_ctx.no_color,
    )
    raise typer.Exit(code=code)


@app.command("audit-hook", hidden=True)
def audit_hook() -> None:
    """PostToolUse hook called by Claude Code after every Bash invocation.

    Reads the hook payload from stdin. Full provenance logging (writing to
    cases/<id>/audit/claude-code.jsonl) is implemented in story-cli-audit-hook.
    This stub ensures the hook exits 0 so Claude Code does not abort Bash calls.
    """
    import sys

    sys.stdin.read()


@app.command("register-evidence")
def register_evidence(
    ctx: typer.Context,
    case_id: str = typer.Argument(...),
    path: Path = typer.Argument(..., readable=False),
    dry_run: bool = typer.Option(False, "--dry-run"),
    recursive: bool = typer.Option(False, "--recursive"),
) -> None:
    from silentwitness_agent.cli_commands.register_evidence import run as _run

    cli_ctx: _CliCtx = ctx.obj
    err = _console(cli_ctx.no_color, stderr=True)
    case_dir = _resolve_case_dir(case_id)
    if not case_dir.exists():
        err.print(f"[red]✗[/red] case '{case_id}' not found", highlight=False)
        raise typer.Exit(code=1)
    examiner = _read_case_examiner(case_dir, cli_ctx.config.examiner.name)
    code = _run(
        case_dir,
        case_id,
        path,
        dry_run=dry_run,
        recursive=recursive,
        examiner=examiner,
        no_color=cli_ctx.no_color,
    )
    raise typer.Exit(code=code)


@app.command("prepare")
def prepare(
    ctx: typer.Context,
    case_id: str = typer.Argument(...),
) -> None:
    """Extract artifacts from registered disk images and decompress memory archives."""
    from silentwitness_agent.cli_commands.prepare import run as _run

    cli_ctx: _CliCtx = ctx.obj
    err = _console(cli_ctx.no_color, stderr=True)
    case_dir = _resolve_case_dir(case_id)
    if not case_dir.exists():
        err.print(f"[red]✗[/red] case '{case_id}' not found", highlight=False)
        raise typer.Exit(code=1)
    examiner = _read_case_examiner(case_dir, cli_ctx.config.examiner.name)
    code = _run(case_dir, case_id, examiner=examiner, no_color=cli_ctx.no_color)
    raise typer.Exit(code=code)


@app.command("index")
def index(
    ctx: typer.Context,
    case_id: str = typer.Argument(...),
    host: str = typer.Option("", "--host", help="Host label stamped on indexed rows (multi-host)."),
) -> None:
    """Parse the prepared artifacts into the case's searchable evidence index."""
    from silentwitness_agent.cli_commands.index_case import run as _run

    cli_ctx: _CliCtx = ctx.obj
    err = _console(cli_ctx.no_color, stderr=True)
    case_dir = _resolve_case_dir(case_id)
    if not case_dir.exists():
        err.print(f"[red]✗[/red] case '{case_id}' not found", highlight=False)
        raise typer.Exit(code=1)
    examiner = _read_case_examiner(case_dir, cli_ctx.config.examiner.name)
    code = _run(case_dir, case_id, examiner=examiner, host=host, no_color=cli_ctx.no_color)
    raise typer.Exit(code=code)


@app.command("baseline-comparison")
def baseline_comparison(
    ctx: typer.Context,
    case_id: str = typer.Argument(...),
    baseline: str = typer.Option("protocol-sift", "--baseline"),
    out: Path | None = typer.Option(None, "--out"),
    metrics: str = typer.Option("time,pivots,provenance,hallucinations,epistemic", "--metrics"),
    results_dir: Path | None = typer.Option(None, "--results-dir"),
) -> None:
    from silentwitness_agent.cli_commands.baseline_comparison import run as _run

    cli_ctx: _CliCtx = ctx.obj
    # fmt: off
    raise typer.Exit(code=_run(
        _resolve_case_dir(case_id), case_id, baseline_mode=baseline, out=out,
        metrics_arg=metrics, no_color=cli_ctx.no_color, results_dir=results_dir,
    ))
    # fmt: on
