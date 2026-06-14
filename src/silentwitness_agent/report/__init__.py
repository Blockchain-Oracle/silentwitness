"""Report module — Markdown template + YAML frontmatter for report-as-state."""

from silentwitness_agent.report.audit_index import AuditEntryRef, AuditIndex
from silentwitness_agent.report.template import (
    Frontmatter,
    ReportTemplate,
)
from silentwitness_agent.report.verify_links import (
    APPENDIX_ANCHOR_PREFIX,
    BrokenVerifyLink,
    ValidationReport,
    VerifyLinkRenderer,
    VerifyRef,
)
from silentwitness_agent.report.writer import ReportRenderResult, ReportWriter
from silentwitness_common.types import ReportSection

__all__ = [
    "APPENDIX_ANCHOR_PREFIX",
    "AuditEntryRef",
    "AuditIndex",
    "BrokenVerifyLink",
    "Frontmatter",
    "ReportRenderResult",
    "ReportSection",
    "ReportTemplate",
    "ReportWriter",
    "ValidationReport",
    "VerifyLinkRenderer",
    "VerifyRef",
]
