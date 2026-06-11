"""Report module — Markdown template + YAML frontmatter for report-as-state."""

from silentwitness_agent.report.events import FindingEvent, ReportSubscriber
from silentwitness_agent.report.template import (
    Frontmatter,
    ReportTemplate,
)
from silentwitness_agent.report.writer import ReportRenderResult, ReportWriter
from silentwitness_common.types import ReportSection

__all__ = [
    "FindingEvent",
    "Frontmatter",
    "ReportRenderResult",
    "ReportSection",
    "ReportSubscriber",
    "ReportTemplate",
    "ReportWriter",
]
