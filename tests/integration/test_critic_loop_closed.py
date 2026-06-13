"""Integration test — critic closed-loop: stage findings, apply verdicts, assert state.

E2E scenario: 3 findings → 1 AGREE + 1 CHALLENGE + 1 REJECT → verify all four
output artefacts are consistent.
"""

from __future__ import annotations

import json
from pathlib import Path

from silentwitness_agent.critic import CriticVerdictRecord
from silentwitness_agent.critic_handler import handle_critic_verdicts


def _make_findings(case_dir: Path) -> None:
    findings = [
        {
            "finding_id": "F-001",
            "status": "DRAFT",
            "observation_id": "O-001",
            "interpretation_id": "I-001",
            "title": "Lateral movement via PsExec",
        },
        {
            "finding_id": "F-002",
            "status": "DRAFT",
            "observation_id": "O-002",
            "interpretation_id": "I-002",
            "title": "C2 via HTTPS to 203.0.113.42",
        },
        {
            "finding_id": "F-003",
            "status": "DRAFT",
            "observation_id": "O-003",
            "interpretation_id": "I-003",
            "title": "Persistence via scheduled task",
        },
    ]
    (case_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")


def test_critic_loop_closed_e2e(tmp_path: Path) -> None:
    """Stage 3 findings, apply 1 AGREE / 1 CHALLENGE / 1 REJECT, assert all state."""
    case_dir = tmp_path
    (case_dir / "audit").mkdir()
    _make_findings(case_dir)

    pending_critiques: list[CriticVerdictRecord] = []
    verdicts = [
        CriticVerdictRecord(
            finding_id="F-001",
            verdict="AGREE",
            reason="PsExec evidence clearly present in prefetch",
        ),
        CriticVerdictRecord(
            finding_id="F-002",
            verdict="CHALLENGE",
            reason="interpretation requires intercepted-traffic evidence; tool install only",
            suggested_revision="downgrade confidence or corroborate via captured-pcap",
            missing_corroboration=["network/zeek pcap"],
        ),
        CriticVerdictRecord(
            finding_id="F-003",
            verdict="REJECT",
            reason="scheduled task entity not found in cited blobs",
        ),
    ]

    result = handle_critic_verdicts(case_dir, "aj", verdicts, pending_critiques)

    # findings.json has exactly 2 entries (AGREE + CHALLENGE remain)
    findings = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    assert len(findings) == 2
    ids_remaining = {f["finding_id"] for f in findings}
    assert ids_remaining == {"F-001", "F-002"}

    # AGREE finding has critic_status=AGREED
    f001 = next(f for f in findings if f["finding_id"] == "F-001")
    assert f001["critic_status"] == "AGREED"

    # CHALLENGE finding has critic_status=CHALLENGED
    f002 = next(f for f in findings if f["finding_id"] == "F-002")
    assert f002["critic_status"] == "CHALLENGED"
    assert f002["critic_challenge_reason"] == verdicts[1].reason

    # findings.archived.json has exactly 1 entry (REJECT)
    archived = json.loads((case_dir / "findings.archived.json").read_text(encoding="utf-8"))
    assert len(archived) == 1
    assert archived[0]["finding_id"] == "F-003"
    assert archived[0]["status"] == "ARCHIVED"
    assert archived[0]["critic_status"] == "REJECTED"

    # pending_critiques has exactly 1 entry (the CHALLENGE)
    assert len(pending_critiques) == 1
    assert pending_critiques[0].finding_id == "F-002"
    assert pending_critiques[0].verdict == "CHALLENGE"

    # audit/critic.jsonl has exactly 3 lines
    raw = (case_dir / "audit" / "critic.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(raw) == 3
    types = {json.loads(line)["type"] for line in raw}
    assert types == {"agree", "challenge", "reject"}

    # result counts are correct
    assert result.agree_count == 1
    assert result.challenge_count == 1
    assert result.reject_count == 1
    assert result.archived_finding_ids == ["F-003"]
    assert result.audit_lines_written == 3
