"""Integration tests for PdfRenderer against synthetic case directories (>=8 tests).

Skipped entirely on systems without WeasyPrint native libraries (pango/cairo/
gdk-pixbuf/harfbuzz). Those libraries are pre-installed in the project
Dockerfile and on SIFT 2026 (story-docker-baseline).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

# Skip entire module when WeasyPrint native libs are absent. WeasyPrint raises
# OSError (not ImportError) when pango/cairo/gdk-pixbuf/harfbuzz are missing.
try:
    import weasyprint as _weasyprint_check  # noqa: F401
except (ImportError, OSError):
    pytest.skip(
        "WeasyPrint native libs not installed (pango/cairo/gdk-pixbuf/harfbuzz)",
        allow_module_level=True,
    )

from pypdf import PdfReader

from silentwitness_agent.report.pdf import PdfRenderer, PdfRenderResult
from silentwitness_agent.report.template import (
    Frontmatter,
    ReportStatus,
    ReportTemplate,
    dump_frontmatter,
)
from silentwitness_agent.report.verify_links import BrokenVerifyLink

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AUDIT_IDS = ["sift-aj-20260613-007", "sift-aj-20260613-008"]

_BODY_WITH_TWO_REFS = """\
# Incident Report — Case test-001

## Executive Summary

PowerShell ran with -EncodedCommand [verify:F-001/sift-aj-20260613-007].

## Findings

Malware executed via scheduled task [verify:F-002/sift-aj-20260613-008].

## Appendix — Audit

_Audit logs are referenced above via verify-links._
"""


def _make_case_dir(tmp_path: Path, *, broken_ref: bool = False) -> Path:
    """Create a minimal synthetic case directory with report.md and audit/."""
    d = tmp_path / "cases" / "test-001"
    d.mkdir(parents=True)
    audit_dir = d / "audit"
    audit_dir.mkdir()

    (audit_dir / "findings.jsonl").write_text(
        "\n".join(json.dumps({"audit_id": aid, "tool": "vol3"}) for aid in _AUDIT_IDS) + "\n",
        encoding="utf-8",
    )

    body = _BODY_WITH_TWO_REFS
    if broken_ref:
        body = body + "\nBroken [verify:F-003/sift-fake-20260101-999].\n"

    content_hash = ReportTemplate.compute_content_hash(body)
    fm = Frontmatter(
        case_id="test-001",
        examiner="aj",
        status=ReportStatus.DRAFT,
        content_hash=content_hash,
        created_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC),
        silentwitness_version="1.0.0",
        model_used="anthropic:claude-opus-4-7",
    )
    (d / "report.md").write_text(dump_frontmatter(fm) + body, encoding="utf-8")
    return d


# ---------------------------------------------------------------------------
# 1. render() produces a report.pdf file
# ---------------------------------------------------------------------------


def test_render_produces_pdf(tmp_path: Path) -> None:
    case_dir = _make_case_dir(tmp_path)
    PdfRenderer(case_dir).render()
    assert (case_dir / "report.pdf").exists()


# ---------------------------------------------------------------------------
# 2. The PDF starts with valid magic bytes
# ---------------------------------------------------------------------------


def test_render_pdf_magic_bytes(tmp_path: Path) -> None:
    case_dir = _make_case_dir(tmp_path)
    PdfRenderer(case_dir).render()
    assert (case_dir / "report.pdf").read_bytes()[:7] == b"%PDF-1."


# ---------------------------------------------------------------------------
# 3. PdfRenderResult carries correct metadata
# ---------------------------------------------------------------------------


def test_render_result_fields(tmp_path: Path) -> None:
    case_dir = _make_case_dir(tmp_path)
    result = PdfRenderer(case_dir).render()
    assert isinstance(result, PdfRenderResult)
    assert result.bytes_written > 0
    assert result.verify_links_expanded_count == 2
    assert result.title_page_rendered is True


# ---------------------------------------------------------------------------
# 4. PDF has at least 2 pages (title page + body)
# ---------------------------------------------------------------------------


def test_render_page_count(tmp_path: Path) -> None:
    case_dir = _make_case_dir(tmp_path)
    result = PdfRenderer(case_dir).render()
    assert result.page_count >= 2


# ---------------------------------------------------------------------------
# 5. BrokenVerifyLink raised before WeasyPrint writes anything
# ---------------------------------------------------------------------------


def test_broken_verify_link_aborts_render(tmp_path: Path) -> None:
    case_dir = _make_case_dir(tmp_path, broken_ref=True)
    with pytest.raises(BrokenVerifyLink) as exc_info:
        PdfRenderer(case_dir).render()
    assert exc_info.value.audit_id == "sift-fake-20260101-999"
    assert not (case_dir / "report.pdf").exists()


# ---------------------------------------------------------------------------
# 6. _load_stylesheet returns the bundled CSS (non-empty, contains spec tokens)
# ---------------------------------------------------------------------------


def test_load_stylesheet_returns_bundled_css(tmp_path: Path) -> None:
    case_dir = _make_case_dir(tmp_path)
    renderer = PdfRenderer(case_dir)
    css = renderer._load_stylesheet()
    assert len(css) > 100
    assert "A4" in css
    assert "portrait" in css
    assert "#5ba3d0" in css


# ---------------------------------------------------------------------------
# 7. Custom output_path is honored; default path is not created
# ---------------------------------------------------------------------------


def test_custom_output_path(tmp_path: Path) -> None:
    case_dir = _make_case_dir(tmp_path)
    custom = tmp_path / "custom_report.pdf"
    result = PdfRenderer(case_dir).render(output_path=custom)
    assert custom.exists()
    assert result.output_path == custom
    assert not (case_dir / "report.pdf").exists()


# ---------------------------------------------------------------------------
# 8. Custom stylesheet_path is used instead of bundled CSS
# ---------------------------------------------------------------------------


def test_custom_stylesheet_path(tmp_path: Path) -> None:
    case_dir = _make_case_dir(tmp_path)
    custom_css = tmp_path / "custom.css"
    custom_css.write_text("body { font-size: 12pt; }", encoding="utf-8")
    result = PdfRenderer(case_dir, stylesheet_path=custom_css).render()
    assert result.bytes_written > 0


# ---------------------------------------------------------------------------
# 9. Title page contains case_id, examiner, and status (pypdf extraction)
# ---------------------------------------------------------------------------


def test_title_page_text_content(tmp_path: Path) -> None:
    case_dir = _make_case_dir(tmp_path)
    PdfRenderer(case_dir).render()
    reader = PdfReader(case_dir / "report.pdf")
    title_text = reader.pages[0].extract_text() or ""
    assert "test-001" in title_text
    assert "aj" in title_text
    assert "DRAFT" in title_text


# ---------------------------------------------------------------------------
# 10. Body pages contain the expanded verify-link text (pypdf extraction)
# ---------------------------------------------------------------------------


def test_body_pages_contain_verify_ref_text(tmp_path: Path) -> None:
    case_dir = _make_case_dir(tmp_path)
    result = PdfRenderer(case_dir).render()
    reader = PdfReader(case_dir / "report.pdf")
    # Collect text from all pages beyond the title page
    body_text = " ".join(reader.pages[i].extract_text() or "" for i in range(1, len(reader.pages)))
    # expand_for_pdf produces [<sup>verify:F-001/sift-aj-20260613-007</sup>](...)
    # pypdf strips HTML tags — the text "verify:F-001/sift-aj-20260613-007" should survive
    assert "verify:F-001/sift-aj-20260613-007" in body_text
    assert result.verify_links_expanded_count == 2
