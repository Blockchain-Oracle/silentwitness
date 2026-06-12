"""Integration tests for harness dataset manifests (story-dataset-manifests, ≥6 BDD scenarios)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from harness.datasets.schema import DatasetManifest

_MANIFEST_DIR = Path(__file__).resolve().parents[2] / "harness" / "datasets"
_STUB_PCAP = _MANIFEST_DIR / "stubs" / "nitroba-stub.pcap"
_VERIFY = str(_MANIFEST_DIR / "verify_manifest.py")


def _load(name: str) -> DatasetManifest:
    raw = (_MANIFEST_DIR / name).read_text(encoding="utf-8")
    return DatasetManifest.model_validate(json.loads(raw))


# ---------------------------------------------------------------------------
# 1. Every committed manifest parses against DatasetManifest
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "manifest_file",
    [
        "nitroba.manifest.json",
        "nitroba-stub.manifest.json",
        "nist-data-leakage.manifest.json",
        "nist-hacking-case.manifest.json",
        "case-trapdoor.manifest.json",
    ],
)
def test_all_manifests_parse(manifest_file: str) -> None:
    """Every committed manifest must parse against DatasetManifest without error."""
    manifest = _load(manifest_file)
    assert isinstance(manifest, DatasetManifest)


# ---------------------------------------------------------------------------
# 2. verify_manifest.py --stub-only exits 0 against the committed stub
# ---------------------------------------------------------------------------


def test_verify_stub_only_exits_0() -> None:
    result = subprocess.run(
        [sys.executable, _VERIFY, "--stub-only"],
        capture_output=True,
        text=True,
        cwd=str(_MANIFEST_DIR.parents[1]),
    )
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    combined = result.stdout + result.stderr
    # Rich table shows dataset_id="nitroba" and the match result; file path may be truncated
    assert "nitroba" in combined
    assert "match=True" in combined


# ---------------------------------------------------------------------------
# 3. verify_manifest.py against full manifests skips missing files (no --strict)
# ---------------------------------------------------------------------------


def test_verify_full_manifests_skips_missing() -> None:
    """Without --strict, missing evidence binaries are skipped, exit 0."""
    result = subprocess.run(
        [sys.executable, _VERIFY],
        capture_output=True,
        text=True,
        cwd=str(_MANIFEST_DIR.parents[1]),
    )
    # Missing full images → exit 0 (skipped), not exit 1 (mismatch)
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    # Rich may wrap "missing (skipped)" across table row lines; check for either form
    combined = result.stdout + result.stderr
    assert "missing" in combined


# ---------------------------------------------------------------------------
# 4. verify_manifest.py --strict exits 2 when evidence file is missing
# ---------------------------------------------------------------------------


def test_verify_strict_exits_2_on_missing(tmp_path: Path) -> None:
    """--strict exits 2 if any pinned evidence file is absent from disk."""
    stub_manifest = _MANIFEST_DIR / "nist-hacking-case.manifest.json"
    result = subprocess.run(
        [sys.executable, _VERIFY, "--strict", "--manifest", str(stub_manifest)],
        capture_output=True,
        text=True,
        cwd=str(_MANIFEST_DIR.parents[1]),
    )
    assert result.returncode == 2, f"stdout={result.stdout!r} stderr={result.stderr!r}"


# ---------------------------------------------------------------------------
# 5. Corrupting stub byte 0 → verify_manifest.py --stub-only exits 1
# ---------------------------------------------------------------------------


def test_corrupted_stub_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A single-byte mutation of the stub pcap must cause verify to exit 1."""
    original = _STUB_PCAP.read_bytes()
    corrupted = bytes([original[0] ^ 0xFF]) + original[1:]
    fake_stub = tmp_path / "stubs" / "nitroba-stub.pcap"
    fake_stub.parent.mkdir(parents=True)
    fake_stub.write_bytes(corrupted)

    # Copy stub manifest to tmp_path with relative_path pointing at our fake stub
    stub_manifest_json = json.loads(
        (_MANIFEST_DIR / "nitroba-stub.manifest.json").read_text(encoding="utf-8")
    )
    tweaked_manifest = tmp_path / "nitroba-stub.manifest.json"
    tweaked_manifest.write_text(json.dumps(stub_manifest_json, indent=2) + "\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, _VERIFY, "--stub-only", "--manifest", str(tweaked_manifest)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert result.returncode == 1
    combined = result.stdout + result.stderr
    assert "sha256 mismatch" in combined or "match=False" in combined


# ---------------------------------------------------------------------------
# 6. nist-hacking-case LLM_memorization_risk is exactly "very_high"
# ---------------------------------------------------------------------------


def test_nist_hacking_case_memorization_risk_very_high() -> None:
    manifest = _load("nist-hacking-case.manifest.json")
    assert manifest.LLM_memorization_risk == "very_high"
    assert "writeups" in manifest.memorization_risk_note


# ---------------------------------------------------------------------------
# 7. nist-data-leakage ground_truth_status is "public_pdf" + pc.E01 in evidence_files
# ---------------------------------------------------------------------------


def test_nist_data_leakage_ground_truth_and_evidence() -> None:
    manifest = _load("nist-data-leakage.manifest.json")
    assert manifest.ground_truth_status == "public_pdf"
    paths = [ef.relative_path for ef in manifest.evidence_files]
    assert any(p.endswith("pc.E01") for p in paths)


# ---------------------------------------------------------------------------
# 8. dataset_id round-trips through model_dump_json / model_validate_json
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "manifest_file",
    [
        "nitroba.manifest.json",
        "nist-hacking-case.manifest.json",
        "case-trapdoor.manifest.json",
    ],
)
def test_dataset_id_roundtrip(manifest_file: str) -> None:
    original = _load(manifest_file)
    serialized = original.model_dump_json()
    restored = DatasetManifest.model_validate_json(serialized)
    assert restored.dataset_id == original.dataset_id


# ---------------------------------------------------------------------------
# 9. case-trapdoor manifest passes schema validation with placeholder sha256
# ---------------------------------------------------------------------------


def test_case_trapdoor_placeholder_validates() -> None:
    manifest = _load("case-trapdoor.manifest.json")
    assert manifest.sha256 == "<filled-by-epic-15>"
    assert manifest.ground_truth_status == "synthetic"
    assert manifest.LLM_memorization_risk == "low"


# ---------------------------------------------------------------------------
# 10. Nitroba manifest sha256 matches the story-specified pin
# ---------------------------------------------------------------------------


def test_nitroba_sha256_matches_spec() -> None:
    manifest = _load("nitroba.manifest.json")
    assert manifest.sha256 == "2b77a9eaefc1d6af163d1ba793c96dbccacb04e6befdf1a0b01f8c67553ec2fb"
    assert manifest.size_bytes == 56180821
