"""Unit tests for the dfVFS-free logic of ``silentwitness prepare``.

The dfVFS-backed extraction path is exercised by the real-evidence integration
run on the VPS (and the access-layer integration tests); here we cover the pure
mapping and the no-op early return, which must work on any dev machine without
the forensic C-extension stack installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from silentwitness_agent.cli_commands.prepare import _artifact_evidence_type, run
from silentwitness_common.types import EvidenceType


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
