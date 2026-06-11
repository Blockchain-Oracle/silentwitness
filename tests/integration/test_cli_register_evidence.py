"""Integration tests for `silentwitness register-evidence` (≥9 BDD scenarios)."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest
from typer.testing import CliRunner

from silentwitness_agent.cli import app

runner = CliRunner()


def _init_case(tmp_path: Path, case_id: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    runner.invoke(app, ["init", case_id], catch_exceptions=False)
    return tmp_path / "cases" / case_id


# ---------------------------------------------------------------------------
# 1. Happy-path single file — exit 0, evidence.json gains one record
# ---------------------------------------------------------------------------


def test_register_single_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = _init_case(tmp_path, "c001", monkeypatch)
    evidence = tmp_path / "disk.E01"
    evidence.write_bytes(b"fake image data")
    result = runner.invoke(
        app, ["register-evidence", "c001", str(evidence)], catch_exceptions=False
    )
    assert result.exit_code == 0
    data = json.loads((case_dir / "evidence.json").read_text())
    assert len(data["records"]) == 1
    assert data["records"][0]["type"] == "disk_image"


# ---------------------------------------------------------------------------
# 2. Type auto-detection covers all expected extensions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("suffix", "expected_type"),
    [
        (".E01", "disk_image"),
        (".ewf", "disk_image"),
        (".dd", "disk_image"),
        (".img", "disk_image"),
        (".raw", "disk_image"),
        (".mem", "memory_dump"),
        (".vmem", "memory_dump"),
        (".dmp", "memory_dump"),
        (".evtx", "evtx"),
        (".pcap", "pcap"),
        (".pcapng", "pcap"),
        (".hve", "hive"),
        (".hiv", "hive"),
    ],
)
def test_type_detection_by_suffix(
    suffix: str, expected_type: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_case(tmp_path, "c002", monkeypatch)
    f = tmp_path / f"evidence{suffix}"
    f.write_bytes(b"data")
    result = runner.invoke(app, ["register-evidence", "c002", str(f)], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads((tmp_path / "cases" / "c002" / "evidence.json").read_text())
    assert data["records"][0]["type"] == expected_type


# ---------------------------------------------------------------------------
# 3. Known hive filenames (no suffix) detected as hive type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hive_name",
    ["SYSTEM", "SOFTWARE", "SAM", "SECURITY", "NTUSER.DAT", "DEFAULT", "USRCLASS.DAT"],
)
def test_hive_name_detection(
    hive_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_case(tmp_path, "c003", monkeypatch)
    hive = tmp_path / hive_name
    hive.write_bytes(b"regf" + b"\x00" * 12)
    result = runner.invoke(app, ["register-evidence", "c003", str(hive)], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads((tmp_path / "cases" / "c003" / "evidence.json").read_text())
    assert data["records"][0]["type"] == "hive"


# ---------------------------------------------------------------------------
# 4. Idempotent re-register — exit 0, still one record, warns "sha256 matches"
# ---------------------------------------------------------------------------


def test_idempotent_reregister(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_case(tmp_path, "c004", monkeypatch)
    f = tmp_path / "disk.dd"
    f.write_bytes(b"stable bytes")
    runner.invoke(app, ["register-evidence", "c004", str(f)], catch_exceptions=False)
    result = runner.invoke(app, ["register-evidence", "c004", str(f)], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads((tmp_path / "cases" / "c004" / "evidence.json").read_text())
    assert len(data["records"]) == 1
    assert "sha256 matches" in result.output


# ---------------------------------------------------------------------------
# 5. Content drift — exit 1, stderr contains sha256_mismatch_on_reregister
# ---------------------------------------------------------------------------


def test_content_drift_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_case(tmp_path, "c005", monkeypatch)
    f = tmp_path / "disk.dd"
    f.write_bytes(b"original bytes")
    runner.invoke(app, ["register-evidence", "c005", str(f)], catch_exceptions=False)
    f.write_bytes(b"tampered bytes!!")
    result = runner.invoke(app, ["register-evidence", "c005", str(f)], catch_exceptions=False)
    assert result.exit_code == 1
    assert "sha256_mismatch_on_reregister" in result.stderr


# ---------------------------------------------------------------------------
# 6. Non-existent path — exit 1, stderr contains "does not exist"
# ---------------------------------------------------------------------------


def test_nonexistent_path_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_case(tmp_path, "c006", monkeypatch)
    result = runner.invoke(
        app, ["register-evidence", "c006", str(tmp_path / "ghost.E01")], catch_exceptions=False
    )
    assert result.exit_code == 1
    assert "does not exist" in result.stderr


# ---------------------------------------------------------------------------
# 7. Case not found — exit 1, stderr contains "not found"
# ---------------------------------------------------------------------------


def test_case_not_found_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    f = tmp_path / "disk.E01"
    f.write_bytes(b"data")
    result = runner.invoke(
        app, ["register-evidence", "no-such-case", str(f)], catch_exceptions=False
    )
    assert result.exit_code == 1
    assert "not found" in result.stderr


# ---------------------------------------------------------------------------
# 8. --recursive registers all files in a directory
# ---------------------------------------------------------------------------


def test_recursive_registers_all_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = _init_case(tmp_path, "c008", monkeypatch)
    evidence_dir = tmp_path / "batch"
    evidence_dir.mkdir()
    (evidence_dir / "disk.E01").write_bytes(b"image")
    (evidence_dir / "ram.mem").write_bytes(b"memdump")
    (evidence_dir / "events.evtx").write_bytes(b"evtx")
    result = runner.invoke(
        app,
        ["register-evidence", "c008", str(evidence_dir), "--recursive"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    data = json.loads((case_dir / "evidence.json").read_text())
    assert len(data["records"]) == 3
    types = {r["type"] for r in data["records"]}
    assert types == {"disk_image", "memory_dump", "evtx"}


# ---------------------------------------------------------------------------
# 9. --dry-run does NOT modify evidence.json or audit log, prints DRY-RUN sha256
# ---------------------------------------------------------------------------


def test_dry_run_no_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = _init_case(tmp_path, "c009", monkeypatch)
    f = tmp_path / "disk.dd"
    f.write_bytes(b"dry bytes")
    before_evidence = (case_dir / "evidence.json").read_text()
    before_audit = (case_dir / "audit" / "cli.jsonl").read_text()
    result = runner.invoke(
        app, ["register-evidence", "c009", str(f), "--dry-run"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "DRY-RUN" in result.output
    assert "sha256:" in result.output
    assert (case_dir / "evidence.json").read_text() == before_evidence
    assert (case_dir / "audit" / "cli.jsonl").read_text() == before_audit


# ---------------------------------------------------------------------------
# 10. Audit entry written for successful registration
# ---------------------------------------------------------------------------


def test_audit_entry_written(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = _init_case(tmp_path, "c010", monkeypatch)
    f = tmp_path / "disk.raw"
    f.write_bytes(b"audit test")
    runner.invoke(app, ["register-evidence", "c010", str(f)], catch_exceptions=False)
    lines = (case_dir / "audit" / "cli.jsonl").read_text().splitlines()
    tools = [json.loads(ln)["tool"] for ln in lines]
    assert "cli.register-evidence" in tools


# ---------------------------------------------------------------------------
# 11. Unreadable file — exit 1, stderr contains permission wording
# ---------------------------------------------------------------------------


@pytest.mark.skipif(os.getuid() == 0, reason="root bypasses file permissions")
def test_unreadable_file_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_case(tmp_path, "c011", monkeypatch)
    f = tmp_path / "locked.E01"
    f.write_bytes(b"secret")
    f.chmod(stat.S_IWUSR)
    try:
        result = runner.invoke(app, ["register-evidence", "c011", str(f)], catch_exceptions=False)
        assert result.exit_code == 1
        assert "permission" in result.stderr.lower()
    finally:
        f.chmod(stat.S_IRUSR | stat.S_IWUSR)


# ---------------------------------------------------------------------------
# 12. stdout shows truncated sha256 and human-readable size on success
# ---------------------------------------------------------------------------


def test_stdout_shape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_case(tmp_path, "c012", monkeypatch)
    f = tmp_path / "capture.pcap"
    f.write_bytes(b"X" * 2048)
    result = runner.invoke(app, ["register-evidence", "c012", str(f)], catch_exceptions=False)
    assert result.exit_code == 0
    assert "✓" in result.output
    assert "sha256:" in result.output
    assert "..." in result.output
    assert "size:" in result.output


# ---------------------------------------------------------------------------
# 13. Empty directory — exit 1, stderr suggests --recursive
# ---------------------------------------------------------------------------


def test_empty_directory_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_case(tmp_path, "c013", monkeypatch)
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    result = runner.invoke(
        app, ["register-evidence", "c013", str(empty_dir)], catch_exceptions=False
    )
    assert result.exit_code == 1
    assert "no files found" in result.stderr


# ---------------------------------------------------------------------------
# 14. Examiner sourced from case.toml, not config — audit_ids share slug
# ---------------------------------------------------------------------------


def test_examiner_from_case_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    runner.invoke(app, ["init", "c014", "--examiner", "alice"], catch_exceptions=False)
    f = tmp_path / "disk.E01"
    f.write_bytes(b"data")
    runner.invoke(app, ["register-evidence", "c014", str(f)], catch_exceptions=False)
    case_dir = tmp_path / "cases" / "c014"
    lines = (case_dir / "audit" / "cli.jsonl").read_text().splitlines()
    audit_ids = [json.loads(ln)["audit_id"] for ln in lines]
    assert all("alice" in aid for aid in audit_ids)
