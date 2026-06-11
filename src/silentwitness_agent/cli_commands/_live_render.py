"""In-process display state, hooks factory, and background state-update tasks."""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.layout import Layout

from silentwitness_agent.cli_commands._live_layout import ToolCallSnapshot, update_layout

if TYPE_CHECKING:
    pass

_EVT_PREFIX = "EVT "

_HYP_TYPE_TO_EVT: dict[str, str] = {
    "form": "HYPOTHESIS_FORMED",
    "dispatch": "HYPOTHESIS_DISPATCHED",
    "confirm": "HYPOTHESIS_CONFIRMED",
    "pivot": "HYPOTHESIS_PIVOTED",
    "abandon": "HYPOTHESIS_ABANDONED",
}


@dataclasses.dataclass
class DisplayState:
    """Mutable display state written by hooks and read by update_layout on each refresh tick."""

    stack_snap: Any = None  # StackSnapshot | None
    active_tool: ToolCallSnapshot | None = None
    findings: Any = None  # FindingsSnapshot | None
    budget: Any = None  # BudgetSnapshot | None
    last_event: Any = None  # HypothesisEvent | None
    flash_frame: int = 0
    step_count: int = 0
    t_start: float = dataclasses.field(default_factory=time.monotonic)


def build_display_hooks(state: DisplayState, is_tty: bool) -> Any:
    """Return a Pydantic AI Hooks instance that updates DisplayState and emits non-TTY EVT lines."""
    from pydantic_ai import RunContext
    from pydantic_ai.capabilities import Hooks, ValidatedToolArgs
    from pydantic_ai.messages import ModelResponse, ToolCallPart
    from pydantic_ai.models import ModelRequestContext
    from pydantic_ai.tools import ToolDefinition

    from silentwitness_agent.investigator import InvestigatorDeps

    hooks: Hooks[InvestigatorDeps] = Hooks()

    @hooks.on.before_tool_execute
    async def _before_tool(
        ctx: RunContext[InvestigatorDeps],
        /,
        *,
        call: ToolCallPart,
        tool_def: ToolDefinition,
        args: ValidatedToolArgs,
    ) -> ValidatedToolArgs:
        try:
            args_summary = json.dumps(args, default=str)[:100]
        except (TypeError, ValueError):
            args_summary = "<unserializable>"
        state.active_tool = ToolCallSnapshot(
            tool_name=call.tool_name,
            args_summary=args_summary,
            started_at=datetime.now(UTC),
        )
        return args

    @hooks.on.after_tool_execute
    async def _after_tool(
        ctx: RunContext[InvestigatorDeps],
        /,
        *,
        call: ToolCallPart,
        tool_def: ToolDefinition,
        args: ValidatedToolArgs,
        result: Any,
    ) -> Any:
        state.active_tool = None
        # display-only; never abort agent run on snapshot failure
        with contextlib.suppress(Exception):
            state.stack_snap = ctx.deps.stack.snapshot()
        return result

    @hooks.on.after_model_request
    async def _after_model_req(
        ctx: RunContext[InvestigatorDeps],
        /,
        *,
        request_context: ModelRequestContext,
        response: ModelResponse,
    ) -> ModelResponse:
        prev_pivots = state.stack_snap.total_pivot_count if state.stack_snap is not None else 0
        snap = state.stack_snap  # fallback to last known state if snapshot() fails
        with contextlib.suppress(Exception):
            snap = ctx.deps.stack.snapshot()
            state.stack_snap = snap
        if snap is not None and snap.total_pivot_count > prev_pivots:
            state.flash_frame = 4
        state.step_count += 1
        if not is_tty:
            hyp_id = snap.active.id if snap is not None and snap.active else None
            evt = {
                "event": "step",
                "active_hypothesis_id": hyp_id,
                "ts": datetime.now(UTC).isoformat(),
            }
            print(f"{_EVT_PREFIX}{json.dumps(evt)}", flush=True)
        return response

    return hooks


async def stream_hypothesis_events(case_dir: Path) -> None:
    """Tail hypothesis.jsonl and emit each new entry as an EVT JSONL line.

    Maps hypothesis ``type`` values to SCREAMING_SNAKE_CASE ``event`` names
    (e.g. ``pivot`` → ``HYPOTHESIS_PIVOTED``) so non-TTY consumers can filter
    with ``jq '.event'`` without knowing the hypothesis schema internals.
    """
    path = case_dir / "audit" / "hypothesis.jsonl"
    seen = 0
    while True:
        await asyncio.sleep(0.1)
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for raw in lines[seen:]:
            line = raw.strip()
            if line:
                try:
                    obj = json.loads(line)
                    event_name = _HYP_TYPE_TO_EVT.get(
                        str(obj.get("type", "")).lower(),
                        str(obj.get("type", "UNKNOWN")).upper(),
                    )
                    obj["event"] = event_name
                    print(f"{_EVT_PREFIX}{json.dumps(obj)}", flush=True)
                except json.JSONDecodeError:
                    print(
                        f"{_EVT_PREFIX}{json.dumps({'event': 'PARSE_ERROR', 'raw': line[:200]})}",
                        flush=True,
                    )
            seen += 1


async def decay_flash(state: DisplayState) -> None:
    """Decrement flash_frame at 4 Hz so pivot yellow flash lasts ~1 s.

    Note: _after_model_req also resets flash_frame to 4 on each pivot, so actual
    flash duration may be shorter when LLM responses arrive during the window.
    """
    while True:
        await asyncio.sleep(0.25)
        if state.flash_frame > 0:
            state.flash_frame -= 1


async def refresh_layout_loop(layout: Layout, state: DisplayState) -> None:
    """Re-render all Rich layout panes from DisplayState at 4 Hz (0.25 s cadence)."""
    while True:
        await asyncio.sleep(0.25)
        update_layout(
            layout,
            stack_snap=state.stack_snap,
            active_tool=state.active_tool,
            findings=state.findings,
            budget=state.budget,
            last_event=state.last_event,
            flash_frame=state.flash_frame,
        )
