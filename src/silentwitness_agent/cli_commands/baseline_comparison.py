"""silentwitness baseline-comparison <case-id> — compose scorer + delta into rich.table + JSON.

Reads existing baseline-*.json + silentwitness-*.json result triples from the case's
results dir (typically harness/results/<dataset>/), computes Δ via harness.scorer +
harness.delta_report, writes baseline-delta.json, and renders a colored rich.table.

Exit codes: 0 ok; 1 case not found; 2 setup error (missing GT, missing Epic 14, bad input).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, cast

from rich.console import Console
from rich.table import Table

from silentwitness_common.atomic_io import write_bytes_atomic

_DATASET_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

_ALL_METRICS = (
    "time_to_handoff_seconds_delta",
    "pivots_count_delta",
    "hallucination_rate_delta",
    "precision_delta",
    "recall_delta",
    "epistemic_honesty_count_delta",
)
_METRIC_ALIASES = {
    "time": "time_to_handoff_seconds_delta",
    "pivots": "pivots_count_delta",
    "hallucinations": "hallucination_rate_delta",
    "provenance": "precision_delta",
    "recall": "recall_delta",
    "epistemic": "epistemic_honesty_count_delta",
}
# Lower-is-better metrics (regression direction = increase)
_LOWER_BETTER = frozenset({"time_to_handoff_seconds_delta", "hallucination_rate_delta"})


def _check_epic14_importable() -> str | None:
    """Return None if Epic 14 modules are importable; else a human-readable hint."""
    try:
        import harness.delta_report
        import harness.scorer  # noqa: F401
    except ImportError as exc:
        return f"baseline-runner not installed; Epic 14 required ({exc})"
    return None


def _resolve_dataset_id(case_dir: Path, notes: list[str]) -> str:
    """Read case manifest; surface parse failures via notes; fall back to case_dir.name."""
    manifest = case_dir / "case.toml"
    if manifest.exists():
        try:
            import tomllib

            data = tomllib.loads(manifest.read_text())
            ds = data.get("dataset_id") or data.get("case", {}).get("dataset_id")
            if isinstance(ds, str) and ds:
                return ds
            notes.append(f"warning: case.toml missing dataset_id; falling back to {case_dir.name}")
        except (OSError, tomllib.TOMLDecodeError, KeyError) as exc:
            notes.append(f"warning: case.toml unreadable ({exc}); falling back to {case_dir.name}")
    return case_dir.name


def _gt_root() -> Path:
    """Ground-truth root dir (env-injectable for tests)."""
    env_root = os.environ.get("SILENTWITNESS_GT_DIR")
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[3] / "harness" / "ground_truth"


def _gt_path(dataset_id: str) -> Path:
    return _gt_root() / f"{dataset_id}.json"


def _latest(case_results: Path, prefix: str) -> Path | None:
    matches = sorted(case_results.glob(f"{prefix}-*.json"))
    return matches[-1] if matches else None


def _safe_delta(b: float | None, s: float | None) -> float | None:
    return None if b is None or s is None else s - b


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level must be a JSON object, got {type(data).__name__}")
    return cast(dict[str, Any], data)


def _coalesce(*values: float | None) -> float | None:
    """Return first value that is not None (preserves 0.0 unlike `a or b`)."""
    for v in values:
        if v is not None:
            return v
    return None


def _compute_delta_dict(
    baseline_path: Path, silentwitness_path: Path, scoring_path: Path | None
) -> dict[str, float | None]:
    """Return the full delta dict — populated from runner JSONs + scoring report if present."""
    baseline = _load_json(baseline_path)
    sw = _load_json(silentwitness_path)
    scoring = _load_json(scoring_path) if scoring_path else {}

    b_metrics: dict[str, Any] = dict(scoring.get("baseline") or {})
    s_metrics: dict[str, Any] = dict(scoring.get("silentwitness") or {})
    # Use explicit-None coalesce — `or` would treat legitimate 0.0 as missing
    b_t = _coalesce(
        b_metrics.get("time_to_handoff_ready_report_seconds"),
        baseline.get("time_to_handoff_ready_report_seconds"),
    )
    s_t = _coalesce(
        s_metrics.get("time_to_handoff_ready_report_seconds"),
        sw.get("time_to_handoff_ready_report_seconds"),
    )

    b_pivots = baseline.get("pivots_count", 0)
    s_pivots = len(sw.get("pivots", []) or [])
    b_honesty = baseline.get("epistemic_honesty_count", 0)
    s_honesty = sw.get("epistemic_honesty_count", 0)

    return {
        "time_to_handoff_seconds_delta": _safe_delta(b_t, s_t),
        "pivots_count_delta": _safe_delta(b_pivots, s_pivots),
        "hallucination_rate_delta": _safe_delta(
            b_metrics.get("hallucination_rate"), s_metrics.get("hallucination_rate")
        ),
        "precision_delta": _safe_delta(b_metrics.get("precision"), s_metrics.get("precision")),
        "recall_delta": _safe_delta(b_metrics.get("recall"), s_metrics.get("recall")),
        "epistemic_honesty_count_delta": _safe_delta(b_honesty, s_honesty),
    }


def _fmt_value(metric: str, value: float | None) -> str:
    if value is None:
        return "n/a"
    sign = "+" if value >= 0 else ""
    suffix = "s" if metric == "time_to_handoff_seconds_delta" else ""
    return f"{sign}{value:.3f}{suffix}"


def _color_for(metric: str, value: float | None) -> str:
    """Improvement → green, regression → yellow, neutral/none → default."""
    if value is None or value == 0:
        return "white"
    lower_is_better = metric in _LOWER_BETTER
    improved = (value < 0) if lower_is_better else (value > 0)
    return "green" if improved else "yellow"


def _arrow_for(metric: str, value: float | None) -> str:
    if value is None or value == 0:
        return ""
    return "↓" if value < 0 else "↑"


def _resolve_metric_filter(metrics_arg: str, *, notes: list[str] | None = None) -> tuple[str, ...]:
    """Parse --metrics comma-list; note unknown aliases instead of silently falling back."""
    if not metrics_arg or metrics_arg.lower() == "all":
        return _ALL_METRICS
    requested: list[str] = []
    unknown: list[str] = []
    for raw in metrics_arg.split(","):
        key = raw.strip().lower()
        if not key:
            continue
        canonical = _METRIC_ALIASES.get(key, key)
        if canonical in _ALL_METRICS:
            requested.append(canonical)
        else:
            unknown.append(key)
    if unknown and notes is not None:
        notes.append(f"warning: unknown --metrics aliases ignored: {unknown}")
    return tuple(requested) if requested else _ALL_METRICS


def _render_table(
    case_id: str, delta: dict[str, float | None], shown: tuple[str, ...], console: Console
) -> None:
    table = Table(title=f"Δ measured against Protocol SIFT baseline — {case_id}")
    table.add_column("Metric", style="bold")
    table.add_column("Δ", justify="right")
    table.add_column("Direction")
    for metric in shown:
        value = delta.get(metric)
        color = _color_for(metric, value)
        arrow = _arrow_for(metric, value)
        cell = f"[{color}]{arrow} {_fmt_value(metric, value)}[/{color}]"
        direction = "lower is better" if metric in _LOWER_BETTER else "higher is better"
        table.add_row(metric, cell, direction)
    console.print(table)
    console.print("Δ measured against Protocol SIFT baseline.")


def run(
    case_dir: Path,
    case_id: str,
    *,
    baseline_mode: str = "protocol-sift",
    out: Path | None = None,
    no_color: bool = False,
    results_dir: Path | None = None,
    metrics_arg: str = "time,pivots,provenance,hallucinations,epistemic",
) -> int:
    err = Console(stderr=True, no_color=no_color)
    out_console = Console(no_color=no_color)
    notes: list[str] = []

    if not case_dir.exists():
        err.print(f"[red]✗[/red] case '{case_id}' not found", highlight=False)
        return 1

    hint = _check_epic14_importable()
    if hint:
        err.print(f"[red]✗[/red] {hint}", highlight=False)
        return 2

    dataset_id = _resolve_dataset_id(case_dir, notes)
    if not _DATASET_ID_RE.match(dataset_id):
        err.print(
            f"[red]✗[/red] dataset_id {dataset_id!r} fails validation ({_DATASET_ID_RE.pattern})",
            highlight=False,
        )
        return 2
    gt_path = _gt_path(dataset_id)
    if not gt_path.exists():
        err.print(
            "[red]✗[/red] GROUND_TRUTH_MISSING — add ground truth at "
            f"harness/ground_truth/<case_id>.json (looked at {gt_path})",
            highlight=False,
        )
        return 2

    primary_results = results_dir or (case_dir / "results")
    fallback_results = Path("harness") / "results" / dataset_id
    case_results = primary_results if primary_results.exists() else fallback_results
    if not primary_results.exists():
        notes.append(f"results dir {primary_results} missing; using {fallback_results}")

    baseline_path = _latest(case_results, "baseline")
    sw_path = _latest(case_results, "silentwitness")
    scoring_path = _latest(case_results, "scoring")
    if baseline_path is None or sw_path is None:
        err.print(
            f"[red]✗[/red] no baseline or silentwitness result JSON in {case_results}",
            highlight=False,
        )
        return 2

    try:
        delta = _compute_delta_dict(baseline_path, sw_path, scoring_path)
    except ValueError as exc:
        err.print(f"[red]✗[/red] malformed runner result: {exc}", highlight=False)
        return 2

    payload = {
        "case_id": case_id,
        "dataset_id": dataset_id,
        "baseline_mode": baseline_mode,
        "baseline_result_path": str(baseline_path),
        "silentwitness_result_path": str(sw_path),
        "scoring_result_path": str(scoring_path) if scoring_path else None,
        **delta,
    }
    out_path = out if out is not None else case_dir / "baseline-delta.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_bytes_atomic(out_path, json.dumps(payload, indent=2).encode("utf-8"))

    shown = _resolve_metric_filter(metrics_arg, notes=notes)
    _render_table(case_id, delta, shown, out_console)
    for n in notes:
        print(n, file=sys.stderr)
    err.print(f"wrote {out_path}", highlight=False)
    return 0
