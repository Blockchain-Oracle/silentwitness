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

from pydantic import BaseModel, ConfigDict, Field, model_validator

from silentwitness_agent.report.audit_index import AuditIndex

# Per-entry anchor prefix used by expand_for_pdf() to build fragment links
# (#audit-<audit_id>) into the Appendix-Audit section of the PDF output.
# The Appendix-Audit section body must emit a matching anchor target for each
# audit_id entry — that target emission is handled by compose_appendix_audit.
APPENDIX_ANCHOR_PREFIX = "audit-"

# Regex: [verify:F-NNN/sift-<slug>-YYYYMMDD-NNN]
# F-\d{3,}       — 3+ digit finding sequence (supports F-001 through F-9999+)
# sift-[a-z0-9]+ — examiner slug: single unbroken lowercase-alnum run, no hyphens
#                  (per slug_examiner() in silentwitness_common.ids)
# \d{8}          — YYYYMMDD date
# \d{3,}         — 3+ digit audit sequence
_RE_VERIFY = re.compile(r"\[verify:(F-\d{3,})/(sift-[a-z0-9]+-\d{8}-\d{3,})\]")

_CONTEXT_WINDOW = 40  # chars before span_start / after span_end in BrokenVerifyLink.context

# Shared pattern constants — keep in sync with _RE_VERIFY groups.
_FINDING_ID_PATTERN = r"^F-\d{3,}$"
_AUDIT_ID_PATTERN = r"^sift-[a-z0-9]+-\d{8}-\d{3,}$"


class BrokenVerifyLink(Exception):  # noqa: N818  # name mandated by story spec
    """Raised when a [verify:...] ref cannot be resolved in the audit index.

    Always let this propagate — do not catch-and-swallow. The writer must abort
    rather than emit a report with an unresolvable provenance link.
    """

    __slots__ = ("audit_id", "context", "finding_id")

    def __init__(self, audit_id: str, finding_id: str, context: str) -> None:
        if not audit_id:
            raise ValueError("audit_id must be non-empty")
        if not finding_id:
            raise ValueError("finding_id must be non-empty")
        super().__init__(
            f"Broken verify link — audit_id {audit_id!r} referenced by {finding_id!r} "
            f"not found in audit index. Context: {context!r}"
        )
        self.audit_id = audit_id
        self.finding_id = finding_id
        self.context = context


class VerifyRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    finding_id: str = Field(pattern=_FINDING_ID_PATTERN)
    audit_id: str = Field(pattern=_AUDIT_ID_PATTERN)
    span_start: int = Field(ge=0)
    span_end: int = Field(gt=0)

    @model_validator(mode="after")
    def _span_ordered(self) -> VerifyRef:
        if self.span_end <= self.span_start:
            raise ValueError(f"span_end ({self.span_end}) must be > span_start ({self.span_start})")
        return self


class ValidationReport(BaseModel):
    """Result of a successful validate() pass — broken_refs is always 0.

    validate() raises BrokenVerifyLink on the first broken ref and never
    returns a report with broken_refs > 0; the accounting invariant
    resolved_refs + broken_refs == total_refs is enforced by model validation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_refs: int = Field(ge=0)
    resolved_refs: int = Field(ge=0)
    broken_refs: int = Field(ge=0)

    @model_validator(mode="after")
    def _counts_consistent(self) -> ValidationReport:
        if self.resolved_refs + self.broken_refs != self.total_refs:
            raise ValueError(
                f"resolved_refs ({self.resolved_refs}) + broken_refs ({self.broken_refs}) "
                f"must equal total_refs ({self.total_refs})"
            )
        return self


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

        Raises BrokenVerifyLink on the first unresolved reference (fail-fast).
        The returned ValidationReport.broken_refs is always 0 — the exception
        fires before any broken count could be returned.
        """
        refs = self.extract(body)
        if not refs:
            return ValidationReport(total_refs=0, resolved_refs=0, broken_refs=0)

        index = AuditIndex.from_dir(audit_dir)
        resolved = 0

        for ref in refs:
            if index.contains(ref.audit_id):
                resolved += 1
            else:
                context = _extract_context(body, ref.span_start, ref.span_end)
                raise BrokenVerifyLink(
                    audit_id=ref.audit_id,
                    finding_id=ref.finding_id,
                    context=context,
                )

        return ValidationReport(
            total_refs=len(refs),
            resolved_refs=resolved,
            broken_refs=0,
        )

    def expand_for_pdf(self, body: str) -> str:
        """Replace each [verify:F-id/audit_id] with a superscript Markdown link.

        Produces: [<sup>verify:F-id/audit_id</sup>](#audit-audit_id)

        Pre-condition: validate() MUST have returned without raising on this
        exact body — expansion is purely syntactic and does not re-check refs.
        WeasyPrint renders <sup>-inside-<a> as a superscript link; see the PDF
        stylesheet for color/size overrides.
        """

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
    """Return up to CONTEXT_WINDOW chars before span_start and after span_end.

    Adds ellipsis where text is truncated at either boundary.
    """
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
