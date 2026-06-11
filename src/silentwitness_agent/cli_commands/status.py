"""Read-only case status snapshot — safe during active investigate runs."""

from __future__ import annotations

import json
import signal
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

_PIVOT_GLYPH = "⤷"  # ⤳
_STATUS_APPROVED = "APPROVED"
_DEFAULT_TOKEN_BUDGET = 800_000
_DEFAULT_STEP_BUDGET = 200
_HYP_TYPE_MAP = {
    "form": "ACTIVE",
    "dispatch": "ACTIVE",
    "confirm": "CONFIRMED",
    "pivot": "PIVOTED",
    "abandon": "ABANDONED",
}


def _humanize(n: int) -> str:
    if n >= 1_000_000:
        return f"{n // 1_000_000}M"
    if n >= 1_000:
        return f"{n // 1_000}k"
    return str(n)


def _elapsed_fmt(s: float) -> str:
    s = int(s)
    return f"{s // 3600}h {(s % 3600) // 60:02d}m" if s >= 3600 else f"{s // 60}m {s % 60:02d}s"


def _read_jsonl(path: Path, strict: bool = False) -> tuple[list[dict[str, Any]], list[int]]:
    """Parse a JSONL file; bad_lines non-empty only when strict=True."""
    events: list[dict[str, Any]] = []
    bad: list[int] = []
    if not path.is_file():
        return events, bad
    for lineno, raw in enumerate(path.open("r", encoding="utf-8", errors="replace"), 1):
        line = raw.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            if strict:
                bad.append(lineno)
    return events, bad


def _findings(case_dir: Path) -> tuple[int, int, int]:
    staged = approved = rejected = 0
    p = case_dir / "findings.json"
    if p.is_file():
        try:
            for item in json.loads(p.read_text(encoding="utf-8")):
                if isinstance(item, dict):
                    approved += item.get("status") == _STATUS_APPROVED
                    staged += item.get("status") != _STATUS_APPROVED
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    rows, _ = _read_jsonl(case_dir / "audit" / "findings.jsonl")
    for ev in rows:
        rs = ev.get("result_summary") or {}
        if isinstance(rs, dict) and rs.get("success") is False:
            rejected += 1
    return staged, approved, rejected


def _case_status(events: list[dict[str, Any]]) -> str:
    if not events:
        return "IDLE"
    for ev in reversed(events):
        if ev.get("type") == "finish" or ev.get("event") == "on_finish":
            return "COMPLETED"
        if ev.get("event") == "sigint_checkpoint":
            return "ABORTED"
    return "INVESTIGATING"


def _tokens_steps(events: list[dict[str, Any]]) -> tuple[int, int]:
    steps = sum(1 for e in events if e.get("type") == "step")
    for ev in reversed(events):
        if ev.get("type") == "finish" and "total_tokens_consumed" in ev:
            return int(ev["total_tokens_consumed"]), steps
    tokens = sum(
        (e.get("input_tokens") or 0) + (e.get("output_tokens") or 0)
        for e in events
        if e.get("type") == "step"
    )
    return tokens, steps


def _elapsed(events: list[dict[str, Any]], status: str) -> float:
    if not events:
        return 0.0
    try:
        t0 = datetime.fromisoformat(events[0]["ts"])
        t1_str = events[-1].get("ts", "")
        t1 = datetime.fromisoformat(t1_str) if t1_str else datetime.now(UTC)
        if status == "INVESTIGATING":
            t1 = datetime.now(UTC)
        return max(0.0, (t1 - t0).total_seconds())
    except (KeyError, ValueError):
        return 0.0


