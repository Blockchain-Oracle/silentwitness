"""Pure layout builders for the 4-pane rich.live investigation HUD (ux-spec §2.3)."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from rich.layout import Layout
from rich.panel import Panel

if TYPE_CHECKING:
    from silentwitness_agent.hypothesis.stack import StackSnapshot
    from silentwitness_agent.hypothesis.types import HypothesisEvent


@dataclasses.dataclass(frozen=True)
class ToolCallSnapshot:
    """Point-in-time capture of an in-progress tool call."""

    tool_name: str
    args_summary: str  # pre-truncated to ≤100 chars
    started_at: datetime  # must be UTC-aware

    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware (UTC)")


@dataclasses.dataclass(frozen=True)
class FindingsSnapshot:
    """Cumulative investigation statistics."""

    findings_staged: int
    total_tool_calls: int
    elapsed_ms: float


@dataclasses.dataclass(frozen=True)
class BudgetSnapshot:
    """Point-in-time budget headroom from the active hypothesis."""

    tokens_remaining: int
    steps_remaining: int
    tokens_budgeted: int
    steps_budgeted: int


def build_layout() -> Layout:
    """Build the 4-pane Layout per ux-spec §2.3 verbatim sketch."""
    layout = Layout()
    layout.split_column(
        Layout(name="hypothesis_stack", size=8),
        Layout(name="current_tool_call", size=6),
        Layout(name="footer", size=5),
    )
    layout["footer"].split_row(
        Layout(name="findings"),
        Layout(name="budget"),
        Layout(name="last_event"),
    )
    return layout


def render_hypothesis_stack(
    snap: StackSnapshot | None,
    flash_frame: int = 0,
) -> Panel:
    """Render the HYPOTHESIS STACK pane; yellow border for one tick after a pivot."""
    if snap is None:
        return Panel("[dim]awaiting first hypothesis…[/dim]", title="HYPOTHESIS STACK")

    rows: list[str] = []
    if snap.active:
        h = snap.active
        rows.append(f"[bold cyan]ACTIVE[/bold cyan]  [{h.id}]  {h.statement[:72]}")
        if h.assigned_specialist:
            rows.append(f"  specialist: [dim]{h.assigned_specialist}[/dim]")
    else:
        rows.append("[dim]no active hypothesis[/dim]")

    for h in snap.queued[:2]:
        rows.append(f"  [dim]QUEUED[/dim]  [{h.id}]  {h.statement[:60]}")
    if len(snap.queued) > 2:
        rows.append(f"  [dim]… {len(snap.queued) - 2} more queued[/dim]")

    formed = len(snap.history) + (1 if snap.active else 0)
    confirmed = sum(1 for h in snap.history if str(h.status).upper() == "CONFIRMED")
    rows.append(
        f"  formed={formed}  confirmed={confirmed}"
        f"  pivots={snap.total_pivot_count}  history={len(snap.history)}"
    )

    border_style = "yellow" if flash_frame > 0 else "blue"
    title = "HYPOTHESIS STACK" + (" [PIVOT]" if flash_frame > 0 else "")
    return Panel("\n".join(rows), title=title, border_style=border_style)


def render_current_tool_call(active_tool: ToolCallSnapshot | None) -> Panel:
    """Render the CURRENT TOOL CALL pane."""
    if active_tool is None:
        return Panel("[dim]idle[/dim]", title="CURRENT TOOL CALL")
    elapsed = (datetime.now(UTC) - active_tool.started_at).total_seconds()
    content = (
        f"[bold]{active_tool.tool_name}[/bold]  [dim]{elapsed:.1f}s elapsed[/dim]\n"
        f"[dim]{active_tool.args_summary[:100]}[/dim]"
    )
    return Panel(content, title="CURRENT TOOL CALL", border_style="green")


def render_findings_budget(
    findings: FindingsSnapshot | None,
    budget: BudgetSnapshot | None,
) -> tuple[Panel, Panel]:
    """Return (FINDINGS panel, BUDGET panel) for the footer row."""
    if findings is None:
        f_panel = Panel("[dim]—[/dim]", title="FINDINGS")
    else:
        f_panel = Panel(
            f"staged: [bold]{findings.findings_staged}[/bold]\n"
            f"tool calls: {findings.total_tool_calls}\n"
            f"elapsed: {findings.elapsed_ms / 1000:.0f}s",
            title="FINDINGS",
        )

    if budget is None:
        b_panel = Panel("[dim]—[/dim]", title="BUDGET")
    else:
        tokens_used = budget.tokens_budgeted - budget.tokens_remaining
        pct = int(100 * tokens_used / max(budget.tokens_budgeted, 1))
        steps_used = budget.steps_budgeted - budget.steps_remaining
        b_panel = Panel(
            f"tokens: [bold]{tokens_used:,}[/bold]/{budget.tokens_budgeted:,} ({pct}%)\n"
            f"steps: {steps_used}/{budget.steps_budgeted}",
            title="BUDGET",
            border_style="yellow" if pct > 80 else "default",
        )

    return f_panel, b_panel


def render_last_event(event: HypothesisEvent | None) -> Panel:
    """Render the LAST EVENT pane."""
    if event is None:
        return Panel("[dim]—[/dim]", title="LAST EVENT")

    color_map: dict[str, str] = {
        "form": "cyan",
        "dispatch": "blue",
        "confirm": "green",
        "pivot": "yellow",
        "abandon": "red",
    }
    color = color_map.get(str(event.type).lower(), "white")
    ts_str = event.ts.strftime("%H:%M:%S")
    content = (
        f"[bold {color}]{str(event.type).upper()}[/bold {color}]"
        f"  [{event.hypothesis_id}]  [dim]{ts_str}[/dim]"
    )
    if event.reason:
        content += f"\n[dim]{event.reason[:60]}[/dim]"
    return Panel(content, title="LAST EVENT")


def update_layout(
    layout: Layout,
    *,
    stack_snap: StackSnapshot | None,
    active_tool: ToolCallSnapshot | None,
    findings: FindingsSnapshot | None,
    budget: BudgetSnapshot | None,
    last_event: HypothesisEvent | None,
    flash_frame: int,
) -> None:
    """Refresh all five layout panes from the current display state."""
    layout["hypothesis_stack"].update(render_hypothesis_stack(stack_snap, flash_frame))
    layout["current_tool_call"].update(render_current_tool_call(active_tool))
    f_p, b_p = render_findings_budget(findings, budget)
    layout["findings"].update(f_p)
    layout["budget"].update(b_p)
    layout["last_event"].update(render_last_event(last_event))
