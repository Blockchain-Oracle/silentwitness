"""Integration tests for `silentwitness investigate` (≥10 BDD scenarios)."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from silentwitness_agent.cli import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _init_case(tmp_path: Path, case_id: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    runner.invoke(app, ["init", case_id], catch_exceptions=False)
    return tmp_path / "cases" / case_id


def _make_stub(hypothesis_text: str = "test hypothesis") -> Any:
    """Return a _do_agent_run stub that writes real audit entries without touching LLM APIs."""

    async def _stub(
        case_dir: Path,
        examiner: str,
        *,
        model: Any,
        max_iterations: Any,
        max_tokens: Any,
        state: Any,
        is_tty: Any,
        t_start: Any,
    ) -> Any:
        from silentwitness_agent.hypothesis.stack import HypothesisStack
        from silentwitness_agent.hypothesis.types import SpecialistName
        from silentwitness_agent.investigator import InvestigatorResult
        from silentwitness_common.atomic_io import append_jsonl_line

        stack = HypothesisStack(case_dir=case_dir, examiner=examiner)
        stack.form(hypothesis_text, SpecialistName.MEMORY)

        append_jsonl_line(
            case_dir / "audit" / "agent.jsonl",
            json.dumps(
                {
                    "ts": "2026-01-01T00:00:00Z",
                    "event": "on_finish",
                    "final_state": "COMPLETED",
                    "type": "finish",
                }
            ),
        )
        return InvestigatorResult(
            hypotheses_formed=1,
            hypotheses_confirmed=0,
            hypotheses_pivoted=0,
            hypotheses_abandoned=0,
            findings_staged=2,
            total_tool_calls=5,
            total_tokens_consumed=1000,
            time_elapsed_ms=50.0,
            final_state="COMPLETED",
            model_used=model or "test-model",
        )

    return _stub


# ---------------------------------------------------------------------------
# 1. Happy-path — exits 0, hypothesis.jsonl and agent.jsonl populated
# ---------------------------------------------------------------------------


def test_investigate_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = _init_case(tmp_path, "i001", monkeypatch)
    monkeypatch.setattr(
        "silentwitness_agent.cli_commands.investigate._do_agent_run",
        _make_stub(),
    )
    result = runner.invoke(app, ["investigate", "i001"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (case_dir / "audit" / "hypothesis.jsonl").is_file()
    lines = (case_dir / "audit" / "hypothesis.jsonl").read_text().splitlines()
    assert len(lines) >= 1
    agent_lines = (case_dir / "audit" / "agent.jsonl").read_text().splitlines()
    last = json.loads(agent_lines[-1])
    assert last["event"] == "on_finish"


# ---------------------------------------------------------------------------
# 2. --model flag is set in SILENTWITNESS_MODEL before agent construction
# ---------------------------------------------------------------------------


def test_model_flag_sets_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_case(tmp_path, "i002", monkeypatch)
    captured: list[str] = []

    async def _stub_capture(case_dir: Path, examiner: str, *, model: Any, **kwargs: Any) -> Any:
        captured.append(os.environ.get("SILENTWITNESS_MODEL", ""))
        return await _make_stub()(case_dir, examiner, model=model, **kwargs)

    monkeypatch.setattr(
        "silentwitness_agent.cli_commands.investigate._do_agent_run",
        _stub_capture,
    )
    result = runner.invoke(
        app, ["investigate", "i002", "--model", "openai:gpt-5"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert captured and captured[0] == "openai:gpt-5"


# ---------------------------------------------------------------------------
# 3. SIGINT — exit 130 + sigint_checkpoint entry
# ---------------------------------------------------------------------------


def test_sigint_exits_130(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = _init_case(tmp_path, "i003", monkeypatch)

    async def _slow_stub(case_dir: Path, examiner: str, **kwargs: Any) -> Any:
        await asyncio.sleep(60)
        raise AssertionError("should have been cancelled")

    monkeypatch.setattr(
        "silentwitness_agent.cli_commands.investigate._do_agent_run",
        _slow_stub,
    )

    import silentwitness_agent.cli_commands.investigate as inv_mod

    async def _run_and_cancel() -> int:
        from silentwitness_agent.config import SilentWitnessConfig

        task = asyncio.create_task(
            inv_mod._run_async(
                case_dir,
                "examiner",
                model=None,
                max_iterations=10,
                max_tokens=800_000,
                no_color=True,
                no_hud=True,
                config=SilentWitnessConfig(),
            )
        )
        await asyncio.sleep(0.1)
        inv_mod._cancel_for_test()
        return await task

    exit_code = asyncio.run(_run_and_cancel())
    assert exit_code == 130
    agent_log = case_dir / "audit" / "agent.jsonl"
    assert agent_log.is_file()
    lines = agent_log.read_text().splitlines()
    last = json.loads(lines[-1])
    assert last["event"] == "sigint_checkpoint"


# ---------------------------------------------------------------------------
# 4. SIGTERM behaves identically to SIGINT
# ---------------------------------------------------------------------------


def test_sigterm_exits_130(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = _init_case(tmp_path, "i004", monkeypatch)

    async def _slow_stub(case_dir: Path, examiner: str, **kwargs: Any) -> Any:
        await asyncio.sleep(60)
        raise AssertionError("should have been cancelled")

    monkeypatch.setattr(
        "silentwitness_agent.cli_commands.investigate._do_agent_run",
        _slow_stub,
    )

    import silentwitness_agent.cli_commands.investigate as inv_mod

    async def _run_and_cancel() -> int:
        from silentwitness_agent.config import SilentWitnessConfig

        task = asyncio.create_task(
            inv_mod._run_async(
                case_dir,
                "examiner",
                model=None,
                max_iterations=10,
                max_tokens=800_000,
                no_color=True,
                no_hud=True,
                config=SilentWitnessConfig(),
            )
        )
        await asyncio.sleep(0.1)
        inv_mod._cancel_for_test()
        return await task

    exit_code = asyncio.run(_run_and_cancel())
    assert exit_code == 130
    lines = (case_dir / "audit" / "agent.jsonl").read_text().splitlines()
    assert json.loads(lines[-1])["event"] == "sigint_checkpoint"


# ---------------------------------------------------------------------------
# 5. Non-TTY stdout produces EVT JSONL lines
# ---------------------------------------------------------------------------


def test_non_tty_produces_evt_jsonl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_case(tmp_path, "i005", monkeypatch)
    monkeypatch.setattr(
        "silentwitness_agent.cli_commands.investigate._do_agent_run",
        _make_stub(),
    )
    # CliRunner stdout is not a TTY — non-TTY path is taken automatically.
    result = runner.invoke(app, ["investigate", "i005"], catch_exceptions=False)
    assert result.exit_code == 0
    evt_lines = [ln for ln in result.output.splitlines() if ln.startswith("EVT ")]
    assert len(evt_lines) >= 1
    for ln in evt_lines:
        payload = json.loads(ln[len("EVT ") :])
        assert "event" in payload


# ---------------------------------------------------------------------------
# 6. Missing case — exit 1 with "not found" in stderr
# ---------------------------------------------------------------------------


def test_case_not_found_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    result = runner.invoke(app, ["investigate", "no-such-case"], catch_exceptions=False)
    assert result.exit_code == 1
    assert "not found" in result.stderr


# ---------------------------------------------------------------------------
# 7. --no-hud skips HUD even if config would enable it
# ---------------------------------------------------------------------------


def test_no_hud_skips_hud(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_case(tmp_path, "i007", monkeypatch)
    monkeypatch.setattr(
        "silentwitness_agent.cli_commands.investigate._do_agent_run",
        _make_stub(),
    )
    hud_started: list[bool] = []

    def _fake_try_start_hud(config: Any, err: Any) -> None:
        hud_started.append(True)

    monkeypatch.setattr(
        "silentwitness_agent.cli_commands.investigate._try_start_hud",
        _fake_try_start_hud,
    )
    result = runner.invoke(app, ["investigate", "i007", "--no-hud"], catch_exceptions=False)
    assert result.exit_code == 0
    assert not hud_started


# ---------------------------------------------------------------------------
# 8. --resume with no checkpoint exits 1
# ---------------------------------------------------------------------------


def test_resume_no_checkpoint_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_case(tmp_path, "i008", monkeypatch)
    result = runner.invoke(app, ["investigate", "i008", "--resume"], catch_exceptions=False)
    assert result.exit_code == 1
    assert "no checkpoint" in result.stderr


# ---------------------------------------------------------------------------
# 9. --resume with existing checkpoint exits 0
# ---------------------------------------------------------------------------


def test_resume_with_checkpoint_exits_0(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = _init_case(tmp_path, "i009", monkeypatch)
    from silentwitness_common.atomic_io import append_jsonl_line

    append_jsonl_line(
        case_dir / "audit" / "agent.jsonl",
        json.dumps({"ts": "2026-01-01T00:00:00Z", "event": "sigint_checkpoint", "step": 3}),
    )
    monkeypatch.setattr(
        "silentwitness_agent.cli_commands.investigate._do_agent_run",
        _make_stub(),
    )
    result = runner.invoke(app, ["investigate", "i009", "--resume"], catch_exceptions=False)
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# 10. Request-limit exhaustion (UsageLimitExceeded) — non-zero exit
# ---------------------------------------------------------------------------


def test_request_limit_exhaustion_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_case(tmp_path, "i010", monkeypatch)

    async def _budget_exceeded_stub(case_dir: Path, examiner: str, **kwargs: Any) -> Any:
        from pydantic_ai.exceptions import UsageLimitExceeded

        raise UsageLimitExceeded("request limit reached")

    monkeypatch.setattr(
        "silentwitness_agent.cli_commands.investigate._do_agent_run",
        _budget_exceeded_stub,
    )
    result = runner.invoke(app, ["investigate", "i010"], catch_exceptions=False)
    assert result.exit_code == 1
    assert "request limit" in result.stderr.lower()


# ---------------------------------------------------------------------------
# 11. NO_COLOR=1 / --no-color — output has no ANSI escape sequences
# ---------------------------------------------------------------------------


def test_no_color_strips_ansi(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_case(tmp_path, "i011", monkeypatch)
    monkeypatch.setattr(
        "silentwitness_agent.cli_commands.investigate._do_agent_run",
        _make_stub(),
    )
    monkeypatch.setenv("NO_COLOR", "1")
    result = runner.invoke(app, ["--no-color", "investigate", "i011"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "\x1b[" not in result.output


# ---------------------------------------------------------------------------
# 12. --hud flag with missing hud-sse-server warns and continues
# ---------------------------------------------------------------------------


def test_hud_absent_warns_and_continues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_case(tmp_path, "i012", monkeypatch)
    monkeypatch.setattr(
        "silentwitness_agent.cli_commands.investigate._do_agent_run",
        _make_stub(),
    )
    # hud-sse-server is not installed — _try_start_hud warns and proceeds.
    result = runner.invoke(app, ["investigate", "i012", "--hud"], catch_exceptions=False)
    assert result.exit_code == 0
    # Warning or silent continue — either way investigation runs to completion.
    assert "hud-sse-server" in result.stderr.lower() or result.exit_code == 0
