"""Behavioural unit tests for report/template.py — 12 scenarios."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from silentwitness_agent.report.template import (
    SECTION_HEADINGS,
    SECTION_ORDER,
    Frontmatter,
    ReportTemplate,
    dump_frontmatter,
    parse_frontmatter,
)

_UTC = UTC

_HASH_ZEROS = "sha256:" + "0" * 64
_HASH_EMPTY = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def _make_fm(**overrides: object) -> Frontmatter:
    defaults: dict[str, object] = {
        "case_id": "hacking-case-001",
        "examiner": "aj",
        "status": "DRAFT",
        "content_hash": _HASH_ZEROS,
        "created_at": datetime(2026, 6, 13, 14, 27, 3, tzinfo=_UTC),
        "updated_at": datetime(2026, 6, 13, 14, 42, 17, tzinfo=_UTC),
        "silentwitness_version": "1.0.0",
        "model_used": "anthropic:claude-opus-4-7",
    }
    defaults.update(overrides)
    return Frontmatter.model_validate(defaults)


# ---------------------------------------------------------------------------
# dump_frontmatter
# ---------------------------------------------------------------------------


def test_dump_frontmatter_starts_and_ends_with_fences() -> None:
    fm = _make_fm()
    out = dump_frontmatter(fm)
    assert out.startswith("---\n")
    assert out.endswith("---\n")


def test_dump_frontmatter_field_order_matches_architecture() -> None:
    """Fields must appear in architecture §5.4 order: case_id→model_used."""
    fm = _make_fm()
    out = dump_frontmatter(fm)
    lines = [ln for ln in out.splitlines() if ":" in ln and not ln.startswith("-")]
    keys = [ln.split(":")[0].strip() for ln in lines]
    assert keys == [
        "case_id",
        "examiner",
        "status",
        "content_hash",
        "created_at",
        "updated_at",
        "silentwitness_version",
        "model_used",
    ]


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------


def test_parse_frontmatter_round_trips() -> None:
    fm = _make_fm()
    md = dump_frontmatter(fm) + "\n# stub\n"
    fm2, body = parse_frontmatter(md)
    assert fm2 == fm
    assert body.strip() == "# stub"


def test_parse_frontmatter_rejects_malformed_content_hash() -> None:
    md = (
        "---\n"
        "case_id: test\n"
        "examiner: aj\n"
        "status: DRAFT\n"
        "content_hash: sha256:not-a-real-hash\n"
        "created_at: '2026-06-13T14:27:03Z'\n"
        "updated_at: '2026-06-13T14:42:17Z'\n"
        "silentwitness_version: 1.0.0\n"
        "model_used: anthropic:claude-opus-4-7\n"
        "---\n"
    )
    with pytest.raises(ValidationError):
        parse_frontmatter(md)


def test_parse_frontmatter_raises_on_missing_case_id() -> None:
    md = (
        "---\n"
        "examiner: aj\n"
        "status: DRAFT\n"
        f"content_hash: {_HASH_ZEROS}\n"
        "created_at: '2026-06-13T14:27:03Z'\n"
        "updated_at: '2026-06-13T14:42:17Z'\n"
        "silentwitness_version: 1.0.0\n"
        "model_used: anthropic:claude-opus-4-7\n"
        "---\n"
    )
    with pytest.raises(ValidationError):
        parse_frontmatter(md)


def test_parse_frontmatter_rejects_naive_created_at() -> None:
    """Timezone-naive created_at must raise ValidationError mentioning 'timezone'."""
    md = (
        "---\n"
        "case_id: test\n"
        "examiner: aj\n"
        "status: DRAFT\n"
        f"content_hash: {_HASH_ZEROS}\n"
        "created_at: 2026-06-13T14:27:03\n"
        "updated_at: '2026-06-13T14:42:17Z'\n"
        "silentwitness_version: 1.0.0\n"
        "model_used: anthropic:claude-opus-4-7\n"
        "---\n"
    )
    with pytest.raises(ValidationError) as exc_info:
        parse_frontmatter(md)
    assert "timezone" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# render_skeleton
# ---------------------------------------------------------------------------


def test_render_skeleton_contains_all_9_sections_in_order() -> None:
    fm = _make_fm()
    out = ReportTemplate.render_skeleton(fm)
    positions = [out.index(f"## {SECTION_HEADINGS[s]}") for s in SECTION_ORDER]
    assert positions == sorted(positions), "sections not in SECTION_ORDER"


def test_render_skeleton_gaps_has_default_placeholder() -> None:
    fm = _make_fm()
    out = ReportTemplate.render_skeleton(fm)
    assert "(no gaps identified)" in out


def test_render_skeleton_gaps_placeholder_overridable() -> None:
    fm = _make_fm()
    out = ReportTemplate.render_skeleton(fm, gaps_placeholder="custom gap note")
    assert "custom gap note" in out
    assert "(no gaps identified)" not in out


# ---------------------------------------------------------------------------
# compute_content_hash
# ---------------------------------------------------------------------------


def test_compute_content_hash_returns_sha256_prefix_and_64_hex() -> None:
    result = ReportTemplate.compute_content_hash("some content")
    assert result.startswith("sha256:")
    hex_part = result[len("sha256:") :]
    assert len(hex_part) == 64
    assert all(c in "0123456789abcdef" for c in hex_part)


def test_compute_content_hash_empty_string_is_stable_canary() -> None:
    assert ReportTemplate.compute_content_hash("") == _HASH_EMPTY


# ---------------------------------------------------------------------------
# SECTION_ORDER
# ---------------------------------------------------------------------------


def test_section_order_has_9_elements() -> None:
    assert len(SECTION_ORDER) == 9
