"""Integration tests for `silentwitness init` via Typer CliRunner (≥8 BDD scenarios)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from silentwitness_agent.cli import app

runner = CliRunner()


def _invoke(*args: str, env: dict[str, str] | None = None, cwd: Path | None = None) -> object:
    kwargs: dict[str, object] = {"catch_exceptions": False}
    if env is not None:
        kwargs["env"] = env
    if cwd is not None:
        kwargs["catch_exceptions"] = False
    return runner.invoke(app, list(args), **kwargs)


# ---------------------------------------------------------------------------
# 1. Happy-path: all expected paths created
# ---------------------------------------------------------------------------


def test_init_creates_skeleton(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    result = runner.invoke(app, ["init", "mr-evil-001"], catch_exceptions=False)
    assert result.exit_code == 0
    case = tmp_path / "cases" / "mr-evil-001"
    assert (case / "audit").is_dir()
    assert (case / "evidence").is_dir()
    assert (case / ".tool-output").is_dir()
    assert (case / "evidence.json").is_file()
    assert (case / "report.md").is_file()
    assert (case / "audit" / "cli.jsonl").is_file()


# ---------------------------------------------------------------------------
# 2. evidence.json shape is exactly {"records": [], "schema_version": 1}
# ---------------------------------------------------------------------------


def test_init_evidence_json_shape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    runner.invoke(app, ["init", "mr-evil-001"], catch_exceptions=False)
    data = json.loads((tmp_path / "cases" / "mr-evil-001" / "evidence.json").read_text())
    assert data == {"records": [], "schema_version": 1}


# ---------------------------------------------------------------------------
# 3. report.md starts with case_id frontmatter
# ---------------------------------------------------------------------------


def test_init_report_md_frontmatter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    runner.invoke(app, ["init", "mr-evil-002"], catch_exceptions=False)
    text = (tmp_path / "cases" / "mr-evil-002" / "report.md").read_text()
    assert text.startswith("---\ncase_id: mr-evil-002\n")
    assert "status: DRAFT" in text


# ---------------------------------------------------------------------------
# 4. audit/cli.jsonl gets exactly one entry with tool="cli.init"
# ---------------------------------------------------------------------------


def test_init_audit_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    runner.invoke(app, ["init", "mr-evil-003"], catch_exceptions=False)
    lines = (tmp_path / "cases" / "mr-evil-003" / "audit" / "cli.jsonl").read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["tool"] == "cli.init"


# ---------------------------------------------------------------------------
# 5. Re-init without --force → exit 1, no stdout
# ---------------------------------------------------------------------------


def test_reinit_without_force_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    runner.invoke(app, ["init", "mr-evil-004"], catch_exceptions=False)
    result = runner.invoke(app, ["init", "mr-evil-004"], catch_exceptions=False)
    assert result.exit_code == 1
    # CliRunner mixes stderr into output; check error message is present
    assert "already exists" in result.output
    # No success tree-shape on re-init (error path only)
    assert "initialized at" not in result.output


# ---------------------------------------------------------------------------
# 6. --force re-initialises and audit/cli.jsonl gains a second entry
# ---------------------------------------------------------------------------


def test_force_reinit_adds_second_audit_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    runner.invoke(app, ["init", "mr-evil-005"], catch_exceptions=False)
    result = runner.invoke(app, ["init", "mr-evil-005", "--force"], catch_exceptions=False)
    assert result.exit_code == 0
    lines = (tmp_path / "cases" / "mr-evil-005" / "audit" / "cli.jsonl").read_text().splitlines()
    assert len(lines) == 2
    assert all(json.loads(ln)["tool"] == "cli.init" for ln in lines)


# ---------------------------------------------------------------------------
# 7. --examiner flag lands in report.md frontmatter
# ---------------------------------------------------------------------------


def test_examiner_flag_in_frontmatter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    runner.invoke(app, ["init", "mr-evil-006", "--examiner", "aj"], catch_exceptions=False)
    text = (tmp_path / "cases" / "mr-evil-006" / "report.md").read_text()
    assert "examiner: aj" in text


# ---------------------------------------------------------------------------
# 8. --no-color strips ANSI sequences from stdout
# ---------------------------------------------------------------------------


def test_no_color_strips_ansi(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    result = runner.invoke(app, ["--no-color", "init", "mr-evil-007"], catch_exceptions=False)
    assert result.exit_code == 0
    assert not re.search(r"\x1b\[", result.output)
    assert "✓" in result.output


# ---------------------------------------------------------------------------
# 9. Unwritable parent → exit 2 with "system error"
# ---------------------------------------------------------------------------


def test_unwritable_parent_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cases_root = tmp_path / "ro_cases"
    cases_root.mkdir(mode=0o555)
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(cases_root))
    result = runner.invoke(app, ["init", "mr-evil-008"], catch_exceptions=False)
    assert result.exit_code == 2
    assert "system error" in result.stderr


# ---------------------------------------------------------------------------
# 10. --debug prints model.default to stderr
# ---------------------------------------------------------------------------


def test_debug_prints_model_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    result = runner.invoke(app, ["--debug", "init", "mr-evil-009"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "model.default" in result.stderr


# ---------------------------------------------------------------------------
# 11. stdout tree shape matches ux-spec §2.2 verbatim patterns
# ---------------------------------------------------------------------------


def test_stdout_tree_shape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    result = runner.invoke(app, ["init", "mr-evil-010"], catch_exceptions=False)
    assert result.exit_code == 0
    output = result.output
    assert "case 'mr-evil-010' initialized at" in output
    assert "├─ audit/" in output
    assert "├─ evidence/" in output
    assert "├─ report.md" in output
    assert "└─ .silentwitness/case.toml" in output


# ---------------------------------------------------------------------------
# 12. .silentwitness/case.toml actually exists on disk (tree vs reality)
# ---------------------------------------------------------------------------


def test_case_toml_exists_on_disk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    runner.invoke(app, ["init", "mr-evil-011"], catch_exceptions=False)
    toml_path = tmp_path / "cases" / "mr-evil-011" / ".silentwitness" / "case.toml"
    assert toml_path.is_file()
    content = toml_path.read_text(encoding="utf-8")
    assert "mr-evil-011" in content


# ---------------------------------------------------------------------------
# 13. Malformed --config-file → exit 2 with system error
# ---------------------------------------------------------------------------


def test_malformed_config_file_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    bad_toml = tmp_path / "bad.toml"
    bad_toml.write_text("[[not valid toml\n", encoding="utf-8")
    result = runner.invoke(
        app, ["--config-file", str(bad_toml), "init", "mr-evil-012"], catch_exceptions=False
    )
    assert result.exit_code == 2
    assert "system error" in result.output
