"""Integration tests for silentwitness baseline-comparison."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from silentwitness_agent.cli import app

_FIXTURE_RESULTS = Path(__file__).resolve().parents[1] / "fixtures" / "baseline-comparison-results"
_GT_NAME = "nitroba"


def _prep_case(tmp_path: Path, *, register_gt: bool = True) -> tuple[Path, Path]:
    """Set up cases/<case_id> + harness/ground_truth/<id>.json in a tmp tree."""
    cases_root = tmp_path / "cases-root"
    case_dir = cases_root / "cases" / _GT_NAME
    case_dir.mkdir(parents=True)
    (case_dir / "case.toml").write_text(
        f'[case]\ncase_id = "{_GT_NAME}"\ndataset_id = "{_GT_NAME}"\n'
    )
    results = case_dir / "results"
    results.mkdir()
    for src in _FIXTURE_RESULTS.glob("*.json"):
        shutil.copy(src, results / src.name)
    if register_gt:
        gt_dir = Path("harness") / "ground_truth"
        gt_path = gt_dir / f"{_GT_NAME}.json"
        if not gt_path.exists():
            # ground_truth/nitroba.handcrafted.json exists, but we want nitroba.json
            # for the CLI's literal lookup. Use a sentinel file the test cleans up.
            gt_path.write_text("[]")
    return cases_root, case_dir


@pytest.fixture
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cases_root, _ = _prep_case(tmp_path)
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(cases_root))
    return cases_root


@pytest.fixture(autouse=True)
def _cleanup_gt() -> object:
    gt = Path("harness") / "ground_truth" / f"{_GT_NAME}.json"
    yield
    if gt.exists() and gt.read_text() == "[]":
        gt.unlink()


class TestBaselineComparison:
    def test_happy_path_writes_delta_json_and_table(self, cli_env: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(app, ["baseline-comparison", _GT_NAME])
        assert result.exit_code == 0, result.output
        delta_path = cli_env / "cases" / _GT_NAME / "baseline-delta.json"
        assert delta_path.exists()
        data = json.loads(delta_path.read_text())
        for key in (
            "time_to_handoff_seconds_delta",
            "pivots_count_delta",
            "hallucination_rate_delta",
            "precision_delta",
            "recall_delta",
            "epistemic_honesty_count_delta",
        ):
            assert key in data
        assert "Δ measured against Protocol SIFT baseline" in result.output

    def test_metrics_filter_restricts_table_rows(self, cli_env: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            app, ["baseline-comparison", _GT_NAME, "--metrics", "time,hallucinations"]
        )
        assert result.exit_code == 0
        # JSON still contains all metrics (filter is display-only)
        delta = json.loads((cli_env / "cases" / _GT_NAME / "baseline-delta.json").read_text())
        assert len(delta) > 6  # case_id + dataset_id + paths + 6 metrics
        # Output shows the filtered metric names but NOT the un-shown ones
        assert "time_to_handoff_seconds_delta" in result.output
        assert "hallucination_rate_delta" in result.output
        assert "recall_delta" not in result.output

    def test_baseline_vanilla_mode_recorded(self, cli_env: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(app, ["baseline-comparison", _GT_NAME, "--baseline", "vanilla"])
        assert result.exit_code == 0
        data = json.loads((cli_env / "cases" / _GT_NAME / "baseline-delta.json").read_text())
        assert data["baseline_mode"] == "vanilla"

    def test_out_flag_redirects_path(self, cli_env: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        custom = tmp_path / "custom-delta.json"
        result = runner.invoke(app, ["baseline-comparison", _GT_NAME, "--out", str(custom)])
        assert result.exit_code == 0
        assert custom.exists()
        default = cli_env / "cases" / _GT_NAME / "baseline-delta.json"
        assert not default.exists()

    def test_missing_ground_truth_exits_2(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cases_root, _ = _prep_case(tmp_path, register_gt=False)
        monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(cases_root))
        gt = Path("harness") / "ground_truth" / f"{_GT_NAME}.json"
        if gt.exists():
            gt.unlink()
        runner = CliRunner()
        result = runner.invoke(app, ["baseline-comparison", _GT_NAME])
        assert result.exit_code == 2
        assert "GROUND_TRUTH_MISSING" in result.output

    def test_case_not_found_exits_1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(app, ["baseline-comparison", "no-such-case"])
        assert result.exit_code == 1
        assert "case 'no-such-case' not found" in result.output

    def test_table_renders_improvement_in_green(self, cli_env: Path) -> None:
        """Fixture: SW hallucination_rate=0.0, baseline=0.4 → -0.4 (improvement)."""
        runner = CliRunner()
        result = runner.invoke(app, ["baseline-comparison", _GT_NAME])
        assert result.exit_code == 0
        # hallucination_rate row shows negative delta (lower-is-better → green improvement)
        assert "-0.400" in result.output

    def test_table_renders_regression_in_yellow(self, cli_env: Path) -> None:
        """Fixture: time_to_handoff baseline=610, sw=250 → -360 (improvement actually).

        Force a regression: rewrite fixtures so SW is slower than baseline.
        """
        results = cli_env / "cases" / _GT_NAME / "results"
        for f in results.glob("silentwitness-*.json"):
            data = json.loads(f.read_text())
            data["time_to_handoff_ready_report_seconds"] = 999.0
            f.write_text(json.dumps(data))
        # Scoring file's silentwitness section also overrides time
        for f in results.glob("scoring-*.json"):
            data = json.loads(f.read_text())
            data["silentwitness"]["time_to_handoff_ready_report_seconds"] = 999.0
            f.write_text(json.dumps(data))

        runner = CliRunner()
        result = runner.invoke(app, ["baseline-comparison", _GT_NAME])
        assert result.exit_code == 0
        # positive seconds delta = regression
        assert "+389" in result.output or "+389.000" in result.output

    def test_epic14_missing_exits_2(self, cli_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import sys

        # Drop the cached harness.scorer + delta_report and block re-import
        monkeypatch.delitem(sys.modules, "harness.scorer", raising=False)
        monkeypatch.delitem(sys.modules, "harness.delta_report", raising=False)

        import builtins

        original_import = builtins.__import__

        def block(name: str, *a: object, **kw: object) -> object:
            if name == "harness.scorer":
                raise ImportError("simulated absence of Epic 14")
            return original_import(name, *a, **kw)  # type: ignore[no-any-return]

        monkeypatch.setattr("builtins.__import__", block)
        runner = CliRunner()
        result = runner.invoke(app, ["baseline-comparison", _GT_NAME])
        assert result.exit_code == 2
        assert "baseline-runner not installed" in result.output
        assert "Epic 14" in result.output


def test_resolve_metric_filter_aliases() -> None:
    """Aliases (time, pivots, hallucinations, etc.) resolve to canonical metric names."""
    from silentwitness_agent.cli_commands.baseline_comparison import (
        _resolve_metric_filter,
    )

    assert "time_to_handoff_seconds_delta" in _resolve_metric_filter("time")
    assert "hallucination_rate_delta" in _resolve_metric_filter("hallucinations")
    assert _resolve_metric_filter("") == (
        "time_to_handoff_seconds_delta",
        "pivots_count_delta",
        "hallucination_rate_delta",
        "precision_delta",
        "recall_delta",
        "epistemic_honesty_count_delta",
    )
    assert "precision_delta" in _resolve_metric_filter("provenance")
