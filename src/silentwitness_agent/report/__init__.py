"""Report module — Markdown template + YAML frontmatter for report-as-state."""

from silentwitness_agent.report.template import (
    Frontmatter,
    ReportTemplate,
)
from silentwitness_common.types import ReportSection

__all__ = ["Frontmatter", "ReportSection", "ReportTemplate"]
