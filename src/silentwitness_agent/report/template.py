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
from datetime import UTC
from enum import StrEnum
from typing import Any

import yaml
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from silentwitness_common.types import ReportSection

REPORT_SCHEMA_VERSION = "1.0.0"


class ReportStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    FINAL = "FINAL"


class Frontmatter(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    case_id: str = Field(min_length=1)
    examiner: str = Field(min_length=1)
    status: ReportStatus
    content_hash: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    created_at: AwareDatetime
    updated_at: AwareDatetime
    silentwitness_version: str = Field(min_length=1)
    model_used: str = Field(min_length=1)


SECTION_ORDER: tuple[ReportSection, ...] = (
    ReportSection.EXECUTIVE_SUMMARY,
    ReportSection.ENGAGEMENT_OVERVIEW,
    ReportSection.METHODOLOGY,
    ReportSection.FINDINGS,
    ReportSection.TIMELINE,
    ReportSection.IOCS,
    ReportSection.ATTACK,
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
    ReportSection.ATTACK: "MITRE ATT&CK Techniques",
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
    ReportSection.ATTACK: "mitre-attack-techniques",
    ReportSection.RECOMMENDATIONS: "recommendations",
    ReportSection.GAPS: "gaps",
    ReportSection.APPENDIX_AUDIT: "appendix-audit",
}

# Fail loudly at import time if any ReportSection member is missing from the
# lookup dicts — catches the "added enum member, forgot to update dict" class of bug.
assert set(SECTION_ORDER) == set(ReportSection), (  # noqa: S101
    f"SECTION_ORDER missing members: {set(ReportSection) - set(SECTION_ORDER)}"
)
assert set(SECTION_HEADINGS) == set(ReportSection), (  # noqa: S101
    f"SECTION_HEADINGS missing members: {set(ReportSection) - set(SECTION_HEADINGS)}"
)
assert set(SECTION_ANCHORS) == set(ReportSection), (  # noqa: S101
    f"SECTION_ANCHORS missing members: {set(ReportSection) - set(SECTION_ANCHORS)}"
)


def dump_frontmatter(fm: Frontmatter) -> str:
    """Serialise Frontmatter to a YAML block wrapped in --- fences.

    Field order matches architecture §5.4 exactly (sort_keys=False).
    Datetime fields are normalised to UTC and emitted as ISO-8601 with Z suffix.
    """
    data: dict[str, Any] = {
        "case_id": fm.case_id,
        "examiner": fm.examiner,
        "status": fm.status.value,
        "content_hash": fm.content_hash,
        "created_at": fm.created_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_at": fm.updated_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "silentwitness_version": fm.silentwitness_version,
        "model_used": fm.model_used,
    }
    body = yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True)
    return f"---\n{body}---\n"


def parse_frontmatter(md_text: str) -> tuple[Frontmatter, str]:
    """Parse the YAML frontmatter block from a Markdown document.

    Returns (Frontmatter, body) where body is the text after the closing ---.
    Raises pydantic.ValidationError on invalid field values.
    Raises ValueError if --- fences are missing, the YAML block is empty or
    not a mapping, or the YAML itself is malformed.
    """
    if not md_text.startswith("---\n"):
        raise ValueError("document does not begin with ---")
    rest = md_text[4:]
    close = rest.find("\n---\n")
    if close == -1:
        raise ValueError("no closing --- found in document")
    yaml_block = rest[:close]
    body = rest[close + 5 :]
    try:
        data = yaml.safe_load(yaml_block)
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(
            f"YAML frontmatter did not parse to a mapping "
            f"(got {type(data).__name__}); document may be empty or malformed"
        )
    return Frontmatter.model_validate(data), body


class ReportTemplate:
    @classmethod
    def render_skeleton(
        cls,
        fm: Frontmatter,
        *,
        gaps_placeholder: str = "(no gaps identified)",
    ) -> str:
        """Render a full report skeleton: frontmatter + title + 9 section headings.

        The GAPS section includes gaps_placeholder as its body (required by
        architecture §5.4 — the section must never be empty).
        """
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
        """Render a section heading with its body text.

        Trailing whitespace is stripped from body to avoid double-blank-line
        artifacts when sections are concatenated.
        """
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
