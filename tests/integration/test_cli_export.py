"""Integration tests for `silentwitness export` — ≥8 BDD scenarios."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from silentwitness_agent.cli import app
from silentwitness_agent.report.pdf import PdfRenderResult
from silentwitness_agent.report.template import ReportStatus, parse_frontmatter
from silentwitness_agent.report.verify_links import BrokenVerifyLink
from tests.integration._helpers_status import init_case

runner = CliRunner()


def _make_case(tmp_path: Path, case_id: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    return init_case(tmp_path, case_id, monkeypatch)


def _fake_render_result(output_path: Path) -> PdfRenderResult:
    content = b"%PDF-1.4 minimal-test-pdf"
    output_path.write_bytes(content)
    return PdfRenderResult(
        output_path=output_path,
        bytes_written=len(content),
        page_count=1,
        verify_links_expanded_count=0,
    )


# ---------------------------------------------------------------------------
# 1. Default mode (no flags) prints report.md path, exit 0
# ---------------------------------------------------------------------------


def test_export_md_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Default export (no --pdf/--md) emits report.md absolute path, exit 0."""
    case_dir = _make_case(tmp_path, "mr-exp-001", monkeypatch)
    result = runner.invoke(app, ["export", "mr-exp-001"], catch_exceptions=False)
    assert result.exit_code == 0
    expected = str((case_dir / "report.md").resolve())
    assert expected in result.output
    assert "IOC export" not in result.output


# ---------------------------------------------------------------------------
# 2. Explicit --md flag emits report.md path
# ---------------------------------------------------------------------------


def test_export_md_explicit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit --md emits report.md path and exits 0."""
    case_dir = _make_case(tmp_path, "mr-exp-002", monkeypatch)
    result = runner.invoke(app, ["export", "mr-exp-002", "--md"], catch_exceptions=False)
    assert result.exit_code == 0
    assert str((case_dir / "report.md").resolve()) in result.output
    assert "IOC export" not in result.output


def test_export_md_rerenders_report_status_from_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Approved findings should refresh stale DRAFT frontmatter during export."""
    case_dir = _make_case(tmp_path, "mr-exp-reviewed-001", monkeypatch)
    records = [
        {
            "observation_id": "O-001",
            "text": "Evidence text",
            "audit_ids": ["sift-001"],
            "interpretations": [
                {
                    "interpretation_id": "I-001",
                    "text": "Approved interpretation",
                    "confidence": "HIGH",
                }
            ],
        },
        {
            "finding_id": "F-001",
            "observation_id": "O-001",
            "interpretation_id": "I-001",
            "status": "APPROVED",
        },
    ]
    (case_dir / "findings.json").write_text(json.dumps(records), encoding="utf-8")

    result = runner.invoke(app, ["export", "mr-exp-reviewed-001", "--md"], catch_exceptions=False)

    assert result.exit_code == 0
    frontmatter, _ = parse_frontmatter((case_dir / "report.md").read_text(encoding="utf-8"))
    assert frontmatter.status == ReportStatus.REVIEWED


# ---------------------------------------------------------------------------
# 3. --pdf renders PDF and prints output path (monkeypatched renderer)
# ---------------------------------------------------------------------------


