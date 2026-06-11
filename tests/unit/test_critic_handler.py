"""Unit tests for critic_handler — ≥12 behavioural BDD scenarios.

Each test uses tmp_path for an isolated case directory and a pre-written
findings.json. No real I/O beyond the local tmp_path.
"""

from __future__ import annotations

import json
from pathlib import Path

from silentwitness_agent.critic import CriticVerdictRecord
from silentwitness_agent.critic_handler import (
    CriticHandlerResult,
    handle_critic_verdicts,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _f(n: int) -> dict[str, str]:
    return {
        "id": f"F-{n:03d}",
        "status": "DRAFT",
        "observation_id": f"O-{n:03d}",
        "interpretation_id": f"I-{n:03d}",
    }


def _write_findings(case_dir: Path, findings: list[dict[str, str]]) -> None:  # type: ignore[type-arg]
    (case_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")


def _make_case(tmp_path: Path) -> Path:
    (tmp_path / "audit").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _verdict(
    finding_id: str,
    verdict: str,
    *,
    reason: str = "test reason",
    suggested_revision: str | None = None,
    missing_corroboration: list[str] | None = None,
) -> CriticVerdictRecord:
    return CriticVerdictRecord(
        finding_id=finding_id,
        verdict=verdict,  # type: ignore[arg-type]
        reason=reason,
        suggested_revision=suggested_revision,
        missing_corroboration=missing_corroboration or [],
    )


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


# ---------------------------------------------------------------------------
# AGREE tests
# ---------------------------------------------------------------------------


def test_agree_appends_one_jsonl_line_with_type_agree(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    _write_findings(case, [_f(1)])
    handle_critic_verdicts(case, "aj", [_verdict("F-001", "AGREE")], [])
    lines = _read_jsonl(case / "audit" / "critic.jsonl")
    assert len(lines) == 1
    assert lines[0]["type"] == "agree"
    assert lines[0]["finding_id"] == "F-001"


def test_agree_marks_critic_status_agreed_in_findings_json(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    _write_findings(case, [_f(1)])
    handle_critic_verdicts(case, "aj", [_verdict("F-001", "AGREE")], [])
    findings = json.loads((case / "findings.json").read_text(encoding="utf-8"))
    assert findings[0]["critic_status"] == "AGREED"


def test_agree_does_not_touch_pending_critiques(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    _write_findings(case, [_f(1)])
    pending: list[CriticVerdictRecord] = []
    handle_critic_verdicts(case, "aj", [_verdict("F-001", "AGREE")], pending)
    assert pending == []


# ---------------------------------------------------------------------------
# CHALLENGE tests
# ---------------------------------------------------------------------------


def test_challenge_appends_jsonl_line_with_type_challenge_and_suggested_revision(
    tmp_path: Path,
) -> None:
    case = _make_case(tmp_path)
    _write_findings(case, [_f(2)])
    v = _verdict(
        "F-002",
        "CHALLENGE",
        reason="overstates evidence",
        suggested_revision="downgrade to MEDIUM",
        missing_corroboration=["pcap"],
    )
    handle_critic_verdicts(case, "aj", [v], [])
    lines = _read_jsonl(case / "audit" / "critic.jsonl")
    assert len(lines) == 1
    assert lines[0]["type"] == "challenge"
    assert lines[0]["suggested_revision"] == "downgrade to MEDIUM"


def test_challenge_appends_verdict_to_pending_critiques(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    _write_findings(case, [_f(2)])
    pending: list[CriticVerdictRecord] = []
    v = _verdict("F-002", "CHALLENGE")
    handle_critic_verdicts(case, "aj", [v], pending)
    assert len(pending) == 1
    assert pending[0].finding_id == "F-002"


def test_challenge_marks_critic_status_challenged_in_findings_json(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    _write_findings(case, [_f(2)])
    handle_critic_verdicts(case, "aj", [_verdict("F-002", "CHALLENGE", reason="weak evidence")], [])
    findings = json.loads((case / "findings.json").read_text(encoding="utf-8"))
    assert findings[0]["critic_status"] == "CHALLENGED"
    assert findings[0]["critic_challenge_reason"] == "weak evidence"


# ---------------------------------------------------------------------------
# REJECT tests
# ---------------------------------------------------------------------------


def test_reject_appends_jsonl_line_with_type_reject_and_reason(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    _write_findings(case, [_f(3)])
    handle_critic_verdicts(
        case, "aj", [_verdict("F-003", "REJECT", reason="hallucinated entity")], []
    )
    lines = _read_jsonl(case / "audit" / "critic.jsonl")
    assert len(lines) == 1
    assert lines[0]["type"] == "reject"
    assert lines[0]["reason"] == "hallucinated entity"


def test_reject_removes_finding_from_findings_json(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    _write_findings(case, [_f(3)])
    handle_critic_verdicts(case, "aj", [_verdict("F-003", "REJECT")], [])
    findings = json.loads((case / "findings.json").read_text(encoding="utf-8"))
    assert not any(f.get("id") == "F-003" for f in findings)


def test_reject_appends_finding_to_archived_with_provenance(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    _write_findings(case, [_f(3)])
    handle_critic_verdicts(case, "aj", [_verdict("F-003", "REJECT", reason="hallucinated")], [])
    archived = json.loads((case / "findings.archived.json").read_text(encoding="utf-8"))
    assert len(archived) == 1
    rec = archived[0]
    assert rec["id"] == "F-003"
    assert rec["status"] == "ARCHIVED"
    assert rec["critic_status"] == "REJECTED"
    assert rec["archival_reason"] == "hallucinated"
    assert rec["observation_id"] == "O-003"
    assert rec["interpretation_id"] == "I-003"
    assert "archived_at" in rec


def test_reject_never_silently_deletes_archived_file_is_post_condition(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    _write_findings(case, [_f(3)])
    handle_critic_verdicts(case, "aj", [_verdict("F-003", "REJECT")], [])
    assert (case / "findings.archived.json").exists()
    archived = json.loads((case / "findings.archived.json").read_text(encoding="utf-8"))
    assert any(f.get("id") == "F-003" for f in archived)


# ---------------------------------------------------------------------------
# Mixed batch + counts
# ---------------------------------------------------------------------------


def test_mixed_batch_returns_correct_counts(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    _write_findings(case, [_f(1), _f(2), _f(3)])
    pending: list[CriticVerdictRecord] = []
    result = handle_critic_verdicts(
        case,
        "aj",
        [_verdict("F-001", "AGREE"), _verdict("F-002", "CHALLENGE"), _verdict("F-003", "REJECT")],
        pending,
    )
    assert result == CriticHandlerResult(
        agree_count=1,
        challenge_count=1,
        reject_count=1,
        archived_finding_ids=["F-003"],
        audit_lines_written=3,
    )


def test_audit_jsonl_lines_all_parseable_with_required_fields(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    _write_findings(case, [_f(1), _f(2), _f(3)])
    handle_critic_verdicts(
        case,
        "aj",
        [
            _verdict("F-001", "AGREE"),
            _verdict("F-002", "CHALLENGE", suggested_revision="downgrade"),
            _verdict("F-003", "REJECT"),
        ],
        [],
    )
    lines = _read_jsonl(case / "audit" / "critic.jsonl")
    assert len(lines) == 3
    for line in lines:
        assert "type" in line
        assert "finding_id" in line
        assert "ts" in line


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_unknown_finding_id_emits_skip_line(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    _write_findings(case, [])
    result = handle_critic_verdicts(case, "aj", [_verdict("F-MISSING", "AGREE")], [])
    assert result.agree_count == 0
    assert result.audit_lines_written == 1
    lines = _read_jsonl(case / "audit" / "critic.jsonl")
    assert lines[0]["type"] == "skip"


def test_agree_verdict_reason_preserved_in_audit_line(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    _write_findings(case, [_f(1)])
    handle_critic_verdicts(
        case, "aj", [_verdict("F-001", "AGREE", reason="evidence supports interpretation")], []
    )
    lines = _read_jsonl(case / "audit" / "critic.jsonl")
    assert lines[0]["reason"] == "evidence supports interpretation"


def test_reject_preserves_existing_archived_entries(tmp_path: Path) -> None:
    """REJECT appends to findings.archived.json; does not overwrite prior entries."""
    case = _make_case(tmp_path)
    prior = [{"id": "OLD-001", "status": "ARCHIVED", "critic_status": "REJECTED"}]
    (case / "findings.archived.json").write_text(json.dumps(prior), encoding="utf-8")
    _write_findings(case, [_f(3)])
    handle_critic_verdicts(case, "aj", [_verdict("F-003", "REJECT")], [])
    archived = json.loads((case / "findings.archived.json").read_text(encoding="utf-8"))
    assert len(archived) == 2
    ids = {r.get("id") for r in archived}
    assert ids == {"OLD-001", "F-003"}


# ---------------------------------------------------------------------------
# Additional coverage: encoding safety, examiner field, no-op, corrupt reads
# ---------------------------------------------------------------------------


def test_unicode_line_separator_in_reason_does_not_raise(tmp_path: Path) -> None:
    """U+2028 / U+2029 in LLM-supplied reason must not crash the handler."""
    case = _make_case(tmp_path)
    _write_findings(case, [_f(1)])
    reason_with_separators = "step" + chr(0x2028) + "evidence" + chr(0x2029) + "detail"
    handle_critic_verdicts(
        case, "aj", [_verdict("F-001", "AGREE", reason=reason_with_separators)], []
    )
    lines = _read_jsonl(case / "audit" / "critic.jsonl")
    assert len(lines) == 1
    assert lines[0]["type"] == "agree"


def test_examiner_field_present_in_all_audit_line_types(tmp_path: Path) -> None:
    case = _make_case(tmp_path)
    _write_findings(case, [_f(1), _f(2), _f(3)])
    handle_critic_verdicts(
        case,
        "analyst-x",
        [_verdict("F-001", "AGREE"), _verdict("F-002", "CHALLENGE"), _verdict("F-003", "REJECT")],
        [],
    )
    lines = _read_jsonl(case / "audit" / "critic.jsonl")
    for line in lines:
        assert line["examiner"] == "analyst-x"


def test_empty_verdicts_list_does_not_write_findings_json(tmp_path: Path) -> None:
    """Empty verdict batch must not overwrite findings.json (no-op write guard)."""
    case = _make_case(tmp_path)
    _write_findings(case, [_f(1)])
    original_mtime = (case / "findings.json").stat().st_mtime
    handle_critic_verdicts(case, "aj", [], [])
    assert (case / "findings.json").stat().st_mtime == original_mtime


def test_audit_dir_auto_created_when_missing(tmp_path: Path) -> None:
    """handle_critic_verdicts must create audit/ if it does not exist."""
    case = tmp_path  # no _make_case — audit/ not pre-created
    _write_findings(case, [_f(1)])
    handle_critic_verdicts(case, "aj", [_verdict("F-001", "AGREE")], [])
    assert (case / "audit" / "critic.jsonl").exists()


def test_corrupt_findings_archived_raises(tmp_path: Path) -> None:
    """Corrupt findings.archived.json must raise ValueError, not silently return []."""
    import pytest

    case = _make_case(tmp_path)
    _write_findings(case, [_f(3)])
    (case / "findings.archived.json").write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="corrupt"):
        handle_critic_verdicts(case, "aj", [_verdict("F-003", "REJECT")], [])


def test_multiple_rejects_in_one_batch(tmp_path: Path) -> None:
    """Multiple REJECTs in one call must all appear in findings.archived.json."""
    case = _make_case(tmp_path)
    _write_findings(case, [_f(1), _f(2), _f(3)])
    result = handle_critic_verdicts(
        case,
        "aj",
        [_verdict("F-001", "REJECT"), _verdict("F-002", "REJECT"), _verdict("F-003", "AGREE")],
        [],
    )
    assert result.reject_count == 2
    assert result.agree_count == 1
    archived = json.loads((case / "findings.archived.json").read_text(encoding="utf-8"))
    assert len(archived) == 2
    remaining = json.loads((case / "findings.json").read_text(encoding="utf-8"))
    assert len(remaining) == 1
    assert remaining[0]["id"] == "F-003"
