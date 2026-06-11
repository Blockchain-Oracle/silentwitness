"""ReportWriter — atomic Markdown report renderer for one case directory.

Subscribes to FindingEvent (observation_staged / interpretation_staged /
pivot_staged / finding_approved / finding_archived) via on_finding_event
and debounces concurrent events within a 50ms window into a single render.

Atomicity invariant: report.md is written via write_text_atomic (atomic
rename from a sibling .tmp file). A killed process never leaves a partial
write — the prior report.md survives intact.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from silentwitness_agent.report.compose import (
    compose_appendix_audit,
    compose_engagement_overview,
    compose_executive_summary,
    compose_findings,
    compose_gaps,
    compose_iocs,
    compose_methodology,
    compose_recommendations,
    compose_timeline,
)
from silentwitness_agent.report.template import (
    Frontmatter,
    ReportStatus,
    ReportTemplate,
    dump_frontmatter,
    parse_frontmatter,
)
from silentwitness_common.atomic_io import write_text_atomic
from silentwitness_common.types import ReportSection

_LOG = logging.getLogger(__name__)

_DEBOUNCE_SECS = 0.05
_REPORT_FILENAME = "report.md"
_FINDINGS_FILENAME = "findings.json"

# Section composers in SECTION_ORDER, mapping ReportSection → callable
_SECTION_ORDER = (
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


class ReportRenderResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    content_hash: str
    bytes_written: int
    sections_rendered: int
    findings_approved_count: int
    findings_draft_count: int
    gaps_count: int


class ReportWriter:
    """Atomically renders cases/<case_id>/report.md on every state change.

    Construction is side-effect-free. Wire event subscription externally by
    calling on_finding_event directly (or via a bus) after construction.
    """

    def __init__(
        self,
        case_dir: Path,
        *,
        examiner: str,
        model_used: str,
        silentwitness_version: str,
    ) -> None:
        self._case_dir = case_dir
        self._examiner = examiner
        self._model_used = model_used
        self._silentwitness_version = silentwitness_version
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._render_count = 0  # for test introspection

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self) -> ReportRenderResult:
        """Load findings.json, compose 9 sections, atomically write report.md."""
        case_id = self._case_dir.name
        now = datetime.now(UTC)

        # Load findings.json
        findings = self._load_findings()

        # Partition into approved finding records vs observation records
        approved: list[dict[str, Any]] = []
        non_approved: list[dict[str, Any]] = []
        obs_map: dict[str, dict[str, Any]] = {}

        for item in findings:
            if not isinstance(item, dict):
                continue
            if "observation_id" in item and "text" in item:
                oid = item.get("observation_id")
                if isinstance(oid, str):
                    obs_map[oid] = item
            elif "finding_id" in item:
                if item.get("status") == "APPROVED":
                    approved.append(item)
                else:
                    non_approved.append(item)

        # Compose all 9 sections
        section_bodies: dict[ReportSection, str] = {
            ReportSection.EXECUTIVE_SUMMARY: compose_executive_summary(approved, obs_map),
            ReportSection.ENGAGEMENT_OVERVIEW: compose_engagement_overview(
                self._case_dir, case_id, self._examiner
            ),
            ReportSection.METHODOLOGY: compose_methodology(self._case_dir),
            ReportSection.FINDINGS: compose_findings(approved, obs_map),
            ReportSection.TIMELINE: compose_timeline(approved, obs_map),
            ReportSection.IOCS: compose_iocs(approved, obs_map),
            ReportSection.RECOMMENDATIONS: compose_recommendations(),
            ReportSection.GAPS: compose_gaps(self._case_dir),
            ReportSection.APPENDIX_AUDIT: compose_appendix_audit(self._case_dir),
        }

        # Build the body (everything after frontmatter)
        title_line = f"# Incident Report — Case {case_id}"
        section_parts = [title_line]
        for section in _SECTION_ORDER:
            section_parts.append(ReportTemplate.render_section(section, section_bodies[section]))

        body = "\n\n".join(section_parts) + "\n"
        # parse_frontmatter returns rest[close+5:] which includes the "\n" separator
        # between the closing --- and the body. Hash the same bytes it will return.
        content_hash = ReportTemplate.compute_content_hash("\n" + body)

        # Preserve created_at from existing report.md if it exists
        created_at = now
        report_path = self._case_dir / _REPORT_FILENAME
        if report_path.exists():
            try:
                existing_text = report_path.read_text(encoding="utf-8")
                prior_fm, _ = parse_frontmatter(existing_text)
                created_at = prior_fm.created_at
            except Exception:
                _LOG.debug("Could not read prior report.md created_at; using now", exc_info=True)

        fm = Frontmatter(
            case_id=case_id,
            examiner=self._examiner,
            status=ReportStatus.DRAFT,
            content_hash=content_hash,
            created_at=created_at,
            updated_at=now,
            silentwitness_version=self._silentwitness_version,
            model_used=self._model_used,
        )

        full_text = dump_frontmatter(fm) + "\n" + body
        encoded = full_text.encode("utf-8")
        write_text_atomic(report_path, full_text)

        # Count gaps from the gaps body
        gaps_body = section_bodies[ReportSection.GAPS]
        gaps_count = sum(1 for line in gaps_body.splitlines() if line.startswith("- "))

        with self._lock:
            self._render_count += 1

        return ReportRenderResult(
            content_hash=content_hash,
            bytes_written=len(encoded),
            sections_rendered=len(_SECTION_ORDER),
            findings_approved_count=len(approved),
            findings_draft_count=len(non_approved),
            gaps_count=gaps_count,
        )

    def on_finding_event(self, event: object) -> None:
        """Debounced subscriber callback — resets the 50ms render timer."""
        _ = event  # event details are not needed; findings.json is the source of truth
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(_DEBOUNCE_SECS, self._do_render)
            self._timer.daemon = True
            self._timer.start()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _do_render(self) -> None:
        """Timer callback — runs render() and resets the timer slot."""
        with self._lock:
            self._timer = None
        self.render()

    def _load_findings(self) -> list[Any]:
        """Load and parse findings.json; returns empty list if absent/empty."""
        path = self._case_dir / _FINDINGS_FILENAME
        if not path.exists():
            return []
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return []
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError(f"findings.json must be a JSON array; got {type(data).__name__}")
        return data


__all__ = ["ReportRenderResult", "ReportWriter"]
