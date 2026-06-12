"""Integration tests for harness/delta_report.py."""

from __future__ import annotations

from pathlib import Path

import pytest

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "delta-results"


class TestComputeDeltaRows:
    def test_emits_seven_rows_one_per_metric(self) -> None:
        from harness.delta_report import compute_delta_rows

        b = {
            "precision": 0.5,
            "recall": 0.6,
            "hallucination_rate": 0.4,
            "time_to_first_finding_seconds": 90.0,
            "time_to_handoff_ready_report_seconds": 600.0,
            "pivot_count": 0,
            "epistemic_honesty_count": 0,
        }
        s = {
            "precision": 0.85,
            "recall": 0.8,
            "hallucination_rate": 0.0,
            "time_to_first_finding_seconds": 40.0,
            "time_to_handoff_ready_report_seconds": 250.0,
            "pivot_count": 2,
            "epistemic_honesty_count": 3,
        }
        rows = compute_delta_rows(b, s)
        assert len(rows) == 7
        metrics = {r.metric for r in rows}
        assert metrics == {
            "precision",
            "recall",
            "hallucination_rate",
            "time_to_first_finding_seconds",
            "time_to_handoff_ready_report_seconds",
            "pivot_count",
            "epistemic_honesty_count",
        }

    def test_precision_delta_higher_is_better(self) -> None:
        from harness.delta_report import compute_delta_rows

        rows = compute_delta_rows({"precision": 0.5}, {"precision": 0.85})
        precision_row = next(r for r in rows if r.metric == "precision")
        assert precision_row.baseline_value == pytest.approx(0.5)
        assert precision_row.silentwitness_value == pytest.approx(0.85)
        assert precision_row.delta == pytest.approx(0.35)
        assert precision_row.direction == "higher_is_better"

    def test_missing_baseline_value_yields_none_delta(self) -> None:
        from harness.delta_report import compute_delta_rows

        rows = compute_delta_rows({}, {"recall": 0.8})
        recall_row = next(r for r in rows if r.metric == "recall")
        assert recall_row.baseline_value is None
        assert recall_row.delta is None


class TestRenderMarkdown:
    def _report(self) -> object:
        from harness.delta_report import build_delta_report

        return build_delta_report("nitroba", _FIXTURES)

    def test_contains_dataset_id_in_h1(self) -> None:
        from harness.delta_report import render_markdown

        md = render_markdown(self._report())  # type: ignore[arg-type]
        assert md.startswith("# Δ vs vanilla Protocol SIFT baseline — nitroba")

    def test_contains_hallucination_heading(self) -> None:
        from harness.delta_report import render_markdown

        md = render_markdown(self._report())  # type: ignore[arg-type]
        assert "## Baseline hallucinated; SilentWitness refused" in md

    def test_callout_cited_paths_and_argv_appear(self) -> None:
        from harness.delta_report import render_markdown

        md = render_markdown(self._report())  # type: ignore[arg-type]
        assert "dropper.exe" in md
        assert "find /evidence/case-001 -iname dropper.exe" in md


class TestRenderBarChartPng:
    def test_writes_png_with_magic_bytes_in_range(self, tmp_path: Path) -> None:
        from harness.delta_report import build_delta_report, render_bar_chart_png

        report = build_delta_report("nitroba", _FIXTURES)
        out = tmp_path / "delta.png"
        render_bar_chart_png(report, out)
        assert out.exists()
        data = out.read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert 4000 <= len(data) <= 1_000_000


class TestBuildDeltaReport:
    def test_picks_most_recent_baseline(self) -> None:
        from harness.delta_report import build_delta_report

        report = build_delta_report("nitroba", _FIXTURES)
        assert report.baseline_result_path.name == "baseline-2026-06-12T18-00-00Z.json"
        assert report.silentwitness_result_path.name.startswith("silentwitness-")
        assert report.scoring_result_path.name.startswith("scoring-")

    def test_includes_baseline_hallucination_callouts(self) -> None:
        from harness.delta_report import build_delta_report

        report = build_delta_report("nitroba", _FIXTURES)
        assert len(report.baseline_hallucinated_callouts) == 2
        assert report.baseline_hallucinated_callouts[0].side == "baseline"


