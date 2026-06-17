"""Integration tests for `silentwitness status` — core BDD scenarios (≥9 per story spec)."""

from __future__ import annotations

import json
import select
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from silentwitness_agent.cli import app
from tests.integration._helpers_status import (
    finish_event,
    init_case,
    make_stack_snapshot,
    runner,
    step_event,
    write_agent_jsonl,
    write_findings_json,
)

# 1. Case with no hypotheses shows zero counts and "no hypotheses yet"


def test_status_no_hypotheses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given a just-initialized case with no audit files, status shows zero counts."""
    init_case(tmp_path, "mr-idle-001", monkeypatch)
    result = runner.invoke(app, ["status", "mr-idle-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "no hypotheses yet" in result.output
    assert "(0 active, 0 confirmed, 0 pivoted, 0 abandoned)" in result.output


# 2. Full hypothesis counts match UX-spec sample shape


def test_status_hypothesis_counts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given 3 active + 2 confirmed + 1 pivoted + 0 abandoned, counts are correct."""
    case_dir = init_case(tmp_path, "mr-evil-001", monkeypatch)
    snap = make_stack_snapshot(
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
    write_agent_jsonl(case_dir, [finish_event(total_tokens=312_000, stack_snapshot=snap)])
    write_findings_json(case_dir, [{"status": "DRAFT"} for _ in range(9)])
    (case_dir / "audit" / "findings.jsonl").write_text(
        json.dumps({"result_summary": {"success": False}}) + "\n", encoding="utf-8"
    )
    result = runner.invoke(app, ["status", "mr-evil-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "(3 active, 2 confirmed, 1 pivoted, 0 abandoned)" in result.output
    assert "findings: staged 9  approved 0  rejected 1" in result.output
    assert "312k / 6M budget" in result.output


# 3. --json emits valid JSON with expected keys, no ANSI escapes


def test_status_json_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given --json, stdout is clean JSON with all required top-level keys."""
    case_dir = init_case(tmp_path, "mr-json-001", monkeypatch)
    snap = make_stack_snapshot(
        active={"id": "H-001", "statement": "Active hypothesis"},
        history=[{"id": "H-002", "status": "CONFIRMED", "statement": "Confirmed finding"}],
    )
    write_agent_jsonl(case_dir, [finish_event(total_tokens=50_000, stack_snapshot=snap)])
    result = runner.invoke(app, ["status", "mr-json-001", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    for key in ("case_id", "hypotheses", "findings", "budget", "last_event"):
        assert key in data
    assert data["case_id"] == "mr-json-001"
    assert data["hypotheses"]["counts"]["active"] == 1
    assert data["hypotheses"]["counts"]["confirmed"] == 1
    assert "\x1b[" not in result.output


# 4. Case not found exits 1


def test_status_case_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given a nonexistent case ID, status exits 1 with 'not found' in output."""
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    result = runner.invoke(app, ["status", "mr-evil-999"], catch_exceptions=False)
    assert result.exit_code == 1
    assert "mr-evil-999" in result.output
    assert "not found" in result.output


# 5. Corrupted hypothesis.jsonl exits 2


def test_status_corrupted_hypothesis_jsonl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given hypothesis.jsonl has a non-JSON line mid-file, status exits 2."""
    case_dir = init_case(tmp_path, "mr-corrupt-001", monkeypatch)
    write_agent_jsonl(case_dir, [step_event()])
    # Bad line in the middle (not last) → genuine corruption → exit 2
    (case_dir / "audit" / "hypothesis.jsonl").write_text(
        '{"type": "form", "hypothesis_id": "H-001"}\nNOT VALID JSON\n'
        '{"type": "form", "hypothesis_id": "H-002"}\n',
        encoding="utf-8",
    )
    result = runner.invoke(app, ["status", "mr-corrupt-001"], catch_exceptions=False)
    assert result.exit_code == 2
    assert "hypothesis.jsonl parse error at line" in result.output


# 6. Tokens from finish event total_tokens_consumed


def test_status_tokens_from_finish_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given finish event has total_tokens_consumed=312000, budget shows 312k / 6M."""
    case_dir = init_case(tmp_path, "mr-token-001", monkeypatch)
    write_agent_jsonl(case_dir, [step_event(1000, 500), finish_event(total_tokens=312_000)])
    result = runner.invoke(app, ["status", "mr-token-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "312k / 6M budget" in result.output


# 7. Tokens summed from step events when no finish event


def test_status_tokens_from_step_events(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given step events but no finish event, tokens are summed from step events."""
    case_dir = init_case(tmp_path, "mr-inprogress-001", monkeypatch)
    write_agent_jsonl(case_dir, [step_event(2_000, 1_000) for _ in range(5)])
    result = runner.invoke(app, ["status", "mr-inprogress-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "15k / 6M budget" in result.output


# 8. --full shows ABANDONED section once only (no double-render)


def test_status_full_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given --full, ABANDONED hypotheses appear in the dedicated section exactly once."""
    case_dir = init_case(tmp_path, "mr-full-001", monkeypatch)
    snap = make_stack_snapshot(
        active={"id": "H-001", "statement": "Active investigation thread"},
        history=[
            {"id": "H-002", "status": "CONFIRMED", "statement": "Confirmed persistence"},
            {"id": "H-003", "status": "PIVOTED", "statement": "Initial entry vector"},
            {"id": "H-004", "status": "ABANDONED", "statement": "Discarded lateral movement"},
        ],
    )
    write_agent_jsonl(case_dir, [finish_event(stack_snapshot=snap)])
    result = runner.invoke(app, ["status", "mr-full-001", "--full"], catch_exceptions=False)
    assert result.exit_code == 0
    for label in ("ACTIVE", "CONFIRMED", "PIVOTED", "ABANDONED"):
        assert label in result.output
    assert result.output.count("H-004") == 1


# 9. Non-locking concurrent read


def test_status_nonlocking_concurrent_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Status reads succeed while another thread holds a file write handle open."""
    case_dir = init_case(tmp_path, "mr-concurrent-001", monkeypatch)
    write_agent_jsonl(case_dir, [step_event(1000, 500)])
    agent_log = case_dir / "audit" / "agent.jsonl"
    write_errors: list[Exception] = []

    def _writer() -> None:
        try:
            with agent_log.open("a", encoding="utf-8") as fh:
                time.sleep(0.2)
                fh.write(json.dumps({"ts": "2026-01-01T00:01:00+00:00", "type": "step"}) + "\n")
        except Exception as exc:
            write_errors.append(exc)

    writer_thread = threading.Thread(target=_writer, daemon=True)
    writer_thread.start()
    time.sleep(0.05)
    result = runner.invoke(app, ["status", "mr-concurrent-001"], catch_exceptions=False)
    writer_thread.join(timeout=2.0)
    assert not write_errors
    assert result.exit_code == 0


# 10. --watch exits 130 on SIGINT (subprocess isolation)


def test_status_watch_exits_130_on_sigint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given --watch, the command exits 130 when SIGINT is sent to its process."""
    case_dir = init_case(tmp_path, "mr-watch-001", monkeypatch)
    write_agent_jsonl(case_dir, [step_event()])
    env = {"SILENTWITNESS_CASES_DIR": str(tmp_path)}
    venv_bin = Path(sys.executable).parent
    proc = subprocess.Popen(
        [str(venv_bin / "silentwitness"), "status", "mr-watch-001", "--watch"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**__import__("os").environ, **env},
    )
    # Deterministic readiness sync (replaces a flaky fixed sleep(0.6)): the watch
    # loop renders its first frame to stdout only AFTER its SIGINT handler is
    # installed, so wait for that first byte before signalling. A fixed sleep
    # raced startup — on a loaded CI box imports exceed it, SIGINT lands mid-import,
    # and the process exits with the wrong code (the long-standing flake).
    assert proc.stdout is not None
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            proc.wait()
            pytest.fail(f"--watch exited before rendering (code {proc.returncode})")
        readable, _, _ = select.select([proc.stdout], [], [], 0.2)
        if readable and proc.stdout.read(1):
            break  # first frame rendered → loop is running, handler installed
    else:
        proc.kill()
        proc.wait()
        pytest.fail("--watch never rendered a frame within 10s")
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        pytest.fail("--watch did not exit within 5s of SIGINT")
    assert proc.returncode == 130


# 11. INVESTIGATING status


def test_status_investigating_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given step events but no terminal event, status shows INVESTIGATING."""
    case_dir = init_case(tmp_path, "mr-running-001", monkeypatch)
    write_agent_jsonl(case_dir, [step_event(1000, 500)])
    result = runner.invoke(app, ["status", "mr-running-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "INVESTIGATING" in result.output


def test_status_reports_terminal_non_completed_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Given a finish event with MAX_ITERATIONS, status does not call it COMPLETED."""
    case_dir = init_case(tmp_path, "mr-max-iterations-001", monkeypatch)
    write_agent_jsonl(case_dir, [finish_event(final_state="MAX_ITERATIONS")])
    result = runner.invoke(app, ["status", "mr-max-iterations-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "MAX_ITERATIONS" in result.output
    assert "COMPLETED" not in result.output


# 12. ABORTED status on sigint_checkpoint


def test_status_aborted_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given sigint_checkpoint event, status shows ABORTED."""
    case_dir = init_case(tmp_path, "mr-aborted-001", monkeypatch)
    write_agent_jsonl(
        case_dir,
        [
            step_event(),
            {"ts": "2026-01-01T00:02:00+00:00", "event": "sigint_checkpoint", "step": 1},
        ],
    )
    result = runner.invoke(app, ["status", "mr-aborted-001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "ABORTED" in result.output
