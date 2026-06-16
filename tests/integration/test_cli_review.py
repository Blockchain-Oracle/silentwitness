"""Integration tests for `silentwitness review` — ≥10 BDD scenarios."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from silentwitness_agent.cli import app
from tests.integration._helpers_status import init_case

runner = CliRunner()


# ---------------------------------------------------------------------------
# Test fixture helpers
# ---------------------------------------------------------------------------


def _make_findings(n: int = 1, status: str = "DRAFT") -> list[dict[str, Any]]:
    """Return a findings.json list with n observation + finding record pairs."""
    result: list[dict[str, Any]] = []
    for i in range(1, n + 1):
        oid = f"O-{i:03d}"
        iid = f"I-{i:03d}"
        fid = f"F-{i:03d}"
        result.append(
            {
                "observation_id": oid,
                "text": f"Observation text {i}: something suspicious was observed",
                "audit_ids": [f"sift-001-20260602-0{i:02d}"],
                "interpretations": [
                    {
                        "interpretation_id": iid,
                        "text": f"Interpretation text {i}: consistent with malicious activity",
                        "confidence": "HIGH",
                    }
                ],
            }
        )
        result.append(
            {
                "finding_id": fid,
                "observation_id": oid,
                "interpretation_id": iid,
                "status": status,
                "staged_at": f"2026-01-01T12:00:{i:02d}+00:00",
            }
        )
    return result


def _write_findings(case_dir: Path, data: list[dict[str, Any]]) -> None:
    (case_dir / "findings.json").write_text(json.dumps(data), encoding="utf-8")


def _with_finding(
    case_dir: Path,
    finding_id: str = "F-mr-evil-001-001",
    obs_text: str = "Ethereal was present",
    interp_text: str = "wardriving activity",
    caveats: str = "Tool installation alone does not prove use",
    mitre: str = "T1040 (Network Sniffing)",
    status: str = "DRAFT",
) -> None:
    data = [
        {
            "observation_id": "O-001",
            "text": obs_text,
            "audit_ids": ["sift-001-20260602-014", "sift-001-20260602-019"],
            "interpretations": [
                {
                    "interpretation_id": "I-001",
                    "text": interp_text,
                    "confidence": "MEDIUM",
                }
            ],
        },
        {
            "finding_id": finding_id,
            "observation_id": "O-001",
            "interpretation_id": "I-001",
            "status": status,
            "staged_at": "2026-01-01T12:18:02+00:00",
            "caveats": caveats,
            "mitre": mitre,
        },
    ]
    _write_findings(case_dir, data)


# ---------------------------------------------------------------------------
# 1. List mode shows DRAFT findings only
# ---------------------------------------------------------------------------


def test_review_list_draft_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given findings.json with 3 DRAFT + 1 APPROVED, list mode shows 3 DRAFT rows."""
    case_dir = init_case(tmp_path, "mr-list-001", monkeypatch)
    data = [
        *_make_findings(3, "DRAFT"),
        {"finding_id": "F-999", "observation_id": "O-999", "status": "APPROVED"},
    ]
    _write_findings(case_dir, data)
    result = runner.invoke(app, ["review", "mr-list-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "F-001" in result.output
    assert "F-002" in result.output
    assert "F-003" in result.output
    assert "F-999" not in result.output
    # Verify staged_at ascending sort by checking positional order in output.
    pos1, pos2, pos3 = (result.output.index(f) for f in ("F-001", "F-002", "F-003"))
    assert pos1 < pos2 < pos3


# ---------------------------------------------------------------------------
# 2. --status APPROVED filter
# ---------------------------------------------------------------------------


def test_review_list_status_approved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given 5 DRAFT + 2 APPROVED, --status APPROVED shows exactly 2 rows."""
    case_dir = init_case(tmp_path, "mr-approved-filter-001", monkeypatch)
    data = _make_findings(5, "DRAFT")
    # Add 2 APPROVED findings
    data += [
        {
            "finding_id": "F-A01",
            "observation_id": "O-001",
            "interpretation_id": "I-001",
            "status": "APPROVED",
            "staged_at": "2026-01-01T13:00:00+00:00",
        },
        {
            "finding_id": "F-A02",
            "observation_id": "O-001",
            "interpretation_id": "I-001",
            "status": "APPROVED",
            "staged_at": "2026-01-01T13:01:00+00:00",
        },
    ]
    _write_findings(case_dir, data)
    result = runner.invoke(
        app,
        ["review", "mr-approved-filter-001", "--status", "APPROVED"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "F-A01" in result.output
    assert "F-A02" in result.output
    assert "F-001" not in result.output


# ---------------------------------------------------------------------------
# 3. --finding-id renders ux-spec block shape
# ---------------------------------------------------------------------------


def test_review_detail_full_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given --finding-id, output matches the documented review block shape."""
    case_dir = init_case(tmp_path, "mr-detail-001", monkeypatch)
    _with_finding(case_dir)
    result = runner.invoke(
        app,
        ["review", "mr-detail-001", "--finding-id", "F-mr-evil-001-001", "--non-interactive"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "F-mr-evil-001-001" in result.output
    assert "staged 12:18:02Z" in result.output
    assert "observation:" in result.output
    assert "Ethereal was present" in result.output
    assert "interpretation:" in result.output
    assert "wardriving activity" in result.output
    assert "cited:" in result.output
    assert "sift-001-20260602-014" in result.output
    assert "caveats:" in result.output
    assert "mitre:" in result.output
    assert "T1040" in result.output


# ---------------------------------------------------------------------------
# 4. Keystroke 'q' exits 0 with no state change
# ---------------------------------------------------------------------------


def test_review_keystroke_q(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pressing 'q' exits 0 and leaves findings.json unchanged."""
    case_dir = init_case(tmp_path, "mr-q-001", monkeypatch)
    _with_finding(case_dir)
    before = (case_dir / "findings.json").read_text(encoding="utf-8")
    result = runner.invoke(
        app,
        ["review", "mr-q-001", "--finding-id", "F-mr-evil-001-001"],
        input="q\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (case_dir / "findings.json").read_text(encoding="utf-8") == before
    assert "to approve:" not in result.output


# ---------------------------------------------------------------------------
# 5. Keystroke 'a' prints approve hint, exits 0, no state change
# ---------------------------------------------------------------------------


def test_review_keystroke_a(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pressing 'a' prints the approve hint and exits 0 without mutating findings.json."""
    case_dir = init_case(tmp_path, "mr-a-001", monkeypatch)
    _with_finding(case_dir)
    before = (case_dir / "findings.json").read_text(encoding="utf-8")
    result = runner.invoke(
        app,
        ["review", "mr-a-001", "--finding-id", "F-mr-evil-001-001"],
        input="a\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (case_dir / "findings.json").read_text(encoding="utf-8") == before
    assert "to approve: silentwitness approve mr-a-001 F-mr-evil-001-001" in result.output


# ---------------------------------------------------------------------------
# 6. Keystroke 's' exits 0
# ---------------------------------------------------------------------------


def test_review_keystroke_s(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pressing 's' (skip) exits 0."""
    case_dir = init_case(tmp_path, "mr-s-001", monkeypatch)
    _with_finding(case_dir)
    result = runner.invoke(
        app,
        ["review", "mr-s-001", "--finding-id", "F-mr-evil-001-001"],
        input="s\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# 7. Keystroke 'r' updates findings.json with REJECTED
# ---------------------------------------------------------------------------


def test_review_keystroke_r(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pressing 'r' then entering a reason sets status=REJECTED in findings.json."""
    case_dir = init_case(tmp_path, "mr-r-001", monkeypatch)
    _with_finding(case_dir, finding_id="F-001")
    result = runner.invoke(
        app,
        ["review", "mr-r-001", "--finding-id", "F-001"],
        input="r\ninsufficient evidence\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    updated = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    finding = next(
        (item for item in updated if isinstance(item, dict) and item.get("finding_id") == "F-001"),
        None,
    )
    assert finding is not None
    assert finding["status"] == "REJECTED"
    assert finding["rejection_reason"] == "insufficient evidence"
    cli_log = case_dir / "audit" / "cli.jsonl"
    assert cli_log.is_file()
    lines = [ln for ln in cli_log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    entry = json.loads(lines[-1])
    assert entry["tool"] == "cli.review.reject"
    assert entry["finding_id"] == "F-001"
    assert entry["reason"] == "insufficient evidence"


# ---------------------------------------------------------------------------
# 8. Keystroke 'm' invokes $EDITOR and increments modification_count
# ---------------------------------------------------------------------------


def test_review_keystroke_m(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pressing 'm' with EDITOR=true increments modification_count in findings.json."""
    case_dir = init_case(tmp_path, "mr-m-001", monkeypatch)
    _with_finding(case_dir, finding_id="F-001")
    monkeypatch.setenv("EDITOR", "true")
    result = runner.invoke(
        app,
        ["review", "mr-m-001", "--finding-id", "F-001"],
        input="m\nq\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    updated = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    finding = next(
        (item for item in updated if isinstance(item, dict) and item.get("finding_id") == "F-001"),
        None,
    )
    assert finding is not None
    assert finding.get("modification_count", 0) == 1


# ---------------------------------------------------------------------------
# 9. --finding-id not found exits 1
# ---------------------------------------------------------------------------


def test_review_finding_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given --finding-id for a nonexistent finding, exits 1 with error on stderr."""
    case_dir = init_case(tmp_path, "mr-notfound-001", monkeypatch)
    _with_finding(case_dir)
    result = runner.invoke(
        app,
        ["review", "mr-notfound-001", "--finding-id", "F-not-found"],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    assert "F-not-found" in result.stderr
    assert "not found" in result.stderr


# ---------------------------------------------------------------------------
# 10. --non-interactive skips the prompt
# ---------------------------------------------------------------------------


def test_review_non_interactive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--non-interactive prints the block without reading stdin."""
    case_dir = init_case(tmp_path, "mr-nonint-001", monkeypatch)
    _with_finding(case_dir, finding_id="F-001")
    result = runner.invoke(
        app,
        ["review", "mr-nonint-001", "--finding-id", "F-001", "--non-interactive"],
        input="",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "F-001" in result.output
    assert _PROMPT_FRAGMENT not in result.output


_PROMPT_FRAGMENT = "[a]pprove"


# ---------------------------------------------------------------------------
# 11. Corrupted findings.json exits 2
# ---------------------------------------------------------------------------


def test_review_corrupted_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given malformed findings.json, exits 2 with parse error on stderr."""
    case_dir = init_case(tmp_path, "mr-corrupt-002", monkeypatch)
    (case_dir / "findings.json").write_text("NOT VALID JSON", encoding="utf-8")
    result = runner.invoke(app, ["review", "mr-corrupt-002"], catch_exceptions=False)
    assert result.exit_code == 2
    assert "parse error" in result.stderr


# ---------------------------------------------------------------------------
# 12. List mode with no matching findings shows empty table
# ---------------------------------------------------------------------------


def test_review_list_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given no DRAFT findings, list mode exits 0 with an empty table."""
    case_dir = init_case(tmp_path, "mr-empty-001", monkeypatch)
    _write_findings(case_dir, _make_findings(2, "APPROVED"))
    result = runner.invoke(app, ["review", "mr-empty-001"], catch_exceptions=False)
    assert result.exit_code == 0
    # DRAFT filter → no rows; table header still appears
    assert "ID" in result.output


# ---------------------------------------------------------------------------
# 13. Interactive prompt appears in default (interactive) mode
# ---------------------------------------------------------------------------


def test_review_interactive_prompt_shown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """In interactive mode (no --non-interactive), the action prompt is shown."""
    case_dir = init_case(tmp_path, "mr-prompt-001", monkeypatch)
    _with_finding(case_dir, finding_id="F-001")
    result = runner.invoke(
        app,
        ["review", "mr-prompt-001", "--finding-id", "F-001"],
        input="q\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "[a]pprove" in result.output
    assert "[r]eject" in result.output
    assert "[m]odify" in result.output