def test_export_pdf_renders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--pdf mode calls PdfRenderer.render and prints the PDF path, exit 0."""
    case_dir = _make_case(tmp_path, "mr-exp-003", monkeypatch)
    expected_pdf = case_dir / "report.pdf"

    def _fake_render(self: object, *, output_path: Path | None = None) -> PdfRenderResult:
        p = output_path if output_path is not None else expected_pdf
        return _fake_render_result(p)

    monkeypatch.setattr("silentwitness_agent.cli_commands.export.PdfRenderer.render", _fake_render)
    result = runner.invoke(app, ["export", "mr-exp-003", "--pdf"], catch_exceptions=False)
    assert result.exit_code == 0
    assert str(expected_pdf.resolve()) in result.output
    assert expected_pdf.exists()


# ---------------------------------------------------------------------------
# 4. --out overrides default PDF output path
# ---------------------------------------------------------------------------


def test_export_pdf_custom_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--out /custom.pdf with --pdf writes to the custom path, exit 0."""
    case_dir = _make_case(tmp_path, "mr-exp-004", monkeypatch)
    custom_out = tmp_path / "custom-report.pdf"
    default_pdf = case_dir / "report.pdf"

    def _fake_render(self: object, *, output_path: Path | None = None) -> PdfRenderResult:
        p = output_path if output_path is not None else default_pdf
        return _fake_render_result(p)

    monkeypatch.setattr("silentwitness_agent.cli_commands.export.PdfRenderer.render", _fake_render)
    result = runner.invoke(
        app,
        ["export", "mr-exp-004", "--pdf", "--out", str(custom_out)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert str(custom_out.resolve()) in result.output
    assert custom_out.exists()
    assert not default_pdf.exists()


# ---------------------------------------------------------------------------
# 5. --pdf and --md together → exit 1, conflicting-flags error
# ---------------------------------------------------------------------------


def test_export_conflicting_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Passing both --pdf and --md exits 1 with mutually exclusive message."""
    _make_case(tmp_path, "mr-exp-005", monkeypatch)
    result = runner.invoke(app, ["export", "mr-exp-005", "--pdf", "--md"], catch_exceptions=False)
    assert result.exit_code == 1
    assert "mutually exclusive" in result.output


# ---------------------------------------------------------------------------
# 6. Case not found → exit 1
# ---------------------------------------------------------------------------


def test_export_case_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-existent case exits 1 with the case id in stderr."""
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    result = runner.invoke(app, ["export", "mr-exp-no-case"], catch_exceptions=False)
    assert result.exit_code == 1
    assert "mr-exp-no-case" in result.output


# ---------------------------------------------------------------------------
# 7. Missing report.md → exit 2
# ---------------------------------------------------------------------------


def test_export_missing_report_md(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Case without report.md exits 2 with run-investigate hint."""
    case_dir = _make_case(tmp_path, "mr-exp-007", monkeypatch)
    (case_dir / "report.md").unlink()
    result = runner.invoke(app, ["export", "mr-exp-007"], catch_exceptions=False)
    assert result.exit_code == 2
    assert "report.md not generated" in result.output


# ---------------------------------------------------------------------------
# 8. WeasyPrint render error → exit 2, "PDF render failed" in output
# ---------------------------------------------------------------------------


def test_export_pdf_render_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Render exception exits 2 with 'PDF render failed' in output."""
    _make_case(tmp_path, "mr-exp-008", monkeypatch)

    def _fail_render(self: object, *, output_path: Path | None = None) -> PdfRenderResult:
        raise RuntimeError("cairo: surface not available")

    monkeypatch.setattr("silentwitness_agent.cli_commands.export.PdfRenderer.render", _fail_render)
    result = runner.invoke(app, ["export", "mr-exp-008", "--pdf"], catch_exceptions=False)
    assert result.exit_code == 2
    assert "PDF render failed" in result.output


# ---------------------------------------------------------------------------
# 9. --ioc-format with unimplemented module → warning, exit 0
# ---------------------------------------------------------------------------


def test_export_ioc_format_unavailable_when_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit IOC request emits warning but does not block the export."""
    _make_case(tmp_path, "mr-exp-009", monkeypatch)
    result = runner.invoke(
        app, ["export", "mr-exp-009", "--ioc-format", "stix"], catch_exceptions=False
    )
    # IOC export module doesn't exist yet; expect warning and clean exit.
    assert result.exit_code == 0
    assert "IOC export not yet available" in result.output


# ---------------------------------------------------------------------------
# 10. --out ignored in --md mode → warning emitted, report.md path returned
# ---------------------------------------------------------------------------


def test_export_out_ignored_in_md_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--out with --md emits an --out-ignored warning and still returns report.md path."""
    case_dir = _make_case(tmp_path, "mr-exp-010", monkeypatch)
    result = runner.invoke(
        app,
        ["export", "mr-exp-010", "--md", "--out", str(tmp_path / "ignored.pdf")],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "--out ignored" in result.output
    assert str((case_dir / "report.md").resolve()) in result.output


# ---------------------------------------------------------------------------
# 11. Stdout discipline — path is on the last output line (no ANSI contamination)
# ---------------------------------------------------------------------------


def test_export_path_is_last_output_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The emitted path is the last non-empty line of combined output, free of ANSI codes."""
    case_dir = _make_case(tmp_path, "mr-exp-011", monkeypatch)
    result = runner.invoke(app, ["export", "mr-exp-011"], catch_exceptions=False)
    assert result.exit_code == 0
    non_empty_lines = [ln for ln in result.output.splitlines() if ln.strip()]
    assert non_empty_lines, "expected at least one output line"
    last_line = non_empty_lines[-1]
    expected = str((case_dir / "report.md").resolve())
    assert last_line == expected, f"last line {last_line!r} is not the bare path {expected!r}"


# ---------------------------------------------------------------------------
# 12. BrokenVerifyLink → exit 2 with verify-link hint in output
# ---------------------------------------------------------------------------


def test_export_pdf_broken_verify_link(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """BrokenVerifyLink from the renderer exits 2 with a verify-link remediation hint."""
    _make_case(tmp_path, "mr-exp-012", monkeypatch)

    def _raise_broken(self: object, *, output_path: Path | None = None) -> PdfRenderResult:
        raise BrokenVerifyLink("F-999", "sift-001", "audit id not found")

    monkeypatch.setattr("silentwitness_agent.cli_commands.export.PdfRenderer.render", _raise_broken)
    result = runner.invoke(app, ["export", "mr-exp-012", "--pdf"], catch_exceptions=False)
    assert result.exit_code == 2
    assert "broken verify-link" in result.output
    assert "silentwitness verify" in result.output
