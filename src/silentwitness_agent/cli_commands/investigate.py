"""CLI investigate command: orchestrate investigator agent + 4-pane rich.live render.

SIGINT/SIGTERM flow (load-bearing per story):
  1. loop.add_signal_handler passes agent_task.cancel as the SIGINT/SIGTERM callback directly.
  2. CancelledError propagates from await agent_task into the outer except block.
  3. We write a sigint_checkpoint entry to audit/agent.jsonl, then return 130.
  4. Rich Live is always stopped in a finally block to prevent raw-mode leakage.

Test seam: monkeypatch _do_agent_run to replace the full agent build-and-run
cycle; doing so skips all model construction (no API key required in tests).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import signal
import sys
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.layout import Layout
from rich.live import Live

from silentwitness_agent.cli_commands._live_layout import build_layout, update_layout
from silentwitness_agent.cli_commands._live_render import (
    DisplayState,
    build_display_hooks,
    decay_flash,
    refresh_layout_loop,
    stream_hypothesis_events,
)
from silentwitness_agent.config import SilentWitnessConfig
from silentwitness_common.atomic_io import append_jsonl_line
from silentwitness_mcp.evidence.registry import EvidenceRegistry

# Held during an active investigation so tests can trigger cancellation.
_active_agent_task: asyncio.Task[Any] | None = None


# ---------------------------------------------------------------------------
# Public test helper
# ---------------------------------------------------------------------------


def _cancel_for_test() -> None:
    """Cancel the active agent task — for integration testing only."""
    if _active_agent_task is not None:
        _active_agent_task.cancel()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_case_dir(case_id: str) -> Path:
    root = Path(os.environ.get("SILENTWITNESS_CASES_DIR") or str(Path.cwd()))
    return root / "cases" / case_id


def _read_case_examiner(case_dir: Path, fallback: str) -> str:
    toml_path = case_dir / ".silentwitness" / "case.toml"
    if not toml_path.is_file():
        return fallback
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
        return str(data.get("examiner", fallback))
    except (tomllib.TOMLDecodeError, OSError):
        return fallback


def _emit_sigint_checkpoint(case_dir: Path, step: int) -> None:
    payload = {
        "ts": datetime.now(UTC).isoformat(),
        "event": "sigint_checkpoint",
        "step": step,
        "reason": "sigint_checkpoint",
    }
    # Best-effort: ValueError (forbidden chars) or OSError (disk) must not abort SIGINT exit.
    with contextlib.suppress(Exception):
        append_jsonl_line(case_dir / "audit" / "agent.jsonl", json.dumps(payload))


def _load_checkpoint(case_dir: Path) -> dict[str, Any] | None:
    """Return the last sigint_checkpoint entry from agent.jsonl, or None."""
    agent_log = case_dir / "audit" / "agent.jsonl"
    if not agent_log.is_file():
        return None
    try:
        text = agent_log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None  # unreadable checkpoint treated same as absent
    for raw in reversed(text.splitlines()):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if obj.get("event") == "sigint_checkpoint":
                return dict(obj)
        except json.JSONDecodeError:
            pass
    return None


def _try_start_hud(config: SilentWitnessConfig, err: Console) -> None:
    try:
        from hud_sse_server import start  # type: ignore[import-not-found]
    except ImportError:
        err.print(
            "[yellow]⚠[/yellow] HUD requested but hud-sse-server not installed;"
            " continuing without HUD",
            highlight=False,
        )
        return
    try:
        start(port=config.hud.port, bind=config.hud.bind)
    except Exception as exc:
        err.print(
            f"[yellow]⚠[/yellow] HUD server failed to start: {exc}; continuing without HUD",
            highlight=False,
        )


# ---------------------------------------------------------------------------
# Agent run wrapper — all agent construction is here so tests stub at this seam
# ---------------------------------------------------------------------------


async def _do_agent_run(
    case_dir: Path,
    examiner: str,
    *,
    model: str | None,
    max_iterations: int,
    max_tokens: int,
    state: DisplayState,
    is_tty: bool,
    t_start: float,
) -> Any:  # pragma: no cover — integration-only seam (monkeypatched in tests)
    """Test seam (monkeypatched in tests to bypass model construction); else builds
    the investigator, runs it, returns InvestigatorResult."""
    from pydantic_ai.usage import UsageLimits

    from silentwitness_agent.hooks import build_investigator_hooks
    from silentwitness_agent.hypothesis.budget import BudgetEnforcer
    from silentwitness_agent.hypothesis.stack import HypothesisStack
    from silentwitness_agent.hypothesis_tools import register_hypothesis_tools
    from silentwitness_agent.investigator import (
        InvestigatorDeps,
        InvestigatorResult,
        build_investigator,
    )
    from silentwitness_agent.live_critic import (
        build_live_critic_hooks,
        register_pending_critique_instruction,
    )
    from silentwitness_agent.specialists._wiring import register_all_specialists

    stack = HypothesisStack(case_dir=case_dir, examiner=examiner)
    budget = BudgetEnforcer(default_token_budget=max_tokens)
    audit_hooks = build_investigator_hooks(case_dir, examiner, stack, budget)
    display_hooks = build_display_hooks(state, is_tty)
    # Live closed-loop critic: CHALLENGEs route into deps.pending_critiques each turn.
    critic_hooks = build_live_critic_hooks(case_dir, examiner, model=model)
    cfg = build_investigator(
        case_dir,
        examiner,
        model=model,
        max_iterations=max_iterations,
        hooks=[audit_hooks, display_hooks, critic_hooks],
    )
    register_hypothesis_tools(cfg.agent)  # without these the hypothesis wedge stays at zero
    register_pending_critique_instruction(cfg.agent)
    register_all_specialists(cfg.agent, model=model, shared_server=cfg.mcp_server)
    deps = InvestigatorDeps(case_dir=case_dir, examiner=examiner, stack=stack, budget=budget)

    # Surface registered evidence in the opening prompt so the agent doesn't burn
    # iterations guessing paths that fail registration.
    evidence_records = EvidenceRegistry(case_dir=case_dir).list_all()
    evidence_block = (
        "\n".join(f"- {rec.path} ({rec.type.value})" for rec in evidence_records)
        or "- (no evidence registered)"
    )
    run_result = await cfg.agent.run(
        f"Investigate case {case_dir.name}.\n\n"
        "This evidence is parsed into the searchable case index — discover with "
        f"search_evidence/timeline/get_record (do NOT read raw artifacts):\n{evidence_block}\n\n"
        "Form your first hypothesis and analyse the evidence by querying the index.",
        deps=deps,
        usage_limits=UsageLimits(request_limit=cfg.max_iters),
    )
    snap = deps.stack.snapshot()
    usage = run_result.usage
    return InvestigatorResult(
        hypotheses_formed=len(snap.history) + (1 if snap.active else 0),
        hypotheses_confirmed=sum(1 for h in snap.history if str(h.status).upper() == "CONFIRMED"),
        hypotheses_pivoted=snap.total_pivot_count,
        hypotheses_abandoned=sum(1 for h in snap.history if str(h.status).upper() == "ABANDONED"),
        findings_staged=run_result.output.findings_staged,
        total_tool_calls=run_result.output.total_tool_calls,
        total_tokens_consumed=getattr(usage, "total_tokens", 0) or 0,
        time_elapsed_ms=(time.monotonic() - t_start) * 1000,
        final_state="COMPLETED",
        model_used=cfg.model_str,
    )


# ---------------------------------------------------------------------------
# Core async orchestrator
# ---------------------------------------------------------------------------


async def _run_async(
    case_dir: Path,
    examiner: str,
    *,
    model: str | None,
    max_iterations: int,
    max_tokens: int,
    no_color: bool,
    no_hud: bool,
    config: SilentWitnessConfig,
) -> int:
    """Run the investigation; returns exit code (0 = ok, 1 = error, 130 = SIGINT/SIGTERM)."""
    global _active_agent_task

    from pydantic_ai.exceptions import UsageLimitExceeded

    is_tty = sys.stdout.isatty()
    t_start = time.monotonic()
    state = DisplayState(t_start=t_start)

    agent_task: asyncio.Task[Any] = asyncio.create_task(
        _do_agent_run(
            case_dir,
            examiner,
            model=model,
            max_iterations=max_iterations,
            max_tokens=max_tokens,
            state=state,
            is_tty=is_tty,
            t_start=t_start,
        )
    )
    _active_agent_task = agent_task

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, agent_task.cancel)
    loop.add_signal_handler(signal.SIGTERM, agent_task.cancel)

    live: Live | None = None
    live_started: bool = False
    decay_task: asyncio.Task[None] | None = None
    refresh_task: asyncio.Task[None] | None = None
    stream_task: asyncio.Task[None] | None = None

    try:
        if is_tty:
            layout: Layout = build_layout()
            update_layout(
                layout,
                stack_snap=None,
                active_tool=None,
                findings=None,
                budget=None,
                last_event=None,
                flash_frame=0,
            )
            decay_task = asyncio.create_task(decay_flash(state))
            refresh_task = asyncio.create_task(refresh_layout_loop(layout, state))
            live = Live(layout, refresh_per_second=4, console=Console(no_color=no_color))
            live.start()
            live_started = True
            await agent_task
        else:
            stream_task = asyncio.create_task(stream_hypothesis_events(case_dir))
            await agent_task
            # Yield to let the stream task pick up any trailing hypothesis events.
            await asyncio.sleep(0.15)

        return 0

    except asyncio.CancelledError:
        _emit_sigint_checkpoint(case_dir, state.step_count)
        return 130

    except UsageLimitExceeded:
        return 0

    except Exception as exc:
        Console(stderr=True, no_color=no_color).print(
            f"[red]✗[/red] Investigation failed: {exc}", highlight=False
        )
        return 1

    finally:
        _active_agent_task = None
        if decay_task is not None:
            decay_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await decay_task
        if refresh_task is not None:
            refresh_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await refresh_task
        if stream_task is not None:
            stream_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await stream_task
        if live is not None and live_started:
            if is_tty and state.stack_snap is not None:
                update_layout(
                    live.renderable,  # type: ignore[arg-type]
                    stack_snap=state.stack_snap,
                    active_tool=state.active_tool,
                    findings=state.findings,
                    budget=state.budget,
                    last_event=state.last_event,
                    flash_frame=0,
                )
            live.stop()
        with contextlib.suppress(OSError, RuntimeError):
            loop.remove_signal_handler(signal.SIGINT)
        with contextlib.suppress(OSError, RuntimeError):
            loop.remove_signal_handler(signal.SIGTERM)


# ---------------------------------------------------------------------------
# Sync entry point called by cli.py Typer command
# ---------------------------------------------------------------------------


def run(
    case_id: str,
    config: SilentWitnessConfig,
    no_color: bool,
    quiet: bool,
    debug: bool,
    *,
    model: str | None,
    max_iterations: int,
    max_tokens: int,
    no_hud: bool,
    hud: bool,
    resume: bool,
) -> None:
    err = Console(stderr=True, no_color=no_color)
    case_dir = _resolve_case_dir(case_id)
    if not case_dir.exists():
        err.print(f"[red]✗[/red] case '{case_id}' not found", highlight=False)
        raise typer.Exit(code=1)

    if resume and _load_checkpoint(case_dir) is None:
        err.print("[red]✗[/red] no checkpoint to resume from", highlight=False)
        raise typer.Exit(code=1)

    should_start_hud = (not no_hud) and (hud or config.hud.enabled)
    if should_start_hud:
        _try_start_hud(config, err)

    resolved_model = model or os.environ.get("SILENTWITNESS_MODEL") or config.model.default
    examiner = _read_case_examiner(case_dir, config.examiner.name)

    # Set SILENTWITNESS_MODEL for the duration of the run then restore.
    _prev_model = os.environ.get("SILENTWITNESS_MODEL")
    os.environ["SILENTWITNESS_MODEL"] = resolved_model
    try:
        exit_code: int = asyncio.run(
            _run_async(
                case_dir,
                examiner,
                model=resolved_model,
                max_iterations=max_iterations,
                max_tokens=max_tokens,
                no_color=no_color,
                no_hud=no_hud,
                config=config,
            )
        )
    except KeyboardInterrupt:
        exit_code = 130
    except Exception as exc:
        err.print(f"[red]✗[/red] Investigation failed: {exc}", highlight=False)
        exit_code = 1
    finally:
        if _prev_model is None:
            os.environ.pop("SILENTWITNESS_MODEL", None)
        else:
            os.environ["SILENTWITNESS_MODEL"] = _prev_model
    raise typer.Exit(code=exit_code)
