"""Integration tests for `silentwitness approve` — ≥12 BDD scenarios."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from silentwitness_agent.cli import app
from tests.integration._helpers_status import init_case

runner = CliRunner()

_CORRECT_PW = "examiner-secret-pw"
_WRONG_PW = "wrong-password"
_PBKDF2_ITER = 600_000


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_verifier(password: str) -> tuple[str, str]:
    """Return (verifier_salt_hex, verifier_hex) for a given password."""
    v_salt = hashlib.sha256(f"vsalt:{password}".encode()).digest()
    v_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), v_salt, _PBKDF2_ITER)
    return v_salt.hex(), v_hash.hex()


def _write_case_yaml(
    case_dir: Path,
    *,
    salt_hex: str | None = "deadbeef" * 8,
    with_verifier: bool = True,
    password: str = _CORRECT_PW,
) -> None:
    data: dict[str, Any] = {}
    if salt_hex is not None:
        data["salt_hex"] = salt_hex
    if with_verifier:
        v_salt_hex, v_hex = _make_verifier(password)
        data["verifier_salt_hex"] = v_salt_hex
        data["verifier_hex"] = v_hex
    (case_dir / "CASE.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")


def _write_draft_finding(case_dir: Path, finding_id: str = "F-001") -> None:
    data = [
        {
            "observation_id": "O-001",
            "text": "Ethereal was present on the filesystem",
            "audit_ids": ["sift-001-20260602-014"],
            "interpretations": [
                {
                    "interpretation_id": "I-001",
                    "text": "wardriving activity consistent with network sniffing",
                    "confidence": "HIGH",
                }
            ],
        },
        {
            "finding_id": finding_id,
            "observation_id": "O-001",
            "interpretation_id": "I-001",
            "status": "DRAFT",
            "staged_at": "2026-01-01T12:00:00+00:00",
            "caveats": "Tool installation alone does not prove use",
            "mitre": "T1040",
        },
    ]
    (case_dir / "findings.json").write_text(json.dumps(data), encoding="utf-8")


def _make_ledger_dir(tmp_path: Path) -> Path:
    ledger_dir = tmp_path / "verification"
    ledger_dir.mkdir(mode=0o700)
    return ledger_dir


# ---------------------------------------------------------------------------
# 1. Correct password → exit 0, finding APPROVED, ledger entry written
# ---------------------------------------------------------------------------


def test_approve_correct_password(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Correct password seals ledger entry and promotes finding to APPROVED."""
    case_dir = init_case(tmp_path, "mr-ap-001", monkeypatch)
    _write_case_yaml(case_dir)
    _write_draft_finding(case_dir)
    ledger_dir = _make_ledger_dir(tmp_path)
    monkeypatch.setenv("_SILENTWITNESS_TEST_PASSWORD", _CORRECT_PW)
    result = runner.invoke(
        app,
        ["approve", "mr-ap-001", "F-001", "--ledger", str(ledger_dir)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "F-001 APPROVED" in result.output
    assert "PBKDF2-SHA256" in result.output
    findings = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    f = next(x for x in findings if isinstance(x, dict) and x.get("finding_id") == "F-001")
    assert f["status"] == "APPROVED"
    ledger_file = ledger_dir / "mr-ap-001.jsonl"
    assert ledger_file.is_file()
    entry = json.loads(ledger_file.read_text(encoding="utf-8").strip())
    assert entry["item_id"] == "F-001"
    assert entry["item_type"] == "finding"
    assert "hmac" in entry


# ---------------------------------------------------------------------------
# 2. Wrong password once then correct → exit 0, "2 attempts remain" shown
# ---------------------------------------------------------------------------


def test_approve_wrong_once_then_correct(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """One wrong attempt prints '2 attempts remain'; second correct attempt approves."""
    case_dir = init_case(tmp_path, "mr-ap-w1-001", monkeypatch)
    _write_case_yaml(case_dir)
    _write_draft_finding(case_dir)
    ledger_dir = _make_ledger_dir(tmp_path)
    calls: list[str] = [_WRONG_PW, _CORRECT_PW]
    monkeypatch.setattr(
        "silentwitness_agent.cli_commands.approve._read_password",
        lambda prompt="examiner password: ": calls.pop(0),
    )
    result = runner.invoke(
        app,
        ["approve", "mr-ap-w1-001", "F-001", "--ledger", str(ledger_dir)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "2 attempts remain" in result.stderr
    findings = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    f = next(x for x in findings if isinstance(x, dict) and x.get("finding_id") == "F-001")
    assert f["status"] == "APPROVED"
    ledger_file = ledger_dir / "mr-ap-w1-001.jsonl"
    assert ledger_file.is_file()
    # Only ONE ledger entry despite two password attempts.
    lines = [ln for ln in ledger_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1


# ---------------------------------------------------------------------------
# 3. Wrong password three times → exit 4, no ledger entry, finding unchanged
# ---------------------------------------------------------------------------


def test_approve_wrong_three_times(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Three wrong passwords exits 4 with no ledger entry and finding still DRAFT."""
    case_dir = init_case(tmp_path, "mr-ap-w3-001", monkeypatch)
    _write_case_yaml(case_dir)
    _write_draft_finding(case_dir)
    ledger_dir = _make_ledger_dir(tmp_path)
    monkeypatch.setattr(
        "silentwitness_agent.cli_commands.approve._read_password",
        lambda prompt="examiner password: ": _WRONG_PW,
    )
    result = runner.invoke(
        app,
        ["approve", "mr-ap-w3-001", "F-001", "--ledger", str(ledger_dir)],
        catch_exceptions=False,
    )
    assert result.exit_code == 4
    assert "0 attempts remain" in result.stderr or "approval denied" in result.stderr
    ledger_file = ledger_dir / "mr-ap-w3-001.jsonl"
    assert not ledger_file.exists()
    findings = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    f = next(x for x in findings if isinstance(x, dict) and x.get("finding_id") == "F-001")
    assert f["status"] == "DRAFT"


# ---------------------------------------------------------------------------
# 4. SIGINT during password prompt → exit 130, no ledger entry
# ---------------------------------------------------------------------------


def test_approve_sigint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """KeyboardInterrupt during password read exits 130 with no ledger entry."""
    case_dir = init_case(tmp_path, "mr-ap-sig-001", monkeypatch)
    _write_case_yaml(case_dir)
    _write_draft_finding(case_dir)
    ledger_dir = _make_ledger_dir(tmp_path)

    def _raise_interrupt(prompt: str = "examiner password: ") -> str:
        raise KeyboardInterrupt()

    monkeypatch.setattr("silentwitness_agent.cli_commands.approve._read_password", _raise_interrupt)
    result = runner.invoke(
        app,
        ["approve", "mr-ap-sig-001", "F-001", "--ledger", str(ledger_dir)],
        catch_exceptions=False,
    )
    assert result.exit_code == 130
    assert not (ledger_dir / "mr-ap-sig-001.jsonl").exists()
    findings = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    f = next(x for x in findings if isinstance(x, dict) and x.get("finding_id") == "F-001")
    assert f["status"] == "DRAFT"


# ---------------------------------------------------------------------------
# 5. Finding not found → exit 1, no password prompt shown
# ---------------------------------------------------------------------------


def test_approve_finding_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-existent finding_id exits 1 with error on stderr (no password prompt)."""
    case_dir = init_case(tmp_path, "mr-ap-nf-001", monkeypatch)
    _write_case_yaml(case_dir)
    _write_draft_finding(case_dir)
    ledger_dir = _make_ledger_dir(tmp_path)
    result = runner.invoke(
        app,
        ["approve", "mr-ap-nf-001", "F-not-exist", "--ledger", str(ledger_dir)],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    assert "F-not-exist" in result.stderr
    assert "not found" in result.stderr


# ---------------------------------------------------------------------------
# 6. Case not found → exit 1
# ---------------------------------------------------------------------------


def test_approve_case_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-existent case exits 1 before any filesystem access."""
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    result = runner.invoke(
        app,
        ["approve", "mr-ap-no-case", "F-001"],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    assert "mr-ap-no-case" in result.stderr


# ---------------------------------------------------------------------------
# 7. CASE.yaml missing salt → exit 2, CASE_SALT_MISSING
# ---------------------------------------------------------------------------


def test_approve_case_salt_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CASE.yaml present but no salt_hex → exit 2 with CASE_SALT_MISSING."""
    case_dir = init_case(tmp_path, "mr-ap-salt-001", monkeypatch)
    _write_case_yaml(case_dir, salt_hex=None)
    _write_draft_finding(case_dir)
    ledger_dir = _make_ledger_dir(tmp_path)
    result = runner.invoke(
        app,
        ["approve", "mr-ap-salt-001", "F-001", "--ledger", str(ledger_dir)],
        catch_exceptions=False,
    )
    assert result.exit_code == 2
    assert "CASE_SALT_MISSING" in result.stderr


# ---------------------------------------------------------------------------
# 8. Ledger dir mode 0755 → exit 2, LEDGER_DIR_PERMISSIONS_WEAK
# ---------------------------------------------------------------------------


def test_approve_ledger_dir_weak(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ledger dir with mode 0755 exits 2 with LEDGER_DIR_PERMISSIONS_WEAK."""
    case_dir = init_case(tmp_path, "mr-ap-perm-001", monkeypatch)
    _write_case_yaml(case_dir)
    _write_draft_finding(case_dir)
    ledger_dir = tmp_path / "verification-weak"
    ledger_dir.mkdir(mode=0o755)
    result = runner.invoke(
        app,
        ["approve", "mr-ap-perm-001", "F-001", "--ledger", str(ledger_dir)],
        catch_exceptions=False,
    )
    assert result.exit_code == 2
    assert "LEDGER_DIR_PERMISSIONS_WEAK" in result.stderr


# ---------------------------------------------------------------------------
# 9. Already APPROVED → exit 1, ALREADY_APPROVED, no new ledger entry
# ---------------------------------------------------------------------------


def test_approve_already_approved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-approving an APPROVED finding exits 1 with ALREADY_APPROVED."""
    case_dir = init_case(tmp_path, "mr-ap-aa-001", monkeypatch)
    _write_case_yaml(case_dir)
    data = [
        {
            "observation_id": "O-001",
            "text": "obs",
            "audit_ids": [],
            "interpretations": [
                {"interpretation_id": "I-001", "text": "interp", "confidence": "LOW"}
            ],
        },
        {
            "finding_id": "F-001",
            "observation_id": "O-001",
            "interpretation_id": "I-001",
            "status": "APPROVED",
            "staged_at": "2026-01-01T12:00:00+00:00",
        },
    ]
    (case_dir / "findings.json").write_text(json.dumps(data), encoding="utf-8")
    ledger_dir = _make_ledger_dir(tmp_path)
    result = runner.invoke(
        app,
        ["approve", "mr-ap-aa-001", "F-001", "--ledger", str(ledger_dir)],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    assert "ALREADY_APPROVED" in result.stderr
    assert not (ledger_dir / "mr-ap-aa-001.jsonl").exists()


# ---------------------------------------------------------------------------
# 14. CASE.yaml with invalid YAML → exit 2, CASE_SALT_MALFORMED
# ---------------------------------------------------------------------------


def test_approve_case_salt_malformed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed CASE.yaml exits 2 with CASE_SALT_MALFORMED before any password prompt."""
    case_dir = init_case(tmp_path, "mr-ap-csm-001", monkeypatch)
    (case_dir / "CASE.yaml").write_text(": !!invalid yaml [", encoding="utf-8")
    _write_draft_finding(case_dir)
    ledger_dir = _make_ledger_dir(tmp_path)
    result = runner.invoke(
        app,
        ["approve", "mr-ap-csm-001", "F-001", "--ledger", str(ledger_dir)],
        catch_exceptions=False,
    )
    assert result.exit_code == 2
    assert "CASE_SALT_MALFORMED" in result.stderr
    assert not (ledger_dir / "mr-ap-csm-001.jsonl").exists()


# ---------------------------------------------------------------------------
# 15. No TTY available → exit 2, error message mentions TTY
# ---------------------------------------------------------------------------


def test_approve_no_tty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No TTY exits 2 with a message directing the examiner to use /dev/tty."""
    from silentwitness_agent.cli_commands.approve import _NoTTYError

    case_dir = init_case(tmp_path, "mr-ap-tty-001", monkeypatch)
    _write_case_yaml(case_dir)
    _write_draft_finding(case_dir)
    ledger_dir = _make_ledger_dir(tmp_path)

    def _raise_no_tty(prompt: str = "examiner password: ") -> str:
        raise _NoTTYError()

    monkeypatch.setattr("silentwitness_agent.cli_commands.approve._read_password", _raise_no_tty)
    result = runner.invoke(
        app,
        ["approve", "mr-ap-tty-001", "F-001", "--ledger", str(ledger_dir)],
        catch_exceptions=False,
    )
    assert result.exit_code == 2
    assert "TTY" in result.stderr
    assert not (ledger_dir / "mr-ap-tty-001.jsonl").exists()


# ---------------------------------------------------------------------------
# 16. findings.json contains invalid JSON → exit 2, parse error on stderr
# ---------------------------------------------------------------------------


def test_approve_findings_json_corrupted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """findings.json with invalid JSON exits 2 before the password prompt."""
    case_dir = init_case(tmp_path, "mr-ap-fjc-001", monkeypatch)
    _write_case_yaml(case_dir)
    (case_dir / "findings.json").write_text("{not valid json", encoding="utf-8")
    ledger_dir = _make_ledger_dir(tmp_path)
    result = runner.invoke(
        app,
        ["approve", "mr-ap-fjc-001", "F-001", "--ledger", str(ledger_dir)],
        catch_exceptions=False,
    )
    assert result.exit_code == 2
    assert "parse error" in result.stderr
    assert not (ledger_dir / "mr-ap-fjc-001.jsonl").exists()
