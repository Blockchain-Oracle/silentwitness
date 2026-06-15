"""ReportWriter — atomic Markdown report renderer for one case directory.

Callers invoke render() directly (see cli_commands/approve.py) to (re)build
report.md from findings.json on demand.

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

from pydantic import BaseModel, ConfigDict, Field

from silentwitness_agent.report.compose import (
    compose_appendix_audit,
    compose_attack_techniques,
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
    SECTION_ORDER,
    Frontmatter,
    ReportStatus,
    ReportTemplate,
    dump_frontmatter,
    parse_frontmatter,
)
from silentwitness_common.atomic_io import write_text_atomic
from silentwitness_common.types import ReportSection

_LOG = logging.getLogger(__name__)

_REPORT_FILENAME = "report.md"
_FINDINGS_FILENAME = "findings.json"


class ReportRenderResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    # content_hash must match ReportTemplate.compute_content_hash output format
    content_hash: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    bytes_written: int = Field(gt=0)
    sections_rendered: int = Field(gt=0)
    findings_approved_count: int = Field(ge=0)
    findings_draft_count: int = Field(ge=0)
    gaps_count: int = Field(ge=0)


class ReportWriter:
    """Atomically renders cases/<case_id>/report.md from findings.json.

    Construction is side-effect-free; call render() to (re)build the report.
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
        self._lock = threading.Lock()  # guards _render_count
        self._render_count = 0  # for test introspection

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self) -> ReportRenderResult:
        """Load findings.json, compose 10 sections, atomically write report.md."""
        case_id = self._case_dir.name
        now = datetime.now(UTC)

        # Load findings.json
        findings = self._load_findings()

        # Partition into approved finding records vs observation records
        approved: list[dict[str, Any]] = []
        draft: list[dict[str, Any]] = []
        obs_map: dict[str, dict[str, Any]] = {}
        for item in findings:
            if not isinstance(item, dict):
                continue
            if "observation_id" in item and "text" in item:
                oid = item.get("observation_id")
                if isinstance(oid, str):
                    obs_map[oid] = item
            elif "finding_id" in item:
                status = item.get("status")
                if status == "APPROVED":
                    approved.append(item)
                elif status == "DRAFT":
                    draft.append(item)

        # Compose all 10 sections
        section_bodies: dict[ReportSection, str] = {
            ReportSection.EXECUTIVE_SUMMARY: compose_executive_summary(approved, obs_map),
            ReportSection.ENGAGEMENT_OVERVIEW: compose_engagement_overview(
                self._case_dir, case_id, self._examiner
            ),
            ReportSection.METHODOLOGY: compose_methodology(self._case_dir),
            ReportSection.FINDINGS: compose_findings(approved, obs_map),
            ReportSection.TIMELINE: compose_timeline(approved, obs_map),
            ReportSection.IOCS: compose_iocs(approved, obs_map),
            ReportSection.ATTACK: compose_attack_techniques(self._case_dir),
            ReportSection.RECOMMENDATIONS: compose_recommendations(),
            ReportSection.GAPS: compose_gaps(self._case_dir),
            ReportSection.APPENDIX_AUDIT: compose_appendix_audit(self._case_dir),
        }

        # Build the body (everything after frontmatter)
        title_line = f"# Incident Report — Case {case_id}"
        section_parts = [title_line]
        for section in SECTION_ORDER:
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
            except (OSError, ValueError):
                _LOG.warning("Could not read prior report.md created_at; using now", exc_info=True)

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
            sections_rendered=len(SECTION_ORDER),
            findings_approved_count=len(approved),
            findings_draft_count=len(draft),
            gaps_count=gaps_count,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

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
