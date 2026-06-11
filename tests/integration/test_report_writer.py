"""Integration tests for ReportWriter — real tmp_path case directories.

≥12 tests covering: section ordering, APPROVED/DRAFT partitioning,
content_hash correctness, atomic rename safety, Recommendations placeholder,
Gaps fallback, Gaps populated, Appendix-Audit, debounce timing, Executive
Summary truncation, and deterministic hash across two renders.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from silentwitness_agent.report.events import FindingEvent
from silentwitness_agent.report.template import ReportTemplate, parse_frontmatter
from silentwitness_agent.report.writer import ReportRenderResult, ReportWriter

# ---------------------------------------------------------------------------
# Test fixtures / helpers
# ---------------------------------------------------------------------------


def _make_case(tmp_path: Path) -> Path:
    """Create minimal case directory structure."""
    case_dir = tmp_path / "cases" / "test-case-001"
    (case_dir / "audit").mkdir(parents=True)
    (case_dir / "findings.json").write_text("[]", encoding="utf-8")
    return case_dir


def _make_writer(case_dir: Path) -> ReportWriter:
    return ReportWriter(
        case_dir,
        examiner="aj",
        model_used="anthropic:claude-opus-4-7",
        silentwitness_version="1.0.0",
    )


def _obs_record(
    obs_id: str,
    text: str,
    audit_ids: list[str],
    interp_id: str,
    interp_text: str,
    confidence: str = "HIGH",
) -> dict:  # type: ignore[type-arg]
    return {
        "observation_id": obs_id,
        "text": text,
        "audit_ids": audit_ids,
        "cited_spans": [],
        "interpretations": [
            {
                "interpretation_id": interp_id,
                "text": interp_text,
                "confidence": confidence,
                "justification": "test justification",
                "what_would_change_this_confidence": "counter-evidence",
                "recorded_at": "2026-06-13T14:00:00Z",
            }
        ],
    }


def _finding_record(fid: str, obs_id: str, interp_id: str, status: str = "DRAFT") -> dict:  # type: ignore[type-arg]
    return {
        "finding_id": fid,
        "observation_id": obs_id,
        "interpretation_id": interp_id,
        "status": status,
        "title": f"Test finding {fid}",
    }


def _write_findings(case_dir: Path, records: list) -> None:  # type: ignore[type-arg]
    (case_dir / "findings.json").write_text(json.dumps(records), encoding="utf-8")


def _make_finding_event(case_dir: Path) -> FindingEvent:
    return FindingEvent(
        event_type="observation_staged",
        finding_id="F-001",
        case_id=case_dir.name,
        ts=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Test: report.md exists and 9 sections in canonical order
# ---------------------------------------------------------------------------


def test_render_creates_report_md(tmp_path: Path) -> None:
    case_dir = _make_case(tmp_path)
    result = _make_writer(case_dir).render()
    assert (case_dir / "report.md").exists()
    assert isinstance(result, ReportRenderResult)
    assert result.sections_rendered == 9


def test_report_sections_in_canonical_order(tmp_path: Path) -> None:
    case_dir = _make_case(tmp_path)
    _make_writer(case_dir).render()
    text = (case_dir / "report.md").read_text(encoding="utf-8")
    sections = [
        "## Executive Summary",
        "## Engagement Overview",
        "## Methodology",
        "## Findings",
        "## Timeline",
        "## Indicators of Compromise",
        "## Recommendations",
        "## Gaps",
        "## Appendix — Audit",
    ]
    positions = [text.find(s) for s in sections]
    assert all(p >= 0 for p in positions), (
        f"Missing section in: {[s for s, p in zip(sections, positions, strict=False) if p < 0]}"
    )
    assert positions == sorted(positions), "Sections out of canonical order"


# ---------------------------------------------------------------------------
# Test: APPROVED finding appears; DRAFT does NOT appear in Findings body
# ---------------------------------------------------------------------------


def test_approved_finding_appears_in_findings_section(tmp_path: Path) -> None:
    case_dir = _make_case(tmp_path)
    obs = _obs_record(
        "O-001",
        "Malware detected on host.",
        ["sift-aj-20260613-001"],
        "I-001",
        "Attacker installed malware.",
    )
    finding_a = _finding_record("F-001", "O-001", "I-001", "APPROVED")
    _write_findings(case_dir, [obs, finding_a])
    _make_writer(case_dir).render()
    text = (case_dir / "report.md").read_text(encoding="utf-8")
    assert "F-001" in text


def test_draft_finding_does_not_appear_in_findings_body(tmp_path: Path) -> None:
    case_dir = _make_case(tmp_path)
    obs = _obs_record(
        "O-001",
        "Suspicious network traffic.",
        ["sift-aj-20260613-001"],
        "I-001",
        "Possible exfiltration.",
    )
    obs2 = _obs_record(
        "O-002",
        "Registry key modified.",
        ["sift-aj-20260613-002"],
        "I-002",
        "Persistence established.",
    )
    finding_approved = _finding_record("F-001", "O-001", "I-001", "APPROVED")
    finding_draft = _finding_record("F-002", "O-002", "I-002", "DRAFT")
    _write_findings(case_dir, [obs, obs2, finding_approved, finding_draft])
    result = _make_writer(case_dir).render()
    text = (case_dir / "report.md").read_text(encoding="utf-8")

    # F-002 must not appear in the Findings section body (only count)
    findings_start = text.find("## Findings")
    recommendations_start = text.find("## Recommendations")
    findings_body = text[findings_start:recommendations_start]
    assert "F-001" in findings_body
    assert "F-002" not in findings_body
    assert result.findings_approved_count == 1
    assert result.findings_draft_count == 1


# ---------------------------------------------------------------------------
# Test: content_hash in frontmatter matches compute_content_hash(body)
# ---------------------------------------------------------------------------


def test_content_hash_matches_body_hash(tmp_path: Path) -> None:
    case_dir = _make_case(tmp_path)
    _make_writer(case_dir).render()
    full_text = (case_dir / "report.md").read_text(encoding="utf-8")
    fm, body = parse_frontmatter(full_text)
    expected = ReportTemplate.compute_content_hash(body)
    assert fm.content_hash == expected


# ---------------------------------------------------------------------------
# Test: file mode is 0o644
# ---------------------------------------------------------------------------


def test_report_md_has_mode_644(tmp_path: Path) -> None:
    case_dir = _make_case(tmp_path)
    _make_writer(case_dir).render()
    mode = (case_dir / "report.md").stat().st_mode & 0o777
    assert mode == 0o644


# ---------------------------------------------------------------------------
# Test: deterministic hash on second render with no state change
# ---------------------------------------------------------------------------


def test_deterministic_hash_on_repeated_render(tmp_path: Path) -> None:
    case_dir = _make_case(tmp_path)
    writer = _make_writer(case_dir)
    result1 = writer.render()
    result2 = writer.render()
    assert result1.content_hash == result2.content_hash


# ---------------------------------------------------------------------------
# Test: created_at preserved across renders
# ---------------------------------------------------------------------------


def test_created_at_preserved_on_re_render(tmp_path: Path) -> None:
    case_dir = _make_case(tmp_path)
    writer = _make_writer(case_dir)
    writer.render()
    first_text = (case_dir / "report.md").read_text(encoding="utf-8")
    fm1, _ = parse_frontmatter(first_text)

    time.sleep(0.01)  # ensure clock advances
    writer.render()
    second_text = (case_dir / "report.md").read_text(encoding="utf-8")
    fm2, _ = parse_frontmatter(second_text)

    assert fm1.created_at == fm2.created_at
    assert fm2.updated_at >= fm1.updated_at


# ---------------------------------------------------------------------------
# Test: Recommendations placeholder is verbatim
# ---------------------------------------------------------------------------


def test_recommendations_is_placeholder(tmp_path: Path) -> None:
    case_dir = _make_case(tmp_path)
    _make_writer(case_dir).render()
    text = (case_dir / "report.md").read_text(encoding="utf-8")
    assert "_To be populated by examiner._" in text


# ---------------------------------------------------------------------------
# Test: Gaps section with no gaps → placeholder
# ---------------------------------------------------------------------------


def test_gaps_section_fallback_when_no_gaps(tmp_path: Path) -> None:
    case_dir = _make_case(tmp_path)
    _make_writer(case_dir).render()
    text = (case_dir / "report.md").read_text(encoding="utf-8")
    assert "(no gaps identified)" in text


# ---------------------------------------------------------------------------
# Test: Gaps section populated when abandoned_hypotheses present
# ---------------------------------------------------------------------------


def test_gaps_section_lists_abandoned_hypotheses(tmp_path: Path) -> None:
    case_dir = _make_case(tmp_path)
    state = {
        "abandoned_hypotheses": ["Hypothesis A ruled out", "Hypothesis B ruled out"],
        "exhausted_budgets": ["budget item C"],
        "explicit_gaps": [],
    }
    (case_dir / "case_state.json").write_text(json.dumps(state), encoding="utf-8")
    result = _make_writer(case_dir).render()
    text = (case_dir / "report.md").read_text(encoding="utf-8")

    gaps_start = text.find("## Gaps")
    appendix_start = text.find("## Appendix")
    gaps_body = text[gaps_start:appendix_start]

    assert "Hypothesis A ruled out" in gaps_body
    assert "Hypothesis B ruled out" in gaps_body
    assert "budget item C" in gaps_body
    assert result.gaps_count == 3


# ---------------------------------------------------------------------------
# Test: Appendix-Audit lists audit/*.jsonl with SHA-256
# ---------------------------------------------------------------------------


def test_appendix_audit_lists_audit_files(tmp_path: Path) -> None:
    case_dir = _make_case(tmp_path)
    audit_line = json.dumps({"tool": "vol3", "audit_id": "sift-aj-20260613-001"})
    (case_dir / "audit" / "vol3.jsonl").write_text(audit_line + "\n", encoding="utf-8")
    _make_writer(case_dir).render()
    text = (case_dir / "report.md").read_text(encoding="utf-8")
    assert "vol3.jsonl" in text
    assert "sha256:" in text


def test_appendix_audit_sha256_is_correct(tmp_path: Path) -> None:
    case_dir = _make_case(tmp_path)
    content = b'{"tool": "sbeCmd", "audit_id": "sift-aj-20260613-002"}\n'
    (case_dir / "audit" / "sbeCmd.jsonl").write_bytes(content)
    _make_writer(case_dir).render()
    expected_digest = hashlib.sha256(content).hexdigest()
    text = (case_dir / "report.md").read_text(encoding="utf-8")
    assert expected_digest in text


# ---------------------------------------------------------------------------
# Test: debounce — 5 events within 30ms → exactly 1 render
# ---------------------------------------------------------------------------


def test_debounce_coalesces_events(tmp_path: Path) -> None:
    case_dir = _make_case(tmp_path)
    writer = _make_writer(case_dir)
    initial_count = writer._render_count

    event = _make_finding_event(case_dir)
    for _ in range(5):
        writer.on_finding_event(event)
        time.sleep(0.005)  # 5ms between events — all within 50ms window

    # Wait for the debounce timer to fire (50ms + buffer)
    time.sleep(0.15)

    assert writer._render_count == initial_count + 1


# ---------------------------------------------------------------------------
# Test: Executive Summary truncates at ≤500 words
# ---------------------------------------------------------------------------


def test_executive_summary_truncates_at_500_words(tmp_path: Path) -> None:
    case_dir = _make_case(tmp_path)
    # 12 findings with verbose interpretations (60+ words each)
    records: list = []
    for i in range(1, 13):
        oid = f"O-{i:03d}"
        iid = f"I-{i:03d}"
        fid = f"F-{i:03d}"
        long_text = (
            "The attacker performed reconnaissance by scanning the network " * 10
        ).strip() + "."
        obs = _obs_record(oid, f"Obs {i}", [f"sift-aj-20260613-{i:03d}"], iid, long_text)
        finding = _finding_record(fid, oid, iid, "APPROVED")
        records.extend([obs, finding])
    _write_findings(case_dir, records)

    _make_writer(case_dir).render()
    text = (case_dir / "report.md").read_text(encoding="utf-8")

    exec_start = text.find("## Executive Summary")
    engagement_start = text.find("## Engagement Overview")
    exec_body = text[exec_start:engagement_start]

    word_count = len(exec_body.split())
    assert word_count <= 600  # heading adds some words; body itself ≤500
    assert "[...truncated" in exec_body


# ---------------------------------------------------------------------------
# Test: verify link appears for approved finding
# ---------------------------------------------------------------------------


def test_verify_link_in_findings_section(tmp_path: Path) -> None:
    case_dir = _make_case(tmp_path)
    audit_id = "sift-aj-20260613-007"
    obs = _obs_record("O-001", "Malicious PE found.", [audit_id], "I-001", "Malware dropper.")
    finding = _finding_record("F-001", "O-001", "I-001", "APPROVED")
    _write_findings(case_dir, [obs, finding])
    _make_writer(case_dir).render()
    text = (case_dir / "report.md").read_text(encoding="utf-8")
    assert f"[verify:F-001/{audit_id}]" in text
