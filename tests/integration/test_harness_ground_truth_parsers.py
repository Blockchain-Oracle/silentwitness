"""Integration tests for ground-truth parsers (story-ground-truth-parsers, ≥7 BDD scenarios)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
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


def test_case_trapdoor_returns_empty_when_absent(tmp_path: Path) -> None:
    from harness.ground_truth import case_trapdoor_parser

    synthetic_json = Path(case_trapdoor_parser.__file__).parent / "case-trapdoor.synthetic.json"
    assert not synthetic_json.exists(), "test assumes synthetic JSON is absent"
    findings = case_trapdoor_parser.parse()
    assert findings == []


# ---------------------------------------------------------------------------
# 7. Corrupting cached leakage-answers.pdf → SHA256MismatchError
# ---------------------------------------------------------------------------


def test_corrupted_pdf_raises_sha256_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from harness.ground_truth import nist_data_leakage_parser
    from harness.ground_truth.schema import SHA256MismatchError

    # Write a 1-byte file to a temp location and monkeypatch _PDF_PATH
    fake_pdf = tmp_path / "leakage-answers.pdf"
    fake_pdf.write_bytes(b"\x00")
    monkeypatch.setattr(nist_data_leakage_parser, "_PDF_PATH", fake_pdf)
    monkeypatch.setattr(nist_data_leakage_parser, "_CACHE_DIR", tmp_path)

    with pytest.raises(SHA256MismatchError) as exc_info:
        nist_data_leakage_parser._verify_pdf()

    assert "answer-key-sha256.txt" in str(exc_info.value)


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
# 10. GroundTruthFinding round-trips through model_dump_json / model_validate_json
# ---------------------------------------------------------------------------


def test_ground_truth_finding_roundtrip() -> None:
    from harness.ground_truth.nitroba_parser import parse

    for original in parse():
        serialized = original.model_dump_json()
        restored = GroundTruthFinding.model_validate_json(serialized)
        assert restored.id == original.id
        assert restored.dataset_id == original.dataset_id