def _hyp_rows(snap: dict[str, Any]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for h in ([snap.get("active")] if snap.get("active") else []) + list(snap.get("queued") or []):
        if isinstance(h, dict):
            rows.append((h.get("id", "?"), "ACTIVE", h.get("statement", "")))
    for h in snap.get("history") or []:
        if isinstance(h, dict):
            rows.append(
                (h.get("id", "?"), str(h.get("status", "")).upper(), h.get("statement", ""))
            )
    return rows


def _hyp_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    last: dict[str, str] = {}
    for ev in events:
        hid = ev.get("hypothesis_id")
        t = str(ev.get("type", "")).lower()
        if hid and t in _HYP_TYPE_MAP:
            last[hid] = _HYP_TYPE_MAP[t]
    out = {"ACTIVE": 0, "CONFIRMED": 0, "PIVOTED": 0, "ABANDONED": 0}
    for s in last.values():
        out[s] = out.get(s, 0) + 1
    return out


def _last_pivot(events: list[dict[str, Any]]) -> str | None:
    for ev in reversed(events):
        if str(ev.get("type", "")).lower() == "pivot":
            try:
                ts = datetime.fromisoformat(ev["ts"]).strftime("%H:%M:%SZ")
            except (KeyError, ValueError):
                ts = ev.get("ts", "?")
            hid = ev.get("hypothesis_id", "?")
            reason = (ev.get("reason") or "")[:60]
            return f"{ts}  {hid}  {reason}" if reason else f"{ts}  {hid}"
    return None


def _examiner(case_dir: Path) -> str:
    p = case_dir / ".silentwitness" / "case.toml"
    if not p.is_file():
        return "examiner"
    try:
        with p.open("rb") as fh:
            return str(tomllib.load(fh).get("examiner", "examiner"))
    except Exception:
        return "examiner"


def _render_once(
    case_dir: Path, case_id: str, *, json_out: bool, full: bool, no_color: bool
) -> int:
    err = Console(stderr=True, no_color=no_color)
    out = Console(no_color=no_color)

    agent_evts, _ = _read_jsonl(case_dir / "audit" / "agent.jsonl")
    hyp_evts, bad = _read_jsonl(case_dir / "audit" / "hypothesis.jsonl", strict=True)
    if bad:
        err.print(f"[red]✗[/red] hypothesis.jsonl parse error at line {bad[0]}", highlight=False)
        return 2

    staged, approved, rejected = _findings(case_dir)
    status = _case_status(agent_evts)
    tokens_consumed, steps_consumed = _tokens_steps(agent_evts)
    elapsed_s = _elapsed(agent_evts, status)
    examiner = _examiner(case_dir)
    model = next(
        (ev["model_used"] for ev in reversed(agent_evts) if ev.get("model_used")), "unknown"
    )
    snap = next(
        (ev["stack_snapshot"] for ev in reversed(agent_evts) if "stack_snapshot" in ev), None
    )
    rows = _hyp_rows(snap) if snap else []
    _skeys = ("ACTIVE", "CONFIRMED", "PIVOTED", "ABANDONED")
    counts = (
        {s: sum(1 for _, st, _ in rows if st == s) for s in _skeys}
        if rows
        else _hyp_counts(hyp_evts)
    )
    pivot = _last_pivot(hyp_evts)

    if json_out:
        payload = {
            "case_id": case_id,
            "examiner": examiner,
            "elapsed_seconds": int(elapsed_s),
            "status": status,
            "hypotheses": {
                **{
                    k.lower(): [{"id": r[0], "statement": r[2]} for r in rows if r[1] == k]
                    for k in ("ACTIVE", "CONFIRMED", "PIVOTED", "ABANDONED")
                },
                "counts": counts,
            },
            "findings": {"draft": staged, "approved": approved, "rejected": rejected},
            "budget": {
                "tokens_consumed": tokens_consumed,
                "tokens_budget": _DEFAULT_TOKEN_BUDGET,
                "steps_consumed": steps_consumed,
                "steps_budget": _DEFAULT_STEP_BUDGET,
            },
            "last_event": {"pivot_line": pivot},
        }
        # Use print() directly so Rich never word-wraps machine-readable JSON.
        print(json.dumps(payload))
        return 0

    elapsed_str = _elapsed_fmt(elapsed_s) if elapsed_s > 0 else "0m 00s"
    out.print(
        f"case:        {case_id:<20}  model:   {model}\n"
        f"examiner:    {examiner:<20}  status:  {status} ({elapsed_str} elapsed)",
        highlight=False,
    )
    out.print()
    n_a, n_c = counts["ACTIVE"], counts["CONFIRMED"]
    n_p, n_ab = counts["PIVOTED"], counts["ABANDONED"]
    out.print(
        f"hypothesis stack ({n_a} active, {n_c} confirmed, {n_p} pivoted, {n_ab} abandoned):",
        highlight=False,
    )
    if rows:
        tbl = Table(show_header=False, box=None, padding=(0, 1))
        tbl.add_column("id", style="cyan", no_wrap=True)
        tbl.add_column("status", no_wrap=True)
        tbl.add_column("statement")
        show = set(
            ("ACTIVE", "CONFIRMED", "PIVOTED")
            if not full
            else ("ACTIVE", "CONFIRMED", "PIVOTED", "ABANDONED")
        )
        for hid, st, stmt in rows:
            if st not in show:
                continue
            label = f"[{st}]"
            out_stmt = (f"{_PIVOT_GLYPH} {stmt}" if st == "PIVOTED" else stmt) or "[in progress]"
            tbl.add_row(hid, label, out_stmt[:80])
        out.print(tbl)
        if full:
            ab_rows = [(hid, st, stmt) for hid, st, stmt in rows if st == "ABANDONED"]
            if ab_rows:
                out.print("[bold]ABANDONED[/bold]")
                tbl2 = Table(show_header=False, box=None, padding=(0, 1))
                for _ in range(3):
                    tbl2.add_column()
                for hid, _, stmt in ab_rows:
                    tbl2.add_row(hid, "[ABANDONED]", stmt[:80] or "[in progress]")
                out.print(tbl2)
    elif n_a + n_c + n_p + n_ab == 0:
        out.print("  [dim]no hypotheses yet[/dim]")
    else:
        out.print("  [dim]snapshot unavailable (run in progress)[/dim]")

    out.print()
    out.print(
        f"findings: staged {staged}  approved {approved}  rejected {rejected}", highlight=False
    )
    out.print(
        f"tokens:   {_humanize(tokens_consumed)} / {_humanize(_DEFAULT_TOKEN_BUDGET)} budget",
        highlight=False,
    )
    if pivot:
        out.print(f"last pivot: {pivot}", highlight=False)
    return 0


def render(
    case_dir: Path, case_id: str, *, json_out: bool, watch: bool, full: bool, no_color: bool
) -> int:
    """Entry point from cli.py."""
    if not watch:
        return _render_once(case_dir, case_id, json_out=json_out, full=full, no_color=no_color)

    _done = [False]

    def _sigint(sig: int, frame: Any) -> None:
        _done[0] = True

    signal.signal(signal.SIGINT, _sigint)
    try:
        while not _done[0]:
            Console(no_color=no_color).print("\x1b[2J\x1b[H", end="", highlight=False)
            _render_once(case_dir, case_id, json_out=json_out, full=full, no_color=no_color)
            deadline = time.monotonic() + 2.0
            while not _done[0] and time.monotonic() < deadline:
                time.sleep(0.1)
    finally:
        signal.signal(signal.SIGINT, signal.SIG_DFL)
    return 130
