"""Integration tests for ground-truth parsers (story-ground-truth-parsers, ≥7 BDD scenarios)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from harness.ground_truth import cli as cli_module
from harness.ground_truth.schema import GroundTruthFinding

_HARNESS_DIR = Path(__file__).resolve().parents[2] / "harness" / "ground_truth"
_CLI = str(_HARNESS_DIR / "cli.py")


# ---------------------------------------------------------------------------
# 1. nist_data_leakage_parser.parse() returns ≥20 findings
# ---------------------------------------------------------------------------


def test_nist_data_leakage_returns_at_least_20() -> None:
    from harness.ground_truth.nist_data_leakage_parser import parse

    findings = parse()
    assert len(findings) >= 20, f"expected ≥20, got {len(findings)}"


# ---------------------------------------------------------------------------
# 2. Every NDL finding has dataset_id == "nist-data-leakage" and source == "nist_pdf"
# ---------------------------------------------------------------------------


def test_nist_data_leakage_dataset_id_and_source() -> None:
    from harness.ground_truth.nist_data_leakage_parser import parse

    for f in parse():
        assert f.dataset_id == "nist-data-leakage", f"{f.id}: wrong dataset_id {f.dataset_id}"
        assert f.source == "nist_pdf", f"{f.id}: wrong source {f.source}"


# ---------------------------------------------------------------------------
# 3. Every NDL finding has ≥1 non-empty expected_artifact_substring
# ---------------------------------------------------------------------------


def test_nist_data_leakage_no_empty_substrings() -> None:
    from harness.ground_truth.nist_data_leakage_parser import parse

    for f in parse():
        assert len(f.expected_artifact_substrings) >= 1, f"{f.id}: empty substrings list"
        for s in f.expected_artifact_substrings:
            assert s.strip(), f"{f.id}: blank substring"


# ---------------------------------------------------------------------------
# 4. nist_hacking_case_parser returns ≥15 findings with the wireless MAC
# ---------------------------------------------------------------------------


def test_nist_hacking_case_returns_at_least_15_and_has_mac() -> None:
    from harness.ground_truth.nist_hacking_case_parser import parse

    findings = parse()
    assert len(findings) >= 15, f"expected ≥15, got {len(findings)}"
    mac_findings = [
        f for f in findings if any("00:02:B3:DD:00:A2" in s for s in f.expected_artifact_substrings)
    ]
    assert len(mac_findings) >= 1, "expected ≥1 finding with MAC 00:02:B3:DD:00:A2"


# ---------------------------------------------------------------------------
# 4b. NHC data-quality: every finding has correct dataset_id and non-empty substrings
# ---------------------------------------------------------------------------


def test_nist_hacking_case_data_quality() -> None:
    from harness.ground_truth.nist_hacking_case_parser import parse

    for f in parse():
        assert f.dataset_id == "nist-hacking-case", f"{f.id}: wrong dataset_id {f.dataset_id}"
        assert len(f.expected_artifact_substrings) >= 1, f"{f.id}: empty substrings list"
        for s in f.expected_artifact_substrings:
            assert s.strip(), f"{f.id}: blank substring"


# ---------------------------------------------------------------------------
# 5. nitroba_parser returns ≥6 findings
# ---------------------------------------------------------------------------


def test_nitroba_returns_at_least_6() -> None:
    from harness.ground_truth.nitroba_parser import parse

    findings = parse()
    assert len(findings) >= 6, f"expected ≥6, got {len(findings)}"
    assert all(f.dataset_id == "nitroba" for f in findings)
    assert all(f.source == "hand_crafted" for f in findings)


# ---------------------------------------------------------------------------
# 6. case_trapdoor_parser returns [] when synthetic JSON is absent
# ---------------------------------------------------------------------------


def test_case_trapdoor_returns_empty_when_absent() -> None:
    from harness.ground_truth import case_trapdoor_parser

    synthetic_json = Path(case_trapdoor_parser.__file__).parent / "case-trapdoor.synthetic.json"
    if synthetic_json.exists():
        pytest.skip(
            "case-trapdoor.synthetic.json exists (Epic 15 shipped) — skipping absent-file test"
        )
    findings = case_trapdoor_parser.parse()
    assert findings == []


# ---------------------------------------------------------------------------
# 6b. case_trapdoor_parser returns findings when synthetic JSON is present
# ---------------------------------------------------------------------------


def test_case_trapdoor_returns_findings_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from harness.ground_truth import case_trapdoor_parser

    synthetic_data = [
        {
            "id": "GT-CT-001",
            "dataset_id": "case-trapdoor",
            "category": "other",
            "summary": "Test synthetic finding",
            "expected_artifact_substrings": ["test-artifact"],
            "expected_path_globs": [],
            "supporting_question_id": None,
            "source": "synthetic_spec",
            "source_url": "https://example.com/synthetic",
            "source_excerpt": "Synthetic test finding for unit tests.",
        }
    ]
    synthetic_json = tmp_path / "case-trapdoor.synthetic.json"
    synthetic_json.write_text(json.dumps(synthetic_data), encoding="utf-8")
    monkeypatch.setattr(case_trapdoor_parser, "_SYNTHETIC_JSON", synthetic_json)

    findings = case_trapdoor_parser.parse()
    assert len(findings) == 1
    assert findings[0].id == "GT-CT-001"
    assert findings[0].dataset_id == "case-trapdoor"
    assert findings[0].source == "synthetic_spec"


# ---------------------------------------------------------------------------
# 7. Corrupting cached leakage-answers.pdf → SHA256MismatchError via parse()
# ---------------------------------------------------------------------------


def test_corrupted_pdf_raises_sha256_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from harness.ground_truth import nist_data_leakage_parser
    from harness.ground_truth.schema import SHA256MismatchError

    fake_pdf = tmp_path / "leakage-answers.pdf"
    fake_pdf.write_bytes(b"\x00")
    monkeypatch.setattr(nist_data_leakage_parser, "_PDF_PATH", fake_pdf)
    monkeypatch.setattr(nist_data_leakage_parser, "_CACHE_DIR", tmp_path)
    # Prevent re-download from hiding the mismatch — test the verify path via parse()
    monkeypatch.setattr(nist_data_leakage_parser, "_fetch_pdf", lambda: None)

    with pytest.raises(SHA256MismatchError):
        nist_data_leakage_parser.parse()


# ---------------------------------------------------------------------------
# 8. CLI nist-data-leakage exits 0 and emits valid JSON of GroundTruthFinding
# ---------------------------------------------------------------------------


def test_cli_nist_data_leakage_exits_0_valid_json() -> None:
    result = subprocess.run(
        [sys.executable, _CLI, "nist-data-leakage"],
        capture_output=True,
        text=True,
        cwd=str(_HARNESS_DIR.parents[1]),
    )
    assert result.returncode == 0, f"stdout={result.stdout[:500]!r} stderr={result.stderr[:500]!r}"
    findings_raw = json.loads(result.stdout)
    assert isinstance(findings_raw, list)
    assert len(findings_raw) >= 20
    for item in findings_raw:
        GroundTruthFinding.model_validate(item)


# ---------------------------------------------------------------------------
# 9. CLI unknown-dataset exits 1 with "unknown dataset_id" in stderr
# ---------------------------------------------------------------------------


def test_cli_unknown_dataset_exits_1() -> None:
    result = subprocess.run(
        [sys.executable, _CLI, "unknown-dataset"],
        capture_output=True,
        text=True,
        cwd=str(_HARNESS_DIR.parents[1]),
    )
    assert result.returncode == 1
    assert "unknown dataset_id" in result.stderr


# ---------------------------------------------------------------------------
# 9b. CLI exits 2 when the parser raises (in-process to get coverage credit)
# ---------------------------------------------------------------------------


def test_cli_exits_2_on_parser_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> list[GroundTruthFinding]:
        raise RuntimeError("injected test error")

    monkeypatch.setitem(cli_module._PARSERS, "nitroba", _boom)
    result = cli_module.main(["cli.py", "nitroba"])
    assert result == 2


# ---------------------------------------------------------------------------
# 9c. CLI main() in-process: known dataset returns 0 (coverage for cli.py)
# ---------------------------------------------------------------------------


def test_cli_main_known_dataset_returns_0(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from harness.ground_truth.schema import GroundTruthFinding

    fake_finding = GroundTruthFinding(
        id="GT-TEST-001",
        dataset_id="nitroba",
        category="other",
        summary="Test finding",
        expected_artifact_substrings=["test"],
        expected_path_globs=[],
        supporting_question_id=None,
        source="hand_crafted",
        source_url=None,
        source_excerpt=None,
    )
    monkeypatch.setitem(cli_module._PARSERS, "nitroba", lambda: [fake_finding])
    result = cli_module.main(["cli.py", "nitroba"])
    assert result == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 1
    assert parsed[0]["id"] == "GT-TEST-001"


# ---------------------------------------------------------------------------
# 10. GroundTruthFinding round-trips through model_dump_json / model_validate_json
# ---------------------------------------------------------------------------


def test_ground_truth_finding_roundtrip() -> None:
    from harness.ground_truth.nitroba_parser import parse

    for original in parse():
        serialized = original.model_dump_json()
        restored = GroundTruthFinding.model_validate_json(serialized)
        assert restored == original, f"{original.id}: round-trip mismatch"
