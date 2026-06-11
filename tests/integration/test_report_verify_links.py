"""Integration tests for VerifyLinkRenderer against synthetic case directories (≥10 tests)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from silentwitness_agent.report.verify_links import (
    BrokenVerifyLink,
    ValidationReport,
    VerifyLinkRenderer,
    VerifyRef,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _audit_dir(tmp_path: Path, entries: list[dict]) -> Path:  # type: ignore[type-arg]
    """Create a minimal audit/ directory with the given audit records."""
    d = tmp_path / "audit"
    d.mkdir()
    (d / "findings.jsonl").write_text(
        "\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8"
    )
    return d


# ---------------------------------------------------------------------------
# 1. extract finds 0 refs in body without any
# ---------------------------------------------------------------------------


def test_extract_empty_body() -> None:
    result = VerifyLinkRenderer().extract("No verify refs here.")
    assert result == []


# ---------------------------------------------------------------------------
# 2. extract finds 3 refs in a body with 3 inline [verify:...]
# ---------------------------------------------------------------------------


def test_extract_three_refs() -> None:
    body = (
        "Evidence A [verify:F-001/sift-aj-20260613-007]. "
        "Evidence B [verify:F-002/sift-aj-20260613-008]. "
        "Evidence C [verify:F-003/sift-aj-20260613-009]."
    )
    refs = VerifyLinkRenderer().extract(body)
    assert len(refs) == 3
    assert all(isinstance(r, VerifyRef) for r in refs)
    assert refs[0].finding_id == "F-001"
    assert refs[0].audit_id == "sift-aj-20260613-007"
    assert refs[1].finding_id == "F-002"
    assert refs[2].finding_id == "F-003"


# ---------------------------------------------------------------------------
# 3. extract rejects malformed refs — [verify:bogus] is NOT included
# ---------------------------------------------------------------------------


def test_extract_ignores_malformed_refs() -> None:
    body = (
        "Malformed [verify:bogus] and [verify:not-a-finding-id/wrong] "
        "and valid [verify:F-001/sift-aj-20260613-001]."
    )
    refs = VerifyLinkRenderer().extract(body)
    assert len(refs) == 1
    assert refs[0].finding_id == "F-001"


# ---------------------------------------------------------------------------
# 4. validate returns resolved report when all audit_ids exist
# ---------------------------------------------------------------------------


def test_validate_all_resolved(tmp_path: Path) -> None:
    d = _audit_dir(
        tmp_path,
        [
            {"audit_id": "sift-aj-20260613-007", "tool": "vol3"},
            {"audit_id": "sift-aj-20260613-008", "tool": "sbeCmd"},
        ],
    )
    body = "A [verify:F-001/sift-aj-20260613-007] and B [verify:F-002/sift-aj-20260613-008]."
    report = VerifyLinkRenderer().validate(body, audit_dir=d)
    assert isinstance(report, ValidationReport)
    assert report.total_refs == 2
    assert report.resolved_refs == 2
    assert report.broken_refs == 0


# ---------------------------------------------------------------------------
# 5. validate raises BrokenVerifyLink when one audit_id is missing
# ---------------------------------------------------------------------------


def test_validate_raises_on_missing_audit_id(tmp_path: Path) -> None:
    d = _audit_dir(tmp_path, [{"audit_id": "sift-aj-20260613-007", "tool": "vol3"}])
    body = (
        "Real [verify:F-001/sift-aj-20260613-007]. Broken [verify:F-002/sift-alice-20260602-009]."
    )
    with pytest.raises(BrokenVerifyLink) as exc_info:
        VerifyLinkRenderer().validate(body, audit_dir=d)
    assert exc_info.value.audit_id == "sift-alice-20260602-009"


# ---------------------------------------------------------------------------
# 6. BrokenVerifyLink.audit_id matches the offending ID
# ---------------------------------------------------------------------------


def test_broken_verify_link_carries_audit_id(tmp_path: Path) -> None:
    d = _audit_dir(tmp_path, [])
    body = "Broken [verify:F-001/sift-alice-20260602-007]."
    with pytest.raises(BrokenVerifyLink) as exc_info:
        VerifyLinkRenderer().validate(body, audit_dir=d)
    assert exc_info.value.audit_id == "sift-alice-20260602-007"
    assert exc_info.value.finding_id == "F-001"


# ---------------------------------------------------------------------------
# 7. BrokenVerifyLink.context shows ±40 chars around the broken ref
# ---------------------------------------------------------------------------


def test_broken_verify_link_context_window(tmp_path: Path) -> None:
    d = _audit_dir(tmp_path, [])
    prefix = "X" * 50  # longer than the 40-char window
    suffix = "Y" * 50
    body = f"{prefix}[verify:F-001/sift-alice-20260602-007]{suffix}"
    with pytest.raises(BrokenVerifyLink) as exc_info:
        VerifyLinkRenderer().validate(body, audit_dir=d)
    ctx = exc_info.value.context
    # Context must be smaller than the full body and contain the ref itself
    assert "verify:F-001" in ctx
    assert len(ctx) < len(body)


# ---------------------------------------------------------------------------
# 8. expand_for_pdf produces [<sup>verify:...</sup>](#audit-...) for each ref
# ---------------------------------------------------------------------------


def test_expand_for_pdf_produces_superscript_link(tmp_path: Path) -> None:
    body = "PowerShell ran [verify:F-001/sift-aj-20260613-007]."
    out = VerifyLinkRenderer().expand_for_pdf(body, audit_dir=tmp_path)
    assert "[<sup>verify:F-001/sift-aj-20260613-007</sup>]" in out
    assert "(#audit-sift-aj-20260613-007)" in out


# ---------------------------------------------------------------------------
# 9. expand_for_pdf leaves non-verify text unchanged
# ---------------------------------------------------------------------------


def test_expand_for_pdf_leaves_other_text_unchanged(tmp_path: Path) -> None:
    body = "Intro text. [verify:F-001/sift-aj-20260613-007]. Conclusion."
    out = VerifyLinkRenderer().expand_for_pdf(body, audit_dir=tmp_path)
    assert "Intro text." in out
    assert "Conclusion." in out
    # The original plain ref is gone
    assert "[verify:F-001/sift-aj-20260613-007]" not in out


# ---------------------------------------------------------------------------
# 10. expand_for_markdown is a no-op (body identical)
# ---------------------------------------------------------------------------


def test_expand_for_markdown_noop() -> None:
    body = "PowerShell ran [verify:F-001/sift-aj-20260613-007]."
    assert VerifyLinkRenderer().expand_for_markdown(body) == body


# ---------------------------------------------------------------------------
# 11. expand_for_pdf handles multiple refs on one line
# ---------------------------------------------------------------------------


def test_expand_for_pdf_multiple_refs_same_line(tmp_path: Path) -> None:
    body = "[verify:F-001/sift-aj-20260613-001] and [verify:F-002/sift-aj-20260613-002]."
    out = VerifyLinkRenderer().expand_for_pdf(body, audit_dir=tmp_path)
    assert "(#audit-sift-aj-20260613-001)" in out
    assert "(#audit-sift-aj-20260613-002)" in out
    assert "[verify:F-001/sift-aj-20260613-001]" not in out
    assert "[verify:F-002/sift-aj-20260613-002]" not in out


# ---------------------------------------------------------------------------
# 12. validate body with 0 refs returns total_refs=0
# ---------------------------------------------------------------------------


def test_validate_body_no_refs(tmp_path: Path) -> None:
    d = _audit_dir(tmp_path, [])
    report = VerifyLinkRenderer().validate("No refs here.", audit_dir=d)
    assert report.total_refs == 0
    assert report.resolved_refs == 0
    assert report.broken_refs == 0


# ---------------------------------------------------------------------------
# 13. VerifyRef span positions are correct
# ---------------------------------------------------------------------------


def test_extract_span_positions_correct() -> None:
    body = "Text [verify:F-001/sift-aj-20260613-007] more."
    refs = VerifyLinkRenderer().extract(body)
    assert len(refs) == 1
    assert body[refs[0].span_start : refs[0].span_end] == "[verify:F-001/sift-aj-20260613-007]"


# ---------------------------------------------------------------------------
# 14. BrokenVerifyLink context ellipsis appears when body is long
# ---------------------------------------------------------------------------


def test_broken_verify_link_context_has_ellipsis(tmp_path: Path) -> None:
    d = _audit_dir(tmp_path, [])
    body = "A" * 100 + "[verify:F-001/sift-alice-20260602-007]" + "B" * 100
    with pytest.raises(BrokenVerifyLink) as exc_info:
        VerifyLinkRenderer().validate(body, audit_dir=d)
    ctx = exc_info.value.context
    assert "…" in ctx
