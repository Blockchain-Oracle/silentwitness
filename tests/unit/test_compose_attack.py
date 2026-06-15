"""Unit tests for compose_attack_techniques — the MITRE ATT&CK report overlay."""

from __future__ import annotations

import json
from pathlib import Path

from silentwitness_agent.report.compose import compose_attack_techniques

_T = "tags=lateral_movement,t1021.001"


def _write(case_dir: Path, findings: list[dict]) -> None:
    (case_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")


def test_from_sigma_tags(tmp_path: Path) -> None:
    _write(
        tmp_path,
        [
            {
                "observation_id": "O-001",
                "cited_spans": [
                    {"record_id": 1, "span_text": "SIGMA tags=credential_access,t1110 id=4625"}
                ],
            },
            {
                "observation_id": "O-002",
                "cited_spans": [
                    {"record_id": 2, "span_text": "SIGMA tags=lateral_movement,t1021.001 id=4624"}
                ],
            },
        ],
    )
    out = compose_attack_techniques(tmp_path)
    assert out.startswith("| Technique | Tactic | Evidenced by |")
    assert "T1110" in out and "credential access" in out and "O-001" in out
    assert "T1021.001" in out and "lateral movement" in out and "O-002" in out


def test_dedupes_and_aggregates(tmp_path: Path) -> None:
    _write(
        tmp_path,
        [
            {"observation_id": "O-001", "cited_spans": [{"record_id": 1, "span_text": _T}]},
            {"observation_id": "O-002", "cited_spans": [{"record_id": 2, "span_text": _T}]},
        ],
    )
    out = compose_attack_techniques(tmp_path)
    assert out.count("T1021.001") == 1
    assert "O-001, O-002" in out


def test_no_tags_placeholder(tmp_path: Path) -> None:
    _write(
        tmp_path,
        [{"observation_id": "O-1", "cited_spans": [{"record_id": 1, "span_text": "EventID=4688"}]}],
    )
    assert "No MITRE ATT&CK" in compose_attack_techniques(tmp_path)


def test_missing_findings(tmp_path: Path) -> None:
    assert "No MITRE ATT&CK" in compose_attack_techniques(tmp_path)
