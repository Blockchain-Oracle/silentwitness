"""export command — emit report path and optionally render PDF via WeasyPrint."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from silentwitness_agent.report.pdf import PdfRenderer
from silentwitness_agent.report.template import parse_frontmatter
from silentwitness_agent.report.verify_links import BrokenVerifyLink
from silentwitness_agent.report.writer import ReportWriter
from silentwitness_common.version import __version__ as sw_version

_IOC_EXTENSIONS: dict[str, str] = {
    "csv": "iocs.csv",
    "stix": "iocs.stix.json",
    "misp": "iocs.misp.json",
    "openioc": "iocs.openioc.xml",
}


def _emit_iocs(
    case_dir: Path,
    ioc_format: str,
    *,
    err: Console,
) -> None:
    ext = _IOC_EXTENSIONS.get(ioc_format)
    if ext is None:
        err.print(
            f"[yellow]⚠[/yellow] unknown --ioc-format {ioc_format!r}; "
            f"valid values: {', '.join(_IOC_EXTENSIONS)}",
            highlight=False,
        )
        return
    try:
        import importlib

        _mod = importlib.import_module("silentwitness_agent.report.ioc_export")
        _mod.export_iocs(case_dir, ioc_format, case_dir / ext)
    except ImportError:
        err.print(
            f"[yellow]⚠[/yellow] IOC export not yet available; skipping {ext} sidecar",
            highlight=False,
        )
    except Exception as exc:
        err.print(f"[yellow]⚠[/yellow] IOC export failed: {exc}", highlight=False)


def _render_report_md(case_dir: Path, *, err: Console) -> bool:
    report_md = case_dir / "report.md"
    examiner = "examiner"
    model_used = "unknown"
    try:
        frontmatter, _ = parse_frontmatter(report_md.read_text(encoding="utf-8"))
        examiner = frontmatter.examiner or examiner
        model_used = frontmatter.model_used or model_used
    except (OSError, ValueError):
        err.print("[yellow]⚠[/yellow] report.md frontmatter unreadable; using defaults")
    try:
        ReportWriter(
            case_dir,
            examiner=examiner,
            model_used=model_used,
            silentwitness_version=sw_version,
        ).render()
        return True
    except Exception as exc:
        err.print(f"[red]✗[/red] report.md render failed: {exc}", highlight=False)
        return False


def run(
    case_dir: Path,
    case_id: str,
    *,
    pdf: bool,
    md: bool,
    out: Path | None,
    ioc_format: str | None,
    no_color: bool,
) -> int:
    err = Console(stderr=True, no_color=no_color)

    # Flag conflict check.
    if pdf and md:
        err.print("[red]✗[/red] --pdf and --md are mutually exclusive", highlight=False)
        return 1

    report_md = case_dir / "report.md"
    if not report_md.exists():
        err.print(
            "[red]✗[/red] report.md not generated; run `silentwitness investigate` first",
            highlight=False,
        )
        return 2

    if out is not None and not pdf:
        err.print("[yellow]⚠[/yellow] --out ignored in --md mode", highlight=False)

    if not pdf:
        if not _render_report_md(case_dir, err=err):
            return 2
        if ioc_format is not None:
            _emit_iocs(case_dir, ioc_format, err=err)
        print(str(report_md.resolve()))
        return 0

    # --pdf mode: render via WeasyPrint.
    output_path = out if out is not None else case_dir / "report.pdf"
    renderer = PdfRenderer(case_dir)
    try:
        from rich.progress import Progress, SpinnerColumn, TextColumn

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=err,
            transient=True,
        ) as progress:
            progress.add_task("Rendering PDF…", total=None)
            result = renderer.render(output_path=output_path)
    except ImportError as exc:
        err.print(
            f"[red]✗[/red] WeasyPrint not installed; install with: uv sync --extra pdf\n  ({exc})",
            highlight=False,
        )
        return 2
    except FileNotFoundError:
        err.print(
            "[red]✗[/red] report.md not generated; run `silentwitness investigate` first",
            highlight=False,
        )
        return 2
    except BrokenVerifyLink as exc:
        err.print(
            f"[red]✗[/red] PDF render failed: broken verify-link in report.md — "
            f"{exc}. Re-run `silentwitness verify` or `silentwitness investigate --resume`.",
            highlight=False,
        )
        return 2
    except Exception as exc:
        err.print(f"[red]✗[/red] PDF render failed: {exc}", highlight=False)
        return 2

    err.print(
        f"[green]✓[/green] PDF rendered to {result.output_path} "
        f"({result.page_count} pages, {result.bytes_written:,} bytes)",
        highlight=False,
    )
    if ioc_format is not None:
        _emit_iocs(case_dir, ioc_format, err=err)
    print(str(result.output_path.resolve()))
    return 0
