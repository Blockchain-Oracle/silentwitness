"""FOR508-shaped Markdown report template with YAML frontmatter.

REPORT_SCHEMA_VERSION = "1.0.0" — bump when frontmatter fields are added or
renamed; forward-compat readers should check this value.

compute_content_hash operates on the body (everything after the closing ---\n),
NOT the frontmatter — frontmatter timestamps change on every update, so
including them would invalidate the hash even when the substantive content is
unchanged.
"""

from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Any

import yaml
from pydantic import AwareDatetime, BaseModel, Field

from silentwitness_common.types import ReportSection

REPORT_SCHEMA_VERSION = "1.0.0"


class ReportStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    FINAL = "FINAL"


class Frontmatter(BaseModel):
    case_id: str
    examiner: str
    status: ReportStatus
    content_hash: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    created_at: AwareDatetime
    updated_at: AwareDatetime
    silentwitness_version: str
    model_used: str


SECTION_ORDER: tuple[ReportSection, ...] = (
    ReportSection.EXECUTIVE_SUMMARY,
    ReportSection.ENGAGEMENT_OVERVIEW,
    ReportSection.METHODOLOGY,
    ReportSection.FINDINGS,
    ReportSection.TIMELINE,
    ReportSection.IOCS,
    ReportSection.RECOMMENDATIONS,
    ReportSection.GAPS,
    ReportSection.APPENDIX_AUDIT,
)

SECTION_HEADINGS: dict[ReportSection, str] = {
    ReportSection.EXECUTIVE_SUMMARY: "Executive Summary",
    ReportSection.ENGAGEMENT_OVERVIEW: "Engagement Overview",
    ReportSection.METHODOLOGY: "Methodology",
    ReportSection.FINDINGS: "Findings",
    ReportSection.TIMELINE: "Timeline",
    ReportSection.IOCS: "Indicators of Compromise",
    ReportSection.RECOMMENDATIONS: "Recommendations",
    ReportSection.GAPS: "Gaps",
    ReportSection.APPENDIX_AUDIT: "Appendix — Audit",
}

SECTION_ANCHORS: dict[ReportSection, str] = {
    ReportSection.EXECUTIVE_SUMMARY: "executive-summary",
    ReportSection.ENGAGEMENT_OVERVIEW: "engagement-overview",
    ReportSection.METHODOLOGY: "methodology",
    ReportSection.FINDINGS: "findings",
    ReportSection.TIMELINE: "timeline",
    ReportSection.IOCS: "indicators-of-compromise",
    ReportSection.RECOMMENDATIONS: "recommendations",
    ReportSection.GAPS: "gaps",
    ReportSection.APPENDIX_AUDIT: "appendix-audit",
}


def dump_frontmatter(fm: Frontmatter) -> str:
    """Serialise Frontmatter to a YAML block wrapped in --- fences.

    Field order matches architecture §5.4 exactly (sort_keys=False).
    Datetime fields are emitted as ISO-8601 strings with Z suffix.
    """
    data: dict[str, Any] = {
        "case_id": fm.case_id,
        "examiner": fm.examiner,
        "status": fm.status.value,
        "content_hash": fm.content_hash,
        "created_at": fm.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_at": fm.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "silentwitness_version": fm.silentwitness_version,
        "model_used": fm.model_used,
    }
    body = yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True)
    return f"---\n{body}---\n"


def parse_frontmatter(md_text: str) -> tuple[Frontmatter, str]:
    """Parse the YAML frontmatter block from a Markdown document.

    Returns (Frontmatter, body) where body is the text after the closing ---.
    Raises pydantic.ValidationError on invalid field values.
    Raises ValueError if --- fences are missing or malformed.
    """
    if not md_text.startswith("---\n"):
        raise ValueError("document does not begin with ---")
    rest = md_text[4:]
    close = rest.find("\n---\n")
    if close == -1:
        raise ValueError("no closing --- found in document")
    yaml_block = rest[:close]
    body = rest[close + 5 :]
    data = yaml.safe_load(yaml_block)
    return Frontmatter.model_validate(data), body


class ReportTemplate:
    @classmethod
    def render_skeleton(
        cls,
        fm: Frontmatter,
        *,
        gaps_placeholder: str = "(no gaps identified)",
    ) -> str:
        """Render a full report skeleton: frontmatter + title + 9 section headings."""
        parts: list[str] = [f"# Incident Report — Case {fm.case_id}"]
        for section in SECTION_ORDER:
            heading = f"## {SECTION_HEADINGS[section]}"
            if section == ReportSection.GAPS:
                parts.append(f"{heading}\n\n{gaps_placeholder}")
            else:
                parts.append(heading)
        return dump_frontmatter(fm) + "\n" + "\n\n".join(parts) + "\n"

    @classmethod
    def render_section(cls, section: ReportSection, body: str) -> str:
        """Render a section heading with its body text."""
        return f"## {SECTION_HEADINGS[section]}\n\n{body.rstrip()}\n"

    @classmethod
    def compute_content_hash(cls, body: str) -> str:
        """Return sha256:<hex> of the report body (not the frontmatter)."""
        return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


__all__ = [
    "REPORT_SCHEMA_VERSION",
    "SECTION_ANCHORS",
    "SECTION_HEADINGS",
    "SECTION_ORDER",
    "Frontmatter",
    "ReportStatus",
    "ReportTemplate",
    "dump_frontmatter",
    "parse_frontmatter",
]