class TestCLI:
    def test_happy_path_writes_md_and_png(self, tmp_path: Path) -> None:
        from harness import delta_report as mod

        # Mirror fixture into tmp results dir
        case = tmp_path / "nitroba"
        case.mkdir()
        for src in (_FIXTURES / "nitroba").glob("*.json"):
            (case / src.name).write_bytes(src.read_bytes())

        rc = mod.main(
            [
                "--dataset",
                "nitroba",
                "--results-dir",
                str(tmp_path),
            ]
        )
        assert rc == 0
        md = case / "delta.md"
        png = case / "delta.png"
        assert md.exists()
        assert png.exists()
        assert "Δ vs vanilla Protocol SIFT baseline" in md.read_text()
        assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    def test_missing_inputs_exits_3(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from harness import delta_report as mod

        rc = mod.main(
            [
                "--dataset",
                "case-trapdoor",
                "--results-dir",
                str(_FIXTURES / "empty"),
            ]
        )
        assert rc == 3
        assert "no baseline result found" in capsys.readouterr().err

    def test_malformed_json_exits_2(self, tmp_path: Path) -> None:
        from harness import delta_report as mod

        case = tmp_path / "nitroba"
        case.mkdir()
        (case / "baseline-2026-06-12T18-00-00Z.json").write_text("{not-json")
        (case / "silentwitness-2026-06-12T18-05-00Z.json").write_text("{}")
        (case / "scoring-2026-06-12T18-10-00Z.json").write_text("{}")

        rc = mod.main(["--dataset", "nitroba", "--results-dir", str(tmp_path)])
        assert rc == 2


def test_module_dump_dump_roundtrips_delta_row() -> None:
    """DeltaRow survives model_dump_json → model_validate_json."""
    from harness.delta_report import DeltaRow

    row = DeltaRow(
        metric="precision",
        baseline_value=0.5,
        silentwitness_value=0.85,
        delta=0.35,
        direction="higher_is_better",
        interpretation="SilentWitness precision +0.350 vs baseline (higher is better)",
    )
    restored = DeltaRow.model_validate_json(row.model_dump_json())
    assert restored.delta == pytest.approx(0.35)
    assert restored.direction == "higher_is_better"


class TestReviewFindings:
    """Tests added in response to PR #201 review findings."""

    def test_insufficient_data_branch_in_interpretation(self) -> None:
        """compute_delta_rows with both sides empty surfaces 'insufficient data' interpretation."""
        from harness.delta_report import compute_delta_rows

        rows = compute_delta_rows({}, {})
        precision = next(r for r in rows if r.metric == "precision")
        assert precision.baseline_value is None
        assert precision.silentwitness_value is None
        assert precision.delta is None
        assert "insufficient data" in precision.interpretation

    def test_bool_value_does_not_coerce_to_int(self) -> None:
        """precision=True must NOT become 1.0 (bool is int subclass; Pydantic quirk)."""
        from harness.delta_report import compute_delta_rows

        rows = compute_delta_rows({"precision": True}, {"precision": 0.85})
        precision = next(r for r in rows if r.metric == "precision")
        assert precision.baseline_value is None

    def test_malformed_callout_drops_with_note(self, tmp_path: Path) -> None:
        """Malformed hallucination_examples entries are skipped; count surfaces in report.notes."""
        import json as _json

        from harness.delta_report import build_delta_report

        case = tmp_path / "nitroba"
        case.mkdir()
        # Copy good fixtures, then overwrite scoring with mixed good+bad callouts
        good_scoring = _json.loads(
            (_FIXTURES / "nitroba" / "scoring-2026-06-12T18-10-00Z.json").read_text()
        )
        good_scoring["hallucination_examples"] = [
            good_scoring["hallucination_examples"][0],
            {"side": "baseline"},  # missing required fields
            {"not_a_callout": "garbage"},  # missing 'side'
        ]
        (case / "baseline-2026-06-12T18-00-00Z.json").write_text(
            (_FIXTURES / "nitroba" / "baseline-2026-06-12T18-00-00Z.json").read_text()
        )
        (case / "silentwitness-2026-06-12T18-05-00Z.json").write_text(
            (_FIXTURES / "nitroba" / "silentwitness-2026-06-12T18-05-00Z.json").read_text()
        )
        (case / "scoring-2026-06-12T18-10-00Z.json").write_text(_json.dumps(good_scoring))

        report = build_delta_report("nitroba", tmp_path)
        assert len(report.baseline_hallucinated_callouts) == 1
        assert any("malformed hallucination_examples" in n for n in report.notes)
        assert any("2 malformed" in n for n in report.notes)

    def test_refused_count_surfaces_entity_gate_rejections(self) -> None:
        """silentwitness_refused_count comes from sw runner's entity_gate_rejections."""
        from harness.delta_report import build_delta_report, render_markdown

        report = build_delta_report("nitroba", _FIXTURES)
        # Fixture sets entity_gate_rejections=4
        assert report.silentwitness_refused_count == 4
        md = render_markdown(report)
        assert "count = 4)" in md

    def test_path_traversal_dataset_id_rejected(self, tmp_path: Path) -> None:
        """--dataset '../etc' → exit 2; no write outside results_dir."""
        from harness import delta_report as mod

        rc = mod.main(["--dataset", "../etc", "--results-dir", str(tmp_path)])
        assert rc == 2

    def test_markdown_callout_sanitizes_backticks(self) -> None:
        """Backticks/newlines in cited_artifact_path don't break Markdown code spans."""
        from datetime import UTC, datetime as _dt

        from harness.delta_report import render_markdown
        from harness.delta_report_models import DeltaReport, HallucinationCallout

        callout = HallucinationCallout(
            side="baseline",
            cited_artifact_path="C:\\evil`backtick\nnewline.exe",
            excerpt="x",
            evidence_shellout_argv=["find", "/ev", "-iname", "`evil`"],
            evidence_shellout_hits=0,
        )
        report = DeltaReport(
            dataset_id="nitroba",
            baseline_result_path=Path("b.json"),
            silentwitness_result_path=Path("s.json"),
            scoring_result_path=Path("sc.json"),
            generated_at=_dt.now(UTC),
            rows=[],
            baseline_hallucinated_callouts=[callout],
            silentwitness_refused_callouts=[],
            silentwitness_refused_count=0,
            notes=[],
        )
        md = render_markdown(report)
        # Original path had backtick + newline; sanitized form is in the output
        assert "`backtick" not in md  # original backtick replaced with '
        assert "\nnewline" not in md or md.count("nnewline") == 1  # newline collapsed to space

    def test_brand_colors_used_in_chart(self, tmp_path: Path) -> None:
        """Bar chart uses ux-spec §3.5 brand colors (#d96c5c / #7fb069)."""
        from harness.delta_report import _BASELINE_COLOR, _SW_COLOR

        assert _BASELINE_COLOR == "#d96c5c"
        assert _SW_COLOR == "#7fb069"
