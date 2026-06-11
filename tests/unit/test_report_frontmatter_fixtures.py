"""Fixture tests — verbatim frontmatter samples must parse cleanly (4 tests)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from silentwitness_agent.report.template import (
    Frontmatter,
    ReportStatus,
    parse_frontmatter,
)

# Architecture §5.4 verbatim frontmatter (content_hash uses all-zeros placeholder
# as the spec sample has `<sha256 of body>` — replaced with a valid 64-hex value).
_ARCH_54_FRONTMATTER = """\
---
case_id: hacking-case-001
examiner: aj
status: DRAFT
content_hash: sha256:0000000000000000000000000000000000000000000000000000000000000000
created_at: '2026-06-13T14:27:03Z'
updated_at: '2026-06-13T14:42:17Z'
silentwitness_version: 1.0.0
model_used: anthropic:claude-opus-4-7
---
"""

# ux-spec §5.1 verbatim frontmatter (abbreviated hash `sha256:f0c2...a991` expanded
# to a valid 64-hex value while preserving the case/examiner/version fields exactly).
_UX_SPEC_51_FRONTMATTER = """\
---
case_id: mr-evil-001
examiner: sansforensics
created_at: '2026-06-02T12:00:00Z'
updated_at: '2026-06-02T13:48:30Z'
status: DRAFT
content_hash: sha256:f0c2a8b3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9a991
silentwitness_version: 0.3.1
model_used: anthropic:claude-opus-4-7-1m
---
"""


def test_architecture_54_verbatim_sample_parses() -> None:
    fm, _ = parse_frontmatter(_ARCH_54_FRONTMATTER)
    assert fm.status == ReportStatus.DRAFT


def test_ux_spec_51_verbatim_sample_parses() -> None:
    fm, _ = parse_frontmatter(_UX_SPEC_51_FRONTMATTER)
    assert fm.examiner == "sansforensics"


def test_status_accepts_all_three_values() -> None:
    for value in ("DRAFT", "REVIEWED", "FINAL"):
        fm = Frontmatter.model_validate(
            {
                "case_id": "x",
                "examiner": "aj",
                "status": value,
                "content_hash": "sha256:" + "a" * 64,
                "created_at": "2026-06-13T14:27:03Z",
                "updated_at": "2026-06-13T14:42:17Z",
                "silentwitness_version": "1.0.0",
                "model_used": "anthropic:claude-opus-4-7",
            }
        )
        assert fm.status.value == value


def test_unknown_status_rejected() -> None:
    with pytest.raises(ValidationError):
        Frontmatter.model_validate(
            {
                "case_id": "x",
                "examiner": "aj",
                "status": "SUBMITTED",
                "content_hash": "sha256:" + "a" * 64,
                "created_at": "2026-06-13T14:27:03Z",
                "updated_at": "2026-06-13T14:42:17Z",
                "silentwitness_version": "1.0.0",
                "model_used": "anthropic:claude-opus-4-7",
            }
        )
