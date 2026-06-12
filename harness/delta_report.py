"""Delta report: Markdown + matplotlib PNG comparing baseline vs SilentWitness per dataset.

Reads the most recent baseline-*.json + silentwitness-*.json + scoring-*.json triple
from harness/results/<dataset>/ and renders:
  - delta.md: Markdown comparison table + hallucination callouts
  - delta.png: 4-panel bar chart (matplotlib Agg backend, CI-friendly)

Exit codes: 0 ok; 2 config/validation; 3 missing result file.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # CI-friendly; no display required
import matplotlib.pyplot as plt

from harness.delta_report_models import (
    METRIC_DIRECTIONS,
    DeltaReport,
    DeltaRow,
    Direction,
    HallucinationCallout,
)


def _write_atomic(path: Path, data: bytes) -> None:
    """Atomic-rename write: tmp file in same dir, fsync, replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        Path(tmp).replace(path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError as cleanup_exc:
            print(f"warning: tmp cleanup failed: {cleanup_exc}", file=sys.stderr)
        raise


def _interpret(metric: str, baseline: float | None, sw: float | None, direction: Direction) -> str:
    if baseline is None or sw is None:
        return f"{metric}: insufficient data (baseline or silentwitness side missing)"
    delta = sw - baseline
    sign = "+" if delta >= 0 else ""
    return f"SilentWitness {metric} {sign}{delta:.3f} vs baseline ({direction.replace('_', ' ')})"


def _safe_delta(baseline: float | None, sw: float | None) -> float | None:
    if baseline is None or sw is None:
        return None
    return sw - baseline


def compute_delta_rows(
    baseline_metrics: dict[str, Any], silentwitness_metrics: dict[str, Any]
) -> list[DeltaRow]:
    """Emit one DeltaRow per metric, pulling values directly from the metrics dicts."""
    rows: list[DeltaRow] = []
    for metric, direction in METRIC_DIRECTIONS.items():
        b = baseline_metrics.get(metric)
        s = silentwitness_metrics.get(metric)
        b_val = float(b) if isinstance(b, (int, float)) else None
        s_val = float(s) if isinstance(s, (int, float)) else None
        rows.append(
            DeltaRow(
                metric=metric,
                baseline_value=b_val,
                silentwitness_value=s_val,
                delta=_safe_delta(b_val, s_val),
                direction=direction,
                interpretation=_interpret(metric, b_val, s_val, direction),
            )
        )
    return rows


def _fmt(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.3f}"


def _fmt_delta(v: float | None) -> str:
    if v is None:
        return "n/a"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.3f}"


def _row_md(row: DeltaRow) -> str:
    direction_label = row.direction.replace("_", " ")
    return (
        f"| {row.metric} | {_fmt(row.baseline_value)} | "
        f"{_fmt(row.silentwitness_value)} | {_fmt_delta(row.delta)} | {direction_label} |"
    )


def render_markdown(report: DeltaReport) -> str:
    """Render the canonical Markdown delta-report shape."""
    lines = [
        f"# Δ vs vanilla Protocol SIFT baseline — {report.dataset_id}",
        "",
        "## Headline (PRD §4)",
        "| Metric | Baseline | SilentWitness | Δ | Direction |",
        "|---|---|---|---|---|",
    ]
    lines.extend(_row_md(r) for r in report.rows)
    lines += [
        "",
        "## Baseline hallucinated; SilentWitness refused",
        "The architectural floor in action — these are claims the baseline emitted",
        "against artifacts that do not exist on the mounted evidence, verifiable",
        "by re-running the cited shell command:",
    ]
    if report.baseline_hallucinated_callouts:
        for c in report.baseline_hallucinated_callouts[:10]:
            argv_str = " ".join(c.evidence_shellout_argv)
            lines.append(
                f"- `{c.cited_artifact_path}` — `{argv_str}` → {c.evidence_shellout_hits} hits"
            )
    else:
        lines.append("- (no baseline hallucinations on this dataset)")
    refused = len(report.silentwitness_refused_callouts)
    refused_line = (
        "SilentWitness rejected the equivalent class of claims at the entity gate "
        f"(count = {refused})."
    )
    lines += [
        "",
        refused_line,
        "",
        "## Footnotes",
        f"- Run anchor: {report.baseline_result_path.name}, "
        f"{report.silentwitness_result_path.name}, {report.scoring_result_path.name}",
        "- Methodology: harness/scorer.py classification tree; see PRD §6 for definitions.",
        f"- Generated at: {report.generated_at.isoformat()}",
    ]
    return "\n".join(lines) + "\n"


