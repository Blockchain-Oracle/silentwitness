"""PdfRenderer — WeasyPrint PDF renderer for SilentWitness investigation reports.

WeasyPrint requires native OS libraries (pango, cairo, gdk-pixbuf, harfbuzz).
These are pre-installed in the project Dockerfile (story-docker-baseline).
On a fresh macOS: brew install pango cairo gdk-pixbuf libffi harfbuzz.

First render after process start takes ~2-3s (WeasyPrint font-cache warmup).
Subsequent renders are sub-second.

The PDF is regenerated on every render() call — it is NOT the source of truth.
The Markdown report.md is canonical (architecture §5.4).
"""

from __future__ import annotations

import html as _html_stdlib
import importlib.resources
import logging
from pathlib import Path

import mistune
from pydantic import BaseModel, ConfigDict, Field

from silentwitness_agent.report.template import Frontmatter, parse_frontmatter
from silentwitness_agent.report.verify_links import VerifyLinkRenderer

# Suppress WeasyPrint rendering chatter — CLI owns progress output
logging.getLogger("weasyprint").setLevel(logging.ERROR)

_LOG = logging.getLogger(__name__)
_ASSETS = importlib.resources.files("silentwitness_agent.report.assets")


class PdfRenderResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    output_path: Path
    bytes_written: int = Field(gt=0)
    page_count: int = Field(gt=0)
    title_page_rendered: bool
    verify_links_expanded_count: int = Field(ge=0)


class PdfRenderer:
    """Renders cases/<case_id>/report.md as a PDF via WeasyPrint.

    Every call to render() re-reads report.md and re-renders from scratch.
    The prior report.pdf is replaced atomically only after a successful render.
    """

    def __init__(self, case_dir: Path, *, stylesheet_path: Path | None = None) -> None:
        self._case_dir = case_dir
        self._stylesheet_path = stylesheet_path

    def render(self, *, output_path: Path | None = None) -> PdfRenderResult:
        """Load report.md, expand verify-links, and render to PDF via WeasyPrint.

        Raises BrokenVerifyLink if any [verify:...] ref is unresolvable — no
        partial PDF is written and any existing report.pdf is unchanged.
        Raises ImportError if WeasyPrint native libs are absent (pango/cairo/gdk-pixbuf).
        """
        try:
            import weasyprint
        except (ImportError, OSError) as exc:
            raise ImportError(
                "WeasyPrint native libs not available (pango/cairo/gdk-pixbuf/harfbuzz). "
                "See README §Installation for SIFT/Docker setup instructions."
            ) from exc

        report_md = (self._case_dir / "report.md").read_text(encoding="utf-8")
        fm, body = parse_frontmatter(report_md)

        link_renderer = VerifyLinkRenderer()
        # Validate BEFORE invoking WeasyPrint — BrokenVerifyLink aborts here,
        # leaving any existing report.pdf unchanged.
        link_renderer.validate(body, audit_dir=self._case_dir / "audit")

        expanded_body = link_renderer.expand_for_pdf(body)
        verify_links_expanded_count = len(link_renderer.extract(body))

        markdown = mistune.create_markdown(escape=False, plugins=["table", "url", "strikethrough"])
        body_html: str = markdown(expanded_body)  # type: ignore[assignment]

        title_page_html = self._compose_title_page(fm, fm.case_id)
        css_text = self._load_stylesheet()
        full_html = self._html_wrapper(fm.case_id, title_page_html, body_html)

        css = weasyprint.CSS(string=css_text)
        document = weasyprint.HTML(string=full_html, base_url=str(self._case_dir)).render(
            stylesheets=[css]
        )
        page_count: int = len(document.pages)
        pdf_bytes: bytes = document.write_pdf()

        dest = output_path if output_path is not None else self._case_dir / "report.pdf"
        dest.write_bytes(pdf_bytes)
        bytes_written = len(pdf_bytes)

        _LOG.info("PDF rendered: %s (%d bytes, %d pages)", dest, bytes_written, page_count)
        return PdfRenderResult(
            output_path=dest,
            bytes_written=bytes_written,
            page_count=page_count,
            title_page_rendered=True,
            verify_links_expanded_count=verify_links_expanded_count,
        )

    def _compose_title_page(self, fm: Frontmatter, case_id: str) -> str:
        esc = _html_stdlib.escape
        status_lower = fm.status.value.lower()
        return (
            '<div class="title-page">\n'
            f"  <h1>{esc(case_id)}</h1>\n"
            f'  <p class="meta">Examiner: {esc(fm.examiner)}</p>\n'
            f'  <p class="meta">Created: {esc(str(fm.created_at))}</p>\n'
            f'  <p class="meta">Updated: {esc(str(fm.updated_at))}</p>\n'
            f'  <p class="meta">Model: {esc(fm.model_used)}</p>\n'
            f'  <p class="meta">SilentWitness {esc(fm.silentwitness_version)}</p>\n'
            f'  <span class="status-pill status-pill-{esc(status_lower)}">'
            f"{esc(fm.status.value)}</span>\n"
            f'  <p class="content-hash"><code>{esc(fm.content_hash)}</code></p>\n'
            "</div>\n"
        )

    def _load_stylesheet(self) -> str:
        if self._stylesheet_path is not None:
            return self._stylesheet_path.read_text(encoding="utf-8")
        return (_ASSETS / "report.css").read_text(encoding="utf-8")

    def _html_wrapper(self, case_id: str, title_page_html: str, body_html: str) -> str:
        esc = _html_stdlib.escape
        return (
            "<!DOCTYPE html>\n"
            "<html>\n"
            "<head>\n"
            '  <meta charset="utf-8">\n'
            f"  <title>{esc(case_id)}</title>\n"
            "</head>\n"
            "<body>\n"
            f"{title_page_html}"
            f"{body_html}"
            "</body>\n"
            "</html>\n"
        )


__all__ = ["PdfRenderResult", "PdfRenderer"]
