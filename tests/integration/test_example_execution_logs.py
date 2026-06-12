"""Tests for docs/EXAMPLE_EXECUTION_LOGS/ (story-execution-logs-export)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "build_example_execution_logs.py"
_COMMITTED = _REPO / "docs" / "EXAMPLE_EXECUTION_LOGS"
_CASE = _COMMITTED / "case-example-001_EXAMPLE"


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


class TestCommittedTreeShape:
    def test_all_required_files_present(self) -> None:
        for relpath in (
            ".silentwitness/case.toml",
            "evidence.json",
            "audit/memory.jsonl",
            "audit/disk.jsonl",
            "audit/log.jsonl",
            "audit/findings.jsonl",
            "audit/hypothesis.jsonl",
            "audit/critic.jsonl",
            "findings.json",
            "report.md",
            "ledger.jsonl",
        ):
            assert (_CASE / relpath).exists(), f"missing {relpath}"
        assert (_COMMITTED / "README.md").exists()

    def test_filenames_carry_example_suffix(self) -> None:
        """The case directory MUST carry _EXAMPLE to mark the simulation status."""
        assert _CASE.name.endswith("_EXAMPLE")

    def test_all_jsonl_files_are_valid_jsonl(self) -> None:
        for jsonl in (_CASE / "audit").glob("*.jsonl"):
            rows = _read_jsonl(jsonl)
            assert rows, f"{jsonl.name} is empty"


class TestAuditTrailShape:
    def test_hypothesis_jsonl_has_exactly_five_events(self) -> None:
        rows = _read_jsonl(_CASE / "audit" / "hypothesis.jsonl")
        assert len(rows) == 5

    def test_hypothesis_jsonl_has_exactly_one_pivot(self) -> None:
        """FR7 self-correction visible: exactly one pivot transition."""
        rows = _read_jsonl(_CASE / "audit" / "hypothesis.jsonl")
        pivots = [r for r in rows if r.get("transition") == "pivot"]
        assert len(pivots) == 1
        assert "vol3 symbol-table mismatch" in str(pivots[0].get("reason", ""))

    def test_critic_jsonl_has_challenge_and_approved(self) -> None:
        rows = _read_jsonl(_CASE / "audit" / "critic.jsonl")
        verdicts = [r.get("verdict") for r in rows]
        assert verdicts.count("CHALLENGE") == 1
        assert verdicts.count("APPROVED") >= 1

    def test_findings_jsonl_envelope_is_approved_with_entity_matches(self) -> None:
        rows = _read_jsonl(_CASE / "audit" / "findings.jsonl")
        assert len(rows) == 1
        env = rows[0]
        assert env["status"] == "APPROVED"
        assert env["citation_gate"] == "PASS"
        assert isinstance(env["entity_gate_matches"], list)
        assert env["entity_gate_matches"]  # non-empty

    def test_three_tool_calls_across_backends(self) -> None:
        """FR5: at least one tool call per backend (memory, disk, log)."""
        for backend, fname, tool in (
            ("memory", "memory.jsonl", "vol_pslist"),
            ("disk", "disk.jsonl", "parse_mft"),
            ("log", "log.jsonl", "parse_evtx"),
        ):
            rows = _read_jsonl(_CASE / "audit" / fname)
            assert len(rows) >= 1
            assert rows[0]["backend"] == backend
            assert rows[0]["tool_name"] == tool


class TestReportShape:
    def test_report_has_gaps_and_appendix_audit(self) -> None:
        text = (_CASE / "report.md").read_text()
        assert text.count("## Gaps") == 1
        assert text.count("## Appendix-Audit") == 1

    def test_report_contains_verify_link(self) -> None:
        text = (_CASE / "report.md").read_text()
        assert "[verify:sift-example-" in text


class TestDeterministicRegeneration:
    def test_rerun_produces_byte_identical_output(self) -> None:
        """Re-running the script must match the committed tree byte-for-byte."""
        with tempfile.TemporaryDirectory() as td:
            tmp_out = Path(td)
            r = subprocess.run(
                [sys.executable, str(_SCRIPT), "--out", str(tmp_out)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert r.returncode == 0, r.stderr

            for committed_file in _COMMITTED.rglob("*"):
                if not committed_file.is_file():
                    continue
                rel = committed_file.relative_to(_COMMITTED)
                fresh = tmp_out / rel
                assert fresh.exists(), f"regen missed {rel}"
                assert committed_file.read_bytes() == fresh.read_bytes(), (
                    f"byte drift on {rel}; committed differs from fresh build"
                )


class TestHmacLedger:
    def test_ledger_carries_hmac_pbkdf_marker(self) -> None:
        rows = _read_jsonl(_CASE / "ledger.jsonl")
        assert len(rows) == 1
        entry = rows[0]
        assert "hmac_sha256" in entry
        assert len(entry["hmac_sha256"]) == 64  # type: ignore[arg-type]
        assert entry["pbkdf2_iter"] == 600000
        assert "EXAMPLE-not-a-real-secret-EXAMPLE" in str(entry["notes"])