def _bar_pair(ax: Any, title: str, labels: list[str], values: list[float], ylabel: str) -> None:
    colors = ["#888888", "#1a73e8"]
    ax.bar(labels, values, color=colors)
    ax.set_title(title, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.tick_params(axis="x", labelsize=9)
    ax.tick_params(axis="y", labelsize=8)


def _val(row: DeltaRow, side: str) -> float:
    v = row.baseline_value if side == "baseline" else row.silentwitness_value
    return v if v is not None else 0.0


def _row_by_metric(rows: list[DeltaRow]) -> dict[str, DeltaRow]:
    return {r.metric: r for r in rows}


def render_bar_chart_png(report: DeltaReport, out_path: Path) -> None:
    """Render a 4-panel grouped bar chart and save to out_path (atomic write)."""
    by_metric = _row_by_metric(report.rows)
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), dpi=120)
    fig.suptitle(
        f"SilentWitness vs vanilla Protocol SIFT — {report.dataset_id}",
        fontsize=12,
        fontweight="bold",
    )

    sides = ["baseline", "silentwitness"]

    handoff = by_metric.get("time_to_handoff_ready_report_seconds")
    if handoff:
        _bar_pair(
            axes[0][0],
            "time-to-handoff-ready-report (lower is better)",
            sides,
            [_val(handoff, s) for s in sides],
            "seconds",
        )

    halrate = by_metric.get("hallucination_rate")
    if halrate:
        _bar_pair(
            axes[0][1],
            "hallucination_rate (lower is better)",
            sides,
            [_val(halrate, s) for s in sides],
            "rate (0..1)",
        )

    precision = by_metric.get("precision")
    recall = by_metric.get("recall")
    if precision and recall:
        import numpy as np

        x = np.arange(2)
        width = 0.35
        axes[1][0].bar(
            x - width / 2,
            [_val(precision, "baseline"), _val(recall, "baseline")],
            width,
            label="baseline",
            color="#888888",
        )
        axes[1][0].bar(
            x + width / 2,
            [_val(precision, "silentwitness"), _val(recall, "silentwitness")],
            width,
            label="silentwitness",
            color="#1a73e8",
        )
        axes[1][0].set_xticks(x)
        axes[1][0].set_xticklabels(["precision", "recall"])
        axes[1][0].set_title("precision + recall (higher is better)", fontsize=10)
        axes[1][0].legend(fontsize=8)

    honesty = by_metric.get("epistemic_honesty_count")
    if honesty:
        _bar_pair(
            axes[1][1],
            "epistemic-honesty count (higher is better)",
            sides,
            [_val(honesty, s) for s in sides],
            "count",
        )

    plt.tight_layout()
    import io as _io

    buf = _io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    _write_atomic(out_path, buf.getvalue())


def _latest_match(results_dir: Path, prefix: str) -> Path | None:
    """Return the lexicographically-largest filename match (ISO timestamps sort lexically)."""
    matches = sorted(results_dir.glob(f"{prefix}-*.json"))
    return matches[-1] if matches else None


def _extract_metrics(result: dict[str, Any], side: str) -> dict[str, Any]:
    """Pull metrics from either a baseline/silentwitness runner result OR the scoring report."""
    metrics = dict(result.get(side, {}))
    for k in (
        "time_to_first_finding_seconds",
        "time_to_handoff_ready_report_seconds",
        "pivot_count",
        "epistemic_honesty_count",
    ):
        if k not in metrics:
            metrics[k] = result.get(k)
    return metrics


