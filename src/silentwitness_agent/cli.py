"""SilentWitness CLI — Typer entry point (Epic 12)."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import shutil
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console

from silentwitness_agent.cli_commands._evidence_types import (
    detect_evidence_type,
    human_size,
    sha256_hex,
)
from silentwitness_agent.config import SilentWitnessConfig, load_config
from silentwitness_agent.report.template import Frontmatter, ReportStatus, dump_frontmatter
from silentwitness_common.atomic_io import write_json_atomic, write_text_atomic
from silentwitness_common.version import __version__ as _sw_version
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import (
    EvidenceContentDriftError,
    EvidenceRegistry,
    EvidenceRegistryError,
)

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
    tree = (
        f"[green]✓[/green] case '{case_id}' initialized at {case_dir}\n"
        "       ├─ audit/        (JSONL tool-call ledger)\n"
        "       ├─ evidence/     (registered symlinks — ro,noexec,nosuid mount)\n"
        "       ├─ report.md     (DRAFT — frontmatter only)\n"
        "       └─ .silentwitness/case.toml"
    )
    out.print(tree, highlight=False)


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


@app.command("register-evidence")
def register_evidence(
    ctx: typer.Context,
    case_id: str = typer.Argument(...),
    path: Path = typer.Argument(..., readable=False),
    dry_run: bool = typer.Option(False, "--dry-run"),
    recursive: bool = typer.Option(False, "--recursive"),
) -> None:
    cli_ctx: _CliCtx = ctx.obj
    out = _console(cli_ctx.no_color)
    err = _console(cli_ctx.no_color, stderr=True)
    t0 = time.monotonic()
    if not path.exists():
        err.print(f"[red]✗[/red] '{path}' does not exist", highlight=False)
        raise typer.Exit(code=1)
    case_dir = _resolve_case_dir(case_id)
    if not case_dir.exists():
        err.print(f"[red]✗[/red] case '{case_id}' not found", highlight=False)
        raise typer.Exit(code=1)
    try:
        candidates = path.rglob("*") if recursive and path.is_dir() else [path]
        files = [p for p in candidates if p.is_file()]
    except PermissionError as exc:
        err.print(f"[red]✗[/red] permission denied traversing '{path}': {exc}", highlight=False)
        raise typer.Exit(code=1) from exc
    except OSError as exc:
        err.print(f"[red]✗[/red] system error traversing '{path}': {exc}", highlight=False)
        raise typer.Exit(code=2) from exc
    if not files:
        hint = (
            " (use --recursive to traverse subdirectories)"
            if path.is_dir() and not recursive
            else ""
        )
        err.print(f"[red]✗[/red] no files found under '{path}'{hint}", highlight=False)
        raise typer.Exit(code=1)
    if dry_run:
        for p in files:
            try:
                digest, _ = sha256_hex(p)
                out.print(
                    f"DRY-RUN sha256:{digest}  {p.name}  ({detect_evidence_type(p)})",
                    highlight=False,
                )
            except PermissionError as exc:
                err.print(f"[red]✗[/red] permission denied: {p.name}: {exc}", highlight=False)
            except OSError as exc:
                err.print(f"[red]✗[/red] system error reading {p.name}: {exc}", highlight=False)
        return
    examiner = _read_case_examiner(case_dir, cli_ctx.config.examiner.name)
    try:
        registry = EvidenceRegistry(case_dir=case_dir)
        audit_log = AuditLogger(case_dir, examiner)
        invocation_audit_id = audit_log.next_audit_id()
    except RuntimeError as exc:
        err.print(f"[red]✗[/red] audit lock conflict for case '{case_id}': {exc}", highlight=False)
        raise typer.Exit(code=2) from exc
    except OSError as exc:
        err.print(
            f"[red]✗[/red] system error initialising case '{case_id}': {exc}", highlight=False
        )
        raise typer.Exit(code=2) from exc
    registered = 0
    failed = 0
    for p in files:
        try:
            record = registry.register(p, detect_evidence_type(p), invocation_audit_id)
            if record.registered_audit_id != invocation_audit_id:
                # Returned record carries the original audit_id → idempotent re-register hit.
                out.print(
                    f"[yellow]⚠[/yellow] already registered (sha256 matches): {p.name}",
                    highlight=False,
                )
            else:
                sha_s = f"{record.sha256[:4]}...{record.sha256[-4:]}"
                out.print(
                    f"[green]✓[/green] registered {p.name}\n"
                    f"       sha256: {sha_s}    size: {human_size(record.size_bytes)}",
                    highlight=False,
                )
            registered += 1
        except EvidenceContentDriftError as exc:
            err.print(
                f"[red]✗[/red] sha256_mismatch_on_reregister: {p.name}: {exc}",
                highlight=False,
            )
            failed += 1
        except (EvidenceRegistryError, PermissionError, OSError) as exc:
            err.print(f"[red]✗[/red] {p.name}: {exc}", highlight=False)
            failed += 1
    result_summary: dict[str, object] = {"registered": registered, "errors": failed}
    try:
        audit_log.emit(
            backend="cli",
            tool="cli.register-evidence",
            params={"case_id": case_id, "paths": [str(p) for p in files], "recursive": recursive},
            result_summary=result_summary,
            result_sha256=hashlib.sha256(
                json.dumps(result_summary, sort_keys=True).encode()
            ).hexdigest(),
            stdout_path=case_dir / "audit" / "cli.jsonl",
            elapsed_ms=(time.monotonic() - t0) * 1000,
            model_used="cli",
        )
    except (OSError, ValueError) as exc:
        err.print(f"[red]✗[/red] system error writing audit entry: {exc}", highlight=False)
        raise typer.Exit(code=2) from exc
    finally:
        try:
            audit_log.close()
        except OSError as close_exc:
            err.print(
                f"[red]✗[/red] system error releasing audit log lock: {close_exc}",
                highlight=False,
            )
    # Partial success exits 0; only an all-failure run is a hard error.
    if failed and not registered:
        raise typer.Exit(code=1)
