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


def _prep_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, register_gt: bool = True
) -> tuple[Path, Path]:
    """Set up cases/<case_id> + tmp ground_truth tree; injects SILENTWITNESS_GT_DIR.

    All paths are under tmp_path — no writes to the real repo working tree.
    """
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
    gt_root = tmp_path / "gt-root"
    gt_root.mkdir()
    monkeypatch.setenv("SILENTWITNESS_GT_DIR", str(gt_root))
    if register_gt:
        (gt_root / f"{_GT_NAME}.json").write_text("[]")
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(cases_root))
    return cases_root, case_dir


@pytest.fixture
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cases_root, _ = _prep_case(tmp_path, monkeypatch)
    return cases_root


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
        _prep_case(tmp_path, monkeypatch, register_gt=False)
        runner = CliRunner()
        result = runner.invoke(app, ["baseline-comparison", _GT_NAME])
        assert result.exit_code == 2
        assert "GROUND_TRUTH_MISSING" in result.output.replace("\n", " ")

    def test_case_not_found_exits_1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
        monkeypatch.setenv("SILENTWITNESS_GT_DIR", str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(app, ["baseline-comparison", "no-such-case"])
        assert result.exit_code == 1
        assert "case 'no-such-case' not found" in result.output.replace("\n", " ")

    def test_table_renders_improvement_in_green(self, cli_env: Path) -> None:
        """Fixture: SW hallucination_rate=0.0, baseline=0.4 → -0.4 (improvement)."""
        runner = CliRunner()
        result = runner.invoke(app, ["baseline-comparison", _GT_NAME])
        assert result.exit_code == 0
        # hallucination_rate row shows negative delta (lower-is-better → green improvement)
        assert "-0.400" in result.output

    def test_table_renders_regression_in_yellow(self, cli_env: Path) -> None:
        """Force SW slower than baseline; expect positive (yellow) delta from real fixture math."""
        results = cli_env / "cases" / _GT_NAME / "results"
        for f in results.glob("silentwitness-*.json"):
            data = json.loads(f.read_text())
            data["time_to_handoff_ready_report_seconds"] = 999.0
            f.write_text(json.dumps(data))
        baseline_time: float | None = None
        for f in results.glob("scoring-*.json"):
            data = json.loads(f.read_text())
            data["silentwitness"]["time_to_handoff_ready_report_seconds"] = 999.0
            baseline_time = float(data["baseline"]["time_to_handoff_ready_report_seconds"])
            f.write_text(json.dumps(data))
        assert baseline_time is not None
        expected_delta = 999.0 - baseline_time

        runner = CliRunner()
        result = runner.invoke(app, ["baseline-comparison", _GT_NAME])
        assert result.exit_code == 0
        # Positive seconds delta = regression — assert exact value from fixture math
        assert f"+{expected_delta:.3f}" in result.output

    def test_color_styles_present_in_styled_output(
        self, cli_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Render to a recorded Console with styles; assert improvement → green styling."""
        from rich.console import Console as _Console

        from silentwitness_agent.cli_commands.baseline_comparison import (
            _render_table,
            _resolve_metric_filter,
        )

        delta = {
            "hallucination_rate_delta": -0.4,
            "time_to_handoff_seconds_delta": -100.0,
            "precision_delta": 0.3,
            "recall_delta": 0.2,
            "pivots_count_delta": 0.0,
            "epistemic_honesty_count_delta": 1.0,
        }
        rec = _Console(record=True, force_terminal=True, width=120)
        _render_table("nitroba", delta, _resolve_metric_filter(""), rec)
        styled = rec.export_text(styles=True, clear=False)
        # ANSI green = 32; ANSI yellow = 33
        assert "\x1b[32m" in styled  # improvement → green

    def test_epic14_missing_exits_2(self, cli_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import sys

        # Use sys.modules sentinel — narrower blast radius than __import__ monkeypatch,
        # and blocks BOTH names (review: import order should not determine pass/fail).
        monkeypatch.setitem(sys.modules, "harness.scorer", None)
        monkeypatch.setitem(sys.modules, "harness.delta_report", None)
        runner = CliRunner()
        result = runner.invoke(app, ["baseline-comparison", _GT_NAME])
        assert result.exit_code == 2
        flat = result.output.replace("\n", " ")
        assert "baseline-runner not installed" in flat
        assert "Epic 14" in flat


class TestReviewFindings:
    """Tests added in response to PR #202 review findings."""

    def test_zero_value_not_falsy_coalesced(self) -> None:
        """Scoring time=0.0 must NOT fall through to runner JSON via `or` (was a bug)."""
        from silentwitness_agent.cli_commands.baseline_comparison import _coalesce

        # 0.0 is preserved; only None is skipped
        assert _coalesce(0.0, 99.0) == 0.0
        assert _coalesce(None, 99.0) == 99.0
        assert _coalesce(None, None) is None

    def test_malformed_case_toml_surfaces_note(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Malformed case.toml emits a stderr warning instead of silent fallback."""
        _, case_dir = _prep_case(tmp_path, monkeypatch)
        (case_dir / "case.toml").write_text("this is not valid TOML [[[")
        # GT registered against case_dir.name (nitroba) so command can succeed past the GT check
        runner = CliRunner()
        result = runner.invoke(app, ["baseline-comparison", _GT_NAME])
        assert result.exit_code == 0
        # The warning may be in stderr (mixed-stream typer) or stdout
        combined = result.output
        assert "case.toml unreadable" in combined or "falling back" in combined

    def test_unknown_metrics_alias_surfaces_warning(self, cli_env: Path) -> None:
        """Unknown --metrics tokens emit a warning instead of silent ALL fallback."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["baseline-comparison", _GT_NAME, "--metrics", "bogus,alsobogus"]
        )
        assert result.exit_code == 0
        assert "unknown --metrics" in result.output.replace("\n", " ")

    def test_path_traversal_dataset_id_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Hostile dataset_id in case.toml is rejected by regex guard."""
        _, case_dir = _prep_case(tmp_path, monkeypatch)
        (case_dir / "case.toml").write_text(
            '[case]\ncase_id = "nitroba"\ndataset_id = "../../../etc/passwd"\n'
        )
        runner = CliRunner()
        result = runner.invoke(app, ["baseline-comparison", _GT_NAME])
        assert result.exit_code == 2
        assert "fails validation" in result.output.replace("\n", " ")

    def test_non_dict_result_json_rejected(self, cli_env: Path) -> None:
        """Non-dict top-level result JSON → clean exit 2, not uncaught AttributeError."""
        results = cli_env / "cases" / _GT_NAME / "results"
        for f in results.glob("baseline-*.json"):
            f.write_text('"not a dict"')
        runner = CliRunner()
        result = runner.invoke(app, ["baseline-comparison", _GT_NAME])
        assert result.exit_code == 2
        # Rich may wrap + double-space at line breaks — normalize whitespace
        import re

        flat = re.sub(r"\s+", " ", result.output)
        assert "top-level must be a JSON object" in flat

    def test_baseline_delta_json_schema_round_trip(self, cli_env: Path) -> None:
        """baseline-delta.json keys all have expected types (no string-vs-float drift)."""
        runner = CliRunner()
        result = runner.invoke(app, ["baseline-comparison", _GT_NAME])
        assert result.exit_code == 0
        data = json.loads((cli_env / "cases" / _GT_NAME / "baseline-delta.json").read_text())
        assert isinstance(data["case_id"], str)
        assert isinstance(data["dataset_id"], str)
        assert isinstance(data["baseline_mode"], str)
        for key in (
            "time_to_handoff_seconds_delta",
            "pivots_count_delta",
            "hallucination_rate_delta",
            "precision_delta",
            "recall_delta",
            "epistemic_honesty_count_delta",
        ):
            assert data[key] is None or isinstance(data[key], (int, float))


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
