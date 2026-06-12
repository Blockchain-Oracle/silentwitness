"""Unit tests for harness/silentwitness — case_dir_reader helpers and runner utilities."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "case-harness"


class TestReadFindingsJson:
    def test_returns_at_least_five_findings(self) -> None:
        """read_findings_json returns ≥5 SwFinding objects from the fixture."""
        from harness.silentwitness.case_dir_reader import read_findings_json

        findings = read_findings_json(_FIXTURE)
        assert len(findings) >= 5

    def test_finding_ids_are_f_prefix(self) -> None:
        """Every returned SwFinding.id starts with 'F-'."""
        from harness.silentwitness.case_dir_reader import read_findings_json

        findings = read_findings_json(_FIXTURE)
        assert all(f.id.startswith("F-") for f in findings)

    def test_cited_audit_ids_propagated_from_observation(self) -> None:
        """cited_audit_ids on SwFinding are lifted from the linked observation record."""
        from harness.silentwitness.case_dir_reader import read_findings_json

        findings = read_findings_json(_FIXTURE)
        f1 = next(f for f in findings if f.id == "F-001")
        assert "sift-harness-20260612-001" in f1.cited_audit_ids

    def test_missing_findings_json_returns_empty(self, tmp_path: Path) -> None:
        from harness.silentwitness.case_dir_reader import read_findings_json

        assert read_findings_json(tmp_path) == []

    def test_non_list_json_returns_empty(self, tmp_path: Path) -> None:
        """read_findings_json returns [] when findings.json contains a JSON object."""
        from harness.silentwitness.case_dir_reader import read_findings_json

        (tmp_path / "findings.json").write_text('{"error": "failed"}')
        assert read_findings_json(tmp_path) == []


class TestReadHypothesisJsonl:
    def test_returns_at_least_eight_events(self) -> None:
        """read_hypothesis_jsonl returns ≥8 SwHypothesisEvent objects."""
        from harness.silentwitness.case_dir_reader import read_hypothesis_jsonl

        events, _ = read_hypothesis_jsonl(_FIXTURE)
        assert len(events) >= 8

    def test_exactly_two_pivots(self) -> None:
        """Exactly 2 hypothesis events have type='pivot'."""
        from harness.silentwitness.case_dir_reader import read_hypothesis_jsonl

        events, _ = read_hypothesis_jsonl(_FIXTURE)
        pivots = [e for e in events if e.type == "pivot"]
        assert len(pivots) == 2

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        from harness.silentwitness.case_dir_reader import read_hypothesis_jsonl

        events, notes = read_hypothesis_jsonl(tmp_path)
        assert events == []
        assert notes == []

    def test_malformed_lines_surfaced_in_notes(self, tmp_path: Path) -> None:
        """Malformed hypothesis JSONL lines produce a skip note."""
        from harness.silentwitness.case_dir_reader import read_hypothesis_jsonl

        (tmp_path / "audit").mkdir()
        (tmp_path / "audit" / "hypothesis.jsonl").write_text("NOT_JSON\n")
        _, notes = read_hypothesis_jsonl(tmp_path)
        assert any("malformed" in n for n in notes)


class TestReadAuditJsonl:
    def test_merges_across_files_returns_at_least_twelve(self) -> None:
        """read_audit_jsonl merges memory.jsonl + disk.jsonl + findings.jsonl (≥12 entries)."""
        from harness.silentwitness.case_dir_reader import read_audit_jsonl

        tool_calls, _notes = read_audit_jsonl(_FIXTURE)
        assert len(tool_calls) >= 12

    def test_skips_hypothesis_and_critic_files(self) -> None:
        """read_audit_jsonl does not include hypothesis or critic JSONL entries."""
        from harness.silentwitness.case_dir_reader import read_audit_jsonl

        tool_calls, _ = read_audit_jsonl(_FIXTURE)
        tool_names = {tc.tool for tc in tool_calls}
        assert "form" not in tool_names
        assert "agree" not in tool_names

    def test_missing_audit_dir_returns_empty(self, tmp_path: Path) -> None:
        from harness.silentwitness.case_dir_reader import read_audit_jsonl

        tool_calls, notes = read_audit_jsonl(tmp_path)
        assert tool_calls == []
        assert notes == []

    def test_malformed_lines_surfaced_in_notes(self, tmp_path: Path) -> None:
        """Malformed audit JSONL lines produce a skip note."""
        from harness.silentwitness.case_dir_reader import read_audit_jsonl

        (tmp_path / "audit").mkdir()
        (tmp_path / "audit" / "custom.jsonl").write_text("NOT_JSON\n")
        _, notes = read_audit_jsonl(tmp_path)
        assert any("skipped" in n for n in notes)


class TestCountGapsInReport:
    def test_returns_exactly_three(self) -> None:
        """count_gaps_in_report returns exactly 3 for the fixture report.md."""
        from harness.silentwitness.case_dir_reader import count_gaps_in_report

        assert count_gaps_in_report(_FIXTURE / "report.md") == 3

    def test_returns_zero_for_missing_file(self, tmp_path: Path) -> None:
        from harness.silentwitness.case_dir_reader import count_gaps_in_report

        assert count_gaps_in_report(tmp_path / "report.md") == 0

    def test_returns_zero_when_no_gaps_heading(self, tmp_path: Path) -> None:
        from harness.silentwitness.case_dir_reader import count_gaps_in_report

        report = tmp_path / "report.md"
        report.write_text("## Executive Summary\nSome content.\n")
        assert count_gaps_in_report(report) == 0

    def test_stops_at_next_heading(self, tmp_path: Path) -> None:
        """Bullet count stops before a subsequent ## heading."""
        from harness.silentwitness.case_dir_reader import count_gaps_in_report

        report = tmp_path / "report.md"
        report.write_text("## Gaps\n- item1\n- item2\n## Next Section\n- item3\n")
        assert count_gaps_in_report(report) == 2


class TestGetCommitSha:
    def test_nonzero_git_exit_returns_unknown(self) -> None:
        from harness.silentwitness.runner import _get_commit_sha

        with patch("harness.silentwitness.runner.subprocess.run") as m:
            m.return_value = MagicMock(returncode=1, stdout="")
            assert _get_commit_sha().startswith("unknown")

    def test_git_not_found_returns_unknown(self) -> None:
        from harness.silentwitness.runner import _get_commit_sha

        with patch("harness.silentwitness.runner.subprocess.run", side_effect=FileNotFoundError):
            assert _get_commit_sha() == "unknown (git not found on PATH)"

    def test_git_timeout_returns_unknown(self) -> None:
        from harness.silentwitness.runner import _get_commit_sha

        with patch(
            "harness.silentwitness.runner.subprocess.run",
            side_effect=subprocess.TimeoutExpired("git", 10),
        ):
            assert _get_commit_sha() == "unknown (git rev-parse timed out)"


class TestCheckExecutiveSummary:
    def test_empty_section_returns_none(self, tmp_path: Path) -> None:
        """Section immediately followed by next heading returns None."""
        from harness.silentwitness.runner import _check_executive_summary

        f = tmp_path / "report.md"
        f.write_text("## Executive Summary\n## Next\n")
        assert _check_executive_summary(f, 0.0) is None

    def test_populated_section_returns_elapsed(self, tmp_path: Path) -> None:
        from harness.silentwitness.runner import _check_executive_summary

        f = tmp_path / "report.md"
        f.write_text("## Executive Summary\nContent here.\n")
        assert _check_executive_summary(f, 0.0) is not None