def build_delta_report(dataset_id: str, results_dir: Path) -> DeltaReport:
    """Locate latest result triple under results_dir/dataset_id/, build DeltaReport."""
    case_dir = results_dir / dataset_id
    baseline_path = _latest_match(case_dir, "baseline")
    sw_path = _latest_match(case_dir, "silentwitness")
    scoring_path = _latest_match(case_dir, "scoring")
    if baseline_path is None:
        raise FileNotFoundError(f"no baseline result found in {case_dir}")
    if sw_path is None:
        raise FileNotFoundError(f"no silentwitness result found in {case_dir}")
    if scoring_path is None:
        raise FileNotFoundError(f"no scoring result found in {case_dir}")

    baseline_result = json.loads(baseline_path.read_text())
    sw_result = json.loads(sw_path.read_text())
    scoring_result = json.loads(scoring_path.read_text())

    b_metrics = _extract_metrics(scoring_result, "baseline")
    s_metrics = _extract_metrics(scoring_result, "silentwitness")
    # Inject pivot/epistemic_honesty from runner results when not in scoring
    s_metrics.setdefault("pivot_count", len(sw_result.get("pivots", [])))
    s_metrics.setdefault("epistemic_honesty_count", sw_result.get("epistemic_honesty_count", 0))
    b_metrics.setdefault("pivot_count", 0)
    b_metrics.setdefault("epistemic_honesty_count", 0)
    # Pass-through timing fields from runner results if scoring doesn't carry them
    for k in ("time_to_first_finding_seconds", "time_to_handoff_ready_report_seconds"):
        if b_metrics.get(k) is None:
            b_metrics[k] = baseline_result.get(k)
        if s_metrics.get(k) is None:
            s_metrics[k] = sw_result.get(k)

    rows = compute_delta_rows(b_metrics, s_metrics)

    callouts_raw = scoring_result.get("hallucination_examples", [])
    b_callouts: list[HallucinationCallout] = []
    s_callouts: list[HallucinationCallout] = []
    for ex in callouts_raw[:20]:
        if not isinstance(ex, dict) or "side" not in ex:
            continue
        try:
            c = HallucinationCallout(
                **{
                    k: ex[k]
                    for k in (
                        "side",
                        "cited_artifact_path",
                        "excerpt",
                        "evidence_shellout_argv",
                        "evidence_shellout_hits",
                    )
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
        if c.side == "baseline":
            b_callouts.append(c)
        else:
            s_callouts.append(c)

    refused = sw_result.get("entity_gate_rejections", 0)
    # Use a placeholder list with the rejection count surfacing as a footnote-equivalent.
    if refused and not s_callouts:
        s_callouts = []

    return DeltaReport(
        dataset_id=dataset_id,
        baseline_result_path=baseline_path,
        silentwitness_result_path=sw_path,
        scoring_result_path=scoring_path,
        generated_at=datetime.now(UTC),
        rows=rows,
        baseline_hallucinated_callouts=b_callouts[:10],
        silentwitness_refused_callouts=s_callouts[:10],
    )


def write_delta_artifacts(report: DeltaReport, results_dir: Path) -> tuple[Path, Path]:
    case_dir = results_dir / report.dataset_id
    case_dir.mkdir(parents=True, exist_ok=True)
    md_path = case_dir / "delta.md"
    png_path = case_dir / "delta.png"
    _write_atomic(md_path, (render_markdown(report)).encode("utf-8"))
    render_bar_chart_png(report, png_path)
    return md_path, png_path


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Render delta report (Markdown + PNG).")
    parser.add_argument("--dataset", required=True)
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "results",
    )
    parser.add_argument("--out-md", type=Path, default=None)
    parser.add_argument("--out-png", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        report = build_delta_report(args.dataset, args.results_dir)
    except FileNotFoundError as exc:
        print(f"missing input: {exc}", file=sys.stderr)
        return 3
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"config/validation error: {exc}", file=sys.stderr)
        return 2

    if args.out_md or args.out_png:
        md_path = args.out_md or (args.results_dir / args.dataset / "delta.md")
        png_path = args.out_png or (args.results_dir / args.dataset / "delta.png")
        md_path.parent.mkdir(parents=True, exist_ok=True)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        _write_atomic(md_path, (render_markdown(report)).encode("utf-8"))
        render_bar_chart_png(report, png_path)
    else:
        md_path, png_path = write_delta_artifacts(report, args.results_dir)

    print(f"wrote {md_path} and {png_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
