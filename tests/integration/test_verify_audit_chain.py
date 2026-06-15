"""End-to-end: ``silentwitness verify --audit-chain`` walks a real audit
directory + reports breaks (Phase 6b)."""

from __future__ import annotations

import json
from pathlib import Path

from silentwitness_agent.cli_commands.verify_audit_chain import run_audit_chain
from silentwitness_mcp.audit.logger import AuditLogger


def _emit(logger: AuditLogger, backend: str, n: int = 3) -> None:
    """Emit ``n`` audit rows under ``backend``."""
    for i in range(n):
        logger.emit(
            backend=backend,
            tool=f"tool_{i}",
            params={"i": i},
            result_summary={"ok": True},
            result_sha256="0" * 64,
            stdout_path=Path("/tmp/nowhere"),  # noqa: S108  # placeholder path for test
            elapsed_ms=1.0,
            model_used="cli",
        )


def test_fresh_chain_verifies_clean(tmp_path: Path) -> None:
    logger = AuditLogger(tmp_path, examiner="ex")
    _emit(logger, "cli", n=4)
    _emit(logger, "agent", n=2)
    logger.close()

    rc = run_audit_chain(tmp_path, no_color=True)
    assert rc == 0


def test_tampered_row_detected(tmp_path: Path) -> None:
    """Modify one row's `params` after the fact — verify must detect it."""
    logger = AuditLogger(tmp_path, examiner="ex")
    _emit(logger, "cli", n=3)
    logger.close()

    audit_file = tmp_path / "audit" / "cli.jsonl"
    lines = audit_file.read_text(encoding="utf-8").splitlines()
    # Tamper the middle row.
    mid = json.loads(lines[1])
    mid["params"] = {"i": 99}  # change without updating record_hash
    lines[1] = json.dumps(mid)
    audit_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    rc = run_audit_chain(tmp_path, no_color=True)
    assert rc == 1


def test_legacy_pre_chain_row_appended_detected(tmp_path: Path) -> None:
    """An attacker who appends a raw JSON line WITHOUT chain fields gets
    detected — the row is reported as `record_hash_missing`."""
    logger = AuditLogger(tmp_path, examiner="ex")
    _emit(logger, "cli", n=2)
    logger.close()

    audit_file = tmp_path / "audit" / "cli.jsonl"
    with audit_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"tool": "evil", "audit_id": "x"}) + "\n")

    rc = run_audit_chain(tmp_path, no_color=True)
    assert rc == 1


def test_empty_case_returns_clean(tmp_path: Path) -> None:
    (tmp_path / "audit").mkdir()
    rc = run_audit_chain(tmp_path, no_color=True)
    assert rc == 0


def test_missing_audit_dir_returns_setup_error(tmp_path: Path) -> None:
    rc = run_audit_chain(tmp_path, no_color=True)
    assert rc == 2


def test_restart_continues_chain_correctly(tmp_path: Path) -> None:
    """Logger restarted mid-case picks up the last record_hash from disk —
    appended rows continue the chain, no break."""
    logger1 = AuditLogger(tmp_path, examiner="ex")
    _emit(logger1, "cli", n=2)
    logger1.close()
    # New logger instance — must re-read the last hash from disk.
    logger2 = AuditLogger(tmp_path, examiner="ex")
    _emit(logger2, "cli", n=2)
    logger2.close()

    rc = run_audit_chain(tmp_path, no_color=True)
    assert rc == 0
