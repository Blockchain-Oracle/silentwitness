"""Unit tests for the dfVFS-free logic of ``silentwitness prepare``.

The dfVFS-backed extraction path is exercised by the real-evidence integration
run on the VPS (and the access-layer integration tests); here we cover the pure
mapping and the no-op early return, which must work on any dev machine without
the forensic C-extension stack installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import silentwitness_agent.cli_commands.prepare as prepare_mod
from silentwitness_agent.cli_commands.prepare import _artifact_evidence_type, run
from silentwitness_common.types import EvidenceType
from silentwitness_mcp.evidence.registry import EvidenceRegistry


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("evtx", EvidenceType.EVTX),
        ("hive_software", EvidenceType.HIVE),
        ("hive_system", EvidenceType.HIVE),
        ("ntuser", EvidenceType.HIVE),
        ("usrclass", EvidenceType.HIVE),
        ("amcache", EvidenceType.HIVE),
        ("mft", EvidenceType.OTHER),
        ("usnjrnl", EvidenceType.OTHER),
        ("srum", EvidenceType.OTHER),
        ("prefetch", EvidenceType.OTHER),
        ("anything-unknown", EvidenceType.OTHER),
    ],
)
def test_artifact_evidence_type_mapping(label: str, expected: EvidenceType) -> None:
    assert _artifact_evidence_type(label) == expected


def test_run_returns_1_when_nothing_registered(tmp_path: Path) -> None:
    """With no DISK_IMAGE / archive registered, prepare is a no-op (exit 1) and
    never imports the dfVFS stack — so this runs anywhere."""
    case_dir = tmp_path / "cases" / "c1"
    case_dir.mkdir(parents=True)
    code = run(case_dir, "c1", examiner="examiner", no_color=True)
    assert code == 1


def test_run_returns_0_for_pcap_only_case(tmp_path: Path) -> None:
    """PCAP indexing is handled by the index phase, so prepare is a successful no-op."""
    case_dir = tmp_path / "cases" / "nitroba"
    case_dir.mkdir(parents=True)
    pcap = tmp_path / "nitroba.pcap"
    pcap.write_bytes(b"pcap")
    EvidenceRegistry(case_dir).register(pcap, EvidenceType.PCAP, "sift-examiner-20260616-001")

    code = run(case_dir, "nitroba", examiner="examiner", no_color=True)

    assert code == 0


def test_run_missing_forensics_extra_exits_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A base install without dfVFS must print install guidance, not a traceback."""
    case_dir = tmp_path / "cases" / "rocba"
    case_dir.mkdir(parents=True)
    disk = tmp_path / "rocba-cdrive.e01"
    disk.write_bytes(b"image")
    EvidenceRegistry(case_dir).register(disk, EvidenceType.DISK_IMAGE, "sift-examiner-20260616-001")

    def missing_access() -> None:
        raise ModuleNotFoundError("No module named 'dfvfs'", name="dfvfs")

    monkeypatch.setattr(prepare_mod, "_load_access", missing_access)

    code = run(case_dir, "rocba", examiner="examiner", no_color=True)

    captured = capsys.readouterr()
    assert code == 2
    assert "forensic evidence dependencies are unavailable" in captured.err
    assert "silentwitness[forensics]" in captured.err
