"""Regression tests for investigate command run-wide usage limits."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pydantic_ai.exceptions import UsageLimitExceeded
from typer.testing import CliRunner

from silentwitness_agent.cli import app
from silentwitness_agent.cli_commands._investigate_runner import (
    _agent_usage_limits,
    _usage_limit_final_state,
)

runner = CliRunner()


def _init_case(tmp_path: Path, case_id: str, monkeypatch: Any) -> Path:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    runner.invoke(app, ["init", case_id], catch_exceptions=False)
    return tmp_path / "cases" / case_id


async def _stub_result(case_dir: Path, examiner: str, *, model: Any = None, **kwargs: Any) -> Any:
    from silentwitness_agent.investigator import InvestigatorResult

    return InvestigatorResult(
        hypotheses_formed=1,
        hypotheses_confirmed=0,
        hypotheses_pivoted=0,
        hypotheses_abandoned=0,
        findings_staged=0,
        total_tool_calls=0,
        total_tokens_consumed=0,
        time_elapsed_ms=1.0,
        final_state="COMPLETED",
        model_used=model or "test",
    )


def test_investigate_uses_configured_budget_defaults(tmp_path: Path, monkeypatch: Any) -> None:
    _init_case(tmp_path, "i-budget-defaults", monkeypatch)
    captured: list[tuple[int | None, int]] = []

    async def _capture(
        case_dir: Path,
        examiner: str,
        *,
        max_iterations: int | None,
        max_tokens: int,
        **kwargs: Any,
    ) -> Any:
        captured.append((max_iterations, max_tokens))
        return await _stub_result(
            case_dir,
            examiner,
            max_iterations=max_iterations,
            max_tokens=max_tokens,
            **kwargs,
        )

    monkeypatch.setattr(
        "silentwitness_agent.cli_commands.investigate._do_agent_run",
        _capture,
    )

    result = runner.invoke(app, ["investigate", "i-budget-defaults"], catch_exceptions=False)

    assert result.exit_code == 0
    assert captured == [(80, 6_000_000)]


def test_runner_usage_limits_include_token_budget() -> None:
    limits = _agent_usage_limits(request_limit=80, token_limit=6_000_000)

    assert limits.request_limit == 80
    assert limits.total_tokens_limit == 6_000_000
    assert limits.count_tokens_before_request is True


def test_runner_classifies_token_limit_as_budget_exhausted() -> None:
    state = _usage_limit_final_state(
        UsageLimitExceeded("Exceeded the total_tokens_limit of 6000000")
    )

    assert state == "BUDGET_EXHAUSTED"


def test_tty_live_cleanup_uses_original_layout(tmp_path: Path, monkeypatch: Any) -> None:
    case_dir = _init_case(tmp_path, "i-live-cleanup", monkeypatch)

    async def _stub(case_dir: Path, examiner: str, **kwargs: Any) -> Any:
        from silentwitness_agent.cli_commands._live_layout import (
            BudgetSnapshot,
            FindingsSnapshot,
        )
        from silentwitness_agent.hypothesis.stack import HypothesisStack
        from silentwitness_agent.hypothesis.types import SpecialistName
        from silentwitness_agent.investigator import InvestigatorResult

        state = kwargs["state"]
        stack = HypothesisStack(case_dir=case_dir, examiner=examiner)
        stack.form("test hypothesis", SpecialistName.LOG)
        state.stack_snap = stack.snapshot()
        state.findings = FindingsSnapshot(
            findings_staged=0,
            total_tool_calls=0,
            elapsed_ms=1.0,
        )
        state.budget = BudgetSnapshot(
            tokens_remaining=6_000_000,
            steps_remaining=80,
            tokens_budgeted=6_000_000,
            steps_budgeted=80,
        )
        return InvestigatorResult(
            hypotheses_formed=1,
            hypotheses_confirmed=0,
            hypotheses_pivoted=0,
            hypotheses_abandoned=0,
            findings_staged=0,
            total_tool_calls=0,
            total_tokens_consumed=0,
            time_elapsed_ms=1.0,
            final_state="COMPLETED",
            model_used="test",
        )

    class _BadRenderable:
        def __getitem__(self, key: str) -> object:
            raise AssertionError("cleanup must not index live.renderable")

    stopped: list[bool] = []

    class _FakeLive:
        def __init__(self, renderable: object, **kwargs: object) -> None:
            self.renderable = _BadRenderable()

        def start(self) -> None:
            return None

        def stop(self) -> None:
            stopped.append(True)

    import silentwitness_agent.cli_commands.investigate as inv_mod
    from silentwitness_agent.config import SilentWitnessConfig

    monkeypatch.setattr(
        "silentwitness_agent.cli_commands.investigate._do_agent_run",
        _stub,
    )
    monkeypatch.setattr("silentwitness_agent.cli_commands.investigate.Live", _FakeLive)
    monkeypatch.setattr(inv_mod.sys, "stdout", SimpleNamespace(isatty=lambda: True))

    exit_code = asyncio.run(
        inv_mod._run_async(
            case_dir,
            "examiner",
            model=None,
            max_iterations=80,
            max_tokens=6_000_000,
            no_color=True,
            no_hud=True,
            config=SilentWitnessConfig(),
        )
    )

    assert exit_code == 0
    assert stopped == [True]
