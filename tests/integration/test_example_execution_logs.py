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

            committed_files = [
                f.relative_to(_COMMITTED) for f in _COMMITTED.rglob("*") if f.is_file()
            ]
            fresh_files = [f.relative_to(tmp_out) for f in tmp_out.rglob("*") if f.is_file()]
            assert set(committed_files) == set(fresh_files), (
                f"tree shape drift; committed_only={set(committed_files) - set(fresh_files)} "
                f"fresh_only={set(fresh_files) - set(committed_files)}"
            )
            for rel in committed_files:
                assert (_COMMITTED / rel).read_bytes() == (tmp_out / rel).read_bytes(), (
                    f"byte drift on {rel}"
                )

    def test_two_independent_builds_byte_identical(self) -> None:
        """Two fresh builds must match each other byte-for-byte (catches
        datetime.now() / random / dict-iter drift independent of committed bytes)."""
        with tempfile.TemporaryDirectory() as ta, tempfile.TemporaryDirectory() as tb:
            for td in (ta, tb):
                r = subprocess.run(
                    [sys.executable, str(_SCRIPT), "--out", td],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                assert r.returncode == 0, r.stderr
            a, b = Path(ta), Path(tb)
            a_files = sorted(f.relative_to(a) for f in a.rglob("*") if f.is_file())
            b_files = sorted(f.relative_to(b) for f in b.rglob("*") if f.is_file())
            assert a_files == b_files
            for rel in a_files:
                assert (a / rel).read_bytes() == (b / rel).read_bytes(), f"non-deterministic: {rel}"


class TestHmacLedger:
    def test_ledger_carries_hmac_pbkdf_marker(self) -> None:
        rows = _read_jsonl(_CASE / "ledger.jsonl")
        assert len(rows) == 1
        entry = rows[0]
        assert "hmac_sha256" in entry
        assert len(entry["hmac_sha256"]) == 64  # type: ignore[arg-type]
        assert entry["pbkdf2_iter"] == 600000
        assert "EXAMPLE-not-a-real-secret-EXAMPLE" in str(entry["notes"])

    def test_ledger_hmac_recomputes_from_sentinel_key(self) -> None:
        """Recompute HMAC from sentinel key + canonical payload; assert equality."""
        import hashlib
        import hmac

        sentinel_key = b"EXAMPLE-not-a-real-secret-EXAMPLE"  # pragma: allowlist secret
        # Payload schema mirrors the build script
        ts = "2026-06-13T12:00:25Z"
        payload = f"F-example-001|APPROVED|sift-example-20260613-001|{ts}".encode()
        expected = hmac.new(sentinel_key, payload, hashlib.sha256).hexdigest()
        rows = _read_jsonl(_CASE / "ledger.jsonl")
        assert rows[0]["hmac_sha256"] == expected, (
            "ledger HMAC drifted from sentinel-key computation; "
            "the committed ledger is stale or the key/payload changed"
        )


class TestSyntheticGuards:
    def test_no_real_secret_shaped_strings_in_tree(self) -> None:
        """Tree-wide grep: no string looks like a real API key/secret/token."""
        import re

        # Match `secret|api_key|token|password = "long-string"` patterns
        secret_pat = re.compile(
            r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*"
            r'["\'][A-Za-z0-9+/_-]{20,}["\']'
        )
        for f in _COMMITTED.rglob("*"):
            if not f.is_file() or f.suffix in (".png", ".bin"):
                continue
            text = f.read_text(errors="ignore")
            for match in secret_pat.finditer(text):
                # Allow the sentinel form explicitly
                assert "EXAMPLE-not-a-real-secret-EXAMPLE" in match.group(0), (
                    f"{f.relative_to(_COMMITTED)}: real-secret-shaped match: {match.group(0)!r}"
                )

    def test_every_case_id_value_is_synthetic(self) -> None:
        """case_id values must be 'case-example-...' (no real-looking IDs)."""
        import re

        case_id_pat = re.compile(r'case_id\s*[:=]\s*["\']?([^"\'\n,}]+)["\']?')
        for f in _COMMITTED.rglob("*"):
            if not f.is_file() or f.suffix in (".png", ".bin"):
                continue
            text = f.read_text(errors="ignore")
            for match in case_id_pat.finditer(text):
                value = match.group(1).strip()
                assert value.startswith("case-example-"), (
                    f"{f.relative_to(_COMMITTED)}: non-synthetic case_id {value!r}"
                )


class TestSchemaSanity:
    def test_case_toml_roundtrips_via_tomllib(self) -> None:
        """case.toml parses and carries required keys."""
        import tomllib

        data = tomllib.loads((_CASE / ".silentwitness" / "case.toml").read_text())
        assert data["case_id"] == "case-example-001"
        assert "examiner" in data
        assert "created_at" in data

    def test_evidence_json_schema(self) -> None:
        """evidence.json: 1 record with 64-hex sha256, integer size_bytes."""
        data = json.loads((_CASE / "evidence.json").read_text())
        assert data["schema_version"] == 1
        assert len(data["records"]) == 1
        rec = data["records"][0]
        assert isinstance(rec["sha256"], str) and len(rec["sha256"]) == 64
        assert isinstance(rec["size_bytes"], int) and rec["size_bytes"] > 0
        assert "/evidence/sample_EXAMPLE.bin" in rec["path"]

    def test_index_readme_has_six_required_sections(self) -> None:
        """README.md must carry the 6 documented sections (intro + 5 H2 headings)."""
        text = (_COMMITTED / "README.md").read_text()
        for heading in (
            "## What this contains",
            "## How to read this",
            "## What it demonstrates",
            "## Synthetic disclosure",
            "## Source",
        ):
            assert heading in text, f"missing section: {heading}"


class TestReferentialIntegrity:
    def test_verify_link_audit_id_exists_in_audit_jsonl(self) -> None:
        """The [verify:audit_id] in report.md must resolve to an actual audit row."""
        import re

        text = (_CASE / "report.md").read_text()
        verify_ids = set(re.findall(r"\[verify:([a-zA-Z0-9-]+)\]", text))
        assert verify_ids, "report.md has no [verify:] tokens"
        all_audit_ids: set[str] = set()
        for jl in (_CASE / "audit").glob("*.jsonl"):
            for row in _read_jsonl(jl):
                if "audit_id" in row:
                    all_audit_ids.add(str(row["audit_id"]))
        missing = verify_ids - all_audit_ids
        assert not missing, f"dangling verify-links (no audit_id match): {missing}"
