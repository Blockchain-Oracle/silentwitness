"""Integration tests for `silentwitness status` via Typer CliRunner (≥9 BDD scenarios)."""

from __future__ import annotations

import json
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from silentwitness_agent.cli import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_case(tmp_path: Path, case_id: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    result = runner.invoke(app, ["init", case_id], catch_exceptions=False)
    assert result.exit_code == 0
    return tmp_path / "cases" / case_id


def _write_agent_jsonl(case_dir: Path, events: list[dict[str, Any]]) -> None:
    lines = "\n".join(json.dumps(e) for e in events) + "\n"
    (case_dir / "audit" / "agent.jsonl").write_text(lines, encoding="utf-8")


def _write_hyp_jsonl(case_dir: Path, events: list[dict[str, Any]]) -> None:
    lines = "\n".join(json.dumps(e) for e in events) + "\n"
    (case_dir / "audit" / "hypothesis.jsonl").write_text(lines, encoding="utf-8")


def _write_findings_json(case_dir: Path, items: list[dict[str, Any]]) -> None:
    (case_dir / "findings.json").write_text(json.dumps(items), encoding="utf-8")


def _step_event(input_tokens: int = 1000, output_tokens: int = 500) -> dict[str, Any]:
    return {
        "ts": "2026-01-01T00:00:00+00:00",
        "type": "step",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def _finish_event(
    total_tokens: int = 312_000,
    stack_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ev: dict[str, Any] = {
        "ts": "2026-01-01T00:05:00+00:00",
        "type": "finish",
        "event": "on_finish",
        "total_tokens_consumed": total_tokens,
        "model_used": "claude-sonnet-4-6",
    }
    if stack_snapshot is not None:
        ev["stack_snapshot"] = stack_snapshot
    return ev


def _hyp_event(hid: str, hyp_type: str) -> dict[str, Any]:
    return {
        "ts": "2026-01-01T00:01:00+00:00",
        "type": hyp_type,
        "hypothesis_id": hid,
    }


def _make_stack_snapshot(
    active: dict[str, Any] | None = None,
    queued: list[dict[str, Any]] | None = None,
    history: list[dict[str, Any]] | None = None,
    total_pivot_count: int = 0,
) -> dict[str, Any]:
    return {
        "active": active,
        "queued": queued or [],
        "history": history or [],
        "total_pivot_count": total_pivot_count,
    }


# ---------------------------------------------------------------------------
# 1. Case with no hypotheses shows zero counts and "no hypotheses yet"
# ---------------------------------------------------------------------------


def test_status_no_hypotheses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given a just-initialized case, status shows no hypotheses and exits 0."""
    _init_case(tmp_path, "mr-idle-001", monkeypatch)
    result = runner.invoke(app, ["status", "mr-idle-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "no hypotheses yet" in result.output
    assert "(0 active, 0 confirmed, 0 pivoted, 0 abandoned)" in result.output


# ---------------------------------------------------------------------------
# 2. Full hypothesis counts match UX-spec sample shape
# ---------------------------------------------------------------------------


def test_status_hypothesis_counts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given 3 active + 2 confirmed + 1 pivoted + 0 abandoned, counts are shown correctly."""
    case_dir = _init_case(tmp_path, "mr-evil-001", monkeypatch)

    snap = _make_stack_snapshot(
        active={"id": "H-001", "statement": "Malware injected via spearphishing"},
        queued=[
            {"id": "H-002", "statement": "Lateral movement via PsExec"},
            {"id": "H-003", "statement": "Data exfil over DNS"},
        ],
        history=[
            {"id": "H-004", "status": "CONFIRMED", "statement": "Persistence via Run key"},
            {"id": "H-005", "status": "CONFIRMED", "statement": "Credential dumping via LSASS"},
            {"id": "H-006", "status": "PIVOTED", "statement": "Ransomware deployment"},
        ],
    )
    _write_agent_jsonl(case_dir, [_finish_event(total_tokens=312_000, stack_snapshot=snap)])
    _write_findings_json(
        case_dir,
        [{"status": "DRAFT"} for _ in range(9)],
    )
    # Add a rejected finding via findings.jsonl
    (case_dir / "audit" / "findings.jsonl").write_text(
        json.dumps({"result_summary": {"success": False}}) + "\n", encoding="utf-8"
    )

    result = runner.invoke(app, ["status", "mr-evil-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "(3 active, 2 confirmed, 1 pivoted, 0 abandoned)" in result.output
    assert "findings: staged 9  approved 0  rejected 1" in result.output
    assert "312k / 800k budget" in result.output


# ---------------------------------------------------------------------------
# 3. --json emits valid JSON with expected keys, no ANSI escapes
# ---------------------------------------------------------------------------


def test_status_json_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given --json, stdout is clean JSON with all required top-level keys."""
    case_dir = _init_case(tmp_path, "mr-json-001", monkeypatch)
    snap = _make_stack_snapshot(
        active={"id": "H-001", "statement": "Active hypothesis"},
        history=[{"id": "H-002", "status": "CONFIRMED", "statement": "Confirmed finding"}],
    )
    _write_agent_jsonl(case_dir, [_finish_event(total_tokens=50_000, stack_snapshot=snap)])

    result = runner.invoke(app, ["status", "mr-json-001", "--json"], catch_exceptions=False)
    assert result.exit_code == 0

    # Must be valid JSON
    data = json.loads(result.output)

    # Required top-level keys
    assert "case_id" in data
    assert "hypotheses" in data
    assert "findings" in data
    assert "budget" in data
    assert "last_event" in data

    # case_id matches
    assert data["case_id"] == "mr-json-001"

    # Hypothesis counts
    assert data["hypotheses"]["counts"]["ACTIVE"] == 1
    assert data["hypotheses"]["counts"]["CONFIRMED"] == 1

    # No ANSI escape sequences
    assert "\x1b[" not in result.output


# ---------------------------------------------------------------------------
# 4. Case not found exits 1 with correct stderr message
# ---------------------------------------------------------------------------


def test_status_case_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given a nonexistent case ID, status exits 1 with 'not found' in stderr."""
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    result = runner.invoke(app, ["status", "mr-evil-999"], catch_exceptions=False)
    assert result.exit_code == 1
    assert "mr-evil-999" in result.output
    assert "not found" in result.output


# ---------------------------------------------------------------------------
# 5. Corrupted hypothesis.jsonl exits 2 with parse error wording
# ---------------------------------------------------------------------------


def test_status_corrupted_hypothesis_jsonl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given hypothesis.jsonl has a non-JSON line, status exits 2 with parse error."""
    case_dir = _init_case(tmp_path, "mr-corrupt-001", monkeypatch)
    _write_agent_jsonl(case_dir, [_step_event()])
    (case_dir / "audit" / "hypothesis.jsonl").write_text(
        '{"type": "form", "hypothesis_id": "H-001"}\nNOT VALID JSON\n',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["status", "mr-corrupt-001"], catch_exceptions=False)
    assert result.exit_code == 2
    assert "hypothesis.jsonl parse error at line" in result.output


# ---------------------------------------------------------------------------
# 6. Tokens computed correctly from finish event total_tokens_consumed
# ---------------------------------------------------------------------------


def test_status_tokens_from_finish_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given finish event has total_tokens_consumed=312000, budget shows 312k / 800k."""
    case_dir = _init_case(tmp_path, "mr-token-001", monkeypatch)
    _write_agent_jsonl(case_dir, [_step_event(1000, 500), _finish_event(total_tokens=312_000)])

    result = runner.invoke(app, ["status", "mr-token-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "312k / 800k budget" in result.output


# ---------------------------------------------------------------------------
# 7. Tokens computed from step events when no finish event present
# ---------------------------------------------------------------------------


def test_status_tokens_from_step_events(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given step events but no finish event, tokens are summed from step events."""
    case_dir = _init_case(tmp_path, "mr-inprogress-001", monkeypatch)
    # 5 step events x (2000 input + 1000 output) = 15000 tokens total
    events = [_step_event(2_000, 1_000) for _ in range(5)]
    _write_agent_jsonl(case_dir, events)

    result = runner.invoke(app, ["status", "mr-inprogress-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "15k / 800k budget" in result.output


# ---------------------------------------------------------------------------
# 8. --full shows confirmed/pivoted/abandoned sections
# ---------------------------------------------------------------------------


def test_status_full_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given --full, confirmed, pivoted, and abandoned hypotheses appear in output."""
    case_dir = _init_case(tmp_path, "mr-full-001", monkeypatch)
    snap = _make_stack_snapshot(
        active={"id": "H-001", "statement": "Active investigation thread"},
        history=[
            {"id": "H-002", "status": "CONFIRMED", "statement": "Confirmed persistence mechanism"},
            {"id": "H-003", "status": "PIVOTED", "statement": "Initial entry vector"},
            {"id": "H-004", "status": "ABANDONED", "statement": "Discarded lateral movement path"},
        ],
    )
    _write_agent_jsonl(case_dir, [_finish_event(stack_snapshot=snap)])

    result = runner.invoke(app, ["status", "mr-full-001", "--full"], catch_exceptions=False)
    assert result.exit_code == 0
    # All statuses should appear
    assert "ACTIVE" in result.output
    assert "CONFIRMED" in result.output
    assert "PIVOTED" in result.output
    assert "ABANDONED" in result.output
    # Hypothesis IDs should appear
    assert "H-002" in result.output
    assert "H-004" in result.output


# ---------------------------------------------------------------------------
# 9. Status is non-locking (safe during concurrent investigation)
# ---------------------------------------------------------------------------


def test_status_nonlocking_concurrent_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Status reads succeed while another thread holds a file write lock."""
    case_dir = _init_case(tmp_path, "mr-concurrent-001", monkeypatch)
    # Populate some agent events
    _write_agent_jsonl(case_dir, [_step_event(1000, 500)])

    # Simulate a concurrent writer holding a file open for writing
    agent_log = case_dir / "audit" / "agent.jsonl"
    write_errors: list[Exception] = []
    status_result: list[Any] = []

    def _writer() -> None:
        try:
            with agent_log.open("a", encoding="utf-8") as fh:
                time.sleep(0.2)  # Hold the file open during status read
                fh.write(json.dumps({"ts": "2026-01-01T00:01:00+00:00", "type": "step"}) + "\n")
        except Exception as exc:
            write_errors.append(exc)

    writer_thread = threading.Thread(target=_writer, daemon=True)
    writer_thread.start()
    time.sleep(0.05)  # Ensure writer is holding the file

    result = runner.invoke(app, ["status", "mr-concurrent-001"], catch_exceptions=False)
    status_result.append(result)

    writer_thread.join(timeout=2.0)

    assert not write_errors
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# 10. --watch exits 130 on SIGINT (subprocess isolation to avoid pytest interrupt)
# ---------------------------------------------------------------------------


def test_status_watch_exits_130_on_sigint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given --watch, the command exits 130 when SIGINT is sent to its process."""
    case_dir = _init_case(tmp_path, "mr-watch-001", monkeypatch)
    _write_agent_jsonl(case_dir, [_step_event()])

    env = {"SILENTWITNESS_CASES_DIR": str(tmp_path)}
    # Use the installed venv entry-point so Typer's sys.exit() propagates correctly.
    venv_bin = Path(sys.executable).parent
    cli_script = str(venv_bin / "silentwitness")
    proc = subprocess.Popen(
        [cli_script, "status", "mr-watch-001", "--watch"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**__import__("os").environ, **env},
    )
    time.sleep(0.6)  # Let at least one render happen
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=3.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        pytest.fail("--watch did not exit after SIGINT within 3s")

    assert proc.returncode == 130


# ---------------------------------------------------------------------------
# 11. INVESTIGATING status shown when no terminal event
# ---------------------------------------------------------------------------


def test_status_investigating_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given step events but no finish/sigint event, status shows INVESTIGATING."""
    case_dir = _init_case(tmp_path, "mr-running-001", monkeypatch)
    _write_agent_jsonl(case_dir, [_step_event(1000, 500)])

    result = runner.invoke(app, ["status", "mr-running-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "INVESTIGATING" in result.output


# ---------------------------------------------------------------------------
# 12. ABORTED status shown on sigint_checkpoint entry
# ---------------------------------------------------------------------------


def test_status_aborted_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given sigint_checkpoint event, status shows ABORTED."""
    case_dir = _init_case(tmp_path, "mr-aborted-001", monkeypatch)
    _write_agent_jsonl(
        case_dir,
        [
            _step_event(),
            {"ts": "2026-01-01T00:02:00+00:00", "event": "sigint_checkpoint", "step": 1},
        ],
    )

    result = runner.invoke(app, ["status", "mr-aborted-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "ABORTED" in result.output
