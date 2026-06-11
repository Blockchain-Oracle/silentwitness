"""VerifyLinkRenderer — extract, validate, and expand [verify:F-id/audit_id] refs.

Inline verify references embed a claim provenance token in Markdown prose:

    PowerShell ran with -EncodedCommand flag [verify:F-001/sift-aj-20260613-042].

At validate time, every audit_id is checked against the case's audit/*.jsonl
index — unresolved refs raise BrokenVerifyLink so the writer aborts before any
broken reference lands in report.md. At PDF export time, each ref expands to a
superscript hyperlink jumping to the Appendix-Audit anchor for that audit_id.
Markdown / terminal display keeps plain [verify:...] syntax intact.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from silentwitness_agent.report.audit_index import AuditIndex

# Anchor prefix for Appendix-Audit entries — must match compose_appendix_audit output.
APPENDIX_ANCHOR_PREFIX = "audit-"

# Regex: [verify:F-NNN/sift-<slug>-YYYYMMDD-NNN]
# F-\d{3,}      — 3+ digit finding sequence (supports F-001 through F-9999+)
# sift-[a-z0-9]+ — slugged examiner (lowercased alphanumeric per common-types)
# \d{8}          — YYYYMMDD date
# \d{3,}         — 3+ digit audit sequence
_RE_VERIFY = re.compile(r"\[verify:(F-\d{3,})/(sift-[a-z0-9]+-\d{8}-\d{3,})\]")

_CONTEXT_WINDOW = 40  # chars either side of the broken ref for BrokenVerifyLink.context


class BrokenVerifyLink(Exception):  # noqa: N818  # name mandated by story spec
    """Raised when a [verify:...] ref cannot be resolved in the audit index."""

    def __init__(self, audit_id: str, finding_id: str, context: str) -> None:
        super().__init__(
            f"Broken verify link — audit_id {audit_id!r} referenced by {finding_id!r} "
            f"not found in audit index. Context: {context!r}"
        )
        self.audit_id = audit_id
        self.finding_id = finding_id
        self.context = context


class VerifyRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    finding_id: str
    audit_id: str
    span_start: int
    span_end: int


class ValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    total_refs: int
    resolved_refs: int
    broken_refs: int


class VerifyLinkRenderer:
    """Stateless renderer for [verify:F-id/audit_id] inline references."""

    def extract(self, body: str) -> list[VerifyRef]:
        """Return a VerifyRef for every well-formed [verify:...] match in body."""
        return [
            VerifyRef(
                finding_id=m.group(1),
                audit_id=m.group(2),
                span_start=m.start(),
                span_end=m.end(),
            )
            for m in _RE_VERIFY.finditer(body)
        ]

    def validate(self, body: str, *, audit_dir: Path) -> ValidationReport:
        """Validate that every [verify:...] ref resolves in audit_dir/*.jsonl.

        Raises BrokenVerifyLink on the first unresolved reference so the caller
        can abort before writing a report with a dangling claim.
        """
        refs = self.extract(body)
        if not refs:
            return ValidationReport(total_refs=0, resolved_refs=0, broken_refs=0)

        index = AuditIndex.from_dir(audit_dir)
        resolved = 0
        broken = 0

        for ref in refs:
            if index.contains(ref.audit_id):
                resolved += 1
            else:
                broken += 1
                context = _extract_context(body, ref.span_start, ref.span_end)
                raise BrokenVerifyLink(
                    audit_id=ref.audit_id,
                    finding_id=ref.finding_id,
                    context=context,
                )

        return ValidationReport(
            total_refs=len(refs),
            resolved_refs=resolved,
            broken_refs=broken,
        )

    def expand_for_pdf(self, body: str, *, audit_dir: Path | None) -> str:
        """Replace each [verify:F-id/audit_id] with a superscript Markdown link.

        Produces: [<sup>verify:F-id/audit_id</sup>](#audit-audit_id)

        WeasyPrint CSS styles <sup> inside <a> as a small #5ba3d0 superscript
        that jumps to the Appendix-Audit anchor for that audit_id.
        audit_dir is accepted but not used — validation is a separate step.
        """
        _ = audit_dir  # expansion is purely syntactic; validation is a separate step

        def _replace(m: re.Match[str]) -> str:
            finding_id = m.group(1)
            audit_id = m.group(2)
            label = f"verify:{finding_id}/{audit_id}"
            anchor = f"#{APPENDIX_ANCHOR_PREFIX}{audit_id}"
            return f"[<sup>{label}</sup>]({anchor})"

        return _RE_VERIFY.sub(_replace, body)

    def expand_for_markdown(self, body: str) -> str:
        """No-op — plain [verify:...] syntax is preserved for terminal display."""
        return body


def _extract_context(body: str, span_start: int, span_end: int) -> str:
    """Return the ±CONTEXT_WINDOW chars around a span, with ellipsis at truncated ends."""
    lo = max(0, span_start - _CONTEXT_WINDOW)
    hi = min(len(body), span_end + _CONTEXT_WINDOW)
    snippet = body[lo:hi]
    if lo > 0:
        snippet = "…" + snippet
    if hi < len(body):
        snippet = snippet + "…"
    return snippet


__all__ = [
    "APPENDIX_ANCHOR_PREFIX",
    "BrokenVerifyLink",
    "ValidationReport",
    "VerifyLinkRenderer",
    "VerifyRef",
]
